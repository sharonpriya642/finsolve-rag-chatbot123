"""
guardrails/pii.py

Regex-based PII detection. Deliberately rule-based (not LLM-based) because
PII patterns like emails, phone numbers, and ID formats are structurally
predictable — regex catches them reliably, instantly, and for free.

Used in two places:
  1. Input guardrail — block/flag a user's question if it contains PII
     (e.g. someone pasting in another employee's email to "look them up").
  2. Output guardrail — redact PII from the LLM's generated answer as a
     safety net, even though RBAC should already prevent most leaks at
     the retrieval stage.
"""

import re

# Each pattern: (label, compiled regex)
PII_PATTERNS = [
    ("email", re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")),
    ("phone", re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b")),
    ("employee_id", re.compile(r"\bFINEMP\d{3,6}\b", re.IGNORECASE)),
    ("dob", re.compile(r"\b\d{4}-\d{2}-\d{2}\b")),  # matches YYYY-MM-DD style dates
    ("ssn_like", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
]


def detect_pii(text: str) -> list[str]:
    """Returns a list of PII types found in the text, e.g. ['email', 'phone']."""
    found = []
    for label, pattern in PII_PATTERNS:
        if pattern.search(text):
            found.append(label)
    return found


def redact_pii(text: str) -> str:
    """Replaces any detected PII with a [REDACTED-<type>] placeholder."""
    redacted = text
    for label, pattern in PII_PATTERNS:
        redacted = pattern.sub(f"[REDACTED-{label.upper()}]", redacted)
    return redacted