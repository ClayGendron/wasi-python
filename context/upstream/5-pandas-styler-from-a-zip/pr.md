- **Project:** pandas (https://github.com/pandas-dev/pandas)
- **Against:** 3.0.6 (the pinned tarball)
- **Status:** drafted
- **Title:** BUG: Styler cannot find its templates when pandas is imported from a zip archive
- **Files:** pandas/io/formats/style_render.py
- **Why we carry it:** `df.style` (every Styler export) and `df.to_latex()` raise `jinja2.exceptions.TemplateNotFound: html.tpl` in the guest, because pandas' Python files are read from the stdlib zip and `FileSystemLoader` reads templates by path.

**This is a facts sheet, not pull request text** (question 80 in
`context/questions-for-the-owner.md`). pandas lets a contributor use AI tools to write code, but
not to speak for them in issues, pull requests or reviews. So the owner writes the issue and
the pull request in their own words, from the facts below, after reviewing and changing the code
as pandas asks. Nothing here has been posted, and no agent will post anything to pandas.

When spec 041 is built, this file moves unchanged to
`context/upstream/patches/pandas-3.0.6/0001-styler-templates-from-a-zip.md`. `fix.patch` is
copied byte for byte to `recipes/patches/pandas-3.0.6/0001-styler-templates-from-a-zip.patch`.
The evidence stays in `context/upstream/5-pandas-styler-from-a-zip/evidence/`, so every link
below is a path from the repository's top.

## What pandas asks of a contributor who used AI

All READ on 2026-10-17. The guide is `doc/source/development/contributing.rst`, served at
`https://pandas.pydata.org/docs/dev/development/contributing.html`, "Automated contributions
policy". `AGENTS.md` and `.github/PULL_REQUEST_TEMPLATE.md` were read on `main` with `gh api`.

- **Review and modify.** "You must fully review and modify the result of the automated tool."
  "You must ensure the contribution fully abides by all documented, contribution conventions in
  pandas."
- **Your own words.** "You must not use AI to speak for you when interacting with the
  community." In issues, pull requests and review comments, "do not use AI to speak for you".
  Help with grammar or translation is allowed, and must be disclosed.
- **Disclosure.** The contributor names the tool, the model and its version, and any
  reasoning-effort or thinking setting. If several tools or models were used, the disclosure
  says which part each did. pandas' `AGENTS.md` says the same in short: "harness, model,
  reasoning level". For this change, the agent's work was done in:
  - harness: Claude Code;
  - model: Claude Opus 5.5 (`claude-opus-5-5`);
  - reasoning level: not recorded by the drafting session. Do not guess it.

  The agent wrote the patch and these facts. A fresh agent with the same model reviewed both
  (`context/reviews/041-files-read-by-path-from-the-zip-spec-2026-10-17.md`).
- **Quoted tool output is marked.** Verbatim agent output that the contributor quotes goes in a
  `>` quote or a code fence. The tracebacks and outputs below are tool output, so fence them if
  you quote them.
- **The pull request template's AI box** reads: "I used AI to develop this pull request. I
  prompted it to follow `AGENTS.md`, I have reviewed and understood every change, and I have
  described above how I used it and exactly which tool, model version, and effort setting". The
  drafting session did not read pandas' `AGENTS.md`; the review read it afterwards. So the box
  is true only after you have gone over the change yourself with `AGENTS.md` in hand.
- **Agents never act on GitHub.** pandas' `AGENTS.md`: "Never perform issue- or
  pull-request-related actions on the pandas-dev/pandas GitHub repository on behalf of the
  user", including pushing code, opening issues or pull requests, and replying. In this project
  an agent only ever prepares a local branch (spec 020, Decision 2).
- **Issue first, then claim it.** An issue is open to work on when it has none of the labels
  Needs Triage, Needs Discussion, Needs Info or Closing Candidate, and nobody else holds it. You
  claim it by commenting `/take`, which assigns it to you. The guide's section "Issue assignment
  and the pull request lifecycle" says a pull request must be linked to an issue assigned to
  you. So the route is:
  1. a bug report in your own words;
  2. wait for triage;
  3. `/take`;
  4. the pull request, with "closes #…".
- **The rest of the template:**
  - "Tests added and passed if fixing a bug": see "A test, if the maintainers want one" below.
  - "All code checks passed": `pre-commit`.
  - "Added an entry in the latest `doc/source/whatsnew/vX.X.X.rst` file": under "Bug fixes,
    Styler".

  The carried patch has no whatsnew entry, since the guest ships no documentation. pandas asks
  for no contributor licence agreement.

## The facts

**What fails.** pandas' Python modules are read from a zip archive by zipimport, CPython's own
importer. Then the first use of the Styler fails while `pandas/io/formats/style_render.py`
defines `StylerRenderer`. The class body calls `env.get_template("html.tpl")`, so the import of
the module fails (tool output):

```
  File "pandas/io/formats/style_render.py", line 78, in StylerRenderer
  ...
jinja2.exceptions.TemplateNotFound: 'html.tpl' not found in search path:
'/usr/local/lib/python315.zip/pandas/io/formats/templates'
```

So `DataFrame.style`, every `Styler.to_*` export, and `DataFrame.to_latex()` fail. `to_latex()`
renders through the Styler. `DataFrame.to_html()` does not use jinja2, and it works. The
templates are in the archive; only the loader cannot see them.

**Why.** `StylerRenderer` builds `jinja2.FileSystemLoader(Path(__file__).parent.resolve() /
"templates")`. A path inside a zip archive is not a directory, so `FileSystemLoader` finds
nothing there. jinja2's `PackageLoader` reads templates through the package's loader. It has a
branch for `zipimport.zipimporter` that reads each template with `get_data` (jinja2 3.1.6,
`jinja2/loaders.py`, `PackageLoader.__init__` and `get_source`, READ).

**History, and two earlier reports that differ.**
- pandas used `PackageLoader("pandas", "io/formats/templates")` until pandas-dev/pandas#62123
  (merged 2025-08-15). That pull request moved to `FileSystemLoader` because, with newer
  meson-python, an editable install raised `ValueError: PackageLoader could not find a
  'io/formats/templates' directory in the 'pandas' package`. A plain revert would break editable
  installs again.
- pandas#38775 (2020, the Styler's templates in a PyInstaller bundle) was closed by a maintainer
  with "this is the pandas repo not pyinstaller". pandas#39733 (2021, the same error in an exe
  made by PyInstaller) was closed as a PyInstaller matter.
- This case is different in two ways. zipimport is CPython's own importer, not a third-party
  freezer. And the change does nothing wherever the Styler works today (next paragraph).

**The change.** Keep `FileSystemLoader` whenever the templates folder is a directory. Use
`PackageLoader` only when it is not:

```python
    if template_dir.is_dir():
        loader = jinja2.FileSystemLoader(template_dir)
    else:
        # pandas was imported from a zip archive, so its templates are not
        # files on disk. PackageLoader reads them through zipimport.
        loader = jinja2.PackageLoader("pandas", "io/formats/templates")
```

The class body loads `html.tpl` at once. So every install where the Styler works today has the
folder on disk, and it keeps today's loader. That covers a wheel, #62123's editable install
(its `__file__` is in the source tree, which has `templates/`), and a frozen application that
collects the templates as files. Only the case that fails today changes.

The comment says "imported from a zip archive". Strictly, the branch serves any install whose
templates are not a directory. In your own version you may write "for example, when pandas is
imported from a zip archive". The carried patch keeps the reviewed wording.

**Another way, for the maintainers to weigh.** A loader over `importlib.resources` would serve
every importer that supports resources, with no branch: `jinja2.FunctionLoader` reading
`files("pandas.io.formats") / "templates" / name`. But it changes the loader for every install,
so the smaller change comes first.

**How it was tested** (EXECUTED 2026-10-17):
- **In the guest.** The guest is a statically linked CPython 3.15.0 for `wasm32-wasip1`; its
  standard library and pure-Python packages are one zip on `sys.path`. With jinja2 3.1.6:
  - before the change, six Styler calls fail with `TemplateNotFound: html.tpl`;
  - after it, these give output equal, byte for byte, to the same calls on native CPython 3.15.0
    with pandas 3.0.6 installed normally: `to_html`, `DataFrame.to_latex`,
    `Styler.to_latex(environment="longtable")`, `to_string`, `to_typst`, and
    `Styler.from_custom_template` with a template that extends `html_table.tpl`;
  - evidence: `context/upstream/5-pandas-styler-from-a-zip/evidence/guest-run.txt`.

  The pre-build review repeated this with a seventh call (a custom `html_style` and `html_table`
  pair), comparing full SHA-256. `PackageLoader.list_templates()` gave the eight templates.
- **Natively, on a normal install.** The patched module takes the `FileSystemLoader` branch
  (`context/upstream/5-pandas-styler-from-a-zip/evidence/pandas-native.txt`). The review ran
  pandas' `pandas/tests/io/formats/style` and `test_to_latex.py` on a stock and on a patched
  install: 911 passed, 2 failed, 2 skipped on both. The two failures were matplotlib being
  absent, the same on both.

**A test, if the maintainers want one.** The template asks for one. The carried patch has none,
because pandas' test suite cannot build a zip-imported pandas: its compiled extensions cannot
load from a zip. The review wrote and ran a test that forces the branch:
- it monkeypatches `pathlib.Path.is_dir` to return `False`;
- it reloads `pandas.io.formats.style_render`;
- it skips on `ValueError`, which is #62123's editable case;
- it asserts the loader is a `PackageLoader`.

It passed on a patched wheel install and failed on stock (EXECUTED; the review's scratch
`pdtest/test_forced_branch.py`). Its limits:
- it proves the branch serves templates from a directory install, not from a zip;
- it skips under the editable installs pandas' CI uses;
- reloading a module inside the suite has side effects the maintainers may not want.

Whether to offer it is your call.

**Base.** The carried patch is against 3.0.6. pandas' `main` has the same three lines, with two
`#:` comments added above `loader` and `env` (READ 2026-10-17). When you ask, an agent rebases
the change onto `main` in a scratch clone and hands you the branch and these facts. It never
writes the description and never touches GitHub.
