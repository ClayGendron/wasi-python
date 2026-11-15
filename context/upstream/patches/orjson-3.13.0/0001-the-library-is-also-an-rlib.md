- **Project:** orjson (https://github.com/ijl/orjson)
- **Against:** 3.13.0 (the pinned sdist)
- **Status:** standing, provisionally: orjson takes no pull requests; re-checked at each orjson version
- **Title:** Declare the library as an rlib as well as a cdylib
- **Files:** Cargo.toml
- **Why we carry it:** a static CPython links orjson as a library of its own Rust crate, and cargo builds a dependency only as the crate types the dependency declares; orjson declares `cdylib` alone, so no other crate can link it.

**This is a facts sheet, not a pull request.** orjson's `README.md` says there is no open issue tracker and no pull requests (READ, 3.13.0, line 47), so this patch cannot go upstream and be deleted when a release carries it, as constitution §4.1 asks of a carried patch. It is carried provisionally, under the orchestrating session's default of 2026-11-15 while the owner's answer is awaited (specification 187, Decision 3): it stands until orjson declares an `rlib` itself, and it is checked again against each orjson version the set moves to. The owner's answer goes in `../../../decisions.md` before the pull request that adds it merges.

The one channel the maintainer names is the author address in orjson's `Cargo.toml`: `ijl <ijl@mailbox.org>` (READ, 3.13.0). Nothing has been sent, and no agent will send anything to the project.

## The facts

**What fails.** A program that embeds CPython statically, as a WebAssembly build or an embedded interpreter does, registers each compiled extension module in CPython's inittab and links the module's code into the one binary. A Rust extension then has to be a library that a Rust crate of the embedder depends on, so that one static library carries every Rust module and one copy of Rust's standard library (two Rust static libraries in one binary collide on `rust_eh_personality`). Cargo compiles a dependency only as the crate types it declares in `[lib] crate-type`, and has no way to change them from outside. orjson 3.13.0 declares `crate-type = ["cdylib"]`, so a crate that writes `orjson = { path = ... }` gets no `rlib` to link.

**The change.** `crate-type = ["cdylib", "rlib"]`. Nothing else. orjson's own wheels are still built from the `cdylib` (maturin builds the `cdylib` target), so its released binaries do not change.

**Checked.** The 2026-10-31 spike made this exact change and built, linked and ran orjson 3.13.0 in a statically linked CPython for `wasm32-wasip1`.
