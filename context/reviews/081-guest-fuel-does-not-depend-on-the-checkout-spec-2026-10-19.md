# Pre-build review of 081 — guest fuel does not depend on where the repository is checked out, 2026-10-19

- **Reviewer:** a fresh agent. I wrote none of 081. Its starting point is N2 of my 075 build
  review.
- **Under review:** `context/specifications/081-guest-fuel-does-not-depend-on-the-checkout.md` on
  `spec/081-guest-fuel-does-not-depend-on-the-checkout`, commit `b603055` over main `8f8de73`, with
  its evidence in `context/research/2026-10-19-guest-fuel-and-the-checkout-path/`.
- **Read:**
  - the spec in full, and the evidence: `prototype.diff`, `compare.out`, `compare.py`,
    `guard_only.out`, `fixed.out`, `mutant_outside.out`, `lxml.sh`;
  - in the code: `tests/harness/guest.py` (`run`, `_random_stream`, `clock_time_get`),
    `tests/checks/test_v1_3_lxml.py` (the check and `SAFETY`), `tests/checks/conftest.py`,
    `tests/harness/upstream.py` (`_run`, `group_spec`), the ratchet in
    `tests/harness/scoreboard.py`, and `context/progress/accepted.json`;
  - spec 063's diff of the lxml check (`spec/063-the-release-judges-in-parallel-shards`, `d538a4c`).
- **How I ran things:** a `git clone -b` of the branch into the scratch folder (`c081/`), and an
  export of it with `prototype.diff` applied (`p081/`, a root of 128 characters). Each was
  `uv sync`ed. Runs used `build/sets/s-c50ca51fae5eb55b`, read only. I touched no project git
  tree. My probes are in `probes/`, and their logs in `logs/`, beside this file.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED** (reasoned, not run).

## Short version

The diagnosis is right, and so is the fix.

- **One check moves with the checkout's path,** through the host path it hands its guest. I
  reproduced the restated fuel exactly at a third path length (128 characters), and the mutant
  still bites there.
- **The split keeps the security property.** The secret is still unreadable by its host path,
  checked by the same document, the same parser and the same grants.
- **The guard is the right shape,** and every direct caller of the driver passes it.

Three things to write in before building:

- **F1. The "multiples of 17" are not run-to-run noise.** They come from the real file
  timestamps that the host hands the guest through `stat` (EXECUTED: pinning a file's mtime in
  the guest removes them). That is a hidden dependency on the time a check runs. It is small
  today, but Decision 4 should name it.
- **F2. The guard's stated holes are incomplete.** It misses a percent-encoded `file:` URI
  (EXECUTED), Windows' escaped backslashes (INFERRED) and anything a `host=` door answers (READ).
  Add the cheap forms, or list them.
- **F3. Spec 063 edits the same check.** The spec should say what the merged check asserts,
  whichever lands second.

## 1. Does the split keep the security property?

**The probe is the same (READ).** The prototype's `OUTSIDE` builds the same document as
`SAFETY`'s `entity()`:
`<!DOCTYPE r [<!ENTITY e SYSTEM 'file://<host path>'>]><r>&e;</r>`. It parses it with the same
`etree.XMLParser(resolve_entities=True)`, under the same grants (`/ro` read-only holding
`secret.txt`, `/rw` writable), and is given the same argument, `str(ro / "secret.txt")`. Moving
the case to its own run changes nothing it depends on. The other cases share no parser state with
it. The positive control, "entity resolved" reading `<r>SECRET\n</r>` through `/ro`, stays in
`SAFETY`, under identical grants.

**It still bites (EXECUTED).** In my patched copy, at a 128-character root:

- **The fix:** the check passes, twice. Both rows give exactly the draft's restated values every
  time: plain 506,200,859 and snapshot 215,014,922 (`logs/latest-proto-1.json`, `-2.json`,
  `logs/proto-run-*.log`). So the fuel is the same at 44, 205 and 128 characters.
- **The mutant (criterion 3):** granting `ro` at its own host path, in `OUTSIDE` only, fails both
  rows with `entity outside grants: ok '<r>SECRET\n</r>', want ok with ('<r/>',)`
  (`logs/mutant_outside.log`). The file was restored afterwards.

**What the split cannot catch (INFERRED).** If `OUTSIDE` were given a made-up path (say
`/nonexistent/secret.txt`), it would pass vacuously. Today that is ruled out only by reading the
check. A positive control in the same run would rule it out mechanically (N1).

## 2. The guard: coverage and holes

**What it covers (READ, and EXECUTED by its unit rows, which pass in `p081`).**
- It looks at the argument list, the environment (`NAME=value`), each `files=` guest path and its
  contents, and each grant's guest path.
- Its roots are the checkout (`paths.REPO`) and pytest's base temp (`getbasetemp()`, per xdist
  worker). Each root is looked for as written, resolved, and in forward slashes.
- `guest_workdir` is under `HARNESS_TMP`, under the checkout, so that is covered.

**Every direct caller of the driver passes it (READ, grep).**
- The `guest` fixture passes `measured=record`.
- The upstream suite's `_run` passes guest paths only: `/upstream/judge/drive.py`,
  `{"TMPDIR": "/tmp", "HOME": "/tmp"}`, the grant `/upstream`. Its `group_spec` files name
  `/upstream/...` paths.
- 071's recursion check uses `own=`, which the guard skips by design. `Turns` records no fuel.
- So `measured=True` as the default breaks no current caller. The prototype's fast tier is green
  (`fast_tier_prototype.out`). The slow tier is criterion 5's full run.

**Forms it misses** (`probes/r3_guard_holes.py`, `logs/r3_guard_holes.log`):

| form of the host path | named? |
|---|---|
| `str(path)`, its `as_posix()`, inside `repr()` in `-c` code, inside `json.dumps` in `-c` code (POSIX) | named (EXECUTED) |
| `path.as_uri()`, when the root has no special characters | named (EXECUTED) |
| **`path.as_uri()`, when the root holds a space or non-ASCII** (`%20`) | **missed** (EXECUTED) |
| **a Windows path inside `repr()` or `json.dumps`** (`C:\\Users\\…`, doubled backslashes) | **missed** (INFERRED: neither the backslash form nor the slash form is a substring) |
| a drive letter in another case (`c:` against `C:`) | missed (INFERRED) |
| **a host path in a `host=` door's answer** | **not looked at** (READ: `host_paths_in` gets argv, env, files and grants only) |
| a host path written by a check into a file in a grant, not through `files=` | not looked at (stated in the spec) |
| a host path outside the checkout and the base temp: the system temp (`/var/folders/…` on macOS, `%TEMP%` on Windows), `$HOME`, the uv cache | missed (EXECUTED for the system temp; stated in the spec) |

None of these occurs in a check today: the draft's measurement found no other path-dependent row.
But the guard is meant to stop the next one, and the ones it misses should be few and named (F2).
A false positive in the safe direction: the match is a substring, so a sibling path that starts
with the root's text (`…/wasi_python-075/x` against the root `…/wasi_python`) is named. That is
harmless.

## 3. The multiples of 17: noise, or a hidden input?

**A hidden input: the host's real file timestamps (EXECUTED).** The driver already answers
`random_get` and `clock_time_get` itself, deterministically (READ: `_random_stream`, a SHA-256
counter, and `clock_time_get`, from a fixed 2026-01-01 start in steps of 1 µs). So I looked for
another host-supplied value. Eight small programs, each run 12 times through `harness.guest.run`
on the snapshot binary, same paths, fresh root each time (`probes/r1_seventeen.py`,
`logs/r1_seventeen.log`):

| program | distinct fuel values |
|---|---|
| pure compute; write and read a file; `stat` size only; `st_ino` into a dict; list the root; sqlite in the root | **1** |
| `time.localtime(os.stat(f).st_mtime)`; `st_mtime_ns` into a dict | **2, 17 apart** |

Then, 16 runs each, 0.37 s apart (`probes/r2_timestamps.py`, `logs/r2_timestamps.log`):

| program | distinct |
|---|---|
| `st_mtime_ns` into a dict | 2 (0, +17) |
| **the same after `os.utime` to a fixed time** | **1** |
| `localtime` of a fixed mtime | **1** |
| just reading `os.stat(f).st_mtime` (the float) | 2 (0, +17) |
| `str(st_mtime_ns)` | 1 |

So the steps come from the real modification times that wasmtime's `fd_filestat_get` and
`path_filestat_get` pass to the guest. These are wall-clock values of files the check or the
guest just wrote, so they differ on every run. Some value-dependent work on them (a float
conversion, a dict probe) costs one more 17-instruction step for some values (INFERRED). Fixing
the time removes the variation. This is a dependency on *when* a check runs, not noise. And it
is not the checkout's path, so the spec is right that 081 need not fix it.

**Does it threaten the ratchet?** Barely, and not today.
- The rule is relative (READ, `scoreboard.py:159`): a row grows when
  `value > accepted × (1 + 1e-4)`.
- The largest step seen is 119, on rows of 40 M instructions or more, at most 4.2 parts in ten
  million.
- **The smallest accepted row is 1,213,059** (`test_unbuffered_output_survives_a_hard_exit
  [snapshot]`), so its tolerance is 121 instructions. That is just above the largest step seen.
  That row did not vary in the draft's runs; it does not read timestamps (INFERRED from its
  absence in `compare.out`).
- So the risk is a future small check that stats files, or one that reads many timestamps,
  adding steps. The cure is the clock's: the driver could answer the `filestat` calls' times
  from its fixed clock. That is a later specification (F1).

## 4. Spec 063 and the merged check

063 changes the same assertion (READ, its diff over `8f8de73`). On `win32`, "entity outside
grants" must be `XMLSyntaxError` with "failed to load" and "Operation not permitted", and
"SECRET" must not be in its value. Elsewhere it stays `ok <r/>`. It also adds `import sys` and a
Windows sentence to the docstring. 081 moves the case into `OUTSIDE`. The edits do not conflict
in meaning, but they touch the same lines, so whichever lands second must merge them by hand.

**The merged check must:**
1. Run `OUTSIDE` with the real host path and `record=False`, and assert its exit code is 0.
2. Run `SAFETY` (measured) with guest paths only, and assert its exit code is 0.
3. Merge the two answers, and assert the keys are disjoint: `OUTSIDE` gives exactly
   `{"entity outside grants"}`, and `SAFETY` does not give it. A future edit must not leave the
   case in both, with one silently overriding the other.
4. For "entity outside grants": on `win32`, `XMLSyntaxError` with "failed to load" and
   "Operation not permitted" (063); elsewhere, `ok` with `<r/>` (046). **On every platform, no
   "SECRET" in the value**, whatever the kind. 063 has that line on `win32` only; it costs
   nothing to make it unconditional, and it is the property itself.
5. Keep the other twelve `expect` lines, and the closing assertion on `ro/out.xml` and
   `rw/out.xml`.
6. Keep both docstrings' sentences (Windows' refusal by name, and the unrecorded run of spec
   081), and `import sys` at the module's top.

A note on fuel: 063's Windows run of this check no longer differs in its measured part, because
the case that refuses differently is now unrecorded. Windows' fuel is not compared with
`accepted.json` anyway (INFERRED: accepted values are darwin-arm64's).

## Findings

### F1. Decision 4 calls the 17-instruction steps run-to-run noise; they are the host's real file timestamps. Low; write in (EXECUTED)

Restate Decision 4 with:
- **the source:** the real `st_mtime` passed through wasmtime's `filestat` calls, with r1 and r2
  as evidence (variation only in programs that use a file's mtime; none once `os.utime` fixes it);
- **the bound:** the largest step seen is 119, against a tolerance of 121 on the smallest accepted
  row (1,213,059), which reads no timestamps;
- **its owner:** a later specification can answer the `filestat` times from the driver's fixed
  clock, as it already answers `clock_time_get`.

The driver's docstring ("repeats to a few parts in ten million") may say why. 081's goal does not
change.

### F2. The guard's holes: add the cheap forms, and list the rest. Low; write in (EXECUTED, READ, INFERRED)

- **Add to the needles:** each root's `as_uri()` (a percent-encoded `file:` URI; missed today
  when the root holds a space, EXECUTED), and each root's escaped form, with `\` doubled (a
  Windows path inside `repr` or JSON, INFERRED). On Windows, also compare case-insensitively.
  Each is one line in `host_paths_in`, and one row in its unit test.
- **List under "What it does not catch":** a `host=` door's answer (READ), and the system temp
  folder by name. Better still: add `tempfile.gettempdir()` as a root whenever it is not literally
  `/tmp` (macOS' `/var/folders/…`, Windows' `%TEMP%`, a CI's `RUNNER_TEMP`), so no guest path
  collides with it.

### F3. Name the merge with spec 063. Low; write in (READ)

Add a line to Depends on, or to Scope: 063 edits the same assertion. Whichever lands second
merges both, and the merged check asserts section 4's six points. Criterion 3's mutant still
applies; on Windows the expectation is 063's.

## Notes

- **N1. A positive control inside `OUTSIDE`** (optional). Also resolve `file:///ro/secret.txt` in
  the same run and expect `SECRET`. Then the unrecorded run shows on its own that the file is
  readable by its guest path and not by its host path. A made-up path in place of the real one
  would then be caught, because the two cases name the same file.
- **N2. Criterion 4's comparison** ("no row differs between the two paths by more than the
  largest difference between two runs at one path") is sound. With F1's timestamp steps, that
  largest difference is up to about 119 instructions.
- **N3. Reproduced** (EXECUTED): the restated values at a third path length, and the mutant's
  failure. The draft's `guard_only.out` shows exactly the two lxml rows refused, naming
  `argv[3]` (READ).
- **N4. Constitution.** A judge change only: no `src/`, recipe, workflow or artifact change.
  Parallel-safe. It needs `--accept-judge`. The two restated rows fall, so no `--accept-growth`
  is needed. §4.9 holds: fuel is counted, not timed.

## Verdict

**Ready once F1, F2 and F3 are written in.** All three are wording, plus a few lines of needles
and their unit rows. The decisions stand. The split keeps the security property, and its mutant
bites. The guard covers every input it names, and breaks no current caller. The restated values
reproduce exactly at a third path.

## One line

The fix is right: the host path goes to an unrecorded run, and the driver refuses it in a
measured one. Name the 17-steps for what they are (the host's file timestamps), close the guard's
cheap holes, and say how the check merges with 063.

## Confirmation (2026-10-19)

The same reviewer read `git diff b603055..2d59bf0` in the -081 worktree: the specification and
one roadmap line. I touched no git tree.

**Each item (READ, with one new probe):**

- **F1: written in.** Decision 4 names the source: the real modification times that wasmtime's
  `fd_filestat_get` and `path_filestat_get` hand the guest. It cites r1 and r2 accurately (only
  programs that use `st_mtime` vary; none once `os.utime` fixes the time). It gives the bound,
  119 against 121 on the smallest accepted row, which reads no timestamps. It names the owner:
  spec 083, reserved in `context/roadmap.md` in words that match. The summary paragraph above the
  decisions no longer says "run-to-run".
- **F2: written in.**
  - Decision 2 adds the forms I asked for: `as_uri()` for an absolute root, every backslash
    doubled for a form that holds one, and case folding on Windows (`fold_case`).
  - It adds the system temp folder as a root unless it is literally `/tmp`. Here it is
    `/var/folders/…/T`, so it is a root on this Mac (EXECUTED).
  - The holes list now names a `host=` door's answer, a file written into a grant, paths outside
    every root (`$HOME`, the uv cache, `/tmp` on Linux) and other encodings.
  - Criterion 4 now also requires that no measured run is refused by the added roots. Criterion
    4a requires each new unit row to fail on the prototype's guard. Both are right: a new root
    that names a current check's input is caught at the build, not discovered later.
- **F3: written in.** Depends on names 063, which lands first, and Decision 5 lists the merged
  check's six points. Point 3 is reshaped correctly for N1's control: `OUTSIDE` answers exactly
  two keys ("entity outside grants" and "entity by guest path, outside run"), and `SAFETY`
  answers neither. The new key's name does not collide with `SAFETY`'s "entity resolved". Point 4
  makes "no `SECRET`" unconditional, as asked.
- **N1: written in, and better than I proposed.** I claimed that a control in the same run would
  catch a made-up host path "because the two cases name the same file". **That was wrong.** The
  control reads `/ro/secret.txt` whatever `argv[1]` holds, so it shows the file is readable by
  its guest path, but it says nothing about the argument. The author saw this and added the
  right check: on the host, before the run, the path handed to `OUTSIDE` reads `SECRET` and is
  the same file as `ro / "secret.txt"`. Criterion 3 gains three mutants: a control naming a
  missing file, a made-up host path, and the case answered in both runs. Each targets one of the
  new assertions.

**Nothing new is wrong.** Two points for the builder, neither a condition:

- **c1. On POSIX, a Windows-shaped root is a relative path** (EXECUTED,
  `logs/r4_windows_shaped_root.log`). `Path(r"C:\Users\runner\work")`:
  - is not absolute on this Mac;
  - `resolve()` places it under the current folder, a harmless extra needle under the checkout;
  - `as_uri()` raises `ValueError: relative paths can't be expressed as file URIs`.

  So "`as_uri()`, for an absolute root" must be an `is_absolute()` test, or the unit row with a
  Windows-shaped root raises inside `host_paths_in` on macOS and Linux. The doubled form is found
  in both `json.dumps` and `repr` text, as Decision 2 says.
- **c2. Assert on the string that is passed.** Make the host-side assertion of Decision 6 test
  the very string handed to `OUTSIDE` (bind it once: `host = str(ro / "secret.txt")`, assert on
  `host`, pass `host`), not a second computation of the path. Otherwise a later edit could change
  one and not the other.

Ordering: Depends on makes 081 wait for 063. If the lane ever lands 081 first instead, Decision
5's six points still describe the merged check completely; only the merge falls to 063.

**Confirmed for build.**
