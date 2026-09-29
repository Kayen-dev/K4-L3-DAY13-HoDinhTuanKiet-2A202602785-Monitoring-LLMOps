from app.pii import scrub_text


def test_scrub_email() -> None:
    for email in ("student@vinuni.edu.vn", "Student.Name+lab@EXAMPLE.COM"):
        out = scrub_text(f"Email me at {email}")
        assert email not in out
        assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
        "84 (90) 123-4567",
        "028 1234 5678",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd() -> None:
    for cccd in ("001203012345", "001 203 012 345"):
        out = scrub_text(f"CCCD: {cccd}")
        assert cccd not in out
        assert "REDACTED_CCCD" in out


def test_scrub_credit_card() -> None:
    card_numbers = (
        "4111111111111111",
        "4111 1111 1111 1111",
        "4111-1111-1111-1111",
    )

    for card_number in card_numbers:
        out = scrub_text(f"Card: {card_number}")
        assert card_number not in out
        assert "REDACTED_CREDIT_CARD" in out


def test_does_not_scrub_numeric_runs_inside_opaque_ids() -> None:
    trace_id = "bd0841234567c8db0f775402b13e6f2"
    correlation_id = "req-a0841234567b"

    assert scrub_text(trace_id) == trace_id
    assert scrub_text(correlation_id) == correlation_id
