# 051 — What the upstream tests found

- **Status:** built 2026-10-18 on `spec/051-what-the-upstream-tests-found`; build-reviewed the same day (`../reviews/051-what-the-upstream-tests-found-2026-10-18.md`: land after F1 to F3; each finding answered in its Disposition and below). **The lane's order (2026-10-18): 051 lands first; 050 rebases onto 051 and re-derives its tables on 051's set** (written into 050's status), so Decision 12 and criterion 5 are done by 050, not here. Confirmed for build 2026-10-18 (the review's Confirmation; its builder notes stand in the review). drafted 2026-10-18. Revised the same day against its pre-build review
  (`../reviews/051-what-the-upstream-tests-found-spec-2026-10-18.md`, findings F1 to F7, each
  answered in its Disposition and written in below); it awaits the reviewer's confirmation. It
  changes the build recipe and the artifact set, so it takes that review before it is built
  (constitution §5.6). **Build-class** (§5.7): it touches `recipes/patches/` and `scripts/`.
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

  **Its place among the build-class specifications** (§5.7; the review's F3). Not landed and
  build-class today: 035, 037, 038, 039, 040, 041, 042 to 047. 051 takes the next build-class slot
  after 050 lands, and waits for any build-class landing already in the lane.
  - **With 035.** Both change what the snapshot and the zip measure. 035's criterion 9 asks for a
    zip "byte for byte 033's" and calls any plain fuel growth a finding; this one grows the zip
    and the plain binary's fuel (Decision 8). **Whichever of 035 and 051 lands second restates
    its byte and fuel comparisons against the base it lands on.** If 051 is second, its growth
    account is measured on 035's set. If 035 is second, its criterion 9 compares with 051's zip,
    and the zip's code names are part of that base, not a finding.
  - **With every later package** (Decision 4a). After 051, the callback scan runs in the fast
    tier on every build. A package spec that lands later meets it in its own judge run.
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

  **The pre-build review's runs** (its "Executed" list):
  - both patches applied by `scripts/steps/apply_patches.sh` to a fresh extraction;
  - the scan reproduced, then extended with references (737 runs, 5 unreferenced: the six false
    lines) and with code-referenced single definitions (2,029 more entries, 0 mismatches);
  - clang's `-Wcast-function-type-mismatch` shown unable to tell the bug from CPython's idiom;
  - `pandas/tests/reshape` with the renamed zip: 2,664 passed, 0 failed, where the frozen zip
    gave 7 stack-level failures.

  **Revision runs** (EXECUTED 2026-10-18, scratch folder `051-review/author/`):
  - 0001 amended again for F5, and both patches applied by the project's own applier to a fresh
    extraction ("applied" for both);
  - 0001's three tests (`test_file_truncated`, `test_save_masked_without_dup`,
    `test_save_load_without_dup` over its 161 arrays) run natively under the pinned oracle with
    the patched module, `sys.platform` set to `"wasi"` and `os.dup` raising: all passed;
  - the golden job's three private calls run natively: `_ScaledFloatTestDType 2.0` after a
    pickle round trip, `_BoundArrayMethod True`, and `(True, False)`.

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

4. **A scan for the whole class, as a judge check, counting only what something references.**
   `tests/harness/callbacks.py` reads the linked `python.wasm` without running it. It reuses
   `tests/harness/wasm.py` (§6.4): the type, import and function sections that file already
   reads, plus four it learns to read here:
   - the element section (the table index a C function pointer holds);
   - the data section (the static memory image);
   - the code section's bytes;
   - the name section, when present.

   A passive data segment, or an element segment in any form but an active `funcref` list, is a
   finding, not a skip: the scan must never pass by reading less.

   **What it checks.** It finds CPython's callback tables in the image, and keeps only tables
   that something points at (the review's F1). A table is kept when its start address appears
   either as an aligned 4-byte word in the data image or as an `i32.const` operand in the code
   section. The operands are found by reading each `0x41` byte and the LEB number after it. That
   over-approximates, so it can only add references, never lose one. The tables are:
   - **`PyMethodDef` arrays**: 16-byte entries `{name, meth, flags, doc}` ending in a zero entry.
     Referenced from a type's `tp_methods`, a `PyModuleDef`, a `PyType_Slot`, or code.
   - **Single `PyMethodDef`s referenced from code** (the review's F2). These are Cython's
     `__pyx_mdef_…` for every module-level `def`, and CPython's own single definitions. A single
     is kept when a code operand points at a 16-byte entry with an identifier name, valid flags
     and a valid table index.
   - **`PyGetSetDef` arrays**: 20-byte entries `{name, get, set, doc, closure}`, referenced the
     same way.
   - **`PyMemberDef` arrays** (`{name, type ≤ 20, offset, flags, doc}`) are found first and
     skipped. So a member's type code is never read as a function pointer, and so are the bytes
     of method arrays when getsets are sought.

   Each entry's function type must be the type CPython calls it with:
   - `METH_VARARGS`, `METH_NOARGS`, `METH_O` → `(i32, i32) -> i32`;
   - `METH_VARARGS|METH_KEYWORDS` and `METH_FASTCALL` → 3 parameters;
   - `METH_FASTCALL|METH_KEYWORDS` → 4;
   - `METH_METHOD|METH_FASTCALL|METH_KEYWORDS` → 5;
   - getter → `(i32, i32) -> i32`; setter → `(i32, i32, i32) -> i32`;
   - `METH_CLASS`, `METH_STATIC` and `METH_COEXIST` are ignored.

   A finding names the entry and its table index, `<kind> <entry name>: table index <n> has
   <type>, called as <type>`, with the function's name added when the name section has it.

   **What it found on the frozen plain binary** (EXECUTED by the drafting runs, and with
   references by the review):
   - **Without references:** 3,073 method entries, 1,129 getset entries and 1,004 member
     entries, in about a second. That reported the six numpy callbacks of Decision 1, plus six
     lines that are not callback tables: getters named `EncodingMap`, `moduledef`,
     `builtin_method`, `SkippedEntityHandler`, a setter `SkippedEntityHandler`, and a method
     `bytes`.
   - **With references:** of 737 runs, exactly 5 have no reference, and they are those six
     lines (pyexpat's getter and setter are one run). All six real numpy callbacks sit in
     referenced runs.
   - **The singles** add 2,029 entries, 1,976 of them Cython's, with no mismatch. So pandas'
     module functions (`lib.is_scalar`, `groupby.group_sum`, …) are checked, and clean.

   **So the exclusion list is empty.** The check keeps the strict-both-ways mechanism for a
   reviewed real case only: an excluded entry that no longer appears is a finding. The rule for
   every later package is that a mismatch is fixed by a carried patch or an upstream release,
   never by an exclusion.

   **The check.** `test_callbacks_have_the_types_cpython_calls` is v1.3, fast, and needs
   `plain binary`. Besides its findings, it asserts minimum counts, set from today with room to
   spare, so a toolchain change cannot make it pass by finding nothing (the review's F6):
   - at least 2,500 entries in referenced method arrays;
   - at least 1,000 referenced getset entries;
   - at least 1,500 referenced single definitions.

   It reports its coverage (arrays, singles, getsets, members) in its message and in
   `latest.json`. It reads the plain binary only. The snapshot is the same code and the same
   table, made from it by Wizer; its image differs by the heap.

   **Why the judge, not a build step.** One implementation, kept apart from the build it judges
   (spec 002's lesson 2). It runs on every judge run, the lane's and the release workflow's
   (`release.yml` runs `uv run pytest`), so no set with a mismatch is accepted or released. A
   compile-time warning cannot replace it: clang's `-Wcast-function-type-mismatch` flags the bug
   and CPython's ordinary `(PyCFunction)` cast alike (the review, EXECUTED).

   **Out of the scan, and said so in its docstring:**
   - `tp_*` slots of static type objects;
   - `PyType_Slot` arrays;
   - number, sequence and mapping method structs;
   - C callbacks passed to C APIs (`qsort`, LAPACK).

   The first two can follow when a defect shows the need.

   4a. **What the scan means for specifications already reviewed** (the review's F3). It changes
   none of their texts. It adds one condition to each build-class landing after 051: the
   callback scan is green, and a mismatch it finds is fixed by a carried patch or an upstream
   release, never by an exclusion. When 051 lands, the lane adds that sentence to the status of
   each specification below that has not landed. By package:
   - **039 (tier A) and 042 (seaborn, reportlab):** pure Python. They add nothing the scan
     reads, beyond reportlab's small C accelerators if 042 builds them; those are scanned like
     any other.
   - **037 and 038 (scipy):** hand-written C and C++, plus f2py and Cython wrappers. f2py and
     Cython write their own tables; scipy's hand-written modules are the likeliest place for
     this mistake. If 037 or 038 lands before 051, 051's rebuild scans them, and a mismatch
     found there is fixed in 051's branch as a carried scipy patch, named in its landing notes.
     If they land after, their own builds meet the scan.
   - **043 (matplotlib's second milestone):** contourpy through pybind11, whose dispatcher
     calls with the right types (INFERRED). Its first milestone's C extensions, if already
     linked, are scanned now: the drafting scan of the frozen set (which has no matplotlib)
     says nothing of them.
   - **044 (scikit-learn) and 045 (statsmodels):** almost all Cython, whose single definitions
     are now covered.
   - **046 (lxml):** Cython over libxml2. Its libxml2 callbacks are C-to-C and out of the scan.
   - **047 (regex):** the five getters its carried patch fixes are this class and shape. With
     047's patch the scan must be green; without it, the scan would name them (INFERRED).
   - **035, 040, 041:** add no compiled package.

5. **The guest checks, seen failing first.** A golden job `tests/jobs/callbacks.py` with its
   `.expected` from the pinned oracle (spec 002, Decision 11), run on both binaries by
   `test_callbacks_job_matches_native[plain|snapshot]` (v1.3, slow). It prints, each in its own
   `try`, with the exception's type and message on failure:
   - `copy.copy` of `np.float64(1.5)`, `np.int32(3)`, `np.bool_(True)`, `np.str_("a")`,
     `np.datetime64("2017-08-25")`, `np.void(b"a")`, each with its type;
   - `a = np.zeros(4, np.int32); a.dtype = np.float32` under `warnings.catch_warnings(record=True)`:
     the array and the warning categories (natively `[0. 0. 0. 0.] ['DeprecationWarning']`,
     EXECUTED);
   - `pickle.loads(pickle.dumps(SF(2.0)))` and its scaling (`sfloat___reduce__`), where
     `SF = np._core._multiarray_umath._get_sfloat_dtype()` and `np._ScaledFloatTestDType = SF`
     first, as numpy's own test does (pickle finds the type by its repr);
   - `repr(_get_castingimpl(np.dtypes.Float64DType, np.dtypes.Int64DType))` reduced to its class
     name, and that object's `_supports_unaligned`;
   - `_array_converter(1, [2]).scalar_input`.

   Natively the job ends. The three private calls give `_ScaledFloatTestDType 2.0`,
   `_BoundArrayMethod True` and `(True, False)` (EXECUTED in the revision runs). On the frozen set
   it traps at the first `copy.copy` (EXECUTED: the
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
      refuses. Patch 0001 is amended in place (it is ours, and not yet sent):
      - **One predicate.** Native `isfileobj`'s two tests, the `isinstance` and the `fileno()`
        probe, become one private predicate, `_is_real_file(f)`. `isfileobj(f)` returns
        `_is_real_file(f) and sys.platform != "wasi"` (the review's F5). So "a real file" means
        on WASI exactly what it means natively: a `BufferedWriter` over a `BytesIO` is not one.
      - **The subclass rule.** In `write_array`, after the pickle branch, on WASI, when
        `_is_real_file(fp)` and `type(array).tofile` is not `ndarray.tofile`, the subclass's own
        `tofile` decides (`array.T.tofile(fp)` for a Fortran-ordered array, as the native branch
        does).
      - **Its test.** `test_save_masked_without_dup` sits next to the patch's other test. Its
        last line saves the masked array to `io.BufferedWriter(io.BytesIO())`, which must write,
        as natively.

      The amended patch is in the review folder (`051-review/author/`). It applies with the
      project's applier. Its three tests pass natively with WASI simulated (revision runs,
      EXECUTED). The drafting runs also checked, natively with `sys.platform`
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
      (EXECUTED both). Changing it would add WASI-only code to numpy's reader for a message.
      It is a deliberate difference, written in the README's platform paragraph.
      - **numpy's own test.** `test_file_truncated` expects the native message, so it would fail
        on WASI once numpy takes 0001. The amended 0001 therefore also changes that test: on
        WASI its pattern accepts the in-memory message too, behind
        `if sys.platform == "wasi"`. It passes natively under simulated WASI (revision runs,
        EXECUTED).
      - **In spec 050,** this empties the class `patch-0001-truncated-message` (Decision 12).
      - **Upstream.** The upstream draft proposes the same test change, so the README fact stays
        true while the test passes everywhere.
    - **The draft.** `context/upstream/patches/numpy-2.5.2/0001-npy-files-without-dup.md` and the
      facts in `../upstream/3-numpy-npy-wasi/pr.md` gain three points:
      - the `_is_real_file` predicate and the subclass rule;
      - the message a real file now gives on WASI;
      - the change to `test_file_truncated`, and why.

      The `Files:` line is unchanged: the same two files.
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
    Acceptance: `--accept-judge` (the new checks, the golden job, `wasm.py`'s readers, spec 050's
    edits), `--retire` (050's seven trap checks) and `--accept-growth` with the build's measured
    account. Growth is expected: the zip's
    bytes, every plain-binary run's fuel (Part 2), and the snapshot's numbers.

12. **What it changes in spec 050's judge, if 050 has landed** (a judge change, in this branch,
    following 050's condition C1):
    - **The classes stay, emptied.** The six `zip-code-names` classes (193 pandas failures and 1
      numpy failure), `patch-0001-masked-save` and `patch-0001-truncated-message` empty. Each
      keeps its class and an empty list file, and its gap is removed, so the scoreboard shows
      eight gaps become passes. Each keeps guarding: a returning failure shows as `+<node id>`.
    - **The trap entries go.** In the same acceptance:
      - the seven trap checks first pass, and their gaps are removed;
      - the seven `[[trap]]` entries are deleted, so their tests run in `numpy-core` again;
      - the seven trap checks, now absent, are retired with `--retire` (050, Decision 9). The
        landing notes say so, with the trap checks' last results.
    - **Two files return.** `test_casting_unittests.py` and `test_arraymethod.py` leave
      `not_selected` and run in `numpy-core`. They have never run past their first trap (the
      drafting hunt stopped at its cap of 40), so their outcomes are new (the review's F4):
      - a failure gets a class only with a named closer, and the landing notes give the counts;
      - a new trap in them gets a `[[trap]]` entry, a gap and a named follow-up specification,
        and the notes say so. It does not hold back the three parts that work.

    The `passes` metric rises; the notes give each group's new count.

13. **The README.**
    - "Known defects" (from 050, if landed) loses the traps and the warnings line.
    - The platform paragraph gains: a truncated `.npy` file read from a path raises the
      `ValueError` numpy gives for in-memory streams; `np.save` of a masked array raises
      `NotImplementedError`, as natively.
    - Tracebacks name zip members by their full zip path.
    - The patch count becomes 2.

    The CHANGELOG names the new patch and its path, the amended 0001, and the zip's code names.

14. **Notes for the builder** (the review's F7).
    - **The unit check over the built zip** walks nested code objects (`co_consts`), not only
      each module's top-level code. `compile` names them all today; a later writer might not.
    - **The path is written in two places:** the step 70 prefix and `STDLIB_ZIP`
      (`recipes/reactor_main.c:25`). A comment at each site names the other.
      `test_a_pandas_warning_names_the_callers_line` catches drift at judge time.
    - **The golden job's private calls** were confirmed natively in the revision runs. The
      `.expected` file is still made by `regen.py` from the oracle, as for every job.
    - **Measuring a zip change needs the plain binary.** A snapshot runs only beside the zip it
      was made with. With another zip it exited 1 after 0.76 G fuel (the review, EXECUTED).
    - **Order of the three commits:** Part 1, Part 2, Part 3. The scan's check comes with Part 1,
      so the review sees it red on the frozen set and green on the rebuilt one.

## Intent

The defects numpy's and pandas' own tests found are fixed or written down. The judge scans every
build for that class of trap, so the next one is caught at the build that brings it, and found
before any user meets it.

## Design

```
recipes/patches/numpy-2.5.2/0002-callback-signatures.patch   six callbacks, seven files (Decision 2)
recipes/patches/numpy-2.5.2/0001-npy-files-without-dup.patch  amended: _is_real_file, the subclass rule, its test,
                                                                 test_file_truncated on WASI (Decision 10)
context/upstream/13-numpy-callback-signatures/                 notes.md, pr.md (facts), fix.patch, evidence/
context/upstream/patches/numpy-2.5.2/0002-callback-signatures.md   six header lines; body points to the facts
context/upstream/patches/numpy-2.5.2/0001-npy-files-without-dup.md amended body
context/upstream/3-numpy-npy-wasi/pr.md                        the two behaviours
context/upstream/README.md                                     row 13
scripts/make_stdlib_zip.py                                     --code-prefix; pyc(source, prefix + name)
scripts/steps/70_zip.sh                                        --code-prefix "/usr/local/lib/python$PYTHON_TAG.zip/"
tests/harness/wasm.py                                          element, data, code bytes, name sections
tests/harness/callbacks.py                                     the scan (Decision 4): references, singles,
                                                                 minimum counts, coverage
tests/checks/test_v1_3_data_stack.py                           test_callbacks_have_the_types_cpython_calls,
                                                                 test_callbacks_job_matches_native[*],
                                                                 test_a_pandas_warning_names_the_callers_line[*],
                                                                 test_npy_files_round_trip's two new cases
tests/jobs/callbacks.py, callbacks.expected                    the golden job, from the oracle
tests/unit/test_callbacks.py                                   the scan on small modules built with wat2wasm:
                                                                 a referenced mismatch is found; an unreferenced
                                                                 look-alike is not; a code-referenced single is
                                                                 checked; a passive segment is a finding
tests/upstream/numpy.toml, pandas.toml                         Decision 12, if 050 has landed
README.md, CHANGELOG.md                                        Decision 13
```

## Scope

In: the six numpy callbacks; the scan of referenced method and getset tables and of
code-referenced single definitions; the zip's code names; patch 0001's masked-array rule, its
documented message and numpy's own test of it; spec 050's classes and traps as Decision 12 says.

Out:
- **Scanning `tp_*` slots and other C callback paths** (Decision 4).
- **Sending anything upstream:** the owner's.
- **numpy's other WASI behaviours already documented** (no `dup`, no `mmap`, no `ctypes` calls).
- **Changing CPython's zipimport.**
- **pandas' remaining suites:** spec 050's budget.

## Acceptance criteria

1. **Seen failing first, on the frozen set.**
   - `test_callbacks_have_the_types_cpython_calls` reports exactly the six numpy callbacks, with
     the exclusion list empty, and its minimum counts are met.
   - `test_callbacks_job_matches_native[*]` traps.
   - `test_a_pandas_warning_names_the_callers_line[*]` reports `pandas/io/parsers/readers.py:1798`.
   - The masked-array case of `test_npy_files_round_trip` reports `saved`.

   The builder records each.
2. A full build from pins in a clean clone:
   - step 40's log names both patches applied;
   - spec 020's zero-diff check passes with exactly the two;
   - `python.wasm`'s six callbacks have the types Decision 2 names (the scan says so);
   - every code object in every `.pyc` in the zip, nested ones included (`co_consts`, walked
     recursively), has `co_filename` equal to `/usr/local/lib/python315.zip/` plus its member
     name less `c` (a unit check over the built zip);
   - the zip's member list equals the frozen set's.
3. After the build, every check in criterion 1 passes. The golden job equals the oracle's output
   on both binaries. The scan's findings are empty, with no exclusion. Its coverage is at least
   the minimum counts, and close to the review's figures; the notes give them. Unit checks on
   crafted modules show:
   - a referenced mismatch is found;
   - an unreferenced look-alike is not;
   - an exclusion that stops matching is a finding;
   - a passive data segment is a finding.
4. **Spec 012:** the same-bytes rebuild on a second host (the release dry run's arm64 Linux job)
   gives the same `python.wasm`, zip and snapshot as the macOS build.
5. If spec 050 has landed, its suites pass with Decision 12's edits:
   - the eight emptied classes pass, with their gaps removed;
   - the seven trap checks are retired;
   - `numpy-core` runs the two returned files. Any new trap there has its entry, its gap and a
     named follow-up;
   - each group's `passes` is reported, and none falls.
6. `uv run ruff check`, `uv run ruff format --check`, and `uv run pytest` green.
   - `--accept-judge` names the new checks, the job, `wasm.py`'s new readers and spec 050's
     edits.
   - `--retire` names the seven trap checks, with their last results.
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

Built 2026-10-18 by a builder agent (Claude Opus 5.5) in the worktree `wasi_python-051`, branch
`spec/051-what-the-upstream-tests-found`, from main at `fe67910` (spec 040 accepted). The machine:
Apple arm64, macOS 26.5, 10 CPUs; Docker 29.7.2 for the Linux arm64 rebuild. Every claim below is
EXECUTED unless labelled; `uv run` only; the judge ran on the worktree's own `build/artifacts/`,
never with `--accept`. Scratch scripts and logs are in the session's scratch folder; the numbers
are written here. Not yet reviewed: the build review (`../reviews/`) is next, then the lane.

**Spec 050 had not landed** when this was built (main has no `tests/upstream/`). The lane's
order, settled after the build review (its F1): **051 lands first**, and 050 rebases onto 051 and
re-derives its tables (the seven traps, the `zip-code-names` and `patch-0001-*` classes, the two
returned files, the `passes` figures) on this rebuilt set. So Decision 12 and criterion 5 are
050's work, not this branch's; a line in 050's status says so. This branch touches none of 050's
judge files.

### What changed (three commits, one per part)

- **Part 1** (`fc6fe74`; was `19d0db5` before the build review's F3 rewrite):
  - `recipes/patches/numpy-2.5.2/0002-callback-signatures.patch`: the author's patch, byte for
    byte (`context/research/2026-10-18-what-the-upstream-tests-found/author/`).
  - Its draft `context/upstream/patches/numpy-2.5.2/0002-callback-signatures.md` (six header
    lines, `Files:` the seven paths, a body pointing to the facts and naming numpy's AI policy's
    clauses), and the facts sheet `context/upstream/13-numpy-callback-signatures/` (`notes.md`,
    `pr.md`, `fix.patch` = the carried patch against 2.5.2, to be rebased onto `main` when the
    owner asks; `evidence/` with the scan and the guest before and after, the native output,
    and the drafting runs' object types). `context/upstream/README.md` gains row 13.
  - `tests/harness/wasm.py` learns the function, element, data, code and name sections, and
    records an element segment that is not an active `funcref` list for table 0, or a data
    segment that is passive or not placed by a constant, in `Module.unread`.
  - `tests/harness/callbacks.py`: the scan of Decision 4 (members first, then referenced method
    arrays, referenced getset arrays, and code-referenced singles not inside a found table; a run
    is kept from its first referenced entry), `EXCLUDED = {}`, and `findings()`, strict both ways.
  - `tests/harness/plugin.py`: a `note` fixture; a passing check's note is its reason in
    `latest.json` (never compared). The scan's check uses it for its coverage.
  - Checks: `test_callbacks_have_the_types_cpython_calls` (v1.3, fast, `plain binary`; minimums
    2,500 / 1,000 / 1,500) and `test_callbacks_job_matches_native[plain|snapshot]` (v1.3, slow),
    over the golden job `tests/jobs/callbacks.py` and its `.expected` from `regen.py` under the
    pinned oracle (`jobs.JOBS` gains it, so `test_goldens_reproduce_under_the_pinned_oracle`
    covers it). Unit checks `tests/unit/test_callbacks.py` (7) on wat2wasm modules.
  - README: carried patches 2; six golden jobs; the callback sentence. CHANGELOG: its bullet.
- **Part 2** (`24b8ef5`; was `44ede8a`): `scripts/make_stdlib_zip.py --code-prefix` (refuses a prefix not
  absolute or not ending in `.zip/`); `scripts/steps/70_zip.sh` passes
  `"/usr/local/lib/python$PYTHON_TAG.zip/"`; a comment at it and at `recipes/reactor_main.c`'s
  `STDLIB_ZIP` names the other. Checks: `test_a_pandas_warning_names_the_callers_line[plain|
  snapshot]` and `test_zip_code_objects_carry_the_zip_path` (criterion 2's walk, run in the
  plain guest because the judge's host Python is 3.14 and cannot unmarshal 3.15 code). Unit
  checks: `pyc` names every nested code object; the prefix's three refusals. README and
  CHANGELOG lines.
- **Part 3** (`06f61aa`; was `fffd8ad`): `recipes/patches/numpy-2.5.2/0001-npy-files-without-dup.patch` is the
  author's amended patch, byte for byte. The 0001 draft and `../upstream/3-numpy-npy-wasi/pr.md`
  gain the three points; `fix.patch` there predates the amendment and is remade on rebase (said
  in both). `test_npy_files_round_trip` gains the masked and truncated cases. README platform
  paragraph and CHANGELOG lines.

### The frozen set, rebuilt first

`scripts/build.sh --plain` in the worktree at `fe67910`, before any change: `python.wasm`
`4befe9de64edc783`, `python-snapshot.wasm` `0cdc7b2bd78db6f5`, `python-stdlib.zip`
`ee1acace2fc1fb26`. Its `SHA256SUMS` equals main's `build/artifacts/SHA256SUMS` on every line but
`MANIFEST` (`diff` after dropping that line: empty), as the brief said. The failing-first runs
below are on this set.

### Criterion 1: seen failing first

On the base set, `uv run pytest tests/checks/test_v1_3_data_stack.py -k "callbacks or
pandas_warning or zip_code or npy_files"`: 8 failed.

- `test_callbacks_have_the_types_cpython_calls`: exactly the six numpy callbacks, exclusion list
  empty, minimums met (`scanned 3072 method-array entries, 1989 single definitions, 1125 getset
  entries, 429 member entries`):
  - `getter _supports_unaligned: table index 4598 has (i32) -> (i32), called as (i32, i32) -> (i32) (boundarraymethod__supports_unaligned)`
  - `getter scalar_input: table index 7906 … (array_converter_get_scalar_input)`
  - `method __copy__: table index 7134 has (i32) -> (i32), called as (i32, i32) -> (i32) (gentype___copy__)`
  - `method __reduce__: table index 10233 … (sfloat___reduce__)`
  - `method _get_castingimpl: table index 8262 has (i32, i32) -> (i32), called as (i32, i32, i32) -> (i32) (_get_castingimpl)`
  - `setter dtype: table index 6169 has (i32, i32) -> (i32), called as (i32, i32, i32) -> (i32) (array_descr_set)`
- `test_callbacks_job_matches_native[plain]` and `[snapshot]`: `trapped`. Each line alone, plain
  guest (`evidence/guest-before.txt` in the facts sheet): all six `copy.copy` calls, `a.dtype =
  np.float32`, the sfloat pickle, `_get_castingimpl(...)` and `.scalar_input` each trap; a control
  line with no such callback prints `2.5 [0 0 0 0]`. `_supports_unaligned` cannot be reached
  alone before `_get_castingimpl` works.
- `test_a_pandas_warning_names_the_callers_line[*]`: `[['ParserWarning',
  'pandas/io/parsers/readers.py', 1798]]`.
- `test_zip_code_objects_carry_the_zip_path`: 1,102 `.pyc`, 37,509 code objects, the first
  `/usr/local/lib/python315.zip/__future__.py: … names __future__.py`.
- `test_npy_files_round_trip[*]`: `masked saved [1 2 3] ndarray`; the truncated case already
  gave `truncated ValueError`, as designed (the type only).

### Criterion 2: the build

`scripts/build.sh --plain` in the worktree (every step remakes its outputs). Step 90 first
refused the then-untracked `0002` patch (`untracked recipe files (stage them first)`); staged,
step 90 alone then wrote the set.
- Step 40's log: `applied 0001-npy-files-without-dup.patch`, `applied 0002-callback-signatures.patch`,
  each file `Applied … cleanly`.
- Spec 020's zero-diff check: `test_source_tree_matches_its_tarball[numpy]` passes with the two
  (full judge run below).
- The scan on the new `python.wasm`: `0 findings` (`evidence/scan-after.txt`).
- `test_zip_code_objects_carry_the_zip_path`: passes, every code object of the 1,102 `.pyc`,
  nested ones included.
- The zip's member list: 1,760 members, the same names, order, dates, compression and modes as
  the frozen zip's; exactly the 1,102 `.pyc` differ in bytes, no data file.

The new set: `python.wasm` 31,760,992 bytes `5648e4c5143da71d` (the same size; six functions'
signatures), `python-snapshot.wasm` 65,533,118 bytes `f94dec535086b06c`, `python-stdlib.zip`
11,203,143 bytes `daf2cdd86357e617`, `MANIFEST` `c4474f7695491e67` (its `diff` with the base: the
two patch hashes, `reactor_main.c`, `make_stdlib_zip.py`, `70_zip.sh`, and `x-snapshot-zip`).

### Criterion 3: after the build

- The golden job equals the oracle's output on both binaries; each line alone runs
  (`evidence/guest-after.txt`). The oracle's `regen.py --check` (with `--online` once to set up
  the worktree's oracle) reproduced the five old goldens before `callbacks.expected` was written.
- The scan: no finding, no exclusion. Coverage 3,072 method-array entries, 1,989 singles, 1,125
  getsets, 429 member tables' entries (members are counted only when referenced). The review's
  figures were 3,072 / 1,990 / 1,125: of 2,029 code-referenced entries, 39 are array starts and
  1 is inside an array but not its start; the review subtracted the starts only, this scan
  leaves out every entry inside a found table.
- Unit checks (`tests/unit/test_callbacks.py`): a referenced mismatch is found (method, getter,
  single); an unreferenced look-alike is not; findings name no function without a name section;
  an exclusion that stops matching is a finding; a passive data segment and an element segment
  of another form are findings; a module with nothing to scan is a finding; `i32.const` operands
  are read at every position.
- One limit, written in the scan's docstring: members are found first, so a getset array whose
  getters all sit at table indices 1 to 20 with no doc would read as members. In this link those
  twenty are CPython's parser rules (`_tmp_6_rule` …, READ from the name section). Without the
  member pass the getset count would be 1,278, members misread as getsets.

### Criterion 4: the same bytes on a second host

A clean clone of the branch at `fffd8ad` (the pre-rewrite Part 3; the rewritten `06f61aa` differs from it only in `tests/harness/wasm.py`, `tests/unit/test_callbacks.py` and the facts sheet's `pr.md`, no recipe), built from empty `downloads/` and `build/` in the
`linux/arm64` container spec 040 used (image `wp040-arm64`: the pinned `debian:trixie-slim`, uv
0.9.22 checked by hash; its `run-build.sh`): `uname` `Linux 7.0.12-linuxkit aarch64`, Debian 13;
`00_download: 29 pins, 29 fetched, 29 verified`; step 40 `applied` both patches; `exit: 0`,
284 s (a benchmark fact). Its `SHA256SUMS` (`9595a1dd752ac96b…`) is byte-identical to the macOS
worktree build's (`diff`: empty): `python.wasm` `5648e4c5143da71d`, snapshot `f94dec535086b06c`,
zip `daf2cdd86357e617`, `MANIFEST` `c4474f7695491e67`. The x86_64 and Windows rebuilds are the
release workflow's (spec 040's gate), not run here.

### Criterion 6: the judge and the growth account

`uv run pytest` (full, slow included) on the rebuilt set: 1,165 passed, 10 skipped;
`251/254 pass · 0 gap · 3 blocked · 0 fail`; v1.3 27/27; `lost 0 · absent 0 · unrun 0 · gained
6 · grew 36`, `RED: 36 metric(s) grew`, red only for growth. The 6 gained are this spec's new
checks. Blocked: `wheel`, `three systems`, `prior-art clones`, as on main. `ruff check` and
`ruff format --check` clean on `src` and `tests`.

For the lane:
- `--accept-judge`: the new checks (the scan, the golden job on both binaries, the warning on
  both, the zip's code names), `tests/jobs/callbacks.py` and its `.expected` (and `jobs.JOBS`),
  `tests/harness/wasm.py`'s new readers, `tests/harness/callbacks.py`, the plugin's `note`, and
  `test_npy_files_round_trip`'s two new cases.
- `--retire`: none (050 has not landed; no trap check exists).
- `--accept-growth`, the measured account (base set against the new one; `measure.py`, the
  judge's driver, fixed clock):
  - **Zip bytes** +28,115 (11,175,028 → 11,203,143, +0.25%): every code object's `co_filename`
    gains `/usr/local/lib/python315.zip/` (Part 2). The prototype's estimate was +28,360.
  - **Snapshot bytes** +23,169 (65,509,949 → 65,533,118, +0.035%): the pre-imported modules'
    code objects in the heap carry the longer names (INFERRED from Part 2; the binary's own
    size did not change).
  - **Plain fuel**, from the longer names unmarshalled at each import (Part 2): `-c pass`
    242,161,579 → 242,196,369 (+34,790, +0.014%); `-c "import pandas"` 4,988,102,407 →
    4,991,551,151 (+3,448,744, +0.069%). In the judge, every plain-binary check grew by
    +22,602 to +3,416,842 (+0.009% to +0.093%; `test_longdouble_parses` the most in percent).
  - **Snapshot fuel** mostly fell: `-c pass` 82,143,381 → 82,060,117 (−83,264); 16 judge checks
    fell by 1,169 to 130,431 (−0.04% to −0.16%). It grew where the program imports modules
    after the snapshot: `test_stdlib_debugging_tools_import` +390,672,
    `test_ctypes_stand_in_names_what_packages_import[snapshot]` +189,714,
    `test_extra_preopens_work_on_the_snapshot[*]` +160,239,
    `test_packages_carry_their_metadata[snapshot]` +132,772, `test_the_guest_package_round_trips_
    through_the_door[snapshot]` +12,476; and `test_fuel_is_exact_across_tool_calls` +16,389. Why
    the snapshot's start fell was not studied. In all, 53 metrics changed: 37 rose (the ratchet
    counts 36 past its tolerance) and 16 fell.
  - **`test_npy_files_round_trip`** +116,270,927 plain (+8.5%) and +3,595,509 snapshot (+1.7%):
    the check's program gained two cases (a judge change), not product growth.
  - `python.wasm`'s bytes: unchanged (31,760,992).

The fast judge at the then-committed `fffd8ad` (`uv run pytest -m "not slow"`): 1,157 passed, 10
skipped, 8 deselected; `243/254 pass · 0 gap · 3 blocked · 0 fail · 8 deselected`; `lost 0 ·
absent 0 · unrun 0 · gained 4 · grew 31`. Both runs also say `unrun locally 1`:
`test_every_prior_art_clone_has_its_licence_recorded`, since the worktree has no prior-art
clones; it is not red, and the main tree has them.

### Criterion 7, and what is left

- README, CHANGELOG, both drafts, the facts sheet and `context/upstream/README.md` say what
  Decisions 3, 10 and 13 say; `test_carried_patches_follow_the_rules` passes with two patches.
- Decision 4a's sentence is in the status of each unlanded specification it names (035, 037,
  038, 039, 041, 042, 043, 044, 045, 046, 047; 040 has landed), on this branch, so the review
  sees what lands. 035's status also says its absolute byte and fuel baselines move with 051
  while its per-member figures hold (the build review's F5).
- Sending either draft upstream is the owner's.

### For the reviewer

- `tests/harness/callbacks.py`'s table rule: members first, a run kept from its first
  referenced entry, singles left out when inside any found table. The figures above against the
  review's.
- `tests/harness/wasm.py` reads a constant expression to its `end`: one `i32.const` gives the
  offset; any other expression of the extended-constant proposal (`global.get`, `i32.add` …)
  records its segment in `unread`, so the wall checks still read the binary the scan flags. Only
  an opcode outside that proposal raises (the build review's F4).
- The plugin's `note`: a pass's reason is now non-empty for one check.
- `test_zip_code_objects_carry_the_zip_path` runs in the guest, not on the host (the host's
  Python is 3.14).
- The README's sentence placement, and the snapshot fuel's fall, whose cause is not studied.

### Answers to the build review (2026-10-18)

The review (`../reviews/051-what-the-upstream-tests-found-2026-10-18.md`) asked for F1 to F3
before landing, F4 and F5 small. Each is answered in its Disposition; in short:

- **F1, the order.** 051 first; 050 rebases and re-derives (above, and in 050's status).
  Decision 4a's sentence is written into each unlanded build-class specification's status here.
- **F2, three rules unguarded.** `tests/unit/test_callbacks.py`'s module gains a getset whose
  setter has the wrong type (`st`), a method array that only code points at (`coded`, as numpy's
  scalar methods), and a method whose function returns nothing (`void`). Each of the review's
  mutants now fails the unit suite (EXECUTED, applied to `harness/callbacks.py` and restored,
  `cmp` identical): M2 (setters not checked) loses `setter st`; M11 (code references ignored)
  turns `method coded` into `single method coded` and the array count from 4 to 3; M8 (results
  not compared) loses `method void`.
- **F3, the intermediate commits.** The branch was rewritten from `fe67910` with `git reset
  --soft` and three part commits with explicit paths; Part 1 carries the blank line, and each
  commit's `ruff format --check` and `ruff check` were run on its own tree (`git archive`).
- **F4, extended constants.** As above; a unit check builds a data segment placed by
  `i32.add (i32.const 16) (i32.const 16)`: it is in `unread`, the next segment is read, and
  `wall_errors` is empty. Seen failing on the old reader: `WasmError: constant expression longer
  than one instruction`.
- **F5, 035.** Its status line (above).
- **The facts sheet's nit:** `pr.md` no longer says "the table below".

None of these changes a recipe byte or an artifact: the set judged above stands
(`5648e4c5…`, `f94dec53…`, `daf2cdd8…`, `MANIFEST` `c4474f76…`).
The full judge on that set after the rewrite (`uv run pytest`, slow included, no `--accept`):
1,166 passed, 10 skipped; `251/254 pass · 0 gap · 3 blocked · 0 fail`, v1.3 27/27; `lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 6 · grew 36` (red for growth only); `ruff check` and `ruff format --check` clean. The one more pass than before is the new unit check.
