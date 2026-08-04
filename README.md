# FinSolve Assistant — RAG Chatbot with RBAC, Guardrails & Evaluation

An internal company chatbot that answers questions from private company documents (finance, HR, marketing, engineering, and general policy), while enforcing **role-based access control**, **PII/scope guardrails**, and backed by an **automated evaluation suite**.

Live demo:https://finsolve-rag-chatbot123-noutpszd7btguh5q4agv3p.streamlit.app/

---

## Features

- **Retrieval-Augmented Generation** — answers are grounded in real company documents, not the model's general knowledge
- **Role-Based Access Control (RBAC)** — enforced at the vector database query level, not just prompted. A user's role determines which departments' documents can even be retrieved
- **Guardrails**
  - Input: blocks questions containing PII (emails, phone numbers, employee IDs, etc.) before retrieval; detects and redirects out-of-scope questions
  - Output: redacts any PII-shaped text that makes it into a generated answer, as a safety net
- **Evaluation suite**
  - Deterministic `pytest` regression tests covering RBAC enforcement and both guardrails
  - Ragas-based `faithfulness` scoring (hallucination check) using an LLM judge
- **Custom UI** — a distinct "ledger" visual theme, built in Streamlit
- **Deployed** — Streamlit Community Cloud (app) + Qdrant Cloud (vector store)

---

## Architecture

```
User question
    |
    v
Streamlit UI (login, session, role attached)
    |
    v
Input guardrails -- PII check -- out-of-scope check
    |
    v
Retriever (Qdrant) -- filtered by role -> allowed departments only
    |
    v
LLM (GPT-OSS-120B via Groq) -- answers using only retrieved context
    |
    v
Output guardrails -- PII redaction
    |
    v
Response + source citations shown to user
```

Every document chunk is tagged with a `department` field in its metadata at ingestion time. RBAC works by turning a user's role into a Qdrant filter (`rbac/filters.py`) that restricts search results to only the departments that role is allowed to see — enforced by the database, not by asking the model to behave.

---

## Tech stack

| Layer | Choice |
|---|---|
| LLM | GPT-OSS-120B via Groq |
| Embeddings | fastembed (local, CPU-friendly) |
| Vector store | Qdrant (Qdrant Cloud in production) |
| Framework | LangChain |
| Frontend | Streamlit |
| Evaluation | pytest + Ragas |
| Deployment | Streamlit Community Cloud |

---

## Project structure

```
RAG/
├── app/
│   ├── streamlit_app.py     # Web UI (login, chat, sidebar)
│   └── rag_chain.py         # Core pipeline: guardrails -> retrieval -> generation
├── rbac/
│   ├── users.py             # Demo username/role directory
│   └── filters.py           # Builds the Qdrant role-based filter
├── guardrails/
│   ├── pii.py                # Regex-based PII detection/redaction
│   └── scope.py               # LLM-based out-of-scope classifier
├── ingestion/
│   └── ingestion.py          # Chunks + embeds + uploads documents to Qdrant
├── evals/
│   ├── test_rbac_guardrails.py  # pytest suite
│   └── ragas_eval.py             # Ragas faithfulness evaluation
├── data/                      # Sample company documents, one folder per department
├── config.py                  # Settings + role-to-department access map
├── requirements.txt
└── runtime.txt                 # Pins Python version for deployment
```

---

## Access control model

| Role | Can access |
|---|---|
| finance | finance, general |
| hr | hr, general |
| marketing | marketing, general |
| engineering | engineering, general |
| c-level | everything |

Demo credentials (hardcoded in `rbac/users.py` — for demonstration only, not a production auth system):

| Username | Password | Role |
|---|---|---|
| priya | priya123 | hr |
| raj | raj123 | finance |
| sam | sam123 | marketing |
| alex | alex123 | engineering |
| ceo | ceo123 | c-level |

---

## Running locally

1. Clone the repo and create a virtual environment (Python 3.11 recommended):
   ```
   python -m venv venv
   venv\Scripts\activate      # Windows
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the project root:
   ```
   GROQ_API_KEY=your_groq_key
   QDRANT_URL=http://localhost:6333
   QDRANT_API_KEY=          # leave blank for local Qdrant, set it for Qdrant Cloud
   ```

3. Start Qdrant (Docker):
   ```
   docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage qdrant/qdrant
   ```

4. Ingest the sample data:
   ```
   python ingestion/ingestion.py
   ```

5. Run the app:
   ```
   streamlit run app/streamlit_app.py
   ```

---

## Running the evaluation suite

```
pytest evals/test_rbac_guardrails.py -v
```

```
python evals/ragas_eval.py
```

**Note:** `ragas`'s dependency chain (specifically `scikit-network`) does not ship precompiled wheels for very new Python versions, and current `ragas` releases have a compatibility bug with `fastembed`'s embedding wrapper that breaks the `answer_relevancy` metric specifically. For this reason the eval suite runs `faithfulness` only; see the comment in `evals/ragas_eval.py` for details and a path to re-enabling `answer_relevancy` with a different embeddings provider.

---

## Known limitations

- Authentication is a hardcoded demo directory, not a real identity provider
- `answer_relevancy` is currently disabled in the Ragas eval (see above)
- Sample data (`data/`) is synthetic, generated for demonstration purposes, not real company or personal data

---

## Roadmap / not yet implemented

- CI pipeline to auto-run the eval suite on every push
- LangSmith or equivalent request tracing/monitoring
- Token cost tracking and alerting
