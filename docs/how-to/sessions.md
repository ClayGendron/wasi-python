# Run several turns in a session

This guide shows you how to keep one guest interpreter across several calls with a `Session`: how to open it, run code in it, know what it keeps, and close it.

A *session* is one instance of the runtime kept across several calls. Each call is a *turn*. Variables, functions, classes and imports made in one turn are there in the next. A turn costs a small fraction of a fresh `run`, and later turns do not pay again for what an earlier turn imported. A session is not a shell: it runs the code you send it, one turn at a time, and keeps nothing once it ends.

## Open a session and run turns

```python
from wasi_python import Grant, Session

with Session(grants=[Grant("data", "/data")]) as session:
    session.run("import pandas as pd; df = pd.read_csv('/data/sales.csv')")
    done = session.run("df.groupby('region').total.sum()")
    done.stdout          # the echoed Series
    session.ended        # None: it can run more turns
```

`Session` takes the same arguments as `run`, except `argv`, `stdin` and `cancel`, plus three bounds of its own: `idle_s`, `lifetime_s` and `shutdown_s`. `session.run(code)` runs one turn and returns a `Completed`, as `run` does. From async code, use `await session.run_async(code)`.

## Know how a turn runs

A turn runs in `__main__`, as the interactive interpreter runs it and as a Jupyter kernel runs a cell:

- **A final expression is echoed.** `df.head()` as the last line prints it.
- **An exception is reported** with its traceback, which names `<turn N>` and shows the turn's source lines. The turn's `exit_code` is 1, and the session goes on.
- **`sys.exit(n)` is reported** as the turn's `exit_code`, and the session goes on.
- **`exit(n)` and `quit()` end the session.** The turn stops at that line and returns its status; then the session runs Python's shutdown and ends with `ended == "quit"`.
- **`os._exit(n)` ends the session at once**, with no shutdown.

A session has no argv and no stdin: a turn's input is its code, and `sys.stdin.read()` returns `""`. Turns of one session run one at a time. A second turn while one runs raises `RuntimeError`.

## Know what is per session and what is per turn

| argument | scope |
|---|---|
| `root`, `grants`, `mounts`, `import_path`, `env`, `host`, `tools`, `gate`, `snapshot`, `artifacts`, `cache_dir` | per session: fixed when it opens |
| `memory_bytes` | per session: memory never shrinks, so a session holds its high-water mark |
| `max_open_files` | per session: the cap counts what all its turns and its shutdown hold open |
| `idle_s`, `lifetime_s`, `shutdown_s` | per session: they bound the session and its ending |
| `fuel`, `deadline_s`, `output_bytes` | per turn: the session's value is each turn's default, and `session.run(code, fuel=…)` may pass its own |
| `max_file_calls`, `max_tool_calls`, `max_tool_request_bytes` | per turn, set once on the session: each turn gets the full allowance |
| `cancel` | per turn only |

`Session(fuel=N)` opens a *metered* session, whose turns each get `N` instructions of fuel. `Session()` is unmetered, and its turns report `fuel_used=None`.

## Know how a session ends

A session ends at the first of these. `session.ended` then says which, and every later turn raises `SessionEnded`, whose `reason` is the same:

| cause | `ended` |
|---|---|
| `close()`, or leaving the `with` block | `"closed"` |
| it rested longer than `idle_s` (default 900 s, 15 minutes) | `"idle"` |
| `lifetime_s` passed since it opened (default 3,600 s, 1 hour) | `"lifetime"` |
| a turn called `exit()` or `quit()` | `"quit"` |
| a turn called `os._exit` | `"exit"` |
| a turn trapped or was stopped | the turn's `trapped`, such as `"out of fuel"`, `"deadline"`, `"cancelled"` or `"out of file calls"` |
| `run` raised in your process after the guest started, such as on Ctrl-C | `"error"` |

A turn's exception, its `sys.exit()`, a truncated output and a `MemoryError` do not end a session. No turn starts at or after the lifetime, and each turn's deadline is capped at the lifetime left. The runner keeps these bounds, not the guest.

## Close it, and write files within a turn

When a session is closed, or its idle bound or lifetime passes while it is at rest, it runs Python's normal shutdown, as a Jupyter kernel does: `atexit` handlers run, then the interpreter is finalized, which flushes the files it closes. The shutdown has `shutdown_s` seconds (default 5; 0 skips it) and, in a metered session, the session's `fuel`. If either runs out, the session is simply stopped. `session.shutdown_outcome` then says `"finished"`, `"stopped"` or `"skipped"`. `close()` waits for the ending.

A session that ends by a trap, `os._exit` or a stop runs no shutdown. So **write and close files within a turn**: the shutdown is a courtesy for a session closed at rest, not a guarantee.

The shutdown costs fuel: tens of millions of instructions, and hundreds of millions after importing pandas. Size a metered session's `fuel` to cover it.

## Keep state beyond the session

A session ends with its process at the latest. To keep state for a later session or `run`, write it as files to a writable grant and read them back:

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

`df.to_csv` and `json.dump` work the same way. Parquet does not, since pyarrow is not built. Only a guest may unpickle what a guest wrote: never unpickle a guest's file on the host.

## Keep trust levels apart

A session is one trust domain. An earlier turn can hook `builtins`, `print` or the runtime's own module, and so read every later turn's source, rewrite what it prints, or make it report exit 0. A secret any turn put in the guest stays readable for the rest of the session. Never send a more trusted turn, such as a check whose exit code you believe, after less trusted code in the same session: open a new session for it.

While it is open, a session holds on the host its store, every file its guest opened, up to `memory_bytes` of memory and up to `memory_bytes` of mount staging. For untrusted code, give a short `idle_s` and call `close()` promptly.

For why a session is bounded this way, see [Sessions](../explanation/sessions.md).

In one line: `with Session(...) as session:` keeps one interpreter across `session.run` turns, within an idle bound and a lifetime, and you write files within a turn to keep them.
