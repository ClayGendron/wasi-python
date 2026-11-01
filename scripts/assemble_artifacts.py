"""Assemble the artifact directory: the two binaries, the stdlib zip, the
licence notices of everything inside, MANIFEST and SHA256SUMS, written to build/artifacts.new/ and
renamed to build/artifacts/ only when complete.

    assemble_artifacts.py <repository root>
"""

from __future__ import annotations

import ast
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import line
from litter import has_litter, is_litter

LINE = line.read()
PYTHON = LINE["PYTHON_VERSION"]
PACKAGES = {
    "numpy": "2.5.4",
    "pandas": "3.1.0",
    "zlib": "1.3.2",
    "bzip2": "1.0.8",
    "xz": "5.8.4",
    "sqlite-autoconf": "3540100",  # SQLite 3.54.1, named as its pin names it
    "python-dateutil": "2.9.0.post0",
    "tzdata": "2026.6",
    "six": "1.17.0",
    "regex": "2026.9.29",
    # matplotlib: the package, its compiled dependencies, the C libraries linked in, the
    # header-only C++ compiled in, and the pure packages in the zip. Its second milestone:
    # contourpy, and qhull, linked with matplotlib's _qhull.
    "matplotlib": "3.11.2",
    "pillow": "13.0.0",
    "kiwisolver": "1.5.1",
    "freetype": "2.14.3",
    "harfbuzz": "14.1.0",
    "sheenbidi": "3.0.0",
    "libraqm": "0.10.5",
    "pybind11": "3.1.0",
    "cppy": "1.3.1",
    "cycler": "0.12.1",
    "pyparsing": "3.3.3",
    "packaging": "26.3",
    "fonttools": "4.67.0",
    "contourpy": "1.4.0",
    "qhull": "8.0.2",
    # lxml: the package and its two C libraries, linked in.
    "libxml2": "2.15.4",
    "libxslt": "1.1.45",
    "lxml": "6.1.3",
    # tier A: thirty pure-Python distributions, in the order they were chosen in
    "openpyxl": "3.1.5",
    "et-xmlfile": "2.0.0",
    "xlsxwriter": "3.2.9",
    "xlrd": "2.0.2",
    "pypdf": "6.21.4",
    "beautifulsoup4": "4.15.0",
    "soupsieve": "3.0.4",
    "html5lib": "1.1",
    "webencodings": "0.6.1",
    "defusedxml": "0.7.1",
    "xmltodict": "1.0.4",
    "pyyaml": "6.0.3",
    "tomli-w": "1.2.0",
    "jinja2": "3.1.6",
    "markupsafe": "3.0.4",
    "tabulate": "0.10.0",
    "charset-normalizer": "3.5.2",
    "networkx": "3.7",
    "patsy": "1.0.3",
    "sympy": "1.14.0",
    "mpmath": "1.3.0",
    "attrs": "26.1.0",
    "more-itertools": "11.2.1",
    "toolz": "1.2.0",
    "tqdm": "4.70.1",
    "typing-extensions": "4.16.0",
    "joblib": "1.6.0",
    "cloudpickle": "3.1.2",
    "threadpoolctl": "3.7.0",
    "narwhals": "2.27.1",
    # scipy: the package, and OpenBLAS, whose C LAPACK is the LAPACK, linked in.
    "scipy": "1.18.1",
    "openblas": "0.3.34",
    # scikit-learn: the package, its bundled C and C++ (libsvm, liblinear, MurmurHash3)
    # and vendored Python, under its notice.
    "scikit-learn": "1.9.1",
    # seaborn and reportlab: pure Python, seaborn from its sdist, reportlab its wheel
    "seaborn": "0.13.2",
    "reportlab": "5.0.1",
    # statsmodels: the package, its bundled code and its public-domain datasets, under
    # its notice; its formula engine formulaic and formulaic's two requirements, pure wheels.
    "statsmodels": "0.15.0",
    "formulaic": "1.2.2",
    "interface-meta": "2.0.1",
    "wrapt": "2.5.2",
    # python-docx and python-pptx: pure Python, each from its sdist, so that its carried patch has
    # a tree to apply to
    "python-docx": "1.2.0",
    "python-pptx": "1.0.2",
    # pdfplumber, its pure wheel, and pdfminer.six, which it pins exactly, from its sdist with its
    # carried patch; xarray from its sdist, with the notices of the code it adapts
    "pdfplumber": "0.11.10",
    "pdfminer-six": "20260107",
    "xarray": "2026.9.0",
    # drawsvg, its pure wheel
    "drawsvg": "2.4.2",
}
WHEELS = {
    "python-dateutil": "python_dateutil-2.9.0.post0-py2.py3-none-any.whl",
    "tzdata": "tzdata-2026.6-py2.py3-none-any.whl",
    "six": "six-1.17.0-py2.py3-none-any.whl",
    "pybind11": "pybind11-3.1.0-py3-none-any.whl",
    "cppy": "cppy-1.3.1-py3-none-any.whl",
    "cycler": "cycler-0.12.1-py3-none-any.whl",
    "pyparsing": "pyparsing-3.3.3-py3-none-any.whl",
    "packaging": "packaging-26.3-py3-none-any.whl",
    "fonttools": "fonttools-4.67.0-py3-none-any.whl",
    # tier A: the 27 wheels; pyyaml, markupsafe and networkx are sdists
    # (networkx's so that its carried patch has a tree to apply to)
    "openpyxl": "openpyxl-3.1.5-py2.py3-none-any.whl",
    "et-xmlfile": "et_xmlfile-2.0.0-py3-none-any.whl",
    "xlsxwriter": "xlsxwriter-3.2.9-py3-none-any.whl",
    "xlrd": "xlrd-2.0.2-py2.py3-none-any.whl",
    "pypdf": "pypdf-6.21.4-py3-none-any.whl",
    "beautifulsoup4": "beautifulsoup4-4.15.0-py3-none-any.whl",
    "soupsieve": "soupsieve-3.0.4-py3-none-any.whl",
    "html5lib": "html5lib-1.1-py2.py3-none-any.whl",
    "webencodings": "webencodings-0.6.1-py3-none-any.whl",
    "defusedxml": "defusedxml-0.7.1-py2.py3-none-any.whl",
    "xmltodict": "xmltodict-1.0.4-py3-none-any.whl",
    "tomli-w": "tomli_w-1.2.0-py3-none-any.whl",
    "jinja2": "jinja2-3.1.6-py3-none-any.whl",
    "tabulate": "tabulate-0.10.0-py3-none-any.whl",
    "charset-normalizer": "charset_normalizer-3.5.2-py3-none-any.whl",
    "patsy": "patsy-1.0.3-py2.py3-none-any.whl",
    "sympy": "sympy-1.14.0-py3-none-any.whl",
    "mpmath": "mpmath-1.3.0-py3-none-any.whl",
    "attrs": "attrs-26.1.0-py3-none-any.whl",
    "more-itertools": "more_itertools-11.2.1-py3-none-any.whl",
    "toolz": "toolz-1.2.0-py3-none-any.whl",
    "tqdm": "tqdm-4.70.1-py3-none-any.whl",
    "typing-extensions": "typing_extensions-4.16.0-py3-none-any.whl",
    "joblib": "joblib-1.6.0-py3-none-any.whl",
    "cloudpickle": "cloudpickle-3.1.2-py3-none-any.whl",
    "threadpoolctl": "threadpoolctl-3.7.0-py3-none-any.whl",
    "narwhals": "narwhals-2.27.1-py3-none-any.whl",
    "reportlab": "reportlab-5.0.1-py3-none-any.whl",  # its other parts are below
    # statsmodels' formula engine
    "formulaic": "formulaic-1.2.2-py3-none-any.whl",
    "interface-meta": "interface_meta-2.0.1-py3-none-any.whl",
    "wrapt": "wrapt-2.5.2-py3-none-any.whl",
    "pdfplumber": "pdfplumber-0.11.10-py3-none-any.whl",
    "drawsvg": "drawsvg-2.4.2-py3-none-any.whl",
}
# The Unicode data terms of HarfBuzz's tables, pinned as a file.
UNICODE_TERMS = "unicodetools-4fd8eca9-LICENSE"
# The licence notices of what the SDK links in, named by the line's wasi-libc and LLVM commits.
WASI_LIBC = [
    f"wasi-libc-{LINE['WASI_LIBC_COMMIT']}-{name}"
    for name in (
        "LICENSE",
        "LICENSE-APACHE",
        "LICENSE-APACHE-LLVM",
        "LICENSE-MIT",
        "musl-COPYRIGHT",
        "cloudlibc-LICENSE",
    )
]
LLVM = [
    f"llvm-{LINE['LLVM_COMMIT']}-{component}-LICENSE.TXT"
    for component in ("libcxx", "libcxxabi", "libunwind", "compiler-rt")
]
# wasi-libc's LICENSE-MIT, already pinned and shipped: a generic MIT text with no holder named, the
# text reportlab's QR encoder's notice names
MIT_TEXT = f"wasi-libc-{LINE['WASI_LIBC_COMMIT']}-LICENSE-MIT"
RESEARCH_PINS = {"python-3.14.7-wasi_sdk-24.zip"}
# matplotlib's notices beside its LICENSE/ folder: Agg's, compiled in, and the fonts' that travel
# with mpl-data (the AFM files' readme must go with them).
MPL_NOTICES = (
    "extern/agg24-svn/src/copying",
    "lib/matplotlib/mpl-data/fonts/ttf/LICENSE_DEJAVU",
    "lib/matplotlib/mpl-data/fonts/ttf/LICENSE_STIX",
    "lib/matplotlib/mpl-data/fonts/pdfcorefonts/readme.txt",
)
# contourpy's mpl2005 code came from GIST's gcntr.c (src/mpl2005_original.cpp), whose notice, the
# Regents of the University of California's, contourpy does not ship; matplotlib ships it, and it
# goes beside contourpy's own licence.
CONTOURPY_GIST_NOTICE = "LICENSE/LICENSE_YORICK"
# libxml2's own notices beside its Copyright file: the two files Copyright
# names as its exceptions, each under an ISC-style grant of its own, and timsort.h's MIT notice.
# Each is the comment at the file's head that holds these words; a file missing, or a notice not
# where it was, stops the build.
LIBXML2_NOTICES = (
    ("dict.c", ("Copyright (C) 2003-2012 Daniel Veillard.", "Permission to use, copy, modify")),
    (
        "list.c",
        ("Copyright (C) 2000 Gary Pennington and Daniel Veillard.", "Permission to use, copy"),
    ),
    ("timsort.h", ("The MIT License (MIT)", "Copyright (c) 2010-2017 Christopher Swenson.")),
)
# lxml's terms: its licence, its list of the licences in its wheels (which
# bundle GNU libiconv and zlib; this build links neither), and the BSD and ElementTree texts.
LXML_NOTICES = (
    "LICENSE.txt",
    "LICENSES.txt",
    "doc/licenses/BSD.txt",
    "doc/licenses/elementtree.txt",
)
# scipy's terms: its licence and its list of bundled licences, then the licence
# of each bundled component that is compiled in or packed, as the sdist ships it (the vendored
# subprojects and the libraries inside scipy's own tree). Tempita is a build tool and ampgo only a
# benchmark; Chebfun's Python carries its notice in place, as LICENSES_bundled.txt says.
SCIPY_NOTICES = (
    "LICENSE.txt",
    "LICENSES_bundled.txt",
    "subprojects/boost_math/math/LICENSE",
    "subprojects/xsf/LICENSE",
    "subprojects/xsf/LICENSES_bundled.txt",
    "subprojects/highs/LICENSE.txt",
    "subprojects/highs/extern/LICENCE_1_0.txt",
    "subprojects/highs/extern/filereaderlp/LICENSE",
    "subprojects/highs/extern/pdqsort/license.txt",
    "subprojects/duccfft/LICENSE.md",
    "subprojects/qhull_r/libqhull_r/COPYING.txt",
    "subprojects/unuran/license.txt",
    "subprojects/array_api_compat/array_api_compat/LICENSE",
    "subprojects/array_api_extra/LICENSE",
    "subprojects/cobyqa/LICENSE",
    "subprojects/pyprima/pyprima/LICENCE.txt",
    "scipy/_external/packaging_version/src/LICENSE.BSD",
    "scipy/_lib/_uarray/LICENSE",
    "scipy/fft/_duccfft/LICENSE.md",
    "scipy/integrate/src/LICENSE_DOP",
    "scipy/io/_fast_matrix_market/LICENSE.txt",
    "scipy/io/_fast_matrix_market/fast_matrix_market/dependencies/fast_float/LICENSE-MIT",
    "scipy/io/_fast_matrix_market/fast_matrix_market/dependencies/ryu/LICENSE-Boost",
    "scipy/ndimage/LICENSE.txt",
    "scipy/optimize/_direct/COPYING",
    "scipy/optimize/tnc/LICENSE",
    "scipy/sparse/linalg/_dsolve/SuperLU/License.txt",
    "scipy/sparse/linalg/_eigen/arpack/arnaud/LICENSE",
    "scipy/sparse/linalg/_propack/PROPACK/LICENSE",
    "scipy/spatial/COPYING_QHULL.txt",
    "scipy/stats/biasedurn/license.txt",
)
# The bundled notices scipy's LICENSES_bundled.txt points to inside source headers ("For details,
# see ..."), for the three compiled or packed here: pystreambuf (cctbx,
# BSD-3-Clause, linked in io._fast_matrix_market), Chebfun and getLebedevSphere (BSD-3-Clause and
# BSD-2-Clause, packed as bytecode). (path, words the notice must hold.)
SCIPY_HEAD_NOTICES = (
    ("scipy/io/_fast_matrix_market/src/pystreambuf.h", ("cctbx Copyright", "Redistribution")),
    ("scipy/interpolate/_bary_rational.py", ("Chebfun Developers", "Redistribution")),
    ("scipy/integrate/_lebedev.py", ("getLebedevSphere", "Redistribution")),
)
# scikit-learn's terms: its licence, then each bundled component's notice,
# labelled with its path in the sdist. Comments do not survive compilation to .pyc, so these parts
# are where the zip's users meet the notices of the vendored Python. A file's licence file is taken
# whole; a notice inside a source file is its exact lines, which must hold the words given, so an
# upstream change that moves it stops the build. (path, first line, last line, words.)
SKLEARN_TOP = "scikit_learn-1.9.1"
SKLEARN_FILES = (
    "COPYING",
    "sklearn/svm/src/liblinear/COPYRIGHT",
    "sklearn/externals/array_api_compat/LICENSE",
    "sklearn/externals/array_api_extra/LICENSE",
)
SKLEARN_LINES = (
    # libsvm's BSD-3-Clause-style notice, the comment that opens svm.cpp
    (
        "sklearn/svm/src/libsvm/svm.cpp",
        1,
        32,
        ("Chih-Chung Chang and Chih-Jen Lin", "Redistribution"),
    ),
    # liac-arff (MIT)
    (
        "sklearn/externals/_arff.py",
        1,
        25,
        ("Renato de Pontes Pereira", "Permission is hereby granted"),
    ),
    # packaging's two modules (BSD-2-Clause)
    ("sklearn/externals/_packaging/version.py", 4, 26, ("Donald Stufft", "Redistribution")),
    ("sklearn/externals/_packaging/_structures.py", 4, 26, ("Donald Stufft", "Redistribution")),
    # MurmurHash3's public-domain statement
    ("sklearn/utils/src/MurmurHash3.cpp", 2, 3, ("Austin Appleby", "placed in the public")),
    # CPython's pprint, adapted: the PSF licence in full and the summary of changes it asks for
    ("sklearn/utils/_pprint.py", 7, 67, ("Python Software Foundation", "summary of changes")),
    # the pytest-derived lines of a module that ships (it is not under tests/)
    ("sklearn/utils/_testing.py", 575, 577, ("derived from pytest", "MIT License")),
    # HDBSCAN's code, from Leland McInnes' hdbscan (BSD-3-Clause): the five files of
    # cluster/_hdbscan/ carry its terms, and _tree.pxd its notice whole (the build's notice sweep)
    ("sklearn/cluster/_hdbscan/_tree.pxd", 1, 28, ("Leland McInnes", "Redistribution")),
    # StratifiedGroupKFold's fold assignment, based on a Kaggle kernel under Apache-2.0, with the
    # list of changes Apache-2.0 4(b) asks for (the build's notice sweep); the licence text follows
    ("sklearn/model_selection/_split.py", 1001, 1015, ("kaggle", "Apache 2.0 License")),
)
# Three adaptations whose files carry no full notice: the projects' own licence texts, pinned.
SKLEARN_PINNED = (
    ("numpydoc-894c8c47-LICENSE.txt", "numpydoc, for sklearn/externals/_numpydoc/docscrape.py"),
    ("django-1dae4ac1-LICENSE", "django, for the slugify adaptation in sklearn/datasets/_base.py"),
    # the MIT permission text for _testing.py's pytest-derived lines
    ("pytest-0d90a31d-LICENSE", "pytest, for the derived lines of sklearn/utils/_testing.py"),
)
# The six bundled datasets: three are copies of sets UCI publishes under CC BY 4.0, which asks for
# this attribution.
SKLEARN_DATA = """\
scikit-learn 1.9.1 bundles six datasets (sklearn/datasets/data/), each with a description
(sklearn/datasets/descr/), which a loader's DESCR returns and which carries the full citation.
This release packs them unchanged from scikit-learn 1.9.1's copy.

Three are copies of datasets the UCI Machine Learning Repository publishes under the Creative
Commons Attribution 4.0 International licence (CC BY 4.0,
https://creativecommons.org/licenses/by/4.0/):

- Optical Recognition of Handwritten Digits (load_digits, its test set). Creator: E. Alpaydin, as
  descr/digits.rst cites. Source: https://archive.ics.uci.edu/dataset/80. Licence: CC BY 4.0.
  Unchanged from scikit-learn 1.9.1's copy.
- Breast Cancer Wisconsin (Diagnostic) (load_breast_cancer). Creators: W. H. Wolberg, W. N.
  Street, O. L. Mangasarian, as descr/breast_cancer.rst cites. Source:
  https://archive.ics.uci.edu/dataset/17. Licence: CC BY 4.0. Unchanged from scikit-learn 1.9.1's
  copy.
- Wine (load_wine). Original owners: M. Forina et al., PARVUS, as descr/wine_data.rst cites.
  Source: https://archive.ics.uci.edu/dataset/109. Licence: CC BY 4.0. Unchanged from scikit-learn
  1.9.1's copy.

Iris (load_iris) is taken from R. A. Fisher, "The use of multiple measurements in taxonomic
problems", Annual Eugenics 7, Part II, 179-188 (1936), as descr/iris.rst says; UCI's copy
(https://archive.ics.uci.edu/dataset/53, CC BY 4.0) differs from it in two points.

Diabetes (load_diabetes; B. Efron, T. Hastie, I. Johnstone and R. Tibshirani, 2004) and Linnerud
(load_linnerud; M. Tenenhaus, 1998) state no terms.

The two sample photographs of sklearn/datasets/images/ (CC BY 2.0) are not in this release.
"""
# statsmodels' terms (Decision 13), as scikit-learn's: its licence, COPYRIGHTS.txt (the
# numpy, scipy, pandas, matplotlib, scikit-learn and qsturng-py code it carries), the licences of
# its two folders that have their own, each bundled component the build's notice sweep found, the
# pinned licence texts of the two projects whose adapted code carries none, and its datasets'
# terms, read from each dataset module's own COPYRIGHT. (path, first line, last line, words.)
STATSMODELS_TOP = "statsmodels-0.15.0"
STATSMODELS_FILES = (
    "LICENSE.txt",
    "COPYRIGHTS.txt",
    "statsmodels/multivariate/factor_rotation/LICENSE.txt",
    "statsmodels/multivariate/factor_rotation/COPYRIGHTS.txt",
    "statsmodels/stats/libqsturng/LICENSE.txt",
)
STATSMODELS_LINES = (
    # parallel_func, copied from mne-python (its licence text pinned below)
    ("statsmodels/tools/parallel.py", 1, 12, ("mne-python", "Simplified BSD")),
    # the docstring parser, copied from numpydoc (its licence text pinned below)
    ("statsmodels/tools/docstring.py", 1, 1, ("NumpyDoc",)),
    # Peter John Acklam's inverse normal, from a Perl port, inside libqsturng
    ("statsmodels/stats/libqsturng/qsturng_.py", 1926, 1961, ("dfield", "Peter John Acklam")),
    # the STL port of the NETLIB Fortran (compiled in)
    ("statsmodels/tsa/stl/_stl.pyx", 3, 13, ("Kevin Sheppard", "NETLIB")),
    # the boxplot variations' origin
    ("statsmodels/graphics/boxplots.py", 3, 4, ("Flavio Coelho", "Teemu Ikonen")),
    # quantile regression's IRLS, translated from Matlab with its author's permission
    ("statsmodels/regression/quantile_regression.py", 1, 16, ("Mohammadi", "with permission")),
)
STATSMODELS_PINNED = (
    ("mne-python-2c4a3b03-LICENSE.txt", "mne-python, for statsmodels/tools/parallel.py"),
    ("numpydoc-894c8c47-LICENSE.txt", "numpydoc, for statsmodels/tools/docstring.py"),
)
# The datasets that ship (each module's COPYRIGHT says public domain) and those whose files stay
# out (Decision 9), each named with its module's own statement.
STATSMODELS_DATASETS = (
    "anes96", "co2", "danish_data", "elec_equip", "elnino", "engel", "grunfeld", "longley",
    "macrodata", "modechoice", "nile", "randhie", "stackloss", "statecrime", "strikes", "sunspots",
)  # fmt: skip
STATSMODELS_LEFT_OUT = (
    "cancer", "ccard", "china_smoking", "committee", "copper", "cpunish", "fair", "fertility",
    "heart", "interest_inflation", "scotland", "spector", "star98",
)  # fmt: skip
# OpenBLAS's terms: its own licence and Reference-LAPACK's, whose C translation it carries.
OPENBLAS_NOTICES = ("LICENSE", "lapack-netlib/LICENSE")
# What each carried patch to an Apache-2.0 file changes, for the notice Apache-2.0 §4(b) asks of
# a modified file: keyed by the patch's path, which the notice names, so a
# patch added or deleted without its line here stops the build.
MODIFIED = {
    "recipes/patches/regex-2026.9.29/0001-callback-signatures.patch": (
        "five callbacks gain the parameter CPython passes"
    ),
    "recipes/patches/regex-2026.9.29/0002-timeout-ticks.patch": (
        "clock ticks kept in 64 bits, so timeout= fires past 2.147 s"
    ),
}
# tqdm is MPL-2.0 AND MIT, and the zip ships it as bytecode, MPL-2.0's Executable Form:
# the release carries its source, the pinned wheel unchanged (its SHA-256 is the
# pin's), and its notice holds the full MPL-2.0 text, which the wheel's LICENCE only names.
TQDM_WHEEL = "tqdm-4.70.1-py3-none-any.whl"
TQDM_SOURCE = "tqdm-4.70.1-source.whl"
TQDM_URL = (
    "https://files.pythonhosted.org/packages/a7/03/"
    "921a3d3c75785aca9ebfbfcabfbc3a1be12e2ab5265deb026d55a5a3f83e/" + TQDM_WHEEL
)
TQDM_TAG = "https://github.com/tqdm/tqdm/tree/v4.70.1"
MPL_TEXT = "spdx-31ba1a50-MPL-2.0.txt"
# sympy's LaTeX grammar and its generated parser carry their own MIT notice inside the package,
# where wheel_licences does not look.
SYMPY_WHEEL = "sympy-1.14.0-py3-none-any.whl"
SYMPY_NESTED = "sympy/parsing/latex/LICENSE.txt"
# seaborn's notice: its licence, then the licences of the five pieces of code
# it vendors in seaborn/external/ (appdirs, husl, numpydoc, packaging, scipy), from its sdist.
SEABORN_NOTICES = (
    "LICENSE.md",
    "licences/APPDIRS_LICENSE",
    "licences/HUSL_LICENSE",
    "licences/NUMPYDOC_LICENSE",
    "licences/PACKAGING_LICENSE",
    "licences/SCIPY_LICENSE",
)
# pdfminer.six's notices beside its MIT licence, comments in its code that compilation drops: each
# (file, first line, last line, words the lines must hold). _saslprep.py is MongoDB's, under
# Apache-2.0 (whose text follows), with Matthias Valvekens' changes under pyHanko's MIT licence;
# glyphlist.py holds Adobe's Glyph List under its notice, fontmetrics.py the Adobe Core 35 AFM
# files' terms; arcfour.py and runlength.py are in the public domain.
PDFMINER_TOP = "pdfminer_six-20260107"
PDFMINER_NOTICES = (
    ("pdfminer/_saslprep.py", 1, 16, ("MongoDB", "Apache License, Version 2.0", "pyHanko")),
    ("pdfminer/glyphlist.py", 16, 46, ("Adobe Systems Incorporated", "Permission is hereby")),
    ("pdfminer/fontmetrics.py", 12, 27, ("Adobe Core 35 AFM", "paragraph is not modified")),
    ("pdfminer/arcfour.py", 1, 3, ("public domain",)),
    ("pdfminer/runlength.py", 1, 5, ("public domain",)),
)
# xarray's notice: its Apache-2.0 licence, then every file of its sdist's licenses folder, the
# notices of the code it adapts (from dask, pandas, NumPy, seaborn, scikit-learn, anytree and
# Python) and of its HTML view's icons (IcoMoon's, CC BY 4.0).
XARRAY_TOP = "xarray-2026.9.0"
# reportlab's third-party notices, comments in its code that
# compilation drops: each file's leading comment block, byte for byte from the pinned wheel, after
# its wheel's LICENSE. (file, words the block must hold, what the heading says.) Sarna's notice
# heads seven files of reportlab/graphics/barcode/, named in the heading, outside the compared
# bytes; the QR encoder's names the MIT licence, whose text follows it.
REPORTLAB_WHEEL = "reportlab-5.0.1-py3-none-any.whl"
SARNA_FILES = ("__init__", "code128", "code39", "code93", "common", "fourstate", "usps")
REPORTLAB_NOTICES = (
    (
        "reportlab/graphics/barcode/__init__.py",
        ("Tyler C. Sarna", "This product includes software developed by Tyler C. Sarna."),
        "Tyler C. Sarna's BSD-4-Clause notice, which heads "
        + ", ".join(f"{n}.py" for n in SARNA_FILES[:-1])
        + f" and {SARNA_FILES[-1]}.py in reportlab/graphics/barcode/",
    ),
    (
        "reportlab/pdfbase/_glyphlist.py",
        ("Copyright 2002-2019 Adobe", "Redistribution and use"),
        "Adobe's BSD-3-Clause notice for the Adobe Glyph List",
    ),
    (
        "reportlab/graphics/barcode/qrencoder.py",
        ("Open End AB", "Kazuhiko Arase", "Licensed under the MIT license"),
        "Open End AB's and Kazuhiko Arase's notice; the MIT licence it names follows",
    ),
)
# The snapshot's pre-import list has one source, the recipe's #define.
PREIMPORT_RECIPE = "recipes/reactor_main.c"
PREIMPORT_DEFINE = re.compile(r'^#define PREIMPORT "import (.*)"\s*$', re.M)
LICENCE_NAME = re.compile(r"(LICEN[CS]E|COPYING|NOTICE)[^/]*$", re.I)
# What a program imports to use each distribution: a starting image of every package imports it.
SNAPSHOT_PACKAGES_RECIPE = "recipes/snapshot-packages.txt"
DOTTED_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*")


def preimport_list(text: str) -> str:
    """The modules the snapshot pre-imports, as MANIFEST's x-preimport line names them, read from
    the recipe's one `#define PREIMPORT "import …"`; none, or more than one, stops the build."""
    found = PREIMPORT_DEFINE.findall(text)
    if len(found) != 1:
        raise SystemExit(f"{PREIMPORT_RECIPE}: {len(found)} '#define PREIMPORT' lines, not one")
    return found[0]


def snapshot_packages(text: str, packages: dict[str, str]) -> list[tuple[str, list[str]]]:
    """Each distribution of `packages` with the names a program imports to use it, in the recipe
    file's order, a name already on an earlier line dropped. A distribution with no line, a line
    for no distribution, a second line, a line without its colon and a name that is not a dotted
    Python name each stop the build, named."""
    pairs: list[tuple[str, list[str]]] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        dist, colon, rest = line.partition(":")
        dist = dist.strip()
        if not colon:
            raise SystemExit(f"{SNAPSHOT_PACKAGES_RECIPE}: {line!r} has no colon")
        if dist not in packages:
            raise SystemExit(f"{SNAPSHOT_PACKAGES_RECIPE}: {dist} has no package line")
        if any(d == dist for d, _ in pairs):
            raise SystemExit(f"{SNAPSHOT_PACKAGES_RECIPE}: {dist} has a second line")
        names = []
        for name in rest.split():
            if not DOTTED_NAME.fullmatch(name):
                raise SystemExit(
                    f"{SNAPSHOT_PACKAGES_RECIPE}: {dist}: {name!r} is not a dotted Python name"
                )
            if name not in seen:
                seen.add(name)
                names.append(name)
        pairs.append((dist, names))
    missing = [d for d in packages if all(d != listed for listed, _ in pairs)]
    if missing:
        raise SystemExit(f"{SNAPSHOT_PACKAGES_RECIPE}: no line for {', '.join(missing)}")
    return pairs


def snapshot_package_lines(pairs: list[tuple[str, list[str]]]) -> list[str]:
    """MANIFEST's x-snapshot-package lines: one per distribution with names, in order."""
    return [f"x-snapshot-package {dist} {' '.join(names)}" for dist, names in pairs if names]


def _remove(path: Path) -> None:
    """Remove a folder, retrying as scripts/steps/remove.sh does: Finder can write into it while
    it is emptied. A path already gone is success."""
    for _ in range(3):
        if os.path.islink(path) or os.path.isfile(path):
            try:
                os.unlink(path)
            except OSError:
                pass
        else:
            shutil.rmtree(path, ignore_errors=True)  # goes on past an entry, as rm -rf does
        if not os.path.lexists(path):
            return
    raise SystemExit(f"ERROR: cannot remove {path}")


def drop_litter(folder: Path) -> None:
    """Delete litter from a folder this script made, before it is listed: a litter file, and a
    litter folder whole."""
    for p in sorted(folder.rglob("*"), reverse=True):  # a folder's entries before the folder
        if not is_litter(p.name) or not os.path.lexists(p):
            continue
        if p.is_dir() and not p.is_symlink():
            _remove(p)
        else:
            p.unlink()


def listed_files(folder: Path) -> list[Path]:
    """The set's files for SHA256SUMS. Litter written after drop_litter is never listed (any path
    with a litter part), and the judge forgives exactly those names."""
    return sorted(
        p
        for p in folder.rglob("*")
        if p.is_file() and not has_litter(p.relative_to(folder).as_posix())
    )


def licence_files(folder: Path) -> list[Path]:
    """A licence folder's files, without litter: each is packed into a LICENSES file."""
    return sorted(p for p in folder.iterdir() if not is_litter(p.name))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def notice(parts: list[tuple[str, bytes]]) -> bytes:
    """The parts joined unaltered, each after a one-line header naming it."""
    out = b""
    for label, data in parts:
        out += f"==== {label} ====\n".encode() + data
        if not data.endswith(b"\n"):
            out += b"\n"
        out += b"\n"
    return out


def wheel_licences(wheel: Path) -> list[tuple[str, bytes]]:
    """A pinned wheel's licence files, read from its bytes once they match its pin."""
    with zipfile.ZipFile(io.BytesIO(pinned_bytes(wheel.parent, wheel.name))) as z:
        names = sorted(
            n
            for n in z.namelist()
            if ".dist-info/" in n and not n.endswith("/") and LICENCE_NAME.search(n)
        )
        return [(f"{wheel.name}: {n}", z.read(n)) for n in names]


def pinned_bytes(d: Path, name: str) -> bytes:
    """A pinned download's bytes, checked against its line in downloads/SHA256SUMS first."""
    rows = (d / "SHA256SUMS").read_text().splitlines()
    want = [row.split()[0] for row in rows if row.split()[1:] == [name]]
    data = (d / name).read_bytes()
    if len(want) != 1 or hashlib.sha256(data).hexdigest() != want[0]:
        raise SystemExit(f"downloads/{name} does not match its pin")
    return data


def tqdm_source_part(source: bytes) -> bytes:
    """Where tqdm's source is: first the copy this release carries, then, for convenience, PyPI
    and the project's tag."""
    return (
        "tqdm is MPL-2.0 AND MIT. This release ships it as bytecode in python-stdlib.zip,\n"
        "MPL-2.0's Executable Form. Its Source Code Form travels with the release, unchanged:\n"
        f"  LICENSES/{TQDM_SOURCE}, the pinned wheel {TQDM_WHEEL}, which holds tqdm's .py files,\n"
        f"  SHA-256 {hashlib.sha256(source).hexdigest()} (MANIFEST's pin line for {TQDM_WHEEL}).\n"
        "The same file is on PyPI, and the source is in the project's repository at its tag:\n"
        f"  {TQDM_URL}\n"
        f"  {TQDM_TAG}\n"
    ).encode()


def hacl_notice(cp: Path) -> bytes:
    """The MIT notice at the head of HACL*'s sources, as CPython ships them."""
    text = (cp / "Modules" / "_hacl" / "Hacl_Hash_SHA2.h").read_text()
    end = text.index("*/")
    if "MIT License" not in text[:end] or "Permission is hereby granted" not in text[:end]:
        raise SystemExit("HACL*'s header no longer carries its MIT notice")
    return (text[: end + 2] + "\n").encode()


def sqlite_notice(b: Path) -> bytes:
    """SQLite has no licence file: it is public domain, and its blessing heads each source file."""
    text = (b / "sqlite-autoconf-3540100" / "sqlite3.h").read_text()
    end = text.index("*/")
    if "disclaims copyright" not in text[:end] or "May you do good" not in text[:end]:
        raise SystemExit("sqlite3.h no longer opens with SQLite's blessing")
    return (text[: end + 2] + "\n").encode()


def head_notice(path: Path, words: tuple[str, ...]) -> bytes:
    """The first of a C file's two leading comments that holds every one of `words`."""
    if not path.is_file():
        raise SystemExit(f"{path.name} is missing: its licence notice cannot be read")
    text = path.read_text()
    start = 0
    for _ in range(2):
        begin = text.find("/*", start)
        end = text.find("*/", begin)
        if begin < 0 or end < 0:
            break
        comment = text[begin : end + 2]
        if all(w in comment for w in words):
            return (comment + "\n").encode()
        start = end + 2
    raise SystemExit(f"{path.name} no longer opens with the notice {words[0]!r}")


def hash_notice(path: Path, words: tuple[str, ...]) -> bytes:
    """A Python file's leading `#` comment, which must hold every one of `words`."""
    if not path.is_file():
        raise SystemExit(f"{path.name} is missing: its licence notice cannot be read")
    lines = []
    for line in path.read_text().splitlines():
        if not line.startswith("#"):
            break
        lines.append(line)
    comment = "\n".join(lines) + "\n"
    if not all(w in comment for w in words):
        raise SystemExit(f"{path.name} no longer opens with the notice {words[0]!r}")
    return comment.encode()


def leading_comment(data: bytes, name: str, words: tuple[str, ...]) -> bytes:
    """A Python file's leading comment block, byte for byte: its first lines that begin with `#`,
    up to the first that does not. It must hold every one of `words`."""
    lines = []
    for line in data.splitlines(keepends=True):
        if not line.startswith(b"#"):
            break
        lines.append(line)
    block = b"".join(lines)
    if not all(w.encode() in block for w in words):
        raise SystemExit(f"{name} no longer opens with the notice {words[0]!r}")
    return block


def reportlab_parts(d: Path) -> list[tuple[str, bytes]]:
    """reportlab's three third-party notices from the pinned wheel, checked against its pin first,
    and the pinned MIT text the QR encoder's notice names."""
    wheel = pinned_bytes(d, REPORTLAB_WHEEL)
    parts = []
    with zipfile.ZipFile(io.BytesIO(wheel)) as z:
        for name, words, what in REPORTLAB_NOTICES:
            block = leading_comment(z.read(name), name, words)
            parts.append((f"{REPORTLAB_WHEEL}: {name}, its leading comment ({what})", block))
    parts.append(
        (
            f"The MIT licence reportlab/graphics/barcode/qrencoder.py names ({MIT_TEXT})",
            pinned_bytes(d, MIT_TEXT),
        )
    )
    return parts


def scipy_head_notice(tree: Path, rel: str, words: tuple[str, ...]) -> bytes:
    path = tree / rel
    return hash_notice(path, words) if rel.endswith(".py") else head_notice(path, words)


def lines_notice(path: Path, first: int, last: int, words: tuple[str, ...]) -> bytes:
    """Lines first to last (counted from 1) of a source file, which must hold every one of
    `words`."""
    if not path.is_file():
        raise SystemExit(f"{path.name} is missing: its licence notice cannot be read")
    lines = path.read_text(encoding="utf-8").splitlines()[first - 1 : last]
    text = "\n".join(lines) + "\n"
    if len(lines) != last - first + 1 or not all(w in text for w in words):
        raise SystemExit(
            f"{path.name}: lines {first}-{last} no longer hold the notice {words[0]!r}"
        )
    return text.encode()


def sklearn_parts(tree: Path, d: Path) -> list[tuple[str, bytes]]:
    """LICENSES/scikit-learn.txt's parts, in order."""
    parts = [(f"scikit-learn {n}", (tree / n).read_bytes()) for n in SKLEARN_FILES]
    parts += [
        (f"scikit-learn {n}, lines {a}-{b}", lines_notice(tree / n, a, b, words))
        for n, a, b, words in SKLEARN_LINES
    ]
    parts += [(f"{what} ({name})", pinned_bytes(d, name)) for name, what in SKLEARN_PINNED]
    apache = f"wasi-libc-{LINE['WASI_LIBC_COMMIT']}-LICENSE-APACHE"  # the plain Apache-2.0 text
    parts.append(
        (
            f"Apache License 2.0, the full text, for sklearn/model_selection/_split.py ({apache})",
            pinned_bytes(d, apache),
        )
    )
    parts.append(
        ("scikit-learn's bundled datasets: their sources and terms", SKLEARN_DATA.encode())
    )
    return parts


def pdfminer_parts(tree: Path, d: Path) -> list[tuple[str, bytes]]:
    """LICENSES/pdfminer-six.txt's parts: its licence, the notices in its code, and the plain
    Apache-2.0 text _saslprep.py's notice names."""
    parts = [("pdfminer.six LICENSE", (tree / "LICENSE").read_bytes())]
    parts += [
        (f"pdfminer.six {n}, lines {a}-{b}", lines_notice(tree / n, a, b, words))
        for n, a, b, words in PDFMINER_NOTICES
    ]
    apache = f"wasi-libc-{LINE['WASI_LIBC_COMMIT']}-LICENSE-APACHE"  # the plain Apache-2.0 text
    parts.append(
        (
            f"Apache License 2.0, the full text, for pdfminer/_saslprep.py ({apache})",
            pinned_bytes(d, apache),
        )
    )
    return parts


def dataset_copyright(tree: Path, name: str) -> str:
    """A statsmodels dataset module's COPYRIGHT string, read without running it, on one line."""
    path = tree / "statsmodels" / "datasets" / name / "data.py"
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "COPYRIGHT" for t in node.targets
        ):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return " ".join(node.value.value.split())
    raise SystemExit(f"{path}: no COPYRIGHT string")


def statsmodels_parts(tree: Path, d: Path) -> list[tuple[str, bytes]]:
    """LICENSES/statsmodels.txt's parts, in order (Decision 13)."""
    parts = [(f"statsmodels {n}", (tree / n).read_bytes()) for n in STATSMODELS_FILES]
    parts += [
        (f"statsmodels {n}, lines {a}-{b}", lines_notice(tree / n, a, b, words))
        for n, a, b, words in STATSMODELS_LINES
    ]
    parts += [(f"{what} ({name})", pinned_bytes(d, name)) for name, what in STATSMODELS_PINNED]
    shipped = []
    for name in STATSMODELS_DATASETS:
        terms = dataset_copyright(tree, name)
        if "public domain" not in terms.lower():
            raise SystemExit(f"statsmodels dataset {name}: its COPYRIGHT is not public domain")
        shipped.append(f"- {name}: {terms}\n")
    left = [
        f"- {name} (its module says: {dataset_copyright(tree, name)})\n"
        for name in STATSMODELS_LEFT_OUT
    ]
    data = (
        "statsmodels 0.15.0 bundles example datasets (statsmodels/datasets/), each module stating\n"
        "its own terms in COPYRIGHT; statsmodels' COPYRIGHTS.txt says they are not under its\n"
        "licence. This release packs the data files of these sixteen, unchanged, each stating\n"
        "public domain:\n\n" + "".join(shipped) + "\n"
        "The data files of these thirteen are not in this release, since their stated terms are\n"
        "not approved (their modules stay, and their loaders raise FileNotFoundError), and\n"
        "neither is any datasets/*/src/ folder, nor sandbox/rlsdata.txt (a table with no stated\n"
        "terms):\n\n"
        + "".join(left)
    )
    parts.append(("statsmodels' bundled datasets: their terms", data.encode()))
    return parts


def modified_notice(root: Path, top: str) -> bytes:
    """One line per carried patch of a tree: the files it changes, read from the patch itself,
    the patch's path and what it does; then that the rest is compiled as released."""
    lines = []
    for patch in sorted((root / "recipes" / "patches" / top).glob("[0-9][0-9][0-9][0-9]-*.patch")):
        rel = patch.relative_to(root).as_posix()
        if rel not in MODIFIED:
            raise SystemExit(f"{rel}: no line in MODIFIED says what it changes")
        files = re.findall(r"^\+\+\+ b/(\S+)$", patch.read_text(), re.M)
        if not files:
            raise SystemExit(f"{rel}: changes no file")
        lines.append(
            f"This build modifies {', '.join(files)} with {rel} ({MODIFIED[rel]}); "
            "the module is otherwise compiled as released.\n"
        )
    if not lines:
        raise SystemExit(f"recipes/patches/{top}: no carried patch, so no modification notice")
    return "".join(lines).encode()


def main() -> None:
    root = Path(sys.argv[1]).resolve()
    b, d = root / "build", root / "downloads"
    untracked = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "ls-files",
            "--others",
            "--exclude-standard",
            "recipes",
            "scripts",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    if untracked:
        raise SystemExit(f"untracked recipe files (stage them first): {', '.join(untracked)}")

    new, final = b / "artifacts.new", b / "artifacts"
    _remove(new)
    (new / "LICENSES").mkdir(parents=True)
    for name in ("python.wasm", "python-snapshot.wasm", "python-stdlib.zip"):
        shutil.copyfile(b / "out" / name, new / name)

    cp, np_src, pd_src = b / f"Python-{PYTHON}", b / "numpy-2.5.4", b / "pandas-3.1.0"
    numpy_files = tomllib.loads((np_src / "pyproject.toml").read_text())["project"]["license-files"]
    licences = {
        "cpython": [
            ("CPython LICENSE", (cp / "LICENSE").read_bytes()),
            ("CPython Doc/license.rst", (cp / "Doc" / "license.rst").read_bytes()),
            # HACL* (hashlib's hashes) is compiled in and license.rst does not cover it; its MIT
            # notice is the header comment of each of its files.
            ("CPython Modules/_hacl (HACL*), the header of Hacl_Hash_SHA2.h", hacl_notice(cp)),
        ],
        "numpy": [(f"numpy {f}", (np_src / f).read_bytes()) for f in numpy_files],
        "pandas": [("pandas LICENSE", (pd_src / "LICENSE").read_bytes())]
        + [
            (f"pandas LICENSES/{p.name}", p.read_bytes())
            for p in licence_files(pd_src / "LICENSES")
        ]
        # fast_float, which pandas' CSV tokenizer compiles in, ships its licences in its vendored
        # folder, and pandas' own license-files names them there.
        + [
            (f"pandas {p.relative_to(pd_src).as_posix()}", p.read_bytes())
            for p in sorted(pd_src.glob("subprojects/fast_float-*/LICENSE-*"))
        ],
        "zlib": [("zlib LICENSE", (b / "zlib-1.3.2" / "LICENSE").read_bytes())],
        "bzip2": [("bzip2 LICENSE", (b / "bzip2-1.0.8" / "LICENSE").read_bytes())],
        # Only liblzma is linked, and its files are 0BSD (COPYING says which parts are which).
        "xz": [(f"xz {n}", (b / "xz-5.8.4" / n).read_bytes()) for n in ("COPYING", "COPYING.0BSD")],
        "sqlite": [("SQLite sqlite3.h, its header comment", sqlite_notice(b))],
        # FreeType's BDF and PCF drivers are built, so their notices ship.
        "freetype": [
            (f"FreeType {n}", (b / "freetype-2.14.3" / n).read_bytes())
            for n in ("LICENSE.TXT", "docs/FTL.TXT", "src/bdf/README", "src/pcf/README")
        ],
        "harfbuzz": [
            (f"HarfBuzz {n}", (b / "harfbuzz-14.1.0" / n).read_bytes())
            for n in ("COPYING", "src/ms-use/COPYING")
        ]
        + [(f"Unicode's data terms ({UNICODE_TERMS})", pinned_bytes(d, UNICODE_TERMS))],
        "sheenbidi": [("SheenBidi LICENSE", (b / "SheenBidi-3.0.0" / "LICENSE").read_bytes())],
        "libraqm": [("libraqm COPYING", (b / "libraqm-0.10.5" / "COPYING").read_bytes())],
        "matplotlib": [
            (f"matplotlib LICENSE/{p.name}", p.read_bytes())
            for p in licence_files(b / "matplotlib-3.11.2" / "LICENSE")
        ]
        + [(f"matplotlib {n}", (b / "matplotlib-3.11.2" / n).read_bytes()) for n in MPL_NOTICES],
        "pillow": [("Pillow LICENSE", (b / "pillow-13.0.0" / "LICENSE").read_bytes())],
        "kiwisolver": [("kiwisolver LICENSE", (b / "kiwisolver-1.5.1" / "LICENSE").read_bytes())],
        # contourpy's licence and GIST's notice for its mpl2005 code; qhull's
        # licence now that it is linked
        "contourpy": [
            ("contourpy LICENSE", (b / "contourpy-1.4.0" / "LICENSE").read_bytes()),
            (
                f"matplotlib {CONTOURPY_GIST_NOTICE} (GIST's notice, for contourpy's mpl2005 code)",
                (b / "matplotlib-3.11.2" / CONTOURPY_GIST_NOTICE).read_bytes(),
            ),
        ],
        "qhull": [("Qhull COPYING.txt", (b / "qhull-8.0.2" / "COPYING.txt").read_bytes())],
        "libxml2": [("libxml2 Copyright", (b / "libxml2-2.15.4" / "Copyright").read_bytes())]
        + [
            (f"libxml2 {n}, its head comment", head_notice(b / "libxml2-2.15.4" / n, words))
            for n, words in LIBXML2_NOTICES
        ],
        "libxslt": [("libxslt Copyright", (b / "libxslt-1.1.45" / "Copyright").read_bytes())],
        "lxml": [(f"lxml {n}", (b / "lxml-6.1.3" / n).read_bytes()) for n in LXML_NOTICES],
        # Apache-2.0 headed by its CNRI derivation, then the modified file
        "regex": [
            ("regex LICENSE.txt", (b / "regex-2026.9.29" / "LICENSE.txt").read_bytes()),
            ("regex, as this build compiles it", modified_notice(root, "regex-2026.9.29")),
        ],
        "scipy": [(f"scipy {n}", (b / "scipy-1.18.1" / n).read_bytes()) for n in SCIPY_NOTICES]
        + [
            (f"scipy {n}, its head comment", scipy_head_notice(b / "scipy-1.18.1", n, words))
            for n, words in SCIPY_HEAD_NOTICES
        ],
        "openblas": [
            (f"OpenBLAS {n}", (b / "OpenBLAS-0.3.34" / n).read_bytes()) for n in OPENBLAS_NOTICES
        ],
        "scikit-learn": sklearn_parts(b / SKLEARN_TOP, d),
        "statsmodels": statsmodels_parts(b / STATSMODELS_TOP, d),
        **{pkg: wheel_licences(d / wheel) for pkg, wheel in WHEELS.items()},
        # the sdists' notices from their trees
        "pyyaml": [("PyYAML LICENSE", (b / "pyyaml-6.0.3" / "LICENSE").read_bytes())],
        "markupsafe": [
            ("MarkupSafe LICENSE.txt", (b / "markupsafe-3.0.4" / "LICENSE.txt").read_bytes())
        ],
        # networkx from its sdist, its notice from its tree
        "networkx": [("NetworkX LICENSE.txt", (b / "networkx-3.7" / "LICENSE.txt").read_bytes())],
        # seaborn from its sdist, its licence and its five vendored ones
        "seaborn": [
            (f"seaborn {n}", (b / "seaborn-0.13.2" / n).read_bytes()) for n in SEABORN_NOTICES
        ],
        # python-docx and python-pptx from their sdists, each its notice from its tree
        "python-docx": [
            ("python-docx LICENSE", (b / "python_docx-1.2.0" / "LICENSE").read_bytes())
        ],
        "python-pptx": [
            ("python-pptx LICENSE", (b / "python_pptx-1.0.2" / "LICENSE").read_bytes())
        ],
        "pdfminer-six": pdfminer_parts(b / PDFMINER_TOP, d),
        "xarray": [("xarray LICENSE", (b / XARRAY_TOP / "LICENSE").read_bytes())]
        + [
            (f"xarray licenses/{p.name}", p.read_bytes())
            for p in licence_files(b / XARRAY_TOP / "licenses")
        ],
        "wasi-libc": [(name, pinned_bytes(d, name)) for name in WASI_LIBC],
        "llvm-runtimes": [(name, pinned_bytes(d, name)) for name in LLVM],
    }
    tqdm_source = pinned_bytes(d, TQDM_WHEEL)
    (new / "LICENSES" / TQDM_SOURCE).write_bytes(tqdm_source)
    licences["tqdm"] += [
        (f"Mozilla Public License 2.0, the full text ({MPL_TEXT})", pinned_bytes(d, MPL_TEXT)),
        ("tqdm source", tqdm_source_part(tqdm_source)),
    ]
    with zipfile.ZipFile(io.BytesIO(pinned_bytes(d, SYMPY_WHEEL))) as z:
        licences["sympy"].append((f"{SYMPY_WHEEL}: {SYMPY_NESTED}", z.read(SYMPY_NESTED)))
    licences["reportlab"] += reportlab_parts(d)
    for component, parts in licences.items():
        if not parts:
            raise SystemExit(f"no licence text found for {component}")
        (new / "LICENSES" / f"{component}.txt").write_bytes(notice(parts))

    pins = [
        line.split()
        for line in (d / "SHA256SUMS").read_text().splitlines()
        if line.strip() and line.split()[1] not in RESEARCH_PINS
    ]
    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "recipes", "scripts"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    recipes = sorted(f for f in tracked if not Path(f).name.startswith("bench_"))
    wizer = (b / "out" / "wizer-command.txt").read_text().strip()
    manifest = [f"python {PYTHON}"]
    manifest += [f"package {name} {version}" for name, version in PACKAGES.items()]
    manifest += [f"pin {sha} {name}" for sha, name in pins]
    manifest += [f"recipe {sha256(root / f)} {f}" for f in recipes]
    manifest += [
        # The pin lines are every supported build host's inputs, not only this build's: each host
        # builds the same bytes, so MANIFEST is the same file from any of them.
        "x-pins every-supported-build-host",
        f"x-wizer {wizer}",
        f"x-source-date-epoch {os.environ['SOURCE_DATE_EPOCH']}",
        f"x-preimport {preimport_list((root / PREIMPORT_RECIPE).read_text())}",
        *snapshot_package_lines(
            snapshot_packages((root / SNAPSHOT_PACKAGES_RECIPE).read_text(), PACKAGES)
        ),
        f"x-snapshot-zip {sha256(new / 'python-stdlib.zip')}",
    ]
    (new / "MANIFEST").write_text("\n".join(manifest) + "\n")

    drop_litter(new)
    files = listed_files(new)
    (new / "SHA256SUMS").write_text(
        "".join(f"{sha256(p)}  {p.relative_to(new).as_posix()}\n" for p in files)
    )
    _remove(final)
    new.rename(final)
    print(f"artifacts: {len(files) + 1} files in build/artifacts")


if __name__ == "__main__":
    main()
