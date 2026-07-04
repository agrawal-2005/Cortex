"""End-to-end stress test for Cortex.

Runs against a fully ISOLATED stack so production data is never touched:
- Fresh Postgres database  `cortex_stress`  (real concurrency semantics)
- Temp ChromaDB directory
- Real uvicorn server on port 8001 (real HTTP, real connection pool)

Phases:
  1. Upload 5 data sources rapidly (Slack zip, Discord json, CSV, JSON,
     GitHub background ingest)
  2. While ingestion runs: 20 concurrent queries + 20 concurrent skill
     lists + 5 feedback submissions — verify no crashes / 500s
  3. After ingestion: verify document storage, embedding counts, run
     extraction, verify skills created
  4. Concurrent users: 3 users querying simultaneously; concurrent
     feedback on one skill (race-condition detection)

Usage (from repo root):
    PYTHONPATH=. .venv/bin/python tests/stress_test.py

The cortex_stress database must exist (CREATE DATABASE cortex_stress).
"""

import asyncio
import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile
from collections import Counter
from pathlib import Path

TMP_DIR = Path(tempfile.mkdtemp(prefix="cortex-stress-"))
STRESS_DB_URL = "postgresql+asyncpg://cortex:cortex@localhost:5432/cortex_stress"
BASE_URL = "http://127.0.0.1:8001"
FIXTURES = Path(__file__).parent / "fixtures"

# Point THIS process at the isolated stack too (for in-process checks)
os.environ["DATABASE_URL"] = STRESS_DB_URL
os.environ["CHROMA_PERSIST_DIR"] = str(TMP_DIR / "chroma")

import httpx  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    async_sessionmaker,
    create_async_engine,
)

engine = create_async_engine(STRESS_DB_URL)
Session = async_sessionmaker(engine, expire_on_commit=False)

# ── Result tracking ───────────────────────────────────────────────────────

problems: list[str] = []      # crashes, 500s, timeouts, corruption
notes: list[str] = []         # non-fatal observations
checks: list[tuple[str, str, bool]] = []  # (check, result, ok)


def check(name: str, ok: bool, result: str):
    checks.append((name, result, ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {result}")
    if not ok:
        problems.append(f"{name}: {result}")


def hr(title: str):
    print(f"\n{'=' * 66}\n{title}\n{'=' * 66}")


class Outcome:
    """Aggregates HTTP outcomes for a barrage of requests."""

    def __init__(self, label: str):
        self.label = label
        self.statuses: Counter = Counter()
        self.errors: list[str] = []
        self.latencies: list[float] = []
        self.bodies: list = []

    def summary(self) -> str:
        parts = [f"{n}x{code}" for code, n in sorted(self.statuses.items())]
        if self.errors:
            parts.append(f"{len(self.errors)} exceptions")
        lat = ""
        if self.latencies:
            lat = (f" | {min(self.latencies)*1000:.0f}-"
                   f"{max(self.latencies)*1000:.0f}ms")
        return f"{', '.join(parts)}{lat}"

    @property
    def server_errors(self) -> int:
        return sum(n for code, n in self.statuses.items() if code >= 500)


async def hit(client: httpx.AsyncClient, outcome: Outcome, method: str,
              url: str, **kwargs):
    t0 = time.perf_counter()
    try:
        resp = await client.request(method, url, **kwargs)
        outcome.latencies.append(time.perf_counter() - t0)
        outcome.statuses[resp.status_code] += 1
        try:
            outcome.bodies.append(resp.json())
        except Exception:
            outcome.bodies.append(resp.text)
        return resp
    except httpx.TimeoutException:
        outcome.errors.append(f"TIMEOUT {method} {url}")
        return None
    except Exception as e:
        outcome.errors.append(f"{type(e).__name__}: {e}")
        return None


# ── Fixture preparation ───────────────────────────────────────────────────


def make_slack_zip() -> Path:
    src = FIXTURES / "sample_slack_export"
    zip_path = TMP_DIR / "slack_export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for p in src.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(src))
    return zip_path


def make_csv() -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=["content", "source_id", "channel_or_project",
                         "author_name"]
    )
    writer.writeheader()
    for i in range(20):
        writer.writerow({
            "content": (
                f"Runbook entry {i}: when the nightly ETL job fails, first "
                f"check the dead-letter queue, then re-run step {i % 5} of "
                "the pipeline with --resume. Escalate to data-eng if the "
                "checkpoint file is corrupted."
            ),
            "source_id": f"stress-csv-{i}",
            "channel_or_project": "data-eng",
            "author_name": f"csv-user-{i % 3}",
        })
    return buf.getvalue().encode()


def make_json() -> bytes:
    records = [
        {
            "content": (
                f"Support macro {i}: for refund requests over $500, verify "
                "the original payment method, create a ticket in the "
                "billing queue, and get manager approval before issuing. "
                f"Use template R-{i} in the shared drive."
            ),
            "source_id": f"stress-json-{i}",
            "channel_or_project": "support",
            "author_name": f"json-user-{i % 3}",
        }
        for i in range(20)
    ]
    return json.dumps(records).encode()


# ── Server lifecycle ─────────────────────────────────────────────────────


def start_server() -> subprocess.Popen:
    env = os.environ.copy()
    env["DATABASE_URL"] = STRESS_DB_URL
    env["CHROMA_PERSIST_DIR"] = str(TMP_DIR / "chroma")
    log = open(TMP_DIR / "server.log", "w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--port", "8001", "--host", "127.0.0.1"],
        env=env, stdout=log, stderr=subprocess.STDOUT,
        cwd=str(Path(__file__).parent.parent),
    )
    return proc


async def wait_for_server(timeout: float = 60.0):
    async with httpx.AsyncClient() as client:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                r = await client.get(f"{BASE_URL}/health", timeout=2.0)
                if r.status_code == 200:
                    return
            except Exception:
                pass
            await asyncio.sleep(0.5)
    raise RuntimeError("server did not become healthy in time")


# ── Phase 1 + 2: rapid uploads with concurrent read/write load ───────────


async def phase_1_and_2(client: httpx.AsyncClient) -> dict:
    hr("PHASE 1+2: 5 RAPID UPLOADS + CONCURRENT LOAD (20 queries, "
       "20 skill lists, 5 feedback)")

    # Seed one skill so feedback has a target during the storm
    seed = await client.post(
        f"{BASE_URL}/api/v1/skills/",
        json={"name": "Seed Skill (stress)", "description": "seed",
              "steps": [{"step_order": 1, "action": "Do the thing",
                         "confidence": 0.9}]},
    )
    seed.raise_for_status()
    seed_skill_id = seed.json()["id"]

    uploads = Outcome("uploads")
    queries = Outcome("queries")
    skill_lists = Outcome("skill lists")
    feedback = Outcome("feedback")

    slack_zip = make_slack_zip()

    async def up_slack():
        with open(slack_zip, "rb") as f:
            return await hit(
                client, uploads, "POST", f"{BASE_URL}/api/ingest/slack",
                files={"file": ("export.zip", f, "application/zip")},
                timeout=180.0,
            )

    async def up_discord():
        data = (FIXTURES / "discord" / "sample_export.json").read_bytes()
        return await hit(
            client, uploads, "POST",
            f"{BASE_URL}/api/ingest/discord/upload",
            files={"file": ("export.json", data, "application/json")},
            timeout=120.0,
        )

    async def up_csv():
        return await hit(
            client, uploads, "POST", f"{BASE_URL}/api/ingest/file",
            files={"file": ("stress.csv", make_csv(), "text/csv")},
            data={"source_type": "jira"},
            timeout=180.0,
        )

    async def up_json():
        return await hit(
            client, uploads, "POST", f"{BASE_URL}/api/ingest/file",
            files={"file": ("stress.json", make_json(), "application/json")},
            data={"source_type": "notion"},
            timeout=180.0,
        )

    async def up_github():
        return await hit(
            client, uploads, "POST", f"{BASE_URL}/api/ingest/github",
            json={"repo": "usestrix/strix", "months": 6,
                  "max_requests": 20, "include_comments": False},
            timeout=30.0,
        )

    questions = [
        "How do we handle refunds over $500?",
        "What do I do when the nightly ETL job fails?",
        "How do I escalate a corrupted checkpoint file?",
        "What is the billing queue process?",
    ]

    async def one_query(i: int):
        await hit(client, queries, "POST", f"{BASE_URL}/api/query/",
                  json={"question": questions[i % len(questions)]},
                  timeout=60.0)

    async def one_list(_: int):
        await hit(client, skill_lists, "GET", f"{BASE_URL}/api/skills/",
                  timeout=60.0)

    async def one_feedback(i: int):
        await hit(client, feedback, "POST", f"{BASE_URL}/api/feedback/",
                  json={"skill_id": seed_skill_id,
                        "action": ["approve", "edit", "reject"][i % 3],
                        "reason": f"stress feedback {i}",
                        "submitted_by": f"stress-user-{i}"},
                  timeout=60.0)

    t0 = time.perf_counter()
    results = await asyncio.gather(
        up_slack(), up_discord(), up_csv(), up_json(), up_github(),
        *[one_query(i) for i in range(20)],
        *[one_list(i) for i in range(20)],
        *[one_feedback(i) for i in range(5)],
        return_exceptions=True,
    )
    elapsed = time.perf_counter() - t0
    print(f"\n  50 concurrent requests completed in {elapsed:.1f}s")

    crashed = [r for r in results if isinstance(r, Exception)]
    for outcome in (uploads, queries, skill_lists, feedback):
        print(f"  {outcome.label:<12} {outcome.summary()}")
        for err in outcome.errors:
            print(f"      ! {err}")

    check("No unhandled crashes", not crashed, f"{len(crashed)} exceptions")
    total_5xx = sum(o.server_errors
                    for o in (uploads, queries, skill_lists, feedback))
    check("No 500 errors under load", total_5xx == 0, f"{total_5xx} 5xx")
    total_timeouts = sum(
        len([e for e in o.errors if e.startswith("TIMEOUT")])
        for o in (uploads, queries, skill_lists, feedback))
    check("No timeouts under load", total_timeouts == 0,
          f"{total_timeouts} timeouts")
    check("All 5 uploads accepted",
          sum(o for o in uploads.statuses.values()) == 5
          and all(c < 400 for c in uploads.statuses),
          uploads.summary())
    check("All 20 queries answered",
          queries.statuses.get(200, 0) == 20, queries.summary())
    check("All 20 skill lists answered",
          skill_lists.statuses.get(200, 0) == 20, skill_lists.summary())
    check("All 5 feedback accepted",
          feedback.statuses.get(201, 0) == 5, feedback.summary())

    # Pull expected counts + github task id from upload responses
    expected: dict[str, int] = {}
    github_task_id = None
    for body in uploads.bodies:
        if not isinstance(body, dict):
            continue
        if "task_id" in body and body.get("status") == "running":
            github_task_id = body["task_id"]  # only github returns pre-completion
        elif "documents_ingested" in body:
            expected[str(body)[:40]] = body["documents_ingested"]

    return {"github_task_id": github_task_id,
            "seed_skill_id": seed_skill_id,
            "upload_bodies": uploads.bodies}


# ── Phase 3: verify storage, embeddings, extraction ──────────────────────


async def phase_3(client: httpx.AsyncClient, ctx: dict) -> dict:
    hr("PHASE 3: POST-INGESTION VERIFICATION + EXTRACTION")

    # Wait for the GitHub background task
    task_id = ctx["github_task_id"]
    gh_status = "no-task-id"
    if task_id:
        deadline = time.time() + 180
        while time.time() < deadline:
            r = await client.get(f"{BASE_URL}/api/ingest/status",
                                 params={"task_id": task_id}, timeout=10.0)
            body = r.json()
            gh_status = body.get("status", "?")
            if gh_status in ("completed", "failed"):
                if gh_status == "failed":
                    notes.append(f"GitHub ingest failed: {body.get('error')}")
                break
            await asyncio.sleep(2)
    check("GitHub background ingest finished", gh_status == "completed",
          gh_status)

    # Verify documents stored per source
    async with Session() as db:
        rows = (await db.execute(text(
            "SELECT source_type, COUNT(*), "
            "COUNT(*) FILTER (WHERE content IS NULL OR content = ''), "
            "COUNT(*) FILTER (WHERE embedding_id IS NOT NULL) "
            "FROM documents GROUP BY source_type ORDER BY source_type"
        ))).all()
        dup = (await db.execute(text(
            "SELECT COUNT(*) FROM (SELECT source_type, source_id "
            "FROM documents GROUP BY source_type, source_id "
            "HAVING COUNT(*) > 1) d"
        ))).scalar()

    print(f"\n  {'source_type':<15} {'docs':>5} {'empty':>6} {'embedded':>9}")
    total_docs = 0
    for st, n, empty, embedded in rows:
        total_docs += n
        print(f"  {st:<15} {n:>5} {empty:>6} {embedded:>9}")

    source_types = {r[0] for r in rows}
    expected_sources = {"slack"} | {"jira", "notion"}
    has_github = any(st.startswith("github") for st in source_types)
    has_discord = "discord" in source_types
    check("Documents stored from all 5 sources",
          expected_sources <= source_types and has_github and has_discord,
          f"{sorted(source_types)}")
    check("No empty document content",
          all(r[2] == 0 for r in rows),
          f"{sum(r[2] for r in rows)} empty docs")
    check("No duplicate documents", dup == 0, f"{dup} duplicate groups")

    # Embedding consistency
    from backend.processing.embedder import DocumentEmbedder
    embedder = DocumentEmbedder()
    chroma_count = embedder._get_collection().count()
    print(f"\n  documents in Postgres: {total_docs} | "
          f"embeddings in Chroma: {chroma_count}")
    if chroma_count < total_docs:
        notes.append(
            f"Embedding gap after ingest: {total_docs - chroma_count} docs "
            "(github/discord ingestion does not embed — known gap); "
            "backfilling in-process."
        )
        async with Session() as db:
            stats = await embedder.embed_documents(db)
            await db.commit()
        print(f"  backfilled: {stats}")
        chroma_count = embedder._get_collection().count()
    check("Embeddings match document count", chroma_count == total_docs,
          f"{chroma_count}/{total_docs}")

    # Cluster + extract (LLM — bounded to 2 clusters to limit HF spend)
    r = await client.post(f"{BASE_URL}/api/v1/processing/cluster",
                          params={"limit": 500}, timeout=300.0)
    check("Clustering endpoint OK", r.status_code == 200,
          f"HTTP {r.status_code}")
    clusters = [c for c in r.json().get("clusters", [])
                if c["cluster_id"] != -1]
    clusters.sort(key=lambda c: c["document_count"], reverse=True)
    print(f"  clusters found: {len(clusters)}")

    extracted = []
    for cl in clusters[:2]:
        r = await client.post(
            f"{BASE_URL}/api/v1/processing/extract",
            params={"topic_label": cl["topic"]},
            json=cl["document_ids"][:20],
            timeout=300.0,
        )
        if r.status_code == 200:
            body = r.json()
            extracted.append(body)
            print(f"  extracted skill: '{body.get('name')}' "
                  f"({len(body.get('steps', []))} steps) "
                  f"from cluster '{cl['topic']}' "
                  f"({cl['document_count']} docs)")
        else:
            print(f"  extraction failed for '{cl['topic']}': "
                  f"HTTP {r.status_code} {r.text[:200]}")
    check("Extraction created skills", len(extracted) >= 1,
          f"{len(extracted)}/2 clusters extracted")

    async with Session() as db:
        n_skills = (await db.execute(
            text("SELECT COUNT(*) FROM skills"))).scalar()
        n_steps = (await db.execute(
            text("SELECT COUNT(*) FROM skill_steps"))).scalar()
    check("Skills persisted with steps", n_skills >= 2 and n_steps > 0,
          f"{n_skills} skills, {n_steps} steps")

    return {"extracted": extracted}


# ── Phase 4: concurrent users + race conditions ───────────────────────────


async def phase_4(client: httpx.AsyncClient, ctx: dict, ctx3: dict):
    hr("PHASE 4: CONCURRENT USERS + RACE CONDITIONS")

    # 3 users querying simultaneously (5 queries each)
    user_questions = [
        "How do we handle refunds over $500?",
        "What do I do when the ETL job fails?",
        "How do I resume the pipeline after a failure?",
        "Who approves large refunds?",
        "Where is the billing queue?",
    ]
    outcomes = [Outcome(f"user-{u}") for u in range(3)]

    async def user_session(u: int):
        for q in user_questions:
            await hit(client, outcomes[u], "POST", f"{BASE_URL}/api/query/",
                      json={"question": q}, timeout=60.0)

    await asyncio.gather(*[user_session(u) for u in range(3)])

    all_200 = all(o.statuses.get(200, 0) == 5 for o in outcomes)
    for o in outcomes:
        print(f"  {o.label}: {o.summary()}")
    check("3 concurrent users all served", all_200,
          "; ".join(o.summary() for o in outcomes))

    # Same question must produce the same answer for every user
    consistent = True
    for qi in range(len(user_questions)):
        answers = set()
        for o in outcomes:
            if qi < len(o.bodies) and isinstance(o.bodies[qi], dict):
                skill = o.bodies[qi].get("skill")
                answers.add(skill["id"] if skill else "no-skill")
        if len(answers) > 1:
            consistent = False
            notes.append(f"Divergent answers for question {qi}: {answers}")
    check("Consistent answers across users", consistent,
          "identical skill match per question")

    # Race condition: 10 concurrent EDIT feedbacks on one skill.
    # Each edit does version += 1 read-modify-write; lost updates
    # mean version < initial + 10.
    target = ctx3["extracted"][0]["id"] if ctx3["extracted"] else ctx["seed_skill_id"]

    async with Session() as db:
        v0 = (await db.execute(
            text("SELECT version FROM skills WHERE id = :i"),
            {"i": target})).scalar()

    race = Outcome("race-feedback")
    await asyncio.gather(*[
        hit(client, race, "POST", f"{BASE_URL}/api/feedback/",
            json={"skill_id": target, "action": "edit",
                  "reason": f"race {i}", "submitted_by": f"racer-{i}"},
            timeout=60.0)
        for i in range(10)
    ])
    print(f"  race feedback: {race.summary()}")

    n_ok = race.statuses.get(201, 0)
    check("Concurrent feedback: no 500s", race.server_errors == 0,
          race.summary())

    async with Session() as db:
        v1 = (await db.execute(
            text("SELECT version FROM skills WHERE id = :i"),
            {"i": target})).scalar()
        n_fb = (await db.execute(
            text("SELECT COUNT(*) FROM feedback WHERE skill_id = :i "
                 "AND reason LIKE 'race %'"), {"i": target})).scalar()

    check("All feedback rows persisted", n_fb == n_ok,
          f"{n_fb} rows for {n_ok} accepted requests")
    check(
        "No lost updates on skill.version",
        v1 == v0 + n_ok,
        f"version {v0} -> {v1}, expected {v0 + n_ok} "
        f"({v0 + n_ok - v1} lost update(s))",
    )


# ── Main ──────────────────────────────────────────────────────────────────


async def main():
    hr(f"CORTEX STRESS TEST — isolated stack "
       f"(db=cortex_stress, chroma={TMP_DIR / 'chroma'})")

    server = start_server()
    try:
        await wait_for_server()
        print("server healthy on :8001")

        async with httpx.AsyncClient() as client:
            ctx = await phase_1_and_2(client)
            ctx3 = await phase_3(client, ctx)
            await phase_4(client, ctx, ctx3)
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    # Scan server log for tracebacks
    log_text = (TMP_DIR / "server.log").read_text()
    tracebacks = log_text.count("Traceback (most recent call last)")
    if tracebacks:
        notes.append(f"{tracebacks} traceback(s) in server log "
                     f"({TMP_DIR}/server.log)")

    hr("STRESS TEST REPORT")
    name_w = max(len(c) for c, _, _ in checks) + 1
    for name, result, ok in checks:
        print(f"  {'✅ PASS' if ok else '❌ FAIL'}  {name:<{name_w}} {result}")
    print(f"\n  server log tracebacks: {tracebacks}")
    if notes:
        print("\n  Notes:")
        for n in notes:
            print(f"   - {n}")
    if problems:
        print(f"\n  {len(problems)} PROBLEM(S) FOUND:")
        for p in problems:
            print(f"   - {p}")
    else:
        print("\n  No crashes, 500s, timeouts, or data corruption detected.")

    await engine.dispose()
    print(f"\n  (server log kept at {TMP_DIR}/server.log)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    asyncio.run(main())
