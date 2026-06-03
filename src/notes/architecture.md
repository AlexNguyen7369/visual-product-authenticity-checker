# Visual Product Authenticity Checker — Architecture & Implementation Guide

> **Purpose of this document:** A learning-first breakdown of every system component and why it's built the way it is. Each phase
> teaches a concept. Read this before touching code.

---

## What This System Does (Plain English)

You hold a physical sneaker up to a USB webcam. You press a key to capture a frame. The system answers: *"Is this a real pair, or a fake?"*

It does this in four steps:

1. **See** — The webcam captures a frame. The system isolates the shoe from the messy real-world background (lighting, angle, clutter).
2. **Identify** — A vision-language model looks at the frame and figures out *what shoe this is supposed to be* (e.g., "Nike Air Jordan 1 Retro High OG 'Chicago' 2015"). OCR pulls the SKU code off the tongue label if visible.
3. **Look up the truth** — The system pulls official reference photos and known counterfeit indicators for that exact SKU from brand and reseller pages (Nike.com, StockX, GOAT).
4. **Compare and decide** — The vision model compares the captured frame against the scraped references across three independent pillars (logo/stitching, sole/silhouette, serial number) and returns a verdict with evidence.

The project is implemented **twice** — once on the edge (your laptop) and once in the cloud (AWS) — so you learn both stacks.

---

## The Two Implementation Paths

The same problem, two different stacks. The CV pipeline and verdict logic are identical; what changes is **where the work happens** and **which services run it**.

| Aspect | Edge Version | Cloud Version |
|---|---|---|
| Primary learning goal | Computer vision fundamentals | Cloud architecture on AWS |
| Capture device | USB webcam on laptop | USB webcam on laptop (capture is always local — you need a physical camera) |
| Frame processing | Local Python: OpenCV + Tesseract | AWS Lambda + Rekognition |
| Product identification | Direct call to Gemini Vision API | Lambda → Gemini Vision API |
| Reference lookup | Gemini Google Search grounding (or custom scraper) | Same, called from Lambda |
| Cache | Local Redis (Docker) | ElastiCache for Redis |
| Persistent storage | SQLite | DynamoDB |
| Orchestration | A single Python script + Celery worker | API Gateway → Lambda → S3 events |
| What you learn | OpenCV pipeline, OCR tuning, prompt engineering, scraping | AWS service composition, IAM, event-driven design, managed-services tradeoffs |

**Build the edge version first.** It's the shortest path from "no code" to "working verdict." The cloud version is a port — you rewrite the orchestration layer while keeping the core logic.

---

## The Three Pillars of Authenticity

Every verdict is based on cross-checking three independent signals. If they agree, the verdict is high-confidence. If they disagree, the system flags `SUSPICIOUS` and surfaces the conflict.

```
┌──────────────────────────────────────────────────────────────┐
│  Pillar 1: Logo + Stitching + Materials                      │
│    - Logo proportions, font, placement                       │
│    - Stitch spacing, density, thread color                   │
│    - Leather grain, suede nap, color accuracy                │
│  How: Gemini Vision compares captured crop ↔ reference crop  │
├──────────────────────────────────────────────────────────────┤
│  Pillar 2: Sole Pattern + Silhouette                         │
│    - Tread geometry, midsole shape, heel cup curve           │
│    - Counterfeit factories rarely match the exact mold       │
│  How: Gemini Vision side-by-side comparison                  │
├──────────────────────────────────────────────────────────────┤
│  Pillar 3: Serial Number / SKU (OCR)                         │
│    - Read code from tongue label or insole                   │
│    - Validate format (length, prefix, check digit)           │
│    - Confirm the code is real (matches brand DB)             │
│  How: Tesseract (edge) or Rekognition DetectText (cloud)     │
└──────────────────────────────────────────────────────────────┘

Verdict logic:
  3/3 agree authentic → GENUINE
  3/3 agree fake     → COUNTERFEIT
  Mixed              → SUSPICIOUS (return evidence, ask human)
```

---

## Edge Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        EDGE — QUERY PATH                          │
│                                                                   │
│  USB Webcam ──► OpenCV VideoCapture ──► Manual Trigger (keypress) │
│                                              │                    │
│                                              ▼                    │
│                                      Frame Preprocessor           │
│                                  (denoise, white-balance,         │
│                                   crop to product, resize)        │
│                                              │                    │
│                                              ▼                    │
│                                       Image Hash (sha256)         │
│                                              │                    │
│                                              ▼                    │
│                                      Redis Cache Check            │
│                                       (hit → return verdict)      │
│                                              │ miss               │
│                              ┌───────────────┴───────────────┐    │
│                              ▼                               ▼    │
│                      Tesseract OCR                  Gemini Vision │
│                      (SKU / serial code)            (identify SKU)│
│                              │                               │    │
│                              └───────────────┬───────────────┘    │
│                                              ▼                    │
│                                  Identified product               │
│                                  + extracted serial               │
│                                              │                    │
│                                              ▼                    │
│                                  Gemini + Google Search           │
│                                  Grounding (reference lookup)     │
│                                              │                    │
│                                              ▼                    │
│                                  Official reference images        │
│                                  + known counterfeit indicators   │
│                                              │                    │
│                                              ▼                    │
│                                  Gemini Vision (cross-compare)    │
│                                  → 3-pillar scoring               │
│                                              │                    │
│                                              ▼                    │
│                              ┌───────────────┴───────────────┐    │
│                              │  GENUINE / SUSPICIOUS /       │    │
│                              │  COUNTERFEIT + evidence       │    │
│                              └───────────────┬───────────────┘    │
│                                              ▼                    │
│                                  Redis (cache verdict, TTL 24h)   │
│                                  SQLite (append to verdict log)   │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                       EDGE — FEEDBACK LOOP                        │
│                                                                   │
│   CLI prompt: "Was this verdict correct? [y/n]"                   │
│                       │                                           │
│                       ▼                                           │
│              SQLite feedback table                                │
│              (image_hash, predicted, actual, timestamp)           │
│                       │                                           │
│                       ▼                                           │
│              Cache invalidator                                    │
│              (overwrite Redis entry with corrected verdict)       │
└──────────────────────────────────────────────────────────────────┘
```

**Edge stack:**
- **Python 3.11+** as the runtime
- **OpenCV (`cv2`)** for webcam capture and frame preprocessing
- **Pillow** for image encoding before API calls
- **Tesseract** (via `pytesseract`) for offline OCR of serial codes
- **Google GenAI SDK** (`google-genai`, imported as `google.genai`) for Gemini calls — note this replaces the now-EOL `google-generativeai` package
- **Redis** (Docker container) for verdict cache
- **SQLite** for verdict + feedback log
- **Playwright** (optional, advanced) if you want a custom scraper instead of Gemini grounding

---

## Cloud Architecture (AWS)

```
┌──────────────────────────────────────────────────────────────────┐
│                       CLOUD — QUERY PATH                          │
│                                                                   │
│  USB Webcam ──► Local Python capture client                       │
│                       │ (manual keypress trigger)                 │
│                       ▼                                           │
│                Local preprocessing (resize, hash)                 │
│                       │                                           │
│                       ▼                                           │
│                HTTPS POST → API Gateway                           │
│                       │ (frame + hash + auth)                     │
│                       ▼                                           │
│                Lambda: cache_check                                │
│                       │                                           │
│                       ├──► ElastiCache Redis (hit → return)       │
│                       │                                           │
│                       ▼  miss                                     │
│                S3: PutObject (frames/{hash}.jpg)                  │
│                       │                                           │
│                       ▼ (S3 Event)                                │
│                Lambda: process_frame                              │
│                       │                                           │
│              ┌────────┴────────┐                                  │
│              ▼                 ▼                                  │
│      Rekognition          Rekognition                             │
│      DetectText           DetectLabels                            │
│      (read SKU)           (confirm "Footwear")                    │
│              │                 │                                  │
│              └────────┬────────┘                                  │
│                       ▼                                           │
│              Lambda: identify_product                             │
│              → Gemini Vision API (identify SKU)                   │
│                       │                                           │
│                       ▼                                           │
│              Lambda: lookup_reference                             │
│              → Gemini + Google Search Grounding                   │
│                       │                                           │
│                       ▼                                           │
│              Lambda: cross_compare                                │
│              → Gemini Vision (3-pillar verdict)                   │
│                       │                                           │
│                       ▼                                           │
│              DynamoDB: write verdict + evidence                   │
│              ElastiCache: cache verdict (TTL 24h)                 │
│                       │                                           │
│                       ▼                                           │
│              API Gateway response → local client                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                      CLOUD — FEEDBACK LOOP                        │
│                                                                   │
│   Local client → API Gateway → Lambda: record_feedback            │
│                       │                                           │
│                       ▼                                           │
│              DynamoDB: feedback table                             │
│              ElastiCache: overwrite cached verdict                │
└──────────────────────────────────────────────────────────────────┘
```

**Cloud stack:**
- **Local client**: same Python capture code as edge, but instead of running the pipeline locally, it POSTs to API Gateway
- **API Gateway**: REST endpoint for `/check`, `/feedback`, `/health`
- **AWS Lambda**: each pipeline step is its own function (cache check, process, identify, lookup, compare, feedback) — composable, separately scalable
- **S3**: frame storage with event-driven processing
- **Rekognition**: managed CV for `DetectText` (OCR) and `DetectLabels` (sanity-check it's a shoe). Optional `Custom Labels` for trained brand/logo detection
- **Gemini API**: called from Lambda over HTTPS (Gemini is *not* on Bedrock — it stays an external dependency)
- **ElastiCache for Redis**: managed cache, same role as local Redis on edge
- **DynamoDB**: verdict log + feedback table (key-value access pattern, no joins needed)
- **IAM**: per-Lambda execution roles, principle of least privilege

**Why Rekognition + Gemini together** — Rekognition does the deterministic, structured CV (OCR, labels) cheaply and at low latency. Gemini does the reasoning (identification, cross-comparison, verdict explanation). Rekognition can't say "is this fake?" — it labels. Gemini can't reliably OCR a curved tongue label — it hallucinates. Use each for what it's good at.

---

## Core Concepts You'll Learn (and Where)

| Concept | Where It Appears | Why It Matters |
|---|---|---|
| Vertical slice / walking skeleton | Phase 0 | Prove the layers connect before deepening any one of them |
| Dependency isolation (venv) | Phase 0 | Per-project package trees; the seed of reproducible builds |
| Image serialization (encode + base64) | Phase 0 | Why in-memory pixels must become bytes to cross a network |
| Request/response lifecycle & latency | Phase 0 | Where time goes in a service call; retries, timeouts, rate limits |
| Webcam capture pipeline | Phase 1 | The CV "hello world" — frames, codecs, buffering |
| Image preprocessing | Phase 1 | Real-world lighting and angles wreck downstream accuracy |
| Optical Character Recognition (OCR) | Phase 2 | Reading text from images — the core of structured CV |
| Vision-language models | Phase 2, 4 | How modern multimodal AI reasons about images |
| Prompt engineering for verdicts | Phase 4 | Asking an LLM the right structured question matters as much as the model |
| Web scraping vs LLM grounding | Phase 3 | When to write a scraper vs let an AI do the lookup |
| Read-through caching | Phase 5 | Avoid paying for the same Gemini call twice |
| Cache invalidation on feedback | Phase 5 | Why writes break read-optimized structures |
| Event-driven cloud architecture | Phase 6 | S3 events, Lambda triggers, distributed pipelines |
| Managed CV vs custom CV | Phase 6 | Rekognition's tradeoffs against rolling your own |
| IAM and least privilege | Phase 6 | The cloud security mindset |

---

## Component Map

```
visual-product-authenticity-checker/
│
├── capture/                # Phase 1 — The eyes
│   ├── webcam.py           #   OpenCV VideoCapture wrapper, keypress trigger
│   ├── preprocess.py       #   Denoise, white-balance, crop, resize
│   └── hash.py             #   sha256 of canonicalized frame bytes
│
├── identify/               # Phase 2 — The naming
│   ├── ocr.py              #   Tesseract wrapper for SKU/serial extraction
│   ├── gemini_vision.py    #   Gemini Vision client (identify product)
│   └── sku_validator.py    #   Format + check-digit validation per brand
│
├── reference/              # Phase 3 — The truth source
│   ├── grounding.py        #   Gemini Google Search grounding lookup
│   ├── scraper.py          #   (optional) Playwright fallback scraper
│   └── reference_cache.py  #   Cache reference dossiers per SKU
│
├── verdict/                # Phase 4 — The judgment
│   ├── pillars.py          #   Score each of the 3 pillars independently
│   ├── compare.py          #   Gemini cross-compare prompt + parser
│   └── synthesize.py       #   Combine pillar scores → final label
│
├── cache/                  # Phase 5 — The memory
│   ├── redis_client.py     #   Read-through cache for verdicts
│   ├── feedback.py         #   Persist user confirm/reject
│   └── invalidate.py       #   Overwrite cached verdict on feedback
│
├── cloud/                  # Phase 6 — The AWS port
│   ├── lambdas/            #   One folder per Lambda function
│   ├── infra/              #   Terraform or CDK for AWS resources
│   └── client.py           #   Local capture client that posts to API GW
│
└── notes/                  # This folder — learning docs
    ├── architecture.md     # This document
    └── phase{N}-*.md       # One per phase, written before code
```

The same `capture/`, `identify/`, `reference/`, `verdict/`, and `cache/` modules are used by **both** the edge entrypoint and the cloud Lambdas. Only the orchestration is different.

---

## Data Flow: Step by Step

### Query (is this sneaker genuine?) — Edge

1. User presses `SPACE` in the live webcam window
2. OpenCV grabs the current frame as a NumPy array
3. Preprocessor denoises, white-balances, crops the product, resizes to 1024×1024
4. Compute sha256 of the canonical bytes → cache key
5. Check Redis: if hit and not expired, return cached verdict immediately
6. On miss:
   - Run Tesseract on the frame to extract any visible serial/SKU text
   - Send the frame to Gemini Vision with a prompt: *"Identify this shoe. Return brand, model, colorway, year, SKU."*
7. Use the identified SKU to query Gemini with Google Search grounding: *"Find official product page and known counterfeit indicators for SKU XYZ."*
8. Send the captured frame + retrieved reference images to Gemini Vision with the 3-pillar comparison prompt
9. Parse the structured verdict (JSON), compute final label
10. Write verdict to Redis (TTL 24h) and append to SQLite log
11. Display verdict + evidence (top differences highlighted) in the terminal/window
12. Prompt: *"Was this correct? [y/n]"* — write the answer to the feedback table

### Query — Cloud

Same conceptual steps, but:
- Steps 1–4 happen on the local client
- Step 5 is a Lambda call (cache_check)
- Step 6's OCR is `Rekognition DetectText`, identification is Lambda → Gemini
- Step 7 is Lambda → Gemini grounding
- Step 8 is Lambda → Gemini
- Steps 10–12 write to DynamoDB and ElastiCache

---

## Technology Choices Explained

### Why Gemini (not Claude or GPT-4V)?

Gemini's free tier gives 1,500 requests/day on Flash, which is enough for a learning project that may make dozens of identification + comparison calls per session. Claude and GPT-4V are pay-per-call from the first request. Gemini also has **built-in Google Search grounding**, which collapses identification + reference lookup into a single API call instead of a separate scraping step. For a sneaker authenticity project specifically, Gemini's lineage from Google Lens gives it strong product recognition.

The codebase wraps the LLM call behind a `VisionClient` interface (`identify`, `lookup_reference`, `compare`), so you can swap to Claude or GPT-4V later for comparison.

### Why OpenCV for capture (not raw v4l2 or DirectShow)?

OpenCV's `VideoCapture` abstracts platform differences (Windows DirectShow, macOS AVFoundation, Linux V4L2). The same code reads from any USB webcam. It also bundles the preprocessing primitives (denoise, color conversion, resize) so the whole capture-and-prepare layer is one dependency.

### Why Tesseract on edge but Rekognition in cloud?

On edge, Tesseract is free, offline, and good enough for a printed serial on a clean tongue label after preprocessing. In the cloud, Rekognition `DetectText` is already deployed and integrated with the AWS event flow — using Tesseract in Lambda would mean packaging a binary and managing its layer. The contrast is the lesson: **on edge you assemble your own pipeline; in the cloud you compose managed services**.

### Why Gemini Google Search grounding (not a custom scraper)?

A custom scraper for Nike.com / StockX / GOAT works but is brittle — selectors change, anti-bot measures escalate, and you'll spend more time maintaining it than learning CV. Gemini's grounding tool issues real Google searches under the hood and returns structured results with citations. **A custom Playwright scraper is included as an optional Phase 3 extension** so you can compare both approaches and see the tradeoff explicitly.

### Why Redis for cache (not just SQLite)?

A SHA-256 hash → verdict lookup needs sub-millisecond reads. Redis is purpose-built for this access pattern; SQLite would technically work but would block on the file. Redis is also the path to learning ElastiCache for the cloud port — the API is identical.

### Why DynamoDB (not RDS) in the cloud?

Access patterns are key-value: `get_verdict(image_hash)`, `get_feedback(image_hash)`, `list_feedback(user_id)`. No joins, no complex queries. DynamoDB scales to zero, has no idle cost, and integrates natively with Lambda. RDS would add VPC complexity and idle costs for no benefit.

### Why two separate Lambdas (cache_check and process_frame) instead of one?

If the cache hits, you skip S3, Rekognition, and Gemini entirely — paying ~10ms of Lambda warm time instead of seconds. Splitting them lets the cheap path stay cheap. The cold path is naturally asynchronous via the S3 event.

---

## Implementation Phases

---

## Phase 0 — Bootstrap & Vertical Slice (Edge)
**Status: `NOT STARTED`**

**What you're building:** The thinnest possible end-to-end thread that proves the whole stack is wired up *before* you invest in any one layer. Three baby steps, each a few lines of code:

1. **Environment smoke test** — import every dependency and print its version. If this fails, nothing else can run.
2. **Capture smoke test** — open the webcam, show a live preview, grab one frame on `SPACE`, and write it to disk.
3. **Detection smoke test** — send that one frame to Gemini and ask a single yes/no question: *"Is there a sneaker in this image?"*

That's it. No preprocessing, no OCR, no cache, no verdict. The goal is a **walking skeleton**: webcam → frame → model → answer, running on your machine, in under ~50 lines total. Every later phase is "make one of these three steps better," which is why getting the skeleton right matters more than getting any single step complete.

> **Want to build up to this gradually?** See `roadmap.md` — a ladder of ~13 tiny do-it-by-hand modules (each with test cases and a debugging drill) that hand-build every piece of this skeleton from first principles.

> **Why a vertical slice first (the system-design point).** You can build a system *horizontally* (finish all of capture, then all of identification, then all of comparison) or *vertically* (one thin thread through every layer, then thicken it). Horizontal builds hide integration risk until the end — you discover the webcam outputs the wrong color format *after* you've written 2,000 lines that assume otherwise. A vertical slice surfaces those interface mismatches on day one, when they're cheap. In interviews this is the "walking skeleton" / "tracer bullet" pattern, and it's the same instinct behind a health-check endpoint: prove the pipes connect before you pump anything through them.

**Concepts taught:**
- Dependency isolation and why a virtualenv exists at all
- What a video frame *actually is* in memory
- The blocking capture loop and frame buffering
- Encoding an in-memory image into bytes that can cross a network
- The request/response lifecycle of a model API call, and where latency comes from
- Secrets handling (12-factor config)

---

### Step 0.1 — Environment smoke test

**What runs:** A script that does nothing but `import cv2, numpy, PIL, google.genai, dotenv` and prints each version.

**What's actually happening (and why a venv):** When you `pip install opencv-python`, pip downloads a *wheel* (a zip of precompiled `.pyd`/`.so` binaries — OpenCV is C++ under the hood) and unpacks it into the venv's `site-packages/` directory. The venv is just a folder with its own `python.exe` and its own `site-packages`; activating it puts that `python.exe` first on your `PATH`. So `import cv2` resolves to *this project's* copy, not a global one. The interview framing: a venv gives you **dependency isolation** — Project A's `numpy 2.x` can't break Project B's `numpy 1.x`, because they read from different `site-packages` trees. `requirements.txt` is the *declared* set; `pip freeze` is the *resolved, pinned* set (every transitive dependency at an exact version) — the distinction between "what I asked for" and "what actually got installed" is the seed of reproducible builds and, later, lockfiles and immutable container images.

**Done when:** Running the script prints five version strings and exits 0.

---

### Step 0.2 — Capture smoke test

**What runs:** `cv2.VideoCapture(0)` opens the default camera; a loop calls `cap.read()`, shows each frame with `cv2.imshow`, and breaks on a `SPACE` keypress, writing the held frame with `cv2.imwrite`.

**What a frame actually is:** `cap.read()` returns `(ok, frame)` where `frame` is a **NumPy `ndarray` of shape `(height, width, 3)` and dtype `uint8`** — a contiguous block of `H×W×3` bytes in memory, row-major, one byte per color channel (0–255). Two gotchas that bite everyone:
- **Channel order is BGR, not RGB.** OpenCV inherited this from a 1990s Windows bitmap convention. Pillow, Gemini, and almost every ML model expect RGB. Get this wrong and reds/blues swap silently — no error, just wrong answers. You convert with `cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)`.
- **The array is a view over a buffer the driver may reuse.** If you stash `frame` references in a list without copying, later writes can mutate earlier ones.

**The capture loop and buffering (the backend concept):** `cap.read()` is **blocking, synchronous I/O** — your thread parks until the camera driver hands over the next frame, which is why everything in the loop runs at camera cadence (~30 FPS = one frame every ~33 ms). Under the hood the driver maintains a small **frame buffer queue**; if your loop is slower than the camera, you read *stale* frames (the queue backs up) — that's why naive capture feels laggy, and why production code either drains the buffer or sets `CAP_PROP_BUFFERSIZE=1`. `read()` is really `grab()` (pull from the driver) + `retrieve()` (decode into an ndarray); separating them matters when syncing multiple cameras. This is your first concrete encounter with **blocking vs. non-blocking I/O** and **backpressure** — the same ideas that govern message queues and socket servers.

**Done when:** A preview window appears, `SPACE` saves a `.jpg`, and you can open the file and see your shoe.

---

### Step 0.3 — Detection smoke test

**What runs:** Load `GEMINI_API_KEY` from `.env`, read the saved frame, convert BGR→RGB, JPEG-encode it, send it to Gemini with the prompt *"Reply with only YES or NO: is there a sneaker/athletic shoe in this image?"*, and print the answer.

**How the data flows, byte by byte:**

```
ndarray (H×W×3 uint8, BGR, ~6 MB raw for 1080p)
   │  cv2.cvtColor → RGB           (fix channel order)
   ▼
ndarray (RGB)
   │  cv2.imencode('.jpg', ...)    (compress: 6 MB → ~200 KB; DCT, quantization)
   ▼
JPEG bytes
   │  SDK base64-encodes for the JSON body   (+33% size: 3 bytes → 4 ASCII chars)
   ▼
HTTPS POST → Gemini endpoint        (TLS handshake, then request body)
   │  model runs: image → patches → tokens → autoregressive decode
   ▼
HTTPS response (JSON)  →  parse  →  "YES" / "NO"
```

The two transformations worth understanding for interviews:
- **Why encode at all?** A raw ndarray is just bytes in *your* process's memory — meaningless to another machine. To cross a network you need an agreed-upon **serialization format**. JPEG is lossy compression (discrete cosine transform + quantization throws away high-frequency detail your eye barely notices) that shrinks a 1080p frame ~30×. That trade — bandwidth/latency vs. fidelity — is a recurring system-design decision (it's why Phase 1 cares how hard you denoise: over-compression and over-denoising both destroy the fine stitching detail Pillar 1 needs).
- **Why base64 inflates the payload 33%.** JSON is a text protocol; raw binary bytes can collide with control characters. Base64 re-expresses 3 binary bytes as 4 printable ASCII characters so they survive a text channel. The lesson: **the transport dictates the encoding.** (A binary protocol like gRPC/protobuf would skip this tax — a natural "how would you optimize this?" follow-up.)

**The API call as a request/response lifecycle:** This single call is a microcosm of every backend service interaction. Your thread **blocks** on a network round-trip; total latency = TLS setup + upload time (proportional to payload size — hence compression matters) + **model inference time** (the dominant term, often 1–3 s, because the model is generating tokens) + download. Things that *will* go wrong and that production code must handle: timeouts, transient 5xx errors (→ **retry with exponential backoff**), and 429 rate limits (Gemini's free tier is 1,500 req/day — you'll hit this, which is the entire motivation for the Phase 5 cache: *don't pay the network+inference cost twice for the same image*). Notice this step is a **degenerate version of Phase 2's `identify()`** — same encode-and-POST plumbing, just asking "is it a shoe?" instead of "which exact SKU?". That's the scalability thread: Phase 0's yes/no detector *becomes* the Phase 2 identifier by swapping the prompt and parsing richer JSON.

**Secrets handling (12-factor config):** The API key never goes in code or git (`.env` is git-ignored). `python-dotenv` loads it into the process environment at startup, and you read it via `os.environ`. The principle — **config and secrets live in the environment, not the artifact** — is what lets the *identical* code run locally with a `.env` file and in Phase 6 as a Lambda reading the key from AWS Secrets Manager. Same code, different config source.

**Done when:** Holding a sneaker to the camera, pressing `SPACE`, and running the script prints `YES`; pointing at a coffee mug prints `NO`.

---

### How Phase 0 scales into the full project

| Phase 0 baby step | Grows into |
|---|---|
| `VideoCapture` + `imshow` + keypress | Phase 1 capture with denoise/white-balance/crop/resize/hash |
| BGR→RGB + JPEG encode | Phase 1 preprocessing + the canonical bytes that get hashed for the cache key |
| "Is it a sneaker?" Gemini call | Phase 2 `identify()` returning full `{sku, brand, model}` |
| Reading one `.env` key | Phase 6 config sourced from Secrets Manager, same code |
| The blocking single call | Phase 4's three parallel pillar calls; Phase 5's cache that makes the repeat call free |

**Key decisions:**
- Run detection through Gemini (recommended — it's a real vertical slice and reuses the project's primary engine) vs. a local heuristic. A local object detector is rejected for the baby step: COCO-trained models have no "sneaker" class, and standing up a custom-trained detector is a project of its own. The one Gemini call proves the *integration* end-to-end, which is the whole point of Phase 0.
- Where to keep `.env` and confirming it's git-ignored before the first commit.

**Done when:** All three smoke tests pass in sequence on your machine — imports load, the webcam saves a frame, and Gemini correctly answers YES on a sneaker and NO on a non-shoe. You now have a proven skeleton to thicken in Phase 1.

---

## Phase 1 — Webcam Capture & Preprocessing (Edge)
**Status: `NOT STARTED`**

**What you're building:** The eyes. A Python script that opens the USB webcam, shows a live preview, captures a frame on keypress, and prepares it for downstream processing.

**Concepts taught:**
- How a webcam delivers frames (codec, buffering, BGR vs RGB)
- Why preprocessing matters before any model touches the image
- Image hashing for cache keys

**Modules:**
- `capture/webcam.py` — Open `cv2.VideoCapture(0)`, show preview window, listen for SPACE keypress, return the captured frame
- `capture/preprocess.py` — Denoise (`cv2.fastNlMeansDenoisingColored`), white-balance (gray-world), crop to largest contour, resize to 1024×1024
- `capture/hash.py` — sha256 of the canonical-encoded frame bytes

**Key decisions:**
- BGR vs RGB ordering (OpenCV ships BGR; most models expect RGB)
- How aggressively to denoise (too much washes out stitching detail, which Pillar 1 needs)

**Done when:** Pressing SPACE in a live preview window saves a clean, square, denoised 1024×1024 crop of the sneaker, plus its sha256 hash.

---

## Phase 2 — Product Identification (OCR + Vision LLM)
**Status: `NOT STARTED`**

**What you're building:** The naming layer. Given a preprocessed frame, return the exact SKU.

**Concepts taught:**
- OCR strengths and failure modes (curved surfaces, low contrast, font confusion)
- Multimodal LLM prompting for structured output
- Why two signals beat one (OCR + LLM cross-confirm)

**Modules:**
- `identify/ocr.py` — Tesseract wrapper. Pre-crop to the label region, threshold, run OCR, regex out SKU candidates
- `identify/gemini_vision.py` — Call Gemini Vision with a structured-output prompt; parse JSON `{brand, model, colorway, year, sku}`
- `identify/sku_validator.py` — Per-brand format check (Nike SKUs are 6+3 alphanumeric with a dash)

**Key decisions:**
- Trust OCR or LLM first if they disagree? (Suggested: prefer OCR when SKU validates; otherwise LLM)
- How to handle "I don't know" from the LLM (no confident SKU → return EARLY with `UNIDENTIFIED`)

**Done when:** `identify(frame)` returns `{sku, brand, model, confidence}` for any clear sneaker photo.

---

## Phase 3 — Reference Acquisition
**Status: `NOT STARTED`**

**What you're building:** The truth source. Given a SKU, fetch official reference images and known counterfeit indicators.

**Concepts taught:**
- LLM grounding vs traditional scraping
- The cost/brittleness tradeoff of each
- Caching expensive lookups by SKU

**Modules:**
- `reference/grounding.py` — Gemini call with Google Search grounding enabled; prompt asks for official product page URLs and counterfeit-guide URLs; parse cited image URLs
- `reference/scraper.py` *(optional Phase 3.5)* — Playwright scraper for StockX/GOAT as a learning exercise to compare against grounding
- `reference/reference_cache.py` — SKU → dossier lookup in SQLite (dossiers don't change often; TTL 7d)

**Key decisions:**
- How many reference images per SKU? (3–6 covering different angles)
- Source priority (brand > authoritative reseller > forum guides)

**Done when:** `get_reference(sku)` returns `{official_images: [...], counterfeit_indicators: [...]}` for a known SKU.

---

## Phase 4 — Cross-Comparison & Verdict
**Status: `NOT STARTED`**

**What you're building:** The judgment. Given a captured frame and reference dossier, score each pillar and produce a verdict.

**Concepts taught:**
- Structured prompting for explainable AI
- Aggregating multiple independent signals
- When to defer (the SUSPICIOUS label is a feature, not a failure)

**Modules:**
- `verdict/pillars.py` — Three Gemini calls, one per pillar, each returning `{score: 0..1, evidence: str}`
- `verdict/compare.py` — Side-by-side prompting: send the captured frame + reference images, ask for pillar-specific comparison
- `verdict/synthesize.py` — Combine pillar scores into final label (`GENUINE` / `SUSPICIOUS` / `COUNTERFEIT`) with thresholds

**Key decisions:**
- Run pillars in parallel (faster, more API calls) or sequential (cheaper, exit early on strong signal)?
- How to weight pillars (serial number disagreeing is a stronger fake signal than slight stitching variance)

**Done when:** `verdict(frame, reference)` returns `{label, score, pillar_breakdown, evidence}`.

---

## Phase 5 — Cache & Feedback Loop
**Status: `NOT STARTED`**

**What you're building:** The memory. Make repeat captures instant, and let the user correct wrong verdicts.

**Concepts taught:**
- Read-through caching with TTL
- Cache invalidation under writes (the opposite pattern from read-only caches)
- Persistent feedback that survives across runs

**Modules:**
- `cache/redis_client.py` — `get(hash)`, `set(hash, verdict, ttl=86400)`, namespace prefix `verdict:`
- `cache/feedback.py` — SQLite table `(image_hash, predicted_label, actual_label, user_note, timestamp)`; append-only
- `cache/invalidate.py` — On feedback, overwrite the Redis entry with the corrected verdict (TTL 30 days for corrected entries)

**Key decisions:**
- TTL strategy: short for predictions, long for human-corrected verdicts
- Whether to use the feedback log to improve Phase 4 prompts later (yes — extract patterns and add to the comparison prompt as examples)

**Done when:** A repeat capture of the same shoe returns instantly from cache, and a user correction is reflected on the next capture.

---

## Phase 6 — Cloud Port to AWS
**Status: `NOT STARTED`**

**What you're building:** The same pipeline, re-orchestrated on AWS managed services.

**Concepts taught:**
- Decomposing a monolithic pipeline into Lambdas
- Event-driven architecture (S3 events, API Gateway triggers)
- Managed CV (Rekognition) vs custom CV
- IAM least privilege
- Why "the same thing in the cloud" is never quite the same thing

**Modules:**
- `cloud/lambdas/cache_check/` — Fast path, ElastiCache lookup, returns immediately on hit
- `cloud/lambdas/process_frame/` — Triggered by S3 event, calls Rekognition + Gemini, writes to DynamoDB
- `cloud/lambdas/feedback/` — Records user correction, invalidates cache
- `cloud/client.py` — Local capture client that POSTs frames to API Gateway
- `cloud/infra/` — Terraform or AWS CDK: VPC, ElastiCache subnet group, DynamoDB tables, Lambda functions, API Gateway, IAM roles

**Key decisions:**
- Terraform vs CDK (CDK if you want Python everywhere; Terraform if you want broader transferable knowledge)
- Lambda packaging: zip vs container image (container if you need Playwright or large deps)
- Cold start mitigation (provisioned concurrency for `cache_check`, accept cold starts elsewhere)

**Done when:** The local client can POST a frame to API Gateway and receive the same verdict the edge version produces, with cache and feedback working through AWS services.

---

## Learning Checkpoints

Before moving to the next phase, answer these questions in your own words. If you can't, re-read the phase notes.

**After Phase 0:**
- Why does a vertical slice surface integration bugs earlier than building one layer at a time?
- A frame is an `(H, W, 3)` `uint8` ndarray in BGR — why must it be converted and encoded before it can reach Gemini?
- Where does the latency in a single Gemini call actually go, and which part does the Phase 5 cache eliminate?

**After Phase 1:**
- Why does denoising help downstream models, and when does it hurt?
- Why hash the *preprocessed* frame instead of the raw capture?

**After Phase 2:**
- What kinds of input does Tesseract fail on, and what preprocessing fixes those failures?
- What's the difference between asking an LLM "what is this?" and asking it to fill a structured schema?

**After Phase 3:**
- When does LLM grounding beat a custom scraper, and when does it not?
- Why is the reference dossier worth caching by SKU instead of by image hash?

**After Phase 4:**
- Why split the comparison into three pillars instead of one big prompt?
- What does the `SUSPICIOUS` label give you that a binary genuine/fake never could?

**After Phase 5:**
- Why does a feedback write require touching both Redis and SQLite?
- What's a TTL strategy that distinguishes "model guessed" from "human confirmed"?

**After Phase 6:**
- Where did the edge code transfer cleanly, and where did the cloud port force you to rewrite?
- What does Rekognition do well that Gemini doesn't, and vice versa?

---

*Last updated: 2026-06-03 | Status: Pre-implementation (Phase 0 bootstrap defined; venv created)*
