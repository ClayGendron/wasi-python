# Review of 167 — pdfplumber and xarray (the first pull request, #77)

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** `origin/dev...e262f17a` (dev at `117bcd67`), 56 files; then the fix commit `7b22202a`
- **Run:** 41214665033 on `7b22202a` (relayed): gather and 13 Windows legs green; `ci-status` red only for this file; one unclaimed `GROWTH` row (Finding 6)
- **Re-ran:** (darwin arm64, the builder's set) `tests/lint`, the wheel-limit unit row, both claim-shape checks → 17 passed; the cryptography row (both binaries) and the two goldens → 4 passed; the well-formed check and `pdfminer-six-smoke` → 2 passed. Fast tier not run. At `7b22202a`: lint, the new mmap row (both binaries), well-formed, news shape → 18 passed. All exit 0.
- **Box:** 45 minutes (a package); kept.

## Acceptance criteria against evidence

1. Licence sweep before choice 1 — met (READ, the landing notes).
2. Growth per distribution and the wheel's bytes — met (READ). +2,091,901 bytes, 185 members, wheel 101,631,881.
3. `wheel_errors` refuses a wheel over `PYPI_FILE_LIMIT` — met (EXECUTED, the unit row). It runs in `test_wheel_carries_the_artifact_set` on every run that builds a wheel (READ).
4. No `pdfminer/cmap/` member, and the trees are their tarballs plus their patches — met. The guest row asserts the first; MANIFEST's hash of the patch equals its `shasum` (EXECUTED).
5. Two goldens match native — met (EXECUTED).
6. AES and `to_image` name their modules — met (EXECUTED). Seen failing without the patch (READ, the landing notes).
7. Classes recorded, families pass in their tiers, growth claimed — met for the normal tier (EXECUTED: pdfminer-six smoke). The release groups were measured before the rebase onto 165 (READ).
8. plotly cites PyPI's limit — not in this pull request (deferred by the owner).
9. Fast tier, `tests/lint`, `ci-status` — lint is green (EXECUTED); the rest wait on the run.

**The judge.** Each class's members are an exact list by node id (`test_upstream_class`, `class_findings`). A new failure is red as a `+id` even if a pattern catches it (Finding 3).

Every cap is at most `rule_cap(measured)`, and each family's `budget` is the sum of its caps (EXECUTED). pdfminer-six-smoke's cap, 1.479 times its measure, is tighter.

Each test runs once. `smoke_ignores` leaves pdfplumber's and pdfminer's smoke files out of their `tests` groups. xarray's eight release groups list 68 files. With the 3 smoke files, that is all 71 `test_*.py` in the sdist's `xarray/tests`, with no duplicates (EXECUTED, `comm`); `properties` is in `xarray-r-arrays`.

`xarray.ini`'s one `ignore` is upstream's own line (READ).

**The patch** is minimal. The draft discloses its one side effect (`default_backend()` in `_aes_cbc_encrypt`). The CHANGELOG line names the patch's path.

**pytz** is pinned by URL and SHA-256 in `kit-extra.txt`. The cached wheel's hash matches (EXECUTED). Only xarray's `kit_extra` names it, and the zip holds no `pytz/` (EXECUTED).

**The mmap limitation** is true (EXECUTED in the guest): by path it raises `OSError`; `mmap=False` or an open file reads. Finding 2 asked for its check.

**The news file** follows the house shape (EXECUTED). Its claim covers growth, the new checks and every verdict-bearing judge file. `release-claims.toml` carries the ten release groups and the sixteen classes. `tests/harness/artifacts.py` is not verdict-bearing; its hash records it.

## Findings, most severe first

1. **Low: two xarray classes name a closer that does not close them** (`tests/upstream/xarray.toml`, `fails-natively` and `staged-tests-folder`; their gaps in `tests/known_gaps.toml`). Both close with `docs/reference/limitations.md`, but that page says nothing of either.
   - `staged-tests-folder` is an artefact of where the tests are staged. matplotlib's `stage-layout` class has the same cause and closes with `context/roadmap.md`.
   - `fails-natively` fails natively too. pillow's like class closes with its upstream notes file.
   
   Fix text: `closes_with = "context/roadmap.md"` for `staged-tests-folder`. For `fails-natively`, close with a roadmap line, "re-read at the next xarray pin". Make the same change in both gaps. This is a judge-file edit, so the author makes it, or answers in writing.
2. **Low: the documented `mmap=False` route has no check, and the raise is held only in the release tier** (`docs/reference/limitations.md:53`, `docs/reference/packages.md`). The golden reads netCDF3 from a `BytesIO` only. Fix text: in `labelled_arrays.py`, write `ds.to_netcdf(out / "t.nc")` and print `open_dataset(out / "t.nc", mmap=False).identical(ds)`. Native prints the same line. Or answer in writing that the 161 members of the release classes hold the raise.
3. **Low: three patterns are wider than their cause** (`xarray-r-rest` `wasm32-int32`: `int32|int64|…`; `xarray-r-backends` `no-mmap`: `|DID NOT WARN`; `pdfminer-six-r` `no-cjk-cmaps`: `AssertionError: 'Hello`). Because membership is exact, nothing new is hidden. A listed member that starts failing for a new reason the pattern still matches would stay quiet. Fix text: narrow each to its message the next time the file is edited, for example `dtype\('int32'\)|dtype=int32|int32 ` for the int32 class. No round is needed.
4. **Low: xarray's ten gaps sit after the section's closing comment** (`tests/known_gaps.toml:1866`, "The pure-Python packages' own tests. (end)"). No code reads the marker. Fix text: move the ten `[[gap]]` tables above line 1866, beside pdfminer's.
5. **Low: pyHanko's notice is shipped by reference** (`LICENSES/pdfminer-six.txt`, the `_saslprep.py` block). The header's "licensed under the license of the pyHanko project (see LICENSE file)" ships with Valvekens' copyright line. The MIT permission text reaches the reader only as pdfminer's own `LICENSE`. That meets MIT's condition in substance, and recording it is enough. Pinning pyHanko's `LICENSE` from its release tag, as statsmodels' `parallel_func` notice is pinned, would make it exact. The PSF text in xarray's folder ships more than anything cites, which costs nothing; recording it is enough.
6. **Low: `matplotlib-rest-a` gains two passes, unclaimed** (run 41214665033, `GROWTH`: 966 → 968). The cause is xarray in the zip, not pytz. `test_cbook.py::test_reshape2d_xarray` and `::test_index_of_xarray` take matplotlib's `xr` fixture, which skips without xarray; `test_cbook.py` is in `matplotlib-rest-a` (READ). The two pytz tests in `test_dates.py` stay skipped: a family's kit is `kit.txt` alone, and `kit_extra` only reaches its own family's root (`packages.py`, the stage), and the zip holds no `pytz/` (EXECUTED). No pandas group runs `test_to_xarray.py` (READ). Failure: after the merge the row is recorded unclaimed, and the release pull request asks for its reason. Fix text: in the news file's claim, `passes = ["tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[matplotlib-rest-a]"]`, and the two tests named in the claim's reason.

## Constitution checks

- §4.1: one patch, recorded, hashed in MANIFEST, named in the CHANGELOG, with its draft. Holds.
- Pins: three product files and two test archives are in `SHA256SUMS` and `00_download.sh`; pytz is in `kit-extra.txt`. Holds.
- §4.12: within the owner's approval of 2026-10-31 (Finding 5 is a note, not a gap).
- §5.6: the pre-build review stands, with its Disposition taken.
- 4a Structure: nothing under `src/`. Not structural. Holds.
- 4b `.github/workflows/release.yml`: only the count `^30 passed` → `^32 passed` and its comment, in the three tree-check steps. Nothing else runs, is refused or holds a token differently.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Fixed in `7b22202a`: both close with `context/roadmap.md`, each with a Reserved line; both gaps match. **Reviewer:** confirmed (READ).
2. Fixed in `7b22202a`: the guest row `test_xarray_reads_netcdf3_files_without_mmap`, seen failing first. **Reviewer:** confirmed (EXECUTED, both binaries pass).
3. Fixed in `7b22202a`: each pattern is its members' own messages; the author re-ran the three groups, digests unchanged. **Reviewer:** confirmed (READ; the groups not re-run here).
4. Fixed in `7b22202a`: the marker follows the last gap. **Reviewer:** confirmed (READ).
5. Answered in writing: recorded in the landing notes; pinning pyHanko's `LICENSE` is left for later. **Reviewer:** accepted.
6. Fixed in the review commit: the claim's `passes` names `matplotlib-rest-a`, its comment the two tests and the cause. **Reviewer:** confirmed (READ).

## Verdict

Lands: no High or Medium stands, the six Lows are fixed or answered, and run 41214665033 is green but for this file.
