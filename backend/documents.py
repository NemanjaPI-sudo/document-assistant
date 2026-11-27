
import logging
import os
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

import pymupdf
from database import create_document, delete_file, upload_file
from dotenv import load_dotenv

# Load configuration from the backend .env file.
load_dotenv(Path(__file__).resolve().parent / ".env")

logger = logging.getLogger(__name__)

# File upload restrictions.
MAX_FILE_SIZE = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


# PDF text extraction

def extract_pdf_pages(file_content: bytes):
    """Extract text from a PDF while preserving page numbers."""
    pages = []

    try:
        with pymupdf.open(stream=file_content, filetype="pdf") as document:
            if not document.is_pdf:
                raise ValueError("Invalid PDF format")

            if document.needs_pass:
                raise ValueError("Password-protected PDF is not supported")

            if document.page_count == 0:
                raise ValueError("PDF has no pages")

            # Preserve page numbers for accurate source citations.
            for page_index in range(document.page_count):
                page = document.load_page(page_index)

                pages.append({
                    "page_number": page_index + 1,
                    "content": page.get_text()
                })

    except (pymupdf.FileDataError, pymupdf.EmptyFileError) as error:
        raise ValueError("Invalid or corrupted PDF file") from error

    # Reject documents without extractable text.
    # OCR is not supported in the current version.
    if not any(page["content"].strip() for page in pages):
        raise ValueError("PDF contains no extractable text")

    return pages


# File validation

def validate_file(filename: str, file_content: bytes):
    """Validate the file extension, size and basic DOCX structure."""
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Only PDF and DOCX files are supported")

    if not file_content:
        raise ValueError("File is empty")

    if len(file_content) > MAX_FILE_SIZE:
        raise ValueError("File exceeds the 20 MB size limit")

    # DOCX files are ZIP archives with a specific internal structure.
    # Check the required files and archive integrity.
    if extension == ".docx":
        try:
            with ZipFile(BytesIO(file_content)) as document:
                if (
                    "[Content_Types].xml" not in document.namelist()
                    or "word/document.xml" not in document.namelist()
                    or document.testzip() is not None
                ):
                    raise ValueError("Invalid or corrupted DOCX file")
        except BadZipFile as error:
            raise ValueError("Invalid or corrupted DOCX file") from error

    # Return the file type without the leading dot.
    return extension.removeprefix(".")


# DOCX conversion

def convert_docx_to_pdf(file_content: bytes) -> bytes:
    """Convert a DOCX document to PDF using LibreOffice."""
    validate_docx(file_content)

    libreoffice_path = os.getenv("LIBREOFFICE_PATH")

    if not libreoffice_path:
        raise RuntimeError("LibreOffice path is not configured")

    # Temporary files are automatically removed after conversion.
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        input_path = temp_path / "document.docx"
        output_path = temp_path / "document.pdf"
        profile_path = temp_path / "profile"

        input_path.write_bytes(file_content)

        # Use an isolated LibreOffice profile to avoid conflicts
        # with other running instances.
        command = [
            libreoffice_path,
            f"-env:UserInstallation={profile_path.as_uri()}",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(temp_path),
            str(input_path)
        ]

        try:
            # Run LibreOffice without a graphical interface.
            # Limit the execution time to prevent long-running conversions.
            result = subprocess.run(
                command,
                capture_output=True,
                timeout=60,
                check=False
            )
        except subprocess.TimeoutExpired as error:
            raise ValueError("DOCX conversion timed out") from error

        # Check both the exit code and the generated PDF file.
        if result.returncode != 0 or not output_path.is_file():
            raise ValueError("Failed to convert DOCX to PDF")

        return output_path.read_bytes()


def validate_docx(file_content: bytes):
    """Check whether the file has the required DOCX archive structure."""
    try:
        with ZipFile(BytesIO(file_content)) as archive:
            files = archive.namelist()

            required_files = {
                "[Content_Types].xml",
                "word/document.xml"
            }

            if not required_files.issubset(files):
                raise ValueError("Invalid DOCX format")

    except BadZipFile as error:
        raise ValueError("Invalid or corrupted DOCX file") from error


# Document processing

def process_document(filename: str, file_content: bytes):
    """Validate and process a PDF or DOCX document."""
    file_type = validate_file(filename, file_content)

    # Convert DOCX files to PDF to use the same extraction logic
    # and maintain consistent page references.
    if file_type == "docx":
        pdf_content = convert_docx_to_pdf(file_content)
    else:
        pdf_content = file_content

    pages = extract_pdf_pages(pdf_content)

    # Identify pages without extractable text.
    empty_pages = [
        page["page_number"]
        for page in pages
        if not page["content"].strip()
    ]

    return {
        "file_type": file_type,
        "page_count": len(pages),
        "pages": pages,
        "pdf_content": pdf_content,
        "empty_pages": empty_pages
    }


# Document storage

def save_document(
    filename: str,
    file_content: bytes,
    processed: dict
) -> dict:
    """Save document files and metadata to Supabase."""

    # Use a unique ID to prevent filename conflicts in storage.
    document_id = str(uuid4())
    file_type = processed["file_type"]

    storage_path = f"{document_id}/original.{file_type}"

    # PDF files can be used directly for preview.
    # DOCX files require a separate converted PDF.
    if file_type == "pdf":
        content_type = "application/pdf"
        preview_path = storage_path
    else:
        content_type = (
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        )
        preview_path = f"{document_id}/preview.pdf"

    # Track uploaded files for cleanup if an operation fails.
    uploaded_paths = []

    try:
        upload_file(storage_path, file_content, content_type)
        uploaded_paths.append(storage_path)

        # Store the converted PDF for document preview and citations.
        if file_type == "docx":
            upload_file(
                preview_path,
                processed["pdf_content"],
                "application/pdf"
            )
            uploaded_paths.append(preview_path)

        # Keep the document in processing status until indexing is complete.
        document = create_document({
            "id": document_id,
            "filename": filename,
            "file_type": file_type,
            "storage_path": storage_path,
            "preview_path": preview_path,
            "page_count": processed["page_count"],
            "status": "processing"
        })

        return document

    except Exception:
        # Attempt to remove uploaded files if saving fails.
        for path in uploaded_paths:
            try:
                delete_file(path)
            except Exception:
                logger.exception("Failed to delete file: %s", path)

        # Preserve the original exception for the API error handler.
        raise
