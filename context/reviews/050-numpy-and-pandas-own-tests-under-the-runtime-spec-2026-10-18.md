# Review of spec 050 before build: numpy's and pandas' own tests under the runtime

- **Reviewed:** `context/specifications/050-numpy-and-pandas-own-tests-under-the-runtime.md` as
  drafted at `9a98498` (main), with the memo it stands on,
  `context/research/2026-10-18-numpy-and-pandas-own-tests-in-the-guest.md`, and its evidence
  folder (`prototype/drive.py`, `batch2.py`, `hunt.py`, `probe.py`, `kit.txt`, `numpy.ini`,
  `pandas.ini`, the unit lists, the group tables, the non-pass lists, `numpy-traps.txt`).
  This is a voluntary pre-build review. §5.6 does not require one, because the spec changes no
  guest import or export, no artifact and no recipe. The spec asks for one because it changes
  how the judge admits failure.
- **Reviewer:** a fresh agent (Claude Opus 5.5). It did not write the specification or the memo.
- **Read:** `AGENTS.md`; the constitution (§4.1, §4.2, §4.8–§4.10, §4.12, §4.13, §5.2, §5.6,
  §5.7, §6); spec 002 (Decisions 3, 4, 5, 6, 11, and the "not machine-checked" list);
  `tests/known_gaps.toml` (header); `tests/harness/scoreboard.py` (whole), `needs.py` (whole),
  `guest.py` (whole), `plugin.py` (`metric`, the report hook, the judge-file and dirty logic),
  `paths.py` (`JUDGE_PATHS`, `judge_files`, `BUILD`, `DOWNLOADS`), `pins.py` (`source_pair`);
  `tests/checks/test_v1_5_rebuild_from_pins.py` (the tree check); `.github/workflows/release.yml`
  (the judge steps); `scripts/line.py` (for blocked handling); the frozen set's `MANIFEST`;
  `build/pandas-3.0.6/pandas/conftest.py:200–216`; `build/numpy-2.5.2/numpy/conftest.py:39–58`;
  `build/numpy-2.5.2/pytest.ini`; pandas' `pyproject.toml` `[tool.pytest.ini_options]`;
  pytest 9.0.3's `_pytest/compat.py:260–279`; question 89.
- **Executed** (scripts and outputs in this folder; `uv run` only; nothing in the repository
  changed):
  - **The kit's pins.** PyPI's JSON API for each of the seven releases: every wheel's URL and
    SHA-256 equal its `kit.txt` line, and the licences and `requires_dist` match Decision 2.
    The seven wheels, downloaded into `wheels/`: `shasum -a 256 -c` prints `OK` seven times.
  - **The staged tests are tarball members today.** Every file under every `tests` folder of
    `build/numpy-2.5.2/numpy` (except `_core/src`) and `build/pandas-3.0.6/pandas`, compared with
    the pinned tarball's member list: numpy 493 files, 0 not in the tarball; pandas 1,122 files,
    0 not in the tarball.
  - **The product's zip** (`s-0cdc7b2bd78db6f5`): `numpy/f2py/` 23 members, `numpy/typing/` 2,
    `numpy/_pyinstaller/` 2, `numpy/conftest` 0, `pandas/conftest` 0, any `tests` folder 0.
  - **A guest probe** (`scripts/probe.py`, `grant/judge/drive.py`): the frozen snapshot through
    the judge's own `tests/harness/guest.py`, imported read-only, with the kit and pandas' tests
    granted read-only at `/upstream`, Decision 5's options and pandas' fast selection.
    `pandas/tests/libs`: `exit 0`, fuel **22,453,233,702**, then again in a second process,
    **22,453,233,702** (identical); 1,063 passed. `pandas/tests/tslibs`: 590 passed, 1 failed,
    fuel 38,578,483,545 (drafting: 38.6 G). At collection's end the active hypothesis settings
    were `derandomize=True max_examples=15 database=None` (F8).
  - **The classes, recounted from the evidence** with Decision 10's regular expressions:
    frame 21, groupby 71, io/formats 21, io/parser 73 + 40, reshape 7, tslibs 1, nothing left
    over. numpy's non-pass list gives 8 / 3 / 3 / 1, 5 / 1 / 1, 8 / 1 / 2 / 1. All equal the
    table.
  - **The selection.** The 29 numpy test files absent from the drafting unit lists are exactly
    Decision 8's not-selected files (23 + 2 + 2 + `test_memmap` + `test_ctypeslib`).
  - **Full-judge times today** (READ from the lane's logs): `build/accept-033.log` 179.63 s,
    `accept-048.log` 239.14 s, `accept-036.log` 538.31 s.
  - I did not run the judge, nor any numpy session: nothing is built yet, and this review judges
    a design. The trap and numpy facts below are READ from the drafting evidence.

Two terms used below. A **class** is one `[[expected]]` entry: a named set of failing tests,
admitted by count and digest. **Admitted** means a failure the judge accepts without turning red.

## Findings, most severe first

### F1 (high). A second way to admit failures, under which a group with 268 failures shows as `pass`

**Evidence (READ).** Spec 002 gives every check one of five states (Decision 3). A check that
fails in a known way is a `gap`, never a `pass` (Decision 4). The scoreboard shows gaps on its
own lines: `· N gap`, `gaps close with: <closer> k`, and the `next:` line counts closers as work
(`scoreboard.py:render`). That is how an agent sees what is admitted and what closes it.

Spec 050's classes admit failures *inside* a check that then reports `pass` (Decision 10). The
drafting runs admit 31 + 3 numpy and 234 pandas failures, in 18 classes, across 9 of the 11
groups. After landing, the scoreboard would read `11/11 pass` for these groups. None of the 268
would appear in `gaps close with:` or in `next:`. The three follow-ups the memo names (the C
signatures, the zip's code names, patch 0001's draft) would close 196 of them, and nothing on the
scoreboard would point at them. The spec also drops "numpy/pandas test subsets" from the "not
machine-checked" line, so the scoreboard would claim more than it shows.

The strictness itself is honest (see "What holds"). The weakness is visibility. Rule 4 says
never weaken the judge to get a pass. This mechanism does not weaken an existing check. But it
creates a channel where admitted failures count as passes, and spec 002 is not amended to say so.

**Fix.** Do one of these, and amend spec 002's Decisions 3 and 4 in writing (as spec 029 amended
Decision 5):

1. **Preferred: reuse spec 002's gaps.** Keep the classes' `match`/`nodes` in the package TOML,
   since they sort failures. Add one check per class, `test_upstream_class[<group>-<class>]`. It
   reads the group's stream (a session fixture, so the guest runs once) and fails with one
   finding per node id. Each class is then one `known_gaps.toml` entry with its own closer. The
   count and digest are spec 002's, strict both ways as now. The scoreboard shows 18 gaps, with
   their closers in `gaps close with:` and `next:`. A fix moves a gap to `pass`, which is how
   spec 002 says every later spec lands. The group check stays `pass` when every failure falls
   in some class.
2. **At least: surface them.** Record an `admitted` metric per group (the number of class
   members). Rising is growth, which already turns red under today's ratchet direction. Add a
   scoreboard line that is never cut: `upstream: 62,569 passed · 268 admitted in 18 classes ·
   close with: memo 196 · README 69 · question 89 3`. Feed the closers into `next:`.

Either way, name `tests/upstream/*.toml` in AGENTS.md rule 4 and in `context/progress/README.md`
beside `tests/known_gaps.toml`: an allowance file the judge's acceptance must justify.

### F2 (medium). A fall in `passes` hides behind any fuel growth, and is printed as "GREW"

**Evidence (READ).** Decision 12 accepts a fall in `passes` with `--accept-growth`. That flag
is a single reason for the whole run. In `accept()`, a growth reason makes every metric of every
check take its new value (`keep_old = … and not growth_reason`). Specs 039 and later change the
zip, which grows the fuel of every snapshot check (the spec says so under "Depends on"). Each of
those landings needs `--accept-growth "the zip grew"`. The same flag would then silently accept
a fall of 40 passes in `pandas-io-parser`. The scoreboard prints at most three `GREW` lines
(`render`, `ratchet.growth[:3]`), so the fall can be the fourth line of forty. Spec 002's ratchet
also uses `growth` for "the wrong way", and a fall in passes would print as `GREW … passes
62569 -> 62529`.

Rule 5 says no pass is lost quietly. This path loses one quietly.

**Fix.**
- Keep falls in passes in their own ratchet list (`fewer`), red on their own.
- Print each as `FEWER <node>: passes <old> -> <new>`, before the `GREW` lines and never cut.
- Accept a fall only with its own flag, `--accept-fewer-passes "<why>"`. Record it in its own
  history field.
- Say where a rise is reported. It must not go into `Ratchet.gained`, which counts checks:
  criterion 10's "gained 19" would be wrong otherwise.
- Criterion 6: add the case "fuel growth accepted, passes fall in the same run: still refused".

### F3 (medium). A digest says *that* the admitted set changed, never *which* test joined it

**Evidence (READ).** A class stores `count` and the first 12 hex digits of a digest of its node
ids (Decision 10). The finding reads `class <id>: expected <n> (<digest>), saw <m> (<digest>)`.
Say a product change breaks one more pandas test whose message happens to match "Warning not
set with correct stacklevel". The builder sees `expected 71, saw 72`. The fix is to write `72`
and the new digest. The judge-hash change then asks for `--accept-judge`, and the reviewer sees a
diff of two numbers. Nobody can tell from the diff which test was admitted, or whether it really
fails for the class's reason. The spec's argument against a list ("a 193-line entry") weighs
file length against auditability. Rule 4's review needs the latter.

Churn makes this worse. The 3 `no-dup-file-left-open` errors are unraisable-exception reports.
pytest attaches each to whichever test is running when the file object is collected
(`numpy-fast-nonpass.txt`: they land on the same `test_fromfile*` nodes today). Any change to
earlier tests can move them, and the digest moves with them.

**Fix.**
- Keep each class's sorted node ids in a judge file, one per line:
  `tests/upstream/expected/<group>/<class>.txt` (268 lines in all). The count and digest are
  computed from it.
- The finding names the ids added and removed: `class zip-code-names: +pandas/tests/…::test_x,
  -…`.
- An edit then shows in `git diff` as the exact tests admitted or released, and the review sees
  them.
- Keep `match` as a sanity rule: every listed node's reason must still match its class's
  expression. Otherwise a `nodes` list could admit anything.

### F4 (medium). The tests are not tied to the artifact under judgment, and files a build adds are not checked

**Evidence (READ, EXECUTED).** The harness finds the tests through `pins.source_pair`, under
`paths.BUILD` (the repository's `build/`). It finds the binary through `$WASI_PYTHON_ARTIFACTS`
or `build/artifacts`. Nothing compares the two. The frozen set's `MANIFEST` names exactly what it
was built from: `pin d482d171… numpy-2.5.2.tar.gz`, `pin 66b07ef7… pandas-3.0.6.tar.gz`, `recipe
521d4114… recipes/patches/numpy-2.5.2/0001-npy-files-without-dup.patch`. After a re-pin, or
with a frozen set older than the tree, numpy 2.6's tests would run against numpy 2.5.2's binary.
The resulting failures would be read as product defects.

Separately, spec 020's tree check judges only files the tarball holds. "Files a build adds inside
a source tree" is on the "not machine-checked" line. Decision 3 copies whole folders, so a stray
`conftest.py` or test file under `build/pandas-3.0.6/pandas/tests` would run in the guest and
could change outcomes. Today there is none (EXECUTED: 493 + 1,122 files, 0 outside the tarballs).
The spec's sentence "so the tests are the pinned release's" holds only for files the tarball
holds.

**Fix.**
- Before staging, compare the tarball and the patch hashes against the artifact's `MANIFEST`
  `pin` and `recipe` lines. On any difference the check fails: `tests from numpy-2.6.0.tar.gz,
  artifact built from numpy-2.5.2.tar.gz`. A need would not do here: the mismatch is a judge
  input error, so it must fail, not block.
- Stage only paths that are tarball members, or files a recorded patch touches (`tarfile`
  member names are cheap to read once per run). Criterion 9 or a unit check shows that a stray
  file in a scratch tree is not staged.

### F5 (medium). The trap check cannot hold for a trap at collection, `castingimpl-arraymethod`

**Evidence (READ).** Decision 9 asserts that "the last test the stream started begins with the
entry's node id". The stream writes `S` only from `pytest_runtest_logstart` (Decision 11).
`test_arraymethod.py` traps while pytest collects it, before any test starts. The drafting hunt
records exactly that: `numpy-traps.txt`, first line, `CRASH None | 0: … cfunction_call`. Run
alone, the entry produces no `S` line, and criterion 4 fails for it as written.

**Fix.**
- The driver also writes `C <node id>` from `pytest_collectstart`.
- The trap check asserts that the last `S` or `C` line with no matching `R`/`X` begins with the
  entry's id.
- Add this case to criterion 4's unit checks: a stream that ends after a `C` line.
- The spec labels this entry's cause INFERRED. With the trap's cause kept (Decision 14), the
  builder can record frame 0 and mark it EXECUTED.

### F6 (medium-low). Criterion 8's budget is broken by Decision 8's own caps

**Evidence (READ, arithmetic).** The group caps sum to 3.0 + 2.0 + 2.7 + 5.1 + 7.0 + 1.6 + 1.3 +
0.81 + 0.58 + 0.28 + 0.34 = 24.71 × 10¹¹. The seven trap caps add 7 × 5 × 10¹⁰. That makes
**2.82 × 10¹²**. Criterion 8 requires "the sum of the groups' caps and the trap caps is at most
1.8 × 10¹²". Decision 8's 1.8 × 10¹² is a budget for fuel *spent* (1.62 T measured), not for caps.

**Fix.**
- Bound the caps in criterion 8 by what they are: at most 3 × 10¹².
- Keep the 1.8 × 10¹² spent-fuel budget as a review rule. Each landing's notes sum the recorded
  `fuel` metrics of the 18 checks, and a sum over the budget states why.
- Optionally, the rules check can read `accepted.json` and sum the accepted fuel per platform.

### F7 (medium). The builder's worktree cannot run the groups, and the spec does not say how it will

**Evidence (READ).** `paths.BUILD` and `paths.DOWNLOADS` are the worktree's own folders. No
environment variable redirects them. In a worktree outside the repository (§4.14), the needs
`source tree numpy` and `source tree pandas` are unmet, so all 18 checks are `blocked`.
Spec 036's landing notes show this pattern ("The 11 blocked are this worktree's (source trees,
…)"). Rule 6a says the builder judges against the frozen artifact set its class allows.
Criteria 2, 3 and 7 must be executed by the builder, but the spec never says how. Otherwise the
lane would be the first to run 1.6 T of fuel.

**Fix.** Write the builder's setup into the Design. For example, the builder places read-only
links to `downloads/numpy-2.5.2.tar.gz`, `downloads/pandas-3.0.6.tar.gz`, `build/numpy-2.5.2`
and `build/pandas-3.0.6` in its worktree, runs `fetch.py` there, and sets
`WASI_PYTHON_ARTIFACTS` to the frozen set. Its landing notes record the scoreboard line showing
the 18 checks ran. Check that the judge's conftest walk and `dirty_path` ignore those links
(`build/` and `downloads/` are in `NOT_SOURCE`, which suggests they do).

### F8 (low-medium). pandas' sessions do not use the profile the spec names; they are derandomized only by import order

**Evidence (EXECUTED, READ).** `pandas/conftest.py:206–216` registers and loads its own profile,
`pandas_ci` (`max_examples=15`, two health checks suppressed). pytest imports that conftest
after the driver loads `judge`. hypothesis's `register_profile` inherits unspecified settings
from the default that is current when it is called. So `pandas_ci` inherits
`derandomize=True` from `judge`. The probe printed `derandomize=True max_examples=15
database=None` at the end of collection. Decision 6 says pandas gets numpy's values. In fact it
gets pandas' values, and it is deterministic only because the driver loads `judge` first. If the
driver loaded `judge` after pytest started, or if a later pandas registered `pandas_ci` with a
`parent=`, the examples would come from the seeded random stream. They would still be the same
from run to run. But they would shift whenever an earlier test drew one more random byte, so
fuel and outcomes would change for no visible reason.

**Fix.**
- Decision 6 states it plainly: numpy sessions use `judge`; pandas sessions use pandas'
  `pandas_ci`, layered on `judge` so that `derandomize=True` and `database=None` hold.
- The driver writes the active settings into the stream once collection finishes (`P
  derandomize=… database=…`).
- A group whose stream shows `derandomize=False` or a database is a finding.

### F9 (low-medium). The lane can accept with all 18 checks unrun, and their passes kept

**Evidence (READ).** `upstream kit` and the source trees are not protected needs (Decision 13;
spec 002, Decision 6). If the kit or a tree is missing on the lane, the 18 accepted passes become
"unrun locally". `accept()` does not refuse that, and `scripts/line.py` does not look at it.
`accept()` then keeps each check's earlier metrics, `passes` included. A landing that breaks a
numpy function the suites would catch could land green on a lane machine that lost
`build/upstream/wheels/`. The spec's safeguard is a sentence in the landing notes.

**Fix (judge-only, no `scripts/` change).**
- The scoreboard's ratchet line already counts `unrun locally`. The landing notes cite that line
  showing `unrun locally 0` for `test_v1_3_upstream_suites.py`. Make this a written lane rule in
  `context/progress/README.md`.
- Alternatively, make the three needs protected on a lane run. If a later spec gives the lane
  its own flag, use it.
- Also name the release question for later. The release job runs `uv run pytest` with the kit
  absent, so these checks are blocked there (`release.yml:70`). Before a release, someone should
  confirm that `history.jsonl` holds an accepted run of the suites on the release's artifact
  hash, as `three systems` does for platforms.

### F10 (low). The kit's pinning is sound; give it the precedent, a rules check and a safe unpack

**Evidence (EXECUTED, READ).** All seven URLs and hashes equal PyPI's published digests. The
downloaded wheels verify. The argument for keeping the kit out of `downloads/SHA256SUMS` holds:
`assemble_artifacts.py` turns every line there into a `MANIFEST` `pin`, which would change the
artifact set. But §4.2's text names `downloads/SHA256SUMS` for "every … tool and pure-Python
dependency", and AGENTS.md repeats it. The spec does not cite the precedent that makes judge-only
pins acceptable: spec 002's Decision 11 pins the oracle in its own `uv.lock` under `tests/`, and
the judge's own pytest is pinned in `uv.lock`, not in `SHA256SUMS`.

**Fix.**
- Cite spec 002, Decision 11 as the precedent: the kit is judge input, pinned in the judge,
  hashed, and in `JUDGE_PATHS`.
- Add a line to the rules check (criterion 8): every `kit.txt` line is 64 hex digits, two
  spaces, and an `https://files.pythonhosted.org/` URL whose basename is a `py3-none-any` (or
  `py2.py3-none-any`) wheel.
- `fetch.py` downloads to a temporary name and renames only after the hash matches.
- The harness unpacks with `zipfile` and refuses absolute member names and members with `..`
  (§4.8: downloads are untrusted, even hashed ones).
- If the owner wants §4.2's letter matched, one line in the constitution's §4.2 ("judge-only
  inputs are pinned in the judge, by URL and SHA-256") would settle it. The reviewer does not
  think this is needed, because the oracle already set the practice.

### F11 (low). Staging: only the groups' folders, once per run, and a guard on `__path__`

**Evidence (READ, EXECUTED).** Decision 3 stages "every folder named `tests`". That includes
`f2py/tests`, `typing/tests` and `_pyinstaller/tests`, which no group runs (672 K and 1.0 M for
the first two). It does so for each of 18 sessions: about 20 MB per session, roughly 400 MB of
copies per full judge. The grant is read-only, so one staging per run is enough.

Appending to `__path__` is safe today. The product's entry comes first, and every staged
directory is either a package the product has (EXECUTED: `numpy/f2py/` 23 members,
`numpy/typing/` 2, `numpy/_pyinstaller/` 2 in the zip) or a `tests` folder. So nothing shadows
anything. But nothing enforces it.

The memo and Decision 4 also say numpy's test folders have no `__init__.py`. Twelve of the
thirteen do; only `_core/tests` lacks one (READ, `find`).

**Fix.**
- Stage the groups' and trap entries' folders only, once per run, under
  `build/harness/upstream/<run>/`.
- At session end the driver lists every `sys.modules` entry whose `__file__` starts with
  `/upstream/tests/`. Any entry that is not under a `tests` package or `pandas.conftest` is a
  finding: a product module came from the grant.
- Correct the `__init__.py` sentence in the memo and in Decision 4.

### F12 (low). `passes` is a floor, not an identity

**Evidence (READ).** A count cannot see a substitution: one test passes → skipped while another
skipped → passes. Decision 12's "so no pass is lost quietly, even to a skip or a deselection"
claims more than a count can show. The skip set is deterministic on pinned tests, so a stronger
record is cheap.

**Fix.**
- Record a `passed_digest` (12 hex digits of the sorted passing ids) per group in
  `build/progress/latest.json`. It is informational, not ratcheted.
- Weaken the sentence to "no fall in the number of passes goes unaccepted".

### F13 (low). Evidence drift: the driver that ran is not the one in the evidence, and the invocation differs

**Evidence (READ).** `batch2.py` and `hunt.py` run `/t/tests/_judge/drive4.py`. The evidence
holds `drive.py`. The numpy numbers come from explicit file lists (`np_units_fast.txt`), not from
directories with `--ignore`. The order also differs: the list puts `test_hermite_e.py` before
`test_hermite.py`, and pytest's directory sort puts them the other way round. Decision 8 states
"about 13 minutes" for all of pandas with no label (§4.10).

**Fix.**
- Copy `drive4.py` into the evidence, or state that `drive.py` is the same file.
- Note in Decision 8 that the drafting fuel came from file lists. The builder's first run on the
  specified argv sets the baseline. Criterion 3's pass counts should match; fuel may differ
  slightly.
- Label the 13 minutes INFERRED.

### F14 (low). Upstream's `--strict-markers` and `--strict-config` are dropped from the "transcribed" configuration

**Evidence (READ).** numpy's `pytest.ini` has `addopts = -l -ra --strict-markers
--strict-config`. pandas' `addopts` has `--strict-markers --strict-config` too. Decision 6 says
"transcribed" but keeps neither, and gives no reason. Without `--strict-markers`, a misspelled
marker in a test, or in the driver's registration, passes silently.

**Fix.** Pass both, as upstream does, or write why not. For example, if `--strict-config`
rejects a key, say which one.

### F15 (low, a benchmark fact for the owner). The full judge roughly doubles

**Evidence (READ, INFERRED).** The lane's last full judges took 180 s, 239 s and 538 s. The
spec's six minutes (INFERRED from two groups at about 5 G fuel a second) is 0.7 to 2 times that,
for every landing. The release workflow's runner time does not change, because these checks are
blocked there. The cost is the owner's to weigh, not a defect.

**Fix.**
- The landing notes record the full judge's time before and after, as a benchmark fact.
- If the time is too much, the spec's knob is the pandas groups, not the strictness.

## What holds

- **Strict both ways is honest (READ, EXECUTED).** A class's tests, counted and hashed, differ
  by one either way and the check is red. A failure no class takes is red. A trap, out of fuel,
  a collection error, `INTERNALERROR` or a bad exit code is never admitted. The TOMLs live under
  `tests/`, so every edit is a judge change that needs `--accept-judge` (`paths.JUDGE_PATHS`).
  Recounting with the spec's own expressions reproduces every class count exactly. Not using
  `xfail` markers or `known_gaps.toml` per test is right. F1 and F3 are about visibility and
  auditability, not about looseness.
- **No product change, and not build-class (READ).** The spec touches no `scripts/`,
  `recipes/`, `downloads/SHA256SUMS` or workflow. It reads `build/` and the frozen set and writes
  only under `build/`. The guest gets one more read-only grant, which is the embedder-neutral
  mechanism spec 017 already judges. §4.4 holds: pytest is pure Python in the guest, and no
  import is added.
- **Determinism (EXECUTED).** The same group gives the same fuel in two processes, to the
  instruction (22,453,233,702 twice). The drafting pairs differ by 221 and 68 instructions.
  Test order is pytest's sorted collection. `tmp_path` is the fixed `/tmp/pytest` in a fresh
  root. The guest's random stream and clock are the judge's own, so `mkstemp` names repeat
  (`/tmp/tmpbo8hd74k` in the evidence). Hashing is seeded through `random_get`.
- **The traps (READ).** The hunt's method (deselect the last started test, run again) is sound.
  The four C functions and their registered signatures are cited to lines. Making a trap that
  stops trapping fail the check ("remove the entry") is the right way to keep traps honest.
- **The selections are upstream's own** (`numpy.test()`'s `not slow`, `pandas.test()`'s
  marker expression, `--no-strict-data-files`). The pandas choice is reasoned from the product
  (the golden job's path, then the frame core, then the C layers). Leaving out the C-test-module
  files under question 89 keeps the product's bytes untouched.
- **One builder (INFERRED).** A harness module, a guest driver, two TOMLs, a ratchet change, 19
  checks and their unit checks: one builder's work. F1's preferred fix adds 18 small checks and
  18 gap entries, which is still one builder.

## Constitution checks

- **§4.1 (patches):** met. No source change. The two patch-0001 behaviours go to the patch's
  upstream draft (Decision 18).
- **§4.2 (pinned and hashed):** met in substance. All seven wheels match PyPI (EXECUTED). The
  pins live in the judge, not in `downloads/SHA256SUMS`. Cite spec 002's oracle as precedent
  and add the rules line (F10).
- **§4.4 (two imports):** met. Nothing is added to the guest.
- **§4.8 (downloads untrusted):** met in design: wheels unpack under `build/`, and their code
  runs only in the guest (EXECUTED in the probe). Guard the unpack (F10).
- **§4.9 (counts, never time):** met. Every criterion counts tests, findings, fuel or bytes. The
  six minutes are a benchmark fact (F15).
- **§4.10 (claims carry evidence):** mostly met. The driver that ran is missing from the
  evidence; the `__init__.py` claim is wrong; one time estimate is unlabeled (F11, F13).
- **§4.12 (licences):** not reached. The kit ships in neither the release nor the wheel.
- **§4.13 (tooling):** met. Nothing is added to `pyproject.toml`; `uv run` throughout.
- **§5.2 (no open questions):** met. Question 89 is the owner's, and the spec builds without it.
- **§5.6 (pre-build review):** not required. This review was asked for.
- **§5.7 (one lane):** met, but say how the builder runs the groups (F7) and how the lane proves
  they ran (F9).
- **AGENTS rule 4 (never weaken the judge):** no existing check is weakened. The new admission
  channel must be made as visible as gaps (F1) and as auditable as a diff (F3).
- **AGENTS rule 5 (no pass lost quietly):** not yet. A fall in passes rides on any fuel growth
  (F2), and a substitution is invisible to a count (F12).

## Disposition (filled in by the author, then confirmed by the reviewer)

## Verdict

**Not ready to build until F1 to F7 are written in.** The method is right, and the drafting
work is careful. pytest runs in the guest with six reasoned adaptations. The tests come from
pinned trees. The traps are found and named down to the C line. The classes are strict both
ways. The admission machinery, though, must be no less visible than spec 002's gaps (F1). It must
show which test was admitted, not only that a digest moved (F3). Its new metric must not be
waved through by an unrelated `--accept-growth` (F2). Three more are mechanical: tie the tests
to the artifact's `MANIFEST` (F4), let a collection-time trap be named (F5), and fix criterion
8's arithmetic (F6). The builder also needs a written way to run the groups in a worktree (F7).
F8 to F15 are low, and each has a one-paragraph fix.

One line: the suites belong in the judge and their strictness is honest, but make the admitted
failures show on the scoreboard as gaps do, list them by node id, give falling passes their own
flag, and tie the staged tests to the artifact's `MANIFEST` before building.
