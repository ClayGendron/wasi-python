# 077 — The grant follow-ups

- **Status:** **landed 2026-10-19** (accepted on `961f4b9` as `4441f7a`, history line 76; the build review, `../reviews/077-the-grant-follow-ups-build-2026-10-19.md`, said it lands once criterion 6's Windows run passed, and it did). Before landing: drafted 2026-10-19 on `spec/077-the-grant-follow-ups` from main `d900dd9`
  (`f7f248c`); **revised 2026-10-19 against its pre-build review** (written in the lane's
  scratchpad, `077-review/077-the-grant-follow-ups-spec-2026-10-19.md`, with its probes, to be
  copied to `../reviews/` by the lane; verdict: "ready once F1 and F2"; the lane's rulings on F1,
  F2, N1 and N2 written in; every finding answered in "Disposition of the pre-build review");
  confirmed for build at `cba597e` (the confirmation is appended to the same review); rebased
  onto main `23f1c4f` (specs 069 and 071) as `aaac75e`; **built 2026-10-19** (`42795d4`; the
  Landing notes): the full judge has 0 fail on macOS, its one growth a run-to-run variation of
  spec 071's checks that main shows too; the first Windows dry run, 39210847037, did not reach
  Windows (the macOS build job's judge failed on that same variation; the lane ruled to fix it
  first, as spec 080). **Rebased onto main `8f8de73` (spec 080 landed)**, with this spec's diff
  unchanged; the fast tier there shows `grew 0`; **the Windows dry run 39225762652 passed every
  job on all three systems**, with the four named nodes `PASSED` on `verify (windows-2025)`;
  awaiting its build review. The lane asked for the pre-build review, though §5.6
  does not: the spec changes neither the guest's imports nor its exports, the artifact set nor
  the build recipe. A different agent reviews the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** the runner, the judge and docs; **parallel-safe**, not build-class.
  `src/wasi_python/runner.py` (`_WIN_DEVICES` and `_rewritten`, and one new set beside them);
  `tests/unit/test_runner_grants.py` (one case's module and rows, one case's rows, one case
  added, the Win32 model's reserved names and one folder); `README.md` (*Grants*),
  `CHANGELOG.md` (0.1.0a7). It touches no `scripts/`, `recipes/`, `downloads/SHA256SUMS` or
  workflow on its branch. One temporary commit that adds `-rA` to the release workflow's verify
  step lives only on a throwaway remote branch, `spec/077-verify`, deleted after the Windows dry
  run (Decision 5). **It changes no line of `tests/public_api.txt`.**
- **Depends on:** 076 (the grant checks agree on Windows: `_rewritten`, `_WIN_DEVICES`, the raw
  wrong-mode rows and the Win32 model), landed in `3ea0582`.
- **Research it stands on:**
  - Spec 076's build review, findings F1 and F2
    (`../reviews/076-the-grant-checks-agree-on-windows-build-2026-10-19.md`), and spec 076's
    landing notes, which hand both to this spec.
  - This spec's pre-build review and its probes (`probe_control_order.py`, `probe_077_names.py`,
    EXECUTED there on macOS): in the raw case's real order the final write leaves its count, 2,
    at 208 before any control read; and `root=C:\b\new\a*b` is returned as `missing`, so
    `_make_missing` makes `new` before `a*b` fails.
  - Microsoft, "Naming Files, Paths, and Namespaces" (learn.microsoft.com, page dated
    2024-08-28, updated 2025-04-11; READ 2026-10-19). Its reserved names are `CON, PRN, AUX,
    NUL, COM1` to `COM9`, `COM¹, COM², COM³, LPT1` to `LPT9`, `LPT¹, LPT², and LPT³`, "also
    … followed immediately by an extension". Its note: Windows treats the ISO/IEC 8859-1
    superscript digits as digits in `COM#` and `LPT#`, "making them reserved in every
    directory". It names no `COM0` or `LPT0` as reserved. Its reserved characters are
    `< > : " / \ | ? *`, the character 0 and the characters 1 to 31.
  - CPython's `Lib/ntpath.py` (`context/prior_art/cpython`, branch 3.14, `7c04882`, lines 302
    to 333, READ). `_reserved_chars` is the characters 0 to 31 and `" * : < > ? | / \`.
    `_reserved_names` is `CON PRN AUX NUL CONIN$ CONOUT$`, and `COM` and `LPT` with `1` to `9`,
    `¹`, `²`, `³`. `_isreservedname` refuses a name that ends in a period or space (but not `.`
    or `..`), holds a reserved character, or whose stem (before the first period, trailing
    spaces dropped, upper-cased) is a reserved name. Its comment: "The rules are complex and
    vary across Windows versions. On the side of caution, return True for names that may not be
    reserved." `ntpath.isreserved` is new in 3.13, and the runner supports 3.11, so it cannot be
    called from the runner.
  - Probes, EXECUTED on macOS arm64, CPython 3.14.2, wasmtime-py 49.0.0, on main `d900dd9`;
    scripts and outputs in the worktree's git-ignored `build/077/`:
    - `probe_raw_read.py` → `.out`. Today's `read` export's iovec at 400 is `(0, 0)`. A read
      through a write-only descriptor answers 8 through it and through the iovec at 200,
      `(300, 2)`. (It ran the control read without the case's earlier write; the review's
      `probe_control_order` corrects what a control sees in the real order.)
    - `probe_rewritten.out`. Today `_rewritten` is false for `COM¹`, `lpt³.txt`, `Com² .x`,
      `CONIN$`, `conout$.log`, `COM0` and `LPT0`, and true for `COM1`.
    - `probe_oracle.py` → `.out`. Over 18,275 names of up to three pieces, a `_rewritten` with
      CPython's reserved characters and an upper-cased stem equals
      `ntpath.isreserved("x\\" + name)` on every one; with a lower-cased stem it differs on 76,
      all holding the dotless `ı` (`'con\u0131n$'.upper()` is `CONIN$`, its `.lower()` is not
      `conin$`).

## Decisions

1. **The raw read row reads two bytes, and a control read proves it (F1; the lane's ruling).**
   The `read` export of `RAW` reads through the iovec at 200 (`buf 300, len 2`) that the
   module's data already holds, and writes its count at 208, as `write` does. The row's expected
   value is unchanged: `files.wrong_mode_errno(sys.platform)`. Then, after the file assertions,
   one control row:
   - the count and the buffer are zeroed first, `memory.write(store, bytes(4), 208)` and
     `memory.write(store, bytes(2), 300)`, because the final write has just left 2 at 208 and
     `XX` at 300 (the review's F1, EXECUTED there);
   - the grant's `f.txt` is opened again to read, and `read` through it answers 0;
   - the count at 208 is 2, and memory at 300 holds `b"or"`.

   Both assertions are then live. An errno alone cannot tell a two-byte read from a zero-length
   one, since both answer 8 today (`probe_raw_read.out`), so the control is what makes the
   row's length checkable. It runs last because it overwrites the buffer the final write sends.
   The review's other options (eight more bytes at 400, or a count slot of its own) were not
   taken: one iovec and one count, used by both exports and zeroed once, is the simpler module.

2. **The reserved names are Microsoft's and CPython's, together (F2 of 076's build review).**
   `_WIN_DEVICES` gains `COM¹ COM² COM³ LPT¹ LPT² LPT³` (Microsoft's page) and `CONIN$ CONOUT$`
   (CPython's `ntpath`; the review upheld them). The rule 076 set is "refuse a name Windows may
   rewrite"; Microsoft reserves the six, and CPython refuses the two console names "on the side
   of caution". Refusing one costs an embedder nothing it could use: a folder so named cannot be
   granted on Windows, as for `NUL`. `COM0` and `LPT0` stay allowed: neither source reserves
   them. The page mentions `COM0` once, as a link in the object manager's `Global??` folder; a
   `\\.\COM0` path reaches that, but a folder named `COM0` inside a path is an ordinary name
   (INFERRED from the page's two lists). The superscripts are written as `\u00b9`, `\u00b2`,
   `\u00b3` escapes, so the source shows which code points they are.

3. **`_rewritten` is `ntpath.isreserved` for one component (the review's F2; the lane's
   ruling).** It gains CPython's reserved characters: a new `_WIN_RESERVED_CHARS`, the
   characters 0 to 31 and `" * < > ? |` (`:` is already refused, and `/` and `\` never reach a
   component, since the walk splits on them). And it compares the stem upper-cased, against
   upper-case names, as CPython does: `.lower()` differs from CPython on names with the dotless
   `ı` (`probe_oracle.out`), and the rule is easiest to state and to check as "the same as
   `ntpath.isreserved`". The refusal's message is unchanged ("a name Windows rewrites"), so
   076's rows and messages stand. Without the characters, `root=C:\b\new\a*b` makes `new` and
   then fails "cannot be made" (the review, EXECUTED in the model); with them, it is refused
   before anything is made, as `C:\b\new\COM¹` now is (that root, too, made `new` before
   failing: 076's build review, INFERRED there).

4. **The model follows the same rule, and an oracle case pins it.**
   - The Win32 model in `tests/unit/test_runner_grants.py` keeps its own reserved names and
     characters (never imported from the runner, so a stand-in in the runner is caught). It
     gains the eight names, upper-cased as CPython's, and the reserved characters: a segment
     holding one names nothing, as a device does, so `_win_resolve` answers None (Win32's
     `ERROR_INVALID_NAME`).
   - Its folders gain `c:\b\com0`, so a row can show Decision 2's boundary. The fuzz's alphabet
     is unchanged, so its count, 16,653, holds.
   - A new unit case, `test_a_rewritten_name_is_one_ntpath_refuses`, asserts
     `runner._rewritten(name) == ntpath.isreserved("x\\" + name)` over every name of one to
     three pieces from `probe_oracle.py`'s 26 pieces, 18,275 names, and asserts that count and
     that both answers occur (so it is not vacuous). The `x\` prefix keeps `ntpath` from reading
     a leading `D:` as a drive. It is skipped below Python 3.13, which has no
     `ntpath.isreserved`; the judge and the release run 3.14.2 (`UV_PYTHON`), so it runs
     everywhere it counts. It counts names, not time.

5. **How it runs on Windows: one temporary commit, `-rA` only** (spec 076's Decision 7 route,
   cut down). Main's verify step already runs `tests/unit/test_runner_grants.py` whole on all
   three systems, and every changed or new case is in it. So no node id is added. The other two
   files 076 named are unchanged here and hold none of the new names or characters. `-rA` is
   still needed: pytest's default short summary names only failures, so a passing node leaves
   no `PASSED <node id>` line (the review's N2), and the workflow takes no dispatch input. The
   route:
   - `git commit-tree` on this branch's tip makes one commit whose only parent is the tip and
     whose tree differs only in `.github/workflows/release.yml`: `-rA` appended to the verify
     step's first command line (+1 −1). It is pushed straight to
     `refs/heads/spec/077-verify`; no local branch is made, and nothing is force-pushed.
   - `gh workflow run release.yml --ref spec/077-verify`, and wait for every job.
   - Record the run id, its `headSha`, that commit's parent (this branch's tip, the commit under
     review), the temporary diff and the per-system verdicts; quote the `PASSED` lines of
     criterion 6 from `verify (windows-2025)`.
   - `git push origin --delete spec/077-verify`; `git ls-remote` shows it gone.
   - **Authority.** Question 98's answer ("We should push changes as a branch"), as in 076.
   - **Freshness.** Any later change under `src/` or `tests/` (a review fix, or a rebase that
     changes a file there against the run's parent) needs a new dry run the same way. Only
     `context/`, `CHANGELOG.md` and `README.md` may follow it.
   - If spec 063 lands first, its shards run the whole file on Windows; the builder then uses
     that workflow's own output if it shows `PASSED` lines, and adds `-rA` only where it does
     not. The rest of the route is the same.

## Intent

Close spec 076's two low findings and the corner its pre-build review found beside them. The raw
read row reads real bytes, and a live control row shows it. The Windows walk refuses every name
`ntpath.isreserved` refuses (the six superscript device names, CPython's two console names, and
the reserved characters) before it opens or makes anything.

## Design

- `src/wasi_python/runner.py`:
  - `_WIN_DEVICES` holds upper-case names: `CON PRN AUX NUL CONIN$ CONOUT$`, and `COM` and `LPT`
    with `1` to `9` and `\u00b9\u00b2\u00b3`; a comment cites Microsoft's page and CPython's
    `ntpath`.
  - **new** `_WIN_RESERVED_CHARS = frozenset('"*<>?|' + "".join(map(chr, range(32))))`.
  - `_rewritten(name)`: false for `.` and `..`; true if `name` holds `:` or a character of
    `_WIN_RESERVED_CHARS`, ends in a space or a period, or its stem (before the first period,
    trailing spaces dropped) upper-cased is in `_WIN_DEVICES`. Its docstring says it equals
    `ntpath.isreserved` for one component.
- `tests/unit/test_runner_grants.py`:
  - `RAW`'s `read` export: `(call $fd (local.get 0) (i32.const 200) (i32.const 1) (i32.const
    208))`.
  - `test_a_read_only_grant_refuses_raw_writes`: the docstring says the read row reads two
    bytes; the control row of Decision 1 at the end, zeroing 208 and 300 first.
  - The model: its reserved names upper-cased with the eight added, its reserved characters,
    `_win_resolve` answering None for a segment that holds one; `_WIN_FOLDERS` gains
    `"c:\\b\\com0"` at its end.
  - `test_the_windows_walk_takes_dot_dot_on_walked_folders`: the rows of criterion 1 join the
    rewritten-name list, and their names join the `rewritten` tuple that asserts nothing was
    opened for them; one `walked_to(r"C:\b\COM0", r"C:\b\COM0")`.
  - **new** `test_a_rewritten_name_is_one_ntpath_refuses` (Decision 4).
- `README.md`, *Grants*: the reserved names become "`CON`, `PRN`, `AUX`, `NUL`, `COM1` to
  `COM9`, `COM¹` to `COM³`, `LPT1` to `LPT9`, `LPT¹` to `LPT³`", and the clause adds "a name that
  holds `<`, `>`, `"`, `|`, `?`, `*` or a control character, and, out of caution, `CONIN$` and
  `CONOUT$`, as Python's `ntpath.isreserved` refuses them" (the review's N1): the README says
  Windows rewrites or rejects such names, not that it rewrites all of them.
- `CHANGELOG.md`, 0.1.0a7: 076's bullet names the superscript names, the reserved characters
  and the two console names, with "(spec 077)" beside them. The raw row is a judge change, not a
  user-facing one, and is not listed.

## Scope

In: the two findings; the reserved characters and the upper-cased stem; the model; one oracle
case; the README and CHANGELOG lines; one Windows dry run on a throwaway branch.

Out:
- the refusal's message, which keeps 076's wording (Decision 3);
- the fuzz's alphabet (Decision 4);
- a real-file-system row on Windows: the refusal comes before any open, and the model's rows
  and the oracle case run on every system and in the Windows verify step;
- the model's N1 (076's build review: one trailing period stripped from `a..`): it cannot
  change a verdict;
- any change to the workflow that lands.

(The earlier draft put the reserved characters out of scope, saying the walk's open refuses
them. That holds only when the name is reached; a root still to be made is returned at its first
missing component, and the folders before the name were made. The review's F2; now in scope.)

## Acceptance criteria

Each check is seen failing first, before the code it guards, and against each stand-in named.
Stand-ins are made in the worktree, run, and restored; their output goes to `build/077/*.log`.

1. `test_the_windows_walk_takes_dot_dot_on_walked_folders` passes on macOS and Linux, and on
   Windows in the verify step. New rows, each refused "a name Windows rewrites" with nothing
   opened for the name:
   - roots still to be made, `C:\b\new\COM¹`, `C:\b\new\CONIN$` and `C:\b\new\a*b`
     (`may_make`): nothing is made, since the walk raises before it returns `missing`;
   - `C:\b\com²\x`, `C:\b\Com³.log`, `C:\b\LPT¹`, `C:\b\lpt² .x`, `C:\b\lpt³.txt` and
     `C:\b\conout$.log`, so each of the six superscript names is refused in some case and
     position;
   - and `C:\b\COM0` is walked to itself (Decision 2's boundary).

   Seen failing before the change (every new refused row). **S1:** `_WIN_DEVICES` without the
   superscripts: fails on `C:\b\new\COM¹`, "DID NOT RAISE". **S2:** without `CONIN$` and
   `CONOUT$`: fails on `C:\b\new\CONIN$`, "DID NOT RAISE". **S5:** `_rewritten` without
   `_WIN_RESERVED_CHARS`: fails on `C:\b\new\a*b`, "DID NOT RAISE".
2. `test_a_read_only_grant_refuses_raw_writes` passes on macOS and Linux, and on Windows in the
   verify step, with the read row through the iovec at 200 and the control row. Seen failing
   before the change (the control row written, the export still at 400 and 408): the control's
   count at 208 is 0 after the zeroing, `assert 0 == 2`, and the buffer would hold `b"\0\0"`,
   not `b"or"`. **S3:** the `read` export put back at offsets 400 and 408 after the change: the
   same failure, `0 == 2` on the count. **S4:** the write-only descriptor opened with `READ |
   WRITE` rights: the read row answers 0, not the wrong-mode errno, and fails.
3. `test_a_rewritten_name_is_one_ntpath_refuses` passes on macOS and Linux, and on Windows in
   the verify step, over 18,275 names with both answers seen. Seen failing before the change
   (today's `_rewritten` lacks the superscripts, the console names and the characters). **S6:**
   the stem lower-cased against lower-case names: fails on a name holding `ı`, such as
   `con\u0131n$`. S1, S2 and S5 fail it too.
4. The README and CHANGELOG lines of the Design.
5. In the worktree, without `--accept`: the fast tier while building, then the full judge with
   `-n 6` before "built": no pass lost, nothing grows, the judge change named
   (`tests/unit/test_runner_grants.py`); `ruff check` and `ruff format --check` green;
   `tests/public_api.txt` unchanged.
6. **On Windows:** one release dry run on `spec/077-verify` (Decision 5), every job passed on
   all three systems. The landing notes record the run id, its `headSha`, that commit's parent
   (this branch's tip, as reviewed), the temporary diff and the branch's deletion, and quote
   the `PASSED` line from `verify (windows-2025)` for
   `test_the_windows_walk_takes_dot_dot_on_walked_folders`,
   `test_the_windows_walk_records_the_true_chain`, `test_a_rewritten_name_is_one_ntpath_refuses`
   and `test_a_read_only_grant_refuses_raw_writes`. A node missing, `SKIPPED`, blocked or
   deselected there fails this criterion, as a `FAILED` one does. A failure is fixed here and
   run again on a new throwaway branch; nothing is skipped or allowed to fail.

## Disposition of the pre-build review

1. **F1 — fixed** (the lane's ruling). The control zeroes 208 and 300 before it reads
   (Decision 1); criterion 2 and S3 now state the failure that really happens, the count `0 ==
   2`. The draft's "count at 208 is 0" came from `probe_raw_read.py`, which ran the control
   without the case's earlier write.
2. **F2 — fixed** (the lane's ruling). `_rewritten` gains CPython's reserved characters and
   compares the stem upper-cased, so it equals `ntpath.isreserved` for one component (Decision
   3, `probe_oracle.out`); the model follows; `C:\b\new\a*b` is a criterion-1 row with S5; an
   oracle case pins the equality (Decision 4, criterion 3); the Scope line is corrected.
3. **N1 — taken.** The README says `CONIN$` and `CONOUT$` are refused out of caution, as
   `ntpath.isreserved` refuses them (Design).
4. **N2 — taken.** Decision 5's reason for `-rA` is pytest's default report, which names only
   failures; the verify step does not pass `-q`.
5. **N3 — no action.** The six names' coverage and the fuzz count hold.

## Landing notes

Built 2026-10-19 by the implementer (Claude Opus 5.5) in the worktree `../wasi_python-077`, on
`spec/077-the-grant-follow-ups`. The spec was confirmed for build at `cba597e`, then rebased with
no conflict onto main `23f1c4f` (specs 069 and 071 landed), where it is `aaac75e`, the same text.
Every local claim below was run (EXECUTED) on macOS arm64, CPython 3.14.2, wasmtime-py 49.0.0,
against main's frozen artifact set `build/sets/s-c50ca51fae5eb55b` of the main tree, read only
(`WASI_PYTHON_ARTIFACTS`). Logs are in the worktree's git-ignored `build/077/`.

### What was built (`42795d4`)

- `src/wasi_python/runner.py`: `_WIN_DEVICES` holds upper-case names, Microsoft's with the six
  superscript names and CPython's `CONIN$` and `CONOUT$`; a new `_WIN_RESERVED_CHARS`;
  `_rewritten` refuses a reserved character and compares the stem upper-cased (Decisions 2, 3).
- `tests/unit/test_runner_grants.py`: the `read` export through the iovec at 200 and the zeroed
  control row (Decision 1); the model's reserved names and characters and the `c:\b\com0`
  folder; criterion 1's nine refused rows and the `COM0` row; the new
  `test_a_rewritten_name_is_one_ntpath_refuses`.
- `README.md` (*Grants*) and `CHANGELOG.md` (0.1.0a7, 076's bullet), as the Design says.

### Seen failing first, and against every stand-in

- Before the code (`build/077/seen-failing.log`), with the checks written and the runner and
  the `read` export unchanged: `3 failed, 1 passed`. The walk-model case: "DID NOT RAISE" (its
  first new row, `C:\b\new\COM¹`). The oracle case listed the names that differ: `com¹`,
  `LPT³`, `conin$`, `CONOUT$`, `x*y`, `a\x01` and more. The raw case's control: `assert 0 ==
  2`. The fuzz case passed with the model's change, as it must; its count, 16,653, held.
- `build/077/stand-ins.log` (`build/077/standins.py` edits one file, runs the named nodes and
  restores the file; the `git diff` hash is equal before and after): **S1 to S6 all CAUGHT**.
  - S1 (no superscripts) and S2 (no console names): the walk-model case "DID NOT RAISE", and the
    oracle case lists the differing names.
  - S3 (the export back at 400 and 408): `assert 0 == 2` on the control's count.
  - S4 (the write-only descriptor opened `READ | WRITE`): the read row, `assert 0 == 8`.
  - S5 (no reserved characters): "DID NOT RAISE", and the oracle case lists `x*y`, `a\x01`, `?`.
  - S6 (the stem lower-cased): the oracle case lists `con\u0131n$` and its spellings.

### The judge (no `--accept`)

- Fast tier, `uv run pytest -m "not slow" -n 3` (`build/077/fast-1.log`): `wasi_python v1:
  474/550 pass · 1 gap · 24 blocked · 0 fail · 51 deselected (unit suite 1268/1276, 8
  skipped)`; `ratchet vs 9dad163977: lost 0 · absent 0 · unrun 0 · unrun locally 22 · gained 0
  · grew 1 · upstream unrun 31 · not selected 37 · judge changed:
  tests/unit/test_runner_grants.py`; `1742 passed, 32 skipped, 1 xfailed`.
- Full judge, `uv run pytest -n 3` (`build/077/full-n3.log`, its record
  `build/077/full-n3-latest.json`): `wasi_python v1: 491/550 pass · 3 gap · 56 blocked · 0 fail
  (unit suite 1268/1276, 8 skipped)`; `ratchet vs 9dad163977: lost 0 · absent 0 · unrun 0 ·
  unrun locally 42 · gained 0 · grew 1 · upstream unrun 31 · judge changed:
  tests/unit/test_runner_grants.py`; `1759 passed, 64 skipped, 3 xfailed`. The blocked checks
  are the worktree's missing source trees and clones, as in any worktree.
- **The one growth is not this spec's.** Every run shows some of spec 071's
  `test_recursion_through_python_raises[heapq-plain]`, `[lru-cache-plain]` and
  `[pickle-partial-plain]` above the accepted fuel, by 0.03 to 0.26 %. The count and the values
  differ on each run. In the fast tier it was `pickle-partial-plain`, 247,215,911 → 247,800,861;
  in the full judge, `lru-cache-plain`, 217,073,420 → 217,452,861.
  - I ran the check alone twice on this branch, and twice on a pristine `git archive main` copy
    against the same set. It grew on every run. On main it grew in 2 and then 3 rows, for
    example `heapq-plain` 177,337,468 → 177,599,451 and then → 177,481,847.
  - So these three rows vary from run to run on main itself. 077 changes no guest code, and no
    line those checks reach.
  - Only `-plain` rows grew in these six runs, never their `-snapshot` twins. That fits a hash seed drawn fresh at each
    plain start, where a snapshot has its seed frozen (INFERRED, not tested).
  - Left for the lane (AGENTS.md rule 4: the judge is not this spec's to change).
- `ruff check` and `ruff format --check` on `src` and `tests`: clean. `tests/public_api.txt`:
  unchanged.
- The judge change, for the lane's `--accept-judge`: "spec 077: the raw read row reads two real
  bytes through the iovec at 200, checked by a zeroed control read; the Windows walk model
  refuses the superscript device names, CONIN$, CONOUT$ and the reserved characters, upper-cased
  as CPython does, with a COM0 row; one new unit case pins `_rewritten` to `ntpath.isreserved`
  over 18,275 names".

### On Windows (criterion 6)

**Dry run 1: run 39210847037**, dispatched on `spec/077-verify`.
- Its `headSha` is `70bdf252fc7a78cb4cc792f8587fb37134508c89`, and its only parent is `42795d4`
  (this branch's build, as built).
- The temporary commit was made with `git commit-tree`, with no local branch, and pushed
  straight to `refs/heads/spec/077-verify`, not forced. Its diff (`build/077/verify-commit.diff`)
  changes only `.github/workflows/release.yml`, +1 −1: `-rA` appended to the verify step's first
  command line.
- Verdicts: both `rebuild from the pins` jobs passed. **`build and judge (arm64 macOS)` failed in
  its step "The judge"**, so `verify` on all three systems, `the same bytes from every host`,
  attest and both publishes were skipped.
- The judge's lines (`build/077/dryrun1-failed.log`): `wasi_python v1: 513/550 pass · 3 gap ·
  34 blocked · 0 fail (unit suite 1269/1276, 7 skipped)`; `ratchet vs 9dad163977: lost 0 ·
  absent 0 · unrun 0 · unrun locally 21 · gained 1 · grew 2 · …`; `GREW
  …[lru-cache-plain]: fuel 217073420 -> 217597671`, `GREW …[pickle-partial-plain]: fuel
  247215911 -> 247851144`, `RED: 2 metric(s) grew`; `1782 passed, 41 skipped, 3 xfailed`.
- The throwaway branch was deleted on GitHub after the run (`git ls-remote` shows none).

So no `PASSED` line exists yet from `verify (windows-2025)`, and criterion 6 is open. The
failure is the run-to-run variation above, on main's own checks, not a row of this spec.
Main's next release dry run will meet it too: main's last one, 39203056348, ran before 071
landed. Re-running until the fuel happens to fall is not a fix. The lane ruled to deal with the
variation first: spec 080 (deterministic fuel for 071's recursion checks), built by 071's author.

**The rebase onto `8f8de73`** (spec 080 landed, accepted as `fae6615`). There was no conflict.
The branch's diff against its base is byte for byte the same as before (`git diff 23f1c4f
fd94262` equals `git diff 8f8de73 63d864e`, EXECUTED). Main brought two files under `tests/`,
both 080's and neither this spec's: `tests/checks/test_v1_2_hostile_guest.py` and
`tests/unit/test_runner_async.py`. Nothing under `src/` changed. The tip is now `63d864e` (the
build is `bd81664`).
- Fast tier there, `uv run pytest -m "not slow" -n 3` (`build/077/fast-2.log`): `wasi_python
  v1: 474/550 pass · 1 gap · 24 blocked · 0 fail · 51 deselected (unit suite 1268/1276, 8
  skipped)`; `ratchet vs 7f150e33b9: lost 0 · absent 0 · unrun 0 · unrun locally 22 · gained 0
  · grew 0 · upstream unrun 31 · not selected 37 · judge changed:
  tests/unit/test_runner_grants.py`; `1742 passed, 32 skipped, 1 xfailed`.

**Dry run 2: run 39225762652, every job passed on all three systems.**
- Its `headSha` is `8472a38e0c67b2f7be236298e50c32d5cb04f743`, whose only parent is `63d864e`,
  this branch's rebased tip.
- The temporary commit was made the same way: `git commit-tree`, no local branch, pushed to
  `refs/heads/spec/077-verify`, not forced. Its diff (`build/077/verify-commit-2.diff`) equals
  run 1's: `release.yml` only, +1 −1, `-rA`.
- Verdicts: `rebuild from the pins` (ubuntu-24.04 and ubuntu-24.04-arm), `build and judge (arm64
  macOS)`, `verify (ubuntu-24.04)`, `verify (macos-15)`, **`verify (windows-2025)`** and `the
  same bytes from every host`: success. Attest and the two publish jobs were skipped, as on
  every dry run.
- The Windows step's scoreboard: `wasi_python v1: 223/227 pass · 1 gap · 3 blocked · 0 fail
  (unit suite 95/102, 7 skipped)`, `blocked by: oracle 1 · three systems 1 · wheel 1`, the three
  the next step allows; `318 passed, 10 skipped, 1 xfailed`.
- The four named nodes' lines from `verify (windows-2025)` (`build/077/dryrun2-windows-verify.log`,
  `build/077/dryrun2-windows-passed.txt`). None is skipped, blocked, deselected or missing; the
  oracle case ran on Windows' CPython 3.14.2:

```
PASSED tests/unit/test_runner_grants.py::test_the_windows_walk_takes_dot_dot_on_walked_folders
PASSED tests/unit/test_runner_grants.py::test_the_windows_walk_records_the_true_chain
PASSED tests/unit/test_runner_grants.py::test_a_rewritten_name_is_one_ntpath_refuses
PASSED tests/unit/test_runner_grants.py::test_a_read_only_grant_refuses_raw_writes
```

- The throwaway branch was then deleted on GitHub (`git push origin --delete spec/077-verify`;
  `git ls-remote` shows none). Only this file follows the run, so the code that ran on Windows
  is the code under review (Decision 5, freshness).

## One line

Point the raw read row at a real two-byte buffer and prove it with a zeroed control read, and
make the Windows walk refuse exactly what `ntpath.isreserved` refuses, before anything is made,
run once on Windows with `-rA` on a throwaway branch.

**Landed 2026-10-19** through the lane, after spec 079. The lane rebased the branch onto main
`59b90b6` with no conflict; its diff equals the reviewed diff at `dc35ffd` line for line (EXECUTED,
`build/lane-077/delta.txt`, empty). Because the rebase brought specs 075's and 079's changes under
`src/` and `tests/`, the freshness rule called for a new Windows run: the lane made the same
temporary commit (`-rA`, the diff of `8472a38`) on the rebased tip with `git commit-tree`, pushed it
to the throwaway `spec/077-verify` (`6b604c8`, parent `9f8b3d0`) and ran the release workflow there:
run 39232968343, success on every job on all three systems, with PASSED lines on `verify
(windows-2025)` for `test_the_windows_walk_takes_dot_dot_on_walked_folders`,
`test_the_windows_walk_records_the_true_chain`, `test_a_rewritten_name_is_one_ntpath_refuses` and
`test_a_read_only_grant_refuses_raw_writes` (EXECUTED, `build/dryrun-077-verify2.log`). The
throwaway branch was deleted. The pre-build review with its confirmation and the build review were
committed on the detached HEAD as `961f4b9`. No build: 077 changes `src/`, one unit file and
documents. The full judge, serial: `wasi_python v1: 534/551 pass · 15 gap · 2 blocked · 0 fail (unit
suite 1377/1379, 2 skipped)`, `1911 passed, 4 skipped, 15 xfailed in 1325.64s`, accepted with
`--accept-judge` as `4441f7a`, history line 76; nothing grew (EXECUTED, `build/lane-077-accept.log`).
The rules tier passed (40/40, unpiped); main fast-forwarded only after the Windows run passed.

