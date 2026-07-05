# Graph Report - .  (2026-07-05)

## Corpus Check
- 137 files · ~86,293 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1439 nodes · 3795 edges · 80 communities detected
- Extraction: 45% EXTRACTED · 55% INFERRED · 0% AMBIGUOUS · INFERRED: 2071 edges (avg confidence: 0.58)
- Token cost: 9,800 input · 6,200 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Core Data Models & Pipeline|Core Data Models & Pipeline]]
- [[_COMMUNITY_Source Ingesters|Source Ingesters]]
- [[_COMMUNITY_API Routes & Extraction|API Routes & Extraction]]
- [[_COMMUNITY_Benchmarks & Scripts|Benchmarks & Scripts]]
- [[_COMMUNITY_Lazy Extraction Service|Lazy Extraction Service]]
- [[_COMMUNITY_Auth, Embedding & Clustering|Auth, Embedding & Clustering]]
- [[_COMMUNITY_Connector Base & Slack|Connector Base & Slack]]
- [[_COMMUNITY_Skill Scoring & Query|Skill Scoring & Query]]
- [[_COMMUNITY_Frontend API Client|Frontend API Client]]
- [[_COMMUNITY_Config & Crypto|Config & Crypto]]
- [[_COMMUNITY_Dashboard UI Pages|Dashboard UI Pages]]
- [[_COMMUNITY_File Upload Ingestion|File Upload Ingestion]]
- [[_COMMUNITY_Confidence Scoring|Confidence Scoring]]
- [[_COMMUNITY_API Integration Tests|API Integration Tests]]
- [[_COMMUNITY_Product Docs & Rationale|Product Docs & Rationale]]
- [[_COMMUNITY_Skill Rendering|Skill Rendering]]
- [[_COMMUNITY_Stack & Requirements|Stack & Requirements]]
- [[_COMMUNITY_Favicon Brand Graphics|Favicon Brand Graphics]]
- [[_COMMUNITY_Website App Mockups|Website App Mockups]]
- [[_COMMUNITY_Skill Showcase Component|Skill Showcase Component]]
- [[_COMMUNITY_Processing Pipeline Tasks|Processing Pipeline Tasks]]
- [[_COMMUNITY_Edge Case Audit Tests|Edge Case Audit Tests]]
- [[_COMMUNITY_Rate Limiting|Rate Limiting]]
- [[_COMMUNITY_Skills API Tests|Skills API Tests]]
- [[_COMMUNITY_Logo Geometry|Logo Geometry]]
- [[_COMMUNITY_Integrations Section|Integrations Section]]
- [[_COMMUNITY_Feedback Loop E2E Test|Feedback Loop E2E Test]]
- [[_COMMUNITY_Extraction Prompts|Extraction Prompts]]
- [[_COMMUNITY_How It Works Section|How It Works Section]]
- [[_COMMUNITY_Ingestion Tests|Ingestion Tests]]
- [[_COMMUNITY_Light Wordmark|Light Wordmark]]
- [[_COMMUNITY_Dark Wordmark|Dark Wordmark]]
- [[_COMMUNITY_Website Footer|Website Footer]]
- [[_COMMUNITY_Problem Section|Problem Section]]
- [[_COMMUNITY_Alembic Migration Env|Alembic Migration Env]]
- [[_COMMUNITY_Initial Schema Migration|Initial Schema Migration]]
- [[_COMMUNITY_Automation-Ready Migration|Automation-Ready Migration]]
- [[_COMMUNITY_Pending Clusters Migration|Pending Clusters Migration]]
- [[_COMMUNITY_Skill Documents Migration|Skill Documents Migration]]
- [[_COMMUNITY_Security Migration|Security Migration]]
- [[_COMMUNITY_Groq LLM Choice|Groq LLM Choice]]
- [[_COMMUNITY_App Roots|App Roots]]
- [[_COMMUNITY_Logo Component|Logo Component]]
- [[_COMMUNITY_Source Icons|Source Icons]]
- [[_COMMUNITY_Wordmark Component|Wordmark Component]]
- [[_COMMUNITY_Idempotent Ingestion Rule|Idempotent Ingestion Rule]]
- [[_COMMUNITY_Modal Component|Modal Component]]
- [[_COMMUNITY_Sidebar Component|Sidebar Component]]
- [[_COMMUNITY_Dropzone Component|Dropzone Component]]
- [[_COMMUNITY_CTA Section|CTA Section]]
- [[_COMMUNITY_Stats Section|Stats Section]]
- [[_COMMUNITY_Reveal Animation|Reveal Animation]]
- [[_COMMUNITY_Features Section|Features Section]]
- [[_COMMUNITY_Sync Loop Visual|Sync Loop Visual]]
- [[_COMMUNITY_Navbar|Navbar]]
- [[_COMMUNITY_Hero Section|Hero Section]]
- [[_COMMUNITY_Comparison Section|Comparison Section]]
- [[_COMMUNITY_Demo Section|Demo Section]]
- [[_COMMUNITY_Health Check Test|Health Check Test]]
- [[_COMMUNITY_Celery Worker|Celery Worker]]
- [[_COMMUNITY_PostgreSQL Layer|PostgreSQL Layer]]
- [[_COMMUNITY_MiniLM Embeddings|MiniLM Embeddings]]
- [[_COMMUNITY_Security Cryptography|Security Cryptography]]
- [[_COMMUNITY_Frontend Vite Config|Frontend Vite Config]]
- [[_COMMUNITY_Frontend Entry|Frontend Entry]]
- [[_COMMUNITY_Website Vite Config|Website Vite Config]]
- [[_COMMUNITY_Website Entry|Website Entry]]
- [[_COMMUNITY_Tests Package|Tests Package]]
- [[_COMMUNITY_Backend Package|Backend Package]]
- [[_COMMUNITY_Tasks Package|Tasks Package]]
- [[_COMMUNITY_Ingestion Package|Ingestion Package]]
- [[_COMMUNITY_Security Package|Security Package]]
- [[_COMMUNITY_Processing Package|Processing Package]]
- [[_COMMUNITY_Embeddings Rationale|Embeddings Rationale]]
- [[_COMMUNITY_Prompts Package|Prompts Package]]
- [[_COMMUNITY_Knowledge Package|Knowledge Package]]
- [[_COMMUNITY_API Package|API Package]]
- [[_COMMUNITY_Vectorstore Package|Vectorstore Package]]
- [[_COMMUNITY_HuggingFace Fallback|HuggingFace Fallback]]
- [[_COMMUNITY_Ollama Option|Ollama Option]]

## God Nodes (most connected - your core abstractions)
1. `Document` - 170 edges
2. `Skill` - 161 edges
3. `SkillExtractionPipeline` - 142 edges
4. `SkillStep` - 107 edges
5. `SkillDocument` - 101 edges
6. `LazyExtractionService` - 97 edges
7. `DocumentCreate` - 85 edges
8. `PendingCluster` - 75 edges
9. `VectorStore` - 64 edges
10. `StepSource` - 60 edges

## Surprising Connections (you probably didn't know these)
- `test_redact_secrets_masks_tokens()` --calls--> `redact_secrets()`  [INFERRED]
  tests/test_security.py → backend/security/validation.py
- `TestLLMCall` --uses--> `SkillExtractionPipeline`  [INFERRED]
  tests/test_skill_extractor.py → backend/processing/skill_extractor.py
- `TestEmptyCluster` --uses--> `SkillExtractionPipeline`  [INFERRED]
  tests/test_skill_extractor.py → backend/processing/skill_extractor.py
- `Create a mock Document object.` --uses--> `SkillExtractionPipeline`  [INFERRED]
  tests/test_skill_extractor.py → backend/processing/skill_extractor.py
- `Widened net: production/incident/rollback context must trip the     approval-gat` --uses--> `SkillExtractionPipeline`  [INFERRED]
  tests/test_skill_extractor.py → backend/processing/skill_extractor.py

## Hyperedges (group relationships)
- **Four Validator-Enforced Extraction Quality Gates** — readme_citations_gate, readme_approval_gates, readme_safety_validator, readme_readiness_labels [EXTRACTED 1.00]
- **Triple LLM Backend (Groq default, HuggingFace, Ollama)** — readme_groq, readme_huggingface, readme_ollama [EXTRACTED 1.00]
- **Cortex Brand Identity System** — websiteclaude_wordmark, websiteclaude_logo, websiteclaude_brand_colors, websiteclaude_design_direction [EXTRACTED 1.00]

## Communities

### Community 0 - "Core Data Models & Pipeline"
Cohesion: 0.06
Nodes (159): Run the full extraction pipeline on the AcmeTech synthetic documents.  Phase 1 (, Backfill skill_documents for skills extracted before the table existed.  Legacy, Base, Cortex performance benchmark — times every stage of the pipeline.  Run:  .venv/b, Read real GitHub document contents from the production DB (read-only).      Fall, TopicClusterer, Data integrity audit for the Cortex database.  Checks orphaned records, duplicat, Run migrations in 'offline' mode. (+151 more)

### Community 1 - "Source Ingesters"
Cohesion: 0.03
Nodes (116): BaseConnector, Establish connection to the data source., Fetch documents from the connected data source., Abstract base class for all data source connectors., BaseConnector, ConfluenceJsonIngester, _parse_timestamp(), Confluence JSON export ingester.  Parses a Confluence export shaped as ``{"pages (+108 more)

### Community 2 - "API Routes & Extraction"
Cohesion: 0.04
Nodes (95): BaseModel, _format_documents(), _parse_response(), Skill extraction from documents using LangChain + HuggingFace Inference API., Format document dicts into a string for the prompt., Parse the LLM JSON response into SkillCreate objects., Extracts structured skills/workflows from documents using LLM., Lazy-load the HuggingFace LLM endpoint. (+87 more)

### Community 3 - "Benchmarks & Scripts"
Cohesion: 0.04
Nodes (69): main(), main(), bench_api(), bench_clustering(), bench_embeddings(), bench_extraction(), bench_ingestion(), bench_query() (+61 more)

### Community 4 - "Lazy Extraction Service"
Cohesion: 0.07
Nodes (70): Exception, _is_covered(), _utcnow(), fake_clusterer(), make_cluster(), make_hits(), make_service(), pending_rows() (+62 more)

### Community 5 - "Auth, Embedding & Clustering"
Cohesion: 0.05
Nodes (53): generate_api_key(), hash_api_key(), API key authentication.  Keys look like ``ctx_<random>`` and are shown to the ca, Generate a new plaintext API key (only ever shown once)., Deterministic hash for storage and lookup., FastAPI dependency: reject requests without a valid X-API-Key.      On success,, require_api_key(), _clean_text() (+45 more)

### Community 6 - "Connector Base & Slack"
Cohesion: 0.06
Nodes (29): ABC, connect(), fetch_documents(), Connect to the source, fetch documents, and return them., Parse messages, grouping threads together., Ingests a Slack export directory into Cortex documents with embeddings., Run the full ingestion pipeline.          1. Load users and channels metadata, Load users.json and build lookup. (+21 more)

### Community 7 - "Skill Scoring & Query"
Cohesion: 0.05
Nodes (26): Query(), _authority_weight(), _evidence_weight(), _http_status_of(), _recency_weight(), _sanitize_json(), _step_is_risky(), Query the collection for similar skills.          Args:             query_embedd (+18 more)

### Community 8 - "Frontend API Client"
Cohesion: 0.04
Nodes (10): getIngestStatus(), ReviewQueue(), Settings(), escapeHtml(), highlightJson(), SkillDetail(), pollIngestTask(), SlackModal() (+2 more)

### Community 9 - "Config & Crypto"
Cohesion: 0.06
Nodes (33): BaseSettings, Resolve allowed CORS origins for the current environment., Settings, decrypt_token(), encrypt_token(), Fernet encryption for source tokens stored at rest.  Uses ``settings.TOKEN_ENCRY, Encrypt a plaintext token for storage., Decrypt a stored token.      Raises:         ValueError: If the ciphertext canno (+25 more)

### Community 10 - "Dashboard UI Pages"
Cohesion: 0.06
Nodes (17): Dashboard(), ConfidenceBar(), DeptBadge(), AnswerStep(), collectSources(), ConfidenceDot(), hasGate(), normalizeFailures() (+9 more)

### Community 11 - "File Upload Ingestion"
Cohesion: 0.1
Nodes (30): ingest_file_upload(), ingest_slack_export(), FileUploadIngester, Ingests documents from CSV or JSON file uploads., Ingest documents from a JSON string (array of objects).          Each object sho, Ingest documents from a CSV string.          CSV must have a 'content' column. O, _parse_slack_messages(), File-based ingestion endpoints for Slack exports and generic CSV/JSON uploads. (+22 more)

### Community 12 - "Confidence Scoring"
Cohesion: 0.1
Nodes (17): ConfidenceScorer, Confidence scoring for extracted skills., Calculate a confidence score for a skill.          Scoring breakdown:         -, Calculates and updates confidence scores for skills based on     data completene, Update a confidence score based on user feedback.          Args:             cur, Correction should not drop below 0.1., A fully-populated skill should score at least 0.6 (full completeness)., Rejection can drop to 0.0. (+9 more)

### Community 13 - "API Integration Tests"
Cohesion: 0.06
Nodes (30): GET /api/skills/{id} - returns full skill with steps., GET /api/skills/{id}/executable - machine-readable format., GET /api/skills/{bad_id} - returns 404., POST /api/feedback/ - submit feedback on a skill., GET /api/feedback/history/{skill_id} - returns feedback list., POST /api/feedback/ - 404 for bad skill_id., POST /api/query/ - returns no-match message when empty DB., POST /api/query/ - 400 for empty question. (+22 more)

### Community 14 - "Product Docs & Rationale"
Cohesion: 0.1
Nodes (22): AcmeTech Synthetic Dataset (cross-referenced 4-source test data), Lazy Extraction Architecture (top-N pre-extract, pending on demand), Rationale: Lazy Extraction Replaced Extract-All for Cost/Speed, Repeatability Filter (reject one-time projects), Rationale: Rubric Ceiling ~5.3 Reflects Source-Data Gaps, Not Pipeline Weakness, Safety Validator Rule (risky tools force safe_to_automate=false, never weaken), Skills Schema Requirements (inputs_schema, trigger, automation_readiness, per-step fields), Approval Gates (+14 more)

### Community 15 - "Skill Rendering"
Cohesion: 0.14
Nodes (14): _confidence_indicator(), _format_date(), Human-readable renderer for extracted skills.  Converts a structured Skill (with, Render a Skill into a compact plain-text summary (no markdown).      Useful for, Render a Skill into a flat dictionary for JSON API responses.      Includes the, Return an ascii indicator for a confidence score., Render a Skill ORM object into readable Markdown.      The skill should have its, render_skill_dict() (+6 more)

### Community 16 - "Stack & Requirements"
Cohesion: 0.1
Nodes (20): Rationale: ChromaDB Local over Pinecone (bottleneck is LLM calls, not vector search), Test Suite Baseline (279 passing, run before/after extraction changes), Cortex (Company Brain System), Current Stats (694 docs, 273 tests, 72 clusters), Origin Story (Locus.sh 4-hour Onboarding Extraction), YC RFS 'Company Brain' Quote (Tom Blomfield), Alembic Migrations, Celery + Redis Queue (+12 more)

### Community 17 - "Favicon Brand Graphics"
Cohesion: 0.17
Nodes (18): Brain / Knowledge Concept, Central Convergence Node, Central Hub Node, Circuit Pathways Motif, Connections / Data-Flow Concept, Four Corner Nodes, Cortex Brand, Cortex Favicon (+10 more)

### Community 18 - "Website App Mockups"
Cohesion: 0.14
Nodes (2): ConfBar(), confColor()

### Community 19 - "Skill Showcase Component"
Cohesion: 0.16
Nodes (3): confColor(), ConfidenceBar(), confText()

### Community 20 - "Processing Pipeline Tasks"
Cohesion: 0.25
Nodes (10): ProcessingPipeline, _async_process_documents(), _async_reprocess_skill(), process_documents(), Celery tasks for document processing and skill extraction., Process documents through the extraction pipeline.      Creates a ProcessingPipe, Async implementation of document processing., Re-extract a skill from its original source documents.      Fetches the skill's (+2 more)

### Community 21 - "Edge Case Audit Tests"
Cohesion: 0.15
Nodes (5): Explicit edge-case audit: empty uploads, duplicate exports, tiny clusters.  Comp, Groups smaller than min_cluster_size (3) must not become real         clusters —, TestDuplicateExportIdempotent, TestEmptyFileUploads, TestTinyClustersNotExtracted

### Community 22 - "Rate Limiting"
Cohesion: 0.29
Nodes (7): _caller_id(), ingest_rate_limit(), query_rate_limit(), Per-API-key rate limiting with a sliding one-hour window.  In-process, like the, Record one event for ``key``; raise 429 when over ``limit``/hour., Identify the caller: API key if authenticated, else client IP., SlidingWindowLimiter

### Community 23 - "Skills API Tests"
Cohesion: 0.22
Nodes (0): 

### Community 24 - "Logo Geometry"
Cohesion: 0.36
Nodes (9): Central Hub Node, Right-Angle Circuit Traces, Cyan #00D2FF, Purple #6C5CE7, Four Corner Nodes, Cortex (Brand), Cortex Logo, Knowledge Graph / Neural Network Motif (+1 more)

### Community 25 - "Integrations Section"
Cohesion: 0.25
Nodes (0): 

### Community 26 - "Feedback Loop E2E Test"
Cohesion: 0.43
Nodes (5): FakeLLMChain, _seed_cluster(), _skill_json(), test_feedback_found_even_when_llm_renames_skill(), test_feedback_loop_end_to_end()

### Community 27 - "Extraction Prompts"
Cohesion: 0.32
Nodes (7): build_extraction_prompt(), format_documents_for_prompt(), format_feedback_for_prompt(), Prompt templates for skill extraction.  These prompts instruct the LLM to extrac, Render a list of document dicts into the prompt section.      Each document dict, Render past expert feedback into the prompt section.      Each feedback dict sho, Assemble the full user-turn prompt for skill extraction.      Combines topic con

### Community 28 - "How It Works Section"
Cohesion: 0.29
Nodes (0): 

### Community 29 - "Ingestion Tests"
Cohesion: 0.29
Nodes (0): 

### Community 30 - "Light Wordmark"
Cohesion: 0.43
Nodes (7): Accent Purple #6C5CE7, Cortex Brand, Near-Black Ink #16161F, Inter Typeface, Light Theme Variant, Cortex Wordmark (Light Theme), Accented Letter X

### Community 31 - "Dark Wordmark"
Cohesion: 0.43
Nodes (7): Accent Purple #6C5CE7, Cortex (Brand/Product), Dark Theme Variant, Inter Typeface, Light Gray Text #E8E8ED, Cortex Dark Wordmark, Accented Letter 'x'

### Community 32 - "Website Footer"
Cohesion: 0.4
Nodes (0): 

### Community 33 - "Problem Section"
Cohesion: 0.4
Nodes (0): 

### Community 34 - "Alembic Migration Env"
Cohesion: 0.5
Nodes (3): run_async_migrations(), run_migrations_offline(), run_migrations_online()

### Community 35 - "Initial Schema Migration"
Cohesion: 0.5
Nodes (1): Initial database schema.  Revision ID: 001 Revises: None Create Date: 2025-07-02

### Community 36 - "Automation-Ready Migration"
Cohesion: 0.5
Nodes (1): Add automation-readiness fields to skills.  The skill evaluation showed skill_st

### Community 37 - "Pending Clusters Migration"
Cohesion: 0.5
Nodes (1): Add pending_clusters table for lazy extraction.  On ingestion every document is

### Community 38 - "Skill Documents Migration"
Cohesion: 0.5
Nodes (1): Add skill_documents cluster-provenance table.  Links every document in a skill's

### Community 39 - "Security Migration"
Cohesion: 0.5
Nodes (1): Add api_keys and connected_sources tables.  api_keys stores SHA-256 hashes of AP

### Community 40 - "Groq LLM Choice"
Cohesion: 0.5
Nodes (4): Rationale: Groq Default, Ollama Rejected for Model Size, Groq TPD/TPM Limit Gotcha (413 hard cap, org limits shift), Groq LLM Backend (default), langchain-groq

### Community 41 - "App Roots"
Cohesion: 0.67
Nodes (1): App()

### Community 42 - "Logo Component"
Cohesion: 0.67
Nodes (1): Logo()

### Community 43 - "Source Icons"
Cohesion: 0.67
Nodes (0): 

### Community 44 - "Wordmark Component"
Cohesion: 0.67
Nodes (1): Wordmark()

### Community 45 - "Idempotent Ingestion Rule"
Cohesion: 0.67
Nodes (3): Rationale: Dedup Guard Born from 240-to-834 Document Duplication Bug, Idempotent Ingestion Dedup Guard (source_type, source_id), Production-Grade LLM Error Handling (10 Failure Modes)

### Community 46 - "Modal Component"
Cohesion: 1.0
Nodes (0): 

### Community 47 - "Sidebar Component"
Cohesion: 1.0
Nodes (0): 

### Community 48 - "Dropzone Component"
Cohesion: 1.0
Nodes (0): 

### Community 49 - "CTA Section"
Cohesion: 1.0
Nodes (0): 

### Community 50 - "Stats Section"
Cohesion: 1.0
Nodes (0): 

### Community 51 - "Reveal Animation"
Cohesion: 1.0
Nodes (0): 

### Community 52 - "Features Section"
Cohesion: 1.0
Nodes (0): 

### Community 53 - "Sync Loop Visual"
Cohesion: 1.0
Nodes (0): 

### Community 54 - "Navbar"
Cohesion: 1.0
Nodes (0): 

### Community 55 - "Hero Section"
Cohesion: 1.0
Nodes (0): 

### Community 56 - "Comparison Section"
Cohesion: 1.0
Nodes (0): 

### Community 57 - "Demo Section"
Cohesion: 1.0
Nodes (0): 

### Community 58 - "Health Check Test"
Cohesion: 1.0
Nodes (0): 

### Community 59 - "Celery Worker"
Cohesion: 1.0
Nodes (1): Celery worker configuration for Cortex async tasks.

### Community 60 - "PostgreSQL Layer"
Cohesion: 1.0
Nodes (2): PostgreSQL 16 Skills Store, SQLAlchemy (async) + asyncpg

### Community 61 - "MiniLM Embeddings"
Cohesion: 1.0
Nodes (2): MiniLM-L6-v2 Embeddings (384-dim, local), sentence-transformers

### Community 62 - "Security Cryptography"
Cohesion: 1.0
Nodes (2): Security Layer (API Keys, Fernet, Rate Limits), cryptography (Fernet)

### Community 63 - "Frontend Vite Config"
Cohesion: 1.0
Nodes (0): 

### Community 64 - "Frontend Entry"
Cohesion: 1.0
Nodes (0): 

### Community 65 - "Website Vite Config"
Cohesion: 1.0
Nodes (0): 

### Community 66 - "Website Entry"
Cohesion: 1.0
Nodes (0): 

### Community 67 - "Tests Package"
Cohesion: 1.0
Nodes (0): 

### Community 68 - "Backend Package"
Cohesion: 1.0
Nodes (0): 

### Community 69 - "Tasks Package"
Cohesion: 1.0
Nodes (0): 

### Community 70 - "Ingestion Package"
Cohesion: 1.0
Nodes (0): 

### Community 71 - "Security Package"
Cohesion: 1.0
Nodes (0): 

### Community 72 - "Processing Package"
Cohesion: 1.0
Nodes (0): 

### Community 73 - "Embeddings Rationale"
Cohesion: 1.0
Nodes (1): Lazy-load the SentenceTransformer model.

### Community 74 - "Prompts Package"
Cohesion: 1.0
Nodes (0): 

### Community 75 - "Knowledge Package"
Cohesion: 1.0
Nodes (0): 

### Community 76 - "API Package"
Cohesion: 1.0
Nodes (0): 

### Community 77 - "Vectorstore Package"
Cohesion: 1.0
Nodes (0): 

### Community 78 - "HuggingFace Fallback"
Cohesion: 1.0
Nodes (1): HuggingFace LLM Backend

### Community 79 - "Ollama Option"
Cohesion: 1.0
Nodes (1): Ollama LLM Backend (local)

## Ambiguous Edges - Review These
- `Current Stats (694 docs, 273 tests, 72 clusters)` → `Test Suite Baseline (279 passing, run before/after extraction changes)`  [AMBIGUOUS]
  CLAUDE.md · relation: conceptually_related_to
- `Current Stats (694 docs, 273 tests, 72 clusters)` → `Website Facts Block (206 tests, 454 docs, 28 skills)`  [AMBIGUOUS]
  website/CLAUDE.md · relation: conceptually_related_to
- `Cortex Brand` → `Node-Graph Motif`  [AMBIGUOUS]
  frontend/public/favicon.svg · relation: symbolizes
- `Central Convergence Node` → `Connections / Data-Flow Concept`  [AMBIGUOUS]
  website/public/favicon.svg · relation: conceptually_related_to
- `Cortex Brand` → `Light Theme Variant`  [AMBIGUOUS]
  docs/assets/wordmark-light.svg · relation: conceptually_related_to
- `Cortex (Brand/Product)` → `Accented Letter 'x'`  [AMBIGUOUS]
  docs/assets/wordmark-dark.svg · relation: conceptually_related_to
- `Cortex (Brand)` → `Central Hub Node`  [AMBIGUOUS]
  docs/assets/logo.svg · relation: symbolizes

## Knowledge Gaps
- **110 isolated node(s):** `POST /api/ingest/file - upload CSV, verify documents created.`, `POST /api/ingest/file - reject non-csv/json files.`, `GET /api/skills/ - empty list initially.`, `Create a skill via v1 API, then list via v2 API.`, `GET /api/skills/?status=draft - filters work.` (+105 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Modal Component`** (2 nodes): `Modal.jsx`, `Modal()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Sidebar Component`** (2 nodes): `Sidebar.jsx`, `Sidebar()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Dropzone Component`** (2 nodes): `DropZone()`, `DropZone.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `CTA Section`** (2 nodes): `CTA()`, `CTA.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Stats Section`** (2 nodes): `Stats()`, `Stats.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Reveal Animation`** (2 nodes): `Reveal()`, `Reveal.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Features Section`** (2 nodes): `Features()`, `Features.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Sync Loop Visual`** (2 nodes): `SyncLoop()`, `SyncLoop.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Navbar`** (2 nodes): `Navbar()`, `Navbar.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Hero Section`** (2 nodes): `Hero()`, `Hero.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Comparison Section`** (2 nodes): `Comparison()`, `Comparison.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Demo Section`** (2 nodes): `Demo()`, `Demo.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Health Check Test`** (2 nodes): `test_health_check()`, `test_api_health.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Celery Worker`** (2 nodes): `worker.py`, `Celery worker configuration for Cortex async tasks.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `PostgreSQL Layer`** (2 nodes): `PostgreSQL 16 Skills Store`, `SQLAlchemy (async) + asyncpg`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `MiniLM Embeddings`** (2 nodes): `MiniLM-L6-v2 Embeddings (384-dim, local)`, `sentence-transformers`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Security Cryptography`** (2 nodes): `Security Layer (API Keys, Fernet, Rate Limits)`, `cryptography (Fernet)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Frontend Vite Config`** (1 nodes): `vite.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Frontend Entry`** (1 nodes): `main.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Website Vite Config`** (1 nodes): `vite.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Website Entry`** (1 nodes): `main.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Tests Package`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Backend Package`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Tasks Package`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Ingestion Package`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Security Package`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Processing Package`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Embeddings Rationale`** (1 nodes): `Lazy-load the SentenceTransformer model.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Prompts Package`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Knowledge Package`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `API Package`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Vectorstore Package`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `HuggingFace Fallback`** (1 nodes): `HuggingFace LLM Backend`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Ollama Option`** (1 nodes): `Ollama LLM Backend (local)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Current Stats (694 docs, 273 tests, 72 clusters)` and `Test Suite Baseline (279 passing, run before/after extraction changes)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Current Stats (694 docs, 273 tests, 72 clusters)` and `Website Facts Block (206 tests, 454 docs, 28 skills)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Cortex Brand` and `Node-Graph Motif`?**
  _Edge tagged AMBIGUOUS (relation: symbolizes) - confidence is low._
- **What is the exact relationship between `Central Convergence Node` and `Connections / Data-Flow Concept`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Cortex Brand` and `Light Theme Variant`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Cortex (Brand/Product)` and `Accented Letter 'x'`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Cortex (Brand)` and `Central Hub Node`?**
  _Edge tagged AMBIGUOUS (relation: symbolizes) - confidence is low._