# OpenBLAS: build for wasm32-wasip1 with make variables alone (a courtesy pull request)

- **Project:** OpenBLAS (https://github.com/OpenMathLib/OpenBLAS)
- **Against:** `develop` (read at `5137bb62`, 2026-10-18); the same lines are in 0.3.34
- **State:** drafted for the owner to send; nothing is carried for it (spec 037, Decision 5)
- **Policy, as read:** OpenBLAS's repository holds no contributor guide and no rule on
  AI-written changes that the agent could find (READ, 2026-10-19: the `develop` tree's top folder
  and `docs/`). The owner decides how to present it; a disclosure that an agent drafted it is
  the honest default.

## What builds today, and what it needs

wasi_python builds OpenBLAS 0.3.34 for `wasm32-wasip1` (wasi-sdk 33, `TARGET=WASM128_GENERIC`,
`NOFORTRAN=1`, `C_LAPACK=1`, no threads) with no source change, by five outside fixes on the make
line (`scripts/steps/38_openblas.sh`):

1. `ARCH=wasm` and `-DARCH_WASM`: OpenBLAS knows wasm only through `__EMSCRIPTEN__`
   (`ctest.c:180`), so on WASI it detects no architecture.
2. `-D_WASI_EMULATED_MMAN` (and `-lwasi-emulated-mman` at the final link): its buffer is mapped.
3. `-DNO_SYSV_IPC`: WASI has no System V shared memory.
4. `-include sched.h`: `common.h` includes `<sched.h>` for `sched_yield` only on platforms it
   names.
5. An empty `<sys/ipc.h>` on the include path: `driver/others/memory.c:148` includes it outside
   the `NO_SYSV_IPC` guard that holds `<sys/shm.h>` (lines 145-147), and wasi-libc has none.

## The change

- `ctest.c`: test `__wasi__` beside `__EMSCRIPTEN__`, so `ARCH=wasm` comes from detection.
- `common.h`: include `<sched.h>` for WASI as for the other POSIX platforms.
- `driver/others/memory.c`: move `#include <sys/ipc.h>` inside the existing `#ifndef NO_SYSV_IPC`.
- `Makefile.system` (optional): on `OSNAME=WASI`, add `-D_WASI_EMULATED_MMAN -DNO_SYSV_IPC`.

Then a WASI build is `make TARGET=WASM128_GENERIC NOFORTRAN=1 ...` with no CFLAGS of its own.

## How it was checked

The five fixes are what step 38 uses (EXECUTED: the build, its seven warning classes, and the
link-whole gate at 0 signature mismatches with the carried void patches; spec 037's landing
notes). The source change itself was not built; the owner, or the agent when asked, builds it on
`develop` before sending.
