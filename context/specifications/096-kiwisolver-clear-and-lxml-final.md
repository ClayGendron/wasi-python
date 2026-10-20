# 096 — kiwisolver's `tp_clear` returns `int`, `lxml.html.diff` imports, and the scan reads type slots

- **Status:** **drafted 2026-10-20** on `spec/096-kiwisolver-clear-and-lxml-final` from main
  `1ce7381`, with its research; **reviewed before build** the same day
  (`../reviews/096-kiwisolver-clear-and-lxml-final-spec-2026-10-20.md`, verdict "ready once
  findings 1 and 2 are written into Decision 3 and check 3, with their unit rows"); **revised
  against all of its findings** and rebased onto main `c091f3d` (roadmap only; the set is
  unchanged). *Disposition of the pre-build review* says where each went. **Confirmed for build** by
  the same reviewer (its *Confirmation*), with one Low written in (option 1). **Built 2026-10-20**
  on `0054f5b` (from an empty `build/`, base `c091f3d`); the dry run 39386471189's only red lines
  are its three claimed growth lines (*Landing notes*). A different agent reviews the build. It carries two upstream patches (§4.1) and changes the build
  recipe and the artifact set, so it was reviewed before it is built (constitution §5.6). A
  different agent reviews the build.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** **build-class** (§5.7): it adds two carried patches under `recipes/patches/`, which
  change `python.wasm`, the snapshot and the stdlib zip, and `MANIFEST` gains their two `recipe`
  lines. It fixes two packages already in the set; it adds none, so it is not a package entry in a
  wave. **And a judge change:** a widened callback scan (`tests/harness/callbacks.py`), three new
  goal checks (five nodes) and their unit rows; the lane accepts with `--accept-judge` and
  `--accept-growth`. Also `README.md`, `CHANGELOG.md` and the two drafts. The guest's imports and
  exports do not change; no line of `tests/public_api.txt` changes.
- **Depends on:** landed specifications only: 051 (the callback scan, which this widens), 023
  (kiwisolver, its step and its patch 0001), 046 (lxml, Decision 1: its Cython-compiled Python
  modules stay plain Python), 020 (carried patches). It meets 066, 043, 037, 038 and 044
  (Decision 8).
- **Research it stands on:** spec 066's survey,
  `context/research/2026-10-20-the-compiled-packages-own-tests-under-the-runtime.md` and its
  folder (`kiwisolver-trap.txt`, `failures.txt`), findings 1 and 2; it is on spec 066's branch
  (`055a38a`) until 066 lands. **The drafting runs** (EXECUTED 2026-10-20 on macOS arm64, in this
  worktree, on a private `cp -c -Rp` copy of main's set, wave 05's, `SHA256SUMS` `4eaf1c3d…`,
  `python.wasm` `b6953170…`, `build/lane.lock` absent): their scripts and outputs are in
  `../research/2026-10-20-the-slot-scan/`. The two patches and their drafts are in
  `../upstream/28-kiwisolver-tp-clear-returns-int/` and `../upstream/29-lxml-fake-cython-final/`.

## The problem

Spec 066's survey ran the compiled packages' own tests in the guest and found two defects in the
product, not in the tests.

1. **kiwisolver traps the guest whenever the garbage collector clears one of its objects.**
   kiwisolver's four `*_clear` functions return `void`. CPython calls `tp_clear` as
   `int (*)(PyObject *)`. Under WebAssembly the call's type does not match, and the guest ends in
   `wasm trap: indirect call type mismatch` at `gc_collect_main`. Any cycle that holds a
   `Variable`, `Term`, `Expression` or `Constraint` can do it, collected by `gc.collect()` or by
   the collector's own schedule. Carried patch 0001 fixed kiwisolver's 21 methods and getters,
   which spec 051's scan found; the scan did not find these four.
2. **`import lxml.html.diff` raises `TypeError: 'str' object is not callable`.** The guest runs
   `lxml/html/diff.py` as plain Python, with no Cython installed. Its stand-in `fake_cython` has no
   `final`, and its `__getattr__` answers every unknown name with the string `"object"`. So
   `@cython.final` calls a string.

Both are build-class fixes. And the first is a class, not an instance: a slot function whose
wasm type is not the type CPython calls it with. The judge must catch that class, so it cannot
come back in another package.

## Decisions

### 1. Why spec 051's scan missed kiwisolver's four (READ)

Spec 051's scan reads three kinds of table: `PyMethodDef` arrays, single `PyMethodDef`s that
code points at, and `PyGetSetDef` arrays. Its Decision 4 put the rest out of scope, in so many
words: "`tp_*` slots of static type objects; `PyType_Slot` arrays; number, sequence and mapping
method structs; C callbacks passed to C APIs … The first two can follow when a defect shows the
need." The callback scan's docstring says the same.

kiwisolver builds its four types from `PyType_Spec`s. Each lists
`{ Py_tp_clear, void_cast( X_clear ) }` in its `PyType_Slot` array (READ, `py/src/term.cpp:190`
and the three like it). So the four sit in exactly the table kind the scan did not read.

- **The survey's guess was not the reason.** It said the functions "pass through kiwisolver's
  `void_cast`". That cast changes the C type only; the table index in the image is the same. The
  scan never looked at the slot array at all.
- **This is the defect that "shows the need."** So this specification widens the scan to the
  first two kinds, and to the method structs their types point at, and to the same mistake in
  module definitions (Decision 3).

### 2. The kiwisolver patch: upstream's own fix (EXECUTED and READ)

- **Upstream has it.** kiwisolver's pull request #245, "Build wheels for WASM/Pyodide also"
  (merged 2026-09-10, commit `4df2f39c01`), has a second part titled "Fix signature of `tp_clear`
  methods": each `X_clear` returns `int` and ends with `return 0;`. It is on `main`, after 1.5.1
  (tagged 2026-08-28), and in no release (READ, GitHub and PyPI, 2026-10-20).
- **The carried file**, `recipes/patches/kiwisolver-1.5.1/0002-tp-clear-returns-int.patch`, is
  that commit's four C++ hunks, made against the 1.5.1 tarball with 0001 applied, in `git diff`
  form (`../upstream/28-kiwisolver-tp-clear-returns-int/fix.patch`, SHA-256 `138e3cbe…`, 9 lines
  in and 4 out in `py/src/constraint.cpp`, `expression.cpp`, `term.cpp`, `variable.cpp`). Its
  changed lines equal the commit's byte for byte (EXECUTED: the `+` and `-` lines `diff`ed). The
  commit's two CI workflow changes build nothing here and are left out.
- **It applies** on top of 0001 with no offset, and to the pristine tarball too (EXECUTED,
  `git apply --check`). The two patches touch different functions. The judge's patch rules
  (`patch_shape_errors`) find nothing (EXECUTED).
- **Natively nothing changes.** `delete_garbage` ignores the result (`(void) clear(op)`,
  `Python/gc.c:1105`), and each `X_dealloc` calls `X_clear` directly and ignores it too.
- **Its draft** (`pr.md` in the same folder) has the six header lines, status `merged
  https://github.com/nucleic/kiwi/pull/245`, as matplotlib's 0001 does: nothing to send. It moves
  at build time (Design).

### 3. The scan reads type slots, slot arrays and module definitions

`tests/harness/callbacks.py` gains a second scan, `scan_slots(mod)`, with its own report and its
own check (check 3). It reads the plain binary's image as spec 051's scan does (`harness/wasm.py`,
the same `_Image`, `data_words` and `code_constants`), and keeps only what something points at:
an address that appears as an aligned word in the image or as an `i32.const` operand.

**A C string**, wherever this Decision says so, is 1 to 256 bytes in 0x20–0x7E, ending in NUL
(a space is allowed: CPython names two static types `<dummy key> type` and `symtable entry`).

**Three kinds of record** (the layouts READ from CPython 3.15.0's headers, wasm32, 4-byte
pointers; the offsets EXECUTED: `type`'s own record and the 481 types below read with them):

- **Static `PyTypeObject`s** (212 bytes). A **static record** is an aligned word equal to
  `_Py_STATIC_IMMORTAL_INITIAL_REFCNT` (`7 << 28` on 32-bit, `Include/refcount.h:67`, which
  `PyObject_HEAD_INIT` writes into every static object). **Every static record is classified,
  and every one the scan drops is counted by its reason** (the pre-build review's F1):
  - `type` itself is the one static record whose `ob_type` is its own address. Exactly one is
    required; none, or two, is a finding.
  - A **metatype** is `type`, or a static record with a C-string `tp_name`, `ob_type` 0 or a
    metatype, and a `tp_basicsize` of at least 212 (its instances are type objects, as numpy's
    `_DTypeMeta`'s are) or a `tp_base` that is a metatype; found to a fixed point. This
    over-includes (ten today, some only large iterators), which can only add records to read.
  - A static record shaped as a module definition (Part 3's rule) goes to Part 3.
  - Dropped, and counted: a record whose `ob_type` is neither 0 nor a metatype (a static
    instance: a string, an int, `None`; 5,188 today); a record whose `tp_name` is neither 0 nor a
    pointer into the image (1 today: bytes of a string table that read as the refcount).
  - What is left is a **type candidate**: `ob_type` 0 (filled by `PyType_Ready`, as Cython and
    numpy write it) or a metatype, and `tp_name` 0 or a pointer into the image. A candidate
    must be referenced: unreferenced candidates are counted, and check 3 holds the count at 0
    (0 today).
  - **A referenced candidate whose `tp_name` points into the image but at no C string is a
    finding**, `type at <address>: does not read as a type (tp_name)`. One whose `tp_name` is 0
    is a type named at run time and is read as `<tp_name NULL at <address>>` (one today: a
    numpy DType whose name numpy fills in).
    Because a metatype needs a C-string `tp_name`, a metatype named at run time would not
    classify its instances; so **a dropped record whose `ob_type` is a type named at run time is
    a finding** (none today), and check 3 holds the types named at run time at most 1 (the
    confirmation's Low, option 1).
  - Every other referenced candidate is a **type**.
  - Its function fields are checked: `tp_dealloc`, `tp_getattr`, `tp_setattr`, `tp_repr`,
    `tp_hash`, `tp_call`, `tp_str`, `tp_getattro`, `tp_setattro`, `tp_traverse`, `tp_clear`,
    `tp_richcompare`, `tp_iter`, `tp_iternext`, `tp_descr_get`, `tp_descr_set`, `tp_init`,
    `tp_alloc`, `tp_new`, `tp_free`, `tp_is_gc`, `tp_del`, `tp_finalize`, `tp_vectorcall` and
    `_tp_iteritem` (offset 208; set by `bytes`, `list`, `tuple` and `str`, and returning a
    two-word struct through a hidden pointer).
  - And the suites its `tp_as_async`, `tp_as_number`, `tp_as_sequence`, `tp_as_mapping` and
    `tp_as_buffer` point at, field by field. A suite that lies past the image is zero at load (an
    empty static struct, in `.bss`) and holds nothing to check; it is counted, not read.
  - **A type that does not read as a type is a finding**, never skipped: a function field that is
    not a table index, a pointer field (`tp_as_*`, `tp_doc`, `tp_methods`, `tp_members`,
    `tp_getset`, `tp_base`) that is neither 0 nor in static memory (the image's base or above,
    since `.bss` lies past the image), or a `tp_basicsize` of 1 MiB or more (or `tp_itemsize` of
    64 KiB or more).
- **`PyType_Slot` arrays, through their `PyType_Spec`.** A spec is a referenced 20-byte record
  `{name, basicsize, itemsize, flags, slots}` whose `name` is a C string, whose sizes are under
  1 MiB and 64 KiB, and whose `slots` points at a readable first entry. An entry is readable when
  its id is a known slot id (`Include/slots_generated.h`) and, for a function slot, its value is
  a table index or 0. **A function slot holding 0 is readable, skipped and counted, never
  checked** (CPython's legacy iterator only logs "unwanted NULL", `Python/slots.c`; the review's
  L3). From the first entry **the whole run must read to its zero end, or it is a finding.** A
  spec-shaped record whose `slots` points past the image is dropped and counted (24 today, every
  one a method table or keyword list that reads as a record). Data slots (`tp_doc`, `tp_base`,
  `tp_bases`, `tp_methods`, `tp_members`, `tp_getset`, `tp_token`) are skipped. The four ids 3.15 renumbered
  are read in both forms: `bf_getbuffer`, `bf_releasebuffer`, `mp_ass_subscript` and
  `mp_length` are 1 to 4 under a limited API before 3.15 and 88 to 91 otherwise.
- **Static `PyModuleDef`s** (52 bytes). A candidate is the static refcount, then `ob_type`,
  `m_init`, `m_index` and `m_copy` all 0, then `m_name` a C string, referenced. Checked:
  `m_traverse`, `m_clear`, `m_free`, and the `m_slots` array's `Py_mod_create` and `Py_mod_exec`
  (ids 1 and 2, or 84 and 85); its data slots (`Py_mod_multiple_interpreters`, `Py_mod_gil`,
  `Py_mod_abi`, `Py_mod_token`) are skipped. A module definition that does not read as one, or a
  slot entry with an unknown id, is a finding. A slot array past the image is all zero at load
  (in `.bss`): empty, or filled by code at run time as pybind11's are. It holds nothing to check,
  and is counted, not read.

**The types CPython calls** (`Include/object.h`, `Include/cpython/object.h`; every pointer,
`Py_ssize_t`, `Py_hash_t`, `int` and enum is `i32` on wasm32):

| function type | wasm type | slots |
|---|---|---|
| `destructor`, `freefunc` | `(i32) -> ()` | `tp_dealloc`, `tp_del`, `tp_finalize`, `tp_free`, `m_free` |
| `inquiry`, `lenfunc`, `unaryfunc`, `reprfunc`, `hashfunc`, `getiterfunc`, `iternextfunc` | `(i32) -> (i32)` | `tp_clear`, `tp_is_gc`, `nb_bool`, `sq_length`, `mp_length`, `tp_repr`, `tp_str`, `tp_hash`, `tp_iter`, `tp_iternext`, the unary `nb_*`, `am_await`, `am_aiter`, `am_anext`, `m_clear`, `Py_mod_exec` |
| `binaryfunc`, `getattrfunc`, `getattrofunc`, `ssizeargfunc`, `objobjproc`, `allocfunc` | `(i32, i32) -> (i32)` | the binary `nb_*`, `sq_concat`, `sq_repeat`, `sq_item`, `sq_contains`, `sq_inplace_*`, `mp_subscript`, `tp_getattr`, `tp_getattro`, `tp_alloc`, `Py_mod_create` |
| `ternaryfunc`, `setattrfunc`, `setattrofunc`, `richcmpfunc`, `descrgetfunc`, `descrsetfunc`, `initproc`, `newfunc`, `traverseproc`, `ssizeobjargproc`, `objobjargproc`, `sendfunc`, `getbufferproc` | `(i32, i32, i32) -> (i32)` | `tp_call`, `nb_power`, `nb_inplace_power`, `tp_setattr`, `tp_setattro`, `tp_richcompare`, `tp_descr_get`, `tp_descr_set`, `tp_init`, `tp_new`, `tp_traverse`, `sq_ass_item`, `mp_ass_subscript`, `am_send`, `bf_getbuffer`, `m_traverse` |
| `releasebufferproc` | `(i32, i32) -> ()` | `bf_releasebuffer` |
| `vectorcallfunc` | `(i32, i32, i32, i32) -> (i32)` | `tp_vectorcall` |
| `_Py_iteritemfunc` | `(i32, i32, i32) -> ()` | `_tp_iteritem` |

A finding reads `type <tp_name>.<field>`, `spec <name>.<slot>` or `module <m_name>.<field>`,
then `: table index <n> has <type>, called as <type>`, with the function's name when the name
section has it, as spec 051's findings do. Spec 051's `EXCLUDED` and `findings()` serve both
scans: still empty, still strict both ways, and a mismatch is fixed by a carried patch or an
upstream release, never by an exclusion.

**What it found on main's plain binary** (EXECUTED, the drafting scanner
`../research/2026-10-20-the-slot-scan/slotscan.py`, which embodies these rules,
`slotscan-main-4eaf1c3d.txt`, 3.7 s; re-run after the pre-build review):

- **Exactly four findings**: `spec kiwisolver.Constraint.tp_clear`, `….Expression.tp_clear`,
  `….Term.tp_clear` and `….Variable.tp_clear`, each `(i32) -> ()`, called as `(i32) -> (i32)`.
  No other, no "does not read as" finding, and every named record of check 3 read.
- **Coverage**: 481 static types (10 metatypes; `<dummy key> type` and `symtable entry` among
  them, and one named at run time; 2,675 function fields and suite entries checked; 40 number,
  42 sequence, 46 mapping, 14 buffer and 6 async suites), 454 `PyType_Spec`s (3,101 slot
  entries, 2,374 functions checked, no NULL function slot; specs: pandas' Cython types 265, the
  stdlib's, kiwisolver's 6, pybind11's one), 149 module definitions (311 functions checked; 7 slot arrays past the
  image: matplotlib's six pybind11 modules, `_c_internal_utils`, `_image`, `_path`, `_tri`,
  `_backend_agg` and `ft2font`, and Pillow's `_imagingmorph`, whose array is empty, `{0, NULL}`).
  5,360 functions in all. Dropped and counted: 5,188 static instances, 1 record whose
  `tp_name` is not a pointer, 24 spec-shaped records with slots past the image; 0 unreferenced
  type candidates.
- **It catches what it claims** (EXECUTED, `slotscan_mutants.py`, `slotscan_mutants.out`: one word
  of the parsed image rewritten each time, the binary untouched; each line prints the total, so
  nothing else new can hide, the review's L6): `numpy.ndarray`'s and `ImagingCore`'s
  `tp_clear`, `int`'s `nb_bool` and `_regex`'s `m_clear`, each pointed at a destructor, are each
  found by name, total 5 (the four plus one). `kiwisolver.Term`'s spec with its `slots` word
  zeroed: its `tp_clear` finding goes, and the two named records (`spec kiwisolver.Term`, `spec
  slot kiwisolver.Term.tp_clear`) come, total 5, while every minimum stays met (453 specs). And
  `numpy.ndarray`'s `tp_name` pointed at a zero word: `does not read as a type (tp_name)` and its
  named record unread, total 6.
- **The open branches' sets** (EXECUTED, read-only): 039's, 043's and 086's `python.wasm` give the
  same four and nothing else. 037, 038 and 044 have no built set to scan.

**Out of the scan, and said so in its docstring:** slots that code fills at run time
(pybind11's heap types, `PyType_Ready`'s inherited slots, a type object made by
`PyType_FromMetaclass` from a spec built in code); type objects, specs, slot arrays and module
definitions that C++ dynamic initialization fills (they lie in `.bss`, past the image); a spec
whose first entry is neither a known id nor a NULL function slot (irreducible by shape: even
filtered by flags and size, more than 300 `PyMethodDef`s read as specs, the review measured);
the new `PySlot` arrays of 3.15 (`PySlot`, `PyModExport`), which no linked module uses (READ:
only CPython's test modules `_testmultiphase`, `xxlimited`, `_testlimitedcapi`, `_testcapi`,
none of which is in the set); and C callbacks passed to C APIs (`qsort`, LAPACK), as before.
The docstring also names the ids 92 to 110 (`Py_slot_subslots`, `Py_tp_slots`, `Py_tp_name`,
`Py_mod_state_clear` and the rest), which belong to `PySlot` arrays: one in the middle of a
`PyType_Slot` run is a finding, as it should be, and the name tells a reader why.

### 4. The lxml patch: upstream's own line, not a recipe (EXECUTED and READ)

§4.1 prefers a recipe file. None does this job:

- **A stand-in `cython` module in the zip** would make `import cython` succeed for every program
  in the guest, where natively it fails without Cython. It changes behaviour beyond lxml, and
  misleads a program that tests for Cython. Refused.
- **Compiling `lxml.html.diff` with Cython**, as upstream's wheels do, is spec 046's Decision 1,
  declined there: a new pinned tool, a fifth builtin with a generic init name
  (`PyInit_diff`), for speed no check needs. Not reopened.
- **An edit in step 54** (a `sed` on the unpacked tree) is a source change by another name. It
  would escape the tree check that holds each tree to its tarball plus exactly the recorded
  patches (spec 020). Refused.
- **A file beside `diff.py`** cannot help: `import cython` is absolute, so nothing in
  `lxml/html/` answers it.

So it is a carried patch, and upstream already has its line:

- **Upstream.** lxml's pull request #477, "Support freethreading Python" (merged 2026-05-25,
  commit `dce45bd6e9`), adds `def final(self, func): return func` to `fake_cython`, right after
  `cclass`. It is on `master` and in 7.0.0a1 to 7.0.0b1, not on the `lxml-6.1` branch and in no
  final release (READ, GitHub and PyPI, 2026-10-20).
- **The carried file**, `recipes/patches/lxml-6.1.3/0001-fake-cython-final.patch`, is that one
  line against the 6.1.3 tarball (`../upstream/29-lxml-fake-cython-final/fix.patch`, SHA-256
  `0291f7c0…`, 1 line in, `src/lxml/html/diff.py` only). The rest of #477 is free-threading work,
  left out. `patch_shape_errors` finds nothing (EXECUTED).
- **It is the only such gap.** `diff.py` is the only one of lxml's five plain-Python fallbacks
  that uses a decorator `fake_cython` lacks (READ, `grep` of `builder.py`, `sax.py`,
  `_elementpath.py`, `html/_difflib.py`); the survey found no other import failing but
  `lxml.cssselect` (not shipped, by spec 046's choice).
- **Native shows the same bug** (EXECUTED, `native-runs.out`, CPython 3.15.0 from the pinned
  archive, lxml 6.1.3's wheel, no Cython): the sdist's `diff.py`, loaded as `lxml.html.diff`,
  raises the same `TypeError`; with the line, it loads. Upstream never sees it because its builds
  compile the module and its test environments install Cython.
- **In the guest** (EXECUTED, `guest_patched_diff.out`, main's set, both binaries): the same
  loader over a granted copy of `diff.py` raises the `TypeError`; over the patched copy,
  `htmldiff("<p>Hello world</p>", "<p>Hello there world</p>")` returns native's
  `<p>Hello <ins>there</ins> world</p>`.
- **Its draft** (`pr.md`) has status `merged https://github.com/lxml/lxml/pull/477`, title the
  pull request's, and says the patch is one line of it. Nothing to send. A backport to
  `lxml-6.1` is the owner's choice (*The owner's choices*).
- **No licence line.** lxml and kiwisolver are BSD-3-Clause, which asks no notice of
  modification; `MODIFIED` in `scripts/assemble_artifacts.py` holds regex's Apache-2.0 lines only
  (spec 047, Decision 10) and does not change. `LICENSES/` does not change.

### 5. Check 1: one cycle through all four kiwisolver types (EXECUTED)

The program (`../research/2026-10-20-the-slot-scan/kiwi_cycle.py`) disables the collector, makes
a `Variable`, a `Term` (`v * 2.0`), an `Expression` (`t + 1.0`) and a `Constraint` (`e >= 0.0`),
puts all four in a list that also holds itself, sets the list as the variable's context, drops
every name, and calls `gc.collect()`. It prints the three type names, `collected True` (at least
five objects collected) and `ok`.

- **Why each `tp_clear` is reached** (READ, `delete_garbage`, `Python/gc.c:1083`, INFERRED for
  the order). The collector calls `tp_clear` on each collectable object in list order, which here
  is the order of allocation: the variable, the term, the expression, the constraint, then the
  list. The list holds all four and itself, so each kiwisolver object is still alive when its
  turn comes, and each type's `tp_clear` is called through its pointer in turn. Only the list's
  own clear frees them.
- **Seen failing on main's set** (EXECUTED, `kiwi_cycle_flushed.out`, the program with its first
  line flushed): both binaries print `Term Expression Constraint`, then trap at the collection
  (the runner's "bad signature"; plain 198,270,795 fuel, snapshot 6,805,770).
- **Native** (EXECUTED, `native-runs.out`, kiwisolver 1.5.1's wheel): `Term Expression
  Constraint`, `collected True`, `ok`.
- **Which `tp_clear` trapped is not observable from Python**, and only the first call can trap
  before the patch. So check 1 proves the path, and check 3 proves each pointer's type; the
  build's scan shows all four `(i32) -> (i32)`.
- **matplotlib's constrained layout did not trap** (EXECUTED, `mpl_layout_gc.py`, both
  binaries): a 2×2 constrained-layout figure drawn, closed and collected. Its kiwisolver
  variables are leaves whose containers are cleared first. So the README and the CHANGELOG say
  "a cycle that holds a kiwisolver object", not "constrained layout".

### 6. No new step, pin or recipe file

Both patches go through the existing `patch_tree` call of their step; `scripts/` is not edited,
and no input is added to `downloads/SHA256SUMS`. The drafting scanner under `../research/` is
evidence, not judge code: the judge's version is written fresh in `tests/harness/callbacks.py`
from Decision 3's rules, with its own unit rows.

### 7. The README and the CHANGELOG

- **The patches row** (line 41): "upstream patches carried: 12", its words "or, for
  matplotlib's, kiwisolver's `tp_clear` fix and lxml's `fake_cython` line, already merged
  upstream".
- ***How it is built*** (line 424): the stale "seven today" list becomes the twelve: numpy's
  `.npy` fix and its callback signatures, matplotlib's enum fix from upstream, Pillow's,
  kiwisolver's and regex's callback signatures, kiwisolver's `tp_clear` fix from upstream,
  regex's timeout ticks, libxml2's file input without `dup()`, pandas' Styler templates and
  networkx's graph atlas from a zip, and lxml's `fake_cython` line from upstream.
- ***lxml in the guest***: after "is in the zip", one sentence: "lxml's five modules that
  upstream compiles with Cython for speed (`lxml.builder`, `lxml.sax`, `lxml._elementpath`,
  `lxml.html.diff`, `lxml.html._difflib`) run as plain Python, as on PyPy; `lxml.html.diff`
  needs one line lxml 7 carries (`recipes/patches/lxml-6.1.3/0001-fake-cython-final.patch`)."
- **CHANGELOG**, under `## 0.1.0a8 — unreleased`: "**A garbage cycle holding a kiwisolver object
  is collected, not a trap** (spec 096; spec 066's survey): kiwisolver's `Variable`, `Term`,
  `Expression` and `Constraint` declared `tp_clear` as returning nothing, so the collector's call
  ended the guest in `indirect call type mismatch`; carried patch
  `recipes/patches/kiwisolver-1.5.1/0002-tp-clear-returns-int.patch` is upstream's fix (#245),
  until a kiwisolver release has it. **`import lxml.html.diff` works**: its plain-Python form
  lacked `cython.final` without Cython; carried patch
  `recipes/patches/lxml-6.1.3/0001-fake-cython-final.patch` is upstream's line (#477), until lxml
  7.0. **The judge's callback scan reads type slots**: static type objects and their method
  suites, `PyType_Slot` arrays and module definitions, 5,360 functions on today's set, where spec
  051's read method and getset tables."

### 8. Where this meets other specifications

- **066** (the compiled packages' own tests). Its survey found both defects, and **066 depends
  on 096** (066 at `82f2d6c`, *Depends on*; its confirmation's C3): it is built after 096 lands,
  or stacked on 096's reviewed tip, and its re-survey runs on a set with 096. If 096 slipped, 066
  would keep kiwisolver `later` with `closes_with = "spec 096"` and give lxml the class
  `lxml-html-diff`, closed by spec 096 (three members: `test_diff.txt`, `test_diff.py`,
  `lxml.html.diff`'s docstrings). **If 066 nonetheless lands first**, 096's builder closes that
  `later` entry and that class: kiwisolver becomes a suite under 066's rules, with its caps from
  a measured run on 096's set, and the `lxml-html-diff` class and its members go. The builder
  names each change in `--accept-judge` and drops that flag's words "no existing expectation
  edited". If the kiwisolver group then shows any failure but the trap, the builder stops and
  hands it to 066; it adds no allowance (the pre-build review's L5).
- **037, 038, 044** (scipy, scikit-learn) and **043** (contourpy): their builds meet the widened
  scan as spec 051's Decision 4a made them meet the first. When 096 lands, the lane adds to each
  unlanded build-class specification's status: "spec 096's slot scan is green, and a mismatch it
  finds is fixed by a carried patch or an upstream release, never by an exclusion." scipy's
  hand-written types are the likeliest place for a finding. contourpy's and pybind11's types are
  heap types made at run time, outside the scan.
- **Upstream folder numbers:** 28 and 29 are the next free across main and the open branches
  (26 and 27 are 037's, 038's and 044's). If another branch lands with either first, the builder
  renumbers.

## Intent

A program whose garbage holds a kiwisolver object is collected, not killed. `import
lxml.html.diff` works as natively. And the judge reads every static slot table CPython calls
through, so a slot of the wrong type in any package is a red check, not a trap in a user's
program.

## Design

| file | change |
|---|---|
| `recipes/patches/kiwisolver-1.5.1/0002-tp-clear-returns-int.patch` | new: `../upstream/28-kiwisolver-tp-clear-returns-int/fix.patch` byte for byte (Decision 2) |
| `recipes/patches/lxml-6.1.3/0001-fake-cython-final.patch` | new: `../upstream/29-lxml-fake-cython-final/fix.patch` byte for byte (Decision 4) |
| `context/upstream/28-…/pr.md` → `context/upstream/patches/kiwisolver-1.5.1/0002-tp-clear-returns-int.md`; `context/upstream/29-…/pr.md` → `context/upstream/patches/lxml-6.1.3/0001-fake-cython-final.md` | moved unchanged (`git mv`) at build time; `fix.patch` stays in each folder |
| `context/upstream/README.md` | rows 28 and 29: carried, upstream's merged change, nothing to send |
| `tests/harness/callbacks.py` | `scan_slots` and its report (Decision 3); the module docstring's "Out of the scan" now names only what Decision 3 leaves out |
| `tests/checks/test_v1_3_data_stack.py` | check 3, with its minimums |
| `tests/checks/test_v1_3_matplotlib.py` | check 1 |
| `tests/checks/test_v1_3_lxml.py` | check 2 |
| `tests/unit/test_callbacks.py` | check 4's rows |
| `README.md`, `CHANGELOG.md` | Decision 7 |

No step script changes: step 55 already applies kiwisolver's patches and step 54 lxml's
(`patch_tree`, which applies every patch in the tree's folder). No pin changes.

## The checks, first

Each is written before the change it judges, and each was, or will be, seen failing first.

1. **v1.3, `test_a_cycle_through_kiwisolver_objects_is_collected[which]`**
   (`tests/checks/test_v1_3_matplotlib.py`, both binaries, fast tier). Decision 5's program by
   `-c`; it asserts exit 0 and stdout exactly `Term Expression Constraint\ncollected True\nok\n`,
   native's output (EXECUTED, `native-runs.out`). No matplotlib data is needed. It records fuel.
   Seen failing first: it traps on main's set on both binaries (EXECUTED).
2. **v1.3, `test_lxml_html_diff_imports[which]`** (`tests/checks/test_v1_3_lxml.py`, both
   binaries, fast tier). `from lxml.html.diff import htmldiff`, then
   `print(htmldiff("<p>Hello world</p>", "<p>Hello there world</p>"))`; it asserts exit 0 and
   stdout exactly `<p>Hello <ins>there</ins> world</p>\n`, native's output (EXECUTED,
   `native-runs.out`). It records fuel. Seen failing first: on main's set the import raises the
   `TypeError` on both binaries (EXECUTED, `drafting-runs.out`).
3. **v1.3, `test_type_slots_have_the_types_cpython_calls`** (`tests/checks/test_v1_3_data_stack.py`,
   fast, needs `plain binary`, beside spec 051's check). `callbacks.scan_slots` over the plain
   binary; `callbacks.findings` of it must be empty, and its coverage at least the minimums, set
   from main's set with room, so a toolchain change cannot make it pass by finding nothing:
   - at least 400 static types (481);
   - at least 380 `PyType_Spec`s (454);
   - at least 120 module definitions (149);
   - at least 4,500 slot functions checked (5,360);
   - **exactly 0 unreferenced type candidates** (0; the pre-build review's F1);
   - **at most 1 static type named at run time** (1; the confirmation's Low).

   **And the named records** (the pre-build review's F2), each of which the report must have read,
   one or more per compiled package with a static record, so one package's tables cannot vanish
   under the minimums:
   - the specs `kiwisolver.Constraint`, `kiwisolver.Expression`, `kiwisolver.Term` and
     `kiwisolver.Variable`, each with its `tp_clear` checked;
   - the spec `pandas._libs.tslibs.timestamps._Timestamp` (pandas' Cython types);
   - the types `type`, `numpy.ndarray`, `ImagingCore` (Pillow) and `lxml.etree._Element`;
   - the module definitions `_regex` and `ft2font` (matplotlib).

   A named record not read is a finding, `named record not read: <kind> <name>`. The report keeps
   the names it read, by kind, for this. Its coverage, with the drops counted by reason, is the
   pass's reason in `latest.json`, as spec 051's is. Seen failing first: on
   main's set it reports exactly Decision 3's four kiwisolver findings (EXECUTED by the drafting
   scanner; the builder re-sees it with the judge's own code and records the message).
4. **Unit rows, `tests/unit/test_callbacks.py`** (small modules built with wat2wasm, as spec 051's
   rows are; no artifact needed). Each fails on main, where `scan_slots` does not exist, and the
   rules marked † each get a mutant that fails without them (the builder records each):
   - a static type (`ob_type` 0) whose `tp_clear` is `(i32) -> ()` is found as
     `type <name>.tp_clear`, and its `tp_dealloc` `(i32) -> ()` is not;
   - a static type named with a space (`a b`) is read and its fields checked † (F1);
   - a referenced static record, `ob_type` 0, whose `tp_name` points into the image at bytes
     that are no C string (one below 0x20): `does not read as a type (tp_name)` † (F1); the same
     with `tp_name` 0: read as a type named at run time; a static record whose `ob_type` is that
     type: a finding †; a second type named at run time: check 3's bound turns red † (the
     confirmation's Low);
   - an unreferenced type candidate: counted, and check 3's bound turns red on it † (F1); a static
     instance (`ob_type` a non-metatype) and a record whose `tp_name` is not a pointer: each
     counted under its reason, no finding;
   - `type` (its `ob_type` itself), a metatype (`tp_basicsize` 212 or more), and an instance of
     the metatype whose `tp_repr` has one parameter too few: found †;
   - a static type whose `tp_as_number` points at a suite with a two-parameter `nb_bool`: found;
     a suite past the image: counted, not read;
   - a type whose `tp_traverse` is not a table index: "does not read as a type" †;
   - no candidate for `type`: a finding †;
   - a referenced `PyType_Spec` whose slots hold a void `tp_clear`: found; the same record
     unreferenced: not †;
   - a slot run that breaks before its zero end (an unknown id after a good entry): a finding †;
   - a NULL function slot as a spec's first entry and as a later one: the spec is read, the
     entry counted, no finding † (L3);
   - a module whose named records are all present passes the named-record rule; with one named
     spec's `slots` word zeroed, the minimums still met, `named record not read` is the finding †
     (F2);
   - old and new ids (`mp_length` as 4 and as 91) each checked as `(i32) -> (i32)` †;
   - a `PyModuleDef` whose `m_clear` is `(i32) -> ()`: found; its `Py_mod_exec` slot with two
     parameters: found; a slot array past the image: counted, not read;
   - an exclusion that matches no slot finding: a finding (the shared `findings()`).
5. **The patch rules and trees** (existing): `test_carried_patches_follow_the_rules` (the README's
   count 12, the CHANGELOG naming both patches, each draft's six header lines and `Files:`) and
   `test_source_tree_matches_its_tarball[kiwisolver]` and `[lxml]` cover both patches by
   construction. Seen failing first: the builder shows the lxml tree check failing on a tree with
   the patch applied and the patch file absent.

## Scope

In: Decisions 1 to 5. Out:

- **kiwisolver's, lxml's and the others' own test suites under the runtime**: spec 066's. This
  specification removes what blocks two of its groups (Decision 8).
- **The slots code fills at run time** and the 3.15 `PySlot` arrays (Decision 3).
- **A Cython-compiled `lxml.html.diff`** (spec 046, Decision 1).
- **Sending anything upstream**: both fixes are merged there already.

## Acceptance criteria

1. **The checks exist and were seen failing first,** as *The checks* says, each failure recorded
   in the landing notes.
2. **The build.** From an empty `build/` in a clean clone, `scripts/build.sh` applies kiwisolver's
   0001 then 0002, and lxml's 0001, with no offset, and makes a set whose binaries pass every
   check. `MANIFEST` names both new patches by hash (two new `recipe` lines). `LICENSES/` is
   unchanged. Steps 54 to 90 run twice give the same `SHA256SUMS`.
3. **The same bytes everywhere** (spec 012): the arm64 Linux rebuild gives macOS's `SHA256SUMS`,
   and the release's x86_64 rebuild too.
4. **The patches are what their drafts say.** Each `recipes/patches/…` file equals its
   `../upstream/2N-…/fix.patch` byte for byte (SHA-256 `138e3cbe…` and `0291f7c0…`, or the
   builder's restated hash if the review changes one), and each draft moved unchanged.
5. **The scan on the rebuilt set**: `scan_slots` reports no finding, and kiwisolver's four
   `tp_clear` functions are `(i32) -> (i32)` (the builder prints them from the name section);
   coverage at or above the minimums; spec 051's check still green with its coverage unchanged.
6. **The numbers recorded** in the landing notes: both binaries' and the zip's bytes (INFERRED: a
   few bytes each; a growth above 1 KB in a binary is a finding for the build review), checks 1
   and 2's fuel, and any other fuel row the rebuild moves, each named.
7. **The judge.** `uv run pytest -n 6` in the worktree, green but for the growth named here; the
   lane's run on three cores. The lane accepts with `--accept-judge` (the scan and the checks)
   and `--accept-growth` (bytes, and any moved fuel, each with its reason).
8. **The release.** A release dry run on the branch passes every job on all three systems but
   growth lines (AGENTS.md rule 2's "built").

## The judge's changes

- `tests/harness/callbacks.py`: `scan_slots(mod) -> SlotReport` (Decision 3); `findings()` and
  `EXCLUDED` shared; the docstring's out-of-scope list rewritten. `scan()` does not change, so
  spec 051's check keeps its findings, coverage and fuel-free verdict.
- `tests/checks/test_v1_3_data_stack.py`: check 3, `SLOT_MINIMUMS` and `SLOT_NAMED` (the named
  records).
- `tests/checks/test_v1_3_matplotlib.py`: check 1. `tests/checks/test_v1_3_lxml.py`: check 2.
- `tests/unit/test_callbacks.py`: check 4.
- No golden output, gap, allowance or progress file is edited, and no check is weakened. Only if
  spec 066 lands first, its kiwisolver `later` entry and its `lxml-html-diff` class are closed by
  this specification's builder, as a named judge change in the `--accept-judge` reason
  (Decision 8).

## The owner's choices

None blocks the build. Decided until answered:

1. **A backport to lxml 6.1.x.** Not sent. The line is on lxml's `master` for 7.0; a one-line
   pull request to the `lxml-6.1` branch would let a 6.1.4 carry it, if one is cut. The pin
   moves to 7.0.0 when it is final, and the patch goes then.
2. **Nothing to send for kiwisolver.** Upstream merged the fix in #245; the patch goes with the
   next kiwisolver release.

## For the lane

- **Kind:** build-class, not a package; in a wave it is one of the "at most two other build-class
  changes". It shares no file with 066 but `tests/upstream/` if 066 lands first (Decision 8), and
  `CHANGELOG.md`, `README.md`'s patch count and `context/upstream/README.md` with any build-class
  entry that adds a patch (textual merges).
- **The rebuild:** steps 54 (lxml), 55 (kiwisolver, inside matplotlib's step), 60 (link), the
  snapshot, 70 (zip) and 90 change their outputs; 10 to 53 do not.
- **The claim list** (measured, the builder's fast tier on the built set; each line starts "096:"):
  - 096: **new checks (5 nodes), each passing:**
    `test_v1_3_matplotlib.py::test_a_cycle_through_kiwisolver_objects_is_collected[plain]`
    (fuel 228,133,887), `[snapshot]` (48,249,988);
    `test_v1_3_lxml.py::test_lxml_html_diff_imports[plain]` (701,579,788), `[snapshot]`
    (398,909,529); `test_v1_3_data_stack.py::test_type_slots_have_the_types_cpython_calls` (no
    fuel; its reason the coverage line).
  - 096: **unit rows:** `tests/unit/test_callbacks.py` gains twenty (fifteen, then five for the build
    review's L1; the suite 1,802/1,809 in the
    fast tier).
  - 096: **retired checks:** none. **Lost passes:** none. No fuel row grew.
  - 096: **rows that grow, three, all bytes:**
    `test_v1_1_artifact_set.py::test_binary_is_a_core_wasm_module[plain]` 41,169,347 → 41,169,355;
    `[snapshot]` 45,444,036 → 45,444,037;
    `test_v1_1_artifact_set.py::test_stdlib_zip_is_bytecode_only_and_deflated` 38,723,140 →
    38,723,169.
  - **The judge hash changes** in `tests/harness/callbacks.py`, `tests/checks/test_v1_3_data_stack.py`,
    `test_v1_3_matplotlib.py`, `test_v1_3_lxml.py` and `tests/unit/test_callbacks.py`.
- **The flags** (paste-safe, with the measured numbers):

  ```
  --accept "096: kiwisolver's tp_clear returns int (carried patch 0002, upstream's #245), so a garbage cycle holding a kiwisolver object is collected instead of trapping; import lxml.html.diff works (carried patch 0001, upstream's line from #477); the callback scan reads static type objects, PyType_Slot arrays and module definitions"
  --accept-judge "096: the callback scan reads static PyTypeObjects (their tp_* functions and number, sequence, mapping, async and buffer suites), PyType_Spec slot arrays and PyModuleDefs, with minimum coverage (400 types, 380 specs, 120 module definitions, 4,500 functions, 0 unreferenced type candidates, at most 1 type named at run time), every dropped record counted by reason, and named records it must read (kiwisolver's four specs with their tp_clear, a pandas spec, type, numpy.ndarray, ImagingCore, lxml.etree._Element, _regex, ft2font); checks that a cycle through Variable, Term, Expression and Constraint is collected and that lxml.html.diff imports and diffs as natively; unit rows on WAT modules; no existing expectation edited"
  --accept-growth "096: kiwisolver's four tp_clear return int (carried patch 0002): python.wasm +8 bytes (41,169,347 -> 41,169,355) and the snapshot +1 byte (45,444,036 -> 45,444,037); lxml/html/diff.py gains one line (carried patch 0001): the zip +29 bytes (38,723,140 -> 38,723,169); MANIFEST two recipe lines"
  ```

- **Dry-run needs:** the release workflow on the branch (criterion 8); the Windows judge shards
  run checks 1 to 3 as any other.

## Disposition of the pre-build review

The review (`../reviews/096-kiwisolver-clear-and-lxml-final-spec-2026-10-20.md`) re-ran the patch
rules and the drafting scanner, applied both patches with the real applier on fresh tarballs (no
offset), and matched both against upstream's commits (kiwisolver's hunks identical but for the
`index` lines; lxml's the same blob pair). Every finding is written in; no decision changed. The
drafting scanner and its mutants were re-run after the changes (`slotscan-main-4eaf1c3d.txt`,
`slotscan_mutants.out`).

- **F1 (Medium), written in.** Decision 3 defines a C string (1 to 256 bytes in 0x20–0x7E, NUL),
  classifies every static record and counts each drop by reason, makes a referenced type
  candidate with an unreadable `tp_name` a finding, and reads one with `tp_name` 0 as a type named
  at run time. Check 3 holds unreferenced type candidates at 0. Re-run: 481 types, with
  `<dummy key> type` and `symtable entry` now read, and a numpy DType named at run time; no new
  finding. Unit rows and a mutant (`numpy.ndarray`'s `tp_name` at a zero word: total 6).
- **F2 (Medium), written in.** Check 3 names records it must read, one or more per compiled
  package. The mutant that zeroes `kiwisolver.Term`'s `slots` word turns it red by the named
  records alone, with every minimum met (total 5, 453 specs). A unit row holds the rule.
- **L3, written in.** A NULL function slot is readable, skipped and counted, never checked
  (Decision 3); unit rows for the first and a later entry. None today.
- **L4, written in.** The out-of-scope list names C++ dynamic initialization in `.bss` and a spec
  whose first entry is unreadable; the docstring names ids 92 to 110.
- **L5, written in.** Decision 8 follows 066's confirmed text: kiwisolver `later` with
  `closes_with = "spec 096"`, the class `lxml-html-diff`, no allowance added.
- **L6, written in.** The mutants print each total.
- **L7, written in.** The coverage line counts kiwisolver's 6 among the specs, not the functions.
- **The confirmation's Low, written in (option 1).** The reviewer confirmed for build and accepted
  reading a `tp_name`-0 candidate as a type. To bound its interplay with the metatype rule, check
  3 holds the types named at run time at most 1, and a dropped record whose `ob_type` is one is a
  finding, with unit rows; the builder names the choice in the landing notes.
- **N8, N9.** No change asked for the metatype rule (Decision 3 says it over-includes safely).
  Rebased onto `c091f3d`.

## One line

kiwisolver's four `tp_clear` and lxml's `fake_cython` get upstream's own fixes as carried
patches, and the callback scan now reads the type slots that hid the first.

## Landing notes

### What was built (on `spec/096-kiwisolver-clear-and-lxml-final`, base main `c091f3d`)

- **The patches**, byte for byte the drafts' `fix.patch` (criterion 4: SHA-256 `138e3cbe…643e`
  and `0291f7c0…9334`, unchanged by the review), and their drafts moved with `git mv` to
  `context/upstream/patches/kiwisolver-1.5.1/0002-tp-clear-returns-int.md` and
  `…/lxml-6.1.3/0001-fake-cython-final.md`; `context/upstream/README.md`'s rows 28 and 29 say
  carried.
- **The judge:** `tests/harness/callbacks.py` gains `scan_slots`, `SlotReport`, `unread_named`
  and `slot_verdict` (Decision 3 as revised); written fresh from the rules, it gives the drafting
  scanner's numbers exactly on main's set (481 types, 454 specs, 149 module definitions, 5,360
  functions, the same four findings). Checks 1 to 3 and fifteen unit rows.
- **The confirmation's Low: option 1.** Check 3 holds the types named at run time at most 1
  (`SLOT_MAXIMUMS`), and a static record whose `ob_type` is a type named at run time is a
  finding; unit rows `test_slots_names_unreadable_null_and_typed_by_a_nameless_type` and
  `test_slots_check_3s_verdict_bounds_and_named_records`.
- `README.md` (the count 12, the list of twelve, the lxml sentence) and `CHANGELOG.md` under
  `## 0.1.0a8 — unreleased`, as Decision 7 says.

### The build (criteria 2 and 5; EXECUTED, macOS arm64, the native slot)

- `scripts/build.sh` from an empty `build/` (the downloads cloned from the main tree's, every pin
  verified by step 00): 16 steps in 9 m 40 s, exit 0. Steps 54 and 55 applied the patches through
  `patch_tree` with no offset.
- **The set against main's** (wave 05's, `SHA256SUMS` `4eaf1c3d…`): `python.wasm` 41,169,347 →
  41,169,355 (+8, `02baa6cb…`), the snapshot 45,444,036 → 45,444,037 (+1, `627eb450…`), the zip
  38,723,140 → 38,723,169 (+29, `5f1b5918…`). `MANIFEST` differs in exactly two new `recipe`
  lines and the snapshot's `x-snapshot-zip` line; `LICENSES/` is identical.
- **The scan on the new set:** no finding; kiwisolver's four `X_clear` at table indices 16969,
  16979, 17034 and 17048 are now `(i32) -> (i32)`; coverage unchanged (481, 454, 149, 5,360).
  Spec 051's scan: 3,607 method-array entries, 2,313 singles, 1,325 getsets, 451 members, the same
  on both sets.
- Not run: steps 54 to 90 twice on one host. Criterion 2's determinism is answered instead by
  three independent builds (this one on macOS arm64, and the dry run's Linux x86_64 and arm64
  rebuilds) giving the same `SHA256SUMS` (below; the build review's finding 4).

### The checks, seen failing first (criterion 1; EXECUTED)

- On main's set (`WASI_PYTHON_ARTIFACTS` at a private copy, `build_seen_failing_first.out`):
  check 1 traps on both binaries (`trap_cause` `wasm trap: indirect call type mismatch`, stdout
  `Term Expression Constraint`); check 2 exits 1 with `TypeError: 'str' object is not callable` on
  both; check 3 reports exactly the four kiwisolver findings. On the new set all five pass.
- The unit rows' daggers (`build_unit_mutants.py`, `build_unit_mutants.out`): each of thirteen
  rule mutants of `callbacks.py` fails its row, and only that rule's rows.
- The tree check: with the lxml patch file moved aside, `test_source_tree_matches_its_tarball[lxml]`
  fails (`src/lxml/html/diff.py: modified`); with it back, all trees pass.

### The numbers (criterion 6)

- Fuel: check 1 228,133,887 (plain) and 48,249,988 (snapshot); check 2 701,579,788 and
  398,909,529. Check 3 records none.
- The fast tier, `-n 3`, no lock (`build/096/fast.log`): `589/713 pass · 0 gap · 3 blocked · 0
  fail`, unit suite 1,802/1,809; ratchet `lost 0 · gained 5 · grew 3`, its only red the three
  byte rows above. No fuel row grew.
- Criterion 7's local `uv run pytest -n 6` was not run; the fast tier above and the dry run's judge
  shards on three systems (0 fail) stand for it (the build review's finding 3).

### The release dry run (criteria 3 and 8; READ, run 39386471189 on `0054f5b`)

- **24 jobs passed (4 skipped); one red, `judge (macos-15, own-guest)`, and its only red lines are the three
  growth lines** claimed above (`wasi_python v1: 351/713 pass · 2 gap · 2 blocked · 0 fail`;
  ratchet `lost 0 · gained 6 · grew 3`; the sixth gained row is
  `test_wheel_carries_the_artifact_set`, blocked locally for want of a wheel, not 096's). No G7
  line. `gather` and the release-only jobs were skipped, as a red judge makes them.
- Both Linux rebuilds (x86_64 and arm64) and "the same bytes from every host" passed: the set is
  the same on every host (criterion 3). The three `verify` jobs and every Windows shard passed,
  checks 1 to 3 among them.
- So 096 is **built**: every red line in its dry run is a growth line it claims.


### After the build review (2026-10-20)

The review, `../reviews/096-kiwisolver-clear-and-lxml-final-build-2026-10-20.md`, says 096 lands.
Its context-only Lows (3, 4 and 5) are written in above, by the reviewer's commit `5c720ef`.

- **L1, fixed.** Five unit rows, one for each rule the reviewer's mutants C, D, F, G and J left
  uncovered: `test_slots_a_types_pointer_fields_must_be_in_static_memory` (a `tp_methods` below the
  image's base), `test_slots_a_types_sizes_are_bounded` (`tp_basicsize` `1 << 20`),
  `test_slots_a_module_definition_that_does_not_read_as_one_is_a_finding` (an `m_clear` that is no
  table index), `test_slots_an_unknown_module_slot_id_is_a_finding` (id 200 in `m_slots`) and
  `test_slots_a_c_string_is_at_most_256_bytes` (a `tp_name` of 257 printable bytes). Each was seen
  failing under its mutant, and only its own row failed (`build_unit_mutants.py` now runs eighteen
  mutants, `build_unit_mutants.out`, with `PYTHONDONTWRITEBYTECODE=1`). The unit file has 31 rows,
  20 of them the slot scan's. Only unit rows changed, so no check, fuel or byte number moves; the
  judge hash moves in `tests/unit/test_callbacks.py` only, which `--accept-judge` already names.
- **L2, a follow-up, not fixed here.** The `note` fixture (`tests/harness/plugin.py`) keeps the
  first 240 characters of a pass's reason, and check 3's coverage line is about 330, so
  `latest.json` loses its last three counts. Nothing is compared on it, so no verdict changes. The
  follow-up: a shorter summary, or the counts as a `fact`; it changes the judge only.
