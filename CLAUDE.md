# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Visual product authenticity checker: given a product image URL, determine whether it looks genuine or counterfeit by comparing it against known-authentic reference images via CLIP visual embeddings and FAISS nearest-neighbor search.

**This is a learning-first project.** Every phase is chosen to teach a specific concept. Read `src/notes/architecture.md` before touching code — it explains *why* each component exists, not just what it does.

## Current State

Pre-implementation. No code exists yet. All 6 phases are `NOT STARTED`. The architecture and tech stack are fully decided; implementation starts at Phase 1.

## Planned Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Embeddings | CLIP (`openai/clip-vit-base-patch32`) via HuggingFace | Semantic image representations trained on product-like data |
| Vector search | FAISS (local) | Exposes internals; no API cost; teachable index types |
| Metadata | SQLite | FAISS has no metadata concept; SQLite maps `faiss_id → product info` |
| Embedding cache | Redis | Avoids re-running ~100ms CLIP inference on already-seen images |
| Background jobs | Celery + Redis | Long re-index ops must leave the HTTP request cycle |
| API | FastAPI + Pydantic | Async-native, schema validation, matches Python ML ecosystem |

## Planned Source Layout

```
src/
├── embeddings/     # Phase 1 — CLIP inference, preprocessing, Redis embedding cache
├── index/          # Phase 2 — FAISS store, SQLite metadata, batch builder
├── scorer/         # Phase 3 — Cosine similarity aggregation, calibration, evidence packaging
├── feedback/       # Phase 4 — User confirm/reject signals, online index updates, drift detection
├── jobs/           # Phase 5 — Celery tasks, Beat scheduler, worker entrypoint
├── api/            # Phase 6 — FastAPI routes (/check, /index, /feedback, /jobs/{id})
└── notes/          # Architecture doc and learning checkpoints (not production code)
```

## Workflow: Before Implementing Any Feature

Before writing any code for a new feature or phase, create a markdown file in `src/notes/` named after the feature (e.g., `src/notes/phase1-embeddings.md`). The file must cover:

1. **What it does** — plain English, no jargon
2. **Why this approach** — the design decision and what alternatives were rejected and why
3. **How it fits** — how this component connects to the rest of the system
4. **Technical breakdown** — the key implementation details, data structures, and gotchas
5. **What you'll learn** — the concept this feature teaches, explained digestably

Write for someone encountering the concept for the first time. Prioritize *why* over *what*. Only start coding once the note exists.

---

## Key Architectural Constraints

**FAISS has no metadata.** Vectors are stored by integer position only. Every write to the FAISS index must be mirrored to the SQLite `metadata` table to map `faiss_id → {url, product_name, brand}`. Never write one without the other.

**Two separate FAISS indexes.** One for confirmed-genuine reference images, one for confirmed-fake images. The scorer queries both and uses the relative distances.

**Redis serves two roles.** It's the embedding cache (TTL-based, keyed by image URL hash) *and* the Celery broker/results backend. Use separate Redis key namespaces (`embed:` prefix vs Celery's default).

**Feedback loop is write-heavy.** Unlike the read-heavy TTL cache pattern, feedback writes invalidate cached similarity results. Phase 4 requires explicit cache busting — don't assume TTL handles it.

**Async jobs return job IDs.** `POST /index` and re-index operations enqueue Celery tasks and return a `job_id` immediately. `GET /jobs/{job_id}` lets the caller poll status. Never block an HTTP handler on embedding or indexing work.

## Phase Status

Update these as phases complete:

- Phase 1 — Embedding Pipeline: `NOT STARTED`
- Phase 2 — FAISS Index: `NOT STARTED`
- Phase 3 — Confidence Scorer: `NOT STARTED`
- Phase 4 — Feedback Loop: `NOT STARTED`
- Phase 5 — Background Jobs: `NOT STARTED`
- Phase 6 — API Layer: `NOT STARTED`

## Development Setup (once bootstrapped)

Commands will live here once `requirements.txt`, `docker-compose.yml`, and the package structure are created in Phase 1. Until then, the only prerequisite is Redis running locally.
