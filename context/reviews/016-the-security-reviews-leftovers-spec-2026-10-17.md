# Review of 016 — The security review's leftovers (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the constitution (§4.9, §4.15 and §5.2 most closely), `context/reviews/README.md`, the 015 pre-build review (for its format), the 0.1.0a2 security review (F5 to F10 and their dispositions), and the specification. In the runner I read `run`, `_run_checked`, `_instance` (the scratch folder), `_drive`, `_Call.stop`, `_shared`, `_trap_name`, `_first_line`, `stats`, `_lock`, `_epoch_ticker._tick`, `_private`, `_cache_dir`, `_place_*` and `_after_fork_in_child`. I also read `.github/workflows/release.yml` (`build`, `same-bytes`, `verify`, `attest`, `publish`, `pypi`), `release/version.py`'s `write_assets`, `README.md` (the `run` paragraph, the cache paragraph, "Enforced" and "Not protected"), `CHANGELOG.md`, the stats checks in `tests/checks/test_v1_4_embedding.py`, and wasmtime-py 49's `_trap.py`. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/016-the-security-reviews-leftovers.md` as drafted (untracked), against the runner and workflow at `bbeac1f`. The working tree's tracked files match `bbeac1f`.
- **Ran (EXECUTED, darwin-arm64, host CPython 3.14.2, wasmtime-py 49.0.0, the artifacts in `build/artifacts/` read only, `WASI_PYTHON_CACHE=$PWD/build/cwasm-cache`).** The repo was not edited, except to write this file. Scripts and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev016/`:
  - `f7/traps_run.py` → `f7/traps_run.txt`: four guests that trap, through the real runner;
  - `f7/traps_wat.py` → `f7/traps_wat.txt`: seven WAT modules, one per trap kind, and a host-made trap;
  - `f5/check.sh` and `f5/README.txt`: Decision 1's three rules as shell commands, run against a wheel built from `git archive HEAD` plus the set (`uv build --wheel`, the pinned hatchling), and against six altered copies of it;
  - `sweep/rules.py` → `sweep/rules.txt`: the `os.kill(pid, 0)` rule on edge cases, a zombie, mkdtemp's mode with a pid prefix, `rmtree.avoids_symlink_attacks`;
  - `sweep/cost.py` → `sweep/cost.txt`: one scandir pass over 200,000 entries (a benchmark fact, not a test);
  - `kill/child.py`, `kill/parent.py` → `kill/parent.txt`: a child killed mid-call, today;
  - `ns/scripts/a.py`, `ns/scripts/b.py` → `ns/namespaces.txt`: the pid rule across two containers that share one folder (Docker, the local `python:3.13-slim` image, `--pull never --network none`).
  - I did not run `uv run pytest`. Nothing is built yet; the scoreboard is the build review's job.

## What holds

- **The premise of F6 holds.** EXECUTED (`kill/parent.txt`): a child killed while its door host blocks leaves `wasi-python-root-*` and `wasi-python-*`, and the stdin file inside still holds the caller's bytes (`b'secret'`). This machine's temporary folder now holds 109 `wasi-python-*` entries from earlier runs (EXECUTED, `ls -d $TMPDIR/wasi-python-* | wc -l`).
- **The premise of F7 holds, and the codes are there.** EXECUTED (`f7/traps_run.txt`): every guest trap today reads `trapped == 'error while executing at wasm backtrace:'`.

  | guest | `trap_code` | the rule's name |
  |---|---|---|
  | unbounded recursion, `setrecursionlimit(10**8)` | `STACK_OVERFLOW` | `stack overflow` |
  | `json.loads('[' * 200000 + ']' * 200000)` | `STACK_OVERFLOW` | `stack overflow` |
  | `repr` of a list nested 10**6 deep | `STACK_OVERFLOW` | `stack overflow` |
  | `os.abort()` | `UNREACHABLE` | `unreachable` |
  | WAT `unreachable` | `UNREACHABLE` | `unreachable` |
  | WAT load past memory | `MEMORY_OUT_OF_BOUNDS` | `memory out of bounds` |
  | WAT `i32.div_s` by 0 | `INTEGER_DIVISION_BY_ZERO` | `integer division by zero` |
  | WAT `INT_MIN / -1` | `INTEGER_OVERFLOW` | `integer overflow` |
  | WAT `i32.trunc_f32_s nan` | `BAD_CONVERSION_TO_INTEGER` | `bad conversion to integer` |
  | WAT self-call | `STACK_OVERFLOW` | `stack overflow` |
  | WAT `call_indirect` on a null entry | `INDIRECT_CALL_TO_NULL` | `indirect call to null` |
  | a `wt.Trap("my host trap")` from a host function | `None` | (keeps `my host trap`) |

  The rule is `trap_code.name.lower().replace("_", " ")`. It gives the four names the spec lists.
- **mkdtemp keeps 0700 with a pid in the prefix.** EXECUTED (`sweep/rules.txt`): `wasi-python-root-83055-ofxu3cq3 0o700`. The random suffix is unchanged.
- **The pid in the name leaks nothing that matters.** READ: the guest sees its root as `/` and its stdin as a stream, never the host path. INFERRED: other local users can list `/tmp` on Linux and learn that a pid uses wasi_python. Pids are public in `/proc`, except under `hidepid`. That is negligible.
- **A guest cannot turn the sweep against the host.** INFERRED. A guest whose `root=` is the temporary folder can already delete every folder there, so naming one for a dead pid gives it nothing new. A link it leaves inside a swept folder is not followed: `rmtree` is fd-based here (EXECUTED: `shutil.rmtree.avoids_symlink_attacks == True` on macOS) and refuses a link at the top (READ, CPython 3.14.2's `shutil.py`, "Cannot call rmtree on a symbolic link"). On Windows a guest cannot make links.
- **The sweep's listing is cheap.** EXECUTED, a benchmark fact (`sweep/cost.txt`): scandir plus the name filter over 200,000 entries took 0.316 s. The removal is the cost (finding 4).
- **F5's three rules each catch what they aim at.** EXECUTED (`f5/README.txt`): the wheel has no directory entries (`unzip -Z1 … | grep '/$'` gives 0), and its set sits at `wasi_python/artifacts/`. One byte of `MANIFEST` fails `sha256sum -c`, as the spec says. `python.wasm` changed with the wheel's `SHA256SUMS` recomputed fails `cmp`. An extra `.DS_Store` fails the file-list rule. A listed file missing fails `sha256sum -c`. macOS 15's `sha256sum (Darwin) 1.0` takes `--strict -c`. INFERRED: GNU coreutils' `sha256sum` is on ubuntu-24.04, since coreutils is essential there.
- **`attest`, `publish` and `pypi` all sit behind `same-bytes`.** READ: `attest` and `publish` need it; `pypi` needs `publish`.

## Acceptance criteria against evidence

1. *The checks exist and were seen failing first.* Can be met for most of them. Today `stats()` has no `"swept"`, and `trapped` is the heading, so the new checks fail first. The Windows branch is never run by any job (finding 6). Five existing checks fail for the wrong reason once `stats()` gains a key (finding 3).
2. *`uv run pytest` is green with `--accept-judge`.* Right, since checks are added. The judge change must also name the edits finding 3 forces.
3. *A dry run passes every job, including the new wheel check.* Right as a criterion. It does not, as written, show the wheel's code is the tag's (finding 2), and it runs none of the sweep's checks off macOS (finding 6).

## Findings, most severe first

1. **The pid rule removes a live call's folders when the temporary folder is shared across pid namespaces or hosts.** High. The spec's guarantee, "a leak, never a removal of a live call's folder", holds only inside one pid namespace on one kernel.
   - EXECUTED (`ns/namespaces.txt`): container A, running as pid 7 in its namespace, made `wasi-python-root-7-nznxddbf` in a folder shared with container B. B applied the spec's rule. Same owner (uid 0), a directory, and `os.kill(7, 0)` raised `ProcessLookupError` in B's namespace. Verdict: SWEEP. A was still running (`pids [1, 7, 8]`).
   - INFERRED: this is a common shape, not an exotic one. Two containers running as the same uid with `/tmp` or `TMPDIR` on a shared volume (a Kubernetes pod's shared `emptyDir`, a Compose volume, a host `/tmp` bind-mounted into a container). Two hosts with `TMPDIR` on NFS. A Hyper-V-isolated Windows container with a mapped folder. Every container's pids start at 1, so collisions are the rule.
   - Fix: make "running" answerable only inside one pid space, and sweep nothing else.
     - Put a pid-space token in the name: `wasi-python-root-<token>-<pid>-<random>`. The sweep considers only names whose token is its own.
     - On Linux the token is derived from `/proc/sys/kernel/random/boot_id` and the inode of `/proc/self/ns/pid`. EXECUTED (`ns/namespaces.txt`): two live containers had different inodes (4026532556 and 4026532690). An inode is reused only after its namespace is dead, and then every process the old folder names is dead too.
     - On macOS and Windows, which have no pid namespaces, the token is the host name and the boot time. The boot time must be read the same way every time (macOS `kern.boottime`; Windows rounded down from `GetTickCount64`), or the mismatch must be harmless.
     - A token mismatch is always a leak, never a removal. Where the token cannot be read, the process does not sweep.
     - Alternative: a kernel lock held for the call's life (`fcntl.flock` on POSIX, `msvcrt.locking` on Windows), taken by the creator before the folder takes its swept name. It also settles finding 7's sweeper race. It costs more code, and NFS lock semantics vary. Either way, the spec decides one and says why.
     - The keep-check gains a case: a folder with the right pid but another token survives.
     - The README names the limit: the sweep works within one machine and one pid namespace.
2. **F5's check proves the wheel's artifacts but not its code or metadata.** Medium-high. The threat F5 answers is a compromised macOS build job. That job also writes the wheel's `runner.py`, which is the host side of the wall, and its `METADATA`.
   - EXECUTED (`f5/README.txt`): with `runner.py` given an extra line, and with `METADATA` given `Requires-Dist: evil-package`, all three rules pass (`OK`, exit 0). The Intent's sentence, "the wheel is proven to carry the attested bytes", is true only of `wasi_python/artifacts/`.
   - EXECUTED: the wheel is reproducible here. Two builds with `SOURCE_DATE_EPOCH=1767225600`, and a third with `runner.py` at mode 0664, all hashed `224de1ae…`. A build without `SOURCE_DATE_EPOCH` hashed `654e7309…`. INFERRED, not shown: a Linux build gives the same bytes.
   - Fix: the `rebuild` job, which already has the checkout and its own set, also runs the build job's wheel command and uploads the wheel's hash. `same-bytes` then `cmp`s it with the release's wheel. That covers code, metadata and artifacts in one comparison. If the dry run shows a host difference, fall back to this: check out the tag in `same-bytes`, require every file outside `wasi_python/artifacts/` and `*.dist-info/` to equal `src/wasi_python/`, and pin the wheel's whole file list and its `METADATA` lines.
   - Smaller points in the step itself:
     - Name the unzip tool. `python3 -m zipfile -e` worked in the probe.
     - Run `cmp` first. Then run `sha256sum --strict -c` against the *set's* `SHA256SUMS` from inside the wheel's folder, so the wheel's own list is never trusted for file names.
     - List files with `find -type f`, since `LICENSES/` is a folder.
   - "A deliberate failure is shown once" exercises one rule of three. Show one per rule: a byte of `MANIFEST`; a changed `python.wasm` with its hash recomputed in the wheel's `SHA256SUMS`; an extra file. Under the fix, also a changed `runner.py`.
3. **Adding `"swept"` to `stats()` breaks five existing checks and ties them to the host's temporary folder.** Medium.
   - READ: `test_runner_caches_the_compiled_module` and the fuel and cache-off checks in `tests/checks/test_v1_4_embedding.py` (lines 219, 220, 264, 265, 279, 283) assert `stats()` equals a three-key dict. Each fails once a fourth key appears.
   - INFERRED: worse, those probes run in fresh processes against the real temporary folder. Once this ships, any killed run leaves pid-named folders there, so `"swept"` in those probes depends on the machine's history. The judge would flicker.
   - Fix: those checks compare only `compiled`, `loaded` and `written`, and their probes set `tempfile.tempdir` to an empty folder. The spec names these edits as part of the judge change. `stats()`'s docstring ("how this process got its compiled modules") says what `swept` counts.
4. **The sweep runs under `_lock`, and its removals are unbounded.** Medium.
   - READ: the epoch ticker takes `_lock` every round (`_epoch_ticker._tick`), and so do `_engine`, `_module`, `_linker`, `_place_stdlib` and `stats`.
   - INFERRED: a sweep that holds `_lock` stalls every other thread's call. Their deadlines stop advancing until it ends; the ticker catches up after. The README says a guest can write tens of GiB in 60 s, so a dead guest may have left millions of files to remove.
   - Fix: take `_lock` only to claim the once-per-process flag, and set it before sweeping. Sweep with no runner lock held, on the calling thread, before that call's deadline starts.
5. **Several choices the sweep needs are left open (§5.2).** Medium. Each must be decided in the spec.
   - **A pid too large for `os.kill`.** EXECUTED (`sweep/rules.txt`): `os.kill(2**31, 0)` raises `OverflowError`. Any process of this user can make such a name. Without a decision, the first call raises. Or, if the flag is set only after a clean sweep, every call raises. Decide: the sweep never raises into a call. Any exception ends the sweep, and the flag stays set.
   - **Windows' `OpenProcess` failure.** The spec says what `STILL_ACTIVE` means, but not what a failed `OpenProcess` means. INFERRED, from the Win32 contract: a pid with no process fails with `ERROR_INVALID_PARAMETER` (87). Another user's or a protected process (pid 4, System, for one) fails with `ERROR_ACCESS_DENIED` (5). Decide: only 87 means not running; any other failure means running. Also name the access right (`PROCESS_QUERY_LIMITED_INFORMATION`), and declare `restype` as a handle (default `c_int` truncates). Close the handle, and use `use_last_error=True`. pid 0 fails with 87, so a folder named for pid 0 is removed. Only a process of this user can make that name, so this is harmless, but the spec says so.
   - **pid 0 on POSIX.** EXECUTED: `os.kill(0, 0)` succeeds (it signals the process group). Such a folder is kept, which is a leak, so it is safe. The spec says so.
   - **The owner rule on Windows.** The spec states it for POSIX only. Decide: none on Windows, because `%TEMP%` is per user. Say that a shared `TMP` loses the rule.
   - **The exact name pattern.** "Has that form" must be a pattern, for example `wasi-python-(root-)?<token>-(\d+)-[a-z0-9_]+`, matched in full. EXECUTED: the release tarball's own folder name, `wasi-python-0.1.0a3`, does not match it.
6. **The Windows branch, and the sweep on Linux, are never run by any job.** Medium.
   - READ: the full judge runs only in `build` (macOS). `verify` runs on Linux, Windows and macOS, but only on `test_v1_1_artifact_set.py`, `test_v1_2_portable_and_sealed.py`, `test_v1_3_data_stack.py` and `test_v1_4_embedding.py`. The new checks are in `test_v1_2_hostile_guest.py` and `tests/unit/`. There is no other workflow.
   - So the `ctypes` `OpenProcess` code, the part most likely to be wrong (finding 5), would ship never executed. "POSIX and Windows" in Decision 5 would be unproven.
   - Fix: put the killed-process check, the keep-check and the `_running` unit test where `verify` runs them on all three systems, by moving them or adding their files to its list. The dry run then shows them passing on windows-2025 and ubuntu-24.04.
7. **The killed-process check must reap the child, and must not meet a reused pid.** Medium-low.
   - EXECUTED (`sweep/rules.txt`): an exited child that is not yet reaped (a zombie) reads as running (`os.kill` succeeds). After `waitpid` it reads as not running. If the test starts the second child before reaping the first, nothing is swept and the check fails for the wrong reason.
   - INFERRED: on Windows, `TerminateProcess` (what `Popen.kill` calls) returns before the process has ended and its handles are closed.
   - Fix: `Popen.kill()` then `Popen.wait()`, then the second child. Keep the first `Popen` alive until then; on Windows its handle keeps the pid from being reused. If the second child's pid equals the first's, start another; this is a rule, not a retry of a failure. Assert the folder ends empty, not only "nothing of the dead child's".
   - Two sweepers: both may `rmtree` one folder. Say what `"swept"` counts (folders this process found and that are gone after its `rmtree`), and say two processes may both count one.
8. **The keep-check's link case needs a canary, and a Windows rule.** Low-medium.
   - A link that survives is not the danger. The danger is that `rmtree` follows it. The case should point the link at a folder holding a file, and check that the file survives.
   - Add a link *inside* a dead pid's folder pointing at a second canary, which must survive while the folder goes.
   - On Windows, `os.symlink` needs a privilege or Developer Mode. Decide: use a junction (`_winapi.CreateJunction`), or skip that case where `os.symlink` is refused, and say which.
9. **F7: state the rule exactly, pin it, and fix the CHANGELOG's quote.** Low.
   - The rule `trap_code.name.lower().replace("_", " ")` gives the spec's four names (EXECUTED, table above). The spec says "in lower case with spaces" but never writes the rule down.
   - Stability: READ: the Python names are wasmtime-py's own. `UNREACHABLE` stands for the C API's `WASMTIME_TRAP_CODE_UNREACHABLE_CODE_REACHED`. The pin `wasmtime>=49,<50` fixes them. The cloned wasmtime-py is also 49.0.0, so this review has no cross-version evidence. INFERRED: a major bump may add members (49 has 50) or rename one.
   - Fix: write the rule in Decision 3. Add a unit test that maps every `TrapCode` member and compares with a written table, so a bump that renames one changes the judge visibly.
   - It is a contract change: `trapped` is a documented field. The spec already sends it to the CHANGELOG. But its quoted old text, "wasm trap: ...", is wrong. EXECUTED: the old text was `error while executing at wasm backtrace:` for every coded guest trap.
   - Also update `Completed.trapped`'s comment (`runner.py:228`, "or the trap's first line") and the README's `run` paragraph ("or a trap's first line").
10. **The README sentence promises more than the sweep does.** Low.
    - READ: "Not protected" has no killed-process entry today, so the spec's "changes to" should read "gains".
    - "Until the next process's first call" is true only under these conditions:
      - the next process runs as the same user;
      - it uses the same temporary folder and the same pid space (finding 1);
      - the dead pid has not been reused;
      - the dead process has been reaped.
    - Fix: say "until a later process of the same user, on the same machine and temporary folder, makes its first call; longer if the pid is reused". Say also that an embedder's `root=` is never swept.

Not a finding: the spec leaves F8 for "the wheel's next change". This spec changes `runner.py`, which ships in the wheel. The deferral is still reasonable: F8 concerns how artifacts are found, and nothing here touches that. One sentence in Scope saying so would help a later reader.

## Constitution checks

- §4.9 (tests count): holds. Every new check asserts counts, folder listings and strings. The 120 s fail-safes are bounds on a hang, as in spec 015, not measurements. The scandir time above is a benchmark fact in this review, not in a check.
- §4.15 (safe by default): the sweep is a new host action that deletes files. It is safe by default only if it can never remove a live call's folder. Finding 1 shows it can, so this constraint is not yet met. With a pid-space token, or a kernel lock, it is.
- §5.2 (no open questions): not met. Finding 5 lists the choices left open. Findings 1, 7 and 8 add choices the spec must make.
- §4.4 and §4.13: no new import to the guest; `ctypes` is in the standard library, so no dependency is added.
- §4.5 (embedder-neutral): holds.
- §4.10 (claims carry evidence): the spec's EXECUTED claims reproduce (F6's leftovers; F7's `STACK_OVERFLOW`). Its CHANGELOG quote does not (finding 9).
- §7: nothing tripped. Nothing is committed, pushed or published.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 — Fixed by a different design: liveness is a kernel lock, not a pid. Each private folder has a `<name>.lock` beside it, outside the guest's root, held locked by its call; the sweep removes a folder only after taking its lock without waiting. A lock is released when its holder dies, in any pid namespace on the kernel, zombie or not, and pid reuse no longer matters. A lock that fails (`ENOLCK`, a network filesystem) means "leave it". Decision 2.
2. Finding 2 — Fixed: the `rebuild` job builds the wheel too, and `same-bytes` `cmp`s the whole wheel, after the three artifact rules that name what differs. Each rule and the whole-wheel comparison is shown failing once in a local run. Decision 1.
3. Finding 3 — Fixed: `stats()` is unchanged; a module counter, `_swept`, is what the checks read.
4. Finding 4 — Fixed: the sweep is claimed under `_lock` and run without it.
5. Finding 5 — Fixed: the whole sweep sits in `try/except Exception`, each entry on its own; no pid is read, so `os.kill`, `OpenProcess` and `OverflowError` are gone; the exact name pattern is given; Windows's owner rule is "the file can be opened for writing" in the user's own temp folder.
6. Finding 6 — Fixed: the sweep's checks are in `test_v1_4_embedding.py` and a new `tests/unit/test_runner_sweep.py`, which `verify`'s file list gains, so every OS runs them.
7. Finding 7 — Fixed: the check kills and waits; with locks, a zombie and a reused pid no longer matter. A second check proves a live call's folders are never swept.
8. Finding 8 — Fixed: links named like lock files and roots, each pointing at a canary folder, and a link to a canary inside a dead folder; the Windows link cases are skipped.
9. Finding 9 — Fixed: the rule is written down, every `TrapCode` member is mapped in a unit test, and the CHANGELOG quotes the real old text and calls it a change.
10. Finding 10 — Fixed: the README entry is new ("gains"), and says when it holds: same temporary folder, a later wasi_python process; folders from before 0.1.0a3 are never swept.

## Verdict

**revise.** F7 and F10 are ready, and F5 needs a wider comparison. F6's sweep can remove a live call's folder across pid namespaces, which was shown in two containers. It must be bound to one pid space, and its open choices decided, before it is built.

One line: name and pin the traps; compare the whole wheel; sweep only folders from your own pid space, outside `_lock`, never raising, and test it on Windows.

## Confirmation (2026-10-17)

- **Reviewer:** the pre-build reviewer above (Claude Opus 5.5), not the author.
- **Read:** the revised specification in full (untracked, so read whole rather than diffed), and the author's disposition above. I also read CPython 3.14's `Modules/posixmodule.c` (`os.open` on Windows calls `_wopen`, line 11250), `Lib/tempfile.py` (`_TemporaryFileCloser.cleanup` closes, then unlinks), `Doc/library/tempfile.rst` ("a `PermissionError` removing open files on Windows"), `Doc/library/msvcrt.rst` (`locking`), and hatchling 1.32.4's `builders/plugin/interface.py`, `builders/utils.py` and `builders/constants.py`.
- **Ran (EXECUTED, same host).** New scripts and outputs are in the same scratch folder:
  - `lock/race.py` → `lock/race.txt`: the lock rule's orderings, stepped by hand;
  - `ns/scripts/hold.py`, `ns/scripts/try.py` → `ns/locks.txt`: the two-container probe, re-run against the lock rule;
  - one more wheel build with `python.wasm` at mode 0755.

### Each earlier finding

- **1. Confirmed, within one kernel.** EXECUTED (`ns/locks.txt`). On the earlier bind mount, the holder sat at pid 8 in one container. The sweeper, pid 1 in another, got `EWOULDBLOCK` and kept the folder. On a named volume the result was the same. After the holder's container was killed, the sweeper took the lock, which is correct. So pid namespaces, pid reuse and zombies no longer matter. Two kernels sharing a folder are a different case: see C1.
- **2. Confirmed.** The plan is sound.
  - READ: hatchling sorts both directories and files (`interface.py:191-193`). It drops `__pycache__` and `.DS_Store` (`constants.py`). It sets every time to `SOURCE_DATE_EPOCH`. It normalizes modes to 644 or 755 (`utils.py:97-110`).
  - READ: the workflow sets `SOURCE_DATE_EPOCH`, `UV_PYTHON`, `UV_VERSION` and `UV_BUILD_CONSTRAINT` at the top level, so both jobs inherit them.
  - EXECUTED: the owner's execute bit is kept. `python.wasm` at 0755 gives a wheel hashing `4fea254d…`; at 0644 it hashes `224de1ae…`. `assemble_artifacts.py` writes the set with `shutil.copyfile`, so modes follow the umask (READ). INFERRED: both runners use umask 022, so the two builds agree.
  - The dry run is the proof. Criterion 3 already requires it. If the wheels differ, the cause is a fault to fix, not a reason to loosen the check.
- **3, 4, 6, 8, 10. Confirmed.** `stats()` is untouched. The sweep is claimed under `_lock` and runs without it. `verify` gains the sweep's unit file, and `test_v1_4_embedding.py` already runs everywhere. The link cases have canaries. The README entry is new and conditional.
- **5. Confirmed.** No pid is read. The whole sweep is guarded, the pattern is exact, and a Windows owner rule is given.
- **7. Confirmed.** The check kills and then waits. A second check covers a live call.
- **9. Confirmed.** The rule is written down, every `TrapCode` member is mapped, and the CHANGELOG quotes the real old text.

### New findings on the lock design

C1. **A folder shared between two kernels can still lose a live call's folder.** Medium.
   - EXECUTED (`ns/locks.txt`, case iii): a process on the macOS host held the lock on a bind-mounted folder. A container in Docker Desktop's VM took the same lock without an error. Under the spec's rule it would sweep the live folder.
   - INFERRED from `nfs(5)`: NFS mounted with `nolock` behaves the same. Locks then exclude only processes on the same client, and no `ENOLCK` is raised.
   - So the Scope's sentence, "a lock that fails (`ENOLCK`) means leave it", covers only part of the case. The Intent's "no live call's folder is ever removed" claims more than the design does.
   - Fix: choose one of two. Either way, the spec states the choice and why.
     - Write the kernel's identity into the lock file once it is locked, and sweep only lock files whose identity equals one's own. An empty or unreadable identity means leave it.
       - Linux: `/proc/sys/kernel/random/boot_id`. Containers on one kernel share it, so they still sweep each other's dead folders.
       - macOS: `kern.bootsessionuuid`. EXECUTED: `sysctl -n kern.bootsessionuuid` answers.
       - Windows: the lock must cover a byte past the identity, because a Windows lock also blocks reads of its range.
     - Or narrow the Intent and the Scope to "one kernel". The README then says that a temporary folder shared between machines or VMs (NFS, a VM's file share) is unsupported, and that a live call's folder there can be removed.

C2. **On a Linux NFS client, the sweep can take a lock that its own process holds.** Medium.
   - INFERRED from Linux `flock(2)`: since 2.6.12, an NFS client emulates `flock` with `fcntl` byte-range locks. Those belong to the process, not to the open file description.
   - The result: the sweep's thread would lock another thread's live lock file, which is the first call on that thread or a `run_async` worker. Its `close` would then release that thread's lock too.
   - Fix: the runner keeps a set of the names this process holds. A name joins the set before its lock file is created, and leaves it after the file is removed. The sweep never opens a name in the set. This also makes the in-process case independent of the filesystem.

C3. **On Windows, "remove the lock file, then release" cannot work.** Medium.
   - READ: `os.open` on Windows calls the C runtime's `_wopen` (`posixmodule.c:11250`). CPython's own `tempfile` closes before it unlinks, and its documentation names "a `PermissionError` removing open files on Windows".
   - INFERRED: `_wopen` shares read and write but not delete, so neither the call nor the sweep can unlink a lock file it still has open.
   - The result on Windows: every call leaves two lock files, the sweep never removes one, and the killed-process check's "the directory then holds nothing" fails there.
   - Fix: release (`close`), then unlink, on every system. Ignore `FileNotFoundError`. The folder is already gone by then, so a sweeper that wins the gap removes only the lock file.
   - On every system, remove the lock file only once the folder is really gone. Today `rmtree(ignore_errors=True)` can leave part of a folder. If the lock file goes anyway, what is left has no lock file, and it is never swept.

C4. **The gap between the `O_EXCL` open and the lock.** Medium-low.
   - EXECUTED (`lock/race.txt`, case 2): a sweeper that opens the new lock file in that gap takes the lock. The creator's `flock` then raises `BlockingIOError` (`EAGAIN`). The spec redraws a name only on `FileExistsError`, so `run` would raise.
   - If the sweeper unlinks and releases first, the creator locks a file that is no longer on disk. It then makes its folder, which has no lock file: a leak, never swept.
   - EXECUTED (case 3): the same shape lets a sweeper hold a lock on an unlinked inode while a new file has the same name. Only a reused or planted name reaches it.
   - Fix:
     - The creator treats a failed lock like a taken name: close, unlink if still its own, and draw again.
     - After locking, the creator and the sweeper each require `fstat(fd)` to match `lstat(path)` on `st_dev` and `st_ino`. On a mismatch the creator draws again and the sweeper leaves the file. EXECUTED: the check catches both cases. C5. **Smaller points.** Low.
   - **"The lock file is outside the guest's root."** That is false when `root=` is the temporary folder or an ancestor of it. INFERRED: such a guest can unlink a live call's lock file, which only makes a leak. It can also swap in an unlocked file so that a later sweep removes the folder. It could delete that folder itself anyway, so this gives it no new power. Fix: say so, and add to the README that a guest must not be given the temporary folder or an ancestor of it. It would see every rootless call's private root and stdin, which is true today as well.
   - **The sweeper's open.** Open with `O_NONBLOCK`, and check `S_ISREG` on `fstat` after the open. A file swapped for a FIFO after the `lstat` would otherwise block the first call. Only a process of the same user can make one, since WASI preview1 cannot.
   - **Windows locking.**
     - `msvcrt.locking` locks from the file's current position, so seek to 0 first (READ, `msvcrt.rst`).
     - INFERRED, from Microsoft's documentation of `LockFile`: a lock belongs to its handle, so the unit case with "a second open file description" holds on Windows. The same documentation says a dead process's locks are released after a delay that "depends upon available system resources". So in the killed-process check, the parent first confirms it can take both lock files without waiting, then releases them, then starts child 2. This is a precondition, not the property under test.
   - **Wording.**
     - "Between its lock file and its `mkdtemp`" should read `os.mkdir`.
     - Say whether a lone lock file counts in `_swept`. The checks expect it does not.

### Verdict

**revise again.** The lock is the right design. Across containers on one kernel it now does what the pid could not (EXECUTED). Four details still let it fail, all small text changes to Decision 2 that change no structure:
- C1: a folder shared between kernels;
- C2: Linux NFS's per-process locks;
- C3: Windows' unlink of an open file;
- C4: the gap between create and lock.

F5's whole-wheel comparison, F7 and F10 are ready to build.

One line: keep the lock; tie it to one kernel, skip your own names, close before unlink, and check the inode after locking.

## Disposition of the confirmation (filled in by the author)

- C1 — Fixed: each lock file holds its kernel's identity (Linux `boot_id`; macOS `kern.bootsessionuuid`, read through `sysctlbyname`, EXECUTED by the author; Windows `MachineGuid`), and a sweep touches only its own kernel's. No identity: no sweep and no identity written, so those files are never swept. Cloned Windows images sharing a temporary folder are named out of scope and in the README.
- C2 — Fixed: a process-wide set of held names; the sweep skips them.
- C3 — Fixed: end of call is folder, held set, close, then unlink (ignoring `FileNotFoundError`); a lock file is unlinked only after its folder is gone.
- C4 — Fixed: a busy lock at creation is a taken name (redraw); creator and sweeper both check `fstat` against `lstat` (device and inode) after opening; unit cases for both.
- C5 — Fixed: the README warns against `root=` at or above the temporary folder, and the spec says what such a guest can reach; the sweeper opens with `O_NONBLOCK` and checks a regular file after opening (a FIFO unit case); Windows seeks to 0 before locking; the killed-process check confirms both locks are free first (a counted fail-safe); `os.mkdir` is named; `_swept` counts folders, not lone lock files.
- Also folded in: the hostile-guest file's Windows `skipif` that names no need (the 015 build review's follow-up) becomes a branch.

## Second confirmation (2026-10-17)

- **Reviewer:** the pre-build reviewer above (Claude Opus 5.5), not the author.
- **Read:** the revised specification in full (Decision 2, Decision 5, Intent and Scope), and "Disposition of the confirmation" above.
- **Ran (EXECUTED, same host).** I wrote the identity rule into the probe: `ns/scripts/ident.py`, `hold2.py` and `try2.py`, with output in `ns/identity.txt`, in the same scratch folder.
  - The holder locks, writes its kernel's identity and makes the folder. The sweeper takes the lock without waiting, then compares the first line with its own identity.
  - The identities: the macOS host's `kern.bootsessionuuid`, read through `sysctlbyname` with `ctypes`, was `009534F7…`. The Docker Desktop VM's `boot_id` was `fc6f82e0…`.

  | case | the lock | the identity | verdict |
  |---|---|---|---|
  | (a) the macOS host holds, a container sweeps | taken (across kernels) | `009534F7` ≠ `fc6f82e0` | KEEP |
  | (b) a container holds, the macOS host sweeps | taken (across kernels) | `fc6f82e0` ≠ `009534F7` | KEEP |
  | (c) a container holds, a second container sweeps | busy | — | KEEP |
  | (d) the holder container is killed, a second container sweeps | taken | equal | SWEEP |
  | (e) the holder container is killed, the macOS host sweeps | taken | differs | KEEP (a leak) |

  Case (b) is new. Across kernels the lock is invisible in both directions, and the identity alone keeps the live folder. Within one kernel, the lock decides both ways.

### Each confirmation finding

- **C1. Confirmed** (the table).
  - Linux's `boot_id` is shared by every container on one kernel, so those containers still sweep each other's dead folders, as case (d) shows.
  - Windows' `MachineGuid` belongs to the install, not the boot. INFERRED: that is fine, since a reboot frees every lock.
  - The cloned-image case is named in Scope and goes to the README.
- **C2. Confirmed in design, but the set is joined too late.** See S1.
- **C3. Confirmed for the order** (close, then unlink). See S2 for one sentence the disposition claims but the text lacks.
- **C4. Confirmed.** A busy lock at creation means a new name. Both creator and sweeper compare device and inode. Unit cases cover the redraw and the FIFO.
- **C5. Confirmed.**
  - The `root=` paragraph is there, and so are `O_NONBLOCK` with the regular-file check after the open, and the seek to 0.
  - The killed-process check confirms the locks are free before child 2, through a counted fail-safe. It bounds a wait and measures nothing, so §4.9 holds.
  - `os.mkdir` is named, and `_swept` counts folders.
- The hostile-guest file's Windows branch is a judge change. It falls under criterion 2's `--accept-judge`.

### Remaining points (low; text only)

S1. **The held set must be joined before step 1, not at step 6.**
   - On a Linux NFS client a lock belongs to the process (C2). The sweep's thread could reach a name between another thread's `os.mkdir` (step 5) and step 6. It would then take the lock, find this kernel's identity, and remove a live folder.
   - The window is tiny, and only an NFS-hosted temporary folder has it, but it is the case the set exists for.
   - Fix: add `<name>` to the set first, as step 0. On a failed draw, drop it.
   - At the end of the call, drop it last, after the unlink. It only matters a little, since the folder is already gone by then.

S2. **"A lock file is unlinked only after its folder is gone" is in the disposition, not the spec.**
   - Decision 2's end-of-call bullet and sweep step 5 both unlink unconditionally. `rmtree(ignore_errors=True)` can leave part of a folder. If the lock file goes anyway, that part has no lock file and is never swept.
   - Fix: add "if the folder no longer exists" to both places.

S3. **Read and write the identity at offset 0, explicitly.**
   - The creator writes after locking. The sweeper reads after locking. Make both seek to 0, or use `os.pwrite` and `os.pread` where they exist. Windows has neither, so seek there.
   - INFERRED: a 32-bit Python on Windows sees the 32-bit registry view, and needs `KEY_WOW64_64KEY` to read `MachineGuid`. Without it the identity is unread, and that only leaks, so say it once.

S4. **The Intent's "no live call's folder is ever removed".** Add "within one kernel identity", to match Scope's cloned-image exception.

Optional, not a finding: a lone lock file whose creator died between steps 1 and 4 has no identity. It stays for good, as a 0-byte file. If the lock is free, no folder exists and the inode check holds, removing it is safe on any kernel: at worst a live creator redraws or leaks. The spec may sweep these or leave them.

### Verdict

**build.** C1 to C5 are resolved, and the identity rule does what it claims on the host and container pair (EXECUTED, both directions). S1 to S4 are one-sentence edits that change no design. The author makes them before writing code, and the build review checks them.

One line: lock plus kernel identity is sound; join the held set first, unlink only an emptied folder's lock, seek to 0, and qualify the Intent; then build.

## Disposition of the second confirmation (filled in by the author)

- S1 — Fixed: a name joins the held set before its lock file exists, and leaves it last.
- S2 — Fixed: a lock file is unlinked only when its folder no longer exists, at the end of a call and in the sweep; `_swept` counts a folder only once it is gone.
- S3 — Fixed: the identity is written and read at offset 0 after `os.lseek`; `MachineGuid` is opened with `KEY_WOW64_64KEY`.
- S4 — Fixed: the Intent says "by a process of the same kernel identity".
- The optional point is taken: a lone lock file whose lock is free is removed if it is empty or names this kernel.

Your verdict is "build"; these needed no further confirmation.
