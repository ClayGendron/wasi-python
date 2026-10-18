"""Follow-up probes: dist-info kept, a writable /tmp, pytz's cost, the jinja2 loader, ctypes.

    uv run --no-sync python guest_followup.py <profile dir> <probe-set file> <out dir>

Builds <out>/python-stdlib-meta.zip: guest/python-stdlib-ext.zip plus each packed package's
dist-info METADATA and entry_points.txt (what step 70 drops today), and runs probes on it.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from wasi_python import Artifacts, artifacts, run

PROFILE, LIST, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
names = LIST.read_text().split()
base = artifacts()
ext = OUT / "guest" / "python-stdlib-ext.zip"
meta = OUT / "python-stdlib-meta.zip"
with zipfile.ZipFile(ext) as z:
    have = {i.filename: (i, z.read(i)) for i in z.infolist()}
n0 = len(have)
for n in names:
    for di in (PROFILE / "pkgs" / n).glob("*.dist-info"):
        for f in ("METADATA", "entry_points.txt"):
            p = di / f
            if p.is_file():
                info = zipfile.ZipInfo(f"{di.name}/{f}", (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                have[info.filename] = (info, p.read_bytes())
with zipfile.ZipFile(meta, "w") as z:
    for name in sorted(have):
        info, data = have[name]
        z.writestr(info, data, compresslevel=9)
print(f"dist-info members added: {len(have) - n0}")
EXT = Artifacts(snapshot=base.snapshot, plain=base.plain, stdlib_zip=ext, manifest=base.manifest)
META = Artifacts(snapshot=base.snapshot, plain=base.plain, stdlib_zip=meta, manifest=base.manifest)


def go(code, a, root=False):
    return run(["-c", code], artifacts=a, snapshot=False, fuel=10**13, deadline_s=1800,
               root=root, cache_dir=False)


PROBES = [
    ("pass, meta zip", META, False, "pass"),
    ("pandas loader type", EXT, False, "import pandas; print(type(pandas.__spec__.loader))"),
    ("jinja2 PackageLoader on zip", EXT, False,
     "import jinja2; l = jinja2.PackageLoader('pandas', 'io/formats/templates'); print(l._archive, l._template_root)"),
    ("openpyxl, root=True", EXT, True, """
import io, openpyxl, pandas as pd
df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}); b = io.BytesIO(); df.to_excel(b, index=False); b.seek(0)
print(pd.read_excel(b).equals(df))
"""),
    ("xlsxwriter in_memory, no /tmp", EXT, False, """
import io, xlsxwriter
b = io.BytesIO(); wb = xlsxwriter.Workbook(b, {"in_memory": True}); wb.add_worksheet().write("A1", 1); wb.close()
print(len(b.getvalue()) > 0)
"""),
    ("pandas xlsxwriter in_memory, no /tmp", EXT, False, """
import io, pandas as pd
b = io.BytesIO()
with pd.ExcelWriter(b, engine="xlsxwriter", engine_kwargs={"options": {"in_memory": True}}) as w:
    pd.DataFrame({"a": [1, 2]}).to_excel(w, index=False)
b.seek(0); print(pd.read_excel(b).shape)
"""),
    ("requests import, root=True", EXT, True, """
import requests
try:
    requests.get("http://example.com", timeout=1)
except Exception as e:
    print(type(e).__name__, str(e)[:160])
"""),
    ("import pytz", EXT, False, "import pytz"),
    ("pytz.timezone", EXT, False, "import pytz; pytz.timezone('Europe/Paris')"),
    ("pytz.timezone, small zip", EXT, False, "import pytz; pytz.utc"),
    ("zoneinfo baseline", EXT, False, "import zoneinfo; zoneinfo.ZoneInfo('Europe/Paris')"),
    ("tabulate with metadata", META, False,
     "import pandas as pd; print(pd.DataFrame({'a': [1], 'b': ['x']}).to_markdown())"),
    ("plotly with metadata", META, False, """
import plotly.express as px, pandas as pd
fig = px.bar(pd.DataFrame({"a": ["x", "y"], "b": [1, 2]}), x="a", y="b"); print(len(fig.to_json()))
print(len(fig.to_html(include_plotlyjs=True)))
"""),
    ("markdown tables with metadata", META, False,
     "import markdown; print(markdown.markdown('|a|\\n|-|\\n|1|', extensions=['tables']))"),
    ("altair with metadata", META, False, "import altair"),
    ("sympy, ctypes", EXT, False, "import ctypes; print([n for n in dir(ctypes) if not n.startswith('_')][:20])"),
    ("charset-normalizer longer", EXT, False, """
from charset_normalizer import from_bytes
print(from_bytes(("Grüße aus Köln, ça va très bien. " * 20).encode("cp1252")).best().encoding)
"""),
]

rows = ["probe\texit\tfuel_used\tstdout_tail\tstderr_tail"]
for label, a, root, code in PROBES:
    r = go(code, a, root)
    so = r.stdout.decode(errors="replace").strip().replace("\n", " | ")[-260:]
    se = r.stderr.decode(errors="replace").strip().splitlines()
    rows.append(f"{label}\t{r.exit_code}\t{r.fuel_used}\t{so}\t{se[-1][:200] if se else ''}")
    print(rows[-1], flush=True)
(OUT / "followup.tsv").write_text("\n".join(rows) + "\n")
