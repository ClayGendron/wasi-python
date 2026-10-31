"""A checked call for the judge's stand-ins: the one place in the harness a call is built by hand.

`BASE_CALL` is a `_CheckedCall` written out with every field explicit: no limit, nothing granted,
no tools, no results, `argv` the one-line `pass`. `checked_call(**fields)` is a copy with the
named fields changed; an unknown name is `dataclasses.replace`'s own `TypeError`, so a stand-in
can never carry a field the runner does not know.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from wasi_python import _call

BASE_CALL = _call._CheckedCall(
    fuel=None,
    deadline_s=None,
    memory_bytes=None,
    output_bytes=None,
    output_keep="head",
    on_output=None,
    argv=("-c", "pass"),
    env=None,
    stdin=None,
    cancel=None,
    tools=None,
    gate=None,
    tool_calls=None,
    tool_request_bytes=None,
    root=False,
    grants=(),
    mounts=(),
    import_path=(),
    import_serving=(),
    file_calls=None,
    open_files=None,
    binary="snapshot",
    start=None,
    results=None,
)


def checked_call(**fields: Any) -> _call._CheckedCall:
    """`BASE_CALL` with `fields` changed; an unknown field name is a `TypeError`."""
    return dataclasses.replace(BASE_CALL, **fields)
