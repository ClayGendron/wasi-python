# Review of 014 — The inputs are checked (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the
  constitution (§4, §7), `context/reviews/README.md` and the 013 build review (for its format).
  Then I read specification 014 with its landing notes, and its pre-build review with the
  dispositions and the reviewer's confirmation. Then I read the diff. I did not rely on the
  landing notes. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** the uncommitted working tree on top of `1f21dd0`:
  - `src/wasi_python/runner.py`, `tests/checks/test_v1_4_embedding.py`, `README.md` and
    `CHANGELOG.md` (the diff);
  - the new `tests/unit/test_runner_inputs.py` and the specification.
- **Re-ran (EXECUTED, darwin-arm64, wasmtime-py 49.0.0, the artifacts in `build/artifacts/` read
  only, `WASI_PYTHON_CACHE=build/cwasm-cache`).** Probes, outputs and the mutation log are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev014b/`
  (`probes/*.py` with their `.txt`, `mutate.py`, `mutations.txt`, `logs/`, `pytest-full.txt`,
  `head_new_tests.txt`).
  - `uv run pytest` → `142/144 pass · 0 gap · 2 blocked · 0 fail (unit suite 300/300)`;
    `442 passed, 2 skipped`; v1.4 `47/47`; ratchet `lost 0 · absent 0 · unrun 0 · gained 4 ·
    grew 0 · judge changed: tests/checks/test_v1_4_embedding.py,
    tests/unit/test_runner_inputs.py`; **exit 0**. I did not pass `--accept`; the acceptance with
    `--accept-judge` is the author's.
  - `uv run ruff check src tests` → all checks passed. `uv run ruff format --check src tests` →
    43 files already formatted.
  - One probe (`p4_formats.py`) ran under `uv run --with numpy`, an ephemeral environment.
    `pyproject.toml` and `uv.lock` are untouched.
  - **How I mutated.** I did not edit the tree's runner. Each mutation went into a scratch copy of
    the package (`mut/src/wasi_python/`), put first on `PYTHONPATH`. I checked that
    `wasi_python.runner.__file__` was the scratch copy. The copy was restored from the tree's
    bytes after each mutation and checked by SHA-256.
  - At the end, the tree's `runner.py`, both test files, the README, the CHANGELOG and the spec
    were `cmp`-equal to copies I took first (`orig/`, `orig.sha256`).
  - I did not commit, push, run `scripts/build.sh` or touch `build/artifacts/`. My pytest runs
    rewrote untracked state under `build/progress/` and `build/harness/`. The only tracked-tree
    file I wrote is this review.
  - While I worked, two other tracked files changed in the tree:
    `context/questions-for-the-owner.md` and `context/specifications/013-the-limits-are-checked.md`
    (5 lines each). Another piece of work owns them. Neither touches the runner, and I ignored
    them.

## Decisions against the code

- **Decision 1, check first (READ, EXECUTED).** `run` calls `_check_inputs` right after
  `_check_limits` (`runner.py:240-242`). Both come before `find_artifacts`, `_engine`, `_module`,
  `mkdtemp` and `_place_stdlib` (`runner.py:246-268`).
  - EXECUTED (`p2_run.txt`). I passed 18 refused inputs, each in four forms: no root, a `root=`,
    an `artifacts=` that raises on any attribute, and both. That is 72 calls.
    - For the 17 refused inputs, every call raised `TypeError` or `ValueError`, and every
      message named the argument. The eighteenth is the generator below.
    - `tempfile.tempdir` (pointed at a fresh directory) and the root stayed empty. The
      `cache_dir=` I passed was never created. The artifacts were never touched.
    - A generator `argv` that raises partway passes its own `RuntimeError` through unchanged.
      Nothing is created. That is the caller's own error, so this is right.
- **Decision 2, the rules (READ, EXECUTED, `p1_check.txt`, `p2_run.txt`).**
  - **`str` subclasses.** I tried five: ones that override `__str__`, `encode`, `__eq__` with
    `__hash__`, `__contains__` (to hide a NUL from `in`), and `__iter__`. For each, the checked
    value is a plain `str` holding the real text. A NUL inside is still refused, and a `=` in a key
    still refused. Through `run`, the guest sees `ok`, not `evil`, in an argument and in an env
    value.
  - **An object whose `__class__` lies** passes `isinstance(x, str)`. It then fails in
    `str.__str__` with `TypeError: descriptor '__str__' requires a 'str' object`. That message does
    not name `argv`. It is still a `TypeError` before any work. It is contrived (finding 5).
  - **Keys equal only after `str.__str__`.** Two subclass keys whose `__eq__` and `__hash__` keep
    them apart, both with the text `HOME`, give `{'HOME': '/b'}`: the later wins, silently.
    INFERRED from HEAD's `_instance`: before this change wasmtime got both entries and the guest
    kept the later one too. So nothing got worse (finding 5).
  - **A `Mapping` whose `items()` lies.** The runner reads `env.items()` once. It checks those
    pairs and passes those same pairs on. So there is no gap between what is checked and what is
    sent. An `items()` that yields `HOME` twice keeps the last. HEAD read `keys()` and
    `__getitem__` instead (`{**env}`). Only a mapping that contradicts itself sees a difference.
  - **`argv` iterables.** A tuple, list, generator, `dict_keys`, `dict` and `set` are taken. One
    million items check fine. `str`, `bytes`, `bytearray`, `None` and a `PathLike` item are
    refused. An old-style iterable (only `__getitem__`) is refused, though `list()` and HEAD's
    `[ARGV0, *argv]` take it (finding 5).
  - **`stdin` buffers.**
    - A `bytearray` changed after the check does not change what was checked: the check copied
      it (`b'hello'` stays).
    - `memoryview(x).tobytes()` gives the raw bytes for a C-contiguous buffer of any format:
      `array('i', [1, 258])` reaches the guest as `0100000002010000` (host byte order), and
      `array('d')` and a ctypes structure array come out as their memory. For a non-contiguous
      or Fortran-order buffer, it gives the logical elements in C order: `[::2]` of
      `array('i', [1,2,3,4])` gives the bytes of `[1, 3]`; a Fortran-order numpy array gives
      `tobytes(order="C")`, not its memory order. HEAD raised `BufferError` for both. So this is
      a gain, and it matches numpy's own default.
    - A `bytes` subclass is copied into a plain `bytes`. An exact `bytes` is passed on as the same
      object.
    - A released `memoryview` raises `ValueError: operation forbidden on released memoryview
      object`, which does not name `stdin` (finding 5).
    - A numpy object array is bytes-like, so its raw `PyObject*` pointers reach the guest as
      input (EXECUTED, 16 bytes for two items, `p4_formats.txt`). HEAD did the same. That is
      "anything `memoryview()` accepts", as the specification says (finding 5).
  - **Messages never contain a value (EXECUTED).** I put a marker string in each value and in each
    refused key: NUL, `=`, surrogate, an `int` or `bytes` value, and an `argv` item. None of the
    messages holds it. A refused key is never quoted. A valid key is quoted in its value's
    message, as the specification's example shows. It is not cut short: a 100,000-character
    key gives a 100,036-character message (finding 3).
- **Decision 3, no other change (READ, EXECUTED).**
  - READ: the diff touches neither `BASE_ENV` nor the `wasi.argv` and `wasi.env` lines in
    `_instance`. The only new `HOME` is in a docstring.
  - EXECUTED (`p2_run.txt`): with `env=None` and `env={}`, the guest's environment is exactly
    `HOME`, `PYTHONTZPATH` and `TMPDIR`, with a fresh `/tmp/.home-…`. An `env` that sets `HOME`,
    `TMPDIR` and `PYTHONTZPATH` still overrides all three. Odd but valid keys (`A B`, `KÉ`, `1K`,
    and an empty value) reach the guest exactly.
- **Decision 4, the checks (READ).** Every listed case is there: each table row, `"=K"`, `False`
  and `[]`, a `PathLike`, a lone surrogate in an argument, a key and a value; the accepted forms;
  plain types out; and a message test. The v1.4 check has the four cases, a fresh
  `tempfile.tempdir` and a `root=`. Two gaps follow from the mutations: nothing checks that `run`
  passes the checked values on (finding 1), and the v1.4 check has no `artifacts=` that fails if
  touched (finding 2).
- **Decision 5, the CHANGELOG (READ).** The line is in 0.1.0a2's "`run` changes for existing
  callers" list. One clause is not quite true (finding 4).
- **The pre-build confirmation's three points (READ, EXECUTED).** The plain copy uses
  `str.__str__`, the UTF-8 check uses `str.encode`, and an exact `bytes` is not copied. Each has a
  unit test, and each is killed by its mutation (m14, m15, m10). Item 8's request to cut a quoted
  key short was not taken (finding 3).

## Mutations (EXECUTED, `mutations.txt`, `logs/`)

The tests run were `tests/unit/test_runner_inputs.py`, `test_runner_limits.py`,
`test_runner_calls.py`, `test_runner_waits.py`, `tests/checks/test_v1_4_embedding.py` and
`test_v1_2_hostile_guest.py` (158 tests). The baseline, unmutated, passed 158 of 158. "Caught"
means at least one test failed.

| # | mutation | result |
|---|---|---|
| m01 | NUL check dropped | caught: 5 (3 unit, the 2 NUL v1.4 cases) |
| m02 | UTF-8 check dropped | caught: 4 (3 unit, the v1.4 surrogate case) |
| m03 | `=` check dropped (empty key still refused) | caught: 3 (`= in a key`, `leading =`, the v1.4 case) |
| m04 | empty-key check dropped (`=` still refused) | caught: 1 (`empty key`) |
| m05 | `str`/`bytes`/`bytearray` refusal for `argv` dropped | caught: 1 (`[str]`). The `bytes` and `bytearray` cases pass anyway: their items are `int`, so the item check raises the same `TypeError` |
| m06 | `bytes`/`bytearray` refusal dropped, `str` kept | **survives**. Near-equivalent: every non-empty `bytes` is still a `TypeError` naming `argv[0]`. Only `b""` and `bytearray()` would pass, as an empty `argv` (INFERRED from the code). Info |
| m07 | `Mapping` check dropped | caught: 1 (`a list of pairs`, which then raises `AttributeError`, not `TypeError`) |
| m08 | `Mapping` check dropped, entries read as `{**env}` did | caught: 1 (the same) |
| m09 | `memoryview` conversion dropped (checked, passed as given) | caught: 4 (`bytearray`, `memoryview`, non-contiguous, `array`) |
| m10 | exact-`bytes` pass-through dropped (always `tobytes()`) | caught: 1 (`test_exact_bytes_stdin_is_not_copied`) |
| m11 | **`run` checks but does not pass on the plain values** | **survives** (finding 1) |
| m12 | **`_check_inputs` moved after `find_artifacts` and the compile** | **survives** (finding 2) |
| m13 | `run` without `_check_inputs` | caught: the 4 v1.4 cases |
| m14 | plain copy made with `str(x)` | caught: 2 (the plain-`str` tests) |
| m15 | no plain copy (`text = value`) | caught: 2 (the same) |
| m16 | **an illegal key quoted in its message** | **survives** (finding 3) |
| m17 | the NUL message quotes the value | caught: 1 (`NUL in a value`) |

What m11 lets through, EXECUTED (`p3_passthrough.txt`, a scratch copy with only the
pass-through line removed):
- `argv=(a for a in ["-c", SHOW, "g"])`: the check uses up the generator. The guest then gets
  no arguments, runs its prompt on empty input, and returns **exit 0 with empty output**. The tree
  prints `['g']`.
- A `str` subclass whose `encode` lies, in `argv` or as an env value: the guest sees `evil`. The
  tree gives `ok`.
- A non-contiguous `memoryview` as `stdin`: `BufferError`, late, from the temporary file. The tree
  gives `b'hi'`.

## Acceptance criteria against evidence

1. *The unit tests and the v1.4 check exist and were seen failing before the change.* **Met.**
   EXECUTED (`head_new_tests.txt`): HEAD's `runner.py`, in a scratch copy of the package, gave
   49 failed. That is 45 unit tests (no `_check_inputs`) and the 4 v1.4 cases. Three of those say
   `DID NOT RAISE ValueError`: the guest ran. The surrogate case failed on the root holding `usr`
   and `tmp`: the root was prepared before the late `UnicodeEncodeError`. This matches the landing
   notes exactly.
2. *`uv run pytest` is green with `--accept-judge`.* **Met, pending the acceptance run.**
   EXECUTED: exit 0, `lost 0 · absent 0 · gained 4`, and the judge changed in the two named files.
3. *A dry run of the release workflow passes every job.* **Not shown.** Nothing is pushed.

## Findings, most severe first

1. **Nothing checks that `run` passes the checked values on. Without that, a generator `argv`
   runs the wrong program and says nothing** (`runner.py:242`). Medium-low.
   - This is spec 013's build finding 1 again, for the inputs.
   - EXECUTED (m11, `p3_passthrough.txt`): with the line
     `argv, env, stdin = checked["argv"], checked["env"], checked["stdin"]` removed, all 158
     tests pass. Then a generator `argv` gives exit 0 with empty output, because the check used
     it up. A `str` subclass reaches wasmtime-py, whose `encode` call the subclass controls. A
     non-contiguous `memoryview` fails late with `BufferError`.
   - The specification's Decision 2 accepts a generator *because* it is "consumed once". Only
     the pass-through makes that true.
   - All the "passed on" tests call `_check_inputs`, never `run`.
   - **Fix (counts only).** Add a v1.4 case that calls `run` with
     `argv=(a for a in ["-c", "import os, sys; print(sys.argv[1:], os.environ['K'], sys.stdin.read())", "a"])`,
     `env={Sneaky("K"): Sneaky("v")}` (a subclass whose `__str__` and `encode` lie) and
     `stdin=memoryview(b"h_i_")[::2]`. Assert the stdout is `['a'] v hi`. m11 then fails it.
2. **"Before any work" is not checked against the artifacts or the compile**
   (`tests/checks/test_v1_4_embedding.py`, the new check). Low.
   - Spec 013's build review found the same gap (its finding 2). Its fix gave the limits check an
     `artifacts=` object that fails if touched (`test_v1_4_embedding.py:568-575`). The new check
     copies the pattern but leaves that form out.
   - EXECUTED: m12 moves `_check_inputs` after `find_artifacts`, `_engine` and `_module`. All 158
     tests pass. The check counts directory entries only, and a compile writes elsewhere.
   - INFERRED from `run`: under m12, a bad input on a machine without artifacts raises
     `ArtifactsMissing`, not `ValueError`. On a cold cache, a refused call compiles first.
   - **Fix.** Add `{"artifacts": Untouched()}` to the forms the check loops over, as spec 013's
     check does. My `p2_run.py` does this, and the current build passes it.
3. **The key quoted in a value's message is not cut short, and the "a key is never quoted"
   choice has no test** (`runner.py:150-151`). Low.
   - The pre-build confirmation (item 8) asked: "show it with `repr` and cut it to a few dozen
     characters, so that a huge key does not fill a log". EXECUTED: a valid 100,000-character
     key with a NUL value gives a 100,036-character message.
   - The landing notes add a choice: an illegal key is never quoted, "since a malformed key such
     as `TOKEN=abc` can carry a secret". The code does that (EXECUTED). But m16, which quotes
     the illegal key, passes every test. The message test puts its secret only in the value.
   - **Fix.** Cut a quoted key, for example `{name[:40]!r}` plus `…` when longer. Add a case
     whose secret is inside a refused key, such as `{"TOKEN=" + SECRET: "v"}`, and assert the
     secret is not in the message.
4. **The docs say slightly less, and in one place slightly other, than the code does**
   (`CHANGELOG.md`, `README.md`, `runner.py:203-208`). Low.
   - CHANGELOG: "a `str`, `0`, `False` or `[]` is now a `TypeError`, where it meant empty
     input". Only the empty `str` meant empty input. A non-empty `str`, such as `"hi"`, was
     already a `TypeError` from `memoryview`, naming nothing (the specification's own table,
     EXECUTED by its author and the pre-build review). §4.10 asks a claim to be true as stated.
     Suggested: "`""`, `0`, `False` or `[]` meant empty input and a non-empty `str` failed late;
     each is now a `TypeError`".
   - README: the new clause reads "raises `TypeError` or `ValueError` before any work, so no
     value can quietly remove a limit, and so are an `argv`, `env` or `stdin` …". "So are" has no
     verb to match. It also sits inside the **defaults** bullet, which is about limits. A
     separate bullet would read better.
   - README: nothing says what types `env` and `stdin` take. The README lists `env` and `stdin`
     among `run`'s parameters (line 221) but not that `env` must be a `Mapping` of `str`, that
     `stdin` must be bytes-like (`str` refused), or that `argv` may be any iterable but not a
     `str`. The CHANGELOG says it; the README should too, in a few words.
   - `run`'s signature still says `argv: list[str]` and `stdin: bytes | None`. The contract is
     wider: any iterable of `str`, any bytes-like object. A type checker will flag a tuple
     `argv`, which the specification calls normal. The docstring does not mention the refusal.
     These are nits.
5. **Odd inputs that are refused, or passed, with an imperfect message. None creates anything or
   reaches the guest wrongly.** Info. EXECUTED (`p1_check.txt`, `p4_formats.txt`).
   - A released `memoryview` as `stdin` raises `ValueError` without naming `stdin`.
   - An object with a lying `__class__` raises `TypeError` from `str.__str__`, without naming
     `argv`.
   - An old-style iterable (only `__getitem__`) as `argv` is refused, though HEAD took it. The
     CHANGELOG does not name this. It is rare enough to leave as it is.
   - `bytes` or `bytearray` that is empty would pass as an empty `argv` if the explicit refusal
     were removed (m06); today it is refused. No action.
   - Two keys that differ only as subclass objects collapse to the later one. HEAD did the same
     (INFERRED). No action.
   - A numpy object array as `stdin` sends the guest host pointer values. HEAD did the same. It is
     the caller's own buffer and within "anything `memoryview()` accepts". No action, though a
     README word ("its raw bytes") would make it plain.
6. **Housekeeping at landing.** Info. The specification's status line still reads "draft", and
   its landing notes say "build review pending". Spec 013's became "landed" with both reviews
   cited.

## Constitution checks

- **§4.1, zero upstream patches.** Holds. Only the runner, the judge and two docs change.
- **§4.4, two imports; §4.6, the artifact set.** Untouched. The change is host-side only.
- **§4.5, embedder-neutral.** Holds. The rules name no embedder.
- **§4.9, tests count.** Holds. The new checks compare exceptions, types, bytes and directory
  entries. None measures time.
- **§4.10, evidence.** The landing notes reproduce: 49 failed before and 49 pass after
  (EXECUTED). One CHANGELOG clause is not true as stated (finding 4).
- **§4.13, tooling.** No new dependency: `collections.abc.Iterable` is stdlib. ruff is clean. The
  buffer test is `memoryview()`, not `collections.abc.Buffer`, which the declared Python floor
  (3.11) lacks.
- **§5.2, no open questions.** The specification decides each rule.
- **§7, never-do list.** Nothing tripped. The judge changed in two files, so acceptance needs
  `--accept-judge`.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **Finding 1 — fixed.** A new v1.4 check, `test_the_guest_gets_exactly_the_checked_inputs`,
   passes a generator `argv`, an env key and value of a lying `str` subclass, and a
   non-contiguous `memoryview` as stdin through `run`, and requires the guest to print the real
   text. EXECUTED: with the pass-through line removed (m11), it fails.
2. **Finding 2 — fixed.** The refusal check also passes an `artifacts=` object that fails if
   touched (m12).
3. **Finding 3 — fixed.**
   - A valid key quoted in a value's message is cut to 40 characters.
   - A unit test requires that a refused key's message never holds its text (m16), and that a
     100,000-character key gives a short message.
4. **Finding 4 — fixed.**
   - The CHANGELOG now says only `""`, `0`, `False` and `[]` meant empty input, and that any
     other `str` already raised.
   - The README has its own **inputs** bullet with the accepted types, and the limits bullet is
     restored.
   - `run`'s signature says `argv: Iterable[str]` and `stdin: bytes | bytearray | memoryview |
     None`.
5. **Finding 5 — noted.** None of the odd inputs creates anything or reaches the guest wrongly.
   An old-style `__getitem__` iterable is now refused as `argv`; the CHANGELOG's "a `str` as
   `argv`" line covers refusals of the wrong type.
6. **Finding 6 — fixed at landing.** The status is "landed".

## Reviewer's confirmation, 2026-10-17

I checked the uncommitted fixes in the working tree: the runner, both test files, the README, the
CHANGELOG and spec 014. Logs are in the same scratch folder: `pytest-full2.txt`,
`mutations2.txt`, `logs/` (the first run's logs are kept in `logs1/`), `orig2/` and
`partial_passthrough.txt`.

**Re-ran (EXECUTED).**
- `uv run pytest`, without `--accept`: `143/145 pass · 0 fail · 2 blocked` (unit suite 301/301);
  v1.4 `48/48`; `444 passed, 2 skipped`. Ratchet: `lost 0 · absent 0 · unrun 0 · gained 5 ·
  grew 0`. The judge changed in the same two files. Exit 0.
- `ruff check` and `ruff format --check` are clean (43 files).
- Mutations, in a scratch copy of the package as before. The baseline passed 160 of 160.
  - m11 (no pass-through) fails `test_the_guest_gets_exactly_the_checked_inputs`.
  - m12 (check after `find_artifacts` and the compile) fails the 4 refusal cases, on
    `the artifacts were used before the check (snapshot)`.
  - m13 (no `_check_inputs`) fails those 4 and the new check.
  - m16 (refused key quoted) fails `test_a_refused_key_is_never_quoted_and_a_long_key_is_cut`.
  - A new mutation, the key cut dropped (`shown = name`), fails the same test.
- Afterwards the tree's runner, both test files, the README, the CHANGELOG and the spec were
  `cmp`-equal to the copies I took before mutating (`orig2/`).

**Each item.**
1. **Finding 1 — confirmed.** The new check sends a generator `argv`, a lying `str` subclass as an
   argument, an env key and an env value, and a non-contiguous `memoryview` through `run`. It
   requires `b"['arg'] val hi\n"`. m11 fails it, on `BufferError`. I also dropped the pass-through
   for `argv` alone, then for `env` alone (EXECUTED, `partial_passthrough.txt`). Each fails the
   check: the first with `NameError` (the generator was used up), the second with `KeyError: 'K'`
   (the guest got `evil`).
2. **Finding 2 — confirmed.** The refusal check loops over `{}`, `root=` and an `Untouched`
   `artifacts=`, as spec 013's does. m12 now fails it.
3. **Finding 3 — confirmed.**
   - READ: a quoted key is cut to 40 characters plus `…` (`runner.py:151-152`).
   - The new unit test refuses `{"TOKEN=" + SECRET: "v"}` without the secret in the message. It
     also requires a message under 100 characters for a 100,000-character key. m16 and the
     dropped cut both fail it.
4. **Finding 4 — confirmed.**
   - The CHANGELOG now says `""`, `0`, `False` and `[]` meant empty input, and that any other
     `str` already raised. That is true (the specification's table).
   - The README has its own **inputs** bullet: the three types, `ValueError` and `TypeError`
     before any work, and no value quoted. The limits bullet reads as before 014. The grammar
     slip is gone.
   - `run`'s signature says `argv: Iterable[str]` and `stdin: bytes | bytearray | memoryview |
     None`. The stdin type is still narrower than the contract, since `array` and numpy buffers
     are accepted too. The README's "a bytes-like object" states the contract. This is a nit and
     does not block.
5. **Finding 5 — confirmed as noted.** These were info items with no fix asked. The CHANGELOG
   does not name the old-style `__getitem__` iterable. That case is rare, and the error is a
   `TypeError` naming `argv`, raised before any work.
6. **Finding 6 — confirmed.** The spec's status reads "landed" and cites both reviews. Its
   landing notes list the review's fixes.

**Verdict (confirmation).** All six dispositions are confirmed. It lands once the acceptance run
(`--accept-judge`) is recorded. Criterion 3, a dry run of the release workflow, is still to be
shown.

## Verdict

Does not land yet. The checking itself is right. Every refused input I tried gives the
specified error, names the argument, quotes no value, and creates nothing. Every accepted input
reaches the guest exactly. `BASE_ENV` and `HOME` are unchanged. But the line that hands the
checked values to the guest can be removed with the judge still green (finding 1). Without it, a
generator `argv` silently runs the wrong program. Add that check, and preferably the ones in
findings 2 and 3, and fix the CHANGELOG clause (finding 4). Then it lands once the acceptance run
is recorded.

One line: `run` now refuses any input the guest would see differently, before any work, but the
judge does not yet notice if `run` stops passing on the values it checked.
