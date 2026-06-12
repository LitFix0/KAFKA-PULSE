# ⚡ KafkaPulse

A real-time sentiment analysis and RAG-powered news intelligence pipeline. Ingests live news, analyzes sentiment with NLP, stores everything in MongoDB and ChromaDB, and lets you both **view live dashboards** and **chat with the news** using a RAG-powered LLM.

## Tech Stack

- **Apache Kafka** — real-time message streaming
- **Python** — producer and consumer microservices
- **VADER NLP** — sentiment analysis
- **MongoDB** — persistent structured storage
- **ChromaDB** — vector database for semantic search
- **SentenceTransformers** — text embeddings (all-MiniLM-L6-v2)
- **Groq API** — LLM inference (llama-3.1-8b-instant)
- **FastAPI** — REST API backend
- **React + Recharts** — live dashboard and chat UI
- **News API** — live news data source

## Architecture

```
News API
   │
   ▼
Producer (Python)
   │
   ▼
Apache Kafka  →  raw_text topic
   │
   ├──────────────────────────┐
   ▼                           ▼
Sentiment Consumer       Embedding Consumer
(VADER NLP)               (SentenceTransformers)
   │                           │
   ▼                           ▼
MongoDB                    ChromaDB
   │                           │
   └───────────┬───────────────┘
               ▼
            FastAPI
       (/api/stats, /api/recent,
        /api/timeline, /api/chat)
               │
               ▼
       React Dashboard
   (Charts + RAG Chat tab)
   localhost:3000
```

## Project Structure

```
KafkaPulse/
├── producer/
│   ├── news_producer.py        # Fetches live news, publishes to Kafka
│   ├── docker-compose.yml       # Kafka + Zookeeper + MongoDB
│   └── .env                     # NEWS_API_KEY (not committed)
├── consumer/
│   ├── sentiment_consumer.py    # VADER sentiment → MongoDB
│   └── .env                     # MONGO_URI (not committed)
├── embedding_consumer/
│   ├── embedding_consumer.py    # Embeddings → ChromaDB
│   └── chroma_db/                # Vector DB storage (auto-created)
├── api/
│   ├── main.py                  # FastAPI: REST + RAG chat endpoint
│   └── .env                     # MONGO_URI, GROQ_API_KEY (not committed)
├── frontend/
│   └── src/
│       └── App.js               # React dashboard + chat UI
├── start.ps1                    # Start all 6 services with one command
├── stop.ps1                     # Stop all services and close windows
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.9+
- Docker Desktop
- Node.js (LTS)
- News API key — https://newsapi.org (free)
- Groq API key — https://console.groq.com (free)

### Installation

```powershell
# Clone the repo
git clone https://github.com/yourusername/kafkapulse.git
cd KafkaPulse

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install Python dependencies
pip install kafka-python requests vaderSentiment pymongo python-dotenv fastapi uvicorn chromadb sentence-transformers groq

# Install React dependencies
cd frontend
npm install
npm install recharts
cd ..
```

### Configuration

Create three `.env` files:

**producer/.env**
```
NEWS_API_KEY=your_news_api_key_here
```

**consumer/.env**
```
MONGO_URI=mongodb://localhost:27017
```

**api/.env**
```
MONGO_URI=mongodb://localhost:27017
GROQ_API_KEY=your_groq_api_key_here
```

## Running the Project

### 1. Start Docker Desktop
Make sure Docker Desktop is open and running before proceeding.

### 2. Open PowerShell in the project root

```powershell
cd C:\Users\ASUS\Desktop\KafkaPulse
```

### 3. Activate the virtual environment

```powershell
.venv\Scripts\Activate.ps1
```

### 4. Set execution policy and run start script

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\start.ps1
```

This automatically opens 5 separate PowerShell windows running:
- **KafkaPulse-Producer** — fetches live news every 30s
- **KafkaPulse-Consumer** — runs VADER sentiment analysis
- **KafkaPulse-Embedding** — generates embeddings for RAG
- **KafkaPulse-API** — FastAPI backend on port 8000
- **KafkaPulse-Frontend** — React dashboard on port 3000

Wait ~30-40 seconds for everything to initialize.

### 5. Open the dashboard

```
http://localhost:3000
```

## Stopping the Project

```powershell
cd C:\Users\ASUS\Desktop\KafkaPulse
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\stop.ps1
```

This closes all 5 service windows and stops the Docker containers (Kafka, Zookeeper, MongoDB).

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/stats` | GET | Sentiment counts (positive/negative/neutral) |
| `/api/recent?limit=N` | GET | Latest N analyzed articles |
| `/api/timeline?limit=N` | GET | Sentiment scores over time |
| `/api/chat` | POST | RAG chat — ask questions about the news |

### Example chat request

```json
POST /api/chat
{
  "question": "What's happening with stocks today?"
}
```

### Example response

```json
{
  "answer": "According to the articles, stocks are experiencing mixed trends...",
  "sources": [
    { "text": "...", "source": "Reuters", "query": "stocks", "url": "..." }
  ]
}
```

## Features

### Dashboard Tab
- Real-time sentiment counts (total, positive, negative, neutral)
- Sentiment distribution donut chart
- Sentiment score timeline chart
- Live article feed with sentiment, query topic, and source tags
- Auto-refreshes every 5 seconds

### RAG Chat Tab
- Natural language Q&A over live news data
- Semantic search via ChromaDB + SentenceTransformers
- Grounded responses via Groq LLM (llama-3.1-8b-instant)
- Source citations with query topic and news outlet for every answer

## Notes on Timestamps

All timestamps are stored in **UTC** (Coordinated Universal Time). For users in India (IST = UTC+5:30), add 5 hours 30 minutes to the displayed time to get local time. This is standard practice in distributed systems for consistency across services and time zones.

## Rate Limits

- **News API free tier**: 100 requests/day. Producer polls every 30 seconds across 5 query topics with deduplication to stay within limits.
- **Groq API free tier**: Generous rate limits suitable for development and demo use.

## Future Enhancements

- Convert dashboard timestamps to IST display
- Add Reddit API as a second data source
- Keyword/trend extraction consumer
- Sentiment spike alerting
- Cloud deployment (AWS/GCP + Kubernetes)
- Replace VADER with transformer-based sentiment model