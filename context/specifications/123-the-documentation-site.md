# 123: The documentation site

- **Status:** **built 2026-10-22 on `spec/123-the-documentation-site`, base main `fb8343cd`;
  awaiting review** (Landing notes). Drafted 2026-10-22; no pre-build review (neither touches `src/` or the build
  recipe; AGENTS.md rule 8). Built in parallel with 122 (a short README and a clean tree), on
  disjoint files, for the one wave before the 0.1.0 tag (`decisions.md`, "The documentation before
  the 0.1.0 tag, within a day"). No builder dispatches a branch run or loops on the fast tier: the
  judge runs once, as the lane's release acceptance on the wave's tip, then the dry run on main.
- **Date:** 2026-10-22
- **Owner:** Clay Gendron
- **Kind:** **context only**, parallel-safe. It writes Markdown pages under `docs/` and nothing
  else: no `src/`, no `tests/`, no `scripts/`, `recipes/`, `downloads/SHA256SUMS` or workflow, no
  `pyproject.toml`. Not a judge change (the judge hash, `tests/harness/paths.py:277-287`, holds no
  `docs/` path); not build-class; not structural. Its pages are read by two scans once 122 lands
  (122's Decision 6), so a page that breaks the public-page rule fails the judge on the wave's tip.
- **Depends on:** 122, drafted beside it, for the scaffold (`mkdocs.yml`, the `docs` dependency
  group, `docs.yml`) and the three pages it owns (`docs/reference/python-api.md`, `cli.md`,
  `limitations.md`), which this specification's pages link to. The lane rebases this specification
  first and 122 onto it (For the lane). Landed and unchanged: every specification whose behaviour a
  page describes; the pages describe the product at main `bb2235f2` and change nothing.
- **Research it stands on:** `../research/2026-10-22-a-plan-for-the-documentation.md` (section 2,
  the system; section 4, the tree and the public-page rules; section 7, the habits) and the five
  reports it folds in: the README's section map by line (every line range below is from it,
  re-read on main `bb2235f2`, READ), the `context/` audit's list of sources per topic, and the
  systems report (Diátaxis, Google's developer style, the Good Docs templates; the exemplars
  Pyodide's `wasm-constraints` page and Monty's limitations pages; uv's and Pydantic's MkDocs
  trees). The owner's decisions of 2026-10-22 (`../decisions.md`, the newest entry).

## The problem

Everything a user, an embedder or a contributor needs is in one 3,753-line README, written in the
project's internal vocabulary (specification, decision, question and wave numbers; review names;
`context/` paths), with the facts a check reads sitting between tutorials. 122 cuts the README to
about 150 lines. The rest needs a home that outside readers can navigate: a site, organised by the
reader's need (Diátaxis: a *tutorial* is a lesson that must work, a *how-to guide* a recipe for one
goal, *reference* what the machinery is, *explanation* why), served at the GitHub Pages default
address `https://claygendron.github.io/wasi_python/` (the owner, 2026-10-22; the GitHub owner is
`ClayGendron`, Pages hostnames are lower-case), built from the `v0.1.0` tag so the site is the
wheel's. The pages must be written within the day, so this specification gives each page its path,
its sources by README line range and `context/` file, its audience and whether it may ship thin.

## Decisions

### 1. The tree is Diátaxis's four kinds plus a contributor section; no empty quadrant

The nav (the exact list in Scope's shared contract; 122's `mkdocs.yml` names it) is Home, Get
started, How-to guides, Reference, Explanation, Contributing. Every page serves one need. A page
may ship **thin** (one screen: what it is, one example, a link to the reference) but never empty:
a page that would be a stub is omitted instead, from the "may omit" list only (Decision 4), so the
nav stays honest. The first cut ships every quadrant with at least two real pages.

### 2. The style: Google's developer style, second person, no internal vocabulary

Short sentences, one idea each, present tense, active voice, sentence-case headings, code font for
code (AGENTS.md "Explaining things" says the same). A term of art is defined on first use and in
the glossary. Benchmarks and sizes appear only on the dated performance page, never in a tutorial.

**The public-page rule**, held by 122's scans on every `*.md` under `docs/` (read whole: prose,
code spans and links alike; `tests/harness/scan.py:3362` lists the patterns): a page never writes

- "spec 025", "specification 025", "specs 023 and 043", or a bare "025's";
- "question 89"; "decision 34"; "wave 11"; a review by date or path, or the phrases "build
  review", "pre-build review", "security review", "integration review", "delta review",
  "re-review";
- the word "memo" (write "research note" or "a dated write-up");
- "§" or "constitution §4.1" (write "the project's principles");
- `context/…` in any form, a GitHub URL included (a contributor page links to AGENTS.md on GitHub,
  which maps the memory folder, and says "the project's memory folder" in words);
- a name from `context/embedders.txt`, or a personal path such as a home folder.

Where the README gave a fact's reason by a number, the page gives the reason in words. A page may
link to a code file on GitHub (`https://github.com/ClayGendron/wasi_python/blob/main/src/…`,
`recipes/…`, `scripts/…`, `AGENTS.md`, `SECURITY.md`, `CHANGELOG.md`).

### 3. Content comes from the README and `context/`, rewritten, not copied

The README's sections are the first source: the table in Design gives each page its line ranges on
main `bb2235f2`. The `context/` sources named per page are the second: the builder reads them for
the facts and the reasons, then writes for an outside reader. No `context/` text is pasted; the
constitution becomes one abridged principles page, the decisions that shape the product become
one design-decisions page, research notes feed the explanation pages. Facts the builder cannot
verify in the README or a cited source are left out, not guessed. The pages describe behaviour as
it is on main today; a page never promises what is reserved for 0.1.1.

### 4. The first cut, the thin pages, and the pages that may be omitted

Full in the first cut: Home; the three Get started pages but the embedding tutorial; grants,
mounts, sessions, limits, async, tools, troubleshooting, verify a download; results and errors,
defaults and limits, guest filesystem, tool protocol, packages, support and versioning, artifacts,
changelog; why WASI, how it works, security model, fuel; first change, building, review and
landing, release process, principles.

Thin is allowed for: `how-to/matplotlib.md`, `explanation/sessions.md`,
`explanation/pinned-releases-and-patches.md`, `explanation/performance-and-size.md`.

May be omitted if the day runs out (122's nav carries the same list; the lane deletes the nav line
of each page absent on this specification's tip): `get-started/embed-python-wasm.md`,
`how-to/excel-pdf-xml.md`, `reference/glossary.md`, `explanation/design-decisions.md`,
`contributing/adding-a-package.md`, `contributing/carrying-a-patch.md`. The builder tells the
lane which pages it omitted when it hands the branch over.

### 5. Snippets are inline for 0.1.0

Code blocks are written in the page, with the output the README shows for that example. Snippets
as files under `docs/examples/`, included into pages and run as a slow-tier guest job, are 0.1.1's
(Scope). Every example a page gives is one the README gives today, so its output is one the judge
has checked.

### 6. The changelog page includes `CHANGELOG.md` by a snippet

`docs/reference/changelog.md` is a heading and the line `--8<-- "CHANGELOG.md"` (pymdownx.snippets,
`base_path: ["."]`, `check_paths: true` in 122's `mkdocs.yml`), so the changelog is written once.
The CHANGELOG names specifications; it is a record read where it lives, not a page under `docs/`,
and the scans do not read it through the include (122's Decision 6).

## Intent

A user installs the wheel and runs a sandboxed program from the tutorial; an embedder finds the
artifact set, the hosts, the tool protocol and the limits; a contributor finds how to build, how
the judge works and how a change lands; and none of them meets a specification number, a review
name or a path into the project's memory.

## Design

The builder works page by page down this table, in order, so the full pages come first. Each row
gives the path, the kind (T tutorial, H how-to, R reference, E explanation; U user, M embedder, C
contributor), the README line ranges on main `bb2235f2` that feed it, the `context/` sources to
read, and what the page says.

### Home

| path | kind | README lines | `context/` sources | the page |
|---|---|---|---|---|
| `docs/index.md` | U, M, C | 1-18, 3747-3753 | — | What it is in one paragraph (CPython 3.15 for `wasm32-wasip1`, numpy, pandas, scipy, scikit-learn, statsmodels, matplotlib and lxml compiled in, one static binary, no browser, no JavaScript; built to run code you did not write, a model's included); the three-line `run()` example from 1033-1037 with its output; three doors: "Use it" (get-started/first-run.md), "Embed it" (how-to/embed-from-other-languages.md), "Build it" (contributing/building.md); why WASI and not a browser build in two sentences; a line on the licence. |

### Get started

| path | kind | README lines | `context/` sources | the page |
|---|---|---|---|---|
| `docs/get-started/install.md` | H, U | 1026-1048 | — | `pip install wasi-python` or `uv add wasi-python`; what comes with it (the artifact set, wasmtime-py 49); Python 3.11 or later; the embedder's `pip install --no-deps` and `wasi_python.artifacts()`; the `.cwasm` cache and `WASI_PYTHON_CACHE` in one paragraph (1099-1125). |
| `docs/get-started/first-run.md` | T, U | 1656-1664, 1026-1037, 1049-1059 | — | The command first (`wasi-python run -- -c "print(1)"` and its one JSON line), then `run()` with the pandas example and `done.exit_code, done.stdout`; what the guest can and cannot do by default (nothing writable; `open('x', 'w')` is `OSError`); `root=True` for a fresh private `/`; reading the result (link to reference/results-and-errors.md). |
| `docs/get-started/csv-through-a-grant.md` | T, U | 1146-1200, 1685-1701 | — | A folder with a CSV, `Grant("data", "/data")` read-only, a writable `Grant(out, "/out", writable=True)`, pandas reads and writes through them, the host reads the result; the same with `--grant` and `--grant-writable` on the command. |
| `docs/get-started/embed-python-wasm.md` (may omit) | T, M | 1039-1048, 1665-1716, 19-31 | `research/2026-10-16-cpp-exceptions-and-wasi-hosts.md` (the hosts' facts) | Load `python.wasm` in a host of your own: the preopens (the stdlib zip read-only at `/usr/local/lib`, matplotlib's data), argv and env, the exception-handling requirement, a wasmtime CLI line that works, then the TypeScript example in brief. |

### How-to guides

| path | kind | README lines | `context/` sources | the page |
|---|---|---|---|---|
| `docs/how-to/grants.md` | H, U | 1146-1318 | `research/2026-10-17-typed-grants.md` | Grants, `writable=True`, `root=` (True, a path, none), HOME and the import path, state across calls (`root=` a path keeps files; nothing else does), the stdlib zip never in a root. |
| `docs/how-to/mounts.md` | H, U, M | 1319-1655 | `research/2026-10-17-a-filesystem-provider-for-the-runner.md`, `research/2026-10-18-a-providers-oserror-carries-its-errno.md` | A mount and the provider protocol in the user's terms, writable mounts, the limits (1431-1450), **On Windows** (1616-1655) as its own heading (122's limitations page keeps the facts; this page keeps the recipe). |
| `docs/how-to/sessions.md` | H, U | 2275-2420 | `research/2026-10-18-bounded-sessions.md` | Open a `Session`, call it several times, what persists and what does not, close it; the bounds in one table with a link to explanation/sessions.md. |
| `docs/how-to/limits.md` | H, U | 1060-1100, 3479-3520 | `research/2026-10-18-a-cap-on-open-files.md`, `research/2026-10-18-a-per-run-budget-of-request-bytes.md` | Set memory, deadline, output bytes, fuel, open files; `None` for no limit; cancel; what `truncated` and `trapped` report; a link to reference/defaults-and-limits.md. |
| `docs/how-to/async.md` | H, U | 1717-1858 | `research/2026-10-18-async-host-functions.md` | `run_async`, cancellation, the FastAPI example, async host tools. |
| `docs/how-to/tools.md` | H, U, M | 1859-2135 | `research/2026-10-17-a-tool-protocol-over-the-door.md` | `run(tools=...)`, a tool's schema, the LangChain and MCP adapters, errors a tool raises; a link to reference/tool-protocol.md. |
| `docs/how-to/matplotlib.md` (thin allowed) | H, U | 427-500 | — | Save a plot as PNG, SVG or PDF into a writable grant; Agg only; fonts and the data folder; what matplotlib cannot do here in one line with a link to the limitations page. |
| `docs/how-to/excel-pdf-xml.md` (may omit) | H, U | 2461-2568, 537-655 | — | openpyxl and pandas' `.xlsx` reader, reportlab's PDF, lxml's XML and XSLT, each one example. |
| `docs/how-to/embed-from-other-languages.md` | H, M | 1656-1716, 656-679 | `research/2026-10-16-cpp-exceptions-and-wasi-hosts.md` | The command as a subprocess from any language, the JSON line and its keys, the TypeScript example, the hosts table (runs by default, with a switch, does not run), the stack-size note. |
| `docs/how-to/verify-a-download.md` | H, U, M | 1011-1025, 19-31 | `research/2026-10-18-the-release-ties-what-it-signs.md` | The `gh attestation verify` block verbatim, what it proves, `SHA256SUMS` without `gh`, the release assets' names. |
| `docs/how-to/troubleshooting.md` | H, U | 1049-1059, 1431-1450, 3479-3530, 1616-1655 | `tests/known_gaps.toml` (the reasons' wording only) | Keyed by what the user sees: `OSError` on a write (nothing is writable), out of fuel or past the deadline (`trapped`), `truncated`, `EMFILE`, `ModuleNotFoundError` for a package not in the set, `RecursionError`, a Windows path difference; each with the fix and a link. |

### Reference

| path | kind | README lines | `context/` sources | the page |
|---|---|---|---|---|
| `docs/reference/results-and-errors.md` | R, U | 1060-1100, 3565-3587, 1656-1664 | — | The result's fields (`exit_code`, `stdout`, `stderr`, `fuel_used`, `trapped`, `truncated`, the stats), the exceptions by type, the command's JSON keys and exit codes, `Errno`. |
| `docs/reference/defaults-and-limits.md` | R, U | 3479-3520, 1431-1450 | — | One table: each limit, its default, its unit, `None`'s meaning, where it is set (`run()`, the command, a `Session`, a mount). |
| `docs/reference/guest-filesystem.md` | R, U, M | 1049-1059, 1146-1160, 1260-1318, 1319-1340 | `research/2026-10-18-read-only-code-on-the-import-path.md` | What the guest sees at `/`, `/tmp`, `HOME`, `/usr/local/lib`, matplotlib's data, a grant's and a mount's paths; the import path order. |
| `docs/reference/tool-protocol.md` | R, M | 2136-2274 | `research/2026-10-17-a-tool-protocol-over-the-door.md` | The wire format: frames, kinds, the schema subset, `PROTOCOL` and its versioning. |
| `docs/reference/packages.md` | R, U | 2421-2460, 164-660 (each package's headline facts only) | `tests/upstream/packages.toml` (names and versions) | The headline versions, the table of the pure-Python families, one line per compiled package on what works and a link to the limitations page for what does not. Hand-written for 0.1.0 (generation is 0.1.1's). |
| `docs/reference/support-and-versioning.md` | R, U, M | 656-679, 2579-2607, 1026-1032 | `CHANGELOG.md` (the release line) | Host OS and wasmtime versions the wheel runs on, the exception-handling requirement, the Python line, the public surface and the `0.MINOR.PATCH` promise, what is not promised, the deprecation rule. |
| `docs/reference/artifacts.md` | R, M | 19-31, 680-700 | `release/` (names only), `research/2026-10-18-the-release-ties-what-it-signs.md` | The four artifacts, `MANIFEST`'s fields, `SHA256SUMS`, the wheel's layout, where the release puts them. |
| `docs/reference/glossary.md` (may omit) | R | — | — | fuel, grant, mount, root, door, reactor, snapshot, preopen, provider, session, the judge; one or two sentences each. |
| `docs/reference/changelog.md` | R | — | `CHANGELOG.md` | Decision 6. |

122 writes `docs/reference/python-api.md`, `docs/reference/cli.md` and
`docs/reference/limitations.md`; this specification's pages link to them by those paths and
write them no further.

### Explanation

| path | kind | README lines | `context/` sources | the page |
|---|---|---|---|---|
| `docs/explanation/why-wasi.md` | E | 3747-3753, 1-18 | `constitution.md` (the mission), `research/2026-10-16-cpp-exceptions-and-wasi-hosts.md` | Why WASI and not Emscripten or a browser build; a capability sandbox; one static binary; why the hosts need exception handling. |
| `docs/explanation/how-it-works.md` | E, M | 680-760, 127-162 | `research/2026-10-16-the-spike-that-proved-the-build.md`, `research/2026-10-16-making-the-snapshot-byte-reproducible.md` | Static builtin modules, the reactor and the host door, the Wizer snapshot and what it pre-imports (nothing), the stdlib zip, the `.cwasm` cache. |
| `docs/explanation/security-model.md` | E, U, M | 3446-3684 | `SECURITY.md`, `reviews/0.1.0-security-review-2026-10-21.md` and `reviews/0.1.0-whole-surface-security-review-2026-10-19.md` (facts only; never named) | What is enforced (nothing writable by default, limits, fuel, grants read-only, a trap cannot end your process, a call's folders go with it), **what is not protected** (3588-3684: a killed process, disk use in a granted folder, timing, the host's own process), how to report a vulnerability and what counts as one (`SECURITY.md` links here). |
| `docs/explanation/fuel.md` | E, U | 3479-3493, 32-54 (the idea only) | `research/2026-10-16-fuel-as-the-operation-count.md`, `research/2026-10-16-a-host-supplied-clock-and-random-make-fuel-exact.md` | Fuel counts operations, not time; why that makes a limit the same on every machine; what consumes fuel; how to pick a budget. |
| `docs/explanation/sessions.md` (thin allowed) | E, U | 2275-2420 | `research/2026-10-18-bounded-sessions.md` | Why a session is bounded, what it keeps between calls and why not more. |
| `docs/explanation/pinned-releases-and-patches.md` (thin allowed) | E, C | 680-760, 41 | `constitution.md` (pinned inputs, patches few and temporary), `upstream/README.md` | Every input pinned by URL and hash; a few releases rather than every version; a patch is recorded, has its pull request drafted and goes when upstream ships the fix; 27 today. |
| `docs/explanation/performance-and-size.md` (thin allowed) | E, U | 32-54, 2569-2578, 127-162 | — | **Dated** (2026-10-22, arm64 macOS, wasmtime 49): the wheel's size, about 16 ms per call with the snapshot, compute about 1.3 to 2.3 times native, pandas' import cost; how the numbers were taken; a note that the figures are facts of one machine. |
| `docs/explanation/design-decisions.md` (may omit) | E | — | `decisions.md`, the Decisions sections of the specifications a reader's reason needs | Six short entries, ADR-shaped (context, decision, consequence): fuel not time; nothing writable by default; few pinned releases; embedder-neutral code; the snapshot pre-imports nothing; builtin modules not shared libraries. No numbers, no dates of questions. |

### Contributing

| path | kind | README lines | `context/` sources | the page |
|---|---|---|---|---|
| `docs/contributing/first-change.md` | T, C | 3722-3735 | `AGENTS.md` ("Working autonomously", in words), `progress/README.md` | Clone, `uv sync`, `uv run pytest -m "not slow"`, read the scoreboard's last lines, the ratchet in one paragraph, what a known gap is, where a change starts (a check first). Links to AGENTS.md on GitHub as the rule book; never a `context/` path. |
| `docs/contributing/building.md` | H, C | 680-874 | `research/2026-10-16-what-the-scripted-build-needs.md`, `research/2026-10-16-reproducible-builds-on-linux.md` | `scripts/00_download.sh`, `scripts/build.sh`, the step flags, the preflight, host-neutral bytes, the pins and their verification, what a recipe file is. |
| `docs/contributing/adding-a-package.md` (may omit) | H, C | 2421-2460, 229-320 (scipy as the example) | `tests/upstream/packages.toml`, `research/2026-10-17-what-scipy-needs.md` | Pin the source, write the recipe, build it in, run its own tests in the release, add its page. |
| `docs/contributing/carrying-a-patch.md` (may omit) | H, C | 41, 680-760 | `upstream/README.md`, `upstream/patches/` (the shape, not the content) | When a recipe file is not enough; the patch file, its hash in `MANIFEST`, its CHANGELOG line, the pull request draft, its removal. |
| `docs/contributing/review-and-landing.md` | E, C | — | `AGENTS.md` rules 8 to 9 (in words), `reviews/README.md` (the rubric's idea, not its rows) | A fresh reader reviews every built change; what the reviewer gets; waves and the lane; why the implementer never reviews. No review names, no wave numbers. |
| `docs/contributing/release-process.md` | H, C | 875-1010 | `research/2026-10-18-the-release-judges-in-parallel-shards.md`, `research/2026-10-18-the-release-ties-what-it-signs.md` | The version bump, the release workflow, the shards and tiers in a paragraph, attestation, publication; what a dry run is. |
| `docs/contributing/principles.md` | E, C | — | `constitution.md` (abridged; no section numbers) | The mission; the hard constraints in words (pinned inputs, few patches, uv only, prior art studied never copied, tests count operations, artifacts never in git, nothing lands unreviewed, code speaks for itself). |

### Local build

The builder copies 122's `mkdocs.yml` (the text in 122's Decision 7) into the worktree
**uncommitted**, adds `mkdocs==1.6.1` and `mkdocs-material==9.7.7` to a scratch environment (`uv
run --with mkdocs==1.6.1 --with mkdocs-material==9.7.7 mkdocs build --strict`, or 122's `docs`
group once it exists), and builds after every few pages. Until 122's three pages exist, the
builder may put three one-line stand-ins at their paths, uncommitted, so links resolve. `git
status` before the handover shows only `docs/` pages.

## Scope

In: Decisions 1 to 6; the pages in Design. The files: every `*.md` under `docs/` **except**
`docs/reference/python-api.md`, `docs/reference/cli.md` and `docs/reference/limitations.md`. Nothing
else: no `mkdocs.yml`, `pyproject.toml`, `uv.lock`, workflow, `README.md`, `CHANGELOG.md`,
`context/` or `tests/` change (122's files). 122 writes this specification's CHANGELOG line, "The
documentation site: a Diátaxis tree under `docs/` (get started, how-to guides, reference,
explanation, contributing), built with MkDocs and served at
`https://claygendron.github.io/wasi_python/` from each release tag", and the roadmap line
(122's Decision 10).

**The shared contract with 122** (both specifications carry it):

- 122 writes `docs/reference/python-api.md`, `docs/reference/cli.md`,
  `docs/reference/limitations.md`, and `mkdocs.yml` whose nav names exactly the paths below.
- 123 writes `docs/index.md`; `docs/get-started/install.md`, `first-run.md`,
  `csv-through-a-grant.md`, `embed-python-wasm.md`; `docs/how-to/grants.md`, `mounts.md`,
  `sessions.md`, `limits.md`, `async.md`, `tools.md`, `matplotlib.md`, `excel-pdf-xml.md`,
  `embed-from-other-languages.md`, `verify-a-download.md`, `troubleshooting.md`;
  `docs/reference/results-and-errors.md`, `defaults-and-limits.md`, `guest-filesystem.md`,
  `tool-protocol.md`, `packages.md`, `support-and-versioning.md`, `artifacts.md`, `glossary.md`,
  `changelog.md`; `docs/explanation/why-wasi.md`, `how-it-works.md`, `security-model.md`,
  `fuel.md`, `sessions.md`, `pinned-releases-and-patches.md`, `performance-and-size.md`,
  `design-decisions.md`; `docs/contributing/first-change.md`, `building.md`,
  `adding-a-package.md`, `carrying-a-patch.md`, `review-and-landing.md`, `release-process.md`,
  `principles.md`.
- May be omitted (Decision 4): `get-started/embed-python-wasm.md`, `how-to/excel-pdf-xml.md`,
  `reference/glossary.md`, `explanation/design-decisions.md`, `contributing/adding-a-package.md`,
  `contributing/carrying-a-patch.md`.
- Links between pages are relative Markdown links to the `.md` file; `--strict` checks them.

Out, for 0.1.1 (the owner, 2026-10-22): snippets as files under `docs/examples/` run as a
slow-tier guest job; `help=` strings for the command's options; versioned docs; the roadmap's trim;
archiving landed specifications with their reviews; the packages table generated from `MANIFEST`
and `tests/upstream/packages.toml`; the "later" pages of the plan's tree (a guest ABI page, one
embedding page per language, the snapshot-or-reactor choice).

## Acceptance criteria

A reviewer checks each by reading the pages, plus the commands this work allows.

1. **Every page in the contract exists** at its path, or is on the "may omit" list and named as
   omitted in the handover; no page outside the contract; no file outside `docs/` in the diff.
2. **No stub.** Every page has a heading, at least one paragraph of its own and, for a tutorial or
   how-to, at least one code block with its output or result. A thin page is one of the four
   Decision 4 allows.
3. **The public-page rule holds** on every page: `grep -rniE "spec(ification)?s? [0-9]{3}|question [0-9]+|decision [0-9]+|wave [0-9]+|\bmemo\b|§|(build|pre-build|security|integration|delta) review|context/" docs/` prints nothing for this specification's pages; no name from `context/embedders.txt` and no home-folder path (`grep -rn "/Users/\|/home/" docs/` prints nothing). On the wave's tip 122's two scans pass by node id (122's criterion 6).
4. **The facts match the README** of main `bb2235f2`: every number (limits, versions, the 27
   patches), every example and its output, and every host in the hosts table is one the README
   gives at the line range the Design names; the reviewer samples ten.
5. **Style**: second person, present tense, sentence-case headings, no first-person project
   history ("we decided"), no dates except on the performance page and the changelog.
6. **The build**: `uv run --group docs mkdocs build --strict` passes on the wave's tip with 122's
   `mkdocs.yml`; every link between pages resolves; the changelog page renders `CHANGELOG.md`.
7. **The three doors on Home** resolve to `get-started/first-run.md`,
   `how-to/embed-from-other-languages.md` and `contributing/building.md`.
8. **The security-model page** has a heading "What is not protected" and a section on reporting
   that agrees with `SECURITY.md`.
9. **Nothing promised that is 0.1.1's**: no page says snippets are tested, that docs are
   versioned, or describes a generated packages table.

## For the lane

- **Wave kind: context only, parallel-safe.** One wave with 122: this specification first, 122
  onto it. This specification's builder never rebases onto 122; 122's builder rebases onto this
  tip and names every conflict (none expected; the files are disjoint by contract). If this
  specification omitted a page, the lane deletes its nav line in 122's `mkdocs.yml` on the rebase
  and names it.
- **No builder judge runs.** The builder runs only `mkdocs build --strict` locally (Design, Local
  build). No branch run, no fast tier. The reviewer reads the pages against the criteria and does
  not run the judge.
- **The lane, on the wave's tip**: `uv run --group docs mkdocs build --strict` and 122's two scans
  by node id, then the one release acceptance and the dry run, as 122's For the lane says. This
  specification adds no `--accept-judge` reason and no claim-list row: it changes no check and no
  judged file.
- **Pages**: the site serves only after the owner enables Pages and the `v0.1.0` tag's `docs.yml`
  run deploys; until then the README's documentation links 404, which the lane says in the landing
  notes if the owner tags before enabling Pages.

## One line

Forty pages under `docs/`, each with its path, its README lines and its sources, written for
outside readers in Diátaxis's four kinds plus a contributor section, naming no specification,
question, review or memory path; thin where it must be, never empty; built strict, served from the
tag.

## Landing notes

### Built 2026-10-22 (the builder)

On `spec/123-the-documentation-site`, base main `fb8343cd`. The builder wrote `docs/index.md`,
the glossary, the changelog page and five contributing pages, and three helper agents in the
same worktree wrote the rest by page group from this specification and one shared brief (the
public-page rule, the style, the facts rule); the builder checked every page against the rules
and made the links consistent.

**Pages: 39 of the contract's 40.** Written: every page in Scope's shared contract except
`get-started/embed-python-wasm.md`, **omitted** (Decision 4's list): the README gives no host
command for the bare binary that works with its output (it says only that a plain `wasmtime run`
cannot bind the door's import), so the tutorial would have had to invent its example. **The
lane deletes its nav line** in 122's `mkdocs.yml` on the rebase. The five other "may omit" pages
are written and real, and linked from the pages around them: `how-to/excel-pdf-xml.md` (its code
blocks are the README's fragments, each with the result the prose states, not a printed output;
a reviewer who reads criterion 2 strictly may ask for it to be dropped, which is one nav line),
`reference/glossary.md`, `explanation/design-decisions.md`, `contributing/adding-a-package.md`,
`contributing/carrying-a-patch.md`. Thin pages: none is a stub; `how-to/matplotlib.md` is full.

**Deviations, each with its reason:**

- `docs/reference/changelog.md` is the snippet line alone, without its own heading: the included
  `CHANGELOG.md` brings `# Changelog`, and a second H1 rendered the title twice. The page's
  title is "Changelog" (checked in the built HTML).
- Where the README contradicts itself, the pages take the newer statement or leave the claim out:
  27 carried patches (the Measured table, as acceptance criterion 4 names; "How it is built"
  still says twenty-three); 16 ms and 43.8M instructions per snapshot call (not the older 14 ms,
  20 to 25 ms or 82 million); 53.9 MB for the zip; the release set as one `.tar.xz`; no version
  for cycler, pyparsing, packaging, python-dateutil, tzdata or six (none given).
- `get-started/csv-through-a-grant.md` uses three README examples as they stand (the grant
  example writing `n.txt`, the session example writing and reading `df.csv` and `df.pkl` with its
  `b'6\n'`, the `--grant`/`--grant-writable` command line); the README has no single `run()`
  example that reads and writes a CSV through grants, and none was invented.
- `how-to/limits.md` shows the README's own lines that set limits (the command's `--deadline-s`,
  `set_defaults(dataclasses.replace(...))`, the `resource` lines, the `print(1)` JSON line); the
  README has no `run()` example passing a limit with its output.
- `explanation/security-model.md` names the two wasmtime advisories the runner carries fixes for
  (GHSA-m9f7-9w4p-gv38, GHSA-96f6-r43r-8c24), as `SECURITY.md` already publishes them; nothing
  from `upstream/advisories/` (the project's own draft) is on any page.
- `contributing/review-and-landing.md` names "the lane" and "waves" in words, defined there, as
  this specification's Design row asks; no wave number, review name or path.
- Instruction counts for finalization (about 28M; 45M to 60M after pandas) are on
  `explanation/fuel.md` too, as product facts for sizing a budget, not benchmarks; times and
  sizes appear only on the dated performance page.

**Self-check** (`reviews/README.md`, the items that apply to a context-only specification):

- Base: main `fb8343cd`, today; the branch carries this specification only.
- **No branch run, by the owner's rule for this work (decisions.md, 2026-10-22)**; no fast tier,
  no `uv run pytest` at all. No number here is a measured run's: the pages' numbers are the
  README's at the Design's line ranges.
- `uv run --with mkdocs==1.6.1 --with mkdocs-material==9.7.7 mkdocs build --strict` with 122's
  `mkdocs.yml` text (Decision 7, the nav less the omitted page) and three one-line stand-ins for
  122's pages (headings "On Windows" and "The platform's facts" included), all uncommitted and
  deleted before the commit: **passes, no warning**; the changelog page renders `CHANGELOG.md`.
  No page links to an anchor in 122's three pages.
- Criterion 3's grep (`spec(ification)?s? [0-9]{3}|question …|context/`) and the home-path grep:
  **nothing** on the 39 pages. `scan.CITATION_RULES` applied line by line to every `docs/*.md`,
  read whole, and `context/embedders.txt`'s names: **0 hits**. Also clean: finding-like tokens, a
  review by date or path, dates outside the performance page.
- Criterion 7: Home's three doors resolve to `get-started/first-run.md`,
  `how-to/embed-from-other-languages.md`, `contributing/building.md`.
- Criterion 8: `explanation/security-model.md` has "What is not protected" and a reporting
  section that agrees with `SECURITY.md` (private report through the Security tab, no public
  issue, what to include, the advisory's credit, only the newest release supported).
- `git status` before the commit: only `docs/` pages and this file. CHANGELOG and roadmap lines
  are 122's (Scope). ruff does not read `docs/`.

### Disposition of the build review

The build review (`../reviews/123-the-documentation-site-build-2026-10-22.md`, on `92a134d3`;
verdict "lands after fixes", no High, two Medium, seven Low; no run, by the owner's rule for this
work). Every finding is fixed in the commit after `92a134d3`, with the review's text where it gave
one:

1. **M1, the CSV tutorial never reads the reader's CSV and does not make its folders** — fixed.
   `get-started/csv-through-a-grant.md` is retitled "Read and write files through a grant" (the
   path stays), its opening says "a folder to read and a folder to write into", Step 1 gains the
   review's host-side `mkdir` block (no guest output claimed), Step 3 is "Write a CSV with pandas
   and read it back", and the link in `get-started/first-run.md` takes the new title. **For the
   lane:** if 122's `mkdocs.yml` names a title for this path, change it to "Read and write files
   through a grant" on the rebase; a nav entry without a title takes the H1.
2. **M2, seven code blocks cannot run as copied** — fixed. The three `set_defaults` blocks
   (`how-to/limits.md`, `how-to/async.md`, `reference/defaults-and-limits.md`) now import
   `dataclasses`, `defaults` and `set_defaults` and pass `async_workers=4`; the three `resource`
   blocks (`how-to/limits.md`, `how-to/troubleshooting.md`, `reference/defaults-and-limits.md`)
   import `resource` with the comment "Linux and macOS; Windows has no resource module"; the
   matplotlib block imports `Grant` and `run`. The two guest-side xlsxwriter fragments
   (`how-to/troubleshooting.md`, `how-to/excel-pdf-xml.md`) gain the line "Inside the guest
   program, with `buf = io.BytesIO()`". `how-to/limits.md` shows one `run(["-c", code],
   deadline_s=10, memory_bytes=256 << 20, fuel=5_000_000_000)` call, every keyword `run`'s own
   (`src/wasi_python/runner.py`, the signature), with its limits in words and no output claimed.
3. **L1, the `SHA256SUMS` check fails on a single download** — fixed with the review's text:
   `shasum -a 256 -c --ignore-missing SHA256SUMS` (`sha256sum` on Linux); the asset prints `OK`.
4. **L2, a heading contradicts its entry** — fixed: "The snapshot pre-imports no package" (no
   page linked the old anchor).
5. **L3, a time on the wrong measurement** — fixed: the `import pandas` on the snapshot row's time
   cell is empty, as `import numpy`'s is.
6. **L4, the command's `none` understated** — fixed on both pages: every limit option
   (`--deadline-s`, `--memory-bytes`, `--output-bytes`, `--fuel`, `--max-open-files`) takes `none`.
7. **L5, a reference page leans on the README** — fixed: "For example, this call returns exit code
   0 and the sum on standard output:".
8. **L6, the 5-minute path skips install from Home** — fixed: "**Use it.** `pip install
   wasi-python`, then run your first sandboxed program." The door's target is unchanged
   (criterion 7).
9. **L7, small wording** — fixed. `get-started/install.md` says "the files that make up the
   runtime". `contributing/first-change.md`'s early scoreboard sample is replaced by the
   scoreboard's shape, with placeholders, taken from `tests/harness/scoreboard.py`'s line formats
   (first line, one line per area, `blocked by:`, `gaps close with:`, `next:`, the ratchet line,
   `not machine-checked:`); the judge was not run for a new sample.

After the fixes (EXECUTED, the same way as the build): `mkdocs build --strict` with 122's
`mkdocs.yml` text less the omitted page and three uncommitted stand-ins, since deleted: **exit 0,
no warning**. Criterion 3's grep and the home-path grep: nothing. `scan.CITATION_RULES` and
`context/embedders.txt`'s names over every `docs/*.md`: **0 hits**. Finding-like tokens, a review
by date or path, dates outside the performance page: none. No pytest, no workflow, no branch run.
