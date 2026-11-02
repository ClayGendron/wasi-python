# Sessions

This page explains why a `Session` exists, why it is bounded, and why it keeps no more than it does. To use one, see [the sessions how-to](../how-to/sessions.md).

## Why sessions exist

A `run` starts a fresh instance, runs one program and throws the instance away. That is the cleanest isolation there is, but each call pays to start Python and to import what it uses. The snapshot pre-imports no package, so a call that uses pandas pays for `import pandas` every time.

A *session* keeps one instance alive across several calls, each a *turn*. Variables, functions, classes and imports made in one turn are there in the next, as in a Jupyter kernel or the interactive interpreter. A later turn costs a small fraction of a fresh `run`, and it pays for an import only once.

## Why a session is bounded

A live instance holds host resources for as long as it lives: its store, every file it has open (up to `max_open_files`), and its memory. Linear memory never shrinks, so a session holds its high-water mark until it ends. A session nobody closes would hold all of that forever.

So every session has bounds, with defaults:

- `idle_s`: it ends after resting this long (15 minutes by default);
- `lifetime_s`: it ends this long after it opened (1 hour by default), and no turn runs past it;
- `shutdown_s`: the time its closing shutdown may take (5 seconds by default).

The runner keeps these bounds, not the guest. They are host bookkeeping: a clock reading when the session opens and when each turn ends, checked when a turn is asked for, and by one reaper thread per process that ends sessions whose bound has passed. No timer runs in the guest, and the guest gains no new import for it.

Each turn also has its own fuel, deadline and output limit, re-armed before it starts. A turn that meets the memory cap gets a `MemoryError`, and the session goes on. The session keeps 256 KiB of its memory back, so a turn after one that filled the heap can still parse its code: it lets that go only when a turn's code, or its parse, meets a full heap, and takes it again at the next turn.

## Why a trap ends the session

A trap stops the interpreter in the middle of whatever it was doing, and skips its cleanup. After that, its state cannot be trusted. So a turn that traps or is stopped (out of fuel, past its deadline, cancelled) ends the session. An ordinary exception, a `sys.exit()`, truncated output or a `MemoryError` does not: those are Python's own outcomes, and the interpreter is still sound.

## Why it closes as Jupyter does

When a session is closed, or its bound passes while it rests, it runs Python's normal shutdown, as a Jupyter kernel does when it is shut down or culled: `atexit` handlers run, then the interpreter finalizes and flushes the files it closes. That shutdown is bounded by `shutdown_s` and, in a metered session, by its fuel; if either runs out, the session is simply stopped.

A session that ends by a trap or `os._exit` runs no shutdown. So write and close your files within a turn. The shutdown is a courtesy for a session closed at rest, not a guarantee.

## Why it keeps no more than it does

A session is not a shell and not a development environment. It runs the code you send it, one turn at a time, and keeps nothing once it ends. It has no argv and no stdin: a turn's input is its code. It ends with its process at the latest.

Two reasons keep it this small:

- **A session is one trust domain.** Every turn runs inside whatever earlier turns left. An earlier turn can hook `print` or the runtime itself and so read or rewrite what later turns do. A turn's result is only as trustworthy as the least trusted turn before it. Keeping sessions short-lived and separate keeps that risk contained. Open a new session for more trusted code.
- **State you want to keep belongs in files you control.** To carry state to a later session or `run`, write it to a writable grant and read it back. That state is then visible, in a folder you chose, and survives your process.

## In one line

A session trades a fresh instance per call for a live one across turns, so it is bounded in time, ends on a trap, closes as Python closes, and keeps nothing past its end.
