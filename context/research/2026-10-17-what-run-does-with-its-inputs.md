# What `run` does with its inputs

- **Status:** placeholder, 2026-10-17.
- **Owner:** Clay Gendron
- **Researcher:** the author agent (Claude Opus 5.5), from the pre-build review of spec 013
  (`../reviews/013-the-limits-are-checked-spec-2026-10-17.md`, finding 5). Spec 013 checks the
  four limits only.
- **Feeds:** a later specification that checks `argv`, `env` and `stdin` as spec 013 checks the
  limits.
- **Blocks:** that specification only.

## The question

Which values of `argv`, `env` and `stdin` does `run` silently change today, and which should it
refuse with a clear error instead?

## What is known (the review of spec 013, EXECUTED)

- **A NUL in an argument or an environment value silently cuts it short.** The guest sees a
  different program or value from the one the caller passed. This matters most: a host that
  builds `argv` from untrusted text could have it truncated without knowing.
- A `str` passed as `argv` is split into one argument per character.
- `stdin=""` or `stdin=0` silently becomes empty input. wasmtime-py never sees `stdin`, because
  the runner writes it to a file.
- A non-`str` value in `argv` or `env` raises `AttributeError`, which does not name the argument.

None of these removes a limit, so spec 013 left them out.

## What to find out

- What the C API does with each input, as against what wasmtime-py does: where the NUL is lost,
  and whether a key may hold `=`.
- What native CPython's `subprocess` refuses, so the runner can match it (it raises
  `ValueError: embedded null byte`).
- Whether `stdin` should take `bytes`-like values only.
