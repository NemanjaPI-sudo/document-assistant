import os

from dotenv import load_dotenv

from supabase import create_client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SECRET_KEY")

if not supabase_url or not supabase_key:
    raise RuntimeError("Missing Supabase configuration")

supabase = create_client(supabase_url, supabase_key)

def create_document(document):
    response = supabase.table("documents").insert(document).execute()
    return response.data[0]


def get_documents():
    response = supabase.table("documents").select("*").execute()
    return response.data


def update_document(document_id, data):
    response = supabase.table("documents").update(data).eq(
        "id", document_id
    ).execute()
    return response.data


def delete_document(document_id):
    response = supabase.table("documents").delete().eq(
        "id", document_id
    ).execute()
    return response.data

def create_chunks(chunks):
    response = supabase.table("document_chunks").insert(chunks).execute()
    return response.data


def get_document_chunks(document_id):
    response = supabase.table("document_chunks").select("*").eq(
        "document_id", document_id
    ).execute()
    return response.data


def delete_document_chunks(document_id):
    response = supabase.table("document_chunks").delete().eq(
        "document_id", document_id
    ).execute()
    return response.data

def upload_file(path, file_content, content_type):
    return supabase.storage.from_("documents").upload(
        path,
        file_content,
        {"content-type": content_type}
    )


def download_file(path):
    return supabase.storage.from_("documents").download(path)


def delete_file(path):
    return supabase.storage.from_("documents").remove([path])

def match_chunks(query_embedding, match_count=8, document_ids=None):
    response = supabase.rpc(
        "match_document_chunks",
        {
            "query_embedding": query_embedding,
            "match_count": match_count,
            "filter_document_ids": document_ids
        }
    ).execute()

    return response.data