- **Project:** matplotlib (https://github.com/matplotlib/matplotlib)
- **Against:** 3.11.2 (the pinned tarball)
- **Status:** merged https://github.com/matplotlib/matplotlib/pull/30291
- **Title:** Migrate to Pybind11 v3
- **Files:** ci/mypy-stubtest-allowlist.txt, src/_enums.h, src/_image_wrapper.cpp, src/ft2font_wrapper.cpp
- **Why we carry it:** linked statically into a WASI reactor, `ft2font`'s enum constants run `py::gil_scoped_acquire` and `pybind11::cast` during static initialization, before `Py_Initialize`, and `_initialize` waits forever for a GIL that never comes (spec 023).

There is nothing to send. This patch is upstream's own change, already merged for matplotlib 3.12.0: commit `8e5591bcb3163d88bd9900ae74fc043c080aa631` of pull request #30291, which deletes `src/_enums.h` and binds the enums with `py::native_enum` inside module initialization. The carried file is that commit whole, made against the 3.11.2 tarball in `git diff` form so it applies with no offset: its changed lines equal the commit's in all four files, the `ci/mypy-stubtest-allowlist.txt` line included (that file builds nothing).

The patch is deleted when the pin moves to a matplotlib release that carries the commit (3.12.0 or later). The facts behind it are in [`../../17-matplotlib-ft2font-enums/notes.md`](../../17-matplotlib-ft2font-enums/notes.md).
