# Review of 141 — The access lists on the way to the cache are read

- **Date:** 2026-10-28
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of https://claude.ai/code/session_01ThzDEU6oHaVS4VRYYiC1im; not the author
- **Reviewed:** `git diff 6f5ba427..f1301a36` on `spec/141-the-access-lists-on-the-way-to-the-cache-are-read` (stacked on group A's head `6f5ba427`, pull request #44): the specification with its landing notes and "Differences from the text", its pre-build review (M1, L1 to L6), the rows `a41ce742`, the code `9034ca26`, the page, news file and resolve-once row `3342378d`, row 1's generic-write case `ba887657`, and the Lows' answer `f1301a36`; with 147's `_way` and `_owner_trusted`, 149's resolve-once rule and row, 150's `open_owned`, and the SDK's `sys/acl.h` and `sys/kauth.h`
- **Run:** 40715519918 on `d08f1d16` (pull request #45, the branch rebased onto `dev` at `bd8dcaee`, group A's merge; the ids in this file are those before the rebase, and the landing notes map them), read once with `gh run view` (`build/141/review-run.txt`): green, `ci-status` included; `quick` and `verify` green; the judge's own shards green on ubuntu-24.04 and macos-15 (own-embedding, own-embedding-a, own-guest, own-hostile, own-runner, own-rest) and on windows-2025 (own-embedding, own-embedding-a, own-guest, own-hostile, own-runner); the cached set; the rebuild, fresh-build and release-tier jobs not chosen by the plan
- **Re-ran** (macOS, Darwin 25.5.0, arm64, the 0.1.1 set through `WASI_PYTHON_ARTIFACTS`, 516 GiB free; logs `build/141/review-*.txt`):
  - `uv sync`; `ruff check src tests`, `ruff format --check src tests`, `mypy` → clean, 193 files formatted, 29 source files. EXECUTED.
  - `uv run pytest tests/lint -q -p no:cacheprovider` → 9 passed. `tests/checks/test_rules.py` → 122 passed, 1 skipped. EXECUTED.
  - `tests/unit/test_runner_module_cache_read.py`, `tests/unit/test_runner_threads.py`, `tests/unit/test_runner_module_caches.py` → 118 passed, 3 skipped (row 9's two cases, "the mask rule is Linux's", and the Windows held-handle row); the row file alone 52 passed, 3 skipped, 55 collected; the nine new tests collect **24** items. EXECUTED.
  - `test_runner_threads.py::test_a_resolve_once_table_is_never_seen_half_filled` both ways: as built, 4 passed; against a scratch copy of `src/` (`PYTHONPATH` first, its `__file__` printed) whose `_Darwin._acl` publishes `self.acl_api = {}` first and fills it key by key, the macOS access-list case fails `assert (KeyError('free'), [True]) == (True, [True])`. So the ten-name stand-in still refuses a half-published table. EXECUTED.
  - `ls -led /`, `/Users`, the home, `~/Library`, `~/Library/Caches` → no list on `/`, `/Users`, `~/Library/Caches`; `0: group:everyone deny delete` on the home and `~/Library`. EXECUTED.
  - One `uv run python -c` importing `wasi_python`, `stats()` around `run(["-V"])` with a fresh `WASI_PYTHON_CACHE`: under the scratch folder (`/private/tmp/...`) and again under the worktree's `build/141/` (so the walk crosses the home's `deny delete`): each `compiled 1, loaded 0, written 1`, no warning, exit 0. EXECUTED.
  - `build/141/rows-red-on-base-91b393a8.txt` and `generic-red-on-base-91b393a8.txt` READ: rows 1 (8 cases), 3, 4, 5, 7(a) fail at `:269` on counts (the cache used); 7(b) at `:271` on the words (the presence test's); 8 on `AttributeError`; the generic case at `:269` on the pre-build code.
  - `grep` of `sys.platform|os.name|platform.system` in `src/` → 3, all in `_platform.py`; the module-mutable pattern on `_platform.py` → 0 at `6f5ba427` and at the head; `tests/public_api.txt` unchanged; function spans by `ast` → `_way` 41, `_listed_writer` 22, `_principal` 18, `_advice` 10, `_Posix.access_entries` 8, `_Darwin._acl` 28, `_access_list` 14, `access_entries` 26, `_read_entry` 23 (24 with its decorator), `_Posix.cache_folder` 30; `wc -l` 1,341. EXECUTED.
  - `git log --format='%h %(trailers:key=Co-Authored-By,valueonly)' 6f5ba427..HEAD` → all eight commits `Claude Opus 5.5 <noreply@anthropic.com>`. EXECUTED.
- **Time box:** 45 minutes (a change to a security check); kept.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning.

## The brief's questions, answered first

1. **The macOS reading is Decisions 1 and 2.** Tag 1 is the only allow (`_ACL_ALLOW`, `src/wasi_python/_platform.py:136`); a deny is skipped and never excuses (`_listed_writer`, `:742-763`, judges each allow alone). The six rights are `sys/acl.h`'s bits in Decision 1's order (`:138-145`); `_ACL_GENERIC` is `1<<23 | 1<<21` and grants the first five (`:146-147`), which is exactly what `KAUTH_VNODE_GENERIC_WRITE_BITS` and `GENERIC_ALL_BITS` give among the counted rights (READ, `sys/kauth.h:365-383`: neither holds `CHANGE_OWNER`). Only-inherit is `1<<8` from `acl_get_flag_np`, and "inherited" is not read, so an inherited entry counts (row 7 EXECUTED). The mask is read through `POINTER(c_uint64)` (`:1195`). The loop stops at 128 entries or at the first nonzero `acl_get_entry` (`:1238-1242`). `acl_get_link_np` NULL with `ENOENT`, `ENOTSUP`, `EOPNOTSUPP` is `()`; any other errno is an `OSError` (`:1228-1234`); a nonzero answer from the tag, mask or flagset call, and a -1 from `acl_get_flag_np`, are `OSError`s (`:1251-1259`); `_listed_writer` turns each into the "cannot read" words. Held. READ, and EXECUTED through rows 1 to 8.
2. **The table is filled once and published whole.** `_Darwin._acl` (`:1176-1203`) builds the ten calls in a local dict literal and assigns `self.acl_api` once; `_access_list` and `access_entries` both call it. 149's row was changed only in its stand-in's names (two to ten, `acl_free` last) and still fails on a half-published table (Re-ran). Held.
3. **`_way(folder, lstat, entries)`.** The kind, owner (`_owner_trusted`) and mode branches are unchanged and come first; the list is read only in their `else` (`:732-735`), so 147's trust of `/`'s owner and 135's judgments are as they were. `_advice` returns `hint` unchanged for a hint other than the cache's, and `_ROOT_ADVICE` for `/` when no list is to blame, which is the old expression. READ.
4. **Structure.** No platform branch outside `_platform.py`; no new module-level state (ints, a tuple of pairs, a `NamedTuple`; the table on the instance); every function under 80; `_platform.py` 1,341 of 1,500. The seam is `monkeypatch.setattr(_platform.PLATFORM, "access_entries", …)`, the platform object's public method, as the pre-build review accepted; `SEAM_ALLOWED` unchanged. EXECUTED.
5. **Linux.** `_Posix.access_entries` answers `()` and `_Linux` does not override it: no system call. Row 9's `_posix_acl` writes `struct.pack("<I", 2)` then `<HHI` records in tag order 0x01, 0x02, 0x04, 0x10, 0x20, unnamed ids `0xFFFFFFFF`, and skips on `ENOTSUP`, `EOPNOTSUPP`, `EINVAL` with the errno named (`tests/unit/test_runner_module_cache_read.py:756-790`); it removes the attribute in a `finally`. READ; the Linux leg runs it in the pull request's run.
6. **The rows.** They count `stats()` deltas and warnings, never time. Real lists are set only on `work/above`, `work/listed` and the folder the runner makes below `above`, each removed in a `finally` (`chmod -N`, and `chmod -R -N` in row 7). Row 7(a) is red on the base on counts and 7(b) on words, as M1 asked (READ, the log). `_listed` reads `getattr(_platform.PLATFORM, "access_entries", lambda path: ())` before `monkeypatch.setattr(..., raising=False)` (`:537-556`). Held.
7. **The words.** Decision 6's texts verbatim: `why` and `ENTRY_ADVICE` asserted whole by row 1(g), `_ROOT_LIST_ADVICE` by row 4, with neither `$WASI_PYTHON_CACHE` nor `chmod -a` at `/`. Each names the folder, the principal by name and number, and the rights `chmod -a` takes back. Actionable.
8. **The install sentence** is Decision 9's with L5's "remove or rename the folder", placed right after "The cache folder and its files must carry no access list.", beside 147's sentences, no number. READ.
9. **The news file** has one `### Security` line; `new` names the nine tests, which collect 24 items, matching `units = 24`; `changed` names 149's resolve-once row with its reason. READ, EXECUTED (collect).

## Acceptance criteria against evidence

1. Rows red on the base, guards green — met on macOS: the logs above, 7(a) on counts and 7(b) on words; rows 2, 6 pass on the base (READ). Linux's red is the pull request's run.
2. Green on Linux and macOS with the stated skips — met on macOS (EXECUTED); Linux and Windows in the pull request's run.
3. The guards unchanged — met on macOS: `test_runner_module_caches.py` green, and a fresh cache below the home loads with no warning (EXECUTED); `test_v1_4_embedding.py`'s two guards are the builder's (READ) and the run's.
4. The warning texts verbatim, rows 1(g) and 4 assert them — met. READ, EXECUTED.
5. The reader's calls counted — met: 25 C calls a walk, 50 a miss, on this host's default way (`build/141/reader-calls.txt`, READ).
6. No lost pass, no growth — checkable in the run; no guest, pin or recipe moved.
7. The rules — met: rules, lint, ruff, mypy green; `public_api.txt` unchanged (EXECUTED).
8. News file, install sentence — met (READ); `ci-status` is the run's.

## Findings, most severe first

No High, no Medium.

1. **L1. The snapshot way's reader says what, not why** (`src/wasi_python/_platform.py:656`) — the comment `# its lists are not read` states the fact; the writing rule asks a code comment for its reason in words. Failure: a reader of `open_owned` sees a security check passing a reader that reads nothing, with no word of why, and may "fix" it into a `PermissionError` on `load` and `save`. Fix text: `# a snapshot's way is held to its owner and mode alone: reading its lists would refuse load and save, which needs rows of its own`.
2. **L2. The snapshot follow-up lives only in the landing notes** (`context/specifications/141-the-access-lists-on-the-way-to-the-cache-are-read.md:162`) — "a follow-up reserved for after 0.1.2 … recorded here only, since the roadmap is 151's to edit". A finding kept in one landed specification's notes is easy to lose. Fix text: the pull request's description names it under "gaps", and the orchestrator hands the line to 151's roadmap edit ("Reserved: the access lists on a snapshot file's way, after 0.1.2; source 141's landing notes"). Context only.
3. **Info. The entry walk does not read `errno` at its end** (`src/wasi_python/_platform.py:1238-1242`) — Decision 2 says to stop at the first nonzero answer, and libc's `acl_get_entry` answers -1 only with `EINVAL` (an index past the list, in memory), so a truncated read is not reachable today. No change.

## Structure (not structural; the eight rows, for the record)

| row | moves | reason |
|---|---|---|
| R1 Contract | holds | no public name; `tests/public_api.txt` unchanged; the warning is the same `RuntimeWarning` path |
| R2 Safety | toward Strong | the way's lists read on macOS; unreadable lists and unnamed principals fail closed; the default way still passes (EXECUTED) |
| R3 Layering | holds | no wasmtime-py private API; the C calls stay in `_Darwin` |
| R4 Process state | holds | no module mutable; the ten calls on the instance, built in a local and published whole (EXECUTED both ways) |
| R5 Portability | holds | macOS's reading on `_Darwin`, the empty answer on `_Posix`, chosen once; no branch outside `_platform.py` |
| R6 Testability | holds | the stand-in is the platform object's public method, as for `stack_bounds` and `try_lock`; `_way`'s new parameter is passed only by production code |
| R7 Evolvability | holds | `_platform.py` 1,341 of 1,500; the largest new function 28 lines; docstrings give reasons (L1 the one exception) |
| R8 Operability | toward Strong | the warning names the folder, the principal by name and number, and the rights in `chmod -a`'s words |

## Constitution checks

- §4: no upstream patch, recipe, pin or artifact; uv only; rows count operations, never time; real lists only on folders the rows make, removed in `finally`; code files name no specification, review or `context/` path (lint green); 149's row change is a judge change, claimed under `changed` with its reason.
- §7: nothing tripped. No network, no third-party host, nothing dispatched.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. L1 — fixed in `f1301a36`: the comment above the call in `open_owned` (`src/wasi_python/_platform.py:656-657`) now gives the reason in words, the review's fix text verbatim, split over two lines. READ, confirmed; `tests/lint` 9 passed after it (EXECUTED).
2. L2 — answered in `f1301a36`: the landing notes' disposition paragraph records it in the specification's Differences, names it under gaps in the pull request's description, and hands the roadmap line, in the review's words, to the next documentation change. READ, confirmed.
3. Info — accepted as Decision 2 has it, in the same paragraph. READ.

## Verdict

Lands: run 40715519918 is green on Linux, macOS and Windows (2026-10-28), on head `ea4ed268`, and the review stands as signed below.

Signed earlier on 2026-10-28, on `f1301a36` (`3cc9135a` after the rebase): Lands once the pull request's run is green: the macOS reading, the rule and the words are Decisions 1, 2 and 6 as amended by the pre-build review, the walk keeps 147's and 135's judgments, and the two Lows are write-ins with their fix text.
