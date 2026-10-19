# Review of 068 — A cap on files open at once (the build)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did the pre-build review and its
  confirmation. I wrote none of the code, the checks or the landing notes.
- **Reviewed:** `spec/068-a-cap-on-open-files`, `git diff 24bc10d..f63ce9f`: `ef0882f` (code,
  checks, README, CHANGELOG, API snapshot) and `f63ce9f` (landing notes), against the
  specification as confirmed at `24bc10d`. I read every changed line of `src/` and `tests/`, the
  README and CHANGELOG hunks, the landing notes, and the builder's `build/068/standins.py` and
  `standins.log` in the worktree.
- **Ran (EXECUTED, darwin-arm64, CPython 3.14.2, wasmtime-py 49.0.0, the frozen set
  `s-4eb5418a2b1bb553-c353b1d9`, read only).** Nothing was written in either git tree.
  - Two scratch clones of the branch at `f63ce9f`, each with its own `.venv`: `clone/` for the
    judge and probes, `mutants/` for mutants (restored after each; `git status` clean
    afterwards).
  - Outputs in `probes/` beside this file:
    - `fast_tier.txt`: `uv run pytest -m "not slow" -n 3`.
    - `full_judge.txt` and `full_judge_latest.json`: `uv run pytest -n 3`.
    - `m_mutants.py` → `m_mutants.txt`: seven mutants of mine, and four of the builder's re-run.
    - `b1_command_end_to_end.py` → `.txt`: the console script under soft limits of 256 and 1,024,
      and the library under 256 as a control.
    - `b2_accounting_built.py` → `.txt`: the pre-build review's `r1_accounting` probe, re-run on
      the built code.

## What holds

- **The code is the confirmed spec (READ).**
  - `open_now()` is `len(held) + opened − len(owed)`, and `_at_cap()` compares it with
    `open_files` by `>=`.
  - `_path_open` refuses a wasmtime number at the cap before the forward. After a forwarded 0 it
    reads the u32 at `out` and adds it to `held`.
  - A mount open is refused beside `MAX_MOUNT_FILES`'s check, before any provider call.
  - `_fd_close` discards the number only after a forwarded 0.
  - `_fd_renumber` keeps the `ENOTSUP` rule only `if self.mounts`. After a forwarded 0 with
    `a != b`, it discards `b`, then moves `a` to `b` if `a` was held.
  - `_instance` reads `c["open_files"]` strictly. `_check_places` reads an unset value from the
    call's one `limits`. `Defaults.open_files = 1024` is last and checked. The keyword is last
    on `run` and `run_async`, with the spec's `Args:` text. `_guard_linker` shadows
    `GUARDED + COUNTED`.
  - The module docstring, the `GUARDED` comment and the linker docstring were updated.
- **The count is exact on the built code (EXECUTED b2).** `r1_accounting`'s output is
  byte-identical to the prototype's run in the pre-build review. That covers renumber chains, a
  held number onto a preopen, stdin onto a held number, double closes, number reuse, `O_CREAT`
  and `O_TRUNC` at the cap (nothing created or truncated), a closed mount preopen whose number
  comes back, and wasmtime's open set at the end equal to the held set plus stderr and the
  preopen.
- **The command's raise works end to end (EXECUTED b1).** The console script is `main()` with no
  argument, which is the builder's departure.
  - Under `ulimit -Sn 256` and under 1,024, the guest opened exactly **1,024**, then errno 33.
  - With `--max-open-files none`, it opened all 5,000, so the raised limit has room.
  - Control: the library's `run()` in a process at 256 gave 244 opens, then `EIO`, and the soft
    limit was still 256 afterwards. The library leaves the process alone.
- **The departures are sound.**
  - Raising only when `main()` is called with no argument keeps the judge's own process and any
    embedder that calls `cli.main([...])` untouched. The console script and `python -m
    wasi_python` (`__main__.py`: `main()`) both get the raise (READ).
  - N1: one retry at `min(hard, 10240)`, only when that differs from the hard limit and exceeds
    the soft one.
  - N2: the 3,000-open bound on every system.
  - All three are checked: rows in criterion 6, stand-in (z), criterion 5's loop.
- **The judge is not weakened (READ).** Every removed line under `tests/` is one of Decision 8's
  two assertions or three docstrings:
  - `test_a_guard_call_leaves_the_other_calls_native`: its assertion and docstring;
  - `test_a_call_without_mounts_is_unchanged`: its assertion, now `<= set(GUARDED + COUNTED)`,
    and its docstring;
  - `Guarded`'s docstring.

  Everything else is additions. There are no edits to `tests/known_gaps.toml`, the upstream
  allowances or `context/progress/`. `tests/public_api.txt` gains exactly Decision 11's five
  lines.
- **The builder's stand-ins (READ `standins.log`; a sample re-run, EXECUTED).**
  - All 27 named stand-ins are caught by the check the spec names: (a) to (z), (t'), (u') and
    (p'), including (m) by 049's `test_set_defaults_changes_what_run_reads`.
  - I re-ran (t'), (u'), (h) and (i) on my clone: each caught, with the builder's failing lines.
- **My own mutants (EXECUTED `m_mutants.txt`).**
  - Caught:
    - M3, a renumber that drops `from` but never adds `to`;
    - M4, the command raising on every `main()` call;
    - M5, a retry even when `min(hard, 10240)` is the hard limit;
    - M6, the cap not applied to a mount open.
  - Not caught, three:
    - **M7**, a failed close that discards anyway: equivalent. wasmtime's `fd_close` fails only
      with `EBADF`, on a number it does not hold, so that number is never in `held` (READ,
      p1.rs).
    - **M1**, the count without `− len(owed)`: equivalent in practice. An owed buffer exists only
      after a gate refusal, and the call is then stopping, so no open can follow (READ,
      `_write_back`, `_gate`). Nothing could observe it; the spec chose the guest's view.
    - **M2**, a renumber left untracked in a *mount* table: not equivalent. See F1.
- **Fuel, cost, docs.**
  - The builder's re-runs give a fuel delta of 0 in all four rows, the same numbers as before.
  - Host CPU: 65.5 µs per pair on a busy machine, against my earlier 54.5.
  - Path depth: a peak of 311 at depth 300.
  - The README and CHANGELOG carry Decision 13's text. The CHANGELOG lines move to 0.1.0a7 at
    landing (the lane's note, not a finding).

## Findings, most severe first

1. **F1. No check renumbers in a table with mounts. Low; a row is suggested, not required.**
   (Criterion 2; EXECUTED M2; INFERRED below.)
   - The held set's update is shared code, and criterion 1 checks it on a guard table. But a
     build that skips it when `self.mounts` is set passes every check (M2: criteria 1 and 2
     green).
   - Its effect would be bounded. In a call with mounts, a renumber of wasmtime numbers would
     leave `held` stale. Mostly the count drifts high, which only refuses wrongly. It can drift
     low by at most the stdio and grant preopens a guest renumbers onto, a handful. No binary
     imports `fd_renumber` today.
   - **Suggested:** one row in criterion 2, `fd_renumber(g0, g1)` of two held grant numbers,
     after which one more open succeeds and the next is `EMFILE`; M2 as its stand-in. A follow-up
     commit or the next change to these units may carry it. It need not hold the landing.
2. **F2. `if resource is None` in `_raise_descriptor_limit` is unreachable. Note.** (READ,
   `cli.py`.) `import resource` with `sys.modules["resource"] = None` raises `ImportError`,
   which the line above catches. Harmless; delete it at leisure.

## Constitution checks

- §4.15: a default for the new limit; nothing loosened.
- §4.3: no host-dependent default. The command's `setrlimit` happens only in the command's own
  process, and is skipped without `resource`.
- §4.4: the guest's imports and exports are unchanged; the shadows define calls the guest
  already imports.
- §4.9: every new check counts opens, forwards, provider calls, `setrlimit` calls or errnos;
  none times anything.
- §4.10: the landing notes label and log their claims (`build/068/`).
- 049, Decisions 10 and 13: the public docstrings carry no spec number or internal name; the
  snapshot diff is the five lines; the README reference is regenerated.
- AGENTS.md rule 4: the judge change is exactly the stated one. The `--accept-judge` reason
  names it truthfully.

## Scoreboard

Both tiers ran on a fresh clone at `f63ce9f`, against the frozen set, without `--accept`
(EXECUTED).

- **Fast tier**, `uv run pytest -m "not slow" -n 3` (`probes/fast_tier.txt`): 1,581 passed and
  27 skipped. `wasi_python v1: 353/418 pass · 0 gap · 19 blocked · 0 fail` (unit suite
  1228/1236; v1.2 66/67; v1.4 163/163). Ratchet: lost 0, gained 2, grew 0.
- **Full judge**, `uv run pytest -n 3` (`probes/full_judge.txt`; the record copied to
  `probes/full_judge_latest.json`): 1,593 passed, 59 skipped, 2 xfailed, in 3 min 9 s.
  `wasi_python v1: 365/418 pass · 2 gap · 51 blocked · 0 fail` (unit suite 1228/1236; v1.4
  163/163). Ratchet vs `2ce08a592d`: lost 0, absent 0, unrun 0, gained 2, grew 0. The judge
  changed in the seven files the landing notes list.
- Both match the builder's records line for line (`fast-built.log`,
  `latest-full-ef0882f.json`).
- The 51 blocked are the source trees and artifacts a worktree lacks, as on main's runs.

The proposed `--accept-judge` reason is accurate.

## Verdict

**It lands.** The code is the confirmed specification, line for line where it matters: the
count, the renumber rule, the strict `c["open_files"]` and the command's raise. The count
matches wasmtime's own table exactly. The command's default cap now holds under macOS's 256 and
Linux's 1,024. The judge change is exactly Decision 8's, and every stand-in is caught. Both
tiers are green with nothing lost or grown.

F1 is an optional extra row; F2 is a dead line.

## One line

Built as specified, counted exactly, judged green twice; it lands, and a renumber row for mount tables would be a nice extra.

## Confirmation of the post-review delta (addendum)

- **Reviewed:** `624cc62` on `spec/068-a-cap-on-open-files`, with the rebase onto main
  `a0de463`. Nothing was written in either git tree. Checks ran in the scratch clone `mutants/`,
  checked out at `624cc62`, against the frozen set.
- **The rebase is clean (EXECUTED, READ).**
  - `git range-diff 24bc10d..f63ce9f a0de463..077b1cb`: `ef0882f = c91db62` and
    `f63ce9f = 077b1cb`.
  - `git range-diff ef1441b..24bc10d a0de463..1042edf`: both spec commits are `=`.
  - Main gained only the 0.1.0a6 release and the bump to 0.1.0a7 (`CHANGELOG.md`, `__init__.py`).
  - So the reviewed build is carried over unchanged.
- **The delta (READ, `git diff 077b1cb..624cc62`).** Four files:
  - `CHANGELOG.md`: the two lines moved, word for word, from the released 0.1.0a6 section into
    "0.1.0a7 — unreleased", replacing its placeholder.
  - `cli.py`: the unreachable `if resource is None` deleted (F2).
  - `test_runner_mounts.py`: criterion 2's new F1 row. In a table with mounts, two held grant
    numbers are renumbered; then one open answers 0 and the next `EMFILE`. The docstring grew one
    clause.
  - The specification: criterion 2's row, stand-in (f2), and the landing notes' "After the build
    review".
  - No other judge line changed.
- **Checks by node id (EXECUTED, `probes/delta_checks.txt`).**
  - Criteria 1, 2 and 6's three units, plus `tests/checks/test_v1_4_public_api.py`: 15 passed.
  - `ruff check`, `ruff format --check` and `tests/harness/api.py --check` are clean.
- **Stand-in (f2) (EXECUTED, `probes/delta_f2.txt`).** I applied my M2, the held-set update
  skipped when the table has mounts. Criterion 2 then fails with `assert 33 == 0`, the builder's
  line. The file was restored and the clone is clean. F1 is closed.
- F2 is closed. Criterion 6's row with `sys.modules["resource"] = None` still passes, inside the
  15 above.

**Confirmed, it lands.**
