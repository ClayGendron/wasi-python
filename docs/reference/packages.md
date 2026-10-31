# Packages

This page lists the packages in the artifact set, with their versions and a line on what works. The [limitations page](limitations.md) has what does not.

Every package here is pinned to one version. The set carries one version of each package, built from its released source, not a choice of versions. Compiled code is linked into `python.wasm` as *builtin modules*: modules compiled into the interpreter itself, so nothing is loaded from a shared library at run time. The Python half of each package is in the stdlib zip.

## The interpreter

CPython 3.15.2, built for `wasm32-wasip1`. `python.wasm -V` prints the version, then a line of the platform's facts:

> (wasm32-wasip1: numpy's default integer is 32-bit; no threads; no ctypes, mmap, sockets, ssl, zstd or scipy.odr; compute about 1.3 to 2.3 times slower than native)

`zlib`, `bz2`, `lzma` and `sqlite3` are built in, over zlib, bzip2 1.0.8, liblzma from xz 5.8.4 and SQLite 3.54.1. `bz2`, `lzma` and `tarfile`'s `bz2` and `xz` modes write the same bytes as native Python. `sqlite3` has native's feature set: FTS3/4/5, R-tree, Geopoly, math functions, dbstat and percentile.

## Compiled packages

| package | version | what works |
|---|---|---|
| numpy | 2.5.2 | Built in. Linear algebra, `dot` and `matmul` run on the set's OpenBLAS 0.3.34, as native numpy's do. The default integer is 32-bit. |
| pandas | 3.0.6 | Built in, including `read_html`, `read_xml` and `to_xml` through lxml, `.xlsx` through openpyxl and xlsxwriter, and the Styler. |
| scipy | 1.18.1 | Everything but `scipy.odr`: `linalg`, `sparse`, `optimize` (HiGHS's `linprog` and `milp`), `integrate`, `interpolate`, `signal`, `fft`, `special`, `stats`, `spatial`, `ndimage`, `cluster`, `io` and the rest. It runs on one thread. |
| scikit-learn | 1.9.1 | Every public submodule, and its six bundled datasets. It runs serially, with the same answers. |
| statsmodels | 0.15.0 | Every public submodule, `statsmodels.api` and `statsmodels.formula.api` included, with formulaic 1.2.2 (with interface-meta 2.0.1 and wrapt 2.5.1) as a second formula engine. Sixteen public-domain datasets ship. |
| matplotlib | 3.11.2 | The Agg backend. PNG, PDF, PS, EPS and SVG save. Contours through contourpy 1.4.0, and Delaunay triangulations through qhull 8.0.2. Text through FreeType 2.14.3, HarfBuzz 14.1.0, SheenBidi 3.0.0 and libraqm 0.10.5. See [matplotlib](../how-to/matplotlib.md). |
| Pillow | 13.0.0 | Its core, with zlib only: PNG works; JPEG and the other codecs do not. |
| kiwisolver | 1.5.1 | Built in, as one of matplotlib's dependencies. |
| contourpy | 1.4.0 | Contours for matplotlib. Its threaded algorithm runs on one thread. |
| lxml | 6.1.3 | `lxml.etree` and `lxml.objectify` over libxml2 2.15.4 and libxslt 1.1.45 with libexslt: XPath, XSLT, XInclude, C14N, DTD, XML Schema, RELAX NG and Schematron validation, the HTML parser and `iterparse`. |
| regex | 2026.9.29 | Fuzzy matching, full Unicode properties, graphemes, variable-length lookbehind, `captures()`, with native regex's answers. |

A *golden job* is a fixed program whose output the project compares with native Python's at the same pins. numpy, pandas, scipy, scikit-learn, statsmodels, matplotlib, lxml and regex each have golden jobs, and each gives native's answers.

## Pure-Python packages

matplotlib brings fontTools 4.67.0, cycler, pyparsing and packaging. The zip also carries python-dateutil, tzdata and six. Besides these, the stdlib zip carries thirty pure-Python packages, plus seaborn, reportlab, python-docx, python-pptx, pdfplumber with pdfminer.six, and xarray:

| family | distribution and version | what it is for |
|---|---|---|
| Excel | openpyxl 3.1.5, et-xmlfile 2.0.0 | read and write `.xlsx`; pandas' `.xlsx` reader |
| | xlsxwriter 3.2.9 | write `.xlsx` (pandas' default writer), in memory too |
| | xlrd 2.0.2 | read old `.xls` files |
| plotting | seaborn 0.13.2 (beside matplotlib) | statistical plots over pandas frames |
| labelled arrays | xarray 2026.9.0 | n-dimensional arrays with named dimensions and labels; netCDF3 through scipy |
| PDF | pypdf 6.21.4 | read, extract text, merge, split, encrypt (RC4) |
| | reportlab 5.0.1 | write PDFs: text, tables, charts, Unicode text, images |
| | pdfplumber 0.11.10, pdfminer.six 20260107 | text, words with their positions, and tables from PDF pages |
| documents | python-docx 1.2.0 | read and write Word `.docx` |
| | python-pptx 1.0.2 | read and write PowerPoint `.pptx`, charts included |
| HTML and XML | beautifulsoup4 4.15.0, soupsieve 3.0.4 | parse messy HTML, CSS selectors |
| | html5lib 1.1, webencodings 0.6.1 | a browser's HTML parsing; bs4's `html5lib` parser |
| | defusedxml 0.7.1 | parse untrusted XML, refusing entity tricks |
| | xmltodict 1.0.4 | XML to dicts and back |
| text formats | pyyaml 6.0.3 | YAML |
| | tomli-w 1.2.0 | write TOML (the stdlib's `tomllib` reads it) |
| | jinja2 3.1.6, markupsafe 3.0.4 | templates, HTML escaping |
| | tabulate 0.10.0 | text tables; `df.to_markdown()` |
| | charset-normalizer 3.5.2 | guess a file's encoding |
| modelling | networkx 3.7 | graphs and their algorithms |
| | patsy 1.0.3 | model formulas (`y ~ x + C(g)`) to design matrices |
| symbolic | sympy 1.14.0, mpmath 1.3.0 | symbolic maths; arbitrary precision |
| utilities | attrs 26.1.0, typing-extensions 4.16.0 | classes without boilerplate; typing backports |
| | more-itertools 11.2.1, toolz 1.2.0 | iteration and functional helpers |
| | tqdm 4.70.1 | progress bars |
| | joblib 1.6.0, cloudpickle 3.1.2 | caching, `Parallel`, pickling closures |
| | threadpoolctl 3.7.0 | thread-pool limits (there are none to limit here) |
| | narwhals 2.27.1 | dataframe-agnostic code over pandas |

pyyaml and markupsafe come from their source releases and run as pure Python: pyyaml has no libyaml, and `yaml.CSafeLoader` is absent. Each package's `importlib.metadata` answers work, so `df.to_markdown()` finds tabulate.

python-docx and python-pptx start from their own default templates, which they read from the zip. python-pptx's `fit_text()` needs Pillow's FreeType module, which the set lacks: it raises `OSError` looking for the system's fonts, or `ImportError` when given `font_file=`. Set a font size instead.

Each family has a golden job whose output equals native Python's at the same pins.

## What is not carried

These are not in the set, so each raises its `ImportError`, as it does natively without it:

- `pytz`: use `zoneinfo`, which reads the stdlib zip's tzdata;
- `cryptography`, which pypdf and pdfminer.six need for AES;
- `pypdfium2`, for pdfplumber's page images;
- `antlr4` and `lark`, for sympy's `parse_latex`;
- `odfpy`, for pandas' `engine="odf"`, and `pyxlsb`, for `.xlsb` files;
- `cssselect` and `lxml_html_clean`, for `lxml.cssselect` and `lxml.html.clean`.

pdfplumber's `page.to_image()` needs pypdfium2, which is not carried; it raises `ModuleNotFoundError`. pdfminer.six reads files encrypted with RC4, and raises `ModuleNotFoundError` naming `cryptography` for one encrypted with AES. xarray's other file engines (netCDF4, h5netcdf, zarr) and its tutorial data are not carried; netCDF3 works through scipy.

reportlab's bitmap renderer needs rlPyCairo, which is not carried either; it raises `RenderPMError`. Draw reportlab charts to PDF or SVG instead.

## Adding a package of your own

You cannot add a compiled package: the guest has no `dlopen` and loads no shared library. A pure-Python package can come from a read-only grant named in `import_path=`, as on the [guest filesystem](guest-filesystem.md#the-import-path) page. It comes after the runtime on the import path, so a module the set already has is always the set's.

There is no `pip` inside the guest.

To build a package into the artifact set itself, see [Adding a package](../contributing/adding-a-package.md).

## In one line

CPython 3.15.2 with numpy, pandas, scipy, scikit-learn, statsmodels, matplotlib, lxml and regex compiled in, and thirty pure-Python packages plus seaborn, reportlab, python-docx, python-pptx, pdfplumber with pdfminer.six, and xarray in the zip, each at one pinned version.
