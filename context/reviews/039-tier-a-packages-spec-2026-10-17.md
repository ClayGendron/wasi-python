# Review of 039 — Tier A: the pure-Python packages (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the constitution (§4.1, §4.2, §4.6, §4.8 to §4.13, §4.15, §5.2, §5.6, §5.7), the specification, the memo `../research/2026-10-17-what-else-the-default-profile-carries.md`, decisions 43 to 48 (`../decisions.md`), question 64, and specs 033, 035 and 023 (their Decisions, checks and pre-build reviews). I read the code the specification changes or leans on: `scripts/steps/70_zip.sh`, `scripts/make_stdlib_zip.py` (`walk`, `wheel_members`, `pyc`, `add`), `scripts/steps/common.sh` (`pinned`, `patch_tree`), `scripts/steps/50_pandas.sh` and `35_stdlib_libs.sh` (the unpack pattern), `scripts/steps/80_snapshot.sh`, `scripts/assemble_artifacts.py` (`PACKAGES`, `WHEELS`, `wheel_licences`, `MANIFEST`), `scripts/00_download.sh`, `downloads/SHA256SUMS`, `.github/workflows/release.yml` (the zero-patch count), and the judge: `tests/harness/paths.py` (`PACKAGES`, `LICENCE_COMPONENTS`, `norm`, `_pin_for`, `is_version_of`, `licence_source`, `_top_level_licence`), `tests/harness/pins.py`, `tests/harness/needs.py`, `tests/harness/jobs.py`, `tests/jobs/regen.py`, `tests/jobs/oracle/pyproject.toml`, `tests/harness/guest.py`, `tests/harness/scan.py` (`url_errors`, `clock_hits`, `report`), `tests/harness/plugin.py` (`load_gaps`), `tests/checks/test_rules.py` (`test_known_gaps_are_well_formed`, `test_no_test_reads_a_clock`), `tests/checks/test_v1_3_data_stack.py` (`_run_job`, the golden checks), `tests/checks/test_v1_5_rebuild_from_pins.py` and `tests/known_gaps.toml`. I read the pinned upstream code that decides the design: pyyaml 6.0.3's `lib/yaml/__init__.py`, `cyaml.py`, `lib/_yaml/__init__.py`, `setup.py` and `pyproject.toml`; markupsafe 3.0.4's `__init__.py` and `setup.py`; threadpoolctl 3.7.0's `_load_libraries`, `_find_libraries_with_python` and `_get_libc`; sympy 1.14.0's nested `parsing/latex/LICENSE.txt`; tqdm 4.70.1's `LICENCE`. Each claim below is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/039-tier-a-packages.md` as drafted (committed in `e2b6e87`).
- **Ran (EXECUTED, darwin-arm64).** Nothing in `src/`, `tests/`, `scripts/`, `recipes/`, `downloads/` or the specification was edited; `scripts/build.sh` and the judge were not run. Guest runs used copies of `build/artifacts/` (`python.wasm`, `python-snapshot.wasm` `c7302cfd…`, `python-stdlib.zip`, checked against its `SHA256SUMS`) and the drafter's tier-A zip (`039-spec/guestzip/python-stdlib.zip`: today's 1,751 members plus the 2,014), on the judge's own driver (`tests/harness/guest.run`, fuel exact) and, for the Excel edge, through `wasi_python.run`. Host runs used the drafter's venv on the oracle's own CPython 3.15.0, under `uv run`. Everything is under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/039-review/`:
  - `scripts/pins.py` → `out/pins.txt`: every `get` line and SHA-256 of Decision 2 against PyPI's JSON for that release (`pypi/*.json`), and each package's latest version.
  - `dl/`: the two sdists and the MPL-2.0 text fetched again and hashed.
  - `scripts/members.py` → `out/members.txt`: the members step 70 adds, from the pinned files, with `make_stdlib_zip.py`'s own `walk` and `wheel_members` (imported read-only) and 033's two kept files.
  - `scripts/lic.py` → `out/licences.txt`: each wheel's notice parts by `assemble_artifacts.py`'s rule, the judge's `_top_level_licence`, and nested licence files.
  - `scripts/pinfor.py`: the judge's `_pin_for` and `is_version_of` for the thirty names.
  - `scripts/seeds.sh` → `out/seeds/`, `out/seeds.txt`: each of the seven drafted jobs natively under `PYTHONHASHSEED` 0 to 23; `excel`, `pdf` and `utilities` again under `TZ=Pacific/Kiritimati LC_ALL=C`.
  - `oracle/` → `out/oracle-uv.lock`, `out/oracle-sync.log`: a scratch oracle project with the thirty, locked and synced by the pinned uv 0.9.22 into the scratch folder.
  - `stage/`, `scripts/stage.py`: Decision 4's staging by hand, then `walk` with and without `.DS_Store` at both levels.
  - `scripts/tpc_probe.py` (the drafter's, re-run): threadpoolctl with and without `dllist`.
  - `scripts/quiet_t.py` → `out/quiet.txt`: every tier-A top-level import in the guest with warnings as errors, and the pure-path facts of criterion 12's check.
  - `scripts/excel_edge.py` → `out/excel_edge.txt`: Decision 9's Excel edge through `wasi_python.run`, on both binaries, with no grants and with a writable `/tmp`.
  - `snap/`: two snapshots made by step 80's own command (`x-wizer`) with the pinned wasmtime, one on today's zip (byte for byte the artifact's, `c7302cfd…`) and one on the tier-A zip → `out/snapshot_bytes.txt`, `scripts/snapfuel_t.py` → `out/snapfuel.txt`, `scripts/imp.py` → `out/imports.txt`.
  - `scripts/split_t.py` → `out/split.txt`: plain `-c pass`, 035's top-level split and the 035 review's reader prototype (`035-review/proto/zip_directory.py`) on both zips.
  - `scripts/mdparse.py` → `out/mdparse.txt`: the cost of reading a version from each of the thirty `METADATA` files.
  - The scratch oracle's `uv sync` built pyyaml's sdist on the host (its `setup.py` and backend ran, with setuptools and Cython fetched by uv) inside the scratch folder. That is what the specified oracle would do; it is finding 1's evidence.

## What holds

- **Every pin is right.** EXECUTED (`out/pins.txt`): all 30 `get` URLs and SHA-256 lines equal PyPI's JSON for that release, none is yanked, and each is the latest release except mpmath 1.3.0, as Decision 2 says. The two sdists and the MPL-2.0 text hash to their lines (`66a3107d…` from SPDX's `license-list-data` at commit `31ba1a50`, "License list build 3.29.0", READ from GitHub's API). The text differs from mozilla.org's copy only in trailing spaces. `packaging` 26.3's wheel is `d7193f7c…cd1c` on PyPI, as the matplotlib memo pins it.
- **The licences are the approved ones.** READ (`out/pins.txt`, each `METADATA`): every declared licence matches decision 43's list. No pin needs `importlib_metadata` or `importlib_resources`; the non-extra requirements close over the thirty, `six`, `numpy` and `packaging` (tqdm's `colorama` is Windows-only).
- **The judge maps every name to its pin.** EXECUTED (`scripts/pinfor.py`): `_pin_for` and `is_version_of` find exactly the right file for each of the thirty PyPI names, so `test_manifest_is_well_formed` and `licence_source` work unchanged. Every wheel has a `.dist-info` licence file both `wheel_licences` and `_top_level_licence` find (`out/licences.txt`), so all 28 wheels get a content check, not a presence check.
- **The member count is exact.** EXECUTED (`out/members.txt`): 2,014 members, 2,014 distinct, none clashing with today's zip, no `.so`, no name that step 70's `REWRITE` rule would touch. The non-code members are the 36 metadata files, `py.typed`, networkx's `atlas.dat.gz`, tqdm's `completion.sh` and man page, and sympy's grammar, `.xsl`, `.lark` and autolev example files.
- **The pure builds are clean.** READ: pyyaml's `__init__` catches `ImportError` from `.cyaml`, whose first line imports `yaml._yaml`; markupsafe catches it from `._speedups`. EXECUTED (`out/quiet.txt`, guest, tier-A zip): all 28 top-level imports succeed with `warnings.simplefilter("error")`; `yaml.__with_libyaml__` is `False`; `import _yaml` raises `ModuleNotFoundError: No module named '_yaml'`; `markupsafe._escape_inner.__module__` is `markupsafe._native`; `charset_normalizer.md` is `md.pyc`; `hasattr(yaml, "CLoader")` is `False`; no `speedups`, `mypyc` or `_yaml` module is loaded. `yaml.safe_*` never use libyaml, even natively (READ), so the C path does not reach any golden line.
- **The staging is deterministic and litter-free.** EXECUTED (`scripts/stage.py`): the staged `pure-install/` walks to 20 members (17 + 3) with one digest, the same with a `.DS_Store` at its top and inside `yaml/`. Both sdists hold an `.egg-info` beside the package (READ), so 033's `tree_members` would stop on `lib/` or `src/` as a tree; the staging is needed. No `._*` AppleDouble member is in either tarball (EXECUTED).
- **The golden jobs are seed-, zone- and locale-stable.** EXECUTED (`out/seeds.txt`): each of the seven gives one output over 24 hash seeds, equal to the drafter's native output; `excel`, `pdf` and `utilities` give the same under `TZ=Pacific/Kiritimati LC_ALL=C`. The xlsx is compared part by part, openpyxl's own output only as read-back values, and no container bytes that went through deflate are printed. That comparison is honest. No job trips the clock rule (`scan.clock_hits`, EXECUTED).
- **The Excel edge is as Decision 9 says.** EXECUTED (`out/excel_edge.txt`, `wasi_python.run`, tier-A zip, plain and snapshot): with no root and no grants, `openpyxl.Workbook().save(…)` raises `FileNotFoundError: … No usable temporary directory found …`, `df.to_excel(…)` raises `xlsxwriter.exceptions.FileCreateError`, and the `in_memory` writer round-trips the frame. With `Grant(folder, "/tmp", writable=True)` both writers work.
- **threadpoolctl's fix is right, and it belongs here.** READ (`threadpoolctl.py:1126-1160`): off Linux and Emscripten, 3.7.0 takes `ctypes.util.dllist` when it imports, and only falls back to `_get_libc()`, which is `CDLL(None, …)`, when it does not. EXECUTED (the drafter's probe, re-run): without `dllist` all three calls raise the stand-in's `OSError`; with `dllist = lambda: []` they give `[]`, `[None]` and `[]` with no warning. 033's Decision 6 hands this choice to this specification, and 033 is confirmed; putting the line in 033 now would reopen a confirmed text for one function. So 039 is the right place (see finding 8 for one sentence on the rule).
- **Decision 10 holds: an import does not grow with the zip.** EXECUTED (`out/imports.txt`): on the two snapshots, `import email.parser, decimal, statistics` grows by +4.98 M, the same as `pass` (+4.83 M). Each family's own import on the tier-A snapshot (before 035) costs 0.21 G (`yaml`) to 3.69 G (`sympy`) (`out/snapfuel.txt`); pre-importing any of them would put that into the snapshot for every call.
- **The cost estimates hold where they could be measured.** EXECUTED:
  - plain `-c pass` before 035: +77,692 per member (`out/split.txt`; the drafter had 77,867);
  - the 035 review's reader prototype on the tier-A zip: 25,000 per member, so about 26,900 after 035 with its 1,931 of other start work, +54.2 M for 2,014 members against the +60.4 M cap (10% headroom);
  - the snapshot: `pass` +4,831,524 (2,399 per member), a `json` call +2,392 and a pandas groupby +2,419 per member (`out/snapfuel.txt`), against the 3,500 cap;
  - the snapshot's bytes: +737,113 (366 per member; `out/snapshot_bytes.txt`), against the 2.0 MB cap; my control snapshot on today's zip is byte for byte the artifact's;
  - the wheel's three files at zlib level 6: 38.66 MB today, 55.14 MB with tier A (+16.48 MB).

  Not measured: a metadata miss through a built 035 (none exists). Finding 4 gives the split's slope at tier A's names, which decides that bound.

## Acceptance criteria against evidence

1. **Seen failing first:** credible for each check. The two known-gap checks need the shape finding 6 names, or `test_known_gaps_are_well_formed` refuses their entries.
2. **Names and bytes:** sound. The 2,014 reproduce from the pins with step 70's own functions (`out/members.txt`). The `cmp` of each `METADATA` with its `PKG-INFO` or wheel is the right test.
3. **The same bytes everywhere:** the release-workflow part is sound. The litter part cannot fail as written (finding 3).
4. **The judge:** sound in shape. The growth account needs two more rows (finding 4) and check 6's re-base, which is sound (finding 5).
5. **The numbers recorded:** sound. Add the snapshot's per-member growth and the split's slope measured here, so the build has a baseline.
6. **The release:** sound; the zero-patch count needs finding 9's wording.

## Findings, most severe first

1. **The oracle cannot install pyyaml the way Decision 11 says. It builds the sdist with unpinned tools, and whether it gets the C extension depends on the host.** High: the goldens' oracle would run unpinned code fetched at build time, need a C compiler, and differ by host; and the drafting evidence never ran the oracle as specified.
   - Decision 11 says "the oracle installs their platform wheels with the C speedups". EXECUTED (`out/pins.txt`, `pypi/pyyaml.json`): pyyaml 6.0.3 publishes wheels for cp38 to cp314t and **none for cp315**. markupsafe 3.0.4 does have cp315 wheels (20 files, macOS, Linux and Windows).
   - EXECUTED (`oracle/`, the pinned uv 0.9.22): `uv lock` on the oracle's dependencies plus the thirty records pyyaml as an sdist only (`out/oracle-uv.lock`). `uv sync` then builds it: uv resolves the build requirements at that moment (setuptools 84.0.0, Cython 3.3.0; neither is in `uv.lock`, neither is hashed), runs pyyaml's own `_pyyaml_pep517` backend and `setup.py`, and calls the C compiler. Here it fell back to pure Python only because `yaml.h` is absent (`out/oracle-sync.log`: "fatal error: 'yaml.h' file not found … falling back to pure Python"). A host with libyaml's headers builds `yaml._yaml`.
   - So the oracle on one machine is not the oracle on another; it needs network access for unhashed build tools (§4.2's spirit; spec 002 keeps every oracle download pinned by the lock); and it runs a download's build code on the host (§4.8 allows build tools under the build's control; this is the judge's oracle, outside it).
   - READ (`039-spec/venv/…/site-packages`): the drafter's native runs used the pure `yaml/` and `markupsafe/` trees copied in by hand (no `.so`, no `WHEEL` file), not an oracle install. So "each EXECUTED natively" is true of a pure native, not of the specified oracle.
   - Fix: decide the oracle's pyyaml in Decision 11. Recommended: the oracle gets pyyaml as the guest does. `tests/harness/jobs.py` unpacks the pinned `pyyaml-6.0.3.tar.gz` (hash-checked against `downloads/SHA256SUMS`, as `oracle_python()` checks its archive) under `build/oracle/pure/`, copies `lib/yaml/`, writes `pyyaml-6.0.3.dist-info/METADATA` from `PKG-INFO`, and puts the folder on the oracle's path through `oracle_env`. pyyaml leaves `pyproject.toml`'s list; nothing else requires it (READ). markupsafe stays a locked cp315 wheel, since jinja2 requires it, with its C speedups; say so, and say the guest's `_native` path is held by criterion 12's check. Weaker alternatives: build constraints (the lock records no build requirement: EXECUTED, `out/oracle-uv.lock` has no setuptools or Cython entry) or a build flag that forces the pure path (still a compiler-free build of a download on the host).

2. **tqdm's source is offered only as a pointer to files this project does not control.** Medium: the release would rest one licence obligation on PyPI and GitHub keeping tqdm's files.
   - READ (MPL-2.0 §1.6, §1.14, §3.2(a)): a `.pyc` is not the form preferred for modification, so the zip ships tqdm in Executable Form. §3.2(a) asks that the Covered Software "must also be made available in Source Code Form" and that recipients be told how to get it "by reasonable means in a timely manner". Decision 8 names the PyPI wheel and the upstream tag.
   - INFERRED (a reading, not legal advice): pointing to an unmodified upstream copy is common practice. But a PyPI project's owners can delete a release, and a tag can be moved. The release would then fall out of compliance with nothing in this repository changing.
   - The cost of carrying it is small: the pinned wheel is 80,199 bytes and already hashed.
   - Fix: carry the source with the release. Recommended: `assemble_artifacts.py` copies the pinned `tqdm-4.70.1-py3-none-any.whl` (hash-checked) to `LICENSES/tqdm-4.70.1-source.whl` (or its `.py` files into `LICENSES/tqdm-4.70.1-source.zip`), so the GitHub release and the `wasi-python` wheel both hold it; `LICENSES/tqdm.txt`'s third part names that file first, then PyPI and the tag. `test_tqdm_notice_carries_the_mpl_and_its_source` checks the file's bytes equal the pinned wheel's. If the author prefers the pointer alone, the specification says why, in writing, as §5.2 asks.

3. **Criterion 3's litter test cannot fail.** Medium-low: it claims a proof it does not give.
   - READ (Decision 4): step 70 starts with `remove "$B/pyyaml-6.0.3" "$B/markupsafe-3.0.4" "$B/pure-install"`, then unpacks and copies again. So a `.DS_Store` put in `build/pure-install/yaml/` or beside a `PKG-INFO` before "steps 70 to 90 re-run" is deleted before anything reads it. And `--metadata` reads one named file, so litter beside it is never read in any case.
   - Fix: replace that clause with a unit check in `tests/unit/test_build_scripts.py`. It stages a tree as Decision 4 does (a package folder with a `.DS_Store` at the tree's top and inside the package) and asserts `tree_members` gives the same names and bytes with and without the litter. This review ran that test by hand (`scripts/stage.py`: one digest).

4. **The growth account misses two kinds of check.** Medium-low: as written, legitimate growth would breach a cap, and the build review would chase it.
   - **Checks that read metadata, plain.** The "every other plain check" row allows +60.4 M plus 0.2%. A plain check that queries `importlib.metadata` also pays the top-level split over every member. EXECUTED (`out/split.txt`): the split costs **4,844 per member** at tier A's names (the 035 review measured 4,608 on padded names), so +9.8 M more for 2,014 members.
   - **Checks that read every distribution's metadata.** EXECUTED (`out/mdparse.txt`, plain): reading `.version` from the thirty new `METADATA` files costs **565.9 M, about 18.9 M each** (the `email` parse; 033 found the same kind of cost for numpy). So `test_packages_carry_their_metadata[plain, snapshot]`, which this specification extends to the thirty, grows by about 0.57 G on each binary. Spec 035's check 6 snapshot comparison, over "the distributions the zip holds", reads every distribution twice and grows by at least twice that. None of the table's rows covers this.
   - **The snapshot row's basis is confounded, but its number is right.** Spec 023's +2.0% was measured with matplotlib's binary as well as its zip. EXECUTED (`out/snapfuel.txt`): 2,399 per member on today's binary with only the zip changed. Cite this instead.
   - Fix: add the rows "plain checks that query metadata: ≤ 2,014 × (30,000 + 6,000) = 72.5 M" and "checks that read every distribution's metadata: ≤ 25 M per added distribution (about 18.9 M measured)". Name 033's metadata check and 035's check 6 there. Cite this review's snapshot numbers.

5. **035's check 6 re-base is sound. Three points of wording.** Low-medium (a judge change).
   - The arithmetic holds. EXECUTED: the split's slope at tier A's names is 4,844 per member. With the 035 confirmation's 9.4 M at 1,758 members, the miss at 4,382 members (023 and this) is about 9.4 + 610 × 4,622 + 2,014 × 4,844 ≈ **22.0 M**, past 20 M, as Decision 13 says. The new bound is 20 M + 6,000 × 2,624 ≈ **35.7 M**.
   - The formula is the plain slope bound applied to the snapshot, with 035's own intercept. It guards the fixed part (≤ 20 M at 1,758) and the per-member part (≤ 6,000) separately. That is sound. The headroom on the slope is 19% at tier A's names, not the 30% 035 assumed for 4,600.
   - It also loosens with every future member (scipy, tier B) without a new account. That is acceptable only because the plain slope check (≤ 6,000 per member) stays. Say so.
   - Fix: write in Decision 13 that (a) "members" is `len(zipfile.ZipFile(zip).infolist())` of the artifact zip at check time; (b) the snapshot miss is still bounded per member by the plain slope check, and the measured slope at tier A's names is 4,844; (c) check 6's snapshot comparison should open the zip once (`zipfile.Path(zf, folder + "/")` on one `ZipFile`), or it parses the 4,382-member directory once per distribution. Optional for 035's author: priming the split for the artifact zip in phase 1 would make the snapshot miss constant and leave check 6's 20 M as it is.

6. **The two known-gap checks need a shape the specification does not give.** Low-medium: the first build would meet `test_known_gaps_are_well_formed` and stop.
   - READ (`test_rules.py:140-162`, `plugin.py:81-102`): a gap's `match` must hold "`N finding(s), digest …`", the form `scan.report(findings)` prints; its `closes_with` must be a file under `context/`. `tests/known_gaps.toml` holds no gap today, so there is no example to copy.
   - Fix: say that each check builds a list of one-line findings with no fuel or path in them, for example `nx.graph_atlas(100): TypeError: filename must be a str or bytes object, or a file` and `df.style.to_html(): TemplateNotFound: html.tpl`, and asserts `not findings, scan.report(findings)`. The closer is `context/specifications/039-tier-a-packages.md` until 041 is a file. Re-see the atlas's message after 035 lands: `files()` then returns 035's `ZipDirectoryPath`, which is not path-like either (INFERRED), so the message should not change.

7. **The jobs as drafted differ from their description in four small ways.** Low.
   - `excel` and `pdf` print their versions from `__version__`, not `importlib.metadata.version` (READ), so they do not "prove spec 033's metadata for its family" as Decision 11 says. Fix: use `version()` in both.
   - `text_formats` prints `cp1252 -> cp1250 True` (EXECUTED): charset-normalizer names **cp1250** for the cp1252 bytes, a fair guess, since both decode the sentence alike. Decision 11 says it names cp1252. Fix the text.
   - `symbolic` uses `lambdify`'s default modules. READ (sympy 1.14.0): the default is `["numpy", "scipy"]` when scipy imports. Once 037 lands, the job imports scipy, so its fuel jumps for a reason that is not this family's. Fix: `modules="numpy"`. It still runs `from numpy import *`, which reaches `numpy.ctypeslib` through 033's stand-in.
   - EXECUTED (`ruff check` with the repository's configuration): the seven drafts have 82 findings (`E702`, `E501`, `E401`, `I001`, `F401`), and `ruff format --check` would change all seven. Formatting does not change their output. Say the builder formats them.

8. **Small text points.** Low.
   - Decision 5: state the rule as 033's, extended. A name exists so that an import succeeds, and a query whose true wasm32 answer is known is answered (`find_library` → `None`, `dllist` → `[]`). Anything that would load or call still raises.
   - Decision 9 and the README: one line that `yaml.CLoader` and `yaml.CDumper` are absent and `yaml.__with_libyaml__` is `False`. That is the same as a native install without libyaml; code that uses `getattr(yaml, "CSafeLoader", yaml.SafeLoader)` works.
   - Criterion 12's charset-normalizer check: add that no member name holds `__mypyc` and that no `*__mypyc*` module is loaded. `md.pyc` alone does not show that the mypyc path is absent.
   - Decision 12: the `threadpool_limits` check should leave the context it enters (the drafting probe entered it only).
   - The sympy row could name its 16 autolev `test-examples` files, which pass `SKIP_DIRS` because the folder is not called `test`. They stay, as Scope says (no trimming).

9. **The release count and the order with 037 are stated for one path only.** Low.
   - The Design table says the zero-patch count goes "to 17 after 023's 15". Decision 14 allows this to land before or after 037, which adds two trees too. Fix: "rises by two from main's count", as 037 words it.
   - 037's Decision 16 places tier A after 037 and 038; Decision 14 here allows either order. One of the two texts, or the roadmap, should say which wins, so the lane does not have to choose.

10. **sympy carries a nested MIT notice that `LICENSES/sympy.txt` would not hold.** Low.
    - EXECUTED (`out/licences.txt`): `sympy/parsing/latex/LICENSE.txt` ("Copyright 2016, latex2sympy", MIT) is inside the package, not in `.dist-info`. It covers the LaTeX grammar and its generated parser, which the zip carries. `wheel_licences` reads only `.dist-info`. The file does travel inside the zip as a member. No other wheel has a nested licence file.
    - Fix: `assemble_artifacts.py` adds that file as a second part of `LICENSES/sympy.txt`, named in Decision 8. MIT is the licence decision 43 approves for most of tier A, so no owner question follows.

## Is it one builder's work?

Yes. The change is mechanical: 31 pins, about 40 lines of step 70, a dict in `assemble_artifacts.py`, one recipe line, the judge's lists, seven jobs already drafted and seed-stable, and a few checks. The three steps in Decision 14 are the right order. Finding 1 adds a small oracle helper to step 2. A full rebuild is needed only in step 1.

## On the order 033 → 035 → 023 → 039

Right. 033 gives `--metadata`, `tree_members` and the stand-in that `dllist` extends; 035 cuts the per-member start cost first (decision 44; EXECUTED here: 77,692 per member today); 023 brings `packaging`, which patsy imports at import. Nothing here depends on scipy. Finding 9 asks that 037's text and this one agree on which comes first.

## Constitution checks

- **§4.1, patches few:** holds. No patch; two sdists are unpacked and checked by spec 020's tree check; their packages are copied, not changed.
- **§4.2, every input pinned:** holds for the build (EXECUTED: all 31 lines). The oracle as specified breaks it in spirit (finding 1).
- **§4.3 and §4.4, one target, two channels:** hold. No native file enters the zip; the binary does not change.
- **§4.6, the artifact set:** holds. The zip, the snapshot, `MANIFEST` and `LICENSES/` change; `python.wasm` does not.
- **§4.8, downloads untrusted:** holds for the build (the sdists are data; their `setup.py` never runs). The oracle as specified runs pyyaml's build code (finding 1).
- **§4.9, tests count:** holds. Every check is equality, an exit, bytes or fuel; no job reads a clock (EXECUTED).
- **§4.10, claims carry evidence:** mostly holds. Decision 11's oracle claim was not executed (finding 1); the charset line and the versions source are misdescribed (finding 7).
- **§4.11, platform semantics documented:** holds with Decision 9's README list and finding 8's `CLoader` line.
- **§4.12, licences ship with the artifact:** holds after findings 2 and 10.
- **§4.13, tooling:** holds once the jobs are formatted (finding 7).
- **§4.15, safe by default:** holds. Nothing writable stays the default; the Excel edge is documented and EXECUTED.
- **§5.2, no open questions:** holds after finding 1's choice is written in. Question 64 is correctly outside the specification.
- **§5.6, review before build:** this review.
- **§5.7, build-class, one in flight:** holds. The order is stated; finding 9 aligns it with 037.

## Disposition (filled in by the author, then confirmed by the reviewer)

The author's answers, 2026-10-17. Every finding is fixed in the specification's text; none is declined. Section references are to the revised `specifications/039-tier-a-packages.md`.

1. **Fixed (Decision 11, "The oracle"; Design; criterion 4).** pyyaml leaves the oracle's `pyproject.toml`. A new `oracle_pure()` in `tests/harness/jobs.py` checks the pinned `pyyaml-6.0.3.tar.gz` against `downloads/SHA256SUMS`, extracts only `lib/yaml/` and `PKG-INFO` under `build/oracle/pure/`, writes `pyyaml-6.0.3.dist-info/METADATA`, stamps the unpack with the hash, and `oracle_env` puts it on `PYTHONPATH`. Nothing is built on the host and nothing unhashed is fetched. markupsafe stays a locked cp315 wheel with its C speedups, said so, with the guest's `_native` path held by the pure-path check. The text now says the drafting natives were pure by hand, and that for markupsafe `regen.py` and the guest check are what show the goldens hold. Criterion 4 asks that the oracle's sync shows no build step.
2. **Fixed (Decision 8; Decision 12's tqdm check; criterion 1).** The release carries tqdm's source: `assemble_artifacts.py` copies the pinned, hash-checked `tqdm-4.70.1-py3-none-any.whl` unchanged to `LICENSES/tqdm-4.70.1-source.whl`. The pinned wheel's bytes rather than a repacked zip of its `.py` files, so its SHA-256 is the pin's and checkable against `MANIFEST`. `LICENSES/tqdm.txt`'s third part names that file first, then PyPI and the tag. The check asserts the file's bytes equal the pinned wheel's; criterion 1 sees it fail on a missing and a one-byte-changed copy.
3. **Fixed (Decision 12; criterion 3; Design).** The litter re-run is gone from criterion 3, with the reason. A unit check, `test_a_staged_tree_ignores_litter`, stages a tree as Decision 4 does and asserts `tree_members` gives the same names and bytes with `.DS_Store` at the top and inside the package; seen failing first against a mutant that keeps litter.
4. **Fixed (Decision 13's table).** Two rows added: plain checks that query metadata (≤ 2,014 × 36,000 = 72.5 M + 0.2%; the split's 4,844 per member cited), and checks that read every distribution's metadata (about 18.9 M each, ≤ 25 M per added distribution per read; 033's metadata check ≤ +0.75 G, 035's check 6 comparison ≤ +1.5 G, since it reads each twice). A snapshot row for metadata queries is widened to 3,500 + 6,000 per member. The snapshot rows now cite this review's two-snapshot measurements (2,399 fuel and 366 bytes per member), not spec 023's +2.0%, and the plain row cites the prototype's 25,000 + 1,931. Criterion 5 records the per-member and split baselines.
5. **Fixed (Decision 13, "Spec 035's check 6").** Written as a proposed amendment to 035, which the lane writes into 035 when 039 lands, or 035's builder adopts first; the judge change is in 039's diff and `--accept-judge`. (a) N is `len(zipfile.ZipFile(zip).infolist())` of the artifact zip at check time; (b) the plain slope bound (≤ 6,000) stays and is what bounds each member, with the measured 4,844 and 19% headroom stated, and the loosening with later members named; (c) the snapshot comparison opens the zip once. The optional priming is recorded for 035's builder; if 035 primes, neither change is made.
6. **Fixed (Decision 12, "The two known-gap checks"; Design; criterion 1).** Each check builds one-line findings with no fuel or path (for `TemplateNotFound`, the template's `e.name`, not its message, which quotes the zip's path), asserts `not findings, scan.report(findings)`, and its gap names that exact set and closes with `context/specifications/039-tier-a-packages.md` until 041 is a file. The atlas's message is re-seen after 035, as the review notes.
7. **Fixed (Decision 11).** All seven jobs print versions from `importlib.metadata.version` (the `excel` and `pdf` drafts did not; said so). The charset line names cp1250 and says why. `symbolic` uses `lambdify(…, modules="numpy")`, with the reason (sympy's default adds scipy once 037 lands) and that it still reaches `numpy.ctypeslib`. The builder writes the jobs formatted and clean under `ruff format` and `ruff check`; criterion 4 asks for it.
8. **Fixed.** Decision 5 states the rule as 033's, extended (a known true answer is answered; anything that loads or calls raises). Decision 9 and the README gain the `CLoader`/ `__with_libyaml__` line. The pure-path check adds no `__mypyc` member name and no `__mypyc` module loaded. The threadpoolctl check enters and leaves the `threadpool_limits` block. Decision 1 names sympy's 16 autolev `test-examples` files, kept as Scope says.
9. **Fixed (Design; Decision 14).** The zero-patch count "rises by two from main's count". Decision 14 now says 037's order wins (037 and 038 first, as 037's Decision 16 and the roadmap say), with one rule so the lane does not choose: 039 goes first only if 037 is not confirmed for build when 039 is confirmed and 023 has landed; otherwise it waits for 038.
10. **Fixed (Decision 8; the tqdm/notice check).** `assemble_artifacts.py` adds `sympy/parsing/latex/LICENSE.txt` as a second, labelled part of `LICENSES/sympy.txt`, and the v1.1 notice check asserts it is there.

## Verdict

Not ready to build as written, but close. The pins, the member count, the pure builds, the staging, the jobs' determinism, the Excel edge, threadpoolctl's fix and the snapshot's growth all check out against the real code and the guest. Before the build:

- fix finding 1: the oracle takes pyyaml from the pinned sdist's pure tree, not from an sdist build;
- fix finding 2: the release carries tqdm's source, or the specification says in writing why a pointer is enough;
- fix findings 3 to 6 in the text and criteria (the litter test, two growth rows, the check-6 wording, the gap checks' shape);
- findings 7 to 10 are one-line edits the author may make at the same time.

A confirmation by this reviewer is enough; no second full review is needed.

## One line

The pins, members, pure paths and jobs hold, and the snapshot grows 2,399 fuel and 366 bytes per member as estimated; fix the oracle's pyyaml (no cp315 wheel, so it builds with unpinned tools), carry tqdm's source, and make the litter test and growth account real, then 039 can be built.

## Confirmation (2026-10-17)

The reviewer, against the revised specification (commit `7f842c6`) and the Disposition above. New runs are under the same scratch folder (`039-review/`): `oracle2/`, `pure/`, `jobs2/`, `out/c/`, `scripts/gaps.py` → `out/gaps.txt`. Nothing outside this section was edited.

### The ten dispositions

1. **Confirmed, and now executed.** I built the oracle as Decision 11 now says. EXECUTED (`oracle2/`, the pinned uv 0.9.22): the oracle's dependencies plus twenty-nine of the thirty, without pyyaml, lock to 37 packages with no pyyaml entry; `uv sync -v` builds nothing (no `Building` or `Built` line in `oracle2/sync.log`); markupsafe arrives as the cp315 wheel with `_speedups.cpython-315-darwin.so`. pyyaml was staged as `oracle_pure()` describes: the pinned sdist's hash checked, `lib/yaml/` (17 files) and `PKG-INFO` extracted, `PKG-INFO` written as `pyyaml-6.0.3.dist-info/METADATA`, the folder on `PYTHONPATH`. There `yaml` loads from the staged folder, `__with_libyaml__` is `False`, `version("pyyaml")` is `6.0.3`, and markupsafe runs `_speedups`. All seven jobs, as revised (finding 7's edits applied to the drafts), give the same output under seeds 0 and 1, **equal byte for byte to the pure-native outputs** (`out/c/`). So the C-speedups path the drafts never ran does not change a golden line.
2. **Confirmed.** Carrying the pinned wheel unchanged as `LICENSES/tqdm-4.70.1-source.whl` meets §3.2(a) without relying on anyone else's server, and its hash is the pin's. READ: the judge's set rule (`tests/harness/artifacts.py:27-42`) lists every file under the set, so the new file is covered by `SHA256SUMS`; `wheel_errors` compares every file of the set with the wheel; the licence checks look only at `LICENSES/<component>.txt`. Nothing refuses a non-text file there. The criterion's mutants (missing, one byte changed) are the right ones.
3. **Confirmed.** The vacuous re-run is gone. The unit check calls `tree_members` directly; READ: `tests/unit/test_build_scripts.py` already imports `make_stdlib_zip` on the host's Python, as the check needs. My hand run (`scripts/stage.py`) is the case it encodes.
4. **Confirmed.** The new rows match the measurements: 2,014 × 36,000 = 72.5 M; 9,500 per member = 19.1 M; 25 M × 30 = 0.75 G and twice that for 035's comparison. The snapshot rows now cite the two-snapshot runs.
5. **Confirmed.** Writing the re-base as a proposed amendment that the lane applies to 035 (or 035's builder adopts) keeps 039 from editing a confirmed text while the judge change rides in 039's diff and `--accept-judge`. The formula, the definition of N, the slope note, the open-once comparison and the "if 035 primes, neither change" rule are as asked (20 M + 6,000 × 2,624 ≈ 35.7 M).
6. **Confirmed, with one detail to write in (C1).** EXECUTED (`out/gaps.txt`, guest, tier-A zip): `df.style.to_html(): TemplateNotFound: html.tpl`; `nx.graph_atlas(100): TypeError: filename must be a str or bytes object, or a file`; and `df.to_latex()` also names **`html.tpl`** (the Styler loads its HTML template first). Using `e.name` keeps the findings path-free.
7. **Confirmed.** The versions lines, the cp1250 line, `modules="numpy"` and the formatting requirement are written in; the revised jobs reproduce (point 1).
8. **Confirmed.** The `dllist` rule, the `CLoader` line, the `__mypyc` assertions, the `with threadpool_limits(…)` block and the autolev note are in.
9. **Confirmed.** "Rises by two from main's count" and one ordering rule the lane can apply without choosing.
10. **Confirmed.** sympy's nested notice is a labelled part of `LICENSES/sympy.txt` and checked.

### New points (none blocks the build)

- **C1.** Decision 12's expected findings: write the `df.to_latex()` one as `df.to_latex(): TemplateNotFound: html.tpl` (EXECUTED above), so the gap's digest is known in advance.
- **C2.** `oracle_env` puts `pure/` on `PYTHONPATH` for every oracle run, so `oracle_available()` depends on `oracle_pure()` too. If the sdist is missing it raises `RuntimeError`, which `oracle_available()` already turns into "oracle unmet" (a skip with its reason), as for the host Python's archive. Say so in one line, so a missing pin reads as a blocked need, not a passing run.
- **C3.** Cosmetic: the Kind line's wrap was broken by the edit ("two\n source-tree patterns").

### Result

**Confirmed for build,** on one condition: C1's finding string is written into Decision 12 before the build starts. C2 and C3 are one-line edits the author may make at the same time. No further pre-build review is needed. The build review re-runs the oracle's sync (no build step), `regen.py --check`, the two gap checks against `tests/known_gaps.toml`, and the growth account against Decision 13's rows.

One line: every finding is fixed as written; the revised oracle builds nothing, runs markupsafe's C path and stages pyyaml's pure tree, and all seven revised jobs reproduce the goldens byte for byte under it. Write in `df.to_latex()`'s `html.tpl`, and 039 can be built.

### The author's note (2026-10-17)

All three points are written into the specification. C1: Decision 12 now expects `df.to_latex(): TemplateNotFound: html.tpl`, so both Styler findings and the gap's digest are known before the build. C2: Decision 11 says a missing or mismatched pyyaml sdist makes `oracle_pure()` raise, which `oracle_available()` turns into the oracle need unmet, so the golden checks skip with that reason. C3: the Kind line's wrap is fixed. The Status line says "confirmed for build with conditions, written in".
