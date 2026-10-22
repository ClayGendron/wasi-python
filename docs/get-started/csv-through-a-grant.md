# Read a CSV through a grant

In this tutorial you hand the guest a folder of data to read and a folder to write into, then read
what it wrote from the host. You do it from Python and then from the command line. Start with
[Your first run](first-run.md) if you have not run the guest yet.

A *grant* gives the guest one host folder at a path of the guest's choosing. A grant is read-only
unless you say `writable=True`. The guest sees no host folder except through a grant.

## Step 1: Make the two folders

The guest reads from one folder and writes to another. Both must exist on the host before the
call:

- a data folder, `~/project/data`, holding your CSV files;
- an output folder, `/tmp/job-17`, empty.

The runner checks every granted folder before the guest starts, and a grant whose folder is
missing is refused.

## Step 2: Grant them and run

```python
from pathlib import Path

from wasi_python import Grant, run

data = Path.home() / "project" / "data"
done = run(
    ["-c", "import os; open('/out/n.txt', 'w').write(str(len(os.listdir('/data'))))"],
    grants=[Grant(data, "/data"), Grant("/tmp/job-17", "/out", writable=True)],
)
```

The guest sees your data folder at `/data`, read-only, and `/tmp/job-17` at `/out`, writable. It
lists `/data` and writes the count to `/out/n.txt`.

The result is on the host: `/tmp/job-17/n.txt` now holds the number of entries in
`~/project/data`.

Try writing to `/data` from the guest. A read-only grant refuses every write with `EPERM`, which
the guest sees as `PermissionError`.

## Step 3: Write and read a CSV with pandas

pandas reads and writes through grants as through any folder. This example uses a `Session`, which
runs several pieces of code one after another in one interpreter, so the second piece sees the
`df` the first one made. See [Run several turns in a session](../how-to/sessions.md) for more.

```python
import tempfile
from wasi_python import Grant, Session

keep = tempfile.mkdtemp()
with Session(grants=[Grant(keep, "/keep", writable=True)]) as session:
    session.run("import pandas as pd; df = pd.DataFrame({'a': [1, 2, 3]})")
    session.run("df.to_pickle('/keep/df.pkl'); df.to_csv('/keep/df.csv', index=False)")
with Session(grants=[Grant(keep, "/keep")]) as later:
    done = later.run("import pandas as pd; int(pd.read_pickle('/keep/df.pkl').a.sum())")
    done.stdout                                  # b'6\n'
```

The first session writes `df.csv` and `df.pkl` into the writable grant. The second session grants
the same folder read-only and reads the data back. On the host, the folder `keep` now holds both
files, and you can open `df.csv` with any tool.

Only a guest may unpickle what a guest wrote. Never unpickle a guest's file on the host: read the
CSV instead.

## Step 4: Do the same from the command line

The `wasi-python run` command takes the same grants as options. `--grant GUEST=HOST` gives a
folder read-only, and `--grant-writable GUEST=HOST` gives it writable:

```
$ wasi-python run --grant /data=./inputs --grant-writable /out=./results --stdin prog.py -- -
```

The guest does not see the host's folders, so it cannot open `prog.py` itself. `--stdin prog.py`
sends the file as the guest's standard input, and the `-` after `--` tells the guest's Python to
run its standard input as the program. Whatever `prog.py` writes to `/out` is in `./results` when
the command returns.

## What you did

You gave the guest a read-only folder and a writable one, ran pandas against them, and read the
output from the host. Everything else on your machine stayed out of the guest's reach.

Next, see [Grant folders to the guest](../how-to/grants.md) for nested grants, the import path,
and the folders the runner refuses to grant.

In one line: a grant hands the guest one host folder, read-only unless you say `writable=True`,
and what the guest writes there is yours to read when the call returns.
