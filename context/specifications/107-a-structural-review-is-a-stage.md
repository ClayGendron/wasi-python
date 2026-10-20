# 107 — A structural review is a stage

- **Status:** **drafted 2026-10-20** on `claude/gallant-ride-9nxxmn` from main `5feb7e9` (the
  memo's commit `a9064a2` on top; `src/` is unchanged from `30e9b41`, the memo's tree: EXECUTED,
  `git diff --stat 30e9b41 a9064a2 -- src` is empty), awaiting its pre-build review. It is the
  last of the stacked chain 102 → 103 → 104 → 105 → 106 → 107 (the memo, section 8; the owner,
  2026-10-20): it is built stacked on 106's reviewed tip, whose commit the builder writes here, and
  lands last in the chain's one wave. A pre-build review is optional for a context-and-judge
  specification (AGENTS.md rule 8); this one asks for it anyway, because it changes the review
  stage itself. A different agent reviews the build.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** parallel-safe, not build-class (§5.7); context and judge only. Files: `AGENTS.md`,
  `context/reviews/README.md`, `context/questions-for-the-owner.md`, `context/roadmap.md`,
  `CHANGELOG.md`, `tests/checks/test_rules.py`, `tests/harness/scan.py`,
  `tests/unit/test_scan.py`. No file under `src/` changes, no artifact byte changes, and it
  changes no line of `tests/public_api.txt`. By Decision 1's own definition it is not structural:
  it adds no module, no global, no seam and no private-API use.
- **Depends on:** 102 to 106, by their rules checks (Decision 5): 102 (one module imports
  wasmtime-py's private API), 103 (the runner becomes a package; the size ceiling), 104 (one owner
  for the process's state; the test seams on the process object), 105 (a type checker in the
  judge), 106 (one platform module; the citation rule). The rule this specification writes names
  those checks as its mechanical half, so it lands after them. Also 092 (`sameness.py`, the judge
  of "no verdict moved", the memo's section 8) and 004 (`release/version.py`'s version form).
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

Specs 102 to 106 fix the structure once. Each adds a rules check that holds its fix: one module
may import `wasmtime._ffi`; no module passes the ceiling; no lock or mutable at module level
outside the process object's module; no platform branch outside the platform module; the type
checker passes. Those checks are regular expressions and an AST walk. They see a
`threading.Lock()` at module level. They do not see a lifecycle encoded in one more boolean flag, a
concern added to a module that is still under its ceiling, a dict used as a lock, or a protocol
object that quietly grows a method only the judge calls. The memo's section 5 names the gap: "A
change that adds a sixth concern to `runner.py` gets no design review, only a behaviour review,
which is how the file got here."

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
judgement half that the five rules checks cannot be, and it makes the judge refuse a release that
skipped it.

## Decisions

### 1. What "structural" means, and where the rule lives

A specification is **structural** when its change to `src/` does any of five things:

1. adds a module-level mutable or a lock outside `src/wasi_python/_process.py` (spec 104's
   owner object);
2. adds a use of wasmtime-py's private API (`wasmtime._ffi`, `wasmtime._bindings`,
   `Func._func`, `_from_ptr`, `caller._context()`, `store.ptr()`) outside
   `src/wasi_python/_wasmtime_ffi.py` (spec 102's seam);
3. adds a platform branch (`sys.platform`, `os.name`, `platform.system()`) outside
   `src/wasi_python/_platform.py` (spec 106's module);
4. adds a test seam (a hook, a flag, a name the judge patches) that is not on the process object
   (spec 104's rule);
5. takes a module past the size ceiling (spec 103's number).

The module names are those specs 102, 104 and 106 give; if one lands under another name, the
rule names the landed one (a one-word context edit, by the lane). A structural specification says
so in its Kind line, with the word **structural**, and is reviewed before it is built, as a
change to the build recipe is, against the rubric of Decision 3. Why these five: they are exactly
what specs 102 to 106 make true and what their rules checks hold (Decision 5). A sixth trigger
with no check behind it would be a rule the judge cannot see; a trigger the checks cover but the
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
  check in one context-and-judge commit, named in `decisions.md`; the pre-build half, the rubric
  and the mirror check stay, since §5.6 already allows a pre-build review for any change and
  AGENTS.md rule 8 already requires one for the runner. Nothing built is lost either way.

### 3. The structural review: when, how long, what it records

`context/reviews/README.md` gains a section, "Structural review" (Design, B). What it decides:

- **When it is written.** Twice. (a) Before every release, by a fresh agent that wrote none of
  the code since the last structural review, on the commit the release's dry run passed (AGENTS.md
  rule 6b), beside the security review. (b) For a structural specification, as a "Structure"
  section of its pre-build review, by that review's reviewer: the eight rows, one line each,
  saying which row the change moves and which way.
- **The time box:** 45 minutes for a release review, the build-class box, since `src/` is read
  whole; the measurements are one command each (below), so the box goes to judgement. The
  "Structure" section of a pre-build review fits inside that review's own box. A review states its
  box.
- **The eight rows**, as a checklist, each with the question the reviewer answers (the memo's
  section 1 restated as questions): R1 contract, R2 safety, R3 layering, R4 process state, R5
  portability, R6 testability, R7 evolvability, R8 operability. Each row gets a score, Strong,
  Adequate or Weak, as the memo scored it, and a one-line reason. The memo's scorecard (section
  2, at `30e9b41`) is structural review zero: the first release review compares with it; each
  later one compares with the last.
- **The measurements**, each a command that runs on any tree, before and after the chain, with
  today's numbers (EXECUTED on `a9064a2`, Design B's table): module sizes; functions over 80
  lines; module-level mutables and locks; private-API uses; platform branches; private names the
  judge patches; `Any` and `type: ignore` counts; the type checker's result (spec 105's check);
  citations of the archive. Where a rules check of specs 102 to 106 reports the same number, the
  review quotes the check's pass line too. Commands, not harness code: the review is a reviewer's
  record, and a command beside a number is what constitution §4.10 asks; a measurement script
  would be judge code with unit rows of its own, for numbers the five checks already hold.
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
- **The template** (Design, B): the header (date, reviewer, reviewed commit, the last structural
  review it compares with, box), the measurements table, the eight rows with then and now,
  findings most severe first, and a one-sentence verdict: "the structure holds", "holds once
  <Mediums are reserved>", or "does not hold: <High>".

### 4. Two rules checks

**(a) A released version has its structural review:
`test_a_release_has_its_structural_review`.** It reads `__version__` from
`src/wasi_python/__init__.py`. When the version is a release, a file
`context/reviews/<version>-structural-review-YYYY-MM-DD.md` must exist and score every row: the
tokens `R1` to `R8` and the eight row names, each present (Design, D).

- **"A release" is a version of the form `X.Y.Z` with no `aN`, `bN` or `rcN` suffix**
  (`release/version.py`'s `FORM`; `Version.parse("0.1.0").is_prerelease` is `False` and
  `"0.1.0a8"`'s is `True`: EXECUTED). Why not every version from 0.1.0 on, prereleases included:
  the tree carries the next prerelease's string for the whole cycle (`0.1.0a8` today, bumped the
  day a7 shipped), so a check keyed on it would be red from the cycle's first commit until a
  review was written of code that did not exist yet. A final version is different: `release/
  version.py bump --to 0.1.0` is run at the release itself, so the check turns red at exactly
  the moment the gate applies and stays red until the review file is committed, which rule 6b
  allows after the dry run (a `context/` commit). The first release is 0.1.0 (the owner,
  2026-10-19: no more alphas), so "from 0.1.0 on" is what the rule gives; and if the owner ever
  cuts a `0.2.0a1`, the AGENTS.md rule still binds the agent to write its review by hand, as the
  security reviews of a2 to a7 were written by hand.
- **The lane's order at 0.1.0:** the dry run passes on main's commit X; a fresh agent writes
  `0.1.0-structural-review-<date>.md` of X and the security review's addendum; the lane commits
  both with the bump to `0.1.0` and the CHANGELOG's date; the fast tier passes on that commit
  (this check among it); the owner tags.

**(b) A built structural specification cites its pre-build review:
`test_built_structural_specifications_cite_their_pre_build_review`**, the mirror of
`test_landed_specifications_cite_an_existing_review`. For every specification whose Kind line
(the `- **Kind:**` line and its continuation lines) contains the word `structural`, and whose
Status line, with its `*` stripped, contains `built` or `landed`: the text must cite
`reviews/NNN-<slug>-spec-YYYY-MM-DD.md` with its own number `NNN`, and the file must exist.

- **Why the word `structural`:** it appears in no Kind line today (EXECUTED, `grep -rn
  structural context/specifications AGENTS.md context/reviews/README.md` is empty), so no
  existing specification trips the check, and it is the word Decision 1 defines.
- **Why `built` or `landed` and not only `landed`:** the review must precede the build; a
  specification that says "built" without a `-spec-` review skipped the stage, and the check
  should say so before the wave, not after. The `*` are stripped because status lines are bold
  (`**landed 2026-10-20 …**`); `status_line()` keeps them.
- **102 to 106** were reviewed before build under rule 8's "the runner's code"; their Kind
  lines need no word, and the check does not fire on them. Their builders may add the word at
  their rebase onto the wave, and then the check reads their `-spec-` reviews, which exist. The
  check binds every structural specification drafted after it lands.

Both are rules checks (fast tier, no artifact), both seen failing first (Acceptance 2 and 3).

### 5. Where the enforcement lives: the letter and the spirit

| rule | the letter (a rules check, mechanical) | the spirit (a review, judgement) |
|---|---|---|
| one module touches wasmtime-py's private API | spec 102's check: only `_wasmtime_ffi.py` imports `wasmtime._ffi` or `wasmtime._bindings` | R3: is the policy still apart from the mechanism; does a new operation belong in the seam |
| modules a person can hold in their head | spec 103's size ceiling | R7: is a module under the ceiling taking a concern that is not its own |
| process state has one owner | spec 104's lock and mutable rule | R4: is a lifecycle still an enum and a table, or did a flag come back |
| seams are injected, not patched | spec 104's seam rule (the judge patches private names only through the process object) | R6: does production code carry a branch only the judge takes |
| the platform is behind one seam | spec 106's platform-branch rule | R5: does the Windows story still read in one file |
| the code explains itself | spec 106's citation rule (M2) | R7: does a new comment say why, or cite an archive |
| types are checked | spec 105's type checker in `test_rules.py` | R7, R1: did `Any` come back; is a contract still a sentence a test checks |

The checks are the five specifications' and are not changed here. This specification adds the
right column: the rubric, the two reviews, the checklist line, and the two checks of Decision 4
that hold the reviews themselves. Why both halves: a regex cannot score R4; a reviewer cannot
read 11,000 lines for a stray lock every wave. Each half holds what the other cannot.

### 6. The reviewer's checklist gains one line

`context/reviews/README.md`'s checklist gains item 4a, between the constitution check and the
probes (Design, B, the exact text): the reviewer says in one line whether the diff adds a concern,
a lifecycle flag, a module-level mutable, a test seam, a platform branch or a private-API use that
the rubric would score down, whether or not a rules check catches it, naming the row; if it does
and the Kind line does not say "structural", that is Medium, because the specification was
structural and was not reviewed as one. Why one line and not a section: every review of a `src/`
change pays it, so it must be cheap; the full rubric is for the two structural reviews.

### 7. No verdict moves

This specification adds two rules checks and unit rows and changes nothing the judge measures.
`uv run python tests/harness/sameness.py` between the baseline record (the fast tier on the
frozen `v0.1.0a7` set, the memo's section 8) and this build's record lists exactly the two new
rows and the unit suite's count, and nothing else (Acceptance 5). The claim list names them.

### 8. Where it meets other specifications and the release

- **102 to 106:** stacked below this one; their checks are Decision 5's left column; their Kind
  lines are their own. The rule's module names are theirs (Decision 1).
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
write the code, with the numbers beside the scores. The judge refuses a release that skipped it.

## Design

| file | change |
|---|---|
| `AGENTS.md` | the bullet "Structure is reviewed, not only behaviour" after "Nothing lands unreviewed"; one clause in rule 8 (A) |
| `context/reviews/README.md` | checklist item 4a; the section "Structural review" with its rubric, measurements, ranking rule and template (B) |
| `context/questions-for-the-owner.md` | question 108 under "## Open", replacing "None." (C) |
| `tests/harness/scan.py` | `STRUCTURAL_ROWS`, `structural_review_errors`, `structural_spec_review_errors` (D) |
| `tests/checks/test_rules.py` | the two checks (D) |
| `tests/unit/test_scan.py` | the unit rows (D) |
| `context/roadmap.md`, `CHANGELOG.md` | the lines in E |

Every text below is ready to paste. The builder pastes it unchanged; the build review diffs the
tree against this section.

### A. AGENTS.md

**A1. The new bullet**, in "Rules that bind all work", inserted after the bullet that begins
"**Nothing lands unreviewed.**" and before "**Commit or push only when asked.**":

```
- **Structure is reviewed, not only behaviour** (spec 107; the design
  review `context/research/2026-10-20-a-design-review-of-the-runner.md`).
  A specification is **structural** when its change to `src/` adds a
  module-level mutable or lock outside `_process.py`, a use of
  wasmtime-py's private API outside `_wasmtime_ffi.py`, a platform branch
  (`sys.platform`, `os.name`) outside `_platform.py`, a test seam that is
  not on the process object, or takes a module past the size ceiling.
  Its Kind line says "structural", and it is reviewed before it is
  built, as a change to the build recipe is (constitution §5.6), against
  the eight-row rubric in `context/reviews/README.md`. The rules checks
  of specs 102 to 106 hold the letter of this; the review holds its
  spirit. Before every release, a fresh agent writes a structural review
  of `src/` against the same rubric,
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
   lifecycle flag, a module-level mutable, a test seam, a platform branch or a private-API use
   that the rubric below would score down, whether or not a rules check catches it? Name the row.
   If it does and the Kind line does not say "structural", that is Medium: the specification is
   structural and was not reviewed as one.
```

**B2. The section**, appended after the "Template" section's closing fence, at the end of the
file:

````
## Structural review

A review of `src/` against the eight-row rubric of
`../research/2026-10-20-a-design-review-of-the-runner.md` (section 1), which is structural
review zero: its scorecard (section 2, at `30e9b41`) is what the first release review compares
with, and each later review compares with the last. It is written twice (AGENTS.md, "Structure
is reviewed"; spec 107):

- **Before every release**, by a fresh agent that wrote none of the code since the last
  structural review, on the commit the release's dry run passed (AGENTS.md rule 6b), beside the
  security review. File: `<version>-structural-review-YYYY-MM-DD.md`, the twin of
  `<version>-security-review-YYYY-MM-DD.md`. The release waits on its High findings; the judge
  refuses a released version with no such file (`test_a_release_has_its_structural_review`).
- **For a structural specification**, as a "Structure" section of its pre-build review
  (`NNN-<slug>-spec-YYYY-MM-DD.md`): the eight rows, one line each, saying which row the change
  moves and which way, and the measurements it claims to change, before and after, by the
  commands below. The judge holds that a built structural specification cites that review
  (`test_built_structural_specifications_cite_their_pre_build_review`).

Time box: 45 minutes for a release review (the whole of `src/` is read; the measurements are one
command each, so the box goes to judgement); the "Structure" section fits inside its review's
box. The review states its box.

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
- **R7 Evolvability.** Can one person hold each module in their head? Does the code say why
  without the archive open? Does the type checker pass? Is the engine upgrade's cost written?
- **R8 Operability.** Do `stats()`, the records and the trap strings still say what the guest
  did? Can a warning deadlock an embedder?

### The measurements

One command each, run from the repository's root on the reviewed commit; the review records the
output beside the score it informs, labelled EXECUTED. Where a rules check of specs 102 to 106
reports the same number, quote its pass line too (`uv run pytest tests/checks/test_rules.py -q`).
The numbers are those of `a9064a2` (EXECUTED 2026-10-20, spec 107), before the chain; the memo's
differ where its method was reading, not a command.

| what (row) | command | at `a9064a2` |
|---|---|---|
| module sizes (R7) | `wc -l src/wasi_python/*.py \| sort -n` | `runner.py` 6,241; `tools.py` 2,450; `mounts.py` 2,235; 11,423 in all |
| functions over 80 lines (R7) | `uv run python -I -c "import ast,pathlib;[print(p.name,sum(1 for n in ast.walk(ast.parse(p.read_text())) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.end_lineno-n.lineno+1>80)) for p in sorted(pathlib.Path('src/wasi_python').rglob('*.py'))]"` | `runner.py` 6, `tools.py` 2 |
| module-level mutables and locks (R4) | `grep -rnE '^_?[a-z]\w*\s*(:[^=]+)?=\s*(threading\.(R?Lock\|Condition\|Event\|Semaphore)\(\|\{\|\[\|dict\(\|list\(\|set\(\|collections\.)' src/wasi_python --include=*.py` | 47 lines: `runner.py` 46, `__init__.py` 1 |
| private-API uses (R3) | `grep -rnE 'wasmtime\._\|\b_ffi\.\|\b_bindings\.\|\._func\b\|_from_ptr\|\._context\(\)\|\.ptr\(\)' src/wasi_python --include=*.py` | 27 lines: `mounts.py` 15, `runner.py` 11, `tools.py` 1 |
| platform branches (R5) | `grep -rnE 'sys\.platform\|os\.name\b\|platform\.system' src/wasi_python --include=*.py` | 22 lines, all in `runner.py` |
| private names the judge patches (R6) | `grep -rhoE 'monkeypatch\.setattr\(\s*\w+(\.\w+)*,\s*"_\w+"' tests --include=*.py \| sort \| uniq -c \| sort -rn` | 59 distinct; `runner._ctrl_c_watched` 8 times, `_remove_tree` 5 |
| `Any` and `type: ignore` (R7) | `grep -rc '\bAny\b' src/wasi_python --include=*.py; grep -rc 'type: ignore' src/wasi_python --include=*.py` | 349 `Any`; 12 ignores |
| the type checker (R7) | spec 105's check by its node id in `tests/checks/test_rules.py`, and the length of its allowlist | none before 105 |
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
- **Reviewed:** main at <commit>, the commit the dry run <run id> passed
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

- **Asked:** 2026-10-20. **Source:** `specifications/107-a-structural-review-is-a-stage.md`,
  Decisions 1 and 2; `research/2026-10-20-a-design-review-of-the-runner.md`, section 5. Your ask
  of 2026-10-20: "this PR should include changes so that this refactor/review process is more a
  part of the normal workflow".
- **The fact:** §5.6 names three kinds of change that are reviewed before they are built, and
  one review before each release, the security review. The review stage has checked behaviour,
  not structure: 89 landed specifications and 187 reviews left `runner.py` at 6,241 lines with 60
  mutable module globals and 27 locks (the memo, section 2, READ). Specs 102 to 106 fix that
  once, and their rules checks hold the letter of the fix. Nothing in the constitution asks a
  reviewer to look at the structure again.
- **The question:** may §5.6 be amended with the two sentences below, and its Status line with
  the entry below? AGENTS.md's rule "Structure is reviewed, not only behaviour" (spec 107) binds
  agents from the wave that lands it, as rule 8's "the runner's code" did on 2026-10-19; the
  constitution is yours to change.
- **The amendment, §5.6.** After "so a wrong design is caught before it is code.": "A
  specification that is structural (AGENTS.md: it adds a module-level mutable or lock outside the
  process object's module, a use of the engine's private API outside the engine seam, a platform
  branch outside the platform module, a test seam not on the process object, or takes a module
  past the size ceiling) is reviewed before it is built in the same way, against the structural
  rubric in `reviews/README.md` (owner, 2026-10-20, question 108)." After the last sentence, on
  the security review: "Before each release a fresh reviewer also writes a structural review of
  `src/` against that rubric, recorded under `reviews/` beside the security review; the release
  waits on its High findings (owner, 2026-10-20, question 108)."
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
    (spec 107, Decision 4). A prerelease needs none from the judge: its string is what the tree
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


def structural_spec_review_errors(path: Path, reviews: Path) -> list[str]:
    """A specification whose Kind line says "structural" cites, once built or landed, its own
    review before build, `reviews/NNN-<slug>-spec-YYYY-MM-DD.md`, and the file exists (spec 107,
    Decision 4: the mirror of landed_review_errors for the pre-build review)."""
    text = path.read_text()
    kind = KIND_LINE.search(text)
    if kind is None or "structural" not in kind[1].lower():
        return []
    status = status_line(text).replace("*", "")
    if not re.search(r"\b(built|landed)\b", status):
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

**D2. `tests/checks/test_rules.py`**, after `test_landed_specifications_cite_an_existing_review`:

```python
VERSION_LINE = re.compile(r'^__version__ = "([^"]+)"$', re.M)


def test_a_release_has_its_structural_review() -> None:
    """AGENTS.md, "Structure is reviewed" (spec 107, Decision 4; constitution §5.6 as question 108
    amends it): a released version has its structural review of src/ under context/reviews/,
    scoring the rubric's eight rows. A prerelease needs none from the judge."""
    init = (paths.REPO / "src" / "wasi_python" / "__init__.py").read_text()
    version = VERSION_LINE.search(init)
    assert version is not None, "src/wasi_python/__init__.py has no __version__ line"
    errors = scan.structural_review_errors(version[1], paths.CONTEXT / "reviews")
    assert not errors, scan.report(errors)


def test_built_structural_specifications_cite_their_pre_build_review() -> None:
    """A specification whose Kind line says "structural" was reviewed before it was built: once
    built or landed, it cites its own `-spec-` review, and the file exists (spec 107, Decision 4)."""
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


def test_a_built_structural_spec_cites_its_pre_build_review(work) -> None:
    reviews = work / "reviews"
    write(reviews, "110-a-spec-2026-10-21.md", "review")
    plain = write(work, "110-a.md", SPEC.format(status="**built 2026-10-21**", notes=""))
    drafted = write(work, "111-b.md", STRUCTURAL.format(status="drafted 2026-10-21", notes=""))
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
    assert scan.structural_spec_review_errors(plain, reviews) == []  # not structural
    assert scan.structural_spec_review_errors(drafted, reviews) == []  # not yet built
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

### E. The roadmap and the CHANGELOG

**E1. `context/roadmap.md`**, a "Reserved" paragraph in "Where 0.1.0 stands", after the
paragraph "Reserved: 101 (a faster release run …)":

```
Reserved: 107 (a structural review is a stage; the last of the chain 102 to 107 that
`research/2026-10-20-a-design-review-of-the-runner.md`, section 8, sets out; the owner,
2026-10-20): the rule "Structure is reviewed, not only behaviour" in AGENTS.md, the eight-row
rubric, its measurements and a template in `reviews/README.md`, one line in the reviewer's
checklist, two rules checks (a released version has its structural review; a built structural
specification cites its pre-build review), and question 108 for the owner's amendment of §5.6.
Parallel-safe, context and judge only; before 0.1.0, since 0.1.0 is the first release the rule
gates.
```

**E2. `context/roadmap.md`**, the "Release rule" paragraph: the text "Before 0.1.0: a security
review of the whole surface (milestone 6)," becomes "Before 0.1.0: a security review of the
whole surface (milestone 6), a structural review of `src/` against the design review's rubric
(spec 107; `reviews/0.1.0-structural-review-<date>.md`, written on the dry run's commit by a
fresh agent),".

**E3. `CHANGELOG.md`**, under `## 0.1.0a8 — unreleased`, a bullet:

```
- **A structural review is a stage** (spec 107; the design review of 2026-10-20). A change that
  adds a module-level mutable or lock, a use of wasmtime-py's private API, a platform branch or a
  test seam outside the one place specs 102 to 106 give each, or takes a module past the size
  ceiling, is reviewed before it is built; and every release gets a structural review of `src/`
  against the design review's eight-row rubric, beside its security review, which the judge
  requires of a released version. Nothing in the artifact set or the wheel changes.
```

## Scope

In: Decisions 1 to 7; the texts of Design A to E, pasted as written.

Out:

- **Amending the constitution.** Question 108 asks; the lane commits the owner's answer
  (Decision 2).
- **The structural review of 0.1.0 itself.** It is written by a fresh agent at the release, on
  the dry run's commit, not by this specification's builder (Decision 4).
- **A rules check that the security review was written.** None exists; adding one changes what
  the judge requires of a stage the constitution already names, which is the owner's reason to
  give, not this specification's (Decision 8).
- **The structural fixes and their checks** (specs 102 to 106), including the size ceiling's
  number, the function-length ceiling the memo suggests, and the module names, which are theirs
  (Decision 1).
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
   whose version is a prerelease (`0.1.0a8` at drafting).
3. **Check (b) exists and was seen failing first**, on a fixture specification (the unit row's
   `112-c.md` case) and on the tree: `uv run pytest
   tests/checks/test_rules.py::test_built_structural_specifications_cite_their_pre_build_review
   -q` passes, since no Kind line says "structural" (or, if 102 to 106 added the word at the
   wave, since each cites its `-spec-` review).
4. **The unit rows pass, each seen failing first:** on the base (106's tip) both rows fail with
   `AttributeError` (no `structural_review_errors`), recorded in the landing notes; on the build
   every case of D3 passes. `ruff check` and `ruff format --check` are clean on `src/` and
   `tests/`.
5. **No verdict moves.** The fast tier in the worktree on the frozen `v0.1.0a7` set (the memo,
   section 8), `-n 3` when another judge runs: green; `uv run python tests/harness/sameness.py
   <the baseline record> build/progress/latest.json` lists exactly the two new rows of D2 and the
   unit suite's count, and nothing else; the output is in `build/107/sameness.txt`.
6. **The open-question scan is green with the new texts:** `uv run pytest
   tests/checks/test_rules.py::test_specifications_have_no_open_question
   tests/checks/test_rules.py::test_specifications_have_their_header_and_sections -q` passes
   (it reads AGENTS.md and every specification, this one included).
7. **Nothing under `src/` changed:** `git diff --stat <base>..HEAD -- src tests/public_api.txt`
   is empty; no artifact is rebuilt; `uv run python tests/harness/api.py` reports no change.
8. **The release workflow:** no dispatch of its own. The chain's one dispatch on its final tip
   (the owner, 2026-10-20) is this specification's run, since this is the tip; its id goes in the
   landing notes, every red line a growth line claimed by 102 to 106 or none.

Eight criteria. Criteria 2 to 4 are the "check before the code" of AGENTS.md rule 3; criterion 5
is the chain's rule.

## For the lane

- **Kind:** parallel-safe, context and judge only; the last entry of the chain's wave (the owner,
  2026-10-20: all six land as one wave, past §5.7's five). It rebases onto 106's tip in the
  lane's order; no other entry in the wave should touch `AGENTS.md` rule 8, `reviews/README.md`
  or the questions file, so no conflict is expected; `roadmap.md` and `CHANGELOG.md` merge
  textually with 102 to 106's lines, each named if it conflicts.
- **The claim list** (each line starts "107:"):
  - 107: **new checks (2 nodes), each passing, no fuel, no bytes:**
    `tests/checks/test_rules.py::test_a_release_has_its_structural_review` and
    `tests/checks/test_rules.py::test_built_structural_specifications_cite_their_pre_build_review`.
  - 107: **unit rows:** `tests/unit/test_scan.py` gains two rows (the suite's count rises by
    two).
  - 107: **retired checks:** none. **Lost passes:** none. **Grown rows:** none.
  - 107: **the judge hash changes** in `tests/harness/scan.py`, `tests/checks/test_rules.py` and
    `tests/unit/test_scan.py`.
- **The flags** (paste-safe):

  ```
  --accept "107: a structural review is a stage: the rule in AGENTS.md, the rubric and template in reviews/README.md, the reviewer's checklist line 4a, and question 108 for the owner's amendment of §5.6"
  --accept-judge "107: two rules checks: a released version (X.Y.Z, no suffix) has context/reviews/<version>-structural-review-<date>.md scoring R1 to R8, and a built or landed specification whose Kind line says structural cites its own existing -spec- review; two unit rows in test_scan.py; no existing expectation edited"
  ```

- **Dry-run needs:** none beyond the chain's one dispatch on this tip (criterion 8). The two
  checks run in every judge shard that runs `test_rules.py`, Windows included; they read files
  only.
- **At the release of 0.1.0:** the lane's order of operations is Decision 4's; the first
  `0.1.0-structural-review-<date>.md` is written then, by a fresh agent, in the README's
  template.

## One line

A change that would turn the runner back into one file is reviewed before it is code, and every
release is scored against the memo's eight rows by someone who did not write it, with the judge
refusing a release that skipped it.

## Landing notes

Filled in when it lands.
