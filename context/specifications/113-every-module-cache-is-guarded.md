# 113: every module cache is guarded

- **Status:** **drafted 2026-10-21** on `spec/113-every-module-cache-is-guarded` from main
  `1875d4cd`, with its checks written first and seen failing on main's code (Decision 6);
  awaiting its pre-build review. The fix is not written. The worktree is
  `.claude/worktrees/agent-a8a67f30f6c037394`; the checks ran against the main tree's frozen set
  (`build/artifacts`, `SHA256SUMS` `d0d91cef`) through `$WASI_PYTHON_ARTIFACTS`, and their
  output is under `build/113/` there. A different agent reviews the specification, and another
  the build.
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
3. **the platform's default folder** (`PLATFORM.default_cache_dir(Path.home())`), always, even
   when `$WASI_PYTHON_CACHE` is set: another process of this user may run without it.

Each is refused as the module cache is today: a writable grant or `root` **at, inside or above**
any of them is a `ValueError` before any work, its message naming which cache ("the module
cache `$WASI_PYTHON_CACHE` names", "the platform's default module cache", "this call's module
cache") and its path. A read-only grant over a cache stays allowed, as today: it cannot write.

**A cache not made yet** is judged by its deepest existing ancestor, the rule the judge already
applies to a missing runtime folder (`_places._chain`): a writable grant or root at or above
that ancestor is refused, since the guest could make the cache below it. One case that rule
misses today is closed here: **a root still to be made** whose path would come to hold a cache
still to be made. Both have no identity yet, and both carry the same deepest existing ancestor;
the root is refused when, below that ancestor, its missing components are a leading part of the
cache's missing components. The components are compared after `str.casefold()` on every
system: a compare by spelling is safe here because it can only refuse more (a case-sensitive
Linux folder `Cache` beside `cache` is refused too), and a component not made yet has no link,
no 8.3 short name and no identity to compare instead. A root beside the cache under the same
ancestor is not refused.

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

- `_engines.py` gains one function beside `_cache_dir`, which returns every cache the process
  could use for a given `cache_dir`, each with the label the judge's message uses, the call's
  own first and the rest without duplicates by path.
- `_places._walk_grants` takes those caches; `_runtime_folders` makes only the call's own and
  lists all of them; `_places._chain` (or a sibling) also returns a missing folder's missing
  components; `_places._judge` gains the root-still-to-be-made rule over them.
- `_call.py:145` and `_sessions.py:971` pass the caches in. `Session` loads its module before
  it walks (`_sessions.py:974-976`), as today; its walk still refuses before any guest code runs.

The builder may shape the signatures otherwise; the contract is the one above.

### 3. Defence in depth: a cache folder at 0700, a `.cwasm` at 0600

The rule is the fix. Behind it, POSIX `private()` asks for what the runner itself makes and a
guest, under the usual umask, does not:

- **a cache folder**: a directory, not a link (`lstat`), owned by this user, with **no bit for
  group or other** (`st_mode & 0o077 == 0`; `0700`, or stricter);
- **a `.cwasm`**: a regular file, not a link, owned by this user, with no bit for group or
  other (`0600`, or stricter).

The runner makes both so already (`mkdir(mode=0o700)`, `mkstemp`); a guest's `mkdir` gives
`0755` and its `open` gives `0644` under umask `022`, since WASI preview 1 has no `chmod`. Under
umask `077` a guest's files are `0600` too, and this defence gives nothing; the rule still
holds. The warning names the mode wanted: "it must be a directory owned by this user that no
one else may read, write or enter (mode 0700)", and "a file … (mode 0600)".

**What happens to what is there:**

- **A `.cwasm` that fails** (`0644`, a link, another owner) in a folder that passes: it is
  never loaded. The module is compiled, and the runner's own file, written `0600` beside it,
  takes its place by `os.replace` (a rename replaces a link itself, never its target). The
  counts read compiled 1, loaded 0, written 1; the warning names the file once. Today such a
  file is left in place and recompiled around on every process's first call.
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
load, where wasmtime maps it. The review itself
calls the rule "the real fix".

### 4. Windows: what `private()` can check there, and what it cannot

Windows has no mode bits, and a guest there writes as this user through wasmtime, so its file
gets the folder's inherited access list exactly as the runner's own file does. After this
specification, Windows `private()` checks what it can without reading security descriptors:

- **can check:** the folder is a directory and the file a regular file, and neither is a
  reparse point (a symbolic link or a junction): `os.lstat(path).st_file_attributes &
  stat.FILE_ATTRIBUTE_REPARSE_POINT == 0`. A planted link to a module elsewhere is refused and
  replaced (Decision 3).
- **cannot check:** who wrote the file, or who else may write the folder. Its owner is this
  user whether the runner or a guest wrote it; its access list is inherited the same way.
  Telling them apart would take the runner setting a protected access list of its own on every
  folder and file it writes and requiring it on load (`SetSecurityInfo` and `GetSecurityInfo`
  through `advapi32`), which is a later specification (the roadmap's reserved line), not this
  one: it adds a ctypes surface `_platform.py` has no room for under its ceiling (1,407 of
  1,500 lines today).

So on Windows the cache is guarded by Decision 1's rule alone, and the README says so
(Decision 5). The change is about ten lines in `_Windows.private`.

### 5. The README and the CHANGELOG

**README, "Safety", the runtime folders bullet** (lines 1044 to 1048) becomes:

> - a writable grant or `root` at, inside or above the runtime's own folders
>   is refused, since later calls and processes trust them: the stdlib folder
>   (or the temporary folder that holds it), the artifact set, every module
>   cache this process could use (the call's own, the folder
>   `$WASI_PYTHON_CACHE` names, and the platform's default, whatever the
>   call's `cache_dir`, made or not), the code of `wasi_python` and
>   wasmtime-py themselves, and the host Python's own `stdlib`,
>   `site-packages` (the user's too) and `bin` (or `Scripts`) folders. So …

**README, the module-cache paragraph** (lines 942 to 947), its first sentences become:

> The compiled module is cached as a `.cwasm` in the user cache directory, or
> in `$WASI_PYTHON_CACHE`, only in a folder at mode `0700` holding files at
> `0600`, as the runner makes them (a `.cwasm` is native code); anything else
> is compiled again and never loaded. `cache_dir=False` keeps it in memory
> only. On Windows the runner can check only that the folder and its files
> are not links, not who wrote them, so `cache_dir` and `$WASI_PYTHON_CACHE`
> must name a folder only you can write; the default, in your own profile, is
> one.

**README, "Not protected"**, two items added:

> the module cache's contents, if anything but the runner can write there: a
> writable grant, a mount provider, another program or another user that can
> write a folder of compiled modules can run code in the host process at the
> next call, outside wasm (the runner refuses a grant or `root` over every
> cache it knows of, and on POSIX loads only files at `0600` in a folder at
> `0700`, but a folder you pass as another call's `cache_dir` it cannot know);
> `cache_dir` and `$WASI_PYTHON_CACHE` are trusted input, as the artifact
> folder is: name only folders that no guest and no other user can write;

**The CHANGELOG line**, under the one unreleased section (`## 0.1.0a8 — unreleased`, which
becomes 0.1.0):

> - **Every module cache is guarded, whatever a call's own `cache_dir`** (spec 113; the 0.1.0
>   security review's H1). A call with `cache_dir=False` or a cache of its own no longer passes
>   a writable grant or `root` over the cache other calls and processes use: the judge now
>   refuses one at, inside or above the call's own cache, `$WASI_PYTHON_CACHE` and the
>   platform's default, made or not, in `run`, `run_async` and `Session`. Before, a guest given
>   such a grant could write a compiled module under the snapshot's public name that the next
>   call loaded as native code. On POSIX a cache folder is used only at `0700` and a `.cwasm`
>   loaded only at `0600`, as the runner makes them; a file that is not is compiled again and
>   replaced, never loaded. On Windows the cache refuses links; it cannot tell who wrote a
>   file, and the README says so. No public name, artifact byte or guest-visible errno changes.

### 6. The checks first, and what they hold

One new file, `tests/unit/test_runner_module_caches.py`, written before the fix and run by
node id on main's code (EXECUTED, `build/113/checks-on-main.txt`: **15 failed, 2 passed**).
The run-level rows need the runner and the artifact set (`needs.need("runner", "artifact
dir")`); a module-scoped fixture compiles the snapshot once in memory (`cache_dir=False`) so no
row writes a 254 MB module to disk on its way to the judge. The mode rows need only wasmtime and
a module of a few bytes. Every verdict is a refusal, a file mode or a count from `stats()`;
none is a time.

| row | holds | on main |
|---|---|---|
| `test_a_writable_grant_over_another_calls_cache_is_refused[<caller>-<own>-<victim>]`, 12 rows: caller `run`, `run_async`, `Session`; own cache off or elsewhere; victim the cache `$WASI_PYTHON_CACHE` names (made) or the platform default under a fresh home (not made) | step 1 of the probe is a `ValueError` naming the module cache, and nothing is planted; were it not, step 2 runs in a fresh process with every default and its `stats()["loaded"]` is printed in the failure | **fail** ×12: "was not refused … loaded 1 compiled module(s) the guest wrote" |
| `test_a_root_still_to_be_made_that_would_hold_a_cache_is_refused` | `root` to be made above a `$WASI_PYTHON_CACHE` to be made: refused, neither made; a root beside it passes; `cache_dir=False` makes no cache | **fail**: "DID NOT RAISE ValueError" |
| `test_a_cwasm_others_may_read_is_compiled_again_and_replaced_never_loaded` | POSIX: a `0644` `.cwasm` in a `0700` folder: compiled 1, loaded 0, written 1, the file now `0600`. Windows: loaded, recorded | **fail** (POSIX): loaded 1, compiled 0 |
| `test_a_cache_folder_others_may_enter_is_not_used` | POSIX: a `0755` folder holding a `0600` `.cwasm`: compiled 1, loaded 0, written 0, a warning naming the folder, nothing written. Windows: loaded, recorded | **fail** (POSIX): loaded 1, compiled 0 |
| `test_the_runner_makes_its_cache_folder_0700_and_its_files_0600` | a fresh cache: the folder `0700`, the file `0600` (POSIX); compiled 1, written 1 everywhere | pass (holds the runner's own modes) |
| `test_a_cwasm_that_is_a_link_is_never_loaded` | a link in the cache to a `0600` module: never loaded, never written through, on every system | pass on POSIX; on Windows main loads it (INFERRED from `_platform.py:1389-1392`; the Windows leg shows it) |

The Windows branches of the two mode rows record Windows' answer (Decision 4) rather than skip,
as `test_runner_refuses_a_cache_others_can_write` does. The link row skips only where the host
cannot make a link, naming the errno.

**Existing checks that may now refuse.** The judge's own calls run with
`$WASI_PYTHON_CACHE=build/cwasm-cache` (`tests/checks/conftest.py`) and the user's default cache
beside it. A check that grants `build/`, the repository or the home folder writable, with its
own cache off, would now be refused. The builder lists every such row in the claim list with
its reason, or records that there is none (INFERRED: none; the checks' writable folders are
under `build/harness/` or the guest temporary folder, siblings of the cache).

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
  and the POSIX ones in `_Posix.private`; the default folder is already
  `PLATFORM.default_cache_dir`. The casefold compare of Decision 1 is the same on every system.
- **test seam:** none; the checks set environment variables and call `_engines._module_miss`
  and `PLATFORM.default_cache_dir`, patching nothing.
- **module ceiling (1,500):** `_platform.py` 1,407 (about +12, INFERRED), `_places.py` 524
  (about +30), `_engines.py` 236 (about +20); the builder records each.
- **function ceiling (80):** `_judge` is 37 lines, `_runtime_folders` 40, `_walk_grants` 34,
  `_chain` 21, `_module_miss` 52, `_Posix.private` 17, `_Windows.private` 4 (EXECUTED, `ast`); each
  grows by about ten. The builder records each; none may pass 80, and
  `LONG_FUNCTIONS` and `SEAM_ALLOWED` do not change.

So it is not structural, and the reviewer applies the rubric's rows only as rule 4a of the
checklist asks. It is still reviewed before it is built: it is runner code and a security fix.

## Intent

After this specification, no argument a call takes opens a way for its guest to write where the
runner keeps compiled modules. A call that keeps nothing on disk, or keeps its own cache, still
refuses a writable grant or root over the cache the next call will read, made or not, in `run`,
`run_async` and `Session` alike. Behind that rule, on POSIX the cache loads only what the runner
itself could have written: a folder at `0700`, files at `0600`. A file that is not is compiled
again and replaced, never run. On Windows the cache refuses links, and the README says plainly
that the rule is the only guard there. The README also says what stays the embedder's to keep:
`cache_dir` and `$WASI_PYTHON_CACHE` are trusted input, and anything that can write a folder of
compiled modules can run code in the host.

## Design

### The commits, in order

Each commit is green on its own but the first, which carries the checks seen failing
(AGENTS.md, rule 3) and is this specification's draft.

1. **The specification, the roadmap lines and the checks** (this draft): the seventeen rows of
   Decision 6, fifteen of them red on main's code, and the file's line in the `own-runner`
   shard (`test_release_shards_cover_the_judge` green with it, EXECUTED).
2. **The rule** (Decisions 1 and 2): `_engines`' list of caches, `_places`' judge of every
   cache and of a root still to be made over a cache still to be made, the two call sites. The
   thirteen run-level rows go green.
3. **The modes** (Decisions 3 and 4): `_Posix.private` at `0o077`, a refused `.cwasm` replaced,
   `_Windows.private`'s kind and reparse-point checks. The four mode rows go green.
4. **The README and the CHANGELOG** (Decision 5).

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
- **A protected access list on Windows** (Decision 4): a later specification, reserved.
- **Caches named by other calls' `cache_dir`**: trusted input, said in the README (Decision 1).
- **Any change to what the guest sees**: no errno, no file, no limit, no default but the
  refusals added.

## Acceptance criteria

1. **The plant is refused, in every caller:** the twelve rows of
   `test_a_writable_grant_over_another_calls_cache_is_refused` green on three systems, each seen
   failing first on `1875d4cd` (`build/113/checks-on-main.txt`).
2. **A root still to be made over a cache still to be made is refused**, one beside it is not,
   and `cache_dir=False` makes no cache: `test_a_root_still_to_be_made_that_would_hold_a_cache_is_refused`
   green, seen failing first.
3. **The modes on POSIX:** `test_a_cwasm_others_may_read_is_compiled_again_and_replaced_never_loaded`
   and `test_a_cache_folder_others_may_enter_is_not_used` green, seen failing first on POSIX;
   their Windows branches green on the Windows leg.
4. **The runner's own modes and links:** `test_the_runner_makes_its_cache_folder_0700_and_its_files_0600`
   and `test_a_cwasm_that_is_a_link_is_never_loaded` green on three systems (the link row named
   in the landing notes if the Windows runner skips it, with its errno).
5. **The review's probe, re-run on the built tip:** `p50_cwasm_plant.py` (copied into this
   worktree's `build/113/`) stops at step 1 with the `ValueError`, and step 2 reports loaded 0;
   output in `build/113/`.
6. **Existing caches still load:** `test_runner_caches_the_compiled_module` and
   `test_fuel_does_not_depend_on_the_module_cache` green (a cache the runner made loads, compiled
   0 and loaded 1, on the second process).
7. **No verdict moves but the claim list's:** every existing row that newly refuses is named in
   the claim list with its reason, or the landing notes say there is none.
8. **Not structural, measured:** the sizes of `_platform.py`, `_places.py`, `_engines.py` and of
   `_judge`, `_runtime_folders`, `_walk_grants`, `_module_miss` and both `private` methods
   recorded, each under its ceiling; `LONG_FUNCTIONS` and `SEAM_ALLOWED` unchanged; the rules
   checks green.
9. **The README and the CHANGELOG** carry Decision 5's text (the Safety bullet, the module-cache
   paragraph, the two *Not protected* items, the CHANGELOG line under the unreleased section).
10. **`tests/public_api.txt` is unchanged**; `ruff check`, `ruff format --check` and `mypy` are
    clean; no code file names a specification, review, finding or `context/` path.
11. **The dispatch:** the release workflow on the built tip, every red line a growth line of
    another entry or G7; the run id in the landing notes; the Windows legs read.

Eleven criteria.

## For the lane

- **Kind:** parallel-safe; lands in the next wave, before the 0.1.0 tag; rebased onto the
  wave's tip in the lane's order, every conflict named.
- **Files it shares with others:** `README.md` (the Safety bullet, the cache paragraph,
  *Not protected*, which H2's specification may also touch), `CHANGELOG.md`,
  `context/roadmap.md`, `tests/release_shards.toml` (one line). Its `src/` files are shared with no specification in flight.
- **The claim list** (each line "113:"): **new checks**, the seventeen rows of Decision 6;
  **retired:** none; **lost passes:** none expected (criterion 7); **fuel and bytes:** none. The
  **judge hash changes** in `tests/unit/test_runner_module_caches.py` (new) and
  `tests/release_shards.toml` (one line in `own-runner`).
- **The flags** (paste-safe):

  ```
  --accept "113: every module cache the process could use is judged in every call, whatever its own cache_dir: a writable grant or root at, inside or above the call's own cache, the folder WASI_PYTHON_CACHE names or the platform's default, made or not, is refused in run, run_async and Session; on POSIX the cache folder is used only at 0700 and a .cwasm loaded only at 0600, and one that is not is compiled again and replaced; Windows refuses links in the cache"
  --accept-judge "113: one unit file of seventeen rows reproduces the 0.1.0 security review's planted compiled module and holds the cache's modes, in the own-runner shard on three systems; no existing expectation edited"
  ```

- **Dry-run needs:** one dispatch on the built tip; the builder reads the `unit` group on the
  three systems, the Windows leg above all (Decision 4).

## One line

A call that does not use the shared module cache still refuses to give its guest a way to write
there, and the cache loads only files the runner itself could have written.

## Landing notes

Not built. The checks of Decision 6 were run on main's code by node id on 2026-10-21, against
the main tree's frozen set through `$WASI_PYTHON_ARTIFACTS` (EXECUTED,
`build/113/checks-on-main.txt` and `build/113/modes-on-main.txt` in the builder's worktree):
15 failed, 2 passed, as the table says. The rest is written once the fix is built.
