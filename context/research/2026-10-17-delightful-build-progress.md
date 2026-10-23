# A build that says where it is

- **Status:** research, 2026-10-17. Nothing in `scripts/`, `src/` or `tests/` changed; the prototype lives only in this memo's folder.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5). Box: one session. It studied six tools' progress code, read three guides, captured two of the build's own tools on a terminal and on a pipe, and built a throwaway POSIX sh prototype with a mode-equality check. It did not run `scripts/build.sh`.
- **Feeds:** a specification that amends spec 003, Decision 1 (`build.sh` "printing one line, `ok <step>` or `ERROR <step>: <last log line>`"), and the README's "How it is built".
- **Stands on:** the owner's request (2026-10-17): "Can we improve this experience with a progress bar and some other DX features?". Also `scripts/build.sh`, `scripts/00_download.sh`, `scripts/steps/common.sh`, spec 003 Decision 1, `2026-10-17-finder-litter-breaks-a-desktop-build.md` (a build is long enough for a desktop to interfere with it), and constitution §4.2, §4.7, §4.8, §4.9, §4.13 and §6.4.

## Terms

- **TTY mode** is output to a terminal (a *TTY*), which may redraw lines in place.
- **Plain mode** is output to a pipe or file: append-only lines, no cursor movement, no colour.
- The **live region** is the part of a terminal the build redraws while a step runs: a status line and the last few lines of the step's log.
- A **permanent line** is a line that stays on screen once a step ends.
- The **ticker** is a background process that redraws the live region a few times a second.
- The **mode-equality rule**: once the build ends, the terminal shows exactly what plain mode printed. The live region adds motion, never content.

## Labels

EXECUTED: a command run in this session, with its output in `2026-10-17-delightful-build-progress/captures/`. READ: source read in a clone under `context/prior_art/` (commits in its README) or a web page. INFERRED: a conclusion drawn from the two. Durations below are benchmark facts about one build; no check may assert them (§4.9).

## Method

1. Read the build driver, the download script, `common.sh`, spec 003 Decision 1 and the release workflow (`.github/workflows/release.yml` runs `scripts/00_download.sh` and `scripts/build.sh` on non-TTY runners, and uploads `build/logs/` on failure).
2. Shallow-cloned ninja, cargo, uv, buildkit, Homebrew and pnpm (sparse where large). Checked each licence right after cloning: Apache-2.0, MIT/Apache-2.0, MIT/Apache-2.0, Apache-2.0, BSD-2-Clause, MIT. Rows added to `context/prior_art/README.md`. Read clig.dev, no-color.org, the Evil Martians article (Shamin and Turner, 2024-04-15) and GitHub's workflow-commands page.
3. Captured the pinned ninja (`build/tools/pylib/bin/ninja`) and uv on a pseudo-terminal and on a pipe (`capture_tty_vs_plain.sh`, `pty_run.py`: stdlib `os.openpty`).
4. Measured what today's logs hold: step durations from log times, the lines the failure grep would pick, the progress lines already present, and the bytes a live tail would send to a terminal.
5. Wrote a POSIX sh prototype (`prototype/progress.sh`, about 120 lines) over fake steps. Then checked it three ways under dash and bash: plain output against the replayed terminal screen (`check_modes.sh`, `replay_terminal.py`), Ctrl-C on a real pty (`interrupt_probe.py`), and the log sanitizer (`progress_clean`).

## 1. What today's build shows, and what its logs already know (EXECUTED, READ)

- **Silence during a step.** `build.sh:41-46` runs `sh "$script" > "$log" 2>&1` and prints only after the step ends. The last full build (2026-10-17, 15:56 to 16:01) spent 345 s on steps 10 to 90. CPython alone took 182 s, 53 % of it (`captures/step_durations.txt`: each log's last write marks its step's end). So the longest silence is about three minutes.
- **A count of steps misleads.** When step 20 ends, 3 of 11 steps are done (27 %). But 199 of 345 s have passed (58 %). A bar that fills by step count would run slow and then jump.
- **The failure line can lie.** It quotes the last log line that matches `ERROR|[Ee]rror` anywhere. Today's successful zlib log already has one: `Checking for strerror... Yes.` (`captures/what_the_logs_hold.txt`). So a zlib failure that printed no error word would be reported as "strerror... Yes". A failure with no match prints an empty reason.
- **The steps already write their own progress.** Meson runs ninja off a terminal, so the numpy and pandas logs hold ninja's `[n/N]` lines: 331 and 154 of them. CPython's `Platforms/WASI` driver writes 7 phase lines (`❯  make --jobs 10 all`) to the step log and sends compiler output to `build/logs/cpython/*.log`. A live view can read X of Y for the two longest meson steps, and the current phase of CPython, from files that exist today. No step needs to change.
- **Log bytes are not all plain text.** The CPython step log has 31 lines with bytes of 0x80 and above (emoji). No log holds an ESC byte today, but the logs come from upstream build systems running on untrusted downloads (§4.8). A live tail must not pass escape sequences through to the terminal.
- **The download step is quiet by design.** `00_download.sh:16-21` runs `curl -fsSL` and skips a file that is present. Its summary line is the last `shasum` line, for example `libclang_rt-33.0+m.tar.gz: OK`. That names one file, not the 29 pins this host fetches.
- **One step already shows its own failure tail.** `35_stdlib_libs.sh:52-53` prints the last 20 lines of `make.out` before it dies. The pattern belongs in the driver, for every step.

## 2. The patterns that make build progress feel good (READ)

| pattern | who does it, and where |
|---|---|
| X of Y, not a bare spinner | Evil Martians: X of Y is "the default choice"; a stuck count shows a stall. ninja's default status is `[%f/%t] ` (`src/status_printer.cc:83-85`). cargo's `Building [===>   ] 35/222` (`src/util/progress.rs:213-228`; used at `src/compiler/job_queue/mod.rs:495`). buildkit's header `[+] Building 12.3s (5/10)` (`display.go:1004`). |
| what is running now | cargo appends the active units' names (`job_queue/mod.rs:947-962`). uv shows the current package (`uv-install-operations/src/reporters.rs:87-112`). |
| elapsed time; past-tense lines with durations | cargo: `Finished ... target(s) in {time}` (`job_queue/mod.rs:881-912`). buildkit plain: `#N DONE 1.2s` (`printer.go:195-205`). uv: `Prepared 1 package in 2ms` (captured). Evil Martians: switch "-ing" to past tense once done. Homebrew: `HOMEBREW_DISPLAY_INSTALL_TIMES` (`env_config.rb:321-324`). |
| ETA from the previous run | ninja reads each edge's last duration from `.ninja_log` and predicts by time, not count. It trusts the old timings only while the new run's average is within 10x, checked once 15 s and 5 % have passed (`status_printer.cc:135-215`). Its `%W` and `%P` give ETA and predicted percentage (`doc/manual.asciidoc:261-310`). |
| a rolling tail of the live log | buildkit shows the last 6 lines under the running step as ` => => # ...`, dimmed (`init.go:16`, `display.go:1040-1080`), sized by `BUILDKIT_TTY_LOG_LINES` (`init.go:44-52`). |
| failure output with the last lines inline | buildkit plain keeps the last 10 lines per step and prints them after `------ > <step>:` (`printer.go:22`, `display.go:785-800`). pnpm collapses a script's output to its last 10 lines plus `[N lines collapsed]` (`state/lifecycle.rs:100-108`). ninja prints `FAILED: [code=N] <outputs>`, the command, then the output (`status_printer.cc:240-257`). clig.dev: put "the most important information at the end". |
| a final summary | Homebrew: `🍺  <prefix>: <size>, built in <time>` (`formula_installer.rb:1141-1147`), with an emoji switch (`HOMEBREW_NO_EMOJI`, `HOMEBREW_INSTALL_BADGE`, `env_config.rb:496-500, 561-568`). clig.dev: "Suggest commands the user should run." |
| throttled, flicker-free redraws | cargo waits 500 ms before the first draw, then redraws at most every 100 ms (`progress.rs:125-139, 428-462`). uv ticks its spinner every 200 ms (`reporters.rs:19`). pnpm redraws at most every 200 ms on a terminal and every 1 s append-only (`default-reporter/src/lib.rs:285-286`). Homebrew wraps each frame in synchronized-update escapes (`utils/tty.rb:130-140`) and redraws every 50 ms (`download_queue.rb:245-300`). |
| colour by intent, off on request | no-color.org: a non-empty `NO_COLOR` turns colour off. ninja honours `NO_COLOR`, `CLICOLOR_FORCE` and `FORCE_COLOR` (`line_printer.cc:40-91`). Homebrew: `NO_COLOR`, `HOMEBREW_COLOR`, else the stream's TTY state (`utils/tty.rb:213-221`). pnpm: colour when the stream is a TTY and `NO_COLOR` is unset (`colors.rs:21-29`). |
| a machine-readable mode | buildkit `rawjson` (`display.go:120-170, 280-300`). pnpm `ndjson` (`cli_args/reporter.rs:16-30`). cargo `--message-format json` emits `BuildFinished` (`job_queue/mod.rs:890-897`). clig.dev: `--json`, `--plain`. |
| CI annotations | Homebrew turns warnings and errors into `::warning`/`::error` when `GITHUB_ACTIONS` is set (`utils/github/actions.rb:19`, `utils/output.rb:88-92`). GitHub: `::error title=...::message` makes an annotation. |
| strip escapes from child output | ninja strips ANSI codes from a command's output when it is not on a smart terminal (`status_printer.cc:259-276`). Homebrew has `Tty.strip_ansi` (`utils/tty.rb:84-90`). |
| terminal taskbar progress | cargo emits OSC 9;4 when the terminal supports it (`progress.rs:466-556`; `term.progress.term-integration`, `doc/book/src/reference/config.md:1636-1641`). A nicety, not a need. |

## 3. How each tool decides TTY or plain, and what plain looks like (READ, EXECUTED)

- **ninja.** It treats stdout as a "smart terminal" when `isatty(1)` is true and `TERM` is set and not `dumb` (`line_printer.cc:55-58`). There it prints `\r`, the status and `ESC[K` (`line_printer.cc:99-113`); otherwise each status ends with a newline. EXECUTED with the build's pinned ninja: on a pty, every update overwrites one line and only `[4/4] SLOW d` stays. On a pipe and on a pty with `TERM=dumb`, it prints the same four lines, `[1/4] SLOW a` to `[4/4] SLOW d` (`captures/ninja.*.txt`). A second run with `NINJA_STATUS='[%f/%t %p eta %W pred %P] '` read the first run's `.ninja_log` and printed `eta 00:03` down to `00:00` (`captures/ninja.status-eta.txt`).
- **cargo.** `term.progress.when` is `auto`, `always` or `never` (`progress.rs:56-62`; `CARGO_TERM_PROGRESS_WHEN`). Under `auto`, there is no bar when output is quiet, when `TERM=dumb`, or when `is_ci()` finds `CI` or `TF_BUILD` set (`shell.rs:366-379`, `crates/cargo-util/src/lib.rs:24-26`). There is also no bar without a stderr width, which needs a TTY (`shell.rs:108-116`). Its plain output is the same status lines (`Compiling`, `Finished`), right-aligned in 12 columns (`shell.rs:482-494`), with no bar. Its bar formatter is a pure function of (cur, max, width): the tests call it with fixed numbers and no clock (`progress.rs:558-700`).
- **uv.** It draws through indicatif to stderr. Indicatif hides the bars when stderr is not a terminal. `--no-progress`/`UV_NO_PROGRESS`, `-q` and `-v` hide them too (`printer.rs:18-56`). A Jupyter session gets a single-line mode (`progress.rs:117-127`). When the bars are hidden, uv writes a plain line for the same event instead: `Building <x>`, `Built <x>`, and `Downloaded <x>` for files over 1 MiB (`progress.rs:155-182, 289-320`). EXECUTED: an offline install of the pinned `six` wheel, on a pty and on a pipe. After removing the transient lines (those ending in CR) and the escapes, the pty transcript equals the pipe transcript line for line, timings aside, with colour and with `NO_COLOR=1` (`captures/uv.*.txt`). That is the mode-equality rule, met by a mature tool.
- **buildkit.** `auto` picks `tty` when the writer is a console, else `plain`. `tty` on a non-console is an error. `rawjson` and `quiet` are explicit (`display.go:120-170`). Plain prints numbered lines: `#5 [2/3] RUN make`, `#5 0.512 <log line>`, `#5 DONE 3.2s`, `#5 ERROR: ...`, `#5 CACHED` (`printer.go:61-205`). It rate-limits progress lines (`antiFlicker` 5 s, `maxDelay` 10 s, `printer.go:17-20`) and replays the last 10 log lines of a failed step at the end.
- **Homebrew.** Colour follows `NO_COLOR`/`HOMEBREW_COLOR`, else `$stdout.tty?` (`utils/tty.rb:213-221`). Live redraw needs a TTY and `TERM` other than `dumb` (`download_queue.rb:30-31, 439-441`); otherwise it waits up to 1 s between checks and prints only finished lines with `✔︎`/`✘` (`download_queue.rb:288-290, 462-478`). Its `==>` headings are the same in both modes; only truncation to the terminal width depends on the TTY (`utils/output.rb:53-60`).
- **pnpm.** `default` renders in place on a terminal and becomes `append-only` when stdout is not one. `--reporter=append-only` forces that mode on a TTY. `ndjson` and `silent` are explicit (`cli_args/reporter.rs:16-30`; `default-reporter/src/lib.rs:270-292`). Off a TTY it assumes 80 columns and redraws at most once a second.

All six agree on three things. A pipe gets plain, append-only lines. Escapes go only to a terminal that can take them. And every tool offers a switch to force plain on a terminal. Cargo and ninja also treat `TERM=dumb` as plain, and cargo treats `CI` as plain (INFERRED from the above).

## 4. What fits this project (INFERRED, with the prototype EXECUTED)

### 4.1 The driver stays POSIX sh

Two options, weighed.

- **A small stdlib-only Python driver** (`uv run --no-project python -I scripts/build.py`) would be pleasant to write and to unit-test. But it fails four of this project's constraints.
  1. The pinned host Python does not exist until step 10 unpacks it (`common.sh`: `HOSTPY` is under `build/tools/`). So steps 00 and 10 would run under whatever Python uv finds. That interpreter is unpinned (§4.2), even if it touches no artifact byte.
  2. `uv run` changes the environment: it sets `VIRTUAL_ENV` and puts a venv on `PATH` unless told not to. Whatever the driver exports reaches every step. CPython's `configure` and meson search `PATH` for `python3`. A driver that changes a step's environment puts the same-bytes promise at risk (spec 012).
  3. Spec 003 Decision 1 says `00_download.sh` "calls no Python".
  4. §6.4 asks for the fewest files and dependencies, and the steps already run under `sh`.
- **A POSIX sh driver plus a small function library**, `scripts/steps/progress.sh`, sourced by `build.sh` the way `remove.sh` is today. It adds no dependency and no interpreter. It works for steps 00 and 10. It leaves the step environment alone by construction. The prototype shows it is enough: about 120 lines, run under dash (Linux's `/bin/sh`) and bash (macOS's `/bin/sh`).

**Decision: sh.** Its two pitfalls have known fixes. First, `build.sh:14` exports `LC_ALL=C`, so `cut -c` cuts bytes and can split a multibyte character. The fix: show log lines as printable ASCII only (below). Second, decide UTF-8 glyphs from the user's locale before `LC_ALL=C` is set.

### 4.2 One way to run a step; two ways to show it

- **The step always runs in the foreground**, in both modes, as today: `sh step > build/logs/<step>.log 2>&1`. On a terminal, the *ticker* is the background job. The step is not. This is decided by evidence:
  - POSIX lets a non-interactive shell's background job ignore SIGINT. Shells differ in practice: zsh's background job survived a SIGINT, while dash's and bash's died (`captures/signal_probe.txt`). A step in the background could therefore leave `make` and `clang` running after Ctrl-C.
  - With the step in the foreground, a real ^C on a pty killed the step's `sleep` and the ticker under both dash and bash. The build exited 130, and its last line was `INTERRUPTED d_long (log: logs/d_long.log)` (`captures/interrupt_probe.txt`).
- **The step's environment, stdin and argv are the same in both modes.** The renderer reads logs and writes to the terminal only. It writes no file except the timings record under `build/logs/`, which is never an input to any step or to the artifact set. The prototype's ticker builds each frame in memory.
- **Mode choice**, from what the six tools agree on:
  - `auto` (the default) picks TTY when `[ -t 1 ]`, `TERM` is set and not `dumb`, and `CI` is unset. Otherwise it picks plain.
  - `--plain` (or `BUILD_PROGRESS=plain`) forces plain on a terminal. `BUILD_PROGRESS=tty` exists for tests.
  - Colour only in TTY mode, and only when `NO_COLOR` is empty or unset.
  - Glyphs (`✓ ✗` and a braille spinner) only when the user's own locale was UTF-8. Otherwise ASCII (`ok`, `x`, `|/-\`).
  - Everything goes to stdout, as today. A build has no other "primary output" that stderr would protect (clig.dev's stdout/stderr split assumes one). So one stream keeps CI logs in order.
- **Plain mode is the record.** Its lines are exactly the permanent lines of TTY mode. EXECUTED on the prototype: the same fake build ran in plain mode and on a pty, each with a counting clock. The pty bytes were replayed to the final screen and compared. The screen equalled the plain output for a passing build (4 lines) and a failing one (24 lines), under dash and bash. That held whether the ticker drew 6 frames or 93 (`captures/prototype_check.txt`). So the invariant does not depend on timing.
- **Log lines are sanitized before they reach a terminal.** The live tail and the failure tail keep printable ASCII, tab and newline only. EXECUTED: a line holding `ESC[31m` and U+276F came out with no ESC byte and no high byte (`captures/progress_clean.txt`). A spec could go further and drop whole CSI sequences, so `[31m` does not show as text.

### 4.3 What the live region shows

- The status line has five parts, built from what exists today:
  1. the spinner;
  2. the step;
  3. elapsed time, set against the previous run's duration (`1m48s / ~3m02s`);
  4. the step's own progress: ninja's last `[n/N]` in the log, or else the last log line;
  5. the overall position, `[3/11]`.
- The **rolling tail** shows the last 4 lines of the newest file under `build/logs/`, dimmed. "Newest" catches the CPython driver's own log under `build/logs/cpython/` without special-casing it.
- **Long lines are shown from their end.** That log is mostly clang command lines, and every one starts with the same absolute path to `wasi-sdk-33.0-arm64-macos/bin/clang`. Their ends differ: `-DPy_BUILD_CORE -o Python/import.o ../../Python/import.c` (EXECUTED: the last 70 bytes of four such lines). So the tail drops the repository prefix, and when a line is too wide it keeps the line's end behind `...`. The prototype does not do this yet; it cuts from the start.
- The **overall bar and ETA** come from `build/logs/timings.tsv` (step, status, seconds), which every run writes. The bar fills by *previous time*, not by step count, as ninja's `%P` does. Without a previous run it falls back to the count, and it drops the ETA if a step runs past 10x its old time (ninja's sanity rule).
- **Redraws** happen at about 4 to 5 Hz. The cursor goes back with `ESC[nA`, and the region is erased with `ESC[J` before each permanent line. The prototype redraws every 0.2 s. A specification could add cargo's 500 ms quiet start, so steps under half a second never flicker.

### 4.4 Plain mode in CI

- Plain mode prints `start <step>` lines, but no heartbeat by default. GitHub Actions does not kill a silent job. A spec may add one heartbeat line a minute when `CI` is set, prefixed `..`, so `grep '^ok \|^ERROR '` still sees only results. Buildkit's 5 to 10 s plain cadence is too chatty for a log people read.
- When `GITHUB_ACTIONS` is set, a failure also emits one `::error title=build step <step> failed::<reason>`, as Homebrew does. The 20-line tail stays outside any `::group::`, so it is visible without a click.
- The release workflow already uploads `build/logs/` on failure, and that stays.

### 4.5 The download step

`00_download.sh` stays Python-free and keeps one literal `get <url> <name>` line per pin.

- `get` prints one line per pin into the log: `have <name>` or `got <name> <bytes>`.
- `shasum`'s `<name>: OK` lines stay as the verify ticks.
- The script ends with one summary line, `downloads: 29 pins, 3 fetched, 29 verified`. That becomes the step's `ok` line in place of today's last `shasum` line.
- The ticker shows `fetching wasi-sdk-33.0-arm64-macos.tar.gz 41.2 MB` by reading the size of the growing `.part` file. No curl progress meter is needed, and none goes into the log.
- Counting the pins needs no new metadata: `get` can run once in a counting mode before the real pass, with the same literal lines.

### 4.6 How a judge check tests the renderer without a clock

The pattern is already in the repo. `tests/unit/test_build_scripts.py` runs `remove.sh` under `sh` with `rm` replaced by a function that counts calls, and its docstring says "Nothing measures time". cargo's bar tests and ninja's `FormatProgressStatus(fmt, time_millis)` tests work the same way: the time is an argument (`status_test.cc`). For a new `tests/unit/test_build_progress.py`:

1. **A fake step runner.** A temporary steps directory of tiny scripts. Each prints N lines and maybe `ERROR: ...` to stderr, and exits with a chosen code. The driver takes the directory from the library function the test calls, so `build.sh` itself needs no test hook.
2. **A counting clock.** The test overrides `progress_now` with a counter: each reading adds a fixed number. Durations become counts, and the output is the same on every run.
3. **A fake terminal.** A pty (stdlib `os.openpty`) plus a small replayer that understands CR, LF, `ESC[K`, `ESC[J`, `ESC[nA` and SGR. This is `replay_terminal.py` here.

The checks then are:

- the final screen equals the plain output, for a passing and a failing build;
- a failure shows exactly the last 20 lines, then the step's own `^ERROR` line (not the `[Ee]rror` match), and the build exits 1;
- a fake step that writes `env | sort` and `[ -t 0 ]` sees the same thing in plain mode, in TTY mode and when run alone with `build.sh`'s exports. This is the guard that progress cannot reach the artifacts;
- a step that prints escape bytes never gets one onto the terminal; only the renderer's own `ESC[K`, `ESC[J`, `ESC[nA` and SGR appear;
- mode selection is a table: (TTY or not, `TERM`, `CI`, `NO_COLOR`, the flag) gives (mode, colour);
- duration format and ETA are tables: numbers in, strings out;
- `--list` prints the eleven steps in order; `--from 60` resolves to `60 70 80 90`; an unknown step exits 2 and lists the steps.

These count lines and compare bytes, so they stay inside §4.9. The prototype's `check_modes.sh` is the first of them in miniature.

### 4.7 Other DX features, weighed

- **`--list`**: each step with the first line of its script's header comment (`# Step 20: CPython ...`; every step has one) and its last duration. Tiny effort, no new metadata.
- **`--from STEP`** (and `--resume`, meaning "from the step that failed last", read from `timings.tsv`): sugar over today's `build.sh 60 70 80 90`. It is safe for the same reason that is: each step deletes and rebuilds its own outputs from the earlier steps' outputs. The line says what it skipped: `skip 00_download..50_pandas: not rebuilt this run`.
- **A preflight** (`build.sh --check`, also run first by every build because it costs milliseconds):
  - the host key (`line.sh` already fails on an unknown host);
  - the host tools the README names, `cc make curl shasum tar xz sed uv git`, with versions, as the rebuild job already records them;
  - free space under `build/`. The last build's own directories took 1.8 GiB, and `downloads/` holds 572 MiB (EXECUTED: `du`; `build/` is 4.2 GiB in all, but most of the rest is the judge's `cwasm-cache`, `harness` and `oracle`). So warn below 3 GiB;
  - a warning, not a failure, when `build/` already holds `.DS_Store` litter. It fails in a second instead of three minutes in, when step 20 finds no `make`.
- **A summary**: total time, the three artifacts with size and the first 16 hex digits of their `SHA256SUMS` hash, where they are, and `next: uv run pytest -m "not slow"`, the first command of every session (AGENTS.md, "Working autonomously" 1).
- **A machine-readable mode**: `build/logs/timings.tsv` is written on every run, plain and awk-able, and is the ETA source too. A `--json` event stream (buildkit, pnpm, cargo) is cheap later but has no consumer today. Deferred, not rejected.
- **Skipping up-to-date steps automatically: not safe here. Not recommended.** A skip is right only if a stamp covers *every* input of the step and of all earlier steps:
  - the step script, `common.sh`, `line.conf` and `line.sh`;
  - each recipe file and `scripts/*.py` helper it reads, and the compiler wrappers;
  - the pins it unpacks, and the earlier steps' outputs;
  - the unpinned host `cc` and `make` of step 20. Miss one, and the build silently keeps stale bytes. Locally nothing would catch it; only the release's same-bytes and rebuild-from-pins gates would. The build is built the other way on purpose: each step deletes and remakes its outputs, and `build.sh:36-38` removes `build/artifacts` before every step after the download, so a rebuild never looks current when it is not. What is safe is advisory: record a hash of `git ls-files -s scripts recipes` beside each step's timing, and have `--from` *warn* when an earlier step ran under different scripts or recipes. It never skips on its own.
- **Not worth it:**
  - Shell completions: eleven step names, and `--list` covers discovery.
  - A `Makefile` or `justfile`: a second entry point, and §6.4.
  - Emoji badges: the build runs under `LC_ALL=C`, and the project's voice is plain.
  - Parallel steps: interleaved logs and a concurrency risk to reproducibility, for a few seconds.
  - Cargo's OSC 9;4 taskbar progress: pleasant, optional, and last.

## What it decides

A specification ("the build says where it is") amends spec 003 Decision 1 as follows.

- `scripts/build.sh` stays POSIX sh and sources a new function library, `scripts/steps/progress.sh`. There is no Python and no new dependency. The step environment is unchanged, and a check guards that.
- Every step runs in the foreground, its output to `build/logs/<step>.log`, as today. On a terminal, a background ticker redraws a live region: spinner, step, elapsed against the last run, the step's own `[n/N]`, `[k/11]`, a time-weighted bar with ETA, and the last 4 lines of the newest log, sanitized to printable ASCII. The region is erased before each permanent line.
- Plain mode prints the permanent lines only. They are the record, and the terminal ends showing exactly them. Plain is chosen when stdout is not a TTY, `TERM` is `dumb` or unset, `CI` is set, or `--plain` is given. `NO_COLOR` turns colour off.
- Permanent lines keep today's prefixes, so existing greps hold:
  - `ok <step>: <summary> [<duration>]`;
  - on failure, `ERROR <step>: exit <n> after <duration>`, then the last 20 log lines indented `  | `, then `ERROR <step>: <the log's last line starting ERROR, else exit n> (log: <path>)`. The most important line comes last.
- A summary ends every passing build: the total time, the three artifacts with sizes and hashes, and the next command.
- `build/logs/timings.tsv` is written on every run. It holds step, status, seconds and a hash of the scripts and recipes. It feeds the ETA, `--list`, `--resume` and the `--from` staleness warning.
- New flags: `--list`, `--from STEP`, `--resume`, `--check`, `--plain`, `--help`. There is no automatic skipping.
- `00_download.sh` prints one line per pin and a one-line summary. On a terminal, the ticker shows a fetch's bytes from the `.part` file.
- In CI with `GITHUB_ACTIONS` set, a failure also emits one `::error` annotation.

### Mock: the terminal, mid-build

The durations are the 2026-10-17 build's (`captures/step_durations.txt`). The download time is illustrative: every pin was present.

```
build: 11 steps on MACOS_ARM64 · logs in build/logs/ · last build 5m46s
✓ 00_download     downloads: 29 pins, 0 fetched, 29 verified                    1s
✓ 10_tools        tools: python 3.15.0, meson 1.12.1, ninja 1.13.2…, cython 3.3.0  17s
⠼ 20_cpython      make --jobs 10 all                                  1m48s / ~3m02s
    | ...-DPy_BUILD_CORE -o Python/hamt.o ../../Python/hamt.c
    | ...-DPy_BUILD_CORE -o Python/hashtable.o ../../Python/hashtable.c
    | ...-DPy_BUILD_CORE -o Python/import.o ../../Python/import.c
    | ...-DPy_BUILD_CORE -o Python/initconfig.o ../../Python/initconfig.c
  [███████████▋                    ] 3/11 · 2m06s · about 3m40s left
```

The mock assumes a UTF-8 locale and colour. The `✓` lines are green and the tail is dim. In ASCII the glyphs become `ok` and `|/-\`. When step 20 ends, the five live lines are erased, and one permanent line takes their place: the plain line below, drawn with `✓`.

### Mock: plain output for the same build (CI, a pipe, or `--plain`)

```
build: 11 steps on MACOS_ARM64; logs in build/logs/; the last build took 5m46s
ok 00_download: downloads: 29 pins, 0 fetched, 29 verified [1s]
ok 10_tools: tools: python 3.15.0, meson 1.12.1, ninja 1.13.2.git.kitware.jobserver-pipe-1, cython 3.3.0 [17s]
ok 20_cpython: cpython: 29582540 bytes, 7a906d750d998aa3 [3m02s]
ok 30_zlib: zlib: 102842 bytes [2s]
ok 35_stdlib_libs: stdlib libs: bz2 80798, lzma 213672, sqlite3 2048884 bytes [36s]
ok 40_numpy: numpy: 19 extension archives, installed at numpy-install/usr/local/lib/python3.15/site-packages/numpy [41s]
ok 50_pandas: pandas: 45 extension archives, package at pandas-install/pandas [43s]
ok 60_link: reactor: 31760992 bytes, 4befe9de64edc783 [14s]
ok 70_zip: python-stdlib.zip: 1098 pyc, 653 data files, 11140635 bytes [5s]
ok 80_snapshot: snapshot: 65506824 bytes, c7302cfd191ac3b9 [5s]
ok 90_artifacts: artifacts: 17 files in build/artifacts [0s]
done: 11 steps in 5m46s; the artifact set is in build/artifacts/
  python.wasm             31760992 bytes  4befe9de64edc783
  python-snapshot.wasm    65506824 bytes  c7302cfd191ac3b9
  python-stdlib.zip       11140635 bytes  1add57e442f3d565
next: uv run pytest -m "not slow"
```

A failure, in the same plain form (a mock of a liblzma failure in step 35):

```
ok 30_zlib: zlib: 102842 bytes [2s]
ERROR 35_stdlib_libs: exit 1 after 12s; the last 20 lines of build/logs/35_stdlib_libs.log:
  | ...
  | ERROR: liblzma make failed (build/xz-build/make.out)
::error title=build step 35_stdlib_libs failed::ERROR: liblzma make failed (build/xz-build/make.out)
ERROR 35_stdlib_libs: ERROR: liblzma make failed (build/xz-build/make.out) (log: build/logs/35_stdlib_libs.log)
```

The `::error` line appears only when `GITHUB_ACTIONS` is set.

### The top five, by value for effort

1. **The failure block.** The last 20 lines inline, and the reason taken from the anchored `^ERROR`. It fixes a real defect (the `strerror` match) in about ten lines.
2. **Durations and the summary.** `[3m02s]` on each line, the total, the artifacts with sizes and hashes, the next command, and `timings.tsv`. Small.
3. **The live status line on a terminal.** Elapsed against the last run, ninja's `[n/N]` from the log, `[k/11]`. This ends the three-minute silence. Medium, as the prototype shows.
4. **`--list`, `--from`, `--resume`, `--help`.** Tiny, and safe because they never skip on their own.
5. **The preflight.** Tools, host key and 3 GiB free, checked in a second at the start. Small.

Next come the rolling tail (small once item 3 exists), the time-weighted bar and ETA, the download lines, and the CI annotation.

### Where it stopped

- The prototype is a study. It is not the build, and nothing under `scripts/` uses it.
- The timings it records are kept only on success.
- It reads the terminal width once per step, from `stty`, so a resize mid-step is missed.
- It cuts long tail lines from the start, not from the end (§4.3).
- It does not yet do the time-weighted bar, the summary's artifact hashes against a real `SHA256SUMS`, the download lines or the preflight.
- The real implementation is a specification's work, with its own review (AGENTS.md: nothing lands unreviewed).

## The folder

`2026-10-17-delightful-build-progress/` holds:

- `capture_tty_vs_plain.sh` and `pty_run.py`: the ninja and uv captures;
- `signal_probe.sh`: background jobs and SIGINT, per shell;
- `prototype/`:
  - `progress.sh`, `demo.sh` and `steps/`: the prototype and its fake steps;
  - `check_modes.sh` and `replay_terminal.py`: the mode-equality check;
  - `interrupt_probe.py`: Ctrl-C on a real pty;
- `captures/`: every output cited above. Local paths are shown as `<repo>` and `<scratch>`.

Reproduce:

```
D=context/research/2026-10-17-delightful-build-progress
sh $D/capture_tty_vs_plain.sh "$PWD" <scratch> $D/captures
sh $D/signal_probe.sh
sh $D/prototype/check_modes.sh /bin/dash <scratch>/m a_fetch b_compile c_fails
uv run --no-project python -I $D/prototype/interrupt_probe.py /bin/bash $D/prototype/demo.sh <scratch>/i
```

## One line

The build is silent for three minutes and can misreport its failures. Keep the driver in POSIX sh. Run each step in the foreground, unchanged. Add a terminal-only live line built from what the logs already say. Make plain mode the record that the terminal ends on, with durations, the last 20 lines on failure and a summary. Test it with fake steps, a counting clock and a replayed terminal.
