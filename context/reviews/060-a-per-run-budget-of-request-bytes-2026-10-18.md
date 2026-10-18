# Review of 060 — A per-run budget of request bytes, and N8 (build review)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). I wrote none of the spec, its pre-build review,
  its confirmation, the research or the build.
- **Reviewed:** `git diff 5e66995 32f0503` on `spec/060-a-per-run-budget-of-request-bytes`
  (worktree `wasi_python-060`, made from main `5e66995`): `b8cb370` (confirmed for build),
  `f77d97d` (the build) and `32f0503` (the landing notes). I judged from the spec (Decisions 1 to
  12, criteria 1 to 9, stand-ins (a) to (n) and the builder's (c')) and the diff. I used the
  landing notes only to find things to check.
- **Read:** AGENTS.md; the constitution (§4.4, §4.9, §4.15, §5.6, §7); specs 049 (Decisions 8,
  10, 13), 053 and 055 (and the branch's edit of 055); the pre-build review and its confirmation
  (`build/reviews-evidence/060-spec/` in the main tree) with their probes; the house format
  (`context/reviews/053-async-host-functions-2026-10-18.md`); and `src/wasi_python/tools.py`
  (`_bound_keywords`, `_type_hints`, `_make`, `_ToolHost`, `_list_answer`, `_answer`) and
  `runner.py` (`Defaults`, `run`, `run_async`, `_checked`, `_check_tools`, `_door`,
  `_tool_host`) as they stand at `32f0503`.
- **Re-ran:** all with `WASI_PYTHON_ARTIFACTS=…/build/sets/s-c4190ca065ada03a`, on darwin-arm64,
  CPython 3.14.2 (3.11.14 where named), in the worktree, without `--accept`. Scripts and logs are
  beside this file. Nothing was written in either git tree; every `src/` mutation was restored
  from memory in a `finally`, and `git diff -- src/` was empty after each run.
  - **The fast tier**, `uv run pytest -m "not slow" -n 3` (`fast_tier.txt`):
    ```
    wasi_python v1: 317/366 pass · 0 gap · 10 blocked · 0 fail · 39 deselected   (unit suite 1119/1127, 8 skipped)
      v1.4  embedding           159/159
    ratchet vs 588ec65390: lost 0 · absent 0 · unrun 0 · unrun locally 8 · gained 2 · grew 0 · upstream unrun 31 · not selected 27 · judge changed: tests/checks/test_v1_4_embedding.py, tests/public_api.txt, tests/unit/test_runner_tools.py and 1 more
    1436 passed, 18 skipped in 168.61s (0:02:48)
    ```
  - **The full judge, once, serially, with no flags** (`full_judge.txt`):
    ```
    wasi_python v1: 324/366 pass · 0 gap · 42 blocked · 0 fail   (unit suite 1119/1127, 8 skipped)
      v1.4  embedding           159/159
    ratchet vs 588ec65390: lost 0 · absent 0 · unrun 0 · unrun locally 28 · gained 2 · grew 0 · upstream unrun 31 · judge changed: tests/checks/test_v1_4_embedding.py, tests/public_api.txt, tests/unit/test_runner_tools.py and 1 more
    1443 passed, 50 skipped in 249.79s (0:04:09)
    ```
    The 42 blocked are the worktree's missing source trees (numpy 17, pandas 16, one each for
    bzip2, cpython, sqlite, xz and zlib), the oracle, the prior-art clones, the wheel and "three
    systems", as the landing notes say: not this change. The 2 gained are criteria 3 and 4.
    The numbers match the builder's full run line for line.
  - `uv run python tests/harness/api.py --check`: exit 0. The snapshot's diff is exactly four
    added lines and no removed one (`p6_api_ruff.txt`). `uv run ruff check src tests`: clean.
    `uv run ruff format --check src tests`: 81 files clean. `git diff --check`: clean.
  - Probes P1 to P7 and stand-ins P5/P5b, below.

## Acceptance criteria against evidence

Labels: EXECUTED (I ran it), READ (I read code or text), INFERRED (reasoned, not run).

1. **`test_the_request_byte_budget_counts_admitted_bytes`.** Met (EXECUTED, READ). Every bullet
   of the criterion is in the check: the 600-byte non-JSON frame spends; `admit(401)` is refused
   with "bytes", nothing pending, `op=None`, `request_bytes=401`; 400 exactly reaching 1000 is
   admitted; 1 is refused; the 1 MiB cap comes first; the raw path counts the same; frame limit
   and byte budget messages differ; an empty frame under `max_bytes=0` is admitted; `None`
   admits 2,000 frames. Parses are counted, never timed. My stand-ins (c'), (l) and (o) each
   fail it (P5).
2. **`test_the_request_byte_budget_is_a_limit_with_a_default`.** Met (EXECUTED, READ). The
   check covers the field and `defaults()`, the `_integer_limit` rules on both names, unset /
   5 / `None` through `_checked`, the refusal without `tools=` with 0 lookups and 0 submits,
   `set_defaults` restored in a `finally`, and `_tool_host` with and without the key. My
   stand-in (p) (the refusal without `tools=` removed) fails it ("the artifacts must not be
   looked up"). The existing four-argument `_check_tools` calls, its exact three-key no-tools
   result and the hand-built `c` dicts pass unchanged: the diff of `tests/` removes no line
   (READ, `git diff … -- tests | grep '^-'`: 0).
3. **`test_the_request_byte_budget_holds`.** Met (EXECUTED). Through `run`, with
   `_ToolHost.__call__` wrapped: `[300000, 300000, 'budget', 2]`, outcomes `list ok, call ok,
   call ok, None budget_exceeded, call ok`, 3 tool runs, 4 frames read; the default reads 5.
   Stand-in (c') fails it on the count read, `[26, 400071, 400071, 400071, 75]`, as the
   pre-build review's F3 (b) asked (P5).
4. **`test_a_call_chain_of_any_depth_hides_bound_keywords`.** Met (EXECUTED, on 3.14.2 in the
   judge; the same cases on 3.11.14 in P3). Depth 2, 3 and the metaclass case publish `limit`
   only, keep `SECRET` out of the descriptor and the stubs, refuse `user_id` with the
   unknown-argument message, and run once with `(42, SECRET, 3)`; `itemgetter` and an ordinary
   class are empty; a plain callable object still describes `a`; the cycle is the walk's
   `TypeError`. Stand-in (k) fails it (the metaclass case leaks `user_id` and `api_key`, P5).
5. **`test_the_tool_list_is_encoded_once`.** Met (EXECUTED). One encode for five `list` frames;
   each answer byte for byte the un-spliced encode; `too_large` on both frames over a 100-byte
   cap. Stand-ins (m) (5 encodes) and (n) (id 1 where 2 was due) fail it (P5, P5b).
6. **Nothing else moves.** Met (EXECUTED). v1.4 goes from 157/157 (the pre-build review's
   main) to 159/159, exactly the two new checks; the unit suite from 1116/1124 to 1119/1127,
   the three units. Lost 0, grew 0, in both tiers. No `budget_exceeded` appears where there was
   none: no existing check fails. The snapshot diff is Decision 9's four lines (055 has not
   landed). `test_every_public_name_is_documented`, `test_the_readme_reference_matches_the_api`
   and `test_set_defaults_changes_what_run_reads` pass in both tiers. Ruff is green.
7. **Benchmark facts.** Met (READ the builder's `build/060/bench_built.log`; my own P4 and P7
   agree in kind). Through `run` at the default, 60 frames of 1,000,071 bytes gave 16 read, sum
   16,001,136, and 44 `budget_exceeded` (P4). The builder's departure (a script of its own, not
   `bench060.py`'s part C, which would stack its prototype on the real budget) is sound.
8. **The README and the CHANGELOG; 055's text.** Met (READ), with one clause I would widen
   (N2). The README's *Running it* list, *Tools* (**Limits**, **The host's cost per frame**,
   **What `run` refuses**), the kinds table and *Not protected* carry Decision 11's text; the
   CHANGELOG has the Security bullet and the Changed line. 055 has Decision 7's bullet, its
   table cell and the keyword in `Session`'s signature.
9. **055 landed first.** Does not apply: 055 has not landed (READ, main `5e66995`).

## Probes

- **P1 (`p1_budget_unit.py`), the budget through a `_ToolHost`.** EXECUTED. At budgets of 100,
  1,000 and 1 MiB, a frame exactly at the budget is admitted and the next 1-byte frame refused;
  one byte short, the same frame is refused with 0 admitted. Under `max_bytes=0`, 1,000 empty
  frames are each one failed decode (`protocol`), spend 0, and a 1-byte frame after them is
  refused. After a 400-byte frame under 500, 10,000 frames of 200 bytes are refused with
  **1 parse in total** (the first frame's), and a 100-byte frame is still admitted after them.
  A denying gate (sync, async, raising) spends its frame's bytes; an async tool counts the same;
  the door-length mismatch path spends the admitted length. The over-cap frame spends nothing,
  and `2**63 − 1` is a plain integer budget.
- **P4 (`p4_budget_run.py`), the built budget through `run` and `run_async`.** EXECUTED, no
  prototype. Criterion 3's guest with an async tool: `[300000, 300000, 'budget', 2]`, reads
  `[26, 400072, 400072, 76]` (the async tool's name is a byte longer). With a denying sync or
  async gate: `['denied', 'denied', 'budget', 'denied']`, the third refused unread. 3,000 empty
  frames with `max_tool_request_bytes=0, max_tool_calls=None`: 3,000 read, 0 bytes, all
  `protocol`, and a `list` after them `budget_exceeded`. The boundary through the real door:
  budget 126 admits 26 + 100 and refuses a 1-byte frame ("126 are used"); budget 125 refuses the
  100-byte frame and admits the 1-byte one after it (26 + 1 fits). `run_async` matches `run`.
  With `max_tool_request_bytes=0`, the guest's `from host import tools` raises `ImportError`
  ("the host refused the tool list (budget_exceeded) …"; see N2).
- **P2 (`p2_splice.py`), the splice.** EXECUTED. 78 answers compared with `_encode` of the whole
  body: ids 0, 1, 7, 10**6, `_MAX_ID`, and the ones echoed as `null` (`_MAX_ID + 1`, −1,
  `True`, `False`, 1.0, `"1"`, `None`, missing), each followed by two more `list` frames; an
  empty tool list (`[]`); and three tools with non-ASCII text in descriptions, defaults and a
  `Literal`, an `input_schema` enum with an astral character, a lone surrogate, `U+2028`, NUL
  and `</`. **0 differ**; the wire stays ASCII; over a 200-byte cap every frame is `too_large`
  with the descriptors encoded once.
- **P3 (`p3_n8.py`), N8's walk against main's, 43 callables, on 3.14.2 and 3.11.14.** EXECUTED.
  - Changed, as intended: depth 2, 3, 5 and 20 (main found nothing; built fixes `api_key` and
    `user_id`, props `['limit']`); the metaclass partial; a metaclass whose `__call__` is a
    callable object whose class's `__call__` is the partial; an object whose class's `__call__`
    is the metaclass class (fixed by the walk; `tool()` then refuses it on its hints); cycles
    of one object, two objects, and through a metaclass (`Meta.__call__ = staticmethod(C)` for
    `C` of that metaclass): each the walk's `TypeError`, "nest deeper than 64".
  - Unchanged: a function, a partial, nested partials, 056's depth-1 case, a callable object,
    a bound method, a classmethod `__call__`, `lru_cache`, `functools.wraps`, a lambda, an
    `async def`, a singleton metaclass with a plain `__call__`, an ordinary class, `int`,
    `dict`, `itemgetter`, `attrgetter`, `methodcaller`, `len`, `math.sqrt`, `str.upper`,
    `[].append`, `print`, a `partialmethod` through an instance (fixed) and through the class
    and as `__call__` (both refused as before).
  - My own adversarial cases: a `__slots__` `__call__` holding the partial (refused: its hints
    cannot be read); a class with `__wrapped__ = partial(…)` and an annotated metaclass
    `__call__` (props from the metaclass function, no default, no secret: `inspect` does not
    unwrap it either); an object whose `__signature__` is copied from the partial (publishes the
    defaults, by design: that is the embedder writing defaults into a signature, no partial is
    on the call path, as for `def f(api_key=SECRET)`; not N8, and unchanged from main).
  - 3.11.14 differs from 3.14.2 only in the message `tool()` gives for the three `operator`
    callables (their signatures read differently); the walk's results are identical.
- **P7 (`p7_overcap_list.py`), a benchmark fact.** EXECUTED. A 18,196,101-byte tool list (over
  the 16 MiB answer cap): built 0.90 ms CPU per `list` frame, main's per-frame encode 33.94 ms.
  See N1.

## Stand-ins re-applied (P5, P5b)

Written from the spec's words, not from the builder's `standins.py`; each applied, run by node
id, and the file restored (`p5_standins.txt`, `p5b_standin_n.txt`).

| stand-in | check | failing line |
|---|---|---|
| (c') checked after the read, counted when it fits | criterion 1 | `admit(401)` returns `None` (`isinstance(None, bytes)`) |
| | criterion 3 | `assert 5 == 4`, read `[26, 400071, 400071, 400071, 75]` |
| (k) the walk stops at a class | criterion 4 | `('metaclass', …'user_id'…'default': 'sk-live-SECRET'…)` |
| (l) a `protocol` answer refunds its bytes | criterion 1 | `admit(401)` returns `None` |
| (m) the list encoded per frame | criterion 5 | `assert 5 == 1` |
| (n) the whole first answer kept | criterion 5 | `At index 12 diff: b'1' != b'2'` |
| (o, mine) a refusal resets the count | criterion 1 | `admit(1)` after 400 returns `None`; criterion 3 passes (it does not claim this one) |
| (p, mine) no refusal without `tools=` | criterion 2 | "the artifacts must not be looked up" |
| (q, mine) `_C_SLOTS` narrowed to `WrapperDescriptorType` | criterion 4 and all of `test_tools.py` | **survives** (175 passed); see N3 |

My first (n) in P5 was my own mistake (it returned before keeping the answer, so it was the
built code and passed); P5b is (n) done right, and it fails.

## Findings, most severe first

No finding blocks landing. Three notes.

1. **N1 (note). A tool list over the 16 MiB answer cap is still concatenated whole on every
   `list` frame, only to be measured and refused.** EXECUTED (P7).
   - **Where:** `tools.py`, `_answer`'s `list` branch: `answer = self._list_answer(frame_id)`,
     then `if len(answer) > _TOOL_RESPONSE_BYTES: return failed("too_large", …)`.
   - **Cost:** 0.90 ms of GIL-held CPU per frame for an 18 MB list, so 0.9 s at the default
     1,000 frames (main: 34 ms per frame, 34 s). It is per frame, so `max_tool_calls` bounds it,
     which is what the README already says of each `list` answer's copy. So it is honest as
     written, and a 37-fold improvement on main.
   - **Fix (optional, two lines):** refuse before building, from the lengths:
     `len(self._tools_json) + len(shown) + 32 > _TOOL_RESPONSE_BYTES` (the envelope is fixed),
     or remember the `too_large` verdict at the first `list` frame. A list that big is an
     embedder's mistake, not a guest's choice, so this can wait.
2. **N2 (note, docs). A refused discovery frame is an `ImportError`, not `ToolBudgetExceeded`.**
   EXECUTED (P4).
   - With `max_tool_request_bytes` under 26 (0 included, as Decision 4 says), `from host import
     tools` raises `ImportError: the host refused the tool list (budget_exceeded): …`. The
     README's **Limits** says "Past either, the guest gets `ToolBudgetExceeded` and runs on".
     The same was already true of `max_tool_calls=0`, so this is not new to 060; 060 widens the
     sentence to a second limit.
   - **Fix (optional):** one clause in **Limits**: "if the discovery frame itself is refused,
     `from host import tools` raises `ImportError`".
3. **N3 (note). Four of the five `_C_SLOTS` entries are unpinned.** EXECUTED (stand-in (q)
   survives criterion 4 and the whole of `test_tools.py`).
   - With only `types.WrapperDescriptorType` left, every case I tried still stops with the
     same result (EXECUTED, `p8_cslots.py`: a `__call__` that is `len`, `str.upper`, a
     method-wrapper, and `itemgetter`, `int`, a partial). A `BuiltinFunctionType` `__call__`
     stops one hop later on `inspect.isbuiltin`, and a method descriptor's own `__call__` is a
     wrapper descriptor, so it stops there. (P8 also shows a pre-existing oddity that 060 does
     not change: a `__call__` that is a class-method descriptor of another type, such as
     `dict.__dict__["fromkeys"]`, raises its own `TypeError` from `type(obj).__call__`. Main's
     walk makes the same access at its first hop, and it is still a `TypeError`, as `tool()`
     promises.)
   - So they are belt and braces, matching `inspect`'s own list, not a defect. A unit row with
     `class X: __call__ = str.upper` would pin `MethodDescriptorType` if wanted. Not required.

## Checks of the rest

- **The budget has no bypass I could find** (EXECUTED P1, P4; READ `_door`, `admit`,
  `__call__`). The door calls `admit(length)` after the address checks and before the copy, with
  `length` masked to an unsigned 32-bit value, so no negative length can refund. Refused frames
  never reach `__call__` and spend nothing; a fitting frame after them is admitted; a refusal
  does not reset the count (my (o) is killed). Gates and async tools run after the parse, on
  admitted frames. The raw path (`host(frame)` with nothing pending) admits in `__call__`. The
  zero-length frame spends nothing and costs one failed decode, which `max_tool_calls` bounds
  (with `max_tool_calls=None`, only the deadline, as the README says).
- **The splice is exact** (EXECUTED P2; READ). The id is echoed only when `type(id) is int` and
  in `0 … 2**53 − 1`, so `str(int)` is its JSON; `_encode`'s settings are fixed
  (`ensure_ascii`, no NaN, compact separators, no key sorting), so the slice of
  `{"tools": …}` is the array `_encode` would write inside the body. `PROTOCOL` for `v` is the
  same bytes as the literal 1 (the builder's stated departure).
- **N8's walk stops where `inspect` stops** (EXECUTED P3, on both versions): it follows
  `type(target).__call__` on every hop, a class included, and stops at the C slot types and at
  a missing `__call__`. The 64-hop bound turns every cycle I built into the promised
  `TypeError`; on main the same cycles gave `RecursionError` on 3.14 (the builder's
  `main_cases.log`, the pre-build review's P2).
- **The runner** (READ, EXECUTED criterion 2 and `test_set_defaults_changes_what_run_reads`):
  `_check_tools` reads `limits` once for whichever limit is unset; `_checked` passes the keyword
  by name; the no-tools result keeps its three keys; `_tool_host` uses `.get`, so hand-built
  `c` dicts mean no limit, as Decision 5 says. `Defaults.__post_init__` checks the field.
- **The public API** (EXECUTED): `api.py --check` exits 0; the snapshot gains Decision 9's four
  lines and loses none; the docstrings carry `Args:` and `Attributes:` entries, no spec number
  and no internal name (the `# spec 060` is a comment, not docstring text). The keyword is last
  in `run` and `run_async`, the field last in `Defaults` with its default.
- **055's edit** (READ). One bullet in "The rule for arguments `run` gains", the keyword in the
  `max_file_calls, max_tool_calls` row, and in `Session`'s signature after `max_tool_calls`.
  055's Decision 17 records the constructor's parameters by reference to Decision 5, and the
  rule list says "the builder adds each such argument to Decision 17's lines", so 055's builder
  is told. Nothing else in 055 needed to change; its Decision 9's two `Defaults` fields will
  now sit after `tool_request_bytes`, which is still "last, with a default".
- **Honesty of the text** (READ against the code and P1, P4, P7). The README's **Limits**,
  **The host's cost per frame**, **What `run` refuses**, the kinds table and *Not protected*
  say what the code does and claim nothing of the byte budget beyond parsing: fixed per-frame
  cost and `list` copies are given to `max_tool_calls`. "About 5 to 10 s at the default" agrees
  with the builder's 5.09 s for 16 worst frames and the pre-build review's per-MiB figures. The
  CHANGELOG's Security bullet and Changed line match the code, including "encoded once per
  call" (one frame host per call) and the 3.14 `RecursionError` now a `TypeError`. The only
  imprecision is N2's, and it predates 060.

## Constitution checks

- **§4.15 (safe by default; every limit has a default):** holds. A new limit with a 16 MiB
  default, tighter than "none", checked like `max_tool_calls`; nothing is loosened, so no
  owner's decision is needed. `None` is explicit opt-out.
- **§4.4 (the tool protocol):** holds (READ). No import, export or kind changes; the guest
  package is untouched; `budget_exceeded` is an existing kind; the wire for `list` is byte for
  byte the same (P2).
- **§4.9 / AGENTS.md "tests count operations":** holds (READ). The new checks count parses,
  encodes, frames read, outcomes and tool runs; no check reads a clock. Times are in this
  review's probes and the builder's logs only.
- **AGENTS.md rule 4 (never weaken the judge):** holds (READ). The judge change is additive:
  three new test functions appended, two new checks in v1.4, and `tests/public_api.txt`
  regenerated with exactly four added lines. No existing check, golden, gap or allowance is
  edited. The lane accepts with `--accept-judge`.
- **049, Decisions 8, 10 and 13:** holds. Each line is placed and allowed as Decision 9 lists;
  both CHANGELOG lines cite their exception.
- **§5.6:** this review re-ran the counted tests (both tiers) and checked every criterion.
- **§7 and build class:** nothing tripped. The diff touches `src/`, `tests/`, `README.md`,
  `CHANGELOG.md` and `context/` only: no `scripts/`, `recipes/`, `downloads/SHA256SUMS` or
  workflow (READ, the diff stat).

## Verdict

**Lands.** Every criterion is met. All the named stand-ins I re-applied are killed, and so are
two of my own three; the third, (q), is a near-equivalent mutant (N3). The budget is checked
before a byte is read, spends whatever the answer, refunds nothing, and has no bypass through
async tools, gates, refused frames, frames after `budget_exceeded`, the empty frame or the
boundary. The splice is byte for byte the old wire. N8's walk closes the chain, the metaclass
and the cycle without moving any ordinary callable, on 3.11 and 3.14. The full judge is green
with lost 0 and grew 0. N1 to N3 are optional and need no change before landing.

## One line

The byte budget holds where it must, before the read, and the list and N8 fixes are exact;
three optional notes, nothing to fix before it lands.
