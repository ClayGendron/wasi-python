# Review of 170 — Pillow reads and writes JPEG

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** `0ebf7dc2`, the fix `ceb24521`, then the rebase onto `9c0d879e` (head `7d694412`)
- **Run:** 41275395475 on `7d694412` (relayed): every job green, the 13 Windows legs included. Before the rebase, 41216656701 on `ceb24521`. No `gh` call, no run dispatched.
- **Re-ran:** lint, the new and held checks by node id → passed; the job under the oracle, plain and with `JSIMD_FORCENONE=1` → both equal the golden. After the rebase, below.
- **Time box:** 45 minutes; kept.

## Acceptance criteria against evidence

1. Signature, fingerprint and source — met (READ, landing notes).
2. Licence sweep, IJG and BSD-3-Clause only — met (READ, landing notes).
3. 101 files, and the step's refusals — met (READ, `37_plot_libs.sh`; refusals seen by the builder).
4. Broken-JPEG check — met (EXECUTED, both binaries; seen failing first, READ).
5. Golden — met (EXECUTED: SIMD and `JSIMD_FORCENONE=1` equal, and equal the golden).
6. Imports and tag count — met (EXECUTED).
7. Suites — met before the rebase: 0 fail, each class matching its gap (READ).
8. Tree row and notice — met (EXECUTED; READ, `assemble_artifacts.py` ships `LICENSE.md` and `README.ijg`).
9. Wheel 99,687,768, 5,169,832 under the line; 167 (about 2.2 MB) and 169 (at most 1.0 MB) still fit (READ; INFERRED).
10. `ci-status` — met: 41275395475 green (relayed). The x86-64 same-bytes vote is read at the first weekly run after the merge and recorded in the landing notes then, as 165's was.

## The questions put to this review

**`JPEG_LIB_VERSION` 62 is right.** The oracle's wheel reports `jpg` 6.2 and ships `libjpeg.62.4.0.dylib` (EXECUTED). 62 is libjpeg-turbo's default; 80 needs `WITH_JPEG8` (`CMakeLists.txt:378-383`), which only Pillow's Windows build sets (`winbuild/build_prepare.py:143`). Pillow only prints the macro, and the library's 7.0 and 8.0 branches on Pillow's paths change no output (`jcmaster.c`, `jcparam.c`, `jdmaster.c`; READ). Decision 2 said 80 (Finding 1, fixed).

**Build hygiene.** Pinned by URL and SHA-256. The headers are recipe files held to their templates; no patch. `BUILD` fixed, SIMD off, archive in list order. The weekly same-bytes run is the backstop.

**Hostile input.** Pillow's handler longjmps to its `setjmp`, then destroys the codec (READ). In the guest, longjmp throws the `__c_longjmp` tag, as for qhull. The check proves 300 header-time errors neither trap nor break the next decode. It measures no memory; the destroy calls and Pillow's `check_jpeg_leaks.py` are the leak evidence. A bomb costs only the guest's fuel and memory (INFERRED).

**The judge.** Every class, gap, cap and shard change is claimed under `[claim.judge]` with its reason; caps move by the 1.5 rule (910 G, 140 G). The shards hold at 621.1 G and 683.4 G. The pre-build write-in is done. One closer was wrong (Finding 2, fixed). The three "unclaimed" pass gains are claimed under `passes`; the gather prints the empty `fewer` text, and acceptance needs no reason for a gain (`scoreboard.py:200-204`, READ).

**The news file.** Two entries in the house shape; the package rows carry the IJG sentence.

## Findings, most severe first

1. **Low: Decision 2 still says 80** (`context/specifications/170-pillow-reads-and-writes-jpeg.md`, Decision 2, "The configuration"). The built configuration is 62, and the specification states 80 with a reason that no longer holds. Fix text: replace "`JPEG_LIB_VERSION` 80, as Pillow's own Windows build sets `WITH_JPEG8`." with "`JPEG_LIB_VERSION` 62, libjpeg-turbo's default (the libjpeg v6b API), as the oracle's macOS and Linux wheels are built; only Pillow's Windows build sets `WITH_JPEG8` (amended at the build; the landing notes say why)." Context only; the author or the reviewer may commit it.
2. **Low: `not-pillows-wheel` names a closer that does not close it** (`tests/upstream/pillow.toml:101`, `tests/known_gaps.toml:497`). Its `closes_with` moved from 023 to 170, but 170 lands and `check_wheel.py` still fails. A reader of the gap sees a closed specification as the closer. Fix text: `closes_with = "docs/reference/limitations.md"` in both files, as the other permanent codec allowances read. This is a judge file, so the change is the author's, under the existing `changed` claim.

3. **Low: the self-check's Windows box is unticked.** Fix: tick it; the 13 legs are green.

## Constitution checks

- §4.1 and pinning hold: no patch, one tarball pinned by URL and SHA-256.
- §4.12 holds: approved, shipped, and the IJG sentence reaches the packages page.
- §5.6: reviewed before the build; imports, exports and tags unchanged (EXECUTED).
- The judge is not weakened: each edit narrows an allowance or raises a cap by rule.
- `.github/workflows/release.yml`: three jobs expect one more source tree (33 after the rebase). Nothing else changes in what runs or holds a token.
- Structure: nothing under `src/`. §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Fixed in `ceb24521`: Decision 2 says 62 in the fix text, and the Status line agrees. Confirmed (READ).
2. Fixed in `ceb24521`: `closes_with = "docs/reference/limitations.md"` in both files, its reason added to the two `[claim.judge]` lines. Confirmed (READ).
3. The coordinator ticks the box before the review commit.

## After the rebase (2026-11-01)

`git range-diff` of the three commits (EXECUTED) differs only in:
- the claim block, now `context/release-claims/170-pillow-reads-and-writes-jpeg.toml`, same text, named in `[claim.judge]`;
- context lines from #86 (`vector_drawings`, drawsvg's limitation), above 170's additions.

Against `9c0d879e`, the diff touches only 170's files; its deletions are the five class lists that leave. `JOBS` keeps `pdf_tables`, `labelled_arrays` and `vector_drawings`, then `jpeg_images`. The workflow's tree count moves from dev's 32 to 33, as does `SOURCE_COMPONENTS`. Nothing from #71, #86 or #87 is undone (READ).

On the rebuilt set (EXECUTED):
- `test_source_tree_matches_its_tarball`: 33 passed;
- the two JPEG checks: 3 passed;
- the news, ledger and known-gaps rules: 4 passed;
- `tests/lint`: 14 passed.

## Verdict

Lands on `7d694412`: no High or Medium; Lows 1 and 2 fixed, Low 3 answered.
