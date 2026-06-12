# Learning Curriculum — Fundamentals, Labs & Mini-Projects

> **Purpose:** The conceptual syllabus underneath this whole project. Seventeen units, in strict
> order, each teaching one fundamental from first principles — what's actually happening under the
> hood — and each paired with hands-on labs and a small standalone mini-project. The center of
> gravity here is **doing**, not reading.

## How to use this doc

Three documents, three jobs:

| Doc | Job |
|---|---|
| `architecture.md` | **Why** each component exists — design rationale, per phase |
| `roadmap.md` | **The build ladder** — 13 tiny throwaway modules (M1–M13) that hand-assemble Phase 0 |
| `learning.md` (this doc) | **The concepts** — fundamentals in order, each with its own labs and mini-projects |

Work a unit's **Concept**, do its **Labs**, then do the matching roadmap module (cross-linked
where it exists), then move on. Labs here *add to* the roadmap modules — they never just repeat them.

Practical rules:

- Keep all lab and mini-project code in a git-ignored `experiments/` scratch folder — `src/` is for
  the real project only.
- Always run inside the project venv: `.\.venv\Scripts\Activate.ps1` (PowerShell).
- Every lab has a **Done when** — don't move on until you hit it.
- Every unit ends with **Check yourself** questions. Answer them out loud, in your own words.
  If you can't, re-read the Concept section.

---

## Unit 1 — Python Environments & Dependency Isolation

### Concept

When you type `python`, Windows walks your `PATH` and runs the first `python.exe` it finds. When
that interpreter executes `import cv2`, it walks `sys.path` — a list of directories — and imports
the first `cv2` it finds, usually from a folder called `site-packages`.

A **virtual environment** is nothing magical: it's a folder (`.venv/`) containing its own
`python.exe` (or a thin launcher pointing at the real one) and its own empty `site-packages/`.
"Activating" it just edits your shell's `PATH` so `.venv\Scripts\python.exe` wins the race. From
that moment, `pip install` writes into *this project's* `site-packages`, and `import cv2` reads
from it. Two projects can now hold incompatible versions of the same library without ever touching
each other — that's **dependency isolation**.

A **wheel** (`.whl`) is what pip actually downloads: a zip of *precompiled* code. `opencv-python`
is mostly C++; its wheel contains `.pyd` binaries (Windows shared libraries). Pip unpacks the zip
into `site-packages` — no compilation on your machine, which is why the install takes seconds, not
an hour.

Two related files that people conflate:

- `requirements.txt` — what you **declared** ("I need opencv-python and google-genai").
- `pip freeze` output — what actually **resolved**: every package including transitive
  dependencies, pinned to exact versions.

The gap between "declared" and "resolved" is the seed of every reproducible-build tool you'll meet
later: lockfiles, `pip-tools`, Docker images. "Works on my machine" is almost always a resolved-set
mismatch.

### Why it matters here

Every later unit imports `cv2`, `numpy`, `google.genai`. If those resolve from the wrong
interpreter, nothing downstream is trustworthy. Phase 6 raises the stakes: a Lambda deployment
package is essentially a frozen `site-packages` zipped up — exactly the resolved set, made
immutable.

### Interview / system-design lens

"How do you make builds reproducible?" The ladder is: declared deps → pinned/locked deps →
frozen environment (venv) → immutable artifact (container image / Lambda zip). A venv is rung two
of that ladder; be able to narrate the whole thing.

### Labs

**Lab 1.1 — Prove which interpreter is running** *(builds on roadmap M1)*

M1 prints versions; go one step deeper into the *mechanism*. Inside the activated venv run:

```powershell
python -c "import sys; print(sys.executable); print(*sys.path, sep='\n')"
```

Then deactivate (`deactivate`) and run the same line. Diff the two `sys.path` lists by eye.

**Done when:** You can point at the exact `site-packages` entry that differs and explain why
`import cv2` succeeds in one shell and fails (or resolves differently) in the other.

**Lab 1.2 — Declared vs resolved**

In a *throwaway* second venv (`python -m venv C:\temp\scratchvenv`), `pip install requests`. Then:

```powershell
pip freeze
```

Count the packages. You asked for one; you got several (`urllib3`, `idna`, `charset-normalizer`...).

**Done when:** You can name the transitive dependencies of `requests` and explain why pinning only
`requests==2.x` does *not* make the build reproducible.

**Lab 1.3 — Open the wheel**

```powershell
pip download opencv-python --no-deps -d C:\temp\wheels
```

Rename the `.whl` to `.zip`, extract it, and find the `.pyd` files inside.

**Done when:** You've seen with your own eyes that "installing OpenCV" means "unzipping
precompiled C++ binaries into a folder Python searches."

### Mini-project: `envdoctor`

A small CLI script that diagnoses a Python environment: prints `sys.executable`, whether a venv is
active (`sys.prefix != sys.base_prefix`), Python version, and for a list of package names passed as
arguments, whether each imports and from *what file path* (`module.__file__`). Output a pass/fail
table. Run it inside and outside the venv and watch the story change. (You'll genuinely reuse this
when an import mysteriously breaks in Phase 2.)

### Check yourself

1. What does "activating" a venv actually change, mechanically?
2. Why can `requirements.txt` be satisfied and the app still behave differently on another machine?
3. What is inside a wheel, and why does that make `pip install opencv-python` fast?

---

## Unit 2 — The Image as Data: NumPy ndarrays

### Concept

An image in memory is not a grid object — it's a **flat, contiguous run of bytes** plus metadata
that tells NumPy how to interpret it. A 1080p color frame is `1080 × 1920 × 3 = 6,220,800` bytes
sitting in one block. The ndarray wraps that block with:

- **shape** `(1080, 1920, 3)` — how to slice the flat buffer into rows, columns, channels
- **dtype** `uint8` — each element is one unsigned byte, values 0–255
- **strides** `(5760, 3, 1)` — how many *bytes* to skip to move one step along each axis

Strides are the key insight. To go one row down, skip `1920×3 = 5760` bytes. One column right: 3
bytes. Next channel: 1 byte. This is **row-major** layout (C order): rows are contiguous, which is
why iterating row-by-row is cache-friendly and column-by-column isn't.

Because shape and strides are just metadata, NumPy can give you a **view** — a new ndarray that
points at the *same* bytes with different metadata — for free. `frame[100:200, 300:400]` allocates
nothing; it's a window onto the original buffer. Mutate the view, and you mutate the parent. This
is a feature (zero-copy crops) and a footgun (aliasing bugs). `.copy()` allocates fresh bytes and
breaks the link.

`uint8` arithmetic **wraps around**: `np.uint8(250) + np.uint8(10)` is `4`, not `260` and not an
error. Brightness math done naively in `uint8` silently corrupts bright pixels. The fixes: convert
to a wider dtype first (`frame.astype(np.int16)`), or use OpenCV's saturating ops (`cv2.add` clamps
at 255 instead of wrapping).

### Why it matters here

Every single thing this project passes around — webcam frames, crops, preprocessed canonical
images — is an `(H, W, 3) uint8` ndarray. Views explain why stashing frames from the capture loop
without `.copy()` corrupts your saved captures (Unit 8). Wraparound explains a whole class of
"colors went weird after my brightness tweak" bugs in preprocessing (Unit 5).

### Interview / system-design lens

"What's the difference between a view and a copy?" is a real screening question, and the deeper
version — *how do shape/strides let NumPy do zero-copy slicing?* — separates people who've used
NumPy from people who understand it. The same buffer-plus-metadata idea reappears in Arrow,
protobuf zero-copy, and GPU tensors.

### Labs

**Lab 2.1 — Read the strides** *(builds on roadmap M2)*

M2 builds a tiny frame; now interrogate its memory layout:

```python
import numpy as np
frame = np.zeros((4, 6, 3), dtype=np.uint8)
print(frame.strides)                  # expect (18, 3, 1)
print(frame[::2].strides)             # every other row — strides change, no copy
print(frame.T.flags['C_CONTIGUOUS'])  # transpose: False — same bytes, new walk order
```

Predict each output *before* running.

**Done when:** You can compute the strides of any `(H, W, 3) uint8` array on paper and explain why
a transpose is free but makes the array non-contiguous.

**Lab 2.2 — Hunt the aliasing bug**

Create a 100×100 black frame. Take `crop = frame[10:20, 10:20]`, set `crop[:] = 255`, then check
`frame[15, 15]`. Now repeat with `crop = frame[10:20, 10:20].copy()`.

**Done when:** You can state the rule for when slicing returns a view vs a copy, and you've watched
a mutation travel "backwards" into the parent.

**Lab 2.3 — Wraparound vs saturation**

```python
a = np.full((1, 1, 3), 250, dtype=np.uint8)
print(a + 10)                            # wraps → 4
print(cv2.add(a, np.full_like(a, 10)))   # saturates → 255
```

Then brighten a real photo two ways — `img + 60` vs `cv2.add(img, 60)` — and view both.

**Done when:** You can show a photo where naive `+` turned bright sky into dark garbage, and
explain the byte-level reason.

### Mini-project: ASCII image renderer

Load any photo, convert to grayscale, downsample to ~80 columns (pure slicing/striding — no
`cv2.resize` allowed), and map pixel intensity to a character ramp (`" .:-=+*#%@"`). Print it to
the terminal. Everything in this unit — shape math, dtype ranges, row-major iteration — gets
exercised, and the output is fun. Stretch: re-render live from the webcam after Unit 8.

### Check yourself

1. Given shape `(720, 1280, 3)` and dtype `uint8`, what are the strides, and how many bytes is the
   whole frame?
2. Why is `frame[0:100, 0:100]` free, and when is that dangerous?
3. What does `np.uint8(200) + np.uint8(100)` return, and why doesn't it raise?

---

## Unit 3 — Color & Channels

### Concept

A "color" pixel is three numbers — but *which* three, in *what order*, is pure convention. OpenCV
stores channels as **BGR** (blue first), a fossil from 1990s Windows bitmap formats. Pillow,
matplotlib, web browsers, Gemini, and essentially every ML model expect **RGB**. Nothing checks.
If you hand BGR bytes to something expecting RGB, reds and blues silently swap — no error, just a
shoe in the wrong colorway.

Conversion is a byte shuffle: `cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)` or the slice trick
`frame[..., ::-1]` (note: the slice produces a *view* with negative stride; some downstream code
wants a contiguous copy — `np.ascontiguousarray` fixes that).

**Grayscale** collapses three channels into one weighted sum (~`0.299R + 0.587G + 0.114B` — green
dominates because human eyes do). The shape changes from `(H, W, 3)` to `(H, W)`. Code that
blindly indexes channel 2 of a grayscale image breaks — shape contracts matter.

**White balance** corrects for the light source. Under warm indoor light, a white tongue label
photographs orange. The **gray-world assumption** says: averaged over a whole natural scene, the
world is roughly gray, so the mean of each channel should be equal. If the means are skewed,
scale each channel until they match:

```python
def gray_world(img_bgr: np.ndarray) -> np.ndarray:
    img = img_bgr.astype(np.float32)
    means = img.reshape(-1, 3).mean(axis=0)   # per-channel mean (B, G, R)
    img *= means.mean() / means               # scale each channel toward the global mean
    return np.clip(img, 0, 255).astype(np.uint8)
```

Note the dtype dance: float math, then clip, then back to `uint8` — Unit 2's wraparound lesson
applied.

### Why it matters here

Colorway is *identity* for sneakers — "Chicago" vs "Bred" Jordan 1s differ mostly in color. A BGR
mixup sends Gemini a different-looking shoe; a bad white balance makes a genuine pair look like a
counterfeit with off-color leather (a real Pillar 1 signal!). `capture/preprocess.py` runs
gray-world precisely so lighting doesn't masquerade as evidence.

### Labs

**Lab 3.1 — The swap, made visible** *(builds on roadmap M4)*

M4 shows BGR vs RGB side by side. Add the quantitative version: take a photo with a clearly red
object, print the mean of each channel before and after conversion, and confirm the "R" channel
mean physically moves to the other end of the array.

**Done when:** You can look at a wrong-looking image and say "that's a channel swap" in under five
seconds, and prove it with channel means.

**Lab 3.2 — Gray-world by hand**

Implement `gray_world` above yourself (don't paste it). Photograph a sheet of white paper under
your warmest household light, run it through, and compare per-channel means before/after.

**Done when:** Post-correction channel means are within ~5 of each other and the paper *looks*
white.

**Lab 3.3 — Break the gray-world assumption**

Run your `gray_world` on a photo that is dominantly one color (a red sneaker filling the whole
frame). Watch it overcorrect — it assumes the world is gray, and your red world violates that.

**Done when:** You can explain why crop-then-white-balance ordering matters in the Phase 1
pipeline (balance on the full scene *before* cropping to the shoe).

### Mini-project: Dominant-color guessing game

Script picks a random image from a folder, computes its dominant color (k-means on pixels with
`k=3`, or just the per-channel median for the simple version), shows you the image for 2 seconds,
then asks you to type the dominant color name. Map RGB to the nearest of ~10 named colors. Score
yourself over 10 rounds. Teaches channels, color distance, and the gap between perceived and
numeric color.

### Check yourself

1. Why does OpenCV use BGR, and what's the symptom when you forget to convert?
2. Why is grayscale not just the average of the three channels?
3. What assumption does gray-world white balance make, and what input breaks it?

---

## Unit 4 — OpenCV on Still Images

### Concept

Three calls cover file I/O: `cv2.imread(path)` decodes a JPEG/PNG from disk into a BGR ndarray;
`cv2.imwrite(path, img)` encodes and writes; `cv2.imshow(name, img)` displays.

Two under-the-hood facts trip everyone:

**`imread` returns `None` on failure — it does not raise.** Bad path, wrong permissions, corrupt
file: you get `None`, and the crash happens three lines later as
`AttributeError: 'NoneType' object has no attribute 'shape'` — far from the actual bug. The fix is
a guard at the source: check for `None` immediately and raise with the path in the message.
Failing **early and loudly** at the point of error is a discipline, not a style preference.

**`imshow` doesn't actually draw — `waitKey` does.** OpenCV's window is driven by a GUI event
loop, and `cv2.waitKey(ms)` is the only function that pumps it: it processes pending window events
(including the actual paint), then polls the keyboard for up to `ms` milliseconds.
`waitKey(0)` blocks forever until a key. Forget `waitKey` entirely and the window appears gray and
frozen — the paint event never ran. This is your first contact with event loops: a queue of
pending events that only advances when something pumps it. (Browsers, GUIs, and Node.js all live
on this idea.)

Also note `imwrite(".jpg")` *re-encodes lossily* — a save/load round trip does not return the
original bytes. That detail becomes load-bearing in Units 6 and 7.

### Why it matters here

The capture pipeline saves frames, reloads fixtures for tests, and shows previews — all three
calls, constantly. The `None` failure mode is the canonical example of the silent-failure class of
bug; the `waitKey` event loop is exactly the mechanism that makes the live capture loop in Unit 8
tick.

### Interview / system-design lens

"Fail fast" is a system-design principle, not just a code style: detect bad state at the boundary
where context exists (the file path), not deep in the pipeline where it doesn't. The same logic is
why APIs validate requests at the edge.

### Labs

**Lab 4.1 — Write the guard** *(builds on roadmap M3)*

M3 has you trip the `None` crash. Now write the permanent fix — a 6-line `load_image(path)` that
raises `FileNotFoundError(f"imread failed: {path}")` on `None` — and use it in every later lab.
You're building your first utility with a deliberate contract.

**Done when:** A typo'd path produces a one-line error naming the path, not a `NoneType` traceback.

**Lab 4.2 — Starve the event loop**

Show an image, then replace `waitKey(0)` with `time.sleep(5)`. Observe the gray/frozen window.
Restore `waitKey` and explain the difference in one sentence.

**Done when:** You can explain why `sleep` doesn't paint the window but `waitKey` does, using the
words "event loop."

**Lab 4.3 — Quality dial**

Save the same photo at JPEG quality 95, 70, 40, 10 via
`cv2.imwrite(p, img, [cv2.IMWRITE_JPEG_QUALITY, q])`. Compare file sizes and zoom into a detailed
region (laces, stitching) at each level.

**Done when:** You can name the quality level where stitching detail visibly degrades — you'll
reuse this judgment in Unit 6 when choosing the canonical encode setting.

### Mini-project: Contact-sheet generator

A CLI that takes a folder of images and produces one big "contact sheet" image: thumbnails in a
grid with filenames drawn on (`cv2.putText`), saved as a single JPEG. Forces you through imread
guards, resizing, ndarray pasting via slice assignment (`sheet[y:y+h, x:x+w] = thumb`), and
imwrite. Genuinely useful for eyeballing your capture fixtures later.

### Check yourself

1. What does `imread` do on a bad path, and where does the crash actually surface?
2. What is `waitKey` really doing besides reading the keyboard?

---

## Unit 5 — Preprocessing Primitives

### Concept

Preprocessing is controlled information *destruction*. Every primitive throws something away on
purpose — the skill is knowing what each one destroys and whether downstream needs it.

- **Resize** — `cv2.resize(img, (1024, 1024))` interpolates new pixel values. **The axis trap:**
  OpenCV's size argument is `(width, height)` while NumPy shape is `(rows, cols)` = `(height,
  width)`. They're opposite. Swapping them on a non-square image silently distorts the aspect
  ratio — the single most common OpenCV bug in existence.
- **Crop** — pure slicing, `img[y0:y1, x0:x1]`. Destroys everything outside the window. Free
  (it's a view — Unit 2).
- **Gaussian blur** — `cv2.GaussianBlur(img, (5,5), 0)` replaces each pixel with a weighted
  average of its neighbors. Destroys high-frequency content: noise, but also fine texture.
- **Non-local means denoise** — `cv2.fastNlMeansDenoisingColored(img, None, h, h, 7, 21)` is
  smarter: it averages each patch with *similar patches elsewhere in the image*, so repeated
  texture survives better than under blur. Strength `h` is the destruction dial.
- **Threshold** — `cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)` collapses everything to 0 or
  255. Maximum destruction: only shape survives. That's the point — it's the standard prelude to
  contour finding and OCR.
- **Contours** — `cv2.findContours` on a binary image returns boundary point lists; pick the
  largest by `cv2.contourArea`, take its `cv2.boundingRect`, and crop to it. That's
  "crop-to-largest-object": cheap object isolation with zero ML.

**The fidelity-vs-aggression tradeoff is the unit's real lesson.** Pillar 1 judges authenticity by
stitch spacing, thread texture, and leather grain — exactly the high-frequency content that
denoising and compression destroy first. Preprocess too gently and noise confuses OCR and
contours; too hard and you erase the evidence the verdict depends on. There is no "correct"
setting, only a tradeoff you choose with your eyes open — and possibly *different* preprocessing
for different consumers (hard threshold for the OCR path, light touch for the comparison path).

### Why it matters here

This unit *is* `capture/preprocess.py` (Phase 1): denoise → white-balance → crop-to-contour →
resize to 1024×1024. Get the order or the aggression wrong, and either the cache key never
stabilizes (Unit 7) or Pillar 1 goes blind.

### Interview / system-design lens

"Lossy preprocessing as a tradeoff" generalizes everywhere: downsampling logs, sampling traces,
compressing thumbnails. The interview-grade observation is that different consumers may need
different fidelity from the *same* source — which is why pipelines often fork rather than share
one canonical transform.

### Labs

**Lab 5.1 — Trip the axis trap on purpose** *(builds on roadmap M5)*

M5 has you swap width/height once. Make it stick: write `resize_square(img, side)` plus a second
function `letterbox(img, side)` that *preserves* aspect ratio by scaling the long edge and padding
the rest with black. Compare a sneaker photo through both — distorted vs letterboxed.

**Done when:** You can articulate why a distorted silhouette would corrupt Pillar 2
(sole/silhouette comparison) and which version Phase 1 should use.

**Lab 5.2 — The destruction dial**

Run `fastNlMeansDenoisingColored` at `h = 3, 10, 25, 50` on a close-up photo of fabric or
stitching. Save all four (`denoise_h3.jpg`, etc.) and inspect zoomed-in.

**Done when:** You can point at the `h` value where stitch boundaries stop being countable, and
state your chosen Phase 1 value with a one-sentence justification.

**Lab 5.3 — Make contours work, then break them** *(builds on roadmap M6)*

M6 finds the largest contour on a clean synthetic image. Now do it on a *real* photo of a shoe on
your floor. It will probably fail (busy background → wrong largest contour). Fix it by improving
the *preprocessing*: blur → threshold (try `cv2.THRESH_OTSU` for automatic threshold selection) →
contours. Iterate until the bounding box hugs the shoe.

**Done when:** The crop is correct on three different photos of the shoe with different
backgrounds, and you can explain which preprocessing change made the difference.

### Mini-project: Document scanner

Photograph a receipt or page at an angle on a dark table. Pipeline: grayscale → blur → threshold →
largest contour → `cv2.approxPolyDP` to get four corners → `cv2.getPerspectiveTransform` +
`cv2.warpPerspective` to produce a flat, top-down "scan." This is the classic CV starter project
and exercises every primitive in the unit plus one new one (perspective warp). Bonus: it produces
ideal input for Unit 9's OCR.

### Check yourself

1. `cv2.resize` takes `(width, height)`; NumPy shape is `(height, width)`. Why does this bug fail
   silently?
2. What does thresholding destroy, and why is that destruction useful before `findContours`?
3. Which pillar is most damaged by over-denoising, and what specifically gets lost?

---

## Unit 6 — Serialization & Encoding

### Concept

An ndarray is meaningful only inside your process: it's a pointer to bytes plus Python object
metadata. To cross a process boundary — disk, network, another machine — you need a
**serialization format**: an agreed byte layout both sides understand.

For images, the chain this project uses is:

```
ndarray (1024×1024×3 uint8 ≈ 3 MB raw)
   │  cv2.imencode('.jpg', img)        lossy compress  → ~150–300 KB
   ▼
JPEG bytes
   │  base64.b64encode(...)            text-safe re-encode → +33%
   ▼
ASCII string inside a JSON body
   │  HTTPS POST
   ▼
Gemini
```

**JPEG** is lossy by design. Under the hood: the image is converted to a luma/chroma color space
(chroma gets downsampled — eyes are bad at color detail), split into 8×8 pixel blocks, each block
run through a **Discrete Cosine Transform** (re-expressing 64 pixels as 64 frequency
coefficients), then **quantized** — high-frequency coefficients get divided by big numbers and
rounded, mostly to zero. That rounding is where information dies and where the compression comes
from; the zeros then pack tightly under entropy coding. Decode reverses the path but the rounded
bits are gone forever. Re-encode a JPEG repeatedly and artifacts compound — generational loss.

**Base64** exists because JSON is a *text* protocol: raw binary bytes include control characters
and invalid UTF-8 sequences that text channels mangle. Base64 maps every 3 binary bytes onto 4
characters from a 64-character safe alphabet — hence exactly +33% size. The principle: **the
transport dictates the encoding.** A binary protocol (gRPC/protobuf) would skip the tax entirely.

`cv2.imencode` returns `(ok, buf)` where `buf` is a 1-D uint8 ndarray of the *encoded file bytes*
— call `.tobytes()` to get a Python `bytes` object. `cv2.imdecode(np.frombuffer(b, np.uint8),
cv2.IMREAD_COLOR)` is the inverse.

### Why it matters here

Every Gemini call ships a frame through this exact chain. Payload size drives upload latency
(Unit 10), so JPEG quality is a real latency lever. And the JPEG bytes — not the ndarray — are
what gets hashed for the cache key (Unit 7), which makes the encode settings part of a *contract*.

### Interview / system-design lens

"Why is the payload 33% bigger than the file?" and "how would you cut image upload latency?" are
bread-and-butter API design questions. Answers: text-transport tax; and compress harder / use a
binary protocol / upload once and pass a reference (which is literally what Phase 6 does with S3).

### Labs

**Lab 6.1 — Measure the whole chain** *(builds on roadmap M7)*

M7 prints sizes at each stage. Extend it into a table across JPEG qualities:

```python
for q in (95, 85, 70, 50, 30):
    ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, q])
    jpeg = buf.tobytes()
    b64 = base64.b64encode(jpeg)
    print(q, img.nbytes, len(jpeg), len(b64), round(len(b64) / len(jpeg), 3))
```

**Done when:** Every row shows the b64/jpeg ratio ≈ 1.333, and you've chosen a quality level for
the project's canonical encode (and written the number down).

**Lab 6.2 — See the DCT blocks**

Encode at quality 5, decode, and compute the absolute difference from the original
(`cv2.absdiff`), then amplify it (`diff * 8`) and display. You'll *see* the 8×8 block grid.

**Done when:** You can point at the block structure and explain where it comes from.

**Lab 6.3 — Generational loss**

Loop encode→decode 50 times at quality 70 on a detailed photo. Save generation 1, 10, 50.

**Done when:** You can articulate why the Phase 1 pipeline must encode **once** to canonical bytes
and pass those same bytes to both the hasher and the API — never re-encoding along the way.

### Mini-project: Image-diff tool

A CLI `imdiff a.jpg b.jpg` that loads two images, aligns sizes, computes per-pixel absolute
difference, prints summary stats (mean diff, % of pixels differing by >10), and writes a heatmap
visualization (`cv2.applyColorMap(diff_gray, cv2.COLORMAP_JET)`). Instantly useful for the rest of
the project: it's how you'll *prove* two "identical" captures aren't byte-identical (Unit 7) and
debug preprocessing changes.

### Check yourself

1. Where exactly in the JPEG pipeline is information irreversibly lost?
2. Why can't you put raw JPEG bytes in a JSON string, and what does base64 trade to fix it?
3. Why must the canonical encode happen exactly once?

---

## Unit 7 — Hashing & Content Addressing

### Concept

A cryptographic hash like **SHA-256** is a function that maps any byte string to a fixed 32-byte
digest with three properties you can lean on:

- **Deterministic** — same bytes in, same digest out. Always, everywhere, forever.
- **Avalanche** — flip one input bit and ~half the output bits flip. Digests of near-identical
  inputs look completely unrelated.
- **Collision-resistant** — you cannot feasibly find two different inputs with the same digest.

Together these enable **content addressing**: use the hash *of the data* as the data's name. Git
does this (every commit/blob is named by its hash); so do Docker layers and CDNs. For us, the
digest of a frame's canonical bytes is the **cache key**: same image → same key → cache hit.

The catch — and the central engineering lesson of this unit — is the word **canonical**. Two raw
webcam captures of the same shoe are *never* byte-identical: sensor noise alone flips thousands of
bytes, and avalanche turns each into a totally different digest. Hash raw frames and your cache
hit rate is 0%. The fix is the pipeline you've already built: preprocess to a normalized form
(denoise, white-balance, crop, resize, single JPEG encode) and hash *those* bytes. Preprocessing
isn't just cleanup — it's **canonicalization**, the act of collapsing many raw representations of
the same thing into one stable byte string.

This creates the **cache-key contract**: the digest is only stable while every preprocessing
parameter is frozen — resize dimensions, denoise strength, JPEG quality, even the OpenCV version's
encoder behavior. Change any of them and every existing cache entry silently becomes unreachable
(which is sometimes exactly what you want: changing the pipeline *should* invalidate old answers).

```python
import hashlib

def frame_key(canonical_jpeg: bytes) -> str:
    return hashlib.sha256(canonical_jpeg).hexdigest()   # 64 hex chars
```

### Why it matters here

This is `capture/hash.py` and the entire foundation of Phase 5: the Redis key is
`verdict:{sha256}`. The cloud port reuses the same key for ElastiCache and as the S3 object name
(`frames/{hash}.jpg`) and the DynamoDB partition key — one hash, three systems, one contract.

### Interview / system-design lens

"How would you deduplicate uploads / cache by content?" → content addressing. The senior follow-up
is the canonicalization problem: *what counts as "the same"?* Byte-identical is easy;
semantically-identical (same shoe, slightly different angle) needs perceptual hashing or
embeddings — a great "how would you extend this?" thread to be able to pull.

### Labs

**Lab 7.1 — Avalanche, quantified** *(builds on roadmap M8)*

M8 shows a 1-pixel change flips the digest. Quantify it: hash two inputs differing by one bit,
then compare digests *bit by bit* (convert hex → int → XOR → `bin(x).count('1')`).

**Done when:** You measure roughly 128 of 256 bits differing and can explain why "close inputs"
give no information about each other's digests.

**Lab 7.2 — Simulate the cache-hit-rate disaster**

Simulate 20 "captures" of the same scene: one base image plus per-capture Gaussian noise
(`np.random.normal(0, 2, img.shape)`, added in int16 then clipped — Unit 2!). Hash all 20 raw →
count unique digests. Then run each through your Unit 5 preprocess chain (denoise → resize →
encode once) and hash again.

**Done when:** Raw gives ~20 unique digests; canonicalized gives 1 (or you can explain exactly
which pipeline stage still leaks noise if it doesn't).

**Lab 7.3 — Break the contract on purpose**

Take Lab 7.2's working canonicalizer, change JPEG quality from 85 to 84, and re-hash.

**Done when:** You've watched the entire "cache" invalidate from a one-character config change,
and can say where the preprocessing parameters should therefore live (one frozen config, versioned
with the code — not scattered literals).

### Mini-project: Content-addressed file deduper

A CLI that walks a folder tree, SHA-256s every file (read in chunks — `h.update(block)` in a loop,
so you learn hashes are streaming), groups by digest, and reports duplicate sets with wasted
bytes. Stretch: add `--apply` to move duplicates into a quarantine folder. You're rebuilding the
heart of git's object store and every backup deduper, in ~60 lines.

### Check yourself

1. Why does hashing raw webcam frames give a 0% cache hit rate?
2. What exactly is in the "cache-key contract," and what happens when any part changes?
3. Why is avalanche a *feature* for cache keys but a *problem* for "find similar images"?

---

## Unit 8 — Live Capture

### Concept

`cv2.VideoCapture(0)` asks the OS (DirectShow/MSMF on Windows) to open camera device 0 and start a
**driver-side frame queue**. From then on, the camera produces frames at its own cadence (~30 FPS,
one every ~33 ms) whether you're reading or not.

`cap.read()` is **blocking, synchronous I/O**: your thread parks until a frame is available. So a
naive loop runs at camera speed — your code is rate-limited by hardware. Two consequences:

- **Backpressure / stale frames.** If your loop iteration is slower than 33 ms (say you do heavy
  processing inline), the driver queue fills with old frames and `read()` returns *stale* ones —
  the preview lags seconds behind reality. Mitigations: keep the loop lean (process only on
  keypress, which is exactly this project's design), set `cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)`, or
  drain reads. This is the same producer-consumer backpressure problem as a message queue with a
  slow consumer.
- **`read()` = `grab()` + `retrieve()`.** Grab pulls a frame off the queue (cheap); retrieve
  decodes it into an ndarray (costly). They're separable so multi-camera rigs can grab from all
  cameras nearly simultaneously, then decode. Knowing the split tells you where the cost lives.

The camera is an exclusive **OS resource**, like a file handle or a socket. If your process exits
without `cap.release()`, the device can stay locked and the *next* run fails to open it. The
pattern is `try/finally` (or a context manager): acquire → use → *guaranteed* release, even on
exception.

The loop's heartbeat is `cv2.waitKey(1)` — Unit 4's event-loop pump, now with a 1 ms poll so the
loop stays live. `waitKey(1) & 0xFF == 32` detects SPACE. And remember Unit 2: if you keep the
frame past this iteration, take `.copy()` — the buffer may be reused by the next `read()`.

```python
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("no camera at index 0")
try:
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        cv2.imshow("preview", frame)
        if cv2.waitKey(1) & 0xFF == 32:        # SPACE
            shot = frame.copy()                # detach from driver buffer
            break
finally:
    cap.release()
    cv2.destroyAllWindows()
```

### Why it matters here

This is `capture/webcam.py` and Phase 0 Step 0.2. The manual-keypress design (a project
constraint) is what keeps the loop lean enough that backpressure never bites. The `try/finally`
release habit is the same shape as closing DB connections in Phase 5 and not leaking resources in
Phase 6's Lambdas.

### Interview / system-design lens

This loop is a one-machine microcosm of producer-consumer systems: a producer (camera) at fixed
rate, a bounded queue (driver buffer), a consumer (your loop), and a policy question — drop,
buffer, or block? — when the consumer is slow. Being able to narrate webcam lag in queue-theory
terms is a neat trick.

### Labs

**Lab 8.1 — Measure your loop's cadence** *(builds on roadmap M9)*

M9 builds the preview loop. Instrument it: `time.perf_counter()` around each iteration, print a
rolling FPS every 30 frames. Then add `time.sleep(0.2)` inside the loop to simulate heavy
processing and wave your hand at the camera.

**Done when:** You can see the preview lag behind your hand and explain it as the driver queue
backing up — then fix it with `CAP_PROP_BUFFERSIZE` or by removing the sleep.

**Lab 8.2 — The stale-reference bug, live**

Capture 5 frames into a list *without* `.copy()` while moving an object through the scene, then
display all 5 after the loop. Repeat with `.copy()`.

**Done when:** You've observed whether your backend reuses buffers (many do), and you can defend
the rule "always `.copy()` a frame that outlives its loop iteration."

**Lab 8.3 — Context-manage the camera**

Wrap `VideoCapture` in a class with `__enter__`/`__exit__` so usage becomes
`with Camera(0) as cam:` and release is automatic even when the body raises. Test it by raising
inside the `with` and confirming the next run still opens the camera.

**Done when:** Two consecutive runs work even when the first one crashed mid-loop.

### Mini-project: Webcam photobooth

A live preview where number keys apply a filter (1 = grayscale, 2 = gray-world WB, 3 = heavy
denoise "beauty mode", 4 = threshold "sketch"), SPACE saves the filtered frame named by its
content hash (`{sha256[:12]}.jpg` — Unit 7 cameo), and Q quits cleanly via `try/finally`. Fun,
demo-able, and it integrates Units 2–8 into one running artifact.

### Check yourself

1. Why does a slow loop make the preview *lag* rather than just drop frames?
2. What's the difference between `grab()` and `retrieve()`, and why does the split exist?
3. Why `try/finally` around `cap.release()` — what's the failure mode without it?

---

## Unit 9 — OCR Fundamentals

### Concept

OCR (optical character recognition) turns pixels into text. **Tesseract** — the open-source
engine this project uses via `pytesseract` — works roughly like this: binarize the image, detect
text-line regions (page segmentation), then run each line through an LSTM neural network that
emits character probabilities, decoded into a string.

The decisive insight: **Tesseract was built for scanned documents** — flat, high-contrast, dark
text on a clean light background, in document-ish fonts. A sneaker tongue label is the opposite of
that on almost every axis, which is why raw frames produce garbage and *preprocessed crops*
produce clean SKUs. The failure modes, concretely:

- **Curved surfaces** — the tongue bows, so text lines bend; the line detector expects straight
  baselines.
- **Low contrast** — gray text on white satin labels under dim light; binarization smears it away.
- **Font confusion** — `0/O`, `1/I/l`, `8/B`, `5/S` in condensed industrial label fonts.
- **Clutter** — the whole frame contains laces, swooshes, floor; segmentation finds "text" in
  texture.

So OCR quality is mostly *preprocessing* quality: crop to the label region first, grayscale,
upscale (Tesseract likes ~30px-tall characters), threshold (Otsu), and tell Tesseract what to
expect via the page-segmentation mode — `--psm 7` means "treat this as a single text line," which
is exactly what a cropped SKU is:

```python
import pytesseract

text = pytesseract.image_to_string(
    label_crop_binary,
    config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-",
)
```

The second half of the lesson: **never trust OCR raw — validate the output structurally.** Brand
SKUs have known formats (a Nike style code is 6 alphanumerics, a dash, then 3 digits — e.g.
`CT8012-104`). A regex like `r"\b[A-Z0-9]{6}-[0-9]{3}\b"` plus format rules turns "OCR said
something" into "OCR found a *valid candidate*." Validation is what lets Phase 2 decide whether to
trust OCR or the LLM when they disagree: a format-valid OCR hit outranks an LLM guess.

### Why it matters here

This is Pillar 3 and `identify/ocr.py` + `identify/sku_validator.py` (Phase 2). It's also the
edge/cloud contrast in miniature: Phase 6 swaps Tesseract for Rekognition `DetectText` — same
job, assembled-by-you vs managed.

### Interview / system-design lens

"Garbage tolerance": any component with unreliable output (OCR, LLMs, user input) needs a
validation layer that converts *strings* into *typed, checked values* before the rest of the
system sees them. Parse at the boundary, don't validate later. The same pattern returns at full
strength in Unit 11.

### Labs

**Lab 9.1 — Watch preprocessing make or break it**

Photograph a sneaker tongue label (or any printed product label). Run `image_to_string` on:
(a) the raw frame, (b) a tight crop of the label, (c) the crop after grayscale + 2× upscale +
Otsu threshold + `--psm 7`. Record all three outputs side by side.

**Done when:** You have a table showing accuracy improving across (a)→(c), and you can name which
single step bought the most.

**Lab 9.2 — Build the SKU validator**

Write `extract_sku(text) -> str | None`: regex out candidates matching the Nike pattern, apply a
confusion-repair pass (`O→0`, `I→1`, `B→8` *in digit positions only*), and return the first
candidate that validates. Unit-test it against deliberately corrupted strings
(`"CT8O12-1O4"` → `"CT8012-104"`).

**Done when:** The validator repairs at least the `O/0` and `I/1` confusions and rejects
near-miss garbage (`"CT801-104"`, `"CT8012104"`).

**Lab 9.3 — Find the breaking angle**

Photograph the same label at 0°, ~20°, and ~45° of tilt and run your Lab 9.1 pipeline on each.

**Done when:** You know roughly the angle where OCR falls off a cliff for your camera — which
becomes user guidance ("hold the tongue flat to the lens") rather than a code fix. Knowing when
to fix the *capture instructions* instead of the algorithm is a real engineering judgment.

### Mini-project: Receipt line-item extractor

Feed your Unit 5 document-scanner output (or any flat receipt photo) through Tesseract with
`image_to_data` (which returns per-word boxes and confidences, not just a string). Regex out
`(item, price)` pairs, sum the prices, and compare to the printed total — a built-in correctness
check, just like SKU validation. Stretch: draw the detected word boxes back onto the image to
*see* what Tesseract saw.

### Check yourself

1. Why does Tesseract fail on a raw webcam frame but succeed on a thresholded label crop?
2. Why is format validation (regex + check rules) essential rather than nice-to-have?
3. In Phase 2, when OCR and the LLM disagree on the SKU, which wins and why?

---

## Unit 10 — HTTP, APIs & the Request-Response Lifecycle

### Concept

Every Gemini call is an HTTPS request. Knowing where the time and the failures live turns "the API
is slow/broken" into a diagnosable system. One call, dissected:

```
DNS lookup                  ~10–50 ms      (cached after first call)
TCP handshake               1 round trip
TLS handshake               1–2 round trips (certs, key exchange — now the channel is encrypted)
Upload request body         payload_size / bandwidth   ← your JPEG quality dial lives here
Server work (inference)     1–5 s          ← THE dominant term for an LLM call
Download response           usually small
```

The lesson in that table: for LLM APIs, **inference dominates**, and the only way to not pay it is
to not make the call — which is the entire justification for the Phase 5 cache. Upload time is the
one term *you* control per-call (Unit 6's compression).

Reused connections (HTTP keep-alive) skip DNS/TCP/TLS after the first call — why call #1 is always
slower.

**Failure handling**, the production trio:

- **Timeouts** — a request with no timeout can hang forever; your thread is hostage. Always set
  one. There are really two: connect timeout (can I reach the server?) and read timeout (is it
  still talking?).
- **Retries with exponential backoff** — transient failures (network blips, 5xx) deserve a retry,
  but immediate retries from many clients create a stampede. Back off exponentially (1s, 2s, 4s…)
  and add **jitter** (randomness) so a thousand clients don't all retry on the same beat.
- **429 rate limits** — the server saying "you, specifically, are over quota." Gemini's free tier
  is 1,500 req/day; you *will* see 429s during testing. Retrying a 429 hard is hostile and
  useless — honor the `Retry-After` hint, or better, stop spending calls (cache!).

**Secrets (12-factor config):** the API key never appears in code or git. It lives in a
git-ignored `.env` file, loaded into the process environment by `python-dotenv`, read via
`os.environ["GEMINI_API_KEY"]`. The principle — *config lives in the environment, not the
artifact* — is what lets identical code run locally (.env) and in Lambda (environment variables /
Secrets Manager) in Phase 6.

### Why it matters here

Phases 2–4 make three to five Gemini calls per verdict. Latency budget, retry policy, 429
handling, and the cache's reason for existing are all this unit. The `.env` discipline starts at
Phase 0 Step 0.3 and never relaxes.

### Interview / system-design lens

"Walk me through what happens when you call an API" is a literal interview prompt — the latency
table above *is* the answer. The follow-ups are also above: where does the time go (inference),
what do you control (payload), what breaks (timeouts/5xx/429), and what's the systemic fix
(cache + backoff with jitter).

### Labs

**Lab 10.1 — Time the phases** *(builds on roadmap M11)*

M11 makes the first Gemini text call. Instrument it: wrap the call in `time.perf_counter()` and
make the same trivial request 5 times in a loop with one client object.

**Done when:** Call 1 is measurably slower than calls 2–5, and you can attribute the difference
(connection setup amortized away by keep-alive).

**Lab 10.2 — Write `retry_with_backoff`**

A generic wrapper: takes a zero-arg function, retries on exception up to `max_attempts`, sleeping
`base * 2**attempt + random.uniform(0, jitter)` between tries, re-raising after the last. Test it
against a fake function that fails twice then succeeds — *no network needed*, and you've just
discovered why injectable failure beats real failure for testing (Unit 16 foreshadowed).

**Done when:** A pytest run proves: succeeds on attempt 3, raises after `max_attempts`, and the
sleep sequence is exponential (capture sleeps by injecting a fake `sleep`).

**Lab 10.3 — Leak a secret, then un-leak it (drill)**

In `experiments/`, hardcode a *fake* key in a script, commit it, then practice the recovery:
remove it, move it to `.env`, confirm `.env` is in `.gitignore`, and note that the fake key is
still in git history (`git log -p`) — which is why a real leaked key must be **rotated**, not just
deleted.

**Done when:** You can state the full incident response for a leaked key: rotate first, then
scrub.

### Mini-project: API latency profiler

A CLI that calls any public JSON API (e.g. `httpbin.org/delay/1`) N times and prints a latency
histogram plus p50/p95/p99 — using `requests` with explicit timeouts and your Lab 10.2 backoff
wrapper. Stretch: add a `--payload-kb` flag that POSTs random bytes of that size and observe how
upload size moves the latency. You're building the intuition that p99 ≠ p50, which is half of
system-design interviews.

### Check yourself

1. For a Gemini vision call, rank the latency contributors — and which one does the cache delete?
2. Why jitter on top of exponential backoff?
3. Why does a 429 deserve different treatment than a 503?

---

## Unit 11 — Vision-Language Models & Multimodal LLMs

### Concept

How does a language model "see"? The image is cut into a grid of fixed-size **patches** (e.g.
16×16 pixels). Each patch is flattened and projected into an embedding vector — the same kind of
vector a text token becomes. The image thus enters the model as a *sequence of image tokens*
interleaved with your text tokens, and the transformer attends across both. The model then
generates its answer **autoregressively** — one token at a time, each conditioned on everything
before — which is why inference latency scales with *output* length and why asking for terse
output is a real optimization.

Two practical consequences of "image → patches → tokens":

- Resolution beyond what the model ingests is wasted upload. This is partly why the canonical
  size is 1024×1024 — past a point, more pixels are just latency.
- Fine details (stitch counts!) can fall below patch granularity. When detail matters, send a
  *crop* of the detail region, not a smaller overview — same pixels, more patches on target.

**Structured output:** by default a model returns prose, and prose is un-parseable. You want JSON
matching a schema. The `google.genai` SDK supports enforcing this:

```python
import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
resp = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=[
        types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"),
        "Identify this sneaker. Return brand, model, colorway, sku, confidence 0-1.",
    ],
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ProductID,        # a pydantic-style schema class
    ),
)
```

Even with schema enforcement, **treat the response as untrusted input**. Models return fenced
code blocks, trailing prose, `null` where you expected a string, confidences of `"high"` instead
of `0.9`. The robustness of your system lives in the **parser**, not the prompt: a function that
takes raw text and returns either a *validated typed object* or a *typed failure*
(`UNPARSEABLE`), never a half-trusted dict. Parsers are pure functions — cheap to test
exhaustively (Unit 16), unlike the network call they guard.

**The `VisionClient` interface:** wrap all model access behind one abstraction —

```python
class VisionClient(Protocol):
    def identify(self, image: bytes) -> ProductID: ...
    def lookup_reference(self, sku: str) -> ReferenceDossier: ...
    def compare(self, image: bytes, reference: ReferenceDossier, pillar: str) -> PillarScore: ...
```

— so Gemini is an *implementation*, not a load-bearing assumption. Swapping in Claude or GPT-4V
later means writing one new class, not touching the pipeline. This is dependency inversion: the
pipeline depends on the interface; implementations depend on vendors.

### Why it matters here

Phases 2 and 4 are entirely this unit: `identify/gemini_vision.py`, `verdict/compare.py`, and
their parsers. The crop-for-detail insight directly shapes how Pillar 1 sends stitching close-ups.

### Interview / system-design lens

"How would you integrate an LLM into a production system?" Strong answer shape: typed interface
boundary (VisionClient), schema-constrained output, a defensive parser that yields typed
results-or-failures, retries/timeouts from Unit 10, and a cache from Unit 14. That's this
project's exact architecture — you'll be describing something you built.

### Labs

**Lab 11.1 — Patch-budget intuition**

Send Gemini the same sneaker photo twice: once full-frame, once as a tight crop of just the
stitching region (same JPEG quality). Ask both times: "Describe the stitching pattern in detail."

**Done when:** You can articulate the difference in answer specificity and explain it via patch
allocation.

**Lab 11.2 — Harden the parser** *(builds on roadmap M12)*

M12 builds `parse_yes_no`. Build its bigger sibling: `parse_product_json(text) -> ProductID |
ParseFailure` that survives: a fenced ```` ```json ```` block, leading prose ("Sure! Here's the
JSON:"), missing keys, `confidence: "0.9"` as a string, and pure garbage. Write the pytest cases
*first* from that list, then implement until green.

**Done when:** 8+ parametrized cases pass and none of them required network access.

**Lab 11.3 — Two implementations, one interface**

Define the `VisionClient` Protocol, then write `FakeVisionClient` (returns canned responses
instantly) alongside `GeminiVisionClient`. Run the same little driver script against both.

**Done when:** The driver doesn't know or care which client it got — and you realize the fake is
also your offline test double for all of Unit 16.

### Mini-project: "What's in my fridge?"

Photograph your open fridge with the webcam, send it through your `GeminiVisionClient` with a
schema asking for `{items: [{name, count, shelf}]}`, parse defensively, and print a shopping-list
diff against a hardcoded "want" list. Silly, fast, and a complete rep of the
capture→encode→model→parse→typed-output pipeline on a non-sneaker domain.

### Check yourself

1. How does an image physically enter a transformer, and what does that imply about crops vs
   full frames?
2. Why does robustness live in the parser rather than the prompt?
3. What does the VisionClient interface buy you, concretely, the day Gemini's free tier changes?

---

## Unit 12 — Prompt Engineering for Explainable Verdicts

### Concept

You could ask one big question — "Is this shoe fake? Look at everything." — and get back a
confident paragraph. The problem isn't accuracy; it's **explainability and failure isolation**.
One blended answer gives you no way to see *which* evidence drove it, no way to detect internal
contradiction, and no way to tune one signal without re-prompting everything.

The three-pillar decomposition fixes this by making each signal its own constrained call:

```
Pillar 1: logo / stitching / materials   →  {score: 0..1, evidence: "..."}
Pillar 2: sole pattern / silhouette      →  {score: 0..1, evidence: "..."}
Pillar 3: serial / SKU (OCR-grounded)    →  {score: 0..1, evidence: "..."}
```

Each prompt is narrow ("Compare ONLY the stitching and logo of image A against reference images
B. Ignore everything else."), asks for a numeric score *plus cited evidence*, and returns schema
JSON through your Unit 11 parser. Narrow prompts get better answers — the model can't pad a
constrained question with vibes — and three independent numbers are something you can *do math
on*.

**Synthesis** then becomes deterministic code, not model judgment:

```python
def synthesize(p1, p2, p3, w=(0.3, 0.3, 0.4)) -> Verdict:   # serial weighted highest
    scores = (p1.score, p2.score, p3.score)
    agg = sum(s * wi for s, wi in zip(scores, w))
    if max(scores) - min(scores) > 0.5:        # pillars disagree → surface it
        return Verdict("SUSPICIOUS", agg, conflict=True)
    if agg >= 0.75:
        return Verdict("GENUINE", agg)
    if agg <= 0.35:
        return Verdict("COUNTERFEIT", agg)
    return Verdict("SUSPICIOUS", agg)
```

Notes on that code: serial-number disagreement is the strongest fake signal, hence the weighting;
the *disagreement check* runs before the thresholds, because pillars conflicting is information
the average would hide; and the thresholds are named constants you can tune against the feedback
log (Phase 5) without touching any prompt.

**`SUSPICIOUS` is a designed state, not an error path.** A binary classifier forced to choose on
conflicting evidence destroys exactly the signal a human verifier most needs ("the shoe looks
right but the serial doesn't validate — check the label"). The middle state plus per-pillar
evidence *is* the product.

### Why it matters here

This is Phase 4 — `verdict/pillars.py`, `compare.py`, `synthesize.py` — and the constraint in
CLAUDE.md ("do not collapse these into a single LLM call") is this unit's thesis.

### Interview / system-design lens

This is **ensembling and separation of concerns applied to LLMs**: independent weak judges +
deterministic aggregation beats one opaque judge whenever you need explainability, tunability, or
audit trails. It's also the "LLM as component, not oracle" pattern — keep the model inside narrow,
typed boxes and keep the *decision logic* in code you can test.

### Labs

**Lab 12.1 — One prompt vs three, empirically**

Take one sneaker photo and 2–3 reference images (screenshots from a product page are fine for the
lab). Run (a) one mega-prompt asking for an overall verdict, and (b) three pillar prompts + your
`synthesize`. Do this for a genuine-looking pairing and a deliberately mismatched one (photo of
shoe A vs references for shoe B).

**Done when:** You can show a case where the mega-prompt was confidently smooth while the pillar
version surfaced *which* signal disagreed.

**Lab 12.2 — Tune `synthesize` without any network**

Using `FakeVisionClient` (Lab 11.3) to fabricate pillar scores, write parametrized tests for
`synthesize`: all-high → GENUINE, all-low → COUNTERFEIT, `(0.9, 0.9, 0.2)` → SUSPICIOUS with
conflict, boundary values exactly at 0.75 and 0.35. Then change the weights and watch which tests
break.

**Done when:** You have a deterministic test suite over the decision logic and can explain why
the serial pillar carries the largest weight.

**Lab 12.3 — Evidence quality pass**

Rewrite one pillar prompt three ways: (a) "score this 0-1", (b) score + "explain briefly",
(c) score + "cite at most 3 specific visual observations, each naming a location on the shoe."
Compare the usefulness of the evidence strings.

**Done when:** You've adopted a prompt format whose evidence a human could actually act on, and
written it down as the Phase 4 template.

### Mini-project: Rock-paper-scissors referee

Webcam captures two hands (yours and a friend's, or two photos); two narrow Gemini calls — "what
gesture is in this image?", each returning schema JSON — then a deterministic ruler decides the
winner, with an `UNCLEAR` verdict when either gesture parse is low-confidence. It's the pillar
pattern in miniature: narrow perception calls, typed parses, decision logic in code, a designed
middle state.

### Check yourself

1. What three concrete things do you lose by collapsing the pillars into one prompt?
2. Why does the disagreement check run *before* the threshold check in `synthesize`?
3. Who is the `SUSPICIOUS` verdict *for*, and what do they do with it?

---

## Unit 13 — Grounding vs Scraping

### Concept

The verdict needs ground truth: what does SKU `CT8012-104` *officially* look like? Two ways to
get it from the web:

**Custom scraping (Playwright):** drive a real browser, navigate to Nike/StockX/GOAT, select DOM
elements, extract image URLs. Maximum control, total fragility: you're coupling your code to
another company's HTML, which changes without notice, plus anti-bot escalation (challenges,
fingerprinting, IP blocks) that you fight forever. The deeper issue is **structural coupling**: a
scraper encodes assumptions about page structure, and every assumption is a future breakage.

**LLM grounding:** Gemini's Google Search grounding tool lets the model issue *real Google
searches* mid-generation and compose an answer **with citations** from the live results:

```python
resp = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=f"Find the official product page, colorway details, and known counterfeit "
             f"indicators for sneaker SKU {sku}. Cite sources.",
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
    ),
)
# resp.candidates[0].grounding_metadata carries the cited sources
```

You trade away control (you can't choose the exact image crop) for resilience (no selectors to
break) and one less subsystem to maintain. The grounding metadata's citations matter: an
ungrounded LLM asked about a SKU will *hallucinate plausible product details* — grounding tethers
the answer to retrieved pages, and the citations let you verify it did.

The decision rule generalizes: **scrape when you need exact structured data from a small set of
stable pages; ground when you need good-enough synthesis across a changing open web.** This
project picks grounding and keeps a Playwright scraper as an optional Phase 3.5 *comparison
exercise* — the point is to feel the tradeoff, not to win it.

Either way, the result is a **reference dossier** cached by SKU (not by image hash — every photo
of the same model shares one dossier). Dossiers change rarely, so TTL is long (7 days), and the
expensive lookup amortizes across all future checks of that model. Note the system now has *two*
caches with different keys and lifetimes: `verdict:{image_hash}` (24h/30d) and `dossier:{sku}`
(7d) — different data, different volatility, different TTLs.

### Why it matters here

This is Phase 3: `reference/grounding.py`, optional `reference/scraper.py`, and
`reference_cache.py`. The dossier's quality bounds the verdict's quality — comparison against bad
references produces confident nonsense.

### Interview / system-design lens

This is the **build-vs-buy / control-vs-resilience tradeoff** with current vocabulary, plus a RAG
talking point: grounding ≈ retrieval-augmented generation operated by the provider. Knowing *when
each loses* is the senior answer: grounding loses when you need pixel-exact official imagery;
scraping loses when maintenance cost exceeds the data's value.

### Labs

**Lab 13.1 — Hallucination vs grounding, A/B**

Ask Gemini about a real SKU twice: once with no tools, once with Google Search grounding enabled.
Then repeat both for a *plausible but fake* SKU (`CT9999-999`).

**Done when:** You've captured a case where the ungrounded call confabulated details for the fake
SKU and the grounded call hedged or came back empty — and you can explain why citations are the
tell.

**Lab 13.2 — Parse the dossier**

Define a `ReferenceDossier` schema (`{sku, official_urls: [...], image_urls: [...],
counterfeit_indicators: [...]}`), run a grounded lookup for a popular SKU, and parse the response
+ grounding metadata into the schema with your Unit 11 defensive-parser discipline.

**Done when:** `get_reference("CT8012-104")` returns a validated dossier object with at least one
cited source, or a typed failure.

**Lab 13.3 — Feel the scraper's pain (optional, Phase 3.5 preview)**

`pip install playwright; playwright install chromium`. Write a 30-line scraper that loads a
product page on one reseller site and extracts the main image URL via a CSS selector. Then open
devtools and ask: how many distinct assumptions (selectors, URL shape, load timing) did those 30
lines make?

**Done when:** You can list 4+ breakage points in your own scraper — the brittleness argument,
felt firsthand.

### Mini-project: Album-art dossier builder

Pick 5 music albums; for each, do a grounded Gemini lookup ("official cover art description,
release year, label — cite sources") and build a little JSON dossier cache keyed by album name,
with a 7-day TTL stamp. Second run must hit the cache and make zero API calls (print which path
served each). It's Phase 3's exact shape — grounded lookup → typed dossier → keyed cache — on a
domain where you can verify the answers instantly.

### Check yourself

1. Why does a scraper break more often than a grounded lookup, structurally?
2. Why is the dossier cached by SKU rather than image hash, and why is its TTL longer than the
   verdict's?
3. What signal tells you a grounded answer is actually grounded?

---

## Unit 14 — Caching

### Concept

A cache is a smaller, faster store in front of a slower, expensive operation. Here the expensive
operation is brutal: a full verdict costs 3–5 Gemini calls ≈ 5–15 seconds and burns daily quota.
A repeat capture of the same shoe should cost a sub-millisecond lookup instead.

**The cache-aside (read-through) pattern** — the one this project uses:

```python
key = sha256(canonical_bytes)               # Unit 7's contract
cached = r.get(f"verdict:{key}")
if cached is not None:                      # HIT — done in <1 ms
    return Verdict.from_json(cached)
verdict = run_full_pipeline(frame)          # MISS — pay the 5-15 s
r.set(f"verdict:{key}", verdict.to_json(), ex=86400)   # populate, TTL 24h
return verdict
```

The application owns the logic; the cache is a dumb fast map. (Alternatives like write-through
matter when writes are the hot path — here reads are.)

**Why Redis and not SQLite for this?** Redis keeps everything in RAM and serves each command from
a single-threaded event loop — no disk seek, no SQL parse, no file-lock contention; a GET is
microseconds. SQLite *would* return the right answer, but through a filesystem path that can
block. The deeper reason is role separation: Redis is the disposable hot path (lose it, you only
re-pay some Gemini calls), SQLite is the durable record (Unit 15). Also strategic: Redis's API is
identical to ElastiCache's, so Phase 5 code ports to Phase 6 untouched.

**TTL (time-to-live)** is expiry-on-write: `SET key val EX 86400` and Redis serves the key for
24h, then treats it as absent. TTL answers "how long until this answer might be stale?" For a
*model prediction*, 24h. For a *human-confirmed* verdict, 30 days — humans outrank models, and
their answers age slower.

**Invalidation under writes** — the famous hard problem, in concrete form: the user says the
verdict was wrong. TTL expiry is *not* the fix (up to 24 more hours of serving a known-wrong
answer). The fix is an **explicit overwrite at the moment of feedback**: write the corrected
verdict over the cache entry with the 30-day TTL. The rule: TTL handles *staleness you can't
observe*; explicit invalidation handles *staleness you just observed*. Never use the first where
you have the second.

Run it locally: `docker run -d --name redis -p 6379:6379 redis:7`, then `pip install redis`,
`r = redis.Redis()`, `r.set(...)` / `r.get(...)`.

### Why it matters here

Phase 5 entire: `cache/redis_client.py` and `cache/invalidate.py`. Also the economic core of the
project — the cache is what makes a 1,500-req/day free tier survivable.

### Interview / system-design lens

Cache-aside vs write-through, TTL strategy, and "how do you handle invalidation?" are the most
reliably-asked caching questions there are. This project gives you a concrete story for the
hardest one: *feedback-triggered explicit overwrite, with TTL as the backstop, and differentiated
TTLs by confidence source* — that's a senior-sounding answer because it is one.

### Labs

**Lab 14.1 — Touch real Redis** *(builds on roadmap M13)*

M13 builds the dict-with-TTL cache. Now swap the backend: start Redis in Docker and rewrite M13's
`Cache` class against `redis.Redis` with the same `get/set(ttl)` interface — your M13 *tests
should pass unchanged* against the new backend. Use `r.ttl(key)` to watch a key's remaining
lifetime tick down.

**Done when:** The same test file passes against both the dict cache and Redis (parametrize the
fixture over both backends) — you've just demonstrated why interfaces matter.

**Lab 14.2 — Measure the speedup honestly**

Wrap a deliberately slow function (`time.sleep(2)` standing in for Gemini) in cache-aside. Time
the 1st call, the 2nd call, and a call after `r.delete(key)`.

**Done when:** You can report the hit/miss latency ratio and explain which real-world cost the
`sleep` is impersonating.

**Lab 14.3 — The invalidation moment**

Simulate the feedback flow: populate `verdict:abc` with `("GENUINE", ttl=86400)`; a "user" says
it's wrong; overwrite with `("COUNTERFEIT", ttl=2592000)`; read it back and check both value and
`r.ttl`.

**Done when:** The corrected value reads back with the 30-day TTL, and you can say in one sentence
why waiting for expiry would have been wrong.

### Mini-project: TTL cache CLI

A small command-line key-value tool over Redis: `kv set <key> <value> --ttl 60`, `kv get <key>`,
`kv ls` (SCAN over a namespace prefix, show each key's remaining TTL), `kv watch <key>` (poll and
print the countdown until expiry, then "MISS"). Watching a key die in real time makes TTL
semantics permanent knowledge. Stretch: add `kv set --if-newer` using a version field — a first
taste of write conflicts.

### Check yourself

1. Walk the cache-aside flow for a hit and a miss — who writes the cache, and when?
2. Why two different TTLs (24h vs 30d), and what does each encode?
3. When is TTL the right invalidation tool, and when is it the wrong one?

---

## Unit 15 — Persistence: SQLite & the Feedback Log

### Concept

Redis answers "what do we currently believe?" fast, and forgets. Something must remember
*everything that happened* — every verdict issued, every human correction — durably, across
restarts, forever. That's the persistence layer, and for the edge build it's **SQLite**: a full
SQL database that lives in one file, runs *inside your process* (no server, no port, no
password), and ships in Python's standard library (`import sqlite3`).

Schema for this project:

```sql
CREATE TABLE IF NOT EXISTS verdicts (
    image_hash  TEXT NOT NULL,
    label       TEXT NOT NULL,             -- GENUINE / SUSPICIOUS / COUNTERFEIT
    score       REAL NOT NULL,
    evidence    TEXT NOT NULL,             -- JSON blob of pillar breakdown
    created_at  TEXT NOT NULL              -- ISO-8601 UTC
);

CREATE TABLE IF NOT EXISTS feedback (
    image_hash      TEXT NOT NULL,
    predicted_label TEXT NOT NULL,
    actual_label    TEXT NOT NULL,
    user_note       TEXT,
    created_at      TEXT NOT NULL
);
```

The design decision worth dwelling on: **feedback is append-only.** You never UPDATE or DELETE a
feedback row. If the user corrects the same shoe twice, that's two rows; "current truth" is the
*latest* row per hash (a `MAX(created_at)` query), but the full history survives. Why this
matters: an event log preserves information an overwrite destroys — *how often* the model is
wrong, *whether users flip-flop*, *when* accuracy changed. The mutable "current state" lives in
Redis (Unit 14's overwrite); the immutable "what happened" lives here. State vs log — keep them
separate and each stays simple.

Mechanics you need: parameterized queries — always
`conn.execute("INSERT INTO feedback VALUES (?,?,?,?,?)", row)`, never f-strings (SQL injection,
plus correct quoting for free); transactions — `with conn:` commits on success and rolls back on
exception; and `PRAGMA journal_mode=WAL` for saner concurrent reads.

The cloud rhyme: in Phase 6, this exact access pattern (`get latest by image_hash`, `append
feedback row`) maps onto DynamoDB items keyed by `image_hash` — same shape, managed service.
Designing the SQLite schema around key-value access *now* is what makes the port mechanical
*later*.

### Why it matters here

Phase 5's `cache/feedback.py`. The feedback log is also the project's future training signal —
the architecture notes call for mining it to improve Phase 4's comparison prompts.

### Interview / system-design lens

"Cache vs database — why both?" and "event log vs mutable state" are core distinctions.
Append-only feedback is a pocket-sized example of event sourcing; being able to say *why* you
chose append-only (history is data) is the interesting part.

### Labs

**Lab 15.1 — Build the feedback table**

In `experiments/`, write `feedback_db.py`: `init(path)`, `record(hash, predicted, actual, note)`,
`latest(hash)`, `accuracy()` (fraction of rows where predicted == actual). Use parameterized
queries and `with conn:` throughout.

**Done when:** Recording three corrections for one hash leaves three rows, `latest` returns the
newest, and `accuracy()` computes over all of them.

**Lab 15.2 — Prove durability vs Redis**

Write a value into Redis and a row into SQLite. Restart the Redis container with a wipe
(`docker rm -f redis` then re-run the container) and re-run your reader.

**Done when:** You've watched the cache forget and the database remember, and can map each
behavior to its role.

**Lab 15.3 — Injection drill**

Take a copy of `record()` and rewrite it with an f-string. Pass
`note = "x'); DROP TABLE feedback;--"`. Watch what happens (sqlite3's single-statement `execute`
actually blunts this one — figure out *why*, then construct an input that still corrupts the data
semantically, e.g. a quote that breaks the value). Restore the parameterized version.

**Done when:** You can explain what parameterized queries actually do (separate the query *plan*
from the *data*) rather than just reciting "prevents injection."

### Mini-project: Personal metrics logger

A two-command CLI: `log <metric> <value> [--note]` appends `(metric, value, note, timestamp)` to
SQLite; `report <metric>` prints count/min/max/mean and a sparkline-ish ASCII trend of the last 30
entries. Strictly append-only — a `correct` command adds a superseding row rather than editing.
Use it for anything real (pushups, sleep) for a week; nothing teaches schema design like your own
data coming back at you.

### Check yourself

1. Why does the feedback write touch *both* Redis and SQLite, and what different thing does each
   write accomplish?
2. What information does append-only preserve that UPDATE destroys?
3. Why are parameterized queries non-negotiable even in a single-user local tool?

---

## Unit 16 — Testing & Debugging as a Practiced Skill

### Concept

Testing is asking, per function: *"if this were silently wrong, what input exposes it?"* Three
inputs per function, always (roadmap's trichotomy, now formalized):

- **Happy path** — normal input → expected output.
- **Edge case** — boundaries: empty, smallest/largest valid, 0, 255, the exact-expiry instant.
- **Failure case** — invalid input fails *loudly* with a typed/clear error, never garbage.

**pytest structure.** Each test is arrange/act/assert. Shared setup goes in **fixtures**;
repeated cases go in **parametrize**:

```python
import pytest

@pytest.fixture
def shoe_frame():
    img = cv2.imread("experiments/fixtures/shoe_001.jpg")
    assert img is not None
    return img

@pytest.mark.parametrize("text,expected", [
    ("YES", True), ("yes.", True), ("Yes, it is", True),
    ("NO", False), ("I cannot determine", None),
])
def test_parse_yes_no(text, expected):
    assert parse_yes_no(text) == expected
```

**The two test-enabling design moves** this project leans on:

1. **Inject the clock.** TTL logic compared against `time.time()` forces tests to `sleep()` —
   slow and flaky. Instead the cache takes `now: Callable[[], float] = time.time` as a parameter;
   tests pass a fake they can advance instantly. Generalization: any nondeterminism (time,
   randomness, network) injected as a parameter becomes controllable in tests. This is dependency
   injection earning its keep.
2. **Fixtures stand in for hardware and networks.** You can't unit-test a webcam or Gemini — so
   you design **seams**: the preprocess chain takes *an ndarray* (a saved fixture file works as
   well as a live frame); the pipeline takes *a VisionClient* (the `FakeVisionClient` from
   Lab 11.3 works offline). Hardware and network live only at the outermost edge, behind
   interfaces, with thin untested adapters.

**CV debugging has one special move: save the intermediate image.** You cannot `print` a picture,
and `array([[[ 34, 41, ...` tells you nothing. So instrument pipelines to dump each stage —
`debug/01_raw.jpg`, `02_denoised.jpg`, `03_balanced.jpg`, `04_cropped.jpg` — and *look*. The
broken stage is the first image that looks wrong. This is printf-debugging adapted to data your
eyes parse better than your terminal does.

**Break code on purpose.** A test that has never failed proves nothing — maybe it asserts
nothing. Discipline: after writing a test, sabotage the code (flip a comparison, off-by-one a
boundary) and confirm the test goes red, then revert. Every roadmap module's "debugging drill" is
this idea; manual mutation testing is its name.

### Why it matters here

Every prior unit's labs produced parsers, validators, caches, and pipelines — this unit is how
you keep them working while the project grows around them. Phase 4's `synthesize` thresholds and
Phase 5's TTL boundaries are exactly the kind of logic that rots without tests.

### Interview / system-design lens

"How do you test code that depends on time / a camera / an external API?" is a real question with
one real answer: *design seams, inject the dependency, fake it in tests.* Testability isn't a
testing topic — it's an architecture topic, and saying it that way is the senior framing.

### Labs

**Lab 16.1 — Retrofit the trichotomy** *(builds on roadmap M13's pytest suite)*

Pick three functions you've built in earlier units (suggested: `gray_world`, `extract_sku`,
`frame_key`). For each, write exactly one happy, one edge, one failure test. The failure tests
will likely force you to *add* the loud-failure behavior — that's the point.

**Done when:** 9 tests pass, and at least one function got a new explicit `raise` because the
failure test demanded it.

**Lab 16.2 — De-flake a sleeping test**

Write the *bad* version first: a TTL cache test that uses `ttl=1` and `time.sleep(1.1)`. Time the
suite. Now refactor the cache to take an injectable `now`, rewrite the test with a fake clock you
advance manually, and probe the *exact* expiry boundary (`now == expiry`: hit or miss? pick and
test the contract).

**Done when:** The suite drops from seconds to milliseconds, and the boundary semantics are pinned
by a test that would catch a `<` vs `<=` regression.

**Lab 16.3 — The intermediate-dump harness**

Write `run_pipeline(img, debug_dir=None)` for your Unit 5 preprocess chain: when `debug_dir` is
set, every stage writes `NN_stagename.jpg`. Then sabotage one middle stage (skip the BGR→RGB
conversion, or swap resize axes) and — looking only at the dumped images — identify which stage
broke.

**Done when:** You located the sabotaged stage from the images alone, without reading the code.

**Lab 16.4 — Mutation hour**

Take your best existing test file. Introduce five separate single-character mutations into the
code under test (one at a time): flip `<` to `<=`, change a `0.75` to `0.74`, swap two arguments,
return early, off-by-one a slice. Record which mutations your tests caught.

**Done when:** You've added tests for every mutation that survived, or consciously documented why
a survivor doesn't matter.

### Mini-project: Test a stranger's function

Find any small pure-Python utility (a snippet from a blog, an old script of yours, a single
function from a library's source). Without modifying it, write a pytest file that fully
characterizes its behavior — including its weird edges (what *does* it do on empty input?). Then
write down two behaviors you found that you'd call bugs. Characterization testing — pinning down
what code *actually does* before changing it — is the single most useful testing skill for
real-world legacy code.

### Check yourself

1. Why is a test that has never failed not yet trustworthy?
2. How do you test TTL expiry without sleeping, and what general principle is that an instance of?
3. Your preprocessed output looks wrong. What is your literal first move?

---

## Unit 17 — Cloud Port Fundamentals

### Concept

Phase 6's thesis: **same logic, different orchestration.** On the edge, one Python process calls
functions in sequence. In the cloud, each step becomes an independently-deployed unit and the
"function calls" become **events** flowing between managed services.

**Event-driven architecture.** Instead of `process_frame(frame)` as a call, the client PUTs the
frame to S3, and S3 *emits an event* (a JSON notification: bucket, key, size) that AWS delivers
to a subscribed Lambda. The caller and the processor never meet — they're coupled only by the
event contract. That decoupling buys independent scaling, retries, and fan-out; it costs you
end-to-end visibility (hence structured logging and request IDs become survival gear, not
nice-to-haves).

**Lambda** is functions-as-a-service: you ship a handler (`def handler(event, context)`) plus its
frozen dependency set (Unit 1's resolved-set lesson, now load-bearing — the deploy zip *is* a
frozen `site-packages`). AWS runs it on demand and bills per millisecond. The catch: **cold
starts.** The first invocation after idleness must provision a sandbox, load your code, and run
imports — hundreds of ms to seconds (heavy imports like big SDKs hurt; this is why Lambda people
get obsessive about import weight). Warm invocations reuse the sandbox and skip all that.

**Why split `cache_check` from `process_frame`:** the cache-hit path should cost ~10 ms of warm
Lambda + one ElastiCache GET — no S3 write, no Rekognition, no Gemini. Folding both paths into
one function means the cheap path drags the expensive path's dependencies (cold-start weight) and
its failure modes. Splitting keeps the cheap path cheap and lets you target cold-start mitigation
(provisioned concurrency) at just the latency-sensitive function. This is the granularity
question of serverless design: split where cost/latency/scaling profiles differ.

**API Gateway** is the managed front door: HTTPS termination, routing (`/check`, `/feedback`,
`/health`), auth, throttling — everything you'd otherwise hand-roll in a web framework, as
config.

**Rekognition vs rolling your own:** `DetectText` replaces the Tesseract pipeline (and handles
angled/curved text better, because it's a modern detection+recognition model, not a document
engine); `DetectLabels` gives a cheap "is this even Footwear?" sanity gate before spending Gemini
calls. The boundary to respect: Rekognition *labels*, it doesn't *reason* — verdicts stay with
Gemini. Managed CV trades your control and your tuning knobs for zero maintenance and native
IAM/event integration. That trade is the entire edge-vs-cloud lesson of the project, localized to
one service swap.

**DynamoDB vs RDS:** our access pattern is pure key-value — `get verdict by image_hash`, `append
feedback by image_hash` — no joins, no ad-hoc queries. DynamoDB models this as items under a
**partition key** (the key is hashed to decide which storage partition holds the item — Unit 7's
hashing, now placing data). It scales to zero cost when idle and needs no VPC. RDS would add
connection pools, idle billing, and network plumbing to answer queries we never ask. Rule: choose
the database by *access pattern*, not by familiarity.

**IAM least privilege:** every Lambda gets its own execution role listing exactly the actions it
needs — `cache_check` can read ElastiCache but cannot touch S3; `process_frame` can
`rekognition:DetectText` and `dynamodb:PutItem` on *one table*, nothing else. Why so strict:
credentials leak and code gets confused; least privilege converts "compromise" into "contained
incident." Think of it as type-checking for authority.

**Infrastructure-as-Code:** clicking the AWS console produces unreproducible state. Terraform
(declarative HCL, multi-cloud, huge transferable mindshare) or AWS CDK (your infra in Python,
synthesizes CloudFormation) make the infrastructure a reviewed, versioned, re-applyable artifact —
`git diff` for your cloud. Either works here; CDK keeps the whole project in Python, Terraform
teaches the broader-market tool.

### Why it matters here

This is Phase 6 wholesale. Every prior unit reappears wearing a managed-service costume: venv →
Lambda package, hash → S3 key + DynamoDB partition key, Redis → ElastiCache, retry/backoff → SDK
config and DLQs, `.env` → Lambda environment config / Secrets Manager, the split pipeline →
per-Lambda decomposition.

### Interview / system-design lens

"Design an image-processing pipeline on AWS" is a stock interview prompt, and Phase 6's diagram —
API Gateway → fast-path Lambda → S3 event → worker Lambda → managed CV + external LLM → DynamoDB +
ElastiCache — *is* a reference answer. Rehearse narrating it with the why's: split for the cheap
path, S3 events for decoupling, DynamoDB for the access pattern, IAM per function.

### Labs

(These need an AWS account; free tier covers all of them. Tear down everything after — that's
Lab 17.4's actual point.)

**Lab 17.1 — One Lambda, by hand first**

In the console (deliberately — feel what IaC later automates), create a Python Lambda that logs
its `event` and returns `{"statusCode": 200, "body": "warm"}`. Invoke it from PowerShell via
`aws lambda invoke --function-name ... out.json`. Invoke twice and compare durations in the
CloudWatch logs — find the `Init Duration` line on the first.

**Done when:** You can point at the cold start in the logs and state its cause in one sentence.

**Lab 17.2 — The S3 event trigger**

Create a bucket; subscribe your Lambda to `s3:ObjectCreated:*`; upload a JPEG with
`aws s3 cp shoe.jpg s3://your-bucket/frames/`. Read the event JSON your Lambda logged — find the
bucket name, object key, and size inside the nested structure.

**Done when:** Uploading a file runs your code with no explicit call anywhere, and you can sketch
the event JSON's shape from memory.

**Lab 17.3 — Rekognition vs your Tesseract**

From your *local* machine (`boto3.client("rekognition").detect_text(Image={"Bytes": jpeg})`), run
DetectText on the same label photos from Lab 9.1, including the 45° one that broke Tesseract.
Compare outputs and per-detection confidence scores.

**Done when:** You have a side-by-side table (Tesseract vs Rekognition, per photo) and a sentence
on what the managed service bought and what it cost (per-call price, network dependency, no
tuning knobs).

**Lab 17.4 — IaC round trip**

Reproduce Labs 17.1–17.2 as code: a minimal Terraform config (or CDK app) defining the bucket,
the Lambda, its least-privilege role (only `logs:*` for its own log group and the S3 read it
needs), and the event notification. `terraform apply`, verify the trigger works, then
`terraform destroy` and confirm the console is empty.

**Done when:** Apply→verify→destroy leaves zero residue, and you've felt why "the infra is a
reviewable file" beats "the infra is what someone clicked."

### Mini-project: Serverless drop-box thumbnailer

End-to-end mini-pipeline, IaC from the start: S3 `uploads/` prefix → event → Lambda that resizes
the image with Pillow to a 256px thumbnail → writes to `thumbs/` (guard against re-triggering on
its own output — a classic event-loop-of-doom bug worth meeting now) → logs a record to a
DynamoDB table keyed by the file's sha256. It's the cloud pipeline shape of Phase 6 in miniature,
with Units 1, 5, 7, and 17 all in play.

### Check yourself

1. Why split `cache_check` from `process_frame` — name the cost it avoids and the property it
   enables.
2. What makes a cold start slow, and which Phase 6 function gets mitigation money? Why that one?
3. Why DynamoDB over RDS *for this project's access pattern* — and what pattern would flip the
   answer?

---

## Concept Dependency Ladder

```
                              EDGE                                               CLOUD

 U1 venv & isolation ────────────────────────────────────────────────► (Lambda packaging)
  │        [Phase 0 · M1]
  ▼
 U2 ndarray as image ──► U3 color/channels ──► U4 imread/imshow ──► U5 preprocessing
  │   [M2]                  [M4]                  [M3]                 [Phase 1 · M5,M6]
  │                                                                      │
  │                                                                      ▼
  ├────────────────────────────────────────────────────────────► U6 encode/base64
  │                                                                 [Phase 0/1 · M7]
  │                                                                      │
  │                                                                      ▼
  │                                                              U7 hashing/content-addr ──► (S3 keys,
  │                                                                 [Phase 1 · M8]            DynamoDB PK)
  ▼                                                                      │
 U8 live capture ◄───────────────────────────────────────────────────────┘
  │   [Phase 0/1 · M9,M10]
  ▼
 U9 OCR ────────────────────────────────────────────────────────► (Rekognition DetectText)
  │   [Phase 2]
  ▼
 U10 HTTP/APIs/secrets ──► U11 VLMs & parsing ──► U12 pillar prompting
  │   [Phase 0 · M11]        [Phase 2 · M12]        [Phase 4]
  │                              │                      │
  │                              ▼                      │
  │                        U13 grounding vs scraping    │
  │                            [Phase 3]                │
  ▼                              │                      │
 U14 caching ◄───────────────────┴──────────────────────┘
  │   [Phase 5 · M13] ───────────────────────────────────────────► (ElastiCache)
  ▼
 U15 persistence (SQLite) ───────────────────────────────────────► (DynamoDB)
  │   [Phase 5]
  ▼
 U16 testing & debugging  (crosscutting — practiced in every unit's labs)
  │   [all phases · every M-module's tests & drills]
  ▼
 U17 cloud port: events, Lambda, API GW, Rekognition, DynamoDB, IAM, IaC
      [Phase 6]
```

## Suggested order of attack

Interleave concept → labs → roadmap module → checkpoint. One block per sitting or two:

1. **U1 → labs → M1.** Checkpoint: explain declared-vs-resolved out loud.
2. **U2 → labs → M2.** Checkpoint: strides on paper for a 720p frame.
3. **U3 → labs → M4**, then **U4 → labs → M3.** Checkpoint: spot-a-channel-swap speed run.
4. **U5 → labs → M5, M6.** Checkpoint: state your chosen denoise `h` and defend it.
5. **U6 → labs → M7**, then **U7 → labs → M8.** Checkpoint: recite the cache-key contract.
6. **U8 → labs → M9, M10.** Checkpoint: a crashed run doesn't lock the camera.
7. **U9 → labs.** (No M-module — this is Phase 2 territory.) Checkpoint: your SKU validator's
   test suite is green.
8. **U10 → labs → M11**, then **U11 → labs → M12.** Checkpoint: Phase 0's vertical slice now
   fully assembled from parts you hand-built.
9. **U12 → labs**, **U13 → labs.** Checkpoint: pillar-vs-megaprompt comparison written down.
10. **U14 → labs → M13** (then the Redis swap), **U15 → labs.** Checkpoint: feedback flow touches
    both stores correctly.
11. **U16 → labs** — retrofitting tests across everything above. Checkpoint: mutation hour
    survivors all addressed.
12. **U17 → labs + mini-project** when Phases 1–5 are real. Checkpoint: narrate the Phase 6
    diagram from memory, with why's.

Mini-projects are floaters: grab one whenever a unit's concept feels shaky — they're reps, and
reps are the curriculum.

---

*Companion to `architecture.md` (the design rationale) and `roadmap.md` (the M1–M13 build
ladder). Concepts here, blueprints there, rungs in between — build it twice, understand it once
and for all.*
