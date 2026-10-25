import json
S = "context/reviews/0.1.0-security-audit-2026-10-25/agents/r04-eh-fuel/scratch"
guest = open(S + "/evidence/kiwi_guest.py").read()
wat = open(S + "/evidence/eh_fuel.wat").read()
host = ("import wasi_python; r = wasi_python.run(['-c', GUEST, N, K, MODE], fuel=FUEL, deadline_s=None); "
        "print(r.exit_code, r.trapped, r.fuel_used, r.stdout)")
rec = {
 "verdict": "confirmed",
 "fingerprint": "wasmtime-49.0.0:GHSA-m63x-6p34-q65x:try_table-catch-fuel:src/wasi_python/_engines.py:_engine",
 "title": "Metered engine on wasmtime-py 49.0.0 drops the fuel of C++ work that ends in a caught exception (GHSA-m63x-6p34-q65x), so guest Python can run far past its fuel cap",
 "description": (
  "The runner meters calls with fuel on a wasmtime-py 49.0.0 engine. Wasm exceptions and Cranelift are left at their defaults. "
  "That is GHSA-m63x-6p34-q65x's affected configuration; the fix is in wasmtime 49.0.1, and no wasmtime-py release carries it yet. "
  "On the exceptional edge of a call inside try_table, 49.0.0 resets fuel to what remained before the call. "
  "So all the work the callee did before throwing is not counted. "
  "The compiled-in C++ packages are built with -fwasm-exceptions, so every C++ catch is such an edge. "
  "Guest Python reaches one directly: kiwisolver's Solver.addConstraint calls the C++ solver inside try/catch, "
  "and the solver throws UnsatisfiableConstraint after building a row whose size grows with the system. "
  "Measured through wasi_python.run with the shipped artifact set (fuel given, deadline_s=None): "
  "one failing addConstraint is counted as about 17,000 to 18,600 fuel whether the chain has 200, 2,000 or 6,000 variables, "
  "while its wall time grows from 9.8 to 190 microseconds. "
  "At 6,000 variables the failing calls are counted at about 90 million fuel per second of wall time; "
  "the pure-Python control in the same guest is counted at 8.9 to 10.6 billion per second, about 100 times more. "
  "A guest given a cap of 2.2e9 fuel ran 20,000 failing calls (1.12 s of loop) and exited 0, reporting 2,017,052,943 fuel used. "
  "The same loop with the no-throw variant of the call ended 'out of fuel' under the same cap. "
  "The engine defect also reproduces with a standalone WAT module: 100 rounds of a 100,000-iteration callee that throws "
  "count as 1,101 fuel on wasmtime-py 49.0.0, but need 80,001,285 under the pinned wasmtime CLI 49.0.3. "
  "A finite deadline_s (the default is 60 s) still bounds wall time through epoch interruption, which the advisory does not affect. "
  "So the cap is lost only where fuel is the bound an embedder relies on: deadline_s=None with fuel, a fuel cap tighter than the deadline, "
  "or fuel_used read as an instruction count."),
 "root_cause": (
  "pyproject.toml pins wasmtime>=49,<50 and uv.lock resolves it to 49.0.0, whose Cranelift fuel accounting resets to the pre-call fuel "
  "on the exceptional edge of a call inside try_table. _engine sets consume_fuel on the metered engine and leaves wasm exceptions enabled. "
  "The build compiles C++ with -fwasm-exceptions and links python.wasm with it, so every caught C++ exception (and every longjmp under "
  "-wasm-enable-sjlj) takes that edge. The runner carries no mitigation for this advisory, though it carries its own fixes for two later "
  "wasmtime filesystem advisories."),
 "intended_behavior": (
  "A fuel cap bounds the guest's executed instructions, and fuel_used counts them, whatever path the guest's code takes, "
  "including C++ exceptions caught inside a compiled-in package. SECURITY.md lists a guest that runs past its fuel cap as in scope."),
 "trace": [
  {"kind": "entrypoint", "file": "scripts/steps/55_matplotlib.sh", "line": 102, "scope": "kiwisolver _cext build",
   "description": "kiwisolver's seven C++ files are compiled with CXX_EH (line 50: -fwasm-exceptions -mllvm -wasm-use-legacy-eh=false -fexceptions), "
                  "so the extension's catch of kiwi::UnsatisfiableConstraint around solver.addConstraint is a try_table catch. "
                  "recipes/wasi-scipy.cross line 44 and the other cross files set the same flags for the other C++ packages."},
  {"kind": "propagation", "file": "scripts/steps/60_link.sh", "line": 129, "scope": "link",
   "description": "python.wasm is linked with -fwasm-exceptions; the hunter counted 44,791 try_table in 7,905 functions."},
  {"kind": "propagation", "file": "uv.lock", "line": 1049, "scope": "wasmtime pin",
   "description": "wasmtime resolves to 49.0.0 (installed in .venv), inside the advisory's affected range."},
  {"kind": "propagation", "file": "src/wasi_python/_engines.py", "line": 122, "scope": "_engine",
   "description": "cfg.consume_fuel = metered; wasm exceptions and the compiler are left at their defaults."},
  {"kind": "sink", "file": "src/wasi_python/_call.py", "line": 618, "scope": "_drive",
   "description": "store.set_fuel(fuel) sets the instruction cap; fuel_used is read at line 511 through _fuel_used (line 554). "
                  "On 49.0.0 both miss callee work that unwinds to a try_table catch."}
 ],
 "evidence": [
  {"file": "context/research/2026-10-18-wasmtime-49-advisories/advisories/GHSA-m63x-6p34-q65x.json", "line": 1,
   "description": "The advisory: with fuel enabled, the catch path of a call inside try_table can drop the callee's fuel, allowing exponential amplification. Affects 49.0.0; fixed in 49.0.1. Workaround: epoch interruption."},
  {"file": "src/wasi_python/_engines.py", "line": 122, "description": "consume_fuel on the metered engine; no override of wasm exceptions."},
  {"file": "pyproject.toml", "line": 18, "description": "dependencies = [\"wasmtime>=49,<50\"]."},
  {"file": "SECURITY.md", "line": 24, "description": "The runner uses wasmtime-py 49.0.0 and no wasmtime-py release yet carries a later wasmtime; the handled-advisories list does not include GHSA-m63x-6p34-q65x."},
  {"file": "SECURITY.md", "line": 18, "description": "In scope: a guest that runs past its deadline, fuel, memory or output cap."},
  {"file": "scripts/steps/55_matplotlib.sh", "line": 50, "description": "CXX_EH=\"-fwasm-exceptions -mllvm -wasm-use-legacy-eh=false -fexceptions\" for the kiwisolver, matplotlib and contourpy C++ code."}
 ],
 "conditions": [
  {"kind": "third_party_dependency", "description": "wasmtime-py 49.0.0 (wasmtime 49.0.0, Cranelift), the only version the pin admits today."},
  {"kind": "system_configuration", "description": "The embedder passes fuel and relies on it as the bound: deadline_s=None, a fuel cap much tighter than the deadline, or fuel_used used for accounting. With the default 60 s deadline, wall time stays bounded."},
  {"kind": "data_state", "description": "The guest runs code that reaches a caught C++ exception (or longjmp) in a compiled-in package after material work; kiwisolver's unsatisfiable addConstraint is one plain-Python way."}
 ],
 "execution": {
  "attacker_perspective": "An untrusted guest Python program run by an embedder through wasi_python.run with a fuel cap and deadline_s=None.",
  "payloads": [guest, host, wat],
  "instructions": [
   "Confirm build/lane.lock is absent and build/artifacts holds the shipped set (MANIFEST lists kiwisolver 1.5.1); confirm .venv has wasmtime 49.0.0.",
   "Write the first payload to a guest file; from a host script under the brief's sandbox wrapper (network denied, HOME, TMPDIR and a mode-0700 WASI_PYTHON_CACHE under scratch), call wasi_python.run(['-c', guest, N, K, MODE], fuel=FUEL, deadline_s=None) as in the second payload.",
   "Run N:K:MODE = 200:0:none, 200:500:fail, 2000:0:none, 2000:500:fail, 6000:0:none, 6000:500:fail, 2000:500:py, 6000:500:py with fuel=10**13; per-call fuel of a mode is (fuel_used - fuel_used of N:0:none) / K; compare with the loop_s the guest prints.",
   "Run 2000:20000:fail and 2000:20000:weak with fuel=2200000000.",
   "Engine-level control: run the third payload (WAT) on wasmtime-py 49.0.0 with consume_fuel, calling 'thrown' and 'returned' with r=100, n=100000, and under the pinned wasmtime CLI 49.0.3 with -W fuel=N,exceptions=y, bisecting the smallest N that completes."
  ],
  "observed_result": (
   "Failing addConstraint, fuel per call / wall per call: N=200 18,619 / 9.8 us; N=2000 18,112 / 59 us; N=6000 17,162 / 190 us. "
   "Setup fuel (N:0:none): 79,798,429; 1,633,156,729; 15,272,412,226. "
   "Pure-Python control: 6,050,026,811 fuel in 0.5724 s (N=2000) and 35,211,663,305 in 3.9596 s (N=6000), 8.9 to 10.6e9 fuel/s; "
   "failing calls at N=6000: 8,581,128 fuel in 0.0952 s, 9.0e7 fuel/s. "
   "Cap 2.2e9: 2000:20000:fail exited 0, trapped None, fuel_used 2,017,052,943, loop 1.1182 s, 20,000 caught; 2000:20000:weak trapped 'out of fuel'. "
   "WAT: on wasmtime-py 49.0.0 'thrown' r=100 n=100000 used 1,101 fuel and 'returned' 80,001,201; the CLI 49.0.3 needed 80,001,285 for 'thrown'.")
 },
 "remediation": {
  "strategy": (
   "Raise the wasmtime floor to a wasmtime-py carrying wasmtime 49.0.1 or later (or move to 50.x) as soon as one is published. "
   "Until then, do not let fuel stand alone as the bound: when fuel is given on 49.0.0, require a finite deadline_s (refuse or warn on deadline_s=None), "
   "since epoch interruption is the advisory's workaround and is unaffected. "
   "List GHSA-m63x-6p34-q65x in SECURITY.md as unmitigated, and say that on 49.0.0 fuel and fuel_used under-count work that ends in a caught C++ exception or longjmp. "
   "Disabling wasm exceptions is not an option, because the build depends on them. "
   "Add a check that runs the kiwisolver loop above and asserts per-call fuel grows with N, so the defect cannot return unseen.")
 },
 "severity": {
  "likelihood": {"score": "low", "reason": "Needs an embedder that relies on fuel as the bound (deadline_s=None, or a cap far below the deadline, or fuel_used for accounting); the default 60 s deadline bounds wall time. The guest side is easy: plain Python reaching a caught C++ exception."},
  "impact": {"score": "medium", "reason": "The documented fuel limit does not bound CPU: about 100x under-count at N=6000, growing with N, and a 2.2e9 cap let a loop run that the no-throw variant could not. Impact is CPU denial of service and wrong instruction accounting; no sandbox escape."},
  "overall_severity": "low"
 },
 "confidence": {"score": "high", "reason": "Reproduced locally through wasi_python.run on the shipped artifacts: per-call fuel stays flat across a 30x range of N while wall time grows 19x, the cap test diverges from the no-throw control, and the engine defect matches the advisory in a standalone differential against the fixed CLI. Not run on a fixed wasmtime-py (none exists), so the true per-call cost is inferred from wall time."}
}
reason = ("Material: promotes needs_validation to confirmed. The first blocker is answerable locally and is now answered: guest Python reaches a "
          "try_table catch with material, N-proportional callee work through kiwisolver's unsatisfiable addConstraint, measured through "
          "wasi_python.run on the shipped artifacts (flat ~17-18.6k fuel per call over N=200..6000 while wall per call grows 9.8->190 us; a 2.2e9 cap "
          "lets 20,000 failing calls finish while the no-throw control runs out of fuel). The second blocker is not decisive (wall-time "
          "calibration and the no-throw control stand in for a fixed engine). Also corrects the earlier evidence note: eh_fuel.wat was not promoted "
          "and is neither embedded in nor reconstructible from eh_fuel_py.py or eh_fuel_cli.py (both read it from argv); its text is now carried in "
          "execution.payloads. Adds trace/evidence for scripts/steps/55_matplotlib.sh lines 50 and 102 and SECURITY.md line 24. Fresh evidence: "
          "r04-eh-fuel/scratch/evidence/kiwi_guest.py, kiwi_host.py, eh_fuel.wat.")
out = {"decision": "replace", "reason": reason, "record": rec}
s = json.dumps(out, ensure_ascii=False)
open(S + "/result.json", "w").write(s)
print(len(s))
