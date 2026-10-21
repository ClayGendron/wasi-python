# Review of 111 — the filesystem along the WASI seams

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent (pre-build reviewer; wrote none of 111, none of the chain 103–109)
- **Reviewed:** the specification as drafted,
  `context/specifications/111-the-filesystem-along-the-wasi-seams.md` at `330c09f` on
  `spec/111-the-filesystem-along-the-wasi-seams`, worktree `/home/user/wt/111`; the tree read is
  `b14b68c` (the chain's tip before its rebase onto main), which the specification names as the
  tree it measured
- **Run:** none (pre-build review of the draft; no build, no dispatch)
- **Re-ran:** `uv sync` → a fresh `.venv`; `uv run pytest tests/checks/test_rules.py -k
  "specifications or open_question" -q -p no:cacheprovider` → 4 passed, 54 deselected, exit 0;
  five rules checks by node id (the ceiling, 107's import rule, 105's mutable scan, 108's seam
  check, 108's function ceiling) → 5 passed; two mounts unit rows by node id
  (`test_the_rename_is_forwarded_by_its_plain_names`, `test_a_listing_is_counted_as_what_it_holds`)
  → 2 passed; my own measurement script over `_Files` (`ast`, callers and `self` attributes per
  method) and a probe of `scan.module_mutable_hits` on a stand-in `HANDLERS` module. No fast
  tier. Time box: 25 minutes (parallel-safe), kept at the box with the Structure section in it.

Precedent form: `107-mounts-behind-a-protocol-and-one-platform-module-spec-2026-10-20.md`.

## Verified, not trusted

Each line says what I did: EXECUTED (a command on `b14b68c` in the worktree), READ (the file at
the line named) or INFERRED (reasoning from those).

1. **The measurements.** EXECUTED, my own script: `_Files` is lines 622–2093, 1,472 lines, 84
   methods; the method lines sum to 1,359; `__init__` binds 22 attributes, the ones listed; the
   longest methods are `_path_open` 78, `_open_writing` 56, `__init__` 53, `_list_answer` 52,
   `_zeroed` 48, `_path_rename` 43; none over 80. The writer's `build/111/measure.py` re-run
   gives the five families exactly as the specification prints them (`fd_*` 27 / 395, `path_*`
   25 / 514, table 12 / 161, bridge 14 / 199, memory and forwards 6 / 90). My script assigns
   helpers by their callers rather than by hand and so puts `_take`, `_at_cap`, `_stat`,
   `_read`, `_change`, `_path`, `_text`, `_resolve` on the path side and `_drop`, `_iovecs` on
   the descriptor side (`path_*` 35 / 605, `fd_*` 28 / 402): a different cut of the same 1,359
   lines, not a contradiction; the writer's cut is the one Decision 1 builds on (those helpers
   are the table's and the memory's), and it is consistent. The state matrix holds under both
   cuts: with the writer's families, `fd_*` writes `staged` only (`_changed` 1329, `_fd_readdir`
   1497) and `path_*` writes `staged` only (`_unlink` 1893); the one cross-family call is
   `_path_filestat_get` → `_filestat` (callers of `_filestat`: `_fd_filestat_get`,
   `_path_filestat_get`). The ten by-hand writes Decision 1 replaces are exactly the ten my grep
   finds in the two families (EXECUTED, `self\.[a-z_]+ ?[-+]=|self\.[a-z_]+\[…\] ?=|del self\.|
   \.(add|discard)\(` over lines 1152–2093): `held.discard` 1192, `del table[…]` 1211,
   `owed[…] =` 1212, `staged +=` 1329, 1497, 1893, `held.discard/add` 1573–1576, `held.add`
   1602. Import graph: EXECUTED `grep -n mounts src/wasi_python/*.py` matches the
   specification's list line for line (`__init__.py:32`, `_call.py:31/38/424/898/921/940/952`,
   `_places.py:19`, `_sessions.py:42/49/1042`, `runner.py:39`); out of `mounts.py` only
   `_wasmtime_ffi` at 767, 783, 820. The runner's uses of the table: EXECUTED `grep table\.`
   over `_call.py` and `_sessions.py`: `walk`, `record`, `release`, `bind`, `new_turn`,
   `stop_fuel` (507), `context` (780), `session` (`_sessions.py:1063`), `__call__` (643), the
   constructor, `open_now` — eleven. The patches: EXECUTED, `_Files.__call__` (501), `forward`
   (771, 821, 915), `_source_type` (914), and no other `setattr` on a `mounts` name in `tests/`.
   `tests/harness/files.py:654` and `:713` import `_Files`; `test_runner_mounts.py` reaches
   twelve names through `mounts_module` with the counts the specification gives (EXECUTED,
   `grep -o | uniq -c`). Types: 69 `Any`, 2 `type: ignore` (496, 1995), 2 `cast`. EXECUTED.
2. **The checks the plan reads.** READ: `ALLOWED` at `test_rules.py:163`, keyed by `p.name`;
   `_runner_modules_but_the_owner` at 192, `package.glob("*.py")` at 194; `_platform_hits` at
   868 with `package.glob("*.py")`; `MOUNTS_MAY_IMPORT` 818, `_sibling_imports` 821 (it reports
   `TYPE_CHECKING` imports as hits today, so the typing column is new work, as the plan says),
   `test_mounts_imports_only_the_engine_seam` 849; `SEAM_ALLOWED` 974 with eighteen names and
   none of `mounts.py`; `LONG_FUNCTIONS` 1021 with nine keys and none of `mounts.py`;
   `scan.RUNNER_MODULE` `^wasi_python\.(runner|mounts|_\w+)$` and `SEAM_BY_PATH` (`scan.py`
   ~1967–1971): a dotted subpackage name would not match, as Decision 3 says;
   `scan.READ_ONLY_DISPLAYS = (ast.Dict, ast.List, ast.Set)` and `module_mutable_hits` admit an
   upper-case name bound to one of them; `api.py` `RUNNER_FILES`, `INTERNAL_FILES`,
   `INTERNAL_MODULES`, `DEFINING` (39–65) by bare filename. The seam scanner (`_seam_sites`)
   resolves `setattr`'s first argument through `_dotted` and `_runner_module`: `mounts_module.
   _Files` is not a module, so the class-attribute patch is not a site today, and a
   `setattr(_fs_paths, "_source_type", …)` would be one. READ.
3. **`HANDLERS` under 105's check.** EXECUTED, a probe of `scan.module_mutable_hits` on two
   stand-in files: `HANDLERS: dict[str, Callable[..., int]] = {…}` and `HANDLERS =
   {**_fs_descriptors.HANDLERS, **_fs_paths.HANDLERS}` produce no hit; a lower-case `handlers =
   {}` beside them is reported. The `**` union is an `ast.Dict` with `None` keys, which the
   scanner treats as a display. The plan's "read-only upper-case display 105 admits" holds.
4. **The flat-reading list** (Decision 3). READ, each of the five is as described; the four that
   read whole (`scan.files_under` / `rglob`, `mypy`'s directory target) are too. No judge check
   holds 104's import order as a list (EXECUTED, `grep -n order` over `test_rules.py` and
   `scan.py`: nothing; 104's Decision 2 is a document rule and its order places `mounts` beside
   the list, where the four new modules also stand). The new modules go to `INTERNAL_FILES` and
   `INTERNAL_MODULES`, not `RUNNER_FILES`, and `DEFINING` keeps `mounts.py`: consistent with the
   lists' meaning (`future_errors` walks `DEFINING`; `internal_names` walks `INTERNAL_FILES`).
   `test_api_lists_every_module_of_the_package` is green today: EXECUTED, 18 files under the
   package, 18 in `DEFINING ∪ INTERNAL_FILES`, no difference either way.
5. **The GC row** (`test_runner_mounts.py:596–620`). READ: it counts `_Call`, `_Files` and
   `_Open` with the collector off and wants zero left. A module-level function in `HANDLERS`
   references nothing of an instance; an instance references no handler; so no cycle is added.
   INFERRED, from the plan's shape.
6. **`mounts.py` after.** READ 50–318, 530–621: the public types, the errno table, `_Listing`,
   `_Mounted`, `_Open` and `_CallContext` use no name of the WASI tables or numbers (the
   upper-case names in 50–262 are `Errno`'s members only), so `mounts.py` can import nothing of
   the package and sit at the bottom of the chain, as Decision 2 says. `_T` (used by `_home`)
   and `_Forwards` go with the table and the memory. `from __future__ import annotations` is
   present (line 36), so the `TYPE_CHECKING` import of `_fs_table` from the handlers is a string
   annotation at runtime.
7. **The one seam that moves** — see "Point 3" below.

## Acceptance criteria against evidence

For a draft, "met" means the criterion is countable, the judge can check it, and the facts it
rests on are true at `b14b68c`.

1. **Modules exist, sizes recorded, all under 1,500; `ALLOWED` without `mounts.py`** — met as
   written; the sizes are INFERRED and labelled so. READ.
2. **The split is a move, non-moves listed** — met as written: `--color-moved=dimmed-zebra`
   and a list of the non-moved lines. READ.
3. **Handlers change no table state by hand, by one grep** — **not met as written**: the grep
   misses the forms the ten writes take today (finding 1).
4. **Dispatch equals the signatures** — met: the unit row is exact (two tables disjoint, union
   equal to `SIGNATURES`, each a function named `_` + key with first parameter `files`, no
   `_Files` attribute of that name). READ.
5. **Allowances shrink, import rule holds the group** — met: `FILESYSTEM_IMPORTS` as a chain,
   runtime and typing columns, the stale-name rule; `grep -nE 'from \.|import wasi_python'
   src/wasi_python/mounts.py` empty after. EXECUTED today: three lines (767, 783, 820), so the
   check is seen red first as the plan says.
6. **Three unit rows and the lists row seen failing first** — met: each names its red state.
   READ.
7. **No function over 80** — met; `_path_open` is 78 today and stays 78 (note 1).
8. **Test seams accounted for** — met in substance; "import lines only" for `_call.py` leaves
   three docstring tokens stale (finding 3).
9. **No verdict moved** — met as written: `sameness.py --claims` with the claim list of six
   rows and five judge-hash lines. READ.
10. **`tests/public_api.txt` unchanged** — met: the eight names keep their module and
    docstrings; `api.DEFINING` keeps `mounts.py`. READ.
11. **ruff, mypy, `Any` ≤ 69, ignores ≤ 2** — met: today's counts are exactly those (EXECUTED);
    the split adds `files: _Files` annotations, not `Any`, and the `cast` in `__call__` leaves.
12. **The dispatch, run id in the notes** — met as written.

## Findings, most severe first

1. **AC3's grep does not catch the writes it guards against** (`111 …md`, Acceptance criterion
   3; Decision 1, "no `files.<field> =`") — Medium. The pattern
   `files\.[a-z_]+ ?=[^=]|files\.[a-z_]+\.(add|discard|pop|clear|append|update)\(|del files\.`
   matches a plain assignment, a mutator call and a `del`, but not an augmented assignment
   (`files.staged += n`) or a subscript store (`files.owed[n] = entry`, `files.table[n] = e`),
   and those are three of the ten by-hand writes today (EXECUTED: `mounts.py:1212`, 1329,
   1497, 1893). The plan moves every one of them into the table, so the built code should pass
   a correct grep; but the criterion as written would also pass a handler that re-grows
   `staged` by hand, which is the one thing Decision 1 promises cannot happen. Evidence that
   closes it: the criterion's pattern widened to the five forms, recorded empty per module.
   Text to write in, replacing the command in criterion 3:
   `grep -nE 'files\.[a-z_]+(\[[^]]*\])? ?([-+*/|&^%]|<<|>>)?=[^=]|files\.[a-z_]+\.(add|discard|pop|clear|append|update|remove|extend|setdefault)\(|del files\.' src/wasi_python/_fs_descriptors.py src/wasi_python/_fs_paths.py`
   — and one sentence after it: "the five forms are a plain assignment, an augmented one, a
   subscript store, a mutator call and a `del`; a `files.<field>` read is not a hit."
2. **"Three new modules" where there are four** (Decision 1's title and line 143; Decision 2
   line 229; Decision 3 lines 254, 274, 278; Decision 5's failing-first line 325, "three
   modules not found"; the lists row, "the commit that adds the three modules"; the
   `mounts.py` docstring sketch, line 472; For the lane, line 626) — Low. The module table,
   the import chain, `FILESYSTEM_IMPORTS`, the CHANGELOG line, the roadmap line, Decision 7
   ("four nodes") and the One line all count four (`_fs_memory`, `_fs_table`,
   `_fs_descriptors`, `_fs_paths`); the prose says three at nine sites. Fix: "four" at each,
   and "four modules not found" at 325. **Written in by the reviewer** (second commit).
3. **`_call.py`'s docstrings name `mounts.SHADOWED`, `mounts.GUARDED`, `mounts.COUNTED`**
   (`src/wasi_python/_call.py:895`, 916, 917; EXECUTED grep) — Low. After the split those names
   live in `_fs_memory`, and "import lines only" (For the lane; criterion 8's "import paths that
   move") would leave the three tokens stale; `api.py`'s `INTERNAL_MODULES` scan reads only the
   dotted `wasi_python.mounts` form, so nothing red would say so. `mounts._CallContext` at 728
   stays true. Fix text, in The problem's import paragraph after "`tools.py` imports nothing of
   it": "Three docstrings of `_call.py` name the tables by module (`mounts.SHADOWED` 895,
   `mounts.GUARDED` 916, `mounts.COUNTED` 917) and read `_fs_memory.` after the move;
   `mounts._CallContext` at 728 stays." and in For the lane, "`_call.py` … (import lines and
   three docstring tokens only)". **Written in by the reviewer** (the specification's text;
   the code change is the builder's).
4. **The handlers' read surface is not named** (Decision 1, "The table's interface for the
   handlers") — Low. The write half is named (ten methods, five new) and AC3 holds it; the read
   half is "a handler reads the table's fields". After the five moves the handler modules read
   six fields directly (EXECUTED, per-method attributes of the methods that stay: `context`
   in `_fd_readdir`, `_path_open`; `forwards` in `_zeroed`, `_source_type`; `held`, `mounts`,
   `table` in `_fd_renumber`, `_fd_close`; `opened` in `_path_open` at 1632). Naming them
   lets the build review hold the seam's width in one line. Text to add after the by-hand
   writes sentence: "A handler reads six fields of the table and no other: `context`,
   `forwards`, `held`, `mounts`, `opened` and `table` (EXECUTED, the methods that stay after
   the five moves); the builder records the per-module list with the grep of criterion 3."
   **Written in by the reviewer.**

Notes (no action required):

- *Note 1.* `_path_open` stays at 78 lines, not 79: `self,` has its own line in the signature
  and becomes `files: _Files,` (READ, `mounts.py:1581–1593`). Decision 4's fallback is
  therefore unlikely to be needed; harmless either way.
- *Note 2.* The moved race injection fires on any `path_filestat_get` forwarded with
  `stat=True` that answers 0, folder or not, where today's fires only after `_source_type`
  returns 0 (a folder). In the row the source is always the folder `d`, and `_rename` forwards
  one stat per call, so the row exercises the same race; the builder may narrow the condition
  with `args[2] == STAT_PATH` but need not.
- *Note 3.* The CHANGELOG and roadmap lines are proposed in Design and not yet in
  `CHANGELOG.md` or `context/roadmap.md` (EXECUTED grep: no 110 or 111 line in either). The
  chain's lines went in at its rebase commit (`1b85fe1`), so this follows the precedent; the
  builder adds them at build.
- *Note 4.* The dispatch's cost: `HANDLERS[name](self, caller, *args)` is one dict lookup and
  one call; today's `getattr(self, "_" + name)` is a string concatenation, a class-dict lookup
  and a bound-method allocation, plus a `cast`. Host-side Python time is not metered and no
  check counts wall-clock, so no fuel row and no verdict moves; the guest's fuel is the
  guest's. If anything the hot path gets cheaper. INFERRED.
- *Note 5.* An alternative the plan does not weigh, for the builder's judgement rather than a
  change: the handlers could annotate `files` with a small protocol (`_Table`, the six fields
  and the fifteen methods) in place of the `TYPE_CHECKING` import of `_fs_table`, which would
  make the seam a type the checker holds and drop the one upward import. It would need
  `_Forwards` and `_Open` in its signatures, so it would live in `_fs_memory.py` or `mounts.py`;
  the plan's `TYPE_CHECKING` import is the simpler move and is what 104 allowed for the two
  upward annotations. Either is fit.

## Point 2: the shape (the hardest look)

- **Is the table's surface a real seam or the whole object leaking through underscored
  names?** A real seam on the write side and a narrow one on the read side, by measurement.
  Writes: after the five moved methods and the five new ones, the handlers change the table's
  state through methods only (the ten by-hand writes today are exactly the ones Decision 1
  names; EXECUTED). Reads: six fields (finding 4), of 22. Methods: about fifteen of the table's
  (`_entry`, `_take`, `_drop`, `_at_cap`, `_gate`, `forward`, `_stat`, `_read`, `_list`,
  `_change`, `_made`, `_write_back`, `_fits`, `_changed`, `_hold`, `_unhold`, `_renumbered`,
  `_owe`, `_relist`, `_follow`; `_gate` only through `_write_back`). That is wider than a
  textbook interface but it is one direction (handlers → table, the table reaching a handler
  only through `HANDLERS`), and every invariant of the state (`staged` is the sum of `held`;
  `opened` counts the table and the owed; `held` ⊆ wasmtime's numbers) is kept in one file.
  The underscores are the plan's explicit deferral ("a move is a move"); they mark "not the
  runner's", which stays true. Fit.
- **Would two small classes be clearer?** No, for the reasons the plan gives and one more.
  A `_Descriptors(files)` holds no state of its own (the measured writes are one attribute per
  family and both move into the table), so its only field would be the table: a parameter with
  a longer name. It would also hold a back reference, which the GC row refuses (READ,
  `test_runner_mounts.py:596`). And the two families never call each other but for
  `_filestat`, which the plan makes a pure function, so there is no shared behaviour for a
  class to carry. Free functions are the honest shape of what is there.
- **Is `HANDLERS` a module-level mutable 105 refuses?** No: EXECUTED probe (verified item 3),
  both the annotated display and the `**` union pass `module_mutable_hits`; the admission is by
  name case and node type, and the plan's dicts are only read. The unit row of criterion 4
  holds them equal to `SIGNATURES`, so a stray key or a missing one is red.
- **Does the dispatch cost anything on the hot path?** Less than today's `getattr` (note 4);
  fuel is the guest's and unaffected.
- **`_Mounted`, `_Open`, `_Listing` in `mounts.py`?** Right. They use nothing of the ABI
  (verified item 6), they are the private shapes of the public `Mount` and a provider's file,
  and the graph needs them below both the table and the handlers (the handlers construct
  `_Open` at four sites at runtime). `_fs_memory.py` would also be acyclic but would make the
  ABI module hold a descriptor's record, which is not bytes.

## Point 3: the seam that changes shape

READ `test_runner_mounts.py:884–928` and `mounts.py:2021–2069`. Today `swapped` wraps
`_Files._source_type` and swaps the folder `d` for the link `d -> ../outside` after the real
`_source_type` returns 0; `recorded` wraps `forward` and records the `path_rename` arguments.
`_source_type` does three things: writes the source path to the stat page, forwards
`path_filestat_get` with `stat=True`, and reads the filetype byte from the page. The plan moves
the swap into `recorded`, after a `stat=True` `path_filestat_get` forward answers 0.

- *The same race?* Yes. The race is "the host folder is replaced between wasmtime's stat and
  wasmtime's rename". Both injections sit between those two host calls: today's after the
  filetype read, the plan's before it. The filetype read is of the guard page in the guest's
  memory, written by the stat that already returned; the swap changes the host filesystem, not
  that page, so `_source_type` still answers 0 and `_rename` still forwards the plain names.
- *Exactly once?* Yes. `r.rename(3, "d/", 3, "stolen//")` on a `Guarded` table with grants
  only: `_path_rename` finds both entries `None` and goes straight to `_rename`, which forwards
  one stat (the source) and one rename. The destination is never stat-ed, so the swap cannot
  fire twice (a second `os.rmdir` would raise). The `fd_readdir` path is not taken.
- *The assertions unchanged?* Yes: the forwarded names `(b"d", b"stolen")`, the grant holding
  only `stolen`, the link reading `../outside`, the canary untouched. None depends on which
  wrapper did the swap. `recorded`'s signature already carries `stat`.
- *Under 108's seam check?* Both patches stay class attributes of `_Files`
  (`mounts_module._Files` → after the move `_fs_table._Files`), which `_seam_sites` does not
  resolve to a module, so `SEAM_ALLOWED` is untouched and the check stays green. A patch of
  `_fs_paths._source_type` would be a site and red, as the plan says.

Not a High. Note 2 records the one width difference, which this row cannot reach.

## Point 4: the import chain and the checks that must accommodate four modules

- Acyclic by name use (READ): `mounts` imports nothing of the package (item 6); `_fs_memory`
  needs `mounts` at most; the handlers need `mounts` (`_Open`, `_Mounted`) and `_fs_memory`
  (the numbers, `_Memory`, the readers) at runtime and `_fs_table` for one annotation; the
  table needs all four and the engine seam inside three methods. A chain.
- 107's rule becomes `FILESYSTEM_IMPORTS`: the only runtime import of a runner module in the
  five rows is `_wasmtime_ffi` in `_fs_table.py`, so "the filesystem imports nothing from the
  runner but the seam" still holds, reachable from one module of the five. READ.
- 104's `ALLOWED` by `p.name`: loses `mounts.py`; the stale-entry rule keeps `tools.py` honest
  until 110. 105's `glob("*.py")`, 107's `_platform_hits` `glob("*.py")`: both see flat
  siblings. 108's `RUNNER_MODULE` `_\w+` matches `_fs_table`, `_fs_paths`, `_fs_descriptors`,
  `_fs_memory`. `api.py` lists: `INTERNAL_FILES`/`INTERNAL_MODULES` gain four, `DEFINING`
  unchanged, `RUNNER_FILES` unchanged (the filesystem stands beside 104's order, as `mounts`
  does). No judge check holds 104's order as a list (EXECUTED grep). READ/EXECUTED.
- The GC row: no back reference (item 5).

## Structure (108's rubric, applied to the planned result)

Decision 7 is right that this is not **structural** by 108's five triggers (no mutable or lock,
no private-API use, no platform branch, no new seam, no ceiling crossed; two allowances shrink);
it is runner code and reviewed before build under rule 8. The rubric applied anyway, before and
after, with the measurements EXECUTED on `b14b68c`:

| what | now (`b14b68c`) | planned | command |
|---|---|---|---|
| module sizes | `mounts.py` 2,206; `tools.py` 2,449; 12,870 in all | `mounts.py` ~380, `_fs_table.py` ~640, `_fs_paths.py` ~560, `_fs_descriptors.py` ~450, `_fs_memory.py` ~340 (INFERRED by the writer) | `wc -l src/wasi_python/*.py` |
| functions over 80 | `runner.py` 4, `_call.py` 1, `_process.py` 1, `_sessions.py` 1, `tools.py` 2; `mounts.py` 0 | unchanged | the `ast` one-liner |
| module-level mutables and locks | 0 lines | 0 (`HANDLERS` ×3 admitted by name; probe EXECUTED) | the `grep -rnE` |
| private-API uses | `_wasmtime_ffi.py` 84, `_places.py` 1, `tools.py` 1; `mounts.py` 0 | unchanged; `_fs_table.py` reaches the seam only | the `grep -rnE` |
| platform branches | 0 in `mounts.py` | 0 | `grep -nE 'sys\.platform\|os\.name'` |
| private names the judge patches | 30 distinct; on `mounts`: `_Files._source_type`, `_Files.__call__` (class attributes) | `_source_type` patch gone | the `monkeypatch.setattr` grep |
| `Any` / `type: ignore` | 338 / 25 in all; `mounts.py` 69 / 2 | ≤ 69 / ≤ 2 over the five | `grep -rc` |
| citations of the archive | 0 | 0 | `grep -roE 'spec [0-9]{3}'` |

| row | now | planned | reason |
|---|---|---|---|
| R1 Contract | Strong | Strong | `public_api.txt` byte-identical; `__all__` unchanged; the eight types keep their module and docstrings |
| R2 Safety | Strong | Strong | no errno, limit or default moves; the state's invariants (`staged`, `opened`, `held`) are kept by one file's methods instead of by hand in two families; the rename guard's check-and-use is unchanged |
| R3 Layering | Adequate (after 103/107) | Adequate, firmer | the filesystem is a five-module chain with `mounts.py` at the bottom; the engine's private API still reached through `_wasmtime_ffi` from one of the five; one upward annotation under `TYPE_CHECKING`, 104's allowed form |
| R4 Process state | Adequate (after 105) | Adequate | no new module-level mutable; `HANDLERS` are read-only tables; nothing of the lifecycle moves |
| R5 Portability | Strong (after 107) | Strong | no platform branch in any of the five |
| R6 Testability | Adequate | Adequate, firmer | one class-attribute patch of a private name becomes none; three unit rows drive the memory, the table's numbers and the dispatch without wasmtime; two `forward` patches and one `__call__` patch stay, on a class, outside 108's rule |
| R7 Evolvability | Adequate | Adequate, firmer | 2,206 lines become five files of one concern, none over ~640; no function over 80; the dispatch is a table a reader diffs against `SIGNATURES`; `Any` does not grow; the directory's trigger is written |
| R8 Operability | Strong | Strong | `record()`, `FileRecord`, the trap strings and the fuel rule untouched |

Nothing in the plan should change on the rubric's account. The rows it moves are R3, R6 and R7,
each toward Strong, as Decision 7 says.

## Constitution checks

- §4 constraints: no patch, no pin, no artifact, no prior art copied; `src/` keeps "code speaks
  for itself" (the sketches carry no specification number; the new docstrings say the concern);
  §4.14, one specification per branch and worktree. Holds.
- §5.6: runner code, so reviewed before build; this is that review. §5.2 no open question
  (EXECUTED, the rules checks). Holds.
- §7 never-do list: nothing tripped; the judge is changed only where a reason is written
  (two allowances shrink, one rule becomes a table, four rows are added), and no existing
  expectation is edited.

## Document hygiene

Header fields present (Status, Date, Owner, Kind with reason, Depends on, Research); Kind
parallel-safe with the build-class test stated; Depends on 104, 107, 108 and 110 by order only;
the CHANGELOG line and the roadmap line proposed in Design (note 3);
`test_specifications_have_their_header_and_sections` and `test_specifications_have_no_open_question`
green (EXECUTED). The new modules' docstring sketches name their concern and no document.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 (Medium, AC3's pattern) — the writer writes the widened command in.
2. Findings 2, 3, 4 (Low, the specification's text) — written in by the reviewer, second
   commit on this branch, the exact text above.

## Verdict

Fit to build once finding 1 is written in: the measurements hold under my own cut, the shape is
the honest one for what is there, the moved race injection exercises the same race with the
same assertions, the chain is acyclic and every flat-reading check sees the four new modules;
the one gap is that criterion 3's grep would not catch the writes Decision 1 forbids.

## Confirmation

- **Read:** `git diff 668026c b75c3a7` (the specification only, +84 −14). READ.
- **Finding 1 (Medium), confirmed written in.** Decision 1 names the five forms of a write and the
  ten sites (the same ten my grep found, by line); Decision 5's row 7,
  `test_the_handlers_change_the_table_only_through_its_methods`, is an AST walk with no
  allowance, seen failing with ten hits on the verbatim move; criterion 3 cites the row as the
  judge and records the widened grep as the record; criterion 6, Design's commit 3, the claim
  list, the accept-judge flag and the Kind line count the row. EXECUTED, a probe of the walk as
  row 7 describes it (`Assign`, `AnnAssign`, `AugAssign` and `Delete` targets that are an
  `Attribute` or `Subscript` chain rooted at the name `files`; a `Call` of `files.<field>.<m>`
  with `<m>` among the nine mutators) over a scratch snippet: eight hits, one per form — a plain
  assignment, an augmented one, a subscript store, an attribute store under a subscript
  (`files.table[fd].held = 1`), a mutator call, a `del`, an annotated assignment and a nested
  subscript store (`files.forwards.slots[fd] = 1`) — the four my grep missed among them; and no
  hit on a read (`files.staged + 1`), a non-mutator call (`files.table.get`,
  `files.context.name_end`, `files.forwards.page.write`), a call of a table method
  (`files._hold`), or a row's field (`entry.held = 2`). The row holds what the criterion promises.
  One edge, for the build reviewer's eye and not a finding: a write through a local alias
  (`x = files.held; x.add(fd)`) is outside the rule as written, as its "rooted at the name
  `files`" says; no handler today aliases a table field to mutate it (the one alias,
  `forwards = self.forwards` in `_source_type`, writes the guard page, not the table), and the
  build review reads for the pattern.
- **Findings 2–4 (Low), confirmed** as written in at `668026c`; the Disposition restates each
  correctly.
- **Note 5, the placement: the writer is right and I was loose.** A `_Table` protocol names
  `_Forwards`, which the plan puts in `_fs_memory.py`; `mounts.py` is the bottom of the chain and
  imports nothing of the package (verified item 6), so the protocol cannot live there without
  either a cycle or an `Any` where the type should be. `_fs_memory.py` is its one home. The
  Disposition's "builder's option, `TYPE_CHECKING` import the default" is the right disposition.
- **Notes 1–4** acknowledged as I meant them.
- **Hygiene:** `uv run pytest tests/checks/test_rules.py -k "specifications or open_question"
  -q -p no:cacheprovider` on `b75c3a7` → 4 passed, 54 deselected. EXECUTED. The Status line now
  cites this review and says what each party wrote in.

**Verdict, confirmed: fit to build.** Nothing remains open; the build review reads the handler
modules for an aliased write beside row 7's green line.
