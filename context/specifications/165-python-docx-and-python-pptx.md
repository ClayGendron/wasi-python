# 165: python-docx and python-pptx

- **Status:** drafted 2026-10-30, to be reviewed before it is built (the artifact set and the build recipe: two packages and two carried patches join the zip; constitution §5.6), as `../reviews/165-python-docx-and-python-pptx-spec-YYYY-MM-DD.md`. The owner chose it on 2026-10-30 (`../decisions.md`, "The scope of 0.1.3"). Both licences (MIT) are approved (constitution §4.12, question 43; decision 48).
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** **build-class** (constitution §5.6 and §5.7), **not structural**: nothing under `src/` changes. Two pins, two carried patches, step 70, `assemble_artifacts.py` and the snapshot package list; a judge change (the package lists, two upstream families, one golden job, one guest check); the release workflow's tree count; the packages page.
- **Depends on:** landed and unchanged: 020 (carried patches, the tree check), 023 (Pillow), 033 (`--metadata`), 035 (the zip's `Traversable`), 039 (xlsxwriter, typing-extensions, `build/pure-install/`), 041 (Decision 4: a pure package that needs a patch comes from its sdist), 046 (lxml), 063 and 067 (every package runs its own suite), 157 (`recipes/snapshot-packages.txt`). Siblings 166 (the pins) and 167 (pdfplumber, plotly, xarray, libzstd) edit the same files; whichever lands second rebases and recounts. If 159 lands first, the new release shard carries its `minutes` key.
- **Research it stands on:** `../research/2026-10-30-what-0-1-3-could-carry.md`, item B. `046-lxml.md`, Decision 12 (the deferral, EXECUTED there: python-docx 1.2.0 reads and writes in the guest, and `Document()` raises `PackageNotFoundError`). `041-files-read-by-path-from-the-zip.md`, Decisions 1 and 4. **The drafting runs** (EXECUTED 2026-10-30 in the session's scratch folder): PyPI's JSON for both; both wheels and sdists downloaded and their SHA-256 checked against PyPI's; sdist and wheel packages compared by `diff -r`; every `__file__` path and `open(` in both packages and their tests read; the size estimated with the host's Python 3.10.

Labels: EXECUTED means run and seen; READ means read from a file, cited; INFERRED means reasoned.

## The problem

Agents write Word and PowerPoint files, and both commercial code interpreters ship python-docx and python-pptx (the memo, §1, READ). The guest has neither. Spec 046 deferred them to a follow-up that was never numbered.

Adding them to the zip is not enough. Each opens its templates by a path made from `__file__`, which inside the zip names no file. So `docx.Document()` raises `PackageNotFoundError` in the guest (046, Decision 12, EXECUTED), and `pptx.Presentation()` opens its template the same way (READ).

The sites, read in the 1.2.0 and 1.0.2 releases (READ):

- python-docx, six: `docx/api.py:34-37` (`_default_docx_path`, `default.docx`); `parts/settings.py:45-50`, `parts/styles.py:37-42`, `parts/comments.py:46-51`, and `parts/hdrftr.py:28-33` and `:48-53` (the footer and header). Each part reads its XML template when a document lacks that part. The memo's five missed the comments part, new in 1.2.0.
- python-pptx, three: `pptx/api.py:40-43` (`_default_pptx_path`, `default.pptx`); `oxml/__init__.py:25-31` (`parse_from_template`, used for the theme, the notes master and a notes slide); `shapes/shapetree.py:1121-1140` (`_icon_image_file`, an OLE object's default icon).

## Decisions

### 1. The pins: python-docx 1.2.0 and python-pptx 1.0.2, from their sdists

Both are the latest releases on PyPI on 2026-10-30 (EXECUTED). The pins:

| file | SHA-256 |
|---|---|
| `python_docx-1.2.0.tar.gz` | `7bc9d7b7d8a69c9c02ca09216118c86552704edc23bac179283f2e38f86220ce` |
| `python_pptx-1.0.2.tar.gz` | `479a8af0eaf0f0d76b6f00b0887732874ad2e3188230315290cd1f9dd9cc7095` |

Each comes from its sdist, because a carried patch needs a tree (041, Decision 4). The sdists' packages equal the wheels' file for file (EXECUTED). Each sdist holds the project's `tests/`, so one pin serves the zip and the suite. The builder reads PyPI once at build; if a newer release exists, it pins that and re-makes the patches.

### 2. The fix is a carried patch per package, not a recipe

§4.1 prefers a recipe file. None fits, for 041's reasons (Decision 1 there):

- **A stand-in module.** The nine sites are private methods in six upstream modules; a stand-in would copy whole modules. That is wider than the patch.
- **The runner extracts the templates, as it does matplotlib's data.** That needs a change under `src/` and a grant on every call.
- **`importlib.resources.as_file`.** It copies to a temporary file, and by default nothing is writable (§4.15).

So each package carries one patch: `recipes/patches/python_docx-1.2.0/0001-templates-read-as-package-resources.patch` and `recipes/patches/python_pptx-1.0.2/0001-templates-read-as-package-resources.patch`. Each is recorded in `MANIFEST`, named in the CHANGELOG line, and deleted when upstream releases the fix.

### 3. What each patch changes

Every site reads its template as a package resource, `importlib.resources.files("docx").joinpath("templates", name).read_bytes()` (or `"pptx"`), which works from a folder, a zip and 035's `ZipDirectoryPath` (READ, `recipes/zip_resources.py:152`, `:196`).

- The XML sites return the same bytes as before.
- `_default_docx_path()` becomes `_default_docx()`, and `_default_pptx_path()` becomes `_default_pptx()`. Each returns an `io.BytesIO` of the template, which `Package.open` accepts (READ, `docx/opc/package.py:124`, `pptx/opc/package.py:80`).
- `_icon_image_file` returns an `io.BytesIO` for a default icon. A user's `icon_file` passes through unchanged. The OLE element uses only the icon's relationship id, so nothing saved changes (READ, `shapetree.py:1142-1145`).

One code path serves every install, so each project's own suite tests it natively. Four upstream test files name the old helpers or open a template by path, and the patches update them: python-docx's `tests/test_api.py`; python-pptx's `tests/test_api.py`, `tests/test_package.py` and `tests/shapes/test_shapetree.py` (READ).

### 4. The upstream drafts

Each patch has its draft at `context/upstream/patches/<top>/0001-templates-read-as-package-resources.md`, with the six header lines `recipes/patches/README.md` names, for `github.com/python-openxml/python-docx` and `python-pptx`. It gives the defect, the reproduction from a zip, the patch, the evidence, and the project's contribution rules as its repository states them at build (the sdists carry none, READ). The owner sends it, or not.

### 5. Every dependency is already carried

| requirement (READ, `METADATA`) | carried | by |
|---|---|---|
| lxml ≥ 3.1.0 | 6.1.3, compiled in | 046 |
| typing-extensions ≥ 4.9.0 | 4.16.0 | 039 |
| Pillow ≥ 3.3.2 (pptx; imported by `import pptx`) | 13.0.0, zlib only | 023 |
| XlsxWriter ≥ 0.5.7 (pptx charts) | 3.2.9 | 039 |

No other pin is added.

### 6. What goes into the zip

Step 70 unpacks each sdist beside seaborn's, calls `patch_tree`, and copies `src/docx` and `src/pptx` into `build/pure-install/` (`scripts/steps/70_zip.sh:80-90`); `--metadata` takes each `PKG-INFO` (`:146-161`).

`--drop docx/templates/default-docx-template` leaves out 17 files: the unpacked source of `default.docx`, which no module names (READ).

`LICENSES/python-docx.txt` and `LICENSES/python-pptx.txt` are each sdist's `LICENSE` (MIT, Steve Canny). `recipes/snapshot-packages.txt` gains `python-docx: docx` and `python-pptx: pptx`.

### 7. Their own tests run in the release

Each package gets `tests/upstream/<name>.toml` and `.ini`, with seaborn's settings (`driver = "package"`, `test_source = true`, `stage_folders = ["tests"]`, `cwd = "tree"`). Each `.ini` carries the project's collection rules from its `pyproject.toml` (`Describe` classes, `it_`-style functions, `filterwarnings = error`; READ).

- **The smoke groups.** `python-docx-smoke` (`tests/test_api.py`, `tests/test_document.py`) and `python-pptx-smoke` (`tests/test_api.py`, `tests/test_presentation.py`) run in the normal tier, in `upstream-pure-smoke-b` (128.5 G today, `tests/release_shards.toml:843-845`).
- **The release groups.** `python-docx-r` and `python-pptx-r` each run `tests` whole, in one new release shard after `upstream-pure-r-113`, or split by measured fuel as the file's rule says.
- `tests/upstream/packages.toml` names both `kind = "suite"`. The `features/` acceptance tests need behave, which the kit lacks; each `.toml` says so.
- An item that fails in the guest is named in `tests/upstream/expected/` with its reason. The target is none.

### 8. The golden job and the template check

**`tests/jobs/documents.py`**, compared with native Python by `test_documents_job_matches_native`. It runs:

- python-docx: `Document()`; a heading, runs in bold and italic, a 3×3 table, a picture from a PNG Pillow writes in memory, a section's own header and footer (two template sites), and a comment (a third).
- python-pptx: `Presentation()`; a title slide, a bullet slide, a table, a column chart from `CategoryChartData` (xlsxwriter writes its workbook), a picture, and a notes slide (the three XML templates).
- It saves each file to `/out`, reopens it, and prints what it reads back, never the archive's bytes: member times and some core-property dates come from the clock (READ, `docx/opc/phys_pkg.py:119`, `pptx/opc/serialized.py:236`).

The oracle (`tests/jobs/oracle/pyproject.toml`) pins `python-docx==1.2.0` and `python-pptx==1.0.2`, stock. Equal output shows the patches change no result on these calls.

**`test_office_templates_read_from_the_zip`** runs on `[plain, snapshot]` with nothing granted. The guest calls each of the nine sites, prints the SHA-256 of what each returns, and builds a document and a presentation into `BytesIO`. The judge compares each hash with that template's member in the artifact's `python-stdlib.zip`; the tree check ties those members to the pinned sdists. It asserts that `docx.__file__` and `pptx.__file__` lie inside the zip.

### 9. Size and fuel, measured at the build

Estimated with Python 3.10 bytecode (INFERRED): 212 members and 0.90 MB deflated (docx 102 and 0.30 MB; pptx 110 and 0.60 MB), about 1.7% of the 53,915,154-byte, 6,262-member zip of the 2026-10-21 main-tree build (EXECUTED).

The build measures the zip's bytes and members, `python-snapshot.wasm`'s bytes (the zip's directory is in the image) and a plain start's fuel, records them, and claims each growth in the news file.

### 10. The documents

`docs/reference/packages.md`'s pure-Python table gains a "documents" family: python-docx 1.2.0, "read and write Word `.docx`"; python-pptx 1.0.2, "read and write PowerPoint `.pptx`, charts included". Its counts at lines 35 and 90 change, and one sentence says `fit_text()` needs Pillow's FreeType module, which the set lacks. `README.md`'s count of carried patches rises by two.

## Intent

A program in the guest starts a Word document or a slide deck from the defaults, fills it, saves it to a granted folder or to memory, and reads it back, as native Python does. Each package's own suite runs in the release.

## Design

Recipe: `downloads/SHA256SUMS` and `scripts/00_download.sh` (Decision 1); the two patches and their drafts (2 to 4); `scripts/steps/70_zip.sh` (6); `scripts/assemble_artifacts.py` (`PACKAGES` at line 27, the two notices); `recipes/snapshot-packages.txt`.

Judge: `tests/harness/pins.py` (`SOURCE_PATTERNS`), `needs.py` (`SOURCE_COMPONENTS`, line 149), `paths.py` (`LICENCE_COMPONENTS`, `PACKAGES`) and `upstream.py` (`PURE_SUITES`, line 52) name both; the four upstream files, `packages.toml` and `tests/release_shards.toml` (7); `tests/jobs/documents.py`, its `.expected`, the oracle's `pyproject.toml` and `uv.lock`, and the two checks in `tests/checks/test_v1_3_default_profile.py` (8).

Also: `.github/workflows/release.yml:338-344` and `:440` (the tree count, two more); `docs/reference/packages.md` and `README.md` (10); the news file `context/changes/165-python-docx-and-python-pptx.md`.

## Scope

**In:** the ten decisions.

**Out:**

- `fit_text()` (no FreeType in Pillow).
- JPEG pictures in python-pptx: Pillow has no JPEG decoder; the builder records what `add_picture` does with one.
- The projects' behave acceptance tests.
- Sending anything upstream; that is the owner's (§7).

## Acceptance criteria

1. `test_office_templates_read_from_the_zip` is seen failing first on a set built with the stock sdists: `Document()` and `Presentation()` raise `PackageNotFoundError`. It passes on the patched set, plain and snapshot (EXECUTED, in the landing notes).
2. `test_documents_job_matches_native` passes; the job's native output is regenerated from the oracle.
3. `test_source_tree_matches_its_tarball` passes for both trees, and `test_carried_patches_follow_the_rules` with both drafts.
4. On the host, the patched sdists' own suites pass the same tests as the stock ones (EXECUTED, both counts in the landing notes).
5. The four groups run, smoke in the normal tier and whole suites in the release tier; `test_every_package_names_its_own_suite` passes; any expected item names its reason.
6. Each staged package equals its wheel's members but the dropped folder and the patched files (EXECUTED, 041's `walk` against `wheel_members`).
7. The artifact-set checks pass with both `LICENSES` files, both `package` lines in `MANIFEST` and both `x-snapshot-package` lines.
8. The zip's bytes and members, the snapshot's bytes and a plain start's fuel are recorded, and each growth is claimed (EXECUTED).
9. The fast tier, `tests/lint` and the pull request's `ci-status` are green.

## Landing notes

To be written at the landing.
