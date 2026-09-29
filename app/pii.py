from __future__ import annotations

import hashlib
import re

PII_PATTERNS: dict[str, str] = {
    "email": r"(?i:\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}\b)",
    # Match longer numeric identifiers before phone numbers so they are not
    # partially classified when separators are present.
    "credit_card": r"(?<![A-Za-z0-9])(?:\d[ -]?){15}\d(?![ -]?\d|[A-Za-z])",
    "cccd": r"(?<![A-Za-z0-9])\d{3}[ .-]?\d{3}[ .-]?\d{3}[ .-]?\d{3}(?![ .-]?\d|[A-Za-z])",
    # Nine digits after 0/+84 covers mobile numbers; an optional tenth digit
    # also handles Vietnamese landlines.
    "phone_vn": r"(?<![A-Za-z0-9])(?:\+?84|0)(?:[ .()-]*\d){9,10}(?![ .()-]*\d|[A-Za-z])",
}


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe)
    return safe


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
