# Read a cell's value and displays

This guide shows you how to get a program's last value, the objects it passes to `display()` and its matplotlib figures back as typed records, as a notebook shows them, instead of as printed text.

## Pass results=True

`run`, `run_async` and `Session` take `results=True`. A session's last expression in each turn, and a `-c` program's last expression, come back as `Completed.value`, and are not printed:

```python
from wasi_python import Session

with Session(results=True, root=True) as session:
    session.run("import pandas as pd\ndf = pd.DataFrame({'x': [1, 2], 'y': [3, 4]})")
    done = session.run("df.head()")

done.value.data["text/plain"]   # the frame's text, as repr() gives it
done.value.data["text/html"]    # its HTML table
done.stdout                     # b""
```

A value of `None` gives `value=None`, as the interactive interpreter prints nothing for it. `_` is still bound to the last value. A program that replaced `sys.displayhook` has its hook called instead, and no value is sent. A script, `-m` or a program read from stdin has no value; its displays still arrive.

## Call display()

In results mode `display` is a builtin, as in IPython. Each object passed to it becomes one `Display` in `Completed.displays`, in order:

```python
from wasi_python import run

done = run(["-c", "print('a')\ndisplay({'k': 1})\nprint('b')"], results=True)
d = done.displays[0]
d.data["text/plain"]            # "{'k': 1}"
done.stdout[: d.stdout_at]      # b"a\n": what printed before it
```

A `Display` has four fields:

- **`data`** maps MIME types to content, read-only. `text/plain` is always there: the object's `repr`. `text/html`, `text/markdown`, `image/svg+xml` and `application/json` are text, and `image/png` is bytes. They come from the object's `_repr_mimebundle_`, then its `_repr_html_`, `_repr_markdown_`, `_repr_svg_`, `_repr_json_` and `_repr_png_`, as a notebook reads them. A method that raises an `Exception`, or returns the wrong type, is skipped.
- **`truncated`** names the MIME types cut or left out because the room ran short.
- **`stdout_at`** and **`stderr_at`** count the bytes the program had written to each stream before it, kept or not.

Without `results=True`, `display` is not a builtin. `from host.display import display` still works there, and prints each object's `repr`, as IPython does in a terminal.

## Add figures=True

`figures=True`, beside `results=True`, sends matplotlib's figures as displays. `plt.show()` sends each open figure as its PNG and its `repr`, then closes it. A figure a cell leaves open is sent at the cell's end, after its value:

```python
with Session(results=True, figures=True, root=True) as session:
    done = session.run("import matplotlib.pyplot as plt\nplt.plot([1, 2, 3])")

png = done.displays[0].data["image/png"]
```

The backend is `module://host.figures`. It is set through `MPLBACKEND`, unless your `env` sets that variable, so a program's own `matplotlib.use()` still wins. A starting image that already imported pyplot is switched at the call's first cell. Rendering a PNG costs the call's fuel. matplotlib needs a writable folder for its cache: see [Plot with matplotlib](matplotlib.md).

## Know the room

A call's or a turn's displays, its value included, share one more `output_bytes` of decoded bytes, beside stdout and stderr, and at most 1,000 records.

- A display past the room is sent once more as its text alone, cut to fit. The other types are named in its `truncated`.
- Once the room or the 1,000 records are spent, the cell sends nothing more and prints nothing more.
- Either way, `Completed.truncated` names `"displays"`.

Under `output_keep="tail"`, with `N` bytes cut, a display's place in `stdout` is `stdout_at - N` plus the length of the `[N bytes cut]` line. A place before the line means the display came in the cut part.

## Trust what comes back as the guest's

A display is guest output, as stdout is. Its HTML and SVG can hold script: render them in a sandboxed frame, never in your own page.

Printed bytes never become a record. Records travel through the door, as tool calls do, and the runner checks every one: six MIME types, each of its own type. A program can still call `display()` with anything it likes.

`results=True` excludes `host=`, and `figures=True` needs `results=True`. Both are fixed for a session. A session started from a checkpoint takes its own `results` and `figures`, never the checkpointed session's.

## In one line

Pass `results=True` and read `Completed.value` and `Completed.displays`; add `figures=True` for matplotlib's figures.
