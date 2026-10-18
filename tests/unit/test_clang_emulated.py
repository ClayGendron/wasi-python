"""The x86_64 host's compiler launcher, `scripts/clang-emulated` (spec 040, Decisions 5 and 7).

The launcher runs against a stand-in emulator, a script that writes its arguments one per line and
then the `QEMU_` names in its environment, in a temporary tree laid out as step 10 lays out
`build/tools/`: the emulator, the guest's root, the aarch64 SDK's `bin/` with the real clang and the
launcher beside it, and the native SDK's `bin/` whose clang links to the launcher. Each case counts
and compares the arguments the emulator received. Nothing measures time.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from harness import paths

SH = shutil.which("sh")
LAUNCHER = paths.REPO / "scripts" / "clang-emulated"
# The Windows verify job has no sh, and the launcher runs only on x86_64 Linux.
pytestmark = pytest.mark.skipif(SH is None, reason="no sh on this host")

STAND_IN = """#!/bin/sh
# The stand-in emulator: one `call` line, then each argument, then its environment's QEMU_ names.
out="$(dirname "$0")/calls"
printf 'call\\n' >> "$out"
for a in "$@"; do printf 'arg %s\\n' "$a" >> "$out"; done
env | sed -n 's/^\\(QEMU_[A-Za-z0-9_]*\\)=.*/env \\1/p' >> "$out"
"""
LOADER_FLAGS = ("LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT")
CALLER = ["-O3", "-c", "a file with spaces.c", "-o", "out.o"]


class Tree:
    """Step 10's layout under a temporary `tools/`."""

    def __init__(self, base: Path) -> None:
        t = base / "tools"
        self.emulator = t / "emulator" / "qemu-aarch64"
        self.root = t / "aarch64-root"
        self.csdk = t / "wasi-sdk-arm64-linux" / "bin"
        self.sdk = t / "wasi-sdk-x86_64-linux" / "bin"
        for d in (self.emulator.parent, self.root, self.csdk, self.sdk):
            d.mkdir(parents=True)
        self.emulator.write_text(STAND_IN)
        self.emulator.chmod(0o755)
        self.real = self.csdk / "clang-22"
        self.real.write_text("#!/bin/sh\nexit 99\n")  # an aarch64 ELF on a real host: never run
        self.real.chmod(0o755)
        (self.csdk / "clang").symlink_to("clang-22")
        self.launcher = self.csdk / "clang-emulated"
        shutil.copyfile(LAUNCHER, self.launcher)
        self.launcher.chmod(0o755)
        # The native tree's real clang is replaced by a link to the launcher; its names link to it.
        (self.sdk / "clang-22").symlink_to(self.launcher)
        for name in ("clang", "clang++", "clang-cpp", "clang-cl"):
            (self.sdk / name).symlink_to("clang-22")

    def run(self, program: Path, *args: str, **env: str) -> subprocess.CompletedProcess:
        environment = {"PATH": os.environ.get("PATH", os.defpath), **env}
        return subprocess.run(
            [str(program), *args], env=environment, capture_output=True, text=True, timeout=60
        )

    def calls(self) -> list[tuple[list[str], list[str]]]:
        """Each emulator run: its arguments and the QEMU_ names it saw."""
        out: list[tuple[list[str], list[str]]] = []
        record = self.emulator.parent / "calls"
        for line in record.read_text().splitlines() if record.exists() else []:
            kind, _, value = line.partition(" ")
            if kind == "call":
                out.append(([], []))
            else:
                out[-1][0 if kind == "arg" else 1].append(value)
        return out


@pytest.fixture
def tree(work) -> Tree:
    return Tree(work)


def _one_call(tree: Tree, done: subprocess.CompletedProcess) -> list[str]:
    assert done.returncode == 0, done.stderr
    calls = tree.calls()
    assert len(calls) == 1, calls
    args, qemu_names = calls[0]
    assert qemu_names == [], qemu_names
    for name in LOADER_FLAGS:  # the guest's loader never sees the host's
        assert sum(1 for a, b in zip(args, args[1:], strict=False) if (a, b) == ("-U", name)) == 1
    assert args.count("-L") == 1 and args[args.index("-L") + 1] == os.path.realpath(tree.root)
    assert args.count("-0") == 1
    at = args.index("-0")
    assert args[at + 1] == os.path.realpath(tree.launcher), args  # the driver's InstalledDir
    assert args[at + 2] == os.path.realpath(tree.real), args
    return args[at + 3 :]


def _modes(args: list[str]) -> list[str]:
    return [a for a in args if a.startswith("--driver-mode")]


def test_a_driver_call_through_clang_gets_no_mode_and_every_argument(tree) -> None:
    rest = _one_call(tree, tree.run(tree.sdk / "clang", *CALLER))
    assert rest.count("-no-canonical-prefixes") == 1
    assert _modes(rest) == []
    assert rest == ["-no-canonical-prefixes", *CALLER]


@pytest.mark.parametrize(
    ("name", "mode"), [("clang++", "--driver-mode=g++"), ("clang-cpp", "--driver-mode=cpp")]
)
def test_each_name_keeps_its_driver_mode(tree, name, mode) -> None:
    rest = _one_call(tree, tree.run(tree.sdk / name, *CALLER))
    assert _modes(rest) == [mode]
    assert rest.count("-no-canonical-prefixes") == 1
    assert rest[-len(CALLER) :] == CALLER


def test_any_other_name_is_refused_in_one_line(tree) -> None:
    done = tree.run(tree.sdk / "clang-cl", *CALLER)
    assert done.returncode != 0
    assert len(done.stderr.strip().splitlines()) == 1, done.stderr
    assert "clang-cl" in done.stderr
    assert tree.calls() == []


@pytest.mark.parametrize("first", ["-cc1", "-cc1as"])
def test_the_drivers_own_rerun_gets_nothing_inserted(tree, first) -> None:
    # The emulated driver re-runs itself by the -0 path, the launcher's own name.
    args = [first, "-triple", "wasm32-unknown-wasip1", "-o", "x y.o"]
    assert _one_call(tree, tree.run(tree.launcher, *args)) == args


def test_the_emulators_variables_never_reach_it(tree) -> None:
    done = tree.run(tree.sdk / "clang", "-c", "a.c", QEMU_SET_ENV="A=1", QEMU_CPU="max")
    assert _one_call(tree, done)[-2:] == ["-c", "a.c"]  # _one_call asserts no QEMU_ name arrived


@pytest.mark.parametrize(
    ("missing", "named"),
    [("emulator", "qemu-aarch64"), ("root", "aarch64-root"), ("real", "/bin/clang")],
)
def test_a_missing_piece_stops_it_in_one_line(tree, missing, named) -> None:
    path = getattr(tree, missing)
    if path.is_dir():
        path.rmdir()
    else:
        path.unlink()
    done = tree.run(tree.sdk / "clang", "-c", "a.c")
    assert done.returncode != 0
    assert len(done.stderr.strip().splitlines()) == 1, done.stderr
    assert named in done.stderr, done.stderr
    assert tree.calls() == []
