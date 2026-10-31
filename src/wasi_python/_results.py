"""The result an agent reads: `Display`, the record of one value or display, and the host that
takes a guest's display frames beside its tool frames.

A call or turn asked for results (`results=True`) gets a `_ResultHost` at its door. It answers
the tool protocol's `display` operation itself and hands `list` and `call` to the call's tool
host, or answers them `protocol` when the call has none, so a guest still fails to import its
tools. Every display frame is judged here, whoever sent it: only the six MIME types, each value
of its own type. A call's displays, its value included, share one more `output_bytes` of
decoded bytes and a thousand records; past either a display is answered as not kept, and the
result names "displays" in `truncated`. Nothing here touches the tool record or its budget.

This module is imported with the package, for `Display`; the frame rules it shares with the
tool host are imported only when a call asks for results.
"""

from __future__ import annotations

import types
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ._outputs import _Stream
    from ._tool_host import _ToolHost

MIME_TYPES = (
    "text/plain",
    "text/html",
    "text/markdown",
    "image/svg+xml",
    "application/json",
    "image/png",
)
BINARY = "image/png"  # the one type whose content is bytes; the rest are text
RECORDS = 1000  # the displays a call or turn keeps, its value included: the tool record's number
ESCAPE = 6  # a byte of text is at most six in a JSON string (\u00XX)
ENVELOPE = 1024  # room for a frame's keys and its list of cut types, beside its content
# The guest's argument that turns results on, first after the program's name; the second form
# adds matplotlib's figures. It is read and removed before the program sees its arguments.
FLAG = "-Xhost-results"
FIGURES_FLAG = "-Xhost-results=figures"


@dataclass(frozen=True, slots=True)
class Display:
    """One value or display a guest handed the host, as a notebook keeps it.

    Attributes:
        data: The content by MIME type, read-only: "text/plain" always (the object's `repr`),
            and any of "text/html", "text/markdown", "image/svg+xml" and "application/json" as
            `str`, and "image/png" as `bytes`. HTML and SVG are the guest's: render them in a
            sandboxed frame.
        truncated: The MIME types cut or left out because the call's room for displays ran
            short.
        stdout_at: The bytes the guest had written to stdout before it, kept or not: under the
            "head" keep, `stdout[:stdout_at]` is what printed before it.
        stderr_at: The same for stderr.

    Two are equal when their fields are; a display is not hashable, since `data` is a mapping.
    """

    __hash__ = None  # type: ignore[assignment]  # unhashable, as a dict is

    data: Mapping[str, str | bytes]
    truncated: tuple[str, ...] = ()
    stdout_at: int = 0
    stderr_at: int = 0

    def __post_init__(self) -> None:
        # A copy no holder can change, whatever mapping was given.
        object.__setattr__(self, "data", types.MappingProxyType(dict(self.data)))
        object.__setattr__(self, "truncated", tuple(self.truncated))


def _check_results(results: Any, figures: Any, host: Any, argv: tuple[str, ...]) -> str | None:
    """`results=` and `figures=` as the guest's mode: None, "results" or "figures". Figures
    need results, results need the tool protocol's door rather than a raw `host=`, and the flag
    is the runner's to pass: an embedder's argv that holds it before the program's target is
    refused, since the guest would read it as the runner's."""
    for name, flag in (("results", results), ("figures", figures)):
        if type(flag) is not bool:
            raise TypeError(f"{name} must be True or False; got {type(flag).__name__}")
    if figures and not results:
        raise TypeError("figures= without results= sends nothing: pass results=True too")
    if results and host is not None:
        raise TypeError(
            "results= needs the runner's door, and host= hands the door to your code: pass one"
        )
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in (FLAG, FIGURES_FLAG):
            raise ValueError(f"argv may not pass {a} before the program: pass results= instead")
        if a in ("-c", "-m") or a == "-" or not a.startswith("-"):
            break  # the program's target: what follows it is the program's own
        i += 2 if a == "-X" else 1
    if not results:
        return None
    return "figures" if figures else "results"


def _flag(mode: str | None) -> list[str]:
    """The guest's argument for `mode`, to put first after the program's name."""
    if mode is None:
        return []
    return [FIGURES_FLAG if mode == "figures" else FLAG]


def _size(data: Mapping[str, str | bytes]) -> int:
    """A display's decoded bytes: its text as UTF-8, its PNG as is."""
    return sum(len(v) if isinstance(v, bytes) else len(v.encode("utf-8")) for v in data.values())


class _ResultHost:
    """The door's host for a call or turn with results: its display frames answered and kept,
    every other operation handed to `tools`, or refused when there is none.

    `room` is the decoded bytes left for displays (None: no bound); `streams` and `settle` tell
    where each display falls in stdout and stderr. `admit(length)` judges a frame by its length
    before it is read, and never spends a tool frame; `__call__(frame)` answers it. Nothing a
    frame does raises out of either."""

    def __init__(
        self,
        tools: _ToolHost | None,
        room: int | None,
        streams: tuple[_Stream, _Stream],
        settle: Callable[[], None],
    ) -> None:
        from . import _tool_host  # the frame rules, loaded only when results are asked
        from .tools import PROTOCOL

        self._wire, self._version = _tool_host, PROTOCOL
        self._tools, self._room = tools, room
        self._streams, self._settle = streams, settle
        self._records = 0
        self.value: Display | None = None
        self.displays: list[Display] = []
        self.cut = False  # a display was cut or not kept: the result names "displays"

    def admit(self, length: int) -> bytes | None:
        """None to read the frame; else the answer to one too long to be a display that fits,
        nor, under tools, a tool frame the tool host would read. Once the records are spent, a
        display keeps nothing, so a frame longer than its keys is answered unread."""
        spent = self._records >= RECORDS
        if self._room is None and not spent:
            return None
        bound = ENVELOPE if spent or self._room is None else ESCAPE * self._room + ENVELOPE
        cap = self._wire._TOOL_REQUEST_BYTES if self._tools is not None else 0
        if length <= max(bound, cap):
            return None
        self._records += 1
        if cap:  # past the tool frame's cap too: refused as a frame, not judged a display
            most = max(bound, cap)
            return self._too_large(None, f"the frame is {length} bytes; at most {most}", False)
        self.cut = True
        if spent:
            return self._encoded({"id": None, "ok": True, "kept": False})
        return self._too_large(None, f"the frame is {length} bytes; a display has room for")

    def __call__(self, frame: bytes) -> bytes:
        try:
            return self._answer(bytes(frame))
        except Exception:  # a bug here must not reach the guest's door as a fault
            message = "the host could not answer this frame (internal error)"
            return self._refused(None, message)

    def _answer(self, frame: bytes) -> bytes:
        wire = self._wire
        try:
            request = wire._parse(frame)
        except wire._Refused as e:
            if self._tools is not None:
                return self._tools(frame)  # a tool frame's refusal stays in the tool record
            self._records += 1
            return self._refused(None, str(e))
        op = request.get("op")
        if op != "display" and self._tools is not None:
            return self._tools(frame)
        frame_id = request.get("id")
        if type(frame_id) is not int or not 0 <= frame_id <= 2**53 - 1:
            frame_id = None
        self._records += 1
        version = request.get("v")
        if type(version) is not int or version not in wire._PROTOCOLS:
            return self._refused(frame_id, "this host serves protocol version 1")
        if op in ("list", "call"):
            return self._refused(frame_id, "this run has no tools: the embedder passed none")
        if op != "display":
            return self._refused(frame_id, "unknown operation; this host serves display")
        refusal = _refusal(request)
        if refusal is not None:
            return self._refused(frame_id, refusal)
        return self._keep(frame_id, request)

    def _keep(self, frame_id: int | None, request: dict[str, Any]) -> bytes:
        """A valid display frame: kept if it has a record and room left, else answered."""
        data = request["data"]
        size = _size(data)
        if self._records > RECORDS or self._room == 0:
            self.cut = True
            return self._encoded({"id": frame_id, "ok": True, "kept": False})
        if self._room is not None and size > self._room:
            self.cut = True
            return self._too_large(frame_id, f"the display is {size} bytes; there is room for")
        if self._room is not None:
            self._room -= size
        self._settle()  # every byte written before the frame is in the streams
        out, err = self._streams
        truncated = tuple(dict.fromkeys(request.get("truncated", ())))
        record = Display(data, truncated, out.written, err.written)
        if truncated:
            self.cut = True
        if request["value"]:
            self.value = record  # the cell's last value frame is its value
        else:
            self.displays.append(record)
        return self._encoded({"id": frame_id, "ok": True, "kept": True})

    def _encoded(self, answer: dict[str, Any]) -> bytes:
        encoded: bytes = self._wire._encode({"v": self._version, **answer})
        return encoded

    def _refused(self, frame_id: int | None, message: str) -> bytes:
        """`protocol`, as the tool host refuses a frame that breaks the rules."""
        refused: bytes = self._wire._error(frame_id, "protocol", message)
        return refused

    def _too_large(self, frame_id: int | None, said: str, room_said: bool = True) -> bytes:
        """`too_large`, with the room left, so the guest can send the text alone, cut to fit."""
        room = self._room or 0
        error = {"kind": "too_large", "message": f"{said} {room}" if room_said else said}
        return self._encoded({"id": frame_id, "ok": False, "error": error, "room": room})


def _refusal(request: dict[str, Any]) -> str | None:
    """Why a display frame breaks the protocol, or None: `value` a boolean; `data` an object of
    the six MIME types, "text/plain" among them, each a string but "image/png", which is bytes;
    `truncated`, if given, a list naming only the six."""
    if type(request.get("value")) is not bool:
        return 'a display says with "value" true or false whether it is the value'
    data = request.get("data")
    if not isinstance(data, dict) or "text/plain" not in data:
        return 'a display\'s "data" is an object with "text/plain"'
    for mime, content in data.items():
        if mime not in MIME_TYPES:
            return f"a display may carry {', '.join(MIME_TYPES)}; not {mime[:64]!r}"
        want = bytes if mime == BINARY else str
        if type(content) is not want:
            kind = '{"$bytes": "<base64>"}' if want is bytes else "a string"
            return f"{mime} must be {kind}"
    truncated = request.get("truncated", [])
    if not isinstance(truncated, list) or any(t not in MIME_TYPES for t in truncated):
        return '"truncated" is a list of the six MIME types'
    return None


def _host_of(host: Any) -> _ResultHost | None:
    """The result host at a door, or None when the call did not ask for results."""
    return host if isinstance(host, _ResultHost) else None


def _door_hosts(
    mode: str | None,
    host: Any,
    tools: _ToolHost | None,
    room: int | None,
    streams: tuple[_Stream, _Stream],
    settle: Callable[[], None],
) -> tuple[Any, Callable[[int], bytes | None] | None]:
    """The door's host and its admit for a call or turn: the result host over the tool host
    when results are asked, else the tool host, else the embedder's raw `host`."""
    if mode is not None:
        results = _ResultHost(tools, room, streams, settle)
        return results, results.admit
    if tools is not None:
        return tools, tools.admit
    return host, None
