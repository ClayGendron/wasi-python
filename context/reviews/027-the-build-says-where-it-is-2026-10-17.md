# Review of 027 — The build says where it is (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change. I did not write the
  specification's pre-build review or its confirmation. I read `AGENTS.md`, the constitution
  (§4.2, §4.6, §4.8, §4.9, §4.10), the 021 build review (for the format), specification 027 with
  its landing notes, its pre-build review with the confirmation and conditions A to E,
  `.github/workflows/release.yml`, `tests/harness/scan.py` (the fetch, url, download-script,
  bare-rm and clock rules), `release/version.py`, and the diff. I did not rely on the landing
  notes. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `git show dd79241` (one commit, seven files): `scripts/steps/progress.sh` (new),
  `scripts/build.sh`, `scripts/00_download.sh`, `tests/unit/test_build_progress.py` (new, 75
  checks), `README.md`, `CHANGELOG.md`, and the specification's landing notes.
- **Ran (EXECUTED, darwin-arm64, 10 cores).** Everything is under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev027b/`.
  - Three scratch clones of `dd79241`: `clone/` (the real builds; the main tree's `downloads/`
    hard-linked in, `SHA256SUMS` equal by `cmp`), `t/` (repeat runs and mutants), `u/` (the
    shells: `SHELLS` made overridable by an environment variable in that copy of the check).
  - The check file, 75 checks: once in the main tree; 20 times as four parallel loops while the
    real build ran (`runs/summary-[e-h].txt`); 12 times as four parallel loops beside twelve
    `yes` busy loops (`runs/summary-[i-l].txt`); 40 more times the two Ctrl-C checks alone;
    and with the driver's shells set to `/bin/sh`+`/bin/bash`, `/bin/bash`+`/bin/dash`,
    `/bin/dash`+`/bin/sh`, and `zsh --emulate sh` (`tools/zsh-sh`).
  - 30 mutants through `tools/mutants.py`, each applied to `t/`, run, and restored
    (`mut-results.txt`, `mut/`, `mut2/`). `t/` was clean afterwards (`git status`).
  - The real build in `clone/`: `sh scripts/build.sh` piped to a file (`plain1.log`); a second
    full build on a 100-column pty (`tools/ptyrun.py`, `pty1.raw`); Ctrl-C at
    `20_cpython 10s` on an 80-column pty (`pty2.raw`); `--list`, `--check`, `--help`, a bad
    option, `--list 40`; `--resume` piped (`resume.log`); `--from 80` on a 60-column pty
    (`pty3.raw`). `tools/replay.py` replays each pty with the check's own `screen()`.
  - Probes on fake trees (`tools/probe.py`, the check's own `Tree`): TERM during the last step,
    HUP mid-step, SIGKILL to `build.sh` alone, OSC and other escapes in logs, 1 to 10 columns,
    `TERM=dumb`, `CI=`, `BUILD_PROGRESS=plain`, `COLUMNS=0`, a damaged `timings.tsv`.
  - `uv run pytest -p no:cacheprovider -q` in the main tree (`judge-main.txt`) and in `clone/`
    with its own new set (`judge-clone.txt`); `uv run ruff check src tests` and
    `uv run ruff format --check src tests`.
  - In the main tree I wrote only this file. I did not run `scripts/build.sh` there. The judge
    runs (and my first check run) overwrote `build/progress/latest.json`; I restored it from a
    copy each time, byte for byte (sha256 `7530f697…` before and after). No commit, stage,
    push, checkout, restore or stash. I never passed `--accept`.
  - One slip: one command in a compound line ran a bare `python3` with an empty here-document
    (it did nothing; the edit it was meant to make was then made with `perl` in `u/`).

## The real build

- **Plain output (EXECUTED, `plain1.log`).** Exit 0 in 5m39s. The preflight line, eleven `ok`
  lines with durations, `done: 11 steps in 5m39s; the artifact set is in build/artifacts/`, the
  three artifacts with sizes and hash prefixes, and `next: uv run pytest -m "not slow"`. It reads
  well: one glance says what ran, how long, and what came out.
- **Same bytes (EXECUTED).** Against the main tree's `build/artifacts/SHA256SUMS`, 15 of 16 lines
  are equal: the three artifacts and every licence. `MANIFEST` differs only in three `recipe`
  lines: `scripts/00_download.sh`, `scripts/build.sh` (new hashes) and
  `scripts/steps/progress.sh` (new). The pty build and the `--resume` and `--from 80` rebuilds
  gave the same three artifact hashes.
- **Terminal output (EXECUTED, `pty1.raw`).** 1712 frames, the widest 56 of 100 columns. With the
  times masked, the final screen equals the plain output line for line (19 lines). The raw bytes
  hold only `ESC[K`, `ESC[32m` and `ESC[0m`; no cursor movement. Frames read naturally:
  `⠸ [7/11] 50_pandas 56s / ~47s · [95/154] · ~30s left`. When a step overruns its estimate the
  time left stops falling (the running step counts as 0 left), as Decision 6 says.
- **Ctrl-C (EXECUTED, `pty2.raw`).** Sent 10 s into CPython: exit 130,
  `INTERRUPTED 20_cpython (log: build/logs/20_cpython.log)` as the last line, no process of the
  clone's build left (`ps`), and the row `20_cpython interrupted 10`. `--resume` then ran 20 to 90
  (`done: 9 steps in 6m20s`), exit 0.
- **Options (EXECUTED).** `--list` prints each step, its header's first line and newest time;
  `--check` prints the one preflight line; `--help` and a bad option print the usage, the latter
  with `ERROR build: no option --frm` and exit 2. `--from 80` on a 60-column pty runs two steps.

## The checks

- **Stable in a normal environment (EXECUTED).** 75 passed in every run: 20 runs in parallel with
  a real build, 12 under twelve busy loops, 80 executions of the Ctrl-C pair alone, and under
  each shell pairing above (zsh-as-sh: 69 passed, 6 skipped, as only one shell was named). Two
  ways it can still fail are finding 3.
- **Mutants (EXECUTED, `mut-results.txt`).** Caught: EXIT trap removed; reason grep back to
  today's; `exec 3>&1` in `build.sh`; `export P_MODE`; `shasum` piped through `tee`; no width
  cut; no signal check before a step; `--resume` treating `interrupted` as finished; `--resume`
  reading the oldest row; no `interrupted` row between steps; no `interrupted` row during a step;
  the ten-times rule removed; the step's stdin from `/dev/null`; an extra argv word; no erase in
  `progress_stop`; the cleaner keeping CSI; no `%25`; no 120-character cut; colour in plain
  mode; the space check removed, or made unconditional; the `curl` check removed.
  Survived: the ticker without `kill -0` (finding 2); log text, or a raw log line, appended to
  the status line (finding 1); the newest-`ok` estimate made the oldest, and the
  `INTERRUPTED after` line removed (finding 5); no erase in `progress_line` (as the landing notes
  say; the other erase covers it, INFERRED); the ticker under `set -e`, and the ticker keeping
  the HUP trap (INFERRED equivalent: no ticker command fails on a pty, and a subshell resets
  traps anyway).

## What the renderer could touch

- **The step's environment, stdin and argv (READ, EXECUTED).** `build.sh` exports only the four
  variables it exported before. The ticker is a background job with its own fd 3; no `P_*`
  variable is exported. Criterion 3's check records `env | sort`, `[ -t 0 ]`, argv and
  `ls /dev/fd`, and catches each of the four mutants aimed at it. INFERRED, not a finding: a
  variable the caller already exported (say `n` or `log`) would be changed by the driver's
  assignment, as `step` and `log` already were before this change.
- **The artifacts (EXECUTED).** Unchanged, above. `timings.tsv` and the new
  `build/downloads-verified.txt` are under `build/`, and no step reads them (READ: `grep` of
  `scripts/` and `recipes/`).
- **Escapes from logs (EXECUTED).** The tail and the `ok` summary drop CSI sequences and every
  byte outside printable ASCII and tab. An OSC title or hyperlink in a log loses its ESC and BEL,
  so nothing reaches the terminal, but its payload shows as text (`]0;TITLE`). No step writes
  such sequences today (their stdout is a file). The status line is guarded by the code alone
  (finding 1).
- **Exit paths (EXECUTED).** Success, a failing step, a failing renderer command (the check),
  Ctrl-C, TERM and HUP to `build.sh` alone (exit 143, 129), and TERM during the last step
  (`INTERRUPTED after 90_artifacts: every step had finished`, exit 143) all erase the status
  line and leave no process. SIGKILL to `build.sh` alone leaves its last frame on the screen, as
  it must; the ticker then exits by its `kill -0` check and the group empties.
- **Narrow and odd terminals (EXECUTED).** 1 to 3 columns draw nothing; 4 columns draw `| [`;
  every frame is at most width − 1. `TERM=dumb`, `CI=` (set but empty), `BUILD_PROGRESS=plain`
  give plain output on a pty; `COLUMNS=0` falls back to the pty's size.
- **The release workflow (READ).** It runs `scripts/00_download.sh` and `scripts/build.sh` and
  greps neither's output; its only grep is on a pytest summary. On Actions `CI` is set, so the
  output is plain, and `GITHUB_ACTIONS` adds the `::error` line before the one `ERROR` line.
- **The scan rules (EXECUTED: the rules goal 19/19 in the main tree).** `curl` appears only in
  `00_download.sh` (the fetch rule's exemption) and in comments; every `get <url> <name>` line
  and the `shasum -a 256 … -c SHA256SUMS` line stay; nothing writes `SHA256SUMS`; no bare
  recursive `rm`; the new check reads no clock (it counts readings of a fake `BUILD_CLOCK`; its
  `select` timeout is a hang guard).

## The implementer's three flags

- **Criterion 8's "same `SHA256SUMS`".** Agreed. EXECUTED as above: every line but `MANIFEST`'s
  is equal, and `MANIFEST` differs only in the recipe hashes of the changed scripts, as for specs
  018 and 020. The criterion means the artifacts; the landing notes say so. No change needed.
- **A signal during the last step.** The reading is sound: every step finished, the record shows
  them all `ok`, `--resume` says `nothing to resume`, and the exit code still says a signal came.
  It has no check (finding 5).
- **`0.1.0a4 — unreleased` in the CHANGELOG.** A real snag (finding 4).

## Acceptance criteria against evidence

1. *Frames, then equality.* **Met** (EXECUTED). The check covers the five factors pairwise in
   eight runs rather than all 32 combinations; every value appears with every other factor's
   values, which I take as meeting the criterion. The real build's screen also equals its plain
   output.
2. *Every exit path.* **Met** (EXECUTED), with two gaps in the checks (findings 2 and 3).
3. *The step sees nothing of the renderer.* **Met** (EXECUTED; four mutants caught).
4. *The failure block.* **Met** (EXECUTED; three mutants caught).
5. *Tables.* **Met** (EXECUTED).
6. *Options and preflight.* **Met** (EXECUTED, on fakes and on the real build).
7. *The download step.* **Met** (EXECUTED; the piped-`shasum` and no-`curl` mutants caught).
8. *The real build.* **Met**, with `MANIFEST`'s line as above (EXECUTED).
9. *Green with `--accept-judge`; a release dry run.* **Not yet.** EXECUTED in the main tree:
   732 passed, 1 failed, 4 skipped; lost 1, grew 0; the judge changed
   (`tests/unit/test_build_progress.py`). The one failure is
   `test_manifest_recipes_match_the_tree`, as expected: the main tree's set names the old
   scripts. Nothing else fails. In `clone/`, whose set was built from `dd79241`: 726 passed,
   11 skipped, 0 failed; lost 0, grew 0 (four checks blocked by that clone's environment:
   oracle, prior-art clones, three systems, wheel). So rebuilding the main tree's set gives the
   pass back. `ruff check` and `ruff format --check` are clean. The dry run needs the push.

## Findings, most severe first

1. **Medium. Nothing checks that the status line holds only the driver's words.** (Decision 3,
   "No log text reaches the status line"; `progress_ticker`)
   - The defect. The code is right (READ): the ticker reads the log only through a digits-only
     `[n/N]` parse and a filtered `.part` name. But no check would fail if that changed.
   - Failure. EXECUTED: a mutant that appends the log's last line to every frame, and one that
     appends the log's second line raw, both pass all 75 checks. This is the one place untrusted
     bytes from building downloaded sources could reach the terminal live; the permanent lines
     have checks for it, the status line has none. The pre-build review's finding 15 rested on
     this property.
   - Fix. In the frame checks, give the held step a log line with a marker and an escape before
     the frame is awaited (for example `printf 'LOGTEXT \033[31mred\n'` in `before`), and assert
     that no frame contains `LOGTEXT`, `red` or ESC; and, for the 80-column runs, that every frame
     fully matches the frame grammar (spinner, `[k/N] step time`, then the optional ` / ~t`,
     `[n/N]`, `fetching name size` and `~t left` parts).

2. **Low. The ticker's `kill -0` exit is unchecked.** (Decision 2, "checks `kill -0` before every
   frame, and exits on its own when the build is gone")
   - Failure. EXECUTED: the mutant `while :; do` passes all 75 checks, because every tested exit
     runs the EXIT trap, which kills the ticker first. The probe shows the rule works today:
     after SIGKILL to `build.sh` alone the group empties.
   - Fix. One check: SIGKILL `build.sh` alone during a held step, then release the step, and
     assert the pty reaches end of file within the read bound (a ticker drawing for ever would
     exceed `READS`).

3. **Low. The Ctrl-C check fails for two reasons that are not the build's.**
   (`test_ctrl_c_interrupts_the_step_and_leaves_nothing`)
   - a. EXECUTED: run from a background job of a non-interactive shell (`cmd &`), it failed in
     40 of 40 runs (`assert 0 == 130`). Such a job starts with SIGINT ignored; the child keeps
     it ignored, the shell cannot trap it, and Ctrl-C does nothing. With SIGINT reset to default
     before pytest, the same loops passed 40 of 40. An agent that runs the judge with `&` would
     see a false lost pass.
   - b. EXECUTED once in about 220 executions, under load: the last line was
     `INTERRUPTED 50_pandas` instead of `INTERRUPTED 40_numpy`. INFERRED cause: the held step
     polls with `sleep 0.05`; when that `sleep` exits normally at the instant SIGINT arrives,
     `/bin/sh` (bash) assumes the child handled the signal and goes on. The step then runs out
     its polls, exits 0, and the driver correctly stops before 50 (Decision 2).
   - Fix. In `_controlling_tty`, reset SIGINT, SIGTERM, SIGHUP and SIGQUIT to `SIG_DFL` before
     the `exec` (this also covers the other pty checks). Hold the Ctrl-C check's step with one
     long command (`sleep 30`, bounded by the read guard) instead of a poll loop.

4. **Low. The CHANGELOG section blocks the release tool.** (`CHANGELOG.md`, spec 004's flow)
   - Failure. EXECUTED in `u/`: `uv run python release/version.py bump` prints
     `ERROR: CHANGELOG.md already has a section for 0.1.0a4` and exits 1, while
     `release/version.py check` still says `ok 0.1.0a3`. The project's flow makes the section with
     `bump` and then fills it (0.1.0a3's section was made that way, READ: `39a2c84^`).
   - Fix. In the fix commit, remove the heading, run `uv run python release/version.py bump`
     (0.1.0a3 to 0.1.0a4, the next release `c4a8a00` already names), and put the four entries
     under the section it makes. Or answer in writing that the owner bumps by hand.

5. **Low. Two of the author's choices have no check.**
   - EXECUTED: removing the `INTERRUPTED after <step>` line passes all 75 checks; so does taking
     the oldest `ok` row as a step's estimate instead of the newest (Decision 6). The first
     mutant's single failure was finding 3b, and a rerun survived.
   - Fix. Two small checks: TERM during the held last step gives `ok 90_artifacts`, then
     `INTERRUPTED after 90_artifacts: every step had finished`, exit 143 and no summary; and
     `--list` with two `ok` rows for one step shows the newer time.

6. **Low. Four things a person reads are unclear.** (EXECUTED on the real build and the probes)
   - a. `downloads: 29 pins, 0 fetched, 30 verified`: more verified than pins. The research zip
     is present and verified, but `research` does not count as a pin without `--all`. Count
     each file `shasum` verifies as a pin, or name the extra (`30 verified, 1 a research input`).
   - b. After a signal between steps, `INTERRUPTED 50_pandas (log: build/logs/50_pandas.log)`
     points at a log this run never wrote: it is a previous run's, or absent. Say
     `INTERRUPTED before 50_pandas` with no log (the TERM check's expected line changes too).
   - c. `--list` shows only the first line of each header, so most descriptions stop
     mid-sentence (`… run under the`, `… with numpy's vendored`, `… as static`), and ten of the
     eleven repeat `Step NN:` beside the step's name while step 00 does not. Strip the
     `Step NN: ` prefix and print up to the first full stop, or keep a one-line summary per step.
   - d. Nit: `--list 40` ignores `40`, and `--check --list` runs only the last action. Refusing
     both with exit 2, like the other combinations, would match the usage.

7. **For the record (no change asked).** A run killed with SIGKILL, by the kernel or by power
   loss writes no row for its running step, so `--resume` says `nothing to resume`
   (EXECUTED: the last row was `35_stdlib_libs ok`). That is Decision 7's rule as written; a
   later specification could write a row when a step starts.

## Constitution checks

- §4.2: `curl` runs only in the download step, for a pin not yet present; the `get` lines and the
  `shasum -c` line are unchanged in substance; a mismatch still fails (EXECUTED: the check and
  the piped-`shasum` mutant).
- §4.6: the artifact set is unchanged byte for byte; `MANIFEST` records the scripts' new hashes
  (EXECUTED).
- §4.8: the driver runs nothing new from `downloads/`; it reads only file names and sizes of
  `.part` files (READ).
- §4.9: no check reads a clock (EXECUTED: the rules goal); durations come from a counting
  `BUILD_CLOCK`, and the `select` timeout only stops a hang (READ).
- §4.10: the landing notes label their claims, and what I re-ran matches them (EXECUTED).
- `AGENTS.md` rules: uv only (the driver stays POSIX sh, as Decision 1 says); a failure is one
  `^ERROR` line with its reason (EXECUTED); logs go to `build/logs/`.
- §7: nothing tripped. No source tree changed; no artifact in git.

## Disposition (filled in by the author, then confirmed by the reviewer)

By the implementer, 2026-10-17. The evidence is EXECUTED unless labelled. Its outputs are under
`/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/build027/`.
The lab is `lab2/`, a clone of `20dfcb6` holding the committed `dd79241`. The full numbers are in
the specification's landing notes.

1. **Fixed.** The held step's log now carries `LOGTEXT ESC[31mred` before and after the ninja
   line, and the `.part` step's log carries it too. No frame may contain `LOGTEXT`, `red` or ESC.
   At 80 columns every frame must fully match the status grammar (`GRAMMAR` in the check). The
   frame parser now keeps an ESC inside a frame, so a raw line is seen, not skipped. Both of your
   mutants fail 9 checks each in `lab2/`: the log's last line appended (cleaned), and its first
   line appended raw.
2. **Fixed.** `test_the_ticker_ends_itself_when_the_build_is_gone`. A first version, with
   `build.sh` as the pty's session leader, passed even with `while :`. The leader's death hangs
   up the terminal: SIGHUP goes to the group, and macOS also revokes the tty. So a small leader
   now starts `build.sh`, reaps it after the SIGKILL, and stays two seconds. The check allows at
   most one frame after the kill. The `while :` mutant fails it: "the ticker drew 7 frames after
   the build was gone". The fixed ticker passed in every run.
3. **Fixed.**
   - a. `_controlling_tty` resets SIGINT, SIGTERM, SIGHUP and SIGQUIT to `SIG_DFL` before the
     exec. With SIGINT ignored in the parent (`sh -c "trap '' INT; uv run pytest …"`), the
     committed check failed 2 of 2 (`assert 0 == 130`). The new one passed 60 of 60.
   - b. The Ctrl-C check's step is now one `sleep 30`, not a `sleep 0.05` poll loop. The read
     bound and the guard still stop it. 60 of 60 runs passed plain, 60 of 60 under twelve busy
     loops, and 30 of 30 under load with SIGINT ignored. That is 420 executions of the pair with
     no failure. INFERRED: no short `sleep` is left to end on its own just as SIGINT arrives.
4. **Answered:** the lane bumps the version with `release/version.py` at landing.
5. **Fixed.** `test_term_during_the_last_step_ends_without_a_summary` expects `ok 90_artifacts`,
   then `INTERRUPTED after 90_artifacts: every step had finished`, exit 143, no `done:` line, and
   the last row `ok`. `test_list_shows_the_newest_ok_time` uses rows `ok 5`, `ok 99`, `error 500`
   and expects `[1m39s]`. In `lab2/` the oldest-row mutant and the removed line each fail one
   check.
6. **Fixed.**
   - a. `verified` counts this run's pins only. Any other file that verifies is named apart:
     `downloads: 29 pins, 0 fetched, 29 verified; 1 other file in downloads/ verified too`. A new
     check uses such a file. `shasum`'s output is still saved and never piped (condition D).
   - b. A signal between steps prints `INTERRUPTED before <step>` with no log path, and still
     writes the `interrupted 0` row. The EXIT trap's fallback names a step's log only once that
     step has started (`P_STEP` is set just before the step runs).
   - c. `--list` shows the first sentence of the header without `Step NN: `. When it does not
     fit 80 columns it is cut at a word and ends `...`. A check runs `--list` over copies of the
     real step scripts: each line fits 80 columns, and each cut ends at a word of the real first
     sentence.
   - d. `--list`, `--check` and `--help` go alone. `--list 40`, `--check --list` and
     `--help --from 60` exit 2 with the usage; each has a check.
7. **Noted;** no change, as asked. A later specification may write a row when a step starts.

The three wording changes (6a, 6b, 6c) amend Decisions 9, 2 and 7 as written. The landing notes
say so.

## Verdict

**Lands once findings 1 and 3 are fixed**; 2, 4, 5 and 6 are small and can go in the same pass.
The build does what the specification says: the artifacts are unchanged, the plain output keeps
today's prefixes, the terminal ends showing exactly the plain lines, every exit path I tried
erases the line and leaves nothing running, and the failure block names the step's own `ERROR`
line. Twenty-two of thirty mutants are caught. The gaps are in the checks, not the code:
the status line's one safety rule is unguarded, and the Ctrl-C check can go red for reasons that
are not the build's. Criterion 9 waits for the main tree's rebuild, the owner's `--accept-judge`
and a release dry run.

One line: the build is right and pleasant to watch; guard the status line against log text, make
the Ctrl-C check immune to an ignored SIGINT and the bash race, then rebuild, accept and land.

## Confirmation

- **Date:** 2026-10-17
- **Reviewer:** the same fresh agent (Claude Opus 5.5); not the author.
- **Reviewed:** the main tree's uncommitted fixes over `dd79241` (`scripts/build.sh`,
  `scripts/steps/progress.sh`, `scripts/00_download.sh`, `tests/unit/test_build_progress.py`,
  the specification's revision section), and the Disposition above.
- **Ran (EXECUTED, darwin-arm64).** Outputs are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev027b/`.
  Two scratch clones of `a5c7098` with the four changed files copied in, equal to the main tree's
  by `cmp`: `v/` (mutants, `mut3-results.txt`) and `w/` (repeat runs, `runs2/`). The fixed scripts
  were also copied into `clone/`, which holds a full real build, for `--list`, step 00 and the
  option refusals. I wrote nothing in the repository but this section. No commit, stage, push,
  checkout, restore or stash. I did not run `scripts/build.sh` in the main tree.

### Each disposition against its finding

1. **Closed.** All 30 mutants from the review were re-run on the fixed tree. Both mutants that put
   log text in the status line now fail 5 frame checks each: the last line cleaned, and a raw
   line. READ: the held step's log carries `LOGTEXT ESC[31mred`, and 80-column frames must match
   `GRAMMAR` in full.
2. **Closed.** The ticker without `kill -0` now fails
   `test_the_ticker_ends_itself_when_the_build_is_gone`.
3. **Closed.** The four loops ran with SIGINT ignored in the parent; a probe confirmed the
   inherited `IGNORE`. They gave 83 passed in 20 of 20 runs. With twelve `yes` busy loops beside
   them, 12 of 12. That is 64 executions of the Ctrl-C pair with no failure. Before the fix, the
   same setup failed 40 of 40. READ: `_controlling_tty` resets the four signals, and the Ctrl-C
   step is one `sleep 30`.
4. **Answered,** and I accept it. The lane runs `release/version.py bump` when it lands. Until
   then `bump` refuses, as shown above. Whoever lands this must remove the hand-made heading
   first, or bump by hand.
5. **Closed.** The oldest-`ok` mutant fails `test_list_shows_the_newest_ok_time`. Removing the
   `INTERRUPTED after` line fails `test_term_during_the_last_step_ends_without_a_summary`.
6. **Closed.**
   - a. The real step 00 prints `downloads: 29 pins, 0 fetched, 29 verified; 1 other file in
     downloads/ verified too`.
   - b. READ: `INTERRUPTED before <step>`, with the `interrupted 0` row kept. The TERM checks
     expect it.
   - c. The real `--list` fits 80 columns, without `Step NN:`, cut at a word with `...`. Most
     lines are still cut, but none reads as a broken sentence any more.
   - d. `--list 40`, `--check --list` and `--help --from 60` exit 2 with one `ERROR build:` line.
     `--plain --check` still works.
7. **Noted;** nothing asked.

Mutants: 27 of 30 are caught now (22 before). The three left are the ones the review judged
equivalent or covered: the ticker under `set -e`, the ticker keeping the HUP trap, and no erase
in `progress_line`. Under the other shells: `/bin/sh` with bash gave 83 passed, bash with dash 83
passed, and `zsh --emulate sh` 77 passed with 6 skipped (one shell named).

### The judge

The full judge ran once in the main tree with `-p no:cacheprovider -q`: 740 passed, 1 failed, 4
skipped. v1 is 187/190 and the unit suite 553/555. The ratchet: lost 1, grew 0, judge changed.
The one failure is `test_manifest_recipes_match_the_tree`, as expected until step 90 is re-run.
Nothing else fails. `ruff check` and `ruff format --check` on `src` and `tests` are clean.
`build/progress/latest.json` was restored byte for byte (`7530f697…` before and after). Other
work is now uncommitted in the tree too (`src/wasi_python/__init__.py` and new files); the run
included it, and nothing of it failed.

### New gaps (nits; none blocks landing)

- The revision section amends Decisions 2, 7 and 9, but their own text still reads the old way:
  `INTERRUPTED <step> (log: …)`, "the first line of its script's header comment", and "`v` the
  `OK` lines". One clause in each decision ("as revised below") would stop a reader of the
  decision alone from being misled.
- A Ctrl-C that lands during the estimate loop, before `P_STEP` is set, ends with
  `INTERRUPTED build` and no row (INFERRED from the code). That is rare, and `--resume` then says
  `nothing to resume`, the same case as review finding 7.

### Verdict

**Lands,** after the main tree's set is rebuilt from step 90 on the committed scripts, which
gives `test_manifest_recipes_match_the_tree` back. Then come the owner's `--accept-judge`, and
finding 4's bump or heading removal at landing. Every finding is fixed or answered. The
mutants that survived before are now caught, and the Ctrl-C check holds with SIGINT ignored and
under load.

One line: the fixes close all six findings with checks that bite; rebuild step 90, accept, and
land.
