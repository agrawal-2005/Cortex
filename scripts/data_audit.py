"""Data integrity audit for the Cortex database.

Checks orphaned records, duplicates, embedding consistency, source link
validity, skill quality, and cluster health. Prints a health report table.

Run from the repo root (so ./chroma_data resolves):

    .venv/bin/python scripts/data_audit.py
"""

import asyncio
import random
import sys
from collections import Counter
from urllib.parse import urlparse

import httpx
from sqlalchemy import func, select

from backend.database import async_session_factory
from backend.knowledge.models import (
    Document,
    Feedback,
    Skill,
    SkillStep,
    StepSource,
)
from backend.processing.clustering import TopicClusterer
from backend.processing.embedder import DocumentEmbedder

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
ICONS = {PASS: "\u2705 PASS", WARN: "\u26a0\ufe0f WARN", FAIL: "\u274c FAIL"}

results: list[tuple[str, str, str]] = []  # (check, result, status)
details: list[str] = []


def record(check: str, result: str, status: str, detail: str | None = None):
    results.append((check, result, status))
    if detail:
        details.append(f"[{check}] {detail}")


def section(title: str):
    print(f"\n{'=' * 62}\n{title}\n{'=' * 62}")


# ── 1. Orphaned records ─────────────────────────────────────────


async def audit_orphans(db):
    section("1. ORPHANED RECORDS")

    q = select(func.count(SkillStep.id)).where(
        SkillStep.skill_id.notin_(select(Skill.id))
    )
    orphan_steps = (await db.execute(q)).scalar() or 0
    print(f"  skill_steps without parent skill:        {orphan_steps}")

    q = select(func.count(StepSource.id)).where(
        StepSource.document_id.notin_(select(Document.id))
    )
    orphan_src_docs = (await db.execute(q)).scalar() or 0
    print(f"  step_sources -> missing document:        {orphan_src_docs}")

    q = select(func.count(StepSource.id)).where(
        StepSource.step_id.notin_(select(SkillStep.id))
    )
    orphan_src_steps = (await db.execute(q)).scalar() or 0
    print(f"  step_sources -> missing step:            {orphan_src_steps}")

    q = select(func.count(Feedback.id)).where(
        Feedback.skill_id.notin_(select(Skill.id))
    )
    orphan_feedback = (await db.execute(q)).scalar() or 0
    print(f"  feedback -> missing skill:               {orphan_feedback}")

    total = orphan_steps + orphan_src_docs + orphan_src_steps + orphan_feedback
    record("Orphaned records", str(total), PASS if total == 0 else FAIL)


# ── 2. Duplicate detection ──────────────────────────────────────


async def audit_duplicates(db):
    section("2. DUPLICATE DETECTION")

    q = (
        select(
            Document.source_type,
            Document.source_id,
            func.count(Document.id).label("n"),
        )
        .group_by(Document.source_type, Document.source_id)
        .having(func.count(Document.id) > 1)
    )
    dup_docs = (await db.execute(q)).all()
    extra_docs = sum(n - 1 for _, _, n in dup_docs)
    print(f"  duplicate documents (source_type+source_id): "
          f"{len(dup_docs)} group(s), {extra_docs} extra row(s)")
    for st, sid, n in dup_docs[:10]:
        print(f"    - {st}/{sid}: {n} copies")

    q = (
        select(Skill.name, func.count(Skill.id).label("n"))
        .group_by(Skill.name)
        .having(func.count(Skill.id) > 1)
    )
    dup_skills = (await db.execute(q)).all()
    extra_skills = sum(n - 1 for _, n in dup_skills)
    print(f"  duplicate skills (same name):            "
          f"{len(dup_skills)} group(s), {extra_skills} extra row(s)")
    for name, n in dup_skills[:10]:
        print(f"    - '{name}': {n} copies")

    record(
        "Duplicate documents", str(extra_docs),
        PASS if extra_docs == 0 else WARN,
        None if not dup_docs else f"{len(dup_docs)} duplicate groups",
    )
    record(
        "Duplicate skills", str(extra_skills),
        PASS if extra_skills == 0 else WARN,
    )


# ── 3. Embedding consistency ────────────────────────────────────


async def audit_embeddings(db):
    section("3. EMBEDDING CONSISTENCY")

    pg_ids = set((await db.execute(select(Document.id))).scalars().all())
    print(f"  documents in PostgreSQL:                 {len(pg_ids)}")

    embedder = DocumentEmbedder()
    try:
        collection = embedder._get_collection()
        chroma_ids = set(collection.get(include=[])["ids"])
    except Exception as e:
        print(f"  ChromaDB unavailable: {e}")
        record("Missing embeddings", "?", FAIL, f"ChromaDB error: {e}")
        return []

    print(f"  embeddings in ChromaDB:                  {len(chroma_ids)}")

    expected = {f"doc-{i}" for i in pg_ids}
    missing = sorted(expected - chroma_ids)   # docs without embeddings
    stale = sorted(chroma_ids - expected)     # embeddings without docs
    print(f"  documents missing embeddings:            {len(missing)}")
    for m in missing[:10]:
        print(f"    - {m}")
    print(f"  stale embeddings (no matching doc):      {len(stale)}")
    for s in stale[:10]:
        print(f"    - {s}")

    record(
        "Missing embeddings", str(len(missing)),
        PASS if not missing else FAIL,
    )
    record(
        "Stale embeddings", str(len(stale)),
        PASS if not stale else WARN,
    )
    return [m.removeprefix("doc-") for m in missing]


# ── 4. Source link validity ─────────────────────────────────────


async def audit_source_links(db):
    section("4. SOURCE LINK VALIDITY (sample of 20)")

    q = (
        select(StepSource.id, Document.source_link)
        .join(Document, StepSource.document_id == Document.id)
    )
    rows = (await db.execute(q)).all()
    print(f"  total step_sources with joined docs:     {len(rows)}")

    if not rows:
        record("Invalid source links", "n/a", PASS, "no step_sources to check")
        return

    sample = random.sample(rows, min(20, len(rows)))
    invalid_format = 0
    broken_github = 0
    checked_gh = 0

    async with httpx.AsyncClient(
        follow_redirects=True, timeout=10.0,
        headers={"User-Agent": "cortex-data-audit"},
    ) as client:
        for ss_id, link in sample:
            if not link:
                invalid_format += 1
                print(f"    MISSING  step_source {ss_id}: no source_link")
                continue
            parsed = urlparse(link)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                invalid_format += 1
                print(f"    INVALID  {link}")
                continue
            if "github.com" in parsed.netloc:
                checked_gh += 1
                try:
                    resp = await client.head(link)
                    if resp.status_code == 405:
                        resp = await client.get(link)
                    status = resp.status_code
                except Exception as e:
                    status = f"error: {e}"
                if status == 404:
                    broken_github += 1
                    print(f"    404      {link}")
                elif not isinstance(status, int) or status >= 400:
                    print(f"    {status}  {link} (not counted as broken)")

    print(f"  sampled: {len(sample)}  |  bad format: {invalid_format}  |  "
          f"github checked: {checked_gh}  |  github 404s: {broken_github}")

    bad = invalid_format + broken_github
    record(
        "Invalid source links", f"{bad}/{len(sample)}",
        PASS if bad == 0 else (WARN if broken_github and not invalid_format else FAIL),
    )


# ── 5. Skill quality ────────────────────────────────────────────


async def audit_skill_quality(db):
    section("5. SKILL QUALITY CHECK")

    q = select(Skill.id, Skill.name).where(
        Skill.id.notin_(select(SkillStep.skill_id))
    )
    empty_skills = (await db.execute(q)).all()
    print(f"  skills with 0 steps:                     {len(empty_skills)}")
    for sid, name in empty_skills:
        print(f"    - {name} ({sid})")

    q = select(Skill.id, Skill.name).where(Skill.confidence == 0)
    zero_conf = (await db.execute(q)).all()
    print(f"  skills with confidence = 0:              {len(zero_conf)}")
    for sid, name in zero_conf[:10]:
        print(f"    - {name} ({sid})")

    q = select(func.count(SkillStep.id)).where(
        func.trim(SkillStep.action) == ""
    )
    empty_actions = (await db.execute(q)).scalar() or 0
    print(f"  steps with empty action text:            {empty_actions}")

    q = select(func.count(SkillStep.id)).where(
        SkillStep.id.notin_(select(StepSource.step_id))
    )
    unsourced_steps = (await db.execute(q)).scalar() or 0
    total_steps = (await db.execute(select(func.count(SkillStep.id)))).scalar() or 0
    print(f"  steps with no source references:         "
          f"{unsourced_steps}/{total_steps}")

    record("Empty skills (0 steps)", str(len(empty_skills)),
           PASS if not empty_skills else FAIL)
    record("Zero-confidence skills", str(len(zero_conf)),
           PASS if not zero_conf else WARN)
    record("Empty step actions", str(empty_actions),
           PASS if empty_actions == 0 else FAIL)
    record("Unsourced steps", str(unsourced_steps),
           PASS if unsourced_steps == 0 else WARN)
    return [sid for sid, _ in empty_skills]


# ── 6. Cluster health ───────────────────────────────────────────


async def audit_cluster_health(db):
    section("6. CLUSTER HEALTH (live TopicClusterer, default params)")

    rows = (await db.execute(select(Document.id, Document.content))).all()
    n_docs = len(rows)
    if n_docs < 3:
        print("  not enough documents to cluster")
        record("Noise cluster ratio", "n/a", WARN, "too few documents")
        record("Mega-cluster share", "n/a", WARN)
        return

    clusters = TopicClusterer().cluster_documents(
        [{"id": i, "content": c} for i, c in rows]
    )
    noise = sum(
        c["document_count"] for c in clusters if c["cluster_id"] == -1
    )
    sizes = sorted(
        (c["document_count"] for c in clusters if c["cluster_id"] != -1),
        reverse=True,
    )
    noise_pct = 100.0 * noise / n_docs
    largest = sizes[0] if sizes else 0
    mega_pct = 100.0 * largest / n_docs

    print(f"  total documents:                         {n_docs}")
    print(f"  clusters found:                          {len(sizes)}")
    print(f"  noise (unclustered):                     {noise} ({noise_pct:.0f}%)")
    print(f"  largest cluster:                         {largest} ({mega_pct:.0f}%)")
    hist = Counter(
        "3-5" if s <= 5 else "6-10" if s <= 10 else
        "11-25" if s <= 25 else "26-50" if s <= 50 else ">50"
        for s in sizes
    )
    print("  cluster size distribution:")
    for bucket in ("3-5", "6-10", "11-25", "26-50", ">50"):
        if hist.get(bucket):
            print(f"    {bucket:>6} docs: {hist[bucket]} cluster(s)")
    print(f"  top 10 cluster sizes: {sizes[:10]}")

    record(
        "Noise cluster ratio", f"{noise_pct:.0f}%",
        PASS if noise_pct < 40 else (WARN if noise_pct < 60 else FAIL),
    )
    record(
        "Mega-cluster share", f"{mega_pct:.0f}%",
        PASS if mega_pct < 30 else (WARN if mega_pct < 50 else FAIL),
    )


# ── Report ──────────────────────────────────────────────────────


def print_report():
    name_w = max(len(c) for c, _, _ in results) + 1
    res_w = max(len(r) for _, r, _ in results) + 1
    res_w = max(res_w, len("Result") + 1)
    st_w = 10

    def row(c, r, s):
        return f"\u2502 {c:<{name_w}}\u2502 {r:<{res_w}}\u2502 {s:<{st_w}}\u2502"

    top = f"\u250c{'\u2500' * (name_w + 1)}\u252c{'\u2500' * (res_w + 1)}\u252c{'\u2500' * (st_w + 1)}\u2510"
    mid = f"\u251c{'\u2500' * (name_w + 1)}\u253c{'\u2500' * (res_w + 1)}\u253c{'\u2500' * (st_w + 1)}\u2524"
    bot = f"\u2514{'\u2500' * (name_w + 1)}\u2534{'\u2500' * (res_w + 1)}\u2534{'\u2500' * (st_w + 1)}\u2518"

    print(f"\n{'=' * 62}\nHEALTH REPORT\n{'=' * 62}")
    print(top)
    print(row("Check", "Result", "Status"))
    print(mid)
    for check, result, status in results:
        print(row(check, result, ICONS[status]))
    print(bot)

    fails = [c for c, _, s in results if s == FAIL]
    warns = [c for c, _, s in results if s == WARN]
    if fails:
        print(f"\nFAIL: {', '.join(fails)}")
    if warns:
        print(f"WARN: {', '.join(warns)}")
    if not fails and not warns:
        print("\nAll checks passed.")
    return fails


async def main():
    async with async_session_factory() as db:
        await audit_orphans(db)
        await audit_duplicates(db)
        await audit_embeddings(db)
        await audit_source_links(db)
        await audit_skill_quality(db)
        await audit_cluster_health(db)

    fails = print_report()
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    asyncio.run(main())
