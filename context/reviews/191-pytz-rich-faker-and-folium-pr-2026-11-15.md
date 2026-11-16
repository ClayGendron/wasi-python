# Review of 191 — pytz, rich, Faker and folium

- **Date:** 2026-11-15
- **Reviewer:** an agent (Claude), a fresh sub-agent of https://claude.ai/code/session_01BD1pVHiZoxnwRv6JCqJKeC; not the author
- **Reviewed:** `origin/dev` (`7deb6043`) to `a4c03b0a` on `spec/191-pure-python-packages`: the pushed head `64b9002b` and the local commit `a4c03b0a` above it. Box: 45 minutes (a package specification); the box closed with the macOS legs and the gather still running.
- **Run:** 43772062248, on `64b9002b`. Read: every finished job's result; the logs of the three red legs (Linux and Windows `own-guest-b`, Linux `upstream-pure-smoke-a`), `review`, `plan`, and Linux `own-guest-d`. Windows: all twelve legs finished; eleven green, `own-guest-b` red. **Not yet read:** macOS `own-embedding`, `-b`, `own-guest-a`, `-b`, `-c`, `own-hostile-b`, `own-rest` (queued or running at 23:33 UTC), the gather's summary and `ci-status`, which had not started. No run is on `a4c03b0a`, which changes `scripts/assemble_artifacts.py`.
- **Re-ran:** `uv run pytest tests/unit/test_artifact_rules.py tests/unit/test_packages.py -q` → 115 passed, exit 0; `uv run pytest tests/lint -q` → 14 passed, exit 0; `pure_notice_parts(<the pinned Pygments wheel>, "pygments")` → four parts, the two new ones at `terminal256.py:7-9` (165 B) and `configs.py:1130` (55 B), exit 0; a scratch probe of Faker 40.54.0 seeded 4321, once on today's clock and once with `datetime.now` fixed at 2026-01-01 (the judge's guest clock, `tests/harness/guest.py:45`) → one line differs: `mina_2023` against `mina_2022`, the CI failure exactly (EXECUTED).

## Acceptance criteria against evidence
1. The owner's answers recorded first; the sweep in the landing notes — met: `decisions.md` holds choices 1 to 4 and "Approve all three" (READ). §4.12 lacks the three (Low 5).
2. Every pin's SHA-256 is PyPI's — met for the pins built here: the build job built from them and `release/set_key.py verify` passed (READ, job result). Tag archives: not pinned, deferred to 193.
3. Decision 2's numbers from a full run, `test_pytz_first_zone_is_bounded` passing — partly met: the plan ran full because `release.yml` changed (READ, `release/ci_plan.py:524-526`); the check passed on Linux, Windows and macOS `own-guest-d` (READ, job results). The other three bounds are not recorded (Medium 3). The two rewritten checks pass in the guest (the embedding and `own-guest-d` legs green, READ), which settles the landing notes' natively read pyarrow count; neither is claimed (Medium 4).
4. Growth named, claimed and classified from the run — not met: tqdm's three classes grew (Medium 2).
5. The zip's names; folium's and branca's trees their sdists plus patches — partly met: the build job's zero-patch step requires 43 and the job is green (READ, `release.yml:383-394` and the result; its log not read). The zip's names wait for the gather.
6. The four jobs match native — not met: `fake_data` fails on Linux and Windows (High 1); `time_zones`, `terminal_text` and `web_maps` pass (READ).
7. The guest checks seen failing first — not met as written: none was run on a set without its package (the landing notes say so; Low 1). All pass on Linux and Windows.
8. The nine families — deferred to 193 as `later` gaps with their closer (READ, `packages.toml`); no smoke group read shows a module loaded outside its family (READ, the smoke legs).
9. `SMOKE_TOTAL_BOUND` — unchanged, since no group joins; consistent with 8.
10. Bytes and fuel per pull request — not met yet (Medium 3).
11. Fast tier, lint, `ci-status` — `quick` green; `ci-status` red until the above.

## Findings, most severe first
1. **High: `fake_data` draws a year from the clock, so its golden cannot match the guest** (`tests/jobs/fake_data.py:24-25`, `tests/jobs/fake_data.expected:9`). ru_RU's `user_name_formats` include `{{first_name}}_{{year}}`, and `year()` is `date_time()`, drawn between 1970 and now (Faker's `providers/date_time/__init__.py:1884-1900`, `:2532-2536`, READ); ru_RU's `email()` goes through the same formats. The oracle ran on 2026-11-15, the guest runs at 2026-01-01. Failure: `test_fake_data_job_matches_native` is red on Linux and Windows (`mina_2023` expected, `mina_2022` got), and natively the golden drifts with the calendar, so `regen.py --check` breaks too. The job's docstring and Decision 9 say no value is relative to today. Fix: draw nothing that reaches `year()` (drop ru_RU's `user_name()` and `email()`, or give the job a locale and calls with no year format, checked by reading every chosen locale's `user_name_formats` and `email_formats`), regenerate with the oracle, and say in the job why. Never fix it by moving the guest's clock, loosening `jobs.compare`, or writing the guest's value into the golden.
2. **Medium: rich's arrival grew tqdm's smoke classes, unclassified** (`tests/upstream/tqdm.toml:41`, `:65`, `:73`). Failure: Linux `upstream-pure-smoke-a` is red: `tqdm-smoke-no-asyncio-loop-error` 10 → 14 findings, `-no-threads-error` 98 → 100, `-no-threads` 116 → 118. Decision 3 and criterion 4 ask the rich pull request to name, claim and classify these. Fix: read each new node id in the run's record (`failed-record-linux-upstream-pure-smoke-a-1`), confirm each is the class's platform limit (the asyncio four in particular: say why rich adds them), update the class lists and their gaps, and claim each changed verdict-bearing file. This is the classification the specification asks for, not a weakening, only if every new id is read.
3. **Medium: pytz's line is held by one of its four bounds, and no figure of Decision 10 is recorded** (`context/specifications/191-pytz-rich-faker-and-folium.md:298`, `:307`). The first zone is under 1 G (the check passed); `import pandas` (+2%), a snapshot start (+1%) and the zip (0.6 MB) are not read from the run. Evidence that closes it: the gather's figures on darwin-arm64, recorded in the landing notes with the run id; pytz cut if one is past its bound.
4. **Medium: the judge changes are not all claimed** (`context/changes/191-pytz-rich-faker-and-folium.md:50-51`). `[claim.judge]` names only `packages.toml`. `context/release-claims/191-pytz-rich-faker-and-folium.toml` is verdict-bearing (`tests/harness/paths.py:365-374`) and unclaimed; 188 claimed its own. Decision 2 and criterion 3 ask for the two rewritten checks under `[claim.judge]` with their reasons. Fix: add those three lines, and the files Finding 2's fix touches.
5. **Low: §4.12 does not list the sweep's three** (`context/constitution.md:48`, and the Status line). Plotly's sweep items were written in. Text, after "under plotly's MIT licence.": "Approved 2026-11-15, after 191's licence sweep: Pygments' terminal formatter's colour routines, adapted from xterm256-conv (no stated terms, under Pygments' BSD-2-Clause notice), and its TOML lexer's patterns, adapted from CPython's tomllib (PSF); Faker's randomColor (CC0), its `person/hu_HU` data (public domain) and its `date_time/th_TH` code (public domain or CC0)." The Status line gains "and the three its sweep found ("Approve all three")".
6. **Low: the self-check.** Its first two boxes are unchecked. Fix: read this run's Windows legs and tick the second; for the first, see each guest check fail once on `dev`'s cached set by node id, or say in the description that none was.
7. **Low: the description says the second carried patch is Faker's reseed.** It is branca's table read; Faker's reseed is a recipe change. Fix the "After:" paragraph.
8. **Low: the news file's Upgrading entry names pytz alone** (`context/changes/191-pytz-rich-faker-and-folium.md:12-14`). The Design asks it for rich, Pygments, Faker and folium on the import path too. Fix: name all five.
9. **Low: `grows = ["tests/checks/*"]` claims every check** (`:47`). Fix: narrow it to the gather's `GROWTH` rows once read.

## Constitution checks
- §4.1: two patches, each with its draft under `context/upstream/patches/`, named in the news file, counted in the README (35) and `release.yml` (43); the branca stand-in and the reseed are recipe files. Holds.
- §4.2: nine pins and the licence-only files, matched; nothing unpacked into the system. Holds.
- §4.12: every notice approved; the sweep's three approved in `decisions.md`, not yet in §4.12 (Low 5).
- §5.6 and the judge: the pre-build review lands at round 1. The branch does not weaken the judge: `PANDAS_FOLDERS` and the stub follow pytz's arrival and pass in the guest, `DRAWS` and the guard only add, no cap, gap digest or bound moves, and the nine `later` entries name their closer. Findings 1 and 2 must keep it so.
- `.github/`: `release.yml` changes only the zero-patch count, 41 → 43, in three jobs (the build job and both rebuilds); no permission, token or selection changes. Nothing under `release/` changes. Nothing under `src/` changes; not structural.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)
1. —
2. —
3. —
4. —
5. —
6. —
7. —
8. —
9. —

## Round 1 verdict (on `a4c03b0a`; the verdict of round 2, below, replaces it)
Does not land yet: the High (`fake_data`'s clock-drawn year, red on Linux and Windows) and Mediums 2 to 4 (tqdm's unclassified classes, pytz's three unread bounds with the run's figures, and the unclaimed judge files) stand, and the macOS legs, the gather and a run on `a4c03b0a` are still to read.

## Round 2

- **Date:** 2026-11-16
- **Reviewer:** an agent (Claude), a fresh sub-agent of https://claude.ai/code/session_01BD1pVHiZoxnwRv6JCqJKeC; not the author
- **Reviewed:** `a4c03b0a..9cff04f8`, the round's one fix commit (the job and its golden, three tqdm lists, three gaps, the news file, §4.12, the landing notes; trailer Claude Opus 5.5), and `a4c03b0a`, which had no run under it in round 1. Box: 45 minutes; finished inside it.
- **Run:** 43779692842 on `9cff04f8` (READ): every judge leg green, 31 Linux, 12 Windows, 14 macOS; the build job built the set; the gather green, `0 fail`; `review` and `ci-status` red, and both logs give one refusal, this file's absence.
- **Re-ran** (EXECUTED):
  - `uv run python release/precheck.py` → exit 1 on one test, `tests/unit/test_runner_grants.py::test_the_walk_judges_links` (it needs non-root; allowed): the unit suite 3,654 passed, 104 skipped; ruff, mypy, the rules checks (143 passed, 5 skipped), their budget and lint (14 passed) ok; the plan waits on this file. This covers the two unit files the branch touches.
  - `uv run python tests/jobs/regen.py --check --job fake_data --job time_zones --job terminal_text --job web_maps` → four `reproduces`, exit 0.
  - A scratch probe: `fake_data.py` on the pinned Faker 40.54.0 wheel, `datetime.now` fixed at 2026-01-01 and at 2031-01-01, hash seed 0 → the golden byte for byte, both times. The round-1 job (`64b9002b`) under the same two clocks differs from its golden both times, so the probe sees the fault.
  - `scan.digest` of each tqdm list → 12 `ba273df75009`, 99 `a1fb56cd7644`, 116 `c2531945eb68`: the three gaps' `match` exactly.

### Round 1's findings
1. **High, `fake_data`'s year** — closed. ru_RU draws no `email()` or `user_name()`; the job's docstring says why. Of the other locales, only `ja_JP` has its own `user_name_formats`, with no year; `en_US`, `de_DE` and `fr_FR` take the base provider's four, none with a year (READ, the wheel's `providers/internet/`). The fixed-clock probe and `--check` pass (EXECUTED); the guest checks are green on all three systems (READ).
2. **Medium, tqdm's classes** — closed. The three lists and gaps follow the guest, and each changed file has its reason under `[claim.judge]`. Linux `upstream-pure-smoke-a`: 31 passed, 29 xfailed, 0 failed (READ), so every class matched its gap exactly. The asyncio pair depends on when the collector runs. The guest is deterministic, so it holds until the allocations move again (INFERRED).
3. **Medium, pytz's bounds** — closed. The landing notes' table holds all four, with verdicts. Checked against 43779692842 (READ): the gather's rows for `door[plain]` (5,042,005,894 → 5,086,106,329), `test_guest_runs_here[snapshot]` and `[plain]`, and `entropy[snapshot]` match the notes; the build job's step 70 prints 8,698 pyc, 1,659 data files and 72,339,631 bytes; `accepted.json` holds 65,481,316 bytes and `import pandas` at 5,028,776,029. **Not checked:** the first zone's own figure (it is in a record artifact, and downloads are refused); the two `import pandas` nodes and the zip check's bytes row (the gather prints at most five growths a leg, `tests/harness/gather.py:455`, and none of the three is among them); and the scratch figure for pytz alone (+0.70% on a snapshot start), which needs a set and wizer.
4. **Medium, the claims** — closed. Every verdict-bearing file the branch changes (`tests/harness/paths.py`'s `VERDICT_BEARING`: `known_gaps.toml`, `packages.toml`, the three lists, the ledger file) has its line, and the two rewritten checks too.
5. **Low, §4.12** — closed: the three are in §4.12 and the Status line (READ).
6. **Low, the self-check** — half open. The first box's parenthesis is a written answer. The second is still unticked, with "No run yet on this head"; 43779692842's twelve Windows legs are green.
7. **Low, "Faker reseeds" as a carried patch** — open: the description's "After:" still says so.
8. **Low, Upgrading** — closed: it names all five.
9. **Low, `grows = ["tests/checks/*"]`** — left as it is, by the author's choice; no effect on the verdict.

### Findings of round 2
1. **Low: the landing notes do not name the green run, and one paragraph is stale** (`context/specifications/191-pytz-rich-faker-and-folium.md:318`). AGENTS.md, step 6, asks for the run's id. "Not machine-checked here, and waiting for a built set" lists checks that 43779692842 ran. Fix: replace that paragraph with "**Judged by run 43779692842** (READ, on `9cff04f8`): every judge leg is green on three systems (31 Linux, 12 Windows, 14 macOS), on a set its build job built (step 70: 8,698 pyc, 1,659 data files, 72,339,631 bytes; 43 zero-patch trees). The gather is green, each growth with its claim. So the guest checks named above, the four jobs' guest runs, the Faker row of the refresh check and the new pandas, matplotlib and tqdm cases passed, under their caps. Still not read: the first zone's own figure, which is in the leg's record (the check asserts the bound)." It touches only `context/`.
2. **Low: the description and the draft state.** "For the owner before merge" asks about three items the owner has approved (`decisions.md`, §4.12), and the pull request is still a draft, which `gh pr merge` refuses. Fix: drop that paragraph or say they were approved on 2026-11-15; with round 1's Lows 6 and 7, tick the Windows box, write "Two carried patches: folium no longer imports requests, and branca reads its colour tables through the package's loader, so it imports from the zip; Faker reseeds on each call's refresh, a recipe change"; then mark the pull request ready.

Outside this pull request (INFERRED, no finding): the gather shows `test_binary_is_a_core_wasm_module[snapshot]`'s growth, 109,640,952 → 110,411,202 bytes, with 188's reason, since a pull request's gather reads every news file's claims. The acceptance reads only the news files merged since 7deb6043, so 191's own glob claims it.

### Constitution checks, round 2
- §4.1, §4.2: no change in the round. `release.yml`'s count of 43 is read on this run: "43 passed" (READ).
- The judge: the fix commit edits a golden, three class lists and three gaps. Each follows the guest (the fixed-clock probe; the digests) and is claimed. None loosens a compare, a cap or a bound.
- `a4c03b0a`: `scripts/assemble_artifacts.py` adds Pygments' two notice parts; the build job's `LICENSE` line reads "97 component licences" on this run (READ). Nothing under `.github/`, `release/` or `src/` changes in the round. §7: nothing tripped.

## Verdict
Lands on `9cff04f8`: round 1's High and three Mediums are fixed and read. `fake_data` draws no year and reproduces its golden under any fixed clock. tqdm's three classes match the guest exactly. pytz's four bounds are recorded, and every figure I could read matches run 43779692842. Every verdict-bearing file is claimed. That run is green on every judge leg of three systems. The open Lows (round 1's 6 and 7, this round's 1 and 2) are write-ins to the description and the landing notes, to make before the merge.
