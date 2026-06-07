"""
producer/news_producer.py
--------------------------
KafkaPulse — Producer Service (Real Data)

Fetches live headlines from News API and publishes them to
the Kafka `raw_text` topic.

Run:
    python news_producer.py

Requirements:
    pip install kafka-python requests python-dotenv
"""

import os
import json
import time
import uuid
import logging
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Load .env file
load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────

KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC     = "raw_text"

NEWS_API_KEY    = os.getenv("NEWS_API_KEY")
NEWS_QUERIES    = ["technology", "AI", "economy", "climate", "stocks"]
POLL_INTERVAL_S = 30    # News API free tier has rate limits, 30s is safe
PAGE_SIZE       = 10    # articles per query per poll

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PRODUCER] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Kafka ──────────────────────────────────────────────────────────────────────

def create_producer() -> KafkaProducer:
    """Connect to Kafka, retry up to 5 times."""
    for attempt in range(1, 6):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                retries=3,
                linger_ms=100,
            )
            log.info(f"Connected to Kafka at {KAFKA_BOOTSTRAP}")
            return producer
        except KafkaError as e:
            log.warning(f"Kafka not ready (attempt {attempt}/5): {e} — retrying in 5s")
            time.sleep(5)
    raise RuntimeError("Could not connect to Kafka after 5 attempts.")


# ── News API ───────────────────────────────────────────────────────────────────

def fetch_articles(query: str) -> list[dict]:
    """
    Fetch latest articles for a query keyword from News API.
    Returns a list of normalized article dicts.
    """
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q":        query,
                "apiKey":   NEWS_API_KEY,
                "pageSize": PAGE_SIZE,
                "language": "en",
                "sortBy":   "publishedAt",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        # Handle API-level errors (e.g. invalid key, rate limit)
        if data.get("status") != "ok":
            log.error(f"News API error: {data.get('message', 'Unknown error')}")
            return []

        articles = []
        for item in data.get("articles", []):
            # Combine title + description for richer sentiment analysis
            text = " ".join(filter(None, [
                item.get("title", ""),
                item.get("description", ""),
            ])).strip()

            # Skip articles with no text or removed content
            if not text or text == "[Removed]":
                continue

            articles.append({
                "id":        str(uuid.uuid4()),
                "text":      text,
                "url":       item.get("url", ""),
                "source":    item.get("source", {}).get("name", "news"),
                "query":     query,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        log.info(f"Fetched {len(articles)} articles for query='{query}'")
        return articles

    except requests.RequestException as e:
        log.error(f"News API request failed for query='{query}': {e}")
        return []


# ── Main loop ──────────────────────────────────────────────────────────────────

def run():
    # Validate API key before starting
    if not NEWS_API_KEY:
        raise RuntimeError(
            "NEWS_API_KEY not found. "
            "Add it to producer/.env as: NEWS_API_KEY=your_key_here"
        )

    producer  = create_producer()
    seen_urls = set()   # deduplicate within session

    log.info(f"Producer started. Topic='{KAFKA_TOPIC}', interval={POLL_INTERVAL_S}s")
    log.info(f"Queries: {NEWS_QUERIES}")

    try:
        while True:
            for query in NEWS_QUERIES:
                articles = fetch_articles(query)

                published = 0
                for article in articles:
                    dedup_key = article["url"] or article["id"]
                    if dedup_key in seen_urls:
                        continue
                    seen_urls.add(dedup_key)

                    producer.send(KAFKA_TOPIC, value=article) \
                        .add_callback(lambda m: log.debug(f"Delivered → partition={m.partition} offset={m.offset}")) \
                        .add_errback(lambda e: log.error(f"Delivery failed: {e}"))

                    published += 1

                log.info(f"Published {published} new messages (query='{query}')")

            producer.flush()
            log.info(f"Sleeping {POLL_INTERVAL_S}s...\n")
            time.sleep(POLL_INTERVAL_S)

    except KeyboardInterrupt:
        log.info("Shutting down...")
    finally:
        producer.flush()
        producer.close()
        log.info("Producer closed.")


if __name__ == "__main__":
    run()