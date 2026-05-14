"""
consumer/sentiment_consumer.py
-------------------------------
Step 3 of KafkaPulse — Consumer + MongoDB Storage

Reads messages from Kafka `raw_text` topic,
runs VADER sentiment analysis,
and saves each result to MongoDB Atlas.

Run:
    python sentiment_consumer.py
"""

import os
import json
import logging
import certifi  
from datetime import datetime, timezone

from dotenv import load_dotenv
from kafka import KafkaConsumer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from pymongo import MongoClient

# Load .env file
load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────

KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC     = "raw_text"
GROUP_ID        = "sentiment-group"

MONGO_URI       = os.getenv("MONGO_URI")    # loaded from .env
MONGO_DB        = "kafkapulse"
MONGO_COLLECTION = "sentiment_results"

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CONSUMER] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Sentiment analysis ─────────────────────────────────────────────────────────

def analyze(text: str, analyzer: SentimentIntensityAnalyzer) -> dict:
    scores   = analyzer.polarity_scores(text)
    compound = scores["compound"]

    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"

    return {
        "sentiment": label,
        "score":     round(compound, 4),
    }


# ── MongoDB ────────────────────────────────────────────────────────────────────

def connect_mongo():
    """Connect to MongoDB Atlas and return the collection."""
    client     = MongoClient(MONGO_URI)
    collection = client[MONGO_DB][MONGO_COLLECTION]

    # Quick ping to verify connection
    client.admin.command("ping")
    log.info("Connected to MongoDB.")
    return collection


# ── Main ───────────────────────────────────────────────────────────────────────

def run():
    analyzer   = SentimentIntensityAnalyzer()
    collection = connect_mongo()

    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=GROUP_ID,
        auto_offset_reset="earliest",
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
    )

    log.info(f"Consumer started. Listening on topic='{KAFKA_TOPIC}'...")
    log.info("-" * 60)

    try:
        for message in consumer:
            data = message.value

            text   = data.get("text", "").strip()
            source = data.get("source", "unknown")
            query  = data.get("query", "")

            if not text:
                continue

            # Run sentiment analysis
            result = analyze(text, analyzer)

            # Build the document to save
            document = {
                "text":       text,
                "source":     source,
                "query":      query,
                "sentiment":  result["sentiment"],
                "score":      result["score"],
                "saved_at":   datetime.now(timezone.utc).isoformat(),
            }

            # Save to MongoDB
            collection.insert_one(document)

            # Print to terminal
            log.info(
                f"[{result['sentiment'].upper():8}] "
                f"score={result['score']:+.3f} | "
                f"saved to MongoDB ✓\n"
                f"           text: {text[:80]}"
            )

    except KeyboardInterrupt:
        log.info("Shutting down consumer...")
    finally:
        consumer.close()
        log.info("Consumer closed.")


if __name__ == "__main__":
    run()