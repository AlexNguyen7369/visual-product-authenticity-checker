# Learning Roadmap — Micro-Projects to the Starter Phase

> **Purpose:** A ladder of tiny, do-it-by-hand modules that each teach one piece of the tech stack, one
> testing skill, and one debugging skill. Each rung is small enough to finish in a sitting. By the top of
> the ladder you'll have *built*, line by line, every component that Phase 0's vertical slice assembles —
> and you'll understand not just *what* the code does but *what's happening underneath* and *how to prove
> it's correct*.

## How to use this

- Do the modules **in order**. Each assumes the previous one's understanding.
- For every module: build it, then **write the test cases before you call it done**, then run the
  **debugging drill** (deliberately break it and watch how it fails — debugging is a skill you practice,
  not a thing you do only in emergencies).
- Each module is its own script under `experiments/`, *not* in `src/`. `src/` is for the real project; this
  is a sandbox. The stub code under `experiments/` is tracked in git (so you can commit your solutions as
  you go), while the image outputs it produces are git-ignored by the `*.jpg` / `*.png` rules. Run
  `experiments/assets/make_sample.py` once to generate a sample image the still-image modules can load.
- Run everything inside the project venv (`.\.venv\Scripts\Activate.ps1`).

## The testing mindset (read once, apply everywhere)

A good test answers: *"if this function were silently wrong, what input would expose it?"* Three
categories you'll use in every module:

- **Happy path** — a normal input produces the expected output.
- **Edge case** — empty input, the smallest/largest valid input, a boundary value (0, 255, the last pixel).
- **Failure case** — bad input *should* fail loudly (raise/return an error), not silently produce garbage.

A test you can't make fail isn't testing anything. Before trusting a test, break the code on purpose and
confirm the test goes red.

---

## Track A — Foundations: the environment and the array

### M1 — Hello venv
**Build:** A script that imports `cv2, numpy, PIL, google.genai, dotenv` and prints each version, then prints
`sys.executable`.
**You learn:** That `sys.executable` points *inside* `.venv\` — proof you're running the isolated
interpreter, not global Python. The difference between `requirements.txt` (what you declared) and
`pip freeze` (what actually resolved, pinned).
**Test cases:** Assert each module imports without raising. Assert `".venv"` is a substring of
`sys.executable`.
**Debugging drill:** Deactivate the venv and run it with global Python — watch the import fail or the path
change. That failure mode (wrong interpreter) is the #1 "but it works on my machine" bug.
**Maps to:** Phase 0, Step 0.1.

### M2 — Build a frame by hand
**Build:** With **no camera**, create `frame = np.zeros((4, 6, 3), dtype=np.uint8)`. Set individual pixels.
Make the top-left pixel pure blue *in BGR* (`frame[0,0] = [255,0,0]`). Print `frame.shape`, `frame.dtype`,
`frame.nbytes`. Slice out a 2×2 crop. Swap channel 0 and channel 2 (BGR→RGB) two ways: `frame[..., ::-1]`
and `cv2.cvtColor`.
**You learn:** A frame *is* an `(H, W, 3) uint8` ndarray — a flat byte buffer with shape metadata. Cropping
is just slicing (a *view*, not a copy — mutate it and you mutate the original). Why `nbytes = H*W*3`. The
BGR convention, concretely.
**Test cases:** Assert `shape == (4,6,3)` and `dtype == uint8`. Assert the hand-swapped array equals the
`cvtColor` result (`np.array_equal`). Assert that mutating a slice *without* `.copy()` changes the parent
(prove the view aliasing bug exists), and that `.copy()` prevents it.
**Debugging drill:** Set a pixel to `[256, 0, 0]` and observe `uint8` wraparound to 0 — silent overflow,
the kind of bug that makes colors mysteriously wrong.
**Maps to:** The data structure every later module passes around; the BGR→RGB conversion in Step 0.3.

---

## Track B — OpenCV on still images (no camera yet)

### M3 — Load, show, save
**Build:** `cv2.imread` a `.jpg` you have, show it with `cv2.imshow` + `cv2.waitKey(0)`, save a copy with
`cv2.imwrite`. Then load the *saved* copy and compare.
**You learn:** `imread` returns `None` (not an exception!) on a bad path — a classic silent failure.
`waitKey` is what actually pumps the GUI event loop (forget it and the window hangs gray). JPEG save→load
is **lossy** — the reloaded array is *not* byte-identical.
**Test cases:** Assert `imread` of a real file returns an ndarray; assert `imread` of a nonexistent path
returns `None` (and write an explicit guard that raises a clear error). Assert reloaded JPEG is *close to*
but *not equal to* the original (`np.array_equal` is False; mean abs diff is small).
**Debugging drill:** Pass a path with a typo and watch the `None` propagate into a cryptic crash three lines
later — then add the guard that turns it into a clear message at the source. (Failing *early and loudly* is
a debugging discipline.)
**Maps to:** File I/O in every capture/save step.

### M4 — Color spaces and channels
**Build:** Convert an image BGR→RGB, BGR→GRAY. Use `cv2.split` / `cv2.merge`. Display the same image with and
without the BGR→RGB fix side by side.
**You learn:** Why your shoe looks "wrong-colored" if you skip the conversion before showing or sending it.
Grayscale collapses 3 channels to 1 (shape becomes `(H,W)`) — downstream code that assumes 3 channels will
break.
**Test cases:** Assert grayscale output shape is `(H,W)` (2-D, not 3-D). Assert round-trip BGR→RGB→BGR
equals the original. Assert a known red pixel reports high in the R channel after conversion.
**Debugging drill:** Feed a grayscale `(H,W)` image into a function expecting `(H,W,3)` and read the
resulting shape/broadcast error — learn to recognize "shape mismatch" stack traces fast.
**Maps to:** Step 0.3's mandatory BGR→RGB before encoding; Phase 1 preprocessing.

### M5 — Preprocessing primitives
**Build:** On a still image: `cv2.resize` to 1024×1024, crop via slicing, `cv2.GaussianBlur`, denoise with
`cv2.fastNlMeansDenoisingColored`, threshold to binary with `cv2.threshold`. Display before/after for each.
**You learn:** The exact operations Phase 1 chains. The fidelity/aggression trade-off: heavy denoise/blur
smooths away the fine stitching that Pillar 1 needs — *more preprocessing is not always better*.
**Test cases:** Assert resized shape is exactly `(1024,1024,3)`. Assert denoised image has lower pixel
variance than the noisy original (denoise *reduces* high-frequency content). Assert threshold output
contains only 0 and 255.
**Debugging drill:** Resize with the width/height swapped and watch the aspect ratio distort — then learn to
read `cv2.resize`'s `(width, height)` ordering, which is the *opposite* of NumPy's `(rows, cols)`. This
axis-order mismatch is a perennial bug.
**Maps to:** `capture/preprocess.py` (Phase 1).

### M6 — Find the object (contours)
**Build:** Threshold an image, `cv2.findContours`, pick the largest by area, draw its bounding box with
`cv2.rectangle`, and crop to it.
**You learn:** The "crop to product" idea — isolating the shoe from background clutter. Contours are just
lists of boundary points; "largest area" is a cheap proxy for "the main object."
**Test cases:** On a synthetic image (white rectangle on black) assert the detected bounding box matches the
rectangle's known coordinates within a tolerance. Assert behavior on an all-black image (no contours →
should return a sensible default/None, not crash).
**Debugging drill:** Run contour detection on a noisy unthresholded image and watch it find hundreds of
junk contours — learn that the *preprocessing* (M5) is what makes the *detection* (M6) work. Garbage in,
garbage out, made visible.
**Maps to:** Crop-to-largest-contour in `capture/preprocess.py`.

---

## Track C — Bytes, encoding, and hashing (how an image leaves your process)

### M7 — Encode, base64, measure
**Build:** Take an ndarray, `cv2.imencode('.jpg', img)` to JPEG bytes, base64-encode it, then decode both
back. Print the byte sizes at each stage: raw `nbytes`, JPEG bytes, base64 length.
**You learn:** Raw → JPEG is ~30× smaller (lossy compression); JPEG → base64 is +33% larger (text-safe
re-encoding). *Why* each step exists: compression for bandwidth/latency, base64 because JSON is a text
transport. This is the exact pipeline inside Step 0.3.
**Test cases:** Assert `len(jpeg_bytes) < raw.nbytes` (compression shrinks). Assert `len(base64) ≈
len(jpeg)*4/3` within a few bytes. Assert decode(encode(x)) is a valid image of the same shape.
**Debugging drill:** Forget to base64-encode and try to stuff raw bytes into a JSON string — observe the
`UnicodeDecodeError` / corruption. That error *means* "you put binary in a text channel."
**Maps to:** The ndarray→JPEG→base64→HTTPS flow in Step 0.3; the canonical bytes hashed in Phase 1.

### M8 — Deterministic image hashing
**Build:** `hashlib.sha256(canonical_bytes).hexdigest()` of an image's JPEG bytes. Hash the same image
twice; hash a 1-pixel-changed version.
**You learn:** A hash is a content fingerprint: identical bytes → identical hash (deterministic), any change
→ totally different hash (avalanche). This is the **cache key**: same shoe photo → same key → cache hit.
Why you hash the *preprocessed canonical* bytes, not the raw frame (raw frames are never byte-identical
twice, so they'd never cache-hit).
**Test cases:** Assert hashing the same bytes twice gives the same digest. Assert a 1-byte change gives a
different digest. Assert digest length is 64 hex chars.
**Debugging drill:** Hash a raw camera-style array (simulate by adding tiny random noise each run) and watch
the key change every time → 0% cache hit rate. This *is* the bug that motivates canonicalization before
hashing.
**Maps to:** `capture/hash.py` (Phase 1); the cache-key contract for Phase 5.

---

## Track D — Live capture (now the camera turns on)

### M9 — Webcam preview + keypress capture
**Build:** `cv2.VideoCapture(0)`, loop `cap.read()` + `cv2.imshow`, break on `SPACE` (`waitKey(1) == 32`),
save the held frame. Always `cap.release()` and `cv2.destroyAllWindows()` at the end.
**You learn:** `cap.read()` returns `(ok, frame)` and is **blocking** — your loop runs at camera cadence.
`waitKey(1)` (not `0`) keeps the loop live while still polling keys. Releasing the device matters: forget
it and the camera stays locked (next run fails to open).
**Test cases:** Hard to unit-test live hardware, so test the *seams*: assert `cap.isOpened()` is True after
open (and fail with a clear message if a camera isn't available). Factor the "is this key SPACE?" check into
a pure function and unit-test it (32 → True, others → False).
**Debugging drill:** Comment out `cap.release()`, run twice in a row, and watch the second run fail to grab
the camera — learn to recognize "resource not released" bugs (the same class as unclosed files/sockets).
Then add a `try/finally` so release always happens even on error.
**Maps to:** `capture/webcam.py` (Phase 1); Phase 0, Step 0.2.

### M10 — Capture → preprocess → save (mini Phase 1)
**Build:** Chain it: capture a frame (M9) → BGR→RGB + resize + denoise + crop-to-contour (M4–M6) → hash
(M8) → save the crop named by its hash (`{hash}.jpg`).
**You learn:** How the small pieces compose into a pipeline, and that **each stage's output is the next
stage's input** — so each stage needs a stable, documented shape/format contract. This is integration, and
integration is where mismatched assumptions surface.
**Test cases:** Feed a *saved still* (not the live camera) through the preprocess+hash chain so it's
repeatable, and assert the same input file always yields the same hash and a `(1024,1024,3)` output. (This
is your first **fixture-based** test — a fixed input file standing in for the camera.)
**Debugging drill:** Insert a stage that forgets the BGR→RGB conversion and watch the colors flip in the
saved file — trace *which* stage introduced it by saving intermediate outputs. Saving intermediates is a
core CV debugging technique: you can't `print` an image, so you *look* at it.
**Maps to:** The whole of Phase 1.

---

## Track E — The model call (the network round-trip)

### M11 — First Gemini call (text only)
**Build:** Load `GEMINI_API_KEY` from `.env` via `python-dotenv`, create a `google.genai` client, send a
plain text prompt ("Reply with the single word OK"), print the response. Add a timeout and a try/except that
prints a clear message on failure.
**You learn:** The request/response lifecycle: construct request → block on network round-trip → parse
response. Where latency lives (network + model inference). Secrets come from the *environment*, never code.
What failures look like (auth error with a bad key, timeout, rate-limit 429).
**Test cases:** Assert the key loads and is non-empty *before* calling (fail fast with a clear message if
`.env` is missing). Wrap the call so a network error returns a typed result you can assert on, rather than
crashing. (You're testing *your* error handling, not Google's API.)
**Debugging drill:** Run with a deliberately wrong API key and read the auth error; run with a 1ms timeout
and read the timeout error. Knowing what each failure *looks like* is half of debugging integrations.
**Maps to:** The `VisionClient` wrapper; Step 0.3; every Gemini call in Phases 2–4.

### M12 — Image → Gemini yes/no detector (the vertical slice closes)
**Build:** Capture/load a frame → BGR→RGB → JPEG-encode (M7) → send to Gemini with *"Reply with only YES or
NO: is there a sneaker in this image?"* → parse and print. Test on a shoe and on a non-shoe.
**You learn:** This is **Phase 0, Step 0.3** — and it's a degenerate `identify()`. The plumbing (encode +
POST + parse) is identical to Phase 2; only the prompt and the richness of the parsed response differ. You
now see the scalability thread end to end.
**Test cases:** Factor out a pure `parse_yes_no(text) -> bool` and unit-test it against messy model outputs
("YES", "yes.", "Yes, it is", "NO" → True/True/True/False) — **model responses are unreliable text, so the
parser is where your robustness lives and where tests pay off most.** Use a saved shoe image as a fixture
for a (network-dependent) end-to-end check.
**Debugging drill:** Feed the parser unexpected output ("I cannot determine") and decide the contract — does
it raise, default to False, or return `UNKNOWN`? Designing for the *ambiguous* answer is exactly the
instinct behind the project's `SUSPICIOUS` verdict.
**Maps to:** Phase 0 complete; the seed of Phase 2's `identify()`.

---

## Track F — Crosscutting: a tiny cache and a real test suite

### M13 — Dict cache with TTL + a pytest suite
**Build:** A `Cache` class backed by a plain dict: `get(key)`, `set(key, value, ttl_seconds)`, with entries
expiring after their TTL (store `(value, expiry_timestamp)`; treat expired as a miss). Then write a real
`pytest` file covering M5's preprocess functions, M8's hash, and this cache.
**You learn:** Read-through caching and TTL semantics *before* Redis exists — Phase 5 just swaps the dict
for Redis with the *same interface*. How to structure a `pytest` suite: arrange/act/assert, fixtures for
shared inputs, parametrized cases for many inputs at once.
**Test cases:** Assert `set` then immediate `get` hits. Assert `get` of an expired entry misses (use a tiny
TTL and a controllable clock — inject `now()` so you don't have to actually sleep; **tests that sleep are
slow and flaky**). Assert `get` of an unknown key returns the miss sentinel.
**Debugging drill:** Write the TTL check with `<=` vs `<` and probe the exact-expiry boundary — off-by-one
on time/index boundaries is one of the most common real bugs. Then make the clock injectable and watch the
flaky sleep-based test become deterministic.
**Maps to:** `cache/redis_client.py` (Phase 5); the TTL strategy (24h predictions / 30d confirmed).

---

## The ladder at a glance

```
A. Foundations      M1 venv ──► M2 ndarray-as-frame
B. OpenCV stills    M3 load/show/save ──► M4 color ──► M5 preprocess ──► M6 contours
C. Bytes & hashing  M7 encode/base64 ──► M8 sha256 cache-key
D. Live capture     M9 webcam+keypress ──► M10 capture→preprocess→save  (mini Phase 1)
E. The model call   M11 text Gemini ──► M12 image yes/no detector       (= Phase 0 Step 0.3)
F. Crosscutting     M13 dict-cache+TTL + pytest suite                   (seed of Phase 5)

        └────────────────────────► assemble = Phase 0 vertical slice ────► Phase 1
```

Finish M1–M12 and you've hand-built every part of Phase 0. Add M13 and you've also previewed the caching and
testing patterns that carry through to Phase 5. At that point the "real" `src/` code is just these
experiments, cleaned up, given stable interfaces, and wired together.

---

*Companion to `architecture.md`. Do the rungs in order; write the tests; break things on purpose.*
