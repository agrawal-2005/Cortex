"""Cortex performance benchmark — times every stage of the pipeline.

Run:  .venv/bin/python tests/benchmark.py

Design:
- Pipeline stages (ingest / embed / cluster / extract) run IN-PROCESS against
  an isolated throwaway environment (temp SQLite DB + temp ChromaDB dir) so
  the benchmark never pollutes real data. Source material is real GitHub
  documents read (read-only) from the production database, with a synthetic
  fallback if that DB is unreachable.
- Query timing and read-only API timings hit the LIVE server on
  http://localhost:8000 (real data, real numbers).
- Mutating API endpoints are timed against the in-process app (isolated DB).
- LLM-dependent endpoints are timed once in section 4 (extraction) and
  skipped in the API sweep; external-network endpoints (GitHub/Discord
  ingestion) are skipped.
"""

from __future__ import annotations

import asyncio
import io
import shutil
import statistics
import sys
import tempfile
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Isolated environment (MUST precede backend.main import: routers create
#    VectorStore instances at import time using settings.CHROMA_PERSIST_DIR).
from backend.config import settings  # noqa: E402

TMP_DIR = Path(tempfile.mkdtemp(prefix="cortex-bench-"))
settings.CHROMA_PERSIST_DIR = str(TMP_DIR / "chroma")

import numpy as np  # noqa: E402
from hdbscan import HDBSCAN  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from backend.database import Base, get_db, async_session_factory  # noqa: E402
from backend.main import app  # noqa: E402
from backend.ingestion.file_upload_ingester import FileUploadIngester  # noqa: E402
from backend.processing.embeddings import EmbeddingService  # noqa: E402
from backend.processing.skill_extractor import (  # noqa: E402
    LLMCreditsExhaustedError,
    LLMTimeoutError,
    SkillExtractionPipeline,
)

LIVE_BASE_URL = "http://localhost:8000"

# SLOW thresholds
THRESHOLDS = {
    "ingest_per_doc": 0.5,     # seconds
    "embed_per_doc": 0.2,      # seconds
    "cluster_400": 30.0,       # seconds
    "extract_skill": 60.0,     # seconds
    "query_ms": 2000.0,        # milliseconds
}

# ── Benchmark database (isolated SQLite) ──────────────────────────────────

bench_engine = create_async_engine(f"sqlite+aiosqlite:///{TMP_DIR}/bench.db")
BenchSession = async_sessionmaker(bench_engine, expire_on_commit=False)


async def override_get_db():
    async with BenchSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


# ── Helpers ───────────────────────────────────────────────────────────────

def hr(title: str) -> None:
    print(f"\n{'=' * 66}\n{title}\n{'=' * 66}", flush=True)


def percentiles(times_ms: list[float]) -> tuple[float, float, float]:
    if len(times_ms) == 1:
        t = times_ms[0]
        return t, t, t
    q = statistics.quantiles(times_ms, n=100, method="inclusive")
    return q[49], q[94], q[98]


async def load_source_texts(limit: int = 400) -> tuple[list[str], str]:
    """Read real GitHub document contents from the production DB (read-only).

    Falls back to synthetic documents if the DB is unreachable or sparse.
    """
    texts: list[str] = []
    origin = "production DB (GitHub documents)"
    try:
        async with async_session_factory() as db:
            result = await db.execute(
                text(
                    "SELECT content FROM documents "
                    "WHERE source_type LIKE 'github%' "
                    "ORDER BY ingested_at LIMIT :lim"
                ),
                {"lim": limit},
            )
            texts = [row[0] for row in result if row[0] and row[0].strip()]
    except Exception as exc:
        print(f"  ! Could not read production DB ({exc}); using synthetic docs")
        origin = "synthetic"

    if len(texts) < limit:
        # Pad with variations so cluster sizes are always reachable
        base = texts or [
            "The deploy pipeline runs tests, builds a Docker image, and "
            "rolls out to production via kubectl.",
            "Bug report: the scanner crashes when the target returns a 302 "
            "redirect without a Location header.",
            "PR review: refactor the authentication middleware to store "
            "session tokens according to the compliance requirements.",
        ]
        i = 0
        while len(texts) < limit:
            texts.append(f"{base[i % len(base)]} (variant {i})")
            i += 1
        if origin != "synthetic":
            origin += " + synthetic padding"
    return texts[:limit], origin


def make_records(texts: list[str], prefix: str) -> list[dict]:
    return [
        {
            "content": t,
            "source_id": f"{prefix}-{i}",
            "author_name": "Benchmark Bot",
            "author_role": "Engineer",
            "channel_or_project": "benchmark",
        }
        for i, t in enumerate(texts)
    ]


def make_csv(texts: list[str], prefix: str) -> str:
    import csv as csv_mod

    buf = io.StringIO()
    writer = csv_mod.DictWriter(buf, fieldnames=["content", "source_id", "author_name"])
    writer.writeheader()
    for i, t in enumerate(texts):
        writer.writerow(
            {
                "content": t.replace("\r", " "),
                "source_id": f"{prefix}-{i}",
                "author_name": "Benchmark Bot",
            }
        )
    return buf.getvalue()


class Summary:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def add(self, operation: str, timing: str, status: str) -> None:
        self.rows.append((operation, timing, status))

    def print(self) -> None:
        w1 = max(len(r[0]) for r in self.rows) + 2
        w2 = max(max(len(r[1]) for r in self.rows), len("Time")) + 2
        w3 = max(max(len(r[2]) for r in self.rows), len("Status")) + 2
        top = f"┌{'─' * w1}┬{'─' * w2}┬{'─' * w3}┐"
        mid = f"├{'─' * w1}┼{'─' * w2}┼{'─' * w3}┤"
        bot = f"└{'─' * w1}┴{'─' * w2}┴{'─' * w3}┘"
        print(top)
        print(f"│ {'Operation'.ljust(w1 - 1)}│ {'Time'.ljust(w2 - 1)}│ {'Status'.ljust(w3 - 1)}│")
        print(mid)
        for op, t, s in self.rows:
            print(f"│ {op.ljust(w1 - 1)}│ {t.ljust(w2 - 1)}│ {s.ljust(w3 - 1)}│")
        print(bot)


summary = Summary()


# ── 1. Ingestion ──────────────────────────────────────────────────────────

async def bench_ingestion(texts: list[str], bench_client: AsyncClient) -> None:
    hr("1. INGESTION TIMING")
    ingester = FileUploadIngester()

    # 1a. 100 documents through the full ingest path (DB + embed + Chroma)
    records = make_records(texts[:100], "bench-ingest")
    async with BenchSession() as db:
        t0 = time.perf_counter()
        result = await ingester._ingest_records(records, "github", db)
        await db.commit()
        total = time.perf_counter() - t0
    per_doc = total / 100
    print(f"  Ingest 100 GitHub docs : {total:6.2f}s total, {per_doc * 1000:7.1f}ms/doc "
          f"(created={result['documents_created']})")
    status = "SLOW" if per_doc > THRESHOLDS["ingest_per_doc"] else "OK"
    summary.add("Ingest 100 docs", f"{total:.1f}s ({per_doc * 1000:.0f}ms/doc)", status)

    # 1b. CSV file upload through the API endpoint
    csv_texts = texts[100:120]
    csv_content = make_csv(csv_texts, "bench-csv")
    t0 = time.perf_counter()
    resp = await bench_client.post(
        "/api/ingest/file",
        files={"file": ("bench.csv", csv_content.encode(), "text/csv")},
        data={"source_type": "csv"},
    )
    total = time.perf_counter() - t0
    n = len(csv_texts)
    per_doc = total / n
    ok = resp.status_code < 300
    print(f"  CSV upload ({n} docs)   : {total:6.2f}s total, {per_doc * 1000:7.1f}ms/doc "
          f"(HTTP {resp.status_code})")
    status = "SLOW" if per_doc > THRESHOLDS["ingest_per_doc"] else ("OK" if ok else "FAILED")
    summary.add(f"CSV upload ({n} docs)", f"{total:.2f}s ({per_doc * 1000:.0f}ms/doc)", status)


# ── 2. Embeddings ─────────────────────────────────────────────────────────

def bench_embeddings(texts: list[str]) -> list[list[float]]:
    hr("2. EMBEDDING TIMING")
    service = EmbeddingService()
    snippets = [t[:500] for t in texts]

    # Single-doc calls: embed the same 50 docs one call at a time
    t0 = time.perf_counter()
    for s in snippets[:50]:
        service.generate_embedding(s)
    single_total = time.perf_counter() - t0
    single = single_total / 50
    print(f"  Embed 1 doc at a time  : {single_total:6.2f}s for 50 docs, "
          f"{single * 1000:7.1f}ms/doc")

    # Same 50 docs in one batch call
    t0 = time.perf_counter()
    service.generate_embeddings(snippets[:50])
    batch50 = time.perf_counter() - t0
    batch50_per_doc = batch50 / 50
    speedup = single / batch50_per_doc if batch50_per_doc > 0 else 0
    print(f"  Embed batch of 50      : {batch50:6.2f}s total, {batch50_per_doc * 1000:7.1f}ms/doc "
          f"→ {speedup:.1f}x faster than single calls")

    # 100 documents (and embed all 400 for the clustering stage)
    t0 = time.perf_counter()
    service.generate_embeddings(snippets[:100])
    hundred = time.perf_counter() - t0
    per_doc = hundred / 100
    print(f"  Embed 100 docs         : {hundred:6.2f}s total, {per_doc * 1000:7.1f}ms/doc")

    status = "SLOW" if per_doc > THRESHOLDS["embed_per_doc"] else "OK"
    summary.add("Embed 100 docs", f"{hundred:.1f}s ({per_doc * 1000:.0f}ms/doc)", status)
    summary.add("Embed batch-vs-single", f"{speedup:.1f}x speedup", "OK" if speedup > 1 else "SLOW")

    # Return 400 embeddings for clustering
    return service.generate_embeddings(snippets)


# ── 3. Clustering ─────────────────────────────────────────────────────────

def bench_clustering(embeddings: list[list[float]]) -> None:
    hr("3. CLUSTERING TIMING (HDBSCAN, same params as TopicClusterer)")
    timings: dict[int, float] = {}
    for n in (100, 200, 400):
        arr = np.array(embeddings[:n])
        clusterer = HDBSCAN(
            min_cluster_size=3,
            min_samples=2,
            metric="euclidean",
            core_dist_n_jobs=-1,
        )
        t0 = time.perf_counter()
        labels = clusterer.fit_predict(arr)
        timings[n] = time.perf_counter() - t0
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        print(f"  HDBSCAN {n:3d} docs      : {timings[n] * 1000:8.1f}ms "
              f"({n_clusters} clusters)")

    ratio = timings[400] / timings[100] if timings[100] > 0 else float("inf")
    verdict = (
        "sub-linear" if ratio < 4 else
        "≈ linear" if ratio <= 6 else
        "super-linear (worse than linear)"
    )
    print(f"  Scaling 100→400 (4x data): {ratio:.1f}x time → {verdict}")

    status = "SLOW" if timings[400] > THRESHOLDS["cluster_400"] else "OK"
    summary.add("Cluster 400 docs", f"{timings[400]:.2f}s ({verdict})", status)


# ── 4. Extraction (one real LLM call) ─────────────────────────────────────

async def bench_extraction(texts: list[str]) -> None:
    hr("4. EXTRACTION TIMING (one real LLM call)")
    from backend.knowledge.models import Document

    # Seed a small cluster into the benchmark DB
    doc_ids = []
    async with BenchSession() as db:
        for i, t in enumerate(texts[:6]):
            doc = Document(
                id=str(uuid.uuid4()),
                content=t,
                source_type="github",
                source_id=f"bench-extract-{i}",
                channel_or_project="benchmark",
                author_name="Benchmark Bot",
                author_role="Senior Engineer",
            )
            db.add(doc)
            doc_ids.append(doc.id)
        await db.commit()

    pipeline = SkillExtractionPipeline()

    # Wrap the chain to record prompt/response sizes (≈4 chars per token)
    stats = {"prompt_chars": 0, "response_chars": 0}
    real_chain = pipeline._get_chain()

    class RecordingChain:
        async def ainvoke(self, inputs):
            stats["prompt_chars"] = len(inputs["system_prompt"]) + len(inputs["user_prompt"])
            out = await real_chain.ainvoke(inputs)
            stats["response_chars"] += len(out)
            return out

    pipeline._chain = RecordingChain()

    t0 = time.perf_counter()
    try:
        async with BenchSession() as db:
            skill = await pipeline.extract_from_cluster(
                db=db, document_ids=doc_ids, topic_label="github workflow",
            )
            await db.commit()
            elapsed = time.perf_counter() - t0
            # Count steps inside the session (relationship is lazy-loaded)
            from sqlalchemy import func, select
            from backend.knowledge.models import SkillStep
            n_steps = (
                await db.execute(
                    select(func.count(SkillStep.id)).where(SkillStep.skill_id == skill.id)
                )
            ).scalar()
            skill_name = skill.name
        est_tokens = int((stats["prompt_chars"] + stats["response_chars"]) / 4)
        print(f"  Extract 1 skill        : {elapsed:6.2f}s "
              f"(skill '{skill_name}', {n_steps} steps)")
        print(f"  Estimated tokens       : ~{est_tokens} "
              f"(prompt ~{stats['prompt_chars'] // 4}, response ~{stats['response_chars'] // 4})")
        status = "SLOW" if elapsed > THRESHOLDS["extract_skill"] else "OK"
        summary.add("Extract 1 skill", f"{elapsed:.1f}s (~{est_tokens} tok)", status)
    except LLMCreditsExhaustedError as exc:
        elapsed = time.perf_counter() - t0
        print(f"  Extract 1 skill        : FAILED after {elapsed:.1f}s — HF credits exhausted (402)")
        print(f"                           {exc}")
        summary.add("Extract 1 skill", f"{elapsed:.1f}s", "FAILED (402)")
    except LLMTimeoutError:
        elapsed = time.perf_counter() - t0
        print(f"  Extract 1 skill        : TIMED OUT after {elapsed:.1f}s (> 60s limit)")
        summary.add("Extract 1 skill", f"{elapsed:.1f}s", "SLOW (timeout)")
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        print(f"  Extract 1 skill        : FAILED after {elapsed:.1f}s — {exc}")
        summary.add("Extract 1 skill", f"{elapsed:.1f}s", "FAILED")


# ── 5. Query timing (live server, real data) ──────────────────────────────

QUERY_QUESTIONS = [
    "How do we fix the Discord badge in the README?",
    "How do we handle authentication in the scanner?",
    "What is the process for releasing a new version?",
    "How do we run the test suite?",
    "How are prompt injection vulnerabilities detected?",
    "How do we configure the LLM provider?",
    "What's the workflow for triaging bug reports?",
    "How do we add a new scanning module?",
    "How is Docker used in the project?",
    "How do we update project dependencies?",
]


async def bench_query(live_client: AsyncClient) -> None:
    hr("5. QUERY TIMING (live server, 10 distinct questions)")
    # Untimed warm-up: the live server lazy-loads its embedding model on
    # the first query, which would otherwise skew the first measurement.
    await live_client.post("/api/query/", json={"question": "warmup"})
    times_ms = []
    for q in QUERY_QUESTIONS:
        t0 = time.perf_counter()
        resp = await live_client.post("/api/query/", json={"question": q})
        ms = (time.perf_counter() - t0) * 1000
        times_ms.append(ms)
        matched = "skill" if (resp.status_code == 200 and resp.json().get("skill")) else "no-skill"
        print(f"  {ms:8.1f}ms  [{matched:8s}]  {q}")

    avg = statistics.mean(times_ms)
    p50, p95, _ = percentiles(times_ms)
    print(f"  Average: {avg:.1f}ms | p50: {p50:.1f}ms | p95: {p95:.1f}ms")
    status = "SLOW" if avg > THRESHOLDS["query_ms"] else "OK"
    summary.add("Query response (avg)", f"{avg:.0f}ms", status)


# ── 6. API response times ─────────────────────────────────────────────────

async def bench_api(live_client: AsyncClient, bench_client: AsyncClient) -> None:
    hr("6. API RESPONSE TIMES (10 hits per endpoint)")

    # Discover real IDs on the live server
    live_skill_id = live_doc_id = None
    try:
        r = await live_client.get("/api/skills/", params={"limit": 1})
        items = r.json().get("items", [])
        live_skill_id = items[0]["id"] if items else None
        r = await live_client.get("/api/v1/ingest/documents", params={"limit": 1})
        docs = r.json()
        live_doc_id = docs[0]["id"] if docs else None
    except Exception as exc:
        print(f"  ! Could not fetch live IDs: {exc}")

    # Prepare objects in the benchmark DB for mutation endpoints
    skill_payload = {
        "name": "Benchmark Skill",
        "description": "Skill used only for benchmarking.",
        "department": "engineering",
        "skill_data": {},
        "steps": [
            {"step_order": 1, "action": "Step one", "details": {}, "confidence": 0.9, "depends_on": []},
            {"step_order": 2, "action": "Step two", "details": {}, "confidence": 0.9, "depends_on": []},
        ],
    }
    r = await bench_client.post("/api/v1/skills/", json=skill_payload)
    bench_skill_id = r.json()["id"]
    r = await bench_client.post(
        "/api/feedback/",
        json={"skill_id": bench_skill_id, "action": "approve", "reason": "benchmark"},
    )
    bench_feedback_id = r.json().get("id")
    csv_small = make_csv(["benchmark document for csv upload timing"] * 5, "api-bench")

    # (label, client, method, url, kwargs, skip_reason)
    specs: list[tuple] = [
        ("GET  /health", live_client, "GET", "/health", {}, None),
        ("GET  /api/skills/", live_client, "GET", "/api/skills/", {}, None),
        ("GET  /api/skills/{id}", live_client, "GET", f"/api/skills/{live_skill_id}", {},
         None if live_skill_id else "no live skill"),
        ("GET  /api/skills/{id}/executable", live_client, "GET",
         f"/api/skills/{live_skill_id}/executable", {}, None if live_skill_id else "no live skill"),
        ("GET  /api/v1/skills/", live_client, "GET", "/api/v1/skills/", {}, None),
        ("GET  /api/v1/skills/search", live_client, "GET", "/api/v1/skills/search",
         {"params": {"query": "deploy"}}, None),
        ("GET  /api/v1/skills/{id}", live_client, "GET", f"/api/v1/skills/{live_skill_id}", {},
         None if live_skill_id else "no live skill"),
        ("GET  /api/v1/ingest/documents", live_client, "GET", "/api/v1/ingest/documents", {}, None),
        ("GET  /api/v1/ingest/documents/{id}", live_client, "GET",
         f"/api/v1/ingest/documents/{live_doc_id}", {}, None if live_doc_id else "no live doc"),
        ("GET  /api/v1/processing/.../render", live_client, "GET",
         f"/api/v1/processing/skills/{live_skill_id}/render", {},
         None if live_skill_id else "no live skill"),
        ("GET  /api/feedback/history/{id}", live_client, "GET",
         f"/api/feedback/history/{live_skill_id}", {}, None if live_skill_id else "no live skill"),
        ("GET  /api/v1/feedback/{skill_id}", live_client, "GET",
         f"/api/v1/feedback/{live_skill_id}", {}, None if live_skill_id else "no live skill"),
        ("GET  /api/ingest/status", live_client, "GET", "/api/ingest/status",
         {"params": {"task_id": "benchmark-unknown"}}, None),
        ("POST /api/query/", live_client, "POST", "/api/query/",
         {"json": {"question": "How do we deploy?"}}, None),
        # Mutations → in-process app, isolated DB
        ("POST /api/v1/ingest/documents", bench_client, "POST", "/api/v1/ingest/documents",
         {"json": {"content": "benchmark doc", "source_type": "benchmark", "source_id": "b-1"}}, None),
        ("POST /api/v1/ingest/batch", bench_client, "POST", "/api/v1/ingest/batch",
         {"json": [{"content": f"batch doc {i}", "source_type": "benchmark",
                    "source_id": f"batch-{i}"} for i in range(10)]}, None),
        ("POST /api/ingest/file (CSV x5)", bench_client, "POST", "/api/ingest/file",
         {"files": {"file": ("b.csv", csv_small.encode(), "text/csv")},
          "data": {"source_type": "csv"}}, None),
        ("POST /api/v1/ingest/upload (CSV x5)", bench_client, "POST", "/api/v1/ingest/upload",
         {"files": {"file": ("b.csv", csv_small.encode(), "text/csv")},
          "data": {"source_type": "csv"}}, None),
        ("POST /api/v1/skills/", bench_client, "POST", "/api/v1/skills/",
         {"json": skill_payload}, None),
        ("PUT  /api/v1/skills/{id}", bench_client, "PUT", f"/api/v1/skills/{bench_skill_id}",
         {"json": {"description": "updated by benchmark"}}, None),
        ("POST /api/v1/skills/{id}/execute", bench_client, "POST",
         f"/api/v1/skills/{bench_skill_id}/execute", {}, None),
        ("POST /api/feedback/", bench_client, "POST", "/api/feedback/",
         {"json": {"skill_id": bench_skill_id, "action": "approve", "reason": "bench"}}, None),
        ("POST /api/v1/feedback/", bench_client, "POST", "/api/v1/feedback/",
         {"json": {"skill_id": bench_skill_id, "action": "approve", "reason": "bench"}}, None),
        ("PATCH /api/v1/feedback/{id}", bench_client, "PATCH",
         f"/api/v1/feedback/{bench_feedback_id}", {"json": {"reason": "updated"}},
         None if bench_feedback_id else "feedback create failed"),
        # Skipped endpoints
        ("DELETE /api/v1/skills/{id}", None, None, None, {}, "timed separately below"),
        ("POST /api/ingest/github", None, None, None, {}, "external network (GitHub API)"),
        ("POST /api/ingest/discord/live", None, None, None, {}, "external network (Discord API)"),
        ("POST /api/ingest/slack", None, None, None, {}, "requires Slack export archive"),
        ("POST /api/v1/ingest/slack-export", None, None, None, {}, "requires Slack export archive"),
        ("POST /api/ingest/discord/upload", None, None, None, {}, "requires Discord export file"),
        ("POST /api/v1/processing/cluster", None, None, None, {}, "LLM labeling — see section 3"),
        ("POST /api/v1/processing/extract", None, None, None, {}, "LLM call — see section 4"),
        ("POST /api/v1/processing/extract-all", None, None, None, {}, "LLM call — see section 4"),
    ]

    header = f"  {'Endpoint':40} {'p50':>9} {'p95':>9} {'p99':>9}  status"
    print(header)
    print("  " + "-" * len(header))
    for label, client, method, url, kwargs, skip in specs:
        if skip:
            print(f"  {label:40} {'—':>9} {'—':>9} {'—':>9}  SKIPPED ({skip})")
            continue
        times_ms: list[float] = []
        code = None
        for _ in range(10):
            t0 = time.perf_counter()
            resp = await client.request(method, url, **kwargs)
            times_ms.append((time.perf_counter() - t0) * 1000)
            code = resp.status_code
        p50, p95, p99 = percentiles(times_ms)
        print(f"  {label:40} {p50:8.1f}ms {p95:8.1f}ms {p99:8.1f}ms  HTTP {code}")

    # DELETE: create a fresh skill each round, time only the DELETE
    times_ms = []
    code = None
    for _ in range(10):
        r = await bench_client.post("/api/v1/skills/", json=skill_payload)
        sid = r.json()["id"]
        t0 = time.perf_counter()
        resp = await bench_client.delete(f"/api/v1/skills/{sid}")
        times_ms.append((time.perf_counter() - t0) * 1000)
        code = resp.status_code
    p50, p95, p99 = percentiles(times_ms)
    print(f"  {'DELETE /api/v1/skills/{id}':40} {p50:8.1f}ms {p95:8.1f}ms {p99:8.1f}ms  HTTP {code}")


# ── Main ──────────────────────────────────────────────────────────────────

async def main() -> None:
    print("Cortex Performance Benchmark")
    print(f"Isolated env: {TMP_DIR}")

    # Create benchmark tables
    async with bench_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Check the live server
    live_up = False
    live_client = AsyncClient(base_url=LIVE_BASE_URL, timeout=60.0)
    try:
        r = await live_client.get("/health", timeout=3.0)
        live_up = r.status_code == 200
    except Exception:
        pass
    if not live_up:
        print(f"  ! Live server not reachable at {LIVE_BASE_URL} — "
              "query/API sections will be skipped")

    bench_transport = ASGITransport(app=app)
    bench_client = AsyncClient(transport=bench_transport, base_url="http://bench", timeout=120.0)

    texts, origin = await load_source_texts(400)
    print(f"Source material: 400 documents from {origin}")

    # Warm up the embedding model so model-load time doesn't pollute timings
    print("Warming up embedding model (untimed)...", flush=True)
    t0 = time.perf_counter()
    EmbeddingService().generate_embedding("warmup")
    print(f"  Model loaded in {time.perf_counter() - t0:.1f}s")

    try:
        await bench_ingestion(texts, bench_client)
        embeddings = bench_embeddings(texts)
        bench_clustering(embeddings)
        await bench_extraction(texts)
        if live_up:
            await bench_query(live_client)
            await bench_api(live_client, bench_client)
        else:
            summary.add("Query response (avg)", "—", "SKIPPED (server down)")
    finally:
        await bench_client.aclose()
        await live_client.aclose()
        await bench_engine.dispose()

    hr("SUMMARY")
    summary.print()
    print("\nThresholds: ingest >0.5s/doc, embed >0.2s/doc, cluster >30s/400 docs, "
          "extract >60s/skill, query >2000ms")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        shutil.rmtree(TMP_DIR, ignore_errors=True)
