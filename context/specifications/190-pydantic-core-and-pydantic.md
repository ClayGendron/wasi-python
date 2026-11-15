# 190: pydantic-core and pydantic

- **Status:** drafted 2026-11-15, not built; asked for by the owner on 2026-11-14 (`../decisions.md`, "0.1.5's scope": "I want to land pydantic-core so we start developing a rust pipeline", and on its size, "Add it to every python wasm"). Not yet reviewed before it is built.
- **Open for the owner:** two choices, each written below with the default the build takes unless the owner says otherwise: how orjson and pydantic-core share one PyO3 (Decision 3), and what a prepared image does with Rust's hash keys (Decision 7). Neither is decided here, and neither default is recorded in `../decisions.md` as the owner's. A third is asked only if a check finds what it looks for (Decision 5).
- **Date:** 2026-11-15
- **Owner:** Clay Gendron
- **Kind:** **build-class** (the build recipe: pydantic-core in the umbrella, the crate pins and lock, the bytes of both binaries and the zip, MANIFEST's lines, the licence notices), **a judge change** (four suites and their shard rows, a golden job, new checks and rules), and, on Decision 3's default, a second carried patch to orjson. Not structural: nothing under `src/` changes. Reviewed before it is built (constitution §5.6), since it changes the artifact set and the build recipe.
- **Depends on:** 187 (the Rust pipeline: Rust 1.100.0, build-std under `RUSTC_BOOTSTRAP=1` with `-Cpanic=$RUST_PANIC`, the umbrella crate, the entropy shim found with `llvm-nm`, the link-map gate, `recipes/guest-imports.txt`, `_rust_probe`), not yet merged; this branch starts from its local tip, `d58bea64`. It is built once 187 merges, or stacked on 187's reviewed tip (constitution §4.14). 187's two owner questions stand under this one too: whether orjson's carried patch may stand, since orjson takes no pull requests, and the notices of yyjson and `core`'s Unicode tables. It stands on 063 (every package runs its own tests), 157 (entropy pinned while an image is prepared), 171 (the packages list) and 173 (how a pure-Python package is added).
- **Research it stands on:** the two spikes of 2026-11-14, whose record is the session's working notes, "Ask 3" (pydantic-core built for `wasm32-wasip1`, its imports, its math, its size, both suites run natively) and "Ask 4" (unwinding on pinned stable), not in the repository; PyPI's JSON for pydantic, pydantic-core, annotated-types, typing-inspection and orjson, read 2026-11-15; the four sdists read whole from files.pythonhosted.org the same day, each checked against PyPI's SHA-256; the crates in this machine's cargo cache (ahash 0.8.12, getrandom 0.3.3, foldhash 0.2.0, version_check 0.9.5, pyo3-ffi 0.29.3 and 0.30.1); orjson's GitHub head, read 2026-11-15; the prior-art clones `orjson` (at 3.13.0), `pyo3` and `pydantic`; two cargo runs in scratch on Rust 1.97.0 (Decision 3).

Labels: EXECUTED, run and seen; READ, read from a file or a page, cited; INFERRED, reasoned. A label from a spike's record is that record's own, kept ("built", "checked", "run", "measured").

## The problem

The owner wants pydantic in every `python.wasm`: pydantic-core, its Rust half, compiled in, and pydantic, annotated-types and typing-inspection beside it in the zip. pydantic is the validation library most agent tools use for their schemas.

187 builds the pipeline and ships orjson through it. pydantic-core is the second module in the umbrella, and the first large one. The spikes showed it builds. Four things stand between it and the set.

1. **Two PyO3 lines cannot share one build.** orjson 3.13.0 needs `pyo3-ffi` 0.29; pydantic-core 2.50.4 needs `pyo3` 0.30.1. Both `pyo3-ffi` versions declare `links = "python"`, and cargo admits one package per `links` value in a build graph. 187 left this to this specification.
2. **One crate's allocator serves every crate.** orjson declares a `#[global_allocator]`, and a build graph has one. In the umbrella it becomes pydantic-core's allocator too.
3. **pydantic-core reads entropy past the wrap**, through `getrandom`, and keeps the keys it draws in a static. A prepared image keeps them.
4. **Four new packages, four suites**, and a gate the owner set: both pydantic suites in the sandbox on `panic=unwind`, before it ships.

## What the spikes and the reads showed

| Fact | Label and source |
|---|---|
| pydantic-core 2.50.4 builds for `wasm32-wasip1` as a static library with a PyO3 config file (3.15, static): on stable 1.97 with panic=abort in 1m22s; with `RUSTC_BOOTSTRAP=1` and `-Zbuild-std=std,panic_unwind -Cpanic=unwind` in 98 seconds | built, Asks 3 and 4 |
| Its object imports `wasi_snapshot_preview1.random_get` directly, twice: `getrandom` 0.3.3's `wasi_p1` backend (ahash's `runtime-rng`) and std's `RandomState` (regex-automata); a C shim defining the two mangled names to call `__wasi_random_get` removes the direct import | checked, Ask 3 |
| No direct clock or poll import: Rust's clocks go through wasi-libc's `clock_gettime`, which is wrapped | checked, Ask 3 |
| Linked as cargo writes it, the archive takes `round` from `compiler_builtins`; kept to the crate's own object, wasi-libc's | checked, Ask 3 |
| 4,521,038 bytes standalone, stripped, on abort; 5,331,840 with unwinding (1.22 MB and 1.39 MB gzipped) | measured, Asks 3 and 4 |
| Natively on CPython 3.15.2, panic=abort: pydantic-core's suite 5,836 passed, 122 skipped, 8 xfailed (`test_docstrings` skipped, it needs pytest-examples); pydantic 2.14.3's 10,835 passed, 146 skipped, 27 xfailed (docs, mypy and benchmarks left out). No panic in either | checked natively, Ask 3; nothing ran in the guest |
| `js-sys` is not in the `wasm32-wasip1` tree | checked, Ask 3 |
| The licence sweep: pydantic-core 2.50.4's 67 crates for `wasm32-wasip1`, normal dependencies, proc macros left out | READ, the notes' "Crate licence sweep"; approved 2026-11-14 |

Nothing was linked into `python.wasm` or run in the guest: the container's network refuses CPython's source at www.python.org, and the spikes did not route around it. The guest numbers come from the pull request's CI run.

## Decisions

### 1. The pins: pydantic 2.14.3 with pydantic-core 2.50.4

Read from PyPI's JSON on 2026-11-15 (READ): pydantic's newest release is 2.14.3 (2026-11-05), and its `Requires-Dist` names `pydantic-core==2.50.4`, `annotated-types>=0.6.0`, `typing-extensions>=4.16.0` and `typing-inspection>=0.4.4`. pydantic-core's newest is 2.50.4 (2026-11-05), the version the spikes built and the licence sweep read. So the pair is pydantic's own pin, not a choice. annotated-types' newest is 0.8.0 and typing-inspection's 0.4.5. The set's typing-extensions, 4.16.0, meets both floors (READ, `downloads/SHA256SUMS`). pydantic lists Python 3.15 among its classifiers; pydantic-core lists up to 3.14 but ships `cp315` wheels for 2.50.4 (READ). That the pair works on 3.15 rests on the spike's native run (checked natively).

| Pin | Kind | SHA-256 (READ from PyPI, and EXECUTED on the downloaded file where marked) |
|---|---|---|
| `pydantic_core-2.50.4.tar.gz` | source, built | `aead3b74b68396bf0feab5d57e050b730ded7df55853c1e048a87e00aaf033c6` (EXECUTED) |
| `pydantic-2.14.3-py3-none-any.whl` | the package | `3f7b347782ab7e4cf4c798496ae3a82787d9f21ec12676a9c564355eeef8daa8` |
| `pydantic-2.14.3.tar.gz` | tests | `1054f237f4d4733e5a30e1e2333bd33a2004ab9ab1510bd053a9a31bb48e232d` (EXECUTED) |
| `annotated_types-0.8.0-py3-none-any.whl` | the package | `f072f4d804ea359e4eaf198b1af7a8b0943881a87f31bb764f8bf219bb9419e0` |
| `annotated_types-0.8.0.tar.gz` | tests | `13b2beaad985e05e2d6407ee4c4f35590b11f8d693a258a561055cac8f64cab7` (EXECUTED) |
| `typing_inspection-0.4.5-py3-none-any.whl` | the package | `bc210535442b39e1bf2805e0c7a17dfd6a4ace760c84c7f7d16245d23a6b1c39` |
| `typing_inspection-0.4.5.tar.gz` | tests | `7f16c411e7930dc79596d42ab44672a3fe5f60eb34b781a1647e7872363120c7` (EXECUTED) |

Each URL is the one PyPI's JSON gives; the build session's first download checks each file, as every pin is checked. Every sdist carries its tests (READ: pydantic-core's has `tests/`, 129 entries at its top; pydantic's `tests/`; annotated-types' and typing-inspection's `tests/`). pydantic-core's sdist is both the source and the test source.

A rule holds the pair: the pinned pydantic wheel's `Requires-Dist` names exactly the pinned pydantic-core version (read from the wheel, so it runs where the downloads are). The two move together or not at all.

### 2. pydantic-core joins the umbrella as upstream ships it

Step 52 unpacks the sdist to `build/pydantic_core-2.50.4` (the judge's tree check, `SOURCE_PATTERNS`, gains it) and stops unless `PKG-INFO` says 2.50.4. The umbrella depends on it by path, and `recipes/rust/modules/src/lib.rs` gains `extern crate _pydantic_core as _;`. `recipes/rust/modules.txt` gains `pydantic_core._pydantic_core PyInit__pydantic_core`, so it is a builtin through the inittab, as `orjson.orjson` is.

No patch to pydantic-core. Its library already declares `crate-type = ["cdylib", "rlib"]` (READ, its `Cargo.toml`), so it can be a dependency; its `cdylib` links for `wasm32-wasip1` with the pinned `rust-std` component, as orjson's does (187, Decision 1). What else in the sdist meets the build (READ unless marked):

- Its `.cargo/config.toml` sets no flag for the wasm family, and cargo reads configuration from the working folder's ancestors, not a dependency's (INFERRED from cargo's rules; step 52 runs from `build/`), and `CARGO_ENCODED_RUSTFLAGS` wins anyway.
- Its `build.rs` asks `version_check::supports_feature("coverage_attribute")`. version_check 0.9.5 answers from the channel `rustc -V` prints and does not read `RUSTC_BOOTSTRAP`, so on stable 1.100.0 it answers false and the cfg stays off on every host.
- Its release profile (`lto`, `codegen-units`, `strip`) is not read for a dependency; the workspace's governs (187, Decision 4).
- Its recursion guard stops at 49 levels on the wasm family, 255 natively (`src/recursion_guard.rs:89`).
- Its module is `#[pymodule(gil_used = false)]` with a submodule `_schema_gather`, which pydantic reaches as an attribute (`from pydantic_core._pydantic_core import _schema_gather`, `pydantic/_internal/_schema_gather.py:5`). That a multi-phase module initialises as a builtin under a dotted name is INFERRED from CPython's `create_builtin`; `_rust_probe` on PyO3 proves the path first, in 187.

Step 70 packs `python/pydantic_core/` as pydantic-core's wheel lays it out: `__init__.py`, `core_schema.py`, `py.typed` and the stub folder `_pydantic_core/` (`__init__.pyi`, `_schema_gather.pyi`), with METADATA from `PKG-INFO` and a `top_level.txt` of `pydantic_core`. The builtin importer comes before the zip's path finder, so the stub folder never shadows the module (INFERRED). The three wheels go in as every pure-Python wheel does (173).

### 3. One PyO3, 0.30.1

Cargo refuses both lines in one graph (EXECUTED, cargo 1.97.0, offline, a scratch crate depending on `pyo3-ffi` `=0.29.3` and `=0.30.1`: "package `pyo3-ffi` links to the native library `python`, but it conflicts with a previous package which links to `python` as well … only one package in the dependency graph may specify the same links value"). The notes' "two versions in the umbrella; inferred OK as separate crates" is wrong. Two umbrellas are no way out: two Rust libraries collide on the standard library (187, hazard 1). A `[patch.crates-io]` cannot cross a semver line, so it cannot give orjson 0.30 without editing orjson's requirement. pydantic-core uses 0.30's API, so the line is 0.30.1, and orjson must move.

orjson has no release on 0.30: PyPI's newest is 3.13.0, and its GitHub head still requires `pyo3-ffi = "0.29"` (READ, 2026-11-15). orjson 3.13.0 with that requirement and `pyo3-build-config`'s changed to 0.30 passes `cargo check --release --target wasm32-wasip1` on Rust 1.97.0 with no warning (EXECUTED, in scratch, offline, wasi-sdk 34's clang for yyjson; a check only: not built, linked or tested). PyO3 0.30.0's changelog adds FFI definitions and removes what 0.28 deprecated (READ, the `pyo3` clone).

**Open for the owner.** How orjson reaches PyO3 0.30:

- **A, the default:** a second carried patch, `recipes/patches/orjson-3.13.0/0002-pyo3-0-30.patch`, changes the two requirements to `"0.30"`. It stands on the same terms as the first, whatever the owner answers 187 about a patch orjson cannot take upstream; it is checked again at each orjson version and deleted when orjson moves to 0.30. orjson's suite and golden job, already in the set, prove it.
- **B:** wait for an orjson release on PyO3 0.30. pydantic-core waits with it, and leaves 0.1.5 if none comes before the cut.

Not offered: pydantic-core down to 0.29 (a larger patch, backwards, that pydantic would not take), and orjson out of the set (the owner chose orjson first). If the owner refuses 187's standing patch, A falls with it and B is what is left.

`_rust_probe`, our crate, moves to `pyo3 = "=0.30.1"` with the same feature list as today; cargo unifies pydantic-core's features into the one `pyo3` (INFERRED).

### 4. One lock for every Rust package

`recipes/rust/Cargo.lock` is written once, with network, by the build session. orjson's lock and pydantic-core's name different versions of eight crates they share or that the umbrella already holds, and of the PyO3 family (READ, the three locks compared): `libc` 0.2.190 and 0.2.185, `once_cell` 1.21.4 and 1.21.3, `quote` 1.0.47 and 1.0.44, `unicode-ident` 1.0.26 and 1.0.12, `target-lexicon` 0.13.5 and 0.13.4, `zmij` 1.0.23 and 1.0.6, `portable-atomic` 1.15.0 and 1.6.0, `syn` 2.0.119 and 2.0.82, and the PyO3 family. Cargo unifies semver-compatible versions to one (INFERRED), so both locks cannot hold.

The rule: each crate keeps the version its package's own lock names; where two packages' locks name two compatible versions of one crate, the higher; the PyO3 family is 0.30.1 (Decision 3). 187's rule "orjson's versions" becomes "the packages' versions", reading both sdists' locks (`needs.need("downloads")`). The lock's resolution moves only those crates (`cargo update -p <name> --precise <version>`), and the build session lists every crate whose version differs from its package's lock in the landing notes. The scratch check of Decision 3 also moved `quote` and `unicode-ident` downward, to the versions this machine's cache held; an offline resolution is not the rule.

The crate pins and their `.cargo-checksum.json` files follow 187's Decision 2 unchanged: one `static.crates.io` pin per non-path package, its SHA-256 the lock's checksum, about 60 more.

### 5. One allocator: orjson's

orjson declares `#[global_allocator] static ALLOCATOR: PyMemAllocator`, unconditionally, calling `PyMem_Malloc`, `PyMem_Realloc` and `PyMem_Free` (READ, `src/alloc.rs`, `src/lib.rs:49`). A build graph has one global allocator, so in the umbrella it serves pydantic-core, PyO3, `_rust_probe` and the standard library too (INFERRED from Rust's rule; true already under 187). Upstream, pydantic-core's wheel uses Rust's default, which on `wasm32-wasip1` is wasi-libc's `malloc`, honouring alignment (INFERRED).

The build keeps orjson's allocator. In this build `PyMem_Malloc` is the C library's `malloc`, since there is no pymalloc (READ, `recipes/reactor_main.c`, the teardown comment), so the memory is the same memory. Two differences are named:

- **The GIL.** The mem domain wants the GIL held. pydantic-core never releases it: no `detach` or `allow_threads` in its source or in jiter 0.18.0's (READ).
- **Alignment.** orjson's allocator ignores `Layout::align`. wasm's loads and stores do not trap on misalignment, so a misaligned block is slower, not wrong, unless code relies on the address (INFERRED). The builder reads wasi-libc's `malloc` alignment from the pinned sysroot source and searches every vendored crate compiled for the target for `align(` above it. None found is recorded in the landing notes. **Any found is asked of the owner** before the pull request merges, with the fallback a carried patch to orjson that drops its allocator, so wasi-libc's `malloc` serves everything.

The free-nothing hook at teardown (`reactor_main.c`) then covers Rust's frees too, as it covers C's.

### 6. The shim routes getrandom too

187's shim gains pydantic-core's name with no change to its code: step 52 finds every undefined name whose demangled form ends in `::random_get` and defines it to call `__wasi_random_get`. With orjson, the probe and pydantic-core, the expected count is two, std's and getrandom's (checked on 1.97, Ask 3; INFERRED on 1.100.0), and the step's line names them. `getrandom` 0.3.3 imports `random_get` from `wasi_snapshot_preview1` itself (READ, `src/backends/wasi_p1.rs:9-11`). Its `custom` backend would route it without a mangled name, but std's name still needs the shim, so one mechanism serves both, as the owner decided.

The other key source in the tree, foldhash 0.2.0 (hashbrown's default hasher, through `lru`), seeds itself from an address and `std::time::UNIX_EPOCH.elapsed()` (READ, `src/seed.rs:150-164`), so it reads the wrapped clock and needs no shim.

### 7. The hash keys and the snapshot

ahash keeps its keys in a static: `get_fixed_seeds` fills a `OnceBox` once from `getrandom::fill`, and each new `RandomState` mixes a counter with an address (READ, ahash 0.8.12, `src/random_state.rs:70-77`, `:153-163`). std's `RandomState` keeps its keys per thread, the same way (INFERRED). So the keys are drawn at a process's first use and kept.

Decision 34 stands: the default snapshot pre-imports no package (`../decisions.md`, "34, answered"). So in a plain call pydantic-core draws its keys from real entropy at first use, as natively. Two kinds of image hold them:

- **A prepared image** (`make_snapshot`, `make_package_snapshot`): entropy is pinned to zeros while the prelude runs (157, Decision 2), so a prelude that validates draws the same keys in every image, everywhere. With the shim this is deterministic; without it they would be real and the image unreproducible.
- **A checkpoint** (`Session.checkpoint`): the session's real keys go into every resume.

This is the class CPython's own string hash already sits in: the snapshot's hash secret is fixed at Wizer time (`hash_randomization == 0`, EXECUTED, `../research/2026-10-16-a-principal-engineers-direction.md`). What it exposes: most of pydantic-core's ahash maps are keyed by a schema's field names or by object ids, but a model that does not ignore extra keys collects a JSON input's unknown keys into an ahash-keyed `IndexMap` (READ, `src/validators/model_fields.rs:503-512`). With the keys known, crafted JSON can collide there; the call's fuel and deadline bound the cost to that call (INFERRED). No reseed is possible from Python: the static has no API.

**Open for the owner.** What a prepared image does with Rust's keys:

- **A, the default:** nothing changes, and it is said. The limitations page says, beside the snapshot's string hash, that Rust's hash keys in a prepared image or a checkpoint are those of the moment it was made.
- **B:** a carried patch to ahash so each `RandomState` draws from the guest's entropy, one `random_get` per map, a cost on every validation, with an upstream pull request that ahash may not take.

### 8. Panics: the gate's second half

The owner's gate ("0.1.5's scope") is a CI run that links the unwinding build, runs both pydantic suites in the sandbox and tests a deliberate panic. 187's run is its first half. This pull request's run with `ci:full` is the second: pydantic-core's and pydantic's suites run on `panic=unwind` on Linux and Windows, and 187's panic checks run with pydantic-core in the umbrella. PyO3 wraps each pydantic-core entry point, so a panic there raises `PanicException` as natively; its `py-clone` feature can panic, its own manifest says (READ).

If the unwinding fails here, the builder records why, tries once more, then throws 187's switch (`RUST_PANIC=abort`) in a commit of its own, as 187's Decision 8 says, and tells the owner in the pull request. Under abort a panic in pydantic-core ends the run.

### 9. The suites, the job and the checks

- **The suites** (spec 063). `tests/upstream/pydantic-core.toml`, `pydantic.toml`, `annotated-types.toml` and `typing-inspection.toml`, each with its `.ini`, driver `package`, the sdist as test source. Each has a smoke group in the normal tier, about a fifth of its files by measured fuel, and the rest in the release tier, each test in exactly one. pydantic-core's suite needs dirty-equals, inline-snapshot (with asttokens, executing and rich), pytest-mock and hypothesis; pydantic's needs dirty-equals, pytest-mock and pytz (READ, their `pyproject.toml` and imports). The test-only wheels join `tests/upstream/kit-extra.txt`; rich comes from the set if the packages track has landed it. Left out: pydantic-core's `tests/benchmarks` and `test_docstrings.py` (pytest-examples); pydantic's `tests/mypy`, `tests/plugin`, `tests/benchmarks` and `test_docs.py`. Expected classes are found by the run and reasoned. Known now: the suites branch on `sys.platform == 'emscripten'` where they mean wasm (eight lines of pydantic-core's tests and twelve of pydantic's name `emscripten`, READ), and the guest's platform is `wasi`, so subprocess tests and the depth-limit tests meet native expectations; pydantic's tests of email-validator, pydantic-settings, time-machine and the packages later in 0.1.5 (Faker, jsonschema) skip or are classed. `tests/release_shards.toml` places each group by its measured fuel. `tests/upstream/packages.toml`: four suites, and `pyo3`'s `later` row becomes `via` `pydantic-core`.
- **A golden job**, `tests/jobs/pydantic_models.py`: a model with nested models, `Annotated` constraints (annotated-types), validators, a discriminated union, datetimes, UUIDs, `Decimal`, `TypeAdapter`, a dataclass, `model_dump_json`, `model_json_schema`, and a `ValidationError`'s `json()`. It prints each result's bytes and SHA-256; native pydantic 2.14.3 in the oracle's lock gives the expected file.
- **`tests/checks/test_v1_3_rust.py`** gains, each seen failing first:
  - `test_pydantic_core_is_built_in`: `pydantic_core._pydantic_core` is in `sys.builtin_module_names`, `pydantic_core.__version__` is `"2.50.4"`, `pydantic.VERSION` is `"2.14.3"`, and `pydantic_core.__file__` is in the zip.
  - `test_a_panic_after_pydantic_validates_is_caught`: a run validates a model, `_rust_probe.panic("probe")` raises `PanicException`, and the model validates again in the same run. One unwinder and one personality serve both modules.
  - `test_pydantic_core_reads_entropy_through_the_wrap`: two images prepared with a prelude that validates JSON into a model with `extra="allow"` are byte-equal. Seen failing first in scratch, with the shim's getrandom definition left out and step 52's stop on an unrouted name turned off.

### 10. The rules

Each in `tests/harness/scan.py` with unit rows, each seen failing first: the pair (Decision 1); the packages' versions (Decision 4); `modules.txt` lists `pydantic_core._pydantic_core` and the archive defines `PyInit__pydantic_core` (187's gate 1); pydantic-core and the three wheels join `scripts/assemble_artifacts.py`'s and `tests/harness/paths.py`'s `PACKAGES`; on Decision 3's default, the patch rule (spec 020) sees exactly two orjson patches.

### 11. The zip, MANIFEST and the snapshot list

`recipes/snapshot-packages.txt` gains four lines after typing-extensions', in import order: `annotated-types: annotated_types`, `typing-inspection: typing_inspection typing_inspection.introspection`, `pydantic-core: pydantic_core`, and `pydantic: pydantic pydantic.main pydantic.type_adapter`, the builder confirming which submodules `from pydantic import BaseModel, TypeAdapter` loads. That list feeds `make_package_snapshot`, not the default snapshot. MANIFEST gains the four packages' lines; `x-rust` is unchanged.

### 12. The licences

Approved (`../decisions.md`, "0.1.5's scope" and "The Rust crates' licences"; constitution §4.12): MIT for pydantic, pydantic-core, annotated-types and typing-inspection; MIT wherever one of pydantic-core's crates offers it; Unicode-3.0 for its 15 ICU4X crates (`icu_*`, litemap, tinystr, writeable, yoke, zerofrom, zerovec); Zlib for foldhash. The notices: `LICENSES/pydantic.txt`, `annotated-types.txt` and `typing-inspection.txt` from each wheel's licence file, and `LICENSES/pydantic-core.txt` with pydantic-core's own and each crate's from its pin, the list being the graph cargo resolves for `wasm32-wasip1` (187's rule). The build's sweep runs on the merged lock; a crate or a licence beyond the approved set, and any version Decision 4 moved that changes a licence, is asked again before it ships. This pull request amends §4.12's list with the four MIT packages by name, quoting "0.1.5's scope", which approved them.

### 13. Size and fuel

Expected (INFERRED from the spikes): each binary grows by about 4.5 to 5.3 MB, less the standard library and PyO3 runtime orjson already brought; the zip by pydantic's, annotated-types' and typing-inspection's files; the wheel by about 3 MB compressed, far under `PYPI_FILE_LIMIT` (268,435,456). A plain start and a snapshot start should cost the same fuel: nothing new runs until `import pydantic_core`. The builder records every artifact's bytes, the fuel of a plain start, of `import pydantic`, of `from pydantic import BaseModel` and of the golden job, and claims each growth in the news file.

### 14. The pages and the news file

- `docs/reference/packages.md`: the four rows come through the news file; the sentences naming the compiled packages gain pydantic-core.
- `docs/reference/limitations.md`: a model nested past 49 levels is refused, as on every wasm build of pydantic-core; email validation needs email-validator, which the set does not carry, so `EmailStr` raises `ImportError`; Decision 7's sentence on A; and under the abort switch, that a panic in pydantic-core ends the run.
- `context/changes/190-pydantic-core-and-pydantic.md`, written at build time. Changelog, under New: "**pydantic is built in**: pydantic 2.14.3 with its Rust core, `import pydantic`, with native pydantic's results". Package rows for the four. Claims: the new checks, units and files, the four suites' groups under `passes`, both binaries and the zip under `grows` with Decision 13's reasons, the judge files with theirs; the release groups' claims also in `context/release-claims/190-pydantic-core-and-pydantic.toml`.
- `.github/workflows/release.yml`: the tree count rises by pydantic-core's tree.

## Intent

A program in the guest imports pydantic and gets native pydantic's results, with its Rust core compiled into every `python.wasm`. A panic behind PyO3 raises `PanicException` and the run goes on. pydantic-core goes in as upstream ships it: one PyO3, one allocator and one entropy route for every Rust module, and no new import.

## Design

Added: `tests/upstream/pydantic-core.toml`, `pydantic.toml`, `annotated-types.toml`, `typing-inspection.toml` and their `.ini` files; `tests/jobs/pydantic_models.py` and its expected file; on Decision 3's default, `recipes/patches/orjson-3.13.0/0002-pyo3-0-30.patch` and its facts sheet under `context/upstream/patches/orjson-3.13.0/`; `context/changes/190-pydantic-core-and-pydantic.md`; `context/release-claims/190-pydantic-core-and-pydantic.toml`.

Changed: `scripts/00_download.sh` and `downloads/SHA256SUMS` (Decision 1's seven pins, the crate pins); `recipes/rust/Cargo.lock`, `modules.txt`, `modules/Cargo.toml`, `modules/src/lib.rs`, `modules/probe/Cargo.toml`; `scripts/steps/52_rust.sh` (the sdist, the version stop); `scripts/steps/70_zip.sh`; `scripts/assemble_artifacts.py` (the packages, the notices); `recipes/snapshot-packages.txt`; `tests/harness/paths.py`, `pins.py`, `scan.py`; `tests/checks/test_rules.py`, `test_v1_3_rust.py`; `tests/unit/test_scan.py`; `tests/upstream/packages.toml`, `kit-extra.txt`; `tests/release_shards.toml`; `tests/jobs/oracle/pyproject.toml` and `uv.lock`; `docs/reference/packages.md`, `limitations.md`; `.github/workflows/release.yml`; `context/constitution.md` (§4.12's list).

## Scope

In: Decisions 1 to 14. Out: email-validator and pydantic's other extras; pydantic-settings; the runner reporting a Rust abort as an error of its own; moving `RUST_VERSION`; a reseed of Rust's keys (Decision 7's B, unless the owner chooses it); rpds-py and python-calamine, the next Rust packages.

## Acceptance criteria

1. Decision 1's seven pins and every new crate pin match their SHA-256 on first fetch; the pair rule passes (EXECUTED).
2. Step 52 builds the umbrella with orjson, `_rust_probe` and pydantic-core on PyO3 0.30.1, offline, on each host; its line names two shimmed entropy imports and pydantic-core's kept object; 187's archive gates pass (EXECUTED).
3. The landing notes list every crate whose version differs from its package's lock, wasi-libc's `malloc` alignment and what the search for larger alignments found (EXECUTED).
4. Imports equal `recipes/guest-imports.txt`, two exception tags, and constructors, target features and the exception form unchanged, on both binaries; the link map names wasi-libc's `round` (EXECUTED).
5. The pull request's run with `ci:full` is green on Linux and Windows: the four suites' smoke and release groups, every expected class reasoned; orjson's suite and job still green; the golden job with exact bytes; Decision 9's three checks, each seen failing first; 187's panic checks on `panic=unwind`, or the switch thrown as Decision 8 says and recorded (READ from that run). This is the owner's gate.
6. Two builds of the archive from two folders give one SHA-256, and `same-bytes` is green across hosts (EXECUTED; READ).
7. Decision 13's bytes and fuel are recorded and claimed; the licence sweep on the merged lock finds nothing beyond Decision 12, or the owner is asked again (EXECUTED).
8. The owner's answers to Decisions 3 and 7, and to 5 if it was asked, are in `../decisions.md` before the pull request merges; the fast tier, `tests/lint`, `ci-status` and `review` are green; the news file is present.

## Landing notes

Not built.
