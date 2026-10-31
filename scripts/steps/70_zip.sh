#!/bin/sh
# Step 70: the stdlib zip (build/out/python-stdlib.zip): bytecode-only, deflated, deterministic,
# compiled by the pinned host Python. _sysconfigdata and numpy's __config__
# say nothing about the build host: make_stdlib_zip.py sets their host keys
# to fixed values, and the text rewrites below, computed from what the build knows and applied in
# this order (the triple appears only inside the build-Python's path, which goes first), replace
# the rest. Each Python distribution's METADATA rides along: a wheel's from the wheel,
# numpy's and pandas' from their pinned sdists' PKG-INFO, and beside it the top_level.txt of the
# names to import: a wheel's are what it packs, and each --metadata names its own after its `=`,
# since a tree may hold several sdists' packages. CPython's own ctypes stays out (no libffi
# in wasi-sdk); the recipe's stand-in package takes its place. The tool protocol's guest package,
# `host`, rides along as the project's own code, with `host.display` and the figures backend
# `host.figures` for a call that asks for results; the snapshot does not pre-import it.
# Each module's code is compiled under the name zipimport gives a source in the same zip, the
# archive's guest path plus the member: that path is recipes/reactor_main.c's
# STDLIB_ZIP, written there once more, and step 80's ZIP. The plot packages:
# Pillow's, kiwisolver's and matplotlib's Python files from step 55, the four pure wheels, and their
# METADATA; matplotlib's backends but the ten a plot and its saves can use, its testing and
# sphinxext folders, and every tests/ folder stay out; its mpl-data goes in as one member, an inner
# archive the runner extracts and grants at the path matplotlib computes (Decision 5). contourpy:
# its Python package from step 55, its _build_config.py made host-neutral as numpy's
# __config__ is, and its METADATA from the pinned sdist. lxml:
# its Python package from step 54 without isoschematron, whose stand-in takes its place
# (Decision 8), and its METADATA from the pinned sdist. Tier A: twenty-seven
# pure wheels, and the pure package folders of pyyaml's, markupsafe's and networkx's sdists, each
# unpacked from its pin, given its carried patches, and staged under build/pure-install/, since
# each sdist keeps an .egg-info beside the package, which the zip refuses at a tree's top; their
# METADATA is their PKG-INFO. pyyaml and markupsafe publish no pure wheel; networkx does, but a
# wheel is never patched, so a pure package that needs a carried patch comes from its sdist,
# and its entry_points.txt rides beside its METADATA (--entry-points). scipy:
# its package as step 57 installed it from meson's plan, a stand-in at scipy/odr.py
# (scipy.odr needs Fortran), its METADATA from the sdist, and its __config__.py made host-neutral
# as numpy's is. scikit-learn: its package as step 58 staged it from the
# patched sdist, its METADATA from the sdist, and its two sample photographs left out with their
# folder (`--drop`, matplotlib's rule, which applies to every input and stops when it matches
# nothing): no JPEG decoder could read them, so their loaders fail by name. seaborn and reportlab:
# seaborn's package from its sdist, which holds the licences of the code it vendors,
# staged beside tier A's, its METADATA its PKG-INFO; reportlab's wheel, without its fonts (their
# licences are not approved, and reportlab cannot read them from a zip; Decision 4) and, until a
# later change ships it with Tyler C. Sarna's acknowledgement, without its barcode folder
# (Decision 4a), both by the same --drop; and one empty stand-in packed twice at the zip's top, as
# reportlab_mods.py and reportlab_settings.py, which reportlab imports before it would run
# ~/.reportlab_mods or ~/.reportlab_settings from the home folder as code, so it runs neither.
# statsmodels: its package as step 59 staged it from the
# patched sdist, its METADATA from the sdist, and three pure wheels, formulaic, interface-meta and
# wrapt (wrapt's own py3-none-any wheel: its C file is source and stays out); left out, each by a
# line written here so a reader sees it: the data files of the thirteen datasets whose stated
# terms the owner has not approved (each folder kept to its two modules, which
# statsmodels.datasets imports), every datasets/*/src/ folder (original sources no loader reads),
# and sandbox/rlsdata.txt, a table with no stated terms that nothing reads (`--drop` of one member
# by its exact name). python-docx and python-pptx: each package from its sdist with its carried
# patch, which reads each template through the package's loader, so it is found in the zip; their
# METADATA their PKG-INFO; and docx/templates/default-docx-template left out, the unpacked source
# of default.docx, which no module reads.
# pdfplumber: its pure wheel; pdfminer.six, which it reads PDF files with, from
# its sdist with its carried patch, which imports cryptography only where AES runs, without its
# cmap folder (the predefined CJK character maps, read by path; a font that names one and has no
# ToUnicode table reads as `(cid:N)`); xarray from its sdist, whose licences folder holds the
# notices of the code it adapts, with its entry_points.txt, as networkx's. Both sdists' METADATA
# their PKG-INFO.
# drawsvg: its pure wheel, whole: its raster, video and colour helpers and its widgets folder stay,
# so each names the package it lacks (CairoSVG, imageio, pwkit, ipywidgets) as it does natively.
set -eu
. "$(dirname "$0")/common.sh"

NUMPY_SITE=$(dirname "$(find "$B/numpy-install" -type d -name numpy -path '*site-packages*' | head -n 1)")
SYSCONFIG="$W/build/lib.wasi-wasm32-$PYTHON_MM/_sysconfigdata__wasi_wasm32-wasi.py"
[ -f "$SYSCONFIG" ] || die "no WASI _sysconfigdata at $SYSCONFIG"
# traceback's reasons for the stdlib modules this platform lacks, generated beside _sysconfigdata
# by CPython's build.
MISSING_INFO="$(dirname "$SYSCONFIG")/_missing_stdlib_info.py"
[ -f "$MISSING_INFO" ] || die "no _missing_stdlib_info at $MISSING_INFO"
for pkg in pillow kiwisolver matplotlib contourpy; do
  [ -d "$B/plot-install/$pkg" ] || die "build/plot-install/$pkg is missing: run step 55"
done
[ -d "$B/lxml-install/lxml" ] || die "build/lxml-install/lxml is missing: run step 54"
[ -d "$B/regex-install/regex" ] || die "build/regex-install/regex is missing: run step 53"
[ -d "$B/scipy-install/scipy" ] || die "build/scipy-install/scipy is missing: run step 57"
[ -d "$B/sklearn-install/sklearn" ] || die "build/sklearn-install/sklearn is missing: run step 58"
[ -d "$B/statsmodels-install/statsmodels" ] || die "build/statsmodels-install/statsmodels is missing: run step 59"
BACKENDS="__init__.py,registry.py,_backend_pdf_ps.py,backend_mixed.py,backend_agg.py,backend_pdf.py"
BACKENDS="$BACKENDS,backend_ps.py,backend_svg.py,backend_pgf.py,backend_template.py"
# The build-Python CPython's driver built, found as scripts/python-wasi-cross finds it: its
# directory under cross-build/ is the build triple. Both are host facts the zip must not carry.
BUILD_PYTHON=""
for dir in "$CP"/cross-build/*; do
  [ "$dir" = "$W" ] && continue
  for exe in "$dir/python.exe" "$dir/python"; do
    if [ -f "$exe" ] && [ -x "$exe" ]; then BUILD_PYTHON=$exe; break 2; fi
  done
done
[ -n "$BUILD_PYTHON" ] || die "no build-Python under $CP/cross-build"
TRIPLE=$(basename "$(dirname "$BUILD_PYTHON")")
remove "$B/pyyaml-6.0.3" "$B/markupsafe-3.0.4" "$B/networkx-3.7" "$B/seaborn-0.13.2" \
  "$B/python_docx-1.2.0" "$B/python_pptx-1.0.2" "$B/pdfminer_six-20260107" "$B/xarray-2026.9.0" \
  "$B/pure-install"
for sdist in pyyaml-6.0.3 markupsafe-3.0.4 networkx-3.7 seaborn-0.13.2 python_docx-1.2.0 \
  python_pptx-1.0.2 pdfminer_six-20260107 xarray-2026.9.0; do
  tar -xzf "$(pinned "$sdist.tar.gz")" -C "$B"
  [ -d "$B/$sdist" ] || die "the pinned tarball did not unpack to build/$sdist"
  patch_tree "$B/$sdist"
done
mkdir -p "$B/pure-install"
cp -R "$B/pyyaml-6.0.3/lib/yaml" "$B/pure-install/yaml"
cp -R "$B/markupsafe-3.0.4/src/markupsafe" "$B/pure-install/markupsafe"
cp -R "$B/networkx-3.7/networkx" "$B/pure-install/networkx"
cp -R "$B/seaborn-0.13.2/seaborn" "$B/pure-install/seaborn"
cp -R "$B/python_docx-1.2.0/src/docx" "$B/pure-install/docx"
cp -R "$B/python_pptx-1.0.2/src/pptx" "$B/pure-install/pptx"
cp -R "$B/pdfminer_six-20260107/pdfminer" "$B/pure-install/pdfminer"
cp -R "$B/xarray-2026.9.0/xarray" "$B/pure-install/xarray"
mkdir -p "$OUT"
host_from_source
PYTHONHASHSEED=0 "$HOSTPY" "$HERE/scripts/make_stdlib_zip.py" \
  --lib "$CP/Lib" --skip ctypes \
  --code-prefix "/usr/local/lib/python$PYTHON_TAG.zip/" \
  --tree "$NUMPY_SITE" \
  --tree "$B/pandas-install" \
  --tree "$B/plot-install/pillow" \
  --tree "$B/plot-install/kiwisolver" \
  --tree "$B/plot-install/matplotlib" \
  --tree "$B/plot-install/contourpy" \
  --tree "$B/lxml-install" \
  --tree "$B/regex-install" \
  --tree "$B/pure-install" \
  --tree "$B/scipy-install" \
  --tree "$B/sklearn-install" \
  --tree "$B/statsmodels-install" \
  --wheel "$(pinned python_dateutil-2.9.0.post0-py2.py3-none-any.whl)" \
  --wheel "$(pinned tzdata-2026.6-py2.py3-none-any.whl)" \
  --wheel "$(pinned six-1.17.0-py2.py3-none-any.whl)" \
  --wheel "$(pinned cycler-0.12.1-py3-none-any.whl)" \
  --wheel "$(pinned pyparsing-3.3.3-py3-none-any.whl)" \
  --wheel "$(pinned packaging-26.3-py3-none-any.whl)" \
  --wheel "$(pinned fonttools-4.67.0-py3-none-any.whl)" \
  --wheel "$(pinned openpyxl-3.1.5-py2.py3-none-any.whl)" \
  --wheel "$(pinned et_xmlfile-2.0.0-py3-none-any.whl)" \
  --wheel "$(pinned xlsxwriter-3.2.9-py3-none-any.whl)" \
  --wheel "$(pinned xlrd-2.0.2-py2.py3-none-any.whl)" \
  --wheel "$(pinned pypdf-6.21.4-py3-none-any.whl)" \
  --wheel "$(pinned defusedxml-0.7.1-py2.py3-none-any.whl)" \
  --wheel "$(pinned beautifulsoup4-4.15.0-py3-none-any.whl)" \
  --wheel "$(pinned soupsieve-3.0.4-py3-none-any.whl)" \
  --wheel "$(pinned html5lib-1.1-py2.py3-none-any.whl)" \
  --wheel "$(pinned webencodings-0.6.1-py3-none-any.whl)" \
  --wheel "$(pinned tomli_w-1.2.0-py3-none-any.whl)" \
  --wheel "$(pinned jinja2-3.1.6-py3-none-any.whl)" \
  --wheel "$(pinned tabulate-0.10.0-py3-none-any.whl)" \
  --wheel "$(pinned charset_normalizer-3.5.2-py3-none-any.whl)" \
  --wheel "$(pinned xmltodict-1.0.4-py3-none-any.whl)" \
  --wheel "$(pinned sympy-1.14.0-py3-none-any.whl)" \
  --wheel "$(pinned mpmath-1.3.0-py3-none-any.whl)" \
  --wheel "$(pinned patsy-1.0.3-py2.py3-none-any.whl)" \
  --wheel "$(pinned attrs-26.1.0-py3-none-any.whl)" \
  --wheel "$(pinned more_itertools-11.2.1-py3-none-any.whl)" \
  --wheel "$(pinned toolz-1.2.0-py3-none-any.whl)" \
  --wheel "$(pinned tqdm-4.70.1-py3-none-any.whl)" \
  --wheel "$(pinned typing_extensions-4.16.0-py3-none-any.whl)" \
  --wheel "$(pinned joblib-1.6.0-py3-none-any.whl)" \
  --wheel "$(pinned cloudpickle-3.1.2-py3-none-any.whl)" \
  --wheel "$(pinned threadpoolctl-3.7.0-py3-none-any.whl)" \
  --wheel "$(pinned narwhals-2.27.1-py3-none-any.whl)" \
  --wheel "$(pinned reportlab-5.0.1-py3-none-any.whl)" \
  --wheel "$(pinned formulaic-1.2.2-py3-none-any.whl)" \
  --wheel "$(pinned interface_meta-2.0.1-py3-none-any.whl)" \
  --wheel "$(pinned wrapt-2.5.2-py3-none-any.whl)" \
  --wheel "$(pinned pdfplumber-0.11.10-py3-none-any.whl)" \
  --wheel "$(pinned drawsvg-2.4.2-py3-none-any.whl)" \
  --metadata "$B/numpy-2.5.4/PKG-INFO=numpy" \
  --metadata "$B/pandas-3.0.6/PKG-INFO=pandas" \
  --metadata "$B/pillow-13.0.0/PKG-INFO=PIL" \
  --metadata "$B/kiwisolver-1.5.1/PKG-INFO=kiwisolver" \
  --metadata "$B/matplotlib-3.11.2/PKG-INFO=matplotlib,mpl_toolkits,pylab" \
  --metadata "$B/contourpy-1.4.0/PKG-INFO=contourpy" \
  --metadata "$B/lxml-6.1.3/PKG-INFO=lxml" \
  --metadata "$B/regex-2026.9.29/PKG-INFO=regex" \
  --metadata "$B/pyyaml-6.0.3/PKG-INFO=yaml" \
  --metadata "$B/markupsafe-3.0.4/PKG-INFO=markupsafe" \
  --metadata "$B/networkx-3.7/PKG-INFO=networkx" \
  --entry-points "$B/networkx-3.7/PKG-INFO" "$B/networkx-3.7/networkx.egg-info/entry_points.txt" \
  --metadata "$B/scipy-1.18.1/PKG-INFO=scipy" \
  --metadata "$B/scikit_learn-1.9.1/PKG-INFO=sklearn" \
  --metadata "$B/seaborn-0.13.2/PKG-INFO=seaborn" \
  --metadata "$B/statsmodels-0.15.0/PKG-INFO=statsmodels" \
  --metadata "$B/python_docx-1.2.0/PKG-INFO=docx" \
  --metadata "$B/python_pptx-1.0.2/PKG-INFO=pptx" \
  --metadata "$B/pdfminer_six-20260107/PKG-INFO=pdfminer" \
  --metadata "$B/xarray-2026.9.0/PKG-INFO=xarray" \
  --entry-points "$B/xarray-2026.9.0/PKG-INFO" "$B/xarray-2026.9.0/xarray.egg-info/entry_points.txt" \
  --keep "matplotlib/backends=$BACKENDS" \
  --drop matplotlib/testing \
  --drop matplotlib/sphinxext \
  --drop sklearn/datasets/images \
  --drop reportlab/fonts \
  --drop reportlab/graphics/barcode \
  --keep statsmodels/datasets/cancer=__init__.py,data.py \
  --keep statsmodels/datasets/ccard=__init__.py,data.py \
  --keep statsmodels/datasets/china_smoking=__init__.py,data.py \
  --keep statsmodels/datasets/committee=__init__.py,data.py \
  --keep statsmodels/datasets/copper=__init__.py,data.py \
  --keep statsmodels/datasets/cpunish=__init__.py,data.py \
  --keep statsmodels/datasets/fair=__init__.py,data.py \
  --keep statsmodels/datasets/fertility=__init__.py,data.py \
  --keep statsmodels/datasets/heart=__init__.py,data.py \
  --keep statsmodels/datasets/interest_inflation=__init__.py,data.py \
  --keep statsmodels/datasets/scotland=__init__.py,data.py \
  --keep statsmodels/datasets/spector=__init__.py,data.py \
  --keep statsmodels/datasets/star98=__init__.py,data.py \
  --drop statsmodels/datasets/anes96/src \
  --drop statsmodels/datasets/co2/src \
  --drop statsmodels/datasets/elnino/src \
  --drop statsmodels/datasets/grunfeld/src \
  --drop statsmodels/datasets/macrodata/src \
  --drop statsmodels/datasets/modechoice/src \
  --drop statsmodels/datasets/randhie/src \
  --drop statsmodels/datasets/sunspots/src \
  --drop statsmodels/sandbox/rlsdata.txt \
  --drop docx/templates/default-docx-template \
  --drop pdfminer/cmap \
  --inner matplotlib/mpl-data \
  --file "$SYSCONFIG=_sysconfigdata__wasi_wasm32-wasi.py" \
  --file "$MISSING_INFO=_missing_stdlib_info.py" \
  --file "$HERE/recipes/ctypes_stand_in/__init__.py=ctypes/__init__.py" \
  --file "$HERE/recipes/ctypes_stand_in/_types.py=ctypes/_types.py" \
  --file "$HERE/recipes/ctypes_stand_in/util.py=ctypes/util.py" \
  --file "$HERE/recipes/mmap_stub.py=mmap.py" \
  --file "$HERE/recipes/lxml_isoschematron_stand_in.py=lxml/isoschematron.py" \
  --file "$HERE/recipes/scipy_odr_stand_in.py=scipy/odr.py" \
  --file "$HERE/recipes/reportlab_start_up_stand_in.py=reportlab_mods.py" \
  --file "$HERE/recipes/reportlab_start_up_stand_in.py=reportlab_settings.py" \
  --file "$HERE/recipes/guest/host/__init__.py=host/__init__.py" \
  --file "$HERE/recipes/guest/host/tools.py=host/tools.py" \
  --file "$HERE/recipes/guest/host/display.py=host/display.py" \
  --file "$HERE/recipes/guest/host/figures.py=host/figures.py" \
  --replace "cross-build/$TRIPLE/$(basename "$BUILD_PYTHON")=cross-build/build/python" \
  --replace "$WASI_SDK_DIR=wasi-sdk" \
  --replace "$WASMTIME_DIR=wasmtime" \
  --replace "$TRIPLE=build" \
  --replace "$HERE=/wasi-python-build" \
  "$OUT/python-stdlib.zip"
