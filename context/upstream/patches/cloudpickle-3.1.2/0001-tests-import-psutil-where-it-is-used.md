- **Project:** cloudpickle (https://github.com/cloudpipe/cloudpickle)
- **Against:** 3.1.2 (the pinned release tag's archive, `cloudpickle-3.1.2-tag.tar.gz`, a test source of spec 067)
- **Status:** drafted
- **Title:** Import psutil where the tests use it, so the suite loads without it
- **Files:** tests/testutils.py
- **Why we carry it:** our Python (CPython 3.15 for `wasm32-wasip1`) has no psutil, a compiled package. `tests/testutils.py` imports it at module level and uses it once, in `_Worker.memsize` (line 166 of 3.1.2), and `tests/cloudpickle_test.py`, most of cloudpickle's suite (139 test functions), imports `testutils`, so none of those tests could load. With the import moved into `memsize`, only the tests that measure a worker's memory need psutil.

The patch is `recipes/patches/cloudpickle-3.1.2/0001-tests-import-psutil-where-it-is-used.patch`: test code only, no file of the `cloudpickle/` package changes. Written by spec 067's build (2026-10-21), the rule of its Decision 8.

**This is a facts sheet, not a pull request.** The owner decides whether and how to engage, and writes any issue or pull request in their own words. Nothing has been posted, and no agent will post anything to cloudpickle. Carrying the patch does not depend on sending anything (§4.1). cloudpickle's repository has no contributing guide (READ, `gh api repos/cloudpipe/cloudpickle/contents`, 2026-10-21); check its pull request template before writing.

## The facts

**What fails.** On a Python without psutil, collecting `tests/cloudpickle_test.py` fails at `from .testutils import …` with `ModuleNotFoundError: No module named 'psutil'` (EXECUTED in our guest, spec 067's survey).

**The change** (test code only): remove `import psutil` from the module's imports, and add `import psutil` as the first line of `_Worker.memsize`'s return path. Nothing changes where psutil is installed.

**How it was tested** (EXECUTED in our guest, spec 067's build, `cloudpickle-smoke`): the whole `tests/` folder collects, and the tests that do not measure memory run. Natively, the change was not run; run cloudpickle's suite with it on a host CPython before sending anything.
