# 035 — The zip's directory is read once

- **Status:** **revised against its build review; awaiting the reviewer's confirmation**
  (2026-10-18; the build review's F1 to F5 answered in the landing notes' last part, "Revised
  against the build review"; F3 fixed in code, so the set was rebuilt from pins and judged
  again). **Spec 051's callback scan binds this build** (051, Decision 4a; written in when 051 landed): `test_callbacks_have_the_types_cpython_calls` is green, and a mismatch it finds is fixed by a carried patch or an upstream release, never by an exclusion. **Spec 051 lands before this one** (the lane's order, 2026-10-18): 051 changes every `.pyc` in the zip (each code object's `co_filename` carries `/usr/local/lib/python315.zip/`) and grows plain fuel (`-c pass` +34,790). So this specification's absolute byte and fuel baselines (criterion 9, Decision 10) are restated against 051's set, and that difference is 051's, not a finding. Its per-member directory figures hold: the zip's member list (names, order, dates, compression, modes) is unchanged. drafted 2026-10-17; revised the same day against its pre-build review
  (`../reviews/035-the-zips-directory-is-read-once-spec-2026-10-17.md`), all eight findings
  written in (its Disposition); its confirmation passed it for build with one condition (C1, the
  second zone's figure) and two clarifications (C2, C3), written in. It changes the build recipe and how the interpreter starts, so it
  was reviewed before it is built (constitution §5.6). It is build-class: it touches `recipes/`
  and `scripts/` (§5.7).
- **Owner:** Clay Gendron
- **Kind:** the build recipe (`recipes/reactor_main.c`, two new recipe modules
  `recipes/zip_directory.py` and `recipes/zip_resources.py`, `scripts/freeze_bootstrap.py`,
  `scripts/steps/60_link.sh`), judge additions (a new check file, a zip-making helper, the
  `guest` fixture's `stdlib=`, a golden job, unit checks), `README.md`, `CHANGELOG.md`, an
  upstream courtesy-issue draft.
- **Depends on:** 003 (the reactor, `_reactor`, step 60), 008 (fuel counts the guest), 012 (the
  same bytes from any host), 002 (the judge and its ratchet). All landed. It does not depend on
  033 or 023; Decision 12 orders them.
- **Research it stands on:** `../research/2026-10-17-the-zips-directory-is-read-once.md` and its
  evidence folder (`scripts/candidates.py` holds the prototypes; `outputs/derived.txt` every
  derived number). Findings 1 to 5 and its design section are this specification's base. The
  pre-build review's runs (its "Ran" list): both install points on host CPython 3.15.0, the
  reader on 13 ordinary and hostile zips, and the reader's and the metadata split's fuel in the
  guest. The owner's decision 44 (`../decisions.md`, "43–48": cut the zip's per-member cost
  first, before tier A grows the zip). Questions 59 and 60 (`../questions-for-the-owner.md`),
  drafted here with the recommended answers.

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
  Spec 033 keeps `METADATA` in the zip, so these queries become common. 033 measured a first
  `version("numpy")` at about 361 M on the snapshot: about 219 M of directory scan and about
  142 M of reading and parsing `METADATA` (its Decision 7).
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
   and 3 share one `Traversable` and one member reader. The whole is about 400 lines of Python,
   60 of C and a judge file; one builder builds it, in the review's order: part 1 with checks 1,
   2, 3 and 8; then part 2 with checks 4, 5 and 7; then part 3 with check 6. Each step is green
   before the next.

   One split is decided now, in case it is needed. If neither install point (Decisions 3 and 4)
   serves the start, the builder stops after two attempts on each (AGENTS.md rule 7) and records
   why in the landing notes. Parts 2 and 3 then become their own specification. They need no
   early install: they work installed right after `Py_InitializeFromConfig`. Part 1 waits for a
   new memo. Nothing half-built lands (§5.4). Both points ran on host CPython 3.15.0 in the
   review, so this is unlikely.

2. **The directory reader (part 1).** A frozen module of ours, `_zip_directory`, from
   `recipes/zip_directory.py`. Its `read_directory(archive)` returns **the same dict** as
   zipimport's `_read_directory(archive)`: the same keys, the same toc tuples, **in the same
   order**. It does one read of the central directory and one `_struct` unpack per member (24,798
   fuel per member, EXECUTED by the review from this text). It imports only `_io`, `_struct` and
   `zipimport` (and through it `_frozen_importlib_external`).
   - **The plain case.** It opens the archive with `_io.open_code(archive)`, as zipimport does,
     so an embedder's open-code hook sees the same calls (`Lib/zipimport.py:297`, READ). It reads
     the same tail window zipimport reads (65,535 + 22 + 56 + 20 bytes). It finds the last end
     record (`PK\x05\x06`), applies zipimport's three offset checks, reads `cd_size` bytes at the
     directory's start, and walks `n` entries. Per entry it keeps zipimport's fields: `(path,
     compress, data_size, file_size, file_offset + arc_offset, time, date, crc)`. `path` equals
     `_bootstrap_external._path_join(archive, name)`. For a name that is non-empty and does not
     end in `/` it is `head + name`, with `head = _path_join(archive, "x")[:-1]` computed once;
     that equals `_path_join`'s answer for every archive, `""` and `"/"` included (READ: the POSIX
     `_path_join`). Any other name calls `_path_join` itself. Then it adds the implied
     directories with zipimport's own loop, so the order matches.
   - **Everything else goes to zipimport's reader.** The module keeps the original as the module
     global `stock_read_directory`, and `read_directory` looks it up by that name at each call
     (never bound as a default argument), so a unit check can replace it. It calls it, and returns
     its result or lets its error rise, when any of these holds: the tail holds `PK\x06\x06` (a
     Zip64 end record) anywhere; no end record; an end-record field at its maximum (`0xFFFF` or
     `0xFFFFFFFF`); any entry field at `0xFFFFFFFF` (a Zip64 extra); a name without the UTF-8
     flag that is not ASCII (cp437); an entry past the bytes read; a bad signature; a
     local-header offset past the directory's; another `PK\x01\x02` after `n` entries; or any
     exception, `MemoryError` included. So Zip64, cp437 names and every error are upstream's,
     with upstream's messages. A Zip64 zip, or a zip whose tail happens to hold `PK\x06\x06`,
     costs one cheap probe more than today, then today's cost. The review checked this routing
     on 13 zips, ordinary and hostile (EXECUTED, its `odd.txt`).
   - **What served each read.** The module keeps `served`, a dict from archive to `"fast"` or
     `"stock"`, set at each read. It is one store per read. It lets a check see which path ran.
   - It is used only where `zipimport.path_sep == "/"`, which is always true in the guest.
     `install()` leaves zipimport untouched otherwise.

3. **Where it goes in: the interpreter's two-phase start (install point A).** The first read
   happens inside `Py_InitializeFromConfig`, when `encodings` is imported from the zip (EXECUTED
   by the memo, finding 1). So `recipes/reactor_main.c` starts the interpreter in two phases:
   - `config._init_main = 0`, then `Py_InitializeFromConfig(&config)`. This runs the core phase
     only: builtin and frozen importers work; nothing has touched the zip.
   - `PySys_SetObject("_stdlib_dir", <the zip's path>)`, the value the main phase sets anyway.
     Without it, the modules phase 1 imports (`zipimport`, `_frozen_importlib_external`) keep no
     `__file__`, because `FrozenImporter._resolve_filename` needs `sys._stdlib_dir`, which only
     the main phase sets (`Python/sysmodule.c:4208`, `Python/pylifecycle.c:1378`, READ by the
     review; EXECUTED by it: with the call, both attributes and both `loader_state`s equal a
     one-phase start's).
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

   Why it works (READ, `build/Python-3.15.0/`): `PyConfig._init_main`
   (`Include/cpython/initconfig.h:230`) and `_Py_InitializeMain`
   (`Include/cpython/pylifecycle.h:29`) exist in 3.15. `Py_InitializeFromConfig` skips
   `pyinit_main` when `_init_main` is 0 (`Python/pylifecycle.c:1631`). `zipimport` and
   `_frozen_importlib_external` are in the bootstrap frozen table, which is always searched
   (`Python/frozen.c:70`, `Python/import.c:3126`). When the main phase runs
   `_install_external_importers` and `init_zipimport`, it imports both modules by name and finds
   the ones phase 1 left in `sys.modules`, with our function in place. **EXECUTED by the review
   on host CPython 3.15.0, the build's own source** (its `two_phase.txt`): between the phases
   zipimport is not loaded; `import _zip_directory` through `PyImport_FrozenModules` and
   `install()` work; afterwards `served == {zip: "fast"}`, `encodings` came from a
   `zipimporter`, and the cached dict equals the stock reader's. Check 1 is still the gate on
   wasm.

   **The API's history.** Both names are private. `_Py_InitializeMain()` was removed in 3.14
   (gh-129033, `Doc/whatsnew/3.14.rst:3071`) and restored in 3.15 (gh-142417,
   `Doc/whatsnew/3.15.rst:2630`, READ by the review). The C-API docs say the core phase "can be
   modified or even be removed anytime". So: **a re-pinned CPython that lacks
   `_Py_InitializeMain` or `PyConfig._init_main` uses install point B at once**, without the two
   strikes on A, and the re-pin's memo records it. Such a re-pin fails at the link, loudly, before
   any check runs.

4. **Install point B: a C audit hook.** Decided now, so the builder does not stop to ask (§5.2).
   It is used only if check 1 fails twice on point A on wasm, or at once on a re-pin as Decision 3
   says. The landing notes record why.
   - Before `Py_InitializeFromConfig`, `reactor_main.c` calls
     `PySys_AddAuditHook(zip_hook, NULL)`. The C API documents it as safe before initialization,
     and runtime initialization keeps it (READ by the review: `_PyRuntimeState_Init` keeps
     `audit_hooks.head`). Initialization is then one phase, as today, and `sys._stdlib_dir` is set
     as today.
   - `zip_hook` returns 0 at once unless the event is `"import"`. On an `"import"` event it looks
     for `zipimport` in `sys.modules`, fully executed: its `__spec__._initializing` is false.
     (`init_zipimport` imports zipimport before any zip is read. Each import raises `"import"`
     before its finders run: `_find_and_load_unlocked` audits, then calls `_find_spec`, READ in
     `Lib/importlib/_bootstrap.py`.) The first time both hold, the hook sets a static flag,
     imports `_zip_directory` and calls `install()`. On failure it prints and aborts. The flag
     also stops the import inside `install()` from re-entering. That moment is the import of
     `encodings`, before the first `zipimporter` is made (EXECUTED by the review on host 3.15.0,
     its `audit_hook.txt`: 7 import events before the install, then `served` says `"fast"`).
   - **It returns 0 with no exception set, always.** Every lookup that fails is cleared with
     `PyErr_Clear()`. `sys_audit_tstate` restores the caller's pending exception only when every
     hook succeeds (READ by the review).
   - **Its cost, per event.** Once any hook exists, CPython builds an argument tuple for every
     audited event (imports, opens, `marshal.loads`, `compile`, `exec`) and calls the hook, which
     returns at the flag. INFERRED: about 1,000 to 3,000 fuel per event (one `Py_BuildValue`
     tuple, one C call, one decref). The review counted 654 events for importing `json`,
     `zoneinfo`, `importlib.resources` and `email.parser` (EXECUTED, host), so about 0.7 M to 2 M
     for such a program. If B serves, the builder measures the cost per event: plain `import
     pandas` against today's, plus the reader's measured saving (check 2's slope times the
     members), divided by the events a scratch build counts. The landing notes give it. More than
     5,000 fuel per event is a finding for the build review.
   - The guest cannot see or remove the hook. It opens no channel (§4.4, §4.15).

5. **How the modules are frozen and found.** Both new modules are compiled at build time, as
   `_reactor` is.
   - `scripts/freeze_bootstrap.py` takes two optional arguments, the C array's name and the code
     object's file name: `freeze_bootstrap.py <src.py> <out.h> [<NAME> <filename>]`. The header
     defines `<NAME>` and `<NAME>_MAGIC`. The defaults, `REACTOR_BOOTSTRAP` and `<reactor>`, give
     today's header byte for byte. The work splits into two functions outside the version gate:
     `compile_module(src, filename)` (the `compile` and `marshal.dumps`) and `render(data, magic,
     name, source)` (the header text). `main()` keeps the gate (the guest's version,
     `PYTHONHASHSEED=0`).
   - Step 60 runs it twice more: `recipes/zip_directory.py` → `$L/zip_directory.h`
     (`ZIP_DIRECTORY`, `<frozen _zip_directory>`), and `recipes/zip_resources.py` →
     `$L/zip_resources.h` (`ZIP_RESOURCES`, `<frozen _zip_resources>`). The file names follow
     CPython's frozen modules, so tracebacks read like theirs.
   - `reactor_main.c` lists the two in a static `struct _frozen` table and sets
     `PyImport_FrozenModules` to it before `Py_InitializeFromConfig`. That is CPython's public
     hook for an embedder's frozen modules (`Include/cpython/import.h:30`). They are searched
     after the bootstrap table, so they cannot shadow `zipimport` (READ, `Python/import.c:3126`).
     So `import _zip_directory` works in phase 1, and `import _zip_resources` works lazily, on
     first use, through the frozen importer. Their `__spec__.origin` is `"frozen"`. With
     `sys._stdlib_dir` set (Decision 3), their `__file__` reads
     `/usr/local/lib/python315.zip/_zip_directory.py` and `…/_zip_resources.py`, as a frozen
     stdlib module's does; no such member exists, as for CPython's own frozen modules.
   - `_reactor` is loaded as today. Moving it is not this specification's business.
   - Nothing is added to the zip. **The zip's bytes do not change**, and step 70 is untouched.

6. **The resource reader (part 2).** `install()` sets `zipimport.zipimporter.get_resource_reader`
   to a small function in `_zip_directory`. It imports `_zip_resources` on first use and returns
   `ZipDirectoryReader(self, fullname)`. As built, `_zip_resources` imports `io`, `os`,
   `pathlib`, `posixpath`, `sys`, `zipimport` and `zlib`, and imports `importlib.resources.abc`
   only when `ZipDirectoryReader` is first made, so a metadata query does not pay for
   `importlib.resources` and `tempfile` (the landing notes, "One design change"; the draft said
   it imports `importlib.resources.abc` at once). It imports `zipfile` only on the fallback below.
   - **`ZipDirectoryReader`** subclasses `TraversableResources`, made on first access through the
     module's `__getattr__` and kept. Its root prefix is computed as
     `importlib.resources.readers.ZipReader` computes it: the loader's prefix, plus the package's
     last name and `/` for a package. `files()` returns that root. `is_resource(path)` answers as
     `ZipReader.is_resource` does. `open_resource` and `resource_path` are the base class's
     (`FileNotFoundError` for a missing name; `resource_path` always raises it, as for
     `ZipReader`).
   - **`ZipDirectoryPath`** satisfies the `Traversable` protocol (a runtime-checkable one) as
     `zipfile.Path` does, without subclassing it (as built; the draft said it subclasses
     `Traversable`; the landing notes, "One design change"). It holds the loader and `at`, a name in the
     archive (`""` for the root, `a/b/` for a directory, `a/b/c` for a file). It answers names
     from `loader._get_files()`, zipimport's cached dict, called `files` below. It never touches
     `zipimport._zip_directory_cache` (CPython #121342, READ: direct use broke when 3.13 made
     invalidation lazy). `_get_files()` refills the dict after `invalidate_caches()`.
   - **Its exact definitions**, those of `zipfile.Path` in 3.15 (`Lib/zipfile/_path/__init__.py`,
     READ; EXECUTED by the review, its `trav.txt`), with zipimport's dict as the name set:
     - `is_dir()` is `not at or at.endswith("/")`, purely from the name, as `zipfile.Path`'s is.
       So `joinpath("missing/")` is a directory that does not exist.
     - `exists()` is `at in files`. So the root does not "exist", as for `zipfile.Path`.
     - `is_file()` is `exists() and not is_dir()`.
     - `joinpath(*parts)` is `resolve_dir(posixpath.join(at, *map(os.fspath, parts)))`, where
       `resolve_dir(name)` gives `name + "/"` only when `name` is not in `files` and
       `name + "/"` is. So a file `a` wins over a directory `a/`. `/` is `joinpath`. No part is
       dropped or normalized: `//lead.py` stays `//lead.py`.
     - `name` is `PurePosixPath(at).name`, or the archive's file name for the root. `suffix`,
       `suffixes` and `stem` come from `PurePosixPath(at)`, or the archive's path for the root.
     - `parent` is the archive's folder (`pathlib.Path(archive).parent`) for the root; otherwise
       `posixpath.dirname(at.rstrip("/"))`, plus `/` when not empty.
     - `str()` is `posixpath.join(archive, at)`. `==` holds for the same class, archive and
       `at`, and is `NotImplemented` for any other type (so numpy's `locate_file("numpy") !=
       NUMPY_ROOT` stays true, as spec 033 recorded); `hash` is on (archive, `at`).
     - `iterdir()` raises `ValueError("Can't listdir a file")` when not `is_dir()`. Otherwise it
       yields the children from a children map: directory name to its children, in the dict's
       order. The map is built in one pass over the names the first time `iterdir()` lists any
       directory of that archive. It is kept with the dict object it came from and rebuilt when
       `_get_files()` returns another. Only `iterdir()` builds it. Listing order is not promised,
       as for `zipfile.Path`; the checks compare sorted names.
     - `open(mode="r", *args, pwd=None, **kwargs)`: first, a directory raises `IsADirectoryError`. Then
       `mode[0] == "r"` reads, and a missing name raises `FileNotFoundError`. Any other first
       letter raises `ValueError`, as the read-only `ZipFile` behind `zipfile.Path` does (`"w"`
       through `_writecheck`; `"x"`, `"a"` and `"br"` through `ZipFile.open`'s mode test). With
       `"b"` in the mode the bytes come back as a binary stream, and any extra arguments raise
       `ValueError("encoding args invalid for binary operation")`. Otherwise (`"r"`, `"rt"`,
       `"r+"`) a `TextIOWrapper` with `io.text_encoding`'s default encoding, as
       `zipfile.Path.open` builds it. A `pwd` other than `None` is `zipfile.Path.open`'s keyword:
       that read goes to the `zipfile` fallback below with it (added against the build review,
       its finding 3).
     - `read_bytes` and `read_text` go through `open`, as `Traversable`'s do.
   - **The bytes: a strict, bounded fast path; anything else is upstream's `zipfile`.** This
     reader serves every `zipimporter`, so also a zip a guest puts on `sys.path`. Such a zip is
     untrusted. Today its resources are read through `zipfile`, which checks each CRC-32, the
     local header's name, overlapped entries and encryption, reads bzip2 and LZMA, and streams.
     `zipimporter.get_data` does none of that and decompresses a whole member at once (READ by the
     review, `Lib/zipimport.py:632-679`). So the fast path does not use `get_data`. It uses a
     member reader of ours, and serves a member only when all of these hold:
     - the toc entry's method is stored (0) or deflate (8), and its `file_size` and `data_size`
       are each at most **1 MiB** (1,048,576 bytes);
     - the local header at the entry's offset has the right signature, the encryption bit
       (`0x1`) clear, the directory's method, and the directory's name, byte for byte, compared
       as `at.encode("utf-8")` (zipimport keeps only the decoded name, so a cp437-named member
       always goes to `zipfile`, the safe direction);
     - the archive is opened with `_io.open_code(archive)`, as zipimport opens it;
     - the data is read as `data_size` bytes and, for deflate, inflated by
       `zlib.decompressobj(-15).decompress(raw, file_size + 1)`, so no read makes more than
       1 MiB + 1 bytes; the result is exactly `file_size` bytes, the stream is complete, and
       `zlib.crc32` equals the entry's CRC.

     Any other member, any failed test, any exception and any `pwd` open through
     `zipfile.Path(loader.archive, at).open(mode, *args, pwd=pwd, **kwargs)`: upstream's object, with its
     streaming, its checks and its errors, for that one read. It pays the archive's parse only in
     that rare case. Overlap is not tested on the fast path; it cannot amplify a read, because
     each read is bounded at 1 MiB. This is Decision 2's rule again: anything odd is upstream's.
     Today's stdlib zip is all deflate with no flag bits, and its largest member is 620,623 bytes
     (`pydoc_data/topics.pyc`), its largest `tzdata` file 104,917 (EXECUTED by the review), so
     every member of it takes the fast path.
   - **Accepted differences from `zipfile.Path`**, which the README names (Design):
     - **Not provided:** `zipfile.Path`'s own attributes (`root`, `at`, `filename`) and its
       `glob`, `rglob`, `match`, `relative_to` and `is_symlink`. They are not part of
       `Traversable`. Code that needs them breaks; code using `Traversable`, and
       `importlib.resources.as_file`, works as before. `as_file` still copies the resource to a
       temporary file, so it still needs a writable temporary folder, as with `zipfile.Path`.
     - **Implied directories for odd names:** zipimport implies `a//` for a member `a//b.py`,
       where `zipfile` implies `a/` (READ: both loops; EXECUTED by the review). A name with `//`
       or a leading `/` lists differently.
     - **Duplicates and the empty name:** `zipfile.Path.iterdir()` repeats a duplicated name and
       yields an empty-named member under the archive's file name; the dict holds each name once
       and lists no empty name.
     - **Equality:** two `files()` calls give equal paths here, where `zipfile.Path` gives
       unequal ones (each holds its own `ZipFile`).
     - **Freshness:** answers reflect zipimport's view of the zip, refreshed by
       `importlib.invalidate_caches()`, as imports do. A zip on `sys.path` rewritten in place
       keeps its old listing until then (a new member is `FileNotFoundError`), and Decision 7's
       metadata its old distributions (a moved `METADATA` raises `MetadataNotFound`, where
       upstream, re-reading the archive, finds the new one). The bytes are always current: a
       stale entry fails the member reader's checks and goes to `zipfile`. (Written in against
       the build review, its finding 2.)
   - Namespace packages inside a zip keep the stock `NamespaceReader` path (it builds its own
     `zipfile.Path`). No package in the zip needs it.
   - This is question 59's recommended answer, as its wording now says: our own `Traversable`
     for every zip on the import path; the same bytes and listings for the runtime's zip; for
     any other zip, upstream's reader wherever a member is not plain and small.

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
     `self.joinpath` to the root `ZipDirectoryPath`'s `joinpath`, and returns upstream's own
     expression over zipimport's keys: `dict.fromkeys(name.split("/", 1)[0] for name in
     loader._get_files())`. The order is upstream's: members first; the implied directories that
     follow add no new first part. It does not build the children map, which costs 10,944 fuel
     per member against the split's 4,608 (EXECUTED by the review, its `children.txt`). Any
     other root (a zip not on `sys.path`, a zip with a prefix) gets upstream's `zip_children`,
     kept as `stock_zip_children`. A zip on the import path is then as current as zipimport's
     view of it, which `invalidate_caches()` refreshes for both.
   - **It works with spec 033's members.** `PathDistribution` reads `METADATA` and
     `entry_points.txt` through our path's `joinpath(…).read_text(encoding="utf-8")`, so through
     Decision 6's checked member reader. A missing `RECORD` gives `None`. `str()` of a
     `.dist-info` folder equals `zipfile.Path`'s (it ends in `/`), so `_normalized_name` takes
     the same branch. `locate_file` uses `parent` and `/`. Check 6 compares every answer with
     upstream's objects on the same zip.
   - **What it recovers, against spec 033's account.** It recovers the directory scan, about
     219 M on the snapshot. It does not recover the reading and parsing of `METADATA` (033's
     about 142 M, and most of `import numpy.testing`'s +136 M): that is `email`'s parse and its
     imports, which this specification does not replace. The builder measures `version("numpy")`
     and `import numpy.testing` on the snapshot with 033 in, as 033 asks, and records what
     remains in the landing notes.

8. **A recipe, not a patch (question 60, the recommended answer).** Three stdlib functions are
   replaced at run time: zipimport's directory reader, `zipimporter.get_resource_reader`, and
   `importlib.metadata`'s zip search (through `PathFinder.find_distributions`). No upstream file
   changes, and every pinned tree still equals its tarball plus the recorded patches (spec 020).
   The rule that keeps it honest: each replacement gives upstream's results, or hands the case
   to upstream's own code, and a judge check compares them on every case named in Acceptance. A
   carried patch would stay carried for good: upstream builds `_struct` outside the bootstrap,
   so zipimport cannot use it (memo, finding 4). The memo's courtesy issue is drafted for the
   owner to send, to python/importlib_resources: "`ZipReader.files()` parses the archive on every
   call; zipimport's directory already has it"
   (`context/upstream/16-importlib-resources-zip-directory/issue.md`; folder `4-` was taken, the
   landing notes). Nothing here waits on it.

9. **What a guest sees.** `import _zip_directory` and `import _zip_resources` work, as
   `import _reactor` does. `zipimport._read_directory`,
   `zipimport.zipimporter.get_resource_reader` and `PathFinder.find_distributions` are our
   functions. `importlib.resources.files(pkg)` for a package in a zip on `sys.path` is a
   `ZipDirectoryPath`, not a `zipfile.Path`, with Decision 6's accepted differences.
   `importlib.metadata` gives the same answers. Every import, every byte read, `pkgutil` (which
   reads zipimport's dict directly), `zipimport.__file__` and every golden output are unchanged.
   The `-V` banner is unchanged. The README says what changed (Design).

10. **What it costs and saves, so a fall can be told from a regression.** Today's numbers are
    EXECUTED by the memo, and re-run while drafting with `wasi_python.run` on `build/out`
    (`python.wasm` `4befe9de…`, `python-snapshot.wasm` `c7302cfd…`, `python-stdlib.zip`
    `1add57e4…`, the memo's set). The "after" numbers are INFERRED from the memo's prototypes and
    the review's measurement of this text's reader.

    | what | today | after (INFERRED) | bound |
    |---|---|---|---|
    | plain `-c pass` slope | 79,077 per member (the review, judge's driver) | about 26,700: the reader's 24,798 plus 1,931 of the start's other per-member work | ≤ 30,000 per member (check 2) |
    | plain `-c pass`, 1,751 members (1,758 with 033) | 241.8 M | about 150 M | |
    | plain `-c pass`, about 6,630 members | about 619 M (linear) | about 280 M | |
    | snapshot `-c pass` | 81.9 M | 81.9 M | the ratchet (check 9) |
    | first zone after `import zoneinfo, importlib.resources`, snapshot | 205.6 M | about 7 M plus `_zip_resources`' import | ≤ 15 M (check 4) |
    | the same, plain | 255.7 M | 11 M to 14 M plus that import | ≤ 20 M on both zips; slope ≤ 1,000 per member |
    | a second zone | about 182 M | about 1.35 M (mostly importing `tzdata.zoneinfo.Asia`) | ≤ 2 M |
    | metadata miss after `import importlib.metadata`, snapshot | 218.9 M | about 10 M plus that import | ≤ 20 M (check 6) |
    | the same, plain, slope | 132,458 per member | about 4,600 (the split's, `children.txt`; the memo's 4,472 was the same split) | ≤ 6,000 per member |
    | pandas time-zone job, snapshot, after `import pandas, zoneinfo, importlib.resources` | 961.0 M | about 29 M | ≤ 60 M (check 7) |
    | `invalidate_caches()` then an import, plain, slope | 77,842 per member | about 26,700 | ≤ 30,000 per member (check 8) |

    The drafting runs: snapshot `pass` 81,916,308; `import zoneinfo, importlib.resources`
    101,895,320, then `ZoneInfo('Europe/Paris')` 307,505,192; `import importlib.metadata`
    117,387,162, then a missing `version('nope')` 336,264,649; `import pandas, zoneinfo,
    importlib.resources` 101,998,294, then the job 1,063,016,795. Plain `pass` 241,815,784;
    `import zoneinfo, importlib.resources` 614,592,426, then Paris 870,317,283. The invalidate
    slope is the memo's (671.7 M − 262.8 M) over (7,004 − 1,751) members. The baselines import
    `importlib.resources` and `importlib.metadata` first because those imports cost about 20 M
    and 35 M on the snapshot and are not the reader's work. The lazy import of `_zip_resources`
    (unmarshal and class creation) is inside checks 4 and 6 and was not measured; the margins
    (7.3 M and 9.7 M measured against 15 M and 20 M) cover it (INFERRED), and the landing notes
    give it.

    **The margins.** Check 2's bound leaves about 11% over the expected 26,700, enough for a
    count that repeats to parts in ten million. Check 6's leaves about 30% over 4,600.

    **The ratchet.** Fuel falls on every plain check, by about 92 M each (more on checks that
    read resources). A fall is not growth; the ratchet records it. Snapshot checks move only
    where they read resources, query metadata or invalidate caches. Elsewhere they may move by
    a few thousand fuel: one more module in the heap at start (`_zip_directory`; `_zip_resources`
    loads only on use). A growth above the 0.01% tolerance is accepted with its measured reason.
    A snapshot `-c pass` that grows by more than 0.1%, or any plain check that grows, is a
    finding for the build review, not a reason to accept.

    **The artifact set.** `python.wasm` grows by the two frozen modules and the C table, about
    20 KB (INFERRED; the review's marshalled `_zip_directory` is 4,353 bytes, EXECUTED; a `bytes`
    growth the accept names). The snapshot changes. The zip does not change, byte for byte.
    `MANIFEST` gains `recipe` lines for the two new recipe files, and the lines for
    `recipes/reactor_main.c`, `scripts/freeze_bootstrap.py` and `scripts/steps/60_link.sh`
    change. `SHA256SUMS` changes for both binaries and `MANIFEST`.

11. **The checks** are listed in Acceptance. They live in a new file,
    `tests/checks/test_v1_3_the_zips_directory.py`, goal v1.3: constitution §2.3, "every
    compiled-in package imports and works", here the stdlib's own import and resource
    machinery. They run on the judge's driver (`tests/harness/guest.py`), which answers random
    and the clock itself, so fuel repeats to a few parts in ten million. A bound's slack is for
    the design, not for noise.
    - **The fixture.** The `guest` fixture in `tests/checks/conftest.py` passes
      `stdlib=d / "python-stdlib.zip"` and then `**kw`, so a check cannot name another zip today
      (a `TypeError`, READ by the review). It gains a `stdlib=` keyword, defaulting to the
      artifact zip, which checks 2, 3, 4, 6 and 8 set to `small.zip` or `padded.zip`. Every
      existing caller is unchanged.
    - **The zips.** A new helper, `tests/harness/zips.py`, makes them on the host under
      `build/harness`, once per session:
      - `small.zip`: a copy of the artifact zip, opened in append mode, plus two made-up
        distributions (`judge_meta_a-1.0.dist-info/METADATA`; `judge_meta_b-2.0.dist-info/` with
        `METADATA`, `entry_points.txt` and a `RECORD`). Append mode keeps every existing member's
        bytes, so imports from it cost what they cost from the artifact zip. The names cannot
        clash with spec 033's.
      - `padded.zip`: `small.zip`'s members plus a copy of each artifact member under `pad1/`,
        `pad2/` and `pad3/`, as the memo's `make_zips.py` does, added in append mode at zlib
        level 1. Nothing imports from `pad*/`, and a member's compression does not change the
        directory's cost (memo, finding 1). Slopes use each zip's real member count.
      - the odd zips of checks 3 and 5. The Zip64 zip is written with `zipfile`'s
        `ZIP64_LIMIT` and `ZIP_FILECOUNT_LIMIT` lowered for the write, since `zipfile` writes no
        Zip64 record for a small zip (the review's `odd.py`). The cp437 name is patched into the
        bytes by hand. Each is checked on the host for the feature it must have before any guest
        runs. A check never passes on a zip that lacks it.

    The snapshot runs only beside its own zip (spec 003), so slopes are plain-only, and the
    snapshot's bounds are on the artifact zip.

12. **Ordering with other build-class work** (§5.7: one build-class specification in flight; a
    change to the build recipe overlaps no other). Spec 033, now confirmed for build, builds
    first (question 57). This specification builds next, and spec 023 (matplotlib M1) after it.
    Why before 023: 023 adds about 610 zip members, the largest growth planned, and the roadmap's
    milestone 4 places this cut "before the zip grows (decision 44)". If 023 is already being
    built when this one is confirmed, this one waits; its checks are slopes and differences, so
    they hold on either zip.
    - **With 033:** no file overlaps (033 changes step 70, `make_stdlib_zip.py` and the `ctypes`
      stand-in, whose `ctypes/_types.py` makes the zip 1,758 members; this one changes step 60
      and the reactor). 033's `test_packages_carry_their_metadata` then runs through part 3 and
      must still pass. Part 3 recovers the scan in 033's metadata account, not the `METADATA`
      parse (Decision 7).
    - **With 023:** both change step 60. Whichever builds second rebases onto the other's step 60.
      If this one lands first, 023's Decision 6 plain-start figures were stated at 76,490 fuel
      per member. Its builder re-derives them at this one's measured slope (about 610 × 26,700,
      about +16 M rather than +47 M) and records that in 023's landing notes. Otherwise 023's
      "outside these by more than a tenth" rule would flag a smaller growth. 023's choice to
      pack `mpl-data` as one inner archive stays right: its files are read from a grant, not
      through `importlib.resources`. Only its numbers change.
    - Tier A waits for this one (decision 44).

## Intent

A zip's directory is parsed once per process, by a reader three times cheaper than today's. Every
later use (imports, resource reads, metadata, a re-read after invalidation) answers from that
one parse. The answers stay upstream's, byte for byte, and anything odd goes to upstream's code.

## Design

| file | change |
|---|---|
| `recipes/zip_directory.py` | new: `read_directory`, `stock_read_directory`, `served`, `install()`, the `get_resource_reader` and `find_distributions` wrappers (Decisions 2, 6, 7) |
| `recipes/zip_resources.py` | new: `ZipDirectoryReader` (made on first use), `ZipDirectoryPath` (the `Traversable` protocol, not a subclass), the member reader, the children map, `zip_children`, `stock_zip_children` (Decisions 6, 7) |
| `recipes/reactor_main.c` | the two headers; the `struct _frozen` table and `PyImport_FrozenModules`; `_init_main = 0`, `sys._stdlib_dir`, the magic checks, `_zip_directory.install()`, `_Py_InitializeMain()` (Decision 3); install point B only if Decision 4 applies; the file's header comment |
| `scripts/freeze_bootstrap.py` | the optional `<NAME> <filename>` arguments; `compile_module()` and `render()` outside the version gate (Decision 5); its docstring |
| `scripts/steps/60_link.sh` | two more `freeze_bootstrap.py` runs into `$L/` (Decision 5) |
| `tests/checks/conftest.py` | the `guest` fixture's `stdlib=` keyword (Decision 11) |
| `tests/checks/test_v1_3_the_zips_directory.py` | new: checks 1 to 8 |
| `tests/harness/zips.py` | new: `small.zip`, `padded.zip` and the odd zips (Decision 11) |
| `tests/jobs/pandas_tz.py`, `tests/jobs/pandas_tz.expected`; `JOBS` in `tests/harness/jobs.py` | new golden job (check 7), its golden from the pinned oracle through `regen.py` |
| `tests/unit/test_zip_directory.py` | new: the recipe modules and the judge's zips on the host |
| `tests/unit/test_build_scripts.py` | `test_freeze_names_each_module` |
| `README.md` | the recipe paragraph names the two frozen modules; the platform paragraph says `importlib.resources.files()` on a zip gives the runtime's own `Traversable`: the same bytes and listings, upstream's reader for a member that is not plain and small or is opened with a `pwd`, and Decision 6's accepted differences (no `root`, `at`, `glob` and the rest; odd names' implied directories; duplicates and the empty name; equality across `files()` calls; freshness until `invalidate_caches()`); the speed table's plain-reactor row re-measured |
| `CHANGELOG.md` | the next unreleased section: the zip's directory is read once; resource reads and metadata no longer parse the zip |
| `context/upstream/16-importlib-resources-zip-directory/issue.md`, `context/upstream/README.md` | the courtesy issue draft and its row (Decision 8) |

Unit checks (no artifacts), each seen failing first because the module or function does not
exist. They run on the judge's host Python, which may not be 3.15 (it is 3.14.2 on the review's
machine), so none of them needs the guest's version:

- `test_the_fast_reader_matches_zipfile_on_the_host`: `recipes/zip_directory.py` loaded under a
  private name. On zips the check makes (plain members, explicit directory entries, bytes
  prepended, an archive comment), each entry's fields equal the host `zipfile`'s `ZipInfo`
  (offset plus prepended bytes, both sizes, CRC, method, DOS time and date). The implied
  directories equal the set `zipfile.Path` implies. `served` says `"fast"`. It compares with
  `zipfile`, not the host's zipimport, whose reader differs across versions.
- `test_odd_zips_go_to_the_stock_reader`: with a recording stub set as the module global
  `stock_read_directory`, a Zip64 zip, a cp437 name, a truncated directory and one entry more
  than declared each call the stub. Its result, or its exception, comes back unchanged.
  `served` says `"stock"`.
- `test_the_zip_path_answers_as_a_traversable`: `ZipDirectoryPath` over a fake loader (a dict,
  and an archive file for the member reader). It checks Decision 6's definitions against
  written-out expected values: `joinpath` with several parts, with `/`, `"UTC/"`, `"missing/"`,
  `//lead.py` and a file beside a same-named directory; `name` (the root's too), `parent`,
  `str()`, `==`; `is_file`, `is_dir`, `exists`; `iterdir` (and `ValueError` on a file); `open`
  with `"rb"`, `"r"`, `"rt"`, `"r+"`, `"w"`, `"br"`, binary with an encoding, a missing name and
  a directory. The children map is built once, only by `iterdir`, and rebuilt for a new dict.
- `test_the_member_reader_hands_odd_members_to_zipfile`: with `zipfile.Path` replaced by a
  recording stub, an LZMA member, a member over 1 MiB, a member whose CRC is wrong, an
  encrypted-flag member, a local header whose name differs, and a deflate stream that inflates
  past `file_size` each reach the stub. A plain small member does not, and its bytes are
  right.
- `test_freeze_names_each_module` (in `tests/unit/test_build_scripts.py`): `render()` on fixed
  bytes and a fixed magic writes exactly a written-out header text, `#define NAME_MAGIC …L` and
  `static const unsigned char NAME[]` included. With the defaults it writes today's
  `reactor_bootstrap.h` layout: the same name, the same comment line, rows of 24. And
  `compile_module(src, "<frozen _x>")` gives code whose `co_filename` is `<frozen _x>`, on the
  host's own Python.
- `test_the_judges_zips_have_what_they_claim`: the helper's Zip64 zip has `PK\x06\x06` and
  `0xFFFFFFFF` fields; the cp437 zip has flag bit 11 clear and a byte at or above `0x80` in a
  name; `small.zip` keeps each member of a small source zip, local entry and data, byte for byte.

## Scope

In: the above. Out:

- **A C reader, or a pre-parsed index shipped with the zip.** The memo's numbers: about 190 M
  at 6,630 members instead of about 280 M (INFERRED), at the price of a C zip parser to review,
  or a second artifact that can go stale. Snapshot calls, the default, pay nothing at start. A
  later memo may show the plain start needs it.
- **The `METADATA` parse** (Decision 7): `email`'s work, not the directory's.
- **Moving `_reactor` into the frozen table.** It works as it is.
- **Namespace packages' resources in a zip**, and **`zipfile.Path`'s extra attributes**
  (Decision 6).
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
   guest:
   - `zipimport._read_directory is _zip_directory.read_directory`;
   - `_zip_directory.served == {"/usr/local/lib/python315.zip": "fast"}` with no extra call, so
     the start's own read was ours;
   - `sys.modules["encodings"].__spec__.loader` is a `zipimporter`;
   - `zipimporter.get_resource_reader` and `PathFinder.find_distributions` are ours;
   - `_zip_directory.__spec__.origin == "frozen"`;
   - `zipimport.__file__ == "/usr/local/lib/python315.zip/zipimport.py"`, and
     `_frozen_importlib_external`'s `__spec__.loader_state.filename` is
     `/usr/local/lib/python315.zip/importlib/_bootstrap_external.py`, as a one-phase start gives
     today (Decision 3).

   Seen failing first: `ModuleNotFoundError: _zip_directory`. Built and run before parts 2 and
   3. Its landing note says which install point serves (Decisions 3 and 4).
2. **`test_a_plain_start_grows_at_most_30k_fuel_per_member`**: plain `-c pass`; the slope is at
   most **30,000**. Seen failing first: today about 79,077.
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
5. **`test_resources_read_as_zipfile_reads_them[plain, snapshot]`**:
   - on the artifact zip:
     - `type(importlib.resources.files("tzdata")).__name__ == "ZipDirectoryPath"`;
     - for every member under `tzdata/zoneinfo/`, `files("tzdata").joinpath(rel).read_bytes()`
       equals `zipfile.ZipFile(zip).read(name)`;
     - for every directory of `tzdata` and `pandas`, including implied ones, the sorted
       `iterdir()` names equal `zipfile.Path`'s;
     - `is_file`, `is_dir`, `exists`, `name` and `str()` equal `zipfile.Path`'s for each entry,
       for a missing name, and for `"zoneinfo/UTC/"` and `"missing/"`;
       `read_text(encoding="utf-8")` of `zoneinfo/tzdata.zi` equals, and so does
       `open("rt").read()` and `open("r+").read()`;
       `importlib.resources.read_binary("tzdata.zoneinfo", "UTC")` equals;
     - the error types match `zipfile.Path`'s: `iterdir` on a file, `open` on a missing name,
       `open` on a directory, `read_bytes` on a missing name, `open("w")` on a file and on a
       directory, `open("rb", encoding="utf-8")`.
   - plain, on a guest zip on `sys.path` (written into the guest's root) holding a package with
     an LZMA member, a member whose stored CRC is wrong, and a stored member of 2 MiB: through
     `importlib.resources`, the LZMA member's bytes equal `zipfile`'s, the corrupt member raises
     `zipfile.BadZipFile` as `zipfile.Path` does, and the large member read in 64 KiB chunks
     gives `zipfile`'s bytes through a `zipfile` stream (its `open("rb")` is not a `BytesIO`).

   Seen failing first: the type is `Path` (from `zipfile`) today.
6. **`test_metadata_answers_from_the_zips_directory[plain, snapshot]`**:
   - snapshot: with A = `import importlib.metadata` and B = A plus a missing `version("nope")`,
     B − A is at most **20 M** (today 218.9 M);
   - plain: the slope of that difference is at most **6,000** per member (today 132,458);
   - plain, on `small.zip`: for each `.dist-info` folder in the zip (the judge's two, and spec
     033's five), the distribution `importlib.metadata` finds equals
     `PathDistribution(zipfile.Path(zip, folder + "/"))`. That means the same `version`,
     `metadata` items, `entry_points`, `files` compared as `[(str(p), p.hash and p.hash.value,
     p.size) …]` (`None` without `RECORD`), `requires`, `origin` and `read_text("METADATA")`.
     The set of `(Name, version)` over `distributions()` equals the set built that way.
     `entry_points(group=…)` for the judge's group equals.
   - snapshot, on the artifact zip: the same comparison for the distributions the zip holds.

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
   - Every existing check passes, spec 033's included. Lost 0.
   - A full build from pins in a clean clone gives a zip byte for byte 033's. `python.wasm` and
     the snapshot change.
   - The same bytes from every host: the release dry run's rebuild jobs pass (spec 012). The
     snapshot rebuilds the same, since phase 1 does the same work on every host.
   - `uv run pytest` is green with `--accept "<reason>" --accept-judge "<the new checks, job,
     fixture keyword and helper>" --accept-growth "<the measured account>"`. The account names
     the plain binary's `bytes` growth (about 20 KB), any snapshot `bytes` change, and each
     snapshot fuel growth above the tolerance with its cause. Decision 10's limits apply: a
     snapshot `pass` growth above 0.1%, or any plain fuel growth, is a finding for the build
     review.
   - The landing notes record, measured: plain and snapshot `-c pass` and `import pandas`;
     checks 2, 4, 6, 7 and 8's numbers and slopes; the install point, and point B's cost per
     event if it serves; the two modules' marshalled sizes; `_zip_resources`' import cost; and,
     as spec 033 asks, `version("numpy")` and `import numpy.testing` on the snapshot.
   - A release dry run passes every job.

## The owner's choices

None waits on the owner. The two choices the memo left to the owner are drafted with its recommended
answers and recorded as questions 59 (our own `Traversable` for resources in a zip on the import
path, with upstream's reader for odd or large members, Decision 6) and 60 (run-time replacement
as a recipe, not a carried patch, Decision 8) in `../questions-for-the-owner.md`. Spec 033
landing first is question 57's answer. The order before spec 023 (Decision 12) follows the
roadmap's "before the zip grows". Nothing waits on any of them; an answer otherwise changes
Decisions 6, 8 or 12 before the build.

## Landing notes

Built 2026-10-18 by an agent (Claude Opus 5.5) in the worktree `wasi_python-035`, branch
`spec/035-the-zips-directory-is-read-once`, in the review's order, one commit per step:
`c6900b6` (part 1, checks 1, 2, 3, 8), `749b873` (part 2, checks 4, 5, 7), `0a875e1` (part 3,
check 6), then the README, CHANGELOG, upstream draft and these notes. Every number below is
EXECUTED on darwin-arm64 with the judge's driver (fuel exact) unless marked; the scratch scripts and
logs are in the session scratchpad (`035-build/`), not in git. The judge was run in the worktree
on its own build, never with `--accept`.

**The baseline.** A full build from pins in the worktree (`scripts/build.sh`, 5 min 18 s) gave
`python.wasm`, the snapshot and the zip byte for byte main's set `s-f94dec535086b06c` (spec 051's).
Its first step 90 wrote a different `MANIFEST`, because `scripts/freeze_bootstrap.py` was edited
while the build ran; with the file put back, step 90 again gave `SHA256SUMS` equal to main's, every
line. Every "before" figure below is that set's.

**Install point A serves.** Check 1, the gate, passed on wasm on both binaries at the first try:
`served == {"/usr/local/lib/python315.zip": "fast"}` with no extra call, `encodings` loaded by a
`zipimporter`, the three seams ours, `_zip_directory.__spec__.origin == "frozen"`,
`zipimport.__file__` and `_frozen_importlib_external`'s `loader_state.filename` as a one-phase
start gives them. Install point B was not built.

**What failed first.** On 051's set every new guest check failed with `ModuleNotFoundError:
_zip_directory`; check 2 measured 77,700 fuel per member; check 4 a first Paris zone of 257.7 M
(plain) and 206.6 M (snapshot); check 5 `type(files("tzdata")) == Path`, with no other
difference (the check's own comparison program agrees with itself on the stock reader); check 7
968.8 M beyond the imports; check 6 `kinds == ["Path"]`. Each unit check failed first because its
module was missing. Two of the checks' first drafts were wrong and were corrected before any code
they judge: check 3 expected `ZipImportError` for the truncated zip, where zipimport's own reader
raises `EOFError` ("EOF read where not expected"); the check now asserts an error, the same from
both readers. And the unit check of `install()` put back only the reader, so the host's own
`importlib.metadata` broke for the rest of the pytest session (the judge recorded no wasmtime
version); it now puts back all three seams.

**One design change, found by check 6 (Decision 6).** The first build of part 3 measured a
snapshot metadata miss of **31.8 M** against the 20 M bound. 9.5 M was the miss; 22.2 M was
importing `_zip_resources`, because `from importlib.resources.abc import …` runs
`importlib.resources` and with it `tempfile`, which a metadata-only call has not imported
(Decision 6 said "already imported by then", true for a resource read only). So
`ZipDirectoryPath` does not subclass `Traversable`: it satisfies the runtime-checkable protocol
the way `zipfile.Path` does, with `read_bytes` and `read_text` written as `Traversable`'s are
(`isinstance(path, Traversable)` holds; a unit check says so). `ZipDirectoryReader`, which must
subclass `TraversableResources`, is made on first access through the module's `__getattr__` and
kept. The miss then measured 11.0 M. No bound or check changed.

**Two readings of the text, recorded.** (1) Check 3 says `served` is "fast" for the zips other
than Zip64 and cp437; the truncated zip's read is `"stock"`, by Decision 2's routing (an entry
past the bytes read), and the check asserts that. (2) The fast reader requires the walk of `n`
entries to end exactly at the directory's size; any other end goes to zipimport's reader. That is
a little stricter than "another `PK\x01\x02` after `n` entries", always in the safe direction.
Also: the courtesy issue is `context/upstream/16-importlib-resources-zip-directory/issue.md`,
since folder `4-` was taken; `_zip_directory` imports `sys` lazily inside the metadata wrapper,
and `_zip_resources` also imports `pathlib` (already loaded by `importlib.metadata` and
`importlib.resources`), `sys` and `zipimport`.

**The fuel.** Before is 051's set, after is this build (`python.wasm` `c2e7c88f…`, snapshot
`2993fb91…`, zip `daf2cdd8…`).

| what | before | after | bound |
|---|---|---|---|
| plain start, slope (check 2) | 77,700 per member | **25,058** per member | 30,000 |
| plain `-c pass` | 242.2 M | **151.0 M** | |
| plain `import pandas` | 4,991.6 M | **4,897.7 M** | |
| snapshot `-c pass` | 82.06 M | **81.90 M** | ratchet |
| snapshot `import pandas` (pre-imported) | 82.08 M | **81.92 M** | |
| re-read after `invalidate_caches()`, plain slope (check 8) | 77,842 (memo) | **25,862** per member; 175.2 M on small.zip | 30,000 |
| first zone, snapshot (check 4) | 206.6 M | **8.61 M** | 15 M |
| first zone, plain, small / padded | 257.7 M / 891.1 M | **8.61 M / 8.63 M**, 4 per member | 20 M; 1,000 |
| second zone (Tokyo after Paris) | | **1.31 M** snapshot, **1.43 M** plain | 2 M |
| metadata miss after `import importlib.metadata`, snapshot (check 6) | 221.9 M | **11.0 M** | 20 M |
| the same, plain, small / padded | | **15.7 M / 40.0 M**, **4,620** per member | 6,000 |
| pandas time-zone job beyond its imports, snapshot (check 7) | 968.8 M | **33.5 M** (plain 38.1 M) | 60 M |
| `version("numpy")` after `import importlib.metadata`, snapshot | 360.9 M | **148.1 M** | |
| `import numpy.testing`, snapshot | 600.6 M | **387.7 M** | |
| importing `_zip_resources`, snapshot | | **1.31 M** after `importlib.resources`, **1.24 M** after `importlib.metadata` (swapped and off; the build review measured 1.27 M and 1.32 M; the final set's figures are in "Revised against the build review") | |

As spec 033 asked: part 3 recovered 212.8 M of `version("numpy")` and 212.9 M of `import
numpy.testing`, the directory scan. What remains of `version("numpy")`, 148 M, is reading and
parsing `METADATA` (`email`'s work, out of scope). Spec 023's re-derivation (Decision 12) should use
**25,058** fuel per member: about 610 × 25,058 ≈ +15.3 M on a plain start (INFERRED, linear).

The marshalled modules: `_zip_directory` 7,907 bytes, `_zip_resources` 16,766 bytes
(`_reactor` 9,859, unchanged). Wall-clock, one machine, a benchmark fact (`wasi_python.run`,
median of five): plain `-c pass` 28 ms → 21 ms, plain `import pandas` 623 ms → 619 ms; the
README's row says 21 ms / 620 ms.

**The judge.** The full `uv run pytest` (slow checks included) on this build: 1,211 passed, 10
skipped, 0 failed; `271/274 pass · 0 gap · 3 blocked · 0 fail`, the three blocked as on main
(prior-art clones, three systems, wheel). `test_callbacks_have_the_types_cpython_calls` (spec
051's scan) is green. Lost 0; gained 20 (the new checks: 1 ×2, 2, 3 ×8, 4 ×2, 5 ×2, 6 ×2, 7 ×2, 8).
`test_goldens_reproduce_under_the_pinned_oracle` passes with the new `pandas_tz` golden, made by
`tests/jobs/regen.py` (every other golden rewrote byte for byte the same). Fuel fell on 53 checks
(every plain check by about 91.5 M; snapshot checks by 0.1 M to 0.5 M).

**Growth, for the accept** (`--accept-growth`):

- `test_binary_is_a_core_wasm_module[plain]`: bytes 31,760,992 → 31,786,310 (+25,318): the two
  frozen modules (24,673 bytes marshalled) and the frozen-module table.
- `test_binary_is_a_core_wasm_module[snapshot]`: bytes 65,533,118 → 65,552,587 (+19,469): the same
  data in the snapshot's image, and (INFERRED) the one more module in its heap.
- `test_extra_preopens_work_on_the_snapshot[root first, data first]`: fuel 847,440,276 and
  847,440,410 → +902,859 to +902,876 each over two runs (+0.107%). The probe calls `isinstance(x, io.IOBase)` on all 62,300
  heap objects. Measured at step 1 (the same growth, then +2.1 M): the heap gained 12 objects, and
  the extra fuel is in the first `isinstance` per type, which fills `io.IOBase`'s ABC caches,
  sets keyed by object address, so their cost moves with the heap's layout; the same loop run a
  second time was 1.1 M cheaper on the new set than on the old. Layout, not work. (Superseded:
  the build review found that step-1 figure does not repeat on the final set; the growth and
  its reason are restated with the final set's numbers in "Revised against the build review".)

  Two snapshot checks that grew past the tolerance at steps 1 and 2 are within it here
  (`test_unbuffered_output_survives_a_hard_exit[snapshot]`, +2,029 at step 2;
  `test_ctypes_stand_in…[snapshot]`, +113,779 at step 2). The snapshot `-c pass` fell 0.2%; no
  plain check grew. Neither is a finding under Decision 10.

**The set.** `MANIFEST` gains `recipe` lines for `recipes/zip_directory.py` and
`recipes/zip_resources.py`; the lines for `recipes/reactor_main.c`,
`scripts/freeze_bootstrap.py` and `scripts/steps/60_link.sh` change; nothing else does. The zip is
byte for byte 051's (`daf2cdd8…`). Steps 60 to 90 run twice from the same tree gave the same
`SHA256SUMS` (the snapshot rebuilds the same on one host). Not run here, left to the lane: a
build in a clean clone, the release dry run and its rebuild jobs on the other hosts (criterion 9).

**For the build review.** The two-phase start in `recipes/reactor_main.c` (`sys._stdlib_dir`
before the import; abort on any failure); the fallback rules in `recipes/zip_directory.py`;
`_zip_resources`' member reader and `open`'s order of errors; the `__getattr__` that makes
`ZipDirectoryReader` (the design change above); `iterdir` on odd names (`"//"` lists under the
root, by `zipfile.Path`'s own `_is_child` rule over zipimport's names); and the layout reading of
the one fuel growth.

### Revised against the build review

By the implementer, 2026-10-18, against the build review
(`035-the-zips-directory-is-read-once-2026-10-18.md`, written in the lane's scratchpad
`build/reviews-evidence/035-buildreview/`, not yet in git; F1 to F4 and the informational F5).
Not rebased: main moved (spec 050, AGENTS.md rule 3a) and the lane rebases. Every check below was
written before its fix and seen failing first. EXECUTED on darwin-arm64 with the judge's driver
unless marked; logs in the worktree's ignored `build/revise035/`.

- **F1, five unchecked rules, now checked** (`5e30cfe`, `tests/unit/test_zip_directory.py`).
  Three zips join `ODD` in `test_odd_zips_go_to_the_stock_reader`: a local-header offset past the
  directory, a negative archive offset (the end record's directory offset raised by 10), and a
  Zip64 extra (compressed size `0xFFFFFFFF`) with a plain end record and no `PK\x06\x06`. A new
  `test_the_odd_zips_have_what_they_claim` asserts each zip's feature, so the check cannot pass on
  a zip that lacks it (and that `zipfile` reads the Zip64-extra zip). A new
  `test_metadata_leaves_a_prefixed_zip_to_upstream` puts a zipimporter for `<zip>/sub` (prefix
  `sub/`) in `sys.path_importer_cache` and asserts its root reaches `stock_zip_children` while the
  archive's own root is answered from the dict. A new case, `stream not ended`, in
  `test_the_member_reader_hands_odd_members_to_zipfile`: a deflate stream with no final block
  (sync-flushed), marked deflated, whose output has the right size and CRC, reaches `zipfile`.
  On the review's mutants (its `mutate.py`, on a `git archive` copy, restored and `cmp`-clean;
  `build/revise035/f1-mutants.log`): `no_offset_check`, `no_arc_check` and `no_entry_max32` each
  fail their zip's two cases; `zr_zip_children_prefix` fails the prefix check; `zr_no_eof` fails
  the new case; HEAD passes all. `no_header_checks` still passes, as the review expected: those
  two tests are implied by `arc_offset < 0` (INFERRED from the arithmetic, `header - cd_size -
  cd_offset`). The optional host differential against `build/Python-3.15.0/Lib/zipimport.py` is
  not added: the unit suite runs without a build tree, and the named cases cover the surviving
  mutants.
- **F2, staleness, now said** (`625a4d6`). Decision 6's accepted differences gain
  "Freshness": answers reflect zipimport's view of the zip, refreshed by
  `importlib.invalidate_caches()`, as imports do; a zip rewritten in place lists its old names
  and distributions until then, a moved `METADATA` raises `MetadataNotFound` (a
  `FileNotFoundError`, not a `PackageNotFoundError`), and the bytes stay current because a stale
  entry fails the member reader's checks. The README's list says the same, and the Design
  table's README row names it. No code change: this is Decision 7's design.
- **F3, `pwd`, fixed in code** (`dce6cd3`). `ZipDirectoryPath.open(mode="r", *args, pwd=None,
  **kwargs)`: with `pwd` `None` the fast reader serves as before; any other `pwd` goes to
  `zipfile.Path.open(mode, *args, pwd=pwd, **kwargs)`. Why code rather than a README line, by
  §6 and the spec's own promises: the owner accepted question 59 with a closed list of
  differences, and `pwd` is not on it; the Intent says "the answers stay upstream's"; and
  question 59 sends encrypted members to `zipfile.Path`, which without `pwd` could never decrypt
  one, so the documented route would leave a guest's encrypted member unreadable through
  `files()` where upstream reads it. The fix is a few lines of a recipe file (§6.2: a recipe, no
  patch), works the same on every host (§6.3), and is the smallest change that keeps the spec's
  promise (§6.4); a new accepted difference would have widened what the owner accepted. The
  checks, both seen failing first with `ValueError: encoding args invalid for binary operation`
  (`build/revise035/f3-unit-failfirst.log`, `f3-failfirst.log`): in
  `test_the_zip_path_opens_as_zipfile_path_does`, reads with `pwd` `None`, `b"k"` and `"k"`, binary
  and text, equal the host `zipfile.Path`'s (3.15's `ZipFile.open` ignores a password, of any
  type, for an unencrypted member: its type test is inside the encrypted branch, READ
  `Lib/zipfile/__init__.py:1812-1817`); `test_a_password_goes_to_zipfile`, with `zipfile.Path`
  stubbed, sees a plain member opened with `pwd=b"k"` reach `zipfile` with that password; and
  check 5 (`test_resources_read_as_zipfile_reads_them`, both binaries) compares `open("rb"|"r",
  pwd=…)` reads of `tzdata.zi` with `zipfile.Path`'s for the same three values. The README says
  a `pwd` read goes to `zipfile`; Decision 6's `open` is written with it.
- **The binaries changed, so the set was rebuilt from pins** (`scripts/build.sh --plain`, every
  step, exit 0, `build/revise035/build.log`): `python.wasm` 31,786,374 bytes `42344e2c…`,
  `python-snapshot.wasm` 65,548,702 bytes `c4190ca0…`, the zip 11,203,143 bytes `daf2cdd8…`
  (unchanged, still byte for byte 051's), `MANIFEST` `7c9ab793…`. Against the reviewed build, `MANIFEST`
  differs in exactly two `recipe` lines (`recipes/zip_resources.py`, `scripts/freeze_bootstrap.py`,
  the latter for F5's docstring). `_zip_resources` is 16,841 bytes marshalled (was 16,766);
  `_zip_directory` 7,907 and `_reactor` 9,859, unchanged.
- **F4, the growth reason restated on the final set** (`build/revise035/growth.log`, the review's
  `growth.py`, main's set `s-f94dec535086b06c` against this one). The check's fuel:
  `[root first]` 847,440,276 → 848,590,531 and `[data first]` 847,440,410 → 848,590,665, each
  **+1,150,255 (+0.136%)**. The probe split out:

  | snapshot | objects, types | setup | a plain loop (`type(o) is int`) | first `isinstance(o, io.IOBase)` loop | second |
  |---|---|---|---|---|---|
  | main | 62,302, 343 | 407,050,351 | 237,075,875 | 531,703,344 | 452,554,777 |
  | 035, final | 62,315, 343 | 406,969,480 (−80,871) | 237,034,514 (−41,361) | 533,067,838 (+1,364,494) | 453,338,054 (+783,277) |

  The reason, for `--accept-growth`: the heap holds 13 more objects (INFERRED: `_zip_directory` and
  what it keeps) and the same 343 types. Setup and a plain loop over the same objects fell. All the
  growth is in `isinstance(o, io.IOBase)`, whose ABC caches are sets of types hashed by address,
  so its cost moves with where the snapshot's heap puts the types (INFERRED). 13 objects at about
  7,300 fuel each explain about 0.1 M of the two loops' 2.15 M; the rest follows the layout,
  which moved again with F3's change (INFERRED; the same check grew +902,876 on the reviewed
  build, +1,150,255 on this one).
  Not work the probe does: nothing in it touches the zip. The step-1 claim ("1.1 M cheaper the
  second time") is withdrawn; it does not hold on the reviewed or the final set.
- **F5, informational.** Decision 6 now says the built structure (no `Traversable` subclass;
  `importlib.resources.abc` imported only when `ZipDirectoryReader` is first made; the reader made
  through the module's `__getattr__`) and points here; Decision 8 and the Design table name
  `context/upstream/16-importlib-resources-zip-directory/` (`625a4d6`). The `_zip_resources`
  import row above is marked; the final set's figures are below. The courtesy draft now names
  freshness and `pwd` beside odd names (`625a4d6`). The E501 at `scripts/freeze_bootstrap.py:41`
  is fixed (`31581f1`; one word, a docstring, so only `MANIFEST`'s line changes). The landing
  notes' "Lost 0; gained 20" is joined by the one "unrun locally" check, the prior-art licence
  check, as on the review's run: the worktree has no clones.

**The final set's numbers** (`build/revise035/measure.log`, the review's `measure.py`, and the
checks' own notes; before is main's set):

| what | before | after |
|---|---|---|
| plain start, slope (check 2) | 77,700 per member | **25,058** per member |
| plain `-c pass` | 242,196,369 | **150,988,365** |
| plain `import pandas` | 4,991,551,117 | **4,898,859,993** |
| snapshot `-c pass` | 82,060,117 | **81,868,626** |
| snapshot `import pandas` | 82,082,564 | **81,892,613** |
| re-read after `invalidate_caches()`, plain slope (check 8) | | **25,911** per member |
| first zone, snapshot (check 4) | 206,573,835 | **8,560,452**; Tokyo after it **1,340,678** |
| first zone, plain, small / padded | | **8,688,525 / 8,764,350**, 14 per member; Tokyo 1,378,516 |
| metadata miss, snapshot (check 6) | 221,967,070 | **11,041,335** |
| the same, plain, small / padded | | **15,692,259 / 40,044,753**, 4,612 per member |
| pandas time-zone job beyond its imports (check 7) | | **33,408,424** snapshot, 38,289,547 plain |
| `version("numpy")` after `import importlib.metadata`, snapshot | 360,991,107 | **148,086,666** |
| `import numpy.testing`, snapshot | 600,649,333 | **387,706,546** |
| importing `_zip_resources` alone, snapshot | | **1,414,814** after `importlib.resources`, **1,337,710** after `importlib.metadata` |

Every bound holds with the margins of the first build.

**The judge.** The full `uv run pytest` (slow checks included), once, after the rebuild
(`build/revise035/judge-full.log`; the fast tier was the loop before it, as AGENTS.md rule 3a
asks): **1,221 passed, 10 skipped**; `wasi_python v1: 271/274 pass · 0 gap · 3 blocked · 0 fail
(unit suite 950/957, 7 skipped)`, the three blocked as on main; ratchet against `614520fff6`:
`lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 20 · grew 4`, exit 1 only for
`RED: 4 metric(s) grew`, the four below (`build/revise035/ratchet.txt`: every metric against
`accepted.json`; 53 fell, none grew besides these). The unrun-locally check is the prior-art
licence check (no clones in the worktree). `ruff check` and `ruff format --check` are clean on
`src tests`.

**Growth, for the accept** (`--accept-growth`), replacing the list above:

- `test_binary_is_a_core_wasm_module[plain]`: bytes 31,760,992 → 31,786,374 (+25,382): the two
  frozen modules (24,748 bytes marshalled) and the frozen-module table.
- `test_binary_is_a_core_wasm_module[snapshot]`: bytes 65,533,118 → 65,548,702 (+15,584): the
  same data in the snapshot's image and (INFERRED) the one more module in its heap.
- `test_extra_preopens_work_on_the_snapshot[root first, data first]`: fuel +1,150,255 each
  (+0.136%): F4's account above, layout of the `isinstance` loops, not work.

Not run here, left to the lane, as before: a build in a clean clone, the release dry run and its
rebuild jobs on the other hosts (criterion 9).
