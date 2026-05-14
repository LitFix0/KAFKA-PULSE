"""
api/main.py
-----------
Step 4a of KafkaPulse — FastAPI Backend

Reads sentiment data from MongoDB and exposes it
as REST API endpoints for the React frontend.

Run:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient, DESCENDING
import os
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────

MONGO_URI        = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB         = "kafkapulse"
MONGO_COLLECTION = "sentiment_results"

# ── App setup ──────────────────────────────────────────────────────────────────

app = FastAPI(title="KafkaPulse API")

# Allow React (localhost:3000) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── MongoDB connection ─────────────────────────────────────────────────────────

client     = MongoClient(MONGO_URI)
collection = client[MONGO_DB][MONGO_COLLECTION]


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/api/recent")
def get_recent(limit: int = 20):
    """Return the most recent sentiment results."""
    docs = collection.find(
        {},
        {"_id": 0}   # exclude MongoDB internal _id field
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