
from database import match_chunks
from embeddings import generate_embedding

# Default number of chunks retrieved for each question.
DEFAULT_MATCH_COUNT = 8


def retrieve_chunks(
    question: str,
    document_ids: list[str] | None = None,
    match_count: int = DEFAULT_MATCH_COUNT
) -> list[dict]:
    """Retrieve relevant document chunks for a user question."""

    if not question.strip():
        raise ValueError("Question cannot be empty")

    if match_count <= 0:
        raise ValueError("Match count must be positive")

    # Skip the API request when no documents are selected.
    if document_ids == []:
        return []

    # Convert the user question into a search embedding.
    query_embedding = generate_embedding(
        question,
        "RETRIEVAL_QUERY"
    )

    # Search the vector database using our SQL function.
    return match_chunks(
        query_embedding,
        match_count=match_count,
        document_ids=document_ids
    )
