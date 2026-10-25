# Phase 5 record-verifier brief: r02-cache-swap

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


## 2. The final record to verify (verdict `needs_validation`, decided by Phase 3 verifier `v01-cache-swap`; you did not hunt or validate it)

```json
{
  "verdict": "needs_validation",
  "fingerprint": "src/wasi_python/_engines.py:_load:cwasm-checked-by-lstat-opened-by-path",
  "title": "Module cache: the .cwasm checked by lstat is not bound to the file wasmtime deserializes, so a lower-trust owner of an ancestor of the default cache folder can swap in its own native code",
  "description": "The runner loads a .cwasm (native code) only when private() finds the cache folder and the file owned by this user, with no group or other bits and one link. Each check is an lstat of the leaf by its full path. wasmtime-py then reopens the file by the same full path (Module.deserialize_file, which passes the path to the C API), and the runner afterwards compares a fresh lstat stamp (dev, ino, size, mtime) with the first one. No step checks the ancestors of the cache folder, and the check and the load are not bound to one descriptor. A principal that can rename entries in any ancestor can point the path at its own folder only while wasmtime opens it, and restore it before the stamp re-check. The planted module is then cached in the process and used as python.wasm. The default cache is chosen by the runner from $HOME (or $XDG_CACHE_HOME on Linux), so a process whose HOME belongs to another user, such as root under a sudo that keeps HOME, places the default cache under a folder that other user owns. The verifier reproduced the identity mismatch on one OS user: with a deterministic schedule the checked file was inode 222410199 and the opened file was the planted inode 222410200, and _module returned the planted module with no warning. With a blind external swapper (renamex_np RENAME_SWAP in a loop, no hook in the runner), 3 of 5000 in-process load attempts returned the planted module, the first of them with no RuntimeWarning in that attempt; 4367 of the 5000 attempts did raise a 'not using the module cache' warning. The cross-user case and the deployment that creates it were not observed. Context that limits the effect: when the user whose HOME is kept holds unrestricted sudo, that user already has root and no boundary is crossed; the effect matters where that user is lower trust than the runner's user, for example a sudo rule restricted to one command, a container or CI step running as another uid with a mapped home, or HOME set to a shared folder another user can pre-create entries in.",
  "claimed_root_cause": "private() (src/wasi_python/_platform.py:556-577) and the post-load stamp check (src/wasi_python/_engines.py:237) bind the trust decision to path names, by lstat of the leaf, while the load (src/wasi_python/_engines.py:233) reopens the file by path and follows any link in its ancestors. Nothing checks that every ancestor of the cache folder is owned by this user or root and not writable by others, and the .cwasm is not opened once with no-follow and deserialized from that verified descriptor (for example by reading it from the checked descriptor into Module.deserialize, or by checking the ancestry). The default cache path is derived from $HOME without checking that $HOME belongs to this user.",
  "trace": [
    {
      "kind": "entrypoint",
      "file": "src/wasi_python/runner.py",
      "line": 115,
      "scope": "run",
      "description": "Embedder call with the default cache_dir=None (parameter at line 130): the default module cache is used."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_call.py",
      "line": 146,
      "scope": "_run_checked",
      "description": "cache = _engines._cache_dir(cache_dir)."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_engines.py",
      "line": 85,
      "scope": "_cache_dir",
      "description": "With no $WASI_PYTHON_CACHE, the cache is default_cache_dir(Path.home()); Path.home() reads $HOME, which under a sudo that keeps HOME is the invoking user's home."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_platform.py",
      "line": 534,
      "scope": "_Posix.default_cache_dir",
      "description": "$XDG_CACHE_HOME or $HOME/.cache, then wasi_python (macOS line 1091: $HOME/Library/Caches/wasi_python); the parent folders belong to whoever owns that home."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_engines.py",
      "line": 178,
      "scope": "_module_miss",
      "description": "private(cache, is_dir=True) makes the folder if absent and lstats only the cache folder itself (owner, kind, no group/other bits); its ancestors are not checked."
    },
    {
      "kind": "propagation",
      "file": "src/wasi_python/_engines.py",
      "line": 228,
      "scope": "_load",
      "description": "private(cwasm) lstats the leaf by path: this user's regular file, one link, no group/other bits; the stamp 'before' was taken by lstat at line 222."
    },
    {
      "kind": "sink",
      "file": "src/wasi_python/_engines.py",
      "line": 233,
      "scope": "_load",
      "description": "wt.Module.deserialize_file(engine, str(cwasm)) reopens the full path inside wasmtime's C API, following any link swapped into an ancestor; the stamp re-check at line 237 passes once the ancestor is restored, the load is counted, and the module is kept in process().modules and instantiated as the guest binary."
    }
  ],
  "evidence": [
    {
      "file": "src/wasi_python/_platform.py",
      "line": 564,
      "description": "POSIX private(): one os.lstat of the given path, then owner, kind and mode-bit checks; no ancestor ownership or writability check."
    },
    {
      "file": "src/wasi_python/_engines.py",
      "line": 217,
      "description": "_load docstring: the post-load check 'narrows, not closes, the window between the check and the load'."
    },
    {
      "file": "src/wasi_python/_engines.py",
      "line": 237,
      "description": "The re-check compares lstat stamps by name, which a swap restored before it runs passes."
    },
    {
      "file": "src/wasi_python/_platform.py",
      "line": 545,
      "description": "default_cache_dirs docstring: the runner expects processes whose $HOME is not the password database's home (sudo, a container, CI), so the configuration is anticipated by source, not excluded."
    },
    {
      "file": "docs/explanation/security-model.md",
      "line": 89,
      "description": "Names cache_dir, $WASI_PYTHON_CACHE and the artifact folder as trusted input; it does not name $HOME or the default cache derived from it, so the documented threat model does not settle a HOME owned by another user either way."
    },
    {
      "file": "docs/get-started/install.md",
      "line": 60,
      "description": "States the default 'in your own profile' is a folder only you can write: an assumption about the default, which a process with another user's HOME breaks; not a declaration that HOME is trusted input."
    },
    {
      "file": "agents/v01-cache-swap/artifacts/evidence/v01_swap_run.log",
      "line": 5,
      "description": "Verifier's deterministic schedule: the identity checked (inode 222410199) differs from the identity opened (222410200, the planted 0644 file), and the path is back to the checked identity at the re-check."
    },
    {
      "file": "agents/v01-cache-swap/artifacts/evidence/v01_swap_run.log",
      "line": 6,
      "description": "_module returned the planted module (exports ['planted_image_loaded']) for a.wasm with no warning, counts loaded=1."
    },
    {
      "file": "agents/v01-cache-swap/artifacts/evidence/v01_swap_run.log",
      "line": 8,
      "description": "Blind race with no hook: 3 of 5000 load attempts returned the planted module (first at attempt 1132, with no warning in that attempt); 4367 attempts raised a cache warning; 34044 swaps; the runner's own write replaced the planted file through the link 371 times."
    }
  ],
  "blockers": [
    "The cross-user case was not observed: this macOS machine offers one OS user (uid 501) and no root, so a lower-trust owner of an ancestor of the cache folder racing another user's or root's runner could not be run; the verifier's evidence uses one user in both roles.",
    "Whether a supported deployment runs the runner as one user with a $HOME (or $XDG_CACHE_HOME) whose ancestors another, lower-trust user can rename entries in is a deployment fact outside source. /etc/sudoers on this machine is root-only (0440), so whether this host's sudo keeps HOME could not be read. Source anticipates such processes (_platform.py:545) and the documentation names only cache_dir, $WASI_PYTHON_CACHE and the artifact folder as trusted input, so neither settles it.",
    "The blind race was measured only in-process with a tiny module (3 of 5000 attempts on darwin-arm64); a real runner process loads its module once per process, and the per-process success rate with the real snapshot-sized .cwasm across two users was not measured."
  ],
  "validation_plan": {
    "local": "On a disposable macOS or Linux VM with users alice and root, never on a real cache: (1) as root with HOME=/home/alice (Linux: sudo --preserve-env=HOME, or a sudoers env_keep HOME for one test command; macOS: check sudo -V output for HOME in env_keep) run wasi_python.run(['-c','print(1)'], snapshot=False) once so root makes its 0700 cache and .cwasm under alice's ~/.cache (or ~/Library/Caches). (2) As alice, put a serialized module of another wasm, made by the same wasmtime 49.0.0 engine configuration, at /home/alice/planted/<same .cwasm name>, mode 0644, and a link /home/alice/.cache/swaplink -> /home/alice/planted. (3) As alice, loop an atomic swap of ~/.cache/wasi_python and ~/.cache/swaplink (Linux renameat2 RENAME_EXCHANGE, macOS renamex_np RENAME_SWAP), re-planting the file whenever it changes. (4) As root, start N fresh processes, each calling run() once and printing wasi_python's process().counts and whether the call failed for missing exports or printed the planted module's behaviour, with RuntimeWarnings captured. Record the count of processes that loaded the planted module and whether each raised a warning. The single-user deterministic and blind schedules are in agents/v01-cache-swap/artifacts/evidence/v01_swap_harness.py.",
    "deployment": "The owner states whether running the runner as root or another user with a different user's $HOME or $XDG_CACHE_HOME (sudo keeping HOME, a container or CI step with a mapped or shared home, HOME in a shared folder) is a supported configuration or is declared trusted input like cache_dir and $WASI_PYTHON_CACHE. If supported, confirm on the release platforms whether sudo keeps HOME by default and that the default cache's ancestors are then owned by the invoking user; if declared trusted, the security model's list at docs/explanation/security-model.md:89 should name $HOME and $XDG_CACHE_HOME, and this becomes hardening."
  }
}
```

Evidence the earlier agents promoted (read-only): under `context/reviews/0.1.0-security-audit-2026-10-25/agents/*/artifacts/evidence/` (the hunter's and the Phase 3 verifier's folders; their ids appear in the record's execution instructions or can be found by listing that directory).

## 3. Execution boundary and paths

- Target root: `.` (all record paths are repository-relative). Never edit a file under it; never run `uv sync`, plain `uv run`, the download or build scripts, `release/set_key.py`, `gh workflow run`, `git push`, `pytest --accept*`, or anything writing under `context/`. Never download from the internet.
- Your scratch (the only place you write): `context/reviews/0.1.0-security-audit-2026-10-25/agents/r02-cache-swap/scratch/`. If you re-run a check, wrap it as: `ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME=context/reviews/0.1.0-security-audit-2026-10-25/agents/r02-cache-swap/scratch/home TMPDIR=context/reviews/0.1.0-security-audit-2026-10-25/agents/r02-cache-swap/scratch/tmp WASI_PYTHON_CACHE=context/reviews/0.1.0-security-audit-2026-10-25/agents/r02-cache-swap/scratch/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' ./.venv/bin/python -I <script under scratch>` with a `subprocess.run(timeout=...)` bound from a trusted driver; confirm `./build/lane.lock` is absent first; never point a writable grant or root at the target or a real cache; this platform cannot read-only mount the target.
- Return exactly one JSON object and no prose: `{"decision":"verified","fingerprint":"src/wasi_python/_engines.py:_load:cwasm-checked-by-lstat-opened-by-path"}` or `{"decision":"replace","reason":"...","record":{...}}` where a replacement record matches its schema branch exactly (`additionalProperties: false`). Also write it to `context/reviews/0.1.0-security-audit-2026-10-25/agents/r02-cache-swap/scratch/result.json`. Non-material wording or line-number corrections are a `replace` with a reason that says they are non-material; a change of verdict, root cause, trace, execution input, observed result, impact or severity is material and must say so.

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
