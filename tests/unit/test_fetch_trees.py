"""`tests/upstream/fetch.py --shard`: the kit and every upstream tree, verified, unpacked and
patched, with nothing fetched from the network."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import subprocess
import tarfile
from pathlib import Path

import pytest

from harness import paths

_spec = importlib.util.spec_from_file_location(
    "upstream_fetch", paths.REPO / "tests" / "upstream" / "fetch.py"
)
fetch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetch)


def _tarball(top: str, members: dict[str, bytes], links: dict[str, str] | None = None) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for name, data in members.items():
            info = tarfile.TarInfo(f"{top}/{name}" if not name.startswith("/") else name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
        for name, target in (links or {}).items():
            info = tarfile.TarInfo(f"{top}/{name}")
            info.type = tarfile.SYMTYPE
            info.linkname = target
            t.addfile(info)
    return buf.getvalue()


class World:
    """A temporary repository: downloads/SHA256SUMS, a download script, patches, a fake network."""

    def __init__(self, tmp: Path, tarballs: dict[str, bytes]) -> None:
        self.tmp = tmp
        self.downloads = tmp / "downloads"
        self.build = tmp / "build"
        self.patches = tmp / "patches"
        self.downloads.mkdir()
        self.patches.mkdir()
        self.served = dict(tarballs)
        self.fetched: list[str] = []
        self.applied: list[list[str]] = []
        self.script = tmp / "00_download.sh"
        self.script.write_text(
            "".join(f"get https://example.org/{n} {n}\n" for n in tarballs)
            + "get https://example.org/other.tar.gz other.tar.gz\n"
        )
        (self.downloads / "SHA256SUMS").write_text(
            "".join(f"{hashlib.sha256(d).hexdigest()}  {n}\n" for n, d in tarballs.items())
        )

    def urlopen(self, url, timeout=0):
        name = url.rsplit("/", 1)[1]
        self.fetched.append(name)
        return io.BytesIO(self.served[name])

    def run(self, argv, check=False):
        self.applied.append(argv)
        return subprocess.CompletedProcess(argv, 0)

    def go(self, monkeypatch, packages=("numpy", "pandas")):
        monkeypatch.setattr(fetch.urllib.request, "urlopen", self.urlopen)
        return fetch.fetch_trees(
            list(packages),
            downloads=self.downloads,
            build=self.build,
            script=self.script,
            applier=Path("apply.sh"),
            patches=self.patches,
            run=self.run,
        )


GOOD = {
    "numpy-2.5.2.tar.gz": _tarball("numpy-2.5.2", {"numpy/tests/test_a.py": b"x"}),
    "pandas-3.0.6.tar.gz": _tarball("pandas-3.0.6", {"pandas/tests/test_b.py": b"y"}),
}


def test_a_shard_without_groups_fetches_nothing(capsys) -> None:
    assert fetch.main(["--shard", "own-rest"]) == 0
    assert "nothing to fetch" in capsys.readouterr().out


def test_both_trees_are_fetched_unpacked_and_patched(tmp_path, monkeypatch) -> None:
    w = World(tmp_path, GOOD)
    assert w.go(monkeypatch) == []
    assert sorted(w.fetched) == sorted(GOOD)
    assert (w.build / "numpy-2.5.2" / "numpy" / "tests" / "test_a.py").read_bytes() == b"x"
    assert (w.build / "pandas-3.0.6" / "pandas" / "tests" / "test_b.py").read_bytes() == b"y"
    assert w.applied == [
        ["sh", "apply.sh", str(w.build / "numpy-2.5.2"), str(w.patches / "numpy-2.5.2")],
        ["sh", "apply.sh", str(w.build / "pandas-3.0.6"), str(w.patches / "pandas-3.0.6")],
    ]


def test_a_hash_mismatch_deletes_the_part_file_and_names_it(tmp_path, monkeypatch) -> None:
    w = World(tmp_path, GOOD)
    w.served["pandas-3.0.6.tar.gz"] = b"other bytes"
    errors = w.go(monkeypatch)
    assert errors and errors[0].startswith("pandas-3.0.6.tar.gz: SHA-256"), errors
    assert not list(w.downloads.glob("*.part"))
    assert not (w.downloads / "pandas-3.0.6.tar.gz").exists()
    assert not w.applied


def test_a_name_with_no_get_line_or_no_pin_is_refused(tmp_path, monkeypatch) -> None:
    w = World(tmp_path, GOOD)
    w.script.write_text("get https://example.org/numpy-2.5.2.tar.gz numpy-2.5.2.tar.gz\n")
    assert w.go(monkeypatch) == ["pandas-3.0.6.tar.gz: no get line in 00_download.sh"]
    (tmp_path / "b").mkdir()
    w = World(tmp_path / "b", GOOD)
    pins = (w.downloads / "SHA256SUMS").read_text().splitlines()
    (w.downloads / "SHA256SUMS").write_text(pins[0] + "\n")
    errors = w.go(monkeypatch)
    assert errors == ["pandas: 0 pinned tarballs in downloads/SHA256SUMS, not one"]
    assert not w.fetched


@pytest.mark.parametrize(
    ("members", "links"),
    [
        ({"../escape.py": b"x"}, None),
        ({"/abs/escape.py": b"x"}, None),
        ({"ok.py": b"x"}, {"link": "../../outside"}),
    ],
    ids=["a .. member", "an absolute name", "a link out of the tree"],
)
def test_a_member_outside_the_tree_is_refused(tmp_path, monkeypatch, members, links) -> None:
    bad = dict(GOOD)
    bad["pandas-3.0.6.tar.gz"] = _tarball("pandas-3.0.6", members, links)
    w = World(tmp_path, bad)
    errors = w.go(monkeypatch)
    assert errors and errors[0].startswith("pandas-3.0.6.tar.gz:"), errors
    assert not (tmp_path / "escape.py").exists() and not (tmp_path / "outside").exists()


def test_a_tree_already_there_is_refused(tmp_path, monkeypatch) -> None:
    w = World(tmp_path, GOOD)
    (w.build / "numpy-2.5.2").mkdir(parents=True)
    errors = w.go(monkeypatch)
    assert errors and "is already there" in errors[0], errors
    assert not w.applied


# ---------------------------------------------------------------------------------------------
# CPython's tests have their own stage


def _xz(top: str, members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz") as t:
        for name, data in members.items():
            info = tarfile.TarInfo(f"{top}/{name}")
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def test_a_shard_with_a_cpython_group_fetches_the_cpython_tarball_and_its_family() -> None:
    assert fetch.shard_packages("upstream-numpy-a") == ["numpy", "pandas", "cpython"]
    assert fetch.shard_packages("upstream-windows") == ["numpy", "pandas", "cpython"]
    assert fetch.shard_packages("upstream-groupby") == ["numpy", "pandas"]


def test_the_kit_is_fetched_only_for_a_pytest_group() -> None:
    assert fetch.needs_kit(["numpy", "pandas", "cpython"])
    assert not fetch.needs_kit(["cpython"])


def test_the_cpython_tree_is_fetched_verified_unpacked_and_patched(tmp_path, monkeypatch) -> None:
    tar = {"Python-3.15.0.tar.xz": _xz("Python-3.15.0", {"Lib/test/test_a.py": b"z"})}
    w = World(tmp_path, tar)
    assert w.go(monkeypatch, packages=("cpython",)) == []
    assert w.fetched == ["Python-3.15.0.tar.xz"]
    assert (w.build / "Python-3.15.0" / "Lib" / "test" / "test_a.py").read_bytes() == b"z"
    assert w.applied == [
        ["sh", "apply.sh", str(w.build / "Python-3.15.0"), str(w.patches / "Python-3.15.0")]
    ]


def test_a_cpython_hash_mismatch_deletes_the_part_file(tmp_path, monkeypatch) -> None:
    tar = {"Python-3.15.0.tar.xz": _xz("Python-3.15.0", {"Lib/test/test_a.py": b"z"})}
    w = World(tmp_path, tar)
    w.served["Python-3.15.0.tar.xz"] = _xz("Python-3.15.0", {"Lib/test/test_a.py": b"changed"})
    errors = w.go(monkeypatch, packages=("cpython",))
    assert errors and "Python-3.15.0.tar.xz" in errors[0]
    assert not list(w.downloads.glob("*.part"))


# ---------------------------------------------------------------------------------------------
# scipy's, scikit-learn's and statsmodels' families: a tree each, fetched only by their shards


def test_a_shard_with_a_scipy_group_fetches_the_kit_and_scipys_tarball_only() -> None:
    assert fetch.shard_packages("upstream-sci-smoke-a") == ["scipy"]
    assert fetch.shard_packages("upstream-sci-smoke-b") == ["scikit_learn", "statsmodels"]
    assert fetch.needs_kit(["scipy"])
    assert "scipy" not in fetch.shard_packages("upstream-plot-a")


SCIPY = {"scipy-1.18.1.tar.gz": _tarball("scipy-1.18.1", {"scipy/linalg/tests/test_a.py": b"s"})}


def test_the_scipy_tree_is_fetched_verified_unpacked_and_patched(tmp_path, monkeypatch) -> None:
    w = World(tmp_path, SCIPY)
    assert w.go(monkeypatch, packages=("scipy",)) == []
    assert w.fetched == ["scipy-1.18.1.tar.gz"]
    assert (w.build / "scipy-1.18.1/scipy/linalg/tests/test_a.py").read_bytes() == b"s"


def test_a_scipy_hash_mismatch_deletes_the_part_file_and_names_it(tmp_path, monkeypatch) -> None:
    w = World(tmp_path, SCIPY)
    w.served["scipy-1.18.1.tar.gz"] = b"other bytes"
    errors = w.go(monkeypatch, packages=("scipy",))
    assert errors and errors[0].startswith("scipy-1.18.1.tar.gz: SHA-256"), errors
    assert not list(w.downloads.glob("*.part"))
    assert not w.applied
