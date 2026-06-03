# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Visual product authenticity checker for sneakers: a USB webcam captures a physical shoe, a vision-language model identifies the exact SKU, the system pulls official reference imagery from the web, and a cross-comparison produces a `GENUINE` / `SUSPICIOUS` / `COUNTERFEIT` verdict with evidence.

**This is a learning-first project, built twice.** Once on the **edge** (laptop + Python pipeline) to teach computer vision fundamentals, and once in the **cloud** (AWS) to teach managed-services architecture. Read `src/notes/architecture.md` before touching code — it explains *why* each component exists, not just what it does.

## Current State

Pre-implementation. No code exists yet. All 6 phases are `NOT STARTED`. The architecture and tech stack are fully decided; implementation starts at Phase 1.

## Planned Tech Stack — Edge Version

| Layer | Technology | Why |
|---|---|---|
| Capture | OpenCV (`cv2.VideoCapture`) | Cross-platform USB webcam access; bundled preprocessing primitives |
| Preprocessing | OpenCV + Pillow | Denoise, white-balance, crop, resize to 1024×1024 |
| OCR | Tesseract (`pytesseract`) | Offline, free, good enough for printed SKU codes after preprocessing |
| Identification & comparison | Gemini Vision API (`google-genai`, imported as `google.genai`) | Free tier (1,500 req/day on Flash), strong product recognition, built-in Google Search grounding. Replaces the now-EOL `google-generativeai` package |
| Reference lookup | Gemini + Google Search grounding | Collapses identification + scraping into one call; Playwright scraper is optional Phase 3.5 |
| Cache | Redis (Docker) | Sub-ms verdict lookups by image hash; same API as ElastiCache for the cloud port |
| Persistent storage | SQLite | Verdict log + feedback table; zero-config |

## Planned Tech Stack — Cloud Version (AWS)

| Layer | Technology | Why |
|---|---|---|
| Client | Local Python capture script | Webcam is always physical; only the pipeline moves to cloud |
| Ingress | API Gateway → Lambda | Event-driven HTTPS entrypoint |
| Frame storage | S3 | Triggers downstream processing via S3 events |
| Managed CV | AWS Rekognition (`DetectText`, `DetectLabels`) | Replaces Tesseract; integrates natively with Lambda |
| Identification & comparison | Gemini Vision API (called from Lambda) | Gemini is **not** on Bedrock — it stays an external dependency |
| Cache | ElastiCache for Redis | Same role as local Redis, managed |
| Persistent storage | DynamoDB | Key-value access pattern (`image_hash → verdict`); scales to zero |
| Infrastructure | Terraform or AWS CDK | Reproducible cloud resources |

## Planned Source Layout

```
src/
├── capture/    # Phase 1 — Webcam, preprocessing, frame hashing
├── identify/   # Phase 2 — Tesseract OCR + Gemini Vision (product ID)
├── reference/  # Phase 3 — Gemini grounding for reference dossiers
├── verdict/    # Phase 4 — Three-pillar cross-comparison and label synthesis
├── cache/      # Phase 5 — Redis cache + SQLite feedback + invalidation
├── cloud/      # Phase 6 — AWS Lambdas, infra-as-code, local client
└── notes/      # Architecture doc and per-phase learning notes
```

## Workflow: Before Implementing Any Feature

Before writing any code for a new feature or phase, create a markdown file in `src/notes/` named after the feature (e.g., `src/notes/phase1-capture.md`). The file must cover:

1. **What it does** — plain English, no jargon
2. **Why this approach** — the design decision and what alternatives were rejected and why
3. **How it fits** — how this component connects to the rest of the system
4. **Technical breakdown** — the key implementation details, data structures, and gotchas
5. **What you'll learn** — the concept this feature teaches, explained digestably

Write for someone encountering the concept for the first time. Prioritize *why* over *what*. Only start coding once the note exists.

## Workflow: After Implementing a Feature

As soon as a newly added feature is working, create a git commit. The commit message must be a single sentence describing what changed (e.g., `Add Tesseract OCR wrapper for SKU extraction`). One feature per commit — do not batch multiple features together. This applies to every feature, refactor, or fix added to the codebase.

---

## Key Architectural Constraints

**Build edge first, then port to cloud.** Phases 1–5 are the edge build. Phase 6 re-orchestrates the same logic on AWS. The `capture/`, `identify/`, `reference/`, `verdict/`, and `cache/` modules must be importable by both the edge entrypoint and the cloud Lambdas — only the orchestration differs.

**Three independent authenticity pillars.** Every verdict aggregates three separate signals: (1) logo/stitching/materials, (2) sole pattern/silhouette, (3) OCR'd serial/SKU. Do not collapse these into a single LLM call — the explicit per-pillar scoring is what makes the verdict explainable and what creates the meaningful `SUSPICIOUS` middle state.

**`SUSPICIOUS` is a feature, not a failure.** When pillars disagree, return `SUSPICIOUS` with evidence and surface the conflict. Forcing a binary genuine/fake decision destroys the most useful signal the system produces.

**Sneakers only.** The narrow scope is deliberate. Per-SKU reference data, brand-specific SKU validation, and known counterfeit indicators are all category-specific. Do not generalize to other product categories until Phase 6 is complete.

**Manual capture.** A keypress (SPACE) triggers a frame grab. No continuous detection, no auto-trigger. Keeps the CV pipeline focused on single-frame analysis.

**Redis is the cache only.** Unlike the previous design, Redis is *not* a Celery broker here — there is no Celery in this project. Use the `verdict:` key namespace.

**Cache invalidation on feedback.** When the user corrects a verdict, overwrite the Redis entry (TTL 30d for human-confirmed verdicts; TTL 24h for model predictions). Do not rely on TTL expiry to fix wrong verdicts.

**Gemini is the primary LLM.** Wrap calls behind a `VisionClient` interface (`identify`, `lookup_reference`, `compare`) so Claude or GPT-4V can be swapped in for comparison later, but Gemini's free tier and Google Search grounding make it the default.

**Rekognition + Gemini together in the cloud.** Rekognition handles deterministic structured CV (OCR via `DetectText`, sanity-check labeling via `DetectLabels`). Gemini handles reasoning (identification, comparison, verdict). Do not try to make Rekognition produce verdicts — it labels, it doesn't reason.

## Phase Status

Update these as phases complete:

- Phase 1 — Webcam Capture & Preprocessing (Edge): `NOT STARTED`
- Phase 2 — Product Identification (OCR + Vision LLM): `NOT STARTED`
- Phase 3 — Reference Acquisition: `NOT STARTED`
- Phase 4 — Cross-Comparison & Verdict: `NOT STARTED`
- Phase 5 — Cache & Feedback Loop: `NOT STARTED`
- Phase 6 — Cloud Port to AWS: `NOT STARTED`

## Development Setup (once bootstrapped)

Commands will live here once `requirements.txt`, `docker-compose.yml`, and the package structure are created in Phase 1. Until then, prerequisites are:

- Python 3.11+
- A USB webcam (built-in laptop camera also works for development)
- Tesseract installed locally (`choco install tesseract` on Windows)
- Docker (for Redis)
- A Gemini API key (free tier from [aistudio.google.com](https://aistudio.google.com))
- (Phase 6 only) AWS account + credentials configured locally
