"""statsmodels' build scripts on the host (Decision 12's unit checks): the configure-time
setuptools_scm stand-in's get_version, the zip's --drop of one file by its exact name, its --keep
of a dataset folder's code alone, and gen_inittab's four statsmodels renames. No artifact."""

from __future__ import annotations

import os
import re
import subprocess
import sys

import pytest

from harness import paths

sys.path.insert(0, str(paths.REPO / "scripts"))

import gen_inittab  # noqa: E402
import make_stdlib_zip  # noqa: E402

STAND_IN = paths.REPO / "recipes" / "setuptools_scm_stand_in"
PKG_INFO = "Metadata-Version: 2.4\nName: statsmodels\nVersion: 0.15.0\n\nVersion: 9.9 in the body\n"


def _stand_in():
    sys.path.insert(0, str(STAND_IN))
    try:
        sys.modules.pop("setuptools_scm", None)
        import setuptools_scm
    finally:
        sys.path.remove(str(STAND_IN))
    return setuptools_scm


def test_the_stand_in_reads_the_version_from_pkg_info(tmp_path) -> None:
    """get_version(root) is the Version: header of root/PKG-INFO, as setuptools_scm gives in an
    sdist without a repository (statsmodels' git_version.py calls it so); a str or a path; a header
    in the body does not count, and a file without one, or no file, stops naming the file."""
    scm = _stand_in()
    (tmp_path / "PKG-INFO").write_text(PKG_INFO)
    assert scm.get_version(root=tmp_path) == "0.15.0"
    assert scm.get_version(root=str(tmp_path)) == "0.15.0"
    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / "PKG-INFO").write_text("Metadata-Version: 2.4\nName: x\n\nVersion: 1.0\n")
    with pytest.raises(SystemExit, match=re.escape(str(bare / "PKG-INFO"))):
        scm.get_version(root=bare)
    with pytest.raises(SystemExit, match=re.escape(str(tmp_path / "none" / "PKG-INFO"))):
        scm.get_version(root=tmp_path / "none")


def test_the_stand_in_still_prints_the_version_for_matplotlib(tmp_path) -> None:
    """`python -m setuptools_scm` in an sdist's top folder prints its version, as matplotlib's
    meson.build asks, and stops without one."""
    (tmp_path / "PKG-INFO").write_text(PKG_INFO)
    env = {**os.environ, "PYTHONPATH": str(STAND_IN)}
    run = [sys.executable, "-m", "setuptools_scm"]
    r = subprocess.run(run, cwd=tmp_path, env=env, capture_output=True, text=True)
    assert (r.returncode, r.stdout) == (0, "0.15.0\n")
    (tmp_path / "PKG-INFO").write_text("Name: x\n")
    r = subprocess.run(run, cwd=tmp_path, env=env, capture_output=True, text=True)
    assert r.returncode != 0 and "PKG-INFO" in r.stderr


def test_a_drop_takes_one_file_by_its_exact_name() -> None:
    """--drop names a folder or one member (Decision 9: sandbox/rlsdata.txt): the member
    whose name, before .py becomes .pyc, is the argument goes, and nothing else, not even a member
    whose name merely starts with it; a folder's drop is unchanged; a drop that matches nothing,
    such as x.pyc for the member that comes from x.py, stops the build, named."""
    chosen = make_stdlib_zip.Selection(
        ["statsmodels/sandbox/rlsdata.txt", "statsmodels/datasets/co2/src"], [], []
    )
    assert not chosen.take(b"", "statsmodels/sandbox/rlsdata.txt")
    assert chosen.take(b"", "statsmodels/sandbox/rlsdata.txt.bak")
    assert chosen.take(b"", "statsmodels/sandbox/rlsdata.txt2")
    assert chosen.take(b"", "statsmodels/sandbox/rls.py")
    assert not chosen.take(b"", "statsmodels/datasets/co2/src/co2.dat")
    assert chosen.take(b"", "statsmodels/datasets/co2/co2.csv")
    chosen.check()
    pyc = make_stdlib_zip.Selection(["statsmodels/api.pyc"], [], [])
    assert pyc.take(b"", "statsmodels/api.py")
    with pytest.raises(SystemExit, match="statsmodels/api.pyc"):
        pyc.check()


def test_a_kept_dataset_folder_keeps_only_its_code() -> None:
    """--keep <dataset>=__init__.py,data.py, the form step 70 gives each dataset whose terms are not
    approved (Decision 9): its modules stay, so statsmodels.datasets imports, and its data files,
    R scripts and src/ folder go."""
    chosen = make_stdlib_zip.Selection([], ["statsmodels/datasets/spector=__init__.py,data.py"], [])
    assert chosen.take(b"", "statsmodels/datasets/spector/__init__.py")
    assert chosen.take(b"", "statsmodels/datasets/spector/data.py")
    assert not chosen.take(b"", "statsmodels/datasets/spector/spector.csv")
    assert not chosen.take(b"", "statsmodels/datasets/spector/src/spector.dat")
    assert chosen.take(b"", "statsmodels/datasets/spectorx/data.py")
    chosen.check()


def test_the_inittab_renames_statsmodels_four(tmp_path, monkeypatch) -> None:
    """The three state-space smoothers register beside their filters, and statespace._tools beside
    scipy's csgraph._tools, under the renamed init functions; the filters keep theirs. Without the
    table's four entries the clash check stops on exactly those names."""
    built = {
        "sm": [
            "statsmodels/tsa/statespace/_tools",
            *(
                f"statsmodels/tsa/statespace/{kind}/{name}"
                for kind in ("_filters", "_smoothers")
                for name in ("_conventional", "_univariate", "_univariate_diffuse")
            ),
            "statsmodels/tsa/statespace/_filters/_inversions",
            "statsmodels/tsa/statespace/_smoothers/_classical",
        ],
        "sp": ["scipy/sparse/csgraph/_tools"],
    }
    for folder, modules in built.items():
        for module in modules:
            so = tmp_path / folder / (module + gen_inittab.SUFFIX)
            so.parent.mkdir(parents=True, exist_ok=True)
            so.write_bytes(b"!<arch>\n")
    out = tmp_path / "inittab.c"
    argv = [
        "gen_inittab.py",
        str(out),
        f"scipy={tmp_path / 'sp'}",
        f"statsmodels={tmp_path / 'sm'}",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    # Only this link's scipy module: the table's other scipy entries would be unused here.
    ours = {k: v for k, v in gen_inittab.RENAMED.items() if k.startswith("statsmodels.")}
    monkeypatch.setattr(gen_inittab, "RENAMED", ours)
    gen_inittab.main()
    inits = dict(
        re.findall(
            r'_PyImport_SwapPackageContext\("([\w.]+)"\);\s*PyObject \*m = PyInit_(\w+)\(\);',
            out.read_text(),
        )
    )
    ss = "statsmodels.tsa.statespace"
    assert inits == {
        "scipy.sparse.csgraph._tools": "_tools",
        f"{ss}._tools": "statsmodels_tsa_statespace__tools",
        f"{ss}._filters._conventional": "_conventional",
        f"{ss}._filters._univariate": "_univariate",
        f"{ss}._filters._univariate_diffuse": "_univariate_diffuse",
        f"{ss}._filters._inversions": "_inversions",
        f"{ss}._smoothers._conventional": "statsmodels_tsa_statespace__smoothers__conventional",
        f"{ss}._smoothers._univariate": "statsmodels_tsa_statespace__smoothers__univariate",
        f"{ss}._smoothers._univariate_diffuse": (
            "statsmodels_tsa_statespace__smoothers__univariate_diffuse"
        ),
        f"{ss}._smoothers._classical": "_classical",
    }
    assert len(ours) == 4
    monkeypatch.setattr(gen_inittab, "RENAMED", {})
    want = r"\['_conventional', '_tools', '_univariate', '_univariate_diffuse'\]"
    with pytest.raises(SystemExit, match=want):
        gen_inittab.main()
