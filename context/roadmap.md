# Roadmap

The owner's living plan: what each release contains and the order of work. It changes by the
owner's decision, recorded here with its date; the constitution (`constitution.md`) holds the
mission, the bar every release meets (§2) and the rules, and does not change with this file.
Specifications and research memos carry the detail; this page only orders them.

The runtime is embedder-neutral (constitution §4.5): its consumers are not on this roadmap. A
feature lands because it is general, whoever asked for it first.

## 0.1.0: the first release to rely on

Decided by the owner on 2026-10-17: **matplotlib and scipy are in 0.1.0**, and with them tiers A
and B of the default-profile memo (decisions 43 to 48).

### The default profile

| package | state |
|---|---|
| CPython 3.15 with its stdlib, including `sqlite3`, `bz2`, `lzma` | shipped (0.1.0a2) |
| numpy, pandas | shipped (0.1.0a1) |
| matplotlib | M1 specified and confirmed (spec 023); M2 (triangulation, contourpy) next |
| scipy | researched (`research/2026-10-17-what-scipy-needs.md`, the OpenBLAS memo); its licences, SIMD and placement decided (`decisions.md`, 25 to 31) |
| tier A: about thirty pure-Python packages (Excel, PDF, HTML, YAML, templates, graphs, sympy, seaborn, reportlab) | approved (decisions 43 to 45); after the zip's per-member cost is cut, and after matplotlib M1 |
| tier B: scikit-learn, statsmodels, lxml (with python-docx and python-pptx), regex | approved for 0.1.0 (decision 48); native builds after scipy |
| left out of 0.1.0 | pytz (decision 47); Rust packages, pyarrow, polars, duckdb, plotly (later, or a profile); network libraries |

### Milestones

1. **An install that just works** (0.1.0a4): the build says where it is (spec 027);
   `pip install wasi-python` runs programs (spec 028); the landing lane is guarded (spec 029),
   after which specifications are built in parallel.
2. **Plotting:** matplotlib M1 (spec 023), then M2; whether the snapshot pre-imports it is
   decided from M1's measurements (question 34).
3. **scipy** in the default build (decision 30), with OpenBLAS's C LAPACK made consistent by a
   carried patch until its next release.
4. **The rest of the default profile** (`research/2026-10-17-what-else-the-default-profile-carries.md`,
   "The order of specifications"): the zip keeps what packages need (metadata, a wider `ctypes`
   stand-in); the zip's directory is read once, researched and then specified, before the zip
   grows (decision 44); tier A, sympy included; pandas' Styler from a zip; then on the scipy
   line scikit-learn, statsmodels, lxml with python-docx and python-pptx, and regex. Excel
   output with nothing writable is documented (decision 46).
5. **The agent runtime's features,** as the owner places them (below).
6. **Hardening:** a security review against the threat model, extended to every new surface;
   x86_64 Linux rebuilds byte-identical; numpy's and pandas' own test subsets under the
   runtime; the public API frozen and documented.

### Agent runtime features (placement in 0.1.0 to be decided; question 49)

Decided as features (`decisions.md`): a cancel during a blocked door call reports `cancelled`
(a defect); a tool protocol over the door (`from host import tools`, an optional gate, call
counting and a call record); async host functions; read-only code on the import path; a
filesystem provider (`Mount`, at `/` too, 10,000 calls by default); bounded sessions across
turns.

### Where 0.1.0 stands (2026-10-18, overnight)

Landed (each reviewed, accepted by the lane, dry run cited in its landing notes): 027, 028, 029
(milestone 1 complete); 030, 031, 036 (the tool protocol), 032 with three post-landing fixes
(read-only mounts), 033 (the zip carries metadata and a `ctypes` stand-in), 048 (the sandbox
holds on wasmtime 49.0.0: GHSA-m9f7-9w4p-gv38 and GHSA-96f6-r43r-8c24 mitigated in the runner).

Built and confirmed, waiting on the owner: 034 (writable mounts; question 71).

In build: 040 (x86_64 rebuilds the same bytes; build-class), 050 (numpy's and pandas' own tests
in the guest).

Confirmed for build, in the build-class queue (one at a time, §5.7): 051 (what the upstream tests
found: numpy signature traps, `.pyc` names), 035 (the zip's directory is read once), 023
(matplotlib M1), 043 (matplotlib M2; waits on question 81), 037 and 038 (scipy), 039 (tier A),
041 (files read by path from the zip), 042 (seaborn and reportlab; question 73 for the barcode
folder), 046 and 047 (lxml, regex; question 82), 044 and 045 (scikit-learn, statsmodels;
question 83). Not build-class, confirmed: 049 (the public API frozen; after 034; question 88).

Not yet specified for 0.1.0: the release itself (0.1.0a4 and then 0.1.0 are the owner's to tag,
§5.5; question 84 for a4); a security review of the whole surface before 0.1.0 (milestone 6).

## After 0.1.0

Build-time profiles beyond the default (constitution §2's principle;
`research/2026-10-16-build-time-profiles-of-the-core-c-libraries.md`).
