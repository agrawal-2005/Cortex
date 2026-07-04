<p align="center">
  <img src="docs/assets/logo.svg" alt="Cortex logo" width="96" />
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/wordmark-dark.svg" />
    <img src="docs/assets/wordmark-light.svg" alt="cortex" width="176" />
  </picture>
</p>

<p align="center">
  <b>Extract how your company actually works. Turn it into workflows AI agents can run.</b>
</p>

<p align="center">
  <img src="https://github.com/agrawal-2005/Cortex/actions/workflows/ci.yml/badge.svg" alt="CI" />
</p>

Cortex extracts scattered company knowledge from tools like Slack, Jira, Confluence, and GitHub — synthesizes it into structured, executable workflows called **skills** — and serves them via API so AI agents can reliably execute company processes.

Cortex is honest about what it produces: **assisted-level skills with human checkpoints, moving toward full autonomy** — not fully autonomous automation. Every skill declares what's still missing before an agent could run it unattended.

> *"If we want every company to run on AI automation, we need a new primitive: a company brain."*
> — Tom Blomfield, YC Partner ([RFS Summer 2026](https://www.ycombinator.com/rfs))

---

## The Problem

Every company has critical know-how scattered everywhere — Slack threads, GitHub PRs, Jira tickets, Confluence pages, and people's heads. Humans vaguely remember where knowledge lives. AI agents can't operate like that.

**Existing tools help humans find information. Cortex makes company knowledge executable by machines.**

| | Glean / Notion AI | Cortex |
|---|---|---|
| **Output** | Natural language paragraphs | Structured, executable JSON |
| **Consumer** | Humans reading answers | AI agents executing workflows |
| **Knowledge source** | Retrieves existing docs | Synthesizes from fragments across tools |
| **Learning** | Basic thumbs up/down | Structural feedback loop with trust calibration |
| **Undocumented knowledge** | Can't surface it | Extracts from behavioral patterns |

---

## How It Works

```
┌──────────────┐     ┌───────────────┐     ┌─────────────┐
│  Company's   │     │               │     │  AI Agents  │
│  scattered   │ ──→ │    Cortex     │ ──→ │  execute    │
│  knowledge   │     │               │     │  reliably   │
│              │     │  Ingests      │     │             │
│  Slack       │     │  Embeds       │     │  Support    │
│  Jira        │     │  Clusters     │     │  Ops        │
│  Confluence  │     │  Extracts     │     │  Sales      │
│  GitHub      │     │  Validates    │     │  Eng        │
│  Discord     │     │  Scores       │     │  Finance    │
│  Files       │     │  Learns       │     │  HR         │
└──────────────┘     └───────────────┘     └─────────────┘
```

**Input:** Fragmented knowledge across company tools.

**Output:** Structured executable skills like:

```json
{
  "skill": "handle_p0_incident",
  "confidence": 0.71,
  "automation_readiness": {
    "level": "assisted",
    "safe_to_automate": false,
    "missing_for_automation": [
      "approval language detected in source but not captured"
    ]
  },
  "steps": [
    {
      "action": "Page the on-call engineer and open an incident channel",
      "tool": "PagerDuty",
      "approval_gate": null,
      "on_failure": "Escalate to the engineering manager directly",
      "sources": [
        { "type": "slack", "author": "Sarah Chen", "link": "slack://..." },
        { "type": "confluence", "author": "Mike Torres", "link": "confluence://..." }
      ]
    }
  ]
}
```

Every step must cite its sources — uncited steps are rejected at extraction time. AI agents consume the JSON. Humans read a plain-English version on the dashboard.

---

## Features

### Multi-Source Synthesis
Connect **Slack** (export or live bot token), **Jira**, **Confluence**, **GitHub** (live repos or JSON exports), **Discord**, or upload **CSV/JSON/PDF** files. Skills are synthesized *across* tools, not per-tool — in the current evaluation dataset, **82% of extracted skills cite more than one source system** (e.g., a Slack incident thread + the Confluence runbook + the Jira postmortem ticket).

### Lazy Extraction
After every ingestion, Cortex clusters all documents and **pre-extracts only the top 6 clusters**. Everything else is stored as a *pending topic* and extracted **on demand at query time** — the first person to ask about a topic triggers its extraction. A concurrency lock prevents overlapping runs from duplicating skills (manual triggers get a 409 while a run is in progress).

### Extraction Quality Gates
Four validator-enforced guarantees on every skill:
1. **Required citations** — every step must cite at least one source document, or it's rejected.
2. **Approval gates** — steps can carry an explicit `approval_gate` (who must sign off before the step runs).
3. **Safety validator** — if a step looks risky (deploy, rollback, refunds, production changes) or any cited source contains approval language, and no approval gate was captured, the skill is **forced to `safe_to_automate: false`** with an explicit note in `missing_for_automation`.
4. **Honest readiness labels** — skills are labeled `manual` / `assisted` / `supervised` / `autonomous` based on what the evidence supports, never inflated.

### Conflict Resolution
When sources disagree (a stale runbook vs. a recent Slack thread describing the new process), recency weighting resolves the conflict — **newer evidence beats stale documentation**, and the confidence score reflects the disagreement.

### Automation-Readiness Rubric
Each skill is scored against an automation-readiness rubric (citations, failure handling, approval gates, tool specificity, corroboration). The quality gates above raised the average rubric score of extracted skills from **3.0 to 5.3** across the evaluation dataset.

### Source Tracing
Every step in every skill links back to the exact Slack message, Jira ticket, Confluence page, or GitHub PR it was extracted from. Full transparency and auditability.

### Confidence Scoring
Each skill and step carries a confidence score based on source recency, author authority, behavioral evidence, and community trust scores that improve over time.

### Human-in-the-Loop Feedback
Domain experts review, approve, edit, or reject extracted skills. Corrections feed back into the extraction pipeline — **verified end-to-end**: reject a step → re-extract → correction appears in the new skill.

### Query Intelligence
Natural language queries match skills via cluster-level document provenance (not just LLM-cited sources). Ranking blends the skill's own semantic similarity to the question with document relevance. If the best match is a pending topic, it's extracted on the spot; if no relevant knowledge exists at all, Cortex says so honestly instead of hallucinating a skill.

### Production-Grade Error Handling
10 LLM failure modes handled: empty responses, truncated JSON (auto-repaired), markdown fences, wrong schema, timeouts, rate limits (429 backoff), credits exhausted (402 graceful stop), and server errors. Per-cluster commits ensure partial results are never lost. Re-uploading the same export is idempotent — duplicates are detected and skipped.

### Security
- **API key authentication** on every route (SHA-256 hashed, shown once at creation)
- **Rate limiting** per API key (10 ingestions/hr, 100 queries/hr)
- **Token encryption** at rest (Fernet) for connected source credentials
- **CORS restriction** (localhost in dev, explicit origins in production)
- **Input validation** (50MB upload cap, file type whitelist, repo format validation)
- **Secret hygiene** (tokens never logged or returned in API responses)

---

## Current Stats

| Metric | Value |
|--------|-------|
| Documents ingested | 694 |
| Data sources | Slack + Jira + Confluence + GitHub + Discord + file uploads |
| Topic clusters | 72 (top clusters pre-extracted, rest on demand) |
| Multi-source skills | 82% cite more than one source system |
| Automation-readiness rubric | 3.0 → 5.3 average after quality gates |
| Automated tests | 273 |
| CI | GitHub Actions (backend tests + frontend & website builds on every push) |
| LLM backends | Groq (default) + HuggingFace Inference API + Ollama (local) |

---

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.12+
- Node.js 20+
- A Groq API key (free tier works) **or** HuggingFace account **or** Ollama (local, free)

### Setup

```bash
# Clone the repository
git clone https://github.com/agrawal-2005/Cortex.git
cd Cortex

# Copy environment template and configure
cp .env.example .env
# Edit .env — set at minimum:
#   LLM_PROVIDER=groq
#   GROQ_API_KEY=gsk_...          (free at console.groq.com)
#   TOKEN_ENCRYPTION_KEY          (generate with command below)

# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Start infrastructure (PostgreSQL + Redis)
docker-compose up -d

# Install backend dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Create your first API key
PYTHONPATH=. .venv/bin/python scripts/create_api_key.py "dev-key"
# Save the printed key — it's shown only once

# Start the backend
uvicorn backend.main:app --reload --port 8000

# In another terminal — start the frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 — you'll see the Cortex dashboard.

### LLM Backends

**Groq (default):** fast, generous free tier. Cortex uses two models:
- `GROQ_MODEL=llama-3.1-8b-instant` — bulk extraction after ingestion
- `GROQ_LIVE_MODEL=llama-3.3-70b-versatile` — on-demand extraction at query time, where quality matters most

**HuggingFace:** set `LLM_PROVIDER=huggingface` and `HUGGINGFACE_API_TOKEN`.

**Ollama (local, unlimited, free):**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1

# In .env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1
OLLAMA_BASE_URL=http://localhost:11434
```

With Ollama, no API credits are needed and your data never leaves your machine.

### Ingest Your First Data

**Option A — GitHub repo (easiest):**
1. Go to Data Sources page
2. Click "Connect" on GitHub
3. Enter any public repo (e.g., `usestrix/strix`)
4. Optionally add a GitHub token for higher rate limits
5. Click "Ingest" — documents appear within minutes

**Option B — Slack export:**
1. Export your Slack workspace (Settings → Import/Export)
2. Go to Data Sources → Slack → "Upload Export"
3. Upload the zip file

**Option C — Jira / Confluence / GitHub JSON export:**
1. Go to Data Sources → pick the source → "Upload Export"
2. Upload the JSON export file (see `data/synthetic/` for the expected shapes)

**Option D — Discord export:**
1. Export channels using [DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter)
2. Go to Data Sources → Discord → "Upload Export"
3. Upload the JSON file

**Option E — File upload:**
1. Go to Data Sources → File Upload
2. Drag and drop any CSV or JSON file

Skill extraction runs automatically after every ingestion (top clusters up front, the rest on demand at query time). Settings → "Run Skill Extraction" is available as a manual re-trigger.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                           │
│  Slack │ Jira │ Confluence │ GitHub │ Discord │ Files       │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   INGESTION LAYER                           │
│  Source connectors + JSON-export ingesters                  │
│  Document normalization → Deduplication (idempotent)        │
│  Rate limiting, boilerplate stripping, file processing      │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   PROCESSING LAYER                          │
│  Embedding (MiniLM-L6-v2) → ChromaDB vector store           │
│  Clustering (HDBSCAN + boilerplate cleaning)                │
│  Lazy extraction: top clusters now, rest pending/on-demand  │
│  Skill Extraction (LLM via Groq / HuggingFace / Ollama)     │
│  Quality gates: citations, approval gates, safety validator │
│  Confidence Scoring (recency + authority + trust)           │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   KNOWLEDGE LAYER                           │
│  Skills Store (PostgreSQL) with source references           │
│  Pending topics (extracted on demand at query time)         │
│  Cluster provenance (skill_documents)                       │
│  Feedback Loop (approve / edit / reject → re-extraction)    │
│  Source Trust Scoring (per-source learning)                 │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   API + SECURITY LAYER                      │
│  REST API → Structured JSON for agents                      │
│  API key auth + rate limiting + token encryption            │
│  Dashboard → Human-readable view                            │
│  Query → Natural language → best matching skill             │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI (Python 3.12), async throughout |
| LLM | Groq (llama-3.3-70b-versatile + llama-3.1-8b-instant) — HuggingFace and Ollama as alternatives |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 (local, 384-dim) |
| Vector DB | ChromaDB (local) |
| Database | PostgreSQL 16 |
| Queue | Celery + Redis |
| Frontend | React + Tailwind CSS |
| LLM Framework | LangChain |
| Clustering | HDBSCAN with boilerplate stripping |
| Security | API keys (SHA-256), Fernet encryption, rate limiting |
| CI/CD | GitHub Actions (273 tests + frontend & website builds) |

**No custom ML models. No training required.** The entire system runs on pre-trained models + prompt engineering + solid software engineering.

---

## Testing

273 tests covering:

| Category | Tests | What's Covered |
|----------|-------|----------------|
| Skill extraction | 50 | Core pipeline, quality gates, safety validator, JSON parsing |
| LLM failure modes | 44 | All 10 failure types: retries, repair, graceful stop |
| Discord ingester | 22 | Export parsing, reply chains, live bot ingestion |
| Security | 21 | Auth, rate limits, encryption, CORS, validation, token hygiene |
| Slack ingester | 20 | Export parsing, threading, idempotent re-ingest |
| Schemas | 18 | Request/response validation |
| JSON export ingesters | 17 | Jira, Confluence, GitHub export parsing + dedup |
| Confidence scoring | 15 | Recency, authority, trust weighting |
| API integration | 15 | All endpoints, error responses |
| Lazy extraction | 14 | Pre-extract, pending topics, on-demand, concurrency guard |
| Query matching | 10 | Cluster provenance, semantic ranking, honest no-knowledge fallback |
| Skills API | 8 | CRUD, executable JSON |
| Ingestion core | 6 | Normalization, deduplication |
| Edge-case audit | 5 | Empty files, duplicate exports, tiny clusters |
| GitHub ingester + routes | 5 | Pagination, rate limits, JSON upload route |
| Feedback loop | 2 | End-to-end: reject → re-extract → correction applied |
| Health | 1 | Liveness |
| Stress test | ✓ | 50 concurrent requests, zero failures |

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=backend --cov-report=term-missing

# Run stress test (requires running server + cortex_stress DB)
PYTHONPATH=. .venv/bin/python tests/stress_test.py

# Run performance benchmark
PYTHONPATH=. .venv/bin/python tests/benchmark.py
```

### Performance Benchmarks

| Operation | Time | Threshold |
|-----------|------|-----------|
| Ingest 100 docs | 2.0s (20ms/doc) | < 500ms/doc ✅ |
| Embed 100 docs | 1.2s (12ms/doc) | < 200ms/doc ✅ |
| Embed batch speedup | 7.3x vs single | — |
| Cluster 400 docs | 0.14s | < 30s ✅ |
| Extract 1 skill (LLM) | 8.4s | < 60s ✅ |
| Query response | 32ms (p95: 60ms) | < 2000ms ✅ |

---

## API Reference

All routes require `X-API-Key` header (except `/health`).

### Ingestion
| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| POST | `/api/ingest/github` | Ingest from live GitHub repo (async, returns 202) | 10/hr |
| POST | `/api/ingest/github/upload` | Upload GitHub JSON export | 10/hr |
| POST | `/api/ingest/slack` | Upload Slack export zip | 10/hr |
| POST | `/api/ingest/jira` | Upload Jira JSON export | 10/hr |
| POST | `/api/ingest/confluence` | Upload Confluence JSON export | 10/hr |
| POST | `/api/ingest/discord/upload` | Upload Discord export JSON | 10/hr |
| POST | `/api/ingest/discord/live` | Ingest via Discord bot token | 10/hr |
| POST | `/api/ingest/file` | Upload CSV/JSON/PDF (max 50MB) | 10/hr |
| GET | `/api/ingest/status` | Check ingestion progress | — |

### Skills
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/skills/` | List all skills (filterable by status, department) |
| GET | `/api/skills/stats` | Skills ready + topics available on demand |
| GET | `/api/skills/{id}` | Skill with steps, sources, human-readable view |
| GET | `/api/skills/{id}/executable` | Machine-readable JSON for AI agents |

### Query
| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| POST | `/api/query/` | Natural language → best matching skill (extracts pending topics on demand) | 100/hr |

### Feedback
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/feedback/` | Submit approve/edit/reject with corrections |

### Processing
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/processing/cluster` | Run document clustering |
| POST | `/api/v1/processing/lazy-extract` | Cluster all docs, extract top clusters, store rest as pending topics (409 if a run is already in progress) |

### Sources
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sources/` | List connected sources (tokens never exposed) |
| POST | `/api/sources/` | Connect new source (token encrypted at rest) |
| DELETE | `/api/sources/{id}` | Disconnect a source |

---

## Project Structure

```
Cortex/
├── .github/workflows/ci.yml     # GitHub Actions CI
├── backend/
│   ├── main.py                   # FastAPI app with auth + rate limiting
│   ├── config.py                 # Environment settings (Groq/HF/Ollama)
│   ├── database.py               # Async SQLAlchemy setup
│   ├── security/                 # Security layer
│   │   ├── auth.py               # API key authentication (SHA-256)
│   │   ├── crypto.py             # Fernet token encryption
│   │   ├── ratelimit.py          # Per-key sliding window rate limits
│   │   └── validation.py         # Input validation + secret hygiene
│   ├── ingestion/                # Source connectors
│   │   ├── slack_ingester.py
│   │   ├── github_ingester.py    # Live GitHub API
│   │   ├── github_json_ingester.py  # GitHub JSON exports
│   │   ├── jira_json_ingester.py
│   │   ├── confluence_json_ingester.py
│   │   ├── discord_ingester.py
│   │   └── file_upload_ingester.py
│   ├── processing/               # Knowledge extraction
│   │   ├── embedder.py           # sentence-transformers embeddings
│   │   ├── clustering.py         # HDBSCAN + boilerplate stripping
│   │   ├── skill_extractor.py    # LLM extraction + quality gates + safety validator
│   │   ├── lazy_extraction.py    # Top-N pre-extract + on-demand pending topics
│   │   └── prompts/
│   │       └── extraction.py     # Structured extraction prompts (citations, approval gates)
│   ├── knowledge/
│   │   └── models.py             # 10 SQLAlchemy models
│   └── api/
│       ├── routes_ingest.py      # Async background ingestion + JSON export uploads
│       ├── routes_skills.py      # Skill CRUD
│       ├── routes_query.py       # Query with relevance ranking + on-demand extraction
│       ├── routes_feedback.py    # Feedback with trust updates
│       └── routes_sources.py     # Encrypted source management
├── frontend/                     # React + Tailwind dashboard (the product)
├── website/                      # Marketing landing page (Vite + React + Framer Motion)
├── data/synthetic/               # AcmeTech synthetic dataset + export generators
├── scripts/
│   ├── create_api_key.py         # Mint API keys
│   ├── acmetech_pipeline.py      # End-to-end synthetic dataset pipeline
│   ├── backfill_skill_documents.py
│   └── purge_orphan_embeddings.py
├── tests/                        # 273 automated tests
├── alembic/                      # 5 database migrations
├── LICENSE                       # MIT
└── docs/
    └── assets/                   # Brand mark + wordmark SVGs
```

---

## Roadmap

### Done
- [x] Multi-source ingestion (Slack, Jira, Confluence, GitHub, Discord, file upload)
- [x] LLM extraction with required source citations
- [x] Triple LLM backend (Groq default + HuggingFace + Ollama)
- [x] Lazy extraction (pre-extract top clusters, rest on demand at query time)
- [x] Extraction quality gates (citations, approval gates, safety validator, honest readiness labels)
- [x] Conflict resolution (recency beats stale docs)
- [x] Human feedback loop — verified end-to-end
- [x] Query with cluster provenance and semantic relevance ranking
- [x] Honest no-knowledge fallback (raw docs or "I don't know" when no skill exists)
- [x] 10 LLM failure modes handled
- [x] Idempotent re-ingestion + extraction concurrency guard
- [x] Security (auth, encryption, rate limiting, CORS, validation)
- [x] 273 automated tests + CI/CD
- [x] Performance benchmarks + stress testing
- [x] Brand identity + marketing landing page (`website/`)

### Next
- [ ] Raise more skills from assisted → supervised → autonomous (capture approval gates at the source)
- [ ] Deploy to cloud (Railway/Render)
- [ ] Live Slack OAuth integration
- [ ] Auto-sync scheduler
- [ ] Drift detection (flag skills whose sources have changed)
- [ ] MCP server (Claude Code/Cursor integration)
- [ ] Frontend tests
- [ ] Multi-tenant support

---

## Origin Story

Built by [Prashant Agrawal](https://linkedin.com/in/pr-shant26) — inspired by manually extracting a 4+ hour client onboarding process from scattered Slack threads and tribal knowledge at [Locus.sh](https://locus.sh), then automating it into a single API call.

Every company has hundreds of processes like this. Cortex automates the extraction.

---

## License

[MIT](LICENSE)
