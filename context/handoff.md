# The lane's handoff

Where the work stands between sessions, written by the lane when a session ends and replaced by
the next one. It points at the records that matter: the roadmap for the order,
`decisions.md` for the owner's answers, each specification's landing notes for its state. The
lane never tags; the 0.1.0 tag is the owner's.

## 2026-10-20, end of day (main `4161ef9`)

### Landed today

- **Wave 07** (038, 044) at main `1cd25e2`, history line 88; dry run 39442080658 green on all
  three systems.
- **Wave 08** (042, 066, 099) at main `faa9c93`, history line 89: 763/850 pass, 0 fail, on the set
  `SHA256SUMS` `b5a66245`. The first attempt in the main tree was void (spec 089): macOS host
  litter from an open Storage pane and Finder windows while the owner was away. The lane accepted
  from a clone of the wave outside the home folder, rebuilt from the same pins to the same bytes;
  all 358 metrics measured in both checkouts were equal. Records in the main tree's
  `build/wave-08/` (git-ignored): the flags, every attempt's log and record, the sameness output.
  **Its dry run 39488145764 on `faa9c93` was still running at the end of the day: read it back
  first** (`gh run view 39488145764 --json jobs`; every red line a growth line or G7), then
  `uv run python tests/harness/sameness.py <its release-record-1/record.json>
  build/wave-08/latest-accepted.json`.

### The owner's standing rules added today (all in `decisions.md`)

- **CI:** a reviewer reads the builder's run when it is on the exact commit reviewed; a builder
  that only rebased onto a wave's tip (hunks named, fast tier green) dispatches no run.
- **Disk:** the lane may delete a landed spec's worktree `build/` (regenerable output only) and
  logs each deletion; anything else is asked first.
- **Two tiers of tests (spec 102):** upstream's opt-in slow tests, and tests the project chooses
  as slow, run only on the publishing run and the dry run on main before a tag; the lane runs them
  locally only before a tag. Nothing is ever left out of the full suite.
- **Host litter:** never close or kill the owner's apps; when they are open and the owner is away,
  accept from a clone outside the home folder (rebuild there; a moved build tree fails two v1.5
  checks on absolute paths). Spec 097 removes the need.

### In flight (every branch pushed; no agent running)

| Spec | Branch tip | State | Next |
|---|---|---|---|
| 100, numpy on OpenBLAS | `b2d9e7a` | build reviewed (lands); restacked onto main; 099's L1 carried | rebuild from empty (native slot), re-measure on main's set, flags, CI, Disposition |
| 101, the faster release run | `6992fc0` | built and rebased onto main; source run 46.0 min (wave 07: 59.7), reuse runs about 22.5 to 35 | read run 39488829008 (on `6992fc0`), update its notes, build review (reads that run); criterion 3, the traced build, needs a container slot, after the build review if the reviewer agrees in writing |
| 097, host litter outside the home folder | `5d5204d` | pre-build reviewed; half-built: checks seen failing, fix in, fuel equal across locations on four legs | rebase onto main, a new CI run, criterion 4 from its assets, fast tier against a copy of main's set, criterion 7, self-check, build review |
| 045, statsmodels | `27205a5` | pre-build confirmed; rebased onto main (22 hunks named); built natively, set `f2a3e87d`, not yet judged | fast tier and node ids, README, CI, flags, build review; `python.wasm` grew 6.87 MB, past the spec's own bound of 2.5 to 5.5 MB, cause not measured: the build review must explain it |
| 102, the release tier | `9460d14` | drafted and revised for the owner's four answers | pre-build review |
| 067, the pure-Python packages' own tests | `0eb887d` | pre-build reviewed; revised (42 packages, 39 pins; normal tier about 25 to 35 T, inferred) | survey on main's set after wave 09 and 045, a confirmation round, the measured price to the owner |

### The order to 0.1.0

1. Wave 09: 100, 101, 097.
2. Then 045, 102, 095 (scipy's, scikit-learn's and statsmodels' own tests) and 067.
3. Then the version bump to 0.1.0 (`release/version.py`), a green dry run on main's exact commit,
   and the owner's tag.

### Loose ends

- The `build/` folders of the landed 042 and 099 worktrees were only partly removed (the removal
  hit folders being written to); finish them under the disk rule.
- Probe folders left by 097's builder and reviewer: `~/Git/Repos/wasi_python-097-review-probe`
  (under the owner's home folder: ask before removing), and two under the per-user temp folder
  (`judge-097-review-probe`, `wasi-python-097-probe`).
- Disk was about 40 GiB free at the end of the day; a Time Machine local snapshot from 12:46
  holds purgeable blocks. Check `df -h ~` before any rebuild or accept.
- The local `main` ref in the main tree is stale; the main tree's checkout is on `wave/08`, equal
  to `origin/main`. Work from `origin/main`.
