# Pre-build review of 087 — the 0.1.0a7 review's guest follow-ups, 2026-10-19

- **Reviewer:** a fresh agent. I wrote none of 087, nor the 0.1.0a7 security review it answers.
- **Under review:** `context/specifications/087-the-a7-reviews-guest-follow-ups.md` on
  `spec/087-the-a7-reviews-guest-follow-ups`, commit `97cc573` over main `a6dfc17` (main is now
  `932bc00`). It is build-class: it carries a second patch to regex (constitution §4.1), so §5.6
  asks for this review, and spec 020, Decision 8 asks it to read the patch and its facts sheet.
- **Read:**
  - the spec in full; `context/upstream/24-regex-timeout-ticks/` (`fix.patch`, `pr.md`, every
    file in `evidence/`); `context/research/2026-10-19-the-a7-guest-follow-ups/` (every script and
    output); the a7 security review's F2, F3, F4 and addendum;
  - regex 2026.9.29's `src/_regex.c` from the pinned tarball (SHA-256 `8b5fcc47…`, checked): every
    line that names `timeout`, `tim`, `clock`, `CLOCKS_PER_SEC`, `start_time`, `RE_NO_TIMEOUT`,
    and every caller of `decode_timeout`, `state_init`, `state_init_2` and `pattern_subx`;
  - in the judge: `tests/harness/guest.py` (`run`, `clock_time_get`, `clock_res_get`,
    `trap_cause`, `engine`), `tests/checks/conftest.py` (`guest`), `tests/checks/test_v1_3_lxml.py`
    (`_grants`, `FILES`, `FILES_WANT`), `tests/checks/test_v1_3_regex.py`,
    `tests/checks/test_v1_2_hostile_guest.py` (071's recursion checks and `LIMITS`),
    `tests/checks/test_rules.py` with `tests/harness/scan.py` (`clock_hits`, `patch_errors`,
    `_draft_errors`), `tests/unit/test_guest.py`, `tests/harness/wat.py`;
  - `scripts/assemble_artifacts.py` (`MODIFIED`, `modified_notice`), `scripts/steps/53_regex.sh`,
    `scripts/steps/60_link.sh`, `recipes/reactor_main.c`'s clock wrapper;
  - main's README at `932bc00` (the regex, *Deep recursion*, *lxml in the guest* and *From any
    language* step 4 text), and spec 078's step 4 rewrite and its 087 paragraph (`fb41ed4`).
- **How I ran things:** in the scratch folder only, on a fresh `cp -Rp` copy of
  `build/sets/s-c50ca51fae5eb55b-c9dcb5b8` (33 files, `shasum -c` passed; the copy's zip has one
  link). I unpacked the pinned regex into a scratch git tree, applied 0001, then `fix.patch`,
  compiled with `scripts/wasi-cc` and step 53's flags, and relinked with step 60's own command
  (`build/link/reactor-commands.txt`, line 3) with only the archive, map and output paths changed.
  Nothing in `build/` was written (checked with `find -newer`). Guests ran through the judge's
  driver with `uv run --project <repo> python -I`. My scripts are in `scripts/` and their
  outputs beside this file. I touched no git tree.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED** (reasoned, not run).

## Short version

The patch is right, small and complete. The timeout check counts operations, fails today and
passes after. F2's facts reproduce, natively too. F4's depths all hold on the engine they name.
Declining the `xsltMaxDepth` recipe is right.

But four of the checks would not run green as written. Each is a few words to fix in the spec:

- **F1.** Check 4 asserts `trapped == "stack overflow"`. On the driver's `own` path a stack
  overflow reads "error while executing at wasm backtrace:". The cause line is
  "wasm trap: call stack exhausted" (EXECUTED).
- **F2.** Adding `ent.xsl` to `_grants` changes an existing check's expected output and fuel:
  `test_files_by_path_in_grants` prints the sorted listing of `/ro` (READ).
- **F3.** The rules check `test_no_test_reads_a_clock` flags `time.monotonic_ns()` in any string
  under `tests/checks` and `tests/unit`. Check 1's program and check 5 both use it (EXECUTED).
- **F4.** The predicates row's fallback cannot work at 4,950. With room, libxml2 completes 5,000
  chained predicates and raises from 5,001 (EXECUTED).

And five smaller ones (F5 to F9), plus two for the facts sheet and the accepting lines (F10,
F11).

## 1. The patch (F3 of the a7 review)

**It reproduces (EXECUTED).** I rebuilt `_regex.c` with 0001 alone. It equals
`build/regex-build/_regex.o` byte for byte. Relinked, the `python.wasm` equals the set's
(`ab78e893…`). So the scratch build is the real one. With `fix.patch` on top:

- `git apply` takes it with no offset;
- step 53's flags give 0 warnings;
- `python.wasm` is 41,099,863 bytes, `5f8d1b29…`: exactly the author's, 202 bytes larger.

**No narrowing is left (READ and EXECUTED).**

- **Every carrier moved (READ).** I listed every `Py_ssize_t` that holds ticks. They are
  `RE_State.timeout`, `decode_timeout`'s return, the `timeout` parameters of `state_init_2`,
  `state_init` and `pattern_subx`, and nine `tim` locals (lines 21103, 21503, 21560, 22148,
  22179, 22210, 22241, 22272, 22399). The patch changes all of them.
- **Nothing else carries ticks.** `start_time` is already `clock_t`. `_regex.h` holds no timeout.
  No other call site passes one.
- **The compiler agrees (EXECUTED).** I compiled with `-Wall -Wextra -Wconversion
  -Wshorten-64-to-32 -Wfloat-conversion -Wimplicit-int-float-conversion`. 0001 alone and 0001 plus
  0002 give the same 164 warnings, line numbers aside. So the patch adds none. A narrowing left
  behind would show as a new `-Wshorten-64-to-32` warning on wasm32.

**Overflow is handled (READ).**

- `(double)LLONG_MAX` rounds to 2^63. Every double below it converts to `long long` exactly. So
  "ticks ≥ 2^63 means no timeout" removes the only undefined conversion.
- `inf` meets `>=`. NaN fails `value >= 0.0`. Both mean no timeout. So does any negative value.
  `-0.0` gives 0 ticks and fires at once, as before.
- The elapsed time, `clock() - start_time`, is `clock_t`. Casting it to `long long` widens it or
  keeps it. On wasm32 it is 64-bit nanoseconds, good for 292 years. `clock()`'s error value, −1,
  still never fires, as before.
- `LLONG_MAX` comes from `<limits.h>`, which `Python.h` includes. So MSVC and glibc builds have it.

**It is minimal.** It is one typedef with its comment, the type changes, one cast and one guard.
It changes no API and no pickled form. Widening only the stored timeout would leave the
comparison 32-bit, so nothing smaller works.

**The facts sheet meets §4.1 (READ).**

- **The header.** `pr.md`'s six lines match `DRAFT_FIELDS` and `STATUS`. `Files: src/_regex.c`
  is what the patch touches.
- **The licence.** The `MODIFIED` line is Decision 2's, and `modified_notice` writes a second
  line from it.
- **The MANIFEST.** It hashes each patch as a recipe line, as the set already does for 0001.
- **The CHANGELOG.** Decision 8's text names the patch's path, which `patch_errors` requires.
- **The README count** goes from 7 to 8.
- **The folder number.** 24 is free on main and on every open branch (037 has 21 to 23, 078 has
  21, 085 has 21 and 22). One accuracy point for the sheet is F10.

**Its behaviour (EXECUTED, my check 1 run, `check1.out`):**

| `timeout=` | the set's plain binary | the 0002 relink | the set's snapshot |
|---|---|---|---|
| `0` | TimeoutError, 6 ms | the same | the same |
| `2.0` | TimeoutError, 2.004 s | the same | the same |
| `3` | **completed, 4.658 s** | **TimeoutError, 3.004 s** | **completed, 4.658 s** |
| `1e9` | completed | completed | completed |
| `1e13`, `inf` | completed, 4.658 s (clock read) | completed, 2 ms (no clock read) | completed, 4.658 s |

**Fuel elsewhere does not move (EXECUTED, `fuel_compare.out`).** On the 0001 and 0002 relinks:

| run | fuel, both relinks |
|---|---|
| `-c pass` | 167,481,449 |
| check `FIVE` | 445,139,578 |
| check `PICKLE` | 468,862,262 |
| the `regex_features` job | 603,192,551 |

No existing check uses `timeout=`, and regex's own suite has no timeout test (READ).

## 2. The timeout check and `clock_step_ns`

- **It counts operations (READ, EXECUTED).** The driver answers `clock_time_get` from a counter.
  regex reads `clock()` when its `uint16_t iterations` wraps, which is every 256 steps (lines
  11917 to 11919). So "3 s at 2 ms per read" means 1,500 reads, a fixed count of steps. The search
  needs 4.658 s, 2,329 reads, so `timeout=3` has 55% of room on the far side. A toolchain change
  (086) does not move it, since the read count is algorithmic.
- **It fails today and passes after (EXECUTED).** See the table above. On both released binaries
  `timeout=3` runs to the end. With 0002 it raises at 3.004 s.
- **`clock_step_ns` is sound (READ).** The guest fixture already passes keywords through. The
  default keeps today's step, so no other check's fuel moves. Nothing in `tests/` monkeypatches
  `CLOCK_STEP_NS`. Only `test_regrtest.py` reads it, and only to compare with
  `CLOCK_RESOLUTION_NS`. `Turns` has no clock of its own. But F3 (the program's text) and F9 (the
  stated resolution) need words.
- **I ran the guest program with its clock read assembled.** It calls
  `time.clock_gettime_ns(time.CLOCK_MONOTONIC)`. The step it measured was exactly 2,000,000 ns.

## 3. F2's checks against the README's two sentences

**The facts reproduce (EXECUTED, `f2.out`, snapshot binary, check 2's layout).** I granted `/ro`
read-only, holding `ent.xsl` (an entity on `/ro/secret.txt`) and `secret.txt`. For both
`xsl:import` and `xsl:include`, under `DENY_ALL`, the output holds `SECRET` in five cases:

- a `file:` href;
- `ent.xsl` with `base_url="file:///ro/main.xsl"`;
- `/ro/ent.xsl` with `base_url="/ro/main.xsl"`;
- a `main.xsl` parsed from the grant by path;
- `XSLTAccessControl(read_file=False)`.

An absent file raises `XSLTParseError`, "Cannot resolve URI file:///ro/none.xsl".

- **Native lxml does the same (EXECUTED, `native_f2.out`):** lxml 6.1.3 with libxslt 1.1.43 in
  the oracle venv prints `SECRET` for both, under `DENY_ALL`.
- **A refusing resolver stops every case that otherwise loads (EXECUTED).** The resolver's
  exception carries the URL.
- **The mutants bite (EXECUTED).** An `ent.xsl` without the entity prints `none`, not `SECRET`. A
  resolver that returns `None` lets every load through.

**The probe is faithful about base URLs, with one hole (F5).** The author's table already
separates the `file:` href and the base-URL forms. It shows that an absolute href with no base URL
fails anyway (`string://__STRING__XSLT__/ro/ent.xsl`). But check 3 lists an "absolute" case, and
the probe ran that case with no base URL. There the resolver refuses a URL ("ro/ent.xsl") that
would never have loaded, so that row proves nothing.

**A nuance for the README's remedy (EXECUTED, `f2_file_parse.out`).** What happens depends on how
the stylesheet is parsed through the refusing parser:

| parse | result |
|---|---|
| by path, `etree.parse("/ro/main.xsl", p)` | refuses the stylesheet itself (`/ro/main.xsl`) |
| from an open file object | compiles; refuses the import (`/ro/ent.xsl`) |
| from bytes with a `base_url` | compiles; refuses the import (`/ro/ent.xsl`) |
| from bytes with no base | compiles; refuses the import (`ent.xsl`) |

So the remedy fails closed, but a reader who parses by path gets an error, not a working
stylesheet. This is optional wording, folded into F5.

## 4. F4's checks

**Every depth holds on the named engine (EXECUTED, `f4_defaults.out`, `f4_must_not_trap.out`).**
The engine was `wt.Engine(wt.Config())` (512 KiB, no fuel, no epochs), the snapshot, through
`driver.run(…, own=…)`.

- **The trap rows.** Each "completes at" printed `ok`. Each "traps at" trapped. The next call
  printed `ok`. This held for all seven rows: parens 260/640, predicates 3,000/4,950,
  call-template 340/700, copying apply-templates 330/680, C14N 1,100/2,100, RelaxNG 290/660, and
  traceback freed 2,000/4,200.
- **The must-not-trap rows.** Recursion 20,000 deep under a raised limit printed `ok 20000`.
  `set_global_max_depth(250)` gave `XSLTApplyError` for call-template, the copying
  apply-templates and the heavy template, with no trap.

**But the trap is not named "stack overflow" on this path (F1).** The driver takes the first line
of wasmtime's message, which is its heading. The runner names the trap, and 071's checks assert
through the runner. The author's bisection (`f4_own.py`) accepted any trap, so it never saw this.

**Is a 512 KiB default engine a faithful stand-in?** For a drift guard, yes. For the README's
numbers, only loosely (F7).

- **What it shares (READ).** It has the same binary, the same 512 KiB, and the same shapes. Every
  edge moves the same way when frames grow.
- **Where it differs.** It has no epoch checks, so it has the most room. Its edges are 4% to 35%
  above the runner's unmetered ones (parens 500 against 373). The README states the runner's
  numbers.
- **After 078.** 078 moves the list "unchanged" into step 4, for an embedder who keeps 512 KiB.
  That is this engine, but the numbers are the runner's. Check 4 then holds depths the README
  does not state.

**The margins on x86-64 (INFERRED from 071's measured 0 to 29% larger x86-64 frames).**

- **The "traps at" depths.** Larger frames lower every edge, so these only get safer.
- **The "completes at" depths.** Each needs the x86-64 edge on this engine above it. The
  arm64 edge over 1.29 is still above every one. The thinnest is predicates (4,644 / 1.29 ≈
  3,600 against 3,000, a fifth of room). Next come C14N (1,263 against 1,100) and call-template
  (405 against 340).
- **The re-measure.** The builder's linux/amd64 run (criterion 6) is the right gate.

**The tight predicates row (EXECUTED, `f4_xpath_limit.out`, a 2 MiB engine).** libxml2 finished
`a[1]…` with 4,950, 4,999 and 5,000 predicates. From 5,001 it raised "XPathEvalError: Recursion
limit exceeded".

- **So at 4,950 a host with room completes.** It neither traps nor raises.
- **The spec's fallback misses.** It asserts "traps or raises" at the same depth, so it fails on
  exactly the host it is for (F4).

**078 and 086 restate it cleanly (READ).**

- **078.** Check 4 runs its own engine, never `run`, so 078's 8 MiB does not touch it. 078's
  10 MiB thread only adds room above a 512 KiB `max_wasm_stack`.
- **086.** It recompiles the guest and re-measures the table. The 25% rules leave room, except
  for predicates (F4).

The merges in `guest.py` and `test_v1_2_hostile_guest.py` are textual. 083 also edits
`guest.py`, which Decision 9 does not name. That merge is textual too.

**Two coverage points.**

- **The `apply-templates` sentence (F6).** Main's README (932bc00) now also says "about 670 with
  one that only applies templates", and no row of check 4 holds it.
- **The shared module (F8).** "One module compiled per judge run" does not hold for parametrized
  rows under `-n 6`. The plugin allows only `--dist load`, so each worker compiles its own: seconds
  and about a gigabyte each.

## 5. Declining the `xsltMaxDepth` recipe

Right. `etree.XSLT.set_global_max_depth` exists, and I confirmed it works on this engine
(EXECUTED, above). After 078, `run` stops at libxslt's own 3,000 before any trap, so a lower
default would refuse templates that work natively. It would help only embedders at 512 KiB, who
can make the call.

One wording point. The README sentence "makes deep templates raise `XSLTApplyError` instead" was
measured on three template shapes. A template with much heavier C frames per level could still
trap before 250 (INFERRED). "Templates like these" or "deep templates in practice" is more
exact. This is optional.

## 6. The accepting reasons

- **`--accept-judge`.** It names the new checks and the driver keyword. It holds if F2 is fixed
  by giving checks 2 and 3 their own grant. If instead `FILES_WANT` changes, the reason must name
  that edited expectation (F11).
- **`--accept-growth`.** It says the snapshot grows "about +200 bytes". That was not measured:
  `relink.txt` says the snapshot was not rebuilt. The builder restates it with the measured
  number, as criterion 5 asks. The rest holds: the plain binary grows 202 bytes, and I found no
  per-check fuel the patch moves.

## Findings

### F1. Check 4's trap assertion fails on the driver's `own` path. Medium; write in (EXECUTED)

On `driver.run(…, own=(engine, module))` a stack overflow gives:

- `trapped == "error while executing at wasm backtrace:"`;
- `trap_cause == "wasm trap: call stack exhausted"`.

It never gives "stack overflow". That name is the runner's (`test_a_stack_overflow_is_named`).
Write check 4 to assert `(r.exit_code, r.trap_cause) == (None, "wasm trap: call stack
exhausted")`. Or make the driver name a trap by its code, which is a judge change with its own
reason. Say which.

### F2. `ent.xsl` in `_grants` moves an existing check. Medium; write in (READ)

`test_files_by_path_in_grants` prints `sorted(os.listdir("/ro"))`. Its `FILES_WANT` expects
`['d.dtd', 'doc.xml', 'ent.xml', 'inc.xml', 'secret.txt']`. Adding `ent.xsl` breaks that line and
changes its fuel. That contradicts *The judge's changes* ("the folder listing is not part of its
program").

The fix: give checks 2 and 3 a grant of their own, a second folder or an `extra=` argument to
`_grants`, so no expectation or recorded fuel moves.

### F3. The clock scanner refuses `time.monotonic_ns()` in a check's text. Medium; write in (EXECUTED)

`test_no_test_reads_a_clock` scans every line of `tests/checks` and `tests/unit`, strings
included, for `time.monotonic(_ns)`. Check 1's program as executed (`f3_check.py`) would turn the
rules check red, and so would check 5 as worded. Editing the scanner would weaken the judge.

The fix:

- **check 1:** have the guest read `time.clock_gettime_ns(time.CLOCK_MONOTONIC)`. It is not
  flagged, and it gave the same 2 ms step and the same verdicts (EXECUTED);
- **check 5:** write it as a WAT probe that calls `clock_time_get` twice, beside `CLOCK_PROBE` in
  `tests/harness/wat.py`, as the driver's other unit checks do. It then needs no artifact.

### F4. The predicates fallback needs a depth above libxml2's 5,000. Medium; write in (EXECUTED)

With room, 5,000 chained predicates complete and 5,001 raise `XPathEvalError`. So on a host whose
stack edge passes 4,950, the check at 4,950 completes. The fallback "traps or raises
`XPathEvalError`" must use a deep depth above 5,000, say 5,500.

Say also that 086's re-measure triggers the same fallback. Its margin (6.6%) is the only one
under the spec's own 25% rule.

### F5. Check 3's absolute-href case must carry a base URL. Low; write in (EXECUTED)

With no base URL the load fails without any resolver ("Cannot resolve URI
string://__STRING__XSLT__/ro/ent.xsl"), so refusing it proves nothing. Use
`base_url="/ro/main.xsl"`. That load succeeds under `DENY_ALL` without the resolver, and the
resolver refuses `/ro/ent.xsl` with it.

State the URL each case expects in the exception: `file:///ro/ent.xsl`, `file:///ro/ent.xsl` and
`/ro/ent.xsl` respectively.

Optional: the README's remedy may add "parse it from its bytes or an open file". Parsing by path
through that parser refuses the stylesheet itself.

### F6. Rebase on 932bc00: the two README rows are in; hold the third sentence. Low; write in (READ)

The lane has already put Decision 5's two corrections into main's README. Decision 5's "wrong in
the README today", Decision 8's matching edits and *The owner's choices* item 2 are done. Restate
them as landed.

Main's README now also says "about 670 with one that only applies templates". Add check 4's
`xslt-apply-bare` row to hold it. From the author's edges (defaults 740, runner unmetered 677,
metered 663), the depths are about 490 to complete and 930 to trap.

### F7. Say which engine step 4's numbers describe. Low; write in (READ, INFERRED)

Check 4 measures the bare defaults engine. Its edges are 500, 4,644, 523, 509, 1,629, 516 and
3,259. The README gives the runner's: about 375, 4,600, 480, 470, 1,500, 430 and 2,700. Once 078
moves the list to step 4, one clause keeps the two honest: "with fuel or epoch interruption on;
up to a third deeper without". Or state the defaults column. Decision 8 or 9 should say which.

### F8. Name how check 4 shares its module, and its tier. Low; write in (READ)

Under `-n 6` (`--dist load` only), parametrized rows compile one module per worker. Either loop
the rows in one test, as 071's default-engine check does, or say "one module per worker". Say
whether it is fast or slow tier.

### F9. `clock_res_get` keeps 1 µs when the step is 2 ms. Low; write in (READ)

This is harmless to regex. But the docstring should say the stated resolution does not follow
`clock_step_ns`, or make it follow. A reader of `time.get_clock_info` would otherwise be misled.

### F10. The sheet's case against `clock_t` applies to `long long` too on 32-bit glibc. Low; write in (READ, INFERRED)

There, `clock_t` is a 32-bit `long`, so the elapsed ticks wrap past 2^31: about 2,147 s, or 36
minutes, at 10^6 a second. With the patch a timeout above that still cannot fire. It now never
fires, where x86 fired at once.

`pr.md` says `clock_t` "would … fix nothing on 32-bit Linux", which reads as though `long long`
does. Say plainly what changes there. The argument for `long long` still stands on Win64, where
`clock_t` would narrow a 64-bit field.

### F11. The accepting lines: measure the snapshot, and name any edited expectation. Low; write in (READ)

See section 6.

## Notes

- **N1. What I could not run.** linux/amd64 edges are the builder's (criterion 6). The release's
  Windows job judges Windows. 078's driver is not landed, and Decision 9 already asks for one run
  on it if it has.
- **N2. The patch's comment** says why in three lines. Upstream may prefer `int64_t`. `long long`
  is fine and needs no new header.
- **N3. The native x86-64 claim** (`timeout=1e13`, `1e30`, `inf` raise at once) agrees with
  `cvttsd2si`'s `INT64_MIN` against the code (READ). I did not re-run the container.

## Verdict

**Ready once F1 to F5 are written in, and the spec is rebased on main per F6.** F7 to F11 are
small words that can be written in at the same time. All of them are spec text. No decision
changes.

The patch is correct, complete and minimal, and I reproduced it byte for byte. The timeout check
counts clock reads, fails on both released binaries and passes on the patched one. F2's facts
hold, natively too. Every depth in F4's table holds on the engine it names. Declining the
`xsltMaxDepth` recipe is right.

## One line

The regex patch is right and the timeout check bites. Fix four check details before building:
the `own` path's trap name, a grant of check 2's own, no `time.monotonic_ns` in check text, and a
predicates fallback above libxml2's 5,000.

## Confirmation (2026-10-19)

- **Under review:** the revision `ee53bad` on `spec/087-the-a7-reviews-guest-follow-ups`, rebased
  onto main `932bc00` (the draft is now `c421835`). I read `git diff c421835..ee53bad` (the spec
  and `pr.md`) and the revised spec's *Disposition of the pre-build review*.
- **How I ran things:** the same scratch folder, a fresh `cp -Rp` of the set (33 files,
  `shasum -c` passed, removed afterwards), and my `scripts/f4.py`. No pytest run: the lane's
  serial judge was running.

**The rebase and the patch (READ).**

- `932bc00` is an ancestor of `ee53bad`.
- The branch, compared with main, only adds files, all under `context/`.
- `fix.patch` is untouched: SHA-256 `9da893d0…`.
- `pr.md` changes only the folder-number sentence and the 32-bit text.

**Each finding (READ, and EXECUTED where marked):**

| finding | as written in | holds? |
|---|---|---|
| F1 | Check 4 asserts `(r.exit_code, r.trap_cause) == (None, "wasm trap: call stack exhausted")`. The driver is not changed. | yes |
| F2 | Checks 2 and 3 get their own grant from a helper beside `_grants`. `_grants`, `FILES_WANT` and the recorded fuel are unchanged. | yes |
| F3 | Check 1 reads `time.clock_gettime_ns(time.CLOCK_MONOTONIC)`. Check 5 becomes two WAT probes. The scanner is untouched. | yes |
| F4 | The fallback's deep depth is 5,500. 086's re-measure triggers it too. EXECUTED: on the defaults engine 5,500 traps with the cause above. On a 2 MiB engine libxml2 raises from 5,001 (`f4_xpath_limit.out`). | yes |
| F5 | The three forms carry their base URLs and expected URLs, which match `f2.out`. The no-base form is used by no check. The README note is added. | yes |
| F6 | Rebased. Decision 5's corrections are restated as landed, and the owner's choice is gone. The bare `apply-templates` row is 490 / 930, and both obey the rules (74% of 663; 126% of 740). EXECUTED: 490 printed `ok`; 930 trapped with "wasm trap: call stack exhausted" (`c_f4_bare.out`). | yes |
| F7 | The README gains one clause saying its numbers are the runner's, with epochs on. In step 4 once 078 has landed. | yes |
| F8 | Check 4 is one fast-tier test. It compiles once and loops the rows, as 071's does. | yes |
| F9 | `clock_res_get` answers the run's step for clocks 0 and 1. | **see C1** |
| F10 | `pr.md` and Decision 2 say plainly that 32-bit glibc keeps its wrap at about 2,147 s, and that the case for `long long` rests on Win64. | yes |
| F11 | `--accept-growth` takes the builder's measured bytes for both binaries. `--accept-judge` names any edited expectation, and none is edited. | yes |
| optional points | "templates like these"; the 083 merge is named. | yes |

The `--accept-judge` reason names the grant, the keyword, the resolution and the probes. It
still holds.

### C1. Say that F9's resolution follows the step only when the keyword moves it. Low; write in (READ)

`tests/checks/test_v1_2_portable_and_sealed.py::test_the_guest_clocks_resolution_is_the_judges`
(spec 065's guard) monkeypatches `CLOCK_RESOLUTION_NS` to `{0: 7_000, 1: 11_000, …}`. It runs at
the default step and expects the guest to see 7,000 and 11,000.

The revised text has `clock_res_get` "answer that step for the realtime and monotonic clocks".
Taken literally, that makes this guard print 1,000 three times, and it fails. Fixing it by editing
the guard would weaken the judge. Decision 3's "at the default nothing changes" points the right
way but names only `test_regrtest.py`.

Write one sentence: "clock_res_get reads `CLOCK_RESOLUTION_NS` as today, and answers the step for
clocks 0 and 1 only when `clock_step_ns` differs from `CLOCK_STEP_NS`", or an equivalent rule,
and name the 065 guard as unchanged. My F9 caused this. Dropping the resolution change and
keeping only a docstring would also close it.

**Verdict: ready once C1.** It is one sentence of spec text. Every other finding, and the
optional wording, is written in as I asked, and no decision moved. The two new numbers (490 / 930
and 5,500) behave as stated on the engine they name.

### One line

The revision takes all eleven findings faithfully. One sentence remains: keep the resolution at
`CLOCK_RESOLUTION_NS` unless the step is moved, so spec 065's guard stays green.

**C1 in, at `d9769d4`: ready to build** (READ). The units are consistent, not a slip: both WAT
probes return microseconds, like `CLOCK_PROBE`, which divides by 1,000. So a 2 ms step, 2,000,000
ns, reads 2,000, and the default 1,000 ns reads 1. Both fit `run`'s i32 result.
