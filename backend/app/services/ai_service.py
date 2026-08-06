"""
Thin wrapper around the OpenAI Chat Completions API. Isolating all OpenAI
calls in one module means: (1) swapping providers (e.g. to Gemini) only
touches this file, and (2) every caller gets the same JSON-mode parsing and
timeout/error handling instead of re-implementing it.
"""
import json

from openai import APIError, APITimeoutError, OpenAI

from app.config import settings
from app.utils.prompt_templates import build_pdf_extraction_messages, build_sql_generation_messages


class AIServiceError(Exception):
    """Raised with a user-friendly message when the AI call fails or returns something unusable."""


def _client() -> OpenAI:
    if not settings.OPENAI_API_KEY:
        raise AIServiceError("AI features are not configured — missing OPENAI_API_KEY on the server.")
    return OpenAI(api_key=settings.OPENAI_API_KEY, timeout=settings.AI_REQUEST_TIMEOUT_SECONDS)


def generate_sql(schema_text: str, user_prompt: str, history: list[dict] | None = None) -> dict:
    """Returns {"sql": str, "explanation": str}."""
    messages = build_sql_generation_messages(schema_text, user_prompt, history)
    data = _chat_json(messages)

    if "sql" not in data or not isinstance(data["sql"], str):
        raise AIServiceError("The AI response didn't include a usable SQL query. Try rephrasing your question.")

    return {"sql": data["sql"].strip(), "explanation": data.get("explanation", "").strip()}


def extract_pdf_records(target_columns: list[str], document_text: str) -> list[dict]:
    """Returns a list of record dicts, keyed by target_columns, extracted from document_text."""
    messages = build_pdf_extraction_messages(target_columns, document_text)
    data = _chat_json(messages)

    records = data.get("records")
    if not isinstance(records, list):
        raise AIServiceError("The AI could not extract structured records from this PDF.")
    return records


def _chat_json(messages: list[dict]) -> dict:
    client = _client()
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
    except APITimeoutError as exc:
        raise AIServiceError("The AI took too long to respond. Please try again.") from exc
    except APIError as exc:
        raise AIServiceError(f"The AI service returned an error: {exc.__class__.__name__}.") from exc

    raw_content = response.choices[0].message.content
    try:
        return json.loads(raw_content)
    except (json.JSONDecodeError, TypeError) as exc:
        raise AIServiceError("The AI returned a response that wasn't valid JSON.") from exc
