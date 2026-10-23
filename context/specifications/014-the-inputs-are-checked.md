# 014 — The inputs are checked

- **Status:** landed, 2026-10-17. Reviewed before build (`../reviews/014-the-inputs-are-checked-spec-2026-10-17.md`) and after (`../reviews/014-the-inputs-are-checked-2026-10-17.md`).
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`), judge additions in `tests/`, `README.md`, `CHANGELOG.md`.
- **Depends on:** 013 (the limits are checked: the same place, the same style of error).
- **Research it stands on:**
  - `../research/2026-10-17-what-run-does-with-its-inputs.md` (the placeholder from spec 013's review).
  - The author's probe, EXECUTED on the current runner and artifacts. The script is `inputs_probe.py` in scratch, with its output `inputs_before.txt` beside it.

## The defect

`run` passes `argv`, `env` and `stdin` on unchecked. Some values silently become different ones:

| input | what the guest sees today (EXECUTED) |
|---|---|
| `argv=["-c", code, "a\0b"]` | the argument `a`: cut at the NUL |
| `argv="-c"` | the arguments `-`, `c`: a `str` is split into characters |
| `env={"K": "a\0b"}` | `K=a` |
| `env={"K\0X": "v"}` | **`K=v`**: the key is cut at the NUL, so a different variable is set |
| `env={"K=X": "v"}` | **`K=X=v`**: the key's `=` splits it, so a different variable is set |
| `env={"": "v"}` | the guest's start-up fails with `OSError` (exit 1) |
| `stdin=0` | empty input |
| an `int` or `bytes` in `argv`, an `int` in `env` | `AttributeError: … has no attribute 'encode'`, naming no argument |
| `stdin="hi"` | `TypeError` from `memoryview`, naming no argument |
| a lone surrogate (`"\udcff"`, as `os.environ` and `os.listdir` produce for undecodable bytes) | `UnicodeEncodeError` inside wasmtime-py, after the root is prepared, naming no argument (the review, EXECUTED) |
| a non-contiguous `memoryview` as `stdin` | `BufferError`, late (the review, EXECUTED) |

Two of these matter for the users this project serves.
- **A key filter is bypassed.** A host that passes untrusted text as an environment key, after a deny-list check, can have it set a different variable, because the key is cut at a NUL or split at an `=`. `env={"HOME\0x": "/shared"}` passes a filter for `HOME` and gives the guest `HOME=/shared` (the review, EXECUTED).
- **Arguments are cut short.** A host that builds arguments from untrusted text can have them cut at a NUL without knowing.

Native Python refuses a NUL and an `=` in a key: `subprocess` raises `ValueError: embedded null byte` and `ValueError: illegal environment variable name` (EXECUTED).

## Decisions

1. **`run` checks its inputs first, with the limits (spec 013), before any work.** A wrong type raises `TypeError` and a wrong value raises `ValueError`. Each message names the argument.
2. **The rules.** Every `str` must also encode as UTF-8, because WASI carries UTF-8. So a lone surrogate is refused with `ValueError` naming the argument. That includes the surrogateescape characters `os.environ` and `os.listdir` produce for undecodable bytes (the review, EXECUTED).
   - **`argv`:** any iterable except `str`, `bytes` and `bytearray`, consumed once with `list()`. A generator or `dict_keys` works today, and `subprocess` accepts any iterable (the review, EXECUTED). Each item must be a `str` with no NUL.
     - `os.PathLike` is refused. The guest sees its own file system, so a host path object would mislead; a caller who means the text passes `str(path)`.
     - Each item is passed on as a plain `str`, made with `str.__str__(x)`, never `str(x)`, which returns a subclass's override (the review's confirmation, EXECUTED). Its UTF-8 check uses `str.encode(x, "utf-8")` for the same reason.
     - An empty `argv` stays allowed: the guest runs the interactive prompt on empty stdin, as today.
   - **`env`:** `None`, or a `collections.abc.Mapping` of `str` to `str`. Today any object with `keys()` and `__getitem__` works; the CHANGELOG names the change. A value must hold no NUL. A key must be non-empty, hold no NUL, and hold no `=` anywhere: not at its start either.
     - This is the strictest of the native rules (the review, EXECUTED). POSIX `subprocess` accepts an empty key, and `os.execve` and Windows accept a leading `=`. It is right for this guest, whose start-up fails on an empty key or a key starting with `=`.
     - Odd but valid keys stay allowed: non-ASCII, a leading digit, a space. They reach the guest exactly, as `subprocess` and `os.putenv` accept them.
     - The message words follow `subprocess`: "embedded null byte", "illegal environment variable name".
     - It is passed on as a `dict` of plain `str`.
   - **`stdin`:** `None`, or a bytes-like object, which is anything `memoryview()` accepts. It is passed on as `memoryview(x).tobytes()`, so a non-contiguous view works too. An exact `bytes` is passed on unchanged, so a large input is not copied again.
     - A `str` is refused with `TypeError`: its encoding would be a guess.
     - `0`, `False` and `[]` are refused too. Each is a caller's mistake that today silently means "no input". `subprocess.run(input=…)` happens to accept them in binary mode (the review, EXECUTED), so this rule is stricter on purpose.
     - There is no cap. `stdin` goes to a host temporary file of its size, and input larger than the guest's memory cap fails inside the guest only (the review, EXECUTED: 128 MiB under a 96 MiB cap gave a `MemoryError` in the guest). The README says so.
   - **Messages** name the argument and the position or key, and never quote a value: environment values are often secrets. For example, `env value for 'TOKEN': embedded null byte`.
3. **No other change.** `BASE_ENV` and the per-call `HOME` are laid under `env` as today, so a caller may still override `HOME`, `TMPDIR` or `PYTHONTZPATH`.
   - That undoes part of spec 006 on a reused root (the review, EXECUTED). With `HOME` pointing at a shared directory, pdb reads a planted `.pdbrc` there. With `PYTHONTZPATH` pointing at a planted directory, `zoneinfo` parses a planted file.
   - `PYTHONPATH`, `PYTHONUSERBASE` and a user-site `.pth` have no effect, because `site` does not run.
   - The README's "Not protected" list states this cost.
   - An `argv` or `env` larger than the guest's memory makes the guest exit 1 with empty stderr. Nothing is cut short, so it is documented rather than checked.
4. **Checks.**
   - **Unit tests of the checking function.**
     - Refused: one test per row of the table, plus `"=K"` as a key, `False` and `[]` as `stdin`, a `PathLike` in `argv`, and a lone surrogate in each of `argv`, an env key and an env value.
     - Accepted: a tuple, a list, a generator, a `dict`, a `MappingProxyType`, `bytearray`, a non-contiguous `memoryview`, `None`, a `str` subclass, and odd but valid keys.
     - Passed on: plain types.
     - Messages: a refusal's message never contains the value.
   - **A v1.4 check** that `run` refuses each of these with `ValueError`, creating nothing:
     - a NUL in `argv`;
     - `{"HOME\0x": "/shared"}`;
     - an `=` in an `env` key;
     - a lone surrogate.

     It uses spec 013's pattern: a fresh `tempfile.tempdir`, and a `root=`.
   - Each new test is seen failing first.
5. **The CHANGELOG** adds one line to 0.1.0a2's "`run` changes for existing callers" list. It names the stricter `stdin` and the empty or `=` keys.

## Intent

The guest sees exactly the arguments, environment and input the caller passed, or the call is refused with an error that says why.

## Design

```
src/wasi_python/runner.py   _check_inputs(argv, env, stdin) -> the plain values, called with
                            _check_limits, first in run
tests/unit/test_runner_inputs.py   the rules
tests/checks/test_v1_4_embedding.py   NUL and '=' refused, nothing created
README.md, CHANGELOG.md
```

## Scope

In: `argv`, `env` and `stdin`. Out: `root` and `host`, and the content of arguments beyond NUL, such as a program text the guest cannot parse, which the guest reports itself.

## Acceptance criteria

1. The unit tests and the v1.4 check exist and were seen failing before the change.
2. `uv run pytest` is green with `--accept-judge`.
3. A dry run of the release workflow passes every job.

## Landing notes

Built 2026-10-17 by the author agent; reviewed in `../reviews/014-the-inputs-are-checked-2026-10-17.md`. The review's fixes:
- a v1.4 check that the guest gets exactly the checked inputs, which fails when `run` drops the pass-through (EXECUTED);
- the refusal check passes an `artifacts=` that must not be touched;
- a long key is cut in a value's message, and a unit test requires that a refused key is never quoted;
- the README has its own inputs bullet;
- `run`'s signature names the accepted types. The confirmation's three points are in the build: plain `str` through `str.__str__`, the UTF-8 check through `str.encode`, and exact `bytes` passed on uncopied (all unit-tested). One choice beyond the text: an illegal key is not quoted in its message either, since a malformed key such as `TOKEN=abc` can carry a secret.

**Seen failing first** (EXECUTED): before the runner had `_check_inputs`, all 49 new tests failed. That is 45 unit tests in `tests/unit/test_runner_inputs.py` and the four cases of `test_an_input_the_guest_would_see_differently_is_refused`. In those four, `run` ran the guest, or, for the lone surrogate, raised `UnicodeEncodeError` after preparing the root.

**After** (EXECUTED): all 49 pass. The author's probe, run again: every row of the defect table is refused with an error that names the argument; `bytearray` and `memoryview` stdin and a tuple `argv` work as before.

**The dry run** (EXECUTED: https://github.com/ClayGendron/wasi_python/actions/runs/39027959144): every job it runs passed, including the arm64 Linux rebuild, `same-bytes`, and verify on ubuntu-24.04, windows-2025 and macos-15 (criterion 3).
