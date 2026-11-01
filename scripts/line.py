"""The release line for the Python build scripts: `scripts/line.conf`, parsed.

The grammar is one `NAME=value` per line, the value only letters, digits and `._+-`, and `#`
starting a comment line; any other line, a blank one included, is an error (so the file is also
safe for the shell to source). `PYTHON_MM` and `PYTHON_TAG` are derived from `PYTHON_VERSION`, as
`steps/common.sh` derives them, so they cannot disagree with it.

The host-specific names (`WASI_SDK_DIR`, ...) are set for the build host this runs on, from its
key's lines, as `line.sh` sets them. On any other host (Windows, an Intel
Mac) they are left unset and nothing is raised: such a host reads the line but builds nothing, and
a reader that needs a host name says so itself.
"""

import platform
import re
from pathlib import Path

CONF = Path(__file__).resolve().with_name("line.conf")
LINE = re.compile(r"([A-Z][A-Z0-9_]*)=([A-Za-z0-9._+-]+)")
# (platform.system(), platform.machine()) -> the build host's key in line.conf
HOSTS = {
    ("Darwin", "arm64"): "MACOS_ARM64",
    ("Linux", "aarch64"): "LINUX_AARCH64",
    ("Linux", "arm64"): "LINUX_AARCH64",
    ("Linux", "x86_64"): "LINUX_X86_64",
}
HOST_NAMES = (
    "WASI_SDK_DIR",
    "WASMTIME_DIR",
    "HOST_PYTHON_ARCHIVE",
    "CYTHON_WHEEL",
    "NINJA_WHEEL",
    "PKGCONF_WHEEL",
    "NUMPY_HOST_WHEEL",  # f2py's numpy, for scipy's build
    "CFFI_WHEEL",  # the build host's cffi, which writes cairocffi's bindings as C
)


def read(path: Path = CONF) -> dict[str, str]:
    """`line.conf`'s names and values, plus the two derived ones and, on a build host, its own
    inputs under the plain names."""
    values: dict[str, str] = {}
    for number, text in enumerate(path.read_text().splitlines(), 1):
        if text.startswith("#"):
            continue
        match = LINE.fullmatch(text)
        if match is None:
            raise SystemExit(f"{path.name}:{number}: not NAME=value: {text!r}")
        values[match[1]] = match[2]
    key = HOSTS.get((platform.system(), platform.machine()))
    for name in HOST_NAMES if key else ():
        if f"{key}_{name}" not in values:
            raise SystemExit(f"{path.name} has no {key}_{name}")
        values[name] = values[f"{key}_{name}"]
    major, minor, _ = values["PYTHON_VERSION"].split(".")
    values["PYTHON_MM"] = f"{major}.{minor}"
    values["PYTHON_TAG"] = f"{major}{minor}"
    return values


def target() -> tuple[int, int]:
    """The guest's (major, minor), which the host Python that compiles for it must match."""
    major, minor = read()["PYTHON_MM"].split(".")
    return int(major), int(minor)
