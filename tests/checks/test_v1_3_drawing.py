"""v1.3: drawing through cairo. cairocffi binds the cairo linked into the binary, its toy font
API draws matplotlib's DejaVu faces rather than cairo's built-in stroke font, and what the guest
cannot do fails by name: a PostScript surface, a callback pool past its size, a call through a C
function pointer. A program can still import a CairoSVG of its own ahead of the zip's."""

from __future__ import annotations

import pytest

from harness import jobs

pytestmark = pytest.mark.goal("v1.3")

BINARY = pytest.mark.parametrize("which", ["plain", "snapshot"])

# Each family drawn through select_font_face, against a face made directly from the DejaVu file
# the font map should choose, and against cairo's own face of the same family (`@cairo:`), which
# is the stroke font cairo draws without fontconfig.
TEXT = """
import hashlib, importlib.util, os
import cairocffi as cairo
import _cairocffi_api
api = _cairocffi_api
ttf = os.path.join(list(importlib.util.find_spec("matplotlib").submodule_search_locations)[0],
                   "mpl-data", "fonts", "ttf")
keep = []

def explicit(name):
    data = open(os.path.join(ttf, name), "rb").read()
    buf = api.ffi.new("unsigned char[]", data)
    keep.append(buf)
    face = cairo.FontFace._from_pointer(
        api.lib.wasi_cairo_ft_face_from_memory(buf, len(data), 0), incref=False)
    return lambda c: c.set_font_face(face)

def draw(set_font):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, 120, 60)
    c = cairo.Context(s)
    c.set_source_rgb(1, 1, 1)
    c.paint()
    c.set_source_rgb(0, 0, 0)
    set_font(c)
    c.set_font_size(40)
    c.move_to(4, 46)
    c.show_text("Hg")
    s.flush()
    return hashlib.sha256(bytes(s.get_data())).hexdigest()

N, I, B = cairo.FONT_SLANT_NORMAL, cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_BOLD
W = cairo.FONT_WEIGHT_NORMAL
for family, slant, weight, file in [
    ("sans-serif", N, W, "DejaVuSans.ttf"),
    ("serif", N, B, "DejaVuSerif-Bold.ttf"),
    ("monospace", I, W, "DejaVuSansMono-Oblique.ttf"),
]:
    mapped = draw(lambda c: c.select_font_face(family, slant, weight))
    own = draw(lambda c: c.select_font_face("@cairo:" + family, slant, weight))
    print(family, mapped == draw(explicit(file)), mapped != own)
"""


@BINARY
def test_cairo_text_is_drawn_in_dejavu(guest, which) -> None:
    """ "Hg" at 40 px through `select_font_face` with a generic family is, pixel for pixel, the
    same text drawn with the DejaVu face made directly from the file the map names (Sans, Serif
    Bold, Sans Mono Oblique), and differs from cairo's own face of that family, the stroke font it
    draws without fontconfig: so the check cannot pass with both sides in the stroke font."""
    r = guest(which, ["-c", TEXT], mpl_data=True)
    assert r.exit_code == 0, r.describe()
    assert r.text == "sans-serif True True\nserif True True\nmonospace True True\n", r.text


LIMITS = """
import array, gc, io
import cairocffi as cairo

try:
    cairo.PSSurface(io.BytesIO(), 10, 10)
except OSError as e:
    print("ps", type(e).__name__, "temporary file" in str(e))

def fill(make):
    live = [make() for _ in range(128)]
    try:
        make()
    except MemoryError as e:
        print("pool full:", e)
    del live
    gc.collect()
    print("again", type(make()).__name__)

fill(lambda: cairo.SVGSurface(io.BytesIO(), 10, 10))
fill(lambda: cairo.ImageSurface(cairo.FORMAT_ARGB32, 2, 2, data=array.array("B", bytes(16))))
"""
FULL = "pool full: 128 {} callbacks are alive, the most this build of cairocffi has\n"
LIMITS_OUT = (
    "ps OSError True\n"
    + FULL.format("cairo_write_func_t")
    + "again SVGSurface\n"
    + FULL.format("cairo_destroy_func_t")
    + "again ImageSurface\n"
)
# A call through a C function pointer, which only cffi's ABI mode makes: the stand-in for libffi
# has no way to make it, and stops the instance.
POINTER_CALL = """
import _cairocffi_api as api
f = api.ffi.cast("void(*)(void *)", api.ffi.addressof(api.lib, "_wasi_cairo_destroy_0"))
print("calling", flush=True)
f(api.ffi.NULL)
print("returned")
"""
MINE = "WHICH = 'mine'\n"
REPLACE = """
import sys
sys.path.remove("/mine")
sys.path.insert(0, "/mine")
import cairosvg
print(cairosvg.WHICH, cairosvg.__file__)
"""


@BINARY
def test_cairo_names_what_it_cannot_do(guest, which) -> None:
    """A PostScript surface raises cairo's temporary-file error (the guest has no tmpfile); the
    129th live stream surface and the 129th ImageSurface over a buffer each raise MemoryError
    naming the pool, and a new one works once the others are dropped; a call through a C function
    pointer traps, and a new instance runs; and a CairoSVG in a folder the program moves ahead of
    the zip on sys.path is the one imported."""
    r = guest(which, ["-c", LIMITS])
    assert r.exit_code == 0, r.describe()
    assert r.text == LIMITS_OUT, r.text
    r = guest(which, ["-c", POINTER_CALL])
    assert r.trapped is not None and r.stdout == b"calling\n", r.describe()
    r = guest(which, ["-c", "import cairocffi; print(cairocffi.cairo_version_string())"])
    assert (r.exit_code, r.text) == (0, "1.18.6\n"), r.describe()
    r = guest(
        which,
        ["-c", "import sys; sys.path.append('/mine')\n" + REPLACE],
        files={"/mine/cairosvg/__init__.py": MINE},
    )
    assert (r.exit_code, r.text) == (0, "mine /mine/cairosvg/__init__.py\n"), r.describe()


@pytest.mark.slow
@BINARY
def test_svg_to_png_job_matches_native(guest, which) -> None:
    """CairoSVG's PNGs of a drawing, of text in every mapped family and of gradients, a clip, a
    mask, dashes, markers and an embedded PNG; cairocffi's own drawing and a PNG round trip; and a
    PDF's pages, media box and text: every line equals the oracle's, run on a native cairo built
    from the same pins with the same Python (recorded on the platform tests/jobs/svg_to_png.platform
    names). Each image line holds its RGBA pixels' SHA-256, so the pixels are native's exactly."""
    job = "svg_to_png"
    out = jobs.run_in_guest(guest, job, mpl_data=True)
    why = jobs.compare(jobs.expected_path(job).read_bytes(), out)
    assert why is None, why
