# A Rust core with JavaScript and Python wrappers: an assessment

- **Status:** research, 2026-10-18. An assessment of a design proposal, at the owner's request.
  It changes nothing: no code, no specification, no pin. Written in a scratchpad and filed here
  by the lane.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Fable 5.1). Box: one session.
- **The proposal** (the owner's words, 2026-10-18, in short): a Rust core runner on the
  `wasmtime` crate; napi-rs bindings for Node, Bun and Deno; PyO3 for Python, replacing
  wasmtime-py; the artifacts downloaded on first use and verified against `SHA256SUMS`; port
  `run()` with grants and limits first and check it against the judge.
- **Stands on:** `context/constitution.md`; `AGENTS.md`; `context/roadmap.md`;
  `context/decisions.md`; `context/questions-for-the-owner.md` (question 64);
  `src/wasi_python/{runner,mounts,tools}.py`; specs 001, 006, 010, 011, 013, 014, 015, 028,
  031, 032, 034, 036, 048, 049, 053, 055; `context/research/2026-10-18-wasmtime-49-advisories.md`,
  `2026-10-17-fuel-depends-on-how-the-module-was-made.md`,
  `2026-10-17-the-runtime-for-agent-code.md`, `2026-10-17-market-research-use-cases.md`;
  `context/upstream/12-wasmtime-py-on-wasmtime-49-0-3/`; `tests/harness/guest.py`,
  `tests/harness/scoreboard.py`; `.github/workflows/release.yml`; `scripts/00_download.sh`;
  the prior-art clones `wasmtime-v49` (tag v49.0.3) and `wasmtime-py` (280ce73), read only.
- **Evidence:** the folder of the same name beside this memo: PyPI's `wasmtime` release list, wasmtime's and
  wasmtime-py's release dates, and `notes.md` with the sentences read on the web.

Labels: EXECUTED means run here; READ means read from a file or page, cited; INFERRED means the
researcher's reasoning.

## The short version

The proposal is three proposals. They deserve three different answers.

1. **A JavaScript embedder path.** Real need, allowed by the constitution, and the right shape
   is a napi-rs binding on the `wasmtime` crate. But it is a second product, not a change to
   this one, and it belongs after 0.1.0.
2. **Replacing wasmtime-py with a PyO3 core.** The stated benefit is smaller than it looks and
   is about to expire on its own: wasmtime-py ships each major the same day wasmtime does, and
   wasmtime 50 is due within days. The cost is the whole runner (about 7,900 lines of Python
   under 944 tests, 25 specifications) plus a native build and release matrix the project does
   not have today. Do not do this before 0.1.0, and do not do it after unless wasmtime-py
   breaks its pattern.
3. **Download-on-first-use artifact delivery.** It solves question 64 but contradicts the
   mission's own words ("without … a package install step"), opens a network channel in the
   embedder's process, and weakens offline use. Keep bundling for the wheel; ask PyPI for the
   raise, as question 64 already recommends; let the JavaScript package decide its own delivery.

**Verdict: adopt in part, after 0.1.0.** Spike the Rust core now only as a research memo with a
time box, to put the fuel-equality fact on the record; build a separate `@wasi-python`-style
Node package on that core after 0.1.0; keep the Python wheel on wasmtime-py.

## 1. The facts, checked one by one

### 1.1 What "no JavaScript" says

- Constitution §1 (READ): the mission is to run Python "inside a sandbox it fully controls,
  without a browser, a JavaScript engine, a kernel feature or a package install step." That
  describes what the *host* must not need. It does not forbid a JavaScript host.
- §4.3 (READ): "One target: `wasm32-wasip1`. No Emscripten, no JavaScript, no native code
  path, no host-specific branch." This is a rule about the guest build: one target, one
  artifact. A binding that *calls* wasmtime is not a native code path in the guest.
- §2.4 (READ): "An embedder in any language with a wasmtime binding can run it by preopening
  the folders it grants … binding one host function and calling one export." A JavaScript
  embedder is therefore contemplated, not excluded.
- The README already shows a TypeScript caller (READ, `README.md` "From any language", lines
  920 to 1072): it spawns `wasi-python run` and parses one JSON line. The market memo (READ,
  `2026-10-17-market-research-use-cases.md`, rows 1 and 4) names "a TypeScript path" as a gap
  and notes "Node hosts have no safe WASI" (Node's own `node:wasi` docs say it must not run
  untrusted code).

So the owner's reading is right: the rule is about the guest, not about who calls it.
Offering a JavaScript binding fits §2.4 and the market memo.

### 1.2 Embedder neutrality (§4.5)

A napi-rs package and a PyO3 package are bindings for a language, not for a particular
embedder. Neither names vfs or any consumer. §4.5 is not touched (INFERRED from the text).

### 1.3 What the constitution does not cover

- §4.6 (READ): "The artifact set is the product … Nothing compiled per host (`.cwasm`) is ever
  published." A Rust core is not a `.cwasm`, but it is a native binary per host, published.
  Today the project publishes no native binary of its own: wasmtime-py's are wasmtime-py's.
  Owning native binaries is a new kind of artifact the constitution has not decided on.
- §4.2 (READ): every input pinned by URL and SHA-256. A Rust toolchain per build host, and
  wasmtime's crate tree, would all become pins. `Cargo.lock` records checksums, so the shape
  fits; the count does not: wasmtime v49.0.3's `Cargo.lock` names **581 packages** (EXECUTED,
  `grep -c '^name = ' Cargo.lock` in the clone). Not all reach a release binary, but each that
  does ships its licence (§4.12). Decision 2 (READ, `decisions.md`) rejected wasi-vfs partly
  because "it brings Rust runtime code whose licences would ship". Today that burden is
  wasmtime-py's, not ours.
- §4.13 (READ): "`uv` only." AGENTS.md repeats it. A Rust core adds cargo; a napi-rs package
  adds Node and npm to the release path. The build today has **no Rust step** (EXECUTED:
  `downloads/SHA256SUMS` names no Rust toolchain; the snapshot is made by the pinned wasmtime
  CLI's own `wasmtime wizer`, READ `scripts/steps/80_snapshot.sh`).
- §3 (READ): "Not a general wasm toolchain. It builds one artifact well." A runner in Rust with
  two bindings is a second artifact family.
- §6.4 and §6.5 (READ): prefer "fewer files, fewer dependencies, fewer artifacts", and ask
  "would the owner recognise it as this project?"

### 1.4 What the owner has already decided that this touches

- **Spec 028 (decision of 2026-10-17, READ):** `pip install wasi-python` must run programs;
  wasmtime-py is a required dependency, chosen because it has "a wheel for every major
  platform". A PyO3 core keeps that property only if the project ships as many wheels itself.
- **Spec 049 (landed, READ):** the public API is frozen: `tests/public_api.txt`, 243 lines of
  signatures, dataclass fields, exceptions and `stats()` keys; a deprecated thing survives at
  least two final minor releases (question 88). A Rust core behind PyO3 must reproduce this
  surface exactly, including frozen dataclasses, `Errno` as an `IntEnum`, the `FileProvider`
  protocol and the `tool()` decorator. PyO3 does not make Python dataclasses; the Python layer
  that does would stay. "Three thin wrappers" is not what the Python wrapper would be.
- **Question 49 (READ):** "cancel nothing for 0.1.0". The build-class queue before 0.1.0 holds
  about ten specifications, one slot at a time (§5.7; question 91).
- **Decision 86 (READ):** "the shadow is removed with the pin that moves past wasmtime 49.0.3."
  The project already plans to drop spec 048's shadows by moving the pin.

### 1.5 The wasmtime-py burden today, measured

What the proposal calls "the lagging binding you're backporting security fixes into":

- **Nothing is backported into wasmtime-py.** Spec 011 Decision 5 and spec 048 (READ): no
  wasmtime-py code is replaced or patched. Spec 048 shadows two preview1 calls in Python
  (`fd_readdir`, `path_rename`) on every call through a guard linker, applying wasmtime
  49.0.3's own rule. The fix sits in `mounts.py`, about 2,054 lines in all with the mount
  machinery it reuses (EXECUTED, `wc -l`).
- **The runner reaches into wasmtime-py's private binding.** `_ffi` is used 6 times in
  `runner.py` and 7 in `mounts.py`; `_bindings` twice; `ctypes` 32 and 4 times (EXECUTED,
  `grep -c`). The names: `wasmtime_func_call`, `wasmtime_context_{get,set}_fuel`,
  `wasmtime_context_set_epoch_deadline`, `wasmtime_store_epoch_deadline_callback`,
  `wasi_config_set_{stdout,stderr}_custom`, `wasmtime_error_new`.
- **Specifications that exist to work around wasmtime-py** (READ, each): 010 (a shadow cannot
  call the WASI function it replaces, hence the trampoline), 011 (process-wide callback tables
  and `LAST_EXCEPTION`), 013 (ctypes `ArgumentError` for `fuel=1.5`), 014 (`UnicodeEncodeError`
  inside wasmtime-py for a lone surrogate), 048 (the 49.0.x shadows), 006 ("wasmtime-py cannot
  lower wasmtime's table limit"), the fuel memo (`Config.operator_cost` not exposed). Three
  upstream facts sheets are wasmtime-py's (1, 2, 12). 25 specification files mention
  wasmtime-py (EXECUTED, `grep -c`).

So the burden is real, and it is of two kinds: design workarounds (010, 011, the `_ffi`
reach-ins), and the security lag (048). A Rust core removes both kinds. The next section asks
whether the second kind is about to vanish anyway.

### 1.6 wasmtime-py's cadence against wasmtime's (EXECUTED)

| wasmtime release | date | wasmtime-py release | date |
|---|---|---|---|
| v47.0.1 | 2026-07-20 | 47.0.1 | 2026-07-20 |
| v48.0.0 | 2026-08-20 | 48.0.0 | 2026-08-20 |
| v48.0.1 … v48.0.6 | 08-24 to 10-14 | none | |
| v49.0.0 | 2026-09-21 | 49.0.0 | 2026-09-21 |
| v49.0.1, 49.0.2, 49.0.3 | 09-24, 10-02, 10-14 | none | |
| v50.0.0-rc.1 | 2026-10-05 | | |

Sources: `2026-10-18-a-rust-core-with-js-and-python-wrappers/wasmtime-releases.txt`, `2026-10-18-a-rust-core-with-js-and-python-wrappers/wasmtime-py-tag-dates.txt`,
`2026-10-18-a-rust-core-with-js-and-python-wrappers/pypi-wasmtime.txt`.

- wasmtime-py ships every **major** the same day as wasmtime, twelve months running (39.0.0
  through 49.0.0, each within a day of wasmtime's tag; READ the two lists).
- wasmtime-py ships **no patch release** for wasmtime's security patches (none for 48.0.1 to
  48.0.6, none for 49.0.1 to 49.0.3).
- wasmtime's majors come about every four to five weeks (48: 08-20; 49: 09-21; 50's rc.1:
  10-05). **wasmtime 50.0.0 is due within days**, and on the pattern wasmtime-py 50.0.0 arrives
  the same day (INFERRED from twelve data points). 50.0.0 carries every 49.0.x fix (READ:
  wasmtime's release branches merge fixes forward; the advisories memo lists them as fixed in
  49.0.x, which 50 includes).
- The project's response is already decided: move the pin to `>=50,<51`, remove the shadows
  (decision 86), re-run the judge on 50 (spec 004 tests one major).

So the lag that spec 048 answered is **structural but short**: the window between a wasmtime
patch release and the next major is at most about five weeks. The project's exposure is
"wasmtime's security patches reach PyPI users at the next major", and wasmtime-py's pattern
makes that reliable. A Rust core would get the patch on crates.io the same day, but it would
still need **our own** release on every patch (rebuild the native binaries for every platform,
publish to npm and PyPI). §5.5 makes a security fix a reason to release anyway, so this is a
shift of who does the work, not a removal of it.

### 1.7 What the proposal gets right about the Rust side (READ, `wasmtime-v49` clone and docs.rs)

- `Store::set_fuel`, `get_fuel`, `set_epoch_deadline`, `epoch_deadline_callback` and
  `limiter(ResourceLimiter)` exist in the Rust API (`crates/wasmtime/src/runtime/store.rs`
  lines 930, 1016, 1084, 1147; `limits.rs:32`). Fuel, the memory cap and deadlines carry over.
  `Config::operator_cost`, which wasmtime-py does not expose, is reachable.
- `wasmtime_wasi::p1` provides `WasiP1Ctx` and `add_to_linker_sync` (`crates/wasi/src/p1.rs`
  lines 141 and 846); `WasiCtxBuilder::preopened_dir(host, guest, FsPerms::{ReadOnly,
  ReadWrite})` (`ctx.rs:296`) is the same read-only/writable bit the runner uses today.
- `Linker::allow_shadowing` exists in Rust too (`linker.rs:208`).
- The door is a plain `func_wrap`; a host function can call back into Python (PyO3, taking the
  GIL on the worker thread) or JavaScript (napi-rs `ThreadsafeFunction`).

### 1.8 What the proposal understates about the Rust side

- **The p1 functions are not meant to be called one by one.** `p1.rs` (READ, lines 846 to
  870): "None of the generated modules, traits, or types should be used externally to this
  module." The docs (READ) say "WASIp1 is not as extensible or configurable as WASIp2" and that
  the p2 layer beneath is "just an internal implementation detail". So a Rust shadow that must
  *forward* to wasmtime's own `path_open` has the same problem spec 010 met in Python: it either
  builds the same trampoline on a second linker, or it reimplements the call over `cap-std`.
  mounts.py forwards 29 calls fuel-neutrally through a trampoline (READ, the module docstring,
  `FUEL_ALLOWANCE`). The port of mounts is not "redo the provider calls"; it is redo the
  descriptor table, the staging, the write-back at every ending (spec 034, question 71), the
  spec 048 guard and the parity table (`test_raw_calls_answer_as_a_grant_does`).
- **The tool protocol's host half is Python by nature.** `tools.py` (2,353 lines, EXECUTED) is
  mostly schema from type hints, validation, the gate, the bounded thread pool and spec 053's
  async tools awaited "on your loop, bounded by the call's deadline and cancel" (READ, README
  "From async code"). The wire is JSON frames (READ, `recipes/guest/host/tools.py:127`,
  `tools.py:1411`) and is language-neutral; the Python side of it is not thin and would stay.
  A JavaScript side would be written afresh: `tool()` from TypeScript types or zod, a gate,
  promises awaited under the deadline. That is proper work, not a wrapper.
- **Ctrl-C is host-language work.** `runner.py` installs a `SIGINT` handler on the main thread
  and raises `KeyboardInterrupt` through the shared host function (READ, lines 2635 to 2700,
  2921 to 2958; spec 015's order). Node has its own `SIGINT` semantics. Each wrapper owns this.
- **Cancel and the epoch ticker.** A thread-local call stack, a 50 ms epoch ticker, an epoch
  callback that names "cancelled" or "deadline" (READ, `_shared`, `_epoch_answer`). In Rust
  this is cleaner (`epoch_deadline_callback` with store data), but spec 015's measured promises
  (stop within 200 ms with a spinning thread) and spec 030's "a cancel in the door is named"
  are behaviours with checks; each is re-proven.
- **Sessions (spec 055, confirmed for build, build-class).** A store kept alive across turns,
  called from several threads, a reaper, `Session` and `SessionEnded` in the frozen API
  (READ, 055's head). It is specified on the Python runner and queued last before 0.1.0. A
  Rust core either waits for it or re-specifies it.
- **The judge does not drive the runner.** `tests/harness/guest.py` (READ, its docstring)
  "is kept apart from `wasi_python.run`, the runner it judges" and imports `wasmtime` directly;
  it answers `random_get` and `clock_time_get` itself so fuel repeats. The ratchet's fuel
  tolerance is `1e-4` (READ, `scoreboard.py:31`). So "one set of sandbox tests" and "check it
  against your existing judge" need new checks: the goal checks judge the artifacts through a
  wasmtime-py driver, and removing wasmtime-py from the product does not remove it from the
  judge. 16 unit-test files reach `runner._*` internals (`_walk`, `_epoch_ticker`, `_stack`,
  `_ctrl_c`, `_judge`, …; EXECUTED, `grep`), and 944 tests exist in all (EXECUTED).

### 1.9 Would fuel match exactly across runners?

- `fuel_used` is wasmtime's count of guest instructions, metered from after instantiation
  (READ, spec 008 and the fuel memo: `UNMETERED` then `set_fuel`). The count comes from
  Cranelift's instrumentation of the same `python.wasm`, so with the **same wasmtime version
  and the same `Config`** (`consume_fuel`, `epoch_interruption`, default operator costs), two
  runners should report the same `fuel_used` for the same program and the same host answers
  (INFERRED; the fuel memo's experiments show the guest's own count "never differed" across
  how the module was loaded, which is the analogous case).
- Two things can break equality: a different wasmtime (49.0.0 under wasmtime-py against
  49.0.3 or 50 in the crate; 49.0.1 changed fuel accounting for `call_ref` and exception
  `catch`, GHSA-m63x, which our C-built module does not use, INFERRED by the advisories memo),
  and host-call fuel: mounts' forwards are made fuel-neutral by hand in Python; a Rust port must
  do the same or its mount runs differ by the trampoline's instructions.
- Note `WasiP1Ctx` has a `hostcall_fuel` field (READ, `p1.rs:145`); it bounds array copies
  per host call and is not store fuel. It does not change `fuel_used`.

So: fuel equality is likely but unproven. It is exactly what a spike should measure, and it
is cheap to measure.

### 1.10 Sizing the port

| piece | lines today (EXECUTED, `wc -l`) | commits (EXECUTED, `git log`) | what a Rust core must redo |
|---|---|---|---|
| `runner.py` | 3,536 | 39 | grants and their walk (017, 024), limits and input checks (013, 014), the door, cancel and Ctrl-C (015, 030), the epoch ticker (010), the shared-nothing discipline (011), the `.cwasm` cache, stats, `run_async`'s pool, sessions (055) |
| `mounts.py` | 2,054 | 13 | 29 shadows, staging and write-back (032, 034), the 048 guard, the parity with grants |
| `tools.py` | 2,353 | 13 | the host half of the protocol (031, 036, 053, 056, 060): stays Python; a JS twin is new |
| `tests/` | 944 tests, 82 files | | the unit tests that reach internals are rewritten; the goal checks stay on their own driver |

The whole repository is 471 commits over three days (EXECUTED), 25 of its specifications
mention wasmtime-py, and the public API is frozen. The proposal's "start by porting `run()`
with grants and limits only" is the right first step for a spike. It is also the easy fifth of
the work: grants, limits, fuel and deadlines are the parts wasmtime gives any binding for free.
The hard four fifths are mounts, the door's threading, cancel, sessions and the tests.

### 1.11 napi-rs, Node, Bun, Deno (READ, `2026-10-18-a-rust-core-with-js-and-python-wrappers/notes.md`)

- napi-rs publishes a root package with per-platform packages as `optionalDependencies`, each
  constrained by npm `os`, `cpu` and `libc`; "No compiler or install-time download script is
  required on the consumer's machine." The proposal's description of the distribution model is
  accurate.
- Runtimes: napi-rs's CI "exercises Node.js 22, 24, and 26"; Bun is best effort and "Bun
  failures do not block napi-rs releases"; Deno: "Do not infer Deno support from Node-API
  compatibility alone." So "it works in Node, Bun and Deno" is **Node: yes; Bun: usually;
  Deno: not promised.** The browser exclusion is right.
- Template-backed targets: macOS x64 and arm64; Windows x64, x86, arm64; Linux glibc x64,
  arm64, armv7; Linux musl x64 and arm64; Android; FreeBSD. A sensible first set for us is
  eight (macOS 2, Windows 2, Linux glibc 2, musl 2), matching wasmtime-py's own wheel set
  minus Android.

### 1.12 crates.io, PyPI, and the sizes

- crates.io: "currently has a 10MB size limit on the `.crate` file" (READ, cargo docs). The
  proposal's number is right. It only matters if a Rust *crate* is a product; a Rust core that
  exists to be linked into two bindings need not be published to crates.io at all, and a Rust
  embedder uses the `wasmtime` crate directly (§2.4).
- The artifact set unpacked, the main tree's built set (EXECUTED, `ls -l build/artifacts`):
  `python.wasm` 36.9 MB, the snapshot 70.9 MB, the stdlib zip 21.9 MB; about 130 MB in all,
  and the wheel carries all three (READ, spec 049's `Artifacts`: snapshot, plain, zip,
  manifest). Deflated in the wheel: 8.8, 21.4 and 21.6 MB (READ, question 64). So "60 to
  90 MB unpacked" undercounts today's set by about a third; it grows further with scipy and
  tier B.
- PyPI: 100 MiB per file unless raised (READ, question 64). The wheel: 38.9 MB at 0.1.0a5,
  52.1 MB with matplotlib M1, "95 to 110 MB" estimated at 0.1.0 (READ, question 64).
- npm's package size limit was not checked here; do not rely on bundling 90 MB in an npm
  package without checking it.

### 1.13 The existing cache-and-verify pattern (READ)

- **Build time:** `scripts/00_download.sh` fetches each pin by a literal URL into
  `downloads/`, prints `present` or `fetched`, verifies every file with `shasum -c` against
  `downloads/SHA256SUMS`, and "never writes it; a mismatch fails the build". Downloads are
  untrusted and never leave `downloads/` and `build/` (§4.8).
- **Run time:** the runner has a compiled-module cache (`cache_dir`, `WASI_PYTHON_CACHE`,
  `.cwasm` files keyed by digest; READ `runner.py` lines 3273 to 3290, 3393 to 3446) and an
  artifact locator (`WASI_PYTHON_ARTIFACTS`, `artifacts()`, `ArtifactsMissing`; spec 001,
  049). There is **no run-time download anywhere**, and the release's own integrity story is
  `SHA256SUMS` plus `gh attestation verify` (README "Verifying a download").

So the pattern the proposal would reuse exists at build time and would be new at run time.
Moving it into the embedder's process changes two rules: §4.8's "unpack under `downloads/` and
`build/`, never into the system", and the mission's "without … a package install step".

## 2. The questions, answered

### 2.1 Does it fit the constitution and the decisions?

- A JavaScript binding: **fits** §1, §2.4 and §4.5; the "no JavaScript" rule is about the
  guest (§1.1 above).
- A Rust core published as native binaries: **not covered**; needs the owner's decision on a
  new artifact kind (§4.6), new pins and licences (§4.2, §4.12), and a toolchain beyond uv
  (§4.13). It strains §3 and §6.4, §6.5.
- Replacing wasmtime-py: **conflicts** with the spirit of spec 028's decision (the plain
  `pip install` on wasmtime-py's platform wheels) unless the project ships its own wheel per
  platform, and with spec 049's freeze (every public name re-implemented or wrapped).
- Download on first use: **conflicts** with the mission's words and §4.8 as written; it is a
  constitution change, not a specification.
- Security posture: a Rust core improves it in one way (the fix on crates.io the same day) and
  widens it in two (our own native binaries to attest and audit on 8 targets; a run-time
  network fetch in the embedder's process if delivery changes).
- Reproducibility: the artifact set stays byte-identical (nothing in the guest changes). The
  native binaries would be a new reproducibility problem the project has not studied (Rust
  builds across hosts are reproducible with care, INFERRED; not researched here).

### 2.2 Is the claimed benefit real?

Partly.

- The security lag is real but bounded by wasmtime's monthly major, which wasmtime-py has
  followed the same day for twelve months (§1.6). wasmtime 50 and the pin move retire spec
  048's shadows within weeks on the project's existing plan (decision 86).
- The design workarounds (010, 011, the `_ffi` reach-ins) are real and permanent on
  wasmtime-py. They cost about two specifications' worth of code and are already built, tested
  and landed. A Rust core would make them unnecessary, at the price of rebuilding everything
  else.
- A Rust core's own burden: a Rust toolchain pin per build host; 581 crates in wasmtime's lock
  file to pin and licence; eight native binaries per release for npm and about eight abi3
  wheels for PyPI; a release workflow that today runs on three runners and treats Windows as
  the fragile one (0.1.0a4 failed on Windows, READ roadmap); a release of our own for every
  wasmtime patch; two more registries (npm, and crates.io if published) in the supply chain.
- "One runner, three thin wrappers, one set of sandbox tests" is not what would result. The
  Python wrapper keeps the frozen API's dataclasses, `tools.py`'s schema and validation, and
  spec 053's asyncio integration; the JavaScript wrapper writes those afresh; the judge keeps
  its own driver. Closer to: one core, two thick wrappers, two test suites and the judge.

### 2.3 Is the port's risk sized right?

No. mounts.py is one of five hard parts (§1.8, §1.10). The frozen API, the door's threading
and cancel semantics, sessions, and the judge's independence from the runner each add a part
the proposal does not mention. Fuel equality is likely but must be measured (§1.9), and the
measurement is cheap, which is the strongest argument for a spike.

### 2.4 Artifact delivery

| | bundle in the package (today) | download on first use (proposed) |
|---|---|---|
| PyPI's 100 MiB (question 64) | needs a raise, or a split, at 0.1.0 | solved |
| offline and air-gapped embedders | `pip download` once; works | needs a side channel and `WASI_PYTHON_ARTIFACTS` |
| trust | the wheel is attested; `SHA256SUMS` inside it | the same hashes pinned in the package; availability now depends on GitHub |
| the embedder's process | no network | a fetch in a runtime that otherwise promises "no network"; a new threat-model row |
| the mission's words | "without … a package install step" | an install step at first run |
| one install, one call (§2.4) | yes | yes after the first call succeeds |
| what it reuses | the wheel rule and `artifacts()` | `00_download.sh`'s verify, rewritten in Python for a user cache; §4.8 amended |

The cache-and-verify pattern exists (§1.13) at build time. Reusing it at run time is a new
feature with a new rule. The project already has the hook an embedder needs for a separate
delivery: `WASI_PYTHON_ARTIFACTS` and `artifacts()`. An **optional** `wasi-python fetch`
command that writes a verified set where that variable points is the small version of the
proposal, and it keeps the default install self-contained. The JavaScript package, which has
no PyPI limit but may have npm's, decides its own delivery when it is specified.

For question 64 itself, nothing here changes the agent's recommendation on record: measure the
wheel as packages land, then ask PyPI for the raise with real numbers.

### 2.5 Timing

- **Before 0.1.0: no.** The owner's direction is "cancel nothing for 0.1.0"; the build-class
  queue is about ten deep with one slot; a Rust core is build-class (it changes the release
  workflow) and the largest change the project has considered. It would displace the scipy
  line, tier B, matplotlib M2 and sessions, each already decided in, and it would reopen spec
  049's freeze before the first release to rely on.
- **What a wasmtime 50 move does on its own, within weeks:** the pin to `>=50,<51`; spec 048's
  shadows removed (decision 86); the wasmtime-py facts sheet 12 closed. This takes away the
  proposal's most urgent reason.
- **Smaller steps that get most of the value:**
  1. A JavaScript path exists today: the CLI as a subprocess (README). It is slow to start and
     has no in-process tools, so it is a stopgap, not the answer.
  2. **A Rust spike as a research memo**, time-boxed: `run()` with grants, limits, fuel,
     deadline and the door, in Rust on `wasmtime` 49.0.3; the judge's five jobs run through
     both runners; `fuel_used`, exit codes and stdout compared; binary size, crate count,
     licence count and build time recorded. It commits the project to nothing and settles
     §1.9. It fits a parallel-safe slot (no `scripts/`, `recipes/` or workflow change) and can
     run now.
  3. **After 0.1.0, a separate Node package** on that core, consuming the published artifact
     set. The Python wheel stays on wasmtime-py.
  4. **Never, or only on evidence:** replacing wasmtime-py under the Python wheel. The trigger
     would be wasmtime-py breaking its pattern (no 50.0.0 within a week of wasmtime's), or a
     measured fault the Python runner cannot work around.

### 2.6 Recommendation

**Adopt in part, after 0.1.0.** In order:

1. Now, parallel-safe: a research memo, "A Rust runner spike against the judge", boxed at one
   session, written to `context/research/` by an agent that has read specs 001, 008, 013,
   015, 017 and 030; it answers §1.9 and §1.10 with numbers, and records the crate and licence
   count of a release binary.
2. After 0.1.0 and the wasmtime 50 pin move: a specification, "A Node package on the artifact
   set" (build-class: the release workflow publishes to npm): a napi-rs binding on a Rust core
   that does `run()` with grants, limits, the door and the tool protocol's wire with JavaScript
   tools; eight prebuilt targets; the artifact set bundled or fetched as its own decision
   after npm's limit is checked; conformance checks that run the judge's jobs through it and
   compare `fuel_used` and outputs with the Python runner. Node first; Bun as best effort;
   Deno not promised.
3. Not adopted: PyO3 under the Python wheel, and download-on-first-use as the default
   delivery. Revisit the first only on the trigger in §2.5 item 4; offer the second as an
   optional `wasi-python fetch` if PyPI refuses the raise.

## 3. Where it stopped

- No Rust was written or built; the fuel-equality claim is INFERRED and is what the spike is
  for.
- npm's package size limit and the reproducibility of Rust release binaries across hosts were
  not researched.
- wasmtime 50.0.0's release date is a projection from rc.1 and the last twelve majors; the
  owner should check `pypi.org/project/wasmtime` in the week of 2026-10-20.

## One line

A JavaScript binding on a Rust core fits the constitution and is worth building as its own
package after 0.1.0, but replacing wasmtime-py would rebuild a 7,900-line, 944-test, frozen-API
runner to escape a security lag that wasmtime 50 closes within weeks, so spike it now, build the
Node package later, and keep the wheel bundled on wasmtime-py.
