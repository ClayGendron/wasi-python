# 106 — `mounts.py` behind a call-context protocol, one platform module, one stamp, and the source explains itself

- **Status:** **drafted 2026-10-20** on `claude/gallant-ride-9nxxmn` from main `5feb7e9` (the
  memo's plan; the tree read is `a9064a2`, the memo's commit), awaiting its pre-build review. It is
  the fifth link of the stacked chain 102 → 103 → 104 → 105 → 106 → 107 (constitution §4.14): it
  is built on 105's reviewed tip, which stands on 104's, on 103's, on 102's, and its header names
  that base commit when the build starts. The chain lands as one wave of six past §5.7's five, with
  one dispatch of the release workflow on the chain's final tip (the owner, 2026-10-20, the memo's
  section 8). A different agent reviews the build.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**: `src/` only, plus unit checks, a harness fake and rules checks. It
  **changes no line of `tests/public_api.txt`**, no artifact byte, no errno a guest sees, no
  golden output, no gap, no allowance and no progress file. Build-class it is not: it touches
  nothing under `scripts/`, `recipes/`, `downloads/SHA256SUMS` or the release workflow.
- **Depends on:** **105** (typed call state, explicit lifecycles, the type checker in the judge),
  and through it 104 (the process object, the test seams off the module globals), 103 (the runner
  as a package: `_limits`, `_places`, `_private_dirs`, `_zip`, `_engine`, `_call`, `_home`,
  `_platform`, `_sessions`, `_artifacts`) and 102 (the engine seam). Landed: 032, 034, 048 and
  068 (the mount table, its write half, the guard table and the open-file cap, which `_Files`
  serves); 017, 076 and 077 (the Windows walk and the grant checks that agree on Windows); 087
  (the `SHA256SUMS` check that `_digest` backs). The names of 103's modules are the memo's table
  (H1); when 103's specification names them otherwise, its names hold and this one reads through.
- **Research it stands on:** `../research/2026-10-20-a-design-review-of-the-runner.md` (findings
  H4, M3, M4 and M2; section 8 for the chain and its baseline).

## The problem

Four small structural faults stay after 102 to 105, each in the memo's list, each a reader's cost
rather than a user's.

1. **`mounts.py` and the runner depend on each other** (H4). `_Files.__init__` does
   `from . import runner` and keeps the module. From it the table reaches eight private names in
   fourteen places (EXECUTED at `a9064a2`: `grep -oE 'self\._runner\._[a-zA-Z_]+|\br\._[a-zA-Z_]+'
   src/wasi_python/mounts.py`): `_siphash13` five times, `_epoch_now` three, and `_ctrl_c`,
   `_ctrl_c_watched`, `_epoch_ticker`, `_hook`, `_trampoline_module` and
   `_stat_trampoline_module` once each. It also imports `_Call` under `TYPE_CHECKING` and reads
   four of a call's fields (`cancel`, `stop_at`, `ended`, `home`). The runner in turn imports
   `_Files`, `SIGNATURES`, `GUARDED`, `COUNTED` and the WAT builders from `mounts`. So the
   wasi-libc emulation layer, 2,235 lines with a 1,908-line unit file, cannot be read or
   constructed alone: its unit checks patch the runner's `_epoch_ticker.count`, `_ctrl_c_watched`
   and `_siphash13` to drive it (READ, `tests/unit/test_runner_mounts.py`).
2. **The platform is chosen in seventeen places** (M3). `grep -nE "os\.name|sys\.platform"
   src/wasi_python/*.py` lists 22 lines, all in `runner.py` (EXECUTED), inside seventeen
   functions: `_kernel_identity` (3), `_try_lock` (2), `_unlock_close`, `_sweep_entry` (2),
   `_long_path`, `_Walked.fd`, `_close_held`, `_walk`, `_make_missing`, `_identity_of`,
   `_write_member`, `_copy_zip`, `_cache_dir` (2), `_guest_stack`, `_tell_interpreter`,
   `_trap_handlers_ready` and `_private`. Each pair is clean. But "what does Windows do
   differently" has seventeen answers, and 103 moves the text without changing that: its
   `_platform.py` holds the stack probes, the locks and the kernel identity, while the walks stay
   in `_places`, the tree remover in `_private_dirs`, the cache folder in `_engine`.
3. **Three caches, three ideas of "the file changed"** (M4). `_stamp` is
   `(dev, ino, size, mtime_ns, ctime_ns)` and keys `_guest_packages`. `_digest`, which backs the
   `SHA256SUMS` check of spec 087, keys `_digests` on `(resolved path, size, mtime_ns)` only
   (READ, `runner.py:4678`). `_versions` keys on the `MANIFEST` path forever. A file replaced by
   one of the same size and modification time (a `cp -p`, a tar extract, a `git checkout` of an
   older build) keeps its stale digest for the life of the process. The artifact folder is trusted
   by the threat model, so this is defence in depth, not a hole; but a cache in front of an
   integrity check should key on at least the full stamp.
4. **The source cites the archive** (M2). 38 lines in `src/` name a review's finding ("the build
   review's F3", "the a4 security review's F2", "the re-review's N3", "the Confirmation's N2";
   EXECUTED: `grep -cE "review'?s? [A-Z]?[0-9]|the (build|security|delta|re-)?review"`: mounts 3,
   runner 25, tools 10), and about 30 more carry a bare finding ID, "(N2)", "(F7)", "(C6)",
   "(spec 032, F3)". The prose reason is
   usually written beside the ID, which is good; the IDs add noise, go stale (187 files under
   `context/reviews/` today) and send the reader to the archive for what the sentence should say.
   Counted the way the rule of Decision 4 counts, through `tokenize` over comments and
   docstrings (EXECUTED, `build/106/ids.py`): 61 lines carry the word "review" in some form
   (mounts 9, runner 38, tools 14) and 80 tokens are bare finding IDs (mounts 14, runner 49,
   tools 17). `spec NNN` appears 315 times for 39 distinct numbers (EXECUTED,
   `grep -oh 'spec [0-9]\{3\}' src/wasi_python/*.py | wc -l` and `… | sort -u | wc -l`; the
   memo's 315 agrees).

## Decisions

### 1. `_Files` takes a `_CallContext`; `mounts.py` imports nothing from the runner

**The protocol.** `mounts.py` declares `class _CallContext(Protocol)` with nine methods, one for
each thing the table asks of its host today. The names say what the table needs, not how the
runner provides it.

| method | replaces (READ, `mounts.py`) | answer |
|---|---|---|
| `ino_of(path: str) -> int` | `runner._siphash13(path.encode())`, five sites, the mount's own ino at construction included | the SipHash-1-3 inode number of a guest path, 64 bits |
| `trampolines(wt, engine) -> tuple[Any, Any]` | `_trampoline_module(wt, engine)` and `_stat_trampoline_module(wt, engine)` in `bind` | the forwarders module and the stat trampoline module, compiled with `wt.Module` for that engine; `wt` stays the wasmtime module `bind` already carries (the runner's seam, or the real `wasmtime` in the harness), so `bind`'s signature and the harness's two calls do not change |
| `exiting() -> bool` | `_hook["exiting"]` in `walk` | whether the interpreter is exiting, so no provider code may run |
| `ctrl_c_pending() -> bool` | `_ctrl_c_watched() and _ctrl_c["pending"]` in `walk` | whether a deferred Ctrl-C waits for this call |
| `stop_now(caller) -> None` | `_epoch_now(caller)`, three sites in `_gate` | the guest stops, or meets its epoch callback, at its next function entry |
| `cancelled() -> bool` | `call.cancel is not None and call.cancel.is_set()` | whether the call's cancel is set |
| `deadline_passed() -> bool` | `call.stop_at is not None and _epoch_ticker.count() >= call.stop_at` | whether the call's deadline tick has been reached |
| `name_end(reason: str) -> None` | `if call.ended is None: call.ended = reason` | names the call's end once; a first name holds |
| `on_home(fn, *args) -> Any` | `_Files._home`: `call.home.call(fn, *args)`, or `fn(*args)` with no home | runs `fn` where the embedder's code runs (spec 078, Decision 4) |

The first four are process-wide answers; the last five are the call's. One object answers all
nine, so the table holds one thing. Between a session's turns the call's five answer as "no
call": `cancelled()` and `deadline_passed()` False, `name_end` a no-op, `on_home` runs `fn`
directly; that is what `self.call is None` means in the table today.

**Who implements it.** `_call.py` (103's call module) defines `class _Context`, one per table,
constructed where the table is and holding `call: _Call | None`. Where `_Call.__init__` does
`table.call = self` today (READ, `runner.py:3258`) it does `table.context.enter(self)`; where the
table's `release()` sets `self.call = None` (the one such site today, `mounts.py:750`, READ) it
calls `context.leave()`. A `leave()` at a session turn's ending is new: today the table keeps the
last turn's `_Call` until the next turn's `_Call.__init__` overwrites it, and nothing reads it in
between (`_gate` and `_home` run only under a host function during a turn; `walk` calls `_made`
directly), so the "no call" answers between turns change no behaviour. The
`_Files` constructor gains one required keyword-only argument, `context: _CallContext` (`engine`
has a default today, so a positional one cannot follow it); the attribute `_Files.call` and the
`TYPE_CHECKING` import of `_Call` go. `_gate`
becomes four questions in the same order as today (cancel, deadline, the file-call limit, which
names the end), and `walk` asks `exiting()` and `ctrl_c_pending()`.

**Why a protocol and not a smaller runner import.** The memo's R3: the dependency graph between
modules must be acyclic, and `mounts.py` is the self-contained layer. A protocol names the nine
needs in one place, lets the type checker (105) hold the runner to them, and gives the unit checks
a fake instead of monkeypatching four private names of another module. The fake is also what H5
asks for: a seam that is a constructor argument.

**The fake.** `tests/harness/files.py` gains `class FakeContext`, a dataclass with the fields
`inos: dict[str, int]` (missing: the SipHash the runner uses, imported from its module, so the
inode numbers the unit checks compare stay the same), `exiting: bool`, `ctrl_c: bool`,
`cancel: threading.Event | None`, `ticks: int` and `stop_at: int | None`, `ended: str | None`,
`home: Callable | None`, and `stopped: list[object]` recording every `stop_now` caller. The unit
checks that today set `runner._epoch_ticker.count` and `runner._ctrl_c_watched` by
`monkeypatch` (EXECUTED: three sites, `tests/unit/test_runner_mounts.py:128`, `130`, `132`, and
one, line `171`) set the fake's fields instead; the one direct call of `runner._siphash13` (line
472, which computes an expected inode number) is not a patch, and the fake's SipHash fallback
keeps its number equal. The harness classes `Mounted`
and `Guarded`, which drive real wasmtime, pass the call module's real `_Context`, since they
build a real `_Call`.

**The rule.** A rules check, `test_mounts_imports_only_the_engine_seam`, reads `mounts.py`'s
AST and refuses any import of a sibling module, at module level, inside a function or under
`TYPE_CHECKING`, except 102's FFI seam module (the memo names it `_wasmtime_ffi.py`; 102's name
holds), which `forward` uses for the fuel-neutral call. The check names each offending line.
Seen failing on 105's tip: `from . import runner` and `from .runner import _Call`.

**What stays.** The runner keeps importing `_Files`, `SIGNATURES`, `GUARDED`, `COUNTED` and the
WAT builders from `mounts`: one direction is the point. `mounts.py`'s use of the FFI seam for
`forward` is 102's, unchanged here.

### 2. One platform interface in `_platform.py`, chosen once at import

**The interface.** `_platform.py` declares `class _Platform(Protocol)` and four classes that
satisfy it: `_Posix` (the base: any POSIX host the runner does not know by name), `_Linux(_Posix)`,
`_Darwin(_Posix)` and `_Windows`. One module-level name, `PLATFORM: _Platform`, is bound once at
import by `_select()`, the only function in `src/` that reads `sys.platform` or `os.name`:

```
def _select() -> _Platform:
    if sys.platform == "win32":
        return _Windows()
    if sys.platform == "darwin":
        return _Darwin()
    if sys.platform.startswith("linux"):
        return _Linux()
    return _Posix()
```

`startswith("linux")` is today's test in every Linux-only branch (READ, `runner.py:804`, `4505`,
`4599`), so an Android host (`sys.platform == "android"`, CPython 3.13 and later) stays what it is
today: a `_Posix` with no boot-id read, no `pthread_getattr_np` probe and no trap-handler check.
One function differs today: `_guest_stack` alone accepts `android` (`runner.py:4397`, READ) and
tries the POSIX probe there. After this specification an Android host gets `None` from
`_Posix.stack_bounds`, and the runner then refuses to start a guest as it does on any host whose
stack it cannot read. That is the one behaviour change this specification names, decided here:
one class answers one host, and no release runs or judges on Android (INFERRED: the release
workflow's three systems are Linux, macOS and Windows). A later specification that wants Android
adds `_Android(_Posix)` with the probe, under 107's review.

| member | today (READ, `runner.py`) | `_Posix` | `_Linux` | `_Darwin` | `_Windows` |
|---|---|---|---|---|---|
| `name: str` | (new) | `"posix"` | `"linux"` | `"darwin"` | `"windows"`; the one name a message may print |
| `has_dir_fd: bool` | `_dir_fd_ok()` and `os.name == "posix"` in `_Walked.fd`, `_make_missing` | `os.mkdir in os.supports_dir_fd and shutil.rmtree.avoids_symlink_attacks is not False`, read once at construction into an instance attribute; `_Posix` carries both branches below and consults it per call, as the five sites do today (`runner.py:1122`, `2832`, `2923`, `2929`, `2941`, READ) | inherited | inherited | `False` |
| `open_dir(path) -> int or None` | `_open_dir` | a handle opened without following a link when `has_dir_fd`, else `None` | inherited | inherited | `None` |
| `holds_open_files: bool` | `os.name != "nt"` in `_write_member`, `_copy_zip` | `False` | inherited | inherited | `True`: a file a running guest holds open cannot be replaced |
| `walk(where, path, *, judge, may_make) -> _Walked` | `_walk` → `_walk_posix` / `_walk_windows` | the descriptor walk | inherited | inherited | the handle walk |
| `make_missing(where, walked) -> _Walked` | `_make_missing` | through descriptors when `has_dir_fd`, else by path (today's `else` body; today the test is `os.name`, so a POSIX host without `dir_fd` would take the descriptor branch and fail at `os.mkdir(…, dir_fd=)`, and after this it takes the path branch: the same answer the remover and `real_dir` already give such a host) | inherited | inherited | by path |
| `close_held(h) -> None` | `_close_held` | `os.close` | inherited | inherited | `CloseHandle` |
| `identity_of(path) -> Identity` | `_identity_of` | `(st_dev, st_ino)` of a directory | inherited | inherited | the handle's identity, attributes only |
| `real_dir(root, fd, parts) -> tuple[Path, int or None]` | `_real_dir_at` / `_real_dir`, chosen at two sites | through `fd` when `has_dir_fd` and the root was walked by descriptor, else by path (today's two-sided test, `fd is not None and _dir_fd_ok()`) | inherited | inherited | by path |
| `long_path(path) -> str` | `_long_path` | the absolute path | inherited | inherited | the `\\?\` form |
| `try_lock(fd) -> bool or None` | `_try_lock` | `flock`, non-blocking | inherited | inherited | `msvcrt.locking`, with its busy errnos |
| `unlock_close(fd, *, unlink=None) -> None` | `_unlock_close` and the two orderings in `_sweep_entry` | unlink the lock file, then close (the lock is held until the close) | inherited | inherited | unlock, close, then unlink (a Windows lock outlives the handle for a moment; an open file cannot be deleted) |
| `kernel_identity() -> str or None` | `_kernel_identity` | `None` | `/proc/sys/kernel/random/boot_id` | `kern.bootsessionuuid` by `sysctlbyname` | `MachineGuid` from the registry |
| `remove_tree(name, parent, removal) -> bool` | `_remove_tree` → `_remove_at` / `_remove_by_path` | by descriptors, at most two held, when `has_dir_fd`; else by paths (today's `elif dir_fd is None` branch, `runner.py:1122`), so the sweep check that forces the by-path walk on Linux keeps its home | inherited | inherited | by paths, links and junctions never entered |
| `stack_bounds() -> tuple[int, int] or None` | `_guest_stack` → three probes, `None` elsewhere | `None` | `pthread_getattr_np` | the Mach probe | the TIB probe |
| `tell_interpreter(bottom, size, *, implementation, version, libc, resolve) -> bool` | `_tell_interpreter` with its `platform=` parameter | `False` | CPython 3.14+ without glibc: told | `False` | `False` |
| `trap_handlers_ready(machine) -> bool or None` | `_trap_handlers_ready` | `None` | the signal-handler check | `None` | `None` |
| `default_cache_dir(home) -> Path` | `_cache_dir`'s two branches | `XDG_CACHE_HOME` or `~/.cache` | inherited | `~/Library/Caches` | `LOCALAPPDATA` |
| `private(path, *, is_dir) -> bool` | `_private` | owner and mode checked | inherited | inherited | `True`: the default cache sits under the user's profile |

The implementations are today's functions moved verbatim, each pair's two bodies becoming the two
classes' methods, the chooser deleted. `_Walked`, `Identity`, `_win`, `_win_open`, `_Removal` (the
remover's budget) and the walk constants (`_DIR`, `_WALK_ACCESS`, `_STAT_ACCESS` and the Windows
flags) move with them, so `_platform.py` imports nothing from `_places` or `_private_dirs` and
the graph stays acyclic. The three lazy dicts `_identity`, `_win_api` and `_stack_api` become
attributes of the platform object, filled on first use; whatever 104 did with them in the process
object, they leave it, since a kernel identity and a bound C function are the same after a fork.

**Size** (INFERRED from EXECUTED spans): the thirty functions named above are 704 lines of
`runner.py` today (`build/106/spans.py`); with `_Removal`, the constants and the class scaffolding,
`_platform.py` ends near 850 lines, one file, and `_places` and `_private_dirs` lose the same.

**Why four classes and not two.** The shape is "posix and windows, darwin as posix with its own
stack probe". Two things make it four. Darwin also differs in its kernel identity, its cache
folder, and in not being Linux for the two CPython-on-Linux concerns (`tell_interpreter`,
`trap_handlers_ready`). And today an unknown POSIX host gets no stack probe, no kernel identity
and no interpreter hint (`_guest_stack(platform="freebsd14") is None`, pinned by
`tests/unit/test_runner_threads.py:100`, READ): that is the base class `_Posix`, and `_Linux` is
the one that knows the kernel. A subclass with a few overrides says exactly that; a flag inside
one class would be the branch this specification removes, moved one file over.

**Why a module-level object and not an argument.** Every caller of these members runs in the one
process, on the one platform; threading a platform through forty signatures would add noise for no
second caller. Every caller writes `from . import _platform` and reads `_platform.PLATFORM` at the
call, never `from ._platform import PLATFORM`, so a rebinding of the name reaches every caller; a
rules check (`test_the_platform_is_chosen_once`, below) refuses the second form.

**How a check binds a platform.** `PLATFORM` carries no underscore, so 104's rule (the judge
patches an underscore name only through `process()`) does not cover it, and it is the one
platform seam, which 107's seam check knows by name. A check that needs the other platform's rule
does `monkeypatch.setattr(_platform, "PLATFORM", _Windows())` for its duration, or calls a class's
method directly (`_Windows().walk`, `_Posix().stack_bounds()`). A check that needs the real
platform without `dir_fd` sets the attribute on the real object,
`monkeypatch.setattr(_platform.PLATFORM, "has_dir_fd", False)`, and `_Posix` takes its by-path
branches: that is the sweep check at `tests/unit/test_runner_sweep.py:539`, which forces
`_dir_fd_ok` False on Linux today to drive the by-path remover against a symlink canary; it is
never bound to `_Windows()` on Linux, whose `long_path` and `try_lock` are Windows's. When 104
lands with a process-object field for the platform instead, the binding is
`monkeypatch.setattr(process(), "platform", …)` and the attribute form stays; the fallback when
104 gives it no such field is the module name above.

**The allowance list.** 104's Decision 4 leaves twenty private names the judge still patches by
name as the allowance list that 107's seam check starts from, and says 106 shrinks it. This
specification removes from that list the nine platform names its object absorbs
(`_guest_stack`, `_tell_interpreter`, `_trap_handlers_ready`, `_dir_fd_ok`, `_win_open`,
`_close_held`, `_try_lock`, `_unlock_close`, `_remove_tree`) and, of the call-path names, only
the mount table's own site (`_ctrl_c_watched` in `tests/unit/test_runner_mounts.py:171`, which
the fake context replaces); the other `_ctrl_c_watched`, `_stop_error` and `_epoch_now` sites
belong to checks of the call pipeline, not the table, and stay on the list for their own closers.
The builder hands 107's builder the shrunk list in the landing notes.

**The rule.** A rules check, `test_the_platform_is_chosen_once`, greps `src/wasi_python/*.py`
for `os\.name|sys\.platform` and refuses every match outside `_platform.py`, and inside it every
match outside `_select`; it also refuses `from ._platform import PLATFORM` (or any `import` that
binds `PLATFORM` to a local name) anywhere in `src/`, so the object is always read through its
module. No line may stay: each of the 22 is in a function the table absorbs, and
none is a message text (READ, every line listed in *The problem*). A later message that must name
the host's platform prints `PLATFORM.name`. Seen failing on 105's tip: 22 lines.

### 3. One stamp for the three caches

`_stamp(st)` stays `(st_dev, st_ino, st_size, st_mtime_ns, st_ctime_ns)` and is defined once, in
`_artifacts.py` (103's home of the artifact-set check, which `_digest` serves), imported by
`_zip.py` for the zip copy. Then:

- **`_digest(path)`** opens the file, takes `os.fstat` of the descriptor it hashes, and keys
  `_digests` on `(str(path.resolve()), *_stamp(fstat))`. A later call stats the path first; a
  key with the same resolved path and the same stamp is a hit, anything else hashes again. The
  stamp is of the descriptor read, so what was hashed and what is keyed are one file. A
  replacement of the same size and `mtime_ns` has another inode or another `ctime_ns` (a rename
  into place updates the new inode's change time), so it is hashed again. The dictionary stays
  unlocked: a race only hashes twice.
- **`_version_tag(manifest)`** keys `_versions` on `(str(manifest), *_stamp(os.stat(manifest)))`.
  A `MANIFEST` rewritten in place by a reinstall is read again.
- **`_has_guest_package`** already keys on the full stamp; it stays and loses nothing.
- **`_zips`** keys on a digest, a content key, and is right as it is.

**Why not drop the caches.** `_digest` hashes a 41 MB binary and a 39 MB zip; the artifact check
runs on every call (spec 087). The stamp costs one `stat`.

**The check.** `tests/unit/test_runner_artifacts.py` (or the unit file 103 names for
`_artifacts`) gains `test_a_same_size_same_mtime_replacement_is_hashed_again`: write file A,
digest it; write file B of the same length beside it, `os.utime` it to A's exact `mtime_ns`,
`os.replace` it over A; digest again and see B's hash; then a third call sees the cached B with no
new read (the check counts opens through a seam on `open`, never time). And
`test_a_rewritten_manifest_gives_its_new_version_tag` for `_versions`. Both seen failing on 105's
tip.

### 4. The source explains itself: finding IDs out, one specification list per module

**What goes.** Every review-finding ID in `src/wasi_python/*.py`: the phrases that name a review
("the build review's F3", "the a4 security review's F2", "the re-review's N3", "the delta
review's D3", "the pre-build review's F1", "the follow-up review's F1", "the Confirmation's N2",
"0.1.0 security review's S3", "review F9"), and the bare IDs in parentheses or lists ("(N2)",
"(F7)", "(C6)", "(spec 032, F3)", "F3's error row", "(spec 053, D5)"). A decision is written
"Decision 5", never "D5".

**What stays, by rule.** The rule removes an ID and nothing else. Stated so that it never removes
a reason:

1. An edit under this decision deletes the ID token, its parentheses or its possessive phrase
   ("the review's "), and a dangling connector (", " or "; "), and leaves every other word of the
   sentence where it was.
2. Where the ID was the whole explanation ("(F7)" with no reason beside it), the builder looks the
   finding up in `context/reviews/`, or in the specification that carries the finding in its
   decisions, and writes its reason in words in that sentence; the landing notes list each such
   sentence with the review or specification it was read from.
3. No sentence is deleted, shortened or reworded beyond rules 1 and 2. No code token changes.

**Specification numbers.** Each module's docstring ends with one paragraph, `Specifications:`,
listing every spec number the module stands on, one per line, each with a few words
(`spec 032: the mount table`). In the body, `spec NNN` stays only where a decision number is the
only name a rule has (`spec 032, Decision 10`), or where a cross-reference names what another
module does (`the walk of spec 034, Decision 8`); a bare `(spec NNN)` beside a sentence that
explains itself goes, under the same three rules. The count 315 falls; the landing notes record
the number after.

**Its own commit.** This is the only edit in the chain that changes text rather than moving it,
so it is one commit on its own, `106: finding IDs out of src/ (Decision 4)`, with no other change
in it. The reviewer reads it apart with `git diff --word-diff` and checks that every removed word
matches the ID regexes below or is a connector, and that every added word is in a sentence the
landing notes list under rule 2.

**The rule.** A rules check, `test_src_names_no_review_finding`, runs two regexes over the
comments and docstrings of `src/wasi_python/*.py` (through `tokenize`: comment tokens and
string tokens that are docstrings, so an identifier or a literal never trips it):

```
REVIEW_PHRASE = re.compile(r"\breviews?\b|\bre-review|\bconfirmation's\b", re.I)
FINDING_ID = re.compile(r"(?<![A-Za-z0-9_])[CDFLNS]\d{1,2}(?:\.\d+)?(?![A-Za-z0-9_])")
```

The first refuses the word "review" in any form in `src/`: nothing a maintainer needs to say
about the code is about a review. The second refuses a one- or two-digit ID of a finding
(`F3`, `N12`, `F4.2`, `S3`, `D3`, `C6`, `L1`); the trailing look-ahead keeps `F401` in a `noqa`
out, and the leading one keeps a word like `MD5` out. The check names each file and line. Seen
failing on the commit before the text commit: 61 lines for the phrase (mounts 9, runner 38,
tools 14) and 80 bare IDs (14, 49, 17), the counts of `build/106/ids.py` at `a9064a2`
(EXECUTED), less whatever 102 to 105 already moved or reworded.

**What the ID regex also refuses, and the recourse.** `[CDFLNS]\d{1,2}` matches more than
review findings: `C99` and `C11` (ISO C), `L1` and `L2` (cache levels), `F1` (a key), `N1`.
That is by design: the rule is cheap, and a comment that needs such a token writes it in words
("ISO C of 1999", "the first-level cache", "the F1 key"), which reads better in a sentence
anyway. Where words will not do, the check carries one tuple, `FINDING_ID_ALLOWED`, empty at
first, of exact tokens with a one-line reason each, and the review reads every addition; a new
review-finding ID is never added to it. Three of today's IDs are a review's items that a
specification carries in its decisions (`C1` and `C2` of spec 078's and spec 048's
confirmations, `S2` of spec 024's security review; EXECUTED, `mounts.py:2041`,
`runner.py:2718`, `3007`), so rule 2 above looks them up in `context/reviews/` or in the
specification that carries the finding, and the landing notes name whichever it read.

A second rules check, `test_each_module_lists_its_specifications`, reads each module's
`Specifications:` paragraph and the `spec NNN` numbers in its body, and refuses a body number the
paragraph lacks or a listed number the body never names. It keeps the list true as code moves.

### 5. Acceptance: no verdict moves

The judge of "nothing a guest sees changed" is the same as the chain's (the memo's section 8):

- **The baseline set** is the `v0.1.0a7` release's, verified against its `SHA256SUMS`, frozen in
  the worktree for every link of the chain. No link builds an artifact.
- **The fast tier** (`uv run pytest -m "not slow" -n 3`) runs on the built commit in the
  worktree; its `build/progress/latest.json` is compared with 105's reviewed-tip record and with
  the chain's baseline record by `uv run python tests/harness/sameness.py --claims
  build/106/claims.toml A.json B.json`. The only differences allowed are 106's claim list: the
  four new rules checks, the new unit rows, and the unit rows retired or renamed (the three that
  patched the runner for the mount table). Any other line is a finding.
- **The errno and parity tables** stay the judge of the guest's errnos:
  `tests/unit/test_runner_mounts.py`
  (`_HOSTS`, `_ERRNO_NAMES`, `NATIVE_RENAME_END`, `PAST_THE_LIMIT`, `SPIN_DIRTY`) and
  `tests/checks/test_v1_4_embedding.py` (`GRANT_PARITY`, `WRITE_PARITY`, `WRITE_DIFFERENCES`,
  `ERRNO_GUEST`, `MOUNT_CANCEL`). None is edited. The slow ones among them run by node id in the
  worktree once, and in the chain's one dispatch.
- **The new rules checks are seen failing first**, each on the commit before the code it guards,
  by node id, the output kept under `build/106/` and quoted in the landing notes.
- **`ruff check`, `ruff format --check` and 105's `mypy` run** are clean on `src/` and `tests/`;
  the `Any` count in `mounts.py` and `_platform.py` does not grow (`grep -c '\bAny\b'`, recorded).

## Intent

After this specification `mounts.py` reads alone: a table that asks nine questions of a context it
is given, with a fake for the unit checks and the call module as the one real answer. The
Windows story is one file: a reviewer who asks "what does Windows do differently" opens
`_platform.py` and reads `_Windows`. The three caches in front of the artifact check agree on
what "changed" means. And a maintainer reads why a line is what it is in the line itself, with
the specifications a module stands on listed once at its top, and no review's filing number in
between.

## Design

### The commits, in order

Each commit is green on its own (AGENTS.md rule 9); each check is seen failing on the commit
before its code, by node id, and the output kept under `build/106/`.

1. **`106: _Files takes a _CallContext (Decision 1)`**: the protocol in `mounts.py`; `_Context`
   in `_call.py` with `enter`/`leave`; `FakeContext` in `tests/harness/files.py`; the three unit
   checks moved off `monkeypatch`; `test_mounts_imports_only_the_engine_seam` in
   `tests/checks/test_rules.py`.
2. **`106: one platform interface (Decision 2)`**: `_Platform`, the three classes, `_select` and
   `PLATFORM` in `_platform.py`; the moved functions; every caller through `_platform.PLATFORM`;
   every site of the table under *The unit checks that bind a platform* rebound, bound or
   redirected as that paragraph says; `test_the_platform_is_chosen_once`.
3. **`106: one stamp (Decision 3)`**: `_digest` and `_version_tag` keyed on the stamp; the two
   unit checks.
4. **`106: finding IDs out of src/ (Decision 4)`**: the text commit alone, under the three rules.
5. **`106: the citation rules (Decision 4)`**: `test_src_names_no_review_finding` and
   `test_each_module_lists_its_specifications`, green on commit 4, seen failing on commit 3.

### `mounts.py` after commit 1

```
class _CallContext(Protocol):
    def ino_of(self, path: str) -> int: ...
    def trampolines(self, wt: Any, engine: Any) -> tuple[Any, Any]: ...
    def exiting(self) -> bool: ...
    def ctrl_c_pending(self) -> bool: ...
    def stop_now(self, caller: Any) -> None: ...
    def cancelled(self) -> bool: ...
    def deadline_passed(self) -> bool: ...
    def name_end(self, reason: str) -> None: ...
    def on_home(self, fn: Callable[..., Any], *args: Any) -> Any: ...
```

`_gate` reads, in today's order:

```
if self.context.cancelled():
    self.context.stop_now(caller)   # named "cancelled" by the epoch callback at the next entry
    return ECANCELED
if self.context.deadline_passed():
    self.context.stop_now(caller)   # an interrupt at the next entry: "deadline"
    return ETIMEDOUT
if self.limit is not None and self.total >= self.limit:
    self.context.name_end("out of file calls")
    self.context.stop_now(caller)   # in the same step: the guest stops at its next entry
    return EIO
return 0
```

`walk` returns when `(self.context.exiting() and not ending) or self.context.ctrl_c_pending()`,
exactly today's condition with the names replaced. `bind(wt, store, plain, instance)` keeps its
signature and takes `module, stat_module = self.context.trampolines(wt, self.engine)`. The five
`ino_of` sites replace five `_siphash13` calls.

### `_call._Context`

```
class _Context:
    """The runner's answers to the mount table's nine questions (mounts._CallContext)."""
    def __init__(self, process: _Process) -> None: ...   # 104's object: the ticker, the hooks
    def enter(self, call: _Call) -> None: ...             # where table.call = self was
    def leave(self) -> None: ...                          # where table.call = None was
```

`ino_of` is `_siphash13`; `trampolines` is `_engine`'s two module builders; `exiting` and
`ctrl_c_pending` read 104's process object; the five call methods read `self.call` and answer
"no call" when it is None.

### `_platform.py` after commit 2

The file's order: the docstring with its `Specifications:` paragraph (017, 024, 076, 077, 078,
084 and the others the moved text names); `Identity`, `_Walked`, `_Removal`; the constants; the
`_Platform` protocol; `_Posix`; `_Linux`; `_Darwin`; `_Windows`; `_select`; `PLATFORM`. Every caller in
`_places`, `_private_dirs`, `_zip`, `_engine`, `_home` and `_artifacts` writes
`from . import _platform` and calls a member of `_platform.PLATFORM` at the call (Decision 2,
*How a check binds a platform*). The seventeen choosers are gone; the
functions `_walk`, `_guest_stack`, `_remove_tree`, `_cache_dir` and `_private` either become
one-line callers kept for their docstrings or disappear, the builder's choice per function,
named in the landing notes.

### The unit checks that bind a platform

Every site in `tests/` that names a platform function, in both forms, the attribute read
`runner._name` and the patch string `monkeypatch.setattr(runner, "_name", …)` (EXECUTED at
`a9064a2`, `build/106/platform-sites.txt`, one grep with both alternations over the 26 names the
table absorbs; the builder re-runs it on 105's tip, where 103 and 104 have moved some):

| file | attribute reads | patch strings |
|---|---|---|
| `tests/unit/test_runner_sweep.py` | `_remove_tree` 9, `_try_lock` 7, `_unlock_close` 2, `_dir_fd_ok` 1, `_kernel_identity` 1 | `_remove_tree` 6, `_dir_fd_ok` 2 (lines 453 and 539), `_try_lock` 2, `_unlock_close` 1 |
| `tests/unit/test_runner_grants.py` | `_walk` 18, `_identity_of` 5, `_walk_windows` 2 | `_close_held` 1, `_win_open` 1 |
| `tests/unit/test_runner_threads.py` | `_tell_interpreter` 3, `_guest_stack` 2 | `_guest_stack` 2, `_tell_interpreter` 1 |
| `tests/unit/test_runner_async.py` | none | `_trap_handlers_ready` 2 |
| `tests/unit/test_inline_sessions.py` | `_trap_handlers_ready` 2 | none |
| `tests/unit/test_runner_calls.py` | `_trap_handlers_ready` 1 | none |
| `tests/checks/test_v1_2_hostile_guest.py` | `_guest_stack` 1 (line 2745) | `_guest_stack` 2 (lines 2792, 2799) |
| `tests/checks/test_v1_4_embedding.py` | `_try_lock` 1, `_unlock_close` 1 (lines 1516, 1518) | none |

After commit 2 each site is one of three things: a call of the member on `_platform.PLATFORM`
(a read that drove the real platform); a direct call of a class's method where it drove one
platform's function (`_Windows().walk` for `_walk_windows`, `_Posix().stack_bounds() is None` for
the unknown-host row); or a binding, `monkeypatch.setattr(_platform, "PLATFORM", fake)` with a
small `_Platform` stand-in, or an attribute set on the real object (`has_dir_fd` for the sweep
check at line 539), where it patched a function to fake a platform answer or force an error
path. No site may keep patching a name on the runner: commit 2 deletes or thins those functions,
so a patch that stays would replace a stub no caller reads and the check would stop meaning what
it says. The checks' assertions do not change; the landing notes list every site in this table
and what replaced it, and criterion 8 counts them.

### The CHANGELOG line

Under the one unreleased section:

> **The runner's mount table, platform choice, file stamps and comments explain themselves**
> (spec 106; the design review's H4, M3, M4 and M2). `mounts.py` asks nine questions of a
> call-context protocol and imports nothing from the runner; one `_platform.py` holds every
> POSIX, macOS and Windows difference behind one interface chosen once at import; the digest and
> version caches in front of the artifact check key on the full file stamp, so a same-size,
> same-time replacement is hashed again; review-finding IDs are gone from the source, every
> reason kept in words, and each module lists its specifications once. No public name, artifact
> byte or guest-visible errno changes.

### The roadmap line

> Reserved: 106, "`mounts.py` behind a call-context protocol, one platform module, one stamp,
> and the source explains itself" (the design review's H4, M3, M4, M2): the fifth link of the
> chain 102 to 107, stacked on 105; parallel-safe; lands in the chain's wave.

## Scope

In: Decisions 1 to 5. Out:

- **102's FFI seam, 103's module boundaries, 104's process object, 105's types and state
  machines**: this specification stands on them and changes none of their decisions. Where 103
  names a module otherwise than the memo's table, 103's name holds.
- **The private-folder protocol's own module and property checks** (M5): 103's.
- **A structural review as a stage** (section 5): 107's.
- **Any change to what the guest sees**: no errno, no record field, no limit, no default.
- **`tools.py`'s friend-class coupling** (L2): not in the chain.
- **Citations in `tests/`, `scripts/` and `context/`**: the rule is for `src/`, where the reader
  is a maintainer of the code; a check's docstring may name the review that made it.

## Acceptance criteria

1. **The four rules checks and the two unit checks exist and were seen failing first**, each by
   node id on the commit before its code, the output under `build/106/` and quoted in the landing
   notes (Decisions 1 to 4).
2. **`mounts.py` imports nothing from the runner**: `test_mounts_imports_only_the_engine_seam`
   green; `grep -nE 'from \.|import wasi_python' src/wasi_python/mounts.py` lists only 102's seam.
3. **The platform is chosen once**: `test_the_platform_is_chosen_once` green;
   `grep -nE "os\.name|sys\.platform" src/wasi_python/*.py` lists only lines inside
   `_platform._select`.
4. **One stamp**: `_digests` and `_versions` keyed on the full stamp; the two unit checks green.
5. **No finding ID in `src/`**: `test_src_names_no_review_finding` green; the citation commit's
   word diff removes only ID tokens, parentheses, possessives and connectors, and adds words only
   in the sentences the landing notes list under Decision 4's rule 2, each with its review named.
6. **Every module lists its specifications**: `test_each_module_lists_its_specifications` green;
   the count of `spec NNN` in `src/` after, recorded.
7. **No verdict moved**: `sameness.py --claims` between the built commit's fast-tier record and
   105's reviewed-tip record, and between it and the chain's baseline record, prints nothing
   outside the claim list (Decision 5).
8. **The parity checks are untouched, and every platform site is accounted for**: `git diff
   105-tip..HEAD` touches, in `tests/checks/test_v1_4_embedding.py`, only the two lines that call
   `_try_lock` and `_unlock_close` (1516 and 1518 today) and no line of its parity tables or
   their checks; in `tests/unit/test_runner_mounts.py` only the four sites moved off
   `monkeypatch` (lines 128, 130, 132 and 171 today); and in the eight files of the table under
   *The unit checks that bind a platform*, every site that table counts (76 at `a9064a2`, both
   forms) and no other, each named in the landing notes with what replaced it; after the change
   `grep -rnoE 'runner\._(walk|…)|setattr\(runner, "_(walk|…)"' tests/` with the 26 names is
   empty.
9. **`tests/public_api.txt` is unchanged**, byte for byte; `uv run python tests/harness/api.py`
   reports no difference.
10. **`ruff check`, `ruff format --check` and `mypy` are clean**; the `Any` counts in `mounts.py`
    and `_platform.py` recorded, not grown.
11. **The chain's dispatch**: the release workflow on the chain's final tip, every red line a
    growth line of another link or none (the owner's one-dispatch rule); the run id in the landing
    notes of whichever link the lane names.

Eleven criteria.

## For the lane

- **Kind:** parallel-safe; one of the six links that land as one wave past the five (the owner,
  2026-10-20). It is built on 105's reviewed tip and rebased onto the wave's tip in the chain's
  order, after 105 and before 107.
- **Files it shares with others:** every module under `src/wasi_python/` (the citation commit
  touches comments in all of them), so it rebases last among the chain's code links and names
  every conflict; `tests/checks/test_rules.py` (four new checks, appended at the end of the file
  so a rebase against another link's check is a trivial merge); `tests/harness/files.py`;
  `tests/unit/test_runner_mounts.py`, `test_runner_sweep.py`, `test_runner_grants.py`,
  `test_runner_threads.py`, `test_runner_async.py`, `test_inline_sessions.py`,
  `test_runner_calls.py` (the platform sites of the table under *The unit checks that bind a
  platform*); `tests/checks/test_v1_2_hostile_guest.py` (one call site and two patch sites) and
  `tests/checks/test_v1_4_embedding.py` (two call sites, no parity line); `CHANGELOG.md`;
  `context/roadmap.md`.
- **The claim list** (`build/106/claims.toml`, each line "106:"; the counts filled by the
  builder):
  - 106: **new checks**: `test_rules.py::test_mounts_imports_only_the_engine_seam`,
    `::test_the_platform_is_chosen_once`, `::test_src_names_no_review_finding`,
    `::test_each_module_lists_its_specifications`; the two stamp unit checks.
  - 106: **unit rows moved**: the four mount sites off `monkeypatch` (two checks), and the 76
    platform sites of the eight files in the table under *The unit checks that bind a platform*
    (the landing notes list them by name).
  - 106: **retired checks:** none. **Lost passes:** none. **Fuel rows:** none grow (no guest byte
    changes). **Bytes:** none.
  - **The judge hash changes** in `tests/checks/test_rules.py`, `tests/harness/files.py` and the
    unit files named.
- **The flags** (paste-safe; the lane folds them into the wave's one acceptance):

  ```
  --accept "106: mounts.py asks a _CallContext protocol its nine questions and imports nothing from the runner; one _platform.py chooses the platform once at import behind one interface; the digest and version caches key on the full file stamp; review-finding IDs are gone from src/ with every reason kept in words, and each module lists its specifications once"
  --accept-judge "106: four rules checks (mounts imports only the engine seam; the platform is chosen once; no review-finding ID in src/; each module lists its specifications) and two unit checks (a same-size, same-mtime replacement is hashed again; a rewritten MANIFEST gives its new tag); three mount unit checks drive a fake context instead of patching the runner; no existing expectation edited"
  ```

- **Dry-run needs:** none of its own: the chain's one dispatch on its final tip (the owner's rule
  for the chain). The Windows shards run the platform checks on `_Windows` as a matter of course;
  the builder reads that run's `rules` and `unit` groups for the three systems.

## One line

`mounts.py` asks nine questions of a protocol instead of reaching into the runner, every POSIX,
macOS and Windows difference lives behind one interface chosen once, the three caches in front of
the artifact check agree on what "changed" means, and the source keeps its reasons in words and
drops the review filing numbers.

## Landing notes

Filled in when it lands.
