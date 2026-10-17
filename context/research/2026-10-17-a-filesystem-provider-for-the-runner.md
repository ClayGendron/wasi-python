# A filesystem provider for the runner

- **Status:** research, 2026-10-17. It commits the project to nothing. It recommends a design and
  a first milestone for the specification that question 13 calls for.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5). It wrote none of the code or documents it reads,
  here or in vfs. vfs was read, never edited. Box: one session. It stopped where "Where it
  stopped" says.
- **Feeds:** the filesystem-provider specification (question 13: "converge on our runner, but do
  not edit vfs"); the async host function specification (question 15); the embedder contract's
  conformance job (`2026-10-17-the-runtime-for-agent-code.md` §5 item 7).
- **Stands on:**
  - `decisions.md` 13 and 37 (vfs runs its guests through `wasi_python.run`, which needs "a
    filesystem provider in the runner (the guest's file calls served by embedder code, as vfs's
    169b shim does), researched first"; tools are counted and their outcomes recorded), 15
    (async host functions, under the call's deadline), 17 (governance left to embedders; the
    runner offers "grants, the gated tool protocol, a filesystem provider") and 24 (nothing
    writable by default);
  - constitution §4.4 (two channels, no third import), §4.5 (embedder-neutral), §4.9 (tests
    count) and §4.15 (safe by default);
  - `2026-10-17-the-runtime-for-agent-code.md` §5 item 8, which asked for this memo "with an
    experiment";
  - `2026-10-16-a-principal-engineers-direction.md` layer 3, which shadowed `path_open` once;
  - specs 011 (shared host functions, found by the thread's call stack), 015 (`cancel`,
    `run_async`), 017 (typed grants), 024 and 025;
  - `src/wasi_python/runner.py` as of commit `88d71c4`.

## Terms

- **Provider:** an object the embedder passes that answers file operations from its own code:
  a database, an object store, a permission layer. Its authority is bound in by the embedder
  before the call, as vfs binds an `Authority` into `Fs` (vfs ADR 082 pin 2).
- **Mount:** a provider placed at a guest path, as a grant places a host folder.
- **Shadow:** a host function defined over one of wasmtime's own WASI functions, through
  wasmtime-py's `Linker.allow_shadowing`. The runner already shadows `poll_oneoff`
  (`runner.py:1946-1951`).
- **Forward:** a shadow handing a call it does not own back to wasmtime's own WASI.
- **Trampoline:** a tiny wasm module, made by the runner, whose functions call wasmtime's WASI.
  It is how a forward reaches wasmtime (finding 3).
- **Placeholder:** an empty, read-only folder the runner owns. Each mount is preopened on it,
  so wasmtime's own fd table holds a number for every provider fd (finding 4).
- **Staging:** reading a whole file into host memory at open, serving reads and writes from
  that buffer, and writing it back at close. vfs's 169b does this (`169…/spec.md:392-421`).

## Labels

Each claim is **EXECUTED** (run here, with its script and output in
`2026-10-17-a-filesystem-provider-for-the-runner/`), **READ** (cited by path and line; vfs
paths are under `/Users/claygendron/Git/repos/vfs/context/`, prior art under
`context/prior_art/` at the commits its README records) or **INFERRED** (reasoned from the
two). Times are benchmark facts on one machine, which was also running another review; they
are noisy and nothing should assert them.

## Method

- **Read:** the files named in "Stands on"; in vfs, spec 169 slice 169b
  (`specs/active/169-programs-the-index-and-the-vfs-views/spec.md:319-612`), ADRs 082, 084 and
  086, spec 172 (`specs/active/172-the-wasi-python-runtime/spec.md`) and study 04
  (`research/studies/2026-10-15-agent-shell/04-filesystem-over-the-sandbox-boundary.md`); in
  wasmtime v49, `crates/wasi/src/p1.rs`, `crates/wiggle/generate/src/wasmtime.rs` and
  `crates/c-api/include/wasi.h`; wasmtime-py 49.0.0's `_func.py` and `_linker.py`.
- **Ran,** under wasmtime-py 49.0.0 and Python 3.14, on a copy of `build/artifacts/` in the
  session scratchpad (SHA-256: snapshot `c7302cfd…`, plain `4befe9de…`, zip `1add57e4…`).
  Nothing ran the judge or the build. From the repository root, with `D` this memo's folder:
  - `uv run --no-sync python $D/imports.py ART` → `imports.txt`: the guest's imports.
  - `$D/shadow.py ART SCRATCH MODE PROGRAM`: a model of the recommended design, outside the
    runner. Modes `plain` (today), `passthru` (every file call shadowed and forwarded) and
    `provider` (as passthru, plus an in-memory provider at `/work` beside a real read-only
    grant at `/data`). Outputs: `provider.txt` (snapshot) and `provider-plain.txt` (plain
    reactor) with `files.py`; `bench.txt` with `bench.py`; `micro.txt` from `sh $D/micro.sh`.
  - `$D/cost.py SCRATCH` → `cost.txt`: one crossing, five ways, on a 30-line guest.
  - `$D/async_cancel.py` → `async_cancel.txt`: an async provider, a cancel and a deadline while
    inside it. (Run inside `faulthandler.dump_traceback_later(20)`, after a first version hung;
    finding 8 says why.)
  - `$D/dot_path.py ART` → `dot_path.txt`: what wasi-libc and wasmtime do with `.` and `..`.

## Findings

### 1. The guest imports 26 file calls; a CPython program calls about 14 of them (EXECUTED)

`imports.txt`: both binaries import 43 functions: `host::call` and 42 from
`wasi_snapshot_preview1`. Of the 42, 28 take a file descriptor or a path. Two of those,
`fd_prestat_get` and `fd_prestat_dir_name`, are the preopen scan, which wasmtime can keep
answering (finding 4). That leaves **26 calls a provider layer must own**:

- 16 on a descriptor: `fd_advise`, `fd_close`, `fd_datasync`, `fd_fdstat_get`,
  `fd_fdstat_set_flags`, `fd_filestat_get`, `fd_filestat_set_size`, `fd_filestat_set_times`,
  `fd_pread`, `fd_pwrite`, `fd_read`, `fd_readdir`, `fd_seek`, `fd_sync`, `fd_tell`,
  `fd_write`;
- 10 on a path: `path_create_directory`, `path_filestat_get`, `path_filestat_set_times`,
  `path_link`, `path_open`, `path_readlink`, `path_remove_directory`, `path_rename`,
  `path_symlink`, `path_unlink_file`.

Not imported: `fd_renumber`, `fd_allocate`, `fd_fdstat_set_rights`. So the hardest fd-table
operation, renumbering, never arises. `poll_oneoff` is already the runner's
(`runner.py:2061-2092`); the four `sock_*` calls on a provider fd reach wasmtime, which sees an
empty folder and refuses (INFERRED).

`provider.txt`: a program that reads a real grant, then writes, appends, renames, lists, stats
and removes files on the provider, made 69 shadowed calls on the snapshot, using 14 distinct
calls: `fd_close`, `fd_fdstat_get`, `fd_filestat_get`, `fd_read`, `fd_readdir`, `fd_seek`,
`fd_tell`, `fd_write`, `path_create_directory`, `path_filestat_get`, `path_open`,
`path_remove_directory`, `path_rename`, `path_unlink_file`. `micro.txt` adds `fd_pread`. This
matches vfs's study 04, which found CPython 3.12 called 22 preview1 functions, file and
non-file, and that "the union of what all three [guests] actually called is the memo's 24 names"
(`04-…md:20-39`, EXECUTED there). The other ten of the 26 still need a defined answer.

### 2. Shadowing wasmtime's file calls works beside its own WASI, on both binaries (EXECUTED)

`shadow.py` defines `define_wasi()`, sets `allow_shadowing`, then defines all 26 file calls as
Python functions. Every call on a provider fd is served by the provider. Every other call is
forwarded to wasmtime. Results:

- **Snapshot** (`provider.txt`) and **plain reactor** (`provider-plain.txt`): exit 0, the same
  output. The real grant at `/data` read its CSV. `/work` held the provider's seed file; the
  program made a folder, wrote JSON, appended, renamed, listed, stat-ed, read it back equal,
  removed the file and the folder.
- **The real grant stayed read-only:** `open("/data/new.txt", "w")` gave errno 63, wasmtime's
  answer, through a forwarded `path_open`.
- **A refused write-back reached the guest:** the provider refused `denied.txt` at close; the
  guest's `with` block raised `PermissionError` (errno 2), and the model recorded
  `[('denied.txt', 2)]` although the program went on to exit 0. That is vfs's rule, "a refused
  write-back is never silent" (`169…/spec.md:400-412`).
- **Escapes were refused:** `/work/../data/in.csv` and `/work/out/../../etc` gave errno 63.
- **The placeholder stayed empty** after every run.

So mixing wasmtime's WASI with overrides is allowed and works: option (a), "shadow only some
calls alongside wasmtime's WASI", is real. Option (a) "define all of preview1 ourselves" is not
needed: the 14 non-file calls (args, environ, clocks, random, `proc_exit`, `sched_yield`,
`sock_*`) and the preopen scan stay wasmtime's.

### 3. A forward needs a trampoline that re-exports the guest's memory (READ, EXECUTED)

- **READ:** wasmtime's preview1 functions find guest memory by asking the *calling instance*
  for its `memory` export (`wasmtime-v49/crates/wiggle/generate/src/wasmtime.rs:118-132`:
  `caller.get_export("memory")`, else "missing required memory export"). A Python shadow
  cannot call wasmtime's original function directly: the original is not reachable through
  the shadowing linker, and a call from Python has no calling instance.
- **EXECUTED:** a second, plain linker (`define_wasi()` only) supplies the originals. A
  trampoline module imports them and `env.memory`, re-exports that memory as `memory`, and
  exports one forwarder per call (`local.get`… `call`). It is instantiated per store, after the
  guest, with the guest's own memory (`shadow.py`, `trampoline_wat`). wasmtime's WASI then
  reads and writes the guest's buffers directly, with no copy, and uses the store's one WASI
  context, so stdin, stdout, grants and the zip behave as today.
- **Fuel:** a forward costs the trampoline's own instructions: 4 per 2-argument call
  (`cost.txt`: 18.0 against 14.0 per loop round), about 7 per 5-argument call (`micro.txt`:
  352.5 M against 352.3 M fuel for 40,000 calls).

### 4. wasmtime's fd table must stay the only numbering (READ, EXECUTED)

- **READ:** wasmtime v49 hands out a freed number first, else one above the highest in use
  (`crates/wasi/src/p1.rs:434-466`, `unused` and `push`). It does not know about numbers
  anyone else hands out. A provider that picked its own numbers would collide with wasmtime's
  next `path_open`.
- **READ:** wasi-libc finds preopens by asking `fd_prestat_get` for 3, 4, 5… until `EBADF`
  (study 04 finding 2, `04-…md:41-49`, EXECUTED there). A mount must therefore be a real,
  contiguous preopen number.
- **EXECUTED, the answer:** each mount is `preopen_dir(placeholder, guest_path, False)`, on an
  empty folder the runner owns. wasmtime answers the preopen scan with the mount's guest path,
  with no shadow. For each file the provider opens, the runner reserves a number by calling
  wasmtime's own `path_open(dir, ".", O_DIRECTORY)` through a second small module with its own
  memory (`shadow.py`, `RESERVE_WAT`), and releases it with `fd_close`. Every provider fd is
  then a real wasmtime descriptor on an empty read-only folder, mapped in the runner's table to
  its staged file.
- **Why this is also a safety net (INFERRED):** if a shadow ever forwarded a provider fd by
  mistake, the guest would see an empty, read-only, runner-owned folder, nothing more.
- **The snapshot needs nothing new:** it forgets Wizer's preopens and rebuilds the table by
  name on first use (`recipes/reactor_main.c:203-206`, spec 006). `/work` appeared on both
  binaries (EXECUTED, finding 2). vfs's spec 172 expected the snapshot's preopen to be "baked at
  snapshot time" (`172…/spec.md:123-125`); with this project's artifacts it is not.

### 5. What a crossing costs (EXECUTED; times are benchmark facts)

`cost.txt`, 100,000 calls of `fd_fdstat_get(1)` from a wasm loop, best of three:

| how the call is answered | fuel per call | µs per call |
|---|---|---|
| wasmtime's own WASI (today) | 14.0 | 0.16 |
| a Python shadow that returns at once | 14.0 | 9.4 |
| a Python shadow that writes a 24-byte answer (a provider fd) | 14.0 | 18.1 |
| a forward through `Func.__call__` | 18.0 | 39.5 |
| a forward through a cached `wasmtime_func_call` | 18.0 | 13.2 |

- **Entering Python costs about 9 µs** in wasmtime-py's trampoline, whatever the shadow does.
- **`Func.__call__` is slow because it looks up the type and converts every argument each
  time** (`wasmtime/_func.py:59-104`). A forward that keeps its argument array and calls
  `_ffi.wasmtime_func_call` directly is three times faster. The runner already depends on
  `_ffi` for the epoch deadline (`runner.py:1785-1795`, `1844-1849`) under the `<50` pin.
- **On real programs:** `bench.txt` (imports of seven modules the snapshot did not load, then
  2,000 printed lines) made 489 shadowed calls, all forwarded: 68 opens of the zip, each with a
  `fd_fdstat_get`, `fd_filestat_get`, `fd_seek`, `fd_tell`, `fd_read` and `fd_close`. The run
  took 0.10–0.17 s plain and 0.15 s shadowed with `Func.__call__`. With the cached call that is
  about 489 × 13 µs ≈ 6 ms (INFERRED).
- **Real host files are slower than shadows:** `micro.txt`, 20,000 `os.stat` and 20,000
  `os.pread` on a real grant: 1.6–3.6 s plain (40–90 µs a call), 7.3–8.2 s forwarded by
  `Func.__call__`. On a provider in memory: 1.0–1.1 s (about 25 µs a call).
- **Runs without a mount pay nothing** if the shadowing linker is a second linker used only
  when mounts are given (INFERRED; `plain` mode is today's linker, and its fuel and calls are
  today's).

### 6. A whole-file interface keeps untrusted input away from the provider (EXECUTED, INFERRED)

The model's provider has eight methods on normalized paths: `stat`, `list`, `read`, `write`,
`mkdir`, `remove`, `rmdir`, `rename` (`shadow.py`, `MemoryProvider`). Everything else is the
runner's: descriptors, offsets, seeks, appends, truncation, `iovec`s, directory cookies, rights,
flags and errno encoding (`shadow.py`, `Shim`, about 250 lines). The program in finding 2 used
it all through those eight methods (EXECUTED). The provider never sees an offset, a flag, a
pointer or a raw path.

This is vfs's own conclusion: "the filesystem ABI we should expose to every guest kind is the
vfs verb set itself, not POSIX" (`04-…md:14`), with whole-file staging (`04-…md:51-81`) and at
most one verb per open (`169…/spec.md:365-390`). It is also the shape of Monty's `AbstractOS`
(`04-…md:277`, READ there). The model spent two provider calls per open (`stat`, then `read`:
10 stats and 3 reads for 12 opens, `provider.txt`); 169b's table shows one is enough, by
classifying `read`'s own error (INFERRED, `169…/spec.md:365-390`).

What staging costs: a 1-byte read stages the whole file, and buffers live in host memory
outside the store's memory limit (study 04, `04-…md:265`). A write at a huge offset would grow
a buffer without bound. Both need a bound (vfs: `STAGING_BYTE_BUDGET`, `FBIG`,
`169…/spec.md:497-500`).

### 7. Paths: wasi-libc does not normalize `.`, and wasmtime answers 63 for an escape (EXECUTED)

`dot_path.txt`, with a private root: `/usr/local/lib/python315.zip` opened;
`/usr/local/./lib/python315.zip` and `/usr/./local/lib/python315.zip` gave `ENOENT`, because
wasi-libc matched the root `/`, not the zip's preopen, by text; `/usr/local/lib/../lib/…` gave
errno 63 (`EPERM`), wasmtime's answer for a path that leaves its preopen even for a moment.

- **Parity:** a provider must answer as a grant does: 63 for an escape (the model first
  answered 76, `NOTCAPABLE`, as vfs's 169b and study 04 do; it was changed and re-run), and 63
  for a write on a read-only mount (finding 2's grant).
- **The runner normalizes, the provider never does.** After normalizing, a provider path can
  name a place that a more specific preopen owns, such as `/usr/local/./lib` under a mount at
  `/`. Only the guest can spell that, and it fools only itself (INFERRED). The specification
  should still pick one rule; refusing such a path is the simple one.

### 8. Async providers, deadlines and cancel reach inside a provider call (EXECUTED)

`async_cancel.txt`: the guest runs on a worker thread, as `run_async` runs it; the event loop
runs on the main thread. The shadow posts the provider's coroutine to the loop
(`run_coroutine_threadsafe`) and waits in 10 ms slices, checking a cancel event and a deadline
between slices.

| trigger | guest saw | outcome | provider saw | stopped after |
|---|---|---|---|---|
| `cancel` set at 0.3 s | errno 11 (`ECANCELED`) | trap `INTERRUPT` | `stat cancelled` | 0.317 s |
| deadline 0.5 s | errno 11 | trap `INTERRUPT` | `stat cancelled` | 0.495 s |

- The coroutine received `CancelledError`, so vfs's verb would stop too.
- **Seen first (the hang):** a bare `(loop (br))` after the call never stopped. wasmtime keeps
  the epoch deadline in a local and reloads it at a function entry, so a deadline lowered by a
  host call is seen at the guest's next call. The runner's `_Call.stop` says the same
  (`runner.py:1785-1795`). CPython calls functions constantly; the fixed test guest calls one
  per round.
- **A sync provider cannot be interrupted** from the shadow (INFERRED): a blocked Python call
  holds the guest's thread. The runner can only check before and after it. vfs's ADR 084 states
  the same gap for its verbs: "The epoch deadline does not cover time inside a verb"
  (`084-…md:113-114`).
- **The tool memo's finding 5 applies here:** a stop recorded during a host call is reported by
  its raw error, not `"cancelled"` (`2026-10-17-a-tool-protocol-over-the-door.md:287-312`). The
  provider layer knows the reason, so it should record `call.ended` itself.

### 9. The other mechanisms (READ, INFERRED)

- **(b) A virtual directory through wasmtime:** none exists. `WasiConfig` offers
  `preopen_dir(path, guest_path, fs_mutable)` and custom stdout and stderr only (EXECUTED,
  `dir(wt.WasiConfig)`); the C API has the same list (`wasmtime-v49/crates/c-api/include/
  wasi.h`, `wasi_config_preopen_dir` at 235, no custom directory). Study 04 reached the same
  answer: "`WasiConfig` cannot be bent to a virtual store" (`04-…md:191-195`). Rejected.
- **(c) FUSE, a RAM disk, or materializing into a temporary folder:** FUSE and RAM disks touch
  the host system (a kernel extension or privileges on macOS, a mount on Linux, nothing on
  Windows) and break §4.8 and §4.15. Materializing is possible today with a writable grant, but
  copies everything before the run, sees writes only after it, and gives up per-access gating,
  which is what vfs wants (`decisions.md` 37; ADR 084 pin 1). Rejected as the mechanism; it
  stays the embedder's fallback.
- **(d) A guest-side shim** (a provider behind the tool protocol, with `open` and `os` patched
  in the guest): rejected as the mechanism. Patching covers Python-level calls only. C code
  opens files through wasi-libc and never sees the patch: `io.FileIO`, `os.open`, sqlite3,
  numpy's `.npy` path (`2026-10-17-numpy-npy-files-need-dup.md`), `os.scandir`. It would put
  file traffic on the door's frames, and depend on an optional, gated protocol. A
  verb-shaped guest API over the door (vfs's `vfs.read`, spec 172 §4) is still useful *beside*
  ordinary files; it is not a replacement for them.
- **(a) Define all of preview1 ourselves:** this is vfs's 169b ("bind every import the module
  declares", `04-…md:273`). In this runner it would replace wasmtime's audited handling of real
  grants, the zip and stdio with ours. Forwarding (finding 3) keeps wasmtime's. Rejected.

### 10. What vfs's 169b becomes on this runner (READ, INFERRED)

| 169b / 172 piece | on this runner |
|---|---|
| the 35 preview1 functions (`169…:333-349`) | the runner's provider layer (26 shadows) |
| one verb per open, staging, write-back at close and on every exit (`169…:365-421`) | the runner's, generic |
| refused write-backs recorded per run (`169…:400-412`) | `Completed`'s file record |
| text-or-bytes write-back, `/.vfs` hidden, the ladder as errno (`169…:351-363`, `413-421`) | vfs's provider |
| `ErrorKind` → errno (`169…:435-463`) | vfs's provider raises `OSError`; the runner encodes |
| one guest per process, single-thread executor (`169…:465-480`) | gone: the runner runs calls concurrently (spec 011) |
| context crosses the hand-off (`169…:474-480`) | `run_async` copies the caller's context (`runner.py:326`) |
| fuel, memory, epoch deadline (`169…:481-487`) | the runner's limits |
| `VERB_CALL_BUDGET`, `STAGING_BYTE_BUDGET` (`169…:489-505`) | the runner's file-call and staging limits |
| the staged-buffer cache for the zip row (`172…:126-135`) | moot: the zip is the runner's read-only grant (spec 017) |
| the door bound beside preview1 (`172…:136-139`) | the runner's `host=` (spec 001) |

## What must stay true, and how the design keeps it

- **No third import (§4.4).** The guest's imports do not change: the provider answers
  preview1 calls the guest already makes (finding 1). EXECUTED on both binaries.
- **The zip at `/usr/local/lib`.** Stays a real read-only grant, first among the preopens,
  answered by wasmtime through forwards. A mount at or under `/usr/local/lib` is refused, as a
  grant is (`runner.py:802-803`).
- **Identity checks for real grants.** Unchanged: grants are walked, judged and checked by
  identity after preopening (`runner.py:1339-1366`, `1370-1395`). The placeholder is a runtime
  folder like the zip folder: made private, checked by identity, and protected from every
  writable grant (`_runtime_folders`, `runner.py:1398`).
- **Deadlines, fuel and cancel.** Fuel counts only guest instructions, plus a few per forward
  (finding 3). A provider's time is outside the epoch; the runner checks before and after every
  provider call, and an async provider is waited on in slices (finding 8).
- **Concurrency (spec 011).** The 26 shadows are defined once per engine on a second linker,
  each in `_shared`'s form (`runner.py:1809-1841`): it serves the call on top of the thread's
  stack, only for that call's store, and never raises into wasmtime-py. The trampoline and
  reserve modules are compiled once per engine and instantiated per call, which defines no
  callback (INFERRED from decision 11: the race is in `define_func` and custom output).
- **Counting and the call record (decision 37).** Every provider call is counted by kind,
  limited by a default, and its failures recorded in `Completed`.
- **Embedder-neutral (§4.5).** `Mount`, a provider protocol, `OSError` for errors. No vfs word.
- **Safe by default (§4.15).** No mount unless the embedder passes one; a mount is read-only
  unless it says `writable=True`; staging, open files and provider calls each have a default
  limit.
- **The judge counts.** New checks count provider calls, shadowed calls, refused write-backs
  and errno values. A run with no mount keeps today's fuel exactly, an equality the judge can
  hold.

## What it decides (recommended design)

### The mechanism

Shadow the 26 file calls on a second, per-engine linker used only when `mounts=` is not empty.
Serve calls on provider fds in the runner; forward every other call to wasmtime through a
per-call trampoline instance on the guest's memory, by a cached `wasmtime_func_call`. Preopen
each mount on one empty, runner-owned placeholder folder, so wasmtime's table numbers every
provider fd. Stage whole files.

### The provider interface

```python
class Files(Protocol):  # paths are absolute within the mount: "/" is the mount itself
    def stat(self, path: str) -> Stat: ...            # Stat(kind="file"|"dir", size=0, mtime_ns=0)
    def list(self, path: str) -> Iterable[tuple[str, str]]: ...   # (name, "file"|"dir")
    def read(self, path: str) -> bytes: ...           # IsADirectoryError makes a directory open
    # a writable mount also needs:
    def write(self, path: str, data: bytes) -> None: ...  # the whole file, at close or sync
    def mkdir(self, path: str) -> None: ...
    def remove(self, path: str) -> None: ...
    def rmdir(self, path: str) -> None: ...
    def rename(self, src: str, dst: str) -> None: ...

run(argv, mounts=[Mount(files, "/work", writable=True)], grants=[Grant(data, "/data")])
```

- **Errors are Python's own `OSError`s:** `FileNotFoundError`, `FileExistsError`,
  `IsADirectoryError`, `NotADirectoryError`, `PermissionError`, `OSError(errno.ENOTEMPTY)`.
  The runner maps the host `errno` names to preview1 numbers. Any other exception is `EIO` for
  the guest and a fault in the record; nothing reaches wasmtime-py. vfs's adapter would map its
  `ErrorKind` to these.
- **Paths** reach the provider normalized, valid UTF-8, without NUL, `.` or `..`, bounded in
  length. Names from `list` are checked before the guest sees them.
- **One provider call per open,** following 169b's table: `read` for a plain open, `list` for
  `O_DIRECTORY`, `stat` for a create.
- **Read-only by default.** On a read-only mount, write-shaped calls are refused with 63, as a
  read-only grant's, before the provider is called.
- **Writes land at close, `fd_sync` and every exit,** traps included. A refused write-back is
  the guest's errno at close and a line in `Completed`.
- **Async:** any method may later be `async def`, awaited on the loop that called `run_async`,
  in slices, under the deadline and `cancel` (finding 8). This is question 15's mechanism, shared
  with the door and the tool protocol.

### The record and the limits

- `Completed.files`: calls by kind, refused write-backs (path, errno name), faults. No times.
- Limits with defaults (§4.15): provider calls per run (vfs uses 10,000); open provider files
  (for example 1,024, then `EMFILE`); staged bytes, summed over open files (for example
  `memory_bytes`, then `EFBIG`).

### The first milestone (one specification)

**Synchronous providers, mounted at any guest path a grant may use, read-only or writable.**

- `Mount(files, guest, *, writable=False)` and `mounts=` on `run` and `run_async`, checked like
  grants (no `/`, nothing at or under `/usr/local/lib`, no duplicate guest path with a grant or
  another mount).
- The mechanism above: second linker, 26 shared shadows, trampoline with the cached call, the
  placeholder and reservation, staging, one call per open, errno parity with grants.
- The answers for the ten calls a program rarely makes: `path_link`, `path_symlink` →
  `ENOTSUP`; `path_readlink` → `EINVAL` (not a link); `fd_advise` and the `set_times` calls →
  success; `fd_sync` and `fd_datasync` → a write-back now.
- `Completed.files`, the three limits, and `call.ended` set by the provider layer.
- A sync provider runs on the guest's thread; deadline and cancel are checked before and after
  each call, and the documentation says a sync provider must bound its own calls.
- **Checks, all counts:** an open, read and close of a provider file makes exactly one `read`;
  a write makes exactly one `write` at close; a refused write-back is in `Completed` on exit 0;
  every row of a parity table (missing file, directory as file, file as directory, escape,
  write on read-only, create under a missing parent, rename across a mount and a grant) gives
  the same errno on a `Mount` of an in-memory tree and on a `Grant` of the same tree on disk;
  a run with no mount has today's fuel exactly and zero shadowed calls; the limits each stop at
  their count; both binaries.

Later milestones: async providers (with question 15); a mount at `/` (question 1 below); ranged
reads for large files (`read(path, offset, size)`); the conformance job of the embedder
contract, which the parity table starts.

## Cost and risk

- **Size:** about 26 shadows, a fd table and staging. The model is about 250 lines; with input
  checks, limits, the record and errno parity, the runner's version is perhaps 700 to 900
  (INFERRED). It is security-critical code and needs a security review.
- **Speed:** zero for runs without a mount. With one: about 13 µs per forwarded call and 20 µs
  per provider-served call on this machine, against provider work that for vfs is several SQL
  statements per verb (study 04: one `read` is 5 statements; `04-…md:51-81`).
- **Untrusted input reaching embedder code:** only normalized paths and whole-file bytes, after
  the runner's checks. Offsets, flags, pointers and cookies stop in the runner.
- **Host memory:** staged buffers are outside the store's limit; the staging limit bounds them.
- **wasmtime-py internals:** the cached forward uses `_ffi`, as the epoch code already does. A
  wasmtime-py upgrade must re-run the forward checks. `Func.__call__` is the public fallback, at
  about three times the cost.
- **A provider bug** can only answer the guest wrongly or raise; the guest can never reach
  another folder through it, because unowned calls go to wasmtime and owned fds sit on an empty
  read-only placeholder.

## Questions for the owner

1. **May a provider be mounted at `/`, when `root` is not given?** vfs's guests see vfs's whole
   namespace at `/` (169b's one preopen, `169…/spec.md:351-357`). Grants may not use `/` today
   (`runner.py:796-797`). A mount at `/` needs the runner to show `/usr`, `/usr/local` and
   `/usr/local/lib` itself and to decide `/tmp` and `HOME`. *Recommended: yes, as the second
   milestone, after the first has shown parity.*
2. **The provider-call limit: what default, and what happens at it?** vfs uses 10,000 verbs per
   run and stops the guest (`084-…md:101-112`). *Recommended: 10,000; the call that passes it
   gets `EIO` and the run stops with its own `trapped` value, as the fuel limit does.*

## Where it stopped

- The model is outside the runner. It never ran under `_shared`, the call stack, the epoch
  ticker or the identity check.
- Not executed: a rename across a mount and a grant (`EXDEV` in the model, untested); a provider
  at `/`; a mount nested in a grant or a grant nested in a mount; Windows and Linux;
  `poll_oneoff` on a provider fd; sqlite3 over a provider.
- The cached forward was measured on one call with two arguments only.
- The model's guests do not fix the clock or entropy, so fuel varies by about 0.1 % between
  runs; per-call fuel was measured on the small guest, where it is exact.

## One line

The runner can serve a guest's ordinary file calls from embedder code with no new import:
shadow the 26 file calls, forward every call it does not own to wasmtime through a small
trampoline on the guest's memory, number provider files through an empty placeholder preopen,
stage whole files, and give the embedder an eight-method, `OSError`-raising provider, counted,
limited and read-only by default.
