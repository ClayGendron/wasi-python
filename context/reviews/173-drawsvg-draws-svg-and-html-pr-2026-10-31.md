# Review of 173 — drawsvg draws SVG and HTML

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude), a fresh sub-agent of Claude Code session 0672b924-ca3c-4b6c-91ca-f834537cb1bc; not the author
- **Reviewed:** pull request #86, `spec/173-drawsvg-draws-svg-and-html` at `a9b3ea89`, the diff `2ec3c1ee...a9b3ea89` (23 files), with the specification, its pre-build review and the news file; then the fix commit `02a6be8c`
- **Run:** `41255302937` on `02a6be8c` (`ci-status`), read below.
- **Re-ran:** on the builder's sets (`build/artifacts` from this head, `build/artifacts-dev` from dev's recipe): ruff and `tests/lint` (14 passed); `test_shards.py` and `test_artifact_rules.py` (118 passed); on this set the two new checks, three neighbouring rules (7 passed) and `test_v1_1_artifact_set.py` (50 passed, 1 skipped); on dev's set the two new checks (3 failed, `No module named 'drawsvg'`); start fuel; the pdf job under the oracle.

Labels: EXECUTED, READ, INFERRED. I dispatched no run.

## Acceptance criteria against evidence

1. The pin and the `none` reason — met. The wheel's SHA-256 equals `SHA256SUMS`, the oracle's lock and `MANIFEST` (EXECUTED); the reason names the sdist, the tag and master (READ).
2. The golden job — met. It passes on this set and fails on dev's (EXECUTED); the oracle reproduces it (READ, `build/regen-check.txt`).
3. The guest check — met. It passes on both binaries and fails on dev's set; every loaded `drawsvg` module comes from the zip (EXECUTED).
4. The six refusals — met. Five `BAD_PACKAGES` rows and two functions cover them, the `ast` row included (READ, EXECUTED). The one-guard mutation I took from the landing notes (READ).
5. The artifact-set checks — met. `LICENSES/drawsvg.txt` is the wheel's MIT text; `MANIFEST` has the package, `pin` and `x-snapshot-package` lines (EXECUTED).
6. Bytes and fuel — met, and honest (EXECUTED). Zip +90,595 bytes and 22 members; snapshot +19,294; `python.wasm` unchanged. The snapshot start reproduces exactly. A plain start spreads about ±0.1 % between runs: my four-run means give +0.20 %, the builder's +0.15 %. The wheel I could not rebuild (INFERRED plausible); CI's wheel check holds it. `9d311a0a..2ec3c1ee` touches only `context/`, so the numbers stand.
7. Fast tier, lint, `ci-status` — met. Lint green (EXECUTED); every judge leg of run `41255302937` passed; `ci-status` is red only for want of this file (READ).

## The run

Run `41255302937` on `02a6be8c` (READ: `gh pr checks 86`, the gather's and `ci-status`'s logs, the gather's record).

- `quick`, the build, `verify`, all 20 Linux legs and all 11 Windows legs passed. macOS and the release tier were not selected.
- Scoreboard: 1026/2122 pass, 129 gap, 6 blocked (dev's), 0 fail. `ci-status` and `review` are red only for want of this file.
- No `GROWTH` or `unclaimed` line. Against dev's `accepted.json` the record loses no pass (EXECUTED). Its six new passes are this change's three and three of 171's not yet in dev's record.
- Dev's accepted fuel is darwin-arm64 only, so the `grows` claim is read at the post-merge acceptance, which runs macOS.

## Findings, most severe first

No High and no Medium.

1. **Low: the self-check's Windows box is unticked** (the pull request's description). It is unticked for the right reason: the run had not started. Fix text: tick it once the Windows legs of the head's run are read, all boxes in one edit.
2. **Low: "its golden job is its only check" overstates** (`docs/reference/packages.md`, the paragraph after the pure-Python table). `test_drawsvg_names_what_the_set_lacks` also runs drawsvg in the guest. Fix text: "drawsvg ships no tests of its own, so its golden job stands in for them: it shows the guest writes native drawsvg's SVG and HTML bytes." This touches `docs/`, so it is the author's to make or answer.
3. **Low: the landing notes name the bases `863c2929` and `9d311a0a`, not the branch's base `2ec3c1ee`** (`context/specifications/173-…md`, Landing notes). Fix text, appended to "Measured": "The branch was then rebased onto `2ec3c1ee`; `9d311a0a..2ec3c1ee` touches only `context/`, so the measurements stand."

## Constitution checks

- §4.1: no patch; drawsvg's own `ImportError` text is kept.
- §4.12: drawsvg (MIT) is approved in §4.12 and `decisions.md`. Its notice ships as `LICENSES/drawsvg.txt`, `LICENCE_COMPONENTS` and `PACKAGES` name it, and `MANIFEST` has its package line. `Package rows: None.` is right: that table is for compiled packages.
- Pins: URL and SHA-256, verified.
- Judge: `packages.toml`, the one verdict-bearing file, is claimed; nothing is loosened; `grows`, `new` and `units = 7` match the diff.
- No `src/` change. No comment, docstring or page names a specification or `context/` path. The trailer is Claude Opus 5.5.
- §7: nothing tripped.

**Note, not a finding against #86.** `regen.py --check` fails on `pdf` on dev. 167 (`a750e8fe`) brought `cryptography` into the oracle's lock through pdfminer-six. `pdf.expected` expects `AES-128 DependencyError`, which the guest still gives, and natively line 6 reads `AES-128 True OWNER_PASSWORD Invoice 17` (EXECUTED). No CI job runs `regen.py`. Its judge form, `test_goldens_reproduce_under_the_pinned_oracle`, needs the oracle, which no workflow provides, so `accepted.json` keeps its pass from `2961ea34`, before 167. Its fix is its own change.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 — answered: the orchestrator ticks the Windows box once this review is signed. The 11 Windows legs of `41255302937` passed (READ).
2. Finding 2 — fixed in `02a6be8c`: the page now says the project checks drawsvg instead, through the golden job and a second check of what the set lacks. Read and confirmed.
3. Finding 3 — fixed in `02a6be8c`: the landing notes name the rebase onto `2ec3c1ee` and why the measurements at `9d311a0a` stand. Read and confirmed.

## Verdict

Lands on 02a6be8c: every criterion is met, the new kind is narrow and each refusal holds, run `41255302937` passed every judge leg on Linux and Windows with no loss, and the three Lows are fixed or answered.
