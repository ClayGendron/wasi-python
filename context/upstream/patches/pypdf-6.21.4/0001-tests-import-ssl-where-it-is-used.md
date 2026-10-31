- **Project:** pypdf (https://github.com/py-pdf/pypdf)
- **Against:** 6.21.4 (the pinned sdist, `pypdf-6.21.4.tar.gz`, a test source of spec 067; moved from 6.21.1 on 2026-10-30, `tests/__init__.py` the same file in both, so the patch is byte for byte the 6.21.1 one)
- **Status:** drafted
- **Title:** `TST: Import ssl where it is used in tests/__init__.py`
- **Files:** tests/__init__.py
- **Why we carry it:** our Python (CPython 3.15 for `wasm32-wasip1`) has no `_ssl`, so `import ssl` raises. pypdf's `tests/__init__.py` imports `ssl` at module level, and every pypdf test module imports `tests`, so none of pypdf's tests can load there. With the import moved into the one function that uses it, 1,689 of pypdf's tests pass in our guest (spec 067's survey, EXECUTED 2026-10-21: `context/research/2026-10-21-the-pure-python-packages-own-tests-under-the-runtime.md`).

The patch is `recipes/patches/pypdf-6.21.4/0001-tests-import-ssl-where-it-is-used.patch`: test code only, no file of the `pypdf/` package changes (the wheel tie compares those, unchanged). Drafted 2026-10-21 with spec 067's answer to its delta review (M2); committed here with its patch by 067's build.


**This is a facts sheet, not a pull request or an issue.** pypdf's `CONTRIBUTING.md` (READ on `main`, 2026-10-21, with `gh api`) allows AI coding assistance, with the contributor responsible for the code, and says: "AI should not be used to generate comments when communicating with maintainers. We expect comments on our projects to be written by humans. If you are opening an issue, we expect you to describe the problem in your own words." So the owner decides whether to engage, and writes any issue, pull request description and comment in their own words from these facts. Nothing has been posted, and no agent will post anything to pypdf. Carrying the patch does not depend on sending anything (§4.1).

## The facts

**What fails.** On a Python without the `_ssl` extension (a WASI build, or any CPython built without OpenSSL), collecting pypdf's tests fails at `tests/__init__.py`:

```
tests/__init__.py:5: in <module>
    import ssl
.../ssl.py:103: in <module>
E   ModuleNotFoundError: Standard library module '_ssl' was not found
```

(EXECUTED in our guest, 2026-10-21.) Every test module does `from tests import …`, so the whole suite fails to collect, including the many tests that never touch the network.

**Where `ssl` is used.** Only in `_get_data_from_url` (lines 46 to 48 of 6.21.1), which downloads a sample file and disables certificate checks for it. Tests that download are marked `enable_socket` and are already deselected when there is no network.

**The change** (test code only):

```diff
--- a/tests/__init__.py
+++ b/tests/__init__.py
@@ -2,7 +2,6 @@
 import functools
 import os
 import random
-import ssl
 import sys
 import tempfile
 import time
@@ -43,6 +42,8 @@
 
 
 def _get_data_from_url(url: str) -> bytes:
+    import ssl
+
     ssl._create_default_https_context = cast(
         Callable[..., ssl.SSLContext],
         ssl._create_unverified_context,
```

Nothing changes on a Python with `ssl`: the first download imports it, as the module did before. One point to review: a linter that forbids imports inside functions (pypdf's ruff settings) may need a `# noqa` or a `PLC0415` exception; check the project's configuration on `main`.

**Base.** `main` still has `import ssl` at line 5 of `tests/__init__.py` and uses it only in `_get_data_from_url` (READ by spec 067's delta review, `gh api repos/py-pdf/pypdf/contents/tests/__init__.py`, on `main` and at `6.21.1`). `gh search issues --repo py-pdf/pypdf "ssl tests import"` found no issue (2026-10-21).

**Commit message form.** pypdf's `docs/dev/intro.md` asks for `PREFIX: DESCRIPTION`; `TST` is "Adding or adjusting tests".

**How it was tested** (EXECUTED 2026-10-21, spec 067's survey, the change applied to a staged copy): in the guest, `pytest tests -m "not enable_socket"` gives 1,689 passed, 18 failed, 62 skipped and 1 xfailed; without the change, nothing collects. Natively, the change was not run; the builder runs pypdf's suite with the patch on a host CPython before the owner sends anything.
