"""The type checker's two passes over a copy of the runner's package: what the Windows pass reads
that the Linux pass cannot, and each platform class held to the protocol the runner uses it
through. Each row plants one mistake in the copy and reads which pass names it."""

from __future__ import annotations

import shutil
from pathlib import Path

from harness import paths, typecheck

WINDOWS = "src/wasi_python/_platform_windows.py"
PLATFORM = "src/wasi_python/_platform.py"


def _copy(tmp_path: Path) -> Path:
    """The package and its configuration, as the passes read them in the repository."""
    shutil.copytree(
        paths.REPO / "src" / "wasi_python",
        tmp_path / "src" / "wasi_python",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    shutil.copy2(paths.REPO / "pyproject.toml", tmp_path / "pyproject.toml")
    return tmp_path


def _plant(path: Path, old: str, new: str) -> int:
    """Replace the one occurrence of `old` and return the line it starts on."""
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, old
    path.write_text(text.replace(old, new), encoding="utf-8")
    return text[: text.index(old)].count("\n") + 1


def test_the_windows_pass_reads_what_the_linux_pass_cannot(tmp_path) -> None:
    """An argument of the wrong type to a Windows-only call is named once, by the Windows pass:
    Linux's stubs have no `WinDLL`, so only win32's can say what it takes."""
    root = _copy(tmp_path)
    line = _plant(
        root / WINDOWS,
        'ctypes.WinDLL("kernel32", use_last_error=True)',
        'ctypes.WinDLL("kernel32", use_last_error="yes")',
    )
    findings = typecheck.run(root)
    assert len(findings) == 1, findings
    (found,) = findings
    assert found.startswith("win32: "), found
    assert f"_platform_windows.py:{line}: error: " in found, found
    assert found.endswith("[arg-type]"), found


def test_each_platform_class_is_held_to_the_protocol(tmp_path) -> None:
    """A member the protocol gains and no class has is named for every class: the Windows class
    by the Windows pass, the Linux class and the macOS and plain POSIX pair by the Linux pass,
    which reads the platform choice as Linux's and skips the other branches."""
    root = _copy(tmp_path)
    _plant(
        root / PLATFORM,
        "class _Platform(Protocol):\n",
        "class _Platform(Protocol):\n    def planted_member(self) -> int: ...\n\n",
    )
    findings = typecheck.run(root)
    windows = [f for f in findings if f.startswith("win32: ") and '"_Windows"' in f]
    linux = [f for f in findings if f.startswith("linux: ") and '"_Linux"' in f]
    pair = [f for f in findings if f.startswith("linux: ") and "tuple[_Darwin, _Posix]" in f]
    assert windows and linux and pair, findings
    assert set(findings) == {*windows, *linux, *pair}, findings
