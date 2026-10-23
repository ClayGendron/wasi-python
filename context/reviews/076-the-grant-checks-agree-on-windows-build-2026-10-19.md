# Review of 076 — The grant checks agree on Windows (the build)

- **Date:** 2026-10-19
- **Reviewer:** a fresh agent (Claude Opus 5.5). I wrote the spec's pre-build review and its confirmation, and none of the code.
- **Reviewed:** `spec/076-the-grant-checks-agree-on-windows` at `b8fe1ac`, on main `6fd89e0` (`git diff c0c5698..b8fe1ac`: `cb1d8be` the build, `d0d1dd7` the UTF-8 README read and notes, `b8fe1ac` notes). Read whole: the `runner.py` hunk, the four test files' hunks, `tests/harness/files.py`, `README.md`, `CHANGELOG.md`, the landing notes. The facts sheets were read for their claims only. Main has since moved to `b413192` (047, 055); the lane rebases at landing.
- **Ran:** EXECUTED on darwin-arm64, against the frozen set `build/sets/s-ff5246a2c2f1a52b`, read only. No tracked file of any tree was written. The judge runs rewrote the worktree's git-ignored `build/progress/latest.json`; the builder's record was copied first, to `builder-latest.json` here. Edits and stand-ins ran on a scratch copy (`tree/`, from `git archive b8fe1ac`). Scripts and outputs sit beside this file:
  - `probe_built_walk.py` → `.out`: the **built** `runner._walk_windows`, driven through its own seams (`_win_open`, `_close_held`, `_drive_folder`) over my confirmation's Win32 model. It runs named rows, roots to be made, and a fuzz of 96,205 spellings under ten heads, three more than the builder's unit case: `\\srv\share` and `\\?\C:` with nothing after them, and a lower-case `c:`.
  - `standins.py` → `standins.out`: eight stand-ins re-made independently on the scratch copy.
  - `probe_read_len.py` → `.out`: what the new raw read row actually reads.
  - `gh-temp-commits.json`, `dryrun2-windows-verify.log`: both temporary commits and the Windows verify log, fetched from GitHub with `gh`.
  - `fast-n3.log`, `full-n3.log` and their `-latest.json` records: the judge.

## What holds

1. **The walk is the confirmed design** (READ, and EXECUTED with the model).
   - **The judged start.** `splitdrive`. A rooted tail, or a share or verbatim drive with nothing after it, starts at the drive's root. A rooted path with no drive takes `_drive_folder("")`'s drive. Anything else starts at `_drive_folder(drive)`.
   - **The walk.** `..` pops the handle, the identity and the prefix, never below the root. Prefixes are concatenated, never joined. The root is entered as `drive + "\\"` (N6). A missing component followed by `..` is refused, or returned as `missing` when `may_make`.
   - **Rewritten names.** Every component, the start's own included, is checked before any open (departure 4).
   - **Handles.** `enter` appends the handle before its checks, and the outer `except` closes every held handle, so a refusal leaks nothing.
   - **The unjudged walk.** Unchanged in effect: `ntpath.realpath` is `os.path.realpath` on Windows, and concatenation gives the same strings as `os.path.join` for its names.
2. **The fuzz agrees with the built code** (EXECUTED, `probe_built_walk.out`).
   - Over 96,205 spellings: 1,179 accepted, **0 with a wrong chain, 0 leaking a handle, 0 errors other than `ValueError`**.
   - Every named row behaves as the spec says:
     - the review's two cases, `a.`, `...`, `::$INDEX_ALLOCATION`, `NUL`, `nul.txt` and `aux.d` are refused "a name Windows rewrites";
     - `.hidden` and `v1.2` pass;
     - `C:\b\..` gives `C:\`, `\\srv\share\x\..` gives `\\srv\share\`, and `\\srv\share` and `\\?\C:` give their roots;
     - `C:\b\sub\..\x` holds three handles;
     - `root=C:\b\new\NUL` and `C:\b\new\x.` are refused before anything is made (the confirmation's corner, closed).
3. **The stand-ins bite.** The builder's log records S1 to S4 and S6 to S15 as CAUGHT, and S5 in its own log (READ). I re-made eight independently on the scratch copy: S1, S2, S3, S11, S12, S13, S14 and S15 are all CAUGHT, each with the expected message, and the unchanged copy passes (EXECUTED, `standins.out`).
4. **The judge is not weakened** (READ).
   - *The read-only check.* The write row's value comes from one per-system table. The Windows link branch is deleted, so the link row is 63 everywhere; that is stricter.
   - *The bad-grant check.* It gains four rows and two `exists()` assertions; nothing is removed.
   - *The rename check.* At full fuel it now asserts the native end per system and the guard's `returned ENOTDIR` exactly. At each cap it compares guard with native, after mapping native's own Windows ending to the guard's. On Linux and macOS that mapping is the identity, so every assertion there is as before.
   - *The raw case.* Two new rows.
   - *The UTF-8 README read* (departure 6). It changes how the file is decoded, not what is asserted. The README is UTF-8, so this is the correct reading.
   - `tests/public_api.txt`, `scripts/`, `recipes/`, `downloads/` and `.github/` are untouched (EXECUTED: an empty `git diff`). `ruff check` and `ruff format --check` pass on the copy (EXECUTED).
5. **The dry-run evidence is honest** (EXECUTED with `gh`).
   - **Run 1, 39193391287.** `headSha` `baa4b3e…` on `spec/076-verify`, `workflow_dispatch`, failure. That commit's only parent is `cb1d8be`.
   - **Run 2, 39196291455.** `headSha` `1cfeff6…`, success. Its only parent is `d0d1dd7`.
   - **The temporary diff.** Each temporary commit changes exactly one file, `.github/workflows/release.yml`, +4 −1: `-rA` and the three node ids, nothing else (`gh-temp-commits.json`).
   - **Jobs.** In run 2 every job succeeded on all three systems; attest and both publishes were skipped, as on any dry run.
   - **The Windows passes.** I fetched the `verify (windows-2025)` log myself. It holds a `PASSED` line for every node criterion 9 names, plus `test_default_integer_width_is_documented`, and `blocked by: ['oracle', 'three systems', 'wheel']`.
   - **Cleanup and freshness.** `git ls-remote` shows no `spec/076-verify` left. `d0d1dd7..b8fe1ac` touches only the spec file, so the code that ran on Windows is the code under review.
   - **Departure 5** (`git commit-tree` pushed straight to the remote ref) made no local branch. The lane ruled the remote branch, and its record is complete.
6. **N2 is settled.** The Windows job installs Python under `UV_PYTHON_INSTALL_DIR=D:\a\_temp\…`, and the bad-grant check's stdlib rows passed there (EXECUTED there, READ in the log).

## The departures

1. **`WRONG_MODE_ERRNO`.** Better: the table holds the read twin too. Accepted.
2. **The extra fuzz unit case.** A real guard: it would have caught F1, and S12 and S15. It is deterministic, counts only operations, and asserts it is not vacuous. Accepted.
3. **A bare share or `\\?\` drive is rooted.** Right: such a drive has no current folder, and Win32 treats it as rooted. Probed: `\\srv\share` gives `\\srv\share\` and `\\?\C:` gives `\\?\C:\`, both with a true chain. Accepted.
4. **Rewritten names checked before any open.** Stricter than "before it is opened", and the simplest form of the rule. It also refuses a path whose process current folder holds such a name, which is conservative and can only happen through `\\?\`-made folders. Accepted.
5. **`git commit-tree`.** No local branch, and the remote branch is deleted. Honest and recorded. Accepted.
6. **The UTF-8 README read.** It fixes a defect already on main (spec 046's README text cannot be decoded as cp1252), which would fail main's own next release dry run on Windows. Nothing is loosened, and the lane's `--accept-judge` line names it. Accepted.

## Findings, most severe first

### F1 (Low): the new raw read row reads zero bytes

`test_a_read_only_grant_refuses_raw_writes` reads through an iovec at offset 400, which nothing writes, so it is `{buf 0, len 0}` (EXECUTED, `probe_read_len.out`: `(0, 0)`). wasmtime still calls the host read with an empty buffer (49.0.0 `p1.rs:204-219`, `1672-1695`, READ). It answers 8 on macOS (EXECUTED), Linux and Windows (the dry runs), because each kernel checks the mode before the count. So the row passes, and the README's claim about reads holds. But it observes a zero-length read, an edge case some file systems or future versions could short-circuit, not an ordinary one. A two-byte read through the same descriptor answers 8 too (EXECUTED). Point the `read` export at a real iovec (the existing one at 200, `buf 300 len 2`), or add the eight bytes at 400 to the module's data. One line; re-run the row on all three systems with the next dry run that 063 or a later spec makes, or now if the lane prefers.

### F2 (Low): the reserved names leave out `COM¹ COM² COM³ LPT¹ LPT² LPT³`

Microsoft's "Naming Files, Paths, and Namespaces" lists the superscript forms as reserved "in every directory" (READ today). `_WIN_DEVICES`, the README, the CHANGELOG and the test model stop at `COM1-9` and `LPT1-9`.
- The chain stays true: walking through one, Win32 maps it to the device, and the open fails, so the path is refused.
- But the corner the clause exists for, a root still to be made through a reserved name, stays open for these six: `root=C:\b\new\COM¹` makes `new`, then fails "cannot be made" (INFERRED from the walk and `_make_missing`).
- Fix: add the six to `_WIN_DEVICES`, the model and one criterion-1 row, and say "`COM1` to `COM9`, `COM¹` to `COM³`" and likewise for `LPT` in the README.

## Notes (no action)

- N1. `_win_resolve` in the unit model strips one trailing period even from `a..`, where Win32 strips one only if a single period ends the segment. Every name ending in a period is refused before the model sees it, so this cannot change a verdict.
- N2. The confirmation's N6 (the drive's root) and the reserved-name corner are both built and guarded (S15, S14).
- N3. Facts sheet 20 and fact 5 of facts sheet 12 carry the corrections the pre-build review asked for: preview2 checks only the grant's perms, the `sync_data` precedent, the runner image.

## The judge

EXECUTED in the worktree, `-n 3`, with `WASI_PYTHON_ARTIFACTS` set to the frozen set.

- **Fast tier**, `uv run pytest -m "not slow" -n 3` (`fast-n3.log`): `wasi_python v1: 371/442 pass · 0 gap · 22 blocked · 0 fail · 49 deselected (unit suite 1254/1262, 8 skipped)`; `ratchet vs 75f03ab77e: lost 0 · absent 0 · unrun 0 · … · gained 0 · grew 0`; the judge change named (five files, `test_v1_3_data_stack.py` among them); `1625 passed, 30 skipped`.
- **Full judge**, `uv run pytest -n 3` (`full-n3.log`, `full-n3-latest.json`): `386/442 pass · 2 gap · 54 blocked · 0 fail (unit suite 1254/1262, 8 skipped)`; `lost 0 · absent 0 · unrun 0 · gained 0 · grew 0`; `1640 passed, 62 skipped, 2 xfailed`. The blocked checks are the worktree's missing source trees and clones. These are the builder's numbers.
- `uv run python tests/harness/sameness.py build/076/full-n3-latest.json full-n3-latest.json`: no differences, exit 0 (EXECUTED; the builder's record against mine).

## Verdict

**It lands.** F1 and F2 are low, and neither touches a refusal or the wall. They are to be taken or answered in writing before landing. Mind Decision 7's freshness rule: either one changes `tests/` (F2 changes `src/` too), so taking them now needs one more Windows dry run on a throwaway branch, as before. Answering them in writing and taking them in the next spec that runs on Windows is the cheaper equal; spec 063's rebase onto main with 076 runs every row there. The lane chooses.

## One line

The built walk is the confirmed design: 96,205 modelled spellings give no wrong chain and no leaked handle; eight stand-ins re-made independently all bite; the judge is stricter, not weaker; the Windows dry run is honest down to its parent commit and its four-line diff. Two low notes remain: a zero-length read row, and the superscript `COM¹`/`LPT¹` reserved names.
