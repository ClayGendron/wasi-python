"""The limits of a call (spec 049, spec 015, spec 055): the tick constants, the checks of every
limit argument, the text and input checks, the worker count, and the sentinel `_UNSET` for an
argument not given."""

from __future__ import annotations

import math
import numbers
import operator
import os
from collections.abc import Iterable, Mapping
from typing import Any

TICK_S = 0.01
NO_DEADLINE = 2**62
CANCEL_TICKS = 5  # a call with `cancel` is checked every 5 ticks while it computes (spec 015)
MAX_WORKERS = 1024


LIMIT_MAX = 2**63 - 1  # wasmtime reads a memory limit as signed: 2**63 and above mean none


def _shown(value: Any) -> str:
    """A value for an error message: an integer too long to print is named by its size."""
    if isinstance(value, int) and value.bit_length() > 128:
        return f"an integer of {value.bit_length()} bits"
    return repr(value)


def _integer_limit(name: str, value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError(f"{name} must be an integer, or None; got {value!r}")
    try:
        number = operator.index(value)
    except TypeError:
        raise TypeError(f"{name} must be an integer, or None; got {value!r}") from None
    if not 0 <= number <= LIMIT_MAX:
        raise ValueError(f"{name} must be from 0 to 2**63 - 1, or None; got {_shown(number)}")
    return number


def _deadline_limit(value: Any) -> float | None:
    return _seconds_limit("deadline_s", value)


def _seconds_limit(name: str, value: Any) -> float | None:
    """`deadline_s`'s rule, named for its argument (spec 055, Decision 9: idle_s, lifetime_s)."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise TypeError(f"{name} must be a number of seconds, or None; got {value!r}")
    rule = f"{name} must be finite and above 0, and at most about 4.6e16 s, or None"
    try:
        seconds = float(value)
        ticks = math.ceil(seconds / TICK_S) if seconds > 0 else 0
    except (OverflowError, ValueError):
        raise ValueError(f"{rule}; got {_shown(value)}") from None
    if not math.isfinite(seconds) or seconds <= 0 or not 0 < ticks < NO_DEADLINE:
        raise ValueError(f"{rule}; got {_shown(value)}")
    return seconds


def _shutdown_limit(name: str, value: Any) -> float:
    """A session's shutdown budget in seconds: finite and at least 0; 0 skips the shutdown, and
    `None` is refused, since the runner itself starts endings and must bound them (spec 055,
    Decision 8)."""
    if value is None or isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise TypeError(f"{name} must be a number of seconds, 0 or more; got {value!r}")
    rule = f"{name} must be finite and 0 or more, and at most about 4.6e16 s"
    try:
        seconds = float(value)
        ticks = math.ceil(seconds / TICK_S) if seconds > 0 else 0
    except (OverflowError, ValueError):
        raise ValueError(f"{rule}; got {_shown(value)}") from None
    if not math.isfinite(seconds) or seconds < 0 or not 0 <= ticks < NO_DEADLINE:
        raise ValueError(f"{rule}; got {_shown(value)}")
    return seconds


def _check_limits(
    fuel: Any, deadline_s: Any, memory_bytes: Any, output_bytes: Any
) -> dict[str, Any]:
    """The four limits as plain values, or TypeError for a wrong type and ValueError for a value
    out of range. A negative fuel or memory cap, or a memory cap of 2**63 or more, would mean no
    limit to wasmtime, and `True` would mean 1, so none of them reaches it (spec 013)."""
    return {
        "fuel": _integer_limit("fuel", fuel),
        "deadline_s": _deadline_limit(deadline_s),
        "memory_bytes": _integer_limit("memory_bytes", memory_bytes),
        "output_bytes": _integer_limit("output_bytes", output_bytes),
    }


def _text(where: str, value: Any) -> str:
    """A plain str the guest will see exactly: no NUL, and valid UTF-8, which WASI carries.
    `str.__str__` and `str.encode` are called directly, so a subclass's overrides are ignored.
    Messages name `where`, never the value: environment values are often secrets."""
    if not isinstance(value, str):
        raise TypeError(f"{where} must be a str, not {type(value).__name__}")
    text = str.__str__(value)
    if "\0" in text:
        raise ValueError(f"{where}: embedded null byte")
    try:
        str.encode(text, "utf-8")
    except UnicodeEncodeError:
        raise ValueError(f"{where}: not valid UTF-8 (a lone surrogate)") from None
    return text


def _check_inputs(argv: Any, env: Any, stdin: Any) -> dict[str, Any]:
    """argv, env and stdin as plain values, or TypeError for a wrong type and ValueError for a
    value the guest would see differently: a NUL cut an argument or key short, and an = split a
    key, so {"HOME\\0x": ...} set HOME (spec 014)."""
    if isinstance(argv, (str, bytes, bytearray)) or not isinstance(argv, Iterable):
        raise TypeError(f"argv must be an iterable of str, not {type(argv).__name__}")
    args = [_text(f"argv[{i}]", item) for i, item in enumerate(argv)]
    plain_env = None
    if env is not None:
        if not isinstance(env, Mapping):
            raise TypeError(f"env must be a mapping of str to str, not {type(env).__name__}")
        plain_env = {}
        for key, value in env.items():
            name = _text("env key", key)
            if not name or "=" in name:
                raise ValueError("env key: illegal environment variable name")  # never quoted
            shown = name if len(name) <= 40 else name[:40] + "…"
            plain_env[name] = _text(f"env value for {shown!r}", value)
    data = None
    if stdin is not None:
        if type(stdin) is bytes:
            data = stdin  # not copied again
        else:
            try:
                data = memoryview(stdin).tobytes()
            except TypeError:
                raise TypeError(
                    f"stdin must be bytes-like, or None; got {type(stdin).__name__}"
                ) from None
    return {"argv": args, "env": plain_env, "stdin": data}


def _cpus() -> int:
    count = getattr(os, "process_cpu_count", os.cpu_count)()  # 3.13 honours CPU affinity
    return count or 1


def _default_workers() -> int:
    """At most 8: at the defaults a worker holds up to 1 GiB of guest memory and 32 MiB of output,
    so 8 bound a process at about 8.3 GiB, and past 8 the measured speedup flattens (spec 015)."""
    return min(_cpus(), 8)


def _check_workers(value: Any) -> int:
    if isinstance(value, bool):
        raise TypeError(f"async_workers must be an integer; got {value!r}")
    try:
        number = operator.index(value)
    except TypeError:
        raise TypeError(f"async_workers must be an integer; got {value!r}") from None
    if not 1 <= number <= MAX_WORKERS:
        raise ValueError(f"async_workers must be from 1 to {MAX_WORKERS}; got {_shown(number)}")
    return number


class _Unset:
    def __repr__(self) -> str:
        return "<default>"


_UNSET: Any = _Unset()
