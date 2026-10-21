"""Install a meson build's Python package from its install plan, without `meson install`.

    install_from_plan.py <meson build dir> <dest dir> <extension list out> <module suffix>
    install_from_plan.py --targets <meson build dir>
    install_from_plan.py --modules-only <meson build dir> <extension list out> <module suffix>

`meson install` is not run: on a macOS host it fixes install names in installed extension modules,
which here are archives. This reads `meson-info/intro-install_plan.json` and copies each file
tagged `python-runtime` to its destination under <dest dir>, the `{py_platlib}/` or
`{py_purelib}/` at its head taken off: Python sources, generated files (`__config__.py`), vendored
packages and data files land where an install would put them. A file tagged `tests` is skipped,
and so is every extension module (a target whose name ends with <module suffix>); each extension
module not tagged `tests` is written to <extension list out>, one line each: its build path, its
install path under <dest dir>, and its tag, tab-separated, sorted by install path. Another
destination or tag on a file to install stops the run, naming it.

With `--targets` it prints, one per line and relative to the build folder, the targets ninja must
build for that install: every installed target not tagged `tests`. A test module need not even
compile for wasm32-wasip1 (scipy.special._test_internal sets the FPU's rounding modes, which WASI
lacks), and none is linked.

With `--modules-only` it writes <extension list out> as above and copies
nothing: scikit-learn installs its Python package with `install_subdir`, whose files meson does not
tag, so step 58 copies the package from the patched source tree and takes only the module list
from the plan. Every other entry of the plan is ignored, whatever its tag. It prints how many
modules it listed and how many tagged `tests` it left out.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

PREFIXES = ("{py_platlib}/", "{py_purelib}/")
SKIPPED_TAGS = ("tests", "devel")


def relative(destination: str, what: str) -> str:
    for prefix in PREFIXES:
        if destination.startswith(prefix):
            rel = destination[len(prefix) :]
            if rel.startswith("/") or ".." in Path(rel).parts:
                raise SystemExit(f"{what}: destination {destination!r} leaves the package folder")
            return rel
    raise SystemExit(f"{what}: destination {destination!r} is not under {' or '.join(PREFIXES)}")


def plan(build: Path, suffix: str) -> tuple[list[tuple[str, str]], list[tuple[str, str, str]]]:
    """(files to copy as (source, relative destination), extension modules as (build path,
    relative install path, tag))."""
    data = json.loads((build / "meson-info" / "intro-install_plan.json").read_text())
    files: list[tuple[str, str]] = []
    modules: list[tuple[str, str, str]] = []
    for section, entries in sorted(data.items()):
        for source, entry in sorted(entries.items()):
            tag = entry.get("tag")
            destination = entry["destination"]
            if section == "targets" and source.endswith(suffix):
                if tag != "tests":
                    modules.append((source, relative(destination, source), tag or ""))
                continue
            if tag in SKIPPED_TAGS:
                continue
            if tag != "python-runtime":
                raise SystemExit(f"{source}: tag {tag!r} in {section}, not python-runtime")
            files.append((source, relative(destination, source)))
    return files, sorted(modules, key=lambda m: m[1])


def modules_only(build: Path, suffix: str) -> tuple[list[tuple[str, str, str]], int]:
    """(extension modules as plan() lists them, how many tagged `tests` were left out); nothing
    else of the plan is read."""
    data = json.loads((build / "meson-info" / "intro-install_plan.json").read_text())
    modules: list[tuple[str, str, str]] = []
    tests = 0
    for source, entry in sorted(data.get("targets", {}).items()):
        if not source.endswith(suffix):
            continue
        tag = entry.get("tag")
        if tag == "tests":
            tests += 1
            continue
        modules.append((source, relative(entry["destination"], source), tag or ""))
    return sorted(modules, key=lambda m: m[1]), tests


def targets(build: Path) -> list[str]:
    """The installed targets not tagged `tests`, relative to the build folder, sorted."""
    data = json.loads((build / "meson-info" / "intro-install_plan.json").read_text())
    root = str(build.resolve()) + "/"
    out = []
    for source, entry in data.get("targets", {}).items():
        if entry.get("tag") == "tests":
            continue
        if not source.startswith(root):
            raise SystemExit(f"{source}: a target outside the build folder {root}")
        out.append(source[len(root) :])
    return sorted(out)


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "--targets":
        print("\n".join(targets(Path(argv[1]))))
        return 0
    if len(argv) == 4 and argv[0] == "--modules-only":
        build, listing, suffix = Path(argv[1]), Path(argv[2]), argv[3]
        modules, tests = modules_only(build, suffix)
        listing.write_text("".join(f"{b}\t{r}\t{t}\n" for b, r, t in modules))
        print(f"{len(modules)} extension modules listed; {tests} tagged tests left out")
        return 0
    if len(argv) != 4:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    build, dest, listing, suffix = Path(argv[0]), Path(argv[1]), Path(argv[2]), argv[3]
    files, modules = plan(build, suffix)
    for source, rel in files:
        target = dest / rel
        if target.exists():
            raise SystemExit(f"{rel}: two plan entries install it")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    listing.write_text("".join(f"{b}\t{r}\t{t}\n" for b, r, t in modules))
    print(f"installed {len(files)} files under {dest}; {len(modules)} extension modules listed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
