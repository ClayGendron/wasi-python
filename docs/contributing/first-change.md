# Your first change

This tutorial takes you from a fresh clone to a test run you can read. At the end you know what the scoreboard says, what a known gap is, and where a change starts.

The rule book for working in the repository is [AGENTS.md](https://github.com/ClayGendron/wasi_python/blob/main/AGENTS.md). It applies to people and coding agents alike. This page explains its first steps in plain words.

## Before you begin

- `git` and [uv](https://docs.astral.sh/uv/). The project uses uv only: run Python tools with `uv run`, and never a bare `python` or `pip`.
- For checks that run the guest, a built artifact set. See [Building from source](building.md).

## Clone and set up

```sh
git clone https://github.com/ClayGendron/wasi_python.git
cd wasi_python
uv sync
```

`uv sync` creates the environment from the lock file.

## Run the fast tests

The project's test suite is also its progress harness: it judges every check and prints a scoreboard. Start every session with the fast tier, which skips the slow guest jobs and the packages' own test suites:

```sh
uv run pytest -m "not slow"
```

The coverage badge on the README is this tier's measurement: the percent of the runner's statements (`src/wasi_python`) the fast tier runs under coverage.py. Every run of the release workflow measures it on Linux and sends the report to Codecov, which draws the badge. `uv run python tests/harness/coverage.py --measure` takes the same measurement on your machine and writes its reports under `build/coverage/`. The guest's packages are not in it. Their own test suites run inside the sandbox before a release.

## Read the scoreboard

Read the last lines of the run, the *scoreboard*. It has this shape; the angle brackets stand for the numbers and names your run prints:

```
wasi_python v1: <pass>/<checks> pass · <n> gap · <n> blocked · <n> fail   (unit suite <passed>/<total>)
  <area> <area name>  <pass>/<checks> gap <n> blocked <n>
  …
blocked by: <prerequisite> <n> · …
gaps close with: <document> <n> · …
next: <document> (unblocks <n>, closes <n>)
ratchet vs <commit>: lost 0 · absent 0 · unrun 0 · gained 0 · grew 0
not machine-checked: …
```

The first line counts every check. One line per area follows. Each check ends in one of four states:

- **pass**: the check ran and held.
- **gap**: the check fails exactly as a *known gap* says. A known gap is an entry in `tests/known_gaps.toml` that names the failure and the document that will fix it. A gap is an allowance, not a backlog: one more failure or one fewer is a different failure, and turns the run red.
- **blocked**: a named prerequisite is missing, such as the artifact set. The `blocked by:` line counts them. On a fresh clone with no artifacts, many checks are blocked.
- **fail**: anything else. The run is red.

The `next:` line names the piece of work that unblocks the most checks.

## The ratchet

The last line is the *ratchet*. The ratchet compares your run with the last accepted state of the project. A pass that is lost, a check that disappears, or fuel or bytes that grow turns the run red. New passes never pay for a lost one. So a change can add passes, but it cannot quietly lose one.

Fuel here is the guest's operation count. Tests count operations, never wall-clock time, so a result is the same on every machine. See [Fuel](../explanation/fuel.md).

## Where a change starts

A change starts with a check, before the code:

1. Write the check for the new behaviour, or a known gap that names what will close it.
2. Make the change.
3. Run the fast tier again, and run any slow check you changed alone by its node id.
4. Keep `ruff check`, `ruff format --check` and `pytest` green on `src/` and `tests/`.

Never weaken a check, a golden output or a known gap to turn a run green. Changing what the tests judge is its own change, with its own reason.

## Next steps

- Build the artifacts so the guest checks can run: [Building from source](building.md).
- Learn how a change is reviewed and lands: [Review and landing](review-and-landing.md).
- Read the rules behind all of this: [Principles](principles.md).
