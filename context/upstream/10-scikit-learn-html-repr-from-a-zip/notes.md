# Upstream 10: scikit-learn's HTML representation from a zip archive

Status: **patch drafted; `pr.md` is a facts sheet, and anything filed upstream is the owner's,
in the owner's words** (scikit-learn's automated contributions policy, see `pr.md`). Nothing was
posted. Carried by spec 044 once built.

## How it was found

Spec 044's drafting imported scikit-learn's Python files from a zip, with its extension modules
loaded by name (a model of the guest's import path, `evidence/zip_hybrid.py`), and `import
sklearn` failed at the style sheets.

## The fix

When spec 044 is built, `fix.patch` is copied byte for byte to
`recipes/patches/scikit_learn-1.9.1/0001-html-repr-styles-from-a-zip.patch` and removed from this
folder, and `pr.md` moves unchanged to `context/upstream/patches/`. This folder then keeps these
notes and `evidence/`.

`fix.patch` (1 file, +8 −10, 1,848 bytes): SHA-256
`1aafac3873917af878a8174a3431fafdada6e05ad49cd17fb37297b5af74b12b`. It was made with `git diff`
under a cleared configuration (`env -i`, `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`),
and applies to the `scikit_learn-1.9.1.tar.gz` sdist (SHA-256 `629cada3…2977`, equal to PyPI's)
with `git apply` and no offset (EXECUTED). `ruff check` passes on the changed file.

## Evidence

All under `evidence/`, run 2026-10-18 while drafting spec 044.

| file | what | label |
|---|---|---|
| `zip_pure.py`, `zip_hybrid.py` | the zip of the packages' Python files, and the runner that imports from it with extension modules loaded by name | ours |
| `import_probe.py`, `html_repr.py` | the import probe and the HTML representation probe | ours |
| `machine_learning-draft.py` | spec 044's drafted golden job | ours |
| `native-run.txt` | stock fails at import from the zip; patched imports; the HTML representation equal to stock on disk; the job equal natively and from the zip | EXECUTED |
