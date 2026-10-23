# Review of 067 — the pure-Python packages' own tests in the release (the build)

- **Date:** 2026-10-22
- **Reviewer:** a fresh agent (Claude). It wrote none of 067. It wrote neither of 067's earlier reviews (`067-…-prebuild-2026-10-20.md`, `067-…-delta-2026-10-21.md`). It reviewed no other entry of wave 12.
- **Reviewed:** `origin/spec/067-the-pure-python-packages-own-tests` at `55d475fb`, then `84c5955c` and `a338f6bf`, checked out detached. The base is `origin/wave/12` `99dcd257` (main `c0d3a212` plus spec 095, reviewed). The diff is `git diff 99dcd257 55d475fb`: 262 files, +16,037 −175. **Then the fix commit `84c5955c`** (H1's fix: `tests/upstream/fetch.py`, a unit row in `tests/unit/test_fetch_trees.py`, and the spec's landing notes; 3 files, +50 −9), read whole and judged by node id. The verdict is on `84c5955c`.
- **Box:** 45 minutes (build-class and a package). Over, by the wait for the run and a loaded machine (load average about 60; the fast tier took 12 min 13 s at `-n 3`).
- **Run:** the builder's run **39715865231** on `55d475fb`, the exact commit reviewed. I dispatched no run of my own, as the lane asked (decisions.md, "The path to 0.1.0 is compressed": the review starts while the branch run goes). Read back (EXECUTED, `gh run view --json jobs`, `--log-failed`):
  - **39715865231 on `55d475fb`: red.** 45 jobs green, 5 skipped, 2 red: `judge (ubuntu-24.04, upstream-pure-smoke-a)` and `-smoke-b`, at "What the shard needs" (`cycler-0.12.1-tag.tar.gz: [Errno 2] No such file or directory`): H1, 067's own, not a host's outage. The gather was skipped behind them, so that run has no G line.
  - **39720564953 on `84c5955c`, the fix: green but G7.** 46 jobs green, 5 skipped (the release-tier job, as a normal run skips it, and the publishing jobs). The one red job is the gather, and its one red line is `RED: G7 the newest acceptance is not on the release's set (SHA256SUMS)` (`release-record-1`'s `scoreboard.txt` and the gather's log). Its scoreboard: `853/1871 pass · 128 gap · 7 blocked · 0 fail`; `v1.1 48/48`, `v1.5 53/53`. Both pure smoke shards green; the set is reused under its key (`wasi-python-set-v1-87caffda…`). No GREW line and no other RED line.
  - The final tip `a338f6bf` adds only the run id in the spec (`git diff --stat 84c5955c a338f6bf`: one context file), so the run on `84c5955c` is the run of the code reviewed.
- **Re-ran (EXECUTED, in this worktree; logs and scripts under `build/067-review/`):**
  - The fast tier, `uv run pytest -m "not slow" -n 3`, against the builder's judging set (a copy of its `build/067/sets/derived`: set `1556bbd5`'s `python.wasm`, snapshot and zip, with this branch's `MANIFEST`), with `WASI_PYTHON_ARTIFACTS` at the copy and `TMPDIR` at a scratch folder, in the lane's fast slot (`build/slots/fast` taken; `build/lane.lock` absent; the slot removed after). Result: `670/1871 pass · 0 gap · 42 blocked · 0 fail · 1159 deselected`; ratchet `lost 0 · absent 0 · unrun 0 · unrun locally 40 · gained 2 · grew 0`; `rules 71/72` (1 blocked, the prior-art clones), `v1.4 231/231`; 2,992 passed, 51 skipped, exit 0 (`fast.log`). The judge-hash line names `tests/checks/test_rules.py`, `test_v1_3_upstream_suites.py`, `test_v1_5_rebuild_from_pins.py` "and 306 more": a judge change, as the flags say. The 42 blocked rows are this worktree's missing source trees and compile records (the builder's 2,996 passed, 47 skipped differ by the same).
  - `uv run ruff check src tests`: clean. `uv run ruff format --check src tests`: 164 files formatted.
  - `pkgpaths.py`: the nine families' `[package_paths]` tables at the pre-rebase tip `aaf8a962` against the tables 095's `package_inits` generates on `55d475fb`.
  - `collect-base.txt`, `collect-head.txt`, `claims.py`: `--collect-only --tier release` of `tests/checks/test_v1_3_upstream_suites.py` on the base (a `git archive` of `99dcd257`) and on the head, against 067's claim block with `sameness._names`' prefix rule.
  - `shardsum.py`: each 067 shard's measured fuel and cap, from the family TOMLs.
  - `doccover.py`: for each family with docstring groups, the zip's modules in no group.
  - `probe_unshipped.py`: a `docstring_packages` entry the product does not ship, through every static rule.
  - sympy 1.14.0's `sympy/testing/runtests.py`, read in the builder's unpacked tree (READ).

## The builder's self-check

The list is present. Two items are unchecked, and each says why in its own words:

- The CI run was dispatched on this exact commit; its id was to follow in a context commit. I read the run myself (above).
- "Every new check seen failing first": this builder's four rows (the doctest setup, runner and checker rules, and their spec row) yes; the earlier builder's 30 rows of `tests/unit/test_pure_suites.py` were written beside the code, not seen failing first. The landing notes say so plainly ("The earlier builder's notes, carried"). That is rule 3's deviation, recorded, not hidden: L1.

Every other item is checked and true where I looked: the base in the Status line, the claim block, the flags, the CHANGELOG under the one unreleased section, `packages.toml` (all 42 `suite`, none names spec 067), ruff and the fast tier.

## Acceptance criteria against evidence

1. **The pins** — met. 39 `tests` lines in `scripts/00_download.sh` and 39 lines in `downloads/SHA256SUMS` (READ, counted); `test_every_test_source_is_pinned_and_named` and the unit row `test_a_tests_line_needs_its_pin_and_a_forges_archive_its_tag_name` pass (EXECUTED, fast tier). Every forge archive is named `-tag.tar.gz` (READ). The download itself is the run's (no host probed here).
2. **The rules** — met but for two rules (M1). Every key's rule has a unit variant (`test_each_source_key_has_its_rule`, seven ids; the bounds, the support file, the `python_files` widening, the one-group-per-unit rule, the named kind, the node-id rule, the opt-in skip on a fixed stream: EXECUTED, fast tier). **Not built:** "a `docstring_packages` entry the product does not ship" and "a shipped module of the entry in no group" (M1).
3. **The tie** — met. Five unit rows on synthetic archives, the patch unapplied included (EXECUTED, fast tier). The four patches' SHA-256 equal their `MANIFEST` `recipe` lines in the judging set (EXECUTED, `shasum`).
4. **The items** — met in part, as the builder says. The walk, `module_functions`, the `D` lines, `cwd_folders` have unit rows (EXECUTED). The three driver rows (`sys_flags` before import, a sympy XFAIL as `xfailed`, the conftest's profile) have none; they are held only by the guest runs (L3).
5. **The survey, then the baseline** — met (READ: the memo and its delta review's verdict).
6. **The TOML, lists and gaps complete** — met as far as the fast tier sees: the well-formed check passes with caps under `rule_cap` and each budget the sum of its caps, sympy's six trap caps included (EXECUTED). The group checks themselves are slow and release-tier rows (READ).
7. **Fuel repeats** — met for the smoke groups by the builder's two passes (READ, the landing notes; its logs not re-read); each release group once by node id (READ, the landing notes). The claim block's rows come from them (below).
8. **Nothing else moves** — met in the fast tier: `lost 0 · grew 0` (EXECUTED). No file of 095, numpy, pandas, lxml or CPython under `tests/upstream/` changes; `known_gaps.toml` and `release_shards.toml` lose no line (EXECUTED, `git diff --diff-filter`, `grep '^-'`).
9. **The artifact set** — not shown by this build, as the builder says: no rebuild. The judging set's `MANIFEST` has the 39 pins and four patch lines (READ). The run's rebuild shows it (EXECUTED on run 39720564953: both rebuilds from the pins, the same bytes and `v1.1 48/48` green on the set the lane holds; READ: the lane names it `3339091f`).
10. **`packages.toml`** — met (READ; `test_the_pure_packages_are_suites_and_none_waits`, EXECUTED).
11. **The shards and the fetch** — not met at `55d475fb` (H1). Each smoke group is in one of two Linux shards; 110 release shards; the workflow's matrix lists all 112 (`shards.py`, EXECUTED); the fetch's retry rows pass (EXECUTED). But the fetch on a clean host cannot stage nine of the 39 test sources (H1), and both smoke shards are red on run 39715865231 for it.
12. **The full judge** — the fast tier green; the run: 39720564953 green but G7, 0 fail (EXECUTED).
13. **The branch's dry run** — met by 39720564953 (every job green but G7; both smoke shards green, 262 s and 194 s by the lane's reading, under 360 s). No dispatch with `release-tier` true (READ: the run's inputs).

## Rule 4: can the doctest keys turn a real failure green?

No (READ, sympy 1.14.0's `runtests.py`; EXECUTED, the unit rows).

- **The keys are closed lists.** `DOCTEST_SETUPS`, `DOCTEST_RUNNERS` and `DOCTEST_CHECKERS` each hold one sympy name; any other name is refused with its own line (three unit ids). A family cannot name an arbitrary callable.
- **The runner counts failures as the stdlib does.** `SymPyDocTestRunner` overrides only `run`. Its `run` calls `self.__run`, which is the stdlib's own `DocTestRunner.__run` copied under the mangled name, as are `__record_outcome` and `__patched_linecache_getlines`. So `runner.failures`, which `DoctestItem.runtest` reads, is the stdlib's count. sympy's `run` adds `raise_on_deprecated()`, which can only add failures, and does not reset `sys.displayhook`, which is the point.
- **The checker is upstream's tolerance, no more.** `SymPyOutputChecker` accepts identical output, the stdlib's `<BLANKLINE>`, `NORMALIZE_WHITESPACE` and `ELLIPSIS` rules, and floats within 1e-5 of the expected. The float rule is the only leniency over the stdlib's checker, and it is the one sympy's own CI judges by (N3).
- **The setup is a printer, not a judge.** `setup_pprint` sets ASCII pretty printing, no line wrap and sympy's display hook. It changes what an example prints, never whether a failure is counted.
- **Where ours differs from `bin/doctest`** (L2): upstream runs `setup_pprint` before each docstring and restores the display hook after, empties each docstring's globals (`test.globs = {}` outside "normal" mode), and skips a docstring whose `_doctest_depends_on` names a missing dependency. The driver runs the setup once per session and keeps the stdlib finder's module globals. The first can only add failures (a leaked printer state). The second can let an example that forgets an import pass here and fail upstream: a lenience about the example's text, not about the product's output. The third runs about 40 docstrings that fail into `sympy-doctest`.
- **The class is exact.** `sympy-doctest` matches `doctest failed`, but its members are the 266 listed node ids (`class_findings`): a new failure is a `+id` finding, red.

**sympy's doctest blacklist** (READ, `_get_doctest_blacklist`, lines 662 to 786): every entry that names a module or doc file the product ships is in `docstring_not_selected` or left out of `doctest_files`, with upstream's reason in `sympy.toml`'s comment: the two compatibility shims, `galgebra`, `this`, autolev (only its `__init__` has examples, so the package-wide entry equals upstream's), latex's `_antlr` and `_parse_latex_antlr`, `sym_expr`, `pygletplot` (upstream's `ON_CI`), `aesaracode`, `randtest`, `autowrap` (its bot), the four deprecated stubs, `plotting.rst` and `numeric-computation.rst`. Upstream's other entries name files sympy 1.14.0 does not have (`codegen/array_utils.py`, `printing/ccode.py`, `cxxcode.py`, `fcode.py`, `utilities/quality_unicode.py`: EXECUTED, `ls`), the `examples/` tree (not shipped), and `doc/src/modules/physics/mechanics/autolev_parser.rst`, a stale path: the file now lives under `doc/src/explanation/…`, so upstream's runner runs it too, and so does `sympy-r-docfiles-1`. The numpy, scipy and matplotlib branches leave nothing out, as the product has all three.

**The six traps** are sound. Each is `@slow` or `@tooslow` upstream, measured past 3 T (one past 4.5 T) in the guest, and run alone to the 50 G cap by its trap check. A trap check is a gap that turns green if the test ever ends within its cap (`trap_findings`), so it hides no pass. The three removed from `sympy-r-solvers-7-9` are deselected by node id, so no test runs twice.

**The 480 to 725 G groups kept whole** are sound. Each fits one 725 G shard alone, about 225 s on Linux at 0.31 s per G, under the 360 s shard bound; splitting them would cost about 10 T of measuring and change no shard count. Decision 10's 480 G is a packing aid, and the lane should read this as a written deviation.

**No allowance is loosened.** No line of `known_gaps.toml`, `release_shards.toml`, any existing family's TOML or any `expected/` file of 095 or earlier is removed or changed (EXECUTED). The citation allowances for `packages.toml` lose three entries (`spec 039`, `042`, `067`), which is stricter. `smoke_errors` no longer lets a not-selected node id exclude its whole file, which is stricter.

## The merge with 095

- **`package_inits`** (EXECUTED, `pkgpaths.py`): for all nine families (beautifulsoup4, et-xmlfile, html5lib, joblib, mpmath, openpyxl, networkx, toolz, xlsxwriter), the table 067 listed at `aaf8a962` equals the table 095's `ancestors()` generates on `55d475fb` (1, 1, 1, 1, 1, 20, 25, 2 and 1 entries), and the stage folders are the same. None lists `package_paths` now. So the stage is the same files.
- **`env`** (READ): reportlab's and narwhals' variables are in 095's `[env.NAME]` form with `value` and `reason`, in `ENV_ALLOWED`; the unit row `an env name` expects 095's message.
- **095's rows are unchanged** (EXECUTED): `scipy.toml`, `scikit-learn.toml`, `statsmodels.toml` and their `expected/` files have no diff; 095's shards and gap block lose no line; `COMPILED_SUITES` keeps 095's three.

## The pins and patches

- **39 pins** (EXECUTED, counted): 30 sdists from `files.pythonhosted.org`, seven tag archives from GitHub, two from heptapod, and pypdf's sample files at a commit. Each has its `tests` line and its `SHA256SUMS` line; `test_source_errors` holds both ways and that one pattern meets each name. The `pypdf` pattern cannot meet the sample files' name (`[\w.]` has no `-`).
- **Four patches** (READ, EXECUTED): each touches only its test source's test files. Each is hashed in `MANIFEST` (the four `recipe` lines equal the files' SHA-256), named in the CHANGELOG, and has its note under `context/upstream/patches/` (three drafted pull requests, pypdf's a facts sheet, as its contributing guide asks a person to write). formulaic's moves the `pyarrow` import after the test's first assertion and skips there: the test counts as skipped, not passed. jinja2's marks the trio case skipped. Neither makes a pass of a failure.

## The shards and the claim block

- **Shards** (EXECUTED, `shardsum.py`): 112 pure shards (two smoke, 110 release), 93.69 T in all, which is 853 G of smoke and 92.84 T of release groups, as the notes say. Thirteen shards hold one group past 725 G. The largest, `upstream-pure-r-001` (`sympy-r-stats-4-continuous-rv-2`), measures 2,865 G: about 14.8 minutes of guest time on Linux at 0.31 s per G. Its cap is 4,300 G, about 22.2 minutes. With the job's setup that is under the 30-minute timeout, with a margin of under two to one (N1). The next are 2,576 G and 2,562 G (about 13.3 minutes each).
- **The release job's matrix** now has 226 legs (EXECUTED): under GitHub's 256-job limit for one matrix, with 30 to spare (N1).
- **The claim block** (EXECUTED, `claims.py`): `--tier release` collects 1,114 ids on the head against 529 on the base; 585 are new and none is gone. Of the new, 512 are claimed (420 suite rows, 86 class rows, 6 trap rows) and the other 73 are the smoke groups' normal-tier rows (42 suite, 31 class), rightly not in the release ledger. No pattern meets a base id, so no wildcard excuses a row outside 067. Six class patterns meet nothing (`packaging-r`, `xlsxwriter-r`, `beautifulsoup4-r`, `patsy-r`, `attrs-r`, `formulaic-r`): L5.

## Code speaks for itself

No new comment or docstring in `tests/`, `scripts/`, `release/` or the workflow cites a specification, memo, finding or `context/` path (EXECUTED, `grep` over the added lines). The `reason` and `closes_with` strings in the TOMLs name specs 023 and 042 as data, as 17 existing entries of `known_gaps.toml` do; the rules check passes (EXECUTED). The citing scripts are under `context/research/`, which may cite.

## Structure

No line of `src/` changes. The diff adds no module-level mutable, lock, private-API use, platform branch or runner seam. Not structural; the Kind line rightly does not say so.

## Findings, most severe first

1. **H1. A clean host cannot fetch nine test sources** (`tests/upstream/fetch.py:70`) — found first by wave 12's integration reviewer on run 39715865231 and relayed by the lane; confirmed here by reading the code and the run's log (EXECUTED, `gh run view --job 119625561170 --log-failed`: `cycler-0.12.1-tag.tar.gz: [Errno 2] No such file or directory: '…/downloads/cycler-0.12.1-tag.tar.gz'`, exit 1). `fetch()` saves a download as `downloads/<the URL's last part>` (`url.rsplit("/", 1)[1]`), but `fetch_trees()` then unpacks `downloads/<the pinned name>`. For wheels the two are the same, so it never mattered. For nine `tests` lines they differ: cycler, cloudpickle, threadpoolctl, tomli-w, xlrd, XlsxWriter, openpyxl and et-xmlfile (a tag archive, `v0.12.1.tar.gz` against `cycler-0.12.1-tag.tar.gz`, and so on) and pypdf's sample files (`818dc013….tar.gz`). Failure: on a fresh runner the file lands under the URL's name, `downloads/cycler-0.12.1-tag.tar.gz` does not exist, and the shard stops at "What the shard needs": `judge (ubuntu-24.04, upstream-pure-smoke-a)` and `-smoke-b` fail on the run. Locally it was hidden, because `scripts/00_download.sh --tests` had already saved every file under its pinned name, and `fetch()` found it in place. The unit row of criterion 11 uses `six`, whose two names agree, so it could not see it. Fix: save under the pinned name (pass the name to `fetch`), with a unit row seen failing first on a `-tag` source whose URL's last part differs, and a new branch run whose smoke shards are green. **Fixed in `84c5955c`** (READ, EXECUTED): `fetch()` takes the name to save as, and `fetch_trees()` and `fetch_files()` pass the pinned name; the kit-extra files keep their URL names, which their readers use. The new row `test_a_source_is_saved_under_its_pinned_name_not_its_urls` (a `tests` line whose URL ends `v2.5.2.tar.gz`, pinned as `numpy-2.5.2.tar.gz`, starting from an empty `downloads/`) **fails on `55d475fb`'s `fetch.py` and passes on the fix** (EXECUTED here, `fetch-red.log`: `1 failed`; `fix-units.log`: `test_fetch_trees.py` and `test_pure_suites.py`, 50 passed). The builder read every `get` and `tests` line: 33 of 155 differ from their URL's name; the ones `fetch.py` reaches are now right (READ, the landing notes). The run on the fix: 39720564953, both smoke shards green (EXECUTED).
2. **M1. Two of criterion 2's rules are not built** (`tests/harness/packages.py`, `tests/harness/tiers.py:445`) — criterion 2 names "a `docstring_packages` entry the product does not ship" and (ii) "a shipped module of the entry in no group" as rules, each with a unit variant; neither exists. `item_errors` holds "at most one group", not "at least one". Failure: `docstring_packages = ["nosuch"]` in a release group passes every static rule (`probe_unshipped.py`, EXECUTED: no error; the driver is sent `docstring_modules = []`). At run time the empty session's "pytest exit code 5" is a finding (`packages.py:1107`, INFERRED), so it is caught, but only in the release tier, before a tag. Today's data is whole (`doccover.py`, EXECUTED: every shipped module of every family's docstring entries is in a group, less its not-selected entries; the one exception, `more_itertools`' `__init__`, is a `docstring_modules` family whose `__init__` has no example). Evidence that closes it: the two rules in `source_rule_errors` (an entry not in `product_packages`/`zip_modules`; a shipped top-level submodule of the family's package in no docstring group and not not-selected), each with a unit row seen failing first; or a written descoping in the landing notes that the lane accepts.
3. **L1. Rule 3 for the earlier builder's 30 rows** (`tests/unit/test_pure_suites.py`) — written beside the code, not seen failing first. Recorded plainly; no fix asked. The lane's `--accept-judge` reason may say so.
4. **L2. "As its `bin/doctest` runs them" overstates** (`CHANGELOG.md`, `README.md`) — upstream's runner sets up the printer per docstring, empties each docstring's globals and reads `doctest_depends_on`; the driver does each once, keeps the module's globals and does not read the mark. Fix text, for both: "sympy's doctests run under sympy's own doctest runner, output checker and printer setup (the setup once per session, with the stdlib's finder: module globals, and `doctest_depends_on` not read)". sympy.toml's header comment may carry the same.
5. **L3. Criterion 4's three driver rows have no unit check** (`tests/upstream/package_drive.py`) — the builder's own open Low. Each is held at run time: a `P` line not derandomized is a finding (`_profile_ok`), and a sympy `@XFAIL` that were not pytest's mark would fail unlisted. Fix: a follow-up's rows on a fixed stream and a synthetic module, or the landing notes' line as it stands.
6. **L4. The README's patch row** (`README.md:41`) — "27, each with an upstream pull request drafted for the owner to send" is no longer true of pypdf's, which is a facts sheet. Fix text: after "lxml's `fake_cython` line, already merged upstream", add "or, for pypdf's test import, a facts sheet, since pypdf asks that a person write its issues".
7. **L5. Six claim patterns meet no row** (`context/release-tier-claims.toml`) — `test_upstream_class[packaging-r*`, `[xlsxwriter-r*`, `[beautifulsoup4-r*`, `[patsy-r*`, `[attrs-r*`, `[formulaic-r*`. They would excuse a class row those families gain before the release acceptance without a claim. Fix: drop the six lines (context only).
8. **N1. Headroom on Linux.** The largest release group is about 14.8 minutes of guest time at 0.31 s per G, 22 at its cap, against the job's 30 minutes with setup. The first CI run of these shards is the dry run on main; a shard past the timeout there is re-split from the darwin fuel. The release job's matrix is at 226 of 256: the next large suite needs a second job.
9. **N2. Forge archives** (nine `-tag` pins from GitHub and heptapod) are not promised byte-stable by their hosts. A drift is a verify failure, never a silent change.
10. **N3. sympy's checker accepts floats within 1e-5**, upstream's own tolerance.
11. **N4. The price is past the upper estimate**: 92.8 T against about 77 T (sympy 78.5 T against 63 T), about 3.6 to 4.4 more hours of guest time in the lane's release acceptance (INFERRED in the notes).
12. **N5. Round-1 fuel kept for split parts whose `-k` text changed** (open item 3): their membership is unchanged by simulation, and the release acceptance measures them again, so the cap (1.5 times) has room. Sound.
13. **N6. A race in the judge's tooling, named by the builder** (READ, the landing notes): on `84c5955c` its first fast tier failed `test_gather.py::test_the_gathers_collection_holds_every_release_tier_check` once, with `FileNotFoundError` from `litter.sealed_leftovers` walking `build/harness` while another `-n 3` worker removed its `unit-*` folder. It passes by node id, and my fast tier on `55d475fb` passed it. Not 067's code; the lane may see it again under `-n 3` or `-n 6`.

## Constitution checks

- §4.1, patches few, recorded and temporary: four test-only patches, hashed, named, each with its upstream note. Holds.
- Every input pinned by URL and SHA-256: 39 new pins, each a literal URL and a hash, verified before use; downloads unpack under `build/` only. Holds.
- Artifacts never in git: no `*.wasm`, `*.zip` or `*.cwasm` in the diff. Holds.
- Tests count operations: every bound is fuel; the minutes above are INFERRED estimates for the timeout, not checks. Holds.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. H1 — fixed in `84c5955c`, confirmed: the new row fails on the old `fetch.py` and passes on the fix (EXECUTED here), and run 39720564953 has both pure smoke shards green.
2. M1 — open. Closed by either the two rules with their unit rows, or a line in the landing notes descoping them to a reserved follow-up with its roadmap line (context only). Landing is safe meanwhile: today's data is whole (`doccover.py`), and an item group that runs nothing is red at run time ("pytest exit code 5").
3. L1 — recorded in the landing notes; no change asked.
4. L2 — open (fix text above; `CHANGELOG.md` and `README.md`).
5. L3 — recorded in the landing notes as an open Low.
6. L4 — open (fix text above; `README.md`).
7. L5 — open (context only).

## Verdict

067 lands at `a338f6bf` (code `84c5955c`, run 39720564953 green but G7) once M1 is answered in writing: the two docstring rules built, or descoped in the landing notes to a reserved follow-up.
