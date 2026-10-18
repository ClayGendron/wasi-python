# The zip's directory is read once

- **Status:** executed, 2026-10-17. Research only: nothing in the build, the recipes, `src/`,
  `tests/` or the judge was changed. Box: one working session; finished inside it, with what was
  not run listed at the end.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), briefed by the session's lead agent.
- **The direction it answers:** the owner's answer to question 44 (`decisions.md`): "cut the
  zip's per-member cost first: a research memo, then a specification ('the zip's directory is
  read once'), before tier A grows the zip."
- **Feeds:** the specification "the zip's directory is read once" (designed below); tier A's
  specification, which waits for it; "the zip carries what packages need" (its kept `METADATA`
  makes `importlib.metadata` reads common, finding 5).
- **Stands on:** `2026-10-17-what-else-the-default-profile-carries.md` (findings 4e and 5: about
  77,912 fuel per member on a plain start, about 116,000 per member per resource read, 155 G per
  `pytz.timezone()`), `2026-10-17-trimming-fonttools.md` (the lever is the per-member cost, not
  one package's member count), `2026-10-17-the-runtime-for-agent-code.md` (the import path is
  the stdlib zip only, `recipes/reactor_main.c:137-150`).
- **Evidence:** `2026-10-17-the-zips-directory-is-read-once/` beside this memo. `scripts/`
  holds every script run; `outputs/` every number quoted (`derived.txt` is every derived number,
  made by `scripts/analyze.py` from the TSVs). The scratch zips stayed in the session scratchpad
  (artifacts never live in git).
- **Repository state:** `main` at `2af09e6`. The guest runs used copies of `build/artifacts/`
  (CPython 3.15.0, numpy 2.5.2, pandas 3.0.6; `python.wasm` `4befe9de…`,
  `python-snapshot.wasm` `c7302cfd…`, `python-stdlib.zip` `1add57e4…`, the hashes in that
  folder's `SHA256SUMS`), through `wasi_python.run` with fuel metered. The main tree's judge
  and `scripts/build.sh` were not run.

## The question

Every member of the stdlib zip costs fuel on every plain start, and every resource read from the
zip costs fuel per member again. The default profile will take the zip from 1,751 members to
about 6,630. Where exactly does the per-member cost come from? Why do snapshot calls not pay it,
and do they pay it on resource reads? What fix cuts it, at what cost and risk, and what would a
specification check?

Terms used below:

- **Member:** one file in the zip. **Directory:** the zip's central directory, the table at its
  end that lists every member's name, size and offset.
- **Plain start:** a call on the plain reactor (`snapshot=False`). **Snapshot call:** a call on
  `python-snapshot.wasm`, whose memory Wizer captured after the interpreter started.
- **Resource read:** reading a data file that sits inside a package, through
  `importlib.resources` (time zones through `zoneinfo`, a template, a font).
- **Fuel:** wasmtime's count of executed WebAssembly instructions. Every number here is fuel,
  never time (§4.9).
- **Slope:** the extra fuel per extra member, from the same case on two zips. Test zips of
  1,751, 3,502, 5,253 and 7,004 members were made by copying today's members under `pad1/`,
  `pad2/`, `pad3/` (`scripts/make_zips.py`, `outputs/zips.tsv`). The copies keep each member's
  name length, compression and bytes; nothing imports them.

## Method (EXECUTED)

- `scripts/guest_start.py`: plain `-c pass` on each zip; one and three extra calls of
  `zipimport._read_directory`; what the start left in zipimport's cache; `zipfile.ZipFile` and
  `zipfile.Path` on the zip; resource reads and `zoneinfo` loads. The snapshot cases run on
  today's zip only, since the snapshot runs beside the exact zip it was built with. Output:
  `outputs/start.tsv`.
- `scripts/guest_candidates.py`: zipimport's reader with parts swapped for C calls; two
  rewrites of the reader; `marshal.loads` of the parsed directory; three resource readers.
  Every case runs the same prelude (`scripts/candidates.py` compiled in the guest), so the
  difference against the `base` case is the body's cost. Output: `outputs/candidates.tsv`.
- `scripts/guest_followup.py`: `importlib.metadata` on zips with one made-up `.dist-info`, and
  a pandas time-zone job on both binaries. Output: `outputs/followup.tsv`.
- `scripts/guest_invalidate.py`: `importlib.invalidate_caches()` then an import. Output:
  `outputs/invalidate.tsv`.
- `scripts/guest_builtins.py`: whether `_struct` is builtin, whether zipimport is frozen, and
  which loader loaded `encodings`. Output: `outputs/builtins.txt`.
- `scripts/candidates.py` holds the prototypes. They are our own code, written for this memo
  to count fuel; they are not product code.
- Plain calls draw a random hash secret, so the same plain case varies by a few M fuel between
  runs (`candidates.tsv` was run twice, the second time with two functions added to the
  prelude; every case-minus-base difference moved by under 2 M except one by 7 M; `outputs/`
  keeps the second run). Snapshot calls are exact.

Each script states its command at its top. From the repository root:
`uv run --no-sync python <script> <artifact copy dir> <scratch zips dir> <output>`, then
`uv run --no-sync python -I scripts/analyze.py outputs`.

## Findings

### 1. A plain start reads the directory exactly once, in zipimport's Python code (EXECUTED)

| zip members | plain `-c pass` | one more `zipimport._read_directory` |
|---|---|---|
| 1,751 (today's) | 241.7 M | 134.9 M |
| 3,502 | 377.4 M | 269.5 M |
| 5,253 | 513.7 M | 405.6 M |
| 7,004 | 649.7 M | 540.3 M |

- Plain start grows **77,662 fuel per member**; one call of zipimport's directory reader grows
  **77,184 per member**. They are the same cost: the start reads the directory once, and that
  read is the whole of the per-member cost (`outputs/derived.txt`).
- The rest of a plain start does not grow with the zip: 241.7 − 134.9 = **106.9 M**. Today the
  directory is 56% of a plain start; at 7,004 members it is 83%.
- The reader is `_read_directory` in `Lib/zipimport.py` (READ: lines 295-534). zipimport is a
  frozen module (EXECUTED: `zipimport.__spec__.origin == 'frozen'`, `outputs/builtins.txt`),
  so its Python bytecode runs under the interpreter like any other Python. The first read
  happens inside `Py_InitializeFromConfig`: `encodings` is not frozen, and the guest's
  `encodings` was loaded by `<zipimporter object "/usr/local/lib/python315.zip/">` (EXECUTED,
  `outputs/builtins.txt`; READ: `Python/pylifecycle.c` imports it in `init_interp_main`, after
  `_PyImport_InitExternal` installs the zipimport path hook).
- The result is cached in `zipimport._zip_directory_cache`, keyed by the archive's path: one
  entry, 1,917 names (1,751 members and 166 implied directories) after the start (EXECUTED,
  `start.tsv`, case "cache after start"). Every later import looks names up in that dict, which
  costs nothing per member.

Where the 77,000 go, per member (EXECUTED: `candidates.tsv`, each part swapped for a C call):

| part of `_read_directory` | fuel per member | share |
|---|---|---|
| eleven calls of the `_unpack_uint16/32` helpers (a Python frame and an `assert` each) | about 14,000 | 18% |
| one call of `_bootstrap_external._path_join` | about 3,300 | 4% |
| the rest: three buffered `fp.read` calls, nine slices, the name's decode and `replace`, the tuple, the dict insert, the implied-directory pass | about 60,000 | 78% |

The read buffer is not the cause: `io.DEFAULT_BUFFER_SIZE` is 131,072 and WASI reports no block
size (EXECUTED, `st_blksize == 0`), so the file gets the 128 KiB default buffer (READ: `open`'s
buffering rule) and the reader asks the host for a new block only every 128 KiB. Its cost is in Python calls per member, not in host calls. Storing the members
uncompressed does not help: a plain `pass` on the 7,004-member zip is 645.6 M stored against
649.7 M deflated (−0.6%, from imports that skip a decompress), and the zip grows from 44.6 MB to
112.4 MB (EXECUTED, `start.tsv`, `zips.tsv`).

### 2. Snapshot calls do not pay it at start, but pay it again in three other places (EXECUTED)

- **At start, no.** Wizer runs the interpreter's start at build time, so the snapshot's memory
  already holds `_zip_directory_cache` with its 1,917 names (EXECUTED: the snapshot's
  "cache after start" shows it before any user code). zipimport reads a directory only for a path
  not in that dict (READ: `zipimporter.__init__`, `_get_files`). A snapshot `pass` is 82.0 M.
- **After `importlib.invalidate_caches()`, yes.** It calls `zipimporter.invalidate_caches()`,
  which drops the dict; the next import reads the whole directory again. On the snapshot that
  costs 170.8 M more; on a plain call at 7,004 members, 671.7 M more (EXECUTED,
  `invalidate.tsv`). Agent code that writes a module and imports it calls this.
- **On every resource read, yes, and at a higher price.** See finding 3.
- **On the first `importlib.metadata` query, yes.** See finding 5.

### 3. Each resource read parses the directory again, in `zipfile`, and builds more (EXECUTED)

`zipimporter.get_resource_reader` returns `importlib.resources.readers.ZipReader`, whose
`files()` is `zipfile.Path(self.archive, self.prefix)` (READ: `Lib/zipimport.py:208-212`,
`Lib/importlib/resources/readers.py:37-60`). `zipfile.Path` opens a new `ZipFile`, which parses
the directory into a `ZipInfo` per member, then builds the set of every name and every implied
directory (`FastLookup._name_set`, READ: `Lib/zipfile/_path/__init__.py`). Nothing is kept
between reads, and zipimport's dict, already parsed, is not used.

| per member, plain | fuel |
|---|---|
| `zipfile.ZipFile(zip)`: the directory into `ZipInfo` objects | 60,746 |
| plus `zipfile.Path`'s name set (implied directories) | 124,090 in all |
| one resource read (`files(...).joinpath('UTC').read_bytes()`), first | 119,729 |
| each later resource read | 124,392 |
| first `ZoneInfo('Europe/Paris')` | 121,317 |
| a second zone | 126,141 |

On today's zip, each read is about 182 M fuel on the snapshot and on a plain call alike (the
snapshot: first read 204.1 M, each later read 182.3 M, `ZoneInfo('Europe/Paris')` 225.4 M, a
second zone 183.7 M). A snapshot `pass` is 82 M, so **one time-zone load costs more than two
whole snapshot calls**. A pandas job that makes one Paris timestamp and a two-day Tokyo range
costs **962.1 M** on the snapshot today (EXECUTED, `followup.tsv`). At 6,630 members each read
would be about 822 M (INFERRED, linear).

This is finding 4e's 116,000 per member per read, now profiled: it is `zipfile`'s parse plus
`zipfile.Path`'s name set, once per read. pytz pays it once per zone file it checks, which is why
one `pytz.timezone()` cost 155 G (pytz itself was not run here).

### 4. The candidate fixes, measured (EXECUTED unless marked)

**For the start (the directory reader):**

| reader | fuel per member | at 6,630 members, plain `pass` | notes |
|---|---|---|---|
| zipimport's, today | 77,184 | about 619 M | |
| our rewrite: one `read` of the directory, one `struct` call per member | **24,129** (15,355 for the parse, the rest for implied directories) | **about 267 M** | same dict, `==` checked at 1,917 and 7,671 names |
| our rewrite with `int.from_bytes` on slices, no `struct` | 53,014 | about 458 M | same dict |
| `marshal.loads` of the parsed dict (a shipped, pre-parsed index) | 12,198 | about 188 M | the index is 224 KB for 1,917 names, 952 KB for 7,671 |
| a reader in C building the same dict | about 10,000 to 15,000 (INFERRED: it makes the objects `marshal.loads` makes) | about 175 M to 205 M (INFERRED) | not built |

The 6,630-member column is 106.9 M plus the per-member cost times 6,630 (INFERRED, linear).

- **Where a new reader must go in.** The first read happens during `Py_InitializeFromConfig`
  (finding 1), before any code of ours runs. CPython's multi-phase start lets code run between
  its two phases: `PyConfig._init_main = 0`, then `_Py_InitializeMain()` (READ:
  `Include/cpython/initconfig.h:230`, `Include/cpython/pylifecycle.h:29`; CPython's own test
  `test_init_main` in `Programs/_testembed.c:2094` runs Python before `_Py_InitializeMain`). In
  the first phase the builtin and frozen importers work (READ), so `zipimport` (frozen) and
  `_struct` (builtin here: EXECUTED, `outputs/builtins.txt`) can be imported, and
  `zipimport._read_directory` replaced. zipimport looks the function up by name at each call
  (READ: `__init__`, `_get_files`), so the replacement serves the start, every later zip, and the
  re-read after `invalidate_caches()`. All of this lives in `recipes/reactor_main.c` and a
  frozen module of ours, as `_reactor` already does (`scripts/freeze_bootstrap.py`). It is a
  recipe, not a patch (§4.1). That the first phase can import frozen `zipimport` was read, not
  run (INFERRED): the specification's first check proves it.
- **A pre-parsed index** is about twice as cheap again, but it needs a second artifact or a
  member found without the directory, a check that it matches the zip it sits in, and a change
  to step 70. The C reader gets the same cost with no new file and nothing to go stale, and the
  rewrite in Python gets two thirds of the gain with neither.
- **A carried patch to `Lib/zipimport.py`** with the `struct` rewrite is not upstreamable as it
  stands: upstream, `_struct` is built as a stdlib module (READ:
  `Modules/Setup.stdlib.in:45`), not a bootstrap one, and zipimport imports only bootstrap
  modules. The `int.from_bytes` form is upstreamable but saves only a third. A patch would stay
  carried, which §4.1 does not want; the recipe needs no patch.
- **A second zip, or packages in a read-only directory.** A second zip on `sys.path` is read at
  the first import that misses the first zip, and every failed `import` (an optional-dependency
  probe) misses both, so nearly every call would read both (INFERRED, READ:
  `PathFinder`). A directory instead of a zip changes the artifact set (§4.6) and trades the
  directory read for host `stat` and `listdir` calls per directory. Neither is needed.

**For resource reads:**

| reader | first zone | each later zone | grows with the zip? |
|---|---|---|---|
| stock `ZipReader` (plain) | 255.0 M (1,751), 885.0 M (7,004) | 182.2 M, 834.9 M | yes, 119,928 per member |
| `ZipReader` keeping one `zipfile.Path` per archive (plain) | 268.9 M, 939.0 M | 0.52 M, 0.24 M | the first read, yes |
| **our reader on zipimport's dict** (plain) | **13.8 M, 11.3 M** | **0.59 M, 0.64 M** | **no** |
| stock, snapshot (1,751) | 205.4 M | 182.4 M | yes |
| our reader, snapshot (1,751) | **7.3 M** | **0.45 M** | no |

- **Our reader** (`IndexReader` and `IndexPath` in `scripts/candidates.py`, about 100 lines)
  answers `files()`, `joinpath`, `is_file`, `is_dir`, `iterdir`, `open` and `name` from
  zipimport's cached dict, through `zipimporter._get_files()`, and reads a member's bytes
  through `zipimporter.get_data`, which zipimport already uses for every import. It parses
  nothing. Checked against the stock reader (EXECUTED, on both binaries and both zip sizes):
  the bytes of 40 zones equal, the listing of `tzdata/zoneinfo/Europe` (65 names) equal,
  `tzdata.zi` read as text equal, and a missing name is not a file.
- Loading all 598 zone files after Paris costs 0.29 M each, 174 M in all, on both zip sizes. A pytz-sized walk of the zone files would cost about 0.2 G instead of 155 G
  (INFERRED: pytz itself was not run).
- The pandas job of finding 3: **28.6 M** on the snapshot with our reader, against 962.1 M
  stock; the same output (`2:00:00 ['+0900', '+0900']`).
- **Keeping one `zipfile.Path` per archive** is rejected: the first read in each call still pays
  the whole parse (224.9 M on the snapshot), which is the case that matters (one call, one
  zone), and it keeps a file open for the life of the process.
- **Use the hook, not the private dict.** CPython issue #121342 (open, READ) records that
  `pkgutil`'s direct use of `zipimport._zip_directory_cache` broke when 3.13 made invalidation
  lazy. The reader asks `zipimporter._get_files()`, which refills the dict.

### 5. `importlib.metadata` pays the same parse, once per process (EXECUTED)

`importlib.metadata` finds distributions in a zip on `sys.path` through
`FastPath.zip_children`, which builds a `zipfile.Path` of the whole archive (READ:
`Lib/importlib/metadata/__init__.py:852-860`). The result is cached per process, so this is one
parse per call that queries metadata, on both binaries.

| query (plain) | stock | on zipimport's dict |
|---|---|---|
| `version('tabulate')` | 455.1 M (1,752), 1,152.7 M (7,005); 132,801 per member | 197.5 M, 213.1 M; 2,971 per member |
| a missing distribution | 273.2 M, 969.0 M; 132,458 per member | 9.7 M, 33.2 M; 4,472 per member |
| a missing distribution, snapshot (1,751) | 217.5 M | 9.7 M |

The 197 M left in `version()` is reading and parsing `METADATA` (its imports, `email` among
them), which does not grow with the zip. Today the zip keeps no `.dist-info`, so few calls query
metadata; "the zip carries what packages need" keeps `METADATA` and `entry_points.txt`, and then
`import tabulate`, `df.to_markdown()` and `markdown`'s extensions query it on every call (the
default-profile memo, finding 4a). At 6,630 members each such call would pay about 0.88 G
(INFERRED, linear).

`FastPath.zip_children` is reached only after `importlib.metadata` is imported, which neither
binary does at start, so a recipe cannot replace it when the interpreter starts. The prototype
(`use_index_metadata` in `scripts/candidates.py`) replaces it after import. The specification
installs it when `importlib.metadata` is first executed: a wrapper around
`zipimporter.exec_module` that replaces the one function once that module has run, then removes
itself. It costs one Python call per module imported from the zip until then (INFERRED, a few
thousand fuel each).

### 6. Upstream (READ, 2026-10-17)

- No open CPython issue or pull request asks for a faster zipimport directory read, or for
  `ZipReader` to reuse zipimport's directory. The last eight commits to `Lib/zipimport.py`
  (to gh-141276, 2026-10-10) are about correctness, zstd, and dropping deprecated code; the last
  six to `Lib/importlib/resources/readers.py` are about behaviour (`gh api` commit listings and
  an issue-title search, sources at the end).
- bpo-8745 (2010, the C-era zipimport) read the directory sequentially to save seeks, with mixed
  results by platform. The pure-Python reader came with bpo-25711 (3.8).
- #121342 (open): direct use of `_zip_directory_cache` is unsafe after invalidation (finding 4).
- `importlib.resources` and `importlib.metadata` come from python/importlib_resources and
  python/importlib_metadata, where a change would be proposed first. A courtesy issue there,
  "`ZipReader.files()` parses the archive on every call; zipimport's directory already has it",
  is worth filing. The design below needs no upstream change, so it waits on none.
- Prior art: no clone under `context/prior_art/` changes how a zip's directory is read (READ:
  a grep for `zipimport` and `_zip_directory_cache` outside the CPython clone finds one Pyodide
  test). Nothing was cloned for this memo.

## The design for the specification (INFERRED from the findings)

**"The zip's directory is read once."** One recipe change, class build (it touches `recipes/`
and the link). No patch, no new artifact, no change to the zip's bytes or step 70.

1. **A faster directory reader, installed before the first import from the zip.**
   - A frozen module of ours, compiled at build time like `_reactor`, defines
     `read_directory(archive)`: one read of the directory, one `struct` unpack per member, the
     implied directories, the same dict as zipimport's. It imports only `_io`, `_struct` and
     `zipimport`. For anything outside the plain case (Zip64 fields, a name that is neither
     UTF-8-flagged nor ASCII, a count that does not match, any error) it calls zipimport's own
     reader, kept under another name, so errors and edge cases are upstream's.
   - `recipes/reactor_main.c` starts the interpreter in two phases (`_init_main = 0`, the
     module's `install()`, then `_Py_InitializeMain()`). `install()` sets
     `zipimport._read_directory`. Both binaries get it; the snapshot freezes the same dict it
     freezes today.
   - Expected: plain `pass` about 149 M today (106.9 M + 1,751 × 24,129), down from 241.7 M;
     about 267 M at 6,630 members, against about 619 M (INFERRED, linear). Snapshot start
     unchanged at 82 M. The re-read after `invalidate_caches()` falls by the same factor.
2. **A resource reader on zipimport's directory.** Our module in the zip (a stand-in, §4.1),
   the reader of `scripts/candidates.py` made complete: the `Traversable` interface, `parent`,
   and an `iterdir` that builds a children map once per call (one pass over the names) instead
   of a scan per directory. The frozen module sets `zipimporter.get_resource_reader` to import
   it on first use. Expected: a zone load about 7 M on the snapshot and 11 M to 14 M plain,
   whatever the zip's size, against 182 M to 255 M today and about 822 M at 6,630 members.
3. **`importlib.metadata` on the same directory.** The same module's `zip_children`, installed
   by the one-time `exec_module` wrapper (finding 5). Expected: a missing distribution about
   10 M, against 218 M on the snapshot today.
4. **A C reader is not in this specification.** It would take the start from about 267 M to
   about 190 M at 6,630 members (INFERRED), at the price of a C parser of zip structures to
   review. Write it only if a later memo shows the plain start matters that much: snapshot calls
   are the default, and they already pay nothing here.

### What the specification checks (operation counts, §4.9)

The judge builds a padded zip from the artifact zip in its own temporary folder, as
`scripts/make_zips.py` does (today's members, plus copies under `pad1/` to `pad3/`), and runs
the plain reactor on both.

1. **Start slope.** Plain `-c pass` grows at most **30,000 fuel per member** between the
   artifact zip and the padded zip (today 77,662).
2. **Same directory.** In the guest, the new reader's dict equals zipimport's own reader's dict,
   on the artifact zip and the padded zip; and the same holds for a Zip64 zip and a cp437-named
   zip written in a writable `/tmp` (`root=True`) and put on `sys.path`, which must also import.
3. **A resource read does not grow with the zip.** The first `ZoneInfo('Europe/Paris')` costs
   at most **20 M** on a plain call on both zips, and at most **15 M** on the snapshot; a
   second zone at most **2 M**. The slope between the two zips is at most **1,000 fuel per
   member** (today 121,317).
4. **Same resources.** For every member under `tzdata/zoneinfo/`, the bytes through
   `importlib.resources` equal `zipfile.ZipFile(zip).read(name)`; `iterdir()` names equal
   `zipfile.Path`'s for every directory of `tzdata` and `pandas`; `is_file`, `is_dir` and a
   missing name answer as `zipfile.Path` does; `read_text` equals.
5. **Metadata.** `importlib.metadata.version` of a missing distribution costs at most **20 M**
   on the snapshot; on a zip with a `.dist-info` it returns the same version as the stock path.
6. **The pandas time-zone job** (finding 3) costs at most **60 M** on the snapshot (today
   962.1 M) and prints what native pandas prints.
7. **Invalidation.** `importlib.invalidate_caches()` then an import grows at most **30,000 fuel
   per member** on a plain call.
8. **The snapshot stays reproducible** (spec 012) and its start does not grow.

Bounds carry slack for the plain reactor's random hash secret (finding: a few M between runs).

### What it changes

- `recipes/reactor_main.c` (two-phase start), a new frozen recipe module, a new stand-in module
  in the zip, `scripts/freeze_bootstrap.py` or step 60 (to freeze one more module), step 70 (one
  `--file` line), judge jobs for the eight checks, the README's numbers.
- What the guest sees: `importlib.resources.files(pkg)` for a package in the zip returns our
  `Traversable`, not a `zipfile.Path`. Code that needs `zipfile.Path`'s own attributes (`.root`,
  `.at`) would break; code using the `Traversable` interface, and `as_file`, works. The output of
  every check above is unchanged.
- It must land before tier A grows the zip; "the zip carries what packages need" can land
  before or after it.

## Questions for the owner

1. **The resource reader changes a type the guest can see.** `importlib.resources.files()` on
   a package in the zip would return our `Traversable` instead of `zipfile.Path`. This memo
   recommends it: same bytes, same listing, 28 times cheaper on the snapshot today and about
   100 times at 0.1.0's size. Accept, or keep `zipfile.Path` and pay about 0.8 G per resource
   read at 0.1.0?
2. **Replacing stdlib functions at start as a recipe.** Three functions are replaced at run time
   by recipe code (zipimport's directory reader, `zipimporter.get_resource_reader`,
   `importlib.metadata`'s zip search), with judge checks that their results equal upstream's.
   §4.1 prefers a recipe to a patch, and a patch here could not be upstreamed as it stands
   (finding 4). Confirm that a run-time replacement counts as a recipe, or say it must be a
   carried patch?

## Where it stopped, and what was not run

- No `python.wasm` was built. The two-phase start and the import of frozen `zipimport` in the
  first phase were read in CPython's source, not run; the specification's first check runs them.
- The C reader's cost is inferred from `marshal.loads`, not measured.
- pytz was not run; its number is inferred from the per-read cost.
- The 6,630-member numbers are linear projections from zips of 1,751 to 7,004 members whose
  extra members are copies of today's; the real packages' name lengths differ a little.
- The snapshot was measured only beside today's zip.
- The `exec_module` wrapper for `importlib.metadata` was not prototyped; the prototype replaced
  the function after importing the module.

## Sources (READ, 2026-10-17)

- CPython 3.15.0 source, `build/Python-3.15.0/`: `Lib/zipimport.py`,
  `Lib/importlib/resources/readers.py`, `Lib/importlib/resources/_adapters.py`,
  `Lib/zipfile/_path/__init__.py`, `Lib/importlib/metadata/__init__.py`,
  `Lib/importlib/_bootstrap_external.py`, `Python/pylifecycle.c`, `Python/import.c`,
  `Include/cpython/initconfig.h`, `Include/cpython/pylifecycle.h`, `Programs/_testembed.c`,
  `Modules/Setup.stdlib.in`.
- Commit listings: `gh api repos/python/cpython/commits?path=Lib/zipimport.py`,
  `...?path=Lib/importlib/resources/readers.py`,
  `gh api repos/python/importlib_resources/commits?path=importlib_resources/readers.py`.
- Issue search: `gh api search/issues -f q='repo:python/cpython zipimport in:title'`;
  https://github.com/python/cpython/issues/121342; https://github.com/python/cpython/issues/103200;
  https://bugs.python.org/issue8745; https://github.com/python/cpython/pull/4023 (bpo-25711).

## One line

A plain start reads the zip's directory once, in zipimport's Python, at about 77,000 fuel a
member, and every resource read parses it again in `zipfile` at about 124,000 a member, snapshot
or not; a recipe that swaps in a one-read `struct` reader at start (24,000 a member) and serves
resources and metadata from the directory zipimport already holds (no cost per member) keeps
0.1.0's plain start near today's and makes a time-zone load about 7 M instead of 0.2 to 0.8 G.
