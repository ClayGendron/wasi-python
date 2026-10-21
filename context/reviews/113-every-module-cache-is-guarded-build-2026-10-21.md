# Review of 113 — every module cache is guarded (the build)

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent (Claude), not the author; it wrote no part of 113, its pre-build
  review or the 0.1.0 security review.
- **Reviewed:** `git diff 1875d4cd e4f0252c` (code `a891dec5`; `e4f0252c` adds the landing
  notes, `context/` only: `git diff --stat a891dec5 e4f0252c -- src tests` is empty), on
  `review/113-build`.
- **Time box:** 60 minutes (the caller's; runner code and a security fix). Used: about 35.
- **Run:** the builder's **39624848889**, on the exact code commit `a891dec5`, read back; no new
  dispatch (AGENTS.md rule 8, the owner 2026-10-20).
- **Re-ran** (EXECUTED; outputs under `build/113r/` in this worktree):
  - `gh run view 39624848889 --attempt 2 --json jobs`: head `a891dec5`, conclusion success;
    **40 success, 3 skipped** (attest, publish, PyPI, as on every dry run).
  - `gh run download 39624848889 -n release-record-2`: scoreboard **797/889 pass · 85 gap ·
    7 blocked · 0 fail**, unit suite 4826/4856 (30 skipped), three systems darwin linux win32 on
    `d4192605…`, set `d0d91cef`.
  - The Windows own-runner leg's log (job 119340423772): `tests\unit\test_runner_module_caches.py`
    prints 32 + 2 = **34 dots, no `s`**; its ratchet line "lost 0 · absent 0 · unrun 0 · gained 0
    · grew 0", judge changed in `tests/release_shards.toml` and the new file only.
  - The rules checks by node id (line ceiling, module-level lock, module-level mutable, private
    API, the platform chosen once, `src/` and code outside it naming no `context/`, the seam
    allowance, eighty lines, names bound twice) and `tests/unit/test_runner_package.py`:
    **14 passed**.
  - `ruff check`, `ruff format --check` (src, tests), `mypy src`: clean.
  - `git diff 1875d4cd e4f0252c -- tests/checks tests/known_gaps.toml tests/upstream
    context/progress tests/public_api.txt`: **empty**.
  - The probe `p50_cwasm_plant.py`, copied to `build/113r/probes/`, against
    `WASI_PYTHON_ARTIFACTS=…/build/artifacts` (`SHA256SUMS` `d0d91cef`): step 0 compiled 1,
    written 1; **step 1 `ValueError: grants[0] at /c is writable and holds the module cache
    $WASI_PYTHON_CACHE names (…/fixtures/p50/xdg/wasi_python)`**; step 2 exit 0, **compiled 1,
    loaded 0, written 1** (`p50-built.log`). Its 471 MB of fixtures deleted after.
  - My own route, judge level only (`build/113r/route/dotdot.py`, `dotdot.log`; the guest runs
    `pass`): finding M1.
  - The fast tier, `-n 3`, with the slot (`build/slots/fast` made, no `build/lane.lock`,
    released at its end): **2,698 passed, 51 skipped, 0 failed** in 10 min 32 s; `643/889 pass ·
    0 gap · 42 blocked · 0 fail`, unit suite 2055/2064; ratchet lost 0, absent 0, unrun 0,
    gained 0, grew 0 (`fast-tier.txt`), the builder's counts on `a891dec5`.

## Acceptance criteria against evidence

1. **The plant is refused, in every caller** — met. The eighteen `[caller-own-victim]` rows and
   the two at/inside rows green on three systems in run 39624848889 (EXECUTED, the Windows log's
   34 dots; the record's 0 fail); seen failing first on `1875d4cd` per
   `build/113/checks-on-main-1b.txt` (READ in the landing notes; I did not re-run main). Each
   asserts `NAMED[victim]` is in the message (READ).
2. **Every default is judged** — met. The method row and the six `fallback` rows green on
   three systems (EXECUTED, the run); `_Posix.default_cache_dirs` adds the `pwd` home and the
   unset-override default (READ, `_platform.py`).
3. **The path as written** — met for the spellings the rows try; **not met for every
   spelling**: a `..` after a link drops the link's folder from the chain (M1). The two link
   rows ran on Windows, unskipped (EXECUTED).
4. **A root still to be made over or inside a cache still to be made** — met (EXECUTED, the
   run; READ, `_judge`'s `missing` rule and the row's three roots).
5. **No home is not a failure** — met (EXECUTED, the run). `_home()` catches `RuntimeError`,
   `KeyError`, `OSError`; `_cache_dir(None)` with no home is `None`, so memory only (READ).
6. **The modes on POSIX** — met (EXECUTED, the run); the Windows branches record "loaded 1"
   (READ).
7. **No verdict moves but the claim list's** — met. No file under `tests/checks/` changed
   (EXECUTED, empty diff); the record has 0 fail and the ratchet lost 0 on every leg I read.
8. **Links, second names, folders** — met (EXECUTED, the run; the junction row ran on Windows).
9. **The probe on the built tip** — met (EXECUTED by me, above).
10. **Existing caches still load** — met in the run (the two embedding checks are in the
    record's passes; READ the builder's `existing-built.txt` claim). `private()` asks for
    `0700`/`0600`, which is what the runner has always written (`mkdir(mode=0o700)`,
    `mkstemp`, `os.replace`; READ).
11. **Not structural, measured** — met, with two numbers off (L1). EXECUTED: `_platform.py`
    1,464, `_places.py` 583, `_engines.py` **321** (notes: 318); `_judge` 52, `_runtime_folders`
    48, `_walk_grants` 38, `_module_miss` **41** (notes: 38), `_load` 26, `_store` 27,
    `_cache_chain` 23, `_Posix.private` 18, `_Windows.private` 14; `LONG_FUNCTIONS` and
    `SEAM_ALLOWED` unchanged (no diff under `tests/checks/`); no `sys.platform`, `os.name` or
    `platform.system()` added outside `_platform.py` (EXECUTED, grep of the diff).
12. **README and CHANGELOG** — met. The Safety bullet, the cache paragraph, both `cache_dir`
    lines (through the docstrings and `api.py --write`) and the *Not protected* text are in;
    the CHANGELOG line is under `## 0.1.0a8 — unreleased` (READ). Criterion 12 says "the two
    *Not protected* items" while Decision 5 quotes one paragraph holding both clauses and the
    README adds that one paragraph; the substance is all there (L4).
13. **`tests/public_api.txt` unchanged; lint, format, types; no code file names a spec** — met
    (EXECUTED).
14. **The dispatch** — met (EXECUTED, read back above; attempt 1's macOS DNS failure came
    before any check, and attempt 2 changed nothing).

## Findings, most severe first

1. **M1 (Medium). A `..` after a link in a cache's path drops the link's folder from the
   judged chain** (`src/wasi_python/_places.py`, `_cache_chain`, the line
   `written = Path(os.path.abspath(path))`). `os.path.abspath` collapses `..` by spelling. The
   OS walks the path through the link and then climbs from the link's target. So the folder
   that holds the link is not among the prefixes judged.
   Failure (EXECUTED, `build/113r/route/dotdot.log`): with `work/a/link -> work/x/y`,
   `$WASI_PYTHON_CACHE=work/a/link/../../c` and `cache_dir=False`, a writable
   `Grant(work/a, "/c")` **passes** (exit 0); the same with one `..` is refused. A guest with
   that grant can replace `link`, the component the OS walks, and so choose where a later call's
   cache resolves. Decision 1 and the README promise "by every folder on its path as written,
   links included". The input is trusted and unusual. On POSIX the `0700` folder check still
   refuses a folder a guest makes under the usual umask. On Windows only the rule guards.
   **Fix:** take the prefixes from `Path(path).absolute()` (pathlib keeps `..`) instead of
   `os.path.abspath`, so each prefix's `identity_of` is the folder the OS reaches; then the
   folder holding `link` (the prefix `work/a`, and `work/a/link` itself) is in the chain. Add a
   row beside `test_a_cache_reached_through_a_link_in_a_writable_grant_is_refused` with the
   two-`..` spelling, seen failing first. Evidence that closes it: that row green on three
   systems.
2. **L1 (Low). Two sizes in the landing notes are off** — `_engines.py` is 321 lines, not 318,
   and `_module_miss` 41, not 38 (EXECUTED, `wc -l` and `ast` on `a891dec5`). Both stay far
   under their ceilings. **Fix text** for *The sizes*: "`_engines.py` | 236 | 321" and
   "`_module_miss` 41".
3. **L2 (Low). One race still fails the call** (`_engines.py`, `_load`). `_load` takes its own
   `os.lstat` and then calls `private(cwasm)`, which takes another and does not catch
   `OSError`. A file removed between the two raises `FileNotFoundError` out of `_module_miss`,
   against Decision 3's "no state of the cache folder makes a call fail". **Fix:** wrap the
   `private(cwasm, is_dir=False)` call in `try`/`except OSError: return None, False`.
4. **L3 (Low). A cache folder that cannot be made or read is now silent** (`_engines.py`,
   `_module_miss`, `except OSError: cwasm = None`). The builder's difference 4 turns a raise
   into memory only, which is right, but with no warning, while difference 3 warns for a file
   that cannot be written. No refusal is lost (the judge's `ValueError`s are raised in
   `_walk_grants`, before `_module`, and neither `except` can catch them; READ). Only the
   embedder's signal that the cache is unused is lost. **Fix:** warn there as `_store` does,
   "not using the module cache at …: <strerror>".
5. **L4 (Low). The `lstat` compare narrows the swap window; the docstring says it closes it**
   (`_engines.py`, `_load`'s docstring: "a file swapped in between is discarded"). The stamp is
   `(st_dev, st_ino, st_size, st_mtime_ns)` of the name before and after the load, so a
   swap that is undone before the second `lstat` is not seen. Decision 3 itself says it
   "narrows a window only a guest the rule failed to stop can use"; the code comment should
   say the same. **Fix text:** "…and whether the file at that name is still the one checked
   once wasmtime has read it, which narrows, not closes, the window between the check and the
   load". Also in criterion 12's wording: "the *Not protected* paragraph" for "the two items".
6. **Note, no fix asked.** Windows `private()` checks the kind, reparse points and the name
   count only, and the README says so; the protected access list is reserved after 0.1.0 with a
   roadmap line, as the pre-build review agreed. The Windows leg ran every row.

## The builder's five differences from the specification's text

1. `_judge`'s `missing` carries the deepest existing ancestor — **acceptable**: the rule needs
   it, and the label cannot carry it; `_judge`'s 3-tuple `runtime` and its positional
   signature are unchanged, so `tests/unit/test_runner_grants.py` stands.
2. The `cache_dir` lines through the docstrings and `api.py --write` — **acceptable**: that is
   how the README's API block is made; `tests/public_api.txt` is unchanged (EXECUTED).
3. A cache write error warns and keeps the module in memory — **acceptable and safe**: it
   catches `OSError` only, deletes the temporary file, re-raises anything else, and runs after
   the judge, so no refusal can be swallowed (READ).
4. A cache folder that cannot be made or read leaves the module in memory — **acceptable**,
   with L3's warning.
5. `_stamp` renamed `_file_stamp` — **acceptable**: `test_every_runner_name_is_defined_in_one_module`
   is green (EXECUTED).

## The fix, read as an attacker

- **Routes the rows cover, and the code holds** (READ, then EXECUTED where named): `run`,
  `run_async` and `Session` each pass `others=_engines._caches(cache)` (the only two callers of
  `_walk_grants`, by grep); own cache off, elsewhere and default; `$WASI_PYTHON_CACHE`;
  defaults with `XDG_CACHE_HOME`, `LOCALAPPDATA` or `HOME` changed, and the `pwd` home; caches
  not made (deepest existing ancestor); grants at, inside and above; a root to be made over or
  inside a cache to be made, compared by NFC, casefold and trailing dots and spaces, which can
  only refuse more; a link on the path with no `..` after it; links and junctions as the cache
  folder; second names by `st_nlink`; the swap, narrowed (L4). Only the call's own cache is
  made.
- **My own route:** M1, above. Everything else I tried by reading held.

## Constitution checks

- §4.1 (patches): none. §4.15: a default tightened, none loosened (a writable grant at `$HOME`
  is now refused where a default cache would be made there, which is the fix's intent and in
  the README).
- Rule 4 (never weaken the judge): nothing under `tests/checks/`, `tests/known_gaps.toml`,
  `tests/upstream/` or `context/progress/` changed. The `tests/release_shards.toml` line adds the
  new file to `own-runner` and removes nothing; that shard runs on all three systems (the
  Windows log shows the file ran there): **honest**.
- Structure (rule 4a of the checklist): no module-level mutable or lock, no private API, no
  platform branch outside `_platform.py`, no new seam (the swap row passes a stand-in as
  `_module_miss`'s existing `wt` parameter and patches no `wasi_python` name), no function past
  80, no module past 1,500. **Not structural**, as the Kind line says.
- Code speaks for itself: `test_src_names_no_context_document` and
  `test_code_outside_src_names_no_context_document` green (EXECUTED).

## The self-check and the claim block

Complete and true but for L1's two numbers; "one Not protected item" matches the README (L4's
wording note). The claim list (34 new rows, nothing changed, retired, lost or grown) matches the
diff and the run's ratchet lines.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. M1 — fixed in `21cc7296`: `_cache_chain` takes its prefixes from `Path(path).absolute()`,
   keeping `..`; the two-`..` row failed on `a891dec5` and passes, beside a one-`..` row.
2. L1 to L4 — L1 corrected in the landing notes (remeasured on `21cc7296`); L2 fixed, `_load`
   catches `OSError` around `private()` (no row: only a patch of `PLATFORM.private` reaches the
   gap); L3 fixed, a warning through one helper shared with `_store`; L4 fixed in `_load`'s
   docstring and criterion 12. The specification's *Disposition of the build review* has each.

## Verdict

**Lands once M1 is answered**: the `..`-after-a-link spelling judged through
`Path(path).absolute()` with its row seen failing first, or answered in writing; the Lows are
write-ins.
