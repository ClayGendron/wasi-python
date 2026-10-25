# How work is done in wasi_python today, as written and as practised

A reader agent's report (Claude Opus, 2026-10-25), read-only (`git log`, `gh run list`, `gh run view`, grep), for the memo beside this folder. Line numbers are for files as of `20fbf294`. Labels: EXECUTED (a git or gh read), READ (a file), INFERRED (reasoning).

## 1. The lifecycle of one specification (READ)

| # | Step | Artefact | CI run | Rule |
|---|---|---|---|---|
| 1 | Research answers the question first | `context/research/*.md` | — | constitution §5.1 |
| 2 | Draft the spec: Status, Kind, Decisions, criteria, "For the lane" (claim list, flags, wave kind, dry-run needs) | `context/specifications/NNN-*.md` | — | reviews/README.md:16-18 |
| 3 | Pre-build review, the author's Disposition, the reviewer's confirmation | `reviews/NNN-<slug>-spec-DATE.md` plus a Disposition section | — | constitution §5.6; AGENTS.md rules 8 and "Structure is reviewed" |
| 4 | Worktree and branch `spec/NNN-slug`; checks written first and seen failing | branch, `build/NNN/*.txt` | — | constitution §4.14; AGENTS.md rule 3 |
| 5 | Fast tier in a loop, in a slot the lane grants | `build/NNN/fast-tier*.txt` | — | AGENTS.md rule 3a |
| 6 | Push, dispatch `release.yml`, read the run back; only then is the spec "built" | run id in the landing notes | **1 or more branch runs** | AGENTS.md rule 2 |
| 7 | Landing notes and the builder's self-check | sections in the spec | — | reviews/README.md:5-24 |
| 8 | Build review; the reviewer reads the builder's run if on the exact commit, else dispatches its own | `reviews/NNN-...-build-DATE.md` | 0 or 1 | constitution §5.6; reviews/README.md:30 |
| 9 | Disposition; a code fix means a new commit, a new run, the reviewer's confirmation | spec section, review appendix | usually +1 | same |
| 10 | Rebase onto the wave's tip in the lane's order; name every conflict; fast tier | a landing-notes paragraph | none if "only rebased" | decisions.md:115; AGENTS.md rule 2 |
| 11 | Lane: rebuild the set in the main tree, take `build/lane.lock`, full normal tier with `--accept`, commit the acceptance alone, rules check, fast-forward main | `accepted.json` and a history line | — | constitution §5.7; progress/README.md:126-138 |
| 12 | Integration review by a fresh agent who reviewed none of the entries | `reviews/wave-NN-integration-DATE.md` | — | reviews/README.md:39 |
| 13 | Push `wave/NN` and dispatch the wave's dry run | record in `build/wave-NN/` | **1, shared by up to 5 specs** | progress/README.md:139 |
| 14 | A "landed" commit: Status lines, the roadmap's wave line, the CHANGELOG, README rows | one commit | — | reviews/README.md:20-22 |
| 15 | If a release-tier row changes, a claim block | `context/release-tier-claims.toml` | — | progress/README.md:114 |
| 16 | Before a tag: structural and security reviews, release acceptance, dry run on main, the tag's own run | two reviews | **2 or more, shared by the release** | AGENTS.md rule 6b; constitution §5.5 |

Verified against history (EXECUTED):

| | 113 (parallel-safe, runner code) | 067 (package suites; touches pins, scripts, patches) |
|---|---|---|
| Commits on main naming it | 17, from `97fb4380` (drafted 10-21 10:31) to `da665abe` (accepted 16:08), then `aa0ad05b` (landed 18:30) | 30, from `36149a0f` (10-20 01:42) to `1aa0eff7` (accepted 10-22 03:38), then fixes through `0d5ab383` |
| Spec size | 10,440 words | 19,707 words |
| Review files | 2 (5,000 and 2,951 words), each with a confirmation round: 4 rounds | 5 (prebuild, delta, build, delta-2, trap): 17,086 words |
| Shared reviews | wave-11 integration (4,942 words) and its addendum | wave-12 integration (5,478 words); the lane's sealed-leftovers fix review |
| Branch runs | 2: 39624848889 (2 attempts; a DNS failure) and 39644201639 | 3, all red: 39715865231 (a High), 39720564953 and 39732496724 (G7 only) |
| Wave dry run | 39667712127 (2 attempts; Savannah's outage) | none (the compressed path) |
| Release runs | — | main dry runs 39741960669 (red, networkx on Linux), 39764234616 (red, joblib on Linux), 39790261668 (green); tag 39957192055 |
| Local runs | 4 builder fast tiers; the lane's wave judge | 3 lane release acceptances of about 1.5 h each |

A typical parallel-safe spec (INFERRED): about 15 commits, 2 review files with 4 rounds, a fifth of an integration review, 2 branch runs plus a fifth of a wave dry run. Build-class or package: 3 to 5 review files, 3 or more branch runs, a lane rebuild. Across all branch runs, 94 runs on 35 `spec/*` branches: a mean of 2.69 and a median of 2 (EXECUTED).

## 2. The roles (READ)

**Builder:** one spec per builder, in its own worktree; fast tier and single node ids locally; dispatches branch runs; never accepts. **Reviewer:** a fresh agent given the spec and the diff, in a box of 25 minutes (parallel-safe) or 45 (build-class or package); may commit Low write-ins that touch only `context/`. **Lane:** one agent that serialises landings, main's only writer and the only one who accepts; sets the wave order, rebuilds, judges, accepts, fast-forwards, dispatches dry runs; in practice also fixes the judge (two lane-fix reviews on 2026-10-22); writes `handoff.md` and `decisions.md`; never tags. **Judge:** `uv run pytest` with the ratchet; refuses `--accept` in a linked worktree, on a dirty tree, or when HEAD moved. **Owner:** answers questions through the tool, makes every tag, approves loosened defaults.

The local budget (AGENTS.md rule 3a; decisions.md:75): while `build/lane.lock` exists, no other tier of the judge runs, the fast tier included, only single node ids; no container build; at most one native build. Otherwise at most one native build, one container build and one fast tier at once; never two full judges. On CI at most three release-workflow runs live at once (the plan is GitHub Pro). The release acceptance at `-n 6` only under the lock on an idle machine, else `-n 3`.

## 3. The rules that make each step mandatory (READ)

| Step | Source and kind | Stated reason |
|---|---|---|
| Research before spec, spec before build, review before land | Constitution §5.1, hard | "No open questions" (§5.2) |
| Fresh reviewer for every built change | §5.6; AGENTS.md rules 8 and "Nothing lands unreviewed" | "An author reads the change they meant to write"; ports lesson 11 |
| Pre-build review for imports/exports, artifact set, recipe, structural | §5.6, amended by question 108 | "a wrong design is caught before it is code" |
| Pre-build review for runner code | AGENTS.md rule 8 (owner, 2026-10-19) | review follows risk |
| A branch run before "built" | AGENTS.md rule 2 | the first measurement must not be the dry run on main (question 98) |
| No run after a pure rebase | owner, 2026-10-20 (decisions.md:115) | 3 to 5 runs per spec; queued runs took 105 minutes |
| Self-check list | reviews/README.md (owner, 2026-10-19) | a convention; an unchecked item is Low |
| Waves of up to 5, one integration review | §5.4, §5.7; decisions.md:67-79 | local full judges fall from three per landing to one per wave |
| Only the lane accepts; main moves by fast-forward | §4.14, §5.7; spec 029 | parallel work without lowering the bar |
| Ratchet: no lost pass, growth needs a reason | AGENTS.md rules 4 to 6 | ports lessons 3, 4, 6: agents solve the verifier |
| Release tier whole before a tag | §5.5 (owner, 2026-10-20) | "every test of every package we build" |
| Tag only after a green dry run | AGENTS.md rule 6b | 0.1.0a4's tag failed on Windows |
| Structural and security reviews before a release | §5.6; AGENTS.md | spec 108; the threat model |
| CHANGELOG and roadmap lines | reviews/README.md:20-22 | a convention |

## 4. Throughput (EXECUTED)

| Day | Commits on main | Specs landed | Release runs (success/failure/cancelled) | Median run (min) |
|---|---|---|---|---|
| 10-16 | 29 | 4 | 4 (1/3/0) | 14 |
| 10-17 | 194 | 26 | 30 (20/8/2) | 17 |
| 10-18 | 360 | 26 | 16 (12/3/1) | 22 |
| 10-19 | 255 | 23 | 31 (14/14/3) | 24 |
| 10-20 | 241 | 11 | 50 (14/34/2) | 42 |
| 10-21 | 148 | 17 | 34 (8/22/4) | 55 |
| 10-22 | 30 | 2, plus wave 13's 4 (accepted 10-23) | 8 (1/7/0) | 41 |
| 10-23 | 4 | — | 4 (2/2/0) | 81 |

Specs landed alone through 10-19; then 13 waves (01 on 10-19 to 13 on 10-23), the structural chain (103 to 109, PR #1) and one batch (089/083). 13 integration review files; 2 lane fix reviews; 258 review files in all; spec words about 910k, review words about 1.0M. Of 1,261 commits on main since 10-16: 812 (64%) touch only `context/`, `docs/`, README, CHANGELOG or AGENTS.md; 376 (30%) touch `src/`, `tests/`, `scripts/`, `recipes/`, `release/`, `.github/` or `downloads/`; 70 (6%) are acceptance commits touching only `context/progress/`. Runs by branch kind (177): `spec/*` 94 (20 green, 67 red, 7 cancelled); `main` 54; `wave/*` 17; tags 9. The most runs on one spec branch: 063 had 9; 101 and 102 had 7 each; 065 had 6.

## 5. The 2026-10-22 process advice, and what became of it (READ)

Section 1's items for that night (release acceptance at `-n 6`; wave 12's acceptance as the release acceptance; dispatch first, write second) were instituted at `c0d3a212` and used at `1aa0eff7`, `deb18923`, `edb88a1b` and `92feb015`. Section 2's five specifications, 117 (red means broken), 118 (a news file per spec), 119 (shards by changed paths), 120 (a light branch run and the full run once per wave) and 121 (the pre-tag dry run beside the release acceptance), are reserved in roadmap.md and **none is built**: no file exists for 115 to 121 (the listing jumps from 114 to 122); `release.yml` still has `cancel-in-progress: false` and no `pull_request` trigger. The later items (accepting from CI's record, result reuse by input hash, one review per parallel-safe spec, a fuel budget on the normal tier, a nightly release tier) are each the owner's call and none is decided. Kept: Windows on every code change, one full three-system run per wave, the ratchet at acceptance, a fresh reader for every spec. Stale text: AGENTS.md rules 3a and 6a still say "Until spec 092 … lands, one reviewer per wave also keeps a local `-n 3` record"; 092 landed in wave 03 (`44540cbd`).

## 6. Every full run the process asks for (READ)

Local: builder and reviewer never run a full judge (fast tier, about 8 minutes by 113's notes, and node ids); the lane runs one full normal-tier `--accept` per wave after one rebuild; per release, a normal-tier run without `--accept` then the release acceptance (1 h 23 min to 1 h 32 min). GitHub: the builder's branch run, one or more (each later code change needs another, because the reviewer reads only a run on the exact commit); the reviewer's own run when the commit differs; the wave dry run on `wave/NN`; a release-tier branch run only when a spec changes the release-tier job; the dry run on main's exact commit with the release tier before a tag (any commit after it beyond `context/`, CHANGELOG or README needs a new one); the tag's own run. Net: about 2.4 to 2.7 full three-system runs per spec plus a share of the wave and release runs; locally one full judge per wave and one or more release acceptances per release.

## 7. Rules that came from incidents (READ)

| Incident | Rule it produced |
|---|---|
| 0.1.0a4's tag run failed on Windows, 10-18 | Rule 6b: tag only what a dry run passed (`c7b7f26a`) |
| 14 of 24 real red runs were Windows alone | Windows legs on every branch run; the self-check's Windows item |
| Agents gaming verifiers in the precedent ports | Rules 4 to 6: no weakened judge, the ratchet, no lost pass |
| ts-rust's stalled port | Rule 7: two strikes, then write it down |
| A red acceptance could reach main (question 70, `0384ca54`) | Progress step 5; the `reset --soft` exception in §4.14 |
| The machine saturated: a `-n 3` accept took 17 minutes against 10 quiet | `build/lane.lock` and the local budget (`302df181`) |
| Runs queued 105 minutes; 3 to 5 runs per spec | The reviewer reads the builder's run; no run after a rebase; spec 101 |
| Finder `.DS_Store` voided wave 08's accept, 10-20 | Specs 089, 090, 097; the "clone outside HOME" workaround |
| Disk full in wave 07's first accept | `df` before accepts |
| numpy-core fuel moved at every build-class landing | Spec 091, a fuel fact |
| Polling Savannah during its outage, 10-21 | No probing upstream hosts |
| Tier placement re-asked many times | "Never re-asked" |
| 315 spec citations in `src/` | "Code speaks for itself"; specs 107, 109, 112 |
| 078's Windows-only row red after landing | "A red dry run on main is fixed forward" |
| 11 of 067's groups had never passed | A reserved check that every group passes (not built) |
| The sealed-scan race at `-n 6`; joblib and networkx failing on Linux | Lane judge fixes, each with a fresh review |
| Docker Desktop stopped | Question 109: the lane restarts it |

One line: today one spec costs about two branch runs, two to five review files with confirmation rounds, a share of a wave's integration review, dry run and lane judge, and about fifteen to thirty commits, most of them context-only; every step is tied to a constitution clause, an owner decision or a past incident, and the 117 to 121 relief is reserved, not built.
