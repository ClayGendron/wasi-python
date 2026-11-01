# 175: The zip's directory is read by folder

- **Status:** built 2026-10-31 with 176 on `spec/175-176-the-zip-directory-and-the-end-of-a-call` (Landing notes), its pull request in review. Drafted 2026-10-31, to be reviewed before it is built (the artifact set and the build recipe: the zip's bytes, the snapshot, step 70 and the reactor; constitution §5.6). The owner chose it on 2026-10-31 (`../decisions.md`, "The zip's directory is read by folder"). Amended the same day against its pre-build review, `../reviews/175-the-zips-directory-is-read-by-folder-spec-2026-10-31.md` ("Fit to build after amendments"), every finding taken (its Disposition).
- **Date:** 2026-10-31
- **Owner:** Clay Gendron
- **Kind:** **build-class**, **a judge change** (the bounds and checks of Decision 8, each claimed with its reason); a recipe, no carried patch (§4.1). Not structural: nothing under `src/` changes.
- **Depends on:** landed: 035 (the reader), 073 (the snapshot finalizes), 012 (the rebuild check). 172 lands first (Decision 9).
- **Research it stands on:** `../research/2026-10-31-the-start-cost-of-the-zips-directory.md`. **Drafting reads** (READ): the files cited; CPython 3.15's `zipimport.py`, `pkgutil.py`; jinja2 3.1.6's `loaders.py`.

Labels: EXECUTED, run and seen; READ, read from a file, cited; INFERRED, reasoned.

## The problem

1. A plain start builds zipimport's dict for every member: about 25 k fuel each, and 2 k more to free it (EXECUTED, the memo §1).
2. A snapshot start reads nothing, but its teardown frees the dict: 19.3 M of 58.5 M at 8,191 members (EXECUTED).
3. plotly adds 1,528 members: +14.7% on a plain start, +7.0% on a snapshot start (spec 167). It waits until the cost is cut.

A **member** is one file in the zip; the **directory**, the zip's list of members; a **folder**, a top-level folder; **teardown**, `Py_FinalizeEx`.

## Decisions

### 1. The reactor keeps the stdlib zip's dict past teardown

`recipes/reactor_main.c` gains `static PyObject *stdlib_directory`. `keep_directory()` sets it, with a new reference, to `zipimport._zip_directory_cache[STDLIB_ZIP]`, dropping any earlier one; with no entry it does nothing. `init_interpreter` (`:289`) calls it last, so once per instance. Nothing drops or reads it after `Py_FinalizeEx`, in `run` (`:561`) or a session's `shutdown` after its turns (`:767`), so teardown leaves the dict alive and nothing grows across turns. The instance is then discarded. An object a program stores in the dict loses its finalizer. A dict made after `invalidate_caches()` is freed as today.

### 2. Step 70 writes a folder table into the zip's comment

`scripts/make_stdlib_zip.py` writes the members sorted (`:464-469`), so each folder is one contiguous run of the directory. A new `write_folder_table(path)` reads the zip's directory and writes the **folder table** as the archive comment, replacing any there; nothing else changes. zipimport and `zipfile` ignore comments.

Version 1, ASCII, every line ended by one LF:

```
wasi-python folders 1
<folder> <offset> <size> <count> <init-offset> <init-count>
```

- One line per folder, in directory order; offsets in bytes from the directory's first entry.
- The init pair covers the folder's `<folder>/__init__.*` entries, contiguous when sorted; `0 0` when none.
- Integers decimal, no sign, no leading zero.
- Every folder is listed, the stdlib's included (the owner's answer), but `*.dist-info` folders and names outside `[A-Za-z0-9_.-]`, which are read at start.

Equal zip bytes from every host give an equal table; spec 012's rebuild check holds it. It is about 3 KB: 92 folders, 2,942 bytes on spec/167-plotly's zip (EXECUTED, the memo's `segment_zip_all.py`). The writer checks its table: the runs tile the directory in order, each run's entries name its folder, the counts add up. A failure, or a comment over 65,535 bytes, stops the build. A version 1 reader reads any other version as no table.

### 3. A plain start reads a folder's members on first use

`read_directory` (`recipes/zip_directory.py:114`) reads the stdlib zip by its table: the directory once, as `_fast` does (`:39-111`), parsing every entry outside the runs, and for each folder only `<folder>/` and its init entries. So zipimport finds a package, a namespace package or neither as before. The rest is pending, kept with the dict it belongs to. The dict is plain, so lookups stay in C. `served` (`:30`) records `"folders"`.

A pending folder loads, one seek and one read, on the first of:

- a `zipimporter` made with a prefix in it, as every submodule import makes (`Lib/zipimport.py:62-96`);
- the import of the folder's package (`zipimporter.exec_module` of a package): the folder loads before the package's own code runs, so that import pays the folder's members once (`import tzdata` alone about 17 M); only a top-level package triggers it, since a submodule's folder is already loaded, and a namespace package runs no loader, so it loads on its first submodule;
- `zipimporter.get_data` on a path in it (`:135`): `pkgutil.get_data`, plotly's patch;
- any name a `ZipDirectoryPath` looks up in it (`recipes/zip_resources.py:93-202`): `importlib.resources`.

`install()` (`:157`) sets the first three. Every trigger takes the dict through the importer's own `_get_files()`, never from `_zip_directory_cache`. So a trigger after `invalidate_caches()` re-reads first, and the re-read loads again every folder loaded before. A load deletes and re-adds the init entries, so each folder's children keep the full read's order; only the top level's order differs.

Until its folder loads, the top-level importer's `_get_files()`, and `_zip_directory_cache` (`pkgutil.py:180`), show a package as `<folder>/` and its init entries. So jinja2's `PackageLoader.list_templates()`, which reads `_get_files()`, lists no templates for a package never imported. `docs/reference/limitations.md` says so.

Seams: `load_all(archive)` loads every folder; `loaded(archive)` returns the loaded folders.

### 4. Only the stdlib zip, and only on the plain start

`install(by_folder, archive=None)` records the archive read by its table: `sys._stdlib_dir` when `None`, which the reactor sets just before (`reactor_main.c:342`). Any other archive, an `import_path=` zip included, gets today's full read, table or not.

`init_interpreter` passes `!fixed_hash_seed`, so `wizer.initialize` (`:400`) reads the full directory: the snapshot's dict, its calls and `make_snapshot` images are today's. A lazy snapshot would charge `import pandas` about 14 M (the memo, §2c).

### 5. A bad table falls back to the full read

At run time nothing is refused: a table absent, of another version, unparsable or not fitting gives the full read, `served` `"fast"`. It does not fit when a run is out of order, overlaps or passes the end; when the walk between runs misses a run's offset; when a run's first entry, or an entry read at start, names another folder; or when the counts do not add up. A load that finds a wrong count, end or name, or raises `OSError`, replaces the dict's contents in place with the full read and drops the table; if that read fails too, zipimport's own error propagates. A wrong table never yields a wrong dict.

The build refuses (Decision 2), and the judge checks the set's zip is served `"folders"`.

### 6. The resource reader's children map follows the dict

`_children` (`recipes/zip_resources.py:80-90`) keeps its map while the dict is the same object. A load grows that object, so the map is keyed by the dict's length too.

### 7. The bytes

The zip grows by its comment, both binaries by the reader's bytecode, a few KB (INFERRED). `MANIFEST` and `SHA256SUMS` change.

### 8. The judge

These change, each claimed under `[claim.judge]` with its reason (READ, a sweep of `tests/checks/` for fuel bounds and served values):

- `test_a_plain_start_grows_at_most_30k_fuel_per_member` (`test_v1_3_the_zips_directory.py:70-76`) and the re-read (`:155-175`): 30,000 to 2,000 per member, renamed; the re-read expects `"folders"`. The memo's 119 fuel per added plotly member is the reason (`outputs/c4-*`).
- The gate (`:54-67`): `"folders"` on the plain binary, `"fast"` on the snapshot.
- The zone check (`:190-209`): its baseline becomes `import zoneinfo, importlib.resources, tzdata.zoneinfo` on both binaries, so Paris less baseline still measures the resource read, not tzdata's 627-member load; its bounds stay.
- `test_the_fast_reader_builds_zipimports_dict` (`:126-152`): a dict comparison after `load_all`, each folder's children in stock order; the snapshot case keeps its list equality.
- `START_FACTOR` (`test_v1_3_data_stack.py:180`): 3 to 2. A plain start of about 113 M is under three snapshot starts of 38.9 M; its docstring asks for this restatement. The ratio falls because the plain start gets cheaper (about 5.2 today, 282.2 M against 54.6 M; about 2.9 after), and the guard tightens in absolute terms: the snapshot start's room before the check goes red shrinks from about 39 M to about 17.6 M. The comment at `test_v1_3_data_stack.py:177-179`, which says "about 3.8 times", is restated with both measured starts and the measured ratio.
- `tests/harness/zips.py`: `small.zip` and `padded.zip` get `write_folder_table`, so the pads are three tabled folders; its cache folder moves to `-v3`.

Unmoved (INFERRED): the pandas tz job's 60 M is the snapshot's; the metadata miss's 6,000 per member falls; `ROOT_START_BOUND` counts provider calls, and the zip is its own preopen; upstream and recorded fuels fall, since a program loads only the folders it uses. Any other check the run turns red joins this list with its reason.

### 9. The neighbours

- **plotly** (167's last part) lands after: the table follows its members, its patch reads through `get_data`, and it claims about 1 M on a plain start, not 41.5 M, and none on the snapshot (INFERRED, the memo §4).
- **171**: host `zipfile` ignores the comment; `top_level.txt` is in a `.dist-info`; `find_spec` needs only init entries.
- **172** lands first: tqdm's two tests flip with the set's allocations, which 175 moves.
- **173**, **174** add folders the table lists unasked; 174's `cairosvg/__init__.py` is in the init run; the later to edit `make_stdlib_zip.py` rebases.

## Intent

A plain start parses only the members it uses, and no start frees the directory, so the zip's size stops costing every call.

## Design

- **Recipe:** `recipes/reactor_main.c` (Decisions 1, 4); `recipes/zip_directory.py` (3 to 5, its docstring); `recipes/zip_resources.py` (3, 6); `scripts/make_stdlib_zip.py` (2, its docstring); `scripts/steps/70_zip.sh` (its comment).
- **Judge:** Decision 8's files; `tests/unit/test_zip_directory.py`; `tests/unit/test_build_scripts.py`.
- **Documents:** `docs/explanation/how-it-works.md:70`; `docs/reference/limitations.md` (Decision 3).

## Scope

In: Decisions 1 to 9. Out: a lazy snapshot; the table after `invalidate_caches()` on the snapshot; ending a call without teardown, researched apart (`../decisions.md`).

## Acceptance criteria

1. **The writer, unit rows seen failing first** (`test_build_scripts.py`): a made zip's table, line for line; the same bytes twice; only the end record and comment changed; an existing comment replaced; a split folder, an oversized comment and a name outside the alphabet as Decision 2 says. READ.
2. **The reader, unit rows seen failing first** (`test_zip_directory.py`, the recipe on the host, the archive passed to `install`, the reader called directly where `install()` returns early on Windows): each malformation of Decision 5, and an `OSError` at load, gives the full read's dict; another archive's table is ignored; after `load_all`, the dict equals `_fast`'s, each folder's children in order; a trigger after invalidation; the children map after a second load. READ.
3. **Every reader, in the guest, plain unless noted, each a check:**
   - the set's zip served `"folders"`;
   - after `import pandas`, `loaded` holds exactly the imported packages' folders (`pandas`, `numpy`, `dateutil` in the memo); `pandas.io.formats.style` imports;
   - `pkgutil.get_data("tzdata", "zoneinfo/Europe/Paris")` and `importlib.resources.files("tzdata")`'s `iterdir`, `joinpath` and `read_bytes`, each as the first touch;
   - `import tzdata`, `invalidate_caches()`, then `pkgutil.get_data("tzdata", "zoneinfo/UTC")`, and again with `files("tzdata").joinpath("zoneinfo/UTC").read_bytes()`;
   - `importlib.metadata`'s answers and `zip_children`'s names, in order, equal the full read's; 171's oracle green;
   - `mpl_toolkits.mplot3d`; `invalidate_caches()` between two submodule imports;
   - `zipimporter(ZIP + "/pandas/")`'s API, and its errors on a missing name in a pending folder;
   - `pkgutil.iter_modules()` and under `pandas.__path__`: the full read's names;
   - pandas' Styler templates through jinja2's `PackageLoader`, `list_templates()` included;
   - an `import_path=` zip, with and without a table, served `"fast"`;
   - on the snapshot, the cached dict equals the stock read as a list. EXECUTED.
4. **Fuel, as counts** (§4.9), each seen failing first on today's set:
   - a plain start, `import pandas` and a first `get_data` each grow at most 2,000 fuel per padding member (27.1 k today for the start);
   - on each binary, popping the stdlib dict from `_zip_directory_cache` then `os._exit(0)` costs within 1 M of `os._exit(0)` alone, after `load_all` on the plain binary (17.6 M more on the snapshot today). EXECUTED.
5. **The numbers, against a line.** On the pull request's set, before and after: a plain start at most half of before (projected 282.2 M to about 113 M, INFERRED); a snapshot start lower by at least 10 M (projected 54.6 M to 38.9 M); the snapshot's `import pandas` less its `-c pass` within 1 M; the bytes of Decision 7. The CHANGELOG line states the measured plain start. A projection missed by over 10% is explained in the landing notes. EXECUTED.
6. **The run.** The fast tier, the lint and `ci-status` green, no accepted pass lost, Decision 8 claimed; the landing notes cite both reviews. READ.

The news file's CHANGELOG line, its number measured:

- Changed: `` - **A plain start reads only the packages it uses.** An empty program starts in <measured> of the fuel, and an added package costs a start almost nothing. [How it works](https://claygendron.github.io/wasi-python/explanation/how-it-works/) ``

## Landing notes

Built 2026-10-31 by an agent (Claude Opus 5.5), a builder sub-agent of the orchestrating session, together with 176 on `spec/175-176-the-zip-directory-and-the-end-of-a-call` from `dev` at `2ec3c1ee`, then rebased onto `a0b1171d` (166's second pull request and 173). Its pre-build review is `../reviews/175-the-zips-directory-is-read-by-folder-spec-2026-10-31.md`; the pull request's review is to come. 172 had not landed (Decision 9's order): if tqdm-smoke's two tests flip with this set's allocations, 172's class holds them. Everything below is EXECUTED on an arm64 Mac (Darwin 25.5.0), fuel through the judge's driver, unless labelled.

**The measure, step by step.** `dev`'s set at `2ec3c1ee` was built whole from the pins in this worktree; then this specification alone (steps 60 to 90); then both specifications (steps 60, 80, 90). Each figure is `-c pass` or the program named, its fuel and the linear memory once `run` returned:

| | dev | 175 | 175 and 176 |
|---|---|---|---|
| plain start | 283,901,206 | 135,278,097 | 132,134,646 |
| snapshot start | 54,696,220 | 41,551,326 | 35,186,249 |
| snapshot `import pandas` less its start | 4,645,781,041 | 4,647,714,277 | 4,616,670,412 |
| the same, both ended by `os._exit(0)` | 4,380,689,386 | 4,380,621,541 | 4,389,481,909 |
| plain `import pandas`, memory | 66,322,432 | 64,356,352 | 64,356,352 |

**Criterion 5.** A plain start at most half of before: 135.3 M against 284.0 M (47.6%). A snapshot start lower by at least 10 M: 13.1 M lower. The snapshot's `import pandas` less its `-c pass` within 1 M: the import itself, both calls ended by `os._exit(0)`, moved by 67,845 fuel; with teardown in both it moved by +1.93 M on this specification alone, since teardown after pandas saves 11.1 M of the kept dict and a bare call 13.1 M, and by −29.1 M with 176. The projections missed: a plain start of 135.3 M against about 113 M (+20%), and a snapshot start of 41.6 M against 38.9 M (+7%). At a real start the folder read costs 23.6 M (`_by_table` in the guest, against 175.8 M for the whole read), where the memo priced 17.8 to 18.9 M inside a call; a start also loads `encodings`, the one folder the start imports (123 members), and the plain teardown still costs 23.3 M (39.1 M before). **Bytes:** the zip 57,068,536 → 57,071,318 (+2,782: the table, 90 folders); `python.wasm` 99,497,353 → 99,511,775 (+14,422, the reader's bytecode); `python-snapshot.wasm` 104,890,482 → 104,800,506 (−89,976).

**Criterion 4.** On the judge's zips: a start 9 fuel a padding member, `import pandas` 55, a first `get_data` 7 (27.1 k before); the re-read 30; a first zone 3. The pop of the stdlib dict before `os._exit(0)` costs within 1 M on both binaries, every folder loaded on the plain one; on dev's set it fails on both.

**Seen failing first**, on dev's set with this branch's tests: the gate (plain), the three rows of 2,000 a member, the re-read, the fast reader's small and padded cases, every new reader row but three, `test_import_pandas_loads_exactly_its_packages`, and the pop row on both binaries. The three that pass on dev's set guard what the whole read already does: the two reads after `invalidate_caches()`, the namespace and invalidation row, and the `import_path=` zips read whole. The unit rows (`test_build_scripts.py`, 3; `test_zip_directory.py`, 18) fail on dev's recipe: no `write_folder_table`, no table read.

**Where the build differs from the text.**
- `START_FACTOR` stays 3. Decision 8 moved it to 2 on a projected plain start of about 113 M; measured, the ratio is 3.26 with this specification alone and 3.75 with 176, so 3 holds and is the stricter guard. The comment at `test_v1_3_data_stack.py:177` ("about 3.8 times") is still true.
- `install` takes `by_folder` as its first argument; the module's own record of the archive read by folder is `tabled`. `touch(importer, at)` is the trigger the four share; `_zip_resources.touch` is set to it when `_zip_directory` loads that module.
- `import pandas` loads the folders `numpy`, `dateutil` and `pandas`, as the memo found; the row compares the folders outside `sys.stdlib_module_names`.
- Criterion 3's rows compare each reader's answers by folder with its answers after the cache is replaced by zipimport's whole read and every importer made again, in the same program.
- **Review round 1** (`../reviews/175-the-zips-directory-is-read-by-folder-pr-2026-11-01.md`). Medium 1: `_load` popped a folder from the pending list before reading it, so a load that raised anything but `OSError` (an audit hook's refusal, a `MemoryError`) lost the folder for the rest of the call. It now pops only after the merge; a unit row (a stub `open_code` that raises once) and a guest row (an audit hook that refuses the load's open once, then `import tomllib` again) failed first on the old reader and pass. Low 3: a load now checks that each `__init__` entry the start read is in the folder's run, equal, and falls back otherwise; a unit row with a forged central header in an extra field failed first. Low 6: the news files give the rebased sizes. The round's set: `python.wasm` `295a67d2…` 100,660,530 bytes, `python-snapshot.wasm` `f60c3928…` 105,948,284, the zip unchanged (`207b382c…`).
- `test_the_fast_reader_builds_zipimports_dict` compares the dicts' sorted items and each folder's children in order; only the top level's order differs.

**Rebased onto `a0b1171d`** (166's pandas 3.1.0 and zlib 1.3.2, 173's drawsvg). The set was built whole from the pins with this branch (13 min 9 s), then steps 60 to 90 again for 176's fix of the function table's order: `python.wasm` `e704620c…` 100,659,378 bytes, `python-snapshot.wasm` `eb09aba2…` 105,955,016, the zip `207b382c…` 57,495,423. `dev`'s set at `a0b1171d`, built over the same tree from `dev`'s recipe (steps 60 to 90): `9800419…` 100,638,734, `f11e1285…` 106,045,881, `98ed43c0…` 57,492,608. Against it: the zip +2,815 bytes, `python.wasm` +20,644, the snapshot −90,865; a plain start 284,437,056 → 132,420,433 fuel and a snapshot start 54,840,044 → 35,202,086, both specifications together. **The wheel**, built by hand from the set: 102,612,346 bytes, 2,245,254 under 104,857,600. On this set `test_v1_3_the_zips_directory.py` (36), `test_v1_4_the_end_of_a_call.py` (142) and `test_v1_3_data_stack.py` pass, and the fast tier (4,685 checks) passed but for the callback scan, which the order fix answers (176's landing notes).
