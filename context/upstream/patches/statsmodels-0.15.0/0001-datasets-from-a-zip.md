- **Project:** statsmodels (https://github.com/statsmodels/statsmodels)
- **Against:** 0.15.0 (the pinned tarball)
- **Status:** drafted
- **Title:** BUG: Load the bundled datasets when statsmodels is imported from a zip archive
- **Files:** statsmodels/datasets/elec_equip/data.py, statsmodels/datasets/utils.py
- **Why we carry it:** every bundled dataset (`sm.datasets.longley.load_pandas()` and the rest) raises `NotADirectoryError` in the guest, because statsmodels' Python files are read from the stdlib zip and `load_csv` reads each CSV by a path beside the module's `__file__`.

**This is a facts sheet, not a pull request** (question 80 in
`context/questions-for-the-owner.md`). statsmodels' AI policy, summarised below, welcomes AI
assistance but asks that no AI output be pasted into an issue or pull request description, that
the contributor understand every line, disclose the tools used, and add a regression test with
full coverage. So if you engage, you write the issue or pull request yourself, from these facts,
and add the test. Nothing has been posted, and no agent will post anything to statsmodels.

When spec 045 is built, this file moves unchanged to
`context/upstream/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.md`, and `fix.patch` is
copied byte for byte to `recipes/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.patch`. The
project carries it so the guest can load statsmodels' public-domain datasets (§4.1); carrying it
does not depend on sending anything. The evidence stays in
`context/upstream/11-statsmodels-datasets-from-a-zip/evidence/`, so every link below is a path
from the repository's top.

## What statsmodels asks of a contributor who used AI

READ on 2026-10-18 in the 0.15.0 sdist, `docs/source/dev/ai-policy.rst` ("AI Policy") and
`AGENTS.md`.

- **Responsibility:** "Personally read, understand, and be able to explain every line of the
  diff"; verify the statistics are correct; keep to statsmodels' API conventions. This change
  touches file reading only, no statistics.
- **Disclosure:** "You must disclose whether AI was used ... state in the PR description which
  tool(s) were used ... and roughly how they were used." For this change: Claude Code with Claude
  Opus 5.5 (`claude-opus-5-5`) wrote the patch and these facts; the reasoning-effort setting was
  not recorded; do not guess it.
- **Code quality:** `ruff` clean with the project's configuration (the two files pass
  `ruff check`, EXECUTED, item 10), numpydoc docstrings (the new helper has one). The helper is
  private (`_open_data_file`), so it adds no public API and needs no docs entry.
- **Testing:** "When fixing a bug, include a regression test that fails against `main` and
  passes with your change", with full coverage of new lines. `fix.patch` carries no test; one is
  sketched below for you to write.
- **Communication:** "Please don't paste raw AI output into issue or PR descriptions or review
  comments."
- **Agents:** "The use of a fully autonomous AI agent that writes code and opens a pull request
  without a human reviewing it first is not permitted." No agent will open one.
- **Commits:** subject lines tagged `BUG:` and the like (`AGENTS.md`); the title above follows
  that.
- **Licence:** contributions are under statsmodels' BSD-3-Clause licence; no contributor
  licence agreement is named.

**Checked for you** (2026-10-18): `load_csv` is unchanged on `main`
(`statsmodels/datasets/utils.py`, line 448 still `filepath = Path(base_file).resolve().parent`);
GitHub's issue search for "datasets zip" in statsmodels finds nothing about this.

## The facts

**What fails.** 28 of the 29 dataset modules load their data with
`du.load_csv(__file__, "<name>.csv")`, and `load_csv` reads
`Path(base_file).resolve().parent / csv_name` with `pandas.read_csv`
(`statsmodels/datasets/utils.py:427-455`); `elec_equip` reads its CSV by the same kind of path
(`elec_equip/data.py:66`). When statsmodels' Python files are imported from a zip archive,
`__file__` is a path inside the archive and its parent is not a directory, so every loader fails.
With statsmodels zipped on `sys.path` (tool output, `evidence/native-run.txt`, item 2):

```
longley NotADirectoryError
...
loaded 0 of 29 from sm.zip
```

and the message names the CSV inside the archive:
`NotADirectoryError: [Errno 20] Not a directory: '…/sm.zip/statsmodels/datasets/longley/longley.csv'`.

**The change** (`fix.patch`, 2 files, +41 −6). A new private helper in
`statsmodels/datasets/utils.py`, `_open_data_file(base_file, file_name)`, opens the data file
beside `base_file` in binary mode: from disk when it is a file there, exactly as before; or,
when `base_file`'s folder lies under `statsmodels/datasets/` and the file is not on disk, as a
package resource, `importlib.resources.files(package).joinpath(file_name).open("rb")`, where
`package` is `statsmodels.datasets.<subfolder>`. Any other path opens as before, so a missing
file beside a user's own module still raises `FileNotFoundError` (item 9). The first draft fell
back for every path and turned that case into a `ValueError` from `relative_to`; spec 045's
review found it.
`load_csv` passes the open file to `read_csv` with the same arguments; `elec_equip` reads through
the helper too and drops its unused `Path` import. On disk nothing changes but that `read_csv`
gets a file object instead of a path.

**How it was tested** (EXECUTED 2026-10-18, `evidence/native-run.txt`; host macOS arm64,
CPython 3.15.0, pandas 3.0.6, statsmodels 0.15.0 from PyPI):
- every dataset in `statsmodels.datasets.__all__` loaded, and a digest of each frame printed:
  stock on disk, 28 loaded (item 1); stock from a zip, 0 (item 2); patched from a zip, 28
  (item 3); patched on disk, 28 (item 4). The patched frames' digests equal the stock ones on
  disk (item 5). `elec_equip`, which is not in `__all__`, the same way: it fails from the stock
  zip and gives the stock digest patched, from the zip and from disk (item 8);
- a program that fits OLS on longley, a Logit on anes96, a Poisson GLM on randhie and ARIMA on
  the Nile, among others, prints the same bytes natively and from the patched zip (item 7;
  `evidence/statistical_models-draft.py`);
- `load_csv` with a `base_file` outside statsmodels' datasets: a missing CSV raises
  `FileNotFoundError` and a present one loads, stock on disk and patched from the zip and on
  disk (item 9).

**A test you could add.** In `statsmodels/datasets/tests/`: copy one dataset's package (its
`__init__.py`, `data.py` and CSV) and `utils.py` into a zip under `statsmodels/datasets/`, or
zip the installed `statsmodels/datasets` folder, put the zip first on `sys.path` in a subprocess
or with a fresh import of a renamed copy, and check `load_pandas().data` equals the on-disk
frame. It fails before the change (`NotADirectoryError`) and passes after. A smaller unit test:
call `_open_data_file` with a `base_file` under a path that is not a directory and a
monkeypatched `importlib.resources.files`. Which fits statsmodels' conventions, and the
coverage, is yours to judge.

**Alternatives a reviewer may raise.**
- *Pass the module's `__name__` instead of `__file__`.* Cleaner, but it changes the call in 29
  modules and the public signature of `load_csv`.
- *Always read through `importlib.resources`.* Simpler, but then `load_csv` with a `base_file`
  outside statsmodels' package (a user's own module) would stop working; the change keeps the
  disk path first.
