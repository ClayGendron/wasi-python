# Phase 5 record-verifier brief: r05-eh-fuel-final

## 1. Instructions (verbatim from the skill)

### Phase 5: Verify the final records with fresh eyes

Launch one fresh `research` verifier per final `confirmed` and `needs_validation` record, in parallel. This verifier checks the structured record, not the hunter write-up, and remains inside source/local boundaries.

In a `quick` run, Phase 3 and Phase 5 merge: the Phase 3 verifier also performs these record checks and returns the final schema-shaped record, so each candidate gets one fresh independent reviewer instead of two. Every other profile keeps the two passes separate. Never skip independent review of a `confirmed` record in any profile.

For `confirmed`, require it to check:

1. Every repository-relative trace/evidence path, line, scope, and described operation.
2. Real entry interface and exact local input shape.
3. Every condition, parser/policy step, source-visible preventing layer, and observed local result.
4. Affected principal/resource and demonstrated impact.
5. Severity separation: realistic likelihood, demonstrated impact, overall no greater than impact.
6. Remediation strategy and any `code_changes`, including whether the fix enforces the invariant without merely moving trust.

For `needs_validation`, require it to check:

1. The source path is real and supports only the `claimed_root_cause` stated.
2. Every listed blocker is decisive and not already answerable locally.
3. The candidate names a boundary and a possible concrete result rather than a generic concern.
4. At least one validation-plan field is present and exact. `local` uses a bounded fixture; `deployment` asks an owner to observe a configuration, identity, route, policy, or runtime fact. Do not invent a plan for an inapplicable context, and never send audit traffic to a deployment.
5. The fingerprint matches prior/current records for the same root cause.

Each verifier returns exactly one JSON object: `{"decision":"verified","fingerprint":"..."}` or `{"decision":"replace","reason":"...","record":{...}}`, with no surrounding prose. A replacement record must match its `confirmed`, `needs_validation`, or `rejected` schema branch. Treat a malformed or prose-wrapped Phase 5 result the same way as in Phase 3: discard it without repairing it and re-run with a fresh verifier when the budget permits.

Do not apply a Phase 5 replacement as final when it promotes a record to a stronger verdict, including any promotion to `confirmed`, or materially changes the root cause, trace, execution input or observed result, demonstrated impact, or severity. Give that complete replacement to a new independent verifier that did not hunt, perform Phase 3 validation, or propose the Phase 5 replacement. The new verifier rechecks the current source and independently reproduces any decisive local result under the execution boundary, then returns `verified` or another replacement. Apply a material replacement only after this fresh verification. If another material replacement results, repeat with a fresh verifier. If budget or independence is unavailable, remove the disputed record from `findings.json`, keep its ledger unit as an unresolved candidate, and set `run_status: "incomplete"` with an exact `incomplete_reason`. Non-material wording or repository-line corrections may be applied directly when they do not change meaning or evidence.

After every applied replacement, rerun both validators and update linked ledger decisions. If a final verifier identifies a separate root cause, assign a new fingerprint and send it through independent candidate validation before inclusion. Set `run_status: "complete"` only when every ledger candidate has an independent final disposition and every retained record passes Phase 5.

Do not verify only `confirmed` records. A misleading `needs_validation` handoff wastes owner time and can preserve a false premise.


## 2. The final record to verify (verdict `confirmed`, decided by Phase 3 verifier `v04-eh-fuel`; you did not hunt or validate it)

```json
{
  "verdict": "confirmed",
  "fingerprint": "wasmtime-49.0.0:GHSA-m63x-6p34-q65x:try_table-catch-fuel:src/wasi_python/_engines.py:_engine",
  "title": "Metered engine on wasmtime-py 49.0.0 drops the fuel of C++ work that ends in a caught exception (GHSA-m63x-6p34-q65x), so guest Python can run far past its fuel cap",
  "description": "The runner meters calls with fuel on a wasmtime-py 49.0.0 engine. Wasm exceptions and Cranelift are left at their defaults. That is GHSA-m63x-6p34-q65x's affected configuration; the fix is in wasmtime 49.0.1, and no wasmtime-py release carries it yet. On the exceptional edge of a call inside try_table, 49.0.0 resets fuel to what remained before the call, so all the work the callee did before throwing is not counted. The compiled-in C++ packages are built with -fwasm-exceptions, so every C++ catch is such an edge. Guest Python reaches one directly: kiwisolver's Solver.addConstraint (py/src/solver.cpp in the pinned 1.5.1 tarball) calls the C++ solver inside try and catches kiwi::UnsatisfiableConstraint, which the solver throws after building a row whose size grows with the system. Measured twice, independently, through wasi_python.run on the shipped artifact set (fuel given, deadline_s=None): one failing addConstraint is counted as about 17,000 to 19,600 fuel whether the chain has 200, 2,000 or 6,000 variables, while its wall time grows from about 9.6 to 190 microseconds. A same-shape control that adds and removes a consistent required equality on the same chain end (no throw) is counted as 140,067 fuel per call at 200 variables, at the same 9.6 microseconds of wall time as the failing call, and 1,552,404 fuel per call at 2,000 variables. The no-throw C++ and pure-Python work in these guests is counted at roughly 9 to 15 billion fuel per second of wall time; the failing calls at 6,000 variables are counted at about 0.9 to 1.0 hundred million per second, so their fuel is under-counted by roughly 100 times, an estimate from wall time since no fixed wasmtime-py exists to count them exactly. Under a cap of 2.2e9 fuel, 20,000 failing calls on a 2,000-variable chain (about 1.2 s of loop) finished with exit 0 and about 2.02e9 fuel used; the same-shape no-throw loop and the weak-strength add/remove loop each ended 'out of fuel' under the same cap, the no-throw one after at most about 364 calls of the 565 million fuel left after setup. The engine defect also reproduces with a standalone WAT module: 100 rounds of a 100,000-iteration callee that throws count as 1,101 fuel on wasmtime-py 49.0.0, but need 80,001,285 under the pinned wasmtime CLI 49.0.3. A finite deadline_s (the default is 60 s) still bounds wall time through epoch interruption, which the advisory does not affect. So the cap is lost only where fuel is the bound an embedder relies on: deadline_s=None with fuel, a fuel cap tighter than the deadline, or fuel_used read as an instruction count. In the guest case observed, the under-count per call grows with the size of the system the guest builds; the advisory's 'exponential' amplification is its own claim for arbitrary wasm and was not shown from guest Python.",
  "root_cause": "pyproject.toml pins wasmtime>=49,<50 and uv.lock resolves it to 49.0.0, whose Cranelift fuel accounting resets to the pre-call fuel on the exceptional edge of a call inside try_table. _engine sets consume_fuel on the metered engine and leaves wasm exceptions enabled. The build compiles C++ with -fwasm-exceptions and links python.wasm with it, so every caught C++ exception (and, by the same lowering, every longjmp under -wasm-enable-sjlj, not separately demonstrated) takes that edge. The runner carries no mitigation for this advisory, though it carries its own fixes for two later wasmtime filesystem advisories.",
  "intended_behavior": "A fuel cap bounds the guest's executed instructions, and fuel_used counts them, whatever path the guest's code takes, including C++ exceptions caught inside a compiled-in package. run()'s docstring calls fuel 'a cap on the guest's executed instructions', and SECURITY.md lists a guest that runs past its fuel cap as in scope.",
  "trace": [
    {
      "kind": "entrypoint",
      "file": "src/wasi_python/runner.py",
      "line": 115,
      "scope": "run",
      "description": "wasi_python.run takes an untrusted guest program (argv) with fuel and deadline_s; deadline_s=None means no wall-clock limit, so fuel is the only CPU bound."
    },
    {
      "kind": "propagation",
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
      "description": "cfg.consume_fuel = metered; wasm exceptions and the compiler are left at their defaults (epoch_interruption is also on, line 123)."
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
      "description": "The advisory: with fuel enabled, the catch path of a call inside try_table can drop the callee's fuel, which it says allows exponential amplification in general. Affects 49.0.0; fixed in 49.0.1. Workaround: epoch interruption."
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
      "file": "src/wasi_python/runner.py",
      "line": 176,
      "description": "run()'s fuel parameter: 'A cap on the guest's executed instructions; past it the call ends \"out of fuel\".'"
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
      "# Guest: N-variable equality chain in kiwisolver, then K calls of one mode; prints loop time.\nimport sys, time\nimport kiwisolver as kw\nn, k, mode = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]\nsolver = kw.Solver()\nv = [kw.Variable(\"v%d\" % i) for i in range(n + 1)]\nsolver.addConstraint(v[0] == 0)\nfor i in range(n):\n    solver.addConstraint(v[i + 1] == v[i] + 1)\ncaught = 0\nt0 = time.perf_counter()\nfor j in range(k):\n    if mode == \"fail\":\n        try:\n            solver.addConstraint(v[n] == -1 - j)\n        except kw.UnsatisfiableConstraint:\n            caught += 1\n    elif mode == \"weak\":\n        c = (v[n] == -1 - j) | \"weak\"\n        solver.addConstraint(c)\n        solver.removeConstraint(c)\n    elif mode == \"ok\":\n        # The same required equality on the chain's end, but consistent with it: no throw.\n        c = v[n] == n\n        solver.addConstraint(c)\n        solver.removeConstraint(c)\n    elif mode == \"py\":\n        sum(range(n * 20))\nprint(\"loop_s=%.4f caught=%d\" % (time.perf_counter() - t0, caught))\n",
      "import wasi_python; r = wasi_python.run(['-c', GUEST, N, K, MODE], fuel=FUEL, deadline_s=None); print(r.exit_code, r.trapped, r.fuel_used, r.stdout)",
      "(module\n  (tag $t)\n  (func $burn_throw (param $n i32)\n    (loop $l\n      (local.set $n (i32.sub (local.get $n) (i32.const 1)))\n      (br_if $l (i32.gt_s (local.get $n) (i32.const 0))))\n    (throw $t))\n  (func $burn_ret (param $n i32)\n    (loop $l\n      (local.set $n (i32.sub (local.get $n) (i32.const 1)))\n      (br_if $l (i32.gt_s (local.get $n) (i32.const 0)))))\n  (func (export \"thrown\") (param $r i32) (param $n i32)\n    (loop $outer\n      (block $h\n        (try_table (catch $t $h)\n          (call $burn_throw (local.get $n))))\n      (local.set $r (i32.sub (local.get $r) (i32.const 1)))\n      (br_if $outer (i32.gt_s (local.get $r) (i32.const 0)))))\n  (func (export \"returned\") (param $r i32) (param $n i32)\n    (loop $outer\n      (block $h\n        (try_table (catch $t $h)\n          (call $burn_ret (local.get $n))))\n      (local.set $r (i32.sub (local.get $r) (i32.const 1)))\n      (br_if $outer (i32.gt_s (local.get $r) (i32.const 0)))))\n)\n"
    ],
    "instructions": [
      "Confirm build/lane.lock is absent and build/artifacts holds the shipped set (MANIFEST lists kiwisolver 1.5.1); confirm .venv has wasmtime 49.0.0.",
      "Write the first payload to a guest file; from a host script under the audit's sandbox wrapper (network denied, empty environment, HOME, TMPDIR and a mode-0700 WASI_PYTHON_CACHE under scratch, CPU and file-size rlimits), call wasi_python.run(['-c', guest, N, K, MODE], fuel=FUEL, deadline_s=None) as in the second payload.",
      "Run N:K:MODE = 200:0:none, 200:500:fail, 200:500:ok, 2000:0:none, 2000:500:fail, 2000:500:ok, 2000:500:py, 6000:0:none, 6000:500:fail, 6000:500:py with fuel=10**13; per-call fuel of a mode is (fuel_used - fuel_used of N:0:none) / K; compare with the loop_s the guest prints.",
      "Run 2000:20000:fail, 2000:20000:ok and 2000:20000:weak with fuel=2200000000.",
      "Engine-level control: run the third payload (WAT) on wasmtime-py 49.0.0 with consume_fuel, calling 'thrown' and 'returned' with r=100, n=100000, and under the pinned wasmtime CLI 49.0.3 with -W fuel=N,exceptions=y --invoke thrown, finding the smallest N that completes."
    ],
    "observed_result": "Proposer's run, failing addConstraint, fuel per call / wall per call: N=200 18,619 / 9.8 us; N=2000 18,112 / 59 us; N=6000 17,162 / 190 us. Independent re-run (fresh guest and host scripts): N=200 18,744 / 9.6 us; N=2000 19,581 / 58 us; N=6000 18,357 / 184 us. Setup fuel (N:0:none): 79,699,507; 1,635,065,251; 15,271,669,312. Same-shape no-throw control (ok): N=200 140,067 / 9.6 us; N=2000 1,552,404 / 127 us. Weak add/remove: N=200 950,942 / 44 us; N=2000 65,972,562 / 2.29 ms. Pure-Python control: 6,049,028,364 fuel in 0.5748 s (N=2000, 1.05e10 fuel/s) and 35,212,385,994 in 3.8875 s (N=6000, 9.1e9 fuel/s); failing calls at N=6000: 9,178,617 fuel in 0.0921 s, 1.0e8 fuel/s. Cap 2.2e9: 2000:20000:fail exited 0, trapped None, fuel_used 2,017,914,692 (proposer 2,017,052,943), loop 1.1842 s, 20,000 caught; 2000:20000:ok and 2000:20000:weak each trapped 'out of fuel'. WAT: on wasmtime-py 49.0.0 'thrown' r=100 n=100000 used 1,101 fuel and 'returned' 80,001,201; the CLI 49.0.3 trapped 'all fuel consumed' at 80,001,284 and completed at 80,001,285."
  },
  "remediation": {
    "strategy": "Raise the wasmtime floor to a wasmtime-py carrying wasmtime 49.0.1 or later (or move to 50.x) as soon as one is published. Until then, do not let fuel stand alone as the bound: when fuel is given on 49.0.0, require a finite deadline_s (refuse or warn on deadline_s=None), since epoch interruption is the advisory's workaround and is unaffected; this bounds wall time but cannot make fuel count correctly. List GHSA-m63x-6p34-q65x in SECURITY.md as unmitigated, and say that on 49.0.0 fuel and fuel_used under-count work that ends in a caught C++ exception or longjmp. Disabling wasm exceptions is not an option, because the build depends on them. Add a check, counted in fuel only, that runs the kiwisolver loop above and asserts that the failing call's per-call fuel grows with N as the same-shape no-throw call's does; on 49.0.0 it fails, so it enters as a known gap closed by the floor raise, and the defect cannot return unseen."
  },
  "severity": {
    "likelihood": {
      "score": "low",
      "reason": "Needs an embedder that relies on fuel as the bound (deadline_s=None, or a cap far below the deadline, or fuel_used for accounting); the default 60 s deadline bounds wall time. The guest side is easy: plain Python reaching a caught C++ exception."
    },
    "impact": {
      "score": "medium",
      "reason": "The documented fuel limit does not bound CPU: roughly 100x under-count at N=6000 by wall-time calibration, growing with N, and a 2.2e9 cap let a loop of 20,000 failing calls run where the same-shape no-throw loop ran out of fuel within a few hundred calls. Impact is CPU denial of service and wrong instruction accounting; no sandbox escape."
    },
    "overall_severity": "low"
  },
  "confidence": {
    "score": "high",
    "reason": "Reproduced twice, independently, through wasi_python.run on the shipped artifacts: per-call fuel stays flat across a 30x range of N while wall time grows about 19x; a same-shape no-throw control is counted 7.5x to 79x more fuel per call at comparable wall time and runs out of fuel under the cap the failing loop finishes under; and the engine defect matches the advisory in a standalone differential against the fixed CLI. Not run on a fixed wasmtime-py (none exists), so the true per-call cost of the failing call is inferred from wall time."
  }
}
```

Evidence the earlier agents promoted (read-only): under `context/reviews/0.1.0-security-audit-2026-10-25/agents/*/artifacts/evidence/` (the hunter's and the Phase 3 verifier's folders; their ids appear in the record's execution instructions or can be found by listing that directory).

## 3. Execution boundary and paths

- Target root: `.` (all record paths are repository-relative). Never edit a file under it; never run `uv sync`, plain `uv run`, the download or build scripts, `release/set_key.py`, `gh workflow run`, `git push`, `pytest --accept*`, or anything writing under `context/`. Never download from the internet.
- Your scratch (the only place you write): `context/reviews/0.1.0-security-audit-2026-10-25/agents/r05-eh-fuel-final/scratch/`. If you re-run a check, wrap it as: `ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME=context/reviews/0.1.0-security-audit-2026-10-25/agents/r05-eh-fuel-final/scratch/home TMPDIR=context/reviews/0.1.0-security-audit-2026-10-25/agents/r05-eh-fuel-final/scratch/tmp WASI_PYTHON_CACHE=context/reviews/0.1.0-security-audit-2026-10-25/agents/r05-eh-fuel-final/scratch/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' ./.venv/bin/python -I <script under scratch>` with a `subprocess.run(timeout=...)` bound from a trusted driver; confirm `./build/lane.lock` is absent first; never point a writable grant or root at the target or a real cache; this platform cannot read-only mount the target.
- Return exactly one JSON object and no prose: `{"decision":"verified","fingerprint":"wasmtime-49.0.0:GHSA-m63x-6p34-q65x:try_table-catch-fuel:src/wasi_python/_engines.py:_engine"}` or `{"decision":"replace","reason":"...","record":{...}}` where a replacement record matches its schema branch exactly (`additionalProperties: false`). Also write it to `context/reviews/0.1.0-security-audit-2026-10-25/agents/r05-eh-fuel-final/scratch/result.json`. Non-material wording or line-number corrections are a `replace` with a reason that says they are non-material; a change of verdict, root cause, trace, execution input, observed result, impact or severity is material and must say so.

## 4. Schema branches (verbatim)

### confirmed
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
### needs_validation
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
### rejected
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
