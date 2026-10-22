# Troubleshooting

This guide is keyed by what you see: an error inside the guest, a field of the result, or an
exception from `run`. Find the symptom, then apply the fix.

Remember the default first. A call with no arguments can read the stdlib and compute, but it has
no `/`, nothing writable, no network and no threads. Most surprises follow from that.

## `OSError` or `PermissionError` when the program writes

**What you see:** `open('x', 'w')`, `tempfile`, `np.save` or `df.to_csv('x.csv')` fails with
`OSError`. Or a write into a granted folder fails with `PermissionError`.

**Why:** by default nothing is writable. A grant is read-only unless it says `writable=True`, and
a read-only grant refuses every write with `EPERM`.

**Fix:** give the call somewhere to write.

- `root=True` gives a fresh, private, writable `/`, removed after the call.
- `Grant(folder, "/out", writable=True)` gives one writable host folder.

```python
from pathlib import Path

from wasi_python import Grant, run

data = Path.home() / "project" / "data"
done = run(
    ["-c", "import os; open('/out/n.txt', 'w').write(str(len(os.listdir('/data'))))"],
    grants=[Grant(data, "/data"), Grant("/tmp/job-17", "/out", writable=True)],
)
```

See [Grants](grants.md) and the [guest filesystem](../reference/guest-filesystem.md).

## A relative path is not found

**What you see:** `FileNotFoundError` for a path such as `data.csv`.

**Why:** with no root, the guest has no `/` and so no working folder.

**Fix:** use the absolute guest path of a grant (`/data/data.csv`), or give the call a root.

## A library cannot find a temporary or cache folder

**What you see:** `import matplotlib` raises `OSError` ("Matplotlib requires access to a writable
cache directory"). openpyxl's `save` raises `FileNotFoundError` ("No usable temporary
directory"). `df.to_excel(…)` raises `xlsxwriter.exceptions.FileCreateError`.

**Why:** these libraries write through `/tmp` or `HOME`, and neither is writable by default.

**Fix:** give the call a writable folder at `/tmp` (`Grant(folder, "/tmp", writable=True)`, or
`root=True`). For matplotlib, you can instead set `MPLCONFIGDIR` in `env=` to a folder inside a
writable grant. To write `.xlsx` with nothing writable, use xlsxwriter in memory:

```python
pd.ExcelWriter(buf, engine="xlsxwriter", engine_kwargs={"options": {"in_memory": True}})
xlsxwriter.Workbook(buf, {"in_memory": True})
```

See [matplotlib](matplotlib.md).

## `trapped` is `"out of fuel"`

**What you see:** `done.trapped == "out of fuel"` and `done.exit_code is None`.

**Why:** the program used the `fuel` cap you gave. *Fuel* counts the guest's executed
instructions. Imports count too, and so does the interpreter's finalization after the program's
last line. A cap that runs out there still stops the call, after the program's output was
written.

**Fix:** raise `fuel`, with room for finalization. Read `done.fuel_used` from a run that passed to
size the cap. See [Fuel](../explanation/fuel.md).

## `trapped` is `"deadline"`

**What you see:** `done.trapped == "deadline"`.

**Why:** the call ran past `deadline_s`, 60 seconds by default. Each call pays for its own
imports, since the snapshot pre-imports no package; `import pandas` is a large part of a small
job.

**Fix:** raise `deadline_s`, or pass `None` for no deadline. To pay an import once for several
steps, put the steps in one call, or use a [session](sessions.md), whose later turns keep what an
earlier turn imported.

## Output is missing after a stop

**What you see:** a trapped call's `stdout` lacks lines the program printed.

**Why:** output is buffered as CPython buffers it without `-u`. A program stopped by fuel, a
deadline or `os._exit` loses what it printed since its last flush.

**Fix:** add `-u` to the program's arguments, as you would for `python`, or flush before the end.

## `truncated` is not empty

**What you see:** `done.truncated == ("stdout",)`, and `stdout` ends early.

**Why:** a stream passed `output_bytes`, 16 MiB by default. The bytes past it were dropped.

**Fix:** raise `output_bytes`, or write large results to a writable grant and read the file on the
host.

## `EMFILE`: too many open files

**What you see:** an open inside the guest fails with `EMFILE`.

**Why:** the guest holds `max_open_files` files and folders open at once, 1,024 by default, across
grants, the root and mounts. The guest runs on after the refusal.

**Fix:** close files in the program, or raise `max_open_files`. Also check your own process's
soft descriptor limit: a guest's descriptors share your process's table, and macOS starts a
process at 256. Raise the soft limit at start:

```python
soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
```

See [Defaults and limits](../reference/defaults-and-limits.md).

## `trapped` is `"out of file calls"`

**What you see:** a call with mounts ends with `trapped == "out of file calls"`.

**Why:** it made more provider calls than `max_file_calls`, 10,000 by default. Every provider call
counts, whatever it answers.

**Fix:** raise `max_file_calls`, or pass `None`. See [Mounts](mounts.md).

## `ModuleNotFoundError` or `ImportError`

**What you see:** `import some_package` fails.

**Why:** the package is not in the artifact set. The guest cannot install packages and loads no
shared library.

**Fix:** check the [packages](../reference/packages.md) page. A pure-Python package can come from
a read-only grant named in `import_path=`. A compiled one cannot be added. Some modules are absent with the
platform, such as `resource`. `pytz` is not carried: use `zoneinfo`. See the
[limitations page](../reference/limitations.md).

## `RecursionError`, or `trapped` is `"stack overflow"`

**What you see:** `RecursionError` after 40 to 250 levels, where native Python allows 1,000.
Or the call ends with `trapped == "stack overflow"`.

**Why:** the guest has a fixed stack. Recursion that runs through Python code raises
`RecursionError` early. Some deep recursion in C, such as freeing a very deeply nested list,
still traps. A trap ends only that call.

**Fix:** make the recursion shallower, or iterate instead. See the
[limitations page](../reference/limitations.md).

## `RuntimeError: can't start new thread`

**What you see:** starting a thread, or a library that starts one, raises `RuntimeError`.

**Why:** the guest has no threads.

**Fix:** use the serial form. Many libraries already run serially here: joblib's `Parallel` and
scikit-learn's `n_jobs` give `n_jobs=1`'s result. For scipy, keep `workers` at its default, 1.

## Error numbers differ on Windows or from Linux

**What you see:** `[Errno 44]` for a missing file, where Linux says `[Errno 2]`. Or a program
that works on Linux and macOS fails on a Windows host.

**Why:** errno values inside the guest are WASI's, not Linux's. And a writable grant answers as
the host's file system does: on a Windows grant, a file the guest holds open cannot be removed or
renamed, so `tempfile.TemporaryFile` fails there.

**Fix:** compare with `errno` names or catch `FileNotFoundError`, never a number. For the Windows
differences, see *On Windows* on the [limitations page](../reference/limitations.md) and on
[Mounts](mounts.md); a mount answers the same on every host.

## `TypeError` or `ValueError` before anything runs

**What you see:** `run` raises at once.

**Why:** an argument has the wrong type or is out of range. A limit of `True`, a negative cap or a
deadline of 0 is refused, so no value can quietly remove a limit. A grant's guest path must be
absolute and not `/` or under `/usr/local/lib`. On Windows, a host path with a reserved name
(`CON`, `NUL`, `COM1` and the like) is refused.

**Fix:** correct the argument. See the [Python API](../reference/python-api.md).

## `RuntimeError` before the guest runs

**What you see:** `run` raises `RuntimeError` and no guest code ran.

**Why**, most often:

- the process was forked after it ran a guest; wasmtime does not support use across a fork;
- on Linux, `faulthandler`, `signal.signal` or a crash reporter was installed or removed after
  the first call;
- the host is CPython 3.14.0 on musl, or a system whose thread stack the runner cannot read.

**Fix:** start guests only after a fork (in gunicorn's `post_fork`, for example). Install
`faulthandler` and crash reporters before the first call. Use CPython 3.14.1 or later on musl.

## `ArtifactsMissing`

**What you see:** `run` raises `ArtifactsMissing`.

**Why:** the runner found no artifact set: not at `$WASI_PYTHON_ARTIFACTS`, not in a source
checkout's `build/artifacts/`, and not in the wheel.

**Fix:** install the released wheel (`pip install wasi-python`), or point `WASI_PYTHON_ARTIFACTS`
at a folder holding the set and its `MANIFEST`. See [Artifacts](../reference/artifacts.md).

## `SessionEnded`

**What you see:** `Session.run` raises `SessionEnded`.

**Why:** the session has ended. `session.ended` says why: `"idle"`, `"lifetime"`, a turn that
called `exit()`, or a turn that was stopped (its `trapped`).

**Fix:** open a new session. See [Sessions](sessions.md).

## In one line

Most errors come from the default sandbox (nothing writable, no threads, no network) or a limit;
grant a folder, raise the limit, or check the packages and limitations pages.
