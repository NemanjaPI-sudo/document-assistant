from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """Request model for document-based questions."""

    question: str = Field(
        min_length=1,
        max_length=2000
    )

    document_ids: list[UUID] | None = None

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        """Reject empty questions and remove surrounding whitespace."""
        value = value.strip()

        if not value:
            raise ValueError("Question cannot be empty")

        return value
