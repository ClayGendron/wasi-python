# Review of 123 — The documentation site (the build)

- **Date:** 2026-10-22
- **Reviewer:** a fresh agent (Claude). It wrote none of 123's pages, none of 122, and none of the research the pages stand on. It did not review 123 before the build (there was no pre-build review; rule 8, context only).
- **Reviewed:** `spec/123-the-documentation-site` at `92a134d3`, in the worktree `.claude/worktrees/agent-a5e3aedbc460a894a`. The base is main `fb8343cd`. The diff is `git diff fb8343cd..92a134d3`: 40 files, +4,790 −2 (39 pages under `docs/` and the specification's status and landing notes). Read from a `git archive` of the tip, so nothing in the builder's worktree was touched.
- **Run:** none, by the owner's rule for this work (decisions.md, 2026-10-22). No `pytest`, no fast tier, no workflow dispatched.
- **Time box:** 50 minutes (the lane's). Kept.
- **Re-ran (EXECUTED, in the scratchpad, outside the repository):**
  - `uv run --no-project --with mkdocs==1.6.1 --with mkdocs-material==9.7.7 mkdocs build --strict` over a copy of the tip's `docs/` and `CHANGELOG.md`, with 122's Decision 7 `mkdocs.yml` written out (validation `omitted_files`, `absolute_links`, `unrecognized_links`, `anchors` all `warn`; the nav exactly the shared contract less `get-started/embed-python-wasm.md`) and one-line stand-ins for `python-api.md`, `cli.md` and `limitations.md` (the last with the headings "On Windows" and "The platform's facts"). **Exit 0, no warning.** The changelog page renders `CHANGELOG.md` under one H1 "Changelog" (8 `h2`s). mkdocs and Material came from PyPI.
  - Criterion 3's grep over `docs/`: nothing. The home-path grep (`/Users/`, `/home/`): nothing (`~/project/data` in the tutorial is a reader's example, not a personal path). `tests/harness/scan.py`'s `CITATION_RULES`, extracted and run over every `docs/*.md` read whole: **0 hits**. `context/embedders.txt`'s name, case-insensitively: **0 hits**. No `GHSA-draft`, no `upstream/advisories`.
  - Every GitHub link's target path exists at the tip (`AGENTS.md`, `SECURITY.md`, `recipes/`, `recipes/patches/`, `release/version.py`, `scripts/00_download.sh`, `scripts/line.conf`, `scripts/steps/`, `scripts/steps/apply_patches.sh`, `scripts/wasi-cc`).
  - Every `--flag` on every page, listed and checked against its parser: `cli.py:_parser` (14 options), `scripts/build.sh` (usage lines 32-39), `release/version.py` (lines 214-226), `tests/harness/plugin.py:116` (`--shard`). None invented.

## Acceptance criteria against evidence

1. **Every page in the contract exists, or is omitted from the list:** met. 39 of 40; `get-started/embed-python-wasm.md` omitted, on Decision 4's list, named in the handover. No page outside the contract; nothing outside `docs/` but the specification's own notes. READ.
2. **No stub:** met. Every page has a heading, prose of its own, and every tutorial and how-to a code block with its output or stated result. `how-to/excel-pdf-xml.md`'s blocks are fragments with the result in prose; acceptable for a how-to (see Deviations). READ.
3. **The public-page rule:** met. EXECUTED (above).
4. **Facts match the README of `bb2235f2`** (identical to `fb8343cd` for `README.md` and `src/`): met, with two Low exceptions (L3, L5). 38 claims sampled, each against its source, listed below. READ.
5. **Style:** met. Second person, present tense, sentence-case headings, no "we decided"; the one "we" is inside a patch-README template (`contributing/carrying-a-patch.md:63`). Dates only on the performance page; `0.1.0a1` and `regex 2026.9.29` are versions. READ.
6. **The build:** met locally (EXECUTED, above); the lane repeats it with 122's real files on the wave's tip. INFERRED for the tip.
7. **Home's three doors:** met: `get-started/first-run.md`, `how-to/embed-from-other-languages.md`, `contributing/building.md` (`index.md:23,25,27`). READ. See L6.
8. **Security model:** met. `## What is not protected` (`explanation/security-model.md:106`); the reporting section (188-220) agrees with `SECURITY.md` lines 6-30: the Security tab, no public issue, what to include, the credit, the four in-scope kinds, the newest release only. The two GHSA ids are the ones `SECURITY.md:40,45` already publishes. READ.
9. **Nothing promised that is 0.1.1's:** met. No page says snippets are tested, docs are versioned, or the packages table is generated (grep). READ.

### The claims sampled (each READ against its source)

API and signatures: `run`'s keywords and defaults (`runner.py:115-139`: `root=False`, `fuel=None`, `max_open_files`, `cancel`, `tools`, `gate`); `run_async` = `run` less `cancel` plus `executor` (`runner.py:285-309`); `Session` = `run` less `argv`, `stdin`, `cancel`, plus `idle_s`, `lifetime_s`, `shutdown_s` (`runner.py:762-787`); `Session.run(code, *, fuel, deadline_s, output_bytes, cancel)` and `run_async` per turn (`runner.py:1034-1093`); a turn echoes its final expression (`runner.py:1045`); `Completed`'s eight fields (`_call.py:80-87`); `Defaults`' eleven fields and values 1 GiB / 60 s / 16 MiB / 10,000 / 1,000 / 16 MiB / 1,024 / 900 / 3,600 / 5 (`runner.py:82-92`, `__init__.py:59-61`); `async_workers` = CPUs, at most 8 (`_limits.py:162-165`); integer limits 0 to 2**63 − 1 and a deadline > 0 (`_limits.py:38-60`); `Artifacts`' four fields (`_artifacts.py:56-59`) and `artifact_dir`; `__all__` (`__init__.py:94-`); `Errno`'s 21 members and values (`mounts.py:41-61`); `Mount(provider, guest, *, writable=False)` (`mounts.py:185-187`); provider methods incl. `rename` (`mounts.py:92-160`); `Stat(kind, size, mtime_ns)`; `SessionEnded(RuntimeError)`, `ToolDenied(ToolError)`; `tools.__all__` and `tool()`'s keywords (`tools.py:236-249, 717-727`); `PROTOCOL = 1`; 1 MiB request, 16 MiB answer, 100,000 steps (`_tool_host.py:31-32`, `_tool_schema.py:22`); 4 abandoned tool threads (`_tool_host.py:38`).

Packaging and command: `wasi-python` on PyPI, `requires-python >=3.11`, `wasmtime>=49,<50`, the empty `run` extra, the `wasi-python` script (`pyproject.toml:2-27`); wasmtime-py 49.0.0 (`uv.lock:323-324`); every `wasi-python run` option and `none` parsing (`cli.py:79-118`); JSON line sorted keys (`cli.py:_write`); release assets wheel + `.tar.xz` + `SHA256SUMS` (`release/version.py:172-179`); `version.py bump` / `release --push`; `build.sh` twenty steps incl. `00_download`, `--list/--from/--resume/--check/--plain`, preflight line, 2.5 GiB (`build.sh:27,32-39`, `progress.sh:195-215`).

Facts: 27 patch files (`find recipes/patches -name '*.patch'`); the package versions in `reference/packages.md` against `downloads/SHA256SUMS` (numpy 2.5.2, pandas 3.0.6, scipy 1.18.1, scikit-learn 1.9.1, statsmodels 0.15.0, matplotlib 3.11.2, Pillow 13.0.0, lxml 6.1.3, regex 2026.9.29, OpenBLAS 0.3.34, openpyxl 3.1.5, pypdf 6.21.1, reportlab 5.0.1, seaborn 0.13.2, fontTools 4.67.0, formulaic 1.2.2, CPython 3.15.0); sizes 99.4 / 104.5 / 53.9 / 98.3 MB, 16 ms and 43.8M, 4.66G / 0.81G, 8.78G / 6.79G, 8 min 35 s, six golden jobs (README 42-52); finalization 28M and 45M to 60M, session shutdown ~308M after pandas (README 1080-1081, 2368-2372); 40 to 250 levels (README 516); "20 ms before the deadline" (README 1987); every README example reproduced verbatim with its output (pandas `(0, b'6\n')`, `print(1)` JSON line, the grants, state, session pickle `b'6\n'`, mounts `Files`/`Store` and `'read': 1`, tools `b'Ada\n'`, async `b'1.08\n'`, FastAPI, matplotlib, the LangChain and MCP recipes with `langchain-core==1.6.12` and `mcp==2.3.0`).

## Findings, most severe first

No High finding. Every flag, signature, default, version and example I sampled is the source's.

### Medium

**M1. The "Read a CSV through a grant" tutorial never reads the reader's CSV, and does not make its folders.** `docs/get-started/csv-through-a-grant.md:1,10-19,44-65`. Step 1 tells the reader both folders "must exist" but gives no way to make them; Step 2 counts directory entries; Step 3 writes `df.csv` but reads back `df.pkl`. A reader who follows the title learns no `pd.read_csv` through a grant. The builder's deviation explains why (the README has no such `run()` example, and Decision 5 forbids inventing one); that justifies the content, not the title or the missing setup. A tutorial must work start to finish. Fix, keeping the path and the README's examples:

- Line 1: `# Read and write files through a grant`
- Line 3: "In this tutorial you hand the guest a folder to read and a folder to write into, then read what it wrote from the host."
- After line 16, a block the reader runs first (host-side, no guest output claimed):

  ```python
  from pathlib import Path

  (Path.home() / "project" / "data").mkdir(parents=True, exist_ok=True)
  Path("/tmp/job-17").mkdir(exist_ok=True)
  ```

- Line 44: `## Step 3: Write a CSV with pandas and read it back`.
- The one link to the page, `first-run.md:71`, takes the text "Read and write files through a grant". A nav entry without a title takes the H1; if 122's `mkdocs.yml` names a title for this path, the lane changes it on the rebase.

**M2. Seven code blocks cannot run as copied.** They name what they never import, or a variable nobody defines. The README gave these as inline fragments; the pages promote them to fenced blocks, where a reader copies them whole.

- `docs/how-to/limits.md:48-50`, `docs/how-to/async.md:56-58`, `docs/reference/defaults-and-limits.md:100-102` — replace each block with:

  ```python
  import dataclasses

  from wasi_python import defaults, set_defaults

  set_defaults(dataclasses.replace(defaults(), async_workers=4))
  ```

- `docs/how-to/limits.md:86-89`, `docs/how-to/troubleshooting.md:116-119`, `docs/reference/defaults-and-limits.md:115-118` — add the import and the platform:

  ```python
  import resource  # Linux and macOS; Windows has no resource module

  soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
  resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
  ```

- `docs/how-to/matplotlib.md:12` — first lines of the block: `from wasi_python import Grant, run` and a blank line.

(`troubleshooting.md:57-58` and `excel-pdf-xml.md:18-21` are guest-side fragments whose `pd`, `buf` and `xlsxwriter` are the guest program's; leave them, or add one prose line: "inside the guest program, with `buf = io.BytesIO()`".)

Also on `limits.md`: the page "Set limits on a call" shows no Python call that passes a limit. Add after line 22 (a signature use, not a claimed output):

```python
done = run(["-c", code], deadline_s=10, memory_bytes=256 << 20, fuel=5_000_000_000)
```

### Low

**L1. The `SHA256SUMS` check fails on a single download.** `docs/how-to/verify-a-download.md:45-46`. The release's `SHA256SUMS` lists the wheel and the `.tar.xz`; with one of them absent, `shasum -a 256 -c SHA256SUMS` prints "FAILED open or read" and exits non-zero, so "Each listed file should print `OK`" is false for the usual case. Fix: "download the asset and `SHA256SUMS` into one folder and run `shasum -a 256 -c --ignore-missing SHA256SUMS` there (`sha256sum -c --ignore-missing SHA256SUMS` on Linux). The asset should print `OK`." (macOS's `shasum` 6.02 has `--ignore-missing`; EXECUTED `shasum --help`.)

**L2. A heading contradicts its own entry.** `docs/explanation/design-decisions.md:77` "## The snapshot pre-imports nothing", while line 85 and `reference/artifacts.md:25-26` say it pre-imports the stdlib's bootstrap modules. Fix: `## The snapshot pre-imports no package`.

**L3. A time is attached to the wrong measurement.** `docs/explanation/performance-and-size.md:32` gives `import pandas` on the snapshot "about 0.8 s". README line 47 gives 0.81 s for "a small pandas job, before the unfreeze", not the import on today's snapshot. Fix: leave the time cell empty, as for `import numpy` on line 31.

**L4. The command's `none` is understated.** `docs/reference/defaults-and-limits.md:32-33` and `docs/how-to/limits.md:34-35` say `--deadline-s`, `--memory-bytes` and `--output-bytes` take `none`; `cli.py:85-92` parses `--fuel` and `--max-open-files` the same way (its help says "none for no limit"). Fix: "On the command line, every limit option (`--deadline-s`, `--memory-bytes`, `--output-bytes`, `--fuel`, `--max-open-files`) takes the word `none`."

**L5. A reference page leans on the README.** `docs/reference/results-and-errors.md:26` "the pandas call from the README". 122 shortens the README; the page should stand alone. Fix: "For example, this call returns exit code 0 and the sum on standard output:".

**L6. The 5-minute path skips install from Home.** `docs/index.md:22-23`: "Install the wheel and run your first sandboxed program. Start with Your first run" links past the install page; the reader learns of it only at `first-run.md:4-5`. Criterion 7 fixes the door's target, so fix the text: "**Use it.** `pip install wasi-python`, then run your first sandboxed program. Start with [Your first run](get-started/first-run.md)."

**L7. Small wording.** `docs/get-started/install.md:25` "the four files" above a table of five (`MANIFEST` and `SHA256SUMS` share a row): write "the files that make up the runtime". And `docs/contributing/first-change.md:41-49` shows an early scoreboard (`14/67`, "unit suite 115/115"); it says numbers differ, so it may stay, but a current excerpt's shape would serve a contributor better.

## The builder's deviations

All six agreed.

- **`embed-python-wasm.md` omitted:** agreed. The README gives no working host command for the bare binary (`wasmtime run` cannot bind the door, README 1039-1048 and the hosts section), and `how-to/embed-from-other-languages.md:79-167` already covers the four things a host does. The lane deletes the nav line, as the handover says.
- **`excel-pdf-xml.md` kept:** agreed. Its blocks are configuration fragments whose result is stated beside them; dropping a real page to satisfy the letter of criterion 2 would lose content. M2's prose line makes the fragments' context explicit.
- **`changelog.md` without its own heading:** agreed; checked in the built HTML (one H1).
- **The README's contradictions resolved toward the newer figure (27 patches, 16 ms, 43.8M, 53.9 MB, one `.tar.xz`):** agreed; each checked against the source (patch files, README's Measured table, `release/version.py:179`).
- **Three README examples in the CSV tutorial; README lines on the limits page:** agreed on content; M1 and M2 fix the framing, not the examples.
- **The two GHSA ids; "the lane" and "waves" in words; finalization counts on the fuel page:** agreed; all public facts, none a citation.

## Prose

Good. Short sentences, one idea each; terms defined where first used (guest, host, grant, root, trap, fuel, golden job, reactor) and again in the glossary; every page ends with its one-line version, as AGENTS.md "Explaining things" asks. The densest places are the tables in `reference/results-and-errors.md` (the `RuntimeError` row) and `how-to/grants.md`'s refusals, which are reference by nature.

## Verdict

**Lands after fixes.** No High. M1 and M2 are small text edits in `docs/` (a title, a setup block, imports), the builder's to make; the Lows may be fixed in the same commit or answered in writing. None changes a check, so no further review round is needed once the lane reads each fix against its finding.

In one line: accurate, clean of internal citations, builds strict; retitle and set up the CSV tutorial, and make the seven copied blocks runnable.
