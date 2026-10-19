"""What `python.wasm` runs before Python starts, and what it asks of a host (spec 023, Decision 8).

A reactor's `_initialize` calls `__wasm_call_ctors`, which runs every static constructor linked
in, before `Py_Initialize`. A constructor that touches Python there waits for a GIL that never
comes: matplotlib 3.11.2's `ft2font` enums did (`_GLOBAL__sub_I_ft2font_wrapper.cpp`, fixed by
carried patch 0001). So the list of constructors is compared, by name, with a list a review has
read; a new one fails until a review adds it. Read statically, it never hangs, unlike a run.

`target_features` names the wasm features the objects were compiled with, which every host must
support. The list is fixed whole, so a build that adds `+atomics` (from `-pthread`), `+simd128`
or `+tail-call` fails here before it reaches a host.

Step 60 runs this module on the binary it links, so a build with a new constructor stops before
step 80, whose Wizer run would hang on it:

    python -m harness.constructors build/out/python.wasm      (with tests/ on PYTHONPATH)
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from harness import wasm

# Each constructor a review has read, in link order (the order `__wasm_call_ctors` calls them),
# and what it does. None calls Python. The list is compared whole, order and count included: two
# of the names are generic (clang names every C++ file's first guarded static's initializer
# `__cxx_global_var_init`, and every `init_priority(100)` group `_GLOBAL__I_000100`), so one more
# constructor with a reviewed name is still a new constructor (spec 023's build review, F2).
REVIEWED_CONSTRUCTORS = (
    "init",  # wasi-libc: the preopened directories
    "__wasilibc_initialize_environ_eagerly",  # wasi-libc: environ
    "_GLOBAL__I_000100",  # libc++'s iostream.cpp: std::ios_base::Init, the standard streams
    "_mi_process_init",  # CPython's mimalloc
    "register_builtin_extensions",  # scripts/gen_inittab.py: PyImport_AppendInittab only
    # kiwisolver.cpp: kiwi::strength's four doubles and a std::recursive_mutex, its destructor
    # registered with __cxa_atexit
    "_GLOBAL__sub_I_kiwisolver.cpp",
    # matplotlib's _image_wrapper.cpp: Agg's sRGB_conv_base<int16u>::lut and <float>::lut, two
    # guarded template statics filled with pow(); spec 023's build read their disassembly
    "__cxx_global_var_init",
    "__cxx_global_var_init.5",
    # scipy (spec 037, Decision 8): each one's call graph was walked in the linked binary (every
    # function it reaches by a direct call; the build's landing notes): libc++'s strings, maps
    # and hash tables built and their destructors registered with __cxa_atexit, operator new and
    # its failure path (bad_alloc, terminate, abort, a message to stderr), getenv; no function of
    # CPython's (no name starting Py or _Py), and the only indirect calls are libc++'s new and
    # terminate handlers and stdio's write. uarray's dispatch statics; fast_matrix_market's
    # enum-to-name maps, one copy per C++ file; HiGHS's pybind11 bindings' and options' strings;
    # xsf's statics in special._gufuncs and special._special_ufuncs (six each, clang's generic
    # names); stats._qmc_cy's.
    "_GLOBAL__sub_I__uarray_dispatch.cxx",
    "_GLOBAL__sub_I__fmm_core.cpp",
    "_GLOBAL__sub_I__fmm_core_read_array.cpp",
    "_GLOBAL__sub_I__fmm_core_read_coo.cpp",
    "_GLOBAL__sub_I__fmm_core_write_array.cpp",
    "_GLOBAL__sub_I__fmm_core_write_coo_32.cpp",
    "_GLOBAL__sub_I__fmm_core_write_coo_64.cpp",
    "_GLOBAL__sub_I_highs_bindings.cpp",
    "_GLOBAL__sub_I_highs_options.cpp",
    "__cxx_global_var_init.7",
    "__cxx_global_var_init.8",
    "__cxx_global_var_init.9",
    "__cxx_global_var_init.10",
    "__cxx_global_var_init.11",
    "__cxx_global_var_init.12",
    "__cxx_global_var_init.7",
    "__cxx_global_var_init.8",
    "__cxx_global_var_init.9",
    "__cxx_global_var_init.10",
    "__cxx_global_var_init.11",
    "__cxx_global_var_init.12",
    "_GLOBAL__sub_I__qmc_cy.cpp",
    "_GLOBAL__sub_I_unique.cpp",  # numpy's unique.cpp: its hash tables' statics
    # OpenBLAS's gotoblas_init (driver/others/memory.c, constructor(101)): it reads the OPENBLAS_*
    # environment variables (getenv, atoi) and sets its buffer's parameters; nothing of Python. On
    # the snapshot it ran at build time, so those variables do nothing there (README).
    "gotoblas_init",
    # wasm-ld's own: registers the module's destructors (OpenBLAS's gotoblas_quit) with atexit.
    ".Lregister_call_dtors",
    # HiGHS (optimize._highspy), file by file: its std::string constants (kHighsOffString and the
    # rest, defined in headers every file includes) and its LP reader's keyword tables.
    "_GLOBAL__sub_I_HighsIO.cpp",
    "_GLOBAL__sub_I_LoadOptions.cpp",
    "_GLOBAL__sub_I_HMpsFF.cpp",
    "_GLOBAL__sub_I_HMPSIO.cpp",
    "_GLOBAL__sub_I_FilereaderMps.cpp",
    "_GLOBAL__sub_I_reader.cpp",
    "_GLOBAL__sub_I_FilereaderLp.cpp",
    "_GLOBAL__sub_I_FilereaderEms.cpp",
    "_GLOBAL__sub_I_Filereader.cpp",
    "_GLOBAL__sub_I_Highs.cpp",
    "_GLOBAL__sub_I_HighsCallback.cpp",
    "_GLOBAL__sub_I_HighsIis.cpp",
    "_GLOBAL__sub_I_HighsInfo.cpp",
    "_GLOBAL__sub_I_HighsInfoDebug.cpp",
    "_GLOBAL__sub_I_HighsInterface.cpp",
    "_GLOBAL__sub_I_HighsLp.cpp",
    "_GLOBAL__sub_I_HighsLpUtils.cpp",
    "_GLOBAL__sub_I_HighsModelUtils.cpp",
    "_GLOBAL__sub_I_HighsOptions.cpp",
    "_GLOBAL__sub_I_HighsRanging.cpp",
    "_GLOBAL__sub_I_HighsSolution.cpp",
    "_GLOBAL__sub_I_HighsDebug.cpp",
    "_GLOBAL__sub_I_HighsSolutionDebug.cpp",
    "_GLOBAL__sub_I_IpxWrapper.cpp",
    "_GLOBAL__sub_I_HighsSolve.cpp",
    "_GLOBAL__sub_I_HighsStatus.cpp",
    "_GLOBAL__sub_I_HighsMipAnalysis.cpp",
    "_GLOBAL__sub_I_HighsFeasibilityJump.cpp",
    "_GLOBAL__sub_I_HighsImplications.cpp",
    "_GLOBAL__sub_I_HighsCliqueTable.cpp",
    "_GLOBAL__sub_I_HighsConflictPool.cpp",
    "_GLOBAL__sub_I_HighsDomain.cpp",
    "_GLOBAL__sub_I_HighsCutPool.cpp",
    "_GLOBAL__sub_I_HighsLpRelaxation.cpp",
    "_GLOBAL__sub_I_HighsMipSolver.cpp",
    "_GLOBAL__sub_I_HighsMipSolverData.cpp",
    "_GLOBAL__sub_I_HighsNodeQueue.cpp",
    "_GLOBAL__sub_I_HighsObjectiveFunction.cpp",
    "_GLOBAL__sub_I_HighsCutGeneration.cpp",
    "_GLOBAL__sub_I_HighsPrimalHeuristics.cpp",
    "_GLOBAL__sub_I_HighsPseudocost.cpp",
    "_GLOBAL__sub_I_HighsRedcostFixing.cpp",
    "_GLOBAL__sub_I_HighsSearch.cpp",
    "_GLOBAL__sub_I_HighsLpAggregator.cpp",
    "_GLOBAL__sub_I_HighsPathSeparator.cpp",
    "_GLOBAL__sub_I_HighsGFkSolve.cpp",
    "_GLOBAL__sub_I_HighsModkSeparator.cpp",
    "_GLOBAL__sub_I_HighsSeparation.cpp",
    "_GLOBAL__sub_I_HighsSeparator.cpp",
    "_GLOBAL__sub_I_HighsTableauSeparator.cpp",
    "_GLOBAL__sub_I_HighsTransformedLp.cpp",
    "_GLOBAL__sub_I_HighsHessian.cpp",
    "_GLOBAL__sub_I_HighsHessianUtils.cpp",
    "_GLOBAL__sub_I_HighsModel.cpp",
    "_GLOBAL__sub_I_CupdlpWrapper.cpp",
    "_GLOBAL__sub_I_HPresolve.cpp",
    "_GLOBAL__sub_I_HPresolveAnalysis.cpp",
    "_GLOBAL__sub_I_HighsPostsolveStack.cpp",
    "_GLOBAL__sub_I_HighsSymmetry.cpp",
    "_GLOBAL__sub_I_ICrash.cpp",
    "_GLOBAL__sub_I_ICrashUtil.cpp",
    "_GLOBAL__sub_I_ICrashX.cpp",
    "_GLOBAL__sub_I_PresolveComponent.cpp",
    "_GLOBAL__sub_I_a_asm.cpp",
    "_GLOBAL__sub_I_a_quass.cpp",
    "_GLOBAL__sub_I_basis.cpp",
    "_GLOBAL__sub_I_quass.cpp",
    "_GLOBAL__sub_I_HEkk.cpp",
    "_GLOBAL__sub_I_HEkkControl.cpp",
    "_GLOBAL__sub_I_HEkkDebug.cpp",
    "_GLOBAL__sub_I_HEkkDual.cpp",
    "_GLOBAL__sub_I_HEkkDualMulti.cpp",
    "_GLOBAL__sub_I_HEkkDualRHS.cpp",
    "_GLOBAL__sub_I_HEkkDualRow.cpp",
    "_GLOBAL__sub_I_HEkkPrimal.cpp",
    "_GLOBAL__sub_I_HSimplex.cpp",
    "_GLOBAL__sub_I_HSimplexDebug.cpp",
    "_GLOBAL__sub_I_HSimplexNla.cpp",
    "_GLOBAL__sub_I_HSimplexNlaDebug.cpp",
    "_GLOBAL__sub_I_HSimplexNlaFreeze.cpp",
    "_GLOBAL__sub_I_HSimplexNlaProductForm.cpp",
    "_GLOBAL__sub_I_HSimplexReport.cpp",
    "_GLOBAL__sub_I_HighsSimplexAnalysis.cpp",
    "_GLOBAL__sub_I_HFactor.cpp",
    "_GLOBAL__sub_I_HFactorDebug.cpp",
    "_GLOBAL__sub_I_HFactorRefactor.cpp",
    "_GLOBAL__sub_I_HVectorBase.cpp",
    "_GLOBAL__sub_I_HighsLinearSumBounds.cpp",
    "_GLOBAL__sub_I_HighsMatrixUtils.cpp",
    "_GLOBAL__sub_I_HighsSort.cpp",
    "_GLOBAL__sub_I_HighsSparseMatrix.cpp",
    "_GLOBAL__sub_I_HighsUtils.cpp",
    "_GLOBAL__sub_I_stringutil.cpp",
    "_GLOBAL__sub_I_control.cc",
    "_GLOBAL__sub_I_indexed_vector.cc",
    "_GLOBAL__sub_I_basiclu_wrapper.cc",
    "_GLOBAL__sub_I_basiclu_kernel.cc",
    "_GLOBAL__sub_I_forrest_tomlin.cc",
    "_GLOBAL__sub_I_guess_basis.cc",
    "_GLOBAL__sub_I_basis.cc",
    "_GLOBAL__sub_I_info.cc",
    "_GLOBAL__sub_I_iterate.cc",
    "_GLOBAL__sub_I_crossover.cc",
    "_GLOBAL__sub_I_kkt_solver.cc",
    "_GLOBAL__sub_I_ipm.cc",
    "_GLOBAL__sub_I_diagonal_precond.cc",
    "_GLOBAL__sub_I_linear_operator.cc",
    "_GLOBAL__sub_I_conjugate_residuals.cc",
    "_GLOBAL__sub_I_kkt_solver_diag.cc",
    "_GLOBAL__sub_I_kkt_solver_basis.cc",
    "_GLOBAL__sub_I_lp_solver.cc",
    "_GLOBAL__sub_I_lu_factorization.cc",
    "_GLOBAL__sub_I_lu_update.cc",
    "_GLOBAL__sub_I_maxvolume.cc",
    "_GLOBAL__sub_I_model.cc",
    "_GLOBAL__sub_I_normal_matrix.cc",
    "_GLOBAL__sub_I_sparse_matrix.cc",
    "_GLOBAL__sub_I_sparse_utils.cc",
    "_GLOBAL__sub_I_splitted_normal_matrix.cc",
    "_GLOBAL__sub_I_starting_basis.cc",
    "_GLOBAL__sub_I_symbolic_invert.cc",
    "_GLOBAL__sub_I_utils.cc",
)

# The features the build compiles for (spec 023, Decision 8): every host must support each.
FEATURES = (
    "+bulk-memory",
    "+bulk-memory-opt",
    "+call-indirect-overlong",
    "+exception-handling",
    "+extended-const",
    "+multivalue",
    "+mutable-globals",
    "+nontrapping-fptoint",
    "+reference-types",
    "+sign-ext",
    # OpenBLAS's kernels, compiled for WASM128_GENERIC (spec 037; decision 29): wasm SIMD is a
    # host requirement of the default build. Only OpenBLAS is compiled with it.
    "+simd128",
)


def constructor_errors(mod: wasm.Module) -> list[str]:
    try:
        found = wasm.call_ctors(mod)
    except wasm.WasmError as e:
        return [f"the static constructors cannot be read: {e}"]
    return list_errors(found, list(REVIEWED_CONSTRUCTORS))


def list_errors(found: list[str], reviewed: list[str]) -> list[str]:
    """The found list against the reviewed one, whole: each name counted, then the order."""
    have, want = Counter(found), Counter(reviewed)
    errors = [
        f"{c}: a static constructor no review has read"
        + (f" ({have[c] - want[c]} more than reviewed)" if want[c] else "")
        for c in have
        if have[c] > want[c]
    ]
    errors += [f"{c}: reviewed, but no longer linked" for c in want if want[c] > have[c]]
    if not errors and found != reviewed:
        errors.append(f"the constructors run in another order than reviewed: {found}")
    return errors


def feature_errors(mod: wasm.Module) -> list[str]:
    found = wasm.target_features(mod)
    if not found:
        return ["no target_features section"]
    errors = [f"{f}: a feature the line does not compile for" for f in found if f not in FEATURES]
    errors += [f"{f}: missing from target_features" for f in FEATURES if f not in found]
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python -m harness.constructors <python.wasm>", file=sys.stderr)
        return 2
    mod = wasm.parse_file(Path(argv[0]))
    errors = constructor_errors(mod) + feature_errors(mod)
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    if not errors:
        print(
            f"constructors: {len(REVIEWED_CONSTRUCTORS)} reviewed, none new; "
            f"target_features: the line's {len(FEATURES)}"
        )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
