"""
embedding_consumer/embedding_consumer.py
------------------------------------------
KafkaPulse — Embedding Consumer (RAG Layer)

Reads articles from Kafka `raw_text` topic,
generates vector embeddings using SentenceTransformers,
and stores them in ChromaDB for semantic search.

This enables the /api/chat endpoint to retrieve
relevant articles for RAG-based question answering.

Run:
    python embedding_consumer.py
"""

import json
import logging
from datetime import datetime, timezone

from kafka import KafkaConsumer
from sentence_transformers import SentenceTransformer
import chromadb

# ── Config ─────────────────────────────────────────────────────────────────────

KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC     = "raw_text"
GROUP_ID        = "embedding-group"   # separate group — gets all messages independently

CHROMA_PATH       = "./chroma_db"
CHROMA_COLLECTION = "articles"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # small, fast, 384-dim embeddings

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [EMBEDDING] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── ChromaDB setup ─────────────────────────────────────────────────────────────

def connect_chroma():
    """Create persistent ChromaDB client and return the collection."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"}   # cosine similarity for semantic search
    )
    log.info(f"Connected to ChromaDB at '{CHROMA_PATH}', collection='{CHROMA_COLLECTION}'")
    return collection


# ── Main loop ──────────────────────────────────────────────────────────────────

def run():
    log.info("Loading embedding model (this may take a moment on first run)...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    log.info(f"Model '{EMBEDDING_MODEL}' loaded.")

    collection = connect_chroma()

    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=GROUP_ID,
        auto_offset_reset="earliest",
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
    )

    log.info(f"Embedding consumer started. Listening on topic='{KAFKA_TOPIC}'...")
    log.info("-" * 60)

    processed = 0

    try:
        for message in consumer:
            data = message.value

            text     = data.get("text", "").strip()
            article_id = data.get("id", "")
            source   = data.get("source", "unknown")
            query    = data.get("query", "")
            url      = data.get("url", "")
            timestamp = data.get("timestamp", datetime.now(timezone.utc).isoformat())

            if not text or not article_id:
                continue

            # Generate embedding vector for the article text
            embedding = model.encode(text).tolist()

            # Store in ChromaDB with metadata for filtering later
            collection.upsert(
                ids=[article_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[{
                    "source":    source,
                    "query":     query,
                    "url":       url,
                    "timestamp": timestamp,
                }]
            )

            processed += 1
            log.info(f"[{processed}] Embedded & stored: '{text[:60]}...' (source={source}, query={query})")

    except KeyboardInterrupt:
        log.info("Shutting down embedding consumer...")
    finally:
        consumer.close()
        log.info(f"Embedding consumer closed. Total embedded: {processed}")


if __name__ == "__main__":
    run()