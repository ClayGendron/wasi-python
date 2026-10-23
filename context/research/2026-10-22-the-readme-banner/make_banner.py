"""Render a line of text in IBM Plex Sans as SVG outlines (no font load at view time)."""
import sys
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

font_path, text, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
size = float(sys.argv[4]) if len(sys.argv) > 4 else 120.0
tracking = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0  # em units per 1000

tt = TTFont(font_path)
upem = tt["head"].unitsPerEm
scale = size / upem
glyphset = tt.getGlyphSet()
order = tt.getGlyphOrder()

blob = hb.Blob.from_file_path(font_path)
face = hb.Face(blob)
hbfont = hb.Font(face)
buf = hb.Buffer()
buf.add_str(text)
buf.guess_segment_properties()
hb.shape(hbfont, buf, {"kern": True, "liga": True})

x = 0.0
paths = []
for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
    name = order[info.codepoint]
    pen = SVGPathPen(glyphset)
    # flip y, scale to px, place at pen position
    tpen = TransformPen(pen, (scale, 0, 0, -scale, (x + pos.x_offset) * scale, pos.y_offset * scale))
    glyphset[name].draw(tpen)
    d = pen.getCommands()
    if d:
        paths.append(d)
    x += pos.x_advance + tracking

width = x * scale
asc = tt["hhea"].ascent * scale
desc = -tt["hhea"].descent * scale
cap = tt["OS/2"].sCapHeight * scale if hasattr(tt["OS/2"], "sCapHeight") else asc
pad = size * 0.35
W = width + 2 * pad
H = cap + 2 * pad
# baseline sits at pad + cap
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.1f} {H:.1f}" width="{W:.0f}" height="{H:.0f}" role="img" aria-label="{text}">
  <title>{text}</title>
  <style>
    .t {{ fill: #1f2328; }}
    @media (prefers-color-scheme: dark) {{ .t {{ fill: #f0f6fc; }} }}
  </style>
  <g class="t" transform="translate({pad:.1f} {pad + cap:.1f})">
    {"".join(f'<path d="{d}"/>' for d in paths)}
  </g>
</svg>
'''
out.write_text(svg)
print(out, f"{W:.0f}x{H:.0f}", len(paths), "glyphs")
