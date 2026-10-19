# LLVM: the WebAssembly backend orders try_table blocks differently from run to run (already fixed upstream; nothing to send)

- **Project:** LLVM (https://github.com/llvm/llvm-project), the WebAssembly backend, as wasi-sdk 33
  ships it (clang 22.1.0, LLVM `4434dabb`, the `llvmorg-22.1.0` tag)
- **State:** **do not file.** The bug is already reported as llvm/llvm-project#204883 and fixed by
  #205184 (`fd76c9bdf10383ae536d8c504dafe3bd91947d83`, 2026-06-27). The fix is in LLVM 23.1.0 and
  later and in wasi-sdk 34. No `release/22.x` build has it, and 22.1.8 (2026-06-16) was the last
  22.x release. This file keeps the facts and a reproducer smaller than the one upstream used
  (`try-table-order.ll`, next to this file), in case the owner wants to comment on the closed issue
  or the PR. The research is in
  `context/research/2026-10-19-the-try-table-order-in-llvm.md`. LLVM's AI Tool Use Policy keeps
  agents from posting, so any comment is the owner's to write and send.

## What happens

scipy 1.18.1's `scipy/fft/_duccfft/pyduccfft.cxx` (ducc0's FFT) is compiled for `wasm32-wasip1`
with standard exception handling (`-fwasm-exceptions -mllvm -wasm-use-legacy-eh=false
-fexceptions`, `-O3`). It gives a different object file on every run of the same command on the
same machine. The optimized IR is the same every time, and code generation from that IR alone
still differs. The disassemblies differ only in how `try_table (catch_all_ref …)` blocks nest in
six to eight functions. The code is correct either way. It just is not reproducible.

## Cause

`llvm/lib/Target/WebAssembly/WebAssemblyCFGStackify.cpp` at `4434dabb`:

- line 1829: `fixCallUnwindMismatches` declares
  `DenseMap<MachineBasicBlock *, SmallVector<TryRange, 4>> UnwindDestToTryRanges`;
- line 1972: it iterates that map and calls `addNestedTryTable` for each range.

When two ranges with different unwind destinations cover the same instructions, the one wrapped
first ends up inner. So the nesting follows the map's iteration order. That order follows the
blocks' heap addresses, which address-space randomization changes on every run. #205184 replaces
this map, plus `EHPadToUnwindDest` (same file), `EHPadToRethrows` (`WebAssemblyLateEHPrepare.cpp`)
and `UnwindDestToNewPreds` (`WebAssemblyLowerEmscriptenEHSjLj.cpp`), with `MapVector`s.

## Reproducer

`try-table-order.ll`: one function, three invokes, two cleanup pads, 30 lines of IR. It came from
`llvm-reduce` on one ducc0 function (`make_shared<cfftpg<double>>`) and was then cleaned by hand.

```
llc -O3 -mtriple=wasm32-unknown-wasip1 -exception-model=wasm -mattr=+exception-handling \
    -wasm-enable-eh -wasm-use-legacy-eh=false -filetype=obj try-table-order.ll -o - | shasum -a 256
```

Run it 32 times and count the distinct hashes.

| Toolchain | Runs | Distinct objects |
|---|---|---|
| LLVM 22.1.0 release `llc` (macOS arm64), `-O3` | 32 | 2 (7 / 25) |
| same, `-O2` / `-O1` / `-O0` | 32 each | 2 / 2 / 1 |
| wasi-sdk 33 clang 22.1.0 (`-c` on the `.ll`, `-Xclang -disable-llvm-passes`) | 64 | 2 (14 / 50) |
| wasi-sdk 34 clang 23.1.0 (LLVM `895aa2c8`, contains `fd76c9bd`), same command | 64 | 1 |

On the full ducc0 translation unit, wasi-sdk 33 gave 4 objects in 4 runs. wasi-sdk 34 gave 1
object in 16 runs from source, and 1 in 16 from the IR.

The upstream test that #205184 adds (`nested_cleanup_unwind_to_caller`) also splits on 22.1.0
(6 / 26 in 32 runs), but only under its `-wasm-disable-ehpad-sort` RUN line. This reproducer
splits under the default `-O1` to `-O3` pipelines.

Tested 2026-10-19 on macOS arm64 (Darwin 25.5).
