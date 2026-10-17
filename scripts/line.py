"""The release line for the Python build scripts: `scripts/line.conf`, parsed (spec 005).

The grammar is one `NAME=value` per line, the value only letters, digits and `._+-`, and `#`
starting a comment line; any other line, a blank one included, is an error (so the file is also
safe for the shell to source). `PYTHON_MM` and `PYTHON_TAG` are derived from `PYTHON_VERSION`, as
`steps/common.sh` derives them, so they cannot disagree with it.
"""

import re
from pathlib import Path

CONF = Path(__file__).resolve().with_name("line.conf")
LINE = re.compile(r"([A-Z][A-Z0-9_]*)=([A-Za-z0-9._+-]+)")


def read(path: Path = CONF) -> dict[str, str]:
    """`line.conf`'s names and values, plus the two derived ones."""
    values: dict[str, str] = {}
    for number, text in enumerate(path.read_text().splitlines(), 1):
        if text.startswith("#"):
            continue
        match = LINE.fullmatch(text)
        if match is None:
            raise SystemExit(f"{path.name}:{number}: not NAME=value: {text!r}")
        values[match[1]] = match[2]
    major, minor, _ = values["PYTHON_VERSION"].split(".")
    values["PYTHON_MM"] = f"{major}.{minor}"
    values["PYTHON_TAG"] = f"{major}{minor}"
    return values


def target() -> tuple[int, int]:
    """The guest's (major, minor), which the host Python that compiles for it must match."""
    major, minor = read()["PYTHON_MM"].split(".")
    return int(major), int(minor)
