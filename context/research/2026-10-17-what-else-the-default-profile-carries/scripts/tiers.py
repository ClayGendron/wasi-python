"""Sum step-70 members and deflated bytes per proposed tier, from out/measure.tsv.

    tiers.py <measure.tsv> <fuel per member>
"""

import csv
import sys

TIERS = {
    "A1 office and documents": ["openpyxl", "et-xmlfile", "xlsxwriter", "xlrd", "pypdf"],
    "A2 web text and formats": ["beautifulsoup4", "soupsieve", "html5lib", "webencodings",
                                "pyyaml", "tomli-w", "jinja2", "markupsafe", "tabulate",
                                "charset-normalizer", "xmltodict", "defusedxml"],
    "A3 maths and modelling (pure)": ["networkx", "sympy", "mpmath", "patsy"],
    "A4 small utilities": ["attrs", "more-itertools", "toolz", "tqdm", "typing-extensions",
                           "joblib", "cloudpickle", "threadpoolctl", "narwhals"],
    "A5 seaborn (after matplotlib)": ["seaborn"],
    "A? pytz": ["pytz"],
    "B scikit-learn (python part)": ["scikit-learn"],
    "B statsmodels (python part) + formulaic deps (est.)": ["statsmodels", "formulaic", "interface-meta", "wrapt"],
    "B lxml (python part) + python-docx + python-pptx": ["lxml", "python-docx", "python-pptx"],
    "B regex (python part)": ["regex"],
    "C plotly": ["plotly"],
    "C pdfminer.six": ["pdfminer.six"],
    "C rich stack": ["rich", "pygments", "markdown-it-py", "mdurl"],
    "C xarray": ["xarray"],
    "C faker": ["faker"],
    "today: scipy (python part)": ["scipy"],
    "today: matplotlib set (python part)": ["matplotlib", "fonttools", "pillow", "contourpy",
                                            "cycler", "kiwisolver", "pyparsing", "packaging"],
}

rows = {r["name"]: r for r in csv.DictReader(open(sys.argv[1]), delimiter="\t")}
per = float(sys.argv[2])
print("tier\tmembers\tdeflated_bytes\tplain_start_fuel")
tot_m = tot_b = 0
for tier, names in TIERS.items():
    m = sum(int(rows[n]["members"]) for n in names)
    b = sum(int(rows[n]["deflated_bytes"]) for n in names)
    print(f"{tier}\t{m}\t{b}\t{m * per / 1e6:.1f} M")
    if tier.startswith("A") and "?" not in tier:
        tot_m += m
        tot_b += b
print(f"A total (without pytz)\t{tot_m}\t{tot_b}\t{tot_m * per / 1e6:.1f} M")
