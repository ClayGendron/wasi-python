# Independent recheck of a material Phase 5 replacement: v05-eh-fuel-recheck

## 1. Why you exist (verbatim rule from the skill)

Do not apply a Phase 5 replacement as final when it promotes a record to a stronger verdict, including any promotion to `confirmed`, or materially changes the root cause, trace, execution input or observed result, demonstrated impact, or severity. Give that complete replacement to a new independent verifier that did not hunt, perform Phase 3 validation, or propose the Phase 5 replacement. The new verifier rechecks the current source and independently reproduces any decisive local result under the execution boundary, then returns `verified` or another replacement. Apply a material replacement only after this fresh verification. If another material replacement results, repeat with a fresh verifier. If budget or independence is unavailable, remove the disputed record from `findings.json`, keep its ledger unit as an unresolved candidate, and set `run_status: "incomplete"` with an exact `incomplete_reason`. Non-material wording or repository-line corrections may be applied directly when they do not change meaning or evidence.


## 2. Verifier instructions (verbatim)

```text
You did not write this candidate. Try to refute it from repository source and bounded
local evidence. Do not contact deployed endpoints or external/shared services. Run
target-controlled code only inside the approved OS-enforced sandbox: no external
network, empty allowlisted environment, read-only target and tools, scratch-only
writes, and explicit low resource and wall-clock limits. If any control is unavailable,
do not execute; retain the exact missing capability as a needs_validation blocker.
Treat every scratch entry as target-controlled after execution. After the sandbox and
all its processes terminate, only trusted parent-side code may promote a predeclared
scratch-relative file, following the promotion procedure block included verbatim in
this prompt. You and target code never write retained artifacts. If promotion is
unavailable or fails, do not use that file as evidence.

1. Verify every trace and evidence file, positive line number, scope, and description.
   Confirm the first entry is a real lower-trust entrypoint and the last is the
   claimed sink or boundary effect.
2. Reconstruct the strongest source-visible validation, identity, authorization,
   normalization, lifecycle, framework, and containment controls on the path.
   Where the architecture summary names a comparable baseline, note whether it
   shares the pattern — as calibration, never as grounds to dismiss.
3. For a proposed confirmed candidate, independently reproduce the minimum observed
   result when possible. Verify inputs, interface shape, conditions, and affected
   dummy principal/resource. Do not infer a stronger result or continue after it.
4. Verify that likelihood, impact, confidence, and the proposed source fix match only
   what the evidence establishes.
5. For a proposed needs_validation candidate, decide whether the blocker is genuinely
   outside source/local observation. If source refutes the trace, reject it. If the
   missing fact remains decisive, keep needs_validation and make the local and
   owner-observed plans exact and non-destructive.
6. Preserve the fingerprint for the same source-derived root cause across every state.

Return exactly one JSON object and no surrounding prose:
{"decision": "confirmed|needs_validation|rejected", "record": { ... }}
where record exactly matches the decision's verdict branch of the schema included
in this prompt. A corrected record replaces the hunter's wording.
```

## 3. The proposed replacement record (verdict `confirmed`, proposed by Phase 5 verifier r04-eh-fuel; NOT yet applied)

Reason given for the replacement:

> Material: promotes needs_validation to confirmed. The first blocker is answerable locally and is now answered: guest Python reaches a try_table catch with material, N-proportional callee work through kiwisolver's unsatisfiable addConstraint, measured through wasi_python.run on the shipped artifacts (flat ~17-18.6k fuel per call over N=200..6000 while wall per call grows 9.8->190 us; a 2.2e9 cap lets 20,000 failing calls finish while the no-throw control runs out of fuel). The second blocker is not decisive (wall-time calibration and the no-throw control stand in for a fixed engine). Also corrects the earlier evidence note: eh_fuel.wat was not promoted and is neither embedded in nor reconstructible from eh_fuel_py.py or eh_fuel_cli.py (both read it from argv); its text is now carried in execution.payloads. Adds trace/evidence for scripts/steps/55_matplotlib.sh lines 50 and 102 and SECURITY.md line 24. Fresh evidence: r04-eh-fuel/scratch/evidence/kiwi_guest.py, kiwi_host.py, eh_fuel.wat.

```json
{
  "verdict": "confirmed",
  "fingerprint": "wasmtime-49.0.0:GHSA-m63x-6p34-q65x:try_table-catch-fuel:src/wasi_python/_engines.py:_engine",
  "title": "Metered engine on wasmtime-py 49.0.0 drops the fuel of C++ work that ends in a caught exception (GHSA-m63x-6p34-q65x), so guest Python can run far past its fuel cap",
  "description": "The runner meters calls with fuel on a wasmtime-py 49.0.0 engine. Wasm exceptions and Cranelift are left at their defaults. That is GHSA-m63x-6p34-q65x's affected configuration; the fix is in wasmtime 49.0.1, and no wasmtime-py release carries it yet. On the exceptional edge of a call inside try_table, 49.0.0 resets fuel to what remained before the call. So all the work the callee did before throwing is not counted. The compiled-in C++ packages are built with -fwasm-exceptions, so every C++ catch is such an edge. Guest Python reaches one directly: kiwisolver's Solver.addConstraint calls the C++ solver inside try/catch, and the solver throws UnsatisfiableConstraint after building a row whose size grows with the system. Measured through wasi_python.run with the shipped artifact set (fuel given, deadline_s=None): one failing addConstraint is counted as about 17,000 to 18,600 fuel whether the chain has 200, 2,000 or 6,000 variables, while its wall time grows from 9.8 to 190 microseconds. At 6,000 variables the failing calls are counted at about 90 million fuel per second of wall time; the pure-Python control in the same guest is counted at 8.9 to 10.6 billion per second, about 100 times more. A guest given a cap of 2.2e9 fuel ran 20,000 failing calls (1.12 s of loop) and exited 0, reporting 2,017,052,943 fuel used. The same loop with the no-throw variant of the call ended 'out of fuel' under the same cap. The engine defect also reproduces with a standalone WAT module: 100 rounds of a 100,000-iteration callee that throws count as 1,101 fuel on wasmtime-py 49.0.0, but need 80,001,285 under the pinned wasmtime CLI 49.0.3. A finite deadline_s (the default is 60 s) still bounds wall time through epoch interruption, which the advisory does not affect. So the cap is lost only where fuel is the bound an embedder relies on: deadline_s=None with fuel, a fuel cap tighter than the deadline, or fuel_used read as an instruction count.",
  "root_cause": "pyproject.toml pins wasmtime>=49,<50 and uv.lock resolves it to 49.0.0, whose Cranelift fuel accounting resets to the pre-call fuel on the exceptional edge of a call inside try_table. _engine sets consume_fuel on the metered engine and leaves wasm exceptions enabled. The build compiles C++ with -fwasm-exceptions and links python.wasm with it, so every caught C++ exception (and every longjmp under -wasm-enable-sjlj) takes that edge. The runner carries no mitigation for this advisory, though it carries its own fixes for two later wasmtime filesystem advisories.",
  "intended_behavior": "A fuel cap bounds the guest's executed instructions, and fuel_used counts them, whatever path the guest's code takes, including C++ exceptions caught inside a compiled-in package. SECURITY.md lists a guest that runs past its fuel cap as in scope.",
  "trace": [
    {
      "kind": "entrypoint",
      "file": "scripts/steps/55_matplotlib.sh",
      "line": 102,
      "scope": "kiwisolver _cext build",
      "description": "kiwisolver's seven C++ files are compiled with CXX_EH (line 50: -fwasm-exceptions -mllvm -wasm-use-legacy-eh=false -fexceptions), so the extension's catch of kiwi::UnsatisfiableConstraint around solver.addConstraint is a try_table catch. recipes/wasi-scipy.cross line 44 and the other cross files set the same flags for the other C++ packages."
    },
    {
      "kind": "propagation",
      "file": "scripts/steps/60_link.sh",
      "line": 129,
      "scope": "link",
      "description": "python.wasm is linked with -fwasm-exceptions; the hunter counted 44,791 try_table in 7,905 functions."
    },
    {
      "kind": "propagation",
      "file": "uv.lock",
      "line": 1049,
      "scope": "wasmtime pin",
      "description": "wasmtime resolves to 49.0.0 (installed in .venv), inside the advisory's affected range."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_engines.py",
      "line": 122,
      "scope": "_engine",
      "description": "cfg.consume_fuel = metered; wasm exceptions and the compiler are left at their defaults."
    },
    {
      "kind": "sink",
      "file": "src/wasi_python/_call.py",
      "line": 618,
      "scope": "_drive",
      "description": "store.set_fuel(fuel) sets the instruction cap; fuel_used is read at line 511 through _fuel_used (line 554). On 49.0.0 both miss callee work that unwinds to a try_table catch."
    }
  ],
  "evidence": [
    {
      "file": "context/research/2026-10-18-wasmtime-49-advisories/advisories/GHSA-m63x-6p34-q65x.json",
      "line": 1,
      "description": "The advisory: with fuel enabled, the catch path of a call inside try_table can drop the callee's fuel, allowing exponential amplification. Affects 49.0.0; fixed in 49.0.1. Workaround: epoch interruption."
    },
    {
      "file": "src/wasi_python/_engines.py",
      "line": 122,
      "description": "consume_fuel on the metered engine; no override of wasm exceptions."
    },
    {
      "file": "pyproject.toml",
      "line": 18,
      "description": "dependencies = [\"wasmtime>=49,<50\"]."
    },
    {
      "file": "SECURITY.md",
      "line": 24,
      "description": "The runner uses wasmtime-py 49.0.0 and no wasmtime-py release yet carries a later wasmtime; the handled-advisories list does not include GHSA-m63x-6p34-q65x."
    },
    {
      "file": "SECURITY.md",
      "line": 18,
      "description": "In scope: a guest that runs past its deadline, fuel, memory or output cap."
    },
    {
      "file": "scripts/steps/55_matplotlib.sh",
      "line": 50,
      "description": "CXX_EH=\"-fwasm-exceptions -mllvm -wasm-use-legacy-eh=false -fexceptions\" for the kiwisolver, matplotlib and contourpy C++ code."
    }
  ],
  "conditions": [
    {
      "kind": "third_party_dependency",
      "description": "wasmtime-py 49.0.0 (wasmtime 49.0.0, Cranelift), the only version the pin admits today."
    },
    {
      "kind": "system_configuration",
      "description": "The embedder passes fuel and relies on it as the bound: deadline_s=None, a fuel cap much tighter than the deadline, or fuel_used used for accounting. With the default 60 s deadline, wall time stays bounded."
    },
    {
      "kind": "data_state",
      "description": "The guest runs code that reaches a caught C++ exception (or longjmp) in a compiled-in package after material work; kiwisolver's unsatisfiable addConstraint is one plain-Python way."
    }
  ],
  "execution": {
    "attacker_perspective": "An untrusted guest Python program run by an embedder through wasi_python.run with a fuel cap and deadline_s=None.",
    "payloads": [
      "# Guest program: a chain of N required equalities, then K calls in one mode.\n#   fail: a required equality that conflicts; kiwi's C++ throws UnsatisfiableConstraint,\n#         which the extension catches in C++ and turns into a Python exception.\n#   weak: the same conflicting equality at weak strength, added and removed (no throw).\n#   py:   pure-Python control, sum(range(20N)) per iteration.\n#   none: no calls (baseline for setup cost).\nimport sys, time, kiwisolver as k\nN, K, mode = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]\ns = k.Solver()\nxs = [k.Variable(\"x%d\" % i) for i in range(N + 1)]\ns.addConstraint(xs[0] == 0)\nfor i in range(N):\n    s.addConstraint(xs[i + 1] == xs[i] + 1)\nt = time.perf_counter()\ncaught = 0\nfor j in range(K):\n    if mode == \"fail\":\n        try:\n            s.addConstraint(xs[N] == -1 - j)\n        except k.UnsatisfiableConstraint:\n            caught += 1\n    elif mode == \"weak\":\n        c = (xs[N] == -1 - j) | \"weak\"\n        s.addConstraint(c)\n        s.removeConstraint(c)\n    elif mode == \"py\":\n        sum(range(N * 20))\nprint(\"loop_s=%.4f caught=%d\" % (time.perf_counter() - t, caught))\n",
      "import wasi_python; r = wasi_python.run(['-c', GUEST, N, K, MODE], fuel=FUEL, deadline_s=None); print(r.exit_code, r.trapped, r.fuel_used, r.stdout)",
      "(module\n  (tag $t)\n  ;; burn: count n down to zero, then throw (or return)\n  (func $burn_throw (param $n i32)\n    (loop $l\n      (local.set $n (i32.sub (local.get $n) (i32.const 1)))\n      (br_if $l (i32.gt_s (local.get $n) (i32.const 0))))\n    (throw $t))\n  (func $burn_ret (param $n i32)\n    (loop $l\n      (local.set $n (i32.sub (local.get $n) (i32.const 1)))\n      (br_if $l (i32.gt_s (local.get $n) (i32.const 0)))))\n  ;; r rounds of: try_table { call callee(n) } catch $t\n  (func (export \"thrown\") (param $r i32) (param $n i32)\n    (loop $outer\n      (block $h\n        (try_table (catch $t $h)\n          (call $burn_throw (local.get $n))))\n      (local.set $r (i32.sub (local.get $r) (i32.const 1)))\n      (br_if $outer (i32.gt_s (local.get $r) (i32.const 0)))))\n  (func (export \"returned\") (param $r i32) (param $n i32)\n    (loop $outer\n      (block $h\n        (try_table (catch $t $h)\n          (call $burn_ret (local.get $n))))\n      (local.set $r (i32.sub (local.get $r) (i32.const 1)))\n      (br_if $outer (i32.gt_s (local.get $r) (i32.const 0)))))\n)\n"
    ],
    "instructions": [
      "Confirm build/lane.lock is absent and build/artifacts holds the shipped set (MANIFEST lists kiwisolver 1.5.1); confirm .venv has wasmtime 49.0.0.",
      "Write the first payload to a guest file; from a host script under the brief's sandbox wrapper (network denied, HOME, TMPDIR and a mode-0700 WASI_PYTHON_CACHE under scratch), call wasi_python.run(['-c', guest, N, K, MODE], fuel=FUEL, deadline_s=None) as in the second payload.",
      "Run N:K:MODE = 200:0:none, 200:500:fail, 2000:0:none, 2000:500:fail, 6000:0:none, 6000:500:fail, 2000:500:py, 6000:500:py with fuel=10**13; per-call fuel of a mode is (fuel_used - fuel_used of N:0:none) / K; compare with the loop_s the guest prints.",
      "Run 2000:20000:fail and 2000:20000:weak with fuel=2200000000.",
      "Engine-level control: run the third payload (WAT) on wasmtime-py 49.0.0 with consume_fuel, calling 'thrown' and 'returned' with r=100, n=100000, and under the pinned wasmtime CLI 49.0.3 with -W fuel=N,exceptions=y, bisecting the smallest N that completes."
    ],
    "observed_result": "Failing addConstraint, fuel per call / wall per call: N=200 18,619 / 9.8 us; N=2000 18,112 / 59 us; N=6000 17,162 / 190 us. Setup fuel (N:0:none): 79,798,429; 1,633,156,729; 15,272,412,226. Pure-Python control: 6,050,026,811 fuel in 0.5724 s (N=2000) and 35,211,663,305 in 3.9596 s (N=6000), 8.9 to 10.6e9 fuel/s; failing calls at N=6000: 8,581,128 fuel in 0.0952 s, 9.0e7 fuel/s. Cap 2.2e9: 2000:20000:fail exited 0, trapped None, fuel_used 2,017,052,943, loop 1.1182 s, 20,000 caught; 2000:20000:weak trapped 'out of fuel'. WAT: on wasmtime-py 49.0.0 'thrown' r=100 n=100000 used 1,101 fuel and 'returned' 80,001,201; the CLI 49.0.3 needed 80,001,285 for 'thrown'."
  },
  "remediation": {
    "strategy": "Raise the wasmtime floor to a wasmtime-py carrying wasmtime 49.0.1 or later (or move to 50.x) as soon as one is published. Until then, do not let fuel stand alone as the bound: when fuel is given on 49.0.0, require a finite deadline_s (refuse or warn on deadline_s=None), since epoch interruption is the advisory's workaround and is unaffected. List GHSA-m63x-6p34-q65x in SECURITY.md as unmitigated, and say that on 49.0.0 fuel and fuel_used under-count work that ends in a caught C++ exception or longjmp. Disabling wasm exceptions is not an option, because the build depends on them. Add a check that runs the kiwisolver loop above and asserts per-call fuel grows with N, so the defect cannot return unseen."
  },
  "severity": {
    "likelihood": {
      "score": "low",
      "reason": "Needs an embedder that relies on fuel as the bound (deadline_s=None, or a cap far below the deadline, or fuel_used for accounting); the default 60 s deadline bounds wall time. The guest side is easy: plain Python reaching a caught C++ exception."
    },
    "impact": {
      "score": "medium",
      "reason": "The documented fuel limit does not bound CPU: about 100x under-count at N=6000, growing with N, and a 2.2e9 cap let a loop run that the no-throw variant could not. Impact is CPU denial of service and wrong instruction accounting; no sandbox escape."
    },
    "overall_severity": "low"
  },
  "confidence": {
    "score": "high",
    "reason": "Reproduced locally through wasi_python.run on the shipped artifacts: per-call fuel stays flat across a 30x range of N while wall time grows 19x, the cap test diverges from the no-throw control, and the engine defect matches the advisory in a standalone differential against the fixed CLI. Not run on a fixed wasmtime-py (none exists), so the true per-call cost is inferred from wall time."
  }
}
```

## 4. The record currently in findings.json that it would replace (verdict `needs_validation`)

```json
{
  "verdict": "needs_validation",
  "fingerprint": "wasmtime-49.0.0:GHSA-m63x-6p34-q65x:try_table-catch-fuel:src/wasi_python/_engines.py:_engine",
  "title": "Metered engine on wasmtime-py 49.0.0 under-counts fuel on try_table catch paths (GHSA-m63x-6p34-q65x); the defect reproduces at engine level, reachability from guest Python is not shown",
  "description": "The runner meters calls with fuel on a wasmtime-py 49.0.0 engine with exceptions and Cranelift at their defaults. That is GHSA-m63x-6p34-q65x's affected configuration (fixed in 49.0.1). A standalone WAT differential confirms the engine defect: on 49.0.0, fuel spent in a callee that throws to a try_table catch in the caller is dropped. 100 rounds of a 100,000-iteration callee count as 1,101 fuel. The same module needs 80,001,285 fuel under the pinned CLI 49.0.3. The return-path control agrees across both engines (800,013 against 799,998 for one round). The shipped python.wasm and snapshot contain 44,791 try_table sites from the -fwasm-exceptions builds of C++ and setjmp/longjmp in the compiled-in packages. Whether a guest Python call reaches one of these catch paths with enough callee work to matter was not measured. A finite deadline_s (the default) still bounds wall-clock time through epoch interruption, which the advisory does not affect. Fuel is the only instruction bound only for an embedder that passes fuel with deadline_s=None.",
  "claimed_root_cause": "pyproject.toml pins wasmtime>=49,<50 and uv.lock resolves it to 49.0.0, whose Cranelift fuel accounting resets to the pre-call fuel on the exceptional edge of a call inside try_table. _engine sets consume_fuel on the metered engine and leaves wasm exceptions enabled. The build puts try_table on every caught C++ exception and longjmp return. The runner carries no mitigation for this advisory, though it does carry its own fixes for the 49.0.2 and 49.0.3 filesystem advisories.",
  "trace": [
    {
      "kind": "entrypoint",
      "file": "recipes/wasi-scipy.cross",
      "line": 44,
      "scope": "C++ build flags",
      "description": "C++ is compiled with -fwasm-exceptions -fexceptions -wasm-use-legacy-eh=false (C with -wasm-enable-sjlj at line 39); numpy, pandas, matplotlib, plot-libs and sklearn cross files do the same, so caught C++ exceptions and longjmp go through try_table catch paths."
    },
    {
      "kind": "propagation",
      "file": "scripts/steps/60_link.sh",
      "line": 129,
      "scope": "link",
      "description": "python.wasm is linked with -fwasm-exceptions; the hunter counted 44,791 try_table in 7,905 functions and 0 call_ref."
    },
    {
      "kind": "propagation",
      "file": "uv.lock",
      "line": 1049,
      "scope": "wasmtime pin",
      "description": "wasmtime resolves to 49.0.0, inside the advisory's affected range."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_engines.py",
      "line": 122,
      "scope": "_engine",
      "description": "cfg.consume_fuel = metered; exceptions and the compiler are left at their defaults."
    },
    {
      "kind": "sink",
      "file": "src/wasi_python/_call.py",
      "line": 618,
      "scope": "_drive",
      "description": "store.set_fuel(fuel) sets the instruction cap. Fuel_used is read at line 511 through _fuel_used (line 554). On 49.0.0 both can under-count callee work that unwinds to a try_table catch."
    }
  ],
  "evidence": [
    {
      "file": "context/research/2026-10-18-wasmtime-49-advisories/advisories/GHSA-m63x-6p34-q65x.json",
      "line": 1,
      "description": "The advisory: with fuel enabled, the catch path of a call inside try_table can drop the callee's fuel. Affects 49.0.0; fixed in 49.0.1. Workaround: epoch interruption."
    },
    {
      "file": "src/wasi_python/_engines.py",
      "line": 122,
      "description": "consume_fuel on the metered engine; no wasm_exceptions(False) override."
    },
    {
      "file": "pyproject.toml",
      "line": 18,
      "description": "dependencies = [\"wasmtime>=49,<50\"]."
    },
    {
      "file": "src/wasi_python/_call.py",
      "line": 618,
      "description": "The guest's fuel cap is set after instantiation; line 416 sets the UNMETERED budget that instantiation runs on."
    },
    {
      "file": "SECURITY.md",
      "line": 18,
      "description": "In scope: a guest that runs past its fuel cap. The out-of-scope section excludes upstream bugs that do not cross the sandbox boundary, so the owner must decide which applies."
    }
  ],
  "blockers": [
    "Not shown: a guest Python call that throws and catches a C++ exception (or longjmps) inside a compiled-in package, with callee work large enough that the dropped fuel matters. The engine defect is confirmed only with a standalone WAT module, not through python.wasm.",
    "No wasmtime-py at 49.0.1 or later is installed locally, so a same-module comparison through wasi_python.run on a fixed engine is not available. The CLI 49.0.3 comparison used the standalone module only.",
    "The target was not mounted read-only, and no memory rlimit could be enforced on this platform."
  ],
  "validation_plan": {
    "local": "Verifier evidence: scratch/evidence/eh_fuel.wat, eh_fuel_py.py (wasmtime-py 49.0.0: 'thrown' r=100 n=100000 uses 1,101 fuel; 'returned' uses 80,001,201) and eh_fuel_cli.py (CLI 49.0.3 -W fuel=N,exceptions=y: 'thrown' r=100 n=100000 needs 80,001,285). The owner should run the project's own fuel tests on wasmtime-py 49.0.1 or later once it exists, and compare fuel_used for a package call known to catch a C++ exception internally.",
    "deployment": "Raise the pin's floor to a wasmtime-py carrying wasmtime 49.0.1 or later, or move to 50.x. Until then, add GHSA-m63x-6p34-q65x to SECURITY.md's handled-advisories list as unmitigated. State that fuel is not a reliable bound on 49.0.0, and keep or require a finite deadline_s beside fuel."
  }
}
```

## 5. Evidence you may read (read-only)

- Proposer's: `context/reviews/0.1.0-security-audit-2026-10-25/agents/r04-eh-fuel/artifacts/evidence/` (kiwi_guest.py, kiwi_host.py; its .wat was not promoted, the WAT text is in the record's payloads)
- Phase 3 verifier's: `context/reviews/0.1.0-security-audit-2026-10-25/agents/v04-eh-fuel/artifacts/evidence/` (eh_fuel_py.py, eh_fuel_cli.py)
- Hunter's: `context/reviews/0.1.0-security-audit-2026-10-25/agents/h17-eh-advisories/artifacts/evidence/` (opcode and section counts)

## 6. Execution boundary and paths

- Target root: `.`. Never edit a file under it; never run `uv sync`, plain `uv run`, the download or build scripts, `release/set_key.py`, `gh workflow run`, `git push`, `pytest --accept*`, or anything writing under `context/`. Never download from the internet.
- Your scratch (only place you write): `context/reviews/0.1.0-security-audit-2026-10-25/agents/v05-eh-fuel-recheck/scratch/`; put evidence files you want retained directly under `scratch/evidence/` named `*.txt|*.json|*.log|*.py` (max 24 files, 512 KiB each). Wrap every target-controlled run as: `ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME=context/reviews/0.1.0-security-audit-2026-10-25/agents/v05-eh-fuel-recheck/scratch/home TMPDIR=context/reviews/0.1.0-security-audit-2026-10-25/agents/v05-eh-fuel-recheck/scratch/tmp WASI_PYTHON_CACHE=context/reviews/0.1.0-security-audit-2026-10-25/agents/v05-eh-fuel-recheck/scratch/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' ./.venv/bin/python -I <script under scratch>` with a `subprocess.run(timeout=...)` bound; make the three folders first (the cache folder mode 0700); confirm `./build/lane.lock` is absent; never point a writable grant or root at the target or a real cache; this platform cannot read-only mount the target or enforce a memory rlimit. The pinned wasmtime CLI is at `./build/tools/wasmtime-v49.0.3-aarch64-macos/wasmtime`.
- Keep runs short: small N and K first; the proposer's largest case (N=6000) took a few seconds of guest time.

## 7. Result contract

Return exactly one JSON object and no prose: `{"decision":"verified","fingerprint":"wasmtime-49.0.0:GHSA-m63x-6p34-q65x:try_table-catch-fuel:src/wasi_python/_engines.py:_engine"}` to accept the replacement as written, or `{"decision":"replace","reason":"...","record":{...}}` with a corrected record matching its schema branch exactly (`additionalProperties: false`; `verdict` set accordingly: `confirmed`, `needs_validation` or `rejected`). Also write it to `context/reviews/0.1.0-security-audit-2026-10-25/agents/v05-eh-fuel-recheck/scratch/result.json`.

### confirmed branch (verbatim)
```json
{
  "type": "object",
  "description": "A source-grounded vulnerability that was independently demonstrated.",
  "properties": {
    "verdict": {
      "type": "string",
      "const": "confirmed"
    },
    "fingerprint": {
      "type": "string",
      "minLength": 1,
      "pattern": "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$",
      "description": "A stable source-derived identifier that does not change between validation states."
    },
    "title": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "description": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "root_cause": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "intended_behavior": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "trace": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "object",
        "properties": {
          "kind": {
            "type": "string",
            "enum": [
              "entrypoint",
              "propagation",
              "sink"
            ]
          },
          "file": {
            "type": "string",
            "minLength": 1
          },
          "line": {
            "type": "integer",
            "minimum": 1
          },
          "scope": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          },
          "description": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          }
        },
        "required": [
          "kind",
          "file",
          "line",
          "scope",
          "description"
        ],
        "additionalProperties": false
      }
    },
    "evidence": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "object",
        "properties": {
          "file": {
            "type": "string",
            "minLength": 1
          },
          "line": {
            "type": "integer",
            "minimum": 1
          },
          "description": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          }
        },
        "required": [
          "file",
          "line",
          "description"
        ],
        "additionalProperties": false
      }
    },
    "conditions": {
      "type": "array",
      "uniqueItems": true,
      "items": {
        "type": "object",
        "properties": {
          "kind": {
            "type": "string",
            "enum": [
              "authentication_level",
              "authorization_role",
              "user_interaction",
              "system_configuration",
              "network_routing",
              "environmental_dependency",
              "data_state",
              "timing_dependency",
              "third_party_dependency"
            ]
          },
          "description": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          }
        },
        "required": [
          "kind",
          "description"
        ],
        "additionalProperties": false
      }
    },
    "execution": {
      "type": "object",
      "description": "Target-neutral reproduction in the target's native interface.",
      "properties": {
        "attacker_perspective": {
          "type": "string",
          "minLength": 1,
          "visibleContent": true
        },
        "payloads": {
          "type": "array",
          "minItems": 1,
          "uniqueItems": true,
          "items": {
            "type": "string"
          }
        },
        "instructions": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          }
        },
        "observed_result": {
          "type": "string",
          "minLength": 1,
          "visibleContent": true
        }
      },
      "required": [
        "attacker_perspective",
        "payloads",
        "instructions",
        "observed_result"
      ],
      "additionalProperties": false
    },
    "remediation": {
      "type": "object",
      "properties": {
        "strategy": {
          "type": "string",
          "minLength": 1,
          "visibleContent": true
        },
        "code_changes": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "file_name": {
                "type": "string",
                "minLength": 1
              },
              "fixed_code": {
                "type": "string"
              }
            },
            "required": [
              "file_name",
              "fixed_code"
            ],
            "additionalProperties": false
          }
        }
      },
      "required": [
        "strategy"
      ],
      "additionalProperties": false
    },
    "severity": {
      "type": "object",
      "properties": {
        "likelihood": {
          "type": "object",
          "properties": {
            "score": {
              "type": "string",
              "enum": [
                "informational",
                "low",
                "medium",
                "high",
                "critical"
              ]
            },
            "reason": {
              "type": "string",
              "minLength": 1,
              "visibleContent": true
            }
          },
          "required": [
            "score",
            "reason"
          ],
          "additionalProperties": false
        },
        "impact": {
          "type": "object",
          "properties": {
            "score": {
              "type": "string",
              "enum": [
                "informational",
                "low",
                "medium",
                "high",
                "critical"
              ]
            },
            "reason": {
              "type": "string",
              "minLength": 1,
              "visibleContent": true
            }
          },
          "required": [
            "score",
            "reason"
          ],
          "additionalProperties": false
        },
        "overall_severity": {
          "type": "string",
          "enum": [
            "informational",
            "low",
            "medium",
            "high",
            "critical"
          ]
        }
      },
      "required": [
        "likelihood",
        "impact",
        "overall_severity"
      ],
      "additionalProperties": false
    },
    "confidence": {
      "type": "object",
      "properties": {
        "score": {
          "type": "string",
          "enum": [
            "low",
            "medium",
            "high"
          ]
        },
        "reason": {
          "type": "string",
          "minLength": 1,
          "visibleContent": true
        }
      },
      "required": [
        "score",
        "reason"
      ],
      "additionalProperties": false
    }
  },
  "required": [
    "verdict",
    "fingerprint",
    "title",
    "description",
    "root_cause",
    "intended_behavior",
    "trace",
    "evidence",
    "conditions",
    "execution",
    "remediation",
    "severity",
    "confidence"
  ],
  "additionalProperties": false
}
```
### needs_validation branch (verbatim)
```json
{
  "type": "object",
  "description": "A source-grounded candidate whose decisive validation is blocked.",
  "properties": {
    "verdict": {
      "type": "string",
      "const": "needs_validation"
    },
    "fingerprint": {
      "type": "string",
      "minLength": 1,
      "pattern": "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
    },
    "title": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "description": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "claimed_root_cause": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "trace": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "object",
        "properties": {
          "kind": {
            "type": "string",
            "enum": [
              "entrypoint",
              "propagation",
              "sink"
            ]
          },
          "file": {
            "type": "string",
            "minLength": 1
          },
          "line": {
            "type": "integer",
            "minimum": 1
          },
          "scope": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          },
          "description": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          }
        },
        "required": [
          "kind",
          "file",
          "line",
          "scope",
          "description"
        ],
        "additionalProperties": false
      }
    },
    "evidence": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "object",
        "properties": {
          "file": {
            "type": "string",
            "minLength": 1
          },
          "line": {
            "type": "integer",
            "minimum": 1
          },
          "description": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          }
        },
        "required": [
          "file",
          "line",
          "description"
        ],
        "additionalProperties": false
      }
    },
    "blockers": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "string",
        "minLength": 1,
        "visibleContent": true
      }
    },
    "validation_plan": {
      "type": "object",
      "properties": {
        "local": {
          "type": "string",
          "minLength": 1,
          "visibleContent": true
        },
        "deployment": {
          "type": "string",
          "minLength": 1,
          "visibleContent": true
        }
      },
      "additionalProperties": false
    }
  },
  "required": [
    "verdict",
    "fingerprint",
    "title",
    "description",
    "claimed_root_cause",
    "trace",
    "evidence",
    "blockers",
    "validation_plan"
  ],
  "additionalProperties": false
}
```
### rejected branch (verbatim)
```json
{
  "type": "object",
  "description": "A source-grounded candidate refuted during validation.",
  "properties": {
    "verdict": {
      "type": "string",
      "const": "rejected"
    },
    "fingerprint": {
      "type": "string",
      "minLength": 1,
      "pattern": "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
    },
    "title": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "description": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "claimed_root_cause": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    },
    "trace": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "object",
        "properties": {
          "kind": {
            "type": "string",
            "enum": [
              "entrypoint",
              "propagation",
              "sink"
            ]
          },
          "file": {
            "type": "string",
            "minLength": 1
          },
          "line": {
            "type": "integer",
            "minimum": 1
          },
          "scope": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          },
          "description": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          }
        },
        "required": [
          "kind",
          "file",
          "line",
          "scope",
          "description"
        ],
        "additionalProperties": false
      }
    },
    "evidence": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "object",
        "properties": {
          "file": {
            "type": "string",
            "minLength": 1
          },
          "line": {
            "type": "integer",
            "minimum": 1
          },
          "description": {
            "type": "string",
            "minLength": 1,
            "visibleContent": true
          }
        },
        "required": [
          "file",
          "line",
          "description"
        ],
        "additionalProperties": false
      }
    },
    "reason": {
      "type": "string",
      "minLength": 1,
      "visibleContent": true
    }
  },
  "required": [
    "verdict",
    "fingerprint",
    "title",
    "description",
    "claimed_root_cause",
    "trace",
    "evidence",
    "reason"
  ],
  "additionalProperties": false
}
```
