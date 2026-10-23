"""The wheel's LICENSE: the project's licence, then every component licence the artifact set carries.

    uv run --no-project python -I release/licences.py append <set>          # rewrite ./LICENSE
    uv run --no-project python -I release/licences.py check <wheel> <set>   # the wheel's LICENSE

The artifact set holds one licence file per linked component under `LICENSES/`. Some of those
licences ask for a notice in the distribution's documentation (FreeType's, for one), so the wheel
carries them where an installer and a reader of the package's metadata look: its
`.dist-info/licenses/LICENSE`. `append` rewrites the checkout's LICENSE as the project's licence
followed by each `LICENSES/*.txt` in name order, each under a heading that names it; the release
workflow runs it before `uv build`. The project's licence is the text before the first heading, so
running it twice gives the same file. `check` holds a built wheel's LICENSE equal to that text.
Standard library only.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LICENSE = REPO / "LICENSE"
RULE = "=" * 78
INTRO = (
    "The wheel carries the artifact set, which links the components below. Each one's licence\n"
    "follows as the set's LICENSES folder holds it, in name order.\n"
)
# The line every appended part starts with; the project's licence is the text before the first.
MARK = f"\n\n{RULE}\nThird-party licences\n{RULE}\n"


def own_licence(text: str) -> str:
    """The project's licence: the LICENSE text before anything `append` added."""
    return text.split(MARK, 1)[0].rstrip("\n") + "\n"


def parts(set_dir: Path) -> list[Path]:
    """The set's licence files in name order; a dot file is a host's litter, not a licence."""
    return sorted(p for p in (set_dir / "LICENSES").glob("*.txt") if not p.name.startswith("."))


def combined(licence: str, set_dir: Path) -> str:
    out = [own_licence(licence).rstrip("\n"), MARK, "\n", INTRO]
    for p in parts(set_dir):
        body = p.read_text(encoding="utf-8").rstrip("\n")
        out += [f"\n{RULE}\n{p.name}\n{RULE}\n\n", body, "\n"]
    return "".join(out)


def check(wheel: Path, set_dir: Path, licence: str) -> list[str]:
    """Why the wheel's .dist-info/licenses/LICENSE is not the combined licence; empty when it is."""
    if not parts(set_dir):
        return [f"{set_dir / 'LICENSES'}: no licence files"]
    with zipfile.ZipFile(wheel) as w:
        names = [n for n in w.namelist() if n.endswith(".dist-info/licenses/LICENSE")]
        if len(names) != 1:
            return [f"{wheel.name}: {len(names)} .dist-info/licenses/LICENSE members, not one"]
        got = w.read(names[0]).decode("utf-8")
    want = combined(licence, set_dir)
    if got == want:
        return []
    missing = [p.name for p in parts(set_dir) if f"\n{RULE}\n{p.name}\n{RULE}\n" not in got]
    why = f"missing {', '.join(missing)}" if missing else "its text differs"
    return [f"{wheel.name}: .dist-info/licenses/LICENSE is not the combined licence ({why})"]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("append", help="rewrite LICENSE with the set's licences")
    a.add_argument("set", type=Path)
    c = sub.add_parser("check", help="hold a wheel's LICENSE equal to the combined text")
    c.add_argument("wheel", type=Path)
    c.add_argument("set", type=Path)
    args = p.parse_args(argv)
    licence = LICENSE.read_text(encoding="utf-8")
    if args.cmd == "append":
        if not parts(args.set):
            print(f"{args.set / 'LICENSES'}: no licence files", file=sys.stderr)
            return 1
        text = combined(licence, args.set)
        LICENSE.write_text(text, encoding="utf-8", newline="\n")
        print(f"LICENSE: the project's licence and {len(parts(args.set))} component licences")
        return 0
    errors = check(args.wheel, args.set, licence)
    for e in errors:
        print(e, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
