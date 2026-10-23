# Fetched-source notes (2026-10-18)

Files beside this one:

- `pypi-wasmtime.json`, `pypi-wasmtime.txt`: PyPI's JSON for `wasmtime` (EXECUTED, `curl`, parsed with `python3 -I`). Latest 49.0.0, uploaded 2026-09-21; 11 wheels of 7.2 to 9.9 MB (macOS x86_64 and arm64, manylinux1 x86_64, manylinux2014 aarch64, musllinux x86_64 and aarch64, win_amd64, win_arm64, android arm64 and x86_64, and a `py3-none-any`).
- `wasmtime-releases.txt`: `gh api repos/bytecodealliance/wasmtime/releases` (EXECUTED).
- `wasmtime-py-tags.txt`, `wasmtime-py-tag-dates.txt`: wasmtime-py's tags and their dates (EXECUTED, `gh api`).

Web pages read (READ, via WebFetch, 2026-10-18):

- crates.io limit: https://doc.rust-lang.org/cargo/reference/publishing.html says "crates.io currently has a 10MB size limit on the `.crate` file."
- napi-rs distribution: https://napi.rs/docs/deep-dive/release . The root package lists the per-platform packages in `optionalDependencies`; each declares npm `os`, `cpu` and `libc`; "No compiler or install-time download script is required on the consumer's machine."
- napi-rs runtimes: https://napi.rs/docs/more/support-compatibility . CI "exercises Node.js 22, 24, and 26"; Bun is best effort, "Bun failures do not block napi-rs releases"; Deno: "Do not infer Deno support from Node-API compatibility alone." Template-backed prebuilt targets: macOS x64 and arm64; Windows MSVC x64, x86, arm64; Linux glibc x64, arm64, armv7; Linux musl x64, arm64; Android arm64, armv7; FreeBSD x64; threaded WASI preview 1.
- wasmtime_wasi::p1: https://docs.rs/wasmtime-wasi/latest/wasmtime_wasi/p1/index.html . `WasiP1Ctx`, `add_to_linker_sync` "adds synchronous versions of all WASIp1 functions"; "WASIp1 is not as extensible or configurable as WASIp2"; the p2 implementation underneath is "just an internal implementation detail".
- WasiCtxBuilder (49.0.3): https://docs.rs/wasmtime-wasi/latest/wasmtime_wasi/struct.WasiCtxBuilder.html . `preopened_dir(host_path, guest_path, FsPerms)`; `stdout(impl StdoutStream)`; `allow_blocking_current_thread`.
- wasmtime::Store: https://docs.rs/wasmtime/latest/wasmtime/struct.Store.html . `set_fuel`, `get_fuel`, `set_epoch_deadline`, `epoch_deadline_callback(FnMut(StoreContextMut) -> Result<UpdateDeadline>)`, `limiter(impl FnMut(&mut T) -> &mut dyn ResourceLimiter)`.
- PyO3 abi3: https://pyo3.rs/latest/building-and-distribution.html . abi3 "allows their wheels to be used on multiple Python versions"; "restricts the functionality they can use"; maturin "is able to build manylinux-compliant wheels out-of-the-box".
- wasmtime GitHub releases page: latest v49.0.3 (2026-10-14); v50.0.0-rc.1 (2026-10-05); no v50.0.0 or v51 yet.
- wasmtime-py GitHub releases page: "There aren't any releases here" (it uses tags only).
