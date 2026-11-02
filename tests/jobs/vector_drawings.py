"""Golden job: drawsvg's vector drawings and animations, as SVG and HTML.

Usage: vector_drawings.py <data dir> <out dir>. drawsvg is pure Python and ships no tests, so equal
output holds the guest's interpreter to native Python's on drawsvg's own code: it says the two
agree, not that the SVG drawsvg writes is right. Each line prints a text's length and SHA-256:

- the README drawing (lines, shapes, a path, text on a path, arcs, a marker, a gradient) through
  `as_svg()`, and `save_svg` read back; through `as_html()`, and `save_html` read back;
- the rich display's SVG, whose element ids drawsvg randomizes, after seeding `random`;
- a native SVG animation with its playback controls, a circle with three key frames and a text
  sequence, through `as_svg()` and `as_html()`;
- a frame animation with a callback: its frame and callback counts and each frame's SVG;
- a drawing of 1,000 circles;
- an image embedded from the data folder (the file read, base64, its MIME type from the suffix),
  and a drawing with a group, a `use`, a clip path and a mask.

Each saved file is removed after it is read back, so the output folder ends empty.
"""

import base64
import hashlib
import os
import random
import sys
from importlib.metadata import version

import drawsvg as draw

data_dir, out_dir = sys.argv[1], sys.argv[2]
print("versions", f"drawsvg={version('drawsvg')}")


def show(name: str, text: str) -> None:
    data = text.encode()
    print(name, len(data), hashlib.sha256(data).hexdigest())


def saved(name: str, save) -> str:
    """Save through drawsvg, read the file back and remove it."""
    path = os.path.join(out_dir, name)
    save(path)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    os.remove(path)
    return text


# 1. The README drawing
d = draw.Drawing(200, 100, origin="center")
d.append(
    draw.Lines(-80, 45, 70, 49, 95, -49, -90, -40, close=False, fill="#eeee00", stroke="black")
)
r = draw.Rectangle(-80, -50, 40, 50, fill="#1248ff")
r.append_title("Our first rectangle")
d.append(r)
d.append(draw.Circle(-40, 10, 30, fill="red", stroke_width=2, stroke="black"))
p = draw.Path(stroke_width=2, stroke="lime", fill="black", fill_opacity=0.2)
p.M(-10, -20).C(30, 10, 30, -50, 70, -20)
d.append(p)
d.append(draw.Text("Basic text", 8, -10, -35, fill="blue"))
d.append(draw.Text("Path text", 8, path=p, text_anchor="start", line_height=1))
d.append(draw.Text(["Multi-line", "text"], 8, path=p, text_anchor="end", center=True))
d.append(
    draw.ArcLine(60, 20, 20, 60, 270, stroke="red", stroke_width=5, fill="red", fill_opacity=0.2)
)
d.append(draw.Arc(60, 20, 20, 60, 270, cw=False, stroke="green", stroke_width=3, fill="none"))
arrow = draw.Marker(-0.1, -0.51, 0.9, 0.5, scale=4, orient="auto")
arrow.append(draw.Lines(-0.1, 0.5, -0.1, -0.5, 0.9, 0, fill="red", close=True))
q = draw.Path(stroke="red", stroke_width=2, fill="none", marker_end=arrow)
q.M(20, 40).L(20, 27).L(0, 20)
d.append(q)
d.append(draw.Line(30, 20, 0, 10, stroke="red", stroke_width=2, fill="none", marker_end=arrow))
g = draw.LinearGradient(-50, -50, 50, 50)
g.add_stop(0, "green")
g.add_stop(1, "red", 0.5)
d.append(draw.Rectangle(40, -45, 30, 30, fill=g))
d.set_pixel_scale(2)
svg = d.as_svg()
show("readme svg", svg)
print("readme save_svg equal", saved("readme.svg", d.save_svg) == svg)
html = d.as_html()
show("readme html", html)
print("readme save_html equal", saved("readme.html", d.save_html) == html)

# 2. The rich display, its element ids drawn from `random`
random.seed(0)
show("readme repr_svg", d._repr_svg_())

# 3. A native SVG animation with playback controls
config = draw.types.SyncedAnimationConfig(
    duration=8, show_playback_progress=True, show_playback_controls=True
)
a = draw.Drawing(200, 200, origin="center", animation_config=config)
c = draw.Circle(0, 0, 0, fill="gray")
c.add_key_frame(0, cx=-100, cy=0, r=0)
c.add_key_frame(2, cx=0, cy=-100, r=40)
c.add_key_frame(8, cx=-100, cy=0, r=0)
a.append(c)
draw.native_animation.animate_text_sequence(
    a, [0, 2, 4, 6, 8], ["0", "1", "2", "3", "4"], 30, 0, 0, fill="black", center=True
)
show("animation svg", a.as_svg())
show("animation html", a.as_html())

# 4. A frame animation with a callback
seen = []


def frame(i: int):
    f = draw.Drawing(50, 50)
    f.append(draw.Circle(25, 25, 5 + 5 * i, fill="none", stroke="black"))
    f.append(draw.Text(f"frame {i}", 6, 4, 10))
    return f


anim = draw.FrameAnimation(frame, callback=seen.append)
for i in range(3):
    anim.draw_frame(i)
print("frames", len(anim.frames), "callbacks", len(seen), "same", seen == anim.frames)
for i, f in enumerate(anim.frames):
    show(f"frame {i} svg", f.as_svg())

# 5. Scale: 1,000 circles
big = draw.Drawing(400, 400)
for i in range(1000):
    big.append(draw.Circle((i * 37) % 400, (i * 91) % 400, 1 + i % 9, fill=f"#{i % 256:02x}4080"))
show("circles svg", big.as_svg())

# 6. An embedded image, and a group, a use, a clip path and a mask
png = os.path.join(data_dir, "swatch.png")
with open(png, "rb") as f:
    raw = f.read()
image = draw.Image(10, 10, 40, 40, path=png, embed=True)
head, _, body = image.args["xlink:href"].partition(",")
print("swatch bytes", len(raw), "uri", head, "decodes equal", base64.b64decode(body) == raw)
e = draw.Drawing(100, 100)
e.append(image)
e.append(draw.Image(50, 50, 40, 40, path="swatch.png"))
show("image svg", e.as_svg())
s = draw.Drawing(120, 120)
clip = draw.ClipPath()
clip.append(draw.Circle(60, 60, 40))
mask = draw.Mask()
mask.append(draw.Rectangle(0, 0, 120, 60, fill="white"))
group = draw.Group(id="pair", fill="teal", clip_path=clip)
group.append(draw.Rectangle(10, 10, 40, 40))
group.append(draw.Circle(80, 80, 20))
s.append(group)
s.append(draw.Use(group, 20, 0, mask=mask))
s.append(draw.Use("pair", 0, 20, fill="orange"))
show("structure svg", s.as_svg())
