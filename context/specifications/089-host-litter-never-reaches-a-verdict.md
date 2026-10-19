# 089 — host litter never reaches a verdict: the judge seals its stages and watches its grants

- **Status:** **drafted 2026-10-19** on `spec/089-host-litter-never-reaches-a-verdict` from main
  `3866f56`. It changes neither the guest's imports nor its exports, the artifact set nor the
  build recipe, so §5.6 asks no review before build; a fresh agent reviews the specification while
  it is built, then the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** a judge change; **parallel-safe**, not build-class (§5.7). New
  `tests/harness/litter.py`, `tests/unit/test_host_litter.py`; edits to `tests/harness/guest.py`
  (`run`, `mpl_data_dir`), `tests/harness/regrtest.py` and `tests/harness/upstream.py` (each
  `Session`), `tests/checks/conftest.py` (the `guest_workdir` fixture), and one new check in
  `tests/checks/test_v1_4_embedding.py`. No `src/`, `scripts/`, `recipes/`, `downloads/`, workflow
  or README. It moves no accepted fuel (criterion 4): the lane accepts it with `--accept-judge`.
- **Depends on:** nothing unlanded. **It lands before spec 083** (the lane's order, with the
  owner's agreement, 2026-10-19): main's serial judge cannot run cleanly while a desktop process
  writes into the stages, and 083's landing waits on exactly that. **083 then rebases onto it**;
  their only shared file is `tests/harness/guest.py`, where 089 adds a few lines around the
  preopens and before `run()` returns, and 083 adds its call shadows; the merge is textual.
- **Research it stands on:** `../research/2026-10-19-ds-store-in-the-judges-stages.md` (EXECUTED:
  the writer, the probe, the six trials, `prototype.diff`). Spec 083's build review, last addendum
  (the `.DS_Store` files in `build/harness/cpython/run-*` mid-run).

## The problem

The ratchet holds fuel to one part in ten thousand, and the lane's sameness check stops a landing
on any difference between a builder's `-n 3` record and its own serial one. So fuel must depend
only on the artifact and the check.

macOS writes `.DS_Store` files, as the user, into folders that something sizes: on the owner's
Mac, System Settings' storage scan and Finder (the memo, §1). They land in the judge's live
stages. Spec 083's build review caught `build/harness/cpython/run-*/.DS_Store` and
`…/lib/.DS_Store` appearing mid-run; `cpython-a`, `-c` and `-archives` moved by up to 1.6e-3 from
run to run, in the main tree only. That stopped 083's landing.

The judge did not notice. A simulated writer on a scratch clone's stage moves `cpython-archives`
from 164,648,434,127 to 164,609,014,815 (−2.4e-4), and the check **passes** (the memo, trial r3).

## Principle

A file a host process drops into a folder the guest sees is either **refused** (it cannot land) or
**named** (the check fails, saying which file). It is never measured, and never hidden: nothing is
filtered from what the guest sees.

## Decisions

1. **Litter, by name.** `litter.is_litter(name)`: `paths.OS_LITTER` (spec 011's three:
   `.DS_Store`, `Thumbs.db`, `desktop.ini`), AppleDouble files (`._` prefix), `Icon\r`, and the
   volume-root names `.Spotlight-V100`, `.fseventsd`, `.Trashes`, `.TemporaryItems`,
   `.DocumentRevisions-V100`, `.apdisk`. `paths.OS_LITTER` itself is not changed here (the build
   shares it through a unit check; spec 090 widens both).
2. **Seal every read-only stage.** Once a stage is written, every folder in it loses its write
   bits (`litter.seal`). No process of the user's can add, remove or rename an entry (EXECUTED: the
   real writer and the simulated one are both refused by a 0555 folder). Folder modes do not reach
   a WASI guest: a filestat carries no mode, and wasmtime opens a read-only grant read-only either
   way. Sealed:
   - the CPython stage (`regrtest.Session`, at the end of `_prepare`, after `judge/`);
   - the upstream stage (`upstream.Session`, once its first `prepare` has staged every package);
   - matplotlib's data (`guest.mpl_data_dir`, after extraction; shared by a session's runs).

   Not sealed: writable roots (the guest writes there) and the per-run stdlib folder (made just
   before one run; Decision 3 watches it). On Windows a folder's mode does not stop a write, so
   nothing is sealed there and Decision 3 alone holds; no desktop writer is known there.
   - **Litter that lands while a stage is written** (EXECUTED: 172 files in the 2 s of staging)
     is removed by `seal` after every folder is closed: each file's folder is opened for its
     unlink alone, and the scan repeats until clean (ten rounds at most, then `HostLitter`). It
     was never staged and no guest has run, so this hides nothing from a guest.
   - **No symlink anywhere.** `seal` changes modes in place, on the real folders `mkdtemp` made
     under `paths.HARNESS_TMP`. It never moves a stage or links to one (the first attempt's
     lesson 1, below).
3. **Unseal, then remove, and retry.** `litter.remove(root)` gives every folder its owner's write
   bit back, removes the tree, and tries again (five times at most) if a writer refilled a folder
   between rmtree's unlinks (EXECUTED: today's `shutil.rmtree(…, ignore_errors=True)`, racing the
   writer, left a stage behind, silently). `regrtest.Session.close`, `upstream.Session.close` and
   the `guest_workdir` fixture call it.
4. **Watch every guest run.** `guest.run` builds a `litter.Watch` over the grants it preopens,
   just before it preopens them, and checks it just before it returns:
   - no grant holds a litter entry, before the run or after it;
   - a read-only grant lists exactly the same entries after the run as before (any file, litter or
     not).

   A failure raises `litter.HostLitter`, an `AssertionError` naming each file by its guest path and
   where such files come from. The check fails and records no fuel. Nothing is retried. The cost is
   one `os.walk` per grant before and after a run; the CPython stage has 178 folders. `Turns`
   (multi-call instances) is not watched here: its grants are a root, the stdlib folder and a
   check's own, and none is a stage.
5. **The check that proves it.** `test_a_file_dropped_into_a_stage_changes_nothing`
   (`test_v1_4_embedding.py`, both binaries): it stages a folder of a few files under the guest
   workdir as the harness stages one (`litter.seal`), tries to drop a `.DS_Store` into every folder
   of it as a desktop writer would (a refusal is the expected outcome), then runs a program that
   lists each of the stage's folders at `/stage` by name (`os.listdir`, which reads no inode
   number or time, so the comparison holds before 083 too) and prints the listings, and compares
   with the same program on a twin stage no writer touched: the same exit, the same output, the
   same fuel, and no `.DS_Store` in the stage. On main, it fails (there is no `litter` module, and without the
   seal the dropped files are listed and the fuel moves).

## Intent

No file a host process drops into a folder the guest sees can change a verdict or a fuel value,
whichever process writes it: a read-only stage refuses it, and any grant that changes anyway fails
its run, naming the file.

## Design

`tests/harness/litter.py` holds the litter names, `seal`, `unseal`, `remove` and `Watch`. The two
`Session`s seal their stages when staged and remove them through `litter.remove`; `mpl_data_dir`
seals the data it extracts; the `guest_workdir` fixture removes through `litter.remove`. `guest.run`
builds its `Watch` from the exact list it preopens, before the preopens, and calls `after()` once
the run has ended, before it returns its `Result`. The new check stages two small folders the same
way and compares them.

### What the first attempt taught

- **A mitigation is tried on the whole fast tier before it is called working.** The research
  proposed a symlinked `build/harness` outside the home folder for 083's rerun, from one CPython
  group. The lane tried it: 87 runner and session checks failed, because the product runner
  refuses a root that passes through a symlink in a user-writable folder. So this spec's seal uses
  no symlink anywhere in a stage's path (Decision 2), and its build runs the full judge.
- **Immunity, whoever writes.** The writer was identified only far enough to know it runs as the
  user and respects folder modes. The seal does not depend on which process it is, and the watch
  names whatever gets past the seal (a root process, a Windows host).
- **Link counts.** A shared artifact set reached nlink 151 after a killed run (spec 039), and link
  counts reach fuel. The build judges a private `cp -c -Rp` copy of the set with every file at
  nlink 1, and never touches the main tree's `build/`; `paths.HARNESS_TMP` is the worktree's own.
- **Parallel and serial alike.** The lane's sameness check compares the reviewer's `-n 3` record
  with its serial one; 083's difference came from this litter. Nothing in 089 depends on worker
  count: every stage, mpl-data folder and watch belongs to one process.

## Scope

In: Decisions 1 to 5. Out, to spec 090: the build's walks, the release tarball, the artifact-folder
checks, `OS_LITTER`'s widening, `.gitignore`. Out, to a follow-up: a third watch, a litter name
handed to the guest by `fd_readdir`, which needs a readdir shadow; 083's rebase adds it (its
`FileFacts.listing` already walks every entry), or a later spec does. Out: which process writes
the files; the product runner's grants.

## Acceptance criteria

1. **The checks fail first.** On main `3866f56`: `test_a_file_dropped_into_a_stage_changes_nothing`
   fails on both binaries, and every row of `tests/unit/test_host_litter.py` fails (no module).
   The landing notes give the failure lines.
2. **The unit rows.** With the build, `tests/unit/test_host_litter.py` passes: litter names (yes
   and no rows); a sealed stage refuses a write in every folder; `seal` removes what landed while
   staging and returns it; `remove` removes a sealed tree; the watch names litter before a run, any
   new entry in a read-only grant (a non-litter `stray.py` included), and litter in a writable root
   after a run, and passes a writable root the guest changed.
3. **The drop check passes,** on both binaries, and the stage holds no `.DS_Store` after it.
4. **Nothing moves.** `ruff check` and `ruff format --check` green. The fast tier `-n 3`, then the
   full judge once (`-n 3`), against a private copy of `build/sets/s-c50ca51fae5eb55b-c9dcb5b8`
   (every file nlink 1, checked before the run): no failure, no lost pass, **no accepted fuel row
   moved past its tolerance**; the ratchet shows the new check's rows as gained and
   `judge changed`. The landing notes give the record's path and the counts.
5. **Cleanup.** After the full judge, no `run-*` stage is left under the worktree's
   `build/harness/cpython` or `build/harness/upstream`, and no folder under `build/harness` lacks
   its owner's write bit.
6. **The upstream groups** (CPython a, b, c, fs, archives; numpy's and pandas'), when their trees
   are present in the worktree, pass at their accepted fuel. If the build cannot run them (no
   trees), the landing notes say so and the lane's serial judge is their measurement.

## Landing notes

Not built yet.

One line: the judge seals every stage it grants read-only and fails any run whose grants change,
so a file a desktop process drops is refused or named, never measured.
