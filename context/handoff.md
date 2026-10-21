# The lane's handoff

Where the work stands between sessions, written by the lane when a session ends and replaced by
the next one. It points at the records that matter: the roadmap for the order,
`decisions.md` for the owner's answers, each specification's landing notes for its state. The
lane never tags; the 0.1.0 tag is the owner's.

## 2026-10-21, evening (main `1875d4cd`; wave 11 accepted on `wave/11`, not yet on main)

### Paused at the owner's word

The owner paused new work at the end of the day: current work finished, nothing new started.
New CI runs were also held for an hour or two after GNU Savannah (freetype's pinned host) was
down from about 20:10 to 20:25 UTC: never probe or poll an upstream host; on an outage, hold
runs that fetch from it and tell the owner.

### Wave 11: accepted, dry run green, main not yet fast-forwarded

- **Entries:** 101 (the faster release run), 102 (the release tier), 112 (strings speak for
  themselves), 114 (HOME is never the root; the security review's H2), 113 (every module cache
  is guarded; its H1). Branch `wave/11`, pushed.
- **Acceptance** `da665abe`, history line 93: 810/935 pass, 0 fail, on the set rebuilt in the
  main tree, `SHA256SUMS` `1556bbd5` (python.wasm byte for byte main's). Sameness against wave 10's
  record: exit 0 with the combined claims (`build/wave-11/lane/claims.toml`, git-ignored; the
  integration review's Appendix A is its source).
- **Integration review** `context/reviews/wave-11-integration-2026-10-21.md`: lands. Landing
  edits `25983899` (102's constitution and AGENTS.md text, the release-tier ledger, 101's roadmap
  lines, 112's CHANGELOG line).
- **Dry run** 39667712127 on `wave/11` at `da665abe`: attempt 1 failed only at the downloads
  (Savannah's outage); attempt 2 (failed jobs re-run, nothing changed) green on three systems;
  the gather concluded success (102's criteria 5 and 7), set `1556bbd5` on every host, 805/935 on
  CI, the wheel 98,264,488 bytes.
- **Next, in order:** (1) fast-forward main to `wave/11` and push. The push starts
  `set-cache.yml` for the first time, which builds and so fetches from Savannah: do it once the
  owner lifts the hold. (2) Record that run (101's criterion 7) and the next cache hit. (3) The
  landing notes: each entry's Status, 112's roadmap line, the review addendum, as wave 10's
  `1875d4cd` did.

### Wave 12: building, paused

| Spec | Tip | State | Next |
|---|---|---|---|
| 067, the pure-Python packages' own tests | `79d865b1` (on 102's `861d5e4b`) | spec confirmed; built in part: 39 pins, four test-source patches, 42 families (285 groups), classes for all but sympy; release about 56 T measured (lower bound) | its landing notes list ten steps: sympy's 54 groups, splits of its capped groups, classes, smoke twice, shards, fast tier, claim block, one normal-tier branch run. Note: its builder ran two guests at once once (named in its notes); its unit checks were written beside the code, not seen failing first (the self-check must say so) |
| 095, scipy's, scikit-learn's and statsmodels' own tests | `8694fc4c` (on `861d5e4b`) | spec confirmed; harness keys and units built (seen failing first), files written; release about 60.5 T over 133 groups, 48 unmeasured | its landing notes list seven steps; tools under `context/research/2026-10-21-scipy-sklearn-statsmodels-own-tests-under-the-runtime/the-build/` |

The release tier will be large: about 117 T measured so far between the two, more to come. The
lane's release acceptance before the tag runs it whole.

### The release reviews (0.1.0)

- **Structural** `context/reviews/0.1.0-structural-review-2026-10-21.md` (branch
  `worktree-agent-a97a92fcefa153822`, `ed8a2983`): no High; M1 is reserved as 115, M2 as 116.
- **Security** `context/reviews/0.1.0-security-review-2026-10-21.md` (branch
  `worktree-agent-a1f1b668360a6db50`, `d1db05e2`): H1 and H2, now closed by 113 and 114 in wave 11.
- Both are committed with the version bump. Before it, each reviewer reads the delta in `src/`,
  `release/`, `scripts/`, `recipes/` and the workflows since `b2d4ccd0` (waves 11 and 12).

### The order to 0.1.0

1. Wave 11 onto main (above).
2. Wave 12: 067 and 095 finished, built, reviewed, landed.
3. The two delta reads, the version bump (`release/version.py`), the release acceptance with the
   release tier, a green dry run on main's exact commit, and the owner's tag.

### The owner's answers today (all in `decisions.md`)

- A branch run may set `release-tier` only for a spec that changes the release-tier job itself;
  adding release shards for a package's groups is not such a change (102).
- Never probe upstream hosts; hold runs during an outage.
- A flaky unit test seen once, unchanged as asked: `tests/unit/test_async_tools.py::test_close_ends_the_calls_loop` (a ResourceWarning from a sqlite3 connection another test left on the same worker).
