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
- **The release supply chain.** An artifact whose bytes differ from what its pins rebuild, or that fails attestation. The README's "Verifying a download" section shows how to check one.

## Upstream advisories the runner handles

The runner uses wasmtime-py 49.0.0, which bundles wasmtime 49.0.0; no wasmtime-py release yet carries a wasmtime past it. Two wasmtime advisories fixed since then reach a guest, and the runner carries each fix itself, on every call, until the published `wasmtime` requirement admits only fixed versions:

- **GHSA-m9f7-9w4p-gv38** (high, fixed in wasmtime 49.0.3): on macOS and FreeBSD, a guest with a writable grant or root could rename a symbolic link that points out with a trailing slash and so move a host folder into its sandbox. The runner applies 49.0.3's rule to `path_rename`: a trailing slash on either path needs a source that is a folder, judged without following its own link, and a folder is renamed by its plain name.
- **GHSA-96f6-r43r-8c24** (low, fixed in wasmtime 49.0.2): `fd_readdir` copied up to three bytes of host memory per entry into the guest. The runner zeroes them.

## Out of scope

- What the [security model](https://claygendron.github.io/wasi_python/explanation/security-model/) lists as not protected, such as disk use in a granted folder, timing side channels, or a guest planting files in a root that is reused.
- A bug in an upstream component (CPython, numpy, pandas, wasmtime) that does not cross the sandbox boundary. Please report it upstream; we will move our pin when a fix ships.
- What an embedder's own host function does with the frames it receives.
