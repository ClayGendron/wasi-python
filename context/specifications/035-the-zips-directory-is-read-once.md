# 035 — The zip's directory is read once

- **Status:** drafted 2026-10-17. It changes the build recipe and how the interpreter starts, so
  it is reviewed once more before it is built (constitution §5.6). It is build-class: it touches
  `recipes/` and `scripts/` (§5.7).
- **Owner:** Clay Gendron
- **Kind:** the build recipe (`recipes/reactor_main.c`, two new recipe modules
  `recipes/zip_directory.py` and `recipes/zip_resources.py`, `scripts/freeze_bootstrap.py`,
  `scripts/steps/60_link.sh`), judge additions (a new check file, a zip-making helper, a golden
  job, unit checks), `README.md`, `CHANGELOG.md`, an upstream courtesy-issue draft.
- **Depends on:** 003 (the reactor, `_reactor`, step 60), 008 (fuel counts the guest), 012 (the
  same bytes from any host), 002 (the judge and its ratchet). All landed. It does not depend on
  033 or 023; Decision 12 orders them.
- **Research it stands on:** `../research/2026-10-17-the-zips-directory-is-read-once.md` and its
  evidence folder (`scripts/candidates.py` holds the prototypes; `outputs/derived.txt` every
  derived number). Findings 1 to 5 and its design section are this specification's base. The
  owner's decision 44 (`../decisions.md`, "43–48": cut the zip's per-member cost first, before
  tier A grows the zip). Questions 59 and 60 (`../questions-for-the-owner.md`), drafted here with
  the recommended answers.

## The problem

Every member of the stdlib zip costs fuel on every plain start. A plain start reads the zip's
central directory once, in zipimport's Python reader, at **77,662 fuel per member** (EXECUTED by
the memo, finding 1). Today that is 56% of a plain `-c pass` (241.7 M). At 0.1.0's zip, about
6,630 members, it would be 83% (about 619 M, INFERRED, linear).

Snapshot calls do not pay it at start: Wizer froze zipimport's parsed directory. But every call,
snapshot or not, pays a whole parse again in three other places (EXECUTED, findings 2, 3 and 5):

- **Each resource read.** `importlib.resources` on a zip builds a fresh `zipfile.Path`, which
  parses the directory again and builds a name set: about 124,000 fuel per member, per read. A
  first `ZoneInfo('Europe/Paris')` costs 205.4 M on the snapshot, more than two whole snapshot
  calls. A pandas job that makes one Paris timestamp and a Tokyo range costs 962.1 M on the
  snapshot.
- **The first `importlib.metadata` query in a process.** `FastPath.zip_children` builds a
  `zipfile.Path` of the whole archive: a missing distribution costs 217.5 M on the snapshot.
  Spec 033 keeps `METADATA` in the zip, so these queries become common.
- **A re-read after `importlib.invalidate_caches()`**, which agent code calls after it writes a
  module: 170.8 M more on the snapshot.

All of these grow with the zip. Tier A will nearly quadruple it.

## Decisions

1. **One specification, three parts, one install.** The parts are the memo's design:
   1. a faster directory reader, in place before the first import from the zip;
   2. a resource reader that answers from the directory zipimport already holds;
   3. `importlib.metadata`'s zip search on that same directory.

   They stay together. They share one install seam, one rebuild, one review of the same rule
   (stdlib functions replaced at run time by recipe code, question 60) and one accept. Parts 2
   and 3 share one `Traversable`. The whole is about 350 lines of Python, 60 of C and a judge
   file; one builder builds it.

   One split is decided now, in case it is needed. If neither install point (Decisions 3 and 4)
   serves the start, the builder stops after two attempts on each (AGENTS.md rule 7) and records
   why in the landing notes. Parts 2 and 3 then become their own specification. They need no
   early install: they work installed right after `Py_InitializeFromConfig`. Part 1 waits for a
   new memo. Nothing half-built lands (§5.4).

2. **The directory reader (part 1).** A frozen module of ours, `_zip_directory`, from
   `recipes/zip_directory.py`. Its `read_directory(archive)` returns **the same dict** as
   zipimport's `_read_directory(archive)`: the same keys, the same toc tuples, **in the same
   order**. It does one read of the central directory and one `_struct` unpack per member (the
   memo's `read_directory_struct`, 24,129 fuel per member, EXECUTED). It imports only `_io`,
   `_struct` and `zipimport` (and through it `_frozen_importlib_external`).
   - **The plain case.** It reads the same tail window zipimport reads (65,535 + 22 + 56 + 20
     bytes). It finds the last end record (`PK\x05\x06`), applies zipimport's three offset checks,
     reads `cd_size` bytes at the directory's start, and walks `n` entries. Per entry it keeps
     zipimport's fields: `(path, compress, data_size, file_size, file_offset + arc_offset, time,
     date, crc)`. `path` equals `_bootstrap_external._path_join(archive, name)`. For a name that
     is non-empty and does not end in `/` that is one concatenation, `head + name`, with `head`
     computed once; any other name calls `_path_join` itself. Then it adds the implied
     directories with zipimport's own loop, so the order matches.
   - **Everything else goes to zipimport's reader.** The module keeps the original as
     `stock_read_directory`. It calls it, and returns its result or lets its error rise, when
     any of these holds: the tail holds `PK\x06\x06` (a Zip64 end record) anywhere; no end
     record; an end-record field at its maximum (`0xFFFF` or `0xFFFFFFFF`); any entry field at
     `0xFFFFFFFF` (a Zip64 extra); a name without the UTF-8 flag that is not ASCII (cp437); an
     entry past the bytes read; a bad signature; a local-header offset past the directory's;
     another `PK\x01\x02` after `n` entries; or any exception. So Zip64, cp437 names and every
     error are upstream's, with upstream's messages. A Zip64 zip costs one cheap probe more than
     today, then today's cost.
   - **What served each read.** The module keeps `served`, a dict from archive to `"fast"` or
     `"stock"`, set at each read. It is one store per read. It lets a check see which path ran.
   - It is used only where `zipimport.path_sep == "/"`, which is always true in the guest.
     `install()` leaves zipimport untouched otherwise.

3. **Where it goes in: the interpreter's two-phase start (install point A).** The first read
   happens inside `Py_InitializeFromConfig`, when `encodings` is imported from the zip (EXECUTED
   by the memo, finding 1). So `recipes/reactor_main.c` starts the interpreter in two phases:
   - `config._init_main = 0`, then `Py_InitializeFromConfig(&config)`. This runs the core phase
     only: builtin and frozen importers work; nothing has touched the zip.
   - The magic check of each frozen recipe module, as `_reactor`'s is. Then
     `PyImport_ImportModule("_zip_directory")` and its `install()`, through the C API, with no
     source compiled. On failure: `PyErr_Print()` and `abort()`, as for `_reactor`. A broken
     recipe never ships quietly.
   - `_Py_InitializeMain()`, which runs the main phase: the path hooks, zipimport's hook, then
     `encodings`, now read by our reader.
   - The rest of `init_interpreter` is unchanged: `_reactor`, then the `site` helpers.

   `install()` sets `zipimport._read_directory`. zipimport looks the name up at each call
   (`zipimporter.__init__` and `_get_files`, READ). So the replacement serves the start, every
   later zip on `sys.path`, and every re-read after `invalidate_caches()`. Both binaries use it;
   the snapshot freezes the dict our reader built.

   Why it should work (READ, `build/Python-3.15.0/`): `PyConfig._init_main`
   (`Include/cpython/initconfig.h:230`) and `_Py_InitializeMain`
   (`Include/cpython/pylifecycle.h:29`) exist in 3.15. `Py_InitializeFromConfig` skips
   `pyinit_main` when `_init_main` is 0 (`Python/pylifecycle.c:1631`). CPython's own
   `test_init_main` runs Python between the phases (`Programs/_testembed.c:2094`). `zipimport`
   and `_frozen_importlib_external` are in the bootstrap frozen table, which is always searched
   (`Python/frozen.c:70`, `Python/import.c:3126`). `_struct` is builtin here (EXECUTED by the
   memo). When the main phase runs `_install_external_importers` and `init_zipimport`, it imports
   both modules by name and so finds the ones phase 1 left in `sys.modules`, with our function
   in place (`Lib/importlib/_bootstrap.py:1549`, `Python/import.c:4801`, READ).

   **This path is INFERRED.** Nothing above was run. The first check (Acceptance, check 1) runs it
   before any other work depends on it. The two names are private, provisional API. A re-pin of
   CPython re-runs check 1, which fails loudly if they change.

4. **If the two-phase start does not work: a C audit hook (install point B).** Decided now, so
   the builder does not stop to ask (§5.2). It is used only if check 1 fails twice on point A,
   and the landing notes record both failures.
   - Before `Py_InitializeFromConfig`, `reactor_main.c` calls
     `PySys_AddAuditHook(zip_hook, NULL)`. The C API documents it as safe before initialization.
     Initialization is then one phase, as today.
   - `zip_hook` returns 0 at once unless the event is `"import"`. On an `"import"` event it looks
     for `zipimport` in `sys.modules`, fully executed: its `__spec__._initializing` is false.
     (`init_zipimport` imports zipimport before any zip is read. Each import raises `"import"`
     before its finders run: `_find_and_load_unlocked` audits, then calls `_find_spec`, READ in
     `Lib/importlib/_bootstrap.py`.) The first time both hold, the hook sets a
     static flag, imports `_zip_directory` and calls `install()`. On failure it prints and aborts.
     The flag also stops the import inside `install()` from re-entering. That moment is before
     the first `zipimporter` is made, so the first read is ours.
   - **Its cost:** once a hook exists, CPython builds an argument tuple for every audited event
     (imports, opens, `marshal.loads`, `compile`, `exec`). Our hook then returns at the flag. That
     is a small C cost per event, for the life of the process. Checks 2 to 8 bound it by the
     same numbers, and the landing notes give it, measured on plain and snapshot
     `import pandas`.
   - The guest cannot see or remove the hook. It opens no channel (§4.4, §4.15).

5. **How the modules are frozen and found.** Both new modules are compiled at build time, as
   `_reactor` is.
   - `scripts/freeze_bootstrap.py` takes two optional arguments, the C array's name and the code
     object's file name: `freeze_bootstrap.py <src.py> <out.h> [<NAME> <filename>]`. The header
     defines `<NAME>` and `<NAME>_MAGIC`. The defaults, `REACTOR_BOOTSTRAP` and `<reactor>`, give
     today's header byte for byte. The rendering moves into a function, `render(data, magic, name,
     source)`, so a unit check runs it on any host Python.
   - Step 60 runs it twice more: `recipes/zip_directory.py` → `$L/zip_directory.h`
     (`ZIP_DIRECTORY`, `<frozen _zip_directory>`), and `recipes/zip_resources.py` →
     `$L/zip_resources.h` (`ZIP_RESOURCES`, `<frozen _zip_resources>`). The file names follow
     CPython's frozen modules, so tracebacks read like theirs.
   - `reactor_main.c` lists the two in a static `struct _frozen` table and sets
     `PyImport_FrozenModules` to it before `Py_InitializeFromConfig`. That is CPython's public
     hook for an embedder's frozen modules (`Include/cpython/import.h:30`). They are searched
     after the bootstrap table, so they cannot shadow `zipimport`. So `import _zip_directory`
     works in phase 1, and `import _zip_resources` works lazily, on first use, through the frozen
     importer. Their `__spec__.origin` is `"frozen"`.
   - `_reactor` is loaded as today. Moving it is not this specification's business.
   - Nothing is added to the zip. **The zip's bytes do not change**, and step 70 is untouched.

6. **The resource reader (part 2).** `install()` sets `zipimport.zipimporter.get_resource_reader`
   to a small function in `_zip_directory`. It imports `_zip_resources` on first use and returns
   `ZipDirectoryReader(self, fullname)`. `_zip_resources` imports `importlib.resources.abc`
   (already imported by then), `io`, `os`, `posixpath` and `zipimport`. It does not import
   `zipfile`.
   - **`ZipDirectoryReader`** subclasses `TraversableResources`. Its root prefix is computed as
     `importlib.resources.readers.ZipReader` computes it: the loader's prefix, plus the package's
     last name and `/` for a package. `files()` returns that root. `is_resource(path)` answers as
     `ZipReader.is_resource` does. `open_resource` and `resource_path` are the base class's
     (`FileNotFoundError` for a missing name; `resource_path` always raises it, as for
     `ZipReader`).
   - **`ZipDirectoryPath`** subclasses `Traversable`. It holds the loader and `at`, a name in the
     archive (`""` for the root, `a/b/` for a directory, `a/b/c` for a file). It answers from
     `loader._get_files()`, zipimport's cached dict, and reads bytes through `loader.get_data`,
     which every import already uses. It never touches `zipimport._zip_directory_cache`
     (CPython #121342, READ: direct use broke when 3.13 made invalidation lazy). `_get_files()`
     refills the dict after `invalidate_caches()`.
   - **It mirrors `zipfile.Path` where the two meet:**
     - `joinpath(*parts)` is `posixpath.join(at, *map(os.fspath, parts))`, plus a trailing `/`
       when that names a directory; `/` is `joinpath`;
     - `name`, `suffix`, `suffixes`, `stem`, `is_dir`, `is_file`, `parent` (the root's
       parent is `pathlib.Path(archive).parent`, as for `zipfile.Path`), `str()`
       (`posixpath.join(archive, at)`), `==` and `hash` on (archive, `at`);
     - `open("rb")` gives a `BytesIO`, and `ValueError` if given text arguments; `open("r", …)`
       gives a `TextIOWrapper` with `io.text_encoding`'s default, as `zipfile.Path.open` does;
       any other mode raises `ValueError` (the read-only `ZipFile` behind `zipfile.Path` raises
       it too, READ: `_writecheck`);
     - `exists()` is `at in` the dict, as `zipfile.Path`'s is `at in` its name set;
     - the errors: `iterdir()` on a file raises `ValueError`; `open` of a missing name raises
       `FileNotFoundError`; `open` of a directory raises `IsADirectoryError`;
     - `read_bytes` and `read_text` are `Traversable`'s, through `open`.
   - **`iterdir()`** uses a children map: directory name to its children, in the dict's order.
     It is built in one pass over the names the first time any directory of that archive is
     listed. It is kept with the dict object it came from and rebuilt when `_get_files()` returns
     another (after `invalidate_caches()`). A later listing costs its own children only.
     Listing order is not promised, as for `zipfile.Path`; the checks compare sorted names.
   - **Not provided:** `zipfile.Path`'s own attributes (`root`, `at`, `filename`) and its
     `glob`, `rglob`, `match`, `relative_to` and `is_symlink`. They are not part of `Traversable`.
     Code that needs them breaks; code using `Traversable`, and `importlib.resources.as_file`,
     works as before. `as_file` still copies the resource to a temporary file, so it still
     needs a writable temporary folder, as it does today with `zipfile.Path`.
   - Namespace packages inside a zip keep the stock `NamespaceReader` path (it builds its own
     `zipfile.Path`). No package in the zip needs it.
   - This is question 59's recommended answer, which the agent takes: a type of our own, the
     same bytes and listings.

7. **`importlib.metadata` on the same directory (part 3).** `install()` replaces
   `_frozen_importlib_external.PathFinder.find_distributions` with a wrapper. The wrapper makes
   sure `importlib.metadata.FastPath.zip_children` is ours (one identity test after the first
   call), then calls the original.
   - **Why this seam.** `PathFinder.find_distributions` runs only when a program asks for
     metadata (`Distribution.discover` calls it on each `sys.meta_path` finder, READ). So it costs
     nothing per import. The memo proposed a wrapper on `zipimporter.exec_module`. That costs a
     Python call per module imported from the zip until `importlib.metadata` loads, and would
     grow snapshot checks that import a few modules past the ratchet's 0.01%. It is rejected.
     The wrapper stays in place, not restored, so a reloaded `importlib.metadata` is patched again.
   - **Our `zip_children`** answers only for a zip on the import path. When
     `sys.path_importer_cache.get(self.root)` is a `zipimporter` with an empty prefix, it sets
     `self.joinpath` to the root `ZipDirectoryPath`'s `joinpath`. It returns the top-level names
     from the children map, as a dict in the order of first appearance, as upstream's does. Any
     other root (a zip not on `sys.path`, a zip with a prefix) gets upstream's `zip_children`,
     kept as `stock_zip_children`. A zip on the import path is then as current as zipimport's
     view of it, which `invalidate_caches()` refreshes for both.
   - **It works with spec 033's members.** `PathDistribution` reads `METADATA` and
     `entry_points.txt` through our path's `joinpath(…).read_text(encoding="utf-8")`. A missing
     `RECORD` gives `None`. `str()` of a `.dist-info` folder equals `zipfile.Path`'s (it ends in
     `/`), so `_normalized_name` takes the same branch. `locate_file` uses `parent` and `/`.
     Check 6 compares every answer with upstream's objects on the same zip.

8. **A recipe, not a patch (question 60, the recommended answer).** Three stdlib functions are
   replaced at run time: zipimport's directory reader, `zipimporter.get_resource_reader`, and
   `importlib.metadata`'s zip search (through `PathFinder.find_distributions`). No upstream file
   changes, and every pinned tree still equals its tarball plus the recorded patches (spec 020).
   The rule that keeps it honest: each replacement gives upstream's results, and a judge check
   compares them on every case named in Acceptance. A carried patch would stay carried for good:
   upstream builds `_struct` outside the bootstrap, so zipimport cannot use it (memo, finding 4).
   The memo's courtesy issue is drafted for the owner to send, to python/importlib_resources:
   "`ZipReader.files()` parses the archive on every call; zipimport's directory already has it"
   (`context/upstream/4-importlib-resources-zip-directory/issue.md`). Nothing here waits on it.

9. **What a guest sees.** `import _zip_directory` and `import _zip_resources` work, as
   `import _reactor` does. `zipimport._read_directory`,
   `zipimport.zipimporter.get_resource_reader` and `PathFinder.find_distributions` are our
   functions. `importlib.resources.files(pkg)` for a package in a zip on `sys.path` is a
   `ZipDirectoryPath`, not a `zipfile.Path`. `importlib.metadata` gives the same answers. Every
   import, every byte read, `pkgutil` (which reads zipimport's dict directly) and every golden
   output are unchanged. The `-V` banner is unchanged. The README says what changed (Design).

10. **What it costs and saves, so a fall can be told from a regression.** Today's numbers are
    EXECUTED by the memo, and re-run while drafting with `wasi_python.run` on `build/out`
    (`python.wasm` `4befe9de…`, `python-snapshot.wasm` `c7302cfd…`, `python-stdlib.zip`
    `1add57e4…`, the memo's set). The "after" numbers are INFERRED from the memo's prototypes.

    | what | today | after (INFERRED) | bound |
    |---|---|---|---|
    | plain `-c pass`, 1,751 members | 241.8 M | about 149 M | slope ≤ 30,000 per member (check 2) |
    | plain `-c pass`, about 6,630 members | about 619 M (linear) | about 267 M | |
    | snapshot `-c pass` | 81.9 M | 81.9 M | the ratchet (check 9) |
    | first zone after `import zoneinfo, importlib.resources`, snapshot | 205.6 M | about 7 M | ≤ 15 M (check 4) |
    | the same, plain | 255.7 M | 11 M to 14 M | ≤ 20 M on both zips; slope ≤ 1,000 per member |
    | a second zone | about 182 M | about 0.6 M | ≤ 2 M |
    | metadata miss after `import importlib.metadata`, snapshot | 218.9 M | about 10 M | ≤ 20 M (check 6) |
    | the same, plain, slope | 132,458 per member | about 4,500 | ≤ 6,000 per member |
    | pandas time-zone job, snapshot, after `import pandas, zoneinfo, importlib.resources` | 961.0 M | about 29 M | ≤ 60 M (check 7) |
    | `invalidate_caches()` then an import, plain, slope | 77,842 per member | about 24,000 | ≤ 30,000 per member (check 8) |

    The drafting runs: snapshot `pass` 81,916,308; `import zoneinfo, importlib.resources`
    101,895,320, then `ZoneInfo('Europe/Paris')` 307,505,192; `import importlib.metadata`
    117,387,162, then a missing `version('nope')` 336,264,649; `import pandas, zoneinfo,
    importlib.resources` 101,998,294, then the job 1,063,016,795. Plain `pass` 241,815,784;
    `import zoneinfo, importlib.resources` 614,592,426, then Paris 870,317,283. The invalidate
    slope is the memo's (671.7 M − 262.8 M) over (7,004 − 1,751) members. The baselines import
    `importlib.resources` and `importlib.metadata` first because those imports cost about 20 M
    and 35 M on the snapshot and are not the reader's work.

    **The ratchet.** Fuel falls on every plain check, by about 93 M each (more on checks that
    read resources). A fall is not growth; the ratchet records it. Snapshot checks move only
    where they read resources, query metadata or invalidate caches. Elsewhere they may move by
    a few thousand fuel (two more modules in the heap). A growth above the 0.01% tolerance is
    accepted with its measured reason. A snapshot `-c pass` that grows by more than 0.1%, or any
    plain check that grows, is a finding for the build review, not a reason to accept.

    **The artifact set.** `python.wasm` grows by the two frozen modules and the C table, about
    20 KB (INFERRED; a `bytes` growth the accept names). The snapshot changes. The zip does not
    change, byte for byte. `MANIFEST` gains `recipe` lines for the two new recipe files, and the
    lines for `recipes/reactor_main.c`, `scripts/freeze_bootstrap.py` and
    `scripts/steps/60_link.sh` change. `SHA256SUMS` changes for both binaries and `MANIFEST`.

11. **The checks** are listed in Acceptance. They live in a new file,
    `tests/checks/test_v1_3_the_zips_directory.py`, goal v1.3: constitution §2.3, "every
    compiled-in package imports and works", here the stdlib's own import and resource
    machinery. They run on the judge's driver (`tests/harness/guest.py`), which answers random
    and the clock itself, so fuel repeats to a few parts in ten million. A bound's slack is for
    the design, not for noise. Zips the checks need are made on the host by a new helper,
    `tests/harness/zips.py`, under `build/harness`, once per session:
    - `small.zip`: a copy of the artifact zip, opened in append mode, plus two made-up
      distributions (`judge_meta_a-1.0.dist-info/METADATA`; `judge_meta_b-2.0.dist-info/` with
      `METADATA`, `entry_points.txt` and a `RECORD`). Append mode keeps every existing member's
      bytes, so imports from it cost what they cost from the artifact zip. The names cannot clash
      with spec 033's.
    - `padded.zip`: `small.zip`'s members plus a copy of each artifact member under `pad1/`,
      `pad2/` and `pad3/`, as the memo's `make_zips.py` does, added in append mode at zlib
      level 1. Nothing imports from `pad*/`, and a member's compression does not change the
      directory's cost (memo, finding 1). The two zips differ by three times the artifact's
      member count; slopes use each zip's real count.
    - the odd zips of check 3, written by hand or with `zipfile`, each checked on the host for the
      feature it must have before any guest runs. A check never passes on a zip that lacks it.

    The snapshot runs only beside its own zip (spec 003), so slopes are plain-only, and the
    snapshot's bounds are on the artifact zip.

12. **Ordering with other build-class work** (§5.7: one build-class specification in flight; a
    change to the build recipe overlaps no other). Spec 033 (in pre-build review) builds first.
    Question 57 decided it may land before this one, and it is small. This specification
    builds next, and spec 023 (matplotlib M1) after it. Why before 023: 023 adds about 610 zip
    members, the largest growth planned, and the roadmap's milestone 4 places this cut "before
    the zip grows (decision 44)". If 023 is already being built when this one is confirmed, this
    one waits; its checks are slopes and differences, so they hold on either zip.
    - **With 033:** no file overlaps (033 changes step 70 and `make_stdlib_zip.py`; this one step
      60 and the reactor). If 033 has landed, its `test_packages_carry_their_metadata` runs
      through part 3 and must still pass. 033's Decision 7 estimate of a first metadata lookup
      (about 0.2 G) becomes about 10 M.
    - **With 023:** both change step 60. Whichever builds second rebases onto the other's step 60.
      If this one lands first, 023's Decision 6 plain-start figures were stated at 76,490 fuel
      per member. Its builder re-derives them at this one's measured slope (about 610 × 24,000,
      about +15 M rather than +47 M) and records that in 023's landing notes. Otherwise 023's
      "outside these by more than a tenth" rule would flag a smaller growth.
    - Tier A waits for this one (decision 44).

## Intent

A zip's directory is parsed once per process, by a reader three times cheaper than today's. Every
later use (imports, resource reads, metadata, a re-read after invalidation) answers from that
one parse. The answers stay upstream's, byte for byte.

## Design

| file | change |
|---|---|
| `recipes/zip_directory.py` | new: `read_directory`, `stock_read_directory`, `served`, `install()`, the `get_resource_reader` and `find_distributions` wrappers (Decisions 2, 6, 7) |
| `recipes/zip_resources.py` | new: `ZipDirectoryReader`, `ZipDirectoryPath`, the children map, `zip_children`, `stock_zip_children` (Decisions 6, 7) |
| `recipes/reactor_main.c` | the two headers; the `struct _frozen` table and `PyImport_FrozenModules`; `_init_main = 0`, the magic checks, `_zip_directory.install()`, `_Py_InitializeMain()` (Decision 3); install point B only if Decision 4 applies; the file's header comment |
| `scripts/freeze_bootstrap.py` | the optional `<NAME> <filename>` arguments and `render()` (Decision 5); its docstring |
| `scripts/steps/60_link.sh` | two more `freeze_bootstrap.py` runs into `$L/` (Decision 5) |
| `tests/checks/test_v1_3_the_zips_directory.py` | new: checks 1 to 8 |
| `tests/harness/zips.py` | new: `small.zip`, `padded.zip` and the odd zips (Decision 11) |
| `tests/jobs/pandas_tz.py`, `tests/jobs/pandas_tz.expected`; `JOBS` in `tests/harness/jobs.py` | new golden job (check 7), its golden from the pinned oracle through `regen.py` |
| `tests/unit/test_zip_directory.py` | new: the recipe modules on the host |
| `tests/unit/test_build_scripts.py` | `test_freeze_names_each_module` |
| `README.md` | the recipe paragraph names the two frozen modules; the platform paragraph says `importlib.resources.files()` on a zip gives the runtime's own `Traversable` (same bytes and listings; no `root`, `at`, `glob`); the speed table's plain-reactor row re-measured |
| `CHANGELOG.md` | the next unreleased section: the zip's directory is read once; resource reads and metadata no longer parse the zip |
| `context/upstream/4-importlib-resources-zip-directory/issue.md`, `context/upstream/README.md` | the courtesy issue draft and its row (Decision 8) |

Unit checks (no artifacts), each seen failing first because the module does not exist:

- `test_the_fast_reader_matches_zipfile_on_the_host`: `recipes/zip_directory.py` loaded under a
  private name. On zips the check makes (plain members, explicit directory entries, bytes
  prepended, an archive comment), each entry's fields equal the host `zipfile`'s `ZipInfo`
  (offset plus prepended bytes, both sizes, CRC, method, DOS time and date). The implied
  directories equal the set `zipfile.Path` implies. `served` says `"fast"`. It compares with
  `zipfile`, not the host's zipimport, because the host's Python may not be 3.15.
- `test_odd_zips_go_to_the_stock_reader`: with a recording stub as `stock_read_directory`, a
  Zip64 zip, a cp437 name, a truncated directory and one entry more than declared each call the
  stub. Its result, or its exception, comes back unchanged. `served` says `"stock"`.
- `test_the_zip_path_answers_as_a_traversable`: `ZipDirectoryPath` over a fake loader (a dict
  and `get_data`). It checks `joinpath` with several parts and with `/`, `name`, `parent`,
  `str()`, `is_file`, `is_dir`, `exists`, `iterdir` (and `ValueError` on a file), both `open`
  modes, and the three errors, against written-out expected values. The children map is built
  once and rebuilt for a new dict.
- `test_freeze_names_each_module`: `render()` with a name and a file name writes `#define
  NAME_MAGIC`, `NAME[]`, and code whose `co_filename` is the name given. The default call
  renders today's `reactor_bootstrap.h` byte for byte.
- `test_the_judges_zips_have_what_they_claim` (in `tests/unit/test_zip_directory.py`): the
  helper's Zip64 zip has `PK\x06\x06` and `0xFFFFFFFF` fields; the cp437 zip has flag bit 11
  clear and a byte at or above `0x80` in a name; `small.zip` keeps each artifact-like member's
  local entry byte for byte.

## Scope

In: the above. Out:

- **A C reader, or a pre-parsed index shipped with the zip.** The memo's numbers: about 190 M
  at 6,630 members instead of about 267 M (INFERRED), at the price of a C zip parser to review,
  or a second artifact that can go stale. Snapshot calls, the default, pay nothing at start. A
  later memo may show the plain start needs it.
- **Moving `_reactor` into the frozen table.** It works as it is.
- **Namespace packages' resources in a zip** (Decision 6), and **`zipfile.Path`'s extra
  attributes** (Decision 6).
- **The `importlib_metadata` and `importlib_resources` backports**, if a tier-A package brings
  one. They keep their own zip parse. The tier-A specification looks at it if one is carried.
- **Any change to the zip, step 70 or `make_stdlib_zip.py`:** spec 033's.
- **Trimming fontTools or any package's member count:** spec 023's Scope.

## Acceptance criteria

Every guest check runs on the judge's driver. "Plain" is the plain reactor. A slope is
(fuel on `padded.zip` − fuel on `small.zip`) ÷ (members of `padded.zip` − members of
`small.zip`). Each check records as its metric the fuel of its measured program on `small.zip`
(plain) or on the artifact zip (snapshot), run last. Each was seen failing first on today's set,
as written.

1. **`test_the_zip_reader_is_ours_from_the_first_import[plain, snapshot]`**, the gate. In the
   guest: `zipimport._read_directory is _zip_directory.read_directory`;
   `_zip_directory.served == {"/usr/local/lib/python315.zip": "fast"}` with no extra call, so
   the start's own read was ours; `sys.modules["encodings"].__spec__.loader` is a
   `zipimporter`; `zipimporter.get_resource_reader` and `PathFinder.find_distributions` are
   ours; `_zip_directory.__spec__.origin == "frozen"`. Seen failing first:
   `ModuleNotFoundError: _zip_directory`. Built and run before parts 2 and 3. Its landing note
   says which install point serves (Decisions 3 and 4).
2. **`test_a_plain_start_grows_at_most_30k_fuel_per_member`**: plain `-c pass`; the slope is at
   most **30,000**. Seen failing first: today about 77,662.
3. **`test_the_fast_reader_builds_zipimports_dict[<zip>]`**, plain, for each zip: `small.zip`,
   `padded.zip`, a Zip64 zip (a Zip64 end record and Zip64 extras), a zip whose module name is
   cp437 without the UTF-8 flag, a zip with explicit directory entries, a zip with bytes
   prepended and an archive comment, and a zip with a truncated directory. The odd zips are
   written into the guest's root and their paths put on `sys.path`. In the guest:
   `list(read_directory(p).items()) == list(stock_read_directory(p).items())`, so keys, values
   and order are equal; `served[p]` is `"stock"` for the Zip64 and cp437 zips and `"fast"`
   for the rest; the truncated zip raises the same type and message from both. A module from
   the Zip64 zip and the cp437-named module both import. On the snapshot, the frozen
   `zipimport._zip_directory_cache` entry for the artifact zip equals
   `stock_read_directory`'s, as lists of items. Seen failing first: `_zip_directory` is missing.
4. **`test_a_zone_load_does_not_grow_with_the_zip[plain, snapshot]`**: A is `import zoneinfo,
   importlib.resources`. B is A plus `zoneinfo.ZoneInfo("Europe/Paris")`. C is B plus
   `zoneinfo.ZoneInfo("Asia/Tokyo")`. B − A is at most **20 M** plain (on both zips) and
   **15 M** on the snapshot. C − B is at most **2 M**. Plain, the slope of B − A is at most
   **1,000** per member. Seen failing first: today 255.7 M plain and 205.6 M on the snapshot.
5. **`test_resources_read_as_zipfile_reads_them[plain, snapshot]`**, on the artifact zip:
   - `type(importlib.resources.files("tzdata")).__name__ == "ZipDirectoryPath"`;
   - for every member under `tzdata/zoneinfo/`, `files("tzdata").joinpath(rel).read_bytes()`
     equals `zipfile.ZipFile(zip).read(name)`;
   - for every directory of `tzdata` and `pandas`, including implied ones, the sorted
     `iterdir()` names equal `zipfile.Path`'s;
   - `is_file`, `is_dir`, `exists`, `name` and `str()` equal `zipfile.Path`'s for each entry
     and for a missing name; `read_text(encoding="utf-8")` of `zoneinfo/tzdata.zi` equals;
     `importlib.resources.read_binary("tzdata.zoneinfo", "UTC")` equals;
   - the error types match `zipfile.Path`'s: `iterdir` on a file, `open` on a missing name,
     `open` on a directory, `read_bytes` on a missing name, `open("w")`.

   Seen failing first: the type is `Path` (from `zipfile`) today.
6. **`test_metadata_answers_from_the_zips_directory[plain, snapshot]`**:
   - snapshot: with A = `import importlib.metadata` and B = A plus a missing `version("nope")`,
     B − A is at most **20 M** (today 218.9 M);
   - plain: the slope of that difference is at most **6,000** per member (today 132,458);
   - plain, on `small.zip`: for each `.dist-info` folder in the zip (the judge's two, and spec
     033's if it has landed), the distribution `importlib.metadata` finds equals
     `PathDistribution(zipfile.Path(zip, folder + "/"))`. That means the same `version`,
     `metadata` items, `entry_points`, `files` (`None` without `RECORD`, the same list with
     it), `requires` and `read_text("METADATA")`. The set of `(Name, version)` over
     `distributions()` equals the set built that way. `entry_points(group=…)` for the judge's
     group equals.
   - snapshot, on the artifact zip: the same comparison for whatever distributions the zip
     holds (none before 033, five after).

   Seen failing first: the miss costs 218.9 M today.
7. **`test_the_pandas_tz_job_matches_native[plain, snapshot]`**: the new golden job
   `tests/jobs/pandas_tz.py` calls `zoneinfo.reset_tzpath(to=[])` so native and guest both use
   the `tzdata` package. It prints its versions line, then Paris's offset in July and a
   two-day Tokyo range's offsets. Its output equals `pandas_tz.expected` on both binaries,
   and the golden reproduces under the pinned oracle
   (`test_goldens_reproduce_under_the_pinned_oracle`). On the snapshot, the job's fuel minus
   that of `import pandas, zoneinfo, importlib.resources` is at most **60 M** (today 961.0 M).
   Seen failing first on the bound.
8. **`test_a_reread_after_invalidate_caches_is_the_fast_read`**, plain: X is `import importlib;
   importlib.invalidate_caches(); import json.tool`, and Y is `import json.tool`. The slope of
   X − Y is at most **30,000** per member, and `served` says `"fast"` after the re-read. Seen
   failing first: today about 77,842.
9. **The rest of the judge, and the set.**
   - Every existing check passes, spec 033's included if it has landed. Lost 0.
   - A full build from pins in a clean clone gives a zip byte for byte today's (or 033's, if it
     has landed). `python.wasm` and the snapshot change.
   - The same bytes from every host: the release dry run's rebuild jobs pass (spec 012). The
     snapshot rebuilds the same, since phase 1 does the same work on every host.
   - `uv run pytest` is green with `--accept "<reason>" --accept-judge "<the new checks, job and
     helper>" --accept-growth "<the measured account>"`. The account names the plain binary's
     `bytes` growth (about 20 KB), any snapshot `bytes` change, and each snapshot fuel growth
     above the tolerance with its cause. Decision 10's limits apply: a snapshot `pass` growth
     above 0.1%, or any plain fuel growth, is a finding for the build review.
   - The landing notes record, measured: plain and snapshot `-c pass` and `import pandas`;
     checks 2, 4, 6, 7 and 8's numbers and slopes; the install point; the two modules'
     marshalled sizes.
   - A release dry run passes every job.

## Questions for the owner

None open here. The two choices the memo left to the owner are drafted with its recommended
answers and recorded as questions 59 (our own `Traversable` for resources in the zip, Decision 6)
and 60 (run-time replacement as a recipe, not a carried patch, Decision 8) in
`../questions-for-the-owner.md`. Spec 033 landing first is question 57's answer. The order
before spec 023 (Decision 12) follows the roadmap's "before the zip grows". Nothing waits on any
of them; an answer otherwise changes Decisions 6, 8 or 12 before the build.

## Landing notes

Not built.
