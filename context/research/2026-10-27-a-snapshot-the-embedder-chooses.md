# A snapshot the embedder chooses: pre-imported packages as every run's starting point

- **Status:** research, 2026-10-27. An embedder's need, measured from outside this repository. It changes nothing here: no code, no pin, no specification. Whether to build it, and how, is the owner's to decide here.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), in a session of the `wasi-python-dev` repository (the wasipython.dev site).
- **Evidence** (in `wasi-python-dev`):
  - `context/research/2026-10-27-warm-sessions-and-short-examples.md` and its folder: `harness/measure.py`, `harness/held_memory.py`, `harness/everything.py`, and `results/`.
  - `context/research/2026-10-27-the-runner-on-cloudflare-measured.md` (commit `f092cdd`): the guest's rate on Cloudflare `standard-1`.
- **Stands on:**
  - `recipes/reactor_main.c` (`PREIMPORT`, a compile-time string);
  - `scripts/steps/80_snapshot.sh` (the snapshot made by `wasmtime wizer` at build time);
  - `docs/explanation/how-it-works.md`, "The snapshot";
  - `context/roadmap.md`: "a `full` profile, its own artifact set with the stack pre-imported, is built only if an embedder asks" (decision 34);
  - `src/wasi_python/runner.py`, `class Session`.

  All read at `898bc091`, which is 0.1.1 as published.

Labels: EXECUTED means run and seen; READ means read from a file, cited; INFERRED means the researcher's reasoning. Fuel is a count, the same on any machine. Seconds on Cloudflare are fuel ÷ 1.2 billion, the rate measured there (INFERRED estimates).

## The need, in the owner's words

> "there needs to be a snapshot capability in wasi-python where a dev can pre-import packages and re-use that snapshot as a starting point for new run calls or sessions"

The owner, 2026-10-27, deciding wasipython.dev's runner. The site's editor runs a visitor's short program in a fresh sandbox per run (that repository's constitution §4.6). Its examples spend almost all their instructions importing packages, and almost none on the visitor's own lines.

## 1. What the imports cost (EXECUTED)

From the warm-session memo:
- **Prelude:** the example's own `import` lines, run as a session's first turn.
- **Turn:** the example itself, run as the second.
- **Fresh:** one `run()` of the whole program.

| program | fresh, billions | prelude | the program's own turn | Cloudflare s, fresh | Cloudflare s, turn |
|---|---|---|---|---|---|
| a scikit-learn decision tree on iris (14 lines) | 15.29 | 14.22 | 0.388 | 12.7 | 0.32 |
| k-means on 90 points (12 lines) | 15.06 | 14.00 | 0.380 | 12.5 | 0.32 |
| a statsmodels OLS fit (13 lines) | 14.23 | 13.50 | 0.076 | 11.9 | 0.06 |
| a matplotlib chart as SVG (15 lines) | 8.35 | 7.61 | 0.375 | 7.0 | 0.31 |
| a pandas pivot (14 lines) | 4.79 | 4.38 | 0.092 | 4.0 | 0.08 |
| a SciPy curve fit (14 lines) | 4.60 | 4.30 | 0.030 | 3.8 | 0.03 |
| a NumPy Mandelbrot grid (13 lines) | 0.84 | 0.73 | 0.022 | 0.7 | 0.02 |

- **One prelude that imports what all 29 of the site's examples import** is 28,655,325,354 instructions: 5.29 s on an M1 Pro, about 24 s on Cloudflare `standard-1` (`results/2026-10-27-everything-prelude.txt`). All 29 examples then ran correctly as a second turn.
- **Held memory** (`results/2026-10-27-held-memory.txt`): one process with the module loaded was at 282 MiB of RSS. Five sessions held after their preludes (numpy, pandas, SciPy, scikit-learn, none) brought it to 460 MiB. The everything-prelude session alone added 153 MiB.

## 2. What the embedder can do today, and why it falls short (EXECUTED and INFERRED)

1. **A fresh `run()` per program.** Correct and simple, but every run pays its imports: about 12 s on Cloudflare for the heaviest examples. This is what the site does now (its decisions, 2026-10-27).
2. **A pool of sessions, each warmed with a prelude and used for one program, then closed.** The program's turn is 10 to 400 times cheaper. But each use needs a refill, which runs the prelude again: up to 14 to 29 billion instructions, 12 to 24 s of CPU on a half vCPU. Sustained throughput is bounded by refills, so several visitors at once need both a deep pool and several vCPUs. The owner judged that not a good option.
3. **A `full` artifact set** (roadmap, decision 34). It fits the need if its list is the embedder's list. But a fixed list is someone else's choice, and the need is for the embedder to choose.
4. **What an embedder cannot do.**
   - It cannot make its own snapshot from the wheel: `PREIMPORT` is compiled into `reactor_main.c`, and `wizer.initialize` runs only it (READ).
   - It cannot fork a warm process: `Session.run` raises `RuntimeError` in "a process forked after it ran a guest" (READ).
   - The site's own rule forbids running a wasi-python built anywhere but PyPI.

## 3. What a snapshot capability could look like (INFERRED; none decided)

**The shape the owner describes:**
- An embedder names packages, or a prelude of code.
- wasi-python makes a starting image from it.
- `run(..., snapshot=image)` or `Session(snapshot=image)` starts each call as a **new instance** from that image.

Every call stays a fresh instance; nothing a call does reaches the image or the next call. It is today's `python-snapshot.wasm` with the embedder's imports added.

**Two ways it could be made.**

- **(a) At build time, as an artifact set.**
  - The embedder runs a `wasi-python snapshot --preimport numpy,pandas,…` that drives the pinned `wasmtime wizer` the build already uses, and gets a new `python-snapshot.wasm`. `run(artifacts=…)` uses it.
  - *Cost:* the new binary is a new module, so it must be compiled per host, about 12 s on an M1 Pro and minutes on a half vCPU. It also needs its own MANIFEST and checksum, and the CLI would need a wizer binary, which the wheel does not carry.
- **(b) At run time, as a memory image.**
  - wasi-python runs the prelude once in an instance of the module it already has compiled. It saves the instance's state — linear memory, globals, and the runner's own host-side state — and starts each new instance by restoring that state before the call's code runs.
  - *For:* no new module, so no recompile.
  - *Cost per call:* a copy or a copy-on-write mapping of the image, perhaps 150 to 300 MiB. That is far below the seconds of import it replaces, but unmeasured.
  - *Against:* it is the harder design. It needs every piece of host-side state a snapshot freezes to be reproducible: the descriptor table, zipimport's offsets, the home folder, the environment restored per call, the fixed hash key.

**Questions either way would have to answer:**

- **Randomness.** The 0.1.1 snapshot answers constants for clocks and entropy while it is made, and restores the real ones per call (READ, `how-it-works.md`). A prelude that seeds a generator at import time, such as `random`'s module state or numpy's legacy global state, would give every call the same seed unless the image is made under constants and reseeded per call. This needs a check per package.
- **Trust.** The image holds whatever the prelude did. It is as trustworthy as the prelude: the embedder's code, never a visitor's.
- **Packages that do work at import.** Font caches (matplotlib writes `fontlist-*.json`), temporary files and environment reads would be frozen into the image or fail at snapshot time.
- **Interaction with fuel.** The prelude's instructions are spent once, so a call's `fuel_used` would be its own work only. That is what an embedder wants to show, and it should be said in the docs.

## 4. What it would give the site (INFERRED from §1)

- **The heaviest tab's call** would fall from about 12.7 s to about 0.3 s on Cloudflare `standard-1`, with no refill and no pool.
- **Throughput** would be bounded by the programs' own work, not their imports: tens of the site's examples per minute on a half vCPU, rather than about five.
- **The site would stop needing a larger instance** to serve several visitors at once.

## Still unknown

- The per-call cost of starting from a 150 to 300 MiB image, by copy or copy-on-write, through wasmtime-py. Not measured.
- Whether wasmtime-py exposes what design (b) needs without private API, which `_wasmtime_ffi.py` would otherwise have to hold.
- Which of the stack's packages seed randomness, or do host work, at import.

In one line: the site's programs spend 90 to 99% of their instructions importing packages; a starting image the embedder chooses, from which every call is still a fresh instance, would remove that cost without a pool, and only wasi-python can provide it.
