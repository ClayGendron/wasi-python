# Security policy

wasi_python is a sandbox: people use it to run code they do not trust. A way out of the sandbox, or around one of its limits, is a vulnerability.

## Reporting

Please report privately through GitHub: the **Security** tab of this repository, then **Report a vulnerability**. Do not open a public issue for a security problem.

Include what you ran, what happened, and what you expected. A reproducer that uses `wasi_python.run` or the release's `python.wasm` is the most useful. A fix is released as soon as it is ready, and the advisory credits you unless you ask otherwise.

## Supported versions

Only the newest release is supported; a fix goes into the next release, and older releases are not patched.

## In scope

- **The sandbox boundary.** A guest program that reaches a host file outside the folders it was given, the network, a host process, or host memory. The same for any way out through the WASI calls or the host door (`host::call`).
- **The limits.** A guest that runs past its deadline, fuel, memory or output cap, or a call that keeps host resources after it ends.
- **The runner.** Anything a guest does that makes `wasi_python.run` raise, crash the host process, or return another call's result. The same for an argument that silently removes a limit or changes what the guest sees.
- **The release supply chain.** An artifact whose bytes differ from what its pins rebuild, or that fails attestation. [Verify a download](https://claygendron.github.io/wasi-python/how-to/verify-a-download/) shows how to check one.

## Upstream advisories

The runner uses wasmtime-py 51.0.0, which bundles wasmtime 51.0.0. That wasmtime carries the fixes of the five advisories below in its own calls, and the runner carries no fix of its own. The build's wasmtime command line, 51.0.0, is on the runner's line and only makes the snapshot, from a read-only folder; it runs no guest, so it is not the engine the sandbox runs on.

- **GHSA-f2pq-268w-886c** (high, fixed in wasmtime 50.0.3, carried by wasmtime 51.0.0): on Windows, a guest could reach host files outside its folders with a name such as `/usr/local/lib/C:secret`, which Windows reads against drive C's current folder. It reached wasi-python 0.1.5 and earlier on Windows in every call: a guest read a file outside its folders through the runner's own read-only folders, with no folder granted, and could write there through a writable grant or `root=True`. wasmtime now refuses a `:` in any path on Windows. An embedder who drives the artifact set with its own wasmtime needs 51.0.0, 50.0.3, 49.0.7, 48.0.10 or 36.0.22 or later on its line.
- **GHSA-5m8g-xhq4-4h93** (moderate, fixed in wasmtime 50.0.2, 49.0.6, 48.0.9 and 36.0.21, carried by wasmtime 51.0.0): empty writes to a custom output stream could grow host memory without bound. It did not reach the runner. The runner uses such a stream on Windows, but a guest's `fd_write` skips every empty buffer before it calls the stream.
- **GHSA-m9f7-9w4p-gv38** (high, fixed in wasmtime 49.0.3, carried by wasmtime 51.0.0): on macOS and FreeBSD, a guest with a writable grant or root could rename a symbolic link that points out with a trailing slash and so move a host folder into its sandbox. wasmtime's own `path_rename` now needs a source that is a folder when either path ends in a slash, judged without following its own link. An embedder's engine needs 49.0.3, 48.0.6 or 36.0.18 or later.
- **GHSA-96f6-r43r-8c24** (low, fixed in wasmtime 49.0.2, carried by wasmtime 51.0.0): `fd_readdir` copied up to three bytes of host memory per entry into the guest. wasmtime now writes them as zeros. An embedder's engine needs 49.0.2, 48.0.4 or 36.0.17 or later.
- **GHSA-m63x-6p34-q65x** (medium, fixed in wasmtime 49.0.1, carried by wasmtime 51.0.0): the fuel cap and `fuel_used` under-counted work a guest does inside a C++ call that ends in a caught exception or a `longjmp`. An embedder that runs the artifact set with fuel on wasmtime 49.0.0, or 47.0.0 to 48.0.2, still meets it.

wasmtime's other seven advisories fixed in 50.0.2 do not reach the runner, and 51.0.0 carries them too. Four are about the GC proposal's heap or a wasmtime built without a feature: the runner's host functions take and return only numbers, it sets none of the heap options they need, and wasmtime-py's library is built with both features. One is a panic when a host function is called from outside wasm, which the runner never does. The other two are in the component model and `wasi-http`, which the runner does not use.

wasmtime's advisories of 2026-10-19, fixed in wasmtime 49.0.4, do not reach the runner either. GHSA-mghf-wjfp-p5xm (critical) is a wrong jump on aarch64 for a `br_table` with more than about 256,000 targets, in a module the attacker writes. wasmtime 51.0.0 is outside its vulnerable range, and the largest `br_table` in `python.wasm` and in the snapshot has 3,203 targets. GHSA-r8xh-cgf7-392j, GHSA-jxcf-8qw5-5c33, GHSA-9prg-84vf-g5fc and GHSA-9pvw-hwfg-92h5 are in `wasi-http` and the component model, which the runner does not use.

## Out of scope

- What the [security model](https://claygendron.github.io/wasi-python/explanation/security-model/) lists as not protected, such as disk use in a granted folder, timing side channels, or a guest planting files in a root that is reused.
- A bug in an upstream component (CPython, numpy, pandas, wasmtime) that does not cross the sandbox boundary. Please report it upstream; we will move our pin when a fix ships.
- What an embedder's own host function does with the frames it receives.
