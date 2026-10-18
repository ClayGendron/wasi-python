# 041 — Files read by path from the zip

- **Status:** drafted 2026-10-17. It changes the build recipe and the artifact set, so it is
  reviewed once more before it is built (constitution §5.6). It is build-class: it touches
  `scripts/`, `recipes/patches/`, `downloads/SHA256SUMS` and the release workflow (§5.7). It
  carries two upstream patches (§4.1), so the pre-build review reads both patches and both pull
  request drafts (spec 020, Decision 8).
- **Owner:** Clay Gendron
- **Kind:** two carried patches (`recipes/patches/pandas-3.0.6/`, `recipes/patches/networkx-3.7/`)
  with their pull request drafts; the build recipe (networkx's pin moves from its wheel to its
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
  - pandas' and networkx's contributor policies on automated contributions (READ, their
    contributor guides, 2026-10-17).

  The evidence is in `../upstream/5-pandas-styler-from-a-zip/evidence/` and
  `../upstream/6-networkx-atlas-from-a-zip/evidence/`.

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

1. **Both are fixed in the packages' own source, as carried patches (§4.1).** A recipe was
   looked for first (§4.1, §6.2), and none fits:
   - **Templates or the atlas as files beside the zip.** Rejected. The path pandas computes is
     inside the zip's own file name, so no folder can exist there. Loose files would also add to
     the artifact set, which is the product (§4.6).
   - **A stand-in module for jinja2's loader, or a recipe that swaps `StylerRenderer.loader`
     after import.** Rejected. It changes upstream behaviour at run time without changing the
     source, so it hides a source change from the tree check, the `MANIFEST` and the CHANGELOG.
     §7 forbids exactly that. Spec 035's run-time replacements are different: they replace
     whole stdlib functions with ours, and judge checks prove the results equal upstream's
     (question 60).
   - **Giving 035's `Traversable` an `__fspath__` or a `read`, so that `gzip.open` takes it.**
     Rejected. `os.fspath` would give a path no `open` can read. A `read` attribute would make
     `gzip.open` treat the path object as a stream; it would also differ from `zipfile.Path`,
     which has neither (035, Decision 6).
   - **`importlib.resources.as_file`.** Rejected. It copies the resource to a temporary file,
     and with nothing writable by default there is no temporary folder (spec 025, §4.15).

   Each fix is a few lines, correct on every install, and wanted upstream, so each is carried as
   a patch with its pull request drafted, and deleted once a pinned release carries it.
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
   - **EXECUTED while drafting** (`../upstream/5-pandas-styler-from-a-zip/evidence/`): in the
     guest with stock pandas, six Styler calls raised `TemplateNotFound: html.tpl`; with the
     patched member they gave output equal to native CPython 3.15.0, by length and SHA-256:
     `df.style…to_html()` (1,009 characters), `df.to_latex()` (137),
     `df.style.to_latex(environment="longtable", caption=…)` (246), `to_string()` (44),
     `to_typst()` (112), and the custom template (1,028); the loader was `PackageLoader`.
     Natively, the patched module keeps `FileSystemLoader`.
   - The patch adds no pandas test (the draft says why: a zip-imported pandas cannot be built
     in pandas' test suite, and a forced `PackageLoader` branch fails under its editable CI).
     This project's judge holds the behaviour (Decision 7).
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
   carried patch is the pull request, test included, as numpy's is. The zip never holds it
   (step 70 skips `tests/`).

   **EXECUTED while drafting** (`../upstream/6-networkx-atlas-from-a-zip/evidence/`): natively,
   with the stock wheel on `PYTHONPATH`, `nx.graph_atlas(6)` raised the `TypeError`; with the
   patched package zipped it gave `[(0, 1), (0, 2)]` and `graph_atlas_g()` 1,253 graphs. The new
   test failed without the fix and passed with it; `test_atlas.py` gave 9 passed, and
   `networkx/generators/tests` gave 598 passed and 34 skipped (pytest 8.4.2, uv's CPython
   3.15.0a3). In the guest, `graph_atlas(100)` and `graph_atlas_g()` gave results equal to
   native.
4. **How a wheel takes a patch: it does not; the package comes from its sdist.** Spec 020
   applies a patch to a source tree unpacked from a pinned tarball, and §4.1 states the rule in
   those words. networkx is a wheel in spec 039. This specification pins **networkx's sdist in
   place of its wheel** and stages it as 039 stages pyyaml and markupsafe. The rule, for this
   and every later pure-Python package that needs a patch: **pin its sdist, unpack it, call
   `patch_tree`, stage its package folder in `build/pure-install/`, and take its metadata from
   the sdist.** A wheel is never unpacked and patched.
   - **Why not patch the wheel.** That needs a second kind of patched archive in three places:
     a step that unpacks and repacks a wheel, the judge's `tree_drift` (it extracts tarballs),
     and spec 020's `<top>` rule (the top of a pinned tarball, from its file name). It would add
     an option to `make_stdlib_zip.py` that packs a wheel from a folder. That is more new
     machinery than the sdist route, for the same bytes. The sdist is also what upstream
     releases as source, so the carried patch and the pull request are made against the same
     files.
   - **The same members, EXECUTED.** The sdist's `networkx/`, walked by step 70's `walk`, gives
     289 members; the wheel's `wheel_members` gives 290 outside `.dist-info`. The 289 are the
     same names and bytes. The one left over is **`networkx/conftest.py`, which is not packed**,
     because `walk` skips `conftest.py` (`SKIP_NAMES`) and `wheel_members` does not. It is pytest's configuration; nothing imports
     it at run time. The sdist's `PKG-INFO` equals the wheel's `METADATA` byte for byte, and
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
   - `--entry-points <PKG-INFO> <file>` (repeatable) packs `<file>`, bytes unchanged, as
     `<name>-<version>.dist-info/entry_points.txt`, with the folder name computed from the
     `PKG-INFO` exactly as `--metadata` computes it (033, Decision 2: the same function).
   - The build stops, with one line naming the file, when the `PKG-INFO` is not also given with
     `--metadata` (an entry-points file never goes into a folder without its `METADATA`).
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
     `../upstream/patches/networkx-3.7/0001-graph-atlas-from-a-zip.md` (`git mv`, unchanged). Each
     folder's `fix.patch` is copied, byte for byte, to the patch path. The numbered folders keep
     `notes.md` and `evidence/`. They are drafted now, outside `upstream/patches/`, because
     spec 020's rules fail a draft there whose patch is not yet carried.
7. **The checks.** Each is seen failing first (Acceptance, criterion 1).
   - **A golden job, `tests/jobs/files_from_the_zip.py`**, run on the plain binary and compared
     with its `.expected` like the others (`jobs.compare`, the versions line first:
     `pandas`, `jinja2`, `networkx`). It prints in full: `df.style.set_uuid("job")` with a
     format and a highlight `.to_html()`; `df.to_latex()`; `df.style.to_latex(environment=
     "longtable", caption=…)`; `.to_string()`; `.to_typst()`; a custom template written to the
     job's output folder that extends `html_table.tpl`, through
     `Styler.from_custom_template(out_dir, html_table=…)`; `nx.graph_atlas(100)`'s name and
     sorted edges; `len(nx.graph_atlas_g())` and its total edge count. The drafting probe
     (`evidence/files.py`) is its model: the job prints the texts, not their digests. The
     uuid is fixed, so the HTML holds no random id. The oracle runs stock pandas and networkx,
     so equal output proves the patches change no result. `jobs.JOBS` gains it.
   - **Spec 039's two known-gap checks become passing checks.**
     `test_pandas_styler_renders_from_the_zip` and `test_networkx_atlas_reads_from_the_zip` run
     on `[plain, snapshot]` (039 runs them on plain only). The Styler check also calls
     `to_string()`, `to_typst()` and `from_custom_template`, and asserts that
     `type(StylerRenderer.loader).__name__ == "PackageLoader"` in the guest, so the patched
     branch is the one that served it. The atlas check also calls `graph_atlas_g()`. Each still
     asserts no findings. Their two entries leave `tests/known_gaps.toml`.
   - **Unit, `test_an_sdists_entry_points_go_beside_its_metadata`** in
     `tests/unit/test_build_scripts.py`: a temporary `PKG-INFO` (`Name: Some.Pkg`,
     `Version: 1.0`) and an `entry_points.txt`; the members built from `--metadata` and
     `--entry-points` are `some_pkg-1.0.dist-info/METADATA` and `…/entry_points.txt` with the
     files' bytes; `--entry-points` without the matching `--metadata` stops with one line naming
     the file. It calls the functions directly, as 033's unit checks do.
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
them, and the owner holds a drafted pull request for each.

## Design

| file | change |
|---|---|
| `recipes/patches/pandas-3.0.6/0001-styler-templates-from-a-zip.patch` | new: `../upstream/5-pandas-styler-from-a-zip/fix.patch`, byte for byte (Decision 2) |
| `recipes/patches/networkx-3.7/0001-graph-atlas-from-a-zip.patch` | new: `../upstream/6-networkx-atlas-from-a-zip/fix.patch`, byte for byte (Decision 3) |
| `context/upstream/patches/pandas-3.0.6/0001-styler-templates-from-a-zip.md` | moved from `../upstream/5-pandas-styler-from-a-zip/pr.md` (Decision 6) |
| `context/upstream/patches/networkx-3.7/0001-graph-atlas-from-a-zip.md` | moved from `../upstream/6-networkx-atlas-from-a-zip/pr.md` (Decision 6) |
| `context/upstream/README.md` | the two rows say the drafts moved to `patches/` and the patches are carried |
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
- **Sending the pull requests:** the owner's (§7). Both projects ask that their descriptions be
  the contributor's own words, so the drafts hold the facts, not the text (the drafts say so).
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
     every call, and the atlas check's name the `TypeError` for both calls; on `snapshot` too;
   - with the networkx sdist staged but its patch file removed, the atlas check fails as
     before; with the patch file present but `build/networkx-3.7` left unpatched,
     `test_source_tree_matches_its_tarball` fails naming `networkx/generators/atlas.py`;
   - with either draft removed, `test_carried_patches_follow_the_rules` fails naming it;
   - `test_an_sdists_entry_points_go_beside_its_metadata`: against 039's `make_stdlib_zip.py`
     (no `--entry-points`).
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

None open here. The owner's answer to question 32 (carry a fix rather than wait for upstream,
with its pull request drafted) is applied as written. Sending either pull request is the owner's
(§7), and both projects ask that the description be the contributor's own words, which the
drafts in `../upstream/5-pandas-styler-from-a-zip/pr.md` and
`../upstream/6-networkx-atlas-from-a-zip/pr.md` respect.

## Landing notes

Not built.
