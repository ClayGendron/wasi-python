# Upstream 5: pandas' Styler from a zip archive

Status: **patch drafted; `pr.md` is a facts sheet, and anything filed upstream is the owner's, in the owner's words** (pandas'
automated contributions policy, see `pr.md`). Nothing was posted. Carried by spec 041 once built.

## How it was found

The default-profile memo ran jinja2 in the guest and saw `df.style` and `df.to_latex()` fail
(`../../research/2026-10-17-what-else-the-default-profile-carries.md`, finding 4d). Spec 039 made
it a known gap with a check; spec 041 closes it with this patch.

## The fix

When spec 041 is built, `fix.patch` is copied byte for byte to `recipes/patches/pandas-3.0.6/0001-styler-templates-from-a-zip.patch` and removed from this folder, and `pr.md` (a facts sheet, question 80) moves unchanged to `context/upstream/patches/`. This folder then keeps these notes and `evidence/`.

`fix.patch` (1 file, +6 −1): `StylerRenderer` keeps `FileSystemLoader` when its `templates`
folder is a directory, and uses `jinja2.PackageLoader("pandas", "io/formats/templates")` when it
is not. pandas-dev/pandas#62123 is why the old one-line `PackageLoader` is not simply restored.
SHA-256 `0b6b418bd09c3be47590244720648b37c096656e883eefba693f0d44bb6fce7d`; it applies to the
pinned `pandas-3.0.6.tar.gz` with `git apply` and no offset (EXECUTED).

## Evidence

All under `evidence/`, run 2026-10-17 while drafting spec 041.

| file | what | label |
|---|---|---|
| `files.py` | the probe: six Styler calls, a custom template that extends `html_table.tpl`, and the graph atlas; each output's length and SHA-256 prefix | ours |
| `guest-run.txt` | native, then the guest with stock pandas (all six Styler calls `TemplateNotFound: html.tpl`), then the guest with the patched `style_render.pyc` (every output equal to native; the loader is `PackageLoader`) | EXECUTED |
| `pandas-native.txt` | natively the patched module keeps `FileSystemLoader`; `PackageLoader` also finds `html.tpl` on a directory install | EXECUTED |

The guest runs used today's plain `python.wasm` and spec 039's drafting zip (3,791 members)
with the two members replaced, compiled by step 70's own `pyc` under the line's Python 3.15.0.
