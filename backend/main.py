
import logging
from pathlib import Path
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from database import download_file, get_document, get_documents
from documents import MAX_FILE_SIZE, process_document, save_document
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from indexing import index_document
from rag import answer_question
from schemas import ChatRequest

logger = logging.getLogger(__name__)

# Initialize the FastAPI application.
app = FastAPI()


@app.get("/api/health")
def health():
    """Check if the backend server is running."""
    return {"status": "ok"}


@app.post("/api/documents")
def upload_documents(files: Annotated[list[UploadFile], File()]):
    """Process, save and index uploaded PDF and DOCX documents."""

    # Limit the number of files per request.
    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 files per request"
        )

    results = []

    # Process each file separately.
    for file in files:
        filename = file.filename or "unknown"

        try:
            # Limit the amount of file content loaded into memory.
            file_content = file.file.read(MAX_FILE_SIZE + 1)

            # Validate the document and extract text from each page.
            processed = process_document(filename, file_content)

            try:
                # Save the original file, PDF preview and metadata.
                document = save_document(
                    filename, file_content, processed
                )

                if document is None:
                    raise RuntimeError("Document was not saved")

            except Exception:
                logger.exception("Failed to save document")

                results.append({
                    "filename": filename,
                    "status": "failed",
                    "error": "Failed to save document"
                })

                # Continue processing the remaining files.
                continue

            try:
                # Index the document using the already extracted pages.
                chunk_count = index_document(
                    document["id"],
                    processed["pages"]
                )

            except Exception:
                logger.exception("Failed to index uploaded document")

                results.append({
                    "id": document["id"],
                    "filename": filename,
                    "status": "failed",
                    "error": "Failed to index document"
                })

                continue

            # Return metadata after successful indexing.
            results.append({
                "id": document["id"],
                "filename": document["filename"],
                "file_type": document["file_type"],
                "page_count": document["page_count"],
                "empty_pages": processed["empty_pages"],
                "chunk_count": chunk_count,
                "status": "ready"
            })

        except ValueError as error:
            # Return a specific message for document validation errors.
            results.append({
                "filename": filename,
                "status": "failed",
                "error": str(error)
            })

        except Exception:
            # Log unexpected errors without exposing internal details.
            logger.exception("Failed to process document")

            results.append({
                "filename": filename,
                "status": "failed",
                "error": "Failed to process document"
            })

        finally:
            # Always close the uploaded file, even if processing fails.
            file.file.close()

    return {"documents": results}


@app.get("/api/documents")
def list_documents():
    """Return the list of documents stored in the database."""
    return {"documents": get_documents()}


@app.get("/api/documents/{document_id}/preview")
def preview_document(document_id: UUID):
    """Return the PDF preview of a document."""

    try:
        # Retrieve trusted document metadata from the database.
        document = get_document(str(document_id))

        if document is None:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )

        # Use the PDF preview created during document processing.
        preview_path = document.get("preview_path")

        if not preview_path:
            raise HTTPException(
                status_code=404,
                detail="Document preview not available"
            )

        # Download the PDF from the private storage bucket.
        pdf_content = download_file(preview_path)

        # Use a PDF extension even when the original file is DOCX.
        filename = Path(document["filename"]).stem + ".pdf"

        # Encode the filename to support spaces and Unicode characters.
        encoded_filename = quote(filename, safe="")

        # Display the PDF directly in the browser.
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f"inline; filename*=UTF-8''{encoded_filename}"
                ),
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff"
            }
        )

    except HTTPException:
        raise

    except Exception:
        logger.exception("Failed to retrieve document preview")

        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve document preview"
        )


@app.post("/api/chat")
def chat(request: ChatRequest):
    """Answer a question using indexed document sources."""

    # Convert UUID objects into strings for the database query.
    document_ids = None

    if request.document_ids is not None:
        document_ids = [
            str(document_id)
            for document_id in request.document_ids
        ]

    try:
        return answer_question(
            question=request.question,
            document_ids=document_ids
        )

    except Exception:
        logger.exception("Failed to answer document question")

        raise HTTPException(
            status_code=500,
            detail="Failed to generate an answer"
        )
