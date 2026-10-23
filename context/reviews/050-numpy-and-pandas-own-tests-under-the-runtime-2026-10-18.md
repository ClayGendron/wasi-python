# Review of 050 — numpy's and pandas' own tests under the runtime (the build; a judge change)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change, the specification, its pre-build review, its disposition or its confirmation. I read `AGENTS.md`, the constitution, specification 050 with its landing notes, its pre-build review (`050-numpy-and-pandas-own-tests-under-the-runtime-spec-2026-10-18.md`: F1 to F15, the Disposition, the Confirmation with C1 and its builder notes), spec 051's Decision 12 and its out-of-scope list, question 89, and the whole diff (`git show f24f219`). I read all of `tests/harness/upstream.py`, `tests/upstream/drive.py`, `fetch.py`, both TOML and both ini files, the check file, the scoreboard, plugin, needs and guest changes, the new unit checks, the 25 gap entries, and the README, AGENTS, CHANGELOG, progress README, spec 002 and memo edits. I compared both ini files with upstream's (`build/numpy-2.5.2/pytest.ini`, pandas' `[tool.pytest.ini_options]`). Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** commit `f24f219` on `spec/050-upstream-tests` in the worktree `../wasi_python-050`, based on `749f6c7`. Main has since moved to `fe67910` (spec 040's acceptance), so the lane rebases before it judges. The worktree was clean before and after every run below (`git status --short` empty, EXECUTED).
- **Ran (EXECUTED, darwin-arm64, Darwin 25.5.0, `uv run` only, wasmtime-py 49.0.0, the frozen set `build/sets/s-0cdc7b2bd78db6f5` read only).** Scripts and outputs are in this folder (`050-buildreview/`):
  - `uv sync`; `uv run python tests/upstream/fetch.py` (the seven wheels; `shasum -a 256` equals every `kit.txt` line).
  - `judge.log`, `judge-latest.json`, `judge-upstream.txt`: the full judge, `WASI_PYTHON_ARTIFACTS=…/s-0cdc7b2bd78db6f5 uv run pytest`, no flags, run once.
  - `uv run ruff check` and `uv run ruff format --check` on `src tests recipes/guest`.
  - `mutants/run_mutants.py` → `mutants/summary.txt`, `mutants/*.log`: 40 one-edit mutants of `upstream.py`, `scoreboard.py`, `plugin.py` and `guest.py`, each applied alone (its text asserted to occur once), the four touched unit files run, the file written back by bytes and its SHA-256 checked (`mutants/before.sha`: all four `OK` after the run).
  - `e2e/run_e2e.py` → `e2e/summary.txt`: four mutants of the judge's *data*, run through the real guest on the smallest failing group (`pandas-tslibs`), its class and the rules check; each file restored by bytes and its hash printed.
  - `gaps_vs_lists.py` → `.txt`: every class's list file recounted and re-digested with `scan.digest`, against its gap.
  - `probe_dropped_metric.py`, `probe_render_cap.py`, `probe_p_line.py`, `probe_public_api.py`, each with its `.txt`.
  - I never passed `--accept`.

## The judge

EXECUTED (`judge.log`, exit 0, 529.4 s by pytest's count):

```
wasi_python v1: 250/284 pass · 25 gap · 9 blocked · 0 fail   (unit suite 925/933, 8 skipped)
  v1.3  data stack          31/57  gap 25 blocked 1
gaps close with: 051-what-the-upstream-tests-found 15 · README 8 · questions-for-the-owner 2
next: context/specifications/051-what-the-upstream-tests-found.md (unblocks 0, closes 15)
ratchet vs 361775dd62: lost 0 · absent 0 · unrun 0 · unrun locally 7 · gained 12 · grew 0 · judge changed: … and 33 more
not machine-checked: publication · copying from prior art · numpy's 25 files that need its C test modules (number 89) · pandas beyond eight groups
1175 passed, 17 skipped, 25 xfailed in 529.40s (0:08:49)
```

- 11 groups and the rule `pass`; 18 classes and 7 traps `gap` (`judge-upstream.txt`).
- Passes per group equal Decision 8's table, 62,569 in all.
- Fuel per group differs from the builder's judge column by at most 0.19 ppm (`numpy-lib`, +24,922). The 11 groups sum to 1,646,467,043,467.
- `left_out` is `[]` for every group: no file outside the tarballs was staged.
- The seven traps name the nodes the landing notes give. `castingimpl-arraymethod` names its collector, `numpy/_core/tests/test_arraymethod.py`.
- `unrun locally 7` is this worktree's missing oracle and five C source trees, as the notes say. No upstream check is among them, and there is no `upstream unrun` count.
- The unit suite counts 925/933 here against the notes' 924/932. Nothing failed; I did not trace the extra case (INFERRED: an environment-dependent parametrization).
- `ruff check` and `ruff format --check` on `src tests recipes/guest` are clean. A bare `ruff format --check` flags `README.md`'s code blocks; main does the same, so this change did not cause it.

## Mutants (EXECUTED)

`mutants/summary.txt`. 35 of 40 are killed by the unit suite. Five survive:

| mutant | what it does | why it survives |
|---|---|---|
| U5 | `Session._prepare` ignores the tie's errors | no unit check goes through `prepare`; F1 |
| U6 | a tie error becomes `pytest.skip`, not a failure | the same; F1 |
| S9 | `upstream unrun` counts only checks missing from the run, not `blocked` or `deselected` ones | the refusal test always carries a missing accepted gap; F2 |
| S13 | `upstream unrun` ignores accepted gaps | the same test always carries an accepted pass; F2 |
| S7 | the passes merge lowers the value under `--accept-growth` | equivalent: `accept` refuses any fall without `--accept-fewer-passes` before the merge runs, so the `max` is unreachable (READ) |

Killed and worth naming:
- U1, admit a failure no class takes;
- U2 and U3, drop the `+`/`-` ids;
- U4, an empty tie;
- U7, stage non-members;
- U8, unzip `..`;
- U9, the kit always met;
- U12, U13 and U15, exit codes, a missing `E` line, collection errors;
- U16, a trap check that never fails;
- U17, a class that ignores its outcome;
- U21, stage only the asked package (the fuel-drift fix);
- U24, `error` outcomes ignored;
- S1 and S2, drop the FEWER refusal or let `--accept-growth` carry it;
- S3 to S6, a fall not red, not detected, cut to three, or printed after `GREW`;
- S8, drop the upstream refusal;
- S10, drop the absent-gap branch;
- S12, merge passes by `min`;
- P1, the flag not passed through;
- G1, the trap cause dropped.

**End to end through the guest** (`e2e/summary.txt`), each with its file restored by hash:

- **E1.** `pandas-tslibs/no-processes.txt` emptied, gap kept. The class check `fail`s: "fails differently from its gap … 2 finding(s) … `+pandas/…`". The rules check `fail`s: "empty but still has a gap".
- **E2.** The class's `match` broken. The group `fail`s with "unexpected failed …test_no_timezone_data — OSError: [Errno 58] wasi does not support processes." The class passes, so its gap says "remove the gap".
- **E3.** The gap removed. The class `fail`s with its one node. The rules check `fail`s: "has members but no gap".
- **E4.** A copy of the set whose `MANIFEST` pins pandas' tarball with another hash. The group and the class both **`fail`**, not blocked: "the tests are not the artifact's: tests from pandas-3.0.6.tar.gz SHA-256 66b07ef7315a, artifact built from pandas-3.0.6.tar.gz SHA-256 000000000000". So the tie works today. Only its unit guard is missing (F1).

## Findings, most severe first

None admits a failure silently today. No path lowers `passes` without a named flag and a judge change. No lost pass can hide. Each finding is a gap in a guard, or in the scoreboard's text.

### F1 (medium-low). The MANIFEST tie's wiring into the checks has no unit check

**Evidence.** Criterion 9 asks the unit checks to show that a mismatched `MANIFEST` "makes the checks fail (not blocked), naming both". The unit checks call `tie_errors` only (`test_a_manifest_from_another_tarball_fails_naming_both`, `test_a_manifest_with_other_patches_fails_naming_both`). Two mutants survive the whole unit suite:
- U5 makes `Session._prepare` drop the tie's errors;
- U6 turns the tie's `AssertionError` into `pytest.skip`.

The judge cannot catch either on a matching set, because then the tie has nothing to say. E4 shows the wiring is right today (EXECUTED). But the one decision the pre-build review's F4 was about, "fails, not blocks", has no guard of its own.

**Fix.** Add a unit check that goes through `Session.prepare`. Decision 3 calls this "the tie": the test files must come from the very tarball and patches the artifact was built from. `test_the_stage_holds_every_package_whichever_check_asks_first` already builds the scaffolding: a tarball, a tree, an artifact `MANIFEST` and a kit. Give the `MANIFEST` another hash and assert `pytest.raises(AssertionError, match="tests from … artifact built from …")`. A pytester variant could also assert that the record's status is `fail`.

### F2 (medium-low). The refusal test cannot see the case it was written for: every upstream check `blocked`

**Evidence.** Decision 13 (the pre-build review's F9) imagines a lane that has lost `build/upstream/wheels/`. There, every upstream check is in the run with status `blocked`. The unit check `test_accept_refuses_while_an_accepted_upstream_check_did_not_run[blocked|deselected|None]` always puts an accepted gap in `base` that is missing from the run, whatever `now` is. That gap alone triggers the refusal. So:
- **S9** survives. It narrows the rule to `now is None`, so `blocked` and `deselected` checks are no longer counted. That mutant re-opens exactly F9: the lane accepts, and the old `passes` are kept.
- **S13** survives. It stops counting accepted gaps.

The code is right today (READ: `now is None or now["status"] not in ("pass", "fail", "gap")`). Only its guard is hollow.

**Fix.** Split the parametrization:
- the `blocked` and `deselected` cases keep only `G` in the upstream file. For the blocked case, give the run the record a real blocked check has (`need="upstream kit"`), and give the gap the same status;
- one case holds only an accepted gap, missing from a run that did not collect the file.

Then S9 and S13 die.

### F3 (low-medium). The scoreboard can now cut its own `RED` line and the "not machine-checked" lines

**Evidence.** `render` builds the tail in this order:
1. the ratchet line;
2. every `FEWER` line (never cut, by design);
3. up to three each of `LOST`, `ABSENT` and `GREW`;
4. `RED`;
5. the two "not machine-checked" lines.

It returns `(lines + tail)[:MAX_LINES]`, so an overflow is cut from the end. With every area line shown, `probe_render_cap.txt` gives (EXECUTED):

| FEWER | LOST, ABSENT, GREW (each) | lines | `RED` kept | "not machine-checked" kept |
|---|---|---|---|---|
| 0 | 3 | 23 | yes | yes |
| 2 | 3 | 25 | yes | yes |
| 6 | 3 | 25 | **no** | **no** |
| 11 | 3 | 25 | **no** | **no** |
| 11 | 0 | 25 | yes | yes |

So the case with no FEWER line, the most this tail could hold before 050, fits. The 11 FEWER lines that 050 adds can push the verdict off the scoreboard. The comment above the tail says "the ratchet and the verdict are never cut". The exit status is still non-zero, so this is no false green. But the one line that says why is gone. This is the very run where it matters most: a product change that loses passes everywhere at once.

`test_every_fewer_line_survives_the_line_cap` uses six FEWER lines and five GREW lines, so the tail just fits. It also does not assert that `RED` is kept.

**Fix.** Keep `RED` and the two "not machine-checked" lines whatever happens. For example, trim `LOST`, `ABSENT` and `GREW` to fit before anything else, or put `RED` right after the ratchet line. Add a case with 11 FEWER lines and three each of the others that asserts `RED` is kept.

### F4 (low). `--accept-growth` can drop the `passes` ratchet altogether

**Evidence.** Say a group check passes but no longer records `passes`. `compare` then files it under `growth` ("passes is no longer recorded"), not under `fewer`. `accept` with `growth_reason` rebuilds the platform's metrics from the fresh ones only, so `passes` is deleted. `probe_dropped_metric.txt` (EXECUTED):
- without flags, the run is refused with "metrics grew";
- with `--accept-growth "unrelated growth"` only, it is accepted, and the metrics become `{'wasmtime': '49', 'fuel': 10}`.

Today this needs a judge change, because the check would have to stop calling `metric("passes")`. That change also needs `--accept-judge`, so the review would see it. Still, it is a path the specification forbids in so many words. Decision 12 says "`--accept-growth` does not accept it: one unrelated growth must not carry a lost pass."

**Fix.** In `compare`, a `COUNTS_UP` metric that is no longer recorded goes to `fewer` as `passes <old> -> none`. Then only `--accept-fewer-passes` can drop it. Add one unit case.

### F5 (low). One class's closer does not cover one of its members

**Evidence.** Class `numpy-others-test-only-modules` admits two nodes, and both close with question 89, numpy's C test modules. I ran `numpy/tests/test_public_api.py` alone in the guest through the harness's own `Session` (`probe_public_api.txt`, EXECUTED):
- `test_NPY_NO_EXPORT`: "module 'numpy._core' has no attribute '_multiarray_tests'". That is question 89's.
- `test_api_importable`: "Modules that are not really public but looked public and can not be imported: ['numpy.conftest']". Its only cause is that the product's zip carries no `numpy/conftest.py`. Decision 4 says exactly that.

Question 89 does not mention `conftest` (READ: grep over its section). None of its three options, as written, would put `numpy/conftest.py` in front of the guest. So the gap `test_upstream_class[numpy-others-test-only-modules]` names a closer that would not empty it. The build follows the specification's own Decision 10 table here, so the finding is against both.

**Fix.** Choose one:
- give `test_api_importable` its own class, for example `no-conftest` closed by `README.md`. The README states the fact: the zip carries no tests and no `conftest.py`. That makes 19 classes, 26 gaps, and 9 closed by the README;
- or add one line to question 89 saying that option (a) must also carry `numpy/conftest.py` for this test to pass.

### F6 (low). A trap check passes when its session does nothing

**Evidence.** `trap_findings` returns a finding only when the session trapped (READ). A trap check whose entry no longer exists still passes, as does one that collects nothing, or one that exits 4 or 5, or ends without an `E` line. That could happen after a numpy re-pin renames the test. Its gap would then say "remove the gap". Once the gap is removed, a passing check guards nothing.

The pre-build review's builder note covers the related case, a trap that becomes a Python failure. Spec 051 removes every `[[trap]]` entry in the same landing, so this does not bite today (INFERRED).

**Fix (cheap).** A trap check also requires an `E` line and at least one `S` line or `C` line under its entry's node id. Otherwise it is a finding: "the entry ran nothing".

### Notes (no change needed)

- **The 25 gaps are honest, apart from F5** (`gaps_vs_lists.txt`, EXECUTED). Every class's gap `match` equals `len(list)` and `scan.digest(list)`; the lists hold 268 ids in all. Every trap gap is one finding. The closers split 15 / 8 / 2:
  - **Spec 051 (15).** Its Decision 12 names exactly these (READ): six `zip-code-names`, two `patch-0001-*`, and seven traps.
  - **The README (8).** It states each fact (READ):
    - `dup` (`tofile`/`fromfile`, line 63);
    - `mmap` (line 64);
    - `/dev/null` (new, line 65);
    - `ctypes` calls (lines 69–72);
    - processes (line 1078, "no network, no processes").

    Spec 051 lists `dup`, `mmap` and `ctypes` as out of its scope, "already documented". So no README-closed gap is something 051 fixes.
  - **Question 89 (2).** It exists. See F5 for one of its members.
- **The absent-gap branch.** `compare` gives an accepted `gap` whose check is gone the status `absent`, under the same rule as an accepted pass: the file is gone, or was collected whole. It is never `lost`. A gap that is merely uncollected is neither. Unit-checked, and S10 is killed. This also makes a vanished gap red for every file, not just this one. That is stricter; main's accepted state has none today (`absent 0`).
- **`upstream unrun` and `--partial`.** The rule is sound as written:
  - every accepted pass or gap in the upstream file that is not `pass`, `fail` or `gap` now and not `absent` counts;
  - `--partial` with any reason releases it, and the reason is recorded.

  Every `-m "not slow"` orientation run will show `upstream unrun 36`. That is expected, and rule 1's run never accepts.
- **The passes merge.** Without the flag it takes `max`. That code is unreachable (S7), because a fall is refused first. It is harmless as a second guard.
- **`FEWER` is never cut** (S5 is killed) and comes before `GREW` (S6 is killed). F3 is about what *it* pushes out.
- **The member filter and `support`.** `stage` copies three things, each only if it is a member of the tarball, or a file a recorded patch creates:
  - the groups' and traps' folders;
  - the `__init__.py` and `conftest.py` of their `tests` ancestors;
  - `support`.

  Anything else goes to `left_out`, which is `[]` today. The rules check confirms that `support`'s four pandas files are members. The only path to them is the stage, through `import pandas.tests.extension.decimal`. The `M` guard accepts them, because their names contain `tests`.
- **The fuller ini transcription** (READ):
  - `numpy.ini` is upstream's `filterwarnings` line for line, plus the one `PytestAssertRewriteWarning` ignore;
  - `pandas.ini` is upstream's four keys, verbatim;
  - left out: `norecursedirs`, `doctest_optionflags`, `junit_family`, `minversion` and `testpaths`. None affects a run of named test folders without doctests (INFERRED).

  The group counts equal the drafting runs' in every group.
- **`Session.prepare` stages both packages** (U21 is killed). The fuel drift it fixes has a consequence for the lane (INFERRED from the memo's correction). Any future change to what the grant holds moves every group's fuel by up to a few hundred ppm, as a `GREW` on an unchanged product: a new group folder, a `support` file, a third package. Such judge changes should expect `--accept-growth` with that reason. Spec 051 returning two `--ignore`d files does not change the stage, because the whole folder is already staged.
- **The kit comes first on the guest's `sys.path`.** The `M` guard covers only `/upstream/tests`. The kit's top-level names have no overlap with the product's zip (EXECUTED: 12 names, 0 shared), so no product module is shadowed today.
- **The P line** (`probe_p_line.txt`, EXECUTED):
  - `pandas-libs`: `derandomize=True database=None max_examples=15`. No `M` line names a product module.
  - `sfloat-reduce` (a trap): `derandomize=True database=None max_examples=100`; cause `wasm trap: indirect call type mismatch` at `…TestSFloat::test_np_save_load`.

  The harness enforces `derandomize` and `database`. It does not enforce `max_examples`, which is per spec.
- **A pytest exit 1 with no `failed` or `error` line is admitted.** I know of no path to it (INFERRED). A one-line consistency finding would close it.

## Decisions against the build

| # | Decision | Evidence |
|---|---|---|
| 1 | snapshot, judge's driver, one session per group | READ (`Session._run` uses `python-snapshot.wasm`); EXECUTED (judge) |
| 2 | kit pinned, fetched, rules line, safe unzip | EXECUTED (hashes; U8, U9 killed); READ (`kit_errors`, `fetch.py` renames after the hash) |
| 3 | stage tied to MANIFEST, members only, patch-created files | EXECUTED (E4 fails, not blocks; `left_out` `[]`; U4, U7 killed); unit guard of the wiring missing (F1) |
| 4 | `__path__` appended; `M` guard | READ (`drive.py`); EXECUTED (probe: no product module; U11 killed) |
| 5 | pytest options | READ (`drive.py` passes exactly the table's options) |
| 6 | ini transcribed; profiles; `P` line | READ (diffed with upstream); EXECUTED (P lines; U10 killed) |
| 7 | upstream's fast selection | READ (`marker` in both TOML files; `group_spec` puts it first) |
| 8 | groups, `not_selected`, caps | EXECUTED (passes equal the table; rules check passes, caps 2.821×10¹²; U20 killed) |
| 9 | traps deselected, own checks, gaps; C1 | EXECUTED (7 trap gaps, nodes as noted; U16, U22 killed); F6 |
| 10 | classes by node id, `+`/`-`, empty class passes | EXECUTED (E1–E3; 18 class gaps; U1–U3, U17, U24 killed); F5 |
| 11 | the outcome stream | READ (`drive.py`); EXECUTED (parsed in the judge and the probes; U13–U15 killed) |
| 12 | `fuel`, `passes`, `fewer`/`more`, flag, `passed_digest` | EXECUTED (S1–S6, S11, S12, P1 killed; digests in `latest.json`); F3, F4 |
| 13 | need `upstream kit`; refusal unless `--partial` | READ (`needs.py`, `scoreboard.accept`); S8 killed; the guard is hollow for `blocked` (F2) |
| 14 | `trap_cause` | EXECUTED (G1 killed; trap reasons carry the cause) |
| 15 | `slow` | READ (three parametrized checks marked; the rule not) |
| 16 | not build-class | EXECUTED (`git show --stat`: nothing under `scripts/`, `recipes/`, `downloads/`, `.github/`) |
| 17 | rules check; "not machine-checked" text | EXECUTED (passes; U18–U20, U25 killed; tail shows the new text) |
| 18 | README, CHANGELOG | READ (`/dev/null`; Known defects; Measured row; CHANGELOG Judge line) |
| 19 | spec 002 amendments; AGENTS rule 4; progress README | READ (all present and dated) |
| 20 | the builder's worktree | READ (four symlinks to the main tree; nothing in it written) |

## Acceptance criteria against evidence

| # | Criterion | Evidence | Holds |
|---|---|---|---|
| 1 | the kit: fetch, one byte, unzip, no network | EXECUTED (fetch; hashes; U8, U9 killed); READ (no network module in the judge's upstream code) | yes |
| 2 | seen failing first | READ (`build/upstream-first/*.json` and `.log`: `numpy-core` trapped at `test_np_save_load`; 7 + 12 numpy failed; pandas 234) | yes |
| 3 | 11 pass, 18 + 7 gaps, passes as in the table, `P` and `M` lines | EXECUTED (judge; probes) | yes |
| 4 | traps, one finding each; collector node; unit cases | EXECUTED (judge; U14, U16 killed) | yes |
| 5 | strictness on fixed streams | EXECUTED (U1–U3, U10–U15, U17, U24 killed) | yes |
| 6 | the `passes` metric | EXECUTED (S1–S6, S8, S11, S12, P1 killed) | yes; the refusal's unit case is hollow for `blocked` (F2) |
| 7 | fuel repeats | READ (the notes' table, under 0.5 ppm); EXECUTED (my judge against the builder's: at most 0.19 ppm) | yes |
| 8 | rules; empty and non-empty lists; absent gap retired | EXECUTED (rules check; E1, E3; U18, U19, S10 killed) | yes |
| 9 | tie fails naming both; stray not staged; read-only grant; no build-class path | EXECUTED (E4; U4, U7, U23 killed; `--stat`) | yes in behaviour; the wiring's unit guard is missing (F1) |
| 10 | full judge green; lost 0, grew 0, fewer 0; gained 12; tail text | EXECUTED (judge); `unrun locally 7` in this worktree, for the lane to clear | yes, for the lane to confirm |

## Constitution checks

- **§4.1 (patches).** No source change; the tests are read from the patched tree as spec 020 proves it (READ).
- **§4.2 and §4.8 (pinned and untrusted inputs).** The kit is pinned by URL and SHA-256 and verified before use. The fetcher renames a file only after its hash matches. The unzip refuses `..` and absolute names. No wheel runs natively (READ; U8, U9 killed).
- **§4.9 (counts, never time).** No check reads a clock. Fuel and passes are counts. The 5¼ minutes, and my 529 s, are benchmark facts in the notes and here (READ).
- **Rule 4 (never weaken the judge).** No path admits a failure silently. Every failure is a class member listed by id, or a finding. A wrong list or a broken expression turns red (E1–E3). `passes` cannot fall without `--accept-fewer-passes`. The one exception is F4, which also needs a judge change. AGENTS rule 4 now names the new allowance files (READ). F1 and F2 are guards to add, not holes today.
- **§4.12 (licences).** The kit ships in nothing. Its licences are recorded (READ).
- **§5.6 and §5.7 (review; class).** The pre-build review was voluntary and is confirmed. This change is not build-class (EXECUTED, `--stat`). It is a judge change, so it needs `--accept-judge`.
- **Artifacts never in git.** The wheels and the stage live under `build/` (READ).

## Disposition (filled in by the author, then confirmed by the reviewer)

By the builder (Claude Opus 5.5), 2026-10-18, on `spec/050-upstream-tests`. Every finding is fixed; each fix's unit case was written first. The full judge after the fixes (`WASI_PYTHON_ARTIFACTS=…/s-0cdc7b2bd78db6f5 uv run pytest`, EXECUTED) exits 0: 38 upstream checks, 12 `pass` and 26 `gap`; `lost 0 · absent 0 · unrun 0 · unrun locally 7 · gained 12 · grew 0`; `gaps close with: 051 15 · README 9 · questions-for-the-owner 2`; passes 62,569; group fuel 1,646,467,107,285 (0.07 ppm from the run you judged). ruff clean.

- **F1, fixed.** `tests/unit/test_upstream.py::test_a_manifest_mismatch_fails_the_checks_through_prepare_not_blocks` builds two scratch packages (tarballs, trees, kit, an artifact `MANIFEST` pinning pandas' tarball with another hash) and calls `Session.prepare("pandas")` twice (the second from the cache). It catches `BaseException` and requires exactly `AssertionError`, so a `pytest.skip` (U6) fails it; a dropped tie (U5) reaches its `else` and fails it. It also checks the message names both tarballs and the wrong hash, and that numpy (whose pin matches) still stages. The code was already right, so the case passed when written; it guards U5 and U6.
- **F2, fixed.** `tests/unit/test_scoreboard.py`: `test_accept_refuses_while_an_accepted_upstream_check_is_blocked_or_deselected[blocked|deselected × pass|gap]` puts only `G` in the upstream file, in the run, `blocked` (need `upstream kit`) or `deselected`, with an accepted pass or an accepted gap; each asserts `upstream_unrun == [G]`, no absent, no lost, the refusal, and acceptance with `--partial`. `test_accept_refuses_while_an_accepted_upstream_gap_is_outside_the_run` holds only an accepted gap missing from a run that did not collect the file. S9 fails the blocked/deselected cases; S13 fails the gap cases (INFERRED from the mutants' descriptions; not re-run).
- **F3, fixed.** `scoreboard.render` builds the tail as: the ratchet line and every `FEWER` line; then `LOST`, `ABSENT` and `GREW` examples, trimmed to the room left; then `RED` and the two "not machine-checked" lines. Those first and last parts are never cut. `FAIL` lines take what room is left, and if the head still overflows it is cut from its end, never the tail. The unit case `test_every_fewer_line_the_red_line_and_the_tail_survive_the_line_cap[0|2|6|11]` uses three each of LOST, ABSENT and five GREW, forty failures, and asserts at most 25 lines, every FEWER line, the `RED` line, the last two lines and the first line. The 6 and 11 cases failed before the fix. (Only a run with more than about 20 `FEWER` lines could exceed 25 lines; `FEWER` is never cut, by Decision 12, so it wins over the cap.)
- **F4, fixed.** In `compare`, a `COUNTS_UP` metric a passing check no longer records goes to `fewer` as `passes <old> -> none`, never to `growth`. `test_a_passes_metric_no_longer_recorded_is_fewer_not_growth`: refused with `--accept-growth` alone, accepted with `--accept-fewer-passes`, which then drops it. Failed before the fix.
- **F5, fixed, the first option.** A new class `numpy-others-no-conftest` (match `looked public and can not be imported: \['numpy\.conftest'\]$`, closed by `README.md`) takes `test_api_importable`; `test-only-modules` keeps `test_NPY_NO_EXPORT` (match narrowed to `has no attribute '_multiarray_tests'`, question 89). The README's platform paragraph now says the zip carries no package's `tests` folders and no `conftest.py`, so `numpy.conftest` does not import. Lists, gaps (two entries rewritten), the README's Measured row (26 gaps, 19 classes) and the CHANGELOG line follow. The judge shows both classes as gaps, README 9.
- **F6, fixed.** `trap_findings(stream, run, entry)`: a trap or out-of-fuel is the finding, as before; without a trap, a missing `E` line is a finding, and so is a session with no `S` or `C` line whose node starts with the entry's id ("the entry ran nothing: <entry> (pytest exit code N)"), as `--deselect` reads a prefix. Unit cases: nothing collected (exit 5), a usage error (exit 4), only another test, no `E` line; and an entry that ran (by test, by file) has no finding. They failed before the fix. The seven trap checks still trap with their one finding each (the judge, above).
- **Notes.** "A pytest exit 1 with no failed or error line": not changed; no path to it is known, and a later change may add the one-line consistency finding. The grant-content fuel effect is recorded in the memo and the landing notes; the next change to the stage should expect `--accept-growth` with that reason.

## Verdict

**Ready to land once F1 and F2 are fixed or answered in writing. F3 to F6 are low; fix them or answer them.** The build does what the specification says, and the judge's run equals the builder's to under 0.2 ppm. Every class and trap is an ordinary gap, listed by id, with a real closer (one closer needs widening, F5). Mutants of the admitting logic, the ratchet, the flag and the tie are killed, with two exceptions. The tie's wiring into the checks, and the refusal's `blocked` case, are right today but unguarded.

**For the lane:**
- `uv run python tests/upstream/fetch.py` in the main tree first.
- Judge the exact commit there. Cite a ratchet line with no `unrun locally` and no `upstream unrun` count.
- `--accept-judge "<reason>"` naming the new checks, the lists, the 25 gaps and the harness changes.
- No `--accept-growth`, `--accept-fewer-passes`, `--retire` or `--partial` is needed. Expect `lost 0 · absent 0 · grew 0 · gained 12`, with no `FEWER` line.
- The review is cited in the landing notes.

## One line

050 makes numpy's and pandas' own tests honest judge checks (62,569 passing, 25 gaps, no silent admission found), but two new guards are hollow: the tie's fail-not-block wiring (F1) and the refusal's `blocked` case (F2). Add those two unit cases. Also keep the verdict line from being cut by FEWER lines (F3).

## Confirmation (2026-10-18)

The reviewer checked commit `0d505d0` on `spec/050-upstream-tests`, the fixes for F1 to F6. Everything below is EXECUTED, `uv run` only, on darwin-arm64 against the frozen set `s-0cdc7b2bd78db6f5`. Outputs are under `050-buildreview/confirm/`. No repository tree was edited. `git status --short` was empty after every run, and all four harness files matched `confirm/mutants/before.sha` after each mutant batch.

**What I ran:**
- **The unit suite:** 930 passed, 13 skipped.
- **ruff** on `src tests recipes/guest`: clean.
- **Every mutant from the review, re-run, plus seven new ones on the fixes** (`confirm/mutants/summary*.txt`, `*.log`). Four of the old mutants had to be re-anchored, because their code moved: U13, U16, S5 and S6.
- **The F3 and F4 probes, re-run** (`confirm/probe_render_cap.txt`, `confirm/probe_dropped_metric.txt`).
- **The gap recount, re-run** (`confirm/gaps_vs_lists.txt`).
- **Selected checks through the real guest** (`confirm/selected.log`, `confirm/selected.txt`):
  - `test_upstream_suite[numpy-others]`;
  - its five classes;
  - the seven trap checks;
  - the rules check.

  Result: exit 0, 37 s. `numpy-others` passes, with 7,267 passes and fuel 175,318,957,071 (my first run gave 175,318,959,740). `no-conftest` is a gap with `1 finding(s), digest de31d83c1d93`: `test_api_importable`. `test-only-modules` is a gap with `1 finding(s), digest 676791284b94`: `test_NPY_NO_EXPORT`. The seven traps are still gaps, each with its one finding and its old digest.

I did not re-run the full judge. The implementer's Disposition reports it: exit 0, 12 `pass` and 26 `gap`, and group fuel 0.07 ppm from my run. Nothing below needs it.

### Each finding

- **F1: confirmed.**
  - U5 (`_prepare` drops the tie's errors) is now killed by `test_a_manifest_mismatch_fails_the_checks_through_prepare_not_blocks`.
  - U6 (the error becomes a `pytest.skip`) is killed by the same case.
  - Together with E4 from the review, the tie now fails the checks, not blocks them, and a unit case guards it.
- **F2: confirmed.**
  - S9 (count only missing nodes) is killed, with 4 failures. Among them is `[blocked-pass]`: exactly the pre-build review's F9 lane, which has lost its kit.
  - S13 (gaps ignored) is killed by `[blocked-gap]` and the other gap cases.
  - S8 is still killed.
- **F3: confirmed.**
  - The probe now keeps `RED` and both "not machine-checked" lines in every row. That includes 11 `FEWER` lines with three each of `LOST`, `ABSENT` and `GREW`, the row that lost them before.
  - Two new mutants are killed: one restores the old `(lines + tail)[:25]`; one drops `RED` from the tail.
  - One caveat: past about 20 `FEWER` lines the board can now exceed 25 lines, because `FEWER` is never cut. Today there are 11 groups. Choosing `FEWER` over the cap is the right priority; it should be remembered when groups are added.
- **F4: confirmed.**
  - The probe now gives `fewer: [… passes 1063 -> none]` and `growth: []`.
  - `--accept-growth` alone is refused, with "pass counts fell … say --accept-fewer-passes".
  - The new mutant, which files the dropped metric as growth again, is killed.
- **F5: confirmed.**
  - The match of the new class `no-conftest` is anchored on the exact module list (`\['numpy\.conftest'\]$`). If any other module joins that failure, the failure fits no class and the group check fails. `test-only-modules` now matches `_multiarray_tests` only.
  - The recount gives 19 classes and 26 gaps. Every gap's count and digest equals its list. The closers are spec 051 15, the README 9, question 89 2.
  - The README states the new fact: the zip carries no `tests` folders and no `conftest.py` (READ).
  - Spec 051's Decision 12 does not touch this class, so it stays a README-closed gap after 051.
- **F6: confirmed, with one small hole left.**
  - F6b (the entry need not start) is killed by three cases.
  - **F6a survives.** It drops the trap check's own "no `E` line" test. The parametrized case `no-E-line` never starts its entry, so F6b's rule catches it first. The gap: a session that starts its entry, does not trap, and ends without an `E` line would pass the check under the mutant. The code is right today (READ).
  - U16 now survives too, but it is equivalent. Dropping `if run.trapped` changes nothing, because a trapped run has no `E` line and `_ended` reports the trap first (READ).
  - **To close F6a:** one more case. Its stream is `C …`, then `S <entry>::t` with no `E` line, and the run did not trap; expect the "no E line" finding.

  This is low. The lane may take it as a follow-up note rather than hold the landing.
- **S7 is still equivalent**, as the review said.
- **Mutant totals:**
  - review set and new ones: 45 run; 42 killed;
  - 3 survive: S7 and U16, both equivalent, and F6a, the small gap above.

**The specification.** The new "After the build review" paragraph states the move to 19 classes and 26 gaps. The body still says 18 classes, 25 entries and 268 lines in several places:
- lines 21, 464, 660, 727 and 782;
- the landing notes' 37 checks.

The rebase below rewrites those numbers anyway. The lane should make the body agree then.

### Rebase onto spec 051: what the lane must re-check

050 now lands after 051. So it will be judged on 051's artifact set, with 051's patches: the amended 0001 and the new 0002. Its tables were measured on `s-0cdc7b2bd78db6f5`; every one must be re-derived. In order:

1. **The frozen set and the tie.** Judge on 051's accepted set. The MANIFEST tie must hold with 051's `recipe` lines for `recipes/patches/numpy-2.5.2/*.patch`. A tie failure names the patch.
2. **Seen failing first, again (criterion 2).** Run the 11 groups on 051's set with 050's classes, lists and trap entries as they stand. Record what changed.
   - Expected, per 051's Decision 12:
     - the six `zip-code-names` classes and the two `patch-0001-*` classes empty;
     - the seven trap checks pass, so each gap says "remove the gap".
   - Any other difference is explained in the notes before a list changes.
3. **Applying condition C1 as written.**
   - Each emptied class keeps its id and an empty list file, and loses its gap.
   - The seven `[[trap]]` entries, their gaps, and the `not_selected` entry for `test_casting_unittests.py` and `test_arraymethod.py` are deleted.
   - Because 050 has never been accepted on main, those trap and class checks have no accepted entries. So **no `--retire`** is needed. The rules check must still pass: empty list ⇔ no gap; every trap has its gap.
4. **The two returning files.**
   - `test_casting_unittests.py` and `test_arraymethod.py` run in `numpy-core` for the first time.
   - A failure gets a class only with a real closer, and the notes give the counts.
   - A new trap gets a `[[trap]]` entry, a gap and a named follow-up specification (051's Decision 12, its F4).
   - No new class is closed by the README unless the README states that fact.
5. **New baselines.**
   - Report the passes per group and the total. They will exceed 62,569 (INFERRED).
   - Report fuel per group, run twice for repeat (criterion 7).
   - Check the caps: `numpy-core` grows by two files, and its cap must still exceed 1.5 × its fuel. The caps' sum must stay at most 3×10¹² (the rules check).
   - Check the spent-fuel budget: under 1.8×10¹².
   - These become the first accepted values, so no `--accept-fewer-passes` or `--accept-growth` applies to 050's own checks.
6. **The counts everywhere.** The gap total, the classes, the closers line (spec 051's 15 go to 0), and the "next:" line must agree in all of these:
   - the README's Measured row and its "Known defects" (051 removes the traps and warnings lines; the masked-save line also goes);
   - the CHANGELOG line;
   - spec 050's tables, criteria, Design and landing notes;
   - spec 002's amendment lines, where they cite counts.
7. **A short review of the rebase delta.** The changes to the lists, `numpy.toml` and `known_gaps.toml`, and the two returning files' outcomes, are judge changes made after this review. Rule "nothing lands unreviewed" applies. A fresh reviewer checks the delta against 051's Decision 12 and this list, and recounts the gaps with `scan.digest`; it need not repeat the mutants. The harness code does not change on rebase, so the mutant results above carry over if `tests/harness/` is unchanged by the rebase (`git diff` to confirm).
8. **The lane's run.**
   - Fetch the kit in the main tree.
   - Judge the exact rebased commit there.
   - Cite a ratchet line with no `unrun locally` and no `upstream unrun`; lost 0, absent 0, grew 0 against 051's accepted state; no `FEWER`.
   - Use `--accept-judge "<reason>"` only.

### Verdict on the revision

**Confirmed: 050 lands, after its rebase onto 051 and the re-check above.** F1 to F5 are fixed as their dispositions say, and the mutants that survived the review (U5, U6, S9, S13) are now killed. F6 is fixed in behaviour. One unit case is missing (F6a, low), which the lane may add on the rebase or record as a follow-up. No path admits a failure silently. No path lowers `passes` without `--accept-fewer-passes`. The verdict line can no longer be cut.

One line: F1 to F6 hold (42 of 45 mutants killed; two survivors equivalent, one low); 050 lands once it is rebased onto 051, its tables re-derived on 051's set under C1, and that delta reviewed.
