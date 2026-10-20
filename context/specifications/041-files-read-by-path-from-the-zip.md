# 041 — Files read by path from the zip

- **Status:** **built** 2026-10-19 on `spec/041-files-read-by-path-from-the-zip`, a **stacked build** (constitution §4.14, the owner, 2026-10-19) on base commit `dcd94ff`, spec 039's reviewed tip, which is built and reviewed but not yet landed; when 039 lands, this branch is rebased onto main and gets a delta review of what the rebase changed (Landing notes). Its branch dry run 39345809724 is red only for growth lines. Build-reviewed 2026-10-19 (lands once F1; F1 to F4 answered, F5 to F7 noted: "The build review and its answers"). Not accepted. **Spec 051's callback scan binds this build** (051, Decision 4a; written in when 051 landed): `test_callbacks_have_the_types_cpython_calls` is green, and a mismatch it finds is fixed by a carried patch or an upstream release, never by an exclusion. drafted 2026-10-17. Revised the same day against its pre-build review
  (`../reviews/041-files-read-by-path-from-the-zip-spec-2026-10-17.md`). All nine findings are
  written in here and in the two upstream folders, and the review's Disposition says where. The
  review's confirmation passed it for build with two conditions, written in: C1, the landing
  notes record question 80's answer at landing (if the owner answers otherwise, only the two
  sheets' bodies change, not the build); C2, it builds only after spec 039 lands, and uses spec
  033's landed `sdist_metadata`. It changes the build recipe and the artifact set, so it is
  reviewed before it is built (constitution §5.6). It is build-class: it touches `scripts/`,
  `recipes/patches/`, `downloads/SHA256SUMS` and the release workflow (§5.7). It carries two
  upstream patches (§4.1), so the review reads both patches and both drafts (spec 020,
  Decision 8).
- **Amended 2026-10-19 (spec 039's build review, F2):** spec 039 sets eleven Styler test files
  aside in `tests/upstream/pandas.toml` (`[[not_selected]]` under `pandas/tests/io/formats/style/`,
  closing with 041), adds the class `styler-templates` to `pandas-frame` (2 tests) and to
  `pandas-io-formats` (221 tests) with their lists under `tests/upstream/expected/`, and four gaps
  in `tests/known_gaps.toml` (the two classes and its two gap checks,
  `test_pandas_styler_renders_from_the_zip[plain]` and `test_networkx_atlas_reads_from_the_zip[plain]`).
  When 041 lands it re-selects the eleven files, removes the two classes, their lists and the four
  gaps, and expects `pandas-frame` back at 10,852 passes (039's lost `test_inspect_getmembers`).
- **Owner:** Clay Gendron
- **Kind:** two carried patches (`recipes/patches/pandas-3.0.6/`, `recipes/patches/networkx-3.7/`)
  with their upstream facts sheets; the build recipe (networkx's pin moves from its wheel to its
  sdist in `downloads/SHA256SUMS` and `scripts/00_download.sh`; `scripts/steps/70_zip.sh`;
  `scripts/make_stdlib_zip.py` gains `--entry-points`; `scripts/assemble_artifacts.py`); judge
  additions and changes (one golden job, the two known-gap checks of spec 039 widened and their
  gaps removed, one unit check, the source-tree patterns); the release workflow's tree count;
  `README.md`, `CHANGELOG.md`.
- **Depends on:** 039 (tier A; built and reviewed, not yet landed: this is built on its reviewed tip `dcd94ff`), which brings jinja2 and networkx, the two
  known-gap checks this closes, the staging folder `build/pure-install/` and networkx's wheel pin
  this replaces. Through 039: 033 (`make_stdlib_zip.py --metadata`, `tree_members`), 035 (the
  zip's own `Traversable`) and 023. Landed: 020 (carried patches: the applier, the tree check,
  the rules), 012 (the same bytes from any host), 018 (no litter in the zip). Where 039, 033 or
  035 lands in another shape than its text, this specification uses what landed and says so in
  its landing notes.
- **Research it stands on:** `../research/2026-10-17-what-else-the-default-profile-carries.md`,
  finding 4d (pandas' Styler cannot find its templates in a zip; jinja2's `PackageLoader` handles
  a zip, EXECUTED there) and item 4 of its order ("one carried patch with its upstream pull
  request"); spec 039, Decisions 9, 12 and 15 (the atlas's `TypeError`, EXECUTED in the guest
  while drafting 039; the two known-gap checks; this specification named). The owner's answer to
  question 32 (carried patches, §4.1). **The drafting runs** (EXECUTED 2026-10-17 in the
  session's scratch folder; nothing in the repository was changed by them but the drafts this
  specification adds under `context/upstream/`):
  - the upstream code READ in the pinned trees and wheels: `pandas/io/formats/style_render.py`
    (lines 74–77) and `style.py` (`from_custom_template`, line 3976) in `build/pandas-3.0.6`;
    `jinja2/loaders.py` in `jinja2-3.1.6-py3-none-any.whl` (`PackageLoader`, its zipimport
    branch, `_get_zipimporter_files`); `networkx/generators/atlas.py` and
    `networkx/utils/backends.py` in `networkx-3.7-py3-none-any.whl`; pandas' and networkx's
    `main` (both still have the lines this changes);
  - pandas-dev/pandas#62123 (READ with `gh pr view`/`gh pr diff`): merged 2025-08-15, it replaced
    `PackageLoader("pandas", "io/formats/templates")` with today's `FileSystemLoader`, because
    `PackageLoader` raised `ValueError` in editable installs made with newer meson-python;
  - networkx 3.7's sdist from PyPI's JSON, downloaded and its SHA-256 recomputed (`shasum -a 256`,
    equal to PyPI's); its `networkx/` tree compared, with step 70's own `walk` and
    `wheel_members` (imported read-only from `scripts/`), with the pinned wheel;
  - both patches made, applied to fresh extractions of the pinned tarballs with spec 020's
    `git apply` form (no offset), and run: in today's plain `python.wasm` on spec 039's drafting
    zip (3,791 members), with and without the two members compiled from the patched sources by
    step 70's own `pyc` under the line's Python 3.15.0; natively on CPython 3.15.0 with the same
    versions; networkx's own tests on the patched sdist with pytest 8.4.2;
  - pandas' and networkx's contributor policies on automated contributions (READ 2026-10-17):
    - pandas: the contributor guide's "Automated contributions policy" and its issue rules,
      `AGENTS.md`, and `.github/PULL_REQUEST_TEMPLATE.md`;
    - networkx: `CONTRIBUTING.rst`, with its note addressed to AI tools, and `AGENTS.md`;
    - the related issues pandas#38775 and #39733 and networkx#3929, #6936 and #7033.

    The files were read on `main` with `gh api`, and the issues with `gh issue view`.

  The evidence is in `context/upstream/5-pandas-styler-from-a-zip/evidence/` and
  `context/upstream/6-networkx-atlas-from-a-zip/evidence/`. The pre-build review's own runs
  repeat and extend it (its "Ran" list).

## The problem

Two packages in the default profile find a file of their own by path. A path inside the zip is
not a file the guest can open, so both fail (spec 039, Decision 9):

- **pandas' Styler.** `StylerRenderer` builds `jinja2.FileSystemLoader(Path(__file__).parent
  .resolve() / "templates")` when its class is defined (`style_render.py:74-77`). From the zip,
  `__file__` is `/usr/local/lib/python315.zip/pandas/io/formats/style_render.py`, and
  `FileSystemLoader` finds nothing under it. So `df.style`, every `Styler.to_*` export and
  `df.to_latex()` raise `TemplateNotFound: html.tpl`. The templates are in the zip.
- **networkx's graph atlas.** `_generate_graphs` calls `gzip.open(ATLAS_FILE, "rb")`, where
  `ATLAS_FILE = importlib.resources.files("networkx.generators") / "atlas.dat.gz"`. Installed as
  files, that is a `pathlib.Path`. From a zip it is a `Traversable`, which `gzip.open` refuses:
  `TypeError: filename must be a str or bytes object, or a file`. So `nx.graph_atlas` and
  `nx.graph_atlas_g` fail.

Both are upstream bugs: any Python that imports these packages from a zip has them. networkx's
reproduces natively with its own wheel on `PYTHONPATH` (EXECUTED, below). Spec 039 records both
as known gaps and names this specification as their closer.

## Decisions

1. **Both are fixed in the packages' own source, as carried patches (§4.1).** §4.1 prefers a
   recipe file, a stand-in module included. A recorded recipe under `recipes/` is no hidden
   source change: spec 035 replaces stdlib functions at run time that way. So a recipe was
   looked for first (§4.1, §6.2), and none fits:
   - **Templates or the atlas as real files the loader can find.** Rejected. The path pandas
     computes lies inside the zip's own file name. A plain folder cannot exist there. A folder
     preopened at exactly `/usr/local/lib/python315.zip/pandas/io/formats/templates` could
     satisfy `FileSystemLoader` (INFERRED: wasi-libc resolves a path against the preopen with
     the longest matching prefix). But:
     - the runner refuses such a grant, because the path is inside the runtime's own folder
       (EXECUTED by the review: "is the runtime's own (/usr/local/lib)");
     - shipping it would add loose files to the artifact set (§4.6);
     - it would add a second runtime preopen to every embedder's contract (§2.4);
     - it would not help networkx.
   - **A run-time recipe.** Rejected, on §6.2's and §6.4's grounds.
     - **Swapping `StylerRenderer.loader` after import cannot work at all.** The failure is
       raised inside `StylerRenderer`'s class body, at `env.get_template("html.tpl")`
       (`style_render.py`, line 78), during the import itself (EXECUTED: the drafting run's
       traceback and the review's). The import fails before any swap could run.
     - **A recipe that would work is wider than the patch.** It would either replace
       `jinja2.FileSystemLoader` for every user of jinja2 before pandas imports it, or rewrite
       pandas' module at import. For networkx it would replace the private `_generate_graphs`
       with a copy of upstream's code.
     - **Spec 020 would not see it.** Its tree check would not cover such a recipe.
     - **It would have no exit.** No upstream release would ever let it be deleted.

     A carried patch is the smallest change. It is checked against its tarball, and it leaves
     once upstream releases the fix.
   - **Giving 035's `Traversable` an `__fspath__` or a `read`, so that `gzip.open` takes it.**
     Rejected. `os.fspath` would give a path no `open` can read. A `read` attribute would make
     `gzip.open` treat the path object as a stream; it would also differ from `zipfile.Path`,
     which has neither (035, Decision 6).
   - **`importlib.resources.as_file`.** Rejected. It copies the resource to a temporary file,
     and with nothing writable by default there is no temporary folder (spec 025, §4.15).

   Each fix is a few lines, correct on every install, and an upstream bug. So each is carried as
   a patch, and deleted once a pinned release carries the fix. Each patch comes with a drafted
   upstream record for the owner.
   - **The drafts are facts sheets, not pull request text** (question 80, recommended answer).
     Both projects refuse AI-written words in their issues and pull requests.
     - **pandas:** the contributor must "fully review and modify" a tool's output, and "must not
       use AI to speak for you". A disclosure names the harness, model and reasoning level. A
       pull request needs a triaged issue the contributor claimed with `/take`.
     - **networkx:** its `CONTRIBUTING.rst` asks AI assistants "do not generate or suggest a PR"
       and to tell their user to engage manually. It closes violating pull requests without
       review. Its `AGENTS.md` adds a two-week wait after an issue.
   - **Each draft states its project's rules in full.** It gives the defect, the reproduction,
     the history, the patch, the evidence and the route the rules allow, so the owner can write
     and file in their own words, or not engage.
   - **Spec 020's six header lines are kept**, so its rules accept the draft unchanged.
   - **Sending is the owner's (§7).** When the owner asks, an agent prepares a branch rebased
     onto upstream's `main` in a scratch clone and hands over the branch and the facts. It never
     writes the description and never acts on the project's GitHub.

   Whether upstream takes either fix does not change what is carried here. §4.1 needs the
   patch recorded and its upstream record drafted, and both are.
2. **pandas: `PackageLoader` only when the templates folder is not a directory.** The patch,
   `recipes/patches/pandas-3.0.6/0001-styler-templates-from-a-zip.patch` (879 bytes, SHA-256
   `0b6b418b…ce7d`), changes one statement in `style_render.py`:

   ```python
       if template_dir.is_dir():
           loader = jinja2.FileSystemLoader(template_dir)
       else:
           # pandas was imported from a zip archive, so its templates are not
           # files on disk. PackageLoader reads them through zipimport.
           loader = jinja2.PackageLoader("pandas", "io/formats/templates")
   ```

   - **Why not spec 039's one line (`PackageLoader` alone).** pandas used exactly that until
     #62123, which replaced it because `PackageLoader` raised `ValueError` in meson-python
     editable installs. Restoring it would undo that fix upstream, and upstream would refuse
     it. With the branch, every install where the Styler works today (a wheel, an editable
     install, a frozen application that collects the templates as files) still has the folder
     on disk and keeps today's loader. Only the failing case changes.
   - **How `PackageLoader` reads from the zip** (jinja2 3.1.6, READ): it imports the package,
     finds its spec, and when `spec.loader` is a `zipimport.zipimporter`, it reads each template
     with `loader.get_data(<archive>/pandas/io/formats/templates/<name>)`. It uses no
     temporary file and no resource reader. Spec 035 replaces zipimport's directory reader, and
     its check 3 proves the replacement builds the same dict, so `get_data` answers the same
     after 035 (INFERRED from 035's text, READ). `list_templates` (which pandas never calls)
     uses `zipimporter._get_files()`, which 035 keeps.
   - **`from_custom_template`** puts a `FileSystemLoader` on the caller's folder before
     `StylerRenderer.loader` in a `ChoiceLoader`. A custom template in a granted folder that
     extends a built-in one finds both (EXECUTED: the `custom` line below).
   - **EXECUTED while drafting** (`context/upstream/5-pandas-styler-from-a-zip/evidence/`): in the
     guest with stock pandas, six Styler calls raised `TemplateNotFound: html.tpl`; with the
     patched member they gave output equal to native CPython 3.15.0, by length and SHA-256:
     `df.style…to_html()` (1,009 characters), `df.to_latex()` (137),
     `df.style.to_latex(environment="longtable", caption=…)` (246), `to_string()` (44),
     `to_typst()` (112), and the custom template (1,028); the loader was `PackageLoader`.
     Natively, the patched module keeps `FileSystemLoader`. The pre-build review repeated this
     with a seventh call and full SHA-256. It also found pandas' own Styler and `to_latex` tests
     equal on stock and patched installs (911 passed, 2 failed for want of matplotlib, 2
     skipped, both).
   - **The comment's wording.** The patch's comment says the `else` branch means "pandas was
     imported from a zip archive". Strictly, it serves any install whose templates folder is not
     a directory. The carried patch keeps the reviewed wording. The pandas facts sheet suggests
     "for example, when pandas is imported from a zip archive" for the owner's own version.
   - **No pandas test in the carried patch.** pandas' suite cannot import a zip-imported pandas,
     because its compiled extensions cannot load from a zip. The review wrote a test that forces
     the branch:
     - it monkeypatches `Path.is_dir` to return `False`;
     - it reloads `style_render`;
     - it skips on #62123's `ValueError`;
     - it asserts a `PackageLoader`.

     It passed on a patched install and failed on stock (EXECUTED). The facts sheet offers it to
     the owner, with its limits: a directory install, a skip under editable CI, and a module
     reload in the suite. Whether to send it is the owner's call. The carried patch stays as
     reviewed, and this project's judge holds the behaviour in the guest (Decision 7).
3. **networkx: open the resource, then decompress the stream.** The patch,
   `recipes/patches/networkx-3.7/0001-graph-atlas-from-a-zip.patch` (2,061 bytes, SHA-256
   `3b8b6d2d…5384`), changes one line of `networkx/generators/atlas.py`, with a two-line comment:

   ```python
       with ATLAS_FILE.open("rb") as raw, gzip.open(raw, "rb") as f:
   ```

   `Traversable.open("rb")` is `importlib.resources`' own API, so the line works for a
   `pathlib.Path`, a `zipfile.Path` and 035's `ZipDirectoryPath`. 035's `open("rb")` serves
   `atlas.dat.gz` (8,887 bytes, deflated, so under its 1 MiB bound) as a binary stream (035,
   Decision 6; INFERRED, since the drafting run used today's `zipfile.Path`). `ATLAS_FILE` keeps
   its value and type.

   The patch also adds `test_atlas_file_in_a_zip` to `networkx/generators/tests/test_atlas.py`:
   it writes `atlas.dat.gz` into a zip under `tmp_path`, points `atlas.ATLAS_FILE` at a
   `zipfile.Path` with `monkeypatch`, and checks `graph_atlas(6)` as `test_graph` does. The
   carried patch is the whole change the facts sheet describes, test included, as numpy's is. The zip never holds it
   (step 70 skips `tests/`).

   **EXECUTED** (`context/upstream/6-networkx-atlas-from-a-zip/evidence/`):
   - **Natively, from a zip.** With the stock wheel on `PYTHONPATH`, `nx.graph_atlas(6)` raised
     the `TypeError`. With the patched package zipped, it gave `[(0, 1), (0, 2)]`, and
     `graph_atlas_g()` gave 1,253 graphs.
   - **The new test** failed without the fix and passed with it. `test_atlas.py` gave 9 passed.
   - **The wider tests.** The counts depend on the optional packages installed.
     - On the line's CPython 3.15.0 with numpy and pandas (the pre-build review),
       `networkx/generators/tests` gave 614 passed and 18 skipped. The whole `networkx` suite
       gave 8,390 passed, 341 skipped and 741 xfailed.
     - While drafting, on uv's CPython 3.15.0a3 without them, the generators' tests gave 598
       passed and 34 skipped. Both runs used pytest 8.4.2.
   - **In the guest,** `graph_atlas(100)` and `graph_atlas_g()` gave results equal to native.
     The review added `graph_atlas(0)` and `graph_atlas(1252)`, and found `ATLAS_FILE` is a
     `zipfile.Path` there before 035.
4. **How a wheel takes a patch: it does not; the package comes from its sdist.** Spec 020
   applies a patch to a source tree unpacked from a pinned tarball, and §4.1 states the rule in
   those words. networkx is a wheel in spec 039. This specification pins **networkx's sdist in
   place of its wheel** and stages it as 039 stages pyyaml and markupsafe. A wheel is never
   unpacked and patched. **The rule, for this and every later pure-Python package that needs a
   patch:**
   1. pin its sdist, unpack it, call `patch_tree`, stage its package folder in
      `build/pure-install/`, and take its metadata from the sdist;
   2. show, in the specification that moves it and with the sdist unpatched, that step 70's
      `walk` of the staged package equals `wheel_members` of the release's pure wheel, name for
      name and byte for byte. List each difference and why it is harmless;
   3. show that `PKG-INFO` equals the wheel's `METADATA`, and that any `entry_points.txt` equals
      the wheel's.

   This does not hold for every project:
   - a wheel may hold files its build backend generates, such as a version file from
     setuptools-scm or compiled data;
   - an sdist made by flit or hatchling carries no `.egg-info/entry_points.txt` (INFERRED from
     those backends' sdist layouts).

   Where the wheel has an `entry_points.txt` and the sdist has none, that specification decides
   what to do. It may generate nothing, as 033 did for numpy and pandas, or say why the entry
   points matter. networkx, below, is the rule's first instance.
   - **Why not patch the wheel.** That needs a second kind of patched archive in three places:
     a step that unpacks and repacks a wheel, the judge's `tree_drift` (it extracts tarballs),
     and spec 020's `<top>` rule (the top of a pinned tarball, from its file name). It would add
     an option to `make_stdlib_zip.py` that packs a wheel from a folder. That is more new
     machinery than the sdist route, for the same bytes. The sdist is also what upstream
     releases as source, so the carried patch and anything the owner files upstream rest on the same
     files.
   - **The same members, EXECUTED.** The sdist's `networkx/`, walked by step 70's `walk`, gives
     289 members; the wheel's `wheel_members` gives 290 outside `.dist-info`. The 289 are the
     same names and bytes. The one left over is **`networkx/conftest.py`, which is not packed**,
     because `walk` skips `conftest.py` (`SKIP_NAMES`) and `wheel_members` does not. It is
     pytest's configuration; nothing imports it at run time. The pre-build review found the raw
     trees the same 598 files (EXECUTED). The sdist's `PKG-INFO` equals the wheel's `METADATA` byte for byte, and
     `networkx.egg-info/entry_points.txt` equals the wheel's `entry_points.txt` byte for byte.
     Its `LICENSE.txt` equals the wheel's `licenses/LICENSE.txt` (`cmp`).
   - **The pin** (PyPI's JSON, 2026-10-17; the hash recomputed from the downloaded file):

     ```sh
     get https://files.pythonhosted.org/packages/dc/76/3af777226b63a5e64a6b36b1ec5855c14e2b94a37096d4760e595fc43511/networkx-3.7.tar.gz networkx-3.7.tar.gz
     ```

     ```
     fd77a511bd90f39f3d016351345b52cf5319b813bdca01de3f755d3cca62e96a  networkx-3.7.tar.gz
     ```

     It replaces spec 039's `networkx-3.7-py3-none-any.whl` line in both files, in the same place.
     The tarball's top folder is `networkx-3.7`, its file name without `.tar.gz`, as spec 020's
     rules require. The oracle keeps networkx 3.7 from its lock, unpatched: natively the atlas
     works, so the golden job shows that the patch changes no result (Decision 7).
5. **The sdist's entry points: `make_stdlib_zip.py --entry-points PKG-INFO FILE`.** Spec 039
   packs networkx's `entry_points.txt` from its wheel. Spec 033's `--metadata` takes a
   `PKG-INFO` only, and 033 chose not to generate entry points for numpy and pandas, since none
   meant anything in the guest. networkx's file is different: it is in the pinned sdist, its
   bytes equal the wheel's, and dropping it would change what `entry_points()` answers from
   039's zip. So it is kept, with one small option:
   - **The option.** `--entry-points <PKG-INFO> <file>` (repeatable) is served by a new
     function, `sdist_entry_points(pkg_info, path) -> (bytes, member name)`, beside 033's
     `sdist_metadata`. It reads the `PKG-INFO`'s `Name:` and `Version:` headers with
     `sdist_metadata`'s own parsing and naming. It returns `<file>`'s bytes, unchanged, as
     `<name>-<version>.dist-info/entry_points.txt`.
   - **The match is by the computed folder name, not by the path string.** After all inputs are
     gathered, `main` stops when no `<that folder>/METADATA` member exists. The stop is one line
     naming both files. So an entry-points file never goes into a folder without its `METADATA`,
     however the `PKG-INFO` path was spelled. A clash with a wheel's own `entry_points.txt` is
     already stopped by `main`'s "comes from two inputs" rule.
   - **Why not today's `--file`.** `--file "<…>/entry_points.txt=networkx-3.7.dist-info/
     entry_points.txt"` would pack the same member with no new code. But it would write the
     folder name by hand, a second time, where a version bump must find it. And nothing would
     check that the folder has its `METADATA`. The option computes the name once, with the same
     function as `--metadata`, and guards it.
   - networkx's one entry point is its test backend (`nx_loopback`, in a `tests` module the zip
     does not hold). networkx removes it itself when it lists backends (`backends.py:95`, READ),
     so keeping the file changes nothing networkx does, and keeps `entry_points()` equal to
     native.
6. **Step 70, and the other recipe files.**
   - `scripts/steps/70_zip.sh`, beside spec 039's two sdists: `remove "$B/networkx-3.7"`; unpack
     `pinned networkx-3.7.tar.gz` into `$B`; `patch_tree "$B/networkx-3.7"`;
     `cp -R "$B/networkx-3.7/networkx" "$B/pure-install/networkx"`; then
     `--metadata "$B/networkx-3.7/PKG-INFO"` and `--entry-points "$B/networkx-3.7/PKG-INFO"
     "$B/networkx-3.7/networkx.egg-info/entry_points.txt"`. The `--wheel` line for networkx goes.
     Only `networkx/` is staged, so 033's `tree_members` never sees the sdist's `.egg-info`.
   - **pandas needs no script change.** Step 50 already calls `patch_tree "$B/pandas-3.0.6"`
     after the unpack (spec 020), and step 70 packs that tree's `pandas/`.
   - `scripts/assemble_artifacts.py`: `WHEELS` loses networkx's wheel; networkx's notice is
     `build/networkx-3.7/LICENSE.txt`, named in the `licences` dict as pyyaml's is (039,
     Decision 8). `PACKAGES` keeps `networkx`. The notice's text does not change.
   - The judge's `pins.SOURCE_PATTERNS` and `needs.SOURCE_COMPONENTS` gain `networkx`
     (`networkx-[\w.]+\.tar\.gz`), so spec 020's tree check and `<top>` rule cover the tree.
   - The release workflow's zero-patch job counts one more tree (networkx's) than main's count
     when this lands.
   - The two drafts move from `../upstream/5-pandas-styler-from-a-zip/pr.md` and
     `../upstream/6-networkx-atlas-from-a-zip/pr.md` to
     `../upstream/patches/pandas-3.0.6/0001-styler-templates-from-a-zip.md` and
     `../upstream/patches/networkx-3.7/0001-graph-atlas-from-a-zip.md` (`git mv`, unchanged).
     - Each folder's `fix.patch` is copied, byte for byte, to the patch path. It is then removed
       from the numbered folder, so one copy exists (criterion 3), and `notes.md` names the
       carried path.
     - The numbered folders keep `notes.md` and `evidence/`. Every evidence link in the drafts is
       written as a repository path (`context/upstream/<folder>/evidence/…`), so it stays true
       after the move.
     - They are drafted now, outside `upstream/patches/`, because spec 020's rules fail a draft
       there whose patch is not yet carried.
     - The drafts are facts sheets (Decision 1). Spec 020's rules read only the six header lines
       and the `Files:` paths, so they accept them as they are (EXECUTED by the review on
       `patch_errors`).
7. **The checks.** Each is seen failing first (Acceptance, criterion 1).
   - **A golden job, `tests/jobs/files_from_the_zip.py`**, run on the plain binary and compared
     with its `.expected` like the others (`jobs.compare`, the versions line first:
     `pandas`, `jinja2`, `networkx`). It prints in full: `df.style.set_uuid("job")` with a
     format and a highlight `.to_html()`; `df.to_latex()`; `df.style.to_latex(environment=
     "longtable", caption=…)`; `.to_string()`; `.to_typst()`; a custom template that extends
     `html_table.tpl`, through `Styler.from_custom_template(data_dir, html_table=…)`;
     `nx.graph_atlas(100)`'s name and sorted edges; `len(nx.graph_atlas_g())` and its total edge
     count.
     - The custom template is written to the job's **data folder**, never its output folder.
       Every file in the output folder is compared byte for byte (`jobs.render`; the
       convention `tests/jobs/compress.py` states).
     - The drafting probe (`context/upstream/5-pandas-styler-from-a-zip/evidence/files.py`) is
       its model. The job prints the texts, not their digests.
     - The uuid is fixed, so the HTML holds no random id.
     - The oracle runs stock pandas and networkx natively, where the bug does not occur. So
       equal output shows that the patches change no result **on the job's calls**. The golden
       cannot tell which loader served the guest. The Styler check below ties the result to the
       patched branch.
     - `jobs.JOBS` gains it.
   - **Spec 039's two known-gap checks become passing checks.**
     `test_pandas_styler_renders_from_the_zip` and `test_networkx_atlas_reads_from_the_zip` run
     on `[plain, snapshot]` (039 runs them on plain only). The Styler check also calls
     `to_string()`, `to_typst()` and `from_custom_template`, and asserts that
     `type(StylerRenderer.loader).__name__ == "PackageLoader"` in the guest, so the patched
     branch is the one that served it.
     - The loader assertion is itself a finding, not an uncaught exception. Importing
       `StylerRenderer` raises `TemplateNotFound` on the starting set (EXECUTED by the review).
       So the check catches that and records `StylerRenderer: TemplateNotFound: html.tpl`, and a
       wrong loader's name is recorded as a finding too.
     - The atlas check also calls `graph_atlas_g()`.
     - Each check still asserts no findings, in 039's path-free `N finding(s), digest …` form.
     - Their two entries leave `tests/known_gaps.toml`.
   - **Unit, `test_an_sdists_entry_points_go_beside_its_metadata`** in
     `tests/unit/test_build_scripts.py`: a temporary `PKG-INFO` (`Name: Some.Pkg`,
     `Version: 1.0`) and an `entry_points.txt`; the members built from `--metadata` and
     `--entry-points` are `some_pkg-1.0.dist-info/METADATA` and `…/entry_points.txt` with the
     files' bytes. `--entry-points` whose computed folder has no `METADATA` member stops with
     one line naming both files. The same `PKG-INFO` given as `x/PKG-INFO` to `--metadata` and
     as `./x/PKG-INFO` to `--entry-points` does not stop. It calls `sdist_metadata` and
     `sdist_entry_points` directly, and
     the folder check through the same function `main` uses, as 033's unit checks do.
   - **Spec 020's checks cover the patches with no new code:** `test_carried_patches_follow_the_
     rules` (each patch's draft, its `Files:` line, the CHANGELOG naming each patch path, the
     README's count) and `test_source_tree_matches_its_tarball` (pandas' tree is its tarball plus
     its patch; networkx's tree is new and patched).
8. **What it changes in the artifact set, so growth can be told from regression.** Against
   spec 039's set (EXECUTED while drafting, step 70's `pyc` and level-9 deflate):

   | member | change |
   |---|---|
   | `pandas/io/formats/style_render.pyc` | 112,205 → 112,373 bytes; deflated 42,921 → 43,008 |
   | `networkx/generators/atlas.pyc` | 6,488 → 6,659 bytes; deflated 3,137 → 3,208 |
   | `networkx/conftest.pyc` | removed (10,098 bytes; deflated 4,710) |
   | every other member | the same bytes, `networkx-3.7.dist-info/METADATA` and `entry_points.txt` included |

   So the zip has **one member fewer** and is about **4.7 KB smaller**. A plain start costs
   about one member's fuel less (about 27,000 after 035). The snapshot changes with the zip's
   directory. `python.wasm` does not change. The Styler is not pre-imported (`import pandas`
   does not import `style_render`), so no snapshot call pays for it. `MANIFEST` changes in the
   `pin` line for networkx (sdist for wheel), the `recipe` lines of `70_zip.sh`,
   `make_stdlib_zip.py`, `00_download.sh` and `assemble_artifacts.py`, and two new `recipe`
   lines for the patches.

   **No accepted metric should grow.** The new job and the two checks that now pass are new
   metrics. A growth in any accepted metric beyond the judge's noise is a finding for the build
   review, not something to accept.
9. **Ordering.** It is build-class, so it overlaps no other build-class change (§5.7). It
   builds after 039, which brings what it changes. With spec 042 (seaborn and reportlab, which
   may find files by path too, 039's Decision 15), whichever builds second rebases onto the
   other's step 70 and `assemble_artifacts.py`. If 042 needs a patch to a pure package, it uses
   Decision 4's rule.

## Intent

An agent's code in the default profile can style a frame and export it to HTML, LaTeX, text or
Typst, and can read networkx's graph atlas, from the zip, with results equal to native Python's.
The two fixes are upstream's own lines, carried as recorded patches until upstream releases
them. For each, the owner holds a facts sheet that states the project's rules, from which the
owner may write and file in their own words.

## Design

| file | change |
|---|---|
| `recipes/patches/pandas-3.0.6/0001-styler-templates-from-a-zip.patch` | new: `../upstream/5-pandas-styler-from-a-zip/fix.patch`, byte for byte (Decision 2) |
| `recipes/patches/networkx-3.7/0001-graph-atlas-from-a-zip.patch` | new: `../upstream/6-networkx-atlas-from-a-zip/fix.patch`, byte for byte (Decision 3) |
| `context/upstream/patches/pandas-3.0.6/0001-styler-templates-from-a-zip.md` | moved from `../upstream/5-pandas-styler-from-a-zip/pr.md` (Decision 6) |
| `context/upstream/patches/networkx-3.7/0001-graph-atlas-from-a-zip.md` | moved from `../upstream/6-networkx-atlas-from-a-zip/pr.md` (Decision 6) |
| `context/upstream/README.md` | the two rows say the facts sheets moved to `patches/` and the patches are carried |
| `context/upstream/5-…/notes.md`, `context/upstream/6-…/notes.md` | name the carried patch path; `fix.patch` removed from each folder (Decision 6) |
| `downloads/SHA256SUMS`, `scripts/00_download.sh` | networkx's sdist in place of its wheel (Decision 4) |
| `scripts/make_stdlib_zip.py` | `--entry-points <PKG-INFO> <file>` (Decision 5) |
| `scripts/steps/70_zip.sh` | unpack, patch and stage networkx's sdist; `--metadata` and `--entry-points` for it; its `--wheel` line removed (Decision 6) |
| `scripts/assemble_artifacts.py` | `WHEELS` without networkx; its notice from the tree (Decision 6) |
| `tests/harness/pins.py`, `tests/harness/needs.py` | `networkx` in `SOURCE_PATTERNS` and `SOURCE_COMPONENTS` |
| `tests/jobs/files_from_the_zip.py`, `.expected` | new golden job (Decision 7); golden written by `regen.py` |
| `tests/harness/jobs.py` | `JOBS` gains `files_from_the_zip` |
| `tests/checks/test_v1_3_default_profile.py` | the job's check; the two gap checks on `[plain, snapshot]`, widened (Decision 7) |
| `tests/known_gaps.toml` | the two gaps removed |
| `tests/unit/test_build_scripts.py` | `test_an_sdists_entry_points_go_beside_its_metadata` |
| `.github/workflows/release.yml` | the zero-patch job's tree count, one more than main's |
| `README.md` | the results row's `upstream patches carried:` count rises by two; the "What the default profile carries" section (039) drops the Styler and the atlas from its edges and says `df.style` and `df.to_latex()` work; the recipe paragraph says a pure package that needs a patch comes from its sdist |
| `CHANGELOG.md` | under the unreleased section: `df.style`, `df.to_latex()` and the graph atlas work from the zip, naming both patch paths (spec 020's rule); networkx is built from its sdist |

## Scope

In: Decisions 1 to 9. Out:
- **Filing anything upstream:** the owner's (§7), in the owner's own words, by the route each
  facts sheet sets out (Decision 1). No agent opens, comments on or pushes to either project.
  The carried patches do not wait on it.
- **The `importlib.resources` loader for pandas** (a `FunctionLoader` over `files()`): offered
  to pandas' maintainers in the draft as an alternative, not carried.
- **Other packages that read their own files by path.** None other is known in today's profile
  or tier A. Spec 042 checks seaborn and reportlab in the guest first.
- **`importlib.resources.as_file` and anything that needs a writable temporary folder:** nothing
  writable stays the default (§4.15).
- **Pre-importing the Styler** in the snapshot.

## Acceptance criteria

1. **The checks exist and were seen failing first** on the set the builder starts from (039
   landed), each recorded in the landing notes:
   - `test_files_from_the_zip_job_matches_native`: the guest's output differs from the golden
     (the job stops at `TemplateNotFound: html.tpl`);
   - the two widened checks: the Styler check's findings name `TemplateNotFound: html.tpl` for
     every call and for the loader assertion (`StylerRenderer: TemplateNotFound: html.tpl`, a
     finding, not an uncaught error), and the atlas check's name the `TypeError` for both calls;
     on `snapshot` too;
   - with the networkx sdist staged but its patch file removed, the atlas check fails as
     before; with the patch file present but `build/networkx-3.7` left unpatched,
     `test_source_tree_matches_its_tarball` fails naming `networkx/generators/atlas.py`;
   - with either draft removed, `test_carried_patches_follow_the_rules` fails naming it;
   - `test_an_sdists_entry_points_go_beside_its_metadata`: against 039's `make_stdlib_zip.py`
     (no `sdist_entry_points`); and against a mutant whose guard compares path strings, the
     case where the same `PKG-INFO` is spelled two ways (`./x/PKG-INFO` and `x/PKG-INFO`).
2. **The zip's names and bytes.** A full build from pins in a clean clone gives a `python.wasm`
   byte for byte the one it started from (`cmp`). Against the starting set's zip, sorted name
   lists (`unzip -Z1 … | LC_ALL=C sort`) differ only in `networkx/conftest.pyc`, removed; every
   shared member is the same bytes except `pandas/io/formats/style_render.pyc` and
   `networkx/generators/atlas.pyc`; `networkx-3.7.dist-info/METADATA` and `entry_points.txt` are
   byte-equal to the starting set's.
3. **The patches are what the drafts say.** Each `recipes/patches/…` file equals its
   `fix.patch` (`cmp`) before the numbered folder's copy is deleted; each draft's `Files:` line
   names exactly the paths `git apply --numstat` reads from its patch (spec 020's rule checks
   this too).
4. **The same bytes everywhere.** A manual run of the release workflow on the reviewed commit
   passes its `rebuild`, `same-bytes` and zero-patch jobs, the last with the new tree count; its
   run number goes in the landing notes.
5. **The judge.** `uv run pytest` is green with `--accept "<reason>"` and `--accept-judge "<the
   new job and golden; the two gap checks widened and their gaps removed; the unit check; the
   source-tree patterns>"`, and loses no pass. The landing notes give: plain and snapshot
   `-c pass` against the starting set (expected about one member's fuel less), the zip's and the
   snapshot's sizes, the new job's fuel, and the Styler check's and the atlas check's fuel on
   both binaries. Any accepted metric that grows is reported with its reason or fixed. The
   golden reproduces under the pinned oracle (`regen.py --check`). The new job passes
   `ruff check` and `ruff format --check`.
6. **The release.** A release dry run passes every job (criterion 4's run).

## The owner's choices

None open here. The owner's answer to question 32 is applied as written: carry a fix rather
than wait for upstream, with its upstream record drafted.

Question 80 in `../questions-for-the-owner.md` was recorded by this specification's pre-build
review. It asks whether, for a project that refuses AI-written contributions, the draft should
be a facts sheet from which the owner writes and files in their own words. This specification
applies the recommended answer (Decision 1). The two facts sheets keep spec 020's six header
lines, so spec 020's rules accept them unchanged. Nothing in the build waits on the answer:
- if the owner answers otherwise, only the two sheets' bodies change;
- the patches, the build and the judge do not.

Filing anything upstream is the owner's (§7).

## Landing notes

**Built** 2026-10-19 by the builder in `../wasi_python-041` on `spec/041-files-read-by-path-from-the-zip`,
a **stacked build** (constitution §4.14 and AGENTS.md rule 2, the owner, 2026-10-19) on base
commit **`dcd94ff`**, spec 039's reviewed tip (built, build-reviewed and accepted on its own branch,
not yet landed; it lands after 083). The branch carries 039's commits and this specification's
only. Not reviewed, not accepted. Evidence is under the worktree's `build/041/` (named below), the
logs under `build/`.

**When 039 lands:** this branch is rebased onto main (by the builder or the lane), and gets a
delta review of what the rebase changed. The ratchet here is against 039's base record
(`b91e0eaa4e`, main's accepted state when 039 was built), so the notes below separate 039's own
moves (already accounted in 039's landing notes and its three accept flags) from this
specification's, which are measured against 039's set (`ada941bc…`, copied with `cp -c -Rp` to
`build/old-artifacts/`, nlink 1) and 039's own records (`../wasi_python-039/build/evidence/latest-fast-065.json`,
`latest-full.json`).

**Question 80 at landing (condition C1):** answered, as recommended (`../decisions.md`: "for
projects that restrict AI-written contributions, the upstream draft is a facts sheet (spec 020's
six header lines) from which the owner writes and files in their own words"). The two drafts are
such facts sheets, unchanged.

### What changed

- **Patches.** `recipes/patches/pandas-3.0.6/0001-styler-templates-from-a-zip.patch` (879
  bytes, `0b6b418b…ce7d`) and `recipes/patches/networkx-3.7/0001-graph-atlas-from-a-zip.patch`
  (2,061 bytes, `3b8b6d2d…5384`), each `cmp`-equal to its `fix.patch` before that copy was removed
  (criterion 3); git records them as renames of the two `fix.patch` files. The two facts sheets
  moved unchanged (`git mv`) to `../upstream/patches/pandas-3.0.6/0001-styler-templates-from-a-zip.md`
  and `../upstream/patches/networkx-3.7/0001-graph-atlas-from-a-zip.md`; both `notes.md` and
  `../upstream/README.md`'s two rows name the carried paths.
- **Recipe.** networkx's sdist pinned in place of its wheel in `downloads/SHA256SUMS` and
  `scripts/00_download.sh`, in the same place (`fd77a511…e96a`, equal to the oracle lock's sdist
  hash). Step 70 unpacks, patches and stages `networkx/` beside pyyaml and markupsafe, passes its
  `PKG-INFO` to `--metadata` and `--entry-points`, and drops the `--wheel` line.
  `make_stdlib_zip.py` gains `--entry-points <PKG-INFO> <file>`, `sdist_entry_points` and the guard
  `check_entry_points` (by the computed `.dist-info` folder). `assemble_artifacts.py`: `WHEELS`
  without networkx; its notice from `build/networkx-3.7/LICENSE.txt`. The release's zero-patch
  count is 22 trees (21 on 039's tip, +1).
- **Judge.** The `files_from_the_zip` job and golden, and its check; the two gap checks widened and
  on both binaries; the unit check; `networkx` in `pins.SOURCE_PATTERNS` and
  `needs.SOURCE_COMPONENTS`; the four gaps removed from `tests/known_gaps.toml`;
  `tests/upstream/pandas.toml`: the eleven Styler files selected again, the two `styler-templates`
  classes emptied, the eight templates staged as `support`, and `pandas-io-formats`' cap 82 G →
  120 G; the synthetic set of the artifact rules' unit tests names networkx's sdist.
- `README.md` (the carried-patch count 7 → 9, the sdist rule, the default profile's edges, the
  "Out" list), `CHANGELOG.md` (under 0.1.0a8, naming both patch paths).

### Revisions and departures, each with its reason

The pre-build review (2026-10-17) was checked against the code at `dcd94ff`; the design still fits.
Where the text and the code differ:

1. **Built before 039 landed (condition C2).** The owner's stacked-build rule of 2026-10-19
   supersedes C2's order: built on 039's reviewed tip, rebased and delta-reviewed when 039 lands.
   033's landed `sdist_metadata` is used, as C2 asks.
2. **The two `styler-templates` classes are emptied, not removed** (spec 039's amendment F2 said
   "removes the two classes, their lists"). `tests/upstream/pandas.toml`'s own rule (spec 050,
   condition C1) keeps a class a fix emptied, "its id, an empty list and the closer that emptied
   it, as a record, and has no gap", as `zip-code-names` was kept when 051 emptied it; the judge's
   `rule_errors` and `class_findings` are written for that. The four gaps are removed.
3. **pandas' templates are staged beside its tests** (a judge change not in the text). With the
   eleven files selected again, `style/test_html.py`'s `env` fixture reads
   `pandas/io/formats/templates/` by path beside the tests, as in pandas' source tree, which the
   stage did not hold: `test_block_names` errored with `TemplateNotFound: 'html_style.tpl' not
   found in search path: '/upstream/tests/pandas/io/formats/templates'`
   (`build/041/pandas-groups.txt`). The eight templates are `support` files now, staged read-only;
   the product still reads its own copies from the zip.
4. **`pandas-io-formats`' cap rises 82 G → 120 G.** With the eleven files, the group ran out of
   fuel at 82 G after 1,739 passes; with the cap raised it finishes at 89.2 G with 1,972 passes,
   nothing failed (`build/041/pandas-io-formats-2.txt`). 120 G is 1.34× that, as 82 G was 1.40×
   main's 58.6 G. The `/upstream` family's caps sum to 2,557 G, under the 3,000 G budget.
5. **The unit check's two spellings.** `./x/PKG-INFO` and `x/PKG-INFO` are the same `Path`
   (pathlib drops `./`, and argparse's `type=Path` does too), so a path-string guard cannot tell
   them apart. The check also gives `x/../x/PKG-INFO` and the absolute path; the path-string mutant
   fails on `x/../x/PKG-INFO` (below). After the build review's F2 the guard takes the members
   gathered (`entries`), and a `main()` case holds the wiring; the path-string mutant now compares
   the entry points' `PKG-INFO` with the `--metadata` strings in `main`, and fails on
   `x/../x/PKG-INFO` there.
6. **Decision 8's sizes are 29 bytes larger per member** than the table: since spec 051 every code
   object carries the zip's guest path. The changes are the table's: `style_render.pyc` +168 bytes
   (112,234 → 112,402; deflated 42,947 → 43,034), `atlas.pyc` +171 (6,517 → 6,688; 3,159 → 3,231),
   `conftest.pyc` removed (10,127; 4,736).
7. **`LICENSES/networkx.txt` changes in its header line only**: `==== networkx-3.7-py3-none-any.whl:
   networkx-3.7.dist-info/licenses/LICENSE.txt ====` becomes `==== NetworkX LICENSE.txt ====`, as
   pyyaml's and markupsafe's name their tree files; the licence text is byte for byte the same
   (`LICENSE.txt` equals the wheel's, the pre-build review's `cmp`).
8. **The README count rises 7 → 9** and the release's tree count 21 → 22, each "relative to main"
   as written, counted on 039's tip.

### Acceptance criteria and their evidence

1. **Seen failing first. EXECUTED**, each on 039's set (`build/old-artifacts/`, `SHA256SUMS`
   `ada941bc…`) unless named otherwise:
   - `test_files_from_the_zip_job_matches_native`: `exit 1; stderr: jinja2.exceptions.TemplateNotFound:
     'html.tpl' not found in search path: '/usr/local/lib/python315.zip/pandas/io/formats/templates'`
     (`build/041/seen-failing-guest.txt`).
   - The Styler check, on both binaries: `6 finding(s), digest 297bd29c88bf`, every call and the
     loader assertion `TemplateNotFound: html.tpl`: `df.style.to_html()`, `df.to_latex()`,
     `df.style.to_string()`, `df.style.to_typst()`, `from_custom_template`, and
     `StylerRenderer: TemplateNotFound: html.tpl`, a finding, not an uncaught error
     (`build/041/seen-failing-findings.txt`, printed in full by `styler_findings.py`). The atlas
     check, on both binaries: `2 finding(s), digest 91e190939c85`, `nx.graph_atlas(100)` and
     `nx.graph_atlas_g()`, each `TypeError: filename must be a str or bytes object, or a file`.
   - With the networkx sdist staged but its patch file moved away (step 70 and 80 rebuilt, the set
     `build/041/no-patch-set/`): the atlas check fails as before, the same digest `91e190939c85`
     on both binaries. With the patch file back but `build/networkx-3.7` left unpatched:
     `test_source_tree_matches_its_tarball[networkx]` fails with `2 finding(s), digest 254b875a3ce1:
     networkx/generators/atlas.py: modified; networkx/generators/tests/test_atlas.py: modified`
     (`build/041/seen-failing-nopatch.txt`). Steps 70 to 90 rebuilt after it give `SHA256SUMS`
     `95b2f93a…` again, the set below (`build/041/build-restore.log`).
   - With either draft removed, `test_carried_patches_follow_the_rules` fails naming it:
     `recipes/patches/pandas-3.0.6/0001-styler-templates-from-a-zip.patch: no pull request draft at
     context/upstream/patches/pandas-3.0.6/0001-styler-templates-from-a-zip.md`, and the same for
     networkx's (`build/041/seen-failing-rules.txt`).
   - `test_an_sdists_entry_points_go_beside_its_metadata`: against 039's `make_stdlib_zip.py`,
     `AttributeError: module 'make_stdlib_zip' has no attribute 'sdist_entry_points'`; against the
     path-string mutant, `SystemExit: --entry-points x/../x/PKG-INFO …: no
     some_pkg-1.0.dist-info/METADATA member` (departure 5); passes on this one
     (`build/041/seen-failing-unit.txt`, `run_mutant.py`, `mutants/`).
   - `test_main_puts_entry_points_beside_metadata_or_stops` (the build review's F2, added after it):
     against a mutant without the guard's call in `main`, `Failed: DID NOT RAISE SystemExit`;
     against one that runs the guard before the `--metadata` inputs are gathered, `SystemExit:
     --entry-points x/PKG-INFO x/entry_points.txt: no some_pkg-1.0.dist-info/METADATA member` on
     the case that should write; against a path-string guard in `main`, the same stop on
     `--metadata x/../x/PKG-INFO`; passes on this one (`build/041/seen-failing-unit-main.txt`,
     `mutants/nocall`, `early`, `pathstr2`).
2. **The zip's names and bytes. EXECUTED** (`build/041/zip_names.py` → `criterion-2.txt`). Built
   from empty in the worktree (`scripts/build.sh`, 16 steps in 8 min 38 s, `build/build-041.log`):
   `python.wasm` is byte for byte 039's (`cmp`, `ab78e893…`). Sorted names (`unzip -Z1 … | LC_ALL=C
   sort`) differ only in `networkx/conftest.pyc`, removed (4,435 → 4,434 members); the shared
   members are the same bytes but `pandas/io/formats/style_render.pyc` and
   `networkx/generators/atlas.pyc` (sizes in departure 6); `networkx-3.7.dist-info/METADATA` and
   `entry_points.txt` are byte-equal to 039's. Decision 4's rule, step 2, on the built tree:
   `walk` of `build/pure-install/networkx` gives 289 members, the pinned wheel's `wheel_members`
   290 outside `.dist-info`; the one only in the wheel is `networkx/conftest.py`, and the one that
   differs is the patched `atlas.py`. `MANIFEST` changes in exactly Decision 8's lines: networkx's
   `pin` (sdist for wheel), two new `recipe` lines for the patches, the `recipe` lines of
   `00_download.sh`, `assemble_artifacts.py`, `make_stdlib_zip.py` and `70_zip.sh`, and
   `x-snapshot-zip`.
3. **The patches are what the drafts say. EXECUTED.** Each `recipes/patches/…` file was `cmp`-equal
   to its `fix.patch` before that copy was removed; `test_carried_patches_follow_the_rules` passes
   (each `Files:` line equals the paths `git apply --numstat` reads).
4. **The same bytes everywhere. EXECUTED**, by the branch's dry run (below): `rebuild from the pins`
   on ubuntu-24.04 and ubuntu-24.04-arm, `the same bytes from every host` and `verify` on the three
   systems pass, and `build and judge (arm64 macOS)` passes its zero-patch step with 22 trees.
5. **The judge. EXECUTED, without `--accept`.** `uv run pytest -n 3` once, at `39cf425`, clean,
   with this set, the wheel built from it (`dist/wasi_python-0.1.0a8-py3-none-any.whl`, 60,329,423
   bytes, SHA-256 `ece4329c…`) and the upstream kit fetched by hash (`build/041/full-judge.txt`;
   the record `build/041/latest-full.json`, SHA-256 `a0a19f88…`; judge hash `c2cf61e7…`):

   ```
   wasi_python v1: 568/647 pass · 77 gap · 2 blocked · 0 fail   (unit suite 1583/1590, 7 skipped)
     v1.1  artifact set        38/38
     v1.2  portable, sealed    120/121 blocked 1
     v1.3  data stack          120/196 gap 76
     v1.4  embedding           207/208 gap 1
     v1.5  rebuild from pins   39/39
     rules constitution rules  44/45  blocked 1
   blocked by: prior-art clones 1 · three systems 1
   trap entries with no trap here: c-stack-itertools-tee
   ratchet vs b91e0eaa4e: lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 25 · grew 165 · more 2 · judge changed: … and 33 more
   RED: 165 metric(s) grew
   2151 passed, 9 skipped, 77 xfailed in 914.28s (0:15:14)
   ```

   The two blocked checks are the worktree's (no prior-art clones; the three systems are the
   release's). The ratchet is against main's accepted state `b91e0eaa4e`, which 039 has not yet
   moved, so it holds 039's moves too. **039's own** (its landing notes and its three flags):
   grew 163 of the 165 (the tier A members and distributions, 035's member walks, the GB18030
   check, CPython's five groups), and its `fewer 1` (`pandas-frame` 10,852 → 10,851), which this
   specification turns into `more`. **This specification's own**, measured against 039's records
   on the same base (`build/041/moves.py` and `grew.py` against `../wasi_python-039/build/evidence/`
   `latest-full.json`, `latest-fast-065.json` and `latest-cpython-groups.json`; `moves-full.txt`,
   `grew-vs-039.txt`):
   - **Gained:** the job check; the Styler and atlas checks on both binaries (gap → pass on plain,
     new on snapshot); `test_source_tree_matches_its_tarball[networkx]`; the two emptied
     `styler-templates` classes (gap → pass). 039's four gaps are removed; the 77 gaps here are
     main's (065's CPython classes and traps among them).
   - **More passes (2):** `pandas-frame` 10,851 → 10,853 (accepted 10,852): `test_inspect_getmembers`
     passes again and `test_latex_repr` passes, both rendering through the Styler.
     `pandas-io-formats` 997 → 1,972 (accepted 977): the eleven Styler files run again.
   - **Grew, with causes:** `pandas-io-formats` +22.84 G (66.38 G → 89.22 G, +34.4%), the eleven
     Styler files' 975 more tests; `pandas-frame` +0.69 G (+0.20%), its two tests that now render;
     the other upstream groups move −0.09% to +0.11% (`numpy-others` +0.19 G the most, `numpy-lib`
     −0.09 G), INFERRED from the stage, which holds eight more files (spec 063, Decision 5: the
     guest's fuel depends on the whole stage). Beyond those, 48 metrics grew past the ratchet's
     0.01% against 039's records and 66 shrank by as much: plain checks by at most +0.05%
     (`test_plot_line_job_matches_native[plain]` +4.0 M) and snapshot checks by −0.45% to +0.42%,
     both directions, from a set whose plain binary is unchanged. INFERRED: layout, the zip's
     directory (one member fewer, two changed) and the snapshot heap made from it, as spec 091
     records for numpy-core. Two of them are past the accepted value where 039's were not, so
     they are this specification's own growth lines against main: `test_unbuffered_output_survives_a_hard_exit[snapshot]`
     1,212,377 → 1,214,000 (+1,623; accepted 1,213,059) and
     `test_the_readmes_encoding_workaround_reads_what_iconv_cannot` 6,040,442,423 →
     6,042,516,382 (+2,073,959, +0.034%; accepted 6,040,380,177); each is the same on two runs per
     set, and moves with the set (`build/041/probe-two-growths.txt`). Decision 8 said no accepted
     metric should grow beyond the judge's noise; these are for the build review to judge.
   - **Shrank:** the zip −4,695 bytes (38,726,339 → 38,721,644), the snapshot −3,308 (45,363,590
     → 45,360,282); plain `-c pass` −25,325 (218,073,038 → 218,047,713, one member's fuel; 039's
     slope 25,120), snapshot `-c pass` −19,241 (20,351,493 → 20,332,252) (`build/041/measure.json`,
     the judge's driver).
   - **New metrics** (`measure.json`): the job 8,931,427,067 on plain; the Styler check
     5,939,204,115 plain and 5,540,450,869 snapshot; the atlas check 3,412,046,711 plain and
     3,063,861,294 snapshot. `import networkx` is +35,822 plain and +4,880 snapshot against 039's.

   The goldens reproduce under the pinned oracle (`test_goldens_reproduce_under_the_pinned_oracle`
   passed; the new golden was written by both seeds, `build/041/regen_one.py`). The new job passes
   `ruff check` and `ruff format --check`. Spec 051's callback scan,
   `test_callbacks_have_the_types_cpython_calls`, passes (the patches change Python only).
   `uv run python tests/harness/sameness.py` is the lane's, between this record and its own.
   The lane accepts, after 039, with:
   - `--accept-judge "spec 041: the files_from_the_zip job and golden; the Styler and atlas checks widened, on both binaries, and their two gaps removed; the unit check for --entry-points; networkx in the source-tree patterns; pandas' eleven Styler files selected again, the two styler-templates classes emptied and their gaps removed, the eight templates staged where pandas' tests read them, pandas-io-formats' cap 82 G -> 120 G; the artifact rules' synthetic set names networkx's sdist; networkx's packages.toml reason (now its sdist, which carries its tests; spec 067's to run them); the unit check's main() case (the build review's F2)"`;
   - `--accept-growth "spec 041: pandas-io-formats +22.8 G and pandas-frame +0.69 G run the Styler tests that now pass (+975 and +2 passes); the other upstream groups move -0.09% to +0.11% with a stage of eight more files; the rest, within +0.05% plain and +-0.45% snapshot both ways, moves with the rebuilt zip directory and snapshot heap (one member fewer, two changed; python.wasm unchanged), among them test_unbuffered_output_survives_a_hard_exit[snapshot] +1,623 and the encoding workaround +2.07 M: neither program imports pandas or networkx, and the hard-exit program costs 19,554 less on plain"`.
   No `--accept-fewer-passes`: 039's falls back.
6. **The release. Met at the lane** (the build review's F7): the branch dry run below cannot be
   green, since CI ratchets against the accepted progress in the commit, which does not yet hold
   039's moves. Criterion 6 is met by **the lane's dry run on the accepted commit**; its run
   number goes here when the lane records it.

### The branch dry run

`gh workflow run release.yml --ref spec/041-files-read-by-path-from-the-zip` on `39cf425`, run
**39345809724**: every job passes but three, and each of the three is red only for growth (0 fail,
lost 0), the darwin-arm64 shards that ratchet against main's accepted metrics:
- `judge (macos-15, own-guest)`: 299/647 pass, 0 fail; `grew 125` (the first lines
  `test_binary_is_a_core_wasm_module[snapshot]` bytes 44,633,983 → 45,360,282 and
  `test_dotted_builtins_keep_their_import_names` on both binaries: tier A's, 039's);
- `judge (macos-15, own-embedding)`: 157 pass, 0 fail; `grew 24` (tier A's start growth, +50 M plain
  and +4.7 M snapshot per check, 039's; the log prints the first three lines only);
- `judge (macos-15, upstream-macos)`: 4 pass, 36 gap, 0 fail; `grew 2`: `cpython-fs` 59.84 G →
  62.37 G (039's measured +2.55 G) and `numpy-lib` 132.02 G → 132.22 G (039's own record has
  132.31 G).
All are growth lines; none is G7 or a failure. The rebuild jobs, the same-bytes job, the three
`verify` jobs, the zero-patch step (22 trees) and every Linux and Windows shard pass.

**The artifact set** (`build/artifacts/`): `SHA256SUMS` `95b2f93a12463b705bbb4bebc9b3553ffd8ca7f45f399b2132e0ffa2d30cf5ff`.

| file | bytes | SHA-256 |
|---|---|---|
| `python.wasm` | 41,099,661 | `ab78e8931e76aaf996d74d3b7766fcdf0249119faab4d0dfa153a6b14d6887db` (039's) |
| `python-snapshot.wasm` | 45,360,282 | `aa14e8e09a3ceeccd191bb4a7e04373b36b95a9a0cdc3fc4b58861282ab4e1de` |
| `python-stdlib.zip` | 38,721,644 | `f7d96aab1a8f8fe2ded11e8f34cf4c2d762da2c9f8c67420f1da0330e1ea9aa0` |
| `MANIFEST` | 19,126 | `703b2ee18a36ae35d89187451ba7ee2ab5bfcfa01dae48956575a94b40185e42` |

### The build review and its answers

The build review (2026-10-19, a fresh agent; verdict "lands once F1"; its record matched this
one exactly) is answered here:
- **F1, fixed:** `tests/upstream/packages.toml`'s networkx reason now says it is pinned as its
  sdist since spec 041, which carries its tests, and that staging and running them is spec 067's
  (`kind = "later"` and the closer kept). Named in `--accept-judge`.
- **F2 (Low), fixed:** `check_entry_points` takes the members gathered (`entries`); the `origins`
  dict is gone. A `main()` case in the unit file's existing pattern holds the wiring, seen failing
  on three mutants (criterion 1). This changes `make_stdlib_zip.py`, so the worktree set's
  `MANIFEST` `recipe` line for it is stale until the next build; the zip's bytes do not depend on
  the change (the guard only stops). The rebase onto main rebuilds anyway, and the branch needs a
  new dry run for this commit.
- **F3 (Low), fixed:** `build/041/measure-rlgqqr8a/` removed; the set's zip has `nlink` 1 again.
- **F4 (note), taken:** the layout reason is in `--accept-growth`.
- **F5 (note):** the emptied `pandas-io-formats` `styler-templates` class keeps its broad `match`,
  as `zip-code-names` kept its text; it has no gap, so a future match is still red. Narrowing it
  would be a judge change of its own.
- **F6 (note):** the facts sheets moved unchanged, as Decision 6 ordered, and still read "When
  spec 041 is built, this file moves"; a tense sweep across them and 046's and 047's is a
  `context/`-only follow-up if the owner wants one.
- **F7 (note), taken:** criterion 6 is met by the lane's dry run on the accepted commit.

**For the lane.** After 039 lands, rebase onto main: the conflicts to expect are none in this
specification's own files unless 037, 043 or 042 land first, in which case step 70's `--wheel`,
`--metadata` and `remove` lines, `00_download.sh`, `SHA256SUMS`, `assemble_artifacts.py`'s
`WHEELS` and licences, `pins.SOURCE_PATTERNS`, `needs.SOURCE_COMPONENTS`, the release's tree count
(22 plus theirs), the README's patch count (9 plus theirs) and `tests/upstream/pandas.toml` take
both sides; then the delta review.

#### Rebased onto wave/02 (`e8ba20a`, wave 01 landed; on 039's rebased tip `2d0a583`; 2026-10-20)

041's base `dcd94ff` was checked (`git merge-base --is-ancestor`; `dcd94ff..HEAD` is 041's three
commits), then `git rebase --onto` 039's tip as rebased onto wave/02 (`8e5df6a`; the context-only
`2d0a583` follows it). Two hunks conflicted, both in the build commit:

1. **`README.md`, the results row:** wave/02 says `upstream patches carried: 8` (087 added regex's
   0002), 041 said 9 (7 + 2). Resolved to **10** (8 + 041's two). A semantic change only of the
   number; 041's text elsewhere says "rises by two", which still holds.
2. **`tests/known_gaps.toml`, one region:** 039's side (via the lane's rebase onto 97be88a) had
   078's nine `c-stack-*` trap gaps removed and 039's four Tier A gaps added; 041's side had the
   nine trap gaps (its old base) and 039's four removed. Resolved by dropping both: 078's removal
   and 041's removal both hold. Checked: the file equals 039's rebased file without its four Tier A
   gaps and their comment, byte for byte otherwise (`diff`).

Git merged the rest; files both wave/02 and 041 touch, each read: `CHANGELOG.md` (041's two
entries under `## 0.1.0a8 — unreleased`, after 039's three; the heading unchanged),
`.github/workflows/release.yml` (085's lines beside the zero-patch count of 22 trees; 087 added no
tree), `scripts/assemble_artifacts.py` (087's `MODIFIED` line is for Apache-2.0 files only; pandas
and networkx are BSD-3-Clause, so 041's patches need no line there), `context/upstream/README.md`
(087's row 24 beside 041's two rows). The other two commits replayed cleanly.

**Checked after the rebase:** `ruff check` and `ruff format --check` clean; `tests/checks/test_rules.py`
and `tests/unit/test_build_scripts.py` pass (71 passed, 1 skipped). **The fast tier** on this tip,
against the worktree's old private set `95b2f93a` (`uv run pytest -m "not slow" -n 3`,
`build/041/fast-wave02.txt`, record `build/041/latest-fast-wave02.json`): 565/693 pass, 1 gap,
2 blocked, 4 fail; ratchet vs `47b3695c2d`: lost 4, gained 15, grew 142. **The four failures are
the rows that need the rebuilt set**, which the lane's rebuild settles:
- `test_manifest_recipes_match_the_tree`: the old MANIFEST lacks 087's
  `recipes/patches/regex-2026.9.29/0002-timeout-ticks.patch`, and `assemble_artifacts.py` (087) and
  `make_stdlib_zip.py` (041's F2) changed since that build;
- `test_a_timeout_past_2_147_seconds_fires[plain]`, `[snapshot]`: the old binary has no 0002 patch
  (`completed`, where the timeout should fire);
- `test_source_tree_matches_its_tarball[regex]`: the worktree's regex tree predates 0002
  (`src/_regex.c: modified`).
Against the old base's fast record, the growth set gains ten rows, all wave 01's new checks growing
by tier A's start cost (039's claim): 087's two DENY_ALL checks and 083's and 089's three
file-facts and stage checks, each on both binaries.

**The claim list: the rows 041 changes**, against main's accepted state `47b3695`, with 039 in the
same acceptance:
- **New checks:** `test_files_from_the_zip_job_matches_native`;
  `test_pandas_styler_renders_from_the_zip[snapshot]` and `test_networkx_atlas_reads_from_the_zip[snapshot]`;
  `test_source_tree_matches_its_tarball[networkx]`; the unit rows
  `test_an_sdists_entry_points_go_beside_its_metadata` and
  `test_main_puts_entry_points_beside_metadata_or_stops`.
- **Gaps that close (039's, made passing):** `test_pandas_styler_renders_from_the_zip[plain]`,
  `test_networkx_atlas_reads_from_the_zip[plain]`, `test_upstream_class[pandas-frame-styler-templates]`,
  `test_upstream_class[pandas-io-formats-styler-templates]` (the classes kept, emptied).
- **Retired checks:** none.
- **Passes that move:** `pandas-frame` 10,853 (accepted 10,852; 039 alone 10,851):
  `test_inspect_getmembers` and `test_latex_repr` render. `pandas-io-formats` 1,972 (accepted 977;
  039 alone 997): the eleven Styler files run again.
- **Rows that grow, and why:** `pandas-io-formats` +22.8 G over 039's (the 975 Styler tests) and
  `pandas-frame` +0.69 G (its two); the other upstream groups −0.09% to +0.11% (eight more files on
  the stage); layout moves of the rebuilt zip directory and snapshot heap, within +0.05% plain and
  ±0.45% snapshot both ways, among them `test_unbuffered_output_survives_a_hard_exit[snapshot]`
  (+1,623) and `test_the_readmes_encoding_workaround_reads_what_iconv_cannot` (+2.07 M). The zip
  shrinks by 4,695 bytes and the snapshot by about 3,300 against 039's set; `python.wasm` does not
  change.
- **Judge files:** `tests/checks/test_v1_3_default_profile.py`, `tests/harness/jobs.py`, `needs.py`,
  `pins.py`, `tests/jobs/files_from_the_zip.py` and `.expected` (new), `tests/known_gaps.toml`,
  `tests/unit/test_artifact_rules.py`, `test_build_scripts.py`, `tests/upstream/pandas.toml`,
  `packages.toml` and the two `styler-templates` lists.

**The exact flags** (041's parts; the lane joins them with 039's; no `--accept-fewer-passes` for the
chain):

```
--accept-judge "041: the files_from_the_zip job and golden; the Styler and atlas checks widened, on both binaries, and their two gaps removed; the unit check for --entry-points and its main() case (the build review's F2); networkx in the source-tree patterns; pandas' eleven Styler files selected again, the two styler-templates classes emptied and their gaps removed, the eight templates staged where pandas' tests read them, pandas-io-formats' cap 82 G -> 120 G; the artifact rules' synthetic set names networkx's sdist; networkx's packages.toml reason (now its sdist, which carries its tests; spec 067's to run them)"
--accept-growth "041: pandas-io-formats +22.8 G and pandas-frame +0.69 G run the Styler tests that now pass (+975 and +2 passes); the other upstream groups move -0.09% to +0.11% with a stage of eight more files; the rest, within +0.05% plain and +-0.45% snapshot both ways, moves with the rebuilt zip directory and snapshot heap (one member fewer, two changed; python.wasm unchanged), among them test_unbuffered_output_survives_a_hard_exit[snapshot] +1,623 and the encoding workaround +2.07 M: neither program imports pandas or networkx, and the hard-exit program costs 19,554 less on plain"
```

CI for this entry comes from the wave's run; the branch dry run 39345809724 was on the old base.
