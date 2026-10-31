# Support and versioning

This page says what the `wasi-python` wheel runs on, which names are public, and what a new release may and may not change. Read it before you depend on a name, or before you upgrade.

## What the wheel runs on

| | supported |
|---|---|
| Host Python | 3.11 or later. |
| WebAssembly engine | wasmtime-py 50 (`wasmtime>=50,<51`), installed with the wheel. |
| Host systems | macOS, Linux and Windows. The release is tested on all three. |
| Guest Python | CPython 3.15.2, for `wasm32-wasip1`. |

The runner must be able to read its own thread's stack size before it starts a guest. It can on Linux, Android, macOS and Windows. On other systems, FreeBSD among them, every call is refused with `RuntimeError`. On CPython 3.14.0 on a C library other than glibc (musl), every call is refused too; use 3.14.1 or later.

On Linux, install `faulthandler` and any crash reporter before your first call. A signal handler installed or removed after it makes every later call refuse with `RuntimeError`, because a guest trap could then end or hang your process.

## What the artifacts need from a host

The artifact set runs on any engine that supports WebAssembly's exception-handling proposal in its standard form (`exnref`, part of WebAssembly 3.0), plus multi-value and reference types (WebAssembly 2.0). Exception handling is what makes C++ exceptions work, and matplotlib needs them. An engine without it cannot load the binaries.

The project runs only wasmtime 50 itself. The list of other engines that run the binaries, and those that do not, is on [Embed from other languages](../how-to/embed-from-other-languages.md).

An older alpha, `0.1.0a1`, built on CPython 3.14.8, runs on hosts without exception handling: use the `v0.1.0a1` release's assets. On it a C++ `throw` ends the guest, it has no matplotlib, and the promises on this page do not cover it.

## The public surface

These are public, and covered by the promise below:

- the names that `wasi_python` and `wasi_python.tools` export (each module's `__all__`), listed in the [Python API](python-api.md) reference;
- the `wasi-python` command, its options and its JSON keys, listed in the [command-line reference](cli.md);
- the environment variables `WASI_PYTHON_ARTIFACTS` and `WASI_PYTHON_CACHE`;
- the tool protocol, which has its own version number, `PROTOCOL` (see the [tool protocol](tool-protocol.md)).

Everything else is internal and may change in any release: every other name, and the modules `wasi_python.runner`, `wasi_python.mounts` and `wasi_python.cli`.

## Version numbers

Versions are `0.MINOR.PATCH`. The promise starts at 0.1.0, the first final release. Alphas before it could change anything.

**A patch release** changes no public name, signature, field, default or command option.

**A minor release** may add:

- names;
- keyword-only arguments whose default keeps today's behaviour;
- dataclass fields placed last with a default, or keyword-only;
- `Errno` members and `stats()` keys;
- command options and JSON keys.

It removes or changes something only after a deprecation.

At 1.0 the same rules hold, with "major" in place of "minor".

## Deprecation

A deprecation comes as three things at once:

- a `DeprecationWarning`;
- a docstring that begins "Deprecated since 0.N: use X instead.";
- a line in the [changelog](changelog.md).

A thing deprecated in 0.N still works in 0.N and 0.N+1. 0.N+2 is the first release that may remove it.

Two kinds of change need no deprecation. Each is named in the changelog:

- a tighter default limit, in a minor release;
- a security fix, in any release.

## What is not promised

- Exceptions are promised by type, never by message.
- Messages, `repr`s and help text.
- wasmtime's trap names and error types. Of `trapped`'s values, only `"out of fuel"`, `"deadline"`, `"cancelled"` and `"out of file calls"` are promised.
- Timings and fuel counts.
- The `.cwasm` cache's location and format.
- The versions of the packages inside the guest. Each release pins one version of each; the [packages](packages.md) page lists them.

## Where releases are published

Each release is a GitHub release, with the wheel, the artifact set and their `SHA256SUMS`, and the `wasi-python` wheel on PyPI. See [Artifacts](artifacts.md) for what they hold and [Verify a download](../how-to/verify-a-download.md) for how to check them. The [changelog](changelog.md) lists every release's changes.

## In one line

Python 3.11 or later with wasmtime-py 50 on macOS, Linux or Windows; the names in `__all__`, the command and two environment variables are public, and a minor release removes nothing without two releases of deprecation.
