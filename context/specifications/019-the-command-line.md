# 019 — The command line

- **Status:** drafted 2026-10-17, awaiting its pre-build review.
- **Owner:** Clay Gendron
- **Kind:** the runner's API (a new `src/wasi_python/cli.py`, `src/wasi_python/__main__.py`,
  `pyproject.toml`'s `[project.scripts]`), judge additions in `tests/`, `README.md`,
  `CHANGELOG.md`.
- **Depends on:** 013 and 014 (`run` checks its limits and inputs, so the command line does not
  check them twice), 015 (cancel and Ctrl-C).
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

1. **One subcommand, `run`.** `wasi-python run [options] [--] ARG...` calls
   `wasi_python.run([ARG...], ...)` once and prints the result. `python -m wasi_python run …` is
   the same command. A subcommand leaves room for later ones (a batch mode) without changing this
   one's meaning. No subcommand, or an unknown one, is a usage error.
2. **It adds no power.** Each option maps to one `run()` argument, and nothing else:

   | option | `run()` argument |
   |---|---|
   | `--env KEY=VALUE` (repeatable; split at the first `=`) | `env` |
   | `--stdin PATH`, or `--stdin -` for this process's standard input | `stdin` (the file's bytes) |
   | `--deadline SECONDS` | `deadline_s` (`none` for no limit) |
   | `--memory BYTES` | `memory_bytes` (`none` for no limit) |
   | `--output-bytes BYTES` | `output_bytes` (`none` for no limit) |
   | `--fuel N` | `fuel` |
   | `--no-snapshot` | `snapshot=False` |

   Without an option the argument is `run()`'s default, so the command is as safe as `run(argv)`:
   a private root, `DEFAULTS`' limits, empty input, no host function. There is no `--root`:
   giving the guest a host folder waits for typed grants (spec 017), whose `--grant` option is a
   later change. There is no host function: a host function is code, and a command line carries
   none. Values are passed through as strings or parsed only as far as their type needs (`int`,
   `float`, `none`); `run()` checks them and its error names the argument.
3. **The output is one JSON object, one line, on standard output.** Keys, sorted:
   - `exit_code`, `trapped`, `fuel_used`, `truncated` (a list): as in `Completed`;
   - the program's standard output as `stdout` when its bytes are valid UTF-8, otherwise as
     `stdout_base64` (standard base64); exactly one of the two is present; the same for `stderr`.
     Text is what agents read; base64 keeps binary output exact.

   `json.dumps(…, sort_keys=True, ensure_ascii=True)`, then a newline. The command prints nothing
   else on standard output.
4. **Exit codes say whether there is a result, not how the program ended.**
   - `0`: the call returned; the JSON says how the program ended (any exit code, any trap).
   - `1`: `run()` raised (a checked argument, missing artifacts, wasmtime not installed); one JSON
     object `{"error": "<the exception's message>", "kind": "<its class name>"}` on standard
     output, so a caller parses one shape on every path but usage errors.
   - `2`: a usage error (argparse's own message on standard error, nothing on standard output).
   - `130`: interrupted. Ctrl-C stops the guest (spec 015 already does this inside `run`), and the
     command exits 130 with nothing on standard output.
   The program's own exit code is never the command's: a caller would not tell a program that
   exited 1 from a command that failed.
5. **wasmtime stays optional.** The wheel's dependencies stay empty; `run` needs the `run` extra.
   The command imports the runner lazily, and without wasmtime it exits 1 with
   `{"error": "the run command needs wasmtime: install wasi-python[run]", "kind": "ImportError"}`.
6. **The entry point** is `[project.scripts] wasi-python = "wasi_python.cli:main"`. `main(argv=None)`
   returns the exit code, so checks call it in process; the script wrapper passes it to
   `sys.exit`.

## Intent

`wasi-python run -- -c "print(1)"` prints
`{"exit_code": 0, "fuel_used": null, "stderr": "", "stdout": "1\n", "trapped": null, "truncated": []}`,
and every other language can run agent code the same way.

## Design

- `src/wasi_python/cli.py`: `argparse` with one subparser; `main(argv: list[str] | None = None) ->
  int`. Parsing helpers `_limit(text)` (`none` → `None`, else `float` or `int`) and `_env(items)`
  (refuses an item with no `=`, as a usage error). The call: `run(args.argv, env=…, stdin=…, …)`
  with only the options given passed, so `run()`'s `_UNSET` defaults apply. `_stream(name, data)`
  returns `{name: text}` or `{name + "_base64": …}`.
- `src/wasi_python/__main__.py`: `raise SystemExit(main())`.
- `pyproject.toml`: the `[project.scripts]` line. The wheel changes (an entry point and two
  modules), so the release's same-bytes rebuild compares it as before.
- README: a "From any language" section with one example in a shell and one in TypeScript
  (`spawn`, `JSON.parse`), the output keys and the exit codes.
- CHANGELOG: one entry.
- Checks (`tests/unit/test_cli.py` for parsing and output without a guest, by a fake `run`;
  `tests/checks/test_v1_4_embedding.py` for real calls):
  - each option reaches `run()` as its argument, and an option not given is not passed (the fake
    records its keyword arguments);
  - `--env` without `=` and an unknown subcommand exit 2 with nothing on standard output;
  - a fake `run` that raises `ValueError("deadline_s must be …")` gives exit 1 and the error JSON;
  - a fake `Completed` with UTF-8 and non-UTF-8 bytes gives `stdout` and `stderr_base64`, and the
    base64 decodes to the bytes;
  - the JSON is one line with sorted keys;
  - without wasmtime (the import made to fail): exit 1 and the ImportError JSON;
  - v1.4, real calls through `main()`: `-c "print(1)"` gives exit 0 and `"stdout": "1\n"`;
    `-c "import sys; sys.exit(3)"` gives command exit 0 and `"exit_code": 3`; `--stdin` of a file
    reaches the guest's `sys.stdin`; `--deadline 0.5` on an endless loop gives
    `"trapped": "deadline"`; `--fuel 1000` gives `"trapped": "out of fuel"`;
  - v1.4, the installed entry point: `uv run wasi-python run -- -c "print(1)"` as a subprocess
    prints the same JSON (the check finds the script on `PATH` through `sysconfig`, not `shutil.which`
    on an unknown `PATH`).
- Each check is seen failing first (no `cli` module).

## Scope

In: the above. Out:
- A batch mode (many programs, one process, JSON Lines in and out): a later specification, once
  a caller needs to keep one process warm.
- `--grant`: after spec 017 lands.
- A Node, Go or other client library: the README's examples are the contract.

## Acceptance criteria

1. The checks exist and were seen failing before the change.
2. `uv run pytest` is green with `--accept-judge`.
3. A release dry run passes every job, and its `verify` jobs run the command from the installed
   wheel on Linux, macOS and Windows.

## Landing notes

Not built.
