# 135: the module cache is read through the descriptor it was checked by

- **Status:** **drafted 2026-10-25** from the 0.1.0 security audit (`../reviews/0.1.0-security-audit-2026-10-25.md`, finding F4, needs validation, and the module-cache hardening notes). Not for build until its pre-build review (runner code, native-code loading). The owner answered question 112 on 2026-10-25 (Decision 1): such deployments are not supported, so this is **defence in depth**, after 0.1.0, in a free slot. Its checks are to be written first and seen failing on main's code.
- **Date:** 2026-10-25
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural** if it fits: `src/wasi_python/_engines.py` (`_load`, `_module_miss`, `_cache_dir`, `_store`), `src/wasi_python/_platform.py` (`private` on `_Posix` and `_Windows`, one new method), one unit-check file in the `own-runner` shard, `docs/explanation/security-model.md`, `README.md` (the cache paragraph), `CHANGELOG.md`. **`_platform.py` stands at 1,464 of its 1,500 lines**, so this specification **stacks on 131** (the platform module is split) if its platform half is more than about 30 lines, and its Kind line is revised then; the builder measures first. No `scripts/`, `recipes/`, pins, workflow or artifact byte. It **tightens** a default and loosens none.
- **Depends on:** 113 (every module cache is guarded), landed: this is the next turn of 113's screw, closing the window 113's Decision 3 calls "narrowed, not closed". 131 if the size needs it (above). Nothing else in flight touches `_engines.py`; 127 touches `_platform.py` only in its Windows constants, if at all.
- **Research it stands on:** the audit's F4 (`0.1.0-security-audit-2026-10-25/NEEDS-VALIDATION.md`; fingerprint `src/wasi_python/_engines.py:_load:cwasm-checked-by-lstat-opened-by-path`), hunted by h04 and verified by v01 and r02 (`agents/h04-loader/artifacts/evidence/`, `agents/v01-cache-swap/`, `agents/r02-cache-swap/`); h04's notes on macOS ACLs (`acl_run.log`), on the two reads of an `artifacts=` set (`unheld_run.log`) and on `cache_dir=""`; spec 113's Decisions 3 and 4 and its build review's L9.

## The problem

A `.cwasm` is native code wasmtime runs as it finds it. Spec 113 made the grant judge the guard (no guest reaches any cache a process of this user could use) and the modes a filter (a folder at 0700, a file at 0600 with one name), and it narrowed the window between the check and the load with a second `lstat` after `Module.deserialize_file` (`_engines.py:233-237`). What is left is a check and a load that are not of the same file:

- `private()` (`_platform.py:556-577`) takes `os.lstat(path)` of the **leaf**: the cache folder, then the file. `Module.deserialize_file` then opens the **path** itself (it takes no descriptor). Between the two, whoever can write the folder, or any ancestor of it, can replace the file or the folder. The second `lstat` catches a swap that changes the stamp, not one that restores it, and not one timed after it.
- **No ancestor is checked.** The default cache is `~/Library/Caches/wasi_python`, `~/.cache/wasi_python` or `%LOCALAPPDATA%\wasi_python\cache`, from `$HOME` (`_engines.py:85`, `_platform.py:534`). Nothing says who owns `~`, `~/Library`, `~/.cache` or the folder `$XDG_CACHE_HOME` names. The judge refuses a guest a grant there; it does not ask whether another **user** owns the way to it.

**Reproduced for one user** (EXECUTED, h04, v01, r02): a swap by this user between the check and the open loaded the planted module (deterministic, with a stand-in that swaps inside `deserialize_file`; and a blind race, 3 hits in 5,000). **Not observed:** another user owning an ancestor. The audit would not run as another account on the owner's machine.

**Who it would reach.** Only a deployment where the runner runs as one user with a cache under a folder another, lower-trust user owns or can write: root under `sudo` keeping `HOME`, a container or CI step with a mapped or shared home, a home on a shared folder, or `$XDG_CACHE_HOME` or `$WASI_PYTHON_CACHE` pointed under `/tmp`. Whether that is supported is the owner's to say.

**Three notes of the same unit** (h04, EXECUTED):
- macOS extended ACLs are invisible to `private()`, which reads `st_mode` alone: an allow entry granting everyone write and `file_inherit` on the cache folder passes, and every new `.cwasm` inherits it (`acl_run.log`).
- A set given through `artifacts=` (not held by its checked digest) is hashed by `_artifacts._digest(binary)` and then compiled by `Module.from_file` (`_engines.py:155`, `195`): two reads, so a file changed between them is compiled and cached under a digest it does not have, and a later call that checked its set against `SHA256SUMS` loads that entry (`unheld_run.log`). The `want` path already reads once and hashes those bytes.
- `cache_dir=""` is `Path("")`, which is `Path(".")`, the working folder (`_engines.py:80`): not refused.

## Decisions

### 1. The owner's answer of 2026-10-25, and what follows from it

**Question 112** asked: is running the runner as root or as another user with a different user's `$HOME`, `$XDG_CACHE_HOME` or `$WASI_PYTHON_CACHE` (sudo keeping `HOME`, a container or CI step with a mapped home, a home on a shared or world-writable folder) a configuration wasi_python supports, or one the security model declares the embedder's own risk, as it declares `cache_dir` trusted input today?

**The answer** (the owner, 2026-10-25, `../decisions.md`): not supported, on the condition that no real use a developer may want breaks. Nothing in this specification refuses a call: a cache whose path passes through a folder another user can write is **not used**, the module is compiled and kept in memory, and one warning says to set `$WASI_PYTHON_CACHE`; a developer under `sudo -E` loses the cache for that process, never the run. So the condition holds, this specification is **defence in depth**, it lands after 0.1.0 when a slot is free, and the security model's cache bullet says in one sentence that the runner trusts every folder on the way to its cache to be this user's ("run it with your own home, or set `$WASI_PYTHON_CACHE` to a folder of yours").

### 2. The cache is opened once, by descriptor, and what is read is what was checked

On POSIX, `_load` opens the cache folder with `os.open(cache, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)`, checks that descriptor with `os.fstat` (a directory, this user's, no bit for group or other), then opens the file **relative to that descriptor** with `os.open(name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC, dir_fd=folder_fd)`, checks it with `os.fstat` (a regular file, this user's, mode 0600 or stricter, one name), and hands wasmtime **that descriptor**: `Module.deserialize_file(engine, f"/dev/fd/{fd}")` (Linux: `/proc/self/fd/{fd}` where `/dev/fd` is absent), the same device spec 129 uses to give wasmtime a pipe. Opening `/dev/fd/N` yields the same open file, whatever the path now names, so the stamp re-check after the load goes: the file loaded is the file checked, by construction. `_file_stamp` stays for Windows (below). Both descriptors are closed in a `finally`. **The builder measures** that `deserialize_file` through `/dev/fd/N` maps the file as it does by path (wasmtime `mmap`s a `.cwasm`); if a platform reads it whole instead, the memo records the cost and the pre-build review decides whether the plain path with the stamp re-check stays there.

`private()` keeps its signature for the other callers and gains a sibling that takes a descriptor (`private_fd(fd, *, is_dir)`), so the judge's `test_runner_module_caches.py` rows hold unchanged. The folder is still made with `mkdir(mode=0o700)` first, as today.

**On Windows** there is no descriptor path wasmtime can open, so the load stays by path with the stamp re-check, and the README says so, as 113 said the rule is the only guard there. `_Windows.private` keeps its reparse-point and one-name checks.

### 3. Every ancestor of the cache folder is this user's or root's, and not writable by others

On POSIX, before the cache is used, each ancestor of the resolved cache folder (`os.path.realpath`, then every prefix up to `/`) is `lstat`ed and must be a directory owned by this user or by root (uid 0) with no group or other write bit (`st_mode & 0o022 == 0`), or world-writable **with the sticky bit** (`/tmp`'s shape, where another user cannot rename this user's entries). The rule is `sshd`'s `StrictModes` for `~/.ssh`, which the same deployments already live under. A cache that fails is **not used**: the module is compiled and kept in memory, and one `RuntimeWarning` names the ancestor and why (the existing `_cache_warning`). Nothing is refused: a call still runs. The identities read are compared with the chain the grant judge already built for the cache (113, Decision 1), so a swap of an ancestor between this read and the open is caught by the open's `O_NOFOLLOW` and `fstat` (Decision 2), not by the path.

`/Users/<me>` and `/home/<me>` are the user's; `/Users`, `/home`, `/Library`, `/var` are root's at 0755; `$XDG_CACHE_HOME=/tmp/x` passes only because `/tmp` is sticky and `/tmp/x` must be this user's. A cache under a folder another user owns, the F4 case, is not used, and the warning says to set `$WASI_PYTHON_CACHE`.

### 4. macOS ACLs, the two reads, and the empty `cache_dir`

- **ACLs on macOS:** `_Darwin.private_fd` also refuses a folder or file that carries an extended ACL with any `allow` entry (`os.listxattr` shows `com.apple.system.Security` on a file with an ACL; the entry count is read through `acl_get_fd_np` in `libSystem` through ctypes, under `_platform.py`'s private-API rule). If the ctypes surface does not fit under the ceiling (Kind line), the ACL check is the `listxattr` presence test alone, which refuses every file with an ACL, the runner's own files having none. Linux ACLs (`system.posix_acl_access` in `listxattr`) are treated the same.
- **One read for every compile:** `_module_miss` reads the binary's bytes once, hashes them, compares with the digest the key was made from and compiles from those bytes, for the `want` path (as today) **and** the `artifacts=` path, so a `.cwasm` under a digest always holds that digest's code; `Module.from_file` is no longer used. The cost is one read of the binary into memory where wasmtime read it itself; measured and recorded.
- **`cache_dir=""`** and any relative `cache_dir` are refused with `ValueError` in the argument checks ("cache_dir must be an absolute path, True, False or None"); the message says what `True` and `False` mean.

### 5. The security model and the README

The security model's cache bullet gains the answer to question 112 (Decision 1) and one sentence: "On POSIX the runner uses a cache only when every folder on the way to it is yours or root's and no one else can write it, and it loads a compiled module through the descriptor it checked; on Windows the grant rule is the only guard." The README's cache paragraph says the same in one line. The CHANGELOG line: "A compiled module is loaded through the descriptor it was checked by, so the file read is the file checked; a cache whose path passes through a folder another user can write is not used, with a warning; a set given through `artifacts=` is hashed and compiled from one read; macOS access lists on a cache are refused; `cache_dir=''` is refused."

### 6. The checks first

One unit file, `tests/unit/test_runner_module_cache_read.py`, in `own-runner`:

1. **The swap inside the load is impossible, not caught:** the stand-in for wasmtime-py (113's L9 row's shape) swaps a 0644 module in **and restores the original's stamp** inside `deserialize_file`; today the restored stamp passes and the swapped module is loaded (red); after, the stand-in receives a `/dev/fd/N` path and the module loaded is the checked file's (green). POSIX only; the Windows branch asserts the stamp path is taken.
2. **An ancestor another user owns is not used:** on a system with a second uid available to the judge (CI's runners have none; the row uses a stand-in `lstat` that reports uid 0 with mode 0777 and no sticky bit for one ancestor, injected through the process object, not a module global), the cache is not used, `stats()` reads compiled 1 loaded 0 written 0, one warning names the ancestor. A sticky world-writable ancestor passes; a root-owned 0755 ancestor passes.
3. **An ACL'd cache is refused on macOS** (`chmod +a "everyone allow write" <folder>` in the row, skipped with its reason elsewhere): the folder is not used; a `.cwasm` with an ACL is compiled around and replaced.
4. **One read:** an `artifacts=` set whose binary is swapped between the digest and the compile (a stand-in for the file reads) raises `ArtifactsMissing` naming the change, never caches.
5. **`cache_dir=""` and `cache_dir="rel"` raise `ValueError`** before any work.
6. **Existing caches still load:** `test_runner_caches_the_compiled_module` and `test_fuel_does_not_depend_on_the_module_cache` unchanged and green (compiled 0, loaded 1 on the second process).

## Intent

After this specification, the file wasmtime deserializes is the file the runner checked, because both are the one open file behind one descriptor; the way to the cache is judged as `sshd` judges the way to a key, so a cache under another user's folder is not used and the embedder is told why; a compiled module always holds the code of the digest it is filed under; and the two inputs that could silently widen the cache, an access list on macOS and an empty `cache_dir`, are refused. On Windows the grant rule stays the guard, said plainly.

## Design

- `src/wasi_python/_engines.py`: `_load` opens by descriptor and hands wasmtime `/dev/fd/N` (Decision 2); `_module_miss` reads once for every compile (Decision 4); `_cache_dir` refuses an empty or relative value (Decision 4).
- `src/wasi_python/_platform.py`: `private_fd` on `_Posix`, `_Darwin` (the access-list check) and `_Windows` (the stamp path kept), and the ancestor rule (Decision 3); measured against the ceiling first, stacking on 131 if it does not fit.
- `tests/unit/test_runner_module_cache_read.py`: the six rows of Decision 6, first; its line in the `own-runner` shard.
- `docs/explanation/security-model.md`, `README.md`, `CHANGELOG.md`: Decision 5 with the owner's answer.
- The commits, in order: the specification with its roadmap line and the rows seen failing; the descriptor load; the ancestor rule; the access lists, the one read and the empty `cache_dir`; the documents.

## Scope

In: Decisions 2 to 6; question 112's answer recorded in `../decisions.md`. Out: a digest record beside the cache (113, Decision 3: not built, for the same reasons); a protected access list on Windows (reserved, after 0.1.0); judging ancestors of the other runtime folders (named by the runner itself, not by an argument).

## Acceptance criteria

1. Rows 1 to 5 of Decision 6 green on three systems (platform rows skipped with their reason where named), rows 1, 2, 4 and 5 seen failing first on `2cd47507`'s code (output in `build/135/`).
2. Row 6 green: an existing cache loads as before, compiled 0 and loaded 1.
3. The measured costs in the landing notes, EXECUTED: the load through `/dev/fd/N` against by path (the same `stats()` and within noise on wall time, which is a fact, not a check); the one-read compile against `from_file`.
4. `_platform.py` under its ceiling (or the Kind line revised to stack on 131); `_load`, `_module_miss` and each `private_fd` under 80 lines; no new module-level mutable; the test seam of row 2 on the process object; `SEAM_ALLOWED` and `LONG_FUNCTIONS` unchanged; the rules checks green.
5. `tests/public_api.txt` unchanged but for nothing (no public name changes); `ruff`, `mypy` clean; no code file names a specification, review, finding or `context/` path.
6. The security model, README and CHANGELOG carry Decision 5's text with question 112's answer.
7. The release workflow dispatched on the built tip; the Windows legs read for the stamp path.

## For the lane

- **Kind:** parallel-safe, runner code, not structural if it fits (Kind line); the wave after 131 if it stacks on it; shares `README.md`, `CHANGELOG.md`, `docs/explanation/security-model.md`, `context/roadmap.md` and `tests/release_shards.toml` with others; `_platform.py` with 131 and possibly 127.
- **Claim list** ("135:"): new rows of Decision 6; retired none; lost passes none; fuel none (the module's code is unchanged; `fuel_does_not_depend_on_the_module_cache` holds); bytes none.
- **Flags:** `--accept "135: a .cwasm is loaded through the descriptor it was checked by (/dev/fd on POSIX), every ancestor of the cache folder must be this user's or root's and not writable by others (sticky /tmp allowed) or the cache is not used with a warning, an artifacts= set is hashed and compiled from one read, a cache folder or file with an access list is refused on macOS, and cache_dir='' or a relative cache_dir is refused"`, `--accept-judge "135: one unit file of six rows in the own-runner shard; no existing expectation edited"`.
- **Waits on:** its pre-build review alone; question 112 is answered (Decision 1), and the specification is after 0.1.0.

## Landing notes

Not yet built. The builder fills this section: the commits, the checks seen failing on main's code first, the fast tier, the branch's release run (its id, every line green on three systems, no growth line), the self-check list (`../reviews/README.md`), and the rebase onto the wave's tip with every conflict named.

## One line

The compiled module wasmtime loads is the file the runner checked, by descriptor, and a cache under a folder another user can write is never used; such a deployment is not supported (question 112), so this is defence in depth.
