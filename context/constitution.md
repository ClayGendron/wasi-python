# Constitution

- **Status:** in force, 2026-10-16; amended the same day by the owner's
  decision on profiles and on what the product is for (§2 "Beyond v1",
  §3 first bullet); amended 2026-10-17 by the owner's answers to
  questions 1, 3, 4, 5, 7 and 9 (`questions-for-the-owner.md`): typed
  grants that may be none (§2.2, §2.4), the build order after v1 (§2),
  a command line inside the runner (§3), safe by default (§4.15), three
  approved licences (§4.12), and the release rules (§5.5, §5.6)
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

Version 1 is reached when all of these are true:

1. A statically linked `python.wasm` for `wasm32-wasip1` with CPython,
   numpy and pandas compiled in as builtin modules is published as a
   GitHub release and as the `wasi-python` wheel on PyPI, with a
   manifest and hashes.
2. It runs under wasmtime on Linux, macOS and Windows from the same
   bytes, with no host directory beyond the grants the embedder gives
   (read-only or writable folders, which may be none), no network, no
   shared library and no host process.
3. `import numpy` and `import pandas` work; a CSV read, a groupby and
   a CSV write run inside it; the result matches native Python.
4. An embedder in any language with a wasmtime binding can run it by
   preopening the folders it grants (possibly none), binding one host
   function and calling one export. A Python embedder does it in one
   call through the wheel.
5. The whole thing rebuilds from pinned sources by a CI job anyone can
   run, with zero patches to any upstream tree.

Beyond v1, in order of value: matplotlib, then the stdlib modules WASI
lacks (sqlite, bz2, lzma), then scipy. Nothing else is in scope until
those are decided. By the owner's decision (2026-10-17) the cheaper
sqlite3, bz2 and lzma are built first, while matplotlib waits on typed
grants; matplotlib's data is a read-only grant (C2).

Also beyond v1, by the owner's decision (2026-10-16): **build-time
profiles of the core C libraries**, so an embedder carries only the
compiled libraries it uses (a CPython-only core, and a data profile
with numpy and pandas, for example). C extensions are linked in at
build time on `wasm32-wasip1`, so a profile is its own artifact set,
chosen by name, never assembled on a user's machine. Profiles stay
few: each one is built, judged and published. v1 ships the one set
§2 names. The question is held by
`research/2026-10-16-build-time-profiles-of-the-core-c-libraries.md`.

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
  power `run()` does not have (owner, 2026-10-17).
- Performant, not the fastest. It is correct, portable and sealed
  first, and it stays close to native: the penalty against native
  Python is measured on every release, documented, never hidden, and
  never the reason to break another rule. A build that gets slower
  than the last one without a stated reason is a regression.

## 4. Hard constraints

These are not preferences. Work that violates one is wrong even if it
works.

1. **Zero upstream patches.** No file in a CPython, numpy, pandas,
   zlib or any other source tree is modified. An adaptation is a
   recipe file: a cross file, a compiler wrapper, a rename header, a
   stand-in module, a linker flag. If a source change is unavoidable,
   it is sent upstream and the project waits or ships without the
   feature. The release workflow fails on any diff against the pinned
   tarball.
2. **Every input is pinned and hashed.** Every source tarball,
   toolchain, tool and pure-Python dependency is a URL plus a SHA-256
   in `downloads/SHA256SUMS`, verified before use. A build that fetches
   anything unpinned is not a build.
3. **One target: `wasm32-wasip1`.** No Emscripten, no JavaScript, no
   native code path, no host-specific branch. If something cannot be
   done inside WASI, it is left out and documented.
4. **The guest reaches the host through exactly two things:** the
   WASI preview1 calls and one custom import, the host door. No third
   import, ever. The door's frames are opaque to this project; what
   they mean is the embedder's.
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
    (BSD-style) and liblzma from xz (0BSD).
13. **Tooling.** `uv` only. `ruff check`, `ruff format --check` and
    `pytest` green on `src/` and `tests/` before any landing. No
    dependency added to `pyproject.toml` without a reason written in
    the specification that needs it.
14. **Git.** Commit or push only when the owner asks. No branches or
    worktrees unless asked. Never `git checkout`, `git restore` or
    `git stash` a file carrying uncommitted work.
15. **Safe by default.** Every limit has a default (memory, time,
    output); no channel to the host opens without an explicit argument
    (no folder, no network, no host function); the runtime's own files
    are never in a writable grant. A change that loosens a default
    needs the owner's decision, not only a review (owner, 2026-10-17).

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

## 6. Deciding when the rules do not say

When a choice is not covered here or in a specification, the agent
decides by these, in order:

1. **Does it keep the wall whole?** Anything that lets the guest reach
   the host by a third way is refused.
2. **Does it keep the build reproducible and patch-free?** Prefer a
   recipe file over a patch, a pin over a floating version, leaving a
   feature out over bending constraint 1.
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

- Patch an upstream source tree, even "temporarily".
- Add an import to the guest binary beyond WASI preview1 and the door.
- Fetch anything unpinned, or install a download into the system.
- Copy code from `context/prior_art/` or any other project.
- Commit, push, branch, tag, publish a release, or upload to PyPI
  without the owner's explicit instruction for that action.
- Report a build, a run or a number it did not execute.
- Leave an open question in a specification, or a question list
  anywhere.
- Widen the scope past §2 and the ordered list that follows it.

## 8. One line

Build one sealed, portable Python with the data stack inside, from
pinned sources with no patches, prove every claim by running it, and
release a new pinned set only when there is a reason to.
