# Review of 027 — The build says where it is (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I wrote neither the specification nor the memo. I read `AGENTS.md` and the constitution (§4.2, §4.8, §4.9, §4.13, §5.2, §5.6, §6.4). Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/027-the-build-says-where-it-is.md` as drafted (`d66711d`).
- **Read:** the memo `context/research/2026-10-17-delightful-build-progress.md`, its prototype (`prototype/progress.sh`, `demo.sh`, `check_modes.sh`, `interrupt_probe.py`, the fake steps) and its captures; `scripts/build.sh`, `scripts/00_download.sh`, `scripts/steps/common.sh`, `scripts/steps/remove.sh`, `scripts/steps/apply_patches.sh`, `scripts/steps/20_cpython.sh` and the other steps (for the tools they call), `scripts/line.sh`, `scripts/line.conf`; `tests/unit/test_build_scripts.py`; `tests/harness/scan.py` (`fetch_hits`, `bare_rm_hits`, `bare_python_hits`, `clock_hits`, `url_errors`, `download_script_errors`, `rebuild_gate_errors`) and its callers in `tests/checks/test_rules.py` and `tests/checks/test_v1_5_rebuild_from_pins.py`; `.github/workflows/release.yml`; spec 003 Decision 1; `README.md` ("How it is built"); `context/reviews/README.md` and the 023 pre-build review (for the format).
- **Ran (EXECUTED, darwin-arm64).** Nothing in the repository was edited but this file. I did not run `scripts/build.sh` or `uv run pytest`. Scripts and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev027/`:
  - The memo's `check_modes.sh` under `/bin/dash` and `/bin/bash` (fake steps `a_fetch b_compile c_fails`), counting cursor-up sequences in the raw pty bytes (`m_dash/`, `m_bash/`).
  - The same demo under dash with a `timings.tsv` already present (`second/`).
  - A driver that starts the prototype's ticker and then fails a command under `set -eu` (`orphan/main.sh`), under dash and bash.
  - SIGTERM to the prototype build during a 4 s fake step (`proto/steps/e_slow.sh`, `term_*`).
  - Ctrl-C on a real pty (`int_probe.py`, a copy of the memo's probe that waits for the step's log instead of sleeping): plain and terminal mode, a step that traps INT and one that does not, under dash, bash, `/bin/zsh` and `zsh --emulate sh` (`zsh-sh`).
  - `scan.fetch_hits` and `scan.bare_rm_hits` on a scratch `scripts/steps/progress.sh` holding the preflight's tool loop (`scan/`).
  - `git ls-files -s | shasum` before and after an unstaged edit, in a scratch repository (`gitls/`).
  - `stty size` inside and outside `$(…)` on a fresh pty; `cut -c1-0`; today's failure grep on two logs; `du -sk build/*/`, `df -Pk build`, `find build -name .DS_Store`, `date +%N`, and `/private/var/select/sh` (read only, in the main tree).

## What holds

- **POSIX sh, no Python, is the right driver.** READ: the pinned host Python exists only after step 10 (`common.sh`: `HOSTPY` under `build/tools/`); spec 003 Decision 1 says `00_download.sh` "calls no Python"; `uv run` would change the steps' `PATH`. INFERRED: the choice is the smallest one (§6.4).
- **The step stays in the foreground, and Ctrl-C works.** EXECUTED: a `^C` written to a real pty during a step ended the prototype with exit 130 and `INTERRUPTED <step> (log: …)` as the last line, with no step and no ticker left running, under dash, bash and `zsh --emulate sh`, in terminal mode, and also when the step traps INT itself and exits 3. (macOS `/bin/sh` here is bash: `/private/var/select/sh -> /bin/bash`, EXECUTED.)
- **Nothing is skipped on its own.** Decision 7 keeps the build's rule that each step deletes and remakes its outputs (`build.sh:36-38` removes `build/artifacts` before every step after 00). `--from` and `--resume` are sugar over `build.sh 60 70 80 90`, which is already allowed, and each step re-verifies its pins through `pinned` (READ, `common.sh:41-48`), so skipping step 00 skips no verification.
- **Neither `timings.tsv` nor the preflight can reach the artifacts.** READ: no step reads `build/logs/` (step 20 only writes its driver's logs there); step 70 zips named trees, step 90 assembles from `build/out/`, and `MANIFEST` lists recipes through `git`. The preflight only runs `command -v`, `df` and `find`. The same-bytes gate stays the proof (criterion 7). (INFERRED for the whole set; READ for each step.)
- **No automated consumer greps the build's output.** READ: the release workflow runs `scripts/00_download.sh` and `scripts/build.sh` and greps only pytest's output (`^7 passed, [0-9]+ deselected in`); the judge needs only the literal `run: scripts/build.sh` lines (`scan.rebuild_gate_errors`); the only other reader is the README's "eleven steps, one line each". On GitHub Actions stdout is a pipe and `CI` is set, so CI gets plain mode twice over.
- **The 20 tail lines are safe in a CI log.** INFERRED: each is cleaned to printable ASCII and starts with `  | `, so no log line can start a GitHub workflow command (`::…`), which the runner reads only at a line's start.

## Acceptance criteria against evidence

1. Final screen equals plain output — **does not prove the ticker ran:** the memo's own check passes under dash with zero frames drawn (Finding 3). The glyph rule contradicts it (Finding 4).
2. The failure block — **passes on today's grep** as worded (Finding 10).
3. The step's environment — **cannot pass as written:** the mode's own variables and `[ -t 0 ]` differ between the runs by construction (Finding 6).
4. No escape bytes — reachable; it should also assert the visible text, since Decision 3 drops whole CSI sequences, not only the ESC byte (Finding 10).
5. Tables — **open:** the duration format and the estimate's formula are not written (Finding 13).
6. Options and `--check` — **open:** how a check reaches `build.sh`, its clock and its preflight is not decided (Finding 7); `--resume` has no defined behaviour to test (Finding 9).
7. A real build — reachable; "today's lines" no longer holds for step 00's `ok` line or for a failure (Findings 11, 14).
8. Green with `--accept-judge` — **not as written:** the preflight fails an accepted rules check (Finding 1).

## Findings, most severe first

1. **High. The preflight's tool list turns the judge red.** (Decision 8; `tests/harness/scan.py:122`, `fetch_hits`; `tests/checks/test_v1_5_rebuild_from_pins.py:38-40`)
   - The defect. `test_no_build_script_fetches_outside_the_download_script` scans every file under `scripts/` for the word `curl` and allows it only in `00_download.sh`. Decision 8 puts `cc make curl shasum tar xz sed uv git` into `build.sh` or `progress.sh`.
   - Failure. EXECUTED: `scan.fetch_hits` on a scratch `scripts/steps/progress.sh` holding `for tool in cc make curl shasum tar xz sed uv git; do` returns that line. The accepted check fails; criterion 8 cannot be met without weakening the fetch rule.
   - Fix. Check `curl` where it is used: `get` in `00_download.sh` fails with one line (`ERROR: no curl on PATH; it fetches <name>`) before its first fetch, which also means a build with every pin present never needs `curl`. The preflight checks the rest. Do not exempt `command -v` lines in the scanner.

2. **High. The ticker's lifetime is not specified, and the prototype's leaks.** (Decision 2, Decision 3; the memo's `progress_step` and `progress_ticker`)
   - The defect. The spec names one exit path, Ctrl-C. The ticker is stopped only by the INT/TERM trap and by the normal path after the step.
   - Failure 1, `set -e`. EXECUTED (`orphan/`): a driver under `set -eu` starts the ticker and then a command fails. Under dash and bash the build exits 1, and the ticker keeps drawing on the terminal after the shell prompt returns (285 and 228 bytes in the next second). Any renderer command between start and stop (`tail`, `awk` on `timings.tsv`, a `$(…)` assignment) is such a command.
   - Failure 2, SIGTERM. EXECUTED (`term_*`): `kill -TERM` to the build during a 4 s step. The step is not signalled and runs to the end (`finished-anyway` in its log); only then does the trap run, printing `INTERRUPTED e_slow` and exiting 130. A step that succeeded is reported interrupted, and the code is not 143. A shell defers a trap until its foreground child exits, so with a 3-minute step 20 a `kill` or `timeout` waits 3 minutes. SIGHUP is not trapped at all.
   - Failure 3. No acceptance criterion exercises Ctrl-C, TERM, or a renderer failure, so Decision 2's promise (`INTERRUPTED`, 130) has no check.
   - Fix. Decide and write: (a) the ticker runs with `set +e`, never exits mid-frame, and exits on its own when the build's PID is gone (`kill -0 "$BUILD_PID"` each frame) or a write fails; (b) an EXIT trap stops the ticker and erases the region on every exit; (c) TERM and HUP: say that a TERM to `build.sh` alone waits for the running step (signal the process group to stop now, as Ctrl-C does), that the finished step's own line is printed, and the exit code (143/129); (d) checks: the memo's interrupt probe as a judge check (exit 130, the last line, no process left), a TERM case, and a renderer failure injected after the ticker starts, each requiring the pty to reach end of file within a bounded number of reads (so a leaked ticker fails instead of hanging).

3. **High. Criterion 1 passes with a ticker that never draws.** (Acceptance criterion 1; memo §4.2, `captures/prototype_check.txt`)
   - The defect. Mode-equality compares the final screen only. A ticker that dies, or never starts, leaves exactly the plain output.
   - Failure. EXECUTED: the memo's `check_modes.sh` passes under dash, but the raw pty bytes hold zero cursor-up sequences: no frame was drawn. Under `set -eu`, `prev=$(progress_prev "$1")` fails when `timings.tsv` does not exist (a first run, which every check run is), and the background function exits. With a `timings.tsv` present, the same demo draws 13 frames. The memo's "6 frames or 93" counts carriage returns that the pty's newline translation adds. The memo's "ticker left running: no" for dash is vacuous for the same reason.
   - Failure 2. EXECUTED: the prototype reads the width as `$(stty size <&1 …)`. Inside `$(…)`, fd 1 is the substitution's pipe, so `stty` never sees the terminal; the width is always `${COLUMNS:-80}`. On a fresh pty `stty size` is `0 0`, and `cut -c1-0` is an error. No criterion would notice either.
   - Fix. Criterion 1 also requires frames: the fake step waits for a file that the test creates after it has read one frame naming the step and `[k/N]` from the pty, bounded by a read count; run it with and without a `timings.tsv`, and on a narrow pty (say 30 columns, set with `TIOCSWINSZ`) with log lines longer than that.

4. **Medium. The glyph rule contradicts mode-equality and the kept prefixes.** (Decision 3)
   - The defect. On a UTF-8 terminal, `✓` and `✗` replace `ok` and `x`; the memo's terminal mock shows `✓ 00_download   …   1s` in columns. Yet the terminal must "end showing exactly the plain output", whose lines start `ok` and `ERROR`. Where `x` would appear is not said.
   - Failure. INFERRED: an implementation that follows the glyph sentence fails criterion 1 in a UTF-8 locale; one that passes criterion 1 ignores the glyph sentence. A person who copies the terminal into `grep '^ok '` gets nothing.
   - Fix. Glyphs and colour only in the live region (spinner, bar). Permanent lines are byte-equal to plain apart from SGR colour; criterion 1 compares after dropping SGR only, under both a UTF-8 and a C locale. Say which variables decide UTF-8 (`LC_ALL`, then `LC_CTYPE`, then `LANG`, read before `build.sh` exports `LC_ALL=C`).

5. **Medium. Terminal width and resize are left to the build.** (Decision 3; §5.2)
   - The defect. The region is redrawn by moving the cursor up one row per line. A line wider than the terminal wraps to two rows and the count is wrong. The spec says nothing about width.
   - Failure. INFERRED: a 60-column terminal, a long status line → each frame leaves one stale row above, and the final screen is not the plain output. A window narrowed mid-step reflows rows already drawn (macOS Terminal and iTerm2 reflow) with the same result.
   - Fix. Write: the width is read every frame from the terminal fd saved before any `$(…)` (`exec 3>&1` … `stty size <&3`), else `COLUMNS`, else 80, and 0 counts as unset; every live line is cut to width − 1 columns after cleaning; a window narrowed between frames may leave stray rows above the region, accepted as cosmetic and said so. No WINCH trap.

6. **Medium. Criterion 3 cannot pass as written, and its baseline is undefined.** (Criterion 3)
   - The defect. The test chooses the mode through the environment (`BUILD_PROGRESS`, `TERM`, `CI`), and the step inherits it, so `env | sort` differs between modes by construction. `[ -t 0 ]` is true on a pty and false on a pipe. "Run alone with `build.sh`'s exports" does not say whether the list is read from `build.sh` (then an extra `export` in `progress.sh` would be read too) or fixed.
   - Failure. INFERRED: either the check is red on a correct build, or it is weakened by excluding variables until a leaked `export P_MODE=tty` passes.
   - Fix. Both runs on the same pty with the same explicit environment (no `CI`); plain chosen by the `--plain` argument, which no step sees; `env | sort`, `[ -t 0 ]` and argv compared exactly; the "alone" run uses the four exports written in the check (`SOURCE_DATE_EPOCH`, `UV_CACHE_DIR`, `PYTHONHASHSEED`, `LC_ALL`).

7. **Medium. How the checks reach `build.sh`, its clock and its preflight is not decided.** (Acceptance criteria preamble, 6; memo §4.6; §5.2)
   - The defect. `build.sh` hard-codes its eleven step names and `$HERE/scripts/steps/`. The memo tests "the library function", which leaves `build.sh`'s options, exports and loop untested; criterion 6 tests `build.sh` itself. The "counting clock in place of `date`" is not placed: if it is a `date` stub on `PATH`, the ticker's reads advance the same counter, so terminal-mode durations differ from plain ones. Every fake build also runs the preflight, which needs 3 GiB free on the judge's temporary disk and the real host tools, so the check's result depends on the machine.
   - Fix. Write the method. One that needs no hook: copy `build.sh`, `progress.sh`, `remove.sh`, `line.sh` and `line.conf` into a temporary tree with fake steps under the eleven real names (`HERE` comes from `$0`); the permanent lines read the clock through one function at step start and end, the ticker through another, and the stub counts only the former; `df` and missing tools are stand-ins on `PATH` in every fake build. Name the clock: `date +%s`, whole seconds, on all three hosts (`%N` is not POSIX; it happens to work on this macOS, EXECUTED, but is not needed). The pty checks skip with `needs: a pty` where there is none (Windows).

8. **Medium. The `--from` staleness warning is wrong in both directions.** (Decision 6, Decision 7)
   - The defect. `git ls-files -s` lists the index, not the working tree; and one hash covers all of `scripts` and `recipes`.
   - Failure. EXECUTED (`gitls/`): the hash is the same before and after an unstaged edit (`d31e2392284b` both), and changes only after `git add`. So the commonest local case, edit a recipe and run `--from`, never warns. Once committed, any edit, including to the step you resume from, changes every earlier step's hash, so every legitimate `--from` warns.
   - Fix. §6.4: drop the warning and the hash column; the same-bytes gate is the guard, as the memo says. If kept, hash working-tree bytes (`find scripts recipes -type f | LC_ALL=C sort | xargs shasum`) and word the line as information, not as a warning about the earlier step.

9. **Medium. `--resume` and `timings.tsv` are underspecified.** (Decision 6, Decision 7)
   - The defect. The rows have no run id, so "the last run" cannot be found. The statuses are not listed (is an interrupted step a row?). There is no rule for a last run that passed, for a failure since fixed by a named run, or for a failure inside a partial run.
   - Failure. INFERRED: run 1 fails at 40; `build.sh 40` passes; `--resume` finds the old error row and rebuilds 40 to 90 again, or finds nothing, depending on the build.
   - Fix. Columns `run step status seconds`, with `run` a value fixed per invocation; statuses `ok`, `error`, `interrupted`; `--resume` takes the newest run only; if its last row is not `ok`, that step and every later one in the full list; else one line `nothing to resume` and exit 2.

10. **Medium. Criterion 2 passes on today's grep; 4 checks only the ESC byte.** (Criteria 2, 4)
    - Failure. EXECUTED: a log with `checking strerror... yes` and a later `ERROR: the real reason`; today's `grep -E 'ERROR|[Ee]rror' | tail -n 1` names the ERROR line. So a mutant that keeps today's reason grep passes criterion 2.
    - Fix. Put the `ERROR:` line before a later `strerror` and `make: *** [all] Error 2` line; add a log whose only match is indented (`  ERROR`), and one with none (reason `exit <n>`); assert exactly 20 tail lines when the log is longer and every line when it is shorter; assert the `::error` line appears only with `GITHUB_ACTIONS`, before the final line, with `%` encoded as `%25`. For 4, assert the screen shows `red`, not `[31mred`.

11. **Low. The download step's lines do not match `00_download.sh`, and have no check.** (Decision 9; `00_download.sh:16-21, 94`)
    - The defect. Verification is one `shasum -a 256 --ignore-missing -c SHA256SUMS` at the end, not a per-pin action, and it also verifies other present files (the research zip, when present). `fetched`, `present` and `verified` are not one status per pin. "Bytes from its partial file" needs the ticker to know the name. No criterion covers Decision 9.
    - Fix. `get` prints `fetched <name>` or `present <name>`; `shasum`'s `<name>: OK` lines stay; a last line `downloads: <n> pins, <f> fetched, <v> verified` (`n` counts `get` calls, `v` the OK lines), which becomes step 00's `ok` summary. The ticker shows the newest `downloads/*.part` and its size. Keep each literal `get <url> <name>` line and the `shasum` line (`scan.url_errors`, `scan.download_script_errors`). A check with `curl` stubbed on `PATH` in a temporary tree.

12. **Low. The preflight's figure and list.** (Decision 8)
    - EXECUTED: the build's own folders under `build/` total 1.77 GiB (`du -sk` of the 25 step folders, `logs` and `uv-cache`: `tools` 766 MiB, CPython 361 MiB, each other under 131 MiB), and `downloads/` 572 MiB; the judge then adds `cwasm-cache` (1899 MiB), `oracle` and `harness`. The memo said warn below 3 GiB; the spec says fail. A rebuild over an existing tree reuses its 1.77 GiB, so a hard 3 GiB floor can refuse a build that fits. `df` on a `build/` that does not exist yet fails.
    - The list: GNU tar runs `gzip` for every `tar -xzf` (steps 10 to 50); the renderer itself needs `stty` and `df`. EXECUTED: `build/` here already holds 61 `.DS_Store` files, so the litter warning fires on every desktop build, though spec 018 made the build immune to them.
    - Fix. Fail only below what a first build needs (say 2.5 GiB, with the `du` above as its evidence) and only when `build/tools` does not exist; `df -Pk` on the nearest existing parent; add `gzip`; limit the litter warning to `build/artifacts/` (the one case the README names) or drop it.

13. **Low. Formats and rules left to the build (§5.2).**
    - The duration format (memo: `7s`, `3m02s`, `1h04m`) and the estimate's formula (weights from the newest `ok` row per step; the count when there is none; the ETA dropped past 10× the old time) are needed for criterion 5's tables but are not in the spec.
    - The `ok` summary's cut width (120 today), the preflight's line and warning texts, `--list` and `--help` output, the exit code for an unknown option, which options combine, the redraw rate and the 500 ms quiet start, and where the `::error` line goes.
    - A partial build's summary: `build.sh 20` removes `build/artifacts/`, so "the artifact set is in `build/artifacts/`" would be false; say the artifact lines appear only when step 90 ran.
    - The tail's source: the spec says the step's log; the memo said the newest file under `build/logs/`. For step 20 the step log holds only the driver's 7 phase lines; the compiler lines are in `build/logs/cpython/`. Choose and say why.
    - Fix. Write each in the Decisions.

14. **Low. A failure now prints two `^ERROR <step>:` lines.** (Decision 4; spec 003 Decision 1; `AGENTS.md`, rule 10)
    - The defect. The header and the last line both start `ERROR <step>:`. Spec 003 promised one `ERROR <step>: <reason>` line, and `AGENTS.md` says "a failure is one line with its reason".
    - Fix. Start the header differently (`FAILED <step>: exit 1 after 12s; the last 20 lines of …:`), so `grep '^ERROR'` still yields exactly the reason line. Put spec 003's amendment note and the README's "one line each" in the Kind.

15. **Low (§6.4). A one-line status meets the Intent with less.** (Decision 3)
    - INFERRED: Findings 2, 3 and 5 come from the multi-row region: cursor-up counts, wrapping and a tail of untrusted text. A single status line redrawn with `\r` and `ESC[K` (ninja's way), holding the spinner, step, elapsed against last time, `[n/N]`, `[k/11]` and the time left, tells a person which step runs and how long it has left. It needs no cursor-up and is safe at any width once cut. The memo ranks the rolling tail after its top five.
    - Fix. Consider a one-line live region, the tail out of scope; or say why four tail lines are worth the extra machinery.

## Constitution checks

- **§4.2:** nothing pinned changes; the preflight only looks for the unpinned host tools the README already names. Its `curl` placement must not break the fetch rule (Finding 1).
- **§4.8:** step logs come from untrusted upstream build systems; Decision 3's cleaning and the `  | ` prefix keep their bytes off the terminal's control path and out of workflow commands. The `::error` text needs `%` encoded (Finding 10).
- **§4.9:** the design counts: a counting clock, replayed bytes, durations shown to a person only. The pty reader must bound by reads, not by `time.*` (`test_no_test_reads_a_clock`), and the clock injection must be written (Finding 7).
- **§4.13:** uv only; no dependency added; the checks use the stdlib `pty`/`os.openpty`, POSIX only.
- **§5.2:** open choices in Findings 2, 4, 5, 7, 9 and 13.
- **§5.6:** the spec changes the build driver, so this pre-build review applies.
- **§6.4:** Finding 8 (drop the hash), Finding 15 (one line).
- **§7:** nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

All fifteen findings are taken; the largest change is finding 15's.

1. **Fixed.** `curl` leaves the preflight; `get` in `00_download.sh` refuses with one line before a fetch it cannot make (Decisions 8 and 9). The fetch rule is unchanged.
2. **Fixed.** Decision 2 writes every exit path: the ticker under `set +e`, `kill -0` each frame, exit on a failed write; an EXIT trap stops it and erases the line; INT, TERM and HUP give 130, 143 and 129, the finished step's own line first, and the README tells how to stop at once. Criterion 2 checks Ctrl-C, TERM and a renderer failure with bounded pty reads.
3. **Fixed.** Criterion 1 requires a frame naming the step and `[k/11]` before the step may end, with and without `timings.tsv`, on 80 and 30 columns; the width is read from fd 3 every frame.
4. **Fixed.** Glyphs only in the status line; permanent lines byte-equal to plain apart from SGR; the locale variables named, read before `LC_ALL=C`.
5. **Fixed, and simplified by 15.** One line cut to width − 1 cannot wrap; no WINCH trap.
6. **Fixed.** Criterion 3: one pty, one explicit environment, `--plain` as the only difference, and the four exports written in the check.
7. **Fixed.** Decision 10: a copied tree with fake steps under the real names, stand-ins on `PATH`, `BUILD_CLOCK` for the permanent lines only, pty checks skipped on Windows.
8. **Fixed by removal.** No hash column and no staleness warning; the same-bytes gate guards.
9. **Fixed.** `timings.tsv` columns `run step status seconds`, statuses `ok`, `error`, `interrupted`; `--resume` reads the newest run only, with the rule written; criterion 6.
10. **Fixed.** Criterion 4 puts the `ERROR:` line before `strerror` and `Error 2`, adds the indented and no-match logs, exact tail lengths, the `::error` placement and encoding, and the screen showing `red`, not `[31mred`.
11. **Fixed.** Decision 9 matches the script's structure (`get` lines, one `shasum`), the summary line, the `.part` size; criterion 7.
12. **Fixed.** 2.5 GiB, only on a first build, `df -Pk` on the nearest parent, `gzip`, `stty` and `df` added, no litter warning.
13. **Fixed.** Durations, the estimate formula, the 120-character cut, the redraw rate and quiet start, the partial summary, and the tail's source (none: finding 15) are written.
14. **Fixed.** The header starts `FAILED`; `grep '^ERROR'` yields exactly the reason line; spec 003 Decision 1 and the README's line are named in the Kind.
15. **Taken.** One live status line, redrawn with `\r` and `ESC[K`; the rolling log tail moves to Scope as a possible later specification. No log text reaches the live line.

## Verdict

Revise first. The design's core is right and its Ctrl-C path works under every shell tried. But the judge goes red on the preflight as written (Finding 1). The ticker can outlive the build (Finding 2). The main check passes with no ticker at all, as the memo's own run did under dash (Finding 3). And the glyph rule, width, the test method and `--resume` are left open (Findings 4, 5, 7, 9).

One line: keep the sh driver and the foreground step, but move `curl`'s check into the download script, give the ticker a cleanup on every exit and a check that it really drew, and decide the glyph, width, clock and resume rules before it is built.

## Confirmation

- **Date:** 2026-10-17
- **Reviewer:** the same fresh agent (Claude Opus 5.5); not the author.
- **Reviewed:** the specification as revised in `4b8ccad` and the Disposition above (`git diff d66711d 4b8ccad`).
- **Ran (EXECUTED, darwin-arm64).** Outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev027/confirm/`. I wrote nothing in the repository but this section, and did not commit or stage it.
  - `rec.sh`: Decision 2's TERM rule. The trap only records the signal; the loop prints and exits after the step returns. I sent TERM to the driver during a 2 s step that then exits 0, under dash, bash and `zsh --emulate sh`.
  - `sh -c 'exec 3>&1; sh -c "[ -e /dev/fd/3 ] …"'`: whether a step inherits the saved fd 3.
  - Decision 6's time-left sum with a step running past its estimate.

### Each disposition against its finding

1. **The `curl` check: closed.** READ: Decision 8 drops `curl`, and Decision 9 checks it in `get`. `command -v curl` inside `00_download.sh` is allowed by `fetch_hits`, which exempts that file.
2. **Every exit path: closed, with condition C.** EXECUTED (`rec.sh`): under all three shells the trap waits for the step, the step's status is 0, and the driver then prints its line and exits
   143. Decision 2 can be built as written, and criterion 2's TERM case reflects what shells do. The ticker's `set +e`, `kill -0` check, failed-write exit and EXIT trap are written, and criterion 2 checks them with bounded reads.
3. **A check that the ticker drew: closed.** READ: criterion 1 has the frame handshake, runs with and without `timings.tsv`, and on 80 and 30 columns.
4. **Glyphs: closed.** READ: glyphs appear only in the status line, and permanent lines differ from plain only by SGR. The locale variables and their order are named.
5. **Width: closed, with condition A.** One line cut to width − 1 cannot wrap. But where fd 3 is opened is a new problem (A).
6. **Criterion 3: closed, with condition E.**
7. **The test method: closed, with condition E.** READ: Decision 10.
8. **The staleness warning: closed by removal.** It is gone from Decision 7 and listed in Scope.
9. **`--resume`: closed, with condition C.** The columns, statuses and newest-run rule are written.
10. **Criterion 4: closed.** READ: the order of the `ERROR:` line, the indented and no-match logs, the exact tail lengths, the `::error` placement and its `%25`, and `red` on the screen.
11. **The download lines: closed, with condition D.**
12. **The preflight: closed.** READ: 2.5 GiB, checked only on a first build, `df -Pk` on the nearest parent, `gzip`, `stty` and `df` added, no litter warning.
13. **Formats: closed, with condition B.**
14. **One `^ERROR` line: closed.** READ: the header starts `FAILED`, and the Kind names spec 003 and the README.
15. **One status line: taken, and sound.** No log text reaches the live line. The cursor never moves up. The tail is in Scope.

### Conditions left (each a sentence; none changes the design)

- **A. fd 3 reaches the steps, and only in terminal mode.** EXECUTED: after `exec 3>&1`, a child `sh` sees `/dev/fd/3`. If `build.sh` saves the terminal on fd 3, each step in terminal mode holds an extra descriptor to the terminal, which plain mode does not give it. That breaks Decision 2's "same in every mode". A step, or a stray process a step leaves behind, could also write past its log or keep the pty open. Fix: the ticker runs `exec 3>&1` as its own first line (its stdout is the terminal), so `build.sh` and the steps never hold fd 3. Criterion 3 should also record the step's open descriptors (`ls /dev/fd`). In plain mode no ticker runs, so `stty size <&3` is never reached there.
- **B. The estimate's edge cases.** EXECUTED arithmetic: a running step at 50 s against a 10 s estimate, as the last step, gives `0 + 10 − 50 = −40` s left. Fix: clamp the running step's term at 0. Use max(estimate, 1) in the ten-times rule, because step 90's newest time is 0 s and would drop the estimate at once. "Remaining" means this run's steps. Write the overall counter as `[k/N]`, with N this run's step count, not `[k/11]` (`--from 60` runs 4 steps). Criterion 1 then reads `[k/N]`.
- **C. A signal between steps, and `--resume` after it.** Decision 2 handles a signal only "when the running step returns". A signal that arrives between steps, or in the preflight, runs its trap at once. Fix: the loop checks the recorded signal before starting each step. For criterion 2's TERM case (`ok`, then `INTERRUPTED`), say which step `INTERRUPTED` names: the next one, not started. Then append a row `<that step> interrupted 0`. Without that row the newest run's last row is `ok`, and `--resume` says `nothing to resume` after a build that stopped early.
- **D. The download summary must keep `shasum`'s failure.** To count the `OK` lines, the script must not pipe `shasum -c` into `tee`, `grep` or `wc` under `sh`, which has no `pipefail`: a mismatch would then pass. Fix: write `shasum`'s output to a file under `build/` with its status kept (`set -e` still sees the exit code), then `cat` and count it. `scan.download_script_errors` stays satisfied, since nothing writes `SHA256SUMS`.
- **E. `BUILD_CLOCK` and the "alone" run.** The test's explicit environment holds `BUILD_CLOCK`, and every step inherits it. Criterion 3 stays equal only if the "alone" run uses that same environment plus the four exports; say so. The ticker's elapsed time must come from its own `date +%s` reading at its start, not from `progress_clock`. Under a counting clock that mix gives nonsense, which matters only for display but would confuse a reader of the frame.

### §5.2

After A to E, nothing is left to the build.

### Verdict

**Passes for build**, once A to E are written into the specification. Each is a sentence and none changes the design. All fifteen findings are closed. The one-line status removes the riskiest machinery, and the TERM rule behaves as written under dash, bash and zsh-as-sh.

One line: the revision closes every finding; open fd 3 inside the ticker only, clamp the estimate, record a signal between steps, keep `shasum`'s status, and say which environment the "alone" run gets.

### The confirmation's conditions, written in by the author

A (fd 3 opened inside the ticker only), B (time left never below 0, estimates at least 1 s, `[k/N]`), C (the signal checked before each step, recorded `interrupted`), D (`shasum`'s output saved, never piped) and E (the alone run's `BUILD_CLOCK`) are written into Decisions 3, 6, 2, 9 and criterion 3.
