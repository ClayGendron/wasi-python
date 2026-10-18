# Upstream 11: statsmodels' datasets from a zip archive

Status: **patch drafted; `pr.md` is a facts sheet, and anything filed upstream is the owner's,
in the owner's words** (statsmodels' AI policy, see `pr.md`). Nothing was posted. Carried by
spec 045 once built.

## How it was found

Spec 045's drafting loaded every bundled dataset with statsmodels zipped on `sys.path`, the
layout the guest's stdlib zip gives, and none loaded.

## The fix

When spec 045 is built, `fix.patch` is copied byte for byte to
`recipes/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.patch` and removed from this folder,
and `pr.md` moves unchanged to `context/upstream/patches/`. This folder then keeps these notes
and `evidence/`.

`fix.patch` (2 files, +37 −6, 2,783 bytes): SHA-256
`a83b56a1e52e211d49c83f8380f2ae1b66b383d9729144f761318674265add58`. It was made with `git diff`
under a cleared configuration (`env -i`, `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`),
and applies to the `statsmodels-0.15.0.tar.gz` sdist (SHA-256 `5d257fe5…ecbc`, equal to PyPI's)
with `git apply` and no offset (EXECUTED). `ruff check` passes on both changed files.

## Spec 045's leave-outs

Spec 045 also leaves out the data files of thirteen datasets whose stated terms the owner has
not approved, and every `datasets/*/src/` folder (`evidence/left-out.txt`, 35 names). That is
this project's licence rule, not part of the upstream change. With both applied, `import
statsmodels.api` works and a left-out dataset raises `FileNotFoundError` naming its file
(`evidence/native-run.txt`, item 6).

## Evidence

All under `evidence/`, run 2026-10-18 while drafting spec 045.

| file | what | label |
|---|---|---|
| `zip_pkg.py`, `zip_pure.py`, `zip_filter.py`, `zip_hybrid.py` | the zips, the leave-out filter, and the runner that imports from a zip with extension modules loaded by name | ours |
| `probe_datasets.py`, `elec.py`, `restricted.py` | every dataset loaded with a digest per frame (`elec_equip` apart, as it is not in `__all__`); the left-out probe | ours |
| `statistical_models-draft.py` | spec 045's drafted golden job | ours |
| `left-out.txt` | spec 045's 35 leave-outs | ours |
| `native-run.txt` | stock and patched, on disk and from a zip; the leave-outs; the job equal natively and from the zip | EXECUTED |
