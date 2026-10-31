# Review of 165 — python-docx and python-pptx

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** `a7f5cee5..0bcdf7c9`, then the rebased head `30566232..5a18d752`: `git range-diff` shows the earlier commits unchanged but the ledger's context line (#67's), and `5a18d752` touches only `context/` (READ)
- **Run:** 41202001240 on `5a18d7528b3e`, as the orchestrator reported it (no `gh` call): every judge leg green (Linux, macOS, 12 Windows legs, verify), the gather green, the one refusal this file's absence. Every `GROWTH` row claimed. `test_markup_job_matches_native` grew 6.61 G → 10.00 G, and the builder measured it alone on each set: 165 adds +6.3 M (+0.06%), the rest is soupsieve 3.0.4 from `dev`. x86-64 vote: run 41201012715 on `dev` at `30566232`, same bytes from every host; its two red release shards are `dev`'s and touch no 165 group
- **Re-ran:** against the worktree's rebuilt set (`build/artifacts`, the zip `d3f084ad…`), on an arm64 Mac:
  - `test_office_templates_read_from_the_zip` (plain, snapshot), `test_documents_job_matches_native`, `test_source_tree_matches_its_tarball[python-docx]` and `[python-pptx]` → 5 passed, exit 0;
  - `test_upstream_suite[python-docx-smoke]` and `[python-pptx-smoke]` → 2 passed, exit 0;
  - `--shard=upstream-release-066` → 2 passed, 3 xfailed (the expected classes), 136 s;
  - `uv run pytest tests/lint` → 14 passed; `ruff check src tests scripts` and `ruff format --check src tests` clean;
  - the fast tier, `-n 2` → 4,299 passed, 2 failed, both #67's rows that `c2083f5c` fixes (`test_upstream_files_are_well_formed`, `test_deep_data_limits[hash-tuple]`)
- **Time box:** 45 minutes (a package); kept.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning.

## Acceptance criteria against evidence

1. Template check seen failing first on stock sdists — met: READ, `build/165/seen-failing-stock.log` (both binaries FAILED, every site `NotADirectoryError`) and `seen-failing-stock-probe.txt`; the check commit `73975698` precedes the pins commit `9bb4c488`. Passes on the patched set, plain and snapshot (EXECUTED).
2. Documents job against native — met (EXECUTED).
3. Tree check and patch rules — met for the tree check (EXECUTED, both nodes); the three tree counts in `release.yml` move 28 → 30, and `needs.SOURCE_COMPONENTS` has 30 entries (EXECUTED).
4. Patched suites equal stock natively — met as recorded: 1,609 and 2,700 passed on 3.15.2 and 3.11.14.
5. Four groups — met (EXECUTED, above). Six expected tests, each with its reason and a gap.
6. Staged package equals its wheel but the patched files — met (EXECUTED): both wheels hash to PyPI's (`3fd478f3…`, `160838e0…`); 119 and 110 files equal, differing only in the five and three patched modules; the zip holds 102 `docx/` members (17 left out) and 110 `pptx/`, none from `default-docx-template`.
7. Artifact-set lines — met (EXECUTED, `build/artifacts/MANIFEST`): two `package` lines, two `pin` lines, two `recipe` lines whose hashes equal the patch files', two `x-snapshot-package` lines.
8. Bytes, fuel, wheel — met: the hand-built wheel is 99,460,553 bytes (EXECUTED), its zip and snapshot the final set's; under the owner's interim line, 104,857,600. Every growth is claimed.
9. Fast tier, lint, `ci-status` — lint met (EXECUTED); fast tier red only in #67's two rows, which `c2083f5c` fixes (Re-ran); the pull request's run 41202001240 green in every judge leg (Run).

## Findings, most severe first

1. **Low: the landing notes' "Two findings for 166" and the wheel sentence go stale at the rebase** (`context/specifications/165-python-docx-and-python-pptx.md`, Landing notes). #67's `c2083f5c` moves soupsieve's `test_api.py` to the release group: soupsieve-smoke falls from 164.8 G to 15.1 G, and the test-source smoke groups with 165's two (32.0 G) sum to 877.2 G, under the 1 T of `SMOKE_TOTAL_BOUND` (`tests/harness/packages.py:1479`) by 122.8 G (EXECUTED: the sum over `tests/upstream/*.toml` with `c2083f5c`'s `soupsieve.toml`). The paragraph would then report two failures that no longer exist. Fix text, after the rebase and a re-run of `test_upstream_files_are_well_formed` by node id: replace the paragraph with "**The smoke bound.** Rebased onto #67's `c2083f5c`, which moves soupsieve's `test_api.py` to its release group, the test-source smoke groups measure 877.2 G with this specification's two (32.0 G), under the 1 T bound, and `test_upstream_files_are_well_formed` passes." In the wheel sentence, replace "It does not cross decision 64's line, but 166's second pull request (pandas 3.1.0) leaves about 0.5 MB." with "The owner's interim line of 2026-10-31 (PyPI's 104,857,600, recorded on #72) replaces decision 64's 100,000,000; the wheel is 5,397,047 under it."
2. **Low: the Status line still reads "drafted"** (the specification, line 3). Other built specifications say where they were built. Fix text: begin it "built 2026-10-31 on `spec/165-python-docx-and-python-pptx` (pull request #70), not landed. Drafted 2026-10-30 …", and keep the rest.
3. **Low: the python-pptx draft's "nothing saved changes" has one exception** (`context/upstream/patches/python_pptx-1.0.2/0001-templates-read-as-package-resources.md`, the `shapetree.py` bullet). The image part made for a default icon now has no file name. A later `add_picture` of the same EMF bytes reuses that part by SHA-1 (`pptx/parts/image.py`, `_find_by_sha1`), and the picture's `descr` becomes `image.wmf` where the stock code writes `xlsx-icon.emf` (INFERRED from `shapetree.py:485` and `ImagePart.desc`). No test or job covers it; it matters only to a maintainer weighing the patch. Fix text, after "so nothing saved changes": "One corner: a later `add_picture` of the very same icon bytes reuses that part, so the picture's `descr` reads `image.wmf` instead of the icon's file name."

No High or Medium. Read and found sound: the two patches touch exactly the nine sites (six docx, three pptx) and three pptx test files; no other `__file__` read remains in either package (EXECUTED, grep of `build/pure-install`); `os` has no other use in the edited modules (EXECUTED); `ImagePart`'s extension comes from Pillow's format, not the file name, so the icon's part name and content type are unchanged (READ, `pptx/parts/image.py:220-237`). Both pins equal PyPI's record, read once (EXECUTED). The two drafts carry the six header lines, the contribution rules read, the related reports and the Pythons tested. The CHANGELOG lines name both patch files. `packages.toml`, the docs row and the README's count (27 → 29) agree. The new release shard carries `minutes = 1.9`, estimated (spec 159); my local run of it took 136 s with collection. `new_upstream_families` lets a new suite's cap wait for its first acceptance, as a new check file's already does, and has its unit row; the judge's verdict-bearing files changed are each under `[claim.judge]`, and the release ledger's block names the two release groups and three classes.

`.github/workflows/release.yml` (4b): three steps change the expected count of `test_source_tree_matches_its_tarball` from 28 to 30 passed, in the source-build job and both rebuild jobs; nothing else in what runs, what is refused, or which job holds a token changes.

Structure: nothing under `src/` changes; not structural, as the Kind line says.

## Constitution checks

- §4.1: two carried patches, each a recorded `recipe` line in `MANIFEST`, named in the CHANGELOG, with its upstream draft. Temporary: `pkgutil.get_data` works on every Python both projects support.
- §4.2: both sdists pinned by URL and SHA-256 and verified (EXECUTED).
- §4.12: python-docx and python-pptx, MIT, approved by name; every dependency already carried.
- §4.15: nothing writable; the template check runs with nothing granted.
- §4.6 and spec 063: both `LICENSES` files and package lines; each package's own suite runs, smoke in the normal tier and whole in the release tier.
- §7 never-do list: nothing tripped. The judge is not weakened: the six expected tests fail natively under `--capture=sys` too, and each gap names its closer.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **Taken** (the review's Lows commit after the rebase onto `dev` at `30566232`): the paragraph is now "The smoke bound" (877.2 G, `test_upstream_files_are_well_formed` passing by node id on the rebuilt set), and the wheel sentence cites the 104,857,600 line of #72.
2. **Taken** (the review's Lows commit after the rebase onto `dev` at `30566232`): the Status line begins "built 2026-10-31 on `spec/165-python-docx-and-python-pptx` (pull request #70), not landed".
3. **Taken** (the review's Lows commit after the rebase onto `dev` at `30566232`): the `shapetree.py` bullet adds the `add_picture` corner, in your words.

**Reviewer:** all three confirmed (READ, `5a18d752`), each the fix text as given. The self-check was not read (no `gh` call).

## Verdict

Lands: the patches, pins, zip, suites and judge changes are sound, the three Lows are fixed in `5a18d752`, run 41202001240 is green with every growth claimed, and the x86-64 same-bytes vote passed in 41201012715.
