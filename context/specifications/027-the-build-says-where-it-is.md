# 027 — The build says where it is

- **Status:** drafted 2026-10-17; revised against its pre-build review (`../reviews/027-the-build-says-where-it-is-spec-2026-10-17.md`), whose confirmation passed it for build with five conditions (A to E), now written in. Built 2026-10-17; build-reviewed (`../reviews/027-the-build-says-where-it-is-2026-10-17.md`, verdict: lands once findings 1 and 3 are fixed); revised against it the same day and confirmed by the reviewer. Landed 2026-10-17 (accepted on `1c8a4bb`; dry run 39084581927).
- **Owner:** Clay Gendron
- **Kind:** the build driver (`scripts/build.sh`, a new `scripts/steps/progress.sh`, `scripts/00_download.sh`'s per-pin lines), unit checks in `tests/unit/`, `README.md` (its "one line each" for the build), `CHANGELOG.md`; spec 003 Decision 1 is amended (below). No step's work changes; no artifact changes.
- **Depends on:** 003 (the build, its Decision 1 amended here), 018 (`remove`), both landed.
- **Research it stands on:** `../research/2026-10-17-delightful-build-progress.md` (uv, cargo, ninja, BuildKit and Homebrew studied; the prototype under its folder; its "What it decides" is this specification's base). The owner asked for it on 2026-10-17: "Can we improve this experience with a progress bar and some other DX features?"

## The problem

`scripts/build.sh` prints one line per finished step. A build takes about 5m46s, and step 20 (CPython) is 3m02s of silence. A failure prints one line found by `grep '[Ee]rror'`, which already matches a harmless `Checking for strerror... Yes.` in today's zlib log (memo §1), so it can name the wrong reason. There is no total, no duration, no summary of what was made, and no way to list or resume steps but by retyping their numbers.

## Decisions

1. **The driver stays POSIX sh; no new dependency.** `build.sh` sources a function library, `scripts/steps/progress.sh`. Python is not used: the pinned host Python exists only after step 10, `uv run` would change the steps' environment, and spec 003 forbids it in the download step (memo §4.1).

2. **Running a step: one way, and every exit path.**
   - Every step runs in the foreground, exactly as today (`sh step > build/logs/<step>.log 2>&1`), with the same environment, stdin and argv in every mode.
   - **Signals.** `build.sh` traps INT, TERM and HUP: the trap records the signal; when the running step returns, its own line is printed from its own status (`ok …` if it finished, else `INTERRUPTED <step> (log: …)`), and the build exits 130, 143 or 129. Ctrl-C reaches the whole process group, so the step stops at once (EXECUTED by the review under dash, bash and zsh-as-sh: exit 130, nothing left running). A TERM or HUP sent to `build.sh` alone waits for the running step to end, because a shell runs a trap only after its foreground child returns; the README says to signal the process group (`kill -TERM -<pgid>`) to stop at once. The loop also checks the recorded signal before it starts each step, so a signal that arrives between steps stops the build before the next one with `INTERRUPTED before <step>` (no log path: that step never started), and that step is written to `timings.tsv` as `interrupted` for `--resume` (condition C; worded so by the build review).
   - **The ticker** (the background redraw, terminal mode only) runs with `set +e`, draws one whole frame per write, checks `kill -0 "$BUILD_PID"` before every frame, and exits on its own when the build is gone or a write fails. An EXIT trap in `build.sh` stops it and erases the status line on every exit: success, a failing step, a `set -e` failure in the renderer, and each signal.

3. **Two ways to show it.**
   - **Plain** (stdout not a terminal, `TERM` unset or `dumb`, `CI` set, `--plain`, or `BUILD_PROGRESS=plain`): the permanent lines only, which keep today's prefixes, so existing greps hold: `ok <step>: <summary> [<duration>]`, the summary cut to 120 characters as today.
   - **Terminal**: the same permanent lines, and **one live status line** below them, redrawn in place with `\r` and `ESC[K` (ninja's way) four times a second after a quiet first half second: `<spinner> [k/N] <step> <elapsed> / ~<last> · [n/N] · ~<left> left`, where `k/N` is the step's place among this run's steps. `[n/N]` is the newest ninja counter in the step's own log (steps 40 and 50 write them; others show none); `~<last>` and `~<left>` appear only when `timings.tsv` has them (Decision 6). The line is cut to the terminal's width − 1 columns. The width is read every frame from fd 3, which the ticker itself opens on its own standard output, the terminal, before any `$(…)` (`exec 3>&1`, then `stty size <&3`), else `COLUMNS`, else 80; 0 counts as unset. `build.sh` never opens fd 3, so no step inherits it in either mode (condition A). No WINCH trap: one line cut to width cannot wrap.
   - **Equality.** Before each permanent line the status line is erased (`\r ESC[K`), so the terminal ends showing the plain output exactly, apart from colour: in terminal mode, unless `NO_COLOR` is set and non-empty, `ok` is green and `FAILED`, `ERROR` and `INTERRUPTED` are red, as SGR around the word. Glyphs (a braille spinner) appear only in the status line, and only when the caller's locale is UTF-8: `LC_ALL`, else `LC_CTYPE`, else `LANG`, read before `build.sh` exports `LC_ALL=C`; otherwise `|/-\`. Everything goes to stdout, in order.
   - **No log text reaches the status line.** It shows only the driver's own words and numbers; `[n/N]` is parsed as digits.

4. **A failure says why, from the step's own words, with one `ERROR` line.**
   ```
   FAILED <step>: exit <n> after <duration>; the last 20 lines of build/logs/<step>.log:
     | <line>            (20 lines, or every line of a shorter log)
   ::error title=build step <step> failed::<reason>     (only with GITHUB_ACTIONS set)
   ERROR <step>: <reason> (log: build/logs/<step>.log)
   ```
   `<reason>` is the log's last line that starts with `ERROR` at column 0, else `exit <n>`. The tail lines are cut to printable ASCII and tab, with whole CSI sequences dropped, in both modes. In the `::error` line `%`, CR and LF are encoded `%25`, `%0D`, `%0A`. `grep '^ERROR'` still yields exactly one line, the reason (spec 003 Decision 1 and `AGENTS.md` rule 10: "a failure is one line with its reason"), and it comes last.

5. **A summary ends every passing build.** `done: <k> steps in <duration>`. When step 90 ran: `; the artifact set is in build/artifacts/`, then the three artifacts, each `  <name> <bytes> bytes  <first 16 hex digits of its SHA256SUMS hash>`, then `next: uv run pytest -m "not slow"`. A build without step 90 says only which steps ran (a named step removes `build/artifacts/`, so it would be false to point there).

6. **Times.** Durations are whole seconds from `date +%s` (POSIX on all three hosts), formatted `7s`, `3m02s`, `1h04m`. Permanent lines read the clock through `progress_clock`, which runs `${BUILD_CLOCK:-date +%s}`; the ticker reads `date +%s` itself. Every run appends to `build/logs/timings.tsv` the columns `run step status seconds`, where `run` is the build's start time and process id, and `status` is `ok`, `error` or `interrupted`. The estimate for a step is its newest `ok` row; the time left is the sum of the remaining steps' estimates plus the running step's estimate minus its elapsed time, never below 0, with every estimate taken as at least 1 second; it is dropped when any is missing or the elapsed time passes ten times the estimate (condition B). Times are shown to a person; no check reads them (§4.9). The file is never an input to a step or the artifact set.

7. **Options.** `--list` (each step, the first sentence of its script's header comment without its `Step NN: ` prefix, cut at a word with `...` past 80 columns, and its newest `ok` time); `--from STEP` (that step and every later one); `--resume` (the newest run in `timings.tsv`: if its last row is not `ok`, that step and every later one in the full list; else `nothing to resume` and exit 2); `--plain`; `--check` (the preflight alone); `--help`. Named steps, `--from` and `--resume` are exclusive; `--plain` combines with any; `--list`, `--check` and `--help` go alone (with steps or with each other they exit 2). An unknown option or step exits 2 with the usage. **Nothing is skipped on its own**, and no staleness warning is given: the same-bytes gate is the guard (memo §4.7; the review, finding 8).

8. **A preflight**, run first by every build and alone by `--check`: the host key (`line.sh`); the host tools `cc make shasum tar gzip xz sed uv git stty df` on `PATH` (not `curl`: step 00 checks it where it fetches, so a build with every pin present never needs it, and the fetch-rule check stays as it is); and, only when `build/tools` does not exist yet (a first build), at least 2.5 GiB free under `build/` (`df -Pk` on its nearest existing parent; evidence: the build's own folders total 1.77 GiB, the review's `du`). One line: `preflight: <host key>; <n> tools; <g> GiB free`, or one `ERROR preflight: …` line and exit 1. `.DS_Store` files are not warned about: spec 018 made the build immune to them.

9. **The download step.** `get` prints `fetched <name>` or `present <name>`, and fails with `ERROR: no curl on PATH; it fetches <name>` before a fetch it cannot make. `shasum`'s `<name>: OK` lines stay. The last line is `downloads: <n> pins, <f> fetched, <v> verified` (`n` counts `get` calls, `v` the `OK` lines of this run's pins, counted from `shasum`'s output saved to a file, never through a pipe, since `sh` has no `pipefail` and a pipe would hide `shasum`'s failure; condition D), which becomes step 00's `ok` summary. A verified file that is no pin of this run is named apart: `; 1 other file in downloads/ verified too`. The ticker shows the newest `downloads/*.part` and its size. Every literal `get <url> <name>` line and the `shasum` line stay, for `scan.url_errors` and `scan.download_script_errors`.

10. **How the checks reach the build.** `tests/unit/test_build_progress.py` copies `build.sh`, `progress.sh`, `remove.sh`, `line.sh` and `line.conf` into a temporary tree with fake steps under the eleven real names (`HERE` comes from `$0`), with stand-ins on `PATH` for `df` and the preflight's tools, and `BUILD_CLOCK` set to a counting script. Terminal mode runs on a pty (stdlib `os.openpty`, the width set with `TIOCSWINSZ`) read by a small replayer of CR, LF, `ESC[K` and SGR; every read is bounded by a count, so a leaked ticker fails instead of hanging. The pty checks skip with `needs: a pty` where there is none (Windows).

## Intent

A person building by hand always knows which step is running, how long it has left, and, when it fails, why; CI's log reads as before, with durations.

## Design

```
scripts/build.sh               options, traps, the loop
scripts/steps/progress.sh      mode choice, the ticker, permanent lines, failure block, summary,
                               timings, the preflight
scripts/00_download.sh         one line per pin; curl checked where it fetches
tests/unit/test_build_progress.py   the checks below
README.md, CHANGELOG.md
```

## Scope

In: the above. Out: a rolling tail of the log under the status line (the review's finding 15: one line meets the intent with no cursor movement; a later specification may add it), a JSON event stream (no consumer yet), parallel steps, shell completions, a Makefile, skipping up-to-date steps, a staleness warning, taskbar progress (memo §4.7).

## Acceptance criteria

Each check runs a fake build as Decision 10 says. Nothing measures time.

1. **Frames, then equality.** In terminal mode, a fake step waits for a file the test creates only after it has read a frame naming the step and `[k/11]` from the pty; then the final screen, with SGR dropped, equals the plain output, for a passing and a failing build, with and without a `timings.tsv`, on an 80- and a 30-column pty with long summaries, in a UTF-8 and a C locale, under `dash` (or `sh`) and `bash`.
2. **Every exit path.** Ctrl-C (SIGINT to the process group): `INTERRUPTED <step>`, exit 130, the pty reaches end of file, no process left. SIGTERM to `build.sh` during a step that then succeeds: its `ok` line, then `INTERRUPTED`, exit 143. A renderer command made to fail after the ticker starts: the build exits non-zero and the pty reaches end of file within the read bound.
3. **The step sees nothing of the renderer.** On one pty with one explicit environment (no `CI`), a fake step records `env | sort`, `[ -t 0 ]` and its argv; terminal mode and `--plain` give equal records; run alone with the four exports written in the check (`SOURCE_DATE_EPOCH`, `UV_CACHE_DIR`, `PYTHONHASHSEED`, `LC_ALL`) and the same `BUILD_CLOCK` gives the same (condition E).
4. **The failure block.** A log whose `ERROR: the real reason` comes before a later `checking strerror... yes` and `make: *** [all] Error 2` names the `ERROR:` line (today's grep would not); a log whose only match is indented gives `exit <n>`; a 50-line log shows exactly its last 20 lines and a 5-line log all 5; one `^ERROR` line; `::error` only with `GITHUB_ACTIONS`, before the last line, `%` as `%25`; a tail line holding `ESC[31mred` shows `red` on the screen.
5. **Tables.** Mode, colour and glyph choice; the duration format; the estimate (numbers in, strings out).
6. **Options and preflight.** `--list`; `--from 60` runs `60 70 80 90`; `--resume` after a run that failed at 40 runs 40 to 90, after a passing run prints `nothing to resume` and exits 2; an unknown step or option exits 2; `--check` refuses a missing tool and, on a first build, too little space, through stand-ins.
7. **The download step,** in a temporary tree with `curl` stubbed: `fetched`, `present`, the summary line, and the missing-`curl` refusal.
8. **The real build.** A build from pins in a clean clone gives the same `SHA256SUMS` as before; its plain output is today's lines with durations, the preflight line and the summary.
9. `uv run pytest` green with `--accept-judge`; lost 0; grew 0. A release dry run passes.

## Landing notes

Built 2026-10-17 by the implementer (Claude Opus 5.5), on darwin-arm64; not yet reviewed. Each claim is labelled. Scratch outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/build027/`.

**What was built** (READ: the diff). `scripts/steps/progress.sh` (new): the mode, colour and glyph choices as pure functions, the cleaner, the estimate, the ticker, the permanent lines, the failure block, the preflight and the summary. `scripts/build.sh`: the options, the traps (INT, TERM and HUP recorded; an EXIT trap stops the ticker), the loop and `timings.tsv`. `scripts/00_download.sh`: `fetched`/`present`, curl checked in `get`, `shasum`'s lines saved to `build/downloads-verified.txt` and never piped, and the `downloads:` line. `tests/unit/test_build_progress.py` (new, 75 checks, Decision 10's method). `README.md` ("How it is built") and `CHANGELOG.md` (a new `0.1.0a4 — unreleased` section).

**Seen failing first** (EXECUTED, `seen-failing.txt`). The checks ran in a clone at `2ea71f5` with today's `build.sh` and an empty `progress.sh`: 74 failed, 1 passed. The one that passed is the mismatch guard (condition D), which today's script already meets. Then (EXECUTED, in a scratch clone) each mutant below was caught:
- no EXIT trap: the renderer-failure check fails;
- a ticker that dies at once under `set -e` (the prototype's defect): 4 frame checks fail;
- the width read as `stty size <&1` inside `$(…)`: both 30-column checks fail;
- today's reason grep: 2 checks fail;
- `export P_MODE` in terminal mode, or `exec 3>&1` in `build.sh`: criterion 3 fails;
- `shasum` piped through `tee`: the mismatch check fails;
- no signal check before a step: both TERM checks fail;
- neither erase: 9 checks fail. One erase alone is caught by nothing. INFERRED: the other one covers it, since `progress_stop` erases before every permanent line that follows a frame.

**The criteria.** EXECUTED: `uv run pytest tests/unit/test_build_progress.py` gives 75 passed, under `dash` and `bash`. A scratch runner (`demo/other_shell.py`) ran the same 75 functions with the shell set to `/bin/sh` (bash in POSIX mode) and to `zsh --emulate sh`: 75 passed each.
1. Criterion 1 runs as a pairwise cover: eight runs, in which every pair of the five factors' values appears. They are passing/failing, timings.tsv or not, 80/30 columns, UTF-8/C, and dash/bash. The full product would be 32 runs. A check also shows the `.part` frame (Decision 9) and `NO_COLOR`.
2. Criterion 2 has Ctrl-C (dash, bash), TERM (dash, bash, then `--resume` from the step not started), and a `BUILD_CLOCK` that fails at step 00's end while the ticker runs.
3. Criterion 3 also records `ls /dev/fd` (condition A).
4. Criterion 4 runs in plain mode. Its `red` line also appears in criterion 1's failing runs on the terminal.
- One flake was found and fixed in the check, not the build. EXECUTED under ten `yes` processes: the Ctrl-C check's "no process left" probe got `PermissionError` (EPERM) from `os.killpg(pgid, 0)` in 12 of 30 runs. On macOS that means a member has exited and is not yet reaped. It now keeps looking (a bounded count). After the fix, under the same load: 90 of 90 exit-path runs passed, and the whole file passed 3 times.
5. Criteria 5 to 7 hold as written.

**Criterion 8, the real build** (EXECUTED). A clean clone of `2ea71f5` got the six changed files copied in and `progress.sh` staged; step 90 refuses an untracked recipe. It used the main tree's `downloads/`, hard-linked. Both builds below exited 0.
- `sh scripts/build.sh > log`: the preflight line, eleven `ok` lines with durations, `done: 11 steps in 5m18s` and the three artifacts (`clean-plain.log`). Step 00's line is now `downloads: 29 pins, 0 fetched, 30 verified`; the research zip is present, so 30 are verified.
- A second build over it on a 100-column pty (`demo/pty_build.py`, the shell's own environment): 1058 frames, the widest 54 columns. The final screen is the same lines (`clean-pty.txt`). The raw bytes hold no cursor-up or erase-below sequence.
- Both builds give the same `SHA256SUMS`. Against the main tree's `build/artifacts/SHA256SUMS`, 15 of its 16 lines are equal: the three artifacts and every licence. The 16th is `MANIFEST`'s, as for specs 018 and 020. `MANIFEST` differs only in the `recipe` lines of `scripts/00_download.sh`, `scripts/build.sh` and the new `scripts/steps/progress.sh`. So the wording "the same `SHA256SUMS`" holds for every line but `MANIFEST`'s, which records the scripts' own hashes.
- In the clone, against its own set: v1.1 24/25 (blocked: wheel), v1.5 18/18, rules 18/19 (blocked: prior-art clones). Together with the new checks: 135 passed, 2 skipped.

**The judge in the main tree** (EXECUTED: `uv run pytest -p no:cacheprovider -q`, never `--accept`). 732 passed, 1 failed, 4 skipped. v1 is 187/190, with 2 blocked (three systems, wheel). The unit suite is 545/547 (470 before, plus these 75). The ratchet: lost 1, grew 0; the judge changed (`tests/unit/test_build_progress.py`). The lost pass is `test_manifest_recipes_match_the_tree`. The main tree's set was built from the old scripts, so its `MANIFEST` names their hashes. INFERRED: rebuilding the main tree's set after the commit gives it back, as in the clone. Then the run with `--accept-judge` follows (criterion 9). `ruff check` and `ruff format --check` on `src` and `tests` are clean. `build/progress/latest.json` was restored byte for byte after the runs.

**Choices the specification left open** (INFERRED, each the smallest reading):
- A signal recorded during the last step, which then succeeds, prints its `ok` line, then `INTERRUPTED after <step>: every step had finished`. It exits with the signal's code and gives no summary. Decision 2 says the build exits 130, 143 or 129; there is no next step to name.
- `CI` counts as set even when empty (`${CI+set}`).
- The `ok` summary is cleaned like the tail lines before its 120-character cut. Today's summaries are ASCII, so no line changes. The `ERROR` reason is not cut, since Decision 4 names no cut; today's cut was 160.
- `--list` and `--help` run no preflight; `--check` runs nothing else.
- The ASCII separator in the status line is `-`; in UTF-8 it is `·`.

**Not done.** A release dry run (criterion 9) needs this change on GitHub. The `--accept-judge` run and the main tree's rebuild are the owner's, after review. The new `0.1.0a4 — unreleased` section means `release/version.py bump` will refuse ("already has a section"). The owner can bump by hand, or remove the heading, bump, and paste the entry back.

**Revised against the build review** (`../reviews/027-the-build-says-where-it-is-2026-10-17.md`; its Disposition answers each finding). The scripts changed in three wording points; Decisions 2, 7 and 9 above now say them:
- A signal between steps now prints `INTERRUPTED before <step>`, with no log path. That step never started, so this run wrote no log for it. Its `interrupted 0` row stays, for `--resume` (condition C). A signal during a step still names the step and its log.
- `--list` prints each header's first sentence without its `Step NN: ` prefix. A sentence too long for 80 columns is cut at a word and ends `...`. `--list`, `--check` and `--help` now go alone: with steps or with each other they exit 2 with the usage.
- The download step's `verified` counts only this run's pins. A file that verifies but is no pin of this run (the research input) is named apart, so the line reads `downloads: 29 pins, 0 fetched, 29 verified; 1 other file in downloads/ verified too`.

The checks grew from 75 to 83:
- Every frame is checked for log text. A held step's log carries `LOGTEXT ESC[31mred`, which no frame may show. At 80 columns every frame must also fully match the status line's grammar.
- New checks: the ticker stops on its own (`kill -0`) once `build.sh` is SIGKILLed; TERM during the last step; `--list` shows the newest `ok` time; the real headers are cut at a word; a verified file that is no pin is named apart; three more option combinations exit 2.
- The pty child now starts with SIGINT, SIGTERM, SIGHUP and SIGQUIT at their defaults.
- The Ctrl-C check holds its step with one `sleep 30`, not a poll loop.

Evidence (EXECUTED, in `lab2/`, a clone of `20dfcb6` holding the committed `dd79241`):
- The new file against the committed scripts: 8 failed, 75 passed. The 8 are the wording and option checks.
- Against the fixed scripts, the reviewer's surviving mutants now fail:
  - log text in the frame (the last line cleaned, or the first line raw): 9 checks fail each;
  - the ticker without `kill -0`: "the ticker drew 7 frames after the build was gone";
  - the oldest `ok` row as the estimate: 1 check fails;
  - no `INTERRUPTED after` line: 1 check fails.
- The committed Ctrl-C check, run with SIGINT ignored in the parent, failed 2 of 2 (`assert 0 == 130`).
- The new pair passed 60 of 60 runs plain, 60 of 60 with SIGINT ignored, 60 of 60 under twelve busy loops, and 30 of 30 under load with SIGINT ignored: 420 executions, all passing.

After the revision (EXECUTED, main tree, `final-runs.txt`, `judge2.txt`):
- `tests/unit/test_build_progress.py` gave 83 passed in each of 10 runs, 5 of them under twelve busy loops.
- `ruff check` and `ruff format --check` are clean.
- The full judge: 740 passed, 1 failed, 4 skipped. v1 is 187/190, the unit suite 553/555. The ratchet: lost 1, grew 0, judge changed.
- The one failure is still `test_manifest_recipes_match_the_tree`. It passes once step 90 re-runs on the committed scripts.
- `build/progress/latest.json` was restored byte for byte (`7530f697…`).

**Landed 2026-10-17.** The build reviewer's confirmation (in the review) found the four surviving mutants caught (27 of 30) and the 83 checks green in 32 runs with SIGINT ignored. The lane re-ran step 90 on `1c8a4bb`, judged that commit (741 passed, 4 skipped; v1 188/190, both blocked as before; lost 0, grew 0, judge changed: `tests/unit/test_build_progress.py`), and accepted it with `--accept-judge` (`dc188a6`). Release dry run 39084581927 on `dc188a6`: every job passed, the arm64 Linux rebuild from the pins and "the same bytes from every host" included.
