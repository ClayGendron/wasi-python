# 081 — guest fuel does not depend on where the repository is checked out

- **Status:** drafted 2026-10-19 on `spec/081-guest-fuel-does-not-depend-on-the-checkout` from
  main `8f8de73`; not built. It changes neither the guest's imports nor its exports, the artifact
  set nor the build recipe, so §5.6 asks no review before build; it is sent for one anyway, at
  the lane's request. A different agent reviews the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** a judge change; **parallel-safe**, not build-class (§5.7). It edits the judge's guest
  driver (`tests/harness/guest.py`), the `guest` fixture (`tests/checks/conftest.py`), one check
  (`tests/checks/test_v1_3_lxml.py`) and the driver's unit tests (`tests/unit/test_guest.py`),
  and nothing else: no `src/`, `scripts/`, `recipes/`, `downloads/SHA256SUMS`, workflow, README
  or CHANGELOG. No golden output, gap or allowance is edited. It restates the accepted fuel of
  two rows, and both fall: **the lane accepts it with `--accept-judge` alone** (Decision 3).
- **Depends on:** nothing unlanded.
- **Research it stands on:** spec 075's build review, N2
  (`../reviews/075-tools-small-fixes-build-2026-10-19.md`: the lxml snapshot row +113.8 k in a
  clone 88 characters longer than the main tree); and this spec's measurement (EXECUTED,
  `../research/2026-10-19-guest-fuel-and-the-checkout-path/`, the section below).

## The problem

A check's fuel is the number of wasm instructions its guest ran. The ratchet holds it to one
part in ten thousand of the accepted value (`FUEL_TOLERANCE`, `tests/harness/scoreboard.py`).
So fuel must depend only on the artifact and the check, never on the machine.

One check breaks that. `test_stylesheets_and_entities_reach_only_grants` (both binaries) gives
its guest a host path as an argument: `str(ro / "secret.txt")`, the real location of a granted
file. The check uses it to show that an entity naming a host path outside every grant reads
nothing. But that path lives under the checkout (`build/harness/guest-…/ro-…/`), so its length
is the checkout's length plus a constant. And the guest's work moves with that length.

The lane judges in the main tree (40 characters). The release's macOS legs check out at
`/Users/runner/work/wasi_python/wasi_python` (41 characters; GitHub's default workspace,
INFERRED from its runner layout, since `release.yml` passes no `path:` to `actions/checkout`)
and compare with `accepted.json`. A path-length-dependent metric there is a latent false
"grew". It has passed so far by luck.

## The measurement (EXECUTED)

Evidence: `../research/2026-10-19-guest-fuel-and-the-checkout-path/`. Against
`build/sets/s-c50ca51fae5eb55b` in the main tree, read only.

**Which rows record fuel.** `accepted.json` holds fuel for 159 rows (darwin-arm64), from 69
check functions (`funcs.txt`). Every fuel metric is recorded in one of three places (READ:
`grep 'metric("fuel"' tests/checks`): the `guest` fixture, and the upstream suite checks
twice. All three take their fuel from the judge's driver, `harness.guest.run`.

**Two checkouts, twice each.** All 69 functions run from this worktree (a 44-character path)
and from a clone at a 205-character path, twice each (`measure.sh`, `compare.py`,
`compare.out`, `runs.out`). 148 rows ran in each; 11 were skipped (the upstream suite groups:
their source trees exist only after a build).

| row | short to long | short to short, long to long |
|---|---|---|
| `test_stylesheets_and_entities_reach_only_grants[snapshot]` | **+113,522 and +113,529** (+0.053%) | +57, +64 |
| `test_stylesheets_and_entities_reach_only_grants[plain]` | **+50,981, both times** (+0.010%) | 0, 0 |
| the other 146 rows | at most 119 instructions, each a multiple of 17 | the same kind, as often |

So **the two lxml rows are the only path-dependent rows**, by an argument the guest is READ and
EXECUTED to receive. The long clone's run is red on its own: `GREW …[snapshot]: fuel 216000964
-> 216086430`. The other differences are run-to-run, not path: they appear as often between two
runs at one path (Decision 4).

**The upstream groups (READ).** Their argv is `["-u", "/upstream/judge/drive.py", package,
group]`, their environment `{"TMPDIR": "/tmp", "HOME": "/tmp"}`, their one grant `/upstream`
(`tests/harness/upstream.py`, `guest_argv`, `ENV`, `preopens`). No host path reaches them.

**The cause, alone (`argv_length.py`, `argv_length.out`).** The same program, the same grants,
the same driver; only the length of the path argument changes:

| argument length | snapshot fuel | step |
|---|---|---|
| 40 | 215,915,897 | |
| 41 | 215,916,301 | +404 |
| 44 | 215,918,722 | |
| 45 | 215,949,977 | **+31,255 for one character** |
| 80 | 216,004,139 | |
| 100 | 215,977,914 | lower than at 80 |
| 180 | 216,154,938 | +239,041 over 40 |

The same lengths in another letter give the same fuel, to the instruction. So the fuel is a
deterministic function of the length alone, and not a smooth one: about 700 instructions a
character, with jumps (INFERRED: an allocation or a collection crossing a threshold). The
tolerance on this row is 21,600 instructions. **One character more in a checkout's path can turn
the row red**; a different one can turn it green by chance. The plain row moves the same way
(40 to 205 characters: +195,252).

## Decisions

1. **The host path goes to a run of its own that records no fuel.** The check makes two runs:
   - first, a small program (`OUTSIDE`) given the real host path, with `record=False`: the
     entity naming it must still give `<r/>`;
   - then the measured program (`SAFETY`, less that one case), given guest paths only.
   The check asserts both, as one dict of answers, exactly as before.
   - **Why the real path stays.** The probe's point is the real host location of a file the
     guest can read through a grant. A made-up path would not show that wasmtime refuses it.
   - **Why not a fixed-length staging folder.** No folder has the same path on every system
     (`/tmp` is not Windows'), and a shared fixed folder breaks parallel workers. Padding the
     argument to a fixed length would work only up to a chosen maximum, and the content of a path
     a check builds still has to be checked by someone.
   - **The cost.** One more guest run per row, of a few lines after `import lxml`.
2. **The driver refuses a measured run that gives the guest a host path.**
   - `harness.guest.run` gains `measured: bool = True` and `host_roots: Sequence[Path] = ()`.
     A measured run whose inputs name a path under the checkout (`paths.REPO`) or under a
     `host_roots` entry raises `ValueError` before anything runs, naming each input. The inputs
     are what the guest sees: each argument, each environment variable, each file's guest path
     and contents (`files=`), and each grant's guest path.
   - Each root is looked for as written, resolved, and in forward slashes, so Windows' two forms
     and macOS' `/tmp` and `/private/tmp` are caught.
   - The `guest` fixture passes `measured=record` and, as a root, pytest's base temp folder
     (`tmp_path_factory.getbasetemp()`), where every `tmp_path` lives. The upstream checks keep
     the default: measured, with the checkout as root.
   - **Not checked:** a run on the caller's own engine (`own=`, which counts no fuel), and
     `Turns` (which records no fuel).
   - **Why a guard, not a self-test from two checkouts.** A two-checkout run needs a clone, its
     own environment and minutes of guest runs, and it covers only the sample it runs. The guard
     costs nothing, runs on every measured run in every judge run, and names the input. It is
     what this measurement found: a host path in a guest's inputs.
   - **What it does not catch.** A host path written by a check into a file in a grant, not
     through `files=`; or a host path outside the checkout and pytest's temp folder. The
     system's temp folder is not a root: on Linux it is `/tmp`, which the upstream groups pass as
     a guest path. Today the measurement shows no row moves by any such channel.
3. **The two rows' accepted fuel is restated, and both fall.** Measured with the prototype
   (`prototype.diff`, `fixed.out`) from both checkouts, twice each, one value every time:

   | row | accepted (main tree) | restated | change |
   |---|---|---|---|
   | `test_stylesheets_and_entities_reach_only_grants[plain]` | 507,157,737 | 506,200,859 | −956,878 (−0.189%) |
   | `test_stylesheets_and_entities_reach_only_grants[snapshot]` | 216,000,964 | 215,014,922 | −986,042 (−0.456%) |

   They fall because the measured program no longer runs the outside-grants entity. No row
   rises, so the lane needs no `--accept-growth`. The build re-measures them; if they differ
   from these, the landing notes say by how much and why.
4. **Out of scope: the 17-instruction steps.** Between two runs at one path, about fifteen of
   the 148 rows differ by a multiple of 17 instructions, at most 119 (`compare.out`; at most
   4.2 parts in ten million, 240 times below the tolerance). They are not the path's: they appear
   as often at one path as between two. The driver's docstring already says fuel repeats "to a
   few parts in ten million". A later specification may find their source; nothing here waits on
   it.

## Intent

Every fuel metric the judge records is the same whatever the checkout's path, so the release's
legs and the lane compare the same numbers; and a check that would hand a measured guest a host
path is refused at once, by name, before it runs.

## Design

- **`tests/harness/guest.py`.** A pure function, `host_paths_in(roots, argv, env, files,
  preopens) -> list[str]`, names each input that holds a root (`argv[3]`, `env DATA`, `file
  /a.py`, `the contents of /a.py`, `grant /ro`). `run()` calls it first when `measured` and not
  `own`, with `(paths.REPO, *host_roots)`, and raises `ValueError("a measured run gives the guest
  a host path in argv[3]: its fuel would depend on where the checkout is; give it guest paths,
  or record no fuel for this run (spec 081)")`.
- **`tests/checks/conftest.py`.** The `guest` fixture takes `tmp_path_factory` and passes
  `measured=record, host_roots=(tmp_path_factory.getbasetemp(),)`; its docstring says so.
- **`tests/checks/test_v1_3_lxml.py`.** `SAFETY` loses `host_secret` and the case
  `entity outside grants`. A new `OUTSIDE` program reads `sys.argv[1]`, parses the same entity
  document with `resolve_entities=True`, and prints `{"entity outside grants": [kind, value]}`.
  The check runs `OUTSIDE` with the host path and `record=False`, then `SAFETY` with no host
  path, and merges the two answers before the same thirteen `expect` lines.
- **`tests/unit/test_guest.py`.** Three rows: every input kind is found, in both forms of the
  root; guest paths and paths under another folder are not; a measured `run` with a host path
  in an argument or a grant is refused before it runs, and the same run with `measured=False`
  runs.

The prototype is `prototype.diff` in the evidence folder: 129 lines added, 10 removed.

## Scope

In: the driver's guard, the fixture's wiring, the lxml check's split, the three unit rows, and
the two restated values. Out: the 17-instruction steps (Decision 4); checks that call
`wasi_python.run` (they record no fuel); spec 082 (inline sessions and wasmtime's handlers).

## Acceptance criteria

1. **The checks fail first.** On main's code the three unit rows fail (`host_paths_in` and
   `measured` do not exist). With the guard alone, of the 148 fuel rows that run without a
   build, exactly the two lxml rows fail, each with the guard's message naming `argv[3]`
   (seen in the draft: `guard_only.out`).
2. **Two paths, one fuel.** Each of the two lxml rows, run twice from the worktree and twice
   from a clone at a path at least 150 characters longer (`lxml.sh`), gives one fuel value
   (seen in the draft: `fixed.out`).
3. **The probe still bites.** A mutant that grants the read-only folder at its own host path, in
   the `OUTSIDE` run only, fails the check on `entity outside grants` with `<r>SECRET\n</r>`
   (seen in the draft: `mutant_outside.out`). The other twelve answers are asserted as before.
4. **No other row depends on the path.** With the build, all 69 functions (`measure.sh`) from
   both checkouts: no row differs between the two paths by more than the largest difference
   between two runs at one path.
5. **The judge.** `ruff check` and `ruff format --check` green; the fast tier and one full run
   (`-n 3`) against `build/sets/s-c50ca51fae5eb55b`: no failure, no lost pass; the ratchet's
   only moves are the two restated rows (both fall) and `judge changed`. The prototype's fast
   tier (`fast_tier_prototype.out`): `474/550 pass · 1 gap · 24 blocked · 0 fail` (the blocked
   are source trees, a wheel, the wasmtime CLI and the like, absent from a worktree), unit suite
   1270/1278, `1744 passed, 32 skipped, 1 xfailed`, `lost 0 · grew 0`.

## Landing notes

Not built yet.

### For the lane

- `--accept-judge "spec 081: a measured guest run may not be given a host path (the driver
  refuses it), so fuel does not depend on where the checkout is; the lxml grant check's
  host-path probe runs on its own, unrecorded, and its two rows' fuel is restated (both fall)"`.
