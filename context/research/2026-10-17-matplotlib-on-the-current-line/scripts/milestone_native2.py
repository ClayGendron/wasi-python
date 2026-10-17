import sys, hashlib
import matplotlib
matplotlib.rcParams["svg.hashsalt"] = "wasi"
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
fig.savefig("/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/mpl-research/native-out2/plot.png")
fig.savefig("/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/mpl-research/native-out2/plot.svg", metadata={"Date": None})
print("png", hashlib.sha256(open("/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/mpl-research/native-out2/plot.png", "rb").read()).hexdigest()[:16])
try:
    fig.savefig("/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/mpl-research/native-out2/bad.png", dpi=-1)
except Exception as e:
    print("bad dpi:", type(e).__name__, e)
from matplotlib import font_manager
print("fonts", len(font_manager.fontManager.ttflist), font_manager.findfont("DejaVu Sans"))
print("cachedir", matplotlib.get_cachedir())
