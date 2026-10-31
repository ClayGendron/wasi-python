# Review of pull request #84 — merged work's worktree and branch are cleared

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude), a fresh sub-agent of Claude Code session 0672b924-ca3c-4b6c-91ca-f834537cb1bc; not the author
- **Reviewed:** `origin/dev...95587e3a` (one commit, `AGENTS.md` alone), and this review's commit, which adds the news file of Low 1
- **Run:** 41250521031 (`plan` green, `review` red for want of a news file and a review file, `quick` running when read)
- **Re-ran:** `uv run pytest tests/lint -q` → 14 passed, exit 0; `uv run pytest tests/checks/test_rules.py::test_the_news_files_have_their_shape` → 1 passed, with the news file added; in a scratch repository, `git worktree remove`, `git branch -D` and their refusals (below); `git ls-remote origin refs/pull/52/head` → the head of #52, whose branch GitHub deleted; `gh api repos/ClayGendron/wasi-python --jq .delete_branch_on_merge` → `true`

Box: 25 minutes, an agents' file and no code.

## Acceptance criteria against evidence

1. The owner's request, "clean up worktrees and branches after work is merged" — met: READ. Step 9 says merged work is cleared once a green post-merge run covers it, and the new bullet says who does it, when, and with which commands.
2. No uncommitted work is lost — met: EXECUTED. `git worktree remove` refused a worktree holding an untracked file ("contains modified or untracked files, use --force"), and the rule forbids `--force` and stops on a non-empty `git status --porcelain`. Ignored files are another matter (Low 2).
3. No unmerged work is lost — met: READ and EXECUTED. The local tip must equal the merged pull request's `headRefOid`, so a commit made after the merge stops the cleanup. `refs/pull/<N>/head` outlives the branch: #52's is still served while its branch is gone, and `git fetch origin pull/<N>/head:<branch>` is a valid refspec that rebuilds the branch from it.
4. Squash merges — met: INFERRED from git's rules. A squash commit does not contain the branch's commits, so `git branch -d` refuses and `-D` is right; the tip check is what makes `-D` safe. `git branch -D` is refused while the branch is checked out in a worktree (EXECUTED), so the order the text gives, worktree first and then branch, is the only order that works.
5. No conflict with "never `git checkout`, `git restore` or `git stash` a file that carries uncommitted work" — met: READ. The rule uses none of the three and stops at the first uncommitted file. It also agrees with constitution §4.14, "no other long-lived branch or worktree unless asked".
6. Remote branches — met: EXECUTED. `delete_branch_on_merge` is `true`, and `git fetch --prune origin` drops the remote-tracking ref.
7. Step 9's wording — met: READ. One sentence, placed after the red-run sentence, with "(below)" pointing to the bullet.
8. "Explaining things" — met, with small wording Lows (4, 5). The bullet is long (about 210 words) but each sentence carries one idea, and the reason for the wait is stated.
9. The news file and the review gate — not met as opened, fixed in this commit (Low 1).

## Findings, most severe first

1. **No news file, so `ci-status` and `review` refuse the pull request** (`context/changes/`) — `AGENTS.md` is an agents' file, not documentation, since specification 148's Decision 1 (`release/ci_plan.py`, `classify` and `agents_only`): an agents-only change runs `quick` alone but carries a news file and a review named after it. The self-check ticks the news box as "documentation only". Failure: run 41250521031's `review` job is red, and `ci-status` would refuse with "a pull request that is not documentation only carries its news file". Fixed in this review's commit as a Low that touches only `context/`: `context/changes/084-merged-work-is-cleared.md`, numbered after the pull request as `context/changes/README.md` allows when a pull request carries no specification (specification 084 is unrelated; the release's bump deletes the file), with one `For contributors` line and an empty claim. This review is named after it. The author may correct the description's news box: an agents' file is not documentation.
2. **`git worktree remove` deletes a worktree's ignored files without asking** (`AGENTS.md:48`) — EXECUTED: a worktree whose only extra file was under its ignored `build/` was removed silently. That covers its `build/`, `.venv/` and any `downloads/` (`downloads/*` is ignored). The bullet's last sentence says the sources under `downloads/` are deleted only by asking. Failure: a reader takes removal as safe for a worktree's own downloaded tarballs, or takes the sentence as forbidding removal. Nothing unrecoverable is lost (the pins fetch again), so Low. Fix text: "…and the sources under the main tree's `downloads/` are deleted only by asking. Removing a worktree also deletes its ignored files (its `build/`, `.venv/` and `downloads/`)."
3. **The two stops come after the commands they guard** (`AGENTS.md:48`) — a reader who runs the commands in the order written runs `git branch -D` before reading the tip check. Fix text: begin the stops' sentence with "Before either command,". Optionally, a local tip that is an ancestor of `headRefOid` (a reviewer pushed from another tree) holds nothing the merge lacked: `git fetch origin pull/<N>/head` then `git merge-base --is-ancestor <branch> FETCH_HEAD` says so. As written it is conservative, so this may be answered in writing.
4. **"deleted by hand"** (`AGENTS.md:48`, and the pull request's description) — the 217 branches (59 remote, 158 local) were deleted by a script. Fix text: "after a script deleted 217 stale branches".
5. **"drops its local copy"** (`AGENTS.md:48`) — `git fetch --prune` drops the remote-tracking ref `origin/<branch>`, not the local branch the previous sentence deleted; "local copy" reads as the latter. Fix text: "and `git fetch --prune origin` drops `origin/<branch>`."

Lows 2 to 5 are in `AGENTS.md`, which is not `context/`, so they are the author's. A fix to `AGENTS.md` after this review is a commit to an agents' file and makes the `review` check refuse this file, so it needs a second signing; an answer in writing does not.

A note outside this pull request: with its news file, an agents' change is no longer `agents_only` (`classify` gives the news file `news`, outside `{"docs", "agents"}`), so its run takes the own shards on Linux and Windows, not `quick` alone as specification 148's Decision 1 intends. The unit row `test_an_agents_change_runs_quick_alone_and_is_not_documentation` decides on the agents' path alone and does not see it. The cost is a larger run on this pull request, not a wrong verdict; it is a candidate for a later specification.

## Constitution checks

- §4 constraints: none touched. No source, pin, patch, artifact or judge file changes; §4.14's "no other long-lived branch or worktree unless asked" is served, and its "never `git checkout`, `git restore` or `git stash`" holds (criterion 5).
- §7 never-do list: nothing tripped. Deleting a merged branch is now the owner's standing instruction (2026-10-31), recorded in the bullet; pushing, tagging and making branches are untouched.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Low 1 — fixed by the reviewer in this commit.
2. Lows 2 to 5 — for the author: fixed in one commit and signed again, or answered in writing.

## Verdict

Lands: the rule does what the owner asked and cannot lose uncommitted or unmerged work, the news file it lacked is added here, and Lows 2 to 5 are wording the author may fix or answer.
