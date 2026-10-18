# How the `_qhull` fix was found and checked

- **Found** by the research memo `context/research/2026-10-17-matplotlib-on-the-current-line.md`
  (finding 5, "Patch 2"): in the guest, every Delaunay triangulation raised
  `RuntimeError: Could not open devnull`. `src/_qhull_wrapper.cpp` opens `MPL_DEVNULL` (the
  cross file's `devnull` property, `src/meson.build:9-13`) to hide qhull's messages. A WASI
  guest has no device files, and a call may have nothing writable at all.
- **The memo's fix** tried `fopen` first and fell back to a discard stream on WASI. While
  drafting spec 043 the agent found that form makes a real file: given a writable root with a
  `dev` folder, `fopen("/dev/null", "w")` creates `dev/null` in the host's folder
  (`evidence/guest-run.txt`, item 2). In a sandbox whose host folders belong to the embedder,
  that is a side effect on the host, so the fix here opens no path on WASI at all.
- **The fix** (`fix.patch`): under `__wasi__`, `error_file` is a `fopencookie` stream whose
  write function returns the size it is given and keeps nothing. Every other platform keeps
  `fopen(MPL_DEVNULL)`. `QhullInfo`'s destructor still `fclose`s it (the stream has no close
  function, which `fopencookie` allows). wasi-libc 33 has `fopencookie` (READ by the memo with
  `llvm-nm`). A captureless lambda converts to the write function's pointer type.
- **Checked** (EXECUTED 2026-10-17, `evidence/guest-run.txt`): the object compiled from
  `fix.patch`'s file was put into a copy of the research build's `_qhull` archive and linked
  with the research's own link command. In that guest: collinear points raise qhull's
  `singular input data` error (qhull's `longjmp` path), four points give two triangles, no
  host file appears, and a larger program's Delaunay triangles, contour numbers, SVG bytes and
  RGBA buffer equal native matplotlib's. The memo's own runs used the fallback form, so they
  are evidence for that form only; the new form was linked and run anew.
- **Tests upstream.** matplotlib's CI has no WASI job, and on every platform it has the
  `#else` branch runs as before. `lib/matplotlib/tests/test_triangulation.py` already holds
  `test_delaunay`, `test_delaunay_points_in_line` and others; on WASI they exercise the new
  branch. A new test could only check the other platforms' unchanged path, so none is added.
- **Alternatives weighed.**
  - Send qhull's messages to `stderr` when `/dev/null` cannot be opened: the guest would
    print qhull's warnings, unlike native matplotlib.
  - The memo's fallback form: it writes a host file where a writable `dev` folder exists.
  - A general fallback on every platform (a discard stream wherever `fopen` fails): not
    every platform matplotlib supports has `fopencookie` (macOS has `funopen`, Windows
    neither), so it would need a branch per C library for a case only WASI meets.
- **Policy.** matplotlib's contributing guide (`doc/devel/contribute.rst`, "Use of Generative
  AI") and its pull request template are quoted in full in `pr.md` (READ in the 3.11.2 sdist
  and on `main`, `493abb1b63`). They rule out an agent opening the pull request and ask for the
  description in the contributor's own words, so `pr.md` is a facts sheet (question 80), and
  the owner decides whether to engage at all.
- **Revised 2026-10-18** against spec 043's pre-build review
  (`context/reviews/043-matplotlib-second-milestone-spec-2026-10-17.md`, finding 2): the
  policy quoted whole, `main`'s "breadth" item and the template added, and the platform claim
  about `fopencookie` narrowed to what was checked.
