# Review of 058 — A Windows grant renames a folder over a file (build)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent that wrote none of spec 058 or its build.
- **Reviewed:** `git diff 3dfdab4...HEAD` on `spec/058-windows-renames-a-folder-over-a-file` (worktree `wasi_python-058`; build 122cd6f, notes 05b56df). Six files: `CHANGELOG.md` (+8), `README.md` (+13/-1), the spec (+255), `tests/checks/test_v1_4_embedding.py` (+19/-3), `tests/harness/files.py` (+48), `tests/unit/test_runner_grants.py` (+39). Nothing in `src/`, `scripts/`, `recipes/`, `downloads/` or the workflows.
- **Given:** the spec, the diff, `build/a4-windows-verify.log` (release run 39135024458, job 117701121795), and, fetched read-only, the passing jobs "verify (ubuntu-24.04)" (117701121785) and "verify (macos-15)" (117701121823).
- **Re-ran:** see *What I ran*. Artifact set `build/sets/s-c4190ca065ada03a`.

## What I ran (EXECUTED)

- The touched tests on macOS (arm64), worktree, no `--accept`: `test_a_writable_mount_answers_as_a_writable_grant_does[plain]`, `[snapshot]` and `test_the_write_parity_asserts_each_systems_grant[linux]`, `[darwin]`, `[win32]`: `5 passed`, `lost 0 · … · judge changed: tests/checks/test_v1_4_embedding.py, tests/harness/files.py, tests/unit/test_runner_grants.py`.
- **The same five on Linux**, which the builder did not run: a copy of the worktree in the local `wp040-arm64` container (Debian, aarch64, uv 0.9.22, `uv sync` from the lock, wasmtime 49.0.0), the same artifact set mounted read-only: `5 passed in 9.38s`; `sys.platform, os.name` there `linux posix`. So Linux's grant answers 54 and lists exactly `_POSIX_LISTING`, and the parity loop still holds both rows on Linux.
- A scratch script (`uv run python -I`, importing the worktree's `tests/harness/files.py`) fed the Windows log's exact values to the new comparisons: the `win32` listing matches the plain run's list (`tmp7zr2b8wp`, `tmpwlt5wwnt`) and the snapshot run's (`tmp5nmlsrcc`, `tmp6scne7rq`); `answer_matches(None, None)`; `WRITE_MOUNT` equals the mount's listing and answer the Windows log printed for both binaries. It refuses `final.bin` in a slot, a listing with one `tmp…` name, a listing with `copy.txt` back, and a `tmpabcd1234.txt` name.
- The fast tier, `uv run pytest -m "not slow"`: `294/343 pass · 0 gap · 10 blocked · 0 fail · 39 deselected (unit suite 1059/1067, 8 skipped)`, `ratchet vs 323ad21aa5: lost 0 · absent 0 · unrun 0 · unrun locally 8 · gained 0 · grew 0 · upstream unrun 31 · not selected 27 · judge changed: (the three files)`, `1353 passed, 18 skipped, 39 deselected`. Load average 32 to 14.
- The full judge, `WASI_PYTHON_ARTIFACTS=…/s-c4190ca065ada03a uv run pytest`, no `--accept`: `wasi_python v1: 301/343 pass · 0 gap · 42 blocked · 0 fail (unit suite 1059/1067, 8 skipped)`, `ratchet vs 323ad21aa5: lost 0 · absent 0 · unrun 0 · unrun locally 28 · gained 0 · grew 0 · upstream unrun 31 · judge changed: tests/checks/test_v1_4_embedding.py, tests/harness/files.py, tests/unit/test_runner_grants.py`, `1360 passed, 50 skipped`, exit 0. The blocked checks are the worktree's missing source trees and clones, as the builder saw. Load average 12 at the start, 27 at the end (`uptime`). **I did not see the builder's one failure**: spec 030's `test_a_deadline_during_a_door_call_under_cancel_is_named` passed here (and in the fast tier) at load 12 to 33. The builder's failure was at load about 89, which fits that check's wall-clock sensitivity (as with 032's O1); this diff touches neither it nor `src/`. Unrelated.
- `uv run ruff check src tests`: all checks passed. `uv run ruff format --check src tests`: 78 files already formatted.
- `gh run view 39135024458 --json jobs` and the two passing jobs' logs: both ran `tests/checks/test_v1_4_embedding.py` and `tests/unit/test_runner_grants.py` in the "v1.1 to v1.4" step and ended `272 passed, 5 skipped`. The Windows job ran the same step on image `windows-2025-vs2026` and ended `2 failed, 265 passed, 10 skipped`, both failures at `test_v1_4_embedding.py:3418`, `assert differ == {}`. So the new unit case runs in all three `verify` jobs.

## What I read (READ)

- **wasmtime v49.0.3** (`context/prior_art/wasmtime-v49`, shallow, tag `v49.0.3`; read only):
  - `crates/wasi/src/filesystem/windows.rs:148-151`: `maybe_dir` sets `share_mode(FILE_SHARE_READ | FILE_SHARE_WRITE)`, no `FILE_SHARE_DELETE`; `filesystem.rs:949` calls `sys::maybe_dir(&mut opts)` at the top of every `open_at`. Confirmed.
  - `filesystem.rs:435-436`: `ERROR_ACCESS_DENIED` and `ERROR_SHARING_VIOLATION` both map to `ErrorCode::Access`. Confirmed.
  - `primitives/windows/fs/mod.rs:30` uses `via_parent::rename as rename_impl`; `windows/fs/rename_unchecked.rs` is `fs::rename(concatenate(old), concatenate(new))`, no kind check; `remove_file_unchecked.rs` is `fs::remove_file`. Confirmed.
  - `crates/test-programs/artifacts/src/lib.rs:13-24`: under `#[cfg(windows)]`, `("RENAME_DIR_ONTO_FILE", "1")`; `crates/test-programs/src/bin/p1_path_rename.rs:66-78`: with that set, `path_rename(dir, "source", dir, "target/file").unwrap()`, else `ERRNO_NOTDIR`. Confirmed: wasmtime's own suite expects this on Windows.
- **Rust 1.95.0** (`~/.rustup/toolchains/1.95.0-aarch64-apple-darwin/.../std/src/sys/fs/windows.rs`): `rename` at 1311 calls `MoveFileExW(old, new, MOVEFILE_REPLACE_EXISTING)` and, only on `ERROR_ACCESS_DENIED`, retries by `FileRenameInfoEx` with `FILE_RENAME_FLAG_REPLACE_IF_EXISTS | FILE_RENAME_FLAG_POSIX_SEMANTICS`; `unlink` at 1288 is `DeleteFileW` with the same `ACCESS_DENIED`-only fallback. Confirmed as the spec says. As the spec says too, the toolchain that built wasmtime-py 49.0.0's library is not known here, so this corroborates; the release run is the proof.
- **CPython 3.14** `Lib/tempfile.py`: `characters = "abcdefghijklmnopqrstuvwxyz0123456789_"`, eight of them after the `tmp` prefix; on `os.name == 'posix'` (WASI) `TemporaryFile` unlinks its open file, and on failure closes the descriptor and re-raises, leaving the name. Confirmed. So `tmp[a-z0-9_]{8}` is exactly tempfile's default name.
- **What I could not verify:** wasmtime **49.0.0** itself (the version `uv.lock` pins and the Windows job used). No 49.0.0 tree is cloned. See F1: one of the files the spec cites did change between 49.0.2 and 49.0.3. Windows's sharing rule (`DELETE` access refused with `ERROR_SHARING_VIOLATION` while another handle lacks `FILE_SHARE_DELETE`) is Windows documentation, not source here; the leftover `tmp…` names are its evidence (EXECUTED there).

## Acceptance criteria against evidence

1. Unit case passes on all three parametrizations — **met** (EXECUTED, macOS and Linux). Its seen-failing claims (3 failed before the table; 1 failed with the `win32` stand-in) are the builder's, in `build/058-standin-unit.log`; not re-done, but the case's logic forces them: `assert rename is None` fails on 54, and `write_by_system` did not exist.
2. The v1.4 check passes on macOS, both binaries — **met** (EXECUTED). The macOS stand-in claim (2 failed, `('rename a folder over a file', 'darwin', ['errno', 54])`) is the builder's; my scratch script shows the same refusal from the other side (the `win32` value refuses the POSIX listing and 54).
3. Linux and macOS still compare both rows as parity, value and tree, and now also exactly — **met** (READ the diff: the only new skip is under `os.name != "posix"`; the new loop only adds asserts; EXECUTED on Linux and macOS).
4. README *On Windows* list and the qualified `tempfile` sentence; CHANGELOG entry — **met** (READ). See F3, F4.
5. Full judge, no `--accept`, no pass lost, nothing grows; ruff green — **met** (EXECUTED: `0 fail`, `lost 0 · grew 0`, the judge change named; ruff clean).
6. The dry run's Windows job — **not yet**, by design: the only Windows evidence for this change is the dry run after landing. INFERRED that it passes; reasons below.

## Will it pass on Windows, exactly? (INFERRED, from the log, character for character)

- The run reached the last assertion of the check (`:3418`); every earlier assert passed, including `len == 45`, the `WRITE_DIFFERENCES` mount answers and `LINUX_ROWS_V14`.
- The new loop asks `answer_matches(None, grant[...])` for the rename (the log: `None`) and the `win32` listing `a.txt, b.txt, copy2.txt, cr.txt, g, h, save.txt, <slot>, <slot>, x.txt` against the logged `… save.txt, tmp7zr2b8wp, tmpwlt5wwnt, x.txt` (plain) and `… tmp5nmlsrcc, tmp6scne7rq …` (snapshot). Same length (10), same names at the same seven fixed places, both slots match. The mount side's 54 and its 11-name listing equal the log's mount values exactly.
- The parity loop's `differ` held exactly these two rows on Windows; both are now skipped there. So `differ == {}`.
- Listing order is deterministic: the guest returns `sorted(os.listdir(B))`, Python's code-point sort, independent of the directory order Windows returns. A `tmp` name always sorts after `save.txt` (`s` < `t`) and before `x.txt` (`t` < `x`), and nothing else in the listing starts with `t`; the two slots are identical, so their mutual order does not matter.
- Determinism across runs: both binaries, two independent guest runs, gave the same shape. The shape depends on the runner image's Windows and file system (see F2).

## Could the slot mask a real difference? (INFERRED)

Not that I can construct. The slot only exists in the `win32` value. It matches one whole name of the exact tempfile shape, in a fixed position, in a list compared by length. The plausible real changes all change the shape: wasmtime adding `FILE_SHARE_DELETE` (one or both `tmp…` names go, `final.bin` appears: length or name differs), the rename refused (`copy.txt`, `e` reappear), a `mkstemp`-style name with a suffix (refused, EXECUTED). Linux and macOS never see a slot: their value has none, so `answer_matches` falls to `==`.

## Findings, most severe first

1. **F1 (low, spec text): the 49.0.3 diff does touch one cited file.** The spec's research list says `fix-49.0.3-files.txt` "shows the 49.0.2 to 49.0.3 diff touches none of these files", but that file lists `crates/wasi/src/filesystem/primitives/via_parent/rename.rs +31 -13`, and the spec cites `via_parent/rename.rs`. `fix-49.0.3-rename-only.diff` shows the change: in 49.0.2 and before, the trailing-slash handling was `#[cfg(unix)]` only, so on Windows `via_parent::rename` never checked kinds at all; 49.0.3 adds a check only when a path ends in `/`. The conclusion stands (a slash-free rename is unchecked in both), but the claim and the Problem's "`via_parent/rename.rs` checks only when a path ends in `/`" describe 49.0.3, not the 49.0.0 the job ran. Failure: a later reader trusts "unchanged" and reasons about 49.0.0's trailing-slash behaviour on Windows from the 49.0.3 file. Fix: say the file changed, what changed, and that it does not affect this row (READ, the rename-only diff).
2. **F2 (low, durability): the Windows listing pins one Windows image's rename behaviour.** The `win32` listing has `g` and no `d`, so on the runner a folder renamed onto an empty folder succeeded, although wasmtime's own Windows test config sets `NO_RENAME_DIR_TO_EMPTY_DIR` (`artifacts/src/lib.rs`). That success most likely comes from Rust's `FileRenameInfoEx` POSIX-semantics fallback, which depends on the Windows build and file system (INFERRED). Failure: a different runner image, a ReFS Dev Drive, or an older Windows keeps `d`, and the check fails on a row it was not about. That is the right outcome (the table changes, with a reason, as Decision 4 says), but the comment in `files.py` and Decision 3 should name the image (`windows-2025-vs2026`) the value was seen on, so the next reader knows why it moved.
3. **F3 (low, README evidence): "(`PermissionError`)" is inferred, not seen, and could be asserted.** The Windows errno of the `TemporaryFile` and `NamedTemporaryFile` rows was not printed; the spec labels it INFERRED (`EACCES`, 2), and the README states it plainly. Either assert `["errno", 2]` for those two rows under `win32` in `WRITE_BY_SYSTEM` (the dry run then confirms the README, the 032 Windows-row review's F1 precedent), or keep the README to what was seen ("fail"). Optional: asserting it risks one more dry-run cycle if the reading is wrong.
4. **F4 (nit, CHANGELOG): "Linux's and macOS's assertions are unchanged".** They are kept and gain an exact value (spec Decision 2's own words). Suggest "kept, and each gains an exact value".
5. **F5 (nit, README placement).** The *On Windows* list sits under *Writable mounts*. An embedder who uses only `Grant(..., writable=True)` reads *Grants* and never sees it. A half-line under *What grants do not do* ("a writable grant answers as the host's file system does; see *On Windows* under *Writable mounts*") would reach them. Not needed for safety (see *Decisions checked*), only for discovery; 032's Windows `..` note sits in the mounts section too, so this is consistent with precedent.

## Decisions checked

- **Mount stays at `ENOTDIR` everywhere (§6.3)** — agreed. The mount's answers are the runner's; making them follow the embedder's OS would give one guest two behaviours for one provider, and the provider protocol does not know the host.
- **No Windows guard on the grant (§4.3, §4.11, §4.15)** — agreed. A guard would be a host-specific branch and a check-then-rename race. It buys no safety: inside a writable grant the guest can already `os.remove` the file and `os.rename` the folder onto its name on any host; Windows only makes it one call. The rename cannot leave the grant (spec 048's guard and wasmtime's sandbox are unchanged). §4.15's defaults are untouched: nothing new is writable. So documenting it is the §4.11 answer, and the README does (F5 is about where).
- **Nothing loosened outside the Windows grant side** — confirmed (READ, EXECUTED). On POSIX the two rows are compared as before, by value and tree, plus an exact value per system; the mount side gains an exact value on every host, including Windows. The only new skip is `name in WRITE_BY_SYSTEM and os.name != "posix"`, and it covers rows the new loop just asserted exactly. An unknown `sys.platform` raises `KeyError`.

## Constitution checks

- §4.3 no host-specific branch in the runtime: holds (no `src/` change; per-system values live in the judge, as 032 did).
- §4.10 claims carry evidence: holds, with F1 (one wrong "unchanged") and F3 (one inferred README parenthesis).
- §4.11 platform semantics documented: holds; the README's earlier `tempfile` sentence, true of Linux and macOS only, is now qualified.
- §4.13 uv only, ruff green: holds.
- §4.15 safe by default: unaffected.
- Judge change: named (`judge changed: …` on every run); it adds assertions and removes none on POSIX. `tests/known_gaps.toml` and `context/progress/` untouched.
- §7: nothing tripped. I committed, pushed, branched and edited nothing tracked; `gh` read-only.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. F1 —
2. F2 —
3. F3 —
4. F4 —
5. F5 —

## Verdict

**Lands once F1 is fixed.** F1 is one sentence of the spec. F2 to F5 are optional; the author answers each in writing. The change does what it says. On Linux (EXECUTED here) and macOS (EXECUTED) it is stricter than before, and it loosens nothing except the Windows grant side of two rows. Those two rows are now asserted exactly, with the values the Windows log printed. That it passes on Windows is INFERRED from that log. The only Windows evidence will be the release dry run after landing (acceptance 6), and the lane should read that job before tagging.

One line: right fix, exact on every system, loosens only Windows's grant side; fix F1's claim that the 49.0.3 diff left the cited files alone, then land, and let the dry run confirm Windows.
