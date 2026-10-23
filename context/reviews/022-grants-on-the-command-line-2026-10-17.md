# Review of 022 — Grants on the command line (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change. I did not write the specification's pre-build review or its confirmation either. I read `AGENTS.md`, the constitution (§3, §4, §4.9, §4.15), specification 022 with its landing notes, its pre-build review with the confirmation, spec 019's build review (for the format), and the diff. I also read `Grant`, `_host_path`, `_guest_path`, `_check_root`, `_check_grants`, `_walk`, `_walk_posix`, `_judge`, `_runtime_folders`, `_shared_folders` and `_cache_dir` in `src/wasi_python/runner.py`, and the release workflow's `verify` job. I did not rely on the landing notes. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** the scratch clone's `git diff c95399c 61d935f` (one commit, `61d935f`). It touches `src/wasi_python/cli.py`, `tests/unit/test_cli.py`, `tests/checks/test_v1_4_embedding.py` (one check), `README.md` (*From any language*), `CHANGELOG.md` and the specification.
- **Re-ran (EXECUTED, darwin-arm64, host CPython 3.14.2; also 3.11.14, 3.12.12 and 3.13.11 for the parser; the main tree's `build/artifacts` and `build/cwasm-cache`, read only).** Probes and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev022b/`: `pytest-full.txt`; `scripts/parse.py` → `out/parse-all.txt` (46 command lines on four Pythons, with a stand-in `run`; `pkg/` holds the built `cli.py` and the stand-in); `scripts/real.sh` → `out/real.txt` (real calls through the clone's installed `wasi-python`); `scripts/readme.sh` → `out/readme.txt` (the README's example as written); `scripts/mutate.py` and `scripts/runmut.sh` → `out/mutations.txt` (18 mutants of `cli.py` and `c95399c`'s command, one log each under `mut/`); `out/ruff.txt`; `out/help.txt`.
  - `uv run pytest -p no:cacheprovider` in the clone → `wasi_python v1: 172/183 pass · 0 gap · 11 blocked · 0 fail (unit suite 421/429, 8 skipped)`; v1.4 `70/70`; `593 passed, 19 skipped`; ratchet vs `98d0210b3c`: `lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 1 · grew 0 · judge changed: tests/checks/test_v1_4_embedding.py, tests/unit/test_cli.py`; **exit 0**. I did not pass `--accept`.
  - `uv run ruff check src tests` → all checks passed; `uv run ruff format --check src tests` → 52 files already formatted.
  - I did not commit or push. The clone's `git status` was empty before and after, at `61d935f`. I wrote nothing in the main tree.

## Decisions against the code

### Decision 1: `GUEST=HOST`, split at the first `=`

- **Built (READ).** `_grants` does `value.partition("=")`. No `=` is `parser.error("--grant needs GUEST=HOST")`, or `--grant-writable …`, named from the tag. Anything that splits becomes `Grant(host, guest, writable=mode == "rw")` and goes to `run()`.
- **Odd inputs (EXECUTED, `out/parse-all.txt` with a stand-in `run`; `out/real.txt` for real calls):**

  | command line (after `run`) | exit | what `run()` got, or the message |
  |---|---|---|
  | `--grant=` | 2 | `--grant needs GUEST=HOST` (an empty value has no `=`) |
  | `--grant ""` | 2 | the same |
  | `--grant ==` | 1 | guest `""`, host `"="`; real: `grants[0]: the guest path must be absolute; got ''` |
  | `--grant /d=` | 1 | real: `grants[0] at /d: host is empty` |
  | `--grant =./inputs` | 1 | real: `the guest path must be absolute; got ''` |
  | `--grant /a=b=c` | 1 | guest `/a`, host `b=c`; real: `'b=c' does not exist` |
  | `--grant "/my data=some dir"`, and `--grant=…` | 1 | guest `/my data`, host `some dir`, whole |
  | `--grant` (last) | 2 | `argument --grant: expected one argument` |
  | `--grant -- -c 1` | 2 | the same: `--grant` took `--`, as `--env` does |
  | `--grant / =./inputs` | 2 | `--grant needs GUEST=HOST`; `=./inputs` began the guest's argv |
  | `--grant /=./inputs` | 1 | real: `the guest path / is the root; pass root= instead` |
  | `--grant -d=x` | 2 | `expected one argument` (a value starting with `-`) |
  | `--grant /d=-x` | 1 | host `-x`, whole |

  Every row is the same on 3.11, 3.12, 3.13 and 3.14 (EXECUTED: `diff` of the four outputs is empty). So the line between 2 and 1 is where Decision 5 draws it: 2 only for no `=`, `--root` twice, `--root` with `--no-root`, and argparse's own errors; every value that splits is `run()`'s to judge.

### Decision 2: order across both options

- **Built (READ).** Both options use `dest="grants"`, `action="append"`, with a tagging `type`. `--grant` carries `default=[]`; `--grant-writable` has none. argparse sets a default only when the attribute is still missing, and `--grant` is registered first, so the list starts as `[]` (INFERRED from argparse; EXECUTED: `[]` gives `run()` no `grants`).
- **EXECUTED (`out/parse-all.txt`).** `--grant /a=ha --grant-writable /b=hb --grant /c=hc --grant-writable /d=hd` reaches `run()` as `/a ro, /b rw, /c ro, /d rw`. Writable first, then read-only, keeps that order too.
- **`run()`'s numbering matches what was typed (EXECUTED, `out/real.txt`).** `--grant /a=./inputs --grant-writable /b=./results --grant /a=./target` is exit 1, `grants[2] at /a: another grant has the same guest path`. The third option typed is `grants[2]`.

### Decision 3: read-only is the default form

- **No typo writes (EXECUTED).** `--grant-writabl`, `--grant-w`, `--grant_writable`, `--Grant-writable`, `--writable` and `--grants` each exit 2, `unrecognized arguments`. `--grant-writable` alone, `--grant-writable /d` and `--grant-writable=` each exit 2. No typed form gives a writable grant except the full option.
- **The same guest twice is refused, never merged (EXECUTED).** `--grant /d=./inputs --grant-writable /d=./results` and `--grant /a=./inputs --grant /a=./inputs` are each exit 1, `grants[1] at …: another grant has the same guest path`.

### Decision 4: `--root`

- **Twice, in every spelling (EXECUTED).** `--root a --root b`, `--root=a --root b`, `--root a --root=b`, `--root=a --root=a` and `--root= --root=` each exit 2, `argument --root: given twice`.
- **With `--no-root`, either order (EXECUTED).** `--root a --no-root`, `--root=a --no-root`, `--no-root --root a` and `--no-root --root=a` each exit 2, `argument … not allowed with argument …`. `--no-root --no-root` is accepted as `root=False`; harmless.
- **`--root ""` (EXECUTED).** `--root ""` and `--root=` reach `run()` as `root=""`; real call: exit 1, `{"error": "root is empty", "kind": "ValueError"}`.
- **`--no-root` with grants (EXECUTED).** `--no-root --grant /d=x --grant-writable /e=y` gives `root=False` and both grants in order. A real call reads `/in/in.txt`, and `os.path.exists('/tmp')` is `False`: there is no `/`.
- **A missing root is made (EXECUTED).** `--root ./made/deeper` made both folders; the guest wrote `/x.txt`, and the host folder holds `tmp`, `usr` and `x.txt` (`r`).
- **`--help` (EXECUTED, `out/help.txt`)** says `--root HOST  the guest's /, writable; made if missing`, as Decision 4 asks.
- **The `_Once` action (READ, EXECUTED).** It refuses when `hasattr(namespace, dest)`. With `default=argparse.SUPPRESS`, argparse never sets the attribute until the first `--root` (READ: `parse_known_args` skips a `SUPPRESS` default). `_main` calls `parser.parse_args(options)` with no namespace, so argparse makes a fresh `Namespace` each call, and `_parser()` itself is built per call (READ). The mutually exclusive group still sees `--root` as given, since its value is never the `SUPPRESS` object (INFERRED; EXECUTED by the rows above). Same on 3.11 to 3.14 (EXECUTED). Even `--root=--` is `root="--"` on all four.

### Decision 5: what is exit 2 and what is `run()`'s

- Matches (EXECUTED, the tables above). `_grants` runs inside `_main`'s `try … except SystemExit`, so its usage error returns 2 (READ; mutant M8 below moves it out and is caught).

### Decision 6: relative host paths

- EXECUTED: every real call above used `./inputs`, `./results` and `./made/deeper` from the probe's working directory, and the host saw the files there.

## Real calls through the installed script (EXECUTED, `out/real.txt`)

The clone's `.venv/bin/wasi-python`, from a working folder under the scratch directory:

| command (after `wasi-python run`) | exit | line |
|---|---|---|
| `--grant /in=./inputs --grant-writable /out=./results -- -c "…copy upper…"` | 0 | `exit_code 0`, `stdout "DATA\n"`; host `results/o.txt` is `DATA`; `inputs` unchanged |
| `--grant /in=./inputs -- -c "open('/in/new','w')"` | 0 | `exit_code 1`; stderr ends `PermissionError: [Errno 63] Operation not permitted: '/in/new'`; no file made |
| `--no-root --grant /in=./inputs -- -c "print(open('/in/in.txt').read())"` | 0 | `stdout "data\n"` |
| `--root ./made/deeper -- -c …` | 0 | made; `/` lists `tmp`, `usr`, `x.txt` |
| `--root ""` | 1 | `root is empty` |
| `--grant-writable /w=./link`, `--grant /w=./link`, `--root ./link` | 1 | `… passes through the link 'link' in a folder this user can write, …; name its target instead` |
| `--grant /t=$TMPDIR`, `--grant-writable /t=$TMPDIR`, `--grant /t=` its parent, `--root $TMPDIR` | 1 | `… holds the temporary folder, which holds every call's private folders and stdin; grant a folder apart from it` |
| `--grant /d=./inputs --grant-writable /d=./results` | 1 | `grants[1] at /d: another grant has the same guest path` |
| `--grant-writable /own=<clone>/src/wasi_python` | 1 | `grants[0] at /own is writable and is inside wasi_python's own code, …` |
| `--grant /own=<clone>/src/wasi_python` | 0 | read-only is allowed, and lists |
| `--root a --root b`; `--no-root --root a` | 2 | `given twice`; `not allowed with argument --no-root` |

Every refusal is exit 1 with `run()`'s own message as `error`. `python -m wasi_python run --grant /in=./inputs -- -c …` gives the same line as the script (EXECUTED).

## The checks

- **They count (READ).** Every assertion is on exit codes, argument lists, file contents and message text. No clock. §4.9 holds.
- **Seen failing first (EXECUTED, `mut/log-OLD_c95399c.txt`).** With `c95399c`'s `src/wasi_python` first on `PYTHONPATH`: 12 of the 38 cases fail, as the landing notes say. The `--grant-writabl` case passes there, because the option is unknown either way; mutant M9 shows it guards.
- **Mutants (EXECUTED, `out/mutations.txt`).** Each mutant is a copy of `src/wasi_python` first on `PYTHONPATH` (confirmed by printing `wasi_python.cli.__file__`), running `tests/unit/test_cli.py` and `test_the_command_grants_folders` (38 cases; the unmutated copy passes 38):

  | # | mutation | result |
  |---|---|---|
  | M1 | two separate lists, read-only then writable | caught: the order case |
  | M2 | `--root` last-wins (`action="store"`) | caught: `given twice` |
  | M3 | split at the last `=` | caught: the order case (`/c=h=c`) |
  | M4 | every grant writable | caught: unit and v1.4 |
  | M4b | no grant writable | caught: unit and v1.4 |
  | M5 | `if getattr(ns, "root", None)` (drops `--root ""`) | caught |
  | M6 | no mutually exclusive group | caught |
  | M7 | `--no-root` ignored | caught |
  | M8 | `_grants` outside the `try` | caught (2 cases) |
  | M9 | `allow_abbrev=True` (`--grant-writabl` becomes writable) | caught (2 cases) |
  | M10 | the message always says `--grant` | caught |
  | M11 | `--root` default `None` | caught (6 cases) |
  | M12 | `grants=[]` always passed | caught (2 cases) |
  | M13 | no `=` check: `/d` becomes host `""` | caught (2 cases) |
  | M14 | `--root` not in `VALUED` | caught (4 cases) |
  | M15 | `--grant` not in `VALUED` | caught (3 cases, v1.4 included) |
  | M16 | `--no-root` wins over `--root`, no group | caught |
  | M17 | an empty side (`/d=`, `=x`) is a usage error, exit 2 | **survives** (finding 2) |

- **`test_the_command_grants_folders` on Linux and Windows (READ, INFERRED).** It grants `tmp_path/in` and `tmp_path/out`. pytest puts `tmp_path` under `tempfile.gettempdir()` on every system, so both grants are inside the temporary folder, never at or above it. `_judge` refuses a grant only when the grant's own identity is in the temporary folder's chain (at or above), so a folder inside it passes (READ). The writable `out` is not at, inside or above any runtime folder either: the stdlib folder is a sibling under the temporary folder (or, on a process's first call, a placeholder with no identity, which only refuses "above"); the module cache is `~/.cache/wasi_python` on Linux and `%LOCALAPPDATA%\wasi_python\cache` on Windows, neither in `out`'s chain; the artifact set in `verify` is under `$RUNNER_TEMP`, not the temporary folder (READ, `_cache_dir`, `release.yml`). On Windows `f"/in={ro}"` is `/in=C:\…\in`, the first-`=` case. `[Errno 63]` is WASI's `EPERM`, raised by wasmtime's read-only preopen before the host is touched; `test_a_read_only_grant_refuses_raw_writes` already asserts 63 for `O_CREAT` and runs in `verify` on all three systems (READ). The third call grants `tempfile.gettempdir()` by name, refused by identity on any system. On macOS it passes (EXECUTED). The pre-build confirmation ran the fresh-process case (EXECUTED there). So it should hold on Linux and Windows; not run there.

## The docs

- **README *From any language* (READ, EXECUTED).** The paragraph is accurate: the two grant options and their modes, the first-`=` split with `C:\data` and `=` in a host path, `--root` writable and made if missing, `--no-root` as `root=False`, and the numbering from 0 across both options in the order typed (each EXECUTED above). **But its example fails as written** (finding 1).
- **CHANGELOG (READ).** One entry under 0.1.0a3, unreleased. Accurate.
- **The specification's text (READ).** The landing notes' numbers match my run (172/183, unit 421/429, 593 passed, lost 0, gained 1). "`--root` is a `_Once` action (no default …)": the default is `argparse.SUPPRESS`, which is what "no default" means here. The Design's `_grants(items)` takes the parser too. Both trivial.

## Acceptance criteria against evidence

1. *The checks exist and were seen failing first.* **Met for what was built** (EXECUTED: 12 cases fail on `c95399c`'s command). One case the Design names is missing (finding 2).
2. *`uv run pytest` is green with `--accept-judge`.* **Met as far as can be seen without accepting:** exit 0, lost 0, grew 0, the judge changed in the two named files (EXECUTED).
3. *A release dry run passes every job.* **Not run.** Nothing found that would stop it; the new check should hold on Linux and Windows (INFERRED, above).

## Findings, most severe first

1. **Low-medium. The README's example fails as written** (`README.md`, the block after "in the order typed").
   - The example is `wasi-python run --grant /data=./inputs --grant-writable /out=./results -- prog.py`. `prog.py` is a guest path. The default private root has no `prog.py`, so the guest cannot open it.
   - Failure (EXECUTED, `out/readme.txt`): from a folder holding `prog.py`, `inputs/` and `results/`, the line is `"exit_code": 2`, `"stderr": "/usr/local/bin/python.wasm: can't open file 'prog.py': [Errno 44] No such file or directory\n"`, and `results/` stays empty. A caller who copies the README's contract gets a failing program and may think the grants are at fault.
   - Fix: `wasi-python run --grant /data=./inputs --grant-writable /out=./results --stdin prog.py -- -`, the form the README's own caution recommends (EXECUTED: `exit_code 0`, `results/r.txt` written). Or use the spec's Intent, `-- -c "…"`.
2. **Low-medium. The Design's check that an empty side reaches `run()` is missing; a mutant survives** (`tests/unit/test_cli.py`).
   - The Design says the unit checks cover "`--grant /d=` and `--root ""` reach `run()` (whose refusal is exit 1)". Decision 5 names `--grant /d=` and `--grant =x` as `run()`'s, exit 1. The pre-build review's finding 4 asked for it. Only `--root ""` was built.
   - Failure (EXECUTED, `mut/log-M17_empty_side_is_usage.txt`): adding `if not guest or not host: parser.error(…)` to `_grants` makes `--grant /d=` exit 2, and all 38 cases still pass. That is the "checked twice, two exit codes" split the pre-build review closed.
   - Fix: one parametrized unit case with the fake `run`: `--grant /d=` reaches `run()` as `[Grant("", "/d")]` and `--grant =x` as `[Grant("x", "")]`, each exit 0 under the fake. M17 then fails.
3. **Low. The v1.4 temporary-folder refusal asserts only the kind** (`tests/checks/test_v1_4_embedding.py`, the last two lines of the new check).
   - `(code, line["kind"]) == (1, "ValueError")` passes for any `ValueError`: a walk failure, a refused guest path, a missing folder. The pre-build review's finding 6 asked for "the exact error text and `"kind": "ValueError"`"; the revised Design kept only the kind.
   - Failure (INFERRED): a later change that refused this grant for another reason, or stopped refusing it while some other check raised `ValueError`, would keep this check green.
   - Fix: also assert `"holds the temporary folder" in line["error"]`.
4. **Low, optional. Two rules are not in the README.**
   - `--root` given twice, or with `--no-root`, is a usage error (exit 2); and a guest path cannot hold `=` here, though `run()` takes one (Decision 1). A caller learns both only from the error or the specification.
   - Fix: one clause each in the paragraph, for example "… `--root` once, and not with `--no-root`" and "the guest path comes first and holds no `=`". Or answer in writing that the error messages suffice.

## Constitution checks

- **§3:** holds. Each option is one `run()` argument (`grants=`, `root=`). The first-`=` split narrows the guest names the command can write; it adds nothing (EXECUTED, READ).
- **§4.9:** holds. The checks assert codes, lists, bytes and text; no clock.
- **§4.10:** the landing notes' numbers match my run.
- **§4.13:** holds. Standard library only; `pyproject.toml` and `uv.lock` untouched (READ); ruff clean (EXECUTED).
- **§4.15:** holds. With no option, `run()` gets no `grants` and no `root` (EXECUTED; M12 shows the check guards it). A grant is read-only unless the full `--grant-writable` is typed (M4, M9). `--root` is writable by design and says so in `--help` and the README. Every runtime folder rule is still `run()`'s, unchanged (EXECUTED: the refusals table).
- **§5.2:** every choice is decided. The Design names one check that was not built (finding 2).
- **§7:** nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

All four findings are fixed, staged in the clone on `61d935f`.

1. **Fixed:** the README example reads the program from the host, `--stdin prog.py -- -`, and says why (the guest sees only its grants).
2. **Fixed:** `test_an_empty_side_reaches_run_which_refuses_it` (`/d=`, `=x`, `==`): each reaches `run()` with its empty side, so the M17 mutant (empty side as a usage error) fails it.
3. **Fixed:** the v1.4 check also asserts "holds the temporary folder".
4. **Fixed:** the README says `--root` twice, or with `--no-root`, is a usage error, and that a guest path given here cannot hold `=`.

EXECUTED: `tests/unit/test_cli.py` 40 passed; the v1.4 grant check passes; ruff clean.

## Verdict

**Does not land yet.** The command is right. Every Decision holds as built, on all four supported Pythons. Order is kept, `--root` refuses a second value in every spelling, no typo gives a writable folder, and every refusal is `run()`'s, exit 1. Seventeen of eighteen mutants are caught. Two small fixes first: the README's example fails as written (finding 1, one line), and the Design's empty-side case is missing, so a mutant survives (finding 2, one parametrized case). Findings 3 and 4 are one line each, or an answer in writing. A confirmation that runs the fixed README example and mutant M17 is enough.

One line: a correct, safe set of options; fix the README's example and add the empty-side check, then it lands.

## Confirmation

- **Date:** 2026-10-17
- **Reviewer:** the same fresh agent (Claude Opus 5.5); not the author.
- **Reviewed:** the fixes staged in the clone on `61d935f` (`git diff --cached`: `README.md`, `tests/checks/test_v1_4_embedding.py`, `tests/unit/test_cli.py`; `cli.py` is unchanged), and the Disposition above.
- **Ran (EXECUTED, darwin-arm64, Python 3.14.2).** Outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev022b/`: `confirm/readme.sh` → `out/confirm-readme.txt`; `out/confirm-mutations.txt` with `mut/confirm-log-*.txt`; `out/confirm-ruff.txt`; `confirm-pytest-full.txt`. I did not pass `--accept`, commit or push. The clone's staged state is as I found it. I wrote nothing in the main tree.

### Each disposition against its finding

1. **The README example: closed.** EXECUTED. `confirm/readme.sh` takes the line from the README's code block as it stands. It runs that line through the clone's installed `wasi-python`, from a folder holding `prog.py`, `inputs/a.txt` and an empty `results/`. The result is command exit 0, `"exit_code": 0`, and `stdout` `['r.txt']`. The host's `results/r.txt` holds `DATA`. Before the fix, the same setup gave `"exit_code": 2`.
2. **The empty-side check: closed.** EXECUTED. Mutant M17 makes an empty side a usage error. It now fails three cases, `test_an_empty_side_reaches_run_which_refuses_it[/d=]`, `[=x]` and `[==]`. The unmutated copy passes 41 of 41. The cases assert what `run()` receives. `run()` itself refusing each one with exit 1 was shown earlier (the review's real calls).
3. **The temporary-folder text: closed.** READ: the check also asserts `"holds the temporary folder" in line["error"]`. EXECUTED: it passes.
4. **The two rules in the README: closed.** READ: the paragraph now says that `--root` given twice, or with `--no-root`, is a usage error. It also says a guest path given here cannot hold `=`. Both match the behaviour I ran.

### The judge

- `uv run ruff check src tests`: clean. `ruff format --check`: 52 files already formatted.
- `uv run pytest -p no:cacheprovider` in the clone: **exit 1**. The run had 595 passed, 1 failed, 19 skipped. The scoreboard read 171/183, unit 424/432, v1.4 70/70, and the ratchet `lost 1 · gained 1 · grew 0`. **The one failure is not this change's.** It is `test_manifest_recipes_match_the_tree`, which reports "MANIFEST names recipes/patches/README.md, which the tree does not have" and that `scripts/steps/*.sh` changed since the build. The main tree's `build/artifacts` was rebuilt at 13:33:36, 22 seconds after my first judge run ended (13:33:14). The new set came from a tree with `recipes/patches/` and `apply_patches.sh`, which the clone (`c95399c`) does not have (EXECUTED: `stat`, `grep` of the `MANIFEST`, `ls`). The staged diff touches no recipe or build script. So the check compares this clone with another tree's artifacts. Every check this change touches passes on the new set.
- To accept, the coordinator must run the judge against an artifact set built from the tree being accepted. Rebuild the artifacts from `c95399c` plus this change, or rebase this change onto the tree that built the current set and re-run. Do not use `--accept` over the red line.

### New gap

- **A. Nit, wording (`README.md`).** "since the guest sees only its grants" is not exact. With the default private root, the guest also sees that root. What it never sees is the host's working folder. Suggested wording: "since the guest does not see the host's folders, only its root and its grants". This does not block landing.

### Verdict

**Lands.** Every finding is closed, and I ran the two re-runs I was asked for. The command needs no further change. The red judge line comes from a rebuilt artifact set from another tree, not from this diff. The landing must still be accepted against a matching artifact set, with `--accept-judge` for the two changed test files.

One line: the fixes hold. The README example runs, and M17 dies. Land it once the judge is green against artifacts built from the tree being landed.

## Disposition of the confirmation (filled in by the author)

- The wording nit is taken: "since the guest does not see the host's folders, only its root and its grants".
- The judge is run for acceptance on `main` with this change rebased onto it, against the set built from that tree.

Your verdict made the change land.
