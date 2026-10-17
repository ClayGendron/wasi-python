# C++ exceptions and WASI hosts

- **Status:** executed, 2026-10-16 (local probes run; the runtime survey is a desk study)
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), with two research sub-agents for the web survey.
  Box: 90 minutes; finished inside it.
- **Feeds:** spec 005 (`../specifications/005-the-3-15-line.md`), Decision 3, and its review's
  finding 4 (`../reviews/005-the-3-15-line-spec-2026-10-16.md`): the host requirement.
- **Stands on:** `2026-10-16-the-cpython-3-15-and-wasi-sdk-33-line.md` (finding 7: a C++ throw
  aborts on SDK 24 and reaches Python on SDK 33) and `2026-10-16-what-matplotlib-needs.md`
  (finding 4: pybind11, matplotlib and kiwisolver throw; FreeType and qhull use setjmp).
- **Evidence:** the probes ran in the session scratchpad (`…/scratchpad/research-eh/`), not in
  the repository. Each command and its output is in the Evidence section below. Nothing in the
  repository changed except this file.

## The question

Spec 005 would make every embedder's engine support the WebAssembly exception-handling proposal
("EH": the instructions that throw and catch inside wasm). The owner wants as many WASI hosts
as possible. So, before requiring EH:

1. Can C++ `throw`/`catch` and C `setjmp`/`longjmp` work on `wasm32-wasip1` without EH, under
   our rules (two imports only, zero patches, no JavaScript)?
2. Which WASI runtimes support EH today, and since when?
3. Is the standard form ("exnref") the one to target, or does the legacy form reach more hosts?
4. Two middle paths: does an EH module that never throws load on a host without EH? Could an
   EH-free "compat" set stand beside the EH set, and at what cost?

## Method

- **Local probes (EXECUTED).** Four small programs, written for this memo:
  - `throw.cpp`: a `throw` that crosses four frames with destructors, then a `catch`;
  - `nothrow.cpp`: a `try`/`catch` whose `throw` is never reached;
  - `sjlj.c`: a `longjmp` from three frames down;
  - `plain.c`: hello world.

  They were compiled with the pinned wasi-sdk 24 (`build/tools/`) and wasi-sdk 33. SDK 33 was
  downloaded into the scratchpad from its pinned URL and checked against
  `downloads/SHA256SUMS` (`shasum -a 256 -c`: `OK`). Each module ran under the pinned wasmtime
  49.0.3 CLI. `-W exceptions=n` stands in for a host without EH. A short script listed each
  module's imports, its tag section (section 13, which only EH code has) and its
  `target_features` section. pybind11 3.1.0 was fetched as its wheel and checked against the
  hash in the matplotlib memo (`OK`). A one-function pybind11 module was compiled against it.
- **Prior art (READ).** These clones:
  - `wasi-sdk` @ 2b65040: `CppExceptions.md`, `SetjmpLongjmp.md`;
  - `wasi-libc` @ 165235b: `include/setjmp.h`, `src/setjmp/wasm32/rt.c`;
  - `wasmtime` @ 2d9c19b: `crates/wasmtime/src/config.rs`, `crates/wasmtime/Cargo.toml`,
    `docs/stability-wasm-proposals.md`.
- **Web survey (READ through two sub-agents).** Release notes, docs and source of each runtime,
  LLVM, Binaryen, Ruby, pybind11, Pyodide and wasixcc. A claim marked "READ (survey)" was read
  at its URL by a sub-agent and was not re-read by the author. The author re-read three
  load-bearing ones, marked "READ (checked)": wasmtime 47's release note, WAMR's build doc and
  wazero's feature constants.

## Findings

### 1. Without EH, C++ exceptions have no route that keeps our rules; the only EH-free option is "a throw ends the program"

Each known route, and why it fails or what it costs:

| route | works on WASI without JS? | extra imports? | patches? | cost | maintained? |
|---|---|---|---|---|---|
| **a. `-fno-exceptions`** | compiles only code with no `try`/`throw` | no | yes, for any code that throws | none | yes |
| **b. Exceptions compiled, throw = abort** (today's 3.14 line, `recipes/cxa_stubs.c`) | yes, but every throw kills the guest | no | no | ~80 KB less than EH on a tiny program | ours |
| **c. Emscripten-style lowering** (`-mllvm -enable-emscripten-cxx-exceptions` / `-enable-emscripten-sjlj`) | only if the host implements `invoke_*` | **yes, 7 to 13 on a toy** | no | "relatively high overhead" | for Emscripten only |
| **d. Asyncify** (Binaryen's unwind/rewind pass) | setjmp/longjmp: yes; C++: no | no | no (a wrapper header) | +20–50% time, up to +50% size on instrumented code | Ruby uses it; no general library |
| **e. Hybrid c + d** (in-module `invoke_*` on asyncify, post-link import rewrite) | in theory | no, after a rewrite | no | as d, plus a hand-written `__cxa_*` runtime | **nobody has built it** |
| **f. LLVM's SjLj exception model** (`-fsjlj-exceptions`) | no: the wasm backend rejects it | – | – | – | – |
| **g. A libunwind-style stack walk** | no: wasm code cannot read its own call stack | – | – | – | – |
| **h. EH (exnref)**, as spec 005 | yes | no (the tag is defined inside the module) | no | needs a host with EH | yes: wasi-sdk 33, LLVM 22 |

The evidence for each row:

- **(a) `-fno-exceptions`.** Clang rejects any `throw` or `try` (EXECUTED: SDK 24 and 33 both
  give `error: cannot use 'throw' with exceptions disabled` on `throw.cpp`).
  - **pybind11 cannot use it.** A one-function module (`PYBIND11_MODULE` with one `m.def`)
    stops with 20 errors under SDK 33 and `-fno-exceptions` (EXECUTED). The first ones are at
    `detail/common.h:1153`, `:1157` and `pytypes.h:347`, `:869`.
  - The same file compiles with no error under `-fwasm-exceptions -mllvm
    -wasm-use-legacy-eh=false` (EXECUTED).
  - pybind11 3.1.0's headers have no `__cpp_exceptions` guard or `-fno-exceptions` mode
    (EXECUTED: `grep` finds none). They have 224 `throw` and 42 `try` tokens.
  - pybind11's author refused such a mode (READ, survey: PR #1703,
    <https://github.com/pybind/pybind11/pull/1703>, closed by wjakob: "exceptions are really
    central to the internals of pybind11 ... this will break any kind of error handling").
- **(b) Exceptions compiled, throw = abort.** Without `-fwasm-exceptions`, clang accepts
  `try`/`catch`. The catch blocks become dead code and a `throw` calls `__cxa_throw`.
  - The no-EH libc++abi of SDK 24 and SDK 33 does not define `__cxa_throw` (EXECUTED: link
    error `undefined symbol: __cxa_throw`).
  - A stub that aborts links (EXECUTED): `throw.cpp` prints the stub's message and traps;
    `nothrow.cpp` runs under `-W exceptions=n`.
  - This is the 3.14 line today. Ordinary error paths die (the 3.15 memo, finding 7).
  - For pybind11 it is worse: its overload dispatcher throws and catches on ordinary calls (the
    matplotlib memo, 4a). So matplotlib cannot use this route.
- **(c) Emscripten-style lowering needs the host to catch.**
  - A C++ build of `throw.cpp` with SDK 24 and `-mllvm -enable-emscripten-cxx-exceptions`
    imports 13 non-WASI functions from `env` (EXECUTED). Among them: `invoke_vi`,
    `invoke_iii`, `invoke_viii`, `__cxa_find_matching_catch_2`/`_3`, `__resumeException`,
    `getTempRet0`, `llvm_eh_typeid_for`.
  - The setjmp form imports `saveSetjmp`, `testSetjmp`, `invoke_v`, `invoke_iii`,
    `emscripten_longjmp`, `getTempRet0`, `setTempRet0` (EXECUTED).
  - LLVM marks the `invoke_*` names as imports on purpose. They "cannot be provided by any
    kind of shared or static library" (READ, survey: `WebAssemblyLowerEmscriptenEHSjLj.cpp`,
    <https://raw.githubusercontent.com/llvm/llvm-project/main/llvm/lib/Target/WebAssembly/WebAssemblyLowerEmscriptenEHSjLj.cpp>).
  - **This breaks §4.4 (two imports only).** Each embedder would also have to write a catching
    `invoke_*` for every call signature.
  - Non-JS precedent: wazero and old Wasmer implement these imports for longjmp only. Wasmer's
    `__cxa_find_matching_catch` is a stub that returns 0 (READ, survey: wazero
    `internal/emscripten/emscripten.go`; Wasmer 2.3.0 `lib/emscripten`).
- **(d) Asyncify can do setjmp/longjmp, not C++ exceptions.**
  - Asyncify is a Binaryen pass that lets wasm code save its stack to memory and resume it.
  - CRuby's WASI port implements `setjmp` by unwinding to a root loop and rewinding (READ,
    survey: `ruby/ruby` `wasm/setjmp.c`, `wasm/runtime.c`).
  - Binaryen turns the asyncify imports into direct calls, so no host import remains (READ,
    survey: Binaryen `src/passes/Asyncify.cpp`).
  - The cost:
    - "the binary is around 50% larger on average", "just enabling Asyncify adds some
      overhead (22%)" (READ, survey: <https://kripken.github.io/blog/wasm/2019/07/16/asyncify.html>);
    - Wasmer measured "20-50% slower", and a 3–4× speed-up for PHP when it moved setjmp from
      asyncify to EH (READ, survey: <https://wasmer.io/posts/announcing-wasmer-6-closer-to-native-speeds>).
  - Asyncify saves locals; it never runs landing pads or destructors. So it cannot unwind C++
    frames by itself (INFERRED). wasixcc, which uses asyncify by default, says C++ exceptions
    are "likely to be broken" in that mode (READ, survey: <https://docs.rs/crate/wasixcc/0.3.0>).
  - What it would take here (INFERRED):
    - a new pinned tool (Binaryen) and an extra post-link pass;
    - a wrapper `setjmp.h` for qhull. FreeType allows its own override: predefine
      `FTSTDLIB_H_` (READ, survey: `include/freetype/config/ftstdlib.h`);
    - the root-loop rewrite of every entry point (`run`, the Wizer init);
    - instrumenting every function on a path between a `setjmp` and its `longjmp`.
- **(e) The hybrid has no implementation anywhere** (READ, survey: none found). It would mean
  writing our own C++ exception runtime on asyncify, plus a binary rewrite that turns LLVM's
  forced imports into module functions. That is a toolchain project, which §3 rules out ("not
  a general wasm toolchain") (INFERRED).
- **(f) LLVM's SjLj exception model.** `-fsjlj-exceptions` on `wasm32-wasip1` stops with
  `fatal error: error in backend: -exception-model should be either 'none' or 'wasm'`
  (EXECUTED, SDK 33 / clang 22.1.0).
- **(g) Stack walking.** LLVM's wasm libunwind (`Unwind-wasm.c`) is built only under
  `__WASM_EXCEPTIONS__`. Its `_Unwind_RaiseException` is a wasm `throw` (READ, survey:
  <https://raw.githubusercontent.com/llvm/llvm-project/main/libunwind/src/Unwind-wasm.c>).
  Wasm keeps its call stack out of reach of the code (READ, survey:
  <https://webassembly.org/docs/security/>). So there is no unwinder without EH (INFERRED).

**setjmp/longjmp is the same story** (READ: `wasi-libc/libc-top-half/musl/include/setjmp.h:12-13`
stops with `#error` unless `__wasm_exception_handling__`; `src/setjmp/wasm32/rt.c` implements
`longjmp` as `__builtin_wasm_throw`). Without EH, the only working route is asyncify (d).

**SDK 24 cannot do setjmp even with EH** (EXECUTED). Clang 18 with `-mllvm -wasm-enable-sjlj
-lsetjmp` emits calls to `saveSetjmp`, `testSetjmp` and `getTempRet0`. SDK 24's `libsetjmp.a`
defines `__wasm_setjmp`, `__wasm_setjmp_test` and `__wasm_longjmp` instead. So the three calls
are left as imports, and the code uses the legacy `try` instruction, which wasmtime 49 rejects.

### 2. EH works today, costs no import, and on SDK 33 costs about 80 KB on a tiny program

- **It works** (EXECUTED, SDK 33, standard EH):
  - `throw.cpp` prints `caught: from deep; destructors run: 4` and exits 0;
  - `sjlj.c` prints `longjmp returned 42`.
- **No import is added** (EXECUTED). `throw.cpp` imports 7 WASI functions; `sjlj.c` imports 5.
  The tag is defined inside the module. The review of spec 005 found the same for
  `python.wasm` (§4.4 holds).
- **Size** (EXECUTED, SDK 33, `-O2`). `nothrow.cpp` is 378,225 bytes with EH and 298,074 bytes
  with the abort stub (−80 KB, −21%). The difference is libunwind, the EH-enabled libc++abi and
  libc++, and landing pads. For `python.wasm` the 3.15 memo measured the whole effect: the
  3.15 + SDK 33 reactor is 29,801,866 bytes against 29,829,406 for 3.14 + SDK 24 (finding 4
  there). That compares different CPython versions, so the EH share cannot be read from it
  (INFERRED).
- **Speed.** Fuel (wasmtime's instruction count) on the 3.15 line is +0.0% to +0.8% for the
  plain runs (the 3.15 memo, finding 9). Asyncify's +20–50% (finding 1d) is the figure to
  compare with (INFERRED).

### 3. Which runtimes support EH

"exnref" is the standard form: `try_table`, `throw`, `throw_ref` and the `exnref` value type.
"Legacy" is the older form (`try`, `catch`, `delegate`, `rethrow`) that browsers shipped first.

| runtime | standard (exnref) | legacy | default |
|---|---|---|---|
| **wasmtime CLI and Rust crate** | since 37.0.0 (2025-09-20) | **no** | on since **47.0.0 (2026-07-20)**; `-W exceptions=y` from 37 to 46; off on Winch; needs the `gc` cargo feature |
| **wasmtime-py** | yes | no | on from 47 (INFERRED from the C API); **EXECUTED on 49** in the 3.15 memo |
| wasmtime-dotnet / wasmtime-go | through the C API | no | follows the C API; Go has no switch (INFERRED) |
| **wasmer** | LLVM since 6.0 (2025-04), V8 since 6.1, Cranelift since 7.0 (2026-01); **Singlepass: no** | no (INFERRED) | off; the CLI detects EH in a module and picks a backend, or `--enable-exceptions` |
| **wazero** | since v1.12.0 (2026-05) | **no**; its error message suggests `wasm-opt --translate-to-exnref` | **off: experimental opt-in** `experimental.CoreFeaturesExceptionHandling` |
| **WAMR** | **no** | classic interpreter only, since 1.3.2 | off: build with `WAMR_BUILD_EXCE_HANDLING=1`; no fast-interp, AOT or JIT |
| **WasmEdge** | interpreter since 0.14; AOT and JIT since 0.18.0 (2026-10-05) | removed in 0.16 | on since 0.16.0 (2025-12-31) |
| **wasm3** | v0.9.1-beta.1 says "Exception Handling with exnref" | not stated | not stated; the README still says "minimal maintenance" |
| **Node.js WASI (V8)** | 22.19+: forced on, but V8 12.4's version predates the spec, fixed toward 22.22.3; 24.0–24.14: flag; **on in 24.15+ and 25+** | on since 17 | as left |
| **browsers (WASI shims use the browser's engine)** | Chrome 137, Firefox 131, Safari 18.4 | Chrome 95, Firefox 100, Safari 15.2 | both on |
| Deno | 2.3.2 | 1.16 | on |
| GraalWasm | 25.1 | 25.1, off | exnref on |
| wasmi | no (planned) | no | – |
| wasmer-python, wasmer-go | no: last releases predate Wasmer 6 (INFERRED) | no | – |

Sources:

- **wasmtime.**
  - 47.0.0: "Wasmtime now has the WebAssembly exception-handling proposal enabled by default"
    (READ, checked: <https://raw.githubusercontent.com/bytecodealliance/wasmtime/release-47.0.0/RELEASES.md>).
  - 37.0.0 first implemented it fully (READ, survey: the 37.0.0 `RELEASES.md`).
  - `wasm_exceptions` is "`true` by default, except when using `Strategy::Winch`" and needs
    `#[cfg(feature = "gc")]`. The legacy switch is `#[doc(hidden)]` and "only exists for
    internal usage with the spec testsuite" (READ: `crates/wasmtime/src/config.rs:1445-1464`,
    clone 2d9c19b). `gc` is a default cargo feature (READ: `crates/wasmtime/Cargo.toml:130-157`).
  - EH is a tier-1 proposal (READ: `docs/stability-wasm-proposals.md:37`).
  - Cranelift rejects the legacy instructions (READ, survey: `code_translator.rs`). Wasmtime
    49 gives `legacy_exceptions feature required for try instruction` on a legacy module
    (EXECUTED, finding 4).
- **wasmer** (READ, survey): `CHANGELOG.md`; `lib/types/src/features.rs` ("This is `false` by
  default"); `lib/cli/src/backend.rs`; `lib/compiler-singlepass/src/config.rs`.
- **wazero.** EH is an experimental constant, outside `api.CoreFeaturesV2` (READ, checked:
  `experimental/features.go`, `api/features.go`). Release v1.12.0 and PR #2489 ("only
  implements the new EH proposal") (READ, survey).
- **WAMR.** "default to off", "works only in classic interpreter mode", "supports only Legacy
  Wasm exception handling proposal, not the latest version" (READ, checked:
  <https://raw.githubusercontent.com/bytecodealliance/wasm-micro-runtime/main/doc/build_wamr.md>).
- **WasmEdge** (READ, survey): the proposals page
  <https://wasmedge.org/docs/start/wasmedge/extensions/proposals/>; release notes 0.14.0, 0.16.0
  and 0.18.0.
- **wasm3** (READ, survey): README; release v0.9.1-beta.1. The page shows no year; 2026 is
  inferred from the commit dates.
- **Node** (READ, survey): `deps/v8/src/wasm/wasm-feature-flags.h` at v24.14.0 (exnref staged,
  `false`) and v24.15.0 (shipped, `true`); `src/node.cc` at v22.19.0; nodejs/node PRs #59179
  and #62783.
- **Browsers, Deno, GraalWasm** (READ, survey):
  <https://raw.githubusercontent.com/WebAssembly/website/main/features.json> (keys `exceptions`
  and `exceptionsFinal`); graal `wasm/CHANGELOG.md`.
- **wasmi** (READ, survey): its README, tracking issue #1137.

Not confirmed: wasm3's default and flag; Chicory's form; whether wasmer's V8 backend takes the
legacy form; the first wasmtime-py with the setter (39.0.0, INFERRED).

### 4. Standard EH (exnref) is the standard; legacy would add almost no WASI host and costs wasmtime

- **exnref is the standard.**
  - The exception-handling proposal is finished and part of Wasm 3.0 (READ, survey:
    <https://raw.githubusercontent.com/WebAssembly/proposals/main/finished-proposals.md>, WG
    2025-07-23, spec "3.0").
  - Wasm 3.0 was announced 2025-09-17 (READ, survey:
    <https://webassembly.org/news/2025-09-17-wasm-3.0/>).
  - wasi-sdk calls the proposal "phase 5" (READ: `wasi-sdk/SetjmpLongjmp.md`).
- **Legacy is superseded.**
  - "This proposal was superseded by the current proposal in Oct 2023 CG meeting" (READ,
    survey: `exception-handling/proposals/exception-handling/legacy/Exceptions.md`).
  - It is in no ratified spec and lives on for the web's sake (INFERRED).
  - LLVM 22 still emits legacy by default unless `-wasm-use-legacy-eh=false` is given (READ:
    `wasi-sdk/CppExceptions.md`). That is why spec 005 must keep the flag.
- **Legacy reaches no extra host that matters, and it loses wasmtime** (EXECUTED and READ):
  - wasmtime 49 rejects legacy code: `legacy_exceptions feature required for try instruction`.
    This holds for C++ (`-wasm-use-legacy-eh=true`) and for setjmp (EXECUTED);
  - wazero and WasmEdge 0.16+ reject it too (READ, survey);
  - legacy-only hosts are WAMR's classic interpreter (behind a build flag), Node 17 to 24.14,
    and browsers older than Chrome 137, Firefox 131 or Safari 18.4.
- **One binary cannot carry both forms for one engine set** (INFERRED). SDK 33's prebuilt
  libc++abi, libunwind and libsetjmp use the standard form (READ: `CppExceptions.md`,
  "Precompiled libraries for wasi-sdk are all built with the standard exception-handling
  proposal").
  - A legacy build would need its own sysroot, which means building wasi-sdk from source.
  - Binaryen converts legacy to exnref (`--translate-to-exnref`) but not the other way
    (READ, survey: Binaryen `src/passes/pass.cpp`).
- So the legacy form would gain only WAMR's slow interpreter and old Node, and lose the
  project's own runtime (INFERRED).

### 5. A module with EH code that never throws does not load on a host without EH

- `nothrow.cpp` with EH runs under default wasmtime (`value: 2`). Under `-W exceptions=n` it
  fails at parse time (EXECUTED): `exception refs not supported without the exception handling
  feature (at offset 0xc)`. Offset `0xc` is the type section, so validation stops before any
  code runs.
- `sjlj.c` under `-W exceptions=n` gives `exceptions proposal not enabled` (EXECUTED).
- The flag alone does no harm. `plain.c` built with `-fwasm-exceptions` has no tag section and
  runs under `-W exceptions=n` (EXECUTED). What blocks loading is EH code linked in: libc++abi,
  libunwind, a `try` or a `setjmp`.
- **The expectation holds.** Validation is all-or-nothing, so "has EH but never throws" is not
  a middle path.
- The 3.14 set has no EH. `build/artifacts/python.wasm` and `python-snapshot.wasm` have no
  tag section, and `wasmtime compile -W exceptions=n build/artifacts/python.wasm` exits 0
  (EXECUTED).

### 6. SDK 33 narrows the host set a little even without EH

- SDK 33's sysroot is built for a newer default CPU (EXECUTED: `plain.c` declares
  `+bulk-memory-opt +call-indirect-overlong +extended-const +multivalue +nontrapping-fptoint
  +reference-types`; SDK 24's declares only `+bulk-memory +mutable-globals +sign-ext`).
  `-mcpu=mvp` on our own code does not remove them, because the libraries carry them.
- SDK 33's `plain.c` needs reference-types (EXECUTED):
  - with reference-types, multi-value, extended-const and EH all off, it fails with `zero byte
    expected`: the "overlong" `call_indirect` encoding;
  - with reference-types back on, it runs;
  - SDK 24's `plain.c` runs either way.
- reference-types is in Wasm 2.0 and in wazero's default `CoreFeaturesV2` (READ, checked). So
  this narrows only hosts older than Wasm 2.0 (INFERRED).
- wazero treats extended-const as experimental (READ, checked). Whether `python.wasm` on SDK
  33 uses extended-const instructions is untested. If it does, wazero needs that opt-in too
  (INFERRED).

### 7. An EH-free compat set beside the EH set: possible, with these costs

Three shapes, cheapest first (all INFERRED from the findings above):

1. **Keep the 3.14 + SDK 24 set published as the compat set.** The constitution already says
   old sets stay published (§3). It has no EH (finding 5). Costs:
   - it stays on CPython 3.14.8; a security fix means rebuilding a second line;
   - a C++ error in numpy kills the guest (the 3.15 memo, finding 7);
   - no matplotlib, ever: pybind11 3.x does not compile on SDK 24 and SDK 24 has no setjmp
     (the matplotlib memo, 4b and 4c; finding 1 here);
   - the README must say which set needs which host.
2. **A second link of the 3.15 line without EH** (a build-time profile, constitution §2):
   - the C++ objects (numpy's) are compiled again without `-fwasm-exceptions`;
   - it links the no-EH libc++ with an abort stub;
   - it gets its own snapshot.

   Costs:
   - a second artifact set: built, judged, published and named in `MANIFEST`;
   - about a second build's time;
   - a scoreboard dimension for the second set;
   - throws abort, as in shape 1;
   - matplotlib cannot be in it (pybind11 throws on ordinary calls; FreeType and qhull need
     setjmp).
3. **A post-link `wasm-opt --strip-eh` of the EH set.** Binaryen's StripEH pass removes catches
   and turns throws into `unreachable` ("Any exception thrown will crash the program") (READ,
   survey: Binaryen `src/passes/StripEH.cpp`). Costs:
   - a new pinned tool;
   - a separate snapshot;
   - no test that it handles exnref's `throw_ref` (the survey found no explicit handler);
   - a binary that no compiler produced, so the judge must cover it as its own set.

   Not run.

In every shape the compat set is "numpy and pandas, where a C++ throw ends the guest". It can
never carry matplotlib.

## What it decides

**Recommendation to the owner:**

- **Require EH, in its standard (exnref) form, for the 3.15 line**, as spec 005 Decision 3
  says. Without EH, C++ exceptions have no working route under our rules. The Emscripten route
  adds imports (§4.4). Asyncify does setjmp but not C++. The hybrid is a toolchain nobody has
  built. pybind11, and so matplotlib, needs real exceptions.
- **Do not target the legacy form.** It would lose wasmtime, wazero and WasmEdge, and gain
  only WAMR's classic interpreter and older Node.
- **Answer review finding 4 with this host table in the README**:
  - runs by default: wasmtime ≥ 47 (CLI, Rust, wasmtime-py; 37–46 with `-W exceptions=y`)
    and WasmEdge ≥ 0.16 (AOT ≥ 0.18);
  - runs with a switch: wasmer ≥ 6 on LLVM, V8 or Cranelift ≥ 7 (not Singlepass); wazero
    ≥ 1.12 with its experimental opt-in; Node ≥ 24.15 or 25;
  - does not run: WAMR, wasmi, wasmer-python, wasmer-go, wasmtime's Winch, and wasmtime built
    without the `gc` feature.

  Only wasmtime 49 has actually been run. The rest are read, and the README should say so.
- **Keep the EH-free set as it is**: the 3.14 + SDK 24 set (0.1.0a1 and any 3.14 patch
  release), named in the README as the set for hosts without EH, with its limit stated (a C++
  throw ends the guest; no matplotlib).
- Build an EH-free 3.15 set (shape 2 or 3) only if an embedder needs one. It would be a profile
  under `2026-10-16-build-time-profiles-of-the-core-c-libraries.md`, not part of spec 005.
- **Two small follow-ups for spec 005** (INFERRED):
  - a check that the built module has exnref and no legacy `try` (so a missing
    `-wasm-use-legacy-eh=false` cannot ship);
  - a note on finding 6: whether `python.wasm` uses extended-const, which wazero gates.

## Evidence

All under `…/scratchpad/research-eh/`. `cxx24`/`cxx33` are `clang++ --target=wasm32-wasip1
--sysroot=<sdk>/share/wasi-sysroot -O2` from the pinned SDK 24 and the hash-checked SDK 33.
`WT` is `build/tools/wasmtime-v49.0.3-aarch64-macos/wasmtime`.

```
cxx24 -fno-exceptions throw.cpp           → error: cannot use 'throw' with exceptions disabled
cxx24 throw.cpp ; cxx33 throw.cpp         → wasm-ld: undefined symbol: __cxa_throw
cxx24 -fwasm-exceptions throw.cpp         → undefined symbol: __wasm_lpad_context, _Unwind_CallPersonality, …
cxx24 -fexceptions -mllvm -enable-emscripten-cxx-exceptions throw.cpp -Wl,--allow-undefined
                                          → 18 imports, 13 from env (invoke_vi, invoke_iii, invoke_viii,
                                            __cxa_find_matching_catch_2/_3, __resumeException, getTempRet0, …)
cc24 -mllvm -enable-emscripten-sjlj sjlj.c (setjmp.h guard bypassed by -D, probe only)
                                          → env: saveSetjmp testSetjmp invoke_v invoke_iii
                                            emscripten_longjmp getTempRet0 setTempRet0
cc24 -mllvm -wasm-enable-sjlj sjlj.c -lsetjmp ; WT run
                                          → imports saveSetjmp/testSetjmp/getTempRet0;
                                            legacy_exceptions feature required for try instruction
cxx33 -fwasm-exceptions -mllvm -wasm-use-legacy-eh=false throw.cpp -lunwind ; WT run
                                          → caught: from deep; destructors run: 4   (7 WASI imports, tag section)
  … WT run -W exceptions=n                → exception refs not supported without the exception handling feature (at offset 0xc)
cxx33 … -wasm-use-legacy-eh=true throw.cpp -lunwind ; WT run
                                          → legacy_exceptions feature required for try instruction
cc33 -mllvm -wasm-enable-sjlj -mllvm -wasm-use-legacy-eh=false sjlj.c -lsetjmp ; WT run
                                          → longjmp returned 42 ; with -W exceptions=n: exceptions proposal not enabled
cc33 … -wasm-use-legacy-eh=true sjlj.c ; WT run → legacy_exceptions feature required for try instruction
cxx33 -fwasm-exceptions … nothrow.cpp -lunwind → 378,225 bytes; WT run: value: 2; -W exceptions=n: exception refs not supported …
cxx33 nothrow.cpp abort_stubs.o           → 298,074 bytes, no tag section; -W exceptions=n: value: 2
cc33 -fwasm-exceptions … plain.c          → no tag section; -W exceptions=n: plain
cxx33 -fexceptions -fsjlj-exceptions -c throw.cpp
                                          → error in backend: -exception-model should be either 'none' or 'wasm'
cxx33 -std=c++17 -fno-exceptions -I pybind11-3.1.0 -I Python-3.14.8/{Include,cross-build/wasm32-wasip1} -c mod.cpp
                                          → 20 errors, first pybind11/detail/common.h:1153: cannot use 'throw' with exceptions disabled
cxx33 -std=c++17 -fwasm-exceptions -mllvm -wasm-use-legacy-eh=false … -c mod.cpp → exit 0
cc33 plain.c ; WT run -W exceptions=n,gc=n,function-references=n,component-model=n,
   component-model-async=n,reference-types=n,multi-value=n,extended-const=n
                                          → zero byte expected   (SDK 24's plain.c: runs)
WT compile -W exceptions=n build/artifacts/python.wasm → exit 0 (3.14 set: no tag section)
shasum -a 256 -c (wasi-sdk-33.0-arm64-macos.tar.gz, pybind11-3.1.0-py3-none-any.whl) → OK, OK
```

## One line

Without the exception-handling proposal, C++ exceptions on WASI can only end the program, and
setjmp needs Binaryen's asyncify at a large cost. So require standard (exnref) EH for the 3.15
line, name the hosts that have it, and keep the EH-free 3.14 set for hosts that do not.
