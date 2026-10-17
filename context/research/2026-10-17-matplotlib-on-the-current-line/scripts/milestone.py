import sys, hashlib
import matplotlib
matplotlib.use("agg")
import matplotlib.pyplot as plt
import numpy as np
print("matplotlib", matplotlib.__version__, matplotlib.get_backend(), matplotlib.ft2font.__freetype_version__)
fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
x = np.linspace(0, 2 * np.pi, 50)
ax.plot(x, np.sin(x), label="sin")
ax.plot(x, np.cos(x), "--", label="cos")
ax.set_title("wasi_python")
ax.legend()
fig.canvas.draw()
rgba = np.asarray(fig.canvas.buffer_rgba())
print("rgba", rgba.shape, hashlib.sha256(rgba.tobytes()).hexdigest()[:16])
fig.savefig("/out/plot.png")
fig.savefig("/out/plot.svg", metadata={"Date": None})
print("png", hashlib.sha256(open("/out/plot.png", "rb").read()).hexdigest()[:16])
try:
    fig.savefig("/out/bad.png", dpi=-1)
except Exception as e:
    print("bad dpi:", type(e).__name__, e)
from matplotlib import font_manager
print("fonts", len(font_manager.fontManager.ttflist), font_manager.findfont("DejaVu Sans"))
print("cachedir", matplotlib.get_cachedir())
