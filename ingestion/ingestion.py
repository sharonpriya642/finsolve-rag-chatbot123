"""
ingestion/ingest.py

Reads every file under data/<department>/, splits it into chunks,
embeds each chunk with a local (lightweight) embedding model via fastembed,
and stores everything in Qdrant with a `department` metadata field on
every chunk. That metadata field is what makes RBAC filtering possible later.

Run this from the project root:
    python ingestion/ingestion.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME, DEPARTMENTS

# data/ lives one level up from this file (project_root/data)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_markdown_file(filepath: Path, department: str) -> list[Document]:
    """Each .md file becomes one Document (we'll chunk it later)."""
    text = filepath.read_text(encoding="utf-8")
    return [
        Document(
            page_content=text,
            metadata={"department": department, "source": filepath.name},
        )
    ]


def load_csv_file(filepath: Path, department: str) -> list[Document]:
    """Each CSV row becomes its own Document (e.g. one employee record per row)."""
    df = pd.read_csv(filepath)
    docs = []
    for i, row in df.iterrows():
        row_text = "\n".join(f"{col}: {row[col]}" for col in df.columns)
        docs.append(
            Document(
                page_content=row_text,
                metadata={"department": department, "source": filepath.name, "row": int(i)},
            )
        )
    return docs


def load_all_documents() -> list[Document]:
    all_docs = []
    for department in DEPARTMENTS:
        dept_folder = DATA_DIR / department
        if not dept_folder.exists():
            print(f"  [!] No folder found for '{department}', skipping.")
            continue

        count_before = len(all_docs)
        for filepath in dept_folder.iterdir():
            if filepath.suffix.lower() == ".md":
                all_docs.extend(load_markdown_file(filepath, department))
            elif filepath.suffix.lower() == ".csv":
                all_docs.extend(load_csv_file(filepath, department))
            else:
                print(f"  [!] Skipping unsupported file type: {filepath.name}")

        print(f"  Loaded {len(all_docs) - count_before} document(s) for department: {department}")
    return all_docs


def chunk_documents(docs: list[Document]) -> list[Document]:
    """Split long documents into smaller overlapping chunks for better retrieval."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    return splitter.split_documents(docs)


def main():
    print("Step 1/4 — Loading documents from data/ ...")
    raw_docs = load_all_documents()
    print(f"Total raw documents loaded: {len(raw_docs)}\n")

    print("Step 2/4 — Chunking documents ...")
    chunks = chunk_documents(raw_docs)
    print(f"Total chunks created: {len(chunks)}\n")

    print("Step 3/4 — Loading embedding model (fastembed, CPU-friendly) ...")
    embeddings = FastEmbedEmbeddings()

    print(f"Connecting to Qdrant at {QDRANT_URL} ...")
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    if client.collection_exists(COLLECTION_NAME):
        print(f"Collection '{COLLECTION_NAME}' already exists — recreating it fresh.")
        client.delete_collection(COLLECTION_NAME)

    sample_vector = embeddings.embed_query("test")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=len(sample_vector), distance=Distance.COSINE),
    )

    print("Step 4/4 — Embedding and uploading chunks to Qdrant ...")
    vectorstore = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )
    vectorstore.add_documents(chunks)

    print(f"\nDone! {len(chunks)} chunks stored in Qdrant collection '{COLLECTION_NAME}'.")
    print("Every chunk carries metadata: department (for RBAC filtering) + source (filename).")


if __name__ == "__main__":
    main()
