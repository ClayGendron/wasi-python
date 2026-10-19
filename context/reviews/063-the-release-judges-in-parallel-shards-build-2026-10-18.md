# Review of 063: the release judges in parallel shards (build)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude). It wrote none of the specification, its pre-build review
  or its build.
- **Reviewed:** `git diff 5b00cca..2efcece` on `spec/063-the-release-judges-in-parallel-shards`
  (worktree `wasi_python-063`). That is 31 files, +4,496 −85, in five commits: `8553753` (the build),
  `e163974`, `070ee4c` and `0815007` (fixes from the dry runs) and `2efcece` (landing notes). I read
  it against the specification on the branch, including its "Amended at build" section and
  landing notes, against AGENTS.md, constitution §5.6 and §5.7, rule 6b, question 98 in
  `context/decisions.md`, and against 057's build review as a model.
- **Evidence:** everything is beside this file, in the scratchpad folder `063-buildreview/`.
  `fast-n3.log`, `full-n3.log` and the two `*-latest.json` files are the judge runs.
  `gather-run4/` holds run 4's real CI records, the gather run over them, and the merged record.
  `plan_probe.py` and its log check the plan's coverage. `mutate_coe.py` and its log are the
  workflow mutation. `sigill_probe/` holds the faulthandler probes. `same_probe.py` and its log
  are the sameness comparisons. `refusals.log` holds the `--shard` refusals.

Labels: **EXECUTED** means I ran it here. **READ** means I read it in code, logs or documents.
**INFERRED** means I reasoned it from what I ran or read.

## What I re-ran

- **The fast tier.** `uv run pytest -m "not slow" -n 3` in the worktree, against the frozen set
  `s-4eb5418a2b1bb553-c353b1d9` (`WASI_PYTHON_ARTIFACTS`), gave **1711 passed, 4 skipped in
  216.11s**, exit 0. The scoreboard read `371/419 pass · 0 gap · 2 blocked · 0 fail · 46
  deselected (unit suite 1340/1342)`. The ratchet read `lost 0 · absent 0 · unrun 0 · unrun
  locally 1 · gained 4 · grew 0 · upstream unrun 31 · not selected 32 · judge changed: …`. This
  equals the builder's `fast-n3-final.log`. EXECUTED.
- **The full judge.** `uv run pytest -n 3` on the same set gave **1743 passed, 4 skipped, 14
  xfailed in 387.94s**, exit 0. The scoreboard read `403/419 pass · 14 gap · 2 blocked · 0 fail
  (unit suite 1340/1342)`, blocked only by `prior-art clones` and `three systems`. The ratchet
  read `lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 4 · grew 0 · judge changed:
  tests/checks/test_rules.py, tests/checks/test_v1_2_hostile_guest.py, tests/harness/gather.py
  and 12 more`. The worktree's `build/progress/latest.json` is kept, and a copy is
  `full-n3-latest.json`. EXECUTED.
- **Sameness against the builder's serial run.** `sameness.py` compared my `-n 3` record with
  the builder's serial record `full-serial-latest.json`, taken on `8553753`. The only difference
  is `suite` (1340/1342 against 1339/1341), which is the one unit test added after `8553753`. No
  check differs. EXECUTED.
- **Lint.** `ruff check src tests` reported "All checks passed!". `ruff format --check src
  tests` reported "95 files already formatted". EXECUTED.
- **The gather on the real CI records of run 4.** I downloaded `39186533835`'s 19 record
  artifacts. The build record was one of them. For the failing Windows leg I used its diagnostic
  record, `record-windows-own-guest-failed-1`. I laid them out as the gather job does and ran
  `gather.py` in a scratch clone at `0815007`, the run's commit. I set `RECORD_*` to the SHA-256
  of each file and `WASM_SHA256` to the build record's `meta.artifact`. That value,
  `1655014314805b58…`, is the frozen set's `python.wasm` hash (EXECUTED, `shasum`).
  The gather exited 1. It was red **only** for the three Windows goal checks: G4 `fail` and G5
  `lost`, three lines each. G1, G2, G3, G6 and G7 all held on real records from three systems.
  All 19 records carry the same judge hash `60fe4e4ed5…`, which is the gather's own (LF
  everywhere, `.gitattributes`). Each has `dirty: false`, `workers: 0` and one `--progress-latest`
  override. The gather wrote nothing in the clone (`git status` was clean). EXECUTED,
  `gather-run4/gather.log`.
- **The plan on the real collection.** The collection is 419 goal checks and 1,342 unit tests.
  No item runs twice on any system, and every item is in some shard. Windows runs 838 items: every
  goal check except `test_rules.py` (43), the v1.5 file (31) and the 29 upstream checks of other
  groups. It also runs every item of the seven files that pre-063 `verify` ran on Windows (28,
  6, 27, 151, 27, 25 and 44 items). EXECUTED, `plan_probe.log`.
- **Refusals of `--shard`.** An unknown name, `-n 2` and a node id were each refused before
  collection, with exit 4. The space form `--shard own-guest` works. `--shard build` fails loudly
  (exit 4), because pytest reads `build` as a path. EXECUTED, `refusals.log`.

## Findings, most severe first

### F1 (High; blocks landing): a product check file now falls quietly off Windows, and the rebase already does it

Departure 2 changed `rest` to run on macOS and Linux only. Rule (e) still requires every `files`
shard to run on all three systems. But `select` gives every file that no shard names to `rest`
(READ, `shards.select`). So a new test file lands off Windows without anyone deciding it, even
when it holds product checks.

This is not hypothetical. Main at `7d377dd` adds `tests/checks/test_v1_3_lxml.py`, nine goal
checks of the lxml build (spec 046, READ). After the rebase that file is in no `files` list. It
goes to `own-rest` and never runs on Windows, and every rule and the gather stay green. INFERRED
from the code and main's tree.

The plan file's own comment says `rest` holds "the rules and the judge's own tooling". Nothing
enforces that.

Fix:
- At the rebase, put `test_v1_3_lxml.py` in `own-guest`, or in another shard that runs on all
  three systems.
- Add a plan rule, seen failing first. Every `tests/checks/` file except `test_rules.py`, the
  upstream file and the `build` shard's files must sit in a `files` shard on all three systems.
  So must every product unit file (`tests/test_api.py`, `tests/unit/test_runner_*.py`,
  `test_cli.py` and the tools files). Then `rest` can only hold rules and tooling, and the
  comment becomes a check.

Today's plan passes that rule. The plan probe shows every v1.1 to v1.4 file and every runner
file on Windows. EXECUTED.

### F2 (High; blocks landing): criterion 10 is not met, because the gather never ran in CI

`gather` was **skipped** in all four dispatched runs. It needs every judge leg, and Windows
`own-guest` failed (READ, `gh run view`). Decision 18 lists what only a dry run proves. Three of
those items are still unproven:
- that GitHub merges each matrix leg's own output names when other legs leave them empty;
- that the comma-joined `artifact-ids` downloads work;
- that the gather step itself runs on the runner.

The local gather over run 4's real records (above) removes much of the doubt about G1 to G7 on
real records, but it bypasses all three of those mechanics. EXECUTED and INFERRED.

063 lands once a branch dry run, after 076 and the rebase, passes every job. That includes
`gather`, with its `three systems: darwin linux win32 on …` line recorded in the landing notes.

### F3 (Medium for 063, because it must be recorded before landing; a real product defect): the Linux SIGILL is reproduced

The landing notes leave the SIGILL INFERRED and "not chased". AGENTS.md rule 3 says a new failure
mode, once seen, becomes a check, or a gap entry that names its closer. This one is real and
reaches the product.

- **The mechanism.** On Linux, wasmtime catches a guest trap through its signal handlers.
  Suppose `faulthandler` is enabled **after** the first engine exists. That is what an inline
  pytest session does when it configures and unconfigures, and `test_plugin.py` runs one before
  `test_runner_calls.py` in the old `own-rest`. Then faulthandler's handler runs first. It
  restores wasmtime's handler and re-raises the signal from outside wasm, and the process dies.
  A probe with wasmtime 49.0.0 in a `python:3.13-slim` container (aarch64) showed this:
  - an `unreachable` trap with faulthandler off, or enabled before the engine, is a `Trap`
    (exit 0);
  - after an enable, or a re-enable, that follows the engine, the same trap kills the process
    with "Fatal Python error: Illegal instruction" (exit -4).

  On macOS all four cases exit 0, because wasmtime uses Mach ports there. EXECUTED,
  `sigill_probe/probe.log` and `probe-darwin.log`.
- **It reaches the product.** I mounted the branch's `src/` and the frozen set read-only in the
  same container. A pure-Python guest ran either `json.loads('['*200000 + ']'*200000)` or
  unbounded recursion.
  - In a plain host process, `wasi_python.run` returns `trapped 'stack overflow'`.
  - When faulthandler was re-enabled after the runner's first call, **the host process dies**
    (exit -4).

  So a hostile guest can kill the embedding host on Linux whenever that host enabled
  faulthandler after its first call. EXECUTED, `sigill_probe/product_probe.log`.
- **For 063.** Separating the runner files into `own-runner` is an acceptable way to keep the
  release green. 063 does not cause the defect. But the order dependence is now known, and the
  trap is product behaviour. Before 063 lands:
  - record a check, or a `known_gaps.toml` entry whose closer is a reserved spec, for the
    host-crash case;
  - name the case for the next release's threat-model review (constitution §5.6);
  - replace the landing notes' INFERRED explanation with this evidence.

  The fix belongs to the product, not to 063.

### F4 (Medium; a condition on 076): of the four Windows failures, none is itself a security defect, but the bad-grant failure hides about twenty security refusals never run on Windows

- **`test_a_bad_grant_is_refused_before_any_work`.** On Windows, `_walk_windows` takes
  `os.path.abspath` of the root when judging (READ). So `base\new\..\x` becomes `base\x`, which
  is missing, and the runner may make it. POSIX refuses the same root, because `..` follows a
  missing folder (`_walk_posix`).
  - Win32 itself resolves `..` by spelling, before any open. The walk then opens every component
    of that normalised path and refuses reparse points. No link in `new` can redirect anything,
    and the root made is the one named. INFERRED: **not a security defect**, but a parity choice
    for 076, which can refuse for parity or correct the expectation.
  - The real problem is different. `pytest.raises` fails on line 685, so **every refusal after
    it has never run on Windows.** Pre-063 `verify` never ran this file (READ, main's workflow).
    The unrun refusals are: the module cache, the artifact set, the temporary folder and the
    moved temporary folder; wasmtime-py's code; the host Python's stdlib and `Scripts\`;
    read-only inside writable; the same guest path; the case-swapped spelling inside the cache
    (a branch that exists **for** win32); the missing grant; and the type checks. READ.
  - 076 must split or correct that line, so that the rest runs green on Windows before 063
    lands.
- **`test_a_read_only_grant_refuses_every_write[plain|snapshot]`.** All 30 kinds of write are
  refused with EPERM (63), and the control write succeeds (READ, run 4's log). Writing to a read
  descriptor answers EACCES (2) instead of EBADF (8). The write through a link answers EPERM
  instead of ENOENT, because no link was made on Windows and the read-only grant refuses first.
  Both are refusals, and both are stricter than expected. Errno parity only. INFERRED.
- **`test_the_rename_rule_forward_is_fuel_neutral`.** On Windows the guard returns ENOTDIR (54),
  the POSIX answer, and native wasmtime returns ENOENT (44). Fuel is equal (2005 on both sides).
  Both refuse. Parity only. But the test stops at its first assert, so its loop over every cap,
  and its `ENOTDIR` assert, have never run on Windows. READ and INFERRED.

### F5 (Low): `PYTHONUTF8=1` covers the product legs too

The variable is set at job level. So Windows `own-guest`, `own-runner` and `own-embedding` now
run in UTF-8 mode. The pre-063 `verify` ran the product checks without it (READ). A
locale-codec bug in `src/` would be hidden.

Today the risk is small. The only text reads in `src/` without an encoding are MANIFEST and
`/proc/.../boot_id`, which is Linux only (READ). The frozen set's MANIFEST has 0 non-ASCII bytes
(EXECUTED, `grep`). The Windows `verify` step, which installs the wheel, still runs without the
variable (READ).

Accept it, and answer in writing. Two follow-ups would close it: a rule that every text read in
`src/` names an encoding, or making the judge's own reads `encoding="utf-8"` and dropping the
variable.

### F6 (Low): the gather is not red on a failed unit test

G3 checks unit tests by count and digest, and G4 checks only goal checks. On run 4's records the
merged scoreboard showed `unit suite 3173/3197, 23 skipped`, one failed (the rename test), with
no RED line for it. EXECUTED.

In the workflow this is not a hole today. A failed shard hands on no record, and the gather is
skipped. 057's rule 17 refuses any `continue-on-error:`, and 063's rule 4 refuses `||` and
`set +e`. A mutation that adds `continue-on-error: true` to the three shard steps fails rule 17,
although 063's scan alone stays empty (EXECUTED, `mutate_coe.log`).

For defence in depth, add to G4: each record's `suite.total == passed + skipped`.

### F7 (Low): the tag detection in `main()` is untested

The G7 tag clause rests on
`GITHUB_EVENT_NAME == "push" and GITHUB_REF_TYPE == "tag"` in `gather.main`. `test_gather.py`
only passes `tag=` to `gather()` (READ). A typo there would silently drop the clause that the
release's judge be the accepted one. Move it into a small function and test it in both cases.

### F8 (Low; documents): claims that are now stale or wrong

- CHANGELOG: "the whole judge on all three systems, in sixteen parallel jobs". `own-rest` is not
  on Windows, and there are 18 judge legs (5 + 9 + 4; READ, run 4's timeline).
- The landing notes say "the 23 judge legs". There are 18.
- Intent says "The judge runs in full on macOS, Linux and Windows". The Design section's
  CHANGELOG draft says the same.
- The header of `tests/release_shards.toml` and the docstring of `shards.py` both say
  `--shard <name>`, which goes against the `=` amendment.
- "Every one in the judge's own tooling" (Amended at build). `test_zip_directory.py` tests the
  product's recipe modules `_zip_directory` and `_zip_resources` on the host. Its six Windows
  failures are about path separators on the host. The guest check
  `test_v1_3_the_zips_directory.py` does run on Windows. INFERRED: no product loss, but the
  sentence should say this.
- Criterion 8 says "0 differences" with "the darwin `suite`". With the darwin suite alone,
  `same_probe` finds one difference, 1330/1332 against 1339/1341, because `test_pins.py`'s 9
  tests are in the `build` suite. With darwin plus build it is 0. Say which convention was used.
  EXECUTED.
- Decision 2 (f): "the plugin asserts again at selection". It does not (READ, the plugin's
  diff). Rule (f) of `plan_errors` covers groups.

## The seven departures

1. **`--shard=NAME` only.** Accepted. The space form fails loudly when the name is also a path
   (`build`, exit 4), and it works otherwise. The `=` form is safe everywhere. EXECUTED. See F8
   for the two texts that still show the space form.
2. **`own-rest` off Windows; `own-runner` on all three.** Accepted **with F1**. No check that ran
   on Windows before 063 is lost. The seven files of the old `verify` all run there, and so do
   `test_v1_2_hostile_guest`, the zips' directory, matplotlib, the public API, mounts and the
   runner's units (EXECUTED, `plan_probe.log`). What leaves Windows is the rules, the v1.5 file
   and tooling that never ran there. Decision 18 allows the change, and the reason is in the plan
   file. The rule as written lets future product files default off Windows, which is F1.
3. **`PYTHONUTF8=1`.** Accepted, with F5.
4. **The need `descriptor limit`.** Accepted. It replaces a skip without a need. It is met
   wherever `resource` imports, which is POSIX (READ). The gather allows it on any system. It
   could be limited to win32, but on POSIX it is always met. Note only.
5. **A `via` may name a `later` entry.** Accepted. matplotlib's five C libraries are reached
   only through matplotlib, which is `later` (closer 066, reserved). The `later` entry carries
   the closer the rule needs. Otherwise the confirmed text would have refused the review's own
   example.
6. **`GITHUB_EVENT_NAME` and `GITHUB_REF_TYPE` read, not bound.** Accepted. GitHub does not let a
   step override `GITHUB_*` variables (READ, GitHub's documentation on default variables). A
   dispatched run on a tag ref reads `workflow_dispatch`, so the tag clause does not apply. In
   that case `attest` and `publish` do not run either, so this is consistent (READ, their `if:`).
   Testing is F7.
7. **The `plan9-amd64` self-test.** Accepted. `linux-x86_64` is the host's own platform on a
   Linux runner. Its twin in `test_landing_lane` runs the same test through a worktree, so the
   one change fixes both. Linux `own-rest` was green in run 4 (READ).

## The open problems

- **The four Windows checks.** None of them is a security defect in itself (F4). The bad-grant
  one hides unrun security refusals, so 076 must make them run. Apart from F1, F2, F3 and F8, 063
  is ready. The shard plan, the plugin, the fetch, the gather logic and the workflow scan all
  hold, both on the real CI records and locally.
- **The SIGILL.** The separation by the plan is acceptable for 063. Leaving it unchased is not:
  it is reproduced and it reaches the product (F3).
- **Is the merged record equal to a serial run?** Yes. The builder's merged record against its
  serial run gives 0 differences when `suite` is darwin plus build, and 1 (suite only) with
  darwin alone (EXECUTED). Run 4's real merged record against the serial run differs in exactly
  these places, all expected:
  - the three Windows failures;
  - `test_mount_descriptors_are_bounded[plain|snapshot]`, blocked by `descriptor limit`;
  - the oracle golden, blocked by `oracle`;
  - seven upstream groups whose fuel comes from the Linux record, up to 1.7e-3 away from
    darwin's.

  EXECUTED, `same_probe.log`.
- **Can the gather hide a failure?** Not a failing goal check. The worst status wins, G4 reads
  every record, and G5 compares each record with `accepted.json`, all EXECUTED on real records. A
  failed unit test can only be hidden if the job's exit code is ignored, and two scan rules
  forbid that (F6).

## Notes (no action required)

- N1. The merged record ranks `blocked` above `pass` (Decision 9). A check that passes on macOS
  and Linux and is blocked on Windows therefore shows as `blocked` in the release record
  (`blocked by: descriptor limit 2 · oracle 1`).
- N2. `gather.collect()` leaks pytest's per-file counts into the gather's output.
  `redirect_stdout` does not catch the terminal writer. Cosmetic.
- N3. The `three systems:` line is inserted inside the two-line "not machine-checked" paragraph.
  Cosmetic.
- N4. At the rebase, `packages.toml` needs entries for `lxml`, `libxml2` and `libxslt`. The rules
  check will fail loudly until it has them (INFERRED, from main's `paths.PACKAGES` and
  `SOURCE_COMPONENTS`). This is separate from F1, which no check catches.
- N5. Times: 18.8 minutes to the last judge leg in run 4, against 29.1 to 33.4 before (READ, the
  timelines).

## Verdict

**Lands once F1, F2, F3, F4 and F8.**
- F1: `test_v1_3_lxml.py` in a shard that runs on all three systems at the rebase, and the plan
  rule seen failing first.
- F2: a green branch dry run that includes `gather`.
- F3: the SIGILL recorded as a check or a gap with its closer.
- F4: 076 lands first, and the masked refusals run green on Windows.
- F8: the documents corrected.

F5, F6 and F7 may be fixed or answered in writing.

One line: the shard plan, the plugin and the gather are sound on real CI records and lose no
check that ran on Windows before; it lands once new product files cannot default off Windows
(lxml at the rebase), a dry run proves the gather, the reproduced Linux SIGILL host crash is
recorded, and 076 makes the hidden Windows refusals run.


# Confirmation of 063's revision against its build review

- **Date:** 2026-10-18
- **Reviewer:** the same fresh agent that wrote the build review beside this file. It wrote none
  of the revision.
- **Reviewed:** `spec/063-the-release-judges-in-parallel-shards` at `1488377`, rebased onto main
  `6fd89e0`. The revision is `3578757`, and `1488377` adds its landing notes.
  - I read `git range-diff 5b00cca..2efcece 6fd89e0..63b16fe`, then `git diff 63b16fe 3578757`
    and the spec's Disposition of the build review.
  - Builder's evidence: `build/reviews-evidence/063-build2/`.
- **Scope:** every finding except F2. F2, the final branch dry run with `gather`, waits on 076.
  F4 belongs to 076.
- **Evidence:** in the `confirm/` folder beside this file.

Labels: **EXECUTED** means I ran it here. **READ** means I read it. **INFERRED** means I reasoned it.

## What I re-ran

- **The fast tier.** `uv run pytest -m "not slow" -n 3` in the worktree, against
  `s-ff5246a2c2f1a52b`, gave **1772 passed, 5 skipped in 379.72s**, exit 0.
  - The scoreboard read `394/446 pass · 0 gap · 3 blocked · 0 fail · 49 deselected (unit suite
    1378/1380)`.
  - Three needs blocked a check: `Linux host` (the new check, as intended on macOS),
    `prior-art clones` and `three systems`.
  - The ratchet read `lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 4 · grew 0 · …
    judge changed: … and 13 more`.
  - This equals the builder's `063-build2/fast-n3.log`.

  EXECUTED, `confirm/fast-n3.log`. The worktree's `build/progress/latest.json` is kept, with a
  copy at `confirm/fast-n3-latest.json`.
- **The plan probe on the revised tree.**
  - The collection is 446 goal checks and 1,380 unit tests.
  - No item runs twice on any system, and every item is in some shard.
  - Windows runs 872 items. The goal checks it does not run are `test_rules.py` (43), the v1.5
    file (34) and 29 upstream checks of other groups.
  - The seven files that pre-063 `verify` ran are all on Windows.
  - `product_files` holds 26 files, `test_v1_3_lxml.py` among them, and `plan_errors` on the real
    plan is empty.

  EXECUTED, `confirm/plan_probe.log`.
- **The new F3 check on Linux, run by pytest in containers.** The setup:
  - a scratch clone at `1488377`;
  - the frozen set `s-ff5246a2c2f1a52b`, mounted read-only;
  - `python:3.13-slim` with wasmtime 49.0.0, pytest 9.1.1, pytest-xdist 3.8.0 and pluggy 1.7.0;
  - the command `python -m pytest -p no:cacheprovider tests/checks/test_v1_2_hostile_guest.py::test_a_guest_trap_cannot_kill_a_host_that_enabled_faulthandler`.

  The results:
  - **aarch64:** `1 xfailed`. The record shows `gap`, with the reason `findings: 1 finding(s),
    digest b5a565e2e3c0: the host process died by a signal … first engine (signal 4)`.
    EXECUTED, `confirm/linux-check.log`.
  - **x86_64** (`--platform linux/amd64`, emulated on Apple silicon): the same `gap` with the
    same digest `b5a565e2e3c0` (signal 4). EXECUTED, `confirm/linux-check-amd64.log`. Emulation
    may not handle signals exactly as a native GitHub runner does. The signal number is kept
    outside the digest, so a different native signal (SIGSEGV) would still match. INFERRED.
  - **The digest by itself.** `scan.report([HOST_DIED])` gives `1 finding(s), digest
    b5a565e2e3c0` on macOS too. EXECUTED, `confirm/digest.py`.

## Each finding

- **F1: confirmed.**
  - Rule (g) is in `shards.plan_errors`, through `product_files`. That is every `tests/checks/`
    file except `test_rules.py`, the upstream file and the `build` shard's files, plus
    `tests/test_api.py`, `tests/unit/test_runner_*.py`, `test_cli.py`, `test_tools.py`,
    `test_async_tools.py` and `test_guest_tools.py`. Each must sit in a `files` shard on all three
    systems. READ.
  - `test_v1_3_lxml.py` is in `own-guest`. READ, and EXECUTED with the probe.
  - It was seen failing first. Before the move, `test_release_shards_cover_the_judge` named
    `(g) tests/checks/test_v1_3_lxml.py …` (READ, `063-build2/f1-seen-failing.log`).
  - Unit variants cover a new `test_v1_9_*.py`, a new `test_runner_*.py`, `test_cli.py` left to
    `rest`, and a product file in a shard off Windows. A rules or tooling file may stay in `rest`.
    READ, and green in the fast tier.
  - The plan header, Decision 2 and Intent now say the same.
- **F3: confirmed.**
  - The check runs the review's case in a child process: a first call, then
    `faulthandler.enable()`, then a guest stack overflow. It fails when the child dies by a
    signal, and also on any other unexpected outcome. READ.
  - It needs `Linux host`, a new need, and the gather's `CI_NEEDS` allows that need to block. So
    the check is blocked on the lane's macOS and on Windows, as intended. READ.
  - The gap names spec 071 through the roadmap. The roadmap's new `Reserved:` paragraph says 071
    is widened to own this case. READ.
  - The gap's digest matches on Linux (above). The README's *Safety* section warns embedders. The
    landing notes name the case for the next threat-model review. READ.
- **F5: answered; I accept the answer.** The shard step is one pytest run that holds the judge's
  reads and the product checks together. So `PYTHONUTF8` cannot be limited to the judge's reads
  without splitting that run. The product's own text reads are ASCII or Linux-only, and Windows
  `verify` still runs without the variable. The follow-ups are deferred to a later judge change.
- **F6: confirmed.** G4 now requires `suite.total == passed + skipped` for every record, and red
  names `G4 <system>/<shard>: N unit test(s) failed`. A mutation in `test_gather.py` covers it.
  READ, and green in the fast tier.
- **F7: confirmed.** `gather.is_tag(environ)` is used by `main`.
  `test_only_a_pushed_tag_is_a_tag` covers four cases: a pushed tag, a pushed branch, a dispatch
  on a tag ref, and an empty environment. READ.
- **F8: confirmed.** Each stale text is fixed:
  - The CHANGELOG entry is under 0.1.0a7. It says eighteen jobs, product checks on three systems
    and tooling on two.
  - The landing notes say 18 legs.
  - Intent and the Design section's CHANGELOG draft are corrected.
  - `--shard=<name>` is now used in the plan header and in `shards.py`.
  - The tooling sentence now names `test_zip_directory`'s host-side tests of the recipe modules.
  - Decision 2 (f) states only what rule (f) does.
  - The suite convention is named in the landing notes ("darwin's plus `build`'s … 0
    differences").

  Criterion 8 itself still reads "with the darwin `suite`", as confirmed. The landing notes now
  say which convention was used, which is what F8 asked. READ.
- **The rebase.**
  - `packages.toml` gains `lxml` (`later`, closer `spec 066`, whose reservation in the roadmap
    now names lxml), and `libxml2` and `libxslt` (`via = "lxml"`, allowed by departure 5).
    `test_every_package_names_its_own_suite` is green in the fast tier.
  - The range-diff shows the build commit `4848672` turning main's zero-patch count from 18 back
    to 15, in both the comment and the `grep`. This is a conflict resolution against 046.
    `3578757` restores 18, so the head's `release.yml` equals main's on those lines. READ.
  - So the intermediate commits `4848672` to `63b16fe` carry a wrong tree count, while the head is
    right. If the lane lands the branch commit by commit, only the head is green on its own
    (AGENTS.md rule 9). Squashing, or noting it, is the lane's choice. Note only.
  - `bb08f92`, `8122314` and `74812cc` are unchanged by the rebase (`=`). EXECUTED, `range-diff`.

## Side effect

Running with `--platform linux/amd64` pulled `python:3.13-slim` again. The local tag now points to
the multi-architecture index (`70729b46…`), and the earlier arm64-only image is dangling
(`7c61056e61ac`). Nothing else on the machine was touched. No git tree was changed, and I
neither pushed nor dispatched anything.

## Verdict

**Confirmed except F2.** F2, a branch dry run with `gather` green and its `three systems:` line
recorded, follows 076 and the rebase onto it. F4 is 076's.

## Addendum, 2026-10-19: F2, the judge change to 046's check, and the rebase onto `3ea0582`

**Reviewed:**
- the branch at `0798c62`. That commit holds the landing notes only: one file, the
  specification. EXECUTED, `git show --stat`.
- `f6046cb`, the rebase onto main `3ea0582` (047, 055 and 076);
- `5715430`, the judge change to `test_v1_3_lxml.py`;
- dry run `39205611721`, run on `5715430`;
- the builder's evidence in `build/reviews-evidence/063-build3/`.

**Evidence:** in `confirm2/` beside this file: the gather job's log, all 19 shard records, the
release record downloaded from the run, and the plan probe at `0798c62`.

### F2: confirmed (EXECUTED, from the run itself)

- The run was dispatched with `workflow_dispatch` on the branch, at head `5715430`. Its
  conclusion is **success**: 26 jobs succeeded and 3 were skipped (`attest`, `publish`, `pypi`,
  as a dry run requires). The gather job, `117912797303`, succeeded. Wall time to the end was 20.2
  minutes, by the builder's timeline (READ).
- **The gather's own log reads:**
  - `wasi_python v1: 476/496 pass · 14 gap · 6 blocked · 0 fail (unit suite 3293/3316, 23 skipped)`,
    so no unit test failed under the new G4;
  - `blocked by: descriptor limit 2 · Linux host 1 · oracle 1 · prior-art clones 1 · three systems 1`;
  - `three systems: darwin linux win32 on 18595c7f1806…`.

  There is no RED line.
- **The release record** names 19 records, commit `57154305`, and the artifact `18595c7f1806…`.
- So the mechanics that only a dry run could prove now hold:
  - matrix legs combining their outputs;
  - the downloads by comma-joined ids;
  - G1 to G7 on the runner.

### The faulthandler gap on native Linux: confirmed (EXECUTED)

- **Linux.** The record `record-linux-own-guest` (`linux-x86_64`) has
  `test_a_guest_trap_cannot_kill_a_host_that_enabled_faulthandler` as **gap**, with the reason
  `findings: 1 finding(s), digest b5a565e2e3c0: the host process died by a signal …`. This is
  a native x86_64 GitHub runner. It agrees with my aarch64 and emulated x86_64 container runs.
- **macOS and Windows.** In the macOS and Windows `own-guest` records the check is `blocked`
  by `Linux host`, as intended.
- **A note on the merged record.** It ranks `blocked` above `gap`, so this check shows as
  `blocked by: Linux host` and not among the 14 gaps. The known defect is visible in the Linux
  record and is G4-checked against `known_gaps.toml`, but not in the merged scoreboard's gap
  count. This is the same ranking issue as the build review's N1. Note only, not blocking.

### The judge change to 046's `test_stylesheets_and_entities_reach_only_grants`: honest, and not a weakening

- **What Windows did.** The run before it, `39203592916`, was the first to run the lxml file on
  Windows. Both parameters failed with
  `XMLSyntaxError 'failed to load "file://D:%5Ca%5C…%5Cro-…%5Csecret.txt": Operation not permitted'`.
  READ, `063-build3/windows-own-guest.log`.
  - The case names the granted file by its **host** spelling.
  - On POSIX that path does not exist in the guest, so libxml2 yields `<r/>`.
  - On Windows the drive and backslashes are no guest path. The open is refused (EPERM), and
    libxml2 raises.
  - Both mean the same thing: a host path reaches nothing. The read never happens.
- **Not a weakening.**
  - The macOS and Linux branch is unchanged, still exactly `ok` and `<r/>`.
  - The Windows expectation is no looser than the old one. It pins the kind (`XMLSyntaxError`),
    two parts of the message (`failed to load`, `Operation not permitted`), and adds an explicit
    failure if `SECRET` appears in the outcome.
  - The other eleven cases of the check are unchanged, and they passed on Windows in run 6: both
    parameters are `pass` in `record-windows-own-guest`. EXECUTED.
  - The old expectation had never run on Windows. This is the first Windows expectation, written
    from an observed run. It is not a relaxation of one that used to pass there.
- **Nit, not blocking.** The check's docstring still says "a host path outside every grant gives
  an empty element". It could add "(on Windows the load is refused)".
- **README: no change needed.** The lxml text (README, "XSLT reads and writes files by default")
  promises only "nothing outside a grant". It never mentions the empty element. That promise
  holds on Windows, where it is even stricter: the load fails loudly. A sentence would be
  optional.

### The rebase `f6046cb`: right

- **`release_shards.toml`.**
  - `tests/checks/test_v1_3_regex.py` (047) and `tests/checks/test_v1_4_sessions.py` (055) are in
    `own-guest`.
  - `tests/unit/test_runner_sessions.py` (055) is in `own-runner`.
  - All three are product files placed by rule (g), on all three systems.

  READ. The plan probe at `0798c62` reports 496 goal checks and 1,392 unit tests, no item twice on
  any system, and every item in some shard. Windows does not run only `test_rules.py`, the
  upstream checks of other groups and the v1.5 file. `plan_errors` is empty. EXECUTED,
  `confirm2/plan_probe.log`.
- **`packages.toml`.** It gains `regex` (`later`, closer spec 066). The roadmap's 066 now lists
  regex with matplotlib, pillow, kiwisolver and lxml. `regex` is in main's `paths.PACKAGES`.
  READ.
- **Nineteen trees.** `release.yml`'s comment says nineteen trees and its grep is
  `^19 passed, …`. Both equal main `3ea0582`'s lines. READ.
- **The judge.** The builder's fast tier at the head shows 1832 passed, 0 fail, lost 0. Its full
  judge (`-n 3`) shows 479/496, 14 gap, 0 fail, lost 0, 1869 passed. READ, `063-build3`. I did
  not re-run these: the dry run judged the whole plan on all three systems at `5715430`, and
  `0798c62` adds only the specification.

### For the lane's last rebase onto `d900dd9`, after 071

- **New test files.** Rule (g) will name any new product test file from 069 or 071 until it is
  placed, so this fails loudly.
- **If 071 fixes the faulthandler host crash,** the gap's check will pass. Its
  `known_gaps.toml` entry must then be retired with it, the plugin's usual handling of a gap that
  passes. The README's *Safety* paragraph must go too.
- **A new dry run.** The rebase touches `tests/` and the workflow, so rule 6b asks for a new dry
  run on main's exact commit before any tag.

### Verdict

**Confirmed, it lands**, after the lane's rebase and its serial judge, as usual. Every finding of
the build review is closed. F4 was closed by 076, and its masked refusals ran green on Windows in
this run. The only remaining items are notes: the merged record ranks `blocked` above `gap` for
the Linux-only check, and the docstring nit.

## Delta, 2026-10-19: the rebase onto `8f8de73` (069, 071, 080, 075) and `983f8e6`

**Reviewed:**
- the branch at `3161485`;
- `git range-diff 3ea0582..0798c62 8f8de73..3161485`;
- the new commits `4fe0a17` (`983f8e6` after the rebase), `d538a4c` and `3161485`;
- dry run `39225879599`, on `d538a4c`;
- the evidence in `063-build5/`.

**My evidence:** in `confirm3/` beside this file: the range-diff, the 19 shard records, the release
record, and `inline_probe.py` with its log.

### Nothing else moved (EXECUTED)

- **The range-diff.** All twelve confirmed commits map one to one. Nine are `=`. The three marked
  `!` (`b6596e6`, `fce6178`, `6718ab8`) differ only in context lines from main: 071's
  `SPEC_071`, the need `wasmtime cli`, its CLI check, 071's CHANGELOG lines, and 073's gap as
  the neighbour of 063's gap entry. Their own `+` lines are unchanged.
- **The three new commits.**
  - `4fe0a17` touches only:
    - the README (the retired *Safety* paragraph);
    - the specification;
    - `test_rules.py` (+2 blank lines; ruff is green in the builder's runs);
    - `test_v1_2_hostile_guest.py` (the check removed, with the `scan` import it used);
    - `test_v1_3_lxml.py` (the docstring only);
    - `gather.py` (in `CI_NEEDS`, `Linux host` out and `wasmtime cli` in, plus the comment);
    - `needs.py` (`Linux host` removed);
    - `known_gaps.toml` (the gap removed).
  - `d538a4c` and `3161485` change the specification only.

### Retiring 063's faulthandler check loses no coverage

- **071's check is a superset.** 071's `test_a_faulthandler_change_cannot_kill_the_host` has an
  `after` row that is 063's case. It runs a first call, then `faulthandler.enable()`, then the
  same deep `json.loads`, in a fresh child. It requires `returncode == 0`, so a host killed by a
  signal fails, as 063's `returncode < 0` did. It adds six more orders:
  - `before`, `before-then-disable`, `after-then-disable` (my probe's `reenable`, in spirit);
  - `signal-after`;
  - `session-turn-after`;
  - `none`.

  READ.
- **It runs everywhere.** It has no Linux-only need, so it runs on all three systems. In run
  `39225879599` all seven rows are `pass` in the macOS, Linux (x86_64) and Windows `own-guest`
  records. EXECUTED.
- **The one difference is by design.** 063's check wanted `None stack overflow` on Linux. 071
  now refuses the call on Linux with `RuntimeError` naming the remedy, and 071's check pins that
  refusal. 071's README text replaces the *Safety* paragraph. `Linux host` had no other user.
  READ.

### `wasmtime cli` allowed to block: it hides no failure, but its check runs in no release leg (D1)

- **Where it is blocked.** `test_recursion_raises_under_the_wasmtime_cli` (071) is in
  `test_v1_2_hostile_guest.py`, so in `own-guest`. It is `blocked` by `wasmtime cli` in the
  macOS, Linux and Windows `own-guest` records of `39225879599`. EXECUTED. The `build` shard
  does not hold that file.
- **So the release never runs it.** Allowing the need cannot hide a failure, because there is no
  leg where the check runs and could fail.
- **But main's release runs it today.** Main's build job, at `8f8de73`, runs the whole judge
  (`uv run pytest -p no:cacheprovider`) on the host that unpacked the CLI (READ). After 063, the
  release drops this one check. It still runs at every landing in the main tree. G7 ties the
  release's `python.wasm` to that acceptance, but the check also reads the stdlib zip and
  MANIFEST, which G7 does not tie. Those rest on the same-bytes job and on reproducibility.
  INFERRED.
- **D1 (Low): fix it or answer in writing, as the lane rules.** The cheapest fix restores main's
  coverage exactly. Move the check into a file of its own, listed in the `build` shard's `files`.
  Rule (g) exempts the build shard's files, and the build host has the CLI. The alternative is
  for `fetch.py --shard` to fetch the pinned CLI on the judge legs. A written answer would say
  that the release judges this check only through the lane's acceptance.

### Inline-session files stay apart from the runner's tests (080's open case): holds (EXECUTED)

- **Where the inline sessions are.** The files that run an **in-process** pytest session are
  `test_plugin.py`, `test_landing_lane.py` and `test_upstream.py` (`pytester.runpytest`). All
  three are in `own-rest` only.
  - `test_checks_wiring.py` and `test_several_cores.py` use `runpytest_subprocess`, also in
    `own-rest`.
  - The other files in the probe matched only `gc.collect()`.

  EXECUTED, `confirm3/inline_probe.log`, and READ.
- **Where the runner's tests are.** Rule (g) keeps every runner unit file and every product check
  out of `rest`. They sit in `own-runner`, `own-guest` and `own-embedding`, each its own process.
- **Note, not a finding.** `own-rest` still holds one tooling file that drives guests in process:
  `test_guest.py`, the judge's own driver, with its own `wasmtime.Engine`. Today it sorts before
  the inline sessions (`test_landing_lane`, `test_plugin`, `test_upstream`). A tooling file that
  sorted after them and trapped a guest in process could die on Linux. That would be loud (the
  leg fails), never silent. Spec 082, reserved, is where 080 left this.
- **The Linux `own-runner` failure** in `39211765022` (071's guard in `test_runner_async`) was
  fixed in 080's item 2 on main (READ, `dcd7e4c`). The leg is green in `39225879599`.

### The dry run `39225879599`: confirmed (EXECUTED)

- `workflow_dispatch` on the branch, at head `d538a4c`. Conclusion **success**: 26 jobs
  succeeded, and 3 were skipped (`attest`, `publish`, `pypi`).
- The release record's scoreboard reads:
  - `532/553 pass · 15 gap · 6 blocked · 0 fail (unit suite 3304/3327, 23 skipped)`;
  - `blocked by: descriptor limit 2 · oracle 1 · prior-art clones 1 · three systems 1 · wasmtime cli 1`;
  - `three systems: darwin linux win32 on ab78e8931e76…`.
- No record has a failed unit test. `3161485` adds only the specification.

### The lxml docstring

It now names Windows. My nit is closed. READ.

### Verdict

**Confirmed, it lands once D1 is fixed or answered in writing** (Low; the lane's call). Nothing
else is open. The lane's own serial judge and its rebase follow, as usual.

## D1, 2026-10-19: the CLI check named by node id in the build shard

**Reviewed:**
- the branch at `cb505e4`, on main `59b90b6`;
- `git range-diff 8f8de73..3161485 59b90b6..d825d5c`;
- `git diff d825d5c cb505e4`, which covers `c8c7ce4` (the file move, undone), `6b65726`
  (by node id), `b450aae` (blank lines) and `cb505e4` (the notes);
- dry run `39234703116`;
- `063-build6/`.

**My evidence:** in `confirm4/`: the range-diff, `node_probe.py` with its log, the shard and
gather tests' record, the 19 records and the release record.

### Nothing else moved (EXECUTED)

- **The range-diff.** All fifteen earlier commits map one to one. Thirteen are `=`. The two
  marked `!` (`16aa04c` and `34fd217`) differ only in context lines from main:
  - 079's lines in `test_scan.py`;
  - main's newer CHANGELOG lines.

  Their own `+` lines are unchanged.
- **The net diff since `d825d5c`.** It touches:
  - `gather.py`, where `CI_NEEDS` loses `wasmtime cli`;
  - `shards.py`, which gains `nodes`, `select`'s node branch and rule (h);
  - `release_shards.toml`, where the build shard has one `nodes` entry;
  - `test_shards.py`;
  - `test_scan.py`, two blank lines;
  - the specification.
- **`c8c7ce4`'s new file is gone.** No test file was added, and no node id changed.

### Rule (h) and its unit cases (READ; EXECUTED green)

- **What `plan_errors` (h) refuses:**
  - a `nodes` entry in any shard but `build`;
  - the same node named twice;
  - a node whose file is not a tracked test file, or that has no function part;
  - a node whose file has no `def <function>(`, with any parametrization stripped first.
- **The unit cases.** Each fails with its own line:
  - a non-build shard naming a node;
  - an untracked file;
  - a duplicate;
  - a node renamed to `test_gone` in the real plan, while the real plan stays clean.

  `test_a_check_named_by_node_goes_to_the_build_shard_alone` checks the selection: the named node
  goes to `build`, and the rest of its file stays in its own shard.
- **The run.** `test_shards.py`, `test_gather.py` and the rules checks for shards, packages and
  the release gave 102 passed. `ruff check` and `ruff format --check` are green. EXECUTED.
- **Limit, not a finding.** The check for a defined function is a text search. It cannot tell
  whether a parametrization id exists. A stale id would select nothing in `build`. The real check
  would then fall back to `own-guest`, be blocked by `wasmtime cli`, and turn the gather red,
  because that need is no longer allowed. So any drift is loud, and nothing is lost: G3 and the
  rule that every item sits in some share still hold.

### `select` hands the node to the build shard alone (EXECUTED, real collection)

- The collection is 554 goal checks and 1,504 unit tests, and the node is among them.
- The only shard taking the node is `build`.
- On macOS, Linux and Windows the node is not in any shard of that system, and no item runs twice
  on any system.
- No item is in no shard.
- Items in two shares across the whole plan come only from the upstream file, by design: a group
  runs on Linux plus one other system.
- The other 113 checks of `test_v1_2_hostile_guest.py` stay in `own-guest`.
- `plan_errors` on the real plan is empty.

### The gather's change hides nothing

- **It is stricter.** Removing `wasmtime cli` from `CI_NEEDS` only tightens G4 (a blocked check
  must name an allowed need) and G5's exemption. If the CLI were missing on the build host, or
  the node drifted back into `own-guest`, the check would be `blocked` and the gather red. READ,
  and `node_probe.log` shows `wasmtime cli in CI_NEEDS: False`.
- **It is proven on the runner.** Dry run `39234703116`, on `b450aae`, which `cb505e4` follows
  with the specification only: `success`, 26 jobs succeeded and 3 skipped.
  - The build record has the node as **pass**. Every other record has it `deselected`.
  - No record has a failed unit test.
  - The release scoreboard reads `534/554 pass · 15 gap · 5 blocked · 0 fail`, blocked only by
    `descriptor limit 2 · oracle 1 · prior-art clones 1 · three systems 1`, and
    `three systems: darwin linux win32 on ab78e8931e76…`.

  EXECUTED.
- **So the release again runs every check that main's release runs,** as D1 asked.

### Verdict

**Confirmed, it lands.** D1 is fixed, and nothing is open. The lane's rebase and serial judge
follow, as usual.
