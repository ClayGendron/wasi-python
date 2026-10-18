"""The model's mapping against exceptions built to mislead it, on the host only (no guest):
what `model.answer_of` gives (a member's name, or None for a fault), and whether reading the
exception ran any of its code. Also whether a mapped exception can be kept alive by the runner:
a weak reference to it after the boundary returns.

    uv run python -I hostile.py
"""

import errno
import gc
import json
import sys
import weakref
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import model  # noqa: E402

ran = []


class Liar(OSError):
    @property
    def errno(self):  # type: ignore[override]
        ran.append("property")
        return errno.ENOENT


class EqualInt(int):
    def __eq__(self, other):
        ran.append("__eq__")
        return True

    def __hash__(self):
        ran.append("__hash__")
        return hash(errno.ENOENT)


class Meta(type):
    def __subclasscheck__(cls, sub):
        ran.append("__subclasscheck__")
        return True

    def __instancecheck__(cls, obj):
        ran.append("__instancecheck__")
        return True


class Odd(OSError, metaclass=Meta):
    pass


class MaskedClass(OSError):
    @property
    def __class__(self):  # type: ignore[override]
        ran.append("__class__")
        return FileNotFoundError


def plain(value):
    e = OSError("x")
    e.errno = value
    return e


cases = {
    "Liar(EINTR) whose property says ENOENT": Liar(errno.EINTR, "x"),
    "plain OSError, errno True": plain(True),
    "plain OSError, errno an int subclass equal to ENOENT": plain(EqualInt(errno.ENOENT)),
    "plain OSError, errno 2**70": plain(2**70),
    "plain OSError, errno -1": plain(-1),
    "plain OSError, errno '2'": plain("2"),
    "plain OSError, errno ENOENT": plain(errno.ENOENT),
    "Odd (a metaclass that says yes), errno None": Odd("x"),
    "MaskedClass whose __class__ says FileNotFoundError": MaskedClass("x"),
    "EOPNOTSUPP": OSError(errno.EOPNOTSUPP, "x"),
    "ConnectionRefusedError()": ConnectionRefusedError("x"),
    "TimeoutError() (a socket timeout)": TimeoutError("timed out"),
    "PermissionError(EPERM)": PermissionError(errno.EPERM, "x"),
    "FileNotFoundError(EACCES)": FileNotFoundError(errno.EACCES, "x"),
}
out = {}
for name, e in cases.items():
    ran.clear()
    member = model.answer_of(e)
    out[name] = [member.name if member is not None else None, list(ran)]


class Secret(FileNotFoundError):
    pass


def provider_call():
    raise Secret(errno.ENOENT, "secret")


holder = []


def boundary():
    try:
        provider_call()
    except Exception as e:
        holder.append(weakref.ref(e))
        return model.answer_of(e)


answer = boundary()
gc.collect()
out["a mapped exception is not kept"] = [answer.name, holder[0]() is None]
print(json.dumps(out, indent=1))
