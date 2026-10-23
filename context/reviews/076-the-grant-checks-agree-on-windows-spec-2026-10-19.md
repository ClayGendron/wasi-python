# Review of 076 — The grant checks agree on Windows (the specification, before build)

- **Date:** 2026-10-19 (the session's clock read 2026-10-18; the 063 logs it reads are stamped 2026-10-19 UTC).
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I wrote none of the spec. I read `AGENTS.md`; the constitution (§4.11, §5.6, §5.7, §6); `decisions.md` (question 98 and the rulesets); specs 017 (Decision 5, its Windows walk, and "Choices the specification left to the build"), 034 (Decision 12), 048 and 058 (Decisions 1 and 2); the review of 068 for the form; 063's build review F4 (`build/reviews-evidence/063-buildreview/`); the three Windows logs (`build/reviews-evidence/063-build/run4/windows-own-guest.log` in full around its failures). Code read: `runner.py` (`_Walked`, `_close_held`, `_walk`, `_walk_posix`, `_make_missing`, `_win_open`, `_walk_windows`, `_judge`, `_check_preopens`, `_walk_grants`, the `preopen_dir` call), `mounts.py` (`_fd_read`, `_fd_write`, `_reads`, `_writes`), `tests/checks/test_v1_2_hostile_guest.py` (the two checks), `tests/unit/test_runner_grants.py`, `tests/unit/test_runner_mounts.py` (the rename loop), `tests/harness/files.py` (`WRITE_BY_SYSTEM`), `.github/workflows/release.yml` (the `verify` job), `README.md` (*Grants*). Upstream read: wasmtime-wasi 49.0.0 and 49.0.3 from the cargo registry (`p1.rs`, `filesystem.rs`, `p2/host/filesystem.rs`, `primitives/via_parent/rename.rs`, `primitives/windows/fs/{rename_unchecked,dir_utils,errors}.rs`); CPython 3.14's `Lib/ntpath.py` and `Modules/_io/fileio.c` (`context/prior_art/cpython`, `7c04882`); Microsoft's "File path formats on Windows systems" (learn.microsoft.com, fetched today). Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `spec/076-the-grant-checks-agree-on-windows` at `ddca4e9` on main `7307f6f` (`git diff 7307f6f..ddca4e9`: one file, the spec, 439 lines; READ).
- **Ran (EXECUTED, darwin-arm64, the project's `uv` environment, wasmtime-py 49.0.0, the frozen set `build/sets/s-ff5246a2c2f1a52b`, read only).** Nothing was written in a tracked file of either tree (one ignored file, below); Python ran with `-B`. Beside this file:
  - `probe_ntpath.py` → `.out`: how `ntpath` splits and joins the spellings below.
  - `probe_walk_chain.py` → `.out`: today's `runner._walk_windows` and `runner._judge`, unchanged, with a stand-in `_win_open` that models Win32 normalisation as Microsoft documents it. The runner code is real; the model is INFERRED from the documentation.
  - `probe_read_twin.py` → `.out`: preview1 `fd_write` through a read descriptor and `fd_read` through a write-only one, on macOS.
  - `baseline_macos.log`: the four checks and all of `test_runner_grants.py` on macOS with `-rA` (27 passed, 2 skipped). **Disclosure:** `--progress-dir` names the baseline, not the output, so this run rewrote the worktree's git-ignored `build/progress/latest.json` (its folder dates from 22:24, so an earlier record there, if any, is gone). No tracked file changed; the builder's own judge run writes it again.

## What holds

1. **The four failures are as stated** (EXECUTED there, READ here): run 4's log lines 428-437 show exactly two differing rows, `write a read descriptor 2` and `through a link in the grant 63`; line 855 "DID NOT RAISE"; line 856 `('returned 44', 2005) == ('returned 54', 2005)`; 4 failed, 244 passed.
2. **Cause 1, the write through a read descriptor** (READ). 49.0.0 `p1.rs:626-695` (`fd_write_impl`) checks neither the grant's perms nor the descriptor's mode; the host's `io::Error` becomes `StreamError::LastOperationFailed` (`p1.rs:678`), which `p1.rs:904-918` turns into `ErrorCode::from(io::Error)`; `filesystem.rs:434` maps `ERROR_ACCESS_DENIED` to `Access`, preview1's 2. On POSIX the kernel's `EBADF` passes through: EXECUTED on macOS, `probe_read_twin.out` (write through a read descriptor 8; read through a write-only one 8). `open_at` opens without read only when the guest asked for `FD_WRITE` (`filesystem.rs:966-978`), so the read twin is a real `O_WRONLY` / `GENERIC_WRITE` handle and `win32: 2` is the likely answer (INFERRED; criterion 5 observes it, as the spec says).
3. **Cause 2, the link row** (READ). 49.0.0 `filesystem.rs:1003-1009`: on a read-only grant any open with `create` or `OpenMode::WRITE` is `NotPermitted` before `primitives::open` runs. `open(R + "/escape/x", "w")` is `O_CREAT|O_TRUNC|O_WRONLY`, so 63 on every host, link or none. Run 4 shows 63 on Windows. Deleting the `os.name != "posix"` branch makes the check stricter. Verified.
4. **Cause 3, the collapse** (READ and EXECUTED). `_walk_windows` begins `full = os.path.abspath(path)` (`runner.py:1609`); `probe_walk_chain.out` scenario 0 shows today's walk turning `C:\b\new\..\x` into `C:\b\x` with no missing part. `_walk_posix` refuses it at `runner.py:1457`, as spec 017's build choice says (`017-typed-grants.md:290`).
5. **"Not a hole", for `..`** (READ, line by line). Win32 evaluates `.` and `..` by text before any open (Microsoft, "Evaluate relative components"; READ today, so the spec's INFERRED step is now READ). The walk opens every prefix of the collapsed path with `FILE_FLAG_OPEN_REPARSE_POINT`, refuses a reparse point, and holds each handle without `FILE_SHARE_DELETE` (`runner.py:1608-1641`). wasmtime gets `p.walked.path` (`runner.py:2455`). `_judge` compares identities only. `_check_preopens` compares the opened folder's `ino` with the walked identity (`runner.py:2054-2077`). For `..` the chain the old walk records is the true ancestor chain, so no rule is skipped. I agree: a parity defect, not a hole. **But the general form of that argument does not hold on Windows** (F1).
6. **Cause 4, the rename** (READ). 49.0.0 `rename.rs:19-42` keeps the trailing slash only under `#[cfg(unix)]`; Windows uses `via_parent::rename` (49.0.3 `windows/fs/mod.rs:30`) and `rename_unchecked` is `fs::rename` of two concatenated paths. 49.0.3 `rename.rs:27, 55-60` stats without following and answers `is_not_directory()`, which on Windows is `ERROR_DIRECTORY` (`windows/fs/errors.rs:15-16`), mapped to `NotDirectory`, 54. The guard carries 49.0.3's rule. The `44` path (f renamed to e, then the folder over the file, then `f/` missing) is consistent with spec 058's EXECUTED Windows behaviour.
7. **Rule 4** (READ). No accepted pass is lost: none of the four checks ever passed on Windows. Linux and macOS keep every value they assert today. The rename check gains an exact `returned ENOTDIR` assertion on the guarded side everywhere; the link row loses a branch. The per-system values are spec 058's form (`WRITE_BY_SYSTEM`, `KeyError` for an unnamed system). The judge change is named in criterion 8.
8. **Option (c) for the errno is sound and honest** (READ). §4.11 asks for platform semantics documented, not disguised; spec 058 Decision 1 is the precedent for grants; the error is wasmtime's own mapping, and every write is still refused. The cost claim is right for a call without mounts: the guard linker shadows only `fd_readdir` and `path_rename` (`test_a_guard_call_leaves_the_other_calls_native`), so an exact translation needs `fd_write`, `fd_pwrite`, `fd_read` and `fd_pread` shadowed, and a shadow is a Python crossing on the guest's hottest calls. Knowing which descriptors are read-only would need `path_open` shadowed too, and the write would still have to be intercepted, so "only on descriptors the runner already tracks" is not cheaper (INFERRED from `mounts.py` and the guard's shape). F5 adds what the spec leaves out.
9. **Decision 9's list is complete** (READ, against `test_v1_2_hostile_guest.py:686-746`): every `refused` after line 685, the read-only stdlib run, the fresh root, the inside-cache root and its `not inside.exists()`, the swapped-case row, and `calls == []`. The POSIX-only plant is rightly left POSIX-only.
10. **Stacking on 063 would be worse** (INFERRED). 063's shards and plugin are in review; its evidence would carry them. 063's run 4 already ran both files whole on Windows and only these four failed, so four node ids are enough here, and 063's next dry run (criterion 10) confirms the whole files.
11. **Baseline** (EXECUTED): all four checks pass on macOS today (`baseline_macos.log`).

## Findings, most severe first

### F1 (Medium; decide before build): the Windows walk's chain can miss a true ancestor for two spellings, so an identity rule can be skipped; the Scope line that excludes them is wrong

The spec's Scope puts "Win32's other path rewrites (trailing dots and spaces, `\\?\` paths)" out, "which the identity check already covers". The identity check covers the **final** folder only (`_check_preopens` compares one `ino`). The rules in `_judge` use the **chain**, and on Windows the chain is the identities of path strings that Win32 re-reads one at a time. Two spellings make the chain record the wrong folder:

- **(a) A component with a drive letter** (READ and EXECUTED with the stand-in). The walk builds each prefix with `os.path.join(here, part)`. `ntpath.join("C:\\b", "D:x")` is `D:x`: a part whose second character is `:` resets the join (`ntpath.py:99-140`; `probe_ntpath.out`). So `C:\b\D:sub` is walked as `C:\`, `C:\b`, then `D:sub`, which Win32 resolves against drive D's current folder. The walked path handed to wasmtime is the drive-relative `D:sub`; its identity matches, so `_check_preopens` passes. The chain is `(D:<cwd>\sub, C:\b, C:\)`: drive D's current folder and all its ancestors are missing. `probe_walk_chain.out`, scenario A: with a runtime folder at `D:\work` and D's current folder `D:\work\proj`, `D:\work\proj\sub` is refused "is inside wasmtime-py's own code", and `C:\b\D:sub` (the same folder) is **accepted**. That `GetFullPathNameW` keeps `D:sub` inside a path as text is INFERRED.
- **(b) A name ending in spaces or dots** (READ from Microsoft; EXECUTED with the stand-in). Win32 trims trailing spaces and periods from the **last** segment only, and a single trailing period from any segment. The walk opens `C:\b\a ` as a last segment, which Win32 trims to `C:\b\a`; the full path `C:\b\a \x` passes through the folder literally named `a `. Scenario B: a writable grant `\\?\C:\b\a ` (verbatim, the space-named folder) and a read-only grant `C:\b\a \x` (inside it) are both **accepted**; the plain spelling of the same pair is refused "read-only but inside". It needs both `a` and `a ` to exist. A trailing separator, which the walk drops, has the same effect on which folder a spelling names.

Both are older than 076 (the old walk has them), and neither is a guest escape: the spelling is the embedder's, and (a) needs a process whose current folder on another drive sits inside a protected folder. But they contradict the spec's own framing ("every rule compares identities on the walked chain"; README: "compared by identity, never by spelling"), and 076 rewrites exactly the loop that has them. The fix is a few lines in that loop, testable on every system with criterion 1's stand-in:

- build each path by concatenation (`here.rstrip("\\") + "\\" + name`), never `ntpath.join`;
- in a judged walk, refuse a component that holds `:` (a drive letter or a stream), or that ends in a space or a period (other than `.` and `..`), "a name Windows rewrites; name the folder plainly";
- rows: `C:\b\D:sub`, `C:\b\a \x`, `C:\b\a.\x`, `C:\b\sub::$INDEX_ALLOCATION`, each refused.

Either fold this into Decision 1 (preferred), or correct the Scope line and record a gap with a follow-up specification and a question to the owner. Either way the README sentence "never by spelling" must be true when 076 lands, or say where it is not.

### F2 (Medium): criterion 2's real-file-system rows would never run on Windows

`test_the_walk_judges_links` is `@pytest.mark.skipif(not POSIX, …)` (`tests/unit/test_runner_grants.py:178`, READ; its two Windows-only siblings show as SKIPPED in `baseline_macos.log`). The Design adds the new `..` rows there "on the real file system, every system", and criterion 2 and Decision 7 say they run "on Windows in the verify step". They would be skipped. Put them in a new test with no skip (it needs no link), so the only real-Windows `..` rows outside the hostile-guest check do run there.

### F3 (Medium): the dry run's log cannot show criterion 9

The `verify` step prints no line per passing test: pytest's default report names failures only, and run 4's log shows only `FAILED` lines and the totals (READ). The job uploads no `latest.json` (READ). A node that skipped, or was blocked by `three systems`, which the next step allows (`release.yml:447`), would leave the step green and the run "passed". So "criteria 1 to 6's checks among the passes on `verify (windows-2025)`" cannot be read from the run as written. Have the temporary commit also add `-rA` (EXECUTED locally: one `PASSED <node id>` line each), and have the landing notes quote the `PASSED` line for each named node and for each new test in `test_runner_grants.py`, with both `[plain]` and `[snapshot]`.

### F4 (Low-Medium): the verification route needs three sentences more

The route is honest if the record is kept: the dry run's head is the reviewed commit plus one recorded commit that only lengthens one step's file list (and, after F3, adds `-rA`). Add:

- **Base.** 068 has landed (`6fd89e0` on main, READ); 076's base `7307f6f` is behind. Rebase before building, so the dry run judges the code that lands.
- **Freshness.** Any change to `src/` or `tests/` after the dry run (a review fix, a rebase that moves `runner.py`) needs a new dry run, as rule 6b treats a tag; only `context/`, `CHANGELOG.md` and `README.md` may follow it. Say whether the lane's rebase at landing is covered by criterion 10 (063's next dry run) or needs its own.
- **Authority.** Question 98's answer allows pushing a branch; it says nothing of a force push. The rulesets protect only the default branch and `v*` tags (`decisions.md:54-55`), so a `--force-with-lease` on `spec/076-…` is allowed by GitHub, but the spec should say on what authority it rewrites a pushed branch, or ask. Record the run's `headSha` from `gh run view --json headSha`, its parent, and the diff text; a dropped commit can later be garbage-collected on GitHub.

### F5 (Low): Decision 4 and facts sheet 20 leave out the mounts, and overstate preview2

- With mounts, `fd_read`, `fd_pread`, `fd_write` and `fd_pwrite` are already shadowed and forwarded (`mounts.py:1278-1330`, READ), so a translation there would cost nothing more. And a mount's own file already answers `EBADF` on every host (`_reads`, `_writes`: "the host's EBADF", spec 034 Decision 12's Linux reference). So on Windows one call can answer 8 for a mount file and 2 for a grant file. That is spec 058's split (the mount is the runner's, the grant is the host's), and it is the right one, but Decision 4 should say it and say why calls with mounts do not translate (one answer per grant, with or without mounts). The README line should name grants, and say a mount answers `EBADF` everywhere.
- Name the only exact route that costs nothing on success: a guest-side wrapper of `write` and `read` in the guest's libc that, on `EACCES` only, asks `fd_fdstat_get`. It is build-class and changes the artifact set; refuse or defer it in a sentence, so the choice is complete.
- "preview2's `write` does check": it checks the **grant's** perms (`p2/host/filesystem.rs:141`), not the descriptor's mode. `open_mode` feeds only `get_flags` (`filesystem.rs:543-556`, READ). So on a writable grant preview2 also passes the host's error. EXECUTED for preview1 on macOS: a read descriptor of the writable grant answers 8 (`probe_read_twin.out`). Facts sheet 20 should say "checks neither the grant's perms nor the open mode (preview1); the grant's perms only (preview2)". Cite wasmtime's own precedent, the Windows `ERROR_ACCESS_DENIED` it already ignores in `sync_data` "for POSIX compatibility" (`filesystem.rs:510-520`): it helps the owner's upstream ask.
- "Python code does not reach it" is a little strong: `os.fdopen(fd, "w")` or `open(fd, "w")` on a read descriptor passes `FileIO`'s mode check (the mode comes from the string), and meets the host's number. Say "Python's file objects opened by path".

### F6 (Low): the new file row breaks the POSIX plant

The Design adds a root `base/shared/data/f.txt/../y` "with a file made there". The check later plants `os.rmdir('/s/data')` (POSIX), which fails on a folder that holds `f.txt`, so the guest exits non-zero and the check fails on Linux and macOS (READ, `test_v1_2_hostile_guest.py:738`). Make the file elsewhere (`base / "a-file"`), or remove it before the plant.

### F7 (Low): Decision 1's details

- **A rooted path without a drive** (`\b\x`): the Design's start is `drive + "\\"`, which is `"\\"`, so the walked path handed to wasmtime is relative to whatever drive is current when wasmtime opens it. The old walk produced `C:\b\x`. Take the drive of the current folder, so every walked path is fully qualified. The identity check would catch a change in between, but as a `RuntimeError` after the work, not a refusal before it.
- **"ntpath is the same pure-Python code on every host"** is not so on Windows: `normpath` is `nt._path_normpath`, `splitroot` is `nt._path_splitroot_ex`, `abspath` is `_getfullpathname` (`ntpath.py:172, 474, 516`, READ). The macOS result is evidence for the pure-Python code; for Windows it is INFERRED, and the Windows `verify` run of criterion 1 is what shows it.
- **"It never accepts a spelling Linux or macOS refuses"** holds for `..` only (`a.\x`, a case swap or a backslash are accepted on Windows and are other names on POSIX). Say "for `..`".
- **The fixed current folder** in criterion 1's test: off Windows `ntpath.abspath(".")` joins the POSIX working folder. Give the walk a seam (a module-level function for "the current folder of a drive") rather than patching `ntpath.abspath` itself.

### F8 (Low): the rename check's Windows value depends on the runner image

The native `returned 44` exists only because the runner allowed a folder renamed over a file, which spec 058 found image-dependent (`windows-2025-vs2026`; wasmtime's own Windows test settings say otherwise). Name the image in `NATIVE_RENAME_END`'s comment, so a red run on a new image is read as a fact about the reference, decided by Decision 9, not a regression. `test_the_rename_ends_are_stated_per_system` tests a constant; keep it if you like, but it proves little beyond the `KeyError`.

## Notes (no action required)

- **N1. Every Windows spelling the coordinator named** (item 3):
  | Spelling | Today | After 076 as designed | Tested on Windows |
  | --- | --- | --- | --- |
  | `..` | collapsed by text, safe (What holds 5) | taken on the walk, refused after a missing folder or a file | yes, once 076 runs |
  | junction, symlink, any reparse point | refused (`runner.py:1631`) | same | `test_a_junction_is_refused_on_windows`, in `verify` |
  | 8.3 short names | resolved by Win32 in any position; identity | same | indirectly: the runner's `TEMP` is `RUNNER~1` |
  | trailing dots or spaces, trailing separator | chain can miss the true folder (F1b) | same unless F1 | no |
  | drive letter in a component (`D:x`, `a:b`) | join reset, chain misses ancestors (F1a) | same unless F1 | no |
  | alternate data streams (`x:s`, `x::$INDEX_ALLOCATION`) | not refused; middle-segment behaviour INFERRED | same unless F1 | no |
  | `\\?\` prefix | `GetFullPathNameW` normalises it, so a spelling CreateFileW itself would refuse was granted; consistent with wasmtime | the walk takes `..` itself; consistent | no |
  | `\\.\` device paths | Win32's `..` root is `\\.\`, the walk's is `\\.\C:\`; the walked string is what wasmtime opens, so consistent | same | no |
  | case | identity | same | swapped-case row, once 076 runs |
  | `CON`, `NUL` and other devices | not folders: the attribute read fails or "is not a folder" (INFERRED) | same | no |
- **N2. A risk for criterion 3 on Windows** (INFERRED, low). uv 0.8+ can create a minor-version junction for a managed Python; if the venv's `sysconfig` `stdlib` ran through one, the judged walk would refuse "passes through a link or junction" and the stdlib rows would fail on Windows. `UV_PYTHON` is pinned to the patch `3.14.2` (`release.yml:29`), which I expect to use the patch folder. If it shows, Decision 9 already says how to decide it.
- **N3. One table.** Spec 058 put its per-system values in `tests/harness/files.py` so "the check and its unit case read one table". The write-through-a-read-descriptor value appears in the hostile-guest check and in the unit case; one table there would follow that precedent.
- **N4. Decision 2's "evidence".** The `cache/new/../made` row's Windows message before the fix (inside the module cache) is never observed on Windows, since the dry run runs after the fix. Criterion 1's S1 shows it at unit level; say that is the evidence.
- **N5. Out of scope.** `GetFileInformationByHandle`'s 64-bit index is not unique on ReFS (Dev Drives), where file identifiers are 128-bit. The runner hashes what wasmtime hashes, so the two agree; a collision could only cause a false refusal or a false match between two folders on one ReFS volume. INFERRED from Microsoft's documentation; worth a line in a later Windows memo, not here.

## Constitution checks

- §4.11, documented not disguised: Decisions 4 and 5 document. Holds.
- §5.6: the spec changes no import, export, artifact or recipe; this review is not required by §5.6 and is advisory. A build review is still due.
- §6.1 (the wall): no change weakens it; F1 is an existing gap in an embedder-facing guard, older than 076.
- §6.3 (one behaviour on every host): the bad grant is fixed in the product; the two errno and rename facts are wasmtime's, stated per system. Consistent with 058.
- Rule 4: not weakened (What holds 7).

## Verdict

**Ready once F1 to F4** (F1 decided in the spec, folded in or recorded as a gap with its question; F2's rows moved to a test that runs on Windows; F3's `-rA` and quoted passes; F4's base, freshness and authority sentences). F5 to F8 are wording and placement the builder can take with the build.

## One line

The `..` fix, the link row and the two per-system facts are right and well sourced, but the Windows walk still judges some spellings by text (a drive letter in a component, trailing spaces), one set of new rows would be skipped on Windows, and the dry run could not show its own passes; fix those, then build.

## Confirmation of 076's revision (addendum to the pre-build review)

- **Date:** 2026-10-19. Same reviewer.
- **Reviewed:** `spec/076-the-grant-checks-agree-on-windows`, rebased onto main `6fd89e0`: the draft is now `44cf165`, the revision `c0c5698` (`git diff 44cf165..c0c5698`, one file, +393 -172; READ, and the whole revised spec read, saved here as `spec-c0c5698.md`). `git range-diff 7307f6f..ddca4e9 6fd89e0..44cf165` shows `ddca4e9 = 44cf165`: the rebase changed nothing (EXECUTED). Line numbers the revision cites at `6fd89e0` were checked: `runner.py:1641, 1489, 2086, 2487`, `mounts.py:1305` (`_fd_read`), `GUARDED` and spec 068's `COUNTED` at `mounts.py:389-393`, and run 4's log lines 17-18 (`windows-2025-vs2026`, `20261007.264.1`) (READ). No git tree was touched.
- **Ran (EXECUTED, macOS):** `probe_revised_walk.py` → `.out`. It holds a prototype of the revised Design's judged `_walk_windows`, written here from the spec (not the builder's code), against the same documented-Win32 model as `probe_walk_chain.py`. The model now also maps legacy device names in the last segment only (Windows 10's rule; INFERRED from Microsoft's page). Named rows, then a fuzz over 67,523 spellings (7 heads: `C:\`, `D:\`, `\`, relative, `\\?\C:\`, `D:`, `\\srv\share\`; components `b sub x a "a " a. .. . "" D:sub nul f.txt new v1.2 work proj`). The property is F1's: whenever a walk accepts a path, the chain it records is the true ancestor chain of the folder the walked path resolves to.
  - Revised Design: 920 accepted, **0 with a wrong chain**.
  - Today's real `runner._walk_windows`, same model: 2,538 accepted, **471 with a wrong chain** (`C:\b\D:sub` and kin).
  - Named rows: the review's two cases, `C:\b\a.\x`, `C:\b\sub::$INDEX_ALLOCATION` and `C:\b\...` are refused "a name Windows rewrites". `.hidden`, `v1.2`, `sub\x` (relative), `\b\x` (qualified to `C:\b\x`), `D:sub` (to D's current folder), UNC with `..` past the share, `\\?\C:\b\sub\..\x`, a trailing separator and forward slashes are all accepted with a true chain.

### Each finding

- **F1: fixed.** Cause 5 states both spellings. Decision 1 builds prefixes by concatenation and refuses a component that holds `:` or ends in a space or a period, before it is opened, existing or not. Criterion 1 adds the rows, and S11 to S13 guard them. The Scope line is corrected, and the README's "never by spelling" becomes true. The fuzz above backs it, under the model. **The new rule's false refusals** (INFERRED): every refused name is one Win32 cannot create by a plain path, since it trims trailing spaces and periods and a `:` is a stream. They can exist only when made through `\\?\`, or by WSL or another OS on a share. The spec names the cost (Decision 1; the README says it). Refusing them even inside a `\\?\` path, where Win32 does not rewrite, is stricter than needed but simple, and the spec states it. Legal names that merely contain a period (`v1.2`, `.hidden`) are not touched. `:` in a UNC host (IPv6) or in `\\?\Volume{…}` falls in the drive part, which is never checked (READ, `ntpath.splitroot`). Holds.
- **F7, the rooted path, qualified rather than refused: the right choice.** Win32 gives `\b\x` "the drive from the current directory" (Microsoft, READ), which is what `_drive_folder("")`'s drive gives, and a UNC current folder gives `\\srv\share`, as Win32 does. The old walk's `abspath` gave the same, so nothing that works today breaks. The walked path handed on is now fully qualified, which closes the gap F7 raised. Refusing would buy nothing, since the folder judged and the folder handed on are the same. The seam is a module-level function, as asked. Confirmed.
- **F2: fixed** (a new test with no skip; `test_the_walk_judges_links` unchanged).
- **F3: fixed** (`-rA`; criterion 9 names every node and counts a missing, skipped, blocked or deselected one as a failure).
- **F4: fixed.**
  - The base is now `6fd89e0`, and the range-diff is clean.
  - The temporary commit lives only on a throwaway `spec/076-verify` branch, deleted after the run, so nothing is force-pushed and the spec's branch is never rewritten. That other branch is the lane's ruling, which is the "unless asked" in AGENTS.md.
  - The run's `headSha` and its parent are recorded, with the parent checked against the reviewed tip.
  - Freshness, and the lane's rebase at landing (`git diff --stat <parent> <tip> -- src tests`), are in Decision 7.
- **F5: written in, accurately.** It covers calls with mounts (spec 058's split, one answer per grant), the guest-side wrapper (named and refused), "opened by path", `os.fdopen`, preview2 checking only the grant's perms, and the `sync_data` precedent. The no-mounts shadow list now names spec 068's three counted calls (READ, `COUNTED`). `path_open` is now shadowed on every call, but a relabel would still need `fd_write` and `fd_read` intercepted, so the cost argument stands.
- **F6: fixed** (`base / "a-file"`). **F8: fixed** (the image named, verified in the log; the constant's unit case dropped).
- **N1:** answered in Scope's "Out" list. **N2:** in Decision 9. **N3:** one table in `tests/harness/files.py`. **N4:** S1 named as Decision 2's evidence. **N5:** out of scope, noted.

### Windows reserved names (`CON`, `NUL`, `COM1`, `LPT1`, `nul.txt` …)

They are **named out** in Scope ("not folders: 'is not a folder' or a failed attribute read, INFERRED"). The reasoning holds for the chain. On Windows 10, Win32 maps a reserved name to its device only in the **last** segment. The walk opens every prefix as a last segment, so a path through a folder literally named `NUL` (made with `\\?\`) is refused at that prefix, never accepted with a wrong chain (EXECUTED in the model: `C:\b\NUL` and `C:\b\NUL\x` are both refused). On Windows 11, which narrowed the mapping, the name is literal in every position, so the chain is true. Either way: only false refusals, no skipped rule.

**One corner the Scope line does not name** (INFERRED, low, not a security matter). A root still to be made whose missing tail holds a reserved name, such as `root=C:\b\new\NUL`, passes the walk: the missing rest is checked for rewritten names, not device names. `_make_missing` then makes `new` and fails on `NUL`, which maps to the device on Windows 10, so the refusal ("cannot be made") comes after a folder was made. That breaks "before any work" for that spelling only. One of these fixes it:
- add the reserved stems (`CON PRN AUX NUL COM1-9 LPT1-9`, with or without an extension or trailing spaces) to the refused names in a judged walk: one more clause and one criterion-1 row;
- or say in Scope's "Out" that this spelling may leave the folders before it.

Either is fine. It does not block the build.

### Anything new that is wrong

- **N6 (for the builder, low): a walk that ends at a drive's root must hand on `C:\`, not `C:`.** My first prototype stored each prefix with its separator stripped, so `C:\b\..` handed on `C:`, which is drive-relative (the fuzz flagged every such row until I fixed the prototype). The Design keeps `here` as the start, `drive + "\\"`, and strips only when joining a child, so it is right as written. But it is an easy slip. A criterion-1 row `C:\b\..`, walked to `C:\` and handed on as `C:\` (and `\\srv\share\x\..` as `\\srv\share\`), would catch it.
- Nothing else. The Kind line, criterion 8's judge-change list and Decision 7's node ids now agree with each other, and with the dropped constant test (READ).

### Constitution checks

As before. The revision adds a product refusal on Windows only, for names Windows itself rewrites. That is §6.1 (the wall) and §4.11 (documented, in the README), and it removes a spelling-dependent judgement rather than adding a host-specific branch to a guest-visible behaviour. Rule 4: the judge only gains rows.

### Verdict

**Confirmed for build.** N6 and the reserved-name corner are small; the builder can take them with the build (a criterion-1 row each, or one Scope sentence for the second).

### One line

Every finding is fixed or answered. The new refusal rule leaves no spelling, in about 67,000 modelled, whose chain differs from the folders opened, and refuses only names Win32 cannot make plainly. Two small notes ride along: a drive root keeps its separator, and a reserved name in a root still to be made.
