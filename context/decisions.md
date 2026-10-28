# The owner's decisions

The owner's answers and decisions, newest first. Until 2026-10-22 questions were asked in `questions-for-the-owner.md`, which is in git history (deleted by spec 122); a decision only the owner can make is now asked through the owner's channel and recorded here once answered. Each entry keeps its question number where it had one, the date, the owner's answer, and what follows from it. A decision that changes the constitution is also recorded there (`constitution.md`, its Status line); this file is the record for the rest.

The owner went through every open question on 2026-10-17. Decisions that change the constitution are recorded there (§3, §4.1, §4.4, §4.12, §4.15).

### Spec 126 is dropped (2026-10-25)

Asked by the orchestrating agent after 127's research measured the module drop at 22 ms under wasmtime 50 with native unwind information left on. What 126 would still buy is about 10 MB off every cached `.cwasm` and a drop of 2 to 12 ms instead of 22. **Answered 2026-10-25:** drop it. 127 gives the win that mattered; the leftover stays a benchmark fact in `research/2026-10-24-native-unwind-information-and-the-module-drop.md`. 126's file is marked superseded and its roadmap line retired.

### The accept job's identity is a deploy key the agent generates (2026-10-25)

Asked by the orchestrating agent for spec 138's accept job, which pushes one acceptance commit to `dev` past its ruleset. **Answered 2026-10-25:** generate and install it. The agent makes an ed25519 key pair, adds the public half as a write deploy key on the repository, stores the private half as a secret in the `accept` environment, names the deploy key as the bypass actor of `dev`'s ruleset, and records the key's fingerprint in 138's landing notes. The private key never enters the repository. A GitHub App remains a later choice for the owner.

### The one-review rule is held by `ci-status`, not by a GitHub approval (2026-10-25)

Asked by the orchestrating agent from 138's pre-build review (High 2): GitHub never lets a pull request's author approve it, and every agent acts through the owner's one account, so a ruleset cannot require an approving review here. **Answered 2026-10-25:** `ci-status` checks for a review file. `dev`'s ruleset requires `ci-status` alone and no approvals; the decision job fails a pull request that touches more than documentation unless its branch carries `reviews/NNN-<slug>-pr-YYYY-MM-DD.md` whose Reviewer line is not the author's and whose verdict says it lands. This is a process guard, not an identity guard, and the specification says so; a second identity (a reviewer GitHub App) is a later choice for the owner.

### The constitution's amendments for the new process cover §4.13, §4.14, §5.4, §5.5 and §7 as well (2026-10-25)

Asked by the orchestrating agent from 138's pre-build review (Medium 8 and Medium 11): the recorded agreement of 2026-10-25 named §5.6 and §5.7, while the lane and the waves are also written into §4.13 (pytest green before any landing), §4.14 (branches and worktrees), §5.4 (landings one at a time or in waves), §5.5 (the release acceptance by the lane) and §7 (the never-do list's branch bullet). **Answered 2026-10-25:** yes, all of them, with the exact texts in spec 138's Decision 10. The constitution's Status line records this decision when the texts are written in.

### The development process moves to pull requests into `dev` (2026-10-25)

The owner asked for a review of the testing harness and the CI/CD workflows "as a principal engineer, allowed to question everything": the suite is too slow to run on every commit; the owner wants to branch from `dev`, implement one to three specifications per branch, pull-request into `dev`, release from `dev` to `main`, and run the full workflow only before publishing to PyPI. The memo `research/2026-10-25-a-development-process-that-runs-what-it-needs.md` recommended exactly that shape and put three choices to the owner: amend §5.6 and §5.7 so pull requests into `dev` behind one required check and one fresh review replace the landing lane, waves and the integration review; let a job accept from CI's record (the "not yet, after three G5-clean waves" of 2026-10-22, whose condition is met); run the release tier weekly on `dev` against the rule that slow tests run only to publish. The owner: "I agree with the recommendation." Recorded as **yes to all three**. What follows: `specifications/138-pull-requests-into-dev-and-the-judge-runs-where-it-is-needed.md`, drafted the same day, carries the exact constitution and AGENTS.md amendments and supersedes the reserved 117 to 121; it waits on its pre-build review and is built as a sequence of pull requests, the first made under the process it describes.

### Question 112: another user's home is not a supported configuration (2026-10-25)

Asked by the 0.1.0 security audit (`reviews/0.1.0-security-audit-2026-10-25.md`, finding F4, needs validation; `specifications/135-the-module-cache-is-read-through-the-descriptor-it-was-checked-by.md`, Decision 1), with the recommendation "not supported": is running wasi_python as root or as another user with a different user's `$HOME`, `$XDG_CACHE_HOME` or `$WASI_PYTHON_CACHE` (sudo keeping `HOME`, a container or CI step with a mapped home, a home on a shared folder) a configuration the project supports? The owner: "I'll go with your recommendation if it doesn't break any real use cases a dev may want." Recorded as **not supported**, on that condition. It holds: spec 135 never refuses a call; a cache whose path passes through a folder another user can write is not used, the module is compiled in memory, and one warning says to set `$WASI_PYTHON_CACHE`, so a developer under `sudo -E` loses that process's cache, never the run. What follows: spec 135 is defence in depth, after 0.1.0, in a free slot; the security model's cache bullet says the runner trusts every folder on the way to its cache to be this user's.

### The documentation before the 0.1.0 tag, within a day (2026-10-22)

With 0.1.0's third dry run green, the owner asked for the README to be "cut down to a clear explanation of what it is, a quick 5 min setup and run guide, and other important details a dev would want to see", everything else on a documentation site on GitHub, unneeded files removed ("like the questions to owner and such"), and other repositories studied for what they do well and for systems such as Diátaxis. Five agents researched; a sixth wrote the plan (`research/2026-10-22-a-plan-for-the-documentation.md`). The owner then decided:

- **Everything before the tag**: the README, the cleanup and the site, "but … we can't spend days on this. We need to get this done within a day". Git history is not rewritten: "we don't need to clean up git history, just the repo before we do the 0.1.0 release."
- **`context/` stays mostly as it is**; only files no longer needed are deleted (git history keeps them).
- **The advisory draft** (`upstream/advisories/GHSA-draft-0.1.0a3.md`): the owner files it in GitHub's advisory form, yanks 0.1.0a3 on PyPI and publishes; then the draft file is deleted.
- **The site** is served at the GitHub Pages default address; the owner sets Settings → Pages → Source to "GitHub Actions".

The lane's defaults for the plan's other questions: MkDocs 1.6.1 with Material 9.7.7 in the subset Zensical reads; the known gaps' `README.md` closers move to the site's limitations page; the private consumer's name stays in dated records, and a scan keeps it off every public page. To fit a day: two specifications built side by side with disjoint files (122, the README, the cleanup and the judge's changes; 123, the site's pages), no pre-build review (neither touches `src/` or the build recipe), one wave, one release acceptance, one dry run, then the tag. The owner, the same afternoon: "Because these are docs changes, we don't need to constantly be running the judge. We'll make all the changes need and then run the judge once at the end of our work." So for this work no builder dispatches a branch run or loops on the fast tier, and reviewers read the diff without re-running the judge; the judge runs once, as the lane's release acceptance on the wave's tip, followed by the dry run on main that rule 6b asks before a tag. Tested snippets as guest jobs, help strings for the CLI's options (runner code), versioned docs, the roadmap's trim and the specifications' archive wait for 0.1.1.

### The process advice, instituted (2026-10-22, night)

The owner felt the work "significantly limited by code running to test our code" and asked for research and an advisor's view. A research agent compared seven projects (`research/2026-10-22-how-other-projects-test-and-release.md`); a separate advisor ranked the changes (`research/2026-10-22-process-advice.md`). Going to sleep, the owner said: "work on instituting the changes and do what you can to get 0.1.0 ready for when I wake up by 6:00AM". The lane took the advisor's section 1 for tonight and reserved its section 2 for after 0.1.0:

- **The release acceptance runs at `-n 6`** while `build/lane.lock` is held and nothing else runs on the machine, else `-n 3` (AGENTS.md rule 6b; the progress README). Fuel is an instruction count and spec 052 showed the parallel verdict is the serial one. Memory is the risk: the lane watches the workers for ten minutes and restarts at `-n 4` past 24 GiB. A wave's acceptance may also run at `-n 6` when the machine is otherwise idle.
- **The last wave's acceptance may be the release acceptance**, when the wave's tip carries the version bump: a normal-tier run without `--accept` first, green, then one `--tier release --accept` run with every entry's reasons, which judges both tiers. The integration review reads during that run; the lane commits the acceptance only once it says the wave lands. This is the lane's reading of §5.5's "on main's tip" (the acceptance commit's first parent is the tip main fast-forwards to); if the owner reads it otherwise, the cost is a repeat, not a weaker release.
- **Dispatch first, write second.** The dry run on main is dispatched the moment the acceptance is on main; notes, delta reads and the CHANGELOG follow while it runs (rule 6b already allows context-only commits after it). No other dispatch starts until its jobs have.
- **Reserved after 0.1.0**: 117 to 121 and the later options, in the roadmap.

Unchanged: 067's own branch run, the fresh build and integration reviews, the release tier whole, the dry run on main's exact commit before the tag, and the owner's tag.

### The path to 0.1.0 is compressed (2026-10-21, night)

The owner asked whether the rest could be "finish up the specs, review them, and then do the full CI checks before creating a release", and chose the compressed plan the lane offered. For wave 12 (095 and 067) and the release only:

- Each specification still dispatches its one branch run, and its build reviewer starts on the diff while that run goes, reading the run back before its verdict (rule 8's order, relaxed).
- Wave 12 has no dry run of its own on `wave/12`. The lane rebuilds, judges and accepts the wave's tip as usual, its fresh integration review included, and fast-forwards main. The one CI check after that is the pre-tag dry run on main's exact commit (rule 6b), which runs every job the wave's dry run would and the release tier as well.
- The release reviewers' delta reads run beside the lane's release acceptance. Their files touch only `context/`, which may follow the dry run (rule 6b).

Unchanged: the fresh build and integration reviews, the lane's release acceptance (the release run's gather compares against it, G7), the dry run on main before the tag, and the owner's tag.

### Upstream hosts are not probed (2026-10-21, evening)

GNU Savannah, freetype's pinned host, was down from about 20:10 to 20:25 UTC, and the lane polled it every seven minutes to learn when it was back. The owner: "let's not probe the URL and pause work related to it for now. Don't want to be a part of something that overloads their servers." Then: let the run in progress finish, and hold new dispatches for an hour or two.

What follows: no agent polls or probes an upstream project's server in a loop. On a download outage, the lane holds runs that fetch from that host, tells the owner, and retries once, later, by hand. A second mirror URL with the same SHA-256 is a recipe change of its own, made only if the owner asks.

### Fast tests and slow tests (2026-10-21, morning)

Asked again, with spec 095's measured price, whether a 15 T fuel threshold should decide which of the packages' own tests run on every landing. The owner, in their words: "My thoughts on this have not changed, we need to have fast tests and slow tests. We only run slow tests when we are trying to publish to pypi, as it is critical we check that our package is working on the libraries we import before we release to catch any errors, otherwise we should only run the tests needed to confirm our new edits are working. I do not understand why this questions keeps coming up."

- **The rule, standing:** a package's own test suite runs in the release tier, whole; the normal tier holds the judge's own checks and, per package, a small smoke group that proves it imports and its core paths work. Nothing leaves the full suite. No branch run runs release groups.
- **Never re-asked:** the lane decides tier placement by this rule and writes each choice in its specification. It came back because the 2026-10-21 default was framed as "normal tier unless over 15 T", the rule inverted.
- **Applied to** spec 095 (its rule (8) struck) and spec 067.
- **The one branch-run exception** (2026-10-21, asked on spec 102's build review, M2): a branch run may run the release tier only when a specification changes the release-tier CI job itself (the `judge-release` job, the release pseudo-system's rules in `tests/harness/shards.py`, the gather's release half); adding or re-packing release shards for a package's groups is not such a change. The owner: "Allow it for that case only." The workflow keeps its `release-tier` input for that one use; the specification says so in its Kind line. Spec 102's run 6 stands as its proof of `judge-release`.

### Questions 108 to 111 (2026-10-21, early morning)

Asked one by one, each with the lane's recommendation.

- **108 (a structural review is a stage):** "Yes, amend as written." §5.6 now says a structural specification is reviewed before it is built against the rubric in `reviews/README.md`, and a fresh structural review of `src/` precedes each release beside the security review; the release waits on its High findings. The constitution's Status line records it. 0.1.0 needs `reviews/0.1.0-structural-review-<date>.md` (spec 108's check).
- **109 (Docker Desktop stopped):** the lane may start it. Standing rule: when Docker Desktop's engine has stopped (`docker` does not answer), the lane restarts it itself without asking. The lane restarted it that morning (its backend, running since 2026-09-04, would not stop; it was ended and the app started; engine 29.7.2).
- **110 (spec 095's four choices):** keep all four defaults: spec 088 widens to scipy's seven test-only C modules; the upstream opt-in modes (scikit-learn's seed sweep, `--check-spmatrix`, `SKLEARN_WARNINGS_AS_ERRORS`; scipy's `SCIPY_ARRAY_API`; statsmodels' formulaic engine; the doctests) stay unrun and are named in the README for 0.1.0, each mode's skips counted; a 15 T fuel threshold, above which scikit-learn's `test_common.py`, then its float32 cases, move to the release tier (still in the full suite); statsmodels' 13 left-out datasets are a README class, and a file that fails at import is a named gap.
- **111 (strings a user reads):** "Before 0.1.0." The string literals outside `src/` that cite a project document are reworded before the version bump, by their own specification (the lane's number, taken from the roadmap's reserved closer for spec 109's leftovers); the judge's allowance files' comments and the guest's own sources stay in that reserved line, after 0.1.0.

### Waves, judging on CI, and the dry run as the serial check (2026-10-19)

The owner asked for "5 spec implementors, 5 spec reviewers, merge them all together and build, fix any build issues, run CI, merge to main", and answered in the session that night (about 01:20 UTC on 2026-10-20), choosing among the options set out. The evidence is a design memo written in the lane's scratchpad, `pace/2026-10-19-the-wave-pipeline.md`, not committed. Its numbers that matter (READ from the lane log, `git log` and `gh run view`, or INFERRED as marked there): the first batch of two landed in 47 minutes end to end, 22 of them the lane's; one release workflow run judges a branch in shards on three systems in about 26 minutes, and three ran at once; the machine was saturated at 01:03 UTC, and the lane's `-n 3` acceptance took 17 minutes loaded against about 10 quiet. A landing costs the lane 50 to 120 minutes alone, and a wave of five about 75 minutes in all; local full judges fall from three per landing to one per wave. Likely 0.1.0 ready: Wed 2026-10-21, about 18:00 UTC (INFERRED), range Wed 10:00 UTC to Thu 2026-10-22 16:00 UTC, against Thu 2026-10-22 04:00 UTC estimated earlier that day.

- **Waves, adopted ("Adopt waves (Recommended)").** Up to five reviewed specifications land as one wave: at most one package or one stacked chain of packages, at most two other build-class specifications, the rest parallel-safe. The toolchain (086) lands alone, with judge-only specifications at most. One integration branch, `wave/NN`, made from main's tip by the lane, pushed for the wave's dry run and deleted at the fast-forward. Each builder rebases onto the wave's tip in the lane's order and names its conflicts; the fast tier runs after each entry; one rebuild in the main tree, compared with the release workflow's build of the same tip; one `-n 3` acceptance with each specification's reasons; one fresh reviewer of the integration. A red entry or an unexplained difference ejects the entry, never the wave; after two failed assemblies the wave is split by kind. Constitution §4.14, §5.4 and §5.7; AGENTS.md rule 2; `progress/README.md` steps 2 to 3a.
- **Judging on CI, adopted ("Yes, judge on CI (Recommended)").** Every full judge but the lane's moves to GitHub Actions: builders and reviewers dispatch `release.yml` on their branch and read the record back; locally they run the fast tier and single node ids only. §5.6's "re-runs the counted tests" is met by the reviewer's own run, whose id the review cites (its **Run** line). Constitution §5.6; AGENTS.md rules 3a and 8; `reviews/README.md`.
- **The dry run as the serial check, adopted ("Dry run = serial check").** The wave's dry run (serial shards, gather's G5 at 1e-4, three systems) replaces the local serial acceptance every fifth landing as spec 052's Decision 11 confirmation. Until spec 092 (the judge reads a release record) lands, one reviewer per wave keeps a local `-n 3` record, at a time the lane grants, for the sameness line. AGENTS.md rule 6a; `progress/README.md` steps 3, 3a and 7.
- **Reviewers write Low fixes in `context/`, adopted ("Reviewer writes Low fixes").** A reviewer may commit the exact text of a Low finding that touches only `context/`, once the builder hands the branch over. Code fixes stay with the builder. Constitution §5.6; AGENTS.md rule 8.
- **The local budget, lane procedure.** While `build/lane.lock` exists, no other tier of the judge runs (the fast tier included) and no container build starts; otherwise at most one native build, one container build and one fast tier at once, and never two full judges. AGENTS.md rule 3a.
- **CI's ceiling.** The plan is GitHub Pro: at most three release workflow runs live at once; a fourth waits.
- **A red dry run on main is fixed forward.** Nothing is reverted after a fast-forward; the next wave carries the fix first. A tag still needs a green run on main's exact commit (AGENTS.md rule 6b, unchanged).
- **Not adopted.** Spec B, the lane accepting from a CI record: "Not yet", revisit after three waves whose dry runs are G5-clean. A `judge_only` input to the release workflow (it saves runner slots, not wall clock, and is build-class). A cache of the artifact set keyed by the pins (after 0.1.0, unless CI minutes become the bottleneck).

### numpy's linear algebra on OpenBLAS before 0.1.0 (question 106, 2026-10-20)

numpy in the guest runs its bundled `lapack_lite`, not the OpenBLAS that has been in the set since spec 037. Spec 099's pre-build review inverted 300 exactly rank-deficient matrices in the guest and natively (numpy on OpenBLAS). After 099, the guest raises `LinAlgError` like native on 150, still returns finite numbers on 12 where native raises, and raises on 8 where native returns finite numbers. Matrices of `nan`s also fail with `ValueError: On entry to DLASCL` in the guest where native raises `LinAlgError` (099's drafting probe). The lane asked (AskUserQuestion), recommending 099 now and the OpenBLAS link right after 0.1.0. The owner's choice: "Both before 0.1.0". So:

- Spec 099 lands as drafted, its "as natively" qualified for `lapack_lite`.
- Spec 100 (reserved) links numpy's linear algebra to the set's OpenBLAS, so its results and errors match native numpy on OpenBLAS. It is build-class, stacked on 099, and lands before 0.1.0.

**Correction and question 107 (2026-10-20, later the same day).** The "native" numpy in 099's review and drafting probes was the oracle's `macosx_14_0_arm64` wheel, which uses Apple's Accelerate, not OpenBLAS; the 150/130/12/8 table above compares against Accelerate. Spec 100's author measured against numpy's `macosx_11_0_arm64` wheel (OpenBLAS 0.3.34, the set's release): of 300 exactly singular matrices, the guest agrees with native OpenBLAS on 249 with `lapack_lite` and 099, and on 254 with the set's OpenBLAS. The other 46 are rounding-edge cases (a pivot of 1e-16 or less) that wasm does not reproduce, likely for want of fused multiply-add (INFERRED). Native Accelerate and native OpenBLAS agree on 243. The lane had told the owner the link would close the differences; it told the owner this was wrong and asked again (AskUserQuestion), recommending yes: spec 100 still gives native errors for `nan` matrices, numpy and scipy agreeing, LAPACK 3.12 in place of 3.2.2, 30 to 56% less fuel on larger linear algebra and about 1.8 MB less `python.wasm`. The owner's choice: "Yes, before 0.1.0". Exact singular-matrix parity is not a goal in wasm; the README says so.

### Spec 102's four questions (2026-10-20, night)

Asked when spec 102 (the release tier) was drafted (`spec/102-the-release-tier`, 2bee892):

- **The constitution is amended at 102's landing:** the lane's landing judge is the normal tier; the release tier runs as the release rules say. Its release-rule line is added with it.
- **The lane runs the release tier locally only before a tag**, not at a landing that changes a release-tier row (the owner chose the stricter reading; the lane had recommended both). A release-tier regression therefore surfaces at the release acceptance and is traced back to its wave then.
- **contourpy's `random_big` cases (about 2.8 T) move to the release tier.** The owner, in their words: "Move to slow teir. We can decide what is slow tier but do not exclude anything from the full suite." So the tier is the project's choice, not only upstream's markers; the rule against leaving tests out stands: every test runs in one tier or the other.
- **CPython's resource-gated tests (`-u cpu`, `largefile`) join 102's release tier.**

### statsmodels' suite, its six components, sympy's slow test, and two tiers of tests (2026-10-20, evening)

Four answers, asked as 045 and 067 were prepared (045's builder; 067's pre-build review):

- **statsmodels' own suite goes to spec 095** (before 0.1.0, beside scipy's and scikit-learn's), on 066's machinery; formulaic, interface-meta and wrapt, pure-Python, go to 067. 045 builds the package. Natively the suite collects 21,412 tests (20,911 pass, 1 fail, 356 skip, 146 xfail); about 3 T of guest fuel, inferred.
- **Six statsmodels components whose terms question 83 did not name are approved**, each with a notice in `LICENSES/statsmodels.txt`: `tools/parallel.py` (from mne-python, Simplified BSD; MNE's licence pinned), `tools/docstring.py` (numpydoc, already pinned), libqsturng's `_phi` (Acklam's algorithm; its own file says its licence is not stated), `tsa/stl/_stl.pyx` (NCSA/BSD-3, from netlib's STL), `graphics/boxplots.py` (after Coelho and Ikonen), `regression/quantile_regression.py` (translated from Mohammadi's Matlab with permission). 045's confirming review corrected one fact after the question went out: libqsturng is a fallback for scipy before 1.7, dead code in this build.
- **sympy's one slow test (about 2.6 T alone) runs on CI in a shard of its own**, allowed past the 360 s shard bound.
- **Two tiers of tests.** The owner, in their words: "I think we should have two concepts of tests. We do not need to run the slow tests unless we're are creating a new release that we publish to pypi. Otherwise, for normal checks, we don't run the slow tests." The lane's reading: upstream's opt-in slow tests (sympy's slow and tooslow, networkx's and narwhals' `--runslow`, numpy's and pandas' `slow`, contourpy's `--runslow` cases that 066 runs today) form a release tier, run on the publishing (tag) run and on the dry run on main before a tag (rule 6b: a tag follows a dry run that passed every job), and skipped on branch runs, wave dry runs and the lane's accepts. Spec 102 builds the tier; until it lands, 066's contourpy slow cases stay in its normal groups.

### statsmodels and the pure-Python packages' own tests in 0.1.0 (2026-10-20)

The lane asked, as wave 08 neared, whether 045 (statsmodels, with formulaic, interface-meta and wrapt; the last of the scipy and scikit-learn chain) and 067 (the pure-Python packages' own tests in the release, 066's companion under "Every test of every package we build") belong in 0.1.0. The owner: both. 0.1.0 waits for wave 09 (100, numpy on OpenBLAS; 101, the faster release run), 045 and 067.

### Fewer CI runs per specification, and a faster run (2026-10-20)

The owner asked whether the CI strategy was working, since work seemed stalled. The lane's answer: release runs took 21 to 27 minutes through wave 05 and take 46 to 64 now (105 when queued behind the three-run limit); wave 07's dry run spent 34 minutes on the native build on macOS and about 25 on the macOS shards, own-guest (21 min) and own-embedding (17 min), which started 3 to 8 minutes late waiting for a runner. Each specification ran CI three to five times (wave 07, two specifications, about eight runs): the builder's, the reviewer's own on the same commit (spec 100's two runs, 39439703872 and 39448839291, gave the same growth lines value for value), and another after each rebase onto a wave the dry run then checks again. Waves landed about five and a half hours apart. The owner chose all three of the lane's proposals:

- **The reviewer reads the builder's run** when that run is on the exact commit reviewed, and names it as its own; it dispatches its own only when the commit differs. Constitution §5.6 is amended.
- **No branch run after a rebase.** A builder that only rebased onto a wave's tip, with every conflict named and the fast tier green, dispatches no new run; the wave's dry run on three systems is the check. A rebase that changes code beyond its named conflict hunks is not "only rebased" and runs again.
- **Spec 101, a faster run, before 0.1.0** (build-class, the release workflow): reuse the native build when the hash of its pins and recipes is unchanged, and split the macOS own-guest and own-embedding shards. The lane's estimate, not measured: about 60 minutes to about 30.

**Spec 101's build shard moves to Linux on every run (2026-10-20, later the same day).** The draft found a cache hit cannot skip a source build: the build shard's checks read the build tree (about 27 GB), not the finished set. It moves them to a new arm64 Linux job that builds from source on every run. Its pre-build review (M1) found that on a tag, seven of those checks (the compile records and `clang -###`, the host Python, the try-table and ducc0 clang checks, the link map's one qhull, `pyconfig.h`) would then read a Linux tree that builds the same bytes, not the published macOS tree: equal bytes stay proven (same-bytes, G2), but CI no longer reads how the published build was made. The review's corrected estimates: about 25 minutes on a reuse run (up to about 35), 35 to 50 on a source run; reuse fits about a third of runs. The lane recommended keeping the build shard on macOS for source runs (2 to 3.5 minutes slower). The owner chose to move it to Linux always, tags included. The lane's darwin run at every landing still runs the seven checks on a macOS tree; the spec writes M1's corrected wording into its Decision 5 and Intent.

### Every test of every package we build (2026-10-20)

Spec 066's re-survey on wave 06's set (branch tip `ad3c065`) found the budget rule's price was misstated in the answer below. contourpy measured 4,155 G, of which its `test_*_random_big` cases are about 2,833 G. By the rule, 066's caps are about 12.6 T, not about 7 T. Counting the 2.89 T of upstream groups the judge already runs, a full judge runs about 11.2 T of upstream fuel with every test, or about 8.4 T without the random_big cases. The confirming reviewer's delta review found that contourpy's two big files cannot stay single groups: each would need a shard to itself, past criterion 12. The lane explained this to the owner without a recommendation and asked Fable to weigh in. Fable recommended leaving the big cases out as upstream's own slow-host selection (contourpy's `test.yml` runs `-k "not big"` on its emulated legs, which the lane confirmed in the pinned 1.4.0 source).

The owner chose otherwise, in their words: "I think I want to include all tests from the packages that we are building into wasi_python, so if we can achieve that, I'd love to keep that in and adjust our caps so we can handle them." So:

- Every upstream test of a package we build runs in the release, random_big included. The rule against leaving tests out for convenience stands, unamended.
- Caps follow the same rule (1.5 times measured fuel, each family's budget the sum of its caps), now about 12.6 T for 066. A group too big for one shard is split into groups by construction (spec 066's option (b): an ordered list of `-k` expressions, each group excluding the earlier ones and the last taking the rest), never left out.
- The price, accepted: about 11.2 T of upstream fuel per full judge (3.9 times today), about twelve Linux shards for 066, and longer lane accepts. Fable's note stands as the speed lever: spec 092 (the judge reads CI's record) shortens the lane's own judge.

### Three answers for 0.1.0 (2026-10-20)

The owner answered three questions the lane asked on 2026-10-20 (AskUserQuestion):

- **scikit-learn's two unnamed components: approved.** Spec 044 bundles HDBSCAN's code (Leland McInnes, BSD-3-Clause, `cluster/_hdbscan/`) and one function in `model_selection/_split.py` based on a Kaggle kernel (Apache-2.0), with pytest's MIT text for a few derived lines; question 83's approval did not name them (044's builder note B1, confirmed by its pre-build reviewer). The owner's choice: "Approve both". The notices ship in `LICENSES/scikit-learn.txt`.
- **Spec 066's fuel budget: the larger budget, set by rule.** matplotlib's own tests alone measured 3.35 T against the 3 T budget for every compiled package. The owner's choice: "Larger budget by rule": each group's cap is 1.5 times its fuel in the re-survey on 043's set with 096, each family's budget the sum of its caps (about 7 T), across six Linux shards. The price, stated in the question: every full judge runs about 7 T of upstream fuel instead of 2.84 T, roughly 1.5 to 2 times longer accepts. Not chosen: running part of matplotlib on Linux CI only, or leaving test files out (which would need the rule against leaving tests out for convenience amended).
- **numpy's silent singular inverse: fix before 0.1.0.** With no floating-point exception flags in wasm, `numpy.linalg.inv` of a singular matrix returns `nan`s and raises no `LinAlgError` (spec 066's survey, a guest probe). The owner's choice: "Fix before 0.1.0": a specification (099, reserved in the roadmap) that makes singular matrices raise `LinAlgError` as natively.

### No more alphas (2026-10-19)

The owner said in the session that night (about 01:03 UTC on 2026-10-20): "No more alphas". The next release is 0.1.0, not 0.1.0a8 (the last tag is v0.1.0a7). Every specification's CHANGELOG lines go under the one unreleased section. It reads "0.1.0a8 — unreleased" until a small change runs `release/version.py` to make the version 0.1.0 in `__init__.py` and the CHANGELOG together (the rules check holds the two equal; AGENTS.md rule 2; the builder's self-check). The tag stays the owner's alone: the lane prepares the release and asks, after a green dry run on main's exact commit (AGENTS.md rule 6b) and the whole-surface security review's points closed.

### The 0.1.0 security review's owner points (2026-10-19)

The whole-surface review (`reviews/0.1.0-whole-surface-security-review-2026-10-19.md`, on main `302df18`) found the sandbox holding on every row of the threat model; 0.1.0 waits on S1 and S2. The owner answered in the session:

- **S1, S4, S7 (repository settings): "You apply via gh."** Applied by the lane with `gh api` and read back the same day: the `pypi` and `release` environments deploy only from tags matching `v*` (custom policy, type tag); immutable releases on; secret scanning and push protection on; Dependabot alerts requested. Only the workflow's two publish jobs name those environments, and they run on a tag push, so dry runs on branches are unaffected. S1 is closed.
- **S2:** closed by spec 084 when it lands (built and reviewed).
- **S5 (the guest's string hash is 32-bit FNV with a public key):** "sneak it in 086 and review it with the rest of the work". Spec 086 adds `--with-hash-algorithm=siphash13` at its rebase onto 083, and its delta review covers it; the README states the hash meanwhile.
- **S3 (an installed wheel can load a neighbouring `build/artifacts/` unverified):** "add to existing spec". Spec 087 (the a7 review's guest follow-ups, being built) takes it: no repository-relative set from an installed wheel, and a set's hashes checked before use.
- **S6:** closed by spec 085 when it lands.

### Speeding the work toward 0.1.0, and 078's Linux price (2026-10-19)

The owner asked for a measure of the pace and for proposals to speed it, and chose in the session among the options set out. The evidence is two memos written in the lane's scratchpad on 2026-10-19: the pace (0.87 landings an hour; the landing queue is the bottleneck; likely ready Fri 2026-10-23) and the proposals (P1 to P12, ranked; likely ready Thu 2026-10-22 if adopted).

- **Stacked builds (P1), approved.** A dependent specification may be built on its dependency's reviewed tip, not only main's; it lands after its base, rebased, with a delta review. Constitution §4.14 amended; AGENTS.md rule 2.
- **The lane accepts on three cores (P4), approved.** `uv run pytest -n 3 --accept`, serial every fifth counted landing as the periodic confirmation; spec 052's Decision 11 bar restated, since every recorded comparison differed only by checks blocked in a worktree. `context/progress/README.md` steps 3 and 3a; AGENTS.md rules 3a and 6a.
- **A permission allowlist (P6), approved as a draft for the owner to review.** A tracked `.claude/settings.json` allowing routine commands (worktrees, the judge, the build, reading and dispatching the release workflow), never one that pushes, tags or publishes. The agent drafts it; the owner reviews it before it is committed, since it changes what agents may run unasked.
- **numpy-core's layout-dependent fuel as a fact (P3), approved.** A small judge-only specification (091) takes `test_string_comparisons`' fuel, which moves with the bool DType object's address at every build-class landing (047, 071, 073, 043, 086), out of the ratchet as a recorded fact, by a reviewed judge change; the group's passes stay ratcheted.
- **Batch landings, approved.** Up to three reviewed parallel-safe specifications land as one batch, judged and accepted once; a red batch or an unexplained difference splits it. Build-class specifications land alone. Constitution §5.4 and §5.7.
- **Review follows risk, approved.** The pre-build review is required where §5.6 requires it and for the runner's code, optional for judge-only or context-only specifications; a Low finding or a note needs no further review round when answered in writing or in `context/` only. Constitution §5.6; AGENTS.md rule 8.
- **Six build slots, later the same day:** "lets make 6 build slots". Up to six build-class specifications may be built at once (four before); each still lands alone. Constitution §5.7; AGENTS.md rule 2.
- **Not adopted:** dropping the lane's local rebuild in favour of CI's, and a 1e-3 fuel band for CI against local (085's Decision 9 stays "not now").
- **The lane's own changes, the owner told:** 086 lands right after 083, then 039 and 043, with 073, 085, 084, 078 and 087 in the gaps (P2); a build-class, growth or Windows-touching specification is built only once its branch's dry run has run, and the lane's main dry run runs every second landing or before a tag (P5); `build/lane.lock` keeps other full judges off the machine while the lane accepts (P8); the whole-surface security review starts now on main, with an addendum per package (P7).
- **078's hand-off price on Linux:** "Accept (Recommended)". About 3× per provider or door call in a Docker VM (30 to 90–100 µs), against the quarter more on darwin accepted earlier; native Linux unmeasured; a cheaper hand-off and a native measurement are a follow-up.

### 105, and the open points of 078, 084 and 085, answered (2026-10-19)

The owner answered in the session, choosing among the options each set out (question 105's text is in this file's history, `questions-for-the-owner.md` before this commit; the specifications' points are in their "For the owner" sections on their branches).

- **105 (scipy's same-bytes exception against gather's G7):** "(b) Toolchain move first." Spec 086 (wasi-sdk 34, whose LLVM carries the fix for the `try_table` order) is drafted and built now, and lands before 037; 037's exception is withdrawn at its rebase onto 086, and no canonical digest is built. G7 stays an exact `python.wasm` hash and spec 085's set hash an exact `SHA256SUMS`. 086 takes 037's build slot while 037 waits; scipy, and 038, 044 and 045 behind it, arrive after 086. This replaces the previous entry's "after the packages" for 086, and question 104's exception is never landed.
- **078 (the runner runs each guest on a stack of its own):** all three of the specification's positions accepted: a wider C-stack window is a follow-up after 086, not part of 078; the thread hand-off for the embedder's code (about 7 to 8 µs a door or provider step on darwin, no fuel) is accepted, keeping the README's promise of where host functions run; CPython 3.14.0 on musl is refused with a `RuntimeError` naming 3.14.1.
- **084 (a private root never outlives its call):** both accepted: a folder left is reported as a `RuntimeWarning`, not a `stats()` key (the public API stays frozen); a failed removal is retried by at most three sweeps per process.
- **085 (gather checks what it trusts), Decision 9:** "Not now." Gather does not bound fuel across the three systems; a fuel band may be a later specification.

### 100 to 103, and the toolchain move's place, answered (2026-10-19)

The owner answered the four open questions and one new one in the session, choosing among the options each question set out (their text is in this file's history, `questions-for-the-owner.md` before this commit).

- **100 (where the cap on open files protects):** "Leave limits alone." The cap stays 1,024; the library never changes the process's limits; the README tells embedders to raise their soft `RLIMIT_NOFILE` or set `max_open_files` below it; `wasi-python run` raises its own, since it owns its process. Spec 072 (a bound on path depth) still closes the deep-path descriptors.
- **101 (CPython's C test modules):** "Yes, same judge binary." The later judge-only build of question 89, never published, is also built with CPython's test modules (`--enable-test-modules`), and the tests that need them run there. Spec 065's class, deselection and three left-out modules close with that specification (reserved in the roadmap as 088) instead of this question.
- **102 (what closes the deep-recursion traps):** "(a) Runner-owned 8 MiB stack." The runner runs each guest on a thread of its own with an 8 MiB stack, and the README asks other embedders for the same. Spec 078 (the runner's own threads have room for the wasm stack) is folded in and widened to this; its costs (host functions on the runner's thread, the caller's contextvars copied in, Ctrl-C stopped from another thread, `threading.stack_size` under a lock or a pool of its own, `run_async` with the caller's executor) are its design's to answer. Before 0.1.0. Spec 065's trap entries name 078 as their closer once it is drafted.
- **103 (finalizing what a program hangs on the frozen heap):** "Yes, unfreeze before finalizing." `run` on the snapshot undoes the freeze before it finalizes, as a session's close does (spec 055), so the snapshot finalizes exactly as CPython does, at about +28 M instructions a call. Spec 073 is amended to do this as well as give every program a fresh `__main__` (which still fixes a script and `-m` on both binaries); spec 069's check (b), the snapshot's start at least 8 times cheaper than the plain start, is restated by 073 with this decision as its reason (about 3.8 times), and check D's gap closes.
- **The toolchain move (spec 086, wasi-sdk 34):** "After the packages." scipy lands with its same-bytes exception (question 104); 086 takes a build slot once the package chains are built, or when no package is ready, and removes the exception.

### 104, answered: scipy lands with a narrow same-bytes exception for ducc0, fixed in parallel (2026-10-19)

- **Asked:** 2026-10-19 (question 104, from spec 037's build: its research memo `research/2026-10-19-ducc0-is-not-reproducible-with-the-pinned-clang.md`). The pinned clang (wasi-sdk 33, LLVM `4434dabb`) compiles one scipy file, ducc0's FFT (`pyduccfft.cxx`), to different bytes on every run; the optimized IR is the same, and the objects differ only in the nesting order of `try_table` blocks in eight functions (the WebAssembly backend). Every other compile is reproducible, and every set built passed the judge. `-O1`, `-O2` and backend switches did not help; `-Os` was reproducible but crashed at import. Spec 037's criterion 3 (the same `SHA256SUMS` from every host) allowed no exception, and 038, 044 and 045 wait on 037. The agent offered: a narrow, recorded exception now with the fix researched in parallel; waiting for a fixed clang; or building ducc0 another way.
- **The owner, 2026-10-19:** "Exception now, fix in parallel."
- **What follows:** spec 037 is amended at build. The same-bytes gate lets exactly that one object's difference through, and a check proves the difference is only the `try_table` order in the named functions: nothing else may differ, on any host. The exception is recorded (spec 037, the CHANGELOG, the README's reproducibility claim) and its design is reviewed before it is built. A research task runs at the same time: reduce the case, read the backend at `4434dabb`, check newer wasi-sdk and LLVM releases, and draft the upstream issue for the owner to send. The exception is removed by the specification that moves the toolchain pin to a fixed clang.

### The packages come first, with four build slots (2026-10-19)

- **Asked:** 2026-10-19, in the session. The owner, that morning: "Can we bring scipy and other packages up in the priority list? I want them done soon." The agent offered three shapes for 039 (tier A), the next package with every dependency landed, while the three build slots held 037, 043 and 065: a fourth slot now; 039 when 065 lands; or 065 paused for 039.
- **The owner, 2026-10-19:** a fourth slot now.
- **What follows:** constitution §5.7 and AGENTS.md rule 2 are amended: up to four build-class specifications are built at once while the packages come first; each still lands alone. A free build slot goes to the next package whose dependencies have landed (037, 038, 044, 045; 039, 041; 043, 042); 073, 072 and 078 build only when no package is ready. The lane lands a built package before any other built specification, except 065, which gates 0.1.0 (question 99) and was already close to landing. 039 starts at once.

### 99, answered: CPython's own test suite gates 0.1.0 (2026-10-18)

- **Asked:** 2026-10-18 (question 99: should CPython's own test suite gate a release? Source: spec 063, Decision 15 and Scope). Spec 063 makes every component of the artifact name its own suite and runs numpy's and pandas' in every release; CPython's suite (`python -m test`) knows WASI but is large, and was not measured.
- **The owner, 2026-10-18:** "Gate 0.1.0 regardless".
- **What follows:** CPython's own suite becomes release shards through its own specification, 065 (reserved in the roadmap), before 0.1.0. Until it lands, `python` is `later` in `tests/upstream/packages.toml` with 065 as its closer (spec 063, Decision 15). A research memo measuring a fast selection in the guest comes first (§5.1).

### 98, answered: spec 063's builder dry-runs the release on its branch; changes move to pull requests (2026-10-18)

- **Asked:** 2026-10-18 (question 98: may spec 063's builder push its branch and dispatch `release.yml` on it before landing? Source: spec 063, Decision 18). Spec 063 runs the whole judge on Linux and Windows for the first time; without a branch run, the first measurement would be the lane's dry run on main, and a failure there would block the next tag.
- **The owner, 2026-10-18:** "Yes, and we should also change the way we push to github: push changes as a branch, create a PR to main that runs the tests."
- **What follows:** at build time, spec 063's builder pushes its branch, dispatches the release workflow on it as a dry run (never signs or publishes), fixes what Linux and Windows find, and deletes the branch from GitHub after landing (spec 063, Decision 18, acceptance 10). The second half, branches with a pull request to main that runs the tests, is spec 064's; spec 063 keeps its judge jobs and gather reusable as pull-request checks (its Scope). AGENTS.md's push rule changes with 064, not before.
### 34, answered: the snapshot pre-imports no package (2026-10-18)

- **Asked:** 2026-10-17 (pre-import matplotlib?); reframed by the owner 2026-10-18: "make it true for all packages whatever the decision is … if we can leave them all as not pre imported then that makes the most sense … but if we must pre import some, we should import all."
- **Measured** (`research/2026-10-18-one-pre-import-rule-for-every-package.md`, a Fable agent; the frozen set's snapshot reproduced byte for byte by the method): with the stdlib only, a bare snapshot run costs 15.6 M fuel instead of 83.4 M, a live instance 9.6 MiB instead of 41.3, the wheel about 41 MB instead of 52; a pandas script costs 4.63 G instead of 110 M (42 times), numpy 9 times, a plot 16% more. Pre-importing every package breaks PyPI's limit within about three specifications (the wheel 123 to 207 MB at the roadmap's end).
- **The owner, 2026-10-18:** "None pre-imported": the default snapshot pre-imports the stdlib bootstrap only, for every package now and later.
- **What follows:** a build-class specification (069) changes `PREIMPORT` in `recipes/reactor_main.c`, its checks, the README's start-cost facts and every fuel number that moves (`--accept-growth` for the pandas and numpy jobs, with this decision as the reason). Mitigations, each its own later choice: bounded sessions (spec 055) pay an import once per session; a `run` that skips Python's teardown at exit (94 to 99% of a bare run's fuel is teardown); a `full` profile, its own artifact set, if an embedder asks.

### The owner's answers of 2026-10-18, evening (questions 64, 90, 92 to 97, and pull requests)

Asked one by one, with the agent's recommendation in each question.

- **64 (the wheel and PyPI's limit):** "wait on a decision until we cross the 100MB threshold". The wheel is about 54.3 MB with lxml (spec 046). Each landing records its size; the agent brings the question back when a landing would cross 100 MB.
- **90 (`batch` in the tool protocol):** after 0.1.0, as recommended.
- **92 (bounded sessions, spec 055):** keep its three choices where they follow precedent, "especially that of Jupyter". `sys.exit()` keeps the session and the last expression is echoed, as in Jupyter, so both stand. Closing did not follow Jupyter, which lets Python exit normally; the owner chose to follow Jupyter: at close and at expiry the session runs Python's shutdown (`atexit`, flushes) inside a small fuel and time budget, and is stopped if the budget runs out. Spec 055's Decision 8 changes before it is built. **The descriptor cap comes before 0.1.0**: a per-sandbox limit on files open at once, set by the embedder like the other limits, default 1,024, `EMFILE` past it, for `run` and sessions alike. The owner's principle, kept: "if an embedder provides it access to an OS and file system, it should be able to use that file system until time, fuel, memory, etc of that individual session run out"; the cap guards the host process, not what the guest may use. A specification of its own.
- **93 (a read-only mount on the import path):** no. "Agents will not be importing code, and wasi python should not design for this use case. The dev building an app with wasi python would define all of the imports and code and libraries upfront." Mounts stay refused there.
- **94 (rulesets):** yes, the agent sets them. Done 2026-10-18 with the owner's `gh`: ruleset 25363090 on the default branch (no deletion, no force push, updates only by the admin role) and 25363091 on `refs/tags/v*` (creation, deletion, moves and updates only by the admin role). The agent's pushes pass as the admin's ("Bypassed rule violations" is printed on each push).
- **95 (docs commits after a dry run):** allowed, written into AGENTS.md rule 6b.
- **96 (a Rust core):** "I want to move over to a rust core after 0.1.0, but I do not think that mean we replace wasmtime-py, but this can be decided later. The main thing is a rust code that can be shared by python and js, at least partially, so there is less to maintain." After 0.1.0; the research and the spike are on record.
- **97 (the release environments):** "nothing for now, later we can state the main is the only branch that can do the release and enforce a human review step."
- **Pull requests (asked with question 98):** "We should push changes as a branch, create a PR to main that runs the tests, and once completed and approved, merge the changes." Asked who approves (a pull request's author cannot approve it, and the agent works as the owner's account), the owner chose "My account, checks only": pull requests must pass their checks; no approval is required. Spec 064 specifies it, after spec 063, whose shards become the checks.

### 91, answered: up to three build changes built at once (2026-10-18)

- **Asked:** 2026-10-18 (question 91: build the next build-class specification stacked on the one in review?). The owner asked that day what limited parallel work; the agent named constitution §5.7's own rule ("a change to the build recipe overlaps no other change to the build recipe", the owner, 2026-10-17) and offered two shapes: build in parallel and land one at a time, or ship several as one landing.
- **The owner, 2026-10-18:** option A, "up to 3, land one by one".
- **What follows:** constitution §5.7 and AGENTS.md rule 2 are amended. Up to three build-class specifications are built and reviewed at once, each in its own worktree. Each lands alone: the lane rebases it, rebuilds the set from the pins in the main tree, compares it with the builder's set rebuilt on the same base, judges and re-measures it; a delta review follows when the rebase altered its recipe hunks or its numbers moved beyond what its review saw. Shipping several as one landing was declined: one landing stays one specification (§5.4). Chains stay in order (scipy before scikit-learn and statsmodels; 041 before 039).

### The x86_64 rebuild without emulation (2026-10-18)

The owner, 2026-10-18: "I don't see the value in the hour long build under emulation", then, on `research/2026-10-18-byte-identical-wasm-builds-prior-art.md` (the flag `-ffp-contract=off` makes the pinned x86_64 and aarch64 clangs emit the same numpy object; no project studied emulates a compiler or normalizes compiler output): "I agree, please make these changes."

- `-ffp-contract=off` goes on **every** compile in the recipe (one rule, not numpy only), as a recipe item under constitution §4.1's first kind.
- The x86_64 rebuild runs natively. The emulated compiler (spec 040's `clang-emulated` and its pins) stays in the tree, switched off, for one release as the same-day fallback, then is deleted.
- "The same bytes" keeps one meaning: `SHA256SUMS` equal, byte for byte. No per-function exception list.
- Specification 059 carries it, build-class, after spec 023 and before spec 057. It changes specs 012 and 040's decisions; its evidence is a dry run with emulation off.

### Work on while the owner is away; the agent may publish alphas (2026-10-18)

The owner, before stepping away on 2026-10-18: "please continue working and do not pause to wait for me. If you run into issues like git worktree, find a resolution for them that is safe. If you have questions, please document them in questions for owner. Do not stop working unless 0.1.0 is fully implemented and ready to publish. You may publish alpha releases but not the 0.1.0 release."

- This is the owner's explicit instruction under constitution §7 for these actions: pushing `main` and alpha tags (`v0.1.0aN`), dispatching the release workflow's dry runs, and publishing alpha releases to GitHub and PyPI. Every other §7 rule stands: no 0.1.0 tag, no final release, nothing else outward-facing.
- Each alpha still waits on its pre-release security review (§5.6).
- Two working changes the owner asked for the same day: builders and reviewers loop on the judge's fast tier and run the full judge once per stage (`AGENTS.md`, rule 3a); and the judge on several cores, researched and specified first (spec 052).

### 49–89. The overnight questions (answered 2026-10-18)

The owner went through every question written overnight on 2026-10-18, in rounds, with the agent's recommendation beside each. The full questions, with their facts, are in git history (`questions-for-the-owner.md` before this change) and in the specifications they cite.

- **49, answered:** nothing is cut from 0.1.0. The owner: "we need to have the tool protocol, a byo file system for embedders, async host functions, sessions, so basically cancel nothing for 0.1.0". So 0.1.0 carries the cancel fix (030), the tool protocol (031, 036), the filesystem provider (032) and writable mounts (034), and also async host functions, read-only code on the import path and bounded sessions (state across agent turns). The three new ones need specifications; sessions need their research first (`research/2026-10-17-state-across-agent-turns.md`).
- **50–53, answered:** keep the tool protocol's defaults as built.
- **54, answered:** a provider may also raise `OSError`; its errno is then the guest's answer (any other exception stays a fault, `EIO`). A follow-up change to spec 032's provider.
- **55, 56 and 72, answered:** keep as built (staging bounded by `memory_bytes`, the `max_file_calls` names, one buffer per open).
- **57–63, answered:** keep all as decided: 033 landed first; the `-V` banner keeps "no ctypes"; spec 035's reader replaces `zipfile.Path` for the zip's packages, and its three run-time replacements are a recipe under §4.1, not a carried patch; scipy is not pre-imported until measured (with question 34's numbers); OpenBLAS's backport is carried in git until 0.3.35; x86_64 compiles with the emulated aarch64 clang.
- **64:** still open (wait, then assess from the measured wheel).
- **70, answered:** yes, unpushed only. If a bad acceptance commit reaches `main` unpushed, the lane may `git reset --soft` that one commit (constitution §4.14); a pushed one stops the lane and comes to the owner.
- **71, answered:** the POSIX rule: unclosed files are handed to the provider at every ending that returns a result, a cancel and a deadline included. Spec 034 lands as built.
- **73, answered:** (a) reportlab's fonts stay out for good; (b) the agent drafts a facts sheet on the `zipimporter._files` bug for the owner to send; (c) the four-clause BSD of Tyler C. Sarna's barcode modules is approved with its advertising clause (§4.12): a later change ships `reportlab/graphics/barcode/`, adds a QR code and a Code 128 barcode to the PDF golden, and puts "This product includes software developed by Tyler C. Sarna." in the README's barcode line, the CHANGELOG, and any later material that mentions barcodes.
- **80, answered:** for projects that restrict AI-written contributions, the upstream draft is a facts sheet (spec 020's six header lines) from which the owner writes and files in their own words.
- **81, answered:** contourpy (BSD-3-Clause) approved, with `LICENSE_YORICK` covering its GIST-derived code (§4.12). Spec 043 is unblocked.
- **82, answered:** (a) lxml (046) and regex (047) may take a free build-class slot before scipy (037, 038); (b) `lxml.isoschematron` stays out for 0.1.0; (c) lxml's ElementTree and difflib-derived files are read as inside the approved CPython family; (d) the agent drafts a wasi-libc and musl facts sheet on GB18030.
- **83, answered:** all as decided in specs 044 and 045: scikit-learn's and statsmodels' bundled code approved; CC BY 4.0 approved for scikit-learn's digits, breast cancer and wine data (§4.12), all six datasets ship with an attribution part; the two sample photographs and statsmodels' fourteen datasets without public-domain terms stay out. Specs 044 and 045 are unblocked.
- **84:** settled by events: spec 048's mitigation landed before any release.
- **85, answered:** the exact 49.0.3 rule (as landed); symlinks are not refused.
- **86, answered:** facts sheet 12 stays the standing ask; the shadow is removed with the pin that moves past wasmtime 49.0.3.
- **87, answered:** both, after 0.1.0a4 (with the fix) is on PyPI: the owner yanks 0.1.0a3 and publishes a GitHub security advisory for wasi-python; the agent drafts the advisory text.
- **88, answered:** the stricter promise: a deprecated thing survives at least **two** final minor releases (as CPython's PEP 387), the rest as spec 049 writes it. Spec 049 is revised to say so before it is built.
- **89, answered:** (a), a judge-only binary linked with numpy's test modules, never shipped: a later build-class specification.

### The owner's direction for the product (2026-10-17; moved here 2026-10-22)

Kept in `questions-for-the-owner.md` until that file was deleted (spec 122). The owner, in paraphrase, without the private path the original named: "I am thinking of this more as a safe runtime for agent code. The use case is much more powerful web agents that can access code and interact with their data and tools (either through a file system, tools in the host program, api calls, mcp, etc.)"; its main use case is to work with a filesystem layer that manages the permissions and governance.

The code stays embedder-neutral (§4.5). The capabilities that agent use needs are built as general features; `research/2026-10-17-the-runtime-for-agent-code.md` studies which. State across turns is researched before any specification (`research/2026-10-17-state-across-agent-turns.md`).

### 43–48. What else the default profile carries

- **Source:** `research/2026-10-17-what-else-the-default-profile-carries.md` (tiers A to D).
- **43, answered 2026-10-17:** tiers A and B approved, with their licences (constitution §4.12), tqdm's MPL-2.0 and regex's CNRI-Python included.
- **44, answered 2026-10-17:** cut the zip's per-member cost first: a research memo, then a specification ("the zip's directory is read once"), before tier A grows the zip.
- **45, answered 2026-10-17:** sympy (with mpmath) joins the default profile after that fix.
- **46, answered 2026-10-17:** nothing writable stays the default; the README documents that openpyxl needs a writable folder and that xlsxwriter (or pandas' `engine="xlsxwriter"`) writes in memory.
- **47, answered 2026-10-17:** pytz is left out; `zoneinfo` is the supported path.
- **48, answered 2026-10-17:** all of tier B is in 0.1.0: scikit-learn, statsmodels, lxml (with python-docx and python-pptx) and regex, after scipy.

### The roadmap, and 0.1.0's contents

- **Decided 2026-10-17:** "Matplotlib and scipy are v0.1.0 for sure, and we should probably consider what other libraries we should include for our v0.1.0 default profile." And: "Vfs shouldn't be a part of our 0.1.0 considerations, that is the main consumer of this package but not a part of its roadmap, and can we update the constitution to remove roadmap details from it? That will change over time."
- Done: the constitution's §2 is now the bar every release meets; the order of work and each release's contents live in `roadmap.md`. The candidates for the default profile are being researched.

### 41–42. The filesystem provider

- **Source:** `research/2026-10-17-a-filesystem-provider-for-the-runner.md`.
- **41, answered 2026-10-17:** a provider may be mounted at `/`, making the embedder the guest's whole filesystem; a `/` mount and `root=` are mutually exclusive; the zip stays at `/usr/local/lib`.
- **42, answered 2026-10-17:** provider calls have a default limit of 10,000 per run; at the limit the run stops, as at its fuel or deadline, and the result names it.

### 37. The tool protocol's gate, and 13. vfs on this runner

- **Studied:** vfs's authority model (read-only, 2026-10-17): every vfs verb takes an `Authority`; programs get an `Fs` curried with the caller's authority (vfs ADR 082); every call re-enters the router's gates; a denial is a `Result`, never an exception; "No `ask` inside vfs" (ADR 084); vfs needs to count calls (`VERB_CALL_BUDGET`) and record refused writes even on exit 0 (its specs 169 and 172); vfs planned its own host (spec 169b) and treated wasi_python as artifacts only.
- **37, answered 2026-10-17:** an optional `gate=`. Tools are capabilities, their authority bound by the embedder; wasi_python validates, routes, counts (`max_tool_calls`, with a default) and records each call's outcome in the result; `gate=` may refuse a validated call before the tool runs, and is absent by default.
- **13, answered 2026-10-17:** "converge on our runner, but do not edit vfs". vfs is to run its guests through `wasi_python.run`. That needs a filesystem provider in the runner (the guest's file calls served by embedder code, as vfs's 169b shim does), researched first. This project never edits vfs; vfs's own specifications are vfs's to change.

### Parallel work: build in parallel, land in series

- **Decided 2026-10-17:** adopted `research/2026-10-17-parallel-work-without-lowering-the-bar.md` (decisions A to D applied to constitution §4.14, §5.4, §5.7, §7 and `AGENTS.md`; F: commits on `spec/` branches are commits, so §4.14 applies as written). Decision E, the four judge rules (an acceptance sits on the commit it judged; main is linear; `--accept` refuses in a linked worktree; a worktree inside the repository is not judge input), is built as its own specification before parallel builders run.
- Disk: the old scratch clones of landed specifications were deleted (owner's approval).

### 38–40. The tool protocol (37 stays open)

- **38, answered 2026-10-17:** the guest's namespace is `host`: `from host import tools`.
- **39, answered 2026-10-17:** schemas are validated first. Errors follow `subprocess.run`'s precedent: `run()` never raises for what the guest or a tool does (it returns `exit_code`, `stdout`, `stderr`); it raises only for programming mistakes, before anything runs; inside the guest a failed tool call raises `ToolError`, as normal Python. No `run_safe`.
- **40, answered 2026-10-17:** no adapters ship (LangChain, MCP); the README may show recipes.

### Install as `pip install wasi-python`, without the `run` extra

- **Decided 2026-10-17**, after 0.1.0a3 shipped: "Could we change it to just pip install wasi-python and not with the run for the next release? That would be a better dev experience."
- wasmtime-py (`wasmtime>=49,<50`, about 8 to 10 MB per platform, with a wheel for every major platform) becomes a required dependency; `wasi-python[run]` stays as an empty alias so older instructions work. Built as spec 028 for 0.1.0a4 (§4.13 asks the specification for the reason).

### 12 and 14. A tool protocol over the door

- **Asked:** 2026-10-17 (12: `research/2026-10-17-market-research-use-cases.md`, proposal A; 14: `research/2026-10-17-the-runtime-for-agent-code.md` §6).
- **Answered 2026-10-17:** yes. "wasm-python should be able to call tools/api/MCPs of the host program through a gated protocol that we design." And: "we should build our own convention. study langchain tools and monty for how it develops tools and how it passes to an embedded programs so we have a clean and familiar api." §4.4 amended: the raw door stays opaque; one optional tool protocol rides on it, used only when the embedder passes tools, gated per call.
- **Next:** a research memo on LangChain's tool API and Monty's embedding API, then a specification.

### 15. Async host functions

- **Answered 2026-10-17:** yes, as a later specification, with the tool protocol: an async host function awaited by the guest's door call, under the call's deadline.

### 16. Read-only code on the guest's import path

- **Answered 2026-10-17:** yes, as an explicit read-only typed grant the embedder asks for; never writable, never by default.

### 17. Per-access governance

- **Answered 2026-10-17:** left to embedders. The runner offers the hooks (grants, the gated tool protocol, a filesystem provider); policy and audit live outside.

### 18–22. State across agent turns

- **Source:** `research/2026-10-17-state-across-agent-turns.md`.
- **18, answered 2026-10-17:** yes, a second guest export that runs a turn without finalizing, after a pre-build review.
- **19, answered 2026-10-17:** a bounded session is in scope (§3 amended): one guest across several calls, not a shell.
- **20, answered 2026-10-17:** default bounds 15 minutes idle and 1 hour lifetime, both overridable.
- **21, answered 2026-10-17:** a trap ends the session in its first version; pause, resume and rollback come later.
- **22, answered 2026-10-17:** yes, the README shows the files-in-a-granted-folder pattern for state that outlives a process.

### 23. Publish the wheel on PyPI?

- **Answered 2026-10-17:** yes, from 0.1.0a3, under `wasi-python`. The owner created the project on pypi.org and configured this repository as its trusted publisher: "try publishing to it". The agent sets the Actions variable `PYPI_PUBLISH=true` (GitHub makes the `pypi` environment on first use) and tags v0.1.0a3 once its release work is clear: spec 024 (the security review's S1), its confirmation, and question 24's strict default.

### 24. A stricter default

- **Answered 2026-10-17:** "our wasi-python shouldn't be able to interact with a filesystem unless explicitly provided by the embedder." A call given no root and no grants has nothing writable: no folder, no `/tmp`, no `HOME` (§4.15 amended). `root=None` (a private scratch root) stays available when asked for. It ships in 0.1.0a3, before the first PyPI release, as its own specification with a README migration note.

### 25 and 28–31. scipy

- **Source:** `research/2026-10-17-what-scipy-needs.md`, `research/2026-10-17-openblas-one-return-convention.md`.
- **25, answered 2026-10-17:** all of scipy's licences approved (§4.12 amended).
- **26:** covered by question 32's scope ("any project, with a drafted pull request").
- **28, answered 2026-10-17:** `scipy.odr` may be absent, documented, with a clear `ImportError`.
- **29, answered 2026-10-17:** wasm SIMD is accepted as a host requirement, in the default build too (it follows from 30). The judge pins the feature list with `+simd128`.
- **30, answered 2026-10-17:** "in the default build for now, we can assess later how to divy things up once we get to profiles."
- **31, answered 2026-10-17:** without pythran at first.

### 33. §4.1's spent clause

- **Answered 2026-10-17:** reword it, without naming the owner. It now reads "(question 32; built by spec 020)".

### 35. Licences for matplotlib

- **Answered 2026-10-17:** the whole list approved (§4.12 amended). Spec 023 can be built.

### 36. Upstream for matplotlib's patches

- **Answered 2026-10-17:** yes. Patch 1's draft says it is merged upstream; patch 2's pull request (`_qhull` without a writable `/dev/null`) is drafted for the owner to send, with M2.

### 32. Carry our own fixes to other projects, or wait for upstream?

- **Asked:** 2026-10-17. **Source:** `research/2026-10-17-what-scipy-needs.md` (OpenBLAS's C LAPACK traps under wasm until a type fix lands upstream), and question 27.
- **The question:** keep §4.1's zero patches (wait, or carry a generated shim layer), or carry patch files that mirror drafted upstream pull requests; and for which projects.
- **Answered 2026-10-17:** Carried patches, for any pinned project, each with an upstream PR drafted in the repository: "I do not want to wait for upstream. I want to build fixes ourselves but document the upstream fixes (PRs) we should submit to other projects." §4.1 is amended; a specification builds the mechanism (patch layout, apply step, `MANIFEST` lines, the release check) before any patch is applied. This also answers question 27 (no waiting) and reopens numpy's `.npy` fix (question 8) as a carried patch.

### 1. Constitution: "only the grants the embedder gives, which may be none"

- **Asked:** 2026-10-16. **Source:** `research/2026-10-16-a-principal-engineers-direction.md` (direction 4, "Constitution changes proposed"), `research/2026-10-16-where-package-data-lives.md` ("The owner's direction").
- **The change:** §2.2 and §2.4 say the guest sees "the one directory the embedder preopens". They would say: only the grants the embedder gives (read-only or writable folders), which may be none. The embedder contract becomes "bind one function, call one export; preopen what you grant".
- **What waits:** matplotlib's data (a second, read-only folder), several folders per run (typed grants), and a run with no folder at all.
- **Meanwhile:** the agent builds what the current text allows (spec 005, the hostile-guest checks, safe defaults with one folder).
- **Answered 2026-10-17:** Yes: typed grants, read-only or writable, which may be none. The constitution's §2.2 and §2.4 are amended.

### 2. matplotlib's data: a read-only folder (C2) or packed inside the binary (C3, wasi-vfs)

- **Asked:** 2026-10-16. **Source:** `research/2026-10-16-where-package-data-lives.md`, `research/2026-10-16-wasi-vfs-for-package-data.md`.
- **The agent's recommendation:** C2, a read-only folder mounted at the path matplotlib already looks in. wasi-vfs works on the real build and allows zero folders, but its packed output is not byte-reproducible (uninitialised padding), it adds about one instruction of start-up per packed byte for a reason not found, it brings Rust runtime code whose licences would ship, and it has one maintainer who has said he has little time. C3 is worth it only if a run with no folder at all, and the stdlib zip inside the binary, become goals.
- **What waits:** the matplotlib specification.
- **Answered 2026-10-17:** C2: a read-only folder where matplotlib already looks, built on typed grants. The constitution's §2 records it.

### 3. A new hard constraint, "safe by default"

- **Asked:** 2026-10-16. **Source:** the principal engineer's memo.
- **The change:** a new §4 rule: every limit has a default; no channel to the host opens without an explicit argument; the runtime's files are never in a writable grant.
- **Meanwhile:** the agent gives `run()` safe defaults anyway (your direction: "no way (unless explicitly provided) to access the host file system or network"); the rule would make them binding on every later change.
- **Answered 2026-10-17:** Yes, binding: §4.15 "Safe by default". A change that loosens a default needs the owner's decision.

### 4. Order of post-v1 work: sqlite3, bz2, lzma before matplotlib?

- **Asked:** 2026-10-16. **Source:** the principal engineer's memo, direction 8.
- **The question:** your order is matplotlib, then sqlite3/bz2/lzma, then scipy. matplotlib now waits on questions 1 and 2; sqlite3, bz2 and lzma need no C++ and no data folder. The agent works on them while matplotlib waits, and keeps your order for anything not blocked.
- **Answered 2026-10-17:** sqlite3, bz2 and lzma first (spec 007), then typed grants and matplotlib. The constitution's §2 records it.

### 5. Security rules for releases

- **Asked:** 2026-10-16. **Source:** the principal engineer's memo, direction 7.
- **The change:** §5.5 gains "a security fix in a pinned component is a reason to release"; §5.6 gains "a security review against the written threat model before each release".
- **Meanwhile:** the agent adds `SECURITY.md` and build-provenance attestations to the release workflow, which change no rule.
- **Answered 2026-10-17:** Both: §5.5 (a security fix in a pinned component is a reason to release; the agent prepares one and asks) and §5.6 (a security review against the threat model before each release).

### 6. May the agent publish 0.1.0a2?

- **Asked:** 2026-10-16.
- **The question:** you authorised 0.1.0a1. Spec 005 names the 3.15 line's release `0.1.0a2`. The agent will prepare it (version bump, changelog, a green dry run of the release workflow) but will not push the tag until you say so (constitution §7).
- **Status, 2026-10-17:** ready. `__version__` is `0.1.0a2`, and the CHANGELOG's unreleased section covers specs 005 to 014. The dry run of `1f21dd0` passed every job, including the arm64 Linux rebuild with byte-identical `SHA256SUMS`. Before tagging, the agent will run one security review of the release against the threat model, by a fresh agent. Releasing is one command (`release/version.py release`) once you say yes.
- **Answered 2026-10-17:** Yes, after a security review of the release against the threat model by a fresh agent; then the agent tags v0.1.0a2.

### 7. A `wasi-python run` command line?

- **Asked:** 2026-10-16. **Source:** the principal engineer's memo.
- **The question:** §3 says the project "ships no shell". Is a thin command that runs a program and prints a JSON result part of the runner (allowed) or a shell (not)? The agent reads it as the runner but does not build it until you answer.
- **Answered 2026-10-17:** Yes, as part of the runner: `wasi-python run` prints one program's result as JSON. The constitution's §3 records it.

### 8. numpy's `.npy` files

- **Asked:** 2026-10-16. **Source:** `research/2026-10-16-what-data-folders-the-packages-need.md`.
- **The fact:** `np.save` and `np.load` of `.npy` files fail in 0.1.0a1 because numpy calls `os.dup`, which WASI preview1 does not have. Zero patches rules out a local fix.
- **The question:** may the agent file an upstream numpy issue (an outward-facing action)? The agent writes the issue text into the repository and records the failure as a known gap.
- **Answered 2026-10-17:** File it, after the owner reads and approves the text (drafted as an artifact).

### 9. Licences for sqlite3, bz2 and lzma

- **Asked:** 2026-10-17. **Source:** `research/2026-10-17-sqlite-bz2-and-lzma.md`.
- **The question:** constitution §4.12: "Nothing with a licence the owner has not approved is linked in." Building these three modules in links: SQLite 3.54.1 (public domain: its header's blessing, no licence file), bzip2 1.0.8 (its own BSD-style licence), and liblzma from xz 5.8.4 (0BSD). Do you approve them?
- **What waits:** spec 007 (sqlite3, bz2 and lzma) is written and reviewed, but not built, until you answer. The experiment shows all three build with no patch; bz2 and lzma match native byte for byte; sqlite3 works with one limit (one connection writes at a time, through a lock directory beside the database).
- **Answered 2026-10-17:** Approved: SQLite (public domain), bzip2 (BSD-style), liblzma from xz (0BSD). The constitution's §4.12 records it; spec 007 is unblocked.

### 10. Turn on private vulnerability reporting?

- **Asked:** 2026-10-17. **Source:** spec 009 (`specifications/009-release-security.md`).
- **The question:** `SECURITY.md` asks reporters to use GitHub's "Report a vulnerability" button, which works only when private vulnerability reporting is on in the repository's settings (Settings → Code security). May the agent turn it on (`gh api -X PUT repos/ClayGendron/wasi_python/private-vulnerability-reporting`), or will you?
- **Meanwhile:** `SECURITY.md` is not written yet; it waits on this answer (spec 010, the other thing it waited on, landed 2026-10-17), so that its reporting route works.
- **Answered 2026-10-17:** Yes, the agent turns it on (`gh api`), then writes `SECURITY.md`.

### 11. File a wasmtime-py issue about its shared callback tables?

- **Asked:** 2026-10-17. **Source:** spec 010's build review, finding 1, and spec 011 (`specifications/011-concurrent-calls-share-nothing.md`).
- **The fact:** wasmtime-py keeps the Python callbacks of `define_func` and of custom WASI output in two process-wide tables with no lock. Threads that define or free them at once corrupt the tables (EXECUTED: after a few hundred concurrent calls every later call raised). Spec 011 works around it in the runner, without patching wasmtime-py.
- **The question:** may the agent file the issue (an outward-facing action)? The agent writes its text into spec 011's landing notes either way.
- **Answered 2026-10-17:** File it, after the owner reads and approves the text (drafted as an artifact).

---

## Memories stay in the repository, and the 0.1.1 release is pushed by the owner's agent

- **Asked:** 2026-10-26. **Source:** the orchestrating session's out-of-repo memory folder, and the release of 0.1.1.
- **The owner's decision (memories):** "please delete all memories from outside of this repo. Either update the agents.md file with ones that are important to remember when developing in this repo or let them be deleted. Update the agents.md to say never save memories outside of this repo, those details should stay in as commited details to reference later by all agents." Applied the same day: the memory files were deleted; the rules that mattered are in `../AGENTS.md` (asking the owner with the tool, permission grants run by the owner, no probing of third-party hosts, truthful trailers, worktrees and disk, docs without fluff, the badge row).
- **The owner's decision (0.1.1):** "please continue to work until 0.1.1 release is ready, and then get it to main and released to pypi", then "I am going to go to sleep, so please go ahead with the tag and push." A one-time delegation of constitution §5.5's owner-only push of `main` and the tag, for 0.1.1, to the orchestrating agent of the session that did the work; recorded again in spec 138's landing notes when the push is made. Later releases ask again.

## The scope of 0.1.2, and its release is pushed by the owner's agent

- **Asked:** 2026-10-27. **Source:** the orchestrating session's scope proposal, drawn from `research/2026-10-27-a-snapshot-the-embedder-chooses.md`, `research/2026-10-27-the-module-cache-refused-where-another-uid-owns-the-root.md`, `research/2026-10-27-a-code-review-of-the-runner-for-production-use.md`, the 0.1.1 security and structural reviews and the 0.1.1 landing notes' follow-ups.
- **The owner's decision (scope):** "approve, and pull in the deferred items if we can. also, there should be work on this branch that makes it in to 0.1.2", naming the branch `spec/144-a-session-is-always-ended` (specifications 144, 145 and 146 and the production-use review). The scope is `roadmap.md`, "0.1.2: the embedder's release": the embedder-chosen starting image (150) after a research spike, the module cache on a host where another uid owns `/` (147), the carried 141 to 143, 115 and 116, the three production-use specifications, two bundles of Lows (148, 149), the hygiene specification (151), and the stretch items 153 to 156 only if the release is not waiting on them.
- **The owner's decision (version):** 0.1.2, not 0.2.0, although the starting image adds a public argument.
- **The owner's decision (release notes):** "for the notes that go with the release, those need to be better. they should be like release notes that explain the value to the reader, right now ours are just a blob of text." Specification 152.
- **The owner's decision (the push):** "You may tag and push 0.1.2." A one-time delegation of constitution §5.5's owner-only push of `main` and the tag, for 0.1.2, to the orchestrating agent of the session that does the work, as for 0.1.1; later releases ask again.
