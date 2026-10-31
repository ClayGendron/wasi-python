"""matplotlib's figures, handed to the host as displays (spec 163): `module://host.figures`.

A matplotlib backend over Agg's canvas. Its `show()` sends each open figure as a display, its
PNG and its repr, then closes them, as Jupyter's inline backend does. In figures mode the
bootstrap selects it, unless the embedder's environment names a backend, and sends the figures a
cell leaves open at its end. Once the host keeps no more, the rest are closed unrendered.
"""

from matplotlib.backend_bases import FigureManagerBase
from matplotlib.backends.backend_agg import FigureCanvasAgg

FigureCanvas = FigureCanvasAgg
FigureManager = FigureManagerBase


def show(*args, **kwargs):
    """Send every open figure to the host, then close them all."""
    _send_open()


def _send_open():
    """Each open figure sent in turn while the host keeps them; then every one closed."""
    import matplotlib.pyplot as plt
    from matplotlib._pylab_helpers import Gcf

    from . import display

    try:
        for manager in Gcf.get_all_fig_managers():
            if display._stopped:
                break
            display._figure(manager.canvas.figure)
    finally:
        plt.close("all")
