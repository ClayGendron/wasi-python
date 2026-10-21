# 108 — A structural review is a stage

- **Status:** **landed 2026-10-21 with the structural chain** (103 to 109, PR #1) on main `5495b46`: accepted on `7a22103`, history line 90, 777/864 pass, 0 fail, on a set rebuilt from the same pins in the main tree (`SHA256SUMS` `83789790`; the three binaries byte-identical to wave 08's); the dry run 39540823534 on `5af0a42` green on three systems but G7; the integration review `../reviews/wave-structural-chain-103-109-integration-2026-10-21.md` and the lane's addendum to it (three fixes found by the dry run and the acceptance, each reviewed by a fresh agent). Before: **built on `3942323` (the code; the commit after it carries these notes) on
  `spec/108-a-structural-review-is-a-stage`, stacked on `0e145b7` (107's reviewed and landed
  tip, its build review's disposition written in), 2026-10-21; awaiting its build review (a
  different agent).** Drafted 2026-10-20 on `claude/gallant-ride-9nxxmn` from main `5feb7e9` (the
  memo's commit `a9064a2` on top; `src/` is unchanged from `30e9b41`, the memo's tree: EXECUTED,
  `git diff --stat 30e9b41 a9064a2 -- src` is empty); **reviewed before build** the same day
  (`../reviews/108-a-structural-review-is-a-stage-spec-2026-10-20.md`, verdict "builds once the
  three Mediums are written into the text"); **revised against all of its findings** the same
  day, with the owner's decision on M1 (*Disposition of the pre-build review* says where each
  went). It is the last of the stacked chain 103 → 104 → 105 → 106 → 107 → 108 (the memo,
  section 8; the owner, 2026-10-20): it is built stacked on 107's reviewed tip, named above, and
  lands last in the chain's one wave. A pre-build review is optional
  for a context-and-judge specification (AGENTS.md rule 8); this one asked for it anyway, because
  it changes the review stage itself. A different agent reviews the build.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** parallel-safe, not build-class (§5.7); context and judge only. Files: `AGENTS.md`,
  `context/reviews/README.md`, `context/questions-for-the-owner.md`, `context/roadmap.md`,
  `CHANGELOG.md`, `tests/checks/test_rules.py` (four checks and two allowance lists),
  `tests/harness/scan.py`, `tests/unit/test_scan.py`. No file under `src/` changes, no artifact
  byte changes, and it changes no line of `tests/public_api.txt`. It adds no module, no global,
  no seam and no private-API use, so this line carries none of Decision 1's bold token.
- **Depends on:** 103 to 107, by their rules checks and their rules (Decision 5): 103 (one
  module imports wasmtime-py's private API), 104 (the runner becomes a package; the module size
  ceiling is 104's check), 105 (one owner for the process's state; the lock and mutable checks;
  the seam rule, whose check this specification adds, with 105's "stays" list as its first
  allowance), 106 (a type checker in the judge), 107 (one platform module; the citation rule;
  107 shrinks the seam allowance). The rule this specification writes names those checks as its
  mechanical half, so it lands after them. Also 092 (`sameness.py`, the judge of "no verdict
  moved", the memo's section 8) and 004 (`release/version.py`'s version form and `read_version`).
- **Research it stands on:** `../research/2026-10-20-a-design-review-of-the-runner.md`,
  sections 1 (the rubric), 2 (the scorecard), 5 (what the process is missing) and 8 (the chain).
  Numbers in this specification are READ from the memo (its tree `30e9b41`) or EXECUTED on
  `a9064a2`, which has the same `src/`, with the command beside each.

## The problem

The review stage checks behaviour, not structure. The memo says it plainly (section 2, READ):
"That is the normal shape of a project that has shipped 89 specifications in four days under a
review gate that checks behaviour, not structure." Every one of those specifications was reviewed.
No review asked whether `runner.py` should take a twenty-second concern. So it did: 6,241 lines,
about 250 top-level definitions, 60 mutable module globals, 27 locks, 24 uses of wasmtime-py's
private API across two modules, eight test hooks in production code (the memo, section 2, READ).

Specs 103 to 107 fix the structure once. Each adds a rules check that holds its fix: one module
may import `wasmtime._ffi`; no module passes the ceiling; no lock or mutable at module level
outside the process object's module; no platform branch outside the platform module; the type
checker passes. Two rules of the chain have no check in it: 105's seam rule (the judge patches
nothing private in the runner except through the process object) and the memo's "no function
over 80 lines" (section 5); 105 and 106 hand both to this specification, which adds them
(Decision 5). Those checks are regular expressions and AST walks. They see a `threading.Lock()`
at module level and a 90-line function. They do not see a lifecycle encoded in one more boolean
flag, a concern added to a module that is still under its ceiling, a dict used as a lock, or a
protocol object that quietly grows a method only the judge calls. The memo's section 5 names
the gap: "A change that adds a sixth concern to `runner.py` gets no design review, only a
behaviour review, which is how the file got here."

What the rules say today (READ):

- Constitution §5.6 requires a review of the specification before it is built for three kinds of
  change: the guest's imports or exports, the artifact set, the build recipe. AGENTS.md rule 8
  adds "the runner's code" (the owner, 2026-10-19). Neither says what the reviewer looks at in
  the structure, so the pre-build review of a runner change checks its behaviour twice.
- §5.6's last sentence gives each release a security review against the threat model. There is
  no sentence for structure. And no rules check reads whether the security review was written:
  `grep -rn 'security review' tests/checks tests/harness` finds only docstrings that cite a
  review's findings (EXECUTED). The release rule holds by hand (`roadmap.md`, "Release rule").
- The constitution changes only by the owner's explicit decision. A specification cannot amend
  it.

The owner's ask of 2026-10-20: "this PR should include changes so that this refactor/review
process is more a part of the normal workflow." This specification is that change. It adds the
judgement half that the rules checks cannot be, the two checks of the letter the chain left
without a builder, and it makes the judge refuse a release that skipped the review.

## Decisions

### 1. What "structural" means, and where the rule lives

A specification is **structural** when its change to `src/` does any of five things:

1. adds a module-level mutable or a lock outside `src/wasi_python/_process.py` (spec 105's
   owner object; 105's two checks);
2. adds a use of wasmtime-py's private API (`wasmtime._ffi`, `wasmtime._bindings`,
   `Func._func`, `_from_ptr`, `caller._context()`, `store.ptr()`) outside
   `src/wasi_python/_wasmtime_ffi.py` (spec 103's seam; 103's check);
3. adds a platform branch (`sys.platform`, `os.name`, `platform.system()`) outside
   `src/wasi_python/_platform.py` (spec 107's module; 107's check);
4. adds a test seam (a hook, a flag, a name the judge patches) that is not on the process object
   (spec 105's rule; the check is this specification's, Decision 5);
5. takes a module past the size ceiling (spec 104's number and check) or a function past 80
   lines (the memo's section 5; the check is this specification's, Decision 5).

The module names are those specs 103, 105 and 107 give; if one lands under another name, the
rule names the landed one (a one-word context edit, by the lane). A structural specification says
so in its Kind line with the bold token **structural**, and is reviewed before it is built, as a
change to the build recipe is, against the rubric of Decision 3. Why these five: they are exactly
what specs 103 to 107 make true and what a rules check holds (Decision 5). A sixth trigger with
no check behind it would be a rule the judge cannot see; a trigger the checks cover but the
review does not would be the memo's gap again.

**Where the rule lives.** A new bullet in AGENTS.md's "Rules that bind all work", right after
"Nothing lands unreviewed", and one clause in rule 8 of "Working autonomously" (the texts are in
Design, A). Why that section: the rule binds every specification and every reviewer, not only an
agent working alone, and it is the structural twin of "Nothing lands unreviewed". Why one clause
in rule 8: rule 8 is where a builder learns whether its specification needs a pre-build review;
the clause points it at the bullet. Why AGENTS.md at all when the constitution is the law: the
constitution governs AGENTS.md, and AGENTS.md may add a review the constitution does not forbid.
Rule 8's "the runner's code" is the precedent: the owner's decision of 2026-10-19, written into
AGENTS.md, with §5.6 unchanged. The rule loosens nothing: it adds one review before a build and
one before a release.

**The second half of the rule:** before every release, a fresh agent writes a structural review
of `src/` against the rubric, beside the security review, and the release waits on its High
findings. Why per release and not per wave: the memo's scorecard is a release-sized judgement (it
read 11,423 lines); a wave lands every few hours; and the release is where the security review
already sits, so the lane's order of operations gains one file, not one stage.

### 2. The constitution's amendment is the owner's: number 108 in the owner's file

The exact text for §5.6, and the Status line entry, go to `context/questions-for-the-owner.md`
as question 108, in that file's format (Design, C; the next free number is 108: EXECUTED,
`grep -ohE 'question (1[0-9][0-9])' context/*.md | sort -t' ' -k2 -n | tail -1` gives
`question 107`). The question asks one thing and recommends "yes".

- **What lands with "yes":** the lane commits the two sentences into §5.6 and the entry into the
  Status line, word for word from the question, as every amendment before it was committed
  (`constitution.md`, Status); the question moves to `decisions.md` under its number. No code
  changes.
- **Meanwhile:** the AGENTS.md rule binds agents from the wave that lands this specification,
  and the judge holds it (Decision 4). The owner's answer changes the constitution, not the
  workflow.
- **With "no":** the lane removes the rule's last sentence (the release half) and the release
  check in one context-and-judge commit, named in `decisions.md`; the pre-build half, the rubric,
  the mirror check and the two checks of the letter stay, since §5.6 already allows a pre-build
  review for any change and AGENTS.md rule 8 already requires one for the runner. Nothing built
  is lost either way.

### 3. The structural review: when, how long, what it records

`context/reviews/README.md` gains a section, "Structural review" (Design, B). What it decides:

- **When it is written.** Twice. (a) Before every release, by a fresh agent that wrote none of
  the code since the last structural review, on the commit before the version bump, whose
  `src/` is the one tagged (the order is Decision 4's), beside the security review. (b) For a
  structural specification, as a "Structure" section of its pre-build review, by that review's
  reviewer: the eight rows, one line each, saying which row the change moves and which way.
- **The time box:** 45 minutes for a release review, the build-class box: the measurements
  first (one command each), then the diff of `src/` since the last structural review and the
  modules whose measurements moved; the whole of `src/` only when no structural review precedes
  it, and even then the first review compares with the memo, which read it whole. The "Structure"
  section of a pre-build review fits inside that review's own box. A review states its box. Why
  not "the whole of `src/`" every time: the memo read 11,423 lines and states no box; a box
  cannot hold a reading it does not bound (the pre-build review's L7).
- **The eight rows**, as a checklist, each with the question the reviewer answers (the memo's
  section 1 restated as questions): R1 contract, R2 safety, R3 layering, R4 process state, R5
  portability, R6 testability, R7 evolvability, R8 operability. Each row gets a score, Strong,
  Adequate or Weak, as the memo scored it, and a one-line reason. The memo's scorecard (section
  2, at `30e9b41`) is structural review zero: the first release review compares with it; each
  later one compares with the last.
- **The measurements**, each a command that runs on any tree, before and after the chain, with
  today's numbers (EXECUTED on `a9064a2`, Design B's table): module sizes; functions over 80
  lines; module-level mutables and locks; private-API uses; platform branches; private names the
  judge patches; `Any` and `type: ignore` counts; the type checker's result (spec 106's check);
  citations of the archive. Where a rules check reports the same number, the review quotes the
  check's pass line too. Commands, not harness code: the review is a reviewer's record, and a
  command beside a number is what constitution §4.10 asks; a measurement script would be judge
  code with unit rows of its own, for numbers the checks already hold.
- **The ranking rule.** High: a structural rule bypassed, or a finding the next change would
  build on (a concern added to a module at its ceiling, a flag added to a lifecycle that has an
  enum, an import cycle, a seam off the process object); a release waits on it, a structural
  specification does not build yet. Medium: a row that moved toward Weak since the last review, or
  a measurement that moved the wrong way with no specification named to move it back; it becomes a
  reserved specification with a roadmap line before the next release, and the release may go.
  Low: a write-in, as in every other review. Why High blocks the release: that is what §5.6's
  security sentence does with its findings, and the two reviews sit side by side.
- **The file name:** `<version>-structural-review-YYYY-MM-DD.md`, the twin of
  `<version>-security-review-YYYY-MM-DD.md`, so `ls context/reviews/0.1.0*` lists both of a
  release's gates together. The ask's `structural-<version>-YYYY-MM-DD.md` would sort the two
  apart; the twin name is the better one. The "Structure" section of a pre-build review needs no
  name of its own: the review keeps `NNN-<slug>-spec-YYYY-MM-DD.md`.
- **The template** (Design, B): the header (date, reviewer, the reviewed commit, which is the
  one before the bump, the last structural review it compares with, box), the measurements
  table, the eight rows with then and now, findings most severe first, and a one-sentence
  verdict: "the structure holds", "holds once <Mediums are reserved>", or "does not hold:
  <High>".

### 4. Two rules checks for the reviews themselves

**(a) A released version has its structural review:
`test_a_release_has_its_structural_review`.** It reads the version with
`release/version.py`'s `read_version` (the pre-build review's note 8), as
`test_the_version_is_released_by_the_book` loads that module. When the version is a release, a
file `context/reviews/<version>-structural-review-YYYY-MM-DD.md` must exist and score every row:
the tokens `R1` to `R8` and the eight row names, each present (Design, D).

- **"A release" is a version of the form `X.Y.Z` with no `aN`, `bN` or `rcN` suffix**
  (`release/version.py`'s `FORM`; `Version.parse("0.1.0").is_prerelease` is `False` and
  `"0.1.0a8"`'s is `True`: EXECUTED). Why not every version from 0.1.0 on, prereleases included:
  the tree carries the next prerelease's string for the whole cycle (`0.1.0a8` today, bumped the
  day a7 shipped), so a check keyed on it would be red from the cycle's first commit until a
  review was written of code that did not exist yet. A final version is different: `release/
  version.py bump --to 0.1.0` is run at the release itself, so the check turns red at exactly
  the moment the gate applies and stays red until the review file is in the tree. The first
  release is 0.1.0 (the owner, 2026-10-19: no more alphas), so "from 0.1.0 on" is what the rule
  gives; and if the owner ever cuts a `0.2.0a1`, the AGENTS.md rule still binds the agent to
  write its review by hand, as the security reviews of a2 to a7 were written by hand.
- **The lane's order at 0.1.0**, consistent with AGENTS.md rule 6b (the pre-build review's M2):
  main stands at commit X, the last wave landed, version `0.1.0a8`. A fresh agent writes
  `0.1.0-structural-review-<date>.md` of X, whose `src/` is the one that ships, and the security
  review's addendum. The lane commits both files together with `release/version.py bump --to
  0.1.0` and the CHANGELOG section's text as one commit Y. Y changes
  `src/wasi_python/__init__.py`, so rule 6b needs a dry run: the lane dispatches the release
  workflow on Y, where this check passes because the review is in the tree, and waits for every
  job on all three systems. Then `release/version.py release` dates the CHANGELOG in its own
  CHANGELOG-only commit Z, which rule 6b allows after the dry run with the fast tier, and the
  owner tags Z. The review's "Reviewed" line names X and says it is the commit before the bump.

**(b) A built structural specification cites its pre-build review:
`test_built_structural_specifications_cite_their_pre_build_review`**, the mirror of
`test_landed_specifications_cite_an_existing_review`. For every specification whose Kind line
(the `- **Kind:**` line and its continuation lines) carries the bold token `**structural**`,
and whose Status line, with its `*` stripped, begins with `built` or `landed`: the text must
cite `reviews/NNN-<slug>-spec-YYYY-MM-DD.md` with its own number `NNN`, and the file must exist.

- **Why the bold token and not the word:** the word appears in prose ("not structural", "a
  structural review"), this specification's own title among it; a substring test fired on this
  file once its Status said built (the pre-build review's M3, EXECUTED by the review). The token
  is what Decision 1 asks a Kind line to carry. What the tree holds (EXECUTED on this tree,
  with 103, 105, 106, 107 and this file present): `grep -rhn '^- \*\*Kind:\*\*'
  context/specifications | grep -c '\*\*structural\*\*'` gives `0`, and the same grep for the
  plain word gives `0` too, since this Kind line no longer uses it. Without `-h` the plain word
  gives `2`: this file's two Kind lines (its header and "For the lane"), matched on the file's
  path, `108-a-structural-review…`, which `grep -rn` prefixes to each line, not on their text.
  So no existing specification trips the check, and 103 to 107 stay outside it until a builder
  adds the token (below).
- **Why `built` or `landed` at the line's start and not anywhere in it:** the newest state is
  written first in every Status line (`status_line()`, and `landed_review_errors`'s
  `startswith("landed")`); "drafted 2026-10-21, to be built on 107's tip" says built and is not
  (the pre-build review's L4). The `*` are stripped because status lines are bold
  (`**landed 2026-10-20 …**`); `status_line()` keeps them.
- **103 to 107** were reviewed before build under rule 8's "the runner's code"; their Kind
  lines need no token, and the check does not fire on them. Their builders may add the token at
  their rebase onto the wave, and then the check reads their `-spec-` reviews, which exist. The
  check binds every structural specification drafted after it lands.

Both are rules checks (fast tier, no artifact), both seen failing first (Acceptance 2 and 3).

### 5. Where the enforcement lives: the letter and the spirit

| rule | the letter (a rules check, mechanical) | the spirit (a review, judgement) |
|---|---|---|
| one module touches wasmtime-py's private API | spec 103's check: only `_wasmtime_ffi.py` imports `wasmtime._ffi` or `wasmtime._bindings` | R3: is the policy still apart from the mechanism; does a new operation belong in the seam |
| modules a person can hold in their head | spec 104's module size ceiling | R7: is a module under the ceiling taking a concern that is not its own |
| functions a person can read whole | **this specification's** function ceiling: no function over 80 lines outside its allowance list (5a) | R7: is a long function one concern or three |
| process state has one owner | spec 105's lock and mutable checks | R4: is a lifecycle still an enum and a table, or did a flag come back |
| seams are injected, not patched | **this specification's** seam check: the judge patches nothing private in the runner except through `process()`, outside its allowance list (5a) | R6: does production code carry a branch only the judge takes |
| the platform is behind one seam | spec 107's platform-branch rule | R5: does the Windows story still read in one file |
| the code explains itself | spec 107's citation rule (M2) | R7: does a new comment say why, or cite an archive |
| types are checked | spec 106's type checker in `test_rules.py` | R7, R1: did `Any` come back; is a contract still a sentence a test checks |

The owner decided who owns the three checks the chain's texts handed back and forth (2026-10-20,
the pre-build review's M1): this specification owns the seam check and the function ceiling;
the module size ceiling is 104's, since the package split sets its number (106's line that
hands it here is corrected in 106's own disposition round). Why both halves: a regex cannot score
R4; a reviewer cannot read 11,000 lines for a stray lock every wave. Each half holds what the
other cannot.

### 5a. The two checks of the letter this specification adds

Both live in `tests/checks/test_rules.py`, their scanners in `tests/harness/scan.py`, their
allowance lists as constants in `test_rules.py` beside `WASMTIME_GUARDS`, each entry with its
closer in a comment (Design, D4 and D5).

**The allowance rule, for both lists:** an entry is removed when its function or its seam is
fixed, and never added; the check fails on a stale entry (an allowed name no test patches any
more, an allowed function no longer over 80 lines or no longer there). So each list only
shrinks, and shrinking it is a judge change the lane accepts with `--accept-judge`, as any
edit to `test_rules.py` is. A name or a function outside the list is red, and the fix is in the
code or the test, never in the list.

**The seam check, `test_the_judge_patches_the_runner_only_through_the_process_object`.** An
AST walk of every `.py` file under `tests/` for the two forms 105's Decision 4 names:
`monkeypatch.setattr(<module>, "_name", …)` and `<module>._name = …`, where `<module>` is a
local name the file's imports bind to a runner module (`wasi_python.runner`,
`wasi_python.mounts`, or any `wasi_python._<name>` module, which after 104 is the package), or
the dotted module path itself; and the same two forms inside every string constant of the file,
by regular expression, because the judge's child programs are strings
(`tests/checks/test_v1_2_hostile_guest.py:3135` assigns `runner._abandon_turn` in a program:
EXECUTED). A hit whose `_name` is not in `SEAM_ALLOWED` is a finding, `file:line: <module>._name`;
an allowed name with no hit is a finding, `stale allowance: _name`. Outside the rule: `tools`,
`cli` and the package `__init__` (the memo's H5 and 105's rule are about the runner; `tools.py`
is the model the memo points at, and its patched names are bounds the judge lowers to reach a
limit, `_TOOL_RESPONSE_BYTES` six times, counted by measurement M6, not seams: EXECUTED); a
first argument that is a call or an attribute of one (`process().observers`, 105's one way);
and a class attribute (`_Files.__call__`, `_ToolHost._list_answer`: objects the tests build).

**Its initial allowance** is 105's "stays" list (105, Decision 4, READ): the twelve platform
answers 107's `_platform.py` closes (`_guest_stack`, `_tell_interpreter`, `_trap_handlers_ready`,
`_dir_fd_ok`, `_win_open`, `_close_held`, `_try_lock`, `_unlock_close`, `_remove_tree`, `_drop`,
`_drive`, `_stack`), the eight engine and call paths 107's call-context protocol or 106's typed
call closes (`_ctrl_c_watched`, `_stop_error`, `_epoch_now`, `_context_address`, `_module_miss`,
`_found_and_checked`, `_join_guest`, `_walk_grants`), the two the checks alone patch
(`_check_preopens`, `_current_defaults`), and two plain assignments 105's monkeypatch count did
not see (EXECUTED, `grep -rnE '\brunner\._\w+\s*=[^=]' tests`): `_Box`, a by-hand save and
restore in `tests/unit/test_runner_threads.py:216` and `:221` (its closer 107's home seam:
INFERRED), and `_abandon_turn` in the program at `test_v1_2_hostile_guest.py:3135` (its closer
106's session lifecycle: INFERRED). Twenty-four names. Every other private runner name patched
today (the pre-build review counted 59 distinct `module.name` pairs across all modules) is state
or a hook that 105 moves to `process()`; on 107's tip the builder re-runs the walk, removes any
of the twenty-four that no test patches any more, and finds nothing else, or the remainder is
red and is fixed in the test through `process()` where 105's object has the field, else named
to the chain's integration review as 105's or 107's to close. 107 shrinks the list as its
protocol fakes land (105, Decision 4).

**The function ceiling, `test_no_function_is_over_eighty_lines`.** An AST walk of every `.py`
file under `src/wasi_python/`: every `FunctionDef` and `AsyncFunctionDef`, nested ones included,
whose `end_lineno - lineno + 1` is over 80 must be in `LONG_FUNCTIONS`, keyed
`<file>:<qualname>`; an entry whose function is at or under 80 lines, or gone, is a stale
allowance. Why 80 and why lines: the memo's section 5 says "no function over 80", and lines are
what a reader scrolls; a complexity measure would need a tool and a pin. **Its initial
allowance** is the tree's offenders, measured by the same walk (EXECUTED on `a9064a2`, eight):
`runner.py:run` 152, `runner.py:run_async` 177, `runner.py:_instance` 150,
`runner.py:_open_session` 137, `runner.py:Session.__init__` 169, `runner.py:Session.run_async` 81,
`tools.py:_make` 82, `tools.py:_ToolHost._answer` 83. 104 moves the first six into the package's
modules and 106 retypes some of them, so the builder re-measures on 107's tip and writes the
keys and lengths it finds there, labelled EXECUTED, in the landing notes: the same functions
under their new files, fewer if 106 shortened one, never one more.

### 6. The reviewer's checklist gains one line

`context/reviews/README.md`'s checklist gains item 4a, between the constitution check and the
probes (Design, B, the exact text): the reviewer says in one line whether the diff adds a concern,
a lifecycle flag, a module-level mutable, a test seam, a platform branch, a private-API use or a
function past 80 lines that the rubric would score down, whether or not a rules check catches
it, naming the row; if it does and the Kind line does not carry **structural**, that is Medium,
because the specification was structural and was not reviewed as one. Why one line and not a
section: every review of a `src/` change pays it, so it must be cheap; the full rubric is for
the two structural reviews.

### 7. No verdict moves

This specification adds four rules checks and unit rows and changes nothing the judge measures.
`uv run python tests/harness/sameness.py` between the baseline record (the fast tier on the
frozen `v0.1.0a7` set, the memo's section 8) and this build's record lists exactly the four new
rows and the unit suite's count, and nothing else (Acceptance 7). The claim list names them.

### 8. Where it meets other specifications and the release

- **103 to 107:** stacked below this one; their checks are Decision 5's left column; their Kind
  lines are their own. The rule's module names are theirs (Decision 1). 105 hands the seam check
  here and 107 shrinks its allowance (105, Decision 4); 106's hand-off of a module size ceiling
  is corrected in 106's own disposition round to name 104; the function ceiling is this
  specification's.
- **092:** `sameness.py` is the judge of Decision 7 and of the whole chain (the memo, section 8).
- **The 0.1.0 release:** gains one file, the structural review, in the order Decision 4 gives;
  the roadmap's "Release rule" says so (Design, E).
- **The security review's own check:** none exists today (The problem) and none is added here
  (Scope). Decision 4's scanner takes the review kind from its file name, so one line adds it;
  what the judge requires of the security review is a change to the judge with the owner's
  reason, not this specification's.

## Intent

A change that would turn the runner back into one file is caught by a reviewer before it is code,
and every release is scored against the same eight rows the memo scored, by someone who did not
write the code, with the numbers beside the scores. The judge refuses a release that skipped it,
a seam the judge patches outside the process object, and a function nobody can read whole.

## Design

| file | change |
|---|---|
| `AGENTS.md` | the bullet "Structure is reviewed, not only behaviour" after "Nothing lands unreviewed"; one clause in rule 8 (A) |
| `context/reviews/README.md` | checklist item 4a; the section "Structural review" with its rubric, measurements, ranking rule and template (B) |
| `context/questions-for-the-owner.md` | question 108 under "## Open", replacing "None." (C) |
| `tests/harness/scan.py` | `STRUCTURAL_ROWS`, `structural_review_errors`, `structural_spec_review_errors` (D1); `seam_hits` (D4); `long_function_hits` (D5) |
| `tests/checks/test_rules.py` | the four checks and the two allowance lists (D2, D4, D5) |
| `tests/unit/test_scan.py` | the unit rows (D3, D4, D5) |
| `context/roadmap.md`, `CHANGELOG.md` | the lines in E |

Every text below is ready to paste. The builder pastes it unchanged; the build review diffs the
tree against this section.

### A. AGENTS.md

**A1. The new bullet**, in "Rules that bind all work", inserted after the bullet that begins
"**Nothing lands unreviewed.**" and before "**Commit or push only when asked.**":

```
- **Structure is reviewed, not only behaviour** (spec 108; the design
  review `context/research/2026-10-20-a-design-review-of-the-runner.md`).
  A specification is **structural** when its change to `src/` adds a
  module-level mutable or lock outside `_process.py`, a use of
  wasmtime-py's private API outside `_wasmtime_ffi.py`, a platform branch
  (`sys.platform`, `os.name`, `platform.system()`) outside
  `_platform.py`, a test seam that is not on the process object, or takes
  a module past the size ceiling or a function past 80 lines. Its Kind
  line carries the bold word **structural**, and it is reviewed before it
  is built, as a change to the build recipe is (constitution §5.6),
  against the eight-row rubric in `context/reviews/README.md`. The rules
  checks of specs 103 to 108 hold the letter of this; the review holds
  its spirit. Before every release, a fresh agent writes a structural
  review of `src/` against the same rubric,
  `context/reviews/<version>-structural-review-YYYY-MM-DD.md`, beside
  the security review; the release waits on its High findings, and the
  judge refuses a released version without one.
```

**A2. Rule 8's clause.** In "Working autonomously", rule 8, the text

```
   requires it (the guest's imports or exports, the artifact set, the
   build recipe) and for the runner's code, optional for a judge-only or
```

becomes

```
   requires it (the guest's imports or exports, the artifact set, the
   build recipe), for the runner's code and for a structural change
   ("Structure is reviewed", above), optional for a judge-only or
```

### B. `context/reviews/README.md`

**B1. Checklist item 4a**, inserted after item 4 ("The diff against §4 and §7; …") and before
item 5 ("One to three probes by node id, locally."):

```
4a. Structure, one line (AGENTS.md, "Structure is reviewed"): does the diff add a concern, a
   lifecycle flag, a module-level mutable, a test seam, a platform branch, a private-API use or a
   function past 80 lines that the rubric below would score down, whether or not a rules check
   catches it? Name the row. If it does and the Kind line does not carry **structural**, that is
   Medium: the specification is structural and was not reviewed as one.
```

**B2. The section**, appended after the "Template" section's closing fence, at the end of the
file:

````
## Structural review

A review of `src/` against the eight-row rubric of
`../research/2026-10-20-a-design-review-of-the-runner.md` (section 1), which is structural
review zero: its scorecard (section 2, at `30e9b41`) is what the first release review compares
with, and each later review compares with the last. It is written twice (AGENTS.md, "Structure
is reviewed"; spec 108):

- **Before every release**, by a fresh agent that wrote none of the code since the last
  structural review, on the commit before the version bump, whose `src/` is the one tagged; the
  review is committed with the bump, the release's dry run runs on that commit, and the tag
  follows the CHANGELOG-only release commit (AGENTS.md rule 6b), beside the security review.
  File: `<version>-structural-review-YYYY-MM-DD.md`, the twin of
  `<version>-security-review-YYYY-MM-DD.md`. The release waits on its High findings; the judge
  refuses a released version with no such file (`test_a_release_has_its_structural_review`).
- **For a structural specification** (its Kind line carries **structural**), as a "Structure"
  section of its pre-build review (`NNN-<slug>-spec-YYYY-MM-DD.md`): the eight rows, one line
  each, saying which row the change moves and which way, and the measurements it claims to
  change, before and after, by the commands below. The judge holds that a built structural
  specification cites that review (`test_built_structural_specifications_cite_their_pre_build_review`).

Time box: 45 minutes for a release review: the measurements first (one command each), then the
diff of `src/` since the last structural review and the modules whose measurements moved; the
whole of `src/` only when no structural review precedes it (the first compares with the memo,
which read it whole). The "Structure" section fits inside its review's box. The review states
its box.

### The eight rows

Score each Strong, Adequate or Weak, with a one-line reason, as the memo did.

- **R1 Contract.** Are the public names still few and snapshotted (`tests/public_api.txt`)? Is
  every invariant a sentence a test checks? Are failures promised by type, never by message?
- **R2 Safety.** Are the defaults safe and read once? Is every channel to the host bounded? Are
  arguments validated before any side effect? Are check-and-use races closed by identity?
- **R3 Layering.** Does exactly one module touch the engine's private API? Is policy apart from
  mechanism? Is the import graph acyclic?
- **R4 Process state.** Is module-level mutable state owned by one object and reset in one
  place? Is each lifecycle an enum and a table, not flags? Is the lock order written down?
- **R5 Portability.** Does OS-specific behaviour live in one module behind one interface, chosen
  once?
- **R6 Testability.** Are seams constructor parameters or protocol objects? Do tests drive public
  behaviour? Does production code carry a branch only the judge takes?
- **R7 Evolvability.** Can one person hold each module, and each function, in their head? Does
  the code say why without the archive open? Does the type checker pass? Is the engine upgrade's
  cost written?
- **R8 Operability.** Do `stats()`, the records and the trap strings still say what the guest
  did? Can a warning deadlock an embedder?

### The measurements

One command each, run from the repository's root on the reviewed commit; the review records the
output beside the score it informs, labelled EXECUTED. Where a rules check of specs 103 to 108
reports the same number, quote its pass line too (`uv run pytest tests/checks/test_rules.py -q`).
The numbers are those of `a9064a2` (EXECUTED 2026-10-20, spec 108), before the chain; the memo's
differ where its method was reading, not a command.

| what (row) | command | at `a9064a2` |
|---|---|---|
| module sizes (R7) | `wc -l src/wasi_python/*.py \| sort -n` | `runner.py` 6,241; `tools.py` 2,450; `mounts.py` 2,235; 11,423 in all |
| functions over 80 lines (R7; spec 108's check and its allowance list) | `uv run python -I -c "import ast,pathlib;[print(p.name,sum(1 for n in ast.walk(ast.parse(p.read_text())) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.end_lineno-n.lineno+1>80)) for p in sorted(pathlib.Path('src/wasi_python').rglob('*.py'))]"` | `runner.py` 6, `tools.py` 2 |
| module-level mutables and locks (R4) | `grep -rnE '^_?[a-z]\w*\s*(:[^=]+)?=\s*(threading\.(R?Lock\|Condition\|Event\|Semaphore)\(\|\{\|\[\|dict\(\|list\(\|set\(\|collections\.)' src/wasi_python --include=*.py` | 47 lines: `runner.py` 46, `__init__.py` 1 |
| private-API uses (R3) | `grep -rnE 'wasmtime\._\|\b_ffi\.\|\b_bindings\.\|\._func\b\|_from_ptr\|\._context\(\)\|\.ptr\(\)' src/wasi_python --include=*.py` | 27 lines: `mounts.py` 15, `runner.py` 11, `tools.py` 1 |
| platform branches (R5) | `grep -rnE 'sys\.platform\|os\.name\b\|platform\.system' src/wasi_python --include=*.py` | 22 lines, all in `runner.py` |
| private names the judge patches (R6; spec 108's seam check holds the runner's) | `grep -rhoE 'monkeypatch\.setattr\(\s*\w+(\.\w+)*,\s*"_\w+"' tests --include=*.py \| sort \| uniq -c \| sort -rn` | 59 distinct; `runner._ctrl_c_watched` 8 times, `_remove_tree` 5 |
| `Any` and `type: ignore` (R7) | `grep -rc '\bAny\b' src/wasi_python --include=*.py; grep -rc 'type: ignore' src/wasi_python --include=*.py` | 349 `Any`; 12 ignores |
| the type checker (R7) | spec 106's check by its node id in `tests/checks/test_rules.py`, and the length of its allowlist | none before 106 |
| citations of the archive (R7) | `grep -roE 'spec [0-9]{3}' src/wasi_python --include=*.py \| wc -l; grep -roE "review'?s? [A-Z][0-9]+" src/wasi_python --include=*.py \| wc -l` | 315 specification references; 37 finding IDs |

### Ranking

- **High:** a structural rule bypassed, or a finding the next change would build on: a concern
  added to a module at its ceiling, a flag added to a lifecycle that has an enum, an import cycle,
  a seam off the process object. A release waits on it; a structural specification does not build
  yet.
- **Medium:** a row that moved toward Weak since the last structural review, or a measurement
  that moved the wrong way with no specification named to move it back. It becomes a reserved
  specification with a roadmap line before the next release; the release may go.
- **Low:** a write-in, as in every review.

Verdict in one sentence: "the structure holds", "holds once <the Mediums are reserved>", or
"does not hold: <the High>".

### Template

```
# <version>: structural review against the rubric, YYYY-MM-DD

- **Date:** YYYY-MM-DD
- **Reviewer:** <agent or person; wrote none of src/ since the last structural review>
- **Reviewed:** main at <commit>, the commit before the bump to <version>; its src/ is what ships
- **Compared with:** <the last structural review's file, or the memo's scorecard at 30e9b41>
- **Box:** 45 minutes; <where it stood at the box>

## Measurements (EXECUTED)
| what | then | now | command |
|---|---|---|---|

## The eight rows
| row | then | now | reason |
|---|---|---|---|
| R1 Contract | | | |
| R2 Safety | | | |
| R3 Layering | | | |
| R4 Process state | | | |
| R5 Portability | | | |
| R6 Testability | | | |
| R7 Evolvability | | | |
| R8 Operability | | | |

## Findings, most severe first
1. **<title>** (`path:line`, row Rn) — <the defect in one sentence>.
   Next change it would shape: <what the next specification would build on it>.

## Verdict
<the structure holds / holds once … / does not hold: …>, in one sentence.
```
````

### C. Number 108 in `context/questions-for-the-owner.md`

Under "## Open", the line "None." becomes:

```
### 108. Amend §5.6: a structural change is reviewed before build, and a structural review of `src/` precedes each release

- **Asked:** 2026-10-20. **Source:** `specifications/108-a-structural-review-is-a-stage.md`,
  Decisions 1 and 2; `research/2026-10-20-a-design-review-of-the-runner.md`, section 5. Your ask
  of 2026-10-20: "this PR should include changes so that this refactor/review process is more a
  part of the normal workflow".
- **The fact:** §5.6 names three kinds of change that are reviewed before they are built, and
  one review before each release, the security review. The review stage has checked behaviour,
  not structure: 89 landed specifications and 187 reviews left `runner.py` at 6,241 lines with 60
  mutable module globals and 27 locks (the memo, section 2, READ). Specs 103 to 108 fix that
  once, and their rules checks hold the letter of the fix. Nothing in the constitution asks a
  reviewer to look at the structure again.
- **The question:** may §5.6 be amended with the two sentences below, and its Status line with
  the entry below? AGENTS.md's rule "Structure is reviewed, not only behaviour" (spec 108) binds
  agents from the wave that lands it, as rule 8's "the runner's code" did on 2026-10-19; the
  constitution is yours to change.
- **The amendment, §5.6.** After "so a wrong design is caught before it is code.": "A
  specification that is structural (AGENTS.md: it adds a module-level mutable or lock outside the
  process object's module, a use of the engine's private API outside the engine seam, a platform
  branch outside the platform module, a test seam not on the process object, or takes a module
  or a function past its ceiling) is reviewed before it is built in the same way, against the
  structural rubric in `reviews/README.md` (owner, 2026-10-20, question 108)." After the last
  sentence, on the security review: "Before each release a fresh reviewer also writes a
  structural review of `src/` against that rubric, recorded under `reviews/` beside the security
  review; the release waits on its High findings (owner, 2026-10-20, question 108)."
- **The Status line entry:** "Amended 2026-10-20 by the owner's answer to question 108: a
  structural change is reviewed before it is built, and a structural review of `src/` precedes
  each release beside the security review (§5.6)."
- **The agent's recommendation:** yes, as written. The cost is one 45-minute review per release
  and one "Structure" section per structural specification; the alternative is the file the memo
  describes, grown again.
- **Meanwhile:** AGENTS.md carries the rule and the judge holds it
  (`test_a_release_has_its_structural_review`,
  `test_built_structural_specifications_cite_their_pre_build_review`). A "no" removes the release
  half (the rule's last sentence and the first check) in one context-and-judge commit by the lane,
  recorded in `decisions.md`; the rubric stays as guidance and the pre-build half stays, since
  AGENTS.md rule 8 already requires a pre-build review of the runner's code.
```

### D. The checks

**D1. `tests/harness/scan.py`**, after `landed_review_errors`:

```python
STRUCTURAL_ROWS = (
    ("R1", "Contract"),
    ("R2", "Safety"),
    ("R3", "Layering"),
    ("R4", "Process state"),
    ("R5", "Portability"),
    ("R6", "Testability"),
    ("R7", "Evolvability"),
    ("R8", "Operability"),
)
RELEASE_VERSION = re.compile(r"^\d+\.\d+\.\d+$")  # X.Y.Z with no aN, bN or rcN (release/version.py)


def structural_review_errors(version: str, reviews: Path) -> list[str]:
    """A released version has its structural review of src/ under reviews/, named
    `<version>-structural-review-YYYY-MM-DD.md`, and the review scores every row of the rubric
    (spec 108, Decision 4). A prerelease needs none from the judge: its string is what the tree
    carries all cycle."""
    if not RELEASE_VERSION.match(version):
        return []
    name = re.compile(rf"^{re.escape(version)}-structural-review-\d{{4}}-\d{{2}}-\d{{2}}\.md$")
    found = sorted(p for p in reviews.glob("*.md") if name.match(p.name))
    if not found:
        return [f"{version} is a release; reviews/ has no {version}-structural-review-<date>.md"]
    errors = []
    for p in found:
        text = p.read_text()
        for tag, row in STRUCTURAL_ROWS:
            if not re.search(rf"\b{tag}\b", text) or row.lower() not in text.lower():
                errors.append(f"{p.name}: does not score {tag} ({row})")
    return errors


KIND_LINE = re.compile(r"^- \*\*Kind:\*\*(.*?)(?=^- \*\*|^## )", re.M | re.S)
STRUCTURAL_TOKEN = "**structural**"


def structural_spec_review_errors(path: Path, reviews: Path) -> list[str]:
    """A specification whose Kind line carries the bold token **structural** cites, once its
    Status begins with built or landed, its own review before build,
    `reviews/NNN-<slug>-spec-YYYY-MM-DD.md`, and the file exists (spec 108, Decision 4: the mirror
    of landed_review_errors for the pre-build review)."""
    text = path.read_text()
    kind = KIND_LINE.search(text)
    if kind is None or STRUCTURAL_TOKEN not in kind[1]:
        return []
    status = status_line(text).replace("*", "")
    if not re.match(r"(built|landed)\b", status):
        return []
    number = path.name.split("-", 1)[0]
    cited = [
        c
        for c in re.findall(r"reviews/([\w.-]+\.md)", text)
        if c.startswith(f"{number}-") and "-spec-" in c
    ]
    if not cited:
        return [f"{path.name}: structural and built, but cites no reviews/{number}-<slug>-spec-<date>.md"]
    return [
        f"{path.name}: cites reviews/{c}, which does not exist"
        for c in cited
        if not (reviews / c).is_file()
    ]
```

**D2. `tests/checks/test_rules.py`**, after `test_landed_specifications_cite_an_existing_review`.
`_release_version_module()` is the loader `test_the_version_is_released_by_the_book` already
inlines (`importlib.util.spec_from_file_location` on `release/version.py`, registered in
`sys.modules` as `release_version`), factored into one helper both checks call; that check's
behaviour does not change.

```python
def test_a_release_has_its_structural_review() -> None:
    """AGENTS.md, "Structure is reviewed" (spec 108, Decision 4; constitution §5.6 as question 108
    amends it): a released version has its structural review of src/ under context/reviews/,
    scoring the rubric's eight rows. A prerelease needs none from the judge."""
    version = _release_version_module()
    current = version.read_version(version.INIT.read_text())
    errors = scan.structural_review_errors(current, paths.CONTEXT / "reviews")
    assert not errors, scan.report(errors)


def test_built_structural_specifications_cite_their_pre_build_review() -> None:
    """A specification whose Kind line carries **structural** was reviewed before it was built:
    once built or landed, it cites its own `-spec-` review, and the file exists (spec 108,
    Decision 4)."""
    reviews = paths.CONTEXT / "reviews"
    errors = [
        e for s in sorted(SPECS.glob("*.md")) for e in scan.structural_spec_review_errors(s, reviews)
    ]
    assert not errors, scan.report(errors)
```

**D3. `tests/unit/test_scan.py`**, two rows, after `test_a_landed_spec_cites_an_existing_review`.
`SPEC` is the file's existing fixture (Kind line `feature`); the second row writes its own with a
Kind line of its own.

```python
ROWS = "".join(f"| {tag} {row} | Strong | Strong | holds |\n" for tag, row in scan.STRUCTURAL_ROWS)


def test_a_release_has_its_structural_review(work) -> None:
    reviews = work / "reviews"
    reviews.mkdir()
    assert scan.structural_review_errors("0.1.0a8", reviews) == []  # a prerelease: never
    assert scan.structural_review_errors("0.1.0", reviews) == [
        "0.1.0 is a release; reviews/ has no 0.1.0-structural-review-<date>.md"
    ]
    write(reviews, "0.1.0-security-review-2026-10-21.md", ROWS)  # the twin does not count
    write(reviews, "structural-0.1.0-2026-10-21.md", ROWS)  # nor the other order of words
    assert len(scan.structural_review_errors("0.1.0", reviews)) == 1
    write(reviews, "0.1.0-structural-review-2026-10-21.md", ROWS)
    assert scan.structural_review_errors("0.1.0", reviews) == []
    assert len(scan.structural_review_errors("0.2.0", reviews)) == 1  # another version's file
    write(reviews, "0.1.0-structural-review-2026-10-22.md", ROWS.replace("R4 Process state", "R4"))
    assert scan.structural_review_errors("0.1.0", reviews) == [
        "0.1.0-structural-review-2026-10-22.md: does not score R4 (Process state)"
    ]


STRUCTURAL = SPEC.replace("- **Kind:** feature", "- **Kind:** parallel-safe;\n  **structural**: it adds a lock")
NOT_STRUCTURAL = SPEC.replace("- **Kind:** feature", "- **Kind:** parallel-safe; not structural")


def test_a_built_structural_spec_cites_its_pre_build_review(work) -> None:
    reviews = work / "reviews"
    write(reviews, "110-a-spec-2026-10-21.md", "review")
    plain = write(work, "110-a.md", SPEC.format(status="**built 2026-10-21**", notes=""))
    word = write(work, "109-z.md", NOT_STRUCTURAL.format(status="**built 2026-10-21**", notes=""))
    drafted = write(work, "111-b.md", STRUCTURAL.format(status="drafted 2026-10-21", notes=""))
    says = write(
        work, "115-g.md", STRUCTURAL.format(status="drafted 2026-10-21, to be built on 107's tip", notes="")
    )
    none = write(work, "112-c.md", STRUCTURAL.format(status="**built 2026-10-21**", notes=""))
    ok = write(
        work,
        "110-d.md",
        STRUCTURAL.format(status="landed", notes="Reviewed: reviews/110-a-spec-2026-10-21.md."),
    )
    other = write(
        work,
        "113-e.md",
        STRUCTURAL.format(status="built", notes="Reviewed: reviews/110-a-spec-2026-10-21.md."),
    )
    missing = write(
        work, "114-f.md", STRUCTURAL.format(status="built", notes="reviews/114-f-spec-2026-10-21.md")
    )
    assert scan.structural_spec_review_errors(plain, reviews) == []  # no token
    assert scan.structural_spec_review_errors(word, reviews) == []  # the word, not the token
    assert scan.structural_spec_review_errors(drafted, reviews) == []  # not yet built
    assert scan.structural_spec_review_errors(says, reviews) == []  # says built, is drafted
    assert scan.structural_spec_review_errors(ok, reviews) == []
    assert scan.structural_spec_review_errors(none, reviews) == [
        "112-c.md: structural and built, but cites no reviews/112-<slug>-spec-<date>.md"
    ]
    assert scan.structural_spec_review_errors(other, reviews) == [  # another spec's review
        "113-e.md: structural and built, but cites no reviews/113-<slug>-spec-<date>.md"
    ]
    assert scan.structural_spec_review_errors(missing, reviews) == [
        "114-f.md: cites reviews/114-f-spec-2026-10-21.md, which does not exist"
    ]
```

The builder may rename a fixture or split a row; the cases are the specification. `ruff format`
decides the line breaks.

**D4. The seam check** (Decision 5a). In `tests/harness/scan.py`, beside `duplicate_name_hits`:

```python
RUNNER_MODULE = re.compile(r"^wasi_python\.(runner|mounts|_\w+)$")  # the runner's modules (spec 108, 5a)
SEAM_IN_TEXT = re.compile(r"""monkeypatch\.setattr\(\s*([\w.]+)\s*,\s*["'](_\w+)["']|\b([\w.]+)\.(_\w+)\s*=[^=]""")


def _runner_names(tree: ast.Module) -> dict[str, str]:
    """Local name -> the runner module the file's imports bind it to."""
    names = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if RUNNER_MODULE.match(a.name):
                    names[a.asname or a.name.split(".")[0]] = a.name
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("wasi_python"):
            for a in node.names:
                full = f"{node.module}.{a.name}"
                if RUNNER_MODULE.match(full):
                    names[a.asname or a.name] = full
    return names


def seam_hits(files: Iterable[Path], root: Path, allowed: Iterable[str]) -> list[str]:
    """Every `monkeypatch.setattr(<runner module>, "_name", …)` and `<runner module>._name = …` in
    the judge, in code (by ast) and in the programs it runs as subprocesses (string constants, by
    regex), whose _name is not allowed; and every allowed name no file patches (a stale
    allowance). The one way to set a seam is through process() (spec 105, Decision 4; spec 108,
    Decision 5a)."""
```

The function's body: for each file, parse it; `names = _runner_names(tree)`; a hit is (1) a
`Call` whose `func` is `Attribute(value=Name("monkeypatch"), attr="setattr")` with a first
argument that is a `Name` in `names`, or an `Attribute` chain whose dotted text matches
`RUNNER_MODULE`, and a second argument that is a string constant starting with `_`; (2) an
`Assign` whose target is `Attribute(value=<the same kinds of module expression>, attr=_name)`;
(3) inside every `ast.Constant` string, each `SEAM_IN_TEXT` match whose module text is a key of
`names` or matches `RUNNER_MODULE`. A hit with `_name` not in `allowed` gives
`f"{rel(file, root)}:{line}: {module}.{_name}"`; after the walk, each allowed name with no hit
gives `f"stale allowance: {_name}"`. A first argument that is a `Call` or an attribute of one
(`process().observers`) is never a hit. In `tests/checks/test_rules.py`:

```python
# Spec 108, Decision 5a: the private runner names the judge still patches by name, each with its
# closer (spec 105, Decision 4: 107's platform seam, 107's call-context protocol, 106's typed
# call). An entry leaves when its seam is fixed; none is ever added; a stale entry is red.
SEAM_ALLOWED = (
    "_guest_stack", "_tell_interpreter", "_trap_handlers_ready", "_dir_fd_ok", "_win_open",
    "_close_held", "_try_lock", "_unlock_close", "_remove_tree", "_drop", "_drive", "_stack",  # 107's _platform.py
    "_ctrl_c_watched", "_stop_error", "_epoch_now", "_context_address", "_module_miss",
    "_found_and_checked", "_join_guest", "_walk_grants",  # 107's protocol or 106's typed call
    "_check_preopens", "_current_defaults",  # the checks' two, the same closers
    "_Box",  # test_runner_threads.py's by-hand swap of the home's box; 107's home seam
    "_abandon_turn",  # spec 093's child program; 106's session lifecycle
)


def test_the_judge_patches_the_runner_only_through_the_process_object() -> None:
    """Spec 105, Decision 4; spec 108, Decision 5a: a check or a unit test patches nothing private
    in the runner except through process(), but for the allowance above, which only shrinks."""
    files = [p for p in scan.files_under(paths.REPO, "tests") if p.suffix == ".py"]
    hits = scan.seam_hits(files, paths.REPO, SEAM_ALLOWED)
    assert not hits, scan.report(hits)
```

Unit rows in `tests/unit/test_scan.py` (small files under `work`, each a case): a file that
imports `from wasi_python import runner` and calls `monkeypatch.setattr(runner, "_x", 1)` is a
hit `…:line: runner._x` when `_x` is not allowed and silent when it is; `runner._x = 1` as a
plain assignment, the same; `import wasi_python.runner` with `wasi_python.runner._x = 1`, the
same; a program string `"from wasi_python import runner\nrunner._x = 1"` inside the file, the
same; `monkeypatch.setattr(process().observers, "x", 1)`, never a hit; `from wasi_python import
tools` with `monkeypatch.setattr(tools, "_x", 1)`, never a hit (outside the rule);
`monkeypatch.setattr(runner._Home, "_x", 1)`, never a hit (a class attribute); an allowed name no
file patches, `stale allowance: _x`.

**D5. The function ceiling** (Decision 5a). In `tests/harness/scan.py`:

```python
FUNCTION_CEILING = 80  # lines, def to last line (the memo, section 5; spec 108, Decision 5a)


def long_function_hits(files: Iterable[Path], root: Path, allowed: dict[str, int]) -> list[str]:
    """Every function or method (nested ones too) longer than FUNCTION_CEILING lines whose
    `<file>:<qualname>` is not allowed, as `file:line: qualname (n lines)`; and every allowed key
    whose function is at or under the ceiling, or gone, as `stale allowance: key (n lines)`."""
```

The body: parse each file; walk with a parent map so a method's qualname is `Class.method` and a
nested function's is `outer.inner`; `n = node.end_lineno - node.lineno + 1`; a key is
`f"{file.name}:{qualname}"`. In `tests/checks/test_rules.py`:

```python
# Spec 108, Decision 5a: the functions over 80 lines on the tree the check was built on, measured
# by scan.long_function_hits (EXECUTED; the builder writes the keys and lengths found on 107's
# tip). An entry leaves when its function is at or under 80 lines; none is ever added.
LONG_FUNCTIONS = {
    "runner.py:run": 152,
    "runner.py:run_async": 177,
    "runner.py:_instance": 150,
    "runner.py:_open_session": 137,
    "runner.py:Session.__init__": 169,
    "runner.py:Session.run_async": 81,
    "tools.py:_make": 82,
    "tools.py:_ToolHost._answer": 83,
}


def test_no_function_is_over_eighty_lines() -> None:
    """The memo's section 5; spec 108, Decision 5a: no function in src/wasi_python is over 80
    lines but for the allowance above, which only shrinks; a stale entry is red."""
    files = [p for p in scan.files_under(paths.REPO, "src") if p.suffix == ".py"]
    hits = scan.long_function_hits(files, paths.REPO, LONG_FUNCTIONS)
    assert not hits, scan.report(hits)
```

The keys above are `a9064a2`'s (EXECUTED); 104's move changes the file part of the first six and
106 may shorten some, so the builder writes the keys and lengths measured on 107's tip, in the
landing notes with the command. The lengths in the dict are the record, not the test: the check
reads the ceiling, not the recorded length. Unit rows: a module with an 81-line function is a hit
`…:line: f (81 lines)`; at 80 lines, silent; a method of a class is keyed `C.m`; a function
nested in `f` is keyed `f.g`; an allowed key whose function is 80 lines is `stale allowance:
…`; an allowed key with no such function, the same.

### E. The roadmap and the CHANGELOG

**E1. `context/roadmap.md`**, a "Reserved" paragraph in "Where 0.1.0 stands", after the
paragraph "Reserved: 101 (a faster release run …)":

```
Reserved: 108 (a structural review is a stage; the last of the chain 103 to 108 that
`research/2026-10-20-a-design-review-of-the-runner.md`, section 8, sets out; the owner,
2026-10-20): the rule "Structure is reviewed, not only behaviour" in AGENTS.md, the eight-row
rubric, its measurements and a template in `reviews/README.md`, one line in the reviewer's
checklist, four rules checks (a released version has its structural review; a built structural
specification cites its pre-build review; the judge patches the runner only through the process
object, with 105's allowance that 107 shrinks; no function over 80 lines, with the tree's
offenders as an allowance that only shrinks), and question 108 for the owner's amendment of
§5.6. Parallel-safe, context and judge only; before 0.1.0, since 0.1.0 is the first release the
rule gates.
```

**E2. `context/roadmap.md`**, the "Release rule" paragraph: the text "Before 0.1.0: a security
review of the whole surface (milestone 6)," becomes "Before 0.1.0: a security review of the
whole surface (milestone 6), a structural review of `src/` against the design review's rubric
(spec 108; `reviews/0.1.0-structural-review-<date>.md`, written by a fresh agent on the commit
before the bump and committed with it, the dry run on that commit),".

**E3. `CHANGELOG.md`**, under `## 0.1.0a8 — unreleased`, a bullet:

```
- **A structural review is a stage** (spec 108; the design review of 2026-10-20). A change that
  adds a module-level mutable or lock, a use of wasmtime-py's private API, a platform branch or a
  test seam outside the one place specs 103 to 107 give each, or takes a module past the size
  ceiling or a function past 80 lines, is reviewed before it is built; every release gets a
  structural review of `src/` against the design review's eight-row rubric, beside its security
  review, which the judge requires of a released version; and two rules checks hold that the
  judge patches the runner only through its process object and that no function is over 80
  lines, each with an allowance list that only shrinks. Nothing in the artifact set or the wheel
  changes.
```

## Scope

In: Decisions 1 to 7, 5a included; the texts of Design A to E, pasted as written.

Out:

- **Amending the constitution.** Question 108 asks; the lane commits the owner's answer
  (Decision 2).
- **The structural review of 0.1.0 itself.** It is written by a fresh agent at the release, on
  the commit before the bump, not by this specification's builder (Decision 4).
- **A rules check that the security review was written.** None exists; adding one changes what
  the judge requires of a stage the constitution already names, which is the owner's reason to
  give, not this specification's (Decision 8).
- **The other structural checks and their numbers** (specs 103 to 107): the private-API seam
  (103), the module size ceiling (104), the lock and mutable checks (105), the type checker
  (106), the platform-branch and citation rules (107), and the module names, which are theirs
  (Decision 1). The seam check and the function ceiling are in (Decision 5a).
- **Moving a seam or shortening a function.** The two allowance lists record what the tree
  holds; fixing an entry is 106's or 107's, or a later specification's (Decision 5a).
- **A measurement script in the harness.** Commands suffice (Decision 3).
- **Any file under `src/`**, any artifact byte, any line of `tests/public_api.txt`.

## Acceptance criteria

1. **The texts are in the tree, verbatim.** AGENTS.md carries bullet A1 in its place and rule 8
   carries clause A2; `context/reviews/README.md` carries item 4a and the section B2;
   `context/questions-for-the-owner.md` carries question 108 under "## Open", in the file's
   format, and `decisions.md` is untouched; the roadmap and the CHANGELOG carry E1 to E3. The
   build review diffs each against Design and finds no difference beyond `ruff format`'s line
   breaks in D.
2. **Check (a) exists and was seen failing first.** Seen failing on the real tree without editing
   `src/`: `uv run python -I -c "import sys; sys.path.insert(0, 'tests'); from pathlib import
   Path; from harness import scan; print(scan.structural_review_errors('0.1.0',
   Path('context/reviews')))"` prints the one error naming `0.1.0-structural-review-<date>.md`;
   the message is in the landing notes. Then `uv run pytest
   tests/checks/test_rules.py::test_a_release_has_its_structural_review -q` passes on the tree,
   whose version is a prerelease (`0.1.0a8` at drafting), the version read by `read_version`.
3. **Check (b) exists and was seen failing first**, on a fixture specification (the unit row's
   `112-c.md` case) and on the tree: `uv run pytest
   tests/checks/test_rules.py::test_built_structural_specifications_cite_their_pre_build_review
   -q` passes, since no Kind line carries the token (or, if 103 to 107 added it at the wave,
   since each cites its `-spec-` review). With this specification's own Status set to
   `**built …**` in the worktree and no `-spec-` citation, the check names this file; with the
   citation of its pre-build review, it passes (both recorded).
4. **The seam check exists and was seen failing first.** On 107's tip with `SEAM_ALLOWED` empty
   the check lists every patched runner name (recorded); with the twenty-four, minus those no
   test patches on that tip (each removal named), it passes and lists nothing else; with one
   allowed name no file patches, it reports `stale allowance` (recorded). The unit rows of D4
   pass, each seen failing first on the base (`AttributeError`, no `seam_hits`).
5. **The function ceiling exists and was seen failing first.** On 107's tip with
   `LONG_FUNCTIONS` empty the check lists every function over 80 lines (recorded, EXECUTED, the
   keys and lengths that become the allowance); with them, it passes; with one key whose
   function is under 80 lines, `stale allowance` (recorded). The unit rows of D5 pass, each seen
   failing first on the base.
6. **The unit rows of D3 pass, each seen failing first:** on the base (107's tip) both rows fail
   with `AttributeError` (no `structural_review_errors`), recorded in the landing notes; on the
   build every case of D3 passes. `ruff check` and `ruff format --check` are clean on `src/` and
   `tests/`.
7. **No verdict moves.** The fast tier in the worktree on the frozen `v0.1.0a7` set (the memo,
   section 8), `-n 3` when another judge runs: green; `uv run python tests/harness/sameness.py
   <the baseline record> build/progress/latest.json` lists exactly the four new rows of D2, D4
   and D5 and the unit suite's count, and nothing else; the output is in
   `build/108/sameness.txt`.
8. **The open-question scan is green with the new texts:** `uv run pytest
   tests/checks/test_rules.py::test_specifications_have_no_open_question
   tests/checks/test_rules.py::test_specifications_have_their_header_and_sections -q` passes
   (it reads AGENTS.md and every specification, this one included).
9. **Nothing under `src/` changed:** `git diff --stat <base>..HEAD -- src tests/public_api.txt`
   is empty; no artifact is rebuilt; `uv run python tests/harness/api.py` reports no change.
10. **The release workflow:** no dispatch of its own. The chain's one dispatch on its final tip
    (the owner, 2026-10-20) is this specification's run, since this is the tip; its id goes in
    the landing notes, every red line a growth line claimed by 103 to 107 or none.

Ten criteria. Criteria 2 to 6 are the "check before the code" of AGENTS.md rule 3; criterion 7
is the chain's rule.

## For the lane

- **Kind:** parallel-safe, context and judge only; the last entry of the chain's wave (the owner,
  2026-10-20: all six land as one wave, past §5.7's five). It rebases onto 107's tip in the
  lane's order; no other entry in the wave should touch `AGENTS.md` rule 8, `reviews/README.md`
  or the questions file, so no conflict is expected; `roadmap.md`, `CHANGELOG.md` and
  `tests/checks/test_rules.py` merge textually with 103 to 107's lines, each named if it
  conflicts.
- **The claim list** (each line starts "108:"):
  - 108: **new checks (4 nodes), each passing, no fuel, no bytes:**
    `tests/checks/test_rules.py::test_a_release_has_its_structural_review`,
    `…::test_built_structural_specifications_cite_their_pre_build_review`,
    `…::test_the_judge_patches_the_runner_only_through_the_process_object` and
    `…::test_no_function_is_over_eighty_lines`.
  - 108: **unit rows:** `tests/unit/test_scan.py` gains four rows (D3's two, D4's one, D5's one;
    the suite's count rises by four; the builder restates the count if it splits a row).
  - 108: **retired checks:** none. **Lost passes:** none. **Grown rows:** none.
  - 108: **the judge hash changes** in `tests/harness/scan.py`, `tests/checks/test_rules.py` and
    `tests/unit/test_scan.py`.
- **The flags** (paste-safe):

  ```
  --accept "108: a structural review is a stage: the rule in AGENTS.md, the rubric and template in reviews/README.md, the reviewer's checklist line 4a, question 108 for the owner's amendment of §5.6, and the two checks of the letter the chain handed here (the seam check with 105's allowance, the function ceiling with the tree's offenders)"
  --accept-judge "108: four rules checks: a released version (X.Y.Z, no suffix) has context/reviews/<version>-structural-review-<date>.md scoring R1 to R8; a built or landed specification whose Kind line carries **structural** cites its own existing -spec- review; the judge patches the runner's private names only through process() but for SEAM_ALLOWED (105's twenty-four names, only ever removed, a stale entry red); no function in src/wasi_python over 80 lines but for LONG_FUNCTIONS (the tree's offenders on 107's tip, only ever removed); four unit rows in test_scan.py; no existing expectation edited"
  ```

- **Dry-run needs:** none beyond the chain's one dispatch on this tip (criterion 10). The four
  checks run in the `own-rest` shard on macOS and Linux, where `test_rules.py` runs (spec 063,
  Decision 18: not on Windows); they read files only.
- **At the release of 0.1.0:** the lane's order of operations is Decision 4's; the first
  `0.1.0-structural-review-<date>.md` is written then, by a fresh agent, in the README's
  template, of the commit before the bump.

## Disposition of the pre-build review

The review (`../reviews/108-a-structural-review-is-a-stage-spec-2026-10-20.md`) re-ran the
shape checks, every measurement command and the pasted scanner code against the unit cases and
the real tree. Every finding is written in; the owner decided M1 (2026-10-20).

- **M1, written in (the owner's decision).** This specification owns the seam check (105's AST
  walk against an allowance list, 105's twenty "stays" names plus the two the checks alone patch
  and the two plain assignments found here, 107 shrinks it) and the function ceiling (the memo's
  "no function over 80 lines", an allowance list of the tree's offenders, measured EXECUTED);
  the module size ceiling is 104's, and 106's hand-off is corrected in 106's own round. The
  allowance rule is stated: an entry is removed when its seam or function is fixed, never added,
  and a stale entry fails the check. Decisions 1 (triggers 4 and 5), 5, 5a (new), 8; Design D4
  and D5; Scope; Acceptance 4 and 5; the claim list and flags; A1, B1, C, E1, E3 name the two
  checks or the function ceiling.
- **M2, written in (the reviewer's order).** The review is of the commit before the bump (its
  `src/` ships); it is committed with the bump; the dry run runs on that commit; the tag follows
  `release/version.py release`'s CHANGELOG-only commit, as rule 6b allows. Decision 3 (when),
  Decision 4 (the order, with the wrong clause removed), B2's first bullet and template, E2.
- **M3, written in.** The check matches the bold token `**structural**` (D1, `STRUCTURAL_TOKEN`),
  with the unit case `109-z.md` for the word without the token (D3); the Kind line is reworded
  without the word; the grep claim is replaced by the tree's real output, restricted to Kind
  lines, EXECUTED with 103 to 108 present (Decision 4b). Criterion 3 records the check on this
  file's own Status.
- **L4, written in.** `re.match(r"(built|landed)\b", status)` (D1), with the unit case `115-g.md`
  ("drafted …, to be built on 107's tip") (D3); Decision 4b says why the line's start.
- **L5, written in.** "The four checks run in the `own-rest` shard on macOS and Linux, where
  `test_rules.py` runs (spec 063, Decision 18: not on Windows); they read files only" (For the
  lane).
- **L6, written in.** A1 lists `platform.system()` with the other two.
- **L7, written in.** The box text is the reviewer's: measurements first, then the diff since the
  last structural review and the modules whose measurements moved, the whole of `src/` only when
  no review precedes it (Decision 3, B2).
- **Note 8, written in.** D2 reads the version through `release/version.py`'s `read_version`,
  the loader factored into `_release_version_module()` shared with
  `test_the_version_is_released_by_the_book`; `VERSION_LINE` is not duplicated.

## One line

A change that would turn the runner back into one file is reviewed before it is code, and every
release is scored against the memo's eight rows by someone who did not write it, with the judge
refusing a release that skipped it.

## Landing notes

Built 2026-10-20 and 2026-10-21 in the worktree `/home/user/wt/108`, branch
`spec/108-a-structural-review-is-a-stage`, from the base `0e145b7` (the PR branch
`claude/gallant-ride-9nxxmn`'s tip: 107's reviewed and landed tip, its build review's
disposition written in). Every number here is EXECUTED on that base or on the built commit, with
its command; the outputs are kept under `build/108/` in the worktree (git-ignored):
`measure-base.txt` (the two measurements on the base, by a scratch walk), the seen-failing
records `seen-failing-review-checks.txt`, `seen-failing-release-review.txt`,
`seen-failing-structural-spec.txt`, `seen-failing-seams.txt`,
`seen-failing-seams-empty-allowance.txt`, `seen-failing-seams-stale.txt`,
`seen-failing-long-functions.txt`, `seen-failing-long-functions-empty-allowance.txt`,
`seen-failing-long-functions-stale.txt`, `verbatim.txt` (each Design block found verbatim in
its file), `api-check.txt`, `mypy.txt`, `fast-tier.sh`, `with-sigint.py`, `fast.log`,
`built.json`, `claims.toml`, `claims-chain.toml`, `sameness-107.txt`,
`sameness-baseline-chain.txt`.

- **Rebase onto main** (the coordinator, 2026-10-21): rebased onto main's `dda6075` with the
  chain; no conflict in this entry's commits (main's `tests/harness/scan.py` block of spec 099
  sits before the chain's additions, and this entry's hunks replayed clean). Hashes: `0540fc7`
  → `6e99c88`, `f645bd7` → `b8047ae`, `4b99408` → `b2aa167`, `75a4d98` → `dfd2a58`, `3942323` →
  `74be2b6`, `3dc9f1f` → `eacacbb`, `64de806` → `0a46365`, `d92307f` → `ab84933`.
- **Commits, in the order built** (`git log --oneline 0e145b7..`): `0540fc7` (Decision 4, Design
  D1 to D3: `structural_review_errors` and `structural_spec_review_errors` in the harness, the
  two checks, the two unit rows, the loader of `release/version.py` factored into
  `_release_version_module()`), `f645bd7` (Decision 5a, D4: `seam_hits`, the seam check,
  `SEAM_ALLOWED`, its unit row), `4b99408` (Decision 5a, D5: `long_function_hits`, the function
  ceiling, `LONG_FUNCTIONS`, its unit row), `75a4d98` (Design A, B, C: the AGENTS.md bullet and
  rule 8's clause, the README's item 4a and section, question 108), `3942323` (the version
  loader's return annotation in place of a `noqa` for a rule ruff does not enable), and the
  commit after it (this Status line and these notes). `git diff --stat 0e145b7 `3942323``:
  6 files changed, 672 insertions(+), 5 deletions(-) (`tests/` three files; `src/` none; `AGENTS.md`, `context/reviews/README.md`,
  `context/questions-for-the-owner.md`). No model name in any repository file.
- **CI: none of its own; the chain's one dispatch on the final tip** (criterion 10; the owner,
  2026-10-20). This specification is the chain's tip, so that dispatch is this specification's
  run; its id is the lane's to write here when it dispatches. The fast tier below is the build's
  judge.
- **The texts are in the tree, verbatim (criterion 1):** each Design block, read from the
  specification's own fence and searched for in its file (`verbatim.txt`): A1 17 lines and A2 3
  lines in `AGENTS.md`, B1 5 lines and B2 117 lines in `context/reviews/README.md`, C 37 lines in
  `context/questions-for-the-owner.md`, all five found whole. A1 sits after "Nothing lands
  unreviewed" and before "Code speaks for itself", the bullet the owner added on 2026-10-20
  between the two the Design names (Decision 1 says "right after Nothing lands unreviewed"). The
  roadmap and CHANGELOG lines (E1 to E3) are proposed below and not written, as 103 to 107's
  were: both files are the lane's at the wave (the lane's instruction to this builder).
- **The checks were seen failing first (criteria 2 to 6):** on the base's `scan.py`, the two
  review checks fail `AttributeError: module 'harness.scan' has no attribute
  'structural_review_errors'` and `… 'structural_spec_review_errors'`, and the unit file errors
  at collection on `STRUCTURAL_ROWS` (`seen-failing-review-checks.txt`); the seam row and check,
  `… no attribute 'seam_hits'`; the ceiling row and check, `… no attribute 'FUNCTION_CEILING'`
  and `… 'long_function_hits'`. Criterion 2 on the real tree: `scan.structural_review_errors
  ('0.1.0', Path('context/reviews'))` prints `['0.1.0 is a release; reviews/ has no
  0.1.0-structural-review-<date>.md']` and `('0.1.0a8', …)` prints `[]`; the check passes on the
  tree, whose `read_version` gives `0.1.0a8`. Criterion 3 on this file
  (`seen-failing-structural-spec.txt`): with its Status set to `**built 2026-10-20**` and the
  tree's Kind line, `[]` (the line carries no token, which is Decision 4b's design); with the
  token `**structural**` added to the Kind line and the citation of its pre-build review
  present, `[]`; with the token and the citation's file name changed, `['108-a-structural-
  review-is-a-stage.md: structural and built, but cites no reviews/108-<slug>-spec-<date>.md']`.
  On the tree, `grep -rhn '^- \*\*Kind:\*\*' context/specifications | grep -c
  '\*\*structural\*\*'` → `0`, and the plain word → `0`; 103 to 107's Status lines begin "built
  on", each citing its `-spec-` and build reviews, and none carries the token, so the check
  reads nothing of them; 109 has no file under `specifications/`. Criterion 4
  (`seen-failing-seams-empty-allowance.txt`): with `SEAM_ALLOWED` empty, **36 sites, 18 names**,
  below; with the eighteen, green; with `_nobody_patches_this` added, `stale allowance:
  _nobody_patches_this`. Criterion 5 (`seen-failing-long-functions-empty-allowance.txt`): with
  `LONG_FUNCTIONS` empty, the nine below; with them, green; with `_process.py:process` (a 3-line
  function) added at 90, `stale allowance: _process.py:process (3 lines)`. Criterion 6: every case
  of D3 passes; `ruff check` and `ruff format --check` clean on `src/` and `tests/`.
- **The seam allowance as measured and as allowed (Decision 5a, EXECUTED on `0e145b7` by the
  check's own walk, `scan.seam_hits` over every `.py` under `tests/` with the allowance empty):**
  36 sites, 18 names: `_home._ctrl_c_watched` 8 (`test_async_tools.py:348`, `test_runner_async.py:24,
  75, 200`, `test_runner_cancel.py:52, 112`, `test_runner_mounts.py:172`, `test_runner_tools.py:366`),
  `_home._join_guest` 3 (`test_runner_threads.py:260` by `setattr`; `test_v1_2_hostile_guest.py:2961`
  and `:3152` assigned in child programs, the second a tuple target), `_artifacts._ARTIFACT_DIR` 2
  and `_artifacts._CHECKOUT_ARTIFACT_DIR` 2 (`tests/test_api.py:30, 31, 44, 45`), `_call._drive` 2
  (`test_runner_mounts.py:500`; `test_v1_2_hostile_guest.py:2938`, a tuple target in a program),
  `_call._epoch_now` 2, `_call._stop_error` 2, `_engines._module_miss` 2, `_home._Box` 2
  (`test_runner_threads.py:215, 220`, assigned), `_private_dirs._REMOVE_BUDGET` 2
  (`test_runner_sweep.py:745, 764`, through the fixture named `m`), `_private_dirs._drop` 2,
  `_artifacts._found_and_checked` 1, `_home._stack` 1, `_places._check_preopens` 1,
  `_places._walk_grants` 1, `_sessions._abandon_turn` 1 (`test_v1_2_hostile_guest.py:3138`, in a
  program), `_sessions._drive_turn` 1 (`:3133`, a tuple target in a program),
  `runner._current_defaults` 1. **Against 107's "for 108" list:** every name and count agrees but
  `_sessions._Phase`, which 107's grep counted at `test_runner_sessions.py:104`, a parameter's
  annotation with a default (`phase: _sessions._Phase = _sessions._Phase.OPEN`), not a patch; the
  AST walk does not see it and it is not allowed. **Against the specification's twenty-four:**
  fourteen stay (`_drop`, `_drive`, `_stack`, `_ctrl_c_watched`, `_stop_error`, `_epoch_now`,
  `_module_miss`, `_found_and_checked`, `_join_guest`, `_walk_grants`, `_check_preopens`,
  `_current_defaults`, `_Box`, `_abandon_turn`); ten are removed because no test patches them on
  this tree: the nine 107 retired into `_platform.py` (`_guest_stack`, `_tell_interpreter`,
  `_trap_handlers_ready`, `_dir_fd_ok`, `_win_open`, `_close_held`, `_try_lock`, `_unlock_close`,
  `_remove_tree`) and `_context_address` (`grep -rn _context_address tests` → none); four are
  patched and were not on the twenty-four: `_ARTIFACT_DIR` and `_CHECKOUT_ARTIFACT_DIR` (the
  artifact folders `tests/test_api.py` redirects), `_REMOVE_BUDGET` (the sweep's budget) and
  `_drive_turn` (the turn's driver, in 093's child program). None has a field on the process
  object (`_process.py`'s fields: observers, clock, `start_ending`, `drive_folder`, the reaper's
  two), so none can be fixed in the test through `process()` today; the specification's rule for
  that remainder names them to the chain's integration review as 105's or 107's to close, and
  they enter the initial allowance with their closers so the check is green on the tree:
  parameters of `artifacts()` or fields of the process object for the two folders, a parameter of
  the remover for the budget, a row of the session's lifecycle table for the driver. **The
  allowance is eighteen names**, grouped by module in `test_rules.py` with the closer of each
  group; it only shrinks from here.
- **The function ceiling as measured and as allowed (Decision 5a, EXECUTED on `0e145b7` by
  `scan.long_function_hits` with the allowance empty, lines def to last line):** nine:
  `runner.py:run` 151, `runner.py:run_async` 176, `runner.py:Session.__init__` 173,
  `runner.py:Session.run_async` 82, `_sessions.py:_open_session` 150, `_call.py:_instance` 159,
  `_process.py:_Process.__init__` 82, `tools.py:_make` 82, `tools.py:_ToolHost._answer` 83. The
  specification's eight at `a9064a2` are these under their new files after 104's split
  (`_open_session` into `_sessions.py`, `_instance` into `_call.py`) with 106's lengths (`run`
  152 → 151, `run_async` 177 → 176, `_instance` 150 → 159, `_open_session` 137 → 150,
  `Session.__init__` 169 → 173, `Session.run_async` 81 → 82), plus one more, `_Process.__init__`,
  105's process object, 82 lines of one field per line with its comment. The lengths in the dict
  are the record; the check reads the ceiling.
- **What the reviews' checks read (Decision 4):** `test_a_release_has_its_structural_review`
  reads `release/version.py`'s `read_version` of `src/wasi_python/__init__.py` (`0.1.0a8`, a
  prerelease: `RELEASE_VERSION` does not match, no file is required) and would read
  `context/reviews/0.1.0-structural-review-<date>.md` for the tokens `R1` to `R8` and the eight
  row names; `test_built_structural_specifications_cite_their_pre_build_review` reads every
  `context/specifications/*.md`'s Kind line for the bold token and, where it is there and the
  Status begins `built` or `landed`, the file's citations of `reviews/NNN-<slug>-spec-<date>.md`.
  The whole rules file: `uv run pytest tests/checks/test_rules.py -q` → **53 passed, 4 skipped**
  (49 and 4 on the base), the open-question and shape scans among them, with AGENTS.md's new
  bullet and this specification read (criterion 8).
- **Nothing under `src/` changed (criterion 9):** `git diff --stat 0e145b7..HEAD -- src
  tests/public_api.txt` is empty; `uv run python tests/harness/api.py --check` exits 0 and prints
  nothing; `uv run mypy --strict src/wasi_python` → `Success: no issues found in 18 source files`.
- **The fast tier on the frozen `v0.1.0a7` set** (`WASI_PYTHON_ARTIFACTS=/home/user/wasi_python/build/baseline-a7/set/wasi-python-0.1.0a7`,
  `uv run pytest -m "not slow" -n 3 -q -p no:cacheprovider`, under the machine's
  `build/fast-tier.lock`, `SIGINT` at its default through `with-sigint.py`): **83 failed, 2440 passed, 52 skipped in 290.11s (0:04:50)** on
  `3942323`, the final code commit, the tree unchanged for the run's length. The failures are
  the chain's baseline's `failing-nodes.txt` exactly (`diff` of the sorted lists empty,
  `build/108/failed-nodes.txt`: 82 checks of an artifact set older than the tree, and
  `test_runner_grants.py::test_the_walk_judges_links`, which needs a non-root user); 107's
  record had 2432 passed, the four more being the four rules checks. The record is
  `build/108/built.json` (`fast.log`), copied from `build/progress/latest.json` as the run ended;
  the ratchet line names the judge changed. An earlier run on `75a4d98`, before the annotation commit, gave the same counts and the same 83 (`fast-run1.log`, `built-run1.json`, 383.96 s; its two sameness lines read the same).
- **Sameness (criterion 7).** Against 107's reviewed record (`/home/user/wt/107/build/107/review.json`)
  with `--claims build/108/claims.toml` (`build/108/sameness-107.txt`):

```
note: explained by claims: 108 5
sameness exit 0
```

  Against the chain's baseline (`/home/user/wasi_python/build/baseline-a7/baseline.json`) with
  the chain's claims (`build/108/claims-chain.toml`: 107's list, then this one's;
  `build/108/sameness-baseline-chain.txt`):

```
note: explained by claims: 103 4 · 104 3 · 105 4 · 106 3 · 107 4 · 108 5
sameness exit 0
```

  The claim: `new` the four rules checks; `units = 4` for the four scanner rows in
  `tests/unit/test_scan.py` (the record names a unit file, not its rows, so an existing file's
  new rows go by the suite tally). No row grows, no pass moves.
- **The judge's files (the claim list's hash line):** `tests/checks/test_rules.py`,
  `tests/harness/scan.py`, `tests/unit/test_scan.py`.

### For the lane, as built

- **Kind:** parallel-safe, context and judge only; the last entry of the chain's wave, rebased
  after 107. No other entry touches `AGENTS.md`'s rule 8, `reviews/README.md` or the questions
  file; `tests/checks/test_rules.py` merges textually with 103 to 107's checks (this one appends
  at the file's end and after `test_landed_specifications_cite_an_existing_review`).
- **The claim list** (each line starts "108:"):
  - 108: **new checks (4 nodes), each passing, no fuel, no bytes:**
    `tests/checks/test_rules.py::test_a_release_has_its_structural_review`,
    `::test_built_structural_specifications_cite_their_pre_build_review`,
    `::test_the_judge_patches_the_runner_only_through_the_process_object`,
    `::test_no_function_is_over_eighty_lines`.
  - 108: **unit rows:** `tests/unit/test_scan.py` gains four rows (D3's two, D4's one, D5's
    one): the suite's count rises by four.
  - 108: **retired checks:** none. **Lost passes:** none. **Grown rows:** none.
  - 108: **the judge hash changes** in `tests/harness/scan.py`, `tests/checks/test_rules.py`
    and `tests/unit/test_scan.py`.
- **The flags** (paste-safe; the spec's, adjusted to what was built):

  ```
  --accept "108: a structural review is a stage: the rule in AGENTS.md, the rubric and template in reviews/README.md, the reviewer's checklist line 4a, question 108 for the owner's amendment of §5.6, and the two checks of the letter the chain handed here (the seam check with the eighteen names the judge still patches on 107's tip, the function ceiling with the tree's nine offenders)"
  --accept-judge "108: four rules checks: a released version (X.Y.Z, no suffix) has context/reviews/<version>-structural-review-<date>.md scoring R1 to R8; a built or landed specification whose Kind line carries **structural** cites its own existing -spec- review; the judge patches the runner's private names only through process() but for SEAM_ALLOWED (eighteen names measured on 107's tip, by setattr under any fixture name, by assignment with tuple targets, and inside child programs, only ever removed, a stale entry red); no function in src/wasi_python over 80 lines but for LONG_FUNCTIONS (the tree's nine offenders on 107's tip, only ever removed); four unit rows in test_scan.py; no existing expectation edited"
  ```

- **Dry-run needs:** none beyond the chain's one dispatch on this tip (criterion 10). The four
  checks run in the `own-rest` shard on macOS and Linux, where `test_rules.py` runs (spec 063,
  Decision 18: not on Windows); they read files only.
- **For the integration review:** the four allowed seams outside the specification's twenty-four
  (`_ARTIFACT_DIR`, `_CHECKOUT_ARTIFACT_DIR`, `_REMOVE_BUDGET`, `_drive_turn`), named above with
  their closers, to assign to 105's or 107's follow-up.
- **At the release of 0.1.0:** the lane's order of operations is Decision 4's; the first
  `0.1.0-structural-review-<date>.md` is written then, by a fresh agent, in the README's
  template, of the commit before the bump.
- **CHANGELOG line proposed** (not written; the file is the lane's), under the one unreleased
  section, the specification's E3 verbatim: *A structural review is a stage (spec 108; the
  design review of 2026-10-20). A change that adds a module-level mutable or lock, a use of
  wasmtime-py's private API, a platform branch or a test seam outside the one place specs 103
  to 107 give each, or takes a module past the size ceiling or a function past 80 lines, is
  reviewed before it is built; every release gets a structural review of `src/` against the
  design review's eight-row rubric, beside its security review, which the judge requires of a
  released version; and two rules checks hold that the judge patches the runner only through
  its process object and that no function is over 80 lines, each with an allowance list that
  only shrinks. Nothing in the artifact set or the wheel changes.*
- **Roadmap lines proposed** (not written; the file is the lane's at the wave), three:
  - E1, the paragraph "Reserved: 108 (a structural review is a stage; …)" verbatim from the
    specification, placed after "Reserved: 101" and before "Reserved: 109", which the roadmap
    already carries.
  - E2, the "Release rule" paragraph's "Before 0.1.0: a security review of the whole surface
    (milestone 6)," becoming "Before 0.1.0: a security review of the whole surface (milestone
    6), a structural review of `src/` against the design review's rubric (spec 108;
    `reviews/0.1.0-structural-review-<date>.md`, written by a fresh agent on the commit before
    the bump and committed with it, the dry run on that commit),".
  - The build review's finding 1 (Low, context only; its exact text), one paragraph after E1's
    "Reserved: 108" paragraph: "Reserved: a closer for spec 108's two allowances (the eighteen
    private runner names the judge still patches, `SEAM_ALLOWED` in
    `tests/checks/test_rules.py`, each with the field or parameter its comment names; the nine
    functions over 80 lines, `LONG_FUNCTIONS`): parallel-safe, `src/` and the tests that patch,
    one specification or two; before the first structural review scores R6 and R7, or named in
    that review as the Medium's reserved specification." The eighteen include the four names
    outside the specification's twenty-four, `_ARTIFACT_DIR`, `_CHECKOUT_ARTIFACT_DIR`,
    `_REMOVE_BUDGET` and `_drive_turn` (named above for the integration review as 105's or 107's
    to close); the closer reserved here owns them with the other fourteen and the nine
    functions.

### The builder's self-check

- rebased onto the named stacked base today: built on `0e145b7`, the base commit in the Status
  line; no rebase since (the PR branch has not moved).
- CI run: none of its own, by the chain's rule (the owner, 2026-10-20); the Windows criterion is
  named: the four checks run only on macOS and Linux (`own-rest`); they read files.
- every number from a measured run on this base, labelled EXECUTED; no growth list (no
  artifact byte, no guest fuel).
- "For the lane": the claim list, the exact flags, each reason beginning with the spec number,
  the wave kind (parallel-safe, context and judge), dry-run needs.
- every new check seen failing first; no Windows or Linux branch in the checks (they read
  files; the one platform difference, `\\` in a path, is in `scan.rel`, which they share).
- gaps: none; reserved follow-ups: the four seams for the integration review, above.
- `packages.toml`: untouched (no package); README rows: none change.
- CHANGELOG: proposed above, not written (the lane's); the question: 108, the next free number
  (`grep -ohE 'question (1[0-9][0-9])' context/*.md | sort -t' ' -k2 -n | tail -1` → `question
  107` before this build).
- `ruff check`, `ruff format --check`, the fast tier: green but for the baseline's failures,
  output in `build/108/`.

### Differences from the specification's text, each with its reason

1. **The judge's new code names no specification, decision, memo or review.** Design D's
   docstrings and comments cite "spec 108, Decision 4" and the memo; the owner's rule of
   2026-10-20 ("Code speaks for itself", AGENTS.md) binds every code file, 107's checks set the
   form, and 109 clears the rest of `tests/`; so each reason is given in words (the AGENTS.md
   rule's name where a document must be pointed at). The names, signatures, messages and cases
   are the Design's.
2. **The seam walk sees more forms than the two the Design lists**, because the tree holds them:
   a `setattr` on the fixture under any name (`m.setattr`, `test_runner_sweep.py:745, 764`,
   without which `_REMOVE_BUDGET` would be a stale entry); a tuple target (`_call._drive,
   wasmtime.Store.close = …`, `test_v1_2_hostile_guest.py:2938`, and `:3133`); a string constant
   parsed as a program and walked with its own imports (the hostile-guest programs import
   `_home`, `_call` and `_sessions` themselves; the file does not, so the Design's regex against
   the file's imports found one of their five sites); an f-string's pieces read as one text; and
   the dotted-string form `setattr("wasi_python.<mod>._name", …)` (no site today, one branch).
   The regex of the Design stays as the fallback for a string that does not parse. Each form
   has a unit case.
3. **`SEAM_ALLOWED` is eighteen names, not twenty-four**, for the reasons measured above: nine
   retired by 107, `_context_address` patched nowhere, and four names outside the twenty-four
   that no process field can take today, entered with their closers and named for the
   integration review (the specification's own rule for the remainder, read with "the check is
   green on the tree it lands on").
4. **`LONG_FUNCTIONS` is nine entries, not eight**, under 104's files and 106's lengths, plus
   `_process.py:_Process.__init__` (82), which 105 added after `a9064a2`; the specification said
   "never one more" of `a9064a2`'s eight, and the ninth is a function 105 built, measured by the
   check's own walk.
5. **The two allowance lists sit at the end of `test_rules.py`** with 107's structural checks,
   not beside `WASMTIME_GUARDS`, a constant of the release section; the file reads by concern.
6. **A1 sits before "Code speaks for itself"**, the bullet the owner added between the two the
   Design names; Decision 1's "right after Nothing lands unreviewed" holds.
7. **E1 to E3 are proposed in these notes, not written**, as 103 to 107 did; the roadmap and
   the CHANGELOG are the lane's at the wave.
8. **Criterion 3's record on this file needed the token**: the tree's Kind line carries no
   `**structural**` (Decision 4b, M3), so the check names this file only with the token added;
   recorded with and without it.
9. **The seam row's programs are assembled from pieces** (an import in one constant, a patch in
   another), so `tests/unit/test_scan.py` does not trip the check it tests, as `test_clock_reads`
   does for the clock scanner.
10. **The sameness outputs are in two files**, `sameness-107.txt` and
    `sameness-baseline-chain.txt`, 107's names, not criterion 7's `sameness.txt`.
11. **The version loader's helper is annotated `-> types.ModuleType`** (the Design leaves the
    helper's shape to the builder); a first commit carried a `noqa` for a rule ruff does not
    enable, removed in `3942323` before the fast tier's run on the final code commit.

### Disposition of the build review

The build review (`../reviews/108-a-structural-review-is-a-stage-2026-10-21.md`, commit
`64de806`; verdict "lands", one Low in `context/` only, three Notes; its own fast tier on
`3dc9f1f` read 83 failed, 2440 passed, 52 skipped, the baseline's 83 exactly, and both sameness
lines the same as the builder's):

1. **The two allowances have design closers but no numbered closer** (Low) — carried to the
   integration: the review's fix text is a "Reserved:" paragraph for the lane's roadmap commit
   at the wave, copied verbatim into "Roadmap lines proposed" above beside E1 and E2, with the
   four names outside the twenty-four named there too, so the integrator has the roadmap's three
   lines in one place. No code changes; no round.
2. **The seam walk does not see `unittest.mock`, the builtin `setattr`, keyword arguments or a
   non-parsing string's own imports** (Note) — acknowledged: the tree uses none of those forms
   (EXECUTED by the reviewer, its greps over `tests/`); the specification that next touches the
   scanner, or the first that reaches for one of them, adds the form and its unit row.
3. **A docstring that mentions `runner._x = 1` in prose is a hit** (Note) — acknowledged: the
   check is conservative, the red names its line, and the fix is wording; none on the tree.
4. **`test_rules.py` alone under the frozen set reads 1 failed** (Note) — acknowledged: the
   counts differ by the artifact set; `test_version_states_the_platform_semantics` fails under
   the a7 set (in the baseline's 83) and skips without one; the 53 agree.
