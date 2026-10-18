"""A model of the proposed boundary, for the experiments only: importing it replaces
`wasi_python.mounts._Files._invoke` with one that turns a provider's OSError into an `Errno`
answer when its errno (or, with no usable errno, its class) names one of the closed set. Not
the implementation: the builder writes that in `mounts.py` from the specification."""

import errno as host_errno

from wasi_python import mounts as M
from wasi_python.mounts import Errno

# A host name that the guest's own C library spells as another member (wasi-libc's errno.h
# defines EOPNOTSUPP as ENOTSUP).
ALIASES = {"EOPNOTSUPP": "ENOTSUP"}


def _host_table() -> dict[int, Errno]:
    """The host's errno number for each member's name, read from the host's errno module."""
    table: dict[int, Errno] = {}
    for member in Errno:
        number = getattr(host_errno, member.name, None)
        if type(number) is int:
            table.setdefault(number, member)
    for alias, name in ALIASES.items():
        number = getattr(host_errno, alias, None)
        if type(number) is int:
            table.setdefault(number, Errno[name])
    return table


HOST = _host_table()
# With no errno that names a member: the class, by PEP 3151's table, where it names one errno.
CLASSES = (
    (FileNotFoundError, Errno.ENOENT),
    (FileExistsError, Errno.EEXIST),
    (IsADirectoryError, Errno.EISDIR),
    (NotADirectoryError, Errno.ENOTDIR),
    (PermissionError, Errno.EACCES),
    (TimeoutError, Errno.ETIMEDOUT),
)
_ERRNO = OSError.__dict__["errno"]  # the slot itself, past any subclass's property


def answer_of(e: BaseException) -> Errno | None:
    """The member an exception stands for, or None (a fault). Runs no provider code."""
    try:
        kind = type(e)
        if not issubclass(kind, OSError):
            return None
        number = _ERRNO.__get__(e, kind)
        if type(number) is int and (member := HOST.get(number)) is not None:
            return member
        for base, member in CLASSES:
            if issubclass(kind, base):
                return member
        return None
    except Exception:
        return None


def _invoke(self, mount, method, args):
    self.total += 1
    self.calls[method] += 1
    try:
        return 0, getattr(mount.provider, method)(*args)
    except Exception as e:
        if (member := answer_of(e)) is not None:
            return 0, member
        self._fault(method, args[0], M._described(e))
        return M.EIO, None


M._Files._invoke = _invoke
