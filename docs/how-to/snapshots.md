# Start every call from a snapshot

This guide shows you how to run your setup code once, keep the result as a snapshot, and start each later call from it: how to make one, save it, load it, and what it keeps.

A *snapshot* is the guest's memory after your code ran once. Every call you give it is still a fresh, sealed instance. That instance starts with a private copy of the snapshot's memory instead of an empty interpreter, so it skips the seconds your imports took.

Every call already starts from the artifact set's own snapshot binary, `python-snapshot.wasm`, which has the interpreter started and no package imported. A snapshot you make starts from that binary and adds your code.

## Make one and use it

```python
from wasi_python import make_package_snapshot, run

snap = make_package_snapshot()  # every package the set ships, imported once
done = run(["-c", "import sklearn; print(sklearn.__version__)"], snapshot=snap)
```

`snapshot=` takes `True` (the set's snapshot binary, the default), `False` (the plain reactor) or a `Snapshot`. `run`, `run_async` and `Session` all take it. Making the snapshot of every package runs about 35 billion instructions, once. A call from it pays only for its own work.

## Run any code once with `make_snapshot`

`make_snapshot(code)` runs any code you give it and keeps what it left: imports, data read from a grant, functions and objects.

```python
from wasi_python import Grant, make_snapshot, run

grants = [Grant("data", "/data")]
snap = make_snapshot(
    "import pandas as pd\n"
    "df = pd.read_csv('/data/sales.csv')\n"
    "def summarize(frame):\n"
    "    return frame.groupby('region').total.sum()\n",
    grants=grants,
)
done = run(["-c", "print(summarize(df))"], grants=grants, snapshot=snap)
```

`make_snapshot` takes `run`'s keywords and checks them by the same rules. Three differ:

- Its deadline is 600 seconds by default, since making a snapshot is a setup step, not a request.
- It takes no `argv`, `stdin` or `cancel`: the code is the program.
- It takes no `tools`. A tool's state lives in your process and cannot be kept in an image, so pass `tools=` to the calls that use the snapshot.

## Import every package, or a few, with `make_package_snapshot`

`make_package_snapshot()` with no list imports every package the set ships, with the submodules a program reaches for, so you never type the list. Give it names to import fewer:

```python
from wasi_python import make_package_snapshot

snap = make_package_snapshot(["scikit-learn", "pandas"])
```

A name is either a distribution's name, as you install it (`scikit-learn`, `pillow`), which imports that package's modules, or a module's dotted name, which is imported as given (`sklearn.tree`, `json`). Its root defaults to a fresh private root, removed after the making, because matplotlib needs a writable `/tmp` to import. The calls from the snapshot need no root.

## Save it and load it in another process

A snapshot lives in your process. To use it in another, save it to a file and load it there:

```python
from wasi_python import Snapshot

snap.save("app.wpsnap")
later = Snapshot.load("app.wpsnap")
```

The file is compressed, and the image of every package takes about 73 MiB. On POSIX, `load` reads only a file that only you can write, as `save` makes it, in a folder no other user can change. On Windows the runner checks only that the file is not a link and has one name, so keep it in a folder only you can write. `load` checks the file's header, size and hash before it returns.

A snapshot binds to the artifact set it was made with. `snap.check()` raises `SnapshotMismatch` when the set you run is another, as a call would. A service that keeps a saved snapshot loads it, or makes it again when the file is missing or the set has changed:

```python
from wasi_python import Snapshot, SnapshotMismatch, make_package_snapshot

try:
    snap = Snapshot.load(path)
    snap.check()
except (FileNotFoundError, SnapshotMismatch):
    snap = make_package_snapshot()
    snap.save(path)
```

Keep saved snapshots where no guest is granted writing, as you keep your own code. Once this process has saved or loaded a snapshot in a folder, the runner keeps guests away from that folder both ways. A call refuses a writable grant or root that holds it. `save` and `load` raise `PermissionError` for a folder that a call or session running now may write. Before that, and in any other process, the runner cannot know the file, so the rule is yours: a guest given writing over it could rewrite it, and the next `load` would accept it.

## Start a session from it

`Session(snapshot=snap)` opens a session whose first state is the snapshot. Its turns run in the namespace your code ran in, so your code's names are there. Each session has its own copy: no session or call sees another's turns.

```python
from wasi_python import Session

with Session(snapshot=snap) as session:
    session.run("result = summarize(df)")
    done = session.run("result")
```

## Know what runs where

Your program runs after the snapshot's code, in the same namespace, as if both were one script. A name your program rebinds is what your code's functions then read.

The modules your code imported stay imported. The making's `import_path` is not kept: a program that imports more from that folder passes `import_path` again, and the runner checks it as it checks every call's.

What is frozen in the snapshot:

- the modules your code imported, and the objects and functions it made;
- what the environment changed while your code imported, such as a path a package read from `HOME`;
- the state of generators your code made itself;
- warnings already shown.

What is fresh in every call:

- `sys.argv` and the environment;
- the clocks;
- the random generators of `random`, numpy, sympy, and `tempfile`'s names;
- `HOME`'s folder: every call sees the snapshot's `HOME` path, `/tmp/.home-snapshot`, with an empty folder of its own there;
- the grants, mounts and root, in any order and any number.

## Avoid these in the snapshot's code

- **Leaving a file open.** A call cannot reopen it, so `make_snapshot` refuses the snapshot with `SnapshotFailed` and the reason `"open file"`. Use `with`.
- **Waiting for time to pass.** The clocks do not move while the code runs, so a loop on the time never ends and runs to its deadline.
- **Making or passing a secret.** The code's entropy is zeros, so a key it draws is the same in every snapshot. Values in `env=` and in the code stay in the image and in a saved file.
- **Temporary files.** They are gone when the making ends. Read data from a grant instead.
- **A visitor's code, or inputs a guest can write.** The snapshot is as trustworthy as its code and everything the code read. Make it from your own code and from files no guest can change.
- **Names a program does not expect.** Every name your code leaves is in every program's namespace: `from os import *` binds `os.open` over `open`. Import modules by name, keep setup in functions, and `del` what the code used only once.

A snapshot holds your own code's state, made before any program runs. A snapshot of a guest's run, taken while or after it ran, is not offered.

## Know the costs

- **Making it** costs its code's instructions, once. With `fuel=`, `snap.origin.prelude_fuel` records them.
- **Each call** copies the image into its fresh instance before any guest code runs. The copy is the host's work, so it spends no fuel: `fuel_used` is the call's own work. The image of every package is 203 MiB and its copy took about 15 ms on an Apple M1 Pro.
- **Memory.** Each live call or session from a snapshot holds a private copy of the whole image, since the copy writes every page. N calls at once hold N copies, plus the one the `Snapshot` holds. A call needs `memory_bytes` at least the image's size. A load holds up to three copies of the image at its peak.
- **The end of a call.** A call from a snapshot does not tear down the modules the snapshot holds, so it ends at the cost of its own work. What your program's own names held is finalized as in CPython. An object it hung on an imported module is flushed, not finalized, so close what you open, or use `with`.

The [limits page](../reference/defaults-and-limits.md#making-a-snapshot) lists every default.

In one line: make a snapshot once with `make_snapshot` or `make_package_snapshot`, pass it as `snapshot=`, and every call starts as a fresh copy of it.
