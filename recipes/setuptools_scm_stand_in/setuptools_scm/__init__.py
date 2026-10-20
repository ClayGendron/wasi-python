"""A stand-in for setuptools_scm at configure time (matplotlib's, spec 023, Decision 2; statsmodels',
spec 045, Decision 3).

matplotlib's meson.build asks `python3 -m setuptools_scm` for the project version (`__main__`);
statsmodels' version script, `statsmodels/_build/git_version.py`, calls `get_version(root=...)`.
Built from an sdist there is no git history to read, and the sdist's PKG-INFO already holds the
version, which is what setuptools_scm itself answers in an sdist with no repository. It is a recipe
file, so setuptools_scm and its dependencies are not pinned.
"""

from pathlib import Path


def get_version(root=".", **_ignored):
    """The Version: header of root/PKG-INFO; anything else stops the build in one line naming the
    file."""
    pkg_info = Path(root) / "PKG-INFO"
    try:
        text = pkg_info.read_text(encoding="utf-8")
    except OSError:
        raise SystemExit(f"setuptools_scm stand-in: no {pkg_info}") from None
    for line in text.splitlines():
        if not line.strip():
            break  # the headers end at the first blank line
        if line.startswith("Version: "):
            return line.split(": ", 1)[1].strip()
    raise SystemExit(f"setuptools_scm stand-in: no Version: header in {pkg_info}")
