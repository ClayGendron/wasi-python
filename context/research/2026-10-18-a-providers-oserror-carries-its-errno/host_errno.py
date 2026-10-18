"""The host's errno numbers for the 21 names of wasi_python.Errno, and the aliases and
subclass facts the design leans on. Standard library only, so it runs on any CPython 3.10+.
Prints one JSON object."""

import errno
import json
import platform
import sys

NAMES = [
    "EACCES", "EBUSY", "ECANCELED", "EDQUOT", "EEXIST", "EFBIG", "EINVAL", "EIO", "EISDIR",
    "ENAMETOOLONG", "ENOENT", "ENOSPC", "ENOSYS", "ENOTDIR", "ENOTEMPTY", "ENOTSUP", "EPERM",
    "EROFS", "ESTALE", "ETIMEDOUT", "EXDEV",
]
ALIASES = ["EOPNOTSUPP", "EWOULDBLOCK", "EAGAIN", "EINTR", "EBADF", "EFAULT", "ENOTCAPABLE"]

numbers = {n: getattr(errno, n, None) for n in NAMES + ALIASES}
present = {n: v for n, v in numbers.items() if n in NAMES and v is not None}
by_number: dict[int, list[str]] = {}
for n, v in present.items():
    by_number.setdefault(v, []).append(n)
print(json.dumps({
    "host": f"{platform.system()} {platform.machine()} CPython {sys.version.split()[0]}",
    "numbers": numbers,
    "missing": [n for n in NAMES if numbers[n] is None],
    "shared_numbers": {k: v for k, v in by_number.items() if len(v) > 1},
    "errorcode_of_ENOTSUP": errno.errorcode.get(getattr(errno, "ENOTSUP", -1)),
    "subclass_errno_none": {
        c.__name__: c("only a message").errno
        for c in (FileNotFoundError, PermissionError, FileExistsError, IsADirectoryError,
                  NotADirectoryError, TimeoutError, InterruptedError, BlockingIOError)
    },
    "constructor_picks_subclass": {
        n: type(OSError(getattr(errno, n), "x")).__name__
        for n in ("ENOENT", "EACCES", "EPERM", "EEXIST", "EISDIR", "ENOTDIR", "ETIMEDOUT",
                  "EINTR", "EAGAIN", "EIO", "ENOSPC")
    },
}, indent=1, sort_keys=True))
