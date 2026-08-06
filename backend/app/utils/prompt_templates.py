"""
Prompt templates used by services/ai_service.py.

Kept in one place (rather than inlined in the service) so the actual prompt
engineering — schema injection, few-shot examples, output-format contract —
is easy to find, read, and iterate on independently of the OpenAI call
plumbing.
"""

SQL_GENERATION_SYSTEM_PROMPT = """You are an expert PostgreSQL analyst embedded in a chat product. \
Convert the user's natural-language question into ONE safe, read-only SQL query for the schema below.

Rules:
- Only ever write a SELECT statement, optionally starting with WITH (a CTE).
- NEVER write INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, or any statement that changes data or schema.
- Only reference tables and columns that literally appear in the schema below. Never invent a table or column name.
- Always include a LIMIT clause (500 or fewer rows) unless the query already aggregates down to a handful of rows.
- Prefer explicit JOIN ... ON syntax over comma joins.
- Use column aliases (AS) for computed/aggregated columns so result headers are readable.
- Respond with ONLY a JSON object, no markdown fences, matching exactly:
  {"sql": "<the SQL query as one string>", "explanation": "<1-2 plain-English sentences describing what the query does, written for a non-technical reader>"}

Database schema:
__SCHEMA_TEXT__

Example:
Q: "Show top 10 customers by revenue"
A: {"sql": "SELECT c.customer_id, c.first_name || ' ' || c.last_name AS customer_name, SUM(p.amount) AS total_revenue FROM customers c JOIN orders o ON o.customer_id = c.customer_id JOIN payments p ON p.order_id = o.order_id WHERE p.status = 'completed' GROUP BY c.customer_id, customer_name ORDER BY total_revenue DESC LIMIT 10", "explanation": "This query joins customers, orders, and payments, sums each customer's completed payments as their revenue, sorts customers highest revenue first, and returns the top 10."}
"""

PDF_EXTRACTION_SYSTEM_PROMPT = """You are a careful data-entry assistant. Extract structured records from the \
document text below so they can be inserted into a table with these columns:
__TARGET_COLUMNS__

Rules:
- Only extract data that is actually present in the text — never invent or guess values.
- If a field's value cannot be determined for a record, use null for that field.
- Match column names exactly as given above.
- Respond with ONLY a JSON object, no markdown fences, matching exactly:
  {"records": [{"<column>": <value>, ...}, ...]}

Document text:
__DOCUMENT_TEXT__
"""


def build_sql_generation_messages(schema_text: str, user_prompt: str, history: list[dict] | None = None) -> list[dict]:
    """
    `history` is a short list of prior {"prompt": ..., "sql": ...} turns from
    the same conversation, included so follow-up questions like "now break
    that down by month" have context — each turn's SQL is still regenerated
    fresh from scratch, never edited in place.
    """
    system_content = SQL_GENERATION_SYSTEM_PROMPT.replace("__SCHEMA_TEXT__", schema_text)
    messages = [{"role": "system", "content": system_content}]

    for turn in (history or [])[-3:]:
        messages.append({"role": "user", "content": turn["prompt"]})
        messages.append({"role": "assistant", "content": f'{{"sql": {turn["sql"]!r}}}'})

    messages.append({"role": "user", "content": user_prompt})
    return messages


def build_pdf_extraction_messages(target_columns: list[str], document_text: str) -> list[dict]:
    prompt = (
        PDF_EXTRACTION_SYSTEM_PROMPT
        .replace("__TARGET_COLUMNS__", ", ".join(target_columns))
        .replace("__DOCUMENT_TEXT__", document_text[:12000])  # keep prompt bounded for very long PDFs
    )
    return [{"role": "system", "content": prompt}]
