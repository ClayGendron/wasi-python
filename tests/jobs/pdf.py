"""Golden job: PDF files with pypdf (spec 039, Decisions 9 and 11).

Usage: pdf.py <data dir> <out dir> (both unused). The job writes two small PDFs itself (a few
lines of PDF syntax, Helvetica, no compression), extracts their text, merges them with a title,
and shows the merged file's length and SHA-256 (pypdf compresses nothing here, so its bytes do not
depend on zlib). RC4-128 encryption round-trips; AES-128 needs `cryptography`, which the profile
does not carry, and raises pypdf's DependencyError.
"""

import hashlib
import io
from importlib.metadata import version

import pypdf

print("versions", f"pypdf={version('pypdf')}")

PAGE = (
    b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R"
    b" /Resources << /Font << /F1 5 0 R >> >> >>"
)


def tiny_pdf(lines):
    shown = b" ".join(b"(" + s.encode() + b") '" for s in lines)
    content = b"BT /F1 14 Tf 20 120 Td 16 TL " + shown + b" ET"
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        PAGE,
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for o in offsets:
        out += b"%010d 00000 n \n" % o
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


a = tiny_pdf(["Invoice 17", "Total: 42.50 EUR"])
b = tiny_pdf(["Page two"])
r = pypdf.PdfReader(io.BytesIO(a))
print(len(r.pages), repr(r.pages[0].extract_text()))

w = pypdf.PdfWriter()
for src in (a, b):
    w.append(io.BytesIO(src))
w.add_metadata({"/Title": "merged"})
merged = io.BytesIO()
w.write(merged)
m = pypdf.PdfReader(io.BytesIO(merged.getvalue()))
print(len(m.pages), m.metadata.title, [p.extract_text() for p in m.pages])
print("written", len(merged.getvalue()), hashlib.sha256(merged.getvalue()).hexdigest()[:16])

for algorithm in ("RC4-128", "AES-128"):
    w2 = pypdf.PdfWriter()
    w2.append(io.BytesIO(a))
    try:
        w2.encrypt("pw", algorithm=algorithm)
        locked = io.BytesIO()
        w2.write(locked)
        r2 = pypdf.PdfReader(io.BytesIO(locked.getvalue()))
        result = r2.decrypt("pw")
        print(algorithm, r2.is_encrypted, result.name, r2.pages[0].extract_text().splitlines()[0])
    except pypdf.errors.DependencyError as e:
        print(algorithm, "DependencyError", e)
