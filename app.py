"""
FastAPI server for the Pest Management RAG system.

Run with:
    uvicorn app:app --reload --port 8000

Then open http://localhost:8000 in your browser.
"""

from contextlib import asynccontextmanager

import chromadb
from anthropic import Anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from transformers import logging as hf_logging
hf_logging.set_verbosity_error()

from query import CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL, run_query

load_dotenv()

clients: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    clients["embed"] = SentenceTransformer(EMBED_MODEL)
    clients["anthropic"] = Anthropic()
    chroma = chromadb.PersistentClient(path=CHROMA_DIR)
    clients["collection"] = chroma.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    yield
    clients.clear()


app = FastAPI(lifespan=lifespan)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    question: str


class Citation(BaseModel):
    source: str
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    collection = clients["collection"]
    if collection.count() == 0:
        raise HTTPException(
            status_code=503,
            detail="No documents ingested yet. Run 'python ingest.py' first.",
        )

    answer, citations = run_query(
        req.question,
        collection,
        clients["embed"],
        clients["anthropic"],
    )
    return ChatResponse(
        answer=answer,
        citations=[Citation(source=c["source"], snippet=c["snippet"]) for c in citations],
    )


# ---------------------------------------------------------------------------
# Serve frontend (must come after API routes)
# ---------------------------------------------------------------------------

app.mount("/", StaticFiles(directory="static", html=True), name="static")
