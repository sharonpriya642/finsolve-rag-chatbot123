"""
guardrails/scope.py

Uses the LLM itself (a very small, cheap prompt) to judge whether a
question is actually about company data, versus something unrelated
(general trivia, creative writing requests, coding help, etc).

This is intentionally a SEPARATE, tiny LLM call from the main answer
generation — it should be fast and cheap, since all it needs to output
is a single word.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from langchain_groq import ChatGroq
from config import GROQ_API_KEY

SCOPE_MODEL_NAME = "openai/gpt-oss-20b"  # smaller/cheaper model, good enough for classification

SCOPE_SYSTEM_PROMPT = """You are a strict classifier. Decide if the user's question is
something an INTERNAL COMPANY CHATBOT should answer using internal company documents
(finance, HR, marketing, engineering, general employee/company information).

Reply with EXACTLY one word, nothing else:
- "IN_SCOPE" if the question is plausibly about company data, policies, reports, or operations.
- "OUT_OF_SCOPE" if the question is unrelated (general trivia, creative writing, coding help,
  personal advice unrelated to the company, jokes, etc).
"""


def _get_scope_llm() -> ChatGroq:
    return ChatGroq(model=SCOPE_MODEL_NAME, groq_api_key=GROQ_API_KEY, temperature=0)


def is_in_scope(question: str) -> bool:
    """Returns True if the question is judged to be about company data."""
    llm = _get_scope_llm()
    messages = [
        ("system", SCOPE_SYSTEM_PROMPT),
        ("human", question),
    ]
    response = llm.invoke(messages)
    verdict = response.content.strip().upper()
    return "IN_SCOPE" in verdict