# Visual Product Authenticity Checker — Architecture & Implementation Guide

> **Purpose of this document:** A learning-first breakdown of every system component and why it's built the way it is. Each phase
> teaches a concept. Read this before touching code.

---

## What This System Does (Plain English)

You give it a product image. It asks: *"Does this look like the real thing?"*

It answers by comparing the image against a collection of known-authentic reference images — not pixel-by-pixel, but by meaning.
An embedding model reads the image and produces a list of ~512 numbers that represent *what the image looks like conceptually*
(texture, shape, logo placement, color distribution). Then it searches a vector database to find reference images with the most
similar meaning-fingerprints. If the closest matches are far away in that meaning-space, the product looks suspicious.

---

## System Architecture Overview

```
 ┌─────────────────────────────────────────────────────────────┐
 │                    QUERY PATH (read)                        │
 │                                                             │
 │  Product Image URL ──► Image Fetcher ──► Preprocessor       │
 │                                               │             │
 │                                               ▼             │
 │                                     Embedding Model (CLIP)  │
 │                                               │             │
 │                                    Query Vector (512-dim)   │
 │                                               │             │
 │                                               ▼             │
 │                                       FAISS Index           │
 │                                     (Top-K Search)          │
 │                                               │             │
 │                                  Similarity Scores + Hits   │
 │                                               │             │
 │                                               ▼             │
 │                                    Confidence Scorer        │
 │                                   (cosine → risk label)     │
 │                                               │             │
 │                             ┌─────────────────┴──────────┐  │
 │                             │  GENUINE / SUSPICIOUS /    │  │
 │                             │  COUNTERFEIT + score 0–1   │  │
 │                             └────────────────────────────┘  │
 └─────────────────────────────────────────────────────────────┘

 ┌─────────────────────────────────────────────────────────────┐
 │                   INDEX PATH (write)                        │
 │                                                             │
 │  Reference Image ──► Preprocessor ──► Embedding Model      │
 │                                               │             │
 │                                         New Vector          │
 │                                               │             │
 │                                               ▼             │
 │                                    FAISS Index (write)      │
 │                                    + Metadata Store (SQLite)│
 └─────────────────────────────────────────────────────────────┘

 ┌─────────────────────────────────────────────────────────────┐
 │                  FEEDBACK LOOP (online learning)            │
 │                                                             │
 │  User flags listing ──► Confirm/Reject UI                   │
 │                                   │                         │
 │                    ┌──────────────┴──────────────┐          │
 │                    │ Confirmed fake:              │          │
 │                    │   add to "known-fake" index  │          │
 │                    │ Confirmed genuine:           │          │
 │                    │   add to reference index     │          │
 │                    └──────────────────────────────┘          │
 └─────────────────────────────────────────────────────────────┘

 ┌─────────────────────────────────────────────────────────────┐
 │               BACKGROUND JOBS (async)                       │
 │                                                             │
 │  Redis Queue ──► Celery Worker                              │
 │                      │                                      │
 │              ┌───────┴────────┐                             │
 │              │  - Re-index    │                             │
 │              │  - Batch embed │                             │
 │              │  - Drift detect│                             │
 │              └────────────────┘                             │
 └─────────────────────────────────────────────────────────────┘
```

---

## Core Concepts You'll Learn (and Where)

| Concept | Where It Appears | Why It Matters |
|---|---|---|
| Dense vector embeddings | Phase 1 | How machines represent image "meaning" as numbers |
| Cosine similarity | Phase 1–2 | How to measure closeness in high-dimensional space |
| Approximate nearest neighbor (ANN) | Phase 2 | Why exact search is too slow at scale, and the accuracy/speed tradeoff |
| FAISS index types (Flat vs IVF vs HNSW) | Phase 2 | Core ANN tradeoffs — this is the heart of vector databases |
| Confidence calibration | Phase 3 | Why raw similarity scores mislead, and how to turn them into risk labels |
| Online learning | Phase 4 | How to update a model/index from live user signals without full retraining |
| Write-heavy cache invalidation | Phase 4–5 | How writes break read-optimized structures (opposite of TTL caching) |
| Task queues | Phase 5 | Why long-running jobs must leave the request/response cycle |

---

## Component Map

```
visual-product-authenticity-checker/
│
├── embeddings/              # Phase 1 — The brain
│   ├── model.py             #   Load CLIP, generate vectors
│   ├── preprocess.py        #   Resize, normalize, tensor conversion
│   └── cache.py             #   Don't re-embed the same image twice
│
├── index/                   # Phase 2 — The memory
│   ├── faiss_store.py       #   Build, query, save, load FAISS index
│   ├── metadata_store.py    #   SQLite: map vector ID → image URL, product info
│   └── builder.py           #   Batch-index a folder of reference images
│
├── scorer/                  # Phase 3 — The judgment
│   ├── similarity.py        #   Cosine distance computation
│   ├── calibrator.py        #   Map distance → probability → risk label
│   └── explainer.py         #   Surface the closest matching reference images
│
├── feedback/                # Phase 4 — The learning
│   ├── collector.py         #   Accept confirm/reject signals from user
│   ├── updater.py           #   Add confirmed samples to the right index
│   └── drift_detector.py    #   Alert when feedback patterns shift (model drift)
│
├── jobs/                    # Phase 5 — The background engine
│   ├── tasks.py             #   Celery task definitions
│   ├── scheduler.py         #   Periodic re-index triggers
│   └── worker.py            #   Worker entrypoint
│
├── api/                     # Phase 6 — The interface
│   ├── routes.py            #   FastAPI endpoints: /check, /index, /feedback
│   ├── schemas.py           #   Pydantic request/response models
│   └── middleware.py        #   Auth, rate limiting
│
└── notes/                   # This folder — learning docs
```

---

## Data Flow: Step by Step

### Query (is this product genuine?)

1. API receives an image URL
2. Image is fetched and decoded to a PIL Image
3. Preprocessor resizes to 224×224, normalizes pixel values to the range CLIP expects
4. Embedding model runs a forward pass and returns a 512-dimensional float vector
5. FAISS index runs a Top-K nearest neighbor search against all reference vectors
6. Returns K closest vectors with their cosine distances
7. Confidence scorer converts those distances into a risk score (0 = clearly genuine, 1 = clearly fake)
8. Response includes: risk score, risk label, K closest reference images as evidence

### Index (add a known-authentic image)

1. Reference image is preprocessed the same way as above
2. Embedding model generates a vector
3. Vector is added to FAISS index; a new integer ID is assigned
4. Metadata store maps that ID → `{url, product_name, brand, date_added}`
5. FAISS index is persisted to disk (`.faiss` file)

---

## Technology Choices Explained

### Why CLIP (not ResNet or ViT alone)?

CLIP (Contrastive Language-Image Pretraining) was trained on 400M image-text pairs from the web. It learned to encode images and
text into the *same* embedding space, which means its image representations are rich with semantic meaning. For products, this
matters: a CLIP embedding of a fake Nike logo will land far from authentic Nike logos because it learned from actual product
photographs and descriptions. ResNet produces good features too, but they're more generic and less aligned to "product identity."

ViT (Vision Transformer) is comparable to CLIP in quality but requires fine-tuning on domain-specific data to beat CLIP
out-of-the-box. CLIP is the right default for a cold-start system.

### Why FAISS (not Pinecone, Weaviate, Chroma)?

FAISS is a local C++ library from Meta. It runs entirely on your machine — no API calls, no latency, no cost per query. For a
learning project, this is ideal: you can inspect and manipulate the index directly, which makes the internals visible. Cloud vector
databases abstract all the interesting parts away.

### Why SQLite for metadata (not PostgreSQL)?

FAISS stores vectors as flat arrays and identifies them by integer position. It has no concept of metadata. You need a separate
store that maps `faiss_id → {url, product, brand}`. SQLite is a single file, zero-config, and perfectly sufficient for thousands
to millions of records. PostgreSQL would add operational overhead with no benefit at this scale.

### Why Celery + Redis for background jobs?

When a user triggers a re-indexing operation (which may take minutes), you cannot block the HTTP response waiting for it. Celery is
a task queue: the API enqueues a job ID, returns immediately, and a background worker picks it up. Redis acts as the message broker
(where tasks are stored before pickup) and the results backend (where task status is written after completion). You already have
Redis from the trending pipeline, so extending it for task queuing is zero additional infrastructure.

---

## FAISS Index Types — The Core Tradeoff

This is the most conceptually important part of the system. Understand this before Phase 2.

```
IndexFlatL2 / IndexFlatIP
  ├── What it does: Exhaustive search. Compares your query to every single vector.
  ├── Accuracy: 100% (exact)
  ├── Speed: O(n) — slow past ~100k vectors
  └── When to use: Small indexes, ground truth validation, learning baseline

IndexIVFFlat
  ├── What it does: Clusters vectors into Voronoi cells. At search time, only
  │   searches the nearest N clusters instead of everything.
  ├── Accuracy: ~95-99% (approximate, some true neighbors missed)
  ├── Speed: Much faster — search only nprobe clusters, not all
  ├── Requires: Training step to learn cluster centroids
  └── When to use: 100k–10M vectors, production-grade speed

IndexHNSWFlat
  ├── What it does: Builds a hierarchical graph. Search traverses the graph
  │   greedily rather than scanning cells.
  ├── Accuracy: Very high (~99%)
  ├── Speed: Extremely fast, especially on CPU
  ├── Memory: Higher memory usage than IVF
  └── When to use: When you need low latency without a GPU

For this project:
  - Start with IndexFlatL2 (Phase 2, baseline)
  - Add IndexIVFFlat (Phase 2, advanced)
  - Compare recall and latency — that comparison IS the learning
```

---

## Confidence Scoring — Turning Distance Into Risk

Raw cosine similarity gives you a number like `0.87`. What does that mean? Is `0.87` genuine or suspicious? It depends on the
distribution of your index.

The calibration process:
1. Run your query against the index and collect the Top-K cosine similarities
2. Compute a summary statistic (e.g., mean of top-3 similarities)
3. Map that summary through a calibration function:
   - Threshold-based: `if mean_sim > 0.90: genuine; elif > 0.75: suspicious; else: fake`
   - Sigmoid-based: `risk = 1 / (1 + exp(k * (sim - threshold)))` — smoother, adjustable
4. The thresholds come from looking at known-genuine and known-fake examples and finding the separating boundary

The key insight: **cosine similarity is not a probability**. Calibration is what turns a geometric measurement into a human-readable
confidence score.

---

---

# Implementation Phases

---

## Phase 1 — Embedding Pipeline
**Status: `NOT STARTED`**

**What you're building:** The layer that converts any product image into a fixed-size numerical fingerprint (embedding vector).

**Concepts taught:**
- How neural networks encode images as vectors
- Why preprocessing matters (garbage in, garbage out)
- Embedding caching to avoid redundant computation

**Modules:**
- `embeddings/preprocess.py` — Fetch image from URL, decode to PIL, resize to 224×224, apply CLIP normalization
- `embeddings/model.py` — Load `openai/clip-vit-base-patch32` via HuggingFace, run inference, return L2-normalized 512-dim vector
- `embeddings/cache.py` — Hash image URL → check Redis → if miss, embed and store result with TTL

**Key decisions to make:**
- Which CLIP variant? `clip-vit-base-patch32` (faster, smaller) vs `clip-vit-large-patch14` (more accurate, 2× slower)
- Cache invalidation: when should a cached embedding expire? (product image changed, model updated)

**Done when:** `embed(image_url)` returns a consistent 512-dim numpy array for any product URL.

---

## Phase 2 — FAISS Index (Vector Store)
**Status: `NOT STARTED`**

**What you're building:** The "memory" of the system — a searchable store of reference image embeddings.

**Concepts taught:**
- Exact vs approximate nearest neighbor search
- The IndexFlat → IndexIVF progression (build with flat, graduate to IVF)
- How FAISS separates vectors from metadata (and why that forces a companion store)

**Modules:**
- `index/faiss_store.py` — Wrap FAISS index: add vectors, search Top-K, save to `.faiss` file, load from disk
- `index/metadata_store.py` — SQLite table: `(faiss_id INTEGER, url TEXT, product_name TEXT, brand TEXT, added_at TIMESTAMP)`
- `index/builder.py` — Given a directory of reference images, embed all and insert into index + metadata store

**Key decisions to make:**
- IndexFlatL2 vs IndexFlatIP (Euclidean vs inner product — with L2-normalized vectors, they're equivalent but understanding why is the lesson)
- When to transition from Flat to IVF: benchmark at 1k, 10k, 100k vectors and measure latency

**Done when:** `search(query_vector, k=5)` returns 5 most similar reference images with their cosine similarities.

---

## Phase 3 — Confidence Scorer
**Status: `NOT STARTED`**

**What you're building:** The layer that translates raw similarity scores into a human-readable risk assessment.

**Concepts taught:**
- Why raw similarity is not a probability
- Calibration: fitting thresholds to your actual data distribution
- Explainability: surfacing evidence (closest matches) alongside the verdict

**Modules:**
- `scorer/similarity.py` — Take Top-K FAISS results, compute weighted mean cosine similarity summary
- `scorer/calibrator.py` — Define thresholds (start with manual, add sigmoid calibration in advanced step); return `{score: float, label: "GENUINE"|"SUSPICIOUS"|"COUNTERFEIT"}`
- `scorer/explainer.py` — Package the top-3 matching reference images + their similarity scores as visual evidence

**Key decisions to make:**
- Where do thresholds come from? (This motivates building a labeled test set)
- How do you handle products with very few reference images? (Low-confidence output rather than false certainty)

**Done when:** `score(query_url)` returns `{risk_score, label, evidence_images}` end-to-end.

---

## Phase 4 — Feedback Loop (Online Learning)
**Status: `NOT STARTED`**

**What you're building:** The mechanism that lets the system improve from user corrections — your first online learning component.

**Concepts taught:**
- Online learning: updating a model/index incrementally from live signals (vs batch retraining)
- Write-heavy cache invalidation: adding vectors to FAISS invalidates query results cached in Redis
- Positive/negative signal separation: confirmed genuine → reference index; confirmed fake → counterfeit index

**Modules:**
- `feedback/collector.py` — Accept `{listing_id, verdict: "genuine"|"fake", image_url}` via API; persist to `feedback_log` table
- `feedback/updater.py` — On "confirmed genuine": embed image, add to reference FAISS index + metadata; on "confirmed fake": add to a separate `known_fake` index. Invalidate affected Redis cache keys.
- `feedback/drift_detector.py` — Monitor rolling feedback ratio: if fake-confirmation rate jumps suddenly, alert (possible adversarial campaign or model drift)

**Key decisions to make:**
- Should every single feedback signal immediately update the index? (Yes for learning; dangerous in production — adversarial users could poison the index)
- How do you handle conflicting feedback? (Same image confirmed genuine by one user, fake by another)

**Done when:** Confirming a listing as genuine adds its embedding to the reference index and future similar listings score higher.

---

## Phase 5 — Background Jobs (Task Queue)
**Status: `NOT STARTED`**

**What you're building:** The async engine that handles work that's too slow for the request/response cycle.

**Concepts taught:**
- Why blocking HTTP handlers on slow work is bad (tied-up workers, timeouts, poor UX)
- Task queues: producer/consumer pattern with Redis as the broker
- Idempotency: what happens if a re-index job runs twice? (It should be safe)

**Modules:**
- `jobs/tasks.py` — Celery task definitions: `reindex_all()`, `batch_embed(image_urls)`, `check_index_health()`
- `jobs/scheduler.py` — Celery Beat schedule: trigger `reindex_all()` nightly, `check_index_health()` hourly
- `jobs/worker.py` — Celery worker entrypoint; configure with Redis broker URL from environment

**Key decisions to make:**
- How do you avoid re-indexing the same image that was already indexed? (Deduplication via URL hash in metadata store)
- Celery vs RQ (Redis Queue)? RQ is simpler; Celery is more powerful and has Beat scheduling built in. Use Celery.

**Done when:** A background re-index job runs without blocking any API response, and job status is queryable by ID.

---

## Phase 6 — API Layer
**Status: `NOT STARTED`**

**What you're building:** The HTTP interface that wires all the above components together.

**Concepts taught:**
- Request/response design: when to return synchronously vs return a job ID
- Input validation: pydantic schemas catch bad input before it reaches your logic
- Separation of concerns: routes are thin wrappers — business logic lives in the modules above

**Endpoints:**

```
POST /check
  Body: { image_url: str }
  Returns: { risk_score: float, label: str, evidence: [...] }
  Sync — fast enough for real-time use (< 200ms if cache warm)

POST /index
  Body: { image_url: str, product_name: str, brand: str }
  Returns: { job_id: str }
  Async — enqueues background embedding + indexing job

POST /feedback
  Body: { listing_id: str, verdict: "genuine"|"fake", image_url: str }
  Returns: { status: "accepted" }
  Sync — fast write to feedback_log, triggers async index update

GET /jobs/{job_id}
  Returns: { status: "pending"|"running"|"done"|"failed" }
  Lets client poll for async job completion
```

**Done when:** All four endpoints return correct responses and async jobs complete in the background.

---

## Learning Checkpoints

Before moving to the next phase, answer these questions in your own words. If you can't, re-read the phase.

**After Phase 1:**
- What does an embedding vector represent? Why is it useful to represent images this way?
- Why do we L2-normalize vectors before indexing?

**After Phase 2:**
- What's the difference between exact search and approximate nearest neighbor?
- Why does FAISS need a companion metadata store?

**After Phase 3:**
- Why can't you use cosine similarity directly as a confidence score?
- What does calibration mean in this context?

**After Phase 4:**
- What is the difference between batch retraining and online learning?
- Why does adding a vector to FAISS require invalidating related cache entries?

**After Phase 5:**
- Why shouldn't slow jobs run inside an HTTP handler?
- What does "idempotent task" mean, and why does it matter for a re-index job?

**After Phase 6:**
- Why does `/index` return a job ID instead of a result?
- What's the contract between the API layer and the business logic modules?

---

*Last updated: 2026-06-02 | Status: Pre-implementation (architecture complete)*
