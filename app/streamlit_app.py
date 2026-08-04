"""
app/streamlit_app.py

Visual redesign pass: a "ledger" aesthetic fitting an internal financial-
services company assistant, instead of a generic chatbot skin. All RBAC,
guardrail, and chat logic is unchanged from before -- only presentation.

Run from the project root with:
    streamlit run app/streamlit_app.py
"""

import streamlit as st

from rag_chain import answer_question
from rbac.users import authenticate
from config import ROLE_ACCESS

st.set_page_config(page_title="FinSolve Assistant", page_icon="\U0001F4D2", layout="centered")

# ---------------------------------------------------------------------------
# Design tokens + global styles
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --ink: #12213A;
    --ink-soft: #1D3255;
    --paper: #FAF6EE;
    --paper-line: #E4DDCB;
    --emerald: #1F6F5C;
    --gold: #C9A227;
    --charcoal: #26313F;
    --muted: #6B7280;
}

/* App canvas */
[data-testid="stAppViewContainer"] {
    background-color: var(--paper);
}
[data-testid="stHeader"] {
    background-color: transparent;
}
.block-container {
    padding-top: 2rem;
    max-width: 760px;
}

/* Sidebar -- the "ledger spine" */
[data-testid="stSidebar"] {
    background-color: var(--ink);
    color: #EDE7D3;
}
[data-testid="stSidebar"] * {
    color: #EDE7D3 !important;
    font-family: 'Inter', sans-serif;
}
[data-testid="stSidebar"] h3 {
    font-family: 'Source Serif 4', serif !important;
    font-weight: 600;
    letter-spacing: 0.01em;
}

/* Role stamp badge */
.role-stamp {
    display: inline-block;
    border: 2px solid var(--gold);
    color: var(--gold) !important;
    border-radius: 50%;
    width: 64px;
    height: 64px;
    line-height: 60px;
    text-align: center;
    font-family: 'Source Serif 4', serif;
    font-weight: 700;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
    transform: rotate(-6deg);
    margin-bottom: 0.5rem;
    text-transform: uppercase;
}

.access-line {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem;
    color: #B9C3D4 !important;
    letter-spacing: 0.02em;
}

/* Header / wordmark */
.wordmark {
    font-family: 'Source Serif 4', serif;
    font-weight: 700;
    font-size: 2.1rem;
    color: var(--ink);
    letter-spacing: -0.01em;
    margin-bottom: 0;
}
.tagline {
    font-family: 'Inter', sans-serif;
    color: var(--muted);
    font-size: 0.92rem;
    margin-top: -0.3rem;
    margin-bottom: 1.6rem;
}
.tagline .rule {
    display: inline-block;
    width: 28px;
    border-top: 2px solid var(--emerald);
    margin-right: 8px;
    transform: translateY(-4px);
}

/* Chat turns rendered as ledger entries */
.turn {
    margin-bottom: 1.1rem;
}
.turn-user {
    text-align: right;
}
.bubble-user {
    display: inline-block;
    background-color: var(--ink);
    color: #F5F1E6;
    font-family: 'Inter', sans-serif;
    font-size: 0.95rem;
    padding: 0.65rem 1rem;
    border-radius: 10px 10px 2px 10px;
    max-width: 82%;
    text-align: left;
}
.bubble-assistant {
    background-color: #FFFFFF;
    border-left: 3px solid var(--emerald);
    font-family: 'Inter', sans-serif;
    font-size: 0.95rem;
    color: var(--charcoal);
    padding: 0.85rem 1.1rem;
    border-radius: 2px 10px 10px 10px;
    box-shadow: 0 1px 2px rgba(18, 33, 58, 0.06);
}
.sources-tag {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--emerald);
    background-color: #EAF2EF;
    border: 1px solid #CFE3DC;
    border-radius: 4px;
    padding: 2px 8px;
    margin-top: 0.5rem;
}

/* Login card */
.login-card {
    background-color: #FFFFFF;
    border: 1px solid var(--paper-line);
    border-radius: 6px;
    padding: 2rem 2rem 0.5rem 2rem;
    box-shadow: 0 2px 10px rgba(18, 33, 58, 0.05);
}

/* Chat input styling */
[data-testid="stChatInput"] textarea {
    font-family: 'Inter', sans-serif !important;
}

/* Buttons */
.stButton button, .stFormSubmitButton button {
    background-color: var(--emerald) !important;
    color: #FAF6EE !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
}
.stButton button:hover, .stFormSubmitButton button:hover {
    background-color: var(--ink-soft) !important;
}
</style>
"""


def inject_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def init_session_state():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "role" not in st.session_state:
        st.session_state.role = None
    if "username" not in st.session_state:
        st.session_state.username = None
    if "messages" not in st.session_state:
        st.session_state.messages = []


def show_login():
    st.markdown('<div class="wordmark">FinSolve</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="tagline"><span class="rule"></span>Internal company ledger &amp; knowledge assistant</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

        if submitted:
            role = authenticate(username, password)
            if role:
                st.session_state.logged_in = True
                st.session_state.role = role
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid username or password.")
    st.markdown("</div>", unsafe_allow_html=True)


def show_chat():
    role = st.session_state.role
    role_label = role.replace("-", " ").upper()
    allowed = ROLE_ACCESS.get(role, [])

    with st.sidebar:
        st.markdown(f'<div class="role-stamp">{role_label}</div>', unsafe_allow_html=True)
        st.markdown("### " + st.session_state.username)
        st.markdown('<div class="access-line">ACCESS &mdash; ' + ", ".join(allowed) + "</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Sign out"):
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.username = None
            st.session_state.messages = []
            st.rerun()

    st.markdown('<div class="wordmark">FinSolve</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="tagline"><span class="rule"></span>Ask about finance, HR, marketing, engineering &amp; company policy</div>',
        unsafe_allow_html=True,
    )

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="turn turn-user"><span class="bubble-user">{msg["content"]}</span></div>',
                unsafe_allow_html=True,
            )
        else:
            sources_html = ""
            if msg.get("sources"):
                tags = "".join(f'<span class="sources-tag">{s}</span> ' for s in msg["sources"])
                sources_html = f"<div style='margin-top:0.4rem'>{tags}</div>"
            st.markdown(
                f'<div class="turn"><div class="bubble-assistant">{msg["content"]}{sources_html}</div></div>',
                unsafe_allow_html=True,
            )

    question = st.chat_input("Ask a question about company data...")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.spinner("Consulting the ledger..."):
            answer, sources = answer_question(question, role)
        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "sources": sources}
        )
        st.rerun()


def main():
    inject_css()
    init_session_state()
    if not st.session_state.logged_in:
        show_login()
    else:
        show_chat()


if __name__ == "__main__":
    main()
