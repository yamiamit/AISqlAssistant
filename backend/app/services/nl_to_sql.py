"""
The natural-language -> SQL -> validate -> execute pipeline, as one callable.

This used to live inline inside api/routes/chat.py. It was pulled out so the
exact same code path can be driven by something that isn't an HTTP request --
specifically the offline eval harness in backend/evals/, which needs to score
the pipeline without creating conversations, messages, or a DB session.

The route stays responsible for everything ORM-shaped (ownership checks,
conversation bookkeeping, persisting the turn); this module is responsible for
the pipeline itself and for turning a failure at any stage into a friendly
message plus a machine-readable `failure_stage`, rather than raising.
"""
from dataclasses import dataclass, field

from app.services.ai_service import AIServiceError, generate_sql
from app.services.schema_introspector import discover_schema, schema_to_prompt_text
from app.services.sql_executor import QueryExecutionError, execute_query
from app.services.sql_validator import SqlValidationError, validate_and_prepare
from app.utils.chart_suggester import suggest_chart_type

# failure_stage values. The API ignores these (it only shows error_message);
# the eval harness uses them to tell "the validator refused it" apart from
# "Postgres refused it", which are very different kinds of model mistake.
STAGE_SCHEMA = "schema"
STAGE_AI = "ai"
STAGE_VALIDATION = "validation"
STAGE_EXECUTION = "execution"
STAGE_UNEXPECTED = "unexpected"


@dataclass
class PipelineResult:
    """
    One pass through the pipeline. On success `error_message` is None; on
    failure the result carries whatever was produced before the failure --
    notably `generated_sql` survives a validation rejection, so callers can
    show (or score) the SQL that got refused.
    """

    generated_sql: str | None = None
    explanation: str | None = None
    result_columns: list[str] | None = None
    result_rows: list[dict] | None = None
    row_count: int | None = None
    execution_time_ms: float | None = None
    chart_type: str | None = None
    error_message: str | None = None
    failure_stage: str | None = None
    schema_text: str = field(default="", repr=False)

    @property
    def ok(self) -> bool:
        return self.error_message is None


def run_nl_to_sql(
    *,
    connection_url: str,
    prompt: str,
    cached_schema: dict | None = None,
    history: list[dict] | None = None,
    row_limit: int = 500,
    statement_timeout_ms: int = 10_000,
) -> PipelineResult:
    """
    Runs one question end to end. Never raises for an expected failure --
    schema/AI/validation/execution problems all come back on the result with
    a user-facing `error_message` and a `failure_stage`.

    `cached_schema` mirrors DBConnection.cached_schema: pass it to skip
    re-introspecting the target database on every call.
    """
    outcome = PipelineResult()

    try:
        try:
            schema = cached_schema or discover_schema(connection_url)
        except Exception as exc:
            raise QueryExecutionError(
                "Could not reach the connected database to read its schema — it may be offline."
            ) from exc
        if not schema.get("tables"):
            # Reachable since introspection became privilege-filtered: a role
            # that can connect but was granted SELECT on nothing. Generating
            # against an empty schema would hand the model no tables and produce
            # a confident hallucination, so stop here with the real reason.
            raise QueryExecutionError(
                "This connection's role can't read any tables. Check its SELECT grants, "
                "then refresh the schema."
            )

        outcome.schema_text = schema_to_prompt_text(schema)

        try:
            ai_result = generate_sql(outcome.schema_text, prompt, history)
        except AIServiceError as exc:
            outcome.error_message = str(exc)
            outcome.failure_stage = STAGE_AI
            return outcome

        outcome.generated_sql = ai_result["sql"]
        outcome.explanation = ai_result["explanation"]

        try:
            safe_sql = validate_and_prepare(ai_result["sql"], row_limit)
        except SqlValidationError as exc:
            outcome.error_message = str(exc)
            outcome.failure_stage = STAGE_VALIDATION
            return outcome

        outcome.generated_sql = safe_sql  # reflect any auto-appended LIMIT

        result = execute_query(connection_url, safe_sql, statement_timeout_ms)
        outcome.result_columns = result.columns
        outcome.result_rows = result.rows
        outcome.row_count = result.row_count
        outcome.execution_time_ms = result.execution_time_ms
        outcome.chart_type = suggest_chart_type(result.columns, result.rows)

    except QueryExecutionError as exc:
        outcome.error_message = str(exc)
        # A schema read that failed never got as far as producing SQL; that
        # distinction matters when scoring, so infer the stage from progress.
        outcome.failure_stage = STAGE_EXECUTION if outcome.generated_sql else STAGE_SCHEMA
    except Exception as exc:  # noqa: BLE001 - last-resort friendly fallback for anything unexpected
        outcome.error_message = f"Something went wrong while processing your request: {exc.__class__.__name__}."
        outcome.failure_stage = STAGE_UNEXPECTED

    return outcome
