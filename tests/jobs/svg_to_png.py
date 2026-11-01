"""Golden job: SVG to PNG and PDF through cairo, and cairo drawn directly through cairocffi.

Usage: svg_to_png.py <data dir> <out dir> (both unused). Each image is printed as its size and the
SHA-256 of its RGBA pixels, decoded by Pillow, so the line holds for every PNG encoder that writes
the same pixels; the PNG files' own bytes are the same-bytes gate's. CairoSVG draws a drawing with
lines, shapes, a path, text on a path, an arc, a marker and a gradient; text in the generic
families and three DejaVu names, bold and italic, at 12 and 40 px; gradients, opacity, a clip, a
mask, dashes, markers and an embedded PNG. cairocffi draws arcs, curves and a radial gradient, and
writes a PNG to a stream and reads it back. `svg2pdf` writes a PDF, whose page count, media box
and text pypdf reads. Text is drawn through cairo's toy font API, which in this build draws
matplotlib's DejaVu faces; natively the same map runs over the same files.
"""

import hashlib
import io
from importlib.metadata import version

import cairocffi as cairo
import cairosvg
import pypdf
from PIL import Image

print(
    "versions",
    f"cairosvg={version('cairosvg')}",
    f"cairocffi={version('cairocffi')}",
    f"cairo={cairo.cairo_version_string()}",
)


def show(name: str, png: bytes) -> None:
    """One image's line: its size, mode and the SHA-256 of its RGBA pixels."""
    image = Image.open(io.BytesIO(png))
    rgba = image.convert("RGBA")
    digest = hashlib.sha256(rgba.tobytes()).hexdigest()
    print(f"{name} {image.size[0]}x{image.size[1]} {image.mode} {digest}")


DRAWING = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
 width="400" height="200" viewBox="-200 -100 400 200">
<defs>
 <linearGradient id="g" x1="-150" y1="0" x2="150" y2="0" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#ff0000" stop-opacity="0.8"/>
  <stop offset="1" stop-color="#0000ff" stop-opacity="0.6"/>
 </linearGradient>
 <marker id="arrow" viewBox="-0.1 -0.5 1.0 1.0" markerWidth="4" markerHeight="4"
  refX="0" refY="0" orient="auto"><path d="M-0.1,0.5 L-0.1,-0.5 L0.9,0 Z" fill="red"/></marker>
 <path id="curve" d="M-150,40 C-50,-40 50,90 150,10"/>
</defs>
<polygon points="-185,-45 -165,-75 -145,-45" fill="#eeee00" stroke="black"/>
<rect x="-80" y="-80" width="100" height="40" fill="#1248ff" rx="8"/>
<circle cx="-40" cy="20" r="30" fill="url(#g)" stroke="red" stroke-width="2"/>
<path d="M-180,90 C-150,50 -110,50 -80,90" fill="none" stroke="green" stroke-width="3"
 marker-end="url(#arrow)"/>
<path d="M60,-70 A40,40 0 1,1 140,-70" fill="none" stroke="purple" stroke-width="4"/>
<text font-size="16" fill="#204" font-family="sans-serif">
 <textPath xlink:href="#curve">Text along a curve, in DejaVu Sans</textPath></text>
<text x="60" y="80" font-size="28" font-family="serif" text-anchor="middle">Basic text</text>
</svg>"""
show("drawing", cairosvg.svg2png(bytestring=DRAWING.encode()))

FAMILIES = [
    "sans-serif", "serif", "monospace", "DejaVu Sans", "DejaVu Serif", "DejaVu Sans Mono",
]  # fmt: skip
rows = []
y = 0
for family in FAMILIES:
    for size in (12, 40):
        for style in ("", 'font-weight="bold"', 'font-style="italic"'):
            y += size + 6
            rows.append(
                f'<text x="4" y="{y}" font-family="{family}" font-size="{size}" {style}>'
                f"Hg {family}</text>"
            )
TEXT = (
    f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="{y + 10}">'
    '<rect width="100%" height="100%" fill="white"/>' + "".join(rows) + "</svg>"
)
show("text", cairosvg.svg2png(bytestring=TEXT.encode()))

# A 4x4 PNG with a gradient of colours, embedded as data: cairo decodes it through libpng.
tile = Image.new("RGBA", (4, 4))
tile.putdata([(r * 60, g * 60, 200, 255) for r in range(4) for g in range(4)])
buffer = io.BytesIO()
tile.save(buffer, format="PNG")
import base64  # noqa: E402

TILE = base64.b64encode(buffer.getvalue()).decode()
EFFECTS = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
 width="320" height="240">
<defs>
 <radialGradient id="r" cx="0.5" cy="0.5" r="0.5" fx="0.3" fy="0.3">
  <stop offset="0" stop-color="white"/><stop offset="0.6" stop-color="orange"/>
  <stop offset="1" stop-color="darkred"/></radialGradient>
 <linearGradient id="l" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="#0a0"/><stop offset="1" stop-color="#00a" stop-opacity="0.2"/>
 </linearGradient>
 <clipPath id="c"><circle cx="240" cy="60" r="45"/></clipPath>
 <mask id="m"><rect x="10" y="130" width="140" height="100" fill="white"/>
  <circle cx="80" cy="180" r="30" fill="black"/></mask>
 <marker id="dot" markerWidth="6" markerHeight="6" refX="3" refY="3">
  <circle cx="3" cy="3" r="2.5" fill="crimson"/></marker>
</defs>
<rect x="10" y="10" width="140" height="100" fill="url(#r)"/>
<rect x="180" y="0" width="140" height="120" fill="url(#l)" clip-path="url(#c)"/>
<rect x="10" y="130" width="140" height="100" fill="teal" mask="url(#m)" opacity="0.7"/>
<polyline points="170,140 200,220 230,150 260,215 300,145" fill="none" stroke="black"
 stroke-width="3" stroke-dasharray="9 4 2 4" stroke-linejoin="round"
 marker-start="url(#dot)" marker-mid="url(#dot)" marker-end="url(#dot)"/>
<image x="250" y="90" width="48" height="48" xlink:href="data:image/png;base64,{TILE}"
 style="image-rendering:optimizeSpeed"/>
<circle cx="60" cy="60" r="25" fill="blue" fill-opacity="0.4" stroke="navy" stroke-opacity="0.5"/>
</svg>"""
show("effects", cairosvg.svg2png(bytestring=EFFECTS.encode()))
show("effects-x2", cairosvg.svg2png(bytestring=EFFECTS.encode(), scale=2))

# cairocffi directly.
surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 160)
ctx = cairo.Context(surface)
ctx.set_source_rgb(1, 1, 1)
ctx.paint()
gradient = cairo.RadialGradient(70, 60, 5, 80, 80, 70)
gradient.add_color_stop_rgba(0, 1, 1, 0.8, 1)
gradient.add_color_stop_rgba(1, 0.1, 0.3, 0.6, 1)
ctx.set_source(gradient)
ctx.arc(80, 80, 70, 0, 2 * 3.141592653589793)
ctx.fill()
ctx.set_source_rgba(0.8, 0.1, 0.1, 0.7)
ctx.set_line_width(5)
ctx.move_to(10, 150)
ctx.curve_to(60, 10, 140, 10, 190, 150)
ctx.stroke()
ctx.set_source_rgb(0, 0, 0)
ctx.arc_negative(150, 40, 25, 0.5, 4.0)
ctx.set_line_width(2)
ctx.stroke()
stream = io.BytesIO()
surface.write_to_png(stream)
show("cairocffi", stream.getvalue())
back = cairo.ImageSurface.create_from_png(io.BytesIO(stream.getvalue()))
print(
    "round trip",
    back.get_width(),
    back.get_height(),
    bytes(back.get_data()) == bytes(surface.get_data()),
)

# A PDF of the drawing, read back.
pdf = cairosvg.svg2pdf(bytestring=DRAWING.encode())
reader = pypdf.PdfReader(io.BytesIO(pdf))
page = reader.pages[0]
print("pdf pages", len(reader.pages), "mediabox", [float(v) for v in page.mediabox])
print("pdf text", repr(" ".join(page.extract_text().split())))
