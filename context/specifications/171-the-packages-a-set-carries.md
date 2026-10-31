# 171: The packages a set carries

- **Status:** drafted 2026-10-31, to be reviewed before it is built (public API, and the build recipe: the zip gains a file per distribution). The owner asked for it on 2026-10-31 and chose its three answers the same day (`../decisions.md`, "The packages a set carries"). Amended the same day against its pre-build review, `../reviews/171-the-packages-a-set-carries-spec-2026-10-31.md` ("Fit to build after amendments"), every finding taken (its Disposition).
- **Date:** 2026-10-31
- **Owner:** Clay Gendron
- **Kind:** public API (`Package`, `packages`, the command `wasi-python packages`); build recipe (constitution §5.6): `scripts/make_stdlib_zip.py` writes a `top_level.txt` into each distribution's `.dist-info`, so the zip, the snapshot, `MANIFEST` and `SHA256SUMS` change; a judge change (Design's Judge line). Not structural: one field joins `_Process` and its `__init__` stays at its listed 84 lines (Decision 4); no module-level mutable, private wasmtime API or platform branch.
- **Depends on:** landed: 033 and 039 (each distribution's `METADATA` in the zip), 035 and 041 (the guest's `importlib.metadata` reads the zip's directory), 157 (`x-snapshot-package`, kept apart, Decision 2). In flight: 165 and 167 add `--metadata` lines to step 70 (169 and 170 add no distribution). Whichever lands after 171 writes its names in Decision 3's form, and the claim rule stops a build that does not; if 171 lands last, it writes theirs.
- **Research it stands on:** the owner's request of 2026-10-31. **Drafting reads** (READ): the files cited, CPython's `importlib/metadata/__init__.py:1147-1209`, and 0.1.2's built zip (6,262 members, 53 `.dist-info` folders).

Labels: EXECUTED means run and seen; READ means read from a file, cited; INFERRED means reasoned.

## The problem

A developer who hands the interpreter to an agent wants to tell it what it can import. Today they read the packages page, or run a guest over `importlib.metadata.distributions()`. Neither gives the import name: an agent told "scikit-learn" writes `import scikit_learn`.

The zip keeps each distribution's `METADATA` and `entry_points.txt` and drops `top_level.txt` and `RECORD` (`scripts/make_stdlib_zip.py:110`, `:149-164`). So the guest's `packages_distributions()` returns `{}`: it reads `top_level.txt`, else `files()`, which is `None`.

## Decisions

### 1. `packages()` and `Package`

```python
@dataclass(frozen=True, slots=True)
class Package:
    name: str                  # METADATA's Name, as the distribution writes it
    version: str               # METADATA's Version
    imports: tuple[str, ...]   # the top-level names it puts on the import path

def packages(artifacts: Artifacts | None = None) -> tuple[Package, ...]: ...
```

One `Package` per distribution the guest's `importlib.metadata.distributions()` finds in the zip, sorted by PEP 503's normalized name. `None` finds the set with `artifacts()`; a non-`Artifacts` is a `TypeError`.

It starts no guest and loads no wasmtime. Inside `with zipfile.ZipFile(path) as zf`, it reads each top-level `*.dist-info` folder as `importlib.metadata.PathDistribution(zipfile.Path(zf, folder + "/"))`, taking Name and Version with `metadata.get(...)`, never `[...]` or `.version`, whose answer to a missing key differs from host 3.11 to 3.15. The imports are `read_text("top_level.txt")` split on whitespace; a folder without one (a set from 0.1.2 or before) gives `()`. The guest reads the same bytes through its own path class (`recipes/zip_resources.py:237-252`); Decision 7 holds the two equal. It never calls `distributions(path=[zip])`: its `FastPath` cache, per root and `st_mtime`, would defeat Decision 4's key and keep the zip open.

It checks nothing against `SHA256SUMS`: it runs nothing, as `artifacts()` does. So it bounds what it reads. Each member is at most 1 MiB. A Name, a Version or an import name with a control character, a newline included, raises `ArtifactsMissing` naming the folder, so no prompt line is split. So do a missing Name or Version and a zip that cannot be read, as `_found_and_checked` does (`src/wasi_python/_artifacts.py:182-221`).

The C libraries, the build tools and the interpreter's components have no `.dist-info`, so are not listed (the owner's first answer); nor are `host` and the stand-ins step 70 packs with `--file`.

### 2. Import names come from the zip, not from `snapshot-packages.txt`

`recipes/snapshot-packages.txt` is hand-written for loading an image. It names submodules and C libraries' stdlib modules, and misses names the zip holds: `tlz`, `isympy`, `pylab` and `mpl_toolkits` (READ). The build knows what it packed.

### 3. The build writes each distribution's `top_level.txt`

`make_stdlib_zip.py` records each input's top-level names: a folder's first part, or a root module's stem, of every member `add` took (`:409-424`).

- **A wheel** owns its members' names; its own `top_level.txt` stays dropped.
- **A tree** has no owner of its own: `pure-install` holds four sdists' packages. So `--metadata` takes the names, `<PKG-INFO>=<name>[,<name>...]`. In step 70 (`scripts/steps/70_zip.sh:146-161`), `--metadata "$B/matplotlib-3.11.2/PKG-INFO=matplotlib,mpl_toolkits,pylab"` and `--metadata "$B/pyyaml-6.0.3/PKG-INFO=yaml"`.
- **`--lib` and `--file`** own nothing.

Four rules close it. A wheel's `*.dist-info` and `*.data` first parts are never names. A name owned by two inputs (a wheel and a tree, two wheels, two claims) stops the build, naming both; a namespace two distributions share is decided when one arrives. A distribution left with no name stops it, so `--metadata` without `=<names>` is refused; `--entry-points` keeps the bare PKG-INFO path. `--metadata` splits on its last `=`. The build also stops on a tree's name no `--metadata` claims, and on a claim of a name no tree packed. The owners live in a small class beside `Selection`, so `main`, already 98 lines, grows by a few only. Then it writes each `<dist-info>/top_level.txt`, names sorted, one per line, by `member` (`:303`): setuptools' format, which `importlib.metadata` reads.

The zip gains 53 members, about 9 KB. The guest's `packages_distributions()` now answers; `limitations.md:73` says so.

### 4. The cache

`process().packages`, in group E of `src/wasi_python/_process.py:143-150`, keyed by the zip's resolved path and its full stamp, taken as `_digest` takes it (`_artifacts.py:224-243`): by descriptor, checked with `os.path.samestat`. A second call on an unchanged zip opens nothing; a zip replaced in place is read again. Unlocked: a race only reads twice. `packages` joins `KEPT` in `tests/unit/test_process.py`: a fork keeps it, as it keeps `versions`.

`_Process.__init__` is listed at 84 lines (`tests/checks/test_rules.py:1620`) and stays there. A module-level type alias, `_Stamped`, takes the stamp comment of line 147, which becomes the new field; `versions` and `digests` use the alias. An alias is not mutable state.

### 5. `str(Package)` is the line for a prompt

`str(p)` is `scikit-learn 1.9.1 (import sklearn)`, the names joined by `, `, or `name version` alone when `imports` is empty. The command prints these lines, so the command and the one-liner agree:

```python
prompt = "Python packages you can import:\n" + "\n".join(map(str, packages()))
```

No second public function: `str` is the helper. The text, like a `repr`, is for reading; the JSON is the contract.

### 6. The command `wasi-python packages`

```
$ wasi-python packages
attrs 26.1.0 (import attr, attrs)
beautifulsoup4 4.15.0 (import bs4)
...
$ wasi-python packages --json
{"packages": [{"imports": ["attr", "attrs"], "name": "attrs", "version": "26.1.0"}, ...]}
```

The JSON is one line by `cli._write` (`cli.py:223`): an object, so a later key can join it. `WASI_PYTHON_ARTIFACTS` chooses the set, as for `run`.

Exit codes are `run`'s: 0, printed; 1, `packages()` raised (under `--json` the `{"error", "kind"}` line, else `wasi-python packages: <message>` on standard error); 2, a usage error.

`_main` (`cli.py:273`) dispatches `packages` to a new `_packages_main`, with its own `_packages_parser()`. `USAGE` (`cli.py:34`) stays `run`'s parser's; a new top-level usage of two lines, one per command, is printed by `-h` and on an unknown command. The module docstring says so.

`tests/harness/cli_doc.py` renders `_parser()` and `_packages_parser()` as two sections of the one block, so `docs/reference/cli.md` regenerates with `--write`.

### 7. The oracle: the guest's own `importlib.metadata`

A goal check in `tests/checks/test_v1_3_data_stack.py`, beside `test_packages_carry_their_metadata` (`:442`), on both binaries. The guest prints, for each `d` in `distributions()`, `[d.metadata["Name"], d.version, sorted(names)]`, where `names` are the keys of `packages_distributions()` whose list holds the Name. The host's `[[p.name, p.version, list(p.imports)] for p in packages()]` must equal it, sorted alike. That proves the reader; so the guest also asserts `importlib.util.find_spec(n) is not None` for every listed name, importing nothing, and every package has at least one name, so it fails on 0.1.2's set.

A second check holds the coverage. The zip's top-level names that are neither the stdlib's nor the reactor's (`zip_non_stdlib_names`, `:183`), less every package's `imports`, are exactly `{"host", "reportlab_mods", "reportlab_settings"}`. `_missing_stdlib_info` joins `CPYTHON_UNLISTED_NAMES` (`tests/harness/paths.py:262`), its comment saying that CPython's build generates it beside `_sysconfigdata`; that also corrects `test_the_snapshot_pre_imports_no_package`'s labels. It fails first on 0.1.2's set, where no name is claimed.

### 8. Use in a system prompt

The packages page gains a section before "In one line", "Tell an agent what it can import". It shows the one-liner and the command. The list is the set's, not the host's; a grant's `import_path=` adds packages it does not show. Each line gives the name to import. `make_package_snapshot(packages=...)` takes the names, `[p.name for p in packages()]`, not the `Package` objects.

## Intent

`packages()` and `wasi-python packages` list each distribution in the set with its version and import names, read on the host, equal to the guest's `importlib.metadata`.

## Design

- **Host:** `src/wasi_python/_packages.py`, new, about 100 lines (`Package`, `packages`, the reader); `_process.py` (the field); `__init__.py` (the import, `__all__`); `cli.py` (`_packages_main`, `_packages_parser`, the dispatch, the docstring).
- **Recipe:** `scripts/make_stdlib_zip.py` (the owners, the claims, `top_level.txt`, its docstring); `scripts/steps/70_zip.sh` (each `--metadata` with its names; its comment).
- **Judge:** `tests/unit/test_packages.py`, new; rows in `tests/unit/test_cli.py` and `test_cli_doc.py`; in `test_build_scripts.py` the new rows, and `test_a_left_out_folder_is_not_packed` and the entry-points row, whose `namelist()` gains `top_level.txt`; the two checks of Decision 7; `tests/harness/cli_doc.py`; `tests/harness/api.py` (`_packages.py` in `INTERNAL_FILES` and `DEFINING`); `tests/harness/paths.py`; `tests/unit/test_runner_package.py` (`_packages` in `ORDER` after `_artifacts`); `tests/unit/test_process.py` (`KEPT`); `tests/public_api.txt`, the one verdict-bearing file.
- **Documents:** `docs/reference/packages.md` (Decision 8); `docs/reference/cli.md` and `python-api.md`, regenerated; `docs/reference/limitations.md:73`.

## Scope

In: Decisions 1 to 8. Out: the C libraries and the interpreter's components; packages on an embedder's `import_path=`; submodules; a guest-side helper; a filter.

## Acceptance criteria

1. **Unit rows, seen failing first** (`tests/unit/test_packages.py`, over a zip the row writes): the order by normalized name; Name as written; `imports` from `top_level.txt`, and `()` without one; a missing Name or Version raises `ArtifactsMissing`; a second call on the same stamp opens no zip (counted by a stand-in for `zipfile.ZipFile` in `_packages`'s namespace, set by `monkeypatch`); a member over 1 MiB and a control character each raise; a rewritten zip is read again; `str(Package)`, with and without names; `packages()` imports no `wasmtime`. READ.
2. **Build rows** (`tests/unit/test_build_scripts.py`): a wheel's `top_level.txt` from its packed names, a dropped folder absent; an unclaimed tree name, a name claimed twice and a claim of nothing each stop the build, named. Seen failing first.
3. **Command rows** (`tests/unit/test_cli.py`): the text lines, the JSON line's shape, exit 1 in both forms on `ArtifactsMissing`, exit 2 on an unknown option, and the usage naming both commands.
4. **The oracle and the coverage**, Decision 7, seen failing first on 0.1.2's set, green on the new set on both binaries. EXECUTED.
5. **The contract.** `git diff dev -- tests/public_api.txt` shows `Package`, its three fields, `packages` and nothing else; the news file's `[claim.judge]` names it; the other judge files are recorded by the judge's hash. READ.
6. **The set.** `MANIFEST` and `SHA256SUMS` carry the new zip and snapshot. Recorded from the pull request's build: the zip's members (6,262 to 6,315) and bytes; the snapshot's bytes; the wheel's bytes against 104,857,600; a plain start's fuel; the snapshot start's fuel, expected unchanged, any move explained; one guest `packages_distributions()`'s fuel. Each growth claimed. EXECUTED.
7. **The documents** of the Design regenerate (`tests/harness/cli_doc.py --check`, `tests/harness/api.py --check`), and `uv run pytest tests/lint` is green. EXECUTED.
8. **The run.** The fast tier and the pull request's `ci-status` are green and no accepted pass is lost; the landing notes cite the pre-build review and the pull request's review. READ.

The news file's CHANGELOG lines, in the shape of `../changes/README.md`:

- New: `` - **List the packages an agent can import.** `wasi_python.packages()` returns each Python package in the runtime with its version and import names, without starting a guest; `wasi-python packages` prints them, or one JSON line with `--json`. [Packages](https://claygendron.github.io/wasi-python/reference/packages/) ``
- Fixed: `` - **`importlib.metadata.packages_distributions()` answers in the guest.** Each package now carries its `top_level.txt`, so the guest maps `sklearn` to scikit-learn. [Limitations](https://claygendron.github.io/wasi-python/reference/limitations/) ``

## Landing notes

Built 2026-10-31 by an agent (Claude Opus 5.5), a builder sub-agent of the orchestrating session, on `spec/171-the-packages-a-set-carries` from `dev` at `117bcd67`. The pre-build review is `../reviews/171-the-packages-a-set-carries-spec-2026-10-31.md`; the pull request is #78, and its review is to come. Everything below is EXECUTED on an arm64 Mac (Darwin 25.5.0) unless labelled.

**The set**, built whole from the pinned sources with this branch's recipe (`scripts/build.sh`, 34 min 55 s): `python.wasm` is byte for byte dev's (`a1137950…`), so the base is dev's set; the zip (`667ae839…`) and the snapshot (`c3f8ef89…`) change, and so do `MANIFEST` (the two recipe lines and `x-snapshot-zip`) and `SHA256SUMS`. Each of the 55 `.dist-info` folders (53 at 0.1.2, and 165's two) carries its `top_level.txt`: matplotlib's `matplotlib`, `mpl_toolkits`, `pylab`; pyyaml's `yaml`; scikit-learn's `sklearn`; toolz's `tlz`, `toolz`; sympy's `isympy`, `sympy`; python-docx's `docx` and python-pptx's `pptx`, whose `--metadata` lines 165 put on `dev`.

**Criterion 6, against dev's set** (the 165 worktree's build at `dev`'s sources, read-only): the zip 54,960,042 → 54,969,118 bytes (+9,076), 6,476 → 6,531 members (+55); `python-snapshot.wasm` 104,660,252 → 104,684,438 (+24,186); `python.wasm` unchanged. A plain start (`-c pass`, the judge's driver) 277,589,139 → 279,014,133 fuel (+1,424,994, +0.51%); a snapshot start 54,177,689 → 54,209,973 (+32,284, +0.06%), not unchanged as criterion 6 expected: INFERRED, the snapshot start's exit frees zipimport's directory, now 55 entries larger. One `packages_distributions()` on the snapshot 241,418,304 → 799,553,249 fuel: it answered `{}` and now reads 55 files and answers 60 names. **The wheel**, built by hand from each set: 99,478,845 → 99,487,321 bytes (+8,476), 5,370,279 under 104,857,600. Each growth is claimed in the news file.

**Seen failing first.** The unit, build and command rows were run against `dev`'s code (an export of `117bcd67` with this branch's `tests/`): `tests/unit/test_package_list.py` fails to import `Package`, and the 23 new or changed rows of `test_cli.py`, `test_cli_doc.py` and `test_build_scripts.py` fail, among them each of the review's three rules (a name a wheel and a tree own, a distribution left with no name, `--metadata` without `=<names>`). Criterion 4: on dev's set both checks fail, the oracle on both binaries with every package nameless (the host's list equal to the guest's, both empty of names) and the coverage with every package name unclaimed; on the new set both pass, plain and snapshot, as do `test_the_snapshot_pre_imports_no_package` and `test_packages_carry_their_metadata`.

**Where the build differs from the text.**
- The unit rows are `tests/unit/test_package_list.py`: `tests/unit/test_packages.py` already holds the compiled packages' family rows.
- Name and Version are read with `PackageMetadata.get_all(...)[0]`, not `.get`: the protocol's `get` is not in Python 3.11's typing, and mypy's strict check runs at 3.11. It answers a missing key with `None` on every host Python, as `.get` would.
- Decision 3's rules hold two more cases: two trees that pack one name stop the build too, and a root member that is not a module (`w.pth`) is no name.
- `tests/harness/cli_doc.py` gains `live_parsers()` and `live_block()`, and `test_generated_pages_are_current` reads the block through `live_block()`. `docs/reference/cli.md` gains a short section, "List the packages", beside the generated block, and `docs/contributing/adding-a-package.md` a paragraph on `--metadata`'s names.
- `_Process.__init__` stays at its listed 84 lines (Decision 4), checked by `test_no_function_is_over_eighty_lines`.
- `tests/checks/test_v1_4_public_api.py`'s `TOP`, the names `from wasi_python import *` must bind, gains `Package` and `packages`: the Design did not list it, and the fast tier's first run at the head failed that row until it did.

**Sibling work.** 167 also edits step 70's `--metadata` lines. Whichever lands second rebases and writes its names in Decision 3's form; the build stops on a tree's name no `--metadata` claims, so a missed line cannot pass.

**Local runs at the head**: `ruff` check and format clean; `tests/lint` green (14 passed); the fast tier (`uv run pytest -m "not slow"`, 27 min 58 s) 4,435 passed with one failure, `test_public_modules_export_exactly_their_all`, then fixed as above and its file re-run green (11 passed); blocked locally only by the prior-art clones and the wheel, as on `dev`. The ratchet lists 231 growths, every one a check whose start reads the larger zip, claimed by the news file's `grows`.
