"""Golden job: matplotlib's first milestone (spec 023).

Usage: plot_line.py <data dir> <out dir> [png].

A fixed line plot on the Agg backend: two lines, a title and a legend on a 4 x 3 inch figure at
100 dpi. It prints the full SHA-256 and the shape of the canvas's RGBA buffer, which must equal
native matplotlib's at the same pins. The output directory stays empty (every file there is
compared byte for byte, and native Pillow deflates with zlib-ng, the guest's with zlib, so the PNG
files differ while the pixels are equal); with a third argument the PNG is saved there, and the
judge decodes it and compares its pixels with this hash. The oracle runs it with
MPL_IGNORE_SYSTEM_FONTS=1 and a fresh MPLCONFIGDIR, so it uses matplotlib's own fonts, as the guest
does."""

import hashlib
import sys

import matplotlib

matplotlib.use("agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import ft2font  # noqa: E402

data_dir, out_dir = sys.argv[1], sys.argv[2]
png = sys.argv[3] if len(sys.argv) > 3 else None
print(
    f"versions python={sys.version_info[0]}.{sys.version_info[1]} "
    f"matplotlib={matplotlib.__version__} numpy={np.__version__}"
)
print("backend", matplotlib.get_backend(), "freetype", ft2font.__freetype_version__)
fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
x = np.linspace(0, 2 * np.pi, 50)
ax.plot(x, np.sin(x), label="sin")
ax.plot(x, np.cos(x), "--", label="cos")
ax.set_title("wasi_python")
ax.legend()
fig.canvas.draw()
rgba = np.asarray(fig.canvas.buffer_rgba())
print("rgba", "x".join(str(n) for n in rgba.shape), hashlib.sha256(rgba.tobytes()).hexdigest())
if png is not None:
    fig.savefig(png)
