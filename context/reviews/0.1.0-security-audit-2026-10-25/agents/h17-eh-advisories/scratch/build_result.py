import json, sys
CID = "build%2Fartifacts%2Fpython.wasm%23try_table::src%2Fwasi_python%2F_engines.py%23_engine::build%2Fartifacts::MEMORY-SAFETY-AND-BINARY.md%23JIT%20and%20generated-code%20consistency"
AG = "h17-eh-advisories"
FP = "wasmtime-49.0.0:GHSA-m63x-6p34-q65x:try_table-catch-fuel:src/wasi_python/_engines.py:_engine"
ADV = "context/research/2026-10-18-wasmtime-49-advisories/advisories/"
checks = [
 {"agent_id": AG, "reviewed_paths": ["build/artifacts/python.wasm", "build/artifacts/python-snapshot.wasm"],
  "invariant": "GHSA-p79w-pv2r-29qp precondition: the module declares an odd number of exception tags (defined plus imported)",
  "method": "local",
  "result": "Read-only section parse of both shipped binaries: the tag section (id 13, 5 bytes) defines exactly 2 tags, both type 6, and no tag is imported (all 43 imports are functions). 2 is even, so the VMContext misalignment precondition is not met by the current artifacts under wasmtime 49.0.0. Target not read-only mounted; the parse ran with the system python3 -I on the files, executing no target code.",
  "artifact": "agents/h17-eh-advisories/artifacts/evidence/eh_sections.json"},
 {"agent_id": AG, "reviewed_paths": ["build/artifacts/python.wasm", "build/artifacts/python-snapshot.wasm", "src/wasi_python/_engines.py"],
  "invariant": "GHSA-wjc8-633q-pwxr precondition: a module (guest-supplied or shipped) registers a long chain of recursive types whose drop recurses in the host type registry",
  "method": "local",
  "result": "Both binaries' type sections hold 858 entries, all plain func types: no explicit rec group, no sub/sub-final declaration, supertype chain depth 0, and no typed reference (0x63/0x64) in any signature (only one exnref, 0x69), so no type refers to another and no chain exists. The guest is Python inside python.wasm and has no API to compile or instantiate a wasm module; the only other module the runner compiles is the fixed _CHECK_WAT (src/wasi_python/_engines.py:47-56), three func types. Precondition not met.",
  "artifact": "agents/h17-eh-advisories/artifacts/evidence/eh_sections.json"},
 {"agent_id": AG, "reviewed_paths": ["build/artifacts/python.wasm"],
  "invariant": "GHSA-m63x-6p34-q65x precondition: the guest bytecode contains try_table or call_ref",
  "method": "local",
  "result": "llvm-objdump -d (wasi-sdk 34) over python.wasm counted 31,968,592 instructions in 89,061 functions: try_table 44,791 (in 7,905 functions), throw_ref 26,569, throw 2 (one in __wasm_longjmp, one in _Unwind_RaiseException), call_ref 0, return_call_ref 0. target_features includes +exception-handling. The try_table precondition is met; call_ref is absent.",
  "artifact": "agents/h17-eh-advisories/artifacts/evidence/eh_opcount_python.txt"},
 {"agent_id": AG, "reviewed_paths": ["build/artifacts/python-snapshot.wasm"],
  "invariant": "GHSA-m63x-6p34-q65x precondition holds for the snapshot too",
  "method": "local",
  "result": "Same counts in python-snapshot.wasm: try_table 44,791 in 7,905 functions, throw_ref 26,569, throw 2, call_ref 0; +exception-handling in target_features. The Wizer snapshot keeps the code section unchanged.",
  "artifact": "agents/h17-eh-advisories/artifacts/evidence/eh_opcount_python-snapshot.txt"},
 {"agent_id": AG, "reviewed_paths": ["src/wasi_python/_engines.py", "uv.lock", "pyproject.toml", "src/wasi_python/_call.py", "src/wasi_python/runner.py", "src/wasi_python/_limits.py"],
  "invariant": "The metered engine under the resolved wasmtime is outside GHSA-m63x's affected range, or fuel is not the only bound on a metered call",
  "method": "source",
  "result": "_engine sets only consume_fuel=metered, epoch_interruption, the async stack and max_wasm_stack (_engines.py:110-127), so exceptions stay at wasmtime's default (on since 47.0.0) and the compiler is the default Cranelift: the advisory's configuration. pyproject.toml:18 pins wasmtime>=49,<50 and uv.lock:1048-1049 resolves 49.0.0, inside the affected range (fixed 49.0.1). A metered call sets fuel at _call.py:412-416 and reports fuel_used at :511. The deadline defaults from limits (runner.py:574-575) and epoch interruption is not affected by the advisory, so a call with a deadline stays wall-clock bounded; an embedder that passes fuel with deadline_s=None has fuel as its only instruction bound.",
  "artifact": None},
 {"agent_id": AG, "reviewed_paths": ["recipes/wasi-numpy.cross", "recipes/wasi-pandas.cross", "recipes/wasi-scipy.cross", "recipes/wasi-matplotlib.cross", "scripts/steps/60_link.sh", "scripts/steps/80_snapshot.sh"],
  "invariant": "Where the try_table code comes from and whether ordinary guest Python can reach it",
  "method": "source",
  "result": "The cross files compile C++ with -fwasm-exceptions -fexceptions and -wasm-use-legacy-eh=false (wasi-numpy.cross:37, wasi-pandas.cross:31, wasi-scipy.cross:44, wasi-matplotlib.cross:39), and C with -wasm-enable-sjlj (wasi-scipy.cross:39, wasi-matplotlib.cross:37); 60_link.sh:129 links with -fwasm-exceptions; 80_snapshot.sh:18 runs Wizer with -W exceptions=y. So every caught C++ exception and every setjmp/longjmp return in the compiled-in packages goes through a try_table catch, and guest Python reaches those paths through ordinary package calls. Python's own exceptions do not use try_table (CPython signals them by return value). The 2026-10-18 advisories memo's statement that the module enables no exception proposal predates these flags and is out of date.",
  "artifact": None},
]
paths = sorted({p for c in checks for p in c["reviewed_paths"]} | {ADV+"GHSA-m63x-6p34-q65x.json", ADV+"GHSA-p79w-pv2r-29qp.json", ADV+"GHSA-wjc8-633q-pwxr.json"})
# keep unit paths exactly the union of check paths: add advisory files to the source check
checks[4]["reviewed_paths"] += [ADV+"GHSA-m63x-6p34-q65x.json", ADV+"GHSA-p79w-pv2r-29qp.json", ADV+"GHSA-wjc8-633q-pwxr.json"]
paths = sorted({p for c in checks for p in c["reviewed_paths"]})
cand = {
 "proposed_verdict": "needs_validation",
 "fingerprint": FP,
 "title": "Shipped binaries carry 44,791 try_table sites run on a metered wasmtime 49.0.0 engine affected by GHSA-m63x-6p34-q65x (fuel dropped on the catch path)",
 "description": "A metered call compiles python.wasm (or the snapshot) on an engine with consume_fuel and wasmtime's default exception support, under the wasmtime 49.0.0 the pin resolves to. GHSA-m63x-6p34-q65x (fixed 49.0.1) says Cranelift's fuel accounting on the catch path of a call inside a try_table can drop the fuel the callee used, resetting to the fuel left before the call. The shipped code has 44,791 try_table instructions in 7,905 functions, from C++ exceptions and setjmp/longjmp built with the new exception-handling proposal, and guest Python reaches them through the compiled-in packages. So the advisory's preconditions are met, and a guest may spend more instructions than its fuel cap counts. SECURITY.md counts running past the fuel cap as in scope. How much fuel a Python-reachable catch path drops, and whether it compounds, was not measured. The default deadline still bounds wall-clock time; a call with fuel and deadline_s=None relies on fuel alone.",
 "claimed_root_cause": "The runner's dependency pin (pyproject.toml wasmtime>=49,<50, resolved to 49.0.0 in uv.lock) admits a wasmtime whose Cranelift fuel accounting is wrong on try_table catch paths, while the build's -fwasm-exceptions flags put try_table on every caught C++ exception and longjmp path, and _engine leaves exceptions enabled on the metered engine. The runner carries no mitigation for this advisory, unlike its shadows for the filesystem advisories.",
 "trace": [
  {"kind": "entrypoint", "file": "recipes/wasi-scipy.cross", "line": 44, "scope": "C++ and sjlj build flags", "description": "Compiled-in C++ is built with -fwasm-exceptions -fexceptions and -wasm-use-legacy-eh=false (C with -wasm-enable-sjlj at line 39), so guest Python calls that throw and catch in C++, or longjmp, run try_table catch paths."},
  {"kind": "propagation", "file": "scripts/steps/60_link.sh", "line": 129, "scope": "link", "description": "python.wasm is linked with -fwasm-exceptions; the shipped module has 44,791 try_table, 26,569 throw_ref and 2 throw instructions, and +exception-handling in target_features."},
  {"kind": "propagation", "file": "uv.lock", "line": 1049, "scope": "wasmtime pin", "description": "wasmtime-py resolves to 49.0.0, inside GHSA-m63x's affected range (fixed in 49.0.1)."},
  {"kind": "propagation", "file": "src/wasi_python/_engines.py", "line": 122, "scope": "_engine", "description": "The metered engine sets consume_fuel and leaves wasm exceptions and the Cranelift compiler at their defaults, which is the advisory's configuration."},
  {"kind": "sink", "file": "src/wasi_python/_call.py", "line": 416, "scope": "metered call", "description": "The store's fuel is the instruction cap the runner promises; per the advisory, fuel spent in a callee that unwinds to a try_table catch can be lost, so the cap and fuel_used (line 511) can under-count."}
 ],
 "evidence": [
  {"file": "context/research/2026-10-18-wasmtime-49-advisories/advisories/GHSA-m63x-6p34-q65x.json", "line": 1, "description": "Advisory: Cranelift drops fuel on try_table catch and call_ref; affects 49.0.0, fixed 49.0.1; only guests with try_table or call_ref are affected; needs consume_fuel."},
  {"file": "src/wasi_python/_engines.py", "line": 122, "description": "cfg.consume_fuel = metered; no wasm_exceptions(False) or other override."},
  {"file": "pyproject.toml", "line": 18, "description": "dependencies = [\"wasmtime>=49,<50\"]."},
  {"file": "recipes/wasi-numpy.cross", "line": 37, "description": "numpy C++ built with -fwasm-exceptions -fexceptions on the new EH encoding."},
  {"file": "scripts/steps/80_snapshot.sh", "line": 18, "description": "The snapshot is made with -W exceptions=y; its code section has the same try_table count."},
  {"file": "SECURITY.md", "line": 18, "description": "In scope: a guest that runs past its deadline, fuel, memory or output cap."}
 ],
 "blockers": [
  "Not measured: how much fuel one Python-reachable try_table catch path loses under 49.0.0, and whether any compiled-in path nests catches so the loss compounds. I stopped at the binary and configuration preconditions and built no guest program to exercise the defect.",
  "No wasmtime-py at 49.0.1 or later is installed to diff fuel counts against; only the wasmtime CLI 49.0.3 is under build/tools."
 ],
 "validation_plan": {
  "local": "The owner runs a differential fuel count. Take one fixed guest script that triggers a C++ exception caught inside a compiled-in package N times, for small N (1, 10, 100). Read fuel_used from run(..., fuel=<large>, deadline_s=<short>) under wasmtime-py 49.0.0. Run the same module with the same fuel through the pinned wasmtime CLI 49.0.3 (-W fuel=...), or a wasmtime-py on 49.0.1 or later, and compare. If 49.0.0 reports less fuel per N than the fixed engine, the cap under-counts. Keep N and the deadline small.",
  "deployment": "The owner confirms whether PyPI now has a wasmtime-py on wasmtime 49.0.1 or later (or 50.x, see the moving-to-wasmtime-50 memo) and moves the pin's floor past the fix. Until then, document that the fuel cap is advisory on 49.0.0 for code paths that throw and catch, and keep a finite deadline_s beside fuel."
 }
}
result = {
 "units": [{"coverage_id": CID, "disposition": "candidate", "reviewed_paths": paths, "checks": checks,
            "candidate_fingerprints": [FP], "unresolved": []}],
 "candidates": [cand],
 "hardening": [
  "context/research/2026-10-18-wasmtime-49-advisories.md says the module enables no exception proposal and rates GHSA-m63x and GHSA-p79w as not reaching the project. The binaries now carry +exception-handling, 44,791 try_table and 2 tags, so that memo's table is out of date and should be corrected.",
  "GHSA-p79w-pv2r-29qp is avoided only because the tag count happens to be 2 (__cpp_exception and __c_longjmp). A build that adds or imports one more tag would meet the odd-count precondition on 49.0.0 to 49.0.2. Until the pin is at 49.0.3 or later, a release check could assert that the tag count is even.",
  "GHSA-wjc8-633q-pwxr is not reachable: the guest cannot supply modules and the shipped types are 858 plain func types with no rec groups or typed references. A future build that adds GC or typed function references would need this checked again."
 ],
 "uncovered": []
}
s = json.dumps(result, indent=1)
open(sys.argv[1], "w").write(s + "\n")
print(len(s))
