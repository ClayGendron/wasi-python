# 165: python-docx and python-pptx

- **Status:** drafted 2026-10-30 and reviewed before it is built (the artifact set and the build recipe; constitution §5.6): `../reviews/165-python-docx-and-python-pptx-spec-2026-10-30.md`, "Fit to build after amendments", its Medium and five Lows taken the same day (its Disposition says where). The owner chose it on 2026-10-30 (`../decisions.md`, "The scope of 0.1.3"). Both licences (MIT) are approved (constitution §4.12, question 43; decision 48).
- **Date:** 2026-10-30
- **Owner:** Clay Gendron
- **Kind:** **build-class** (constitution §5.6 and §5.7), **not structural**: nothing under `src/` changes. Two pins, two carried patches, step 70, `assemble_artifacts.py` and the snapshot package list; a judge change (the package lists, two upstream families, one golden job, one guest check); the release workflow's tree count; the packages page.
- **Depends on:** landed: 020, 023 (Pillow), 033, 035, 039 (xlsxwriter, typing-extensions), 041 (Decision 4: a patched pure package comes from its sdist), 046 (lxml), 063 and 067 (own suites), 157. 166 (the pins): 165 is built after 166's first pull request lands, and merges only once the first weekly run after 166's last merge has its x86-64 `same-bytes` green, or the owner, asked, dispatches one (166, Decision 12). 167 edits the same files; whichever lands second rebases and recounts. If 159 lands first, the new release shard carries its `minutes` key.
- **Research it stands on:** `../research/2026-10-30-what-0-1-3-could-carry.md`, item B. `046-lxml.md`, Decision 12 (the deferral, EXECUTED there: python-docx 1.2.0 reads and writes in the guest, and `Document()` raises `PackageNotFoundError`). `041-files-read-by-path-from-the-zip.md`, Decisions 1 and 4. **The drafting runs** (EXECUTED 2026-10-30, scratch folder): both wheels and sdists downloaded and checked against PyPI's SHA-256; their packages compared by `diff -r`; every `__file__` path and `open(` in both packages and their tests read; the size estimated with Python 3.10.

Labels: EXECUTED means run and seen; READ means read from a file, cited; INFERRED means reasoned.

## The problem

Agents write Word and PowerPoint files; both commercial code interpreters ship these packages (the memo, §1, READ). The guest has neither: spec 046 deferred them.

Adding them is not enough. Each opens its templates by a path made from `__file__`, which inside the zip names no file, so `docx.Document()` raises `PackageNotFoundError` in the guest (046, Decision 12, EXECUTED); `pptx.Presentation()` does the same (READ).

The sites, read in the 1.2.0 and 1.0.2 releases (READ):

- python-docx, six: `docx/api.py:34-37` (`_default_docx_path`, `default.docx`); `parts/settings.py:45-50`, `parts/styles.py:37-42`, `parts/comments.py:46-51`, and `parts/hdrftr.py:28-33` and `:48-53` (the footer and header). Each part reads its template when a document lacks it. The memo's five missed comments, new in 1.2.0.
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

- **A stand-in module.** The nine sites are private methods in six modules; a stand-in would copy whole modules.
- **The runner extracts the templates, as it does matplotlib's data.** That needs a change under `src/` and a grant on every call.
- **`importlib.resources.as_file`.** It needs a writable temporary folder (§4.15).

So each package carries one patch, `recipes/patches/<top>/0001-templates-read-as-package-resources.patch` (`<top>` is `python_docx-1.2.0` or `python_pptx-1.0.2`). Each is recorded in `MANIFEST`, named in the CHANGELOG line, and deleted when upstream releases the fix.

### 3. What each patch changes

Every site reads its template with `pkgutil.get_data("docx", "templates/" + name)` (or `"pptx"`). It reads through the loader's `get_data`, from a folder or a zip, on every Python both projects support (python-pptx's 3.8 lacks `importlib.resources.files`), as plotly does in the guest (167).

- The XML sites return the same bytes as before.
- `_default_docx_path()` and `_default_pptx_path()` keep their names, so the diff stays small, and return an `io.BytesIO` of the template, which `Package.open` accepts (READ, `docx/opc/package.py:124`, `pptx/opc/package.py:80`). The draft offers upstream a rename.
- `_icon_image_file` returns an `io.BytesIO` for a default icon. A user's `icon_file` passes through unchanged. The OLE element uses only the icon's relationship id, so nothing saved changes (READ, `shapetree.py:1142-1145`).

One code path serves every install, so each project's own suite tests it natively. Three python-pptx test files assert a path or open a template by one, and its patch updates them: `tests/test_api.py`, `tests/test_package.py` and `tests/shapes/test_shapetree.py` (READ). python-docx's `tests/test_api.py` mocks `_default_docx_path` and passes unchanged.

### 4. The upstream drafts

Each patch has its draft at `context/upstream/patches/<top>/0001-templates-read-as-package-resources.md`, with the six header lines `recipes/patches/README.md` names, for `github.com/python-openxml/python-docx` and `python-pptx`. It gives the defect, the reproduction from a zip, the patch, the evidence, and the project's contribution rules as its repository states them at build (the sdists carry none, READ). It links any open issue or pull request on the same defect, and names the Python versions the patch was tested on. Where a project asks that AI-written pull requests not be sent, the draft is a facts sheet, as networkx's is (question 80). The owner sends it, or not.

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
- **The release groups.** `python-docx-r` and `python-pptx-r` run `tests` whole, in one new shard after `upstream-pure-r-113`, split by fuel if the file's rule asks.
- `tests/upstream/packages.toml` names both `kind = "suite"`. The `features/` acceptance tests need behave, which the kit lacks; each `.toml` says so.
- An item that fails in the guest is named in `tests/upstream/expected/` with its reason. The target is none.

### 8. The golden job and the template check

**`tests/jobs/documents.py`**, compared with native Python by `test_documents_job_matches_native`. It runs:

- python-docx: `Document()`; a heading, runs in bold and italic, a 3×3 table, a picture from a PNG Pillow writes in memory, a section's own header and footer (two template sites), and a comment (a third).
- python-pptx: `Presentation()`; a title slide, a bullet slide, a table, a column chart from `CategoryChartData` (xlsxwriter writes its workbook), a picture, and a notes slide (the three XML templates).
- It saves each file to `/out`, reopens it, and prints what it reads back, never the archive's bytes: member times, some core-property dates and the comment's `date` come from the clock (READ, `docx/opc/phys_pkg.py:119`, `pptx/opc/serialized.py:236`).

The oracle pins both, stock; equal output shows the patches change no result on these calls.

**`test_office_templates_read_from_the_zip`** runs on `[plain, snapshot]` with nothing granted. The guest calls each of the nine sites and prints a SHA-256 per site: of the bytes returned; for `parse_from_template`, of `etree.tostring` of its result and of the zip member parsed by `parse_xml`, which must be equal; for the icon, of the image part's blob. It also builds a document and a presentation into `BytesIO`. The judge compares each hash with that template's member in the artifact's `python-stdlib.zip`; the tree check ties those members to the pinned sdists. It asserts that `docx.__file__` and `pptx.__file__` lie inside the zip.

### 9. Size and fuel, measured at the build

Estimated with Python 3.10 bytecode (INFERRED; 3.15's is larger): 212 members and 0.90 MB deflated, about 1.7% of the 53,915,154-byte zip of the 2026-10-21 build (EXECUTED). The growth is estimated again before the pins land, with step 70's own functions and the line's Python, as 167 does.

**The wheel.** The 0.1.2 wheel is 98,385,354 bytes, 1.61 MB under decision 64's line (the review, EXECUTED), and the zip's growth passes into it whole. The build records the wheel's bytes from each pull request's build, against 100,000,000 (decision 64) and 104,857,600 (PyPI's default limit). If the wheel would pass 100,000,000, the builder asks the owner with AskUserQuestion before the merge.

The build measures the zip's bytes and members, `python-snapshot.wasm`'s bytes (the zip's directory is in the image) and a plain start's fuel, records them, and claims each growth in the news file.

### 10. The documents

`docs/reference/packages.md`'s pure-Python table gains a "documents" family: python-docx 1.2.0, "read and write Word `.docx`"; python-pptx 1.0.2, "read and write PowerPoint `.pptx`, charts included". Its counts at lines 35 and 90 change, and one sentence says `fit_text()` needs Pillow's FreeType module, which the set lacks. `README.md`'s count of carried patches rises by two.

## Intent

A program in the guest starts a Word document or a slide deck from the defaults, fills it, saves it to a granted folder or to memory, and reads it back, as native Python does. Each package's own suite runs in the release.

## Design

Recipe: `downloads/SHA256SUMS` and `scripts/00_download.sh` (Decision 1); the two patches and their drafts (2 to 4); `scripts/steps/70_zip.sh` (6); `scripts/assemble_artifacts.py` (`PACKAGES` at line 27, the two notices); `recipes/snapshot-packages.txt`.

Judge: `tests/harness/pins.py` (`SOURCE_PATTERNS`), `needs.py` (`SOURCE_COMPONENTS`, line 149), `paths.py` (`LICENCE_COMPONENTS`, `PACKAGES`) and `upstream.py` (`PURE_SUITES`, line 52) name both; the upstream files and shards (7); the job, its `.expected`, the oracle's pins and the two checks in `tests/checks/test_v1_3_default_profile.py` (8).

Also: the tree count in `.github/workflows/release.yml:338-344` and `:440`, two more; the documents (10); the news file.

## Scope

**In:** the ten decisions.

**Out:**

- `fit_text()` (no FreeType in Pillow).
- JPEG pictures in python-pptx (no JPEG decoder); the builder records what `add_picture` does.
- The projects' behave acceptance tests.
- Sending anything upstream; that is the owner's (§7).

## Acceptance criteria

1. `test_office_templates_read_from_the_zip` is seen failing first on a set built with the stock sdists: `Document()` and `Presentation()` raise `PackageNotFoundError`. It passes on the patched set, plain and snapshot (EXECUTED, in the landing notes).
2. `test_documents_job_matches_native` passes, its output regenerated from the oracle.
3. `test_source_tree_matches_its_tarball` passes for both trees, and `test_carried_patches_follow_the_rules` with both drafts.
4. On the host, the patched sdists' own suites pass the same tests as the stock ones (EXECUTED, both counts in the landing notes).
5. The four groups run, smoke in the normal tier and whole suites in the release tier; `test_every_package_names_its_own_suite` passes; any expected item names its reason.
6. Each staged package equals its wheel's members but the dropped folder and the patched files: done once by the builder, each wheel's SHA-256 checked against PyPI's, the output in the landing notes; the wheels are not pins (EXECUTED).
7. The artifact-set checks pass with both `LICENSES` files, both `package` lines in `MANIFEST` and both `x-snapshot-package` lines.
8. The zip's bytes and members, the snapshot's bytes, the wheel's bytes against both lines, and a plain start's fuel are recorded, and each growth is claimed (EXECUTED).
9. The fast tier, `tests/lint` and the pull request's `ci-status` are green.

## Landing notes

Built 2026-10-31 by an agent (Claude Opus 5.5), a builder sub-agent of the orchestrating session, on `spec/165-python-docx-and-python-pptx`, stacked on 166's first pull request (#67, `a7f5cee5`): the set was rebuilt with `scripts/build.sh --from 70` over a copy-on-write clone of 166's build tree, its paths rewritten, which first rebuilt 166's set byte for byte (`build/165/build-baseline.log`). Everything below is EXECUTED on an arm64 Mac (Darwin 25.5.0). It merges after #67 and after a weekly run's x86-64 `same-bytes` is green (Depends).

**Pins** (Decision 1): PyPI read once; 1.2.0 and 1.0.2 are the newest, and both sdists' SHA-256s are PyPI's. **Criterion 6**: each wheel, fetched once (`3fd478f3…`, `160838e0…`, PyPI's), equals the staged package file for file, 119 and 110 files, but the patched ones (five and three); the zip then leaves out `default-docx-template`'s 17 files.

**Seen failing first** (criterion 1): on a set built from the stock sdists, `test_office_templates_read_from_the_zip` fails on both binaries (each site `NotADirectoryError`, the icons `PackageNotFoundError`), and `Document()` and `Presentation()` raise `PackageNotFoundError` there. On the patched set it passes, plain and snapshot, and `test_documents_job_matches_native` passes (criterion 2); `new_upstream_families`' unit row failed before its function.

**The projects' own suites, natively** (criterion 4), stock and patched, on CPython 3.15.2 and 3.11.14: python-docx 1,609 passed, python-pptx 2,700 passed, each the same four times (pyparsing 3.3's deprecations ignored, as the `.ini` does). From each released wheel on `PYTHONPATH`, `Document()` and `Presentation()` raise `PackageNotFoundError`; from a zip of the patched trees they work. The drafts (Decision 4): neither repository states a contribution rule, so both are pull request text; no open report on the defect (python-docx #176 and PR #735 closed; python-pptx #804 is a user's template).

**In the guest** (criterion 5): python-docx-smoke 35 passes, 18.6 G; python-pptx-smoke 20 passes, 13.4 G; python-docx-r 1,571 passes and 3 expected, 105.8 G; python-pptx-r 2,677 passes and 3 expected, 150.0 G. The six expected tests patch `io.BytesIO` for the whole interpreter, which pytest's sys capture (the guest cannot `dup`) asserts against; native pytest with `--capture=sys` fails the same six. A JPEG picture works in both packages (python-pptx reads its 204×204 size from the header; nothing decodes it). `fit_text()` raises `OSError` (no system fonts), or `ImportError` (`_imagingft`) given `font_file=`.

**Size and fuel** (criterion 8), against 166's set: the zip 53,829,197 → 54,960,042 bytes (+1,130,845, +2.10%), 6,262 → 6,476 members; `python-snapshot.wasm` 104,576,267 → 104,660,362 (+84,095); `python.wasm` unchanged; a plain start 272,159,309 → 277,407,635 fuel (+1.93%), a snapshot start +1.01%. **The wheel**, built by hand from each set: 98,327,640 → 99,460,553 bytes (+1,132,913), 539,447 under 100,000,000 and 5,397,047 under 104,857,600. It does not cross decision 64's line, but 166's second pull request (pandas 3.1.0) leaves about 0.5 MB.

**Two findings for 166, not changed here.** `test_upstream_files_are_well_formed` fails here, and on #67's head too: soupsieve-smoke measures 164.8 G, past the 100 G a smoke group may measure (the finding reads only `soupsieve.toml`, which this branch does not change). With this specification's two smoke groups (32.0 G) the test-source smoke groups sum to 1,027.0 G, past the 1 T bound (995.0 G on #67's head). The follow-up 166's review asks for (soupsieve's two heavy tests to the release tier) clears both.

**Local runs at the head**: `ruff` clean; the fast tier's unit, lint and rules rows green but the prior-art row (blocked); `tests/lint` green; `--shard=build` green. Pull request: a draft, stacked on #67.
