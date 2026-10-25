# Phase 5 record-verifier brief: r01-sysconfigdata

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


## 2. The final record to verify (verdict `confirmed`, decided by Phase 3 verifier `v03-sysconfigdata`; you did not hunt or validate it)

```json
{
  "verdict": "confirmed",
  "fingerprint": "runner-env.sysconfig-PYTHON-SYSCONFIGDATA-PATH.loads-code-outside-import-path-rules",
  "title": "env= _PYTHON_SYSCONFIGDATA_PATH makes a module planted in a reused root run on `import pandas` in a later call",
  "description": "The security model promises that code planted in a root never runs at start-up or on import in a later call, on either binary. The runner holds this with an isolated interpreter (PyConfig_InitIsolatedConfig, site off, only the stdlib zip on sys.path, PYTHON* variables ignored) and by allowing import_path entries only from read-only grants with nothing writable under them. CPython 3.15's sysconfig reads the private variable _PYTHON_SYSCONFIGDATA_PATH from os.environ without consulting sys.flags.ignore_environment, and when it is set it finds and execs `_sysconfigdata__wasi_wasm32-wasi` from that folder with PathFinder and exec_module. The runner lays env= over BASE_ENV and HOME with no key policy beyond emptiness and '=', and the reactor copies that environment into os.environ. So when an embedder passes this variable (for example forwarded with the CLI's --env KEY from a shell that sourced the project's own scripts/python-wasi-cross, which exports it) naming a folder in a reused root, a file an earlier guest wrote there runs in the later call on a plain `import pandas`, which calls sysconfig.get_config_var at import. Verified on both the snapshot and the plain binary. The documented not-protected list names only env= overrides of HOME and PYTHONTZPATH; it does not name this code-loading variable, and the 'Writable grants and imports across calls' item covers an import_path the embedder grants writable, which the runner would refuse for a folder served by the root.",
  "root_cause": "sysconfig._get_sysconfigdata (Lib/sysconfig/__init__.py:356-363, shipped as sysconfig/__init__.pyc in the stdlib zip) loads code from os.environ['_PYTHON_SYSCONFIGDATA_PATH'] regardless of isolated mode, and the runner's env check (_limits._check_inputs, line 139) rejects only empty keys and keys containing '=', so the import_path rules (_places._check_import_path) are never applied to this code-loading folder.",
  "intended_behavior": "Every folder the guest's interpreter loads code from is subject to the import_path rules (a read-only grant with nothing writable under or above it), or the runner refuses or drops an env= entry that would load code from elsewhere, as isolated mode already ignores PYTHONPATH.",
  "trace": [
    {
      "kind": "entrypoint",
      "file": "src/wasi_python/_limits.py",
      "line": 139,
      "scope": "_check_inputs",
      "description": "The embedder's env keys are checked only for emptiness and '='; _PYTHON_SYSCONFIGDATA_PATH passes (called from runner.py:581)."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_call.py",
      "line": 452,
      "scope": "_instance",
      "description": "wasi.env is BASE_ENV, HOME, then env= laid over them, unfiltered; the session opening does the same at _sessions.py:999."
    },
    {
      "kind": "propagation",
      "file": "recipes/reactor_bootstrap.py",
      "line": 143,
      "scope": "run",
      "description": "The reactor clears os.environ and copies the WASI environment into it for the program (the session setup does the same at line 240)."
    },
    {
      "kind": "propagation",
      "file": "build/pandas-3.0.6/pandas/compat/_constants.py",
      "line": 21,
      "scope": "module level",
      "description": "`import pandas` calls sysconfig.get_config_var('HOST_GNU_TYPE') at import time."
    },
    {
      "kind": "propagation",
      "file": "build/Python-3.15.0/Lib/sysconfig/__init__.py",
      "line": 360,
      "scope": "_get_sysconfigdata",
      "description": "Reads _PYTHON_SYSCONFIGDATA_PATH from os.environ with no ignore_environment check (the zip's compiled sysconfig carries the same constant and no ignore_environment reference)."
    },
    {
      "kind": "sink",
      "file": "build/Python-3.15.0/Lib/sysconfig/__init__.py",
      "line": 343,
      "scope": "_import_from_directory",
      "description": "PathFinder.find_spec(name, [path]) then spec.loader.exec_module(module): the module the earlier guest planted in the reused root runs."
    }
  ],
  "evidence": [
    {
      "file": "docs/explanation/security-model.md",
      "line": 9,
      "description": "Policy: code planted in a root never runs at start-up or on import in a later call, on either binary."
    },
    {
      "file": "docs/explanation/security-model.md",
      "line": 82,
      "description": "The only env= overrides listed as not protected are HOME and PYTHONTZPATH; no code-loading variable is named."
    },
    {
      "file": "recipes/reactor_main.c",
      "line": 179,
      "description": "PyConfig_InitIsolatedConfig: the design relies on the interpreter ignoring environment-driven code paths; the guest reports sys.flags.ignore_environment=1 and a PYTHONPATH=/data control does not import the planted module."
    },
    {
      "file": "src/wasi_python/_places.py",
      "line": 176,
      "description": "_check_import_path: the control that confines code-loading folders to read-only grants, which this variable bypasses."
    },
    {
      "file": "build/Python-3.15.0/Lib/sysconfig/__init__.py",
      "line": 361,
      "description": "_import_from_directory(path, name) is used whenever the variable is set."
    },
    {
      "file": "scripts/python-wasi-cross",
      "line": 25,
      "description": "The project's own cross-build wrapper exports _PYTHON_SYSCONFIGDATA_PATH, so a host shell that forwards it with --env is a plausible way the variable reaches a call."
    }
  ],
  "conditions": [
    {
      "kind": "system_configuration",
      "description": "The trusted embedder passes env containing _PYTHON_SYSCONFIGDATA_PATH naming a guest folder that an earlier call could write (a reused root, a writable grant or a writable mount), for example forwarded from a cross-build shell with the CLI's --env _PYTHON_SYSCONFIGDATA_PATH."
    },
    {
      "kind": "data_state",
      "description": "An earlier, less trusted call on the same root or writable folder left `_sysconfigdata__wasi_wasm32-wasi.py` there."
    },
    {
      "kind": "user_interaction",
      "description": "The later program imports pandas (or another package that reads sysconfig config vars at import), or calls sysconfig.get_config_var(s)."
    }
  ],
  "execution": {
    "attacker_perspective": "A guest in call 1 with a writable root writes one file at /data/_sysconfigdata__wasi_wasm32-wasi.py; the embedder's later call on the same root, with env={'_PYTHON_SYSCONFIGDATA_PATH': '/data'}, runs a program that only imports pandas, and the planted module runs.",
    "payloads": [
      "call 1: wasi_python.run(['-c', \"import os; os.makedirs('/data', exist_ok=True); open('/data/_sysconfigdata__wasi_wasm32-wasi.py','w').write(\\\"import sys\\\\nsys.stderr.write('PLANTED-V03\\\\\\\\n')\\\\nbuild_time_vars={'installed_base':'/usr/local'}\\\\n\\\")\"], root=R)",
      "call 2: wasi_python.run(['-c', 'import pandas; print(\"ok\")'], root=R, env={'_PYTHON_SYSCONFIGDATA_PATH': '/data'})"
    ],
    "instructions": [
      "Confirm build/lane.lock is absent. The verifier's script is scratch/evidence/v03_check.py, run by scratch/driver.py with a 600 s subprocess timeout as: ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME=<scratch>/home TMPDIR=<scratch>/tmp WASI_PYTHON_CACHE=<scratch>/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' .venv/bin/python -I <scratch>/evidence/v03_check.py <scratch>, with the root R at <scratch>/work/root. The target tree was not mounted read-only (this platform cannot enforce that) and no memory rlimit was applied; no grant or root pointed at the target.",
      "Calls in order on the same root: plant; flags (sys.flags with the env entry); control_pandas_noenv (import pandas without the entry); env_pandas_snapshot and env_pandas_plain (import pandas with the entry, snapshot True and False); control_pythonpath (env PYTHONPATH=/data, import of a second planted module).",
      "Read scratch/evidence/v03_result.json and v03_run.log for 'PLANTED-V03' on stderr per call."
    ],
    "observed_result": "The guest reports sys.flags.ignore_environment=1 and isolated=1. Without the env entry, import pandas printed ok and the planted module did not run. With env={'_PYTHON_SYSCONFIGDATA_PATH': '/data'}, import pandas printed ok and stderr held 'PLANTED-V03' on both the snapshot and the plain binary. The PYTHONPATH=/data control failed with ModuleNotFoundError, so isolated mode does ignore the documented variable but not this private one. The verifier did not test other packages; the hunter's record also reports scipy, sklearn, joblib and statsmodels.api."
  },
  "remediation": {
    "strategy": "Refuse env keys that make the guest interpreter load code from a folder, at least _PYTHON_SYSCONFIGDATA_PATH, in _limits._check_inputs before any work, with a message pointing to import_path; add a regression check that plants the module in call 1 and asserts that call 2 with the entry raises ValueError. As defence in depth the reactor bootstrap can drop the key from os.environ, as isolated mode drops PYTHONPATH. Name the variable in the security model's not-protected or refused list either way.",
    "code_changes": [
      {
        "file_name": "src/wasi_python/_limits.py",
        "fixed_code": "_CODE_FOLDER_ENV = frozenset({\"_PYTHON_SYSCONFIGDATA_PATH\"})  # sysconfig execs a module from this folder\n...\n            if not name or \"=\" in name:\n                raise ValueError(\"env key: illegal environment variable name\")  # never quoted\n            if name in _CODE_FOLDER_ENV:\n                raise ValueError(\n                    \"env key: _PYTHON_SYSCONFIGDATA_PATH loads code from a folder; \"\n                    \"name a read-only grant in import_path instead\"\n                )"
      }
    ]
  },
  "severity": {
    "likelihood": {
      "score": "low",
      "reason": "Requires the trusted embedder to pass a private, underscore-prefixed CPython variable naming a guest-writable folder on a reused root; plausible mainly when forwarding a cross-build shell's environment, which the project's own wrapper sets."
    },
    "impact": {
      "score": "medium",
      "reason": "Crosses the call-to-call boundary the policy promises: an earlier, lower-trust guest's code runs in the later call with that call's grants, door, tools and stdin. It stays inside the wasm sandbox and does not reach the host."
    },
    "overall_severity": "low"
  },
  "confidence": {
    "score": "high",
    "reason": "The source path is complete in the build tree and the shipped zip, and the verifier reproduced the effect independently on both binaries, with a no-env control and a PYTHONPATH control that did not run the planted code."
  }
}
```

Evidence the earlier agents promoted (read-only): under `context/reviews/0.1.0-security-audit-2026-10-25/agents/*/artifacts/evidence/` (the hunter's and the Phase 3 verifier's folders; their ids appear in the record's execution instructions or can be found by listing that directory).

## 3. Execution boundary and paths

- Target root: `.` (all record paths are repository-relative). Never edit a file under it; never run `uv sync`, plain `uv run`, the download or build scripts, `release/set_key.py`, `gh workflow run`, `git push`, `pytest --accept*`, or anything writing under `context/`. Never download from the internet.
- Your scratch (the only place you write): `context/reviews/0.1.0-security-audit-2026-10-25/agents/r01-sysconfigdata/scratch/`. If you re-run a check, wrap it as: `ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME=context/reviews/0.1.0-security-audit-2026-10-25/agents/r01-sysconfigdata/scratch/home TMPDIR=context/reviews/0.1.0-security-audit-2026-10-25/agents/r01-sysconfigdata/scratch/tmp WASI_PYTHON_CACHE=context/reviews/0.1.0-security-audit-2026-10-25/agents/r01-sysconfigdata/scratch/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' ./.venv/bin/python -I <script under scratch>` with a `subprocess.run(timeout=...)` bound from a trusted driver; confirm `./build/lane.lock` is absent first; never point a writable grant or root at the target or a real cache; this platform cannot read-only mount the target.
- Return exactly one JSON object and no prose: `{"decision":"verified","fingerprint":"runner-env.sysconfig-PYTHON-SYSCONFIGDATA-PATH.loads-code-outside-import-path-rules"}` or `{"decision":"replace","reason":"...","record":{...}}` where a replacement record matches its schema branch exactly (`additionalProperties: false`). Also write it to `context/reviews/0.1.0-security-audit-2026-10-25/agents/r01-sysconfigdata/scratch/result.json`. Non-material wording or line-number corrections are a `replace` with a reason that says they are non-material; a change of verdict, root cause, trace, execution input, observed result, impact or severity is material and must say so.

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
