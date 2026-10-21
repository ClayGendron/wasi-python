# 102 — the release tier: slow tests run before a publication, never left out

- **Status:** **drafted 2026-10-20** from main `5805af0` (tip `2bee892`); **revised 2026-10-20,
  night, against the owner's answers to its four questions** (`decisions.md`, "Spec 102's four
  questions", main `4161ef9`) and **rebased onto main `4161ef9`** (wave 08 landed: 066 is on main).
  **Revised 2026-10-20, late night, against its pre-build review**
  (`../reviews/102-the-release-tier-spec-2026-10-20.md`: three Mediums, seven Lows, three Notes,
  each answered in its Disposition) and **rebased onto `dbecd2d`** (`claude/gallant-ride-9nxxmn`:
  main plus the structural chain 103 to 109; no conflict, the branch touched only this file and
  its review). For the reviewer's confirmation of the Mediums, then the build. It changes the
  release workflow (a new judge job, a dispatch input, the gather's conditions), so constitution §5.6 and AGENTS.md rule 8 require that review before it is
  built. It changes neither the guest's imports nor its exports, nor a byte of the artifact set: no
  line of `src/`, `scripts/`, `recipes/` or `downloads/SHA256SUMS` changes. It amends the
  constitution at its landing (the owner's answer 1; the text is in *For the lane*). A different
  agent reviews the draft and, later, the build.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** **build-class** by AGENTS.md's definition (it edits `.github/workflows/release.yml`)
  **and a judge change**. Edits to `tests/harness/upstream.py`, `packages.py`, `regrtest.py`,
  `plugin.py`, `scoreboard.py`, `history.py`, `shards.py`, `gather.py`, `sameness.py`, `scan.py`;
  `tests/upstream/numpy.toml`, `pandas.toml`, `contourpy.toml`, `python.toml`, new
  `tests/upstream/python/cpython-release*.txt`; `tests/release_shards.toml`; unit rows; new
  `context/release-tier-claims.toml`; `context/progress/README.md`, `README.md` (the testing
  paragraph), `CHANGELOG.md`; `tests/checks/test_rules.py` (the allowance entries the four TOMLs'
  edits retire, and the new rules rows). New class lists under `tests/upstream/expected/` and
  their gaps in `tests/known_gaps.toml`. The lane accepts with `--accept-judge`, with the new
  `--accept-tier-move` for contourpy's seventeen groups that move from the normal tier to the
  release tier (Decisions 5 and 7), and with `--accept-growth` only for what criterion 4 measures.
  No pass leaves a normal group, so no `--accept-fewer-passes`.
- **Depends on:**
  - **066** (landed in wave 08, main `faa9c93`): the package families, `measured`, `rule_cap`,
    `[[split]]` by constructed `-k` expressions, contourpy's 40 groups and the fourteen
    `upstream-plot-*` shards. 102 changes contourpy's selection (Decision 7).
  - **101** (wave 09): the `inputs` job and its decision step, the `from-source` input,
    `max-parallel: 20` on every judge matrix, the build shard as a pseudo-system on Linux
    (`shards.PLATFORM["build"] = "linux"`, `gather.JOB["build"] = "build-shard"`). 102 adds a
    `tier` output to the same job and a fourth judge matrix in the same shape. Built after wave 09
    lands, or stacked on wave 09's reviewed tip (§4.14), the Status naming the base.
  - **100** (wave 09): numpy on OpenBLAS changes `numpy.linalg`, where 9 of numpy's selected
    `slow` lines sit. The survey (Decision 11) runs on a set with 100.
  - Landed: **050**, **051** (groups, `passes`, classes, traps), **063** (shards, G1 to G7),
    **065** (CPython's suite under regrtest, families, budgets), **091** (fuel facts), **092**
    (the release record, sameness, claim lists), **052** (several cores), **062** (the history's
    format 2).
- **Meets, with an order rule each** (Decision 15): **067** and **095** mark their release-tier
  groups under Decision 2's rules; the roadmap's order is wave 09, then 045, 102, 095, 067.
- **The owner's decisions it writes to** (`decisions.md`, main `4161ef9`):
  - "Two tiers of tests" (2026-10-20, evening): "I think we should have two concepts of tests. We do
    not need to run the slow tests unless we're are creating a new release that we publish to
    pypi. Otherwise, for normal checks, we don't run the slow tests."
  - "Spec 102's four questions" (2026-10-20, night): (1) the constitution is amended at 102's
    landing: the landing judge is the normal tier, with a release-rule line; (2) the lane runs the
    release tier locally **only before a tag**, so a release-tier regression surfaces at the
    release acceptance and is traced back to its wave then; (3) contourpy's `random_big` cases move
    to the release tier: "Move to slow teir. We can decide what is slow tier but do not exclude
    anything from the full suite."; (4) CPython's resource-gated tests (`-u cpu`, `largefile`) join
    the release tier.
- **Research it stands on:**
  - Spec 066 (READ on main): contourpy's groups, each with its `measured` fuel (EXECUTED there):
    the ten `--runslow` cases 946.6 G in `contourpy-filled-9`, `-10`, `-11`; the `random_big`
    cases in `contourpy-filled-1` to `-7` (1,939.5 G) and `contourpy-lines-1` to `-7` (1,083.6 G).
    The Linux rate, 0.16 to 0.31 s per G past about 60 s of setup (dry run `39371419248`, READ
    there).
  - Spec 065 and `tests/upstream/python.toml` (READ): CPython's suite runs under regrtest in five
    groups from plan files, `resources = "all,-cpu,-gui,-largefile"`; a group's JSON already
    carries `match` (`-m`) and `ignore` (`-i`) lists (`regrtest.group_spec`, `trap_spec`).
  - Spec 067's revision (READ at `0eb887d`): release-tier groups that run the complement of their
    normal partner's marker expression; sympy's `slow` and `tooslow`; `test_issue_17141_slow`,
    about 2,609 G alone (EXECUTED by 067's pre-build review).
  - Spec 101 (READ at `827f826`): a source run is 38 jobs wide at most; the Pro plan allows 40
    concurrent jobs, 5 of them macOS (READ there); tags and dispatches on main never reuse a set.
  - `../research/2026-10-18-the-release-judges-in-parallel-shards.md` (READ, through spec 065):
    0.154 to 0.170 s per G on a quiet Mac.
  - **Read while drafting, no guest run** (EXECUTED; readers in the drafting agent's scratchpad,
    `readers/slow_lines.py` and `readers/cpython_resources.py`, stdlib only, run with `uv run
    --no-project python -I`, tarballs read as data with `tarfile`, nothing unpacked): the pinned
    `numpy-2.5.2.tar.gz`, `pandas-3.0.6.tar.gz`, `contourpy-1.4.0.tar.gz` and `Python-3.15.0.tar.xz`,
    each first checked against `downloads/SHA256SUMS` with `shasum -a 256` (all four equal). The
    counts are in Decisions 7 to 9.
  - The release workflow's run list (`gh run list --workflow release.yml --limit 200`, read-only;
    EXECUTED): since the wave pipeline began, every dispatch on `main` has been a pre-tag dry run.
    The last, `39252500950` (2026-10-19 12:29), preceded `v0.1.0a7`'s tag run `39255794160`; wave
    dry runs run on `wave/NN` (`39442080658` on `wave/07`).

## The problem

The owner's rule is "every test of every package we build" (`decisions.md`, 2026-10-20). Today it
is met in the most expensive way, and in places not at all:

1. **Tests are left out.** numpy's 33 and pandas' 27 `slow` lines in the selected files are dropped
   by `-m "not slow"` (spec 050). CPython's tests that need the `cpu` or `largefile` resource are
   skipped by `-u all,-cpu,-gui,-largefile` (spec 065): 82 decorator lines in 53 planned files,
   one module-level gate, and four tests that do less work without `cpu` (EXECUTED, Decision 9).
   The two `largefile` gates do not run under WASI (Decision 9).
2. **The tests that do run cost every check.** Every branch run, wave dry run and lane acceptance
   pays for contourpy's slow and `random_big` cases, about 3.97 T of 066's measured fuel (EXECUTED
   there, Decision 7). After 067 it would pay for sympy's slow tests too.
3. **The judge has no notion of a test that runs only sometimes.** The ratchet puts an accepted
   upstream check that did not run into `upstream_unrun`, and `--accept` refuses it without
   `--partial` (`scoreboard.accept`, READ). The gather is red on a collected check that ran in no
   record (G3) and on an accepted pass or gap that ran in no record (G5) (`gather.py`, READ).

The owner's answer: two tiers. The slow ones run before a publication. Nothing is left out.

## Principle

**Each test runs in one tier, by construction, with one named exception.** The normal tier and
the release tier together are the whole suite. Which tests are slow is the project's choice, written down with a
reason; that every test lands in a tier is proven, not trusted. The exception runs in both:
a CPython test that does less work when the `cpu` resource is off (Decision 9). It runs reduced in
its normal group, on every system that group runs on, and in full in the release tier. So no test
leaves a system it runs on today.

**A row its tier did not run is not run, never lost.** It keeps what was accepted, in
`accepted.json` and in the history's passed set, it is counted by name, and it never needs
`--partial`.

**A move between tiers is never quiet.** A check accepted in one tier that is now in the other is
red until the lane accepts the move with a flag and a reason of its own.

**Only the lane accepts, on darwin, and the release tier only before a tag.** Between tags, the
release-tier rows a specification changes are claimed in writing; at the release acceptance every
release-tier difference must meet a claim, or it is traced back.

**A publication runs everything.** A tag publishes only if its own run judged both tiers and the
newest acceptance judged both.

## Decisions

### 1. Two tiers, and where each runs

- **The normal tier** is every check but the release-tier groups' checks (their suite, class and
  trap checks). **A release run** runs both tiers.

  | run | tier |
  |---|---|
  | a pushed tag `v*` (the publishing run) | release, always |
  | a dispatch on `main` (AGENTS.md rule 6b's dry run before a tag) | release, always |
  | a dispatch on any other branch (`spec/*`, `wave/*`) | normal; release when the dispatch input `release-tier` is true |
  | the lane's acceptance | normal at every landing; release only at the release acceptance before a tag (Decision 5) |
  | a builder's or reviewer's local run | normal; release with `--tier release` (single node ids, AGENTS.md rule 3a) |

- **Why main is always release, with no input to turn it off.** Rule 6b's dry run rehearses the
  tag and must be what the tag run will be. Since the wave pipeline began, every dispatch on main
  has been a pre-tag dry run (EXECUTED, the run list); landings dry-run on `wave/NN`.
- **Why a branch may ask for it.** A specification that adds or changes release-tier groups (this
  one, 067, 095) shows them on CI before review, and writes its claims from that run (Decision 6).
  The owner's answer 2 limits the lane's local runs, not a builder's CI run.

### 2. Which tests are release-tier: three kinds of selection, each with its reason

The release tier is chosen by the project. Each family says how, in its TOML, with a written
reason per entry. Three kinds, one per way a suite is run:

**(a) By upstream's markers** (pytest families). `release_marker` is the `-m` expression the
family's marker-selected release groups run; `excluded_marker` (optional, with
`excluded_reason` and `excluded_closes_with`) names what no tier runs for a true reason (pandas'
`"network or db"`: no network and no database server in the guest, `README.md`). Normal groups keep
the family's `marker`. **The truth table**: with pytest's own expression parser on the host
(`_pytest.mark.expression.Expression`, as 066's `_keyword_errors` uses it), over every assignment
of true and false to the names the three expressions use, `marker and release_marker` is never true
and `marker or release_marker` is exactly `not excluded_marker` (or always true without one). An
expression the parser accepts but the table cannot evaluate (a marker with keyword arguments) is
refused. **What may be excluded is a closed list.** `excluded_marker` may name only markers in
`upstream.EXCLUDABLE`, today `network` and `db`, each a guest capability `README.md` says is
absent. Any other name in it, or a name of that list used in `release_marker`, is refused. So
`excluded_marker = "slow"` (which the truth table alone would allow) cannot leave a family's slow
tests out of both tiers. A name joins the list only by a judge change with its reason.

**(b) By the project's keyword selections** (pytest families). `[[release_select]]` entries, each
with `files` (test files of the family), `keyword` (a pytest `-k` expression) and `reason`. Within
the named files, a test that is not marker-selected and matches the keyword is release-tier.
**By construction**: a normal group over one of those files adds `-k "not (K)"`, K being the OR of
the entries naming that file; a keyword-selected release group runs `-m <marker> -k "(K)"`. So
within the normal marker class each test matches K or not, never both. The rules: every entry has a
non-empty `reason`; each keyword parses; the keyword release groups' paths, taken together, are
exactly the entries' files.

**(c) By CPython's resources** (the regrtest family). Decision 9: a test that needs the `cpu` or
`largefile` resource is release-tier, and **the judge proves the partition on every normal run**:
the set of tests a normal group skips for those two resources equals its release list's `gated`
entries, by id. A test that reads `cpu` inline and does less work without it is the Principle's
exception: it runs reduced in its normal group and in full in a release group.

| family | kind | normal selection (changes in bold) | release selection | reason |
|---|---|---|---|---|
| numpy | (a) | `-m "not slow"` | `-m slow` | upstream's own slow marker |
| pandas | (a) | `-m "not slow and not network and not db"` | `-m "slow and not network and not db"` | upstream's own slow marker |
| contourpy | (a) and (b) | **`-m "not slow"`**, and **`-k "not (random_big)"`** in `test_filled.py` and `test_lines.py` | `-m slow`; `-m "not slow" -k "(random_big)"` in those files | `--runslow`, contourpy's opt-in; `random_big`, contourpy's own slow-host selection (its CI's emulated legs run `-k "not big"`), about 2.83 T, the owner, 2026-10-20 |
| python (CPython) | (c) | `-u all,-cpu,-gui,-largefile`, unchanged | `-u all,-gui`, `-m` each listed test (the four inline-`cpu` tests also stay in their normal groups) | regrtest's own opt-in resources, the owner, 2026-10-20 |

So nobody can drop a test, and nobody can move one quietly: a move is a TOML or plan edit with its
reason, seen in the diff and the judge hash, and the partition still holds. The ratchet sees it
too (Decision 5): a whole check that moves is `moved`, red without `--accept-tier-move`; a test
that moves out of a normal group lowers that group's `passes`, which is `fewer`, red without
`--accept-fewer-passes`.

### 3. The groups

- A group carries `tier = "release"` (default `"normal"`); a pytest release group carries
  `release_by = "marker"` or `"keyword"` when its family has both kinds.
- **A release group is one of the named kinds, or it is refused.** It is a marker release group
  (its family has `release_marker`), a keyword release group (its family has `[[release_select]]`
  entries), or a regrtest list group (its plan a `cpython-release-<n>.txt` of ids). 067 adds a
  fourth, the node-id group, under these rules. A group with `tier = "release"` that is none of
  these (a plain group in a family with neither `release_marker` nor `[[release_select]]`) is
  refused, so a whole group cannot be moved out of the normal tier without a selection that says
  why.
- **Paths.** In a family, the marker release groups' paths taken together are exactly the normal
  groups' paths taken together; the keyword release groups' paths are exactly the entries' files
  (Decision 2b); no path is in two release groups of one kind, except a file split by `[[split]]`.
- **The argv.** A release group's argv is its family's, with its tier's `-m` and `-k` in place:
  its paths, the family's `not_selected` as `--ignore`, its traps as `--deselect`, the family's
  `args`. A normal group's argv, and so its JSON, is byte for byte what it is today, except
  contourpy's (Decision 7) (criterion 4). CPython's normal groups' JSON does not change
  (Decision 9).
- **`[[split]]` per tier.** A split's groups share one tier (and one `release_by`); a file may
  carry one split per tier and kind. The constructed expressions (066, Decision 11) are built
  within the split, then joined to the tier's filter: group i of a split runs `-k "(F) and (eᵢ)
  and not (e₁ or … or eᵢ₋₁)"`, F being `not (K)` for a normal group on an entry's file, `K` for a
  keyword release group, and nothing otherwise. A test is in one tier by Decision 2, then in one
  group of that tier by the construction. Each split records its file's `collected` count, compared
  within the split.
- **A release group that selects nothing fails** (pytest's exit 5, or a regrtest group that runs
  no listed test), as 066's split groups do.
- **Caps by 066's rule, in every family.** A release group carries `measured`, its cap at most
  `rule_cap(measured)`; in numpy's, pandas' and CPython's TOMLs too, where normal groups keep
  their caps. The 480 G bound applies; a release group past it is split by path or by `[[split]]`.
- **Traps and fuel facts** in a family with release groups name their `group`, and take its tier.
- **067's node-id group** (`sympy-slow-17141`): 067 adds that form under these rules.

### 4. The stage never depends on the tier

Each family's stage (`/upstream`, `/cpython`, `/upstream-<package>`) holds every group's JSON,
both tiers', on every run. The tier decides which checks run, never what is staged. The stage's
content moves fuel (063, Decision 5: numpy-lib by 3.9e-5; READ there); a tier-dependent stage would
give a normal row one fuel on a normal run and another on a release run. The new JSON files are a
one-time change, measured by criterion 4.

### 5. The ratchet, and who accepts release-tier rows

**The record.** Every run record carries `meta.tier` and a new field, `release_checks`: every
release-tier check by this tree's TOMLs and plans, sorted, on every run, both tiers. In a run that
is not a shard run, the normal tier deselects each of them, reason `release tier`. A shard run's
tier is its shard's (Decision 10); `--tier` with `--shard` is an argument error, one line.

**Each accepted entry records its tier.** An entry in `accepted.json` gains `tier`, written as
`"release"` for a check in the run's `release_checks` and left out for a normal-tier check
(absent reads as normal, so today's file needs no rewrite and its normal entries keep their
bytes). It is the check's tier, not the run's: a release acceptance writes both kinds.

**The ratchet** (`scoreboard.compare`), with `R` the run's `release_checks` and an entry's tier
read as above:
- **`moved`**: an accepted entry whose tier is normal and whose check is in `R`, or whose tier is
  release and whose check this run collected (in its checks or its deselected list) outside `R`.
  It is red on any run, in either direction, whether or not the check ran. A move is never only a
  TOML edit: it is a row the lane names. A release-tier check that is gone altogether is `absent`,
  as today, and `--retire` takes it.
- **`release_tier`**: on a normal run, an accepted check in `R` that is not `moved`. It goes there
  and nowhere else (not `deselected`, `upstream_unrun` or `absent`); never red, never asking for
  `--partial`; the ratchet line prints `release tier not run <n>`, and `moved <n>` when there are
  moves.
- On a release run the release-tier rows are ratcheted like any other.

A single test that leaves a normal group for a release group (a new `[[release_select]]` entry,
say) leaves the group's check where it was and lowers its `passes`: that is `fewer`, red without
`--accept-fewer-passes`, as today. So both ways of moving tests, by test and by check, are red.

**The acceptance** (`scoreboard.accept`):
- **Rows.** A check not run here keeps what was accepted (READ: the code keeps every status but
  pass, fail and gap). So a normal acceptance never changes a release-tier row's status or
  metrics.
- **Moves.** `--accept` refuses while `moved` is not empty, unless `--accept-tier-move "<reason>"`
  is given; the reason begins with the specification's number and goes in the history line as
  `tier_move_reason`. With it, each moved entry's `tier` is rewritten to its check's tier now,
  status and metrics kept, whether or not the check ran.
- **The history's passed set.** On a normal run, the passed set is the run's passes **plus** every
  check in `R` that is in the newest line's passed set (`history.last_passed`). So a release-tier
  pass that a normal run did not run is carried forward, and a normal acceptance's `passed_added`
  and `passed_removed` name normal-tier changes only. A release acceptance's name every change. The
  `passed_digest` covers the carried rows, so the history replays.
- **Counts.** The line's per-area `counts` take each check in `R` that this run did not run at its
  accepted status, so a normal acceptance's counts do not fall by the release tier's size.
- The history line gains `tier` (`"normal"` or `"release"`; absent reads as normal) and
  `tier_move_reason`, and `test_progress_history_is_intact` accepts both.

**At 102's own landing**, contourpy's seventeen groups move (Decision 7): their suite, class and
trap checks are accepted, tier normal, and are in `R`. They are `moved`, and the landing carries
`--accept-tier-move` (For the lane). The new release groups' checks have no entry: they are not
moved, only not run, until the release acceptance accepts them.

**Who accepts: the lane, on darwin, only at the release acceptance before a tag** (the owner's
answer 2). On main's tip, after the last wave and before the dry run on main:

```
uv run pytest -n 3 --tier release --accept "Release <version>: the release tier" [flags]
```

A landing that changes a release-tier row does **not** run it: the lane's landing judge is the
normal tier, and those rows stay as last accepted (or unaccepted, if new) until the release
acceptance. **Never from a CI record**: G5 holds only darwin fuel, `accepted.json` keeps darwin's
metrics alone, and Linux fuel moves between runs of one judge on one artifact (spec 092: `cpython-b`
3.5% apart over three runs; EXECUTED there). A release-tier row accepted from Linux would have no
fuel ratchet.

### 6. Between tags: the claims ledger, and tracing a regression back

**The ledger.** `context/release-tier-claims.toml` holds, between two release acceptances, one
`[[claim]]` block (092's shape: `spec`, `new`, `retired`, `changed`, `passes`, `grows`, `growth`)
per landed specification that changes a release-tier row or what one runs:
- a specification that adds, removes, moves between tiers, splits, re-caps or re-classes a
  release-tier group writes its block from its branch run with `release-tier: true` (required for
  it; criterion 6 here) and its own measurements;
- a specification that changes a package with release-tier groups (its pin, its recipe, a patch, the
  toolchain) writes a block that names those groups under `changed`, with what it expects, or
  "release tier not run" when it did not dispatch with the tier.

The lane appends each block at the landing, in the landing's context commit; nobody edits an
earlier block. At the release acceptance the ledger is closed: its blocks move under a heading
`## <version>` in `context/release-tier-claims-history.md`, and the file starts empty.

**At the release acceptance**, the lane compares release-tier rows only:

```
uv run python tests/harness/sameness.py build/releases/<previous>/record.json build/progress/latest.json --tier-rows release --claims context/release-tier-claims.toml
```

`build/releases/<previous>/record.json` is the previous release acceptance's record, which the lane
keeps (as it keeps `build/wave-NN/`); for the first release with a tier (0.1.0) there is none, every
release-tier row is new, and the ratchet against `accepted.json` is the check. `--tier-rows release`
is new in `sameness.py`: it compares release-tier rows alone. Every difference no block explains,
and every ratchet line on a release-tier row (`LOST`, `FEWER`, `GREW`, a class whose members now
pass), is a **release-tier regression**, and the tag waits.

**If that record is gone.** The lane has cleared `build/` before to free disk. The ratchet does
not need it: no normal acceptance writes a release-tier row (Decision 5), so `accepted.json`'s
release-tier rows are the previous release acceptance's, and the ratchet at the release
acceptance already compares every one of them for `LOST`, `FEWER` and `GREW`. The record adds
outcomes by id. The lane keeps it, and names its SHA-256 in the release acceptance's reason. If it
is missing, the lane says so in that reason and relies on the ratchet alone.

**Tracing it back.** For each regression:
1. the ledger and the waves' claim lists since the previous release acceptance name candidate
   specifications (a `changed` entry, a guest-fuel growth, a package rebuild);
2. `git log` of the group's TOML, plan, package pin and recipe since that acceptance names the
   candidate waves;
3. if one candidate remains, a fix-forward specification fixes it, or claims it (growth with its
   reason); if not, that specification's builder runs the one group by node id with `--tier
   release` on each candidate wave's acceptance commit (a worktree each, its set rebuilt from those
   pins in a native build slot the lane grants), first and last first, and bisects. Two strikes,
   then written down (AGENTS.md rule 7).

A lost pass or a fall in `passes` is fixed forward before the tag; growth is accepted with a reason
that names its wave. This is the price of the owner's answer 2, stated so the lane plans for it.

### 7. contourpy: its slow and `random_big` cases move, its splits are re-made per tier

- **`random_big`** matches exactly two functions (EXECUTED: `test_filled_random_big` at
  `tests/test_filled.py:853` and `test_lines_random_big` at `tests/test_lines.py:1818`); **slow**
  marks exactly one, `test_filled_compare_slow`, ten seeds (EXECUTED: one `mark.slow` line in
  contourpy 1.4.0's `tests/`).
- `contourpy.toml`: `marker = "not slow"` (was none), `release_marker = "slow"`, one
  `[[release_select]]` (`files = ["tests/test_filled.py", "tests/test_lines.py"]`, `keyword =
  "random_big"`, the reason of Decision 2). `args` keep `--runslow` (so contourpy's conftest does not
  skip a slow case before `-m` sees it) and `--runtext` (text cases are not slow).
- **The groups by tier** (fuel: 066's `measured`, EXECUTED there):

  | tier | groups | fuel |
  |---|---|---|
  | release, marker | `contourpy-filled-9`, `-10`, `-11` (the ten slow seeds) | 946.6 G |
  | release, keyword | `contourpy-filled-1` to `-7`, `contourpy-lines-1` to `-7` (`random_big`) | 3,023.1 G |
  | normal | `contourpy-1`, `-config-1`, `-config-2`, `-rest`, `-filled-8`, `-filled-12`, `-lines-8` | 1,847.3 G |

- **The splits.** `test_filled.py`: a keyword release split, groups 1 to 7 with 066's e₁ to e₆
  (group 7 the rest of `random_big`); a marker release split, groups 9 to 11 with 066's e₉ and e₁₀;
  a normal split, groups 8 and 12 with `serial` (group 12 the rest). `test_lines.py`: a keyword
  release split, groups 1 to 7 with e₁ to e₆; group 8 is the normal group of the file, unsplit. The
  same tests land in the same groups as today; only the expressions that say so change.
- **What moves.** Every contourpy normal group gains `-m "not slow"`, and those over the two files
  `-k "not (random_big)"`; every release group's `-k` changes form. Selections do not change; fuel
  may move by the filters' cost on each item. The survey re-measures all 40 groups; each `measured`
  and cap follows the new number, and a move past 1e-4 is claimed with this reason.
- **The seventeen groups' checks are `moved`** (Decision 5): accepted in the normal tier, now
  release-tier. 102's landing accepts the move with `--accept-tier-move` and the owner's answer 3
  as its reason; their status and metrics are kept until the release acceptance runs them.
- **The normal tier gets lighter.** About 3.97 T of the 5.82 T of contourpy's measured fuel leaves
  every branch run, wave dry run and lane acceptance.

### 8. numpy's and pandas' slow tests join

- **What is there** (EXECUTED, `readers/slow_lines.py`; a line may stand for several parametrized
  cases): numpy-core 6 lines in 5 selected files, numpy-lib 10 in 5, numpy-others 17 in 8
  (`linalg/test_linalg` 8 of them); pandas 27 in 15 across its eight groups (`frame/methods/test_to_csv`
  9). numpy has 21 more in files `not_selected` for their own reasons; they stay out. No `slow` line
  is module-level.
- **The groups.** `numpy-slow` over the three normal groups' paths; `pandas-slow` over the eight
  groups' paths; each split by path if the survey measures it past 480 G; `measured` and caps by
  the rule.
- **What they will find, INFERRED.** Mostly large-memory and long-loop tests: expected classes
  `no-processes`, `no-threads`, `wasm32-memory`, and skips where numpy's `requires_memory` cannot
  read the host's memory. 0.1 to 2 T for both, unknown to within an order until measured.

### 9. CPython's `cpu` tests join; its `largefile` tests already run

**What is there** (EXECUTED, `readers/cpython_resources.py` over `Lib/test` of the pinned
`Python-3.15.0.tar.xz`, against the five plan files' 543 modules):
- 82 `requires_resource('cpu')` lines in 53 planned files (89 in 58 in all); the ones in modules
  the plans already leave out (`test_gdb`, `test_cext`, `test_subprocess`, …) stay out with those
  modules;
- one module-level gate, `requires('cpu')` in `test_peg_generator/__init__.py`;
- two `requires('largefile', …)` gates, in `test_io/test_largefile.py` and `test_mmap.py`.
  **Neither runs under WASI** (READ by the pre-build review: `test_largefile.py:274` gates only
  when `sys.platform[:3] == 'win' or sys.platform == 'darwin'`, `test_mmap.py:1281` only on
  Windows and Apple; the guest's `sys.platform` is `wasi`). Both modules take the other branch:
  they seek past 2 GiB and skip with "filesystem does not have largefile support" if that fails.
  Both are planned in the normal tier already (`cpython-fs.txt`), and stay there, where that probe
  decides whether they run; the survey records which;
- four tests that read `is_resource_enabled('cpu')` and do less work without it, in
  `test_posixpath`, `test_tokenize`, `test_unicodedata` and `test_unparse`.

**How regrtest runs them.** `python.toml` gains `release_resources = "all,-gui"` (today's
resources plus `cpu` and `largefile`; nothing else changes) and release groups,
`[groups.cpython-release-<n>]`, each with a plan file `tests/upstream/python/cpython-release-<n>.txt`
of **full test ids** (or a module, for a module-level gate), one per line with its kind (`gated` or
`inline`) and its normal group. The release group's JSON: `modules` the ids' modules, `match` the
ids, `resources` the release resources. The normal groups keep today's resources and today's
JSON, byte for byte. `release_resources` keeps `largefile`, so the release tier enables what the
owner asked for, but no `gated` entry names a `largefile` gate unless the survey's normal streams
show one. The `cpu`-decorated tests inside `test_largefile` (its lines 192 and 242) are `gated`
entries like any other.

**The partition, proven on every normal run** (the regrtest verdict, `regrtest.py`):
- **gated**: the set of tests a normal group reports skipped with `resource 'cpu' is not enabled`,
  `resource 'largefile' is not enabled`, or `Use of the 'cpu' (or 'largefile') resource not
  enabled`, plus its modules ending `RESOURCE_DENIED` for those resources, equals the `gated`
  entries naming that group, by id. A gated test missing from the list, or a listed test that was
  not gated, is a finding: no test can fall between the tiers;
- **inline**: an `inline` entry is **not** ignored in its normal group. It runs in both tiers:
  in its normal group on every system that group runs on, doing the reduced work `cpu` off
  allows, and in its release group on Linux and in the release acceptance, with `cpu` on, doing
  the full work. This is the one case where a test id runs in both tiers (the Principle). It is
  not a duplicate, because the work differs, and nothing leaves a system: `test_posixpath`'s
  inline test is in `cpython-fs`, which runs on Linux, macOS and Windows, and keeps running on all
  three. The proof: each `inline` entry ran in its normal group's stream (not skipped, not
  missing) and is in its release group's `match`;
- **in the release group**: every listed id ran, and none was skipped for those two resources.
- **No inline test is unlisted** (a rules check, so a re-pin cannot add one quietly): over the
  `Lib/test` members of the pinned CPython tarball, read as data as `regrtest.py` already reads
  them for its id checks, the set of test functions in planned modules whose body reads
  `is_resource_enabled('cpu')` equals the plans' `inline` entries, by id. A fifth such test after
  a re-pin is red until it is listed.

So the normal groups' `passes` do not fall, and 102 needs no `--accept-fewer-passes`.

**What they will find, INFERRED.** The `cpu`-gated tests are long loops and large inputs;
`test_largefile`'s two `cpu`-gated tests write past 2 GiB in the guest's writable root, if its
filesystem probe passes. Fuel 0.3 to 3 T, until measured.

### 10. Where the release tier runs: a fourth judge matrix, Linux only

- **Shards.** Release groups go in shards of a pseudo-system `release`, as the build shard is the
  pseudo-system `build`: `shards.PLATFORM["release"] = "linux"`, `gather.JOB["release"] =
  "judge-release"`, sameness's `SYSTEMS` maps `release` to `linux`. Each release group is in
  exactly one release shard; a release shard holds only release groups; a normal group is in no
  release shard (063's rule becomes "every normal group is in exactly one Linux shard"); `rest`
  never takes a release-tier check.
- **Packing.** 066's rule, at most 725 G a shard, from measured fuel; a single group past it gets a
  shard of its own (067's sympy group, allowed past the 360 s bound by the owner).
- **The normal plot shards are re-packed.** Seventeen of contourpy's groups leave them; some would
  be empty (`upstream-plot-a` holds only `filled-7` and `filled-11`), which G3 refuses. The builder
  re-packs the normal groups at 725 G, letters contiguous. INFERRED: about 6 T of normal plot fuel
  in nine shards; release contourpy about 3.97 T in six.
- **Linux only**, as 066's Decision 12; the lane's darwin run is the darwin record.
- **The job.** `judge-release`, `runs-on: ubuntu-24.04`, `needs: [inputs, build]`, `if:
  needs.inputs.outputs.tier == 'release'`, its matrix exactly the plan's release shards,
  `max-parallel: 20` (the one text 063's rule 3 and 101's Decision 9 require), steps text-alike with
  `judge-linux`'s, handing on `<shard>-id` and `<shard>-sha256`; every value through `env:`.

### 11. The survey comes first, as research

A research step, **time-boxed at 90 minutes**, before any TOML, plan or harness line is committed,
on main's frozen set after wave 09, with the judge's embedder, a private copy of the set, one
session per group, at most three at once, never while `build/lane.lock` exists. It measures numpy's
and pandas' candidate release groups, CPython's release lists (the normal groups' resource skips,
read from their streams, and the release groups run with `-u all,-gui`), and every contourpy group
under Decision 7's argv: outcomes by id, fuel, traps, collection errors, classes. Written up as
`context/research/2026-10-2x-the-release-tier-survey.md`, EXECUTED, with the stand-in and the
streams. **It states the release tier's measured darwin cost**, its fuel in total and its longest
group, at 0.154 to 0.170 s per G (the parallel-shards research), so the lane can book the release
acceptance's slot; INFERRED before measuring, 4.4 to 9 T, about 12 to 25 minutes of guest time on
top of the normal tier at `-n 3`, and after 067 sympy's 2.6 T group the longest leg. Its delta goes
to the build review, unless it finds a trap, a group past 480 G that a split
cannot bring under, or a class whose closer is not `README.md` or a landed specification: then a
context-only delta review first, as 066's.

### 12. How a run knows its tier: the `inputs` job decides once

101's `inputs` job gains one step and one output, `tier`, its values through `env:`:

```
tier=normal
if [ "$GITHUB_EVENT_NAME" = push ] && [ "$GITHUB_REF_TYPE" = tag ]; then tier=release; fi
if [ "$GITHUB_REF" = refs/heads/main ]; then tier=release; fi
if [ "$GITHUB_EVENT_NAME" = workflow_dispatch ] && [ "$RELEASE_TIER" = true ]; then tier=release; fi
echo "tier=$tier" >> "$GITHUB_OUTPUT"
```

`on.workflow_dispatch.inputs` gains `release-tier` (boolean, default false). Every consumer compares
with `== 'release'`. **The gather derives it again**: from `GITHUB_EVENT_NAME`, `GITHUB_REF_TYPE`
and `GITHUB_REF` (which a step cannot override), a tag or a dispatch on main is a **release run**
whose `TIER` must be `release`; otherwise red at G1 ("G1 a tag (or a dispatch on main), and the
release tier did not run").

### 13. The gather, by tier

- **G1.** `expected_keys` includes the release shards only when `TIER` is `release`.
- **G3.** On a normal run a release-tier check runs in no record, and one that ran is red ("G3
  <node>: a release-tier check ran in a normal run"). On a release run G3 is today's.
- **G5.** On a normal run, "accepted pass, ran in no record" skips release-tier checks. On a
  release run it holds them, and `passes` and `passed_digest` are compared with the darwin
  acceptance as for any upstream group. On every run, an accepted entry whose `tier` differs from
  its check's tier in the merged record's `release_checks` is red ("G5 <node>: accepted in the
  normal tier, release-tier now", or the reverse), so a branch run shows a move before the lane
  does, and the builder's claim list names it beside its growth lines.
- **G7.** On a release run, the newest acceptance's `tier` is `release` ("G7 a tag (or a dispatch on
  main), and the newest acceptance did not run the release tier"), besides today's rules.
- **The merged record** carries `meta.tier`; a release-tier check of a normal run has no `source`
  and is `deselected`, which sameness does not compare (092, Decision 2).
- **The workflow.** `gather` needs `judge-release` too, with `if: ${{ !cancelled() && !failure()
  }}`. INFERRED from GitHub's documented `needs` semantics: a skipped need skips its dependents
  unless a status function says otherwise; `!failure()` lets the gather run beside a skipped
  `judge-release` and still skips it when any need failed. **The skip reaches past the gather**:
  a job that needs `gather` (or any job downstream of `judge-release`) is skipped on a normal run
  unless its own `if:` carries a status function. `attest`, `publish` and `pypi` run only on tags,
  where `judge-release` always runs, so they are unaffected. A later job that needs `gather` and
  can run on a branch carries `!cancelled() && !failure()` too; check 9 holds it.

### 14. What the release fails on

Each alone stops a tag:
- a release-tier record is red (a failure, an unknown class member, a trap, a lost pass, a fall in
  `passes`, `passes` unequal to the darwin acceptance; G4, G5);
- a release-tier leg failed or was cancelled: the gather is skipped, so `attest` and `publish`,
  which need it, are skipped;
- the release tier did not run on a tag or a dispatch on main (G1), or the newest acceptance did
  not run it (G7);
- an unexplained release-tier difference at the release acceptance (Decision 6);
- rule 6b: no tag without a dry run on main's exact commit that passed every job.

### 15. The order with 066, 067, 095 and 101

- **066** is on main; 102 edits its contourpy TOML and its shard plan.
- **103 to 109** (the structural chain) are 102's base (`dbecd2d`). They change only comments and
  docstrings in the files 102 edits, and add the rule that no comment or docstring outside `src/`
  cites a document; 102's code follows it (Design).
- **101** lands in wave 09; textual conflicts in the `inputs` job, the matrices, the gather's
  `needs` and `env:`, and `scan.py`.
- **067** is built after 102 lands: its release groups carry `tier = "release"`, its families
  `release_marker`; its node-id group and its marker `D` lines are 067's; its complement rule is
  Decision 2's truth table.
- **095** applies Decision 2 to scipy, scikit-learn and statsmodels (its survey reads their slow
  options) and packs its release groups into release shards.
- **0.1.0** waits for 067, which waits for 102: 0.1.0's tag is the first publishing run with a
  release tier, and its release acceptance the first.

### 16. What stays the same

The fast tier (`-m "not slow"`, the judge's own marker on its guest checks) is not the release tier;
a release-tier check is deselected by both. No check is retired and no node id changes. The plain
`uv run pytest` runs serially, the normal tier.

## Intent

The slow tests run before every publication, on Linux in CI and on darwin in the lane's release
acceptance, and nowhere else. Nothing is left out: every test runs in one tier, by construction or
by a check on every run. A row its tier did not run reads as not run. A tag publishes only what its
own run judged, both tiers, and every release-tier change since the last tag meets a written claim.

## Design

| file | change |
|---|---|
| `tests/harness/upstream.py`, `packages.py` | `Group.tier`, `release_by`, `measured` in every family; `release_marker`, `excluded_marker` and `EXCLUDABLE`, `[[release_select]]`; the argv by tier, splits per tier and kind; `tier_of(check)`; the rules (truth table, the closed exclusion list, keyword entries, a release group of a named kind, paths, splits, caps, traps naming a group) |
| `tests/harness/regrtest.py` | `release_resources`, release groups from id plans; the partition check in the verdict (gated equal to the list, each inline id run in its normal group); the release group's "every id ran" check; the reader of `is_resource_enabled('cpu')` over the tarball's `Lib/test` |
| `tests/harness/plugin.py` | `--tier normal|release`; `release_checks`; `meta.tier`; `--tier` with `--shard` refused |
| `tests/harness/scoreboard.py`, `history.py` | `Ratchet.release_tier` and `Ratchet.moved`; the entries' `tier`; `--accept-tier-move`; the passed set and counts carried forward on a normal acceptance; the ratchet line; the history line's `tier` and `tier_move_reason` |
| `tests/harness/shards.py` | the `release` pseudo-system and its plan rules |
| `tests/harness/gather.py` | `TIER` and the release run from `GITHUB_*`; G1, G3, G5, G7 by tier; G5's move line; `meta.tier` |
| `tests/harness/sameness.py` | `SYSTEMS["release"]`; release-tier rows compared only when both records ran them; `--tier-rows release` |
| `tests/harness/scan.py` | the input, the tier step, `judge-release` and its text-alike rule, its matrix against the plan, the gather's `needs`, `if:` and `env:`; a status function on every branch-run job that needs `gather` |
| `tests/checks/test_rules.py` | the rules rows (the inline reader, the workflow rows); the `CONTEXT_CITATION_ALLOWED` entries for `numpy.toml`, `pandas.toml`, `contourpy.toml` and `python.toml` removed as 102's edits clear those files' cited comments (an entry that admits nothing fails) |
| `.github/workflows/release.yml` | the input, the step, `judge-release`, the gather |
| `tests/release_shards.toml` | the release shards; the normal plot shards re-packed |
| `tests/upstream/numpy.toml`, `pandas.toml`, `contourpy.toml`, `python.toml`, `python/cpython-release-*.txt` | Decisions 7 to 9 |
| `tests/upstream/expected/`, `tests/known_gaps.toml` | the release groups' classes |
| `context/release-tier-claims.toml` | new, empty: the ledger (Decision 6) |
| `context/progress/README.md` | "The release tier (spec 102)": tiers, the ratchet line, the release acceptance, the ledger, tracing back |
| `README.md`, `CHANGELOG.md` | which tests run before a publication only, and why; one line |

**No new comment or docstring cites a document.** The chain 103 to 109 holds every comment and
docstring under `tests/` and `.github/workflows/` to giving its reasons in words: no specification
number, section sign, `context/` path or finding id
(`test_code_outside_src_names_no_context_document`). 102's code, its `judge-release` job's comments and its TOML comments follow it. The ledger's path
may appear in code (an argument's default), never in a docstring. 102's edits to the four TOMLs
clear their cited comments, and the matching allowance entries go in the same change.

## Scope

**In:** Decisions 1 to 16. **Out:** 067's and 095's release groups (theirs, under Decision 2);
accepting from a CI record (Decision 5); macOS and Windows release shards; CPython's
`extralargefile`, `gui` and `bigmem` sizes beyond regrtest's default (not in the owner's answer 4;
`gui` has no display, a true reason); wall-clock (§4.9: every time here is a benchmark estimate).

## The checks

Each written before the change it judges and seen failing first on the base's tree.

1. **The partition rules** (`test_upstream_files_are_well_formed`, widened; unit variants each
   failing with its own line): a `release_marker` overlapping `marker` (numpy with `"slow or
   leaks_references"`); a union that is not `not excluded_marker` (pandas without one); a marker
   with keyword arguments; a `[[release_select]]` without `reason`, with an unparsable keyword, or
   naming a file no group covers; keyword release groups whose paths are not the entries' files; a
   split mixing tiers; a release group without `measured` or over `rule_cap`; a trap without
   `group`; `tier = "fast"`; `excluded_marker = "slow"` (a name outside `EXCLUDABLE`) and a
   `release_marker` that uses `network`; a plain `tier = "release"` group in a family with neither
   `release_marker` nor `[[release_select]]`.
2. **The argv** (unit): numpy's and pandas' normal groups' JSON byte-identical to the base's;
   `numpy-slow`'s `-m slow`; contourpy's group 12 `-m "not slow" -k "(not (random_big)) and (not
   (serial))"`; group 7 `-k "(random_big) and not (e₁ or … or e₆)"`; CPython's normal groups'
   JSON byte-identical to the base's, no `-i` entry added; a release group's `match` its plan's
   ids (the inline entries among them) and `resources` `all,-gui`.
3. **The stage** (unit): every family's stage manifest equal under both tiers.
4. **The CPython partition** (unit, fixed streams): a normal stream whose resource skips equal the
   list passes; one with an unlisted `cpu` skip, one missing a listed id, and one module
   `RESOURCE_DENIED` but unlisted are findings; a normal stream missing an `inline` id is a
   finding; a release stream with a listed id skipped for `cpu` is a finding. And the rules row
   over the tarball's `Lib/test`: the readers' set equals the `inline` entries; a mutant plan
   missing one, and a mutant source with a fifth test reading `is_resource_enabled('cpu')`, each
   red.
5. **The ratchet** (unit): a normal run with accepted release-tier rows not run is not red, puts
   them in `release_tier` alone, and `--accept` succeeds without `--partial`, keeping their entries
   byte for byte and writing the line's `tier: "normal"`; a release run failing one is `lost`; a
   history line with and without `tier` is intact. **The passed set**: after a release acceptance
   in which release-tier check X passed, a normal acceptance's line has X in neither
   `passed_removed` nor `passed_added`, its `passed_digest` covers X, and its `counts` count X as
   a pass. **Moves**: a normal-accepted pass that is now release-tier is `moved` and red on a normal
   and on a release run; `--accept` refuses it without `--accept-tier-move` and, with it, rewrites
   that entry's `tier` and nothing else of it; the reverse move is `moved` too; a release-tier
   entry whose check is gone is `absent`, not `moved`; a release acceptance writes `tier:
   "release"` on release-tier entries and no `tier` on normal ones.
6. **The plugin** (unit): `--tier release --shard upstream-plot-a` is an argument error before
   anything runs; every record lists every release-tier check in `release_checks`, and a normal
   record deselects each with reason `release tier`.
7. **The shard plan** (unit): a release group in a Linux shard, a normal group in a release shard,
   a release group in two release shards, and an empty shard each fail `plan_errors`.
8. **The gather** (unit): normal run: no release record expected, a release-tier check run nowhere
   is not red, one that ran is red at G3; release run: a missing release record red at G1; a tag
   with `TIER` normal red at G1; a tag or a dispatch on main with a normal newest acceptance red at
   G7; a branch with `release-tier` and a normal acceptance not red; `meta.tier` merged; an
   accepted entry whose tier differs from the record's red at G5, on both kinds of run.
9. **The workflow** (rules): `judge-release`'s matrix is the plan's release shards; its `if:` is
   exact; its steps are `judge-linux`'s; the gather needs it with exactly `if: ${{ !cancelled() &&
   !failure() }}` and gets every `RECORD_RELEASE_<SHARD>` and `TIER`; every job that needs
   `gather` and is not limited to tags carries a status function in its `if:`. Mutants, each red:
   the `if:` dropped; a shard missing; `always()` in the gather's `if:`; a branch-run job needing
   `gather` without a status function.
10. **The tier step** (rules, run in bash): a tag, a dispatch on main, and a branch dispatch with
    `release-tier` true give `release`; a branch without it, with an empty value, and with `True`
    give `normal`.
11. **Sameness** (unit): release-tier rows of a release record against a normal local record are
    counted, not compared; `--tier-rows release` compares them alone, and with a ledger explains a
    `grows` and leaves a lost pass.

## Acceptance criteria

Counted, never timed.

1. **The checks** exist and were each seen failing first; the landing notes give each failure.
2. **The survey** (Decision 11) exists, EXECUTED, before any TOML, plan or harness line; its delta
   is in the build review (or a delta review, by Decision 11's rule).
3. **The baseline.** Every release group by node id with `--tier release` (a builder's single node
   ids) passes its group check, each class check failing as its gap says; each new group run
   twice, restaging between: equal outcomes and `passed_digest`, darwin fuel within tolerance.
4. **Nothing normal moves but what is named.** numpy's and pandas' normal groups within 1e-4 of the
   base (the stage gained files), or the growth named; contourpy's normal groups re-measured, each
   move claimed with Decision 7's reason; CPython's normal groups' JSON byte for byte as the
   base's, `passes` unchanged, within 1e-4 or the growth named (the stage gained files).
5. **A normal branch run** (default inputs): `tier=normal`; `judge-release` skipped; the gather runs
   and passes, `meta.tier` `normal`; no release-tier check in any record; every red line a growth
   line, a G5 move line for the seventeen contourpy groups (Decision 7), or G7.
6. **A release branch run** (`release-tier: true`): every release leg runs and passes; the gather's
   only red lines are the ones criterion 5 allows, `meta.tier` `release`. The landing notes give
   each release leg's job time, the peak of concurrent jobs and the wall time beside run 5's. The ledger's 102 block is written from it.
7. **The gather's conditions.** Run 5 shows the gather running beside a skipped `judge-release`.
   A failed leg skipping the gather is GitHub's documented meaning of `failure()` and today's
   behaviour (spec 092's run `39357023086`; READ there); the first red release leg on any later run
   is its evidence.
8. **The judge.** `ruff check`, `ruff format --check`, the fast tier green in the worktree. The
   lane's landing acceptance is the normal tier, as answer 2 says.

## The owner's answers

All four answered 2026-10-20, night (`decisions.md`, main `4161ef9`), and written in:
1. **The constitution is amended at 102's landing.** The text is in *For the lane*.
2. **The lane runs the release tier only before a tag.** Decisions 1, 5 and 6.
3. **contourpy's `random_big` cases move to the release tier**, and the project chooses what is
   slow without leaving anything out. Decisions 2(b) and 7.
4. **CPython's `-u cpu` and `largefile` tests join.** Decisions 2(c) and 9. Under WASI the two
   `largefile` gates do not apply, so those tests already run in the normal tier, where a
   filesystem probe decides; the release tier enables `largefile` all the same.

## For the lane

- **Wave kind: build-class** (the release workflow and the shard plan; no artifact byte changes).
  **Dry-run needs:** criteria 5 and 6 on the branch; the wave's dry run in the normal tier.
- **The constitution, amended at the landing** (the owner's answer 1; the lane makes the edit in the
  landing commit, with this header line): "Amended 2026-10-2x by the owner's answers to spec 102's
  four questions: the landing judge is the normal tier; the release tier runs before a release
  (§5.5, §5.7)."
  - §5.7, the sentence "runs the full judge on that exact commit in the main tree" becomes "runs the
    judge's normal tier on that exact commit in the main tree", and "judges the tip once" becomes
    "judges the tip's normal tier once".
  - §5.5, a new last sentence of the paragraph (after "…prepares one and asks (owner,
    2026-10-17)."): "**The release rule** (owner, 2026-10-20):
    the judge has two tiers, normal and release, which together are every test of every package
    built; nothing is left out of both. Before a tag, the lane accepts both tiers on main's tip (the
    release acceptance), and the release workflow judges both on main's exact commit and on the tag
    itself; a release-tier failure, or a release-tier change no claim explains, stops the tag."
- **AGENTS.md** (the lane's to write):
  - rule 3a, after "The one local full judge is the lane's `uv run pytest -n 3` on the wave's tip.":
    "That is the judge's normal tier. The release tier (spec 102) runs on a tag, on the dry run on
    main, and in the lane's release acceptance before a tag, never at a landing; a builder whose
    specification changes a release-tier row dispatches its branch run with `release-tier: true`
    and writes its block in `context/release-tier-claims.toml`."
  - rule 6b, first sentence becomes: "Before a release tag, the lane makes the release acceptance on
    main's tip (`uv run pytest -n 3 --tier release --accept "Release <version>: the release
    tier"`), checks every release-tier difference against `context/release-tier-claims.toml`
    (spec 102, Decision 6), then dispatches the release workflow on main's exact commit, which runs
    the release tier itself, and waits for every job to pass on all three systems."
- **The claim list** (skeleton; the builder fills it from the survey): **new**, the release groups'
  suite and class checks (deselected in the lane's normal record); **changed**, the moved
  contourpy rows (17 groups, normal to release, the ratchet's `moved` list, accepted by
  `--accept-tier-move`); **passes**, none (the inline tests stay in their normal groups);
  **grows**, contourpy's normal groups if Decision 7's argv moves them, numpy's, pandas' and
  CPython's if Decision 4's stage does; **retired**, none; **units**, the rows of *The checks*.
  The same rows go in the ledger's first block (spec `"102"`).
- **The flags** (skeleton; each reason begins with "102:"):

  ```
  --accept "102: the release tier: slow tests run before a publication, nothing left out; numpy-slow, pandas-slow, contourpy's slow and random_big cases, CPython's cpu-gated tests and its four inline-cpu tests in full, in <r> release groups"
  --accept-judge "102: tiers in upstream.py, packages.py and regrtest.py (release_marker with the truth table, release_select keyword entries, CPython's resource lists and their partition check, splits per tier, caps on release groups); --tier and release_checks (plugin.py); the ratchet's release_tier and moved, the entries' tier, the passed set carried forward, the history's tier and tier_move_reason; the release pseudo-system; G1, G3, G5, G7 by tier; sameness --tier-rows; judge-release and the tier step; the TOMLs, plans and shards; unit rows"
  --accept-tier-move "102: contourpy's slow and random_big cases move to the release tier, seventeen groups (the owner, 2026-10-20)"
  ```
- **The acceptance's message** (a normal tier, from 102's landing on): the area counts a normal
  scoreboard prints fall by the release tier's size, since those checks show as deselected. The
  history line's `counts` do not (Decision 5). The lane's message quotes the ratchet line's
  `release tier not run <n>` beside the counts, so the gap is explained.

## The builder's self-check

Filled in at the build, from `context/reviews/README.md`'s list, plus: both branch runs' ids; the
survey's memo and its delta's verdict; the stage manifests' equality; every release leg's job time;
the ledger's first block.

## Risks a pre-build reviewer should probe

- **The gather's `if:`** with a skipped and with a failed `judge-release`; only the first is run.
- **The stage and normal fuel**: new JSON files in `/upstream` and `/cpython` may move normal rows.
- **Release-time surprises** (answer 2): regressions surface only at the release acceptance; is
  Decision 6's ledger and bisection enough, and is the previous release record safe in `build/`?
- **The CPython partition**: regrtest's skip texts and the `RESOURCE_DENIED` state must be read
  exactly; a test gated by both a resource and a platform check may report the other reason; the
  four inline tests run in both tiers (Decision 9), reduced and in full.
- **The `-k` composition**: substring matching (`random_big` matches two functions today); a new
  upstream name containing it moves silently to the release tier, still run, never dropped.
- **contourpy's re-made splits and `collected` facts**, and the re-packed normal shards.
- **Width on a tag**: 38 jobs plus up to 20 release legs; before 067 about six to ten, queued
  behind Linux's normal legs; INFERRED a few minutes, more after 067.
- **Main always release**: a dispatch on main without a release acceptance is red at G7.

## One line

The suite splits into a normal tier and a release tier that together run every test; the release
tier runs only before a tag, and every change to it between tags meets a written claim.

## Landing notes

The build, below, as it goes.
