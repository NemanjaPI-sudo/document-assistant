
-- Enable pgvector for storing embeddings and performing vector search.
CREATE EXTENSION IF NOT EXISTS vector
WITH SCHEMA extensions;


-- Document metadata

-- Store information about uploaded PDF and DOCX documents.
CREATE TABLE public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK (file_type IN ('pdf', 'docx')),
    storage_path TEXT NOT NULL,
    preview_path TEXT,
    page_count INTEGER CHECK (page_count > 0),
    status TEXT NOT NULL DEFAULT 'processing'
        CHECK (status IN ('processing', 'ready', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enable row-level security to restrict direct database access.
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

-- Prevent anonymous and authenticated users from accessing the table.
REVOKE ALL ON TABLE public.documents FROM anon, authenticated;

-- Allow the backend to manage document records.
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE public.documents
TO service_role;


-- Document chunks and embeddings

-- Store smaller text segments with their original page numbers.
-- Each chunk contains a 1536-dimensional embedding for vector search.
CREATE TABLE public.document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Automatically delete related chunks when a document is deleted.
    document_id UUID NOT NULL
        REFERENCES public.documents(id) ON DELETE CASCADE,

    page_number INTEGER NOT NULL CHECK (page_number > 0),
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    embedding extensions.vector(1536) NOT NULL,

    -- Prevent duplicate chunk positions within the same document page.
    UNIQUE (document_id, page_number, chunk_index)
);

-- Restrict direct access to document chunks and embeddings.
ALTER TABLE public.document_chunks
ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.document_chunks
FROM anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE public.document_chunks
TO service_role;


-- Supabase Storage configuration

-- Create a private bucket for original documents and PDF previews.
-- Only PDF and DOCX files up to 20 MB are allowed.
INSERT INTO storage.buckets (
    id,
    name,
    public,
    file_size_limit,
    allowed_mime_types
)
VALUES (
    'documents',
    'documents',
    false,
    20971520,
    ARRAY[
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
)
-- Keep the existing bucket if it has already been created.
ON CONFLICT (id) DO NOTHING;


-- Vector similarity search

-- Find the document chunks most relevant to a query embedding.
-- Return up to eight matching chunks by default.
-- Optionally limit the search to specific documents.
CREATE OR REPLACE FUNCTION public.match_document_chunks(
    query_embedding extensions.vector(1536),
    match_count INTEGER DEFAULT 8,
    filter_document_ids UUID[] DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    filename TEXT,
    page_number INTEGER,
    content TEXT,
    similarity DOUBLE PRECISION
)
LANGUAGE sql
STABLE
SET search_path = public, extensions
AS $$
    SELECT
        dc.id,
        dc.document_id,
        d.filename,
        dc.page_number,
        dc.content,

        -- Convert cosine distance into cosine similarity.
        1 - (dc.embedding <=> query_embedding) AS similarity

    FROM public.document_chunks dc

    -- Include document metadata for source citations.
    JOIN public.documents d ON d.id = dc.document_id

    -- Only search documents that have been fully processed.
    WHERE d.status = 'ready'
        AND (
            -- Search all ready documents when no filter is provided.
            filter_document_ids IS NULL
            OR dc.document_id = ANY(filter_document_ids)
        )

    -- Return the closest embeddings first.
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
$$;


-- Vector search permissions

-- Prevent direct execution by public and client-side roles.
REVOKE EXECUTE ON FUNCTION public.match_document_chunks(
    extensions.vector, INTEGER, UUID[]
)
FROM PUBLIC, anon, authenticated;

-- Allow the backend to execute the vector search function.
GRANT EXECUTE ON FUNCTION public.match_document_chunks(
    extensions.vector, INTEGER, UUID[]
)
TO service_role;
