# Review of 035 — The zip's directory is read once (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the
  constitution (§4.1, §4.4, §4.6, §4.9 to §4.11, §4.15, §5.2, §5.4, §5.6, §5.7), the
  specification, the memo `../research/2026-10-17-the-zips-directory-is-read-once.md` and its
  evidence (`scripts/candidates.py`, `guest_candidates.py`, `make_zips.py`, `outputs/`),
  decision 44 (`decisions.md`, "43–48"), questions 59 and 60, spec 033 (in pre-build review)
  and spec 023's Decision 6 and mpl-data design. I read the recipe and build code:
  `recipes/reactor_main.c`, `recipes/reactor_bootstrap.py`, `scripts/freeze_bootstrap.py`,
  `scripts/steps/60_link.sh` and `common.sh`. I read the CPython 3.15.0 tree the build uses
  (`build/Python-3.15.0/`): `Lib/zipimport.py` (`__init__`, `get_data`,
  `get_resource_reader`, `_get_files`, `_read_directory`, `_get_data`),
  `Lib/importlib/_bootstrap.py` (`_install`, `_install_external_importers`,
  `_find_and_load_unlocked`, `FrozenImporter._resolve_filename`, `_fix_up_module`),
  `Lib/importlib/_bootstrap_external.py` (`_path_join`, `_install`, `PathFinder.find_distributions`),
  `Lib/importlib/resources/` (`readers.py`, `abc.py`, `_common.py`, `_adapters.py`),
  `Lib/importlib/metadata/__init__.py` (`FastPath`, `Lookup`, `PathDistribution`),
  `Lib/zipfile/__init__.py` and `_path/`, `Lib/zoneinfo/_common.py` and `_tzpath.py`,
  `Python/pylifecycle.c` (`init_interp_main`, `pyinit_main`, `Py_InitializeFromConfig`,
  `_Py_InitializeMain`, `interpreter_update_config`), `Python/sysmodule.c`
  (`PySys_AddAuditHook`, `sys_audit_tstate`, `_PySys_UpdateConfig`), `Python/pystate.c`
  (`_PyRuntimeState_Init`), `Python/import.c` (`look_up_frozen`, `init_zipimport`,
  `_PyImport_InitExternal`), `Python/frozen.c`, `Include/cpython/import.h`,
  `Doc/c-api/init_config.rst`, `Doc/whatsnew/3.14.rst` and `3.15.rst`. I read the judge:
  `tests/harness/guest.py`, `tests/harness/scoreboard.py` (`FUEL_TOLERANCE`),
  `tests/checks/conftest.py` (the `guest` fixture), `tests/harness/jobs.py`, and the checks
  that touch resources (`test_v1_2_hostile_guest.py:140-160`) or modules. Each claim is
  labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/035-the-zips-directory-is-read-once.md` as drafted
  (committed in `fe2ce10`).
- **Ran (EXECUTED, darwin-arm64).** Nothing in `src/`, `tests/`, `scripts/`, `recipes/` or the
  spec was edited; `scripts/build.sh` and the judge were not run. Guest runs used a copy of
  `build/artifacts/` (the memo's set: `python.wasm` `4befe9de…`, `python-snapshot.wasm`
  `c7302cfd…`, `python-stdlib.zip` `1add57e4…`, checked against its `SHA256SUMS`) on the judge's
  own driver (`tests/harness/guest.run`, fuel exact). Host runs used the build's host CPython
  3.15.0 (`build/tools/python`, the same source as the guest) through
  `uv run --no-project --python build/tools/python/bin/python3.15`, and small embedding programs
  compiled with clang against its `libpython3.15.dylib`. Everything is under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/035-review/proto/`:
  - `zip_directory.py`: the reader written from Decision 2's text alone (fast path, every
    listed fallback, `served`, `install()`), about 90 lines. `freeze.py` marshals it (4,353
    bytes).
  - `embed.c` → `two_phase.txt`: Decision 3 (install point A) on host 3.15.0: isolated config,
    the zip as the only path and as `stdlib_dir`, `_init_main = 0`, `PyImport_FrozenModules`,
    the import and `install()` between the phases, then `_Py_InitializeMain()`. Also a
    one-phase start, a variant that sets `sys._stdlib_dir` in phase 1 (`embed_fix.c`), and the
    failure path.
  - `hook.c` → `audit_hook.txt`: Decision 4 (install point B, the C audit hook) on host 3.15.0.
  - `odd.py` → `odd.txt`: the reader against zipimport's `_read_directory` on 13 zips, ordinary
    and hostile.
  - `trav.py` → `trav.txt`: `zipfile.Path` against the memo's `IndexPath` on trailing slashes
    and odd names.
  - `measure.py` → `measure.txt`: in the guest, the spec's reader, the memo's prototype and
    zipimport's reader on the artifact zip (1,751 members) and a padded zip (7,004), made as
    Decision 11 makes `padded.zip` (`pad.py`, append mode, level 1).
  - `children.py` → `children.txt`: in the guest, the cost of building the children map
    against the memo's top-level split.
  - (One stray `python3 -` with empty input ran nothing; every run above went through `uv`.)

## What holds

- **The directory reader is precise enough to build, and it is safe on hostile zips.**
  EXECUTED (`odd.txt`): the reader written from Decision 2's words alone gives a list of items
  equal to zipimport's on all 13 zips. These are a plain zip, explicit directory entries,
  prepended bytes with a comment, odd names (`//lead.py`, `a//b.py`, a duplicate, an empty
  name, `../up.py`), a cp437 name, a Zip64 zip, a truncated directory, an understated and an
  overstated entry count, a bad UTF-8 name with the flag set, an empty file and a non-zip.
  Each error is upstream's own type and message, because it is raised by
  `stock_read_directory`. `served` says `"stock"` exactly where Decision 2 says it should,
  plus once for a stored member whose bytes hold `PK\x06\x06` in the tail. That case is
  correct (stock gives the same dict) and costs one probe. The fast path is pure Python. Its
  one larger read is bounded by the file's size (`cd_size ≤ header_position`, READ). Any
  exception, `MemoryError` included, goes to the stock reader. Imports from a user zip are
  parsed exactly as today.
- **Both install points work on CPython 3.15.0.** EXECUTED on the build's host 3.15.0, the
  same source (`two_phase.txt`, `audit_hook.txt`):
  - Point A: between the phases `Py_IsInitialized()` is 0 and `zipimport` is not yet loaded.
    `import _zip_directory` through `PyImport_FrozenModules` works. `install()` works. After
    `_Py_InitializeMain()`, `zipimport._read_directory is _zip_directory.read_directory`,
    `served == {zip: "fast"}`, `encodings` was loaded by a `zipimporter`, the cached dict
    equals the stock reader's (646 names), and `sys.path_hooks` and `sys.meta_path` are as
    usual. A failing import in phase 1 still prints its traceback through `PyErr_Print()`
    (to C stderr) before `abort()`.
  - Point B: a hook added before `Py_InitializeFromConfig` survives runtime init (READ:
    `_PyRuntimeState_Init` keeps `audit_hooks.head`). It installs at `import encodings`, the
    first import after zipimport finishes, before any `zipimporter` exists. `served` says
    `"fast"`.
  - So the "INFERRED, nothing above was run" of Decision 3 can say: executed on host 3.15.0
    by this review; check 1 is still the gate on wasm. Two notes are findings 4 and 5.
- **The frozen table cannot shadow zipimport.** READ: `look_up_frozen` searches the bootstrap
  table first, then `PyImport_FrozenModules`, then the frozen stdlib (`Python/import.c:3126-3171`).
  EXECUTED: `_zip_directory.__spec__.origin == "frozen"`.
- **The reader's cost is as claimed.** EXECUTED (`measure.txt`, judge's driver): the spec's
  reader costs 24,798 fuel per member, the memo's prototype 20,690 and zipimport's 77,146. The
  spec's list equals zipimport's on both zips (1,917 and 7,671 names), and `served` says
  `"fast"`. The fallback tests add about 4,100 per member to the prototype. Check 2 stays
  inside its bound (finding 7).
- **The metadata seam is the right one.** READ: `Distribution.discover` reaches each finder's
  `find_distributions` only when a program asks for metadata. A wrapper there costs nothing
  per import. Rejecting the memo's `exec_module` wrapper is right.
- **The reasoning on the snapshot holds.** READ: phase 1 runs the same code on every host, with
  the clocks, entropy and stats pinned. The new headers are made by the same
  `freeze_bootstrap.py` under `PYTHONHASHSEED=0`, after `host_from_source`, as `_reactor`'s is
  today. Nothing in phase 1 reads a host-dependent value (INFERRED). Acceptance 9's rebuild jobs
  are the right proof.
- **A recipe, not a patch (question 60).** READ: no upstream file changes, the zip's bytes do not
  change, and spec 020's tarball check is unaffected. Run-time replacement under a judge that
  compares with upstream fits §4.1's "a stand-in module".

## Acceptance criteria against evidence

1. Check 1, the gate: sound, and now known to pass on host 3.15.0. It misses the `__file__`
   regression of finding 4; add it.
2. Check 2: sound. The expected slope is about 26,700 against a bound of 30,000 (finding 7).
3. Check 3: sound. The odd zips route as stated (`odd.txt`). The Zip64 zip needs zipfile's
   limits lowered on the host (`ZIP64_LIMIT`, `ZIP_FILECOUNT_LIMIT`), as `odd.py` does, since
   zipfile writes no Zip64 record for a small zip.
4. Check 4: sound. A zone load does not list a directory, so the children map is not built.
5. Check 5: right in kind, but it does not test the cases where a builder is most likely to
   diverge: trailing slashes, a file named with a trailing slash, and the `open` modes
   (finding 3).
6. Check 6: **cannot pass as Decision 7 is written** (finding 1). The `files` comparison
   should compare `(str(p), p.hash, p.size)`: `PackagePath` equality is path-only (READ).
7. Check 7: sound; the golden's `reset_tzpath(to=[])` makes native and guest use `tzdata` alike.
8. Check 8: sound.
9. Sound. Its fixture needs one change (finding 6).

"Seen failing first" is credible for each check: `_zip_directory` is missing today, and every
bound is far below today's measured cost.

## Findings, most severe first

1. **Decision 7's `zip_children`, as written, fails check 6.** High: the spec cannot go green
   without changing the design or the bound, and rule 4 forbids changing the bound.
   - Decision 7 says our `zip_children` "returns the top-level names from the children map".
     Decision 6 builds that map in one pass over every name, on first listing.
   - EXECUTED (`children.txt`, guest, judge's driver): building the children map over
     zipimport's dict costs **10,944 fuel per member** (20.6 M at 1,751 members). The memo's
     prototype, `dict.fromkeys(n.split('/', 1)[0] for n in files)`, costs **4,608 per
     member** (8.6 M).
   - Check 6 bounds the snapshot miss at 20 M and the plain slope at 6,000 per member. The
     children map alone takes 20.6 M and 10,944 per member. So the miss would fail both.
   - READ: the memo's 9.7 M and 4,472 per member were measured with the split, not the map.
   - Fix: in Decision 7, the top-level names are upstream's own expression over zipimport's
     keys: `dict.fromkeys(name.split("/", 1)[0] for name in loader._get_files())`. The order is
     upstream's: members first, then implied directories, which add no new first part. The
     children map is built only by `iterdir()`. Say in Decision 10 that the 4,472 figure is
     the split's.

2. **Resource reads from a guest's own zip become less strict, and no longer stream.** High
   for a runtime meant for untrusted agent code. Low for the stdlib zip.
   - The new `get_resource_reader` serves every `zipimporter`, so it also serves a zip a guest
     puts on `sys.path`, from a grant or from its root. READ: today those reads go through
     `zipfile`, which does these things:
     - it checks each member's CRC-32 (`Lib/zipfile/__init__.py:1132`);
     - it checks that the name in the directory matches the local header (`:1795`);
     - it rejects overlapped entries, the quoted-overlap zip bomb (`:1803-1808`);
     - it refuses encrypted members (`:1819`);
     - it reads bzip2 and LZMA members;
     - it streams: `open("rb")` gives a `ZipExtFile` that decompresses as it is read.
   - The spec's path reads through `zipimporter.get_data`, that is `_get_data`
     (`Lib/zipimport.py:632-679`, READ). It does none of the above:
     - it takes stored, deflate and zstd only (anything else raises `ZipImportError`);
     - it checks no CRC, no name and no overlap;
     - it decompresses the whole member into memory before `open` returns a `BytesIO`.
   - INFERRED from that code: a guest zip with an LZMA member that reads today raises
     `ZipImportError` after this change. A corrupt member gives wrong bytes, not `BadZipFile`.
     A 200 MB member read in chunks needs 200 MB of guest memory at once. Under the
     runner's memory cap that is a `MemoryError` or a trap, where it streams today.
   - The claim "the same bytes and listings" (Decision 6, question 59) holds for the stdlib
     zip. EXECUTED: all 1,751 of its members are deflate with no flag bits, and the largest is
     620,623 bytes (`pydoc_data/topics.pyc`). The largest `tzdata` file is 104,917 bytes. The
     claim does not hold for a guest's zip.
   - Fix (pick one and write it into Decision 6):
     - (a) The fast byte path serves a member only when its toc entry has `compress` 0 or 8
       and `file_size` ≤ 1 MiB. The bytes then pass `zlib.crc32(data) == crc`; zlib is
       already loaded by zipimport. Any other member, any CRC miss, and any exception from
       `get_data` open through `zipfile.Path(archive, at).open(mode, …)`. That is upstream's
       object, with upstream's streaming, checks and errors, for that one read. It costs the
       parse only in the rare case. This keeps Decision 2's rule: anything odd is upstream's.
     - (b) Serve only the runtime's own zip (`sys.path[0]` as the reactor sets it). Every
       other archive keeps `importlib.readers.ZipReader`.
   - Add a check on a guest zip on `sys.path` with an LZMA member, a member with a corrupted
     CRC, and a member over the threshold read in chunks. Each answers as `zipfile.Path`
     does. Amend question 59's wording to say "for the runtime's zip, and for any other zip
     through upstream's reader where they differ". The metadata path reads `METADATA` the
     same way, so the fix covers it too.

3. **The `Traversable`'s predicates are underspecified, and the memo's prototype, which a
   builder will reach for, answers differently from `zipfile.Path`.** Medium.
   - EXECUTED (`trav.txt`, host 3.15.0): `zipfile.Path.is_dir()` is purely syntactic. It is
     `not at or at.endswith("/")`, so `joinpath("missing/")` and `joinpath("m.py/")` are
     directories that do not exist. `is_file()` is `exists() and not is_dir()`. The memo's
     `IndexPath` answers `False` for both, drops the trailing `/`, and joins `//lead.py` as
     `lead.py`. That last one is a different member. On a zip with an empty member name,
     `joinpath("/")` gives `is_file() == True`.
   - READ: `zipfile.Path.joinpath` is `resolve_dir(posixpath.join(at, *other))`. It adds
     `/` only when the plain name is absent and `name + "/"` is present, so a file `a` wins
     over a directory `a/`. Decision 6's "plus a trailing `/` when that names a directory"
     does not say which wins.
   - EXECUTED: `zipfile.Path.open` accepts `"rt"` and `"r+"` as text, raises `ValueError` for
     `"w"` (`write() requires mode …`) and for `"br"`/`"x"`, and checks for a directory
     first, so `open("w")` on a directory is `IsADirectoryError`. Decision 6's "any other
     mode raises `ValueError`" would refuse `"rt"`, which real code passes.
   - Not avoidable cheaply, and so to be named as accepted differences:
     - zipimport's implied directories differ from zipfile's for names with `//` or a leading
       `/`. `a//b.py` implies `a//` in zipimport and `a/` in zipfile (READ: both loops;
       `trav.txt`).
     - `zipfile.Path.iterdir()` repeats a duplicated name and yields the empty-named member
       under the archive's file name. The dict does neither.
     - Two `files()` calls give unequal `zipfile.Path` objects (EXECUTED: `False`), because
       each holds its own `ZipFile`. Ours compare equal on `(archive, at)`.
   - Fix: write the exact definitions into Decision 6:
     - `is_dir = not at or at.endswith("/")`;
     - `exists = at in files`;
     - `is_file = exists and not is_dir`;
     - `joinpath` is `resolve_dir(posixpath.join(at, *map(os.fspath, parts)))` with
       zipfile's rule;
     - `open`: directory check first; then `mode[0] == "r"` reads, `"b" in mode` is binary,
       anything else raises `ValueError`;
     - the root's `name` is the archive's file name.
     Add `"UTC/"`, `"missing/"`, `"rt"`, `"r+"` and `"w"` rows to check 5 and to
     `test_the_zip_path_answers_as_a_traversable`. List the three accepted differences in the
     README sentence that already lists `root`, `at` and `glob`.

4. **The two-phase start loses `zipimport.__file__`, which Decision 9 says is unchanged.**
   Medium; the fix is one call.
   - EXECUTED (`two_phase.txt`): after a two-phase start, `zipimport` and
     `_frozen_importlib_external` have no `__file__`, and their `loader_state.filename` is
     `None`. A one-phase start gives `…/python315.zip/zipimport.py` and
     `…/importlib/_bootstrap_external.py`.
   - READ: `FrozenImporter._resolve_filename` returns `None` while `sys._stdlib_dir` is unset.
     `sys._stdlib_dir` is set only by `_PySys_UpdateConfig`, called from
     `interpreter_update_config` in the main phase (`Python/sysmodule.c:4208`,
     `Python/pylifecycle.c:1378`). Phase 1 imports both modules first, so they keep no file
     name. (`importlib/__init__.py` later repairs `importlib._bootstrap_external.__file__`,
     not zipimport's.)
   - EXECUTED (`two_phase.txt`, third run): setting `sys._stdlib_dir` to the zip's path
     (`PySys_SetObject`) in phase 1, before the import, restores both attributes and both
     `loader_state`s exactly. The main phase then sets the same value again.
   - Fix: add that call to Decision 3. Check 1 asserts
     `zipimport.__file__ == "/usr/local/lib/python315.zip/zipimport.py"`.
     `_zip_directory.__file__` then reads `…/python315.zip/_zip_directory.py`, as any frozen
     stdlib module's does.

5. **The private API's history is worse than "provisional".** Medium-low.
   - READ: `_Py_InitializeMain()` was removed in 3.14 (`Doc/whatsnew/3.14.rst:3071`,
     gh-129033). It was restored in 3.15 (`Doc/whatsnew/3.15.rst:2630`, gh-142417). The C-API
     docs say "The 'Core' phase is not properly defined … the API can be modified or even be
     removed anytime" (`Doc/c-api/init_config.rst`).
   - A re-pin to a CPython without it fails at link, not at check 1. That is loud, but the
     builder of a re-pin then meets Decision 4 with no instruction to skip the two strikes.
   - Fix: say this history in Decision 3. Add: "if a re-pinned CPython lacks
     `_Py_InitializeMain` or `PyConfig._init_main`, the re-pin uses install point B at once,
     and its memo records it." Note in Decision 4 what B costs and keeps:
     - EXECUTED (`audit_hook.txt`): 654 audited events for importing `json`, `zoneinfo`,
       `importlib.resources` and `email.parser` on host. Each builds an argument tuple once a
       hook exists (`sys_audit_tstate`, READ).
     - The hook must return 0 with no exception set; `sys_audit_tstate` restores the caller's
       exception only on success (READ).

6. **The judge plumbing the checks need is not in the Design table.** Low-medium: a builder
   finds it at once, but it is a judge change the review should see.
   - READ: the `guest` fixture passes `stdlib=d / "python-stdlib.zip"` and then `**kw`
     (`tests/checks/conftest.py:76-90`). So `guest("plain", …, stdlib=small_zip)` is a
     `TypeError`. Checks 2, 3, 4, 6 and 8 run on `small.zip` and `padded.zip`. Fix: add a
     `stdlib=` override to the fixture, defaulting to the artifact zip, and list
     `tests/checks/conftest.py` in the Design table.
   - EXECUTED: `uv run python -V` is 3.14.2, and `freeze_bootstrap.py` refuses any host but
     3.15 (`TARGET`). So `test_freeze_names_each_module` cannot marshal 3.15 code, and "the
     default call renders today's `reactor_bootstrap.h` byte for byte" has no 3.15 bytes to
     render on the judge's host.
   - Fix: test `render(data, magic, name, source)` on fixed bytes against a written-out
     header text. Test `co_filename` through a small `compile_module(src, filename)` helper
     that the version gate does not cover, run on the host's own Python.
   - Also: `test_odd_zips_go_to_the_stock_reader` patches `stock_read_directory` on the
     module, so `read_directory` must look it up as a module global at each call, not bind
     it as a default argument. Say so.

7. **Bounds: sound, with stated margins. Two numbers should be the measured ones.** Low.
   - Check 2: EXECUTED, the spec's reader is 24,798 per member. The rest of a plain start
     adds about 1,931 per member that is not the reader (79,077 for the whole start against
     77,146 for one read, `measure.txt`). So expect about 26,700 against the 30,000 bound:
     about 11% headroom. That is enough for a deterministic count. Decision 12's 023
     re-derivation should use the measured slope (610 × about 26,700, about 16 M), not
     24,000.
   - Check 6: with finding 1's fix, about 4,600 against 6,000.
   - Checks 4 and 6 on the snapshot include the lazy import of `_zip_resources` (unmarshal and
     class creation), which the memo did not measure. With 7.3 M and 9.7 M measured against
     15 M and 20 M, the margin covers it (INFERRED). The landing notes should give it.
   - Check 6's `files` comparison: compare `[(str(p), p.hash and p.hash.value, p.size) …]`.

8. **Small text points.** Low.
   - Decision 2: name `_io.open_code(archive)` as the open the fast path uses, as zipimport
     does. An embedder's open-code hook then sees the same calls (READ:
     `Lib/zipimport.py:297`).
   - Decision 2: `head` is `_path_join(archive, "x")[:-1]`, which equals `_path_join`'s answer
     for every archive, including `""` and `"/"` (READ: the POSIX `_path_join`).
   - Decision 10: "two more modules in the heap" is one at start under point A (`_zip_resources`
     is lazy).
   - Decision 12: spec 023 packs `mpl-data` as one inner archive because of the 76,490 per
     member cost. That stays right (its files are read from a grant, not through
     `importlib.resources`), so nothing in 023 changes but its numbers.

## Is it one builder's work?

Yes. It is about 350 lines of Python, 60 of C, a judge file, a zip helper and a golden job.
The pre-decided split is sound, and less likely to be needed now that both install points ran
on host 3.15.0. Suggested order, each step green before the next:

1. `render()` and the two header runs in step 60; the frozen table; phase 1 with
   `sys._stdlib_dir` and `read_directory` only. Checks 1, 2, 3 and 8.
2. The resource reader with finding 2's byte path and finding 3's definitions. Checks 4, 5
   and 7.
3. The metadata wrapper with finding 1's `zip_children`. Check 6.

## On questions 59 and 60

- **59 (our own `Traversable`):** agree for the runtime's zip. For other zips, agree only with
  finding 2's fallback, or with the reader limited to the runtime's zip. Amend the question's
  wording to match.
- **60 (a recipe, not a patch):** agree. See "What holds".

## Constitution checks

- **§4.1, patches few:** holds. No upstream file changes; spec 020's check is unaffected.
- **§4.4, two channels:** holds. Two frozen modules and C in the reactor; no import or export
  changes (READ: `PyImport_FrozenModules` and `_Py_InitializeMain` are libpython symbols).
- **§4.6, the artifact set:** holds. The zip's bytes do not change; `python.wasm` and the
  snapshot do, with `MANIFEST` naming the new recipe files.
- **§4.9, tests count:** holds. Every bound is fuel or equality; the slopes are differences on
  one driver whose fuel is exact.
- **§4.10, claims carry evidence:** the spec labels its claims. Decision 3 can now cite this
  review's host runs. Decision 7's cost does not match its own design (finding 1).
- **§4.11, platform semantics documented:** holds once the README names finding 3's accepted
  differences and finding 2's choice.
- **§4.15, safe by default:** at risk only through finding 2. A guest's zip read in chunks
  would need its whole member in memory. Fixed by either option.
- **§5.2, no open questions:** holds after findings 1 to 5 are written in.
- **§5.6, review before build:** this review.
- **§5.7, one build-class specification in flight:** holds. The order 033, then 035, then 023
  is stated, with a rule if 023 is already in flight.

## Disposition (filled in by the author, then confirmed by the reviewer)

The author, 2026-10-17. Every finding is fixed in the specification's text; none is answered
only in writing. The spec's status line cites this review.

1. **Fixed.** Decision 7's `zip_children` now returns upstream's own expression over zipimport's
   keys, `dict.fromkeys(name.split("/", 1)[0] for name in loader._get_files())`, in upstream's
   order. The children map is built only by `iterdir()` (Decision 6 says so). Decision 10's
   table gives the split's 4,608 per member from `children.txt`, and says the memo's 4,472 was
   the same split. Check 6's bounds are unchanged.
2. **Fixed, option (a), made stricter.** Decision 6 no longer reads bytes through
   `zipimporter.get_data`, which inflates a whole member with no bound. A member reader of ours
   serves a member only when: it is stored or deflate; its `file_size` and `data_size` are each at
   most 1 MiB; the local header has the right signature, the encryption bit clear, and the
   directory's method and name; inflation is capped at `file_size + 1` bytes and must give exactly
   `file_size`, a complete stream and the entry's CRC-32. Any other member, any failed test and
   any exception open through `zipfile.Path(archive, at).open(…)`. That covers LZMA and bzip2
   (zipimport cannot read them), corruption, encryption, large members (which stream again), and
   an inflate bomb. Overlap is not tested on the fast path; a read is bounded at 1 MiB, so it
   cannot amplify. Option (b) was not chosen: it would leave a guest's own zip paying the whole
   parse on every read, where (a) keeps the gain and upstream's strictness. `zlib` is imported,
   `zipfile` only on the fallback. Check 5 gains the guest-zip rows (LZMA, a bad CRC, a 2 MiB
   member read in chunks through a `zipfile` stream). A unit check,
   `test_the_member_reader_hands_odd_members_to_zipfile`, covers each route. Question 59's
   wording in `questions-for-the-owner.md` now says this. The metadata path reads `METADATA`
   through the same reader (Decision 7).
3. **Fixed.** Decision 6 writes out the exact definitions: `is_dir`, `exists`, `is_file`,
   `joinpath` with zipfile's `resolve_dir` rule (a file wins over a same-named directory; nothing
   is normalized), `name` and the root's name, `suffix`, `parent`, `str`, `==` (and
   `NotImplemented` for other types, which keeps numpy's `IS_INSTALLED` as 033 recorded), and
   `open` (directory first, `mode[0] == "r"` reads, `"b"` binary with no extra arguments,
   anything else `ValueError`; `"rt"` and `"r+"` are text). The three unavoidable differences
   (odd names' implied directories; duplicates and the empty name; equality across `files()`
   calls) are listed in Decision 6 and in the README row of the Design table. Check 5 and the
   unit check gain the `"UTC/"`, `"missing/"`, `"rt"`, `"r+"`, `"w"`, `"br"` and
   binary-with-encoding rows.
4. **Fixed.** Decision 3 sets `sys._stdlib_dir` with `PySys_SetObject` in phase 1, before the
   import, citing your `two_phase.txt`. Check 1 asserts `zipimport.__file__` and
   `_frozen_importlib_external`'s `loader_state.filename` against a one-phase start's values.
   Decision 5 says what `_zip_directory.__file__` reads.
5. **Fixed.** Decision 3 gives the API's removal in 3.14 and return in 3.15, and the docs'
   warning. A re-pin without `_Py_InitializeMain` or `PyConfig._init_main` uses point B at once,
   with no two strikes on A, and its memo records it. Decision 4 states point B's cost per event
   (INFERRED, about 1,000 to 3,000 fuel; your 654 events for four imports give about 0.7 M to
   2 M). It says how the builder measures the cost if B serves, and that more than 5,000 per
   event is a build-review finding. It also says the hook returns 0 with no exception set,
   clearing every failed lookup. Decisions 3 and 4 now cite your host runs as EXECUTED.
6. **Fixed.** The `guest` fixture's `stdlib=` keyword, defaulting to the artifact zip, is in
   Decision 11 and the Design table (`tests/checks/conftest.py`). `freeze_bootstrap.py` splits
   `compile_module()` and `render()` out of the version gate. `test_freeze_names_each_module`
   checks `render()` on fixed bytes against written-out text, and `co_filename` through
   `compile_module()` on the host's own Python, so it runs on 3.14. Decision 2 says
   `stock_read_directory` is a module global, looked up at each call.
7. **Fixed.** Decision 10 uses your measured numbers: today's start slope 79,077; expected
   about 26,700 (24,798 plus 1,931), with about 11% headroom under 30,000; the invalidate
   re-read the same; metadata about 4,600 under 6,000. Decision 12's 023 re-derivation is
   610 × 26,700, about +16 M. The `_zip_resources` import is named inside checks 4 and 6, and
   the landing notes give its cost. Check 6 compares `files` as `(str(p), p.hash and
   p.hash.value, p.size)`, and adds `origin`.
8. **Fixed.** Decision 2 names `_io.open_code(archive)` and `head = _path_join(archive,
   "x")[:-1]`. Decision 10 says one more module at start (`_zip_resources` is lazy). Decision 12
   says 023's inner archive stays right and only its numbers change.

Also, from spec 033's confirmation: the zip is 1,758 members (033's `ctypes/_types.py`), and
033's metadata account is reconciled. Part 3 recovers the scan of about 219 M. It does not
recover the `METADATA` parse (about 142 M) or most of `numpy.testing`'s +136 M; that is
`email`'s work, now in Scope as out. The landing notes measure both, as 033 asks. The order is
033, then this one, then 023.

## Verdict

Not ready to build as written, but close. The reader is right, and its fallbacks hold against
hostile zips. Both install points ran on CPython 3.15.0. Before the build:

- fix findings 1 to 4 in the text and checks (the metadata names come from a split, not the
  children map; resource bytes from a guest's zip take upstream's path when odd or large; the
  `Traversable`'s exact predicates and modes; `sys._stdlib_dir` in phase 1);
- answer 5 to 8.

These are text and check changes, not a new design. A confirmation of the dispositions is
enough; no further pre-build review is needed.

## One line

A sound recipe whose reader matches zipimport on every zip tried and whose start runs on
3.15.0. But its metadata path fails its own bound, and its resource reader would read a
guest's zip less strictly, and all at once. Fix those, pin the `Traversable`'s exact answers,
and keep `zipimport.__file__`, and it can be built.

## Confirmation (2026-10-17)

The same reviewer re-read the revised specification (commit `46d53f4`): Decisions 2 to 7, 10 and
11, the Design table, the unit checks, and Acceptance 1 to 9. I also re-read the reworded
question 59 and the Disposition above. Nothing in `src/`, `tests/`, `scripts/`, `recipes/` or
the spec was edited; nothing was committed; `scripts/build.sh` and the judge were not run.
Scripts and outputs are under
`/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/035-review/confirm/`.
They used the same copy of `build/artifacts/` (hashes checked), the judge's driver for guest
fuel, and the build's host CPython 3.15.0 through `uv run --no-project --python …` for host runs.

- `member_reader.py`: Decision 6's member reader, written from the revised text alone. It
  serves stored or deflate members only, with both sizes at most 1 MiB. It checks the local
  header (signature, encryption bit, method, and the name compared with `at.encode("utf-8")`).
  It inflates with `decompressobj(-15).decompress(raw, file_size + 1)`, then requires `eof`,
  exactly `file_size` bytes and the CRC-32. Anything else opens through `zipfile.Path`.
- `hostile.py` → `hostile.txt` and `dup_overlap.py` → `dup_overlap.txt` (host 3.15.0): 15 zips and
  16 member reads, each in 64 KiB chunks through our reader and through `zipfile.Path`.
- `measure2.py` → `measure2.txt` and `measure3.py` → `measure3.txt` (guest): a zone load through
  the member reader against `get_data`, and a metadata miss through the split `zip_children`,
  on the artifact zip (both binaries) and the padded zip (plain).

### The eight dispositions

1. **Confirmed.** Decision 7 now uses upstream's split over zipimport's keys, and only
   `iterdir()` builds the children map. Re-measured (EXECUTED, `measure2.txt`, a full
   `version("nope")` miss with the split `zip_children` in place):
   - snapshot: **9.42 M**, against the 20 M bound;
   - plain: 9.59 M on the artifact zip and 33.87 M on the padded zip, a slope of **4,622 per
     member** against 6,000.
   Both match the Disposition's 4,608 and about 4,600.
2. **Confirmed. The stricter option (a) holds on every hostile member tried.** EXECUTED
   (`hostile.txt`): our bytes, or our exception type, equal `zipfile.Path`'s in all 15 cases of `hostile.txt`.
   The route is as Decision 6 says:
   - plain small deflate and stored members take the fast path, with the right bytes;
   - LZMA and bzip2 go to `zipfile`, with the right bytes;
   - a bad CRC gives `BadZipFile` (through `zipfile`);
   - the encryption bit gives `RuntimeError` (through `zipfile`);
   - a local name that differs gives `BadZipFile`;
   - a local method that differs, and a deflate stream one byte short, go to `zipfile`, which
     reads them;
   - stored and deflate members of 2 MiB stream through a `ZipExtFile`, which check 5's
     "not a `BytesIO`" row relies on;
   - a lying bomb (50 MB of zeros declared as 100 bytes) is capped at 101 bytes and handed to
     `zipfile`, which gives 100 bytes;
   - an honest 50 MB inflate is over the limit, and streams through `zipfile`;
   - an overlapped entry under another name fails the local-name test and gets `zipfile`'s
     `BadZipFile`.
   The one gap Decision 6 accepts, overlap, is closed in practice too
   (`dup_overlap.txt`). A same-named second entry on the first entry's header fails the CRC
   test, and `zipfile` raises `Bad CRC-32`, as upstream does. No fast-path read allocates more
   than 1 MiB + 1 bytes.
   - Cost (EXECUTED, `measure2.txt`): a first `ZoneInfo("Europe/Paris")` through the member
     reader is **7.34 M** on the snapshot and 7.38 M and 7.37 M plain on the two zips (a slope
     of −3 per member). The bounds are 15 M and 20 M. Against `get_data` it costs 0.69 M more on
     the snapshot.
   Question 59's new wording matches.
3. **Confirmed.** Decision 6 now writes out every predicate, `joinpath`'s `resolve_dir` rule,
   `name`, `parent`, `str`, `==` and `open`'s modes. Each matches `zipfile.Path` in 3.15 as I
   read it and as `trav.txt` ran it. The three accepted differences are listed, and the README
   row names them. Check 5 and the unit check carry the rows asked for.
4. **Confirmed.** Decision 3 sets `sys._stdlib_dir` in phase 1, and check 1 asserts both values.
   This is the variant `two_phase.txt` ran.
5. **Confirmed.** The history, the rule for a re-pin (point B at once), and B's per-event cost
   are written in, with how to measure that cost and a 5,000-fuel ceiling. The hook's
   no-exception rule is written in.
6. **Confirmed.** The fixture's `stdlib=` keyword is in Decision 11 and the Design table.
   `compile_module()` and `render()` are outside the version gate, so the unit check runs on
   3.14. `stock_read_directory` is a global looked up at each call.
7. **Confirmed,** with one figure to correct (C1 below).
8. **Confirmed.**

### New points (none blocks the build)

- **C1. Decision 10's "a second zone, about 0.6 M" is too low for check 4's case.** EXECUTED
  (`measure3.txt`): check 4's C − B, `Asia/Tokyo` after `Europe/Paris`, is about **1.34 M**
  on the snapshot and 1.36 M plain through the member reader. Through `get_data` it is
  1.32 M and 1.30 M, so the member reader adds only 20,000 to 60,000. Most of it is
  importing the new package `tzdata.zoneinfo.Asia`; with that package already imported the
  zone costs 0.86 M and 0.83 M. The memo's 0.6 M was for zones in an already-imported folder.
  So the 2 M bound holds, but with about 0.65 M of headroom (about 33%), not threefold. That
  margin also covers `ZipDirectoryPath`'s own `joinpath` and `resolve_dir`. Correct the table
  row to "about 1.35 M (it imports `tzdata.zoneinfo.Asia`)". The landing notes give the
  measured C − B.
- **C2. "The directory's name, byte for byte" needs one word on how.** zipimport's toc keeps
  the decoded name, not the raw bytes. So the test is the local name against
  `at.encode("utf-8")`, as the prototype does. A cp437-named member then always goes to
  `zipfile`, which is the safe direction. Say so in Decision 6, so a builder does not keep raw
  names in a second table.
- **C3.** The member reader may open the archive with `_io.open_code`, as zipimport and
  Decision 2 do, so an embedder's open-code hook sees every read. That is optional; say which.

### Result

**Confirmed for build,** on one condition: C1's table row is corrected in Decision 10 before
the build starts. C2 and C3 are one-line clarifications the author may write in at the same
time. No further pre-build review is needed. The build review re-runs checks 4 and 6 and the
member-reader unit check against the built artifacts.

One line: every finding is fixed as written. The stricter member reader matches
`zipfile.Path` on all 16 hostile member reads tried, and never allocates more than 1 MiB. The split
metadata path measures 9.4 M and 4,622 per member, inside its bounds. Correct the
second-zone figure, and 035 can be built.

### The author's note on the conditions (written in by the lane, 2026-10-17)

- C1: Decision 10's table now gives the second zone as about 1.35 M, mostly the import of
  `tzdata.zoneinfo.Asia`; the bound stays 2 M.
- C2: Decision 6's local-header test compares the name as `at.encode("utf-8")`.
- C3: Decision 6's member reader opens the archive with `_io.open_code`, as zipimport does.
