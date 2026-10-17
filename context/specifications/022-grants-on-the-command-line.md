# 022 — Grants on the command line

- **Status:** drafted 2026-10-17 and revised against its pre-build review
  (`../reviews/022-grants-on-the-command-line-spec-2026-10-17.md`), awaiting the reviewer's
  confirmation.
- **Owner:** Clay Gendron
- **Kind:** the command line (`src/wasi_python/cli.py`), judge additions in `tests/`, `README.md`,
  `CHANGELOG.md`.
- **Depends on:** 017 (typed grants) and 019 (the command line), both landed.
- **Research it stands on:** spec 019's Scope ("`--root` and `--grant`: after spec 017 lands")
  and spec 017's *Grants* contract in the README.

## The problem

`wasi-python run` gives the guest only `run()`'s default, a fresh private root. A caller in
another language cannot hand the guest a folder of data to read or a folder to write results to,
which is most of what an agent's code does with files.

## Decisions

1. **Three options, each one of `run()`'s arguments, and nothing else:**

   | option | `run()` argument |
   |---|---|
   | `--grant GUEST=HOST` (repeatable) | a `Grant(HOST, GUEST)`, read-only |
   | `--grant-writable GUEST=HOST` (repeatable) | a `Grant(HOST, GUEST, writable=True)` |
   | `--root HOST`, or `--no-root` | `root=HOST`, or `root=False` |

   **The split is at the first `=`.** The guest side therefore never holds an `=`: a guest path
   with `=` cannot be written on the command line, though `run()` accepts one. That narrows the
   names a caller can give, not the folders the guest can reach, so §3's "no added power" holds.
   The form is chosen over the others (the pre-build review weighed them): `HOST:GUEST` is
   ambiguous with `C:\data`; two values (`--grant GUEST HOST`) would take a host path starting with
   `-` for an option; `HOST=GUEST` split at the last `=` only moves the restriction. With
   `GUEST=HOST` the value always starts with `/`, and `C:\data`, UNC paths and host paths with `=`
   all pass through whole.
2. **Order is kept.** Both grant options write to one list, each value tagged with its mode, so
   `run()`'s errors, which name grants by position (`grants[2]`), match what the caller typed.
3. **Read-only is the default form.** The writable option is the longer one, so a missing word
   never gives a writable folder; abbreviations stay off (`--grant-writabl` is a usage error), and
   the same guest path given twice, in either mode, is refused by `run()`, never merged (§4.15).
4. **`--root` writes.** A root is always writable, and a missing one is made, so the README and
   `--help` say: "`--root HOST`: the guest's `/`, writable; made if missing". Giving `--root`
   twice, or with `--no-root`, is a usage error (exit 2); a silent last-one-wins is not taken.
5. **What is a usage error, and what is `run()`'s.** Exit 2 only for what cannot be parsed: a
   grant value with no `=` ("--grant needs GUEST=HOST"), `--root` twice, or `--root` with
   `--no-root`. A value that parses but `run()` refuses is exit 1 with `run()`'s error, as spec
   019 decides: an empty guest or host side (`--grant /d=`, `--grant =x`), `--root ""`, a guest
   path `run()` refuses, a grant of the temporary folder. Nothing is checked twice. The `=` split
   runs inside the command's `try`, so its usage error returns 2 rather than escaping `main`.
6. **Relative host paths** are taken from the command's working directory, as `run()` takes them.

## Intent

`wasi-python run --grant /data=./inputs --grant-writable /out=./results -- -c "…"` gives the
program its data read-only and a folder for its results, with the runner's checks unchanged.

## Design

- `cli.py`: `--grant` and `--grant-writable` append to one destination with
  `action="append"` and a tagging `type` (`("ro", value)` / `("rw", value)`), so their relative
  order is kept; `--root` (stores, and a second one is a usage error) and `--no-root`; `VALUED`
  gains `--grant`, `--grant-writable` and `--root`. `_grants(items)` splits each at the first `=`.
- Checks (`tests/unit/test_cli.py`, the fake `run`), each asserting the message, so each fails
  first: interleaved `--grant`/`--grant-writable` reach `run()` as `grants=` in the typed order
  with the right modes; `--root x` and `--no-root` reach it as `root=`; `--grant /d` exits 2 with
  "needs GUEST=HOST"; `--root a --root b` and `--root a --no-root` exit 2; `--grant /d=` and
  `--root ""` reach `run()` (whose refusal is exit 1); a host value with `=` and `C:\data` pass
  whole; the scan table gains `--grant=/d=x` and `--no-root x.py`.
- v1.4, real calls: a read-only and a writable grant of folders under the check's own temporary
  folder: the program reads `in.txt` from one and writes `out.txt` to the other; the host sees
  `out.txt` with the program's bytes and `in.txt` unchanged; a write to the read-only grant makes
  the program's stderr end with `PermissionError: [Errno 63] Operation not permitted` and its
  `exit_code` 1, with the command's exit 0; a grant of `tempfile.gettempdir()` (by name, since
  `/tmp` is not that folder on macOS) gives exit 1 and `"kind": "ValueError"`.
- README's *From any language*: the three options, the note that `--no-root` gives no `/` (as
  *Grants* says for `root=False`), and an example. CHANGELOG: one line.

## Scope

In: the above. Out: anything `run()` does not take.

## Acceptance criteria

1. The checks exist and were seen failing first.
2. `uv run pytest` is green with `--accept-judge`.
3. A release dry run passes every job.

## Landing notes

Not built.
