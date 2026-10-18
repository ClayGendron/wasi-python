# How reportlab's `zipimporter._files` bug was found and checked

- **Found** while drafting spec 042 (2026-10-17): reportlab's fonts could not be read from the
  zip, in the guest or natively with reportlab zipped on `sys.path` (spec 042, Decision 4,
  EXECUTED there). Its pre-build review confirmed the reading of `reportlab/lib/utils.py:150`
  (`context/reviews/042-seaborn-and-reportlab-spec-2026-10-17.md`, "The zip-loader bug (READ)").
  Question 73(b) asked whether to report it. The owner said yes, as a facts sheet (decision
  73(b), in question 80's form).
- **Read again for this sheet** (2026-10-18):
  - reportlab 5.0.1's `reportlab/lib/utils.py`, from the wheel downloaded from spec 042's pinned
    URL into a scratch folder outside the repository. Its SHA-256 equals the pin
    (`1c36e6bb0e71780c72331eba60da7f602e8d4389a8723825af71342e49d791e8`, EXECUTED `shasum -a
    256`). PyPI's newest reportlab is still 5.0.1 (EXECUTED, PyPI's JSON API, 2026-10-18).
  - `Lib/zipimport.py` of the uv-managed CPython 3.12.12 and 3.13.11, and of the pinned 3.15.0
    tree in the main tree's `build/Python-3.15.0/` (read only).
  - CPython's `Doc/library/zipimport.rst` and `Misc/NEWS.d/3.13.0a1.rst` in
    `context/prior_art/cpython` (branch 3.14, `7c04882`).
- **Reproduced** (EXECUTED 2026-10-18, darwin-arm64, `uv run --no-project --python <v> python
  -I`, run from the session's scratch folder):
  - `evidence/zipimporter_files.py` → `evidence/zipimporter_files.txt`: standard library only,
    on 3.12.12, 3.13.11, 3.14.2 and 3.15.0a3 (the uv-managed interpreters on this machine; no
    final 3.15.0 host build is installed).
  - `evidence/reportlab_from_zip.py WHEEL` → `evidence/reportlab_from_zip.txt`: with `--with
    pillow==13.0.0`, on 3.12.12, 3.13.11 and 3.14.2. Not on 3.15.0a3, where pillow 13.0.0 does
    not load (recorded in the output).
- **Not established:** whether reportlab has a rule on AI-written reports (its website was not
  read). Whether reportlab's own repository already changed `zipImported` since 5.0.1: only the
  released wheel was read. The owner may want to look at reportlab's current source before
  writing.
- **README row, for when this lands** (for `context/upstream/README.md`'s table):
  `| 14-reportlab-zipimporter-files/ | reportlab | reportlab reads CPython's private zipimporter._files, gone since 3.13, so it cannot read its own files from a zip | a facts sheet (question 73(b), question 80); the owner writes the report |`
