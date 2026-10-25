# Phase 5 record-verifier brief: r04-eh-fuel

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


## 2. The final record to verify (verdict `needs_validation`, decided by Phase 3 verifier `v04-eh-fuel`; you did not hunt or validate it)

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

Evidence the earlier agents promoted (read-only): under `context/reviews/0.1.0-security-audit-2026-10-25/agents/*/artifacts/evidence/` (the hunter's and the Phase 3 verifier's folders; their ids appear in the record's execution instructions or can be found by listing that directory).

## 3. Execution boundary and paths

- Target root: `.` (all record paths are repository-relative). Never edit a file under it; never run `uv sync`, plain `uv run`, the download or build scripts, `release/set_key.py`, `gh workflow run`, `git push`, `pytest --accept*`, or anything writing under `context/`. Never download from the internet.
- Your scratch (the only place you write): `context/reviews/0.1.0-security-audit-2026-10-25/agents/r04-eh-fuel/scratch/`. If you re-run a check, wrap it as: `ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME=context/reviews/0.1.0-security-audit-2026-10-25/agents/r04-eh-fuel/scratch/home TMPDIR=context/reviews/0.1.0-security-audit-2026-10-25/agents/r04-eh-fuel/scratch/tmp WASI_PYTHON_CACHE=context/reviews/0.1.0-security-audit-2026-10-25/agents/r04-eh-fuel/scratch/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' ./.venv/bin/python -I <script under scratch>` with a `subprocess.run(timeout=...)` bound from a trusted driver; confirm `./build/lane.lock` is absent first; never point a writable grant or root at the target or a real cache; this platform cannot read-only mount the target.
- Return exactly one JSON object and no prose: `{"decision":"verified","fingerprint":"wasmtime-49.0.0:GHSA-m63x-6p34-q65x:try_table-catch-fuel:src/wasi_python/_engines.py:_engine"}` or `{"decision":"replace","reason":"...","record":{...}}` where a replacement record matches its schema branch exactly (`additionalProperties: false`). Also write it to `context/reviews/0.1.0-security-audit-2026-10-25/agents/r04-eh-fuel/scratch/result.json`. Non-material wording or line-number corrections are a `replace` with a reason that says they are non-material; a change of verdict, root cause, trace, execution input, observed result, impact or severity is material and must say so.

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
