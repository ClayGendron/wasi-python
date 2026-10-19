# LLVM: the WebAssembly backend orders try_table blocks differently from run to run (facts for the owner)

- **Project:** LLVM (https://github.com/llvm/llvm-project), the WebAssembly backend, as wasi-sdk 33
  ships it (clang 22.1.0, LLVM `4434dabb`)
- **State:** fixed upstream; nothing to send. LLVM `fd76c9bd` (pull request #205184, issue
  #204883) replaced the `DenseMap` keyed by block pointers in `WebAssemblyCFGStackify.cpp`
  (`fixCallUnwindMismatches`, line 1829, and three more) with a `MapVector`; the fix is in
  wasi-sdk 34 (LLVM 23.1.0) and in no 22.x release (main's
  `context/research/2026-10-19-the-try-table-order-in-llvm.md`). Spec 037 carries a narrow
  exception until the toolchain move to wasi-sdk 34 (Decision 17). The facts below stay as
  the record of what was seen.

## What happens

scipy 1.18.1's `scipy/fft/_duccfft/pyduccfft.cxx` (ducc0's FFT, heavy C++ templates), compiled
for `wasm32-wasip1` with standard exception handling (`-fwasm-exceptions -mllvm
-wasm-use-legacy-eh=false -fexceptions`) at `-O3`, gives a different object file on every run of
the same command on the same machine (EXECUTED 2026-10-19, macOS arm64: eight compiles, eight
SHA-256s; the same at `-O2` and `-O1`; at `-Os` eight compiles give one object, but that object's
module crashes at import in the guest, so `-Os` is no workaround). The optimized IR is the same on
every run; compiling that IR alone to an object differs from run to run, so it is the backend. The
disassemblies differ only in the nesting order of `try_table (catch_all_ref …)` blocks in eight
functions, `ducc0::detail_fft::cfftpass<T>::make_pass`, `rfftpass<T>::make_pass` and two
`make_shared` instantiations, each a function with several `make_shared` calls whose cleanups
need landing pads: one run opens the outer `try_table` first, another the inner. The code is
correct either way (scipy's FFT golden matches native on both); it is not reproducible. INFERRED:
an iteration over pointer-keyed containers when the backend places `try_table` markers
(WebAssemblyCFGStackify), which address-space randomization reorders.

## Reproducing

The file and its flags are in spec 037's build (`build/scipy-build/compile_commands.json`, the entry
for `pyduccfft.cxx`). Compile it twice and compare; `llvm-objdump -d` of the two shows the
reordered blocks. A reduced test case is the owner's or a later agent's work, when asked.
