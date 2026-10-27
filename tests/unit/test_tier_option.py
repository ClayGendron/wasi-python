"""The `--tier` option exists before any conftest is read, and only the judge's own environment
declares it: a dev-only workspace package's pytest11 entry point, never the wheel users install."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from harness import paths, scoreboard


def _pytest(*args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST_")}
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", *args],
        cwd=paths.REPO,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_tier_release_parses_with_no_path_given() -> None:
    """With no path, pytest parses the command line before it reads tests/conftest.py, so an option
    the harness plugin adds there is unknown; the entry point's is not."""
    r = _pytest("--tier", "release", "--collect-only", "-q")
    assert "unrecognized arguments" not in r.stderr, r.stderr[-400:]
    assert r.returncode == 0, (r.stdout + r.stderr)[-400:]
    assert " tests collected" in r.stdout.rstrip().splitlines()[-1], r.stdout[-400:]


def test_the_option_offers_the_tiers_the_scoreboard_judges() -> None:
    import wasi_python_judge_options as options

    assert options.TIERS == scoreboard.TIERS


def test_the_wheel_declares_no_pytest11_entry_point(tmp_path: Path) -> None:
    """The wheel's metadata is what every user installs: a pytest11 group there would load a
    plugin into every pytest run of every project that installs the package."""
    uv = os.environ.get("UV") or shutil.which("uv") or "uv"
    r = subprocess.run(
        [uv, "build", "--wheel", "--out-dir", str(tmp_path), "--no-progress"]
        + ["--build-constraints", "release/build-constraints.txt", "--require-hashes"],
        cwd=paths.REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, (r.stdout + r.stderr)[-400:]
    (wheel,) = tmp_path.glob("wasi_python-*.whl")
    with zipfile.ZipFile(wheel) as z:
        names = [n for n in z.namelist() if n.endswith(".dist-info/entry_points.txt")]
        text = z.read(names[0]).decode() if names else ""
    groups = [line.strip() for line in text.splitlines() if line.startswith("[")]
    assert "[console_scripts]" in groups, text
    assert "[pytest11]" not in groups, text


def test_a_copy_of_the_options_module_steers_only_with_the_judges_bytes(tmp_path: Path) -> None:
    from harness import plugin

    files = paths.judge_files()
    real = paths.REPO / plugin.JUDGE_OPTIONS
    same = tmp_path / "same" / real.name
    same.parent.mkdir()
    same.write_bytes(real.read_bytes())
    other = tmp_path / "other" / real.name
    other.parent.mkdir()
    other.write_bytes(real.read_bytes() + b"\n# changed\n")
    renamed = tmp_path / "renamed.py"
    renamed.write_bytes(real.read_bytes())
    assert plugin.is_judged_options_copy(same, files)
    assert not plugin.is_judged_options_copy(other, files)
    assert not plugin.is_judged_options_copy(renamed, files)
