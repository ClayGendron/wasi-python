# 056 — The 0.1.0a4 security review's findings

- **Status:** built 2026-10-18; awaiting confirmation by the a4 security reviewer. Built on
  `spec/056-the-a4-security-reviews-findings` from main `28800bc` (Landing notes). It changes
  neither the guest's imports nor its exports, the artifact set nor the build recipe, so §5.6
  asks no review before build. The reviewer who wrote the 0.1.0a4 security review confirms the
  fixes, and the release waits on that confirmation (§5.6, "the release waits on its
  findings").
- **Owner:** Clay Gendron
- **Kind:** runner and docs; not build-class; a judge change (new checks). The frame host in
  `src/wasi_python/tools.py` (`tool()`'s `_make` and `_derived`, a new `_bound_keywords`, the
  private `Tool._fixed`, `_ToolHost._answer`, `_Work`, `_Bounded._proceed`), judge additions in
  `tests/checks/test_v1_4_embedding.py`, `tests/unit/test_runner_tools.py` and
  `tests/unit/test_tools.py`, `README.md`, `CHANGELOG.md`. It touches no `scripts/`,
  `recipes/`, `downloads/SHA256SUMS` or workflow. No public name or signature changes, so spec
  049 (the public API frozen, built beside it) rebases over it with local conflicts only.
- **Depends on:** 031 (the tool protocol, `tool()`, the frame host) and 036 (tools in the
  runner, the bounded invoke), both landed; 032 and 034 (mounts, for F5's text), landed.
- **Research it stands on:** the 0.1.0a4 security review,
  `build/reviews-evidence/a4-security/0.1.0a4-security-review-2026-10-18.md` in the main tree
  (git-ignored), its probes `probes/p08_tools_partial_and_late_gate.py` and
  `tools-probes/p1_partial.py`, `p4b_cpu_notrace.py`, `p5_flood.py`, `p6_flood_profile.py` and
  `p8_late_gate.py`, with their logs. Its verdict: "0.1.0a4 may be released once F1 is fixed"; F2
  "should ride along"; F3, F4, F5 and the notes "should each be answered in writing or
  scheduled". This specification answers each.

## The problem

The review found the sandbox, the mounts and the wasmtime guards hold. It found five things in
the new surfaces (READ, the review; each EXECUTED there):

- **F1 (high, blocks a4).** `tool(functools.partial(orders, user_id=42, api_key="sk-live-…"),
  name="my_orders")` publishes both bound keywords as optional parameters whose `default` is the
  bound value. The guest reads the key from its descriptor and its signature, and calls
  `my_orders(user_id=7)` as any user. A partial's keywords can be overridden by its caller, so
  the frame host passes the guest's value straight through.
- **F2 (medium).** The gate and the tool run in one piece of work on the tool's thread. When the
  call times out or is cancelled, the bound answers the guest and marks the call abandoned, but
  nothing checks that mark between the gate's yes and the tool. A slow gate (a human approval)
  that says yes after `run` returned still runs `transfer(amount)`.
- **F3 (medium-low).** Each admitted frame, up to 1 MiB, is parsed and validated in Python on the
  door's thread: 0.27 to 0.65 s of host CPU per frame on the review's Mac, for about 1,400 fuel to
  re-send. The per-run total is bounded only by `max_tool_calls` (1,000) and the deadline.
- **F4 (low).** The release workflow's later jobs download the build's artifact by name and never
  check it against the build job's digest.
- **F5 (low, docs).** A mount provider receives `\`, `:` and Windows device names as the guest
  wrote them; the README calls paths "normalized" and does not warn a provider backed by a host
  folder.

And seven notes, N1 to N7, each "no finding, or as designed": the download step's
`--ignore-missing`; wasmtime 49.0.0 admitted, with the runner's guards in its place; the release
path's human controls; `ToolCall.arguments` without defaults; no process-wide ceiling on
abandoned tool threads; write amplification and a blocking provider; `artifact_dir()`'s
preference for a checkout.

## Decisions

1. **A keyword a `functools.partial` binds is fixed (F1).** Not refused.
   - **Fixed** means: it is left out of the derived schema, so neither the descriptor, the guest's
     signature nor `stubs()` names it or holds its value; a frame that names it is answered
     `invalid_arguments`; the tool is called with the bound value, always.
   - **Why fixed, not refused.** The review offered both, and both close F1. Fixed is what
     `partial` means to the embedder who writes it: "this argument is decided". It is already how
     a positionally bound argument behaves (`inspect.signature` drops it). The README tells
     embedders to "pass capabilities", and `partial` is the usual idiom for a capability, as a
     closure is. Refusing it would turn a working idiom into an error and push embedders to
     closures for no extra safety. A side effect, allowed: a bound value need not have a JSON
     form, so a partial may bind a database connection, which `tool()` refused before (its hint
     did not map).
   - **Where a partial is found.** `_bound_keywords` walks what `inspect.signature` may walk on
     its way to the function: a partial (its `keywords`, then its `func`), nested partials, a
     bound method's `__func__`, a `__wrapped__` chain (`functools.wraps`), and once a callable
     object's `type(obj).__call__`. It collects every bound keyword it meets. It collects even
     past an object with its own `__signature__`: over-collecting only hides a name or refuses a
     frame, never shows a value. The walk stops at 64 links; a longer one (a `__wrapped__` cycle)
     is refused with `TypeError`.
   - **`functools.partialmethod`.** Through an instance (`obj.method`) Python hands over a
     partial, which the walk covers. Met any other way (the class attribute `Cls.method`, whose
     signature mixes the instance in; a `partialmethod` over a non-descriptor), `tool()` refuses
     it with `TypeError`, naming `obj.method`, a closure or a partial instead. These are rare, and
     a refusal is the tighter default (§4.15).
   - **A given `input_schema`.** The schema is the embedder's, so `tool()` cannot drop a name from
     it. A given schema whose root `properties` names a bound keyword is refused with
     `ValueError` naming it. A schema that leaves the root open (`{"type": "object"}` under
     `validates_input=True`, as the LangChain and MCP recipes do) would let the guest send any
     key, so the frame host also refuses, after validation, any argument named in `Tool._fixed`.
   - **The message** is the validator's own for an unknown key, `<tool>: the arguments: unknown
     argument 'user_id'`, so a guest learns nothing from it about which names are bound.
   - **Where it lives.** A private field `Tool._fixed` (a frozenset, default empty), set by
     `tool()`. No public name or signature changes.

2. **A parameter's own default stays published.** The prompt to this specification asked
   whether sending *any* default to the guest is right. It is, for a default the function
   declares:
   - A parameter with a default is a parameter the guest may set (spec 031, Decision 2). Its
     default is part of the interface, and showing it helps a model call the tool well.
   - Hiding the value would not make the parameter safe: the guest could still pass any value
     the schema allows. The danger of a secret in a default is that the guest controls the
     parameter, and hiding the default does not change that.
   - Authority belongs where the guest cannot reach it: a closure, a bound method's object, or a
     partial's binding (Decision 1). The README says so in one sentence: never put authority in a
     default. A bound method's own defaults are its function's defaults, published the same way;
     its object (`self`) is never in the signature.

3. **A call answered before its tool starts never starts it (F2).**
   - `_Work.__call__` takes an optional `proceed`. The bound passes `_Bounded._proceed(slot)`,
     which answers `not slot.abandoned` under the bound's lock, the same lock `_abandon` takes to
     mark a call answered. `_Work` asks it once the gate has allowed, or at once with no gate,
     and before the tool starts. So exactly one of two orders holds: the call was answered first,
     and the tool never runs; or the tool started first, and it runs on, abandoned, as spec 036
     and the README's *Abandoned tools* already say.
   - On a skip `_Work` returns a `cancelled` answer ("<name> was not run: its call had ended"),
     which nobody reads: the slot of an abandoned call is dropped (spec 036, D4).
   - **The record is not changed.** The guest was answered while the gate ran on, so the outcome
     already says `abandoned=True`, which now means the call's gate or its tool ran on. Whether
     the gate later allowed may be known only after `run` returned, and a returned record is
     immutable and measures no time. No new counter is added: it would be a public name (a
     `stats()` key), which spec 049 freezes.
   - The inline invoke (a raw `host=` driving `_ToolHost` directly, with no bound) passes no
     `proceed`: it has no timeout and no abandonment, so nothing changes there.

4. **F3 is documented for a4; a per-run budget of request bytes is a later specification.**
   - Why not now: a budget is a new limit, and §4.15 asks every limit to have a default that the
     embedder can set. That needs a public knob (a `run` keyword and a `Defaults` field), a public
     API change that spec 049 freezes while it is being built. A private, fixed ceiling with no
     knob would be a hard cap that a legitimate embedder could not raise.
   - Why that is safe enough for an alpha: the cost is host CPU inside the deadline the embedder
     already grants; it reaches no file, secret or process; the review rates it medium-low and not
     blocking. The README now states the per-frame cost and the per-run bound in *Tools*
     ("The host's cost per frame") and in *Not protected*, with the present mitigations: a lower
     `max_tool_calls` and deadline where many untrusted guests run at once.
   - What the later specification decides (named here so it is scheduled, not open): a per-run
     budget of request bytes, its default, and its knob, checked in `admit` from the frame's
     length before the bytes are read. It follows 049's landing, before 0.1.0 final.

5. **F5 is documented; the runner does not refuse `\`, `:` or device names.**
   - Guest paths are POSIX paths: `/` is the only separator, and `\` and `:` are ordinary
     characters, as on a Linux grant. A refusal would break providers that are namespaces (the
     use cases mounts were built for: a database, an object store), where `12:00.csv` is a fine
     name.
   - It would also not make a host-folder provider safe: such a provider must still handle case
     folding, links inside its base, reserved names, trailing dots and spaces. The provider forms
     the host path, so the containment check belongs where the host path is formed.
   - The README's *Mounts* gains a paragraph, "A path is a name, not a host path", with a
     three-line containment check (resolve, then `is_relative_to` the resolved base).

6. **F4 and the build-class halves of the notes are a follow-up.** F4 (pass the build job's
   artifact id and digest list on, download by id, check `sha256sum` in `attest` before
   signing), N1 (exit 1 when `VERIFIED != PINS` in `00_download.sh`) and N3's workflow part
   (`enable-cache: false` for `setup-uv` in build and publish, an environment on `publish`) touch
   `.github/workflows/` and `scripts/`, which are build-class (AGENTS.md rule 2). They belong to
   one follow-up specification, "the release ties what it signs to what it built", to be
   drafted after this one. None blocks a4 (the review). N3's repository settings (rulesets on
   `main` and `v*`, a protected environment) are the owner's to set: question 94 in
   `../questions-for-the-owner.md`.

7. **The notes.**
   - **N2** is documented: the README's wasmtime-fixes item says the fixes are in this package's
     runner, not in the artifacts, so an embedder that drives the artifacts with its own wasmtime
     before 49.0.3 does not get them.
   - **N4** is documented: the README's gate item says `ToolCall.arguments` holds only what the
     guest sent, with no default and no bound keyword, and a gate that judges effective values
     fills the defaults itself. The `ToolCall` docstring is left to spec 049, which rewrites it.
   - **N5** and **N6** need nothing: each is documented with its reason (README *Abandoned
     tools*; spec 034, Decisions 8 and 10, and *Writable mounts*).
   - **N7** needs nothing here: it is the 0.1.0a2 review's F8 (a3's S4), dispositioned there for
     the wheel's next change.
   - **N1** and **N3**: Decision 6.

8. **Checks first, by events and counts.** Each new check was run against `28800bc`'s
   `tools.py` and seen failing before the code changed. No check measures time: a gate that must
   block waits on an event the check sets; a short `timeout_s` only chooses the outcome, as in
   spec 036's checks; the deadline end uses a fake ticker and the `timeout_s` end a fake clock,
   following spec 032's count-based deadline checks.

## Intent

A value an embedder binds into a tool stays on the host and is the value the tool uses; a call
that has ended never starts its tool; and what is not fixed in a4 (a large frame's host CPU, a
host-folder provider's paths, the release path) is written down for embedders or scheduled.

## Design

```
src/wasi_python/tools.py      _bound_keywords (the walk); _make: Tool._fixed, a given schema
                              naming a bound keyword refused; _derived skips bound keywords;
                              _ToolHost._answer refuses a bound keyword after validation;
                              _Work(proceed); _Bounded._proceed under the bound's lock
tests/checks/test_v1_4_embedding.py   criteria 1 to 3 (four checks, v1.4)
tests/unit/test_runner_tools.py       the three ends at the gate, with fakes; the lock's order
tests/unit/test_tools.py              a callable object's partial; a __wrapped__ cycle
README.md                     Tools (partial, defaults, gate arguments, gate then end, the host's
                              cost per frame); Mounts (a path is a name); Safety (the fixes are
                              in the runner); Not protected (frame CPU)
CHANGELOG.md                  0.1.0a4, one Security entry
```

## Scope

In: F1, F2 (fixed, with checks); F3, F5, N2, N4 (documented); a disposition of every finding.

Out, each with its home:
- F4, N1 and N3's workflow part: the follow-up build-class specification (Decision 6).
- N3's repository settings: the owner (question 94).
- F3's budget: a specification after 049 lands (Decision 4).
- The guest package (`recipes/guest/host/`): unchanged; it renders what the descriptor says, so
  a dropped name is gone from the guest without a rebuild.
- The `ToolCall` and `Tool` docstrings: spec 049 rewrites them.

## Acceptance criteria

1. `test_a_partials_bound_keywords_are_fixed` (v1.4) passes: the review's probe through `run`;
   the descriptor's properties are `{}`; the guest's signature is `() -> list[str]`; the
   guest's `my_orders(user_id=7)` raises `ToolArgumentError` with no frame; two forged frames
   are `invalid_arguments` with the unknown-argument message; the secret is in no descriptor,
   stub, stdout or stderr; the tool ran once with `(42, secret)`. Seen failing on `28800bc`.
2. `test_bound_keywords_are_fixed_however_the_partial_is_reached` (v1.4) passes: nested
   partials, a `__wrapped__` chain and a bound `partialmethod` hide their bound keywords; a given
   schema naming one raises `ValueError`; an unbound `partialmethod` raises `TypeError`; under an
   open schema a frame naming bound keywords is `invalid_arguments` with 0 tool calls; a plain
   function's default is still published. Seen failing on `28800bc`.
3. `test_a_gate_that_allows_late_runs_no_tool[timeout]` and `[cancel]` (v1.4) pass: the gate
   ran once (`seq` 2), the tool 0 times, and 0 tool threads are left. Seen failing on `28800bc`
   (the tool ran once, after `run` returned, in each).
4. The unit cases `test_a_call_ended_at_its_gate_never_runs_its_tool` (three ends, 0 tool runs,
   thread count back to 0, and the other order still runs its tool once, abandoned),
   `test_the_tool_starts_only_if_its_call_was_not_answered` and
   `test_bound_keywords_are_found_through_any_wrapper` pass. The first two were seen failing on
   `28800bc`.
5. The review's own probes, re-run on the built tree against the same artifact set:
   `p08_tools_partial_and_late_gate.py` shows a schema with no properties and no `TOOL RAN`;
   `tools-probes/p8_late_gate.py` shows no `TOOL RAN` and no `TOOL2 RAN`.
6. The full judge in the worktree, without `--accept`: v1.4 goes from 125/125 to 129/129, no
   pass is lost, nothing grows; `ruff check` and `ruff format --check` are green.
7. README: the four *Tools* additions, the *Mounts* paragraph, the *Safety* sentence and the
   *Not protected* entry are present. CHANGELOG: one entry under 0.1.0a4.


## Landing notes

Built 2026-10-18 by the implementer (Claude Opus 5.5) in the worktree
`../wasi_python-056`, from main `28800bc`. Every claim below was run (EXECUTED) on macOS arm64,
CPython 3.14.2, wasmtime-py 49.0.0, against the frozen artifact set
`build/sets/s-f94dec535086b06c` of the main tree (its `SHA256SUMS` is the main tree's
`build/artifacts/SHA256SUMS`, the set the review ran against), unless it says otherwise.

### What was built

- `feb79aa` (F1): `_bound_keywords` and the private `Tool._fixed`; `_derived` skips a bound
  keyword; `_make` refuses a given schema that names one; `_ToolHost._answer` refuses, after
  validation, an argument that names one, with the validator's unknown-argument message.
  Checks: criteria 1 and 2, and the unit case for a callable object and a `__wrapped__` cycle.
- `28abf17` (F2): `_Work.__call__(proceed)`, asked after the gate (or at once with no gate) and
  before the tool; `_Bounded._proceed`, under the lock `_abandon` takes. Checks: criterion 3
  and the two unit cases of criterion 4.
- `7e52c94` (docs): README *Tools* (a partial's bound keywords and a parameter's default; what
  `ToolCall.arguments` holds; a call that ends while its gate decides; "The host's cost per
  frame"), *Mounts* ("A path is a name, not a host path"), *Safety* (the wasmtime fixes are in
  the runner) and *Not protected* (frame CPU); one CHANGELOG entry under 0.1.0a4.
- `897a7b9`: this specification, and question 94 in `../questions-for-the-owner.md`.

Each commit was checked green on its own for the files it carries: the F1 commit's index,
exported alone, passes `ruff check`, `ruff format --check` and the tool checks and units (224
passed).

### Seen failing first (criteria 1 to 4)

The new checks and units, run against `28800bc`'s `src/` (exported with `git archive`, put first
on `PYTHONPATH`), with the new tests (`build/seen-failing-old-code.log`):

```
FAIL test_a_gate_that_allows_late_runs_no_tool[cancel] — assert ([2], [5], []) == ([2], [], [])
FAIL test_a_gate_that_allows_late_runs_no_tool[timeout] — assert ([2], [5], []) == ([2], [], [])
FAIL test_a_partials_bound_keywords_are_fixed — {'type': 'object', 'properties': {'user_id':
     {'type': 'integer', 'default': 42}, 'api_key': {'type': 'string', 'default': 'sk-live-SECRET'}} …
FAIL test_bound_keywords_are_fixed_however_the_partial_is_reached — (the same schema, nested partials)
FAILED tests/unit/test_runner_tools.py::test_a_call_ended_at_its_gate_never_runs_its_tool
       (assert ([1], 0, 0) == ([], 0, 0): the tool ran)
FAILED tests/unit/test_runner_tools.py::test_the_tool_starts_only_if_its_call_was_not_answered
       ('_Bounded' object has no attribute '_proceed')
6 failed
```

`test_bound_keywords_are_found_through_any_wrapper` names `_bound_keywords`, new here, so it
could not run against `28800bc`; its partial-of-a-callable-object case is the same leak as
criterion 2's.

### The review's probes, re-run (criterion 5)

Copied to a scratch folder (so nothing is written beside the review's evidence) with only the
artifact path changed, and run with `uv run python -I` on the built tree
(`build/p08-after-fix.log`, `build/p8-late-gate-after-fix.log`):

```
schema the guest is sent: {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}
guest sees signature: () -> list[str]
as bound: ['orders of user 42 via key sk-liv...']
host.ToolArgumentError: my_orders(): got an unexpected keyword argument 'user_id'
guest got ToolTimeout
after run returned: [('gate allowed', '+0.48s')]
run1 returned: guest told: timeout [('ok', False), ('timeout', True)]
   gate allowed transfer after run returned
run2 (cancelled): cancelled [('ok', False), ('cancelled', True)]
   gate allowed transfer2 after run returned
```

Before the fix the same probes printed the bound key as a default, `overridden: ['orders of user
7 …']`, and `TOOL RAN` after `run` returned (the review's logs). Now the gate still allows late,
and no tool runs.

### The judge (criterion 6)

The fast tier while building, then the full judge once, in the worktree, without `--accept`,
`WASI_PYTHON_ARTIFACTS=…/build/sets/s-f94dec535086b06c uv run pytest` (`build/full.log`):

```
wasi_python v1: 270/312 pass · 0 gap · 42 blocked · 0 fail   (unit suite 1020/1028, 8 skipped)
  v1.4  embedding           129/129
ratchet vs 34eb315196: lost 0 · absent 0 · unrun 0 · unrun locally 28 · gained 4 · grew 0 ·
  upstream unrun 31 · judge changed: tests/checks/test_v1_4_embedding.py,
  tests/unit/test_runner_tools.py, tests/unit/test_tools.py
1290 passed, 50 skipped in 306.86s (0:05:06)
```

The 42 blocked are the worktree's missing source trees, test kit, oracle, wheel and prior-art
clones (numpy 17, pandas 16, and one each for the rest), not this change; the fast tier before
the change was 259/308 with v1.4 125/125 and the same blocks. v1.4 gains exactly the four new
checks. `ruff check` and `ruff format --check` are green on `src/` and `tests/`. The lane accepts
with `--accept-judge`, since three judging files changed.

### Disposition of the review's findings

The same text is in `build/reviews-evidence/a4-security/disposition.md` in the main tree, for
the reviewer to confirm.

- **F1: fixed** (`feb79aa`; Decisions 1 and 2). A keyword a `functools.partial` binds is fixed:
  not in the schema, the descriptor, the guest's signature or `stubs()`; a frame naming it is
  `invalid_arguments` with the unknown-argument message; a given schema naming it is refused;
  an open schema cannot let it through. It is found through nested partials, `__wrapped__`
  chains, bound methods, callable objects and a bound `partialmethod`; an unbound
  `partialmethod` is refused. A parameter's own default is still published, with the reason
  (Decision 2) and a README warning. Checks: criteria 1 and 2, seen failing on `28800bc`.
- **F2: fixed** (`28abf17`; Decision 3). The tool starts only if `_Bounded._proceed` finds the
  call not yet answered, under the lock that marks it answered; with or without a gate. The
  record is unchanged (`abandoned=True`: the gate or the tool ran on). Checks: criterion 3 and
  two units, seen failing on `28800bc`.
- **F3: documented for a4; a budget scheduled** (`7e52c94`; Decision 4). README *Tools* ("The
  host's cost per frame") and *Not protected*. A per-run request-byte budget, with a default
  and a knob, is a specification after 049 lands (the knob is a public name 049 freezes), before
  0.1.0 final.
- **F4: accepted for a follow-up** (Decision 6). Build-class (`.github/workflows/`), so out of
  this specification: "the release ties what it signs to what it built" (artifact id and digest
  list from `build`, download by id, `sha256sum -c` in `attest` before signing), with N1 and
  N3's workflow part. Does not block a4 (the review).
- **F5: documented** (`7e52c94`; Decision 5). README *Mounts*: "A path is a name, not a host
  path", with a containment check. The runner does not refuse `\`, `:` or device names: they are
  ordinary characters in a POSIX path, a refusal would break namespace providers, and it would
  not make a host-folder provider safe.
- **N1: follow-up** (Decision 6): exit 1 when `VERIFIED != PINS`, in the same build-class
  specification as F4. `pinned()` already re-hashes every use.
- **N2: documented** (`7e52c94`): README *Safety*, the fixes are in the runner, not the artifacts.
- **N3: split** (Decision 6): the workflow part (`enable-cache: false`, an environment named on
  `publish`) goes to the F4 follow-up; the repository settings (rulesets on `main` and `v*`, a
  protected environment) are the owner's: question 94.
- **N4: documented** (`7e52c94`): README, the gate item.
- **N5, N6: nothing**: documented with their reasons (README *Abandoned tools*; spec 034,
  Decisions 8 and 10).
- **N7: nothing here**: the 0.1.0a2 review's F8 (a3's S4), dispositioned for the wheel's next
  change.

### Left over

- The follow-up build-class specification (F4, N1, N3's workflow part) and the request-byte
  budget specification (F3) are named, not drafted.
- Question 94 waits on the owner. Its number is the next free one on main and on the sibling
  branches at the time of writing; the lane renumbers it if another branch lands a 91 first.
- Spec 049 rewrites `tools.py`'s docstrings and renames its constants. This change adds one
  private field, one function, two private constants and three short blocks, and changes no
  public name, so the rebase of whichever lands second has local conflicts only.
