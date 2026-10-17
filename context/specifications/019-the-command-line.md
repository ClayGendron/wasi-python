# 019 — The command line

- **Status:** drafted 2026-10-17 and revised against its pre-build review
  (`../reviews/019-the-command-line-spec-2026-10-17.md`), confirmed for build after one more edit
  (the confirmation's C1 to C3, made).
- **Owner:** Clay Gendron
- **Kind:** the runner's API (a new `src/wasi_python/cli.py`, `src/wasi_python/__main__.py`,
  `pyproject.toml`'s `[project.scripts]`), the release workflow's `verify` job, judge additions
  in `tests/`, `README.md`, `CHANGELOG.md`.
- **Depends on:** 013 and 014 (`run` checks its limits and inputs, so the command line does not
  check them twice), 015 (cancel and Ctrl-C), 016 (a killed command's folders are swept).
- **Research it stands on:**
  - The owner's answer to question 7 (`../questions-for-the-owner.md`), recorded in the
    constitution's §3: "A thin command that runs one program through the runner and prints its
    result as JSON (`wasi-python run`) is part of the runner, not a shell: it adds no power
    `run()` does not have."
  - `../research/2026-10-16-a-principal-engineers-direction.md` (the gap table: "a thin
    `wasi-python run` that prints a JSON `Completed` would let any agent framework call it by
    subprocess").
  - `../research/2026-10-17-market-research-use-cases.md` (feature 6: the JSON command is the safe
    path for TypeScript agent frameworks, since `node:wasi` is not a sandbox).

## The problem

`run()` is a Python function. An agent framework written in TypeScript, Go or anything else can
reach it only by writing Python glue. A command that takes a program on its command line and
prints one JSON object lets any language call the runner with `spawn` and `JSON.parse`, with the
runner's checks and defaults unchanged.

## Decisions

1. **One subcommand, `run`.** `wasi-python run [OPTIONS] -- ARG...` calls
   `wasi_python.run([ARG...], ...)` once and prints the result. `python -m wasi_python run …` is
   the same command. A subcommand leaves room for later ones (a batch mode) without changing this
   one's meaning. No subcommand, or an unknown one, is a usage error.
   - **The guest's argv is split off by one left-to-right scan.** Each argument is, in turn:
     `--`, and then everything after it is the guest's argv, untouched; or an argument starting
     with `-` (other than `-` itself), which is this command's option, so an unknown one, such as
     `-c` before any program, is a usage error (exit 2) and a later option can never change what
     an existing call gives its guest; or anything else, and then it and everything after it are
     the guest's argv (`run x.py --fuel 5` gives the guest `["x.py", "--fuel", "5"]`, and
     `run x.py -- y` gives `["x.py", "--", "y"]`). An option that takes a value consumes the next
     argument, unless it is written `--name=value`. The options are then parsed by `argparse`
     with `allow_abbrev=False`, so `--dead` is a usage error, never `--deadline-s`.
   - **An empty argv is allowed:** `run([], stdin=…)` runs the program on standard input, as
     CPython does (the review, EXECUTED).
   - **The command never reads its own standard input** unless `--stdin -` says so.
2. **It adds no power.** Each option maps to one `run()` argument, and nothing else:

   | option | `run()` argument |
   |---|---|
   | `--env KEY=VALUE`, or `--env KEY` to take `KEY`'s value from this command's own environment (repeatable; split at the first `=`; a repeated key keeps its last value) | `env` |
   | `--stdin PATH`, or `--stdin -` for this process's standard input | `stdin` (the file's bytes) |
   | `--deadline-s SECONDS` (a `float`) | `deadline_s` |
   | `--memory-bytes BYTES` (an `int`) | `memory_bytes` |
   | `--output-bytes BYTES` (an `int`) | `output_bytes` |
   | `--fuel N` (an `int`) | `fuel` |
   | `--no-snapshot` | `snapshot=False` |

   The option names are `run()`'s argument names, so an error from `run()` (it names
   `deadline_s`) points at the option. A limit given as `none` is `None`, no limit. A value that
   does not parse as its type (`--fuel ten`) is a usage error, exit 2; a value that parses but
   `run()` refuses (`--fuel -1`) is exit 1 with `run()`'s message. `--env KEY` without `=` takes
   the value from the command's environment, so a secret need not appear on the command line,
   where other local users can read it with `ps`; a `KEY` absent there is a usage error.

   Without an option the argument is `run()`'s default, so the command is as safe as `run(argv)`:
   a private root, `DEFAULTS`' limits, empty input, no host function. There is no `--root` and no
   `--grant`: giving the guest a host folder waits for typed grants (spec 017). There is no host
   function: a host function is code, and a command line carries none.

   **Ctrl-C.** The command always passes `run()` a `cancel` event that nothing sets. Spec 015
   watches for Ctrl-C while a guest computes only when the call has `cancel` (the review,
   EXECUTED: without one, Ctrl-C at 1.5 s stopped an endless loop only at its 8 s deadline; with
   one, at 1.5 s). An unset event changes nothing else, so it adds no power.
3. **The output is one JSON object, one line, on standard output.** Keys, sorted:
   - `exit_code`, `trapped`, `fuel_used`, `truncated` (a list): as in `Completed`;
   - the program's standard output as `stdout` when its bytes are valid UTF-8, otherwise as
     `stdout_base64` (standard base64); exactly one of the two is present; the same for `stderr`.
     Text is what agents read; base64 keeps binary output exact. Output cut at `output_bytes`
     inside a character is not valid UTF-8, so it comes as base64; the README says so.

   `json.dumps(…, sort_keys=True, ensure_ascii=True)` plus `"\n"`, encoded as ASCII and written
   to `sys.stdout.buffer` and flushed, so the line ends in `\n` on Windows too. The command
   prints nothing else on standard output, with one exception: `--help` prints its usage there
   and exits 0, as every command does.
4. **Exit codes say whether there is a result, not how the program ended.**
   - `0`: the call returned; the JSON says how the program ended (any exit code, any trap).
   - `1`: `run()` raised (a value it refused, missing artifacts, wasmtime not installed), or a
     `--stdin PATH` could not be read; one JSON object
     `{"error": "<the exception's message>", "kind": "<its class name>"}` on standard output,
     written as the result line is (sorted keys, ASCII, one line ending in `\n`).
   - `2`: a usage error (argparse's message on standard error, nothing on standard output).
     `main` catches argparse's `SystemExit` and returns its code, so a check calls `main` in
     process.
   - `130`: interrupted. Ctrl-C stops the guest (Decision 2's `cancel`), `run()` raises
     `KeyboardInterrupt`, and the command returns 130 with nothing on standard output.
   - Killed (a caller's timeout sends `SIGTERM` or `SIGKILL`): no output. The call's private
     folders stay until the next wasi_python process on the same kernel sweeps them (spec 016,
     EXECUTED by the review).

   The program's own exit code is never the command's: a caller would not tell a program that
   exited 1 from a command that failed.
5. **wasmtime stays optional, with no special case.** The package imports without wasmtime, and
   `run()` already raises `ImportError('wasi_python.run needs wasmtime-py: pip install
   "wasi-python[run]"')`, which exit 1 reports as is.
6. **The entry point** is `[project.scripts] wasi-python = "wasi_python.cli:main"`. `main(argv=None)`
   returns the exit code, so checks call it in process; the script wrapper passes it to
   `sys.exit`. The wheel gains a two-line `entry_points.txt` and stays reproducible (the review,
   EXECUTED: two builds, one under `umask 077`, gave the same bytes).

## Intent

`wasi-python run -- -c "print(1)"` prints
`{"exit_code": 0, "fuel_used": null, "stderr": "", "stdout": "1\n", "trapped": null, "truncated": []}`,
and every other language can run agent code the same way.

## Design

- `src/wasi_python/cli.py`: `argparse` with one subparser, `allow_abbrev=False` on both;
  `main(argv: list[str] | None = None) -> int`. The guest's argv is split off first: everything
  after the first `--`, or, without `--`, from the first argument that is not an option (the
  options that take a value consume it). Helpers: `_limit(type)(text)` (`none` → `None`, else
  the type, else `argparse.ArgumentTypeError`) and `_env(items)` (the `=` split, or the
  command's environment). The call: `run(argv, cancel=threading.Event(), …)` with only the
  options given passed, so `run()`'s `_UNSET` defaults apply. `_stream(name, data)` returns
  `{name: text}` or `{name + "_base64": …}`.
- `src/wasi_python/__main__.py`: `raise SystemExit(main())`.
- `pyproject.toml`: the `[project.scripts]` line.
- `.github/workflows/release.yml`: the `verify` job's fresh-wheel step also runs
  `wasi-python run -- -c "print(1)"` from the installed wheel and compares its line with the
  Intent's, on Linux, macOS and Windows. The `verify` file list gains `tests/unit/test_cli.py`.
- README: a "From any language" section with one example in a shell and one in TypeScript
  (`spawn` with standard output collected in full, `JSON.parse`), the output keys and the exit
  codes, and three warnings: the JSON line can be about 5.4 times the raw output (escaping;
  about 190 MiB at the defaults, EXECUTED by the review), so Node's `exec`, which stops at 1 MiB
  by default, is the wrong call; output cut inside a character comes as base64; a long program
  belongs in a file, `--stdin PATH -- -`, not in `-c`, which meets the system's argument-length
  limit.
- CHANGELOG: one entry.
- Checks (`tests/unit/test_cli.py` for parsing and output without a guest, by a fake `run`;
  `tests/checks/test_v1_4_embedding.py` for real calls):
  - each option reaches `run()` as its argument, an option not given is not passed, and
    `cancel` is always an unset `threading.Event` (the fake records its keyword arguments);
  - the argv split: after `--`, an argv starting with `-c` and one holding `--fuel`; without
    `--`, `x.py --fuel 5` goes to the guest; `x.py -- y` gives `["x.py", "--", "y"]`; `-c x`
    before any program exits 2; `--fuel=5 x.py` consumes nothing after it; an empty argv;
  - `--env K=V`, `--env K` from the environment, a repeated key, a missing `K` (exit 2);
  - `--dead 1` (an abbreviation), `--fuel ten` and an unknown subcommand exit 2 with nothing on
    standard output; `--help` exits 0;
  - a fake `run` that raises `ValueError("deadline_s must be …")` gives exit 1 and the error
    JSON; an unreadable `--stdin PATH` gives exit 1;
  - a fake `run` that raises `KeyboardInterrupt` gives 130 and nothing on standard output;
  - a fake `Completed` with UTF-8 and non-UTF-8 bytes gives `stdout` and `stderr_base64`, and the
    base64 decodes to the bytes; the line is ASCII, one line, sorted keys, ending in `\n`;
  - v1.4, real calls through `main()`: `-c "print(1)"` gives exit 0 and `"stdout": "1\n"`;
    `-c "import sys; sys.exit(3)"` gives command exit 0 and `"exit_code": 3`; `--stdin` of a file
    reaches the guest's `sys.stdin`; `--deadline-s 0.5` on an endless loop gives
    `"trapped": "deadline"`; `--fuel 1000` gives `"trapped": "out of fuel"`;
  - v1.4, Ctrl-C: a child process runs a small wrapper that calls `main()` once to warm up, then
    starts a thread that sleeps briefly and calls `signal.raise_signal(signal.SIGINT)`, and runs
    `main(["run", "--deadline-s", "none", "--", "-c", "while True: pass"])`; the child expects
    130 and nothing on standard output, on every OS (`raise_signal` works on Windows too). The
    guest's own standard error is held by the runner until the call ends, so the check cannot
    wait for the guest to say it started (the review's confirmation, EXECUTED); the sleep only
    makes the signal likely to land while the guest computes, and either way the answer must be
    130. A fail-safe timeout asserts no duration;
  - v1.4, the installed entry point: the script found by
    `shutil.which("wasi-python", path=sysconfig.get_path("scripts"))` (which finds the `.exe` on
    Windows) prints the Intent's line; the judge never calls `uv`.
- Each check is seen failing first (no `cli` module).

## Scope

In: the above. Out:
- A batch mode (many programs, one process, JSON Lines in and out): a later specification, once
  a caller needs to keep one process warm.
- `--root` and `--grant`: after spec 017 lands.
- A Node, Go or other client library: the README's examples are the contract.

## Acceptance criteria

1. The checks exist and were seen failing before the change.
2. `uv run pytest` is green with `--accept-judge`.
3. A release dry run passes every job, and its `verify` jobs run the command from the freshly
   installed wheel on Linux, macOS and Windows (the fresh-wheel step).

## Landing notes

Not built.
