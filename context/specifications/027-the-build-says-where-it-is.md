# 027 — The build says where it is

- **Status:** drafted 2026-10-17; revised against its pre-build review
  (`../reviews/027-the-build-says-where-it-is-spec-2026-10-17.md`), awaiting that review's
  confirmation.
- **Owner:** Clay Gendron
- **Kind:** the build driver (`scripts/build.sh`, a new `scripts/steps/progress.sh`,
  `scripts/00_download.sh`'s per-pin lines), unit checks in `tests/unit/`, `README.md` (its
  "one line each" for the build), `CHANGELOG.md`; spec 003 Decision 1 is amended (below). No
  step's work changes; no artifact changes.
- **Depends on:** 003 (the build, its Decision 1 amended here), 018 (`remove`), both landed.
- **Research it stands on:** `../research/2026-10-17-delightful-build-progress.md` (uv, cargo,
  ninja, BuildKit and Homebrew studied; the prototype under its folder; its "What it decides" is
  this specification's base). The owner asked for it on 2026-10-17: "Can we improve this
  experience with a progress bar and some other DX features?"

## The problem

`scripts/build.sh` prints one line per finished step. A build takes about 5m46s, and step 20
(CPython) is 3m02s of silence. A failure prints one line found by `grep '[Ee]rror'`, which
already matches a harmless `Checking for strerror... Yes.` in today's zlib log (memo §1), so it
can name the wrong reason. There is no total, no duration, no summary of what was made, and no
way to list or resume steps but by retyping their numbers.

## Decisions

1. **The driver stays POSIX sh; no new dependency.** `build.sh` sources a function library,
   `scripts/steps/progress.sh`. Python is not used: the pinned host Python exists only after
   step 10, `uv run` would change the steps' environment, and spec 003 forbids it in the download
   step (memo §4.1).

2. **Running a step: one way, and every exit path.**
   - Every step runs in the foreground, exactly as today (`sh step > build/logs/<step>.log
     2>&1`), with the same environment, stdin and argv in every mode.
   - **Signals.** `build.sh` traps INT, TERM and HUP: the trap records the signal; when the
     running step returns, its own line is printed from its own status (`ok …` if it finished,
     else `INTERRUPTED <step> (log: …)`), and the build exits 130, 143 or 129. Ctrl-C reaches the
     whole process group, so the step stops at once (EXECUTED by the review under dash, bash and
     zsh-as-sh: exit 130, nothing left running). A TERM or HUP sent to `build.sh` alone waits for
     the running step to end, because a shell runs a trap only after its foreground child
     returns; the README says to signal the process group (`kill -TERM -<pgid>`) to stop at once.
   - **The ticker** (the background redraw, terminal mode only) runs with `set +e`, draws one
     whole frame per write, checks `kill -0 "$BUILD_PID"` before every frame, and exits on its own
     when the build is gone or a write fails. An EXIT trap in `build.sh` stops it and erases the
     status line on every exit: success, a failing step, a `set -e` failure in the renderer, and
     each signal.

3. **Two ways to show it.**
   - **Plain** (stdout not a terminal, `TERM` unset or `dumb`, `CI` set, `--plain`, or
     `BUILD_PROGRESS=plain`): the permanent lines only, which keep today's prefixes, so existing
     greps hold: `ok <step>: <summary> [<duration>]`, the summary cut to 120 characters as today.
   - **Terminal**: the same permanent lines, and **one live status line** below them, redrawn
     in place with `\r` and `ESC[K` (ninja's way) four times a second after a quiet first half
     second: `<spinner> [k/11] <step> <elapsed> / ~<last> · [n/N] · ~<left> left`. `[n/N]` is the
     newest ninja counter in the step's own log (steps 40 and 50 write them; others show none);
     `~<last>` and `~<left>` appear only when `timings.tsv` has them (Decision 6). The line is cut
     to the terminal's width − 1 columns. The width is read every frame from the terminal saved on
     fd 3 before any `$(…)` (`exec 3>&1`, `stty size <&3`), else `COLUMNS`, else 80; 0 counts as
     unset. No WINCH trap: one line cut to width cannot wrap.
   - **Equality.** Before each permanent line the status line is erased (`\r ESC[K`), so the
     terminal ends showing the plain output exactly, apart from colour: in terminal mode, unless
     `NO_COLOR` is set and non-empty, `ok` is green and `FAILED`, `ERROR` and `INTERRUPTED` are
     red, as SGR around the word. Glyphs (a braille spinner) appear only in the status line, and
     only when the caller's locale is UTF-8: `LC_ALL`, else `LC_CTYPE`, else `LANG`, read before
     `build.sh` exports `LC_ALL=C`; otherwise `|/-\`. Everything goes to stdout, in order.
   - **No log text reaches the status line.** It shows only the driver's own words and numbers;
     `[n/N]` is parsed as digits.

4. **A failure says why, from the step's own words, with one `ERROR` line.**
   ```
   FAILED <step>: exit <n> after <duration>; the last 20 lines of build/logs/<step>.log:
     | <line>            (20 lines, or every line of a shorter log)
   ::error title=build step <step> failed::<reason>     (only with GITHUB_ACTIONS set)
   ERROR <step>: <reason> (log: build/logs/<step>.log)
   ```
   `<reason>` is the log's last line that starts with `ERROR` at column 0, else `exit <n>`. The
   tail lines are cut to printable ASCII and tab, with whole CSI sequences dropped, in both
   modes. In the `::error` line `%`, CR and LF are encoded `%25`, `%0D`, `%0A`. `grep '^ERROR'`
   still yields exactly one line, the reason (spec 003 Decision 1 and `AGENTS.md` rule 10:
   "a failure is one line with its reason"), and it comes last.

5. **A summary ends every passing build.** `done: <k> steps in <duration>`. When step 90 ran:
   `; the artifact set is in build/artifacts/`, then the three artifacts, each `  <name>
   <bytes> bytes  <first 16 hex digits of its SHA256SUMS hash>`, then `next: uv run pytest -m
   "not slow"`. A build without step 90 says only which steps ran (a named step removes
   `build/artifacts/`, so it would be false to point there).

6. **Times.** Durations are whole seconds from `date +%s` (POSIX on all three hosts), formatted
   `7s`, `3m02s`, `1h04m`. Permanent lines read the clock through `progress_clock`, which runs
   `${BUILD_CLOCK:-date +%s}`; the ticker reads `date +%s` itself. Every run appends to
   `build/logs/timings.tsv` the columns `run step status seconds`, where `run` is the build's
   start time and process id, and `status` is `ok`, `error` or `interrupted`. The estimate for a
   step is its newest `ok` row; the time left is the sum of the remaining steps' estimates plus
   the running step's estimate minus its elapsed time, dropped when any is missing or the elapsed
   time passes ten times the estimate. Times are shown to a person; no check reads them (§4.9).
   The file is never an input to a step or the artifact set.

7. **Options.** `--list` (each step, the first line of its script's header comment, and its
   newest `ok` time); `--from STEP` (that step and every later one); `--resume` (the newest run
   in `timings.tsv`: if its last row is not `ok`, that step and every later one in the full
   list; else `nothing to resume` and exit 2); `--plain`; `--check` (the preflight alone);
   `--help`. Named steps, `--from` and `--resume` are exclusive; `--plain` combines with any.
   An unknown option or step exits 2 with the usage. **Nothing is skipped on its own**, and no
   staleness warning is given: the same-bytes gate is the guard (memo §4.7; the review,
   finding 8).

8. **A preflight**, run first by every build and alone by `--check`: the host key (`line.sh`);
   the host tools `cc make shasum tar gzip xz sed uv git stty df` on `PATH` (not `curl`: step 00
   checks it where it fetches, so a build with every pin present never needs it, and the
   fetch-rule check stays as it is); and, only when `build/tools` does not exist yet (a first
   build), at least 2.5 GiB free under `build/` (`df -Pk` on its nearest existing parent;
   evidence: the build's own folders total 1.77 GiB, the review's `du`). One line:
   `preflight: <host key>; <n> tools; <g> GiB free`, or one `ERROR preflight: …` line and exit 1.
   `.DS_Store` files are not warned about: spec 018 made the build immune to them.

9. **The download step.** `get` prints `fetched <name>` or `present <name>`, and fails with
   `ERROR: no curl on PATH; it fetches <name>` before a fetch it cannot make. `shasum`'s
   `<name>: OK` lines stay. The last line is `downloads: <n> pins, <f> fetched, <v> verified`
   (`n` counts `get` calls, `v` the `OK` lines), which becomes step 00's `ok` summary. The
   ticker shows the newest `downloads/*.part` and its size. Every literal `get <url> <name>` line
   and the `shasum` line stay, for `scan.url_errors` and `scan.download_script_errors`.

10. **How the checks reach the build.** `tests/unit/test_build_progress.py` copies `build.sh`,
    `progress.sh`, `remove.sh`, `line.sh` and `line.conf` into a temporary tree with fake steps
    under the eleven real names (`HERE` comes from `$0`), with stand-ins on `PATH` for `df` and
    the preflight's tools, and `BUILD_CLOCK` set to a counting script. Terminal mode runs on a
    pty (stdlib `os.openpty`, the width set with `TIOCSWINSZ`) read by a small replayer of CR,
    LF, `ESC[K` and SGR; every read is bounded by a count, so a leaked ticker fails instead of
    hanging. The pty checks skip with `needs: a pty` where there is none (Windows).

## Intent

A person building by hand always knows which step is running, how long it has left, and, when it
fails, why; CI's log reads as before, with durations.

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

In: the above. Out: a rolling tail of the log under the status line (the review's finding 15:
one line meets the intent with no cursor movement; a later specification may add it), a JSON
event stream (no consumer yet), parallel steps, shell completions, a Makefile, skipping
up-to-date steps, a staleness warning, taskbar progress (memo §4.7).

## Acceptance criteria

Each check runs a fake build as Decision 10 says. Nothing measures time.

1. **Frames, then equality.** In terminal mode, a fake step waits for a file the test creates
   only after it has read a frame naming the step and `[k/11]` from the pty; then the final
   screen, with SGR dropped, equals the plain output, for a passing and a failing build, with
   and without a `timings.tsv`, on an 80- and a 30-column pty with long summaries, in a UTF-8
   and a C locale, under `dash` (or `sh`) and `bash`.
2. **Every exit path.** Ctrl-C (SIGINT to the process group): `INTERRUPTED <step>`, exit 130,
   the pty reaches end of file, no process left. SIGTERM to `build.sh` during a step that then
   succeeds: its `ok` line, then `INTERRUPTED`, exit 143. A renderer command made to fail after
   the ticker starts: the build exits non-zero and the pty reaches end of file within the read
   bound.
3. **The step sees nothing of the renderer.** On one pty with one explicit environment (no
   `CI`), a fake step records `env | sort`, `[ -t 0 ]` and its argv; terminal mode and `--plain`
   give equal records; run alone with the four exports written in the check
   (`SOURCE_DATE_EPOCH`, `UV_CACHE_DIR`, `PYTHONHASHSEED`, `LC_ALL`) gives the same.
4. **The failure block.** A log whose `ERROR: the real reason` comes before a later `checking
   strerror... yes` and `make: *** [all] Error 2` names the `ERROR:` line (today's grep would not);
   a log whose only match is indented gives `exit <n>`; a 50-line log shows exactly its last 20
   lines and a 5-line log all 5; one `^ERROR` line; `::error` only with `GITHUB_ACTIONS`, before
   the last line, `%` as `%25`; a tail line holding `ESC[31mred` shows `red` on the screen.
5. **Tables.** Mode, colour and glyph choice; the duration format; the estimate (numbers in,
   strings out).
6. **Options and preflight.** `--list`; `--from 60` runs `60 70 80 90`; `--resume` after a run
   that failed at 40 runs 40 to 90, after a passing run prints `nothing to resume` and exits 2;
   an unknown step or option exits 2; `--check` refuses a missing tool and, on a first build, too
   little space, through stand-ins.
7. **The download step,** in a temporary tree with `curl` stubbed: `fetched`, `present`, the
   summary line, and the missing-`curl` refusal.
8. **The real build.** A build from pins in a clean clone gives the same `SHA256SUMS` as before;
   its plain output is today's lines with durations, the preflight line and the summary.
9. `uv run pytest` green with `--accept-judge`; lost 0; grew 0. A release dry run passes.

## Landing notes

Not built.
