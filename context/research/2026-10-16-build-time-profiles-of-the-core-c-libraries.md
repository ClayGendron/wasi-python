# Build-time profiles of the core C libraries

- **Status:** placeholder (research to do), 2026-10-16
- **Owner:** Clay Gendron
- **Decided already** (the owner, 2026-10-16; constitution §2, "Beyond v1"): profiles come after v1, and they select the core C libraries at build time. The product is a drop-in sealed Python for lightweight loads, not a development environment (constitution §3).
- **Blocks:** the first specification for profiles; nothing in v1.
- **Partly answered** by `2026-10-26-choosing-packages-profiles-and-the-import-path.md` (its sections 3 and 6: the share of each package in the released binary and zip, the dependency lattice the profiles would follow, and what the wheel and the judge would need); items 2 and 3 below (a profile built and measured, the judge across sets) still wait on the experiment.

## The question

How should `scripts/build.sh` produce more than one artifact set, each carrying only some of the C libraries, so that an embedder with a lightweight load does not carry numpy and pandas? Which profiles are worth building, judging and publishing?

## What is known (EXECUTED, the build of spec 003, 2026-10-16)

- C extensions cannot be added at run time on `wasm32-wasip1` (no `dlopen`), so selection happens when the binary is linked. A runtime switch that only refuses imports saves no size.
- numpy and pandas are about 40% of the code in `python.wasm` (pandas 25%, numpy 15%, by the reactor's link map) and about half of the compressed stdlib zip (pandas 3.6 MB, numpy 1.5 MB of 10.5 MB). Most of the snapshot's 62 MB, against the plain reactor's 30 MB, is the memory their import leaves.
- Pure-Python libraries need no rebuild: they could be added at run time as extra zips on `sys.path`, outside any profile.

## What answers it

1. A profile file format (packages, pre-imports, name) and how `scripts/build.sh` takes one; how `MANIFEST` names the profile.
2. A CPython-only profile built and measured: sizes, snapshot size, start-up fuel against the data profile.
3. How the harness judges several sets (a profile dimension on the scoreboard and the ratchet).
4. How the runner and the wheel choose a profile (`run(..., profile=)`), and whether one wheel carries several sets or each profile is its own wheel.
5. Whether run-time extra zips for pure-Python libraries belong with profiles or in their own specification.

## What it decides

The profiles the first post-v1 release ships, and the specification that builds them.
