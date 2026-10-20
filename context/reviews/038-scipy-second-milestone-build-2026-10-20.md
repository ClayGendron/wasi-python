# Review of 038 — scipy, the second milestone: the sandbox's edges (the build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude Opus 5.5). I wrote none of this specification or its build.
  Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `spec/038-scipy-second-milestone` at `1ef614c` (worktree `wasi_python-038`),
  stacked on 037's built tip `28bd08a`: `git diff 28bd08a..1ef614c` (16 files, +774 −87). I read
  the specification whole (Decisions 1 to 8, the criteria, Revised at build items 1 to 8, both
  phases of the landing notes, For the lane), the pre-build review's findings 2, 14, 15 and 16
  and their dispositions, both patches against the pinned tree, both facts sheets, the whole of
  `recipes/ctypes_stand_in/_types.py`, every changed check, the CHANGELOG and README diffs, and
  the builder's evidence in `build/038/`.
- **Time box:** 45 minutes (build-class), plus waiting for CI.
- **Run:** the builder's release-workflow run `39393706506` on `bcc1ac3` (`1ef614c` adds only
  `context/`), watched to the end and read: 18 jobs passed, 7 failed, 4 publishing jobs
  skipped (`ci-failed.log`, `ci-same.log` beside this file). The arm64 and x86_64 Linux rebuilds gave the same
  `SHA256SUMS` as the macOS build, and that file is `e472e198`: the set's sums printed in the
  same-bytes job are identical line for line to the worktree's `build/artifacts/SHA256SUMS`
  (EXECUTED: `diff`, `shasum`). (The build job's printed "SHA256SUMS: sha256 8c11a86f…" is the
  release assets' sums file, the tarball and the wheel, not the set's.) Growth red lines: macOS
  own-guest 154 GREW (0 fail, 0 lost), own-embedding 33 GREW, upstream-macos 2 GREW. **Five red
  lines are neither GREW nor G7**, in four Linux upstream shards: High 1.
- **Re-ran (EXECUTED, darwin-arm64, in the 038 worktree, against its `build/artifacts`, set
  `SHA256SUMS` `e472e198`; only while `build/lane.lock` was absent; no full judge, no rebuild;
  the builder's `build/progress/latest.json` restored byte for byte afterwards).** Logs beside
  this file.
  - `uv run pytest tests/unit/test_build_scripts.py -k "ctypes_stand_in or carried_patches"`:
    5 passed (`unit.log`).
  - `uv run pytest tests/checks/test_rules.py::test_carried_patches_follow_the_rules
    tests/checks/test_v1_3_scipy.py::test_ndarray_ctypes_gives_the_arrays_address
    tests/checks/test_v1_3_scipy.py::test_ctypes_values_scipy_makes`: 5 passed, exit 0
    (`nodes.log`).
  - `uv run pytest tests/checks/test_v1_3_data_stack.py::test_goldens_reproduce_under_the_pinned_oracle`:
    1 passed, exit 0 (`oracle.log`). This reproduces `scipy_edges.expected` natively under the
    pinned oracle with two hash seeds; the builder's own log of that step prints the comparison's
    `None` ("no difference") as "seeds agree: None".
  - Host CPython 3.14.2's `ctypes` against the stand-in under wasm32's sizes, the same 27
    probes (`probe_cpython.py`, `probe_standin.py`).
  - A guest probe through `wasi-python run` with nothing writable (`gp/guest_probe.py`,
    `guest_probe.out`).

## Acceptance criteria against evidence

1. **Checks exist, seen failing first on 037's set; the three gap checks pass with their entries
   removed** — met. READ `build/038/logs/seen-failing-on-037-set.log`: 12 failed, each with the
   gap's exception or digest (`4ea6e755e09e`, `accb7992f785`'s all-zero points, `b1dc10df2320`),
   the address check `OSError`, the edges golden at line 2 (`RuntimeError thread constructor
   failed`), 033's guest check at `ndarray.ctypes.data`, `c_int(1)`, `c_ulong(-1)`. READ
   `standin-seen-failing.log`: the two new value unit checks failed with the stand-in's
   `OSError`. EXECUTED: the gap and address checks pass here. The six `[[gap]]` entries are gone
   (READ).
2. **The two patches apply with no offset in a build from pins** — met. READ `build-from-empty.log`
   (step 57, `0001` to `0004`, no offset); and EXECUTED in the run: both Linux rebuilds from empty passed.
3. **Same `SHA256SUMS` on every host the gate covers** — met (EXECUTED, run `39393706506`): `ubuntu-24.04-arm: the same SHA256SUMS`, `ubuntu-24.04: the same SHA256SUMS`, and the same wheel; the set is `e472e198`.
4. **`uv run pytest` green with `--accept-judge` (and growth accepted)** — met as far as a
   builder can show it: the fast tier is red only by growth (READ `fast-tier-2.log`: 0 fail, 162
   metrics grew, nearly all 037's and 043's); scipy's slow file passes (READ `slow-scipy.log`).
   The builder's local full judge (`-n 6`) was not run; see Low 6.
5. **A release dry run passes every job** — not met: seven jobs failed. Five of their red lines are not growth (High 1).

Pre-build findings: **2** (the gap checks live in 037, 038 removes the entries) holds (READ).
**14** holds: the value rules are in `_types.py`; `import ctypes` does not import `_types`
(asserted in `_load_stand_in_as_wasm32`, EXECUTED). **15** holds: the address check is a guest
check; the host checks use no numpy and include the 32-bit wrap (EXECUTED). **16** holds: the
safety sentence, the fast_matrix_market note and the `mmwrite` hash are written in, and the hash
matches native (READ in `.expected` and `oracle.log`; EXECUTED by the oracle node).

## The patches (READ against the pinned tree in `build/scipy-1.18.1`)

- **0003, Matrix Market serial.** One import, one changed constant, two docstring lines. The
  C++ paths do test only `num_threads != 1` (`read_body.hpp:477`, `write_body.hpp:68`), and the
  pool does start `hardware_concurrency()` threads at 0 (`task_thread_pool.hpp:137-142`), so the
  cause and the fix are as stated. threadpoolctl's controller still reads and sets the same
  global (lines 66-71). Minimal and correct.
- **0004, Sobol without a temporary file.** `import io` and one line: `np.load(io.BytesIO(
  _npzfile.read_bytes()))`. `files()` is still used, so `importlib.resources` stays imported.
  Works from a folder and a zip. Minimal and correct; it changes `python.wasm` (Cython), as
  Decision 2 says.
- **The drafts are facts sheets.** Both open with "This is a facts sheet, not a pull request".
  The three quotations from scipy's AI policy are verbatim (EXECUTED: fetched the policy page
  2026-10-20). Each records "Nothing has been posted" and that the owner writes the text himself
  with the disclosure. The line numbers cited are the pristine file's (READ).

## The ctypes stand-in

Faithful where it claims to be (EXECUTED, the same probes against host CPython 3.14.2): integer
wraps to width and signedness; `TypeError` for a float, a `str`, `None`, a `Fraction` or a
`Decimal` given to an integer type; `__index__` objects accepted by integer types; `c_float`
overflow to infinity; `OverflowError` for a huge `int` to a float type; `c_void_p(0)` and a value
wrapping to 0 read `None`; `c_void_p(True)` is 1; `c_bool` takes truth; instances take
attributes; `==` is identity; `repr` is CPython's form. The 32-bit wrap of `c_void_p(-1)` is
wasm32's, as intended.

The after-build change (item 8) is sound. `_index` reproduces `operator.index`: it looks up
`__index__` on the type (as CPython does), raises `TypeError` when it is missing or returns a
non-int, and returns an exact `int`. `float("inf")` replaces `math.copysign`. The unit check that
holds `_types.py`'s imports to `struct` and `sys` is a real guard (AST walk, level-0 imports).

Where it now differs, each a silent success or a silent wrong answer, none reached by the
packages shipped (READ: the only constructors in scipy, numpy, pandas, matplotlib and networkx
are loadarff's `c_ulong(-1).value`, numpy's `_ctypes` and `BitGenerator.ctypes`):

- **Truth value** (Medium 2 below): CPython's simple instances are false when their bytes are
  zero; the stand-in's are always true.
- **Wider acceptance** (Low 3 below): `c_void_p` takes any `__index__` object (`np.intp(16)` →
  16; CPython: `TypeError: cannot be converted to pointer`); float types take buffer objects
  (`c_double(memoryview(b"2.5"))` → 2.5, `c_double(array('b', b'1'))` → 1.0; CPython: `TypeError:
  must be real number`); instances are hashable (CPython: unhashable).
- **Narrower** (fails safe, no finding): `cast(True, c_void_p)` and `cast` to a `c_void_p`
  subclass raise `OSError` (CPython succeeds); `c_int(value=5)` raises `TypeError` (CPython
  silently gives 0).

Nothing that would need an address or a call now succeeds: `byref`, `pointer`, `addressof`,
`from_*`, typed pointers, `c_char_p`, `c_wchar_p`, arrays, structures, function-type instances
and the byte-order twins still raise `OSError` (EXECUTED, unit checks; the twins because
`_simple` makes them as direct subclasses of `_SimpleCData`, whose `_store_` is `None`, READ).
One consequence not written anywhere: numpy's `BitGenerator.ctypes` now returns its named tuple
(a `c_void_p` state and three uncallable function pointers) where it raised; calling one raises
`OSError` (EXECUTED in the guest). That is Decision 3's rule working; Note 8.

## AGENTS.md rule 4: 033's checks

An honest restatement, not a narrowing (READ). Decision 5 named the change before the build and
it is flagged under `--accept-judge`. In the unit check `test_the_ctypes_stand_in_names_and_refuses`
the instance refusal is skipped only for Decision 3's 25 names; every other kind still refuses,
and all five `from_*` methods are still checked for every kind, holders included. The two
dropped guest refusals (`ndarray.ctypes`, `c_int(1)`) become value assertions, and five refusals
are added (`data_as(POINTER(c_double))`, `ndarray.ctypes.shape`, `c_char_p(b"x")`,
`byref(c_int(1))`, `addressof(c_void_p(8))`). No golden, allowance or other gap moved; the six
entries had to go with their checks passing (spec 002, Decision 4).

## Findings, most severe first

1. **The dry run is red beyond growth** (run `39393706506`; `recipes/ctypes_stand_in/_types.py:81-108`,
   `tests/known_gaps.toml`) — High: the lane cannot accept it, and an accepted pass is lost.
   - `tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-b]` is LOST:
     `test.test_memoryview.OtherTest.test_ctypes_cast` (CPython's own test) does
     `bytes(ctypes.c_double(0.6))`; before 038 the constructor raised `OSError` and the test sat
     in the `no-ctypes` class; now the instance exists, has no buffer, and `bytes()` raises
     `TypeError: cannot convert 'c_double' object to bytes` (digest `553fd33fb0dc`). That also
     breaks 033's rule that touching memory raises `OSError`.
   - `test_upstream_class[cpython-a-no-ctypes]`, `[cpython-b-no-ctypes]`, `[cpython-c-no-ctypes]`
     and `[numpy-others-no-ctypes]` each report "passes, but tests/known_gaps.toml still lists
     it: remove the gap": no test in those groups fails with "ctypes is unavailable" now. numpy's
     eight (three `numpy.ma` tests and five bit generators' `test_ctypes`) now pass.
   - None of this was seen locally: the upstream suites are slow and the builder's full judge was
     not run (Low 6). The claim list's "No group's passes fall" is wrong as built.
   **Fix (the builder's).** Give `_SimpleCData` a `__buffer__(self, flags)` that raises
   `OSError(_MSG)` (PEP 688; EXECUTED on host 3.14: `bytes()`, `memoryview()` and `bytearray()` of
   such an object then raise that `OSError`), with a unit row seen failing first. The memoryview
   test then errors with "ctypes is unavailable" again, `cpython-b`'s class keeps its one member
   and its gap matches as before (INFERRED; the run decides). Remove the `[[gap]]` entries for
   `cpython-a-no-ctypes`, `cpython-c-no-ctypes` and `numpy-others-no-ctypes` (and their empty
   `[[expected]]` classes and lists if the judge's rules want them gone), name them in
   `--accept-judge`, and claim the upstream groups' gained passes. Then dispatch the release
   workflow again and record that every red line is GREW or G7.
2. **A stand-in instance is always true** (`recipes/ctypes_stand_in/_types.py:81-108`) — Medium.
   `_SimpleCData` defines no `__bool__`; CPython's simple instances are false when their stored
   bytes are all zero. Failure (EXECUTED in the guest): `bool(ctypes.c_int(0))` and
   `bool(ctypes.c_void_p())` are `True` (CPython 3.14: `False`), so `if ctypes.c_bool(False):`
   takes the branch and `if not ptr:` misses a NULL. Item 3 says an instance behaves "as CPython's
   `ctypes` does"; this is the one place a held value gives a wrong answer silently. No shipped
   package relies on it (READ), which is why it is Medium and not High.
   **Closes with either:** (a) the builder adds `def __bool__(self): ...` returning whether the
   stored C bytes are non-zero (for the integer types and `c_bool`, `bool(self._value_)`; for
   `c_void_p`, `self._value_ is not None`; for the floating types, non-zero bits, so `-0.0` is
   true as in CPython), with a unit row seen failing first, and the zip's rebuilt bytes in the
   dry run; or (b) a written answer in Revised at build naming the divergence, a README sentence
   beside the stand-in's paragraph, and a roadmap line for the follow-up.
3. **The stand-in accepts more than CPython** (`_types.py:221-242`) — Low, a code follow-up
   (the builder's). `_address` should require `isinstance(value, int)` (CPython's `PyLong_Check`),
   `_double` should take only objects with `__float__` or `__index__` (CPython's
   `PyFloat_AsDouble`) rather than `float()`, which parses buffers, and `_SimpleCData` should set
   `__hash__ = None`. Each is a silent success where CPython raises; none is reached by the
   shipped packages. May ride with Medium 2's fix or go to the roadmap line.
4. **A changed row is not in the claim list** — Low, written in. `tests/checks/test_v1_3_data_stack.py::test_goldens_reproduce_under_the_pinned_oracle`
   now also reproduces `scipy_edges` (on darwin-arm64 only, through `PLATFORM_BOUND`); EXECUTED
   here, it passes. The `--accept-judge` reason names `JOBS and PLATFORM_BOUND`, so the flag
   covers it; the claim list should name the row.
5. **The growth reason overstates its bound** — Low, written in. It says every other fuel row is
   within ±0.15% of 037's. READ `build/038/growth-vs-037-2.txt`:
   `tests/checks/test_v1_4_embedding.py::test_unbuffered_output_survives_a_hard_exit[snapshot]`
   grows +0.39% (1,265,275 → 1,270,242, +4,967 fuel; cause not identified), and
   `test_v1_2_hostile_guest.py::test_recursion_through_python_raises[re-sub-snapshot]` moves
   −0.154%. The reason should name the first.
6. **The builder's local full judge was not run** — Low. AGENTS.md rule 3a asks for
   `uv run pytest -n 6` before "built". The fast tier, scipy's slow file and the dry run stand
   for it here; the landing notes should say so in one line.
7. **The README's Sobol options had no check** — Low, now evidenced. The README says
   `differential_evolution(init='sobol')` and `shgo(sampling_method='sobol')` work with nothing
   writable. EXECUTED in the guest: both return 0.0 on a two-dimensional sphere; before 038 shgo
   raised QH6421. No change needed.
8. **Note.** numpy's `BitGenerator.ctypes` now gives its named tuple; its function pointers
   raise `OSError` when called. Worth a clause in the README's stand-in paragraph when it is next
   touched.
9. **Note.** The builder's self-check list was not in my brief; its items are evidenced above
   except Low 6.

## Constitution checks

- **§4.1:** two patches, each a recorded file under `recipes/patches/scipy-1.18.1/`, named in the
  CHANGELOG, with a facts sheet under `context/upstream/patches/`; spec 020's rules pass
  (EXECUTED). Both are the smallest change that fixes the cause.
- **§4.4, §4.15:** no new channel to the host. A `c_void_p` is an integer; numpy already exposes
  addresses through `__array_interface__`. The edges golden and the gap checks run with nothing
  writable.
- **§4.12:** a patch to a scipy file carries scipy's licence; no new notice.
- **§4.13:** no new development dependency; the host checks use no numpy.
- **Tests count operations:** yes; fuel and bytes only.
- **§7:** nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

Written in by the reviewer on the branch as `8dc0182` (`context/` only): the run's result in the
phase-2 note, Low 4's row in the claim list, Low 5's bound in "Rows that grow". High 1, Medium 2,
Low 3 and Low 6 are the builder's.

## Verdict

Lands once High 1 is fixed (an instance's buffer refuses with `OSError`, the three
`*-no-ctypes` gaps whose classes are now empty are removed under `--accept-judge` with the
upstream passes claimed, and a new dry run shows only GREW or G7 red lines) and Medium 2 is fixed
or answered in writing.

## One line

The patches, the facts sheets, the value rules and the checks are sound and the set
rebuilds to the same `e472e198` everywhere, but the dry run is red beyond growth: a `c_double` is
now made yet has no buffer, so CPython's `test_memoryview` loses a pass and four no-ctypes gaps
must go; fix that, answer the truth-value Medium, and it lands.
