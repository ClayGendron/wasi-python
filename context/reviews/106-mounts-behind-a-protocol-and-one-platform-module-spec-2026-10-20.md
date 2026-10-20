# Review of 106 — `mounts.py` behind a call-context protocol, one platform module, one stamp, and the source explains itself

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (pre-build reviewer for the chain 102–107)
- **Reviewed:** the specification as drafted
  (`context/specifications/106-mounts-behind-a-protocol-and-one-platform-module.md`, untracked on
  `claude/gallant-ride-9nxxmn`; the tree read is main `a9064a2`, the memo's commit, which the
  specification names as the tree it read)
- **Run:** none (pre-build review of the draft)
- **Re-ran:** `uv run pytest tests/checks/test_rules.py -k specifications -q` → 3 passed, 41
  deselected, exit 0; `uv run pytest tests/checks/test_rules.py -k open_question -q` → 1 passed,
  43 deselected, exit 0; a case-insensitive grep of the specification for the three phrases the
  scanner rejects → no line, exit 1. Every other command below is a read of `src/wasi_python/` or `tests/` at `a9064a2`, no
  build, no judge tier, no dispatch. Time box: 25 minutes (parallel-safe), kept.

The chain's context: specifications 103, 104 and 105 are not in the tree (only 102, 106 and 107
are, all untracked). Where 106 depends on their names it says so for 103 ("when 103's
specification names them otherwise, its names hold and this one reads through") and for 102
("102's name holds"); for 104's seam it names no fallback (L8 below).

## Acceptance criteria against evidence

For a draft, "met" means the criterion is countable, the judge can check it, and the facts it
rests on are true at `a9064a2`.

1. **Four rules checks and two unit checks, seen failing first** — met as written: each check is
   named, the commit it fails on is named (commit 1 to 5 of the Design), the output's place
   (`build/106/`) is named. READ.
2. **`mounts.py` imports nothing from the runner** — met: the grep in the criterion is exact.
   EXECUTED at `a9064a2`: `grep -nE 'from \.|import wasi_python' src/wasi_python/mounts.py`
   lists `from .runner import _Call` (line 51, under `TYPE_CHECKING`) and `from . import runner`
   (line 631); after the change only 102's `_wasmtime_ffi` import may remain.
3. **The platform is chosen once** — met: EXECUTED, `grep -nE "os\.name|sys\.platform"
   src/wasi_python/*.py` is 22 lines, all in `runner.py`, in the seventeen functions the
   specification lists (`_kernel_identity` 3, `_try_lock` 2, `_sweep_entry` 2, `_cache_dir` 2,
   the other thirteen one each; the enclosing names read by line). The claim "none is a message
   text" holds: READ, every one of the 22 is a condition.
4. **One stamp** — met: EXECUTED, `_digest` (`runner.py:4678`) keys `_digests` on
   `(str(path.resolve()), st.st_size, st.st_mtime_ns)`; `_versions: dict[Path, str]`
   (`runner.py:3919`) keys on the path forever; `_stamp` (`runner.py:3854`) is the five-tuple
   the specification states. The two unit checks count opens, never time (§4.9 holds).
5. **No finding ID in `src/`** — met in shape; the "seen failing" count is wrong (L3) and the
   regex reaches past review IDs (L7). EXECUTED through `tokenize` over comments and docstrings:
   `REVIEW_PHRASE` matches 61 lines (mounts 9, runner 38, tools 14); `FINDING_ID` matches 80
   tokens (mounts 14, runner 49, tools 17).
6. **Every module lists its specifications** — met in shape; the count it starts from is wrong
   (L2). EXECUTED: 315 occurrences of `spec NNN` in `src/wasi_python/*.py`, 39 distinct numbers.
7. **No verdict moved** (`sameness.py --claims`) — met: `tests/harness/sameness.py` takes
   `--claims` (READ, its docstring line 24 and `load_claims` at line 309); the claim list is
   written. The list of rows that move is incomplete where the platform site list is (M1).
8. **The parity checks are untouched** — met for `test_v1_4_embedding.py`: EXECUTED, its only
   platform-function sites are `runner._try_lock` (line 1516) and `runner._unlock_close` (line
   1518). For `test_runner_mounts.py` the three checks "moved off `monkeypatch`" are the three
   `_epoch_ticker.count` sites (lines 128, 130, 132) and the one `_ctrl_c_watched` site (line
   171); no `_siphash13` is patched (L4).
9. **`tests/public_api.txt` unchanged** — met: EXECUTED, the file names no `_Files`, `mounts`
   module or runner private; `__init__.py:129` re-exports `Errno`, `FileFault`, `FileProvider`,
   `FileRecord`, `Mount`, `RefusedWrite`, `Stat`, `WritableFileProvider` from `mounts`, none of
   which the specification touches. `_Files` is constructed in five places (EXECUTED:
   `runner.py:3067`, `5721`; `tests/harness/files.py:669`, `726`;
   `tests/unit/test_runner_mounts.py:670`); `files.py:726` passes `engine` positionally, so the
   keyword-only `context` the specification chooses is the right shape.
10. **ruff, mypy, the `Any` counts** — met as written; EXECUTED, `grep -c '\bAny\b'
    src/wasi_python/mounts.py` is 72 today, the number the builder records against.
11. **The chain's dispatch** — met as written: the one dispatch on the chain's final tip is the
    owner's rule (the memo, section 8, READ), and the Windows and macOS legs are the only run of
    `_Windows` and `_Darwin`; the specification says the builder reads that run's `rules` and
    `unit` groups on the three systems.

## Findings, most severe first

1. **The platform site list misses three functions and every `monkeypatch` string form**
   (`context/specifications/106-…md`, "The unit checks that bind a platform" and "Files it shares
   with others") — the EXECUTED grep `runner\._(walk|…)` sees only attribute reads, so the sites
   that patch a platform function by name, and three functions the table absorbs, are absent
   from the migration list and from the lane's shared-file list.
   Failure: EXECUTED, `grep -rnoE 'setattr\(runner, "_(…)"' tests/` and the attribute form
   together: `tests/unit/test_runner_threads.py` names `_tell_interpreter` three times and
   patches it once; `tests/unit/test_inline_sessions.py` names `_trap_handlers_ready` twice,
   `tests/unit/test_runner_calls.py` once, `tests/unit/test_runner_async.py` patches it twice;
   `tests/unit/test_runner_grants.py` patches `_close_held` once;
   `tests/checks/test_v1_2_hostile_guest.py` patches `_guest_stack` at lines 2792 and 2799
   beyond the one call at 2745 the specification counts; `tests/unit/test_runner_sweep.py`
   patches `_dir_fd_ok` at lines 453 and 539, not one site. Commit 2 deletes or thins those
   functions ("the builder's choice per function"), so each omitted site either breaks or keeps
   patching a stub that no caller reads, and the verdicts those checks give stop meaning what
   they say. Evidence that closes it: the grep of both forms kept under `build/106/`, the site
   list and the shared-file list corrected (three files added), and criterion 8's "named" list
   grown to match. Medium.
2. **A POSIX host without `dir_fd`, and the check that forces that path, have no stated home**
   (Decision 2's table, rows `has_dir_fd`, `remove_tree`, `real_dir`, `make_missing`) — the table
   gives `_Posix.remove_tree` "by descriptors" and `_Windows.remove_tree` "by paths", with
   `has_dir_fd` a value "read once"; today the choice is made per call on every platform.
   Failure: READ, `runner.py:1122` (`_remove_tree`: `if _dir_fd_ok(): _remove_at … elif dir_fd
   is None: _remove_by_path(_long_path(…))`), `2832`, `2923`, `2929` (`_real_dir_at` guarded by
   `_dir_fd_ok()`) and `2941` (`_open_dir`). A POSIX host where `os.mkdir not in
   os.supports_dir_fd` takes the by-path remover today and would raise or walk wrong under a
   `_Posix` that never consults `has_dir_fd`. And `tests/unit/test_runner_sweep.py:539` forces
   `_dir_fd_ok` False on Linux to drive `_remove_by_path` against a symlink canary; binding
   `PLATFORM` to `_Windows()` there routes `long_path` to the `\\?\` form and `try_lock` to
   `msvcrt`, so that check has no binding that works. Evidence that closes it: one sentence that
   `_Posix.remove_tree`, `real_dir` and `make_missing` branch on `self.has_dir_fd`, and that a
   check may set `has_dir_fd` on a `_Posix()` instance for its duration. Medium.
3. **`_select` sends Android to `_Linux`, which "moved verbatim" does not do** (Decision 2,
   `_select`: `sys.platform.startswith(("linux", "android"))`) — every Linux-only branch today
   tests `startswith("linux")` (READ, `runner.py:804`, `4397`→`4505`, `4599`), so an Android host
   gets no boot-id read, no `pthread_getattr_np` probe and no trap-handler check; after the
   change it gets all three.
   Failure: `sys.platform == "android"` (CPython 3.13+) → `_Linux().kernel_identity()` reads
   `/proc/sys/kernel/random/boot_id` where today `_kernel_identity()` is `None`. Fix text: write
   `sys.platform.startswith("linux")`, or keep the tuple and add the reason in one sentence.
   Low.
4. **"304 times for 60 distinct numbers" is two wrong numbers under an EXECUTED label** (The
   problem, item 4) — the command as written, `grep -oE 'spec [0-9]{3}' src/wasi_python/*.py |
   sort -u | wc -l`, has no `-h`, so it counts distinct `file:spec NNN` pairs.
   Failure: EXECUTED at `a9064a2`: 315 occurrences (`grep -oh … | wc -l`) and 39 distinct
   numbers (`grep -ohE … | sort -u | wc -l`); 60 is the pair count. Fix text: "315 times for 39
   distinct numbers" and `-oh` in the command (the memo's own 315 agrees). Low.
5. **"38 lines for the phrase" is the narrow grep's count, not the check's** (Decision 4, "Seen
   failing") — `REVIEW_PHRASE` is `\breviews?\b|…`, every form of the word, while 38 counts the
   lines of `review'?s? [A-Z]?[0-9]|the (build|security|delta|re-)?review`.
   Failure: EXECUTED through `tokenize` over comment and docstring tokens: 61 lines (mounts 9,
   runner 38, tools 14); the 38 is runner.py's share by coincidence. Fix text: "61 lines for the
   phrase (mounts 9, runner 38, tools 14) and 80 bare IDs". Low.
6. **`_siphash13` is not monkeypatched anywhere** (Decision 1, "The fake": "`runner._siphash13`
   by `monkeypatch` (READ: three, one and two sites)") — EXECUTED,
   `grep -n _siphash13 tests/unit/test_runner_mounts.py` is one line, 472, a direct call that
   computes the expected `(dev, ino)`. Fix text: "three and one sites; one direct call of
   `_siphash13` at line 472, which the fake's SipHash fallback keeps equal". Low.
7. **"a session's turn ending drop[s] the call" names a site that does not exist today**
   (Decision 1, "Who implements it") — EXECUTED, `grep -nE '\.call = None' src/wasi_python/` is
   one line, `mounts.py:750` in `release()`; between turns the table holds the last turn's
   `_Call` until `_arm` (`runner.py:5371`) makes the next one and `_Call.__init__`
   (`runner.py:3258`) overwrites it. The `leave()` at a turn's ending is new. It is unobservable
   (READ: the table reads `self.call` only in `_gate` and `_home`, which run under a host
   function during a turn; `walk` calls `_made` directly, `mounts.py:729` → `889`), so the "no
   call" answers hold; the sentence should say it adds the call, not moves it. Low.
8. **`trampolines(engine)` drops the `wt` that `bind` carries** (Decision 1's table and
   "`mounts.py` after commit 1") — today `bind(wt, store, plain, instance)` (`mounts.py:755`)
   hands `wt` to `_trampoline_module(wt, engine)`, which compiles with `wt.Module`
   (`runner.py:3523`, `3535`); `wt` is the `_wasmtime()` seam's module at `runner.py:487`,
   `670`, `3186`, and the real `wasmtime` in the harness (`tests/harness/files.py:684`, `734`).
   Fix text: say that `bind` loses its first parameter (the harness's two calls change) and that
   `_Context.trampolines` compiles through the engine module's own wasmtime import, or that `wt`
   stays and the protocol reads `trampolines(wt, engine)`. Low.
9. **`FINDING_ID` refuses more than finding IDs, and rule 2 looks in one place** (Decision 4,
   "The rule") — `[CDFLNS]\d{1,2}` with its two look-arounds also matches `C99`, `C11`, `L1`
   and `L2` (cache levels), `F1` (a key) and `N1` in any future comment; the specification names
   only `F401` and `MD5` as kept out, and gives a maintainer no recourse. And three of today's
   IDs are a review's items that a specification carries in its decisions (`C1` and `C2` of
   spec 078's and 048's confirmations, `S2` of spec 024's security review; EXECUTED,
   `mounts.py:2041`, `runner.py:2718`, `3007`), while rule 2 sends the builder to
   `context/reviews/` alone. Fix text: one sentence naming the recourse (an allowlist line in the
   check, or the convention "ISO C of 1999" for such tokens), and "`context/reviews/` or the
   specification that carries the finding" in rule 2. Low.
10. **104's seam is named four times with no fallback** (Decision 2, "Why a module-level object",
    "The unit checks that bind a platform", the Design's commit 2) — 104 is not drafted; 103's
    names have a fallback sentence, 104's seam has none. Fix text: "when 104 gives a module-level
    name no seam, `monkeypatch.setattr(_platform, "PLATFORM", …)` for the check's duration".
    Low.

Checked and found right, for the record (all EXECUTED at `a9064a2` unless marked): the fourteen
back-calls from `mounts.py` into the runner, eight names (`_siphash13` 5, `_epoch_now` 3, the six
others once each); the four call fields read (`cancel`, `stop_at`, `ended`, `home`, at
`mounts.py:707`, `841`, `848`–`857`); the nine protocol methods cover every one of those reads and
calls, and `walk`'s condition at `mounts.py:723`–`725` is exactly `exiting()` and
`ctrl_c_pending()`; the runner's imports from `mounts` (`runner.py:57`, `3053`, `3486`, `3508`,
`3526`, `3537`, `5710`); 2,235 and 1,908 lines; the `_gate` order and its "named once" rule
(`mounts.py:847`–`860`); the two `unlock_close` orderings (`runner.py:1060`–`1063`, `861`–`872`);
`_kernel_identity`'s `None` on an unknown host (`runner.py:798`–`835`, READ);
`tests/unit/test_runner_threads.py:100` (`freebsd14`); the sweep counts (`_remove_tree` 9,
`_try_lock` 7, `_unlock_close` 2, `_kernel_identity` 1) and the grants counts (`_walk` 18,
`_identity_of` 5, `_walk_windows` 2); 187 files under `context/reviews/`; `_identity`, `_win_api`
and `_stack_api` are not in today's fork reset list (`_after_fork_in_child`), so leaving them out
of 104's object changes nothing; the header fields and sections the scanner wants are present
(the two shape checks pass); no scanner word in the text.

## Constitution checks

- §4 constraints: §4.3 and §4.4 untouched (no guest byte, no import). §4.5 holds: no embedder
  named. §4.9 holds: the stamp check counts opens through a seam, never time. §4.10 is the one
  tripped, mildly: three EXECUTED numbers are wrong (findings 4, 5, 6), each with its fix text.
  §4.13 holds: `uv run`, ruff and 105's mypy in criterion 10. §4.14 holds: a stacked build on
  105's reviewed tip, the base commit to be written in the Status line, the branch pushed only
  for the chain's one dispatch. §4.15 holds: `private()` stays `True` on Windows and owner-and-
  mode on POSIX; no default loosens. The judge is not weakened: no golden, gap, allowance,
  parity table or progress file is edited; the moved unit checks keep their assertions; the new
  checks are seen failing first; `--accept-judge` names them. "No finding ID removal deletes a
  reason" is stated as three rules and a word-diff the reviewer reads; it holds as written.
- §5.2: no choice is left undecided; every decision carries its reason (why a protocol, why four
  classes, why a module-level object, why the caches stay, why its own commit). §5.6: a
  parallel-safe specification needs no pre-build review by rule; this one is the chain's, by the
  memo's section 8. Windows and macOS: untestable locally, covered by the chain's one dispatch,
  and the specification says which groups the builder reads there.
- §7 never-do list: nothing tripped. No commit, push, branch, build or dispatch was made for this
  review; the specification asks for none outside §4.14.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. The platform site list misses three functions and every `monkeypatch` string form — fixed: Design, *The unit checks that bind a platform*, is now a table of all eight files with both forms (76 sites at `a9064a2`, EXECUTED by one grep with both alternations over the 26 names, kept at `build/106/platform-sites.txt`), including `_tell_interpreter`, `_trap_handlers_ready`, `_close_held` and `_win_open` and the two `_guest_stack` patches at `test_v1_2_hostile_guest.py:2792`, `2799` and the two `_dir_fd_ok` patches at `test_runner_sweep.py:453`, `539`; each site is a `_platform.PLATFORM` call, a class's method, or a binding; *For the lane* adds `test_runner_async.py`, `test_inline_sessions.py` and `test_runner_calls.py`; commit 2's bullet and criterion 8 count the table (every site, and the grep empty after); the claim list's "unit rows moved" names the 76.
2. A POSIX host without `dir_fd`, and the check that forces that path, have no stated home — fixed: Decision 2's table makes `has_dir_fd` an instance attribute read once at construction that `_Posix` consults per call, and gives `_Posix` both branches in the `remove_tree`, `real_dir` and `make_missing` rows (today's `elif dir_fd is None`, `fd is not None and _dir_fd_ok()`, and the by-path `else`), plus an `open_dir` row for `runner.py:2941`; the new paragraph *How a check binds a platform* says the sweep check at line 539 does `monkeypatch.setattr(_platform.PLATFORM, "has_dir_fd", False)` on the real object and is never bound to `_Windows()` on Linux. The `make_missing` row names the one answer that changes on such a host (the path branch instead of a failing `os.mkdir(…, dir_fd=)`), with its reason.
3. `_select` sends Android to `_Linux`, which "moved verbatim" does not do — fixed: `_select` reads `sys.platform.startswith("linux")`, and the paragraph after it says Android stays a `_Posix` (no boot-id read, no probe, no trap-handler check, as today) and names the one function that differs, `_guest_stack`'s acceptance of `android`, as a decided change (an Android host gets `None` from `_Posix.stack_bounds`; INFERRED harmless, no release runs there; a later `_Android(_Posix)` is the recourse).
4. "304 times for 60 distinct numbers" is two wrong numbers under an EXECUTED label — fixed: *The problem*, item 4, reads "315 times for 39 distinct numbers" with `grep -oh … | wc -l` and `… | sort -u | wc -l`, re-run (EXECUTED) and agreeing with the memo's 315; Decision 4's "The count 315 falls".
5. "38 lines for the phrase" is the narrow grep's count, not the check's — fixed: Decision 4's "Seen failing" reads 61 lines (mounts 9, runner 38, tools 14) and 80 bare IDs (14, 49, 17), re-counted through `tokenize` over comments and docstrings (EXECUTED, `build/106/ids.py`, the same numbers the review found); *The problem*, item 4, carries the same counts beside the narrow grep's 38.
6. `_siphash13` is not monkeypatched anywhere — fixed: Decision 1, *The fake*, reads "three sites (`_epoch_ticker.count`, lines 128, 130, 132) and one (`_ctrl_c_watched`, line 171)", EXECUTED, and says the direct call at line 472 is not a patch and keeps its number through the fake's SipHash fallback; criterion 8 and the claim list say "the four mount sites (two checks)".
7. "a session's turn ending drop[s] the call" names a site that does not exist today — fixed: Decision 1, *Who implements it*, says `leave()` goes where `release()` sets `self.call = None` today (`mounts.py:750`, the one site), that a `leave()` at a turn's ending is new, and why it is unobservable (the table reads the call only in `_gate` and `_home` under a host function; `walk` calls `_made` directly).
8. `trampolines(engine)` drops the `wt` that `bind` carries — fixed: the protocol reads `trampolines(wt, engine)` in Decision 1's table, the code block and the Design; `bind(wt, store, plain, instance)` keeps its signature, so the harness's two calls do not change, and the table row says `wt` stays the wasmtime module `bind` already carries.
9. `FINDING_ID` refuses more than finding IDs, and rule 2 looks in one place — fixed: Decision 4 gains *What the ID regex also refuses, and the recourse*: by design (`C99`, `L1`, `F1` written in words), with one tuple `FINDING_ID_ALLOWED`, empty at first, of exact tokens with a reason each, every addition read by the review, and a review-finding ID never added; rule 2 and that paragraph send the builder to `context/reviews/` or the specification that carries the finding, naming `C1`, `C2` (specs 078 and 048) and `S2` (spec 024) with their lines.
10. 104's seam is named four times with no fallback — fixed: *How a check binds a platform* says `PLATFORM` is outside 104's underscore rule, gives the binding `monkeypatch.setattr(_platform, "PLATFORM", …)` and the attribute form on the real object, and names the fallback both ways (a `process()` field for the platform if 104 adds one, else the module name); commit 2's bullet and the site table no longer say "104's seam". Added for the cross-spec point from 107's review: *The allowance list* says 106 shrinks 104's twenty-name list, which 107's seam check starts from, by the nine platform names and the one mount-table `_ctrl_c_watched` site, and leaves the other call-path names on it; every caller reads `_platform.PLATFORM` through the module (`from . import _platform`), which `test_the_platform_is_chosen_once` enforces.

## Verdict

The specification is fit to build once the two Mediums are written in (the full platform site
list with both grep forms, and `_Posix`'s `has_dir_fd` branch with the sweep check's binding);
the eight Lows are fix text the author writes into the draft without another round.
