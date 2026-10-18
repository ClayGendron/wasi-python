# Review of 061 — A provider's OSError carries its errno (build review)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). I wrote none of the spec, its research memo,
  its pre-build review, the confirmation or the build.
- **Reviewed:** `git diff 5e66995 5c31613` on `spec/061-a-providers-oserror-carries-its-errno`
  (worktree `wasi_python-061`, made from main `5e66995`): `0dc0ffc` (R1 and the status),
  `c34e801` (the code, the seven checks, the docs) and `5c31613` (the landing notes). I judged
  from the spec (Decisions 1 to 11, criteria 1 to 11, stand-ins S0 to S17) and the diff. I used
  the landing notes to find things to check, and judged each listed departure.
- **Read:** AGENTS.md, the constitution (§4.3, §4.4, §4.5, §4.9, §4.10, §4.15, §5.6, §7), the
  owner's answer 54 (`context/decisions.md`), specs 032, 034 and 049, the pre-build review and
  its confirmation (`build/reviews-evidence/061-spec/`), the builder's stand-in script and logs
  (`build/standins/` in the worktree), and `src/wasi_python/mounts.py` at `5c31613` around every
  changed line (`_ask`, `_gate`, `_invoke`, `_made`, `_stat`, `_read`, `_list`, `_close`,
  `_described`).
- **Re-ran:** all with `WASI_PYTHON_ARTIFACTS=…/build/sets/s-c4190ca065ada03a`, on darwin-arm64,
  CPython 3.14.2. Scripts and logs are beside this file.
  - **Fast tier**, `uv run pytest -m "not slow" -n 3` (`fast.log`):
    ```
    wasi_python v1: 319/368 pass · 0 gap · 10 blocked · 0 fail · 39 deselected   (unit suite 1119/1127, 8 skipped)
      v1.2  portable, sealed    61/62  blocked 1
      v1.4  embedding           160/160
    ratchet vs 588ec65390: lost 0 · absent 0 · unrun 0 · unrun locally 8 · gained 4 · grew 0 · upstream unrun 31 · not selected 27 · judge changed: tests/checks/test_v1_2_hostile_guest.py, tests/checks/test_v1_4_embedding.py, tests/unit/test_runner_mounts.py
    1438 passed, 18 skipped in 167.38s (0:02:47)
    ```
    It printed one `PytestUnraisableExceptionWarning`: a `KeyboardInterrupt` inside
    wasmtime-py's `Store.__del__`. It is a pending Ctrl-C from one of the existing Ctrl-C
    checks landing in a later store's deallocator (none of the seven new checks sends a
    signal; READ). It changed no result, and the builder's logs do not show it. Not this
    change (N3).
  - **The full judge, once, serially, no flags** (`full.log`):
    ```
    wasi_python v1: 326/368 pass · 0 gap · 42 blocked · 0 fail   (unit suite 1119/1127, 8 skipped)
      v1.2  portable, sealed    61/62  blocked 1
      v1.4  embedding           160/160
    ratchet vs 588ec65390: lost 0 · absent 0 · unrun 0 · unrun locally 28 · gained 4 · grew 0 · upstream unrun 31 · judge changed: tests/checks/test_v1_2_hostile_guest.py, tests/checks/test_v1_4_embedding.py, tests/unit/test_runner_mounts.py
    1445 passed, 50 skipped in 256.33s (0:04:16)
    ```
    The 42 blocked are the worktree's missing source trees (numpy 17, pandas 16, one each for
    the rest), the oracle, the wheel and the prior-art clones, as the landing notes say. Same
    counts as the builder's `full.log`. No unraisable warning in this run.
  - `uv run ruff check src tests`: clean. `uv run ruff format --check src tests`: 81 files
    already formatted.
  - `uv run python tests/harness/api.py --check`: exit 0. `git diff 5e66995 5c31613 --
    tests/public_api.txt`: empty. The README's generated block (between the `api reference`
    markers) changes in one line, `FileFault`'s summary.
  - `git diff 5e66995 5c31613 -- tests` removes no line: the judge changes only by the seven
    additions. No `tests/known_gaps.toml`, `tests/upstream/` or `context/progress/` change.
  - **Stand-ins and mutants** (`mutants.py`, `mutants.txt`, `mutant-logs/`), on a scratch copy
    of the reviewed commit (`git archive 5c31613` into `copy/`, deleted afterwards), never the worktree. The checks
    ran with the worktree's interpreter and `PYTHONPATH` putting the copy's `src` first (checked:
    `wasi_python.__file__` is the copy's). Each mutant was put back from a byte copy; the copy's
    `mounts.py`, the saved original and the worktree's `mounts.py` all hash `3525544019608b71…`
    afterwards. I re-made S2, S9, S13, S14, S16 and S17 from the spec's table, not from the
    builder's script, and added seven of my own (R1 to R7).
  - **Hostile providers** (`probe_hostile.py`, `probe_hostile.txt`): 37 exceptions given to
    `_raised` directly, with a counter on every hook, and four guest runs.

## Acceptance criteria against evidence

Labels: EXECUTED (I ran it), READ (I read code or text), INFERRED (reasoned, not run).

1. **A raised `OSError` is the answer of its errno (21 names, both mounts).** Met (EXECUTED).
   The check passes. S2 kills it (21 faults). It does what the spec says: `/r` returns
   `Errno[name]`, `/o` raises `OSError(getattr(errno, name), "<name>: <secret>")`; 21 of 21
   under both; `faults == ()`; `calls["stat"] == 42`; the secret in neither output nor
   `repr(done)`. Windows is still to be seen in the release dry run, as the spec says.
2. **The class answers only when the errno is `None`.** Met (EXECUTED). Every row of the
   spec's table is there, in its order, plus one extra row (judged below). Seven faults;
   `_CountStr.calls == []`; one `read` and no `list` for each folder row. S2, S9, S13, S14,
   S16 and my R3 each kill it. S13's failure is exactly the spec's: `TimeoutError(99999)` 73,
   `FileNotFoundError(EINTR)` 44. S14's is the `Stat` row, 44.
3. **A write half's raised `OSError` is a refusal.** Met (EXECUTED). Guest errnos 2, 51, 20,
   75, 31 under both mounts; no fault; the `RefusedWrite`s equal but for `mount`; the last is
   `("write", ("/left",), EDQUOT, "exit", "refused")`. S2, S9 and S16 kill it. My probe adds
   `sync` (an `fsync` refused `EDQUOT`, at `"sync"` then again at `"close"`, the same under a
   returned `EDQUOT`) and `rmdir` (`ENOTEMPTY`), and an `EINTR` raised at a close, which is a
   fault (`"fault"`, `EIO`) while the returned-`EIO` twin is `"refused"`: the record shows the
   errno was not passed on, as Decision 4 promises.
4. **An `OSError` that names no member stays a fault.** Met (EXECUTED), with the departure
   judged below. 16 rows; 15 faults, each one line and at most 200 characters; one `read`
   each; `_RAN == []`; exit 0, `trapped is None`. S2, S9 (`trapped == "out of file calls"`
   after the limit, as the spec says), S16 (the set-after row 29) and my R7 (a `bool` errno
   let through) kill it.
5. **A generator listing that raises answers its errno.** Met (EXECUTED) for what the check
   tests: 44, 44, 2, 29; one fault; `staged` back; `opened == 0`. S16 and my R5 (a mapped
   listing raise also recorded as a fault) kill it. **But** the `iter()` half of Decision 5 is
   not pinned (F2).
6. **A mapped `OSError` leaves nothing of itself.** Met (EXECUTED) for `stat`. Both weak
   references die after `gc.collect()`; the record holds neither the message nor the class
   name. S2 kills it. The listing path's "no reference" is not pinned (F2, my R2).
7. **The host table is by name.** Met in part (EXECUTED). Every row passes, and S17 kills it
   (`KeyError: 'ESTALE'`), as do my R3 (no alias: macOS's 102 is not a key) and the builder's
   S12. **But** the row "a namespace whose `ENOENT` is `True`, or an `int` subclass: `ENOENT`
   is not reached" is vacuous: it tests keys, not values (F1). My R4 (the table takes any
   `isinstance(number, int)`) passes all seven checks.
8. **No existing check changes.** Met (EXECUTED and READ). The diff to `tests/` is additions
   only. The four checks the criterion names pass in both runs.
9. **README.** Met (READ). The protocol's sentence says "or raising an `OSError` (below)". The
   **Raising an OSError** paragraph says each thing the criterion lists: by name, with
   `errno.ENOENT` as `Errno.ENOENT` (44); the six classes only with no errno; an errno outside
   the set is `EIO` and a fault "whatever the class", with `EINTR`'s and `EAGAIN`'s reasons;
   the guest never sees the message; a mapped raise leaves no fault, and a provider that wants
   its raises seen logs them; the Windows host-folder `PermissionError`. The fault sentence
   reads "Any other exception, or an answer outside the protocol, …". The record's `"refused"`
   reads "(your `Errno`, returned or raised)". The docstrings of Decision 10 changed, and
   `run`'s sentence is as Decision 10 words it. `api.py --check` passes; `public_api.txt`
   unchanged; the reference block changes in `FileFault`'s line only.
10. **CHANGELOG.** Met (READ). The entry is the criterion's text, word for word, under
    `## 0.1.0a6 — unreleased`.
11. **The judge is green.** Met (EXECUTED): ruff clean, `api.py --check` passes, the full judge
    lost 0 and grew 0 with v1.4 +3, v1.2 +1 and the unit suite +3.

## The departures

- **S0 now fails criterion 4 on the set-after row.** Correct (EXECUTED: on `5e66995` the row
  gives 29 for 44; every other row passes). The row is a mapped case by design: F10 of the
  pre-build review added it giving 44, to pin the slot read against `e.args[0]`. Main has no
  mapping, so it must give 29. The builder's reading is the only one that satisfies the row.
  The spec's own text is now inconsistent in two places: criterion 4 says "Guards the change
  (S0 passes it)", and the stand-ins' preamble says criterion 4 "is seen failing against its
  stand-ins only". Neither the pre-build review nor the confirmation caught it. See F3: a
  wording fix, so the spec does not contradict its own row.
- **The extra row, `EISDIR` returned at `read`.** Accepted. It is not a fault, so the count of
  seven holds. It makes "as a returned `EISDIR` does" a direct comparison in the same run
  rather than a claim. It also pins the folder rows' call counts (`providers[9]` and `[10]`).
  One weakness: the check names those rows by index (`for i in (9, 10)`), so a row inserted
  above them would check the wrong providers. Harmless today; a nit.
- **S6 and S8 fail on the answer before the count.** Accepted (READ, and EXECUTED for the
  builder's logs). Both mutants change the answer (the lying property and the lying
  `__class__` both give 44) and run code. The check asserts answers first, so it stops there.
  The count is still exercised: S15 is a mutant whose only failure is the count, and it is
  killed (builder's log, `['__class__ (not an OSError)']`). A mutant that ran the property but
  ignored its value would also be caught by `_RAN == []`. The check catches every mutant the
  spec names for it.
- **S12 emulated on the fake hosts.** Faithful (EXECUTED in part).
  - On the real host the builder's S12 uses `errno.errorcode` itself, and on this macOS host
    `errno.errorcode[102] == 'EOPNOTSUPP'` (EXECUTED). So `OSError(errno.EOPNOTSUPP)` gives 29
    and criterion 2 fails on the real table, independent of any emulation.
  - On the fake namespaces it reverses the mapping, the last name for a number winning.
    `_ERRNO_NAMES` puts `EOPNOTSUPP` last, so macOS's 102 maps to `EOPNOTSUPP`, which is no
    member: exactly what the real `errorcode` does on macOS. For Linux (95) the emulation also
    keeps `EOPNOTSUPP`. What `errorcode[95]` holds on a real Linux host I did not check
    (INFERRED either way); whichever name it keeps, the
    criterion-7 failure the spec names is on macOS's numbers, which the emulation models
    correctly.
- **S17 fails before the child runs.** Accepted, and I closed the gap (EXECUTED,
  `s17_child.txt`). The in-process row raises `KeyError` first, so the check never reaches
  the child. I ran the child's code alone against an S17 copy of the package (`PYTHONPATH`, no
  `-I`): `del errno.ESTALE; import wasi_python` exits 1 with `KeyError: 'ESTALE'`. Against the
  reviewed code it prints `False` and exits 0. So the child row kills S17 on its own too.
  - One note on that row: the child runs `sys.executable -I`, which ignores `PYTHONPATH`, so it
    imports whatever `wasi_python` the interpreter's site-packages resolves (here the
    worktree's editable install; EXECUTED). In the lane and in CI that is the tree under test.
    In a scratch copy like mine it is not. Not a defect; worth knowing for anyone who mutates a
    copy.
- **The commit fold.** Accepted. The two unpushed branch commits were folded so that `c34e801`
  is green on its own (AGENTS.md rule 9: the README reference check needs `FileFault`'s
  regenerated line beside its docstring). The "checks first" evidence (Decision 11) lives in
  the S0 logs, not in commit order, and the S0 log shows all seven checks failing on
  `5e66995`'s `mounts.py`. Nothing was pushed or rewritten on main.
- **Not listed as a departure: two private names more than the spec's "five".** The build adds
  `_ERRNO_ALIASES` (the alias the spec asks for, as a dict) and `_Files._listing_raised` (the
  `_list` half of Decision 5's "asks `_raised` the same way"). Both are private, both are named
  under "What was built", and `api.py --check` passes. A nit (N1).

## Probes (hostile providers)

`probe_hostile.py`, output in `probe_hostile.txt`. All EXECUTED on the reviewed code.

- **`_raised` directly, 37 cases, 37 as the spec says, and no hook ran** (`ran=[]` for every
  case): an `int` subclass equal to and hashing as `ENOENT` (its `__eq__` and `__hash__` never
  called); `2**4000`; a negative int; `True`; `False`; `2.0`; `"ENOENT"`; `ENOENT` set after
  construction (44); set and then cleared to `None` (a fault); `OSError("x")` (a fault); each
  of the six classes with errno `None` (their members); `InterruptedError`, `BlockingIOError`,
  `ChildProcessError`, `ConnectionResetError`, `ProcessLookupError` with errno `None` (faults);
  `socket.timeout("timed out")` (`ETIMEDOUT`); a class whose metaclass defines
  `__subclasscheck__`, `__instancecheck__` and `mro`, with errno `None` (a fault) and `ENOENT`
  (44); a `__getattribute__` override; an `errno` property over a slot of `EINTR` (a fault, the
  property never ran); a `__class__` property (never ran); a `FileNotFoundError` subclass whose
  `__init__` never calls `super()` (slot `None`, so the class: `ENOENT`); a counting `__str__`
  (never called); `ValueError`, `KeyError`; `EOPNOTSUPP` and `ENOTSUP` (both `ENOTSUP`);
  `EINTR`, `EAGAIN`, `EMFILE`, 76 (faults).
- **The metaclass:** `raise` of the metaclass class calls `__subclasscheck__` once, in the
  provider's frame, and `_raised` afterwards calls nothing. This is the pre-build review's F1,
  confirmed on the build.
- **Generators and iterators in a listing** (one guest run, `max_file_calls=50`): a generator
  raising `FileNotFoundError(ENOENT)` before its first `yield` → 44; after two yields,
  `PermissionError("…")` → 2; an iterator whose `__next__` raises `NotADirectoryError(ENOTDIR)`
  → 54; an iterable whose `__iter__` raises `FileNotFoundError("…")` → 44; a generator raising
  `InterruptedError(EINTR)` after a yield → 29 and the only fault. One `list` call each. The
  guest's `strerror` is its own C library's ("No such file or directory").
- **OSErrors from answer objects:** a `Stat` subclass whose `kind` raises
  `FileNotFoundError(ENOENT)`, one whose `size` raises `PermissionError`, and a `bytes`
  subclass whose `__buffer__` raises `FileNotFoundError(ENOENT)` at `memoryview()`. Each gives
  29 and a fault, as Decision 5 says.
- **Writes mapped during staging:** a create (`PermissionError` with no errno → `EACCES`, at
  `"open"`), a close (`ENOSPC`), an `fsync` (`EDQUOT`, at `"sync"` and again at `"close"`), an
  `rmdir` (`ENOTEMPTY`) and the ending's walk (`EROFS`, at `"exit"`): every one equals the
  twin mount that returns the same member. An `EINTR` raised at a close is a fault.
- **Nothing of the provider's message reaches the guest or the record.** Every message held a
  secret. Across the four guest runs the secret was never in `stdout` or `stderr`, never in
  `done.files.refused`, and in `repr(done)` only inside an *unmapped* fault's `error`
  (`_described`'s first line, host side, as spec 032 has it). A mapped raise's weak reference
  was dead after the run, and its run had `faults == ()`.
- **The name table:** no `sys.platform` in `mounts.py` (READ and grep); a namespace without
  `ENOSYS` builds without error and does not reach `ENOSYS`; one without `ENOTSUP` still
  reaches `ENOTSUP` through the `EOPNOTSUPP` alias (right, since wasi-libc spells it so); a
  mapping whose `[]` raises but whose `.get` works builds the full 22 keys, so the table uses
  `get` only. The host table on macOS: 22 keys, 21 members, 102 → `ENOTSUP`.

## Findings, most severe first

1. **F1 (low). Criterion 7's "`True` or an `int` subclass" row is vacuous.** EXECUTED.
   - **Where:** `tests/unit/test_runner_mounts.py`, `test_the_host_errno_table_is_by_name`:
     ```python
     for bad in (True, Sneaky(errno.ENOENT)):
         assert Errno.ENOENT not in mounts_module._errno_table({**vars(errno), "ENOENT": bad})
     ```
     `x in dict` tests keys. The table's keys are host numbers; `Errno.ENOENT` is the
     `IntEnum` 44, and 44 is no member's host number on macOS (`ESOCKTNOSUPPORT`) or Linux
     (`ECHRNG`). So the assertion holds for any table, whatever it does with `True` or the
     subclass.
   - **Evidence:** my R4 makes `_errno_table` accept `isinstance(number, int)`. All seven
     checks pass (`mutants.txt`). On a hand-built table that does map `Sneaky(2)` to
     `ENOENT`, the check's expression is still `True`; by `.values()` it is `False`.
   - **Why it matters:** criterion 7 lists this row, and Decision 2 says the table "keeps only
     values that are exactly `int`". Nothing pins it. The runtime is not affected: `vars(errno)`
     holds plain ints on every host. So this is the judge's gap, not a live hole.
   - **Fix:** `.values()` on that line (the `ESTALE` row below it already does this). I
     checked the fixed expression (EXECUTED): under R4's table both halves reach `ENOENT`
     (`True` as key 1, since `ENOENT` precedes `EPERM` in `Errno`'s order, and `Sneaky(2)`),
     so both would fail; under the built table neither does, so both pass.
2. **F2 (low). Two halves of Decision 5 and 6 are built but not pinned.** EXECUTED.
   - **R1, `iter()` not mapped** (`_list` takes `iter(answer)` outside the new `try`). All
     seven checks pass. Criterion 5 uses only generators, and `iter()` of a generator runs no
     provider code. Decision 5 names `iter()` as one of the three places, and the probe shows
     the build maps it (an `__iter__` raising `FileNotFoundError` gives 44).
   - **R2, a mapped listing exception kept on the table** (`self.kept = e` in
     `_listing_raised`). All seven checks pass. Criterion 6 tests only `stat`'s path, so the
     "holds no reference" promise of Decision 6 is unpinned for the listing path.
   - **Why low:** the code is right in both places (READ, and the probe for R1). The spec's
     criteria did not ask for these rows, so the build meets them; this is a gap in the
     criteria that a later change could fall through.
   - **Fix:** one row in criterion 5: a non-generator iterable whose `__iter__` raises
     `FileNotFoundError("x")`, answering 44. Optionally, one weak-reference row in criterion 6
     with the raise in a generator `list`. Both are additions to the judge, said so in the
     notes.
3. **F3 (nit). The spec contradicts its own criterion 4 row.** READ. Criterion 4 says "Guards
   the change (S0 passes it)", and the stand-ins' preamble says criterion 4 is "seen failing
   against its stand-ins only". Since F10 of the pre-build review added the set-after row
   (44), S0 fails it. The landing notes record the departure correctly. **Fix:** in criterion
   4, "Guards the change: S0 fails only the set-after row, a mapped case"; and in the preamble,
   "(criterion 4, but for that row)". Wording only.
4. **N1 (note).** Two private names beyond the spec's "five" (`_ERRNO_ALIASES`,
   `_Files._listing_raised`). Both serve a Decision; neither is public. Mention them in the
   departures for completeness, or leave.
5. **N2 (note, docs).** `WritableFileProvider`'s new sentence says an `OSError` "is a refusal
   when it names a member, as for the read half". It leaves the no-errno class out, which the
   read half's paragraph covers; "as for the read half" carries it. The README line for
   `"refused"` (`` `Errno`, returned or raised), `"fault"` … ``) now runs to 100 characters
   where its paragraph wraps at 80. Cosmetic.
6. **N3 (note, not this change).** The fast tier printed a `PytestUnraisableExceptionWarning`:
   a `KeyboardInterrupt` delivered inside wasmtime-py's `Store.__del__`, from a Ctrl-C check's
   pending signal. None of the seven new checks sends a signal; no result changed. It belongs
   with the existing Ctrl-C checks, if anywhere.
7. **N4 (note).** `_raised`'s `try`/`except Exception` (my R6 removes it) and the order of
   `_RAISED` cannot be told apart by any check, and I found no input that makes either matter:
   every read inside `_raised` is a C-level type check or a dict lookup on an exact `int`. They
   are belt and braces, as the spec intends ("total").

## Constitution checks

- **§4.3 (one target, no host-specific branch):** holds (READ, grep). One code path; no
  `sys.platform`. The table is the host's `errno` module read by the guest's names; Decision 2
  says why that is not a branch, and the owner's answer 54 is the reason it exists.
- **§4.4 (two imports only):** holds (READ). No guest change, no import or export change. The
  guest still receives one `i32` per call.
- **§4.5 (embedder-neutral):** holds. No embedder is named.
- **§4.9 (tests count):** holds (READ). Every new check counts errnos, calls, faults, refusals
  and live references. The `EINTR` stand-in is bounded by `max_file_calls=20`.
- **§4.10 (claims carry evidence):** holds. The landing notes label their runs EXECUTED, and
  the Windows column stays INFERRED until the release dry run runs criterion 1 there. My one
  INFERRED claim (Linux's `errorcode[95]`) is labelled.
- **§4.15 (safe by default):** holds. No default changes. The image of `_raised` is the 21
  members a provider can already return; no number outside the closed set can reach the guest
  by raising (EXECUTED: 37 hostile cases, none outside the set).
- **§5.6:** this review re-ran the fast tier and the full judge, re-made six stand-ins and
  seven mutants of its own, and checked each criterion against its evidence.
- **§7:** nothing tripped. Not build-class (no `scripts/`, `recipes/`, `downloads/SHA256SUMS`
  or workflow change). I wrote nothing in either git tree: mutants ran on a scratch copy;
  `git status` in the worktree is clean afterwards.

## Verdict

**Lands once F1 is fixed.** F1 is one word (`.values()`) in a check that the spec lists as a
criterion, and as written it guards nothing. F2 is two optional rows I recommend at the same
time, since both are cheap and pin promises the spec makes in words. F3 is a wording fix to
the spec. Everything else holds:
- every criterion is met (criterion 7 once F1 is in);
- every stand-in I re-made is killed with the failure the spec names, and so are R3, R5 and
  R7 of mine;
- 37 hostile exceptions run no provider code at the boundary and never leave the closed set;
- nothing of a mapped exception reaches the guest or the record;
- the public API is unchanged and the reference changes in `FileFault`'s line only;
- the full judge is green with lost 0 and grew 0.

## One line

A raised `OSError` now answers by its errno's name, exactly as a returned `Errno` would, and
reads a hostile exception without running it. One check row tests dict keys instead of values
and so guards nothing; fix that, and it lands.

## Confirmation (2026-10-18)

The same reviewer checked `5c31613..c3c2bb6`: `68f9f8f` (the checks, one docstring, the README
rewrap) and `c3c2bb6` (the spec's revision and its Disposition). I read the diff and re-ran the
evidence rather than take the notes' word. All runs used
`WASI_PYTHON_ARTIFACTS=…/build/sets/s-c4190ca065ada03a`. Mutants ran on a fresh
`git archive 68f9f8f` copy in the scratchpad, never the worktree, with the same `mutants.py`;
the copy's `mounts.py` was put back byte for byte and matches `68f9f8f`'s and the worktree's
(`e5b01d8f24dd860d…`). Logs are in `confirm/` beside this file.

1. **F1: confirmed fixed (READ, EXECUTED).** Criterion 7's row now asserts
   `Errno.ENOENT not in _errno_table({...}).values()`. R4 (`isinstance(number, int)` in the
   table), which passed all seven checks before, now fails criterion 7 alone:
   `assert <Errno.ENOENT: 44> not in dict_values([...])`.
2. **F2: confirmed fixed (READ, EXECUTED).**
   - Criterion 5 gains a non-generator iterable whose `__iter__` raises
     `FileNotFoundError("x")`, answered 44. R1 (`iter()` outside the mapped `try`) now fails
     criterion 5 alone: `assert (29, None) == (44, None)`.
   - Criterion 6 gains the listing path: a generator `list` that yields once and raises a
     weakly referenced `_SecretNotFound(ENOENT, …)`; 44, the reference dead after
     `gc.collect()`, neither message nor class name in the record. R2 (`self.kept = e` in
     `_listing_raised`) now fails criterion 6 alone: the reference is alive.
3. **The rest of the mutant set on `68f9f8f` (EXECUTED, `confirm/mutants-68f9f8f.txt`).** S2,
   S9, S13, S14, S16, S17, R3, R5 and R7 are still killed, each by the same checks as before
   (R5 now also by criterion 6's listing row). R6 still survives, as N4 said and the
   Disposition answers. The unmutated copy passes 7 of 7.
4. **F3: confirmed (READ).** The stand-ins' preamble now says main fails criterion 4 only on its
   one mapped row, and criterion 4 says "S0 fails only the set-after row, a mapped case". The
   spec no longer contradicts its own row. The landing notes' departure points at it.
5. **N1, N2 and the folder-row index: confirmed (READ).** N1 is a departure naming both private
   names. `WritableFileProvider`'s sentence names the no-errno class rule. The README line is
   rewrapped to 80 columns, with no other README change. Criterion 2 finds its folder rows by
   their `"open"` action and asserts there are two.
6. **N3 and N4: the answers are sound.** N3 is not this change; neither of my runs below printed
   the warning. N4's guards are kept as the "total" promise; no check is owed.
7. **The judge (EXECUTED).** `ruff check` clean; `ruff format --check` 81 files formatted;
   `api.py --check` exit 0; `tests/public_api.txt` unchanged against `5e66995`; the diff to
   `tests/` against `5e66995` still removes no line.
   - Fast tier, `-n 3`, on `c3c2bb6` (`confirm/fast.log`):
     ```
     wasi_python v1: 319/368 pass · 0 gap · 10 blocked · 0 fail · 39 deselected   (unit suite 1119/1127, 8 skipped)
       v1.2  portable, sealed    61/62  blocked 1
       v1.4  embedding           160/160
     ratchet vs 588ec65390: lost 0 · absent 0 · unrun 0 · unrun locally 8 · gained 4 · grew 0 · upstream unrun 31 · not selected 27 · judge changed: tests/checks/test_v1_2_hostile_guest.py, tests/checks/test_v1_4_embedding.py, tests/unit/test_runner_mounts.py
     1438 passed, 18 skipped in 145.69s (0:02:25)
     ```
   - The full judge once, serially, no flags, on `c3c2bb6` (code identical to `68f9f8f`;
     `confirm/full.log`):
     ```
     wasi_python v1: 326/368 pass · 0 gap · 42 blocked · 0 fail   (unit suite 1119/1127, 8 skipped)
       v1.2  portable, sealed    61/62  blocked 1
       v1.4  embedding           160/160
     ratchet vs 588ec65390: lost 0 · absent 0 · unrun 0 · unrun locally 28 · gained 4 · grew 0 · upstream unrun 31 · judge changed: tests/checks/test_v1_2_hostile_guest.py, tests/checks/test_v1_4_embedding.py, tests/unit/test_runner_mounts.py
     1445 passed, 50 skipped in 272.88s (0:04:32)
     ```
     The same counts as the builder's revised run. The 42 blocked are the worktree's missing
     source trees, oracle, wheel and clones, as before.
   - The worktree's `git status` is clean afterwards.

**Confirmed, it lands.**
