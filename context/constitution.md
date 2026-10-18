# Constitution

- **Status:** in force, 2026-10-16; amended the same day by the owner's
  decision on profiles and on what the product is for (§2 "Beyond v1",
  §3 first bullet); amended 2026-10-17 by the owner's answers to
  questions 1, 3, 4, 5, 7 and 9 (`questions-for-the-owner.md`): typed
  grants that may be none (§2.2, §2.4), the build order after v1 (§2),
  a command line inside the runner (§3), safe by default (§4.15), three
  approved licences (§4.12), and the release rules (§5.5, §5.6); §4.15's
  alpha exception (the stdlib zip in a writable root) ended by spec 017,
  as the exception itself provided.
  Amended 2026-10-17 by the owner's answer to question 32: carried
  upstream patches, recorded and temporary (§4.1, and §2.5, §6.2, §7 and
  §8 to match).
  Amended 2026-10-17 by the owner's answers to questions 12, 14, 19, 24,
  25, 33 and 35: bounded sessions (§3), a tool protocol over the door
  (§4.4), the matplotlib and scipy licences (§4.12), nothing writable by
  default (§4.15), and §4.1's spent clause.
  Amended 2026-10-17 by the owner's adoption of
  `research/2026-10-17-parallel-work-without-lowering-the-bar.md`:
  specifications built in parallel in their own worktrees, landed one
  at a time through one landing lane (§4.14, §5.4, §5.7, §7).
  Amended 2026-10-17 by the owner's decision to keep the roadmap out of
  this document: §2 is the bar every release meets; what each release
  contains, and the order of work, live in `roadmap.md`.
  Amended 2026-10-17 by the owner's answer to question 43: the default
  profile's other packages' licences (§4.12).
  Amended 2026-10-18 by the owner's answers to questions 70, 73, 81
  and 83: contourpy, the barcode modules' four-clause BSD and CC BY 4.0
  for three scikit-learn datasets (§4.12), and one unpushed acceptance
  commit may be soft-reset (§4.14).
- **Owner:** Clay Gendron
- **Scope:** every document, script, recipe and line of code in this
  repository, and every agent or person working on it. The other
  documents under `context/` obey this one. Change it only with the
  owner's explicit decision, recorded in the change.

## 1. Mission

wasi_python exists so that **any program that can host WebAssembly
can run real Python, with numpy and pandas, inside a sandbox it fully
controls, without a browser, a JavaScript engine, a kernel feature or
a package install step.**

One artifact. One wall. Every platform. A few pinned releases, not
every version of everything.

## 2. The goal, stated so it can be checked

A release is ready when all of these are true (the judge's goals v1.1
to v1.5 check them):

1. A statically linked `python.wasm` for `wasm32-wasip1` with CPython
   and its profile's packages compiled in as builtin modules is
   published as a GitHub release and as the `wasi-python` wheel on
   PyPI, with a manifest and hashes.
2. It runs under wasmtime on Linux, macOS and Windows from the same
   bytes, with no host directory beyond the grants the embedder gives
   (read-only or writable folders, which may be none), no network, no
   shared library and no host process.
3. Every compiled-in package imports and works; the judge's jobs for
   each (for numpy and pandas: a CSV read, a groupby and a CSV write)
   run inside it, and the results match native Python.
4. An embedder in any language with a wasmtime binding can run it by
   preopening the folders it grants (possibly none), binding one host
   function and calling one export. A Python embedder does it in one
   call through the wheel.
5. The whole thing rebuilds from pinned sources by a CI job anyone can
   run; any upstream tree differs from its pinned tarball only by the
   recorded, temporary patches §4.1 allows.

What a release contains, which packages its default profile carries,
and the order of work are the roadmap (`roadmap.md`): the owner's
living plan, changed by the owner's decision without amending this
document. One principle holds for every roadmap: a profile is its own
artifact set, built, judged and published, chosen by name and never
assembled on a user's machine, and profiles stay few.

## 3. What this project is not

- Not a development environment. It is a drop-in, easy-to-use,
  sealed Python for lightweight loads: an embedder runs a program and
  gets its result. No pip, no venv, no package tracking.
  A release is one pinned set of versions. The project does not build
  every release of every supported package; it builds a new set when
  there is a reason to, and the old sets stay published.
- Not a browser Python. Pyodide owns that.
- Not a general wasm toolchain. It builds one artifact well.
- Not an application. It ships no filesystem, no shell, no agent, no
  server. Those are its embedders' business. A thin command that runs
  one program through the runner and prints its result as JSON
  (`wasi-python run`) is part of the runner, not a shell: it adds no
  power `run()` does not have (owner, 2026-10-17). A bounded session,
  one guest kept across several calls with an idle timeout and a
  lifetime, is part of the runner too, not a development environment
  (owner, 2026-10-17, question 19).
- Performant, not the fastest. It is correct, portable and sealed
  first, and it stays close to native: the penalty against native
  Python is measured on every release, documented, never hidden, and
  never the reason to break another rule. A build that gets slower
  than the last one without a stated reason is a regression.

## 4. Hard constraints

These are not preferences. Work that violates one is wrong even if it
works.

1. **Upstream patches are few, recorded and temporary.** An adaptation
   is a recipe file first: a cross file, a compiler wrapper, a rename
   header, a stand-in module, a linker flag. Where a source change is
   unavoidable, the project carries it as a patch file under
   `recipes/patches/`, applied after the pinned tarball's hash is
   checked. Each patch is reviewed like any change, recorded in
   `MANIFEST` by its hash, named in the CHANGELOG, and matched by an
   upstream pull request drafted in the repository for the owner to
   send; it is deleted once an upstream release carries the fix. The
   release workflow fails on any difference from the pinned tarball
   other than exactly the recorded patches (question 32; built by
   spec 020).
2. **Every input is pinned and hashed.** Every source tarball,
   toolchain, tool and pure-Python dependency is a URL plus a SHA-256
   in `downloads/SHA256SUMS`, verified before use. A build that fetches
   anything unpinned is not a build.
3. **One target: `wasm32-wasip1`.** No Emscripten, no JavaScript, no
   native code path, no host-specific branch. If something cannot be
   done inside WASI, it is left out and documented.
4. **The guest reaches the host through exactly two things:** the
   WASI preview1 calls and one custom import, the host door. No third
   import, ever. The door's raw frames are opaque to this project; what
   they mean is the embedder's. On top of the door the project may
   ship one tool protocol, through which a guest calls the host's
   tools, APIs and MCP servers: optional, used only when the embedder
   passes its tools, and gated by the embedder on every call (owner,
   2026-10-17, questions 12 and 14).
5. **Embedder-neutral.** No code, name, default or test in this
   repository refers to a particular embedder. vfs is one consumer
   and gets nothing the next consumer does not.
6. **The artifact set is the product.** A plain reactor `python.wasm`,
   a snapshot `python.wasm`, the stdlib zip, `MANIFEST`,
   `SHA256SUMS`, and the licence notices of everything inside. Nothing
   compiled per host (`.cwasm`) is ever published. Nothing large ever
   lives in git.
7. **Prior art is studied, never copied.** Clones under
   `context/prior_art/` are read-only design input. Every line here is
   original. Licences are checked on clone and recorded; a project with
   no licence is deleted from the working set.
8. **Downloads are untrusted.** They unpack under `downloads/` and
   `build/`, never into the system, and execute only as build tools
   under the build's own control or as guests under wasmtime.
9. **Tests count, benchmarks time.** A test asserts operation counts,
   exit codes, bytes and equality with native results. Wall-clock and
   memory are benchmark facts in a research memo. A test that measures
   time is a bug.
10. **Claims carry their evidence.** Every number in a document has a
    command and an output beside it; every claim is labelled EXECUTED,
    READ or INFERRED. A result that was not run is not reported as
    run.
11. **Platform semantics are documented, not disguised.** The 32-bit
    default integer, the missing threads, the missing modules, the
    speed ratio: all stated in the README and in `python3 --version`.
12. **Licence compliance ships with the artifact.** The binary contains
    CPython (PSF), numpy and pandas (BSD-3-Clause), zlib and the
    pure-Python dependencies; their notices are inside the release and
    the wheel. Nothing with a licence the owner has not approved is
    linked in. Approved 2026-10-17: SQLite (public domain), bzip2
    (BSD-style) and liblzma from xz (0BSD); for matplotlib (question
    35), FreeType (FTL), HarfBuzz, SheenBidi (Apache-2.0), libraqm,
    Qhull, Agg, matplotlib (PSF-style) with its bundled data notices,
    kiwisolver, pybind11 and cppy (BSD-3-Clause), Pillow (HPND),
    fonttools, cycler, pyparsing and packaging, and the fonts and their
    terms (OFL, Bitstream Vera, BaKoMa, DejaVu's public-domain part,
    the Adobe AFM and AMS terms, Unicode's data terms); for scipy
    (question 25), Boost.Math and ryu (BSL-1.0), xsf
    (BSD-3-Clause-LBNL), fast_matrix_market (BSD-2-Clause), and scipy,
    OpenBLAS, LAPACK, HiGHS and ducc0 (BSD/MIT); for the default
    profile's other packages (question 43), openpyxl, et-xmlfile,
    beautifulsoup4, soupsieve, html5lib, pyyaml, tomli-w, tabulate,
    charset-normalizer, xmltodict, attrs, more-itertools, narwhals,
    formulaic, interface-meta, libxml2, libxslt, python-docx and
    python-pptx (MIT), xlsxwriter, patsy and wrapt (BSD-2-Clause),
    xlrd, webencodings and reportlab (BSD), pypdf, jinja2, markupsafe,
    networkx, sympy, mpmath, toolz, joblib, cloudpickle, threadpoolctl,
    seaborn, scikit-learn, statsmodels and lxml (BSD-3-Clause),
    defusedxml and typing-extensions (PSF-2.0), tqdm (MPL-2.0 AND MIT)
    and regex (Apache-2.0 AND CNRI-Python). Approved 2026-10-18:
    contourpy (BSD-3-Clause, its GIST-derived code under matplotlib's
    LICENSE_YORICK; question 81); Tyler C. Sarna's barcode modules in
    reportlab (BSD-4-Clause: every material that mentions barcodes says
    "This product includes software developed by Tyler C. Sarna.";
    question 73); scikit-learn's and statsmodels' bundled code as
    specs 044 and 045 list it, and CC BY 4.0 for scikit-learn's digits,
    breast cancer and wine data, shipped with attribution (question 83).
    Each ships with its notice.
13. **Tooling.** `uv` only. `ruff check`, `ruff format --check` and
    `pytest` green on `src/` and `tests/` before any landing. No
    dependency added to `pyproject.toml` without a reason written in
    the specification that needs it.
14. **Git.** Commit or push only when the owner asks. Work on one
    specification may run in its own git worktree, outside the
    repository, on a local branch named `spec/NNN-<slug>` made from
    main's tip; the branch is never pushed and is deleted with its
    worktree when the specification lands or is abandoned. No other
    branch or worktree unless asked. Main moves only by fast-forward,
    through the landing lane (§5.7). One exception (question 70): an
    acceptance commit that is unpushed and breaks rule 1 may be undone
    with `git reset --soft`; a pushed one stops the lane. Never `git checkout`, `git
    restore` or `git stash` a file carrying uncommitted work.
15. **Safe by default.** Every limit has a default (memory, time,
    output); no channel to the host opens without an explicit argument
    (no folder, no network, no host function); the runtime's own files
    are never in a writable grant. A call given no root and no grants
    has nothing writable: no folder, no `/tmp`, no `HOME` (owner,
    2026-10-17, question 24). A change that loosens a default needs
    the owner's decision, not only a review (owner, 2026-10-17).

## 5. How work is done

1. **The pipeline is study → research → specify → build → review.**
   Nothing is built that no specification describes; no specification
   is written on a question no research has answered; nothing lands
   that no review has passed. `context/README.md` holds the rules of
   each stage.
2. **No open questions.** A specification decides every choice it
   needs and says why. What cannot yet be decided becomes a placeholder
   research memo naming the experiment that will decide it, and the
   specification waits. There is no backlog of undecided things.
3. **Time boxes are real.** A research task states its box. At the box
   the agent stops, records exactly where it stood and why, and
   reports. A blocked step is skipped, not forced.
4. **Small, finished, verified.** A landing is one specification,
   green, with its landing notes written and its numbers reproduced.
   Half-built work is not landed; it is reported as half-built.
   Specifications may be built in parallel; they land one at a time.
5. **A release is a re-run, not a project.** A new pinned set means:
   re-pin, re-run, re-verify, publish, and write the memo that says
   what changed. That must cost days, not weeks, which is why
   constraint 1 exists. Cadence is a scope decision the owner makes
   per release, never a schedule the project is bound to. A security
   fix in a pinned component is a reason to release: the agent
   prepares one and asks (owner, 2026-10-17).
6. **Review is a stage, not a courtesy.** Every built change is
   reviewed before it lands, by a reviewer who did not write it (a
   fresh agent or a person), who is given the specification and the
   change, not the author's summary. The reviewer re-runs the counted
   tests, checks each acceptance criterion against its evidence,
   checks the change against §4 and §7, and reports ranked findings.
   Each finding is fixed or answered in writing before the landing;
   the landing notes cite the review. A specification that changes
   the guest's imports or exports, the artifact set or the build
   recipe is reviewed once more before it is built, so a wrong design
   is caught before it is code. Reviews live in `context/reviews/`.
   Before each release, a fresh reviewer checks the release against
   the written threat model (`research/2026-10-16-a-principal-engineers-direction.md`,
   section 2) and the changes since the last release; the release
   waits on its findings (owner, 2026-10-17).
7. **One landing lane.** Builders and reviewers may work in parallel,
   each in its own worktree. Main changes in one place only: the lane
   rebases one reviewed branch onto main, compares it with what was
   reviewed, runs the full judge on that exact commit in the main
   tree, accepts there, and fast-forwards main. Only the lane accepts.
   A change to the build recipe overlaps no other change to the build
   recipe (owner, 2026-10-17).

## 6. Deciding when the rules do not say

When a choice is not covered here or in a specification, the agent
decides by these, in order:

1. **Does it keep the wall whole?** Anything that lets the guest reach
   the host by a third way is refused.
2. **Does it keep the build reproducible, with as few patches as it
   can?** Prefer a recipe file over a patch, a pin over a floating
   version, and a patch only as §4.1 allows it: reviewed, recorded,
   matched by an upstream pull request, and temporary.
3. **Does it work on every WASI host the same way?** Prefer the plain
   WASI form over the clever host-specific one.
4. **Is it the smallest thing that meets the specification?** Prefer
   fewer files, fewer dependencies, fewer artifacts.
5. **Would the owner recognise it as this project?** A basic, sealed,
   portable Python with the data stack inside, released as a few
   pinned sets. If the
   choice pulls toward a development environment, a browser runtime
   or an application, it is wrong.

If the choice is still open after these, it is the owner's, and the
agent writes a placeholder memo and moves to work that does not depend
on it.

## 7. What an autonomous agent must never do here

- Patch an upstream source tree outside §4.1: a change not carried as a
  reviewed patch file under `recipes/patches/` with its upstream pull
  request drafted, or any edit made by hand in `build/`.
- Add an import to the guest binary beyond WASI preview1 and the door.
- Fetch anything unpinned, or install a download into the system.
- Copy code from `context/prior_art/` or any other project.
- Commit, push, tag, publish a release, upload to PyPI, or make a
  branch or worktree beyond §4.14's, without the owner's explicit
  instruction for that action.
- Report a build, a run or a number it did not execute.
- Leave an open question in a specification, or a question list
  anywhere.
- Widen the scope past §2 and the ordered list that follows it.

## 8. One line

Build one sealed, portable Python with the data stack inside, from
pinned sources with only recorded, temporary patches, prove every claim
by running it, and
release a new pinned set only when there is a reason to.
