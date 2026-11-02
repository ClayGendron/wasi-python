# 183: A pass count that rises is listed

- **Status:** built 2026-11-01 on `spec/183-a-pass-count-that-rises-is-listed`, from `dev` at `50d2b5cb`, not landed. The owner approved the judge change on 2026-11-01 (`../decisions.md`, "A pass count that rises is listed, not red").
- **Date:** 2026-11-01
- **Owner:** Clay Gendron
- **Kind:** a judge change (`tests/harness/gather.py`). Not structural: nothing under `src/` changes. No pre-build review: it touches neither the guest's imports or exports, the artifact set nor the build recipe (constitution §5.6).
- **Depends on:** landed: 063 (the gather's upstream pass-count row), 138 (the release pull request's gather), 161 (rows listed after a merge), 181. Blocks: the 0.1.3 release pull request, #96.
- **Research it stands on:** the release pull request's run 41359482215 on `50d2b5cb`, its gather job's log (125022985376), and the orchestrating session's diagnosis of that run made on 2026-11-01.

Labels: EXECUTED, run and seen; READ, read from a file or a log, cited; INFERRED, reasoned.

## The problem

Run 41359482215, the 0.1.3 release pull request's, had every shard green, and its gather was red on four upstream pass counts that rose (READ, the gather's log): cpython-release-archives 4 to 6, fonttools-r-rest 2,634 to 2,635, pypdf-r 1,474 to 1,703 and soupsieve-r 322 to 400.

Each is named under `passes` in a claim, and each claim gives its true reason in its `growth` text or a judge file's reason: 169's for the archives, 181's for fonttools, 166's and 170's for pypdf and 166's for soupsieve. The gather's upstream row went red on any count that differed from the accepted one, rise or fall, unless `news.reason(claims, "passes", node)` returned a reason. That function reads a `passes` claim's `fewer` alone. A claim fills `fewer` only for a fall, as its shape says (`context/changes/README.md`), so a rise always counted as unclaimed.

The rest of the judge lets a rise through. `scoreboard.compare` puts a rise in `more`, "reported, not `gained`". The acceptance from CI asks a reason only for a fall. `../progress/README.md` says acceptance keeps the higher value. 0.1.2's release had no release-tier count that rose, so the gather's rule first met one at 0.1.3 (INFERRED).

## Decisions

### 1. Fix the gather

The owner chose it with the AskUserQuestion tool on 2026-11-01: "Fix the gather". The workaround, a ledger file that copies each rise's reason into `fewer`, was not chosen: it writes a rise's reason into a field named for falls, and every later rise would need the same.

## Intent

The gather judges a pass count the way the ratchet and the acceptance already do. A rise is listed, never red. A fall needs its `fewer`. A lost pass is red whatever any count did.

## Design

In `tests/harness/gather.py`, G5's upstream block:

- When every system's count is a whole number above the accepted one, the row is listed under `GROWTH` with the kind `more`, on every event, and is never red.
- Any other difference is judged as before: listed on a pull request or after a merge into `dev`, and red on the release pull request unless a `passes` claim gives its `fewer`.
- A new function, `rise`, gives the text a listed rise is shown with. It is never a verdict. Among the claims that name the count under `passes`, it takes the first text that names the group: the claim's `growth`, or a judge file's reason whose path names the group. A claim's `growth` may be another row's (181's is the plain reactor's fuel), so a text that does not name the group is passed over. Failing that, it gives the first such claim's number, and with no claim, `more, needing no claim`.

On run 41359482215's claims at `50d2b5cb` (EXECUTED, `rise` over `news_claims() + release_ledger()`), the four rows show 169's zstd text, 181's `counted-clock.txt` reason, and 166's pin text twice.

### A rise never hides a lost pass

A group's count is a sum. One test could stop passing while two others start, and the count would still rise. Such a test is caught by the per-check ratchet, not by the count:

- A test that passed and now fails is outside every class of its group, so the group's own check (`test_upstream_suite`) fails; or it is in a class, so the class's check (`test_upstream_class`) fails on its new member. Either way a check accepted as a pass is now a fail, which G5 reds as `lost`, and the rise beside it is only listed. The unit row `test_a_rise_in_a_groups_count_never_hides_a_lost_pass` shows both.
- A test that passed and is now skipped or no longer collected is not a failure, and no check fails for it. The count is the only thing that sees it, and a rise from other tests can cover it. This change does not widen that: before it, a rise on a pull request or after a merge was already listed, and on the release pull request a `passes` claim with a `fewer` text cleared it. The group's `passed_digest` changes in that case, and the gather holds it equal between systems, not to the accepted value. Closing it would ratchet the passed set itself; it is out of scope here.

## Scope

**In:** G5's upstream pass-count row and the text a rise is listed with. **Out:** the shards' ratchet and the acceptance, which already treat a rise as `more`; the per-test passed set, above.

## Acceptance criteria

1. On the release pull request, a count that rose is listed and not red, with a claim's text that names the group or `more, needing no claim`. Unit: `test_a_rise_in_passes_on_a_release_pull_request_is_listed_not_red`, `test_a_rise_is_shown_with_the_text_that_names_its_group`.
2. On the release pull request, a count that fell is red unless a `passes` claim gives its `fewer`, and is listed with that reason when one does; a claim's `growth` does not clear a fall. Unit: `test_a_fall_in_passes_on_a_release_pull_request_needs_its_fewer`.
3. A rise in a group's count beside a lost pass of its class's check, or a failed group check, is red on the lost pass. Unit: `test_a_rise_in_a_groups_count_never_hides_a_lost_pass`.
4. `../progress/README.md`'s G5 paragraph states the rule.
5. `tests/unit/test_gather.py`, `tests/lint`, `tests/checks/test_rules.py` and the fast tier are green, and so is the pull request's `ci-status`. The release pull request's next gather is not red on the four rows.

## Landing notes

Built 2026-11-01, before its pull request and review.

- **Seen failing first.** Before the change to `gather.py`, the rise row and the lost-pass row failed: the rise was red, not listed (EXECUTED). The fall row pins behaviour the gather already had, so it passed before the change; it was seen failing against the wrong fix the diagnosis named as the alternative, `news.reason` reading `fewer or growth` for `passes`, which clears a fall with a growth text (EXECUTED). The display row was seen failing against a `rise` that takes any claim's `growth` (EXECUTED).
- **The judge hash.** `tests/harness/gather.py` and `tests/unit/test_gather.py` are judge files; the news file claims them under `[claim.judge]`.
- **The tag.** `uv run python release/version.py check --tag v0.1.3` on this branch, with this news file and 181's in `context/changes/`: see the pull request's description.

The pull request, its run and its review are to be written at the landing.
