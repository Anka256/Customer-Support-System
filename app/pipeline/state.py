from typing import TypedDict


class StepLog(TypedDict):
    step_name: str
    duration_ms: int
    success: bool
    error_message: str | None


class TicketState(TypedDict, total=False):
    # Input
    raw_text: str

    # Terminal short-circuit path (validation failure or confirmed prompt injection).
    # These tickets are logged but never written to the `tickets` table.
    rejected: bool
    rejection_reason: str | None
    rejection_step: str | None

    # Pipeline outputs
    detected_language: str | None
    category: str | None
    priority: str | None
    summary: str | None
    draft_reply: str | None
    confidence_score: int | None
    status: str  # "auto_ready" | "manual_review"

    # Bookkeeping
    retry_count: int  # total retry attempts spent across all LLM-calling nodes
    pipeline_error: str | None  # set when a technical failure forces manual_review
    step_logs: list[StepLog]
    ticket_id: str | None


def new_state(raw_text: str) -> TicketState:
    return TicketState(
        raw_text=raw_text,
        rejected=False,
        rejection_reason=None,
        rejection_step=None,
        detected_language=None,
        category=None,
        priority=None,
        summary=None,
        draft_reply=None,
        confidence_score=None,
        status="manual_review",
        retry_count=0,
        pipeline_error=None,
        step_logs=[],
        ticket_id=None,
    )


def append_log(
    step_logs: list[StepLog] | None,
    step_name: str,
    duration_ms: int,
    success: bool,
    error_message: str | None = None,
) -> list[StepLog]:
    """Returns a new list with the entry appended — LangGraph state updates are
    treated as replacement values per key, not in-place mutations."""
    logs = list(step_logs or [])
    logs.append(
        StepLog(
            step_name=step_name,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
        )
    )
    return logs
