# x86_64 rebuilds differ in one function

- **Status:** executed, 2026-10-17. Written when spec 012 took Decision 8's fallback. Traced further on 2026-10-18 by spec 040's build (the addendum below); finding 7's register-allocation explanation is superseded there.
- **Owner:** Clay Gendron
- **Researcher:** the implementer of spec 012 (Claude Opus 5.5), inside spec 012's build. The box was Decision 8's two attempts.
- **Blocks:** x86_64 Linux in the release workflow's `same-bytes` gate. Spec 012 keeps x86_64 as a pinned build host, but its rebuild is not byte-identical yet.
- **Evidence:** `2026-10-17-the-x86-64-rebuild/`.
  - `Dockerfile` and `run-build.sh` are the container and the whole build.
  - `cmp-numpy.sh`, `recompile.sh` and `wizer-x86.sh` are the narrowing steps.
  - `outputs/` holds each run's lines and hashes.
- **Machine (benchmark facts only):** Apple arm64, macOS 26.5, Docker 29.7.2 (10 CPUs, 8 GB). The x86_64 container ran under Rosetta: `/proc/cpuinfo` says `VirtualApple`.

## The question

Spec 012 makes arm64 macOS and arm64 Linux build the same artifact set. Does x86_64 Linux build it too? If not, what differs, and why?

## Method

1. Build the whole recipe three times, from an empty `downloads/` and `build/`: on macOS in a clone, in the experiment's pinned Debian container on linux/arm64, and in the same container on linux/amd64.
2. Compare the three `build/artifacts/SHA256SUMS` files.
3. Where they differ, find the byte, the function, the object, and the cause.

## Findings

1. **The x86_64 set differs in two files** (EXECUTED: `outputs/sha256sums-macos-vs-x86_64.diff`).
   - macOS and arm64 Linux wrote the same `SHA256SUMS`, byte for byte.
   - x86_64 wrote the same zip, `MANIFEST` and licences.
   - Its `python.wasm` is `36c654782b6cdd4b…`, not `2df569f2f59397d5…`, at the same size of 29,802,418 bytes.
   - Its snapshot follows its reactor: `568b9db75d1686a0…`, not `4130d3baa218ce9b…`.
2. **21 bytes differ, all in one function** (EXECUTED: `outputs/reactor-cmp-macos-vs-x86_64.txt`).
   - They lie at file offsets 0x1610c91 to 0x1610cd1, in the CODE section.
   - The link map puts that range in `npy_cpowl`. That is numpy's long-double complex power, from `libnpymath.a(meson-generated_npy_math_complex.c.o)`.
3. **One object differs, compiled from the same source** (EXECUTED: `outputs/numpy-tree-aarch64-vs-x86_64.txt`).
   - The two Linux builds' numpy trees hold equal generated `.c` and `.h` files.
   - Of their objects, only `meson-generated_npy_math_complex.c.o` differs.
   - Its source, `npy_math_complex.c`, is equal on both hosts.
4. **The difference is the stack layout** (EXECUTED: `outputs/npy_cpowl-aarch64-vs-x86_64.diff`).
   - Two 16-byte spill slots trade places: frame offsets 112 and 160.
   - The instructions, their count and the function's size are the same.
5. **Each host's compiler is deterministic, and the two disagree** (EXECUTED: `outputs/recompile.txt`).
   - The build's own compile command, from meson's `compile_commands.json`, was run three times on each host.
   - aarch64 wrote `20ef33440bb2e944…` each time, as its build had.
   - x86_64 wrote `d36897438056e356…` each time, as its build had.
   - So the cause is the host's clang binary, given the same input and the same flags. It is not chance.
6. **NaN canonicalization is not needed, and changes nothing** (EXECUTED: `outputs/wizer-x86_64.txt`). This was Decision 8's first attempt.
   - x86_64's `wasmtime wizer` was run with step 80's flags on macOS's reactor and zip.
   - It wrote macOS's snapshot, `4130d3baa218ce9b…` (63,489,079 bytes).
   - It wrote the same bytes again with `-W nan-canonicalization=y` added.
   - So the snapshot step is host-independent on x86_64 (under Rosetta). The whole difference is the reactor's one function.
7. **Why one function** (INFERRED, not traced). *Superseded in part by the addendum: the choice is made in instruction selection, before register allocation, so the spill-weight explanation below is ruled out.*
   - The same LLVM 22 source, built per host, chose differently between two equal-cost stack-slot assignments.
   - A heuristic computed in floating point on the host is a likely source. Register allocation's spill weights are floats, and a compiler built for aarch64 may contract them with FMA where an x86_64 build does not.
   - Rosetta was the x86_64 CPU here. The GitHub `ubuntu-24.04` runner is expected to give the same bytes, because Rosetta reproduces x86 results (INFERRED). No real x86_64 machine ran it.

## What it decides

- x86_64 Linux stays a pinned build host. Its key, pins and download branch stay, and it builds.
- Its rebuild is not byte-identical, so it is not in the release workflow's `same-bytes` gate. The gate's matrix is `ubuntu-24.04-arm` only.
- The recipe has no fix inside spec 012. The difference is in the host's compiler binary, which wasi-sdk publishes per host and which no flag in the recipe is known to steer.

## Where it stopped

- No compiler flag was tried. A flag that hides this one tie would not show that the next numpy or pandas release has none.
- The same fact rules out the tempting per-file workaround: compiling `npy_math_complex.c` differently on one host.
- A fix needs one of three things, each a specification of its own:
  - a compiler binary that gives the same output on every host;
  - an x86_64 build that runs aarch64's compiler under emulation;
  - an upstream LLVM fix, once the tie is traced to its source.
- Not run: the x86_64 build on a real x86_64 machine, and the `ubuntu-24.04` runner.

## Traced further (spec 040), 2026-10-18

Spec 040's builder re-ran its Decision 1 from this folder (`decision1-host.sh`, `decision1-sweep.sh`, `decision1-x86_64.sh`; outputs in `outputs/decision1/`). The machine is the one above. All EXECUTED.

1. **One file reproduces it.** numpy's `npy_math_complex.c`, preprocessed with the build's own command (`-E -P`, 324,353 bytes, `2193b9bd4d40aadc`), compiled with the build's code-generation flags: the arm64 macOS SDK gives `20ef33440bb2e944`, the build's own object; the x86_64 Linux SDK, native in the `linux/amd64` container, gives `d36897438056e356`, the x86_64 build's object.
2. **The IR is equal; instruction selection differs.** `-print-after-all` for `npy_cpowl` prints 65,227 lines on each host. Apart from three header lines spelling a template name differently, the first difference is the dump after "WebAssembly Instruction Selection (wasm-isel)": two `__multf3` result slots are numbered in swapped order (`outputs/decision1/passes-first-differences.diff`).
3. **The scheduler is not a lever.** Each of the seven `-pre-RA-sched` choices gives different objects on the two hosts (`outputs/decision1/*/sched.txt`).
4. So finding 7's register-allocation explanation is ruled out. Why instruction selection orders the slots differently per host build is not traced (INFERRED: the release binaries have no `-debug-only`).
5. **The aarch64 compiler, emulated on x86_64, gives the aarch64 bytes.** After the recipe's own step 10 puts the arm64 Linux SDK's clang under the pinned `qemu-aarch64` behind `$SDK/bin/clang`, the same sweep through it gives macOS's object and macOS's hash for every scheduler choice (`outputs/decision1/linux-x86_64-emulated/`). Its pass print equals macOS's but for the same three header lines (`outputs/decision1/passes-macos-vs-emulated.diff`): that spelling follows the system each clang was built on (both Linux builds spell it alike), not the CPU, and it is not in any object.
6. **A nine-line reproducer** (`../upstream/4-llvm-wasm-isel-slot-order/evidence/slot-order.c`): a loop carrying a complex multiply in two `long double`s. The arm64 macOS and arm64 Linux SDKs give `9afcef294ca52dad`, the x86_64 Linux SDK `7daeec0794b49c01`, again first differing at `wasm-isel`'s `__multf3` slots. The LLVM issue is drafted there.
7. **The fix.** Spec 040 compiles on x86_64 with the aarch64 clang under qemu. Its three-host build and the numbers are in the spec's landing notes.

## One line

x86_64 Linux builds the same zip, `MANIFEST` and licences, and its Wizer step is host-independent. But its wasi-sdk clang lays out one numpy function's stack differently. So its reactor differs by 21 bytes, and x86_64 stays a pinned build host outside the same-bytes gate.
