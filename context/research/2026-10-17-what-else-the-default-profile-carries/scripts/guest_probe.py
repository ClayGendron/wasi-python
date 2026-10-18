"""Run candidate pure-Python packages inside today's python.wasm (plain reactor).

    uv run --no-sync python guest_probe.py <profile dir> <tier list file> <out dir>

Builds <out>/python-stdlib-ext.zip: today's stdlib zip (build/artifacts) plus every member of
zips/<name>.zip for the names listed (members already in the zip are kept as they are). Then, on
the plain reactor (snapshot=False: the snapshot froze the old zip's directory), it measures
`-c pass` with the old zip and the new one, and runs one probe program per package with fuel
metering. Writes <out>/fuel.tsv and <out>/probes.tsv and each probe's stderr tail.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from wasi_python import Artifacts, Grant, artifacts, run

PROFILE, LIST, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
names = [n.strip() for n in LIST.read_text().split() if n.strip()]
base = artifacts()

ext = OUT / "python-stdlib-ext.zip"
with zipfile.ZipFile(base.stdlib_zip) as z:
    have = {i.filename: (i, z.read(i)) for i in z.infolist()}
before = len(have)
added: dict[str, int] = {}
for n in names:
    with zipfile.ZipFile(PROFILE / "zips" / f"{n}.zip") as z:
        k = 0
        for i in z.infolist():
            if i.filename not in have:
                have[i.filename] = (i, z.read(i))
                k += 1
        added[n] = k
with zipfile.ZipFile(ext, "w") as z:
    for name in sorted(have):
        info, data = have[name]
        z.writestr(info, data, compresslevel=9)
after = len(have)
art = Artifacts(snapshot=base.snapshot, plain=base.plain, stdlib_zip=ext, manifest=base.manifest)

FUEL = 10**13


def go(code: str, a: Artifacts, grants=()):
    return run(["-c", code], artifacts=a, snapshot=False, fuel=FUEL, deadline_s=900,
               grants=grants, cache_dir=False)


rows = ["case\tmembers\tfuel_used\texit"]
for label, a, m in (("old zip", base, before), ("new zip", art, after)):
    for rep in range(2):
        r = go("pass", a)
        rows.append(f"{label} pass #{rep + 1}\t{m}\t{r.fuel_used}\t{r.exit_code}")
r = go("pass", base, ())
(OUT / "fuel.tsv").write_text("\n".join(rows) + "\n")
(OUT / "added.tsv").write_text("".join(f"{k}\t{v}\n" for k, v in added.items()))
print("\n".join(rows))

PDF = r"""
def tiny_pdf(text):
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            None,
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    stream = b"BT /F1 18 Tf 20 100 Td (" + text.encode() + b") Tj ET"
    objs[3] = b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
    out = bytearray(b"%PDF-1.4\n"); offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out)); out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    x = len(out)
    out += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode()
    for o in offs: out += f"{o:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n".encode()
    return bytes(out)
"""

PROBES = {
    "openpyxl": """
import io, openpyxl, pandas as pd
wb = openpyxl.Workbook(); ws = wb.active; ws["A1"] = "x"; ws["B1"] = 41; ws["B2"] = "=B1+1"
b = io.BytesIO(); wb.save(b); b.seek(0)
print(openpyxl.load_workbook(b)["Sheet"]["B1"].value)
df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}); b = io.BytesIO(); df.to_excel(b, index=False); b.seek(0)
print(pd.read_excel(b).equals(df))
""",
    "xlsxwriter": """
import io, pandas as pd
df = pd.DataFrame({"a": [1, 2]}); b = io.BytesIO(); df.to_excel(b, engine="xlsxwriter", index=False)
b.seek(0); print(pd.read_excel(b).equals(df))
""",
    "odfpy": """
import io, pandas as pd
df = pd.DataFrame({"a": [1, 2]}); b = io.BytesIO(); df.to_excel(b, engine="odf", index=False)
b.seek(0); print(pd.read_excel(b, engine="odf").equals(df))
""",
    "xlrd": "import xlrd; print(xlrd.__version__)",
    "pyxlsb": "import pyxlsb; print('ok')",
    "pypdf": PDF + """
import io, pypdf
r = pypdf.PdfReader(io.BytesIO(tiny_pdf("Hello agent"))); print(len(r.pages), r.pages[0].extract_text())
w = pypdf.PdfWriter(); w.add_blank_page(100, 100); b = io.BytesIO(); w.write(b); print(len(b.getvalue()) > 0)
""",
    "pdfminer.six": PDF + """
import io
from pdfminer.high_level import extract_text
print(repr(extract_text(io.BytesIO(tiny_pdf("Hello agent")))))
""",
    "beautifulsoup4": """
from bs4 import BeautifulSoup
s = BeautifulSoup("<table><tr><td class=a>1</td></tr></table>", "html.parser"); print(s.select_one("td.a").text)
""",
    "html5lib": """
import io, pandas as pd
html = "<table><tr><th>a</th><th>b</th></tr><tr><td>1</td><td>x</td></tr></table>"
print(pd.read_html(io.StringIO(html), flavor="bs4")[0].to_dict())
""",
    "pyyaml": """
import yaml; d = yaml.safe_load("a: [1, 2]\\nb: {c: x}"); print(d, yaml.__with_libyaml__); print(yaml.safe_dump(d))
""",
    "tomli-w": "import tomli_w, tomllib; s = tomli_w.dumps({'a': {'b': [1, 2]}}); print(tomllib.loads(s))",
    "jinja2": """
import jinja2, pandas as pd
print(jinja2.Template("{{ x|upper }}").render(x="hi"))
print(len(pd.DataFrame({"a": [1.5]}).style.format("{:.1f}").to_html()) > 0)
""",
    "tabulate": "import pandas as pd; print(pd.DataFrame({'a': [1], 'b': ['x']}).to_markdown())",
    "pytz": """
import pytz, datetime; print(pytz.timezone("Europe/Paris").localize(datetime.datetime(2026, 7, 1)).isoformat())
""",
    "charset-normalizer": """
from charset_normalizer import from_bytes; print(from_bytes("Grüße, café".encode("cp1252")).best().encoding)
""",
    "networkx": """
import networkx as nx; g = nx.karate_club_graph()
print(nx.shortest_path_length(g, 0, 33), round(max(nx.betweenness_centrality(g).values()), 4))
try:
    print(round(nx.pagerank(g)[0], 4))
except Exception as e:
    print("pagerank:", type(e).__name__, e)
""",
    "sympy": """
import sympy as sp; x = sp.symbols("x"); print(sp.solve(x**2 - 2, x), sp.integrate(sp.sin(x)**2, x))
""",
    "mpmath": "import mpmath; mpmath.mp.dps = 30; print(mpmath.pi, mpmath.quad(mpmath.exp, [0, 1]))",
    "patsy": """
import patsy, pandas as pd; df = pd.DataFrame({"y": [1., 2, 3], "x": [1., 0, 2], "g": list("aba")})
y, X = patsy.dmatrices("y ~ x + C(g)", df); print(X.design_info.column_names)
""",
    "joblib": """
from joblib import Parallel, delayed
print(Parallel(n_jobs=1)(delayed(pow)(i, 2) for i in range(4)))
try:
    print(Parallel(n_jobs=2)(delayed(pow)(i, 2) for i in range(4)))
except Exception as e:
    print("n_jobs=2:", type(e).__name__, e)
""",
    "threadpoolctl": "import threadpoolctl; print(threadpoolctl.threadpool_info())",
    "attrs": "import attrs\n@attrs.define\nclass P:\n    x: int\nprint(P(1))",
    "more-itertools": "import more_itertools as mi; print(list(mi.chunked(range(5), 2)))",
    "toolz": "import toolz; print(toolz.groupby(len, ['a', 'bb', 'cc']))",
    "rich": """
import io; from rich.console import Console; from rich.table import Table
c = Console(file=io.StringIO(), width=40); t = Table("a", "b"); t.add_row("1", "x"); c.print(t); print(c.file.getvalue())
""",
    "pygments": """
from pygments import highlight; from pygments.lexers import PythonLexer; from pygments.formatters import HtmlFormatter
print(len(highlight("x = 1", PythonLexer(), HtmlFormatter())))
""",
    "markdown-it-py": "from markdown_it import MarkdownIt; print(MarkdownIt().render('# hi *x*'))",
    "markdown": "import markdown; print(markdown.markdown('# hi', extensions=['tables']))",
    "tqdm": "from tqdm import tqdm\nprint(sum(tqdm(range(1000))))",
    "typing-extensions": "import typing_extensions; print('ok')",
    "xmltodict": "import xmltodict; print(xmltodict.parse('<a><b>1</b></a>'))",
    "docx2txt": "import docx2txt; print('ok')",
    "plotly": """
import plotly.express as px, pandas as pd
fig = px.bar(pd.DataFrame({"a": ["x", "y"], "b": [1, 2]}), x="a", y="b"); print(len(fig.to_json()))
print(len(fig.to_html(include_plotlyjs=True)))
""",
    "narwhals": "import narwhals as nw, pandas as pd; print(nw.from_native(pd.DataFrame({'a': [1]})).shape)",
    "altair": "import altair as alt; print(alt.__version__)",
    "jsonschema": "import jsonschema; print('ok')",
    "requests": """
import requests
try:
    requests.get("http://example.com", timeout=1)
except Exception as e:
    print(type(e).__name__, str(e)[:120])
""",
    "httpx": "import httpx; print('ok')",
    "pydantic": "import pydantic; print('ok')",
    "python-docx": "import docx; print('ok')",
    "python-pptx": "import pptx; print('ok')",
    "seaborn": "import seaborn; print('ok')",
    "statsmodels": "import statsmodels.api; print('ok')",
    "socket": "import socket; print(socket.socket)",
    "threading": """
import threading
try:
    t = threading.Thread(target=print, args=("in thread",)); t.start(); t.join()
except Exception as e:
    print(type(e).__name__, e)
""",
}

rows = ["probe\texit\tfuel_used\tstdout_tail\tstderr_tail"]
for n, code in PROBES.items():
    r = go(code, art)
    so = r.stdout.decode(errors="replace").strip().replace("\n", " | ")[-300:]
    se = r.stderr.decode(errors="replace").strip().splitlines()
    (OUT / f"probe-{n}.stderr.txt").write_bytes(r.stderr)
    (OUT / f"probe-{n}.stdout.txt").write_bytes(r.stdout)
    rows.append(f"{n}\t{r.exit_code}\t{r.fuel_used}\t{so}\t{se[-1] if se else ''}")
    print(rows[-1][:400], flush=True)
(OUT / "probes.tsv").write_text("\n".join(rows) + "\n")
