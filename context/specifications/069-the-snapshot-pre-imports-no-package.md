# 069 — The snapshot pre-imports no package

- **Status:** drafted 2026-10-18; awaiting its pre-build review. Drafted on
  `spec/069-the-snapshot-pre-imports-no-package` from main `4a94c14`. It changes the artifact set
  and the build recipe, so it is reviewed once before it is built (constitution §5.6). The
  draft's evidence (variants A and B rebuilt from the frozen set's objects, A's module list, and
  the full judge run against an artifact set holding A) is in the main tree, git-ignored, under
  `build/reviews-evidence/069-spec/` (Evidence, below).
- **Date:** 2026-10-18
- **Owner:** Clay Gendron
- **Kind:** **build-class** (§5.7): it changes `recipes/reactor_main.c` (the `PREIMPORT`
  default and two comments), `scripts/assemble_artifacts.py` (the `x-preimport` line read from
  the recipe) and one comment in `scripts/steps/80_snapshot.sh`. It is also a judge change
  (Decision 5: one check removed, four added, two edited, two harness constants), and it
  changes `src/wasi_python/` docstrings (four sentences), `README.md` (the facts, the advice, the
  import path's text, the generated reference) and `CHANGELOG.md`. It changes no public name,
  signature, field, default or option: **`tests/public_api.txt` does not change** (Decision 9).
  It changes no pin, no patch and `downloads/SHA256SUMS` not at all. **The lane accepts it with
  `--accept-judge` and `--accept-growth`** (Decision 7).
- **Depends on:** 003 (the reactor, `wizer.initialize`, step 80), 005 (3.15: `_colorize` in the
  list), 008 (start is unmetered), 049 (the public API frozen; what is promised), 054 (the import
  path; its pinned `HIT pytz` numbers, which this specification restates as 054 requires); all
  landed. It interacts with 046, 047, 055 and 063, which are in flight (Decision 11).
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
   specification may pre-import a package even with a judge change: the module check
   (Decision 5a) refuses any non-stdlib top-level name, and changing that rule needs the owner
   to reverse decision 34. *Reason:* the decision is "for every package now and later"; a rule
   that a checklist states and nothing enforces is broken by the first package that wants its
   latency back.

3. **One source for the list.** The `#define` in `recipes/reactor_main.c` is the only place the
   list is written. `scripts/assemble_artifacts.py` stops carrying its own copy
   (`PREIMPORT = "encodings, …, numpy, pandas"`, line 89): it reads the `#define`'s string from
   the recipe with one regular expression, drops the leading `import `, and writes
   `x-preimport encodings, io, os, sys, json, csv, re, _colorize` to MANIFEST exactly as today's
   format. It fails the build (`SystemExit` naming the file) when the line is missing or
   matches more than once. *Reason:* today the two copies agree only by care; no check reads
   `x-preimport` (`paths.parse_manifest` skips every `x-` line), so a drift would ship a
   MANIFEST that misstates the snapshot.

4. **The rest of the recipe stays.**
   - `wizer.initialize` keeps `gc.collect(); gc.freeze()` after the imports, the pinned clocks
     and entropy, and `__wasilibc_reset_preopens`. Two comments change: the file's header
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
     The constant is read only by `wizer.initialize`; the cause is the data segment's layout
     after it, which shifts every later static address (INFERRED; the builder may name a more
     exact cause if it finds one, but need not). It is above the judge's fuel tolerance of 0.01%
     (`scoreboard.FUEL_TOLERANCE`), so 29 plain-binary metrics show as grown in the run below,
     each by 0.011% to 0.017%, and Decision 7's growth reason names them. *Reason for accepting
     it rather than padding the string:* the figure is exact and deterministic, it is a hundredth
     of a percent, and holding a constant's length to keep fuel equal would be a recipe that
     guards nothing.

5. **The checks.** Each is written before the code and seen failing first on main's set
   (Acceptance criteria). Each guest check runs through the judge's driver.
   - **a. `test_the_snapshot_pre_imports_no_package`** (`tests/checks/test_v1_3_data_stack.py`,
     v1.3; it replaces `test_snapshot_preimports_the_stack`). One snapshot run of a probe whose
     first statement reads `sys.modules` and prints, as JSON, its keys and
     `sorted(sys.stdlib_module_names)`. Host-side:
     - every top-level name of a key is in the printed stdlib names or in
       `paths.REACTOR_MODULES` (`"__main__", "_reactor", "_zip_directory", "_zip_resources"`);
       the message names each other name;
     - the **package names** are computed from the artifact set's own zip: the top-level names
       of its members (a folder's first part, or a module file's stem at the root), minus the
       stdlib names, minus `REACTOR_MODULES`. The check asserts that this set holds `numpy`,
       `pandas` and `host` (so the derivation is not vacuous), and that no top-level name in
       `sys.modules` is in it, naming each;
     - every name of `paths.PREIMPORT` is in `sys.modules` (the list really ran).

     It records the probe's fuel. *Reason:* the stdlib rule needs no list of packages, so it
     holds for every package a later specification adds, pure or compiled in, without anyone
     remembering to extend it; the zip-derived names make the failure message name the package,
     and cross-check the rule against the set actually shipped. `tests/upstream/packages.toml`
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
   - **S7, the snapshot replaced by the plain reactor** (a scratch set whose
     `python-snapshot.wasm` is a copy of `python.wasm`): (f) fails (both print `False`); (a)
     fails (`csv`, a name of `paths.PREIMPORT`, is missing); (b) fails (1.0 times).
   - **S4, a stdlib module added** ("… _colorize, random"): (a) and (b) pass, (c) fails. This
     shows that even a stdlib change to the list is a judge change, as Decision 2 says.
   - **S5, a second copy:** `scripts/assemble_artifacts.py` with a literal `PREIMPORT = "…"`
     restored: (c) fails.
   - **S6, a step passing `-DPREIMPORT`** (a line added to `scripts/steps/60_link.sh`): (c)
     fails.

7. **The fuel and bytes that move.** Measured by the full judge run against an artifact set
   holding A's two binaries ("The judge run against A", below; EXECUTED; the built set differs
   from it only in MANIFEST and SHA256SUMS, which no metric reads). The lane's acceptance is
   `uv run pytest --accept "spec 069: the snapshot pre-imports no package" --accept-judge
   "<the judge files of Decision 5>" --accept-growth "<the reason below>"`.
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
     +0.8 to 1.6 G). The plain reactor grows by 0.011% because
     the shorter PREIMPORT constant moves its data layout. The snapshot is 30.4 MB smaller and a
     bare run 5.3 times cheaper." The judge reason names Decision 5's files.
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
     "`import pandas`, snapshot: 4.63G guest instructions (0.81 s, benchmark fact); the
     snapshot pre-imports no package (decision 34)". The plot row's "matplotlib not
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
     embedder who builds its own set can do: `PREIMPORT` is one `-D` flag on step 60's compile
     (the memo, option 6); that is not a product promise.
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
   before (numpy about 0.7G), so a `fuel=` cap set for a pandas job on the snapshot needs that
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
    embedder asks". Amendment lines, one each, dated, in the landed specifications that stated
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
      cost nothing then) are restated by 055's builder on 069's snapshot if 069 lands first; its
      E5b resident figure (37 MiB after a pandas turn) does not change in kind. The README's
      advice (Decision 8) names sessions as "planned" until 055 lands; 055's builder turns the
      word into a present-tense sentence.
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
tests/harness/paths.py          PREIMPORT, REACTOR_MODULES (Decision 5d, 5a)
tests/checks/test_v1_3_data_stack.py   (a) replaces test_snapshot_preimports_the_stack; (b)
tests/checks/test_rules.py             (c)
tests/checks/test_v1_1_artifact_set.py (e)
tests/checks/test_v1_4_embedding.py    (f), (g)
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
   failing against S7. The landing notes quote each failure's one line.
2. **The stand-ins (Decision 6).** S1, S2, S4, S5, S6 and S7 each give exactly the outcomes Decision
   6 lists; the landing notes give each check's line per stand-in.
3. **The build from empty.** `scripts/build.sh` from an empty `build/` with the downloads
   present produces the set; step 80 prints the snapshot's size and hash; the snapshot is
   40,509,812 bytes and its SHA-256 begins `bf89b904f9760f94` (this draft's EXECUTED
   rebuild, if no other change to the recipe or the zip lands first; otherwise the landing notes
   state the new figures and why). `python.wasm` is 36,916,497 bytes, SHA-256 beginning
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
   of Decision 7, and the release dry run (rule 6b) passes on all three systems before the next
   tag.

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

Not built yet.
