# Review of wave 13's integration (123, 122)

- **Date:** 2026-10-22
- **Reviewer:** a fresh agent (Claude Opus 5.5). I wrote none of 122 or 123 and reviewed neither before. Their build reviews belong to other agents. I am the wave's integration reviewer (AGENTS.md rule 8; constitution §5.7).
- **Reviewed:** the wave's tip **`2f218a29`** (branch `wave/13`) on main **`fb8343cd`**. It is linear: 123's two commits (`92a134d3`, `b7066df3`, a fast-forward), 122's two commits cherry-picked on top (`c8de1c55`, `961e0f6d`; no conflicts), and the lane's commit `2f218a29` (the two build reviews; the advisory draft deleted, its row in `context/upstream/README.md` dated).
- **Read first:** AGENTS.md rules 2, 4 and 8; `context/reviews/README.md`; `decisions.md`'s newest entries (the owner's rule for this documentation work: the judge runs once, at the end; reviewers read diffs); both specifications; both build reviews; wave 12's integration review as the model.
- **Run:** the lane's release acceptance, running; not read by this review. While it ran (`build/lane.lock` present) I ran no pytest, no `uv sync`, nothing in the main tree's `.venv`, and wrote nothing in the main tree but this file.
- **Ran** (all in a `git archive 2f218a29` copy in my scratchpad, with its own environment, `UV_PROJECT_ENVIRONMENT=<scratchpad>/wave13-venv`):
  - `uv run --group docs mkdocs build --strict`: **exit 0, no warning**, 42 pages built. `uv.lock` is byte for byte the tip's afterwards.
  - With `UV_LOCKED=1`, as `docs.yml` sets it: `uv run python tests/harness/api.py --check` **exit 0**, `uv run python tests/harness/cli_doc.py --check` **exit 0**, and again with `FORCE_COLOR=1` **exit 0**. So the lock is current and both generated pages equal the live surface.
  - `git diff` of the tip against each reviewed tip; `git grep` for pointers to the deleted files; read-only `gh api` reads of the Pages site and the `github-pages` environment.
- **Box:** 12:50 to 13:30.

## 1. The rebase (EXECUTED)

**122 on the wave is its reviewed tip.** `git diff e7ac6dde 2f218a29 -- . ':!docs' ':!context/reviews' ':!context/specifications/123*' ':!context/upstream'` is **empty**. 122's three pages under `docs/` (`reference/cli.md`, `limitations.md`, `python-api.md`) are byte for byte `e7ac6dde`'s. So the 122 that wave 13 carries is the reviewed 122, plus its fixes to the build review that the lane read.

**123 on the wave is its reviewed tip.** `git diff b7066df3 2f218a29 -- docs` adds exactly 122's three pages; no page of 123's changed. `context/specifications/123-the-documentation-site.md` and `docs/index.md` are unchanged. Every other file in that diff is 122's (its files listed in its specification), the lane's two reviews, or the lane's advisory deletion.

**The lane's commit** touches four files, all `context/`: the two build reviews, the deleted `context/upstream/advisories/GHSA-draft-0.1.0a3.md`, and its row in `context/upstream/README.md`, which now says it was published as GHSA-w99p-2jv3-fvj6 and is in git history.

No difference to name.

## 2. The combined site (EXECUTED)

- **The strict build passes on the tip.** `mkdocs.yml` sets `strict: true` and every `validation` key to `warn`, so a missing page, an orphan page, a broken relative link or a missing anchor fails the build. It built.
- **The nav and the pages agree.** The nav has 42 entries (Home 1, Get started 3, How-to 11, Reference 12, Explanation 8, Contributing 7). `docs/` has 42 Markdown files. Each is in the nav once. The omitted `get-started/embed-python-wasm.md` is out of both, as 122's fix says.
- **Every README link to the site resolves.** The README links the site root and ten pages: `get-started/first-run/`, `reference/artifacts/`, `reference/packages/`, `reference/limitations/`, `explanation/security-model/`, `how-to/embed-from-other-languages/`, `reference/python-api/`, `reference/support-and-versioning/`, `contributing/building/` and `contributing/first-change/`. Each has its `index.html` in the build. `SECURITY.md`'s link (`explanation/security-model/`), `pyproject.toml`'s Documentation URL and `mkdocs.yml`'s `site_url` are the same base. No README link carries an anchor.
- **The cross-links resolve.** Fourteen links from 123's pages into 122's three (`limitations.md` from nine pages, `cli.md` from three, `python-api.md` from two), and 122's four outward (`cli.md` to `python-api.md`, `python-api.md` to `cli.md`, `limitations.md` to `packages.md`, `troubleshooting.md` and `security-model.md`). The strict build checked each.
- **The changelog page** renders `CHANGELOG.md` through the snippet (`0.1.0a7`'s section is in the HTML).

## 3. The README against the pages (EXECUTED by reading)

They agree on:
- **Versions:** CPython 3.15 (the pages say 3.15.0), numpy 2.5.2, pandas 3.0.6, scipy 1.18.1, scikit-learn 1.9.1, statsmodels 0.15.0, matplotlib 3.11.2, lxml 6.1.3; status 0.1.0, which is `__version__` and the CHANGELOG's unreleased section.
- **Defaults:** 1 GiB, 60 s, 16 MiB per stream, 1,024 open files, fuel opt-in, `None` for no limit (`how-to/limits.md`, `reference/defaults-and-limits.md`, `explanation/security-model.md`, `how-to/troubleshooting.md`).
- **The `-V` sentence:** the same text in the README, `reference/packages.md` and `reference/limitations.md`; "1.3 to 2.3 times" matches `explanation/performance-and-size.md`.
- **Install:** `pip install wasi-python`, `uv add wasi-python`, `pip install --no-deps wasi-python` with `wasi_python.artifacts()`; "importing `wasi_python` never loads wasmtime" (`get-started/install.md`, `reference/artifacts.md`).
- **The five-minute path:** the README's `run` example and the CLI's JSON line are the same text as `index.md` and `get-started/first-run.md`.
- **Patches:** 27 in the README, 27 on `explanation/pinned-releases-and-patches.md`, 27 patch files under `recipes/patches/`.
- **Packages:** "about 40 pure-Python packages" against the packages page: seven named first, thirty plus seaborn and reportlab in the table, and formulaic, interface-meta and wrapt in the statsmodels row, which makes 42, the CHANGELOG's number (N3).

They disagree on two things a reader would hit: the wasmer engines (L1), and what "the tutorial" covers (L2). And the generated API page, written from the runner's docstrings, still sends readers to README sections that no longer exist (M1).

## 4. Leftovers (EXECUTED: `git grep` at `2f218a29`, outside decisions.md, research, reviews and specifications)

- **`context/questions-for-the-owner.md`**: twelve files name it.
  - `CHANGELOG.md:23` says it is deleted. That is the record of the deletion, not a pointer.
  - `context/constitution.md:6` is the dated amendment line of 2026-10-17. A dated record; left.
  - **Ten live pointers** under `context/upstream/`, each "question 80 in `context/questions-for-the-owner.md`" (L4): `12-wasmtime-py-on-wasmtime-49-0-3/facts.md:9`, `20-wasmtime-preview1-write-on-a-read-descriptor/facts.md:13`, and line 9 of `patches/libxml2-2.15.4/0001-xmlio-without-dup-on-wasi.md`, `patches/matplotlib-3.11.2/0002-qhull-without-devnull-on-wasi.md`, `patches/networkx-3.7/0001-graph-atlas-from-a-zip.md`, `patches/pandas-3.0.6/0001-styler-templates-from-a-zip.md`, `patches/regex-2026.9.29/0001-callback-signatures.md`, `patches/regex-2026.9.29/0002-timeout-ticks.md`, `patches/scikit_learn-1.9.1/0001-html-repr-styles-from-a-zip.md` and `patches/statsmodels-0.15.0/0001-datasets-from-a-zip.md`. Question 80's answer is in `context/decisions.md` ("80, answered"); it had left the questions file before 122 deleted it.
- **The advisory draft**: one reference, `context/upstream/README.md:29`, the dated row the lane wrote. No code, test, workflow or page names it.
- **The old README's sections**: five pointers in `src/` (M1).

## 5. docs.yml (EXECUTED by reading; settings READ through `gh api`)

- **Triggers.** `push` with `tags: ["v*"]` runs on the `v0.1.0` tag; the deploy job's `if` (`startsWith(github.ref, 'refs/tags/v')`) lets it deploy.
- **The environment.** `github-pages` has custom deployment policies: `main` (branch) and `v*` (tag). The Pages site's `build_type` is `workflow`, at `https://claygendron.github.io/wasi_python/`.
- **The lock.** `UV_LOCKED: "1"` makes every `uv run` a locked sync; `uv run --group docs` then installs the docs group from `uv.lock`. EXECUTED in scratch with `UV_LOCKED=1`: the lock is current.
- **The generated-page checks exist.** `tests/harness/api.py` and `tests/harness/cli_doc.py` each take `--check` (a mutually exclusive mode beside `--write`), and both exit 0 at the tip.
- **The upload path.** `actions/upload-pages-artifact` uploads `site`; `mkdocs.yml` sets no `site_dir`, so MkDocs writes `site/`. They match. `site/` is git-ignored.
- **Permissions.** The workflow grants nothing at the top; the build job reads contents; the deploy job has `pages: write` and `id-token: write`, which `deploy-pages` needs. The deploy's concurrency group is on the deploy job only.
- **The main tree's `.venv`** (READ only): no `platformdirs` and no `mkdocs` in its site-packages, so the docs group was not installed there before the acceptance.

The workflow should succeed on the tag. Its action pins I did not re-read; 122's build review did.

## Findings

1. **M1 (Medium, 122: the generated API page and the runner's own text): four public places still send a reader to README sections that the short README no longer has.**
   - `docs/reference/python-api.md:619` and `:729`, generated from `src/wasi_python/tools.py:24` and `:194`: "(README.md, "The tool protocol")". That section is now the site's `reference/tool-protocol.md`.
   - `src/wasi_python/_tool_schema.py:187`, an error message `tool()` raises: "rename it, as the README shows". The renaming is now on `how-to/tools.md:229` and `reference/tool-protocol.md:162`.
   - `src/wasi_python/__init__.py:23`, what `help(wasi_python)` prints: "README.md's "API reference" lists every public name and the promise each release keeps". That is now `reference/python-api.md` and `reference/support-and-versioning.md`.
   - `src/wasi_python/runner.py:148`, internal: "the README's *Mounts*" (now `how-to/mounts.md`).
   - **Failure:** a reader of the published API page, of `help()`, or of an error, follows a pointer to a section that is gone. Nothing in the judge sees it: the scans forbid specification numbers and `context/` paths on public pages, not README section names, and `test_generated_pages_are_current` only checks the page equals the docstrings.
   - **Fix (122's builder, a `src/` change):** name the site's pages in words (the tool protocol reference, the Python API reference, the mounts guide), then `uv run python tests/harness/api.py --write`. Because it touches `src/`, it cannot ride this acceptance (rule 6b). The lane chooses: fold it in before the tag if another acceptance and dry run run anyway, or record it as 0.1.1's first item in `context/roadmap.md`. It does not block the landing: no behaviour changes and the judge is unaffected.
2. **L1 (Low, 122's README and 123's embed page): the wasmer line is wrong for Cranelift.**
   - `README.md` Hosts: "wasmer 6 or later on LLVM, V8 or Cranelift". The research (`context/research/2026-10-16-cpp-exceptions-and-wasi-hosts.md:180`) says LLVM since 6.0, V8 since 6.1, Cranelift since 7.0, and Singlepass not at all. The README drops both the 7 and "not Singlepass".
   - `docs/how-to/embed-from-other-languages.md:95` keeps the old wording, "wasmer 6 or later on LLVM, V8 or Cranelift 7 or later", which reads as a Cranelift version.
   - **Failure:** a reader on wasmer 6 with Cranelift is told it runs, and it does not.
   - **Fix:** "wasmer 6 or later on LLVM or V8, or 7 or later on Cranelift (not Singlepass)" in both. The README part may follow the dry run (rule 6b); a `docs/` change is not in rule 6b's list, so it waits for the next dry run or goes with M1.
3. **L2 (Low, 122's README): "The tutorial walks through each" covers none of the three.**
   - `README.md`, after the quickstart: `Session`, `run_async` and `run(tools=[…])`, then "[The tutorial](…/get-started/first-run/) walks through each". `first-run.md` covers the command, `run`, what the guest cannot do, a private root and the result. None of the three.
   - **Fix (README only, may follow the dry run):** link each to its guide: `how-to/sessions/`, `how-to/async/`, `how-to/tools/`.
4. **L3 (Low, 122's `mkdocs.yml`): the file's own comment gives the command that turns the judge red.**
   - `mkdocs.yml:1` says the site is "built with `uv run --group docs mkdocs build --strict`". 122's specification (Work, "The site builds in its own environment") says that, run in a tree, installs platformdirs into `.venv`, which stays, and the judge then reports "steered from outside the judge: plugin platformdirs". No public page says to build in its own environment; `docs/contributing/` never mentions the site build.
   - **Fix:** the comment gives `UV_PROJECT_ENVIRONMENT=build/docs-venv uv run --group docs mkdocs build --strict`, and `uv sync --locked` to undo a build made in `.venv`. Optionally one line in `docs/contributing/building.md`. Not before the tag.
5. **L4 (Low, context only): ten upstream drafts point at the deleted questions file.**
   - The ten files are in section 4. Each says "question 80 in `context/questions-for-the-owner.md`".
   - **Fix (the lane, context only):** "question 80 in `context/decisions.md`" in each. It may follow the dry run.
6. **N1:** the docs workflow deploys from the tag at the same time `release.yml` runs on it. If the release run fails, the site already describes a 0.1.0 that is not on PyPI. A `workflow_dispatch` from the next tag replaces it. Nothing to fix.
7. **N2:** the changelog page shows `CHANGELOG.md` whole, specification numbers and `context/` paths included. 123's Decision 6 chose this; the scans read `docs/reference/changelog.md`, which holds only the snippet line.
8. **N3:** the README's "about 40" and the packages page's "thirty … plus seaborn and reportlab" are both true (42 in all), but no page states the total. A reader who counts may wonder.

## Verdict

**Lands.** The rebase is clean: each entry on the wave is its reviewed tip, and the lane's commit is context only. The combined site builds strictly; its nav and its pages agree; every README link and every cross-link between 122's and 123's pages resolves; `docs.yml` should deploy on the tag. M1 is a documentation defect in `src/` that the judge cannot see. It needs a `src/` change, so it goes before the tag only with another acceptance, or into 0.1.1 by a roadmap line. L1 to L4 are wording, and the README and `context/` parts may follow the dry run.

## Disposition (for the lane; 122's builder where named)

1. M1: the lane decides before the tag. Either 122's builder fixes the four docstrings and the message and regenerates the page, with the next acceptance and dry run, or the lane writes 0.1.1's first roadmap item naming the five lines.
2. L1 and L2: README lines by the lane or 122's builder; may follow the dry run. L1's page line waits for the next run that covers `docs/`.
3. L3: with M1, or in 0.1.1.
4. L4: the lane, context only, any time.

In one line: wave 13 is the two reviewed entries exactly, its site builds strictly with every link resolving, and it lands; the runner's text still points at the old README's sections (M1).
