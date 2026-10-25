# Phase 5 record-verifier brief: r03-class-partial

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


## 2. The final record to verify (verdict `confirmed`, decided by Phase 3 verifier `v02-class-partial`; you did not hunt or validate it)

```json
{
  "verdict": "confirmed",
  "fingerprint": "src/wasi_python/tools.py:_bound_keywords:class-construction-partial-unfixed",
  "title": "A guest can override a keyword a class tool's constructor binds with a partial or partialmethod",
  "description": "tool() promises that a keyword a functools.partial binds is fixed: it is left out of the schema, refused when a given schema names it, and refused in a frame. For a class registered as a tool, _bound_keywords goes from the class to type(cls).__call__, which is type.__call__ (a C slot), and returns with no fixed keywords. inspect.signature and the runtime both go into the class's own __new__ and __init__. So when __init__ is a functools.partialmethod, when __init__ is a functools.partial (a method descriptor on Python 3.14), or when __new__ is a staticmethod over a functools.partial, the bound keyword is not recorded in Tool._fixed. tool() then accepts a given schema that names the keyword, and the per-frame refusal in _ToolHost._call_answer never fires. Under an explicit schema that is open, has additionalProperties true, or lists the keyword, a guest frame naming the keyword reaches the constructor, and the guest's value replaces the embedder's bound value, because a partial lets call-time keywords override bound ones. The gate's ToolCall.arguments also carries the keyword, although the documentation says arguments never hold a keyword a partial binds. The same registration path is already refused for a callable instance whose __call__ is a partialmethod, so the class case is a gap in an intended control, not an unhandled design choice.",
  "root_cause": "_bound_keywords (src/wasi_python/tools.py:439-474) treats a class like any other callable object: it reads type(target).__call__ and returns at the C-slot check (tools.py:466-470). It never reads the class's own __new__ or __init__, where inspect.signature and type.__call__ find the partial. So Tool._fixed is empty. The two checks that rely on it, _given (tools.py:418-423) and the frame refusal (_tool_host.py:1003-1009), let the bound keyword through.",
  "intended_behavior": "A keyword bound by a partial or partialmethod on a class's construction path (its __new__ or __init__, found through the MRO, through staticmethod or classmethod wrappers, nested partials and __wrapped__ links) is in Tool._fixed, or the class is refused at tool() as an unbound partialmethod already is. tool() then refuses a given schema that names the keyword, and a frame that names it is answered invalid_arguments without the gate or the constructor running.",
  "trace": [
    {
      "kind": "entrypoint",
      "file": "src/wasi_python/_call.py",
      "line": 1263,
      "scope": "_door",
      "description": "Untrusted guest code calls the imported host::call door; after admit, the frame bytes are copied out of guest linear memory and handed to the tool frame host."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_tool_host.py",
      "line": 1000,
      "scope": "_ToolHost._call_answer",
      "description": "The args object is checked against the tool's explicit schema; an open schema ({\"type\": \"object\"}), additionalProperties true, or a properties map naming the keyword accepts role."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_tool_host.py",
      "line": 1004,
      "scope": "_ToolHost._call_answer",
      "description": "The bound-keyword refusal tests each argument against t._fixed, which is empty for the class tool, so role passes."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/tools.py",
      "line": 469,
      "scope": "_bound_keywords",
      "description": "At registration the walk reached type.__call__, a C slot, and returned no fixed keywords without reading the class's __init__ or __new__."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_tool_host.py",
      "line": 232,
      "scope": "_Work.__call__",
      "description": "The gate receives a deep copy of the arguments with role in it, contrary to the documented contract."
    },
    {
      "kind": "sink",
      "file": "src/wasi_python/_tool_host.py",
      "line": 258,
      "scope": "_Work.__call__",
      "description": "t.fn(**args) calls the class; type.__call__ runs the partial-bound __init__ or __new__, whose keyword merge lets the guest's role replace the embedder's bound role."
    }
  ],
  "evidence": [
    {
      "file": "src/wasi_python/tools.py",
      "line": 439,
      "description": "Docstring of _bound_keywords: keywords a partial binds are found wherever inspect.signature may meet one on its way to the function; each is fixed and refused in a frame."
    },
    {
      "file": "src/wasi_python/tools.py",
      "line": 466,
      "description": "A class target goes to type(target).__call__ and stops at the C-slot check (line 469), so a partial in __init__ or __new__ is never collected."
    },
    {
      "file": "src/wasi_python/tools.py",
      "line": 364,
      "description": "tool() computes fixed = _bound_keywords(name, fn) once; it is the only source of Tool._fixed."
    },
    {
      "file": "src/wasi_python/tools.py",
      "line": 418,
      "description": "_given refuses a schema naming a fixed keyword only through the computed fixed set, so a schema naming role is accepted for the class."
    },
    {
      "file": "src/wasi_python/_tool_host.py",
      "line": 1004,
      "description": "The frame-time refusal relies on t._fixed alone."
    },
    {
      "file": "docs/how-to/tools.md",
      "line": 65,
      "description": "Promise: a keyword the partial binds is fixed, not in the schema, and a frame that names it is refused."
    },
    {
      "file": "docs/how-to/tools.md",
      "line": 71,
      "description": "Promise: the gate's arguments hold no keyword a partial binds."
    },
    {
      "file": "tests/checks/test_v1_4_embedding.py",
      "line": 3517,
      "description": "The regression test covers nested partials, a __wrapped__ chain, a bound partialmethod and refuses an unbound partialmethod, but has no class whose constructor binds a keyword."
    }
  ],
  "conditions": [
    {
      "kind": "system_configuration",
      "description": "The embedder registers a class (a type whose metaclass __call__ is type.__call__) as a tool, with __init__ that is a functools.partialmethod, __init__ that is a functools.partial (Python 3.14 makes it a method descriptor), or __new__ that is a staticmethod over a functools.partial, binding an authority keyword such as a role or user id."
    },
    {
      "kind": "system_configuration",
      "description": "The tool's explicit input_schema lets the keyword through: no properties (open), additionalProperties not false, or a properties map naming it, which tool() refuses for every other binding shape. A derived schema is not reachable: tool() refuses a class without an explicit schema for lack of hints."
    },
    {
      "kind": "authentication_level",
      "description": "The attacker is the untrusted guest code, or the model driving it, which can send any frame through the door."
    }
  ],
  "execution": {
    "attacker_perspective": "Untrusted guest code in wasi_python.run(tools=[...], gate=...) sends a raw tool-protocol frame through _host.call naming a keyword the embedder bound in the tool class's constructor.",
    "payloads": [
      "class AccountPM(dict):\n    def _init(self, q, role=\"user\"): dict.__init__(self, q=q, role=role)\n    __init__ = functools.partialmethod(_init, role=\"viewer\")\ntool(AccountPM, name=\"acct_pm\", input_schema={\"type\": \"object\"})",
      "class AccountP(dict):\n    __init__ = functools.partial(_initp, role=\"viewer\")  # Python 3.14",
      "class AccountNew:\n    __new__ = staticmethod(functools.partial(_new, role=\"viewer\"))  # _new returns a dict",
      "import _host; _host.call(b'{\"v\":1,\"id\":1,\"op\":\"call\",\"tool\":\"acct_pm\",\"args\":{\"q\":\"x\",\"role\":\"admin\"}}')",
      "Control: tool(functools.partial(orders, user_id=42), name=\"orders\", input_schema={\"type\": \"object\"}) and a frame with args {\"q\":\"x\",\"user_id\":1}"
    ],
    "instructions": [
      "Verifier-owned harness: scratch/evidence/v02_class_ctor_partial.py, output scratch/evidence/v02_class_ctor_partial.out.json (stderr in v02_class_ctor_partial.err.txt), run with the repository's .venv (Python 3.14.2, wasmtime-py 49.0.0) and the checkout's build/artifacts set.",
      "Run under ulimit -t 300 -f 4000000 -n 4096, env -i with PATH=/usr/bin:/bin and HOME, TMPDIR and WASI_PYTHON_CACHE in the verifier's scratch, sandbox-exec denying network, python -I, and a 240 s subprocess.run timeout from a trusted driver. build/lane.lock was absent. The target was not mounted read-only (the platform cannot enforce it); no grant or root pointed at it, and nothing was written under it.",
      "Host side: register AccountPM, AccountP and AccountNew each with input_schema={\"type\": \"object\"}, plus the plain-partial control orders, in one wasi_python.run(['-c', prog], tools=[...], gate=gate, deadline_s=60) call with a gate that records call.arguments and allows. Also call tool() on each class with a schema whose properties name role, and on the partial with a schema naming user_id.",
      "Guest side: send through _host.call a frame naming role='admin' to each class tool, one without role, then user_id=1 and a call without user_id to the control.",
      "Read the guest's answers, the host log of what the gate and each constructor received, Tool._fixed, and done.tools.outcomes."
    ],
    "observed_result": "Each of the three class tools answered ok with value {\"q\": \"x\", \"role\": \"admin\"}; the host log shows the gate received {\"q\": \"x\", \"role\": \"admin\"} and each constructor ran with role='admin'; the record's outcome was ok. Without role the constructor ran with the bound role='viewer'. Tool._fixed was [] for all three, inspect.signature showed '(q, *, role='viewer')', and tool() accepted a schema whose properties name role. In the same run the control's user_id=1 frame was answered invalid_arguments ('unknown argument user_id') with neither the gate nor the handler running, and tool() refused a schema naming user_id. A callable instance whose __call__ is a partialmethod is refused at tool(), so only the class construction path is unguarded."
  },
  "remediation": {
    "strategy": "In _bound_keywords, when the target is a class, read its construction path as type.__call__ runs it: inspect.getattr_static(cls, '__new__') and inspect.getattr_static(cls, '__init__') (MRO included), unwrap staticmethod and classmethod through __func__, and then walk each member with the same loop the function already uses (partial keywords collected, nested partials and __wrapped__ followed), treating a partialmethod as its .func plus .keywords rather than refusing it. Do this whatever the metaclass __call__ is: a Python metaclass __call__ that delegates to super().__call__() still runs __init__ with the guest's keywords, and the hunter's patch skips that case (in the verifier's run it returned [] for such a class, where inspect.signature shows only (*a, **k)). A simpler fail-closed alternative is to refuse at tool() any class whose __new__ or __init__ is a partial or partialmethod, as an unbound partialmethod is refused today. Add to test_bound_keywords_are_fixed_however_the_partial_is_reached a class with a partialmethod __init__, a 3.14 partial __init__ and a staticmethod-partial __new__, under an open schema and under a schema naming the keyword, expecting refusal at tool() or invalid_arguments with neither gate nor constructor called.",
    "code_changes": [
      {
        "file_name": "src/wasi_python/tools.py",
        "fixed_code": "    if isinstance(fn, type):\n        # type.__call__ (or a metaclass's __call__ that defers to it) runs the class's own\n        # __new__ and __init__: a partial bound there is fixed too.\n        for attr in (\"__new__\", \"__init__\"):\n            member = inspect.getattr_static(fn, attr, None)\n            member = getattr(member, \"__func__\", member)  # staticmethod, classmethod\n            if isinstance(member, functools.partialmethod):\n                found.update(member.keywords)\n                member = member.func\n            if isinstance(member, functools.partial) or getattr(member, \"__wrapped__\", None) is not None:\n                found.update(_bound_keywords(name, member))\n    # ... then the existing walk from fn, adding its keywords to found"
      }
    ]
  },
  "severity": {
    "likelihood": {
      "score": "low",
      "reason": "It needs an uncommon registration shape the embedder chooses: a class as a tool whose constructor binds authority with a partial or partialmethod, plus an explicit schema that leaves the keyword open or names it."
    },
    "impact": {
      "score": "medium",
      "reason": "Where that shape is used, untrusted guest code replaces an authority value the embedder bound, such as a role or user id, the constructor acts with it, and the gate is shown arguments the documentation says it never holds. That is a confused deputy inside the embedder's process against an explicit documented guarantee; it does not escape the sandbox or reach other tools."
    },
    "overall_severity": "low"
  },
  "confidence": {
    "score": "high",
    "reason": "Independently reproduced end to end through the real door, frame host and gate for three constructor shapes on Python 3.14.2, with the plain-partial control refused in the same run, and the source walk at tools.py:466-470 explains the result exactly."
  }
}
```

Evidence the earlier agents promoted (read-only): under `context/reviews/0.1.0-security-audit-2026-10-25/agents/*/artifacts/evidence/` (the hunter's and the Phase 3 verifier's folders; their ids appear in the record's execution instructions or can be found by listing that directory).

## 3. Execution boundary and paths

- Target root: `.` (all record paths are repository-relative). Never edit a file under it; never run `uv sync`, plain `uv run`, the download or build scripts, `release/set_key.py`, `gh workflow run`, `git push`, `pytest --accept*`, or anything writing under `context/`. Never download from the internet.
- Your scratch (the only place you write): `context/reviews/0.1.0-security-audit-2026-10-25/agents/r03-class-partial/scratch/`. If you re-run a check, wrap it as: `ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME=context/reviews/0.1.0-security-audit-2026-10-25/agents/r03-class-partial/scratch/home TMPDIR=context/reviews/0.1.0-security-audit-2026-10-25/agents/r03-class-partial/scratch/tmp WASI_PYTHON_CACHE=context/reviews/0.1.0-security-audit-2026-10-25/agents/r03-class-partial/scratch/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' ./.venv/bin/python -I <script under scratch>` with a `subprocess.run(timeout=...)` bound from a trusted driver; confirm `./build/lane.lock` is absent first; never point a writable grant or root at the target or a real cache; this platform cannot read-only mount the target.
- Return exactly one JSON object and no prose: `{"decision":"verified","fingerprint":"src/wasi_python/tools.py:_bound_keywords:class-construction-partial-unfixed"}` or `{"decision":"replace","reason":"...","record":{...}}` where a replacement record matches its schema branch exactly (`additionalProperties: false`). Also write it to `context/reviews/0.1.0-security-audit-2026-10-25/agents/r03-class-partial/scratch/result.json`. Non-material wording or line-number corrections are a `replace` with a reason that says they are non-material; a change of verdict, root cause, trace, execution input, observed result, impact or severity is material and must say so.

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
