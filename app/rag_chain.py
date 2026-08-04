"""
app/rag_chain.py

Phase 6 update: internal logic refactored into _run_pipeline() so both the
normal chatbot (answer_question) and the eval suite (run_pipeline_for_eval)
share the exact same retrieval + generation + guardrail code path. This
matters for evals — you want to test the REAL pipeline, not a copy of it.

Run this directly for a command-line login + chat test:
    python app/rag_chain.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_groq import ChatGroq
from qdrant_client import QdrantClient

from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME, GROQ_API_KEY, ROLE_ACCESS
from rbac.users import authenticate
from rbac.filters import build_role_filter
from guardrails.pii import detect_pii, redact_pii
from guardrails.scope import is_in_scope

LLM_MODEL_NAME = "openai/gpt-oss-120b"

SYSTEM_PROMPT_TEMPLATE = """You are the FinSolve Assistant, an internal company chatbot.

Answer the user's question using ONLY the context below, taken from internal
company documents. If the context does not contain enough information to
answer confidently, say so plainly instead of guessing or making anything up.

Keep answers concise and professional. When useful, mention which document
the information came from.

Context:
{context}
"""


def get_vectorstore() -> QdrantVectorStore:
    embeddings = FastEmbedEmbeddings()
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )


def get_llm() -> ChatGroq:
    return ChatGroq(model=LLM_MODEL_NAME, groq_api_key=GROQ_API_KEY, temperature=0)


def run_input_guardrails(question: str):
    pii_found = detect_pii(question)
    if pii_found:
        return True, (
            f"Your question appears to contain personal data ({', '.join(pii_found)}). "
            "Please rephrase your question without including personal identifiers."
        )

    if not is_in_scope(question):
        return True, (
            "I'm the FinSolve internal assistant and can only help with questions "
            "about company data — finance, HR, marketing, engineering, or general "
            "company information. Could you rephrase your question along those lines?"
        )

    return False, None


def run_output_guardrails(answer: str) -> str:
    return redact_pii(answer)


def _run_pipeline(question: str, role: str, k: int = 4):
    """
    The real pipeline, shared by both the chatbot and the eval suite.
    Returns: (answer_text, sources, context_texts)
    context_texts is the list of raw retrieved chunk contents — needed by
    Ragas to score faithfulness/groundedness. Empty list if guardrails
    blocked the question before retrieval happened.
    """
    blocked, block_message = run_input_guardrails(question)
    if blocked:
        return block_message, [], []

    vectorstore = get_vectorstore()
    role_filter = build_role_filter(role)

    retriever = vectorstore.as_retriever(search_kwargs={"k": k, "filter": role_filter})
    docs = retriever.invoke(question)

    if not docs:
        return (
            "I couldn't find any relevant information you're authorized to "
            "access for that question.",
            [],
            [],
        )

    context_texts = [d.page_content for d in docs]
    context = "\n\n---\n\n".join(
        f"[Source: {d.metadata.get('source')}]\n{d.page_content}" for d in docs
    )

    llm = get_llm()
    messages = [
        ("system", SYSTEM_PROMPT_TEMPLATE.format(context=context)),
        ("human", question),
    ]
    response = llm.invoke(messages)

    safe_answer = run_output_guardrails(response.content)
    sources = sorted({d.metadata.get("source") for d in docs})
    return safe_answer, sources, context_texts


def answer_question(question: str, role: str, k: int = 4):
    """Public chatbot interface: returns (answer_text, sources)."""
    answer, sources, _ = _run_pipeline(question, role, k)
    return answer, sources


def run_pipeline_for_eval(question: str, role: str, k: int = 4):
    """Eval interface: returns (answer_text, sources, context_texts)."""
    return _run_pipeline(question, role, k)


def login() -> str:
    print("FinSolve Assistant — please log in")
    while True:
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        role = authenticate(username, password)
        if role:
            print(f"\nLogin successful. Role: {role}")
            print(f"Allowed departments: {', '.join(ROLE_ACCESS.get(role, []))}\n")
            return role
        print("Invalid username or password. Try again.\n")


def main():
    role = login()
    print("Type 'exit' to quit.\n")
    while True:
        question = input("You: ").strip()
        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue

        answer, sources = answer_question(question, role)
        print(f"\nBot: {answer}")
        if sources:
            print(f"Sources: {', '.join(sources)}")
        print()


if __name__ == "__main__":
    main()
