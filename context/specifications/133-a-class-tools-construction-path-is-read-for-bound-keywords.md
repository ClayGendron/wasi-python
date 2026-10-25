# 133: a class tool's construction path is read for bound keywords

- **Status:** **Reviewed before build 2026-10-25** (`../reviews/133-a-class-tools-construction-path-is-read-for-bound-keywords-spec-2026-10-25.md`, "Fit to build once Decision 3 is bounded to the names a frame could send at the arguments' top level, with a row showing a nested property of the same name is still accepted"): finding 1 fixed in Decision 3, the Lows applied in the Disposition (Decisions 1, 3 and 4, the Intent, the documentation sentence and the CHANGELOG line). Before: **drafted 2026-10-25** from the 0.1.0 security audit (`../reviews/0.1.0-security-audit-2026-10-25.md`, finding F2), on main `2cd47507`'s code. Not for build until its pre-build review (runner code, a security fix). Its rows are to be written first and seen failing on main's code (Decision 4).
- **Date:** 2026-10-25
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural**: `src/wasi_python/tools.py` (`_bound_keywords` and `_given`), rows in `tests/checks/test_v1_4_embedding.py` beside `test_bound_keywords_are_fixed_however_the_partial_is_reached`, `docs/how-to/tools.md` (one sentence on bound keywords), `CHANGELOG.md`. No `scripts/`, `recipes/`, pins, workflow or artifact byte. It **tightens** a default: a registration accepted today is refused or its keyword fixed.
- **Depends on:** 110 (tools behind its facade), landed. Nothing in flight touches `tools.py`.
- **Research it stands on:** the audit's F2 (`0.1.0-security-audit-2026-10-25/FINDINGS-DETAIL.md` §2; fingerprint `src/wasi_python/tools.py:_bound_keywords:class-construction-partial-unfixed`), reproduced by hunter h06, verifier v02 and record verifier r03 through the real door, frame host and gate (`agents/h06-tools/artifacts/evidence/`, `agents/v02-class-partial/`); h06's note on `_given` and `$ref`.

## The problem

`tool()` promises that a keyword a `functools.partial` binds is **fixed**: left out of the derived schema, refused when a given schema names it (`_given`, `tools.py:418-423`), and refused in a frame (`_tool_host.py:1003-1009`), so the guest neither reads its value nor sets it. The gate's `ToolCall.arguments` never holds one.

`_bound_keywords` (`tools.py:439-474`) finds partials wherever `inspect.signature` meets one: the partial itself, nested partials, a bound method's function, a `__wrapped__` chain, a callable object's `__call__`. For a **class**, it reads `type(cls).__call__`, meets `type.__call__`, a C slot, and returns with nothing found (`tools.py:466-470`). It never reads the class's own `__new__` or `__init__`, which is where `type.__call__` and `inspect.signature` both go. So for a class whose constructor binds a keyword with a partial, `Tool._fixed` is empty, `_given` accepts a schema that names the keyword, and the frame refusal never fires.

**Reproduced** (EXECUTED by v02 and r03, Python 3.14.2): three class tools, each binding `role="viewer"`, under an explicit schema naming `role`: `__init__` a `functools.partialmethod`; `__init__` a `functools.partial` (a method descriptor on 3.14); `__new__` a `staticmethod` over a `functools.partial`. A frame with `role="admin"` was answered `ok`; the gate received `{"q": "x", "role": "admin"}`; each constructor ran with `role="admin"`. `Tool._fixed` was empty for all three and `inspect.signature` showed `(q, *, role='viewer')`. In the same run a plain partial's `user_id` was refused at `tool()` and per frame (`unknown argument 'user_id'`), and a callable instance whose `__call__` is a `partialmethod` was refused at `tool()`. Only the class construction path is unguarded.

**Who it reaches.** An embedder that registers a class as a tool with authority bound this way and an explicit schema that leaves the keyword open (no `properties`, `additionalProperties` not false, or the keyword listed). A derived schema is unreachable: `tool()` refuses a class without hints. Low likelihood; where it is used, untrusted guest code replaces an authority value the embedder bound and the gate sees arguments the documentation says it never holds.

**Beside it** (h06): `_given` checks bound keywords against the root `properties` only. A schema whose root `anyOf` or `oneOf` branch names a bound keyword, directly or through a `$ref` into the schema's own `$defs`, is accepted at `tool()` and refused only frame by frame. That is fail-closed, but late. (A root `$ref` is already refused at `tool()` by `_vet`, whose root must be an object schema.)

## Decisions

### 1. The construction path is read as `type.__call__` runs it

When `_bound_keywords`' target is a class (`isinstance(target, type)`), the walk does not stop at the metaclass's `__call__`. It reads the class's construction path with `inspect.getattr_static` through the MRO: `__new__` and `__init__`, each unwrapped through `staticmethod` and `classmethod` (`__func__`), and then walks **each** with the same loop the function already has (partial keywords collected, nested partials, `__wrapped__`, a bound `partialmethod` through an instance). A `functools.partialmethod` met on the construction path is read as its `.func` plus its `.keywords`, not refused: on a class it is reached only through an instance, which is exactly the case the existing refusal exempts. `object.__new__` and `object.__init__` are C slots and contribute nothing, as today.

The read is done **whatever the metaclass's `__call__`**: a Python metaclass whose `__call__` delegates to `super().__call__()` still runs `__init__` with the guest's keywords (v02 EXECUTED: the hunter's narrower patch returned nothing for such a class). The metaclass's own `__call__` is still walked too, as today, so a partial bound there stays fixed.

The walk keeps one worklist and one budget of `_WRAPPER_DEPTH` steps across all its branches, so a construction path that names a class, or itself, ends in today's `TypeError` ("its wrappers nest deeper"), never a `RecursionError`.

### 2. The alternative, and why it is not taken

Refusing at `tool()` any class whose `__new__` or `__init__` is a partial or `partialmethod` would be shorter and fail closed. It is not taken: a plain partial on a function is the documented way to bind authority, a class is the natural shape for a tool with state, and the existing message for an unbound `partialmethod` already tells an embedder to "bind its keywords with a closure or a functools.partial", which on a class means exactly the construction path. The fixed-keyword contract is kept for the class as for the function. If the pre-build review finds the walk's cases too many for one function under 80 lines, the refusal is the fallback and this decision is revised.

### 3. `_given` checks every name a frame could send

`_given` collects the names a frame could send at the arguments' top level: the root's `properties`, the `properties` of each root `anyOf` and `oneOf` branch, and of a branch's `$ref` target in the schema's own `$defs` or `definitions`, through branches of branches. It never enters a property's own schema, `items` or `additionalProperties`: a key of the same name there belongs to another object. A schema that names a fixed keyword among those names is refused at registration. `allOf`, and every keyword `validates_input=True` admits outside the subset, is left to the frame refusal, which reads the top-level keys whatever the schema. The walk keeps the set of `$ref` targets it has entered, so a cycle, which `_vet` then refuses, is walked once. The frame refusal stays as the second check. The message is today's.

### 4. The rows first

In `tests/checks/test_v1_4_embedding.py`, beside `test_bound_keywords_are_fixed_however_the_partial_is_reached` (line 3517):

1. **Three class shapes** (a `partialmethod` `__init__`; a `partial` `__init__`; a `staticmethod` over a `partial` as `__new__`), and two more shapes: a subclass with no `__init__` of its own over a base whose `__init__` is a `partialmethod`, and an `__init__` that is a `functools.wraps` wrapper over a `partial`; and a class reached through a `partial` over it. Each binds a keyword, each registered twice: under an open schema, and under a schema that names the keyword. The second registration raises `ValueError` at `tool()` (the message `_given` gives today). Under the open schema a frame naming the keyword is answered `invalid_arguments` with **neither the gate nor the constructor called**, and the gate's `arguments` for a frame without it hold no bound keyword. Seen failing first on main's code: today the audit's three answer `ok` with the guest's value, and `_bound_keywords` returns `frozenset()` for the two more shapes (EXECUTED in the pre-build review).
2. **A Python metaclass** whose `__call__` delegates to `super().__call__()`, with a `partialmethod` `__init__`: the same verdicts.
3. **The published signature:** `Tool.input_schema` for a class tool with an explicit schema is the schema as given, the fixed keyword absent; the derived case is still refused for lack of hints.
4. **`_given` through `anyOf`, `oneOf` and a `$ref` from a root branch:** a schema naming a fixed keyword in a root `anyOf` branch, in a root `oneOf` branch, and in a `$defs` target a root `anyOf` branch points to, each refused at `tool()` with `ValueError` matching `which the partial binds`; today each is accepted (EXECUTED in the pre-build review).
   - **Row 4b, a nested property of the same name:** a schema whose nested object (inline, and through `$defs`) has a property named like the fixed keyword is accepted, and a frame setting it there is answered `ok` with the bound value intact; green today and after.
5. **The existing rows are unchanged** (the plain partial, the nested partials, the `__wrapped__` chain, the bound `partialmethod`, the unbound `partialmethod` refused).

## Intent

After this specification, a keyword bound on a tool's construction path is as fixed as one bound on a function: a class tool's `__new__` and `__init__` are read as the interpreter runs them, through static attribute lookup and the `staticmethod` and `classmethod` wrappers, and every partial met there is recorded in `Tool._fixed`. A given schema that names a fixed keyword among the names a frame could send at the arguments' top level is refused at registration, and a frame that names one is refused before the gate or the tool runs. The embedder's authority value is the only one the constructor sees. What a Python metaclass `__call__` or `__new__` does in its body, such as building the instance through a factory or a subclass, is not read, as a function's body is not; a keyword bound that way is the embedder's to keep from the guest, by a closure.

## Design

- `src/wasi_python/tools.py`: `_bound_keywords` reads a class's construction path (Decision 1); `_given` collects the names a frame could send at the arguments' top level (Decision 3); comments give the reasons in words.
- `tests/checks/test_v1_4_embedding.py`: the rows of Decision 4, first, beside the existing bound-keyword check.
- `docs/how-to/tools.md` (one sentence), `CHANGELOG.md`.
- The commits, in order: the specification with its roadmap line and the rows seen failing; the construction-path walk; `_given`; the documents.

## Scope

In: Decisions 1, 3 and 4; `docs/how-to/tools.md` gains, after "a frame that names it is refused.": "So is a keyword a `partial` or `partialmethod` binds on the `__init__` or `__new__` of a class registered as a tool."; the CHANGELOG line. Out: Decision 2's refusal (the fallback); any change to the frame protocol or the gate's contract.

## Acceptance criteria

1. The rows of Decision 4 green on three systems, rows 1, 2 and 4 seen failing first and row 4b green before and after on `2cd47507`'s code (output in `build/133/`).
2. `_bound_keywords` and `_given` each under 80 lines; `tools.py` under its ceiling; `tests/public_api.txt` unchanged; `ruff`, `mypy` clean; no code file names a specification, review or finding.
3. The audit's reproduction (`0.1.0-security-audit-2026-10-25/agents/v02-class-partial/scratch/`, its driver copied into `build/133/`) answers `invalid_arguments` for all three shapes on the built tip.
4. The CHANGELOG line under the unreleased section: "A class registered as a tool whose constructor binds a keyword with a `functools.partial` or `partialmethod` now has that keyword fixed, as a function's is: a frame naming it is refused and a given schema naming it is refused at registration. A given schema that names a bound keyword in an `anyOf` or `oneOf` branch is now refused at registration, as one naming it in `properties` already was."
5. The release workflow dispatched on the built tip, its Windows legs read.

## For the lane

- **Kind:** parallel-safe; next wave; shares `CHANGELOG.md`, `context/roadmap.md` and `tests/checks/test_v1_4_embedding.py` (appended rows) with others.
- **Claim list** ("133:"): new rows of Decision 4; retired none; lost passes none; fuel and bytes none. Judge hash changes in `test_v1_4_embedding.py`.
- **Flags:** `--accept "133: a class tool's construction path (__new__, __init__, through staticmethod and classmethod) is read for partial-bound keywords, which are fixed as a function's are; a given schema naming a fixed keyword among the arguments' top-level names, through anyOf and oneOf branches and their $ref targets, is refused at registration"`, `--accept-judge "133: rows for the class shapes (three, an inherited partialmethod __init__, a functools.wraps __init__, a partial over a class), a delegating metaclass, schemas naming a fixed keyword through anyOf, oneOf and a $ref from a root branch, and a nested property of the same name still accepted; no existing expectation edited"`.

## Landing notes

Not yet built. The builder fills this section: the commits, the checks seen failing on main's code first, the fast tier, the branch's release run (its id, every line green on three systems, no growth line), the self-check list (`../reviews/README.md`), and the rebase onto the wave's tip with every conflict named.

## One line

A tool class's `__new__` and `__init__` are read for the keywords a partial binds, so a guest can no longer set a role the embedder fixed on the constructor.
