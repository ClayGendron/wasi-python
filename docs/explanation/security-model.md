# Security model

wasi-python is made for running code nobody reviewed, such as code a model wrote. This page explains what the sandbox enforces, what it does not protect, and how to report a way around it.

A *guest* is the Python program running inside `python.wasm`. The *host* is your program, which calls `run` or `Session`. A *root* is the folder the guest sees at `/`; a *grant* is a host folder you hand to the guest at a path of your choice.

## The policy in three sentences

- Code planted in a root never runs at start-up or on import in a later call, on either binary.
- Data planted in a root that a caller reuses is read by later calls, and only a fresh root closes that.
- A call that names no limit still has one.

## What is enforced

### The guest sees only what you give it

- The guest sees only its root and its grants. It sees no host path, cannot climb out with `..`, and cannot follow a symbolic link out: such an open is refused.
- By default the guest has nothing writable: no `/`, no `/tmp`, and a `HOME` it cannot write. It can import, compute, print, read the standard library and call the door. `root=True` gives it a fresh private folder at `/`, removed afterwards.
- Grants are read-only unless you pass `writable=True`. They are checked before any work, and checked again after wasmtime opens them.
- The stdlib zip is a read-only grant on every call. The runtime's own files are never in a writable grant, and the runner refuses a **writable** grant or root over any module cache it knows of.
- Mounts are read-only unless you pass `writable=True`. No host path is opened for a mount, so nothing a guest writes reaches a host file through one; every write goes to the runner's buffer or to your provider.
- The guest does not see your process's environment. It starts from `TMPDIR=/tmp`, `PYTHONTZPATH=` and a fresh `HOME`, and `env=` is laid over them.

### Two channels to the host, and no others

- The guest imports two things only: the WASI preview1 calls and the one door, `host::call`.
- It has no network, no processes and no shared libraries. Starting a thread raises `RuntimeError`.
- Every door frame is bounded by guest memory. Nothing a frame does makes `run` raise, and an `Exception` your host function raises reaches the guest as an error with none of your text.
- Tool-protocol frames that are too deep, too large or malformed are refused before they are parsed.

### Nothing planted runs at start-up

- Only the stdlib zip and the read-only entries you name are on the import path.
- `site` does not run, so modules, `.pth` files or a `pyvenv.cfg` planted in a root never run. `exit`, `quit`, `help` and `license` still exist, as in native Python.
- `env=` may not set a key that begins with `_PYTHON_`: CPython's `sysconfig` reads these in isolated mode, and one, `_PYTHON_SYSCONFIGDATA_PATH`, runs the module it names, so a call raises `ValueError` before any work.

### Every call has limits

- **Defaults.** 1 GiB of memory, a 60-second deadline, 16 MiB of output per stream, and 1,024 files open at once. Output past the cap is dropped and named in the result's `truncated`; an open past the file cap answers `EMFILE` and the guest runs on. `wasi_python.defaults()` returns them, and `None` removes a limit.
- **No quiet removal.** A limit of the wrong type or out of range (a negative cap, `True`, a deadline of 0) raises `TypeError` or `ValueError` before any work.
- **Waiting counts.** The deadline holds while the guest sleeps or waits in `select`: the runner answers those waits itself, in slices that stop at the deadline.
- **Fuel.** An optional cap on executed instructions, the same on every machine. See [fuel](fuel.md).
- **Deep recursion** through Python code raises `RecursionError`. The guest runs on a thread of the runner's own with 8 MiB of wasm stack, checked before any wasm runs.
- **Inputs are checked.** `argv`, `env` and `stdin` that the guest would see differently (a NUL, text that is not UTF-8, an `=` in an env key) raise `ValueError` before any work. No message quotes a value.

[Defaults and limits](../reference/defaults-and-limits.md) lists every limit.

### A call cleans up after itself

- Each call's store is closed when it ends, trapped or not, so its memory and open files are released at once.
- A call's folders go with it, whatever the guest built in them. The private root, the stdin folder and the fresh `HOME` are removed by a walk that never follows a link. A folder that cannot be removed is named in one `RuntimeWarning` per process, and a private folder is retried by a later call.
- Calls made through `run` share nothing but the stdlib zip's folder, which each sees read-only. Each call's output goes to its own buffer.

### A guest trap cannot take down your process

- A *trap* is the guest stopping on an error the wasm engine catches, such as running out of fuel or overflowing its stack. A trap ends the call, not your process.
- On Linux, a trap could end or hang your process if wasmtime's signal handlers were replaced after the first call (by `faulthandler`, `signal.signal` or a crash reporter). So each entry into the guest is refused with `RuntimeError`, before guest code runs, when that has happened. Install `faulthandler` and crash reporters before your first call.

### Three wasmtime fixes, in wasmtime itself

The pinned wasmtime-py bundles wasmtime 50.0.0. Three advisories fixed in wasmtime 49 releases reach a guest, and wasmtime 50.0.0 carries each fix in its own calls; the runner adds none:

- **GHSA-m9f7-9w4p-gv38** (fixed in wasmtime 49.0.3): on macOS and FreeBSD, a guest with a writable grant or root could rename a link that points out, with a trailing slash, and so move a host folder into its sandbox. wasmtime's rename refuses it.
- **GHSA-96f6-r43r-8c24** (fixed in wasmtime 49.0.2): directory listings copied up to three bytes of host memory into the guest. wasmtime writes zeros.
- **GHSA-m63x-6p34-q65x** (fixed in wasmtime 49.0.1): fuel did not count work inside a C++ call that ends in a caught exception, so a guest could run past its fuel cap. wasmtime counts it.

wasmtime's advisories of 2026-10-19, fixed in wasmtime 49.0.4, do not reach the runner: wasmtime 50.0.0 is outside the critical GHSA-mghf-wjfp-p5xm's range, and the rest are in parts of wasmtime the runner does not use.

These fixes live in the engine, not in the artifact set. An embedder that drives the artifacts with its own wasmtime before 49.0.3 does not get them all.

## What is not protected

The sandbox stops the guest reaching what it was not given. It does not make everything you give it safe, and it does not police your own process. These are outside its promise.

### Your disk and your folders

- **Disk use in any root**, the private one included. A guest can write as fast as the disk takes it until its deadline: tens of GiB in the default 60 seconds. Point `root`, or `tempfile.tempdir`, at a size-limited volume if that matters.
- **Links a guest leaves in a granted root that point outside it.** The guest cannot follow them, but your code can. Host code that reads or writes a root after a call must not follow links: open with `O_NOFOLLOW`, or check `os.lstat` first.
- **A killed process.** If your process is killed mid-call, its private root and stdin folder stay in the temporary folder. The stdlib zip's folder and its lock file stay too, once a call has run. The next process that uses wasi_python on the same machine, with the same temporary folder, removes them at its first call.
- **A folder a removal had to leave**, such as content the host made read-only, or a file another program holds open, until a removal can.
- **On Windows**, a file the host gave the read-only attribute, inside a writable grant or a root: the guest can delete it.
- **A special file swapped in during an open.** A guest's open of a FIFO, socket or device file in a granted folder is refused with `ENXIO`, but a host process, or another call writing the same grant, that replaces a name between the runner's look and the open can still make that open wait in the host past the deadline and `cancel`, and `Session.close()` with it. Grant only folders whose contents you control.

### Reused roots and state across calls

- **Data planted in a reused root.** A later call reads what an earlier call left: any user file, matplotlib's `matplotlibrc` in the working folder, libxml2's `/etc/xml/catalog`, dateutil's zone files, `mimetypes`' tables, a `.pdbrc` that pdb runs when a program starts pdb. A script or module you name to run from a reused root is the same. A fresh root closes all of these.
- **An `env=` that overrides `HOME`, `PYTHONTZPATH` or `SCIKIT_LEARN_DATA`** on a reused root, or into a writable grant or mount that a later call reuses. scikit-learn's cached datasets are pickles, so that folder's contents are code.
- **Writable grants and imports across calls.** Granting a folder writable in one call and importing from it in another runs whatever the first call left there.
- **Concurrent calls on one root**, or a guest that can write a folder above another call's root. One can change the files the other uses.
- **Everything a turn leaves in a session** for the turns after it. A session is one trust domain: never send a more trusted turn after less trusted code in the same session. See [sessions](sessions.md).

### Your process's own resources

- **The module cache's contents**, if anything but the runner can write there. The cache holds native code. `cache_dir`, `$WASI_PYTHON_CACHE` and the artifact folder are trusted input: name only folders that no guest and no other user can write. The runner trusts every folder on the way to its cache to be yours, so running it with another user's home (under `sudo` keeping `HOME`, or in a container or CI step with a mapped or shared home) is not supported: run it with your own home, or set `$WASI_PYTHON_CACHE` to a folder of yours. On POSIX the runner uses a cache only when every folder on the way to it is yours, root's or the owner of `/`'s and no one else can write it, and it loads a compiled module through the descriptor it checked, where the system names one (else by path, with the name checked again after); on Windows the grant rule is the guard, and the file is held open from its check until it is loaded. A cache that fails is not used: the module is compiled in memory, with one warning, and the call still runs. The owner of `/` is trusted on that way as root is, since whoever owns `/` can already replace every folder below it on its own file system; some container hosts give `/` to a uid of their own.
- **A saved snapshot's file**, if a guest or another user could write it before you load it. Its image runs as your code in every call made from it, with that call's grants, door and tools. Keep it where no guest is granted writing, in this process or any other. On POSIX the runner loads only a file that only you can write, through a folder no other user can change. On Windows it checks only that the file is not a link and has one name.
- **File descriptors beyond each call's cap.** A guest's descriptors share your process's table. The cap protects your process only while the process's soft descriptor limit is above the cap plus what the process already holds, for every call and session open at once. Raise the soft limit at start, or set `max_open_files` lower.
- **A session's files and memory**, which it holds for its whole life. Give untrusted code a short `idle_s`.
- **Host CPU spent on tool frames**, within the request-byte budget and `max_tool_calls`.
- **Other code in the same process** that uses wasmtime-py directly. A process that compiled a module through wasmtime-py itself must not fork and run a guest in the child: the child waits for the parent's compile pool for good, before any deadline applies.
- **What your own host function, provider or tool does** with the requests it receives. That code runs in your process, with your process's power.
- **On Linux, a signal-handler change made during a call**, by a host function or another thread. The next call is refused.

### Time, randomness and hashing

- **Timing.** The guest's clock is real and fine-grained.
- **Real entropy.** `random`, `secrets`, `os.urandom` and `tempfile` use real randomness. SQLite's own randomness is seeded from the clock's whole second, because the guest has no `/dev/urandom`.
- **Dict and set keys built to collide** under the snapshot's fixed, public string-hash key, and XML parsed by Python's expat parsers (`xml.etree`, `xml.dom.minidom`, `xml.sax`, `plistlib`, `xmlrpc`), whose parser salt is the same fixed key. They make that call's dict, set and XML work quadratic until its deadline. Load untrusted keys and XML with `snapshot=False`, whose key is fresh in every call.
- **A guest that waits with `deadline_s=None`.** No instruction runs while it sleeps, so fuel does not stop it.

### Other edges

- **lxml XSLT without `access_control`.** A stylesheet, or a document it loads, can read any file in the call's grants and write into its writable grants. Use `XSLTAccessControl.DENY_ALL` for untrusted stylesheets.
- **Recursion in C over very deep data**, past the documented depths, ends the call with a stack-overflow trap. The next call is unaffected.
- **`stdin`**, which is written to a host temporary file of its size.
- **The exit status**, which is one byte, as a POSIX process's is.

The [limitations page](../reference/limitations.md) covers what does not work in the guest at all, which is a different question from what is protected.

## Reporting a vulnerability

A way out of the sandbox, or around one of its limits, is a vulnerability. Report it privately through GitHub: open the repository's **Security** tab, then choose **Report a vulnerability**. Do not open a public issue for a security problem.

Include what you ran, what happened, and what you expected. A reproducer that uses `wasi_python.run` or the release's `python.wasm` is the most useful. A fix is released as soon as it is ready, and the advisory credits you unless you ask otherwise. Only the newest release is supported.

### What counts as a vulnerability

- **The sandbox boundary.** A guest that reaches a host file outside the folders it was given, the network, a host process or host memory, through the WASI calls or the door.
- **The limits.** A guest that runs past its deadline, fuel, memory or output cap, or a call that keeps host resources after it ends.
- **The runner.** Anything a guest does that makes `wasi_python.run` raise, crash the host process, or return another call's result; or an argument that silently removes a limit or changes what the guest sees.
- **The release supply chain.** An artifact whose bytes differ from what its pins rebuild, or that fails attestation. Every build input and test source is accepted by its pinned SHA-256, whichever host served it, the copies this project keeps among its release assets included. [Verify a download](../how-to/verify-a-download.md) shows how to check one.

### What does not

- What this page lists under [What is not protected](#what-is-not-protected).
- A bug in an upstream component (CPython, numpy, pandas, wasmtime) that does not cross the sandbox boundary. Report it upstream; the project moves its pin when a fix ships.
- What an embedder's own host function does with the frames it receives.

The full policy is in [SECURITY.md](https://github.com/ClayGendron/wasi-python/blob/main/SECURITY.md).

## In one line

The guest sees only what you grant, writes nothing by default, reaches the host through WASI and one door, and always has limits; what you grant it, and your own process, remain yours to protect.
