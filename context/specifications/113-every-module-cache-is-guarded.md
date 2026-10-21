# 113: every module cache is guarded

- **Status:** **built 2026-10-21 on `a891dec5`** (the code; the commit after it carries these
  notes, `context/` only) on `spec/113-every-module-cache-is-guarded`, from main `1875d4cd`;
  the release workflow's run 39624848889 on `a891dec5` green on three systems on its second
  attempt (*Landing notes*); awaiting its build review (a different agent). Before:
  **drafted 2026-10-21** from main
  `1875d4cd`, with its checks written first and seen failing on main's code (Decision 6). The
  worktree is
  `.claude/worktrees/agent-a8a67f30f6c037394`; the checks ran against the main tree's frozen set
  (`build/artifacts`, `SHA256SUMS` `d0d91cef`) through `$WASI_PYTHON_ARTIFACTS`, and their
  output is under `build/113/` there. **Reviewed before build** the same day
  (`../reviews/113-every-module-cache-is-guarded-spec-2026-10-21.md`, "fit to build once H1, M1,
  M2 and M3 are answered in the specification"); **revised** the same day to answer every
  finding (*Disposition of the pre-build review*, below), with the new check rows written first
  and seen failing on main's code; **confirmed fit to build** by the same reviewer's
  confirmation read (`35ec623f`, three new Lows, L8 to L10, answered in the build).
- **Date:** 2026-10-21
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural**: `src/` (`_engines.py`, `_places.py`,
  `_platform.py`, and the two call sites in `_call.py` and `_sessions.py`), one unit-check
  file and its line in `tests/release_shards.toml`'s `own-runner` shard (so it runs on all three
  systems, as every runner unit file must), `README.md` and `CHANGELOG.md`. It touches nothing under `scripts/`, `recipes/`,
  `downloads/SHA256SUMS` or the release workflow, and no artifact byte. It is runner code and a
  security fix, so its pre-build review is required (AGENTS.md, rule 8). Decision 7 says why it
  is not structural by AGENTS.md's definition, measured. It **tightens** a default and loosens
  none (constitution §4.15).
- **Depends on:** landed and unchanged in intent: 104 (the runner as a package: `_engines`,
  `_places`, `_platform`), 107 (one platform module behind one interface), the grant judge and
  its rule that a writable grant or `root` at, inside or above the runtime's own folders is
  refused (README, "Safety"). On nothing in flight. The other 0.1.0 security finding, H2 (code
  planted in a reused root runs on `import reportlab`), is another specification's; the two
  share no file but `README.md`, `CHANGELOG.md` and `context/roadmap.md`.
- **Research it stands on:** the 0.1.0 security review, finding **H1** (High; 0.1.0 waits on
  it): `../reviews/0.1.0-security-review-2026-10-21.md`, lines 257 to 323, on its own branch
  until it lands; its probe `build/secreview/probes/p50_cwasm_plant.py` and its log
  `build/secreview/logs/p50_cwasm_plant.log` in that review's worktree.

## The problem

The README promises (README lines 1044 to 1048):

> a writable grant or `root` at, inside or above the runtime's own folders is refused, since
> later calls and processes trust them: the stdlib folder (or the temporary folder that holds
> it), the artifact set, the module cache, …

The judge keeps that promise only for **the call's own** module cache. A call made with
`cache_dir=False`, or with a `cache_dir` of its own, does not judge the cache that other calls
and other processes use. So its guest may be handed a writable grant over that cache, and the
judge passes it.

**What the review ran** (EXECUTED by the reviewer; each step a fresh process, so nothing was
compiled in memory):

| step | the call | result |
|---|---|---|
| 0 | `snapshot=False`, `cache_dir=<C0>` | real `.cwasm` bytes of the plain reactor (239,563,920 bytes), standing in for bytes an attacker builds offline |
| 1 | `cache_dir=False`, a writable `Grant(<D>, "/c")`, where `<D>/wasi_python` is the cache `$WASI_PYTHON_CACHE` names | the guest wrote those bytes as `/c/wasi_python/<snapshot digest[:32]>-wasmtime49.0.0-plain.cwasm`; the judge passed the grant; the file was this user's, mode `0644` |
| 2 | every default (the cache at `<D>/wasi_python`), `snapshot=True` | `stats()`: **compiled 0, loaded 1**; the runner loaded the guest's file in place of the snapshot and ran it |

**Why** (READ, on `1875d4cd`):

- `_places._walk_grants` judges `_runtime_folders(found, cache)` (`_places.py:426`, `473-512`)
  with the call's own `cache` only. `_engines._cache_dir(False)` is `None`
  (`_engines.py:67-74`), so then no cache is judged at all. With a `cache_dir` of its own, only
  that folder is.
- `_engines._module_miss` loads any file named `<digest[:32]>-wasmtime<version>-<flavor>.cwasm`
  that `private()` accepts (`_engines.py:143-149`).
- POSIX `private()` asks for a directory or regular file owned by this user and **not group- or
  other-writable** (`st_mode & 0o022`, `_platform.py:535-551`). A guest writes as this user,
  and under the usual umask (`022`) its `mkdir` gives `0755` and its `open` `0644`: both pass.
- Windows `private()` returns `True` for anything (`_platform.py:1389-1392`).
- The file's name is public: the binary's SHA-256 is in `SHA256SUMS`, the version is
  wasmtime-py's. Nothing ties the file's content to the digest in its name.

**What it breaks.** `Module.deserialize_file` runs the file's machine code as it finds it;
wasmtime documents it as unsafe for untrusted input. A guest that writes a `.cwasm` of its own,
built offline against the public wasmtime 49.0.0 and the public binary, runs native code in the
host process at the next call: outside wasm, with the embedder's privileges. That is the threat
model's worst class, through a promise the README makes.

**Who it reaches.** Any embedder that, in any call or process, gives a writable grant or `root`
at or above a module cache another call or process uses, while that call's own cache is off or
elsewhere. `cache_dir=False` is the natural setting for a call that should leave nothing on
disk. The default caches are `~/Library/Caches/wasi_python` (macOS), `~/.cache/wasi_python`
(Linux, or `$XDG_CACHE_HOME/wasi_python`) and `%LOCALAPPDATA%\wasi_python\cache` (Windows).

**Reproduced here, first** (EXECUTED, `build/113/checks-on-main.txt`): the twelve rows of
Decision 6's first check, one per caller (`run`, `run_async`, `Session`), own cache (off,
elsewhere) and victim (`$WASI_PYTHON_CACHE`, existing; the platform default, not yet made), each
fail on main with the same line, for example:

```
the writable grant over …/build/harness/unit-egrsox7w/granted/wasi_python was not refused
(the guest exited 0); the next default call (KeyError) then loaded 1 compiled module(s) the
guest wrote
```

The planted module is a real one this wasmtime loads (an empty module serialized by the
runner's own unmetered engine, 33,792 bytes, EXECUTED, carried in the guest's source); the
next call's `KeyError` is the runner finding none of the snapshot's exports in it, *after*
loading it. A module with the snapshot's exports and the attacker's code would run.

**The existing caches on this machine** (EXECUTED, `stat`): `~/Library/Caches/wasi_python` and
the judge's `build/cwasm-cache` are `drwx------`, and every `.cwasm` in them `-rw-------`. The
runner has made the folder with `mkdir(mode=0o700)` and each file with `mkstemp` (`0600`) then
`os.replace` since the cache existed, so Decision 3's stricter modes cost an existing cache
nothing.

## Decisions

### 1. The rule: judge every cache the process could use, whatever the call's own

In `run`, `run_async` and `Session` (every caller of `_walk_grants`), the judge's runtime
folders hold **every module cache this process could use**, whatever this call's `cache_dir`:

1. **the call's own**, if it has one (`cache_dir` a path, or `None`/`True`, which name one of
   the next two);
2. **the folder `$WASI_PYTHON_CACHE` names**, if it is set and not empty;
3. **every platform default a process of this user could compute**, always, even when
   `$WASI_PYTHON_CACHE` is set (another process of this user may run without it), and for the
   same reason one variable down: another process may run without this one's
   `$XDG_CACHE_HOME` or `%LOCALAPPDATA%`, or with another `$HOME`. So
   `PLATFORM.default_cache_dirs(home)` gives, deduplicated by path, this process's own
   (`default_cache_dir`, overrides read as today) and the same folder with the override
   ignored, for each home:
   - **Linux and other POSIX:** `$XDG_CACHE_HOME/wasi_python` if set, and
     `<home>/.cache/wasi_python`;
   - **macOS:** `<home>/Library/Caches/wasi_python` (it reads no override);
   - **Windows:** `%LOCALAPPDATA%\wasi_python\cache` if set, and
     `<home>\AppData\Local\wasi_python\cache`;
   - **the homes:** on POSIX, `Path.home()` (`$HOME`) and the password database's home for this
     uid (`pwd.getpwuid(os.getuid()).pw_dir`) when the two differ, as they do under `sudo -E`,
     in containers and on CI. On Windows, `Path.home()` (`%USERPROFILE%`) only: Windows sets it
     at logon from the user's profile, and a process with another `%USERPROFILE%` is the
     embedder's own environment, trusted as `$WASI_PYTHON_CACHE` is (reading the system's
     profile folder would need `shell32`'s known-folder call for a case that, unlike POSIX's
     `$HOME`, ordinary tools do not produce).
   - **No home** (`Path.home()` raises `RuntimeError`, `pwd` raises `KeyError`: a container with
     no `$HOME` and a uid the password database does not list): that home gives no default and
     none is judged for it; the call goes on. Such a process has no default cache of its own
     either (`_module` keeps modules in memory), and the README says so.

Each is refused as the module cache is today: a writable grant or `root` **at, inside or above**
any of them is a `ValueError` before any work. **Every label begins "the module cache"**, so
the existing checks that match the message's start hold unchanged (criterion 7): the call's own
is exactly "the module cache", as today; the others are "the module cache `$WASI_PYTHON_CACHE`
names (<path>)" and "the module cache in the platform's default folder (<path>)". When the
call's own is also one of the others, it is judged once, under the call's own label. A read-only
grant over a cache stays allowed, as today: it cannot write.

**The cache's path as written** is judged, not only its resolved folder. `_chain` resolves the
path (`os.path.realpath`) and judges the resolved folder and its ancestors; a link on the path
as written lies outside that chain. With `$WASI_PYTHON_CACHE=/data/link/cache` and `link`
inside `/data`, a writable grant at `/data` would pass, and the guest could replace `link` with
a folder of its own: the next call's cache would be the guest's (the review, EXECUTED on
`_chain`). So a cache's chain also holds the identity of every existing prefix of
`Path(path).absolute()`, each by `identity_of` (links followed), and a writable grant or root at
or above any of them is refused as one above the resolved folder is. The prefixes keep their
`..` (`pathlib` does not collapse it, `os.path.abspath` does): the system walks a link and then
climbs from where it leads, so `work/a/link/../../c` passes through `work/a` and `link`, which a
spelling collapsed to `work/c` would leave out (the build review's M1, EXECUTED). **The limit,
said in the README:** the folders judged are those on the path as written and those holding a
link on it; a folder met only inside a link's target, when that target itself climbs through
another link (`a/link -> ../m/n/..` with `m/n -> x/y`: a writable grant at `m` passes), is not
judged (the build review's confirmation, L5). The full rule, resolving one component at a time
and judging every folder that holds a link met on the way, is reserved after 0.1.0 (the lane's
decision). This is the same on every
system. It is applied to the caches, which this specification guards. The runner's own code and
the host Python's folders are named by the runner itself from its own `__file__` and
`sysconfig`, so a link on their path is the installer's, not an argument's. The artifact set is
an argument too (`artifacts=`, `$WASI_PYTHON_ARTIFACTS`), checked only against its own
`SHA256SUMS` (`_artifacts.py:181-197`), so a link on its path inside a writable grant could let
a guest swap a later call's interpreter; but a set planted there is wasm under the wall, not
native code in the host, so it is outside this specification's subject, and the path-as-written
rule for it is reserved (the roadmap, after 0.1.0; the confirmation read's L8). The other
runtime folders keep the resolved chain.

**A cache not made yet** is judged by its deepest existing ancestor, the rule the judge already
applies to a missing runtime folder (`_places._chain`): a writable grant or root at or above
that ancestor is refused, since the guest could make the cache below it. One case that rule
misses today is closed here: **a root still to be made** and a cache still to be made, either
inside the other. Both have no identity yet, and both carry the same deepest existing ancestor;
the root is refused when, below that ancestor, **either list of missing components is a leading
part of the other** (a root above the cache would come to hold it; a root inside it would make
the cache folder, at the umask's mode, when it is made). The components are compared as
`unicodedata.normalize("NFC", c).casefold().rstrip(" .")` on every system: a compare by
spelling is safe here because it can only refuse more (a case-sensitive Linux folder `Cache`
beside `cache` is refused too; `é` spelled two ways is one name on APFS; Windows drops a
trailing dot or space), and a component not made yet has no link, no 8.3 short name and no
identity to compare instead. A root beside the cache under the same ancestor is not refused.

**Only the call's own cache is made.** `_runtime_folders` makes the call's own cache first, as
today, so it is judged as it will be. The other two are never made by a call that does not use
them: a call with `cache_dir=False` leaves nothing on disk, and one with a cache of its own
makes no default folder.

**Not covered, and said so** (Decision 5): a folder another call or process passes as its own
`cache_dir` is unknowable to this call. A rule that judged every cache this process has used so
far would refuse a call or not by the order calls ran in; this specification keeps the judge a
function of the call's arguments and the process's environment. `cache_dir` and
`$WASI_PYTHON_CACHE` are trusted input, as the artifact folder is.

### 2. Where it lives

- `_platform.py` gains `default_cache_dirs(home) -> tuple[Path, ...]` on `_Posix`, `_Darwin`
  and `_Windows` (and in the `_Platform` protocol), beside `default_cache_dir`, which stays. The
  password-database home is read inside `_Posix`, so no platform branch leaves `_platform.py`.
- `_engines.py` gains one function beside `_cache_dir`, which returns every cache the process
  could use for a given `cache_dir`, each with the label the judge's message uses, the call's
  own first and the rest without duplicates by path. It asks for the home folders inside a
  `try` (Decision 1, "No home").
- `_places._walk_grants` takes those caches; `_runtime_folders` makes only the call's own and
  lists all of them. **`_judge` keeps its `runtime` list of 3-tuples** `(name, identity,
  chain)`, so `tests/unit/test_runner_grants.py:156-175`, which calls it with hand-made
  3-tuples, is unchanged; the root-still-to-be-made rule takes the caches' missing components
  as a separate keyword argument, `missing: Sequence[tuple[str, tuple[str, ...]]] = ()` (each a
  label and the components below the deepest existing ancestor), with an empty default.
  `_chain` (or a sibling for the caches) also returns a missing folder's missing components and
  the identities of the existing prefixes of the path as written.
- `_call.py:145` and `_sessions.py:971` pass the caches in. `Session` loads its module before
  it walks (`_sessions.py:974-976`), as today; its walk still refuses before any guest code runs.

The builder may shape the signatures otherwise; the contract is the one above.

### 3. Defence in depth: a cache folder at 0700, a `.cwasm` at 0600

The rule is the fix. Behind it, POSIX `private()` asks for what the runner itself makes and a
guest, under the usual umask, does not:

- **a cache folder**: a directory, not a link (`lstat`), owned by this user, with **no bit for
  group or other** (`st_mode & 0o077 == 0`; `0700`, or stricter);
- **a `.cwasm`**: a regular file, not a link, owned by this user, with no bit for group or
  other (`0600`, or stricter), and **one name** (`st_nlink == 1`).

The runner makes both so already (`mkdir(mode=0o700)`, `mkstemp`, `os.replace`, which leave a
file with one name); a guest's `mkdir` gives `0755` and its `open` gives `0644` under umask
`022`, since WASI preview 1 has no `chmod`. Under umask `077` a guest's files are `0600` too,
and this defence gives nothing; the rule still holds. The warning names the mode wanted: "it
must be a directory owned by this user that no one else may read, write or enter (mode 0700)",
and "a file … (mode 0600) with one name".

**What the modes stop, and what they do not.** They read *how a file or folder was made*. They
stop a file or folder a guest makes. They do **not** stop a guest that reaches a cache in use
and rewrites the runner's own `.cwasm` in place: the file keeps its owner and its `0600` (the
review, EXECUTED: a `0600` file rewritten by a guest's `open(…, 'wb')` stays `0600`). Every
cache in use holds that file, so the modes guard only a cache never used for that digest. The
argument the digest record fails on below applies to them too: a guest that can reach the cache
can change what is there. **The rule (Decision 1) is the guard; the modes are a filter on new
files.** They are still worth having: they close a guest's new file wherever a residual route
remains (a cache passed as another call's `cache_dir`, a `$WASI_PYTHON_CACHE` that changes
between calls), they cost an existing cache nothing, and they make a planted file loud.

**`st_nlink == 1`, decided yes.** WASI preview 1 has `path_link`, so a guest that can reach a
cache and a runner-made `0600` file elsewhere on the same file system (another cache, or
another digest's file) can give that file a second name in the cache without writing a byte;
the mode and owner checks would pass. The runner's own files never have two names, so the check
refuses nothing it wrote, and costs nothing (`lstat` already reads it). On Windows `os.lstat`
reports `st_nlink` too, and a hard link there needs no privilege, so the check applies on both.

**The swap between the check and the load.** `private()` takes an `lstat`; wasmtime-py's
`Module.deserialize_file` then opens the path itself (it takes no descriptor), so a file
swapped between the two is not the file checked. The runner takes a second `lstat` after the
load and compares `(st_dev, st_ino, st_size, st_mtime_ns)` with the first; on a difference it
discards the loaded module and compiles. That narrows a window only a guest the rule failed to
stop can use. A row holds it (the confirmation read's L9):
`test_a_cwasm_swapped_between_its_check_and_its_load_is_discarded` hands `_module_miss` a
stand-in for wasmtime-py as its `wt` argument, whose `Module.deserialize_file` swaps a `0644`
module in and then loads; no `wasi_python` name is patched.

**What happens to what is there:**

- **A `.cwasm` that fails** (`0644`, a link, a second name, another owner) in a folder that
  passes: it is never loaded. The module is compiled, and the runner's own file, written `0600`
  beside it, takes its place by `os.replace` (a rename replaces a link itself, never its
  target, and drops a hard link's extra name, never the file elsewhere). The counts read
  compiled 1, loaded 0, written 1; the warning names the file once. Today such a file is left
  in place and recompiled around on every process's first call.
- **A folder at a `.cwasm`'s name** (a guest's `mkdir` could leave one): it is not replaced,
  since `os.replace` onto a folder raises. The module is compiled and kept in memory, the
  warning names it, and the call goes on. **Any `OSError` from writing or replacing** a `.cwasm`
  does the same, so no state of the cache folder makes a call fail; today a raising
  `os.replace` is re-raised by the `except BaseException` around it (`_engines.py:177-179`).
- **A cache folder that fails** (`0755`, a link, another owner): nothing in it is read or
  written; the module is compiled and kept in memory; a warning names the folder, as today for
  a folder others may write. The runner never `chmod`s a folder it finds: it cannot tell a
  folder it made from a guest's. An embedder who made `$WASI_PYTHON_CACHE` by hand at `0755`
  runs `chmod 700` once; the warning says so.
- **An existing cache made by the runner** is `0700` with `0600` files (EXECUTED above) and
  loads as before.

**A digest record is out of scope.** The review suggests a record, written only by the runner,
of each `.cwasm`'s SHA-256, checked before loading. It is not built here, for three reasons:
a guest that can reach the cache can rewrite a record kept beside it, so against this route it
adds nothing the rule does not; a record that a guest could not rewrite needs a key kept
elsewhere, which only moves the trusted folder, and that folder needs this same rule; and
checking it reads the whole of each `.cwasm` (253,998,072 bytes for this set's unmetered
snapshot module, `d734fbea…-wasmtime49.0.0-plain.cwasm`, EXECUTED) on every process's first
load, where wasmtime maps it. The review itself calls the rule "the real fix".

### 4. Windows: what `private()` can check there, and what it cannot

Windows has no mode bits, and a guest there writes as this user through wasmtime, so its file
gets the folder's inherited access list exactly as the runner's own file does. After this
specification, Windows `private()` checks what it can without reading security descriptors:

- **can check:** the folder is a directory and the file a regular file, neither is a reparse
  point (a symbolic link or a junction): `os.lstat(path).st_file_attributes &
  stat.FILE_ATTRIBUTE_REPARSE_POINT == 0`, and the file has one name (`st_nlink == 1`). A
  planted link or second name is refused and replaced (Decision 3); a junction as the cache
  folder is not used.
- **cannot check:** who wrote the file, or who else may write the folder. Its owner is this
  user whether the runner or a guest wrote it; its access list is inherited the same way.
  Telling them apart would take the runner setting a protected access list of its own on every
  folder and file it writes and requiring it on load (`SetSecurityInfo` and `GetSecurityInfo`
  through `advapi32`), which is a later specification (the roadmap's reserved line), not this
  one: it adds a ctypes surface `_platform.py` has little room for under its ceiling (1,407 of
  1,500 lines today, about 1,445 after this specification). Even then it would refuse a guest's
  *new* file only: a guest that rewrites the runner's file in place keeps its access list, as on
  POSIX it keeps its `0600` (Decision 3).
- **Folders outside the profile:** a folder made directly under a drive (`C:\cache`) inherits
  write access for every authenticated local user, so `cache_dir` or `$WASI_PYTHON_CACHE` there
  is writable by other users; the default, under `%LOCALAPPDATA%`, is not. The README says so
  (Decision 5).

So on Windows the cache is guarded by Decision 1's rule alone, and the README says so
(Decision 5). The change is about ten lines in `_Windows.private`.

**The deferral of the protected access list past 0.1.0 is agreed** by the pre-build review
("Windows: is the deferral safe? Yes, for 0.1.0"), on the conditions that H1's every-default
rule and M2's path-as-written rule are in this specification (Decision 1) and the README states
the Windows limit (Decision 5). Both are; the deferral stands.

### 5. The README and the CHANGELOG

**README, "Safety", the runtime folders bullet** (lines 1044 to 1048) becomes:

> - a writable grant or `root` at, inside or above the runtime's own folders
>   is refused, since later calls and processes trust them: the stdlib folder
>   (or the temporary folder that holds it), the artifact set, every module
>   cache this process could use (the call's own, the folder
>   `$WASI_PYTHON_CACHE` names, and the platform's default, as this process
>   computes it and without `$XDG_CACHE_HOME` or `%LOCALAPPDATA%`, under
>   `$HOME` and, on POSIX, the home the system gives this user; whatever the
>   call's `cache_dir`, made or not, and by every folder on its path as
>   written, links included), the code of `wasi_python` and
>   wasmtime-py themselves, and the host Python's own `stdlib`,
>   `site-packages` (the user's too) and `bin` (or `Scripts`) folders. So …

And after the bullet's "… are refused", added after the build review's confirmation (L5):

> For a cache, the folders judged are those on its path as written and
> those holding a link on it; a folder reached only inside a link's target,
> when that target itself climbs through another link, is not judged. So do
> not spell a cache's path through links that a grant you give an untrusted
> guest can reach;

**README, the module-cache paragraph** (lines 942 to 947), its first sentences become:

> The compiled module is cached as a `.cwasm` in the user cache directory, or
> in `$WASI_PYTHON_CACHE` (an absolute path: a relative one names a different
> folder in each working folder), only in a folder at mode `0700` holding
> files at `0600` with one name, as the runner makes them (a `.cwasm` is
> native code); a file or folder made otherwise, as a guest's would be, is
> compiled around and never loaded. That stops a file a guest makes, not one
> it rewrites in place, so the guard is that no guest can reach the cache at
> all (see "Safety"). `cache_dir=False` keeps it in memory only, and so does
> a process with no home folder and no `$WASI_PYTHON_CACHE`. On Windows the
> runner can check only that the folder and its files are not links, not who
> wrote them, so `cache_dir` and `$WASI_PYTHON_CACHE` must name a folder only
> you can write; the default, in your own profile, is one, and a folder made
> outside your profile (directly under `C:\`, say) is writable by every local
> user unless you change its permissions.

**README, the `cache_dir` parameter lines** (README:2740 and :2912), "a folder only you can
write" becomes "a folder only you and the runner write: never one a guest is granted, in this
or another call".

**README, "Not protected"**, two items added:

> the module cache's contents, if anything but the runner can write there: a
> writable grant, a mount provider, another program or another user that can
> write a folder of compiled modules can run code in the host process at the
> next call, outside wasm (the runner refuses a grant or `root` over every
> cache it knows of, and on POSIX loads only files at `0600` in a folder at
> `0700`, which stops a file a guest makes, not one it rewrites in place; a
> folder you pass as another call's `cache_dir` it cannot know);
> `cache_dir` and `$WASI_PYTHON_CACHE` are trusted input, as the artifact
> folder is: name only folders that no guest and no other user can write;

**The CHANGELOG line**, under the one unreleased section (`## 0.1.0a8 — unreleased`, which
becomes 0.1.0):

> - **Every module cache is guarded, whatever a call's own `cache_dir`** (spec 113; the 0.1.0
>   security review's H1). A call with `cache_dir=False` or a cache of its own no longer passes
>   a writable grant or `root` over the cache other calls and processes use: the judge now
>   refuses one at, inside or above the call's own cache, `$WASI_PYTHON_CACHE` and every
>   platform default a process of this user could compute (with or without `$XDG_CACHE_HOME`
>   or `%LOCALAPPDATA%`, under `$HOME` and the system's home), made or not, and through every
>   folder on the cache's path as written, in `run`, `run_async` and `Session`. Before, a guest
>   given such a grant could write a compiled module under the snapshot's public name that the
>   next call loaded as native code. On POSIX a cache folder is used only at `0700` and a
>   `.cwasm` loaded only at `0600` with one name, as the runner makes them; a file that is not
>   is compiled again and replaced, never loaded. That stops a file a guest makes, not one it
>   rewrites in place: the refusal is the guard. On Windows the cache refuses links and second
>   names; it cannot tell who wrote a file, and the README says so. No public name, artifact
>   byte or guest-visible errno changes.

### 6. The checks first, and what they hold

One new file, `tests/unit/test_runner_module_caches.py`, written before the fix and run by
node id on main's code: the draft's seventeen rows (EXECUTED, `build/113/checks-on-main.txt`:
15 failed, 2 passed), then, after the pre-build review, all **thirty-three** rows (EXECUTED,
`build/113/checks-on-main-1b.txt`: **28 failed, 5 passed** in 17.03 s).
The run-level rows need the runner and the artifact set (`needs.need("runner", "artifact
dir")`); a module-scoped fixture compiles the snapshot once in memory (`cache_dir=False`) so no
row writes a 254 MB module to disk on its way to the judge. The mode rows need only wasmtime and
a module of a few bytes. Every verdict is a refusal, a file mode or a count from `stats()`;
none is a time.

| row | holds | on main |
|---|---|---|
| `test_a_writable_grant_over_another_calls_cache_is_refused[<caller>-<own>-<victim>]`, 18 rows: caller `run`, `run_async`, `Session`; own cache off or elsewhere; victim the cache `$WASI_PYTHON_CACHE` names (made), the platform default under a fresh home (not made), or the **fallback**: the default without `$XDG_CACHE_HOME`/`%LOCALAPPDATA%` under a fresh home while both name other folders (not made; on macOS, which reads no override, the same folder as the default) | step 1 of the probe is a `ValueError` naming the module cache *and which one* (`$WASI_PYTHON_CACHE` or "default folder"), nothing is planted, and a cache the call does not use is not made; were it not refused, step 2 runs in a fresh process with every default and its `stats()["loaded"]` is printed in the failure | **fail** ×18: "was not refused … loaded 1 compiled module(s) the guest wrote" |
| `test_a_writable_grant_at_or_inside_another_calls_cache_is_refused[at\|inside]` | the grant is the `$WASI_PYTHON_CACHE` folder, or a folder inside it, with `cache_dir=False`: refused, naming `$WASI_PYTHON_CACHE` | **fail** ×2: "DID NOT RAISE" |
| `test_a_cache_reached_through_a_link_in_a_writable_grant_is_refused[off\|own]` | `$WASI_PYTHON_CACHE` is `data/link/wasi_python`, `link` inside the granted `data`, resolving outside it; the call's own cache off, or that cache its own (`cache_dir=None`): refused. Skips only where no link can be made, naming the errno | **fail** ×2: "DID NOT RAISE" (the `own` row shows the path-as-written gap apart from H1) |
| `test_a_cache_reached_through_a_link_then_dotdot_in_a_writable_grant_is_refused[1\|2]` (added after the build review, M1) | `$WASI_PYTHON_CACHE` is `a/link/../c` or `a/link/../../c`, `link` inside the granted `a` and leading to `x/y`, `cache_dir=False`: refused | the two-`..` row **fails** on `a891dec5` ("DID NOT RAISE", `build/113/dotdot-on-a891dec5.txt`); the one-`..` row passes there |
| `test_a_root_still_to_be_made_that_would_hold_a_cache_is_refused[off\|elsewhere]` | a root to be made above a `$WASI_PYTHON_CACHE` to be made, and one inside it: refused, neither made; a root beside it passes; a call that keeps no cache, or its own elsewhere, makes neither `$WASI_PYTHON_CACHE` nor the platform default | **fail** ×2: "DID NOT RAISE" |
| `test_every_default_a_process_of_this_user_could_compute_is_listed` | `_Linux`, `_Darwin` and `_Windows` `default_cache_dirs(home)`, with both overrides set: each lists the override's folder and the one without it; on a POSIX host also the password database's home | **fail**: `AttributeError: … no attribute 'default_cache_dirs'` |
| `test_a_process_with_no_home_folder_still_runs` | `Path.home()` raising and, on POSIX, `pwd.getpwuid` raising: `run(…, cache_dir=False)` exits 0 | pass (holds Decision 1's "No home": main never asks for the home with `cache_dir=False`) |
| `test_a_cwasm_others_may_read_is_compiled_again_and_replaced_never_loaded` | POSIX: a `0644` `.cwasm` in a `0700` folder: compiled 1, loaded 0, written 1, the file now `0600`. Windows: loaded, recorded | **fail** (POSIX): loaded 1, compiled 0 |
| `test_a_cache_folder_others_may_enter_is_not_used` | POSIX: a `0755` folder holding a `0600` `.cwasm`: compiled 1, loaded 0, written 0, a warning naming the folder, nothing written. Windows: loaded, recorded | **fail** (POSIX): loaded 1, compiled 0 |
| `test_the_runner_makes_its_cache_folder_0700_and_its_files_0600` | a fresh cache: the folder `0700`, the file `0600` (POSIX); compiled 1, written 1 everywhere | pass (holds the runner's own modes) |
| `test_a_cwasm_that_is_a_link_is_never_loaded` | a link in the cache to a `0600` module: never loaded, never written through, on every system | pass on POSIX; on Windows main loads it (INFERRED from `_platform.py:1389-1392`; the Windows leg shows it) |
| `test_a_cwasm_with_a_second_name_is_never_loaded` | a hard link in the cache to a `0600` module elsewhere: never loaded, the file elsewhere unchanged, on every system | **fail**: loaded 1 |
| `test_a_cwasm_swapped_between_its_check_and_its_load_is_discarded` (added in the build, L9) | a stand-in `wt` swaps a `0644` module in after the check: compiled 1, loaded 0, written 1, the name now the runner's `0600` file | **fail** on main's code (`build/113/swap-on-main.txt`): loaded 1 |
| `test_a_folder_at_a_cwasm_name_is_skipped_not_raised` | a folder at the `.cwasm`'s name: compiled 1, loaded 0, written 0, no exception, the folder left | pass (holds Decision 3's "not replaced" against a fix that would raise) |
| `test_a_cache_folder_that_is_a_link_is_not_used` | the cache folder a symbolic link (POSIX) or a junction (Windows, `_winapi.CreateJunction`) to a `0700` folder with a `0600` module: compiled 1, loaded 0, written 0 | pass on POSIX; on Windows main loads it (INFERRED; the Windows leg shows it) |

The Windows branches of the two mode rows record Windows' answer (Decision 4) rather than skip,
as `test_runner_refuses_a_cache_others_can_write` does. The link row skips only where the host
cannot make a link, naming the errno.

**Existing checks that may now refuse.** The judge's own calls run with
`$WASI_PYTHON_CACHE=build/cwasm-cache` (`tests/checks/conftest.py`) and the user's default cache
beside it. A check that grants `build/`, the repository or the home folder writable, with its
own cache off, would now be refused. The builder lists every such row in the claim list with
its reason, or records that there is none (INFERRED: none; the checks' writable folders are
under `build/harness/` or the guest temporary folder, siblings of the cache).

**Existing assertions on the message and on `_judge`** (the review's M3, READ):
`tests/checks/test_v1_2_hostile_guest.py:688`, `:699`, `:731`, `:745` and `:748` match
"holds the module cache" or "is inside the module cache", and
`tests/unit/test_runner_grants.py:156-175` calls `_places._judge` with hand-made 3-tuples
labelled "the module cache". Decision 1 keeps the call's own label exactly "the module cache"
and every other label starting with it, and Decision 2 keeps `_judge`'s 3-tuple with the new
rule as a keyword argument, so all six stay unchanged, byte for byte (criterion 7).

### 7. Kind: parallel-safe, not structural, measured

AGENTS.md calls a specification structural when its change to `src/` adds a module-level
mutable or lock outside `_process.py`, a use of wasmtime-py's private API outside
`_wasmtime_ffi.py`, a platform branch outside `_platform.py`, a test seam not on the process
object, or takes a module past the size ceiling or a function past 80 lines. Against each
(READ on `1875d4cd`, sizes EXECUTED with `wc -l` and the judge's own function scan):

- **module-level mutable or lock:** none; the caches are computed per call from the arguments
  and the environment.
- **private API:** none; `Module.deserialize_file` and `serialize` are public.
- **platform branch:** none outside `_platform.py`. The Windows checks go in `_Windows.private`
  and the POSIX ones in `_Posix.private`; the defaults in each class's `default_cache_dirs`,
  the password database read in `_Posix`. The compare of Decision 1 and the path-as-written
  chain are the same on every system.
- **test seam:** none; the checks set environment variables and call `_engines._module_miss`,
  `PLATFORM.default_cache_dir` and each platform class's `default_cache_dirs`. The one patch is
  of the standard library (`Path.home`, `pwd.getpwuid`, for the no-home row), never of a
  `wasi_python` name.
- **module ceiling (1,500):** `_platform.py` 1,407 (about +38, INFERRED: `private` about +16,
  `default_cache_dirs` about +22 over three classes and the protocol), `_places.py` 524 (about
  +45), `_engines.py` 236 (about +35); the builder records each.
- **function ceiling (80):** `_judge` is 37 lines, `_runtime_folders` 40, `_walk_grants` 34,
  `_chain` 21, `_module_miss` 52, `_Posix.private` 17, `_Windows.private` 4 (EXECUTED, `ast`); each
  grows by about ten. The builder records each; none may pass 80, and
  `LONG_FUNCTIONS` and `SEAM_ALLOWED` do not change.

So it is not structural, and the reviewer applies the rubric's rows only as rule 4a of the
checklist asks. It is still reviewed before it is built: it is runner code and a security fix.

## Intent

After this specification, no argument a call takes opens a way for its guest to write where the
runner keeps compiled modules. A call that keeps nothing on disk, or keeps its own cache, still
refuses a writable grant or root over the cache the next call will read, made or not, as any
process of this user would compute it, and through any folder on its path, in `run`,
`run_async` and `Session` alike. Behind that rule, on POSIX the cache loads only files made the
way the runner makes them: a folder at `0700`, files at `0600` with one name. That stops a file
or folder a guest makes; it does not stop a guest that rewrites a file the runner made, so the
rule is the guard. A file that fails is compiled again and replaced, never run. On Windows the
cache refuses links and second names, and the README says plainly that the rule is the only
guard there. The README also says what stays the embedder's to keep:
`cache_dir` and `$WASI_PYTHON_CACHE` are trusted input, and anything that can write a folder of
compiled modules can run code in the host.

## Design


### The commits, in order

Each commit is green on its own but the first two, which carry the checks seen failing
(AGENTS.md, rule 3) and are this specification's draft and its revision.

1. **The specification, the roadmap lines and the checks** (the draft, `6559c149`): seventeen
   rows of Decision 6, fifteen of them red on main's code, and the file's line in the
   `own-runner` shard (`test_release_shards_cover_the_judge` green with it, EXECUTED).
2. **The revision after the pre-build review** (the review cherry-picked, then this text): the
   rows for every default, the path as written, at and inside, the root inside, the second name,
   the folder at a `.cwasm`'s name, the cache folder as a link and no home; thirty-three rows,
   twenty-eight red on main's code.
3. **The defaults** (Decision 1's item 3): `default_cache_dirs` in `_platform.py`. The method
   row goes green.
4. **The rule** (Decisions 1 and 2): `_engines`' list of caches with their labels and the
   no-home guard, `_places`' judge of every cache by its path as written and of a root still to
   be made over or inside a cache still to be made, the two call sites. The twenty-four
   run-level rows go green.
5. **The modes** (Decisions 3 and 4): `_Posix.private` at `0o077` with one name,
   `_Windows.private`'s kind, reparse-point and one-name checks, a refused `.cwasm` replaced
   unless it is a folder, any `OSError` of the write kept in memory, the `lstat` after the load.
   The mode rows go green.
6. **The README and the CHANGELOG** (Decision 5).

### The roadmap line

> Reserved: 113 (every module cache is guarded: …; the 0.1.0 security review's H1, High;
> parallel-safe, runner code, not structural, reviewed before build; **before 0.1.0**, which
> waits on it; …).

Written into `../roadmap.md` with this draft, beside the reservations of 115 and 116 for the
0.1.0 structural review's two Mediums, both after 0.1.0, and an unnumbered reservation for
Decision 4's protected access list on Windows.

## Scope

In: Decisions 1 to 6. Out:

- **H2** (code planted in a reused root runs on `import reportlab`): its own specification.
- **A digest record beside the cache** (Decision 3): not built.
- **A protected access list on Windows** (Decision 4): a later specification, reserved; the
  pre-build review agreed to the deferral.
- **The path as written for the other runtime folders** (Decision 1): the runner names them
  itself; they keep the resolved chain.
- **Caches named by other calls' `cache_dir`**, and a changed `%USERPROFILE%`: trusted input,
  said in the README (Decision 1).
- **Any change to what the guest sees**: no errno, no file, no limit, no default but the
  refusals added.

## Acceptance criteria

1. **The plant is refused, in every caller:** the eighteen rows of
   `test_a_writable_grant_over_another_calls_cache_is_refused`, the two of
   `test_a_writable_grant_at_or_inside_another_calls_cache_is_refused`, green on three systems,
   each seen failing first on `1875d4cd` (`build/113/checks-on-main-1b.txt`), each refusal
   naming which cache.
2. **Every default a process of this user could compute is judged:**
   `test_every_default_a_process_of_this_user_could_compute_is_listed` and the six `fallback`
   rows of criterion 1 green, seen failing first; on Linux and Windows the `fallback` rows judge
   a folder this process's own default is not.
3. **The cache's path as written is judged:** the two rows of
   `test_a_cache_reached_through_a_link_in_a_writable_grant_is_refused` and the two of
   `test_a_cache_reached_through_a_link_then_dotdot_in_a_writable_grant_is_refused` (one `..`
   and two) green on POSIX and on Windows where a link can be made (a skip names its errno in
   the landing notes), seen failing first (the two-`..` row on `a891dec5`).
4. **A root still to be made over or inside a cache still to be made is refused**, one beside it
   is not, and a call that does not use a cache makes none: the two rows of
   `test_a_root_still_to_be_made_that_would_hold_a_cache_is_refused` green, seen failing first.
5. **No home is not a failure:** `test_a_process_with_no_home_folder_still_runs` green on three
   systems.
6. **The modes on POSIX:** `test_a_cwasm_others_may_read_is_compiled_again_and_replaced_never_loaded`
   and `test_a_cache_folder_others_may_enter_is_not_used` green, seen failing first on POSIX;
   their Windows branches green on the Windows leg.
7. **No verdict moves but the claim list's:** the five message assertions of
   `tests/checks/test_v1_2_hostile_guest.py` (lines 688, 699, 731, 745, 748) and
   `tests/unit/test_runner_grants.py:156-175` unchanged and green; every existing row that newly
   refuses is named in the claim list with its reason, or the landing notes say there is none.
8. **The runner's own files, links, second names and folders:**
   `test_the_runner_makes_its_cache_folder_0700_and_its_files_0600`,
   `test_a_cwasm_that_is_a_link_is_never_loaded`, `test_a_cwasm_with_a_second_name_is_never_loaded`
   (seen failing first), `test_a_folder_at_a_cwasm_name_is_skipped_not_raised` and
   `test_a_cache_folder_that_is_a_link_is_not_used` green on three systems (a link row's skip on
   Windows named with its errno).
9. **The review's probe, re-run on the built tip:** `p50_cwasm_plant.py` (copied into this
   worktree's `build/113/`) stops at step 1 with the `ValueError`, and step 2 reports loaded 0;
   output in `build/113/`.
10. **Existing caches still load:** `test_runner_caches_the_compiled_module` and
    `test_fuel_does_not_depend_on_the_module_cache` green (a cache the runner made loads,
    compiled 0 and loaded 1, on the second process).
11. **Not structural, measured:** the sizes of `_platform.py`, `_places.py`, `_engines.py` and of
    `_judge`, `_runtime_folders`, `_walk_grants`, `_chain`, `_module_miss`, both `private`
    methods and each `default_cache_dirs` recorded, each under its ceiling; `LONG_FUNCTIONS` and
    `SEAM_ALLOWED` unchanged; the rules checks green.
12. **The README and the CHANGELOG** carry Decision 5's text (the Safety bullet, the
    module-cache paragraph, the two `cache_dir` parameter lines, the *Not protected* paragraph
    holding both clauses, the CHANGELOG line under the unreleased section).
13. **`tests/public_api.txt` is unchanged**; `ruff check`, `ruff format --check` and `mypy` are
    clean; no code file names a specification, review, finding or `context/` path.
14. **The dispatch:** the release workflow on the built tip, every red line a growth line of
    another entry or G7; the run id in the landing notes; the Windows legs read.

Fourteen criteria.

## For the lane

- **Kind:** parallel-safe; lands in the next wave, before the 0.1.0 tag; rebased onto the
  wave's tip in the lane's order, every conflict named.
- **Files it shares with others:** `README.md` (the Safety bullet, the cache paragraph, the
  `cache_dir` lines, *Not protected*, which H2's specification may also touch), `CHANGELOG.md`,
  `context/roadmap.md`, `tests/release_shards.toml` (one line). Its `src/` files are shared
  with no specification in flight.
- **The claim list** (each line "113:"): **new checks**, the thirty-three rows of Decision 6;
  **retired:** none; **lost passes:** none expected (criterion 7); **fuel and bytes:** none. The
  **judge hash changes** in `tests/unit/test_runner_module_caches.py` (new) and
  `tests/release_shards.toml` (one line in `own-runner`).
- **The flags** (paste-safe):

  ```
  --accept "113: every module cache a process of this user could use is judged in every call, whatever its own cache_dir: a writable grant or root at, inside or above the call's own cache, the folder WASI_PYTHON_CACHE names or any platform default (with or without XDG_CACHE_HOME or LOCALAPPDATA, under HOME and the system's home), made or not, or through a folder on the cache's path as written, is refused in run, run_async and Session; on POSIX the cache folder is used only at 0700 and a .cwasm loaded only at 0600 with one name, one that is not compiled again and replaced; Windows refuses links and second names in the cache"
  --accept-judge "113: one unit file of thirty-three rows reproduces the 0.1.0 security review's planted compiled module by every route its pre-build review named and holds the cache's modes, in the own-runner shard on three systems; no existing expectation edited"
  ```

- **Dry-run needs:** one dispatch on the built tip; the builder reads the `unit` group on the
  three systems, the Windows leg above all (Decision 4).

## Disposition of the pre-build review

The review (`../reviews/113-every-module-cache-is-guarded-spec-2026-10-21.md`) re-ran the
draft's seventeen rows, probed a rewrite in place and a link on the cache's path, and agreed to
the Windows deferral on two conditions. Each finding, and where its answer is:

1. **H1, the default judged only as this process computes it** — fixed in the specification:
   Decision 1's item 3 judges every default a process of this user could compute
   (`default_cache_dirs(home)`, with and without `$XDG_CACHE_HOME` and `%LOCALAPPDATA%`, under
   `$HOME` and on POSIX the password database's home); Decision 2 places it in `_platform.py`;
   the six `fallback` rows and the method row are written and fail on main (Decision 6);
   criterion 2. On Windows a changed `%USERPROFILE%` is trusted input, with the reason.
2. **M1, the modes stop a new file, not a rewrite in place** — fixed in the text: Decision 3's
   "What the modes stop, and what they do not", the Intent, the One line, the README's cache
   paragraph and *Not protected* item, the CHANGELOG line. `st_nlink == 1` decided yes, on POSIX
   and Windows, with its reason and a row (`test_a_cwasm_with_a_second_name_is_never_loaded`,
   fails on main).
3. **M2, a link on the cache's path inside a writable grant** — fixed in the specification:
   Decision 1's "The cache's path as written", every existing prefix of `os.path.abspath(path)`
   judged; held to the caches, with the reason for the other runtime folders; two rows, failing
   on main; criterion 3.
4. **M3, the labels and `_judge`'s tuple** — fixed in the specification: every label begins "the
   module cache", the call's own exactly that (Decision 1); `_judge` keeps its 3-tuple and the
   new rule is a keyword argument with an empty default (Decision 2); criterion 7 names the six
   assertions that stay unchanged.
5. **L1, a root inside a cache, both still to be made** — fixed: either list of missing
   components a leading part of the other (Decision 1); the root row asserts it.
6. **L2, the spelling compare** — fixed: NFC, casefold, trailing dots and spaces stripped
   (Decision 1).
7. **L3, the replace and its races** — fixed: a folder at the name is not replaced, any
   `OSError` of the write keeps the module in memory, an `lstat` after the load is compared
   with the one before (Decision 3); a row holds the folder case; the swap has no row, with the
   reason.
8. **L4, `Path.home()` on every call** — fixed: a home that cannot be found gives no default
   and the call goes on (Decision 1, "No home"); the README says such a process has no default
   cache (Decision 5); a row holds it.
9. **L5, gaps in what the checks hold** — fixed: the plant rows assert which cache refused and
   that a default not used is not made; at and inside rows; the root row with its own cache
   elsewhere, asserting no default is made; a junction as the cache folder on Windows
   (`test_a_cache_folder_that_is_a_link_is_not_used`).
10. **L6, README wording** — fixed in Decision 5: the `cache_dir` parameter lines, folders
    outside the Windows profile, `$WASI_PYTHON_CACHE` as an absolute path.
11. **L7, the builder's self-check list** — answered: it is written under *Landing notes*, "The
    builder's self-check", before the build review is asked for, as 107 and 111 did; at this
    stage there is no build to check.
12. **The Windows deferral** — kept, citing the review's agreement and its two conditions, both
    met (Decision 4).

The confirmation read (the same reviewer, `35ec623f`) confirmed H1 to M3 and the Lows, and
raised three Lows, answered in the build:

13. **L8, the reason for holding the path-as-written rule to the caches** — corrected in
    Decision 1: the artifact set is an argument too, but a set planted through a link is wasm
    under the wall, not native code; its rule is reserved in `../roadmap.md`, after 0.1.0.
14. **L9, the swap can have a row** — added:
    `test_a_cwasm_swapped_between_its_check_and_its_load_is_discarded`, a stand-in `wt` whose
    `deserialize_file` swaps a `0644` module in; it failed on main's code first (loaded 1,
    `build/113/swap-on-main.txt`) and passes on the build.
15. **L10, the method row on a Windows host** — `_Posix.default_cache_dirs` catches
    `ImportError`, `AttributeError` and `KeyError` around the password database; the row passes
    on the Windows leg (*Landing notes*).

## Disposition of the build review

The build review (`../reviews/113-every-module-cache-is-guarded-build-2026-10-21.md`,
`b39cd22b`, "lands once M1 is answered") found no High, one Medium and four Lows; each is
answered in `21cc7296`:

1. **M1, a `..` after a link drops the link's folder from the judged chain** — fixed:
   `_cache_chain` takes its prefixes from `Path(path).absolute()`, which keeps `..`, so each
   prefix's identity is the folder the system reaches (Decision 1). The reviewer's case is
   `test_a_cache_reached_through_a_link_then_dotdot_in_a_writable_grant_is_refused[2]`, failing
   on `a891dec5` ("DID NOT RAISE", `build/113/dotdot-on-a891dec5.txt`) and passing now, beside
   the one-`..` row `[1]`; criterion 3 names both.
2. **L1, two sizes off** — corrected in *The sizes*, remeasured on `21cc7296`, with why the
   first notes read 318 and 38.
3. **L2, a file gone between the two `lstat`s fails the call** — fixed: `_load` catches
   `OSError` around `private(cwasm)` and treats it as a miss (and `deserialize_file`'s
   `OSError` as a stale file). No row: the only way between the two `lstat`s is to patch
   `PLATFORM.private`, a seam the judge's rule would allow but the specification keeps out of
   its checks; the path is read in the diff.
4. **L3, an unusable cache folder is silent** — fixed: one helper, `_cache_warning`, gives
   "not using the module cache at …: <strerror>" there and "not writing the module cache at …"
   in `_store`.
5. **L4, the docstring says the compare closes the window** — fixed: `_load`'s docstring says it
   narrows, not closes, the window; criterion 12 names "the *Not protected* paragraph holding
   both clauses".

The confirmation (the same reviewer, `872cbf80`, "lands" once run 39644201639 reads green)
closed M1 and L1 to L4 and raised one Low that does not block:

6. **L5, a link inside another link's target is judged only by where it resolves** — documented
   now, fixed after 0.1.0 (the lane's decision, 2026-10-21): the README's Safety bullet states
   the limit and asks that a cache's path not be spelled through links a grant to an untrusted
   guest can reach; Decision 1 says the same; `../roadmap.md` reserves the full rule (resolve
   one component at a time, judge every folder holding a link met, a row for this case). No
   code changes, so no new run.

## One line

A call that does not use the shared module cache still refuses to give its guest a way to write
there, by any route a process of this user could take to it, and the cache loads no file or
folder a guest made.

## Landing notes

**Built** on `a891dec5` (2026-10-21), on the reviewed spec `fcd278de` and its confirmation read
`35ec623f`, from main `1875d4cd`; runner code only, judged against the main tree's frozen set
(`SHA256SUMS` `d0d91cef`) through `$WASI_PYTHON_ARTIFACTS`; nothing rebuilt. Every output named
here is under `build/113/` in the builder's worktree.

### The checks, each seen failing first

- The draft's seventeen rows on main's code: 15 failed, 2 passed (`checks-on-main.txt`,
  `modes-on-main.txt`). After the pre-build review, thirty-three rows: 28 failed, 5 passed
  (`checks-on-main-1b.txt`). L9's swap row, added in the build: failed on main's code, loaded 1
  (`swap-on-main.txt`, main's `src/` exported with `git archive 1875d4cd` and put first on
  `PYTHONPATH`).
- On the build, all **thirty-four** rows pass (EXECUTED, `checks-built.txt`, 27.15 s; again
  after the rename below, `after-rename.txt`).
- The existing checks criteria 7 and 10 name, by node id (EXECUTED, `existing-built.txt`): 46
  passed, 2 skipped (`test_runner_grants.py`'s two Windows-only rows, as on main):
  `test_v1_2_hostile_guest.py::test_a_bad_grant_is_refused_before_any_work` (the five message
  assertions), all of `tests/unit/test_runner_grants.py` (its `_judge` 3-tuple row), all of
  `tests/unit/test_runner_sets.py`, the three cache checks of `test_v1_4_embedding.py`
  (`test_runner_caches_the_compiled_module`, `test_fuel_does_not_depend_on_the_module_cache`,
  `test_runner_refuses_a_cache_others_can_write`) and
  `test_runner_tools.py::test_an_artifact_set_without_the_guest_package_is_refused` (the one
  check that patches `_walk_grants`). None was edited.

### The review's probe (criterion 9)

`p50_cwasm_plant.py`, copied to `build/113/probes/`, on the build (EXECUTED, `p50-built.log`):
step 0 compiles the plain reactor as before; **step 1 is refused**, `ValueError: grants[0] at /c
is writable and holds the module cache $WASI_PYTHON_CACHE names (…/fixtures/p50/xdg/wasi_python),
which later calls trust`; step 2, with every default, reports **compiled 1, loaded 0, written
1**. The probe's 471 MB of fixtures were removed after.

### The sizes (criterion 11; EXECUTED, `wc -l` and `ast` on `21cc7296`)

| module | base | built, after the build review | ceiling |
|---|---|---|---|
| `_platform.py` | 1,407 | **1,464** | 1,500 |
| `_places.py` | 524 | 585 | 1,500 |
| `_engines.py` | 236 | 329 | 1,500 |
| `_call.py` | 1,289 | 1,295 (the call's arguments, one per line, by `ruff format`) | 1,500 |
| `_sessions.py` | 1,120 | 1,120 | 1,500 |

Functions (lines, ceiling 80): `_judge` 52, `_runtime_folders` 48, `_module_miss` 42,
`_walk_grants` 38, `_load` 31, `_cache_chain` 25, `_store` 22, `_chain` 21, `_caches` 20,
`_cache_dir` 9, `_home` 7, `_cache_warning` 5, `_spelled` 4, `_file_stamp` 2; `_Posix.private`
18, `_Windows.private` 14, `_Posix.default_cache_dirs` 13, `_Windows.default_cache_dirs` 5,
`_not_used` 8, `_one_file` 4. `LONG_FUNCTIONS` and `SEAM_ALLOWED` unchanged; not structural.
On `a891dec5` `_engines.py` was 321 lines and `_module_miss` 41 (the build review's L1): the
first notes' 318 and 38 were measured before mypy's fix in `_module_miss` (three lines that
type its module).

### The fast tier

Two runs on three cores, each with the slot the lane grants (`build/slots/fast`, released at
its end; no `build/lane.lock`). On the build before the rename: 2,697 passed, **1 failed**,
`test_runner_package.py::test_every_runner_name_is_defined_in_one_module` (`_stamp` bound in
`_artifacts.py` and `_engines.py`), ratchet lost 0, grew 0 (`fast-tier.txt`). The helper was
renamed `_file_stamp`, and on `a891dec5` itself: **2,698 passed, 51 skipped, 0 failed** in
7 min 42 s; `643/889 pass · 0 gap · 42 blocked · 0 fail`, unit suite 2055/2064; ratchet lost 0,
absent 0, unrun 0, gained 0, grew 0 (EXECUTED, `fast-tier-a891dec5.txt`).

### The release workflow (criterion 14)

Run **39624848889** on `a891dec5`, dispatched by the builder with no other run live.

- **Attempt 1:** `build and judge (arm64 macOS)` failed at "Download the pinned inputs" on a DNS
  error (`curl: (6) Could not resolve host: www.python.org`, four times, EXECUTED
  `gh run view --attempt 1 --log-failed`), before any check ran; the jobs that need its set
  waited on it.
- **Attempt 2:** the lane re-ran the failed job alone (`gh run rerun --failed`), changing
  nothing. **Success**: 40 jobs passed (build and judge, two rebuilds, same-bytes, 32 judge legs,
  gather, three verify jobs); attest, publish and PyPI skipped, as on every dry run (EXECUTED,
  `gh run view 39624848889 --json jobs`).
- **The gather** (`release-record-2`, `build/113/record/`): **797/889 pass · 85 gap · 7
  blocked · 0 fail**, unit suite 4826/4856 with 30 skipped, three systems on `d4192605…`, set
  `d0d91cef`; the same counts as the 0.1.0 security review's run 39595555875 on main's
  `b2d4ccd0`.
- **The ratchet**, all 34 lines the run prints (the 32 judge legs and the build job's two;
  EXECUTED, the run's log, `run-39624848889-attempt2.log`): lost 0, absent 0, unrun 0, grew 0.
  No red line, so no GREW and no G7 line. The three own-guest legs read "gained 1", a pass
  gained, not a red line.
- **Windows:** the four Windows legs green (own-guest, own-runner, own-embedding,
  upstream-windows) and `verify (windows-2025)`; own-runner ran all thirty-four rows of the new
  file with none skipped (34 dots), so the link, junction and second-name rows and L10's method
  row ran on `_Windows`. Per system the suite reads darwin 2046/2054, linux 2046/2054, win32
  724/738 passed (8, 8 and 14 skipped).

### For the lane, as built

- **Claim list** (each line "113:"): **new checks**, the thirty-four rows of
  `tests/unit/test_runner_module_caches.py` (Decision 6's thirty-three and L9's swap row);
  **changed checks:** none (`tests/release_shards.toml` gains the file's line in `own-runner`);
  **retired:** none; **lost passes:** none; **fuel and bytes:** none grow; no artifact byte
  changes. The **judge hash changes** in `tests/unit/test_runner_module_caches.py` and
  `tests/release_shards.toml`.
- **The flags**, as in *For the lane*, with "thirty-three" read as "thirty-four" in
  `--accept-judge`:

  ```
  --accept "113: every module cache a process of this user could use is judged in every call, whatever its own cache_dir: a writable grant or root at, inside or above the call's own cache, the folder WASI_PYTHON_CACHE names or any platform default (with or without XDG_CACHE_HOME or LOCALAPPDATA, under HOME and the system's home), made or not, or through a folder on the cache's path as written, is refused in run, run_async and Session; on POSIX the cache folder is used only at 0700 and a .cwasm loaded only at 0600 with one name, one that is not compiled again and replaced; Windows refuses links and second names in the cache"
  --accept-judge "113: one unit file of thirty-four rows reproduces the 0.1.0 security review's planted compiled module by every route its pre-build review named and holds the cache's modes, in the own-runner shard on three systems; no existing expectation edited"
  ```

### Differences from the specification's text, each with its reason

1. `_judge`'s keyword `missing` holds (label, deepest existing ancestor, components), not
   (label, components): the rule compares the root's ancestor with the cache's, and the
   ancestor is not in the label.
2. The README's two `cache_dir` parameter lines are generated from the docstrings, so the text
   went into the three `cache_dir` docstrings of `runner.py` and the README's API block was
   written by `tests/harness/api.py --write`; `api.py --check` passes and
   `tests/public_api.txt` is unchanged.
3. A `.cwasm` that cannot be written (any `OSError`) gives a `RuntimeWarning`, "not writing the
   module cache at …", and the module stays in memory; the specification said only that the
   call goes on.
4. A cache folder that cannot be made or read (an `OSError` from `private()`) also leaves the
   module in memory, where it used to raise, with a warning (the build review's L3); the same
   rule, "no state of the cache folder makes a call fail".
5. The helper that compares two `lstat`s is `_file_stamp`: the fast tier found `_stamp` bound
   in `_artifacts.py` too (`test_every_runner_name_is_defined_in_one_module`), and the name was
   changed before the dispatch.

### The builder's self-check

```
Before you ask for a review:
- [x] rebased onto main's tip (or the named stacked base) today; the base commit in the Status
      line: main 1875d4cd, today's tip; nothing landed since.
- [x] CI run dispatched on this exact commit and read: 39624848889 on a891dec5, green on its
      second attempt (the first failed on a DNS error before any check); no red line; the
      Windows legs green.
- [x] every number from a measured run on this base, labelled EXECUTED; no growth.
- [x] "For the lane": the claim list, the exact flags beginning "113:", the wave kind
      (parallel-safe), dry-run needs (none beyond the run above).
- [x] every new check seen failing first (the swap row by main's src/ put first on PYTHONPATH);
      the Windows and Linux branches named: the mode rows record Windows' answer, the link and
      junction rows ran on Windows, the fallback rows differ from the default on Linux and
      Windows only.
- [x] every gap names its closer (none added); every reserved follow-up has a roadmap line (115,
      116, the Windows access list, the artifact set's path as written).
- [x] packages.toml: no package added; README rows changed: the cache paragraph, the Safety
      bullet, the two cache_dir lines, one Not protected item.
- [x] CHANGELOG under the one unreleased section; no questions raised.
- [x] ruff check, ruff format --check, mypy: clean; the fast tier: 2,698 passed, 0 failed on a891dec5, output in
      build/113/.
```
