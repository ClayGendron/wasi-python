# Spec 096: a figure with constrained layout, drawn, closed, then a full collection.
import gc
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, axs = plt.subplots(2, 2, layout="constrained")
for ax in axs.flat:
    ax.plot([0, 1, 2], [2, 0, 1])
    ax.set_title("t")
fig.canvas.draw()
plt.close(fig)
del fig, axs, ax
print("collected", gc.collect() > 0)
print("ok")
