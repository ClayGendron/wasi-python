# The try_table order in LLVM: a DenseMap in CFGStackify, fixed in LLVM 23 and wasi-sdk 34

- **Status:** draft, 2026-10-19. The parallel half of question 104's answer (`context/decisions.md`, "104, answered"). The culprit is found, an upstream fix exists, and a released toolchain carries it. What stays open is the pin move itself (its own specification), named at the end.
- **Owner:** Clay Gendron
- **Researcher:** a research agent (Claude Opus 5.5), outside every git tree. Evidence is under the session scratch folder `ducc0-llvm/` (`full.ll`, `red/`, `runs*/`, `src33/`, `src34/`, `src/`). The lane committed this memo, and the issue draft and reproducer beside it in `2026-10-19-the-try-table-order-in-llvm/` (spec 037's branch holds its own `context/upstream/23-llvm-wasm-try-table-order/`).
- **Follows:** `context/research/2026-10-19-ducc0-is-not-reproducible-with-the-pinned-clang.md` (spec 037's branch). That memo found the symptom. This one finds the cause and the fix.

## The question

wasi-sdk 33's clang (22.1.0, LLVM `4434dabb`) compiles scipy's `pyduccfft.cxx` to a different object on every run. The objects differ only in how `try_table (catch_all_ref …)` blocks nest in eight ducc0 functions. What in the backend does this? Is it fixed upstream? Does a released toolchain carry the fix, so that a later spec can move the pin and drop spec 037's same-bytes exception?

Short answer: a `DenseMap` keyed by basic-block pointers in `WebAssemblyCFGStackify.cpp`. Its iteration order follows heap addresses, and address-space randomization changes those addresses on every run. LLVM fixed it on 2026-06-27 (`fd76c9bdf103`, PR #205184, issue #204883). The fix is in LLVM 23.1.0 and later and in wasi-sdk 34. No 22.x release has it.

## Findings

1. **It reproduces from the one IR file, in the backend alone** (EXECUTED). The optimized IR (`full.ll`, 241,059 lines, 1,846 functions, SHA-256 `303a6f5d…`) is compiled with wasi-sdk 33's clang, spec 037's flags and `-Xclang -disable-llvm-passes` (no middle end, only code generation). Four runs gave four objects. Without `-disable-llvm-passes`, four runs also gave four objects. LLVM 22.1.0's release `llc` (the same commit, `4434dabb`, is the `llvmorg-22.1.0` tag) gives four objects in four runs too. Across runs, between six and eight functions differ: the six `cfftpass<T>::make_pass` and `rfftpass<T>::make_pass` instantiations, and sometimes also the two `make_shared<cfftpg<T>>` instantiations.

2. **The reduced reproducer is one function, 30 lines of IR** (EXECUTED). `llvm-extract` of `make_shared<cfftpg<double>>` gives 478 lines. That file still splits about 50/50 between two objects (17 and 15 of 32 runs). `llvm-reduce` (LLVM 22.1.0), whose test was "24 `llc` runs give at least two objects", cut it to 50 lines in 5 minutes. A hand clean-up gives `upstream/23-llvm-wasm-try-table-order/try-table-order.ll`: 43 lines with comments, 30 without, SHA-256 `63a709ec…`. It has three invokes. Two of them unwind to `cleanup1`, which unwinds to `cleanup2`, which unwinds to the caller. It needs only the stock flags (`llc -O3 -mtriple=wasm32-unknown-wasip1 -exception-model=wasm -mattr=+exception-handling -wasm-enable-eh -wasm-use-legacy-eh=false`). `-wasm-enable-sjlj` is not needed.
   - `llc` 22.1.0, 32 runs: two objects at `-O3` (7/25), with sjlj (8/24), at `-O2` (1/31) and at `-O1` (9/23). At `-O0` it gives one object.
   - wasi-sdk 33's clang (`-c` on the `.ll`, `-Xclang -disable-llvm-passes`), 64 runs: the same two objects (14/50).
   - The two assemblies differ in one basic block, `%throw`. In one, the `__cxa_allocate_exception` call sits inside two nested `try_table`s: an outer one to the `cleanup2` pad and an inner one to the rethrow-to-caller block. In the other, each call has its own `try_table`, one after the other. Both are correct code. They just aren't the same bytes.

3. **The culprit is `UnwindDestToTryRanges` in `fixCallUnwindMismatches`** (READ, at `4434dabb`). File: `llvm/lib/Target/WebAssembly/WebAssemblyCFGStackify.cpp`.
   - Line 1829: `DenseMap<MachineBasicBlock *, SmallVector<TryRange, 4>> UnwindDestToTryRanges;`.
   - Lines 1877 and 1898 fill it. The key is the unwind destination's block pointer, or the "fake caller block" for calls that unwind to the caller.
   - Line 1972: `for (auto &P : UnwindDestToTryRanges)` calls `addNestedTryTable` for each range. When two ranges with different unwind destinations cover the same instructions, the range wrapped first becomes the inner `try_table`. So iteration order decides how the blocks nest. A `DenseMap` iterates in the order of its pointer keys' hashes, which follows the heap addresses, which follow address-space randomization.
   - The same pattern appears in three more places, all fixed by the same commit: `EHPadToUnwindDest` (line 2134, iterated at 2204 and 2217, in `fixCatchUnwindMismatches`), `EHPadToRethrows` (`WebAssemblyLateEHPrepare.cpp:301`, iterated at 313), and `UnwindDestToNewPreds` (`WebAssemblyLowerEmscriptenEHSjLj.cpp:1724`, iterated at 1801 and 1815).
   - This matches finding 2: the reduced case has two unwind destinations (`cleanup2` and the caller) whose ranges meet in one block.

4. **Upstream fixed it on 2026-06-27** (READ). The commit is `fd76c9bdf10383ae536d8c504dafe3bd91947d83`, "[WebAssembly] Fix nondeterminism by using MapVector for pointer-keyed maps [NFC]" (PR #205184, by Derek Schuff with Ammar Askar). It changes the four maps above to `MapVector`, which keeps insertion order. It adds a test, `nested_cleanup_unwind_to_caller`, to `test/CodeGen/WebAssembly/cfg-stackify-eh.ll`. It fixes issue #204883, opened 2026-06 by another user whose binaryen builds drifted in the same `try_table (catch_all_ref …)` pattern.
   - EXECUTED: that upstream test, run with its NOSORT flags (`-wasm-disable-ehpad-sort`) on `llc` 22.1.0, gives two outputs in 32 runs (6/26). With the default sort it gives one. Our reproducer splits under default flags, so it is the stronger test.
   - READ (GitHub compare API): `fd76c9bd` is an ancestor of `895aa2c8` (wasi-sdk 34's LLVM), of `llvmorg-23.1.0` and of `llvmorg-23.1.3`. It is not an ancestor of `llvmorg-22.1.8`, and no commit on `release/22.x` touching `lib/Target/WebAssembly` after 2026-06-15 picks it up. 22.1.8 (2026-06-16) came out before the fix, and 22.x has had no release since. So **no 22.x toolchain will carry it**.

5. **wasi-sdk 34 is deterministic on every test we have** (EXECUTED). wasi-sdk 34 is clang 23.1.0, LLVM `895aa2c8`, wasi-libc `2e6fb9d8`. We downloaded `wasi-sdk-34.0-arm64-macos.tar.gz` (SHA-256 `9c59398106b417f8f14913380fdf0097a8cc0ff4af9eb3ce0065a859e88d49e9`, the same as the release page's digest) and unpacked it under the scratch folder.
   - The reduced reproducer, 64 runs: one object. It is the same bytes as one of wasi-sdk 33's two.
   - The full IR, backend only, 8 runs: one object. Full pipeline, 16 runs: one object.
   - `pyduccfft.cxx` from source, using spec 037's meson command with `-ffp-contract=off` added (what step 10 puts in `clang.cfg`), against spec 037's build tree, 16 runs: one object (`075795e8…`). wasi-sdk 33 on the same command, 4 runs: four objects.

   The fix is not tested in isolation. INFERRED: no released toolchain has LLVM 23 without the fix, so we cannot run an "after 22, before `fd76c9bd`" build. The evidence that `fd76c9bd` is what fixes our case: it touches exactly the iteration that decides the nesting (finding 3), its test reproduces on 22.1.0 (finding 4), and wasi-sdk 34 is deterministic.

6. **What changes with a move to wasi-sdk 34** (EXECUTED where marked, else READ from its release notes and VERSION file).
   - EXECUTED: the predefined macros at `--target=wasm32-wasip1 -fwasm-exceptions` are the same except the version strings and three `*_MIN__` macros. In particular, every `__wasm_*` feature macro is the same. So the default target features did not change, and wasmtime 49 needs nothing new.
   - EXECUTED: the `wasm32-wasip1` sysroot has the same files, `libwasi-emulated-*` included. Only the `llvm-lto/<version>` directory name changes, 22.1.0 → 23.1.0.
   - EXECUTED: clang 23 warns `-Wunused-template` under spec 037's `-Wall` on `pyduccfft.cxx`. clang 22 printed no warnings on the same command. A package that builds with `-Werror` would stop.
   - READ: wasi-sdk 34 removes the `wasm32-wasi` and `wasm32-wasi-threads` targets. The scripts use `--target=wasm32-wasip1`. The remaining `wasm32-wasi` strings in `scripts/` are Python platform tags (`…-wasm32-wasi.so`, `_sysconfigdata__wasi_wasm32-wasi`), not clang targets.
   - READ: the host-neutral sysroot and builtins are now named `wasi-sysroot-34.0.tar.gz` and `libclang_rt-34.0.tar.gz`, with no `+m` suffix (33's VERSION read `33.0+m`). Release-page digests: sysroot `9d813544eeebe38b7b8f2244ed591de46b6db812c6dd1a257ff9f0d2a905a2be`, libclang_rt `eee3e634dcf71aa22b1333391623cf5c9965a637dc428a27b1a858c026c587f1`, arm64-linux `f7e243dff54d60bcc576e94d6166b69f410f2500ae4a9ceef34315be10e77971`, x86_64-linux `b761e3a0721dbae9c09a0059e5fdb2bf917d1b4a8a7b430fb3b5aafb0984b2c4`. None of these four was downloaded here.
   - READ: wasi-libc moves `161b3195` → `2e6fb9d8`, and libc++ and libc++abi move to 23.1.0. The mangled ABI tag (`B9nqe220100` in finding 1's symbols) follows libc++'s version, so every C++ object's symbol names change.

## What would decide it

The cause is known. The fix is released. So the decision is between three routes:

1. **A pin-move specification to wasi-sdk 34** (recommended). It removes the cause rather than working around it. It needs no toolchain patch, which §4.1 does not cover. Every byte of the artifact set changes, so the spec re-verifies:
   - `downloads/SHA256SUMS` and `scripts/00_download.sh`: the three host SDKs, the sysroot and libclang_rt (new names, no `+m`), and the qemu fallback's arm64-linux SDK.
   - `scripts/line.conf`: `WASI_SDK_VERSION`, the six SDK directory names, `WASI_LIBC_COMMIT=2e6fb9d8`, `LLVM_COMMIT=895aa2c8`. Also the licence-notice downloads at the new commits (`scripts/assemble_artifacts.py` names them from the line).
   - Step 10's sysroot overlay and its `clang.cfg` edits (`-ffp-contract=off`) against 34's layout.
   - Every package still configures and compiles: CPython, numpy, pandas, matplotlib and its C libraries, lxml and its XML libraries, regex, scipy. Watch for new clang 23 warnings in any `-Werror` build, and for the libc++ ABI-tag rename against any rename header or recipe that names a mangled symbol.
   - The recorded patches (`recipes/patches/`) still apply, and the rename headers still match wasi-libc `2e6fb9d8`.
   - Reproducibility, the reason for the move: each of the ~910 scipy compiles twice, and numpy's, pandas', matplotlib's, lxml's and regex's (the original memo's finding-2 method). Then the cross-host check (macOS arm64 and linux/arm64, `SHA256SUMS` equal), and spec 059's claim that the x86_64 and aarch64 Linux clangs emit the same bytes with `-ffp-contract=off`.
   - The full judge: the goldens, the behaviour checks, every package's upstream suites (spec 063's shards), and the fuel and byte ratchet. Fuel and bytes will move with a new compiler, so the lane accepts growth with a stated reason. Also the snapshot, and a release dry run on all three systems (Windows included) before any tag.
   - Then delete spec 037's same-bytes exception for ducc0.
2. **Carry a patched wasi-sdk 33** (not recommended). The patch is four one-line container changes (`fd76c9bd`). But it means building LLVM and wasi-sdk ourselves for three hosts, pinning that build, and opening new ground under §4.1 (patches are to sources, not to the toolchain). That costs more than route 1 and fixes less.
3. **Wait** (not needed). There is nothing to wait for. The fix shipped in LLVM 23.1.0 (2026-08-25) and wasi-sdk 34 (2026-08-25). LLVM 22.x will not get it.

One check would make finding 5's inference EXECUTED: build `llc` at `4434dabb` with and without `fd76c9bd` and run the reproducer 64 times each. It is not needed to choose route 1.

The upstream issue drafted under `context/upstream/23-llvm-wasm-try-table-order/` should not be sent. The bug is already reported (#204883) and fixed (#205184). The refined draft records that, with the reproducer, for the owner.

One line: a pointer-keyed `DenseMap` in WebAssemblyCFGStackify (line 1829, iterated at 1972) nests `try_table`s in address order; LLVM fixed it in `fd76c9bd` (23.1.0), wasi-sdk 34 is deterministic on ducc0, and the next step is a pin-move spec to wasi-sdk 34.
