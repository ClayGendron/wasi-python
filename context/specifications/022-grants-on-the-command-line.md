# 022 — Grants on the command line

- **Status:** drafted 2026-10-17, awaiting its pre-build review.
- **Owner:** Clay Gendron
- **Kind:** the command line (`src/wasi_python/cli.py`), judge additions in `tests/`, `README.md`,
  `CHANGELOG.md`.
- **Depends on:** 017 (typed grants, landed), 019 (the command line), which must land first.
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

   The guest path comes first and the split is at the first `=`: a Windows host path holds `:`
   and `\`, never needed in a guest path, and a guest path with `=` is refused as a usage error.
   Grants keep their command-line order (the runner accepts any order). `--root` and `--no-root`
   together are a usage error. Without them the call has `run()`'s default, a private root.
2. **Read-only is the default form.** The writable option is the longer one, so a caller never
   gets a writable folder by a missing word (§4.15).
3. **`run()` judges every grant.** The command passes the values on; every rule of spec 017
   (links, identities, the runtime's folders, the temporary folder) applies, and a refusal is
   exit 1 with `run()`'s `ValueError` as the error line. Nothing is checked twice.
4. **Relative host paths** are taken from the command's working directory, as `run()` takes them.

## Intent

`wasi-python run --grant /data=./inputs --grant-writable /out=./results -- -c "…"` gives the
program its data read-only and a folder for its results, with the runner's checks unchanged.

## Design

- `cli.py`: the three options in `_parser`; `VALUED` gains `--grant`, `--grant-writable` and
  `--root`; `_grants(items, writable)` splits at the first `=` (a usage error without one, or with
  an empty side).
- Checks (`tests/unit/test_cli.py`, the fake `run`): each option reaches `run()` as `grants=`
  (order kept, modes right) or `root=`; `--grant` without `=`, `--grant =x`, and `--root` with
  `--no-root` exit 2. v1.4: a real call with a read-only and a writable grant: the program reads
  one and writes the other; a write to the read-only one gives `PermissionError` in its stderr; a
  grant `run()` refuses (the temporary folder) gives exit 1 and `"kind": "ValueError"`.
- README's *From any language*: the three options and an example. CHANGELOG: one line.

## Scope

In: the above. Out: anything `run()` does not take.

## Acceptance criteria

1. The checks exist and were seen failing first.
2. `uv run pytest` is green with `--accept-judge`.
3. A release dry run passes every job.

## Landing notes

Not built.
