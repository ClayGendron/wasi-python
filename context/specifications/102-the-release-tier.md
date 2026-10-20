# 102 — the release tier: upstream's slow tests run before a publication, not at every check

- **Status:** **drafted 2026-10-20** on `spec/102-the-release-tier` from main `5805af0`, for its
  pre-build review. It changes the release workflow (a new judge job, a dispatch input, the
  gather's conditions), so constitution §5.6 and AGENTS.md rule 8 require that review before it is
  built. It changes neither the guest's imports nor its exports, nor a byte of the artifact set:
  no line of `src/`, `scripts/`, `recipes/` or `downloads/SHA256SUMS` changes. A different agent
  reviews the draft and, later, the build.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** **build-class** by AGENTS.md's definition (it edits `.github/workflows/release.yml`)
  **and a judge change**. Edits to `tests/harness/upstream.py`, `tests/harness/packages.py`,
  `tests/harness/plugin.py`, `tests/harness/scoreboard.py`, `tests/harness/history.py`,
  `tests/harness/shards.py`, `tests/harness/gather.py`, `tests/harness/sameness.py`,
  `tests/harness/scan.py`; `tests/upstream/numpy.toml`, `pandas.toml`, `contourpy.toml`;
  `tests/release_shards.toml`; unit rows; `context/progress/README.md`, `README.md` (the testing
  paragraph), `CHANGELOG.md`. New groups and their class lists under `tests/upstream/expected/`,
  their gaps in `tests/known_gaps.toml`. The lane accepts with `--accept-judge`, and with
  `--accept-growth` only for what criterion 4 measures.
- **Depends on:**
  - **066** (wave 08, landed by then): the package families, `measured`, `rule_cap`, `[[split]]`
    by constructed `-k` expressions, contourpy's groups and the fourteen `upstream-plot-*` shards.
    102 changes contourpy's selection (Decision 7).
  - **101** (wave 09): the `inputs` job and its decision step, the `from-source` dispatch input,
    `max-parallel: 20` on every judge matrix, the build shard as a pseudo-system on Linux
    (`shards.PLATFORM["build"] = "linux"`, `gather.JOB["build"] = "build-shard"`). 102 adds a
    `tier` output to the same job and a fourth judge matrix in the same shape. 102 is built after
    wave 09 lands, or stacked on wave 09's reviewed tip (§4.14), the Status naming the base.
  - **100** (wave 09): numpy on OpenBLAS changes `numpy.linalg`, where 9 of numpy's selected
    `slow` lines sit (below). The survey (Decision 9) runs on a set with 100.
  - Landed: **050** and **051** (groups, `passes`, classes, traps), **063** (shards, the gather's G1
    to G7), **065** (families and budgets), **091** (fuel facts), **092** (the release record,
    sameness, claim lists), **052** (several cores), **062** (the history's format 2).
- **Meets, with an order rule each** (Decision 13): **067** (marks its release-tier groups; built
  after 102), **095** (scipy's, scikit-learn's and statsmodels' own tests apply Decision 2's rule).
- **The owner's decision it writes to** (2026-10-20, relayed by the lane; spec 067's revision
  quotes it, "The owner's choices", (c)): "I think we should have two concepts of tests. We do not
  need to run the slow tests unless we're are creating a new release that we publish to pypi.
  Otherwise, for normal checks, we don't run the slow tests." The lane's reading, which this
  specification adopts: upstream's opt-in slow tests form a **release tier**; it runs on the
  publishing (tag) run and on the dry run on main before a tag (AGENTS.md rule 6b); it is skipped
  on branch runs, wave dry runs and the lane's accepts. The decision is not yet in
  `context/decisions.md` on main (READ, `grep` on `5805af0`); the lane records it there and reserves
  102 in the roadmap.
- **Research it stands on:**
  - Spec 066 (READ on `origin/wave/08` at `72bc5ed`): contourpy's ten `--runslow` cases measured
    946.6 G in three split groups (`contourpy-filled-9` 376.1 G, `-10` 285.4 G, `-11` 285.1 G;
    EXECUTED there), in shards `upstream-plot-c`, `-g` and `-a`; the Linux rate 0.16 to 0.31 s per
    G past about 60 s of setup (dry run `39371419248`, READ there).
  - Spec 067's revision (READ at `0eb887d`): `tier = "release"` groups that run the complement of
    their normal partner's marker expression over the same paths; sympy's `slow` (185 lines) and
    `tooslow` (14 lines); `test_issue_17141_slow`, about 2,609 G alone (EXECUTED by 067's pre-build
    review); networkx's and narwhals' `--runslow`, packaging's `property` tests.
  - Spec 101 (READ on `origin/spec/101-faster-release-run` at `827f826`): a source run is 38 jobs
    wide at most (39 with `save-set`, which a tag does not run); GitHub's Pro plan allows 40
    concurrent jobs, 5 of them macOS (READ there); tags and dispatches on main never reuse a set.
  - `../research/2026-10-18-the-release-judges-in-parallel-shards.md` (READ, through spec 065):
    0.154 to 0.170 s per G of fuel on a quiet Mac.
  - **Read while drafting (2026-10-20), no guest run**, in the drafting agent's scratchpad
    (`readers/slow_lines.py`, stdlib only, run with `uv run --no-project python -I`; tarballs read
    as data with `tarfile`, nothing unpacked): the pinned `numpy-2.5.2.tar.gz`,
    `pandas-3.0.6.tar.gz` and `contourpy-1.4.0.tar.gz`, each first checked against
    `downloads/SHA256SUMS` with `shasum -a 256` (all three equal; EXECUTED). The counts are in
    Decision 8.
  - The release workflow's run list (`gh run list --workflow release.yml --limit 200`, read-only;
    EXECUTED): since the wave pipeline began, every dispatch on `main` has been a pre-tag dry run.
    The last one, `39252500950` (2026-10-19 12:29), preceded `v0.1.0a7`'s tag run `39255794160`;
    wave dry runs run on `wave/NN` (`39442080658` on `wave/07`).

## The problem

The owner's rule is "every test of every package we build" (`decisions.md`, 2026-10-20). Spec
066 runs contourpy's `--runslow` cases at every judge run. Spec 067 would add sympy's slow tests,
one of them about 2.6 T of fuel alone, and the slow tests of three more packages. numpy's and
pandas' slow tests do not run at all: their TOMLs select `not slow` (spec 050).

So two things are wrong at once:

1. **Tests the owner wants are not run.** numpy's 33 and pandas' 27 `slow` lines in the selected
   files (EXECUTED, Decision 8) are left out by marker, with no reason recorded beside them.
2. **The tests that are run cost every check.** Every branch run, every wave dry run and every lane
   acceptance pays for contourpy's 946.6 G of slow cases today, and would pay for sympy's after
   067. The owner's answer: those belong to a publication, not to a check.

And the judge has no notion of a test that runs only sometimes. Today a check that does not run
looks lost or unrun:
- the ratchet puts an accepted upstream check that did not run into `upstream_unrun`, and
  `--accept` refuses it without `--partial` (`scoreboard.accept`, READ);
- the gather is red on any collected check that ran in no record (G3) and on any accepted pass or
  gap that ran in no record (G5) (`gather.py`, READ).

## Principle

**Each test is in exactly one tier, by construction.** A release-tier group runs exactly the tests
its normal partner leaves out by upstream's slow markers, over the same paths, and nothing else.

**A row the tier did not run is not run, never lost.** It keeps what was accepted, it is counted
by name, and it never needs `--partial`.

**Only the lane accepts, on darwin, as today.** Release-tier rows are accepted by the lane's own
run with the release tier, never from a CI record.

**A publication runs everything.** A tag cannot publish unless its own run judged the release
tier, and the newest acceptance judged it too.

## Decisions

### 1. Two tiers, and what each run runs

- **The normal tier** is every check of the judge but the release-tier groups' checks (their
  suite check, their class checks, their trap checks).
- **A release run** runs both tiers: every check.
- **Where each runs:**

  | run | tier |
  |---|---|
  | a pushed tag `v*` (the publishing run) | release, always |
  | a dispatch on `main` (AGENTS.md rule 6b's dry run before a tag) | release, always |
  | a dispatch on any other branch (`spec/*`, `wave/*`) | normal; release when the dispatch input `release-tier` is true |
  | the lane's acceptance in the main tree | normal; release at the release acceptance and at a landing that changes a release-tier row (Decision 5) |
  | a builder's or reviewer's local run | normal; release with `--tier release` |

- **Why `main` is always release, with no input to turn it off.** Rule 6b's dry run rehearses the
  tag, and must be what the tag run will be. Since the wave pipeline began, every dispatch on main
  has been a pre-tag dry run (EXECUTED, the run list above); landings dry-run on `wave/NN`. A
  dry run on main that skipped the tier could pass while the tag failed, the failure rule 6b
  exists to prevent (0.1.0a4's tag run failed on Windows, AGENTS.md).
- **Why a branch may ask for it.** A specification that adds or changes release-tier groups (this
  one, 067, 095) must show them on CI before it is reviewed. `release-tier: true` on a branch
  dispatch runs them. Nothing else changes on that run: a branch run still reuses a set under
  101's rules.

### 2. Which tests are release-tier: upstream's opt-in slow tests, by marker only

**The rule.** A test is release-tier when upstream's own default test run leaves it out *because it
is slow*, by a marker its own configuration deselects or skips unless asked (`-m "not slow"` in
`addopts`, a `--runslow` option, sympy's `slow` and `tooslow`), and the product can run it. A test
left out for a true reason (no network, no database server, no processes) is not release-tier: it
stays excluded, with its reason, as today.

**Membership is by marker, never by name.** A family that has release-tier groups declares, in its
TOML:
- `release_marker`: the `-m` expression its release-tier groups run;
- `excluded_marker` (optional), with `excluded_reason` and `excluded_closes_with`: what no tier
  runs, and why. pandas' is `"network or db"`, "no network and no database server in the guest",
  `README.md`.

Its normal groups keep the family's `marker`. **The rules check proves the partition** with
pytest's own expression parser on the host (`_pytest.mark.expression.Expression`, as 066's
`_keyword_errors` uses it): over every assignment of true and false to the identifiers the three
expressions name, `marker and release_marker` is never true, and `marker or release_marker` is
exactly `not excluded_marker` (or always true when there is none). A truth table over two to four
names: exact, not textual.

| family | `marker` (normal, unchanged unless named) | `release_marker` | `excluded_marker` |
|---|---|---|---|
| numpy | `not slow` | `slow` | none |
| pandas | `not slow and not network and not db` | `slow and not network and not db` | `network or db` |
| contourpy | **`not slow`** (new; was none) | `slow` | none |

So nobody can move a failing test into the release tier to turn a normal run green: a test is
there only if upstream marked it slow. Moving one is a judge change to a TOML, seen in the diff and
the judge hash.

### 3. The groups: a release-tier group runs its tier's share of its partners' paths

- A group carries `tier = "release"` (default `"normal"`).
- **Paths.** Within a family, the release-tier groups' paths, taken together, are exactly the
  normal groups' paths taken together, and no path is in two release-tier groups, except a file
  split by `[[split]]` (below). So every test under a normal group's paths that matches
  `release_marker` is in exactly one release-tier group.
- **The argv.** A release-tier group runs `-m <release_marker>` in place of `-m <marker>`; every
  other argument is built as for any group of its family: its paths, the family's `not_selected`
  files as `--ignore`, its traps as `--deselect`, the family's `args`. A normal group's argv, and
  so its JSON, is byte for byte what it is today (criterion 4), except contourpy's (Decision 7).
- **`[[split]]` per tier.** A split's groups are all of one tier, and a file may carry one split
  per tier. The constructed `-k` expressions (066, Decision 11) are built within that tier's
  split alone. A test of the file is in exactly one tier by marker, then in exactly one group of
  that tier by the construction. Each split's groups record the file's `collected` count, compared
  within the split as 066 does.
- **A release-tier group that selects nothing fails** (pytest's exit 5 is a finding, as for 066's
  split groups). The survey shapes the groups so each selects at least one test.
- **Caps by 066's rule, in every family.** A release-tier group carries `measured`, and its cap is
  at most `rule_cap(measured)` (1.5 times, rounded up to two significant figures), in numpy's and
  pandas' TOMLs too, where normal groups keep their caps as they are. The 480 G bound applies (066,
  Decision 11): a release-tier group past it is split by path, or by a `[[split]]` of one file.
- **Traps and fuel facts.** A `[[trap]]` or `[[fuel_fact]]` in a family with release-tier groups
  names its `group`; the trap check takes that group's tier. None is expected (Decision 9 measures).
- **067's node-id groups.** 067's `sympy-slow-17141` (one test by node id, past every bound) is a
  release-tier group that names `nodes`; the group whose paths contain it deselects it. That form
  is 067's to add, under this Decision's partition rule.

### 4. The stage never depends on the tier

Each family's stage (`/upstream`, `/cpython`, `/upstream-<package>`) holds every group's JSON,
both tiers', on every run. The tier decides which checks run, never what is staged.

Why: the stage's content moves fuel (063, Decision 5: numpy-lib moved by 3.9e-5 when only numpy's
tree was staged; READ there). A stage that differed by tier would give a normal row one fuel on a
normal run and another on a release run, and the darwin fuel accepted on one would not hold on the
other. Adding the new JSON files to `/upstream` is a one-time change, measured by criterion 4.

### 5. How release-tier rows live in the ratchet, and who accepts them

**The record.** Every run record carries `meta.tier` (`"normal"` or `"release"`). In a run that is
not a shard run, the normal tier deselects every release-tier check, with the reason `release
tier`, and lists them in a new top-level field, `tier_deselected`. A shard run's tier is its
shard's (Decision 6); `--tier` with `--shard` is an argument error, one line.

**The ratchet** (`scoreboard.compare`):
- an accepted check in `tier_deselected` goes to a new list, `release_tier`, and nowhere else: not
  `deselected`, not `upstream_unrun`, not `absent`; it is never red and never asks for `--partial`;
- the ratchet line prints `release tier not run <n>` when the list is not empty;
- everything else is unchanged. On a release run the release-tier rows are ratcheted like any
  other: a lost pass, a fall in `passes`, or fuel past the tolerance is red.

**The acceptance** (`scoreboard.accept`): a check not run here keeps what was accepted (the code
already does this for every status but pass, fail and gap; READ). So a normal acceptance never
changes a release-tier row. The history line gains `tier` (`"normal"` or `"release"`); a line from
before this spec has none and reads as normal. `test_progress_history_is_intact` accepts the field.

**Who records release-tier rows: the lane, on darwin, in its own run with `--tier release`.**
Never from a CI record. Why not from CI: G5 holds only darwin fuel, `accepted.json` keeps darwin's
metrics alone, and Linux fuel moves between runs of one judge on one artifact (spec 092, "Found on
the way": `cpython-b` 3.5% apart over three runs; EXECUTED there). A release-tier row accepted
from Linux would have no fuel ratchet at all. The lane runs `--tier release` at exactly two kinds
of acceptance:

1. **The release acceptance, before every tag.** On main's tip, after the last wave and before the
   dry run on main: `uv run pytest -n 3 --tier release --accept "Release <version>: the release
   tier"`. It judges every release-tier row on the set the tag will publish.
2. **A landing whose entry changes a release-tier row** (its claim list names one: added, changed,
   moved between tiers, its passes or its fuel). Its rows are then accepted when they land, so the
   lane reproduces every number a specification brings (§5.4), and a release is never the first
   darwin judgement of a new row. Rare: this specification, 067, 095. The wave's dry run is then
   dispatched with `release-tier: true` (the dry run runs the tier the acceptance ran).

**What the release acceptance may find**, since release-tier rows are not judged between releases:
a lost pass, a fall in `passes`, fuel growth, or a class whose members now pass. Each is red, and
the tag waits. Growth is accepted only with a reason that names the waves since the last release
acceptance whose claim lists grew guest fuel; a lost pass or a fall is fixed forward by a
specification before the tag. This is the price of the owner's choice, stated here so the lane
plans for it.

### 6. Where the release tier runs: a fourth judge matrix, Linux only

- **Shards.** Release-tier groups go in shards of a pseudo-system, `release`, as the build shard
  is the pseudo-system `build`: `shards.PLATFORM["release"] = "linux"`, `gather.JOB["release"] =
  "judge-release"`, and sameness's `SYSTEMS` maps `release` to `linux`. The plan's rules: each
  release-tier group is in exactly one shard of system `release`; such a shard holds only
  release-tier groups; a normal group is in no release shard (063's "every upstream group is in
  exactly one Linux shard" becomes "every normal group…"); `rest` never takes a release-tier check,
  since the release shards take them by group.
- **Packing.** 066's rule: at most 725 G a shard (about 290 s of job time at the dry run's slowest
  rate), from measured fuel; a single group past it gets a shard of its own (067's sympy group, the
  owner's answer (b) to 067's Q1: allowed past the 360 s bound). The builder packs from the survey.
- **Linux only.** As 066's Decision 12: macOS and Windows run no release-tier group in CI; the
  lane's darwin run is the darwin record. A host difference is a host entry (065, Decision 21).
- **The job.** `judge-release`, `runs-on: ubuntu-24.04`, `needs: [inputs, build]`, `if:
  needs.inputs.outputs.tier == 'release'`, its matrix exactly the plan's release shards, `max-parallel:
  20` (the one text spec 063's rule 3 and 101's Decision 9 require), its steps text-alike with
  `judge-linux`'s (the same download, check, unpack, fetch, shard, hash, upload and output steps),
  handing on `<shard>-id` and `<shard>-sha256`. Every value through `env:` (spec 057, rule 11).

### 7. contourpy's slow cases move: three groups, one marker

- `contourpy.toml` gains `marker = "not slow"` and `release_marker = "slow"`. Its `args` keep
  `--runslow` (so contourpy's conftest does not skip a slow case before `-m` sees it) and
  `--runtext`: text cases are not slow and stay normal.
- `contourpy-filled-9`, `-10` and `-11`, which hold exactly the ten `test_filled_compare_slow`
  cases (EXECUTED: `@pytest.mark.slow` appears once in contourpy 1.4.0's `tests/`, on that
  function, parametrized over ten seeds), become `tier = "release"`.
- `test_filled.py`'s split becomes two (Decision 3): the normal split, groups 1 to 8 and 12, with
  066's expressions e₁ to e₈, so group 12 runs `-k "not (e₁ or … or e₈)"` under `-m "not slow"`
  (the same tests as today's `not (e₁ or … or e₁₁)`); the release split, groups 9, 10 and 11, with
  066's e₉ and e₁₀, group 11 taking the rest under `-m slow`.
- **What moves in fuel.** Every contourpy normal group gains `-m "not slow"` in its argv, and group
  12 a shorter `-k`. Their selections do not change; their fuel may move by the cost of the marker
  on each item. The survey re-measures all of contourpy's groups; a move past 1e-4 is claimed as
  growth with that reason, and each `measured` and cap follows the new number.
- **The shards.** The three groups leave `upstream-plot-c`, `-g` and `-a` and go to release shards
  (946.6 G: two shards at 725 G each, with numpy's and pandas' groups packed beside them). The
  normal shards are not re-packed; three become lighter.

### 8. numpy's and pandas' slow tests join, by a measured survey

- **What is there** (EXECUTED, `readers/slow_lines.py` over the pinned sdists, lines matching
  `mark.slow` or a module-level `pytestmark`; a line can stand for several parametrized cases):

  | group's paths | `slow` lines in selected files | files |
  |---|---|---|
  | numpy-core (`numpy/_core/tests`) | 6 | 5 (`test_array_interface`, `test_mem_policy`, `test_multiprocessing`, `test_shape_base`, `test_strings`) |
  | numpy-lib (`numpy/lib/tests`) | 10 | 5 (`test_format`, `test_function_base`, `test_histograms`, `test_io`, `test_nanfunctions`) |
  | numpy-others | 17 | 8 (`linalg/test_linalg` 8, `linalg/test_regression`, `random/` three files, `testing/test_utils`, `tests/test_public_api`, `tests/test_warnings`) |
  | pandas' eight groups | 27 | 15 (`frame/methods/test_to_csv` 9, `io/parser` six files, `groupby` three files, `frame` three more, `reshape/test_pivot`, `tslibs/test_ccalendar`) |

  numpy has 21 more `slow` lines in files `not_selected` for their own reasons (the C test modules,
  `mmap`); they stay out. No `slow` line is module-level in either package.
- **Two families' release-tier groups.** numpy: `numpy-slow` over the three normal groups' paths,
  split by path if the survey measures it past 480 G. pandas: `pandas-slow` over the eight groups'
  paths, likewise. Each carries `measured` and its cap by the rule.
- **What they will find, INFERRED.** numpy's slow tests are mostly large-memory and long-loop tests
  (`test_format`'s large files, `linalg`'s big matrices, `test_multiprocessing`, `test_extending`'s
  build); pandas' include `test_multi_thread`. Expected classes: `no-processes`, `no-threads`,
  `wasm32-memory`, and skips where numpy's `requires_memory` cannot read the host's memory.
  Unknown to within an order: 0.1 to 2 T of fuel for both, until measured.

### 9. The survey comes first, as research

As 066's Decision 1, smaller:
- **A research step, time-boxed at 60 minutes**, before any TOML, list or harness line is
  committed, on main's frozen set after wave 09 (100 in it), with the judge's own embedder, a
  private copy of the set, one session per group, at most three at once, never while
  `build/lane.lock` exists. It measures numpy's and pandas' candidate release-tier groups (outcomes
  by node id, fuel, traps, collection errors, failures sorted into the platform's classes) and
  re-measures every contourpy group under Decision 7's argv.
- **Written up** as `context/research/2026-10-2x-the-release-tier-survey.md`, labelled EXECUTED,
  with the stand-in and the raw streams.
- **Its delta goes to the build review**, not a separate round, unless it finds a trap, a group
  past 480 G that a path split cannot bring under, or a class whose closer is not `README.md` or a
  landed specification: then a context-only delta review first, as 066's.

### 10. How a run knows its tier: the `inputs` job decides once

101's `inputs` job gains one step and one output, `tier`. The step is one script, its values
through `env:`:

```
tier=normal
if [ "$GITHUB_EVENT_NAME" = push ] && [ "$GITHUB_REF_TYPE" = tag ]; then tier=release; fi
if [ "$GITHUB_REF" = refs/heads/main ]; then tier=release; fi
if [ "$GITHUB_EVENT_NAME" = workflow_dispatch ] && [ "$RELEASE_TIER" = true ]; then tier=release; fi
echo "tier=$tier" >> "$GITHUB_OUTPUT"
```

- `on.workflow_dispatch.inputs` gains `release-tier` (boolean, default false), beside `from-source`.
- Every consumer compares with `== 'release'` exactly.
- **The gather derives it again** and does not trust the output alone: from `GITHUB_EVENT_NAME`,
  `GITHUB_REF_TYPE` and `GITHUB_REF` (which a step cannot override), a tag or a dispatch on main is
  a **release run**, and its tier must be `release`. The gather reads the job's output as `TIER`;
  a release run whose `TIER` is not `release` is red at G1 ("G1 a tag (or a dispatch on main), and
  the release tier did not run"), as 101's G7 reads `set-source`.

### 11. The gather, by tier

- **G1.** `expected_keys` includes the `release` shards only when `TIER` is `release`. A release
  record handed on in a normal run is "a file no job handed on", as today.
- **G3.** On a normal run, a release-tier check is expected to run in no record, and every record
  must deselect it; one that ran anywhere is red ("G3 <node>: a release-tier check ran in a normal
  run"). On a release run, G3 is today's: every collected check runs in exactly its shard.
- **G5.** On a normal run, "accepted pass, ran in no record" skips release-tier checks. On a release
  run it holds them, and `passes` and `passed_digest` are compared with the darwin acceptance as for
  any upstream group.
- **G7.** On a release run, the newest acceptance's `tier` is `release`: "G7 a tag (or a dispatch on
  main), and the newest acceptance did not run the release tier". With today's rules it must also
  be on the release's `python.wasm` and set, clean and not partial.
- **The merged record** carries `meta.tier`. A release-tier check of a normal run has no `source`
  and status `deselected`, which sameness already treats as not compared (092, Decision 2).
- **The workflow.** `gather` needs `judge-release` too, with `if: ${{ !cancelled() && !failure()
  }}`. INFERRED from GitHub's documented `needs` semantics: a skipped need skips its dependents
  unless a status function says otherwise; `!failure()` lets the gather run when `judge-release`
  was skipped and still skips it when any need failed, as today. Criterion 7 proves both on the
  branch.

### 12. What the release fails on

A tag publishes nothing unless all of these hold. Each one alone stops it.

- **A release-tier record is red**: a failure, an unknown class member, a trap, a lost pass, a fall
  in `passes`, or `passes` unequal to the darwin acceptance (G4, G5).
- **A release-tier leg failed or was cancelled**: the gather is skipped, so `attest` and `publish`,
  which need the gather, are skipped.
- **The release tier did not run** on a tag or a dispatch on main (G1), or **the newest acceptance
  did not run it** (G7).
- **Rule 6b**: no tag without a dry run on main's exact commit that passed every job, the
  release-tier legs included.

Nothing in `attest` or `publish` changes: they already need the gather.

### 13. The order with 066, 067, 095 and 101

- **066** has landed (wave 08). 102 edits its contourpy TOML and its shard plan.
- **101** lands in wave 09. 102 is built on main after it, or stacked on wave 09's reviewed tip;
  textual conflicts with 101 are in the `inputs` job, the matrices, the gather's `needs` and `env:`,
  and `scan.py`'s rules.
- **067** is built after 102 lands (067's Decision 10, "the order with 102", takes this branch).
  Its release-tier groups then carry `tier = "release"` and its families `release_marker`; its
  node-id group (Decision 3) and its marker `D` lines are 067's. 067's "complement of its partner"
  rule is this specification's truth table, so 067 adds no second rule. If 067 is ready first, the
  lane holds it (067's own alternative, release-tier groups refused until 102, is not needed).
- **095** applies Decision 2's rule to scipy, scikit-learn and statsmodels (scipy's `slow` and
  `xslow`, statsmodels' slow options: 095's survey reads them), and packs its release-tier groups
  into release shards.
- **0.1.0** waits for 067 (the owner, main `5805af0`), and 067 waits for 102, so 0.1.0's tag is the
  first publishing run with a release tier.

### 14. What stays the same

- The fast tier (`-m "not slow"`, the judge's own `slow` marker on its guest checks) is not the
  release tier and is unchanged; a release-tier check is deselected by both.
- No check is retired and no node id changes: the moved contourpy rows keep their ids.
- The plain `uv run pytest` still runs serially, the normal tier.

## Intent

Upstream's slow tests run before every publication, on Linux in CI and on darwin in the lane's
release acceptance, and nowhere else. A branch, a wave or a landing pays nothing for them. A row
they did not run is shown as not run, never lost. A tag publishes only what its own run judged,
both tiers.

## Design

| file | change |
|---|---|
| `tests/harness/upstream.py` | `Group.tier`, `Group.measured` for every family; `Config.release_marker`, `excluded_marker` and its reason and closer; `group_spec` takes `release_marker` for a release-tier group; `tier_of(check)`; the partition rules in `rule_errors` (truth table, paths, splits per tier, `measured` and caps on release-tier groups, traps and facts naming a group) |
| `tests/harness/packages.py` | the same for package families; `[[split]]` per tier; contourpy's argv |
| `tests/harness/plugin.py` | `--tier normal|release` (default normal); the normal tier deselects release-tier checks, reason `release tier`, into `tier_deselected`; `meta.tier`; `--tier` with `--shard` an argument error; a shard's tier from the plan |
| `tests/harness/scoreboard.py` | `Ratchet.release_tier`; `compare` routes `tier_deselected`; the ratchet line; `accept` writes `tier` into the history line |
| `tests/harness/history.py` | the line's optional `tier` field, accepted by the intact check |
| `tests/harness/shards.py` | the `release` pseudo-system; `PLATFORM["release"] = "linux"`; the plan rules of Decision 6 |
| `tests/harness/gather.py` | `TIER` and the release run from `GITHUB_*`; `JOB["release"]`; G1, G3, G5 and G7 by tier; `meta.tier` |
| `tests/harness/sameness.py` | `SYSTEMS["release"]`; release-tier rows compared only when both records ran the tier, else counted on stderr (`release tier, not run in the first record: <n>`); a `meta.tier` difference is a note |
| `tests/harness/scan.py` | the `release-tier` input; the `inputs` job's tier step and output; `judge-release`'s shape and its text-alike rule with `judge-linux`; its matrix against the plan; the gather's `needs`, `if:` and `env:` |
| `.github/workflows/release.yml` | the input, the step, `judge-release`, the gather's `needs`, `if:` and `RECORD_RELEASE_*` and `TIER` |
| `tests/release_shards.toml` | contourpy's three groups out of `upstream-plot-a`, `-c`, `-g`; the release shards, `systems = ["release"]` |
| `tests/upstream/numpy.toml`, `pandas.toml`, `contourpy.toml` | `release_marker`, `excluded_marker`; the release-tier groups with `measured` and caps; contourpy's `marker` and its two splits |
| `tests/upstream/expected/<group>/<class>.txt`, `tests/known_gaps.toml` | the release-tier groups' classes, from the survey |
| `tests/unit/` | the rows of *The checks* |
| `context/progress/README.md` | "The release tier (spec 102)": the tiers, the ratchet's line, the two release acceptances, the dry run's tier |
| `README.md` | the testing paragraph: which tests run before a publication only, and why |
| `CHANGELOG.md` | one line under the unreleased section |

**A release run, in order.** `inputs` hands on `tier=release`. The build (or, on a branch, a reused
set) and the judges as today; `judge-release` runs each release shard against `accepted.json`,
hashes its record and hands on its id and SHA-256. The gather needs all of them, checks the tier
against `GITHUB_*`, and holds G1 to G7 over every record. On a tag, `attest` and `publish` follow.

## Scope

**In:** Decisions 1 to 14: the mechanism, numpy's and pandas' slow tests, contourpy's move.

**Out, each with its reason:**
- **067's and 095's release-tier groups.** Theirs, under Decision 2's rule (Decision 13).
- **contourpy's `random_big` cases** (about 2.83 T, `decisions.md`, 2026-10-20). They are not
  upstream-slow by Decision 2's rule: contourpy's default run includes them; only its emulated CI
  legs leave them out with `-k "not big"`. The owner kept them in every run; they stay normal
  (owner question 2).
- **CPython's `-u cpu` and `largefile` resources** (spec 065, Decision 15: `resources =
  "all,-cpu,-gui,-largefile"`, READ). Opt-in by regrtest's own rules, so release-tier candidates by
  Decision 2's spirit; regrtest groups are not pytest groups, and 065 chose its resources for its
  own reasons. Not here (owner question 3).
- **Accepting from a CI record.** Decision 5 says why not.
- **macOS and Windows release shards.** Decision 6.
- **The constitution's and AGENTS.md's wording.** The lane's and the owner's (For the lane; owner
  question 1).
- **Wall-clock.** No check reads a clock (§4.9). Every time here is a benchmark estimate.

## The checks

Each is written before the change it judges and seen failing first on the base's tree; the
landing notes record each failure.

1. **The partition rules** (`test_upstream_files_are_well_formed`, widened; unit variants in
   `tests/unit/test_upstream.py` and `test_packages.py`, each failing with its own line): a
   `release_marker` that overlaps `marker` (numpy with `release_marker = "slow or leaks_references"`:
   a test marked `leaks_references` and not `slow` would be in both tiers); a union that is not `not
   excluded_marker` (pandas without `excluded_marker`); an expression pytest cannot parse; a
   release-tier group whose paths are not part of the normal groups' union; a path in two
   release-tier groups; a split mixing tiers; two splits of one file in one tier; a release-tier
   group without `measured`, or with a cap above `rule_cap(measured)`; a trap without `group` in a
   family with release-tier groups; `tier = "fast"`. Fails on the base: no such keys.
2. **The argv** (unit): numpy's three normal groups' JSON is byte-identical to the base's (a hash
   of each); `numpy-slow`'s argv has `-m slow` and every `--ignore` its paths take; contourpy's
   group 12 has `-m "not slow"` and `-k "not (e₁ or … or e₈)"`; group 11 has `-m slow` and `-k "not
   (e₉ or e₁₀)"`.
3. **The stage** (unit): the `/upstream` and `/upstream-contourpy` stage manifests are equal under
   `--tier normal` and `--tier release` (Decision 4).
4. **The ratchet** (unit, `tests/unit/test_scoreboard.py` or its file): a normal-tier run whose
   accepted release-tier rows did not run is not red, puts them in `release_tier` and nowhere else,
   and `--accept` succeeds without `--partial`, keeping their entries byte for byte and writing
   `tier: "normal"`; the same rows on a release-tier run that fails one is `lost`; a release-tier
   row deselected by `-m` in a run that did not name a tier still counts as `release_tier`; a
   history line with and without `tier` is intact.
5. **The plugin** (unit): `--tier release` with `--shard upstream-plot-a` is an argument error, one
   line, before anything runs; a
   normal run's record has `meta.tier = "normal"` and lists every release-tier check in
   `tier_deselected`; a release-shard run's record has `meta.tier = "release"`.
6. **The shard plan** (unit, `tests/unit/test_shards.py`): a release-tier group in a Linux shard,
   a normal group in a release shard, a release-tier group in two release shards, and a release
   shard on `linux` each fail `plan_errors`; `rest` never selects a release-tier check.
7. **The gather** (unit, `tests/unit/test_gather.py`): on a normal run, no release record is
   expected, a release-tier check that ran in no record is not red, and one that ran is red at G3;
   on a release run, a missing release record is red at G1; a tag whose `TIER` is `normal` is red
   at G1; a tag, or a dispatch on main, whose newest acceptance has no `tier: "release"` is red at
   G7; a branch dispatch with `release-tier` and a normal newest acceptance is not; the merged
   record carries `meta.tier`.
8. **The workflow** (rules, `scan.py`): `judge-release`'s matrix is the plan's release shards; its
   `if:` is exactly `needs.inputs.outputs.tier == 'release'`; its steps are `judge-linux`'s, text
   for text, but the job's name and system; the gather needs it, with exactly `if: ${{
   !cancelled() && !failure() }}`, and hands it every `RECORD_RELEASE_<SHARD>` and `TIER`. Mutants,
   each seen red: the `if:` dropped from `judge-release`; a release shard missing from its matrix;
   `always()` in the gather's `if:`.
9. **The tier step** (rules, run in bash over every case): a pushed tag, a dispatch on main, and a
   branch dispatch with `release-tier` true give `release`; a branch dispatch without it, with an
   empty value and with `True` give `normal`.
10. **Sameness** (unit, `tests/unit/test_sameness.py`): a release record of a release run against
    a local normal record prints no difference for release-tier rows and counts them on stderr; two
    release-tier records compare them as any rows.

## Acceptance criteria

Counted, never timed.

1. **The checks** of *The checks* exist and were each seen failing first; the landing notes give
   each failure.
2. **The survey** (Decision 9) exists, EXECUTED, before any TOML, list or harness line, with each
   release-tier group's outcomes by id, fuel, traps and classes and each contourpy group's
   re-measurement; its delta is in the build review (or a delta review, by Decision 9's rule).
3. **The baseline.** With the TOMLs, lists and gaps complete, a local run of every release-tier
   group by node id with `--tier release` passes each group check, and each class check fails as
   its gap says; each new group run twice, restaging between the runs (066, criterion 5): equal
   outcomes and `passed_digest`, darwin fuel within the ratchet's tolerance.
4. **Nothing normal moves but what is named.** The fast tier, and single node ids for numpy's and
   pandas' normal groups: their fuel equal to the base's within 1e-4 (the stage gained files,
   Decision 4), or the growth named with that reason; contourpy's normal groups re-measured, each
   `measured` and cap updated, each move claimed with Decision 7's reason. No pass lost, no
   `passes` fallen.
5. **A normal branch run.** The builder's first dispatch, default inputs: `inputs` hands on
   `tier=normal`; `judge-release` is skipped; the gather runs and passes with `meta.tier`
   `normal`; contourpy's three groups appear in no record; every red line a growth line or G7.
6. **A release branch run.** A second dispatch with `release-tier: true`: every release shard's leg
   runs and passes, each within 360 s of job time (or Decision 6's single-group exception, none
   expected here); the gather passes with `meta.tier` `release`; G5 compares the release-tier
   groups' `passes` with whatever the acceptance holds. The landing notes record each release
   leg's job time, the run's peak of concurrent jobs, and its wall time beside run 5's.
7. **The gather's conditions.** Run 5 shows the gather running beside a skipped `judge-release`.
   The other path, a failed leg skipping the gather, is GitHub's documented meaning of `failure()`
   and today's behaviour without the `if:` (spec 092's run `39357023086`: one red leg, the gather
   skipped; READ there); no scratch run is made for it (no branch beyond §4.14's), and the first
   red release leg on any later run is its evidence. The landing notes give run 5's id and the
   gather's and `judge-release`'s conclusions.
8. **The judge.** `ruff check`, `ruff format --check`, the fast tier green in the worktree. The
   lane's acceptance at the landing runs `--tier release` (Decision 5, kind 2) and the wave's dry
   run `release-tier: true`.

## The owner's choices

1. **The constitution's wording.** §5.7 says the lane "runs the full judge on that exact commit".
   Under this specification the lane's landing runs the normal tier, and the release tier only at
   the release acceptance and at a landing that changes a release-tier row. Proposed amendment, for
   the owner to make or refuse: "runs the full judge (its normal tier, and its release tier when the
   landing changes a release-tier row; spec 102) on that exact commit"; and in §5.5, "a release
   runs every tier of the judge before it is tagged". Default if unanswered: 102 may be built and
   reviewed, and lands only with the owner's answer, since §5.7 changes only by the owner's
   explicit decision.
2. **contourpy's `random_big` cases** (about 2.83 T of 066's fuel): normal tier by Decision 2's
   rule (default), or release tier as upstream's own slow-host selection. Moving them would cut
   the normal tier's upstream fuel by about a quarter and the lane's acceptance with it.
3. **CPython's `-u cpu` and `largefile` resources.** Out of 102 (default). If the owner wants them,
   a follow-up specification brings regrtest groups into the release tier.
4. **The lane runs the release tier at a landing that changes a release-tier row** (Decision 5,
   kind 2). Default: yes, so every number is reproduced at its landing. The stricter reading (only
   before a tag) leaves new release-tier rows unjudged on darwin until the release acceptance.

## For the lane

- **Wave kind: build-class** (the release workflow and the shard plan; no artifact byte changes).
  It may ride as one of a wave's two other build-class changes. **Dry-run needs:** the branch runs
  of criteria 5 to 7; the wave's dry run with `release-tier: true`.
- **AGENTS.md** (the lane's to write; an agent does not edit the project's instructions). Proposed
  lines:
  - rule 3a: "The full judge is its normal tier. The release tier (spec 102) runs on a tag, on the
    dry run on main, at the lane's release acceptance, and at a landing that changes a release-tier
    row; a builder adds it to a branch run with the `release-tier` input when its specification
    changes one."
  - rule 6b: "Before a release tag, the lane makes the release acceptance (`uv run pytest -n 3
    --tier release --accept "Release <version>: the release tier"`) on main's tip, then dispatches
    the release workflow on main's exact commit, which runs the release tier itself."
- **`decisions.md`**: the owner's words of 2026-10-20 and the lane's reading, and 102 in the
  roadmap's `Reserved:` paragraph.
- **The claim list** (skeleton; the builder fills it from the survey): **new**, the release-tier
  groups' suite and class checks (deselected in a normal record, run in the lane's release-tier
  acceptance); **changed**, `test_upstream_suite[contourpy-filled-9]`, `-10`, `-11` (normal to
  release tier); **grows**, contourpy's normal groups if Decision 7's argv moves them, and numpy's
  and pandas' normal groups if Decision 4's stage does, each with its reason; **retired**, none;
  **units**, the rows of *The checks*.
- **The flags** (skeleton; each reason begins with "102:"):

  ```
  --tier release
  --accept "102: the release tier: upstream's slow tests run before a publication; numpy-slow, pandas-slow and contourpy's ten slow cases in <r> release-tier groups, <p> passes, <c> classes"
  --accept-judge "102: release tier key, release_marker and excluded_marker with the truth-table partition, splits per tier, measured and caps on release-tier groups (upstream.py, packages.py); --tier, tier_deselected and meta.tier (plugin.py); the ratchet's release_tier and the history line's tier (scoreboard.py, history.py); the release pseudo-system (shards.py); G1, G3, G5 and G7 by tier (gather.py); sameness by tier; judge-release, the release-tier input and the tier step (release.yml, scan.py); numpy.toml, pandas.toml, contourpy.toml; release_shards.toml; unit rows"
  ```

## The builder's self-check

Filled in at the build (*Landing notes*), from `context/reviews/README.md`'s list, with these
items added: both branch runs' ids (criteria 5 and 6) and the scratch run's (criterion 7); the
survey's memo and its delta's verdict; the stage manifests' equality (check 3); every release
leg's job time.

## Risks a pre-build reviewer should probe

- **The gather's `if:`.** GitHub's skip propagation through `needs` with a status function (`!cancelled()
  && !failure()`): does a skipped `judge-release` let the gather run, and does a failed one still
  skip it and so `attest`? Criterion 7 runs the first path only; the second rests on GitHub's
  documentation and today's behaviour.
- **The stage and normal fuel.** Decision 4 keeps the stage tier-independent, but adds files to
  `/upstream`. 063 found the stage moves fuel; how much a few JSON files move numpy's and pandas'
  normal rows is unmeasured.
- **Release-time surprises.** Decision 5 accepts that release-tier rows are judged only before a
  tag and at their own landings. A wave that changes numpy shows its slow tests' cost only at the
  release acceptance, as growth to attribute, or as a lost pass that blocks the tag.
- **The truth table.** pytest's marker expressions also accept keyword arguments in newer
  releases (`name(key=value)`); the rule must refuse a form it cannot evaluate, not pass it.
- **contourpy's argv change.** Adding `-m "not slow"` to every normal contourpy group moves fuel
  slightly; the split's `collected` fact may count before or after `-m` deselection, which decides
  whether the two splits of `test_filled.py` agree.
- **Width on a tag.** 101 counts 38 jobs on a source run; the release legs add up to 20 more with
  `max-parallel: 20`. Before 067 that is two or three legs; after 067 many more, which GitHub queues
  behind the Linux legs. INFERRED: a few minutes before 067; perhaps 5 to 20 minutes after, with
  sympy's single leg (420 to 810 s, 067's estimate) near macOS's critical path.
- **Main always release.** A dispatch on main for any other purpose pays the release tier and goes
  red at G7 without a release acceptance. The lane's practice since the waves makes that rare
  (EXECUTED: the run list), but it is a new rule for the lane.

## One line

Upstream's slow tests become a release tier: each test is in exactly one tier by its own markers,
a tier that did not run reads as not run, and a tag runs and needs both.

## Landing notes

The build, below, as it goes.
