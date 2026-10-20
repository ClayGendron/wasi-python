"""Golden job: PDF reports with reportlab (spec 042, Decision 10).

Usage: pdf_reports.py <data dir> <out dir>. It reads sales.csv from the data dir; the out dir stays
empty. Everything is built in memory, as a call with nothing writable can.

A PDF's bytes are printed (length and SHA-256) only when it is built with `invariant=1`, which
drops the time and the random document id, and `pageCompression=0`, since a deflated stream's
bytes depend on the zlib that wrote it; a compressed PDF is printed only as pypdf reads it back.
- a two-page canvas letter in the three standard font families, with a line, a filled rectangle,
  a circle, a link, a title and an author; the same letter compressed; one `stringWidth`;
- a platypus report of sales.csv grouped by region: a title, a paragraph with markup, a table
  with a grid and a coloured header, a bulleted list, a page break, a long paragraph, and a footer
  with page numbers;
- charts as drawings: a bar chart and a line chart on one drawing, through renderPDF and
  renderSVG, a pie chart through renderSVG, and renderPM's error (it needs rlPyCairo, a Cairo
  binding that is not carried);
- Unicode text in DejaVu Sans, a TrueType file from matplotlib's data (reportlab's own fonts are
  not shipped);
- a matplotlib figure drawn through `ImageReader`: the image's size and the PDF image object's
  /Width and /Height, not its bytes (reportlab deflates the pixels).
No barcode and no QR code: reportlab's barcode folder is not shipped yet (Decision 4a).
"""

import csv
import hashlib
import io
import math
import os
import sys
from importlib.metadata import version

import matplotlib

matplotlib.use("agg")
import matplotlib.pyplot as plt  # noqa: E402
import pypdf  # noqa: E402
from reportlab.graphics import renderPDF, renderPM, renderSVG  # noqa: E402
from reportlab.graphics.charts.barcharts import VerticalBarChart  # noqa: E402
from reportlab.graphics.charts.linecharts import HorizontalLineChart  # noqa: E402
from reportlab.graphics.charts.piecharts import Pie  # noqa: E402
from reportlab.graphics.shapes import Drawing, String  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4, letter  # noqa: E402
from reportlab.lib.styles import getSampleStyleSheet  # noqa: E402
from reportlab.lib.utils import ImageReader  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

data_dir, out_dir = sys.argv[1], sys.argv[2]
print(
    "versions",
    *(f"{name}={version(name)}" for name in ("reportlab", "pypdf", "matplotlib", "pillow")),
)
SAME = {"invariant": 1, "pageCompression": 0}


def sha(data: bytes | str) -> str:
    """The SHA-256 of bytes, or of a text as UTF-8 (renderSVG returns a str)."""
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def read_back(data: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(data))
    meta = reader.metadata
    texts = [page.extract_text() for page in reader.pages]
    return f"pages {len(reader.pages)} title {meta.title!r} author {meta.author!r} text {texts!r}"


def letter_pdf(**kw) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, **kw)
    c.setTitle("A letter from the guest")
    c.setAuthor("wasi_python")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 720, "Quarterly sales")
    c.setFont("Times-Roman", 12)
    c.drawString(72, 696, "Dear reader, the figures are below.")
    c.setFont("Courier", 10)
    c.drawString(72, 680, "total = 1234.50")
    c.setLineWidth(1.5)
    c.line(72, 670, 540, 670)
    c.setFillColor(colors.HexColor("#4c72b0"))
    c.rect(72, 560, 120, 80, stroke=1, fill=1)
    c.setFillColor(colors.HexColor("#dd8452"))
    c.circle(300, 600, 40, stroke=1, fill=1)
    c.setFillColor(colors.black)
    c.drawString(72, 530, "See example.org")
    c.linkURL("https://example.org/", (72, 525, 200, 542), relative=0)
    c.showPage()
    c.setFont("Times-Roman", 12)
    c.drawString(72, 720, "Page two: yours sincerely.")
    c.showPage()
    c.save()
    return buf.getvalue()


plain = letter_pdf(**SAME)
print("letter", len(plain), sha(plain))
print("letter read", read_back(plain))
print("letter compressed read", read_back(letter_pdf(invariant=1)))
width = pdfmetrics.stringWidth("Quarterly sales", "Helvetica-Bold", 18)
print("stringWidth", format(width, ".6g"))

with open(os.path.join(data_dir, "sales.csv"), newline="") as f:
    rows = list(csv.DictReader(f))
regions = sorted({r["region"] for r in rows})
months = sorted({int(r["month"]) for r in rows})
by_region = {g: [float(r["sales"]) for r in rows if r["region"] == g] for g in regions}
totals = {g: math.fsum(v) for g, v in by_region.items()}

styles = getSampleStyleSheet()
table = [["region", "months", "total", "mean"]]
table += [
    [g, str(len(v)), f"{totals[g]:.2f}", f"{totals[g] / len(v):.2f}"] for g, v in by_region.items()
]
grid = Table(table)
grid.setStyle(
    TableStyle(
        [
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4c72b0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ]
    )
)
story = [
    Paragraph("Sales by region", styles["Title"]),
    Paragraph(
        'Totals are <b>summed</b> over <i>every</i> month, in <font color="#dd8452">euros</font>.',
        styles["Normal"],
    ),
    Spacer(1, 12),
    grid,
    Spacer(1, 12),
    ListFlowable(
        [
            ListItem(Paragraph(f"{g}: best month {max(v):.2f}", styles["Normal"]))
            for g, v in by_region.items()
        ],
        bulletType="bullet",
    ),
    PageBreak(),
    Paragraph(
        " ".join(["The second page holds a long paragraph that wraps."] * 12), styles["BodyText"]
    ),
]


def footer(c, doc) -> None:
    c.setFont("Helvetica", 8)
    c.drawRightString(A4[0] - 72, 36, f"Page {doc.page}")


buf = io.BytesIO()
doc = SimpleDocTemplate(buf, pagesize=A4, title="Sales report", author="wasi_python", **SAME)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
report = buf.getvalue()
print("report", len(report), sha(report), read_back(report))

charts = Drawing(400, 360)
bars = VerticalBarChart()
bars.x, bars.y, bars.width, bars.height = 50, 200, 300, 130
bars.data = [[totals[g] for g in regions]]
bars.categoryAxis.categoryNames = regions
bars.valueAxis.valueMin = 0
bars.bars[0].fillColor = colors.HexColor("#4c72b0")
charts.add(bars)
lines = HorizontalLineChart()
lines.x, lines.y, lines.width, lines.height = 50, 30, 300, 130
lines.data = [
    [
        next(float(r["sales"]) for r in rows if r["region"] == g and int(r["month"]) == m)
        for m in months
    ]
    for g in regions
]
lines.categoryAxis.categoryNames = [str(m) for m in months]
charts.add(lines)
charts.add(String(200, 345, "Sales", textAnchor="middle"))
print(
    "charts pdf",
    sha(renderPDF.drawToString(charts, **SAME)),
    "svg",
    sha(renderSVG.drawToString(charts)),
)
pie = Drawing(200, 200)
wedges = Pie()
wedges.x, wedges.y, wedges.width, wedges.height = 25, 25, 150, 150
wedges.data = [totals[g] for g in regions]
wedges.labels = regions
pie.add(wedges)
print("pie svg", sha(renderSVG.drawToString(pie)))
try:
    renderPM.drawToString(pie, fmt="PNG")
    print("renderPM drew")
except Exception as e:
    print("renderPM", type(e).__name__, str(e).splitlines()[0])

dejavu = os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSans.ttf")
pdfmetrics.registerFont(TTFont("DejaVuSans", dejavu))
buf = io.BytesIO()
c = canvas.Canvas(buf, pagesize=(400, 120), **SAME)
c.setTitle("Unicode")
c.setAuthor("wasi_python")
c.setFont("DejaVuSans", 14)
c.drawString(20, 60, "Grüße, naïve café: Σ x² ≤ 10 €")
c.showPage()
c.save()
unicode_pdf = buf.getvalue()
print("unicode", len(unicode_pdf), sha(unicode_pdf), read_back(unicode_pdf))

fig, ax = plt.subplots(figsize=(3, 2), dpi=50)
ax.plot([1, 2, 3], [2, 1, 3])
png = io.BytesIO()
fig.savefig(png, format="png")
plt.close(fig)
png.seek(0)
image = ImageReader(png)
buf = io.BytesIO()
c = canvas.Canvas(buf, pagesize=(300, 200), **SAME)
c.drawImage(image, 50, 50, width=150, height=100)
c.showPage()
c.save()
xobjects = pypdf.PdfReader(io.BytesIO(buf.getvalue())).pages[0]["/Resources"]["/XObject"]
images = [o.get_object() for o in xobjects.values()]
sizes = sorted((int(o["/Width"]), int(o["/Height"])) for o in images if o["/Subtype"] == "/Image")
print("image", image.getSize(), sizes)
