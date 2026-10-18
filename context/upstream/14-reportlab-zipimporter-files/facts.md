- **Project:** reportlab (https://www.reportlab.com/; reports to reportlab-users@lists2.reportlab.com, the address the wheel's `METADATA` names)
- **Against:** 5.0.1 (the wheel spec 042 pins, SHA-256 `1c36e6bb…d791e8`; PyPI's newest, uploaded 2026-08-20)
- **Status:** drafted
- **Title:** reportlab cannot read its own files from a zip on Python 3.13 and later (`zipimporter._files` is gone)
- **Files:** src/reportlab/lib/utils.py
- **Why we carry it:** nothing is carried. reportlab's fonts stay out of the zip for good (decision 73(a)), so the guest does not need this fix. The bug hits every reportlab user who imports it from a zip on Python 3.13 or later, and the owner chose to report it (decision 73(b)).

**This is a facts sheet, not a report to paste** (question 80; decision 80). The owner writes the
message in their own words. The wheel has no contributor guide, and no reportlab rule on
AI-written reports was found (READ: the 5.0.1 wheel's files and `METADATA`; reportlab's website
was not read). So question 80's form applies. Nothing has been posted, and no agent will post
anything.

**Who it goes to.** The brief that asked for this sheet named CPython. The facts point to
reportlab. Question 73(b) also names reportlab ("report the `_files` bug to reportlab (its users'
list)"). CPython has nothing to fix: `_files` was a private attribute and was never documented.
CPython's docs list only `archive` and `prefix` as zipimporter attributes (READ:
`Doc/library/zipimport.rst`, CPython 3.14 branch `7c04882`). CPython replaced the attribute with
a cache lookup in 3.13. Code that read a private name now gets `AttributeError` (the facts below).

## The facts

1. **reportlab detects a zip install by reading a private CPython attribute.**
   `reportlab/lib/utils.py:145-152` (READ, the 5.0.1 wheel):

   ```python
   def zipImported(ldr=None):
       try:
           ...
           return ldr if isinstance(ldr,zipimporter) and len(ldr._files) else None
       except:
           return None
   ```

   The module-level `try` block at lines 273-321 calls it with the module's own `__loader__`. If
   it returns `None`, the block raises `NotImplementedError` (line 277), and the bare `except` at
   line 316 sets `__rl_loader__ = None` (line 318). Five helpers also
   read `__rl_loader__._files` directly: `rl_glob` (line 314), `rl_isfile` (587), `rl_isdir`
   (594), `rl_listdir` (600) and `rl_getmtime` (606, which reads the time and date fields of the
   table-of-contents tuple, indices 5 and 6).

2. **CPython 3.13 removed `zipimporter._files`.** In 3.12.12, `zipimporter.__init__` sets
   `self._files` (line 96), and `invalidate_caches` re-reads it (lines 266-270). In 3.13.11 and
   in the 3.15.0 tarball this project pins, the attribute does not exist. Members are looked up
   through `self._get_files()`, which reads the module-level `_zip_directory_cache`
   (`Lib/zipimport.py:215-225` in 3.15.0) (READ, each version's `Lib/zipimport.py`). The 3.13.0a1
   NEWS lists gh-103200, "Fix cache repopulation semantics of zipimport.invalidate_caches()"
   (READ, `Misc/NEWS.d/3.13.0a1.rst`). That change is very likely the one that removed the
   attribute (INFERRED: the 3.12 code it describes is the code that assigned `self._files`).

3. **So on 3.13 and later, reportlab decides it is not in a zip, and it cannot see its own
   files there.** `len(ldr._files)` raises `AttributeError`. The bare `except` turns that into
   "not zip-imported", and `__rl_loader__` becomes `None`. Each helper then answers as for a
   plain install: `rl_isfile` is `False` for a member of the zip, and `open_for_read` cannot read
   it. `isCompactDistro()` still says `True`, because it only checks that `utils.py` is not a
   real file. So reportlab half-knows it is in a zip.

4. **Reproduction, CPython alone** (EXECUTED 2026-10-18, darwin-arm64, uv-managed CPython
   3.12.12, 3.13.11, 3.14.2 and 3.15.0a3; `evidence/zipimporter_files.py`, output in
   `evidence/zipimporter_files.txt`). The script builds a one-package zip, imports from it, and
   runs reportlab's test on the package's `__loader__`:

   | Python | `hasattr(ldr, "_files")` | `hasattr(ldr, "_get_files")` | reportlab's test | `ldr.get_data(...)` |
   |---|---|---|---|---|
   | 3.12.12 | True | False | zip-imported | works |
   | 3.13.11 | False | True | `AttributeError`, so "treated as files" | works |
   | 3.14.2 | False | True | the same | works |
   | 3.15.0a3 | False | True | the same | works |

5. **Reproduction, with reportlab** (EXECUTED 2026-10-18, darwin-arm64; the 5.0.1 wheel, which is
   a zip, put first on `sys.path`; pillow 13.0.0 for the import; `evidence/reportlab_from_zip.py`,
   output in `evidence/reportlab_from_zip.txt`):

   | Python | `__rl_loader__ is None` | `rl_isfile(<wheel>/reportlab/fonts/Vera.ttf)` | `open_for_read` of it | `TTFont("Vera", <that path>)` |
   |---|---|---|---|---|
   | 3.12.12 | False | True | reads 65,932 bytes | loads |
   | 3.13.11 | True | False | `OSError` ("Cannot open resource") | `TTFError` |
   | 3.14.2 | True | False | `OSError` | `TTFError` |

   3.15.0a3 was not run with reportlab: pillow 13.0.0's `_imaging` does not load on that alpha
   (`SystemError: … unknown slot ID 85`), which has nothing to do with this bug. Spec 042 saw the
   same `TTFError` natively and in this project's 3.15.0 guest (EXECUTED there, spec 042,
   Decision 4).

6. **Who is affected (INFERRED).** Anyone who imports reportlab from a zip on Python 3.13 or
   later: a zipapp, a wheel or zip on `sys.path`, or a bundler that ships packages in a zip.
   Fonts, images and other files read by path from inside the zip are not found. Code that only
   uses reportlab's built-in standard fonts (which need no file) does not notice. On 3.12 and
   earlier it works.

## A suggested fix, in words

- **Stop reading CPython's private attributes.** In `zipImported`, `isinstance(ldr,
  zipimporter)` is enough. If an emptiness test is still wanted, use the public
  `ldr.archive` with `zipfile`, not `_files`.
- **Build reportlab's own list of member names once, through public API.** Use
  `zipfile.ZipFile(__rl_loader__.archive)`, and from it `namelist()` or `infolist()`.
  zipimport's keys use `os.sep`, and zip names use `/`. So either convert the names with
  `.replace("/", os.sep)`, or compare in `/` form (READ: 3.15.0 `zipimport.py:438`, `name =
  name.replace('/', path_sep)`). Use that list in `rl_glob`, `rl_isfile`, `rl_isdir` and
  `rl_listdir`.
- **`rl_getmtime`:** take `ZipInfo.date_time` from the same `ZipFile`, in place of the tuple's
  fields 5 and 6. It is the same MS-DOS date and time that the current code unpacks by hand.
- **Reading data** already uses the public `__rl_loader__.get_data(name)` (line 469), so it
  needs no change once `__rl_loader__` is set again.
- **A smaller stopgap** would be `getattr(ldr, "_get_files", None)` falling back to `_files`. It
  would work on 3.12, which has `_files`, and on 3.13 to 3.15, which have `_get_files` (READ,
  item 2; older versions were not read). But it still depends on private names, so it may break
  again. The public route is the lasting fix.
- **A test reportlab could add:** put a built wheel (or a zip of `src/reportlab`) first on
  `sys.path`, then assert that `rl_isfile` is true for a font under `reportlab/fonts/` and that
  `TTFont` loads it, on every supported Python (item 5 is that test).

## What the owner might say

That reportlab's zip-import support stopped working on Python 3.13, and why (items 1 to 3). Add
the short CPython-only script (item 4) and the reportlab table (item 5). Offer the fix in words.
Nothing in wasi_python waits on an answer (spec 042, Decision 4: "nothing here waits on it").
