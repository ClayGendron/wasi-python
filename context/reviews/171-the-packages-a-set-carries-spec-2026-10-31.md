# Review of 171 — The packages a set carries

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** the specification as drafted, `context/specifications/171-the-packages-a-set-carries.md` (uncommitted), with its `decisions.md` entry and roadmap sentence, on `docs/specification-171-packages` from `dev` at `30566232`
- **Run:** none: a specification review
- **Re-ran:** short `uv run python -I` scripts over the built zip of the 166 worktree (`build/artifacts/python-stdlib.zip`, read-only); the host's `importlib.metadata` on a zip with no `Name` under Pythons 3.11, 3.12, 3.13, 3.14 and 3.15; function lengths by `ast`; with this file written, `uv run pytest tests/lint -q` → 14 passed, exit 0. No `gh` call, no run dispatched, no guest started.
- **Time box:** 45 minutes (build recipe and public API); kept.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning.

EXECUTED: the zip has 6,262 members and 53 `.dist-info` folders, each with `METADATA` (7 also with `entry_points.txt`), no `.egg-info`, and no root member that is not a module. The host's `importlib.metadata.distributions(path=[zip])` finds the same 53, with Names as written (`Jinja2`, `MarkupSafe`, `PyYAML`, `charset-normalizer`). The zip's top-level names outside the stdlib include `tlz`, `isympy`, `pylab` and `mpl_toolkits`, a namespace folder with no `__init__`, which bears out Decision 2. Every builtin in `build/link/inittab.c` sits under a top-level name the zip holds (`scipy` 190, `sklearn` 138, `pandas` 90, `statsmodels` 52, `numpy` 26, `matplotlib` 14, `PIL` 6, `lxml` 4, `regex`, `kiwisolver`, `contourpy`). So deriving names from the zip misses no compiled package. Fifty-three `top_level.txt` members, deflated at level 9 under the real folder names, add 8,939 bytes.

READ: `AGENTS.md`; constitution §4 and §5.6; `context/reviews/README.md`; the files the specification cites, at the lines it gives, all of which match. Also `recipes/zip_resources.py:237-252`, CPython 3.15.2's `importlib/metadata/__init__.py` (`FastPath`, `Lookup`, `packages_distributions`), `tests/checks/test_rules.py:1609-1630`, `tests/unit/test_process.py`, `tests/unit/test_runner_package.py`, `tests/harness/api.py`, `tests/harness/paths.py:259-304`, `tests/unit/test_build_scripts.py:258-430`, the specifications 165, 167, 169 and 170, and `docs/reference/cli.md`, `packages.md` and `limitations.md`.

## Acceptance criteria against evidence

1. Unit rows — testable. The count of zip opens needs a stated method (Finding 6). The "missing Name" row behaves differently on each host Python (Finding 3).
2. Build rows — testable. The rule leaves four cases open (Finding 4).
3. Command rows — testable. The usage text is ambiguous (Finding 8).
4. Oracle and coverage — the coverage set as written cannot be green (Finding 2). The oracle proves the reader, not the names (Finding 6).
5. The contract — sound for `public_api.txt`, the one verdict-bearing file. The judge change is wider than Design names (Findings 1 and 5).
6. The set — sound. What to measure is listed in Finding 7.
7. The documents — sound.
8. The run — sound once Finding 1 is answered.

## Findings, most severe first

1. **Medium: the new field breaks the long-function allowance, and the Kind line says otherwise** (`tests/checks/test_rules.py:1620`; `src/wasi_python/_process.py:117-200`). `_Process.__init__` is 84 lines (EXECUTED) and is listed at exactly 84; a listed function at any other length is red. Failure: the builder adds `self.packages` as Decision 4 says, and `test_no_function_is_over_eighty_lines` goes red at 85. The Kind line's "every function under 80 lines" does not hold. Fix text: Kind: "one field joins `_Process`, whose `__init__` goes from 84 to 85 lines in `LONG_FUNCTIONS`, claimed under the news file's `[claim.judge]` (the process object's fields, one line each)". Design adds `tests/checks/test_rules.py`, and `tests/unit/test_process.py`, where `packages` joins `KEPT` because a fork keeps it, as it keeps `versions`. Not structural still holds: the function was already past 80 lines, and the rubric rows do not move.
2. **Medium: the coverage check's exact set leaves out `_missing_stdlib_info`** (Decision 7; `tests/harness/paths.py:262`). Step 70 packs `_missing_stdlib_info.py` at the zip's root (`70_zip.sh:192`). The name is not in CPython 3.15.2's `Python/stdlib_module_names.h`, nor in `REACTOR_MODULES` or `CPYTHON_UNLISTED_*`. So `zip_non_stdlib_names` returns it (EXECUTED against that header). Failure: on the new set the residual is `{"_missing_stdlib_info", "host", "reportlab_mods", "reportlab_settings"}`, and criterion 4 cannot be green as written. Fix text: "`_missing_stdlib_info` joins `CPYTHON_UNLISTED_NAMES` in `tests/harness/paths.py`, with its reason in the comment: CPython's build generates it beside `_sysconfigdata`." That also corrects the labels of `test_the_snapshot_pre_imports_no_package`.
3. **Low: Decision 1 misdescribes the guest's reader, and the host's reading of a missing key differs by version.** The guest's metadata search does not use `zipfile.Path`. It uses `_zip_resources.ZipDirectoryPath` over zipimport's dict (`recipes/zip_resources.py:237-252`). Only the `METADATA` bytes and the email parser are shared. Failure: on a folder with no `Name`, `metadata["Name"]` gives `None` on host 3.11, `None` plus a `DeprecationWarning` on 3.12 to 3.14, and `KeyError` on 3.15 (EXECUTED); `.version` reads the same way. Fix text: "The host reads each folder as `PathDistribution(zipfile.Path(zf, folder + "/"))`, inside `with zipfile.ZipFile(path) as zf`, and takes Name and Version with `metadata.get(...)`, never `[...]` or `.version`. The guest reads the same bytes with its own path class, and the oracle holds the two equal. The host does not call `importlib.metadata.distributions(path=[zip])`: its `FastPath` is cached per root for the life of the process and its lookup per `st_mtime`. That would defeat Decision 4's full-stamp key and keep the zip open (CPython `FastPath.__new__`, `lookup`)."
4. **Low: Decision 3 leaves four cases to the builder** (`scripts/make_stdlib_zip.py:409-445`). Fix text: "(a) A wheel's `*.dist-info` and `*.data` first parts are never names. (b) A name owned by two inputs, a wheel and a tree or two wheels, stops the build, naming both. A namespace that two distributions share is decided when one arrives. (c) A distribution that ends with no name stops the build. So `--metadata` without `=<names>` is refused, and `--entry-points` keeps the bare PKG-INFO path. (d) `--metadata` splits on its last `=`. The owners are kept in a small class beside `Selection`, so `main`, already 98 lines (EXECUTED), grows by a few lines only."
5. **Low: Design names fewer judge files than the build will change.** Fix text: Design adds the following. In `tests/unit/test_build_scripts.py`, `test_a_left_out_folder_is_not_packed` and the entry-points row, whose exact `namelist()` gains `top_level.txt`. In `tests/harness/api.py`, `_packages.py` in `INTERNAL_FILES` and `DEFINING`. In `tests/unit/test_runner_package.py`, `_packages` in `ORDER` after `_artifacts`. Only `tests/public_api.txt` needs the `[claim.judge]` line; the rest is recorded by the judge's hash.
6. **Low: the oracle is the same file read twice.** Both sides split the one `top_level.txt`, so equality proves the host's reader. It does not prove that each name imports. Fix text, Decision 7: "The guest program also asserts `importlib.util.find_spec(n) is not None` for every listed name; it imports nothing. Criterion 1's 'opens no zip' is counted by a counting stand-in for `zipfile.ZipFile` in `_packages`'s namespace, set by `monkeypatch`."
7. **Low: the growth is estimated; criterion 6 should name what to measure.** Fifty-three members of about 170 bytes each come to 8,939 bytes (EXECUTED, placeholder contents). Fix text, criterion 6: "Recorded from the pull request's build: the zip's members (6,262 to 6,315) and bytes; the snapshot's bytes, since zipimport's directory lives in the image; the wheel's bytes against 104,857,600, the margin 167, 169 and 170 share; a plain start's fuel, since `_zip_directory` reads 53 more entries; the snapshot start's fuel, expected unchanged, with any move explained; and the fuel of one guest `packages_distributions()`, which now reads 53 files where it read none. Each growth is claimed."
8. **Low: the command's usage and the docs.** `USAGE` (`cli.py:34`) is `run`'s parser's `usage=`, so changing it changes `wasi-python run --help` and the `run` section of `cli.md`. Fix text, Decision 6: "A new top-level usage of two lines, one per command, is printed by `-h` and on an unknown command. `USAGE` stays `run`'s." Decision 8: the section goes before "In one line". It says that `make_package_snapshot(packages=...)` takes the names, `[p.name for p in packages()]`, and not the `Package` objects, which it refuses.
9. **Low: the host reads a set it has not checked** (§4.15). Fix text, Decision 1: "Each member read is at most 1 MiB, the guest's own bound. A Name, a Version or an import name with a control character, a newline included, raises `ArtifactsMissing` naming the folder, so no line of a prompt is split. The cache key's stamp is taken as `_digest` takes it (`_artifacts.py:224-243`): opened by descriptor and checked with `os.path.samestat`."
10. **Low: the Depends-on line names the wrong siblings.** 169 links libzstd into the binary and adds no distribution. 170 says the zip does not grow (READ). Fix text: "In flight: 165 and 167 add `--metadata` lines to step 70. Whichever of them lands after 171 writes its names in Decision 3's form, and the claim check stops a build that does not. If 171 lands last, it writes theirs (`docx`, `pptx`, and those of pdfminer.six, plotly and xarray)."

## Constitution checks

- §4.1: no upstream patch; a recipe change only. Holds.
- §4.2 and §4.8: no new input. Holds.
- §4.6: the zip, the snapshot, `MANIFEST` and `SHA256SUMS` change, and criterion 6 records them. Holds.
- §4.9: the cache is counted by opens, not timed. Holds.
- §4.10: one dependency claim is wrong (Finding 10). The growth is labelled INFERRED, and Finding 7 measures it.
- §4.15: the host reads an unchecked set. That is acceptable, as `artifacts()` reads `MANIFEST`, once Finding 9 bounds it.
- §5.6: the reviewed class is the build recipe; this review is the pre-build review.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Taken, by avoiding the raise: a module-level `_Stamped` alias takes line 147's stamp comment, which becomes the `packages` field, so `__init__` stays at its listed 84; `packages` joins `KEPT`, and the Kind line says so (Decision 4).
2. Taken: `_missing_stdlib_info` joins `CPYTHON_UNLISTED_NAMES` with its reason, and `tests/harness/paths.py` joins Design (Decision 7).
3. Taken: `PathDistribution(zipfile.Path(...))` inside `with`, `metadata.get(...)`, no `distributions(path=[zip])`, the guest's own path class named (Decision 1).
4. Taken: the four rules written into Decision 3.
5. Taken: the judge files listed in Design; only `tests/public_api.txt` takes a `[claim.judge]` line (criterion 5).
6. Taken: `find_spec` for every listed name in the guest program (Decision 7), and the counting stand-in for `zipfile.ZipFile` (criterion 1).
7. Taken: criterion 6 lists the measures; Decision 3 gives about 9 KB.
8. Taken: `USAGE` stays `run`'s and a two-line top-level usage is added (Decision 6); the section's place and the `make_package_snapshot` note are in Decision 8.
9. Taken: the 1 MiB bound, the control-character refusal and the stamp taken as `_digest` takes it (Decisions 1 and 4).
10. Taken: Depends on names 165 and 167 only, with the order rule.

## Verdict

Fit to build after amendments: Finding 1, the 84-to-85 `LONG_FUNCTIONS` raise with its claim and `KEPT` row, and Finding 2, `_missing_stdlib_info` in the coverage rule, are written into the specification; Findings 3 to 10 are fix text the builder applies.

Confirmed after amendments, 2026-10-31: Fit to build. I read the amended specification whole against the ten findings, and each is in the Decision or criterion that its Disposition line names. Medium 1 avoids the raise. Line 147 of `src/wasi_python/_process.py` on `dev` is the stamp comment, and it becomes the `packages` field one line for one line. So `_Process.__init__` stays at 84 lines, lines 117 to 200 (EXECUTED by `ast`), its listed length. `_Stamped`, a type alias, is not a mutable that `test_no_mutable_is_bound_at_module_level_outside_the_process` counts, and `_process.py` is the owner in any case. The field's `Package` annotation follows the module's existing `TYPE_CHECKING` imports of sibling types. Medium 2 is taken in Decision 7 and Design. One Low stays open and does not block: criterion 2's build rows should also cover the new rules of Decision 3, which are a name owned by a wheel and a tree, a distribution left with no name, and `--metadata` without `=<names>`. The builder adds them, each seen failing first.
