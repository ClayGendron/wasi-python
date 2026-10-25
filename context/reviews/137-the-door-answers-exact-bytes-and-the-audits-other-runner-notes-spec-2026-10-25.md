# Review of 137 — The door answers exact bytes, and the audit's other runner notes

- **Date:** 2026-10-25
- **Reviewer:** an agent (Claude); not the author
- **Reviewed:** the specification as drafted, `context/specifications/137-the-door-answers-exact-bytes-and-the-audits-other-runner-notes.md`, at commit `1bfccd6c` on `research/performance-specs-2026-10-24`, whose `src/` is the 0.1.0 release's (`git diff --stat 2cd47507 HEAD -- src` is empty, EXECUTED), with the audit `context/reviews/0.1.0-security-audit-2026-10-25.md` and the hunters' evidence for h05, h14, h01 and h03
- **Run:** none; nothing built. The specification as drafted. Checklist items 1 and 2 (the CI run, the builder's self-check) do not apply.
- **Re-ran:**
  - `uv run pytest "tests/checks/test_rules.py::test_specifications_have_their_header_and_sections" "tests/checks/test_rules.py::test_specifications_have_no_open_question" "tests/checks/test_rules.py::test_markdown_paragraphs_are_one_line_each" "tests/checks/test_rules.py::test_no_module_under_src_is_over_the_line_ceiling" -q -p no:cacheprovider` → **3 passed, 1 failed** in 1.38 s. The failure is the paragraph check, and all 14 of its findings are in `context/research/2026-10-24-moving-to-wasmtime-50/wasmtime-49.0.4-notes.md`, a tracked file outside this specification. It fails the same way at HEAD without this review. No finding names 137.
  - `uv run python tests/harness/wrap.py --check context/specifications/137-…md` → exit 0, and the same for this file.
  - The door probe (`PYTHONPATH=src`, Python 3.14.2, `_call.MAX_RESPONSE` patched as `test_the_door_bounds_every_frame` patches it). It compares today's `_door_answer` with Decision 1's conversion on eight answers. Output is in `build/137-review/door-probe.txt`; the results are under criterion 2.
  - Measurements: `wc -l src/wasi_python/*.py` (`_platform.py` 1,464, `_call.py` 1,343, `_private_dirs.py` 272, `_zip.py` 289); the touched functions' lengths by `ast` (`_door` 57, `frame` 31, `_poll_plan` 32, `_poll_oneoff` 36, POSIX `make_missing` 23, `_sweep_entry` 57, `_member_parts` 12); platform branches in `_call.py`, `_zip.py` and `_private_dirs.py`: none (grep). All EXECUTED.
  - No fast tier, no shard, no full judge.
- **Time box:** 45 minutes (six Decisions across five modules). The box held, with the write-ins inside it.

Labels: EXECUTED means I ran it. READ means I read the file cited. INFERRED means my own reasoning.

## Acceptance criteria against evidence

1. **Every Decision 7 row green on three systems, each seen failing first on `2cd47507`.** Met for most rows; four are not, as listed here.
   - `bytes_subclass_over_max` fails today: 5,000 bytes pass a cap of 1,000 (EXECUTED).
   - `len_lies` fails today, in the shape h05 used: a `__bytes__` that returns a subclass with a lying `__len__`. Today's code hands home a `Liar` whose `len` is 1 over a 3,000-byte buffer (EXECUTED).
   - On 3.11 and later, a plain subclass with a lying `__len__` and no `__bytes__` of its own is already copied to exact `bytes` by `bytes()`. So the row must keep h05's shape (EXECUTED: `len_lies` and `bytearray_len_lies` come back exact today at a cap of 10,000).
   - `host_raises_trap` fails today: trapped "from the host" (READ, `door_probe_results.json`).
   - `reentrant_depth3` fails today in the sense the row means: exit 3 with four host calls, not a fault (READ). But the abort the guard exists for is a different run, the unbounded one (finding 5).
   - The 2 GiB-plus row cannot fail first without a 2 GiB answer (finding 4).
   - The poll rows fail today where h14 shows a difference (READ, `compare_wasmtime.json`).
   - The folder rows need a seam that does not exist yet (finding 8).
2. **The h05 probe reports a fault or exact bytes on the built tip.** The conversion is sound, on this evidence (EXECUTED, the probe).
   - Decision 1's conversion is `bytes()`, then `bytes(memoryview(...))` when the type is not exactly `bytes`, then the cap on `len`. On every shape I tried it gives an exact `bytes` whose `len` is its buffer, or `None` past the cap.
   - The shapes: a `__bytes__` that returns more; a `__bytes__` that returns a liar; a `bytearray` subclass with a lying `__len__`; a `bytearray` subclass with `__bytes__`; a 3.12+ `__buffer__` that disagrees with the object; a `memoryview` of an `int` array.
   - Over the cap, the answer is `None`, so `HOST_FAULT` (-2), and the guest's `_host.call` raises `OSError`. That is the same fault type as today's "response too large" row (READ, `test_v1_2_hostile_guest.py:250-273`). No new error type.
   - `memory.write` copies its argument with `bytearray(value)` and writes `len` of that copy (READ, wasmtime-py `_memory.py:122-124`). With exact `bytes`, the `alloc` size, the bound check and the write are one length. That closes the write past the allocation on the `bytes`, `bytearray` and `memoryview` paths alike.
3. **`_platform.py` under its ceiling, functions under 80, no module-level mutable, seams on the process object.** Met as drafted, with notes.
   - Ceiling: 1,464 lines plus about 12 for Decision 3 (with its Windows sentence, finding 2) is about 1,476, under 1,500 (EXECUTED, `wc`; INFERRED, the count). 137 alone does not need 131. 131 has a roadmap line but no specification file yet (EXECUTED, `ls context/specifications`). So "stacks on 131" would wait on a specification not yet written. If 135 lands first and takes lines, the builder measures again.
   - Functions: `_door` at 57 lines plus the narrowed `try` and the depth guard is about 67, under 80 (INFERRED).
   - Mutable state: the depth fits in `_door`'s closure, which is built once per `_Call` (`_call.py:682`, READ), so it is per call and not a module global.
   - Seams: the folder seam is not named (finding 8).
4. **`tests/public_api.txt` unchanged; ruff and mypy clean; no code file names the archive.** Nothing public moves. `MAX_RESPONSE`, `_door_answer`, `_poll_plan`, `_member_parts` and `make_missing` are private (READ). This is a build-time check.
5. **The documents carry Decision 6's text.** The lines exist where cited (READ):
   - `security-model.md:20` (the cache, "a grant or root");
   - `:28` (the host's `Exception`, no text);
   - `:101` (dicts and sets);
   - the sections *Your process's own resources* (`:87`) and *Time, randomness and hashing* (`:97`);
   - `grants.md:104`, which says "A **writable** grant or `root`".

   One wording is short (finding 10).
6. **The release workflow on the built tip; Windows legs read for the zip-name and poll rows.** As asked. Decision 3 also needs a Windows sentence before Windows can be read against it (finding 2).

**The door's re-raise** (READ, `_call.py:1240-1246`, `_home.py:227-241`, wasmtime-py `_func.py:189-218`):
- What passes the door untouched today: `wasmtime.Trap` and `WasmtimeError` from anywhere in the frame, the host's included; and every `BaseException` that is not an `Exception`, that is `KeyboardInterrupt`, `SystemExit` and the home's `_Stopped`.
- The second group is raised from `run()` by design (`runner.py:239`).
- After Decision 2, only `alloc`'s wasmtime errors pass.
- There is no leak of host text to the guest, today or after the change. The guest gets -2, or its run ends. The text reaches the embedder's `Done.trapped`. Decision 2 fixes an embedder-facing outcome against `security-model.md:28`. It closes no guest channel. The specification says so correctly.

**The sweep** (READ, `_private_dirs.py:186-188`): `os.lstat` and `S_ISDIR` already refuse a symbolic link at the folder's name, and `isjunction` refuses a junction. The new `_owned(folder)` compares `st_uid` with `getuid()`, and it is true on Windows (`_private_dirs.py:152-154`). In a sticky temporary folder, no other user can swap the name between the check and `remove_tree`. That makes the `lstat`-time check enough (INFERRED).

**The zip's member names** (READ, `_zip.py:108-119`). Refused today: an empty name, a leading `/`, a backslash, any `:` (drive letters and streams), and `""`, `.` or `..` as a component. A NUL never reaches the guard, because `zipfile.ZipInfo` cuts a name at its first NUL. Missing today, as the specification says: reserved device names, a trailing dot or space, and case-equal names. Finding 6 gives the predicate to use.

## Findings, most severe first

1. **High: Decision 5's descriptor rule has no way to know wasmtime's own descriptors** (`_call.py:1082-1137`, `_fs_table.py:97-134`).
   - The defect: `_poll_plan` is a pure function of the raw subscriptions. The call's table holds only the mounts' entries (`self.table`) and the numbers of what wasmtime opened (`self.held`), never their kind.
   - What it leads to: every file the guest opens on a plain grant or on the zip is wasmtime's descriptor, not a table entry. Read as written ("a number the table does not hold … answers `EBADF`"), Decision 5 answers `EBADF` for every such file, where wasmtime and today's shadow both answer ready. That is a wrong answer on a path that works today.
   - Failure: a guest opens `/data/x.txt` on a read-only grant and polls it for reading. Wasmtime answers ready, nbytes 1. The built shadow answers `EBADF`.
   - The second part of the defect: telling a held file from a held folder would mean asking wasmtime (a forward of `fd_fdstat_get`, which writes into guest memory) or tracking `path_open`. The specification chooses neither.
   - What closes it: one paragraph in Decision 5 that names the mechanism. A sufficient text:
     > "A descriptor subscription is answered from what the runner knows: 0 to 2 as today; a preopen's number (3 up to 3 plus the call's preopens) and a mount's folder `EBADF`; a mount's file, or a number in the table's `held`, ready; any other number `EBADF`. `_poll_plan` takes a `kind(fd)` argument, so the unit rows stay pure. A folder the guest opened through `path_open` is held, and is answered ready where wasmtime answers `EBADF`: a kept difference, said in the docstring, since the runner does not ask wasmtime a descriptor's kind."
   - Then write a row for a file opened on a plain grant (ready on both).
2. **Medium: Decision 3 says nothing for Windows** (`_platform.py:602-606`, `:1270-1275`).
   - The defect: Windows makes a missing root through `_make_by_path`, the branch Decision 3 calls "systems without `dir_fd`". There, `mkdir`'s mode is ignored, `os.geteuid` does not exist, and `os.lstat(...).st_uid` is 0. The new `grants.md` sentence, "made for you alone (0700)", would be false on one of the three systems.
   - Failure: the builder writes `os.lstat(p).st_uid != os.geteuid()` in `_make_by_path`. On `windows-2025`, every missing `root` then raises `AttributeError`. Or the builder skips the check and the documents overclaim.
   - What closes it: one sentence in Decision 3:
     > "On Windows the mode and the owner test do not apply (a made folder takes its parent's inherited access list, and Windows has no uid); the rows are POSIX-only with that reason, and `grants.md` says 'on Linux and macOS'."
   - The Windows access-list question then goes to its own roadmap line, if the owner wants it.
3. **Low: converting before the cap copies an over-cap answer first** (`_call.py:1220-1222`).
   - The defect: today's comment says "checked in bytes, before the copy". With Decision 1's order, a 1.9 GiB `bytearray` is copied, doubling it, before it is refused.
   - Fix text for Decision 1:
     > "`if memoryview(response).nbytes > MAX_RESPONSE: return None` stays as the first test, then the conversion, then `len(data) > MAX_RESPONSE` again on the exact bytes."
4. **Low: the 2 GiB sentence contradicts itself and is dead code** (Decision 1, last two sentences; `_call.py:46,48`).
   - The defect: `MASK32` is 4 GiB minus 1, not 2 GiB. And `MAX_RESPONSE` is already `0x7FFFFFFF`, so once the cap is on exact bytes, no answer at or past 2 GiB passes it. The 2 GiB-plus row of Decision 7 would need a 2 GiB answer in the judge, and today's code refuses a plain one anyway, so the row cannot fail first.
   - Fix text: replace "`len(response)` is also checked against `MASK32` before `alloc` (a response at or past 2 GiB is a fault, not a truncated size)" with:
     > "The cap, `0x7FFFFFFF`, is below 2 GiB, so on exact bytes it also keeps every length within a signed i32 and wasmtime-py never truncates one; no second test."
   - In Decision 7, replace "a 2 GiB-plus length (fault)" with:
     > "`MAX_RESPONSE < 2**31`, asserted (a guard row, not one seen failing)."
5. **Low: the re-entry evidence is cited to the wrong case** (The problem, the door paragraph; Decision 7).
   - The defect: `reentrant_depth3` returned exit 3 with four host calls and no abort (READ, `door_probe_results.json`). The abort, exit 134, was run 1's unbounded module (READ, h05 `result.json`, and the probe's line 67, skipped in run 2).
   - Fix text: in the door paragraph, "(`reentrant_depth3`)" becomes "(h05's unbounded run 1, exit 134; `reentrant_depth3` returned normally)". Decision 7 gains:
     > "`reentrant_unbounded` in a subprocess (today the process aborts; after, the nested call is a fault and the process exits normally)."
6. **Low: Decision 4 should call the runner's existing Windows name rule** (`_platform.py:197-207`, `:1111-1118`).
   - The defect: `_platform._rewritten(name)` is already "the same answer as `ntpath.isreserved` gives". It covers the devices with `COM¹` to `LPT³`, `CONIN$` and `CONOUT$`, a trailing dot or space, `:`, and the characters Windows rejects. A second list in `_zip.py` would drift from it.
   - Fix text for Decision 4:
     > "A component for which `_platform._rewritten` is true is refused, on every system; the case-equal test is `_zip`'s own."
7. **Low: two owner tests would disagree** (Decision 3; `_private_dirs.py:152-154`).
   - The defect: Decision 3 compares with the effective uid. `_owned` uses `getuid()`.
   - Fix text:
     > "The owner test is one function in `_platform.py` (`os.geteuid()` where it exists, else no test), and `_private_dirs._owned` calls it."
   - `_platform` cannot import `_private_dirs`, which imports `_platform`. So the function belongs in `_platform`.
8. **Low: the Kind line and the claim list miss files the build changes** (Kind line; For the lane).
   - Decision 7's injected `fstat` is a new `process().observers` field, so `_process.py` changes. `tests/unit/test_process.py:171-188` tables the observers' fields, so it changes too.
   - Decision 5 changes `_poll_plan`'s arguments. `tests/unit/test_runner_waits.py::test_descriptors_follow_wasmtime` asserts fd 9 ready, `(7, 1, 1)` at line 90, which becomes `EBADF`.
   - `tests/unit/test_runner_door.py` does not exist. The door rows belong beside `tests/checks/test_v1_2_hostile_guest.py::test_the_door_bounds_every_frame`, which already patches `MAX_RESPONSE`.
   - Fix text: the Kind line gains "`_process.py` (one observers field, the owner seam), `_fs_table.py` if Decision 5 reads `held`". The claim list's changed verdicts gain "`tests/unit/test_runner_waits.py::test_descriptors_follow_wasmtime` (fd 9 moves from ready to `EBADF`, as wasmtime answers it); `tests/unit/test_process.py`'s observers table (one field)". Decision 7's door bullet reads "in `tests/checks/test_v1_2_hostile_guest.py`, beside `test_the_door_bounds_every_frame`".
9. **Low: two parts of the poll change are unsaid** (Decision 5; `_call.py:1171-1172`, `compare_wasmtime.json`).
   - Error handling: `_fs_memory._ends` returns a `WasmtimeError`, which is an `Exception`. `_poll_oneoff.call`'s `except Exception: return EINVAL` would swallow it into `EINVAL`.
   - Kept differences: h14 shows wasmtime ending the run for an out-pointer with no room, where the shadow answers `EFAULT`. So "the same errno or end as wasmtime" cannot hold for that row.
   - Fix text for Decision 5:
     > "`call` re-raises a `WasmtimeError` before its `except Exception`, and records the fuel as `_Files.__call__` does for an ABI error; the bounds' `EFAULT` (wasmtime ends the run) and the `32*n` bound are kept differences, named in the docstring and asserted as the shadow's own answers."
10. **Low: the XML sentence names too few parsers** (Decision 6, second bullet).
    - The defect: every parser on `pyexpat` shares the salt, and the bullet lists only three.
    - Fix text:
      > "and XML parsed by Python's expat parsers (`xml.etree`, `xml.dom.minidom`, `xml.sax`, `plistlib`, `xmlrpc`), whose parser salt is the same fixed key".

## Structure

Checklist item 4a, against AGENTS.md's definition. No Decision is structural, so the Kind line's **not structural** holds, and no eight-row section is owed. Each test, with what I checked:

- **Platform branches.** None is added outside `_platform.py`. Decision 4 calls `_platform._rewritten` on every system (finding 6), which is not a branch. Decision 3's Windows sentence lives in the platform classes. A grep found no `sys.platform`, `os.name` or `platform.system` in `_call.py`, `_zip.py` or `_private_dirs.py` today (EXECUTED).
- **Module-level mutables or locks.** None: the door's depth lives in a per-call closure (READ, `_call.py:682`).
- **Private API.** None is used outside `_wasmtime_ffi.py`, provided Decision 5 takes finding 1's mechanism. A forward of `fd_fdstat_get` would go through `_Files.forward`, which already uses the seam.
- **Seams.** The one new seam is on the process object.
- **Ceilings.** No module crosses its ceiling, and no function passes 80 lines (criterion 3).

R2 moves toward Strong, because the door's cap becomes a cap on what is written. R5 is unchanged once finding 2's sentence is in.

## The split

Split, along three seams, not four:

1. **137, the door:** Decisions 1 and 2, the door rows, and Decision 6's three sentences that need no row (the cache's "writable", the XML salt, the fork). It is ready once findings 3, 4, 5, 8 and 10 are written in. It carries the audit's one EXECUTED overrun.
2. **The folders and the zip's names:** Decisions 3 and 4, with the `grants.md` sentence. Both are host-filesystem guards. Both need the Windows decision (finding 2) and the new owner seam.
3. **The poll shadow:** Decision 5. It shares no code with the others, and it carries the High.

The reason for the split: the three halves differ in readiness (ready, one Medium, one High), in their Windows story, and in the checks they move. As one specification, the High in the poll half holds the door fix, the fix with the evidence of an overrun, behind a design question. Decision 6 is not a fourth seam. Its lines are a few sentences each, best landed with the behaviour they describe.

## Constitution checks

- §4.15 (safe by default): every change tightens. The one an embedder can see is a made root's folders at 0700 instead of the umask's mode. Under §4.15 a tightening needs no decision from the owner, but the CHANGELOG line must name it, and it does. Holds.
- §4.1 and §4.2 (patches and pins): no upstream source, pin or download is touched. Holds.
- §5.6: this is the pre-build review the Status line asks for (runner code). The guest's imports and exports do not change; the artifact set does not change. Holds.
- §7 never-do list: nothing tripped. No wall-clock check (the rows count bytes and errno values), no artifact in git, and nothing copied from prior art. I polled no upstream host.

## Disposition (filled in by the author, then confirmed by the reviewer)

The author's answers, 2026-10-25. **The split:** done as the review asked, along its three seams. 137 is renamed `../specifications/137-the-door-answers-exact-bytes.md` (the `git mv` of the file this review names) and keeps Decisions 1 and 2 and Decision 6's three documentation-only sentences, its Decisions renumbered 1 to 4. Decisions 3 and 4, with the `grants.md` sentence, are `../specifications/139-the-runners-folders-are-this-users-and-the-data-guard-refuses-windows-names.md`; Decision 5 is `../specifications/140-the-poll-shadow-answers-as-wasmtime-does.md`. Each says it is independent of the other two and of 131; 139 measures `_platform.py` at 1,464 lines (EXECUTED, `wc -l`) and adds about 17 (INFERRED, a sketch of the change), about 1,481 of 1,500. `context/roadmap.md`'s 137 line is narrowed and lines for 139 and 140 follow it.

1. Decision 5's descriptor mechanism (High) — fixed in 140, Decision 3, with the review's paragraph as written; Decision 5 gains the plain-grant file row (ready on both). One addition, labelled INFERRED for 140's own pre-build review: `held` is read before the preopen numbers, so a file the guest renumbered onto a preopen's number is ready, as wasmtime answers it. 140's Status says it is not fit to build until its own pre-build review.
2. Decision 3 on Windows (Medium) — fixed in 139, Decision 1's Windows paragraph, with one correction to the suggested text: from Python 3.13, `os.mkdir` on Windows applies a mode of exactly 0700 as a protected access list for the user, SYSTEM and the Administrators (READ, `Modules/posixmodule.c:6208-6215` and `Doc/library/os.rst:2569-2570,2587-2588` in the pinned 3.15.0 source under `build/Python-3.15.0/`), so "the mode does not apply" holds only on 3.11 and 3.12. The owner test does not apply on Windows (no uid); the folder rows are POSIX-only with that reason; `grants.md` says "on Linux and macOS" for the owner test and what Windows does instead. A Windows owner test by security identifier is out of scope, after 131, the owner's call. The reviewer is asked to confirm this paragraph; 139's Status waits on that confirmation.
3. The nbytes pre-check before the copy (Low) — fixed in 137, Decision 1, with the review's text.
4. The 2 GiB sentence and row (Low) — fixed in 137: Decision 1 carries the `0x7FFFFFFF` sentence in place of the `MASK32` one; Decision 4's row is the `MAX_RESPONSE < 2**31` guard row.
5. The re-entry evidence and the unbounded row (Low) — fixed in 137: The problem cites h05's unbounded run 1 (exit 134) and says `reentrant_depth3` returned normally; Decision 4 gains `reentrant_unbounded` in a subprocess.
6. `_platform._rewritten` for the zip's names (Low) — fixed in 139, Decision 3, with the review's text; the case-equal test is `_zip`'s own, in `_extract_data`.
7. One owner test (Low) — fixed in 139, Decision 2, with the review's text: `_platform._this_users`, by `os.geteuid()` where it exists, which `_private_dirs._owned` calls.
8. The Kind line and the claim list (Low) — fixed across the three. 137: the door rows in `tests/checks/test_v1_2_hostile_guest.py` beside `test_the_door_bounds_every_frame`; `tests/unit/test_runner_door.py` is gone. 139: the Kind line names `_process.py` (one observers field, the owner seam) and the claim list names `tests/unit/test_process.py`'s observers table; the seam is `owner_of`, a stand-in owner for a stat result, rather than an injected `fstat`, so one row can tell the lock from the folder beside it. 140: the Kind line names `_fs_table.py` (the `kind` method that reads `held`) and the claim list names `tests/unit/test_runner_waits.py::test_descriptors_follow_wasmtime` (fd 9 moves from ready to `EBADF`).
9. The poll's `WasmtimeError` and its kept differences (Low) — fixed in 140, Decision 4, with the review's text.
10. The XML parsers (Low) — fixed in 137, Decision 3, with the review's text.

Nothing declined.

**Reviewer's confirmation (2026-10-25).** I read the disposition and the three specifications at `6fafb803`. All ten items are closed as written. Item 2, 139's Windows paragraph, stands. It is more exact than my suggested text, which it rightly corrects. The source shows the claim (READ, `os_mkdir_impl` in `build/Python-3.15.0/Modules/posixmodule.c:6185-6235`): when `mode == 0700`, Windows `os.mkdir` creates the folder with the protected access list `D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FA;;;OW)`, full control to SYSTEM, the Administrators and the owner, and it ignores any other mode. `Doc/library/os.rst:2569-2570,2587-2588` says the same and marks it "changed in 3.13". Gh-118486, the fix for CVE-2024-4030, was, as I recall it, also carried by 3.12's later security releases. That is INFERRED, since the clones here show only 3.13's news. So I endorse the paragraph's hedge, that nothing relies on a 3.11 or 3.12 backport, and it needs no change. The `owner_of` seam is sound: an `_Observers` field on the process object, `None` in production, never read on Windows because `_this_users` answers yes there first. It is named in 139's Kind line and in its claim list (`test_process.py`'s observers table). Item 1 (the High) is closed as text in 140. Whether `held` holds every number the guest has on every call (spec 068's counted calls), and the INFERRED `held`-before-preopen order, are for 140's own pre-build review. Verdicts: **137, fit to build**. **139, fit to build**, its Status's wait on this confirmation now met. **140, waits on its own pre-build review**, as its Status says.

## Verdict

Fit to build split as 137 (the door: Decisions 1 and 2, with Decision 6's three documentation-only sentences), a folders specification (Decisions 3 and 4, once the Medium's Windows sentence is written), and a poll specification (Decision 5, not fit to build yet: High 1, its descriptor rule has no mechanism for wasmtime's own descriptors).
