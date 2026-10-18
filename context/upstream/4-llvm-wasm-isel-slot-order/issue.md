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

**Before posting: run it on a real x86_64 CPU.** Every x86_64 object here came from the x86_64
Linux SDK in a `linux/amd64` container on Apple silicon, that is, under Rosetta (spec 040's build
review, finding 1). That the difference is the x86_64 clang's and not Rosetta's is INFERRED, not
shown. So, first, the owner runs `evidence/compare-two-hosts.sh slot-order.c` with the x86_64 SDK on
a real x86_64 Linux machine, and puts that row in the table (replacing the Rosetta row's host
column). If the hash there is not `7daeec0794b49c01`, the issue is not posted and the memo records
why. The disclosure line's "ran the reproducer" is true only after that run.

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
| `wasi-sdk-33.0-x86_64-linux` | Debian 13, x86_64 (linux/amd64 container on Apple silicon, under Rosetta; the real-x86_64 row goes here) | `7daeec0794b49c01` |
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

With `-mllvm -print-after-all`, the two Linux builds (arm64 and x86_64) each print 18,374 lines.
Every IR pass prints the same function, and so does every header line. The first difference is in
the dump after `WebAssembly Instruction Selection (wasm-isel)`:

```
aarch64:  CALL_PARAMS &__multf3, %stack.5, %19:i64, %20:i64, %35:i64, %36:i64, ...
x86_64:   CALL_PARAMS &__multf3, %stack.6, %19:i64, %20:i64, %35:i64, %36:i64, ...
...
aarch64:  CALL_PARAMS &__addtf3, %stack.6, ...
x86_64:   CALL_PARAMS &__addtf3, %stack.7, ...
...
aarch64:  CALL_PARAMS &__multf3, %stack.8, %35:i64, %36:i64, %17:i64, %18:i64, ...
x86_64:   CALL_PARAMS &__multf3, %stack.5, %35:i64, %36:i64, %17:i64, %18:i64, ...
```

The same libcall result slots are numbered in a different order, so the frame layout that follows
differs. (The macOS build's dump also differs from both Linux builds in three header lines that
spell a template name, `RequireAnalysisPass<…, llvm::AnalysisManager<Module>>` against
`RequireAnalysisPass<…>`. That follows the system clang was built on, not the CPU, and changes no
object.)

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

### Narrowed: the difference needs `llvm.fmuladd` on `fp128`

Clang's default `-ffp-contract=on` emits `llvm.fmuladd` for `a*b+c` in one expression (the numpy
file above holds 78 such calls at `-O3`: 26 each on `f32`, `f64` and `f128`). With
`-ffp-contract=off`, which makes clang emit a plain `fmul` and `fadd`, **the two host builds give
the same object**, for the reproducer and for the whole numpy file; `-ffp-contract=fast` gives that
same object too. With `-ffp-model=precise` (which sets `-ffp-contract=on` again) the old pair comes
back. So the host dependence sits in the lowering of `fmuladd` on `fp128` into the `__multf3` and
`__addtf3` libcalls with their 16-byte result slots. Every other flag tried (`-O1`, `-O2`, `-Os`,
`-Oz`, `-mllvm -enable-misched=0`, `-mllvm -fast-isel`, `-fno-unroll-loops`, `-fno-vectorize
-fno-slp-vectorize`, `-fno-omit-frame-pointer`, each `-mllvm -pre-RA-sched`) still differs between
the hosts. An empty or a 300 KB environment changes neither host's output, so the order does not
move with process addresses: a deterministic difference between the two compiler builds (as in
#99396, where x87 excess precision in a spill weight gave different registers per host), not
pointer-keyed iteration.

| input, `-O3` as above | aarch64 clang | x86_64 clang |
|---|---|---|
| `slot-order.c` | `9afcef294ca52dad` | `7daeec0794b49c01` |
| `slot-order.c` with `-ffp-contract=off` | `bca38dcd95e249c3` | `bca38dcd95e249c3` |
| numpy 2.5.2 `npy_math_complex.c`, preprocessed | `20ef33440bb2e944` | `d36897438056e356` |
| the same with `-ffp-contract=off` (or `fast`) | `2914eb833ad62c93` | `2914eb833ad62c93` |

### Running the aarch64 compiler on x86_64

The `wasi-sdk-33.0-arm64-linux` clang, run on the x86_64 machine under `qemu-aarch64` 10.0.13
(user mode), gives the aarch64 bytes, for the reproducer (the table's last row) and for the numpy
file. So the difference is in the x86_64 build of clang, not in the machine it runs on. We used that
as a workaround first; we now compile everything with `-ffp-contract=off` (in the SDK's `clang.cfg`),
which makes the two host builds agree, and build on x86_64 natively.

---

*This report was prepared with an AI tool (Claude) and reviewed by the person posting it, who ran
the reproducer.*
