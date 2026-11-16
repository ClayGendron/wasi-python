# 194: the pydantic suites in the guest

- **Status:** drafted and built 2026-11-16 on `spec/194-the-pydantic-suites-in-the-guest`, stacked on 190's pull request. Every group's fuel is provisional, an upper estimate: no set with pydantic-core linked in could be built where this was written, so the first run of a set built with these groups measures them (the landing notes say which numbers it replaces). Not yet reviewed.
- **The owner's choice:** "pydantic's four test suites judged in the guest, so Rust panics stay catchable (`panic=unwind`) and the abort switch is never thrown" (the orchestrating session's brief, 2026-11-16). The questions this build leaves for the owner are in The owner's choices below; none is decided here.
- **Date:** 2026-11-16
- **Owner:** Clay Gendron
- **Kind:** **a judge change**: four new families (`tests/upstream/pydantic-core.toml`, `pydantic.toml`, `annotated-types.toml`, `typing-inspection.toml` and their `.ini`), their expected classes and gaps, `packages.toml`, `PURE_SUITES`, three test-source patterns in `tests/harness/pins.py`, seven test-only wheels in `kit-extra.txt`, the shards, the budget caps and `SMOKE_TOTAL_BOUND`. It also pins three test sources in `downloads/SHA256SUMS` and `scripts/00_download.sh`, which `MANIFEST` carries (every pin is a line of it), so the artifact's `MANIFEST` bytes change, though no binary, zip or wheel does. Nothing under `src/` changes.
- **Depends on:** 190 (pydantic-core, pydantic, annotated-types and typing-inspection in the set, on `panic=unwind`; its Decisions 1, 8 and 9 and its landing notes), 191 (rich, markdown-it-py, mdurl and pytz in the zip, which the test-only wheels import), 066 and 067 (the package driver and the test-source families), 104 (the tiers). Siblings that edit the same files: 192 (orjson's suite) and 193 (191's nine suites): whichever lands later recomputes `SMOKE_TOTAL_BOUND` from the head's smoke groups and repacks `upstream-pure-smoke-b`.
- **Research it stands on:** PyPI's JSON API for the four packages and the seven test-only wheels, read 2026-11-16 (version, files, SHA-256, `requires_dist`, `requires_python`); the four sdists and seven wheels downloaded from files.pythonhosted.org and matched to PyPI's SHA-256 (EXECUTED, `sha256sum -c`; no fetch was refused); the four suites read and run natively on CPython 3.15.2, the line's own build, with the pinned wheels, with and without stand-ins for the guest's missing processes and threads (EXECUTED, the landing notes); `docs/reference/limitations.md` for the guest's facts.

Labels: EXECUTED, run and seen; READ, read from a file or a page, cited; INFERRED, reasoned.

## The problem

1. 190 links pydantic-core into `python.wasm` with Rust panics that unwind, and ships pydantic, annotated-types and typing-inspection in the zip. The owner's gate ("0.1.5's scope") lets unwinding ship only if a CI run judges both pydantic suites in the sandbox; otherwise 0.1.5 ships `panic=abort` by 190's Decision 8 switch. 190 moved the suites here (190's landing notes), because each smoke group needs its fuel measured on a built set and each expected class reasoned.
2. The four packages name their suites `later`, closing with 194 (`tests/upstream/packages.toml`, READ).
3. pydantic's every test runs an autouse fixture that checks each JSON Schema it builds with jsonschema, on every platform but emscripten (`tests/conftest.py:175-197`, READ). The guest's `sys.platform` is `wasi`, so without jsonschema every test errors at setup (EXECUTED natively: 10,887 errors, `ModuleNotFoundError: No module named 'jsonschema'`). The set does not carry jsonschema; 0.1.5's own jsonschema needs referencing and rpds-py, which is compiled Rust.

## Decisions

### 1. The test sources and their pins

Each suite comes from its package's sdist, which carries `tests/` (READ). pydantic-core's sdist is already pinned as the source step 52 builds, and `tests/harness/pins.py` already names it as its suite's test source. The other three are pinned here, by the SHA-256 of 190's Decision 1, which the downloads matched (EXECUTED):

| test source | file | SHA-256 | from |
|---|---|---|---|
| pydantic-core 2.50.4 | `pydantic_core-2.50.4.tar.gz` | `aead3b74b68396bf0feab5d57e050b730ded7df55853c1e048a87e00aaf033c6` | already pinned (`get`, step 52's source) |
| pydantic 2.14.3 | `pydantic-2.14.3.tar.gz` | `1054f237f4d4733e5a30e1e2333bd33a2004ab9ab1510bd053a9a31bb48e232d` | files.pythonhosted.org, a new `tests` line |
| annotated-types 0.8.0 | `annotated_types-0.8.0.tar.gz` | `13b2beaad985e05e2d6407ee4c4f35590b11f8d693a258a561055cac8f64cab7` | files.pythonhosted.org, a new `tests` line |
| typing-inspection 0.4.5 | `typing_inspection-0.4.5.tar.gz` | `7f16c411e7930dc79596d42ab44672a3fe5f60eb34b781a1647e7872363120c7` | files.pythonhosted.org, a new `tests` line |

`tests/harness/pins.py` gains `pydantic`, `annotated-types` and `typing-inspection` patterns. The three pure families name their wheels (`pydantic-2.14.3-py3-none-any.whl`, `annotated_types-0.8.0-py3-none-any.whl`, `typing_inspection-0.4.5-py3-none-any.whl`, already in `SHA256SUMS`), so the tie holds every file of each wheel equal to the test source's. pydantic-core names no wheel: it is compiled from the same sdist, as markupsafe's family is.

### 2. The test-only wheels

Each is pure, from files.pythonhosted.org, matched to PyPI's SHA-256 (EXECUTED), and joins `tests/upstream/kit-extra.txt`. Each family unpacks only the ones it names.

| wheel | SHA-256 | licence (READ) | for |
|---|---|---|---|
| `dirty_equals-0.11-py3-none-any.whl` | `b1d7093273fc2f9be12f443a8ead954ef6daaf6746fd42ef3a5616433ee85286` | MIT | both |
| `inline_snapshot-0.36.2-py3-none-any.whl` | `2c7980bee5149ecfffae3fea2e6670e56d0cd94fa975e7bd8517c4c984ce6e5c` | MIT | pydantic-core |
| `asttokens-3.0.2-py3-none-any.whl` | `9da13157f5b28becde0bd374fc677dcd3c290614264eff096f167c469cd9f933` | Apache-2.0 | inline-snapshot's |
| `executing-2.3.0-py3-none-any.whl` | `736e859c9f8701f11fcf516856f26f562e04776387824b43a35a1dfe21c84122` | MIT | inline-snapshot's |
| `pytest_mock-3.17.0-py3-none-any.whl` | `1b82aa4b37137248bd687055e109723debeb07b489de1565297dc9589c5f2d6b` | MIT | both |
| `jsonschema-4.17.3-py3-none-any.whl` | `a870ad254da1a8ca84b6a2905cac29d265f805acc57af304784962a2aa6508f6` | MIT | pydantic |
| `pyrsistent-0.20.0-py3-none-any.whl` | `c55acc4733aad6560a7f5f818466631f07efc001fd023f34a6c203f8b6df0f0b` | MIT | jsonschema's |

- **hypothesis stays the kit's 6.152.1.** Every hypothesis release since 6.156.1 is compiled, with no pure wheel (READ, PyPI), and pydantic-core's tests run on 6.152.1 natively (EXECUTED). The roadmap's line lists hypothesis among the wheels to add; the kit already carries it.
- **rich, markdown-it-py, mdurl and pytz** are in the zip since 191 (READ, `recipes/snapshot-packages.txt`), so no family names them; inline-snapshot imports rich from the zip, and pydantic's tests take pytz from it.
- **jsonschema 4.17.3** is the last release whose dependencies are pure (attrs, which the zip carries, and pyrsistent); 4.18 and later need referencing and rpds-py (READ, PyPI). pydantic's conftest only validates the schemas its tests build (`Draft202012Validator.check_schema`), and 4.17.3 knows draft 2020-12. Natively the suite runs on it with warnings as errors (EXECUTED). This is a choice for the owner (choice 1).
- inline-snapshot and pytest-mock register pytest plugins by entry point; the kit's `.dist-info` folders carry them, as pytest-asyncio's does for joblib's family.

### 3. The four families

Each is driver `package`, a test-source family, `stage_folders = ["tests"]`, `extra_sys_path = ["."]` (its tests import `.conftest` and `..conftest`), and its `.ini` is its pyproject's pytest settings transcribed, with the rewrite warning ignored as every family's is.

- **pydantic-core** (`cwd = "/tmp/work"`): `pydantic-core-smoke`, 29 files, about a fifth of the suite's native time (2.13 s of 10.43 s, EXECUTED); `pydantic-core-r`, `tests` less the smoke paths, in the release tier. Its upstream `timeout = 30` and benchmark `addopts` are pytest-timeout's and pytest-benchmark's, plugins the kit lacks, so the `.ini` leaves them out and declares the two markers its tests use (pytest-timeout's, pytest-run-parallel's).
- **pydantic** (`cwd = "tree"`: `tests/types/test_path.py` reads paths such as `tests/test_types.py` relative to the source's root, and natively eight tests fail from any other folder, EXECUTED): `pydantic-smoke`, 25 files, about a fifth of the native time (2.95 s of 15.94 s, EXECUTED); `pydantic-r`, the rest.
- **annotated-types** and **typing-inspection**: the whole suite is the smoke group, as six's, markupsafe's and typing-extensions' are, since natively each takes 0.29 s and 0.20 s (EXECUTED) and a session's start is most of either. Neither has a release group, so neither has a release shard; the roadmap's line asked for a split of each. This is a deviation, written for the owner (choice 3).

The smoke files of the two large suites were chosen by native time, as a proxy for fuel, from the core of each package: validators and serializers of scalars, dates, containers, unions, models and typed dicts for pydantic-core; models, fields, validators, serialization, type adapters and the standard types for pydantic. Every file with a no-processes member is in the release tier, and so are the files whose stack depth a run must first decide (`serializers/test_functions.py`, `test_hypothesis.py`, `test_garbage_collection.py`, `test_schema_gather.py`, `test_forward_ref.py`, `test_generics.py`; the landing notes). The smoke group keeps `test_main.py`, with the one no-threads test as its normal-tier class, and `test_edge_cases.py`, whose recursive models the recursion guard bounds.

### 4. What is left out (190's Decision 9)

Each `not_selected` names its reason and closes with the limitations page:

- pydantic-core: `tests/benchmarks` (pytest-benchmark's timings) and `tests/test_docstrings.py` (pytest-examples, which runs ruff in another process).
- pydantic: `tests/benchmarks`, `tests/mypy` (mypy, which the set lacks), `tests/plugin` (a plugin installed as a distribution; it skips itself without `TEST_PLUGIN`), `tests/test_docs.py` (pytest-examples and time-machine, and examples run in another process), and `tests/test_exports.py::test_public_internal`, which globs the package's source files beside its tests; the stage does not hold them, since the package comes from the zip, so it would pass having checked nothing.

### 5. Fuel: provisional, an upper estimate each

No set with pydantic-core linked in could be built here (python.org and rustup were refused, and the container has 4.6 G of disk), and the only built set at hand predates pydantic-core. So no group's fuel is measured. Each `measured` is one and a half times an estimate from the native pytest session of its own files: 10 G for a session's start plus 10.4 G per second of the session as pytest reports it, fitted from three measured groups run natively on the same CPython the same way (six-smoke, 13.5 G for 0.52 s; typing-extensions-smoke, 18.8 G for 1.27 s; packaging-r-version, 360.1 G for 33.7 s; EXECUTED). Each `fuel` is the rule's cap of that figure, so a group may use up to about 2.25 times its estimate before it runs out.

| group | tier | native session | estimate | `measured` (provisional) | `fuel` |
|---|---|---|---|---|---|
| pydantic-core-smoke | normal | 3.13 s (EXECUTED) | 42.6 G | 64 G | 96 G |
| pydantic-core-r | release | 11.93 s (INFERRED: its files' 8.30 s and the whole session's 3.63 s of collection) | 134.1 G | 210 G | 320 G |
| pydantic-smoke | normal | 4.69 s (EXECUTED) | 58.8 G | 89 G | 140 G |
| pydantic-r | release | 17.89 s (INFERRED: its files' 12.98 s and 4.91 s of collection) | 196.1 G | 300 G | 450 G |
| annotated-types-smoke | normal | 0.35 s (EXECUTED) | 13.6 G | 21 G | 32 G |
| typing-inspection-smoke | normal | 0.22 s (EXECUTED) | 12.3 G | 19 G | 29 G |

Each family's `budget` is the sum of its caps (416 G, 590 G, 32 G, 29 G). Each family's cap in `tests/lint/budget.toml` is twice its smoke group's cap (192 G, 280 G, 64 G, 58 G), so the first run cannot exceed it; the rule asks twice the smoke group's measured fuel, which the first run gives.

### 6. The expected classes

Reasoned from the sources and the guest's facts (`docs/reference/limitations.md`), and confirmed natively with stand-ins that make `subprocess.Popen` raise `OSError(58, 'wasi does not support processes')` and `threading.Thread.start` raise `RuntimeError("can't start new thread")` (EXECUTED: pydantic-core 13 failed, 5,827 passed, 118 skipped, 8 xfailed; pydantic 7 failed, 10,844 passed, 145 skipped, 28 xfailed). Each class's `match` is the house's regular expression for its cause, and each has its gap, its digest computed with `scan.digest` from its list file.

| family | id | group | members | reason |
|---|---|---|---|---|
| pydantic-core | `no-processes` | pydantic-core-r | 13: `test_errors.py::test_errors_include_url_envvar` (7) and `validators/test_decimal.py::test_validate_max_digits_and_decimal_places_pydecimal_huge_exponent` (6) | each starts Python again in another process (both skip themselves on emscripten) |
| pydantic | `no-processes` | pydantic-r | 6: `test_exports.py`'s four import tests, `test_generics.py::test_generic_model_pickle_different_module`, `test_pickle.py::test_cloudpickle_model_with_defs` | each imports pydantic, or pickles a model, in another process (the fixture skips on emscripten) |
| pydantic | `no-threads` | pydantic-smoke | 1: `test_main.py::test_model_rebuild_already_rebuilt_by_other_thread` | it rebuilds a model from two threads (it skips on emscripten) |

The other `emscripten` and platform branches, reasoned (READ, INFERRED):

- pydantic `tests/conftest.py:116` and `:179` (the subprocess fixture and the schema check) run on `wasi`: the first gives the no-processes class, the second needs jsonschema (Decision 2).
- pydantic `test_meta.py:12`: its xfail holds on every platform but emscripten, and with jsonschema present the invalid schema raises, so it is `xfailed`, as natively.
- pydantic `test_freethreaded.py` skips on a build that is not free-threaded; the guest's is not.
- pydantic `types/test_path.py:238`: the socket test skips unless `sys.platform` starts with `linux`; it skips in the guest.
- pydantic-core `test_tzinfo.py:172`: the Europe/London branch runs only on `linux`, so the guest skips that branch and the test passes.
- pydantic-core `test_hypothesis.py:27` skips on `win32` only. The judge's profile (derandomized, no database) replaces the conftest's `fast` profile; natively the file passes under it (EXECUTED).
- pydantic-core's recursion guard stops at 49 levels on wasm (limitations): `serializers/test_any.py:385`, `validators/test_definitions_recursive.py:715` and pydantic's `test_main.py:3219` read the limit from `_recursion_limit` or allow any depth up to 255, so they hold at 49; pydantic's `test_recursion_depth_exceeded_error` and its serialization siblings nest 1,000 levels, past either guard.

The classes that only a run can decide are in the landing notes.

### 7. The shards

- The four smoke groups join `upstream-pure-smoke-b` (Linux), which measured 465.8 G and stays under the packing's 725 G with them.
- `upstream-windows-pydantic`, a new Windows shard, runs pydantic-core's and pydantic's smoke groups too, so the Rust module that unwinds is judged on Windows as on Linux, as 190's Decision 8 gate asks ("its suites run on `panic=unwind` on Linux and Windows"). It is a shard of its own so `upstream-windows`' fetch stays numpy's, pandas' and CPython's.
- `upstream-release-070` holds `pydantic-core-r` and `pydantic-r`, its minutes (3.7) estimated from their provisional fuel at `upstream-pure-r-113`'s rate, as `upstream-release-069`'s were.

### 8. The smoke bound

The four smoke groups record 193 G together, and the test-source smoke groups at this head 1,183.1 G before them, past `SMOKE_TOTAL_BOUND`'s 1.2 T. By 191's rule (its Decision 8: the sum at the head, plus 17 G, rounded up to 10 G) the bound is 1.4 T (1,376.1 G plus 17 G). 191's rule also says the bound is never raised ahead of a measurement; this raise is, on upper estimates, and its comment says so. The first measured fuel sets it again by the same rule. This is a choice for the owner (choice 2).

## Intent

The two pydantic suites, and the two small ones beneath them, run in the guest on `panic=unwind`, on Linux and Windows, so the owner's gate can be read from a run, and every failure the guest causes is named by a class whose cause is one of its documented limits.

## Design

No harness code changes but the bound and three patterns. The families use the package driver and its test-source keys as they are; the only new values are data: four TOMLs and `.ini`, three list files, three gaps, seven `kit-extra.txt` lines, three pins and their download lines, the `packages.toml` rows, the shards and the caps.

## Scope

In: Decisions 1 to 8. Out: email-validator (`EmailStr` stays unavailable, limitations), pydantic-settings and pydantic-extra-types (their `.sh` scripts are not tests the stage runs), pytest-timeout, pytest-benchmark, pytest-examples and pytest-run-parallel, a set built here, and any measured figure.

## Acceptance criteria

1. The four families load, and the package, tier, shard, kit and gap rules hold (`uv run pytest tests/lint tests/unit -q`).
2. Each test source's pin is in `SHA256SUMS`, `00_download.sh` fetches it, and a set built from these pins carries it in `MANIFEST`.
3. The first run of a built set runs the four smoke groups on Linux and pydantic-core's and pydantic's on Windows, and the release run runs `upstream-release-070`; each group's fuel and each class's members are then written from that run, as the landing notes list.
4. No figure in this specification or its files is called measured unless a run measured it.

## The owner's choices

None is decided here; each is the orchestrating session's to put to the owner.

1. **jsonschema for pydantic's schema check.** A (this build): jsonschema 4.17.3 and pyrsistent 0.20.0 as test-only wheels, the last pure jsonschema, since pydantic's conftest checks every schema with it on every platform but emscripten. B: wait for 0.1.5's jsonschema with referencing and rpds-py in the set, and keep pydantic's suite out until then. C: a test-side stand-in for `jsonschema` that accepts every schema, which would weaken that check.
2. **The smoke bound raised ahead of a measurement.** A (this build): 1.4 T, by 191's rule on the four groups' upper estimates, set again from the first measurement. B: keep 1.2 T and the four families `later` until a run of a built set has measured them, as 187's orjson and 191's nine families did.
3. **The two small suites whole in the normal tier.** A (this build): annotated-types' and typing-inspection's whole suites as their smoke groups, as six's and typing-extensions' are, with no release group or shard. B: a fifth of each in the normal tier and the rest in the release tier, as the roadmap's line reads, at the cost of two more session starts.
4. **The families named `suite` with provisional fuel.** A (this build): `suite`, each group's `measured` an upper estimate marked provisional, so the first run measures them; a group that runs out of its cap gives no measurement and is raised and run again. B: `later` until a run has measured them, the precedent of 187 and 191, though no run then measures them without a branch that names them.

## Landing notes

Built 2026-11-16, on 190's head `5cc59db4`.

- **No set was built.** python.org and rustup's dist server were refused here, and the container has 4.6 G of disk; the only built set at hand is a 0.1.4-line set without pydantic-core. So nothing ran in the guest, and every fuel figure is provisional (Decision 5).
- **The native runs (EXECUTED).** CPython 3.15.2 (the line's own `cpython-3.15.2+20261026` build), the pinned wheels and the seven test-only wheels, numpy 2.5.4, pandas 3.1.0, cloudpickle 3.1.2, Faker 40.54.0, tqdm 4.70.1, pytz, python-dateutil and tzdata, with the `.ini` drafts and the driver's flags (`--import-mode=importlib --strict-markers --strict-config -p no:cacheprovider -p no:faulthandler`):
  - annotated-types: 256 passed in 0.29 s. typing-inspection: 108 passed, 2 skipped in 0.20 s.
  - pydantic-core (benchmarks and `test_docstrings.py` left out): 5,840 passed, 118 skipped, 8 xfailed; with the stand-ins, 13 failed (the no-processes class), 5,827 passed.
  - pydantic (benchmarks, mypy, plugin and `test_docs.py` left out, from the source's root, with jsonschema 4.17.3): 10,851 passed, 145 skipped, 28 xfailed in 19.3 s; with the stand-ins, 7 failed (no-processes 6, no-threads 1), 10,844 passed.
  - pydantic-core's validators, serializers and `test_hypothesis.py` under the judge's hypothesis profile loaded after the conftests: 6 failed (the no-processes members in those folders), 5,407 passed, 116 skipped, 8 xfailed.
  - With the `.ini` files as committed, the stand-ins and the judge's hypothesis profile: pydantic-core whole 13 failed, 5,827 passed, 118 skipped, 8 xfailed in 14.06 s; its smoke group alone 2,809 passed, 52 skipped, 1 xfailed in 3.13 s; pydantic whole (with `test_public_internal` deselected) 7 failed, 10,843 passed, 145 skipped, 28 xfailed in 20.85 s, the failures exactly the two classes' lists; its smoke group alone 1 failed (no-threads), 2,606 passed, 65 skipped, 8 xfailed in 4.69 s; annotated-types 256 passed in 0.35 s; typing-inspection 108 passed, 2 skipped in 0.22 s.
- **What the first run measures, and which numbers it replaces.** The pull request's own run, with a set built from this branch (its `build` job), runs the four smoke groups in `upstream-pure-smoke-b` on Linux and pydantic-core's and pydantic's in `upstream-windows-pydantic` on Windows; a `ci:full` or release-tier run runs `upstream-release-070`. From those records, in one commit:
  1. each group's `measured` in its TOML, replacing 64 G (pydantic-core-smoke), 210 G (pydantic-core-r), 89 G (pydantic-smoke), 300 G (pydantic-r), 21 G (annotated-types-smoke) and 19 G (typing-inspection-smoke), and each `fuel` the rule's cap of it, replacing 96 G, 320 G, 140 G, 450 G, 32 G and 29 G; each family's `budget`, the sum of its caps, replacing 416 G, 590 G, 32 G and 29 G; the provisional comments go;
  2. each family's cap in `tests/lint/budget.toml`, twice its smoke group's measured fuel (the gather's "new family" line), replacing 192 G, 280 G, 64 G and 58 G;
  3. `SMOKE_TOTAL_BOUND`, the sum of every test-source smoke group's measured fuel plus 17 G, rounded up to 10 G, replacing 1.4 T, and its comment;
  4. `upstream-pure-smoke-b`'s comment (the four groups' measured fuel) and `upstream-release-070`'s minutes, from the release run's measured minutes, replacing 3.7;
  5. each expected class's list file and gap digest, from the members the run records, and any class the run shows (below). A group that runs out of its provisional cap is not measured by that run: its cap is raised past the fuel it reached, in a commit that says so, and it runs again.
- **The classes only a run can decide.** Reading cannot settle these; each is written, with its members and reason, from the first run's record, or shown not to exist:
  - **Recursion through Python stops at 40 to 250 levels in the guest** (limitations). Candidates: pydantic-core's `serializers/test_functions.py::test_recursive_call` (skipped on emscripten and win32; Python and Rust frames alternate until `RecursionError`), `test_hypothesis.py::test_recursive` (skipped on emscripten), and pydantic's recursive-model tests in `test_forward_ref.py` (one expects `RecursionError` with pydantic's note), `test_edge_cases.py` (in the smoke group, so a class there is a normal-tier one) and `test_generics.py`. If any raises earlier or with another message, it is a class with the limitations page as its closer.
  - **A stack-overflow trap.** pydantic's `test_schema_gather.py::test_deeply_nested_schema` is skipped on emscripten because freeing its 10,000-deep schema overflows the JavaScript stack. In the guest the gather is iterative (pydantic-core's `src/schema_gather.rs` walks an explicit stack, READ) and CPython frees nested dicts through its trashcan, and the limitations page names about 32,000 levels for a nested list, so it is expected to pass (INFERRED). If it traps, the group's session ends there: it then gets a `[[trap]]` of its own and its gap, both written from the run's trap message. A trap entry cannot be written before a run, since its gap matches the trap's digest.
  - **wasm32's sizes.** `sys.maxsize` is 2**31 - 1 and Rust's `usize` is 32 bits. No test reads `sys.maxsize`, and the 64-bit figures the tests use are Rust `i64` values (READ), so none is expected; a run confirms it.
  - **The set's own packages.** Natively matplotlib was absent and numpy, pandas, cloudpickle and Faker were present; the guest carries all of them, so a test that skipped natively may run. Natively the suites were clean with them, so none is expected.
  - **inline-snapshot and jsonschema in the guest**: both run natively on the same CPython; inline-snapshot reports through rich at the session's end, and pytest-mock's and its plugins load by entry point from the kit. A run confirms both.
  - **`test_garbage_collection.py`**: 2.7 s natively, the suite's longest file, ten loops of 10,000 validator builds with `gc.collect()`; in the release tier.
- **`MANIFEST` changes.** The three new test-source pins are `SHA256SUMS` lines, and `MANIFEST` carries every pin, so a set built from this branch has three more `MANIFEST` lines than 190's; nothing else in the set changes.
- **The roadmap's line** is replaced by a built line naming this specification.
