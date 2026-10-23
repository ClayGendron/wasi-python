# Principles

This page states what wasi-python is for and the rules every change keeps. It is an abridged version of the project's principles; the full rule book for contributors is [AGENTS.md](https://github.com/ClayGendron/wasi_python/blob/main/AGENTS.md).

## The mission

Any program that can host WebAssembly can run real Python, with numpy and pandas, inside a sandbox it fully controls, without a browser, a JavaScript engine, a kernel feature or a package install step.

One artifact. One wall. Every platform. A few pinned releases, not every version of everything.

## What a release must be

A release is ready when all of these are true, and each one is checked:

1. A statically linked `python.wasm` for `wasm32-wasip1`, with CPython and its packages compiled in as builtin modules, is published as a GitHub release and as the `wasi-python` wheel on PyPI, with a manifest and hashes.
2. It runs under wasmtime on Linux, macOS and Windows from the same bytes, with no host folder beyond the grants the embedder gives, no network, no shared library and no host process.
3. Every compiled-in package imports and works, and its results match native Python.
4. An embedder in any language with a wasmtime binding can run it by preopening the folders it grants, binding one host function and calling one export. A Python embedder does it in one call.
5. The whole thing rebuilds from pinned sources by a CI job anyone can run.

## What it is not

- **Not a development environment.** It is a sealed Python for light loads: an embedder runs a program and gets its result. No pip, no virtual environments, no package tracking. The `wasi-python run` command and bounded sessions are part of the runner, and add no power that `run()` does not have.
- **Not a browser Python.** Pyodide owns that.
- **Not a general wasm toolchain.** It builds one artifact well.
- **Not an application.** It ships no filesystem, shell, agent or server; those belong to the programs that embed it.
- **Performant, not the fastest.** It is correct, portable and sealed first, and it stays close to native. The cost against native Python is measured, documented and never hidden.

## The hard constraints

These are not preferences. A change that breaks one is wrong even if it works.

- **Every input is pinned.** Every source, toolchain, tool and dependency is a URL and a SHA-256 hash, verified before use. Downloads are untrusted: they unpack only under the build's own folders and run only as build tools or as guests.
- **Upstream patches are few, recorded and temporary.** An adaptation is a recipe file first. An unavoidable source change is a reviewed patch file, hashed in `MANIFEST`, named in the changelog, matched by a drafted upstream pull request, and deleted once upstream ships the fix. See [pinned releases and patches](../explanation/pinned-releases-and-patches.md).
- **One target: `wasm32-wasip1`.** No Emscripten, no JavaScript, no host-specific branch. What cannot be done inside WASI is left out and documented.
- **Two channels to the host.** The guest reaches the host through the WASI preview1 calls and one custom import, the host door. No third import, ever.
- **Embedder-neutral.** No code, name, default or test refers to a particular embedder. Every embedder gets the same thing.
- **The artifact set is the product.** The plain reactor, the snapshot, the stdlib zip, `MANIFEST`, `SHA256SUMS` and the licence notices. Nothing compiled per host is published.
- **Artifacts never live in git.** Binaries, zips and build trees are ignored; their hashes and sizes are recorded instead.
- **Prior art is studied, never copied.** Other projects are read and cited, never pasted. Every line in the repository is original. Building a dependency from its released source is not copying.
- **Tests count operations, never time.** A test asserts operation counts, exit codes, bytes and equality with native results. Speed is a benchmark fact, recorded separately. A test that measures time is a bug.
- **Claims carry their evidence.** Every number in a document comes with the command that produced it.
- **Platform facts are documented, not disguised.** The 32-bit default integer, the missing threads and modules, and the speed ratio are all stated.
- **Licences ship with the artifact.** Every component's notice is inside the release and the wheel, and nothing with an unapproved licence is linked in.
- **uv only.** `uv run` and `uv sync`, never a bare `python` or `pip`. `ruff check`, `ruff format --check` and `pytest` stay green.
- **Safe by default.** Every limit has a default. No channel to the host opens without an explicit argument. A call given no root and no grants has nothing writable.
- **Nothing lands unreviewed.** Every built change is reviewed by someone who did not write it. See [review and landing](review-and-landing.md).
- **Code speaks for itself.** A comment or docstring gives its reason in words. Code never points into the project's internal records to explain itself.

## How work is done

Work moves through five stages: study, research, specify, build, review. Nothing is built that no specification describes. No specification is written on a question no research has answered. Nothing lands that no review has passed.

A specification decides every choice it needs and says why. Research has a time box; at the box, the researcher stops and records where it stood. A landing is small, finished and verified: one change, green, with its numbers reproduced.

The choices these rules lead to, and their reasons, are in [Design decisions](../explanation/design-decisions.md).

## When the rules do not say

Decide by these questions, in order:

1. Does it keep the wall whole? Anything that lets the guest reach the host by a third way is refused.
2. Does it keep the build reproducible, with as few patches as it can?
3. Does it work the same way on every WASI host?
4. Is it the smallest thing that meets the need: fewer files, fewer dependencies, fewer artifacts?
5. Is it still this project: a basic, sealed, portable Python with the data stack inside? A choice that pulls toward a development environment, a browser runtime or an application is wrong.

## In one line

Build one sealed, portable Python with the data stack inside, from pinned sources with only recorded, temporary patches; prove every claim by running it; release a new pinned set only when there is a reason to.
