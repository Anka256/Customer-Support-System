from app.pipeline.validators import validate_ticket


def test_valid_ticket_passes():
    is_valid, reason = validate_ticket(
        "My internet has been down since yesterday, can someone help?", 3, 10_000
    )
    assert is_valid
    assert reason is None


def test_too_short_rejected():
    is_valid, reason = validate_ticket("hi", 3, 10_000)
    assert not is_valid
    assert "short" in reason


def test_too_long_rejected():
    is_valid, reason = validate_ticket("a" * 10, 3, 5)
    assert not is_valid
    assert "long" in reason


def test_repeated_character_rejected():
    is_valid, reason = validate_ticket("aaaaaaaaaaaaaaaaaaaa", 3, 10_000)
    assert not is_valid
    assert "repetitive" in reason


def test_repeated_word_rejected():
    is_valid, reason = validate_ticket("spam spam spam spam spam spam", 3, 10_000)
    assert not is_valid
    assert "repetitive" in reason


def test_no_alphanumeric_content_rejected():
    is_valid, reason = validate_ticket("!!! ??? ...", 3, 10_000)
    assert not is_valid
