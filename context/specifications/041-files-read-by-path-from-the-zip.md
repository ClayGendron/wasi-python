# 041 — Files read by path from the zip

- **Status:** **Spec 051's callback scan binds this build** (051, Decision 4a; written in when 051 landed): `test_callbacks_have_the_types_cpython_calls` is green, and a mismatch it finds is fixed by a carried patch or an upstream release, never by an exclusion. drafted 2026-10-17. Revised the same day against its pre-build review
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
- **Owner:** Clay Gendron
- **Kind:** two carried patches (`recipes/patches/pandas-3.0.6/`, `recipes/patches/networkx-3.7/`)
  with their upstream facts sheets; the build recipe (networkx's pin moves from its wheel to its
  sdist in `downloads/SHA256SUMS` and `scripts/00_download.sh`; `scripts/steps/70_zip.sh`;
  `scripts/make_stdlib_zip.py` gains `--entry-points`; `scripts/assemble_artifacts.py`); judge
  additions and changes (one golden job, the two known-gap checks of spec 039 widened and their
  gaps removed, one unit check, the source-tree patterns); the release workflow's tree count;
  `README.md`, `CHANGELOG.md`.
- **Depends on:** 039 (tier A, not yet built), which brings jinja2 and networkx, the two
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

Not built. At landing, record here the answer question 80 had (condition C1).
