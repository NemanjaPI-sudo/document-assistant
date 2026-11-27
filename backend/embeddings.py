
import math
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load Gemini API configuration.
load_dotenv(Path(__file__).resolve().parent / ".env")

gemini_api_key = os.getenv("GEMINI_API_KEY")
embedding_model = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-001"
)

# Embedding configuration.
EMBEDDING_DIMENSIONS = 1536
BATCH_SIZE = 20

if not gemini_api_key:
    raise RuntimeError("Missing Gemini API key")

client = genai.Client(api_key=gemini_api_key)


def normalize_embedding(values: list[float]) -> list[float]:
    """Validate and normalize an embedding to unit length."""

    if len(values) != EMBEDDING_DIMENSIONS:
        raise RuntimeError("Invalid embedding dimensions")

    magnitude = math.sqrt(sum(value ** 2 for value in values))

    if magnitude == 0 or not math.isfinite(magnitude):
        raise RuntimeError("Invalid embedding magnitude")

    return [value / magnitude for value in values]


def generate_embeddings(
    texts: list[str],
    task_type: str = "RETRIEVAL_DOCUMENT"
) -> list[list[float]]:
    """Generate embeddings for multiple texts in batches."""

    if not texts:
        return []

    if any(not text.strip() for text in texts):
        raise ValueError("Cannot embed empty text")

    embeddings = []

    # Split the input into smaller batches.
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]

        # Request a separate embedding for each text.
        response = client.models.embed_content(
            model=embedding_model,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=EMBEDDING_DIMENSIONS
            )
        )

        # Ensure every input text has a corresponding embedding.
        if (
            not response.embeddings
            or len(response.embeddings) != len(batch)
        ):
            raise RuntimeError("Invalid number of embeddings returned")

        for embedding in response.embeddings:
            values = embedding.values

            if values is None:
                raise RuntimeError("Missing embedding values")

            embeddings.append(normalize_embedding(values))

    return embeddings


def generate_embedding(
    text: str,
    task_type: str = "RETRIEVAL_DOCUMENT"
) -> list[float]:
    """Generate an embedding for a single text."""

    # Reuse the batch implementation for individual requests.
    return generate_embeddings([text], task_type)[0]
