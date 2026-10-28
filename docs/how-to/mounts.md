# Serve files from your own code

This guide shows you how to serve the guest's files from your own Python code with a mount, read only or writable, and what a mount costs and limits.

A *mount* puts a *provider*, an object you write, at a guest path. The guest opens, reads, lists and stats files there with ordinary calls (`open`, `os.listdir`, `os.stat`, `pandas.read_csv`), and your provider answers each one. The files can come from a database, an object store, or a permission layer of your own. A mount is read-only unless you pass `writable=True`.

## Write a read-only provider

A read-only provider has three methods. This one serves files from a dict:

```python
from wasi_python import Errno, Mount, Stat, run

class Files:  # paths are absolute within the mount: "/" is the mount itself
    def __init__(self, tree):  # {"/a.csv": b"...", "/d": None (a folder)}
        self.tree = tree

    def stat(self, path):
        if path == "/" or self.tree.get(path, b"") is None:
            return Stat("dir")
        return Stat("file", len(self.tree[path])) if path in self.tree else Errno.ENOENT

    def list(self, path):
        prefix = path.rstrip("/") + "/"
        return [(p[len(prefix):], "dir" if v is None else "file")
                for p, v in self.tree.items()
                if p.startswith(prefix) and "/" not in p[len(prefix):]]

    def read(self, path):  # the whole file
        if path == "/" or self.tree.get(path, b"") is None:
            return Errno.EISDIR
        return self.tree.get(path, Errno.ENOENT)

done = run(["-c", "import pandas; print(pandas.read_csv('/work/a.csv'))"],
           mounts=[Mount(Files({"/a.csv": b"x,y\n1,2\n"}), "/work")])
done.files.calls  # {'stat': 0, 'list': 0, 'read': 1, 'write': 0, 'mkdir': 0, ...}
```

Each method gets a normalized absolute path, where `/` is the mount itself. Each answers a value or an `Errno`:

- `stat(path)` returns `Stat(kind, size=0, mtime_ns=0)`. `kind` is `"file"` or `"dir"`, and the `Stat` for `/` must be a folder.
- `list(path)` returns an iterable of `(name, kind)` pairs. A name is one path component: not empty, `.` or `..`, with no `/` or NUL, at most 255 bytes of UTF-8, and no repeats.
- `read(path)` returns the whole file as `bytes`, `bytearray` or `memoryview`. It returns `Errno.EISDIR` when the path is a folder, and `Errno.ENOTDIR` when a parent is a file. The runner makes a folder descriptor only from `EISDIR`.

`Errno` holds WASI's own error numbers, such as `ENOENT`, `EACCES`, `EISDIR` and `ENOSPC`. The guest sees each as the `OSError` of that `errno`. The runner knows nothing about permissions: it calls your provider for every access and passes its answer through.

An open of a file makes one `read`. A listing, such as `os.listdir` or `os.scandir`, makes one `stat` and then one `list`; a listing of the mount itself makes only the `list`. A file asked for as a folder answers `ENOTDIR` after the `stat`, and your `list` is never called for it. `os.stat` makes one `stat`, and `os.fstat` of an open file makes none. Nothing is cached between opens; your provider may cache.

## Raise an OSError instead

A method may raise an `OSError` instead of returning an `Errno`, and the guest gets the same answer. The errno is matched by name, never by number, since numbers differ between hosts. With no errno at all, the class answers: `raise FileNotFoundError(path)` is `ENOENT`, and so on for `FileExistsError`, `IsADirectoryError`, `NotADirectoryError`, `PermissionError` and `TimeoutError`.

An errno outside the `Errno` set becomes `EIO`. The guest never sees the exception's message, only its own C library's text for the errno.

Any other exception, or an answer outside the protocol, gives the guest `EIO` and adds a `FileFault` to `done.files.faults`; the run goes on. A `BaseException` that is not an `Exception`, such as Ctrl-C, stops the call and is raised from `run`.

A mapped raise leaves no fault in the record: it is an answer. So a bug in your provider that raises `FileNotFoundError` reads as the guest's missing file. Log your raises in the provider if you want to see them.

## Treat a path as a name, not a host path

Each path your provider gets is `/` and then components joined by `/`. Each component is a name. It is never empty, `.` or `..`, and it never holds `/`, `\`, `:` or NUL. The runner answers `EINVAL` itself for a component with `\` or `:`, on every host, before your provider is called. So no host can read a component as a separator or a drive. A name your `list` returns with `\` or `:` is still listed, but the guest cannot open it.

A provider that stores on a host folder joins the components one at a time. It never hands the whole path to a host path function. A component may still be a Windows device name such as `CON`, so refuse those on Windows, or resolve the joined path and check that it stays inside the base:

```python
target = base.joinpath(*[p for p in path.split("/") if p]).resolve()
if not target.is_relative_to(base.resolve()):
    return Errno.EACCES
```

## Choose where to mount

`Mount(provider, guest)` takes any guest path a grant may use, and also `/`. A mount at `/` makes your provider the guest's whole filesystem, except what a more specific grant or mount owns, and the standard library at `/usr/local/lib`. Relative paths then reach it. A mount at `/` is refused together with `root=`.

Mounts and grants nest either way, and no two share a guest path. The runner adds nothing to your listings. It makes no writable `HOME` in a mount: pass `HOME` in `env=` if you need one, at a folder no untrusted call writes.

A mount never serves the import path.

## Know the limits

Each limit has a default:

- **Provider calls.** `max_file_calls=` caps every provider call, whatever it answers. The default is `defaults().file_calls`, 10,000. The call that would pass it is not made: the run stops, and `trapped` is `"out of file calls"`, with `exit_code` and `fuel_used` `None`.
- **Open files.** At most `max_open_files` files and folders are open at once, 1,024 by default, counted with those in grants and the root. Mounts also hold at most 1,024 whatever the cap. The next open answers `EMFILE` without calling your provider.
- **Staged bytes.** The bytes of every open file plus every kept listing are at most `memory_bytes`. With `memory_bytes=None` the bound is 4 GiB. A `read` that would pass it answers `EFBIG`. Your provider should refuse a large file before it reads it: check the size in `stat` first.

Staged bytes are host memory, beside the guest's own. So a guest with a writable mount can hold three things at once in your process: up to `memory_bytes` of linear memory, up to `memory_bytes` of staged files, and one more copy of a staged file while your provider is handed it at a close. To budget host memory for many untrusted guests, count three times `memory_bytes` for each: about 3 GiB at the default.

## Know how a mount differs from a grant

A read-only mount answers as a read-only grant does: every write-type call is `EPERM`, before your provider is called. It differs in a few ways:

- A whole file is staged at open, so a 1-byte read stages the file.
- `os.fstat` of an open file shows its kind and size but no times. There are no links: `os.readlink` answers `EINVAL`.
- An open file's number (`f.fileno()`) is 2**30 or above, so `select.select` refuses it with `ValueError`. Use `selectors` or `select.poll`.
- `..` is resolved by text, so `missing/../a.txt` opens `a.txt`. A climb above the folder the call starts from is `EPERM`, as on a grant.
- A path over 4,096 bytes is `ENAMETOOLONG`.

## Mind time and threads

A provider runs synchronously on the thread that called `run`. Under `run_async` that is the worker thread, never the event loop's. Before each provider call the runner checks the call's `cancel` and its deadline; if either has passed, it does not call the provider.

Your provider's own time is outside the deadline and cannot be interrupted: bound its calls yourself. One provider may serve several calls at once, from each call's thread, so a shared provider must be thread-safe. An `async def` method is refused. To reach an async layer, call `asyncio.run_coroutine_threadsafe(coro, loop).result()` from the provider.

## Read the record

`done.files` is a `FileRecord`, or `None` for a call without mounts. It holds:

- `calls`, each method's count, zeros included;
- `faults`, the first 1,000 `FileFault(method, path, error)`, where `error` is the exception's type and first line, or `"bad answer: <type>"`;
- for writable mounts, `refused` and `refused_total` (below).

## Make a mount writable

`Mount(provider, guest, writable=True)` lets the guest create, write, append, truncate, make and remove folders, and rename within the mount. `writable` is keyword-only and must be `True` or `False`; any other value is a `TypeError`. A read-only mount never calls the write half.

A writable provider has five more methods. Each answers `None` for success or an `Errno`:

```python
class Store(Files):  # the read half above, plus:
    def write(self, path, data):  # the whole file; create it if missing
        if self.tree.get(path, b"") is None:
            return Errno.EISDIR
        self.tree[path] = data  # `data` is a bytes copy you may keep
    def mkdir(self, path):
        if path in self.tree:
            return Errno.EEXIST
        self.tree[path] = None
    def remove(self, path):  # a file; EISDIR for a folder
        ...
    def rmdir(self, path):  # an empty folder; ENOTEMPTY otherwise
        ...
    def rename(self, src, dst):  # POSIX's replace rule, within the mount
        ...

done = run(["-c", "import pandas as pd; pd.DataFrame({'a': [1]}).to_csv('/work/out.csv')"],
           mounts=[Mount(Store({}), "/work", writable=True)])
```

Each method keeps POSIX's contract in WASI's numbers. For example, `write` is `EISDIR` on a folder and `ENOENT` for a missing parent; `mkdir` is `EEXIST` when the path exists; `rmdir` is `ENOTEMPTY` for a folder that holds anything. Your own answers, such as `EACCES`, `ENOSPC` or `EDQUOT`, reach the guest unchanged.

**A file exists from its open.** A create or a truncation reaches you at open as `write(path, b"")`, so you see an empty first version of every file the guest creates. A create you refuse fails the guest's `open`.

**The bytes are handed over whole.** What the guest writes goes into a buffer the runner holds, with no provider call. The whole file reaches you as one `write(path, data)` when the guest closes it, at `os.fsync`, and at the call's ending, whatever ends it. So a refused write shows at the close or the `fsync`, not at the guest's `write`. Nothing is written back when `run` itself raises, such as on Ctrl-C.

**The record.** `done.files.refused` holds the first 1,000 `RefusedWrite` entries: every write-half call that did not succeed, and every write-back the runner owed but did not make. Each names the `mount`, `method`, `paths`, `errno`, `at` (`"open"`, `"call"`, `"close"`, `"sync"` or `"exit"`) and `cause` (`"refused"`, `"fault"` or `"limit"`). `refused_total` counts every one, so `len(refused) < refused_total` means the list was cut. Whether a refused write fails the run is yours to decide.

A writable mount differs from a writable grant in a few more ways:

- Unflushed writes are seen only through the descriptor that made them, until its close or `fsync`. Two descriptors on one path have two buffers, and the later write-back wins.
- A rename between a mount and another writable folder is `EXDEV`; `shutil.move` then copies and removes.
- `os.link` and `os.symlink` are `ENOTSUP`: the protocol has no links.
- `os.utime` of a name below the mount makes one `stat`. On a path that is there it succeeds and changes nothing; on a missing path it raises `FileNotFoundError`. Times are your provider's.
- sqlite3 over a mount is not supported. It needs ranged writes and locking.

**Cost.** Every write-half call, create and write-back counts toward `max_file_calls`. Each close or `fsync` of a changed file hands you the whole file. So a guest that loops "write one byte, `fsync`" can make many large write-backs. A provider that persists every write should limit its writes and answer `EDQUOT`.

**State across runs is yours.** A provider that keeps its state holds what a later run meets, including modules a later run could import and data files that change its answers. Give each untrusted program its own writable namespace, or check what it left. Writes at or under `/usr/local/lib` are always `EPERM`.

## On Windows

A writable grant answers as Windows does; a mount answers the same on every host. So on a Windows host:

- `os.rename` of a folder onto a file replaces the file on a grant. A mount never does, and answers `ENOTDIR`, as a Linux or macOS grant does.
- A grant cannot remove or rename a file the guest holds open. So `tempfile.TemporaryFile`, and an `os.replace` inside a `NamedTemporaryFile`'s `with` block, fail there and leave their `tmp…` file. A mount allows both.
- A grant cannot make a name with a colon (`FileNotFoundError`). Opening a folder for reading gives `OSError` `EINVAL`, where other hosts give `IsADirectoryError`.
- On every host, an errno is WASI's number, not Linux's: a missing path is `[Errno 44]` (`ENOENT`), where Linux says `[Errno 2]`. `open('')` answers `IsADirectoryError`, not `FileNotFoundError`.

If your guest code must behave the same on every host, serve its writable files from a mount. For the full list of platform differences, see *On Windows* on the [limitations page](../reference/limitations.md).

In one line: a mount is a provider you write, answering whole-file `stat`, `list` and `read` (and, when writable, five more methods), with every call counted and bounded.
