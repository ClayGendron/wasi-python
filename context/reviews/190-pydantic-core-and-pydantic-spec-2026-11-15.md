# Review of 190 — pydantic-core and pydantic (before it is built)

- **Date:** 2026-11-15
- **Reviewer:** an agent (Claude), a fresh sub-agent of https://claude.ai/code/session_01BD1pVHiZoxnwRv6JCqJKeC; not the author
- **Reviewed:** the specification as drafted on `spec/190-pydantic-core-and-pydantic` at `d05fe7cb` (one commit on 187's local tip `d58bea64`), read against AGENTS.md, constitution §4, §5.6 and §7, `decisions.md` ("0.1.5's scope", "The Rust crates' licences", "34, answered"), `roadmap.md` (0.1.5), spec 187 and its pre-build review, `recipes/rust/`, `scripts/steps/52_rust.sh`, `scripts/rust_objects.py`, `recipes/reactor_main.c` (the teardown hook), `recipes/snapshot-packages.txt` and `src/wasi_python/_snapshot_make.py`.
- **Run:** none; a pre-build review has no pull request run. Nothing built into `python.wasm`, nothing dispatched, no `gh`, no push.
- **Box:** 45 minutes (build-class).
- **Re-ran** (EXECUTED unless marked; scratch in the session's scratchpad, `rev190/`; the main tree's prior-art clones read only):
  - PyPI's JSON for the five packages, read 2026-11-15: newest are pydantic 2.14.3, pydantic-core 2.50.4, annotated-types 0.8.0, typing-inspection 0.4.5, orjson 3.13.0. All seven SHA-256 values of Decision 1 match. pydantic's `Requires-Dist` is `pydantic-core==2.50.4`, `annotated-types>=0.6.0`, `typing-extensions>=4.16.0`, `typing-inspection>=0.4.4`; typing-inspection's is `typing-extensions>=4.15.0`. pydantic-core 2.50.4 has 30 `cp315` wheels and a `cp314 … pyemscripten_2026_0_wasm32` wheel, so upstream already ships a 32-bit wasm build. All four are MIT.
  - `sha256sum` of the session's `pydantic_core-2.50.4.tar.gz` → `aead3b74…33c6`, as Decision 1 says.
  - A scratch crate depending on `pyo3-ffi` `=0.29.3` and `=0.30.1`, `cargo generate-lockfile --offline` (cargo 1.97) → "only one package in the dependency graph may specify the same links value". Decision 3's premise holds.
  - orjson 3.13.0 with both PyO3 requirements at `0.30`, `cargo check --release --target wasm32-wasip1 --offline --locked` with the build's eight-line PyO3 config file and wasi-sdk 34's clang → exit 0, no warning. A check only.
  - A scratch umbrella (`staticlib`) with orjson (`0.30` and `["cdylib", "rlib"]`), pydantic-core 2.50.4 and `_rust_probe` on `=0.30.1`, `cargo check` for `wasm32-wasip1`, offline → exit 0: one graph, one `pyo3-ffi` 0.30.1. The probe alone on 0.30.1 also checks with no warning, its source unchanged. The versions were the cache's, not Decision 4's.
  - `cargo metadata --filter-platform wasm32-wasip1` on pydantic-core's sdist → 66 normal, non-macro packages plus the root (67): 15 Unicode-3.0 (the ICU4X set Decision 12 names), foldhash Zlib, every other one MIT or offering MIT.
  - The three locks compared: the eight crates and the PyO3 family Decision 4 names, exactly. The lock has only `getrandom` 0.3.3. Merging pydantic-core's lock into the branch's adds 90 crate versions.
  - wasi-sdk 34's clang, a C program that `malloc`s 286 sizes from 1 to 2,000 bytes, run under wasmtime-py → 286 of 286 blocks 16-aligned, 74 of 286 64-aligned.
  - Native CPython 3.13, pydantic 2.14.3 and pydantic-core 2.50.4 (`uv run --with`), a `gc` census → after `import pydantic, pydantic.main, pydantic.type_adapter` no `SchemaValidator` or `SchemaSerializer` exists; after one `BaseModel` subclass, 1 and 3.
  - `grep` counts: `emscripten` 8 times in pydantic-core's tests and 12 in pydantic's, as Decision 9 says.
  - READ: orjson's `src/alloc.rs`; regex-automata 0.4.18's `src/util/pool.rs`; wasi-libc's `dlmalloc/src/dlmalloc.c:31` (clone at `4ec32c5`); rust-src 1.100.0's `library/std/src/sys/alloc/mod.rs` and `unix.rs`; ahash 0.8.12's `src/random_state.rs`; getrandom 0.3.3's `src/backends/wasi_p1.rs`; foldhash 0.2.0's `src/seed.rs`; version_check 0.9.5's `src/lib.rs`; pydantic-core's `Cargo.toml`, `.cargo/config.toml`, `build.rs`, `src/recursion_guard.rs`, `src/validators/model_fields.rs` and its `ahash` users.

## Acceptance criteria against evidence
1. Pins and the pair rule — testable, and the pins match today (EXECUTED above). The rule is not required to be seen failing first (finding 9).
2. Step 52 builds the three crates on 0.30.1 — the graph type-checks (EXECUTED, check only). "pydantic-core's kept object" cannot be judged under fat LTO (finding 5).
3. Landing notes: the moved crates, the alignment and the search — testable, but the search's result is already known (finding 1), and its method is not a command.
4. Imports, tags, constructors, features, `round` — testable, as in 187.
5. The `ci:full` run — testable, and it is the owner's gate (see below). Option B can leave it never run (finding 2).
6. Same bytes — testable.
7. Bytes, fuel and the sweep — testable. The sweep holds today (EXECUTED).
8. The owner's answers — testable, but it omits 187's two questions, which Depends says stand here too (finding 9).

## Findings, most severe first
1. **Medium: Decision 5's check has already found an alignment above malloc's, and "slower, not wrong" is not shown** (spec lines 96–105).
   - What the check finds. regex-automata 0.4.18 puts each pool stack in `#[repr(C, align(64))] struct CacheLine<T>` (`pool.rs:414`). `Pool::new` pushes them into a `Vec` (`:558–561`), so every compiled `Regex` makes one 64-aligned heap request. pydantic-core depends on `regex` 1.13.1.
   - What malloc gives. wasi-libc's `MALLOC_ALIGNMENT` is 16 (READ). wasi-sdk 34's `malloc` returned 74 of 286 blocks 64-aligned (EXECUTED).
   - What orjson's allocator does. Its `alloc` and `realloc` drop `Layout::align`, which breaks `GlobalAlloc`'s contract. That makes the misalignment undefined behaviour in Rust's model. That wasm tolerates it is INFERRED.
   - What upstream does. The spec's "honouring alignment (INFERRED)" can be READ: std on `wasm32-wasip1` uses `malloc` up to `MIN_ALIGN` 8 and `posix_memalign` above it (rust-src 1.100.0, `sys/alloc/mod.rs:9–31`, `unix.rs:30`, `:78–97`).
   - Failure: every `Regex` in pydantic-core gets a pool buffer at a 16-byte boundary where Rust promised 64. Any code that reads the address (`align_offset`, a tag in the low bits, a checked `is_aligned`) then misbehaves, with no trap to show it.
   - Fix:
     - Ask this question now, beside Decisions 3 and 7, not after the build.
     - Say that its fallback, a patch that drops orjson's allocator, is a third carried orjson patch. Like A, it rides on 187's unanswered question about a standing patch.
     - Make the search a command: explicit `align(N)` with N above 16, and `Layout::from_size_align` with a constant, over the merged lock's `wasm32-wasip1` normal graph. Say which kinds count: heap, not a static or the stack.
     - Make Decision 10's patch count follow from the answer.
   - **187 is affected too.** There the same allocator serves PyO3, `_rust_probe` and std, and 187 never names it. In orjson's 11 crates, the alignments above 16 are a static table or a stack type behind x86 features: zmij `lib.rs:417`, xxhash-rust `xxh3.rs:21–28` and `:857`, simdutf8's helpers. So 187 breaks the contract in principle and has no known heap case (INFERRED). 187's pull request review should record it.
2. **Medium: Decision 3's fallback tree is wrong where it depends on 187** (lines 81–84).
   - The 187 patch. Both A and B need 187's patch 0001. An orjson release on PyO3 0.30 still declares `crate-type = ["cdylib"]`, which the umbrella cannot link.
   - So "If the owner refuses 187's standing patch, A falls with it and B is what is left" is wrong. A refusal takes orjson out of the umbrella by any route. pydantic-core then goes in alone on 0.30.1, with no orjson patch, and std's allocator would serve it. Decision 5 would then not arise.
   - The gate under B. If no orjson release comes before the cut, pydantic-core leaves 0.1.5, and the second half of the owner's gate never runs. The owner said "If that fails, 0.1.5 ships with `panic=abort`" and did not say what happens if it never runs.
   - Fix: write the tree as it is.
     - 0001 kept → A or B.
     - 0001 refused → orjson out, pydantic-core alone.
     - B with no release → state the panic strategy 0.1.5 ships with. The recommended default is abort, unless the gate ran.
   - Tell the owner one more fact. Patch 0002 has a natural end that 0001 lacks: orjson moving to 0.30 deletes it.
3. **Medium: Decision 7's question understates who gets fixed keys** (lines 113–127).
   - The keys are drawn when any schema is built, not only when JSON is validated. pydantic-core's `definitions.rs` and `validators/shared/lookup_tree.rs` use ahash (READ). Natively, one `BaseModel` subclass builds one validator, while the imports alone build none (EXECUTED, the census). So a prelude that only defines a model fills `SEEDS` (INFERRED).
   - Under 157's pinning they are the keys of zero entropy. That makes them the same in every embedder's image, and anyone with the set can compute them. A's sentence, "those of the moment it was made", hides that.
   - CPython's string hash in the snapshot is the same class, so A remains a fair default.
   - Fix:
     - A's limitations sentence says the keys are the same in every prepared image whose prelude defines a model.
     - The builder counts `__wasi_random_get` calls while `make_package_snapshot()` prepares its default list, now that pydantic is on it, and records whether import alone draws.
4. **Low: the owner's questions are not recorded as asked.** AGENTS.md says anything waiting on the owner is asked with AskUserQuestion. 187's Status says "asked on 2026-11-14"; 190's says only "Open". Fix: ask Decisions 3, 5 and 7 in one AskUserQuestion, each with its default first, finding 2's tree beside them. Write "asked <date>" in the Status.
5. **Low: criterion 2's "pydantic-core's kept object" does not exist.** Under fat LTO all Rust code is one object, named after the umbrella (187, Decision 6). Fix: "its line names pydantic-core among the modules, the kept members being the umbrella's object, yyjson's objects and the shim".
6. **Low: the crate pins are about 90, not "about 60"** (line 94; EXECUTED count). The lock also lists crates for other targets: js-sys, five wasm-bindgen crates, wasi 0.14.2, wit-bindgen-rt, r-efi, bumpalo and log. They need pins and fetches though they are never compiled. The sweep rightly leaves them out. Fix: say both.
7. **Low: the "higher" rule moves the code pydantic-core ships.** zmij goes from 1.0.6 to 1.0.23 under its `serde_json`, which formats pydantic's JSON floats; `lib.rs` grew from 972 to 1,857 lines (EXECUTED, `wc`). libc, once_cell and portable-atomic move too. Fix: add floats to the golden job's `model_dump_json`: 0.1, 1e16, 1e-7, 5e-324, -0.0 and a large integer-valued float. Name the moved shipped crates in the landing notes.
8. **Low: orjson's `alloc_zeroed` writes before it checks for NULL** (`src/alloc.rs`). On wasm, address 0 is writable memory. A zeroed request that fails under the memory limit therefore clears low memory instead of faulting, and std aborts after it. This affects 187 too. Fix: name it in Decision 5 beside alignment; the fallback patch removes both.
9. **Low: write-ins.**
   - Under the abort switch, `test_a_panic_after_pydantic_validates_is_caught` becomes a known gap, as 187's panic test does.
   - Criterion 1 holds Decision 10's rules seen failing first, as criterion 5 holds the checks.
   - Criterion 8 names 187's two questions.
   - If rich is not yet in the set, `kit-extra.txt` takes rich, markdown-it-py, mdurl and pygments.
   - In A, "whatever the owner answers 187" reads as independence. Make it "on the terms the owner sets for 0001".

Judged sound (no finding):
- The pins and the pair, which is pydantic's own (EXECUTED).
- One PyO3 at 0.30.1, the scratch checks above (EXECUTED).
- The eight-crate list (EXECUTED).
- version_check reads the channel, not `RUSTC_BOOTSTRAP` (READ, `lib.rs:302–304`).
- pydantic-core's `.cargo/config.toml` is not read from `build/`, and its `build.rs` adds no link flag for wasi (READ).
- The 49-level guard (READ).
- The shim's two names, std's and getrandom 0.3.3's, imported with `wasm_import_module` (READ, `wasi_p1.rs:9–11`).
- foldhash reads the wrapped clock (READ).
- The ahash `OnceBox` (READ).
- The licences (EXECUTED).
- The size and fuel estimates, labelled INFERRED and consistent with 187's spikes. The wheel estimate is about 3 MB against pydantic's 494,071-byte wheel and two 1.39 MB gzipped modules.
- Decision 34: the default snapshot still pre-imports nothing. The new list feeds only `make_package_snapshot` (READ).
- The panic gate matches the owner's decision ("0.1.5's scope"):
  - unwinding on the pinned stable compiler;
  - a CI run that links it, runs both pydantic suites in the sandbox and tests a deliberate panic;
  - abort as the fallback.

  187's run is the first half and this pull request's `ci:full` run the second, on Linux and Windows. Finding 2 covers the case where it never runs.

## Constitution checks
- §4.1: patch 0002, and Decision 5's fallback, carry 187's High: orjson takes no pull requests, and 187's owner question is unanswered (findings 1 and 2). No patch to pydantic-core.
- §4.2: the seven pins hold. The crate pins are written at build time, as in 187.
- §4.4: no new import by design. getrandom's `random_get` is shimmed, and step 52's gate fails on anything else.
- §4.6, §4.12: the four MIT packages are approved in "0.1.5's scope", and the crate licences in "The Rust crates' licences". Amending §4.12 to name the four follows that record.
- §5.6: reviewed before it is built, as required.
- §7: nothing tripped yet. The open owner questions are provisional defaults on a draft, on 187's terms: no "Lands" until `decisions.md` records them.

## Disposition (filled in by the author, then confirmed by the reviewer)
The round's fix commit follows `c2567df0`. It changes only the specification and this section.

1. **Fixed; waits on the owner.** Decision 5 is now an owner question. Its recommended default A is a third carried orjson patch, `0003-no-global-allocator.patch`, so that std's `System` serves every crate; B keeps orjson's allocator and the contract break.
   - The decision states regex-automata's 64-aligned `CacheLine`, wasi-libc's 16, std's `malloc`/`posix_memalign` split (READ, from this review), and the `alloc_zeroed` write at address 0 (finding 8).
   - It says the fallback rides on the terms set for 0001 and has no natural end. It is asked only when 0001 is kept.
   - The search is a command: `cargo tree` over the `wasm32-wasip1` normal graph, then `grep` for `align(N)` and `Layout::from_size_align` above 16, each hit classed heap, static or stack. It names 187's static and stack hits for 187's pull-request review.
   - Decision 10's patch count follows the answers.
2. **Fixed; waits on the owner.** Decision 3 spells out the whole tree:
   - 0001 kept, A: patch 0002, which orjson's own move to PyO3 0.30 deletes.
   - 0001 kept, B: wait for an orjson release; if none comes before the cut, pydantic-core leaves 0.1.5 and the gate never runs.
   - 0001 refused: orjson out, pydantic-core alone on 0.30.1, no orjson patch, and no Decision 5.

   The new Decision 8 question covers a gate that never runs. Its recommended default A is `panic=abort` unless the gate ran on `panic=unwind`; B ships `panic=unwind` on 187's half of the gate alone.
3. **Fixed; waits on the owner.** Decision 7 now says the following:
   - The keys are drawn when any schema is built, citing the census.
   - Under pinning they are the keys of zero entropy: the same in every embedder's image, and computable by anyone with the set.
   - A's limitations sentence says this.
   - The builder counts `__wasi_random_get` calls while `make_package_snapshot()` prepares its default list (criterion 3).
4. **Waits on the orchestrating session.** The author is a sub-agent and cannot ask the owner. The Status says the four questions and 187's two are to be asked together with AskUserQuestion, each with its default first and Decision 3's tree beside them, and that none had been asked when it was written. It also says the specification is not to be built until they are answered. It records no answer and no default as the owner's.
5. **Fixed.** Criterion 2 names pydantic-core among the modules. The kept members are the umbrella's object, yyjson's objects and the shim's.
6. **Fixed.** Decision 4 says about 90 crate versions. It names the other-target crates that are pinned and fetched but never compiled, and says the sweep leaves them out.
7. **Fixed.** Decision 4 names zmij's move and the other shipped crates that move, and the landing notes are to name them. The golden job's `model_dump_json` covers the six floats.
8. **Fixed.** This is in Decision 5, beside alignment; option A removes both problems.
9. **Fixed.**
   - Decision 8: under abort, the new check becomes a known gap.
   - Criterion 1: Decision 10's rules are seen failing first.
   - Criterion 8 names 187's two questions and Decision 8.
   - Decision 9: rich, markdown-it-py and mdurl join `kit-extra.txt` when rich is not yet in the set. pygments is already in `kit.txt` (READ), so it is not added.
   - Decision 3's A now reads "on the terms the owner sets for 0001".

## Reviewer's confirmation (round one, on 0f7b30a2)
Same reviewer. I read `0f7b30a2` whole with `git show --word-diff` (READ). It changes the specification and this file's Disposition only.

1. **Confirmed.** Decision 5 is now an owner question. A, the default, is patch 0003, which drops orjson's allocator. B keeps the contract break. The decision states the regex-automata case, malloc's 16, std's split and the `alloc_zeroed` write, each with its label. It says 0003 rides on 0001's terms and has no natural end. The search is now a command, with each hit classed heap, static or stack. Decision 10's patch count follows the answers.
2. **Confirmed.** Decision 3 now gives the whole tree. Under 0001 kept, A and B both need 0001, and B with no release leaves the gate unrun. Under 0001 refused, orjson is out and pydantic-core goes in alone, with no Decision 5. 0002's natural end is named. The new question in Decision 8 covers a gate that never runs, with abort first.
3. **Confirmed.** Decision 7 says the keys are drawn when any schema is built, and that they are zero entropy's keys, the same in every embedder's image. A's sentence on the limitations page says so. Criterion 3 holds the builder's count of entropy reads during `make_package_snapshot()`.
4. **Confirmed, as written.** The Status names the four questions and 187's two, for the orchestrating session to ask together with AskUserQuestion. It records that none had been asked, and it records no default as the owner's. Asking them is the orchestrator's next step.
5. **Confirmed.** Criterion 2 names the kept members as they are under fat LTO.
6. **Confirmed.** Decision 4 says about 90 versions and names the other-target crates.
7. **Confirmed.** Decision 4 names zmij's move and the shipped crates that move. The golden job covers the six floats.
8. **Confirmed.** It is folded into Decision 5, and A removes it.
9. **Confirmed.** Each write-in is in. pygments is in `tests/upstream/kit.txt` (READ, line 5), so leaving it out of `kit-extra.txt` is right.

One write-in, Low, which needs no round. The Status says "Not to be built" until the answers come. Criterion 8 says the answers come "before the pull request is built past its draft". That is the same rule in two wordings. When the answers are recorded, criterion 8 can say simply "before it is built".

## Verdict
The specification is ready to build as it stands at `0f7b30a2`: every finding is fixed. Building waits on the owner's answers to Decisions 3, 5, 7 and 8 and to 187's two questions, which are not yet asked. Once `decisions.md` records them, it may be built stacked on 187's reviewed tip, on the branch of Decision 3's tree that the answers pick.
