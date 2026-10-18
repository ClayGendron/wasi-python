- **Project:** pandas (https://github.com/pandas-dev/pandas)
- **Against:** 3.0.6 (the pinned tarball)
- **Status:** drafted
- **Title:** BUG: Styler cannot find its templates when pandas is imported from a zip archive
- **Files:** pandas/io/formats/style_render.py
- **Why we carry it:** `df.style` (every Styler export) and `df.to_latex()` raise `jinja2.exceptions.TemplateNotFound: html.tpl` in the guest, because pandas' Python files are read from the stdlib zip and `FileSystemLoader` reads templates by path.

This draft is not the pull request's description. pandas' automated contributions policy
("Contributing to pandas", *Automated contributions policy*, READ 2026-10-17 at
`https://pandas.pydata.org/docs/dev/development/contributing.html`) allows a tool to help write
the code, but says "in issues, pull requests, and review comments, do not use AI to speak for
you", and asks the contributor to disclose the tool, the model and its version, and the effort
setting. So the owner writes the description from the facts below. The change itself was written
by an agent (Claude Opus 5.5, in Claude Code), which the disclosure says.

When this patch is built (spec 041), this file moves, unchanged, to
`context/upstream/patches/pandas-3.0.6/0001-styler-templates-from-a-zip.md`, and `fix.patch` is
copied, byte for byte, to `recipes/patches/pandas-3.0.6/0001-styler-templates-from-a-zip.patch`.

## The facts, for the owner to write from

**What fails.** When pandas' Python modules are imported from a zip archive (zipimport), the
first use of the Styler fails while `pandas/io/formats/style_render.py` defines
`StylerRenderer`:

```
jinja2.exceptions.TemplateNotFound: 'html.tpl' not found in search path:
'/usr/local/lib/python315.zip/pandas/io/formats/templates'
```

So `DataFrame.style`, every `Styler.to_*` export, and `DataFrame.to_latex()` (which renders
through the Styler) fail. `DataFrame.to_html()` does not use jinja2 and works. The templates are
in the archive; only the loader cannot see them.

**Why.** `StylerRenderer` builds `jinja2.FileSystemLoader(Path(__file__).parent.resolve() /
"templates")`. A path inside a zip archive is not a directory, so `FileSystemLoader` finds
nothing. jinja2's `PackageLoader` reads templates through the package's loader, and has a branch
for `zipimport.zipimporter` that reads each template with `get_data` (jinja2 3.1.6,
`jinja2/loaders.py`, `PackageLoader.__init__` and `get_source`, READ).

**History.** pandas used `PackageLoader("pandas", "io/formats/templates")` until pandas-dev/pandas
#62123 (merged 2025-08-15) replaced it with `FileSystemLoader`, because with newer meson-python
an editable install raised `ValueError: PackageLoader could not find a 'io/formats/templates'
directory in the 'pandas' package`. A plain revert would break editable installs again. The
change keeps `FileSystemLoader` whenever the folder exists, and uses `PackageLoader` only when it
does not:

```python
    if template_dir.is_dir():
        loader = jinja2.FileSystemLoader(template_dir)
    else:
        # pandas was imported from a zip archive, so its templates are not
        # files on disk. PackageLoader reads them through zipimport.
        loader = jinja2.PackageLoader("pandas", "io/formats/templates")
```

Every install where the Styler works today (a wheel, an editable install, a frozen application
that collects the templates as data files) has the folder on disk and keeps exactly today's
loader. Only the case that fails today changes.

**Another way, for the maintainers to weigh.** A loader over `importlib.resources`
(`jinja2.FunctionLoader` reading `files("pandas.io.formats") / "templates" / name`) would serve
every importer that supports resources, without a branch. It changes the loader for every install,
so the smaller change is proposed first.

**How it was tested.**
- In a statically linked CPython 3.15.0 for `wasm32-wasip1`, whose standard library and
  pure-Python packages are one zip on `sys.path`, with jinja2 3.1.6: before the change, six
  Styler calls fail with `TemplateNotFound: html.tpl`; after it, `to_html`, `DataFrame.to_latex`,
  `Styler.to_latex(environment="longtable")`, `to_string`, `to_typst`, and
  `Styler.from_custom_template` with a template that extends `html_table.tpl` give output equal,
  byte for byte, to the same calls on native CPython 3.15.0 with pandas 3.0.6 installed normally
  (`evidence/guest-run.txt`, EXECUTED 2026-10-17).
- Natively, on a normal install, the patched module takes the `FileSystemLoader` branch
  (`evidence/pandas-native.txt`, EXECUTED).
- No test is added. Building a zip-imported pandas in pandas' test suite needs its compiled
  extensions outside the archive, and a test that forces the `PackageLoader` branch fails under
  the editable installs pandas' own CI uses (the reason for #62123). The owner may ask the
  maintainers whether they want one.

**What pandas asks for besides the code.** A whatsnew entry under the next release's "Bug fixes,
Styler" heading (`doc/source/whatsnew/`), written when the pull request is rebased onto `main`;
the carried patch leaves documentation out, since the guest does not ship it. pandas asks for no
contributor licence agreement.

**Base.** The carried patch is against 3.0.6. pandas' `main` has the same three lines, with two
`#:` comments added above `loader` and `env` (READ 2026-10-17); the agent rebases the change onto
`main` in a scratch clone when the owner asks to send it.
