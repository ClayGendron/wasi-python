# Plot with matplotlib

This guide shows how to draw a plot in the guest and save it as a file the host can read. matplotlib 3.11.2 is compiled in, on the Agg backend, which draws to files rather than to a window.

## Save a plot into a writable grant

matplotlib needs two things the default sandbox does not give: a folder to save into, and a writable folder for its font cache. One writable grant serves both:

```python
from wasi_python import Grant, run

done = run(["-c", "import matplotlib; matplotlib.use('agg'); import matplotlib.pyplot as plt;"
            " plt.plot([1, 3, 2]); plt.savefig('/out/plot.png')"],
           grants=[Grant("/tmp/job-17", "/out", writable=True)],
           env={"MPLCONFIGDIR": "/out/.matplotlib"})  # a writable folder for its font cache
```

The plot lands in `/tmp/job-17/plot.png` on the host. Its pixels are native matplotlib's at the same pins.

## Pick a format

- PNG, JPEG, PDF, PS, EPS and SVG save. TIFF saves without compression.
- WebP raises an error: Pillow is built with zlib and libjpeg-turbo, and without its other codecs.
- Only the non-interactive backends are in the zip.

For files that are the same on every run, set `rcParams["svg.hashsalt"]` and pass `metadata={"Date": None}` (SVG) or `metadata={"CreationDate": None}` (PDF), or set `SOURCE_DATE_EPOCH`, as natively.

## Keep the font cache between calls

matplotlib writes its font list to `MPLCONFIGDIR`, else to `$HOME/.matplotlib`. The runner makes `HOME` fresh on every call, so each call that imports matplotlib rebuilds the list. To keep it, set `MPLCONFIGDIR` in `env=` to a writable grant you keep across calls.

A shared, writable `MPLCONFIGDIR` is trusted by later calls: its JSON names font files, so one call can make the next parse a font of its choosing. Share one only between calls you trust alike.

## Without any writable folder

With no root, no writable grant at `/tmp` and no `MPLCONFIGDIR`, `import matplotlib` raises `OSError` ("Matplotlib requires access to a writable cache directory"). Give the call `root=True`, a writable grant at `/tmp`, or `MPLCONFIGDIR` in a writable grant. seaborn imports `matplotlib.pyplot`, so it needs the same.

## Fonts and data

matplotlib's data (fonts, `matplotlibrc`, styles) is in the stdlib zip. The runner extracts it once per process and grants it read-only at `/usr/local/lib/python315.zip/matplotlib/mpl-data`, the path matplotlib computes. You need do nothing. A host of your own does this itself: see [Artifacts](../reference/artifacts.md#using-the-files-without-the-runner).

Contours (`contour`, `contourf`, `clabel`) and Delaunay triangulations (`tricontour`, `tripcolor`, `triplot` on bare points) work. There are no threads, so anything that starts one (a `threading.Timer`, say) raises `RuntimeError`; drawing and saving never do. For the rest, see the [limitations page](../reference/limitations.md).

For Excel workbooks, PDFs and XML, see [Work with Excel, PDF and XML files](excel-pdf-xml.md).

## In one line

Use the Agg backend, save into a writable grant, and point `MPLCONFIGDIR` at a writable folder.
