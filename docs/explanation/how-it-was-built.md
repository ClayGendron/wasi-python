# How it was built

wasi-python 0.1.0 was written by AI agents. One person, the maintainer, set the direction and made the decisions. Claude Opus agents did the work, and Fable agents were consulted as advisors at the turning points. This page tells how that went, with the numbers taken from the agents' own session records, the git history and the CI runs.

In short, it took six days, 13.2 billion tokens and 421 agent sessions. The maintainer was out of contact for two thirds of the week.

## The numbers

The week ran from 12:53 on Friday 16 October 2026 to 14:31 on Thursday 22 October (US Eastern time). That is 146 hours, or six days and two hours.

| Measure | Value |
|---|---:|
| Tokens, all kinds | 13.2 billion |
| Tokens, not counting cache reads | 0.54 billion |
| Tokens the models wrote (output) | 9.1 million |
| API calls | 51,610 |
| Agent sessions | 7 lead sessions and 414 subagents |
| Most agents working in one minute | 12 |
| Commits | 1,255 |
| Specifications written | 111, of which 95 landed |
| Reviews by a fresh agent | 251 |
| Release workflow runs on CI | 173 |
| Alpha releases | 7 tagged, 6 published |
| Messages from the maintainer | 199, about 4,000 words in all |

Almost all of the tokens are cache reads. An agent re-reads its whole conversation on every turn, and the cache makes that cheap. So the 13.2 billion measures how much context the agents carried. It does not measure how much they wrote. The models wrote 9.1 million tokens.

Claude Opus made 99.4% of the calls. Fable made 262 calls in ten sessions, nearly all of them advisory. It weighed the project's direction, the test budget and the plan for these documents, and it proposed the faster way of working described below. A cost estimate at list prices, from the ccusage tool, is about $5,400. The maintainer paid a flat subscription, not that sum.

## Tokens per hour

![Bar charts of tokens per hour across the week. All tokens peak at 337 million in one hour on the evening of 18 October. Output tokens peak at 260 thousand in the first hour.](../assets/how-it-was-built-tokens.svg)

The agents spent tokens in 139 of the week's hours, about 95 million an hour. The busiest hour was 22:00 on Sunday 18 October, with 337 million tokens. That evening twelve agents were working at once. The hour that wrote the most was the very first, when one agent wrote the project's rules and its first plans.

The night hours were the busiest. Over the week, 22:00 to 23:00 used more than three times the tokens of 18:00 to 19:00. That is when the maintainer was asleep and had told the agents not to stop.

## Where the time went

Every session's record was split into what it was doing at each moment. A gap that ended in a model's reply was the model generating. A gap that ended in a command's result was that command, sorted by what it ran. Builds ran the build script or a container. The judge and test runs ran pytest or a package's own tests. Waiting on CI was watching a GitHub Actions run. Anything else was another tool call, such as reading or editing a file. Then each minute of the week went to the activity that took the most agent time in it. A minute with no agent at work was idle, unless a CI run was in progress, which counts as waiting on CI.

![A grid of seven days by twenty-four hours, each cell coloured by its main activity. Almost every hour is coloured. The model generating dominates the first three days. Judge runs and waiting on CI dominate the last three.](../assets/how-it-was-built-timeline.svg)

![Stacked bars of hours per activity for each day and for the whole week. The model generating is about a third of the week, judge and test runs about a quarter, waiting on CI about a seventh, and idle under a twentieth.](../assets/how-it-was-built-hours.svg)

| Activity | Hours | Share of the week |
|---|---:|---:|
| The model generating | 50.2 | 34% |
| The judge and test runs | 37.2 | 26% |
| Other tool calls | 22.1 | 15% |
| Waiting on CI | 20.7 | 14% |
| Building | 4.8 | 3% |
| Waiting on the maintainer's answer | 3.9 | 3% |
| Idle | 6.7 | 5% |

The week has two halves. In the first three days the models were writing. In the last three the machines were checking what they wrote. On Wednesday the judge and test runs took more hours than anything else, because by then every package ran its own test suite.

"Near 24/7" holds. In 144 of the week's 147 clock hours an agent was working or a CI run was going. The one long pause came on Tuesday afternoon. The maintainer's token allowance was nearly spent, so the agents found a stopping place and wrote a handoff. Nothing ran for almost five hours. Outside that pause the project sat idle for under two hours in six days.

Counted per agent, the hours add up to 478, more than three times the clock. On average 2.4 agents were working in any minute.

## The story of the week

**Before the week.** A one-day experiment in another project showed that CPython could be built for WebAssembly with numpy and pandas compiled in. This repository started from it.

**Friday. The rules before the code.** The maintainer's first message asked the agent to work "fully autonomously". It asked it to learn first from the large autonomous ports of 2026, such as Bun's move from Zig to Rust, and to build a strong test harness. The agent studied how those projects were run and took three lessons. A judge decides what passes. A ratchet makes sure nothing that passed stops passing quietly. The agent that writes a change never reviews it. The project's constitution and rules came first, then the pinned build that rebuilds to the same bytes. The first alpha shipped that evening with numpy and pandas. At midnight the maintainer went to sleep and asked the agents not to stop.

**Saturday. The product takes shape.** The second alpha moved to CPython 3.15. The maintainer went through every open question with the agents, one at a time. Out of that came the rule that nothing is writable unless the embedder grants it, the tool protocol, sessions, and the first release on PyPI. The maintainer named the purpose, a safe runtime for agent code. The agents also worked out how to build several changes at once in separate worktrees and land them one at a time. Thirty-eight plans were written that day.

**Sunday. The busiest day.** There were 348 commits and 3.5 billion tokens. One alpha failed on Windows and was never published, and the next one fixed it. The maintainer asked why the release was compiled under emulation for an hour. A Fable agent studied how other projects get byte-identical builds, and the fix was adopted the same hour. matplotlib landed and lxml followed.

**Monday. Faster.** The maintainer asked for scipy and the other packages to come first and raised the number of parallel builds to six. One scipy file compiled to different bytes on every run. After two failed attempts the agents wrote the problem down and offered options. The maintainer chose a narrow exception while the toolchain moved to a fixed compiler. That evening the maintainer wrote "I can't express enough how I want this process to move faster". The answer was waves. Up to five reviewed changes now landed together, full test runs moved to CI, and a dry run on three systems was the final check. "No more alphas" came the same night.

**Tuesday. The packages.** scipy, a second matplotlib milestone and scikit-learn landed. The maintainer chose to run every upstream test of every package the project builds, against the advisor's suggestion. In the afternoon the token allowance ran low and work paused until 22:00.

**Wednesday. Fast tests and slow tests.** statsmodels landed, and numpy's linear algebra moved to OpenBLAS. The maintainer settled when tests run. The fast checks run on every change, and the full package suites run before a release. When freetype's download server went down, the maintainer asked the agents to stop polling it, so as not to add to its load. That night the maintainer asked whether the process matched other projects. It felt limited by "code running to test our code". The agents studied seven projects, Fable weighed the options, and the maintainer chose a shorter path to 0.1.0 before going to sleep.

**Thursday. The release candidate and these documents.** The last package tests and the version bump to 0.1.0 landed at 03:40. The full release check ran through the night, and the dry run on main was green by the morning. The maintainer asked for a short README and this documentation site, "within a day". The maintainer also published the security advisory the agents had drafted (GHSA-w99p-2jv3-fvj6). The early alphas had run on a wasmtime release with a sandbox escape on macOS, which the runner had fixed since. The maintainer yanked the affected alpha from PyPI.

## What the maintainer did

The maintainer sent 199 messages in the week. Most were short. "Status?" was a common one. The agents also asked 80 rounds of questions through a question tool, each with options and a recommendation, and the maintainer answered each. Those answers set the product's purpose, the packages in 0.1.0, the release plan and how fast the process ran. More than once the maintainer chose against the recommendation.

Some things only the maintainer could do. The maintainer made the repository public and set up the PyPI project. The maintainer published the advisory, turned on this site and freed disk space. Tagging 0.1.0 is the maintainer's alone.

The agents did the rest. They wrote every line of code, every plan, every review and every test. They made the commits, dispatched and read the CI runs, and published the alphas with the maintainer's leave.

"Largely unsupervised" holds too. There were 19 stretches of two hours or more with no message from the maintainer, 96 hours of the 146. Six of them were nights of seven to eleven hours. The agents spent two thirds of all tokens in those stretches.

## What these numbers leave out

The activities are sorted by the text of each command, so they are approximate. A command that builds and then tests counts as a build. Model time includes the API's queueing. The count of agents at work is not the machine's load, and CI's runners worked beside the agents for another 100 hours that the table above does not add. Token counts are not a bill.

In one line, six days, 13.2 billion tokens (almost all of them re-read context), 421 agent sessions, and one maintainer who decided while the agents built and checked.
