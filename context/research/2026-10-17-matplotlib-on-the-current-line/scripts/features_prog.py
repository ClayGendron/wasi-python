import numpy as np
def tryit(label, fn):
    try:
        print(label, "->", fn())
    except Exception as e:
        print(label, "-> raised", type(e).__name__, str(e)[:90])
import kiwisolver as kiwi
def unsat():
    s = kiwi.Solver(); x = kiwi.Variable("x")
    s.addConstraint(x >= 10); s.addConstraint(x <= 5)
tryit("kiwisolver unsatisfiable", unsat)
import matplotlib.tri as mtri
tryit("qhull collinear points", lambda: mtri.Triangulation([0, 1, 2, 3], [0, 1, 2, 3]).triangles)
tryit("qhull good points", lambda: mtri.Triangulation([0, 1, 0, 1], [0, 0, 1, 1]).triangles.shape)
import contourpy
z = np.add.outer(np.arange(5.0), np.arange(5.0))
tryit("contourpy serial", lambda: len(contourpy.contour_generator(z=z).lines(3.0)))
tryit("contourpy threaded, 2 threads", lambda: len(contourpy.contour_generator(z=z, name="threaded", thread_count=2).lines(3.0)))
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
tryit("contourf", lambda: type(ax.contourf(z)).__name__)
tryit("tricontour", lambda: type(ax.tricontour([0, 1, 0, 1, .5], [0, 0, 1, 1, .5], [1, 2, 3, 4, 5])).__name__)
tryit("mathtext", lambda: (ax.set_title(r"$\alpha^2 + \sqrt{x}$"), fig.canvas.draw(), "drawn")[-1])
tryit("pdf", lambda: (fig.savefig("/out/f.pdf"), "saved")[-1])
tryit("ps", lambda: (fig.savefig("/out/f.ps"), "saved")[-1])
tryit("jpeg", lambda: fig.savefig("/out/f.jpg"))
from PIL import Image
tryit("PIL png roundtrip", lambda: Image.open("/out/f.png" if False else (fig.savefig("/out/f.png") or "/out/f.png")).size)
import threading
tryit("threading.Timer", lambda: threading.Timer(0.1, lambda: None).start())
