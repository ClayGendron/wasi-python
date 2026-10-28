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

The runner uses wasmtime-py 50.0.1, which bundles wasmtime 50.0.0. That wasmtime carries the fixes of the three advisories below in its own calls, and the runner carries no fix of its own. An embedder who drives the artifact set with an older engine lacks them: before wasmtime 49.0.3 (or 48.0.6, or 36.0.18) for the rename, before 49.0.2 (or 48.0.4, or 36.0.17) for the listings, and 49.0.0 (or 47.0.0 to 48.0.2) for fuel. The build's wasmtime command line, 49.0.3, which `MANIFEST`'s `x-wizer` line names, only makes the snapshot from a read-only folder and runs no guest, so it is not the engine the sandbox runs on.

- **GHSA-m9f7-9w4p-gv38** (high, fixed in wasmtime 49.0.3, carried by wasmtime 50.0.0): on macOS and FreeBSD, a guest with a writable grant or root could rename a symbolic link that points out with a trailing slash and so move a host folder into its sandbox. wasmtime's own `path_rename` now needs a source that is a folder when either path ends in a slash, judged without following its own link.
- **GHSA-96f6-r43r-8c24** (low, fixed in wasmtime 49.0.2, carried by wasmtime 50.0.0): `fd_readdir` copied up to three bytes of host memory per entry into the guest. wasmtime now writes them as zeros.
- **GHSA-m63x-6p34-q65x** (medium, fixed in wasmtime 49.0.1, carried by wasmtime 50.0.0): the fuel cap and `fuel_used` under-counted work a guest does inside a C++ call that ends in a caught exception or a `longjmp`. An embedder that runs the artifact set with fuel on wasmtime 49.0.0, or 47.0.0 to 48.0.2, still meets it.

## Out of scope

- What the [security model](https://claygendron.github.io/wasi-python/explanation/security-model/) lists as not protected, such as disk use in a granted folder, timing side channels, or a guest planting files in a root that is reused.
- A bug in an upstream component (CPython, numpy, pandas, wasmtime) that does not cross the sandbox boundary. Please report it upstream; we will move our pin when a fix ships.
- What an embedder's own host function does with the frames it receives.
