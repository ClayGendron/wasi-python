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
from pathlib import Path

from harness import wasm

# Each constructor a review has read, in link order, and what it does. None calls Python.
REVIEWED_CONSTRUCTORS = (
    "init",  # wasi-libc: the preopened directories
    "__wasilibc_initialize_environ_eagerly",  # wasi-libc: environ
    "_mi_process_init",  # CPython's mimalloc
    "register_builtin_extensions",  # scripts/gen_inittab.py: PyImport_AppendInittab only
    "_GLOBAL__sub_I_unique.cpp",  # numpy's unique.cpp: its hash tables' statics
    "_GLOBAL__I_000100",  # libc++'s iostream.cpp: std::ios_base::Init, the standard streams
    # matplotlib's _image_wrapper.cpp: Agg's sRGB_conv_base<int16u>::lut and <float>::lut, two
    # guarded template statics filled with pow(); spec 023's build read their disassembly
    "__cxx_global_var_init",
    "__cxx_global_var_init.5",
    # kiwisolver.cpp: kiwi::strength's four doubles and a std::recursive_mutex, its destructor
    # registered with __cxa_atexit
    "_GLOBAL__sub_I_kiwisolver.cpp",
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
)


def constructor_errors(mod: wasm.Module) -> list[str]:
    try:
        found = wasm.call_ctors(mod)
    except wasm.WasmError as e:
        return [f"the static constructors cannot be read: {e}"]
    reviewed = REVIEWED_CONSTRUCTORS
    new = [f"{c}: a static constructor no review has read" for c in found if c not in reviewed]
    gone = [f"{c}: reviewed, but no longer linked" for c in reviewed if c not in found]
    return new + gone


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
