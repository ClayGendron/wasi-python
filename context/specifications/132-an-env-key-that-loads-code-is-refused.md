# 132: an `env=` key that loads code is refused

- **Status:** **built 2026-10-25 on `spec/132-an-env-key-that-loads-code-is-refused`, base `f6cd4212`, rebased onto `dev`'s `c409e98b` as pull request #5 (head `2802b723`); the release workflow's run 40212238735 green; reviewed (`../reviews/132-an-env-key-that-loads-code-is-refused-pr-2026-10-25.md`).** Before: **Reviewed before build 2026-10-25** (`../reviews/132-an-env-key-that-loads-code-is-refused-spec-2026-10-25.md`, "Fit to build once finding 1 is closed by refusing the `_PYTHON_` prefix or by narrowing the Intent with a pin-move survey line"): finding 1 closed in Decision 1 by the prefix rule (every key that begins with `_PYTHON_` is refused) and the Design's pin-move line, the Lows applied in the Disposition (check 1's host-only ordering row, Decision 3's places and three more readers, three sentences corrected). Before: **drafted 2026-10-25** from the 0.1.0 security audit (`../reviews/0.1.0-security-audit-2026-10-25.md`, finding F1), on main `2cd47507`'s code (the research branch `2c8744fe` carries the same `src/`). Its checks are to be written first and seen failing on main's code (Decision 4); a different agent reviews the build (AGENTS.md, rule 8: runner code and a security fix).
- **Date:** 2026-10-25
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural**: `src/wasi_python/_limits.py` (one string constant and one clause in `_check_inputs`), `src/wasi_python/runner.py` (one sentence in each of the three `env:` docstrings), one new unit-check file in the `own-runner` shard and two rows in `tests/unit/test_runner_inputs.py`, `docs/explanation/security-model.md`, `docs/reference/guest-filesystem.md`, `docs/how-to/embed-from-other-languages.md`, `docs/reference/python-api.md` (regenerated), `CHANGELOG.md`. It touches nothing under `scripts/`, `recipes/`, `downloads/SHA256SUMS` or the release workflow, and no artifact byte. It **tightens** a default and loosens none (constitution §4.15): the `env=` keys CPython keeps for its own build are refused before any work.
- **Depends on:** nothing in flight. Spec 114 (HOME is never the root) and 113 (every module cache is guarded) landed; this closes a gap of the same family, an argument that reaches past the import-path rules.
- **Research it stands on:** the audit's F1 (`0.1.0-security-audit-2026-10-25/FINDINGS-DETAIL.md` §1, `findings.json` fingerprint `runner-env.sysconfig-PYTHON-SYSCONFIGDATA-PATH.loads-code-outside-import-path-rules`), reproduced by hunter h15, verifier v03 and record verifier r01 on both binaries; h15's survey of 52 packages' environment-driven loaders (`agents/h15-env-loaders/artifacts/evidence/`); the pre-build review's survey of what CPython 3.15.0 reads past isolated mode (its section *The refused list against CPython 3.15.0*).

## The problem

The security model promises that code planted in a root never runs at start-up or on import in a later call. The runner holds it with an isolated interpreter: `site` off, only the stdlib zip on `sys.path`, every `PYTHON*` variable ignored, and `import_path` entries allowed only from read-only grants with nothing writable under them.

CPython's `sysconfig` reads its private `_PYTHON_*` build settings past that wall, and one of them loads code. `_get_sysconfigdata` (`Lib/sysconfig/__init__.py:356-363`, shipped compiled in the zip) reads `_PYTHON_SYSCONFIGDATA_PATH` from `os.environ` without consulting `sys.flags.ignore_environment`, and when it is set, finds `_sysconfigdata__wasi_wasm32-wasi` in that folder with `PathFinder` and runs it with `exec_module`. `import pandas` calls `sysconfig.get_config_var` at import (`pandas/compat/_constants.py:21`); so do scipy, scikit-learn, joblib and statsmodels.

The runner passes the key through. `_check_inputs` (`src/wasi_python/_limits.py:139`) refuses an empty key and a key with `=`, nothing else; `_call.py:452` lays `env=` over `BASE_ENV` and `HOME`; the session's opening does the same (`_sessions.py:999`); the reactor copies the environment into `os.environ` (`recipes/reactor_bootstrap.py:143`).

**Reproduced** (EXECUTED by v03 and r01, and again by the pre-build review through `sysconfig.get_config_var('CC')`): call 1 with a writable root writes `/data/_sysconfigdata__wasi_wasm32-wasi.py`; call 2 on the same root with `env={"_PYTHON_SYSCONFIGDATA_PATH": "/data"}` runs `import pandas`, and the planted module prints to stderr, on the snapshot and on the plain binary. Without the entry the module did not run. The `PYTHONPATH=/data` control raised `ModuleNotFoundError`: isolated mode ignores the documented variable and not this private one.

**Who it reaches.** An embedder that forwards this variable into a call on a folder an earlier guest could write: a reused root, a writable grant or a writable mount. The project's own `scripts/python-wasi-cross:22-25` exports it with three other `_PYTHON_*` names, so a shell that sourced it and ran `wasi-python run --env _PYTHON_SYSCONFIGDATA_PATH …` would. The security model's *Reused roots* list names `env=` overrides of `HOME` and `PYTHONTZPATH` only (`docs/explanation/security-model.md:82`).

**The same shape, one step further out** (h15): `SCIKIT_LEARN_DATA` names the folder scikit-learn's `fetch_*` functions load cached datasets from with `joblib.load` and `pickle`, so an `env=` naming a reused root runs a pickle an earlier guest planted on an ordinary `fetch_california_housing()`. That is not at start-up or import, and it is the documented `HOME` shape (`HOME=/data` reaches `/data/scikit_learn_data` too): not a finding, but a sentence the security model lacks.

## Decisions

### 1. The rule: every key CPython keeps for its own build is refused

`_check_inputs` refuses, with `ValueError`, any `env=` key that begins with `_PYTHON_`, before any folder is walked or any store made. The prefix is one string constant in `_limits.py`; its comment gives the reason in words: these are CPython's private build settings, none has a use inside the guest, and `sysconfig` reads them in isolated mode, where the documented `PYTHON*` variables are ignored; one, `_PYTHON_SYSCONFIGDATA_PATH`, names a folder whose `_sysconfigdata_*` module it runs. The match is by exact case, since the guest's environment is case-sensitive and the lowercase spelling is not read (the review's probe, EXECUTED). The clause comes after the illegal-name clause, so a key such as `_PYTHON_X=secret` still gets the message that never shows a key.

A prefix, not a list of names, because CPython adds to the family: it holds four names today (`_PYTHON_SYSCONFIGDATA_PATH`, `_PYTHON_SYSCONFIGDATA_NAME`, `_PYTHON_PROJECT_BASE`, `_PYTHON_HOST_PLATFORM`, all exported by `scripts/python-wasi-cross:22-25`), one of which loads code, and a refusal by one exact name would hold the Intent only until a later CPython read another past isolated mode, with every check here still green. The prefix refuses the next one too.

It loses no use. Nothing in `tests/`, `docs/` or `src/` passes a `_PYTHON_*` key to a guest: the review's `grep -rn "_PYTHON_"` over the three (EXECUTED) found only other names (`HOST_PYTHON_ARCHIVE`, `UV_PYTHON_PREFERENCE`, `UNPINNED_PYTHON_LOG`) and a build-log fixture string in `tests/unit/test_scan.py:1672`, and `tests/unit/test_runner_inputs.py -k env` (18 rows, EXECUTED) passes none.

The message names the key and points at the control the embedder meant: `env: {shown!r} is one of CPython's private build settings (_PYTHON_*), which isolated mode does not ignore; _PYTHON_SYSCONFIGDATA_PATH among them runs code from the folder it names. It is refused; grant a read-only folder with import_path instead.` The key is shown with `{shown!r}`, cut at 40 characters, as the value messages show it (`_limits.py:142`); no value is ever shown.

**Not refused, and said so:** the module-name selectors (`MPLBACKEND`, `QT_API`, `LOKY_PICKLER`, `SYMPY_GROUND_TYPES`, …), which pick a module by name from the read-only import path and are held safe by that path (`PYTHON_DOM` and `PY_SAX_PARSER` are ignored outright, gated on `ignore_environment`); `SCIKIT_LEARN_DATA` and `HOME`, which name data folders whose contents a package then unpickles, the documented shape, named in the security model (Decision 3). A general rule, "refuse or warn on an env value that names a writable root, grant or mount for a key known to select a code-bearing folder", is not built: the list of such keys is the packages', changes with every package landing, and the documented promise already puts a reused root's contents on the embedder.

### 2. Where it lives, and what it costs

One string constant and one `if` in `_check_inputs` (`_limits.py`, 185 lines today; the function 30), under its 80-line function bound. `_call.py` and `_sessions.py` are unchanged: `run`, `run_async` and `Session.__init__` all reach `_check_inputs` through `_checked` before any folder is checked (`runner.py:245,413,881`, `:581-582`), so a session's opening refuses as a call does. The reactor is **not** changed: dropping the keys in `recipes/reactor_bootstrap.py` would be defence in depth, but a recipe change is build-class and changes the artifact set, and the runner's refusal is the control; a note in the roadmap's build-class queue is enough (For the lane).

### 3. The documents and the CHANGELOG

`docs/explanation/security-model.md`, *Reused roots and state across calls*: the `env=` bullet becomes "**An `env=` that overrides `HOME`, `PYTHONTZPATH` or `SCIKIT_LEARN_DATA`** on a reused root, or into a writable grant or mount that a later call reuses. scikit-learn's cached datasets are pickles, so that folder's contents are code."

A new bullet under *Nothing planted runs at start-up* (`docs/explanation/security-model.md:31-34`): "`env=` may not set a key that begins with `_PYTHON_`: CPython's `sysconfig` reads these in isolated mode, and one, `_PYTHON_SYSCONFIGDATA_PATH`, runs the module it names, so a call raises `ValueError` before any work."

`docs/reference/guest-filesystem.md:85` gains: "An `env=` key that begins with `_PYTHON_` (such as `_PYTHON_SYSCONFIGDATA_PATH`), which isolated mode does not ignore, raises `ValueError`."

The three `env:` docstrings in `runner.py` (`run`, `run_async`, `Session`) gain the sentence "A key that begins with `_PYTHON_`, which CPython reads past isolated mode (`_PYTHON_SYSCONFIGDATA_PATH` loads code), raises `ValueError`.", and `uv run python tests/harness/api.py --write` regenerates `docs/reference/python-api.md`; `tests/public_api.txt` holds signatures and names, not docstrings, and stays byte-identical.

`docs/how-to/embed-from-other-languages.md`, *What you give up*, gains: "Do not pass a key that begins with `_PYTHON_` in the guest's environment: CPython's `sysconfig` reads these in isolated mode, and `_PYTHON_SYSCONFIGDATA_PATH` runs the module it names." An engine the embedder drives itself never meets the runner's refusal, so this page is where that reader learns it.

`README.md` and `SECURITY.md` are unchanged: the README has no list of env overrides, and `SECURITY.md:31` defers to the security model. No `docs/how-to/` page lists refusals (`grants.md:47` and `mounts.md:73` only say `env=` is laid over), so none changes but the embedding page above.

The CHANGELOG line under the unreleased section: "An `env=` key that begins with `_PYTHON_` is refused with `ValueError`: CPython's `sysconfig` reads these private build settings in isolated mode, and `_PYTHON_SYSCONFIGDATA_PATH` runs the module it names, so on a reused root a file an earlier guest wrote ran on `import pandas` in a later call."

### 4. The checks first

One unit file, `tests/unit/test_runner_env_keys.py`, in the `own-runner` shard (three systems), and two rows in an existing table:

1. **The plant is refused:** call 1 with `root=<folder>` writes `_sysconfigdata__wasi_wasm32-wasi.py` under `/data`; call 2 on the same root with `env={"_PYTHON_SYSCONFIGDATA_PATH": "/data"}` and a program `import pandas` raises `ValueError` naming the key **before the guest runs** (the `ValueError` itself; and one host-only row: with `$WASI_PYTHON_ARTIFACTS` set to an empty folder, `run(["-c", "pass"], env={"_PYTHON_SYSCONFIGDATA_PATH": "/data"})` raises the env `ValueError`, not the error an empty set raises, which shows the check comes before any artifact is read or store made; seen failing on main's code, where the empty set's error is raised). One row each for `run`, `run_async` and `Session`. Seen failing on main's code: today call 2 runs and stderr carries the planted marker.
2. **The control still runs:** call 2 without the entry prints `ok` and the marker is absent, on both binaries (`snapshot=True` and `False`).
3. **The documented variable is still ignored:** `env={"PYTHONPATH": "/data"}` with `import planted` raises `ModuleNotFoundError` in the guest, not `ValueError` in the runner (the rule refuses only CPython's private settings, not what isolated mode already ignores).
4. **The message:** names the key, `_PYTHON_SYSCONFIGDATA_PATH` and `import_path`; no value is quoted.
5. **The prefix, with no guest:** `tests/unit/test_runner_inputs.py`'s refused table gains rows for `_PYTHON_SYSCONFIGDATA_PATH` and `_PYTHON_PROJECT_BASE` (a name that loads no code, refused by the prefix), each `ValueError`; seen failing on main's code.

The rows of the new file run the real runner on the frozen set through `$WASI_PYTHON_ARTIFACTS`, as `tests/unit/test_runner_module_caches.py` does.

## Intent

After this specification, no `env=` key makes the guest's interpreter load code from a folder the import-path rules did not judge. Every key CPython keeps for its own build (`_PYTHON_*`), among them `_PYTHON_SYSCONFIGDATA_PATH`, the one that loads code today, is refused before any work, in a call and in a session, with a message that says what to do instead. The rule is a prefix, not a name, and that is why the promise survives a CPython pin move: a private setting the next CPython adds is refused without an edit here. The security model names the folders an `env=` can point at a reused root (`HOME`, `PYTHONTZPATH`, and `SCIKIT_LEARN_DATA`, whose cached datasets are pickles and so are code) so an embedder reusing a root knows what an `env=` can reach.

## Design

- `src/wasi_python/_limits.py`: the prefix constant and one clause in `_check_inputs`, after the illegal-name clause (Decision 1), the comment giving the reason in words.
- `src/wasi_python/runner.py`: the sentence in the three `env:` docstrings (Decision 3); `docs/reference/python-api.md` regenerated by `uv run python tests/harness/api.py --write`.
- `tests/unit/test_runner_env_keys.py`: checks 1 to 4 of Decision 4, first; its line in `tests/release_shards.toml`'s `own-runner` shard. `tests/unit/test_runner_inputs.py`: check 5's two rows.
- `docs/explanation/security-model.md`, `docs/reference/guest-filesystem.md`, `docs/how-to/embed-from-other-languages.md`, `CHANGELOG.md`: Decision 3.
- At a CPython pin move, the prefix is not the whole guard: the specification that moves the pin re-reads `Python/initconfig.c` and `Lib/sysconfig/__init__.py` (with `Lib/site.py`) for a variable read past isolated mode that loads code and does not begin with `_PYTHON_`, and extends the rule if it finds one; the builder writes that sentence into the roadmap with this specification's roadmap line.
- The commits, in order: the specification with its roadmap line and the checks seen failing; the rule; the docstrings and the documents.

## Scope

In: Decisions 1 to 4. Out: the reactor's own drop of the keys (build-class; a roadmap note); a general rule over package-specific folder keys (Decision 1); any change to what the guest sees but the refusal.

## Acceptance criteria

1. The three rows of check 1 and its host-only ordering row green on three systems, each seen failing first on `2cd47507`'s code, output in `build/132/`.
2. Checks 2 to 5 green.
3. `_check_inputs` stays under 80 lines; `_limits.py` under its ceiling; `tests/public_api.txt` unchanged and `docs/reference/python-api.md` regenerated; `ruff check`, `ruff format --check`, `mypy` clean; no code file names a specification, review, finding or `context/` path.
4. The sentences of Decision 3 present in the three pages, the three docstrings and the CHANGELOG.
5. The release workflow dispatched on the built tip; every red line a growth line of another entry or G7; the Windows legs read.

## For the lane

- **Kind:** parallel-safe; lands in the next wave; shares `CHANGELOG.md`, `context/roadmap.md`, `tests/release_shards.toml` and `src/wasi_python/runner.py` (docstrings only) with others, and `docs/explanation/security-model.md` with 134 and 137 (each adds its own sentences; conflicts are line-local).
- **Claim list** (each line "132:"): new checks, the rows of Decision 4; retired none; lost passes none; fuel and bytes none. The judge hash changes in the new unit file, `tests/unit/test_runner_inputs.py` and `tests/release_shards.toml`.
- **Flags:** `--accept "132: an env= key that begins with _PYTHON_ (CPython's private build settings; _PYTHON_SYSCONFIGDATA_PATH loads code) is refused before any work in run, run_async and Session"`, `--accept-judge "132: one unit file holds the refusal, its ordering row, the no-env control and the PYTHONPATH control in the own-runner shard; two rows added to the inputs table; no existing expectation edited"`.
- **New rows** (the claim list's `new`, each "132:"): `tests/unit/test_runner_env_keys.py::test_the_key_on_a_planted_root_is_refused_before_the_guest_runs[run]`, `[run_async]`, `[Session]`; `::test_the_key_is_refused_before_any_artifact_is_read[run]`, `[run_async]`, `[Session]`; `::test_without_the_key_the_planted_module_never_runs[snapshot]`, `[plain]`; `::test_pythonpath_is_still_ignored_not_refused`; `::test_the_message_names_the_key_and_the_control_and_quotes_no_value[_PYTHON_SYSCONFIGDATA_PATH]`, `[_PYTHON_PROJECT_BASE]`; `tests/unit/test_runner_inputs.py::test_an_env_entry_the_guest_would_see_differently_is_refused[the sysconfig data folder]`, `[a private build setting that loads no code]`. Retired none; lost none; fuel and bytes none. The orchestrator accepts locally with the two flags above until step 3 of spec 138 lands.
- **Roadmap, for the orchestrator** (the builder did not edit it): 132's line, and the Design's sentence that the specification which moves CPython's pin re-reads `Python/initconfig.c` and `Lib/sysconfig/__init__.py` (with `Lib/site.py`) for a variable read past isolated mode that loads code and does not begin with `_PYTHON_`.
- **Build-class note for the roadmap:** at the next rebuild of the line, the reactor may drop every `_PYTHON_*` key from `os.environ` as isolated mode drops `PYTHONPATH` (defence in depth; the runner's refusal is the control).

## Landing notes

Built 2026-10-25 by an agent (Claude, session `session_01FZg7sj9WydizfDe18oakTT`) on `spec/132-an-env-key-that-loads-code-is-refused`, base `f6cd4212` (the head of pull request #4; its `src/` is main `2cd47507`'s, so the base's code is the code Decision 4 names). Three commits, in the Design's order: the checks seen failing (`5452a70b`), the rule (`8de8bd4f`), the docstrings, the documents and the CHANGELOG (`d75d147c`), then this section. The roadmap line and its pin-move sentence are not written here: the builder was told not to edit the roadmap, so they wait for the orchestrator (For the lane).

Files: `src/wasi_python/_limits.py` (the constant `PRIVATE_ENV_PREFIX` with its reason in words, one clause in `_check_inputs` after the illegal-name clause, the function's docstring; `_check_inputs` is 38 lines, `_limits.py` 200); `src/wasi_python/runner.py` (the three `env:` docstrings); `docs/reference/python-api.md` (regenerated by `uv run python tests/harness/api.py --write`); `tests/public_api.txt` unchanged; `tests/unit/test_runner_env_keys.py` (new, 11 rows); `tests/unit/test_runner_inputs.py` (two rows in the refused table); `tests/release_shards.toml` (the new file in `own-runner`); `docs/explanation/security-model.md`, `docs/reference/guest-filesystem.md`, `docs/how-to/embed-from-other-languages.md` (Decision 3's sentences where it places them); `CHANGELOG.md`. `README.md` and `SECURITY.md` unchanged, as Decision 3 settles.

The CHANGELOG had no unreleased section: 0.1.0 is dated 2026-10-23 and nothing has been bumped since. The line goes under `### Security` in a new `## 0.1.1 — unreleased` section, in `release/version.py`'s own format; `release/version.py check` still answers `ok 0.1.0`. The next version is the owner's to choose: if it is not 0.1.1, the heading is renamed by hand, and `release/version.py bump 0.1.1` would refuse, since the section already exists.

The checks seen failing on `f6cd4212`'s code, all in `build/132/first-failing.txt` (10 failed, 10 passed):

- Check 1, the three plant rows (`test_the_key_on_a_planted_root_is_refused_before_the_guest_runs[run|run_async|Session]`): "`run ran with _PYTHON_SYSCONFIGDATA_PATH: exit 0, planted module ran: True`", and the same for `run_async` and `Session`.
- Check 1, the ordering rows on an empty set (`test_the_key_is_refused_before_any_artifact_is_read[run|run_async|Session]`): `ArtifactsMissing: …/empty-set has no MANIFEST (from $WASI_PYTHON_ARTIFACTS)`, the empty set's error, not the env refusal. One row per entry point, where Decision 4 asks for one.
- Check 4, the message (`test_the_message_names_the_key_and_the_control_and_quotes_no_value[_PYTHON_SYSCONFIGDATA_PATH|_PYTHON_PROJECT_BASE]`): `ArtifactsMissing`, as above.
- Check 5, the table (`test_an_env_entry_the_guest_would_see_differently_is_refused[the sysconfig data folder|a private build setting that loads no code]`): `Failed: DID NOT RAISE ValueError`.
- Checks 2 and 3 are controls and passed on the base's code, as they must: `test_without_the_key_the_planted_module_never_runs[snapshot|plain]` and `test_pythonpath_is_still_ignored_not_refused`.

After the rule: `tests/unit/test_runner_env_keys.py` and `tests/unit/test_runner_inputs.py`, 59 passed (`build/132/after-rule.txt`). `ruff check`, `ruff format --check`, `mypy src/wasi_python` (Success, 24 files) and `tests/checks/test_rules.py` with `tests/unit/test_release_version.py` (95 passed, 1 skipped) clean; `tests/harness/wrap.py --check` clean on every changed page.

The fast tier, once at the end (`uv run pytest -m "not slow" -n 3`, `build/132/fast-tier.txt`), on a machine whose load average was 275 (other agents' jobs; the tier took 35 min 28 s): `1 failed, 3145 passed, 51 skipped`; ratchet `lost 1 · gained 0 · grew 0`. The one loss is `tests/checks/test_v1_4_embedding.py::test_concurrent_calls_get_their_own_results`, a `subprocess.TimeoutExpired` at its 120 s fail-safe, in a check this change does not touch. Run alone by node id straight after, it passed in 87 s (`build/132/concurrent-rerun.txt`). So the loss was the machine's load, not this change. The ratchet reads `gained 0`: the new rows are unit rows, counted in the line's unit suite (2473 of 2482, 9 skipped), not in a goal's count, and none of them failed in that run (its one failure is named above). The fast tier was not run a second time: under this load it costs another 35 minutes. A reviewer or the lane should see it green on a quieter machine or in CI.

The release run: not dispatched by the builder. The orchestrator dispatched the release workflow on the built tip `7d619531`, run 40212238735 (2026-10-25), before `ci-status` exists, as AGENTS.md's transitional paragraph asks: every job green, the release tier and the publishing jobs skipped as on any branch run; the set reused (`wasi-python-set-v1-87caffda…`), `same-bytes` and both rebuilds from the pins green; the gather `856/1876 pass · 128 gap · 7 blocked · 0 fail`; the `own-runner` shard collected `tests/unit/test_runner_env_keys.py` on Windows, macOS and Linux, with 650 rows each against 637 at v0.1.0's run and Windows' skips unchanged at 12; `test_concurrent_calls_get_their_own_results` passed on all three. Pull request #4 then merged into `dev` by squash, and the branch was rebased onto `c409e98b` as pull request #5: `git range-diff` shows the four commits identical and `git diff 7d619531 2802b723 -- src tests` is empty, so the run's reading stands for the head's code.

## One line

Every `env=` key that begins with `_PYTHON_`, CPython's private build settings, among them `_PYTHON_SYSCONFIGDATA_PATH`, which loads code past isolated mode, is refused before any work, and the security model names the folders whose contents are code.
