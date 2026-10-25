# 132: an `env=` key that loads code is refused

- **Status:** **drafted 2026-10-25** from the 0.1.0 security audit (`../reviews/0.1.0-security-audit-2026-10-25.md`, finding F1), on main `2cd47507`'s code (the research branch `2c8744fe` carries the same `src/`). Not for build until its pre-build review (AGENTS.md, rule 8: runner code and a security fix). Its checks are to be written first and seen failing on main's code (Decision 4).
- **Date:** 2026-10-25
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural**: `src/wasi_python/_limits.py` (one tuple and one clause in `_check_inputs`), one unit-check file in the `own-runner` shard, `docs/explanation/security-model.md`, `README.md` if its *Not protected* list names the env overrides, `CHANGELOG.md`. It touches nothing under `scripts/`, `recipes/`, `downloads/SHA256SUMS` or the release workflow, and no artifact byte. It **tightens** a default and loosens none (constitution §4.15): one more `env=` key is refused before any work.
- **Depends on:** nothing in flight. Spec 114 (HOME is never the root) and 113 (every module cache is guarded) landed; this closes a gap of the same family, an argument that reaches past the import-path rules.
- **Research it stands on:** the audit's F1 (`0.1.0-security-audit-2026-10-25/FINDINGS-DETAIL.md` §1, `findings.json` fingerprint `runner-env.sysconfig-PYTHON-SYSCONFIGDATA-PATH.loads-code-outside-import-path-rules`), reproduced by hunter h15, verifier v03 and record verifier r01 on both binaries; h15's survey of 52 packages' environment-driven loaders (`agents/h15-env-loaders/artifacts/evidence/`).

## The problem

The security model promises that code planted in a root never runs at start-up or on import in a later call. The runner holds it with an isolated interpreter: `site` off, only the stdlib zip on `sys.path`, every `PYTHON*` variable ignored, and `import_path` entries allowed only from read-only grants with nothing writable under them.

CPython's `sysconfig` reads one private variable past that wall. `_get_sysconfigdata` (`Lib/sysconfig/__init__.py:356-363`, shipped compiled in the zip) reads `_PYTHON_SYSCONFIGDATA_PATH` from `os.environ` without consulting `sys.flags.ignore_environment`, and when it is set, finds `_sysconfigdata__wasi_wasm32-wasi` in that folder with `PathFinder` and runs it with `exec_module`. `import pandas` calls `sysconfig.get_config_var` at import (`pandas/compat/_constants.py:21`); so do scipy, scikit-learn, joblib and statsmodels.

The runner passes the key through. `_check_inputs` (`src/wasi_python/_limits.py:139`) refuses an empty key and a key with `=`, nothing else; `_call.py:452` lays `env=` over `BASE_ENV` and `HOME`; the session's opening does the same (`_sessions.py:999`); the reactor copies the environment into `os.environ` (`recipes/reactor_bootstrap.py:143`).

**Reproduced** (EXECUTED by v03 and r01): call 1 with a writable root writes `/data/_sysconfigdata__wasi_wasm32-wasi.py`; call 2 on the same root with `env={"_PYTHON_SYSCONFIGDATA_PATH": "/data"}` runs `import pandas`, and the planted module prints to stderr, on the snapshot and on the plain binary. Without the entry the module did not run. The `PYTHONPATH=/data` control raised `ModuleNotFoundError`: isolated mode ignores the documented variable and not this private one.

**Who it reaches.** An embedder that forwards this variable into a call on a folder an earlier guest could write: a reused root, a writable grant or a writable mount. The project's own `scripts/python-wasi-cross:25` exports it, so a shell that sourced it and ran `wasi-python run --env _PYTHON_SYSCONFIGDATA_PATH …` would. The security model's *Reused roots* list names `env=` overrides of `HOME` and `PYTHONTZPATH` only (`docs/explanation/security-model.md:82`).

**The same shape, one step further out** (h15): `SCIKIT_LEARN_DATA` names the folder scikit-learn's `fetch_*` functions load cached datasets from with `joblib.load` and `pickle`, so an `env=` naming a reused root runs a pickle an earlier guest planted on an ordinary `fetch_california_housing()`. That is not at start-up or import, and it is the documented `HOME` shape (`HOME=/data` reaches `/data/scikit_learn_data` too): not a finding, but a sentence the security model lacks.

## Decisions

### 1. The rule: a key that makes the interpreter load code from a folder is refused

`_check_inputs` refuses, with `ValueError`, any `env=` key in a small tuple `_CODE_FOLDER_ENV` in `_limits.py`, before any folder is walked or any store made. The tuple holds **`_PYTHON_SYSCONFIGDATA_PATH`** alone today; its comment says what qualifies: a variable that names a folder the guest's interpreter loads code from outside the import-path rules, which isolated mode does not ignore. The message names the key and points at the control the embedder meant: `env: _PYTHON_SYSCONFIGDATA_PATH names a folder the interpreter loads code from; it is refused, since isolated mode does not ignore it. Grant a read-only folder with import_path instead.` It is quoted with `!r` as the other key messages are not (the key is from a fixed list, so it is safe to show).

**Not refused, and said so:** `_PYTHON_SYSCONFIGDATA_NAME` (reaches only the zip, h15 EXECUTED); the module-name selectors (`MPLBACKEND`, `QT_API`, `LOKY_PICKLER`, `SYMPY_GROUND_TYPES`, `PYTHON_DOM`, `PY_SAX_PARSER`, …), which pick a module by name from the read-only import path and are held safe by that path; `SCIKIT_LEARN_DATA` and `HOME`, which name data folders whose contents a package then unpickles, the documented shape, named in the security model (Decision 3). A general rule, "refuse or warn on an env value that names a writable root, grant or mount for a key known to select a code-bearing folder", is not built: the list of such keys is the packages', changes with every package landing, and the documented promise already puts a reused root's contents on the embedder.

### 2. Where it lives, and what it costs

One tuple and one `if` in `_check_inputs` (`_limits.py`, 185 lines today), under its 80-line function bound. `_call.py` and `_sessions.py` are unchanged: both call `_check_inputs` before any work, so a session's opening refuses as a call does. The reactor is **not** changed: dropping the key in `recipes/reactor_bootstrap.py` would be defence in depth, but a recipe change is build-class and changes the artifact set, and the runner's refusal is the control; a note in the roadmap's build-class queue is enough (For the lane).

### 3. The security model and the CHANGELOG

`docs/explanation/security-model.md`, *Reused roots and state across calls*: the `env=` bullet becomes "**An `env=` that overrides `HOME`, `PYTHONTZPATH` or `SCIKIT_LEARN_DATA`** on a reused root, or into a writable grant or mount that a later call reuses. scikit-learn's cached datasets are pickles, so that folder's contents are code." A new bullet under *What is refused* (or the list the page keeps for refused arguments): "An `env=` key that names a folder the interpreter loads code from (`_PYTHON_SYSCONFIGDATA_PATH`) is refused; isolated mode does not ignore it." `docs/how-to/` pages that list `env=` say the same in one line if they list refusals. The CHANGELOG line under the unreleased section: "An `env=` entry `_PYTHON_SYSCONFIGDATA_PATH` is refused: CPython's `sysconfig` reads it in isolated mode and runs the module it names, so on a reused root a file an earlier guest wrote ran on `import pandas` in a later call."

### 4. The checks first

One unit file, `tests/unit/test_runner_env_keys.py`, in the `own-runner` shard (three systems):

1. **The plant is refused:** call 1 with `root=<folder>` writes `_sysconfigdata__wasi_wasm32-wasi.py` under `/data`; call 2 on the same root with `env={"_PYTHON_SYSCONFIGDATA_PATH": "/data"}` and a program `import pandas` raises `ValueError` naming the key **before the guest runs** (`stats()` compiled and loaded unchanged, no store made: the row asserts the counts). One row each for `run`, `run_async` and `Session`. Seen failing on main's code: today call 2 runs and stderr carries the planted marker.
2. **The control still runs:** call 2 without the entry prints `ok` and the marker is absent, on both binaries (`snapshot=True` and `False`).
3. **The documented variable is still ignored:** `env={"PYTHONPATH": "/data"}` with `import planted` raises `ModuleNotFoundError` in the guest, not `ValueError` in the runner (the rule refuses only what isolated mode does not already ignore).
4. **The message:** names the key and `import_path`; no value is quoted.

The rows run the real runner on the frozen set through `$WASI_PYTHON_ARTIFACTS`, as `tests/unit/test_runner_module_caches.py` does.

## Intent

After this specification, no `env=` key makes the guest's interpreter load code from a folder the import-path rules did not judge. The one variable CPython reads past isolated mode is refused before any work, in a call and in a session, with a message that says what to do instead. The security model names the data folders whose contents are code (`HOME`, `PYTHONTZPATH`, `SCIKIT_LEARN_DATA`) so an embedder reusing a root knows what an `env=` can reach.

## Design

- `src/wasi_python/_limits.py`: the tuple `_CODE_FOLDER_ENV` and one clause in `_check_inputs` (Decision 1), the comment giving the reason in words.
- `tests/unit/test_runner_env_keys.py`: the four checks of Decision 4, first; its line in `tests/release_shards.toml`'s `own-runner` shard.
- `docs/explanation/security-model.md`, `README.md` if it lists the env overrides, `CHANGELOG.md`: Decision 3.
- The commits, in order: the specification with its roadmap line and the checks seen failing; the rule; the documents.

## Scope

In: Decisions 1 to 4. Out: the reactor's own drop of the key (build-class; a roadmap note); a general rule over package-specific folder keys (Decision 1); any change to what the guest sees but the refusal.

## Acceptance criteria

1. The three rows of check 1 green on three systems, each seen failing first on `2cd47507`'s code, output in `build/132/`.
2. Checks 2 to 4 green.
3. `_check_inputs` stays under 80 lines; `_limits.py` under its ceiling; `tests/public_api.txt` unchanged; `ruff check`, `ruff format --check`, `mypy` clean; no code file names a specification, review, finding or `context/` path.
4. The security model's two sentences and the CHANGELOG line (Decision 3) present.
5. The release workflow dispatched on the built tip; every red line a growth line of another entry or G7; the Windows legs read.

## For the lane

- **Kind:** parallel-safe; lands in the next wave; shares `README.md`, `CHANGELOG.md`, `context/roadmap.md` and `tests/release_shards.toml` with others, and `docs/explanation/security-model.md` with 134 and 137 (each adds its own sentences; conflicts are line-local).
- **Claim list** (each line "132:"): new checks, the rows of Decision 4; retired none; lost passes none; fuel and bytes none. The judge hash changes in the new unit file and `tests/release_shards.toml`.
- **Flags:** `--accept "132: an env= key that makes the guest interpreter load code from a folder (_PYTHON_SYSCONFIGDATA_PATH) is refused before any work in run, run_async and Session"`, `--accept-judge "132: one unit file holds the refusal, the no-env control and the PYTHONPATH control in the own-runner shard; no existing expectation edited"`.
- **Build-class note for the roadmap:** at the next rebuild of the line, the reactor may drop `_PYTHON_SYSCONFIGDATA_PATH` from `os.environ` as isolated mode drops `PYTHONPATH` (defence in depth; the runner's refusal is the control).

## Landing notes

Not yet built. The builder fills this section: the commits, the checks seen failing on main's code first, the fast tier, the branch's release run (its id, every line green on three systems, no growth line), the self-check list (`../reviews/README.md`), and the rebase onto the wave's tip with every conflict named.

## One line

The one environment variable CPython reads past isolated mode to load code, `_PYTHON_SYSCONFIGDATA_PATH`, is refused in `env=` before any work, and the security model names the data folders whose contents are code.
