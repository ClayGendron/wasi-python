# 051 — What the upstream tests found

- **Status:** drafted 2026-10-18. It changes the build recipe and the artifact set, so it is
  reviewed once more before it is built (constitution §5.6). **Build-class** (§5.7): it touches
  `recipes/patches/` and `scripts/`.
- **Owner:** Clay Gendron
- **Kind:** a second carried numpy patch (`recipes/patches/numpy-2.5.2/0002-callback-signatures.patch`)
  and its upstream facts sheet; carried patch 0001 amended, with its draft; a recipe change to the
  zip (`scripts/make_stdlib_zip.py`, `scripts/steps/70_zip.sh`); judge additions (a binary scan,
  three guest checks, one golden job); spec 050's selections and expectations updated; `README.md`;
  `CHANGELOG.md`; `context/upstream/`.
- **Depends on:** 050 (numpy's and pandas' own tests under the runtime), which should land first:
  its suites are the judge that shows this work's whole effect, and this specification edits its
  TOML (Decision 10). If 050 is still in review when this is built, this lands first and 050
  re-drafts its tables from the rebuilt set; the lane picks one order, never both at once. Landed:
  020 (carried patches: the applier, the rules, the zero-diff check), 021 (patch 0001, amended
  here), 012 (the same bytes from any host), 003 (the zip is bytecode only, compiled by the pinned
  host Python).
- **Research it stands on:** `../research/2026-10-18-numpy-and-pandas-own-tests-in-the-guest.md`
  (findings 3, 4 and 5); spec 047's facts sheet `../upstream/9-regex-callback-signatures/` (the
  same class of defect in regex, carried as a patch); owner question 80 (facts sheets where a
  project refuses AI-written text). **The drafting runs** (EXECUTED 2026-10-18 in the session's
  scratch folder, against the frozen set `s-0cdc7b2bd78db6f5`, with `uv run` only; nothing in the
  repository was changed; the outputs are in `../research/2026-10-18-what-the-upstream-tests-found/`, called `evidence/`
  below):
  - the six callbacks read in numpy 2.5.2 and in numpy's `main` (`7ed6cf7`, 2026-10-17, by raw
    file; all six unchanged there);
  - a scratch scanner (`evidence/fpscan.py`) run over both binaries;
  - the patch made by editing a git copy of the pinned tarball with patch 0001 applied, checked
    with `git apply --check` against a fresh extraction, and the six changed files compiled with
    the build's own commands (`build/numpy-build/compile_commands.json`, the pinned wasi-sdk 33,
    `-Wall`), before and after; the objects' function types read back (`evidence/objtypes.py`);
  - patch 0001's amendment run natively under the pinned oracle with `sys.platform` set to
    `"wasi"` and `os.dup` raising;
  - a prototype zip whose code objects carry the zip path (`evidence/rename.py`), run with the
    plain binary against a control zip re-marshalled the same way without renaming;
  - every guest behaviour below beside the oracle's (Python 3.15.0, numpy 2.5.2, pandas 3.0.6).

## The problem

numpy's and pandas' own tests, run in the guest (spec 050), found three defects in the product:

1. **numpy callbacks that trap the guest.** `copy.copy(np.float64(1.5))` and
   `a.dtype = np.float32` end the whole call in a wasm trap (`indirect call type mismatch`).
   The embedder sees a trap, not an exception. Natively they print `1.5`, and warn
   `DeprecationWarning` and work (EXECUTED both ways).
2. **pandas' warnings point inside pandas.** `pd.read_csv(io.StringIO("a;b\n1;2\n"), sep=None)`
   warns `ParserWarning` at `pandas/io/parsers/readers.py:1798` in the guest. Natively the
   warning names the caller, `<string>` line 4 (EXECUTED). 2,428 of pandas' fast-mode failures
   are this one cause.
3. **Carried patch 0001 changes two numpy behaviours.** `np.save` of a masked array to a file
   writes the data and drops the mask; natively it raises `NotImplementedError`. And a truncated
   `.npy` file's message differs; the exception type is the same (EXECUTED both ways).

## Decisions

### Part 1: numpy's callbacks get the signatures CPython calls them with

1. **The cause, for each function** (READ, numpy 2.5.2; the same lines on numpy `main`). CPython
   calls a C callback through a pointer of a fixed type. Native code tolerates a function
   defined with fewer parameters. WebAssembly's `call_indirect` checks the type and traps.
   CPython's Emscripten build hides the class with a JavaScript trampoline
   (`Include/internal/pycore_emscripten_trampoline.h`, READ: "Bad fpcasts are an issue in
   WebAssembly"); its WASI build has none, so numpy's Pyodide CI cannot see these.

   | function (numpy 2.5.2) | defined as | CPython calls it as | reachable by users |
   |---|---|---|---|
   | `gentype___copy__`, `_core/src/multiarray/scalartypes.c.src:2128` | `(PyObject *self)` | `METH_NOARGS`: `(self, NULL)` | **yes:** `copy.copy` of any numpy scalar, `np.bool_(True).__copy__()` |
   | `array_descr_set`, `_core/src/multiarray/getset.c:388` | `(self, arg)` | a setter: `(self, value, closure)` | **yes:** `a.dtype = …` (deprecated in 2.5, still supported) |
   | `_get_castingimpl`, `_core/src/multiarray/convert_datatype.c:248` (and `.h:16`) | `(module, args)` | `METH_VARARGS \| METH_KEYWORDS`: `(module, args, kwargs)` | private (`_multiarray_umath._get_castingimpl`); no numpy or pandas Python code calls it |
   | `sfloat___reduce__`, `_core/src/umath/_scaled_float_dtype.c:192` | `(self)` | `METH_NOARGS` | private: numpy's test dtype, through `_get_sfloat_dtype()` |
   | `array_converter_get_scalar_input`, `_core/src/multiarray/array_converter.c:132` | `(self)` | a getter: `(self, closure)` | private: `_array_converter(...).scalar_input`; numpy's own Python code never reads it (READ) |
   | `boundarraymethod__supports_unaligned`, `_core/src/multiarray/array_method.c:974` | `(self)` | a getter | private: only through `_get_castingimpl`'s result |

   The last two were not found by the tests. The scan of Decision 4 found them, and the
   `scalar_input` getter traps the guest (EXECUTED). So two of the six matter to users; all six
   are fixed, because all six are the same mistake and the scan (Decision 4) must end clean.

2. **A carried patch, not a recipe file** (§4.1; §6.2). The candidates were weighed:
   - *A forced-include header of function-like macros* (`#define gentype___copy__(s)
     gentype___copy__(s, PyObject *unused)`) would compile and leave the table casts alone. But it
     changes numpy's code while spec 020's zero-diff check reports the tree as pristine. And it
     differs from the change numpy would take. Spec 021 refused a recipe for the same reasons.
   - *A trampoline in CPython,* as Emscripten's: plain WebAssembly cannot call a function through
     a type other than its own, so there is nothing to build it from (INFERRED).
   - *A carried patch* adds the missing parameters, marked `NPY_UNUSED`, and changes nothing else.
     It is the change numpy would take, and it is deleted when numpy releases it.

   `recipes/patches/numpy-2.5.2/0002-callback-signatures.patch` (7 files, 11 lines added, 7
   removed; `evidence/patches/`): each definition gains the parameter its call type passes
   (`PyObject *NPY_UNUSED(args)` for `METH_NOARGS`, `PyObject *NPY_UNUSED(kwargs)` for
   `_get_castingimpl` and its prototype, `void *NPY_UNUSED(ignored)` for the getters and the
   setter). `_get_castingimpl` keeps its flags: changing them to `METH_VARARGS` would make a
   keyword argument an error where it is ignored today. The method tables are untouched.
   EXECUTED: it applies to the pinned tarball after 0001 with no offset. Each changed file compiles
   with the build's own command and `-Wall` with the same two macro-redefinition warnings the
   unchanged file gives, and no new one. The six objects' function types become exactly what
   CPython calls (`evidence/object-types-after.txt`: `(i32, i32) -> i32` for the four
   one-parameter ones, `(i32, i32, i32) -> i32` for the setter and `_get_castingimpl`).

3. **The upstream facts sheet** is `context/upstream/13-numpy-callback-signatures/`, in owner
   question 80's form: `notes.md` (how it was found and checked), `pr.md` (the facts:
   the six functions, the reproduction, the trampoline that hides the class on Emscripten, the
   patch), `fix.patch` and `evidence/`. numpy's AI policy (`doc/source/dev/ai_policy.rst` on
   `main`, READ 2026-10-18) asks for a disclosure of AI use with "which tool(s) have been used,
   how they were used". It forbids AI-written "comments, pull request descriptions, or issue
   descriptions" and an agent that "submits a pull request autonomously". So the owner writes and
   sends it, as for patch 0001. The draft
   `context/upstream/patches/numpy-2.5.2/0002-callback-signatures.md` has spec 020's six header
   lines (`Files:` the seven paths) and a body that points to the facts sheet and names the
   policy's clauses, as 0001's does. `fix.patch` is made against numpy `main` in a scratch
   clone when the owner asks to send. Against `main` (`7ed6cf7`) today, six of the seven hunks
   apply, and `convert_datatype.h`'s context has moved (EXECUTED). The README's count of carried
   patches becomes 2, and `context/upstream/README.md`'s table gains the row.

4. **A scan for the whole class, as a judge check.** `tests/harness/callbacks.py` reads the linked
   `python.wasm`, without running it: its types, function section, element segment (the table
   index a C function pointer holds) and active data segments (the static memory image), and
   names from the name section. It finds CPython's callback tables in the image and checks every
   entry's function type against the type CPython calls it with:
   - **`PyMethodDef`** arrays (16-byte entries `{name, meth, flags, doc}` ending in a zero
     entry): `METH_VARARGS`, `METH_NOARGS`, `METH_O` → `(i32, i32) -> i32`;
     `METH_VARARGS|METH_KEYWORDS` and `METH_FASTCALL` → 3 parameters;
     `METH_FASTCALL|METH_KEYWORDS` → 4; `METH_METHOD|METH_FASTCALL|METH_KEYWORDS` → 5;
     `METH_CLASS`, `METH_STATIC`, `METH_COEXIST` ignored;
   - **`PyGetSetDef`** arrays (20-byte entries `{name, get, set, doc, closure}`): getter
     `(i32, i32) -> i32`, setter `(i32, i32, i32) -> i32`;
   - **`PyMemberDef`** arrays (`{name, type ≤ 20, offset, flags, doc}`) are found first and
     skipped, so a member's type code is never read as a function pointer, and so are the bytes
     of the method arrays when getsets are sought.

   EXECUTED on the frozen plain binary in about a second. It read 3,073 method entries and 1,129
   getset entries, and skipped 1,004 member entries. It reported all six numpy callbacks of
   Decision 1 and nothing from pandas (Cython writes the right signatures). It also reported six
   matches in CPython's own data that are not callback tables: getters named `EncodingMap`,
   `moduledef`, `builtin_method`, `SkippedEntityHandler`; a setter `SkippedEntityHandler`
   (pyexpat's handler table, whose layout begins like a getset's); a method `bytes`. Each was
   checked by name to be a struct of another shape or a coincidence of bytes (INFERRED from the
   function each points at: a parser rule, `bool_new`, pyexpat's setters).

   The check is `test_callbacks_have_the_types_cpython_calls` (v1.3, fast, needs `plain binary`).
   Its findings are the mismatches less a reviewed exclusion list in the check: those six
   `(kind, entry name, function name)` triples, each with its reason. The list is strict both
   ways. An excluded triple that no longer appears is a finding ("remove the exclusion"), so the
   list cannot rot. The scan reads the plain binary only. The snapshot is the same code and the
   same table, made from it by Wizer; its image differs by the heap, and on the frozen
   snapshot the scan took about 10 s and gave the same six numpy callbacks plus one exclusion.
   **Why the judge, not a build step:** one implementation, kept apart from the build it
   judges (spec 002's lesson 2). It runs on every judge run, the lane's and the release
   workflow's (`release.yml` runs `uv run pytest`), so no set with a mismatch is accepted or
   released. Every later package compiled in (scipy, matplotlib, lxml, regex) is scanned the
   same way. regex's five getters (spec 047) are this class and shape (INFERRED).
   **Out of the scan, and said so in its docstring:** `tp_*` slots of static type objects,
   `PyType_Slot` arrays, number/sequence/mapping method structs, and C callbacks passed to C APIs
   (`qsort`, LAPACK). The first two can follow when a defect shows the need.

5. **The guest checks, seen failing first.** A golden job `tests/jobs/callbacks.py` with its
   `.expected` from the pinned oracle (spec 002, Decision 11), run on both binaries by
   `test_callbacks_job_matches_native[plain|snapshot]` (v1.3, slow). It prints, each in its own
   `try`, with the exception's type and message on failure:
   - `copy.copy` of `np.float64(1.5)`, `np.int32(3)`, `np.bool_(True)`, `np.str_("a")`,
     `np.datetime64("2017-08-25")`, `np.void(b"a")`, each with its type;
   - `a = np.zeros(4, np.int32); a.dtype = np.float32` under `warnings.catch_warnings(record=True)`:
     the array and the warning categories (natively `[0. 0. 0. 0.] ['DeprecationWarning']`,
     EXECUTED);
   - `pickle.loads(pickle.dumps(np._core._multiarray_umath._get_sfloat_dtype()(2.0)))` and its
     scaling (`sfloat___reduce__`);
   - `repr(_get_castingimpl(np.dtypes.Float64DType, np.dtypes.Int64DType))` reduced to its class
     name, and that object's `_supports_unaligned`;
   - `_array_converter(1, [2]).scalar_input`.

   Natively the job ends. On the frozen set it traps at the first `copy.copy` (EXECUTED: the
   program's first line traps), so the check fails with "trapped" before the patch. That is the
   seen-failing-first evidence; the landing notes name each line that trapped, by running each
   line alone. The private calls stay in the job on purpose: they are the scan's findings,
   proved fixed in the guest.

### Part 2: the zip's code objects carry the name they are imported under

6. **The cause** (READ). `scripts/make_stdlib_zip.py`'s `pyc()` compiles each member with its
   relative name (`compile(source, name, …)`, line 140), so `co_filename` is
   `pandas/core/frame.py`. zipimport takes a `.pyc`'s code as it is (`Lib/zipimport.py`,
   `_unmarshal_code`; no `_fix_co_filename`) and sets `__file__` to
   `/usr/local/lib/python315.zip/pandas/core/frame.pyc`. pandas' `find_stack_level`
   (`pandas/util/_exceptions.py:37`) skips frames whose `co_filename` starts with
   `os.path.dirname(pd.__file__)`; none does, so it answers 0 (EXECUTED). numpy's
   `suppress_warnings(module=…)` compares the same two things.

7. **The name: the path zipimport gives a source file in the same zip.** For a `.py` in a zip,
   zipimport compiles with `modpath`, `archive + "/" + path` (`Lib/zipimport.py:818`, READ). So
   each member is compiled with `/usr/local/lib/python3XY.zip/<path>.py`: the archive path the
   binary itself puts on `sys.path` (`recipes/reactor_main.c:25`, `STDLIB_ZIP`), the path the
   runner and the judge grant it at (`ZIP_GUEST`, spec 017), and the path step 80 snapshots it at
   (`scripts/steps/80_snapshot.sh:14`). `make_stdlib_zip.py` gains `--code-prefix <text>`, used
   by `pyc()` as `prefix + name` (the member name with `.py`, as today). Step 70 passes
   `--code-prefix "/usr/local/lib/python$PYTHON_TAG.zip/"`; `make_stdlib_zip.py` refuses a prefix
   that is not absolute or does not end in `.zip/`. Nothing else changes in the zip: members,
   order, dates, compression.
   - **Spec 012 holds.** The prefix is a constant built from the line's version, never a host
     path, so the zip and the snapshot stay the same bytes from every build host. The
     rebuild-from-pins checks prove it, as for any recipe change.
   - **Not a runtime fix.** Rewriting `co_filename` at import, in a zipimport hook or with
     `_imp._fix_co_filename`, would cost every import of every run. Naming at build time costs
     nothing at run time but a longer string in each code object.
   - **What else sees it.** Tracebacks show `/usr/local/lib/python315.zip/pandas/core/frame.py`,
     the form native zip imports have, instead of `pandas/core/frame.py`. `linecache` still finds
     no source, since the zip has none, as today. The bootstrap's traceback trimming
     (`recipes/reactor_bootstrap.py:70`) compares `runpy`'s own `co_filename`, so it still
     matches. Any judge check that compares stderr with a relative frame path is found by the
     full judge run and updated as a judge change.

8. **Measured on a prototype** (EXECUTED, plain binary; `evidence/guest.txt`). The frozen zip's
   1,102 `.pyc` members were re-marshalled with their code renamed (`named.zip`), against a
   control re-marshalled the same way without renaming (`control.zip`).
   - **The warning:** `ParserWarning <string> 4`, native's answer; the control gave
     `pandas/io/parsers/readers.py 1798`.
   - **`find_stack_level()`:** 1 at the top level of a `-c` program (control: 0).
   - **`DataFrame.__init__.__code__.co_filename`:** `/usr/local/lib/python315.zip/pandas/core/frame.py`.
   - **Size:** the zip grows 28,360 bytes over the control (11,297,967 against 11,269,607; the
     control differs from the real zip by my writer's compression, so this is the renaming alone).
   - **Fuel:** `-c pass` grows 42,250 (+0.017%) and `-c "import pandas"` grows 2,629,399
     (+0.05%), from the longer strings each code object carries.

   The real build's numbers come from step 70 and are the ones accepted (Decision 11).

9. **The check, seen failing first.** `test_a_pandas_warning_names_the_callers_line[plain|snapshot]`
   (v1.3) runs a program file `/job/warn.py` whose fourth line is
   `pd.read_csv(io.StringIO("a;b\n1;2\n"), sep=None)` under `catch_warnings(record=True)`. It
   asserts the warning is `ParserWarning` with `filename == "/job/warn.py"` and `lineno == 4`, as
   natively. It also asserts that `pandas.core.frame.DataFrame.__init__.__code__.co_filename`
   equals `os.path.dirname(pandas.__file__) + "/core/frame.py"`, the rule itself, so a change of
   path or version cannot drift. Seen failing on the frozen set: `pandas/io/parsers/readers.py`,
   line 1798 (EXECUTED).

### Part 3: patch 0001's two behaviour changes

10. **A masked array: native behaviour restored. A truncated file's message: recorded as a
    deliberate difference.**
    - **`np.save` of a masked array to a file.** Natively, a real file is written with
      `array.tofile`, and `MaskedArray.tofile` raises `NotImplementedError`. Patch 0001 sends real
      files down the chunked path on WASI, which drops the mask silently: data loss where native
      refuses. Patch 0001 is amended in place (it is ours, and not yet sent): in `write_array`,
      after the pickle branch, on WASI, when `fp` is a real file and `type(array).tofile` is not
      `ndarray.tofile`, the subclass's own `tofile` decides (`array.T.tofile(fp)` for a
      Fortran-ordered array, as the native branch does). Ten lines added, plus a test,
      `test_save_masked_without_dup`, next to the patch's other test (`evidence/patches/`). It
      applies to the pinned tarball with no offset. EXECUTED natively with `sys.platform`
      `"wasi"` and `os.dup` raising: a C-ordered, a Fortran-ordered and an empty array still
      round-trip through a real file; a masked array, C- or Fortran-ordered, raises native's
      `NotImplementedError: MaskedArray.tofile() not implemented yet.`; a masked array saved to
      `BytesIO` still writes, as natively. Only numpy's `MaskedArray` overrides `tofile` in numpy
      and pandas (READ). A subclass whose override calls `ndarray.tofile` meets `os.dup` and
      raises `OSError` 58, which the README already says of `tofile`.
    - **The truncated file's message.** On WASI a real file is read the way numpy reads every
      in-memory stream, so a truncated one raises `ValueError: EOF: reading array data, expected
      48 bytes got 47`. Natively, a real file raises `ValueError: Failed to read all data for
      array. …`. The type is the same; the message is the one numpy itself gives for `BytesIO`
      (EXECUTED both). Changing it would add WASI-only code to the upstream patch for a message.
      It is a deliberate difference, written in the README's platform paragraph.
    - **The draft.** `context/upstream/patches/numpy-2.5.2/0001-npy-files-without-dup.md` and the
      facts in `../upstream/3-numpy-npy-wasi/pr.md` gain both points: the subclass rule, and the
      message a real file now gives on WASI. The `Files:` line is unchanged.
    - **The check.** `test_npy_files_round_trip` (spec 021) gains two cases on both binaries: a
      masked array saved to a path raises `NotImplementedError` with native's message (seen
      failing first: the frozen set prints `saved [1 2 3] ndarray`, EXECUTED), and a truncated
      file raises `ValueError` (the type only, by design).

### For the whole

11. **One specification, three parts, one rebuild.** The parts are independent in code but
    share their cost: a full rebuild, a new snapshot, and an acceptance with growth. Built as one
    branch, `spec/051-what-the-upstream-tests-found`, in three commits (Part 1, Part 2, Part 3)
    so the review reads each alone; landed as one. If the pre-build review finds one part not
    ready, the lane splits that part into its own specification and the rest goes on.
    Acceptance: `--accept-judge` (the new checks, the golden job, the exclusion list, spec 050's
    TOML) and `--accept-growth` with the build's measured account. Growth is expected: the zip's
    bytes, every plain-binary run's fuel (Part 2), and the snapshot's numbers.

12. **What it changes in spec 050's judge, if 050 has landed** (a judge change, in this branch):
    - every `[[trap]]` entry is removed, because none traps any more;
    - `test_casting_unittests.py` and `test_arraymethod.py` leave `not_selected` and run in
      `numpy-core`. Their outcomes are new: classes are added only for failures with a named
      closer, and the landing notes give the counts;
    - the `zip-code-names` classes (193 pandas failures and 1 numpy failure) are removed;
    - the `patch-0001-masked-save` class is removed;
    - `patch-0001-truncated-message` closes with `README.md`.

    The `passes` metric rises; the notes give each group's new count.

13. **The README.**
    - "Known defects" (from 050, if landed) loses the traps and the warnings line.
    - The platform paragraph gains: a truncated `.npy` file read from a path raises the
      `ValueError` numpy gives for in-memory streams; `np.save` of a masked array raises
      `NotImplementedError`, as natively.
    - Tracebacks name zip members by their full zip path.
    - The patch count becomes 2.

    The CHANGELOG names the new patch and its path, the amended 0001, and the zip's code names.

## Intent

The defects numpy's and pandas' own tests found are fixed or written down. The judge scans every
build for that class of trap, so the next one is caught at the build that brings it, and found
before any user meets it.

## Design

```
recipes/patches/numpy-2.5.2/0002-callback-signatures.patch   six callbacks, seven files (Decision 2)
recipes/patches/numpy-2.5.2/0001-npy-files-without-dup.patch  amended: the subclass rule and its test (Decision 10)
context/upstream/13-numpy-callback-signatures/                 notes.md, pr.md (facts), fix.patch, evidence/
context/upstream/patches/numpy-2.5.2/0002-callback-signatures.md   six header lines; body points to the facts
context/upstream/patches/numpy-2.5.2/0001-npy-files-without-dup.md amended body
context/upstream/3-numpy-npy-wasi/pr.md                        the two behaviours
context/upstream/README.md                                     row 13
scripts/make_stdlib_zip.py                                     --code-prefix; pyc(source, prefix + name)
scripts/steps/70_zip.sh                                        --code-prefix "/usr/local/lib/python$PYTHON_TAG.zip/"
tests/harness/callbacks.py                                     the scan (Decision 4)
tests/checks/test_v1_3_data_stack.py                           test_callbacks_have_the_types_cpython_calls,
                                                                 test_callbacks_job_matches_native[*],
                                                                 test_a_pandas_warning_names_the_callers_line[*],
                                                                 test_npy_files_round_trip's two new cases
tests/jobs/callbacks.py, callbacks.expected                    the golden job, from the oracle
tests/unit/test_callbacks.py                                   the scan on small modules built with wat2wasm
tests/upstream/numpy.toml, pandas.toml                         Decision 12, if 050 has landed
README.md, CHANGELOG.md                                        Decision 13
```

## Scope

In: the six numpy callbacks; the scan of method and getset tables; the zip's code names; patch
0001's masked-array rule and its documented message.

Out:
- **Scanning `tp_*` slots and other C callback paths** (Decision 4).
- **Sending anything upstream:** the owner's.
- **numpy's other WASI behaviours already documented** (no `dup`, no `mmap`, no `ctypes` calls).
- **Changing CPython's zipimport.**
- **pandas' remaining suites:** spec 050's budget.

## Acceptance criteria

1. **Seen failing first, on the frozen set.**
   - `test_callbacks_have_the_types_cpython_calls` reports the six numpy callbacks (and, with
     the exclusion list empty, the six non-callback matches).
   - `test_callbacks_job_matches_native[*]` traps.
   - `test_a_pandas_warning_names_the_callers_line[*]` reports `pandas/io/parsers/readers.py:1798`.
   - The masked-array case of `test_npy_files_round_trip` reports `saved`.

   The builder records each.
2. A full build from pins in a clean clone:
   - step 40's log names both patches applied;
   - spec 020's zero-diff check passes with exactly the two;
   - `python.wasm`'s six callbacks have the types Decision 2 names (the scan says so);
   - every `.pyc` in the zip has `co_filename` equal to `/usr/local/lib/python315.zip/` plus its
     member name less `c` (a unit check over the built zip);
   - the zip's member list equals the frozen set's.
3. After the build, every check in criterion 1 passes. The golden job equals the oracle's output
   on both binaries. The scan's findings are empty with its six reviewed exclusions, and an
   exclusion that stops matching is a finding (a unit check on a crafted module).
4. **Spec 012:** the same-bytes rebuild on a second host (the release dry run's arm64 Linux job)
   gives the same `python.wasm`, zip and snapshot as the macOS build.
5. If spec 050 has landed, its suites pass with Decision 12's edits. No trap entry is left.
   `numpy-core` runs the two returned files. Each group's `passes` is reported, and none falls.
6. `uv run ruff check`, `uv run ruff format --check`, and `uv run pytest` green.
   - `--accept-judge` names the new checks, the job, the exclusions and spec 050's TOML.
   - `--accept-growth` gives the build's measured account: zip bytes, the plain binary's fuel,
     and the snapshot's fuel and bytes, each with its cause.
   - Ratchet: lost 0.
7. The README, the CHANGELOG, both drafts, the facts sheet and `context/upstream/README.md`
   say what Decisions 3, 10 and 13 say. The rules check passes with two carried patches.

## The owner's choices

None is needed to build this; every choice is decided above (§5.2). Two are the owner's by
standing rule, and wait for nothing here:
- **Sending the drafts:** patch 0002's facts sheet, and patch 0001's amended draft. Both are
  outward-facing, and numpy's AI policy requires the owner's own words and a disclosure
  (Decision 3).
- **This specification changes a behaviour users see:** tracebacks name zip members by their full
  zip path. It is native's form, and the README says so. No default is loosened (§4.15).

## Landing notes
