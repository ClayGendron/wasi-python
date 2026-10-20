# Review of 066 — the compiled packages' own tests in the release (the specification, before build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I wrote none of the draft or its
  drafting evidence. I read `AGENTS.md`; the constitution §5.1, §5.2, §5.6, §5.7, §6, §7;
  `context/reviews/README.md`; specs 063 and 065 (both landed), and 065's pre-build review;
  `tests/harness/upstream.py`, `tests/upstream/drive.py`, `tests/upstream/{numpy,pandas}.toml`,
  `tests/upstream/packages.toml`, `tests/release_shards.toml`, `tests/harness/shards.py`'s
  closer rule, on main `1ce7381`; the draft and
  `context/research/2026-10-20-the-packages-own-tests-drafting/`. I read the pinned trees the
  draft rests on, as text only: `build/lxml-6.1.3`, `build/matplotlib-3.11.2`,
  `build/pillow-13.0.0`, `build/kiwisolver-1.5.1` (the build's patched trees), and the tarballs
  in `downloads/` with `tar -t`. Time box: 45 minutes (a build-class specification).
- **Reviewed:** `spec/066-the-compiled-packages-own-tests` at `d619e4f` (the draft), drafted from
  `1ce7381`. The diff touches only `context/` (13 files, 1,361 insertions; READ).
- **Run:** none. A pre-build review of a context-only diff; the brief forbade guests, so no
  release workflow was dispatched and no outcome or fuel below is EXECUTED.
- **Re-ran:** `uv run pytest tests/checks/test_rules.py -k spec -q -p no:cacheprovider` in the
  066 worktree, `build/lane.lock` absent → 3 passed, 41 deselected, exit 0
  (`rules-spec.txt` beside this file). Also read, not run: `gh run view 39371419248 --json jobs`
  (the job start and end times).

## The drafter's questions, ruled

- **(a) Survey first, then a delta.** The structure can be confirmed now; the numbers cannot.
  §5.2 says what cannot yet be decided waits on a memo that names the experiment. Every group,
  cap, shard, class and member here is INFERRED, so those parts wait. The families, the driver,
  the keys, the guard, the tie and the shard rule rest on READ facts and are decided. So the
  form is allowed **once Decision 1 is tightened (M1)**: the survey is a research step with its
  own time box and a stand-in driver from a scratch copy. It is written as an EXECUTED memo
  before any check, TOML or harness line is committed. Its delta then always goes to a
  confirmation round, not only on three triggers. 065 had both a memo and a confirmation round,
  and that is the precedent. Two of this review's findings (H1, H2) are design facts a survey
  would also have found. That is the cost of drafting before measuring.
- **(b) Budgets and shards.** 3×10¹² total and 480 G per group are sound bounds. 480 G is
  pandas-groupby's accepted 480.03 G (`accepted.json`, READ). The provisional caps sum to
  3.565×10¹² (arithmetic checked), so Decision 1's escalation is real. But the job-count premise
  is wrong (L5): the base run had 22 jobs running at once, and the binding limit was macOS's
  five slots. The lane's cost is not stated (L6). The conclusion, that three Linux shards end
  before the macOS leg, still holds (INFERRED).
- **(c) One family per package, and a second driver.** Sound. A family per package keeps
  numpy's, pandas' and CPython's stages byte-identical, and criterion 6 proves it.
  `package_drive.py` keeps `drive.py`'s bytes and so numpy's fuel. The kit and the product share
  only `packaging` (`kit.txt` against the product's top-level names, READ), and the draft
  handles it. The shared code under the second driver needs its keys and guard written down
  (M2).
- **(d) lxml.** Not ready as drafted (H1). pytest collects more than lxml's own runner, and the
  `test_suite()` check proves the wrong direction. Two of the not-selected reasons are also
  wrong or imprecise (L3).
- **(e) The `matplotlib.testing` exception.** Sound. No module of matplotlib or mpl_toolkits
  outside `tests/` and `testing/` imports `matplotlib.testing` (grep of the patched tree, READ).
  So no product code path can pass against the stage's copy. The exception admits only
  upstream's test support, built from the same pinned and patched tarball.
- **(f) scipy's closer moves to 095.** Right in kind, but incomplete (L7). 044 also names
  spec 066, for scikit-learn. And the number must sit in the roadmap's `Reserved:` paragraph
  before any branch can name it.
- **(g) The new CI inputs.** Sound. The sizes are as stated: 32,660,610 and 47,058,631 bytes.
  None of the three large tarballs has a symlink, a name that differs only by case, or a
  non-ASCII name (`tar -tv`, READ). They are already pinned and already build inputs. On a judge
  runner they are only unpacked with the `data` filter, patched and copied. The threat-model
  review sees them, as the draft says.

## Acceptance criteria against evidence

1. The rules — not yet met; a design to build. Missing from the list: the guard's shared-code
   cases (M2) and lxml's selection in both directions (H1).
2. The stream and the guard on fixed streams — partly specified. The stream lines that would
   carry "a product module with a `__file__` outside the zip" are not defined (M2).
3. The survey memo, EXECUTED — to come. M1 changes when it comes.
4. TOML, lists and gaps complete — to come. The classes' honesty depends on M3, H2 and L1.
5. Fuel repeats — sound. Restage between the two runs (N1).
6. numpy, pandas and CPython do not move — sound. The stage-manifest hash is the right proof.
7. to 9. Shards, fetch, tie — sound, and the same as 063's and 065's patterns.
10. `packages.toml` — sound as a check. The plan behind it is incomplete (L7).
11. to 13. Full judge, branch dry run, lane dry run — sound.

## What holds (READ unless labelled)

- The table's staged counts: matplotlib has 94 `test_*.py` modules and 2,522 staged files of
  32.70 MB (`tar -tv`). lxml's `test_suite()` functions name exactly 11 `doc/*.txt` files
  (`elementsoup.txt` is commented out) and 6 `html/tests/*.txt` files.
- `LOCAL_FREETYPE_VERSION = '2.14.3'` (`matplotlib/__init__.py:1364`).
  `tol += 0.06` when `sys.maxsize <= 2**32` (`testing/decorators.py:354`).
- Carried patches exist for matplotlib, Pillow, kiwisolver and regex (two), so the tie means
  something for four of the six.
- `judge_group`'s current guard is name-based (`"tests" in name` or `pandas.conftest`).
  `drive.py` emits `M` lines only for `/upstream/tests/`. Both facts matter for M2.

## Findings, most severe first

1. **H1 — lxml under pytest is not "lxml's own less a named part"** (draft Decisions 7 and 14).
   pytest collects every `unittest.TestCase` subclass in a module's namespace. Underscore
   names, imported names and the classes `test_suite()` leaves out are all collected.
   lxml's `tests/test_elementtree.py` has four abstract bases with `etree = None` and no
   `__test__ = False`: `_ETreeTestCaseBase` (274 `test_` methods), `_ElementSlicingTest`,
   `_XMLPullParserTest` and `_C14NTest`. lxml's runner never runs them.
   `html/tests/test_feedparser_data.py` builds `FeedTestCase(fn)` per data file inside
   `test_suite()`. pytest instead makes `FeedTestCase('runTest')`, which opens a file named
   `runTest`. Decision 14's `ast` check proves only that what `test_suite()` adds, pytest
   collects. It does not prove the reverse.
   Failure: about 300 `AttributeError: 'NoneType' object has no attribute …` failures, plus one
   `FileNotFoundError: 'runTest'`, appear as findings. The easy way out is a class whose
   match is `'NoneType' object has no attribute`. That would be a convenience class, and it
   would also hide real `None` errors in lxml's own tests (AGENTS rule 4).
   Fix text: Decision 7 makes pytest's selection equal lxml's in both directions.
   Option (i): `package_drive.py` keeps only the collected classes each module's
   `test_suite()` names. The names come from the same `ast` read, written into the group's
   JSON. The rules fail if pytest's collected class set (from the `C` lines) differs from it.
   Option (ii): each class pytest collects and `test_suite()` does not name is a
   `not_selected` entry by class node id. Its reason is "an abstract base (`etree = None`) or a
   data-driven case lxml's runner builds itself; lxml's own runner never runs it as collected".
   The rules check that the entry is exactly that difference. Either way, criterion 1 gains a
   variant: a staged module with an uncollected-by-lxml `TestCase` that is not named fails.
   `FeedTestCase`'s data cases are named as not run, with their reason. lxml's own runner
   also runs none of them while `lxml.html.clean` is absent.

2. **H2 — Pillow's `Tests/oss-fuzz/` reason is false** (draft Decision 8, the Pillow row).
   `Tests/oss-fuzz/test_fuzzers.py` imports `fuzzers`, `packaging`, `pytest`, `PIL` and
   `Tests.helper`. `fuzzers.py` imports only `io`, `warnings` and `PIL`. `atheris` is imported
   only by `fuzz_pillow.py` and `fuzz_font.py`. pytest never collects those: they do not match
   `test_*.py`. `test_fuzzers.py` sends every file under `Tests/images` (1,060 files, crash
   samples included) through Pillow's decoders, and the 37 files of `Tests/fonts` through
   FreeType. These
   are the tests the Problem section names: a wrong cast or a 32-bit overflow in compiled code.
   Failure: the release leaves out Pillow's most relevant robustness tests, with a reason that
   is not true, and closes it with this specification itself.
   Fix text: select `Tests/oss-fuzz`. Its one need is the sibling import `fuzzers`, so add
   `Tests/oss-fuzz` to Pillow's `sys_path` (Decision 5 already allows this case). Its
   `valgrind_known_error` mark applies only when libjpeg-turbo is present, and the product is
   zlib-only. If the survey finds a real blocker, the row states that blocker as measured.
   This is rule 4's "an honest reason, never a convenience".

3. **M1 — Decision 1's confirmation round must be unconditional, and the survey must come
   before any judge code** (draft Decision 1). As drafted, only three triggers go back to the
   lane. Everything else is "written in" by the builder and first seen by the build review.
   That covers group splits, shard moves, new not-selected rows, dropped classes and every
   class's members. In 050 and 065 those were exactly what the pre-build review judged. And
   "run once … through the judge's own driver" means writing the driver, staging and keys
   before the numbers that decide them exist.
   Evidence that closes it: Decision 1 says (1) the survey is a research step with a time box,
   using a stand-in driver from a scratch copy (as 065's drafting driver was), and no check,
   TOML or harness line is committed before it; (2) its memo, labelled EXECUTED, and a dated
   delta to Decisions 8, 9, 11 and 12 always go to a confirmation round. That round is a
   context-only delta review, so it is cheap. Building starts on its verdict.

4. **M2 — Shared keys and the shared guard collide with today's meaning** (draft Decision 5,
   `upstream.py:153–187, 645–654`, `drive.py:142–145`). `support` today is a list of *files*.
   pandas uses it for `pandas/conftest.py` and two extension `__init__.py` files, and the rules
   check that each is a tarball member. The draft makes `support` a list of *folders* found
   through `path_packages`, and Decision 14 checks "`support` names tarball folders".
   `path_packages` is a list in `numpy.toml` and `pandas.toml`, and the draft makes it a map.
   `judge_group` is shared, and its name-based guard (with its `pandas.conftest` exception)
   would be replaced. The widened guard's second clause needs data the stream does not carry:
   `drive.py` emits `M` only for modules under the tests folder. The draft also says "the `M`
   lines name every module loaded from the grant", which taken literally includes the kit's
   pytest and hypothesis, and that would make every group red.
   Failure: either numpy and pandas fail the new rules, or their verdict logic silently changes
   in a judge-only edit. Or criterion 2's "product module outside the zip" case has no stream
   line to read.
   Fix text: (1) numpy and pandas keep their list-form keys and today's guard, byte for byte.
   The new keys are read only for configs with `driver = "package"`, and a unit check judges a
   recorded numpy and pandas stream exactly as today. (2) Give the new folder-valued key its
   own name, for example `support_packages`, or state the dual form and its rule. (3) Specify
   `package_drive.py`'s `M` scope: every module whose `__file__` is under
   `/upstream-<package>/tree/`, plus every module whose top-level name is in a list the judge
   writes into the group's JSON (the zip's top-level names and builtin module names) and whose
   `__file__` is neither in the zip nor absent. Kit modules are reported only in that second
   case, for example a shadowing `packaging`. (4) The guard's tree clause is path-based (under
   a staged test folder or a named support folder), not name-based. That is what admits
   Pillow's `Tests.*`.

5. **M3 — `read-only-tree` is a failure the judge makes, closed by the README** (draft
   Decisions 6 and 9). Pillow's working folder is read-only only because the judge chose the
   read-only stage as its `cwd`. A test that writes there fails because of the judge's setup,
   not a product fact. Closing that with `README.md`, "if none can move", is a convenience
   under rule 4.
   Fix text: decide it now. Either (i) Pillow's `cwd` is a writable folder in the guest's root
   holding a host copy of `Tests/`. That costs host I/O only, and guest fuel changes only by
   where the files live. Or (ii) keep the read-only `cwd`, and if the survey finds members, the
   class closes with a reserved judge follow-up, never `README.md`. The memo then names each
   member's write. (i) is the smaller honest choice.

6. **L1 — Decision 8 applies its own rule unevenly** (the matplotlib and lxml rows). The rule
   says files that skip themselves stay selected. Several listed files only skip themselves:
   `test_backend_nbagg.py`, `test_backend_inline.py` and `test_sphinxext.py` (module-level
   `importorskip`); `test_doc.py` (`importorskip` in the test); `test_backend_gtk3.py`,
   `test_backend_qt.py`, `test_backend_macosx.py` and `test_backend_tk.py` (backend marks with
   `skip_on_importerror`, or `importorskip`); `test_backend_cairo.py` (the conftest skips cairo
   on `ImportError`). Its stated reason, "GUI and notebook backends", is also wrong: cairo is a
   renderer. And `test_http_io.py`'s `needs_http` tests skip when libxml2 lacks `http`.
   `test_backend_webagg.py`'s honest reason is "imports `backend_webagg_core`, which step 70
   drops: it cannot load". Also, a module-level skip is a skipped collection report, not an `R`
   line, so it is not "a counted outcome" in this stream.
   Fix text: keep the self-skipping files selected, or give each the reason "skips itself
   (`<mark>`), every test". Correct the cairo and webagg reasons. Say that module-level skips
   are not counted, or emit them.

7. **L2 — Self-referencing closers.** `test_sphinxext.py` and `test_doc.py`, contourpy's
   `test_codebase.py`, Pillow's oss-fuzz row (H2) and lxml's docstring suites close with
   `context/specifications/066-…`, which is this specification itself. A closer names what will
   close the gap. A specification that names itself means "never".
   Fix text: name `README.md` where the reason is a platform fact the README states (no
   processes, for `test_codebase.py`), or a reserved follow-up number.

8. **L3 — lxml's doctest reasons and flags** (Decisions 7 and 8). `selftest`, `selftest2` and
   `test_xpathevaluator` are staged as source. So "compiled or bytecode in the zip" is false for
   three of the nine docstring suites. For the other six, the true reason is "pytest collects
   doctests only from files under the given paths; these modules are in the zip or builtin".
   lxml's own runner does run them, through `DocTestSuite(module)`.
   `doctest_optionflags = ELLIPSIS` applies to all 17 files, but lxml runs the six
   `html/tests/*.txt` files without it. lxml runs `validation.txt` five times and pytest once.
   Fix text: split the not-selected entry by reason. Either select the three staged modules'
   doctests, or state their true reason. Say what the `.ini` changes relative to lxml.

9. **L4 — The mpl-toolkits group may load three conftests under one name** (INFERRED).
   `axes_grid1/tests`, `axisartist/tests` and `mplot3d/tests` each have `__init__.py` and
   `conftest.py`. With the toolkit's own `__init__.py` not staged (it is product code), import
   mode `importlib` resolves each to the module name `tests.conftest`. numpy has no conftest
   under a `tests` folder, so 050 never met this case.
   Fix text: the survey runs mpl-toolkits first. The fallback is decided now: one group per
   toolkit folder.

10. **L5 — The job-slot premise is contradicted by its own source run** (Decision 12). In
    `39371419248`, 16 Linux and Windows judge and verify jobs started at 05:00:39. The x86-64
    rebuild ran until 05:04:02. Five macOS jobs started from 05:00:43 to 05:00:47: 22 jobs at
    once. macOS's own-rest waited until 05:01:41, for a macOS slot (the limit of five), not for
    a slot in a total of 20.
    Fix text: "the binding limit in 39371419248 was macOS's five concurrent jobs; Linux jobs ran
    22 at once with the others; the three Linux shards are INFERRED to start at once". The
    landing notes record the branch run's gather start against 05:08:22, as a benchmark.

11. **L6 — The lane's cost and the per-family budgets are not stated** (Decision 11, "The
    owner's choices"). Today's accepted darwin upstream fuel is 2.84 T over 16 groups. 066 adds
    1.3 to 2.6 T (INFERRED), or 45 to 90% more upstream guest work at every landing. That is
    more again on the serial judge every fifth landing. Each family's budget is also left to
    the builder, which makes "caps ≤ budget" empty.
    Fix text: add the lane cost to the owner's choices, as a benchmark estimate. The
    confirmation delta (M1) states each family's budget.

12. **L7 — The closer plan for packages 066 does not run is incomplete** (Decision 13). 044's
    branch names `spec 066` for scikit-learn (`044-scikit-learn.md:722`), as well as 037 and
    038 for scipy. `shards.package_errors` accepts a number only if it is in the roadmap's
    `Reserved:` paragraph (`shards.py:259–313`).
    Fix text: 066's own roadmap edit reserves the number now, at confirmation, under "scipy's,
    scikit-learn's and statsmodels' own tests in the release". The lane tells the builders of
    037, 038 and 044 (and 045 if it adds an entry) to name it. Decision 13 lists every entry,
    not only 037's.

13. **L8 — Small facts.** kiwisolver's `sys_path = ["py/tests"]` is not needed: its six modules
    import only `kiwisolver`, `pytest` and the stdlib (§6.4, the smallest thing). Pillow's
    `Tests/` holds 1,279 regular files (68.83 MB), not 1,310.

- **N1 (note) — Directory order.** `test_bmp_reference`, `test_file_msp` and `test_file_sun`
  use `os.listdir`, and oss-fuzz parametrizes over `rglob`. The order follows the host's file
  system. Outcomes and the sorted `passed_digest` do not depend on it. darwin's APFS order is
  fixed by name, so the lane's fuel is stable. Linux's ext4 order is seeded per file system,
  but Linux fuel is not ratcheted. Criterion 5's repeat should restage between its two runs
  to show this.
- **N2 (note) — `wasm32-memory`.** The reason should cite the binary's declared maximum
  memory, not "4 GiB", unless that is the declared maximum.
- **Determinism (AGENTS rule "tests count operations").** No check reads a clock. The guest's
  clock and random come from the host and are fixed, and regex's `0002-timeout-ticks.patch`
  counts ticks. Every time in the draft is a CI benchmark. This holds.

## Constitution checks

- §4: no artifact byte, no recipe, no pin and no patch changes. Every tarball is already pinned
  and verified (§4 pins). The new grants are judge-made preopens, not guest imports or exports.
  Tests count fuel, never time. These hold.
- §5.2: holds once M1 is written in (ruling (a)).
- §5.6: a pre-build review was asked for and this is it. The threat-model review sees the new
  CI inputs.
- §7: nothing tripped. No guest was run and nothing was committed by this review.

## Disposition (filled in by the author, then confirmed by the reviewer)

(The author, 2026-10-20; each is detailed in the specification's "Disposition of the pre-build
review".)

1. H1 — fixed, option (i): `keep_classes` from `test_suite()`, `D` lines, checked both ways;
   doctest files with lxml's own flags; the nine docstring suites collected (Decision 7).
2. H2 — fixed: `Tests/oss-fuzz` selected, `Tests/oss-fuzz` on `extra_sys_path` (Decisions 5, 8).
3. M1 — fixed: a time-boxed research survey with a stand-in driver before any judge code; the
   EXECUTED memo and its delta always go to a confirmation round (Decision 1).
4. M2 — fixed: `driver = "package"`; numpy and pandas unchanged byte for byte; new key names; the
   `M` scope; a path-based guard (Decisions 3, 5; criterion 2).
5. M3 — fixed, option (i): Pillow's `cwd` is `/tmp/work` with a host copy of `Tests/` (Decision 6).
6. L1 to L8, N1, N2 — written in with the review's fix text (L7: 095 reserved by the lane for
   scipy's and scikit-learn's own tests; both entries point at it).

## Verdict

Ready once H1, H2 and M1 to M3 are written in (the Lows with their fix text need no further
round): the structure is sound, but lxml's selection and Pillow's fuzz row are wrong as
drafted, and the survey's numbers must come back through a confirmation round before the build.

## Confirmation (2026-10-20)

- **Reviewer:** the same fresh agent as above. It wrote none of the revision, the survey or the
  delta.
- **Reviewed:** `spec/066-the-compiled-packages-own-tests` at `055a38a`. `d1864fb` is the
  revision with its Disposition. `055a38a` adds the survey memo
  `context/research/2026-10-20-the-compiled-packages-own-tests-under-the-runtime.md`, its
  evidence (`failures.txt`, `summary.json`, `results.tsv`, `kiwisolver-trap.txt`, the stand-in
  driver) and the spec's "Delta from the survey". The diff touches only `context/` (READ).
- **Ran:** nothing. No guest, no pytest. Time box: 30 minutes. I read the trees again where a
  delta item turns on a single line (`build/pillow-13.0.0`, `build/matplotlib-3.11.2`,
  `build/numpy-2.5.2`, `build/lxml-6.1.3`, `downloads/lxml-6.1.3.tar.gz`). The survey's numbers
  are the builder's, EXECUTED in its memo. I take them as recorded and did not re-run them.

### The pre-build findings, as written in

- **H1 — closed.** Decision 7 makes the selection equal to `test_suite()`'s in both directions
  (`keep_classes`, `D` lines, a check both ways), and criteria 1 and 2 test it. The survey
  bears it out: 360 collected items were deselected and every listed class ran (EXECUTED, memo
  finding 7). The delta changes one thing, rightly. The 17 doctest files and the docstring
  suites run as stdlib `DocTestRunner` items with lxml's own flags, because under pytest's
  doctest plugin 9 files failed: `lxml.usedoctest` swaps the checker's code object. That is how
  lxml's own runner runs them. Decision 7's body must say so (C4).
- **H2 — closed.** `Tests/oss-fuzz/test_fuzzers.py` ran: 1,060 passes and 37 skips (EXECUTED).
  The survey found one more fact, and the `.ini` must carry it: Pillow's tests use the `timeout`
  mark, so `pillow.ini` registers it, or nine modules fail to collect under `--strict-markers`.
  Decision 7's Pillow line still says "nothing to transcribe but the testpath" (C4).
- **M1 — closed.** The memo is EXECUTED, was written before any check, TOML or harness line, and
  is in this round. contourpy's numbers come later, on 043's set, as Decision 1 says.
- **M2 — closed.** `driver = "package"`, the renamed keys, the `M` scope, the path-based guard,
  and numpy and pandas judged byte for byte (criterion 2) are all written in. In the survey no
  `M` line named a product module loaded from outside the zip; pytest used the product's
  `packaging`. One knock-on: Decision 14 now says `cwd` is `/tmp/work`, which the delta's
  Pillow choice contradicts (C1).
- **M3 — closed, by a better route than either option I offered.** See C1. The read-only
  working folder causes no failure, so neither a writable copy nor a judge follow-up is needed.

### Findings of this round, most severe first

1. **C1 — Pillow's one suspect test fails because of `mmap`, not the read-only folder** (Medium;
   delta "Decision 6"). `test_save_without_changing_readonly` (`Tests/test_image.py:246–253`)
   asserts `im.readonly` before and after `im.save`. `ImageFile` sets `readonly = 1` at open
   "until we know better" (`ImageFile.py:133`). After load it is 1 only when `mmap.mmap`
   succeeded (`ImageFile.py:311, 362, 434`). In the guest the `mmap` stand-in raises, Pillow
   falls back to reading, `readonly` becomes 0, and the second assert reports `assert 0`. READ.
   So no measured failure is caused by the read-only tree.
   Fix text: Pillow's `cwd` is the stage's tree root, read-only, with no copy. Decision 14's
   `cwd` rule allows `/tmp/work` or the tree root again, and the criterion-1 variant follows.
   The test is a member of Pillow's mmap facts, as its own class matched by id (its reason line
   is `assert 0`, not `mmap is unavailable`), closed by `README.md`. No judge follow-up is
   reserved for it. This also removes the litter risk that voided the copy.
2. **C2 — `no-lapack-errors` hides a user-visible fact the README does not state** (Medium;
   delta "Decision 9"). The two `test_mlab` cases carry matplotlib's own
   `skipif(sys.platform == 'emscripten', reason="WASM doesn't support floating-point exceptions")`
   (`test_mlab.py:883–889`). The guest's platform is `wasi`, so the skip does not apply. numpy
   signals a singular matrix through floating-point status flags, which wasm32 does not have.
   numpy's own suite skips its two not-invertible tests on any wasm
   (`linalg/tests/test_linalg.py:1169, 1998`, `IS_WASM = platform.machine() in ["wasm32",
   "wasm64"]`). That is why 050's groups never showed this. So in the product,
   `numpy.linalg.inv` and `matrix_power(…, -1)` of a singular matrix return without raising
   `LinAlgError` (INFERRED from upstream's own skips plus these two failures). `README.md` has
   no sentence on it (grep for `LinAlgError` and "singular": none).
   Fix text: name the class `no-fp-exceptions`, with the reason "wasm32 has no floating-point
   exception flags: numpy.linalg cannot raise LinAlgError for a singular matrix; numpy's own
   suite skips these on wasm, matplotlib only on emscripten". 066 adds that sentence to the
   README, since the class's closer is `README.md`. The lane decides whether a product follow-up
   (a carried numpy patch that checks LAPACK's `info`) gets a roadmap line. This is not 066's to
   build.
3. **C3 — 066 should depend on 096, not select around it** (Medium; the coordinator's question).
   - kiwisolver's trap fires at whichever collection first meets a cycle holding a kiwisolver
     object. The bisection moved it through three tests, one of which calls no `gc.collect()`
     (memo finding 1, EXECUTED). A deselection by node id cannot select around a trap whose
     place depends on when the collector runs. The only selection left is the whole group as
     one trap entry, which is no coverage at all.
   - matplotlib's constrained layout builds the same objects. The survey's matplotlib groups did
     not trap. But a change that moves allocation timing (a new pin, a new test file, 043's set)
     could move the trap into a matplotlib group on an unrelated landing (INFERRED). 096 first
     removes that risk from ten groups, not only from kiwisolver's.
   - lxml's `lxml-html-diff` class would be written, then removed by 096. 096 first means no
     class and no churn.
   - 066 must re-survey matplotlib and contourpy on 043's set anyway. That re-survey should run
     on a set that includes 096.
   Fix text: 066 depends on 096 (096 lands first, or 066 is built stacked on 096's reviewed tip,
   §4.14). The fallback is decided now in case 096 slips: 066 builds without the kiwisolver group
   (kiwisolver stays `later`, `closes_with = "spec 096"`), and `lxml-html-diff` is a class closed
   by 096. 096's own scope should say why spec 051's callback scan missed these casts (they pass
   through `void_cast`) and close that scan gap. That is a note for 096's drafter.
4. **C4 — The delta must be folded into the Decisions before building** (Low). Decisions 9, 11
   and 12 still hold the INFERRED tables (three shards, a 3×10¹² budget, `mpl-toolkits` as one
   group). Decision 7 still names a pytest doctest collector, and its Pillow line lacks `timeout`.
   Decision 2 says the six budgets are at most 3×10¹². The Status still says the numbers are
   "INFERRED until its survey runs".
   Fix text: replace each with the measured or ruled value, and keep the delta section as the
   dated record.
5. **C5 — Some new classes' names or reasons do not match what failed** (Low).
   - `no-ffmpeg-messages`: `test_movie_writer_registry` sets the ffmpeg path to `true` and asserts
     it is available (`test_animation.py:297–304`). It needs an executable on `PATH`, which the
     guest cannot run, so its reason is "no processes". Read `test_movie_writer_invalid_path`'s
     reason before naming it.
   - `stubs-not-in-zip`: the test reads `cm.pyi` from the stage's own tree, not from the zip. The
     honest fix is to stage that one tarball member as a support file (data, never imported).
     Otherwise its closer is a judge follow-up, not `README.md`.
   - `open-empty-path` (`open('')` answers `IsADirectoryError`), `builtin-no-file` and
     `include-dir-in-zip` close with `README.md`, so the README gains each fact if it does not
     state it already.
   - `test_tripcolor_warnings` (`DID NOT WARN`) is in the memo but not in the delta's classes.
     Name it with the 93 failures spec 043 owns, to be re-read on 043's set: it builds a
     Delaunay triangulation, which needs `_qhull`.
6. **C6 — Two lxml doctest files are still unread** (Low): `api.txt` and `parsing.txt` ("read in
   the build"). Each class needs its reason before it is written.
   Fix text: read both before the TOML. If either is a product defect, it goes to 096, not to a
   class. The build review sees the reasons.
7. **C7 — Closers for the two new not-selected items** (Low). `test_elementsoup.py`'s judge
   follow-up needs a reserved number in the roadmap's `Reserved:` paragraph, not just "a judge
   follow-up". regex's `test_main` is regex's own `unittest.main()` entry point. Its row says so,
   and closes with `README.md`'s testing paragraph, which names it as not run.
8. **C8 — lxml's copy of `samples/` meets the same litter hazard as Pillow's copy** (Low). The two
   files are tarball members at the sdist's top level (`samples/simple.xml`,
   `samples/simple-ns.xml`, READ).
   Fix text: stage them under the tree and give lxml the tree root as its `cwd`, read-only, as
   C1 does for Pillow. The build confirms that no lxml test writes to its working folder. Or
   keep the copy, with the reason it is safe.
9. **C9 — The proposed 6×10¹² is itself an underestimate** (Low). The survey ran without
   `test_contour.py`, without the 93 tests that failed at import on main's set, and without
   contourpy. On 043's set all of them run in full.
   Fix text: the owner rules on the rule, not on a number (below). The budget per family is
   stated after the re-survey on 043's set.

### The budget: my recommendation

**The larger budget,** set by rule: each cap is 1.5 times the re-survey's fuel on 043's set, and
each family's budget is written in `upstream.py`. The INFERRED total is 6.5 to 7×10¹² of caps,
not 6×10¹² (C9). Six Linux shards of at most about 700 G each.

- **Not "fewer files".** Leaving out a test because it costs fuel is a convenience. Decision 8 and
  AGENTS rule 4 allow only "cannot load" or "every test needs what the product lacks". Choosing
  this would need the owner to amend that rule.
- **Not "part of matplotlib on the lane only".** It saves release time, which is not what binds:
  macOS's five slots do, and six Linux shards end inside the 457 s macOS leg (INFERRED from
  0.16 to 0.31 s per G). It does not reduce the cost that bites, which is the lane's. And it
  removes Linux's G5 comparison for those groups.
- **The cost the owner accepts** is the lane's. The upstream groups' darwin fuel goes from 2.84 T
  to about 7 T at every full judge: the lane's, every builder's, and every reviewer's. That is
  more again on the serial judge every fifth landing. It is the price of matplotlib's 1,300
  image comparisons and Pillow's 1,060 fuzz files actually running, and the owner should choose
  it knowingly.

### Verdict of the confirmation

**Confirmed for build once C1 to C3 are written in and the owner rules on the budget.** The Lows
come with fix text and need no further round. The build starts after 043 and 096 have landed (or
stacked on their reviewed tips). The re-survey of matplotlib and contourpy on that set comes to
the lane as a second, small delta. The bar for that delta is a context-only look: any change in
the not-selected rows or the classes, any group over 480 G, and the budget per family.
