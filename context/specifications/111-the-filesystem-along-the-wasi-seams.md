# 111: the filesystem along the WASI seams

- **Status:** **drafted 2026-10-21** on `spec/111-the-filesystem-along-the-wasi-seams` from
  `b14b68c` (the chain's tip before its rebase onto main), awaiting its pre-build review. The
  worktree is `/home/user/wt/111`; the measurements are scripts under `build/111/` there
  (`measure.py`, `helpers.py`), each run on `b14b68c` and labelled EXECUTED; a number not yet
  measured is labelled INFERRED. **Reviewed before build** the same day
  (`../reviews/111-the-filesystem-along-the-wasi-seams-spec-2026-10-21.md`, "fit to build once
  finding 1 is written in"): the Medium written in by the writer, the three Lows by the
  reviewer, each in its *Disposition*. A different agent reviews the build.
- **Date:** 2026-10-21
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**: `src/` only, plus unit checks, three rules checks and the harness's
  import paths. It **changes no line of `tests/public_api.txt`**, no artifact byte, no errno a
  guest sees, no golden output, no gap, no allowance but the two that shrink, and no progress
  file. Build-class it is not: it touches nothing under `scripts/`, `recipes/`,
  `downloads/SHA256SUMS` or the release workflow. It is runner code, so its pre-build review is
  required (AGENTS.md, rule 8); Decision 7 says why it is not structural by 108's five triggers,
  and why the reviewer may still apply 108's rubric.
- **Depends on:** **104** (the runner as a package, the module ceiling and its `ALLOWED` list),
  **107** (`mounts.py` behind the `_CallContext` protocol, the rule that it imports only the
  engine seam) and **108** (the function ceiling, the seam check, what "structural" means). On
  **110** (the split of `tools.py`, drafted in parallel) by order only, not by code: the two touch
  different files but for two lines of `tests/checks/test_rules.py` (Decision 8). Landed and
  unchanged by this: 032, 034, 048 and 068 (the mount table, its write half, the guard and the
  open-file cap, which the table serves), 103 (the engine seam the forwards use).
- **Research it stands on:** `../research/2026-10-20-a-design-review-of-the-runner.md` (its rows
  on `mounts.py`: H4 and section 5's "no module over 1,500 lines, no function over 80"; R3 and R7
  of the rubric), and the owner's direction of 2026-10-21, after the chain landed on the PR branch:
  split `_Files` along the WASI interface's own seams so each part is one concern under the two
  ceilings, as free functions over the table or two or three cooperating classes, never mixins;
  stay flat, with a private subpackage reserved for the day the filesystem group has its own
  internal API; move no verdict; remove `mounts.py` from the ceiling's allowance, which only
  shrinks.

## The problem

`src/wasi_python/mounts.py` is 2,206 lines (EXECUTED, `wc -l`), the second of the two modules
spec 104's ceiling check still allows past 1,500 (`ALLOWED = {"mounts.py": 2206, "tools.py":
2449}`, `tests/checks/test_rules.py:163`). 104's reviewer allowed it because it was one concern,
the wasi-libc emulation layer. It is three concerns and a vocabulary. Measured by section
(EXECUTED, `build/111/helpers.py`, line ranges of `b14b68c`):

| lines | what | size |
|---|---|---|
| 1 to 49 | the module docstring and the imports | 49 |
| 50 to 262 | the public types: `Errno`, `Stat`, `FileProvider`, `WritableFileProvider`, `Mount`, `FileFault`, `RefusedWrite`, `FileRecord` | 213 |
| 263 to 318 | the errno-by-name table: `_errno_table`, `_HOST_ERRNO`, `_RAISED`, `_raised` | 56 |
| 319 to 449 | the WASI tables and numbers: `SIGNATURES`, `SHADOWED`, `FORWARD_SAFE`, `GUARDED`, `COUNTED`, `PRIVATE`, the limits, the preview1 errnos, the open and fd flags, the rights, the struct formats | 131 |
| 450 to 488 | the two trampolines' WAT builders | 39 |
| 489 to 529 | the ABI argument checks: `_ends`, `_unsigned`, `_flags`, `_enum`, `_lookup`, `_rights` | 41 |
| 530 to 576 | the records: `_T`, `_Listing`, `_Mounted`, `_Open`, `_Forwards` | 47 |
| 577 to 606 | `_Memory` and `_aligned` | 30 |
| 607 to 621 | the `_CallContext` protocol (107) | 15 |
| 622 to 2093 | **`_Files`**: 84 methods | **1,472** |
| 2094 to 2195 | module helpers: `_plain`, `_zero_pads`, `_described`, `_grow`, `_dots`, `_kind`, `_number`, `_listed`, `_close` | 102 |
| 2196 to 2206 | `__all__` | 11 |

**`_Files` by WASI family** (EXECUTED, `build/111/measure.py`: each method's length is `end_lineno
- lineno + 1`, def to last line; the helpers are grouped with the family that calls them):

| family | methods | lines | what |
|---|---|---|---|
| `fd_*`, the descriptor calls | 27 | 395 | `_fd_advise` to `_fd_renumber` (19 handlers), with `_filestat`, `_write_back`, `_sync`, `_fits`, `_changed`, `_reads`, `_writes`, `_zeroed` |
| `path_*`, the path calls | 25 | 514 | `_path_open` to `_path_link` (10 handlers), with `_resolve`, `_open_writing`, `_create`, `_refused`, `_read_paths`, `_texts`, `_namespace`, `_above`, `_follow`, `_unlink`, `_across`, `_wasmtime_folder`, `_wasmtime_writable`, `_rename`, `_source_type` |
| the table: preopens, numbers, the lifecycle | 12 | 161 | `__init__`, `open_now`, `_at_cap`, `new_turn`, `record`, `walk`, `release`, `__call__`, `_entry`, `_gate`, `_take`, `_drop` |
| the provider bridge | 14 | 199 | `_home`, `_invoke`, `_change`, `_made`, `_refuse`, `_fault`, `_bad`, `_stat`, `_stat_answer`, `_read`, `_read_answer`, `_list`, `_list_answer`, `_listing_raised` |
| memory and the host forwards | 6 | 90 | `bind`, `forward`, `_path`, `_text`, `_iovecs`, `_result` |

The method lines sum to 1,359; the rest of the class is its docstring, the section comments
and the blank lines between methods.

**The shared state, per family.** The table binds 22 attributes in `__init__` (EXECUTED:
`calls`, `context`, `engine`, `faults`, `forwards`, `free`, `held`, `limit`, `metered`, `mounts`,
`next`, `open_files`, `opened`, `owed`, `refused`, `refused_total`, `session`, `staged`,
`staging`, `stop_fuel`, `table`, `total`). Which family reads and writes which, and which
methods of another family it calls (EXECUTED, the same script):

| family | reads | writes | calls into other families |
|---|---|---|---|
| the table | 17 of the 22 | all 22 | the bridge: `_made`, `_refuse` (from `walk`) |
| the bridge | `calls`, `context`, `faults`, `refused`, `staged`, `staging` | `refused_total`, `total` | the table: `_gate` |
| memory and forwards | `context`, `engine`, `forwards`, `metered` | `forwards`, `stop_fuel` | none; `_path`, `_text`, `_iovecs`, `_result` read nothing of `self` |
| `fd_*` | `context`, `forwards`, `held`, `mounts`, `owed`, `staged`, `staging`, `table` | `staged` (in `_changed` and `_fd_readdir`) | the table: `_entry`, `_drop`, `_gate`; forwards: `forward`, `_iovecs`, `_result`; the bridge: `_list`, `_made` |
| `path_*` | `context`, `forwards`, `held`, `opened`, `owed`, `table` | `staged` (in `_unlink`) | the table: `_entry`, `_take`, `_at_cap`; forwards: `forward`, `_path`, `_text`, `_result`; the bridge: `_stat`, `_read`, `_list`, `_change`; `fd_*`: `_filestat` |

So the seams are real. The two big families, 909 lines together, reach the table through three
methods each, write one attribute each, and never call each other but for one packing helper
(`_filestat`, 16 lines, which reads nothing but `context`). The table and the bridge are the
state: every write of a counter, a number, a buffer's size or a record goes through them. The
memory readers are pure functions of a `_Memory` that happen to be methods.

**The long methods.** None. The longest are `_path_open` 78, `_open_writing` 56, `_list_answer`
52, `_zeroed` 48, `_path_rename` 43 and `_fd_readdir` 41 (EXECUTED); `LONG_FUNCTIONS`
(`test_rules.py:1021`) holds nine keys and none is in `mounts.py` (EXECUTED, read). The function
ceiling is not what this specification serves; it is what the split must not cross, and
`_path_open` has two lines of room (Decision 4).

**The import graph** (EXECUTED, `grep -n "mounts" src/wasi_python/*.py`). Into `mounts`:
`__init__.py:32` imports the eight public names; `_call.py` imports `STAGING_CEILING`,
`FileRecord`, `Mount` (line 31), `_Files` (38 under `TYPE_CHECKING`, 424 inside the call's
builder), `SIGNATURES` (898), `COUNTED`, `GUARDED`, `SIGNATURES` (921), `stat_trampoline_wat`
(940) and `trampoline_wat` (952); `_places.py:19` imports `METHODS`, `Mount`; `_sessions.py`
imports `STAGING_CEILING` (42) and `_Files` (49 under `TYPE_CHECKING`, 1042); `runner.py:39`
imports `Mount`; `tools.py` imports nothing of it. Three docstrings of `_call.py` name the
tables by module (`mounts.SHADOWED` 895, `mounts.GUARDED` 916, `mounts.COUNTED` 917) and read
`_fs_memory.` after the move; `mounts._CallContext` at 728 stays. Out of `mounts`: `_wasmtime_ffi` three times,
inside `bind` (767), `forward` (783) and `__call__` (820), and nothing else of the package
(107's rule, `test_mounts_imports_only_the_engine_seam`, green). The runner's whole surface of
the table is eleven names: the constructor, `walk`, `record`, `release`, `bind`, `new_turn`,
`open_now`, `__call__` (`_call.py:643`, `self.table(caller, name, *args)`), and the fields
`stop_fuel` (507), `context` (780) and `session` (`_sessions.py:1063`).

**The test seams on `mounts` names** (EXECUTED, `grep -rn` over `tests/`). Imports:
`tests/harness/files.py:654` and `:713` import `_Files`; `tests/unit/test_runner_mounts.py:20`
binds `mounts as mounts_module` and reaches twelve names through it (`_Files` 11 times,
`_errno_table` 4, `SHADOWED` 4, `_Memory` 3, `FORWARD_SAFE` 2, and `_Open`, `_HOST_ERRNO`,
`SIGNATURES`, `MAX_MOUNT_FILES`, `GUARDED`, `FileFault`, `COUNTED` once each), `:656` imports
`_Files` again, and `:1776` runs a child program that reads `mounts.Errno` and
`mounts._HOST_ERRNO`; `tests/checks/test_v1_2_hostile_guest.py:3002` and `:3207` import `Stat`,
a public name. Patches, all class attributes of `_Files`: `__call__` (`test_runner_mounts.py:501`),
`forward` (771, 821, 915) and `_source_type` (914). Reads of a hand-built table's fields:
`table.staged` 12, `table.table` 4, `table.opened` 2, and `total`, `owed`, `mounts`, `held`,
`free`, `forwards`, `calls` once each; one call of a bridge method, `table._list` (676). 108's
`SEAM_ALLOWED` (`test_rules.py:974`) holds eighteen names and none of `mounts.py` (EXECUTED,
read). The GC row at `test_runner_mounts.py:596` counts, with the collector disabled, every
`_Call`, `_Files` and `_Open` alive after a run and wants zero: a back reference from a helper
object to the table would turn it red (Decision 1 stands on this).

**Types** (EXECUTED): `mounts.py` carries 69 `Any` (`grep -c '\bAny\b'`), 2 `type: ignore` and 2
`cast`; `mypy --strict` over `src/wasi_python` is at 0 errors with `UNTYPED` empty
(`test_rules.py:112`).

**The checks that hold the filesystem's verdicts** (EXECUTED, `pytest --collect-only -q` per
file): `tests/checks/test_v1_2_hostile_guest.py` 154 rows (25 lines name a `Mount(` or
`mounts=`), `tests/unit/test_runner_mounts.py` 71 rows (31 lines; `_HOSTS`, `_ERRNO_NAMES`,
`NATIVE_RENAME_END`, `PAST_THE_LIMIT`, `SPIN_DIRTY`), `tests/unit/test_runner_grants.py` 29 rows,
`tests/unit/test_runner_sweep.py` 43 rows, `tests/checks/test_v1_4_embedding.py` 178 rows (29
lines; the parity tables `GRANT_PARITY`, `WRITE_PARITY`, `WRITE_DIFFERENCES`, `ERRNO_GUEST`,
`MOUNT_CANCEL`), `tests/checks/test_v1_4_sessions.py` (7 lines), and `tests/checks/test_rules.py`
58 rows, five of which are the structural checks this specification moves through (104's
ceiling, 107's import rule, 108's function ceiling and seam check, 106's type check).

## Decisions

### 1. Four seams, four new modules, free functions over one table

**The modules.** `mounts.py` splits into itself and four flat siblings, named for the WASI
seam each holds. The sizes are INFERRED from the measured sections and families above plus a
module header, the dispatch tables and the blank lines a move keeps; the builder records the
`wc -l` of each in the landing notes.

| module | holds | size after |
|---|---|---|
| `mounts.py` | the public types; the two private rows, `_Mounted` and `_Open` with `_Listing`; the `_CallContext` protocol; the errno-by-name table | about 380 |
| `_fs_memory.py` | the preview1 ABI as bytes: the WASI tables (`SIGNATURES` to `PRIVATE`), the numbers (errnos, flags, rights, limits, struct formats), the WAT builders, the ABI argument checks, `_Memory`, `_aligned`, `_Forwards`, the four readers `_path`, `_text`, `_iovecs`, `_result` as functions of a `_Memory`, and `_filestat` as a function of `(dev, ino, kind, size, mtime, links)` | about 340 |
| `_fs_descriptors.py` | the 19 `fd_*` handlers as free functions, with `_sync`, `_reads`, `_writes`, `_zeroed`, `_zero_pads`, `_grow`, and its `HANDLERS` table | about 450 |
| `_fs_paths.py` | the 10 `path_*` handlers as free functions, with `_resolve`, `_open_writing`, `_create`, `_refused`, `_read_paths`, `_texts`, `_namespace`, `_above`, `_across`, `_wasmtime_folder`, `_wasmtime_writable`, `_rename`, `_source_type`, `_plain`, and its `HANDLERS` table | about 560 |
| `_fs_table.py` | `_Files`: the preopens and the descriptor table, the numbers and their reuse, the cap, the lifecycle (`new_turn`, `walk`, `release`, `record`), the gate, the provider bridge (its 14 methods and the helpers only it uses: `_described`, `_dots`, `_kind`, `_number`, `_listed`, `_close`), `bind` and `forward`, the staging and the owed accounting the handlers wrote by hand today, and `__call__` | about 640 |

Every module is under 104's ceiling by a wide margin, so `ALLOWED` loses `mounts.py` and holds
`tools.py` alone until 110 lands (Decision 5).

**The shape: free functions over the table.** A handler is `def _fd_close(files: _Files,
caller: Any, fd: int) -> int`, its body today's with `self` renamed `files`; a path handler the
same. Each handler module ends with an upper-case table, `HANDLERS: dict[str, Callable[...,
int]]`, mapping the WASI name to its function (`"fd_close": _fd_close`). `_fs_table.py` binds
`HANDLERS = {**_fs_descriptors.HANDLERS, **_fs_paths.HANDLERS}` at module level and
`_Files.__call__` becomes `HANDLERS[name](self, caller, *args)` inside today's `try`, in place
of `getattr(self, "_" + name)`. The shared host function calls with the 29 names of
`SIGNATURES` and no other, so a missing key cannot be reached; a unit row holds the two tables
equal to `SIGNATURES` (Decision 5). An upper-case dict display that is only read is what 105's
mutable check admits (`scan.READ_ONLY_DISPLAYS`, `tests/harness/scan.py:2158`), so no allowance
moves.

**The table's interface for the handlers.** A handler reads the table's fields and changes the
table's state only through the table's methods. Today's methods keep their names (`_entry`,
`_take`, `_drop`, `_at_cap`, `_gate`, `forward`, `_stat`, `_read`, `_list`, `_change`, `_made`,
`_write_back`): a move is a move, so the reviewer reads `git diff --color-moved=dimmed-zebra` and
sees lines moved, not rewritten; the underscore marks "not the runner's", which is still true
(the runner's eleven names are listed under The problem). Five methods move into the table
from the families because they write its state: `_write_back` (from `fd_*`: the gate, then
`_made`), `_fits` and `_changed` (the staging bound and its accounting), `_follow` and `_unlink`
(this call's descriptors follow a removed or renamed file; `_unlink` re-stages a folder's
listing). Five small methods are new, each replacing a by-hand write a handler makes today
(EXECUTED, the per-method table of `build/111/measure.txt`): `_hold(number)` for
`self.held.add` in `_path_open`; `_unhold(number)` for `self.held.discard` in `_fd_close`;
`_renumbered(a, b)` for the held set's move in `_fd_renumber`; `_owe(number, entry)` for the
`del self.table[number]; self.owed[number] = entry` pair in `_fd_close`; `_relist(entry,
listing, held)` for the `staged` and entry update in `_fd_readdir`. Each is two to six lines;
together they are what "the table owns its state" means, and the rule is one the reviewer can
read in each handler module, in any of the five forms a write takes: no plain assignment
`files.<field> =`, no augmented one `files.<field> +=`, no subscript store
`files.<field>[…] =`, no mutator call `files.<field>.<mutator>(`, no `del files.<field>[…]`.
Today's ten by-hand writes take four of the five (EXECUTED, the pre-build review:
`held.discard` 1192, `del table[…]` 1211, `owed[…] =` 1212, `staged +=` 1329, 1497 and 1893,
`held.discard` and `held.add` 1573 to 1576, `held.add` 1602), and the rule is held by a rules
row, not a one-time grep (Decision 5, row 7; criterion 3 records the grep beside it). A handler reads six fields of the table and no other: `context`, `forwards`, `held`,
`mounts`, `opened` and `table` (EXECUTED, the pre-build review: the attributes read by the
methods that stay after the five moves); the builder records the per-module list beside that
grep.

**Why free functions and not two or three classes.** Three measured reasons. First, the GC row:
a `_Descriptors(files)` object holding the table back would make `_Files` wait for the cyclic
collector, and `test_runner_mounts.py:596` wants zero `_Files` alive with the collector disabled;
`release()`'s docstring promises "nothing waits for the cyclic collector", and a class with no
back reference is a free function with a longer name. Second, the handlers hold no state of
their own: the measured writes are one attribute per family, and both move into the table
above; a class whose only field is the table says less than a parameter named `files`. Third,
the dispatch is then a read-only table a reviewer can diff against `SIGNATURES`, not a
`getattr` on a name. The cost is one test seam, named under Decision 5: `_Files._source_type`
is patched as a class attribute at `test_runner_mounts.py:914`, and a module-level private name
of a runner module is what 108's seam check refuses and `SEAM_ALLOWED` never admits; the row
moves its injection into the `forward` patch it already makes on the next line (915), after the
guard's own stat answers 0 (`_source_type` forwards `path_filestat_get` with `stat=True` and
reads the filetype after, `mounts.py:2066` to `2069`), so the race the row injects, a folder
swapped for a link between the stat and the rename, is injected at the same point with the same
assertions.

**Why not mixins.** A mixin's methods read `self.held` of a class they are not; the reader of
`_fs_paths.py` cannot see what `self` is without the class that mixes it in, which is the memo's
R7 cost in a new shape, and `mypy --strict` types a mixin's `self` only through a protocol that
restates the table's fields. The owner rejected mixins on 2026-10-21; this is why.

**Why the provider bridge stays in the table module.** By the measurements it is a separable
concern: six fields of its own (`calls`, `total`, `faults`, `refused`, `refused_total`, the
`limit`), one method the table calls it through from `walk`, one method it calls of the table
(`_gate`). It stays because `_fs_table.py` is about 640 lines, under the ceiling by more than
half; because the bridge's counters are what `record()` and `new_turn()` reset, so a split would
move the lifecycle too; and because 18 + 15 + 11 + 6 test reads of `files.refused`,
`files.faults`, `files.calls` and `files.refused_total` would move with it for a reader's gain
only. It is the first candidate when the directory of Decision 3 comes.

### 2. What stays in `mounts.py`: the vocabulary

`mounts.py` keeps what every other filesystem module and the runner speak: the eight public
types with their docstrings (the package's API reference is generated from them,
`tests/harness/api.py`, `DEFINING` names `mounts.py`); `_Mounted` and `_Open` with `_Listing`;
the `_CallContext` protocol; and the errno-by-name table (`_errno_table`, `_HOST_ERRNO`,
`_RAISED`, `_ERRNO_SLOT`, `_raised`), which is the contract that a provider's `OSError` is read
by its errno's name. Its docstring keeps the two usage lines and the paragraph on providers,
and sends the reader to the four siblings for how a call is served. `__all__` is unchanged.
After the split it imports no sibling at all: `bind`, `forward` and `__call__`, which imported
the engine seam, are the table's. About 380 lines (INFERRED: 49 + 213 + 56 + 33 for the rows
and `_Listing` + 15 + 11, less the half of the docstring that describes the serving).

**Why the two rows live here and not in the table module.** The graph must be acyclic (the
memo's R3; 107's Decision 1 made `mounts.py` the bottom of it). The table imports the handler
modules for their `HANDLERS`; the path handlers construct `_Open` at four sites (`_path_open`,
`mounts.py:1644`, `1650`, `1654`; `_open_writing`, `1707`), so they need the row at runtime and
cannot import the table module at runtime. The row goes below both. `_fs_memory.py` would do, but
a descriptor's row is not the ABI; `_Mounted` is `Mount` as a call holds it and `_Open` is a
provider's file as the guest holds it, the private shapes of the public ones, and the public
ones are here. The alternative, a fifth module for two dataclasses, is a file for 33 lines.
The handler modules import `_fs_table` under `TYPE_CHECKING` only, for the `_Files` annotation.

**The import order, bottom up:** `mounts` (nothing of the package) ← `_fs_memory` (`mounts`) ←
`_fs_descriptors` and `_fs_paths` (`mounts`, `_fs_memory`; `_fs_table` under `TYPE_CHECKING`)
← `_fs_table` (`mounts`, `_fs_memory`, `_fs_descriptors`, `_fs_paths`, and `_wasmtime_ffi`
inside `bind`, `forward` and `__call__` as today). The runner's imports move with the names:
`_call.py` takes `_Files` from `_fs_table`, `SIGNATURES`, `COUNTED`, `GUARDED` and the two WAT
builders from `_fs_memory`, `STAGING_CEILING` from `_fs_memory`; `_sessions.py` the same two;
`_places.py` takes `METHODS` from `_fs_memory`; `Mount` and `FileRecord` stay from `mounts`.

### 3. Flat now; the directory is a follow-up with a named trigger

The four new modules are files beside `mounts.py`, prefixed `_fs_`, not a package
`wasi_python/_fs/`. The reason is what the judge sees. Five checks read the package flat, by
`src/wasi_python/*.py` or by a one-level module name, and a subdirectory would be invisible to
each (EXECUTED, read):

- 105's two checks, no lock and no mutable at module level outside the process owner:
  `_runner_modules_but_the_owner`, `package.glob("*.py")` (`test_rules.py:194`);
- 107's platform check, `_platform_hits`, `package.glob("*.py")` (`test_rules.py:872`);
- 108's seam check: `scan.RUNNER_MODULE = r"^wasi_python\.(runner|mounts|_\w+)$"` and
  `SEAM_BY_PATH` (`tests/harness/scan.py:1967`, `1971`): `wasi_python._fs.table` has a dot
  `_\w+` does not match, so a patch of a subpackage's private name would pass unseen;
- `tests/harness/api.py`'s lists, `RUNNER_FILES`, `INTERNAL_FILES`, `INTERNAL_MODULES`
  (`api.py:39` to `56`), by bare filename under the package: a file in a subfolder is not
  found, so its names could reach a public docstring or the README unseen;
- 104's `ALLOWED`, keyed by `p.name` (`test_rules.py:163`): two files of one name in two folders
  would collide, which its own stale-entry line would report.

Four read the tree whole and need nothing: 104's ceiling walk and 108's function ceiling
(`scan.files_under`, `rglob`), 107's citation check (the same), and 106's `mypy` target
(`files = ["src/wasi_python"]`, a directory, `pyproject.toml:92`). A directory now would mean
five judge changes in a specification whose point is four files, each change a chance to
loosen a check by accident.

**The trigger for the directory.** The follow-up is reserved for when the filesystem group,
which is `mounts.py`, the four `_fs_*` modules, `_places.py` (the grants and the preopen check),
`_private_dirs.py` and `_zip.py`, has an internal API of its own: a module that other runner
modules import by one name, not five. Its specification does the five judge changes above first
(each check learns `rglob` and a dotted module name), moves the files second, and names in its
claim list every check whose hash moves. Until then, a reviewer who asks "what is the
filesystem" lists `src/wasi_python/_fs_*.py` and `mounts.py` and has it.

### 4. The long methods: none; `_path_open` stays under 80 or is split

No method of `_Files` is over 80 lines (EXECUTED; the longest is `_path_open` at 78). Nothing is
re-keyed, and nothing could be: 108's allowance rule says `LONG_FUNCTIONS` is never added to. A
free function gains one parameter, `files`, and `_path_open`'s signature is already one parameter
per line, so it becomes 79. If the builder's move pushes it to 81 or more (a wrapped line, a
`files.` that no longer fits), the forwarded branch (`if entry is None:` to its `return`, seven
lines today: the cap, the forward, the new number held) becomes `_forwarded_open(files, caller,
args, out)` and `_path_open` is in the sixties. The other families' long methods have room:
`_open_writing` 56, `_list_answer` 52 (the table's), `_zeroed` 48.

### 5. The checks first, and the checks that hold the behaviour

Each new or changed check is seen failing on the commit before its code, by node id, the output
under `build/111/` and quoted in the landing notes (AGENTS.md, rule 3).

**The two allowances shrink** (108's rule: an entry leaves, none is added):

1. `ALLOWED` in `test_rules.py` loses `"mounts.py": 2206`. On the commit before the split the
   ceiling check is red with `mounts.py: 2,206 lines, over 1,500`; after it, green with every
   `_fs_*` module and `mounts.py` under the ceiling.
2. `MOUNTS_MAY_IMPORT` and `test_mounts_imports_only_the_engine_seam` (`test_rules.py:849`)
   become a table and one check for the group, `test_the_filesystem_imports_only_itself_and_the_engine_seam`:

   ```
   FILESYSTEM_IMPORTS = {  # module: (at runtime, under TYPE_CHECKING only)
       "mounts.py": ((), ()),
       "_fs_memory.py": (("mounts",), ()),
       "_fs_descriptors.py": (("mounts", "_fs_memory"), ("_fs_table",)),
       "_fs_paths.py": (("mounts", "_fs_memory"), ("_fs_table",)),
       "_fs_table.py": (("mounts", "_fs_memory", "_fs_descriptors", "_fs_paths", ENGINE_SEAM), ()),
   }
   ```

   `_sibling_imports` learns whether an import sits under `if TYPE_CHECKING:` (an `ast.If` whose
   test is the name `TYPE_CHECKING`) and reports `(line, module, typing_only)`; a runtime import
   outside the first tuple, or a typing import outside both, is a finding; a module the table
   names that is not one file under the package is a finding. The table reads as a chain with
   `mounts.py` at the bottom, so the graph is acyclic by inspection, and `mounts.py`'s own row is
   empty: it imported the engine seam for `forward`, which is the table's now. Seen failing on
   the commit before the split: `mounts.py:767: imports _wasmtime_ffi` and four modules not
   found. 107's rule is not loosened: the filesystem imports nothing of the runner but the engine
   seam, and the seam is reachable from one module of the five.

**Three new unit rows**, one per seam that can be driven without wasmtime, in
`tests/unit/test_runner_mounts.py` beside the hand-built table of line 656:

3. `test_the_memory_readers_answer_over_a_stand_in`: `_fs_memory._path`, `_text`, `_iovecs`
   and `_result` over a 64-byte stand-in with `fits`, `read` and `write` (no caller, no
   wasmtime): a path past the end is `EFAULT`, one longer than `MAX_PATH` is `ENAMETOOLONG`,
   bytes that are not UTF-8 are `EILSEQ`, an iovec count over `MAX_IOVECS` is `EINVAL`, an
   unaligned result pointer raises the ABI error, and a result that fits is 0 (today's answers,
   `mounts.py:1080` to `1150`, read). Red before: the module does not exist.
4. `test_the_table_reuses_numbers_lowest_first`: a `_Files` built with `FakeContext` and no
   handler: `_take` of three rows gives `PROVIDER_BASE`, `+1`, `+2`; `_drop` of the first two and
   `_take` again gives `PROVIDER_BASE` then `+1` (the heap); `open_now()` counts an owed row as
   closed; `_at_cap()` answers at the cap and not below it. Red before: the import path. This
   row drives the table through its five methods and no handler.
5. `test_every_shadowed_call_has_one_handler_function`: `set(_fs_descriptors.HANDLERS) |
   set(_fs_paths.HANDLERS) == set(SIGNATURES)`, the two disjoint, each `fd_*` key in the
   descriptors' table and each `path_*` key in the paths', each value a function (not a bound
   method) named `_` plus its key whose first parameter is `files`; and `_Files` has no attribute
   `_` plus any key, so no handler can be reached two ways. Red before: no `HANDLERS`.

**Two rules rows, for the lists and for the handlers' seam:**

6. `test_api_lists_every_module_of_the_package`: every `.py` under `src/wasi_python/` is in
   `api.DEFINING` or `api.INTERNAL_FILES`, and every name those lists hold is one file. Green
   today (18 files, 18 listed: EXECUTED, read); seen failing on the commit that adds the four
   modules before `INTERNAL_FILES` gains them, so a module whose private names could reach a
   public docstring unseen is a red line, not an oversight.
7. `test_the_handlers_change_the_table_only_through_its_methods`: an AST walk of
   `_fs_descriptors.py` and `_fs_paths.py` (its scanner in `tests/harness/scan.py`, beside
   `long_function_hits`) for the five forms of a write to the table: an `Assign`, `AnnAssign`
   or `AugAssign` whose target, or a `Delete` whose target, is an `Attribute` or `Subscript`
   chain rooted at the name `files`; and a `Call` whose function is `files.<field>.<name>` with
   `<name>` one of `add`, `discard`, `pop`, `clear`, `append`, `update`, `remove`, `extend`,
   `setdefault`. A hit is `file:line: files.<field> <form>`; a read of `files.<field>` is not a
   hit; the allowance is none and there is no list to grow. Seen failing on the handlers moved
   verbatim, before their ten by-hand writes become the table's methods: ten hits, the ones
   Decision 1 lists, the output kept under `build/111/`. Why a row and not criterion 3's grep
   alone: the grep is run once, at the build; the promise, that the table's invariants (`staged`
   is the sum of the rows' `held`, `opened` counts the table and the owed, `held` holds only
   wasmtime's numbers) are kept in one file, is for every later change.

**The seam that moves** (Decision 1): `test_runner_mounts.py:914`'s patch of `_source_type`
goes; its `recorded` forward (915) performs the swap when `stat` is true, `name` is
`path_filestat_get` and the forward answered 0. The assertions (the forwarded names, the link
left outside, the canary untouched) are not edited. 108's seam check stays green through the
move and `SEAM_ALLOWED` is not touched.

**The import paths that move**, and nothing else in them: `tests/harness/files.py:654` and
`:713` (`_Files` from `_fs_table`); `test_runner_mounts.py:20` (the twelve names: `_Files` from
`_fs_table`; `_Memory`, `SHADOWED`, `FORWARD_SAFE`, `SIGNATURES`, `MAX_MOUNT_FILES`, `GUARDED`,
`COUNTED` from `_fs_memory`; `_errno_table`, `_HOST_ERRNO`, `_Open`, `FileFault` stay from
`mounts`), `:606` (`_Open` stays, `_Files` moves) and `:656`; the program string at `:1776`
reads `mounts.Errno` and `mounts._HOST_ERRNO`, both of which stay, so it does not change. The
three `forward` patches and the `__call__` patch keep their shape: both stay methods of
`_Files`, and a patched `forward` still finds `self.forwards.page`.

**The checks that hold the behaviour, not edited:** the 154 rows of the hostile guest, the 71 of
the mounts unit file (its errno and limit tables), the 29 of the grants, the 43 of the sweep, the
178 of the embedding file (its five parity tables) and the sessions file's mount rows, every one
green before and after; the slow rows among them by node id in the worktree, and in the
dispatch.

### 6. No verdict moves

The judge is the one 107 used, with the same baseline:

- **The baseline set** is the `v0.1.0a7` release's, verified against its `SHA256SUMS`, frozen in
  the worktree. No artifact is built. No guest byte changes, so no fuel row moves and no bytes
  row moves.
- **The fast tier** (`uv run pytest -m "not slow" -n 3`, once, at the end of the build, in the
  worktree) gives `build/progress/latest.json`; `uv run python tests/harness/sameness.py --claims
  build/111/claims.toml A.json B.json` against the wave's tip record prints nothing outside the
  claim list: the seven rows above (three rules rows, three unit rows, one renamed rules row and
  its retired name) and the judge-hash lines of the five files the move touches (`test_rules.py`,
  `test_runner_mounts.py`, `tests/harness/files.py`, `tests/harness/api.py`, `tests/harness/scan.py`).
- **The parity and errno tables** are the judge of what the guest sees; none is edited
  (`GRANT_PARITY`, `WRITE_PARITY`, `WRITE_DIFFERENCES`, `ERRNO_GUEST`, `MOUNT_CANCEL`; `_HOSTS`,
  `_ERRNO_NAMES`, `NATIVE_RENAME_END`, `PAST_THE_LIMIT`, `SPIN_DIRTY`).
- **`tests/public_api.txt`** is byte for byte the same; `uv run python tests/harness/api.py`
  reports no difference. The eight public names keep their module and their docstrings.
- **`ruff check`, `ruff format --check` and `mypy --strict`** are clean; the `Any` count over
  the five filesystem modules together does not exceed today's 69 in `mounts.py`, and the
  `type: ignore` count stays at 2 (each recorded per module in the landing notes).

### 7. Kind: parallel-safe, runner code, reviewed before build

By 108's Decision 1 a specification is structural when its change adds one of five things.
This one adds none: no module-level mutable or lock (the two `HANDLERS` dicts and their union
are upper-case displays that are only read, which 105's check admits by name); no use of
wasmtime-py's private API (the engine seam's five names, `raw_func`, `PreparedCall`,
`context_of`, `get_fuel` and `set_fuel`, are called from `_fs_table.py` as from `mounts.py`
today, through `_wasmtime_ffi`); no platform branch; no test seam (one moves into an existing
one, Decision 5); no module past the ceiling and no function past 80 (two allowances shrink).
So its Kind is parallel-safe, and it changes `src/` and the judge only.

It is runner code, so AGENTS.md's rule 8 requires the pre-build review. The reviewer may write
108's "Structure" section anyway: the rows this specification moves are R3 (the graph gains four
nodes and stays acyclic), R6 (one patch of a private class attribute becomes none) and R7 (the
largest module after 110 is `_platform.py` at 1,407 lines, and the filesystem reads as five
files of one concern each); the other five rows do not move.

### 8. Where it lands, and with whom

After the chain's wave (103 to 109) and after 110, in the order the lane sets. 110 splits
`tools.py`; this splits `mounts.py`; the two share no source file. They share two lines of
`tests/checks/test_rules.py`: the `ALLOWED` dict, from which each removes its own entry (110
`tools.py`, 111 `mounts.py`; the dict is then empty and stays, since the check's stale-entry
rule needs it), and the end of the file, where each appends its checks. If 110 extends
`tests/harness/api.py`'s lists, both do. Each conflict is a trivial merge the rebase names. No
stacking: neither builds on the other's tip. One builder, one dispatch of the release workflow on
its tip, read back (every red line a growth line of another entry or none), the run id in the
landing notes. The CHANGELOG line and the roadmap line are in Design.

## Intent

After this specification a reader who asks "how does the guest's `fd_close` reach a provider"
opens `_fs_descriptors.py`, finds a function under thirty lines whose first parameter is the
table, and reads which three methods of the table it calls. One who asks "what state does a call's
filesystem hold" opens `_fs_table.py` and reads one class whose every attribute is written in
its own file. One who asks "what does the embedder see" opens `mounts.py`, which is the eight
public types and the two rows they become, and reads nothing of pointers or trampolines. The
graph between the five is a chain. The dispatch is a table equal to the WASI signatures. No
allowance in the judge names `mounts.py` any more, and the guest cannot tell.

## Design

### The commits, in order

Each commit is green on its own (AGENTS.md, rule 9); each check is seen failing on the commit
before its code, by node id, the output kept under `build/111/`.

1. **`111: the memory module (Decision 1)`**: `_fs_memory.py` with the tables, the numbers, the
   WAT builders, the ABI checks, `_Memory`, `_aligned`, `_Forwards`, the four readers and
   `_filestat` as functions; `mounts.py` imports them from there for one commit; the runner's and
   `_places.py`'s imports of the moved names follow; `test_the_memory_readers_answer_over_a_stand_in`.
2. **`111: the table (Decisions 1, 2)`**: `_fs_table.py` with `_Files` less the two families,
   plus the five moved and the five new methods; `_Mounted`, `_Open` and `_Listing` stay in
   `mounts.py`; `mounts.py`'s docstring trimmed to the vocabulary; the runner's two `_Files`
   imports and the harness's two follow; `test_the_table_reuses_numbers_lowest_first`;
   `test_api_lists_every_module_of_the_package` (seen failing on the commit's first state, before
   `api.INTERNAL_FILES` gains the modules).
3. **`111: the descriptor and path handlers (Decision 1)`**: `_fs_descriptors.py` and
   `_fs_paths.py` with their `HANDLERS`; `_Files.__call__` through the union; the `_source_type`
   seam moved into the `forward` patch; `test_every_shadowed_call_has_one_handler_function`;
   `test_the_handlers_change_the_table_only_through_its_methods`, seen failing on the handlers
   moved verbatim (ten hits), green once the ten writes are the table's methods.
4. **`111: the two allowances shrink (Decision 5)`**: `ALLOWED` loses `mounts.py`;
   `FILESYSTEM_IMPORTS` and the group's import check in place of 107's; both seen failing on
   commit 3's parent state as Decision 5 says.

Commits 1 to 3 may be squashed into two if the builder finds the intermediate import of moved
names from `mounts.py` more churn than clarity; the landing notes say which.

### `mounts.py` after

```
"""Mounts: a provider's files at a guest path, served from embedder code.
…the two usage lines and the paragraph on providers, unchanged…
How a call is served is the four modules beside this one: the bytes that cross the WASI
boundary (_fs_memory), the table a call holds (_fs_table), and the descriptor and path calls
over it (_fs_descriptors, _fs_paths)."""

class Errno(enum.IntEnum): …          # the eight public types, their docstrings unchanged
class Stat: …
class FileProvider(Protocol): …
class WritableFileProvider(FileProvider, Protocol): …
class Mount: …
class FileFault: …
class RefusedWrite: …
class FileRecord: …

_ERRNO_ALIASES, _errno_table, _HOST_ERRNO, _RAISED, _ERRNO_SLOT, _raised   # the errno-by-name table

_Listing = tuple[bytearray, "array[int]"]
class _Mounted: …                     # one mount as a call holds it
class _Open: …                        # a descriptor in the mount table

class _CallContext(Protocol): …       # the nine questions (107)

__all__ = [the eight public names]
```

### `_fs_table.py`: the table's interface

```
HANDLERS = {**_fs_descriptors.HANDLERS, **_fs_paths.HANDLERS}   # the 29 shadowed calls

class _Files:
    # today's fields, lifecycle, bridge, bind and forward, unchanged in body
    def __call__(self, caller, name, *args) -> int:
        try:
            return HANDLERS[name](self, caller, *args)
        except BaseException as e: …                             # today's ABI-error branch
    # moved in, because they write the table's state
    def _write_back(self, caller, entry, at) -> tuple[int, bool]: …
    def _fits(self, entry, size) -> bool: …
    def _changed(self, entry) -> None: …
    def _follow(self, mount, src, dst=None) -> None: …
    def _unlink(self, entry) -> None: …
    # new, each replacing a by-hand write in a handler
    def _hold(self, number) -> None: …          # a wasmtime number the guest opened
    def _unhold(self, number) -> None: …        # it closed it
    def _renumbered(self, a, b) -> None: …      # the held set follows fd_renumber
    def _owe(self, number, entry) -> None: …    # closed for the guest, write-back owed
    def _relist(self, entry, listing, held) -> None: …   # a folder listed again
```

### A handler module

```
"""The descriptor calls (fd_*) over a call's mount table. …the family's section comment of
today, in words…"""

def _fd_close(files: _Files, caller: Any, fd: int) -> int:
    entry = files._entry(fd)
    …today's body, `self` read as `files`, the by-hand writes as the table's methods…

HANDLERS: dict[str, Callable[..., int]] = {
    "fd_advise": _fd_advise,
    …one line per fd_* name of SIGNATURES, in SIGNATURES' order…
}
```

### The runner's imports after

| file | from `mounts` | from `_fs_memory` | from `_fs_table` |
|---|---|---|---|
| `__init__.py` | the eight public names | | |
| `_call.py` | `FileRecord`, `Mount` | `STAGING_CEILING`, `SIGNATURES`, `COUNTED`, `GUARDED`, `trampoline_wat`, `stat_trampoline_wat` | `_Files` |
| `_sessions.py` | | `STAGING_CEILING` | `_Files` |
| `_places.py` | `Mount` | `METHODS` | |
| `runner.py` | `Mount` | | |

### The CHANGELOG line

Under the one unreleased section:

> **The runner's filesystem reads along the WASI interface's seams** (spec 111; the design
> review's section 5 and R3, R7). `mounts.py` keeps the public types, their two private rows
> and the call-context protocol; the preview1 bytes (`_fs_memory.py`), the call's table and its
> provider bridge (`_fs_table.py`) and the descriptor and path calls (`_fs_descriptors.py`,
> `_fs_paths.py`, free functions over the table, dispatched by a table equal to the shadowed
> signatures) are one concern each, every module under the size ceiling and every function under
> 80 lines; the ceiling's allowance loses `mounts.py` and the filesystem's import rule holds all
> five modules in a chain. No public name, artifact byte or guest-visible errno changes.

### The roadmap line

> Reserved: 111 (the filesystem along the WASI seams: `_Files` split into `_fs_memory`,
> `_fs_table`, `_fs_descriptors` and `_fs_paths` as free functions over one table, `mounts.py`
> the vocabulary; flat, the `_fs/` directory a follow-up once the group has its own internal API
> and the five flat-reading checks learn a subfolder; parallel-safe; lands after the chain's wave
> and after 110; the owner, 2026-10-21).

## Scope

In: Decisions 1 to 8. Out:

- **A `wasi_python/_fs/` directory** and the five judge changes it needs (Decision 3).
- **The provider bridge as its own module** (Decision 1, last paragraph): the follow-up's first
  candidate.
- **A rename of the table's internal methods** (`_entry` to `entry` and the like): a move is a
  move; the rename, if wanted, goes with the directory.
- **`tools.py`'s split** (110) and any line of it.
- **Any change to what the guest sees**: no errno, no record field, no limit, no default; no
  change to the guard, the counted calls, the trampolines' WAT or the forward's fuel rule.
- **`_places.py`, `_private_dirs.py`, `_zip.py`**: in the filesystem group by subject, untouched
  here but for `_places.py`'s one import line.

## Acceptance criteria

1. **The modules exist and are the sizes recorded**: `wc -l` of `mounts.py`, `_fs_memory.py`,
   `_fs_table.py`, `_fs_descriptors.py` and `_fs_paths.py` in the landing notes, each under 1,500;
   `ALLOWED` names `tools.py` only (or is empty once 110 has landed).
2. **The split is a move**: `git diff --color-moved=dimmed-zebra` from the base to the built
   commit shows every method of `_Files` moved, and the landing notes list every line that is
   not a move with its reason (the `self` to `files` rename, the ten table methods of Decision 1,
   `HANDLERS`, `__call__`'s lookup, the module headers).
3. **The handlers change no table state by hand**:
   `test_the_handlers_change_the_table_only_through_its_methods` green, seen failing first with
   its ten hits (Decision 5, row 7); and beside it, recorded empty per handler module,
   `grep -nE 'files\.[a-z_]+(\[[^]]*\])? ?([-+*/|&^%]|<<|>>)?=[^=]|files\.[a-z_]+\.(add|discard|pop|clear|append|update|remove|extend|setdefault)\(|del files\.' src/wasi_python/_fs_descriptors.py src/wasi_python/_fs_paths.py`.
   The five forms are a plain assignment, an augmented one, a subscript store, a mutator call
   and a `del`; a `files.<field>` read is not a hit. The row and the grep agree on the forms;
   the row is the judge, the grep the record.
4. **The dispatch equals the signatures**: `test_every_shadowed_call_has_one_handler_function`
   green, seen failing first.
5. **The two allowances shrank and the import rule holds the group**: `ALLOWED` without
   `mounts.py`; `FILESYSTEM_IMPORTS` as Decision 5 writes it; both checks seen failing on the
   commit before their code, outputs under `build/111/`; `grep -nE 'from \.|import wasi_python'
   src/wasi_python/mounts.py` lists nothing.
6. **The three unit rows, the lists row and the handlers row** green, each seen failing first.
7. **No function is over 80 lines**: `test_no_function_is_over_eighty_lines` green with
   `LONG_FUNCTIONS` unchanged; `_path_open`'s length recorded.
8. **The test seams are accounted for**: the landing notes list every site of The problem's
   test-seam paragraph with what replaced it; `test_runner_mounts.py` changes only its import
   lines, the `_source_type` row's injection (lines 898 to 928 today) and the three new rows;
   `tests/harness/files.py` only its two import lines; the hostile-guest, grants, sweep,
   embedding and sessions files not at all; `SEAM_ALLOWED` not at all.
9. **No verdict moved**: `sameness.py --claims` between the built commit's fast-tier record and
   the wave's tip record prints nothing outside the claim list (Decision 6).
10. **`tests/public_api.txt` is unchanged**, byte for byte; `uv run python tests/harness/api.py`
    reports no difference.
11. **`ruff check`, `ruff format --check` and `mypy` are clean**; the `Any` and `type: ignore`
    counts per filesystem module recorded, their sums not over 69 and 2.
12. **The dispatch**: the release workflow on the built tip, every red line a growth line of
    another entry or none; the run id in the landing notes.

Twelve criteria.

## For the lane

- **Kind:** parallel-safe; lands alone or in a wave after the chain's and after 110, rebased
  onto the wave's tip in the lane's order, every conflict named (Decision 8 names the two
  expected: `ALLOWED` and the end of `test_rules.py`).
- **Files it shares with others:** `tests/checks/test_rules.py` (`ALLOWED`; the checks appended
  at the end), `tests/harness/api.py` (`INTERNAL_FILES`, if 110 extends it too), `CHANGELOG.md`,
  `context/roadmap.md`. Its source files, `src/wasi_python/mounts.py`, the four new modules,
  `_call.py`, `_sessions.py`, `_places.py` (import lines, and `_call.py`'s three docstring
  tokens, only), are shared with no specification
  in flight.
- **The claim list** (`build/111/claims.toml`, each line "111:"; the counts filled by the
  builder):
  - 111: **new checks**: `test_rules.py::test_the_filesystem_imports_only_itself_and_the_engine_seam`,
    `::test_api_lists_every_module_of_the_package`,
    `::test_the_handlers_change_the_table_only_through_its_methods`;
    `test_runner_mounts.py::test_the_memory_readers_answer_over_a_stand_in`,
    `::test_the_table_reuses_numbers_lowest_first`,
    `::test_every_shadowed_call_has_one_handler_function`.
  - 111: **retired checks:** `test_rules.py::test_mounts_imports_only_the_engine_seam` (its
    successor above). **Lost passes:** none. **Fuel rows:** none grow. **Bytes:** none.
  - **The judge hash changes** in `tests/checks/test_rules.py`, `tests/harness/scan.py`,
    `tests/harness/api.py`, `tests/harness/files.py` and `tests/unit/test_runner_mounts.py`.
- **The flags** (paste-safe; the lane folds them into its one acceptance):

  ```
  --accept "111: the runner's filesystem reads along the WASI seams: mounts.py keeps the public types, their two rows and the call-context protocol; _fs_memory.py the preview1 bytes and the forwards' tables; _fs_table.py the call's table, its lifecycle and the provider bridge; _fs_descriptors.py and _fs_paths.py the fd_* and path_* calls as free functions over the table, dispatched by a table equal to the shadowed signatures; every module under the ceiling, every function under 80 lines, no public name or guest-visible answer changed"
  --accept-judge "111: the ceiling's allowance loses mounts.py; 107's import rule becomes a per-module table over the five filesystem modules, runtime and typing imports apart; one rules row holds api.py's lists complete; one rules row holds the two handler modules to the table's methods for every form of a write; three unit rows drive the memory readers, the table's numbers and the dispatch table without the other seams; one mounts unit row injects its rename race through the forward patch it already made instead of a class attribute that is a function now; no existing expectation edited"
  ```

- **Dry-run needs:** one dispatch on the built tip (Decision 8). The Windows shard runs the
  mounts rows on `_Windows` as a matter of course; the builder reads the run's `rules` and
  `unit` groups on the three systems.

## Disposition of the pre-build review

The review (`../reviews/111-the-filesystem-along-the-wasi-seams-spec-2026-10-21.md`) re-measured
`_Files` with its own script, read every check the plan reads, probed 105's mutable scan with a
stand-in `HANDLERS`, and walked the moved race injection against the row and the code. Every
finding is written in.

- **Finding 1 (Medium), written in by the writer, this commit.** Criterion 3's grep missed an
  augmented assignment and a subscript store, three of today's ten by-hand writes. Decision 1
  now names the five forms with the ten sites; Decision 5 gains row 7, a rules row whose AST
  walk holds the two handler modules to the five forms with no allowance; criterion 3 cites the
  row as the judge and records the review's widened grep beside it; the claim list, the
  accept-judge flag, Design's commit 3, criterion 6 and the Kind line count the row.
- **Finding 2 (Low), written in by the reviewer (`668026c`), confirmed.** "Three new modules"
  read "four" at nine sites; the module table, the chain and the lines always counted four.
- **Finding 3 (Low), written in by the reviewer (`668026c`), confirmed.** `_call.py`'s three
  docstring tokens (`mounts.SHADOWED` 895, `mounts.GUARDED` 916, `mounts.COUNTED` 917) read
  `_fs_memory.` after the move; `mounts._CallContext` at 728 stays; For the lane names them.
- **Finding 4 (Low), written in by the reviewer (`668026c`), confirmed.** The handlers' read
  surface is six fields (`context`, `forwards`, `held`, `mounts`, `opened`, `table`), named in
  Decision 1 and recorded per module by the builder beside criterion 3's grep.
- **Note 1, acknowledged.** `_path_open` stays at 78 lines (`self,` has its own signature line
  and becomes `files: _Files,`); Decision 4's fallback stays as the rule for a crossing that does
  not come.
- **Note 2, acknowledged.** The moved injection fires on any `stat=True` `path_filestat_get`
  that answers 0, where today's fires only after a folder is judged; in the row the source is
  always the folder `d` and `_rename` forwards one stat per call, so the row reaches the same
  race. The builder may narrow the condition with `args[2] == STAT_PATH`; the specification does
  not require it.
- **Note 3, acknowledged.** The CHANGELOG and roadmap lines go in at the build, as the chain's
  did at its rebase commit.
- **Note 4, acknowledged.** The dict dispatch is cheaper than today's `getattr`; host time is not
  metered, so no verdict can move either way.
- **Note 5, accepted as the builder's option.** A small `_Table` protocol (the six fields and
  the table's methods the handlers call) in place of the `TYPE_CHECKING` import of `_fs_table`
  would make the seam a type the checker holds and drop the one upward import; it would live
  in `_fs_memory.py`, which is below the handlers and names `_Forwards` and, through `mounts`,
  `_Open` (not in `mounts.py`, which must not import `_fs_memory` for `_Forwards`). The builder may
  take it, and then `FILESYSTEM_IMPORTS`' typing column for the two handler modules is empty
  and the landing notes say so; the `TYPE_CHECKING` import stays the default, as the simpler
  move and the form 104 allowed.

## One line

`_Files` becomes four files along the WASI interface's own seams, the memory, the table, the
descriptor calls and the path calls, as free functions over one table dispatched by a table
equal to the signatures, `mounts.py` keeps the vocabulary, the ceiling's allowance loses its
entry, the import rule holds the five as a chain, and nothing the guest or the embedder sees
moves.

## Landing notes

Written by the builder.
