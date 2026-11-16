# Review of 194 — the pydantic suites in the guest

- **Date:** 2026-11-16
- **Reviewer:** an agent (Claude), a fresh sub-agent of https://claude.ai/code/session_01BD1pVHiZoxnwRv6JCqJKeC; not the author
- **Reviewed:** `5cc59db4..7fc3559f` (`9499950b`, the judge files; `7fc3559f`, the context files), against the roadmap's 194 line at `5cc59db4`, 190's Decisions 1, 8 and 9, and 191's Decision 8. Box: 45 minutes; finished inside it.
- **Run:** none: the branch is unpushed, and no self-check exists yet.
- **Re-ran** (EXECUTED):
  - `uv run python release/precheck.py` → exit 1 on the allowed root-only `test_the_walk_judges_links` alone (unit 3,723 passed, 104 skipped); ruff, mypy, rules, budget and lint ok; the plan waits on this file.
  - `uv run pytest tests/lint tests/unit -q -p no:cacheprovider --deselect tests/unit/test_runner_grants.py::test_the_walk_judges_links` → 3,737 passed, 104 skipped, exit 0.
  - `scan.digest(upstream.class_findings(list, list))` of each list file → 13 `d4bce486ff96`, 6 `a243e3dc9965`, 1 `47a860157c80`: each gap's `match` exactly.
  - PyPI's JSON for the three sdists and seven wheels → every SHA-256 and URL matches; none yanked. The seven wheels hold no `.so`, `.pyd`, `.dylib` or `.c` file.
  - `wheel_tie_errors`' comparison of the three wheels with their sdists → no file missing or different. `fetch.shard_packages` and `tarball_names` for the three shards → one pinned tarball each, with its download line. Every group path and `not_selected` file exists; no class member is outside its group.
  - The test-source smoke sum → 1,376.07 G (193.0 G new); plus 17 G, rounded up to 10 G, 1,400 G.

## Acceptance criteria against evidence
1. The families load; the package, tier, shard, kit and gap rules hold — met (EXECUTED).
2. Pins in `SHA256SUMS` and fetched by `00_download.sh` — met (EXECUTED); `MANIFEST`'s three new lines wait for a built set.
3. The first run measures the groups and the classes — not met: no run, and as written no pull-request run can measure the release groups (Medium 1).
4. No figure called measured unless measured — met: each estimate says "provisional" (READ). Each `fuel` is `rule_cap` of its `measured`, each `budget` the sum of its caps, each budget cap twice its smoke cap, and 3.7 minutes is 510 G at 210.2 G per 1.52 min (EXECUTED).

## Findings, most severe first
1. **Medium: nothing but this verdict keeps the provisional figures from merging, and no pull-request run measures the release groups** (`context/specifications/194-the-pydantic-suites-in-the-guest.md:156`, `release/ci_plan.py:514-528`, `:598`). `rule_errors` checks only cap ≤ 1.5 × `measured`, which the estimates meet; `new_family_fuel` is "reported, never red" (`tests/harness/budget.py:139-144`); no check reads "provisional". On a pull request `d.tier` stays `normal` even with `ci:full`, so `upstream-release-070` runs only in the release pull request, the weekly run or a dispatch. The landing notes' "a `ci:full` or release-tier run runs `upstream-release-070`" is wrong. Failure: the PR's run measures the four smoke groups. `pydantic-core-r`, `pydantic-r` and their two no-processes classes merge on estimates, and first run in 0.1.5's release pull request. A red there is the owner's gate failing, so `panic=abort`. Evidence that closes it: the measurement commit (the landing notes' items 1 to 5) with the run's id. For the release groups, either a local run of `test_upstream_suite[pydantic-core-r]`, `[pydantic-r]` and their `test_upstream_class` nodes by node id against the PR's built set (`WASI_PYTHON_ARTIFACTS`), with figures and the set's key in the landing notes; or the owner's answer, by AskUserQuestion, that they may land on estimates until the weekly run. Until then this verdict is the hold; the measurement commit changes `tests/`, so it leaves this review behind and needs a new signing.
2. **Low: the Windows shard runs on the pull request only with `ci:full`** (`release/ci_plan.py:595`; spec `:110`, `:156`). Upstream shards run on Linux alone on a pull request that is not full. Fix: label the pull request `ci:full` (or put a `citest:full` line in a commit message). Write in item 1 of "What the first run measures": "with the label `ci:full`, since a pull request's upstream shards run on Linux alone otherwise". In Decision 7, add: "On Windows only the two smoke groups run; the release groups run where the release tier runs. The gate's 'Linux and Windows' is read as that."
3. **Low: what the measurement does when a figure lands past a bound** (spec `:161`). Add after "and it runs again.": "Raising a cap raises its `measured` with it (`rule_cap`), so the bound is recomputed in the same commit. A smoke group that measures past `SMOKE_GROUP_BOUND`'s 110 G (pydantic-smoke's cap is 140 G), or that takes `upstream-pure-smoke-b` past 725 G, gives up its heaviest file to the release group by path, claimed under `[claim.moved]` and `fewer`. The bound is not raised for it, as 188's Decision 4 says. The estimate is fitted to Python-heavy groups, and pydantic-core's groups are mostly Rust, so its smoke group may run out of its cap first (INFERRED)."
4. **Low: the news file says "in every pull request's run"** (`context/changes/194-the-pydantic-suites-in-the-guest.md:7`). Fix: "a smoke group of each in the normal tier (every merge's run, and a pull request's when the build, the suites or the harness changed), pydantic-core's and pydantic's on Windows in the merge-grade run, and the rest in the release tier, so Rust panics are judged as they unwind."
5. **Low: the jsonschema wheels need a way out** (spec `:50`). Add: "When the set carries 0.1.5's jsonschema, `jsonschema` and `pyrsistent` leave `kit-extra.txt` and pydantic's `kit_extra`, in that pull request, so the suite checks the shipped jsonschema."
6. **Low: the choices section is stale** (spec `:3-4`, `:136-143`). The lead has picked A for each, for now. Fix: under each choice, write the pick, who made it, and what it waits on. 1: the lead's, final. 3: the lead's, final. 2 and 4: branch states, not landable until Finding 1 closes. The Status line's "none is decided here" becomes "the lead picked A for each, for now (The owner's choices)".

## The four choices
1. **jsonschema 4.17.3 with pyrsistent, test-only — holds.** Both are pure, pinned, MIT (EXECUTED), and pydantic's conftest check runs as upstream wrote it, so the judge is not weakened. C would weaken it and is rightly refused; B delays the gate. Record: the check is `Draft202012Validator.check_schema` against 2020-12's metaschema, which 4.17.3 carries; and Finding 5.
2. **The bound raised ahead of a measurement — holds only on the branch.** `smoke_total_errors` runs in the unit tier, so without the raise `quick` refuses the families and no run measures them. 191's "never raised ahead of a measurement" holds only if 1.4 T never lands. Record: 1.4 T is not landable; the measurement commit sets the bound by 191's rule, up or down, with no existing group's `measured` rising; Finding 1's hold.
3. **The two small suites whole as smoke — holds.** six, markupsafe and typing-extensions are whole-suite smoke groups with no release group; the rules require one normal group, not a release group (EXECUTED). Record it as a deviation from the roadmap line and 190's Decision 9, with the reason (a session start is most of 0.29 s and 0.20 s) and the cost (about 40 G of the normal tier, provisional).
4. **`suite` with provisional fuel — holds for the smoke groups, not for the release groups.** `later` would give the run nothing to measure, and no local set exists. But `suite` measures nothing in the release tier on a pull request (Finding 1). Record how the release groups are measured before merge, or the owner's answer.

## Constitution checks
- §4.1: no patch. §4.2: every pin PyPI's (EXECUTED). `MANIFEST` gains three lines, as earlier test-source pins did; no binary, zip or wheel changes. §4.12: the four packages' MIT is approved; the kit wheels are not shipped.
- The judge: no existing class, gap, cap or list moves; each new class is reasoned and its digest right. The one loosening is `SMOKE_TOTAL_BOUND`, claimed (choice 2). Every verdict-bearing file has its `[claim.judge]` line; the `new` checks are in the news file (normal tier) and the ledger file (release tier).
- Code names no specification or `context/` path (READ). Nothing under `src/`, `.github/` or `release/` changes; not structural.
- §7: nothing tripped while 1.4 T and the estimates stay off `dev`.

## Disposition (filled in by the author, then confirmed by the reviewer)
1. —
2. —
3. —
4. —
5. —
6. —

## Verdict
Does not land yet: Medium 1 stands, since every fuel figure, the four budget caps, `SMOKE_TOTAL_BOUND` and the release groups' classes are estimates that only this verdict keeps off `dev`, and no pull-request run can measure the release groups.
