# Design decisions

This page records six decisions that shape wasi-python, each with its context, the decision and
what follows from it. Read it to understand why the product behaves as it does, or before you
propose to change one of them.

## Fuel, not time, measures work

**Context.** The project needs to know when a change makes the guest slower, and users need a
way to stop runaway code. Wall-clock time answers both badly: the same program takes a
different time on a different machine, or on the same machine under load.

**Decision.** Work is measured in *fuel*: wasmtime's count of the wasm instructions the guest
executes. The project's tests assert fuel counts and never time a run. Users can cap a call's
fuel beside its deadline.

**Consequences.**

- A fuel limit stops the same program at the same place on every machine.
- A slowdown shows up as more fuel, so it can be caught by a test that never reads a clock.
- Fuel is wasmtime's own accounting, so counts compare only on one wasmtime version.
- Fuel cannot stop a guest that only waits, so every call still has a deadline by default.

See [fuel](fuel.md).

## Nothing is writable by default

**Context.** wasi-python is made for code nobody reviewed, such as a model's. Whatever a guest
can write, it can fill, plant files in, or leave behind for a later call.

**Decision.** A call given no root and no grants has nothing writable: no folder, no `/tmp`, and
a `HOME` it cannot write. Every channel to the host, writable folders included, opens only by an
explicit argument. Every limit has a default. A change that loosens a default needs the
maintainer's explicit decision, not only a review.

**Consequences.**

- A program that writes files fails with `OSError` until you give it a place: `root=True` for a
  fresh private folder, or a writable grant.
- Granting write access is a visible choice in your code, never an accident.
- The runtime's own files are never in a writable grant.

See the [security model](security-model.md).

## A few pinned releases

**Context.** Python's ecosystem has many versions of many packages. Building every combination
for WASI could not be tested whole, and each package needs care to build for the guest.

**Decision.** A release is one pinned set of versions, built from sources pinned by URL and
hash. A new set is built when there is a reason, and older sets stay published.

**Consequences.**

- Every package in a set runs its own tests inside the guest before release.
- You choose a set, not package versions. There is no pip inside the guest.
- A new release is a re-run: re-pin, rebuild, re-test, publish.

See [pinned releases and patches](pinned-releases-and-patches.md).

## Embedder-neutral code

**Context.** A runtime like this is usually built for one program that needs it first. Code
written for that one program tends to leak into names, defaults and tests, and the next
embedder pays for it.

**Decision.** No code, name, default or test in the repository refers to a particular embedder.
Every embedder gets the same thing.

**Consequences.**

- Features arrive as general mechanisms that any host can use: grants, mounts, the host door
  and its tool protocol, sessions.
- The guest's interface to the host is the same for a Python program, a Rust program or a
  command-line caller.

## The snapshot pre-imports no package

**Context.** The snapshot starts each call from a saved, already-started interpreter. Saving
numpy and pandas in it made a pandas call cheap. But it made every other call pay to tear that
stack down, made each live instance larger, and grew the wheel. Saving every package would keep
growing the wheel as packages were added, toward PyPI's size limit. Saving only some packages
would treat packages unequally.

**Decision.** The default snapshot pre-imports only the standard library's bootstrap modules,
for every package now and later.

**Consequences.**

- A call pays for exactly what it imports, when it imports it, and nothing for the rest.
- Packages import in your call, with your environment, not the build's.
- A call that imports pandas pays for that import. To pay once across several steps, use one
  call or a [session](sessions.md).
- A profile that pre-imports the data stack would be its own artifact set, built only if an
  embedder asks.

## Builtin modules, not shared libraries

**Context.** A normal CPython loads C extensions as shared libraries. WASI has no `dlopen`, so
a guest cannot load a shared library at run time, and the guest's interface to the host stays
at WASI and one door.

**Decision.** Every compiled module is linked into the interpreter as a builtin module. A
compiler wrapper turns each package's shared-library link into a static archive, so the
packages' own build files stay unchanged.

**Consequences.**

- The product is one static binary per profile, with no install step inside the guest.
- Two packages that define the same symbol clash only in this static link; a recipe file
  renames one side.
- Adding a package means rebuilding the binary. Profiles stay few, and each is its own artifact
  set, never assembled on a user's machine.

See [how it works](how-it-works.md).

## In one line

Measure work in fuel, open nothing by default, ship a few pinned sets, favour no embedder,
pre-import nothing, and link every package into one static binary.
