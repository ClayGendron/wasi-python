# Review of 061 — A provider's OSError carries its errno

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). It wrote none of 061, its memo or its probes.
- **Reviewed:** the specification as drafted and its research memo with its evidence folder,
  branch `spec/061-a-providers-oserror-carries-its-errno` at `1c85f56` (diff `5e66995...HEAD`:
  the spec, the memo and its 16 evidence files). A pre-build review. §5.6 does not require one
  here; it was asked for because 061 changes a fault boundary that spec 032's security review
  examined.
- **Re-ran:** no full judge run. A pre-build review changes no code, and the brief kept both
  trees read-only. Instead:
  - `spec_model.py` is the reviewer's own model of 061 as written: `_errno_table`, `_raised`,
    `_invoke`, and `_list` with `iter()` and `next()` mapped. It is not the memo's model, which
    maps only at `_invoke`. `REVIEW_MUTANT=class_only_when_none` selects one mutant.
  - The guest probes ran against the frozen set `build/sets/s-c4190ca065ada03a` (read-only).
    Its `SHA256SUMS` hashes to `3c0ec02e25e0b91d…`, the memo's set. They used wasmtime-py
    49.0.0 and CPython 3.14.2 on macOS arm64, from the 061 worktree. (`build/artifacts` in the
    main tree vanished during the session, presumably because a build was running, so the frozen
    set was used instead.)
  - The existing checks named in criterion 8, plus the whole of `tests/unit/test_runner_mounts.py`,
    ran with the model loaded as a pytest plugin. `--progress-dir` and `--progress-latest`
    pointed at the scratchpad: **71 passed**, both serially and with `-n 3`
    (`existing_checks_under_model*.txt`). The harness marks such a run RED ("steered from
    outside the judge"), as it should.
  - The scripts and their outputs sit beside this file: `probe_host.py`/`.txt`,
    `probe_guest.py` with `probe_guest_model.txt`, `probe_guest_built.txt` and
    `probe_guest_mutant_class_only_when_none.txt`, `probe_meta.py`/`.txt`,
    `probe_raw.py`/`.txt`, and `probe_versions.py`/`.txt`. Three CPython 3.14.8 files and one
    3.15.0 file were extracted from the pinned tarballs into `cpython_src/` and `cpython315/`,
    for reading only.
  - `git status` in the 061 worktree is clean afterwards. The guest runs did create the
    runner's git-ignored `.cwasm` cache, `build/cwasm-cache`, in the worktree.

Labels: EXECUTED (run here), READ (read in a file), INFERRED (reasoned, not run).

## The questions the brief asked

- **Is the name-based mapping sound?** Yes.
  - On macOS the table has 22 keys. All 21 members are reached, `EOPNOTSUPP` (102) maps to
    `ENOTSUP`, and no refused name is a key: `EINTR`, `EAGAIN`, `EWOULDBLOCK`, `EBADF`,
    `EFAULT`, `ENOMEM`, `ELOOP`, `EMFILE`, `ENFILE` (EXECUTED, `probe_host.txt`). Linux is the
    memo's EXECUTED table.
  - On macOS `errno.errorcode[102]` is `"EOPNOTSUPP"` (EXECUTED). So S12, the reverse lookup,
    is a real hazard, and building the table by name is right.
  - wasmtime-py passes the host function's `i32` through unchanged (memo, READ). The guest's
    errno equals `Errno[name].value` in every mapped case run here (EXECUTED,
    `probe_guest_model.txt`).
  - **Windows** (READ, CPython 3.14.8 `Modules/errnomodule.c`):
    - `ETIMEDOUT`, `EOPNOTSUPP` and `EWOULDBLOCK` are `#undef`'d and redefined from `WSAE*`.
    - `EDQUOT`, `ESTALE`, `ENAMETOOLONG` and `ENOTEMPTY` fall back to `WSAE*` only when the C
      library lacks them.
    - `ECANCELED`, `ENOTSUP` and `ENOSYS` are added only `#ifdef`. MSVC's `errno.h` defines
      them (INFERRED, as the memo says). If it did not, the name would be missing (F4).
    - `Objects/exceptions.c:4506-4508` maps both `ETIMEDOUT` and `WSAETIMEDOUT` to
      `TimeoutError`.
    - Criterion 1 in the dry run decides all of this, as the spec says.
- **Is the refusal set right?** Yes.
  - The mapping's image is the 21 members, which a provider can already return.
  - `ENOMEM`, `ELOOP`, `EMFILE`, `ENFILE` and the rest are not members, so they are already
    faults (EXECUTED: not keys, and the guest gets 29 for `ELOOP`, `EBADF`, `EFAULT`, `EINTR`,
    `EAGAIN` and `EWOULDBLOCK`).
  - `ENAMETOOLONG` and `EROFS` are members. Refusing them only when *raised* would break
    "raising is returning" (Decision 1). It would also make nothing safer, since a provider can
    return them.
  - Can a raise mislead the runner's own guards? `_gate` never reads a provider's answer. The
    places where the runner branches on one see the same `Errno` value, raised or returned
    (READ, `mounts.py`):
    - `_open_writing`: `ENOENT` leads to a create, and `O_EXCL` tests `errno != ENOENT`;
    - `_read`: `EISDIR` makes a folder descriptor.

    So a raise can mislead nothing that a return could not.
- **Is the class fallback consistent with decision 54?** For an `errno` of `None`, it is a fair
  reading: PEP 3151 names one errno for each of the six classes. For an errno that is present
  but not usable, the spec contradicts itself and no check decides it (F2).
- **Does "read from OSError's slot, so no subclass property runs" hold?** Yes.
  - `OSError.__dict__["errno"]` is a `member_descriptor` on 3.11, 3.12, 3.13 and 3.14
    (EXECUTED, `probe_versions.txt`).
  - Neither an `errno` property, a `__getattribute__` override nor a `__class__` property ran
    on any of them (EXECUTED).
  - `issubclass(type(e), base)` with a built-in `base` never consults the exception's
    metaclass (EXECUTED).
- **Hostile providers** (EXECUTED, `probe_host.txt`; under the model):
  - **Odd `__init__`:**
    - a subclass whose `__init__` never calls `OSError.__init__` keeps `errno` `None`, so it is
      a fault for a plain `OSError` subclass and the class's member for one of the six;
    - a `__new__` that passes `EACCES` gives `EACCES`.
  - **Errno set after construction:** on a plain `OSError`, `ENOENT` gives `ENOENT`. On a
    `FileNotFoundError`, `EINTR` gives `ENOENT` (F2).
  - **Values that are not a plain errno:** `True`, an `int` subclass, `2**70`, `10**4000`, `-2`
    and `2.0` are each a fault, and none of their code runs.
  - **A metaclass whose `mro()` inserts `FileNotFoundError`:** gives `ENOENT`. Its code ran
    only when the class was made, and the answer is still a member, so this is harmless.
  - **Two of the six classes at once,** `class Both(FileNotFoundError, PermissionError)`: gives
    `ENOENT`, the first in order. That is deterministic.
  - **An `ExceptionGroup` holding a `FileNotFoundError`:** a fault.
  - **Generators** (EXECUTED, `probe_raw.txt`, criterion 5's four paths): a raise before the
    first `yield` gives 44, a raise after one `yield` gives 44, `PermissionError` gives 2, and
    `ValueError` gives 29. That is one fault, `staged` unchanged, and no number held.
- **A mapped error during a write.** EXECUTED (`probe_guest_model.txt`, criterion 3's six
  points):
  - The raising mount and the returning mount give the guest 2, 51, 20, 75 and 31.
  - Their `RefusedWrite`s are equal but for `mount`, the last being `EDQUOT` at `"exit"`.
  - There are no faults.

  `_made` never touches `staged` (READ). A refused write-back leaves the buffer dirty, exactly
  as a returned refusal does.
- **Does anything leak?** No.
  - The secret text is in neither `stdout`, `stderr` nor `repr(done)` (EXECUTED).
  - The record holds neither the message nor the class's name (EXECUTED, `probe_raw.txt`).
  - With no reference cycle, the exception and the provider's local are dead before any
    collection. With a cycle the provider's own frame makes, they live until `gc.collect()`
    (F7).
- **Are the criteria and stand-ins strong enough?**
  - Mostly. Every prediction for S0, S3 and S5, and for the model, matched (EXECUTED, as built
    and under the model).
  - There are three holes. A builder could pick either reading of F2. It could map an answer
    object's `OSError` (F3). And criterion 4 cannot pass as worded (F1).
- **Does it fit spec 049?** Yes (READ).
  - `tests/public_api.txt` records no docstrings.
  - `tests/harness/api.py` renders only each item's and each method's summary (lines 921 and
    936). So the second paragraphs of `FileProvider` and `WritableFileProvider` change no
    reference line, and only `FileFault`'s entry changes, as Decision 10 says.
  - Decision 8 lets an alpha change anything.
  - Calling the change a minor-release addition after 0.1.0 is a fair reading, because no name,
    signature or field changes.

## Acceptance criteria against the evidence

1. Raised equals returned, for 21 names — sound. The memo's `equivalence_model.json` gives 21
   of 21 with 21 stats per mount. Windows is decided in the dry run.
2. The class answers — sound for the rows given, which matched the model exactly (EXECUTED).
   But they do not separate the two readings of F2, and they have no answer-object row (F3).
3. The write half — sound (EXECUTED, every clause).
4. Unmapped stays a fault — the guest's answers and call counts matched (EXECUTED: 15 cases,
   29 each, 15 `read` calls). **"The hostile classes' own code ran 0 times" fails on a correct
   build** (F1). S9's prediction depends on how the mutant is written (F9).
5. Generator listings — sound (EXECUTED).
6. Nothing kept — sound. It already collects (F7 is about wording).
7. The table by name — sound, but it lacks a host that misses a name (F4).
8. No existing check changes — confirmed under the model: 71 of 71 (EXECUTED).
9. and 10. The README and the CHANGELOG — sound, but missing one sentence (F6).
11. The judge — not run here (pre-build).

## Findings, most severe first

1. **Medium — criterion 4's "the hostile classes' own code ran 0 times" fails for the metaclass
   row on a correct build, and that row guards nothing.** EXECUTED (`probe_meta.txt`), as built
   and under the model.
   - A `raise Odd("x")` calls `Meta.__subclasscheck__(Odd, Odd)` once. It does so in the
     provider's own frame, at the `raise`, before the boundary sees anything. CPython's
     `_PyErr_SetObject` asks `PyObject_IsSubclass(type(value), type)`, and `Odd` is not an
     exact `type`.
   - So the count is 1, not 0, for S0, for the model and for any implementation. The builder
     would have to change the check to pass it.
   - The row also guards nothing. The hooks run only when `Odd` is the *second* argument of
     `issubclass` or `isinstance`, and no plausible boundary ever calls them with `Odd` there.
     The memo's `hostile.py` called `answer_of` directly, without a `raise`, which is why it
     saw 0.
   - A second, smaller trap in the same clause: `_described` calls `str(e)` for every
     *unmapped* fault, so a hostile class with a `__str__` would count a run (EXECUTED,
     `probe_host.txt`: `_described_runs___str__`). The clause must exclude `__str__`.
   - **Fix.** Either drop the metaclass row, or have its hooks count only a subject other than
     the class itself (`if sub is not cls`). Then say the 0 counts the boundary's reads, not
     the provider's `raise` and not the existing fault text's `str(e)`.
   - Optional, for a row that does guard step 1: an `Exception` that is not an `OSError`, whose
     `__class__` property returns `FileNotFoundError`. It should give 29 and run 0 times. A
     step 1 written with `isinstance(e, OSError)` runs the property.

2. **Medium — the class fallback for an errno that is present but not usable contradicts
   Decision 4, and no criterion decides it.** EXECUTED (`probe_host.txt`,
   `probe_guest_model.txt`, `probe_guest_mutant_class_only_when_none.txt`).
   - **Decision 3 as written.** Step 2 gives nothing for "an unknown number", and step 3 then
     tries the class. So:
     - `FileNotFoundError(errno.EINTR, "x")` is `ENOENT`, with no fault (guest 44);
     - `PermissionError(errno.EAGAIN, "x")` is `EACCES`;
     - `TimeoutError(99999, "x")` is `ETIMEDOUT` (guest 73).
   - **Decision 4 says otherwise.** It says `EINTR`, `EAGAIN`, `EBADF` and `EFAULT` are
     "Each … a fault, `EIO`, with its `FileFault`. So an embedder sees in the record that its
     errno was not passed on." For the six classes that is false: the errno is dropped
     silently, and the class answers.
   - **No check separates the readings.** A mutant that tries the class *only when the errno
     is `None`* passes every row of criteria 2, 3 and 4 as written. It differs only on the two
     rows this review added (29 instead of 73 and 44).
   - **The owner's words** ("its errno is then the guest's answer (any other exception stays a
     fault, `EIO`)") fit the stricter reading better. When a refused errno is present, a class
     overriding it is a choice the owner did not make.
   - **Fix: decide, write it in Decisions 3 and 4, and pin it.**
     - **(a) Recommended:** the class answers only when the slot is `None`. An errno that is
       present and not in the table is a fault, so Decision 4's sentence becomes true. The
       *Why the class at all* bullet about Windows' `WAIT_TIMEOUT` (errno 138, unnamed) goes;
       that rare case becomes a fault with its record.
     - **(b)** Keep the code as drafted. Then rewrite Decision 4: "a fault, unless the class is
       one of the six, which then answers". Drop "the embedder sees in the record". Say in the
       README that a refused errno on one of those classes is replaced by the class's member.
     - Either way, add rows to criterion 2 for `TimeoutError(99999, "x")` and
       `FileNotFoundError(errno.EINTR, "x")`, with their answers. Add a stand-in for the other
       reading (S13).

3. **Medium — the exclusion of answer objects (Decision 5) is not pinned, and one of its
   sentences is wrong about today's code.**
   - **Not pinned.** No criterion raises an `OSError` from an answer object. A builder who also
     maps in `_stat`'s or `_read`'s `except` passes everything.
     - EXECUTED (`probe_guest_model.txt`): a `stat` that returns a `Stat` subclass whose `kind`
       read raises `FileNotFoundError(errno.ENOENT)` gives the guest 29 and a fault under
       061's rule. That mutant would give 44 (INFERRED).
     - Add that row to criterion 2, with a stand-in that maps in `_stat`'s and `_read`'s
       `except`.
   - **Wrong sentence.** Decision 5 says an exception from "the listing iterator's `close`" is
     "an answer outside the protocol and stays a fault". As built, `_close` swallows every
     `Exception` and records nothing (READ, `mounts.py` `_close`). Write "is ignored, as today".
   - **Imprecise sentence.** "A listed item's checks" can raise nothing: `_listed` runs no
     provider code. Dropping it, or saying so, avoids the builder looking for a case.

4. **Low — a host that lacks a member's name is neither specified nor tested.**
   - Decision 2 says "`getattr(errno, member.name)` maps to the member". Taken literally, or
     written as `names[member.name]`, that raises at import on a host without the name.
     `mounts.py` is imported by `wasi_python/__init__.py`, so the whole package would fail to
     import there.
   - Windows defines `ECANCELED`, `ENOTSUP` and `ENOSYS` only `#ifdef` (READ). The memo's
     Windows column is INFERRED.
   - **Fix.** Write "a name the host lacks is skipped". Add a criterion 7 namespace without
     `ESTALE`: 21 keys, `ESTALE` not reached, no error. (EXECUTED with the model: 21.)
     Criterion 1 would then fail on such a host with one wrong errno, rather than with an
     import error everywhere.

5. **Low — §4.3 is not addressed, though 032 refused `OSError` on it.** READ: spec 032's
   Decision 3 and its review say "accepting `OSError` would bring a host-specific mapping into
   the runner (§4.3)".
   - 061 builds exactly that mapping, from each host's `errno` module. Decision 54 settles the
     question. But the spec should say in Decision 2 why this is not a host-specific branch:
     - one code path, with no `sys.platform` test;
     - names, never numbers;
     - the behaviour that differs by host (Windows' `PermissionError` for a folder) is the
       provider's, and is documented (criterion 9).

     It should also say that the owner's answer replaces 032's reason.

6. **Low — the README does not say that a mapped raise leaves no trace, and `run`'s docstring
   goes slightly out of date.**
   - Before 061, a provider bug that raises `FileNotFoundError` for its own reasons (its own
     configuration file missing, say) was a fault in the record. After 061 it reads as the
     guest's missing file, with nothing recorded.
   - Decision 1 already gives the answer ("an embedder who wants to know logs in its own
     provider"). Criterion 9's *Raising an OSError* paragraph should say it.
   - `run`'s docstring (`runner.py:334`) says a provider's `Exception` is "recorded in the
     result". A mapped `OSError` is an answer, not a recorded fault. Add it to Decision 10's
     list, for example "…makes `run` raise: it is an answer, or recorded in the result".
     It is not the summary, so the README reference does not change.

7. **Low — Decision 6's "no frame of the provider outlives the call" is stronger than the
   facts.** EXECUTED (`probe_raw.txt`).
   - A provider whose own frame holds the exception (`err = …; raise err`) makes a reference
     cycle: the exception, its traceback, the provider's frame and its locals. That cycle is
     alive after the boundary returns, and dead only after `gc.collect()`. With no cycle, both
     are dead at once.
   - The true claim is that the runner holds no reference. Criterion 6 already collects first.
   - **Fix:** "the runner keeps no reference to it; a cycle the provider's own frame makes is
     freed by the collector, as for a fault today."

8. **Nit — Decision 9's 054 bullet (INFERRED) is wrong in part.** READ, CPython 3.15.0
   `Lib/importlib/_bootstrap_external.py:1406-1411`.
   - `FileFinder._fill_cache` catches only `FileNotFoundError`, `PermissionError` and
     `NotADirectoryError` from `listdir`. So today an `EIO` from a raising `list` propagates
     out of `import`, while after 061 an `ENOENT` reads as missing.
   - It is still no interaction with 054, which refuses mounts as import-path servers. But
     "importlib treats a failed `stat` as missing either way" should become: a failed `list`
     was an import error and becomes a missing module.

9. **Nit — S9 must be defined as an errno, not an answer.**
   - The predicted EINTR loop (20 calls, `"out of file calls"`) happens only if the mutant
     returns `(wasi_number, None)` from `_invoke`.
   - If it returns the number as the *answer*, `_read` judges an `int` a bad answer. The
     `EINTR` and `ELOOP` rows then give 29 with a fault, and the mutant passes criterion 4
     (INFERRED from `_read`).
   - Write S9 as "`_invoke` returns `(n, None)`, where n is the preview1 number of any name in
     the host's `errno`".

10. **Nit — two small gaps in Decision 5's reason and criterion 4's rows.**
    - Decision 5 justifies not mapping answer objects because "these objects are values the
      method returned". Yet `iter()` and `next()` on a returned non-generator iterable are
      that object's own code, and they are mapped. State the rule by place (the call,
      `iter()`, each `next()`). The reason: a generator's body runs there, and the runner
      cannot tell a generator from another iterator without running code.
    - Criterion 4 could add "a plain `OSError` whose `errno` is set to `errno.ENOENT` after
      construction" giving 44. It pins the slot read against an `e.args[0]` reading, which
      passes every row as written (INFERRED).

## Constitution checks

- §4.3 (one target, no host-specific branch): no branch on the platform, but the spec should
  say why the name table is not one (F5).
- §4.4 (two imports only): unchanged. No guest change, no new import (READ).
- §4.5 (embedder-neutral): met. No embedder is named.
- §4.9 (tests count): met. Every check counts errnos, calls, faults, refusals and live
  references. The EINTR stand-in is bounded by `max_file_calls`, not a clock.
- §4.10 (claims labelled): the memo labels every claim, and the Windows column is honestly
  INFERRED. One INFERRED claim is wrong in part (F8).
- §4.15 (safe by default): no default changes. A mount is an explicit argument, and a raise
  gives the guest only what a provider could already return. The closed set stays closed
  (EXECUTED).
- §5.2 (no open questions): none, once F2's reading is decided and written in.
- §5.6: a pre-build review is optional here and was held. This is it.
- §6: name over number, and the six classes, are the agent's to choose under decision 54. The
  class overriding a present errno is not clearly within the owner's words (F2).
- §7: nothing tripped. Neither tree was written. Every probe ran from the scratchpad against a
  frozen set, and the existing checks ran with the progress files redirected to the
  scratchpad.

## Verdict

**Ready once F1 to F4 are written in.** F5 to F7 are a sentence each and should go in at the
same time. F8 to F10 are optional.

One line: name over number is right, and the boundary reads a hostile exception without running
it. But criterion 4's metaclass count cannot pass, the class's override of a present errno
contradicts Decision 4 and is unpinned, and the answer-object exclusion and a missing host name
need a row each.

## Confirmation of 061's revision (2026-10-18)

An addendum to `061-a-providers-oserror-carries-its-errno-spec-2026-10-18.md`, by the same
reviewer. I wrote none of 061 or its revision.

- **Reviewed:** `git diff 1c85f56 06c6222` on `spec/061-a-providers-oserror-carries-its-errno`.
  The diff changes only the specification. Its new section, "Disposition of the pre-build
  review", maps F1 to F10. The memo is left as written, and the spec governs where they differ.
  That is the house rule, and I accept it.
- **Re-ran** against the frozen set `build/sets/s-c4190ca065ada03a` (read-only), from the 061
  worktree:
  - The model is `spec_model.py` with `REVIEW_MUTANT=class_only_when_none`. That mutant is
    exactly the revision's outline: the class is tried only when the slot is `None`, and a
    present errno that is not in the table is a fault.
  - The script is `confirm_probe.py`, and its output is `confirm_probe.txt`. It ran once under
    that model, and once with S14 added (`_stat`'s `except` also maps).
  - The earlier outputs still apply: `probe_guest_mutant_class_only_when_none.txt` is reading
    (a), and `probe_guest_model.txt` is the draft's reading, which is now S13.
  - Nothing was written in either git tree.

Labels: EXECUTED (run here), READ (read in the diff), INFERRED (reasoned, not run).

## Each finding against the text

1. **F1 — confirmed.**
   - The metaclass row is gone. Criterion 4 now counts only the `errno` property and the two
     `__class__` properties, and says why the metaclass and `__str__` on an unmapped fault are
     not counted.
   - Each count is 0 on a correct build (EXECUTED):
     - the slot-`EINTR` `errno` property: 0, under the model in `probe_guest_model.txt` and in
       `probe_guest_mutant_class_only_when_none.txt`, criterion 4;
     - the `OSError` subclass with a `__class__` property: 0, in the same two runs;
     - the new non-`OSError` `Exception` with a `__class__` property: 0, and the guest gets
       29 (`confirm_probe.txt`, `ran: []`). Neither CPython's `raise`, nor `except Exception`,
       nor `_described` reads `__class__`.
   - S15 (`isinstance(e, OSError)`) runs that property once (INFERRED). The type check fails,
     so `isinstance` falls back to `__class__`. The slot read on a non-`OSError` then raises
     `TypeError`, which the `except` turns into a fault.
   - The `__str__` count on a mapped raise moved to criterion 2: 44, and `__str__` called 0
     times (EXECUTED, `CountStr`).
   - Decision 3's paragraph on what the boundary reads, and what CPython runs outside it,
     matches `probe_meta.txt`.
2. **F2 — confirmed.**
   - Reading (a) is written consistently in all of these places:
     - Decision 3, steps 2 to 4, and its new *Why only when the errno is `None`*;
     - Decision 4 ("whatever the exception's class");
     - the outline;
     - the Intent;
     - criteria 2, 9 and 10.
   - The outline is the code I ran (EXECUTED):
     - `FileNotFoundError(errno.EINTR, "x")` gives 29 with a fault;
     - `TimeoutError(99999, "x")` gives 29 with a fault;
     - S13 gives 44 and 73 (`probe_guest_model.txt`).
   - Every other row of criteria 2 to 4 gives the same answer under (a) as before (EXECUTED).
     The Windows `WAIT_TIMEOUT` cost is stated.
3. **F3 — confirmed, with one build-time wording note (R1).**
   - The `Stat` row, S14 and "faults: exactly seven" are written in, and the seven add up.
   - Decision 5 now says `_close` swallows, and that `_listed` runs no provider code.
   - EXECUTED (`confirm_probe.txt`): a `Stat` subclass whose `kind` property raises
     `FileNotFoundError(errno.ENOENT)` gives 29 and a fault under the model, and 44 under S14.
     That holds only when the property has a setter (see R1).
4. **F4 — confirmed.**
   - Decision 2 has been rewritten: `names.get`, a name the host lacks is skipped, and the
     import never fails.
   - Criterion 7 gains the namespace without `ESTALE` (EXECUTED earlier: 21 keys).
   - It also gains the child process, `sys.executable -I -c`, which deletes `errno.ESTALE` and
     then imports `wasi_python`. Under `uv run`, an `-I` child still loads the venv's
     editable install. The memo's and my own `-I` probes import `wasi_python` that way.
   - S17 (`names[member.name]`) gives `KeyError`, and the child exits 1 (INFERRED).
5. **F5 — confirmed.** Decision 2's §4.3 paragraph says what I asked: one code path, no
   `sys.platform` test, names not numbers, and the owner's answer replacing 032's reason.
6. **F6 — confirmed.**
   - Criterion 9's paragraph and the CHANGELOG entry both say a mapped raise leaves no fault,
     and that a provider which wants its raises seen logs them itself.
   - `run`'s sentence is in Decision 10, the Kind line and the Design. It is not a summary, so
     the reference still changes only in `FileFault`.
7. **F7 — confirmed.** Decision 6 now says the runner holds no reference, and that a cycle the
   provider's own frame makes is freed by the collector. That matches `probe_raw.txt`.
8. **F8 — confirmed.** Decision 9 cites `_fill_cache` with the right lines and the right
   conclusion.
9. **F9 — confirmed.** S9 is now "`_invoke` returns `(n, None)`", an errno, so the `EINTR` loop
   that criterion 4 predicts does happen.
10. **F10 — confirmed.**
    - Decision 5 names the three places, and gives the reason for mapping every iterable's
      `iter()` and `next()`.
    - The set-after row gives 44 under the model (EXECUTED, `confirm_probe.txt`). It is the
      one row of criterion 4 with no fault, and the text says so.
    - S16 (`e.args[0]`) reads `"x"`, which is neither `None` nor an `int`, so under (a) it
      gives 29 (INFERRED). That matches the prediction.

## Remaining

- **R1 (low; write it in at build).** Criterion 2's `Stat` row should say how the subclass is
  built.
  - `Stat` is a frozen dataclass. Its `__init__` sets `kind` with `object.__setattr__`, so a
    `kind` property *without a setter* makes construction itself raise `AttributeError`.
  - EXECUTED (`confirm_probe.txt`, the `NoSetter` row): built inside `stat`, that
    `AttributeError` is a fault, with guest 29, under the correct build *and under S14*.
    Built that way, the row passes S14, and the fault count stays seven.
  - The fix: write "a `kind` property with a setter (the setter stores nothing the runner
    reads)", or say "a `__getattribute__` that raises for `kind`". With a setter, S14 gives 44
    (EXECUTED).
  - The builder's own step, seeing each check fail against each stand-in, would catch this.
    That is why it does not reopen the review.

No other finding. No open question, no wall-clock, still embedder-neutral, and still no line of
`tests/public_api.txt`.

**Verdict: confirmed — ready to build.** R1 is a one-line clarification to write in at build.

One line: every finding is written in as asked, and the rows I ran give the predicted answers;
only the `Stat` row should say its property needs a setter, or it cannot fail S14.
