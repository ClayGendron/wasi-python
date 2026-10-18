# LLVM issue: wasm32 instruction selection orders `fp128` libcall result slots differently on x86_64 and aarch64 hosts

- **Project:** LLVM (https://github.com/llvm/llvm-project), issue tracker; wasi-sdk
  (https://github.com/WebAssembly/wasi-sdk) builds the per-host binaries and may want a link.
- **Against:** wasi-sdk 33 (`clang version 22.1.0-wasi-sdk`, llvm-project `4434dabb6991`), the
  release binaries `wasi-sdk-33.0-x86_64-linux`, `wasi-sdk-33.0-arm64-linux` and
  `wasi-sdk-33.0-arm64-macos`.
- **Status:** drafted.
- **Labels to suggest:** `backend:WebAssembly`.
- **Why we file it:** wasi_python builds one `python.wasm` from pinned sources and requires the same
  bytes from every build host. The x86_64 compiler gives different bytes for one numpy function,
  so the x86_64 host compiles with the aarch64 compiler under qemu until this is fixed (spec 040).

**AI policy.** LLVM's AI Tool Use Policy (https://llvm.org/docs/AIToolPolicy.html, read
2026-10-18) lets contributors use tools, requires a human to read and review all generated text
before asking others to review it, asks that substantially tool-generated content be labelled, and
bans agents acting in LLVM's spaces without human approval. So the owner reads this text, checks the
reproducer, posts it himself, and keeps the disclosure line at its end. The text below is written to
be posted as is once he has.

---

## Title

[WebAssembly] Host-dependent stack slot order for fp128 libcall results in wasm-isel (x86_64 vs aarch64 builds of clang)

## Body

The same clang release, built for two hosts, gives different wasm32 objects for the same input and
the same flags. Each binary is deterministic on its own host; they disagree with each other. The
difference first appears in the output of WebAssembly Instruction Selection: the stack slots that
receive the 16-byte results of `__multf3` (wasm32's `long double` is `fp128`) are numbered in a
different order. Every later pass carries the swap, so the final object has the same instructions
and size with different frame offsets.

We found it in numpy 2.5.2's `npy_cpowl` while checking that our build gives the same bytes on
x86_64 Linux, aarch64 Linux and aarch64 macOS. The aarch64 Linux and aarch64 macOS binaries agree;
the x86_64 Linux binary does not.

### Reproducer

`slot-order.c`:

```c
long double f(long double a, long double b, int n) {
  long double x = 1, y = 0;
  while (n--) {
    long double t = x*a - y*b;
    y = x*b + y*a;
    x = t;
  }
  return x + y;
}
```

```
clang --target=wasm32-wasip1 -std=c11 -O3 -fno-strict-aliasing -ftrapping-math -fvisibility=hidden -w -c slot-order.c -o slot-order.o
```

| clang binary (wasi-sdk 33) | host | `sha256sum slot-order.o` (first 16) |
|---|---|---|
| `wasi-sdk-33.0-arm64-macos` | macOS 26.5, Apple arm64 | `9afcef294ca52dad` |
| `wasi-sdk-33.0-arm64-linux` | Debian 13, aarch64 (linux/arm64 container) | `9afcef294ca52dad` |
| `wasi-sdk-33.0-x86_64-linux` | Debian 13, x86_64 (linux/amd64 container on Apple silicon) | `7daeec0794b49c01` |
| `wasi-sdk-33.0-arm64-linux`, under `qemu-aarch64` 10.0.13 (user mode) | Debian 13, x86_64 (the same container) | `9afcef294ca52dad` |

Both compiles see the same relative file name (it is recorded in the object). Repeated compiles on
each host give the same hash.

`llvm-objdump -d` differs only in frame offsets, for example:

```
<      125: 41 b0 01     	i32.const	176
>      125: 41 a0 01     	i32.const	160
<      13f: 29 03 b0 01  	i64.load	176
>      13f: 29 03 a0 01  	i64.load	160
```

### Where it starts

With `-mllvm -print-after-all`, both hosts print 18,374 lines. Every IR pass prints the same
function. Apart from three header lines where the two builds spell a template name differently
(`RequireAnalysisPass<llvm::GlobalsAA, llvm::Module, llvm::AnalysisManager<Module>>` against
`RequireAnalysisPass<llvm::GlobalsAA, llvm::Module>`), the first difference is in the dump after
`WebAssembly Instruction Selection (wasm-isel)`:

```
aarch64:  CALL_PARAMS &__multf3, %stack.5, %19:i64, %20:i64, %35:i64, %36:i64, ...
x86_64:   CALL_PARAMS &__multf3, %stack.6, %19:i64, %20:i64, %35:i64, %36:i64, ...
...
aarch64:  CALL_PARAMS &__multf3, %stack.8, %35:i64, %36:i64, %17:i64, %18:i64, ...
x86_64:   CALL_PARAMS &__multf3, %stack.5, %35:i64, %36:i64, %17:i64, %18:i64, ...
```

The same `__multf3` result slots trade numbers, so the frame layout that follows differs.

On the original numpy function, the seven `-mllvm -pre-RA-sched` choices (`default`, `source`,
`list-burr`, `list-hybrid`, `list-ilp`, `linearize`, `fast`) each still give different objects on
the two hosts, so the order seems to be decided inside instruction selection, not by the
pre-register-allocation scheduler. We did not trace it further: the release binaries have no
`-debug-only`.

### What we would expect

The same object from every host build of the same clang. A guess, not verified: something in the
SelectionDAG lowering of the libcall results (the order in which the result `FrameIndex`es are
created) depends on an ordering that is not stable across host builds, such as iteration over a
pointer-keyed container, or a floating-point heuristic compiled differently for each host.

### Running the aarch64 compiler on x86_64

The `wasi-sdk-33.0-arm64-linux` clang, run on the x86_64 machine under `qemu-aarch64` 10.0.13
(user mode), gives the aarch64 bytes, for the reproducer (the table's last row) and for the numpy
file. So the difference is in the x86_64 build of clang, not in the machine it runs on. That is our
workaround until this is fixed.

---

*This report was prepared with an AI tool (Claude) and reviewed by the person posting it, who ran
the reproducer.*
