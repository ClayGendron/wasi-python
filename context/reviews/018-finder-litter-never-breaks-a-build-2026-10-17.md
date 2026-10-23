# Review of 018 — Finder litter never breaks a build (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change. I also did not write the specification's pre-build review or its confirmation; that was another agent. I read `AGENTS.md`, the constitution (§4, §4.9, §4.10, §5.2, §7), `context/reviews/README.md` and the 016 build review (for its format). Then I read specification 018 with its landing notes, its pre-build review with the confirmation, the memo `2026-10-17-finder-litter-breaks-a-desktop-build.md`, and the diff. I did not rely on the landing notes. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** the scratch clone's `git diff 8a2be32 6ee9bbf` (one commit, `6ee9bbf`). It touches `scripts/steps/remove.sh` (new), `scripts/litter.py` (new), `scripts/build.sh`, `scripts/steps/common.sh`, steps 10, 20, 30, 35, 40, 50, 60 and 80, `scripts/make_stdlib_zip.py`, `scripts/assemble_artifacts.py`, `tests/harness/scan.py`, `tests/unit/test_scan.py`, `tests/unit/test_build_scripts.py` (new), `README.md`, the memo and the specification.
- **Re-ran (EXECUTED, darwin-arm64, macOS 26.5.2, APFS; the clone's own `build/`; the main tree's `build/artifacts` read only).** Probes and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev018b/`: `pytest-full.txt`, `clone-set0/` (a copy of the clone's set as I found it), `cmpset.sh`, `planted.txt`, `sem/` (`remove` under four shells), `scan/` (scan-rule probes), `mut/` (copies with mutations, `mutations.txt` and one log each), `race/` (a Finder-like writer and two drivers, with `race-0.0005.txt` and `race_py.txt`), and `author-logs/` (the author's step logs, copied before my runs overwrote steps 70 to 90's logs).
  - `uv run pytest -p no:cacheprovider` in the clone → `162/166 pass · 0 gap · 4 blocked · 0 fail (unit suite 360/365, 5 skipped)`; v1.5 `18/18`; `522 passed, 9 skipped`; ratchet vs `408819a846`: `lost 0 · absent 0 · unrun 0 · unrun locally 2 · gained 0 · grew 0 · judge changed: tests/harness/scan.py, tests/unit/test_build_scripts.py, tests/unit/test_scan.py`; `next: context/specifications/004-alpha-releases.md (unblocks 2, closes 0)`; blocked by oracle, prior-art clones, three systems and wheel (1 each); **exit 0**. I did not pass `--accept`.
  - `uv run ruff check src tests` → all checks passed; `uv run ruff format --check src tests` → 48 files already formatted.
  - `sh scripts/build.sh 90`, `sh scripts/steps/90_artifacts.sh` alone, and `sh scripts/build.sh 70 80 90` with planted litter, in the clone. I did not run steps 10 to 60.
  - I did not commit or push. The clone's `git status` was empty before and after, at `6ee9bbf`. I wrote nothing in the main tree. Everything I planted under the clone's `build/` is removed (`find build -name .DS_Store -o -name Thumbs.db -o -name desktop.ini` → 0), and the clone's `build/artifacts` ends byte for byte as I found it (`cmpset.sh` → 17 of 17 equal).

## Decisions against the code

- **Decision 1, `remove.sh` (READ, EXECUTED).** The function is the Design's, character for character. `sem/sem.sh` runs it under `set -eu` with a counting `rm` shell function, on two folders and a dangling link, in `/bin/sh`, `/bin/dash`, `/bin/bash` and `/bin/zsh`. Same result in all four:

  | `rm` fails | exit | calls (3 paths) | left | standard error |
  |---|---|---|---|---|
  | never | 0 | 3 | nothing | empty |
  | first call | 0 | 4 | nothing | empty |
  | always | 1 | 3 | all | `fake failure 3`, then `ERROR: cannot remove …/a` |

  - Only the third attempt's error is shown, so the cause is the line before `cannot remove`.
  - A dangling link that `rm` cannot remove makes `remove` exit 1 (`sem/link.sh`, EXECUTED). With the `[ -L "$p" ]` test deleted it exits 0 and leaves the link (finding 3).
  - No sleep between attempts (READ).
- **Every former `rm -rf` site (READ, EXECUTED).** Against the old scripts, the new scan rule finds 12 lines: `build.sh:37`, three in step 10, one each in steps 20, 30, 35, 40, 50, 60, 80, and `common.sh`'s `find … -exec rm -rf`. In `6ee9bbf` each is `remove` or the `while read` loop, and the scan finds none. The only `rm` left in `scripts/` outside `remove.sh` is `rm -f` of single files (`wasi-cc:30`, `common.sh:43`, `60_link.sh:75`). `.github/` and `recipes/` have no recursive `rm`.
- **The `while read` loop under `set -e` (EXECUTED, `sem/loop.sh`).** Two caches, one under a folder whose name has a space and one holding a read-only subfolder: the first is removed, then `rm`'s three lines, `ERROR: cannot remove …/b c/__pycache__`, and exit 1. The pipeline's status is the loop's, so `set -e` stops the step with the one line.
- **`build.sh` sources `remove.sh` (READ).** After `set -eu`, before the step loop. A failure there prints `ERROR: cannot remove …` and exits 1 before any step runs.
- **Decision 2, `litter.py` (READ, EXECUTED).** One `frozenset`, imported by both scripts. `test_the_scripts_litter_is_the_judges` holds it equal to `paths.OS_LITTER`. No module named `line` or `litter` exists under `tests/` or `src/`, and no file in `scripts/` shadows a stdlib name, so the test file's `sys.path.insert(0, scripts)` shadows nothing today (READ).
- **Decision 3, the zip (READ, EXECUTED).** `SKIP_NAMES` gains `OS_LITTER`; the walk serves `--lib` and every `--tree`. The littered run below gives the same zip.
- **Decision 4, `licence_files` (READ, EXECUTED).** `sorted(…iterdir() if name not in OS_LITTER)`. The only folder listing in step 90; the other licences come from named files or from pinned wheels.
- **Decision 5, `drop_litter` and `_remove` (READ, EXECUTED).**
  - `drop_litter(new)` runs right before the listing, as decided. But a file written between the two is listed (finding 4).
  - `_remove`: three `rmtree` attempts, each catching `OSError`, verdict by `os.path.lexists`; a path already gone is success (condition A). `test_step_90_removes_or_says_why` covers that, and the stale `artifacts.new` I left with a `.DS_Store` in it was removed by step 90 alone. But each attempt stops at its first error, unlike `rm -rf`, and loses to a writer that `remove` beats (finding 1).
- **Decisions 6, 7 and 8.** The judge is not loosened (READ). Source trees keep litter; no check was added for files a build adds there, which stays on the "not machine-checked" line (EXECUTED, in the scoreboard). Decision 8 is checked under criterion 3 below.

## The steps run alone

- `sh scripts/build.sh 90` in the clone → `ok 90_artifacts: artifacts: 17 files in build/artifacts`; the set is byte for byte the one I found (EXECUTED).
- `sh scripts/steps/90_artifacts.sh` alone stops with `KeyError: 'SOURCE_DATE_EPOCH'` (EXECUTED). That predates this change (READ: the `x-source-date-epoch` line is not in the diff). With `SOURCE_DATE_EPOCH=1767225600 PYTHONHASHSEED=0 LC_ALL=C`, over a stale `artifacts.new` holding `LICENSES/sub/.DS_Store`: exit 0, `artifacts.new` gone, the set the same (EXECUTED).
- `sh scripts/build.sh 70 80 90`: all three `ok` (EXECUTED, below).

## Criterion 3: the artifact set

- **Against the main tree (EXECUTED, `cmp`, read only).** `python.wasm`, `python-snapshot.wasm`, `python-stdlib.zip` and all twelve `LICENSES/*.txt` are byte for byte the main tree's. The file lists are equal. `SHA256SUMS` differs in one line, `MANIFEST`'s.
- **`MANIFEST` (EXECUTED).** `diff` shows only `recipe` lines: twelve changed, for exactly the twelve changed scripts, and two added, `scripts/litter.py` and `scripts/steps/remove.sh` (35 → 37 lines). Every clone `recipe` hash equals that file at `6ee9bbf`, and every main-tree hash equals it at `8a2be32`. So the set was made by the committed scripts.
- **The author's full build (READ).** `build/logs/` holds all eleven steps, ending `artifacts: 17 files`, written 11:48 to 11:57, before the commit at 11:59. Step 90 refuses untracked recipe files, and the `MANIFEST` hashes match `6ee9bbf`. INFERRED: steps 10 to 60 ran the same scripts; I did not re-run them.
- **The litter re-run (EXECUTED, `planted.txt`).** I planted 14 files, each with distinct bytes:
  - `.DS_Store`, `json/Thumbs.db` and `encodings/desktop.ini` in CPython's `Lib/` (`--lib`);
  - `.DS_Store` in numpy's `site-packages/` (the tree's root), in `numpy/`, and `numpy/linalg/Thumbs.db`;
  - `.DS_Store` and `Thumbs.db` in `build/pandas-install/`, `pandas/.DS_Store`, `pandas/core/Thumbs.db`;
  - `.DS_Store`, `Thumbs.db` and `desktop.ini` in `build/pandas-3.0.6/LICENSES/`;
  - `.DS_Store` in `build/out/`.

  `sh scripts/build.sh 70 80 90` → three `ok`, `python-stdlib.zip: 1098 pyc, 653 data files, 11140578 bytes`. All 17 files are byte for byte the set before, `MANIFEST` and `SHA256SUMS` included; no litter name in the zip or the set. Then I removed the 14 files by that list.
- **A writer during removal (EXECUTED, `race/`).** `writer.py` writes a `.DS_Store` into each folder of a junk tree (158 folders, 1,728 files) that still exists, deepest first, with a 0.5 ms pause after each write, until told to stop. The tree sits in `build/artifacts/junk/`. Ten runs each:

  | what removes `build/artifacts` | succeeded |
  |---|---|
  | plain `rm -rf` | 0 of 10, `Directory not empty` |
  | `sh scripts/build.sh 90` (`remove`) | 10 of 10, set the same each time |
  | `sh scripts/steps/90_artifacts.sh` alone (`_remove`) | 6 of 10; 4 end `cannot remove …/build/artifacts` |

  `race_py.py` isolates the Python half, in the pinned host CPython 3.15.0, 20 runs each against the same writer: `_remove` as built removes the tree 11 of 20 times; the same loop with `rmtree(path, ignore_errors=True)` in each attempt, 20 of 20 (finding 1).

## The checks

- **They count (READ).** Every assertion is on exit codes, `rm` call counts, standard error, names yielded, or files present. The 60 s `subprocess.run` timeout is a fail-safe against a hang; no duration is asserted. §4.9 holds.
- **The skip rule (READ, condition B).** Each `sh` case calls `pytest.skip("needs: a POSIX sh")` when `shutil.which("sh")` is `None`. Unit files have no area, so the plugin counts the skip as "skipped" and never turns it into a pass or a failure (`plugin.py`, `pytest_runtest_makereport`). `line.read()` raises nothing on a host outside the three build hosts, so importing the two scripts works on Windows (READ, `scripts/line.py`). On win32 the dangling-link case skips with the same "a POSIX sh" reason, though the need there is symlinks (finding 5).
- **Seen failing first (EXECUTED).** In a copy with `8a2be32`'s scripts and the new tests (`mut/O1_old_scripts`): the walk, the step-90 litter and `_remove` cases and the real-tree scan case fail (4 failed). A `remove` with a fourth attempt fails `test_remove_stops_after_three_attempts_with_one_line` (`M8_four`). The author's one-attempt stand-in is in the landing notes; I did not repeat it.
- **Mutations that survive (EXECUTED, `mut/mutations.txt`).** Each copy ran `test_build_scripts.py` and `test_scan.py` (78 passed, 1 skipped, unmutated):

  | # | mutation | result |
  |---|---|---|
  | M1 | `remove` without `|| [ -L "$p" ]` | **survives** (finding 3) |
  | M2 | `remove` handles only `$1` | **survives** (finding 3) |
  | M3 | `_remove` = `rmtree(path, ignore_errors=True)`, never raises | **survives** (finding 3) |
  | M4 | `licence_files` not sorted | survives; the same-bytes gate covers order |
  | M5 | `remove` says `return 1`, not `exit 1` | survives; equivalent under `set -e` at every call site (INFERRED) |
  | M8 | `remove` tries four times | caught |

- **The scan rule `bare_rm_hits` (EXECUTED, `scan/scan_probe.txt`).** The flag logic is right: `-rf`, `-fr`, `-Rf`, `-r -f`, `-r -v -f`, `--recursive -f`, `-R --force` and `rm -rf --` all hit; `rm -f`, `rm` and `firm -rf` do not. But the regex only finds `rm` after a line start or one of `; & | ( \` { $( then do else -exec`. It misses (finding 2): `if rm -rf`, `while rm -rf`, `! rm -rf`, a `case` arm `x) rm -rf`, `command rm -rf`, `\rm -rf`, `/bin/rm -rf`, `x=1 rm -rf`, `time rm -rf`, `exec rm -rf`, `xargs rm -rf`, `-execdir rm -rf`, and `rm \` with its flags on the next line. False positives, all failing closed: `rm -rf` after `;`, `(`, `then` or `do` inside a string or a trailing comment (`remove "$x"  # then rm -rf it`), and in a here-document. Full-line comments are skipped.

## The judge

See *Re-ran*. The scoreboard matches the landing notes (162/166, unit 360/365, 522 passed, 9 skipped, lost 0, gained 0, grew 0, the same three judge files). The notes leave out `unrun locally 2`; that is the clone's missing system history, not this change.

## The docs

- **README (READ).** Accurate in substance. "Every step removes its old outputs through `remove`" is loose: step 90 removes through `_remove`, and step 70 removes nothing (finding 5). "The artifact set never packs such a file" holds except for finding 4's window.
- **Memo (READ).** The addition is accurate. The "Until then …" sentence above it stays as history, which is fine.

## Acceptance criteria against evidence

1. *The checks exist and were seen failing before the change.* **Met** for the properties the Design names (EXECUTED above). Weak in three places: finding 3.
2. *`uv run pytest` green with `--accept-judge`, after the main tree's set is rebuilt.* **Pending the landing.** In the clone: exit 0, lost 0, grew 0, the judge changed in the three named files (EXECUTED).
3. *Byte for byte, `MANIFEST` only in recipe lines, `SHA256SUMS` only in `MANIFEST`'s line; the littered re-run the same.* **Met** (EXECUTED above), with more litter than the criterion asks.
4. *A release dry run passes every job.* **Not shown.** INFERRED to pass: the Windows `verify` job runs no file under `tests/unit/` but `test_runner_sweep.py` (the confirmation, READ), and the Linux build jobs run the same scripts.

## Findings, most severe first

1. **`_remove` does not retry as `remove.sh` does: each `rmtree` attempt stops at its first error** (`scripts/assemble_artifacts.py:62-72`). Medium, low reach.
   - Decision 5 says "retrying as `scripts/steps/remove.sh` does". `rm -rf` goes on past an entry it cannot remove, so its next attempt has little left. `shutil.rmtree` without `ignore_errors` raises at the first failure and leaves the rest of the tree, so each attempt starts nearly from scratch.
   - Failure, EXECUTED: against the same writer, `build.sh 90` (`remove`) succeeded 10 of 10, and step 90 alone (`_remove` on the old `build/artifacts`) 6 of 10, ending `cannot remove …/build/artifacts`. In isolation, 11 of 20 as built, 20 of 20 with `ignore_errors=True` per attempt.
   - Reach: under `build.sh`, `remove` has already removed both folders, so `_remove` sees absent paths (READ). It matters only when step 90 runs alone. It fails closed.
   - Two smaller differences from `remove.sh` in the same function (READ): the message has no `ERROR:`, so if it ever ran under `build.sh`, the step's line would show an empty reason (`build.sh` greps `ERROR|[Ee]rror`); and `rmtree` refuses a symlink, so a linked `build/artifacts` that `rm -rf` would remove makes step 90 alone fail.
   - Fix: in each attempt call `shutil.rmtree(path, ignore_errors=True)` (or unlink a link or a file first), then decide by `os.path.lexists`; raise `SystemExit(f"ERROR: cannot remove {path}")`. Correct Decision 5's sentence to match.

2. **The scan rule misses `rm -rf` in common command positions** (`tests/harness/scan.py:163`). Medium.
   - The rule exists so no future removal bypasses `remove`. It enumerates what may precede `rm`, and the list leaves out `if`, `while`, `until`, `elif`, `!`, a `case` arm's `)`, `command`, `exec`, `time`, `xargs`, a variable assignment, a path (`/bin/rm`), a backslash (`\rm`) and `-execdir`. A line continuation hides the flags.
   - Failure, EXECUTED: `if rm -rf "$x"; then :; fi` and `printf … | xargs -0 rm -rf` in a `scripts/steps/*.sh` file give no hit.
   - Fix: match `rm` as a word wherever it is, e.g. `(?<![\w./-])(?:\\|/(?:usr/)?bin/)?rm((?:\s+-[-A-Za-z]+)+)`, and join lines that end in `\` first. EXECUTED (`scan/scan_probe_fix.txt`): it catches every miss above but the continuation, the real `scripts/` tree still has no hit, and the extra false positives are strings and comments, which fail closed. Add `if`, `xargs` and `\rm` lines to the unit cases.

3. **Three behaviours of the removers are unchecked** (`tests/unit/test_build_scripts.py`). Medium.
   - M1: `remove` without `|| [ -L "$p" ]` passes every case. The dangling-link case uses an `rm` that works, so it never reaches the test the spec names. EXECUTED: that mutant exits 0 and leaves a link that `rm` could not remove.
   - M2: `remove` that handles only its first path passes every case. Steps call it with up to seven paths; a stale build folder left by such a `remove` would then be reused.
   - M3: a `_remove` that never raises passes; its `SystemExit` branch is never run.
   - Fix: a case with `rm` always failing on a dangling link (exit 1, `cannot remove`); a case with three paths and a working `rm` (all gone, 3 calls), and one where only the second path fails (exit 1, naming it); a `_remove` case with `shutil.rmtree` monkeypatched to raise `OSError` and leave the folder (`SystemExit`, the message names the path, 3 calls).

4. **Litter written between `drop_litter` and the listing is listed, and then passes the judge** (`scripts/assemble_artifacts.py:217-218`). Low.
   - READ: the listing is `p.is_file()` with no name filter. A `.DS_Store` that lands in `artifacts.new` after `drop_litter` and before `rglob` finishes is hashed into `SHA256SUMS`. `sums_errors` then passes, and a wheel copies it. Decision 5's "litter written after the listing is not in `SHA256SUMS`" is true, but this window is before the listing. The window is short and the folder is new, so it is unlikely; CI's same-bytes gate would still differ (INFERRED).
   - Fix: list `if p.is_file() and p.name not in OS_LITTER`. Then any litter left in the set is unlisted, and Decision 6's strict judge names it.

5. **Small inaccuracies.** Low.
   - README: "Every step removes its old outputs through `remove`": say "every shell step" (step 90 uses `_remove`, which retries too).
   - `test_remove_removes_a_dangling_link` skips on win32 with `needs: a POSIX sh`; the need there is symlinks. Name it.
   - The `sh` cases set `PATH=/usr/bin:/bin`. On a host whose `rm` is elsewhere (NixOS), the "fails once" cases fail rather than skip (INFERRED). Pass the parent's `PATH`; the shell function still shadows `rm`.
   - `test_a_zip_entry_is_never_litter` checks the artifact set from the unit suite, so it is outside the scoreboard's areas and the ratchet. That is fine as a guard; note it, or move it to `tests/checks/test_v1_1_artifact_set.py` in a later judge change.

## Constitution checks

- §4.1 (zero patches): holds. No source tree is touched. Litter in source trees is left, and the scripts skip it (EXECUTED: the littered run).
- §4.2 (pins): holds; no new input.
- §4.6 (the set is the product): holds. The set is byte for byte the main tree's except `MANIFEST`'s recipe lines, and litter in every input I tried changes nothing (EXECUTED). Finding 4 is a narrow window.
- §4.9 (tests count): holds. The checks count `rm` calls and names; nothing times anything.
- §4.10 (claims carry evidence): the landing notes' claims I re-ran all hold. Decision 5's "as `remove.sh` does" does not (finding 1).
- uv only, ruff clean on `src/` and `tests/` (EXECUTED).
- §7: nothing tripped. I committed nothing, passed no `--accept`, and wrote only this file outside the scratch folders.

## Disposition (filled in by the author, then confirmed by the reviewer)

All five findings are fixed in the clone, uncommitted on `6ee9bbf` (`git diff 6ee9bbf`). EXECUTED there: step 90 re-run, and the three binaries are still the main tree's byte for byte; `uv run pytest`: exit 0, v1.5 18/18, ratchet lost 0, grew 0; `tests/unit/test_build_scripts.py` and `test_scan.py`: 85 passed.

1. **Fixed as suggested.** `_remove` runs `rmtree(ignore_errors=True)` (or unlinks a link or a file) on each attempt, decides by `lexists`, and raises `SystemExit("ERROR: cannot remove …")`.
2. **Fixed as suggested.** `RM` is your pattern, matching `rm` as a word anywhere (with `\rm`, `/bin/rm`, `/usr/bin/rm`); lines ending in `\` are joined first, so the continuation is caught too. New unit cases: `if rm -rf`, `xargs -0 rm -rf`, `\rm`, `/bin/rm`, an assignment before `rm`, and a continued line. The real `scripts/` tree has no hit.
3. **Fixed.** One case each, and each is seen failing against its mutation (EXECUTED): M1 (no `[ -L ]`) fails `test_remove_removes_a_dangling_link_or_says_so`, which now also uses an `rm` that reports success but leaves the link; M2 (first path only) fails the new `test_remove_removes_every_path_it_is_given`; M3 (`_remove` never raises) fails `test_step_90_removes_or_says_why`, which now makes `rmtree` a no-op and expects the error.
4. **Fixed.** The listing filters `OS_LITTER` as well, so litter written after `drop_litter` is never hashed into `SHA256SUMS`, and the judge and wheel rule 3 see it as unlisted.
5. **Fixed.** The README says shell steps use `remove` and step 90 its own `_remove`; the dangling-link case names its own need on Windows; the `sh` cases use the caller's `PATH`; `test_a_zip_entry_is_never_litter` is removed (the walk case covers the zip's inputs, and a unit check should not read the artifact set outside the ratchet). Step 90 alone needing `SOURCE_DATE_EPOCH` predates this change and is left as is (`build.sh` sets it).

## Verdict

**Does not land yet.** The change does what it set out to do:
- every former `rm -rf` goes through `remove`, which beat a Finder-like writer 10 of 10 times where plain `rm -rf` lost 10 of 10;
- the set is byte for byte the reviewed one except `MANIFEST`'s fourteen recipe lines;
- litter in CPython's `Lib/`, numpy's and pandas' trees and pandas' `LICENSES/` changes no byte;
- the judge is green with nothing lost.

Three cheap things first: `_remove` should go on past errors in each attempt, as `rm -rf` does (finding 1); the scan rule should find `rm` wherever it stands (finding 2); and the checks should pin the dangling-link error, several paths, and `_remove`'s failure (finding 3). Findings 4 and 5 are a line each and best done in the same pass. Nothing found makes a wrong artifact; every gap fails closed.

One line: the shell removals and the litter filters are right and proven on a real build; the Python remover, the scan rule and three checks need one more pass.

## Confirmation

- **Date:** 2026-10-17
- **Reviewer:** the same fresh agent (Claude Opus 5.5); not the author.
- **Reviewed:** the fixes staged in the clone on `6ee9bbf` (`git diff --cached 6ee9bbf`): `scripts/assemble_artifacts.py`, `tests/harness/scan.py`, `tests/unit/test_build_scripts.py`, `tests/unit/test_scan.py`, `README.md`; and the Disposition above. The working tree equals the index (`git status`: five `M ` lines, nothing unstaged).
- **Ran (EXECUTED, darwin-arm64).** Probes and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev018b/confirm/` (`mut/` with `mutations.txt`, `scan_probe.txt`, `links_probe.py` and `.txt`, `race-step90.txt`, `pytest-full.txt`, `set1/`). I edited nothing in the clone or the main tree, except appending this section; I committed nothing and passed no `--accept`. The litter I planted is removed again (0 litter files under `build/`), and the clone's set ends byte for byte as the author left it (`set1`, 17 of 17).

### Each finding against its fix

1. **`_remove` — closed.** Each attempt unlinks a link or a file, else runs `rmtree(path, ignore_errors=True)`, then decides by `lexists`; the message is `ERROR: cannot remove …` (READ).
   - Against the same writer as before, step 90 alone now succeeds **10 of 10** (it was 6 of 10), and the set is unchanged after the runs (EXECUTED, `race-step90.txt`).
   - A link to a folder and a dangling link are removed with the target kept, and a file is removed (EXECUTED, `links_probe.txt`).
   - Residual, Low: no check pins "goes on past an error". A copy with the old body (`rmtree` without `ignore_errors`, catching `OSError`; `M3b_old_remove`) passes all 85 cases. A case could make a fake `rmtree` remove nothing unless given `ignore_errors=True`. Optional.
2. **The scan rule — closed.** `RM` is the wider pattern, and lines ending in `\` are joined first (READ). EXECUTED (`scan_probe.txt`): every miss from my first probe is now a hit, the continued line included. The only misses left are outside the spec's rule (`rm -r` with no `-f`, `rmdir`, `find -delete`) and `rm -r "$x" -f`, which BSD `rm` reads as a file named `-f`.
   - The real tree: 18 shell files under `scripts/`, **0 hits**. `8a2be32`'s scripts: still the 12 hits.
   - New false positives, all failing closed: a continued `echo a \` followed by `rm -rf x`, and a comment line inside a continuation. Strings and trailing comments still match, as the code comment says.
   - The six new unit cases are the probe's lines.
3. **The checks — closed.** EXECUTED (`mut/mutations.txt`), each mutation in a copy of the index:

   | mutation | result |
   |---|---|
   | M1 `remove` without `[ -L ]` | caught: `test_remove_removes_a_dangling_link_or_says_so` |
   | M2 `remove` handles only `$1` | caught: `test_remove_removes_every_path_it_is_given` |
   | M3 `_remove` never raises | caught: `test_step_90_removes_or_says_why` |
   | (unmutated copy) | 85 passed |

   The dangling-link case now uses an `rm` that reports success but leaves the link. That is the one way to reach the `[ -L ]` test, and it expects exit 1, one call and `cannot remove`.
4. **The listing — closed.** The listing filters `OS_LITTER` (READ). Residual: it sits inside `main()`, so no unit case covers it; a copy without the filter (`M4_no_listing_filter`) passes. That is acceptable for one condition; a small `listed(folder)` helper with a case would close it. Optional.
5. **Small inaccuracies — closed.** README: "Every shell step … through `remove`, and step 90 through its own `_remove`; both retry." That is accurate. The win32 skip names its own need. The `sh` cases use the caller's `PATH`. `test_a_zip_entry_is_never_litter` is removed, with a stated reason; the zip walk case still covers the zip's inputs. Running step 90 alone without `SOURCE_DATE_EPOCH` is answered: it predates this change.

### Nothing new broke

- **The set (EXECUTED).** The author's rebuilt `build/artifacts` (12:12) against the main tree: the binaries, the zip and the 12 licences are byte for byte the same. `MANIFEST` differs only in `recipe` lines (0 other differing lines), and every `recipe` hash equals the staged file (`git show :<path>`). `SHA256SUMS` differs only in `MANIFEST`'s line.
- **Litter (EXECUTED).** The same 14 planted files, then `sh scripts/build.sh 70 80 90`: three `ok`, all 17 files byte for byte `set1`.
- **The judge (EXECUTED).** `uv run pytest -p no:cacheprovider` → `162/166 pass · 0 gap · 4 blocked · 0 fail (unit suite 366/371, 5 skipped)`; v1.5 `18/18`; `528 passed, 9 skipped`; ratchet vs `408819a846`: `lost 0 · absent 0 · unrun 0 · unrun locally 2 · gained 0 · grew 0 · judge changed: tests/harness/scan.py, tests/unit/test_build_scripts.py, tests/unit/test_scan.py`; exit 0. Ruff check and format are clean on `src/` and `tests/`.

### Still open

- **The specification does not describe what is now built.** It is not in the staged change (READ):
  - Decision 5 still says each `rmtree` attempt "catch[es] `OSError`", and that the message is `SystemExit("cannot remove <path>")`.
  - The Design's check list does not name the new cases or the removed zip check.
  - The landing notes still give the judge as unit 360/365 and 522 passed (now 366/371 and 528). They do not say the build was revised against this review.

  Fix: one pass over Decision 5, the check list and the landing notes, citing this review. Text only; no re-run needed.

### Verdict of the confirmation

**Lands once the specification's text is brought up to date.** That means Decision 5, the check list and the landing notes, as above. Every finding is closed in the code, and each of the three mutations now fails. The scan rule finds no hit in the real tree. The set is the reviewed one apart from `MANIFEST`'s recipe lines. The judge is green with nothing lost. The two optional check additions (findings 1 and 4) need not block.

One line: the code is right and checked; only the specification's words lag behind it.

## Disposition of the confirmation (filled in by the author)

- **The specification's text:** updated. Decision 5 now describes `_remove` as built (unlink or `rmtree(ignore_errors=True)` per attempt, `ERROR: cannot remove`) and the listing filter (`listed_files`); the Design's check list names the new cases and the removed zip check; the landing notes gain "Revised against the build review" with the new counts.
- **Optional gap 2 (the listing filter):** closed. The filter is `listed_files(folder)`, called by `main()`, and `test_step_90_never_lists_litter` checks it (11 passed).
- **Optional gap 1 (`_remove` going on past an error):** left, and named in the landing notes; your Finder-like writer run is its evidence.

Your verdict made the change land once the text was updated.
