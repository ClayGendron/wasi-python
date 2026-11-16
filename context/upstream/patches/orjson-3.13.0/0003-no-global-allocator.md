- **Project:** orjson (https://github.com/ijl/orjson)
- **Against:** 3.13.0 (the pinned sdist, after 0001 and 0002)
- **Status:** drafted
- **Title:** Leave the global allocator to the program that links the library
- **Files:** src/lib.rs
- **Why we carry it:** orjson's `#[global_allocator]` passes `PyMem_Malloc` only the size of each request and drops its alignment; in a library that holds other Rust modules it serves them too, and pydantic-core's regular expressions ask the heap for 64-byte alignment where the guest's `malloc` gives 16.

**This is a facts sheet, not a pull request.** orjson takes no pull requests and has no issue tracker (READ, its `README.md`, line 47), so nothing is sent. The owner chose this patch on 2026-11-15 (`../../../decisions.md`, "orjson's allocator goes before pydantic-core" and "pydantic-core's four questions"), on the terms of 0001: it is checked again at each orjson version. It has no natural end, since only orjson could make the allocator optional, and nothing asks it to. The one channel the maintainer names is the author address in orjson's `Cargo.toml`: `ijl <ijl@mailbox.org>` (READ, 3.13.0).

## The facts

**What fails.** orjson 3.13.0 declares `#[global_allocator] static ALLOCATOR: PyMemAllocator` in `src/alloc.rs`, unconditionally. Its `alloc` calls `PyMem_Malloc(layout.size())` and never reads `layout.align()`, which `GlobalAlloc`'s contract requires it to honour; its `alloc_zeroed` writes zeros before it checks for a null pointer (READ, 3.13.0). A program has one global allocator, so when orjson is a library beside other Rust modules, as in a static CPython that links every Rust module into one library, orjson's allocator serves all of them and Rust's standard library too. In a WebAssembly build `PyMem_Malloc` is the C library's `malloc`, whose blocks are 16-byte aligned (wasi-libc's dlmalloc, `MALLOC_ALIGNMENT`). regex-automata 0.4.18, through pydantic-core's `regex`, keeps each pool stack in a `#[repr(C, align(64))]` type pushed into a `Vec` (`src/util/pool.rs:414`, `:558-561`), so every compiled pattern asks for 64-byte aligned heap memory and gets 16.

**The change.** `src/lib.rs` no longer declares `mod alloc;`, so `src/alloc.rs` and its allocator are not compiled and Rust's own `System` allocator serves every crate, honouring alignment and checking for null. orjson's other code calls `PyMem_Malloc` and `PyMem_Free` directly where it needs CPython's memory, and those calls are unchanged. `PyMem_Realloc`'s import in `src/ffi/mod.rs` is then unused, and rustc warns of it; the warning is left, so the patch stays one line.

**What changes for orjson.** Its own Rust allocations come from `malloc` through std rather than through the PyMem domain. In the WebAssembly build the PyMem domain is `malloc` itself (no pymalloc), so the memory is the same; only tracemalloc, which watches the PyMem domain, stops seeing orjson's Rust allocations.

**Checked.** With 0001 and 0002, orjson built for `wasm32-wasip1` on Rust 1.97.0 in one library with pydantic-core 2.50.4, with one warning, the unused import above (EXECUTED, 2026-11-15, in scratch; built, not linked into CPython or run). That Rust's `System` allocator then serves every crate is Rust's rule for a program that declares no global allocator (INFERRED).
