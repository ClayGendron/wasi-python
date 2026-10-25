# 134: fuel counts the work a caught exception ends

- **Status:** **drafted 2026-10-25** from the 0.1.0 security audit (`../reviews/0.1.0-security-audit-2026-10-25.md`, finding F3 and the binaries' hardening notes). A judge-and-documents specification: no `src/` change. Its pre-build review is optional (AGENTS.md, rule 8); the owner may ask for one since it touches `SECURITY.md`.
- **Date:** 2026-10-25
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, a **judge change** and documents: one check file (fuel-counted, slow tier), one row in `tests/checks/test_v1_1_artifact_set.py` or beside it (the tag count), `tests/known_gaps.toml` (one gap, closed by 127), `SECURITY.md`, `docs/explanation/security-model.md`, `docs/explanation/fuel.md`, `CHANGELOG.md`, and an addendum to `../research/2026-10-18-wasmtime-49-advisories.md`. No `src/`, `scripts/`, `recipes/`, pins or artifact byte.
- **Depends on:** nothing. **127 (the pin moves to wasmtime 50) closes the gap this specification records**: wasmtime 50.0.0 carries the fix of GHSA-m63x-6p34-q65x (fixed in 49.0.1). This specification may land before, with or after 127; if after, its gap entry is never written and its check lands green.
- **Research it stands on:** the audit's F3 (`0.1.0-security-audit-2026-10-25/FINDINGS-DETAIL.md` §3; fingerprint `wasmtime-49.0.0:GHSA-m63x-6p34-q65x:try_table-catch-fuel:src/wasi_python/_engines.py:_engine`), found by h17, verified by v04, promoted by r04, re-verified by v05 and record-checked by r05 (`agents/h17-eh-advisories/`, `agents/v04-eh-fuel/`, `agents/v05-eh-fuel-recheck/`, `agents/r04-eh-fuel/`, `agents/r05-eh-fuel-final/`); h12's and h18's reads of the binaries (`agents/h12-binary/`, `agents/h18-gc-exnref/`); `../research/2026-10-18-wasmtime-49-advisories.md`, whose table this corrects; `../research/2026-10-24-moving-to-wasmtime-50.md`.

## The problem

`run()` calls fuel "a cap on the guest's executed instructions", and `SECURITY.md` lists a guest that runs past its fuel cap as in scope. On wasmtime-py 49.0.0, the only version the pin admits, that is not what fuel counts.

GHSA-m63x-6p34-q65x (medium, fixed in wasmtime 49.0.1): on the exceptional edge of a call inside `try_table`, Cranelift's fuel accounting resets fuel to what remained before the call, so the callee's work before the throw is not counted. The project's advisory memo of 2026-10-18 rated it "unlikely: our C-built core module uses neither [proposal]" and said so was INFERRED, not shown by disassembly. The audit disassembled: `python.wasm` is linked with `-fwasm-exceptions` (`scripts/steps/60_link.sh:129`), every C++ package is compiled with it (`scripts/steps/55_matplotlib.sh:50,102`; `recipes/wasi-scipy.cross:44` and the other cross files), and the binary carries **44,791 `try_table` sites in 7,905 functions and 2 tags** (`__cpp_exception`, `__c_longjmp`). Every caught C++ exception, and every `longjmp` under `-wasm-enable-sjlj`, takes the edge the advisory names.

**From guest Python** (EXECUTED twice, independently, through `wasi_python.run` on the shipped set with fuel given and `deadline_s=None`): kiwisolver's `Solver.addConstraint` catches `UnsatisfiableConstraint` after the C++ solver builds a row whose size grows with the system. One failing call is counted at about 17,000 to 19,600 fuel whether the chain has 200, 2,000 or 6,000 variables, while its wall time grows from 9.6 to 190 µs. A same-shape no-throw control is counted at 140,067 fuel per call at 200 variables and 1,552,404 at 2,000. Under a cap of 2.2e9, 20,000 failing calls on a 2,000-variable chain finished with exit 0 and 2.02e9 fuel used; the same-shape no-throw loop and a weak-strength add-and-remove loop each ended `out of fuel` under the same cap. A standalone WAT module shows the engine defect alone: 100 rounds of a 100,000-iteration callee that throws count as 1,101 fuel on wasmtime-py 49.0.0 and 80,001,285 on the pinned CLI 49.0.3 (`agents/v04-eh-fuel/scratch/evidence/eh_fuel.wat`). By wall-time calibration the under-count is about 100 times at 6,000 variables.

**What still holds.** A finite `deadline_s` (the default is 60 s) bounds wall time through epoch interruption, which the advisory does not touch. So the cap is lost only where fuel is the bound an embedder relies on: `deadline_s=None` with fuel, a fuel cap tighter than the deadline, or `fuel_used` read as an instruction count. The security model's "a guest that waits with `deadline_s=None`" bullet is the nearest existing sentence; it does not say this.

**Two more facts of the binaries the memo got wrong or left unmeasured** (h17, h18, h12, EXECUTED): GHSA-p79w-pv2r-29qp is avoided only because the tag count is even (2); one more tag would meet its precondition on 49.0.0 to 49.0.2. GHSA-hw8m-q44c-ggrf is unreached not because "no GC proposal" but because no `exnref` local is live into a catch continuation across 102,646 `try_call` edges, a property of this LLVM 23 / wasi-sdk 34 build that another toolchain could change. The `br_table` maximum of 3,203 labels (against about 256k for GHSA-mghf-wjfp-p5xm) is measured by hand.

## Decisions

### 1. The check: a failing call's fuel grows with the system as the no-throw call's does

One slow-tier check, counted in fuel only (AGENTS.md: tests count operations, never wall-clock), `tests/checks/test_v1_4_embedding.py::test_fuel_counts_the_work_a_caught_exception_ends` or its own file in the `own-embedding` shard: the kiwisolver chain at two sizes (200 and 2,000 variables), one failing `addConstraint` and one same-shape no-throw add-and-remove per size, each in its own call with `fuel=` far above the work and `deadline_s=` set (so the check cannot hang on a slow runner). The assertion is a **ratio**, not a number: the failing call's per-call fuel at 2,000 variables is at least 3 times its fuel at 200, as the no-throw call's is (about 11 times, EXECUTED). On 49.0.0 the failing call's fuel is flat (18,619 against 18,112) and the row is red. Its guest program is the audit's driver, rewritten to the judge's conventions (`agents/v05-eh-fuel-recheck/scratch/`).

**The gap.** Until 127 lands, the row enters `tests/known_gaps.toml` with its closer named: "134: fuel under-counts C++ work that ends in a caught exception on wasmtime 49.0.0 (upstream GHSA-m63x-6p34-q65x, fixed in 49.0.1); closed by 127, the pin moves to wasmtime 50". The gap is written by this specification, never by a builder turning a run green (rule 4). When 127 lands, 127's builder deletes the gap entry and the row is green, which 127's claim list names.

### 2. The binaries' facts become per-build rows

Three rows beside the artifact-set checks (`tests/checks/test_v1_1_artifact_set.py`), each reading `python.wasm` with the harness's own reader (`tests/harness/wasm.py`), each green today, each a fact that another toolchain or another package could move:

- **the tag section holds an even count** of tags (2 today), with the comment that an odd count meets GHSA-p79w's precondition on wasmtime below 49.0.3; the row is retired by the specification that moves the floor past 49.0.3 (127 may retire it in its claim list, or leave it as a fact);
- **the largest `br_table` has at most 65,536 labels** (3,203 today), well under GHSA-mghf's about 256k; a fact row that stays;
- **the exception-handling and GC facts recorded**: the module declares the proposals it uses (`+exception-handling`; no `rec` groups, no typed function references: 858 plain function types), as a fact row; the `exnref` liveness scan is **not** a row (it needs a full code-section decoder the harness does not have) and is recorded as a research fact with its script (`agents/h18-gc-exnref/artifacts/evidence/`), rerun by hand at a toolchain change until the floor passes 49.0.2.

### 3. `SECURITY.md`, the security model and the fuel page

`SECURITY.md`, *Upstream advisories the runner handles*, gains a third bullet, under a heading that says it is **not** handled: "**GHSA-m63x-6p34-q65x** (medium, fixed in wasmtime 49.0.1): on wasmtime 49.0.0, the fuel cap and `fuel_used` under-count work a guest does inside a C++ call that ends in a caught exception or a `longjmp`; the compiled-in packages are built with exceptions on, and a guest reaches such a call from plain Python. The runner carries no fix: the exceptions proposal cannot be turned off, because the build depends on it. A finite `deadline_s` (the default, 60 s) bounds wall time through epoch interruption, which the advisory does not affect. The fix is the pin's move to wasmtime 50." When 127 lands, the bullet moves to the handled list in 127's words, as the two others do.

`docs/explanation/security-model.md`, *Time, randomness and hashing*: beside "a guest that waits with `deadline_s=None`", one bullet: "**Fuel as the only bound** on wasmtime 49.0.0: work inside a C++ call that ends in a caught exception is not counted, so a guest that relies on such calls runs past its fuel cap. Keep a finite `deadline_s` beside fuel." `docs/explanation/fuel.md` says the same in one sentence where it says what fuel counts.

### 4. The advisories memo gets an addendum, not a rewrite

`../research/2026-10-18-wasmtime-49-advisories.md` gains a dated section, "Addendum, 2026-10-25, from the security audit": the module **does** enable exception handling (the counts above), so m63x reaches it (confirmed, F3); p79w is unreached only by the even tag count; hw8m is unreached by the `exnref` liveness property, not by the absence of GC; wjc8 is unreached as the memo said, with the type-section facts as the reason; j2g9 (set-times) is in range and not reachable through CPython's `utime`, as the memo said. The table's rows are left as written, marked "see the addendum". The memo's "Where it stopped" asked for exactly this disassembly.

## Intent

After this specification, the judge knows what fuel fails to count on the pinned engine and says so as a gap with its closer, so the defect cannot return unseen when the pin moves again; the facts of the binaries that keep three more advisories away are rows a rebuild must pass; `SECURITY.md` tells an embedder that fuel alone is not a bound on wasmtime 49.0.0 and what to do; and the advisory memo says what the audit measured.

## Design

- `tests/checks/test_v1_4_embedding.py` (or its own file in `own-embedding`): the fuel-ratio row of Decision 1, its guest program from the audit's driver; `tests/known_gaps.toml`: its gap, closer 127, unless 127 landed first.
- `tests/checks/test_v1_1_artifact_set.py`: the three fact rows of Decision 2, reading `python.wasm` through `tests/harness/wasm.py`.
- `SECURITY.md`, `docs/explanation/security-model.md`, `docs/explanation/fuel.md`, `CHANGELOG.md`: Decision 3; `../research/2026-10-18-wasmtime-49-advisories.md`: the addendum of Decision 4.
- No `src/` change. The commits, in order: the specification with its roadmap line; the rows and the gap; the documents and the addendum.

## Scope

In: Decisions 1 to 4 and the CHANGELOG line ("Fuel on wasmtime 49.0.0 under-counts work that ends in a caught C++ exception (an upstream advisory); `SECURITY.md` says so and the judge holds the gap until the pin moves to wasmtime 50."). Out: any change to `src/` (requiring a finite `deadline_s` beside fuel would change an argument's meaning and is 127's to make unnecessary); turning the exceptions proposal off; the `exnref` liveness as a row.

## Acceptance criteria

1. Decision 1's row red on 49.0.0 with its gap entry naming 127 as closer (or green with no entry, if 127 landed first), counted in fuel only; the two per-call fuel pairs recorded in the landing notes, labelled EXECUTED.
2. Decision 2's three rows green on three systems against the frozen set; each seen failing against a hand-edited fixture (an odd tag count; a `br_table` past the bound) in the landing notes.
3. `SECURITY.md`, the security model, the fuel page and the memo's addendum carry Decision 3's and 4's text; no code file names an advisory id (spec 127's rule 3a's clause holds: the check's comments say the behaviour in words).
4. `ruff`, `mypy` clean; the rules checks green; the dispatch read.

## For the lane

- **Kind:** parallel-safe, judge and documents; next wave; shares `SECURITY.md` and `docs/explanation/security-model.md` with 127 (which rewrites the handled list) and with 132 and 137; `tests/known_gaps.toml` with 127 (which deletes this gap); `CHANGELOG.md`, `context/roadmap.md`.
- **Claim list** ("134:"): new rows of Decisions 1 and 2; one known gap (if before 127); retired none; lost passes none; fuel: the new row's own counts, recorded, not compared.
- **Flags:** `--accept "134: the judge holds the fuel under-count of a caught C++ exception on wasmtime 49.0.0 as a known gap closed by 127, and the binaries' tag count, br_table bound and proposal facts as rows; SECURITY.md names the advisory as unhandled"`, `--accept-judge "134: one fuel-ratio row with a known gap, three artifact-set fact rows; no existing expectation edited"`.
- **Order:** if 127 is in the same wave, 134 enters first so 127's deletion of the gap is in 127's diff.

## Landing notes

Not yet built. The builder fills this section: the commits, the checks seen failing on main's code first, the fast tier, the branch's release run (its id, every line green on three systems, no growth line), the self-check list (`../reviews/README.md`), and the rebase onto the wave's tip with every conflict named.

## One line

The fuel cap misses C++ work a caught exception ends on wasmtime 49.0.0; the judge records the gap with 127 as its closer, the binaries' advisory facts become rows, and `SECURITY.md` says fuel alone is not a bound until the pin moves.
