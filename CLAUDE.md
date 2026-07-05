# Cortex — Company Brain

## What This Is
Cortex extracts scattered company knowledge (Slack, GitHub, Jira,
Confluence) and structures it into "skills" — repeatable workflows
with inputs, steps, tools, approval gates, and error handling —
served via API for AI agents to execute, and via UI for humans to
read. Target: YC application, Fall 2026/Winter 2027.

## Tech Stack
- Backend: FastAPI (Python 3.12, async), PostgreSQL 16, Celery + Redis
- LLM: Groq (llama-3.3-70b-versatile default; llama-3.1-8b-instant
  for bulk when it fits token caps). HuggingFace and Ollama supported
  as fallback providers via LLM_PROVIDER config.
- Embeddings: sentence-transformers/all-MiniLM-L6-v2 (local, 384-dim)
- Vector DB: ChromaDB (local — do not suggest Pinecone/managed vector
  DBs, current scale doesn't need it)
- Clustering: HDBSCAN (min_cluster_size=3, min_samples=1) + boilerplate
  stripping
- Frontend: React + Tailwind (dashboard app)
- Website: separate Vite+React+Tailwind+Framer Motion project in website/

## Critical Environment Notes
- `.venv/bin/pip` is bound to Python 3.14, `.venv/bin/python` is 3.12 —
  ALWAYS use `.venv/bin/python -m pip install`, never bare `pip install`
- Groq free tier has TWO separate limits that behave differently:
  - TPD (tokens/day) — recovers over hours, resets daily
  - TPM per-request cap — a hard ceiling on single request size (413
    error), does NOT improve with more quota or waiting
  - Org-level TPM limits can change without warning (confirmed: an
    org's limit dropped from 27k to 12k between sessions) — verify
    current limits with a small probe before assuming a fix will work
- DB_URL and all credentials come from settings/.env — NEVER hardcode
  DB URLs or API keys in scripts, including throwaway/test scripts

## Project Conventions
- Test data: synthetic "AcmeTech" company (30-person SaaS) across
  4 sources (Slack, Jira, Confluence, GitHub) — cross-referencing by
  design (GitHub PRs cite Jira tickets, etc.). Do NOT use the old
  strix (usestrix/strix) GitHub dataset — it was deleted, it's too
  thin for business-process extraction, don't re-add it.
- Extraction prompts must be domain-agnostic — no dependabot/strix/
  acme-specific examples baked into prompts. Use neutral examples.
- Skills schema requires: inputs_schema, trigger, automation_readiness
  (level: executable|assisted|reference, safe_to_automate,
  missing_for_automation), is_repeatable, and per-step: tool,
  parameters, command, success_criteria, on_failure, approval_gate,
  source_document_ids (required, validator-enforced)
- Safety validator: any skill using a risky-pattern tool (refund,
  payment, delete, deploy-to-prod, rollback, hotfix, merge-to-prod,
  mitigate) with no approval_gate on any step gets safe_to_automate
  forced to false — this overrides the LLM's own self-assessment.
  Never remove or weaken this check.
- Repeatability filter: one-time projects must be rejected
  (status="rejected-not-repeatable"), not extracted as skills.
- Ingestion is idempotent: (source_type, source_id) dedup guard exists
  across all ingestion paths (Slack, Jira, Confluence, GitHub, file
  upload, v1 batch). If adding a NEW ingestion path, it MUST include
  this check — this is how we got a 240→834 document duplication bug
  once already.

## Data Trust Features (never remove or weaken)
- Tenancy: Cortex is currently SINGLE-TENANT BY DESIGN — no
  organization_id/workspace_id exists on any model, and all query
  paths (vector search, clustering, skill matching, lazy extraction)
  operate on one global pool. This is fine for one pilot at a time
  and NOT safe for a second company (audited 2026-07-05: cross-company
  data would be fused into the same skills at extraction time). Before
  onboarding a second company: either one deployment per pilot
  (separate DB + CHROMA_PERSIST_DIR) or real org_id scoping on every
  model and query path.
- The "delete all workspace data" cascade (DELETE /api/workspace/data,
  backend/api/routes_workspace.py) must remain complete — any NEW
  table storing customer data must be added to _DELETION_ORDER when
  created, and any new vector collection must be cleared too. It is a
  hard delete with post-deletion verification (fails loudly if
  anything remains); never soften it to a soft-delete. API keys are
  deliberately kept.
- The transparency page (/data-overview) must stay accurate — if new
  document/skill fields or data stores are added, consider whether
  they belong on this page. It backs the claim "this is everything
  Cortex has processed from your uploads."

## Lazy Extraction (current architecture)
- On ingestion: cluster everything (cheap), pre-extract only top
  PRE_EXTRACT_TOP_N clusters (default 6) for the dashboard
- Remaining clusters stored as "pending" (metadata only)
- On query: match existing skills first; check if a PENDING cluster
  has STRONGER relevance than the matched skill — if so, extract it
  live and cache; ties/weaker keep the existing skill (no wasted LLM call)
- Never re-extract an already-extracted cluster
- Do NOT revert to "extract all clusters upfront" — this was
  deliberately replaced for cost/speed reasons

## What NOT to Do
- Don't suggest Pinecone or other managed vector DBs — ChromaDB local
  is correct at current scale; the bottleneck is LLM calls, not vector
  search
- Don't suggest Ollama as the default — user rejected it (model size);
  Groq is the default, HuggingFace/Ollama are fallback options only
- Don't build auto-sync/cron-based re-ingestion yet — no live API
  connections exist yet (file-upload only), premature until deployed
  with a real connected source
- Don't leave throwaway/test/debug scripts in scripts/ — that folder
  is operator-facing only (create_api_key.py, acmetech_pipeline.py,
  backfill/purge utilities). Delete one-off verification scripts after use.
- Don't chase automation-readiness rubric scores higher through more
  prompt tuning on synthetic data — current ceiling (~5.3/10) reflects
  honest gaps in source data richness, not pipeline weakness. Further
  gains require real customer data, not more tuning.

## Codebase Map
A structural map of this repo exists at graphify-out/. Before
making changes that span multiple modules (e.g. touching the
extraction pipeline, adding a new ingester, or modifying the
query flow), check graphify-out/GRAPH_REPORT.md for the
relevant "god nodes" (heavily-depended-on files) so you
understand blast radius before editing. graph.json has the
full dependency graph if you need to trace a specific
relationship.

## Known Issues (see README for full list)
- Extraction can occasionally hallucinate a plausible-sounding but
  ungrounded step (e.g. inventing a "migration script" not in any
  source) — sometimes with high confidence. Candidate fixes: tighten
  repeatability filter for project-epic steps, ground tool/step names
  against source text.

## Before Any Extraction/Schema Change
Run the full test suite (`.venv/bin/python -m pytest tests/ -q
--ignore=tests/stress_test.py --ignore=tests/benchmark.py`) before AND
after. Current baseline: 279 passing. If a change breaks tests, fix
the code, don't weaken the test.
