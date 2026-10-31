"""Rich views of objects for the host (spec 163): `from host.display import display`.

In results mode the bootstrap binds `display` into builtins, as IPython does, and each object
passed to it goes to the host as one record: its `repr` as text/plain and, where the object
offers them, its HTML, Markdown, SVG, JSON and PNG, read from `_repr_mimebundle_` and then the
`_repr_*_` methods, as a notebook reads them. Out of results mode it prints each object's text,
as IPython does in a terminal. A record with no room is sent once more as its text alone, cut
to the room the host names; once the host keeps no more, the cell sends and prints nothing more.
Against a door with no host, or a host that does not serve displays, the text is printed.
"""

import binascii as _binascii
import json as _json
import sys as _sys

import _host as _door

from . import PROTOCOL as _PROTOCOL

_TEXT = "text/plain"
_PNG = "image/png"
_JSON = "application/json"
_METHODS = (
    ("text/html", "_repr_html_"),
    ("text/markdown", "_repr_markdown_"),
    ("image/svg+xml", "_repr_svg_"),
    (_JSON, "_repr_json_"),
    (_PNG, "_repr_png_"),
)
_TYPES = frozenset(m for m, _ in _METHODS)  # what a bundle may add to the text
_on = False  # results mode, set by the bootstrap at each start
_stopped = False  # the host keeps no more in this cell
_next_id = 0

__all__ = ["display"]


def display(*objs):
    """Show each object: in results mode, hand the host its rich view; else print its text."""
    for obj in objs:
        if not _on:
            print(repr(obj))
        elif not _stopped:
            _send(_bundle(obj), False)


def _begin():
    """A new cell: the host may keep records again."""
    global _stopped
    _stopped = False


def _value(obj, text):
    """A cell's last expression, sent as its value; `text` is its repr, which the bootstrap
    takes, so a repr that raises shows no frame of this module, as sys.displayhook shows none."""
    if not _stopped:
        _send(_bundle(obj, text), True)


def _figure(fig):
    """A matplotlib figure, as its PNG and its repr."""
    data = {_TEXT: repr(fig), _PNG: _figure_png(fig)}
    if not _on:
        print(data[_TEXT])
    elif not _stopped:
        _send(data, False)


def _bundle(obj, text=None):
    """The object's views by MIME type. Its repr comes first, `text` when it is given, so a repr
    that raises raises before any other method runs; then `_repr_mimebundle_`, then each
    `_repr_*_` method for a type still missing, and a matplotlib figure's PNG. A method that
    raises an Exception or answers the wrong type is skipped."""
    data = {_TEXT: repr(obj) if text is None else text}
    if isinstance(obj, type):
        return data  # a class's methods are its instances'
    bundle = _ask(obj, "_repr_mimebundle_")
    if isinstance(bundle, tuple) and len(bundle) == 2:
        bundle = bundle[0]  # (data, metadata)
    if isinstance(bundle, dict):
        for mime, content in bundle.items():
            if mime in _TYPES:
                _put(data, mime, content)
    for mime, name in _METHODS:
        if mime not in data:
            _put(data, mime, _ask(obj, name))
    figure = _sys.modules.get("matplotlib.figure")
    if _PNG not in data and figure is not None and isinstance(obj, figure.Figure):
        try:
            data[_PNG] = _figure_png(obj)
        except Exception:
            pass
    return data


def _ask(obj, name):
    """What the object's method `name` answers, or None when it has none or it raised an
    Exception. The method is looked up on the type, so an object that answers every name does
    not seem to offer every view."""
    try:
        if getattr(type(obj), name, None) is None:
            return None
        method = getattr(obj, name)
        if name == "_repr_mimebundle_":
            return method(include=None, exclude=None)
        return method()
    except Exception:
        return None


def _put(data, mime, content):
    """`content` kept under `mime` when it has that type's form: bytes for PNG (or its base64,
    as a bundle may carry it), text for the rest, and for JSON any value JSON can write."""
    if isinstance(content, tuple) and len(content) == 2:
        content = content[0]  # (data, metadata)
    if content is None:
        return
    if mime == _PNG:
        if isinstance(content, str):
            try:
                content = _binascii.a2b_base64(content.encode("ascii"), strict_mode=True)
            except (ValueError, UnicodeEncodeError):
                return
        if isinstance(content, (bytes, bytearray)):
            data[mime] = bytes(content)
        return
    if mime == _JSON and not isinstance(content, str):
        try:
            content = _json.dumps(content, allow_nan=False)
        except (TypeError, ValueError, RecursionError):
            return
    if isinstance(content, str):
        data[mime] = content


def _figure_png(fig):
    import io

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png")
    return buffer.getvalue()


def _send(data, value):
    """One record to the host, and what it answered: kept, or not, after which the cell sends
    nothing more; too large, after which it goes once more as its text alone, cut to fit; or no
    answer, after which its text is printed."""
    global _stopped
    answer = _exchange(data, value, [])
    if answer is not None and _kind(answer) == "too_large":
        room = answer.get("room")
        if type(room) is not int or room <= 0:
            _stopped = True
            return
        whole = data[_TEXT].encode("utf-8", "replace")
        text = whole[:room].decode("utf-8", "ignore")  # at a character's boundary
        cut = [m for m in data if m != _TEXT]
        if len(text.encode("utf-8")) < len(whole):
            cut.insert(0, _TEXT)
        answer = _exchange({_TEXT: text}, value, cut)
    if answer is None:
        print(data[_TEXT])
    elif answer.get("ok") is True:
        _stopped = answer.get("kept") is False
    elif _kind(answer) == "too_large":
        _stopped = True
    else:
        print(data[_TEXT])  # a host that does not serve displays


def _kind(answer):
    error = answer.get("error")
    return error.get("kind") if answer.get("ok") is False and isinstance(error, dict) else None


def _exchange(data, value, truncated):
    """One display frame through the door, after the streams are flushed so the host places it
    after what printed before it: the answer, or None when no host answers in protocol 1."""
    global _next_id
    _next_id += 1
    frame = {
        "v": _PROTOCOL,
        "id": _next_id,
        "op": "display",
        "value": value,
        "data": {m: _content(c) for m, c in data.items()},
        "truncated": truncated,
    }
    # A lone surrogate, which no host reads, is written as "?".
    raw = _json.dumps(frame, ensure_ascii=False, separators=(",", ":"))
    for stream in (_sys.stdout, _sys.stderr):
        try:
            stream.flush()
        except Exception:
            pass
    try:
        answer = _json.loads(_door.call(raw.encode("utf-8", "replace")))
    except (OSError, ValueError, RecursionError):  # no host, a door fault, or no JSON
        return None
    if not isinstance(answer, dict) or type(answer.get("v")) is not int:
        return None
    answer_id = answer.get("id")  # null when the host refused the frame unread
    if answer["v"] != _PROTOCOL or answer.get("ok") not in (True, False):
        return None
    if answer_id is not None and (type(answer_id) is not int or answer_id != _next_id):
        return None
    return answer


def _content(content):
    if isinstance(content, bytes):
        return {"$bytes": _binascii.b2a_base64(content, newline=False).decode("ascii")}
    return content
