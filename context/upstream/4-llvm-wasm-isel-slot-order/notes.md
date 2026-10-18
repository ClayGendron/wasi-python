# Notes: the wasm-isel slot order (spec 040, Decision 9)

How the issue in `issue.md` was found and checked. Each claim is EXECUTED unless labelled.

## Found

- Spec 012's x86_64 build gave a `python.wasm` 21 bytes away from the arm64 hosts', all in numpy's
  `npy_cpowl` (`../../research/2026-10-17-x86-64-rebuilds-differ-in-one-function.md`).
- Spec 040, Decision 1 traced it to instruction selection: equal IR on both hosts, the first content
  difference in the `wasm-isel` dump, no `-pre-RA-sched` choice that makes the hosts agree. The
  scripts and outputs are in `../../research/2026-10-17-the-x86-64-rebuild/` (`decision1-*.sh`,
  `outputs/decision1/`).

## Reduced

- By hand, from numpy's preprocessed `npy_math_complex.c` (324,353 bytes) to `evidence/slot-order.c`
  (nine lines), within the one-hour box (`evidence/reduction.txt`: each cut, and whether the two
  hosts' objects still differ).
- Complex arithmetic is not needed: a loop carrying a complex multiply in two `long double`s is
  enough. Straight-line code with the same multiplies (`r10` to `r13`) and loops with fewer
  multiplies (`r15`, `r17`) give equal objects.
- The compiles: `evidence/compare-two-hosts.sh`. aarch64 is the arm64 macOS SDK on the Mac; x86_64
  is the x86_64 Linux SDK in a `linux/amd64` `debian:trixie-slim` container under Rosetta. The arm64
  Linux SDK in a `linux/arm64` container gives the macOS SDK's object, `9afcef294ca52dad`, and so
  does the same SDK under the pinned `qemu-aarch64` in the `linux/amd64` container (step 10's
  layout, inside spec 040's x86_64 build).
- `evidence/slot-order-objdump-aarch64-vs-x86_64.diff`: only frame offsets differ.
- `evidence/slot-order-passes-first-differences.diff`: the head of the `-print-after-all` diff
  (18,374 lines on each host): three template-name spellings, then `wasm-isel`'s `__multf3` slots.

## Not done

- The cause inside the SelectionDAG is not traced; the release binaries have no `-debug-only`
  (INFERRED from the build type, as Decision 1 says). `issue.md` offers a guess, labelled as one.
- The x86_64 compiles ran under Rosetta, not on an x86_64 machine. The release workflow's
  `ubuntu-24.04` runner is the first real x86_64 machine to run this build (spec 040, dry run 2).

## When it leaves

When the line moves to a new wasi-sdk, compile `evidence/slot-order.c` and the numpy file with that
SDK's x86_64 and aarch64 compilers, natively. If the objects are equal, run one native x86_64
rebuild in the research container; if its set equals the others, the same change removes the
launcher, the five pins, the emulation names and step 10's x86_64 branch (spec 040, Decision 9).
