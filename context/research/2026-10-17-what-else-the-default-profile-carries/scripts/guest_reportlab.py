"""reportlab (pure since 4.x) in today's guest: a one-page PDF to memory, read back by pypdf."""
import sys, zipfile
from pathlib import Path
from wasi_python import Artifacts, artifacts, run
P, OUT = Path(sys.argv[1]), Path(sys.argv[2])
base = artifacts()
z2 = OUT / "python-stdlib-reportlab.zip"
with zipfile.ZipFile(OUT / "guest" / "python-stdlib-ext.zip") as z:
    have = {i.filename: (i, z.read(i)) for i in z.infolist()}
with zipfile.ZipFile(P / "zips" / "reportlab.zip") as z:
    for i in z.infolist():
        have.setdefault(i.filename, (i, z.read(i)))
with zipfile.ZipFile(z2, "w") as z:
    for n in sorted(have):
        z.writestr(have[n][0], have[n][1], compresslevel=9)
a = Artifacts(snapshot=base.snapshot, plain=base.plain, stdlib_zip=z2, manifest=base.manifest)
code = """
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
b = io.BytesIO(); c = canvas.Canvas(b, pagesize=A4); c.drawString(72, 720, "Hello agent"); c.save()
import pypdf; print(pypdf.PdfReader(io.BytesIO(b.getvalue())).pages[0].extract_text())
"""
r = run(["-c", code], artifacts=a, snapshot=False, fuel=10**13, deadline_s=1800, cache_dir=False)
print(r.exit_code, r.fuel_used, r.stdout.decode().strip(), r.stderr.decode().strip().splitlines()[-1:] )
