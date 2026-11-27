
import logging

from chunking import create_document_chunks
from database import create_chunks, delete_document_chunks, update_document
from embeddings import generate_embeddings

logger = logging.getLogger(__name__)

# Limit the number of chunks inserted in a single database request.
INSERT_BATCH_SIZE = 50


def index_document(document_id: str, pages: list[dict]) -> int:
    """Create embeddings and store document chunks in the database."""

    try:
        # Prevent incomplete documents from appearing in search results.
        update_document(document_id, {"status": "processing"})

        # Split document pages into smaller text chunks.
        chunks = create_document_chunks(document_id, pages)

        if not chunks:
            raise ValueError("Document contains no indexable text")

        # Generate embeddings for all chunk contents.
        texts = [chunk["content"] for chunk in chunks]
        embeddings = generate_embeddings(texts)

        if len(chunks) != len(embeddings):
            raise RuntimeError("Chunk and embedding count mismatch")

        # Attach the corresponding embedding to each chunk.
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding

        # Remove previous chunks to support document reindexing.
        delete_document_chunks(document_id)

        # Insert chunks in smaller batches.
        for start in range(0, len(chunks), INSERT_BATCH_SIZE):
            batch = chunks[start:start + INSERT_BATCH_SIZE]
            create_chunks(batch)

        # Make the document searchable only after successful indexing.
        update_document(document_id, {"status": "ready"})

        return len(chunks)

    except Exception:
        logger.exception(
            "Failed to index document: %s", document_id
        )

        # Remove incomplete indexing results.
        try:
            delete_document_chunks(document_id)
        except Exception:
            logger.exception("Failed to clean up document chunks")

        # Keep failed documents excluded from search results.
        try:
            update_document(document_id, {"status": "failed"})
        except Exception:
            logger.exception("Failed to update document status")

        raise
