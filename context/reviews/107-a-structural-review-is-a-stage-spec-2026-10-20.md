# Review of 107 — A structural review is a stage (pre-build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (pre-build reviewer for the chain 102–107); not the author
- **Reviewed:** the specification as drafted
  (`context/specifications/107-a-structural-review-is-a-stage.md` on `claude/gallant-ride-9nxxmn`,
  read untracked over `a9064a2` and committed unchanged as `e364b99` while this review was written)
- **Run:** none (pre-build review of the draft)
- **Re-ran:** `uv run pytest tests/checks/test_rules.py -k "specifications or open_question" -q
  -p no:cacheprovider` → 3 passed, 41 deselected, exit 0 (the draft has its header fields and
  sections and none of the three rejected words or a questions heading: EXECUTED). The nine measurement commands of Design
  B's table, each run from the root on `a9064a2` (EXECUTED, below). The scanner code of Design D1
  pasted into a scratch script with the unit rows of Design D3 and run with `uv run python`
  against them and against the real tree (EXECUTED; `/tmp/claude-0/-home-user-wasi-python/
  a7a0f302-7717-538b-8fac-46c5fd7843f5/scratchpad/probe107.py`). No build, no dispatch, no judge
  beyond those node ids.
- **Box:** 25 minutes (parallel-safe); the whole checklist was worked.

## Acceptance criteria against evidence

There is no diff, so each criterion is judged for whether it is countable as written and
whether its anchors exist in the tree.

1. **The texts are in the tree, verbatim** — countable: every anchor exists. AGENTS.md:43
   "Nothing lands unreviewed" and :48 "Commit or push only when asked" bracket A1's place; rule
   8's two lines AGENTS.md:173–174 are exactly A2's "before" text (EXECUTED, grep). README
   items 4 and 5 (`context/reviews/README.md:40–42`) bracket 4a. The owner's file reads "## Open"
   then "None." (`context/questions-for-the-owner.md:9–11`). `roadmap.md:131` is the "Reserved:
   101" paragraph under "Where 0.1.0 stands" (:56); `roadmap.md:236` carries E2's "before" text;
   `CHANGELOG.md:7` is `## 0.1.0a8 — unreleased` (EXECUTED). One text differs from its own
   decision (L3).
2. **Check (a) seen failing first** — countable: the command's shape works (`from harness import
   scan` with `tests` on `sys.path`: EXECUTED in the probe). On the tree today the pasted
   `structural_review_errors("0.1.0", context/reviews)` returns exactly
   `['0.1.0 is a release; reviews/ has no 0.1.0-structural-review-<date>.md']` and
   `("0.1.0a8", …)` returns `[]` (EXECUTED). `__version__ = "0.1.0a8"` at
   `src/wasi_python/__init__.py:34` (READ).
3. **Check (b) seen failing first** — countable; the fixture case `112-c.md` fails as the
   specification says (EXECUTED). On the real tree today it returns `[]`, but only because 107
   is drafted: marked built, 107 itself trips it (M3).
4. **The unit rows, each seen failing first** — countable; every assertion of D3's two rows
   passes against the pasted code (EXECUTED: "D3 row 1: every case passes", "D3 row 2: every
   case passes"). `SPEC`, `write` and `work` exist as the specification describes
   (`tests/unit/test_scan.py:13`, `:203`; `tests/unit/conftest.py:14`: READ). The
   `AttributeError` on the base is INFERRED (no `structural_review_errors` in
   `tests/harness/scan.py` today: EXECUTED, grep).
5. **No verdict moves** — countable through `sameness.py` (`tests/harness/sameness.py` exists:
   EXECUTED). INFERRED that only the two rows and the unit count move: the design touches no
   existing check, allowance, golden or progress file.
6. **The shape scans are green with the new texts** — met on the draft (EXECUTED, "Re-ran").
   INFERRED for the pasted texts: none contains a word the scan rejects, and the only heading
   with "question" in it is in the owner's file, which the scan does not read.
7. **Nothing under `src/` changed** — countable; `git diff --stat 30e9b41 a9064a2 -- src` is
   empty today (EXECUTED).
8. **The release workflow: no dispatch of its own** — consistent with the memo's section 8
   (one dispatch on the chain's final tip, the owner, 2026-10-20: READ). Its "Windows included"
   line is wrong (L2).

Facts the specification labels EXECUTED, checked on `a9064a2` (all EXECUTED by this review):
`runner.py` 6,241, `tools.py` 2,450, `mounts.py` 2,235, 11,423 in all; functions over 80 lines
`runner.py` 6, `tools.py` 2; mutables and locks 46 + 1; private-API lines 15/11/1; platform
branches 22, all in `runner.py`; 59 distinct patched private names, `runner._ctrl_c_watched` 8
and `_remove_tree` 5; 349 `Any`, 12 ignores; 315 and 37 citations. `Version.parse("0.1.0")
.is_prerelease` is `False`, `"0.1.0a8"` is `True`. `grep -ohE 'question (1[0-9][0-9])'
context/*.md | sort … | tail -1` gives `question 107` (`decisions.md:78`), so 108 is the next
free number. `grep -rn 'security review' tests/checks tests/harness` finds docstrings only. All
agree with the draft. One EXECUTED claim does not (M3).

The module names `_process.py` (104, Decision 1), `_wasmtime_ffi.py` (102, Decision 1) and
`_platform.py` (106, Depends on; 102:131) are those the drafted specifications give (READ), and
107 states them as dependent: "if one lands under another name, the rule names the landed one"
(107:84–85). 103 is not in the tree, so its check (the size ceiling) is READ from the memo's
section 8 table only; 105 appeared, untracked, while this review was written and is read below
where it names 107.

## Findings, most severe first

1. **Three checks are handed to 107 by its siblings and handed back by 107**
   (`context/specifications/107-…:224–226`, `:80–82`, `:706–708`;
   `context/specifications/104-…:258–266`; `context/specifications/105-…:305`, `:564–565`) —
   Medium. 107's Decision 5 names "spec 104's seam rule" as the letter behind trigger 4 and
   "spec 103's size ceiling" behind trigger 5, and its Scope puts "the structural fixes and their
   checks (specs 102 to 106), including the size ceiling's number, the function-length ceiling
   the memo suggests" out as theirs. The siblings say the opposite (READ): 104's Decision 4,
   "the check that enforces the rule (an AST walk of `tests/` for `monkeypatch.setattr(<module>,
   "_name", …)` … against an allowance list) is **spec 107's**", with 104's Decision 5 adding
   only the lock and mutable checks (104:314); 105's "Where it meets" and Scope, "**107** gets a
   rules check to extend (the memo's section 5: a module size ceiling)" and "a module size
   ceiling, a function length ceiling (the memo's section 5: spec 107)". 103 is not in the tree.
   As the chain stands, the seam check, the size ceiling and the function ceiling each have no
   builder, so triggers 4 and 5 would land with no check behind them, which Decision 1 itself
   calls "a rule the judge cannot see"; and no specification in the tree carries the memo's "no
   function over 80" (`grep -n "over 80\|80 lines\|function-length" context/specifications/
   10[2-6]-*.md` finds only 105's hand-off: EXECUTED).
   Failure: a change adds `monkeypatch.setattr(runner, "_new_hook", …)` or a 90-line function
   after the wave → no rules check fails; only the one-line item 4a can catch it.
   Evidence that closes it: each of the three checks has exactly one builder in the chain's
   texts (107's Design D gains the ones 107 takes, each with its unit row and its failing-first
   criterion; the siblings' hand-off lines are amended for the ones they keep), or 107's Scope
   says in so many words that the function ceiling is a measurement (R7) only, and 105's line
   agrees.
2. **The lane's order at 0.1.0 contradicts AGENTS.md rule 6b** (`…107-…:186–196`; `AGENTS.md`
   rule 6b; `release/version.py:240–248`) — Medium. Decision 4 orders: dry run on main's X
   (version `0.1.0a8`), then one commit with the review, `bump --to 0.1.0` and the CHANGELOG
   date, then the fast tier, then the tag. `_bump` writes `src/wasi_python/__init__.py`
   (version.py:245–248: READ), and rule 6b exempts only `context/`, `CHANGELOG.md` and
   `README.md` after a dry run: "any other file means a new dry run". The alphas never met this
   because their string was in the tree all cycle (`2737b29 Release 0.1.0a7` touched only
   `CHANGELOG.md`: EXECUTED, `git show --stat`); the final version is bumped at the release, so
   the specification's own argument for the gate ("turns red at exactly the moment the gate
   applies … which rule 6b allows after the dry run", :186–189) is wrong on its last clause.
   Failure: the lane follows Decision 4 → the commit tagged is one the release workflow never
   dry-ran with `0.1.0` in it, or the lane obeys 6b and dispatches again on a commit whose
   check is red because the review is of "the commit the dry run passed", which is now one
   dry run behind.
   Evidence that closes it: Decision 4's bullet and the template's "Reviewed" line say the
   review is of the commit before the bump (whose `src/` is the one tagged), committed together
   with the bump and the CHANGELOG date; the dry run runs on that commit; the tag follows
   `release/version.py release`'s own CHANGELOG-only commit, which 6b allows. The check's
   design needs no change for this.
3. **Check (b) fires on 107 itself, and the EXECUTED grep it rests on is not empty**
   (`…107-…:17`, `:205–207`, `:547`) — Medium. The Kind line reads "By Decision 1's own
   definition it is not structural", and `"structural" not in kind[1].lower()` is a substring
   test: with the Status changed to `**built 2026-10-20**` the pasted code returns
   `['107-a-structural-review-is-a-stage.md: structural and built, but cites no
   reviews/107-<slug>-spec-<date>.md']` (EXECUTED, the probe). The claim "`grep -rn structural
   context/specifications AGENTS.md context/reviews/README.md` is empty" cannot have been run on
   a tree holding 107 (the file's title contains the word; also 104:264, 106:29, 106:441), so it
   is reported as run where it was not (constitution §4.10). The practical effect is small (107
   will cite this review once built, which clears it), but the check's stated property, "no
   existing specification trips the check", is false for the specification that adds it.
   Fix text: match the token Decision 1 asks for, `re.search(r"\*\*structural\*\*",
   kind[1])` (or `\bstructural\b` not preceded by `not `), with a unit case for "not
   structural"; reword :17 to "it adds no module, no global, no seam and no private-API use"
   without the word; and replace :205–207 with the grep's real output on this tree, restricted
   to Kind lines (`grep -rn '^- \*\*Kind:\*\*' context/specifications | grep -ci structural`
   gives 1, this file).
4. **The Status test matches `built` anywhere in the line** (`…107-…:550`) — Low. A drafted
   specification whose Status reads "drafted 2026-10-21, to be built on 106's tip" trips the
   check (EXECUTED, the probe's `115-g.md` case). `landed_review_errors` uses
   `startswith("landed")` (`tests/harness/scan.py:394`). Fix text: `if not re.match(r"(built|
   landed)\b", status): return []`, and one more unit assertion for the drafted-but-says-built
   case.
5. **"Windows included" is wrong for `test_rules.py`** (`…107-…:776–778`) — Low.
   `test_rules.py` runs in the `own-rest` shard (`rest = true`, `systems = ["macos", "linux"]`;
   `tests/release_shards.toml:71–78`, spec 063 Decision 18: READ). Fix text: "The two checks run
   in the `own-rest` shard on macOS and Linux, where `test_rules.py` runs (spec 063, Decision
   18: not on Windows); they read files only."
6. **A1 drops `platform.system()` from the platform-branch trigger** (`…107-…:296–297`
   against `:78`) — Low. Decision 1 lists `sys.platform`, `os.name`, `platform.system()`; the
   AGENTS.md bullet lists two of the three; the measurement command (:400) greps all three. Fix
   text: in A1, "(`sys.platform`, `os.name`, `platform.system()`)".
7. **The 45-minute box reads "the whole of `src/` is read"** (`…107-…:137`, `:361–363`) —
   Low. The memo read 11,423 lines and states no box (its header, READ); the build-class box is
   45 minutes. As written the box cannot hold the reading it promises. Fix text: "45 minutes: the
   measurements first (one command each), then the diff of `src/` since the last structural
   review and the modules whose measurements moved; the whole of `src/` only when no structural
   review precedes it (the first compares with the memo, which read it whole)".
8. **Note, no rank.** `VERSION_LINE` in D2 duplicates `release/version.py:35`;
   `test_the_version_is_released_by_the_book` (`tests/checks/test_rules.py:230`) already loads
   that module through `importlib`, and `version.read_version(INIT.read_text())` would give the
   same string without a second regex. The duplication is harmless; the builder may keep it.

Judgements the task asked for, in one line each:

- **The trigger list** (Decision 1) is precise enough: five triggers, each the predicate of a
  rules check, each with a named module; an ordinary runner change (a fix inside a function, a
  new record field, a limit's default) trips none of them, so no false positive on the common
  case. Its soft spots are trigger 4 (M1: no check behind it as the chain stands) and the
  substring match on the Kind line (M3); trigger 5's check is M1's too.
- **The release gate** keys on `RELEASE_VERSION = ^\d+\.\d+\.\d+$`, which agrees with
  `release/version.py`'s `FORM` (a final version has no `(a|b|rc)N`) and with how the string is
  written (`VERSION_LINE`, the same regex); it holds for the bump path. The ordering around rule
  6b is M2.
- **Red on the current tree?** No: `0.1.0a8` is a prerelease, so check (a) is `[]`; no Kind
  line carries the bold token, and 107 is drafted, so check (b) is `[]` (EXECUTED). Nothing the
  chain cannot fix: at "built", 107 must cite this review's file name, which it would anyway.
- **The rubric in 45 minutes:** the nine measurements ran in well under a minute here; eight
  rows at one line each are a 45-minute judgement if the reading is bounded (finding 7).
- **Weakens a check or moves a pass?** No: two checks and two unit rows added, no expectation,
  allowance, golden or progress file edited (READ, Design D; INFERRED for the build).
- **Countable criteria:** eight, each with its command or its file; criteria 2 to 4 name the
  failing-first output to record.
- **Header and sections:** all present (EXECUTED, the shape check). None of the words the
  scan rejects, and no questions heading (EXECUTED, the scan).
- **Number 108:** the next free number (EXECUTED, `question 107` is the highest in `context/`);
  drafted as one yes/no with the exact two sentences, the Status entry, a recommendation and a
  "meanwhile", which is the shape the answered questions in `decisions.md` take (READ).

## Constitution checks

- §4 constraints: §4.10 (claims carry their evidence) is tripped once by the empty-grep claim
  (M3); every other number in the draft reproduced here. §4.13 (`uv` only): every command in
  the draft is `uv run …`. §4.14 (git): one specification on the chain's branch, a stacked build
  on 106's tip, no new branch or worktree; nothing committed by this review. §4.9: the 45
  minutes is a reviewer's box, not a test's measurement; no check reads a clock. §4.5: no
  embedder name in any text. §4.3, §4.4, §4.6: untouched (no `src/`, no artifact byte, no
  import). §5.2: no undecided choice in the draft; the owner's decision is asked as a numbered
  item in the file made for it. §5.6: the draft adds a review before a build and one before a
  release and loosens none; the constitution's own text changes only through 108.
- §7 never-do list: nothing tripped. No commit, push, tag or branch; no question list in the
  specification (the one question is in the owner's file, as the file provides); nothing
  reported as run that this review did not run (the draft's one such line is M3, the author's
  to correct).

## Disposition (filled in by the author, then confirmed by the reviewer)
1. Three checks are handed to 107 by its siblings and handed back by 107 — fixed: by the owner's
   decision (2026-10-20), 107 owns the seam check (104's AST walk of `tests/`, in code and in
   program strings, against `SEAM_ALLOWED`: 104's twenty "stays" names, the checks' two, and the
   two plain assignments `_Box` and `_abandon_turn` 104's count did not see; 106 shrinks it) and
   the function ceiling (no function over 80 lines outside `LONG_FUNCTIONS`, the tree's eight
   offenders at `a9064a2`, re-measured on 106's tip); the module size ceiling is 103's, and 105's
   hand-off line is corrected in 105's own round. The allowance rule is stated: an entry is removed
   when its seam or function is fixed, never added, and a stale entry fails the check. Decisions 1
   (triggers 4 and 5), 5, the new 5a and 8; Design D4 and D5; Scope; Acceptance 4 and 5; the claim
   list and flags; A1, B1, C, E1 and E3.
2. The lane's order at 0.1.0 contradicts AGENTS.md rule 6b — fixed: the reviewer's order is
   adopted. The review is of the commit before the bump (its `src/` ships), committed with the
   bump, the dry run runs on that commit, and the tag follows the CHANGELOG-only release commit,
   as rule 6b allows; the wrong clause is gone. Decision 3 (when), Decision 4 (the order), B2's
   first bullet and template "Reviewed" line, E2.
3. Check (b) fires on 107 itself, and the EXECUTED grep it rests on is not empty — fixed: the
   check matches the bold token `**structural**` (D1, `STRUCTURAL_TOKEN`), with the unit case
   `109-z.md` for the word without the token (D3); the Kind line is reworded without the word;
   the claim is replaced by the tree's real output, restricted to Kind lines and EXECUTED with
   102, 104, 105, 106 and 107 present (`grep -rhn '^- \*\*Kind:\*\*' context/specifications |
   grep -c '\*\*structural\*\*'` gives 0, and the plain word gives 0; without `-h` the plain word
   gives 2, both 107's own Kind lines matched on the file's path, which the spec says); criterion
   3 records the check on 107's own Status set to built. Decision 4b, D1, D3.
4. The Status test matches `built` anywhere in the line — fixed: `re.match(r"(built|landed)\b",
   status)`, with the unit case `115-g.md` ("drafted 2026-10-21, to be built on 106's tip" → no
   error). D1, D3, Decision 4b.
5. "Windows included" is wrong for `test_rules.py` — fixed with the reviewer's text: the checks
   run in the `own-rest` shard on macOS and Linux, where `test_rules.py` runs (spec 063, Decision
   18: not on Windows); they read files only. For the lane, "Dry-run needs".
6. A1 drops `platform.system()` from the platform-branch trigger — fixed: A1 lists
   `sys.platform`, `os.name`, `platform.system()`, as Decision 1 and the measurement do.
7. The 45-minute box reads "the whole of `src/` is read" — fixed with the reviewer's text: the
   measurements first, then the diff of `src/` since the last structural review and the modules
   whose measurements moved, the whole of `src/` only when no structural review precedes it.
   Decision 3, B2.
8. Note: `read_version` fits — written in: D2 reads the version through `release/version.py`'s
   `read_version`, the loader factored into `_release_version_module()` and shared with
   `test_the_version_is_released_by_the_book`; `VERSION_LINE` is not duplicated.

## Verdict
Builds once the three Mediums are written into the text: M1 (the seam check, the size ceiling
and the function ceiling each have one builder between 104, 105 and 107), M2 (Decision 4's
order at 0.1.0 agrees with rule 6b: the review of the pre-bump commit lands with the bump, and
the dry run runs on that commit) and M3 (check (b) matches the bold token and the empty-grep
claim is replaced by the tree's output); no High, and the Lows carry their fix text.
