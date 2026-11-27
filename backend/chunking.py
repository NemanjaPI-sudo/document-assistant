import tiktoken

# Default chunking configuration.
CHUNK_SIZE = 350
CHUNK_OVERLAP = 50

# Use the tokenizer compatible with the planned embedding model.
encoding = tiktoken.get_encoding("cl100k_base")


def split_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """Split text into smaller overlapping chunks."""

    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("Invalid chunk overlap")

    if not text.strip():
        return []

    # Convert text into tokens.
    tokens = encoding.encode(text, disallowed_special=())

    chunks = []
    start = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))

        # Avoid splitting a UTF-8 character at the end of a chunk.
        while end > start:
            try:
                chunk_text = encoding.decode(
                    tokens[start:end],
                    errors="strict"
                )
                break
            except UnicodeDecodeError:
                end -= 1

        if end == start:
            raise ValueError("Unable to create a valid text chunk")

        if chunk_text.strip():
            chunks.append(chunk_text)

        # Stop when the end of the text is reached.
        if end == len(tokens):
            break

        # Preserve some context for the next chunk.
        start = max(start + 1, end - overlap)

        # Ensure the next chunk starts at a valid UTF-8 boundary.
        while start < end:
            try:
                encoding.decode(tokens[start:end], errors="strict")
                break
            except UnicodeDecodeError:
                start += 1

    return chunks


def create_document_chunks(
    document_id: str,
    pages: list[dict]
) -> list[dict]:
    """Create text chunks while preserving document and page references."""
    chunks = []

    # Process each page separately to preserve accurate citations.
    for page in pages:
        page_number = page["page_number"]
        content = page["content"]

        # Skip pages without extractable text.
        if not content.strip():
            continue

        page_chunks = split_text(content)

        # Store each chunk with its document ID and page number.
        for chunk_index, chunk_content in enumerate(page_chunks):
            chunks.append({
                "document_id": document_id,
                "page_number": page_number,
                "chunk_index": chunk_index,
                "content": chunk_content
            })

    return chunks
