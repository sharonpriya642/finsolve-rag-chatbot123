"""
evals/ragas_eval.py

Quality evaluation using a real Ragas metric:
  - faithfulness: does the answer only claim things actually present in the
    retrieved context (a hallucination check)?

We use Groq (via ChatGroq) as the judge model, wrapped for Ragas. See the
NOTE below for why answer_relevancy is excluded for now.

Run from the project root with:
    python evals/ragas_eval.py
"""

import os

# Ragas's internal analytics/telemetry has a bug where it tries to log the
# embeddings object as a plain string and fails validation. We don't need
# usage tracking for a local eval run, so we disable it entirely.
os.environ["RAGAS_DO_NOT_TRACK"] = "true"

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_community.embeddings import FastEmbedEmbeddings

from app.rag_chain import run_pipeline_for_eval, get_llm

# NOTE: answer_relevancy is intentionally excluded here. It requires an
# embeddings model, and ragas 0.3.9's internal analytics code has a bug
# where it tries to read a plain string "model name" off the embeddings
# object but instead picks up the actual loaded fastembed model instance,
# causing a pydantic ValidationError before the metric can even run. This
# is a ragas/fastembed compatibility bug, not an issue with the RAG
# pipeline itself. faithfulness (below) does not use embeddings and is
# unaffected. To get answer_relevancy working, you'd need to either patch
# ragas's analytics code or switch to an embeddings provider ragas's
# telemetry handles correctly (e.g. OpenAIEmbeddings, if you have a key).

GOLDEN_SET = [
    {
        "question": "How many weeks of maternity leave are employees entitled to for the first two children?",
        "role": "hr",
        "ground_truth": "Employees are entitled to 26 weeks of maternity leave for the first two children.",
    },
    {
        "question": "How many days of casual leave do employees get per year?",
        "role": "marketing",
        "ground_truth": "Employees get 7 days of casual leave per year.",
    },
    {
        "question": "What percentage of basic salary does the House Rent Allowance (HRA) represent?",
        "role": "finance",
        "ground_truth": "HRA represents 40-50% of the basic salary.",
    },
    {
        "question": "What is the required advance notice period for submitting a leave request?",
        "role": "engineering",
        "ground_truth": "Leave requests must be submitted at least 3 days in advance, except emergencies.",
    },
]


def build_ragas_dataset() -> Dataset:
    questions, answers, contexts, ground_truths = [], [], [], []

    for item in GOLDEN_SET:
        print(f"Running pipeline for: {item['question']!r} (role={item['role']})")
        answer, sources, context_texts = run_pipeline_for_eval(item["question"], item["role"])

        questions.append(item["question"])
        answers.append(answer)
        contexts.append(context_texts if context_texts else [""])
        ground_truths.append(item["ground_truth"])

    return Dataset.from_dict(
        {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        }
    )


def main():
    print("Step 1/2 - Building evaluation dataset by running the real RAG pipeline...\n")
    dataset = build_ragas_dataset()

    print("\nStep 2/2 - Running Ragas evaluation (faithfulness)...")
    ragas_llm = LangchainLLMWrapper(get_llm())
    ragas_embeddings = LangchainEmbeddingsWrapper(FastEmbedEmbeddings())

    results = evaluate(
        dataset,
        metrics=[faithfulness],
        llm=ragas_llm,
        embeddings=ragas_embeddings,
    )

    print("\n=== Ragas Evaluation Results ===")
    print(results)

    df = results.to_pandas()
    out_path = Path(__file__).parent / "ragas_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\nDetailed per-question scores saved to: {out_path}")


if __name__ == "__main__":
    main()
