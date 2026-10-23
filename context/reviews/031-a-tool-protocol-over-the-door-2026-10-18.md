# Review of 031 — A tool protocol over the door (the build; also a security review)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change, the specification, its pre-build review, its confirmation or the author's notes. I read `AGENTS.md`, the constitution, the threat model (`../research/2026-10-16-a-principal-engineers-direction.md` §2), spec 031 with its landing notes, its pre-build review with the Confirmation (C1 to C6) and the author's note, the build review of 032 (for the record's fault text and the review style), and the diff (`git show d58f2a4`). I read all of `src/wasi_python/tools.py`, `recipes/guest/host/__init__.py` and `recipes/guest/host/tools.py`; the new checks' names and the bodies a finding needed; `recipes/reactor_main.c` and `recipes/reactor_bootstrap.py` (for the snapshot's fuel); the `pyproject.toml`, `70_zip.sh` and `test_rules.py` changes. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** commit `d58f2a4` on `spec/031-a-tool-protocol-over-the-door` in the worktree `../wasi_python-031`, based on `cde2a7c`. Main has since moved to `987012e` (spec 032 accepted); the branch is not rebased. Main and the branch both change `README.md`, `CHANGELOG.md` and `tests/checks/test_v1_4_embedding.py` (EXECUTED, `git diff --name-only`).
- **Ran (EXECUTED, darwin-arm64, host CPython 3.14.2 from `uv run`, wasmtime-py 49).** Scripts and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev031/`.
  - `uv sync`; `shasum -a 256 -c SHA256SUMS` in the worktree's `build/artifacts` (every line OK); then `uv run pytest` in the worktree, no flags, against its own artifacts (`full.log`). `git status` was clean before and after every run.
  - `uv run ruff check` and `ruff format --check` on `src tests recipes/guest`, and `ruff check .`.
  - `fuzz_parse.py` → `fuzz_parse.txt`: 41 hostile frames, and 11 frame shapes at 256 KiB and 1 MiB.
  - `cost.py`, `enum_cost.py` → `cost.txt`, `enum.txt`; `walk.py`; `dbg.py`, `dbg2.py`: the validator's work, counted (calls of `_key`, characters `json.dumps` makes for messages, steps per JSON value).
  - `mutants.py` → `mutants.txt`: 21 mutants, each applied, judged by the two unit files and restored byte for byte (`git diff --stat` empty after).
  - `guest.py` → `guest.txt`: the guest package against its own bounds and 19 hostile answers.
  - `base.py`, `misc.py`: `BaseException` paths; a long `$ref` chain; `dataclasses.replace`.
  - `snapfuel.py`, `snapfuel2.py`, `snapfuel3.py` → `snapfuel.txt`: where the snapshot start's growth goes, on main's frozen set `s-8d84b3b190fe9bce` and the worktree's set, with the judge's driver and the builder's heap perturbations.
  - Times below are benchmark facts from those scripts, labelled so. No check measures time.

## The judge

EXECUTED (`full.log`), the same scoreboard as the landing notes:

```
wasi_python v1: 204/208 pass · 0 gap · 4 blocked · 0 fail   (unit suite 750/757, 7 skipped)
  v1.4  embedding           81/81
ratchet vs 92df8325a4: lost 0 · absent 0 · unrun 0 · unrun locally 2 · gained 4 · grew 40 · judge changed: pyproject.toml, tests/checks/test_rules.py, tests/checks/test_v1_4_embedding.py and 2 more
RED: 40 metric(s) grew
954 passed, 11 skipped in 186.38s
```

It is red only for growth, as the landing notes say. The artifact set: `python.wasm` and every `LICENSES/` line equal main's frozen set (EXECUTED, `diff` of the two `SHA256SUMS` without the three changed lines). `MANIFEST` differs by the two recipe lines, `70_zip.sh`'s hash and `x-snapshot-zip` (EXECUTED, `diff`). Ruff is clean on the judged paths and on `.` (EXECUTED).

## Findings, most severe first

### F1 — High. The validation budget counts steps, but `enum` costs its whole list on every visit, uncounted

- C1 asked for a bound on the work the validator does on the door's thread, where no deadline, cancel or Ctrl-C reaches. The budget bounds visits. It does not bound the work inside a visit.
- `visit` checks `enum` with `any(_key(e) == k for e in s["enum"])` (READ, `tools.py:791-794`). Every visit rebuilds the key of every allowed value. The cost is the enum's length, per value, and no step is charged for it.
- A derived hint is enough. `names: list[Literal[<600 names>]]` (time zones, currencies) is plain `tool()` output. A guest sends 99,990 valid names in one 800 KB frame.
  - EXECUTED (`enum.txt`): outcome `ok`, 99,991 steps (under the budget), **60,093,990 calls of `_key`** in one frame.
  - Benchmark fact: 5.15 s for that frame; 17.78 s with a 2,000-value `Literal`.
  - With the default `max_calls=1000`, one run can hold the door's thread for about 1,000 times that (INFERRED: each frame is answered alone, and nothing else charges for it).
- The same class, bounded today only by accident (F2): `enum` and `const` build the key of the whole value (a container's key costs its size), and a failing `enum`, `const` or number check formats the whole value with `json.dumps` before `_echo` cuts it to 64 characters (`_shown`). EXECUTED (`cost.txt`, case B): one frame made 1,238,010 characters of messages. These are paid against the parent's counted walk of the same value (F2), so they stay within a small multiple of the budget today. They stop being bounded once F2 is fixed.
- Fix:
  - At vetting, keep a `frozenset` of each `enum`'s keys (by node identity, on the `Tool` or in a side table), so membership is one hash. The keys are hashable already.
  - Charge each node `_key` touches to the budget (one step per node), for `enum`, `const` and `uniqueItems`, so a key costs what it builds.
  - Make `_shown` bounded: echo a container by its kind and size, or dump it with a walk that stops at 64 characters.
  - A check, counted: a 600-value `Literal` list of 99,990 items costs at most one key build per item (a counting `_key`), and the stand-in (today's code) builds about 60 million.

### F2 — Medium. Steps per value grow with the schema's wrappers, so valid nested arguments are "too complex"

- The builder's choice "bytes are checked at every schema node" is done by walking every container under the implicit `true` schema at every node. A node that only delegates (`$ref`, `anyOf`, `oneOf`) walks the whole value too, after or before its target or branch walks it (READ, `visit`, `object`, `array`; EXECUTED, `dbg2.py`: a `{"anyOf": …}` node visits each item of `[[0, 1, 2]]` under `True` before trying its branches).
- So each `$ref` or `anyOf` above a value re-walks its subtree. The work is the value's size times the number of wrappers above it, not "about one step per JSON value" as Decision 3 and the README say. EXECUTED (`walk.py`):

  | arguments (pydantic's shapes) | JSON values | steps | per value | outcome |
  |---|---|---|---|---|
  | an order, `lines: list[Line]` (`$ref`), 1,000 lines | 7,002 | 16,002 | 2.29 | ok |
  | the same, 10,000 lines | 70,002 | 100,000 | — | too complex |
  | a recursive `Node` tree, depth 5, 1,000 leaves | 2,019 | 16,082 | 7.97 | ok |
  | depth 20, 1,000 leaves | 2,064 | 46,757 | 22.65 | ok |
  | depth 40, 1,000 leaves | 2,124 | 88,707 | 41.76 | ok |
  | depth 20, 5,000 leaves | 10,064 | 100,000 | — | too complex |

- A valid tree of 10,064 values (about 100 KB) is refused. Recursive pydantic models are the schemas C1 was about, so this is the common case, not an edge.
- Fix: walk a value's children at a node only when the node carries a keyword that describes them, or when it delegates nothing. At a node with `$ref`, `anyOf` or `oneOf`, the target or the matching branch already walks the value, so the bytes rule still holds: a value that passes was walked by some schema that says what it may hold. Then fix F1's per-node key charge in the same change, since the redundant walk is what bounds the key work today. A check: the order and tree above cost at most about two steps per value, and a naive "walk at every node" stand-in fails it.

### F3 — Low. A `BaseException` from an exception's `__str__` escapes the frame host

- Decision 6: "Nothing a frame, a gate or a tool does raises out of the frame host. A tool's or gate's `BaseException` is a fault too."
- `_Work` catches a `ToolError`'s `__str__` failing with `except Exception`, and `_fault` reads `str(e)` under `except Exception` too (READ, `tools.py:1139-1145, 1185-1205`).
- EXECUTED (`base.py`): a tool raising a `ToolError` whose `__str__` raises `SystemExit`, a tool raising a `KeyError` whose `__str__` raises `KeyboardInterrupt`, and the same two from a gate: all four **escaped the frame host**.
- Only the embedder's own code can do this; no guest reaches it. It still breaks the rule as written, and the mutant "tool `BaseException` uncaught" (the tool's handler narrowed to `Exception`) survives the unit checks, so no check covers a tool's `BaseException` at all.
- Fix: `except BaseException` in both inner handlers and in `_fault`. After the rebase, consider using 032's `_described` (the type's own name, a `str` check, the first non-blank line), so the record's `fault` is the same text as 032's `FileFault`, as the Design says. Add a check with a tool raising `SystemExit` and one whose `__str__` raises.

### F4 — Low. The guest's encoder does not mirror the host's bounds

EXECUTED (`guest.txt`):
- Arguments nested 63 lists deep pass the guest's check and reach the host, which answers `protocol` ("the frame nests deeper than 64 levels"): the guest raises `ToolProtocolError`, not `ToolArgumentError`. `_encode` checks `depth > 62` on the value inside `args`, but `args` and the envelope add two levels, so the guest's bound is one too loose.
- An integer of 65 digits gets `ToolProtocolError`; one of 5,001 digits raises a bare `ValueError` from `json.dumps` (the guest's digit limit), not a `ToolError` at all.
- Decision 8 wants a `ToolArgumentError`, with no frame sent, for a value the protocol cannot carry.
- Fix: refuse at `depth >= 62` (or count from the frame), and refuse an `int` whose decimal form would exceed 64 characters, by magnitude, before `json.dumps`. Mutants "guest nesting unchecked" and "guest base64 non-strict" both survive: add checks for the nesting bound and for a non-strict `$bytes` answer.

### F5 — Low. Two edges of the catch-all and the recursion bound

- **The catch-all cannot turn a refusal into a success** (READ): it wraps `_answer`, every refusal returns before `invoke`, and it answers `ok: false`, kind `protocol`. But if spec 036's `invoke` raises after the work began, the record says `protocol` with `abandoned=False` and `op` and `tool` `None`, though the tool may have run. 036 should either never raise from `invoke`, or have the catch-all keep `op`, `tool` and an "unknown" for `abandoned`.
- **Validator recursion still depends on CPython's limit.** Vetting accepts any acyclic chain of same-value edges. EXECUTED (`misc.py`): a chain of 1,500 `$ref`s is vetted, and a call is answered `protocol` "(internal error)" with fault `RecursionError`. The validator's depth is the value's depth (62) times the longest same-value chain, so Decision 4's "no parser, validator or decoder recursion depends on the CPython version" holds only for short chains. Fix: in `_Vetting.no_cycle`, refuse a same-value path longer than a fixed bound (16 is far above pydantic's output), naming it.

### F6 — Low. Mutants that survive

EXECUTED (`mutants.txt`): 21 mutants, 16 killed. Survivors:
- **`uniqueItems` key not charged a step.** The budget check still passes, because the items' own visits exhaust it. Pin it with a schema whose items fail at once (`{"type": "array", "uniqueItems": true, "items": {"type": "integer"}}`, against 100,001 distinct strings).
- **A tool's `BaseException` narrowed to `Exception`** (F3).
- **The result's nesting bound removed** (the builder's choice, unchecked).
- **The guest's nesting check removed**, and **the guest's base64 made non-strict** (F4).

### F7 — Info. Notes that need no change before landing

- **`dataclasses.replace` makes a `Tool` that `tool()` never vetted** (EXECUTED, `misc.py`: a `pattern` schema went in). The landing notes' "a `Tool` cannot be built except by `tool()`" is too strong. Only the embedder can do it, and the validator ignores keywords it does not know, so no ReDoS follows. Say so, or make `_made` `init=False` and set it in `_make`.
- **numpy's `bool_` is not a `numbers.Integral`** (INFERRED; numpy was not on the host's Python here), so a tool returning `df["x"].any()` faults as "(internal error)". That follows Decision 6 as written. 036's README should say "return `bool(...)`".
- **`max_calls=None`** means no frame limit. It is private here; 036 should not expose it without saying so (§4.15: every limit has a default).
- **Benchmark facts** (EXECUTED, `fuzz_parse.txt`, 1 MiB frames): an unterminated string of escaped quotes 102 ms; 116,000 keys 80 ms (linear: 19, 38, 80 ms at 25k, 50k, 100k keys, `keys.py`); a float literal with a million-digit mantissa 12 ms; a million `[` 0.1 ms (the scan stops at 65). Nothing before the validator grows faster than the frame.

## The flagged questions, answered

1. **The snapshot start's +0.11 M fuel.** Located, not fully explained.
   - EXECUTED (`snapfuel.txt`, four heap perturbations each): `-c pass` grows +116,708 on average (+112,327 to +122,141). The same program ending in `os._exit(0)`, which skips `Py_FinalizeEx`, grows **−945**. So the start and the program cost nothing more, as Decision 9 predicted. All of the growth is in `Py_FinalizeEx`, after the program ends (READ, `reactor_main.c` `run()` calls it last).
   - The snapshot's zip directory has 1,933 entries against 1,930 (two files and the `host/` directory). Freeing that directory by hand costs only +14,618 more. A full collection, or unfreezing, costs nothing more (−326, −952, −910).
   - Clearing every module's dictionary by hand moved fuel by +68,262 and −107,512 under two paddings. So teardown's cost is sensitive to the frozen heap's layout, which every new member shifts (INFERRED). That fits spec 033's +0.07 M for 7 members, which is not proportional to members either.
   - **Decision:** not a blocker. Accept it with a reason that says where it is: in teardown, not in the start or the program. Amend Decision 9's cost line and criterion 14 in the disposition to say so. Spec 035 may change it; it need not wait.
2. **`_parse` is linear** on a 1 MiB frame: strict UTF-8, the token scan (one `finditer` match per character at most, checked by `test_the_nesting_scan_is_one_pass`), `json.loads` with its hooks (each hook sees one literal; `_unique_keys` is one `dict` plus one set pass only on a repeat), and `_decoded` (one pass; one regex search per string; strict base64). EXECUTED above. `_key` for `uniqueItems` is linear per key, but see F1 and F2.
3. **Is every validator path counted?** Visits, yes: `$ref` with siblings (a visit for the target, then the siblings at the same node), `anyOf` (stops at the first match), `oneOf` (every branch), and one step per `uniqueItems` key, made before the items are visited. Work inside a visit, no: F1.
4. **`_Vetting.no_cycle`.** No escape found. The validator stays on one value only through `$ref`, `anyOf` and `oneOf`, and those are exactly the edges the search walks; `properties`, `additionalProperties`, `items` and `prefixItems` are visited only for a container value and always move one level down (READ). `_plain` copies the schema, so aliasing cannot hide an edge, and a self-referential input dict is refused at depth 256 (READ). `_resolve` follows only dict keys, so a `$ref` cannot land in a list or on the root. The only gap is length, not cycles: F5.
5. **`_Work`.** Every exception from the gate, the tool and the encoder is caught, and only a `ToolError`'s own text crosses (EXECUTED, the unit checks; `str()` of a `str` subclass is unwrapped by `str.__str__` for results). The exception is an exception's `__str__` raising a `BaseException`: F3.
6. **The catch-all** cannot hide a refusal; see F5 for what it can misrecord in 036.
7. **Hostile answers to the guest** (EXECUTED, `guest.txt`): non-UTF-8, 100,000-deep JSON, a string `v`, `v: 2`, a wrong `id`, no `ok`, a dict `tools`, a keyword name, `__getattr__` as a name, two tools of one name, a dict `error`: each an `ImportError` naming why. Garbage schemas, a 900-deep default, a bad `$bytes` default and a 1 MB description all import, the bad schema as `(**kwargs)`. Bad and loose base64 in a result are `ToolProtocolError`; an unknown kind is a plain `ToolError`. No tool name can shadow a module global (every global is underscored; names must start with a letter).
8. **The ruff change** is sound and is a judge change: `_ruff` now passes `src tests recipes/guest` (READ), so the judge lints and formats the guest package. Listing the other recipe files one by one in `extend-exclude` only matters to a bare `ruff check`; a future top-level recipe `.py` would be linted there but not by the judge. Worth a comment in `pyproject.toml`; no change needed.
9. **The builder's choices** are judged below.

## The implementer's choices where the specification was silent

- **`PYTHONPATH` is not read.** Correct (READ, `PyConfig_InitIsolatedConfig`). Accept.
- **Bytes checked at every schema node.** Accept the rule; reject the way it is walked (F2). "A tool hinted `Any` cannot receive bytes" is right, and the README says "never where it says nothing".
- **The guest refuses any dict with a `"$bytes"` key.** Accept: the host would refuse a two-key one as `protocol` anyway, and the guest's error comes earlier and names it. Amend Decision 8's "only key" to match.
- **A result nested deeper than 62 levels is a fault.** Accept; add a check (F6).
- **A gate raising `ToolError` refuses with kind `denied`.** Accept: a gate only refuses.
- **Signatures through `_Hint`, `= ...` for an optional with no default.** Accept: the stubs and the guest agree across versions (EXECUTED, criterion 10's check).
- **Over the cap and past `max_calls`, the budget answer first.** Accept: it is Decision 5's order.
- Not listed, but chosen: **`max_calls=None` is unlimited** (F7), and **`minLength` and `maxLength` count bytes for a bytes value**. Both fine.

## Security, against the threat model

The adversary is the guest: arbitrary Python, every preview1 call, the door, and what the embedder granted (threat model §2). The tools, the gate and the schemas are the embedder's code and data; they are judged for robustness only.

- **No new import (§4.4).** `python.wasm` is byte-identical to main's frozen set (EXECUTED), so its imports and exports are unchanged. The protocol rides the one door, as the amended §4.4 allows.
- **Forged frames.** The guest can bypass the package and write frames itself through `_host.call`. Every rule is on the host side, before any gate or tool (READ; EXECUTED, criterion 12's check and `fuzz_parse.txt`: 41 hostile frames, no tool or gate ran, every answer ASCII JSON, nothing raised).
- **What crosses back.** Only a `ToolError`'s text, cut to 4,096, and guest text echoed cut to 64 (EXECUTED, criteria 7 and 8; mutant "echo not cut" killed). A host path in a `KeyError` stays in the record (EXECUTED, criterion 7).
- **CPU on the door's thread (asset 5).** This is where the build falls short: F1 (a valid frame that costs seconds, uncounted) and, behind it, the per-visit costs F2 currently hides. C1's intent, a bound that is a count and so the same on every host, holds for visits but not for work.
- **Memory (asset 5).** A frame is at most 1 MiB; its parse, copy for the gate and keys are linear in it. The record keeps at most 1,000 outcomes with bounded text (EXECUTED, criterion 8; mutant "record unbounded" killed).
- **Integrity of the result (asset 4).** A refused call never reaches the tool, and the record lists every refusal. F5 notes the one way 036 could misrecord.
- **The guest package** runs with the guest's privileges only; a hostile host answer can only make the guest's own call fail (EXECUTED, question 7).

## Each Decision against the code

1. **One protocol, two halves.** Holds (READ; EXECUTED, `python.wasm` unchanged; `test_importing_the_package_does_not_load_the_tools`).
2. **The decorator.** Holds (READ; EXECUTED, criteria 1 to 3). See F7 for `replace`.
3. **The subset and the validator.** The keywords, the strict types and equality, the one-pass `uniqueItems` and the `$bytes` rule hold (EXECUTED, the 85-row table, mutants). The budget holds for visits only (F1), and "about one visit per JSON value" does not hold (F2).
4. **The frame rules.** Hold, in order, and linear (EXECUTED, `fuzz_parse.txt`; mutants on duplicate keys, nesting, surrogate keys and strict base64 killed). Recursion is bounded for the parser and decoder; for the validator see F5.
5. **The fixed order, `admit` and the handshake.** Hold (EXECUTED, criteria 5 and 6; mutants "pending not checked" and "gate gets the tool's args" killed).
6. **Errors and chosen text.** Hold, except F3.
7. **Protocol 1.** Holds (READ; EXECUTED, `id` and `v` cases; mutant "id bool echoed" killed).
8. **The guest side.** Holds, except F4.
9. **The zip and its cost.** The zip holds the two `.pyc` (EXECUTED, criterion 13). The plain start's cost is as predicted. The snapshot's start costs nothing more; its teardown does (question 1).
10. **Stubs.** Hold (EXECUTED, criterion 10).
11. **Async refused.** Holds (EXECUTED, criterion 2's case).
12. **Docs.** The README section is accurate except the budget's basis (F2). The CHANGELOG entry is accurate.

## Acceptance criteria against evidence

| # | criterion | evidence | holds |
|---|---|---|---|
| 1 | described by hints and docstring | EXECUTED, passes | yes |
| 2 | refusals name the parameter | EXECUTED, 26 cases; mutants "no cycle check", "lax lets $ref remote" killed | yes |
| 3 | a vetted schema cannot change | EXECUTED, passes | yes (F7: `replace`) |
| 4 | no coercion; the budget | EXECUTED, passes; mutant "anyOf tries all" killed, "item key uncounted" survives | yes as written; F1, F2, F6 |
| 5 | the frame rules | EXECUTED, passes; `fuzz_parse.txt` | yes |
| 6 | the gate decides after validation | EXECUTED, passes | yes |
| 7 | only chosen text crosses | EXECUTED, passes | yes, except F3 |
| 8 | the record is bounded | EXECUTED, passes | yes |
| 9 | the guest speaks the host's protocol | EXECUTED, passes | yes, except F4 |
| 10 | stubs match the guest | EXECUTED, passes | yes |
| 11 | round trip through the door, both binaries | EXECUTED, full judge | yes |
| 12 | a forged frame is validated first | EXECUTED, full judge | yes |
| 13 | the zip carries the package | EXECUTED, full judge, with `test_manifest_recipes_match_the_tree` | yes |
| 14 | green with `--accept-judge`; growth accepted; nothing else grows | EXECUTED: red only for growth; the snapshot growth is outside Decision 9's prediction | with the amended reason (question 1) |
| 15 | a release dry run | not run (needs a push); the lane's | open |

## Constitution checks

- §4.1, §4.2: no patch, no new input. Holds (READ).
- §4.4: no new import; the one protocol over the door. Holds (EXECUTED, binary unchanged).
- §4.5: no embedder named (EXECUTED, `grep` for embedder names in the new files: none).
- §4.6: the zip and the snapshot change; `MANIFEST` records the two recipe files. Holds.
- §4.9: the new checks count; none reads a clock (EXECUTED, `test_no_test_reads_a_clock`). This review's times are benchmark facts, labelled.
- §4.10: the landing notes' numbers reproduced (the scoreboard, the hashes, the growth).
- §4.13: no dependency added; ruff green on `src`, `tests` and `recipes/guest`.
- §4.15: no channel opens without the embedder's tools; `max_calls` has a default (F7 for 036).
- §5.6: reviewed before build, confirmed with conditions; C1 is only partly met (F1, F2).
- §5.7: build-class; the branch must be rebased onto `987012e` before the lane judges it, and three files overlap.

## Disposition (filled in by the author, then confirmed by the reviewer)

Filled in by the builder, 2026-10-18. The revision is commit `7a587ad` on `spec/031-a-tool-protocol-over-the-door`, rebased onto `3b9c9c1` (the conflict in `test_v1_4_embedding.py` was two appends, both kept). The spec's Landing notes, "Revision after the build review", hold the numbers.

- **F1: fixed.**
  - Each `enum` and `const` is a `frozenset` of keys, made once by `tool()` (`Tool._keysets`), so a check is one key and one lookup. A schema no `tool()` vetted builds its set on first use, charged.
  - `_key` charges one step for each value below the one it keys; a `uniqueItems` key costs one more for its item.
  - `_shown` and `_echo` name a non-string value by its kind and size; nothing is `json.dumps`ed for a message.
  - The checks: `test_an_enum_costs_one_key_per_value` (your 600-name, 99,990-item frame now answers `ok` with at most 99,990 + 10 key builds, by a counting `_key`; a `const` against 100,000 values is "too complex") and `test_messages_never_format_a_whole_value`. Both failed against `d58f2a4`'s code, loaded in place of the new one.
- **F2: fixed, as you proposed.** A node with `$ref`, `anyOf` or `oneOf` walks a container's children only when it also carries a keyword about them. The schema it delegates to walks them, so the bytes rule holds.
  - `test_valid_arguments_cost_about_one_step_per_value`, with a stated bound per shape:

    | shape | steps per value | bound |
    |---|---|---|
    | order, 5,000 lines | 1.43 | 1.5 |
    | tree 20 deep, 5,000 leaves | 2.33 | 2.5 |
    | tree 60 deep | 2.28 | 2.5 |
    | your recursive union, 60 deep | 2.06 | 2.5 |

  - All four cases failed against the old code.
  - The tree costs 2.3, not "about two", because its `Optional` parent tries `$ref` before `null`.
  - A 10,000-line order is about 100,000 steps and is still refused. Decision 3 and the README now state the per-node rule and say a call over about 50,000 values is bulk data.
- **F3: fixed.**
  - `_fault` is 032's `_described` text (the type's own name, a `str` check, the first line), made total over `BaseException`.
  - Both inner handlers catch `BaseException`, and `_message_of` gives a plain `str`.
  - `test_a_base_exception_never_escapes_the_frame_host` has 8 cases (`SystemExit`, Ctrl-C, a `__str__` raising either, from a tool and from a gate). Against the old code, the Ctrl-C `__str__` case escaped and aborted the pytest session.
- **F4: fixed.**
  - The guest refuses a container or bytes at depth 62 or more inside an argument, and an integer outside `-(10**63) < n < 10**64`. Both are `ToolArgumentError`, before `json.dumps`, with no frame sent.
  - Checks: `test_the_guest_refuses_what_the_host_would_refuse_as_protocol` and `test_a_loose_bytes_answer_is_a_protocol_error`. `"QR=="` is left out of the latter: strict mode accepts it on both halves alike.
  - Rebuilt from step 70; the new `SHA256SUMS` is in the landing notes (zip `ee1acace…`, snapshot `0cdc7b2b…`, `python.wasm` unchanged).
- **F5: fixed for the recursion; the catch-all point left to 036's builder.**
  - `tool()` refuses a same-value chain of more than `SAME_VALUE_CHAIN` = 8 schema nodes, naming it. The check, `test_a_long_same_value_chain_is_refused`, refuses 1,500 nodes and 9 and accepts 7. Decision 4 says so.
  - The point about 036's `invoke` (never raise, or keep `op`, `tool` and an unknown `abandoned`) is not written into 036's spec: this branch carries one specification. 036's builder should take it from here.
- **F6: fixed.**
  - Your 21 mutants, adapted to the new code, plus 10 for the new mechanisms: all 31 are killed.
  - My first run left two survivors (the key charge removed; arrays walked at every delegating node). The `const` and recursive-union cases were sharpened until both were killed.
  - Added `test_unique_item_keys_are_charged` and `test_a_result_nested_too_deep_is_a_fault`.
- **F7: fixed and noted.**
  - `Tool`'s guard is a context variable that only `tool()` sets, so `dataclasses.replace` raises `TypeError` (`test_only_tool_makes_a_tool`).
  - The `bool_` and `max_calls=None` notes are in the landing notes, for 036.
  - Decision 8 is amended for the guest's `"$bytes"` rule, and `pyproject.toml` gains your question 8's comment.
- **Question 1: accepted as teardown.**
  - Re-measured on the revised set, five perturbations: `-c pass` on the snapshot is +110,800; `os._exit(0)` is −989. A plain start is +155,809, and +151,746 under `os._exit(0)`.
  - Decision 9's cost line and criterion 14 are amended to say the snapshot's +0.11 M is in `Py_FinalizeEx`.
  - The landing notes carry your growth reason, re-measured: zip +12,963 bytes, snapshot +4,197, `os._exit` −989.
- **The judge** (worktree, its own artifacts, no flags): `223/227 pass · 0 gap · 4 blocked · 0 fail` (unit suite 812/819); lost 0, gained 4, grew 40; red only for growth. Ruff is clean on `src tests recipes/guest`.

## Verdict

**Not ready to land; fix F1 and F2 first.** Both are in the validator and small. F1 lets a guest hold the door's thread for seconds per valid frame with a plain derived `Literal`, which C1 was written to stop. F2 refuses valid recursive pydantic arguments of about 10,000 values and makes the README's budget basis untrue. Fixing F2 alone would make F1's other per-visit costs unbounded, so fix them together, with counted checks seen failing first. F3 to F6 are low: fix them or answer them in the disposition. Then a short confirmation, a rebuild from step 70 if the guest package changes (F4), and the judge re-run on the rebased commit.

The snapshot's growth (question 1) does not block. When this lands, the lane should use, with the numbers re-measured on the final set:

`--accept-growth "spec 031: the zip gains 2 members (+12,613 bytes) and the snapshot +4,170 bytes; python.wasm unchanged; a plain start +~0.16 M fuel from reading 2 more zip members, as Decision 9 predicted; a snapshot start +~0.11 M, all of it in Py_FinalizeEx after the program (an os._exit(0) run differs by -945), not in the start or the program; heavy jobs move within +-2.2 M, heap-layout noise as in spec 033's acceptance"`

## One line

The protocol, its frame rules and its guest package are right and linear, but the validator's budget counts visits, not work: an `enum` costs its whole list per value and wrappers re-walk their values, so fix F1 and F2 together before landing; the snapshot's +0.11 M is teardown and can be accepted.

## Confirmation (2026-10-18)

- **Reviewed:** commit `7a587ad` on `spec/031-a-tool-protocol-over-the-door`, rebased onto `3b9c9c1` (main with this review), against the Disposition above. I read the diff `2788f49..7a587ad` of `src/wasi_python/tools.py`, `recipes/guest/host/tools.py` and `pyproject.toml`, and the amended Decision 9, criterion 14 and landing notes. Scripts and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev031b/` (and the first round's scripts, rerun, in `rev031/`).
- **The judge** (EXECUTED, `uv run pytest` in the worktree, no flags, its own artifacts; every `SHA256SUMS` line OK, and they equal the landing notes': zip `ee1acace…`, snapshot `0cdc7b2b…`, `python.wasm` `4befe9de…` unchanged): `223/227 pass · 0 gap · 4 blocked · 0 fail (unit suite 812/819)`, `lost 0 · gained 4 · grew 40`, red only for growth, 1035 passed. `git status` clean after.

### Each disposition against its finding

- **F1: confirmed fixed.** EXECUTED (`enum_cost.py`): the 600-name, 99,990-item frame answers `ok` with **99,990 calls of `_key`** (was 60,093,990); as a benchmark fact, 0.14 s for a 600- or a 2,000-value `Literal` (was 5.15 s and 17.78 s). `cost.py`: cases B and C make at most one key call per counted step, and no message is formatted from a whole value (0 characters, was 1,238,010). READ: `_key` charges one step per value below the one keyed; `_shown` names a container by kind and size. But see N1: the key sets are keyed by `id()`.
- **F2: confirmed fixed.** EXECUTED (`walk.py`): the order is 1.43 steps per value; the recursive tree is 1.50 at depth 5, 20 and 40 (was 7.97, 22.65, 41.76); the 10,064-value tree now passes (15,085 steps). A 70,002-value order is still "too complex", as the amended Decision 3 and README say (about 50,000 values). READ: a delegating node walks children only when it also carries a keyword about them, so the bytes rule still holds.
- **F3: confirmed fixed.** EXECUTED (`base.py`): all four cases that escaped are now answered (`tool_error` "(internal error)" and `denied` "was refused"). `_fault` is 032's `_described`, total over `BaseException` (READ).
- **F4: confirmed fixed.** EXECUTED (`guest.py`): 63 nested lists and integers of 65 and 5,001 digits are each `ToolArgumentError` with no frame; 62 levels and 64 digits pass. The 19 hostile answers behave as before.
- **F5: confirmed for the recursion.** EXECUTED (`misc.py`): the 1,500-`$ref` chain is refused by `tool()`, naming the bound. A bound of 8 nodes is above what pydantic emits (an `Optional` union through an alias is 5; INFERRED). The catch-all point is left to 036's builder; I agree, and it should go into 036's pre-build notes.
- **F6: confirmed.** EXECUTED (`mutants.txt`): my 21 mutants adapted, plus 10 for the new mechanisms (an uncharged linear `enum` scan, no key charge, delegating nodes walking objects and arrays, `_shown` dumping whole, the two `BaseException` narrowings, the chain bound, the guest's integer bound, the `Tool` guard): **31 of 31 killed**. Narrowing `_described` to `Exception` kills the session (a `KeyboardInterrupt` escapes), which counts as killed. `git diff` empty after.
- **F7: confirmed.** EXECUTED: `dataclasses.replace`, `copy.replace` and a direct `Tool(...)` each raise `TypeError`.
- **Question 1: confirmed.** EXECUTED (`snapfuel.txt`, five perturbations, main's frozen set against the revised set): snapshot `-c pass` +110,800 (min +87,167, max +122,141), `os._exit(0)` −989; plain `pass` +155,809, `os._exit(0)` +151,746. These are the landing notes' numbers exactly. The amended Decision 9 and criterion 14 say what I found: the start and the program pay nothing; teardown pays; the per-member reading is labelled INFERRED.
- **The frame rules** (EXECUTED, `fuzz_parse.txt`): the 41 hostile frames give the same outcomes as before, and the 1 MiB shapes stay linear.

### New finding

**N1 — Medium. The `enum` and `const` key sets are keyed by `id()`, so a `Tool` that is pickled or deep-copied can check a value against another node's set.**
- `Tool._keysets` maps `(id(node), word)` to a frozenset, and the validator looks a node up by `id(s)` (READ, `_keysets`, `_Validator.keyset`). The ids are only valid for the schema objects that were alive when `tool()` ran.
- After `copy.deepcopy` or a pickle round trip, every entry is stale (EXECUTED, `pickled.py`: 2 of 2). That alone is safe: a lookup misses and the set is rebuilt, charged.
- But when the original `Tool` is freed before `pickle.loads`, the new schema's dicts reuse the freed ids, and a node finds **another** node's set. EXECUTED (`pickled2.py`, `pickled3.py`): a tool with 30 single-value `enum` properties, unpickled in the same process after the original was freed. Collisions happened in 200 of 200 round trips. Through the frame host, 20 round trips **accepted 117 values the schema forbids** (for example `p4` given `v18`), and refused valid ones.
- Only the embedder can pickle a `Tool`, so a guest cannot cause it. But an `enum` is often an allow-list a capability relies on (`table: Literal["public_a", "public_b"]`), and the failure is silent. Pickling tools to a worker, or caching them, is ordinary embedder code.
- Fix (`src/` only; the artifact set does not change): keep the node with its set, `(node, frozenset)`, and use the entry only when `entry[0] is s`; or drop `_keysets` from the `Tool`'s pickled and copied state. Add a check: a `Tool` pickled, the original freed, then unpickled, refuses another property's value. Seen failing first against `7a587ad`.

### Verdict

**031 lands once N1 is fixed.** Everything from the first round is fixed and confirmed. N1 is new, small, host-side only and needs no rebuild. The lane checks that the fix is the one named, with its check seen failing first against `7a587ad`, and that the diff touches only `src/wasi_python/tools.py` and `tests/unit/test_tools.py`. It needs no further review round. Then it judges the exact commit in the main tree with `--accept-judge` (the new and changed check files and ruff's paths) and this growth reason, which is the landing notes' re-measured text and which I reproduced:

`--accept-growth "spec 031: the zip gains 2 members (+12,963 bytes) and the snapshot +4,197 bytes; python.wasm unchanged; a plain start +~0.16 M fuel from reading 2 more zip members, as Decision 9 predicted; a snapshot start +~0.11 M, all of it in Py_FinalizeEx after the program (an os._exit(0) run differs by -989), not in the start or the program (Decision 9 and criterion 14 as amended); heavy jobs move within +-2.2 M, heap-layout noise as in spec 033's acceptance"`

Criterion 15 (the release dry run) stays the lane's, on the reviewed commit.

### One line

Every finding is fixed and confirmed (31 of 31 mutants killed; 99,990 key builds instead of 60 million; 1.5 steps per value), and the snapshot's growth is teardown. One new bug blocks: the key sets are keyed by `id()`, which an unpickled `Tool` can mismatch. Fix that host-side, then land.
