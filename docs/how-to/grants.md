# Grant folders to the guest

This guide shows you how to give the guest host folders: read-only, writable, as its whole `/`, or as a place to import code from. It also lists what the runner refuses, and what a grant does not protect.

A *grant* gives the guest one host folder at a guest path. A *root* is the folder the guest sees as `/`. By default the guest has neither, so nothing it can see is writable.

## Grant a folder

Pass `grants=` to `run` (or to `Session`), one `Grant` per folder:

```python
from pathlib import Path

from wasi_python import Grant, run

data = Path.home() / "project" / "data"
done = run(
    ["-c", "import os; open('/out/n.txt', 'w').write(str(len(os.listdir('/data'))))"],
    grants=[Grant(data, "/data"), Grant("/tmp/job-17", "/out", writable=True)],
)
```

`Grant(host, guest, *, writable=False)` gives the guest the host folder `host` at the guest path `guest`.

- A grant is read-only unless you pass `writable=True`.
- A read-only grant refuses every write-type call with `EPERM`. The guest sees `PermissionError`.
- Grants may nest, in any order: `/data` read-only with `/data/out` writable works. The guest's C library picks the longest matching guest path.

On the command line, `--grant GUEST=HOST` gives a folder read-only and `--grant-writable GUEST=HOST` gives it writable. The split is at the first `=`, so a host path such as `C:\data`, or one that holds `=`, passes whole. A guest path given there cannot hold `=`.

## Choose a root

`root=` sets what the guest sees at `/`:

| `root=` | on the command line | what the guest gets |
|---|---|---|
| `False` or `None` (the default) | `--no-root`, or nothing | no `/` at all; a relative path fails |
| `True` | `--private-root` | a fresh private folder at `/`, writable, removed after the call |
| a host path | `--root HOST` | that folder at `/`, writable, made if missing, kept after the call |

On Linux and macOS, a missing root's folders are made for you alone (0700), and a folder another user made on the way is refused. On Windows, from Python 3.13, a made folder gets an access list for you and the administrators alone; a folder that already exists is used as it is.

A grant and a root work together. With a root, the grants still appear at their guest paths.

## Know where HOME is

The runner makes `HOME` fresh for each call in the folder the guest sees at `/tmp`. That folder is a writable grant at `/tmp` if you give one, else the root's own `tmp`. With neither, `HOME` is an empty, read-only folder the runner owns, so `~` never names a folder of the root. A fresh `HOME` is removed after the call.

The guest's environment also starts with `TMPDIR=/tmp`. Anything you pass in `env=` is laid over these values.

## Keep state between calls

Each call is a fresh instance. A file written to a private root (`root=True`) is removed with it. State that must outlive a call, such as an agent's notes between turns, lives in a writable grant you keep. Each call reads it at the start and writes it at the end:

```python
state = Path.home() / "agent-17"  # the embedder's folder for this agent
state.mkdir(exist_ok=True)
run(["-c", "import json, os; p = '/state/n.json'; n = json.load(open(p)) if os.path.exists(p) else 0;"
     " json.dump(n + 1, open(p, 'w')); print(n + 1)"],
    grants=[Grant(state, "/state", writable=True)])
```

Each call adds one to the count in `/state/n.json` and prints it. A root given as a host path keeps its files too.

## Import code from a grant

`import_path=` names guest paths the program may import from. On the command line, use `--import-path GUEST`, once per entry.

```python
lib = Path.home() / "agent-lib"  # holds helpers.py, and tools.zip with a package toolbox
done = run(
    ["-c", "import helpers, toolbox; print(helpers.VERSION)"],
    grants=[Grant(lib, "/lib")],
    import_path=["/lib", "/lib/tools.zip"],
)
```

The entries go on `sys.path` after the standard library zip, in the order you give. Each entry is a folder or a zip file inside a **read-only grant**. The runner refuses, before any work:

- an entry that the root, a writable grant or a mount serves, or that nothing serves;
- a writable grant, or any mount, whose guest path lies under an entry;
- a writable grant, or `root`, whose host folder lies inside the folder of the grant that serves an entry;
- a relative path, `/`, `/usr/local/lib` or a path under it, or the same entry twice.

These rules stop one call from planting code that the same call, or a later one, imports.

A missing entry, or a file that is not a zip, is skipped, as Python skips a bad `PYTHONPATH` entry. No `.pyc` file is ever written. A valid `.pyc` already in an entry, made for CPython 3.15, is used.

The runtime's own modules come first. A module the runtime has, such as numpy, pandas or the tool protocol's `host`, is always the runtime's, so name your packages apart. A module the runtime looks for and lacks is taken from an entry. That includes C accelerators such as `_decimal`, other platforms' modules such as `fcntl`, and optional dependencies such as `pytz`. Ship such a name only on purpose.

A call with an import path costs a little more fuel, and the program reaches the recursion limit two frames sooner.

## The standard library is never in a root

Every call sees the standard library zip read-only at `/usr/local/lib`, whatever its root and grants. matplotlib's data sits read-only at `/usr/local/lib/python315.zip/matplotlib/mpl-data`. A root holds only your files; the guest cannot change the runtime through it.

## What the runner refuses

The runner checks every grant, and `root`, before it sets up the guest. A bad one raises `TypeError` or `ValueError` and nothing runs.

- **A guest path** must be absolute, with no empty, `.` or `..` part and no trailing `/`. It must not be `/` (use `root=`), nor `/usr/local/lib` or a path under it. No two grants may share one.
- **A host path** is walked one folder at a time, and never through a link in a folder you can write, since a guest could have made it. On Windows it never passes through any link, junction or other reparse point, which includes OneDrive's cloud folders. A grant's folder must exist; a missing `root` is made. Run as the superuser, every folder counts as writable, so every link on the way is refused, macOS's `/tmp` and `/var` included: name the real path.
- **`..` in a host path** is taken on the folders walked, so `new/../x` after a missing `new` is refused, on every system.
- **On Windows**, a name that Windows rewrites or rejects is refused anywhere in the path: one that holds `:` or ends in a space or a period, a reserved device name such as `CON`, `NUL`, `COM1` or `LPT1` (with or without an extension), `CONIN$` and `CONOUT$`, and a name that holds `<`, `>`, `"`, `|`, `?`, `*` or a control character.
- **A read-only grant inside a writable one, or inside `root`**, is refused: the guest could change it through the other.
- **A writable grant or `root` at, inside or above the runtime's own folders** is refused. These are the standard library folder, the artifact set, every module cache this process could use, the code of `wasi_python` and wasmtime-py, and the host Python's own `stdlib`, `site-packages` and `bin` (or `Scripts`) folders. So `root=Path.home()` is refused, and so is a project folder that holds the `.venv` this process runs from.
- **Any grant at or above the temporary folder** is refused, read-only too: it holds every call's private folders and `stdin`.

Folders are compared by identity (device and inode), never by spelling. After wasmtime opens each folder, the runner checks that it opened the folder it checked. A folder swapped in between raises `RuntimeError`.

## What grants do not do

- `..` never crosses from one grant into another, and a grant does not appear in a listing of its parent.
- A read-only grant can still change if the same host files are writable elsewhere, by another call or another program.
- A writable grant answers as the host's file system does. On Windows, see [Serve files from your own code](mounts.md#on-windows).
- A raw descriptor opened only to read refuses a write, and the error is the host's own: `EBADF` on Linux and macOS, `EACCES` on Windows. Python's file objects refuse first, with `io.UnsupportedOperation`.
- A SQLite database in a read-only grant opens only through a URI that takes no lock: `file:/data/db.sqlite?immutable=1`.
- A folder reachable by two routes, such as a bind mount, is judged by the route you give.

To serve files from your own code instead of a host folder, see [Serve files from your own code](mounts.md). For every path the guest sees, see [The guest's filesystem](../reference/guest-filesystem.md).

In one line: pass `Grant(host, guest)` for each folder the guest may read, add `writable=True` only where it must write, and keep code it imports in read-only grants.
