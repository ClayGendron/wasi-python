# Review of 019 — The command line (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change. I did not write the
  specification's pre-build review or its confirmation either; another agent did. I read
  `AGENTS.md`, the constitution (§3, §4, §4.9, §4.15, §5.2, §7), `context/reviews/README.md`,
  the 018 build review (for its format), specification 019 with its landing notes, its pre-build
  review with both confirmations, and the diff. I also read the runner's Ctrl-C and `cancel`
  code (`_deferred_ctrl_c`, `_shared`, `_epoch_answer`, `_check_inputs`, `_text`) and the release
  workflow's `verify` job. I did not rely on the landing notes. Each claim is labelled EXECUTED,
  READ or INFERRED.
- **Reviewed:** the scratch clone's `git diff 067c765 1ba1b7c` (one commit, `1ba1b7c`). It
  touches `src/wasi_python/cli.py` (new), `src/wasi_python/__main__.py` (new), `pyproject.toml`
  (`[project.scripts]`), `.github/workflows/release.yml` (the fresh-wheel step),
  `tests/unit/test_cli.py` (new), `tests/checks/test_v1_4_embedding.py` (three checks),
  `README.md` (*From any language*), `CHANGELOG.md` and the specification.
- **Re-ran (EXECUTED, darwin-arm64, macOS 25.5, host CPython 3.14.2, uv 0.9.22, Node 22.14.0;
  the main tree's `build/artifacts` and `build/cwasm-cache`, read only).** Probes and outputs are
  under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev019b/`:
  `pytest-full.txt`, `argv.py` → `argv.txt` (36 command lines through the installed script),
  `ctrlc.py` → `ctrlc-built.txt` and `ctrlc-nocancel.txt` (SIGINT from outside), `bg-job.txt`
  (the Ctrl-C checks as a background job), `w1/`, `w2/` (two wheel builds), `fresh.sh` →
  `fresh.txt` (the workflow's step under `bash -eo pipefail`) with two mutants, `mut/` (16 mutants
  of `cli.py` and the old runner, `mutations.txt` and one log each), `dupes.py` → `dupes.txt`,
  `node/example.mjs` → `node/example.txt`, `secret.txt`, `fuel-cancel.txt`.
  - `uv run pytest -p no:cacheprovider` in the clone → `wasi_python v1: 170/181 pass · 0 gap ·
    11 blocked · 0 fail (unit suite 401/409, 8 skipped)`; v1.4 `69/69`; `571 passed, 19 skipped`;
    ratchet vs `f2a7a07f47`: `lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 3 · grew 0 ·
    judge changed: pyproject.toml, tests/checks/test_v1_4_embedding.py, tests/unit/test_cli.py`;
    **exit 0**. I did not pass `--accept`.
  - `uv run ruff check src tests` → all checks passed; `uv run ruff format --check src tests` →
    52 files already formatted.
  - I did not commit or push. The clone's `git status` was empty before and after, at `1ba1b7c`.
    I wrote nothing in the main tree. The wheels were built in two fresh clones of the clone, not
    in the clone.

## Decisions against the code

### Decision 1: the argv scan

- **The scan (READ, EXECUTED).** `_split` is one left-to-right scan. `--` first gives the rest
  to the guest. An argument starting with `-` (not `-` itself) is this command's option. One of
  `VALUED` consumes the next argument unless written `--name=value`. Anything else starts the
  guest's argv. The unit cases pass, and `argv.txt` shows the real command:

  | command line (after `wasi-python`) | exit | what happened |
  |---|---|---|
  | (nothing), `walk`, `RUN` | 2 | `the one command is run` on stderr, stdout empty |
  | `-h`, `--help` | 0 | a two-line usage on stdout |
  | `run -h` | 0 | argparse's help on stdout |
  | `run -- -h` | 0 | the guest got `["-h"]` (the guest's own `exit_code` is 2) |
  | `run -` | 0 | the guest got `["-"]` and empty input |
  | `run` | 0 | an empty argv; an empty program ran |
  | `run --env` (last) | 2 | `argument --env: expected one argument` |
  | `run --env -- -c 1` | 2 | the same: `--env` consumed `--` |
  | `run --stdin` (last) | 2 | the same for `--stdin` |
  | `run x.py --fuel 5` | 0 | the guest got all three; no fuel trap, so `--fuel` was not taken |
  | `run -- -c "…" -- --fuel 5` | 0 | the guest's `sys.argv` is `['-c', '--', '--fuel', '5']` |
  | `run --no -- …`, `run --no-snapshot=1 -- …` | 2 | no abbreviation; no value for a flag |
  | `run --env -X=1 -- …` | 2 | a value starting with `-` needs `--env=-X=1` (which exits 0) |

- **`--stdin -` (EXECUTED).** With `/dev/null` the guest reads `''`. With `print(6*7)` piped in,
  `--stdin - -- -` prints `42`. Without `--stdin -`, piped input is never read (`run -- -` with
  the same input printed nothing). With file descriptor 0 closed, exit 1 with
  `{"error": "'NoneType' object has no attribute 'buffer'", "kind": "AttributeError"}`; that is
  exit 1 as Decision 4 says, in unclear words (finding 6).
- **Limits (EXECUTED).** `--fuel NONE` and `--memory-bytes 1e9` exit 2. `--fuel -1`,
  `--deadline-s nan`, `inf` and `0` exit 1 with `run()`'s message. `--fuel 1_000` and
  `--fuel " 5 "` are accepted, as `int()` accepts them; harmless.

### Decision 2: no added power

- **One option, one argument (READ, EXECUTED).** The four limits default to `argparse.SUPPRESS`
  and are passed only when given. `env`, `stdin` and `snapshot=False` are passed only when given.
  No option reaches `root`, `grants`, `host`, `cache_dir` or `artifacts`. The guest's environment
  is only what `--env` names. A mutant that defaults the limits to `None` (which would remove the
  deadline and caps) fails `test_an_option_not_given_is_not_passed` (M8).
- **The unset `cancel` changes nothing else (READ, EXECUTED).** `run()` only type-checks it,
  checks it in the epoch callback and at waits, and starts the ticker for it. `fuel_used` for
  `print(1)` varies run to run by about 0.1% with or without it, and with a fixed hash seed too
  (`fuel-cancel.txt`), so `cancel` adds no measurable difference.
- **`--env KEY` from the environment (EXECUTED).** `--env SECRETKEY` passed the value. An unset
  key exits 2 and names the key only. A value that is not UTF-8 (`sk-very-secret-\xff-tail`)
  exits 1 with `env value for 'BADSECRET': not valid UTF-8 (a lone surrogate)`; the value is in
  neither stream (`secret.txt`). `--env =v` exits 1 with `env key: illegal environment variable
  name`. One edge echoes a secret (finding 7).

### Decision 3: the output line

- **The Intent's line, exactly (EXECUTED).** From the freshly installed wheel and from the
  clone's script: `{"exit_code": 0, "fuel_used": null, "stderr": "", "stdout": "1\n",
  "trapped": null, "truncated": []}` plus `\n`. One write of ASCII bytes to `sys.stdout.buffer`,
  flushed. Sorted keys and `ensure_ascii` are checked: mutants M3 (not ASCII) and M6 (unsorted)
  fail. `\xff` output becomes `stdout_base64` (the unit case, and M11 fails without it).
- **Growth (EXECUTED).** 1,000 bytes of `\x01` become 6.0 times as long in the line, `\n` 2.0
  times, `é` 3.0 times. The README says "about 5.4 times" (finding 8).

### Decision 4: exit codes

- **0, 1, 2 (EXECUTED).** As in the table above. Exit 2 always leaves stdout empty; exit 1
  writes one sorted, ASCII error line. `--help` exits 0.
- **130 and Ctrl-C from outside (EXECUTED, `ctrlc-built.txt`).** A child running the installed
  `wasi-python run --deadline-s none -- -c "while True: pass"`, in its own session:

  | SIGINT | exit | stdout | time from the signal to the exit |
  |---|---|---|---|
  | `os.kill` at 3 s, the guest computing | 130 | empty | 0.55 s |
  | `os.killpg` at 3 s (as a terminal sends it) | 130 | empty | 0.55 s |
  | `os.kill` at 3 s, the guest in `time.sleep(10**6)` | 130 | empty | 0.56 s |
  | `os.kill` at 0.05 s to 1.5 s (six delays) | 130 each | empty | ≤ 0.57 s |
  | `os.kill` at 0.01 s (interpreter start-up) | 1 | empty | a `KeyboardInterrupt` traceback |
  | Node's `child.kill("SIGINT")` at 3 s (`node/example.txt`) | 130 | empty | — |

  The times are benchmark facts, not assertions. A stand-in without `cancel` (`nocancel/`) ran
  past a 20 s fail-safe under `--deadline-s none`, and under the default deadline answered 130
  only after 57.7 s. So the unset `cancel` is what makes Ctrl-C work, as Decision 2 says.
- **Other `BaseException`s (READ, INFERRED).** The runner raises no `SystemExit` (READ, `grep`).
  The command binds no host function, so no host code can raise one into `run()`. A guest's
  `sys.exit` is an `exit_code`. So `KeyboardInterrupt` is the only non-`Exception` that `run()`
  can raise here, and it is caught. Outside the `try`, one can still escape (finding 4).

### Decisions 5 and 6: wasmtime and the entry point

- **No wasmtime (EXECUTED).** The wheel installed without `[run]`: exit 1,
  `{"error": "wasi_python.run needs wasmtime-py: pip install \"wasi-python[run]\"", "kind":
  "ImportError"}`.
- **`python -m wasi_python` (EXECUTED).** `run --fuel 1000 -- -c "print(1)"` gives
  `"trapped": "out of fuel"`; no arguments exits 2.

## The entry point and the wheel

- **Built as the release builds it (EXECUTED).** Two fresh clones of the clone (`w1/`, `w2/`),
  the main tree's artifact set copied into `src/wasi_python/artifacts`, then
  `uv build --wheel --build-constraints release/build-constraints.txt --require-hashes` with
  `SOURCE_DATE_EPOCH=1767225600` and `UV_BUILD_CONSTRAINT` set; `w2` under `umask 077`.
  Both exit 0. `cmp` → the same bytes, sha256
  `b6f7f196639ff5e4699893f745ec41c9b021b852eebaffcf1bff602d55e4a783`, 38,789,038 bytes.
- **`entry_points.txt` is host-neutral (EXECUTED).** Exactly
  `[console_scripts]\nwasi-python = wasi_python.cli:main\n`. The wheel holds `cli.py` and
  `__main__.py`; no launcher is in it.
- **Installed fresh (EXECUTED).** `uv run --isolated --no-project --with "wasi-python[run] @
  ./<wheel>" wasi-python run -- -c "print(1)"` with `WASI_PYTHON_ARTIFACTS=""` (the wheel's own
  set) printed the Intent's line. The script came from uv's ephemeral environment.
- **The workflow's new shell (EXECUTED, `fresh.sh`).** Copied verbatim and run under
  `bash --noprofile --norc -eo pipefail`, which is what `shell: bash` runs on Actions:
  - as written: the line, then exit 0;
  - with `print(2)`: `the installed command printed another line`, exit 1;
  - with `walk` for `run`: the usage on stderr, and `-e` stops the step at the assignment, exit 2.

  The quoting of `want` is right. In single quotes `\n` stays the two characters backslash and
  `n`, which is what the JSON line holds. `$(…)` strips only the final newline, so a `\r\n` line
  ending on Windows would leave a `\r` and fail the comparison, as it should.

## Windows (READ, INFERRED)

- **The installed-script check.** `uv run pytest` in `verify` installs the project editable, and
  uv makes `Scripts\wasi-python.exe`. `sysconfig.get_path("scripts")` names `.venv\Scripts`, and
  `shutil.which` tries `PATHEXT`'s extensions, so it finds the `.exe` (INFERRED). The comparison
  is of bytes; the command writes `\n` through the binary buffer on every host (READ).
- **`signal.raise_signal(SIGINT)` in the child.** On Windows it calls the C runtime's `raise`,
  which runs CPython's C handler at once on the raising thread. That handler marks the signal
  tripped, and the main thread runs the Python handler at its next check. A fresh Windows
  process starts with the CRT's default disposition, so CPython installs `default_int_handler`.
  `_deferred_ctrl_c` then swaps in `_note_ctrl_c`. The epoch callback is Python, on the main
  thread, so it sees the flag and stops the guest within `CANCEL_TICKS` (INFERRED from READ).
  That is the same chain as spec 015's `test_ctrl_c_while_the_guest_runs_ends_the_call[computes]`,
  which passed on `windows-2025` in dry run 39039835209 (READ, spec 015's landing notes).
- **Will `verify (windows-2025)` pass?** INFERRED yes, for the three new checks and the
  fresh-wheel step. Two caveats: the unit file `test_cli.py` is not in `verify`'s list
  (finding 3), so Windows never runs it; and the background-job failure of finding 1 is POSIX
  only (Windows has no inherited `SIG_IGN`).

## The checks

- **They count (READ).** Every assertion is on exit codes, bytes, keys and argument lists. The
  Ctrl-C check's `time.sleep(1)` is a trigger. It asserts `exit 130` and that the second call
  printed nothing; it never asserts a duration. `_child`'s 120 s timeout is a fail-safe. The
  `--deadline-s 0.5` case asserts the outcome `"deadline"`. §4.9 holds.
- **Seen failing first (EXECUTED).** With `067c765`'s `src/wasi_python` first on `PYTHONPATH`:
  `tests/unit/test_cli.py` fails to collect, and all three v1.4 checks fail.
- **Mutants (EXECUTED, `mut/mutations.txt`).** Each mutant is a copy of `src/wasi_python` first
  on `PYTHONPATH`, running `test_cli.py` and the three v1.4 checks (22 tests; the unmutated
  copy passes 22):

  | # | mutation | result |
  |---|---|---|
  | M1 | `allow_abbrev=True` | **survives** (finding 2) |
  | M2 | `cancel` not passed | caught: 2 unit cases, and the Ctrl-C check at its 120 s fail-safe |
  | M3 | `ensure_ascii=False`, UTF-8 bytes | caught: `test_the_result_line` |
  | M4 | `print(line, end="")` instead of the buffer | survives on macOS, as expected: the bytes are the same here; on Windows the installed-script check and the fresh-wheel step would see `\r\n` (INFERRED) |
  | M5a | "the one command is `run`" on stdout | caught (2 cases) |
  | M5b | argparse's messages on stdout | caught (4 cases) |
  | M6 | `sort_keys=False` | caught (3 checks, both v1.4 line checks included) |
  | M7 | `KeyboardInterrupt` caught as an error (exit 1) | caught (unit and v1.4) |
  | M8 | limits default to `None`, not absent | caught |
  | M9 | `--fuel=5` consumes the next argument | caught |
  | M10 | `--env` of an unset key passes `""` | caught |
  | M11 | `errors="replace"`, no base64 | caught |
  | M12 | the error to stderr, not a JSON line | caught |
  | M13 | an unknown option starts the guest's argv | caught (2 cases) |
  | M14 | `--help` exits 2 | caught |
  | M15 | `--stdin -` passes `b""` | **survives** (finding 2) |
  | M16 | a lone `-` is an option | **survives** (finding 2) |

- **Duplicate module-level names (EXECUTED, `dupes.py` → `dupes.txt`).** An AST scan of every
  module under `tests/`, `src/`, `scripts/` and `release/` for a top-level name bound twice (a
  function, class, plain or annotated assignment, or import; subscript and attribute targets
  excluded) finds **none**. On a copy of the v1.4 file with `COMMAND_CTRL_C` renamed back to
  `CTRL_C` (the rebase bug) it finds `CTRL_C` at lines 548 and 1251. `ruff check` with this
  repo's rules (`E, F, I, UP, B`) passes that copy: F811 covers a redefined function or import,
  not an assignment. So a judge rule would have caught the bug that ruff missed (finding 9).

## The docs

- **README *From any language* (READ, EXECUTED).** The shell example's line is exact. The
  TypeScript example, run as written in Node 22 (`node/example.txt`): status 0 logs the parsed
  object; status 1 logs `run()`'s message. Status 2 and 130 do nothing at all, and the usage
  message on stderr is never read. A missing command crashes the Node process with an unhandled
  `'error'` event (finding 5). Chunk-wise `out += chunk` is safe, since the line is ASCII. The
  child's stdin is an open pipe, but the command never reads it without `--stdin -`, so it does
  not hang (EXECUTED above). On Windows, `spawn("wasi-python", …)` without a shell finds
  `wasi-python.exe`, since libuv tries `.com` and `.exe` (INFERRED from libuv's documentation).
- The README groups only three limits as "a number, or `none`"; `--fuel none` works too
  (READ: `--fuel` is parsed by the same `_limit(int)` as `--memory-bytes`, whose `none` the unit
  case passes). Trivial.
- **CHANGELOG (READ).** One entry under 0.1.0a3, unreleased. Accurate.
- **The specification's text (READ).** The Design says "argparse with one subparser,
  `allow_abbrev=False` on both", and "the `verify` file list gains `tests/unit/test_cli.py`". The
  build has one parser and a hand check for `run` (the same behaviour, EXECUTED for no command,
  `walk` and `RUN`), and does not add the file to `verify` (findings 3 and 10).

## Acceptance criteria against evidence

1. *The checks exist and were seen failing before the change.* **Met** (EXECUTED: the old
   runner fails all of them). Three named properties have a check that cannot fail (finding 2).
2. *`uv run pytest` is green with `--accept-judge`.* **Met as far as can be seen without
   accepting:** exit 0, lost 0, grew 0, the judge changed in the three named files (EXECUTED).
   But the new Ctrl-C check fails when the judge runs as a background job (finding 1).
3. *A release dry run passes every job, and `verify` runs the command from the fresh wheel on
   Linux, macOS and Windows.* **Not met yet; not run.** The step is there and its shell works
   under `bash -eo pipefail` (EXECUTED on macOS). As with 017, this can wait for the release.

## Findings, most severe first

1. **Medium. The new Ctrl-C check fails whenever the judge's parent ignores SIGINT**
   (`tests/checks/test_v1_4_embedding.py:1251`).
   - The child script never sets a SIGINT handler. A POSIX process started with SIGINT ignored
     keeps `SIG_IGN`, so CPython installs no `default_int_handler`. A non-interactive shell's
     background job (`cmd &`) and `nohup` start it so. Then `raise_signal(SIGINT)` is ignored,
     `_deferred_ctrl_c` defers nothing, and the guest loops on.
   - Failure (EXECUTED, `bg-job.txt`): `sh -c 'python -m pytest … & wait'` → a child's
     `signal.getsignal(SIGINT)` is `1` (`SIG_IGN`); `test_ctrl_c_stops_the_command_with_130`
     fails at `subprocess.TimeoutExpired` after 120 s. In the same run, spec 015's two Ctrl-C
     checks pass, because their script sets the handler first ("as in a plain script").
   - Fix: the script's first lines are
     `import signal` and `signal.signal(signal.SIGINT, signal.default_int_handler)`, as spec
     015's `CTRL_C` does. The command's own behaviour is right as it is: a background job should
     ignore Ctrl-C.
2. **Medium-low. Three named properties have checks that cannot fail**
   (`tests/unit/test_cli.py:74-83`, `:106`, `:38`).
   - **Abbreviations.** The case `--dead 1` is meant to show "an abbreviation is never taken".
     It exits 2 for another reason: `--dead` is not in `VALUED`, so the scan gives `1` to the
     guest, and argparse sees `--dead` with no value. With `allow_abbrev=True` (M1) every check
     passes, and `run --dead=1 -- -c 1` and `run --no -- -c 1` then exit 0 with `deadline_s` and
     `snapshot` set (EXECUTED, `mut/abbrev-probe.txt`).
   - **A lone `-`.** The confirmation's C2 asked for a unit case `run -` → guest `["-"]`, and its
     Disposition says "a unit case for each". There is none; M16 (a lone `-` is an option, so
     `run -` exits 2) passes every check.
   - **`--stdin -`.** No check gives the command input. M15 (`--stdin -` passes `b""`) passes.
   - Fix: add `["run", "--dead=1", "--", "-c", "1"]` and `["run", "--no", "--", "-c", "1"]` to
     the usage-error cases; add `(["-"], ["-"])` to the split cases; add a unit case that sets
     `sys.stdin` to `io.TextIOWrapper(io.BytesIO(b"x"))` (with `monkeypatch`) and expects
     `stdin == b"x"`. Each mutant above then fails.
3. **Low-medium. `verify` does not run `tests/unit/test_cli.py`, which the Design says it does**
   (`.github/workflows/release.yml:243`).
   - Failure: the parsing and byte-output unit cases never run on Linux or Windows. Only the
     three v1.4 checks do. A Windows-only difference in `_write` or in argparse would be caught
     only by the installed-script line check.
   - Fix: add `tests/unit/test_cli.py` to the `verify` step's file list, as the Design says. Or
     change the Design and say why not.
4. **Low. A Ctrl-C outside the `run()` call escapes `main` as a traceback**
   (`src/wasi_python/cli.py:106-153`).
   - Only `runner.run` and the `--stdin` read are inside the `try`. A SIGINT during parsing or
     during `_write` raises `KeyboardInterrupt` out of `main`: a traceback on stderr and exit 1,
     not 130. During `_write` of a long line it can also leave part of a line on stdout. The
     window is small. EXECUTED only at start-up, which `main` cannot cover: SIGINT at 0.01 s
     gave exit 1 and a traceback. The rest is INFERRED from READ.
   - This also makes the check's docstring ("either way the answer must be 130") slightly too
     strong.
   - Fix: wrap the body of `main` from the parse onwards in one `try/except KeyboardInterrupt:
     return 130`. Only interpreter start-up and import are then left. That is CPython's, and it
     prints nothing on stdout.
5. **Low. The README's TypeScript example ignores 2, 130 and a missing command**
   (`README.md:393-396`).
   - Failure (EXECUTED, `node/example.txt`): status 2 (`--dead 10`) and 130 (`kill("SIGINT")`)
     print nothing. The usage message on stderr is never read. Spawning a name that is not
     installed throws `Unhandled 'error' event … ENOENT` and exits Node with 1. The README calls
     its examples the contract, so a caller that copies it gets silence on a usage error.
   - Fix: add `child.on("error", (e) => console.error(e.message));`, collect `child.stderr`, and
     end with `else console.error(\`wasi-python exited ${status}\`, err);`.
6. **Low. `--stdin -` with no standard input gives an unclear error** (`cli.py:132`).
   - Failure (EXECUTED): fd 0 closed → exit 1, `"'NoneType' object has no attribute 'buffer'"`,
     `"kind": "AttributeError"`. Exit 1 is right; the words do not say what went wrong.
   - Fix: when `sys.stdin is None`, raise `OSError("--stdin -: this command has no standard
     input")`. Optional.
7. **Low. `--env NAME` of an unset name echoes what the caller typed**
   (`cli.py:88`).
   - Failure (EXECUTED): `--env s3cr3t-typed-as-key` exits 2 with
     `--env s3cr3t-typed-as-key: not set in this command's environment` on stderr. A caller who
     writes `--env "$TOKEN"` by mistake, forgetting `KEY=`, gets the token into whatever logs
     stderr. The argument was already in `ps`, so the new exposure is to logs only.
   - Fix: name it only when it looks like a variable name (`[A-Za-z_][A-Za-z0-9_]*`). Otherwise
     say `--env: an argument without "=" must name a variable set in this command's
     environment`. Optional.
8. **Low. "About 5.4 times" understates the line's growth** (`README.md:414`, and the
   specification's Design).
   - EXECUTED: 1,000 bytes of `\x01` give a JSON string 6.0 times as long. The specification's own
     190 MiB at the defaults already uses six (two 16 MiB streams × 6).
   - Fix: "up to 6 times".
9. **Low. A judge rule for duplicate module-level names is worth adding.**
   - No duplicates exist today (EXECUTED). But this change's own rebase lost two accepted passes
     to a silent redefinition (`CTRL_C`), and ruff did not catch it (EXECUTED above). The ratchet
     caught it only because those checks had passed before. A new check that shadows an old
     script on its first landing would not be caught.
   - Fix: a unit check in the judge (for example in `tests/unit/test_scan.py`) that parses each
     `tests/**/*.py` and fails on a top-level name bound twice by an assignment, function or
     class. `dupes.py` is the shape; it runs in milliseconds. It is a judge change, so it is its
     own change with its own reason, not part of this landing.
10. **Low. The specification's text and the build differ in two places.**
    - Design: "argparse with one subparser, `allow_abbrev=False` on both". Built: one parser, and
      `main` checks `run` itself. The behaviour is the one Decision 1 asks for (EXECUTED).
    - Design: "The `verify` file list gains `tests/unit/test_cli.py`" (finding 3).
    - Fix: one sentence in the landing notes for the first; finding 3's fix for the second.

## Constitution checks

- **§3:** holds. One command runs one program and prints its result. Each option is one `run()`
  argument; the always-passed `cancel` is unset and changes nothing measurable (EXECUTED).
- **§4.5:** holds. The README names Node and TypeScript, no framework or embedder.
- **§4.9:** holds. The checks assert exit codes, bytes and arguments. The 1 s sleep is a trigger;
  the 120 s timeout is a fail-safe. No test measures time.
- **§4.10:** the landing notes' numbers match my run (170/181, v1.4 69/69, unit 401/409, lost 0).
- **§4.13:** holds. `argparse` is the standard library. No dependency is added; `uv.lock` is
  untouched (READ).
- **§4.15:** holds. An option not given is absent, so `run()`'s defaults apply; M8 shows the
  check guards it. `none` loosens a limit only when asked, as `run()` allows.
- **§5.2:** every choice is decided; two Design sentences differ from the build (finding 10).
- **§7:** nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

Every finding is taken, fixed in the clone on `1ba1b7c` (uncommitted, staged); the
specification's landing notes gain "Revised against the build review".

1. **Fixed as suggested:** `signal.signal(SIGINT, signal.default_int_handler)` at the top of
   `COMMAND_CTRL_C`. EXECUTED: the v1.4 Ctrl-C checks pass run as `sh -c '… & wait'`.
2. **Fixed:** unit cases for `--dead=1` and `--no` (exit 2), a lone `-`, `--stdin -` reading the
   command's input, and a closed standard input.
3. **Fixed:** `verify` runs `tests/unit/test_cli.py`.
4. **Fixed:** `main` wraps the whole command; a Ctrl-C anywhere is 130 with nothing on stdout (a
   case interrupts the scan).
5. **Fixed:** the TypeScript example handles `'error'`, and statuses 2 and 130.
6. **Fixed:** a closed standard input is exit 1, "--stdin -: this command's standard input is
   closed".
7. **Fixed:** an unset `--env` name is reported by position ("--env number 1"), never echoed; a
   case checks the typed text is absent from standard error.
8. **Fixed:** "up to 6 times".
9. **Left, named:** a duplicate-name rule is its own judge change (recorded in the landing notes).
10. **Answered:** the landing notes say one parser checks `run` itself; behaviour as specified.


## Verdict

**Does not land yet.** The command is right. Each Decision holds as built. Ctrl-C from outside
stops a computing guest with 130. The wheel is reproducible and its installed command prints the
Intent's line. But the judge needs two small fixes first. The new Ctrl-C check fails under a
background job (finding 1, one line). Three named properties have checks that cannot fail
(finding 2, four cases). Findings 3 to 10 are small, and each can be fixed or answered in
writing. A confirmation that reads the revised diff and re-runs the mutants M1, M15 and M16 and
the background-job run is enough.

One line: a correct thin command; fix the Ctrl-C check's signal handler and give three checks
teeth, then it lands.

## Confirmation

- **Date:** 2026-10-17. **Reviewer:** the same fresh agent. I read the staged revision
  (`git diff --cached` on `1ba1b7c`: `cli.py`, `test_cli.py`, the v1.4 Ctrl-C script,
  `release.yml`, `README.md`, the specification's landing notes) and the Disposition above.
- **Ran (EXECUTED, same machine and settings as above).** Outputs are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev019b/confirm/`.
  - `uv run pytest -p no:cacheprovider` in the clone → `170/181 pass · 0 gap · 11 blocked ·
    0 fail (unit suite 407/415, 8 skipped)`; v1.4 `69/69`; `577 passed, 19 skipped`; ratchet vs
    `f2a7a07f47`: `lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 3 · grew 0 · judge
    changed: pyproject.toml, tests/checks/test_v1_4_embedding.py, tests/unit/test_cli.py`;
    **exit 0** (`pytest-full.txt`). Six unit cases more than before; nothing else moved.
  - `ruff check src tests` → all checks passed; `ruff format --check` → 52 files formatted.
  - I did not commit or push. The clone's status is the six staged files and nothing else. I
    wrote nothing in the main tree.

### The four probes asked for

1. **The background job (finding 1) — closed.** `sh -c '… & wait'`: a child's SIGINT handler is
   still `1` (`SIG_IGN`), and now `test_ctrl_c_stops_the_command_with_130` and spec 015's two
   Ctrl-C checks pass, 3 of 3 (`bg-job.txt`). Before the fix this check failed at 120 s.
2. **The `allow_abbrev` stand-in (finding 2) — closed.** `allow_abbrev=True` now fails the new
   cases `--dead=1` and `--no` (`mutations.txt`, M1).
3. **The `--stdin -` mutant (finding 2) — closed.** Passing `b""` for `--stdin -` fails
   `test_stdin_dash_is_this_commands_input` (M15). A lone `-` taken as an option fails the new
   split case (M16).
4. **Node with a missing command (finding 5) — closed.** The README's example, extracted from
   the README as it now stands and run in Node 22 (`readme-example.ts`, `example.mjs`,
   `node.txt`): a missing command prints `wasi-python could not start: spawn … ENOENT` and Node
   exits 0, no crash. Status 2 prints `wasi-python exited 2`; Ctrl-C (`kill("SIGINT")`) prints
   `wasi-python exited 130`; 0 and 1 are as before. Two trivial residues, not blocking: after
   ENOENT, `close` also fires and prints `wasi-python exited -2` (a negative errno, not a
   status); and on a usage error the example still does not show the command's stderr, so the
   reader sees "exited 2" without the reason.

### The other findings

- **3 — closed.** `verify`'s pytest line now ends in `tests/unit/test_cli.py`; parsed as YAML,
  the folded scalar is one command with the file last (EXECUTED). The unit file needs no
  artifacts and no wasmtime (READ), so it runs on all three hosts.
- **4 — closed.** `main` wraps `_main` in `except KeyboardInterrupt: return 130`, and the inner
  `except Exception` no longer sees it. `test_ctrl_c_while_parsing_is_130` interrupts the scan.
  The mutant that drops the outer handler (M17) makes pytest itself stop with
  `KeyboardInterrupt` and exit 2, so the run is red. From outside, SIGINT at 0.05 s to 1.5 s
  gives 130 and an empty stdout every time; at 0.01 s the process dies by the signal (`-2`)
  before Python's handler exists, with nothing on stdout, which is start-up and not the
  command's (`ctrlc-built.txt`).
- **6 — closed.** fd 0 closed → exit 1,
  `{"error": "--stdin -: this command's standard input is closed", "kind": "OSError"}`. The
  case fails when the check is removed (M18).
- **7 — closed.** An unset name is reported as `--env number 1: no such name in this command's
  environment`; the typed text is in neither stream (`argv.txt`), and a mutant that echoes it
  fails `test_a_missing_env_name_is_never_echoed` (M19).
- **8 — closed.** The README says "up to 6 times".
- **9 — answered.** Left for its own judge change and named in the landing notes; the scan still
  finds no duplicate in `tests/`, `src/`, `scripts/` or `release/`.
- **10 — answered.** The landing notes now say the build has one parser and checks `run` itself.

### Nothing new broke

- **The command (EXECUTED).** The 36 command lines of `argv.py`, re-run: identical output to the
  first run except the two intended lines (findings 6 and 7). Ctrl-C from outside, computing or
  waiting, by `kill` or `killpg`: 130, stdout empty.
- **Mutants (EXECUTED, `mutations.txt`).** The 15 earlier mutants that still apply, plus M17 to
  M19, against the revised code: all caught; the unmutated copy passes 28 of 28. M4 (`print`)
  was not re-run; it was expected to survive on macOS and still would.
- **The wheel (INFERRED).** Only `cli.py` changed in the package; `pyproject.toml` and the entry
  point did not. The earlier two-build byte equality and the fresh-wheel line still apply; I did
  not rebuild.

### Small things left

- The Disposition above ends with the template's empty `1.` to `10.` list under the author's
  answers. Delete it when landing.
- The README example's `-2` after ENOENT and its silence about stderr on exit 2 (probe 4). Optional.
- Acceptance criterion 3, the release dry run, is still to be run, as with spec 017; it does not
  block the landing.

### Verdict of the confirmation

**Lands.** Every finding is fixed or answered in writing, and each fix is checked by a case that
fails without it. The judge is green with nothing lost and nothing grown, and the four probes
that failed before now pass.

One line: the Ctrl-C check survives an ignoring parent, the checks have teeth, and the command
behaves as specified; it lands.

## Disposition of the confirmation (filled in by the author)

- The leftover empty list in the Disposition is removed.
- The README example's two optional points are left: `close` after ENOENT and a usage error's
  reason on standard error are the caller's to print; the example shows the statuses.
- Criterion 3 (the release dry run) runs at landing, with spec 017's follow-up.

Your verdict made the change land.

