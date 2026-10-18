# Roadmap

The owner's living plan: what each release contains and the order of work. It changes by the
owner's decision, recorded here with its date; the constitution (`constitution.md`) holds the
mission, the bar every release meets (§2) and the rules, and does not change with this file.
Specifications and research memos carry the detail; this page only orders them.

The runtime is embedder-neutral (constitution §4.5): its consumers are not on this roadmap. A
feature lands because it is general, whoever asked for it first.

## 0.1.0: the first release to rely on

Decided by the owner on 2026-10-17: **matplotlib and scipy are in 0.1.0**, and the default
profile's other packages are to be chosen (below).

### The default profile

| package | state |
|---|---|
| CPython 3.15 with its stdlib, including `sqlite3`, `bz2`, `lzma` | shipped (0.1.0a2) |
| numpy, pandas | shipped (0.1.0a1) |
| matplotlib | M1 specified and confirmed (spec 023); M2 (triangulation, contourpy) next |
| scipy | researched (`research/2026-10-17-what-scipy-needs.md`, the OpenBLAS memo); its licences, SIMD and placement decided (`decisions.md`, 25 to 31) |
| others | to be chosen: `research/2026-10-17-what-else-the-default-profile-carries.md` (in progress) |

### Milestones

1. **An install that just works** (0.1.0a4): the build says where it is (spec 027);
   `pip install wasi-python` runs programs (spec 028); the landing lane is guarded (spec 029),
   after which specifications are built in parallel.
2. **Plotting:** matplotlib M1 (spec 023), then M2; whether the snapshot pre-imports it is
   decided from M1's measurements (question 34).
3. **scipy** in the default build (decision 30), with OpenBLAS's C LAPACK made consistent by a
   carried patch until its next release.
4. **The rest of the default profile,** as chosen.
5. **The agent runtime's features,** as the owner places them (below).
6. **Hardening:** a security review against the threat model, extended to every new surface;
   x86_64 Linux rebuilds byte-identical; numpy's and pandas' own test subsets under the
   runtime; the public API frozen and documented.

### Agent runtime features (placement in 0.1.0 to be decided)

Decided as features (`decisions.md`): a cancel during a blocked door call reports `cancelled`
(a defect); a tool protocol over the door (`from host import tools`, an optional gate, call
counting and a call record); async host functions; read-only code on the import path; a
filesystem provider (`Mount`, at `/` too, 10,000 calls by default); bounded sessions across
turns.

## After 0.1.0

Build-time profiles beyond the default (constitution §2's principle;
`research/2026-10-16-build-time-profiles-of-the-core-c-libraries.md`).
