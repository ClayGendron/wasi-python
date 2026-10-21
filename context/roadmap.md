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
2. **Plotting:** matplotlib M1 (spec 023), then M2; the snapshot pre-imports no package,
   matplotlib included (decision 34, spec 069).
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
(read-only code on the import path); 058 (a Windows grant renames a folder over a file); 053 (async host functions, after the a5 tag); 052 (the judge on several cores); 023 (matplotlib M1); 062 (the progress history in volumes); 060 (a per-run budget of request bytes, and N8); 061 (a provider's `OSError` carries its errno); 059 (the x86_64 rebuild runs natively; its dry run passed with the x86_64 rebuild in 16 min); 057 (the release ties what it signs to what it built); 046 (lxml, with libxml2 and libxslt; after the a6 tag); 070 (the judge's small follow-ups); 068 (a cap on files open at once, default 1,024); 047 (regex); 055 (bounded sessions, closed as Jupyter closes them); 076 (the grant checks agree on Windows); 069 (the snapshot pre-imports no package, decision 34); 071 (deep recursion raises RecursionError, and a host guard against late signal handlers); 080 (071's recursion checks count deterministic fuel); 075 (tools.py small fixes: the a6 review's F1 and 060's N1); 079 (the build runs only the pinned host Python: the a6 review's F2); 077 (the grant follow-ups); 063 (the release judges in parallel shards: twelve shards and a gather, about 23 minutes a dry run); 081 (guest fuel does not depend on where the repo is checked out); 065 (CPython's own tests in the release: 28,108 passes in five groups, the 0.1.0 gate of question 99).

Releases: the 0.1.0a4 tag run failed on Windows (fixed by 058) and nothing was published;
0.1.0a5 was tagged 2026-10-18 after its dry run passed on all three systems (AGENTS.md rule 6b;
question 95) and its security review's addendum ("a5 may be released"), and published the same day
(run 39152890225, every job green). Hand-checked: the wheel on PyPI and on the GitHub release is
`a92b9193…eaad` (38,951,211 bytes), the tarball `a30206ef…589e`; the artifacts inside both are
the build job's (`python.wasm` `42344e2c…`, snapshot `c4190ca0…`, zip `daf2cdd8…`), which is spec
035's reviewed set (`SHA256SUMS` `3c0ec02e…`). 0.1.0a6 was tagged 2026-10-19 on `7b473f6` after its
dry run (39182011247) passed on all three systems on `ef1441b` and its security review said "a6 may be
released", and published the same night (run 39184720868, every job green). Hand-checked: the wheel on
PyPI and on the GitHub release is `fe23e238…4c02` (52,096,520 bytes), the tarball `8126b2de…8f3a`,
the `SHA256SUMS` asset `b7bd4a8b…cacb`, each equal to the build job's printed list; the artifacts
inside both are byte for byte spec 057's set (`python.wasm` `16550143…`, snapshot `4eb5418a…`, zip
`16ee747c…`; `SHA256SUMS` `c353b1d9…`). 0.1.0a7 was tagged 2026-10-19 on `2737b29` after its dry run
(39252500950) passed every job on all three systems on `e72ccf2` (only documents changed after it,
and the fast tier passed on the tagged commit; question 95) and its security review's addendum said
"a7 may be released"; it was published the same day (run 39255794160, all 29 jobs green), the first
release through spec 063's shards and `gather`. Hand-checked: the wheel on PyPI and on the GitHub
release is `e7727db9…4b4b` (43,751,127 bytes), the tarball `fc59b977…291d`, the `SHA256SUMS` asset
`2c7e95ca…f722`; the artifacts inside both are byte for byte main's set (`python.wasm`
`ab78e893…`, snapshot `c50ca51f…`, zip `02026895…`; `SHA256SUMS` `c9dcb5b8…`), and every file
passes `shasum -c`.

In flight (decision 91, widened 2026-10-19: up to six build-class at once, the owner). **089 and 083 landed 2026-10-19 as one batch** (`45b917c`; dry run 39346796670 green on all
three systems, `cpython-fs` included): the judge seals its stages against host litter, and its
driver answers file times and inode numbers itself, so the CPython groups' fuel is the same on
the lane's machine and the release runners. 090 (the build ignores host litter, build-class)
follows later; 089's delta review leaves one follow-up (L1: one `try`/`finally` from the seal to
`run()`'s return). 078 landed on 2026-10-20 (main `97be88a`); its dry run's one red row, a Windows-only session check, is fixed forward by 093, which enters wave 1 first. From that night, landings go by waves (`decisions.md`, "Waves, judging on CI"): wave 01 (087, 085, 084 and 091) landed on 2026-10-20 at main `6006fde` (history line 82); wave 02 (039 and 041, a stacked chain, with 073 and 093) landed the same night at main `b0c7a74` (history line 83); wave 03 (the judge-only 094, 084's removal rows name their Windows need, and 092, the judge reads a release record) landed at main `44540cb` (history line 84); wave 04 (086, the toolchain moves to wasi-sdk 34, with S5's SipHash-1-3) landed alone at main `085dba5` (history line 85); wave 05 (090, the build ignores host litter, and 082, inline sessions keep the handlers) landed at main `c74d0f0` (history line 86); wave 06 (043, matplotlib M2; 037, scipy with OpenBLAS; 096, kiwisolver's clear and lxml's final) landed at main `c5fc7a4` (history line 87); wave 07 (038, scipy M2, which every release tag with 037 needs, and 044, scikit-learn, stacked on it) landed at main `1cd25e2` (history line 88); wave 08 (042, seaborn and reportlab; 066, the compiled packages' own tests; 099, numpy's singular matrices raise) landed at main `faa9c93` (history line 89, accepted from a clone outside the home folder after macOS host litter voided the first attempt); next, wave 09 (100, numpy on OpenBLAS; 101, the faster release run; 097, host litter outside the home folder), then 045 (statsmodels), 102 (the release tier), 095 (scipy's, scikit-learn's and statsmodels' own tests) and 067 (the pure-Python packages' own tests), all in 0.1.0 (the owner, 2026-10-20, `decisions.md`); before that, the stacked chain 043 (matplotlib M2) built on 086's tip, 090 (the build ignores host litter, confirmed for build), 082, and the package chain 037, 038, 044, 045 with 042 and the reserved 066, 067, 072, 074. Follow-ups noted: Linux CI fuel moves between runs (cpython-b 3.5%, 092's builder), 078's abandoned-turn gap N1 (093's review), 087's caller-passed set N1 (wave 01's review). The order after 083 (the owner told, 2026-10-19, `decisions.md`):
086 (wasi-sdk 34; rebase, rebuild, A/B), then 039 (tier A; re-accepted on the new base), then 043, then 041 (built stacked on 039)
(matplotlib M2; rebase, rebuild, delta review), then 037's rework, built on 043's and 086's
reviewed tips once they are (a stacked build). The parallel-safe specifications land in the gaps,
in batches of up to three: 073 (`run` keeps an unclosed file's bytes), 085 (gather checks what it
trusts), 084 (a private root never outlives its call) and 087
(build-class, it carries a patch, with the security review's S3; lands alone). Reserved: 091, numpy-core's layout-dependent fuel
as a fact (judge-only, parallel-safe; `test_string_comparisons`' fuel moves with the bool DType
object's address at every build-class landing, so it leaves the ratchet as a recorded fact while
the group's passes stay ratcheted). The whole-surface security review for 0.1.0 ran on main
`302df18` (`reviews/0.1.0-whole-surface-security-review-2026-10-19.md`): the sandbox holds; 0.1.0
waits on S1 (closed the same day by the owner's repository settings) and S2 (084 lands). S5's hash
flag rides in 086, S3 in 087, S6 is 085. Each package that lands after it gets a one-page addendum
from the review's checklist.

Confirmed for build, in the build-class queue (up to six built at once, the owner, 2026-10-19, each landing alone, §5.7 as amended 2026-10-19). The packages come first (the owner,
2026-10-19: "I want them done soon"): a free slot goes to the next package whose dependencies have
landed, and the lane lands a built package before any other built specification but 065. The two
chains: 037, 038 (scipy), then 044 (scikit-learn), then 045 (statsmodels); 039 (tier A), then 041
(files read by path from the zip) and, with 043 (matplotlib M2; question 81 answered), 042 (seaborn
and reportlab; the barcode folder ships only through decision 73's later change, with Sarna's acknowledgement, per 042's pre-build review C3; 042's build review L3). Questions 83 and
81 are answered. The other build-class specifications (073, 072, 078) take a slot only when no
package is ready to build.

Added by the owner 2026-10-18, evening (`decisions.md`): CPython's own test suite gates 0.1.0
(question 99; its research is running, its specification follows spec 063); a per-sandbox cap on
open files before 0.1.0, default 1,024 (question 92); spec 055 closes sessions as Jupyter does,
running Python's shutdown under a small budget (question 92); landing through pull requests that
must pass their checks (spec 064, after 063). The default snapshot pre-imports no package (decision 34;
spec 069, build-class); a `full` profile, its own artifact set with the stack pre-imported, is
built only if an embedder asks (decision 34, constitution §2). CPython's own suite runs in the guest (27,503 passes; research
`2026-10-18-cpythons-own-tests-under-the-runtime.md`); it gates 0.1.0 through spec 065. It found
one defect fixed before 0.1.0 by its own specification (071): C-level recursion traps the guest
instead of raising `RecursionError`. After 0.1.0: a Rust core shared at least partly by
Python and JavaScript (question 96); the tool protocol's `batch` (question 90).

Reserved: 099 (numpy's linalg raises LinAlgError for a singular matrix as natively, though wasm has no floating-point exception flags; before 0.1.0, the owner, 2026-10-20).

Reserved: 100 (numpy's linear algebra links the set's OpenBLAS in place of its bundled `lapack_lite`, so `nan` matrices fail as native numpy on OpenBLAS does and numpy and scipy share one LAPACK; exactly singular matrices agree with native OpenBLAS on 254 of 300, not all; stacked on 099; before 0.1.0, the owner's answers to questions 106 and 107, 2026-10-20).

Reserved: 101 (a faster release run: the workflow reuses the native build when the hash of its pins and recipes is unchanged, and splits the macOS own-guest and own-embedding shards; build-class, the release workflow; about 60 minutes to about 30 by the lane's estimate, not measured; before 0.1.0, the owner, 2026-10-20, `decisions.md`, "Fewer CI runs per specification").

Reserved: 102 (the release tier: upstream's opt-in slow tests, sympy's slow and tooslow, networkx's and narwhals' `--runslow`, numpy's and pandas' `slow`, contourpy's `--runslow` cases, run only on the publishing run and the dry run on main before a tag; sympy's one 2.6 T test in a shard of its own past the 360 s bound; drafted on `spec/102-the-release-tier`; before 0.1.0, the owner, 2026-10-20, `decisions.md`, "two tiers of tests").

Reserved: 103 to 108, the runner's structural chain (the design review of 2026-10-20, section 8): 103 the engine seam, 104 the runner as a package of one module per concern, 105 one owner for process state and the test seams off module globals, 106 typed call state and a type checker, 107 `mounts.py` behind a protocol and one platform module, 108 a structural review as a stage; parallel-safe, stacked, one wave, one dispatch on the chain's tip, the `v0.1.0a7` set as the baseline; the owner, 2026-10-20.

Reserved: 105 (one owner for the process's state: `_process.py`, one object with every lock, cache and registry, a fork reset by introspection and one exit release; the test seams move onto it; two rules checks keep locks and mutables off module level; parallel-safe, stacked on 104, the third of the chain 103–108 from the design review memo of 2026-10-20).

Reserved: 107, "`mounts.py` behind a call-context protocol, one platform module, one stamp, and the source explains itself" (the design review's H4, M3, M4, M2): the fifth link of the chain 103 to 108, stacked on 106; parallel-safe; lands in the chain's wave.

Reserved: 108 (a structural review is a stage; the last of the chain 103 to 108 that
`research/2026-10-20-a-design-review-of-the-runner.md`, section 8, sets out; the owner,
2026-10-20): the rule "Structure is reviewed, not only behaviour" in AGENTS.md, the eight-row
rubric, its measurements and a template in `reviews/README.md`, one line in the reviewer's
checklist, four rules checks (a released version has its structural review; a built structural
specification cites its pre-build review; the judge patches the runner only through the process
object, with 105's allowance that 107 shrinks; no function over 80 lines, with the tree's
offenders as an allowance that only shrinks), and question 108 for the owner's amendment of
§5.6. Parallel-safe, context and judge only; before 0.1.0, since 0.1.0 is the first release the
rule gates.

Reserved: a closer for spec 108's two allowances (the eighteen private runner names the judge still patches, `SEAM_ALLOWED` in `tests/checks/test_rules.py`, each with the field or parameter its comment names; the nine functions over 80 lines, `LONG_FUNCTIONS`): parallel-safe, `src/` and the tests that patch, one specification or two; before the first structural review scores R6 and R7, or named in that review as the Medium's reserved specification.

Reserved: 109 (code speaks for itself in `tests/`, `scripts/` and `release/`: no specification number, memo, review, finding ID or `context/` path in a code file, the reason kept in words, 1,360 references cleared by a reproducible script plus a read, held by a rules check beside spec 107's for `src/`; build-class by the letter, since comments in `scripts/` change, comments only; the last entry of the chain 103 to 108; the owner, 2026-10-20).

Reserved: a closer for spec 109's leftovers (code speaks for itself, the leftovers: the 78 citing string literals outside `src/`, held by one regex over string tokens for `spec NNN`; the judge's allowance files' comments; the guest's own sources, their fuel re-measured; whether a message a user reads falls under the rule is the owner's to say): parallel-safe, the judge and the guest's inputs; the number is the lane's when it is drafted (109's build review, finding 2; the integration review's finding 3).

Reserved: 095 (scipy's, scikit-learn's and statsmodels' (045, the owner, 2026-10-20) own tests in the release, the closer `tests/upstream/packages.toml` names for 037, 038 and 044 in place of 066); 096 (two product defects spec 066's survey found: kiwisolver's four `*_clear` functions return `void` where `tp_clear` returns `int`, so a garbage collection that clears a cycle holding a kiwisolver object traps the guest, and `import lxml.html.diff` raises `TypeError` because lxml's `fake_cython` has no `final`; build-class, carried patches; 066 depends on it); 097 (the judge's staging follow-ups 066 names: `test_elementsoup.py` under pytest's import mode, the `stage-layout` class; and host litter in writable guest roots, spec 089's accepted residual, which 066's surveys hit four times: 066's delta review L5); 098 (Linux x86-64 fuel is bimodal on a fixed artifact set, cpython-b 292.5 G or 302 G and cpython-archives 163 G or 166 G between CI runs, while darwin rows match exactly: 092's builder and 086's trace). Noted for the owner: with no floating-point exception flags in wasm, `numpy.linalg.inv` of a singular matrix returns `nan`s and raises no `LinAlgError` (066's survey, a guest probe); the owner chose to fix it before 0.1.0, and spec 099's draft (branch `spec/099-numpy-singular-inverse`) does it with a recipe header, `recipes/npy_fenv_flags.h`, not a numpy patch. 037 and 038: no release tag carries 037 without 038's Sobol fix (the lane's ruling on 037's build review F4). Reserved by the lane on 2026-10-20.

Reserved: 065 (CPython's own tests in the release; before 0.1.0, decision 99), 066 (the compiled
packages' own tests in the release: matplotlib, pillow, kiwisolver, contourpy (spec 043), lxml and regex), 067 (the pure-Python
packages' own tests in the release). Spec 063's `tests/upstream/packages.toml` names them as
closers. Spec 071 is widened to own the Linux host crash spec 063's build review reproduced (a
guest trap after the host enabled faulthandler past the runner's first engine); 063's gap for it
names 071 here.

Reserved: 078, "the runner runs each guest on a stack of its own" (question 102 answered (a),
2026-10-19; it folds in the first 078, spec 071's build review F1, the musl pool): the runner runs
each guest on a thread of its own with an 8 MiB stack, and the README asks other embedders for the
same. It closes spec 065's nine recursion trap entries and the data depths 071 documents; its design
answers the thread costs question 102 lists (host functions on the runner's thread, the caller's
contextvars, Ctrl-C, `threading.stack_size`, `run_async` with the caller's executor). Parallel-safe,
before 0.1.0.

Reserved: 088, the judge-only binary (questions 89 and 101): a build never published, linked with
numpy's C test modules and built with CPython's (`--enable-test-modules`), on which the judge runs
the tests that need them. Build-class; after the packages.

Reserved: **089**, host litter never reaches a verdict: the judge seals every stage it grants
read-only (no write bit on any folder, unsealed and retried at removal) and fails any guest run
whose grants gain litter or change, naming the file. macOS's folder-size cache wrote `.DS_Store`
into `build/harness/cpython/run-*` mid-run and moved fuel silently (spec 083's build review;
research `2026-10-19-ds-store-in-the-judges-stages.md`). Parallel-safe; **lands before 083**, which
rebases onto it; an `fd_readdir` litter watch is left to a later spec. **090**, the build and its artifact
checks agree on one litter list (`._*`, `Icon\r`, volume-root names), the release tarball packs
`SHA256SUMS`' list, the repo's `.gitignore` lists litter. Build-class; after 089 or beside it.

Reserved (the lane numbers it): the stdlib zip carries CPython's generated `_missing_stdlib_info.py`.
The WASI build writes it beside `_sysconfigdata__wasi_wasm32-wasi.py` in
`cross-build/wasm32-wasip1/build/lib.wasi-wasm32-3.15/`, and `scripts/steps/70_zip.sh` copies only
the latter, so `traceback` names a missing stdlib module only as "not found" (spec 078's build
review, F2; the class `no-missing-stdlib-info` in `cpython-a` closes with it). A one-line
build-class fix; it rides with 086 (built at 086's rebase onto 078, which closes the class).

Reserved: 082, inline pytest sessions keep wasmtime's signal handlers: pass `-p no:faulthandler` to
inline sessions, or run them as subprocesses (spec 080's review, F1: on Linux's serial unit tier,
16 guard refusals in `test_runner_calls.py` and `test_runner_mounts.py` after `test_landing_lane`
and `test_plugin`, since 071).

Reserved from the 0.1.0a7 security review (2026-10-19,
`../reviews/0.1.0a7-security-review-2026-10-19.md`), each before 0.1.0: **084**, a private root
outlives its call: a guest given `root=True` builds a tree deeper than the process's free
descriptors, so `shutil.rmtree` fails silently and disk use adds up across calls (F1, medium; a
removal that holds no descriptor per level, a retry at the next sweep, and a check); **085**,
`gather` checks what it trusts: the lane's acceptance tied to the set's `SHA256SUMS` hash as well as
`python.wasm`'s (F5), the allowed check-and-reason pairs pinned so an accepted pass reported
`blocked` everywhere turns red (F6), each record's counts cross-checked and a missing metric red
(F7), and the rebuild jobs print `python3 --version` (N5); **087**, the guest follow-ups: a carried
patch so regex keeps clock ticks in `clock_t` and `timeout=` fires past 2.147 s (F3, with its
upstream draft), libxslt's `xsltMaxDepth` lowered from a recipe so deep XSLT raises instead of
trapping (F4, optional), and checks that hold the README's corrected lxml and recursion sentences
(F2, F4).

Reserved: **086**, the toolchain moves to wasi-sdk 34 (LLVM 23.1.0). The pinned wasi-sdk 33 orders
`try_table` blocks by heap address in one pass of the WebAssembly backend, so scipy's ducc0 FFT
compiles to different bytes on every run; LLVM fixed it upstream (`fd76c9bd`, issue #204883) in
LLVM 23, and wasi-sdk 34 compiled that file to one object in 16 runs (research
`2026-10-19-the-try-table-order-in-llvm.md`). The move re-verifies every package's bytes on every
host and removes spec 037's same-bytes exception (question 104). Question 105, answered (b): it lands before 037, which never lands the exception. Clang 23 adds `-Wunused-template`
warnings and changes libc++'s ABI tag in mangled names; the memo lists what to check. Drafted
2026-10-19: `specifications/086-the-toolchain-moves-to-wasi-sdk-34.md` (build-class; a trial of
the move gave one `SHA256SUMS` from every host tried, and wasi-libc 34 changes `os.dup`'s errno,
which a link-time refusal keeps at `ENOTSUP`). Built, reviewed, then rebased onto 078 with the
security review's S5 (`--with-hash-algorithm=siphash13`) and the zip's `_missing_stdlib_info`
folded in, rebuilt (one `SHA256SUMS` from four builds on three hosts) and A/B-measured; its delta
review is next.

Reserved: 074 (what CPython's suite asks of the product; spec 065's follow-up A, build-class;
before 0.1.0, since it closes classes in the gate the owner set): `sys.executable` empty;
`_reset_cache` in the `ctypes` stand-in, so the judge's driver drops it; and whether the `ctypes`
and `mmap` stand-ins name what CPython's tests name at import (`pythonapi`, `py_object`, `Array`,
`mmap.error`, `ACCESS_DEFAULT`).

Follow-ups decided by the owner: a provider's `OSError` carries its errno to the guest (question
54; spec 061); a judge-only binary linked with numpy's test modules (question
89; a later build-class specification).

Follow-up from spec 069's pre-build review (2026-10-18, the lane's ruling on its F1): **spec
073, `run` keeps an unclosed file's buffered bytes** (drafted 2026-10-19 on
`spec/073-run-keeps-unclosed-files-bytes`; confirmed for build after its pre-build review;
amended 2026-10-19 by question 103's answer; build-class; **built 2026-10-19**, awaiting its build
review). On the snapshot, `run` loses the
buffered bytes of a file left open when `__main__` defines a function: `__main__`'s dict is
frozen, so once its module dies at finalization nothing frees it (the frozen heap; found by spec
055's addendum, P10b). A script and `-m` lose them on both binaries too, in runpy's temporary
module. It gives every program a fresh `__main__` and runs a script and `-m` in it, as CPython
does, and, by question 103's answer (`decisions.md`), `run` on the snapshot undoes the freeze
before it finalizes, as a session's close does, so the snapshot finalizes as CPython does: about
+28.2 M fuel a snapshot call, and spec 069's check (b) restated from 8 times to 3 (measured 3.82).
It closes the gap `test_run_keeps_an_unclosed_files_bytes[snapshot]`.

Follow-ups from spec 068's pre-build review (2026-10-18): **spec 072, a bound on path depth**
(not drafted): a limit on the components of every path a path call resolves, so the descriptors
wasmtime holds while it walks a deep path on macOS (and Linux without `openat2`) are bounded
too, which 068's cap does not count (question 100 tells the owner); and **a cheaper forward**
for the runner's shadows (about 26 µs per shadowed call), which after spec 069 every default
call that imports from the zip pays, through 068's counted `path_open` and `fd_close`.

Release rule: alphas are cut by the agent after their pre-release security review (the owner,
2026-10-18: "You may publish alpha releases but not the 0.1.0 release"); 0.1.0 is the owner's to
tag. Before 0.1.0: a security review of the whole surface (milestone 6), a structural review of `src/` against the design review's rubric (spec 108; `reviews/0.1.0-structural-review-<date>.md`, written by a fresh agent on the commit before the bump and committed with it, the dry run on that commit), the a4 review's F3 (a
per-run request-byte budget) and N8 (both spec 060), and the wheel's size against PyPI's limit (question 64:
49.7 MiB with matplotlib M1).

## After 0.1.0

Build-time profiles beyond the default (constitution §2's principle;
`research/2026-10-16-build-time-profiles-of-the-core-c-libraries.md`).
