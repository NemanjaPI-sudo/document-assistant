
import os

from dotenv import load_dotenv

from supabase import create_client

# Load environment variables from the .env file.
load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SECRET_KEY")

# Stop initialization if the required configuration is missing.
if not supabase_url or not supabase_key:
    raise RuntimeError("Missing Supabase configuration")

# Initialize the Supabase client for database and storage operations.
supabase = create_client(supabase_url, supabase_key)


# Document database operations

def create_document(document: dict) -> dict:
    """Insert a new document and return the created record."""
    response = supabase.table("documents").insert(document).execute()

    if not response.data:
        raise RuntimeError("Failed to create document")

    created_document = response.data[0]

    # Ensure the database returns a valid document record.
    if not isinstance(created_document, dict):
        raise TypeError("Invalid database response")

    return created_document


def get_documents() -> list[dict]:
    """Retrieve all documents from the database."""
    response = supabase.table("documents").select("*").execute()

    # Validate the database response.
    if not isinstance(response.data, list):
        raise TypeError("Invalid documents response")

    documents = []

    for item in response.data:
        if not isinstance(item, dict):
            raise TypeError("Invalid document record")

        documents.append(item)

    return documents


def get_document(document_id: str) -> dict | None:
    """Retrieve a single document using its unique ID."""
    response = supabase.table("documents").select("*").eq(
        "id", document_id
    ).execute()

    if not isinstance(response.data, list):
        raise TypeError("Invalid document response")

    # Return None when the requested document does not exist.
    if not response.data:
        return None

    document = response.data[0]

    if not isinstance(document, dict):
        raise TypeError("Invalid document record")

    return document


def update_document(document_id, data):
    """Update a document using its unique ID."""
    response = supabase.table("documents").update(data).eq(
        "id", document_id
    ).execute()
    return response.data


def delete_document(document_id):
    """Delete a document and its related chunks from the database."""
    # Related chunks are automatically removed by ON DELETE CASCADE.
    # Files in storage must be deleted separately.
    response = supabase.table("documents").delete().eq(
        "id", document_id
    ).execute()
    return response.data


# Document chunk operations

def create_chunks(chunks):
    """Insert multiple document chunks into the database."""
    response = supabase.table("document_chunks").insert(chunks).execute()
    return response.data


def get_document_chunks(document_id: str) -> list[dict]:
    """Retrieve all chunks belonging to a specific document."""
    response = supabase.table("document_chunks").select("*").eq(
        "document_id", document_id
    ).execute()

    # Validate the database response.
    if not isinstance(response.data, list):
        raise TypeError("Invalid chunks response")

    chunks = []

    for item in response.data:
        if not isinstance(item, dict):
            raise TypeError("Invalid chunk record")

        chunks.append(item)

    return chunks


def delete_document_chunks(document_id):
    """Delete all chunks belonging to a specific document."""
    response = supabase.table("document_chunks").delete().eq(
        "document_id", document_id
    ).execute()
    return response.data


# Supabase Storage operations

def upload_file(path, file_content, content_type):
    """Upload a file to the private documents bucket."""
    return supabase.storage.from_("documents").upload(
        path,
        file_content,
        {"content-type": content_type}
    )


def download_file(path):
    """Download a file from storage using its path."""
    return supabase.storage.from_("documents").download(path)


def delete_file(path):
    """Remove a file from the documents bucket."""
    return supabase.storage.from_("documents").remove([path])


# Vector search operations

def match_chunks(
    query_embedding: list[float],
    match_count: int = 8,
    document_ids: list[str] | None = None
) -> list[dict]:
    """Find document chunks most similar to the query embedding."""

    # Call our PostgreSQL vector similarity search function.
    response = supabase.rpc(
        "match_document_chunks",
        {
            "query_embedding": query_embedding,
            "match_count": match_count,
            "filter_document_ids": document_ids
        }
    ).execute()

    # Validate the database response before returning search results.
    if not isinstance(response.data, list):
        raise TypeError("Invalid search response")

    results = []

    for item in response.data:
        if not isinstance(item, dict):
            raise TypeError("Invalid search result")

        results.append(item)

    return results
