"""
producer/news_producer.py
--------------------------
Step 1 of KafkaPulse — Producer Service

Fetches headlines from News API and publishes them to
the Kafka `raw_text` topic.

Run:
    python news_producer.py

Requirements:
    pip install kafka-python requests pyyaml
"""

import json
import time
import uuid
import logging
from datetime import datetime, timezone

import requests
from kafka import KafkaProducer
from kafka.errors import KafkaError

# ── Config ─────────────────────────────────────────────────────────────────────

KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC     = "raw_text"

NEWS_API_KEY     = "YOUR_NEWS_API_KEY_HERE"   # https://newsapi.org (free)
NEWS_QUERIES     = ["technology", "AI", "economy"]
POLL_INTERVAL_S  = 10     # seconds between fetches
PAGE_SIZE        = 10     # articles per query per poll

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PRODUCER] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Kafka ──────────────────────────────────────────────────────────────────────

def create_producer() -> KafkaProducer:
    """
    Connect to Kafka and return a producer.
    Retries up to 5 times if Kafka isn't ready yet.
    """
    for attempt in range(1, 6):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",       # wait for broker acknowledgment
                retries=3,
                linger_ms=100,    # batch messages for 100ms before sending
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
    Fetch top headlines for a query keyword from News API.
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

        articles = []
        for item in resp.json().get("articles", []):
            # Combine title + description for richer text
            text = " ".join(filter(None, [
                item.get("title", ""),
                item.get("description", ""),
            ])).strip()

            if not text:
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
        log.error(f"News API error for query='{query}': {e}")
        return []


# ── Simulation mode (no API key needed for testing) ───────────────────────────

_FAKE_HEADLINES = [
    "Tech stocks surge as AI boom continues to drive market optimism",
    "Climate scientists warn of accelerating ice melt in Arctic regions",
    "Federal Reserve signals possible rate cuts amid slowing inflation",
    "Startup raises $200M to build next-generation battery technology",
    "Global chip shortage eases as semiconductor production ramps up",
    "Breakthrough cancer treatment shows promising results in trials",
    "Electric vehicle sales fall short of manufacturer expectations",
    "Geopolitical tensions rise over disputed trade routes in Asia",
    "AI regulation debate intensifies as governments struggle to keep pace",
    "Renewable energy surpasses coal in global electricity generation",
]

def simulate_articles(query: str) -> list[dict]:
    """Return fake articles — used when NEWS_API_KEY is not set."""
    import random
    return [
        {
            "id":        str(uuid.uuid4()),
            "text":      h,
            "url":       "",
            "source":    "simulation",
            "query":     query,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        for h in random.sample(_FAKE_HEADLINES, k=5)
    ]


# ── Main loop ──────────────────────────────────────────────────────────────────

def run():
    producer   = create_producer()
    use_sim    = (NEWS_API_KEY == "YOUR_NEWS_API_KEY_HERE")
    seen_urls  = set()   # simple in-process deduplication

    if use_sim:
        log.warning("No API key set — running in SIMULATION MODE.")

    log.info(f"Producer started. Topic='{KAFKA_TOPIC}', interval={POLL_INTERVAL_S}s")

    try:
        while True:
            for query in NEWS_QUERIES:
                articles = simulate_articles(query) if use_sim else fetch_articles(query)

                published = 0
                for article in articles:
                    dedup_key = article["url"] or article["id"]
                    if dedup_key in seen_urls:
                        continue
                    seen_urls.add(dedup_key)

                    # Send to Kafka — async with delivery callbacks
                    producer.send(KAFKA_TOPIC, value=article) \
                        .add_callback(lambda m: log.debug(f"Delivered → partition={m.partition} offset={m.offset}")) \
                        .add_errback(lambda e: log.error(f"Delivery failed: {e}"))

                    published += 1

                log.info(f"Published {published} new messages  (query='{query}')")

            producer.flush()   # ensure all buffered messages are sent
            log.info(f"Sleeping {POLL_INTERVAL_S}s…\n")
            time.sleep(POLL_INTERVAL_S)

    except KeyboardInterrupt:
        log.info("Shutting down…")
    finally:
        producer.flush()
        producer.close()
        log.info("Producer closed.")


if __name__ == "__main__":
    run()