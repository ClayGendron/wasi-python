
## cfg-route.sh (spec 059, 2026-10-18)

Spec 059 puts `-ffp-contract=off` into the toolchain's own `bin/clang.cfg` and `bin/clang++.cfg` (step 10), so every compile carries it. `cfg-route.sh` reproduces the facts behind that route on scratch copies of the two pinned SDKs: which configuration file each driver reads, the `-cc1` lines, no warning under `-Werror`, the predefined macros unchanged, the override family's effect (the pre-build review's F1), the constant-fold case (F2), the pragma case (F5), and the numpy object through the edited files on both hosts. Its outputs are text under `outputs/cfg-route/`; no object is committed. The earlier files here (`sweep.sh`, `sweep-numpy.sh`, their outputs) are the memo's own experiments, which found the flag.
