# `experiments/` — the learning sandbox

Hand-build the pieces of Phase 0, one rung at a time. This folder is the practical companion to
`../src/notes/roadmap.md` — read a module's entry there for the full *why*, then implement it here.

## Setup (once)

```powershell
# from the repo root, with the venv active
.\.venv\Scripts\Activate.ps1

# generate the sample image the still-image modules load
python experiments\assets\make_sample.py
```

## How to work a module

1. Open `mNN_*.py`. The docstring states the goal; functions are stubbed with `NotImplementedError` and a
   `TODO`.
2. Implement the function bodies.
3. Run the module to see it work: `python experiments\m05_preprocess.py`
4. Run its tests (if it has any) and make them go green: `python -m pytest experiments\tests\test_m05_preprocess.py -v`

The stubs raise `NotImplementedError` on purpose, so the tests start **red**. That's the point — a test you
can't see fail isn't proving anything. Make it pass by implementing the code, not by weakening the test.

## Run everything

```powershell
python -m pytest experiments\tests -v          # the whole suite
python experiments\m01_hello_venv.py           # M1 is fully implemented — use it as a template
```

## Layout

```
experiments/
├── assets/make_sample.py   # generates assets/sample.jpg (git-ignored output)
├── conftest.py             # shared pytest fixtures (synthetic frame, fake clock)
├── m01_hello_venv.py       # ✅ fully implemented reference
├── m02 … m13               # stubs you fill in
└── tests/                  # test scaffolds for M2, M5, M8, M13
```

Module `.py` files are tracked in git (commit your solutions as you go). Image outputs (`*.jpg`, `*.png`)
are git-ignored.
