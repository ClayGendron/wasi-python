- **Project:** lxml (https://github.com/lxml/lxml)
- **Against:** 6.1.3 (the pinned tarball)
- **Status:** merged https://github.com/lxml/lxml/pull/477
- **Title:** Support freethreading Python
- **Files:** src/lxml/html/diff.py
- **Why we carry it:** the guest runs `lxml.html.diff` as plain Python (spec 046, Decision 1) with no Cython installed, and its stand-in `fake_cython` has no `final`, so `@cython.final` calls the string `"object"` and `import lxml.html.diff` raises `TypeError: 'str' object is not callable` (spec 066's survey; spec 096).

There is nothing to send. Upstream already has this line: commit `dce45bd6e9` (2026-05-25) of pull request #477, "Support freethreading Python" (<https://github.com/lxml/lxml/pull/477>), adds `def final(self, func): return func` to `fake_cython` in `src/lxml/html/diff.py`. It is on `master` and in the 7.0.0 pre-releases (`7.0.0a1` to `7.0.0b1`), not on the `lxml-6.1` branch and in no final release (READ, GitHub and PyPI, 2026-10-20: 6.1.3 is the newest final).

The carried file is that one line, not the whole commit (which adds free-threading support across lxml), made against the 6.1.3 tarball in `git diff` form. Its added line equals the commit's in `src/lxml/html/diff.py`, at the same place, after `cclass` (READ, the commit's diff). So this draft's title is the pull request's, and the patch is one line of it.

When spec 096 is built, this file moves unchanged to `context/upstream/patches/lxml-6.1.3/0001-fake-cython-final.md`, and `fix.patch` is copied byte for byte to `recipes/patches/lxml-6.1.3/0001-fake-cython-final.patch`.

## The facts

- **The defect** (READ, `src/lxml/html/diff.py` in 6.1.3). When `import cython` fails, the module defines `fake_cython` with `compiled`, `cfunc`, `cclass` and `declare`, and a `__getattr__` that answers every other name with the string `"object"` (so annotations such as `cython.Py_ssize_t` work). Line 949 decorates `InsensitiveSequenceMatcher` with `@cython.final`, which is then `"object"(cls)`. None of lxml's other plain-Python fallbacks (`builder`, `sax`, `_elementpath`, `html/_difflib`) uses a decorator `fake_cython` lacks (READ, `grep`).
- **Why upstream never saw it.** lxml's builds compile `lxml.html.diff` with Cython, and its test environments install Cython, so `import cython` succeeds there. The plain module runs only where the compiled one is absent and Cython is too, as in this project's guest.
- **Native shows it too** (EXECUTED, spec 096, `context/research/2026-10-20-the-slot-scan/native-runs.out`): CPython 3.15.0 with lxml 6.1.3's wheel and no Cython, loading the sdist's `diff.py` as `lxml.html.diff`, raises the same `TypeError`; with the line added it loads.
- **The guest** (EXECUTED, `guest_patched_diff.out` beside it): on main's set, the same loader raises the `TypeError` on both binaries; with the line added, `htmldiff("<p>Hello world</p>", "<p>Hello there world</p>")` returns native's `<p>Hello <ins>there</ins> world</p>`.
- **When to delete it:** when the pin moves to lxml 7.0.0 or later; this draft's status then becomes `released 7.0.0`, which the judge refuses while the patch stays. If the owner wants a 6.1.x release to carry it, a one-line backport to the `lxml-6.1` branch is the pull request to send (the owner's choice; not needed for this project).
