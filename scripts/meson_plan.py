"""Place the files a meson build installs with no install tag (spec 043, the build review's F5).

    meson_plan.py <meson build dir> <site-packages dir> <path under site-packages>...

`meson install --tags python-runtime` leaves out a file meson installs with no tag, as contourpy's
`configure_file` output `util/_build_config.py` is (meson-python installs every tag, so the wheel
has it). This copies each such file from the build folder to the destination meson's own install
plan (`meson-info/intro-install_plan.json`) gives it under site-packages. The paths named on the
command line must be exactly those destinations, so a file that a later release moves, adds or
drops stops the build instead of landing in the old place.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

SITE_PREFIXES = ("{py_platlib}/", "{py_purelib}/")


def untagged(build: Path) -> list[tuple[Path, str]]:
    """(built file, its path under site-packages) for each file the plan installs with no tag."""
    plan = json.loads((build / "meson-info" / "intro-install_plan.json").read_text("utf-8"))
    found = []
    for group in sorted(plan):
        for source, info in sorted(plan[group].items()):
            if info.get("tag") is not None:
                continue
            dest = info["destination"]
            prefix = next((p for p in SITE_PREFIXES if dest.startswith(p)), None)
            if prefix is None:
                raise SystemExit(f"{source}: installed with no tag outside site-packages ({dest})")
            found.append((Path(source), dest[len(prefix) :]))
    return found


def place_untagged(build: Path, site: Path, want: list[str]) -> None:
    """Copy each untagged file to its planned place under `site`; stop unless the planned paths
    are exactly `want`."""
    placed = untagged(build)
    names = sorted(rel for _, rel in placed)
    if names != sorted(want):
        raise SystemExit(f"meson installs {names} with no tag, not {sorted(want)}")
    for source, rel in placed:
        dest = site / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    place_untagged(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:])
