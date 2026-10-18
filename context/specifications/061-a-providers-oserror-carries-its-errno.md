# 061 — A provider's OSError carries its errno

- **Status:** drafted 2026-10-18; revised against its pre-build review
  (`../reviews/061-a-providers-oserror-carries-its-errno-spec-2026-10-18.md`, written in the
  lane's evidence folder, `build/reviews-evidence/061-spec/`, and copied in by the lane;
  verdict: "ready once F1 to F4 are written in", F5 to F7 at the same time, F8 to F10
  optional); every finding written in (the section "Disposition of the pre-build review");
  **confirmed for build 2026-10-18 (R1 written in)**: the reviewer's confirmation of `06c6222`
  (`../reviews/061-a-providers-oserror-carries-its-errno-spec-2026-10-18-confirmation.md`,
  written in the same evidence folder and copied in by the lane; "confirmed — ready to build",
  with one low note, R1, written into criterion 2). It changes neither the guest's
  imports nor its exports, the artifact set nor the build recipe, so §5.6 asks no review before
  build; one is asked for because it changes a fault boundary that spec 032's security review
  examined (its Decision 4).
- **Owner:** Clay Gendron
- **Kind:** the runner and docs; **parallel-safe**, not build-class: `src/wasi_python/mounts.py`
  (`_Files._invoke`, `_Files._list`, five new private names, four docstrings) and one
  sentence of `run`'s docstring in `src/wasi_python/runner.py`, judge additions
  in `tests/checks/test_v1_4_embedding.py`, `tests/checks/test_v1_2_hostile_guest.py` and
  `tests/unit/test_runner_mounts.py`, `README.md`, `CHANGELOG.md`. It touches no `scripts/`,
  `recipes/`, `downloads/SHA256SUMS` or workflow, and not the guest package. **It changes no
  line of `tests/public_api.txt`** (spec 049's snapshot): no name, signature, field, default or
  `Errno` member is added, removed or changed. It widens the behaviour behind `FileProvider` and
  `WritableFileProvider`, and the docstring summary of `FileFault`, so the README's generated
  reference changes in that one entry (Decision 10).
- **Depends on:** 032 (the filesystem provider: `_invoke`, the fault boundary, `Errno`, the
  record) and 034 (writable mounts: `_made`, `RefusedWrite`, the ending's walk), landed; 049
  (the public API frozen), landed; 053 and 054, landed, with no interaction (Decision 9). 055
  (bounded sessions, confirmed for build) uses the same mount table and inherits this rule
  without a change of its own; whichever lands second rebases, with local conflicts only in
  `mounts.py`.
- **Research it stands on:** `../research/2026-10-18-a-providers-oserror-carries-its-errno.md`
  and its evidence folder (`host_errno.py` with its macOS and Linux outputs; `guest_sees.py`,
  `equivalence.py`, `folder.py` and `retry.py`, run against the main tree's artifact set; `model.py`, a model
  of the boundary; `hostile.py`). The owner's answer to question 54 (`../decisions.md`, "49–89"):
  "a provider may also raise `OSError`; its errno is then the guest's answer (any other exception
  stays a fault, `EIO`). A follow-up change to spec 032's provider."

## The problem

Spec 032 made a provider answer with values: a `Stat`, a listing, bytes, or an `Errno`. Any
exception is a fault: the guest gets `EIO` and the record gets a `FileFault` (its Decision 4).
That keeps a provider whose own layer never raises honest, but it fights ordinary Python. A
provider over a dict or a host folder raises `FileNotFoundError`, and today the guest sees
`[Errno 29] I/O error` for a missing file (EXECUTED, the memo's finding 1: all 20 raised
`OSError`s tried gave the guest 29, and each left a fault).

The owner decided that an `OSError` is an answer. Three things make that more than a one-line
change:

- **Host numbers are not WASI numbers.** `errno.ENOENT` is 2 on macOS, Linux and Windows, and 2
  is WASI's `EACCES`. `EDQUOT` is 69 on macOS, WASI's `EROFS`; `ENOTEMPTY` is 66, 39 or 41 by
  host (the memo's finding 2). Passing the number through would lie.
- **Some numbers must never reach the guest.** WASI's `EINTR` makes the guest's `open()` retry
  until the file-call limit stops the run: 50 provider reads for one `open` under
  `max_file_calls=50` (EXECUTED, finding 3). Spec 032 closed the set for that reason.
- **The idiom often carries no errno.** `raise FileNotFoundError(path)` sets `errno` to `None`;
  only the two-argument form sets it (EXECUTED, finding 4). A socket's timeout is
  `TimeoutError("timed out")`, also `None`.

## Decisions

1. **A raised `OSError` that names a member of `Errno` is that answer, exactly as if returned.**
   - The guest gets the member's number. The runner then does what it does for the returned
     member: `read`'s `EISDIR` makes a folder descriptor; a write-half answer is a refusal.
   - The record is the same as for the returned member. The call is counted; there is no
     `FileFault`. A write-half call gives `RefusedWrite(mount, method, paths, member, at,
     "refused")`. A refused `stat`, `list` or `read` is not recorded, as today.
   - Anything else stays a fault, unchanged: an `OSError` that names no member (Decision 3), any
     other `Exception`, and an answer outside the protocol give the guest `EIO` and a
     `FileFault`. A `BaseException` that is not an `Exception` is still the call's stop, raised
     from `run`.
   - **Why "exactly as if returned".** One rule covers both forms, so nothing downstream changes:
     the descriptor table, the write half, the walk and the record all see an `Errno`. The
     record cannot tell a raised answer from a returned one, and does not need to; an embedder
     who wants to know logs in its own provider.

2. **The errno is matched by name, never by number.**
   - At import, `mounts.py` builds a private table, `_HOST_ERRNO: dict[int, Errno]`, from the
     host's `errno` module: for each member whose name the host defines, the host's number for
     that name maps to the member. **A name the host lacks is skipped** (the review, F4): that
     member is then reached only by a returned `Errno` or by Decision 3's class, and importing
     `wasi_python` never fails for it. Windows defines `ECANCELED`, `ENOTSUP` and `ENOSYS` only
     if its C library does (READ, `errnomodule.c`), so a missing name is possible there.
     One alias is added: the host's `EOPNOTSUPP` maps to `ENOTSUP`, because the guest's own C
     library defines `EOPNOTSUPP` as `ENOTSUP` (READ, wasi-libc's `__errno_values.h`). On
     Linux the two share 95 already; on macOS (102) and Windows (`WSAEOPNOTSUPP`) they differ.
   - The table is made by a private function, `_errno_table(names: Mapping[str, object]) ->
     dict[int, Errno]`, given `vars(errno)`. It reads each name with `names.get(name)`, never
     `names[name]`; it keeps only values that are exactly `int`, and keeps the first member for
     a number (`setdefault`, in `Errno`'s order, then the alias). The unit check feeds it
     macOS's, Linux's and Windows's numbers, and a namespace that lacks a name (criterion 7).
   - **Why by name.** A name means the same thing on every host and in the guest; a number does
     not (the memo's table). Every member's name exists on macOS and Linux, with no two members
     sharing a number on either (EXECUTED). On Windows, CPython defines `EDQUOT`, `ESTALE`,
     `ETIMEDOUT` and `EOPNOTSUPP` from the WSA values, and `ECANCELED`, `ENOTSUP` and `ENOSYS`
     only if the C library does (READ, `errnomodule.c`); that MSVC's does is INFERRED.
     Criterion 1 runs in the release dry run on all three systems and decides Windows; a name
     missing there costs one wrong answer in that check, never an import error.
   - **Why this is not a host-specific branch (§4.3; the review, F5).** Spec 032 refused
     `OSError` partly because accepting it "would bring a host-specific mapping into the
     runner". The owner's answer to question 54 replaces that reason: a provider may raise, so
     the runner must read a host's `OSError`. It does so without a branch on the host. There is
     one code path and no `sys.platform` test. The runner names a meaning, never a host's
     number: the table is the host's own `errno` module read by the guest's names, so the same
     name gives the same member everywhere. What does differ by host is the provider's
     behaviour (for example, Windows raises `PermissionError` for `open()` of a folder). That is
     the provider's business, and the README documents it (criterion 9).
   - **Why not `errno.errorcode`.** It holds one name per number. On macOS `errorcode[102]` is
     `EOPNOTSUPP`, which is no member, so the alias would be lost. The table is built the other
     way, from the members' names.

3. **The errno first, then the class, else a fault.** `_raised(e) -> Errno | None` decides:
   1. **Only an `OSError`:** `issubclass(type(e), OSError)`. `type()` cannot be faked; `isinstance`
      would consult a `__class__` property, provider code.
   2. **The errno slot:** read through `OSError.__dict__["errno"].__get__(e, type(e))`, the
      member descriptor of `OSError` itself, so a subclass's `errno` property is never run. A
      value that is exactly an `int` and in `_HOST_ERRNO` gives its member. Only `None` goes on
      to step 3. Any other value (a `bool`, an `int` subclass, a str, a number not in the table)
      goes to step 4, a fault.
   3. **The class, only when the slot is `None`** (the review, F2): the first of six, in this
      order, that `issubclass(type(e), …)`:
      `FileNotFoundError` → `ENOENT`, `FileExistsError` → `EEXIST`, `IsADirectoryError` →
      `EISDIR`, `NotADirectoryError` → `ENOTDIR`, `PermissionError` → `EACCES`, `TimeoutError` →
      `ETIMEDOUT`.
   4. **Otherwise `None`:** a fault, `EIO`, as today. That includes an errno that is present
      but names no member, whatever the class: `FileNotFoundError(errno.EINTR, …)` and
      `TimeoutError(99999, …)` are faults, not `ENOENT` and `ETIMEDOUT`.

   The whole decision runs inside `try`/`except Exception`, answering `None` on any error. **The
   boundary's own reads run no provider code** (EXECUTED, the memo's finding 5 and the review's
   `probe_versions.txt`, on CPython 3.11 to 3.14): it never calls a subclass's `errno` property,
   a `__getattribute__` override or a `__class__` property, never a hostile `int`'s `__eq__` or
   `__hash__`, and never the exception's metaclass (`issubclass(type(e), base)` with a built-in
   `base` asks `type`). On a mapped raise it never calls `str(e)`. Two things outside the
   boundary do run provider code, and are not this rule's: CPython's own `raise` calls a
   metaclass's `__subclasscheck__` once, in the provider's frame, before the boundary sees
   anything (the review, F1, EXECUTED); and an *unmapped* fault's text is `_described`'s
   `str(e)`, as today.
   - **Why the errno wins.** `PermissionError(errno.EPERM, …)` must be `EPERM`, not the class's
     `EACCES`. The owner's words: "its errno is then the guest's answer".
   - **Why the class at all.** These six classes are PEP 3151's names for exactly these errnos.
     Without the fallback, the most common idiom, `raise FileNotFoundError(path)`, would still
     give `EIO`.
   - **Why only when the errno is `None`.** The owner's words are "its errno is then the guest's
     answer (any other exception stays a fault)". An exception that carries an errno has said
     what it means; when that errno is refused (`EINTR`) or unknown, the class must not quietly
     replace it. Decision 4's promise then holds: a refused errno always shows in the record.
     The cost is one rare case: on Windows a `TimeoutError` from `WAIT_TIMEOUT` carries the C
     library's `ETIMEDOUT`, which the host's `errno` module does not name (READ, `PC/errmap.h`;
     INFERRED for the number). It is a fault, with its record, rather than `ETIMEDOUT`.
   - **Why `EACCES` for `PermissionError`.** PEP 3151 maps both `EACCES` and `EPERM` to it.
     `EACCES` is the answer of a permission check, and the one spec 032 and the README use for a
     policy's refusal.
   - **Why an exact `int`.** The protocol already refuses a `bool` for a size (spec 032). An
     `int` subclass can claim any number through `__eq__` and `__hash__`. A provider that means
     an errno passes a plain one.

4. **The closed set stays closed; raising adds no answer.**
   - The image of `_raised` is the 21 members, which a provider can already return. So a raised
     `OSError` gives the guest nothing a returned `Errno` could not.
   - Refused, as before, by having no member: `EINTR` (the guest retries until a limit, EXECUTED),
     `EAGAIN` and `EWOULDBLOCK` (a non-blocking "try again", which is false for a whole-file
     provider; EXECUTED, `BlockingIOError`), `EBADF` and `EFAULT` (the guest's own arguments),
     `ENOTCAPABLE` (wasmtime's own sandbox answer), `EMFILE` (the runner's open-file limit),
     success, and every other number. Each is a fault, `EIO`, with its `FileFault`, whatever the
     exception's class (Decision 3). So an embedder sees in the record that its errno was not
     passed on.
   - `ECANCELED`, `ETIMEDOUT` and `EIO` are also what the runner's own gate answers (cancel,
     deadline, file-call limit). Spec 032 left them to providers; raising them changes nothing:
     only the gate sets `call.ended`, for a returned answer and a raised one alike.

5. **Where it applies: three places, named by place** (the review, F10).
   - The method call itself (`_invoke`), for all eight methods.
   - `iter()` on the iterable a `list` returned, and each `next()`. A generator method's body
     runs there, not at the call (EXECUTED: the memo's model, which maps only at the call, still
     gave a raising generator `EIO` and a fault). The runner cannot tell a generator from any
     other iterator without running its code, so every iterable's `iter()` and `next()` are
     mapped alike. The listing is dropped whole: nothing gathered is
     served or held against the staging bound, as on `EIO` today. The iterator is
     closed, as today.
   - **Nowhere else.** An exception from `read`'s buffer export (`memoryview(answer)`) or from
     reading a `Stat`'s attributes (`kind`, `size`, `mtime_ns`), an `OSError` too, is an answer
     outside the protocol and stays `EIO` and a fault (criterion 2 pins the `Stat` case). A
     listed item's checks (`_listed`) run no provider code, so nothing can raise there. An
     exception from the listing iterator's `close` is swallowed by `_close` and recorded
     nowhere, as today (READ, `mounts.py`, `_close`); this specification does not change that.
   - Shape, for the builder: `_invoke`'s `except Exception as e:` first asks `_raised(e)` and, for
     a member, returns `(0, member)`, the answer; `_list` takes `iter()` and each `next()` into a
     `try` of their own whose `except Exception` asks `_raised` the same way and returns
     `(int(member), None, 0)`. `_stat`, `_read` and `_made` do not change: they already handle an
     `Errno` answer.

6. **The message never reaches the guest, and nothing of a mapped exception is kept.**
   - The guest receives one `i32` from the preview1 call. Its `OSError` text is its own C
     library's `strerror` ("No such file or directory"), never the provider's (EXECUTED, finding
     6). No filename, no message, no class name crosses.
   - A mapped exception leaves nothing in the record: no message, no type, no traceback. **The
     runner holds no reference to it** (the review, F7). With no reference cycle, the exception
     and the provider's frame are freed when the boundary returns (EXECUTED, the memo's finding
     5 and the review's `probe_raw.txt`). A cycle the provider's own frame makes (`err = …;
     raise err`) is freed by the collector, as a fault's is today.
   - An unmapped `OSError` is a fault as today: `_described` keeps its type and first line, at
     most 200 characters, on the host side only.

7. **The record does not change shape.** `FileRecord`, `FileFault` and `RefusedWrite` keep their
   fields. No new `cause` value: a raised refusal is `"refused"`, as a returned one is. Why: the
   answer is the same answer (Decision 1), and a new field or value is a public change spec 049
   would weigh for no information the embedder lacks.

8. **Read-only and writable mounts follow one rule.** A read-only mount calls only `stat`,
   `list` and `read`; its write half is never called (specs 032 and 034), so only those three
   can raise. A writable mount's `write`, `mkdir`, `remove`, `rmdir` and `rename` go through
   `_made`, at open, call, close, sync and the ending's walk; a mapped `OSError` there is a
   refusal at that point, recorded `"refused"` with the member, and the guest's call (or its
   close, or its `fsync`) raises the `OSError` of that member. The walk's own rules (no call while
   the interpreter exits or a Ctrl-C is pending; the file-call limit) do not change.

9. **No interaction with specs 053, 054 or 055, or the tool protocol.**
   - 053: async providers stay out of scope. An `async def` method returns a coroutine, a bad
     answer closed at once; a `raise` in its body never runs.
   - 054: a mount is refused as an import-path server. A guest may still put a mount on its own
     `sys.path`. There, importlib's `FileFinder._fill_cache` catches only `FileNotFoundError`,
     `PermissionError` and `NotADirectoryError` from its listing (READ, CPython 3.15.0
     `Lib/importlib/_bootstrap_external.py:1406-1411`; the review, F8). So a raising `list` was
     an `OSError` out of `import` (`EIO`), and after this change an `ENOENT` reads as a missing
     module. That is a better answer, and no interaction with 054.
   - 055 (not built) uses the same mount table, so it inherits the rule with no change.
   - Tools keep their own exceptions (`ToolError`, `ToolDenied`, faults; spec 031). A tool's
     `OSError` is still a tool fault.

10. **The public API (spec 049).** No line of `tests/public_api.txt` changes. The change widens
    what a provider may do: a provider that followed the old protocol never raised, so it sees no
    difference; only a provider that broke it (by raising an `OSError`) now gets a better answer
    than `EIO`. Spec 049's Decision 8 lets an alpha change anything; after 0.1.0 this would be a
    minor release's addition, since nothing that worked before changes. It is not a security
    change. The docstrings that say "it does not raise" change: `FileProvider`'s and
    `WritableFileProvider`'s second paragraphs, the module docstring of `mounts.py`, and
    `FileFault`'s summary, "One provider call that raised, or answered outside its protocol",
    which becomes "One provider call that raised an exception that is not an answer, or answered
    outside its protocol". And `run`'s docstring (`runner.py`, the sentence "no `Exception` a
    provider, a tool or a gate raises, makes `run` raise: those are recorded in the result")
    becomes "…makes `run` raise: a provider's `OSError` may be its answer (the README's
    *Mounts*), and the rest are recorded in the result" (the review, F6). It is not a summary,
    so no reference line changes for it. The README's reference is regenerated with
    `tests/harness/api.py --write`; only the `FileFault` entry changes.

11. **Checks first, by counts.** Each new check is run against main's `mounts.py` and seen
    failing before the code changes (a guard, against its stand-ins only), and against each
    stand-in it names. No check measures time:
    each counts errnos, provider calls, faults, refusals and live references. The EINTR stand-in
    is bounded by `max_file_calls`, never by a clock.

## Intent

A provider may raise an `OSError` where it would return an `Errno`. The guest gets the member of
the same name, or of the exception's class when it carries no errno at all, exactly as if the
provider had returned it. Anything outside the closed set stays `EIO` and a fault. The guest
never sees the provider's text, and the record keeps nothing of the exception.

## Design

```
src/wasi_python/mounts.py   _errno_table(names) -> dict[int, Errno]      (private)
                            _HOST_ERRNO = _errno_table(vars(errno))     (private, at import)
                            _RAISED = ((FileNotFoundError, Errno.ENOENT), ...)  (private, 6 rows)
                            _ERRNO_SLOT = OSError.__dict__["errno"]      (private)
                            _raised(e) -> Errno | None                   (private; total)
                            _Files._invoke: a member is the answer (0, member)
                            _Files._list: iter()/next() mapped the same way
                            docstrings: the module, FileProvider, WritableFileProvider,
                              FileFault's summary
src/wasi_python/runner.py   run's docstring: one sentence (Decision 10)
tests/checks/test_v1_4_embedding.py    criteria 1 to 3 (three systems, in the dry run)
tests/checks/test_v1_2_hostile_guest.py criterion 4 (the judge's machine)
tests/unit/test_runner_mounts.py       criteria 5 to 7 (raw calls, no guest run)
README.md                   Mounts: the protocol's sentence, "Raising an OSError", the fault
                              sentence, the record's sentences; the reference, regenerated
CHANGELOG.md                0.1.0a6, one entry
```

`_raised` in outline (the builder writes it; this fixes the order and the reads):

```python
def _raised(e: BaseException) -> Errno | None:
    try:
        kind = type(e)
        if not issubclass(kind, OSError):
            return None
        number = _ERRNO_SLOT.__get__(e, kind)        # OSError.__dict__["errno"]
        if number is None:                            # only then the class (F2)
            for base, member in _RAISED:
                if issubclass(kind, base):
                    return member
            return None
        if type(number) is int:
            return _HOST_ERRNO.get(number)            # None: present but unusable, a fault
        return None
    except Exception:
        return None
```

## Scope

In: the above.

Out, each with its reason:
- Any errno outside the 21 members. The set is spec 032's; widening it is its own change.
- A raised `OSError` from an answer object's own code (a buffer export, a `Stat`'s attributes),
  and the listing iterator's `close`, which `_close` swallows: Decision 5.
- A record of raised answers (a counter, a `cause` value): Decision 7.
- Translating a host-folder provider's Windows semantics (for example `open()` of a folder
  raising `PermissionError`, which becomes `EACCES`): the provider's business, documented in the
  README (criterion 9), as spec 056 documented host paths.
- Async providers (spec 053's scope).

## Acceptance criteria

Each check below is new and is written before the code. Each is seen failing first against
main's `mounts.py` where the behaviour is missing, and against each stand-in it names: a
deliberate mutant of the built code. A check that guards a property today's code already has
(criterion 4) is seen failing against its stand-ins only. The landing notes list each check with
what it printed against each.

**The stand-ins.**

| | the mutant |
|---|---|
| S0 | main's `mounts.py`: no mapping |
| S1 | the host's number passed through, `int(e.errno)`, for any `OSError` with an `int` errno |
| S2 | a mapped exception also recorded as a `FileFault` |
| S3 | the class tried before the errno |
| S4 | no class fallback |
| S5 | the member returned from `_invoke` as an errno, `(int(member), None)`, not as the answer |
| S6 | the errno read as an attribute, `e.errno`, not through `OSError`'s slot |
| S7 | `isinstance(number, int)` for the errno, not `type(number) is int` |
| S8 | `isinstance(e, base)` for the class, not `issubclass(type(e), base)` |
| S9 | `_invoke` returns `(n, None)`, an errno and not an answer, where n is the preview1 number of any name in the host's `errno` that preview1 has, not only the members (the review, F9) |
| S10 | the mapping at `_invoke` only (the memo's model), not in `_list`'s iteration |
| S11 | `_invoke` keeps the last exception on the table |
| S12 | the table built by reverse lookup through `errno.errorcode` |
| S13 | the class tried whenever the errno gives no member, not only when it is `None` (the draft's reading; the review, F2) |
| S14 | the mapping also in `_stat`'s and `_read`'s `except`, so an answer object's `OSError` is mapped (the review, F3) |
| S15 | step 1 written `isinstance(e, OSError)`, not `issubclass(type(e), OSError)` |
| S16 | the errno read from `e.args[0]`, not from the slot (the review, F10) |
| S17 | the table reads `names[member.name]`, so a name the host lacks raises (the review, F4) |

**Three systems** (`tests/checks/test_v1_4_embedding.py`, which the release dry run's `verify`
job runs on Linux, macOS and Windows):

1. **`test_a_raised_oserror_is_the_answer_of_its_errno`.** One run, two mounts. At `/r`, a
   provider whose `stat` returns `Errno[name]`; at `/o`, one whose `stat` raises
   `OSError(getattr(errno, name), "<secret>")`, with the host's own number. The guest `os.stat`s
   each of the 21 names under both.
   - Under both, the guest's errno for each name equals `Errno[name].value` (21 of 21).
   - `done.files.faults == ()`, and `calls["stat"] == 42`.
   - The secret text is in neither `stdout`, `stderr` nor `repr(done)`.
   - Fails against: S0 (20 of 21 are 29, and 21 faults); S1 (on macOS and Linux `ENOENT` gives
     2 and `EACCES` 13); S2 (21 faults).
2. **`test_an_oserrors_class_answers_when_its_errno_cannot`.** Each case is one mount whose
   method raises as named. The guest prints the errno it caught, or what it got:

   | raised from | exception | the guest |
   |---|---|---|
   | `stat` | `FileNotFoundError("x")` (errno `None`) | 44 |
   | `stat` | `FileExistsError("x")` | 20 |
   | `stat` | `NotADirectoryError("x")` | 54 |
   | `stat` | `PermissionError("x")` | 2 |
   | `stat` | `TimeoutError("timed out")` | 73 |
   | `stat` | a user subclass of `FileNotFoundError`, errno `None` | 44 |
   | `stat` | `PermissionError(errno.EPERM, "x")` (the errno wins) | 63 |
   | `stat` | `FileNotFoundError(errno.EACCES, "x")` (the errno wins) | 2 |
   | `stat` | `OSError(errno.EOPNOTSUPP, "x")` | 58 |
   | `read` | `IsADirectoryError("x")` | `os.open` succeeds and `os.fstat` says a folder, with one `read` call: as a returned `EISDIR` does |
   | `stat` | a `FileNotFoundError` subclass with errno `errno.ENOENT` whose `__str__` counts its calls | 44; `__str__` called 0 times |
   | `stat` | `FileNotFoundError(errno.EINTR, "x")`: a present errno that names no member | 29 |
   | `stat` | `TimeoutError(99999, "x")`: the same | 29 |
   | `stat` | returns a `Stat` subclass whose `kind` property raises `FileNotFoundError(errno.ENOENT, "x")`: an answer object's own code. `Stat` is a frozen dataclass whose `__init__` sets `kind` with `object.__setattr__`, so the property has a setter that stores nothing the runner reads; without one, building the subclass raises `AttributeError` inside `stat`, a fault under S14 too (the confirmation, R1) | 29 |
   | `stat` | `InterruptedError("x")`, `BlockingIOError("x")`, `ConnectionRefusedError("x")`, `OSError("x")`: no errno, no class of the six | 29 each |

   - Faults: exactly seven, those of the last four rows.
   - Fails against: S0; S2 (the `__str__` row: called once, and a fault); S3
     (`PermissionError(EPERM)` gives 2); S4 (`FileNotFoundError("x")` gives 29); S5 (`os.open` of
     the folder fails with 31); S13 (the `EINTR` row gives 44, the `99999` row 73); S14 (the
     `Stat` row gives 44).
3. **`test_a_write_halfs_raised_oserror_is_a_refusal`.** A writable mount at `/o` whose provider
   raises, with the host's numbers: `write` at a create, `PermissionError(errno.EACCES, …)`;
   `write` at a close, `OSError(errno.ENOSPC, …)`; `mkdir`, `FileExistsError(errno.EEXIST, …)`;
   `rename`, `OSError(errno.EXDEV, …)`; `remove`, `IsADirectoryError("x")`; and `write` in the
   ending's walk (a file the guest leaves open), `OSError(errno.EDQUOT, …)`. A writable mount at
   `/r` whose provider returns the same members at the same points.
   - The guest's errnos are 2, 51, 20, 75 and 31 under both mounts.
   - `done.files.faults == ()`.
   - The two mounts' `RefusedWrite`s are equal but for `mount`: each holds its member and cause
     `"refused"`, and the last has `at == "exit"` and `errno == Errno.EDQUOT`.
   - Fails against: S0 and S5 (29 each, cause `"fault"`, and a fault each).

**The judge's machine** (`tests/checks/test_v1_2_hostile_guest.py`):

4. **`test_an_oserror_that_names_no_member_stays_a_fault`.** Guards the change (S0 passes it).
   Each case is one mount, raising from `read`; the run has `max_file_calls=20`:

   | exception | the guest | provider calls |
   |---|---|---|
   | `InterruptedError(errno.EINTR, "x")` | 29 | 1 |
   | `BlockingIOError(errno.EAGAIN, "x")`; `OSError(errno.EWOULDBLOCK, "x")` | 29 | 1 each |
   | `OSError(errno.EBADF, "x")`; `OSError(errno.EFAULT, "x")`; `OSError(errno.ELOOP, "x")` | 29 | 1 each |
   | `OSError(0, "x")`; `OSError(99999, "x")`; a plain `OSError` with `errno = 2**70` | 29 | 1 each |
   | a plain `OSError` whose `errno` is set to `True` | 29 | 1 |
   | a plain `OSError` whose `errno` is an `int` subclass equal to, and hashing as, `errno.ENOENT` | 29 | 1 |
   | an `OSError` subclass whose `errno` property returns `errno.ENOENT`, its slot `EINTR` | 29 | 1 |
   | an `OSError` subclass whose `__class__` property returns `FileNotFoundError`, errno `None` | 29 | 1 |
   | an `Exception` that is not an `OSError`, whose `__class__` property returns `FileNotFoundError` | 29 | 1 |
   | a plain `OSError("x")` whose `errno` is set to `errno.ENOENT` after construction (mapped: the slot is read) | 44 | 1 |
   | `ValueError("x")` (unchanged) | 29 | 1 |

   - One fault per case but the mapped one, each `_described`'s text, on one line, at most 200
     characters.
   - The `errno` property ran 0 times, and each `__class__` property ran 0 times (each appends
     to a list when it runs). No count covers what the boundary does not do: CPython's own
     `raise` consults a class's metaclass, and `_described` calls `str(e)` for every unmapped
     fault, as today (the review, F1). Criterion 2 counts `__str__` on a mapped raise.
   - Exit 0, `trapped is None`, and `run` raises nothing.
   - Fails against: S6 (the property case gives 44, and its code ran once); S7 (the `True` case
     gives 63, the `int` subclass 44); S8 (the first `__class__` case gives 44, and its code
     ran); S9 (the `EINTR` case: `trapped == "out of file calls"` after 20 provider calls); S15
     (the second `__class__` case: its code ran once); S16 (the set-after case gives 29).

**Raw calls, no guest** (`tests/unit/test_runner_mounts.py`, through `harness.files.Mounted`):

5. **`test_a_generator_listing_that_raises_answers_its_errno`.** A provider whose `list` is a
   generator, on four paths: it raises `FileNotFoundError(errno.ENOENT, …)` before its first
   `yield`; the same after one `yield`; `PermissionError("x")` after one `yield`; `ValueError`
   after one `yield`.
   - The raw `open` with `O_DIRECTORY` answers 44, 44, 2 and 29.
   - Faults: one, the `ValueError`'s.
   - `table.staged` is back to its value before each, and no provider number is held.
   - Fails against: S0 and S10 (the first three give 29, with a fault each).
6. **`test_a_mapped_oserror_leaves_nothing_of_itself`.** A provider whose `stat` holds a local
   object and raises a `FileNotFoundError` subclass with errno `errno.ENOENT` and a secret
   message; the check holds a weak reference to each.
   - The raw `path_filestat` answers 44.
   - After `gc.collect()`, both weak references are dead.
   - `repr(table.record())` holds neither the message nor the class's name.
   - Fails against: S0 (the record holds both); S11 (both references alive).
7. **`test_the_host_errno_table_is_by_name`.** `_errno_table` given:
   - `vars(errno)`: the values are exactly the 21 members, each reached; the keys are each
     member's `getattr(errno, name)`, and `errno.EOPNOTSUPP` too where it differs from
     `errno.ENOTSUP`; `EINTR`, `EAGAIN`, `EBADF` and `EFAULT` are not keys;
   - macOS's numbers (the memo's table): 22 keys, 102 maps to `ENOTSUP`;
   - Linux's (`EOPNOTSUPP` and `ENOTSUP` both 95): 21 keys, 95 maps to `ENOTSUP`;
   - Windows's (READ and INFERRED, as the memo labels them: `EDQUOT` 10069, `ESTALE` 10070,
     `ETIMEDOUT` 10060, `EOPNOTSUPP` 10045, `ENOTSUP` 129): 22 keys, each member reached;
   - a namespace whose `ENOENT` is `True`, or an `int` subclass: `ENOENT` is not reached;
   - `vars(errno)` without `ESTALE`: no error, one key fewer, and `ESTALE` is not reached;
   - a child process (`sys.executable -I -c`) that deletes `errno.ESTALE` and then imports
     `wasi_python`: it exits 0 and prints that `Errno.ESTALE` is not among the table's values.

   Fails against: S0 (no `_errno_table`); S12 (on macOS's numbers, 102 is not a key); S17 (the
   namespace without `ESTALE` raises `KeyError`, and the child exits 1).

**The judge, the docs and the whole:**

8. **No existing check changes.** Every check of specs 032, 034 and 049 passes as it stands,
   among them `test_a_provider_fault_never_escapes`, `test_a_write_half_fault_never_escapes`,
   `test_the_errno_values_are_the_guests` and `test_the_record_keeps_the_first_thousand_faults`
   (its `OSError("x" * 500)` has no errno and a plain class, so it is still a fault). The judge
   changes only by the seven additions.
9. **README.** In *Mounts*:
   - the protocol's sentence says each method answers "a value or an `Errno`, or raises an
     `OSError`";
   - a paragraph, **Raising an OSError**, says: the errno is matched by name, so `errno.ENOENT`
     on any host is `Errno.ENOENT`; with no errno at all, the six classes answer; an errno
     outside the set is `EIO` and a fault, `EINTR` and `EAGAIN` included, whatever the class,
     with the reason; the guest never sees the message; **a mapped raise leaves no fault in the
     record**, so a provider's own bug that raises `FileNotFoundError` reads as the guest's
     missing file, and a provider that wants its raises seen logs them itself (the review, F6);
     a host-folder provider on Windows still answers `EISDIR` for a folder itself, since Windows
     raises `PermissionError` there;
   - the fault sentence reads "Any other exception, or an answer outside the protocol, …";
   - the writable record's `"refused"` reads "(your `Errno`, returned or raised)".

   The docstrings of Decision 10, `run`'s sentence among them, are changed; `uv run python tests/harness/api.py --write`
   regenerates the reference; `--check` passes; `git diff tests/public_api.txt` is empty; the
   reference block's diff touches only `FileFault`.
10. **CHANGELOG.** One entry under 0.1.0a6: "**A provider may raise `OSError`** (spec 061). Its
    errno, matched by name (never by number, which differs by host), is the guest's answer, as
    the `Errno` of that name would be. With no errno at all, `FileNotFoundError`,
    `FileExistsError`, `IsADirectoryError`, `NotADirectoryError`, `PermissionError` and
    `TimeoutError` answer `ENOENT`, `EEXIST`, `EISDIR`, `ENOTDIR`, `EACCES` and `ETIMEDOUT`. An
    errno outside the closed set (`EINTR`, `EAGAIN` and the rest), whatever the class, and any
    other exception stay a fault, `EIO`. A mapped raise leaves no fault in the record. The guest never sees the exception's message, and the record keeps nothing
    of it."
11. **The judge is green.** `ruff check` and `ruff format --check` are clean on `src/` and
    `tests/`. The full `uv run pytest` in the worktree, without `--accept`: lost 0, grew 0; v1.4
    gains 3, v1.2 gains 1, the unit suite gains 3. The lane accepts with `--accept-judge` (three
    judging files gain checks). The release dry run before the next tag shows criterion 1 green
    on Windows; until it does, the memo's Windows column stays INFERRED.

## Disposition of the pre-build review

The review: `../reviews/061-a-providers-oserror-carries-its-errno-spec-2026-10-18.md` (written
in `build/reviews-evidence/061-spec/`, with its probes; the lane copies it in). Each finding, with
the lane's ruling where it gave one, and where it went:

- **F1 (medium), criterion 4's "hostile code ran 0 times" cannot pass: fixed.** The metaclass row
  is dropped: CPython's own `raise` calls `__subclasscheck__` once in the provider's frame, and
  no boundary calls it, so the row guarded nothing. Criterion 4 now counts only what the
  boundary must not do and a correct build does not: the `errno` property and the `__class__`
  properties run 0 times. It says no count covers the metaclass or `__str__` for an unmapped
  fault. A mapped raise's `__str__` count of 0 moved to criterion 2, against S2. The review's
  optional row (a non-`OSError` with a `__class__` property) is in, against S15. Decision 3
  says what the boundary's reads do and do not run.
- **F2 (medium), the class overriding a present errno: fixed, the reviewer's reading (a).** The
  class decides only when the slot is `None`; a present errno that names no member is a fault
  whatever the class (Decision 3, steps 3 and 4, and its reason; Decision 4; the outline). The
  Windows `WAIT_TIMEOUT` case becomes a fault with its record, said so. Criterion 2 gains
  `FileNotFoundError(errno.EINTR, "x")` and `TimeoutError(99999, "x")`, 29 each; stand-in S13 is
  the draft's reading (44 and 73). README and CHANGELOG say "with no errno at all" and "whatever
  the class".
- **F3 (medium), the answer-object exclusion unpinned, one sentence wrong: fixed.** Criterion 2
  gains a `Stat` subclass whose `kind` raises `FileNotFoundError(errno.ENOENT)`: 29 and a fault;
  stand-in S14 maps in `_stat`'s and `_read`'s `except` (44). Decision 5 now says `_close`
  swallows an exception from the iterator's `close` and records nothing, as today, and that
  `_listed` runs no provider code.
- **F4 (low), a name the host lacks: fixed.** Decision 2: such a name is skipped
  (`names.get`), and importing `wasi_python` never fails for it. Criterion 7 gains a namespace
  without `ESTALE` and a child process that deletes `errno.ESTALE` and imports `wasi_python`;
  stand-in S17 (`names[member.name]`).
- **F5 (low), §4.3: fixed.** Decision 2 says why the name table is not a host-specific branch,
  and that the owner's answer to question 54 replaces spec 032's reason.
- **F6 (low), the README and `run`'s docstring: fixed.** Criterion 9's paragraph says a mapped
  raise leaves no fault and that a provider that wants its raises seen logs them itself.
  Decision 10 adds `run`'s sentence (`runner.py:334`); it is not a summary, so the reference
  changes only in `FileFault`. The CHANGELOG entry says it too.
- **F7 (low), "no frame outlives the call": fixed.** Decision 6: the runner holds no reference;
  a cycle the provider's own frame makes is freed by the collector, as a fault's is today.
- **F8 (nit), the 054 bullet: fixed.** Decision 9 cites `FileFinder._fill_cache`: a raising
  `list` was an `OSError` out of `import`, and an `ENOENT` now reads as a missing module.
- **F9 (nit), S9 as an errno: fixed.** S9 is "`_invoke` returns `(n, None)`", an errno, so the
  `EINTR` loop happens.
- **F10 (nit), Decision 5's rule by place and the set-after row: fixed.** Decision 5 names the
  three places and why every iterable's `iter()` and `next()` are mapped (a generator cannot be
  told from another iterator without running code). Criterion 4 gains a plain `OSError` whose
  `errno` is set to `ENOENT` after construction, 44; stand-in S16 reads `e.args[0]` (29).

The memo (`../research/2026-10-18-a-providers-oserror-carries-its-errno.md`) is left as written,
as research memos are. Where this section corrects it (F1's metaclass count, F8's importlib
claim, F2's reading of the class), this specification governs.

## Landing notes

Not built.
