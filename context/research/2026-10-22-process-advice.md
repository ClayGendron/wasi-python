# Process advice: tonight's path to 0.1.0, and what to change after it

- **Status:** advice, 2026-10-22, about 02:00 UTC. An outside advisor's recommendation on the
  memo `2026-10-22-how-other-projects-test-and-release.md` (options A to K). Nothing but this file
  was written. No judge, build or CI run was started.
- **Owner:** Clay Gendron
- **Stands on:** the memo; AGENTS.md rules 2 to 8; constitution §4.14, §5.5 to §5.7;
  `progress/README.md`; `decisions.md` ("The path to 0.1.0 is compressed", "Fast tests and slow
  tests"); `handoff.md`.
- **Evidence labels:** EXECUTED (`gh run list`, `git diff --stat`, `sysctl`, `df`, `uptime`,
  read-only tonight), READ (a cited file), INFERRED (reasoning).

## 1. Tonight, before 0.1.0

The remaining path, READ from the handoff: wave 12's integration (a 16-minute rebuild, a 20-minute
`-n 3` judge, a fresh review), the version bump, the release acceptance at `-n 3` (3 to 5 hours),
the dry run on main with the release tier (2 to 3 hours), the tag. The release tier is about 151 T
(102's 8.37, 095's 86.22, 067's 56 and more; READ). At 0.154 to 0.170 s per G (READ, spec 102,
Decision 11) that is 6.5 to 7 hours of guest time, which `-n 3` divides by three. INFERRED.

Ranked by hours saved per unit of risk. Each names the rule text that changes.

**1. Run the release acceptance at `-n 6`.** Fuel is an instruction count: spec 052 proved a
parallel run gives the serial verdict, every status, byte and pass count equal and fuel "far inside
the ratchet's 0.01%" (READ, progress README, "Several cores"). `meta.workers` is recorded and never
compared. Rule 3a already allows `-n 6` for both tiers; rule 6b and the progress README say `-n 3`
only because another agent's judge may be running, and under `build/lane.lock` nothing else runs.
*Saving:* 1.5 to 2.5 hours (INFERRED: the guest time over six workers instead of three, plus the
normal tier and the longest group's tail). *Risk:* memory. The normal tier at `-n 6` peaked at 8.4 to
9.8 GiB (READ, spec 052); a release group is packed to 725 G and a wasm32 guest can reach 4 GiB, so
six guests could want 24 GiB of the machine's 32 GiB (EXECUTED, `sysctl`). A worker that dies is a
named `fail` and ends the run: visible, never silent, but the run is lost. *Mitigation:* an idle
machine (the load average was 41.8 on 10 cores at 01:50 UTC, EXECUTED: the measuring agents), Docker
Desktop idle; watch RSS for ten minutes and restart at `-n 4` past 24 GiB. *Text:* AGENTS.md rule 6b, "`uv run pytest -n 3 --tier release
--accept …`" becomes "`-n 6` while `build/lane.lock` is held and nothing else runs, else `-n 3`";
progress README, "The release acceptance" and step 3, the same clause. Constitution §5.5 names no
core count. The same clause takes the wave's normal-tier judge from 20 minutes to about 10.

**2. Make wave 12's acceptance the release acceptance.** Put the version bump on the wave's tip as the
lane's commit, run the normal tier once at `-n 6` without `--accept` (about 10 minutes: a lost pass
or a red smoke group must not cost a three-hour run), then one `--tier release --accept "Wave 12 and
release 0.1.0: …"` run with every entry's reasons. A release acceptance judges both tiers (READ, spec
102), so it meets §5.7's "judges the tip's normal tier once", and §5.5's "on main's tip" because the
acceptance commit's first parent is the tip main fast-forwards to. The integration review reads during
the run, as the compressed path lets the build review do. *Saving:* one 20-minute judge, one
accept-check-fast-forward cycle and the wait for the review: about an hour. INFERRED. *Risk:* the
review finds a code-level defect mid-run and the run's hours are lost. Wave 11's integration review
found Lows only, all in `context/` (READ); the 10-minute gate removes the normal-tier reds from the
risk. *Text:* progress README, "The release acceptance, before a tag, on main's tip,
after the last wave" gains "or as the last wave's acceptance, when its tip carries the version bump";
rule 6b's first sentence, the same. Record it in `decisions.md` as the lane's reading for the owner to
confirm; if the owner reads §5.5 otherwise, the cost is a repeat, not a weaker release.

**3. Dispatch first, write second.** The moment the acceptance commit is on main, push and dispatch the
dry run; write the landing notes, the delta reads and the CHANGELOG while it runs. Rule 6b already
allows it: context-only commits may follow the dry run when the fast tier passes on the commit tagged.
Hold every other dispatch until the dry run's jobs have started, so its legs do not queue behind a
branch run (rule 3a's three-run limit; queued runs took 105 minutes, READ, decisions 2026-10-20).
*Saving:* 30 to 60 minutes. *Risk:* none. *Text:* none; sequencing.

**4. Overlap what the rules already allow.** The lane's rebuild starts the moment the wave's tip exists,
beside the last entry's fast tier in its worktree and the integration reviewer's first read. The rebuild
cannot be skipped: 067 changes `downloads/SHA256SUMS`, `scripts/00_download.sh` and `recipes/patches/`
(EXECUTED, `git diff --stat` from its merge base), so spec 101's set key moves even though `python.wasm`
should not; the rebuild proves it did not (expect `1556bbd5`). *Saving:* 15 to 30 minutes.

**5. A quiet tree now.** `--accept` refuses any tracked change outside `context/progress/`. The main
tree has `context/prior_art/README.md` modified and the new memo untracked (EXECUTED); commit them
before the lane needs the tree. `test_app/` is outside the judged folders. Run `df` before the long
run: 78 GiB free (EXECUTED) and the two specs' source trees are large.

**What must not be cut.** 067's one branch run: 14 of the memo's 24 real red runs were Windows alone,
067 changes harness code that runs there, and the dry run would find the same defect two hours later at
ten times the price. The two fresh reviews. The release tier whole (the owner's rule). The dry run on
main's exact commit, and the tag's own run. The sameness line against `release-tier-claims.toml`.

**The honest clock.** 095's run 39705963592 began 01:29 UTC (EXECUTED). 067 stood at sympy 113 of 167
groups when paused, with ten steps and a one-hour branch run left (READ, handoff). INFERRED: 067 is
built and reviewed by 05:00 to 07:00 UTC, wave 12 accepts by 07:00 to 09:00, the dry run ends by 10:00
to 12:00 UTC, and the tag's own run takes 2 to 3 hours more. With items 1 to 5 the owner wakes to the
release acceptance green or nearly so and the dry run in flight, not to a tag. The one lever that moves
the clock by hours is the owner's: whether 067 stays in 0.1.0 (their decision of 2026-10-20). The lane
proceeds on that decision and asks at 06:00 Eastern through the tool.

## 2. After 0.1.0, as specifications

Ranked by saving per unit of risk, the memo's letters in brackets; the order is the dependency order.

**1. Red means broken [D, G].** The gather reads the branch's claim block and passes when every `GREW`
row is claimed; growth on a branch run is advisory and the gate stays at acceptance (rule 5 keeps its
substance: no pass lost, growth accepted with a reason). A short first job (ruff, units, rules) gates
the build and the 40 shards; `cancel-in-progress: true` for a newer push of one branch. *Saving:* 38 of
62 red runs were red by design and each cost an agent's read; a run that dies on a rules check costs
minutes, not about 250 runner-minutes. *Keeps safe:* the ratchet at acceptance. *Depends on:* nothing;
everything below needs CI's colour to mean something first.

**2. One news file per specification [H].** `context/changes/<NNN>.md`, assembled into CHANGELOG at
release; README's package rows the same way. *Saving:* about half the 38 named conflicts since
2026-10-19 and the rebases they cause (spec 045: 22, 13, then 6 hunks). *Risk:* none.

**3. Shards by changed paths on branch runs [A].** `context/`-only skips the guest; a change outside
`scripts/`, `recipes/`, `downloads/` and the upstream TOMLs skips the upstream shards; Windows `own-*`
stays for any `src/` or `tests/` change. *Saving:* 40 to 60% of runner time, 15 to 30 minutes of wall
time on most runs. *Keeps safe:* the wave's and pre-tag dry runs still run everything. *Risk:* a missed
dependency; the integration run is the net. *Depends on:* 1.

**4. A light branch run, the full run once at the wave [B].** *Saving:* about 1.4 of 2.4 full runs per
specification, about 35 runner-hours a day. *Risk:* a failure surfaces at the wave and ejects an entry
later; Rust pays this for one full run per merge. *Depends on:* 1 and 3.

**5. The pre-tag dry run beside the release acceptance.** The gather's G7 accepts an acceptance commit
pushed after the run began when its first parent is the judged commit. *Saving:* 2 to 4 hours per
release. *Risk:* small; the tag still needs both green. *Depends on:* nothing.

**6. The lane accepts from the dry run's record [C].** Spec 092 reads one already. *Saving:* the lane's
judge and the machine's slot per wave. *Risk:* CI's macOS fuel may differ from the lane's; new judge
code. The owner said "not yet, revisit after three G5-clean waves". *Depends on:* that, then 1.

**7. Result reuse by input hash [E].** *Saving:* nearly a whole run for a context-only change. *Risk:*
an undeclared input, Bazel's own warning; hides flakiness. *Depends on:* 3 and 4, which take most of
the saving at less risk.

**8. One review per parallel-safe specification [I]**: build and integration review merged; the
pre-build review kept for §5.6's classes. *Saving:* agent time and prose, not CI. *Risk:* reviews have
caught real defects (113's M1); keep one fresh reader per spec always.

**9. A fuel budget on the normal tier [K]**, so the fast tier cannot grow by accident. Cheap, small.

**10. A scheduled release-tier run on main [J].** It finds the five-hour surprise a day after the wave
that caused it. It conflicts with the owner's rule that slow tests run only to publish, so it is the
owner's call; the case is that a nightly run on main is the publishing check, run early.

Not recommended: GitHub's merge queue. The lane is the queue and waves are rollups; it would add a
gate without removing one.

## 3. What to keep

- **Windows on CI for every code change.** 14 of 24 real red runs were Windows alone; 0.1.0a4's tag
  failed only there. A wasm runtime fails in platform ways.
- **One full three-system run at one integration point.** Three wave dry runs were red on a real
  failure that branches and the local judge had missed.
- **The exact ratchet at acceptance.** Agents solve what the verifier asks (the ports memo, lesson 1).
  Counting by name, refusing a lost pass and ratcheting fuel at 1e-4 is what converged. Make growth
  advisory on branches, never at acceptance.
- **A fresh reader for every specification.** Agent-written code needs one reviewer who did not write
  it. Cut rounds, not readers.
- **The release tier whole before a tag, pinned inputs, and the lane as main's only writer.** None of
  these cost CI hours.

## 4. For the owner

The slow part is not the tests. It is running every test, on three systems, about three times per
change, and then having an agent read a run that is red on purpose. Tonight the lane can run the
release acceptance on six cores instead of three, fold wave 12's acceptance into it, and dispatch the
dry run before writing the notes; that saves two to three hours and weakens nothing. You will still
wake to the dry run in flight, not a tag, because 067 is on the critical path. After 0.1.0, make red
mean broken, give each change its own news file, run a light set on branches and the full set once at
the wave, and let the pre-tag dry run go beside the local release acceptance. Keep Windows on every
code change, one full run per wave, the ratchet at acceptance and one fresh reviewer per change: those
are the parts that have caught real defects.

## One line

Run the release acceptance at `-n 6` as wave 12's acceptance and dispatch the dry run before the
prose; after 0.1.0, make CI's colour mean something, then a light set per branch and the full set once
per wave, and keep Windows, the ratchet and the fresh reviewer.
