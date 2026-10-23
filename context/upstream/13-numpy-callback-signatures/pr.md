# numpy PR: six callbacks with CPython's signatures, the facts to write from

> **Read first.** numpy's AI policy (`doc/source/dev/ai_policy.rst` on `main`, read 2026-10-18) forbids AI-written "comments, pull request descriptions, or issue descriptions" and an agent that "submits a pull request autonomously", and asks every pull request to disclose "which tool(s) have been used, how they were used". So this file is **not** a description to paste. It is the facts (question 80's form), under numpy's template headings, for you to write the description in your own words. Nothing has been posted, and no agent will post anything.

## Title

`BUG: give six C callbacks the signatures CPython calls them with`

## Commit message (a suggestion; rewrite it if you prefer)

```
BUG: give six C callbacks the signatures CPython calls them with

CPython calls a METH_NOARGS method as (self, NULL), a getter as
(self, closure), a setter as (self, value, closure) and a
METH_VARARGS|METH_KEYWORDS function as (self, args, kwargs). Six
functions were defined with fewer parameters and cast into those
tables. Native calling conventions ignore the extra argument;
WebAssembly checks the type of every indirect call and traps.
Each gains the missing parameter, unused.
```

## PR summary: the facts to cover

- **Problem.** Six functions are defined with fewer parameters than CPython passes them:

  | function (numpy 2.5.2) | defined as | CPython calls it as | reachable by users |
  |---|---|---|---|
  | `gentype___copy__`, `_core/src/multiarray/scalartypes.c.src:2128` | `(PyObject *self)` | `METH_NOARGS`: `(self, NULL)` | yes: `copy.copy` of any numpy scalar |
  | `array_descr_set`, `_core/src/multiarray/getset.c:388` | `(self, arg)` | a setter: `(self, value, closure)` | yes: `a.dtype = …` (deprecated in 2.5, still supported) |
  | `_get_castingimpl`, `_core/src/multiarray/convert_datatype.c:248` (and `.h:16`) | `(module, args)` | `METH_VARARGS \| METH_KEYWORDS`: `(module, args, kwargs)` | private (`_multiarray_umath._get_castingimpl`), used by numpy's tests |
  | `sfloat___reduce__`, `_core/src/umath/_scaled_float_dtype.c:192` | `(self)` | `METH_NOARGS` | private: numpy's test dtype |
  | `array_converter_get_scalar_input`, `_core/src/multiarray/array_converter.c:132` | `(self)` | a getter: `(self, closure)` | private: `_array_converter(...).scalar_input` |
  | `boundarraymethod__supports_unaligned`, `_core/src/multiarray/array_method.c:974` | `(self)` | a getter | private: through `_get_castingimpl`'s result |

  On the usual native ABIs the extra argument is ignored, so these work. WebAssembly's `call_indirect` checks the callee's exact type, and a mismatch traps: the whole call ends, not with a Python exception. All six definitions are unchanged on `main` (`7ed6cf7`, 2026-10-17).
- **Why numpy's CI does not see it.** numpy's WebAssembly job is Pyodide's, on Emscripten. CPython's Emscripten build calls every such function through a JavaScript trampoline (`Include/internal/pycore_emscripten_trampoline.h`: "Bad fpcasts are an issue in WebAssembly"). Its WASI build (`wasm32-wasip1`) has none, and plain WebAssembly has nothing to build one from.
- **Fix.** Each definition gains the parameter its call type passes, marked `NPY_UNUSED`: `PyObject *NPY_UNUSED(args)` for the two `METH_NOARGS` methods, `PyObject *NPY_UNUSED(kwargs)` for `_get_castingimpl` and its prototype, `void *NPY_UNUSED(ignored)` for the two getters and the setter. The method tables are untouched; `_get_castingimpl` keeps `METH_VARARGS | METH_KEYWORDS`, since `METH_VARARGS` alone would turn an ignored keyword into an error. No C code calls any of the six directly (`grep -rnw` over `numpy/_core/src`), so no caller changes. 7 files, 11 lines added, 7 removed (`fix.patch`, against 2.5.2).
- **Reproduction** (CPython 3.15 for `wasm32-wasip1` with numpy 2.5.2 built in, under Wasmtime 49): `python -c "import copy, numpy as np; print(copy.copy(np.float64(1.5)))"` traps; natively it prints `1.5`. Each call named in the next point traps alone in a guest without the change (`_supports_unaligned` cannot be reached until `_get_castingimpl` works), and a control line with no such callback runs (`context/upstream/13-numpy-callback-signatures/evidence/guest-before.txt`).
- **Evidence after the change** (`evidence/guest-after.txt`, `evidence/native.txt`): the same calls give native's output byte for byte: six scalar copies, `a.dtype = np.float32` with its `DeprecationWarning`, the scaled-float dtype's pickle round trip, `_get_castingimpl(...)` and its `_supports_unaligned`, and `_array_converter(1, [2]).scalar_input`.
- **Compiler.** Each changed file compiles with the build's own command and `-Wall` with the same warnings as before and no new one. clang's `-Wcast-function-type-mismatch` would flag these casts, but it flags CPython's ordinary `(PyCFunction)` cast of a three-parameter `METH_VARARGS | METH_KEYWORDS` function just the same, so it cannot tell this bug from the idiom.
- **How they were found.** numpy's own tests, run inside the guest, trapped at `copy.copy` and `a.dtype = …`. A scan of the linked binary then compared every referenced `PyMethodDef` and `PyGetSetDef` entry's function type with the type CPython calls it with (`evidence/scan-before.txt`): these six, and nothing else in numpy or pandas. With the change it finds none (`evidence/scan-after.txt`).
- **Tests.** The change alters no behaviour on any platform, so numpy's existing tests cover it. A test that would fail without it needs a WASI CI job, which numpy does not have.
- **Release note.** Probably none for a bug fix that changes no behaviour.

## First time contributor introduction

Yours to write, as for the `.npy` change (`../3-numpy-npy-wasi/pr.md`).

## AI Disclosure: the facts

- Tool: Claude (Anthropic), Claude Opus 5.5, run as a coding agent.
- What it did: traced the traps to the six definitions, wrote the patch, compiled it with the build's commands, ran the binary scan before and after, and ran the calls in the guest and natively.
- What is AI-generated: the code change (all of `fix.patch`). The description must be yours.
- What you checked: say what you reviewed and re-ran yourself.
