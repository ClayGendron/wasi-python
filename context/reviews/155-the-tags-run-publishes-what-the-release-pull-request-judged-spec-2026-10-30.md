# Review of 155 — The tag's run publishes what the release pull request judged

- **Date:** 2026-10-30
- **Reviewer:** an agent (Claude Opus), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** the specification as drafted, then as amended for these findings (uncommitted in the worktree, read 2026-10-30)
- **Run:** none
- **Re-ran:** `uv run pytest -q tests/unit/test_ci_plan.py -k tag` → 1 passed, 226 deselected, exit 0; `decide()` and `select()` on a tag event in a scratch interpreter → `judge` True, `tier` release, `verify` on three runners, `build` True; `git rev-parse v0.1.2` and `git log` → the tag is `8e21c2c8`, the acceptance commit, whose parent `193c9996` is the newest release-tier history line's `commit`
- **Box:** 40 minutes; the reading list was done and the findings written inside it.

## Acceptance criteria against evidence

1. On a tag, `judge` false, `rebuild` true, `tier` empty, judge lists `[]`. Not yet sound. Today `judge` is a derived property (`release/ci_plan.py`, `Decision.judge`), and `select()` fills `verify` only when it is true. In the workflow, `inputs` and `build` run only `if: needs.plan.outputs.judge == 'true'`. So the criterion as written switches off the build that Decision 1 keeps (READ; EXECUTED for today's values). See High 1.
2. `judged` exists, needs `build` and `same-bytes`, and gates `attest` and `publish`. Buildable. `test_one_required_check_holds_every_job` will also force it into `ci-status`'s needs (READ, `tests/checks/test_rules.py:632`).
3. `--prove-set` holds in four cases. Buildable once Medium 1 names the field it reads, and once Medium 2 adds a fifth case.
4. No judge leg and no gather on the next tag. To be READ at the landing. Acceptable as written.
5. Constitution §5.5 and the release page. The Design's file list misses pages that say the tag judges (Low 4).
6. Fast tier, lint, `ci-status`. Standard.

## Findings, most severe first

1. **High: "judge false" skips the build, verify and everything after them, and `ci-status` calls that green** (`release.yml:190`, `release.yml:253`, `ci_plan.py` `Decision.judge` and `select()`). `judge` gates `inputs`, `build` and the gather, and it is the only thing that makes `select()` fill `verify`. Criterion 1 asks for `judge` false. Decision 1 still wants `build`, `verify`, `same-bytes`, `attest` and `publish`. Failure: built to criterion 1, a pushed `v0.1.3` runs `plan` and `quick`. `inputs`, `build` and `verify` are skipped, and so is everything that needs them. `ci-status` accepts "skipped" for every job, so the tag's run is green and nothing is published. Fix in the specification: split the flag. Either `inputs` and `build` gate on `judge || rebuild`, and `select()` gives `verify` its three runners when `rebuild` is true, or a new plan output (`release_tag`) drives the tag's jobs. Also say that on a tag `ci-status` is red when `publish` is skipped, so a run that publishes nothing is never green. Add a unit row: on a tag the plan's `verify` holds the three runners and `build` runs.
2. **Medium: the accepted state does not carry `meta.event`** (`tests/harness/accept_from.py:367`, `context/progress/history-00060.jsonl`). The history line's extras are `source`, `record` and `platforms`. Its other fields include `tier`, `commit`, `artifact`, `set_sums`, `dirty` and `partial_reason`, but no event. `accepted.json` holds `checks`, `commit`, `judge` and `schema` (EXECUTED: the keys of the newest line and of `accepted.json`). The event is in the gather's merged record, a run artifact that expires. The line carries only that record's SHA-256. Failure: the builder cannot read "a release pull request's" from the tagged tree. They either invent a proxy or fetch an expired artifact. Either way §5.2's "decides every choice" is not met. Evidence that would close it: the specification picks one route. (a) Require `source == "ci"` and `tier == "release"` on the newest line. Only `--accept-from` of a release pull request's record writes that pair today, because `_event_refusal` admits a push to `dev` (tier normal) or a release pull request (INFERRED from `accept_from.py:125` and `decide()`). (b) Add `event` and `base_ref` to the history line's extras. That changes a judge file, needs a claim, and must land before the release pull request whose tag first uses 155.
3. **Medium: the proof binds the set, not the tagged tree, and the wheel's Python is in the tree** (Decision 2). `set_sums` and `artifact` cover the set's files and `python.wasm`. The wheel also carries `src/wasi_python/` from the tagged checkout. "The judged tree plus the acceptance commit" is asserted in Decision 3 but checked nowhere. Today's G7 has a tag clause that compares the judge hash (`gather.py:566`); 155 drops it with the gather. Failure: a commit C, whose parent is the judged head, changes the acceptance pair and also `src/wasi_python/runner.py`. It reaches `main` by a bypass push and is tagged. The parent check holds, the set hashes hold, and the three hosts rebuild one wheel from C, so `same-bytes` holds. `verify`'s smoke test passes. An unjudged `runner.py` is signed and published. Fix: `--prove-set` also requires `git diff --name-only HEAD^ HEAD` to be exactly `context/progress/accepted.json` and one history volume, the rule `accept-release.yml` holds when it pushes. Add it as a fifth unit case. With it, `verify` on three systems is enough of a smoke test, since every byte it installs is then one the release pull request judged (INFERRED).
4. **Low: name the commit field, and drop "or the tagged commit itself"** (Decision 2). Fix text: "the newest history line's `commit` equals `git rev-parse HEAD^`, the tagged commit's parent; `judged` checks out with `fetch-depth: 2`." An acceptance line cannot name the commit that holds it, so the "itself" branch is dead. The default checkout depth of 1 has no `HEAD^`. A tag on a later `main` commit fails the parent check, as it should (INFERRED). `v0.1.2` has this shape (EXECUTED).
5. **Low: say which `SHA256SUMS`, and derive both hashes from the signed bytes** (Decision 2). Fix text: "`judged` downloads `release-assets` through `verify-artifact`, unpacks the set's tarball as `same-bytes` does, and hashes the set's own `SHA256SUMS` (the line's `set_sums`) and `python.wasm`; it never compares the release assets' `SHA256SUMS` (`sums-sha256`), which lists the wheel." The build job hands on both `sums-sha256` and `set-sums-sha256` (READ). Passing the wrong one reddens every tag.
6. **Low: keep G7's other clauses** (Decision 2). Fix text: "and the line is clean (`dirty` false), not partial, `source` ci and `tier` release."
7. **Low: the loose ends of the tag's plan** (Decisions 1 and 4). Fix text: "`tier` is the empty string on a tag (Decision 1's 'none' is criterion 1's empty). On a tag the plan's `build` is false, so the build shard's checks do not run; 159's Decision 5 drops 'a tag' from its list. The zero-patch step, which has no `if:` on the plan, still runs. The event, parent and diff half of `--prove-set` runs first in `judged`, or in `plan`, so a tag on the wrong commit fails before the compile. G7's tag clauses in `gather.py` stay, for a dispatch on `main`."
8. **Low: pages that say the tag judges** (Design). Fix text: add `context/progress/README.md` (its lines on "Two tiers", G1 and G7 "at the tag", and "Before a release") and `release-process.md`'s release-tier bullet ("on the tag") to the files, along with the workflow's header comment.

9. **Low (found in the amended text): the cheap checks cannot fail "in a minute" from inside `judged`** (Decision 2's last sentence). `judged` needs `build` and `same-bytes`, so its first step starts after the compile and both rebuilds, about 40 minutes in. Fix text: "The event, parent and diff checks run as `--prove-set --tree-only` in a step of the `build` job before the compile (the checkout there already has `fetch-depth: 0`), so a wrong tag fails before the compile; `judged` runs the whole check again on the downloaded assets." Or drop the sentence's last clause.
10. **Low (found in the amended text): 159's criterion 4 still says the tag's `build` output is true** (`159-…`, criterion 4), while 155's criterion 1 says false. Fix text, in 155's Design: "`tests/unit/test_ci_plan.py`'s row for 159's criterion 4 drops the tag, and 159's criterion 4 gains `(a tag until 155 lands)`."

## Constitution checks

- **§2's fifth item (rebuild from pins, zero-patch).** Holds. The tag still compiles from the pins, the three hosts vote, and the zero-patch step stays (READ).
- **§5.5.** The specification amends it, with the owner's agreement recorded in `decisions.md` on 2026-10-30 (READ). As amended, the rule holds: Decision 2 now checks "the judged tree plus the acceptance" rather than asserting it (READ).
- **§5.7.** "Reproducibility is proved ... at the tag" holds (READ).
- **Security.** The 0.1.2 security review and the threat model lean on nothing the tag's judge does (EXECUTED grep; READ).
- **§4.** The constraints are untouched.
- **§7.** Nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. High 1 (judge false switches the build off) — fixed in the specification. A new `publish` output is true on a tag alone. `inputs` and `build` run on `judge || rebuild`. `select()` fills `verify` when `rebuild` is true. `ci-status` needs `judged`, and it is red when the plan said `publish` and `publish` was skipped. Criteria 1 and 2 hold all of it (READ).
2. Medium 2 (`meta.event` not in the accepted state) — fixed in the specification by route (a). The newest line must have `source` `ci` and `tier` `release`. The text gives the reason only a release pull request's acceptance writes that pair (READ). Nothing needs adding to the history.
3. Medium 3 (the proof binds only the set) — fixed in the specification. `git diff --name-only HEAD^ HEAD` must name exactly `accepted.json` and one history volume. It has a unit case, "a second file in the acceptance commit" (READ).
4. Low 4 (the commit field, `fetch-depth`) — fixed. The rule is now `commit == HEAD^` at `fetch-depth: 2`, and "or itself" is gone (READ).
5. Low 5 (which `SHA256SUMS`) — fixed. `judged` downloads the assets through `verify-artifact` and hashes the set's own `SHA256SUMS` and `python.wasm` (READ).
6. Low 6 (G7's other clauses) — fixed. The checks for a clean tree and a line that is not partial stay. `source` and `tier` come in through Medium 2 (READ).
7. Low 7 (loose ends) — fixed. `tier` is empty and `build` is false on a tag. 159's Decision 5 says the tag judges only until 155 lands. The zero-patch step stays "as today" (READ). The cheap checks' placement is Low 9.
8. Low 8 (pages) — fixed. Decision 3 and the Design name the progress README and the workflow's header comment (READ).
9. Low 9 and Low 10 — new, from the amended text. Each has its fix text, and neither needs another round.

## Verdict

Fit to build: the amended specification fixes High 1, Mediums 2 and 3 and Lows 4 to 8, and Lows 9 and 10 carry their fix text for the builder.
