# Review of 025: nothing writable by default (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change or its
  specification. Spec 025 changes the runner's default before 0.1.0a3, so this review is also
  §5.6's security review for that change. Every claim is labelled EXECUTED, READ or INFERRED.
- **Read:**
  - `AGENTS.md`;
  - the constitution's §4.15 as amended in `f81d4e7`;
  - `context/decisions.md`, question 24;
  - specification 025 with its landing notes;
  - `git show 39a2c84` (nine files);
  - `run`, `run_async`, `_check_root` and `_run_checked` in `src/wasi_python/runner.py`;
  - `src/wasi_python/cli.py`;
  - the README's *Running it*, *Grants*, *From any language*, *sqlite3 in the guest* and
    *Safety*;
  - the CHANGELOG's 0.1.0a3 entry.
- **Reviewed:** commit `39a2c84` on main (not pushed, not accepted).
- **Re-ran (EXECUTED, darwin-arm64, main's `build/artifacts` read only):** scripts and logs are
  in the scratch folder `rev025/` (`default.py`, `cli.py`, `m1`–`m2`, `*.log`).
  `build/progress/latest.json` was copied before the judge and restored byte for byte after
  (SHA-256 `69fbeefe…`). `--accept` was never passed.

## The judge

- **`uv run pytest -p no:cacheprovider -q` (EXECUTED, the full run, with spec 026 on the same
  tree):**
  - scoreboard: `188/190 pass · 0 gap · 2 blocked · 0 fail` (unit suite 468/470, 2 skipped);
  - `656 passed, 4 skipped`;
  - ratchet vs `efa3f1203e`: lost 0, absent 0, gained 2, grew 0;
  - judge changed: `test_v1_2_hostile_guest.py`, `test_v1_4_embedding.py`, `pins.py` and
    three more.

  These match the landing notes.
- **ruff (EXECUTED):** "All checks passed!"; "53 files already formatted".

## The default, tried hard (EXECUTED, `rev025/default.py`, both binaries)

A call with no `root` and no grants, on the snapshot and on the plain reactor alike:

| attempt | answer |
|---|---|
| `os.listdir('/')`, `os.listdir('.')`, `os.listdir('/usr')` | `FileNotFoundError` (errno 44) |
| `os.getcwd()` | `'/'`, which leads nowhere: every relative path fails |
| `open('x','w')`, `open('/x','w')`, `open('/tmp/x','w')` | errno 44 |
| `os.mkdir('/d')`, `os.mkdir('/tmp')` | errno 44 |
| `open('/usr/local/lib/x','w')` | `PermissionError` (errno 63): the zip's grant is read-only |
| `os.listdir('/usr/local/lib')` | `['python315.zip']` only |
| `tempfile.mkstemp()`, `tempfile.TemporaryFile()` | errno 44 |
| `HOME` | absent; `os.path.expanduser('~')` is `'~'` |
| `np.save('/a.npy', …)` | errno 44 |
| `sqlite3` `:memory:` with a 50,000-row sort | works: `(50000, 1249975000)` |

More, all EXECUTED:

- `root=None` gives the same: no `/`, no `HOME`.
- `run_async` with no `root` is refused too (errno 44).
- No `wasi-python-root-*` folder was made by any default call. Only the runner's own
  `stdin` folder is made on the host, and the guest never sees it.
- The guest's only filesystem is the read-only zip, so §4.15's new sentence holds: "no folder,
  no `/tmp`, no `HOME`".

## `root=True` keeps the old private root (EXECUTED)

- It is writable: `/x` written and read back.
- It is `0700`, with its `.lock` beside it while the call runs (watched from the host).
- It is removed after the call, and after a trapped call (`trapped='deadline'`). No
  `wasi-python-root-*` was left.
- READ: `_check_root(True)` returns `None`, the value the runner has always used for a private
  root. So `_run_checked`'s private-root branch is unchanged: the lock and the sweep (spec 016),
  and `tmp` through the walked descriptor (spec 024).

## The command line (EXECUTED, `rev025/cli.py`)

| options | result |
|---|---|
| none | exit 0, `refused 44` |
| `--no-root` | exit 0, `refused 44` |
| `--private-root` | exit 0, `wrote` |
| `--private-root --no-root` | exit 2, "not allowed with" |
| `--private-root --root r` | exit 2, "not allowed with" |
| `--root r --no-root` | exit 2, "not allowed with" |
| `--private-root --private-root` | exit 0, `wrote` (finding 3) |

Nothing was made in the working folder.

## Mutants (EXECUTED, each a `git archive HEAD` copy with one change reverted)

| mutant | change | result |
|---|---|---|
| m1 | `run`'s and `run_async`'s default back to a private root | `test_nothing_is_writable_by_default[snapshot]` and `[plain]` fail |
| m2 | `--private-root` parsed but not passed to `run` | `test_root_reaches_run[args2-True]` fails (`KeyError`) |

## The judge changes keep their subjects (READ)

Each changed check is about the private root itself or its clean-up, so asking for it by name
keeps what it checks:

- `test_a_call_without_a_root_shares_nothing`: a private root is fresh and removed. Its name
  is now older than its subject, which is harmless.
- `test_a_trapped_call_without_a_root_is_removed[*]`: removal after a trap.
- The two child scripts of the stdin and descriptor checks: their guests write `/f`, and the
  subject is that `run` does not raise and the temporary folder is left empty.
- `HELD` in `test_v1_4_embedding.py`: the sweep counts the private root among the folders it
  removes.
- `test_a_bad_grant_is_refused_before_any_work` drops `root=True`'s refusal.
  `test_the_argument_types` now asserts the new mapping.

No check lost an assertion. The new default has its own check, on both binaries.

One path now has no check of its own (INFERRED, not a finding): a *default* call that traps.
Its clean-up is the same `scratch.remove()` that the `root=True` cases run.

## Findings, most severe first

### 1. Criterion 4, the release dry run, is not reported: blocks landing (READ)

The specification's own criterion asks for every job, Windows included. Nothing here is
Windows-specific (INFERRED), but the release workflow's own check of the wheel's command,
added by spec 019, runs a program on every platform. Run the dry run on this commit before
acceptance.

### 2. One README line still describes the old default: low (READ)

*sqlite3 in the guest*, lines 107–108: "a call without `root` never sees a stale lock, since
its root is fresh". A call without `root` now has no root at all. Suggested wording: "a call
with `root=True` never sees a stale lock, since its root is fresh".

### 3. `--private-root` may be given twice, while `--root` may not: informational (EXECUTED)

It is `store_true`, so repeating it is harmless and unambiguous. Spec 022 made `--root` twice
a usage error so that a path is never silently replaced. No path is involved here, so no
change is asked.

## Security review of the change (§5.6)

- **The change only tightens.**
  - It removes a writable folder from the default. It loosens no other default.
  - `root=True` was refused before, so no existing caller changes from "refused" to
    "writable".
  - `root=None` changes from "private root" to "none". That is a narrowing, and the CHANGELOG
    names it.
- **Threat-model rows touched (EXECUTED above):**
  - **Host filesystem:** the default guest has only the read-only zip.
  - **Disk in the root:** the default call has no root, so the 0.1.0a2 review's F2 now applies
    only to `root=True`, a path, or a writable grant.
  - **Planted data and code:** none is possible by default.
  - **Entropy and imports:** numpy, pandas and `sqlite3` `:memory:` work.
- **Unchanged:** grants, the walk and the identity check (spec 024's code is untouched), the
  door, and the limits.
- **Migration text (READ):** the CHANGELOG's **Breaking** line gives the one-line migration
  (`root=True`, or `--private-root`). The README's *Running it* names what fails and the
  remedy. *Grants* gains a worked pattern for state between calls, which the author ran
  (landing notes).

## Constitution checks

- **§4.15:** met as amended (EXECUTED above).
- **§4.9:** the new check counts outputs, not time (READ).
- **§4.10:** the landing notes' numbers match my re-run (EXECUTED).
- **§5.6:** a fresh reviewer. This review also covers the security review this default change
  needs.
- **AGENTS.md rule 4:** the judge changes are stated in the landing notes, and none weakens a
  check's subject (READ, above).

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **Answered, then done.** The dry run needs the push; it runs on the accepted commit and is
   cited in the landing notes.
2. **Fixed.** The README's sqlite item now says a call with `root=True` never sees a stale lock,
   and that with no root a database file can live only in a writable grant.
3. **Answered, no change.** `--private-root` is a flag, not a value: given twice it asks for the
   same thing twice, as `--no-root` and `--no-snapshot` do. `--root`'s once-only rule exists
   because a second value would silently win; a repeated flag cannot change the meaning.


## Verdict

**Land after finding 1, the release dry run of this commit with every job passing.** Fix
finding 2's README line before the tag. Finding 3 needs no change. As a security review of the
new default: the change only tightens, and nothing in it blocks 0.1.0a3.
