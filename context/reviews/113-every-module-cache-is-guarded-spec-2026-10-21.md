# Review of 113 — every module cache is guarded

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent (pre-build reviewer; wrote none of 113, none of the 0.1.0 security
  review, none of the runner code it changes)
- **Reviewed:** the specification as drafted,
  `context/specifications/113-every-module-cache-is-guarded.md` at `6559c149` on
  `spec/113-every-module-cache-is-guarded` (base main `1875d4cd`), read as
  `git diff 1875d4cd 6559c149` (four files: the specification, `context/roadmap.md`,
  `tests/release_shards.toml`, `tests/unit/test_runner_module_caches.py`); the code read is
  `src/wasi_python/` at `6559c149`, which equals main's
- **Run:** none (pre-build review of a draft: no build, no dispatch, as the lane asked)
- **Re-ran:** the seventeen rows of the new file by function node id, against the main tree's
  frozen set (`WASI_PYTHON_ARTIFACTS=…/build/artifacts`, `SHA256SUMS` `d0d91cef`, EXECUTED
  `shasum`) → **15 failed, 2 passed in 15.90 s**, exit 1, output
  `build/113-review/checks-on-6559c149.txt` in this worktree; `ruff check` and
  `ruff format --check` on the new file → clean; four rules checks by node id
  (`test_release_shards_cover_the_judge`, `test_code_outside_src_names_no_context_document`,
  `test_only_the_engine_seam_touches_wasmtimes_private_api`,
  `test_the_judge_patches_the_runner_only_through_the_process_object`) → 4 passed; two probes of
  my own (below). No fast tier, no full judge.
- **Time box:** 45 minutes (runner code and a security fix); kept.

Precedent form: `111-the-filesystem-along-the-wasi-seams-spec-2026-10-21.md`.

## Verified, not trusted

EXECUTED is a command I ran on `6559c149`; READ is the file at the line named; INFERRED is
reasoning from those.

1. **The checks reproduce H1 and fail for the right reason** (EXECUTED). All twelve rows of
   `test_a_writable_grant_over_another_calls_cache_is_refused` fail with "was not refused (the
   guest exited 0); the next default call (KeyError) then loaded 1 compiled module(s) the guest
   wrote", for `run`, `run_async` and `Session`, own cache off and elsewhere, victim the
   `$WASI_PYTHON_CACHE` folder and the platform default under a fresh home (on macOS
   `<home>/Library/Caches/wasi_python`, not made). The root row fails "DID NOT RAISE
   ValueError". The two POSIX mode rows fail with `loaded 1, compiled 0` where the fix wants
   `loaded 0, compiled 1`. The 0700/0600 row and the link row pass on main, as the table says.
   This is H1's step 1 and step 2 (the security review, lines 257 to 323) as a check that counts
   `stats()["loaded"]`, with a real serialized module, in a fresh process for step 2: the right
   reason.
2. **The code paths the specification names** (READ). `_walk_grants` (`_places.py:414-447`)
   judges `_runtime_folders(found, cache)` (`:473-512`), which appends "the module cache" only
   when the call's own `cache` is not `None` (`:497-498`); `_cache_dir(False)` is `None`
   (`_engines.py:67-74`). `_module_miss` loads any `<digest[:32]>-wasmtime<v>-<flavor>.cwasm`
   that `private()` accepts (`_engines.py:143-149`); POSIX `private()` asks `not st_mode &
   0o022` (`_platform.py:543`); Windows `private()` returns `True` (`_platform.py:1389-1392`).
   The only callers of `_walk_grants` are `_call.py:147` and `_sessions.py:987`, and the only
   callers of `_cache_dir` are `_call.py:145` and `_sessions.py:971` (EXECUTED `grep`): the
   specification's three callers are every route to the judge.
3. **The sizes of Decision 7** (EXECUTED, `wc -l` and `ast`): `_platform.py` 1,407,
   `_places.py` 524, `_engines.py` 236; `_chain` 21, `_judge` 37, `_walk_grants` 34,
   `_runtime_folders` 40, `_module_miss` 52, `_Posix.private` 17, `_Windows.private` 4. All as
   written.
4. **A guest rewrites a runner-made file in place and its mode stays 0600** (EXECUTED, my probe
   `build/113-review/probe-rewrite.txt`: a `0700` folder holding a file made `0600` by
   `os.open(…, 0o600)`, a writable grant over its parent, the guest's
   `open(<that file>, 'wb')`): mode before `0o600`, after `0o600`, owner this user, bytes now the
   guest's. In the same call the guest's `os.mkdir` gave `0o755` and its new file `0o644`, as
   Decision 3 says. See M1.
5. **A link on the cache's path, inside a folder granted writable, is outside the cache's
   chain** (EXECUTED, a Python one-liner on `_places._chain`): with `data/link -> ../safe` and
   the cache at `data/link/cache`, the identity of `data` is not in `_chain(data/link/cache)`,
   because `_chain` takes `os.path.realpath` first (`_places.py:276`). See M2.
6. **Existing caches keep their modes** (READ): the runner makes the folder with
   `mkdir(mode=0o700)` (`_places.py:483`, `_platform.py:540`) and each file with `mkstemp`
   then `os.replace` (`_engines.py:169-176`), so a cache it made is `0700`/`0600` under any
   umask; the checks that pass their own `cache_dir` make it with `tempfile.mkdtemp` (`0700`)
   or `mkdir(mode=0o700)` (`test_v1_4_embedding.py:550-620`, `test_runner_sets.py:113`); no CI
   step restores a `.cwasm` cache (EXECUTED `grep cwasm .github/`). The specification's own
   `stat` of this machine's caches I did not repeat.

## Question by question

1. **Every route** — the rule closes H1 as the review ran it, in all three callers, own cache
   off or elsewhere, `$WASI_PYTHON_CACHE` set or unset, made or not, for a grant at, inside or
   above and for a `root` (made or still to be made, above). Grant paths with links or `..` are
   already handled by the walk (a link in a folder this user can write is refused,
   `_platform.py:343-348`; `..` after a missing component is refused, `:337`), and existing
   folders compare by identity, so case-insensitive file systems hold. Three routes stay open:
   the default computed from an environment another process does not share (**H1** below), a
   link on the cache's own path inside a writable grant (**M2**), and a root still to be made
   *inside* a cache still to be made (**L1**). A cache another call passes as `cache_dir` is
   trusted input: I agree. A process-wide record of caches seen would make a refusal depend on
   the order calls ran in and would not protect a cache used for the first time after the plant;
   the README's *Not protected* item says it plainly. It should also be said where the parameter
   is documented (L6). A process whose `$WASI_PYTHON_CACHE` changes between calls falls under
   the same trusted-input clause; on POSIX the modes catch a guest's new folder or file there,
   but not a rewrite in place (M1).
2. **Modes on POSIX** — sound as a check of *how a file was made*, and they cost an existing
   cache nothing (item 6). They do not hold what the Intent and One line say they hold: a guest
   that reaches a cache in use rewrites the runner's `0600` file in place and keeps its mode
   (item 4). That is M1. Stat-then-open (`os.lstat`, then `deserialize_file` by path) leaves a
   swap window; open-then-fstat cannot be done through wasmtime-py's path-only
   `deserialize_file`, but an `lstat` after the load, compared with the one before, closes the
   swap (L3). On Windows: the honest statement is there (Decision 4, the README paragraph). My
   view on the deferral is its own section below.
3. **Not structural** — agreed, measured (item 3 and the Structure line below).
4. **The checks** — reproduce the finding and fail for the right reason (item 1); count
   refusals, modes and `stats()`, never time; name no specification, review or `context/` path
   (the rules check passes; I read the file too). The `tests/release_shards.toml` line is an
   honest judge change: it adds the new file to `own-runner`, which
   `test_release_shards_cover_the_judge` requires of every runner unit file (green with it), and
   it weakens nothing; it is named in `--accept-judge`. Gaps in what they hold: L5.
5. **Criteria and text** — criteria 1 to 11 are each testable by a named check, a recorded run
   or a measurement; criterion 7 is wrong as it stands (M3) and two criteria are missing (for H1
   and M2 below). The README and CHANGELOG text is accurate as to what the runner does, but its
   *Not protected* item and the specification's Intent and One line overstate the modes (M1).

## Acceptance criteria against evidence

1. The plant refused in every caller — testable; seen failing first (EXECUTED, 12 failed).
2. A root still to be made over a cache still to be made — testable; seen failing first
   (EXECUTED). It covers the root above; not the root inside (L1).
3. The modes on POSIX — testable; seen failing first (EXECUTED); Windows branches record.
4. The runner's own modes and links — testable; pass on main (EXECUTED); the Windows link leg is
   the one that moves.
5. The probe re-run — testable; the probe is in the security review's worktree.
6. Existing caches still load — testable; the two rows named are the right ones (READ).
7. No verdict moves — **not met as written**: Decision 1's labels and a widened `_judge` tuple
   would break five existing assertions (M3).
8. Not structural, measured — testable; the base numbers check out (EXECUTED).
9. README and CHANGELOG — testable by reading; the text needs M1's sentence.
10. Public API unchanged, lint, mypy, code speaks — testable.
11. The dispatch — testable.

Missing: a criterion and a check row for H1 (the fallback default judged when `XDG_CACHE_HOME`
or `LOCALAPPDATA` is set) and for M2 (a cache path through a link inside a writable grant).

## Findings, most severe first

### H1. The default cache is judged only as this process computes it; another process of the same user computes it otherwise (`113…md:112-113`; `_platform.py:531-533`, `:1385-1387`)

Decision 1 judges the platform's default "always, even when `$WASI_PYTHON_CACHE` is set:
another process of this user may run without it". The same reason holds one variable down, and
the specification does not apply it. `default_cache_dir` reads `$XDG_CACHE_HOME` on Linux and
`%LOCALAPPDATA%` on Windows; `Path.home()` reads `$HOME`.

Failure (INFERRED from the code; the shape is the security review's own Linux example, one
variable changed): process A runs with `XDG_CACHE_HOME=/var/cache/svc`, its venv under `/opt`,
and calls `run(code, root=Path.home(), cache_dir=False)`. After 113 it judges
`/var/cache/svc/wasi_python` and `$WASI_PYTHON_CACHE` (unset), not `~/.cache/wasi_python`, so
the root passes (HOME holds none of the other runtime folders there). Process B of the same user
(a shell, a cron job, a second service without the variable) has used `~/.cache/wasi_python`,
so it holds a runner-made `0700` folder and the snapshot's `0600` `.cwasm`. A's guest rewrites
that file in place (M1; EXECUTED that the mode stays `0600`), and B's next call loads it: native
code in the host. On Windows the same route needs only a changed `%LOCALAPPDATA%`, with no mode
check behind it. The 0.1.0 tag waits on H1 of the security review; this is H1 of the security
review still open, so the specification as drafted does not close it.

**Fix (specification text, then about six lines in `_platform.py`):** the platform gives every
default it could compute, not one. Replace Decision 1's item 3 with "every platform default this
user's processes could use: `default_cache_dir` as this process computes it, and the same
folder with the override ignored (`<home>/.cache/wasi_python` on Linux,
`<home>\AppData\Local\wasi_python\cache` on Windows); on POSIX, `<home>` is both `$HOME` and
the password database's home for this uid when they differ". Name it
`PLATFORM.default_cache_dirs(home) -> tuple[Path, ...]`, deduplicated by path, inside
`_platform.py` (no platform branch leaves it; about +6 lines, well under the ceiling). Add a row
to the check: victim the fallback default under a fresh home while `XDG_CACHE_HOME` (POSIX) or
`LOCALAPPDATA` (Windows) names another folder; it fails on main and on the draft's rule, and
passes with the fix. Add an acceptance criterion for it. The README's Safety bullet then reads
"…the platform's default, as this process computes it and without `$XDG_CACHE_HOME` or
`%LOCALAPPDATA%`…".

### M1. The modes stop a guest's new file or folder, not a rewrite of the runner's own file in place; the Intent, the One line and the README's *Not protected* item say more (`113…md:328`, `:432`, `:247-249`)

Decision 3's check reads how a file was made. A guest that can write a cache in use opens the
runner's `<digest>-plain.cwasm` for writing: the file keeps its owner and its `0600` (EXECUTED,
item 4). Every cache in use holds that file, so the modes protect only a cache never used for
that digest. That is the case where the residual routes matter (H1 above, M2, an
`$WASI_PYTHON_CACHE` that changes between calls, another call's `cache_dir`). Decision 3 says
of a digest record that "a guest that can reach the cache can rewrite a record kept beside it".
The same argument applies to the modes, and the specification does not say so.

Failure: a reader of "the cache loads only files the runner itself could have written" (One
line) or "on POSIX loads only files at `0600` in a folder at `0700`" (Not protected) takes the
modes as a second wall. They are a filter on new files.

**Fix (text only; the modes stay, they are still worth having):**
- Intent, line 328: "…on POSIX the cache loads only files made the way the runner makes them: a
  folder at `0700`, files at `0600`. That stops a file or folder a guest makes; it does not stop
  a guest that rewrites a file the runner made, so the rule is the guard."
- One line, line 432: "…and the cache loads no file or folder a guest made."
- README *Not protected* item, after "folder at `0700`": "(which stops a file a guest makes, not
  one it rewrites in place)".
- Optional, two lines: also ask `st_nlink == 1` of a `.cwasm`, so a hard link a guest makes
  (WASI `path_link`) to a runner-made file elsewhere is not loaded either.

Evidence that closes it: the text above in the specification and the README draft; no check
needed (the probe is the record).

### M2. A link on a cache's own path, in a folder a grant makes writable, is not judged (`_places.py:273-293`, `:276`)

`_chain` resolves the cache's path with `os.path.realpath` and judges only the resolved folder
and its ancestors. The folders on the path *as written* that hold a link are not in the chain
(EXECUTED, item 5). With `$WASI_PYTHON_CACHE=/data/link/cache` (or a `cache_dir`, or a default
under a linked `~/.cache`) and `link` inside `/data`, a writable `Grant("/data")` passes. The
grant walk does not see it either: `/data` itself is no link. The guest removes `link` and makes
a folder or a relative link in its place. The next call's cache is then the guest's. On POSIX
the guest's new folder is `0755` and is refused by Decision 3, unless the umask is `077` (the
specification's own caveat). On Windows nothing stands behind it.

This predates 113 and applies to every runtime folder that `_chain` judges. But it is a route
over "every module cache", which this specification promises to guard, and the question asked of
this review names it.

**Fix (about five lines in `_chain`, no platform branch):** the chain also holds the identity
of every existing prefix of the path *as written* (`os.path.abspath(path)`, each prefix by
`identity_of`, links followed), so a grant at or above any folder that holds a link on the path
is refused, as a grant above the resolved folder is. Add a row: a cache through a link inside a
writable grant is refused (POSIX; Windows where a link can be made, else skipped naming the
errno), and a criterion for it. If the builder holds this to the caches only, the specification
says why the other runtime folders may wait and the roadmap reserves the rest.

### M3. Decision 1's labels and a widened runtime tuple would break five existing assertions; criterion 7 claims none move (`113…md:115-118`, `:150`, `:393`)

The judge today matches the message's start: `"holds the module cache"` and
`"is inside the module cache"` at `tests/checks/test_v1_2_hostile_guest.py:688`, `:699`,
`:731`, `:745`, `:748`, and the same against hand-made 3-tuples at
`tests/unit/test_runner_grants.py:156-175`, which call `_places._judge(root, grants,
[("the module cache", identity, chain)])` (READ). Decision 1 names the call's own cache "this
call's module cache", so `"holds this call's module cache"` no longer matches
`"holds the module cache"`. The rows at 688, 699, 731, 745 and 748 judge the call's own cache.
Decision 2 lets `_judge` gain the missing components "over them". If that becomes a fourth
tuple field, the unit row's 3-tuples break as well. Either way the builder must edit the
judge, which criterion 7 and the claim list exclude (AGENTS.md rule 4; an unclaimed changed row
is Medium by the checklist).

**Fix (specification text):** every label begins "the module cache": the call's own stays
exactly "the module cache", the others "the module cache `$WASI_PYTHON_CACHE` names" and
"the module cache in the platform's default folder". The existing regexes then hold, and the new
rows' `"module cache"` match too. `_judge` keeps its 3-tuple `runtime`; the root-still-to-be-made
rule takes the caches' missing components as a separate keyword argument with an empty default.
Criterion 7 then stands as written.

### L1. A root still to be made *inside* a cache still to be made is not refused (`113…md:121-129`)

The new rule refuses a root whose missing components lead the cache's, which is a root above.
The reverse (a root such as `$WASI_PYTHON_CACHE/sub`, neither made) passes. Making that root
makes the cache folder (by `make_missing`, at the umask's mode). The README promises "at, inside
or above". The guest cannot write the cache's own entries from `sub`, so this is the promise,
not an exploit. **Fix:** "refused when either list of missing components is a leading part of
the other", and one assertion in the root row.

### L2. The spelling compare: casefold alone (`113…md:125-129`)

`str.casefold()` does not join NFC and NFD (`é` spelled two ways is one name on APFS), nor
Windows' trailing dots and spaces (`new.` is `new`). Both are cases of the embedder's own two
paths, not the guest's. **Fix:** compare
`unicodedata.normalize("NFC", c).casefold().rstrip(" .")`. Like casefold, it can only refuse
more. Or, more robustly, after `make_missing` re-chain each cache not made and, if the made
root's identity is now in its chain, remove what was made and refuse.

### L3. Decision 3's replace and its races (`113…md:174-179`; `_engines.py:143-179`)

- If a refused name is a directory (a guest's `mkdir`), `os.replace` raises. The
  `except BaseException` at `_engines.py:177-179` re-raises, so every call then fails. Today the
  name is skipped (`not cwasm.exists()`). **Fix text:** "a refused `.cwasm` is replaced only if
  it is not a directory; any `OSError` from the replace keeps the module in memory with the
  warning".
- Stat-then-open: compare `(st_dev, st_ino, st_size, st_mtime_ns)` of an `lstat` taken after
  `deserialize_file` with the one `private()` took, and discard on a difference. wasmtime-py
  deserializes by path only, so this is the cheap stand-in for open-then-fstat. It narrows a
  window that only a guest the rule failed to stop can use.

### L4. `Path.home()` on every call (`113…md:112`)

Today `cache_dir=False` never asks for the home folder. After 113 every call does, and
`Path.home()` raises (`RuntimeError`, or `KeyError` from `pwd`) in a container with no `$HOME`
and an unlisted uid. **Fix text:** "a default that cannot be computed (no home) is not judged",
with a word in the README that such a process has no default cache.

### L5. Gaps in what the checks hold (`tests/unit/test_runner_module_caches.py`)

- Line 152: the refusal must name *which* cache (Decision 1). Assert the label, for example
  `"`$WASI_PYTHON_CACHE`" in str(e)` for `env` and `"default" in str(e)` for `default`.
- After a refused `default` row, also `assert not cache.exists()`: Decision 1 says a cache the
  call does not use is never made.
- The rows grant *above* the victim. One `at` (the cache itself) and one `inside` row cost two
  parameters.
- The root row runs only with `cache_dir=False`; add own cache elsewhere, which makes the own
  cache and must still make no default.
- Windows: a junction as the cache folder (Decision 4's reparse-point check on the folder) has no
  row; `os.symlink(target_is_directory=True)` or `_winapi.CreateJunction` gives one.

### L6. README wording (`113…md:231-252`; README.md:2740, :2912)

- The `cache_dir` parameter lines (README:2740, :2912) say "a folder only you can write". Make
  that "a folder only you and the runner write: never one a guest is granted, in this or another
  call", so the trusted-input clause is where a caller reads the parameter.
- Windows: say that a folder made outside the profile (for example directly under `C:\`)
  inherits write access for other local users, so `cache_dir` or `$WASI_PYTHON_CACHE` there is
  writable by them.
- `$WASI_PYTHON_CACHE` relative to the working folder names a different folder per process: say
  "an absolute path".

### L7. The builder's self-check list is not on the branch

`context/reviews/README.md` asks the builder for the list at the top of the review request. I
was not given one and the branch carries none. **Fix:** write it into the request (or the
Status line) before the build review. The draft-stage items are mostly met: the checks were seen
failing, the Windows branches are named, the roadmap reservations are written.

## Windows: is the deferral safe?

Yes, for 0.1.0. I agree with it, on three conditions: H1 and M2 above are fixed, and the README
states the Windows limit as drafted. My reasons:

- **The guard on Windows is the rule.** A guest writes as this user, and its new file inherits
  the folder's access list exactly as the runner's own file does (Decision 4). Nothing on disk
  tells them apart unless the runner marks its own. Once every cache the user's processes could
  use is judged (H1) and the cache's path cannot be redirected through a granted folder (M2), no
  grant or root can reach a cache. What is left is the embedder's own trust: other programs and
  other users that can write the folder. The README names that.
- **A protected access list would buy less than it seems.** The reserved design sets an
  explicit, non-inherited list on each file the runner writes and requires it on load. That
  refuses a guest's *new* file, but a guest that rewrites the runner's file in place keeps its
  list, as on POSIX it keeps its `0600` (M1). So its gain is bounded the same way as the POSIX
  modes. It is defence in depth, not a second wall. Deferring it past 0.1.0 loses no protection
  the rule does not already give.
- **Other local users** are the one class the rule does not cover, and on Windows it is real:
  a folder made outside the profile is writable by Authenticated Users through inheritance (L6).
  The default, under `%LOCALAPPDATA%`, is not. The drafted README sentence ("must name a folder
  only you can write; the default, in your own profile, is one") is honest. L6 makes it concrete.

The reparse-point check (Decision 4) is cheap and right. It should cover the folder as well as
the file, as written. Without H1 and M2 the deferral is **not** safe on Windows, because there
the modes' partial backstop does not exist.

## Structure (checklist 4a)

Not structural, agreed. The draft adds no module-level mutable (the caches are computed per call
from arguments and the environment), no private-API use (`serialize` and `deserialize_file` are
public), and no test seam (the checks call `_engines._module_miss` and `_engines._engine` and
patch nothing; the seam rules check passes, EXECUTED). Platform branches stay in `_platform.py`:
the reparse-point check in `_Windows.private`, the modes in `_Posix.private`, and H1's fix as a
`_platform.py` method. M2's fix and L2's compare are the same on every system. Sizes:
`_platform.py` at 1,407 of 1,500 has room for Decision 4 (about +10) and H1's fix (about +6);
each function named grows to at most about 50 of 80. No rubric row scores down.

## Constitution checks

- §4.15 (safe by default): the specification tightens defaults (a new refusal, stricter modes)
  and loosens none. A call with `cache_dir=False` gains a refusal it did not have, which is the
  point. L4 keeps it from becoming a crash.
- §4.9 (tests count): every verdict is a refusal, a mode or a `stats()` count (READ).
- §4.13 (uv only; ruff): clean on the new file (EXECUTED).
- §4.4 and §4.6: no import, export or artifact byte changes.
- §5.6: this is the pre-build review §5.6 requires for runner code. The build review is a
  different agent's.
- §7: nothing tripped. "Code speaks for itself" holds in the new check file (the rules check
  passes, EXECUTED, and a read finds no spec number, finding ID or `context/` path).

## Disposition (filled in by the author, then confirmed by the reviewer)

The author's answers, in the specification's *Disposition of the pre-build review*, which gives
each one's place:

1. H1 — fixed in the specification: every default a process of this user could compute,
   `default_cache_dirs(home)` in `_platform.py` (with and without `$XDG_CACHE_HOME` and
   `%LOCALAPPDATA%`, under `$HOME` and the password database's home); six `fallback` rows and a
   method row, failing on main; criterion 2.
2. M1 — fixed in the text (Decision 3, the Intent, the One line, the README and CHANGELOG
   lines); `st_nlink == 1` decided yes, with a row failing on main.
3. M2 — fixed in the specification: every existing prefix of the cache's path as written is
   judged, held to the caches with the reason; two rows, failing on main; criterion 3.
4. M3 — fixed in the specification: every label begins "the module cache"; `_judge` keeps its
   3-tuple, the new rule a keyword argument; criterion 7 names the six assertions kept.
5. L1 to L7 — L1 to L6 fixed in the specification, each with its row where one can hold it (the
   swap of L3 has none, with the reason); L7 answered: the self-check list is written before
   the build review.

Confirmed by the reviewer: (pending the confirmation read).

## Verdict

**Fit to build once H1, M1, M2 and M3 are answered in the specification.** H1 closes a route the
draft leaves open to the security review's own finding. M2 closes a link route the draft's
promise covers. M1 and M3 are text. The Lows need no further round once their answers are
written.

One line: the rule is the right fix and its checks reproduce the finding, but it must judge the
default as every process of the user would compute it and the cache's path as written. It must
also say that the modes catch a guest's new file and not a rewrite of the runner's.
