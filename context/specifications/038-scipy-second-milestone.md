# 038 — scipy, the second milestone: the sandbox's edges

- **Status:** **Spec 051's callback scan binds this build** (051, Decision 4a; written in when 051 landed): `test_callbacks_have_the_types_cpython_calls` is green, and a mismatch it finds is fixed by a carried patch or an upstream release, never by an exclusion. confirmed for build. Drafted 2026-10-17; revised the same day against the
  pre-build review of 037 and 038 (`../reviews/037-scipy-spec-2026-10-17.md`): its findings 2,
  14 and 15 fixed, 16 noted (the review's Disposition), and confirmed there with no condition on
  038. It changes the artifact set (two
  carried patches to scipy, a wider `ctypes` stand-in), so it was reviewed before it is built
  (constitution §5.6). It is build-class: it touches `recipes/` (§5.7). It builds after spec 037
  lands.
  **Amended 2026-10-19 by spec 037's build** (037, Revised at build, items 9 and 10): 037 carries
  `recipes/patches/scipy-1.18.1/0001-uarray-callback-signatures.patch`, so this specification's two
  scipy patches are numbered `0002-…` and `0003-…`; and the `ctypes` stand-in already gives a
  function type's instance from `cast(int, F)` (uncallable) and names `ctypes._CFuncPtr`, which
  Decision 3 keeps ("any other cast raises" reads: any other cast but those).
- **Owner:** Clay Gendron
- **Kind:** two carried patches to scipy with their pull request drafts, the `ctypes` stand-in
  (spec 033's `recipes/ctypes_stand_in/_types.py`), judge additions and changes (a golden job, a
  v1.3 check, `tests/known_gaps.toml`, 033's stand-in checks), `README.md`, `CHANGELOG.md`.
- **Depends on:** 037 (scipy in the build, the three gap checks and their `[[gap]]` entries this
  specification closes, the pinned oracle and its printing rules), 033 (the `ctypes` stand-in it
  widens), 020 (carried patches).
- **Research it stands on:** `../research/2026-10-17-what-scipy-needs.md` finding 8 (on WASI,
  `std::thread::hardware_concurrency()` is 1 and constructing a `std::thread` throws
  `std::system_error`, EXECUTED by `probes/thread2.cpp`); the scipy 1.18.1 sdist, read while
  drafting (SHA-256 `52c4b742…2747307`, equal to PyPI's, EXECUTED), at the lines cited below;
  spec 033's stand-in design (Decision 5 there, and its confirmation's condition 1: the types
  live in `ctypes/_types.py`, imported on first lookup); Pyodide's scipy test configuration,
  which skips the same matrix-market paths for the same reason
  (`context/prior_art/pyodide-recipes`, `packages/scipy/scipy-conftest.py:73`, READ).

## The problem

Spec 037 builds all of scipy but `scipy.odr`. Three things still fail, each because the sandbox
lacks something scipy assumes, not because scipy is miscompiled. 037 has a check for each, which
fails today in exactly the way its `[[gap]]` entry records, and names this specification as the
closer:

- **`scipy.io.mmread` and `mmwrite` raise `RuntimeError`.** Their default parallelism is
  `PARALLELISM = 0` ("number of CPUs"; `io/_fast_matrix_market/__init__.py:24`). Any value but 1
  takes fast_matrix_market's threaded path (`read_body.hpp:477`, `write_body.hpp:68`), whose pool
  starts at least one worker (`task_thread_pool.hpp:137-142`). Starting it throws on WASI.
- **`stats.qmc.Sobol` with nothing writable raises `OSError`.** `_sobol.pyx` loads its direction
  numbers with `importlib.resources.as_file(…)` (lines 147-150), which copies a resource inside a
  zip to a temporary file first. A call with no grants has no temporary folder (§4.15). The same
  path serves `qmc_quad` and `sobol_indices`.
- **Four functions raise `OSError` from the `ctypes` stand-in.** `stats.geninvgauss`'s and
  `stats.genhyperbolic`'s `cdf`, and `stats.studentized_range` (and through it `tukey_hsd`), pass
  their parameters to C as `np.array(…).ctypes.data_as(ctypes.c_void_p)`
  (`_continuous_distns.py:4144, 5249, 12402-12456`). `io.arff.loadarff` computes
  `ctypes.c_ulong(-1).value` (`_arffread.py:485`). Spec 033's stand-in raises `OSError` for any
  instance of a C type.

## Decisions

1. **Matrix Market files are read and written serially where threads cannot start.** A carried
   patch, `recipes/patches/scipy-1.18.1/0001-io-matrix-market-serial-without-threads.patch`:
   `scipy/io/_fast_matrix_market/__init__.py` imports `sys` and sets
   `PARALLELISM = 1 if sys.platform in ("emscripten", "wasi") else 0`, with its docstring saying
   why. Nothing else changes: a program may still set `PARALLELISM`, and scipy's threadpoolctl
   controller reports and sets the same variable.
   - **Why a patch and not a recipe.** The default is a constant in scipy's own Python. The C++
     has no switch: both paths test only `num_threads != 1`. A recipe would have to replace
     scipy's file in the zip with our copy, which is a source change without a record (§7).
   - **Its draft**, `context/upstream/patches/scipy-1.18.1/0001-io-matrix-market-serial-without-threads.md`,
     `Status: drafted`. The case for upstream: Emscripten has the same limit, and Pyodide skips
     these tests for it; the change turns those skips into passes. The draft also notes, for the
     maintainers, the deeper fix in fast_matrix_market itself (which scipy vendors): a requested
     count of 0 that resolves to `hardware_concurrency() == 1` could run serially, which would
     help any one-core host. The carried Python patch stays the right fix for this project.
     Before the owner sends it, the draft states scipy's policy on AI-written contributions as
     read then; where it forbids such text, the body is the facts for the owner to write from.

2. **The Sobol direction numbers are read without a temporary file.** A carried patch,
   `0002-stats-sobol-without-a-temporary-file.patch`: in `scipy/stats/_sobol.pyx`,
   `with importlib.resources.as_file(_npzfile) as f: dns = np.load(f)` becomes
   `dns = np.load(io.BytesIO(_npzfile.read_bytes()))`, with `import io`.
   - It works on every install: from a folder and from a zip. The file is 589,334 bytes
     (EXECUTED: `wc -c`), the same bytes `as_file` would have copied, now read once into memory
     and never written. `np.load` reads an `.npz` from a file object.
   - With spec 035, `read_bytes` on a zip member answers from zipimport's directory, without a
     second parse.
   - The file is Cython, so the patch changes `python.wasm`, not only the zip.
   - **Its draft**, `Status: drafted`: `as_file` exists to give a filesystem path to code that
     needs one; `np.load` does not, so the copy is avoidable, and a zipped or read-only install
     then needs no writable temporary folder.

3. **The `ctypes` stand-in holds values.** Spec 033's rule was: declaring a type works; anything
   that would load a library, touch memory or make an instance raises `OSError`. This
   specification narrows "make an instance" for two kinds of type, and changes nothing else. The
   change is in **`recipes/ctypes_stand_in/_types.py`**, where 033 keeps every type; `ctypes`'s
   `__init__.py` keeps only the names and `__all__` (033's confirmation, condition 1).
   - **Numeric simple types** (`c_bool`, `c_byte`, `c_ubyte`, `c_short`, `c_ushort`, `c_int`,
     `c_uint`, `c_long`, `c_ulong`, `c_longlong`, `c_ulonglong`, the fixed-width aliases,
     `c_size_t`, `c_ssize_t`, `c_float`, `c_double`, `c_longdouble`) may be instantiated, with a
     value or none (zero). `.value` reads and writes it as wasm32 C would store it: an integer
     wraps to the type's width and signedness (`c_ulong(-1).value == 4294967295`, as a real
     wasm32 `ctypes` gives), `c_float` rounds through `struct.pack("f")`, `c_bool` stores a
     `bool`.
   - **`c_void_p`** may be instantiated with an `int` or `None`; its `.value` is that integer,
     wrapped to 32 bits, or `None`.
   - **`cast(obj, c_void_p)`**, where `obj` is an `int`, `None` or a `c_void_p` instance,
     returns a new `c_void_p` with the same value. Any other `cast` raises `OSError`, as today.
   - **Nothing has an address.** `byref`, `pointer`, `addressof`, `from_buffer`,
     `from_buffer_copy`, `from_address`, `from_param` and `in_dll` still raise `OSError`. So do
     instances of `c_char_p`, `c_wchar_p`, structures, unions, arrays, pointers and function
     types, and every library load. Instances take ordinary attributes, because numpy's
     `ndarray.ctypes.data_as` sets one (`ptr._arr = …`, numpy `_core/_internal.py:294-296`,
     READ).
   - **What it enables.** numpy's `ndarray.ctypes` (`data`, `data_as(c_void_p)`,
     `_as_parameter_`) and scipy's `LowLevelCallable` with a `c_void_p` user-data pointer
     (`_lib/_ccallback.py:171`), which keeps `user_data` alive while it is used. `data_as(POINTER(c_double))` still raises: it is a cast to a
     pointer type.
   - **Why it is safe.** A `c_void_p` here is an integer. scipy uses it to give its own C code
     the address of a numpy buffer, in the guest's own memory, which wasm bounds-checks. numpy
     already lets guest code view any linear-memory address through `__array_interface__`, so an
     integer in a `c_void_p` gives no new reach (INFERRED, the review's note). No channel to the
     host opens (§4.4, §4.15). A wrong integer can at worst make the guest's own code read its
     own memory wrongly or trap, as any C extension already can.
   - **The `-V` banner** still says "no ctypes": no foreign call can be made (question 58's
     answer stands).

4. **The known gaps close.** The three `[[gap]]` entries 037 added to `tests/known_gaps.toml` are
   removed, and 037's three checks (`test_matrix_market_round_trips_in_memory`,
   `test_sobol_needs_nothing_writable`, `test_ctypes_values_scipy_makes`) then pass on both
   binaries with nothing writable. A gap whose check passes while its entry remains turns the run
   red (spec 002, Decision 4), so the two changes land together.

5. **The checks**, each seen failing first on 037's set.
   - **037's three gap checks** (above): they fail on 037's set exactly as their entries record;
     here they pass.
   - **A golden job, `tests/jobs/scipy_edges.py`**, on 037's pinned oracle, recording platform
     and printing rules (significant digits; `k = 9` for direct results, `k = 6` with
     `epsabs ≤ 1e-12` for those computed by quadrature): a sparse matrix and a dense one written
     with `mmwrite` to an `io.BytesIO`, the bytes' SHA-256, and read back with `mmread` (equal,
     and their values); `qmc.Sobol(d=3, scramble=False).random(8)` and a seeded scrambled draw;
     `geninvgauss(2.3, 1.5).cdf(1.0)`; `genhyperbolic(0.5, 1.5, -0.5).cdf(0.3)`;
     `studentized_range.cdf(3.0, 3, 10)`; the p-values of `tukey_hsd` on three fixed groups;
     `loadarff` of a small ARFF text from an `io.StringIO`. It fails first on 037's set with the
     gaps' exceptions. The `mmwrite` hash should match although the oracle writes with threads
     and the guest serially: fast_matrix_market writes its chunks in order (READ by the review).
     If it does not, the job prints the read-back values only, and the landing notes say why.
   - **The address check, in the guest (v1.3,** in `tests/checks/test_v1_3_scipy.py`, both
     binaries): `numpy.ndarray.ctypes.data_as(ctypes.c_void_p).value` equals the array's
     `__array_interface__["data"][0]`. It runs in the guest, where addresses fit in 32 bits and
     numpy is the real one. On a 64-bit host a heap address exceeds 2³² (EXECUTED by the review:
     `0x10318ccf0`), and numpy is not a development dependency of this repository (§4.13), so it
     is not a host check.
   - **The stand-in, on the host** (unit checks beside 033's, the stand-in alone, no numpy): the
     value rules of Decision 3 for each listed type, including the wrap of `c_ulong(-1)`,
     `c_byte(200)` and `c_float(0.1)`; `c_void_p` of a value above 2³² wraps to 32 bits; `cast` of
     an `int`, `None` and a `c_void_p`; every operation Decision 3 keeps refusing still raises
     `OSError`; `import ctypes` alone still does not import `_types`. 033's checks that assert an
     instance of a numeric type or `c_void_p` raises are changed to Decision 3's rule: a judge
     change, with this reason, under `--accept-judge`.
   - **Rules:** spec 020's `patch_errors` passes on the two patches and drafts; `SOURCE_PATTERNS`
     already has scipy (037), so the patched-tree check now applies the patches.

6. **What it costs.** The zip changes two members' bytes (`_fast_matrix_market/__init__` and
   `ctypes/_types`) and gains none. `python.wasm` changes in `_sobol` only. A plain start pays
   nothing new, since no member is added. `import ctypes` does not grow: it does not import
   `_types`. The first type lookup grows by the few new methods; that is what the landing notes
   measure and name (033 measured the eager form's cost at +2.9 M to +7.2 M fuel, which is why
   the types are lazy). The three gap checks become passes; their fuel is recorded by the
   scoreboard.

7. **Ordering.** Right after 037, as the next build-class specification (§5.7). It changes no
   file of 037's but `tests/known_gaps.toml`, `tests/checks/test_v1_3_scipy.py` and `JOBS`,
   which 037 created or extended. If spec 039 (tier A) built between them, this one rebases onto
   it; neither touches the other's files beyond `JOBS`.

8. **Licences.** A patch to scipy's file carries scipy's licence (spec 020, Decision 10). No new
   notice.

## Intent

The scipy functions that assumed threads, a writable temporary folder or a real `ctypes` work
inside the sealed Python as they do natively, with nothing writable and no thread.

## Design

| file | change |
|---|---|
| `recipes/patches/scipy-1.18.1/0001-io-matrix-market-serial-without-threads.patch`, `0002-stats-sobol-without-a-temporary-file.patch` | new (Decisions 1, 2) |
| `context/upstream/patches/scipy-1.18.1/0001-…md`, `0002-…md` | their drafts |
| `recipes/ctypes_stand_in/_types.py` | Decision 3 |
| `tests/jobs/scipy_edges.py`, `.expected`; `JOBS` in `tests/harness/jobs.py` | the golden (Decision 5) |
| `tests/checks/test_v1_3_scipy.py` | the guest address check |
| `tests/unit/…` (033's stand-in checks) | Decision 3's rules; the changed assertions |
| `tests/known_gaps.toml` | three entries removed (Decision 4) |
| `README.md`, `CHANGELOG.md` | the gaps closed; what the stand-in now does; the patches by path |

## Scope

In: Decisions 1 to 8. Out:

- **ctypes function pointers and `LowLevelCallable.from_ctypes`.** They need libffi; 037
  documents them as absent.
- **Pointers to typed data** (`POINTER(c_double)` instances, `data_as` to a pointer type),
  character pointers and structure instances: they would need memory the stand-in does not own.
- **Threads.** Nothing here makes one start; 037's `workers` facts stand.

## Acceptance criteria

1. The checks exist and were seen failing first on 037's set, each with the gap's exception;
   037's three gap checks pass here with their entries removed.
2. A full build from pins applies the two scipy patches with no offset; the set runs the golden
   and the checks on both binaries.
3. The same-bytes rebuild gives the same `SHA256SUMS` on every host the gate covers when this
   lands (arm64 Linux; x86_64 Linux too once spec 040 has landed), with no exception (spec 012).
4. `uv run pytest` is green with `--accept-judge` (the stand-in checks, the removed gaps) and,
   if growth occurs, `--accept-growth` with its reason.
5. A release dry run passes every job.

## The owner's choices

None open here.

## Landing notes

Not built.
