# Review of 165 — python-docx and python-pptx

- **Date:** 2026-10-30
- **Reviewer:** an agent (Claude Opus), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** the specification as drafted, `context/specifications/165-python-docx-and-python-pptx.md`, on `docs/0.1.3-specifications` at `4849fc4e`
- **Run:** none: a specification review
- **Re-ran:** no test run. Read the cached wheels of python-docx 1.2.0 and python-pptx 1.0.2 in uv's cache (the sdists are not on this machine); `unzip -v` of `build/0.1.2/release-assets/wasi_python-0.1.2-py3-none-any.whl` in the main tree.
- **Time box:** 45 minutes (a package); kept.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning. No `gh` call was made and no run was dispatched.

EXECUTED: the 0.1.2 wheel is 98,385,354 bytes; its `python-stdlib.zip` is 53,915,154 bytes stored as 53,139,109 (1% smaller), so the zip's growth passes into the wheel almost whole.

READ: every site in "The problem" in the cached wheels, at the lines given (`docx/api.py:34-37`, `parts/settings.py:45-50`, `styles.py`, `comments.py`, `hdrftr.py:28-33` and `:48-53`; `pptx/api.py:40-43`, `oxml/__init__.py:25-31`, `shapes/shapetree.py:1121-1140`); `Package.open` at `docx/opc/package.py:124` and `pptx/opc/package.py:80`; `docx/templates/default-docx-template` holds 17 files; both licences MIT and named in constitution §4.12; `Requires-Python` is `>=3.9` (docx) and `>=3.8` (pptx). In the tree: `scripts/steps/70_zip.sh:80-90`, `:146-161`; `scripts/assemble_artifacts.py:27`; `recipes/zip_resources.py:151-155`, `:196-198`; `tests/harness/needs.py:149`, `upstream.py:52`, `pins.py:26`, `paths.py:102`, `:185`; `tests/release_shards.toml:843-845`; `.github/workflows/release.yml:344` and `:446` (the "28 passed" counts); `tests/upstream/packages.toml`; `recipes/patches/README.md:13-14`; decision 64 (`context/decisions.md:245`).

## Acceptance criteria against evidence

1. The template check seen failing on stock sdists — testable; what it hashes needs a word (Finding 3).
2. The documents job against native — sound; one more clock field (Finding 4).
3. The tree check and the patch rules — sound; Design names every list a tree joins (pins, needs, paths, upstream, the count in `release.yml`).
4. Patched suites equal stock suites on the host — sound.
5. Four groups, the suite rule — sound; `upstream-pure-smoke-b` has room (128.5 G of 725 G).
6. Staged package equals its wheel — sound as a one-off; the wheels are not pins (Finding 5).
7. The artifact-set checks — sound.
8. Bytes and fuel recorded and claimed — not met as written: the wheel is not among them (Finding 1).
9. Fast tier, lint, `ci-status` — sound.

## Findings, most severe first

1. **Medium: the wheel is neither measured nor held to decision 64's line** (Decision 9; criterion 8). Decision 64 says each landing records the wheel's size and the agent brings the question back when a landing would cross 100 MB. 165 records the zip, the snapshot and fuel, never the wheel. The 0.1.2 wheel is 1.61 MB under 100,000,000 bytes (EXECUTED). 165 adds about 0.9 MB, estimated with Python 3.10 bytecode, which is smaller than 3.15's (INFERRED). 166 may add up to its bounds (+1% an artifact on its first pull request, +3% on `python.wasm` and the zip on its second). Failure: 165 lands after 166, the wheel is about 100.3 MB, nobody asks the owner, and the release pull request is the first to see it. Fix text, Decision 9: "The build also records the wheel's bytes from the pull request's build, against 100,000,000 (decision 64) and against 104,857,600, PyPI's default file limit of 100 MiB (question 64). The growth is estimated again before the pins land, with step 70's own functions and the line's Python, as 167 does. If the wheel would pass 100,000,000, the builder asks the owner with AskUserQuestion before the merge." Criterion 8 adds "the wheel's bytes".
2. **Low: the patch's API drops Pythons both projects support, which keeps it from being temporary** (Decision 3). `importlib.resources.files` is 3.9 and later; python-pptx supports 3.8 (READ). A multi-argument `joinpath` on a zip's `Traversable` came after 3.9 (INFERRED). An upstream that cannot take the change keeps the patch carried forever. Fix text: "Each site reads `pkgutil.get_data("docx", "templates/" + name)` (or `"pptx"`), which reads from a folder or a zip on every Python the projects support, as plotly already does in the guest; the old helper names stay as thin wrappers, so the upstream diff stays small. The draft names the Python versions it was tested on."
3. **Low: "the SHA-256 of what each returns" does not fit two sites** (Decision 8). `parse_from_template` returns an lxml element. `_icon_image_file` is a lazy property of `_OleObjectElementCreator` (READ). Fix text: "For `parse_from_template` the guest prints the hash of `etree.tostring` of its result and of the zip member parsed by `parse_xml`, which must be equal. For the icon it prints the hash of the image part's blob."
4. **Low: the comment's date comes from the clock too** (`docx/comments.py:60`, READ). Fix text, Decision 8: "…and the comment's `date`" after "some core-property dates".
5. **Low: criterion 6 needs the wheels, which are not pinned.** 041 compared networkx's tree with its wheel once, by hand, with the output in the specification. Fix text, criterion 6: "Done once by the builder, with each wheel's SHA-256 checked against PyPI's, and the output in the landing notes; the wheels are not pins."
6. **Low: the drafts should look for upstream reports first** (Decision 4). The `default.docx` "file not found" error under zip imports and freezers is a common report (INFERRED). Fix text: "The draft links any open issue or pull request on the same defect. Where the project's rules ask that AI-written pull requests not be sent, the draft is a facts sheet, as networkx's is (question 80)."

## Constitution checks

- §4.1: a patch is justified. A stand-in copies whole modules. The runner route needs `src/` and a grant. `as_file` needs something writable. A fourth route, an import hook in the zip that rebinds the helpers, would be a runtime patch the tree check cannot see, which is worse. The drafts are planned (Decision 4), and Finding 2 keeps them acceptable to upstream.
- §4.2: two sdists hashed. The spec's SHA-256s were not re-checked here, because the sdists are not on this machine.
- §4.12: MIT, approved by name (READ §4.12). Every dependency is carried and approved. The templates and EMF icons are the projects' own files; no other notice is in either wheel (READ).
- §4.15: nothing writable, no temporary file. Holds.
- §4.6 and spec 063: two `LICENSES` files and two `package` lines; smoke and whole-suite groups. Holds.
- Structure: nothing under `src/` changes, so not structural. Agreed.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **Medium, taken.** Decision 9 gains "The wheel": the 0.1.2 wheel's 98,385,354 bytes, the wheel's bytes recorded from each pull request's build against 100,000,000 (decision 64) and 104,857,600 (PyPI's default limit), the AskUserQuestion before a merge that would pass 100,000,000, and the growth estimated again before the pins land with step 70's own functions and the line's Python. Criterion 8 names the wheel's bytes against both lines. The Depends line now carries 166's ordering: built after 166's first pull request lands, merged only once the first weekly run after 166's last merge has its x86-64 `same-bytes` green, or the owner dispatches one. **Reviewer:** confirmed (READ, the amended Decision 9, criterion 8 and Depends line). The two lines, the question before the merge and the re-estimate with the line's Python close it.
2. **Low, taken.** Decision 3: every site reads `pkgutil.get_data("docx", "templates/" + name)` (or `"pptx"`), citing python-pptx's 3.8 and plotly's use in the guest. `_default_docx_path` and `_default_pptx_path` keep their names and return a stream, so python-docx's `tests/test_api.py` passes unchanged and only python-pptx's three test files change; the draft offers the rename. The draft names the Python versions tested (Decision 4). **Reviewer:** confirmed. `pkgutil.get_data` goes through `zipimporter.get_data`, and the guest's zip is on a `zipimporter` (READ, `recipes/zip_resources.py:3-5`). That python-docx's `tests/test_api.py` passes unchanged is INFERRED here (the sdist is not on this machine); criterion 4 would catch it if wrong.
3. **Low, taken.** Decision 8: one hash per site; for `parse_from_template`, `etree.tostring` of its result against the zip member parsed by `parse_xml`; for the icon, the image part's blob. **Reviewer:** confirmed (READ, Decision 8).
4. **Low, taken.** Decision 8 names the comment's `date` among the clock's fields. Confirmed.
5. **Low, taken.** Criterion 6: done once by the builder, each wheel's SHA-256 checked against PyPI's, the output in the landing notes; the wheels are not pins. **Reviewer:** confirmed (READ, criterion 6).
6. **Low, taken.** Decision 4: the draft links any open issue or pull request on the same defect, and is a facts sheet where the project asks that AI-written pull requests not be sent (question 80). **Reviewer:** confirmed (READ, Decision 4).

## Verdict

Fit to build: the Medium and the five Lows are answered in the amended specification, each confirmed above at the second reading of 2026-10-30.
