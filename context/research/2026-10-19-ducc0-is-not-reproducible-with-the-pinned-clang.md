# scipy's ducc0 does not compile to the same bytes twice with the pinned clang

- **Status:** placeholder, 2026-10-19: the facts below are EXECUTED; the experiment that decides
  the fix is named at the end, and spec 037 waits on it (its acceptance criterion 3).
- **Owner:** Clay Gendron
- **Researcher:** spec 037's builder (Claude Opus 5.5), in the worktree `wasi_python-037`, while
  checking criterion 3 (the same `SHA256SUMS` from macOS arm64 and linux/arm64). Evidence is
  under that worktree's git-ignored `build/037/` (`linux/`, `ducc0/`, the judge logs).
- **Blocks:** spec 037's landing (criterion 3 allows no exception), and with it 038, 043, 044 and
  045, which build on scipy.

## The question

The linux/arm64 rebuild of spec 037's set differed from macOS's. Two causes were host facts and
were fixed in the recipe (step 38's two makes; step 57's git ceiling: spec 037, Revised at build,
items 17 and 18). After them the two `python.wasm` files still differed, in eight functions of
ducc0, scipy.fft's engine. Why, and what makes them equal?

## Findings

1. **The pinned clang is not deterministic on this one file** (EXECUTED). The compile command meson
   records for `scipy/fft/_duccfft/pyduccfft.cxx` (`-O3`, `-fwasm-exceptions -mllvm
   -wasm-use-legacy-eh=false -mllvm -wasm-enable-sjlj -fexceptions`, wasi-sdk 33's clang 22.1.0,
   LLVM `4434dabb`), run eight times at once on one macOS host, gave eight different objects. At
   `-O2` and `-O1`, and without `-wasm-enable-sjlj`, each run differed too. Every macOS build of
   the set today gave a different `python.wasm` (`be8c25cf…`, `2de9ee20…`, `1e944fd7…`, with
   ducc0 the only difference; spec 037's landing notes).
2. **Only this file** (EXECUTED): each of scipy's 910 compiles run twice; only `pyduccfft.cxx`
   differed. numpy's, pandas', matplotlib's, lxml's and regex's compiles have given the same bytes
   on every host since spec 059.
3. **The backend, not the front end** (EXECUTED): the optimized IR (`-S -emit-llvm`) is the same
   bytes on three runs; compiling that one IR file to an object gives four objects in four runs.
   The objects differ only in the nesting order of `try_table (catch_all_ref …)` blocks in eight
   functions (`ducc0::detail_fft::cfftpass<T>::make_pass`, `rfftpass<T>::make_pass` for three
   element types, and two `make_shared` instantiations): one run opens the outer block first, the
   other the inner. INFERRED: the WebAssembly backend's placement of try_table markers
   (CFGStackify) iterates a pointer-keyed container, which address-space randomization reorders.
4. **Backend switches do not help** (EXECUTED, four runs each from the one IR file):
   `-mllvm -disable-block-placement`, `-mllvm -disable-branch-fold`, `-mllvm
   -enable-tail-merge=false`: four objects each.
5. **`-Os` is reproducible but its module crashes** (EXECUTED): eight `-Os` compiles gave one
   object; a set with ducc0 at `-Os` (and everything else unchanged) traps in
   `pybind11_exec_pyduccfft` at import (`pybind11::handle::inc_ref`, out-of-bounds memory), which
   failed 20 checks of the full judge, pandas' own groups that import scipy among them
   (`build/037/ducc0/full-judge-Os.log`). Not investigated further (AGENTS.md rule 7: the second
   failed attempt on "a compile option makes it reproducible"). Spec 037 is back at `-O3`.
6. **The code is right either way**: at `-O3` every set built today passed the scipy goldens and
   behaviour checks, and the full judge at `2687418` was 0 fail.

## What would decide it

One experiment, in this order, each step stopping when it answers:

1. Reduce `pyduccfft.cxx`'s IR to the smallest file that still gives two objects (`llvm-reduce`
   is not in wasi-sdk; a pinned LLVM build of the same commit is, as a research tool), and read
   `WebAssemblyCFGStackify.cpp` at `4434dabb` for the container whose order changes.
2. Check LLVM `main` and the newest wasi-sdk for the same reduced file: if a released wasi-sdk is
   deterministic, the fix is a toolchain pin move (its own specification, re-verifying every
   package's bytes).
3. If no release fixes it: the owner's choice (question 104) between carrying a patched clang
   (§4.1's patches are to sources, so a toolchain patch is new ground), waiting, or a narrower
   rule for this one object.

Meanwhile the issue facts are drafted for the owner (`context/upstream/23-llvm-wasm-try-table-order/issue.md`).
