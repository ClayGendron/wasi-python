- **Project:** scipy (https://github.com/scipy/scipy)
- **Against:** 1.18.1 (the pinned tarball)
- **Status:** drafted
- **Title:** linalg: _matfuncs_sqrtm_triu imports SqrtmError where it raises it, so the module can be imported first
- **Files:** scipy/linalg/_matfuncs_sqrtm_triu.pyx
- **Why we carry it:** scipy's compiled modules are builtins here, and pydoc's `apropos` (and `help("modules word")`) imports every builtin by name; `scipy.linalg._matfuncs_sqrtm_triu` imported first raises `ImportError` (a circular import), so `apropos` failed for every keyword (spec 037, found by CPython's own `test_pydoc` in the release run).

**This is a facts sheet, not a pull request.** scipy's AI policy (https://scipy.github.io/devdocs/dev/conduct/ai_policy.html, READ 2026-10-19 for 0001) does not permit an agent to submit a pull request, asks that no AI write the description, and requires a disclosure of what AI wrote. If the owner sends it, he writes the issue or pull request himself from these facts, with that disclosure. Nothing has been posted.

**The case.** `scipy/linalg/_matfuncs_sqrtm_triu.pyx` begins with `from ._matfuncs_sqrtm import SqrtmError`, and `scipy/linalg/_matfuncs_sqrtm.py` imports `within_block_loop` from `._matfuncs_sqrtm_triu` (its line 17, after defining `SqrtmError`). Imported through `scipy.linalg` the order is `_matfuncs_sqrtm` first, and it works. Imported first, the extension module starts, imports `_matfuncs_sqrtm`, which imports the extension module back while it is still partially initialized, and `within_block_loop` is not there yet:

    $ python -c "import scipy.linalg._matfuncs_sqrtm_triu"
    ImportError: cannot import name 'within_block_loop' from partially initialized module
    'scipy.linalg._matfuncs_sqrtm_triu' (most likely due to a circular import)

(EXECUTED natively with scipy 1.18.1's macOS arm64 wheel and CPython 3.14, 2026-10-20.)

**The change.** The import moves into the one branch that raises `SqrtmError`, so importing the module needs nothing from `_matfuncs_sqrtm`. Nothing else changes: the error class, its message and the loop are the same. The pure-Python fallback `_matfuncs_sqrtm_triu.py` (used by Pythran builds) raises `RuntimeError` and imports nothing, so it needs no change. On scipy's `main` (READ 2026-10-20) the `.pyx` keeps the top-level import and has gained `float32_t` and `complex64_t` in its fused type, so the change applies there as it does to 1.18.1.

**Seen.** With the patch, every one of scipy's 95 compiled modules imports first in the guest, and CPython's `test_pydoc` apropos tests no longer meet the `ImportError`.
