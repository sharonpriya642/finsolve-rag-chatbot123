"""
rbac/filters.py

Turns a user's role into a Qdrant search filter that restricts retrieval to
only the departments that role is allowed to see. This is the actual
enforcement mechanism — the LLM never even sees chunks outside the allowed
departments, because Qdrant excludes them before generation happens.
"""

from qdrant_client.models import Filter, FieldCondition, MatchAny

from config import ROLE_ACCESS


def build_role_filter(role: str) -> Filter:
    """
    Returns a Qdrant Filter that only matches chunks whose `department`
    metadata is in this role's allowed list.

    langchain-qdrant stores our metadata nested under "metadata", so the
    payload field to filter on is "metadata.department".
    """
    allowed_departments = ROLE_ACCESS.get(role, [])

    return Filter(
        must=[
            FieldCondition(
                key="metadata.department",
                match=MatchAny(any=allowed_departments),
            )
        ]
    )