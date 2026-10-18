# /context/progress

The accepted state of the progress harness
(`../specifications/002-the-progress-harness.md`). Two files, written
only by `uv run pytest --accept "<reason>"`, never by hand.

- `accepted.json`: for each v1 check, its last accepted status, the
  commit and artifact it was seen on, and its metrics (fuel, bytes)
  per platform, plus the hash of every judging file.
- `history.jsonl`: one line per acceptance, append-only. Each line
  carries the hash of the line before it and of the `accepted.json`
  it wrote, so `test_progress_history_is_intact` notices a hand edit
  or a rewritten line.

## How to read a run

`uv run pytest` ends with the scoreboard:

```
wasi_python v1: 14/67 pass · 8 gap · 45 blocked · 0 fail   (unit suite 115/115)
  v1.1  artifact set         0/15  blocked 15
  …
blocked by: artifact dir 37 · runner 3 · …
gaps close with: 2026-10-16-reproducible-builds-on-linux 5 · …
next: context/specifications/001-the-neutral-host-door-and-the-runner.md (unblocks 40, closes 1)
ratchet vs 2828f2cced: lost 0 · absent 0 · unrun 0 · gained 0 · grew 0
```

- **pass**: the check ran and held.
- **gap**: it fails exactly as `tests/known_gaps.toml` says, and that
  entry names the document that will fix it.
- **blocked**: a named prerequisite is missing (an artifact, the
  runner, a source tree). The `next:` line names the document that
  provides the most of them.
- **fail**: anything else. The run is red.

The ratchet compares the run with `accepted.json`. A pass that is
lost, a check that disappears, or fuel or bytes that grow turns the
run red. A pass that becomes blocked is red too, unless the run says
`--partial "<why>"` (for example, a machine without artifacts).

## Flags

| flag | what it does |
|---|---|
| `--accept "<reason>"` | record this run; refused unless green with no loss |
| `--accept-judge "<reason>"` | also accept a change to the judging files |
| `--accept-growth "<reason>"` | also accept fuel or bytes growth |
| `--partial "<reason>"` | allow accepted passes to be blocked here |
| `--retire <node id>` | with `--accept`: drop a check from the protected set |
| `-m "not slow"` | the fast tier: skip the golden jobs and the oracle |

The full record of the last run is `build/progress/latest.json`.

## The landing lane (spec 029)

Only the lane accepts: in the main tree, on a clean tree, and on a detached HEAD, so main
moves only by fast-forward onto an acceptance already checked. The judge enforces three of
these things:
- `--accept` is refused before collection in a linked worktree whose run would write a
  `context/progress` folder.
- It is refused on a tree with a change the judge could see: any tracked change outside
  `context/progress/`, or an untracked file under `src/`, `tests/`, `scripts/`, `recipes/`,
  `context/specifications/`, `context/reviews/` or `context/upstream/`, or a judging file.
- It is refused again when the acceptance is written, if the tree changed or HEAD moved during
  the run.

The steps, in order:

1. **Wait for a quiet tree.** Nothing else may be uncommitted in the main tree. Other agents'
   tracked edits block every acceptance, and they are never stashed (constitution §4.14). The
   lane waits for them to be committed, or for the work to move to a worktree.
2. **Detach.** Run `git switch --detach <the rebased, reviewed commit>`. It changes no working
   file that step 1 left. For a change built in the main tree, commit the change, its
   specification and its review here first, on the detached HEAD.
3. **Accept.** Run `uv run pytest --accept "<reason>"`, with `--accept-judge` when the judge
   changed.
4. **Commit the acceptance alone, at once.** Run `git commit -m "Accept …" --
   context/progress/accepted.json context/progress/history.jsonl`. The pathspec leaves out
   anything else that is staged.
5. **Check it.** Run `uv run pytest tests/checks/test_rules.py`.
   `test_the_newest_acceptance_sits_on_the_commit_it_judged` reads this commit. Its first
   parent must be the commit its newest line judged, it must carry nothing else, and its line
   must say `dirty: false`. If that check fails, run `git reset --soft HEAD^` (a narrowed run
   can exit 1 only because other checks did not run; read the check's own line). HEAD is still
   detached and nothing has been pushed, so main has not moved. Then redo step 4.
6. **Move main.** Run `git switch main && git merge --ff-only <the acceptance commit>`.

A red acceptance commit cannot be repaired by accepting again. A red rule makes the run red,
and `--accept` refuses a red run. That is why step 5 runs before main moves. What the lane does
if a red acceptance reaches main anyway is the owner's question (question 70); until it is
answered, step 5 must not be skipped, and a red acceptance found on main stops the lane: write it
down under question 70 and change nothing.

The worktree check needs git 2.31 or later (`--path-format=absolute`). Older git fails closed:
it takes the main tree for a linked worktree, and `--accept` is refused.
