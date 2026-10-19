# 069 — The snapshot pre-imports no package

- **Status:** **landed 2026-10-19** (accepted on `96cf575` as `fc9282b`, history line 71; the build review, `../reviews/069-the-snapshot-pre-imports-no-package-build-2026-10-19.md`, confirmed it; see the Landing notes' last part). Before landing: **built 2026-10-19; revised against its build review** (the build review,
  `../reviews/069-the-snapshot-pre-imports-no-package-build-2026-10-19.md`, written in a
  scratchpad and copied by the lane: "lands once F1 is written in"; F1 to F4 are written in, the
  Landing notes' last part). Built on `spec/069-the-snapshot-pre-imports-no-package`, rebased onto
  main `b413192`, from an empty `build/` (`SHA256SUMS` `4530b6ce…`; after F4's comment wrap,
  steps 60 to 90 again: `1889459e…`, the binaries unchanged). Before that: confirmed for build 2026-10-18 at `68062f3`
  with nits N1 to N4 (the confirmation,
  `../reviews/069-the-snapshot-pre-imports-no-package-spec-2026-10-18-confirmation.md`, written in
  the lane's evidence folder and copied by the lane; "confirmed for build"); the nits are taken
  (the Landing notes). Before that: drafted 2026-10-18; revised against its pre-build review. The review (`../reviews/069-the-snapshot-pre-imports-no-package-spec-2026-10-18.md`, written in a scratchpad and copied by the lane) said "ready
  once F1 to F3 are written in"; F1 to F9 are written in as the lane ruled, and the section
  "Disposition of the pre-build review" says where. Drafted on
  `spec/069-the-snapshot-pre-imports-no-package` from main `4a94c14`, rebased onto `ef1441b`
  (specs 065 and 071 on the roadmap). It changes the artifact set
  and the build recipe, so it is reviewed once before it is built (constitution §5.6). The
  draft's evidence (variants A and B rebuilt from the frozen set's objects, A's module list, and
  the full judge run against an artifact set holding A) is in the main tree, git-ignored, under
  `build/reviews-evidence/069-spec/` (Evidence, below).
- **Date:** 2026-10-18
- **Owner:** Clay Gendron
- **Kind:** **build-class** (§5.7): it changes `recipes/reactor_main.c` (the `PREIMPORT`
  default and two comments), `scripts/assemble_artifacts.py` (the `x-preimport` line read from
  the recipe) and one comment in `scripts/steps/80_snapshot.sh`. It is also a judge change
  (Decision 5: one check removed, five added, two edited, two harness constants, one gap
  entry in `tests/known_gaps.toml`, one unit test of Decision 3's reader), and it
  changes `src/wasi_python/` docstrings (four sentences), `README.md` (the facts, the advice, the
  import path's text, the generated reference) and `CHANGELOG.md`. It changes no public name,
  signature, field, default or option: **`tests/public_api.txt` does not change** (Decision 9).
  It changes no pin, no patch and `downloads/SHA256SUMS` not at all. **The lane accepts it with
  `--accept-judge` and `--accept-growth`** (Decision 7).
- **Depends on:** 003 (the reactor, `wizer.initialize`, step 80), 005 (3.15: `_colorize` in the
  list), 008 (start is unmetered), 049 (the public API frozen; what is promised), 054 (the import
  path; its pinned `HIT pytz` numbers, which this specification restates as 054 requires); all
  landed. It interacts with 046, 047, 055, 063, 065 and 071, which are in flight or on the
  roadmap (Decision 11), and names a follow-up, 073 (Decision 4).
- **Research it stands on:** `../research/2026-10-18-one-pre-import-rule-for-every-package.md`
  ("the memo") and its folder of probes and results. The owner's decision 34
  (`../decisions.md`, "34, answered", 2026-10-18): "None pre-imported": the default snapshot
  pre-imports the stdlib bootstrap only, for every package now and later.

## The problem

The snapshot (`python-snapshot.wasm`) is the reactor after Wizer ran `wizer.initialize` once at
build time. That function starts the interpreter and runs one statement, `PREIMPORT`
(`recipes/reactor_main.c`). Today the statement is
`import encodings, io, os, sys, json, csv, re, _colorize, numpy, pandas`. A **pre-import** is a
module in it: its import is paid at build time and lives in the snapshot's memory.

Pre-importing numpy and pandas makes a pandas run cheap, and every other run dear. The memo
measured it on the frozen set (EXECUTED; its method rebuilds today's snapshot byte for byte):

- every run pays about 68 M fuel more for them, almost all of it in Python's teardown at exit
  (`-c pass` is 83.4 M with them, 15.6 M without);
- every live instance holds about 32 MiB more of resident memory (41.3 MiB against 9.6 MiB),
  used or not;
- the snapshot is 70.9 MB instead of 40.5 MB, and the wheel about 52 MB instead of about 41 MB.

Pre-importing every package instead would carry the wheel past PyPI's 100 MiB limit within
about three specifications (the memo's projection). The owner chose one rule for every package:
none is pre-imported. A pandas script then costs 4.63 G fuel instead of 110 M (42 times); a
numpy script 9 times; a plot 16% more. That is the price, accepted by decision 34.

## Terms

- **Package:** anything the artifact set carries that is not CPython's standard library or the
  reactor's own code: numpy, pandas, matplotlib, PIL, kiwisolver, fontTools, dateutil, tzdata,
  six, cycler, pyparsing, packaging, `host` (the tool protocol's guest package), and every
  package a later specification adds. A module is the stdlib's when its top-level name is in the
  guest's `sys.stdlib_module_names`.
- **The reactor's own modules:** `_reactor`, `_zip_directory` and `_zip_resources` (frozen into
  the reactor by step 60), and `__main__`.
- **Start cost:** the fuel of a `-c pass` run through the judge's driver (`tests/harness/guest.py`:
  fixed clock and entropy, so a figure repeats to parts in ten million). Fuel is wasmtime's count
  of guest instructions. Instantiation's own memory fill is unmetered (spec 008).

## Decisions

1. **The list is the stdlib bootstrap, exactly variant A.** `recipes/reactor_main.c`'s default
   becomes:

   ```c
   #define PREIMPORT "import encodings, io, os, sys, json, csv, re, _colorize"
   ```

   - *What "bootstrap" means here:* the eight names the memo measured as variant A, no more and no
     fewer. `encodings`, `io`, `os` and `sys` are loaded by the interpreter's own start anyway;
     `json`, `csv` and `re` make a pure-Python script about twice as cheap as on the plain binary
     (the memo, finding 5: 278 M against 553 M); `_colorize`, which 3.15 loads lazily, keeps the
     first traceback of a run from paying for it (spec 005, the 0.1.0a2 CHANGELOG).
   - *Reason for not trimming or widening it:* this exact list is the one measured, reproduced
     here (Evidence: A's snapshot is 40,509,812 bytes, as the memo's), and the one the owner
     agreed to. A different stdlib list is a different measurement and a later specification's
     choice (Decision 2).
   - What it pulls in: 70 modules at start, every top-level name the stdlib's but `__main__`,
     `_reactor` and `_zip_directory` (EXECUTED, `modules_at_start.json`). `ast` and `linecache`
     are among them, so spec 055's statement that they "are already imported in the snapshot"
     stays true. `random`, `logging`, `zoneinfo`, `uuid`, `inspect` and `zipfile` are not.

2. **The rule for every package, now and later.** A specification that adds or changes a
   package never adds to `PREIMPORT`, by any name, dotted or not, and never passes
   `-DPREIMPORT` from a build step. Its Decisions say "not pre-imported (decision 34, spec
   069)" where 023, 046 and 047 said "not pre-imported (question 34)". The stdlib list itself
   changes only by a specification of its own that measures the change as the memo did and
   changes the judge's copy of the list (Decision 5d), visibly, with `--accept-judge`. No
   specification may pre-import a package in the default profile, even with a judge change (a
   `full` profile, if the owner ever asks for one, is its own artifact set and brings its own
   check): the module check
   (Decision 5a) refuses any non-stdlib top-level name, and changing that rule needs the owner
   to reverse decision 34. *Reason:* the decision is "for every package now and later"; a rule
   that a checklist states and nothing enforces is broken by the first package that wants its
   latency back.

3. **One source for the list.** The `#define` in `recipes/reactor_main.c` is the only place the
   list is written. `scripts/assemble_artifacts.py` stops carrying its own copy
   (`PREIMPORT = "encodings, …, numpy, pandas"`, line 89): it reads the `#define`'s string from
   the recipe with one regular expression, drops the leading `import `, and writes
   `x-preimport encodings, io, os, sys, json, csv, re, _colorize` to MANIFEST exactly as today's
   format. The reader is one function, `preimport_list(text: str) -> str`, which raises
   `SystemExit` naming `recipes/reactor_main.c` when the `#define PREIMPORT` line is missing or
   appears more than once; a unit test (`tests/unit/test_artifact_rules.py`, check i) feeds it
   no line, one line and two lines (the review, F7). *Reason:* today the two copies agree only
   by care; no check reads `x-preimport` (`paths.parse_manifest` skips every `x-` line), so a
   drift would ship a MANIFEST that misstates the snapshot.
   - *The `#define` is the effective value.* `#ifndef PREIMPORT` stays in the recipe (it is how
     the stand-ins are made), but no build step passes `-DPREIMPORT` (check c), and the README
     tells a self-builder to edit the `#define`, not to pass the flag (Decision 8; the review,
     F8). So the recipe's hash in MANIFEST, `x-preimport` and the binary agree.

4. **The rest of the recipe stays.**
   - `wizer.initialize` keeps `gc.collect(); gc.freeze()` after the imports, the pinned clocks
     and entropy, and `__wasilibc_reset_preopens`.
   - **Why the freeze stays** (the review, F1). Most of what the imports left behind is gone,
     but the freeze still pays: on A's snapshot, `-c pass` is 15,593,597 fuel, and the same run
     with `gc.unfreeze()` first is 43,773,463 (EXECUTED, the review's R2; on today's snapshot
     the pair is 83.4 M against 308.2 M). Unfreezing would make a bare run 2.8 times dearer, and
     only 3.8 times cheaper than the plain binary, which check (b) refuses (it asks 8 times).
     So the freeze and check (b) are coupled: whoever changes one restates the other.
   - **A defect this specification keeps, and who closes it.** `run` on the snapshot loses the
     buffered bytes of a file left open when `__main__` defines a function: a `-c` program that
     opens `/out.txt`, writes 100 bytes, defines a function and exits keeps 0 bytes on A's
     snapshot and on today's, and 100 on the plain binary; without the `def`, every binary keeps
     all 100 (EXECUTED, the review's R1, `flush_probe.py`; spec 055's addendum found it first,
     P10b). 069 neither causes nor fixes it. 055 fixes it for sessions only, by unfreezing at
     close. **The closer for `run` is a follow-up specification, 073, "run keeps an unclosed
     file's buffered bytes"**, which this specification adds to the roadmap (Decision 10). Until
     073 lands, the defect is on the scoreboard as a gap (check h). If 073's fix unfreezes the
     heap, 073 restates check (b)'s factor with its numbers, as a judge change; a fix that keeps
     the heap frozen (for example a `__main__` made per run; INFERRED, not measured) need not.
     Amended 2026-10-19 by spec 073: 073 takes that second way, a fresh `__main__` per program
     (its option 4; measured at about +11 K fuel on a bare snapshot run), so the freeze and
     check (b)'s factor of 8 stay; the corner it leaves is question 103.
   - **For 055's builder** (no change to 055 here): on A, undoing the freeze adds about 28.2 M to
     a bare run (15.6 M to 43.8 M), against about 225 M on today's snapshot (83.4 M to 308.2 M;
     the review's R2). 055's closing cost, which unfreezes, therefore falls with 069 to about
     44 M rather than about 310 M (INFERRED: a run is not a session close).
   - Two comments change: the file's header
     ("a live interpreter with the stack imported" becomes "with the stdlib bootstrap imported;
     no package (spec 069)") and the pinned block's list of what is captured (numpy's
     SeedSequence is no longer captured; `random`'s seed is not either, since `random` is not
     imported).
   - `_reactor._refresh` (`recipes/reactor_bootstrap.py`) is not changed. It reseeds `random`
     and `numpy.random`, resets logging's start time and zoneinfo's path only for modules found
     in `sys.modules`; on a fresh snapshot instance it now finds none of them and does nothing.
     Spec 055's sessions call it per turn, where it still matters. *Reason:* removing guarded
     code buys nothing and would change `_reactor`'s frozen bytes for no behaviour.
   - Step 80's header comment ("numpy and pandas imported") becomes "the stdlib bootstrap
     imported (`PREIMPORT`, spec 069)". Its commands do not change.
   - Step 60 does not change. `python.wasm` itself changes bytes, because the `#define`'s string
     is a constant linked into it: the relinked plain reactor is 36,916,497 bytes, the same size,
     SHA-256 `92f181984102215e…` against the frozen `1655014314805b58…` (EXECUTED).
   - **The plain reactor's fuel moves too, by about +0.011%.** Its `-c pass` is 166,530,527
     against the frozen binary's 166,511,583 (+18,944), and B's relinked binary gives the
     frozen figure exactly, so the shorter constant alone moves it (EXECUTED, `plain_fuel.txt`).
     The constant is read only by `wizer.initialize`. What moves is about 84 KB of read-only
     data (EXECUTED, the review's R4: A's and B's link maps differ in one hunk): the merged
     C-string section shrinks by 25 bytes, the `.rodata` after it, from `0x10fc3b4` to
     `0x1110e80` (the recipe's frozen modules, docstrings, `object.c`'s `static_types`), moves
     by 16 to 24 bytes, and the alignment at `_mi_page_empty` absorbs the shift, so the file
     keeps its size; `.data` and `.bss` do not move. The growth is not a fixed cost per run:
     +18,944 on `-c pass`, +149,263 on `test_npy_files_round_trip[plain]`, 0.011% to 0.017%
     throughout, which fits string and memory routines whose cost depends on alignment working
     over literals that moved, some by an odd number of bytes (INFERRED). It is above the
     judge's fuel tolerance of 0.01% (`scoreboard.FUEL_TOLERANCE`), so 29 plain-binary metrics
     show as grown in the run below, the largest `test_uncaught_errors_print_as_native[plain]`
     at +0.0166%, and Decision 7's growth reason names them. *Reason for accepting
     it rather than padding the string:* the figure is exact and deterministic, it is a hundredth
     of a percent, and holding a constant's length to keep fuel equal would be a recipe that
     guards nothing.

5. **The checks.** Each is written before the code and seen failing first on main's set
   (Acceptance criteria). Each guest check runs through the judge's driver.
   - **a. `test_the_snapshot_pre_imports_no_package`** (`tests/checks/test_v1_3_data_stack.py`,
     v1.3; it replaces `test_snapshot_preimports_the_stack`). One snapshot run of a probe whose
     first statement reads `sys.modules` and prints, as JSON, its keys and
     `sorted(sys.stdlib_module_names)`. Host-side:
     - every top-level name of a key is the stdlib's or the reactor's; the message names each
       other name. *The stdlib's* means: in the printed `sys.stdlib_module_names`, or one of the
       three names CPython ships outside that set, which `paths.CPYTHON_UNLISTED` holds and
       labels: `__hello__` and `__phello__` (CPython's frozen test modules) and any name
       beginning `_sysconfigdata_` (CPython's generated build data; the review, F6, EXECUTED
       R3). *The reactor's* means `paths.REACTOR_MODULES`: `"__main__", "_reactor",
       "_zip_directory", "_zip_resources", "_host"` (`_host` is the door module,
       `recipes/hostmodule.c`, not a package);
     - **the zip's non-stdlib names** (so the message calls them) are computed from the
       artifact set's own zip: the top-level names of its members (a folder's first part, or a
       module file's stem at the root), minus the stdlib's and the reactor's names as above. The
       check asserts that this set holds `numpy`, `pandas` and `host` (so the derivation is not
       vacuous; seen failing against S9), and that no top-level name in `sys.modules` is in it,
       naming each;
     - every name of `paths.PREIMPORT` is in `sys.modules` (the list really ran).

     It records the probe's fuel. *Reason:* the stdlib rule needs no list of packages, so it
     holds for every package a later specification adds, pure or compiled in, without anyone
     remembering to extend it; the zip-derived names make the failure message name the package,
     and cross-check the rule against the set actually shipped. A package cannot hide behind a
     stdlib name: to do so it would have to replace the stdlib module in the one zip every module
     comes from, which is the build's own content (the project's stand-ins under stdlib names,
     `ctypes` and `mmap`, are project code, and allowing them is right).
     `tests/upstream/packages.toml`
     (spec 063) and `paths.PACKAGES` are not used: both name distributions (`python-dateutil`,
     `pillow`, `sqlite-autoconf`, header-only `pybind11`), not import names, and the first
     does not exist on main.
   - **b. `test_the_snapshot_starts_cheaper_than_plain`** (same file, v1.3). The start cost of
     the snapshot times 8 is at most the plain binary's start cost; it records the snapshot's
     fuel (the plain run is `record=False`). Variant A gives 15,593,597 against 166,511,583:
     10.7 times (the memo). Today's snapshot gives 83.4 M: 2.0 times, so it fails. numpy alone
     (variant D, 26.9 M) gives 6.2 times and fails. *Reason for 8:* the memo's projection to
     the end of the roadmap keeps A at about 10.5 times (31 M against 325 M), so 8 leaves
     about 25% margin for growth while still refusing even one pre-imported package of numpy's
     size; this is the snapshot's reason to exist (the memo, finding 5), stated as a ratio of
     counts, never a time.
     - Its message prints both counts and the ratio, and says that a failure means either a
       package was pre-imported (see check a) or the snapshot's reason to exist must be
       restated (the review, F5).
     - The factor is stable as packages land (the plain start grows with zip members, spec
       039's 30 K per member; the snapshot's does not, its zip directory being captured at
       build time), but not as the plain start gets cheaper or the snapshot's dearer. **A
       specification that changes the plain start, the freeze or the teardown restates (b)'s
       factor as a judge change, with its numbers**: a faster directory read, the teardown skip
       of Scope, and 073 if its fix unfreezes (Decision 4).
   - **c. `test_the_pre_import_list_is_the_stdlib_bootstrap`** (`tests/checks/test_rules.py`,
     fast tier, no artifact needed). The `#define PREIMPORT` line of `recipes/reactor_main.c`,
     parsed, equals `"import " + ", ".join(paths.PREIMPORT)`; no tracked file under `scripts/`,
     `recipes/` or `.github/` contains `-DPREIMPORT` or `PREIMPORT=`; and
     `scripts/assemble_artifacts.py` contains no literal list (no line matching
     `PREIMPORT\s*=\s*"`). *Reason:* it catches a package added to the list on a machine
     without artifacts, before a build, and keeps Decision 3's single source.
   - **d. `paths.PREIMPORT`** (`tests/harness/paths.py`): `("encodings", "io", "os", "sys",
     "json", "csv", "re", "_colorize")`, with a comment naming decision 34 and this
     specification. Changing it is a judge change.
   - **e. `test_manifest_names_the_pre_imports`** (`tests/checks/test_v1_1_artifact_set.py`,
     v1.1, needs the manifest). MANIFEST has exactly one `x-preimport` line and it equals
     `", ".join(paths.PREIMPORT)`.
   - **h. `test_run_keeps_an_unclosed_files_bytes`** (`tests/checks/test_v1_4_embedding.py`,
     v1.4, parametrised `[plain]` and `[snapshot]`, through the judge's driver). The review's
     `flush_probe.py` program: open `/out.txt`, write 100 bytes, define a function, exit without
     closing. It asserts the file holds 100 bytes, and reports a shortfall as one finding
     through `scan.report(findings, "unclosed file")`, the finding written as
     `"<binary>: a file left open kept <n> of 100 bytes"`. `[plain]` passes. `[snapshot]` fails
     today and after 069 with `unclosed file: 1 finding(s), digest 7da6e52329c1: snapshot: a
     file left open kept 0 of 100 bytes` (the digest computed with `scan.report` for that
     finding). **A gap entry** in `tests/known_gaps.toml` allows exactly that:
     ```toml
     [[gap]]
     check = "tests/checks/test_v1_4_embedding.py::test_run_keeps_an_unclosed_files_bytes[snapshot]"
     match = "1 finding(s), digest 7da6e52329c1"
     reason = "run on the snapshot loses an unclosed file's buffered bytes when __main__ defines a function (the frozen heap; found by spec 055's addendum, P10b; restated by spec 069's review, F1)"
     closes_with = "context/roadmap.md (spec 073, run keeps an unclosed file's buffered bytes)"
     ```
     *Reason* (AGENTS.md rule 3: a failure mode once seen becomes a check or a gap entry): the
     defect has been seen twice and nothing owned it for `run`; the gap puts it on the
     scoreboard with its closer, and turns red the day 073 fixes it (a gap whose check passes
     fails the run) or the day it gets worse. *The judge-hash note:* the new check and the
     edit to `tests/known_gaps.toml` are judge files, so they change the judge hash and are
     named in the `--accept-judge` reason (Decision 7). A 073 that lands first makes the check
     a plain pass and needs no gap; 073's own specification then owns the check.
   - **i. The reader's unit test** (`tests/unit/test_artifact_rules.py`):
     `preimport_list` returns the list for a recipe text with one `#define PREIMPORT "import
     …"`, and raises `SystemExit` naming `recipes/reactor_main.c` for a text with none and for
     one with two (Decision 3).
   - **f. `test_runner_runs_the_plain_reactor`** (`tests/checks/test_v1_4_embedding.py`) tells
     the binaries apart by `'csv' in sys.modules` instead of `'numpy'`: `False` on the plain
     reactor, `True` on the snapshot (csv is pre-imported and not loaded by the plain start;
     EXECUTED, the plain binary's 36 modules). Its docstring says "which starts with only the
     interpreter's own modules".
   - **g. `test_the_import_path_comes_after_the_runtime[snapshot]`**
     (`tests/checks/test_v1_4_embedding.py`): `HIT pytz` is counted **2 on both binaries**
     (`== 2`, the conditional removed). Spec 054's criterion pinned 0 on the snapshot and 2 on
     the plain binary, and said a set that changes the numbers restates them with its reason.
     The reason: pandas' import looks for its optional `pytz` twice; it used to have run at
     build time, before any import path existed; now it runs in the call, after the prelude, on
     both binaries alike. The `_hashlib` half of that check is unchanged (`hashlib` is not
     pre-imported in either variant).
   - **Removed:** `test_snapshot_preimports_the_stack` (a), with its `snap.fuel * 10 <
     plain.fuel` for `import pandas`: that inequality is the property decision 34 gives up
     (A gives 4.63 G against 4.95 G, 1.07 times).

6. **The stand-ins.** Each new or changed check is seen failing against each stand-in that
   concerns it, and the landing notes list what each printed. Stand-in snapshots are made by the
   memo's method (`probes/relink.py` and `probes/snapshot.sh` from the memo's folder, pointed at
   a scratch folder): step 60's recorded compile with `-DPREIMPORT=…`, its link, the strip, and
   step 80's Wizer flags. About ten seconds each. The scratch set is the built set with the
   stand-in's two binaries and its `SHA256SUMS` lines replaced, run with
   `WASI_PYTHON_ARTIFACTS`.
   - **S1, numpy re-added:** `PREIMPORT` "… _colorize, numpy". Expected: (a) fails naming
     `numpy`; (b) fails (6.2 times); (c) fails when the recipe carries it (the source stand-in).
   - **S2, one pure package added:** "… _colorize, six". Expected: (a) fails naming `six`
     (a package from the zip with no compiled part, so the stdlib rule, not a builtin check, is
     what catches it); (b) passes (six is small; that is why (a) exists); (c) fails.
   - **S3, today's list** (main's frozen set, no rebuild): (a) fails naming `numpy`, `pandas`,
     `dateutil`, `six` and the Cython helpers (`_cython_3_3_0`, `_cyutility`,
     `cython_runtime`), and `_sysconfigdata__wasi_wasm32-wasi` (EXECUTED: these are B's
     non-stdlib names); (b) fails (2.0 times); (e) fails (the line names numpy and pandas);
     (g) fails (`HIT pytz` 0 times on the snapshot). (f) passes here, since `csv` is in both
     lists; it is a new discriminator, not a new behaviour, so S7 is its stand-in.
   - **S4, a stdlib module added** ("… _colorize, random"): (a) and (b) pass, (c) fails. This
     shows that even a stdlib change to the list is a judge change, as Decision 2 says.
   - **S5, a second copy:** `scripts/assemble_artifacts.py` with a literal `PREIMPORT = "…"`
     restored: (c) fails.
   - **S6, a step passing `-DPREIMPORT`** (a line added to `scripts/steps/60_link.sh`): (c)
     fails.
   - **S7, the snapshot replaced by the plain reactor** (a scratch set whose
     `python-snapshot.wasm` is a copy of `python.wasm`): (f) fails (both print `False`); (a)
     fails (`csv`, a name of `paths.PREIMPORT`, is missing); (b) fails (1.0 times).
   - **S8, a package imported outside the `#define`** (the review, F7): a second
     `run_private("import six");` in `wizer_initialize` after the `PREIMPORT` line, relinked
     and snapshotted as S1. Expected: (a) fails naming `six`; (c) and (e) pass. It shows that
     (a) does not lean on the recipe's text.
   - **S9, a zip without the guard's names:** check (a)'s derivation run on a scratch zip that
     holds no `numpy`, `pandas` or `host` (a unit-level call of the check's derivation helper,
     no guest run): the non-vacuity assertion fails, naming the three.
   - **Decision 3's reader** is seen failing by its unit test (check i): a recipe text with no
     `#define PREIMPORT` and one with two each exit naming the file.

7. **The fuel and bytes that move.** Measured by the full judge run against an artifact set
   holding A's two binaries ("The judge run against A", below; EXECUTED; the built set differs
   from it only in MANIFEST and SHA256SUMS, which no metric reads). The lane's acceptance is
   `uv run pytest --accept "spec 069: the snapshot pre-imports no package" --accept-judge
   "<the judge files of Decision 5, the new gap check and tests/known_gaps.toml>"
   --accept-growth "<the reason below>" --retire
   tests/checks/test_v1_3_data_stack.py::test_snapshot_preimports_the_stack`. The `--retire` is
   needed: the removed check's node is absent, and `scoreboard.accept` refuses absent checks
   that are not retired (the review, F2).
   - **Grows, 45 metrics on main's checks** (the run's `grew 45`), in four kinds:
     - *pandas on the snapshot, about +4.5 G each (7):* every snapshot check whose measured run
       imports pandas, 83 to 526 M becoming 4.60 to 5.02 G;
     - *numpy or matplotlib on the snapshot (3):* `test_npy_files_round_trip[snapshot]` +0.92 G;
       the two matplotlib jobs +1.22 G each (matplotlib imports numpy and the modules pandas
       used to have loaded);
     - *stdlib modules pandas used to load (6):* `test_stdlib_debugging_tools_import` +391 M,
       `test_resources_read_as_zipfile_reads_them[snapshot]` +220 M,
       `test_a_zone_load_does_not_grow_with_the_zip[snapshot]` +184 M,
       `test_uncaught_errors_print_as_native[snapshot]` +25 M (the traceback machinery),
       `test_metadata_answers_from_the_zips_directory[snapshot]` +25 M,
       `test_patched_callbacks_run[snapshot]` +8 M;
     - *the plain reactor, +0.011% to 0.017% (29):* every plain run whose 0.011% exceeds the
       tolerance (Decision 4).
   - **Grows, 11 more: the upstream groups** (`test_upstream_suite[*]`), unrun in the main run
     (their source trees are a need) and run alone below: each pandas group +4.4 to 5.0 G (+0.9%
     on pandas-groupby to +28.8% on pandas-internals), each numpy group +0.8 to 1.6 G (+0.6% to
     +0.8%). No group loses a pass. **The lane's growth list is 56 metrics.**
   - **Shrinks, 21 metrics:** the snapshot's `bytes` (70,901,724 to 40,509,812,
     `test_binary_is_a_core_wasm_module[snapshot]`); 13 snapshot runs that import neither
     package, by about 67.8 M each (to 15.7 to 21.0 M), and
     `test_the_fast_reader_builds_zipimports_dict[snapshot]` and
     `test_sqlite_holds_a_lock_while_it_writes` by 67.5 M and 56.5 M;
     `test_extra_preopens_work_on_the_snapshot[*]`, whose `gc.get_objects()` walk falls by
     557 M each (65.5%); `test_unbuffered_output_survives_a_hard_exit[snapshot]` (2.88 M to
     1.21 M); the two tool-call runs (0.3%). Without a growth reason `--accept` keeps the lower of
     old and new; with `--accept-growth` every value is replaced, so the shrinks are recorded too.
   - **Unchanged:** the zip's bytes; the plain binary's bytes (36,916,497); 17 plain metrics
     move within the tolerance (the large plain jobs, +0.004% to +0.009%).
   - **The growth reason, written in full:** "decision 34 (the owner, 2026-10-18): the default
     snapshot pre-imports no package (spec 069). Every snapshot run that imports pandas pays
     it in the run (about +4.5 G each), numpy about +0.9 G, matplotlib about +1.2 G, and stdlib
     modules pandas used to load (inspect, zipfile, zoneinfo, traceback) up to +0.4 G; each
     upstream group pays its package's import once (pandas groups +4.4 to 5.0 G, numpy groups
     +0.8 to 1.6 G). The plain reactor grows by 0.011% to 0.017% because the shorter PREIMPORT
     constant moves about 84 KB of read-only data by 16 to 24 bytes. The snapshot is 30.4 MB
     smaller and a bare run 5.3 times cheaper." The judge reason names Decision 5's files, the
     new check (h), its gap entry and the unit test (i).
   - *Which numpy figure is which* (the review, F9): "+0.9 G" here is
     `test_npy_files_round_trip[snapshot]`'s growth; the CHANGELOG's "about 0.7 G" is what the
     pre-import saved a small numpy job (the memo, B − A: 0.70 G); the README's "about 0.8 G" is
     that job's whole cost on A (the memo: 788 M). Each sentence names its figure's kind.
   - **Outside the judge** (recorded in the landing notes, not checks): the wheel shrinks by
     about 11.06 MB (the snapshot deflates to 10,375,343 bytes at zlib level 6 against
     21,435,051; the memo), from 52,091,103 to about 41.0 MB; the snapshot's memory minimum
     falls from 916 pages (57.3 MiB) to the link's floor of 640 (40.0 MiB); resident memory per
     live instance from 41.3 MiB to 9.6 MiB (the memo, one machine's figure).

8. **The README.**
   - *What you get:* the snapshot row becomes "the same binary after a Wizer snapshot with the
     interpreter started and the stdlib's bootstrap modules imported (no package; decision
     34); one `run` per instance, about 14 ms". The time is the memo's benchmark fact (one run,
     an M-series Mac), labelled as such.
   - *Measured:* the sizes row gives the snapshot's new size (40.5 MB, this build's landing
     notes); the `-c pass` row becomes "14 ms (the memo's benchmark fact), most of it finalizing
     the interpreter; 15.6M guest instructions (83.4M with numpy and pandas pre-imported, before
     spec 069)"; the `os._exit(0)` row keeps its time and gains 0.97M instructions; a new row:
     "`import pandas`, snapshot: 4.63G guest instructions for the memo's pandas job (0.81 s,
     benchmark fact; the memo), 4.60G for the judge's
     `test_numpy_and_pandas_are_builtin_at_manifest_versions[snapshot]`; the snapshot
     pre-imports no package (decision 34)". With the old check gone, the row cites both (the
     review, F9). The plot row's "matplotlib not
     pre-imported" becomes "no package pre-imported" with the built set's fresh and kept
     figures.
   - *The snapshot's facts* (after "The snapshot adds three facts of its own"): the second
     becomes "the stdlib modules it pre-imports (`encodings`, `io`, `os`, `sys`, `json`, `csv`,
     `re`, `_colorize`) were imported with an empty environment; no package is pre-imported, so
     numpy, pandas and every other package import in your run, with your environment".
   - *Advice for pandas-heavy embedders* (a short part under *Running it*, "Calls that use
     pandas"): each call that imports pandas pays its import, about 4.6 G instructions and about
     0.8 s on an M-series Mac (benchmark fact); numpy about 0.8 G. Three ways to pay it less
     often, each stated with what it is today: put several steps in one call; bounded sessions
     (spec 055), which pay an import once per session, **once spec 055 has landed** (the
     sentence names the spec and is written only as "planned" until then); and a `full` profile,
     its own artifact set that pre-imports the stack, which the roadmap records and which is
     built only if an embedder asks (constitution §2: profiles stay few). It also says what an
     embedder who builds its own set can do: edit the `#define PREIMPORT` in
     `recipes/reactor_main.c` and rebuild, so that the recipe's hash and MANIFEST's
     `x-preimport` line follow it; that is not a product promise. It does not suggest a `-D`
     flag, which would leave MANIFEST naming the default list (the review, F8). The numpy
     figure is written as "a small numpy job costs about 0.8 G in all" (Decision 7).
   - *The import path* (spec 054's text): "On the plain binary that also happens for packages
     the snapshot imported when it was built: an entry's `pytz.py` is imported by `import
     pandas` on the plain binary, not on the snapshot." becomes "This holds on both binaries
     alike: an entry's `pytz.py` is imported by `import pandas`, since the snapshot pre-imports
     no package." 054's distinction is moot, and its pinned numbers are restated (Decision 5g).
   - *How it is built:* "snapshot the reactor … numpy and pandas pre-imported" becomes "with
     the stdlib's bootstrap modules pre-imported and no package".
   - *Scope:* "pre-importing matplotlib in the snapshot (the owner's question 34)" leaves the
     Out list; Out gains "pre-importing any package (decision 34: the default snapshot pre-imports
     none; a `full` profile only if asked)".
   - *Generated reference:* the four docstrings below change, and the block is regenerated with
     `uv run python tests/harness/api.py --write` (`test_the_readme_reference_matches_the_api`).
   - The docstrings: `src/wasi_python/__init__.py` (the module docstring's `paths.snapshot`
     line, and `Artifacts.snapshot`) and `src/wasi_python/runner.py` (`run`'s and
     `run_async`'s `snapshot` argument) say "with the stdlib's bootstrap imported (no package)"
     in place of "with the stack pre-imported".

9. **The CHANGELOG, and what kind of change this is.** Under 0.1.0a6 (or the section open when
   it lands), one entry headed **Changed:** "The snapshot pre-imports no package (decision 34,
   spec 069): it starts with the interpreter and the stdlib's bootstrap modules (`encodings`,
   `io`, `os`, `sys`, `json`, `csv`, `re`, `_colorize`). A bare call costs 15.6M guest
   instructions instead of 83.4M; a call that imports pandas pays it, about 4.5G more than
   before (numpy about 0.7G more for a small job), so a `fuel=` cap set for a pandas job on the snapshot needs that
   much more. The snapshot is 30 MB smaller and the wheel about 11 MB. numpy and pandas now
   import with the call's environment. `snapshot=True` is unchanged as an argument."
   - *Classification under spec 049:* it is a change of what `snapshot=True` costs and of what
     the guest holds at start, not of the public API. No name, signature, field, default or
     option changes, and `tests/public_api.txt` does not change. Spec 049 lists fuel counts,
     timings and the guest's contents as not promised, and the promise starts at 0.1.0. So it
     needs no deprecation, is neither of 049's two exceptions (not a tighter limit, not a
     security fix), and would be allowed in a minor release even after 0.1.0. It is still
     written under **Changed**, not as a note, because it can break a working embedder: a
     `fuel=` cap tuned to a pandas job on today's snapshot ends "out of fuel", and a program
     that read `sys.modules["numpy"]` without importing it raises `KeyError`.

10. **The roadmap and the other documents.** `context/roadmap.md`: the milestone 2 sentence
    ("whether the snapshot pre-imports it is decided from M1's measurements, question 34")
    becomes "the snapshot pre-imports no package (decision 34, spec 069)"; the default-profile
    part records "a `full` profile (its own artifact set, the stack pre-imported) only if an
    embedder asks"; the follow-ups gain "spec 073: `run` keeps an unclosed file's buffered
    bytes (a defect of the frozen heap, found by 055's addendum and 069's review; a gap until
    then; it restates check (b) of spec 069 if its fix unfreezes)", which is the closer the gap
    entry of check (h) names. Amendment lines, one each, dated, in the landed specifications that stated
    the old snapshot: 023 (its "Numbers for the owner (34)" are history; decision 34 answered
    it; spec 069 changed the snapshot), 054 (Decision 6's "on the plain binary also packages
    the snapshot pre-imported" is moot since 069; its `HIT pytz` numbers are restated there).
    `context/questions-for-the-owner.md` is not touched (34 already moved to decisions).

11. **Specifications in flight.** Whichever of them lands after 069 re-measures against the
    snapshot 069 built, and its landing notes say so; the one that lands before is measured as
    today and 069's builder rebases onto it and re-measures 069's own numbers.
    - **046 (lxml), built, awaiting its build review's confirmation; 047 (regex), built,
      awaiting its build review.** Both measured their snapshot `-c pass` and package jobs on
      today's snapshot, and both chose "not pre-imported (question 34)", which this decision
      confirms. *If either lands after 069:* its builder rebuilds on 069's main, restates its
      "what the set costs" fuel figures against the new snapshot (the snapshot's `-c pass` moves
      from about 83 M to about 16 M; its lxml and regex jobs gain the import of any package they
      use beyond their own; a regex job that does not import pandas falls by about 68 M), and
      accepts its own growth with its own reason; 069's figures are not its to accept. 047's
      review condition "the package-context wrappers leave the pre-imported numpy and pandas as
      they are" is then checked as "numpy and pandas imported in a run on the snapshot give
      native's results under the wrappers": the same jobs, imported in the call rather than at
      build time (the condition loses its object, not its intent). *If both land before 069*
      (the likely order, since both are built): 069's builder rebases, rebuilds, re-runs the
      judge, and restates Decision 7's table and the Evidence's numbers on that set; 069's
      checks need no change for lxml or regex (`lxml` and `regex` are packages to check (a),
      derived from the zip).
    - **063 (the release judges in parallel shards), awaiting its pre-build review's
      confirmation:** it changes no artifact; its shard plan rests on per-group seconds measured
      on today's snapshot. 069 adds about 0.8 s to each pandas group's session and about 0.15 s
      to each numpy group's (one import each, benchmark facts against groups of minutes), so its
      plan does not move. Its `tests/upstream/packages.toml` is not read by 069. Whichever lands
      second rebases; the conflicts can only be in `CHANGELOG.md` and `README.md`.
    - **055 (bounded sessions), confirmed for build:** its design does not depend on the
      pre-import (the session starts from the snapshot and keeps what turn one imported), and
      its claim that `ast` and `linecache` are in the snapshot stays true (Decision 1). Its
      first-turn fuel figures measured with pandas pre-imported (`import pandas as pd` in a turn
      cost nothing then) are restated by 055's builder on 069's snapshot if 069 lands first,
      and so is its closing cost, which unfreezes: about 28 M on A against about 225 M today
      (Decision 4's note); its E5b resident figure (37 MiB after a pandas turn) does not change in kind. The README's
      advice (Decision 8) names sessions as "planned" until 055 lands; 055's builder turns the
      word into a present-tense sentence.
    - **065 (CPython's own tests gate 0.1.0), on the roadmap, not yet drafted** (the research
      `../research/2026-10-18-cpythons-own-tests-under-the-runtime.md`, measured on today's
      snapshot). Its adaptation A1 (a no-op `_reset_cache` given to the `ctypes` stand-in)
      exists because "the snapshot pre-imports numpy, which imports the stand-in", which
      regrtest's `clear_caches()` then calls; with 069 the stand-in is not imported at start, so
      A1 goes away unless a test imports numpy first. Its fixed start ("about 1.14 G before its
      first test") and possibly its 27,503 passes and failure classes restate on 069's
      snapshot. If 069 lands first, 065's drafter re-checks A1 and the fixed start on it; if 065
      lands first, 069's builder rebases and the lane re-judges, and any moved number of 065's
      is restated in 069's landing notes with its cause.
    - **071 (C-level recursion raises `RecursionError`), build-class, on the roadmap:** it may
      touch `recipes/reactor_main.c` or the link step (INFERRED from the research's section
      4.1: a guard and the stack size). The two can collide as text in the recipe and in
      `python.wasm`'s and the snapshot's bytes, so in criterion 3's hashes. They land one at a
      time (§5.7); **whichever lands second rebases, rebuilds, and restates criterion 3's sizes
      and hashes** (and its own), and re-measures the metrics that moved.
    - **073 (`run` keeps an unclosed file's buffered bytes), named here** (Decision 4): it closes
      check (h)'s gap; if its fix unfreezes the heap it restates check (b).
    - **068 (a cap on open files):** no interaction.

12. **The upstream suites.** Each group's session now imports its package in the call. The
    guest's driver (`tests/upstream/drive.py`) puts `/upstream/kit` first on `sys.path` before
    it imports each `path_packages` entry, so numpy and pandas import with the kit ahead of the
    zip (the kit holds pytest, pluggy, iniconfig, packaging, pygments, hypothesis and
    sortedcontainers), and a numpy group no longer has pandas in `sys.modules`. Neither moves a
    result: run against A, every group keeps its `passes` to the test and every class check its
    status, with the same 12 gaps (EXECUTED, "The judge run against A"). `drive.py` is not
    changed. The caps (`[groups.*].fuel`) still leave room: the tightest is pandas-internals,
    21.2 G against a cap of 28 G.

## Intent

After this specification, the default snapshot holds the interpreter and eight stdlib modules,
and nothing else. No package is pre-imported, today or later, and the judge refuses one. A bare
call is 5.3 times cheaper and an instance a quarter of the memory; a pandas call pays for its
own import. The README says so, with the numbers and the ways to pay less.

## Design

```
recipes/reactor_main.c          #define PREIMPORT "import encodings, io, os, sys, json, csv, re, _colorize"
                                two comments (Decision 4)
scripts/assemble_artifacts.py   PREIMPORT read from the recipe's #define (Decision 3)
scripts/steps/80_snapshot.sh    the header comment only
                                preimport_list(text) -> str; SystemExit naming the file
tests/harness/paths.py          PREIMPORT, REACTOR_MODULES (with _host), CPYTHON_UNLISTED
tests/checks/test_v1_3_data_stack.py   (a) replaces test_snapshot_preimports_the_stack; (b)
tests/checks/test_rules.py             (c)
tests/checks/test_v1_1_artifact_set.py (e)
tests/checks/test_v1_4_embedding.py    (f), (g), (h)
tests/known_gaps.toml                  (h)'s gap, closed by 073
tests/unit/test_artifact_rules.py      (i)
src/wasi_python/__init__.py, runner.py four docstring sentences (Decision 8)
README.md                       Decision 8; the reference regenerated
CHANGELOG.md                    Decision 9
context/roadmap.md              Decision 10; amendment lines in 023 and 054
```

The probe of check (a), in outline (the builder writes it):

```python
PROBE = (
    "import sys\n"
    "mods = list(sys.modules)\n"   # first: what the snapshot and the run's start hold
    "import json\n"                # pre-imported, so this adds nothing
    "print(json.dumps({'modules': mods, 'stdlib': sorted(sys.stdlib_module_names)}))\n"
)
```

The zip's top-level names, host-side: for each member name, `name.split("/")[0]`, with `.pyc`
(or `.py`) stripped when the member is at the root; `.dist-info` folders are skipped.

## Scope

In: the above.

Out, each with its reason:
- **A `run` that skips Python's teardown at exit.** 94% to 99% of a bare snapshot run's fuel is
  `Py_FinalizeEx` (the memo, finding 3: A's `-c pass` 15.6 M against 0.97 M with `os._exit(0)`).
  Flushing and skipping teardown for an instance that is discarded anyway would make a bare run
  about 16 times cheaper again. It changes what `run` does at exit (`atexit`, open files'
  buffers, `__del__`), so it is its own specification, after its own research, and decision 34
  names it as a separate later choice.
- **A `full` profile**, its own artifact set and wheel that pre-imports every package, for
  embedders who compute in every run and have the memory (the memo, option 5). Constitution §2
  makes a profile its own set, built, judged and published; it is built only if an embedder
  asks (decision 34). The roadmap records it (Decision 10).
- **Fixing `run`'s lost bytes of an unclosed file** (Decision 4): spec 073's, which this
  specification names, puts on the roadmap and makes visible as a gap (check h). It is a
  defect of the frozen heap that 069 neither causes nor fixes, and its fix may need to restate
  check (b).
- **A documented `PREIMPORT` knob for people who build their own set** beyond the README's one
  sentence (Decision 8): no product promise, no check.
- **Bounded sessions** (spec 055): already specified; Decision 11 says how the two meet.
- **Changing `_reactor._refresh`** or `tests/upstream/drive.py` (Decisions 4 and 12).
- **Question 64** (the wheel against PyPI's limit): this change moves the wheel down by about
  11 MB; the owner's answer (wait until a landing would cross 100 MB) is unchanged.

## Acceptance criteria

1. **Seen failing first on main's set (S3).** With the new checks in place and main's frozen
   set (`build/sets/s-4eb5418a2b1bb553-c353b1d9`): (a) fails naming numpy, pandas and the
   other non-stdlib names of S3; (b) fails (about 2.0 times); (c) fails on main's recipe; (e)
   fails on main's MANIFEST; (g) fails at its snapshot case; (f) passes (S3) and is seen
   failing against S7. (h)'s `[snapshot]` case fails with exactly its gap's finding set and is
   allowed by the gap entry; its `[plain]` case passes. The landing notes quote each failure's
   one line.
2. **The stand-ins (Decision 6).** S1, S2, S4, S5, S6, S7, S8 and S9, and the reader's unit
   test (i), each give exactly the outcomes Decision 6 lists; the landing notes give each
   check's line per stand-in.
3. **The build from empty.** `scripts/build.sh` from an empty `build/` with the downloads
   present produces the set; step 80 prints the snapshot's size and hash; the snapshot is
   40,509,812 bytes and its SHA-256 begins `bf89b904f9760f94` (this draft's EXECUTED
   rebuild, if no other change to the recipe or the zip lands first, such as 046, 047 or 071;
   otherwise the landing notes state the new figures and why, Decision 11). `python.wasm` is 36,916,497 bytes, SHA-256 beginning
   `92f181984102215e` on the same condition. MANIFEST's `x-preimport` line is
   `encodings, io, os, sys, json, csv, re, _colorize`.
4. **The same bytes from a second host.** Steps 60 to 90 on the second supported host (a
   linux/arm64 container, as 046 and 047 did) give the same `SHA256SUMS` (spec 012).
5. **The new checks pass on the built set**, and every check that passed before still passes:
   the judge's lost count is 0. `test_upstream_suite[*]` keeps its `passes` and its expected
   class lists (Decision 12).
6. **The metrics.** The full judge's growth list on the built set equals the 56 node ids of
   "The judge run against A" (45 and the 11 groups), in the same direction, each figure within
   1% of the table's, or the landing notes explain the difference (a set rebased onto 046 or
   047 moves several; Decision 11). The 21 shrinks are compared the same way. The new checks'
   own metrics (a, b) are new, not growth.
7. **The README and the reference.** `test_the_readme_reference_matches_the_api` passes after
   the regeneration; `tests/public_api.txt` is unchanged (`git diff --exit-code
   tests/public_api.txt`); the README's numbers each carry their source.
8. **The rules.** `uv run ruff check`, `uv run ruff format --check` on `src/` and `tests/`, and
   `uv run pytest -m "not slow"`, are green; then the full `uv run pytest` once, at the end of
   the build (AGENTS.md, rule 3a).
9. **After landing:** the lane's acceptance names decision 34 in `--accept-growth` with the text
   of Decision 7, names the judge files (with check h, its gap entry and the unit test i) in
   `--accept-judge`, and passes `--retire
   tests/checks/test_v1_3_data_stack.py::test_snapshot_preimports_the_stack`; the history line
   shows the retirement. The release dry run (rule 6b) passes on all three systems before the
   next tag.

## Disposition of the pre-build review

The review: `../reviews/069-the-snapshot-pre-imports-no-package-spec-2026-10-18.md` (written in a
scratchpad, copied by the lane), on `21dd92e`; verdict "ready once F1 to F3 are written in". Every
finding is written in, as the lane ruled; this revision is rebased onto main `ef1441b`.

- **F1 (medium), the freeze and the lost bytes:** written into Decision 4 (why the freeze stays:
  15.6 M against 43.8 M unfrozen; its coupling with check b; the defect, its evidence, its closer
  spec 073; the note for 055's builder: about 28 M against about 225 M), Decision 5 (check h, a
  gap entry with closer `context/roadmap.md (spec 073 …)`, its reason and the judge-hash note;
  check b's restatement rule names 073), Decision 10 (the roadmap line), Decision 11 (073), Scope
  and criterion 1.
- **F2 (low), `--retire`:** Decision 7's command and criterion 9.
- **F3 (low), 065 and 071:** Decision 11 (065's A1 goes away and its fixed start restates; 071 may
  collide in `recipes/reactor_main.c` and criterion 3's hashes, and whichever lands second
  rebases and restates them); criterion 3 names them.
- **F4 (low), the plain binary's cause:** Decision 4 states the link maps' measured difference
  (about 84 KB of `.rodata` moved by 16 to 24 bytes) and the 0.011% to 0.017% spread; Decision
  7's growth reason says the same.
- **F5 (low), check b's brittleness:** its message prints both counts and the ratio and names
  the two causes; a specification that changes the plain start, the freeze or the teardown
  restates the factor (Decision 5b).
- **F6 (low), check a's names:** `_host` joins `REACTOR_MODULES`; `paths.CPYTHON_UNLISTED` labels
  `__hello__`, `__phello__` and `_sysconfigdata_*` as CPython's and counts them as stdlib; the
  derived set is called "the zip's non-stdlib names"; the sentence on the one shared zip is
  added (Decision 5a).
- **F7 (low), stand-ins:** S8 (a package imported outside the `#define`) and S9 (the
  non-vacuity guard) added; Decision 3's reader is one function that exits when the `#define`
  is missing or appears twice, with a unit test (check i); S7 moved after S6.
- **F8 (low), the `-D` sentence:** dropped from the README's advice; a self-builder edits the
  `#define`, so MANIFEST stays true (Decisions 3 and 8).
- **F9 (nit), numbers and sources:** the README's pandas row cites the memo and the nearest
  recorded check; each numpy figure says what it measures (Decision 7); Decision 2 says "in the
  default profile".

## Evidence (EXECUTED for this draft, 2026-10-18)

All in the main tree, git-ignored, `build/reviews-evidence/069-spec/`; nothing in a git tree
changed; the main tree's build was used read-only (step 60's recorded commands, the CPython
cross-build objects, wasi-sdk 33, wasmtime 49.0.3, the frozen set
`build/sets/s-4eb5418a2b1bb553`).

- `probes/relink.py`, `probes/snapshot.sh`: the memo's probes, copied. `work/B` (today's list)
  rebuilt to the frozen snapshot, SHA-256 `4eb5418a2b1bb553…`, 70,901,724 bytes, and the frozen
  `python.wasm`, `1655014314805b58…`: the method still reproduces the set. `work/A` (Decision 1's
  list): snapshot 40,509,812 bytes, `bf89b904f9760f94…`; `python.wasm` 36,916,497 bytes,
  `92f181984102215e…`.
- `probes/modules_at_start.py`, `modules_at_start.json`: through the judge's driver. A: 70
  modules at start, non-stdlib top-level names `__main__`, `_reactor`, `_zip_directory`; B:
  588, non-stdlib `__main__`, `_cython_3_3_0`, `_cyutility`, `_reactor`,
  `_sysconfigdata__wasi_wasm32-wasi`, `_zip_directory`, `cython_runtime`, `dateutil`, `numpy`,
  `pandas`, `six`; plain: 36, the same three as A.
- `probes/plain_fuel.py`, `plain_fuel.txt`: the plain reactor's `-c pass` and `-c "import os,
  sys"`, frozen against A's relinked and B's relinked binaries (Decision 4).
- `set-A/`: the frozen set with A's two binaries, its `SHA256SUMS` recomputed and its
  `x-preimport` line edited; `judge-set-A.log` and `judge-set-A-upstream.log`: the full judge
  (`uv run pytest`, run in this worktree on main's judge, no `--accept`) against it, and the
  upstream suites alone; `probes/compare.py`, `metrics-set-A.md`, `upstream-set-A.md`: the
  comparison with `accepted.json`. The results are the next section.

## The judge run against A

The full `uv run pytest` (the worktree's judge, which is main's at `4a94c14`; no `--accept`),
`WASI_PYTHON_ARTIFACTS` set to `set-A/` (EXECUTED, darwin-arm64, 774 s; `judge-set-A.log`,
`latest-set-A.json`; the comparison is `probes/compare.py` against `context/progress/accepted.json`,
written to `metrics-set-A.md`):

- **3 failed, 1,583 passed, 59 skipped, 2 xfailed;** the ratchet: lost 3, grew 45, upstream
  unrun 31 (the source trees are a need this worktree did not meet; their run follows).
- **The three lost passes are exactly Decision 5's (a), (f) and (g):**
  `test_snapshot_preimports_the_stack` ("pre-imported: 'False False'"),
  `test_runner_runs_the_plain_reactor` (`False ['-c', 'a']` on the snapshot) and
  `test_the_import_path_comes_after_the_runtime[snapshot]` (`HIT pytz` twice). No other check
  failed: every relative fuel bound on the snapshot held (the zone, metadata and pandas-tz
  bounds of `test_v1_3_the_zips_directory.py`, the 400 M caps past start-up, the memory caps).
- The other 37 checks without a pass were unrun here for the same needs as on every worktree
  (source trees, compile records, the oracle).

**Grew** (45; fuel unless named; the ratio is against the accepted darwin-arm64 value):

| metric | check | accepted | with A | change | ratio |
|---|---|---|---|---|---|
| fuel | `test_packages_carry_their_metadata[snapshot]` (test_v1_3_data_stack.py) | 491,214,698 | 5,023,805,982 | +4,532,591,284 | +922.73% |
| fuel | `test_the_pandas_tz_job_matches_native[snapshot]` (test_v1_3_the_zips_directory.py) | 136,735,235 | 4,654,473,346 | +4,517,738,111 | +3304.00% |
| fuel | `test_callbacks_job_matches_native[snapshot]` (test_v1_3_data_stack.py) | 92,854,953 | 4,610,037,690 | +4,517,182,737 | +4864.77% |
| fuel | `test_numpy_and_pandas_are_builtin_at_manifest_versions[snapshot]` (test_v1_3_data_stack.py) | 83,753,888 | 4,600,566,321 | +4,516,812,433 | +5392.96% |
| fuel | `test_the_guest_package_round_trips_through_the_door[snapshot]` (test_v1_4_embedding.py) | 96,791,327 | 4,613,014,149 | +4,516,222,822 | +4665.94% |
| fuel | `test_a_pandas_warning_names_the_callers_line[snapshot]` (test_v1_3_data_stack.py) | 99,567,848 | 4,615,429,775 | +4,515,861,927 | +4535.46% |
| fuel | `test_ctypes_stand_in_names_what_packages_import[snapshot]` (test_v1_3_data_stack.py) | 525,757,385 | 5,017,499,647 | +4,491,742,262 | +854.34% |
| fuel | `test_plot_line_job_matches_native[snapshot]` (test_v1_3_matplotlib.py) | 7,559,510,899 | 8,784,510,216 | +1,224,999,317 | +16.20% |
| fuel | `test_savefig_rejects_a_negative_dpi` (test_v1_3_matplotlib.py) | 6,720,044,079 | 7,939,334,735 | +1,219,290,656 | +18.14% |
| fuel | `test_npy_files_round_trip[snapshot]` (test_v1_3_data_stack.py) | 218,373,946 | 1,142,983,845 | +924,609,899 | +423.41% |
| fuel | `test_stdlib_debugging_tools_import` (test_v1_3_data_stack.py) | 537,061,545 | 927,890,382 | +390,828,837 | +72.77% |
| fuel | `test_resources_read_as_zipfile_reads_them[snapshot]` (test_v1_3_the_zips_directory.py) | 5,734,401,130 | 5,954,503,716 | +220,102,586 | +3.84% |
| fuel | `test_a_zone_load_does_not_grow_with_the_zip[snapshot]` (test_v1_3_the_zips_directory.py) | 111,905,640 | 295,627,143 | +183,721,503 | +164.18% |
| fuel | `test_uncaught_errors_print_as_native[snapshot]` (test_v1_4_embedding.py) | 84,805,133 | 109,934,611 | +25,129,478 | +29.63% |
| fuel | `test_metadata_answers_from_the_zips_directory[snapshot]` (test_v1_3_the_zips_directory.py) | 133,261,742 | 158,094,459 | +24,832,717 | +18.63% |
| fuel | `test_patched_callbacks_run[snapshot]` (test_v1_3_matplotlib.py) | 215,601,418 | 223,961,262 | +8,359,844 | +3.88% |
| fuel | `test_npy_files_round_trip[plain]` (test_v1_3_data_stack.py) | 1,416,303,852 | 1,416,453,115 | +149,263 | +0.01% |
| fuel | `test_longdouble_parses` (test_v1_3_data_stack.py) | 1,058,252,009 | 1,058,374,412 | +122,403 | +0.01% |
| fuel | `test_default_integer_width_is_documented` (test_v1_3_data_stack.py) | 1,057,888,426 | 1,058,010,760 | +122,334 | +0.01% |
| fuel | `test_a_reread_after_invalidate_caches_is_the_fast_read` (test_v1_3_the_zips_directory.py) | 742,833,102 | 742,940,676 | +107,574 | +0.01% |
| fuel | `test_uncaught_errors_print_as_native[plain]` (test_v1_4_embedding.py) | 596,056,479 | 596,155,306 | +98,827 | +0.02% |
| fuel | `test_a_zone_load_does_not_grow_with_the_zip[plain]` (test_v1_3_the_zips_directory.py) | 567,430,474 | 567,503,330 | +72,856 | +0.01% |
| fuel | `test_metadata_answers_from_the_zips_directory[plain]` (test_v1_3_the_zips_directory.py) | 433,595,527 | 433,652,863 | +57,336 | +0.01% |
| fuel | `test_gzip_round_trips` (test_v1_3_data_stack.py) | 402,475,602 | 402,531,029 | +55,427 | +0.01% |
| fuel | `test_patched_callbacks_run[plain]` (test_v1_3_matplotlib.py) | 469,042,048 | 469,096,013 | +53,965 | +0.01% |
| fuel | `test_the_fast_reader_builds_zipimports_dict[explicit_dirs]` (test_v1_3_the_zips_directory.py) | 290,481,746 | 290,520,386 | +38,640 | +0.01% |
| fuel | `test_the_fast_reader_builds_zipimports_dict[zip64]` (test_v1_3_the_zips_directory.py) | 290,298,631 | 290,337,011 | +38,380 | +0.01% |
| fuel | `test_the_fast_reader_builds_zipimports_dict[prepended]` (test_v1_3_the_zips_directory.py) | 288,767,138 | 288,804,843 | +37,705 | +0.01% |
| fuel | `test_the_fast_reader_builds_zipimports_dict[cp437]` (test_v1_3_the_zips_directory.py) | 288,919,810 | 288,957,341 | +37,531 | +0.01% |
| fuel | `test_the_fast_reader_builds_zipimports_dict[truncated]` (test_v1_3_the_zips_directory.py) | 287,789,266 | 287,826,179 | +36,913 | +0.01% |
| fuel | `test_the_zip_reader_is_ours_from_the_first_import[plain]` (test_v1_3_the_zips_directory.py) | 283,577,388 | 283,612,735 | +35,347 | +0.01% |
| fuel | `test_guest_has_no_network` (test_v1_2_portable_and_sealed.py) | 256,063,746 | 256,094,555 | +30,809 | +0.01% |
| fuel | `test_kiwisolver_raises_unsatisfiable_constraint[plain]` (test_v1_3_matplotlib.py) | 171,925,141 | 171,946,381 | +21,240 | +0.01% |
| fuel | `test_unbuffered_output_survives_a_hard_exit[plain]` (test_v1_4_embedding.py) | 140,256,169 | 140,276,466 | +20,297 | +0.01% |
| fuel | `test_a_program_sees_real_entropy_and_file_metadata[plain]` (test_v1_4_embedding.py) | 167,363,132 | 167,382,508 | +19,376 | +0.01% |
| fuel | `test_guest_sees_only_its_root` (test_v1_2_portable_and_sealed.py) | 167,491,295 | 167,510,624 | +19,329 | +0.01% |
| fuel | `test_stdlib_c_modules_are_builtin[plain]` (test_v1_1_artifact_set.py) | 167,232,224 | 167,251,279 | +19,055 | +0.01% |
| fuel | `test_run_reads_argv_and_environment_each_call[plain]` (test_v1_4_embedding.py) | 166,893,652 | 166,912,691 | +19,039 | +0.01% |
| fuel | `test_main_starts_as_native[plain]` (test_v1_4_embedding.py) | 166,704,879 | 166,723,915 | +19,036 | +0.01% |
| fuel | `test_run_returns_the_exit_code[plain]` (test_v1_4_embedding.py) | 166,663,934 | 166,682,928 | +18,994 | +0.01% |
| fuel | `test_exit_status_is_a_process_status[plain]` (test_v1_4_embedding.py) | 166,611,383 | 166,630,363 | +18,980 | +0.01% |
| fuel | `test_guest_runs_here[plain]` (test_v1_2_portable_and_sealed.py) | 166,600,091 | 166,619,045 | +18,954 | +0.01% |
| fuel | `test_a_plain_start_grows_at_most_30k_fuel_per_member` (test_v1_3_the_zips_directory.py) | 166,614,395 | 166,633,339 | +18,944 | +0.01% |
| fuel | `test_door_without_a_host_says_so[plain]` (test_v1_4_embedding.py) | 167,429,352 | 167,448,280 | +18,928 | +0.01% |
| fuel | `test_door_round_trips_bytes_through_a_host[plain]` (test_v1_4_embedding.py) | 166,998,172 | 167,017,056 | +18,884 | +0.01% |

**Shrank** (21):

| metric | check | accepted | with A | change | ratio |
|---|---|---|---|---|---|
| fuel | `test_extra_preopens_work_on_the_snapshot[root first]` (test_v1_2_hostile_guest.py) | 850,787,462 | 293,293,766 | -557,493,696 | -65.53% |
| fuel | `test_extra_preopens_work_on_the_snapshot[data first]` (test_v1_2_hostile_guest.py) | 850,787,596 | 293,293,988 | -557,493,608 | -65.53% |
| fuel | `test_door_round_trips_bytes_through_a_host[snapshot]` (test_v1_4_embedding.py) | 83,845,252 | 16,063,898 | -67,781,354 | -80.84% |
| fuel | `test_run_reads_argv_and_environment_each_call[snapshot]` (test_v1_4_embedding.py) | 83,753,704 | 15,974,038 | -67,779,666 | -80.93% |
| fuel | `test_guest_runs_here[snapshot]` (test_v1_2_portable_and_sealed.py) | 83,461,327 | 15,684,107 | -67,777,220 | -81.21% |
| fuel | `test_exit_status_is_a_process_status[snapshot]` (test_v1_4_embedding.py) | 83,462,897 | 15,686,229 | -67,776,668 | -81.21% |
| fuel | `test_run_returns_the_exit_code[snapshot]` (test_v1_4_embedding.py) | 83,514,138 | 15,737,553 | -67,776,585 | -81.16% |
| fuel | `test_the_zip_reader_is_ours_from_the_first_import[snapshot]` (test_v1_3_the_zips_directory.py) | 84,968,781 | 17,193,165 | -67,775,616 | -79.77% |
| fuel | `test_main_starts_as_native[snapshot]` (test_v1_4_embedding.py) | 83,568,707 | 15,794,950 | -67,773,757 | -81.10% |
| fuel | `test_a_program_sees_real_entropy_and_file_metadata[snapshot]` (test_v1_4_embedding.py) | 84,244,771 | 16,478,144 | -67,766,627 | -80.44% |
| fuel | `test_door_without_a_host_says_so[snapshot]` (test_v1_4_embedding.py) | 84,245,826 | 16,490,668 | -67,755,158 | -80.43% |
| fuel | `test_a_forged_frame_is_validated_first` (test_v1_4_embedding.py) | 85,237,945 | 17,487,439 | -67,750,506 | -79.48% |
| fuel | `test_no_cpython_test_module_is_built_in` (test_v1_1_artifact_set.py) | 84,104,832 | 16,364,360 | -67,740,472 | -80.54% |
| fuel | `test_stdlib_c_modules_are_builtin[snapshot]` (test_v1_1_artifact_set.py) | 84,072,241 | 16,332,087 | -67,740,154 | -80.57% |
| fuel | `test_kiwisolver_raises_unsatisfiable_constraint[snapshot]` (test_v1_3_matplotlib.py) | 88,726,065 | 20,999,756 | -67,726,309 | -76.33% |
| fuel | `test_the_fast_reader_builds_zipimports_dict[snapshot]` (test_v1_3_the_zips_directory.py) | 285,688,328 | 218,191,586 | -67,496,742 | -23.63% |
| fuel | `test_sqlite_holds_a_lock_while_it_writes` (test_v1_3_data_stack.py) | 96,778,316 | 40,252,615 | -56,525,701 | -58.41% |
| bytes | `test_binary_is_a_core_wasm_module[snapshot]` (test_v1_1_artifact_set.py) | 70,901,724 | 40,509,812 | -30,391,912 | -42.86% |
| fuel | `test_unbuffered_output_survives_a_hard_exit[snapshot]` (test_v1_4_embedding.py) | 2,884,094 | 1,213,716 | -1,670,378 | -57.92% |
| fuel | `test_fuel_is_exact_across_tool_calls` (test_v1_4_embedding.py) | 93,548,625 | 93,236,738 | -311,887 | -0.33% |
| fuel | `test_fuel_is_exact_across_async_tool_calls` (test_v1_4_embedding.py) | 93,529,167 | 93,238,179 | -290,988 | -0.31% |

Seventeen more plain-binary metrics moved by +0.004% to +0.009%, inside the tolerance
(`metrics-set-A.md`, the last table).

**The upstream suites,** run alone the same way once the worktree was given the main tree's
numpy and pandas tarballs, source trees and kit wheels (links and a copy, removed after; EXECUTED,
425 s; `judge-set-A-upstream.log`, `latest-set-A-upstream.json`, `upstream-set-A.md`): 20 passed,
12 xfailed (the 12 known gaps, each with status `gap`, its recorded finding set matched); the ratchet: lost 0, grew 11.
Every group keeps its `passes` to the test; every class check (`test_upstream_class[*]`) has the
status it has on main.

| group | status | passes accepted | passes with A | fuel accepted | fuel with A | change | ratio |
|---|---|---|---|---|---|---|---|
| `test_upstream_suite[numpy-core]` | pass | 9519 | 9519 | 202,236,158,701 | 203,804,605,587 | +1,568,446,886 | +0.78% |
| `test_upstream_suite[numpy-lib]` | pass | 4825 | 4825 | 131,245,201,865 | 132,073,041,321 | +827,839,456 | +0.63% |
| `test_upstream_suite[numpy-others]` | pass | 7269 | 7269 | 175,268,035,885 | 176,695,168,076 | +1,427,132,191 | +0.81% |
| `test_upstream_suite[pandas-frame]` | pass | 10852 | 10852 | 338,092,146,773 | 342,735,206,074 | +4,643,059,301 | +1.37% |
| `test_upstream_suite[pandas-groupby]` | pass | 22227 | 22227 | 474,737,579,070 | 479,186,377,706 | +4,448,798,636 | +0.94% |
| `test_upstream_suite[pandas-internals]` | pass | 258 | 258 | 16,448,860,826 | 21,193,033,986 | +4,744,173,160 | +28.84% |
| `test_upstream_suite[pandas-io-formats]` | pass | 977 | 977 | 53,762,517,378 | 58,650,022,837 | +4,887,505,459 | +9.09% |
| `test_upstream_suite[pandas-io-parser]` | pass | 3474 | 3474 | 88,661,323,249 | 93,630,566,621 | +4,969,243,372 | +5.60% |
| `test_upstream_suite[pandas-libs]` | pass | 1063 | 1063 | 21,974,631,860 | 26,840,880,542 | +4,866,248,682 | +22.14% |
| `test_upstream_suite[pandas-reshape]` | pass | 2664 | 2664 | 97,971,247,410 | 102,654,019,404 | +4,682,771,994 | +4.78% |
| `test_upstream_suite[pandas-tslibs]` | pass | 590 | 590 | 33,418,914,221 | 38,251,438,940 | +4,832,524,719 | +14.46% |

Each pandas group grows by its one import of pandas (4.4 to 5.0 G); each numpy group by numpy's
(0.8 to 1.6 G; the import, and the collector's work over a heap no longer frozen with pandas in
it, INFERRED). The smallest headroom left under a group's cap is pandas-internals': 21.2 G
against 28 G.

So the lane's growth list is **56 metrics: the 45 above and these 11.**

## Landing notes

Built 2026-10-19 on `spec/069-the-snapshot-pre-imports-no-package`, rebased onto main `b413192`
(046, 047, 055, 068 and 070 landed since the draft). The evidence is in the session scratchpad
folder `069-build/` (logs, probes, stand-ins, the container build), which the lane may copy to
`build/reviews-evidence/069-build/`.

### Commits

- `f20e311` the checks first: (a), (b), (c), (e), (h) with its gap entry, (i), and the edits (f)
  and (g); `paths` gains the constants.
- `fbcae4a` the code and the documents: `PREIMPORT`, `preimport_list`, the two comments, the
  docstrings and the README's reference, the README, the CHANGELOG (0.1.0a7), the roadmap, the
  amendment lines in 023 and 054.
- The commit that carries these notes.

### Seen failing first, on main's set (criterion 1, EXECUTED)

The new and changed checks, run against main's frozen set `s-9d43bf645dfcaa71` (`SHA256SUMS`
`b0c4f376…`) before any code changed (`seen-failing-first.log`): 6 failed, 4 passed, 1 xfailed.
- (a) "modules at start that are not the stdlib's: _cython_3_3_0, _cyutility, cython_runtime,
  dateutil, numpy, pandas, six". `_sysconfigdata__wasi_wasm32-wasi` is no longer named: it is
  CPython's (F6).
- (b) "snapshot start 83,482,875 fuel, plain start 167,474,151: 2.01 times, under 8".
- (c) the recipe defines `… _colorize, numpy, pandas`; (e) MANIFEST's line names them too.
- (g) `HIT pytz` 0 times on the snapshot (`b''`).
- (i) `AttributeError: module 'assemble_artifacts' has no attribute 'preimport_list'`.
- (f) passes, as Decision 6 says (`csv` is in both lists); S7 is its stand-in.
- (h)`[snapshot]` failed with exactly its gap's finding set (`1 finding(s), digest
  7da6e52329c1`) and the gap allowed it (xfailed); `[plain]` passed.

### The stand-ins (criterion 2, EXECUTED)

Each stand-in snapshot was relinked from this build's own step-60 records with the memo's method
(`standins/relink.py`, `standins/snapshot.sh`). Relinking without `-DPREIMPORT` gives the built
`python.wasm` byte for byte (`5ab6bc5d…`), so the method still reproduces the set. Each scratch
set is the built set with the stand-in's two binaries and its own `SHA256SUMS`
(`standins/judge_standins.txt`, `standins/source_standins.txt`, `standins/s9.txt`).

| stand-in | (a) | (b) | (c) | (e) | (f) |
|---|---|---|---|---|---|
| S1, `numpy` added | fails: "numpy" | fails: 6.20 times | fails (the `#define` with numpy) | passes | passes |
| S2, `six` added | fails: "six" | passes | fails (the `#define` with six) | passes | passes |
| S4, `random` added | passes | passes | fails (the `#define` with random) | passes | passes |
| S5, a literal list in the writer | | | fails: "carries its own PREIMPORT list" | | |
| S6, `-DPREIMPORT` in step 60 | | | fails: "60_link.sh: overrides PREIMPORT" | | |
| S7, the plain reactor as the snapshot | fails: io, json, csv, re, _colorize missing | fails: 1.00 times | | passes | fails: `False ['-c', 'a']` |
| S8, `run_private("import six")` after the list | fails: "six" | passes | passes | passes | passes |

S9: the derivation over a scratch zip holding `json`, `os`, `six`, `dateutil` and a dist-info
gives `['dateutil', 'six']`, and the guard fails: "the zip's non-stdlib names lack ['numpy',
'pandas', 'host']". The reader's unit test (i) covers a recipe with no `#define` and one with
two; each exits naming `recipes/reactor_main.c`.

### The build (criterion 3, EXECUTED)

`rm -rf build`, then `scripts/build.sh --plain`: sixteen steps in 7 min 44 s (`build-069.log`).
- `python.wasm` 41,099,442 bytes, `5ab6bc5d0637000a…`: the same size as main's set
  (`18595c7f…`), a different hash (the shorter constant).
- `python-snapshot.wasm` 44,633,705 bytes, `1a7242a7a8b518f4…`, against main's 75,083,688
  (−30,449,983).
- `python-stdlib.zip` 22,197,173 bytes, `02026895…`, the same as main's.
- MANIFEST `490db800…`: it differs from main's only in `x-preimport` (now `encodings, io, os,
  sys, json, csv, re, _colorize`) and the three recipe lines (`reactor_main.c`,
  `assemble_artifacts.py`, `80_snapshot.sh`).
- **`SHA256SUMS` `4530b6ce387db3c90ca0fbf87acca099678999f402da3fc5796ca54b1fde171f`.**

Criterion 3's draft figures (40,509,812 bytes, `bf89b904…`) were on the draft's base; the base
moved (046, 047, 055), as criterion 3 allowed. Spec 071 is building and also edits
`recipes/reactor_main.c`: whichever lands second rebases, rebuilds and restates these hashes
(Decision 11).

### The same bytes from a second host (criterion 4)

A clean clone of `fbcae4a`, built from an empty `build/` in a `linux/arm64` container (the
research image `wp040-arm64`: Debian 13, uv 0.9.22; `linux/out/host.txt`,
`linux/out/build-output.txt`): sixteen steps in 7 min 35 s. Its `SHA256SUMS` equals macOS's,
every line (`diff`; the file's SHA-256 is `4530b6ce…` on both). As in 046 and 047, the container
first installs Debian's `python3` (3.13.5) for HarfBuzz's step 37 (023's unpinned host input, a
known follow-up). The x86_64 rebuild was not run here; the release dry run runs it.

### Measurements on the built set (EXECUTED, the judge's driver; `start_cost.txt`, `shutdown_cost-*.txt`, `plot_cost-*.txt`)

| | main's set | this build |
|---|---:|---:|
| snapshot `-c pass` | 83,482,875 | 15,622,338 |
| snapshot `os._exit(0)` | 2,654,588 | 968,103 |
| snapshot `import numpy` | 83,506,469 | 776,261,542 |
| snapshot `import pandas` | 83,506,655 | 4,600,243,824 |
| plain `-c pass` | 167,474,151 | 167,464,294 |
| plain `import pandas` | 4,917,448,956 | 4,917,407,278 |
| a session's `shutdown()` after `pass`, snapshot | 305,764,603 | 42,888,965 |
| the same after `import pandas`, snapshot | 305,766,344 | 308,435,842 |
| the same, plain reactor, after `pass` / `import pandas` | 29,512,562 / 303,761,596 | 29,507,368 / 303,784,115 |
| plot with PNG, snapshot, fresh / kept font cache | 7,557,685,529 / 5,567,304,558 | 8,782,947,963 / 6,792,258,926 |

- Check (b)'s ratio is 10.72 (167,464,294 against 15,622,338).
- **The session close (for 055's README, as the lane asked):** undoing the freeze now costs
  about 27 M on a bare session (42.9 M against 15.6 M for a run), against about 222 M before.
  The review predicted about 28 M against 225 M. A session that imported pandas still pays about
  308 M at close, because its shutdown finalizes pandas. The README states all four figures.
- **The wheel:** the snapshot deflates about 11 MB smaller, as the memo measured. The landing
  lane's wheel build records the exact size.
- 065's adaptation A1 (a no-op `_reset_cache` on the `ctypes` stand-in, needed because the
  snapshot pre-imported numpy) has no reason left on this snapshot. 065 is not drafted on main;
  its drafter measures on this snapshot (Decision 11). No 065 allowance exists to move (N4).

### The judge (criteria 5 and 6, EXECUTED)

The fast tier, then the full `uv run pytest -n 3`, in the worktree on the built set, no
`--accept`. The upstream kit was fetched with `tests/upstream/fetch.py`; the source trees are this
build's own (`full-1.log`, `latest-full-1.json`, `metrics-full-1.md`):

```
=========== 1740 passed, 11 skipped, 15 xfailed in 527.32s (0:08:47) ===========
ratchet vs 1dbf2c831f: lost 0 · absent 1 · unrun 0 · unrun locally 2 · gained 5 · grew 38 ·
judge changed: tests/checks/test_rules.py, tests/checks/test_v1_1_artifact_set.py,
tests/checks/test_v1_3_data_stack.py and 4 more
RED: 1 accepted check(s) absent (retire them with --retire); 38 metric(s) grew
```

- **Lost 0.** (f) and (g) are restated and pass. The absent one is the removed
  `test_snapshot_preimports_the_stack`, retired with `--retire`.
- **The 2 unrun locally** are this worktree's needs: the oracle, and the prior-art clones.
- **The 5 gained:** (a), (b), (c), (e), and (h)`[plain]`. (h)`[snapshot]` is a gap (15 xfailed:
  main's 14 and this one).
- **Every upstream group keeps its `passes`, and every class check its status.**
- **Grew 38**, each with its cause (fuel; main's accepted value to this build's):
  - **pandas imported in the run, +4.49 G to +4.52 G (10):**
    `test_dotted_builtins_keep_their_import_names[snapshot]`,
    `test_gb18030_is_never_silently_wrong[snapshot]`,
    `test_packages_carry_their_metadata[snapshot]`,
    `test_read_html_uses_lxml_by_default[snapshot]`,
    `test_the_pandas_tz_job_matches_native[snapshot]`,
    `test_numpy_and_pandas_are_builtin_at_manifest_versions[snapshot]`,
    `test_callbacks_job_matches_native[snapshot]`,
    `test_the_guest_package_round_trips_through_the_door[snapshot]`,
    `test_a_pandas_warning_names_the_callers_line[snapshot]`,
    `test_ctypes_stand_in_names_what_packages_import[snapshot]`.
  - **numpy or matplotlib imported in the run (3):** `test_npy_files_round_trip[snapshot]`
    +0.92 G; `test_plot_line_job_matches_native[snapshot]` +1.22 G;
    `test_savefig_rejects_a_negative_dpi` +1.22 G.
  - **lxml's runs, which now import the stdlib modules pandas used to load (7):**
    `test_isoschematron_is_left_out_and_schematron_validates[snapshot]` +98 M;
    `test_lxml_is_builtin_at_manifest_versions[snapshot]`,
    `test_files_by_path_in_grants[snapshot]`, `test_libxml2_has_no_zlib[snapshot]` and
    `test_stylesheets_and_entities_reach_only_grants[snapshot]` +76 M each;
    `test_the_readmes_encoding_workaround_reads_what_iconv_cannot` +72 M;
    `test_encodings_are_wasi_libcs_as_documented` +55 M.
  - **other stdlib modules pandas used to load (7):** `test_stdlib_debugging_tools_import`
    +391 M; `test_resources_read_as_zipfile_reads_them[snapshot]` +221 M;
    `test_a_zone_load_does_not_grow_with_the_zip[snapshot]` +184 M;
    `test_uncaught_errors_print_as_native[snapshot]` +25 M;
    `test_metadata_answers_from_the_zips_directory[snapshot]` +25 M;
    `test_regex_features_job_matches_native[snapshot]` +12 M;
    `test_patched_callbacks_run[snapshot]` +8 M.
  - **the upstream groups (11):** each pandas group pays pandas' import once: pandas-frame
    +4.54 G, pandas-groupby +4.69 G, pandas-internals +4.73 G, pandas-io-formats +4.83 G,
    pandas-io-parser +4.90 G, pandas-libs +4.84 G, pandas-reshape +4.68 G, pandas-tslibs
    +4.80 G. Each numpy group pays numpy's import (about 0.69 G) and the collector's work over
    its unfrozen heap (0.20 to 0.37 G, measured by the build review): numpy-core +1.02 G,
    numpy-lib +0.70 G, numpy-others +1.33 G.
- **Shrank 32:**
  - 26 snapshot or `bytes` metrics: the snapshot's 75,083,688 to 44,633,705 bytes; about
    −67.8 M on each bare snapshot run; −556 M on each of the two
    `test_extra_preopens_work_on_the_snapshot` runs; regex's two checks −27 M; and others.
  - 6 plain-reactor or tool-call metrics, by 0.01% to 0.26%.
- **The plain reactor grows nowhere.** On this base its fuel moves by −0.06% to −0.00%
  (`-c pass` 167,474,151 to 167,464,294). The draft's +0.011% (Decision 4) was on the draft's
  base. The data moved by the shorter constant moves the other way here. The cause is the same
  (alignment-sensitive literals); only the sign differs, and nothing of the plain binary's needs
  accepting.

### The lane's acceptance (criterion 9)

```
uv run pytest --accept "spec 069: the snapshot pre-imports no package (decision 34)" \
  --accept-judge "spec 069: (a) test_the_snapshot_pre_imports_no_package (the stdlib rule, through paths.is_stdlib_or_reactor, naming a refused module that the zip carries as a package in the zip) and (b) test_the_snapshot_starts_cheaper_than_plain replace test_snapshot_preimports_the_stack; (c) test_the_pre_import_list_is_the_stdlib_bootstrap; (e) test_manifest_names_the_pre_imports; (h) test_run_keeps_an_unclosed_files_bytes and its gap entry in tests/known_gaps.toml (the frozen heap loses an unclosed file's bytes on run; closer spec 073 via the roadmap); (i) test_the_pre_import_list_is_read_from_the_recipe; (f) test_runner_runs_the_plain_reactor tells the binaries apart by csv; (g) test_the_import_path_comes_after_the_runtime counts HIT pytz 2 on both binaries (spec 054's numbers restated); tests/harness/paths.py: PREIMPORT, REACTOR_MODULES, CPython's unlisted names and prefix, is_stdlib_or_reactor" \
  --accept-growth "decision 34 (the owner, 2026-10-18): the default snapshot pre-imports no package (spec 069). Every snapshot run that imports pandas pays it in the run (+4.49 to +4.52 G, 10 checks), numpy +0.92 G, matplotlib +1.22 G; lxml's runs and the debugging-tools, resources, zone, traceback, metadata, regex and kiwisolver runs import the stdlib modules pandas used to load (+8 to +391 M); each pandas upstream group pays pandas' import once (+4.54 to +4.90 G); each numpy group pays numpy's import and the collector's work over its unfrozen heap (+0.70 to +1.33 G). The snapshot is 30.4 MB smaller and a bare run 5.3 times cheaper." \
  --retire tests/checks/test_v1_3_data_stack.py::test_snapshot_preimports_the_stack
```

### The confirmation's nits

- **N1, taken:** (i) lives in `tests/unit/test_build_scripts.py`, beside the other
  `assemble_artifacts` tests.
- **N2, taken:** the roadmap's 073 line is its own paragraph, "Follow-up from spec 069's
  pre-build review (… the lane's ruling on its F1)", not under the owner's follow-ups. Line 94
  says "decision 34", and the `full` profile is recorded beside it.
- **N3, taken:** `paths.CPYTHON_UNLISTED_NAMES` (two names) and `paths.CPYTHON_UNLISTED_PREFIXES`
  (one prefix), with the predicate `paths.is_stdlib_or_reactor`, in place of one tuple called
  `CPYTHON_UNLISTED`.
- **N4, answered:** 065 has not landed and carries no allowances, so nothing of 065's moves in
  this judge.

### Departures from the specification, each with its reason

1. **The plain reactor does not grow** (Decisions 4 and 7 said +0.011% to 0.017%). On this base
   it moves by −0.06% to −0.00%, so the growth reason names no plain metric. The cause is the
   same layout shift; only its sign differs on the rebased base.
2. **The growth list is 38 metrics, not 56.** Same kinds, rebased: the 29 plain metrics are gone
   (1), and lxml's (046) and regex's (047) checks join, since their runs now import what pandas
   used to load. The snapshot pandas jobs agree with the draft's within 1% (+4.49 to +4.52 G,
   against +4.49 to +4.53 G). The upstream groups do not, and that is explained here, as criterion
   6 asks. The pandas groups grow by +4.54 to +4.90 G against the draft's +4.45 to +4.97 G, within
   6%. The numpy groups grow less: numpy-core +1.02 G against +1.57 G, numpy-lib +0.70 against
   +0.83, numpy-others +1.33 against +1.43. A numpy group pays numpy's import (about 0.69 G) and
   the collector's work over its unfrozen heap (0.20 to 0.37 G, measured by the build review,
   which froze numpy's heap after its import). The gap from the draft is the accepted baseline,
   which moved with 046, 047 and 055 (the build review, F1).
3. **Criterion 3's hashes and sizes are new**, as criterion 3 allowed: the base moved. The
   snapshot is 44,633,705 bytes, not 40,509,812; lxml and regex are in it.
4. **N1 and N3** (above): (i)'s file, and the constants' names.
5. **The README's pandas advice speaks of sessions in the present tense.** 055 has landed, which
   was Decision 8's condition.
6. **The README's session-close figures are re-measured** (the lane's request). Decision 8 did
   not list them, because 055 had not landed when 069 was drafted.
7. **Check (a) has one rule and names its packages in it** (the build review, F2). The stdlib
   rule refuses any other top-level name. The zip's non-stdlib names no longer have an assertion
   of their own, which could never fail after the rule. Instead they label the rule's message: a
   refused name the zip carries is written "six (a package in the zip)". Their guard (numpy,
   pandas and host must be among them) runs first, and S9 shows it failing. Re-run on the
   stand-ins (`standins/f2_message.txt`):
   - S1: "numpy (a package in the zip)".
   - S2 and S8: "six (a package in the zip)".
   - Main's set: "_cython_3_3_0, _cyutility, cython_runtime, dateutil (a package in the zip),
     numpy (a package in the zip), …".
   - S7: the list did not run.

### For the build review

The diff is `b413192..HEAD`. The fast tier and the full judge above are this worktree's. The
stand-ins can be re-run from `069-build/standins/` against this worktree's `build/`.

### Revised against the build review (2026-10-19)

The build review: "lands once F1 is written in"; the lane asked for F2 to F4 too.
- **F1, written in:** a numpy group's growth is numpy's import (about 0.69 G) and the
  collector's work over its unfrozen heap (0.20 to 0.37 G, the review's measurement). The gap
  from the draft is the accepted baseline moving with 046, 047 and 055. This is now in departure
  2, in the upstream line of "Grew 38" and in `--accept-growth`. The pandas-heap wording is gone.
- **F2, written in:** check (a) has no assertion that cannot fail. The separate `held`
  assertion is removed. The zip's non-stdlib names now label the stdlib rule's own message, as
  "six (a package in the zip)", and their guard runs first (departure 7, with the stand-ins'
  messages). `--accept-judge` says so.
- **F3, written in:** the pandas runs grow by +4.49 to +4.52 G (the largest is +4,524,377,786).
- **F4, written in:** `recipes/reactor_main.c`'s pinned-block comment is wrapped to the file's
  width. The new lines are at most 99 columns; the two old lines at 100 and 102 are main's.
  - It changes the recipe's hash in MANIFEST, so steps 60 to 90 ran again
    (`build-069-f4.log`).
  - `python.wasm` (`5ab6bc5d…`), the snapshot (`1a7242a7…`) and the zip are byte for byte the
    same; only MANIFEST moved (`8de36679…`).
  - **`SHA256SUMS` is now `1889459ead8b9b93bfd3ee7e1caa3ef8efe535c2f7abbd6489b9902feae216b7`.**
    The lane rebuilds at landing anyway.
- **Re-run:** check (a) on the built set (passes), on S1, S2, S7 and S8 and on main's set
  (above), and the fast tier with `-n 3` (`fast-2.log`): 1704 passed, 10 skipped, 1 xfailed; ratchet lost 0, absent 1 (the retired check), gained 5, grew 20 (the fast tier's share of the 38), as before the revision.

**Landed 2026-10-19** through the lane, after spec 076. The lane rebased the branch onto main
`3ea0582` (spec 076 since `b413192`) with no conflict; its diff equals the reviewed diff at `0fa9f60`
line for line (EXECUTED, `build/lane-069/delta.txt`, empty). The pre-build review with its
confirmation and the build review with its confirmation
(`../reviews/069-the-snapshot-pre-imports-no-package-spec-2026-10-18.md`,
`../reviews/069-the-snapshot-pre-imports-no-package-build-2026-10-19.md`) were committed on the
detached HEAD as `96cf575`. **The main tree's full build from pins** (16 steps, 8 min 28 s) gave
`SHA256SUMS` `1889459ead8b9b93bfd3ee7e1caa3ef8efe535c2f7abbd6489b9902feae216b7`, byte for byte the
builder's: `python.wasm` `5ab6bc5d…` (41,099,442 bytes), the snapshot `1a7242a7…` (44,633,705, 30.4
MB smaller than 055's), the zip unchanged (EXECUTED, `build/lane-069-build.log`). The set is frozen
read-only as `build/sets/s-1a7242a7a8b518f4`. The full judge there, serial: `wasi_python v1: 480/497
pass · 15 gap · 2 blocked · 0 fail (unit suite 1270/1272, 2 skipped)`, `1750 passed, 4 skipped, 15
xfailed in 698.01s` (the fifteenth gap is check (h)'s, closed by spec 073), accepted with
`--accept-judge`, `--accept-growth` (the confirmed reason) and `--retire
tests/checks/test_v1_3_data_stack.py::test_snapshot_preimports_the_stack` as `fc9282b`, history line
71 (EXECUTED, `build/lane-069-accept.log`). The rules tier passed (40/40, unpiped); main
fast-forwarded. Spec 071 lands next and restates criterion 3's hashes on this set; spec 065 drops its
adaptation A1.

