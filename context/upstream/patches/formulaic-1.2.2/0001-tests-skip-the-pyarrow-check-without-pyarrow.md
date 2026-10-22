- **Project:** formulaic (https://github.com/matthewwardrop/formulaic)
- **Against:** 1.2.2 (the pinned sdist, `formulaic-1.2.2.tar.gz`, a test source of spec 067)
- **Status:** drafted
- **Title:** Skip the one pyarrow assertion of test_base.py when pyarrow is absent
- **Files:** tests/materializers/test_base.py
- **Why we carry it:** our Python (CPython 3.15 for `wasm32-wasip1`) has no pyarrow.
  `tests/materializers/test_base.py` imports it at module level and uses it once, in one of the
  file's eight tests (line 51 of 1.2.2), so the other seven could not load. With
  `pytest.importorskip("pyarrow")` just before that assertion, the seven run and the one skips
  where pyarrow is absent.

The patch is
`recipes/patches/formulaic-1.2.2/0001-tests-skip-the-pyarrow-check-without-pyarrow.patch`: test
code only, no file of the `formulaic/` package changes. Written by spec 067's build (2026-10-21),
the rule of its Decision 8.

**This is a facts sheet, not a pull request.** The owner decides whether and how to engage, and
writes any issue or pull request in their own words. Nothing has been posted, and no agent will
post anything to formulaic. formulaic's repository has no contributing guide (READ, `gh api
repos/matthewwardrop/formulaic/contents`, 2026-10-21).

## The facts

**What fails.** On a Python without pyarrow, collecting `tests/materializers/test_base.py`
fails with `ModuleNotFoundError: No module named 'pyarrow'` (EXECUTED in our guest, spec 067's
survey).

**The change** (test code only): the module-level `import pyarrow` removed; `pyarrow =
pytest.importorskip("pyarrow")` before the one `FormulaMaterializer.for_data(pyarrow.Table…)`
assertion. Nothing changes where pyarrow is installed. One point to review: the test's earlier
assertions still run before the skip; upstream may prefer the skip at the test's top.

**How it was tested** (EXECUTED in our guest, spec 067's build): the file collects, and its seven
other tests run. Natively, not run; run formulaic's suite with it before sending anything.
