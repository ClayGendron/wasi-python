# The scripts behind "How 0.1.0 was built"

These scripts made every EXECUTED number in `../2026-10-22-how-0-1-0-was-built.md` and the three charts under `docs/assets/how-it-was-built-*.svg`. They read the Claude Code transcripts of this project, `git` and GitHub Actions, and write JSON to a scratch folder. Nothing they write belongs in git: the transcripts hold private prompts, and the JSON is about 40 MB.

Run them from a scratch folder, in this order, with `S` the session to leave out (the session that wrote this memo, `80c19a46-a4d5-4add-abd0-70edbba819ce`, whose work began after the week ended):

| Step | Script | Command | What it makes |
|---|---|---|---|
| 1 | `extract.py` | `uv run --no-project python -I extract.py ~/.claude/projects/-Users-claygendron-Git-Repos-wasi-python data.json` | Streams all 434 non-empty transcripts line by line, six at a time, and keeps usage per API message, each session's events and every tool call. About 3 s for 4.2 GB, since it skips the request records by their first bytes. |
| 2 | `tokens.py` | `uv run --no-project python -I tokens.py data.json tokens.json $S` | Tokens deduplicated by message id and request id (the largest count seen for each field), by model, day, hour, hour of day, and lead against subagent. |
| 3 | `timeline.py` | `uv run --no-project python -I timeline.py data.json timeline.json $S` | Every second of every session given a class by the rules in its docstring, rolled up per minute. Also the longest tool calls. |
| 4 | `gh run list` | `gh run list --limit 1000 --json databaseId,createdAt,updatedAt,startedAt,conclusion,status,headBranch,event,workflowName,displayTitle > gh_all.json` (from the repository) | Every GitHub Actions run, read-only. |
| 5 | `rollup.py` | `uv run --no-project python -I rollup.py data.json timeline.json rollup.json gh_all.json $S` | Wall-clock hours by the class that took most agent time in each minute, per day and for the week; a minute with no agent at work but a release run in progress counts as waiting on CI. Idle stretches and parallel sessions. |
| 6 | `work.py` | `uv run --no-project python -I work.py <repo> gh_all.json work.json` | Commits, specifications drafted and landed, reviews, memos and accepted judge records per day; release runs by outcome and length. |
| 7 | `owner.py` | `uv run --no-project python -I owner.py data.json owner.json $S` | The owner's own messages, deduplicated (a queued message is recorded twice), without the lane's self-scheduled heartbeats; AskUserQuestion calls per day. |
| 8 | `charts.py` | `uv run --no-project python -I charts.py rollup.json tokens.json <repo>/docs/assets` | The three SVG charts. |

The cross-check is `bunx ccusage session --json --since 20261015` (ccusage 16.1.1 reads the same transcripts); the memo compares its totals with step 2's.

The classification in `timeline.py` is a set of regular expressions over each Bash or Monitor command. Change one and steps 3, 5 and 8 move; the memo states the rules and their known faults.
