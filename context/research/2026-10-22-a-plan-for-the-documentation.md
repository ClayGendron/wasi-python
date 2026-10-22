# A plan for the documentation: a short README, a docs site, a clean tree before 0.1.0

- **Status:** proposal, 2026-10-22, evening. Written for the owner. Nothing in the repository
  was changed but this file. No judge, build or CI run was started. No third-party host was
  contacted.
- **Owner:** Clay Gendron
- **Stands on:** the owner's request (the README cut to what it is, a five-minute setup and the
  details a developer wants; everything else on a GitHub-hosted docs site; a cleaner repository
  before 0.1.0, no history rewrite); five read-only reports by other agents, folded in here (a
  README audit, the judge's dependence on documents, a `context/` audit, tooling and deployment,
  documentation systems and seven exemplar repositories); AGENTS.md; `context/README.md`;
  `constitution.md`.
- **Evidence labels:** EXECUTED (a grep, `wc` or `git ls-files` run tonight on main `11804405`),
  READ (a file in this repository or one of the five reports), INFERRED (reasoning).

## 1. The recommendation in brief

Cut the README to about 150 lines in the standard-readme shape. Move the generated API block to a
file under `docs/`. Delete the files no code and no rule needs. Do that as one specification with
one judge change, one release acceptance and one dry run, then tag 0.1.0. Build the site in the
Diátaxis shape with MkDocs after the tag, for 0.1.1, deploying from the tag so the site always
matches the wheel. `context/` stays the agents' memory and is never mirrored on the site.

One line: one cheap judge change and a short README before the tag; the site right after.

## 2. The system

**Diátaxis** sorts documentation into four kinds by the reader's need: a *tutorial* (a lesson
that must work), a *how-to guide* (a recipe for one goal), *reference* (what the machinery is),
and *explanation* (why). Its rules that matter here: never create an empty quadrant; start from
what exists and improve one page at a time; a page serves one need (READ, report 5).

It fits because the README is already all four kinds in one file (EXECUTED, `wc -l`: 3,753
lines), with the hard facts (limits, the `-V` sentence, the artifact table) sitting between
tutorials. Three small complements: Google's developer style for sentences, which agrees with
AGENTS.md "Explaining things"; the Good Docs Project templates as page skeletons; docs-as-code
(a page changes with the code, CI builds with warnings as errors, snippets are tested). The
closest exemplars are Monty (sandboxed Python; one Limitations page per area) and Pyodide (a
`wasm-constraints` page; a pinned list of documented API names so drift fails CI) (READ, reports
4 and 5).

**How `context/` relates.** `context/` is the agents' working memory, written in the project's
internal vocabulary (spec numbers, questions, waves). The site is written for users, embedders
and contributors and never mirrors it. Durable knowledge flows out, rewritten: the constitution
becomes one abridged "Project principles" page; the decisions that shape the product (fuel not
time, few pinned releases, embedder-neutral, nothing writable by default) become a few
design-decision pages; research memos feed the explanation pages and one dated "Performance and
size" page (INFERRED from report 5).

**Public-page rules.** A page under `docs/` names no specification, question, decision or wave
number, no review, and no name from `context/embedders.txt`. This is the documents' form of
"code speaks for itself": the reason in words, the number in `context/`. Today neither scan
reaches a `docs/` tree: the citation scan reads `tests/`, `.github/workflows/`, `scripts/` and
`release/` (READ, `tests/harness/scan.py`, `context_citation_files`), and the embedder scan reads
`recipes`, `scripts`, `src`, `tests`, `fixtures` (READ, `tests/checks/test_rules.py`,
`CODE_DIRS`). Decision: `docs/` falls under both, with a Markdown-aware rule (a code span or a
link to `context/` is also a hit). The README too: it is a public page. A page may link to a file
on GitHub (`src/…`, `recipes/…`); it may not link into `context/`.

## 3. The new README

Shape (standard-readme): title and one-line description, a paragraph on what it is and who it is
for, What you get, Quickstart, Safe by default, What runs and what does not, Hosts, API
stability, Verifying a download, Building from source, Contributing and security, Licences.
About 120 to 180 lines. Every link absolute (`https://github.com/claygendron/wasi_python/…`,
`https://claygendron.github.io/wasi_python/…`), because PyPI shows the README as the long
description and relative links break there (READ, report 2; `pyproject.toml` `readme =
"README.md"`).

**What must stay, because a check reads it** (READ, reports 1 and 2; EXECUTED, the lines):

1. FreeType's credit sentence, verbatim (README line 534; `test_rules.py` with
   `scan.py` `freetype`): the README is the wheel's documentation, which FreeType's licence
   names.
2. `upstream patches carried: 27` (line 41; the count under `recipes/patches/`).
3. The guest's `-V` sentence, verbatim (line 59).
4. At least one `default integer is 32-bit` phrase agreeing with the guest
   (`test_v1_3_data_stack.py`); the `-V` sentence satisfies it.
5. No heading containing "question", no TODO or open-question line.
6. No code span or fenced line naming an internal module or constant (`api.readme_hits`).
7. Exactly one generated API block between `api.py`'s markers, byte-equal to the live surface,
   **unless** `api.py`'s default path moves (section 5).
8. The token `README.md` as a `closes_with` closer: 266 entries in `tests/known_gaps.toml`, 294
   across `tests/upstream/*.toml` (EXECUTED). Only existence is checked. The README keeps a
   short "What runs and what does not" so the token stays honest until the entries retarget.

**Stale facts to fix** (READ, report 1): status "alpha, 0.1.0a1 … next alpha moves to CPython
3.15.0 and wasi-sdk 33" (the line is at 3.15 and wasi-sdk 34); "twenty-three carried patches"
at lines 57 and 683 against 27 at line 41; "use 0.1.0a1 once on PyPI"; "Releases are alpha
builds"; the Scope section lists scipy, seaborn and reportlab as out, and all ship; "Next" names
one done item; the promise of Rust and Go examples with only a TypeScript one. Also
`pyproject.toml`: classifier "3 - Alpha", a description naming only numpy, pandas and
matplotlib, no Documentation URL (READ).

**Skeleton** (commands verified in README and `pyproject.toml`, READ):

```
# wasi-python
CPython 3.15 for wasm32-wasip1 with numpy, pandas, scipy, scikit-learn, statsmodels,
matplotlib and lxml compiled in. One static binary; no browser, no JavaScript.
[what it is: 1 paragraph; who: run code you did not write, a model's included]
[Docs · Changelog · Security · Licence]  Status: 0.1.0, Apache-2.0.
## What you get          (4 rows: python.wasm, python-snapshot.wasm, python-stdlib.zip, MANIFEST)
## Quickstart (5 minutes)
  pip install wasi-python     # or: uv add wasi-python
  from wasi_python import run, Grant
  done = run(["-c", "import pandas as pd; print(pd.Series([1, 2, 3]).sum())"])
  done.exit_code, done.stdout                                # (0, b'6\n')
  run([...], grants=[Grant("data", "/data"), Grant("/tmp/out", "/out", writable=True)])
  $ wasi-python run -- -c "print(1)"                        # one JSON line
  [one sentence each: Session, run_async, tools=; link to the guides]
## Safe by default       (nothing writable unless granted; 1 GiB, 60 s, 16 MiB/stream, 1,024
                          open files; fuel; what is NOT protected → security model page)
## What runs, and what does not   (headline versions; the -V sentence verbatim; no threads,
                          processes, network; → Limitations page)
## Hosts                 (wasmtime 47+, WasmEdge 0.16+ by default; wazero, wasmer, Node with a
                          switch; embedding: pip install --no-deps wasi-python; artifacts())
## API stability         (public API = __all__ + the command + two env vars; 0.MINOR.PATCH;
                          two minor releases of deprecation before removal) → reference
## Verifying a download  (the gh attestation verify line, verbatim)
## Building from source  (scripts/00_download.sh; scripts/build.sh; "upstream patches
                          carried: 27") → building page
## Contributing · Security · Changelog   (links; AGENTS.md is the contributor's rule book)
## Licences              (Apache-2.0; FreeType's sentence verbatim; dataset terms → page)
```

## 4. The site

**Tree** (reports 1, 4 and 5 merged; T tutorial, H how-to, R reference, E explanation; U user,
M embedder, C contributor; **first cut** ships with 0.1.1, *later* follows as pages earn their
place). No quadrant is empty in the first cut (INFERRED).

- **Home**: what it is, a three-line example, three doors (use it, embed it, build it). First cut.
- **Get started**: Install [H, U]; Your first sandboxed run, CLI then `run()` [T, U]; Analyse a
  CSV through a grant [T, U]. First cut. *Later:* Embed `python.wasm` in your own host [T, M].
- **How-to guides** [H]: Give the guest a folder (grants, writable, `root=`); Mount data
  (mounts, the provider protocol, Windows); Keep state with a Session; Limit a run (fuel, memory,
  deadline, cancel); Call from async code; Expose host tools (LangChain and MCP adapters); Save a
  plot; Verify a release download; Troubleshooting (keyed by error text). First cut. *Later:*
  Read Excel, PDF and XML; Embed from Node, Rust, Go (one page each, M).
- **Reference** [R]: `wasi-python` command (generated from `cli._parser()`); Python API
  (generated by `api.py`); Results, exit codes and errors; Defaults and limits; Guest filesystem
  layout; Tool protocol wire format (M); Included packages and versions (generated from
  `MANIFEST` and `tests/upstream/packages.toml`); Limitations and unsupported features (Pyodide's
  model: the `-V` facts, no threads, `_ctypes`, `mmap`, sockets, `_ssl`, `_zstd`, `scipy.odr`,
  the 32-bit default integer, SQLite locks, Windows differences); Support matrix (host OS,
  wasmtime version, Python line, the exception-handling requirement) and versioning; Artifact
  set and `MANIFEST`; Changelog (included from `CHANGELOG.md`). First cut, all. *Later:* Guest
  ABI (`_initialize`, `run`, the host door) (M); Glossary.
- **Explanation** [E]: Why WASI and not Emscripten; How it works (static builtins, a reactor, a
  Wizer snapshot); Security model (what is enforced, what is not, disclosure, what counts as a
  vulnerability; `SECURITY.md` links here); Fuel: counting operations, not time; Performance and
  size (dated). First cut. *Later:* Sessions and why they are bounded; Few pinned releases,
  patches few and temporary; Design decisions (curated, ADR-shaped); Project principles.
- **Contributing** [C]: Build from pinned sources (README "How it is built" moved); Your first
  change: run the judge [T]; The judge: tiers, the ratchet, known gaps [E+R]; Review and landing
  [E]; Release process [H] (README "Releasing" moved); Carry an upstream patch [H]. First cut:
  the first three; the rest *later*. The pages point at AGENTS.md and `context/README.md`; they
  do not copy them.

**Tooling.** Markdown plus `mkdocs.yml`, built with MkDocs and Material in the subset Zensical
reads unchanged. Exact pins in a `docs` dependency group: `mkdocs==1.6.1`,
`mkdocs-material==9.7.7` (READ, report 4: Material is in maintenance until May 2027; Zensical
0.0.71 is alpha and reads `mkdocs.yml` as is). No mkdocstrings: `tests/harness/api.py` already
generates and checks the API reference, so `docs/reference/python-api.md` is its output
(INFERRED; fewer pins). No `mike` versioning: deploy from the tag, so the site is the wheel's.
Built-in search. `uv run --group docs mkdocs build --strict` validates every internal link and
anchor. External links: `lychee` on a schedule only, upstream download hosts excluded (the
no-probing rule). Sphinx is not needed and costs reST friction and autodoc's import-time
behaviour (READ, report 4). Zensical's alpha: not yet; the move is one command later.

**Generated reference.** `api.py --write` gains a default output of
`docs/reference/python-api.md` (the markers stay; `test_v1_4_public_api.py` reads the new path).
A sibling generator renders `cli._parser()` into `docs/reference/cli.md` with the same markers
and a drift check; 12 of the parser's 14 options have no `help=` today (EXECUTED), so the
generator's first run adds them, a `src/` change. The packages table is rendered from `MANIFEST`
and `packages.toml`. One check, "generated pages are current", fails when any of the three
drifts (uv's `check-generated-files` pattern; READ, report 4).

**Tested snippets.** Quickstart and how-to code lives as files under `docs/examples/`, included
into pages with its expected output; a slow-tier guest job runs and compares them (Pydantic's
`#>` and wasmtime's `include` patterns; READ, report 5). Third specification (section 7).

**Deployment.** A new `.github/workflows/docs.yml`, separate from `release.yml`. `pull_request`
and `push` to `main` build only (`--strict`, drift checks); a `v*` tag and `workflow_dispatch`
build and deploy. `permissions: {}` at the top; the build job `contents: read`; the deploy job
`pages: write`, `id-token: write`, environment `github-pages`; concurrency group `pages`
without cancel. Actions pinned by commit with the release named, as `set-cache.yml` does:
`actions/checkout` and `astral-sh/setup-uv` at the SHAs already in use, plus
`actions/configure-pages` v6.0.0, `actions/upload-pages-artifact` v5.0.0 and
`actions/deploy-pages` v5.0.1 at the SHAs report 4 lists (READ; the builder re-reads each with
`gh api`). The judge already checks every workflow's pins and citations (READ, report 4). A docs
run is not a release run, so the three-live-runs budget is untouched (INFERRED).

**What the owner clicks.** Settings → Pages → Source: "GitHub Actions" (Pages is not enabled;
READ, report 3). Then the domain: `claygendron.github.io/wasi_python` needs no DNS;
`wasipython.dev` is already `pyproject.toml`'s Homepage (READ), so if it is free the owner adds
it under Pages → Custom domain, sets the DNS records GitHub shows and ticks "Enforce HTTPS"; an
Actions deploy needs no `CNAME` file. Links are written to the final address, so this decision
comes first.

## 5. Repository cleanup before 0.1.0

The judge cites exactly 27 `context/` paths: 19 specifications, 2 reviews, 2 research memos, 3
upstream notes, `context/upstream/patches`, and `roadmap.md` plus `questions-for-the-owner.md`
through closers (EXECUTED, a grep of `tests/`). Nothing else under `context/` is read by code
except `progress/`, `embedders.txt`, `prior_art/README.md`, `reviews/README.md`'s rubric rows,
and the shape of every specification and landed-review citation (READ, report 2). "Delete" below
means delete from the tree; git history keeps it, which the owner has accepted. "Archive" means
`context/archive/`, used only where a file is still cited.

| Path | Action | Reason | What changes first |
|---|---|---|---|
| `context/questions-for-the-owner.md` | delete | "Open: None"; its one paragraph is the owner's product direction, which names the private consumer's path (READ) | retarget its 6 closers (`known_gaps.toml` 41, 65; `numpy.toml` 117, 122, 200, 256) to `context/roadmap.md` (question 89 is answered; EXECUTED, `decisions.md` names it); move the direction paragraph, without the path, to `decisions.md`; drop lines 24 and 43 to 48 of `context/README.md` (judge change) |
| `context/handoff.md` | keep | the lane's state between sessions; no code reads it; it is agent memory | nothing; the lane keeps it to one screen |
| `context/embedders.txt` | keep | judge data, in the judge hash (READ, `paths.py`) | nothing |
| research evidence folders (55 folders, about 1,746 files, 14 MB; 20 have no memo; EXECUTED) | delete all but the memos | raw probes, logs and the wasmtime advisory dump with about 150 third-party emails (READ, report 3); one judge path points into one: `tests/checks/test_rules.py:701` reads `2026-10-18-wasmtime-49-advisories/advisories/GHSA-96f6-r43r-8c24.json` and `GHSA-m9f7-9w4p-gv38.json` (the runner's two wasmtime guards; EXECUTED, the lane's check of this memo), so those two records move to `tests/data/` with the path in that check changed (a judge change in the same specification) or stay where they are; every other evidence file has no judge reader | the memos' relative links to their folders go stale; a one-line note at the top of `research/`'s README says evidence is in history before 2026-10-23 (context only) |
| superseded memos (`a-principal-engineers-direction`, `market-research-use-cases`, `a-rust-core-with-js-and-python-wrappers` and its spike) | keep | `research/` is append-only by rule; they are cheap and dated (READ, `context/README.md`) | nothing |
| `context/reviews/`: 12 wave integrations, 6 alpha security reviews (a2 to a7 and the a5 addendum), per-spec reviews | keep for 0.1.0 | every landed specification's landing notes must cite an existing review (READ, `scan.py` `landed_review_errors`); the 0.1.0 security and structural reviews are required by the release check | after the tag: a specification that archives landed specifications and their reviews together and teaches the scans the archive path |
| `context/specifications/` (109, all landed) | keep for 0.1.0 | 19 are judge-cited; the shape and review checks read the folder; untracked ones dirty the tree (READ, `paths.py` `DIRTY_UNTRACKED`) | same post-tag specification |
| `context/roadmap.md` (300 lines) | trim after the tag | 14 closers and `shards.py` need it to exist; "Where 0.1.0 stands" is history | the trim is context only; move the 0.1.0 history into `decisions.md` or delete it |
| `context/upstream/advisories/GHSA-draft-0.1.0a3.md` | file it, then delete | an unpublished advisory for a sandbox escape in a1 to a3, in a public tree; a3 is on PyPI (READ, report 2) | the owner creates the GitHub draft advisory from the text, yanks a3, publishes; then the file goes |
| personal paths (174 files under `context/`; EXECUTED) | leave in records; delete with the evidence folders | records are not edited; the paths are not secrets | a scan rule for new `docs/` and README pages only |
| the private consumer's name | leave in records; never on a public page | it is judge data in `embedders.txt`; the questions file's path reference goes with the file | the embedder scan extends to `docs/` and README |
| the README's internal references ("spec NNN", "decision 34", "question 103") | delete with the cut | public page rule | the rewrite |
| `SECURITY.md` "while the project is in alpha" | reword | stale at 0.1.0 (READ) | context-class edit, no check reads it |
| `context/prior_art/` clones report 4 refreshed | keep | all four already have licence rows (READ) | the memo that cites them records the commit |

**The judge changes, together.** Retargeting six closers (`known_gaps.toml`, `numpy.toml`),
moving `api.py`'s default output and the public-API check's path, the `pyproject.toml` fixes
(classifier, description, Documentation URL), and the scans' reach into `docs/` and README. All
sit in the judge hash (READ, `paths.py` `JUDGE_PATHS`), so each needs `--accept-judge`. The
`closer` field is one that `sameness.py` compares (READ, report 2), so a retarget shows as a
difference the lane must name. They are one specification, not several: one hash change, one
acceptance, one dry run (INFERRED). The 560 README closers stay as they are for 0.1.0; the site
specification retargets them to `docs/reference/limitations.md` and widens
`test_rules.py`'s closer rule to allow `docs/` (a second, later judge change).

## 6. Sequencing against the 0.1.0 tag

Rule 6b: after a dry run, only `context/`, `CHANGELOG.md` and `README.md` may change without a
new acceptance and dry run; the acceptance took 1 h 23 min to 1 h 32 min at `-n 6` and a dry run
about the same on CI (READ, `handoff.md`, the last three commits) (EXECUTED, `git log`).

- **A. The minimum before the tag, one judge change.** One specification: the README cut with the
  API block moved to `docs/reference/python-api.md` (a file, no site yet), the six closers
  retargeted and the questions file deleted, the evidence folders deleted, `pyproject.toml`
  fixed, `SECURITY.md` reworded, the scans extended. Build, a fresh review, the lane's release
  acceptance, one dry run, the tag. Cost: about half a day of agent work and 3 to 4 hours of
  machine time (INFERRED). 0.1.0's PyPI page shows the short README. The site follows in 0.1.1.
  **Recommended.**
- **A-lite. README and context only, no judge change.** The README is cut but keeps the 840-line
  API block; the questions file stays. Fast tier only, no new dry run. Legal under the rules,
  but the PyPI page carries 840 generated lines and the questions file waits (INFERRED).
- **B. README, site and cleanup all before the tag.** Three specifications, two judge changes, a
  new workflow, Pages enabled, CLI help text in `src/`. Days of agent work, at least two
  acceptances and dry runs; every slip delays a release that has passed three (INFERRED).
- **C. Tag now; docs in 0.1.1.** Zero cost now. 0.1.0's PyPI page is the 3,753-line README with
  stale status lines, against the owner's "clean the repo before 0.1.0".

Option A matches the owner's words at the cost of one cycle. PyPI shows the tagged commit's
README as the long description (READ, `pyproject.toml`): the cut belongs before the tag, the
site need not.

## 7. Process

Three specifications, in order (INFERRED from AGENTS.md's classes):

1. **The README, the closers and the tree** (option A). Kind: judge change (`tests/`,
   `pyproject.toml`); not structural, not build-class. Pre-build review optional; a fresh agent's
   build review and the builder's dispatched dry run required. The builder keeps every check of
   section 3 green by node id.
2. **The site.** Kind: judge change (the `docs` group in `pyproject.toml`; the 560 closers
   retargeted; the closer rule widened; the generated-pages check; the CLI generator) and a
   `src/` change (the `help=` strings), so a build review is required. `docs.yml` is not the
   release workflow, so not build-class; its reviewer still reads permissions and pins. A
   pre-build review of the page tree is cheap and fixes the vocabulary.
3. **Tested snippets and the archive.** The slow-tier job for `docs/examples/`; landed
   specifications archived with their reviews, the scans taught the path; the roadmap trim.

Then three habits. A specification that changes behaviour a page describes changes the page in
the same branch, and its reviewer reads both. The generated-pages check holds `api.py`, the CLI
and the packages table. AGENTS.md's "All project knowledge lives in this repo under `context/`"
becomes "under `context/` (the agents' memory) and `docs/` (what we tell users)", with the
public-page rule beside "Code speaks for itself". The five reports are folded in here and need
not be kept.

## 8. Decisions for the owner

1. Sequence: option A (one judge change, then the tag), A-lite, B or C?
2. Domain: `claygendron.github.io/wasi_python`, or `wasipython.dev` (today the Homepage URL)
   pointed at Pages? Is anything already served at `wasipython.dev`?
3. Does `context/` stay in the public repository as is, or does it move to a private
   repository after 0.1.0 (the specifications, reviews and research would then be mirrored
   only as the judge needs)?
4. History-type files: delete from the tree (git keeps them), or `context/archive/`?
5. The GHSA draft: file it in GitHub's advisory form now, yank 0.1.0a3 and publish, then delete
   the draft; or delete the draft without filing?
6. The private consumer's name: leave it where it already stands in dated records, with the
   scan extended to every public page; or also reword the records that mention it?
7. The 560 README closers: retarget them with the site (a second judge change in 0.1.1), or
   leave `README.md` as the token for good?
8. Tooling: MkDocs with Material now and Zensical later, or Zensical's alpha from the start?

One line: cut the README, move the API block, delete what nothing reads, one acceptance and one
dry run, tag; then build the Diátaxis site for 0.1.1 and deploy it from each tag.
