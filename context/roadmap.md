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
| matplotlib | M1 landed (spec 023, 0.1.0a6); M2 (triangulation, contourpy) next |
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

### Agent runtime features (all in 0.1.0; question 49, answered 2026-10-18)

Decided as features (`decisions.md`): a cancel during a blocked door call reports `cancelled`
(030, landed); a tool protocol over the door (031, 036, landed); a filesystem provider (032,
landed) and writable mounts (034, landed); async host functions (spec 053); read-only code on
the import path (spec 054); bounded sessions across turns (spec 055, build-class: a second guest
export). The owner, question 49: "cancel nothing for 0.1.0".

### Where 0.1.0 stands (2026-10-18, afternoon)

Landed (each reviewed and accepted by the lane): 027, 028, 029 (milestone 1); 030, 031, 036,
032, 033, 048; 040 (x86_64 rebuilds the same bytes); 051 (what the upstream tests found); 034
(writable mounts); 050 (numpy's and pandas' own tests in the guest); 035 (the zip's directory
is read once); 056 (the 0.1.0a4 security review's findings); 049 (the public API frozen); 054
(read-only code on the import path); 058 (a Windows grant renames a folder over a file); 053 (async host functions, after the a5 tag); 052 (the judge on several cores); 023 (matplotlib M1); 062 (the progress history in volumes); 060 (a per-run budget of request bytes, and N8); 061 (a provider's `OSError` carries its errno); 059 (the x86_64 rebuild runs natively; its dry run passed with the x86_64 rebuild in 16 min); 057 (the release ties what it signs to what it built).

Releases: the 0.1.0a4 tag run failed on Windows (fixed by 058) and nothing was published;
0.1.0a5 was tagged 2026-10-18 after its dry run passed on all three systems (AGENTS.md rule 6b;
question 95) and its security review's addendum ("a5 may be released"), and published the same day
(run 39152890225, every job green). Hand-checked: the wheel on PyPI and on the GitHub release is
`a92b9193…eaad` (38,951,211 bytes), the tarball `a30206ef…589e`; the artifacts inside both are
the build job's (`python.wasm` `42344e2c…`, snapshot `c4190ca0…`, zip `daf2cdd8…`), which is spec
035's reviewed set (`SHA256SUMS` `3c0ec02e…`). 0.1.0a6 waits on 057.

Building now (decision 91: up to three build-class at once): 046 (lxml; answering its build review), 047 (regex). Confirmed for build: 055 (bounded sessions;
build-class), 057 (the release ties what it signs to what it built; build-class; closes F4
before the release after a5). Confirmed for build, building next: 059 (the x86_64 rebuild runs natively: `-ffp-contract=off` on
every compile; the owner's decision of 2026-10-18).

Confirmed for build, in the build-class queue (up to three built at once, each landing alone, §5.7 as amended 2026-10-18), in this order: 059, then 057,
then 046 and 047
(lxml, regex; question 82 lets them take a slot before scipy), 037 and 038 (scipy), 043
(matplotlib M2; question 81 answered), 039 (tier A), 041 (files read by path from the zip), 042
(seaborn and reportlab; question 73 adds the barcode folder, written in before its build), 044
and 045 (scikit-learn, statsmodels; question 83 answered), then 055.

Follow-ups decided by the owner: a provider's `OSError` carries its errno to the guest (question
54; spec 061); a judge-only binary linked with numpy's test modules (question
89; a later build-class specification).

Release rule: alphas are cut by the agent after their pre-release security review (the owner,
2026-10-18: "You may publish alpha releases but not the 0.1.0 release"); 0.1.0 is the owner's to
tag. Before 0.1.0: a security review of the whole surface (milestone 6), the a4 review's F3 (a
per-run request-byte budget) and N8 (both spec 060), and the wheel's size against PyPI's limit (question 64:
49.7 MiB with matplotlib M1).

## After 0.1.0

Build-time profiles beyond the default (constitution §2's principle;
`research/2026-10-16-build-time-profiles-of-the-core-c-libraries.md`).
