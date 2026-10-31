# orjson on PyO3 as a builtin: a spike

- **Status:** research, 2026-10-31; the spike the owner chose on 2026-10-30 (`decisions.md`, "The scope of 0.1.3": orjson as the PyO3-on-wasip1 pathfinder toward pydantic and fastparquet). Nothing in `src/`, `recipes/`, `scripts/`, `tests/` or `downloads/SHA256SUMS` changes with this memo.
- **Date:** 2026-10-31
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), a spike sub-agent of the orchestrating session.
- **Evidence:** a scratch folder, `build/orjson-spike/` in the worktree of branch `research/orjson-on-pyo3` (from `dev` `ae695e15`), git-ignored and not kept. The link read the main tree's build of 2026-10-21 (CPython 3.15.0, wasi-sdk 34) and wrote only to the scratch folder. Downloads, each fetched once and checked against PyPI's SHA-256: `orjson-3.13.0.tar.gz` (`d1de5eb0…`), `pydantic_core-2.50.2.tar.gz` (`1b0e8dc3…`), `cramjam-2.14.0.tar.gz` (`05009538…`), and Rust 1.99.1 through rustup into the scratch folder (rustup checks each component against its channel manifest's SHA-256).
- **Stands on:** `2026-10-30-what-0-1-3-could-carry.md` §3 (the PyO3 paragraph; PyO3's CI on wasip1 against 3.15, https://github.com/PyO3/pyo3/pull/6340, READ there and not re-read here); `scripts/steps/60_link.sh`; `scripts/gen_inittab.py`; `tests/harness/constructors.py`; `scripts/weak_duplicates.py`; `src/wasi_python/_call.py` (`_trap_name`).

Labels: EXECUTED means run here; READ means read from a file, cited; INFERRED means the researcher's reasoning.

## The short version

1. **It builds.** orjson 3.13.0 compiles for `wasm32-wasip1` as a static library with Rust 1.99.1, against this build's CPython 3.15, in about 6 seconds at `-j 2`. PyO3 needs one eight-line config file; no `PYO3_CROSS_*` variable. EXECUTED.
2. **It links, with one silent hazard.** The library brings Rust's own libm and compiler-rt. Linked as cargo writes it, those replace wasi-libc's `cbrt`, `fma`, `sqrt` and the `long double` and complex helpers for the whole interpreter, with no warning, and the weak-duplicate gate does not see it. Keeping only orjson's two objects fixes it. EXECUTED.
3. **It runs.** `import orjson; orjson.dumps(...)` works in the guest, under the wasmtime CLI and under the runner with a fresh snapshot. A Rust panic prints its message to stderr and ends as the trap `unreachable`. EXECUTED.
4. **It is cheap.** The interpreter grows by 316,962 bytes (0.32 %); imports, tags, constructors and target features do not change. The toolchain is 556 MiB installed. Two builds from two paths gave the same bytes. EXECUTED.
5. **Two Rust libraries cannot sit side by side.** Two static libraries collide on Rust's standard library. One combined crate (an *umbrella*: a crate whose only job is to depend on every Rust module) links and runs. EXECUTED. pydantic-core already ships as an rlib and fits the umbrella; cramjam bundles C copies of bzip2 and liblzma, which this interpreter already links. READ, INFERRED.

Recommendation: **a specification for 0.1.4** for orjson alone, reviewed before it is built (it changes the build recipe and adds a toolchain). pydantic-core is **more research** after that. cramjam is **not yet**.

## 1. Does it build? (EXECUTED)

orjson's current release is 3.13.0 (PyPI, 2026-10-07; classifiers up to 3.15). READ. Its sdist vendors all 22 crates under `include/cargo/` with a `.cargo/config.toml` that points cargo there, so the build fetches nothing from crates.io. EXECUTED.

The toolchain: rustup's `stable` resolved to rustc 1.99.1 (2026-10-13). It went into the scratch folder (`--profile minimal --target wasm32-wasip1`), not the system. orjson asks for Rust 1.95 or later.

What PyO3 needs. orjson uses `pyo3-ffi` (the raw bindings) and `pyo3-build-config` 0.29.3, not PyO3's macros. `pyo3-ffi` 0.29.3 supports CPython up to 3.15. One file, named by `PYO3_CONFIG_FILE`, replaces every cross-compile variable:

```
implementation=CPython
version=3.15
shared=false
abi3=false
lib_name=python3.15
pointer_width=32
build_flags=
suppress_build_script_link_lines=true
```

PyO3 read it as `target_abi=CPython-gil_enabled-3.15`. abi3 is off, so orjson uses the full API and its struct layouts at 32 bits.

`CC_wasm32_wasip1` and `AR_wasm32_wasip1` name wasi-sdk 34's clang and llvm-ar for orjson's one C file, yyjson. The build is `cargo rustc --release --frozen --offline --target wasm32-wasip1 --lib --crate-type staticlib`. orjson's own release profile already sets `panic = "abort"`, `lto = "fat"` and `codegen-units = 1`. The static init function `PyInit_orjson` is there, and orjson uses multi-phase init.

One harmless warning: on macOS the minimal profile's `rust-objcopy` lacks `libLLVM.dylib`, so stripping a build script fails and the build goes on.

## 2. Does it link? (EXECUTED)

The library, `liborjson.a`, is 3,822,390 bytes in 300 members. One is orjson, one is yyjson; 263 are Rust's `compiler_builtins` and 35 are compiler-rt C files it carries. Its undefined C names are wasi-libc's: `malloc`, `realloc`, `free`, `write`, `getenv`, `getcwd`, `strerror_r`, `strlen`, `memcmp`, `abort`, `errno`, `fma`. So Rust brings no libc of its own. Its allocator is wasi-libc's `malloc`, the one CPython's raw allocator uses.

The test relinked the reactor by step 60's own command (`reactor-commands.txt`) into the scratch folder, with an inittab object holding one more line, `PyImport_AppendInittab("orjson", PyInit_orjson)`, and the library ahead of `-lc++`. A baseline was relinked the same way, without orjson.

- **As cargo writes it, it links with no warning, and it changes the interpreter's math.** `compiler_builtins` defines `cbrt`, `ceil`, `copysign`, `fabs`, `floor`, `fma`, `fmax`, `fmin`, `fmod`, `rint`, `round`, `sqrt`, `trunc` and their `f` forms as weak symbols. A weak symbol is a definition the linker uses only when no other is loaded first. The library comes before `-lc` on the line, so its members load first. The link map shows them serving the whole binary. The same holds for the 128-bit float helpers (`__addtf3`, `__multf3`, `__divtf3`; wasm32's `long double` is 128-bit) and the 128-bit integer ones (`__multi3`, `__udivti3`). With only the Rust members removed, compiler-rt's C copies of `__muldc3`, `__divdc3`, `__mulsc3` and `__divsc3` (complex multiply and divide) still replaced the SDK's. The weak-duplicate gate, run over all 297 archives, passed: it compares the packages' archives with each other, not with the SDK's runtime.
- **Kept to its two objects, it is clean.** A 600,604-byte archive of just orjson's object and yyjson's links. The map then names only those two members. `cbrt` comes from `libc.a(cbrt.c.obj)` and `__multf3` from `libclang_rt.builtins.a`, as in the baseline.
- **The judge's own checks pass on the clean binary.** `harness.constructors`: "158 reviewed, none new; target_features: the line's 11". The import list is the baseline's 43, and the exception tags stay at 2.
- **No duplicate symbol** with any other builtin. orjson's plain global names `dumps` and `loads` would clash loudly, not silently, if one ever did.

## 3. Does it run, and what does a panic do? (EXECUTED)

Under `wasmtime run --invoke run` with the stdlib zip at `/usr/local/lib/python315.zip`, a probe printed `<module 'orjson' (built-in)>`. It then round-tripped a dict with a datetime, a UUID, a dataclass, a 2⁶⁰ integer and non-ASCII text, with `OPT_SORT_KEYS | OPT_INDENT_2`. It serialised a numpy array with `OPT_SERIALIZE_NUMPY`. It matched `json` on a 20,000-item list. It raised `JSONDecodeError` and `JSONEncodeError` where it should, and stopped cleanly at both depth limits.

Under the runner, with the clean binary and a fresh Wizer snapshot, `import orjson, pandas` exited 0. Counted in fuel on 20,000 small records, past the cost of building them:

| | fuel |
|---|---|
| `json.dumps` | 372 M |
| `orjson.dumps` | 91 M |
| `json` round trip | 860 M |
| `orjson` round trip | 357 M |

A panic was tested with a ten-line probe crate of the spike's own whose init function panics. Rust prints `thread '<unnamed>' (1) panicked at …` to stderr. With `panic = "abort"` it calls wasi-libc's `abort`, which executes `unreachable`. The runner reports `exit_code=None`, `trapped='unreachable'` (`_trap_name` maps the trap code to its name), and the panic message in `stderr`. Text still in the guest's stdout buffer is lost, as with any C `abort` today. Native orjson wheels also build with `panic = "abort"`, so orjson behaves as it does on Linux: a panic ends the process.

## 4. What it costs (EXECUTED, INFERRED where marked)

- **Binary.** Stripped `python.wasm` grows from 99,421,511 to 99,738,473 bytes: 316,962 bytes. The snapshot grows by about the same (104,838,443 bytes, against the tree's own 104,517,748).
- **Toolchain.** 556 MiB installed: the wasm32-wasip1 standard library 104 MiB, the host's 157 MiB, `librustc_driver` 80 MiB, binaries 42 MiB. Download size was not measured. As build inputs it would be per build host `rustc`, `cargo` and the host `rust-std` tarballs, plus one host-neutral `rust-std-wasm32-wasip1`: ten pins for three build hosts, from `static.rust-lang.org`, a new host to fetch from. INFERRED from rustup's layout.
- **Same bytes.** Without remapping, panic-location strings carry the build path (`/Users/…/include/cargo/associative-cache-3.0.1/src/lib.rs`). With `--remap-path-prefix` for the source and cargo home, and `-ffile-prefix-map` plus the project's `-ffp-contract=off` for yyjson, two builds from two folders gave the same `liborjson.a` (SHA-256 `b41daa23…`). That is the same host and two paths. Across hosts it is INFERRED: rustc's wasm code does not depend on the host, and Rust never fuses `a*b+c` on its own, which is what `-ffp-contract=off` fixes for clang.
- **CI.** The build is about 6 seconds; the cost is fetching and caching the toolchain on each build host. INFERRED.
- **Licences** (from each vendored crate's `Cargo.toml`). Linked into the binary: orjson `MPL-2.0 AND (Apache-2.0 OR MIT)` (68 source files MPL-2.0, 13 Apache-2.0 OR MIT); yyjson MIT; associative-cache, bytecount, libc, once_cell, pyo3-ffi, simdutf8 `MIT OR Apache-2.0`; itoap and zmij MIT; jiff-core `Unlicense OR MIT`; xxhash-rust BSL-1.0; Rust's `std` `MIT OR Apache-2.0`. Build tools only: cc, find-msvc-tools, shlex, pyo3-build-config (`MIT OR Apache-2.0`), target-lexicon (`Apache-2.0 WITH LLVM-exception`). New to constitution §4.12 is compiled MPL-2.0 code: tqdm's MPL-2.0 is approved, but it ships as source. BSL-1.0 has Boost.Math as precedent. The owner approves before a build.

## 5. pydantic-core, cramjam, and the recommendation

**Every Rust module goes into one library.** A second static library beside orjson's failed to link: `duplicate symbol: rust_eh_personality` and `std::panicking::EMPTY_PANIC`. A combined crate that depends on orjson and on the probe linked, held both `PyInit_orjson` and `PyInit__rspanic`, ran orjson, and trapped on the probe's panic. Its binary was 3,658 bytes bigger than orjson's alone. EXECUTED. orjson declares `crate-type = ["cdylib"]` only; the umbrella needed `rlib`, a one-line manifest change (a patch, with an upstream pull request). EXECUTED in scratch.

**pydantic-core 2.50.2** (READ, its sdist): PyO3 0.30.1 with macros; `crate-type = ["cdylib", "rlib"]`, so it joins the umbrella as published. 102 crates in `Cargo.lock`, not vendored in the sdist: each would be fetched once from crates.io and pinned by the lock's SHA-256. No C `-sys` crate but `js-sys`, which is for the browser target (INFERRED). Two differences from orjson (INFERRED). PyO3 turns a panic into `PanicException` only under unwinding. On wasm, unwinding Rust needs a nightly `-Zbuild-std` with exception handling, so here a panic ends the run, and pydantic-core's own manifest notes a feature that "can panic". Same route, a bigger second step.

**cramjam 2.14.0** (READ, its sdist): PyO3 0.29.2, `crate-type = ["cdylib"]`, 128 crates, and C `-sys` crates for bzip2, liblzma, zstd and lz4. It bundles bzip2 and liblzma, and this interpreter already links both for `_bz2` and `_lzma`. Two copies of their strong symbols would collide, or be steered to the existing archives through each `-sys` crate's own options. fastparquet would also need its own Cython build. Not yet. INFERRED.

**The recommendation: a specification for 0.1.4, orjson only.** It changes the build recipe and adds a toolchain, so constitution §5.6 reviews it before it is built. What it needs:

1. The ten toolchain pins, verified like wasi-sdk, unpacked under `build/tools/`.
2. A step that builds one umbrella crate (a recipe under `recipes/`) with the PyO3 config file, the remap flags and `-ffp-contract=off`, then keeps only the crates' own objects.
3. A link-map check that every libm and compiler-rt name resolves to the SDK's archives. The weak-duplicate gate does not cover that today, and section 2 shows why it must.
4. `orjson.orjson` on the inittab, with `pysrc/orjson/` in the zip, as orjson's wheel lays it out.
5. Its suite. The sdist carries `test/*.py` but not the `data/` fixtures some tests skip without; the GitHub tarball has them.
6. The owner's licence approval first.

pydantic-core is a second spike once orjson's umbrella exists: PyO3's macros, 102 crates and the panic difference. cramjam waits for a reason to build fastparquet.

One line: orjson builds, links and runs as a builtin on PyO3 at 0.32 % size, provided the Rust runtime's own libm and compiler-rt are kept out of the link and every Rust module shares one library.
