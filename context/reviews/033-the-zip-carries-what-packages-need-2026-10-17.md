# Review of 033 — The zip carries what packages need (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change, the specification,
  or its pre-build review and confirmation. I read `AGENTS.md`, the constitution, specification
  033 with its landing notes, its pre-build review with the confirmation and the author's note,
  and the diff (`git log -p main..HEAD`). Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** commits `e58f4f3` and `b25a61d` on `spec/033-the-zip-carries-what-packages-need`,
  in the worktree `../wasi_python-033`: `scripts/make_stdlib_zip.py`, `scripts/steps/70_zip.sh`,
  `recipes/ctypes_stand_in/{__init__,_types,util}.py` (new), `recipes/ctypes_stub.py` (deleted),
  `tests/checks/test_v1_3_data_stack.py`, `tests/unit/test_build_scripts.py`, `README.md`,
  `CHANGELOG.md` and the specification.
- **Ran (EXECUTED, darwin-arm64, uv, wasmtime-py 49, in the worktree only).** Work is under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/033-buildreview/`.
  `$OLD` is the implementer's saved set `scratchpad/033-old/`. Its non-licence `SHA256SUMS` lines
  equal main's frozen set `build/sets/4befe9de64edc783/` (`diff`, empty).
  - `scripts/build.sh --plain 70_zip 80_snapshot 90_artifacts` (`rerun-70-90.log`). Then `cmp`
    with the `SHA256SUMS` saved before it: the same file.
  - The full judge, `uv run pytest`, no flags, against the worktree's `build/artifacts`
    (`judge.log`). `growth.py` compares its `latest.json` with the branch's and main's
    `accepted.json` (`growth.txt`). `uv run ruff check src tests` and
    `uv run ruff format --check src tests`.
  - Criterion 2's commands as written (names, shared members, the five `cmp`s), and `MANIFEST`
    and `SHA256SUMS` against `$OLD`.
  - Criterion 3's litter re-run: a `.DS_Store` in `build/pandas-install/pandas/`, in
    `build/numpy-install/.../site-packages/numpy/`, and beside each `PKG-INFO`. Then steps 70 to
    90 and `cmp` (`litter.log`). The four files were removed after.
  - The two new guest checks against `$OLD` (`old-failfirst.txt`).
  - Fourteen unit mutants (`tools/unit_mutants.sh`, `unit-mutants.txt`). Each one patches one
    literal string, runs the four unit checks, copies the original back, and confirms
    `git diff --stat` is empty.
  - One guest mutant (`gm/`), rebuilt with steps 70 to 90 and judged with the two guest checks.
    It changes three things in `_types.py` (the big-endian twin's dtype code `>` to `<`; `c_size_t`
    picked at 8 bytes; `c_wchar` sized 2) and drops pandas' `--metadata` line. Then the originals
    were copied back and steps 70 to 90 re-ran: `SHA256SUMS` equal to the one before (`cmp`).
  - Fuel probes through the judge's own driver, `$OLD` against the new set
    (`tools/probe.py`, `probe-noise.tsv`, `probe-nogc.tsv`, `probe-meta.tsv`).
  - Guest and host probes of the stand-in under introspection (`introspect_guest.py`,
    `introspect-guest-snap.txt`, `pydoc_guest*.py`, `pydoc2-*.txt`, `tools/host_introspect.py`).
    A host prototype of the fix for finding 1 is in `proto/`.
  - `git merge-tree --write-tree main HEAD`: exit 0, no conflicts.
  - The worktree is clean after all of it (`git status --short` empty). My subset runs rewrote
    the worktree's `build/progress/latest.json`, so I put the full run's copy back
    (`latest-full.json`). I never passed `--accept` or anything that writes `context/progress/`.
    No commit, stage, checkout, restore or stash. In the main tree I wrote only this file.

## The judge

- **Full judge (EXECUTED, `judge.log`).** `779 passed, 11 skipped`. `wasi_python v1: 196/200
  pass · 0 gap · 4 blocked · 0 fail (unit suite 583/590, 7 skipped)`. `ratchet vs f7b8df25de:
  lost 0 · absent 0 · unrun 0 · unrun locally 2 · gained 4 · grew 39 · judge changed:
  tests/checks/test_v1_3_data_stack.py, tests/unit/test_build_scripts.py`. `RED: 39 metric(s)
  grew`, as expected before an acceptance. This matches the landing notes' scoreboard line for
  line.
- **Growth (EXECUTED, `growth.txt`).** Every one of the 39 numbers matches the landing notes'
  table. Main's `accepted.json` has the same value for every check, except `numpy_csv`, which
  differs by 68 fuel. So the rebase moves no baseline.
- **Ruff (EXECUTED).** `All checks passed!`; `55 files already formatted`. Out of scope but
  noted: `scripts/make_stdlib_zip.py:9` is an E501 that is already on main. The four files
  `ruff format` would change under `scripts/` and `recipes/` are all already on main. The new
  recipe files are clean.
- **Determinism (EXECUTED).** Steps 70 to 90 re-run give the same `SHA256SUMS`. With litter they
  give it again, and again after the guest mutant was restored.

## Findings, most severe first

### 1. Medium — `help(ctypes)` and `np.info` on a C type now raise `OSError` whenever numpy is loaded. That means every snapshot call. This is a regression

The refusing `__numpy_dtype__` (`_Refused`) sits on `_CData`, the base class of every stand-in
type, the simple ones included (`_types.py:58-62`). `_SimpleCData` overrides it for its own
subclasses. But introspection tools also read the attribute on the bases:
- `inspect.classify_class_attrs` (`inspect.py:617`, READ in `build/Python-3.15.0/Lib`) calls
  `getattr(base, name, None)` on every class in the MRO;
- `pydoc.allmethods` recurses into `__bases__`.

`getattr(…, None)` only catches `AttributeError`, so the `OSError` escapes.

EXECUTED in the guest:
- **The snapshot, old against new** (`probe-meta.tsv`). `import ctypes, pydoc;
  pydoc.render_doc(ctypes)` exits 0 on `$OLD` and exits 1 on the new set. The traceback runs
  `pydoc.docclass` → `classify_class_attrs` → `inspect.py:617` → `ctypes/_types.py:33`.
  `help(ctypes)` fails the same way (`pydoc2-snap.txt`).
- **With numpy loaded.** On the snapshot, `pydoc.render_doc(numpy.ctypeslib)` raises the
  `OSError` (`introspect-guest-snap.txt`). On the plain binary after `import numpy`, so does
  `np.info(ctypes.c_int)` (`pydoc_guest.py`). It goes through `pydoc.allmethods` →
  `getmembers(_CData)`.
- **The plain binary before numpy loads.** `help(ctypes)` works there, because `_NumpyDtype`
  raises `AttributeError` and the base is never searched. The bug therefore shows exactly where
  numpy is present: always on the snapshot.

Today's one-function stub documents fine. So this change takes away `help()` on a stdlib module
that numpy and pandas import, in the binary embedders use most. That is the kind of call an agent
makes when it explores. Nothing in the specification asks for it. Decision 5 puts the refusing
attribute on "every other stand-in type", not on the shared base.

**Fix (prototyped on the host, EXECUTED: `proto/fixed/_types.py` against `proto/asis/`, with a
stand-in `numpy` module in `sys.modules`):**
- Move `_Refused` from `_CData` to a new intermediate base, for example `_NoLayout(_CData)`.
  `Structure`, `Union`, the array, pointer and function types derive from it.
  `_SimpleCData` stays on `_CData`.
- Make `_NumpyDtype.__get__` return the descriptor itself when it is read on `_SimpleCData`
  itself (`if cls is _SimpleCData: return self`). Then `pydoc.allmethods(c_long)` can read it.

With both changes: `pydoc.render_doc(ctypes)`, `pydoc.render_doc(c_long)` and
`pydoc.allmethods(c_long)` succeed with numpy loaded. Every refusal still holds:
`S.__numpy_dtype__`, `(c_int * 2).__numpy_dtype__`, `POINTER(c_int).__numpy_dtype__` and
`CFUNCTYPE(None).__numpy_dtype__` raise the `OSError`. Today's version fails all three
introspection calls.

**Add a check.** Put these steps in the `CTYPES` program after numpy is imported, on both
binaries: `pydoc.render_doc(ctypes)`, `pydoc.render_doc(ctypes.c_int)` and `np.info(ctypes.c_int)`
(print to a `StringIO`) do not raise. See them fail on `b25a61d` first. Add a unit case that
loads the package with a stand-in `numpy` in `sys.modules`, as `proto/` does. The zip and the
snapshot change, so re-run steps 70 to 90 and the judge, and re-take criterion 4's account.
INFERRED: the fuel moves very little, because no heavy check builds the types.

### 2. Medium — criterion 4 is not met on two checks as written. The cause is noise, not a regression. Amend the criterion; do not change the code

The two checks over their caps (EXECUTED, `growth.txt`, the same numbers as the landing notes):
- `test_uncaught_errors_print_as_native[plain]` (`1/0`, 670.7 M): +624,482 against ≤ +0.6 M;
- `test_stdlib_debugging_tools_import` (snapshot, 535.1 M): +215,125 against ≤ +0.2 M.

Criterion 4 says a growth above a cap "is a finding for the build review, not a reason to
accept". So the lane cannot just state an `--accept-growth` reason over it. Either the criterion
changes, recorded as a change, or the code does.

**A smaller stand-in would not help.** On the plain binary, `1/0` never imports `ctypes`. The
debugging-tools program never builds the types (EXECUTED: in a snapshot call,
`'c_long' in vars(ctypes)` is `False` and `ctypes._types` is not loaded). What both pay is the
seven members on every start, about +0.54 M plain and +0.07 M snapshot, plus noise.

**What the noise looks like (EXECUTED, `probe-noise.tsv`).** I ran each program on both sets
with an unrelated heap perturbation first: `_k = [object() for _ in range(K)]`.

| program | K = 0 | 10 | 100 | 1000 | 3000 | mean | cap |
|---|---|---|---|---|---|---|---|
| `1/0`, plain | +624,397 | +492,311 | +623,795 | +489,215 | +495,196 | +544,983 | 0.6 M |
| `import pdb, pydoc, doctest`, snapshot | +215,074 | +77,600 | +198,047 | −47,716 | −71,710 | +74,259 | 0.2 M |
| `-c pass`, plain / snapshot | +541,683 / +67,223 | | | | | | |

The growth moves by about 135 K (plain) and 287 K (snapshot) when nothing related to this change
moves. The means equal the per-start cost of the seven members. The same program on 1.5 G of
plain fuel moves from +449,528 to +1,014,722. So the confirmation's absolute caps were right for
`-c pass`-sized programs, which stay within 35 K of each other here (+530,461 to +565,359 over 11
checks). They are too tight for programs of 0.3 to 1 G that allocate heavily. `gzip_round_trips`
(477 M, +592,049) sits just under the same cap.

**The amendment to write into criterion 4** (the author's edit, recorded in the Status line and
in the Disposition, citing this finding):

> A check above 300 M fuel that exceeds its absolute cap (the ≤ +0.6 M plain row or the
> ≤ +0.2 M snapshot row) is within the criterion when the account shows, for that check, its
> program run on both sets five times: once as is and once each with `_k = [object() for _ in
> range(K)]` first (K = 10, 100, 1000, 3000). The mean of the five growths must be within the
> cap, and the stand-in's types must not be built. Programs at or below 300 M fuel keep their
> absolute caps unchanged.

This keeps a real regression visible. A real per-run cost moves the mean, and the mean is what
is capped. It also makes no exception for the two checks by name.

**For the lane, once finding 1 is fixed and the numbers are re-taken,** the `--accept-growth`
reason can be: *"spec 033: 7 more zip members, about +0.54 M per plain start and +0.07 M per
snapshot call; the zip +21 KB, the snapshot about −1 KB, python.wasm unchanged; every check
within criterion 4's caps as amended by review 033's finding 2 (uncaught_errors[plain] and
stdlib_debugging_tools_import are over the absolute caps by heap-layout noise; their
perturbation means are within them)"*. Use the re-measured numbers.

### 3. Low — "both shown to be the collector's timing" claims more than its evidence shows

The landing notes and the Status line give `gc.disable()` as the proof: −85,342 for the debugging
tools on the snapshot, and +460,162 for `1/0` plain. EXECUTED (`probe-nogc.tsv`): those numbers
reproduce exactly, but only for the one-line text `import gc; gc.disable(); …`. The same control
written on two lines (`import gc; gc.disable()\n…`) gives +194,628 and +546,311
(`probe-noise.tsv`, `dbg_nogc` and `err_nogc`). So with the collector off, the growth still moves
by 280 K with the program's text. The noise is the heap's layout in general. The collector is
part of it, not all of it, and `gc.disable()` is not a clean control.

**Fix:** in the Status line and the landing notes, say "heap-layout noise (the collector among
it)". Cite finding 2's perturbation series, not the `gc.disable()` pair. The heavy-check evidence
for `pandas_csv` and `numpy_csv` (a two-line tail moves the growth) stays as it is: it already
says "the collector's timing, as Decision 7 says", and it is the confirmation's wording.

### 4. Low — say the edge that remains, and the one refinement, in the specification and the README

Two things the specification did not say:
- **The edge** (EXECUTED in the guest and on the host). For a `Structure` or `Union` subclass, and
  for a pointer, array or function type:
  - `hasattr(t, "__numpy_dtype__")` and `inspect.getmembers(t)` raise the `OSError`;
  - so do pandas' `pd.api.types.pandas_dtype(t)` and `is_integer_dtype(t)`.

  These still work: `dir(t)`, `pydoc.render_doc(t)` (it catches `Exception`),
  `inspect.getmembers_static(t)`, `pickle`, `copy`, `pd.Series([t])` and `np.array([t])`
  (object arrays). `inspect.getmembers(np)`, `inspect.getmembers(np.ctypeslib)` and
  `inspect.getmembers(pd)` work.

  This is acceptable. It is what Decision 5 chose so that numpy never makes `dtype('O')`, and an
  `AttributeError` would let numpy do exactly that. But it is a fact about the platform (§4.11),
  so put one sentence in Decision 5's "The edges, stated" and one clause in the README.
- **The refinement.** Before numpy is loaded, a simple type's `__numpy_dtype__` raises
  `AttributeError`, so `hasattr` is `False`. That matches a real `ctypes` type, which has no such
  attribute. Write it into Decision 5 as one sentence, so it is the specification's choice and
  not only a landing note.

### 5. Informational — no change needed

- **`sdist_metadata` matches header names case-sensitively.** Core metadata headers are
  email-style, and their names are case-insensitive. A lowercase `name:` would stop the build
  with "needs exactly one Name: and one Version: header". That fails closed: the build stops and
  never writes a wrong member. Both pinned `PKG-INFO`s use the usual case (EXECUTED: the five
  `cmp`s). A whitespace-only continuation line in an old-style `Description:` header would also
  end the headers early. Again that only stops the build. If spec 023 meets either case, compare
  `key.lower()`.
- **Name normalization is right.** `re.sub(r"[-_.]+", "_", name).lower()` is the binary
  distribution format's folder rule, and it agrees with `importlib.metadata`'s own normalization.
  EXECUTED: `version("Python-Dateutil")` and `version("python_dateutil")` both answer
  `2.9.0.post0`, and the unit case turns `Foo.Bar-baz` into `foo_bar_baz`. The version is kept
  verbatim. `importlib.metadata` splits the folder name at its first `-` and reads the version
  from `METADATA`, so an unnormalized version could not misdirect a lookup (READ, INFERRED).
- **Step 90 lists recipe files from the git index, and stops on untracked ones.** This has been
  in `assemble_artifacts.py` since spec 003 (`8e3428a`, READ). It is deliberate, so that
  `MANIFEST` names exactly the tracked recipe set. A builder stages new recipe files before step
  90, as the landing notes say. It is not this change's.
- **Names the stand-in does not have** (`ArgumentError`, `alignment`, `c_voidp`, `py_object`,
  `c_buffer`, `BigEndianStructure`, `pythonapi`; EXECUTED on the host: `AttributeError`). Decision
  5's rule is "a name exists so that an import succeeds", and no importer it names needs these.
  The tier-A specification should add any its packages need. `except ctypes.ArgumentError` is
  the common one.

## The implementer's flags

- **The two caps:** finding 2. Amend criterion 4; do not change the code.
- **`__numpy_dtype__` raising `AttributeError` before numpy loads:** right, and closer to real
  `ctypes`. Write it into Decision 5 (finding 4).
- **The `OSError` from non-simple types under introspection:** acceptable for those types,
  stated (finding 4). It is not acceptable when it leaks into the simple types and the module
  through the shared base (finding 1).
  - numpy's own paths are fine (EXECUTED): `np.ctypeslib.as_ctypes_type` of a structured and a
    subarray dtype declares `struct` and `c_long_Array_3`; `ndpointer(np.int32)` and
    `getmembers` of it work; `nc.c_intp is c_long`; `as_ctypes` refuses.
  - pandas' `from_dataframe` refuses with the message (the check).
  - `dir()` always works.
- **Step 90 and the git index; case-sensitive `sdist_metadata`; name normalization:** finding 5.

## Mutants

- **Unit (EXECUTED, `unit-mutants.txt`). Each one kills exactly one of the four unit checks
  (`1 failed, 3 passed`), and each restore left `git diff` empty:**
  - `walk` keeps `.egg-info`;
  - the name is normalized with `-`;
  - two `Version:` headers pass;
  - the blank line no longer ends the headers;
  - `RECORD` is kept;
  - `entry_points.txt` is dropped;
  - a top-level `.egg-info` does not stop the build;
  - the builder is imported eagerly from `__init__`;
  - the refusing `__numpy_dtype__` is removed;
  - there is no `__rmul__`;
  - `CDLL(None)` is allowed;
  - `sizeof` of a non-stand-in returns `None`;
  - `POINTER` is not cached;
  - `in_dll` is allowed.
- **Guest (EXECUTED, `gm/mutant-judge.txt`). `4 failed`:**
  - the metadata check fails on both binaries with `PackageNotFoundError … pandas`;
  - the ctypes check fails on both binaries with exactly `sizeof(c_size_t): 8, want 4;
    sizeof(c_wchar): 2, want 4; dtype(c_int32 be): False, want True`.
- **The implementer's dtype mutant** (READ, `033-mutant/`) shows the `dtype('O')` failure that
  criterion 1 asks for. I did not repeat it.

## Each Decision against the code

1. **A wheel keeps `METADATA` and `entry_points.txt`.** READ: `wheel_members`. EXECUTED: the
   unit check, mutants `RECORD` kept and `entry_points.txt` dropped, and criterion 2's three
   wheel `cmp`s.
2. **`--metadata` from `PKG-INFO`.** READ: `sdist_metadata` and `main`'s loop; step 70 passes
   both files. EXECUTED: the `cmp`s, the unit check and its mutants.
3. **No tree brings metadata.** READ: `walk` skips both kinds of folder, and `main` calls
   `tree_members` for each `--tree`. EXECUTED: the unit check, the mutants, and
   `unzip -Z1 … | grep -c egg-info` is 0.
4. **Licences unchanged.** EXECUTED: the `LICENSES/` lines of `SHA256SUMS` equal `$OLD`'s.
5. **The stand-in.** READ: every name, alias rule, twin, factory and refusal is as written.
   EXECUTED:
   - the guest check;
   - the snapshot does not hold the built types (`'c_long' in vars(ctypes)` is `False`);
   - `import numpy, pandas` on the plain binary does not build them;
   - `multiprocessing.sharedctypes` imports;
   - `read_clipboard()` raises pandas' "could not find a copy/paste mechanism" error.

   One defect: the refusal sits on the shared base (finding 1).
6. **threadpoolctl deferred.** READ: nothing named `threadpoolctl` is added.
7. **Cost.** The judge's numbers match the landing notes. These re-measured exactly as the
   landing notes give them (EXECUTED, `probe-meta.tsv`, snapshot):
   - the first `version("numpy")`: 336,323,860 to 478,501,836;
   - `import numpy.testing`: 463,864,591 to 600,088,569, +136.2 M.

   On the plain binary they are +217.3 M and +213.5 M. No check sees either, as the
   specification says. The snapshot split (metadata alone, stand-in alone) is READ from the
   implementer's `probe-1.tsv`, and its arithmetic checks out. I did not rebuild those variant
   sets.
8. **The checks.** READ: both guest checks assert what Decision 8 lists. EXECUTED: they fail on
   `$OLD` (`old-failfirst.txt`):
   - `PackageNotFoundError … numpy`, on both binaries;
   - `import pandas.io.clipboard: ImportError: cannot import name 'c_size_t'`, then
     `sympy's names: ImportError: cannot import name 'c_long'`, on both binaries.
9. **Ordering.** Nothing to check in code. `git merge-tree` against main is clean, and spec 035
   is not on main.
10. **The artifact set.** EXECUTED:
    - `python.wasm` is unchanged (`cmp`);
    - `SHA256SUMS` changes in exactly the `MANIFEST`, snapshot and zip lines;
    - `MANIFEST` changes in exactly the two scripts' `recipe` lines, the stub's line (replaced by
      three package lines), and `x-snapshot-zip`.

## Acceptance criteria against evidence

1. **The checks, seen failing first. Met.** The guest checks were EXECUTED against `$OLD`, by me
   and by the implementer. The unit checks' failing-first run is the implementer's (READ). My 14
   unit mutants (EXECUTED) show each unit check has teeth. The `dtype('O')` mutant is READ from
   `033-mutant/`.
2. **The zip's names and bytes. Met in the worktree; the clean clone is the lane's.**
   EXECUTED, the commands as written:
   - the names diff is exactly the nine lines, and there are 1,758 names;
   - `1750 shared; 0 differ: []`;
   - all five `cmp`s exit 0;
   - `python.wasm` is the same (`cmp`).

   Not run by me: a full build from pins in a clean clone. The implementer's full build was in
   the worktree, and the landing notes say so.
3. **The same bytes everywhere. Litter part met; dry run outstanding.** The litter re-run is
   EXECUTED and gives the same `SHA256SUMS` (`cmp`). The release dry run is not run; it is the
   lane's.
4. **The judge. Not met as written** (finding 2), and finding 1 changes the artifact, so the
   account must be re-taken. Everything else in the criterion holds:
   - no pass lost;
   - 37 of the 39 growths within their caps;
   - the zip's bytes +21,187 (cap 25 KB);
   - the snapshot's bytes −1,042;
   - `python.wasm` 0;
   - no golden output changed: every `*_job_matches_native` passes;
   - no heavy check above +2.5 M (`pandas_csv` +2,499,682);
   - the uncapped costs are restated, and they re-measure (Decision 7).
5. **The release. Outstanding**, as criterion 3.

## Constitution checks

- **§4.1 (patches).** No source tree is patched. Everything is a recipe file or the build script.
- **§4.2 (pins).** No new input. `PKG-INFO` comes from the pinned sdists, and spec 020's check
  judges those trees.
- **§4.3 and §4.4 (one target; WASI and the door only).** `python.wasm` is byte-identical, so
  its imports and exports are unchanged.
- **§4.5 (embedder-neutral).** `grep -ci vfs` over the diff is 0.
- **§4.6 (artifacts).** The same five kinds of artifact. Nothing large is in git.
- **§4.7 (prior art).** The stand-in restates CPython's alias rule and numpy's dtype rule from
  READ sources. It is not copied text. Building against CPython's own `struct` sizes is the
  design.
- **§4.9 (tests count).** The new checks assert equality, sizes and messages. Nothing is timed.
- **§4.10 (claims and evidence).** Labels are present throughout. The one overclaim is finding 3.
- **§4.11 (platform semantics).** The README says what `import ctypes` does and what the lookups
  cost. Finding 4 adds the introspection edge.
- **§4.12 (licences).** `LICENSES/` is unchanged. `METADATA` names its licences.
- **§4.13 (tooling).** `uv` only, and ruff is clean on `src/` and `tests/`. No dependency is added.
- **§4.14 (git).** The work is on its `spec/NNN` branch in its own worktree, and it merges cleanly.
- **§4.15 (safe by default).** No channel opens. The stand-in refuses every foreign call.
- **§5.6 and §5.7.** The change is build-class. It had a pre-build review and a confirmation, and
  this is its build review.

## Disposition (filled in by the author, then confirmed by the reviewer)

By the implementer, 2026-10-17, on `spec/033-the-zip-carries-what-packages-need` rebased onto
main (`8c56437`, no conflict); the revision is commit `f4f64ce`. Evidence: the specification's
Landing notes, "Revision after the build review", and
`scratchpad/033-variants/probe-fix.tsv`, `033-judge-3.log`, `033-growth-3.txt`.

1. **Fixed, as prototyped.** In `_types.py` the refusing `__numpy_dtype__` moved from `_CData` to
   a new `_NoLayout(_CData)`, the base of `Structure`, `Union` and the array, pointer and function
   types only; `_NumpyDtype.__get__` returns itself when read on `_SimpleCData`.
   - **Checks, seen failing first on `b25a61d`'s set (EXECUTED):** the `CTYPES` program gains
     `help(ctypes)` (via `pydoc.Helper` to a `StringIO`), `pydoc.render_doc(ctypes.c_int)`,
     `pydoc.render_doc(numpy.ctypeslib)` and `np.info(ctypes.c_int)`, after numpy is imported, on
     both binaries. All four failed with the `OSError` on both. A unit check,
     `test_the_ctypes_stand_in_documents_itself_with_numpy_loaded`, loads the package with a
     stand-in `numpy` in `sys.modules`. It failed at `_types.py:33`. Every refusal (`Structure`,
     `Union`, array, pointer, function type) is asserted there too.
   - Steps 70 to 90 re-run. New `SHA256SUMS`: `MANIFEST` `9f6019c6…`, snapshot `8d84b3b1…`
     (65,505,752 bytes), zip `6e3f773a…` (11,162,065 bytes), `python.wasm` `4befe9de…`
     unchanged. Criterion 2's commands and the litter re-run hold again.
   - The full judge: `200/204 pass · 0 fail`, `lost 0 · gained 4 · grew 39`, `791 passed, 11
     skipped`. Criterion 4's account was re-taken in the landing notes. Every growth matches the
     first build's within about 300 fuel, except the zip (+21,430 bytes) and the snapshot (−1,072
     bytes).
2. **Amended as worded.** Criterion 4 now carries your amendment verbatim, marked "Amended from
   the build review's finding 2", with its reason, and the Status line records it. The five-run
   evidence after the fix, `$OLD` against the fixed set:
   - `1/0` plain: +624,428, +492,342, +623,826, +489,246, +495,227; **mean +545,014** (cap 0.6 M);
   - `import pdb, pydoc, doctest` on the snapshot: +215,063, +77,589, +198,036, −47,727, −71,721;
     **mean +74,248** (cap 0.2 M);
   - the types are not built in either (a probe line prints `False False False` plain and `True
     False False` on the snapshot for `ctypes` loaded, `c_long` built, `ctypes._types` loaded).

   The code was not changed for this. The landing notes give the lane your `--accept-growth`
   wording, with the re-measured means.
3. **Fixed.** The Status line and the landing notes now say "heap-layout noise, the collector
   among it". They cite the perturbation series, and record that the `gc.disable()` pair is not a
   clean control. The heavy-check evidence for `pandas_csv` and `numpy_csv` stays as it was.
4. **Fixed.**
   - Decision 5 "The edges, stated" gains the introspection edge: for a `Structure`, `Union`,
     pointer, array or function type, `hasattr`, `inspect.getmembers`, `pandas_dtype` and
     `is_integer_dtype` raise the `OSError`, and what still works.
   - Decision 5 "numpy's dtypes" gains the refinement (`AttributeError` before numpy loads, as a
     real `ctypes` type) and where the refusal sits.
   - The README's platform paragraph and the CHANGELOG state the edge.
5. **No change**, as the review says. Noted for spec 023: compare `key.lower()` in
   `sdist_metadata` if a `PKG-INFO` with lower-case headers appears.

## Verdict

**Revise, then land.** The build does what the specification asks:
- the zip carries exactly the planned metadata;
- the stand-in names, sizes and refuses as written;
- every check fails first and has teeth;
- the bytes are reproducible.

Before it lands, three things must happen. Fix finding 1, a regression in `help(ctypes)` on the
snapshot caused by where the refusal sits. Amend criterion 4 as finding 2 words it. A smaller
stand-in would not help: the growth over the caps is heap-layout noise on top of the seven
members' start cost. Then re-take the account. Findings 3 and 4 are edits to the text. Finding 5
needs nothing.

One line: the metadata and the stand-in are right and reproducible, but the refusal on the shared
base breaks `help(ctypes)` on the snapshot, and the two over-cap checks call for a recorded
criterion amendment, not an unexplained `--accept-growth`.

## Confirmation (2026-10-17)

- **Reviewer:** the same fresh agent that wrote the review above (Claude Opus 5.5), not the
  author. I read the Disposition, the revision commit `f4f64ce` (`git diff 6f29828 f4f64ce`), and
  the specification's amended Status line, Decision 5, criterion 4 and landing notes. I edited
  nothing but this section.
- **Reviewed:** `spec/033-the-zip-carries-what-packages-need` at `f4f64ce`, rebased onto main.
  Since then main has moved only in `context/` documents (034, 041 and this review's
  Disposition). `git merge-tree --write-tree main HEAD` exits 0.
- **Ran (EXECUTED, in the worktree only; under the same scratch folder).**
  - Steps 70 to 90 once (`conf-70-90.log`). `cmp` with the rebuilt set's `SHA256SUMS`, saved
    before the run: the same file. Its non-licence lines are the landing notes' (`MANIFEST`
    `9f6019c6…`, snapshot `8d84b3b1…`, zip `6e3f773a…`, `python.wasm` `4befe9de…`). The
    `LICENSES/` lines equal `$OLD`'s.
  - The full judge, `uv run pytest`, no flags (`judge-conf.log`). Then `growth.py` against the
    branch's and main's `accepted.json` (`growth-conf.txt`). Ruff on `src/` and `tests/`.
  - The help probes on the rebuilt set, both binaries (`conf-pydoc2-*.txt`,
    `conf-introspect-snap.txt`). `probe.py`, `$OLD` against the rebuilt set: `help`, and the
    five-run series for both checks (`conf-noise.tsv`).
  - Two mutants of the fix in `_types.py`, each run against the stand-in unit checks with
    `--progress-latest` set to a scratch file, then restored. `git status --short` is empty
    after them. The worktree's `latest.json` is the full judge's.

### Each finding

1. **Fixed, as prototyped.** READ: the diff matches `proto/fixed/`.
   - The refusal moved to `_NoLayout(_CData)`. That base serves `Structure`, `Union`, and the
     array, pointer and function types. `_CData` no longer carries it.
   - `_NumpyDtype.__get__` returns itself when read on `_SimpleCData`. It uses `cls is
     _SimpleCData`, which is cleaner than my name test.

   EXECUTED on the rebuilt set:
   - On the snapshot, old against new, `pydoc.render_doc(ctypes)` now exits 0 on both.
   - On both binaries, these all succeed: `help(ctypes)`, `pydoc.render_doc(ctypes)`,
     `pydoc.render_doc(ctypes.c_int)`, `pydoc.render_doc(ctypes.Structure)`,
     `pydoc.render_doc(numpy.ctypeslib)` and `np.info(ctypes.c_int)`.
   - The snapshot introspection probe changes in exactly those lines. Every refusal is
     unchanged: `np.dtype` of a `Structure`, an array or a pointer; `pandas_dtype(S)`;
     `getmembers(S)`; `as_ctypes`; `ndarray.ctypes`.

   The new guest steps and the new unit check have teeth. EXECUTED: putting `_Refused` back on
   `_CData` fails the new unit check. So does removing the `_SimpleCData` guard (`1 failed, 1
   passed` each time). My first review EXECUTED the four guest calls on the first build's set,
   where they raised the `OSError`.
2. **Amended as worded, and met.** READ: criterion 4 carries the amendment word for word. It is
   marked as amended from this finding, with its reason, and the Status line records it.
   EXECUTED (`conf-noise.tsv`), every run equal to the Disposition's numbers to the unit:
   - `1/0` plain: +624,428, +492,342, +623,826, +489,246, +495,227; **mean +545,014**
     (cap 0.6 M);
   - the debugging tools on the snapshot: +215,063, +77,589, +198,036, −47,727, −71,721;
     **mean +74,248** (cap 0.2 M).

   My first review EXECUTED that the types are not built in either program (`'c_long' in
   vars(ctypes)` is `False`). The fix does not change what those programs import.
3. **Fixed.** READ: the Status line and the landing notes now say "heap-layout noise, the
   collector among it". They cite the series, and they record that the `gc.disable()` pair is
   not a clean control.
4. **Fixed.** READ: Decision 5 states the introspection edge and the `AttributeError`-before-numpy
   refinement, and says where the refusal sits. The README and the CHANGELOG state the edge.
   - One wording nit, not a condition. The README's new sentence begins "So does asking numpy or
     pandas for the dtype…" right after "`-V` still says 'no ctypes'". It means "this raises
     `OSError` too". It could say so, but the meaning is recoverable.
5. **No change, as agreed.**

### The judge and the account

- **Full judge (EXECUTED).** `791 passed, 11 skipped`. `200/204 pass · 0 gap · 4 blocked · 0
  fail (unit suite 591/598)`. `ratchet vs aac0a98618: lost 0 · absent 0 · unrun 0 · unrun locally
  2 · gained 4 · grew 39 · judge changed: tests/checks/test_v1_3_data_stack.py,
  tests/unit/test_build_scripts.py`. Ruff: `All checks passed!`, `56 files already formatted`.
- **Growth (EXECUTED, `growth-conf.txt`).** Main's `accepted.json` equals the branch's for every
  changed check. Every number matches the revised landing-notes table:
  - the zip +21,430 bytes;
  - the snapshot −1,072 bytes;
  - `python.wasm` 0;
  - `pandas_csv` +2,499,701, the largest heavy growth, under +2.5 M;
  - `gzip_round_trips` +592,080.

  Only two checks exceed their absolute caps, `uncaught_errors_print_as_native[plain]` (+624,513)
  and `stdlib_debugging_tools_import` (+215,114). Both are within the amended criterion by their
  five-run means.

### For the lane

These are not conditions; they are the lane's own steps.
- **The clean-clone build and the dry run.** Criterion 2's full build from pins in a clean clone
  and criteria 3 and 5's release dry run (`gh workflow run release.yml --ref <branch>`, its
  `rebuild` and `same-bytes` jobs) are not run. They are the lane's. Put the run number in the
  landing notes.
- **The acceptance needs both** `--accept-judge` (the two changed test files) and
  `--accept-growth`.
- **The `--accept-growth` reason:**

  > spec 033: 7 more zip members, about +0.54 M fuel per plain start and +0.07 M per snapshot
  > call; the zip +21,430 bytes, the snapshot −1,072 bytes, python.wasm unchanged; every check
  > within criterion 4's caps as amended by review 033's finding 2:
  > uncaught_errors_print_as_native[plain] (+624,513) and stdlib_debugging_tools_import
  > (+215,114) exceed their absolute caps by heap-layout noise, and their five-run perturbation
  > means (+545,014 and +74,248) are within them; no heavy check above +2.5 M (pandas_csv
  > +2,499,701).

  If the lane's own run in the main tree differs, use its numbers. The fuel figures here
  reproduce exactly on this machine, and the judge's driver differs from `probe.py` by under
  100 fuel.

### Lands?

**Yes. 033 lands**, once the lane has the clean-clone build and a green release dry run, and
accepts with the reason above. Every finding is fixed or answered. The rebuilt set reproduces
byte for byte. The judge is green apart from the growth it must accept.

One line: the refusal now sits only on the types without a layout, `help(ctypes)` works on the
snapshot again, and both over-cap checks are within the amended criterion by their five-run
means, so 033 lands through the lane.
