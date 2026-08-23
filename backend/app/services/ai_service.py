"""
Thin wrapper around the Google Gemini API. Isolating all Gemini calls in one
module means: (1) swapping providers (e.g. to OpenAI) only touches
this file, and (2) every caller gets the same JSON-mode parsing and
timeout/error handling instead of re-implementing it.
"""
import json

import google.generativeai as genai
from google.api_core.exceptions import DeadlineExceeded, GoogleAPICallError

from app.config import settings
from app.utils.prompt_templates import build_pdf_extraction_messages, build_sql_generation_messages


class AIServiceError(Exception):
    """Raised with a user-friendly message when the AI call fails or returns something unusable."""


def _model(system_instruction: str) -> genai.GenerativeModel:
    if not settings.GEMINI_API_KEY:
        raise AIServiceError("AI features are not configured — missing GEMINI_API_KEY on the server.")
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=system_instruction,
        generation_config=genai.types.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )


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
    # Gemini takes the system prompt separately from the turn history, and
    # uses "model" (not "assistant") as the role for prior AI turns.
    system_instruction = ""
    contents = []
    for msg in messages:
        if msg["role"] == "system":
            system_instruction = msg["content"]
        else:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [msg["content"]]})

    model = _model(system_instruction)
    try:
        response = model.generate_content(
            contents,
            request_options={"timeout": settings.AI_REQUEST_TIMEOUT_SECONDS},
        )
    except DeadlineExceeded as exc:
        raise AIServiceError("The AI took too long to respond. Please try again.") from exc
    except GoogleAPICallError as exc:
        raise AIServiceError(f"The AI service returned an error: {exc.__class__.__name__}.") from exc

    try:
        return json.loads(response.text)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise AIServiceError("The AI returned a response that wasn't valid JSON.") from exc
