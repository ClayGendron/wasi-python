# Upstream 11: statsmodels' datasets from a zip archive

Status: **patch drafted; `pr.md` is a facts sheet, and anything filed upstream is the owner's,
in the owner's words** (statsmodels' AI policy, see `pr.md`). Nothing was posted. Carried by
spec 045 (`recipes/patches/statsmodels-0.15.0/`).

## How it was found

Spec 045's drafting loaded every bundled dataset with statsmodels zipped on `sys.path`, the
layout the guest's stdlib zip gives, and none loaded.

## The fix

Carried since spec 045's build began (2026-10-20, branch `spec/045-statsmodels`): `fix.patch` was
moved byte for byte (SHA-256 unchanged, `751e7190…db58`) to
`recipes/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.patch`, and `pr.md` (a facts sheet,
question 80's answer) moved unchanged to
`context/upstream/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.md`. It applies to the
pinned sdist through `scripts/steps/apply_patches.sh`, no offset (EXECUTED by the builder). This
folder keeps these notes and `evidence/`; the `fix.patch` named below is now that carried file.

When spec 045 is built, `fix.patch` is copied byte for byte to
`recipes/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.patch` and removed from this folder,
and `pr.md` moves unchanged to `context/upstream/patches/`. This folder then keeps these notes
and `evidence/`.

`fix.patch` (2 files, +41 −6, 2,979 bytes): SHA-256
`751e719065100f7b1373b663c9e1b4b9ebdae0a68aa3b31d1f1b8c34d5e8db58`. It was made with `git diff`
under a cleared configuration (`env -i`, `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`),
and applies to the `statsmodels-0.15.0.tar.gz` sdist (SHA-256 `5d257fe5…ecbc`, equal to PyPI's)
with `git apply` and no offset (EXECUTED). `ruff check` passes on both changed files under
statsmodels' configuration (EXECUTED, item 10; statsmodels pins no ruff version, ruff 0.14.0).

**Revised after spec 045's pre-build review** (findings 7 and 9): the helper is now private
(`_open_data_file`), its summary line ends with a period, and it falls back to a package
resource only for a `base_file` under `statsmodels/datasets/`, so a missing file elsewhere is a
`FileNotFoundError` as before (the first draft, `a83b56a1…dd58`, raised `ValueError`). The
leave-out list gained `statsmodels/sandbox/rlsdata.txt`. The evidence was re-run.

## Spec 045's leave-outs

Spec 045 also leaves out the data files of thirteen datasets whose stated terms the owner has
not approved, every `datasets/*/src/` folder, and `sandbox/rlsdata.txt`
(`evidence/left-out.txt`, 36 names). That is
this project's licence rule, not part of the upstream change. With both applied, `import
statsmodels.api` works and a left-out dataset raises `FileNotFoundError` naming its file
(`evidence/native-run.txt`, item 6).

## Evidence

All under `evidence/`, run 2026-10-18 while drafting spec 045.

| file | what | label |
|---|---|---|
| `zip_pkg.py`, `zip_pure.py`, `zip_filter.py`, `zip_hybrid.py` | the zips, the leave-out filter, and the runner that imports from a zip with extension modules loaded by name | ours |
| `probe_datasets.py`, `elec.py`, `outside.py`, `restricted.py` | every dataset loaded with a digest per frame (`elec_equip` apart, as it is not in `__all__`); the left-out probe | ours |
| `statistical_models-draft.py` | spec 045's drafted golden job | ours |
| `left-out.txt` | spec 045's 36 leave-outs | ours |
| `native-run.txt` | stock and patched, on disk and from a zip; the leave-outs; the job equal natively and from the zip | EXECUTED |
