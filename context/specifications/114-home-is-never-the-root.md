# 114: HOME is never the root

- **Status:** **drafted 2026-10-21** on `spec/114-home-is-never-the-root` from main `1875d4cd`,
  awaiting its pre-build review. The checks are written first and seen failing on main's code
  (EXECUTED, `build/114/checks-on-main.log` in the builder's worktree, against the main tree's
  frozen set, `SHA256SUMS` `d0d91cef`): 12 rows fail, the 2 fresh-HOME guard rows pass. No fix
  is written yet. A different agent reviews it before build.
- **Date:** 2026-10-21
- **Owner:** Clay Gendron
- **Kind:** **build-class** and runner code. Build-class because it adds one recipe file under
  `recipes/` and two `--file` lines to `scripts/steps/70_zip.sh` (Decision 2), so the stdlib zip
  changes and the set is rebuilt. Runner code because `src/wasi_python/_call.py` and
  `_sessions.py` change what HOME a guest gets (Decision 1). Both need the pre-build review
  (constitution §5.6, the build recipe and the artifact set; AGENTS.md rule 8, the runner). It is
  **not structural** by AGENTS.md's letter, and Decision 6 says how the build keeps it so: no
  module-level mutable or lock, no private wasmtime-py name, no platform branch, no test seam, no
  module past 1,500 lines, and no function past 80 lines, including the two already on
  `LONG_FUNCTIONS` (`_call.py:_instance`, `_sessions.py:_open_session`), which must not grow.
- **Depends on:** landed and unchanged: 025 (nothing writable by default), 032 (mounts and their
  placeholder folder), 042 (reportlab in the zip), 084 (the fresh HOME's removal), 111 (the
  filesystem table, which serves a preopen nested inside a mount). Beside 113 (the module cache,
  drafted in parallel): the two touch different lines of `_call.py` and `_sessions.py`; whichever
  lands second rebases and names the conflict.
- **Research it stands on:** the 0.1.0 security review,
  `../reviews/0.1.0-security-review-2026-10-21.md` (on its reviewer's branch at drafting),
  findings **H2** (High; the release waits on it), **L1**, **L2** and **L3**, and its helper's
  guest probes `p05_planting.py`, `p05b_no_home.py`, `p05c_reportlab_mods.py` and
  `p10_expanduser_scan.py` with their logs. reportlab 5.0.1's wheel and scikit-learn 1.9.1's sdist
  from `downloads/`, hash-checked and unpacked in a scratch folder (READ). A data-only scan of the
  frozen set's zip (EXECUTED, below).

## The problem

The README's *Safety* policy says: "code planted in a root never runs at start-up or on import in
a later call, on either binary" (README:3266-3267). reportlab breaks it (H2, EXECUTED by the
review's helper and re-run by the reviewer; re-run here as the new check, EXECUTED):

| configuration on a reused root | call 1 | call 2 |
|---|---|---|
| a read-only grant at `/tmp` (no HOME) | writes `/~/.reportlab_mods` | `import reportlab` **runs it** |
| a mount at `/tmp` (no HOME) | the same | **runs it** |
| `env={"HOME": "/home"}` | writes `/home/.reportlab_mods` | **runs it** |
| the defaults (a fresh HOME) | writes `/~/.reportlab_mods` | does not run it |

`import reportlab.rl_config` does the same with `~/.reportlab_settings` in every row.

**Why.**

- `_home_folder` (`src/wasi_python/_call.py:294-316`) makes no HOME when `/tmp` is a mount or a
  read-only grant, or when there is no root and no `/tmp` grant. The session's opening uses the
  same function (`_sessions.py:1000`). The guest then has no `HOME` variable.
- The guest has no `pwd` module, so `os.path.expanduser("~/.x")` returns `"~/.x"` unchanged. A
  relative path resolves against the working folder, `/`. With a root, `/` is the writable root;
  with a mount at `/`, it is the provider.
- reportlab 5.0.1 (READ, the pinned wheel):
  - `reportlab/__init__.py:39-45`: `import reportlab_mods`; on `ImportError`, it loads
    `~/.reportlab_mods` with `SourceFileLoader` and executes it. Only `ImportError`, `KeyError`
    and `PermissionError` are caught.
  - `reportlab/rl_config.py:26-41`: `from reportlab_settings import *`; on `ImportError`, it
    reads `~/.reportlab_settings` and executes it with `rl_exec`. `rl_config` is imported by the
    canvas, platypus and the graphics, so any real use of reportlab reaches it.
  - No environment variable turns either off. `RL_*` variables (`rl_config._setOpt`) set
    reportlab's options only after the file has run.
  - Both hooks look on the import path **first**. A module named `reportlab_mods` or
    `reportlab_settings` that imports means reportlab never reads `~` at all. Its own comment
    says such modules "can be anywhere on python path".

The planted code runs inside the sandbox, but with call 2's grants, tools and door. Call 2 may be
a trusted program with wider grants than call 1. That is the cross-run class the policy calls
enforced.

**The low findings beside it.**

- **L3.** Without a HOME, every other `~` path also lands in the root. The review found
  scikit-learn's data home there. This specification's survey (below) finds that it is code, not
  only data: scikit-learn's fetchers unpickle the cache they find there.
- **L1.** matplotlib reads `./matplotlibrc` from the working folder, `/`, the root, on every
  configuration. A planted rc can set `figure.hooks` to a callable in the zip (`sys:exit`).
- **L2.** A planted `/etc/xml/catalog` in a reused root redirects later lxml parses. README:568-569
  says the catalog is read "only if the embedder grants a folder at `/etc/xml`".

### What in the set reads a file under `~` (the survey)

A data-only scan of the frozen set's zip (EXECUTED, `uv run --no-project python -I` over
`python-stdlib.zip`, nothing imported from it): the modules whose compiled code names
`expanduser` or `~/`, read against a name that runs code. Then each candidate read in its
source (READ). Only these read a file under `~` that is not a path the program passed in:

| package | under `~` | read as | when |
|---|---|---|---|
| reportlab | `.reportlab_mods` | Python code | `import reportlab` |
| reportlab | `.reportlab_settings` | Python code | `import reportlab.rl_config` |
| pdb | `.pdbrc` | pdb commands, which run Python | when the program starts pdb |
| scikit-learn | `scikit_learn_data/*.pkz` | **pickle**, so code (`joblib.load`, `pickle.loads`; `_california_housing.py:195`, `_twenty_newsgroups.py:310`, `:564`) | when a `fetch_*` finds its cache |
| matplotlib | `.config/matplotlib/matplotlibrc`, `stylelib/` | data that names callables | at import, only when `MPLCONFIGDIR` is unset |
| reportlab | `fonts`, `.fonts`, `.local/share/fonts` | font data | font lookup |
| Pillow | `.fonts`, `.local/share/fonts` | font data | `ImageFont.truetype` by bare name |
| seaborn | `.cache/seaborn` | CSV | `load_dataset` |
| statsmodels | `statsmodels_data` | compressed CSV | `get_rdataset(cache=True)` |
| sympy | the interactive session's history | data | `init_session` |

`site` would read `~/.local`, but `site` does not run. `netrc`, `mailbox`, `trace`, `joblib`,
`pandas` and `xlrd` expand only paths the program names. **reportlab is the only package in the
set that runs a file under `~` on import.**

## Decisions

### 1. The guest always has a HOME no grant, root or mount can write (the runner)

Where the runner makes a fresh HOME today, nothing changes. Where it makes none, it now preopens
an empty, read-only folder at a guest path of the same form, `/tmp/.home-<32 hex>`, and sets
`HOME` to it.

- **The folder.** An empty folder in the call's private folder (`_Private`), beside the mounts'
  placeholder, made before the preopens and removed with the private folder. A session keeps its
  own for its life. It is preopened read-only, as a read-only grant is, so every write under it
  answers `EPERM` (`PermissionError`).
- **The guest path.** A fresh random name, as the fresh HOME's is. It never equals a grant's or a
  mount's guest path (the runner refuses two preopens at one path), it is nested inside whatever
  serves `/tmp` or `/` (wasi-libc picks the longest matching preopen, and grants and mounts
  already nest), and the guest cannot tell it from a fresh HOME by its form.
- **Always, not only where something would serve `~`.** One rule for every configuration:
  where the runner makes no fresh HOME, the guest's HOME is empty and read-only. Rejected: a
  placeholder only where a root, a mount at `/` or something at `/tmp` would serve the path. It
  saves one preopen in the default profile, but it is one more predicate to keep equal to
  wasi-libc's rule. It also leaves `~` relative in the default profile, and a relative `~` lands
  in whatever folder the program changes into: `os.chdir("/out")` into a writable grant, then
  `import reportlab`, would read `/out/~/.reportlab_mods`. A HOME that is always set is always
  absolute.
- **Nothing becomes writable.** `/tmp` itself stays unserved where it was: with no root and no
  `/tmp` grant, `tempfile` still fails and `open('/tmp/x', 'w')` is still refused. The owner's
  rule of 025 holds: by default the guest has nothing writable.
- **`env=` still wins.** A `HOME` the embedder passes is laid over the runner's, as today.

**What it closes:** both reportlab files in both no-HOME rows of H2 (a read-only grant or a mount
at `/tmp`); L3's whole class in every configuration where the runner chooses HOME (scikit-learn's
pickles, seaborn's and statsmodels' caches, the fonts, pdb's `~/.pdbrc`, matplotlib's
`~/.config`); a mount at `/`; and the `chdir` route above. It does not close the `env=` row: the
runner cannot make a HOME the embedder chose safe by choosing another.

**Why a placeholder, not an unset or a dangling HOME.** An unset HOME is today's bug. A HOME no
preopen serves would work only where neither a root nor a mount at `/` nor anything at `/tmp`
exists, which is the predicate rejected above.

### 2. reportlab's two hooks are empty modules in the zip (a recipe)

`recipes/reportlab_start_up_stand_in.py` is one module with a docstring and no code. The zip step
copies it twice, to `reportlab_mods.py` and `reportlab_settings.py` at the zip's top. reportlab
imports them from the import path before it would read `~`, so it never reads
`~/.reportlab_mods` or `~/.reportlab_settings`, whatever HOME is and whoever chose it.

- **A recipe, not a patch** (constitution §4.1). No reportlab byte changes. The stand-ins use the
  extension point reportlab documents. Nothing goes under `recipes/patches/`, and spec 020's
  sameness check sees reportlab's wheel unchanged.
- **What it closes:** H2's `env=` row for both files, and both no-HOME rows a second time,
  independently of Decision 1. With it, no package in the set runs a file under `~` on import
  (the survey), so the policy's sentence holds as written. No qualifier is added to it.
- **What it costs.**
  - It is build-class: the zip is rebuilt with two more members (a few hundred bytes compiled).
    The snapshot is rebuilt with it (INFERRED: the snapshot is built over the zip).
  - It takes the wave's build-class slot, and the builder dispatches the release workflow on the
    branch, as every build does.
  - What an embedder loses: a `reportlab_mods` or `reportlab_settings` of its own on
    `import_path` is shadowed, since the zip comes first on `sys.path`. reportlab's options stay
    reachable through `RL_*` environment variables (`env=`) and through `reportlab.rl_config` in
    the program. The README says so.
- **Rejected.**
  - **Only documenting the `env=` row** beside pdb. A bare import is a far wider trigger than
    starting pdb. The README itself advises "pass `HOME` in `env=` if you need one"
    (README:1250, 1474). And the finding's own check asks that call 2 not run the file under
    `env=` either.
  - **A runner refusal or warning** when `env=` points `HOME` into a writable root or grant. The
    runner cannot tell a reused root from one the embedder trusts. A writable grant kept for one
    trusted agent is a fair HOME (the README's state example is such a grant). A warning on
    every such call is noise. And neither would help a HOME in a writable mount.
  - **A patch to reportlab** that drops the two reads. §4.1 asks for a recipe first, and one
    exists.

### 3. What stays documented, not fixed

These go in *Not protected*, beside pdb's `.pdbrc`:

- **An `env=` HOME into a reused root, or into a writable grant or mount a later call reuses:**
  pdb's `~/.pdbrc` (when the program starts pdb), scikit-learn's pickled caches in
  `~/scikit_learn_data` (code, when a `fetch_*` runs; `SCIKIT_LEARN_DATA` too), matplotlib's
  `~/.config/matplotlib/matplotlibrc` when `MPLCONFIGDIR` is unset, and data (`zoneinfo`'s
  files, as today). reportlab is named there as reading neither of its start-up files.
- **L1, `./matplotlibrc` in the working folder.** It is data that picks a callable from the
  zip, not new code; the reviewer ranked it Low and offered the README. Dropping matplotlib's
  lookup of the working folder would be a patch to matplotlib's source (`matplotlib_fname`), and
  §4.1 allows a patch only when it cannot be avoided.
- **L2, `/etc/xml/catalog`.** libxml2's default catalog is compiled in. In a reused root it is
  data a later call reads. Fixing README:568-569 is the finding's own fix.

### 4. The checks first

Three new check functions in `tests/checks/test_v1_2_hostile_guest.py`, beside the `.pdbrc`
check, 14 rows (EXECUTED on main's code: 12 fail, 2 pass):

- `test_a_planted_reportlab_start_up_file_never_runs[configuration-name]`: both files, under a
  read-only grant at `/tmp`, a mount at `/tmp`, `env={"HOME": "/home"}` inside the root, and a
  fresh HOME. Call 1 plants the file at `/~`, `/home` and its own HOME where it can write one,
  and the check asserts the plant reached the root, so it cannot pass on a call that wrote
  nothing. Call 2 imports `reportlab` (or `reportlab.rl_config`) and must print only `imported`
  and make no marker file. On main: the six no-HOME and `env=` rows fail ("PLANTED RAN"); the
  two fresh-HOME rows pass, as guards. Decision 1 alone turns four of the six; Decision 2 turns
  all six.
- `test_reportlab_start_up_hooks_are_the_zips_empty_modules`: both stand-ins import from the
  zip, define no public name, and leave `rl_config`'s defaults unchanged. On main:
  `ModuleNotFoundError`.
- `test_where_the_runner_makes_no_fresh_home_the_home_is_empty_and_read_only[configuration]`:
  no root; a root with a read-only grant at `/tmp`; a root with a mount at `/tmp`; a mount at
  `/`; a session with a root and a read-only grant at `/tmp`. Each guest has a `HOME` of the
  runner's form, `~` expands, the folder is empty and a write under it is `PermissionError`, and
  where there is a root, a file call 1 planted at `/~/planted` is not seen through `~` and
  nothing new appears in the root. On main: all five fail (`"home": false`; with a root,
  `"planted": true`).

The checks run on the default binary only. Neither decision depends on the binary: HOME and the
preopens are set the same way for both, and the snapshot pre-imports no package.

### 5. The existing checks Decision 1 changes (a judge change, with its reason)

These encode "no HOME" and change in the build commit with the fix, each named in the claim
list. The reason, in each: the guest now always has a HOME, empty and read-only where the runner
makes no fresh one.

- `test_v1_2_hostile_guest.py::test_nothing_is_writable_by_default[plain]` and `[snapshot]`: the
  word `no HOME` becomes `HOME`; every refusal stays.
- `test_v1_4_embedding.py::test_no_root_and_no_grants_runs`: `None` becomes a `/tmp/.home-` path.
- `test_v1_4_embedding.py::test_a_mount_at_the_root[plain]` and `[snapshot]`: `"home": None`
  becomes the runner's form; its start-up bound of provider calls must still hold (the
  placeholder is not the provider's).
- `test_v1_4_embedding.py::test_a_mount_at_tmp_means_no_home`: **retired**. Its claim is reversed,
  and the new check's `mount at /tmp` rows hold what replaces it.
- `test_v1_3_default_profile.py::test_seaborn_takes_its_scipy_paths[*]`: `FileNotFoundError '~'`
  becomes the placeholder's refusal (INFERRED `PermissionError` naming a path under the HOME;
  the builder records what it sees). The assertion that no `~` folder appears in the grant
  stays.
- `test_v1_3_default_profile.py::test_scikit_learn_says_what_it_lacks`: the fetch row's
  `["FileNotFoundError", "~"]` becomes the placeholder's refusal, matched by the HOME's prefix,
  since the name is random.

The builder greps `tests/` again at build for any other check that reads `HOME` and lists what it
finds. Fuel: a call with the placeholder carries one more preopen and one more environment
variable. Every row of the default profile may grow by a little (INFERRED: within the gather's
1e-4; the builder measures it on `-c pass`, both binaries, and names any GREW line).

### 6. The shape of the change (not structural)

- **One helper owns HOME.** The choice (fresh, or the placeholder) and the fresh folder's
  `mkdir` move into one function in `_call.py`, called by the call and by the session's
  opening. Today both bodies carry their own copy of the fresh HOME's `mkdir` block. Neither `_instance` nor
  `_open_session` grows, and both should shrink. No new function passes 80 lines.
- **No new state.** The placeholder is a path in the call's or session's own private folder,
  which already holds the mounts' placeholder. No module-level mutable, no lock, no
  `sys.platform` branch (the fresh HOME's `dir_fd` route stays in `_platform`), no test seam.
  `_call.py` stays under 1,500 lines (1,289 today).
- **The filesystem table.** The placeholder is one more read-only `_Preopen` in the call's list,
  passed to wasmtime like a grant. Under a writable mount at `/tmp` or `/`, the table forwards its
  paths to wasmtime, as it does for a grant nested in a mount.

## Intent

A planted file in a reused root never runs when a later call imports reportlab, whatever HOME
that call has. Where the runner chooses HOME, `~` never reaches a root, a grant or a mount. Where
the embedder chooses it, the README says what that HOME can carry into a later call.

## Design

- `src/wasi_python/_call.py`: `_home_folder` is joined by one function that returns the guest's
  HOME path and, where the runner makes no fresh one, the placeholder to preopen. `_call_deferred`
  and `_instance` use it; the `fresh` environment line always has a HOME. `BASE_ENV`'s comment
  says the new rule.
- `src/wasi_python/_sessions.py`: `_open_session` uses the same function in place of its copy.
- `src/wasi_python/runner.py`: the `env` argument's docstring in `run`, `run_async` and
  `Session` says "a HOME made fresh where /tmp is writable, else an empty read-only one". The
  README's generated API reference follows.
- `recipes/reportlab_start_up_stand_in.py`: a docstring that says in words why the module is
  empty, and no code.
- `scripts/steps/70_zip.sh`: two `--file` lines beside the other stand-ins, mapping that file to
  `reportlab_mods.py` and `reportlab_settings.py`; its comment on reportlab says why.

### The README lines

- **seaborn and reportlab** (README ~2340): a new item: reportlab reads neither of its start-up
  files, `~/.reportlab_mods` and `~/.reportlab_settings`. The zip carries empty
  `reportlab_mods` and `reportlab_settings` modules, which reportlab finds first. Set its
  options with `RL_*` variables in `env=`, or through `reportlab.rl_config` in the program. The
  seaborn item's "no `HOME`" sentences (2346-2354) say what the read-only HOME gives instead.
- **scikit-learn** (293-296) and **statsmodels** (341-344): "there is no `HOME`" becomes "the
  `HOME` is read-only", with the error the build records.
- **By default** (893-894): "no `/`, no `/tmp` and no `HOME`" becomes "no `/`, no `/tmp`, and a
  `HOME` it cannot write".
- **Grants** (999-1002): "with neither, there is no `HOME`" becomes "with neither, `HOME` is an
  empty, read-only folder the runner owns, so `~` never names a folder of the root".
- **Mounts** (1249-1250 and 1473-1475): "makes no `HOME` in a mount" becomes "makes no writable
  `HOME` in a mount: a mount at `/tmp` gives the empty, read-only HOME a read-only grant there
  gives; pass `HOME` in `env=` if you need a writable one, at a folder no untrusted call writes
  (see *Not protected*)".
- **lxml, Catalogs** (568-569): read if the embedder grants a folder at `/etc/xml`, if a root
  holds `/etc/xml/catalog`, or if `XML_CATALOG_FILES` is set. A catalog planted in a reused root
  steers later parses (see *Not protected*).
- **Safety, defaults** (3305-3309): "(no `HOME` where there is none)" becomes "(where the guest
  sees no writable `/tmp`, an empty, read-only `HOME` in the call's private folder)".
- **Not protected**, the reused-root data list (3445-3448): add matplotlib's `./matplotlibrc` in
  the working folder, `/`, which can name a callable from the zip (`figure.hooks`), and libxml2's
  `/etc/xml/catalog`.
- **Not protected**, the `env=` item (3463-3465): "an `env=` that overrides `HOME` or
  `PYTHONTZPATH` on a reused root, or into a writable grant or mount a later call reuses (pdb
  then reads a `.pdbrc`, scikit-learn's `fetch_*` unpickle what they find in
  `~/scikit_learn_data`, matplotlib reads `~/.config/matplotlib/matplotlibrc` unless
  `MPLCONFIGDIR` is set, and `zoneinfo` a zone file, that a guest may have planted there;
  reportlab reads neither of its start-up files)".

### The CHANGELOG line

Under the one unreleased section:

> **HOME is never the root** (spec 114; the 0.1.0 security review's H2, L1, L2 and L3). Where
> the runner makes no fresh HOME (no root, a read-only grant or a mount at `/tmp`, a mount at
> `/`), the guest's `HOME` is now an empty, read-only folder of the call's own, so `~` never
> falls back to the working folder, a writable root. Before, a reused root let one call plant
> `~/.reportlab_mods` or `~/.reportlab_settings` and a later call's bare `import reportlab` ran
> it. The stdlib zip also carries empty `reportlab_mods` and `reportlab_settings` modules, which
> reportlab imports before it would read either file, so it reads neither, whatever HOME the
> embedder passes. A `reportlab_mods` of the embedder's own on `import_path` is now shadowed; use
> `RL_*` variables. The README names what an `env=` HOME in a reused root still carries (pdb's
> `.pdbrc`, scikit-learn's pickled caches), matplotlib's `./matplotlibrc` and a planted
> `/etc/xml/catalog`.

### The roadmap line

> Reserved: 114 (HOME is never the root: where the runner makes no fresh HOME, an empty
> read-only one, so `~` never falls back to a writable root; reportlab's two start-up hooks as
> empty modules in the zip, a recipe; the README's reused-root list gains `./matplotlibrc` and
> `/etc/xml/catalog`; the 0.1.0 security review's H2, L1, L2, L3; build-class, runner code,
> reviewed before build; before 0.1.0, which waits on H2).

## Scope

In: Decisions 1 to 6, the README lines, the CHANGELOG line, the roadmap line. Out:

- A fix for L1 or L2 in the packages themselves (Decision 3).
- Any refusal or warning about an `env=` HOME (Decision 2, rejected).
- The module cache's own findings (spec 113).

## Acceptance criteria

1. **The new checks pass.** All 14 rows of the three new functions pass on the rebuilt set, on
   macOS and Linux locally or in CI, and on Windows in the release workflow.
2. **The guest always has a HOME.** In every call and session, `HOME` is set: the fresh folder
   where `/tmp` is writable, as today, else an empty, read-only folder of the runner's
   `/tmp/.home-<32 hex>` form. A write under it is `PermissionError`. An `env=` HOME still
   replaces it.
3. **Nothing becomes writable.** `test_nothing_is_writable_by_default` keeps every refusal it
   has today, `/tmp/x` included.
4. **The placeholder leaves nothing.** It lives in the call's or session's private folder and
   goes with it. The litter and removal checks stay green, and a call with a read-only grant at
   `/tmp` leaves that grant's folder unchanged.
5. **reportlab reads no start-up file.** The zip carries exactly two new members, from one
   recipe file, and nothing else in the zip changes. No reportlab byte changes. Spec 020's
   sameness check passes with no new patch.
6. **The judge changes are exactly those listed** in Decision 5, plus any the build's grep finds,
   each named in the claim list with its reason. `test_a_mount_at_tmp_means_no_home` is retired.
7. **Not structural.** No function on `LONG_FUNCTIONS` grows, and none joins it. One helper
   chooses HOME for the call and the session. The rules checks of specs 103 to 109 stay green.
8. **The README and CHANGELOG** carry the lines above. The README's API reference matches the
   docstrings (its rules check stays green).
9. **Growth is named.** Any fuel growth (the placeholder's preopen and variable, measured on
   `-c pass`, both binaries) and the zip's bytes (and the snapshot's, if it grows) are GREW
   lines with reasons in "For the lane". No pass is lost.
10. **Code speaks for itself.** No code file the change touches names a specification, review,
    finding or `context/` path (the rules checks of 107 and 109).
11. **The run.** ruff check, ruff format --check and the fast tier are green. The release workflow
    is dispatched on the branch and read: every red line is a GREW line or G7, the Windows legs
    green.

## For the lane

- **Wave kind: build-class** (a recipe and the zip step), with runner code. It may share a wave
  with 113 if 113 is not build-class; else the lane orders them.
- **The claim list** (to be completed at build with measured numbers):
  - new: the 14 rows of Decision 4;
  - changed: the rows of Decision 5;
  - retired: `test_v1_4_embedding.py::test_a_mount_at_tmp_means_no_home`;
  - grown: the zip's bytes, the snapshot's if it grows, and start-up fuel where the build
    measures it.
- **Flags:** `--accept "114: HOME is never the root"`, `--accept-judge "114: the guest always
  has a HOME; checks that encoded none now read the empty read-only one"`, and
  `--accept-growth` with the measured reasons.

## One line

Where the runner makes no fresh HOME, the guest now gets an empty one it cannot write, so `~`
never falls back to a writable root; and the zip's empty `reportlab_mods` and
`reportlab_settings` mean reportlab never runs a start-up file from any HOME.

## Landing notes

Not built yet. Written by the builder at drafting, 2026-10-21, on
`spec/114-home-is-never-the-root` from main `1875d4cd`: the specification, its roadmap line and
the three new check functions, run by node id against the main tree's frozen set (`SHA256SUMS`
`d0d91cef`) on main's code: 12 rows FAIL for the reasons Decision 4 gives, the 2 fresh-HOME rows
pass (EXECUTED, `build/114/checks-on-main.log`). The fix waits on the pre-build review.
