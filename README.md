# 🧠 Cortex — Company Brain

![CI](https://github.com/agrawal-2005/Cortex/actions/workflows/ci.yml/badge.svg)

**Turn tribal knowledge into AI automation.**

Cortex extracts scattered company knowledge from tools like Slack, Jira, GitHub, and Discord — synthesizes it into structured, executable workflows called **skills** — and serves them via API so AI agents can reliably execute company processes.

> *"If we want every company to run on AI automation, we need a new primitive: a company brain."*
> — Tom Blomfield, YC Partner ([RFS Summer 2026](https://www.ycombinator.com/rfs))

---

## The Problem

Every company has critical know-how scattered everywhere — Slack threads, Jira tickets, Notion docs, meeting recordings, and people's heads. Humans vaguely remember where knowledge lives. AI agents can't operate like that.

**Existing tools help humans find information. Cortex makes company knowledge executable by machines.**

| | Glean / Notion AI | Cortex |
|---|---|---|
| **Output** | Natural language paragraphs | Structured, executable JSON |
| **Consumer** | Humans reading answers | AI agents executing workflows |
| **Knowledge** | Retrieves existing docs | Synthesizes from fragments |
| **Learning** | Basic thumbs up/down | Structural feedback loop |
| **Undocumented knowledge** | Can't surface it | Extracts from behavior patterns |

## How It Works

```
┌──────────────┐     ┌───────────────┐     ┌─────────────┐
│  Company's   │     │               │     │  AI Agents  │
│  scattered   │ ──→ │    Cortex     │ ──→ │  execute    │
│  knowledge   │     │               │     │  reliably   │
│              │     │  Extracts     │     │             │
│  Slack       │     │  Structures   │     │  Support    │
│  GitHub      │     │  Verifies     │     │  Ops        │
│  Jira        │     │  Updates      │     │  Sales      │
│  Discord     │     │               │     │  Eng        │
│  Internal    │     │  Produces     │     │  Finance    │
│  tools       │     │  executable   │     │  HR         │
│              │     │  skills       │     │             │
└──────────────┘     └───────────────┘     └─────────────┘
```

**Input:** Fragmented knowledge across company tools

**Output:** Structured executable skills like this:

```json
{
  "skill": "client_onboarding",
  "confidence": 0.89,
  "steps": [
    {
      "action": "Create tenant in ETS system",
      "tool": "POST /ets/tenants",
      "on_failure": "retry twice, then escalate to pre-sales lead",
      "sources": [
        {
          "type": "slack",
          "author": "Dileep Patel",
          "link": "https://slack.com/archives/C01ABC/p1718..."
        }
      ]
    }
  ]
}
```

Every claim traces back to its source with a clickable link. AI agents consume the JSON. Humans read a plain-English version on the dashboard.

---

## Features

### Multi-Source Ingestion
Connect Slack (export or live bot token), GitHub (public and private repos), Discord (export or bot), Jira, Notion, or upload CSV/JSON/PDF files. Generic API connector for custom internal tools.

### Intelligent Extraction
LLM-powered pipeline that doesn't just retrieve documents — it **synthesizes** workflows from hundreds of scattered messages, tickets, and docs that were never written as a single coherent process.

### Source Tracing
Every step in every skill links back to the exact Slack message, GitHub PR, or Jira ticket it was extracted from. Full transparency and auditability.

### Confidence Scoring
Each skill and each step carries a confidence score based on source recency, author authority, behavioral evidence, and community trust scores that improve over time.

### Human-in-the-Loop Feedback
Domain experts review, approve, edit, or reject extracted skills. Corrections feed back into the extraction pipeline — the system structurally learns from every correction.

### Production-Grade Error Handling
10 LLM failure modes handled with retries, backoff, JSON repair, timeout protection, and graceful degradation. Per-cluster commits ensure partial results are never lost.

### Agent-Ready API
RESTful API returns structured JSON that AI agents can directly execute. Also serves human-readable plain English for dashboards.

---

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.12+
- Node.js 20+
- HuggingFace account (free tier works)

### Setup

```bash
# Clone the repository
git clone https://github.com/agrawal-2005/Cortex.git
cd Cortex

# Copy environment template
cp .env.example .env
# Edit .env — add your HUGGINGFACE_API_TOKEN

# Start infrastructure (PostgreSQL + Redis)
docker-compose up -d

# Install backend dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the backend
uvicorn backend.main:app --reload --port 8000

# In another terminal — start the frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 — you'll see the Cortex dashboard.

### Ingest Your First Data

**Option A — GitHub repo (easiest):**
1. Go to Data Sources page
2. Click "Connect" on GitHub
3. Enter any public repo (e.g., `usestrix/strix`)
4. Click "Ingest" — documents appear within minutes

**Option B — Slack export:**
1. Export your Slack workspace (Settings → Import/Export)
2. Go to Data Sources → Slack → "Upload Export"
3. Upload the zip file

**Option C — File upload:**
1. Go to Data Sources → File Upload
2. Drag and drop any CSV or JSON file

After ingestion, go to Settings → "Run Skill Extraction" to extract workflows.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    DATA SOURCES                          │
│  Slack  │  GitHub  │  Discord  │  Jira  │  File Upload  │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────────┐
│              INGESTION LAYER                            │
│  Source connectors → Document normalization → Storage   │
│  Rate limiting, deduplication, file processing          │
└────────────────────┬───────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────────┐
│              PROCESSING LAYER                           │
│  Embedding (MiniLM-L6-v2) → ChromaDB                   │
│  Clustering (HDBSCAN + boilerplate cleaning)            │
│  Skill Extraction (LLM + structured prompts)            │
│  Confidence Scoring (recency + authority + trust)       │
└────────────────────┬───────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────────┐
│              KNOWLEDGE LAYER                            │
│  Skills Store (PostgreSQL)                              │
│  Source References with deep links                      │
│  Feedback Loop (approve / edit / reject)                │
│  Trust Scoring (per-source learning)                    │
└────────────────────┬───────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────────┐
│              API LAYER                                  │
│  REST API → Structured JSON for agents                  │
│  Dashboard → Human-readable view                        │
│  Query → Natural language → matching skill              │
└────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI (Python 3.12) |
| LLM | Llama 3.1 8B via HuggingFace Inference API |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 (local) |
| Vector DB | ChromaDB |
| Database | PostgreSQL 16 |
| Queue | Celery + Redis |
| Frontend | React + Tailwind CSS |
| LLM Framework | LangChain |
| Clustering | HDBSCAN (scikit-learn) |
| CI/CD | GitHub Actions |

**No custom ML models. No training required.** The entire system runs on pre-trained models + prompt engineering + solid software engineering.

---

## Testing

168 tests covering:
- Ingestion (Slack, GitHub, Discord, file uploads)
- LLM failure handling (10 failure modes with retries and repair)
- Skill extraction and validation
- Feedback loop and trust scoring
- API endpoints
- Clustering quality
- Data integrity

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=backend --cov-report=term-missing

# Run stress test (requires running server)
PYTHONPATH=. .venv/bin/python tests/stress_test.py

# Run performance benchmark
PYTHONPATH=. .venv/bin/python tests/benchmark.py
```

### Performance

| Operation | Time | Threshold |
|-----------|------|-----------|
| Ingest 100 docs | 2.0s (20ms/doc) | < 500ms/doc ✅ |
| Embed 100 docs | 1.2s (12ms/doc) | < 200ms/doc ✅ |
| Cluster 400 docs | 0.14s | < 30s ✅ |
| Extract 1 skill | 8.4s | < 60s ✅ |
| Query response | 32ms (p95: 60ms) | < 2000ms ✅ |

---

## API Reference

### Ingestion
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ingest/github` | Ingest from GitHub repo (returns 202 + task_id) |
| POST | `/api/ingest/slack` | Upload Slack export zip |
| POST | `/api/ingest/discord/upload` | Upload Discord export JSON |
| POST | `/api/ingest/discord/live` | Ingest Discord channels via bot token |
| POST | `/api/ingest/file` | Upload CSV/JSON documents |
| GET | `/api/ingest/status?task_id=...` | Check ingestion progress |

### Processing
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/processing/cluster` | Cluster documents into topics (HDBSCAN) |
| POST | `/api/v1/processing/extract` | Extract a skill from a document cluster |
| POST | `/api/v1/processing/extract-all` | Cluster + extract skills from all documents |

### Skills
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/skills/` | List all skills (filterable) |
| GET | `/api/skills/{id}` | Get skill with steps and sources |
| GET | `/api/skills/{id}/executable` | Machine-readable JSON for agents |

### Query
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/query/` | Natural language query → matching skill |

### Feedback
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/feedback/` | Submit approve/edit/reject |
| GET | `/api/feedback/history/{skill_id}` | Feedback history for a skill |

---

## Project Structure

```
Cortex/
├── .github/workflows/ci.yml    # GitHub Actions CI
├── backend/
│   ├── main.py                  # FastAPI application
│   ├── config.py                # Environment settings
│   ├── database.py              # Async SQLAlchemy setup
│   ├── ingestion/               # Source connectors
│   │   ├── slack_ingester.py
│   │   ├── github_ingester.py
│   │   ├── discord_ingester.py
│   │   └── file_upload_ingester.py
│   ├── processing/              # Knowledge extraction
│   │   ├── embedder.py          # sentence-transformers
│   │   ├── clustering.py        # HDBSCAN + boilerplate cleaning
│   │   ├── skill_extractor.py   # LLM extraction + error handling
│   │   └── prompts/
│   │       └── extraction.py    # Structured extraction prompts
│   ├── knowledge/               # Data models
│   │   └── models.py            # SQLAlchemy models
│   └── api/                     # REST endpoints
│       ├── routes_ingest.py
│       ├── routes_skills.py
│       ├── routes_query.py
│       └── routes_feedback.py
├── frontend/                    # React dashboard
│   └── src/
│       ├── pages/               # Dashboard, Skills, Query, etc.
│       └── components/          # Reusable UI components
├── tests/
│   ├── test_skill_extractor.py
│   ├── test_llm_failures.py     # 10 failure mode tests
│   ├── benchmark.py             # Performance benchmarks
│   └── stress_test.py           # Concurrent load testing
└── alembic/                     # Database migrations
```

---

## Roadmap

- [x] Multi-source ingestion (Slack, GitHub, Discord, file upload)
- [x] LLM-powered skill extraction with source tracing
- [x] Human feedback loop with structural learning
- [x] Production-grade error handling (10 failure modes)
- [x] Performance benchmarks and stress testing
- [x] CI/CD with GitHub Actions
- [ ] Live Slack OAuth integration (real-time sync)
- [ ] Jira live integration
- [ ] Auto-sync scheduler (background re-ingestion)
- [ ] Drift detection (flag outdated skills)
- [ ] MCP server (make Cortex queryable by Claude/Cursor)
- [ ] Deploy to cloud (Railway/Render)
- [ ] SOC 2 compliance and enterprise security

---

## Origin Story

Built by [Prashant Agrawal](https://linkedin.com/in/pr-shant26) — inspired by the experience of manually extracting a 4+ hour client onboarding process from scattered Slack threads and tribal knowledge at [Locus.sh](https://locus.sh), then automating it into a single API call.

Every company has hundreds of processes like this. Cortex automates the extraction.

---

## License

MIT
