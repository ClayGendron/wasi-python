# Upstream fixes, waiting for the owner

Drafts of changes this project needs from its dependencies. Nothing here is posted: the owner
reviews each text and posts it (constitution §4.1, a needed source change goes upstream first).
The issue texts and a reading guide are in the owner's "Upstream issue drafts" doc.

| folder | where | what | state |
|---|---|---|---|
| `1-wasmtime-py-last-exception/` | wasmtime-py | `LAST_EXCEPTION` per thread: one thread's host exception is never raised by another thread's call | PR ready (`pr.md`, `fix.patch`, evidence) |
| `2-wasmtime-py-sigint/` | wasmtime-py | component host functions catch `BaseException`; Ctrl-C at a callback's entry | PR ready for the first; `memo.md` and a prototype for the second, which has no sound fix inside wasmtime-py |
| `3-numpy-npy-wasi/` | numpy | `np.save` and `np.load` on WASI, where `os.dup` is unsupported | patch and facts; numpy's AI policy requires the owner to write the description |
| `4-llvm-wasm-isel-slot-order/` | LLVM (and wasi-sdk) | wasm32 instruction selection numbers the `fp128` libcall result slots differently in the x86_64 and aarch64 builds of the same clang, so x86_64 compiles one numpy function to other bytes; the difference needs `llvm.fmuladd` on `fp128`, so spec 059 compiles everything with `-ffp-contract=off` and x86_64 natively (spec 040's emulated clang is the switched-off fallback) | issue text narrowed to `fmuladd` (spec 059), a nine-line reproducer and evidence; LLVM's AI Tool Use Policy keeps agents from posting and asks for a disclosure, so the owner reviews and posts it |
| `5-pandas-styler-from-a-zip/` | pandas | the Styler's templates when pandas is imported from a zip archive | patch and a facts sheet for spec 041 (question 80); pandas' policy keeps the issue and pull request in the owner's own words |
| `6-networkx-atlas-from-a-zip/` | networkx | the graph atlas when networkx is imported from a zip archive | patch, test and a facts sheet for spec 041 (question 80); networkx asks AI tools not to suggest a pull request, so engaging is the owner's choice |
| `7-matplotlib-qhull-devnull/` | matplotlib | Delaunay triangulation on WASI, where `/dev/null` does not exist and opening it could make a host file | patch and a facts sheet for spec 043 (question 80); matplotlib's guide keeps AI tools from opening pull requests, so the owner writes it |
| `8-libxml2-input-without-dup/` | libxml2 | files read and written by name on WASI, which has no `dup()`; without it libxml2 2.15.4 does not compile for `wasm32-wasip1` | carried as `recipes/patches/libxml2-2.15.4/0001-xmlio-without-dup-on-wasi.patch` (spec 046); its facts sheet (question 80) moved to `patches/libxml2-2.15.4/0001-xmlio-without-dup-on-wasi.md`; no contributor guide found, so the owner writes it |
| `9-regex-callback-signatures/` | regex | five callbacks defined with one parameter where CPython passes two, a trap on WebAssembly | carried as `recipes/patches/regex-2026.9.29/0001-callback-signatures.patch` (spec 047), with a facts sheet (question 80); no contributor guide found, so the owner writes it |
| `10-scikit-learn-html-repr-from-a-zip/` | scikit-learn | the HTML representation's style sheets, read by path at import, so `import sklearn` fails from a zip archive | patch and a facts sheet for spec 044 (question 80); scikit-learn asks that no AI-written text go into a description, so the owner writes it |
| `11-statsmodels-datasets-from-a-zip/` | statsmodels | the bundled datasets, read by a path beside each module, so none loads from a zip archive | patch and a facts sheet for spec 045 (question 80); statsmodels asks for a disclosure, the contributor's own words and a regression test, so the owner writes it |
| `12-wasmtime-py-on-wasmtime-49-0-3/` | wasmtime-py | a release on wasmtime 49.0.3: 49.0.0's `fd_readdir` copies uninitialized host memory into the guest (GHSA-96f6-r43r-8c24, fixed in wasmtime 49.0.2), and 49.0.3 fixes a filesystem sandbox escape (GHSA-m9f7-9w4p-gv38) | a facts sheet (question 80); the Bytecode Alliance AI Tool Use Policy keeps agents from posting, so the owner asks |
| `13-numpy-callback-signatures/` | numpy | six C callbacks defined with fewer parameters than CPython passes; `copy.copy` of a numpy scalar and `a.dtype = …` trap on WebAssembly | carried as `recipes/patches/numpy-2.5.2/0002-callback-signatures.patch` (spec 051), with a facts sheet (question 80); numpy's AI policy keeps the description in the owner's words |
| `14-reportlab-zipimporter-files/` | reportlab | reportlab reads CPython's private `zipimporter._files`, gone since 3.13, so it cannot read its own files from a zip | a facts sheet (question 73(b), question 80); the owner writes the report |
| `15-wasi-libc-gb18030-decoder/` | wasi-libc (musl) | GB18030 four-byte characters above the surrogates decode 0x800 or more too low (1,617 of 56,926 BMP characters, no error); musl fixed it on master (`67219f0`, after 1.2.6), wasi-libc has not taken it | a facts sheet (question 82(d), question 80); spec 046 refuses GB18030 by a recipe until a wasi-sdk carries the fix |
| `advisories/GHSA-draft-0.1.0a3.md` | wasi-python (this project) | the GitHub security advisory for 0.1.0a1 to 0.1.0a3: the two wasmtime 49.0.0 advisories as they reach the runner (spec 048) | the text, for the owner to publish once 0.1.0a5 is on PyPI and 0.1.0a3 is yanked (question 87; 0.1.0a4 was tagged but never published) |
| `16-importlib-resources-zip-directory/` | importlib_resources (and CPython's `importlib.resources`) | `ZipReader.files()` parses the whole archive on every resource read, though zipimport already holds its directory; spec 035 answers from zipimport's dict in a recipe, so nothing here waits on it | a courtesy issue text (`issue.md`); the owner checks the project's AI-tool policy and posts it |
| `17-matplotlib-ft2font-enums/` | matplotlib | `ft2font`'s enum constants take the GIL during static initialization, which hangs a statically linked reactor before Python starts; fixed upstream by #30291 (merged for 3.12.0) | carried as `recipes/patches/matplotlib-3.11.2/0001-ft2font-enums-without-python.patch` (spec 023): upstream's merged commit whole, nothing to send; `notes.md` says how it was made and when it goes |
| `18-pillow-arrow-capsule-signatures/` | Pillow | `__arrow_c_schema__` and `__arrow_c_array__` defined with one parameter where `METH_VARARGS` passes two, a trap on WebAssembly | carried as `recipes/patches/pillow-13.0.0/0001-arrow-capsule-signatures.patch` (spec 023), with a facts sheet (question 80); the owner writes the pull request |
| `19-kiwisolver-callback-signatures/` | kiwisolver | seventeen no-argument methods and four getters defined with one parameter where CPython passes two, a trap on WebAssembly (`Solver.addConstraint`'s path among them) | carried as `recipes/patches/kiwisolver-1.5.1/0001-callback-signatures.patch` (spec 023), with a facts sheet (question 80); no contributor guide found, so the owner writes it |
| `20-wasmtime-preview1-write-on-a-read-descriptor/` | Wasmtime (`wasmtime-wasi`) | preview1's `fd_write` and `fd_read` check neither the grant's permissions nor the open mode, so a descriptor used in a mode it was not opened for answers the host's error: `EBADF` on Unix, `EACCES` on Windows; the runner states it per system (spec 076) | a facts sheet (question 80); nothing waits on it; the Bytecode Alliance AI Tool Use Policy keeps agents from posting, so the owner asks |

Each patch is against the base named in its `pr.md`. `notes.md` in each folder records how the
fix was found and checked. When a fix lands upstream and a pin moves past it, record that here
and in the CHANGELOG, and drop any workaround in the runner.

## Pull requests for carried patches

Since §4.1's amendment (question 32), a fix the project cannot wait for is carried as a patch
under `recipes/patches/<top>/` (specification 020). Its pull request lives here, at
`patches/<top>/NNNN-<slug>.md`, the same name as the patch, starting with six header lines:

```
- **Project:** <name> (<repository URL>)
- **Against:** <version> (the pinned tarball)
- **Status:** drafted | sent <url> | merged <url> | released <version, as the pinned file name writes it>
- **Title:** <the pull request's title>
- **Files:** <every path the patch touches, comma-separated>
- **Why we carry it:** <what fails without it, in this project>
```

The body is the text for the upstream maintainers, and says whether the project needs a
contributor licence agreement, which the owner signs. The owner sends it; then the status records
the link. Where a project forbids AI-written pull request descriptions (numpy does), the draft's body is the facts for the owner to write from, not the text. A draft is not a build input, so recording the status changes no `MANIFEST` line.
