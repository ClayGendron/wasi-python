"""Golden job: tables and text from PDF files with pdfplumber and pdfminer.six.

Usage: pdf_tables.py <data dir> <out dir> (both unused). reportlab draws a two-page report in
memory: a title, a ruled table of eight rows on each page, and a footer. It is built with
`invariant=1` and `pageCompression=0`, so its bytes are printed (length and SHA-256). pdfplumber
reads it back: each page's text, its words with their boxes rounded to a hundredth of a point,
its ruling lines, and `extract_tables()`. Then pypdf encrypts the report with RC4-128 and a
password, and pdfplumber opens the locked file with that password, which pdfminer decrypts in pure
Python. AES needs `cryptography`, which the profile does not carry; the guest's own checks call
it.
"""

import hashlib
import io
from importlib.metadata import version

import pdfplumber
import pypdf
from reportlab.lib.pagesizes import A5
from reportlab.pdfgen import canvas

print(
    "versions",
    f"pdfplumber={version('pdfplumber')}",
    f"pdfminer.six={version('pdfminer.six')}",
    f"reportlab={version('reportlab')}",
)

ROWS = [
    ("North", "Widgets", 12, 30.5),
    ("North", "Gadgets", 7, 12.25),
    ("South", "Widgets", 3, 7.0),
    ("South", "Gizmos", 21, 63.75),
    ("East", "Gadgets", 9, 18.0),
    ("East", "Gizmos", 4, 11.5),
    ("West", "Widgets", 15, 37.5),
    ("West", "Gadgets", 2, 4.5),
]
HEADER = ("Region", "Product", "Units", "Total")
COLUMNS = (40, 130, 230, 300, 380)  # the table's vertical rules, in points
ROW_HEIGHT = 22


def table(c, top, rows):
    """A ruled table: a header row, then one row per record, every cell boxed."""
    lines = [HEADER] + [(r, p, str(u), f"{t:.2f}") for r, p, u, t in rows]
    bottom = top - ROW_HEIGHT * len(lines)
    for i in range(len(lines) + 1):
        y = top - ROW_HEIGHT * i
        c.line(COLUMNS[0], y, COLUMNS[-1], y)
    for x in COLUMNS:
        c.line(x, top, x, bottom)
    for i, cells in enumerate(lines):
        c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", 10)
        y = top - ROW_HEIGHT * i - 15
        for x, text in zip(COLUMNS[:-1], cells, strict=True):
            c.drawString(x + 5, y, text)


def report():
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A5, invariant=1, pageCompression=0)
    c.setTitle("Quarterly units")
    for page, rows in enumerate((ROWS, list(reversed(ROWS))), 1):
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, 540, f"Quarterly units, part {page}")
        table(c, 500, rows)
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(40, 40, f"Page {page} of 2")
        c.showPage()
    c.save()
    return buf.getvalue()


def show(pdf):
    for page in pdf.pages:
        print("page", page.page_number, page.width, page.height)
        print(page.extract_text())
        words = page.extract_words()
        print("words", len(words))
        for w in words[:6]:
            print(" ", w["text"], [round(w[k], 2) for k in ("x0", "top", "x1", "bottom")])
        print("lines", len(page.lines), "rects", len(page.rects))
        for t in page.extract_tables():
            for row in t:
                print(" ", row)


data = report()
print("report", len(data), hashlib.sha256(data).hexdigest()[:16])
with pdfplumber.open(io.BytesIO(data)) as pdf:
    print("pages", len(pdf.pages), pdf.metadata.get("Title"))
    show(pdf)
    print(pdf.pages[0].crop((40, 60, 230, 160)).extract_text())

writer = pypdf.PdfWriter()
writer.append(io.BytesIO(data))
writer.encrypt("pw", algorithm="RC4-128")
locked = io.BytesIO()
writer.write(locked)
with pdfplumber.open(io.BytesIO(locked.getvalue()), password="pw") as pdf:
    first = pdf.pages[0]
    print("RC4-128", len(pdf.pages), first.extract_text().splitlines()[0])
    print(first.extract_tables()[0][1])
try:
    with pdfplumber.open(io.BytesIO(locked.getvalue()), password="wrong") as pdf:
        print("opened", len(pdf.pages))
except Exception as e:
    print("wrong password", type(e).__name__)
