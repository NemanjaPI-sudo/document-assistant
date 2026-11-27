CREATE EXTENSION IF NOT EXISTS vector
WITH SCHEMA extensions;

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

ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.documents FROM anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE public.documents
TO service_role;

CREATE TABLE public.document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL
        REFERENCES public.documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL CHECK (page_number > 0),
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    embedding extensions.vector(1536) NOT NULL,
    UNIQUE (document_id, page_number, chunk_index)
);

ALTER TABLE public.document_chunks
ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.document_chunks
FROM anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE public.document_chunks
TO service_role;

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
ON CONFLICT (id) DO NOTHING;

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
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM public.document_chunks dc
    JOIN public.documents d ON d.id = dc.document_id
    WHERE d.status = 'ready'
        AND (
            filter_document_ids IS NULL
            OR dc.document_id = ANY(filter_document_ids)
        )
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
$$;

REVOKE EXECUTE ON FUNCTION public.match_document_chunks(
    extensions.vector, INTEGER, UUID[]
)
FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.match_document_chunks(
    extensions.vector, INTEGER, UUID[]
)
TO service_role;