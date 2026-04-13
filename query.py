"""
Query the RAG system.

Usage:
    # Interactive mode
    python query.py

    # Single question
    python query.py "What is the treatment protocol for German cockroaches?"
"""

import os
import sys

import chromadb
from anthropic import Anthropic
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

CHROMA_DIR = os.environ.get("CHROMA_DIR", "./chroma_db")
COLLECTION_NAME = "pest_docs"
EMBED_MODEL = "all-MiniLM-L6-v2"
CLAUDE_MODEL = "claude-sonnet-4-6"
TOP_K = 7

SYSTEM_PROMPT = """You are a knowledgeable assistant for Pest Management Systems, Inc.
Your job is to answer questions from technicians, office staff, and management using
the company's own procedures, SOPs, regulatory guidance, and operational documents.

Rules:
- Answer using ONLY information found in the provided context. Do not use outside knowledge.
- Provide thorough, complete answers. Include all relevant details, steps, requirements,
  warnings, and exceptions found in the source material — do not summarize away important content.
- If multiple sources cover the topic, synthesize their information into a single cohesive answer.
- If the context does not contain enough information to fully answer, say so clearly and state
  what was found and what was not found.
- Always cite which source document(s) your answer is drawn from at the end of your response.

Formatting rules (strictly follow these):
- Do NOT use markdown. No #, ##, ###, **, *, --, ---, or backticks.
- Use plain numbered lists (1. 2. 3.) for sequential steps or ordered items.
- Use plain bullet points with a dash and space (- ) for unordered items.
- Separate sections with a blank line.
- Write section labels as plain text followed by a colon on their own line, e.g. "Overview:" or "Required Steps:".
- Keep the writing clear and professional. Technicians need complete, actionable information."""


def embed_query(question: str, model: SentenceTransformer) -> list[float]:
    return model.encode([question])[0].tolist()


def retrieve(question: str, collection, embed_model: SentenceTransformer) -> tuple[list[str], list[str]]:
    embedding = embed_query(question, embed_model)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=TOP_K,
        include=["documents", "metadatas"],
    )
    docs = results["documents"][0]
    sources = [m["source"] for m in results["metadatas"][0]]
    return docs, sources


def generate_answer(question: str, docs: list[str], sources: list[str], anthropic_client: Anthropic) -> str:
    context_blocks = []
    for doc, src in zip(docs, sources):
        context_blocks.append(f"[Source: {src}]\n{doc}")
    context = "\n\n".join(context_blocks)

    user_message = f"""Context from company documents:

{context}

Question: {question}"""

    response = anthropic_client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def build_citations(docs: list[str], sources: list[str]) -> list[dict]:
    """Deduplicate by source, keeping the first (highest-similarity) snippet per source."""
    seen = {}
    for doc, src in zip(docs, sources):
        if src not in seen:
            seen[src] = doc
    return [{"source": src, "snippet": snippet} for src, snippet in seen.items()]


def run_query(
    question: str,
    collection,
    embed_model: SentenceTransformer,
    anthropic_client: Anthropic,
) -> tuple[str, list[dict]]:
    docs, sources = retrieve(question, collection, embed_model)
    answer = generate_answer(question, docs, sources, anthropic_client)
    citations = build_citations(docs, sources)
    return answer, citations


def main():
    embed_model = SentenceTransformer(EMBED_MODEL)
    anthropic_client = Anthropic()
    chroma = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = chroma.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    if collection.count() == 0:
        print("No documents ingested yet. Run 'python ingest.py' first.")
        sys.exit(1)

    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        answer, citations = run_query(question, collection, embed_model, anthropic_client)
        print(f"\nAnswer:\n{answer}")
        print("\nSources:")
        for c in citations:
            print(f"  - {c['source']}")
    else:
        print("Pest Management Systems — AI Knowledge Assistant")
        print("=" * 50)
        print("Type 'quit' to exit.\n")
        while True:
            try:
                question = input("Question: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not question:
                continue
            if question.lower() in ("quit", "exit", "q"):
                break
            answer, citations = run_query(question, collection, embed_model, anthropic_client)
            print(f"\nAnswer:\n{answer}")
            print("\nSources:")
            for c in citations:
                print(f"  - {c['source']}")
            print()


if __name__ == "__main__":
    main()
