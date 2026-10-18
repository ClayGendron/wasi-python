"""A stand-in for setuptools_scm at matplotlib's configure step (spec 023, Decision 2).

matplotlib's meson.build asks `python3 -m setuptools_scm` for the project version. Built from its
sdist there is no git history to read, and the sdist's PKG-INFO already holds the version, so
`__main__` prints that. It is a recipe file, so setuptools_scm and its dependencies are not pinned.
"""
