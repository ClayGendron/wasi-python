"""The preludes the spike measures. EVERYTHING imports every Python package the 0.1.1 MANIFEST names
(its `package` lines that are Python distributions), by import name, with the submodules a program
reaches for; the C libraries (zlib, freetype, openblas, ...) arrive through them."""

# MANIFEST distribution -> what a program imports
EVERYTHING_MODULES = [
    "numpy", "pandas", "dateutil", "dateutil.parser", "tzdata", "six", "regex",
    "matplotlib", "matplotlib.pyplot", "PIL", "PIL.Image", "kiwisolver", "cycler", "pyparsing", "packaging",
    "packaging.version", "fontTools", "fontTools.ttLib", "contourpy",
    "lxml", "lxml.etree", "lxml.html", "openpyxl", "et_xmlfile", "xlsxwriter", "xlrd", "pypdf",
    "bs4", "soupsieve", "html5lib", "webencodings", "defusedxml", "defusedxml.ElementTree", "xmltodict",
    "yaml", "tomli_w", "jinja2", "markupsafe", "tabulate", "charset_normalizer", "networkx", "patsy",
    "sympy", "mpmath", "attr", "attrs", "more_itertools", "toolz", "tqdm", "typing_extensions", "joblib",
    "cloudpickle", "threadpoolctl", "narwhals", "scipy", "scipy.linalg", "scipy.optimize", "scipy.stats",
    "scipy.signal", "scipy.sparse", "scipy.integrate", "scipy.interpolate", "scipy.special",
    "scipy.spatial", "scipy.cluster", "scipy.ndimage", "scipy.fft", "scipy.io",
    "sklearn", "sklearn.linear_model", "sklearn.tree", "sklearn.ensemble", "sklearn.cluster",
    "sklearn.datasets", "sklearn.model_selection", "sklearn.preprocessing", "sklearn.metrics",
    "sklearn.decomposition", "sklearn.neighbors", "sklearn.svm", "sklearn.pipeline",
    "seaborn", "reportlab", "reportlab.pdfgen.canvas", "statsmodels", "statsmodels.api",
    "statsmodels.formula.api", "formulaic", "interface_meta", "wrapt", "sqlite3",
]

MPL = "import matplotlib\nmatplotlib.use('Agg')\n"

PRELUDES = {
    "none": "pass",
    "numpy": "import numpy",
    "pandas": "import numpy, pandas",
    "scipy": "import numpy, scipy, scipy.optimize, scipy.stats",
    "sklearn": "import numpy, pandas, sklearn, sklearn.tree, sklearn.cluster, sklearn.datasets",
    "statsmodels": "import numpy, pandas, statsmodels.api",
    "matplotlib": MPL + "import matplotlib.pyplot",
    "everything": MPL + "".join(f"import {m}\n" for m in EVERYTHING_MODULES),
}

# The packages question 3 asks about, one prelude each (what a program typically imports).
PER_PACKAGE = {
    "numpy": "import numpy",
    "pandas": "import pandas",
    "scipy": "import scipy, scipy.optimize, scipy.stats",
    "sklearn": "import sklearn, sklearn.tree, sklearn.cluster, sklearn.datasets, sklearn.linear_model",
    "statsmodels": "import statsmodels.api, statsmodels.formula.api",
    "matplotlib": MPL + "import matplotlib.pyplot",
}
