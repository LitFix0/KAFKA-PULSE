"""
api/main.py
-----------
KafkaPulse — FastAPI Backend (with RAG Chat)

Reads sentiment data from MongoDB and exposes it
as REST API endpoints for the React frontend.

Also provides /api/chat — a RAG endpoint that retrieves
relevant articles from ChromaDB and answers questions
using Groq's LLM API.

Run:
    uvicorn main:app --reload --port 8000
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient, DESCENDING
from dotenv import load_dotenv

import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────

MONGO_URI        = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB         = "kafkapulse"
MONGO_COLLECTION = "sentiment_results"

GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
GROQ_MODEL      = "llama-3.1-8b-instant"

CHROMA_PATH       = "../embedding_consumer/chroma_db"
CHROMA_COLLECTION = "articles"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ── App setup ──────────────────────────────────────────────────────────────────

app = FastAPI(title="KafkaPulse API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── MongoDB connection ─────────────────────────────────────────────────────────

mongo_client = MongoClient(MONGO_URI)
collection   = mongo_client[MONGO_DB][MONGO_COLLECTION]

# ── ChromaDB + Embedding model + Groq ──────────────────────────────────────────

chroma_client     = chromadb.PersistentClient(path=CHROMA_PATH)
chroma_collection = chroma_client.get_or_create_collection(name=CHROMA_COLLECTION)

embedding_model = SentenceTransformer(EMBEDDING_MODEL)

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# ── Request/Response models ────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str


# ── Existing Routes ─────────────────────────────────────────────────────────────

@app.get("/api/recent")
def get_recent(limit: int = 20):
    """Return the most recent sentiment results."""
    docs = collection.find(
        {},
        {"_id": 0}
    ).sort("saved_at", DESCENDING).limit(limit)

    return list(docs)


@app.get("/api/stats")
def get_stats():
    """Return counts of positive, negative, neutral."""
    counts = {"positive": 0, "negative": 0, "neutral": 0}

    pipeline = [
        {"$group": {"_id": "$sentiment", "count": {"$sum": 1}}}
    ]

    for doc in collection.aggregate(pipeline):
        label = doc["_id"]
        if label in counts:
            counts[label] = doc["count"]

    total = sum(counts.values())

    return {
        "total":    total,
        "positive": counts["positive"],
        "negative": counts["negative"],
        "neutral":  counts["neutral"],
    }


@app.get("/api/timeline")
def get_timeline(limit: int = 50):
    """Return recent results for time-series chart."""
    docs = collection.find(
        {},
        {"_id": 0, "sentiment": 1, "score": 1, "saved_at": 1, "text": 1}
    ).sort("saved_at", DESCENDING).limit(limit)

    return list(docs)


# ── RAG Chat Route ───────────────────────────────────────────────────────────────

@app.post("/api/chat")
def chat(request: ChatRequest):
    """
    RAG endpoint:
    1. Embed the user's question
    2. Retrieve top-K relevant articles from ChromaDB
    3. Build a context-aware prompt
    4. Send to Groq LLM and return the answer
    """
    if not groq_client:
        return {"answer": "GROQ_API_KEY not configured. Add it to api/.env", "sources": []}

    question = request.question.strip()
    if not question:
        return {"answer": "Please ask a question.", "sources": []}

    # 1. Embed the question
    query_embedding = embedding_model.encode(question).tolist()

    # 2. Retrieve top 5 relevant articles
    results = chroma_collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    if not documents:
        return {"answer": "No relevant articles found in the database yet.", "sources": []}

    # 3. Build context from retrieved articles
    context_parts = []
    sources = []
    for doc, meta in zip(documents, metadatas):
        context_parts.append(f"- {doc} (Source: {meta.get('source', 'unknown')}, Topic: {meta.get('query', 'unknown')})")
        sources.append({
            "text":   doc[:150],
            "source": meta.get("source", "unknown"),
            "query":  meta.get("query", "unknown"),
            "url":    meta.get("url", ""),
        })

    context = "\n".join(context_parts)

    prompt = f"""You are a news analyst assistant. Answer the user's question based ONLY on the following news articles. Be concise and cite which articles support your answer.

ARTICLES:
{context}

QUESTION: {question}

ANSWER:"""

    # 4. Call Groq LLM
    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful news analyst assistant. Be concise and factual."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        answer = completion.choices[0].message.content
    except Exception as e:
        answer = f"Error calling Groq API: {e}"

    return {"answer": answer, "sources": sources}