# Review of 054 — Read-only code on the import path (build review)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author of the specification, its
  pre-build review or the build. This is also the change's security review: it lets
  embedder-granted code onto the guest's import path.
- **Reviewed:** `spec/054-read-only-code-on-the-import-path` in `../wasi_python-054`,
  `git diff 62d2c56...c0d3e84` (build commits `615e447..c0d3e84`), against the specification
  (Decisions 1 to 12, criteria 1 to 9, Decision 9: grants only, mounts refused; question 93),
  the pre-build review with its Disposition and Confirmation, and `runner.py` / `cli.py` as
  built.
- **Re-ran** (arm64 macOS, uv, wasmtime-py 49.0.0, the frozen set `build/sets/s-f94dec535086b06c`
  read only through `WASI_PYTHON_ARTIFACTS`, no `--accept`; logs in the worktree's `build/` and
  beside this file):
  - fast tier, `uv run pytest -m "not slow"` → `build/054-buildreview-fast.txt`, exit 0:
    `wasi_python v1: 270/319 pass · 0 gap · 10 blocked · 0 fail · 39 deselected (unit suite
    1020/1028, 8 skipped)`; `v1.4 embedding 132/132`; `ratchet vs 34eb315196: lost 0 · absent 0
    · unrun 0 · unrun locally 8 · gained 11 · grew 0 · upstream unrun 31 · not selected 27 ·
    judge changed: tests/checks/test_v1_2_hostile_guest.py, tests/checks/test_v1_4_embedding.py,
    tests/unit/test_cli.py`; `1290 passed, 18 skipped, 39 deselected`.
  - full judge once, `uv run pytest` → `build/054-buildreview-full.txt`, exit 0:
    `wasi_python v1: 277/319 pass · 0 gap · 42 blocked · 0 fail (unit suite 1020/1028, 8 skipped)`;
    `v1.3 data stack 26/58 blocked 32` (numpy's and pandas' source trees, absent in the worktree),
    `v1.4 embedding 132/132`; `ratchet vs 34eb315196: lost 0 · absent 0 · unrun 0 · unrun locally
    28 · gained 11 · grew 0 · upstream unrun 31 · judge changed: (the same three files)`;
    `1297 passed, 50 skipped`. Both lines equal the landing notes'.
  - `ruff check src tests`: all checks passed; `ruff format --check src tests`: 72 files already
    formatted. The worktree has no tracked change (`git status` clean).
  - the builder's 13 stand-ins and 22 mutants of my own (`mutants.py`, `mutants.txt`,
    `mutants-R22.txt`); the guest and layout attacks (`probe_attacks.py`/`.txt`,
    `probe_swap.py`/`.txt`); fuel and stack depth (`probe_fuel.py`/`.txt`).
  - the rebase: main `90e46cb` (035, 056 and the 0.1.0a4 release landed) exported to a scratch
    folder with 054's diff applied (`rebase/`), its 13 new checks run against main's post-035
    set `s-c4190ca065ada03a` (`rebase-054-checks.txt`), and fuel there (`probe_fuel_main.txt`);
    054's diff test-applied on `spec/049-the-public-api-is-frozen` (`rebase049/`).

## Acceptance criteria against evidence

1. **Every mode** — met. Both binaries pass; 11 of 11 byte-equal cases. Stand-ins 1a, 1b
   (2 of 11 differ) and 1c (3 of 11 differ) fail it, as the landing notes say (EXECUTED). My R16
   (clearing `linecache.cache` instead of `_interactive_cache`) fails it too, 3 of 11.
2. **After the runtime** — met. 0 of 6 shadowed; order among entries; the pins (pytz 0 on the
   snapshot, 2 on the plain binary; `_hashlib` once, `AttributeError`, both). Stand-in 2 fails it
   (EXECUTED). The same pins hold on main's post-035 set (EXECUTED, `rebase-054-checks.txt`).
3. **A zip** — met, both binaries, and on the post-035 set (035's readers serve the user zip's
   resource and metadata; EXECUTED).
4. **Writes nothing** — met, both binaries (READ: the check compares a digest of every file and
   folder before and after, with and without `sys.dont_write_bytecode = False`, and the
   precompiled `.pyc` gives `X == 1`).
5. **32 cases** — met, both binaries. All 9 of the spec's criterion-5 stand-ins fail exactly the
   cases the landing notes list (shortest prefix: 4, as explained there; no host-nesting rule: H3
   counted twice). But three unsafe mutants pass it (F1).
6. **The command line** — met (unit cases and the v1.4 call; R21, passing an empty
   `import_path` always, fails the unit case).
7. **Spec 006's guarantee** — met (unchanged checks pass in the fast tier).
8. **The judge** — met as written: lost 0, grew 0, ruff clean; 049 not landed here. But "no
   existing call's argv or fuel changes" is not something the judge can see (F2: the ratchet's
   fuel comes from the harness's own driver, never from `run()`), and `run_async` with an import
   path is run nowhere (F2).
9. **README and CHANGELOG** — met for Decision 11's list. Decision 7 also says the README
   documents the recursion-limit and fuel differences; it documents neither (F4).

## The guest's attacks (EXECUTED, both binaries, `probe_attacks.txt`, `probe_swap.txt`)

- **A writable root with `/code` a read-only entry.** The guest wrote `/code/evil1.py`
  (`PermissionError`), opened `/` and created `code/evil2.py` relative to its descriptor
  (`FileNotFoundError`), `chdir('/')` and wrote `code/evil3.py`, `mkdir`, `rename('/code', …)`
  and `symlink` inside `/code` (`PermissionError` each). The next call imported none of them; the
  host folder held only `mylib.py`.
- **A writable grant above the entry** (A1's layout, `/work` writable, `/work/lib` read-only).
  Through `/work`'s descriptor the guest created `lib/evil.py`: it landed in the writable host
  folder (`work/lib/evil.py`), and the next call's `import evil` found nothing. Decision 4's
  "a writable place above an entry is harmless" holds for descriptor-relative opens too.
- **Case.** wasi-libc matches preopens case-sensitively, as `_under` does: with a grant at
  `/Code`, `/code/mylib.py` is `ENOENT`, `/code` as an entry is "no grant serves it", and with a
  root it is "served by the root". A writable grant at `/code/out` beside the entry `/Code` is
  not under it and cannot be reached through it.
- **Swaps.** A serving grant's folder replaced, after the judge and before wasmtime's open, by a
  link to a folder holding the writable grant: `RuntimeError: grants[0] at /code changed between
  its check and the call` (spec 017's check covers the new rule too).
- **Links in the host path** of a serving grant, a writable grant or the root, when they pass
  through a folder this user can write, are refused by spec 017's rule before 054's.
- **Second entries.** Guest and host nesting refuse on `import_path[1]` (but no check holds it,
  F1).
- **Odd guest paths through the prelude:** `'`, `"`, `\`, a newline, U+2028, U+0085, a non-BMP
  character and `/q'];print('INJ');['` each reach `sys.path` exactly and import.
- **Shadowing beyond Decision 6:** none found. The prelude's own imports (`linecache`, `sys`,
  `_reactor`, `os`) are resolved before or without the entries; the inner `_reactor.run`'s lazy
  imports (`runpy`, `linecache`) are in the zip, which comes first. Every name an entry supplied
  was a name the runtime lacks, which Decision 6 states as a class.
- **What the runner cannot see** (F3): an embedder's hard link between an entry's folder and a
  writable grant, and a writable mount whose provider stores into an entry's folder. Both let
  call 1 plant and call 2 run, in the same layout.

## Findings, most severe first

1. **Low-medium — three unsafe mutants of the refusal logic pass every check**
   (`tests/checks/test_v1_2_hostile_guest.py`, criterion 5). EXECUTED (`mutants.txt`). The code is
   right today (the probes above); the judge would not notice it going wrong.
   - **R3, the serving place matched case-insensitively** (as an APFS host compares). Failure: a
     writable root, a read-only grant at `/Code`, `import_path=["/code/lib"]` is allowed as
     served by `/Code`, while the guest resolves `/code/lib` through the root: code a call writes
     to the root's `code/lib/` runs in the next call. EXECUTED with the mutant (`probe_r3.txt`,
     both binaries): call 1 wrote `/code/lib/evil.py`, call 2 printed "planted ran"; the built
     runner refuses the layout ("served by the root"). R8 and R9's failures are INFERRED from the
     mutants' code. Add S9: `root=` a host folder, the
     read-only grant at `/Code`, `["/code/lib"]`, refused as served by the root.
   - **R8 and R9, host nesting or guest nesting judged for the first entry only.** Failure:
     `import_path=["/a", "/b"]` with a writable grant of `b/out` (or at `/b/w`) runs, and a later
     call imports what it wrote. Every refused case in criterion 5 but V6 has one entry. Add H5
     and G4: the same layouts as H1 and G1 with the entry second (`["/a", "/code"]`), each
     refused naming `import_path[1]`.
   - AGENTS rule 3: a failure mode once seen becomes a check. Each is one line in the existing
     check.
2. **Low-medium — two paths no check runs: `run_async(import_path=…)`, and the call without an
   import path.** EXECUTED.
   - R22, `run_async` dropping the argument from its `_check_places` call, passes all 13 checks
     (`mutants-R22.txt`). Failure: an async embedder's entries are silently absent (closed, not
     open: nothing is imported). 049's rebase moves exactly that call into `_checked` (finding
     5), so the regression is likeliest there. Add one `run_async` case (in criterion 1: `-c`
     imports `mylib` and prints `sys.path`).
   - R17, the prelude put on **every** call (`_import_prelude(())` no longer `[]`), passes the
     whole fast tier and the whole full judge with `grew 0` (`r17-fast.txt`, `r17-full.txt`:
     `277/319 … lost 0 … grew 0`). Every call then costs about 3.4 M (snapshot) or 1.1 to 1.6 M
     (plain) more fuel and has two frames fewer. The ratchet cannot see it: the checks' `fuel`
     metric is recorded by `tests/checks/conftest.py`'s `guest` fixture, which runs the harness's
     own driver, not `run()`. So criterion 8's "no existing call's argv or fuel changes" rests on
     reading `_import_prelude` (READ: it is right), not on the judge. Add a pin: without
     `import_path`, `-c "import traceback; print(len(traceback.extract_stack()))"` prints `2` on
     both binaries (with one, `4`: EXECUTED, `probe_fuel.txt`), which also holds Decision 7's
     two frames.
3. **Low — the *Safety* sentence still over-claims for the same call**
   (`README.md`, *Safety*: "nothing the same call can write lies under one"). EXECUTED, both
   binaries: (a) the embedder's hard link `code/mylib.py` = `out/mylib.py`, `out` granted
   writable: call 1 rewrote `/out/mylib.py` in place, call 2 printed `PLANTED`; (b) a writable
   mount at `/data` whose provider stores into `code/`: call 1 wrote `/data/evil.py`, call 2's
   `import evil` printed "planted via mount ran". The runner cannot see either (a hard link is not
   a folder; a provider has no identity), which is the F1 lesson for mounts applied to a mount
   beside the entry rather than serving it. Spec 017's sentence ("a read-only grant can still
   change if the same host files are writable elsewhere") is under *Grants*; the sentence under
   "Enforced, and judged" should not say more. Suggested: "… each is served by a read-only grant,
   and nothing the same call's root or grants can write lies under one by folder; a hard link,
   or a writable mount whose store is an entry's folder, is yours to keep apart, as across calls
   (see *The import path*)", and one clause in *The import path* beside the cross-call sentence.
4. **Low — the README omits two differences Decision 7 says it documents, and Decision 7's
   numbers are the draft's.** EXECUTED (`probe_fuel.txt`): the recursion depth is 996, not 998,
   with an import path, on both binaries; `-c pass` costs, in two pairs per binary, +3.39 M to
   +3.48 M on the snapshot and +1.00 M to +1.63 M on the plain binary (fuel varies by up to
   0.5 M between runs of the same call; the landing notes' +3.39 M / +1.54 M are single runs
   inside that spread). The README states neither the frame limit nor the fuel cost, and
   Decision 7 still says +3.26 M / +1.33 M (measured without the `linecache` clear). On main's
   post-035 set the cost is +3.41 M to +3.58 M and +0.90 M to +1.94 M (`probe_fuel_main.txt`).
   Write the built numbers, as approximate benchmark facts on the set 054 lands on, into
   Decision 7, and add "two frames fewer before the recursion limit, and about 3.5 M more fuel
   on the snapshot (about 1.3 M on the plain binary) per call" to the README sentence on frames.
5. **Low (for the lane) — the rebase.** EXECUTED (`rebase/`, `rebase049/`).
   - **Onto main `90e46cb`:** `runner.py`, `cli.py`, the three test files and the README apply
     cleanly; the 13 new checks pass there against `s-c4190ca065ada03a` (main's artifacts, 035
     included): `11/191 pass … ratchet vs 4921daffeb: lost 0 … gained 11 · grew 0`. Two textual
     conflicts: the CHANGELOG entry sits under `0.1.0a4 — unreleased`, but 0.1.0a4 is released
     (`800cc09`): it moves to `0.1.0a5 — unreleased`, and the `- (what changed)` placeholder
     goes. The questions file conflicts by context only; 93 is free (main has 91 and 94).
   - **Onto 049:** `runner.py` conflicts at both signatures and at `_check_places`. 049 moves the
     `_check_places` call into `_checked(…, root=, grants=, mounts=, max_file_calls=)` and adds
     `limits` as its fifth positional parameter; 054 adds `import_path` as the fifth, with a
     default. Resolve with `import_path` keyword-only in `_check_places` and threaded through
     `_checked` from both `run` and `run_async` (F2's case then guards it); write the `Args:`
     entry in both docstrings; regenerate `tests/public_api.txt` and check its diff is exactly
     Decision 10's three lines (049's format matches: `option --grant GUEST=HOST  append`). A
     wrong positional resolution fails loudly (a `Defaults` is not an iterable: every call is a
     `TypeError`); a dropped `run_async` argument does not (F2).
6. **Info — check strength where the code is right.** EXECUTED (`mutants.txt`).
   - R13, a prelude built by naive quoting instead of `repr`, passes all 13 checks: no check uses
     an entry with a quote or backslash. The built prelude handles them (above). Optional: give
     one criterion an odd entry such as `/a'b"c\d`.
   - R14 and R15, each of F6's two layers removed alone, pass; only both together fail A5. That
     is defence in depth, as the landing notes say.
   - R19: the runner's own message for `/` is unpinned (V4 matches `import_path[0]` only).

## Constitution checks

- §4.4 (two imports only): unchanged; no guest change (READ).
- §4.5 and §4.15 (safe by default): the default `import_path=()` gives today's argv byte for byte
  (`_import_prelude(())` is `[]`, READ; fast tier grew 0, EXECUTED). Nothing writable can serve or
  lie under an entry in one call through the root or grants (criterion 5 and the probes). The
  over-claim in F3 is wording, not a loosened default.
- §4.1 (patches): none. Not build-class: no `scripts/`, `recipes/`, `SHA256SUMS` or workflow
  change.
- Decision 16 ("an explicit read-only typed grant … never writable, never by default") and
  Decision 9 (mounts refused): held in code (S3, S4, S6, S7, G2) and stated in the README in the
  same terms; question 93 is filed and nothing waits on it.
- §5.6: this is the build review; the full judge was re-run once before the verdict.
- §7: nothing tripped. No tree was written: probes and mutants ran from the scratchpad (the
  mutants in scratch copies of `src/` on `PYTHONPATH`), logs in the worktree's ignored `build/`;
  the frozen sets were read only.

## Verdict

**Lands once F1 to F4 are fixed.** The refusal logic is right: every layout the pre-build
review listed, and every guest attack I ran on both binaries, is refused or harmless, and all 13
stand-ins fail as the landing notes say. What is missing is judge strength for a security claim:
F1's three cases and F2's two pins (a few lines in existing checks, each seen failing against its
mutant), and two README corrections (F3's same-call wording, F4's frame limit and fuel).
F5 is the lane's rebase work; F6 is optional.

One line: the code keeps writable things off the import path, but the checks would not notice
three ways it could stop doing so, and the README says slightly more than the runner can see.

## Disposition (by the author, 2026-10-18; confirmed below)

From `build/reviews-evidence/054-buildreview/disposition.md` and the specification's
"Disposition of the build review":

1. **F1** — fixed in `dfa6c78`: S9 (grant at `/Code`, root, `["/code/lib"]`), G4 and H5 (the
   bad entry second, naming `import_path[1]`). **Confirmed.**
2. **F2** — fixed in `dfa6c78`: a `run_async` case and the two-frame pin (2 without an import
   path, 4 with) in criterion 1; Decision 7 and criterion 8 corrected in `65a7c4f`.
   **Confirmed.**
3. **F3** — fixed in `65a7c4f`: *Safety* now says "no folder the same call's root or grants can
   write lies under one (a hard link, a writable mount whose store is an entry's folder, and
   other calls are yours to keep apart …)", and *The import path* names both routes beside the
   cross-call sentence. **Confirmed.**
4. **F4** — fixed in `65a7c4f`: the README states the recursion limit two frames sooner (996
   instead of 998) and the fuel (about 3.5 M snapshot, about 1 M, 0.5 to 2 M, plain); Decision 7
   carries the built range on 035's set (+3.35 M to +3.58 M, +0.51 M to +1.94 M), consistent
   with my measurements (+3.41 M to +3.58 M, +0.90 M to +1.94 M). **Confirmed.**
5. **F5** — done: rebased onto main `3dfdab4` (049 landed). **Confirmed** (below).
6. **F6** — done: an odd entry `/a'b"c\d` (R13) and V4's own message (R19); R14 and R15 left as
   defence in depth. **Confirmed.**

## Confirmation (2026-10-18)

Re-checked on `spec/054-read-only-code-on-the-import-path` at `2d8f585` (rebased onto main
`3dfdab4`; fix commits `dfa6c78`, `65a7c4f`; snapshot `7071182`), against
`s-c4190ca065ada03a` (main's post-035 set), read only, no `--accept`. Evidence beside the
scratch copy of this review: `mutants_r2.py`, `mutants-rebased-log.txt`; the worktree's
`build/054-buildreview-fast-rebased.txt`.

- **Mutants and stand-ins (EXECUTED, both binaries):** all 13 builder stand-ins fail as listed
  (no serving rule now 9 of 9 with S9; no guest-nesting rule 4 with G4; no host-nesting rule 6
  with H5). My R3, R8, R9, R13, R17, R19 and R22 each fail now (R3 on S9, R8 on H5, R9 on G4,
  R19 on V4; R13, R17 and R22 on `test_the_import_path_reaches_every_mode`). R22 is anchored at
  `run_async`'s `_checked(…, import_path=import_path)` call, so the case guards the argument
  049's structure threads through. Matches the builder's `results.txt`.
- **The `runner.py` resolution (READ):** `run` and `run_async` both pass
  `import_path=import_path` into `_checked`; `_checked` takes it keyword-only (default `()`) and
  hands it to `_check_places(…, limits, import_path=import_path)`, whose `import_path` is
  keyword-only after `*`, so 049's positional `limits` cannot be confused with it. `_checked`
  still reads the defaults once (`limits = _current_defaults()`), and `_check_import_path` reads
  none; `limits.file_calls` replaces `DEFAULTS.file_calls`. No pool, `_submit` or
  `async_workers` line is touched by 054's diff against main (`git diff 3dfdab4...HEAD -- src/`).
  049's `Args:` entries are the same text in `run` and `run_async`; 054's old prose sentence is
  gone.
- **The snapshot:** `git diff 3dfdab4...HEAD -- tests/public_api.txt` is exactly Decision 10's
  three lines (`param import_path: Iterable[str] = ()  keyword-only` under `run` and under
  `run_async`, after `mounts`; `option --import-path GUEST  append`). The README's generated
  reference gains the matching signature lines, `Args:` entry and options-table row.
- **CHANGELOG:** the entry sits at the top of `0.1.0a5 — unreleased`; nothing else differs from
  main.
- **README F3/F4 wording:** as quoted in the Disposition; it matches Decision 9 (no mounts serve
  or lie under an entry) and no longer claims more than the runner judges.
- **Fast tier** (`build/054-buildreview-fast-rebased.txt`, exit 0):
  `wasi_python v1: 305/354 pass · 0 gap · 10 blocked · 0 fail · 39 deselected (unit suite
  1059/1067, 8 skipped)`; `v1.4 embedding 147/147`; `ratchet vs 323ad21aa5: lost 0 · absent 0 ·
  unrun 0 · unrun locally 8 · gained 11 · grew 0 · upstream unrun 31 · not selected 27 · judge
  changed: tests/checks/test_v1_2_hostile_guest.py, tests/checks/test_v1_4_embedding.py,
  tests/public_api.txt and 1 more`; `1364 passed, 18 skipped, 39 deselected`. Equal to the
  builder's `054-fast-r3.txt`. ruff check and ruff format --check clean; worktree clean.
- **Full judge:** not re-run; I have no reason to doubt the builder's fresh `054-full-r3.txt`
  (`312/354 pass · 0 gap · 42 blocked · 0 fail`, `lost 0 … grew 0`, the 32 blocked being the
  absent numpy and pandas source trees). The lane judges the exact commit in the main tree.

Every finding is fixed or answered; nothing remains for 054. For the lane: the judge changed
(`--accept-judge`), and the ratchet base is now `323ad21aa5`.

**Confirmed, it lands.**
