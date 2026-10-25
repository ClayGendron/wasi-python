## 49.0.4

Released 2026-10-19.

### Fixed

* wasi-http: Guests can add conflicting content lengths to messages [GHSA-r8xh-cgf7-392j](https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-r8xh-cgf7-392j)
* wasi-http p3: forwarded trailers aren't checked against `is_forbidden_header` hook [GHSA-jxcf-8qw5-5c33](https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-jxcf-8qw5-5c33)
* wasi-http p3: Guests can set incorrect content-length for spliced response bodies [GHSA-9prg-84vf-g5fc](https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-9prg-84vf-g5fc)
* Cranelift backend on aarch64 can jump to incorrect target on large Wasm `br_table` instruction [GHSA-mghf-wjfp-p5xm](https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-mghf-wjfp-p5xm)
* Update rustls to 0.23.46 [#14767](https://github.com/bytecodealliance/wasmtime/pull/14767)
*  Panic lowering a host-created component model stream into a guest that expects a different payload type. [GHSA-9pvw-hwfg-92h5](https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-9pvw-hwfg-92h5)


