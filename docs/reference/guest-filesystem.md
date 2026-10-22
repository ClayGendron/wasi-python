# Guest filesystem

This page describes the file system a guest program sees: which paths exist, which are writable,
where `HOME` and `/tmp` are, and how Python finds modules. Use it when a program cannot find a
file, cannot write one, or imports the wrong module.

The *guest* is the Python program running inside the sandbox. The *host* is your process and
your machine. The guest sees no host path unless you hand it one.

## By default: nothing writable

With no arguments, a call has no `/`. It sees only two read-only places:

| guest path | what it is |
|---|---|
| `/usr/local/lib` | The stdlib zip, as `/usr/local/lib/python315.zip`: the standard library and every package in the set. |
| `/usr/local/lib/python315.zip/matplotlib/mpl-data` | matplotlib's data (fonts, `matplotlibrc`, styles), the path matplotlib itself computes. |

The program can import, compute, print and read the stdlib. A relative path fails, because there
is no working folder to resolve it against. `open('x', 'w')`, `tempfile`, `np.save` and
`df.to_csv('x.csv')` all fail with `OSError`.

You add places with three arguments: `root=`, `grants=` and `mounts=`.

## The root: `/`

| `root=` | what the guest sees at `/` |
|---|---|
| `False` or `None` (the default) | No `/` at all. |
| `True` | A fresh private folder, writable, removed after the call (or when a session ends). |
| a host path | That host folder, writable, made if it is missing. |

The runner prepares a root's `usr/local/lib` and `tmp` itself. The stdlib zip is never in a root:
every call sees it read-only at `/usr/local/lib`, whatever the root holds. A write, a create or a
rename at or under `/usr/local/lib` answers `EPERM`, however the path is spelled.

On the command line, `--private-root` is `root=True`, `--root HOST` is a host path, and
`--no-root` (or neither) is no root.

## Grants: host folders at guest paths

A *grant* hands the guest one host folder at a guest path:

```python
from pathlib import Path

from wasi_python import Grant, run

data = Path.home() / "project" / "data"
done = run(
    ["-c", "import os; open('/out/n.txt', 'w').write(str(len(os.listdir('/data'))))"],
    grants=[Grant(data, "/data"), Grant("/tmp/job-17", "/out", writable=True)],
)
```

- A grant is read-only unless it says `writable=True`. A read-only grant refuses every write with
  `EPERM`, which Python raises as `PermissionError`.
- A guest path must be absolute, with no empty, `.` or `..` part and no trailing `/`. It cannot be
  `/` (that is the root), nor `/usr/local/lib` or anything under it. No two grants may share a
  guest path.
- Grants may nest (`/data` read-only with `/data/out` writable), in any order. The guest's C
  library picks the longest matching guest path.
- `..` never crosses from one grant into another, and a grant does not appear in a listing of its
  parent.

See [Grants](../how-to/grants.md) for the checks on the host side.

## Mounts: files served by your code

A *mount* is like a grant, but your own Python object, a *provider*, answers each file call
instead of a host folder. A mount's guest path is absolute, or `/` for the guest's whole file
system (not together with `root=`). A mount is read-only unless it says `writable=True`.

See [Mounts](../how-to/mounts.md).

## `/tmp`, `HOME` and the environment

The guest's environment starts from three variables. Anything you pass in `env=` is laid over
them.

| variable | value |
|---|---|
| `TMPDIR` | `/tmp` |
| `PYTHONTZPATH` | empty, so `zoneinfo` reads the tzdata in the stdlib zip |
| `HOME` | a fresh, empty folder for each call, removed after it (see below) |

There is no `PATH` variable.

`/tmp` is writable only when something writable serves it: a writable root (its own `tmp`) or a
writable grant at `/tmp`. Where `/tmp` is writable, the runner makes `HOME` fresh inside it for
each call. Where it is not, `HOME` is an empty, read-only folder of the call's own, so `~` never
falls back to the working folder. A mount at `/tmp`, writable or not, gets the read-only `HOME`
too. Pass `HOME` in `env=` if you need a writable one, at a folder no untrusted call writes.

A `Session` makes its `HOME` once, for the whole session.

## Paths the guest does not have

The guest has no `/dev/null` and no `/dev/urandom`. Use `os.urandom`, `secrets` or `uuid.uuid4()` for randomness; they use real
entropy.

## The import path

Python looks for modules on `sys.path`. In the guest it holds one entry by default, the stdlib
zip at `/usr/local/lib/python315.zip`.

The interpreter runs in isolated mode with `site` off. So `PYTHONPATH` in `env=` is not read,
and no module, `.pth` file or `pyvenv.cfg` in a root runs at start-up. The runner never puts the
root, a writable grant or a mount on the import path.

To import your own code, put it in a **read-only grant** and name its guest path in
`import_path=` (or `--import-path GUEST` on the command line):

```python
lib = Path.home() / "agent-lib"  # holds helpers.py, and tools.zip with a package toolbox
done = run(
    ["-c", "import helpers, toolbox; print(helpers.VERSION)"],
    grants=[Grant(lib, "/lib")],
    import_path=["/lib", "/lib/tools.zip"],
)
```

- Entries go on `sys.path` after the stdlib zip, in the order given. Each is a folder or a zip
  file inside a read-only grant.
- Because they come after the runtime, a module the runtime has (the stdlib's, numpy's, pandas',
  the tool protocol's `host`) is always the runtime's. Name your packages apart.
- A module the runtime looks for and lacks is taken from an entry: C accelerators such as
  `_decimal`, other platforms' modules such as `fcntl`, and optional dependencies such as `pytz`.
  Ship such a name only on purpose.
- A missing entry, or a file that is not a zip, is skipped, as Python skips a bad `PYTHONPATH`
  entry.
- No `.pyc` is ever written. A valid `.pyc` already in an entry, made for CPython 3.15, is used.

The runner refuses, before any work, an entry served by the root, a writable grant or a mount; a
writable grant or mount under an entry; and a writable grant or root inside the grant that serves
an entry. See [Grants](../how-to/grants.md).

## Error numbers

Errors inside the guest carry WASI's numbers, not Linux's. A missing path is `[Errno 44]`
(`ENOENT`), where Linux says `[Errno 2]`. `open('')` raises `IsADirectoryError`, not
`FileNotFoundError`. See [Results and errors](results-and-errors.md#errno-a-providers-answers).

## In one line

By default the guest sees only the read-only stdlib at `/usr/local/lib`; `root=`, `grants=` and
`mounts=` add the rest, and only read-only grants named in `import_path=` can add code.
