# What 0.1.3 could carry

- **Status:** research, 2026-10-30; the owner chose its scope the same day (`decisions.md`, "The scope of 0.1.3: the features beside the process work"; `roadmap.md`, "0.1.3: the process is faster, and the session's state is a snapshot"). Nothing in `src/` and no pin changes with this memo. Written against a checkout twelve commits behind `dev`, so its first draft took 0.1.2 as unreleased; 0.1.2 was tagged and published on 2026-10-29, and the text below was corrected.
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Fable 5.1), with three sub-agents that read the web only: the platform (wasmtime, WASI, CPython, wasi-sdk), the sandbox market (E2B, Modal, Daytona, Cloudflare, Vercel, Anthropic, OpenAI, Gemini, Monty, boomslang, eryx, hyperlight) and the package ecosystem (Pyodide's list, PyO3 on wasip1, the pins' upstreams).
- **Evidence:** the URLs beside each claim; the repository at `dev` `b2bb0e4b` (0.1.2 released 2026-10-29; 159, 155, 160 and 161 drafted for 0.1.3's process work); the owner's notebook app `test_app/` (untracked) read as a worked example of what an embedder has to build by hand today.
- **Stands on:** `roadmap.md` ("0.1.2: the embedder's release", "Out of 0.1.2", "After 0.1.0"); `2026-10-22-how-the-market-describes-sandboxed-python.md` §4; `2026-10-22-what-the-prior-art-does-and-does-not.md` §4; `2026-10-23-a-rust-runner-against-wasmtime-py-on-speed.md`; `../specifications/150-…`, `157-…` (what they left out); `../specifications/046-lxml.md` Decision 12; `docs/reference/limitations.md`; `docs/reference/packages.md`.

Labels: READ means read from a page or file, cited; INFERRED means the researcher's reasoning; EXECUTED means run here (only the two pin checks were).

## The short version

1. **0.1.2 answers the market's two loudest critiques of WASI Python only half-way.** Pydantic's alternatives table and the otari issue both say WASI Python has "no snapshotting" and "no persistent session" (READ: https://pydantic.dev/docs/monty/reference/alternatives/, measured 2026-09; https://github.com/mozilla-ai/otari/issues/1383, 2026-09-18). 0.1.2's starting image (150, 157) is a snapshot *before* a program runs. What every peer that ships snapshots now offers, and what the owner named "a later feature" on 2026-10-27, is a snapshot *of* a live session: checkpoint, restore, fork. That is the natural headline for 0.1.3.
2. **The owner's own notebook app shows the second gap.** `test_app/app/driver.py` hand-rolls a last-expression value, a `display()` with `_repr_html_` and `_repr_svg_`, and a record protocol multiplexed over stdout; `main.py` replays every earlier cell because a fresh instance is cheaper to reason about than a session. Every hosted interpreter returns typed results (E2B `Result` with text/html/png/chart and a DataFrame field; Cloudflare, Daytona, Anthropic, Gemini likewise; READ). The product has no such result shape, and no streaming while the guest runs.
3. **Three packages are ready and one is owed.** python-docx and python-pptx were approved by decision 48 and deferred by spec 046's Decision 12 to a follow-up that was never numbered; the fix (templates read as package resources, as spec 041 did for pandas and networkx) is written down. pdfplumber and plotly are pure Python over what the zip already carries. Both Anthropic's and OpenAI's interpreters ship docx and pptx (READ).
4. **The platform asks for little.** CPython 3.15.2 (2026-10-25) and SQLite 3.54.1 (a 32-bit heap-overflow fix, 2026-10-16) are the pin moves with a reason; wasmtime 51 is due about 2026-11-20 and 50.0.1's advisories touch nothing a preview1 core-module guest uses (READ). Nothing in WASI 0.3, wasip3 or stack switching is usable by 0.1.3; CPython's `main` moved to `wasm32-wasip3` on 2026-10-22, which is a 3.16 question.

## 1. Where the product stands against the market (READ, INFERRED)

The 2026-10-22 memos' "behind" lists still hold, minus what 0.1.2 closes (the pandas import cost, now paid once in an image). What moved since:

- **Snapshots are table stakes.** E2B forks from in-memory state (2026-07-21); Modal has memory snapshots in alpha; Daytona fork and snapshot are stable (2026-07-29); Sprites checkpoints in about 300 ms; Blaxel resumes with process state; Monty serialises a paused interpreter; hyperlight-sandbox 0.8.0 (2026-10-17) has `snapshot()`/`restore()`; eryx 0.12.1 (2026-10-27, Rust, CPython on wasmtime 50) has snapshots, pools and pre-init. READ, the market report's matrix.
- **Stdin landed everywhere this month.** Vercel (2026-10-26), E2B (2026-10-26), Daytona (2026-10-05), boomslang's `set_stdin()`. The recurring bug they answer is an agent harness hanging on `input()`.
- **Rich results and streaming** are universal among the hosted interpreters; smolagents users work around their absence with `plt.savefig` callbacks.
- **MCP.** Pydantic's `mcp-run-python` was retired after CVE-2026-25905; every hosted vendor is an OpenAI Agents SDK sandbox provider. A `pip install` sandbox that is also an MCP server has no in-process peer today.
- **New peers to study, not copy:** eryx (Rust core, the shape question 96 asked about), hyperlight-sandbox, pysandbox-wasi. Each would go under `prior_art/` with its licence recorded, if the owner wants them read.

What the product has that none of them states: the stack compiled in, every package's own suite in the sandbox, a reproducible attested build, fuel. Unchanged since 2026-10-22.

## 2. The proposal, ranked

Each item names its class (runner, build, judge, docs), whether it is reviewed before build under constitution §5.6 or spec 108, and what it stands on. Numbers are the lane's when drafted.

### Tier 1: the headline and the owed package

**A. A session's state is a snapshot: checkpoint, restore, fork.** Runner and reactor, **structural**, reviewed before build. After a turn, `Session.checkpoint()` reads the instance's linear memory into a `Snapshot` through the same path 157's `prepare` leaves it in (clocks and entropy re-pinned on the next start, the preopen table cleared, the program's names kept or dropped as the embedder says); `Session(snapshot=…)` and `run(snapshot=…)` already accept one, so a checkpoint restores and forks with no new argument. What it must settle, each a decision in the specification: the host-side state a live session holds that an image cannot carry (open descriptors, mount staging, a tool call in flight), which the checkpoint either refuses (a turn ended with files open) or closes; that a checkpoint is the guest's state and so carries the trust level of every turn before it (the sessions page's rule, said again on the snapshot page); `fuel_used` and the image's `origin` for a checkpoint; and the copy-on-write restore the spike measured at 0.76 ms against 21 ms (POSIX, behind the platform object), which makes a fork per cell affordable. Value: it is the one critique both public comparisons make; it removes the owner's notebook's replay; it is what an agent harness means by "fork the sandbox and try two things". INFERRED from 150's and 157's decisions and the market report's item 1.

**B. python-docx and python-pptx.** Build, the zip, reviewed before build (a change to what the guest imports). Decision 48 is met only when they land; spec 046 Decision 12 names the patch each needs (default templates and part templates opened by path, five places in docx and three in pptx, read as package resources instead) and their dependencies (lxml, Pillow, xlsxwriter, typing-extensions, all carried). Their own test suites join `tests/upstream/` under spec 063. MIT, already approved. READ.

### Tier 2: the result shape an agent needs

**C. Typed results: a last value and displays.** Runner and the zip, reviewed before build (a new public field). A turn or a run in cell mode ends with `Completed.value` (the last expression's `repr`, and its `_repr_html_`, `_repr_svg_`, `_repr_png_` where the object has one, each bounded by `output_bytes`) and `Completed.displays`, the records a guest-side `display()` emitted, carried over the door rather than multiplexed in stdout so a program's own prints cannot forge one. matplotlib's open figures at the end of a cell are a display each, as Jupyter's inline backend does, when the embedder asks (`figures=True`). The owner's `driver.py` is the worked prototype; the product version lives in the zip and is called by the reactor's `turn`. Value: every hosted interpreter returns this; E2B's `Result` is the shape agents' code already parses. INFERRED.

**D. Output while the guest runs, and stdin for a turn.** Runner, reviewed before build (public API). `run(..., on_output=callback)` and an async iterator on `run_async` that yields chunks as the pipe of 129 delivers them, so a long run's progress reaches the agent before the deadline; `Session.run(code, stdin=…)`, whole bytes as `run` takes today, so a turn's `input()` answers instead of reading an empty stream. Both are bounded by what already exists (`output_bytes`, the pipe). A second, smaller item under the same specification: `output_keep="tail"` so a truncated stream keeps its end, where the traceback is, with the cut marked, since agents read the end of output first (Vercel's and Gumloop's practice, READ). INFERRED.

### Tier 3: packages and pins

**E. Pure-Python additions to the zip.** Build, each a row in `tests/upstream/packages.toml` and a golden job. In value order: pdfplumber with pdfminer.six (PDF text and tables with layout; Anthropic's list; MIT; pdfminer's optional AES needs cryptography, which stays out, documented as pypdf's is); plotly 6 (pure Python over narwhals, already carried; HTML and JSON figures work, static export through kaleido cannot, since it is a browser; MIT; the roadmap's "later, or a profile" stands on size, so the zip's growth is measured first and the owner decides); xarray (Apache-2.0, over numpy and pandas; E2B's and OpenAI's lists). pytz stays out (decision 47). The report's other "gaps", tabulate and xlrd, are already carried.

**F. libzstd into CPython.** Build. CPython 3.14 and later carry `compression.zstd` when libzstd is linked; the limitations page says `_zstd` is absent because libzstd is not built. One pinned input (BSD-3-Clause, the owner approves it) gives `compression.zstd`, `tarfile`'s zstd mode and pandas' `compression="zstd"`. Small, and the codec a later Parquet reader needs. READ (`docs/reference/limitations.md`).

**G. Pillow with JPEG.** Build, a spike first. Pillow 13.0.0 pins libjpeg-turbo 3.2.0; its decoder uses `setjmp`/`longjmp`, which wasi-sdk supports on top of exception handling (`-mllvm -wasm-enable-sjlj -lsetjmp`), and the guest already runs under wasmtime's exception handling. SIMD off. Licences IJG, BSD-3 and zlib, for the owner. Value: `Image.open` of a photo and `savefig("x.jpg")` are the common image case; today only PNG works. READ (the package report); the sjlj route is untested here.

**H. The pins with a reason.** Build. CPython 3.15.0 to 3.15.2 (EXECUTED: python.org lists 3.15.2 on 2026-10-25); SQLite 3.54.1 (a 32-bit heap overflow fixed, 2026-10-16: the guest is 32-bit); the build's wasmtime command line from 49.0.3 to 50.0.1 so `wasmtime wizer` and the runner's engine are one version (the runner is on 50 since 127; `scripts/steps/80_snapshot.sh`); numpy 2.5.4 (two bug-fix steps). pandas 3.1.0 (2026-10-22) needs C++20 and is eight days old: the owner's call whether 0.1.3 takes a minor release that young. wasmtime-py stays 50.0.1 (EXECUTED: PyPI's latest; no 3.15 classifier yet, but its wheels are interpreter-independent). Wasmtime 51 is due about 2026-11-20; if 0.1.3 is after that, the move is 127's shape again, with fuel re-baselined since 50 changed how fuel is charged around caught exceptions.

### Tier 4: the front door and the record

**I. An MCP server command.** Runner, an optional extra. `wasi-python mcp` serves one tool, `run_python`, over stdio, with the command's limits as its arguments and a session per client, so Claude Code, Cursor or any MCP client gets the sandbox in one line of configuration. The `mcp` package is a new dependency, so it is an extra (`wasi-python[mcp]`) with constitution §4.13's reason written. The retired `mcp-run-python` left the slot empty (READ). INFERRED.

**J. The run's record.** Runner, small. `Completed` gains `seconds` (wall time, a fact of this machine, never a check), `memory_bytes_peak` (the instance's memory size at the end, which wasmtime reports) and `tool_calls` (count and time). Agent harnesses budget on these; Daytona, E2B and Modal expose them (READ). Tests keep counting operations.

**K. Set the record straight.** Docs and outreach, the owner's. With 0.1.2 released, Pydantic's table row and the otari issue are both answerable with measured numbers: a pandas call from a package image, a session of ten turns. Constitution §4.10 and the 2026-10-22 memo's question 5 already ask it.

### Carried over from 0.1.2

153 (Windows output from a pipe) and 156 (the listing-order check), both deferred on 2026-10-28; 155 (the tag's run publishes what the release pull request judged) is already in 0.1.3's process work, and 154 landed in 0.1.2. The lines the roadmap reserves after 0.1.2 (a snapshot file's access lists; the platform module's next split before the next release, the 0.1.2 structural review's M1; 115), and the "Out of 0.1.2" list: the `_instance`/`_open_session` duplication (structural, after 142), the many-sessions benchmark memo, the abandoned tool thread's cancellation. The reserved cache items (a path judged one component at a time; the artifact set judged by its path; the Windows access list) stay where the roadmap put them.

## 3. Not for 0.1.3, with the reason

- **A Rust or JavaScript core.** The 2026-10-23 memo's "adopt in part" stands and the owner found nothing urgent; eryx shows the shape works and is prior art to read, not a reason to move now. INFERRED.
- **pyarrow, polars, duckdb, pydantic, orjson, cryptography.** Nothing has a WASI build to study: Pyodide's are Emscripten; polars is frozen at 1.33.1 even there; pydantic-core and orjson need PyO3 as a static builtin on wasip1, which PyO3's own CI has built against 3.15 since 2026-08-23 (READ: https://github.com/PyO3/pyo3/pull/6340) but no extension has shipped. A **spike** on orjson as the PyO3 pathfinder (a pinned Rust toolchain as a build input, `append_to_inittab`, panic=abort) would be the first step toward pydantic, which agents' generated code reaches for constantly (PyPI rank 18), and toward fastparquet's cramjam. Research in 0.1.3 if the owner wants it; a package in 0.1.4 at the earliest.
- **Threads, WASI 0.3, wasip3.** wasi-sdk 34's experimental cooperative-threads sysroot and PEP 816's "WASI 0.3.1 … some form of threading" are the first real route to `threading`; CPython's `main` is on `wasm32-wasip3` since 2026-10-22. A 3.16 spike, after 3.16's first beta. READ.
- **An in-browser build, network, pip in the guest.** By the constitution.
- **Build-time profiles.** Still waiting on a reason.

## 4. Questions for the owner

1. Is **A** (checkpoint, restore, fork of a session) the headline of 0.1.3, as the starting image was 0.1.2's? It is structural and the largest item; everything else here fits beside it.
2. **C** and **D** change the public API's result shape. One release or two? Both are what the notebook app had to build; together they are "the result an agent reads".
3. Packages: **B** is owed; **E** and **F** are cheap; **G** needs a spike. Which of E's three, and does plotly's size decide it?
4. Does 0.1.3 take **pandas 3.1.0** or stay on 3.0.x?
5. **I**, the MCP command: wanted, and as an extra?
6. The **orjson/PyO3 spike**: research in 0.1.3 or not yet?

## One line

0.1.3 should make a live session's state a snapshot (checkpoint, restore, fork), give a run the typed result and the streaming an agent reads, land the owed python-docx and python-pptx with pdfplumber, zstd and the JPEG spike beside them, and move the pins that have a reason (CPython 3.15.2, SQLite 3.54.1, one wasmtime for build and runner).
