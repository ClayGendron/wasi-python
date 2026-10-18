"""Fetch the upstream test kit into build/upstream/wheels/ (spec 050, Decision 2).

Run by hand, `uv run python tests/upstream/fetch.py`; the judge never fetches. Each wheel is
downloaded to a temporary name and renamed only after its SHA-256 equals its `kit.txt` line. A
mismatch deletes the download and exits non-zero. Nothing is unpacked or run here.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KIT = HERE / "kit.txt"
WHEELS = REPO / "build" / "upstream" / "wheels"


def kit_lines(text: str) -> list[tuple[str, str]]:
    """(sha256, url) per non-empty line."""
    out = []
    for line in text.splitlines():
        if line.strip():
            sha, url = line.split("  ", 1)
            out.append((sha, url.strip()))
    return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(sha: str, url: str, wheels: Path) -> str | None:
    """Download one wheel; None when it is in place with its hash, else why it is not."""
    dest = wheels / url.rsplit("/", 1)[1]
    if dest.is_file() and sha256_file(dest) == sha:
        return None
    part = dest.with_name(dest.name + ".part")
    with urllib.request.urlopen(url, timeout=120) as r, part.open("wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    got = sha256_file(part)
    if got != sha:
        part.unlink()
        return f"{dest.name}: SHA-256 {got}, kit.txt says {sha}"
    part.replace(dest)
    return None


def main() -> int:
    WHEELS.mkdir(parents=True, exist_ok=True)
    errors = [e for sha, url in kit_lines(KIT.read_text()) if (e := fetch(sha, url, WHEELS))]
    for e in errors:
        print(e, file=sys.stderr)
    if not errors:
        print(f"the kit is in {WHEELS}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
