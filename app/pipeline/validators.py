import re

# Same character repeated 10+ times in a row ("aaaaaaaaaa", "!!!!!!!!!!!").
_REPEATED_CHAR_RE = re.compile(r"(.)\1{9,}", re.DOTALL)

# Same word repeated 5+ times in a row, case-insensitive ("spam spam spam spam spam").
_REPEATED_WORD_RE = re.compile(r"\b(\w+)\b(?:\s+\1\b){4,}", re.IGNORECASE)

# Text with no alphanumeric content at all (e.g. only punctuation/whitespace).
_NO_ALNUM_RE = re.compile(r"[^\W_]", re.UNICODE)


def validate_ticket(text: str, min_length: int, max_length: int) -> tuple[bool, str | None]:
    """Deterministic, regex-based ticket validation.

    Returns (is_valid, rejection_reason). rejection_reason is None when valid.
    """
    stripped = text.strip()

    if len(stripped) < min_length:
        return False, f"Ticket text too short (< {min_length} characters)"

    if len(text) > max_length:
        return False, f"Ticket text too long (> {max_length} characters)"

    if not _NO_ALNUM_RE.search(stripped):
        return False, "Ticket text contains no alphanumeric content"

    if _REPEATED_CHAR_RE.search(stripped):
        return False, "Ticket text appears repetitive (same character repeated excessively)"

    if _REPEATED_WORD_RE.search(stripped):
        return False, "Ticket text appears repetitive (same word repeated excessively)"

    return True, None
