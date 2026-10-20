# Review of 104 — The runner becomes a package: one module per concern

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (build reviewer for the chain 103–108)
- **Reviewed:** `c15adf4..2a9546c` on `spec/104-the-runner-becomes-a-package` in `/home/user/wt/104`
  (stacked on 103's built tip `c15adf4`; the five commits `bbdafa3`, `b92aa5b`, `859dad1`,
  `ea08708`, `2a9546c`). Time box: 45 minutes (the diff is 48 files, 7,758 insertions).
- **Run:** none; the chain's one dispatch on its final tip
- **Re-ran:** `WASI_PYTHON_ARTIFACTS=/home/user/wasi_python/build/baseline-a7/set/wasi-python-0.1.0a7
  uv run pytest -m "not slow" -n 3 -q -p no:cacheprovider` on `2a9546c`, twice under
  `build/fast-tier.lock` → **83 failed, 2368 passed, 52 skipped in 330.28s**, exit 1, the first
  time; the 83 node ids are the chain's baseline `failing-nodes.txt` exactly (`diff` of the
  two sorted lists: 0 lines). That run's record was then overwritten by my own node-id probes
  (the harness keeps one `build/progress/latest.json`), so the tier ran a second time with the
  copy and the sameness runs chained behind it: **83 failed, 2368 passed, 52 skipped in 405.88s**, exit 1, the same 83 node ids,
  record `build/104/review.json`, whose `suite` line is `{'passed': 1854, 'skipped': 13, 'total': 1868}`, the builder's. `uv run python tests/harness/sameness.py
  /home/user/wt/103/build/103/built.json build/104/review.json --claims build/104/claims.toml`
  → `note: explained by claims: 104 3`, exit 0 (`build/104/review-sameness-103.txt`); against
  the chain's baseline with `build/104/claims-chain.toml` → `note: explained by claims: 103 4 ·
  104 3`, exit 0 (`build/104/review-sameness-chain.txt`). `uv run pytest
  tests/checks/test_rules.py -q -p no:cacheprovider` → 43 passed, 4 skipped, exit 0. Three
  probes by node id, `tests/unit/test_runner_package.py::test_every_module_level_lock_is_remade_after_fork`,
  `tests/checks/test_v1_4_embedding.py::test_package_imports_without_wasmtime`,
  `tests/checks/test_v1_4_public_api.py::test_set_defaults_changes_what_run_reads` → 3 passed in
  0.72s. `uv run python build/104/verbatim.py c15adf4` → the same counts as the builder's
  `verbatim.txt` (diff: none but uv's TLS warning line), uncategorised residue none, exit 0. My
  own two-way multiset comparison, base `runner.py` + `__init__.py` against the eleven modules
  + `__init__.py` at `2a9546c`, blank lines dropped, indentation kept (scratch
  `residue.py`): base 5,694 lines, tree 5,873; new-only 131 import lines, 210 prefix-only
  qualified lines whose source is consumed on the old side, 87 residue lines, every one a module
  docstring line, an `if TYPE_CHECKING:` header, `find_artifacts = artifacts`, a line of the two
  hooks' bodies or a formatter fragment whose unwrapped source stands in the old-side residue;
  old-only 39 lines: 12 import lines, the `# Last:` comment, the hooks' old lines and the 19
  wrapped sources. `git diff --color-moved=dimmed-zebra --color-moved-ws=no --color=always
  c15adf4..ea08708 -- src/` → 9,429 `+`/`-` lines, 793 not dimmed, all of them import,
  docstring, qualified, hook or wrapped lines (the multiset reading above is the finer one).
  `uv run ruff check src tests` → All checks passed; `uv run ruff format --check src tests` →
  142 files already formatted. `uv run python -c "import wasi_python, sys; assert 'wasmtime'
  not in sys.modules; from wasi_python import run, run_async, Session, Grant, Completed,
  SessionEnded, artifacts, Defaults"` → ok; with `sys.modules['wasmtime'] = None` first, `import
  wasi_python` and `from wasi_python import run, Session, Grant, mounts, tools, cli` → ok.
  `wc -l src/wasi_python/*.py` → `runner.py` 1,225, `_call.py` 1,178, `_sessions.py` 960,
  `mounts.py` 2,212, `tools.py` 2,450. A probe of the size check without editing any file
  (the module loaded by path, `ALLOWED['mounts.py']` set to 2213) → `src/wasi_python/mounts.py:
  2,212 lines, ALLOWED says 2,213`; with an entry `gone.py` → `ALLOWED names gone.py, which is
  not one file under src/`. All EXECUTED.

## Acceptance criteria against evidence

1. **The checks exist and were seen failing first** — met: `build/104/seen-failing.txt` records
   check 2's 15 findings and check 4's ten on the base, check 5's `runner.py: 6,220 lines, over
   1,500`, and the three named drafts (`_spare_lock`, `from ._home import _ctrl_c_watched`,
   `_stamp` twice), each one line (READ; the notes quote them). `bbdafa3` is the checks alone
   (EXECUTED, `git show --stat`).
2. **Every name once** — met: the notes record 360 found, 0 missing, 0 twice on `c15adf4` (READ);
   check 4 passes in both fast-tier runs (EXECUTED); my residue comparison found no base line
   missing from the tree but imports, the hooks' old lines and the "Last:" comment (EXECUTED).
3. **The order holds** — met: check 2 passes (EXECUTED); the by-`from` inventory of the eleven
   modules names only modules earlier in `ORDER` or `mounts` (EXECUTED, scratch `seams.py`); the
   two upward references are `if TYPE_CHECKING:` imports (`_places.py`, `_home.py`, EXECUTED);
   `import wasi_python` loads no wasmtime and imports with wasmtime blocked (EXECUTED, above).
4. **Verbatim** — met: the builder's residue script reproduces with uncategorised residue none;
   my independent comparison agrees (EXECUTED, above). The 19 formatter wraps are each a
   qualified line past 100 columns or the one trailing comment moved up a line, and each tree
   fragment reassembles to its source (EXECUTED, the old-side residue holds the 19 sources). The
   two hooks' bodies are Decision 4's text line for line (EXECUTED, `awk` of both versions):
   `_release` differs by prefixes only; `_after_fork_in_child` keeps the same statements in the
   same order with the `global` list cut to the two runner locks and `_held_lock` on its own
   line. `859dad1` changes docstrings and comments only (EXECUTED, every `+`/`-` line read).
5. **The fork hook** — met: check 1 passes (EXECUTED, the probe); `LOCKS_RESET_BY_FORK` has 12
   entries, `REBOUND_BY_FORK` 4, `NOT_RESET` 2 with `_defaults_lock` on the package root
   (READ, the file); the walk's floor is 14; the `ast` reading requires exactly the 15 names of
   the old `global` statement. The hook body holds no lock (READ).
6. **The judge's files** — met: `grep -rhoE 'runner\._\w+' tests/` finds `_checked`,
   `_check_tools`, `_current_defaults`, `_pool`, `_pool_lock`, `_stop_async_calls`, `__file__`
   and `_after_fork_in_child` (EXECUTED), as the notes say; every one of the 99
   `monkeypatch.setattr(<module>, "name", …)` sites under `tests/` (module aliases resolved) names
   something its target module defines at top level, so no patch lands on a from-imported copy
   (EXECUTED, scratch `seams.py`); the fifteen child-interpreter strings of `ea08708` each import
   every module their body reaches, and the commit's `+`/`-` lines are import lines only (EXECUTED,
   scratch `strings.py` over 59 strings, no gap; `git show ea08708 -- tests/`).
7. **Sameness** — met: both sameness runs print only the claims' note and exit 0 (EXECUTED, above);
   the three records' `suite` lines in the notes are the builder's (READ); the tier's tally is the
   builder's to the test (EXECUTED).
8. **Size** — met: the largest module is `runner.py` at 1,225 (EXECUTED, `wc -l`); check 5 passes,
   and its stale-entry and missing-file branches fail as Decision 6 asks (EXECUTED, the probe).
9. **Lint and the public surface** — met: ruff clean (EXECUTED); `tests/public_api.txt` is absent
   from `git diff --stat c15adf4..2a9546c` (EXECUTED); `api.py`'s `INTERNAL_FILES`,
   `INTERNAL_MODULES` and `DEFINING` gain the ten modules and `_wasmtime_ffi.py` (READ, the diff);
   `_defaults_loads` reads every `.py` beside `runner.py` (READ).
10. **The release** — not evidenced here by design: the chain's one dispatch on its final tip; this
    review dispatched none (the brief).

The pre-build review's seven findings are each answered in the build (READ): the tables
re-measured on `c15adf4` (1, 5), `_defaults_lock` in `NOT_RESET` (2), the lists split 12/4/2
with the `ast` assertion on 15 (3), `Session`'s reason in Decision 1 (4), the seam condition
stated and held by `_seam_errors` (6), `_wasmtime_ffi.py` in `api.py`'s tables (7).

The new lines carry no specification, memo, review, finding ID or `context/` path (EXECUTED,
scratch `cite.py` over every `+` line of `src/` and `tests/` not present in the base): the hits
are moved lines the formatter wrapped (`spec 071`, `spec 084`), retargeted lines whose comment
predates the move, the word "finding" as English, and `test_v1_4_public_api.py`'s existing
"(the build review's F2)" on a line the builder continued. The commit subjects and bodies name no
model; the trailer `Co-Authored-By: Claude Fable 5.1` is the harness's required attribution and is
the base commit `c15adf4`'s too (EXECUTED, `git log --format=%B`). The evidence folder
`context/research/2026-10-20-the-runner-split/` holds six scripts and no memo, so the
EXECUTED/READ/INFERRED rule has nothing to label there; `test_executed_memos_label_their_claims`
passes (EXECUTED). The stale docstring the builder admits (`runner.py:10`, "imported only here")
is the one I find; `runner.py:108`'s "this module's `DEFAULTS`" is still true.

## Findings, most severe first

1. **Check 3's seam condition sees only a bare module name** (`tests/unit/test_runner_package.py:302–324`,
   `_patched`; `known` at `:305–306`) — it maps the eleven module names and `wasi_python` to themselves, so a test that
   imports a runner module under another name, as `tests/unit/test_runner_tools.py:33` does
   (`_artifacts as artifacts_module`, the builder's difference 6) and patches through it
   (`:153`, `:744`), is invisible to `_seam_errors`. Low: today it patches `find_artifacts`, a
   function, which the condition does not cover, and my alias-resolving scan of all 99 sites finds
   no class or constant patched through an alias. Fix text: in `_patched`, build the map per file
   from its `from wasi_python import X [as Y]` and `import wasi_python [as Z]` statements, local
   name to module, and look the first argument up there.
   Failure: a future `from wasi_python import _call as call_module` plus
   `monkeypatch.setattr(call_module, "MAX_RESPONSE", 1)` while some module from-imports
   `MAX_RESPONSE` → the check passes and the patch misses a reader.
2. **Check 1's walk covers the modules `import wasi_python` loads, not the package** (`:109–132`,
   `FORK_WALK`) — the child imports `wasi_python`, `_engines` and `runner`; `tools`, `cli` and
   `_wasmtime_ffi` are never in `sys.modules` there, so a module-level lock added to one of them is
   found by nobody. Low: none has one today (`tools.py` holds two instance locks, the other two
   none; EXECUTED, grep). Fix text: `FORK_WALK` adds `import wasi_python.cli, wasi_python.tools,
   wasi_python._wasmtime_ffi` after `import wasi_python` (wasmtime-py is present in every judge),
   and the test's docstring says the walk loads every module of the package.
   Failure: `_lock = threading.Lock()` at module level in `tools.py`, untouched by the hook → the
   check passes; a child forked while the lock is held inherits it held.
3. **`_is_unchanging` accepts a tuple or frozenset without reading its elements** (`:265–271`) —
   Decision 2 allows "a tuple or `frozenset` of those"; the check allows any tuple, so a tuple
   holding a dict or a lock would pass as unchanging. Low: no runner module from-imports a tuple
   or frozenset today (`_TRAP_HANDLERS_REPLACED` is one `str` in parentheses; EXECUTED, the
   inventory). Fix text: for a `tuple` or `frozenset`, return `all(_is_unchanging(name, e) for e
   in obj)`.
   Failure: `_LINKERS = ({}, {})` from-imported elsewhere → the check passes and the copy's dicts
   are the same objects the hook cannot rebind.
4. **Two self-check items are unchecked** (the specification's "The builder's self-check") — "CI
   run dispatched on this exact commit" and "CHANGELOG under the one unreleased section", each
   with its reason: the chain's one-dispatch rule, and the brief's "do not touch `CHANGELOG.md`"
   with the entry's text in Design. Low, named as the README asks; the fix text is the lane's:
   at the chain's rebase, add Design's CHANGELOG entry under the unreleased section (the builder
   or the lane, whichever holds the branch), and the chain's final dispatch is this entry's run.
   Failure: none in code; a wave that lands without the entry has a runner split the CHANGELOG
   does not name.

## Constitution checks

- §4 constraints: §4.3 and §4.4 untouched (no guest, no import, no export changes; the artifact
  set is the frozen `v0.1.0a7` one in both records). §4.5 holds (no embedder name in the new text;
  `test_no_embedder_name_in_code` passes). §4.6 holds (no artifact in git; `git status` clean).
  §4.9 holds: the one new `timeout=120` is a fail-safe on a subprocess, never a verdict, as its
  comment says; `test_no_test_reads_a_clock` passes. §4.10 holds: every number in the landing
  notes carries its command and label, and the ones I re-measured agree. §4.13 holds: ruff clean,
  no dependency added. §4.14 holds: one worktree, the `spec/104-…` branch from 103's reviewed tip
  as a stacked build, not pushed. §4.15 holds: the fork hook re-makes the same locks and clears
  the same state as before, by module attribute; no default loosened.
- §7 never-do list: nothing tripped. No upstream patch, no fetch, no copy from prior art; the
  builder committed on its own branch as the brief asked and pushed nothing; every number
  reported was run (the ones I checked reproduce); no question left unanswered in the specification
  (the rules check on specifications' questions passes); scope stays Decisions 1 to 8 (the
  `_process` module, the typed call and the protocol are left to 105 to 107 as *Scope* says).

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Check 3's seam condition and module aliases — **fixed in `dcd5fbe`**: `_patched` builds its
   map per file from the file's own `import wasi_python [as Z]` and `from wasi_python import X
   [as Y]` statements, local name to module, and looks the first argument up there; the alias
   `artifacts_module` of `tests/unit/test_runner_tools.py` now resolves to
   `wasi_python._artifacts` (EXECUTED: `_patched(tests)` holds
   `("wasi_python._artifacts", "find_artifacts")`, 48 sites in all).
2. Check 1's walk and the three unloaded modules — **fixed in `dcd5fbe`**: `FORK_WALK` imports
   `wasi_python._wasmtime_ffi`, `wasi_python.cli` and `wasi_python.tools` after `import
   wasi_python`, and the test's docstring says the child loads every module of the package;
   the check passes (EXECUTED, the four checks of the file: 4 passed).
3. `_is_unchanging` and a tuple's elements — **fixed in `dcd5fbe`**: a `tuple` or `frozenset` is
   unchanging only when `all(_is_unchanging(name, element) for element in obj)`; `int`,
   `float`, `str`, `bytes` and `re.Pattern` stay as they were.
4. The two unchecked self-check items — **answered in writing**, not fixed in code: the CI run is
   the chain's one dispatch on its final tip (the owner's rule for the chain; 104 dispatches
   none), and the CHANGELOG entry (its text in Design) is left for the integrator at the chain's
   rebase, since the builder's brief said not to touch `CHANGELOG.md`. The landing notes say
   both.

## Verdict

Lands: the move is verbatim by two independent readings, the fast tier on the frozen set is the
baseline's 83 to the node id, sameness prints nothing outside the claim, and the four findings
are Lows with their fix text, none needing a round.
