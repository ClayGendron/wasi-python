# Where package data lives

- **Status:** research, 2026-10-16
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5). Box: 90 minutes; stopped
  at about 75. The places it stopped are listed under "Where it stopped".
- **Feeds:** the matplotlib specification. It answers the two conditions
  the owner set on "matplotlib's data outside the zip"
  (`2026-10-16-what-matplotlib-needs.md`, "The owner's decisions"):
  the data must not weaken the separation of the runtime from the host
  filesystem, and there must be no other way to include it.
- **Stands on:** `2026-10-16-what-matplotlib-needs.md` finding 6.1 (the
  zip finding); spec 001 Decision 3 (how the runner places the zip);
  spec 003 Decisions 6 and 9 (the snapshot, and its pairing with the
  zip); the spike memo, finding 7 (wasi-libc's preopen table is
  snapshotted).

## The question

matplotlib needs its package data at run time. That is `mpl-data/`
(9,912 KB in the 3.11.2 wheel, 204 files; 8,872 KB of it fonts) and
the `matplotlibrc` inside it. It reads them with plain `open()`, and it
finds them at `Path(matplotlib.__file__).with_name("mpl-data")`. So
the data cannot stay inside the stdlib zip.

Two questions follow:

1. In what ways could the data reach the guest?
2. How safe is each way? Can the guest reach anything outside its
   preopens (security against the host)? Can one run tamper with data
   another run reads (security between runs)?

A **preopen** is a host directory the embedder hands to the guest under
a guest path; under WASI preview1 it is the only way a guest sees any
file.

## Method

- **Read:** the constitution, `AGENTS.md`, spec 001 Decision 3, spec
  003 Decisions 6, 7 and 9, `src/wasi_python/runner.py`,
  `scripts/steps/80_snapshot.sh`, and the matplotlib memo.
- **Read in prior art** (commits as recorded in
  `context/prior_art/README.md`):
  - wasi-libc `165235b`: `libc-bottom-half/sources/preopens.c` and
    `headers/public/wasi/libc.h`;
  - wasmtime `2d9c19b`: `crates/c-api/src/wasi.rs:312-337`,
    `crates/wasi/src/ctx.rs:296-317`, `crates/wasi/src/filesystem.rs:102-116`;
  - wasmtime-py `280ce73` and the installed `wasmtime` 49.0.0 in `.venv`;
  - wizer `6130150`: `src/bin/wizer.rs:207-220`;
  - wasi-virt `448f6df`: `README.md`;
  - webassembly-language-runtimes `5a40c30`: its wasi-vfs helper and
    `python/v3.12.0/wlr-build.sh`;
  - pyodide `6754c1f` and pyodide-recipes `01bd0af`: how Pyodide
    installs a package and ships matplotlib's data.
- **Read outside the repository:** matplotlib 3.11.2's sdist and wheel,
  already in the session scratchpad from the matplotlib memo (hash
  checked there). And the wasi-vfs README on GitHub
  (`kateinoigakukun/wasi-vfs`), through a web fetch. wasi-vfs was not
  cloned: cloning would mean editing `context/prior_art/README.md`,
  which was out of bounds for this task.
- **Executed, in a scratch directory only** (no tracked file changed).
  The tools were the repository's pinned ones: wasi-sdk 24, Wizer
  11.0.3 and wasmtime-py 49.0.0, all through `uv run`. The runs:
  - **A toy guest.** A tiny C reactor (`guest.c`, about 80 lines). It
    stats a path in `wizer.initialize`, which fills wasi-libc's preopen
    table, and optionally calls `__wasilibc_reset_preopens()` after
    that. In `run` it reads, writes and escapes. It was snapshotted with
    one preopen (`/`) and with two (`/`, then `/data`), and run under
    wasmtime-py with the preopens given in different orders. The data
    preopen was read-only. Both preopens held decoys: a `data/x.txt` in
    the root, and in the data directory a relative and an absolute
    symbolic link to a host "secret".
  - **The real artifacts.** `build/artifacts/python.wasm` and
    `python-snapshot.wasm` were run with the root at `/` and a second,
    read-only preopen. A scratch Wizer snapshot of the real reactor was
    also taken with two preopens (`out/python-snapshot-2pre.wasm`, made
    with step 80's flags plus a second `--mapdir`) and run the same way.
  - **Costs.** The host cost of copying, hashing and checking
    `mpl-data` per root. The guest's fuel to unpack it, or read it,
    from a zip.
  - **Host file modes.** What a guest can still do to data in its root
    that the host made read-only.

## Findings

### 1. The second preopen works, and read-only holds (EXECUTED)

wasmtime-py 49.0.0's `WasiConfig.preopen_dir(path, guest_path,
fs_mutable=True)` takes a read-only flag. Its docstring still talks
about `dir_perms` and `file_perms`, which it no longer has
(`uv run python -c "import inspect, wasmtime; print(inspect.signature(wasmtime.WasiConfig.preopen_dir))"`
→ `(self, path: str, guest_path: str, fs_mutable: bool = True)`).
Under it, the C API maps `false` to `FsPerms::ReadOnly`, which opens
the directory with `OpenMode::READ` only (READ: wasmtime
`c-api/src/wasi.rs:328-336`, `wasi/src/ctx.rs:303-306`).

The guest runs on the real plain reactor, with a second preopen,
read-only, at `/usr/local/share/wasi-python`:

```
ok  ## REAL matplotlibrc from the read-only preopen      open(p).readline()
ok  True                                                 os.path.isfile(p)
err PermissionError [Errno 63] ...matplotlibrc           open(p, "a")
err PermissionError [Errno 63] .../new                   open(new, "w")
err PermissionError [Errno 63] ...matplotlibrc           os.remove(p)
err PermissionError [Errno 63] .../d                     os.mkdir
err PermissionError [Errno 63] .../../../../etc/passwd   escape by ".."
err PermissionError [Errno 63] .../out                   a symbolic link to a host file outside
host data after: ['mpl-data', 'out']                     (unchanged)
```

The toy guest showed the same refusals for every operation it tried,
with errno 63. Those were: create, append, unlink, mkdir, rename,
symlink, and `utimensat`. The escapes were refused too: `..`, a relative
link out of the directory, and a link with an absolute host target. A
link made in the root that points at `data/x.txt` stays inside the
root, so a link cannot cross from one preopen to another. With the same
data directory given writable, create, append and unlink succeeded.
The guest's own reads and writes behave like native Python's.

**The guest cannot tell read-only from writable (EXECUTED).** For a
read-only preopen and a writable one, `fd_fdstat_get` gives the same
rights: base `0x7b7fe00`, inheriting `0xff7ffff`. So the read-only
property is wholly the embedder's to set. The guest cannot check it.

**The wasmtime CLI 49 has no read-only flag for `--dir` (EXECUTED,
`wasmtime run --help`).** The CLI is not an embedding path anyway
(spec 001 Decision 2). Embedding APIs have the flag. Bindings built on
the C API carry `fs_mutable` (READ, `wasi.h:230-238`). Other runtimes
are not checked here.

### 2. The snapshot sees only the preopens it was taken with (EXECUTED)

`__wasilibc_populate_preopens` walks the descriptors from 3 upward
once, and stores each preopen's name and number in memory. It then
sets `preopens_populated` and never looks again (READ: `preopens.c:309-388`).
Wizer snapshots that memory. A path goes to the preopen with the
longest matching name (`preopens.c:260-305`), and the number used is the
one frozen at build time. Wizer gives the descriptors in `--dir` order
first, then in `--mapdir` order (READ: `wizer.rs:207-220`).

Five cases, run on the toy guest and on the real artifacts:

| snapshot taken with | runtime gives | result |
|---|---|---|
| `/` only (today's `python-snapshot.wasm`) | `/`, then data (read-only) | **the second preopen is ignored.** `/usr/local/share/wasi-python/mpl-data/matplotlibrc` read the copy a guest had planted in its root (`## PLANTED by a guest in the root`). Writes to that path succeeded and landed in the root (`root share after: ['d', 'mpl-data', 'new']`). |
| `/`, then data | `/`, then data | works. Data is read-only, and escapes are refused (finding 1). |
| `/`, then data | data, then `/` | **the two are swapped.** Root paths went to the data directory, and data paths went to the root, writable. |
| `/`, then data | `/` only | data paths fail with `EBADF` (errno 8). Root paths and programs that do not touch the data run normally (exit 0). |
| any, with `__wasilibc_reset_preopens()` at the end of `wizer.initialize` (toy only) | either order | works. The table is rebuilt at run time from the names the runtime gives, as on the plain reactor. |

Note row 1. The current snapshot silently ignores any preopen an
embedder adds, while the plain reactor honours it (EXECUTED: the same
program on `python.wasm` read the real file). The two artifacts already
behave differently here.

`__wasilibc_reset_preopens` is in wasi-sdk 24's `libc.a` (EXECUTED:
`llvm-nm` shows `T __wasilibc_reset_preopens`). wasi-libc documents it
as meant to be called "just prior to snapshotting the guest state so
that it can be resumed on another runtime" (READ: `libc.h`, current
wasi-libc). SDK 24's header does not declare it. A recipe could declare
it, since calling a libc function from `recipes/reactor_main.c` is a
recipe and not a patch. Whether CPython keeps a descriptor open across
the snapshot was not tested on the real reactor (see "Where it
stopped").

### 3. A guest path under the zip's name needs no hook (EXECUTED)

A preopen's guest path can be any string. Take a module in the zip:
its `__file__` is `/usr/local/lib/python314.zip/<pkg>/…` (EXECUTED:
`decimal.__file__` → `/usr/local/lib/python314.zip/decimal.pyc`). So
for matplotlib in the zip, `get_data_path()` is
`/usr/local/lib/python314.zip/matplotlib/mpl-data`. A read-only preopen
at exactly that guest path, run on the plain reactor, gave:

```
/usr/local/lib/python314.zip/decimal.pyc        imports still come from the zip
REAL rc True ['matplotlibrc']                   open, isfile, listdir under the preopen
True True                                       Path(...).is_dir(); the zip is still a file
write: PermissionError
```

So matplotlib's `.pyc` can stay in the stdlib zip, and its data can
come from the second preopen. No hook is needed, matplotlib is not
patched, and nothing on `sys.path` changes.

This guest path also closes the gap a missing preopen would leave.
Inside the root, a path under `python314.zip/` cannot resolve: the zip
is a regular file in the way. The runner replaces anything a guest
leaves in the zip's place (spec 001 Decision 3). So a guest cannot
plant a stand-in for the data in its root. Under
`/usr/local/share/...` it could, as row 1 of finding 2 shows. (This is
INFERRED from the two EXECUTED facts: the file is in the way, and the
runner replaces it.)

### 4. Host file modes do not protect data inside the root (EXECUTED)

Data was placed in the root as a `0444` file in a `0555` directory, and
the plain reactor was run on it. Writing, removing and creating were
refused (`Permission denied`). But three things succeeded: `os.utime`
on the file, renaming the read-only directory away (its parent is the
guest's), and making a new directory in its place with a planted
`matplotlibrc`. The next read returned `PLANTED`. So inside a writable
root, only re-checking on every call protects the data. File modes do
not.

### 5. The candidates

Each candidate is checked on six points: snapshot, host, between runs,
cost, embedders, and the constitution.

#### C1. The folder in the guest's root, placed by the runner like the zip

- **Snapshot:** works. It is one preopen, as today. The files must sit
  at the paths the snapshot saw (the matplotlib memo, 6.3).
- **Host:** safe, if placement follows spec 001's rules: copies and not
  links, real directories only, links never followed. A hard link
  would let a guest write the shared master. Spec 001's landing notes
  showed exactly this escape for the zip (READ).
- **Between runs:** the guest owns its copy and can rewrite it, or
  rename and replace it (finding 4). On a root shared one call at a
  time, a run sees what the last run left, unless the runner checks
  the whole tree before every call. "The whole tree" means 204 files
  and 10 directories: no extra entries, no links, and every byte. Today
  it checks one file.
- **Cost (EXECUTED; a benchmark, M-series macOS, CPython 3.14.2, median
  of 7):**
  - a first placement (`copytree`) took 56.6 ms;
  - a full SHA-256 of all 204 files took 8.0 ms;
  - an `lstat` of all 204 took 0.33 ms;
  - each root grows by 9.6 MB, beside the 10.5 MB zip.
- **Embedders:** they lay out a tree instead of one file, and must
  re-check it each call or give each untrusted program a fresh root.
- **Constitution:** kept. The artifact set and the root layout change
  (§4.6, spec 003 Decisions 7 and 9, the runner).

#### C2. A second, read-only preopen shared by all runs

- **Snapshot:** works when Wizer is given the same preopens in the same
  order as the runtime (finding 2). Otherwise it fails closed
  (`EBADF`), or it swaps the two when the order is wrong. With
  `__wasilibc_reset_preopens()` at the end of `wizer.initialize`, order
  stops mattering. That is EXECUTED on the toy guest, not yet on the
  real reactor.
- **Host:** the guest reads only that directory. Escapes by `..`,
  relative links and absolute links are refused (EXECUTED). It is no
  new channel: it is the same WASI preview1 filesystem calls the wall
  already allows, so it is not a third import. The embedder must
  preopen the data directory itself. Preopening a parent would show
  everything under the parent.
- **Between runs:** no run can change it. Every write operation is
  refused (EXECUTED), so concurrent and later runs read the same
  bytes, with no per-call check. One hazard is the embedder's: a
  writable mount would let one run change the data for all later runs,
  and the guest cannot detect that (finding 1). The data is the
  artifact set's own files, trusted as `python.wasm` is. A runner may
  hash it once per process (8 ms, EXECUTED as above).
- **Cost:** no copy and no check per call. Reads cost the same as from
  any directory: reading all 204 files took 17 M fuel above the baseline
  (EXECUTED, row "read-all-from-dir" in C4). On disk it is 9.6 MB once
  per install, not per root. The wheel grows by about 4.9 MB deflated
  (EXECUTED: `zip -9 -r` of `mpl-data` → 4,851,866 bytes).
- **Embedders:** the contract grows. Today it is "preopen a directory
  at `/`". It becomes "and, for matplotlib, preopen the artifact set's
  data directory read-only at
  `/usr/local/lib/python314.zip/matplotlib/mpl-data`". An embedder that
  never imports matplotlib can leave it out: programs that do not touch
  the data run normally (EXECUTED, row 4 of finding 2).
- **Constitution:** this needs the owner. §2.4 says "by preopening a
  directory", and §4.6 lists the artifact set. Both would gain the data
  directory. §4.4 (two imports) is kept, and so are zero patches.

#### C3. Data built into the binary

- **wasi-virt** is a WASI preview 2 component tool ("Virtualization
  Component Generator for WASI Preview 2"; READ, its `README.md`). It
  does not apply to a `wasm32-wasip1` core module. Rejected by
  constitution §4.3.
- **wasi-vfs** is preview1. Its static library defines the WASI import
  symbols wasi-libc calls, so the linker emits no import for them; its
  `pack` command is "a wrapper of `wizer`" that copies mapped
  directories into "a read only file system embedded in the `.wasm`
  binary". It is Apache-2.0 (READ: its README; WLR's Python 3.12 build
  links `-lwasi_vfs` and runs `wasi-vfs pack --mapdir /usr::…`).
  - **Host and between runs:** this would be the strongest isolation.
    No host directory is involved, and each instance gets a fresh copy
    in its own memory (INFERRED).
  - **Contract:** unchanged, still one preopen.
  - **Costs** (INFERRED, not built or measured here):
    - the binary and the snapshot grow by about 9.6 MB (fonts barely
      deflate);
    - a new dependency inside the guest, a Rust library that
      intercepts every WASI call, the root's included;
    - a Rust toolchain and its crates to pin, to build it from source
      (§4.2, §4.8);
    - its interaction with the reactor's four `--wrap` flags and with a
      second Wizer pass is untested.
  - **Verdict:** it is another way, but it is unproven here and costs
    more build and more trusted code than C2.
- **Without a filesystem.** FreeType could read from memory:
  `FT2Font` accepts a binary file-like object (READ:
  `ft2font_wrapper.cpp:568-586`). But matplotlib never passes one. Two
  things block it:
  - `rcParamsDefault` always reads `get_data_path()/matplotlibrc` at
    import (`__init__.py:992-996`). `MATPLOTLIBRC` only adds a user file
    on top (`matplotlib_fname`, `__init__.py:643-684`).
  - `font_manager` passes path strings to `FT2Font` and checks
    `os.path.isfile` (`font_manager.py:1699`).

  So the filesystem cannot be avoided without changing how matplotlib
  opens files, which is C5.

#### C4. Unpacking from a zip at first use, inside the guest

The guest copies the data from a zip into its root itself. This is the
pattern Pyodide uses: it unpacks each package archive into its
in-memory filesystem when the package loads (READ:
`pyodide/src/js/load-package.ts:504-538`,
`_package_loader.py:190`).

- **Cost (EXECUTED; `wasi_python.run(..., fuel=10**12)` on the
  snapshot, with the 4.85 MB `mpl-data.zip` in the root):**

  | program | fuel | wall |
  |---|---|---|
  | `pass` | 117,638,725 | 20 ms |
  | unpack all 204 files (`extractall`) | 748,335,504 | 173 ms |
  | read all from the unpacked directory | 134,983,816 | 58 ms |
  | read all from the zip | 714,465,452 | 79 ms |

  Unpacking costs about 630 M fuel per fresh root, which is 5.4 times
  a bare start.
- **Host:** safe, as C1.
- **Between runs:** worse than C1. The unpacked files are guest-written
  in a writable root, and a later run trusts them unless it hashes them
  inside the guest, which costs fuel on every call.
- **Embedders:** the data zip must reach the guest anyway, in the root
  or in the stdlib zip.
- **Verdict:** rejected. It costs more than C1, with the same tamper
  exposure.

#### C5. A runtime hook in the reactor's bootstrap

There are two forms:

- **(a) A loader that lies about `__file__`.** It is feasible, but it
  only moves the data to another real directory. It does not remove
  the need for a folder.
- **(b) A Python layer that makes paths under the zip look like
  files.** It would wrap `io.open`, `builtins.open`, `os.stat`,
  `os.path.isfile`, `os.listdir`, `os.scandir` and `os.walk`. It is
  feasible in principle, because every matplotlib data read goes
  through Python, FreeType's included (finding 6.1 of the matplotlib
  memo).

Form (b) is a patch in disguise. It changes `open()` and `os` for every
program, against constitution §4.11 ("platform semantics are
documented, not disguised"). It is fragile across matplotlib and
CPython releases. It also costs about 35 times the fuel per byte read:
597 M against 17 M above the baseline for all 204 files (EXECUTED, the
table above). Rejected.

#### Also considered

- **The door.** Serving the data through `host::call` is not an
  option: frames are opaque to this project and mean what the embedder
  says (constitution §4.4). Rejected.
- **Copy-on-write clones** (APFS `clonefile`, Linux `FICLONE`) would
  make C1's copy cheap where the filesystem supports them. They do not
  change C1's security, and Windows mostly lacks them. INFERRED.

### 6. Matplotlib already reads one file from the guest's root (READ)

`matplotlib_fname()` tries `./matplotlibrc` first, then
`$MATPLOTLIBRC` and `$MPLCONFIGDIR` (`__init__.py:662-684`). With the
working directory at `/`, a run on a shared root can leave a
`matplotlibrc` that the next run applies on top of the defaults. That
happens in every candidate. It is the same class of exposure spec 001
already names for a shared root, and the answer is the same: one root
per untrusted program, or calls one at a time. It is not a reason to
prefer one candidate over another.

## What it decides

**Recommendation: C2.** Ship `mpl-data` as a read-only directory in the
artifact set. Preopen it as a second preopen at
`/usr/local/lib/python314.zip/matplotlib/mpl-data`. Keep matplotlib's
`.pyc` in the stdlib zip.

The owner's first condition holds. Read-only is enforced by the
runtime: every write was refused. The guest cannot leave the directory:
`..` and both kinds of link were refused. No run can change what another
run reads. No third import is added. The data never touches the
guest's writable root, so the runner gains no per-call check and no
per-root copy. And the guest path under the zip's name cannot be faked
from inside the root.

The owner's second condition holds in part:

- C1 also works. It is safe against the host, but between runs it
  needs a whole-tree check on every call, and it costs about 57 ms and
  9.6 MB per root.
- C4 and C5 are worse: more fuel, and a weaker defence (C4) or a
  disguised patch (C5).
- **C3 through wasi-vfs is a real alternative.** It keeps the
  one-preopen contract, at the price of a new in-guest dependency, a
  Rust toolchain to pin, and an unproven fit with the reactor and
  Wizer. If the owner values the one-preopen contract above those
  costs, a short experiment should decide C3 before the specification
  is written.

What the specification must then decide, from these findings:

1. **The snapshot and the preopens are a pair, as the snapshot and the
   zip are.** Prefer calling `__wasilibc_reset_preopens()` at the end of
   `wizer.initialize`, so the snapshot honours the runtime's preopens by
   name and in any order, as the plain reactor does today. This needs
   one confirming build. If it fails, freeze `/` then the data preopen,
   in that order, record both in `MANIFEST`, and have `run` check the
   two names before Python starts (fail closed).
2. **The runner** preopens the data directory with
   `fs_mutable=False`, from the artifact set's own copy, and never
   writable.
3. **The README states the hazard** that the guest cannot detect: a
   writable data mount lets one run change the data for every later
   run.
4. **The contract change goes to the owner.** Constitution §2.4 and
   §4.6 gain an optional, read-only data directory. A check
   (`test_runner_keeps_the_data_read_only`) asserts the refusals of
   finding 1 before any code.

## Where it stopped

- `__wasilibc_reset_preopens()` was proven on the toy guest only. On
  the real reactor it needs `recipes/reactor_main.c` changed and
  relinked, which this task could not do. The experiment: add the
  call, run step 80, and run the judge and finding 1's script with the
  two preopens in both orders.
- wasi-vfs (C3) was read from its README, not built.
- Windows was not run. cap-std confinement and wasmtime's read-only
  mode are platform-neutral in the source (READ), but that is not an
  execution.

## One line

Give matplotlib's data its own read-only preopen at the path matplotlib
already looks in. The runtime refuses every write and every escape, no
run can touch another's data, and nothing is copied or checked per
call; the price is a second, optional preopen in the embedder's
contract, which is the owner's to approve.
