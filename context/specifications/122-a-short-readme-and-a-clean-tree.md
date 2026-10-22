# 122: A short README and a clean tree

- **Status:** **drafted 2026-10-22; no pre-build review** (neither touches `src/` or the build
  recipe; AGENTS.md rule 8). Built in parallel with 123 (the documentation site), on disjoint
  files, for the one wave before the 0.1.0 tag (`decisions.md`, "The documentation before the
  0.1.0 tag, within a day"). No builder dispatches a branch run or loops on the fast tier: the
  judge runs once, as the lane's release acceptance on the wave's tip, then the dry run on main.
- **Date:** 2026-10-22
- **Owner:** Clay Gendron
- **Kind:** **judge change**; not structural, not build-class. A judge change because it edits
  `tests/` (the API page's path, the CLI generator, the scans' reach, 566 closers),
  `pyproject.toml` and `uv.lock`, all in the judge hash (`tests/harness/paths.py:277-287`), so the
  acceptance carries `--accept-judge`. Not build-class by AGENTS.md's definition: it touches no
  `scripts/`, `recipes/`, `downloads/SHA256SUMS` or the release workflow (`docs.yml` is a new,
  separate workflow that builds a web site; it neither builds nor publishes the artifact set). Not
  structural: `src/` is unchanged (Decision 9). The remaining files are context-class: `README.md`,
  `SECURITY.md`, `AGENTS.md`, `CHANGELOG.md`, `context/`, `docs/reference/`, `mkdocs.yml`,
  `.gitignore`, `.github/workflows/docs.yml`.
- **Depends on:** 123 (the documentation site), drafted beside it: 123 writes every page under
  `docs/` but the three this specification owns, and the lane rebases 123 first, so
  `mkdocs build --strict` and the nav resolve on this specification's tip (For the lane). Landed and
  unchanged: 002 (the judge), 019 (the command), 029 (the public API and its snapshot), 063 and
  067 (the upstream suites' TOML files, whose closers this specification retargets), 112 (strings
  speak for themselves).
- **Research it stands on:** `../research/2026-10-22-a-plan-for-the-documentation.md` (sections
  3, 5, 6 and 7; the five reports it folds in: the README's section map by line, the judge's reads
  of documents, the `context/` audit, tooling and deployment, the documentation systems). The
  owner's decisions of 2026-10-22 (`../decisions.md`, the newest entry). Every file and line this
  specification names was read on main `bb2235f2` (READ).

## The problem

The README is 3,753 lines (EXECUTED, `wc -l`): a user manual, a build manual, a release manual,
an 840-line generated API block (lines 2608 to 3444) and the project's history in one file, which
PyPI shows whole as the wheel's description. Its status lines are stale: line 15 says "alpha,
`0.1.0a1` … the next alpha moves to CPython 3.15.0 and wasi-sdk 33" while the line is at 3.15 and
wasi-sdk 34; lines 3698 to 3705 list scipy, seaborn and reportlab as out, and all three ship;
lines 673 to 678 tell a reader to "use `0.1.0a1` … once that version is on PyPI". It names
specifications, decisions and questions by number throughout, the internal vocabulary the public
page rule forbids. `pyproject.toml` says "Development Status :: 3 - Alpha", describes a product
with "numpy, pandas and matplotlib" and has no Documentation URL.

The tree carries files no code and no rule needs: `context/questions-for-the-owner.md` ("Open:
None"; its one paragraph names a private consumer's path), 55 research evidence folders (about
1,746 files, 14 MB; 20 with no memo), an unpublished advisory draft for a sandbox escape in a1 to
a3 (`context/upstream/advisories/GHSA-draft-0.1.0a3.md`).

The judge reads the README in eight places, so the cut is a judge change, and nothing may be lost
quietly (reports 1 and 2; each verified, READ):

| what the judge reads | where | the README today |
|---|---|---|
| FreeType's credit sentence, verbatim | `tests/checks/test_rules.py:30-35`, `tests/harness/scan.py:328-343` | lines 530 to 535 |
| `upstream patches carried: (\d+)` equal to the count under `recipes/patches/` | `test_rules.py:39-54`, `scan.py:2677-2680` | line 41 (27) |
| the guest's `-V` sentence, verbatim | `test_rules.py:398-410` | line 59 |
| at least one `default integer is N-bit` agreeing with the guest | `tests/checks/test_v1_3_data_stack.py:157-164` | line 59 |
| no heading containing "question"; no unresolved-item marker in the text | `test_rules.py:154-157`, `scan.py:382-389` | holds |
| no code span or fenced line naming an internal module or constant | `tests/checks/test_v1_4_public_api.py:228-235`, `tests/harness/api.py:659-671` | holds |
| exactly one generated API block, byte-equal to the live surface | `test_v1_4_public_api.py:280-287`; markers `api.py:84-85`; writer `api.py --write`, `--readme` defaulting to `README.md` (`api.py:1164`) | lines 2608 to 3444 |
| the token `README.md` as a `closes_with` closer; existence only | `test_rules.py:450-469` (line 462: `README.md` or `context/…`); `tests/harness/upstream.py:936-944` | 266 in `tests/known_gaps.toml`, 294 across 39 files under `tests/upstream/`, plus `pandas.toml:14`'s `excluded_closes_with` (EXECUTED) |

Six more closers name `context/questions-for-the-owner.md` (`known_gaps.toml:41, 65`;
`tests/upstream/numpy.toml:117, 122, 200, 256`; EXECUTED), so the file cannot go before they move.
`test_rules.py:701` reads two advisory records under
`context/research/2026-10-18-wasmtime-49-advisories/advisories/`, so that folder cannot go whole.

## Decisions

### 1. The README is cut to the standard-readme shape, about 150 lines

Title and one-line description; one paragraph on what it is and who it is for (code you did not
write, a model's included); the links line (Docs, Changelog, Security, Licence; status 0.1.0,
Apache-2.0); then these sections, in this order, each a few lines and a link to the site:

| section | keeps | from README lines |
|---|---|---|
| What you get | the four rows: `python.wasm`, `python-snapshot.wasm`, `python-stdlib.zip`, `MANIFEST` | 19-31 |
| Quickstart (5 minutes) | `pip install wasi-python` (or `uv add`); the pandas `run()` example with `(0, b'6\n')`; one `grants=` line; `wasi-python run -- -c "print(1)"` and its one JSON line (the line `release.yml:2310-2316` asserts); one sentence each for `Session`, `run_async`, `tools=` | 1026-1037, 1146-1160, 1656-1664, 2275-2280 |
| Safe by default | nothing writable unless granted (`root=True` for a fresh private `/`); 1 GiB, 60 s, 16 MiB per stream, 1,024 open files; fuel; a pointer to what is not protected | 1049-1059, 3479-3482, 3588 |
| What runs, and what does not | headline versions (numpy 2.5.2, pandas 3.0.6, scipy 1.18.1, scikit-learn 1.9.1, statsmodels 0.15.0, matplotlib 3.11.2, lxml 6.1.3, regex, about 30 pure-Python packages); the `-V` sentence **verbatim** as a blockquote; no processes, no network; the link to the limitations page | 59, 2421-2428 |
| Hosts | wasmtime 47 or later and WasmEdge 0.16 or later by default; wasmer, wazero and Node with a switch; the embedder's `pip install --no-deps wasi-python` and `wasi_python.artifacts()` | 656-672, 1039-1048 |
| API stability | the public surface (`__all__` of `wasi_python` and `wasi_python.tools`, the command, two environment variables); `0.MINOR.PATCH`; two minor releases of deprecation before a removal | 2579-2607 |
| Verifying a download | the `gh attestation verify` block **verbatim** (it names `ClayGendron/wasi_python`, the owner's case; keep it) | 1011-1025 |
| Building from source | `scripts/00_download.sh`, `scripts/build.sh`; the sentence carrying `upstream patches carried: 27` | 41, 680-690 |
| Contributing, security, changelog | three links; AGENTS.md is the contributor's rule book | 3722-3735 |
| Licences | Apache-2.0; FreeType's sentence **verbatim**, in the blockquote form `scan.py:333-343` reads (a `>` and line breaks are spaces) | 530-535 |

Every link is absolute: `https://github.com/claygendron/wasi_python/…` and
`https://claygendron.github.io/wasi_python/…` (the GitHub owner is `ClayGendron`; Pages hostnames
are lower-case; `pyproject.toml:31`'s Repository URL already uses the lower-case form). PyPI
renders the README as the long description and breaks relative links. The README names no
specification, decision, question, wave or review and no path under `context/` (Decision 6 makes
the scans hold it). The "Status" line says 0.1.0, CPython 3.15, wasi-sdk 34; the stale facts of
The problem go with the cut. The wheel's size and the two speed numbers of lines 34 to 54 move to
123's performance page; the README keeps none.

### 2. The generated API block moves to `docs/reference/python-api.md`

`tests/harness/api.py` keeps its markers (`api.py:84-85`) and its `--write` mode; its default page
becomes `docs/reference/python-api.md` (`api.py:35` `README` becomes `PAGE`; the `--readme` option
becomes `--page`; the hit messages name the page, not `README.md`). The page is a short heading,
one sentence saying it is generated and how (`uv run python tests/harness/api.py --write`), the
stability paragraph of README lines 2590 to 2607 reworded for 0.1.0 ("The promise starts at
0.1.0" loses "alphas may still change anything"), then the block. `test_v1_4_public_api.py:281-287`
reads the page; its message names the page. `api.readme_hits` (the internal-name rule,
`test_v1_4_public_api.py:228-235`) runs on **both** `README.md` and the page. The README has no
API block; `api.readme_block` on it returns `(0, None)`, and no check asks it to.

### 3. A CLI reference is generated from `cli._parser()`, and a check holds both pages current

A new `tests/harness/cli_doc.py` imports `wasi_python.cli` (importing `wasi_python` never loads
wasmtime), calls `_parser()` (`src/wasi_python/cli.py:74`) and renders a Markdown table per
subcommand: option, metavar, default, description. 12 of the parser's 14 options have no `help=`
(`cli.py:81-118`; EXECUTED), and `help=` strings are runner code, deferred to 0.1.1 (Scope), so the
generator carries a `DESCRIBED` mapping, option name to one sentence, for 0.1.0; the description
is the parser's `help=` when there is one, else the mapping's. The render fails on an option in
neither, and on a mapping entry the parser no longer has, so the mapping cannot drift. The same
begin and end markers as `api.py`'s (`<!-- cli reference: begin (generated by
tests/harness/cli_doc.py) -->`, `<!-- cli reference: end -->`), the same `--write` flag, the same
one-block rule, writing `docs/reference/cli.md`. A new check in `tests/checks/test_rules.py`,
`test_generated_pages_are_current`, fails when either page's block differs from the live render
and names the `--write` command. Unit rows in `tests/unit/test_cli_doc.py` cover the render, the
one-block rule and the two drift directions, written before the generator and seen failing.

### 4. The 566 `README.md` closers retarget to `docs/reference/limitations.md`

The six `context/questions-for-the-owner.md` closers (The problem) become `context/roadmap.md`:
question 89 is answered (`decisions.md:718`), and the roadmap is where the judge-only numpy test
binary it asked about is reserved.

The 560 `README.md` closers and `pandas.toml:14`'s `excluded_closes_with` become
`docs/reference/limitations.md`, and `test_rules.py:462` widens to `closer == "README.md" or
closer.startswith(("context/", "docs/"))` (its message says "under context/ or docs/"). Decided for
the retarget, against keeping `README.md` as the token, because the retarget is one exact-string
replacement over 40 files, verified by `grep -c` before and after (266, 294, 1; then 0), the judge
checks a closer's existence and nothing else, the page it names is this specification's own file
(so it exists on this tip, before any rebase), and no sameness difference can arise: the `closer`
field (`tests/harness/sameness.py:53`) is compared between records of the same tip, and this work
has one judge run. Keeping the token would leave 560 gaps pointing at a README that no longer
says what the gap is, which is the dishonest side. The reasons' free text ("README: On Windows",
"(README)", "README: the platform's facts") is **not** edited now: the limitations page carries the
headings "On Windows" and "The platform's facts" so each pointer still resolves to a section; the
reasons' wording follows in 0.1.1 (Scope). The upstream TOML files' `closes_with` are existence
checked whole (`upstream.py:940-943`), so the same path works there with no rule change.

### 5. The limitations page is this specification's, in Pyodide's shape

`docs/reference/limitations.md` is written here, not in 123, because the closers (Decision 4) and
the `-V` facts tie to it. Sections, in order, from the README's text rewritten for outside
readers: *The platform's facts* (the `-V` sentence; no threads, processes or network; no `_ctypes`,
`mmap`, sockets, `_ssl`, `_zstd`, `scipy.odr`; numpy's 32-bit default integer; no `dup`; no
floating-point flags; the 4 GiB address space; deep recursion; README lines 56-125, 500-528,
3521-3524), *SQLite* (locks; 164-208), *Packages that are not in the set* (pip in the guest,
SQLite's `load_extension`; 3698-3705), *On Windows* (1616-1655), *What the stdlib zip means*
(bytecode in a read-only zip; 1260-1318 in brief). Each fact gets one sentence of reason. It names
no specification, decision or question.

### 6. Both public-page scans reach `docs/` and the README

`scan.context_citation_files` (`scan.py:3479-3485`) adds `README.md` and every `*.md` under
`docs/`, read whole (prose, code spans and links alike; a Markdown page has no comment to isolate).
`test_rules.py:18`'s `CODE_DIRS` gains `"docs"`, and `test_no_embedder_name_in_code` also reads
`README.md`. The two generated pages are read too; their blocks come from docstrings `src/` already
holds to the string rule. The rules' phrases a page must avoid are listed for 123's builder in
123's Design (no "spec NNN", "question N", "memo", "§", "security review", "build review",
`context/…`, a review by date or path). The CHANGELOG, included on 123's changelog page by a
snippet, is read where it lives, not under `docs/`, so its spec numbers stay; it is a record.

### 7. The site's scaffold: `pyproject.toml`, `uv.lock`, `mkdocs.yml`, `docs.yml`, `.gitignore`

- `pyproject.toml`: description "A statically linked CPython for WebAssembly hosts
  (wasm32-wasip1) with numpy, pandas, scipy, scikit-learn, statsmodels, matplotlib and lxml
  compiled in."; classifier `Development Status :: 4 - Beta` (0.1.0 is the first release with a
  stability promise, under a 0.x version; Production/Stable is 1.0's); `Documentation =
  "https://claygendron.github.io/wasi_python/"` under `[project.urls]`; a dependency group
  `docs = ["mkdocs==1.6.1", "mkdocs-material==9.7.7"]` with a comment giving the reason (exact
  pins: a theme release changes the rendered site). `uv lock` updates `uv.lock`; `dev` is
  unchanged.
- `mkdocs.yml` (the text below is the contract; 123's builder uses the same file, uncommitted, to
  build locally): `site_name: wasi-python`; `site_url:
  https://claygendron.github.io/wasi_python/`; `repo_url:
  https://github.com/ClayGendron/wasi_python`; `strict: true`; `validation` with
  `omitted_files`, `absolute_links`, `unrecognized_links` and `anchors` all `warn` (which
  `--strict` makes errors); `theme: material` with `features: [navigation.tabs,
  navigation.sections, navigation.top, content.code.copy, search.suggest]` and a light and dark
  palette toggle; `plugins: [search]` only; `markdown_extensions: [admonition, tables, toc
  (permalink: true), pymdownx.highlight, pymdownx.superfences, pymdownx.tabbed (alternate_style:
  true), pymdownx.snippets (base_path: ["."], check_paths: true)]`; everything in the subset
  Zensical reads unchanged (report 4). The nav is exactly the page list in Scope's shared contract,
  in that order, with the section titles Get started, How-to guides, Reference, Explanation,
  Contributing.
- `.github/workflows/docs.yml`: `on: pull_request; push: branches: [main]; push: tags: ["v*"];
  workflow_dispatch`. `permissions: {}` at the top. `concurrency: {group: pages,
  cancel-in-progress: false}`. `env:` `UV_VERSION: "0.9.22"`, `UV_LOCKED: "1"`, `UV_PYTHON:
  "3.14.2"` (the values `set-cache.yml:26-28` uses). Job `build` (`contents: read`):
  `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`,
  `astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0` (both already in
  `set-cache.yml:42-45`), `run: uv run --group docs mkdocs build --strict`, `run: uv run python
  tests/harness/api.py` and `uv run python tests/harness/cli_doc.py` (the drift checks, exit code
  non-zero on drift), then `actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9
  # v5.0.0` of `site/`. Job `deploy` (`pages: write`, `id-token: write`; `environment:
  github-pages`; `needs: build`; `if: startsWith(github.ref, 'refs/tags/v') || github.event_name
  == 'workflow_dispatch'`): `actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d #
  v6.0.0`, `actions/deploy-pages@368f82528645a54fb793d4d04e342629a3f51346 # v5.0.1`. The builder
  re-reads each new SHA with `gh api repos/<owner>/<repo>/git/ref/tags/<tag>` before committing
  (GitHub's API, not an upstream download host). No `${{ }}` expression in a `run:` line; values
  through `env:` and `with:`. `test_every_action_is_pinned_by_commit` (`test_rules.py:568-572`)
  globs every workflow, so the pins are judged.
- `.gitignore`: `site/`.
- The owner enables Pages (Settings → Pages → Source: GitHub Actions); the first deploy is the
  `v0.1.0` tag's run. Until then `docs.yml` builds only.

### 8. The tree: what is deleted, and every pointer fixed

- `context/questions-for-the-owner.md`: deleted after Decision 4's six retargets. Its paragraph
  "The owner's direction for the product (2026-10-17)" moves to `decisions.md` as a dated entry,
  **without** the private path it quotes (the sentence ends at "its main use case is to work with
  a filesystem layer that manages the permissions and governance", in the owner's sense, marked as
  a paraphrase); `decisions.md:3` no longer says answers are moved "from" that file but that
  questions were asked there until 2026-10-22 and are in history. `context/README.md:24` (the tree
  line) and lines 43 to 48 (the exception paragraph) go; a one-line note replaces them: a
  decision only the owner can make is asked through the owner's channel and recorded in
  `decisions.md`. `constitution.md:6` is a dated Status record and stays.
- Research evidence folders: all 55 folders under `context/research/` are deleted **except**
  `2026-10-18-wasmtime-49-advisories/`, which `test_rules.py:701` reads and which stays where it is,
  whole (its two guard records are among ten; moving them is a judge change for no gain). The 35
  memos whose folders go keep their text; `context/README.md`'s `research/` line gains one sentence:
  evidence folders before 2026-10-23 are in git history at `bb2235f2`. No memo is edited
  (`research/` is append-only).
- `context/upstream/advisories/GHSA-draft-0.1.0a3.md`: deleted by the **lane at landing**, on the
  owner's word that the advisory is filed on GitHub and 0.1.0a3 yanked; if the owner has not said
  so when the wave lands, the file stays and the lane records why in the landing notes. The
  builder does not delete it.
- Pointers to moved README sections: `release/version.py:299`'s note becomes "see *Verifying a
  download* in the README" only if that section keeps its name (it does; Decision 1), so
  `version.py` and `tests/unit/test_release_version.py:174-184` are **unchanged**. `SECURITY.md:17-18`
  ("While the project is in alpha, fixes go into the next alpha") becomes "Only the newest
  release is supported; a fix goes into the next release, and older releases are not patched";
  its line 31 ("Verifying a download") still resolves; its line 50 ("Not protected") now points at
  the site's security-model page (`docs/explanation/security-model.md`, 123's). `AGENTS.md:78`
  becomes "All project knowledge lives in this repo under `context/` (the agents' memory) and
  `docs/` (what we tell users); no out-of-repo memory", and the "Code speaks for itself" rule
  gains one sentence: a page under `docs/` and the README name no specification, question,
  decision, wave or review number, no `context/` path and no name from `context/embedders.txt`
  (held by the scans of Decision 6).

### 9. `src/` is unchanged

Six docstrings and messages in `src/` point at README sections by name (`__init__.py:23` "API
reference"; `tools.py:24, 194` "The tool protocol"; `runner.py:148` "Mounts"; `_artifacts.py:83`
"see README.md"; `_tool_schema.py:187`). A pointer-only edit would still be a `src/` change and
make this runner code with a pre-build review (AGENTS.md rule 8), which the one-day plan forbids.
They stay, recorded here as stale pointers for 0.1.1 together with the `help=` strings (Scope);
none is a check's input.

### 10. The two lines the other specification needs are written here

`CHANGELOG.md` and `context/roadmap.md` are this specification's files. The builder writes the
CHANGELOG line for this specification and the one 123's Design gives for the site, under
"0.1.0 — unreleased", and one roadmap line reserving 0.1.1's documentation follow-ups (Scope's
list) with both numbers.

## Intent

A reader on PyPI or GitHub sees in 150 lines what this is, installs it, runs one sandboxed call
and knows where the rest is; the judge keeps every fact it kept before, in the file where the fact
now lives; the tree carries nothing the code, the rules or the owner no longer need.

## Design

Order of work for the builder (each step checkable alone, seconds each):

1. `grep -c 'closes_with = "README.md"'` and the questions-file closers: record the counts.
   Retarget (Decision 4); widen `test_rules.py:462`; `uv run pytest
   tests/checks/test_rules.py::test_known_gaps_are_well_formed -q` by its node id (the check
   needs the page: write `docs/reference/limitations.md` first, Decision 5).
2. `api.py`: `PAGE`, `--page`, messages; `test_v1_4_public_api.py:281-287` reads the page;
   `uv run python tests/harness/api.py --write` writes `docs/reference/python-api.md`; the check by
   node id.
3. `tests/unit/test_cli_doc.py` first, failing; then `tests/harness/cli_doc.py`;
   `uv run python tests/harness/cli_doc.py --write`; `test_generated_pages_are_current`; both by
   node id.
4. The README (Decision 1); the six README checks by node id (the table in The problem).
5. The scans (Decision 6): `test_code_outside_src_names_no_context_document` and
   `test_no_embedder_name_in_code` by node id, on a tree that holds 123's pages (copy 123's
   branch's `docs/` into the worktree for the run, uncommitted) so 123's builder hears of a hit
   before the rebase.
6. `pyproject.toml`, `uv lock`, `mkdocs.yml`, `docs.yml`, `.gitignore` (Decision 7);
   `uv run --group docs mkdocs build --strict` with 123's pages copied in, uncommitted.
7. The deletions and the pointers (Decision 8); `git status` shows the deletions and nothing
   untracked under `context/`.
8. `uv run ruff check` and `uv run ruff format --check`; the CHANGELOG and roadmap lines
   (Decision 10); the self-check list for the reviewer.

Nothing else runs: no fast tier, no branch dispatch (the owner, 2026-10-22).

## Scope

In: Decisions 1 to 10. The files: `README.md`, `SECURITY.md`, `AGENTS.md`, `CHANGELOG.md`,
`.gitignore`, `pyproject.toml`, `uv.lock`, `mkdocs.yml`, `.github/workflows/docs.yml`,
`docs/reference/python-api.md`, `docs/reference/cli.md`, `docs/reference/limitations.md`,
`tests/harness/api.py`, `tests/harness/cli_doc.py` (new), `tests/harness/scan.py`,
`tests/checks/test_rules.py`, `tests/checks/test_v1_4_public_api.py`, `tests/unit/test_cli_doc.py`
(new), `tests/known_gaps.toml`, `tests/upstream/*.toml`, `context/README.md`,
`context/decisions.md`, `context/roadmap.md`, the deletions. 123 touches none of these.

**The shared contract with 123** (both specifications carry this list; the nav in `mkdocs.yml`
names exactly these paths):

- 122 writes: `docs/reference/python-api.md`, `docs/reference/cli.md`,
  `docs/reference/limitations.md`.
- 123 writes `docs/index.md` and every other page: `docs/get-started/install.md`,
  `first-run.md`, `csv-through-a-grant.md`, `embed-python-wasm.md`; `docs/how-to/grants.md`,
  `mounts.md`, `sessions.md`, `limits.md`, `async.md`, `tools.md`, `matplotlib.md`,
  `excel-pdf-xml.md`, `embed-from-other-languages.md`, `verify-a-download.md`,
  `troubleshooting.md`; `docs/reference/results-and-errors.md`, `defaults-and-limits.md`,
  `guest-filesystem.md`, `tool-protocol.md`, `packages.md`, `support-and-versioning.md`,
  `artifacts.md`, `glossary.md`, `changelog.md`; `docs/explanation/why-wasi.md`,
  `how-it-works.md`, `security-model.md`, `fuel.md`, `sessions.md`,
  `pinned-releases-and-patches.md`, `performance-and-size.md`, `design-decisions.md`;
  `docs/contributing/first-change.md`, `building.md`, `adding-a-package.md`,
  `carrying-a-patch.md`, `review-and-landing.md`, `release-process.md`, `principles.md`.
- Pages 123 may omit if the day runs out (123's Design names the same list):
  `get-started/embed-python-wasm.md`, `how-to/excel-pdf-xml.md`, `reference/glossary.md`,
  `explanation/design-decisions.md`, `contributing/adding-a-package.md`,
  `contributing/carrying-a-patch.md`. On the rebase the lane deletes the nav line of each page
  absent on 123's tip and names it as a resolved conflict.
- Cross-links between pages are relative Markdown links to the `.md` file (`mkdocs` rewrites
  them; `--strict` checks them). The README and the three 122 pages link to 123's pages by these
  paths.

Out, for 0.1.1 (the owner, 2026-10-22; written on the roadmap by Decision 10): the quickstart and
how-to snippets run as a slow-tier guest job from files under `docs/examples/`; `help=` strings on
the command's options in `src/wasi_python/cli.py` (runner code; `cli_doc.py`'s `DESCRIBED` mapping
then empties); the six stale README pointers in `src/` (Decision 9); the reasons' "README"
wording in `tests/known_gaps.toml` and `tests/upstream/*.toml` (Decision 4); versioned docs
(`mike` or Zensical's); the roadmap's trim; archiving landed specifications with their reviews
and teaching the scans the archive path; the included-packages table generated from `MANIFEST`
and `tests/upstream/packages.toml` (123 writes it by hand for 0.1.0); a scheduled external link
check (`lychee`), upstream download hosts excluded.

## Acceptance criteria

A reviewer checks each by reading the diff, or by one of the commands this work allows.

1. **The README** is 120 to 180 lines (`wc -l`), in Decision 1's section order, and carries
   verbatim: FreeType's sentence, `upstream patches carried: 27`, the `-V` sentence, the
   `gh attestation verify` block, the CLI's one JSON line. Every link is absolute. No "spec",
   "decision", "question", "wave", "alpha" or `context/` in it; the status line says 0.1.0.
2. **The six README checks** pass by node id:
   `test_rules.py::test_the_readme_carries_the_licences_credit_lines`,
   `test_carried_patches_follow_the_rules`,
   `test_version_states_the_platform_semantics`, `test_specifications_have_no_open_question`,
   `test_v1_3_data_stack.py::test_default_integer_width_is_documented`,
   `test_v1_4_public_api.py::test_the_readme_reference_matches_the_api` (now reading the page).
3. **The generated pages** each carry exactly one block, byte-equal to `api.py`'s and
   `cli_doc.py`'s render; `test_generated_pages_are_current` passes; `tests/unit/test_cli_doc.py`
   passes and was seen failing before the generator existed (the builder's log under `build/122/`
   or the commit order). Every option of `cli._parser()` has a description on the page.
4. **The closers**: `grep -c 'closes_with = "README.md"' tests/known_gaps.toml tests/upstream/*.toml`
   is 0 everywhere; `grep -rc 'docs/reference/limitations.md' tests/known_gaps.toml
   tests/upstream/` sums to 561 (266 + 294 + 1); no closer names
   `context/questions-for-the-owner.md`; the file is gone; `test_known_gaps_are_well_formed`
   (`test_rules.py:447`) passes. No gap is added, removed or re-reasoned.
5. **The limitations page** has the headings "The platform's facts" and "On Windows", carries
   the `-V` sentence, and names no specification, decision or question.
6. **The scans** read `README.md` and `docs/**/*.md`: `test_code_outside_src_names_no_context_document`
   and `test_no_embedder_name_in_code` pass by node id on the wave's tip (For the lane); a page
   that says "spec 025" fails them (the builder shows one such run in the self-check list).
7. **The scaffold**: `uv run --group docs mkdocs build --strict` passes on the wave's tip; `docs.yml`
   has `permissions: {}` at the top, the per-job permissions of Decision 7, every `uses:` pinned
   to a 40-hex commit with its release in a comment, no `${{` in any `run:` line; `pyproject.toml`
   carries the classifier, description, Documentation URL and `docs` group;
   `test_every_action_is_pinned_by_commit` passes by node id.
8. **The tree**: `git ls-files context/research | grep /` lists only
   `2026-10-18-wasmtime-49-advisories/…`; no memo text changed (`git diff --stat context/research`
   shows deletions only); `context/README.md`, `decisions.md` and `AGENTS.md` carry Decision 8's
   edits; `SECURITY.md` says "alpha" nowhere; the advisory draft's fate is in the landing notes.
9. **`src/` is unchanged** (`git diff --stat main -- src/` is empty), so this is not runner code
   and not structural.
10. **Code speaks for itself**: no file under `tests/`, `release/` or `.github/workflows/` the
    change touches names a specification, review, finding or `context/` path (the rules checks).
11. **ruff** `check` and `format --check` pass.

## For the lane

- **Wave kind: judge change**, parallel-safe in files with 123. One wave: 123 then 122, in that
  order, so 122's `mkdocs.yml` nav, its README links and its 561 closers resolve on 122's tip. 122's
  builder rebases onto 123's tip and names every conflict (none expected: the files are disjoint).
- **No builder judge runs.** Builders run `uv run ruff check`, `uv run ruff format --check`, the
  node ids named in the criteria, `uv run python tests/harness/api.py --write`, `uv run python
  tests/harness/cli_doc.py --write` and `uv run --group docs mkdocs build --strict`. No branch run
  is dispatched; no fast tier loops. The reviewer reads the diff and the self-check list without
  re-running the judge.
- **The lane, on the wave's tip**: `uv run --group docs mkdocs build --strict` (seconds) and the
  two scans by node id before the release acceptance, so a nav path or a page's phrase fails here
  and not on `docs.yml`'s first run on main; then the normal-tier run without `--accept`, green;
  then `uv run pytest -n 6 --tier release --accept "Release 0.1.0: the release tier; 122: a short
  README and a clean tree; 123: the documentation site" --accept-judge "122: the API page moves
  to docs/reference/python-api.md, the CLI page is generated and held current, the scans read
  docs/ and the README, 561 closers name docs/reference/limitations.md and six name the roadmap;
  pyproject's docs group"` (the wording is the lane's); then the dry run on main (rule 6b); then
  the owner's tag, whose `docs.yml` run is the first deploy.
- **The claim list**: changed, not retired: `test_the_readme_reference_matches_the_api` (reads the
  page), `test_known_gaps_are_well_formed` (the widened rule), the two scans (wider reach);
  new: `test_generated_pages_are_current`, the unit rows of `tests/unit/test_cli_doc.py`. No fuel
  or bytes change: nothing in the guest or the set moves.
- **Sameness**: the `closer` field changes for 567 rows between any record from before this
  landing and one after; the lane's acceptance and the dry run are both on the tip, so no
  difference appears between them. A comparison against an older record names the retarget as
  its one class of difference.
- **The advisory draft**: deleted at landing on the owner's word (Decision 8), else kept and
  noted.
- **Pages**: the owner sets Settings → Pages → Source to GitHub Actions before the tag; the
  README's documentation links point at a site that serves only after the tag's `docs.yml` run.

## One line

Cut the README to 150 lines that keep every sentence a check reads, move the API block to a
generated page beside a generated CLI page and the limitations page the 561 gaps now name, teach
the scans to read the public pages, scaffold the site, and delete what no code or owner needs,
with `src/` untouched and the judge run once.

## Landing notes

Not yet built.
