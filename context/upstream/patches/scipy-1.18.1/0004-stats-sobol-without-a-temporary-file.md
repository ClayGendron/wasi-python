- **Project:** scipy (https://github.com/scipy/scipy)
- **Against:** 1.18.1 (the pinned tarball)
- **Status:** drafted
- **Title:** stats: load Sobol's direction numbers without a temporary file
- **Files:** scipy/stats/_sobol.pyx
- **Why we carry it:** in a zipped install with no writable temporary folder, `qmc.Sobol` silently gets all-zero direction numbers and returns wrong points with exit status 0.

**This is a facts sheet, not a pull request.** scipy's AI policy
(https://scipy.github.io/devdocs/dev/conduct/ai_policy.html, READ 2026-10-20) does not permit an
agent to submit a pull request, asks that no AI write the description, and requires a disclosure
of what AI wrote (the quotations are in this folder's `0003-…md`). If the owner sends it, he
writes the issue or pull request himself from these facts, with that disclosure. Nothing has been
posted.

**What is wrong.** `scipy/stats/_sobol.pyx`, `_initialize_direction_numbers` (lines 147-150),
loads `_sobol_direction_numbers.npz` with
`with importlib.resources.as_file(_npzfile) as f: dns = np.load(f)`. `as_file` exists to give a
filesystem path to code that needs one: when scipy is installed inside a zip it copies the
589,334-byte member to a temporary file first. Where no temporary folder is writable that copy
raises; the function is called from a `noexcept` function, so Python prints "Exception ignored"
and the direction numbers stay zero. Unscrambled, every point is 0; scrambled (the default), one
point repeats in every row; `qmc_quad`, `sobol_indices`, `differential_evolution(init='sobol')`
and `shgo(sampling_method='sobol')` inherit it.

**The change.** `np.load` reads an `.npz` from a file object, so the path is not needed:
`dns = np.load(io.BytesIO(_npzfile.read_bytes()))`, with `import io`. The same bytes are read
once into memory and never written. It works from a folder and from a zip, and a zipped or
read-only install then needs no writable temporary folder.

**How it is checked** (this project's spec 038; the result is written here when its build has
run). In this project's statically linked CPython for `wasm32-wasip1`, whose library is one zip
and whose default call grants nothing writable, `qmc.Sobol(d=2, scramble=False).random(4)` must
give `[[0, 0], [0.5, 0.5], [0.75, 0.25], [0.25, 0.75]]`, and a seeded scrambled draw must equal
native scipy's, on both of its binaries.
**Result** (2026-10-20, the build of spec 038): both hold on both binaries; without the
patch every point was 0.

It is deleted, and the pin moved, when a scipy release carries the fix.
