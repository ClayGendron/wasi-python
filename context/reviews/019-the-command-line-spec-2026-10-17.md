# Review of 019 — The command line (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the specification. I read `AGENTS.md`, the constitution (§3, §4.5, §4.9, §4.13, §4.15, §5.2), `context/reviews/README.md`, the 017 pre-build review (for the format), question 7 in `questions-for-the-owner.md`, and spec 015's Decisions 1 and 3. In the runner I read `run`, `run_async`, `Completed`, `Defaults`, `DEFAULTS`, `_UNSET`, `_checked`, `_check_inputs`, `_text`, `_wasmtime`, `_instance`, `_drive`, `_shared`, `_epoch_answer`, `_watch`, `_deferred_ctrl_c`, `_cache_dir` and `_epoch_ticker`. I also read `src/wasi_python/__init__.py`, `pyproject.toml`, `.github/workflows/release.yml` (build, rebuild, same-bytes and verify), the README's "Running it" and "Safety" sections, and the checks in `tests/checks/test_v1_4_embedding.py`. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/019-the-command-line.md` as committed in `93efa1b`, against the runner at `177ce5c` (spec 016 landed while I reviewed; I re-ran the Ctrl-C probe on `177ce5c`, and the line numbers below are that commit's).
- **Ran (EXECUTED, darwin-arm64, macOS 25.5, host CPython 3.14.2, wasmtime-py 49.0.0, `WASI_PYTHON_ARTIFACTS` = the main tree's `build/artifacts`, read only; `WASI_PYTHON_CACHE` and `TMPDIR` in my scratch folder).**
  - The repo was not edited. Nothing was written under `build/`.
  - Scripts and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev019/`:
    - `ctrlc.py` → `ctrlc.txt`: Ctrl-C (a `SIGINT` raised on a timer) while `run()` computes on the main thread, with and without `cancel`;
    - `term.py` → `term.txt`: `SIGTERM` to a process in the middle of a call;
    - `argp.py`, `argp2.py` → `argp.txt`, `argp2.txt`: the spec's parser shape on CPython 3.11.14, 3.12.12, 3.13.11 and 3.14.2;
    - `jsonp.py` → `jsonp.txt`: Decision 3's output rule on real `Completed` values, and the two v1.4 outcomes (`deadline_s=0.5`, `fuel=1000`) through `run()`;
    - `w1/`, `w2/`, `whl1/`, `whl2/`: the wheel built twice with the `[project.scripts]` line and stub `cli.py` and `__main__.py`, then `uv lock --check` and an editable install.
  - I did not run `uv run pytest`. Nothing is built yet; the scoreboard is the build review's job.

## What holds

- **The option table adds no power.** READ. Each option names one `run()` argument. No option reaches `root`, `host`, `cache_dir` or `artifacts`. The guest's environment is only what `--env` gives, never the command's own. Without options the call is `run(argv)`: a private root and `DEFAULTS`' limits. `none` loosens a limit only when asked, as `run()` already allows, so §4.15 holds.
- **Leaving out `--root` is right.** READ (spec 017 and its review). Spec 017 changes what `root=` accepts (it is walked, and some values are refused) and adds `grants=`. Designing `--root` and `--grant` together after 017 lands means no option changes its meaning later.
- **The Intent's line is exact.** EXECUTED (`jsonp.txt`, 1). Decision 3's rule on `run(["-c", "print(1)"])` prints `{"exit_code": 0, "fuel_used": null, "stderr": "", "stdout": "1\n", "trapped": null, "truncated": []}`.
- **`stdout` never holds a lone surrogate.** EXECUTED (`jsonp.txt`, 8). Python's strict UTF-8 decoder refuses an encoded surrogate (`b"\xed\xa0\x80"` goes to `stdout_base64`). So every text value is well-formed, and a TypeScript caller's `Buffer.from(s, "utf8")` gives back the exact bytes (INFERRED). `ensure_ascii=True` makes the whole line ASCII.
- **The two v1.4 outcome checks are robust.** EXECUTED (`jsonp.txt`, 6 and 7): `deadline_s=0.5` on `while True: pass` gives `"deadline"`; `fuel=1000` on `print(1)` gives `"out of fuel"`. Both assert an outcome, not a time. A slow host only makes the deadline land earlier in the program; it is still `"deadline"`. Fuel is metered from the end of instantiation (READ, `_instance`), so 1000 can never finish a program.
- **The wheel stays reproducible.** EXECUTED. Two builds from different folders, one under `umask 077`, with `SOURCE_DATE_EPOCH=1767225600` and the pinned hatchling 1.32.4, gave the same bytes (`cmp`). The only new metadata is `entry_points.txt`, two lines with no host fact. The launcher is made at install time, not put in the wheel. `uv lock --check` passes, so `uv.lock` does not change. Across hosts this is INFERRED, but nothing host-specific is written. (Since `177ce5c` the same-bytes job compares the wheel byte for byte, so this matters.)
- **An editable install makes the script.** EXECUTED (`w1/`): `uv sync` made `.venv/bin/wasi-python`, and `sysconfig.get_path("scripts")` names that folder.
- **The package needs no lazy import.** READ: `wasi_python/__init__.py` imports `runner`, which imports wasmtime only inside `_wasmtime()` (`runner.py:703`). `test_package_imports_without_wasmtime` already guards it.
- **`--stdin -` into memory is fine.** INFERRED from READ. The caller is the trusted side and can pass the same bytes to `run()` directly. Spec 014 checks only stdin's type, and `run()` copies it to a file in a private folder. A size check would add a limit `run()` does not have.
- **A killed command's folders are swept.** EXECUTED (`term.txt`): `SIGTERM` in a call left the private root (11 MB), the stdin folder and their lock files. The next process's first call removed them (only `uv`'s own lock was left after `ctrlc.py` ran). This is spec 016's sweep.
- **Exit codes 0, 1 and 2 are sound.** A program's own exit code is never the command's, so a caller never confuses the two.

## Acceptance criteria against evidence

1. *The checks exist and were seen failing first.* Can be met. But no check covers exit 130 (finding 1), `--help`, abbreviations or a missing `--` (finding 4).
2. *`uv run pytest` is green with `--accept-judge`.* Can be met. The real-call checks need `needs.need("runner", "artifact dir")`, as `_runner()` does, so a machine without artifacts reports them blocked rather than failed.
3. *The verify jobs run the command from the installed wheel.* Not met by the Design as written (finding 2).

## Findings, most severe first

1. **High. Ctrl-C does not stop a guest that computes, so Decision 4's 130 is late or never.**
   - What the spec says: "Ctrl-C stops the guest (spec 015 already does this inside `run`)".
   - Why that is not so. READ: spec 015 sets the epoch callback only for a call with `cancel` (`runner.py:885`; 015 Decision 1: "A call without `cancel` gets no callback and is unchanged"). Without it, a deferred Ctrl-C is seen only at a wait or a door call. The command passes no `cancel` and binds no host. The README already says so ("Ctrl-C for a guest that never waits or calls the door in a call with `deadline_s=None` and no `cancel` … runs on").
   - Failure. EXECUTED (`ctrlc.txt`, on `177ce5c`): `run(["-c", "while True: pass"], deadline_s=8)` with a SIGINT at 1.5 s raised `KeyboardInterrupt` only after 8.0 s. The same call with `cancel=threading.Event()` ended at 1.5 s, and with `deadline_s=None` too at 1.6 s. So `wasi-python run -- -c "while True: pass"` ignores Ctrl-C for the default 60 s, and under `--deadline none` for ever (INFERRED from the same code: no callback, no `stop_at`).
   - Fix:
     - The command always passes `cancel=threading.Event()`, which nothing sets. It is a `run()` argument and adds no power. Spec 015's outcome 2 then turns Ctrl-C into a stop within `CANCEL_TICKS`. Decision 2 says so: one argument is always passed, for Ctrl-C.
     - `main` catches `KeyboardInterrupt` (not under `except Exception`) and returns 130 with nothing on standard output.
     - The unit check "an option not given is not passed" allows `cancel`.
     - Add two checks. Unit: a fake `run` that raises `KeyboardInterrupt` gives 130 and empty standard output. v1.4, in a child: `main(["run", "--deadline", "none", "--", "-c", "while True: pass"])` with a thread that calls `signal.raise_signal(SIGINT)` after a trigger sleep; assert exit 130 and empty standard output, with a 120 s fail-safe as `test_ctrl_c_while_the_guest_runs_ends_the_call` has. A SIGINT that lands during compilation also gives 130, so the check does not depend on timing.

2. **Medium. Acceptance criterion 3 cannot be met: nothing runs the installed wheel's command.**
   - READ (`release.yml`): the verify job runs the v1.4 checks with `uv run pytest` from the checkout. That runs the editable install's script, not the wheel's. The step "The wheel, installed fresh" calls only `wasi_python.run` through `python -c`. The spec's Kind does not list `release.yml`.
   - The entry-point check is also worded two ways: "`uv run wasi-python run …` as a subprocess" and "finds the script … through `sysconfig`". Running `uv` from inside the judge adds a nested `uv` (with `UV_LOCKED` set) that the check does not need.
   - Fix:
     - Kind lists `.github/workflows/release.yml`. The fresh-wheel step adds `uv run --isolated --no-project --with "wasi-python[run] @ ./$wheel" wasi-python run -- -c "import pandas; print(pandas.Series([1, 2, 3]).sum())"`, then parses the line and asserts exit 0 and `"stdout": "6\n"`.
     - The v1.4 check runs `shutil.which("wasi-python", path=sysconfig.get_path("scripts"))`. That finds `wasi-python.exe` on Windows through `PATHEXT` (INFERRED) and never reads the caller's `PATH`. It never calls `uv`.

3. **Medium. `--env KEY=VALUE` puts secrets where other users can read them.**
   - READ: the runner treats environment values as secrets (`runner.py:128`: "Messages name `where`, never the value: environment values are often secrets").
   - Failure. INFERRED (standard OS behaviour): a process's argv is readable by other local users through `ps` or `/proc/PID/cmdline` on Linux and macOS. An API key passed as `--env TOKEN=sk-…` is visible for the whole call. In-process `run(env=…)` has no such exposure.
   - Fix: `--env KEY` with no `=` takes the value from the command's own environment, and is a usage error when `KEY` is unset (as `docker run -e KEY` does). It still maps to `env` and adds no power. The README says to pass secrets that way. The check "`--env` without `=` exits 2" becomes "`--env` naming an unset variable exits 2".

4. **Medium. argparse's defaults break Decisions 3 and 4.** EXECUTED (`argp.txt`, `argp2.txt`; the same on all four Pythons).
   - `run --help` exits 0 and prints 460 characters on standard output. Decision 4 says exit 0 means "the call returned; the JSON says how the program ended".
   - Abbreviations are on: `--dead 1` sets the deadline, and `--no` means `--no-snapshot`. A later option (say `--no-cache`) would turn a caller's `--no` into a usage error.
   - Without `--`, options after a positional are the command's: `run x.py --fuel 5` gives the guest `['x.py']` and the command `fuel=5`. `run -c "print(1)"` exits 2.
   - `--` itself is right on these versions: `run -- -c x -- y` gives `['-c', 'x', '--', 'y']`, `run -- -- -c` gives `['--', '-c']`, and `run -- --help` gives the guest `['--help']`.
   - Fix:
     - Decision 4 names `--help` as the one exception: usage on standard output, exit 0. No program-running call can reach it, since all after `--` is the guest's.
     - `allow_abbrev=False` on both parsers.
     - Decision 1: the guest's argv is everything after the first `--`, and a positional before it is a usage error. Splitting at the first `--` before argparse sees the list keeps this exact, and independent of argparse's `--` handling, which has changed between releases (INFERRED).
     - Checks: `--help` exits 0; `--dead 1` exits 2; `run x.py` with no `--` exits 2.

5. **Medium. Several parsing choices are left open (§5.2).**
   - `_limit(text)`: "`none` → `None`, else `float` or `int`" does not say which type for which option, or what a non-number does. Example: is `--memory 1e9` a float that `run()` refuses (exit 1), or a usage error (exit 2)? Is `None` or `NONE` accepted? Fix: `--deadline` parses as `float`; `--memory`, `--output-bytes` and `--fuel` as base-10 `int`; only lowercase `none` means no limit. Text that does not parse is a usage error (exit 2). Ranges stay `run()`'s (exit 1).
   - Reading `--stdin PATH` can fail (missing file, a folder). That is not `run()`, so Decision 4 does not cover it. Fix: exit 1 with the error object (`"kind": "FileNotFoundError"`); Decision 4 reads "`run()`, or reading `--stdin`, raised".
   - `main` "returns the exit code", but argparse raises `SystemExit`. Fix: `main` catches it and returns its code, so in-process checks get an int.
   - An empty argv. EXECUTED (`jsonp.txt`, 5): `run([], stdin=b"print(6 * 7)\n")` exits 0 and prints `42`. Fix: say it is allowed, and the README shows `--stdin PATH -- -` as the way to run a long program.
   - A repeated `--env` key. Fix: the last one wins.
   - Without `--stdin`, the command never reads its own standard input. The spec implies this but should say it: a caller that leaves the pipe open must not hang. With `--stdin -`, it reads `sys.stdin.buffer` to EOF (binary, so Windows does not translate line endings).

6. **Low-medium. The wasmtime special case repeats `run()`'s own error, in worse words.**
   - READ: `run()` already raises `ImportError('wasi_python.run needs wasmtime-py: pip install "wasi-python[run]"')` (`runner.py:707`). The exit-1 path turns that into the error object with no extra code.
   - Decision 5 adds a second message, "install wasi-python[run]". It is unquoted, so pasted into zsh the brackets are a glob and fail with "no matches found" (INFERRED; zsh does this to any unmatched `[…]`).
   - Fix: drop the lazy import and the special message. The check runs in a child with `sys.modules["wasmtime"] = None`, as `test_package_imports_without_wasmtime` does, and asserts exit 1, `"kind": "ImportError"` and `wasi-python[run]` in `"error"`.

7. **Low-medium. On Windows the line ends in `\r\n`.**
   - INFERRED from CPython's standard-stream setup: on Windows `sys.stdout` turns `"\n"` into `"\r\n"`. Decision 3 says "then a newline". The entry-point check says "prints the same JSON". A byte comparison fails on `windows-2025`; a later JSON Lines batch mode would inherit the difference.
   - Fix: write `sys.stdout.buffer.write(line.encode("ascii"))`, then flush, so the bytes are the same on every host. The check compares bytes. The whole line is built before the one write, so nothing partial is printed.

8. **Low. Decision 4 does not cover a command its caller kills.**
   - A caller's timeout sends `SIGTERM` (Node's `spawn` `timeout` and `kill()`), or on Windows terminates the process. The command then prints nothing and has no exit code of its own.
   - EXECUTED (`term.txt`): the call's folders stay until the next process's first call sweeps them (spec 016).
   - Fix: Decision 4 adds: killed by its caller, nothing is printed, and the next call removes its folders. A caller that wants a result sets `--deadline` below its own timeout. "Depends on" adds 016.

9. **Low. The README must warn TypeScript callers about size and the second key.**
   - EXECUTED (`jsonp.txt`, 3 and 4): control bytes grow 5.4 times in the line, `é` 3.0 times, and base64 1.33 times. At the default 16 MiB per stream, one line can be about 190 MiB.
   - INFERRED from Node's and V8's documentation: `exec` and `execFile` stop at a 1 MiB `maxBuffer` by default, and a V8 string holds at most about 2**29 characters, which `--output-bytes none` can pass.
   - EXECUTED (`jsonp.txt`, 2): a cap that splits a character makes the whole stream `stdout_base64`, so a caller that reads only `stdout` gets `undefined`.
   - INFERRED: Linux limits one argument to 128 KiB, and Windows a command line to 32,767 characters, so a long `-c` program fails before the command starts.
   - Fix: the README's TypeScript example uses `spawn` and collects `Buffer`s. Chunk-wise decoding is safe, since the line is ASCII. It reads `stdout` or `stdout_base64`, ends the child's stdin when it uses `--stdin -`, and runs a long program with `--stdin PATH -- -`.

10. **Low. Option names differ from the names in `run()`'s errors.** `--deadline 0` exits 1 with "`deadline_s` must be …", and `--memory -1` with "`memory_bytes` must be …". Fix: the README's option table shows both names. Or name the options `--deadline-s` and `--memory-bytes`, as `--output-bytes` already is.

11. **Low. Scope's Out list names `--grant` but not `--root`.** Decision 2 explains the gap. Fix: add `--root` beside `--grant` in Out, so the later spec owns both.

## Constitution checks

- **§3:** holds. The command runs one program and prints its result. With finding 1's `cancel` and finding 3's `--env KEY`, it still adds no power `run()` lacks.
- **§4.5:** holds as drafted. The spec names languages, not embedders. The README example must stay generic too: Node's `spawn`, no framework's name.
- **§4.9:** holds. Every check named asserts exit codes, keys and bytes. The `--deadline 0.5` check asserts an outcome, not a time. Finding 1's check uses a trigger sleep, not a measurement.
- **§4.13:** holds. `argparse` is the standard library; no dependency is added.
- **§4.15:** holds. No default loosens. `none` loosens a limit only on request, as in `run()`. Finding 3 is an exposure of the caller's secrets to other local users, not a channel for the guest.
- **§5.2:** open choices are listed in findings 4 and 5: `--help`, abbreviations, the `--` rule, `_limit`'s types, a failed `--stdin` read, `SystemExit` in `main`, an empty argv, a repeated `--env`. Finding 7 (the newline bytes) and finding 8 (a killed command) are choices too.
- **§7:** nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

Each finding is taken; the specification is revised in place (status "revised against its pre-build review").

1. **Ctrl-C:** fixed. Decision 2 always passes an unset `cancel`, with your measurement as the reason; Decision 4's 130 rests on it; a v1.4 child-process check sends `SIGINT` and expects 130 and nothing on standard output.
2. **Criterion 3:** fixed. The `verify` job's fresh-wheel step runs the command from the installed wheel; the check finds the script with `shutil.which(…, path=sysconfig…)` and never calls `uv`; `release.yml` is in Kind and Design.
3. **`--env` secrets:** fixed. `--env KEY` takes the value from the command's own environment.
4. **argparse:** fixed. `--help` is the named exception; `allow_abbrev=False`; everything after the first `--` is the guest's, and without `--` everything from the first non-option.
5. **Open parsing choices:** decided. Limits parse as `float`/`int`/`none`; unparsable is exit 2, refused by `run()` is exit 1; an unreadable `--stdin PATH` is exit 1; `main` catches argparse's `SystemExit`; an empty argv is allowed; a repeated `--env` key keeps the last; the command never reads its standard input without `--stdin -`.
6. **wasmtime:** taken. No special case; `run()`'s own `ImportError` (with its quoted extra) goes through exit 1.
7. **Windows line ending:** fixed. The line is written as ASCII bytes to `sys.stdout.buffer`.
8. **Killed:** stated in Decision 4, with spec 016's sweep; 016 is in Depends on.
9. **Output size:** the README warns about the 5.4x growth, Node's `exec` limit, base64 after a cut inside a character, and long programs (`--stdin PATH -- -`).
10. **Option names:** renamed to `--deadline-s` and `--memory-bytes`, `run()`'s names.
11. **`--root`:** in the Out list beside `--grant`.

## Verdict

**Revise first.** The shape is right: one subcommand, a one-to-one option table, one JSON line, and exit codes that say whether there is a result. But Decision 4's Ctrl-C promise is false without `cancel` (finding 1). Acceptance criterion 3 has no step to meet it (finding 2). And several parsing choices are still open (findings 4 and 5). Each fix is a sentence or two. Once they are in the specification and recorded in the Disposition, a confirmation that reads the revised text is enough; no second full review is needed.

One line: a sound thin command, but pass `cancel` so Ctrl-C works, add the wheel step to verify, keep secrets off the command line, and decide the argparse rules before building.

## Confirmation

- **Date:** 2026-10-17. **Reviewer:** the same fresh agent. I read `git show 44c25a6 -- context/specifications/019-the-command-line.md` and the Disposition above, and re-read `_instance` and `_Stream` in `runner.py` at `7dc59fd`.
- **Ran (EXECUTED, same machine and settings as above):** `stream.py` → `stream.txt` in the scratch folder named above. A child process ran a guest that printed `started` to its stderr with `flush=True`, then looped. Four seconds in, inside its 5 s deadline, the child's own stderr held `b''`. After the call it still held `b''`.

### What the revision closes

- **Findings 2, 3, 5 to 11 are closed** by the text, as the Disposition says. Some notes:
  - **`--env KEY` from the environment holds.** It maps to `env` and reads only the keys the caller names. A missing key is exit 2, and argparse's message names the key, not a value. A value that is not valid UTF-8 (POSIX `surrogateescape`) reaches `run()` and is refused with exit 1. `_text`'s message never quotes the value (READ). The check list covers all four cases.
  - **Finding 10 is better than my fix.** The options now carry `run()`'s names, so every error names the option the caller typed.
  - **Finding 2:** the fresh-wheel step compares bytes with the Intent's line. Decision 3 now writes `\n` on every host, so the comparison holds on `windows-2025` too (INFERRED from finding 7's fix).
- **Finding 1's design is closed.** Decision 2 always passes an unset `cancel`. Decision 4's 130 rests on it, and the unit check asserts it. **Finding 1's v1.4 check is not closed** (C1 below).
- **Finding 4 is closed for `--help`, abbreviations and `--`.** Without `--`, the revision takes a different rule from the one I suggested: the guest's argv starts at the first argument that is not an option. That is a sound choice; it is how `python script.py args` works. But it leaves three cases undecided (C2 below).

### Conditions left

1. **C1 (medium): the Ctrl-C check waits for a signal that never comes.**
   - The check sends `SIGINT` "once the child prints that the guest started (on standard error, from the guest)". But the runner keeps a guest's stderr in memory and returns it in `Completed` (READ: `_Stream`, `_send_outputs`). Nothing reaches the process's own stderr while the guest runs. EXECUTED (`stream.txt`): `b''` during the call and after it.
   - Failure: the check waits until its fail-safe timeout and fails, with `cancel` or without it. It cannot tell the fix from the bug.
   - Fix (one sentence in Design): the child is `sys.executable -c` running a short wrapper.
     - The wrapper first calls `main(["run", "--", "-c", "pass"])` once, so the module is compiled or loaded in that process.
     - It then starts a thread that sleeps a trigger interval (as `test_ctrl_c_while_the_guest_runs_ends_the_call` does) and calls `signal.raise_signal(signal.SIGINT)`.
     - Then it returns `main(["run", "--deadline-s", "none", "--", "-c", "while True: pass"])` as its exit code.
     - The check expects 130 and no JSON from the second call, with a fail-safe timeout. Without `cancel` it hangs until the fail-safe, so the check tells the fix from the bug.
     - `raise_signal` works on Windows too (the existing check uses it), so drop "(POSIX)".
     - A SIGINT that lands before the guest starts also gives 130, so the assertion does not depend on timing.
2. **C2 (low-medium): the argv split needs three more words of rule.** The scan runs before argparse, so it, not argparse, decides these:
   - **`--` after the program.** For `run x.py -- y`, rule 1 says "after the first `--`", which gives `["y"]`. The without-`--` rule says "from `x.py`", which gives `["x.py", "--", "y"]`. Fix: scan left to right, and the guest's argv starts at whichever comes first. A `--` met first is dropped. A non-option met first is kept with everything after it, any `--` included.
   - **An unknown option before the program.** In `run -c "print(1)"`, is `-c` "an argument that is not an option" (so the guest gets `["-c", "print(1)"]`), or an unknown option (exit 2)? Fix: any argument that starts with `-`, other than `-` itself, is an option of this command, and an unknown one is exit 2. Otherwise a later option (say a `-c` of the command's own) would change what an existing call gives its guest. The unit checks add `run -c x` → exit 2 and `run -` → guest `["-"]`.
   - **`--name=value`.** A value-taking option written with `=` does not consume the next argument. For example, `run --fuel=5 x.py` gives the guest `["x.py"]`. Add it to the split check.
3. **C3 (trivial): the error object's bytes.** Say in Decision 4 that exit 1's object is written as Decision 3's line is: sorted keys, ASCII, `\n`, one write. It is implied but not said.

### Verdict

**Revise once more, by these sentences only.** C1 changes the Ctrl-C check's trigger. C2 adds three rules to Decision 1's split, with their unit cases. C3 is one clause. Everything else is ready to build. Once the author records the three edits in a Disposition of this confirmation, the specification is ready to build without another review.

## Disposition of the confirmation (filled in by the author)

- **C1:** fixed as suggested. The child warms up, a thread raises `SIGINT` with `signal.raise_signal`, and the check runs on every OS; the spec says why it cannot wait for the guest's word.
- **C2:** decided. One left-to-right scan: `--` first gives the rest to the guest; an argument starting with `-` (not `-` itself) is the command's option, unknown ones exit 2; anything else starts the guest's argv, `--` after it included; `--name=value` consumes nothing. A unit case for each.
- **C3:** fixed. The error object is written as the result line is.

Your verdict made the spec ready to build once these edits were made.
