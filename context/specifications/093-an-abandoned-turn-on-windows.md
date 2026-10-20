# 093 — An abandoned turn on Windows

- **Status:** **built 2026-10-19** (tip `e58c07c`, release run 39357013719 green) on `spec/093-an-abandoned-turn-on-windows` from main `97be88a`
  (spec 078 accepted). It fixes the one red line of 078's dry run under the owner's "fix forward"
  rule. Wave 01 landed without it; it enters wave 02, after 073 (the build review's L1). Its build
  review says it lands (`../reviews/093-an-abandoned-turn-on-windows-build-2026-10-20.md`). A judge-only specification, so its pre-build review is optional
  (AGENTS rule 8); a different agent reviews the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, not build-class (§5.7). Files: one check's child program and its
  expected lines in `tests/checks/test_v1_2_hostile_guest.py`, `CHANGELOG.md`, this specification
  and its evidence (`../research/2026-10-19-the-runners-own-stack/093-evidence/`). No line of
  `src/` changes; the artifact set does not change. It is a **judge change**: the lane accepts it
  with `--accept-judge`.
- **Depends on:** 078 (landed; its criterion 17, the session row, and Decision 14).
- **Research it stands on:** 078's research and its build evidence
  (`../research/2026-10-19-the-runners-own-stack.md`); the dry run's failed log (job
  `judge (windows-2025, own-guest)`, run 39351481374); this specification's own evidence
  (`../research/2026-10-19-the-runners-own-stack/093-evidence/`, EXECUTED on darwin-arm64).

## The problem

### The failure

The release workflow's dry run 39351481374, job `judge (windows-2025, own-guest)`, failed one
check, `tests/checks/test_v1_2_hostile_guest.py::test_an_abandoned_turn_keeps_its_session_busy`.
It passes on macOS and Linux. Its child program, `ABANDONED_TURN_CHILD`, prints seven lines. On
Windows the third and fourth differed:

| line | expected | Windows |
|---|---|---|
| 3 | `busy while its guest runs True` | `busy while its guest runs False` |
| 4 | `second turn refused a turn is already running in this session` | `second turn refused the session has ended: error` |

The other five matched: the turn raised `SystemExit`, the session then ended `error`, no store
was closed under running wasm, and the next session worked.

### The cause

The check assumed a timing that spec 078 does not promise. The runner is right.

- **The guest is stopped on purpose.** The child forces the turn's home out: its stand-in `serve`
  raises `KeyboardInterrupt`, which `_on_guest_thread` keeps with `home.stop`, and its stand-in
  join raises `SystemExit`. `_session_turn` then sees `home.done` false and calls
  `home.finish(_abandon_turn)`, which marks the home abandoned and stops it again. "Abandoned
  always means stopped" (078, Decision 14). A stopped guest ends soon: at its next epoch check
  (every 50 ms, `CANCEL_TICKS` ticks), or before its wasm starts.
- **Its end runs the teardown.** The guest body, at its end, runs the abandoned home's steps on
  the guest thread: `_abandon_turn` clears `busy` and ends the session `error`. That is 078's
  promise: `busy` is cleared only after the turn's guest thread has ended, or by that thread's
  abandoned teardown.
- **The child raced it.** The child read `busy` a few lines after `s.run` raised. That is a race
  between the caller's next lines and the guest's next epoch check. On macOS and Linux the caller
  won. On Windows the guest won, so `busy` was already false and the session already ended. Why
  Windows' order differs (its scheduling, its timers) was not measured; it does not matter,
  because neither order is promised.
- **Reproduced on macOS.** The old child, with the caller made to join the guest before it looks,
  prints exactly the Windows lines (`rows-runner.log`, row "old, guest ends first").
- **Why it is not a runner bug.** The Windows lines are also what a broken runner would print: a
  home whose `finish` tears down at once, with the guest still running, prints them too
  (`rows-mutant-home-tears-down-at-once.log`, row "old as is"). So the old check could not tell a
  correct runner from that bug. But `finish`'s choice is plain Python under the home's lock, on
  the `done` flag the guest body sets only after its turn has returned; nothing in it differs on
  Windows. The new check tells the two apart, and it runs on Windows in the release, so the
  release run confirms it there (criterion 3).

## Intent

The session row of 078's criterion 17 passes on every platform for the reason it names: `busy`
is held while the turn's guest thread lives. It must not depend on which thread runs first.
The runner keeps its behaviour; the check stops racing it.

## Decisions

1. **A check fix, not a runner fix.** The runner keeps 078's promise on every platform (the
   cause, above). Changing the runner to keep a stopped guest alive longer would be wrong.
2. **Order by events, never by time.** The child holds the guest with a `threading.Event` and
   waits for the guest's entry with another. No sleep. The 60 s bound on each wait is a
   backstop so a broken runner fails instead of hanging; it never decides a verdict.
3. **The check names its path.** It asserts the teardown ran on the guest thread, so the
   abandoned path is the one tested, on every platform, and a home that tears down at once
   (the bug the old lines could not tell from a fast guest) fails.
4. **Same node id, every old assertion kept.** The ratchet sees one changed check, not a lost
   and a gained one.

## Design

The check holds the guest thread instead of racing it. One idea: make the order certain, not
likely.

- The child's stand-in `_drive_turn` (already there, to count wasm) waits on a gate, a
  `threading.Event`, at the end of the abandoned turn: after the real turn returns, before it
  counts itself out of wasm. So a store closed meanwhile is still recorded as closed under wasm.
- The caller waits for the guest to have entered that turn (another event, not a time), then
  reads `busy` and whether the held guest thread is alive, tries the second turn, opens the gate
  and joins the thread.
- A stand-in `_abandon_turn` records the thread it runs on. The expected lines now say the
  teardown ran on `wasi-python-guest`: the abandoned path, on every platform. Before, which path
  ran depended on the same race.
- The two waits are bounded at 60 s only as a backstop, so a broken runner fails the check
  instead of hanging it. No sleep is added. The check counts what happened, never how long.

The expected lines change in two places: line 3 gains the thread's liveness
(`busy while its guest runs True True`), and line 5 gains where the teardown ran
(`then busy False ended error torn down on ['wasi-python-guest']`).

## Scope

- **In:** `ABANDONED_TURN_CHILD` and the expected lines and docstring of
  `test_an_abandoned_turn_keeps_its_session_busy`; `CHANGELOG.md`; the evidence folder.
- **Out:** `src/` (no runner change); 078's other child rows (`test_the_home_waits_for_its_guest_thread`,
  the start row, the hand-off rows), which assert no such order and passed on Windows; why
  Windows' guest ends first, which no check depends on.

## Acceptance criteria

1. **The new check is certain.** On the runner at `97be88a`, on darwin-arm64, the new child prints
   the expected lines as is and with the caller made to look only after the guest's turn has
   returned: six runs of each, all twelve identical (`rows.py` rows "new as is" and "new, guest
   ends first"; `rows-runner.log`, `rows-runner-six-times.log`). The second row is as near the
   Windows order as the gate allows: the real turn has returned, but the guest thread is held
   before its end, so nothing is torn down yet. It shows the check does not depend on how far the
   turn got. The true Windows order is the old child's row "old, guest ends first" (the build
   review, L2).
2. **Seen failing first.** Against two mutants of the runner, the new check fails in both orders
   (`rows.py`, run with the runner edited and then restored):
   - `_session_turn`'s `if not home.done:` made false (the turn frees `busy` while its guest runs):
     `busy while its guest runs False True`, the second turn told the session ended, and
     `closes while wasm ran ['MainThread']` (`rows-mutant-turn-frees-busy.log`);
   - `_Home.finish`'s `if not self.done:` made false (the home tears down at once):
     `busy while its guest runs False True` and `torn down on ['MainThread']`
     (`rows-mutant-home-tears-down-at-once.log`). Under this mutant the old check prints exactly
     the Windows lines, so it could not catch it.
3. **Windows.** The release workflow on this branch: `judge (windows-2025, own-guest)` passes, and
   every red line is a GREW line or G7 (the landing notes give the run).
4. **The fast tier and the linters.** `uv run pytest -m "not slow" -n 3` on the branch: lost 0,
   0 fail; `ruff check` and `ruff format --check` green on `src/` and `tests/`.

## How to run the evidence

From the repository root, with an artifact set (`WASI_PYTHON_ARTIFACTS` set, or `build/artifacts`):

```
E=context/research/2026-10-19-the-runners-own-stack/093-evidence
uv run python $E/rows.py tests "$(cat $E/old_child.txt)" 0
```

The last argument is the first row to run: 0 runs the old child's two rows and the new child's
two; 2 runs only the new child's. `old_child.txt` is 078's child program as landed.

## For the lane

**What this claims**, each for the build review to check:

- No line of `src/` changes. The diff is one check's child program and expected lines, its
  docstring, `CHANGELOG.md`, this specification and its evidence folder.
- The check keeps its node id and every assertion it had: `busy` held, the second turn refused,
  the session ends `error`, no store closed under wasm, the next session works. It adds two: the
  guest thread is alive when `busy` is read, and the teardown runs on the guest thread.
- The check adds no sleep and no wall-clock assertion; its two event waits are backstops.
- The record: lost 0, gained 0, `judge changed`; no fuel moves (the check measures none).

**The flags**, each pasted as is:

```
--accept "093: the abandoned-turn check holds its guest thread on a gate instead of racing it, so it passes on Windows; no runner change"
--accept-judge "093: test_an_abandoned_turn_keeps_its_session_busy holds the guest thread at the end of its abandoned turn until the caller has looked, and asserts the guest is alive then and that the teardown ran on wasi-python-guest; the Windows release run saw the guest end first; no src change"
```

If the lane's run has a growth line, it is the base's, not this change's: name it with
`--accept-growth` in the base's words, or answer it in the landing notes.

## Landing notes

- **Built** on `spec/093-an-abandoned-turn-on-windows` from main `97be88a`: `bac6899` (the
  check, the CHANGELOG line, this specification, the evidence) and `e58c07c` (this
  specification's header and sections, which the first release run's rule check caught).
- **The release run on `e58c07c`:** 39357013719, every job green on all three systems; no red
  line, so no GREW line and no G7. `judge (windows-2025, own-guest)`: 413 passed, 0 failed
  (078's dry run: 1 failed, 412 passed); ratchet lost 0, gained 1 (this check), grew 0,
  `judge changed: tests/checks/test_v1_2_hostile_guest.py`.
- **The first release run, on `bac6899`:** 39354545205. `judge (windows-2025, own-guest)` passed
  there too. Two shards (`own-rest` on ubuntu and macos) failed one check,
  `test_specifications_have_their_header_and_sections`, on this specification's shape, fixed in
  `e58c07c`. `rebuild from the pins (ubuntu-24.04-arm)` failed downloading a pinned input
  (`curl: (56) Recv failure: Connection reset by peer`), a network failure, and passed in the
  second run.
- **The fast tier**, `uv run pytest -m "not slow" -n 3` on `bac6899` against the main tree's set
  as it stood at `97be88a`: 519/656 pass, 0 fail; lost 0, grew 0, gained 0,
  `judge changed: tests/checks/test_v1_2_hostile_guest.py`. On `e58c07c` the rule checks alone
  (`tests/checks/test_rules.py`, 42 passed); a fast tier there was spoiled twice by the main tree's
  artifact set being rebuilt mid-run, the second time from recipes not on this branch (a
  `regex-2026.9.29` patch), so its one failure (`test_manifest_recipes_match_the_tree`) and two
  byte growths are that set's, not this change's. The release run is the judge of record.
