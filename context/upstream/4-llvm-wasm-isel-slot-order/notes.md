# Notes: the wasm-isel slot order (spec 040, Decision 9)

How the issue in `issue.md` was found and checked. Each claim is EXECUTED unless labelled.

## Found

- Spec 012's x86_64 build gave a `python.wasm` 21 bytes away from the arm64 hosts', all in numpy's `npy_cpowl` (`../../research/2026-10-17-x86-64-rebuilds-differ-in-one-function.md`).
- Spec 040, Decision 1 traced it to instruction selection: equal IR on both hosts, the first content difference in the `wasm-isel` dump, no `-pre-RA-sched` choice that makes the hosts agree. The scripts and outputs are in `../../research/2026-10-17-the-x86-64-rebuild/` (`decision1-*.sh`, `outputs/decision1/`).

## Reduced

- By hand, from numpy's preprocessed `npy_math_complex.c` (324,353 bytes) to `evidence/slot-order.c` (nine lines), within the one-hour box (`evidence/reduction.txt`: each cut, and whether the two hosts' objects still differ).
- Complex arithmetic is not needed: a loop carrying a complex multiply in two `long double`s is enough. Straight-line code with the same multiplies (`r10` to `r13`) and loops with fewer multiplies (`r15`, `r17`) give equal objects.
- The compiles: `evidence/compare-two-hosts.sh`. aarch64 is the arm64 macOS SDK on the Mac; x86_64 is the x86_64 Linux SDK in a `linux/amd64` `debian:trixie-slim` container under Rosetta. The arm64 Linux SDK in a `linux/arm64` container gives the macOS SDK's object, `9afcef294ca52dad`, and so does the same SDK under the pinned `qemu-aarch64` in the `linux/amd64` container (step 10's layout, inside spec 040's x86_64 build).
- `evidence/slot-order-objdump-aarch64-vs-x86_64.diff`: only frame offsets differ.
- `evidence/slot-order-passes-linux-first-differences.diff`: the head of the `-print-after-all` diff of the two Linux builds (18,374 lines each): the first difference is `wasm-isel`'s libcall slots, with no header line between. `evidence/slot-order-passes-first-differences.diff` is macOS against x86_64 Linux: three template-name spellings come first there, which follow the system clang was built on (the build review, finding 2).

## Not done

- The cause inside the SelectionDAG is not traced; the release binaries have no `-debug-only` (INFERRED from the build type, as Decision 1 says). `issue.md` offers a guess, labelled as one.
- The x86_64 compiles ran under Rosetta, not on an x86_64 machine. The release workflow's `ubuntu-24.04` runner is the first real x86_64 machine to run this build (spec 040, dry run 2), but it runs the emulated aarch64 clang, never the native x86_64 one. So the native x86_64 difference has not been seen on an x86_64 CPU. Before the issue is posted, the owner runs `evidence/compare-two-hosts.sh` with the x86_64 SDK on a real x86_64 machine (`issue.md`'s preamble; the build review, finding 1).

## Narrowed (spec 059)

- `context/research/2026-10-18-byte-identical-wasm-builds-prior-art.md` (EXECUTED): a flag sweep on `slot-order.c` and on the preprocessed numpy file with both pinned SDKs (the x86_64 one in the research container under Rosetta). Only `-ffp-contract=off` (and `fast`) makes the two hosts agree; the IR under the default holds 78 `llvm.fmuladd` calls that the flag removes; the object's set of call targets is unchanged. The pre-build review of spec 059 added: `-ffp-model=precise` restores the difference; a constant-folded `a*b+c` moves by one rounding under `off` (`0x1p-54` to `0x0p0`); `#pragma STDC FP_CONTRACT ON` brings `fmuladd` back under the flag.
- The research folder's `cfg-route.sh` reproduces the facts through the SDK's configuration file (`bin/clang.cfg`), which is where spec 059 sets the flag for every compile.

## When it leaves

When the line moves to a new wasi-sdk, compile `evidence/slot-order.c` and the numpy file with that SDK's x86_64 and aarch64 compilers, natively, the x86_64 one on a real x86_64 CPU (not the Rosetta container). If the objects are equal, run one native x86_64 rebuild on real x86_64 (the release workflow's `ubuntu-24.04` runner, with the emulation switched off on a dry-run branch); if its set equals the others, the same change removes the launcher, the five pins, the emulation names and step 10's x86_64 branch (spec 040, Decision 9).
