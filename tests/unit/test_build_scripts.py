"""Finder litter never breaks a build (spec 018): `remove` retries, and the zip, the licences and
the artifact set never carry litter. Each case works on a temporary folder; `remove` runs under a
POSIX `sh` with `rm` replaced by a shell function that counts its calls. Nothing measures time."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

from harness import paths

sys.path.insert(0, str(paths.REPO / "scripts"))

import assemble_artifacts  # noqa: E402
import litter  # noqa: E402
import make_stdlib_zip  # noqa: E402

REMOVE = paths.REPO / "scripts" / "steps" / "remove.sh"
SH = shutil.which("sh")


def _remove(target, fails: int, *more, removes: bool = True) -> tuple[int, int, str]:
    """`remove target more...` under `set -eu`, with an `rm` that fails its first `fails` calls (a
    negative number: always) and then removes for real, or, with `removes=False`, answers success
    without removing; returns the exit code, the calls, stderr."""
    then = 'command rm "$@"' if removes else "return 0"
    script = f"""
set -eu
calls=0
rm() {{
  calls=$((calls + 1))
  echo "$calls" > "$COUNT"
  if [ {fails} -lt 0 ] || [ "$calls" -le {fails} ]; then
    echo "rm: {{}}: Directory not empty" >&2
    return 1
  fi
  {then}
}}
. "$REMOVE"
remove "$TARGET" {" ".join(f'"{m}"' for m in more)}
"""
    count = target.parent / "count"
    env = {
        "PATH": os.environ.get("PATH", os.defpath),
        "COUNT": str(count),
        "REMOVE": str(REMOVE),
        "TARGET": str(target),
    }
    out = subprocess.run([SH, "-c", script], env=env, capture_output=True, text=True, timeout=60)
    calls = int(count.read_text()) if count.exists() else 0
    return out.returncode, calls, out.stderr


def _tree(tmp_path):
    target = tmp_path / "out"
    (target / "deep").mkdir(parents=True)
    (target / "deep" / ".DS_Store").write_bytes(b"x")
    return target


@pytest.mark.parametrize(("fails", "calls"), [(0, 1), (1, 2), (2, 3)])
def test_remove_retries_until_the_path_is_gone(tmp_path, fails, calls) -> None:
    if SH is None:
        pytest.skip("needs: a POSIX sh")  # blocked, never passed or failed (spec 018, B)
    target = _tree(tmp_path)
    assert _remove(target, fails)[:2] == (0, calls)
    assert not target.exists()


def test_remove_stops_after_three_attempts_with_one_line(tmp_path) -> None:
    if SH is None:
        pytest.skip("needs: a POSIX sh")
    target = _tree(tmp_path)
    code, calls, err = _remove(target, -1)
    assert (code, calls) == (1, 3) and target.exists()
    assert err.strip().splitlines()[-1] == f"ERROR: cannot remove {target}"
    assert err.count("Directory not empty") == 1  # only the third attempt's error is shown


def test_remove_removes_a_dangling_link_or_says_so(tmp_path) -> None:
    if SH is None:
        pytest.skip("needs: a POSIX sh")
    if sys.platform == "win32":
        pytest.skip("needs: the privilege to make a link (Windows)")
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "nothing")
    assert _remove(link, 0)[:2] == (0, 1) and not link.is_symlink()
    link.symlink_to(tmp_path / "nothing")  # an rm that reports success but leaves the link
    code, calls, err = _remove(link, 0, removes=False)
    assert (code, calls) == (1, 1) and link.is_symlink() and "cannot remove" in err


def test_remove_removes_every_path_it_is_given(tmp_path) -> None:
    if SH is None:
        pytest.skip("needs: a POSIX sh")
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir()
    second.mkdir()
    assert _remove(first, 0, second)[:2] == (0, 2)
    assert not first.exists() and not second.exists()


def test_the_zip_walk_skips_litter(tmp_path) -> None:
    for tree in ("a", "b"):
        (tmp_path / tree / "pkg").mkdir(parents=True)
        (tmp_path / tree / "pkg" / f"mod_{tree}.py").write_text("x = 1\n")
        for name in litter.OS_LITTER:
            (tmp_path / tree / name).write_bytes(b"litter")
            (tmp_path / tree / "pkg" / name).write_bytes(b"litter")
    names = [n for tree in ("a", "b") for _, n in make_stdlib_zip.walk(tmp_path / tree)]
    assert sorted(names) == ["pkg/mod_a.py", "pkg/mod_b.py"]


def test_step_90_drops_litter_and_skips_it_in_licences(tmp_path) -> None:
    (tmp_path / "LICENSES").mkdir(parents=True)
    (tmp_path / "LICENSES" / "A_LICENSE").write_text("a")
    (tmp_path / "LICENSES" / ".DS_Store").write_bytes(b"x")
    (tmp_path / "Thumbs.db").write_bytes(b"x")
    (tmp_path / "python.wasm").write_bytes(b"\0asm")
    assert [p.name for p in assemble_artifacts.licence_files(tmp_path / "LICENSES")] == [
        "A_LICENSE"
    ]
    assemble_artifacts.drop_litter(tmp_path)
    assert sorted(p.name for p in tmp_path.rglob("*")) == ["A_LICENSE", "LICENSES", "python.wasm"]


def test_step_90_never_lists_litter(tmp_path) -> None:
    (tmp_path / "LICENSES").mkdir()
    for name in ("python.wasm", "LICENSES/zlib.txt", ".DS_Store", "LICENSES/Thumbs.db"):
        (tmp_path / name).write_bytes(b"x")
    names = [p.relative_to(tmp_path).as_posix() for p in assemble_artifacts.listed_files(tmp_path)]
    assert names == ["LICENSES/zlib.txt", "python.wasm"]


def test_step_90_removes_or_says_why(tmp_path, monkeypatch) -> None:
    assemble_artifacts._remove(tmp_path / "never-made")  # already gone: success
    folder = tmp_path / "set"
    (folder / "x").mkdir(parents=True)
    assemble_artifacts._remove(folder)
    assert not folder.exists()
    folder.mkdir()
    monkeypatch.setattr(shutil, "rmtree", lambda *a, **k: None)  # a folder that will not go
    with pytest.raises(SystemExit, match="ERROR: cannot remove"):
        assemble_artifacts._remove(folder)


def test_the_scripts_litter_is_the_judges() -> None:
    assert set(litter.OS_LITTER) == set(paths.OS_LITTER)
