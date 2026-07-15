from collections.abc import Callable
from typing import TypeVar

from app.pipeline.llm_client import LLMCallError

T = TypeVar("T")


def with_retries(fn: Callable[[], T], max_attempts: int) -> tuple[T | None, int, str | None]:
    """Call `fn` up to `max_attempts` times total, stopping on first success.

    Returns (result, attempts_used, error). `result` is None and `error` is
    set only if every attempt raised LLMCallError.
    """
    last_error: str | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(), attempt, None
        except LLMCallError as exc:
            last_error = str(exc)
    return None, max_attempts, last_error
