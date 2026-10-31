# Review of 173 — drawsvg draws SVG and HTML

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** the specification as drafted, `context/specifications/173-drawsvg-draws-svg-and-html.md`, uncommitted on `research/drawsvg-png` from `dev` at `a750e8fe`, with the memo `context/research/2026-10-31-drawsvg-and-svg-to-png.md`, the new `decisions.md` entry, the amended constitution §4.12 and status line, and the roadmap sentence
- **Run:** none: a specification review
- **Re-ran:** no test run. Read drawsvg 2.4.2's installed tree in `build/spike-drawsvg/site/` and the spike's logs; read the cited code on `a750e8fe`.
- **Time box:** 45 minutes (a package and a judge change); kept.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning. No `gh` call was made and no run was dispatched.

**The claims checked.** All READ.

- `KINDS` is `tests/harness/shards.py:335` and `package_errors` is `:362`; the four kinds and their rules are as described: **verified**.
- `JOBS` is `tests/harness/jobs.py:33`; `test_every_package_names_its_own_suite` is `tests/checks/test_rules.py:1253`: **verified**.
- The bad-file table is `BAD_PACKAGES` at `tests/unit/test_shards.py:271`, not `:299` (the table runs to `:295`; `:299` is the test that reads it); each row replaces text that must occur once in `PACKAGES_TEXT` (Finding 5).
- The pdfplumber wheel line is `scripts/assemble_artifacts.py:160` and `wheel_licences` is `:581`; `LICENCE_COMPONENTS` and `PACKAGES` are `tests/harness/paths.py:102` and `:193`: **verified**.
- drawsvg's lazy imports: `raster.py:7-26` (`delay_import_cairo`), `video.py:5-15`, `color.py:3-13` (pwkit at import), `font_embed.py` (`urllib.request.urlopen`); `_repr_svg_` randomizes ids through `random` (`drawing.py:337-339`, `:430-432`): **verified**. The wheel's notice is `drawsvg-2.4.2.dist-info/licenses/LICENSE.txt`: **verified**.
- `--drop` takes a folder or an exact member (`scripts/make_stdlib_zip.py:345-352`), so `--drop drawsvg/widgets` works: **verified**.

## Acceptance criteria against evidence

1. The wheel's SHA-256 — the hash matches the spike's PyPI list (`build/spike-drawsvg/dl/list.txt`, READ); testable.
2. The golden job seen failing first — testable. It holds sameness, not correctness (Finding 3).
3. The guest check — testable, each row matches drawsvg's code (READ).
4. The unit rows and the rule check — testable, but the rule is wider than it should be (Finding 1).
5. The artifact-set checks — testable.
6. Bytes and fuel recorded, growth claimed — sound.
7. Fast tier, lint, `ci-status` — sound.

## Findings, most severe first

1. **Medium: the kind `none` is not tied to the package it excuses** (Decision 4; `tests/harness/shards.py:362`). As written, `package_errors` checks only that `reason` is not empty and that each `checked_by` name is in `jobs.JOBS`. Failure: a later specification marks a package that has a suite, or one no job imports, `kind = "none"` with `checked_by = ["utilities"]`; the rule check passes and nothing of that package runs anywhere, which is the gap spec 063 closed. Fix text for Decision 4: "`package_errors` also refuses a `none` entry when (a) a `tests/upstream/<name>.toml` exists, since a suite then exists; (b) a job it names does not import the package: the job's source, `tests/jobs/<job>.py`, parsed with `ast`, has no `import` or `from` of one of the distribution's import names, read from its `recipes/snapshot-packages.txt` line (`drawsvg: drawsvg`). A `via` that names a `none` entry stays refused, since `via` reaches only `suite` or `later` (`:388-397`); a unit row holds that too. The header comment says `none` is for a project that ships no tests at its pinned version, and a version move re-reads its sdist and its repository's tag and rewrites `reason`." Each refusal gets its unit row, seen once.
2. **Low: "the newest drawsvg at build" against a pin written everywhere** (Decision 1). The reason string, the oracle's `drawsvg==2.4.2`, the packages page and the package line all say 2.4.2. Fix text: "If PyPI has a newer drawsvg at build, every 2.4.2 moves with it, and the `none` reason is read again at that version: its sdist, and its repository at the release's tag."
3. **Low: say what the golden holds** (Decision 5). drawsvg is pure Python, so the job holds the guest's CPython to native's on drawsvg's code; it says nothing about whether drawsvg's SVG is right, which only upstream can test. That is honest for a project with no suite, and the job's docstring and the `reason` should say it in those words. Two cheap rows would reach code the six lines miss: an `Image(..., embed=True)` of a small PNG read from the data folder (the file read, base64 and the MIME guess), and a `Group`, `Use`, `ClipPath` and `Mask` drawing.
4. **Low: keep `drawsvg/widgets`** (Decision 1). Dropping it saves four members (about 100 k fuel a start at 173's 26 k a member) and changes the error from native's "No module named 'ipywidgets'" to "No module named 'drawsvg.widgets'", which no longer says what is missing. Fix text: "`drawsvg/widgets/` is packed; `import drawsvg.widgets` raises `ModuleNotFoundError` naming `ipywidgets`, as natively, and the guest check's row says so." If the drop stays, Decision 1 gives the member count as its reason.
5. **Low: the unit rows' fixture** (Decision 4; `tests/unit/test_shards.py:271`). Each `BAD_PACKAGES` row replaces text that must occur once in `PACKAGES_TEXT` (`:220`), and `_pkg` (`:263`) passes `NAMES` (`:252`). Fix text: "The fixture gains one `none` entry (its package in `NAMES`, its `checked_by` a name in `jobs.JOBS`), and the three refusals of Decision 4 and the two of Finding 1 are rows over it."
6. **Low: why `embed_google_font` fails** (Decisions 2 and 6). The guest's message is `URLError: unknown url type: https` (the memo's table): the guest has no `ssl` module, so no HTTPS handler, before any question of network. The limitations line should say both.

## Constitution checks

- §4.1: no patch; the stand-in for the message is weighed and refused for good reason (Decision 3).
- §4.12: drawsvg (MIT) approved on 2026-10-31 and shipped with its wheel's licence. The amendment's drawsvg clause is worded as approved. (The PNG route's clause is reviewed with 174.)
- §4.15: nothing loosened; `embed_google_font` fails closed.
- §5.6: the artifact set changes, so a review before the build is right. Not structural: nothing under `src/` changes, and the guest's imports and exports do not. Agreed.
- Pins: the wheel by URL and SHA-256 in `downloads/SHA256SUMS`. Planned.
- The judge: a new kind is a judge change and is named as one in the Kind line; with Finding 1 it stays narrow.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 (Medium) — taken: Decision 4 refuses a `none` entry when `tests/upstream/<name>.toml` exists or when no named job imports the package (read with `ast`), keeps `via` from naming one, and states the version-move rule.
2. Finding 2 — taken: Decision 1 moves every 2.4.2 with a newer pin and reads the `none` reason again at that version; criterion 1 records it.
3. Finding 3 — taken: Decision 5 says the golden holds sameness, not correctness, and adds the embedded-image and `Group`/`Use`/`ClipPath`/`Mask` rows.
4. Finding 4 — taken: `drawsvg/widgets/` is packed, and the guest check expects `ModuleNotFoundError` naming `ipywidgets`.
5. Finding 5 — taken: Decision 4 adds the fixture's `none` entry and the refusals as rows over it, at `:220`, `:252` and `:271`.
6. Finding 6 — taken: Decisions 2 and 6 give the cause, no `ssl` module and so no HTTPS handler, besides the missing network.

## Verdict

Fit to build after amendments: Finding 1 (the kind `none` tied to a suite's absence and to a job that imports the package) is written into Decision 4; Findings 2 to 6 are write-ins the builder applies.

Confirmed after amendments, 2026-10-31: Fit to build. I read the amended specification whole against the six findings (READ). Medium 1 is in Decision 4: a `none` entry is refused when `tests/upstream/<name>.toml` exists or when no job in `checked_by` imports one of the package's import names (read with `ast` from `tests/jobs/<job>.py`), a `via` naming a `none` entry stays refused, and the fixture rows sit at `tests/unit/test_shards.py:220`, `:252` and `:271`, which I checked. Findings 2 to 6 are in Decisions 1, 2, 4, 5 and 6 as the Disposition says; `drawsvg/widgets/` is packed and the guest check names `ipywidgets`. Nothing stands open.
