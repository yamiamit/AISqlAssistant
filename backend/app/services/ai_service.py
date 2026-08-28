"""
Thin wrapper around the chat-completion provider (Groq by default, Gemini
optional). Isolating every provider call in one module means: (1) swapping
providers only touches this file, and (2) every caller gets the same JSON-mode
parsing and timeout/error handling instead of re-implementing it.

Error messages here are load-bearing beyond the UI: evals/runner.py classifies
failures by matching substrings in them ("took too long", "429", "quota", ...),
and a rate limit mislabelled as a timeout sends you to the wrong fix. Both
provider paths therefore raise the same vocabulary — see _MARKER comments below.
"""
import json

import groq

from app.config import settings
from app.utils.prompt_templates import build_pdf_extraction_messages, build_sql_generation_messages


class AIServiceError(Exception):
    """Raised with a user-friendly message when the AI call fails or returns something unusable."""


def _gemini_model(system_instruction: str):
    # Imported lazily so the Gemini SDK stays an optional dependency of the
    # non-default provider path.
    import google.generativeai as genai

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
    if settings.AI_PROVIDER == "gemini":
        return _chat_json_gemini(messages)
    return _chat_json_groq(messages)


def _parse_json(raw: str | None) -> dict:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise AIServiceError("The AI returned a response that wasn't valid JSON.") from exc


def _chat_json_groq(messages: list[dict]) -> dict:
    # Groq's API is OpenAI-shaped, so build_*_messages() output is passed
    # straight through — no role translation needed. JSON mode requires the
    # word "json" to appear in the prompt; both system prompts say
    # "Respond with ONLY a JSON object".
    if not settings.GROQ_API_KEY:
        raise AIServiceError("AI features are not configured — missing GROQ_API_KEY on the server.")

    client = groq.Groq(api_key=settings.GROQ_API_KEY, timeout=settings.AI_REQUEST_TIMEOUT_SECONDS, max_retries=0)
    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
    except groq.APITimeoutError as exc:
        # _MARKER "took too long" -> runner classifies ai_timeout
        raise AIServiceError("The AI took too long to respond. Please try again.") from exc
    except groq.RateLimitError as exc:
        # _MARKER "TooManyRequests"/"429" -> runner classifies ai_rate_limited.
        # Groq's own class name contains none of the runner's markers, so the
        # message is spelled out rather than derived from it.
        raise AIServiceError("The AI service returned an error: TooManyRequests (429) — quota or rate limit.") from exc
    except groq.APIConnectionError as exc:
        # _MARKER "Unavailable" -> runner treats as transient, retries once
        raise AIServiceError("The AI service returned an error: ServiceUnavailable (connection failed).") from exc
    except groq.APIStatusError as exc:
        if exc.status_code >= 500:
            raise AIServiceError(
                f"The AI service returned an error: ServiceUnavailable ({exc.status_code})."
            ) from exc
        raise AIServiceError(
            f"The AI service returned an error: {exc.__class__.__name__} ({exc.status_code})."
        ) from exc
    except groq.APIError as exc:
        raise AIServiceError(f"The AI service returned an error: {exc.__class__.__name__}.") from exc

    if not response.choices:
        raise AIServiceError("The AI returned an empty response. Please try again.")
    return _parse_json(response.choices[0].message.content)


def _chat_json_gemini(messages: list[dict]) -> dict:
    from google.api_core.exceptions import DeadlineExceeded, GoogleAPICallError

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

    model = _gemini_model(system_instruction)
    try:
        response = model.generate_content(
            contents,
            request_options={"timeout": settings.AI_REQUEST_TIMEOUT_SECONDS},
        )
    except DeadlineExceeded as exc:
        raise AIServiceError("The AI took too long to respond. Please try again.") from exc
    except GoogleAPICallError as exc:
        raise AIServiceError(f"The AI service returned an error: {exc.__class__.__name__}.") from exc

    return _parse_json(response.text)
