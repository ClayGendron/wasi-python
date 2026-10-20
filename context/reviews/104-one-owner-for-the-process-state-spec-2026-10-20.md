# Review of 104 — One owner for the process's state, and the test seams move off module globals

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (pre-build reviewer for the chain 102–107)
- **Reviewed:** the specification as drafted (`context/specifications/104-one-owner-for-the-process-state.md`
  at `5c35061` on `claude/gallant-ride-9nxxmn`; the runner read at the same tree, `src/wasi_python/runner.py`,
  6,241 lines)
- **Run:** none (pre-build review of the draft)
- **Re-ran:** `uv run pytest tests/checks/test_rules.py -k "specifications or open_question" -q
  -p no:cacheprovider` → 3 passed, 41 deselected, exit 0 (the draft has its header and sections and no
  undecided line). `uv run python build/104/rules_proto.py src/wasi_python` → 14 LOCK lines, 40 MUTABLE
  lines, 38 without the two `_fields_`; byte-identical to `build/104/rules_proto.out`. `uv run python
  build/104/lock_order.py src/wasi_python/runner.py` → no `with` inside a `with`; one call under a lock
  (`_zip_lock remove() -> _lock _zip_folder:2294`). `grep -ohE 'monkeypatch\.setattr\(runner,
  *"_[a-zA-Z_]+"' tests/unit/*.py` → 51 lines, 31 distinct names. The spec's criterion-5 grep with
  `--include='*.py'` over `tests/` → 96 lines. `grep -nE '^\s*global ' src/wasi_python/*.py` → 4 lines
  (`runner.py:1426-1428`, `:3441`). A probe of `threading.Lock`, `RLock` and `Condition` under
  `isinstance` and `type(v)()` on the installed 3.11.17, 3.12.3 and 3.13.16 (scratchpad
  `lockprobe.py`, `uv run --python X --no-project`), recorded under finding 2. Time box: 25 minutes
  (parallel-safe), used in full.

## Acceptance criteria against evidence
1. `_process.py` holds every name of Decision 1's table — judged on the draft: the table's left column
   is the 14 locks and 38 mutables the prototype lists (EXECUTED, same output as the writer's), plus the
   ticker's four class attributes (READ, `runner.py:4810-4813`), `__init__.py:151`'s lock and
   `_epoch_callback` (`runner.py:3434`); every name in the prototype's output has a row. The "not
   moved" list matches the source: `_WIN_DEVICES` is a `frozenset(...)` call (`runner.py:2096`), `_BUSY`
   a set display (`:836`), `_EMPTY` an upper-case annotated dict display (`tools.py:948`), the sentinels
   `_UNSET`, `_DONE`, `_WAKE` object calls (READ). The criterion's grep is countable. Met as a design.
2. Both rules checks seen failing first, with counts — the counts 14 and 38 at `a9064a2` are EXECUTED
   by me and agree; "on 103's tip the same 14" is INFERRED by the spec and says so. Countable. Met as a
   design, with one width note under (e) below.
3. The fork check of Decision 3 — expressible as written only on 3.13+; see finding 2. The three
   real-fork checks it names exist (READ: `tests/unit/test_runner_tools.py:488-498` FORK_HOOK,
   `tests/checks/test_v1_4_embedding.py:1433-1437`). The FORK_HOOK program reads
   `runner._tool_threads_lock` and so changes under Decision 4's table (its rows 493, 496), which
   contradicts "stay as they are" (finding 6). Partly met.
4. No `global` statement remains — today four lines (EXECUTED); the three in the fork hook and the one
   in `_watch` (`runner.py:3441`, `_epoch_callback`) are both covered by the table. Countable. Met.
5. Every test line of Decision 4's table changed; the grep finds nothing — 96 lines today (EXECUTED).
   Spot-checked rows (READ): `test_v1_4_sessions.py:163-164` (`_session_clock`, `_reaper["paused"]`),
   `:233, 239` (`_held`); `test_v1_2_hostile_guest.py:2750-2767` (`_on_entry` by hand,
   `_session_clock()`); `test_v1_4_public_api.py:444-449` (`_pool_lock`, `_pool["size"]`);
   `test_runner_sweep.py:343-344` (`_sweep_state` items); `test_runner_async.py:24` (`count`);
   `test_v1_4_embedding.py:1258-1259, 1293, 2284-2298, 1435, 1478`. Each maps to a field or
   attribute. Tests also reach the runner by `from wasi_python.runner import DEFAULTS` and `Completed`
   (EXECUTED grep), both public; no `mock.patch`, `importlib.reload` or string-form `setattr` on a
   private name (EXECUTED grep, none). Met.
6. Sameness against the chain's baseline — stated (Decision 7, `tests/harness/sameness.py`, the
   `v0.1.0a7` set); the claim list names the five new rows. Met as a design.
7. Thread-safety unchanged, the lock-order scan finds one acquisition and no other — not met: the scan
   is blind to two nestings that exist today (finding 1), so the criterion as written would record a
   wrong fact as EXECUTED.
8. The judge green, ruff clean, `--accept-judge` named — countable. Met as a design.
9. One dispatch on the chain's final tip stands for "built" — the memo's section 8 rule (READ). Met.

On the brief's particular points:
- (a) The fork reset against `_after_fork_in_child` (READ, `runner.py:1423-1458`): today's hook renews
  12 locks (`_pool_lock`, `_live_lock`, `_held_lock`, `_stack_size_lock`, `_tool_threads_lock`,
  `_zip_lock`, `_lock`, `_epoch_callback_lock`, `_outputs_lock`, `_sessions_lock`, `_closers_lock`,
  `_epoch_ticker._cond`); the introspective reset renews all 14, so **`warnings_lock` and
  `defaults_lock` are renewed in the child where today they are not** (finding 3). Every other change
  the hook makes has a line in Decision 2 (the stack window, the tool-thread count, the zip table, the
  compiling guards, the pool and live set, the ticker's thread and active count, the sessions, queue,
  closers, dropped, reaper thread and stop, `hooked` kept, `sessions_open`, the fork flag): nothing is
  left out, and nothing else is added.
- (b) The lock order: no deadlock found, but the written order is wrong in two pairs (finding 1).
- (c) The exit release: the eight clears are today's, in today's order (READ, `runner.py:4053-4064`);
  `_sessions_at_exit` registers at the first session (`:5106`) and so runs first, `_stop_async_calls`
  through `threading._register_atexit` (`:757-761`) runs before every `atexit` hook; the stated order
  holds. One write-in on the two registered callables (finding 7).
- (d) Every seam a unit or goal check sets today is a field of `observers` or an attribute of
  `process()`; the `count` overrides become `ticker_count = <value>`, and every production comparison
  is `count() >= stop_at` (EXECUTED grep: `runner.py:3002, 5351`, `mounts.py:852`), so a value past
  the deadline stays past it as the spec says. No check becomes inexpressible.
- (e) On the current tree the two scanners, run over all of `src/wasi_python/*.py` (EXECUTED), hit only
  `runner.py` and `__init__.py:151`; `tools.py`, `mounts.py` and `cli.py` have no hit, and 102's
  `NEEDED` is a tuple (READ, 102 line 152). So nothing outside the chain's reach turns them red. The
  exceptions are narrow (`__all__`, upper-case displays, `_fields_` in a class body); the one width to
  know is that an upper-case display the code later mutates passes the scanner, which is a naming
  convention, not a check. Acceptable, noted.
- (f) `tests/public_api.txt` carries no underscore name (EXECUTED: 0 lines); `stats()` copies the same
  four keys (READ, `runner.py:3978`); `mounts.py`'s three reads are the ones the spec names (READ,
  `mounts.py:723-724, 852`); `tools.py` reaches the runner only through functions (EXECUTED grep). No
  public name, artifact byte or guest-visible behaviour changes.
- (g) Criteria 1-9 are countable; criterion 7's count rests on a defective scan (finding 1).
- (h) Seven header bullets, every required section, no undecided line (EXECUTED, the shape check).
- 103: the header names 103 as the base and the Decision 1 table carries a fallback (the memo's module
  table, labelled INFERRED, "whatever 103 chose, the state leaves that module"); Decision 4's line
  numbers are all at `a9064a2` and the spec says the builder re-finds them by grep. The fallback holds
  for everything the table names. Decision 8's sentence about what 103 does is an expectation of a
  spec not yet drafted (finding 5). 102, 106 and 107 exist; 106 knows of 104 (READ, 106 lines 174-176,
  194) and 107 names 104's rule (READ, 107 line 73).

## Findings, most severe first
1. **The lock order of Decision 6 is wrong in two pairs, and criterion 7's scanner cannot see them**
   (`context/specifications/104-one-owner-for-the-process-state.md`, Decision 6 items 1 and 2;
   `build/104/lock_order.py:9`) — Medium. The scanner's pattern `(_lock|_cond|\.lock)$` is matched
   against an attribute's bare name, which is `lock` for `state.lock`, `home.lock` and `self.lock`, so
   no `with` over a session's or home's lock is seen; and it follows calls one level only. Two nestings
   exist today (READ): `with _stack_size_lock:` at `runner.py:4301` encloses `with home.lock:` at
   `:4306` and `:4315`; and under `_zip_lock` (`:2287`), `_zip_folder_locked` (`:2312`) makes a
   `_Private` (`_held_lock`, `:900`) and calls `remove()`, which calls `_warn_later` (`:952` →
   `_pending_warnings_lock`, `:1367`), then takes `_lock` (`:958`) and `_drop`'s `_held_lock`. So item
   1 should read "under `zip_lock`, `cache_lock`, `held_lock` and `warnings_lock` may be taken, one at
   a time", and item 2 should not call `stack_size_lock` a leaf. No inversion exists (`_stack_size_lock`
   is taken at one place only; `warnings_lock` is a leaf and `_flush_warnings` runs outside every lock),
   so there is no deadlock, but a docstring that says otherwise is a wrong answer in production code,
   and the rule "a new lock is a leaf unless this list is amended" would be enforced against it.
   Failure: criterion 7 is executed with the scanner as written → it reports "one acquisition, no
   other" as EXECUTED, the docstring is landed with two false lines.
   Fix text: the scanner matches `attr in {"lock"} or attr.endswith(("_lock", "_cond"))`, walks calls
   transitively (or two levels, stated), and the Decision 6 list is restated with both pairs; the
   builder's landing notes paste the corrected output.
2. **Decision 2's lock renewal "by type" is not implementable as written on the project's minimum
   Python, and the judge cannot see that** (Decision 2, first bullet; `pyproject.toml:6`
   `requires-python = ">=3.11"`; `.github/workflows/release.yml:31` `UV_PYTHON: "3.14.2"`) — Medium.
   EXECUTED on 3.11.17 and 3.12.3: `isinstance(x, threading.Lock)` and `isinstance(x, threading.RLock)`
   raise `TypeError` (both are factory functions there), and `type(threading.Lock())()` raises "cannot
   create '_thread.lock' instances"; on 3.13.16 only `Lock` became a type, and `RLock` still raises.
   Failure: a builder writes the recipe as drafted, or renews with `type(value)()` → the unit check of
   Decision 3 passes on 3.13/3.14 (the judge's Pythons), and on an embedder's 3.11 or 3.12 the at-fork
   hook raises, which Python reports as unraisable and ignores, so the child keeps every inherited
   lock and the F8 hazard the hook exists for returns silently. Today's hook, a list of constructor
   calls, has no such edge.
   Fix text: Decision 2 names the table `{type(threading.Lock()): threading.Lock,
   type(threading.RLock()): threading.RLock, threading.Condition: threading.Condition,
   queue.SimpleQueue: queue.SimpleQueue}` as the one way a lock is recognised and made anew, in both
   the method and the unit check, and says that the judge runs on 3.13 and 3.14 so the 3.11/3.12 case
   is covered by this text, not by a run.
3. **The reset renews two locks today's hook leaves alone, and the spec says "exactly the same
   changes"** (Decision 2, "The method makes exactly the same changes the hook makes today") — Low.
   `_after_fork_in_child` (`runner.py:1426-1458`) renews twelve locks; `_pending_warnings_lock`
   (`:1085`) and `__init__.py:151`'s `_defaults_lock` are not among them, and the introspective reset
   will renew both. Harmless, and F8's reason applies to them too, but the sentence is false as
   written and the "kept" list says `warned` and `pending_warnings` are kept without saying their lock
   is not.
   Write-in: "The method makes the changes the hook makes today and two more: `warnings_lock` and
   `defaults_lock` are made anew as well, by the same rule (F8), where today's list leaves them."
4. **A plain dataclass does not raise on a misspelt field outside monkeypatch** (Decision 4, "The
   dataclass raises `AttributeError` on a misspelt field") — Low. It is `monkeypatch.setattr`'s own
   `hasattr` check that raises; in a program the judge runs as a subprocess,
   `process().observers.on_entyr = f` on a plain dataclass instance succeeds silently and the seam
   is never set. Write-in: `_Observers` is `@dataclass(slots=True)` (3.10+), so an unknown field
   raises everywhere.
5. **Decision 8 states what 103 does as a fact** (Decision 8, second bullet: 103 "leaves the globals
   in the module their functions moved to, and a fork hook that reassigns them by module attribute")
   — Low. 103 is not in the tree (EXECUTED: `ls context/specifications/` shows 102, 104, 106, 107).
   Decision 1's fallback is sound and labelled INFERRED; this sentence is not. Write-in: "103 is
   expected to leave ... (a requirement this specification places on 103; 103's reviewer checks it)".
6. **Two counts and one sentence disagree with the tree** — Low. (i) "eleven move ... (14 lines)"
   (Decision 4): the eleven names' lines are 2+1+1+1+1+1+1+1+1+1+1 = 12 (EXECUTED), and the twenty
   that stay are 39, which with 12 makes the 51. (ii) Decision 3, "The three existing fork checks that
   fork a real process stay as they are": FORK_HOOK (`tests/unit/test_runner_tools.py:493, 496`)
   reads `runner._tool_threads_lock` and is in Decision 4's own table. Write-in: "12 lines"; "stay,
   with FORK_HOOK's two reads moved to `process().tool_threads_lock` as Decision 4's table says".
7. **The two callables the zip and warnings modules register on the object have no stated default**
   (Decision 2, `release_at_exit`; Decision 1, "every attribute is declared there with a type") — Low.
   `remove_zips` and `flush_warnings` are set by other modules at import; a fresh `_Process()` (the
   unit check of Decision 3) and any reorder of the package's imports leave them unset. Write-in:
   both are declared in `__init__` as `Callable[[], None]` with a no-op default, and
   `release_at_exit` calls whatever is bound.

## Constitution checks
- §4.3, §4.4 (one target, two imports): untouched; the guest binary does not change.
- §4.6 (the artifact set is the product): no artifact byte changes; the wheel's code changes only.
- §4.9 (tests count): the new unit check counts renewed objects; no time is read.
- §4.10 (claims carry evidence): the draft labels its numbers; the two Mediums are where a number
  would be labelled EXECUTED from a scan that cannot see what it claims to count (finding 1), and
  where a run on the judge's Python would not stand for the minimum Python (finding 2).
- §4.13 (uv, ruff, pytest): named in criterion 8; no dependency added.
- §4.14 (git): a worktree on `spec/104-…`, stacked on 103's reviewed tip; consistent.
- §4.15 (safe by default): no default, limit or channel changes; the fork refusal keeps its fact
  (`fork_used`).
- §5.2 (no undecided choice): the shape check passes; Decision 8's sentence on 103 is an expectation,
  not an undecided choice (finding 5).
- §5.6 (review): this pre-build review is optional for a judge-only change and was asked for because
  the chain's lane wants the design read before code; the build gets its own reviewer.
- §7 never-do list: nothing tripped; no patch, no fetch, no copy, no commit asked of the builder
  beyond the lane's.

## Disposition (filled in by the author, then confirmed by the reviewer)
1. The lock order of Decision 6 is wrong in two pairs, and criterion 7's scanner cannot see them — fixed: `build/104/lock_order.py` rewritten (attribute locks `.lock`, `.*_lock`, `.*_cond` matched by their attribute; calls followed transitively with the shortest path; a class call followed into `__init__`, a method call into every class that defines it, a call on an imported module such as `os.close()` into nothing) and re-run on `a9064a2` (`build/104/lock_order.out`): `_stack_size_lock > home.lock` (`_start_guest:4306`, `:4315`); `_zip_lock > _lock` (`_Private.remove:958`), `> _held_lock` (`_Private.__init__:900` and `_drop:963`), `> _pending_warnings_lock` (`_warn_later:1367`); nothing else. Decision 6 restated from that output: four pairs, two heads (`zip_lock` over `cache_lock`, `held_lock`, `warnings_lock`, one at a time; `stack_size_lock` over a home's `lock`), `stack_size_lock` no longer called a leaf, no inversion; criterion 7 names the corrected scanner, its two reports, the four pairs, and asks for both outputs (103's tip and the built commit) in the landing notes.
2. Decision 2's lock renewal "by type" is not implementable as written on the project's minimum Python, and the judge cannot see that — fixed: Decision 2 names one table, `RENEW` in `_process.py` (`{type(threading.Lock()): threading.Lock, type(threading.RLock()): threading.RLock, threading.Condition: lambda: threading.Condition(), queue.SimpleQueue: queue.SimpleQueue}`), keyed by exact type, shared by `reset_after_fork` and Decision 3's check; it says why not `isinstance` and not `type(value)()` (your probe, cited READ). Decision 3 adds a `RENEW` row and a paragraph "Which Pythons see it": the judge runs on 3.14.2 (CI, `UV_PYTHON`) and 3.13 locally, no leg runs 3.11, so the 3.11/3.12 case is covered by Decision 2's text, not a run; the residual risk is named (an at-fork hook that raised would be unraisable and ignored, the child keeping its inherited locks), and a builder with a 3.11 runs the file once and records it (criterion 3).
3. The reset renews two locks today's hook leaves alone, and the spec says "exactly the same changes" — fixed: Decision 2 now reads "makes the changes the hook makes today and two more: `warnings_lock` and `defaults_lock` are made anew as well, by the same rule (F8), where today's list leaves them", citing 103's Decision 4, which hands that decision here.
4. A plain dataclass does not raise on a misspelt field outside monkeypatch — fixed: `_Observers` is `@dataclass(slots=True)` (Decision 4), with your failure case written in as the reason; the sentence on `AttributeError` now credits the slots and monkeypatch's `raising=True`.
5. Decision 8 states what 103 does as a fact — fixed: 103 is now in the tree, so the bullet quotes its Decision 4 (READ) instead of expecting it; Decision 1's fallback paragraph is replaced by 103's actual placement of each group (READ, its Decisions 4 and 5), with "the builder re-finds each by 103's move table, not by this paragraph"; Decision 1 also adopts 103's import rule (`process` added to check 3's by-name list, `_process` first in check 2's `ORDER`), and Decision 3 retires 103's check 1, which would fail by construction once no module-level lock remains (the problem statement's sentence on 103 is labelled READ too).
6. Two counts and one sentence disagree with the tree — fixed: "12 of the 51 lines (`_engines` twice, the rest once)" and "Twenty stay (39 lines)" in Decision 4; Decision 3's sentence now reads that the three real-fork checks stay "with their reads moved as Decision 4's table says", naming `FORK_HOOK`'s lines 493 and 496 (`process().tool_threads_lock`) and the embedding rows' `fork_used` and `forked`; criterion 3 says the same.
7. The two callables the zip and warnings modules register on the object have no stated default — fixed: Decision 2 declares `remove_zips` and `flush_warnings` in `__init__` as `Callable[[], None]` with a no-op default (`lambda: None`), bound by `_zip.py` and `_private_dirs.py` at import, and `release_at_exit` calls whatever is bound, so a fresh `_Process()` and any import order are safe.

Also written in while revising, outside the findings: Decision 5 notes that 106's `_platform.PLATFORM` (a class call) is outside both scanners' lists and is 106's named seam; Decision 8 says `_Process` has no `platform` field (106's fallback applies) and that group D leaves for 106's platform object; the Design adds `tests/release_shards.toml` (`test_process.py` in `own-runner`, spec 063 rule (g)) and the `test_runner_package.py` row; the claim list names the retired check and the files whose judge hash changes; the Status line records this review and the revision. Cross-spec ownership is unchanged and aligned: 103 the module size ceiling, 107 the function-length ceiling and the test-seam allowance check (Decision 4's twenty names as its initial list), 104 exactly its two placement checks.

## Verdict
Lands (may be built) once Decision 6's lock order is restated from a corrected scan (finding 1) and
Decision 2 names the type-to-factory table for the lock renewal (finding 2); findings 3 to 7 are
write-ins that need no further round.
