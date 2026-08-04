"""
rbac/users.py

Phase 3: a hardcoded username -> role directory, purely for testing that
RBAC filtering works end to end. This is NOT how you'd handle auth in a
real deployment (passwords in plaintext, no hashing, no database) — but it
lets us prove the access-control logic works before adding that complexity.

Later, this file is the one thing you'd swap out for a real user database
(e.g. Azure AD / Entra ID, or a proper hashed-password table) without
touching any of the RBAC filtering logic itself.
"""

USERS = {
    "priya":  {"password": "priya123",  "role": "hr"},
    "raj":    {"password": "raj123",    "role": "finance"},
    "sam":    {"password": "sam123",    "role": "marketing"},
    "alex":   {"password": "alex123",   "role": "engineering"},
    "ceo":    {"password": "ceo123",    "role": "c-level"},
}


def authenticate(username: str, password: str):
    """Returns the user's role (str) if credentials are valid, else None."""
    user = USERS.get(username)
    if user and user["password"] == password:
        return user["role"]
    return None