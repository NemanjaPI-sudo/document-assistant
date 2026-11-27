import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load Gemini API configuration.
load_dotenv(Path(__file__).resolve().parent / ".env")

gemini_api_key = os.getenv("GEMINI_API_KEY")
llm_model = os.getenv(
    "GEMINI_LLM_MODEL",
    "gemini-3.1-flash-lite"
)

if not gemini_api_key:
    raise RuntimeError("Missing Gemini API key")

client = genai.Client(api_key=gemini_api_key)


def generate_answer(
    system_instructions: str,
    prompt: str
) -> dict:
    """Generate a structured JSON response using Gemini."""

    # Send the prepared context without external search tools.
    response = client.models.generate_content(
        model=llm_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instructions,
            response_mime_type="application/json",
            temperature=0.1,
            max_output_tokens=4096
        )
    )

    response_text = response.text

    if not response_text:
        raise RuntimeError("Empty response from Gemini")

    # Parse the generated JSON response.
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError as error:
        raise RuntimeError("Invalid JSON response from Gemini") from error

    # Ensure the response has the expected top-level type.
    if not isinstance(result, dict):
        raise TypeError("Invalid LLM response format")

    return result
