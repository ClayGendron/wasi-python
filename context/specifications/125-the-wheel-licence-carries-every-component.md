# 125: The wheel's LICENSE carries every component licence

- **Status:** **built 2026-10-23 on `wave/13`**; drafted and built the night before the 0.1.0 tag on the owner's instruction (2026-10-22: the FreeType credit out of the README, "follow the Pillow model"). Reviewed with 124 by one fresh agent (Landing notes).
- **Date:** 2026-10-22
- **Owner:** Clay Gendron
- **Kind:** **build-class** (the release workflow's wheel steps) and a **judge change** (`tests/`). Not structural: `src/` is unchanged. The artifact set is unchanged: `release/` is outside the set's key except `release/set_key.py` and the build constraints, and nothing under `scripts/` or `recipes/` changes.
- **Depends on:** 122 (the README it edits). Landed and unchanged: the licence rules that fill the set's `LICENSES/` folder.
- **Research it stands on:** a subagent's survey for the owner, 2026-10-22, in the session (sources READ through GitHub's API and the projects' pages; nothing downloaded or run): Pillow's CI appends each `wheels/dependency_licenses/*.txt`, FreeType's among them, to `LICENSE`, which ships in the wheel's `.dist-info/licenses/`; matplotlib lists `LICENSE/LICENSE_FREETYPE` as a licence file and checks its wheels carry it; Android's FreeType `NOTICE`, Firefox's about:license, Qt, OpenJDK and conda-forge ship the licence text or the credit outside any README. None of the projects surveyed puts the FreeType credit in a README. FreeType's licence (§2) asks a binary distribution's documentation for a disclaimer that the software is based in part on the FreeType Team's work, and does not define "distribution documentation"; its text suggests the sentence "Portions of this software are copyright © <year> The FreeType Project".

## Decisions

1. **Pillow's model** (the owner, choosing it over a `NOTICE` file and over keeping the README sentence). The wheel's one `LICENSE` is the project's Apache-2.0 text followed by every component licence the set carries, so whoever reads the package's licence metadata reads FreeType's licence, credit sentence included.
2. **The README no longer carries the credit.** Its Licences section says the wheel's `LICENSE` holds every licence. The rules check that held the README's sentence (`test_the_readme_carries_the_licences_credit_lines`) is retired, replaced by a check on the workflow and the judge's wheel check.
3. **Assembled at wheel time, not in the set.** `release/licences.py append <set>` rewrites the checkout's `LICENSE` just before `uv build --wheel`, in every job that builds one (the build job and both rebuilds, so the wheels stay byte-identical). The committed `LICENSE` stays Apache-2.0 alone, so GitHub's licence detection and badge are unchanged.
4. **Name order, a heading per file, dot files skipped.** The text is the project's licence, a "Third-party licences" heading, one line saying what follows, then each `LICENSES/*.txt` by name under a heading with its file name. A name starting with a dot is a host's litter. Running `append` twice gives the same file: the project's licence is the text before the heading.
5. **Checked twice.** The build job runs `release/licences.py check` on the wheel it built. The judge's `wheel_errors` compares `.dist-info/licenses/LICENSE` with the same text wherever a wheel is in `dist/` (the CI judge jobs).

## Intent

The wheel carries the licence text of everything it links, where a licence reader looks, and the README is a README.

## Design

- `release/licences.py` (standard library only): `own_licence`, `parts`, `combined`, `check`; `append` and `check` commands.
- `.github/workflows/release.yml`: the append line before each of the three `uv build --wheel` lines; the check line after the build job's.
- `tests/harness/scan.py`: `licence_step_errors` (every wheel build right after the append, and some wheel build followed by the check) replaces `credit_errors` and `FREETYPE_CREDIT`.
- `tests/checks/test_rules.py::test_the_wheel_carries_every_component_licence` replaces `test_the_readme_carries_the_licences_credit_lines`; the acceptance retires the old row.
- `tests/harness/artifacts.py`: `wheel_errors` loads `release/licences.py` by path and adds its `check`. `tests/unit/test_artifact_rules.py`: the fixture wheels carry the combined text; a new row shows a wheel without it, and without one file, named.
- `README.md` Licences: the FreeType sentence out; one sentence on the wheel's `LICENSE`.

## Scope

In: the above. Out: a `NOTICE` file; a credits page on the documentation site; the set's own `LICENSES/` contents (unchanged).

## Acceptance criteria

1. A wheel built from this tree with the set's `LICENSES/` carries `.dist-info/licenses/LICENSE` equal to `combined` (EXECUTED in a scratch copy, 2026-10-23: 70 component licences, 773,726 bytes, `check` exit 0, FreeType's credit sentence at line 3,033, `append` twice byte-identical; `License-File: LICENSE` in METADATA).
2. The fast tier passes with the new rows; the old row is retired at the acceptance.
3. The branch run's build job passes its check step, `same-bytes` matches both rebuilt wheels, and the judge jobs' wheel check passes.

## Landing notes

- The review, the branch run and the dry run are recorded here and in 124 once read.
