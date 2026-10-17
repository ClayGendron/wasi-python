# 027 — The build says where it is

- **Status:** drafted 2026-10-17, awaiting its pre-build review.
- **Owner:** Clay Gendron
- **Kind:** the build driver (`scripts/build.sh`, a new `scripts/steps/progress.sh`,
  `scripts/00_download.sh`'s per-pin lines), unit checks in `tests/unit/`, `README.md`,
  `CHANGELOG.md`. No step's work changes; no artifact changes.
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
2. **One way to run a step.** Every step runs in the foreground, exactly as today
   (`sh step > build/logs/<step>.log 2>&1`), with the same environment, stdin and argv in every
   mode. A Ctrl-C reaches the step; the build prints `INTERRUPTED <step> (log: …)` and exits 130.
   The renderer reads logs and writes to the terminal; the only file it writes is
   `build/logs/timings.tsv`, which no step and no artifact reads.
3. **Two ways to show it.**
   - **Plain** (stdout not a terminal, `TERM` unset or `dumb`, `CI` set, `--plain`, or
     `BUILD_PROGRESS=plain`): the permanent lines only. They keep today's prefixes, so existing
     greps hold: `ok <step>: <summary> [<duration>]`.
   - **Terminal**: the same permanent lines, plus a live region a background ticker redraws:
     a spinner, the step, its elapsed time against the last run, the step's own `[n/N]` when its
     log has ninja's lines, `[k/11]`, a bar weighted by the last run's step times with the time
     left, and the last 4 lines of the step's log, dimmed. The region is erased before each
     permanent line, so the terminal ends showing exactly the plain output.
   - Colour only on a terminal and only when `NO_COLOR` is unset or empty; `✓`, `✗` and a braille
     spinner only when the caller's locale was UTF-8, else `ok`, `x` and `|/-\`. Everything goes
     to stdout, in order.
   - Log text shown on the terminal is cut to printable ASCII, tab and newline, with whole CSI
     sequences dropped, so a step's output cannot move the cursor or change colours.
4. **A failure says why, from the step's own words.** `ERROR <step>: exit <n> after
   <duration>; the last 20 lines of <log>:`, the 20 lines indented `  | `, then a last line
   `ERROR <step>: <the log's last line that starts with ERROR, else "exit <n>"> (log: <path>)`.
   The most important line comes last. With `GITHUB_ACTIONS` set, one `::error` annotation too.
5. **A summary ends every passing build.** `done: <k> steps in <duration>; the artifact set is in
   build/artifacts/`, the three artifacts with their sizes and the first 16 hex digits of their
   hashes from `SHA256SUMS`, and `next: uv run pytest -m "not slow"`. A partial build (named
   steps) says which steps ran.
6. **Timings.** Every run appends to `build/logs/timings.tsv`: step, status, seconds, and a hash
   of `git ls-files -s scripts recipes`. It feeds the estimates, `--list` and `--resume`. Times
   are benchmark facts shown to a person; no check reads them (§4.9).
7. **New options.** `--list` (each step, its header comment's first line, its last duration);
   `--from STEP` (that step and every later one); `--resume` (from the step that failed last,
   read from `timings.tsv`); `--plain`; `--check` (the preflight alone); `--help`. Named steps
   work as today. **Nothing is ever skipped on its own:** a step skipped because it looks up to
   date would keep stale bytes the moment one input was missed (memo §4.7). `--from` warns when
   an earlier step last ran under different scripts or recipes.
8. **A preflight**, run first by every build and alone by `--check`, in about a second: the host
   key (`line.sh`), the host tools the README names (`cc make curl shasum tar xz sed uv git`),
   and at least 3 GiB free under `build/`. A missing tool or too little space fails at once with
   one line; `.DS_Store` litter under `build/` is a warning.
9. **The download step** prints one line per pin (`fetched`, `present` or `verified`) and a
   summary line; on a terminal the ticker shows a fetch's bytes from its partial file.

## Intent

A person building by hand always knows which step is running, how long it has left, and, when it
fails, why; CI's log reads as before, with durations.

## Design

```
scripts/build.sh               options; the loop calls progress.sh's functions
scripts/steps/progress.sh      mode choice, the ticker, permanent lines, failure block, summary
scripts/00_download.sh         one line per pin
tests/unit/test_build_progress.py   the checks below
README.md, CHANGELOG.md
```

## Scope

In: the above. Out: a JSON event stream (no consumer yet), parallel steps, shell completions, a
Makefile, skipping up-to-date steps, taskbar progress (memo §4.7).

## Acceptance criteria

The checks run a fake build: a temporary steps folder of tiny scripts, a counting clock in place
of `date`, and a pty with a small replayer for the terminal (memo §4.6). Nothing measures time.

1. The terminal's final screen equals the plain output, for a passing and a failing fake build,
   under `dash` (or `sh`) and `bash`.
2. A failure shows exactly the last 20 lines, then the step's own `^ERROR` line (a log holding
   `strerror` and a later `ERROR: …` names the latter), and exits 1.
3. A fake step's `env | sort`, `[ -t 0 ]` and argv are equal in plain mode, terminal mode, and
   run alone with `build.sh`'s exports.
4. A step's escape bytes never reach the terminal; only the renderer's own sequences do.
5. The mode, colour and glyph choice is a table of cases; duration format and the estimate are
   tables of numbers.
6. `--list`, `--from 60` (`60 70 80 90`), `--resume`, an unknown step (exit 2), and `--check`'s
   refusals (a missing tool, too little space, through stand-ins) behave as Decision 7 and 8 say.
7. A real build from pins in a clean clone gives the same `SHA256SUMS` as before, and its plain
   output is today's lines plus durations, the summary and the preflight line.
8. `uv run pytest` green with `--accept-judge`; lost 0; grew 0. A release dry run passes.

## Landing notes

Not built.
