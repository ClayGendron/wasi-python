# 173: drawsvg draws SVG and HTML

- **Status:** drafted 2026-10-31, to be reviewed before it is built (the artifact set and the build recipe: a package joins the stdlib zip, as 165 and 167 did). The owner asked for drawsvg on 2026-10-31 and approved its MIT licence (decisions.md, "drawsvg, and SVG to PNG through cairo"). Amended the same day against its pre-build review, `../reviews/173-drawsvg-draws-svg-and-html-spec-2026-10-31.md` ("Fit to build after amendments"): its Medium and five Lows taken (its Disposition says where).
- **Date:** 2026-10-31
- **Owner:** Clay Gendron
- **Kind:** **a judge change** (a new kind in `tests/upstream/packages.toml`), one pure-Python package, no carried patch; not structural: nothing under `src/` changes, and the guest's imports and exports do not change.
- **Depends on:** landed: 041 (pure packages in the zip), 063 (own suites), 157. 171 lists the set's packages; drawsvg joins that list with no change to it. 174 follows and turns drawsvg's raster calls on; 173 lands first and alone.
- **Research it stands on:** `../research/2026-10-31-drawsvg-and-svg-to-png.md`, §1 (EXECUTED: drawsvg 2.4.2 in the guest; READ: no test suite in its sdist or its repository). **Drafting reads** (READ, 2026-10-31): drawsvg 2.4.2's `drawing.py`, `raster.py`, `video.py`, `color.py`; `scripts/steps/70_zip.sh`, `scripts/assemble_artifacts.py`, `tests/harness/shards.py:335-420`, `tests/upstream/packages.toml`, `tests/harness/jobs.py:33`.

Labels: EXECUTED means run and seen; READ means read from a file, cited; INFERRED means reasoned.

## The problem

1. The set draws charts through matplotlib, but has no free-form vector drawing API. drawsvg builds SVG from Python objects: shapes, paths, text on a path, gradients, markers, and SMIL animations with playback controls.
2. The owner wants high-quality images, animations, interactive HTML and SVGs. drawsvg's core serves SVG, HTML and browser animation with no compiled code (the memo, §4).
3. drawsvg has no test suite anywhere (the memo, §1). Spec 063's rule needs every package to run its own tests, and `packages.toml`'s four kinds (`tests/harness/shards.py:335`) have none for a package that ships none.

## Decisions

### 1. The pin: drawsvg 2.4.2's wheel

`drawsvg-2.4.2-py3-none-any.whl`, 44,175 bytes, SHA-256 `b1c101e187aa395cb13c039549e4f26fb7b7ee03974f53dc9798436463781bf1`, from PyPI (READ: PyPI's JSON, checked by the spike). It is pure Python and carries no patch, so its wheel serves, as `pdfplumber`'s does (`scripts/assemble_artifacts.py:160`). `downloads/SHA256SUMS` and `scripts/00_download.sh` gain it; step 70 packs it with a `--wheel` line beside pdfplumber's (`70_zip.sh:163`). `drawsvg/widgets/` is packed, so `import drawsvg.widgets` names `ipywidgets` as natively. If PyPI has a newer drawsvg at build, every 2.4.2 moves with it, and the `none` reason is read again at that version: its sdist, and its repository at the release's tag.

### 2. Nothing is added for the extras

drawsvg's optional parts stay out, each failing by name:

- **Rasterizing** (`rasterize`, `save_png`, `save_gif`, `save_mp4`, `save_spritesheet`) raises `ImportError` from `drawsvg/raster.py:9-26` and `video.py:5-15`. 174 turns on all but `save_mp4`.
- **`drawsvg.color`** raises `ImportError` (it needs pwkit).
- **`embed_google_font`** raises `URLError: unknown url type: https`: the guest has no `ssl` module, so no HTTPS handler, and no network either.

### 3. The message stays drawsvg's

drawsvg's `ImportError` says "Install with `python3 -m pip install "drawsvg[all]"`". In the guest, pip does not apply. The text is not rewritten: a patch to an exception's words is not unavoidable (constitution §4.1), and a stand-in `raster.py` would hide the real module. 174 removes the message for the four raster calls. For `drawsvg.color`, `save_mp4` and, until 174 lands, the raster calls, the documents say what raises and why (Decision 6).

### 4. A package with no suite is a kind of its own

`packages.toml` gains a fifth kind, `none`: the project ships no tests at its release or in its repository. It needs a `reason`, saying where that was read, and `checked_by`, a list of golden jobs that run the package. `package_errors` (`tests/harness/shards.py:362`) refuses a `none` entry:

- whose `reason` or `checked_by` is empty;
- whose `checked_by` names a job not in `jobs.JOBS` (`tests/harness/jobs.py:33`);
- when `tests/upstream/<name>.toml` exists, since a suite then exists;
- when a job it names does not import the package: the job's source, `tests/jobs/<job>.py`, parsed with `ast`, has no `import` or `from` of one of the package's import names, read from its `recipes/snapshot-packages.txt` line (`drawsvg: drawsvg`).

A `via` naming a `none` entry stays refused, since `via` reaches only `suite` or `later` (`:388-397`). `KINDS` (`:335`) and the file's header comment name it: `none` is for a project that ships no tests at its pinned version, and a version move reads its sdist and its repository's tag again and rewrites `reason`. The fixture `PACKAGES_TEXT` (`tests/unit/test_shards.py:220`) gains one `none` entry, its package in `NAMES` (`:252`) and its `checked_by` a name in `jobs.JOBS`; `BAD_PACKAGES` (`:271`) gains the five refusals above and the refused `via` as rows over it.

Why not the other kinds. `via` needs a suite that reaches the package; none does. `later` promises a suite a specification will run; none will exist. A project-written group under `tests/upstream/` would claim to be drawsvg's own tests. A new kind says the fact.

drawsvg's entry: `kind = "none"`, `reason = "drawsvg 2.4.2 ships no tests: none in its sdist, none in its repository at master (read 2026-10-31)"`, `checked_by = ["vector_drawings"]`.

### 5. The checks

- **Golden job `vector_drawings`** (`tests/jobs/vector_drawings.py`, joining `JOBS`; its check `test_vector_drawings_job_matches_native` in `tests/checks/test_v1_3_default_profile.py`). The oracle's `pyproject.toml` pins `drawsvg==2.4.2`. drawsvg is pure Python, so the job holds the guest's CPython to native's on drawsvg's code; whether drawsvg's SVG is right only upstream could test. The job's docstring and the `none` reason say so. Each line prints a length and a SHA-256:
  - **SVG.** The README drawing the memo ran (lines, shapes, a path, text on a path, an arc, a marker, a gradient), through `as_svg()`, and `save_svg` read back equal to it.
  - **HTML.** The same drawing through `as_html()` and `save_html`.
  - **Rich display.** `_repr_svg_()` after `random.seed(0)`, since it randomizes element ids (`drawing.py:433`).
  - **Native animation.** A drawing with `SyncedAnimationConfig(duration=8, show_playback_progress=True, show_playback_controls=True)`, a circle with three key frames and a text sequence, through `as_svg()` and `as_html()`.
  - **Frame callbacks.** A `FrameAnimation` with a `callback`, three frames drawn by `draw_frame`; the frame count, the callback count and each frame's SVG.
  - **Scale.** A 1,000-circle drawing's SVG.
  - **Embedding and structure.** An `Image(..., embed=True)` of a small PNG from the job's data folder (the file read, base64, the MIME guess), and a drawing with a `Group`, `Use`, `ClipPath` and `Mask`.
- **Guest check `test_drawsvg_names_what_the_set_lacks`** (the same file). `rasterize()` raises `ImportError` whose cause names `cairosvg`; `drawsvg.color` raises `ImportError`; `embed_google_font` raises `URLError`; `import drawsvg.widgets` raises `ModuleNotFoundError` naming `ipywidgets`. 174 rewrites its first row. Seen failing first on a set without drawsvg.

### 6. The files of the set and the documents

- `scripts/assemble_artifacts.py`: `PACKAGES` and `WHEELS` gain drawsvg; its notice is its wheel's `licenses/LICENSE.txt` (MIT), through `wheel_licences` (`:581`).
- `tests/harness/paths.py`: `LICENCE_COMPONENTS` (`:102`) and `PACKAGES` (`:193`) gain it.
- `recipes/snapshot-packages.txt`: `drawsvg: drawsvg`.
- **Packages page** (`docs/reference/packages.md`): a row in the pure-Python table, family "drawing": "drawsvg 2.4.2 | vector drawings and SMIL animations, saved as SVG or HTML". The golden-job sentence names drawsvg.
- **Limitations page**: drawsvg's raster calls, `drawsvg.color` and `embed_google_font` raise, the last because the guest has no `ssl` and no network; the `pip` advice in the first two messages does not apply. Once 174 lands, the raster line narrows to `save_mp4`.

### 7. Size and fuel, measured

drawsvg's source is 131 KB; as bytecode in the zip, about 50 KB deflated (INFERRED). Its members add to the zip's directory, which every plain start reads: about 26 k fuel a member (INFERRED, 044 and 045). Importing drawsvg cost 739 M fuel from source in the spike (EXECUTED); from bytecode it costs less. The builder records the zip's and the wheel's bytes, the fuel of an empty program and of `import drawsvg`, and the news file claims each growth.

## Intent

A program in the guest draws with drawsvg and gets the same SVG and HTML bytes as native Python, animations and frame callbacks included. What drawsvg cannot do here raises a named exception.

## Design

- Recipe: `downloads/SHA256SUMS`, `scripts/00_download.sh`, `scripts/steps/70_zip.sh`, `scripts/assemble_artifacts.py`, `recipes/snapshot-packages.txt`.
- Judge: `tests/jobs/vector_drawings.py` and its `.expected`; `tests/harness/jobs.py`; `tests/jobs/oracle/pyproject.toml` and its lock; `tests/checks/test_v1_3_default_profile.py`; `tests/harness/shards.py` and `tests/unit/test_shards.py` (the kind); `tests/upstream/packages.toml`; `tests/harness/paths.py`; `tests/unit/test_artifact_rules.py`'s synthetic set.
- Documents: `docs/reference/packages.md`, `docs/reference/limitations.md`.

## Scope

In: Decisions 1 to 7. Out: rasterizing (174); `drawsvg.color` and pwkit; ipywidgets; Google fonts.

## Acceptance criteria

1. The wheel's SHA-256 matches PyPI's, and the `none` reason is read at the pinned version (EXECUTED, in the landing notes).
2. `test_vector_drawings_job_matches_native` passes, its golden from the oracle (`tests/jobs/regen.py --check`); it is seen failing first on a set without drawsvg.
3. `test_drawsvg_names_what_the_set_lacks` is seen failing first and passes on both binaries.
4. The unit rows of Decision 4 pass, each of the six refusals seen once; `test_every_package_names_its_own_suite` (`tests/checks/test_rules.py:1253`) passes with drawsvg's `none` entry.
5. The artifact-set checks pass with `LICENSES/drawsvg.txt`, the `drawsvg 2.4.2` package line and its `x-snapshot-package` line.
6. The bytes and fuel of Decision 7 are recorded, the wheel under the PyPI limit then in force, each growth claimed (EXECUTED).
7. The fast tier, `tests/lint` and the pull request's `ci-status` are green.

## Landing notes

Built 2026-10-31 on `spec/173-drawsvg-draws-svg-and-html` from `dev` `863c2929`, by a builder sub-agent of the orchestrating session, and rebased onto `dev` `2ec3c1ee`, the branch's base. `9d311a0a..2ec3c1ee` touches only `context/`, so the measurements below, taken at `9d311a0a`, stand. The pull request's run id is added at the merge.

- **The pin (criterion 1, EXECUTED).** `drawsvg-2.4.2-py3-none-any.whl`, 44,175 bytes, SHA-256 `b1c101e1…781bf1`, equal to PyPI's JSON for 2.4.2, still the newest release on 2026-10-31. The `none` reason was read at the pinned version: the sdist `drawsvg-2.4.2.tar.gz` (`5efd8bcd…dd303`) lists no test file, and the repository's tree at the tag `2.4.2` (GitHub's tree API, once: tree `f2f70ae4`, 115 entries, not truncated) holds only the package, its docs, examples, `setup.py` and `mkdocs.yml`. The reason names both and master, which the memo read.
- **What was built.** Decisions 1 to 6 as written. `drawsvg/widgets/` is packed. The wheel's `licenses/LICENSE.txt` reaches `LICENSES/drawsvg.txt` through `wheel_licences`; `MANIFEST` carries `drawsvg 2.4.2` and its `x-snapshot-package` line. drawsvg comes from a `--wheel` line, which owns its names under 171's rule, so its `top_level.txt` is written with no claim. The golden's PNG is `fixtures/swatch.png` (100 bytes, 4×4 RGBA), staged into every job's data folder beside `sales.csv`; no job lists that folder but `sqlite`, which filters by name. `docs/contributing/adding-a-package.md` names the new kind.
- **Seen failing first (EXECUTED).** `test_drawsvg_names_what_the_set_lacks` (both binaries) and `test_vector_drawings_job_matches_native` on dev's set from 167's worktree: `ModuleNotFoundError: No module named 'drawsvg'`. Each of the six refusals of Decision 4 by removing its guard from `package_errors` alone: its row failed, and only its row (reason; empty `checked_by`; a job not in `JOBS`; a job that does not import the package, and the `ast` row; the suite file, through `suites` and the file; a `via` naming a `none` entry). The fixture's rows first failed for the right reason too, before `vector_drawings` joined `JOBS`.
- **Measured (criterion 6, EXECUTED, darwin arm64)**, after the rebase onto `dev` `9d311a0a` (171 landed first): dev's set and this one from the same build tree, steps 70 to 90 run with each recipe. dev's came out byte for byte as 171 recorded it (`40663653…`, `ee76ead5…`); this set's two builds were equal file for file. Zip 57,068,536 → 57,159,131 bytes (+90,595, +0.16 %), 6,721 → 6,743 members (20 modules, a METADATA and, through 171's rule, the wheel's `top_level.txt`, `drawsvg`). Snapshot 104,890,482 → 104,909,776 (+19,294). `python.wasm` unchanged, 99,497,353. A plain start 283.76 M → 284.18 M fuel (+0.15 %, about 19 k a member, below the 26 k Decision 7 assumed); a snapshot start 54,767,956 → 54,881,031 (+0.21 %). `import drawsvg`: 897.3 M on the plain binary (614 M over an empty start, against the spike's 739 M from source) and 525.3 M from the snapshot. The wheel, built as the release workflow builds it: 101,659,542 → 101,758,925 bytes (+99,383), 3,098,675 under PyPI's 104,857,600; `release/licences.py check` passes on it. Before the rebase, against `863c2929`: zip +90,435, wheel 101,744,109.
- **Local runs at the head.** ruff clean; the fast tier after the rebase 4,506 passed, 0 failed (its RED line one pass blocked locally by the missing wheel and prior-art clones); `tests/unit` 3,468 passed before the rebase, and the unit suite 3,591 in the fast tier after it; `tests/lint` 14 passed; the two new checks, `test_packages_carry_their_metadata`, `test_v1_1_artifact_set.py` and `test_every_package_names_its_own_suite` pass on the built set. `tests/jobs/regen.py --check` reproduces `vector_drawings` from the oracle (criterion 2); it fails on `pdf` alone, as on `dev` since 167: the oracle's pdfminer.six brings `cryptography`, so native pypdf decrypts AES where that golden expects `DependencyError`. Not this change's; named for the orchestrator.
