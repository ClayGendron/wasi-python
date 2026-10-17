"""Which fontTools modules matplotlib imports for plots saved in every non-GUI format."""
import io, os, sys, tempfile
os.environ["MPL_IGNORE_SYSTEM_FONTS"] = "1"
os.environ["MPLCONFIGDIR"] = tempfile.mkdtemp()
import matplotlib
matplotlib.use("agg")
import matplotlib.pyplot as plt

def figure():
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [3, 1, 2], label="line ünï")
    ax.set_title(r"$\alpha^2 + \sqrt{x}$ mathtext")
    ax.text(1.5, 2, "DejaVu Serif", family="serif")
    ax.text(1.5, 2.5, "mono", family="monospace")
    ax.text(1.5, 1.5, r"$\mathcal{C}\int$", math_fontfamily="stix")
    ax.legend()
    return fig

for fonttype in (3, 42):
    matplotlib.rcParams["pdf.fonttype"] = fonttype
    matplotlib.rcParams["ps.fonttype"] = fonttype
    for fmt in ("png", "pdf", "ps", "eps", "svg"):
        fig = figure()
        fig.savefig(io.BytesIO(), format=fmt)
        plt.close(fig)
matplotlib.rcParams["svg.fonttype"] = "none"
fig = figure(); fig.savefig(io.BytesIO(), format="svg"); plt.close(fig)
from matplotlib.backends.backend_pdf import PdfPages
with PdfPages(io.BytesIO()) as pp:
    pp.savefig(figure())
mods = sorted(m for m in sys.modules if m == "fontTools" or m.startswith("fontTools."))
print("\n".join(mods))
