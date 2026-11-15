# Review of 187 — A Rust build pipeline, with orjson first (before it is built)

- **Date:** 2026-11-14
- **Reviewer:** an agent (Claude), a fresh sub-agent of https://claude.ai/code/session_01BD1pVHiZoxnwRv6JCqJKeC; not the author
- **Reviewed:** the specification as drafted on `spec/187-a-rust-build-pipeline-with-orjson-first` at `a98d6158` (commits `0bd363cb`, `a98d6158` on `origin/dev` `25e49df5`), with the branch's edits to `decisions.md`, constitution §4.12 and `prior_art/README.md`; read against AGENTS.md, constitution §4 and §5.6, `scripts/line.conf`, `scripts/steps/60_link.sh`, `80_snapshot.sh`, `common.sh`, `scripts/wasi-cc`, `scripts/gen_inittab.py`, `recipes/reactor_main.c` ("pinned"), `tests/harness/scan.py` (hosts, URLs, test sources), `wasm.py`, `constructors.py`, `pins.py`, the October memo, the spikes' working notes ("Ask 3", "Ask 4", "Crate licence sweep"), and the owner's "0.1.5's scope" at `654f3d52`.
- **Run:** none; a pre-build review has no pull request run. Nothing built, nothing dispatched, no `gh`, no fetch.
- **Box:** 45 minutes (build-class).
- **Re-ran** (all EXECUTED, on the spikes' leftovers in the session's scratchpad and the main tree's pinned tarballs, read only):
  - Decision 7's algorithm on Ask 4's stable-1.97 unwinding object (`spike/objs-bs/_pydantic_core-….o`): its `llvm-nm -u` names, Python's set aside, minus every global `llvm-nm -g --defined-only` finds in wasi-sysroot 34's `libc.a`, `libsetjmp.a`, `libwasi-emulated-mman.a`, `eh/libc++abi.a`, `eh/libunwind.a` and `libclang_rt.builtins.a` → exactly the two mangled `random_get` names, `__stack_pointer` and `__indirect_function_table`. Nothing needs a symbol only `compiler_builtins` defines.
  - Gate 2 on the same object → no overlap (its 4 globals: `PyInit_`, `PyModExport_`, `EMPTY_PANIC`, `rust_eh_personality`). The `compiler_builtins` object overlaps in 377 names, as expected.
  - `llvm-readobj --symbols` → both `random_get` symbols are `UNDEFINED|EXPLICIT_NAME` with `ImportModule: wasi_snapshot_preview1`, `ImportName: random_get`. `PyInit__pydantic_core` has flags `0x0` (not exported). `__cpp_exception` is an undefined TAG. `eh/libunwind.a` defines it (`D`).
  - `harness.wasm.parse_file` on the object → its only non-`env` import is `wasi_snapshot_preview1.random_get`. Its target features fit `constructors.FEATURES`.
  - The SDK's `llvm-cxxfilt` → `wasip1::lib_generated::wasi_snapshot_preview1::random_get`, `getrandom::backends::wasi_p1::random_get`.
  - Decision 1's ten SHA-256 values against the author's saved `channel-rust-stable.toml` (dated 2026-11-12; its own SHA-256 `3051e859…ef9258`) → 10 of 10 match, rustc `1.100.0 (0ef1bc386 2026-11-09)`.
  - `cargo metadata --offline --locked --filter-platform wasm32-wasip1` on a scratch copy of the orjson 3.13.0 clone → 11 normal packages, licences exactly as Decision 12 lists them.
  - `scan.prior_art_errors` with this branch's README over the main tree's clones → 0 errors. `uv run pytest tests/checks/test_rules.py -k "specifications or open_question or one_line or prior_art or memo_label"` → 2 passed, 1 skipped (no clones in the worktree), exit 0.
  - rust-src 1.97 (the `stable` toolchain): `library/vendor/` holds 30 crates, each with a per-file `.cargo-checksum.json`, and `library/.cargo/config.toml` points crates-io at them. The session's `~/.cargo/registry/cache` holds those same versions (hashbrown 0.17.1, libc 0.2.185, wasip1 1.0.0, addr2line 0.25.1, gimli 0.32.3), written at 22:11 and 22:19, during the build-std runs.
  - The Ask 4 probe's cargo fingerprints → its rustflags were `["-Cpanic=unwind"]` alone.
  - The 1.97 rustc component's `share/doc/rust/COPYRIGHT-library.html` lists `library/core/src/unicode/unicode_data.rs` under Unicode-3.0. rust-src's top folder holds only `library` and `src`.
  - orjson's `README.md:47` (READ): "There is no open issue tracker or pull requests".

## Acceptance criteria against evidence
1. Pins match on first fetch — the ten match the saved manifest (EXECUTED). The crate pins and orjson's two are `TBD`, and the std's own crates are missing (finding 4).
2. Step 52 offline from an empty cargo home — the design does not yet hold this: std's crates (finding 4), a cdylib link (finding 5) and host config (finding 6). The three planted refusals are sound tests.
3. Link-map and import-list gates refuse — sound. The planted import must be a field `python.wasm` lacks (finding 9).
4. Imports, tags, constructors, features unchanged — consistent with the spike object (EXECUTED above).
5. The `ci:full` run, unwinding — testable, but narrower than the owner's gate (finding 2).
6. Same bytes from two folders and across hosts — testable. Host environment leaks can break it (finding 6).
7. Bytes, fuel, sweep — testable. The sweep misses notices that are not crates (finding 7).
8. Prior-art rows — met (EXECUTED above).

## Findings, most severe first
1. **High: the orjson patch cannot meet §4.1** (Decision 3). §4.1 holds a carried patch to "an upstream pull request drafted … for the owner to send", and deletes it "once an upstream release carries the fix". orjson takes no pull requests and has no issue tracker (`README.md:47`, READ). The spec does not say so. Failure: the facts sheet is drafted, cannot be sent, and the patch stays in every release: a permanent change to an upstream tree that §4.1 does not allow. Fix: ask the owner before the build with AskUserQuestion. Recommended: accept this one patch as standing until orjson declares an rlib, with any channel the maintainer takes (the address in orjson's `Cargo.toml`) named in the facts sheet, and the patch re-checked at each orjson version. Record the answer in `decisions.md`. Alternatively, find a recipe-only route, if one exists.
2. **Medium: the CI gate the spec builds is not the gate the owner set** (Decision 8, "That is the CI run the owner asked for"). "0.1.5's scope" says the gate "runs both pydantic suites in the sandbox and tests a deliberate panic." orjson's entry points are raw `extern "C"`, so its suite never unwinds. Here only `_rust_probe` exercises unwinding. Fix: say that 187's run is the first half of the gate. pydantic-core's specification runs both suites on `panic=unwind`, and the abort switch stays open until then.
3. **Medium: Decision 8 adds flags the spikes never built with** (`-Ctarget-feature=+exception-handling -Cllvm-args=-wasm-use-legacy-eh=false`). Ask 4 passed `-Cpanic=unwind` alone (EXECUTED: fingerprints). That already turned on `exception-handling` and gave the standard form. The working notes tie the open ICE rust-lang/rust#156469 to `-wasm-use-legacy-eh=false`. Failure: 1.100.0 hits that ICE on a flag nothing needed, and the builder throws the abort switch for the wrong reason. Fix: build with `-Cpanic=unwind` as run. The binary's existing standard-form check and the tag count already gate the form. If the explicit flags are wanted, try them once beside the plain form and record which built.
4. **Medium: build-std's own crates are not where Decision 2 says** (Decision 2, ¶1). Cargo resolves std's dependencies through crates-io, so the replacement in `build/.cargo/config.toml` sends them to `build/rust/vendor/`. The spikes' cargo downloaded exactly rust-src's vendored versions from crates.io during their build-std runs (EXECUTED, the registry cache; INFERRED cause). The fallback also collides with Decision 14's rule "no crate pin lacks a lock package", since those crates live in `library/Cargo.lock`. Fix, decided now: step 52 copies rust-src's `library/vendor/*` into the same directory source. They are already pinned by rust-src's SHA-256 and carry per-file checksums (EXECUTED), so they need no new pins. The crate rule reads `recipes/rust/Cargo.lock` only, and a name and version in both folders must hold identical bytes.
5. **Medium: orjson's patched `cdylib` may need the target library the spec drops** (Decision 1 ¶3, Decision 3). Cargo compiles a dependency's lib with every declared crate type (INFERRED). A `wasm32-wasip1` cdylib links against the self-contained `crt1-*.o` and `libc.a` that only `rust-std-…-wasm32-wasip1` ships (EXECUTED: the 1.97 `self-contained/` folder). The spikes never built a cdylib under build-std: the October one had that library installed, and Ask 4 wrote only `.a` files. Fix, decided now: pin that host-neutral file from the start (its hash is in Decision 1), or patch the crate type to `["rlib"]` (folded into finding 1's question). Not left to a failed first build.
6. **Medium: the host's Rust settings leak into the build** (Decisions 5.4, 15). Cargo takes `CARGO_ENCODED_RUSTFLAGS`, then `RUSTFLAGS`, before any `CARGO_TARGET_<triple>_RUSTFLAGS` (INFERRED from cargo's documented order). A builder's `RUSTFLAGS` silently drops the remaps and the panic flags. `RUSTC_WRAPPER` (sccache) puts an unpinned tool in the compile. Cargo also reads `.cargo/config.toml` from every ancestor of its working folder, `$HOME/.cargo` included when the checkout lies under it. With `--manifest-path`, it does not read `build/.cargo/` unless it runs from there. Failure: different bytes on the owner's Mac, or a replacement never read. Fix: put the source replacement in `$CARGO_HOME/config.toml`. Pass the flags by `CARGO_ENCODED_RUSTFLAGS`. Unset `RUSTFLAGS`, `RUSTC_WRAPPER`, `RUSTC_WORKSPACE_WRAPPER`, `CARGO_BUILD_*` and `CARGO_PROFILE_*` (except the step's own). Run cargo from `build/`, and refuse any ancestor `.cargo/config*`. Add a rule over all of it.
7. **Medium: two compiled-in notices lack a recorded approval, and Rust's notice is read from the wrong place** (Decision 12). (a) yyjson (MIT) is vendored C, so a `cargo metadata` sweep cannot see it. The owner's recorded words are "MPL-2.0 for orjson's compiled code" and "Yes to both" to a crate sweep, and `decisions.md`'s new entry does not name yyjson. Yet the branch writes it into §4.12. (b) Rust's own notice lists `core`'s Unicode tables under Unicode-3.0 (EXECUTED). core is in the build graph the spec ships notices for, but Unicode-3.0 is approved only for pydantic-core's ICU4X crates. (c) rust-src has no `LICENSE-MIT` or `COPYRIGHT` at its top. Rust's notices are the rustc component's `share/doc/rust/` (EXECUTED), a per-host tarball, so they must be read from one host or shown equal. Fix: put (a) and (b) to the owner in one question, record the answer in `decisions.md`, and point the notice at `share/doc/rust/`. yyjson's notice is the header comment of `include/yyjson/yyjson.h`. Its folder has no licence file.
8. **Medium: the crate trees are outside §4.1's tree check** (Decisions 2, 3; `tests/harness/pins.py`). Only orjson joins `SOURCE_PATTERNS`. The `.cargo-checksum.json` written with `"files": {}` turns off cargo's own per-file check. A changed file under `build/rust/vendor/` is compiled in and nothing sees it. Fix: write each file's SHA-256 from the verified `.crate` members, as `cargo vendor` does, so cargo refuses a change. Add the crate trees to the judge's tree check, or say why not.
9. **Low: make the direct-import gate read the imports themselves** (Decision 7). Name matching works today (EXECUTED), but `harness.wasm` reads each kept object's import entries exactly (EXECUTED). Fix: fail on any non-`env` import but `wasi_snapshot_preview1.random_get`, and shim the names whose count matches. The list of "names wasm-ld defines" is wrong: `__cpp_exception` comes from `eh/libunwind.a` (EXECUTED), so drop it and let the link's other inputs supply it. Say that this gate alone sees a bypass of a wrap. wasm-ld merges imports with the same module, field and type (INFERRED), so gate 5 sees only new fields, and criterion 3's planted import must be one. Name both binaries in gate 5.
10. **Low: Decision 6's member counts are for the shipped std.** Under build-std the spike's library held 2 members: the crate's object and one `compiler_builtins` object, with no compiler-rt C (EXECUTED). Fix: state both layouts.
11. **Low: the panic rule forbids step 52's own flag.** "No `-Cpanic` flag … in `scripts/`". Fix: the only one is `-Cpanic=$RUST_PANIC` in step 52.
12. **Low: Decision 13's entropy check may not be able to fail first.** If 1.100's std reads entropy through wasi-libc, there is no shim to leave out. Fix: say that it is then seen failing by linking without `--wrap=__wasi_random_get`, in scratch.
13. **Low: list `hashed(keys)` in Decision 9.** It is the probe's third function, within "a private rust module … for the panic tests" (INFERRED), and the packages page line should cover it.
14. **Low: name the harness rows.** orjson joins `assemble_artifacts.PACKAGES` and `paths.PACKAGES`, or step 90 refuses `orjson: orjson`. `pyo3`'s `later` needs pydantic-core's number reserved in `roadmap.md`. Name `test_v1_3_rust.py`'s files shard. Add `pytz` to the suite's skips (`test_datetime.py`, `test_memory.py`, `test_non_str_keys.py` guard it). Name `#105` in Depends, since this branch's `decisions.md` cites its entry.
15. **Low: record the trust roots.** Record the manifest's own SHA-256 beside the ten pins. Say that the lock's one online resolution reads `index.crates.io`, and that `RUSTC_BOOTSTRAP=1` reaches every crate's build probes (proc-macro2's), on every host alike.

Judged sound (no finding): one umbrella with the workspace at `build/`; keeping each crate's own objects (EXECUTED: nothing needs `compiler_builtins`); gates 1, 2 and 4; the shim's wrap route (`reactor_main.c` zeroes entropy and pins clocks while pinned, and Rust's clocks go through `clock_gettime`, EXECUTED as `U clock_gettime`); no new export (EXECUTED); `_rust_probe` as the owner approved it; the remap order; orjson's build script giving the same cfgs on every host, since pointer width 32 turns off its 64-bit branches (READ); the size and fuel claims, labelled INFERRED and to be measured.

## Constitution checks
- §4.1: not met for the orjson patch (finding 1). The crate trees are not checked (finding 8).
- §4.2: the toolchain pins hold. The std crates, a possible cdylib input and host config are not yet pinned or shut out (findings 4–6).
- §4.4: holds by design. The spike object's only direct import is `random_get`, which the shim routes. The step-52 gate fails closed on any other import (finding 9 makes it exact).
- §4.6, §4.12: the notices are incomplete (finding 7).
- §5.6: a build-recipe and artifact-set change, reviewed before it is built, as required.
- §7: nothing tripped yet. Finding 1 would trip the first bullet if built as written.

## Disposition (filled in by the author, then confirmed by the reviewer)
The round's fix commit follows `56acdc1f`; it changes the specification only.

1. **Waits on the owner.** Asked on 2026-11-14, not yet answered: whether the patch may stand, re-checked at each orjson version, or the crate type becomes `["rlib"]` alone. The specification's Status and Decision 3 carry an "Open for the owner" note; nothing is written in `decisions.md` until the answer.
2. **Fixed.** Decision 8 and criterion 5 call 187's run the first half of the owner's gate; pydantic-core's specification runs both suites on `panic=unwind`, and the abort switch stays open until then.
3. **Fixed.** Decision 8 builds with `-Cpanic=unwind` alone, as Ask 4 did, the binary's checks gating the form; the explicit flags are tried once beside it only if wanted, and recorded.
4. **Fixed.** Decisions 2 and 5: step 52 copies `rust-src`'s `library/vendor/*` into the same directory source, a name and version in both must hold identical bytes, and the crate rule (Decision 14) reads `recipes/rust/Cargo.lock` only.
5. **Fixed, first route.** Decision 1 pins `rust-std-1.100.0-wasm32-wasip1` from the start (eleven pins); the `["rlib"]` route waits on the owner's answer to finding 1, and drops this pin if chosen.
6. **Fixed.** Decision 5: the source replacement in `$CARGO_HOME/config.toml`, flags by `CARGO_ENCODED_RUSTFLAGS`, the host's Rust settings unset, cargo run from `build/`, an ancestor `.cargo/config*` refused; Decision 14 gains a rule over all of it.
7. **(a), (b) wait on the owner** (Decision 12's "Open for the owner" note, asked 2026-11-14). **(c) fixed:** Rust's notices are read from the rustc component's `share/doc/rust/`, from each host and checked equal; yyjson's notice is `include/yyjson/yyjson.h`'s header comment.
8. **Fixed.** Decision 2: each `.cargo-checksum.json` holds every file's SHA-256 from the verified `.crate`, and the crate trees join `SOURCE_PATTERNS`.
9. **Fixed.** Decision 7 reads the import entries with `harness.wasm`, fails on any non-`env` import but `random_get`, matches the shim count, drops `__cpp_exception` from wasm-ld's list, and says this gate alone sees a wrap bypassed; Decision 10's gate 5 names both binaries and a new field.
10. **Fixed.** Decision 6 states both layouts.
11. **Fixed.** Decision 14's panic rule allows step 52's one `-Cpanic=$RUST_PANIC`.
12. **Fixed.** Decision 13: if there is no shim to leave out, the check is seen failing by linking without `--wrap=__wasi_random_get`, in scratch.
13. **Fixed.** Decision 9 lists `hashed(keys)`; the probe has three functions.
14. **Fixed.** Decision 14's harness rows (`PACKAGES` twice, `pyo3`'s `later` with pydantic-core's number reserved when built); Decision 13 names `own-guest-c` and the `pytz` skips; Depends names #105.
15. **Fixed.** Decision 1 records the manifest's SHA-256; Decision 2 names `index.crates.io` for the one online resolution; Decision 8 says `RUSTC_BOOTSTRAP=1` reaches every crate's build probes on every host alike.

## Reviewer's confirmation (round one, on 75eb824a)
Same reviewer. `9d54f3e5` and `75eb824a` were read against the findings, and `git diff 338ed06d..HEAD` was read whole (READ).

1. **Answered provisionally: acceptable to build, not to land.** Decision 3 and the Status carry the default and say it awaits the owner (READ). The judgment is below.
2. **Confirmed.** Decision 8 and criterion 5 now say "the first half of the owner's gate" (READ).
3. **Confirmed.** The build uses `-Cpanic=unwind` alone, the flag the spike's fingerprints showed (READ; EXECUTED in round 0).
4. **Confirmed.** `library/vendor` joins the directory source, and a crate in both must hold identical bytes or the build stops (READ).
5. **Confirmed for the first route.** There are eleven pins, with the wasip1 rust-std (READ). If the owner picks `["rlib"]`, the pin goes and Decision 1's count changes. That change is local and reversible (INFERRED).
6. **Confirmed.** The fix has four parts and a Decision 14 rule over them (READ):
   - flags by `CARGO_ENCODED_RUSTFLAGS`;
   - the host's Rust settings unset;
   - cargo run from `build/`;
   - an ancestor `.cargo/config*` refused.
7. **(c) confirmed** (READ). **(a) and (b) are provisional, and one part is unfixed.**
   - Decision 12 says neither default is the owner's answer yet (READ).
   - §4.12 on the branch still reads "orjson 3.13.0 (… AND MIT) with yyjson (MIT)" as approved on 2026-11-14 (READ). `235d913c` wrote it, before this review.
   - The constitution changes only on the owner's recorded decision, and `decisions.md` does not name yyjson.
   - Fix, before the build commits anything else: drop "with yyjson (MIT)" from §4.12 until the owner answers, or mark it "asked 2026-11-14, awaiting the owner". When the answer comes, put core's Unicode tables in the same sentence.
8. **Confirmed.** Each `.cargo-checksum.json` holds per-file checksums from the verified `.crate`, and the crate trees join `SOURCE_PATTERNS` (READ).
9. **Confirmed.** Decision 7 reads the import entries themselves (READ).
10. **Confirmed.** Decision 6 states both layouts (READ).
11. **Confirmed.** The panic rule allows step 52's one `-Cpanic=$RUST_PANIC` (READ).
12. **Confirmed.** Decision 13's fallback links without `--wrap=__wasi_random_get` (READ).
13. **Confirmed.** Decision 9 lists `hashed(keys)` (READ).
14. **Confirmed.** Decision 14 names both `PACKAGES` rows and `pyo3`'s `later` row (READ). #105, which Depends names, is on dev as `8d85302a` (EXECUTED, `git log`).
15. **Confirmed.** Decision 1 records the manifest's SHA-256 (`3051e859…`), which matches the hash from round 0 (READ; the hash EXECUTED in round 0).

**Building on a provisional answer to the High.** It is acceptable, on two conditions.
- **§5.6.** It asks for review before a change lands, with each finding "fixed or answered in writing before the landing". It does not forbid building while a finding waits on the owner, and the owner asked for the work to go on. The answer is due at the landing, and the specification puts it there (READ, INFERRED).
- **§4.1 and §7.** They govern what is carried and shipped, and a patch on a draft branch that cannot merge ships nothing. The default is still not an answer: silence is not the owner's yes, and the specification says so (READ).
- **The cost if the owner declines.** It is small. The pipeline, PyO3 and `_rust_probe` survive; only orjson's patch and its notice change (INFERRED).
- **Condition (i): a mechanical block, not prose alone.**
  - The pull request stays a draft, and its description names both questions.
  - The post-build review gives no verdict that begins "Lands" until `decisions.md` records both answers.
- **Condition (ii): §4.12 corrected first.** Correct the text named in finding 7 before anything else, so that nothing on the branch claims an approval the owner has not given.

## Verdict
May be built on the draft branch once §4.12 stops naming yyjson as approved, and lands only after `decisions.md` records the owner's answers on the orjson patch (High) and on yyjson and core's Unicode tables (Medium 7(a)(b)).
