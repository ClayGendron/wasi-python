# Your first run

In this tutorial you run Python code inside the sandbox twice: once from the command line and once from Python. You also see what the code can and cannot do by default. You need the package installed first; see [Install wasi-python](install.md).

## Run a program from the command line

Run one line of Python with the `wasi-python` command:

```
$ wasi-python run -- -c "print(1)"
{"exit_code": 0, "fuel_used": null, "stderr": "", "stdout": "1\n", "trapped": null, "truncated": []}
```

Everything after `--` goes to the guest's Python, as it would go to `python`. The *guest* is the program that runs inside the sandbox.

The command prints one line of JSON that says how the program ended:

- `exit_code` is the program's exit status, here 0.
- `stdout` and `stderr` are what it printed.
- `trapped` is `null` because the program ended by itself.
- `fuel_used` is `null` because you set no cap on the instructions it may run.
- `truncated` is empty because no output passed the limit.

## Run a program from Python

Now do the same from Python, with pandas:

```python
from wasi_python import run

done = run(["-c", "import pandas as pd; print(pd.Series([1, 2, 3]).sum())"])
done.exit_code, done.stdout        # (0, b'6\n')
```

`run` takes the guest's arguments as a list, as `python` would take them. It runs the program in a fresh instance of the runtime and returns a `Completed` value with the same fields as the JSON line. `stdout` is bytes, not text.

Each call gets its own instance. No variable or import from one call is there in the next.

## See what the guest cannot do

By default the guest has nothing it can write. It has no `/`, no `/tmp`, and a `HOME` folder it cannot write. It sees only the read-only standard library and whatever you grant it.

So the guest can import, compute, print and read the standard library. But each of these fails with `OSError`:

- `open('x', 'w')`
- `tempfile`
- `np.save`
- `df.to_csv('x.csv')`

This is on purpose. The runner is made for running code nobody reviewed, such as a model's. Code like that gets nothing writable unless you hand it something.

## Give the guest a private root

Pass `root=True` to give one call a fresh, private folder as its `/`. The guest can write there. The runner removes the folder after the call.

You can also pass a host folder as `root=`. The guest then sees that folder at `/`, writable, and the files stay there after the call.

On the command line, `--private-root` is `root=True` and `--root HOST` names a folder.

To hand the guest only some folders, use grants. The next tutorial, [Read and write files through a grant](csv-through-a-grant.md), shows how.

## Read the result

`done` is a `Completed`. Its fields are `exit_code`, `stdout`, `stderr`, `trapped`, `fuel_used`, `truncated`, `files` and `tools`. When the program is stopped, for example by the deadline, `trapped` names the reason and `exit_code` is `None`. See [Results and errors](../reference/results-and-errors.md) for every field and value.

In one line: `wasi-python run -- -c "print(1)"` and `run(["-c", code])` run code in a sandbox that can compute and print but cannot write anything you did not give it.
