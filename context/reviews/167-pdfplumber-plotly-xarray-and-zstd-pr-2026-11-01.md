# Review of 167 — pdfplumber, plotly, xarray and zstd (the plotly pull request, #92)

- **Date:** 2026-11-01
- **Reviewer:** an agent (Claude), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** `4d199003..7e35b683` (`git diff origin/dev...HEAD`, eight commits) with the specification, its pre-build review, the two decisions of #89 and #91 and the description; the replay by `git range-diff b13f1888..43005960 4d199003..648ea459`
- **Run:** 41326040694 on `7e35b683` (relayed): every judge shard green, ctrl-c's rows on three systems included; red only for this file's absence.
- **Windows:** all 13 windows-2025 legs of 41326040694 green (relayed).
- **Re-ran:** (darwin arm64, the worktree's set at the head, load average about 86) `tests/lint` → 14 passed; `tests/checks/test_rules.py` → 135 passed, 1 skipped; plotly's golden, guest rows, smoke group and tree, with `test_artifact_rules.py` → 48 passed; `--tier=release -k plotly-r` → 1 passed, 8 xfailed; the artifact-set file → 50 passed, 1 skipped.
- **Box:** 45 minutes; within it.

Labels: EXECUTED, I ran it; READ, I read it; relayed, the builder's number.

## Acceptance criteria against evidence

- **1. The licence sweep** — met as a sweep: `LICENSES/plotly.txt` carries LICENSE.txt, the colour and pypng blocks, plotly.min.js's head and seven `/*!` comments, the pinned cmocean and maplibre texts, Apache-2.0 and the datasets' sources (EXECUTED). The additions were not put to the owner (Low 1).
- **2. Growth and the wheel** — met (relayed: zip +7,084,514, wheel 112,145,034, plain start +0.21%, snapshot +2.11%). The zip has 8,389 members, 1,507 under `plotly/`, 20 under `_plotly_utils/`, two in the dist-info: 1,529 added (EXECUTED).
- **3. The wheel's check** — unchanged: `PYPI_FILE_LIMIT` is 268,435,456 from #91 (READ).
- **4. Exact additions, the tree** — met: no `labextension/` or `widgetbundle.js` member (EXECUTED); the tree is its tarball plus its patch (EXECUTED); the workflow's count is 41 (READ).
- **5, 6. The golden and `to_image`** — met: the guest matches the oracle's stock wheel, and `to_image` raises `RuntimeError` naming kaleido (EXECUTED).
- **7. Classes, suites, growth** — met: plotly-smoke and plotly-r with eight classes pass (EXECUTED); growth claimed (READ).
- **8. PyPI's limit** — met by #91's decision, as that decision says (READ).
- **9.** Met: lint EXECUTED; the run green (relayed).

**§4.1.** A recipe could only fork two plotly modules as stand-ins, and the pre-build review took Decision 4's patch. Its SHA-256 `9eb4c5a0…` is MANIFEST's `recipe` line (EXECUTED); the news file names its path; the draft is present. Patches and drafts number 33, as the README says (EXECUTED). The patched `data/__init__.py` uses `os` nowhere else (READ).

**The eight classes** are true, and none hides a pass. `test_offline.py:20-21` writes beside its own file, as openpyxl's and jinja2's classes do. `basevalidators.py:833,840` take `sys.maxsize`, which is 32-bit here. `convert_colors_to_same_type` assigns into the list it is given (`_plotly_utils/colors/__init__.py:454-480`), so `test_sample_colorscale` rewrites `Inferno` in place, with a reserved roadmap line. The `no-requests` test imports `requests.sessions`. `test_px/conftest.py` imports polars and pyarrow at its top (all READ).

**The claims.** Every verdict-bearing file changed is in `[claim.judge]`. No other staged suite's tests import plotly (EXECUTED, a grep), so no other pass count moves. **Replacing #77's block is right:** #77 was accepted at `27c70069`, four acceptances ago, so the next acceptance should read plotly's claims alone, as `context/changes/README.md` prescribes. The ledger keeps #77's block and adds plotly's.

**The rebase** drops exactly `2314296d`, the gate commit; the last commit loses its `decisions.md` entry and its wheel-line rewrite; `d3b0bea8` differs from `353f2ddd` only in the workflow's count and one line of `upstream.py` (EXECUTED, `git range-diff`). Neither `decisions.md` nor `tests/harness/artifacts.py` is touched; #91's decision stands.

**`.github/workflows/release.yml`:** three tree-check steps, in the source build and both rebuild jobs, require `41 passed` in place of 40. No token or selection changes.

**Structure:** nothing under `src/` changes; lint holds the writing rules (EXECUTED).

**`test_ctrl_c_stops_a_computing_guest`:** an unlikely cause: `python.wasm` is the same bytes and the guest imports no plotly. The run's ctrl-c rows are green.

## Findings, most severe first

1. **Low: the swept additions were not put to the owner** (the specification, "The owner's choices", 1: "the owner is asked with the swept list"). plotly.min.js bundles native-promise-only, buffer, safe-buffer, the assert module's comparisons, object-assign (MIT) and ieee754 (BSD-3-Clause). Neither the pre-build list nor §4.12's line of 2026-10-31 names them, and seven datasets state no source. All are licence kinds the owner has approved, inside a file the owner approved by name, and every notice ships. Merging into `dev` publishes nothing, so this does not hold the merge. Fix: before 0.1.3's release pull request, the orchestrator asks the owner with AskUserQuestion. The recommended option is "approve the six libraries inside plotly.min.js, and the seven datasets under plotly's MIT licence". The answer goes into `decisions.md` and §4.12's line of 2026-10-31.
2. **Low: 167's news file still says the wheel check refuses anything over 100 MiB** (`context/changes/167-pdfplumber-plotly-xarray-and-zstd.md`, "For contributors", third line). The rebase restored the line the dropped commit had rewritten. `091-the-wheel-may-reach-256-mib.md` says the check allows 256 MiB, so 0.1.3's notes would carry both lines and contradict each other. Fix text: delete the line "**The wheel's size is checked against PyPI's file limit.** … [Release process](…)" from 167's news file. 091's line already says what the check now does.
3. **Low: stale words in the specification.** The Status line still calls #77 "not landed" and does not say the plotly pull request is built. Fix text: "first pull request built 2026-10-31 and merged as #77 (pdfplumber with pdfminer.six, and xarray); plotly built 2026-11-01 as #92". The plotly "Pins" paragraph says "The tree count in `release.yml` rises to 33". Fix text: "rises to 41 (40 on `dev` at `4d199003`)". `648ea459`'s subject still names "the decision on the wheel past 100 MiB", which it no longer carries. The squash's title governs, so it needs no fix.
4. **Low: the self-check's Windows box is open, with its reason** (the run starts with the pull request). It is ticked once the run's Windows legs are read.

## Constitution checks

- §4.1 holds. §4.12: every swept notice ships; Low 1 asks for the additions. §4.15: no channel opens, no default loosens. §4.6: nothing large enters git. §5.6: pre-build reviewed; not structural. Pins: three files, each by URL and SHA-256.
- §7: nothing tripped; the trailers name Claude Opus 5.5.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. The owner: "Approve all", in `decisions.md` ("plotly's licence sweep") and §4.12 (READ).
2. Fixed in the review commit: the line is deleted (the security review's R1).
3. Fixed in the review commit: Status and Pins corrected.
4. Closed: the Windows box ticked with 41326040694.

## Verdict

Lands on `7e35b683`: run 41326040694 is green with its Windows legs, nothing High or Medium stands, the carried patch is recorded as §4.1 asks, the eight classes are true and claimed, the rebase kept #91's decision, and the four Lows are closed.
