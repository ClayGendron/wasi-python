# 079 — The build runs only the pinned host Python

- **Status:** drafted 2026-10-19 on `spec/079-the-build-runs-only-the-pinned-host-python` from
  main `23f1c4f` (`abf1817`). **Revised 2026-10-19 against its pre-build review** (written in the
  scratchpad, `079-review/079-the-build-runs-only-the-pinned-host-python-spec-2026-10-19.md`, with
  its probes beside it, to be copied to `../reviews/` by the lane; verdict: "ready once F1 to
  F3"). All six findings are taken; "Disposition of the pre-build review" says where each went.
  Awaiting the reviewer's confirmation. Not built. Main's tip is still `23f1c4f`, so the rebase
  before this revision was empty.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** build-class: the build driver and two steps. It changes `scripts/build.sh` (a
  refusing stand-in for every Python name the caller's `PATH` holds and a fixed list besides, on
  the `PATH` each step inherits; a step that ran one fails), `scripts/steps/common.sh` (the shim
  folder first on `PATH`), `scripts/steps/10_tools.sh` (writes the shim, gates it, and names what
  stands behind it), and adds `scripts/refuse-python` (the stand-in). It changes
  `tests/harness/scan.py`, `tests/checks/test_v1_5_rebuild_from_pins.py` (one check added),
  `tests/unit/test_scan.py`, `tests/unit/test_build_progress.py` (the fake tree copies the new
  file; four cases added), `README.md` and `CHANGELOG.md`. It changes no file under `recipes/`
  (Decision 3 says why no cross file changes), no pin, no `downloads/SHA256SUMS` line, no source
  tree, no carried patch, no `src/` file and no workflow. The artifacts are expected to be the
  same bytes; `MANIFEST` changes in exactly its `recipe` lines for the four files above, and so
  `SHA256SUMS` changes in exactly `MANIFEST`'s line (Decision 7). It changes no line of
  `tests/public_api.txt`.
- **Depends on:** 023 (matplotlib M1: steps 37 and 55, where the unpinned interpreter runs),
  059 (whose landing notes named it), 020 (`MANIFEST`'s recipe lines), 012 and 040 (the same
  bytes from every host, the same-bytes job), 003 (the step layout and `common.sh`). All are
  landed. Spec 037 (scipy) is being built at the same time and edits four of the files this one
  edits; Decision 9 says how the two meet.
- **Research it stands on:**
  - The 0.1.0a6 security review, finding F2
    (`../reviews/0.1.0a6-security-review-2026-10-18.md`): FreeType's meson resolves
    `find_program('python3')` to the host's interpreter, and HarfBuzz runs `gen-hb-version.py`
    through its `#!/usr/bin/env python3` line. Its suggested fix is the one taken here, widened.
  - Spec 059's landing notes (Criterion 1): the first arm64 container run stopped at step 37 with
    `gen-hb-version.py … failed with status 127`, because the research image had no `python3`.
  - A census run while drafting this specification, in this branch's worktree
    (`build/079/`, git-ignored; each run's output file is named in Decision 2). It read the main
    tree's step logs, meson logs, `build.ninja` files, `.ninja_log` files and CPython's two
    `config.log` files (READ), and ran single steps of today's recipe with a refusing stand-in
    first on `PATH` and then with a prototype of Decision 3's shim ahead of it (EXECUTED). Every
    fact in Decisions 2 and 3 is labelled. The builder repeats the ones criterion 1 names.
  - This specification's pre-build review and its probes (the scratchpad's `079-review/probes/`).
    EXECUTED there:
    - the stand-in's log is lost under `env -i PATH="$PATH"`, which steps 35 and 36 use (p3b);
    - with the fixed list first on `PATH`, `python3-intel64`, `python3.7m`, four
      `python3*-config` scripts and `python-build` still reach this machine's own interpreters
      (p3a);
    - an independent prototype of Decisions 3 to 5 ran steps 10, 30 and 37 through `build.sh` and
      gave the main tree's bytes, from another checkout path (p2).

    READ there: every `build.ninja` command's first word in the main tree and in 037's tree
    (p1); the absolute Python paths in the records and the absolute Python shebangs in the source
    trees (Decision 2 f).

## The problem

Constitution §4.2: every tool is pinned, and a build that runs anything unpinned is not a build.
The build pins one host Python per build host: python-build-standalone's CPython 3.15.0, unpacked
by step 10 to `build/tools/python/` and named `$HOSTPY` in `scripts/steps/common.sh`. Every step
script calls it by that path. That part holds.

But `common.sh` builds each step's `PATH` as `build/tools/pylib/bin`, then wasmtime's folder, then
the caller's `PATH`. Neither folder holds a `python3`. So any tool that looks up `python3` **by
name** gets the build host's own interpreter, whatever it is. Three upstream builds do exactly
that, and CPython's configure probes for one too. On this machine the interpreter they found was
`/Library/Frameworks/Python.framework/Versions/3.10/bin/python3` (Python 3.10.4) and
`~/.local/bin/python3.14`. On a GitHub runner it is the image's `python3`. In a container without
one, the build stops (spec 059).

What those interpreters write is not trivial. They choose the FreeType modules compiled in
(`ftmodule.h`), write FreeType's options header (`ftoption.h`), generate HarfBuzz's amalgamated
sources, and write matplotlib's shipped `matplotlibrc`. Three hosts with three different
`python3`s already agree byte for byte, so nothing is wrong in the bytes today. The rule is
broken all the same, and the build depends on a tool nobody pinned, printed, or listed.

## Decisions

1. **What counts as a pinned interpreter.** Exactly three Pythons may run during a build:
   - `$HOSTPY`, the pinned python-build-standalone CPython (`build/tools/python/bin/python3`);
   - the build-Python that step 20 compiles from the pinned CPython tarball
     (`build/Python-3.15.0/cross-build/<build triple>/python.exe` or `python`), which
     `scripts/python-wasi-cross` runs for meson's introspection and which CPython's cross build
     uses as `--with-build-python`;
   - the WASI `python.wasm` under the pinned wasmtime, which CPython's cross Makefile runs as
     `PYTHON_FOR_BUILD`.
   No Python found on the caller's `PATH` or at a fixed system path may run. "The pinned host
   Python" in this specification means the first one; the other two are built from pins.

2. **The census: every place an unpinned interpreter is reached today.** Four places, two more
   than the review found. A fifth surface was checked and is clean, and a sixth, calls by
   absolute path, is reached nowhere today.
   - **(a) FreeType's meson** (step 37). `meson.build:38` is `python_exe =
     find_program('python3')`. The cross file names no `python3`, so meson takes `PATH`'s.
     - READ, main tree: `freetype-build/meson-logs/meson-log.txt:112` `Program python3 found: YES
       (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)`.
     - At configure it runs `extract_libtool_version.py` twice and `parse_modules_cfg.py` three
       times (the same log, lines 113 to 161).
     - At build, `build.ninja:42` runs `parse_modules_cfg.py --format=ftmodule.h` and line 46 runs
       `process_ftoption_h.py`; `.ninja_log` shows both outputs built. Line 258
       (`generate_reference_docs.py`) is not a default target and did not run.
     - EXECUTED (`e2-step-37-main-refused.out`): today's step 37 with a refusing stand-in first
       on `PATH` stops at `freetype-2.14.3/meson.build:40:17: ERROR: Command
       \`…/refuse/python3 …/extract_libtool_version.py --soversion …\` failed with status 97`.
   - **(b) HarfBuzz's generators** (step 37). Their files carry `#!/usr/bin/env python3` and the
     executable bit. The pinned meson 1.12.1 runs an executable file directly and parses the
     shebang only of a file that is not executable (READ, `mesonbuild/programs.py:282-292`; its
     lines 262-265 put meson's own interpreter in place of `python3` for that second kind). So
     the kernel runs `env`, and `env` searches `PATH`.
     - READ, main tree: `harfbuzz-build/meson-logs/meson-log.txt:909-911` runs
       `gen-hb-version.py` at configure (it writes `hb-version.h`).
     - READ, main tree: `.ninja_log` shows `src/harfbuzz.cc` (`gen-harfbuzzcc.py`),
       `src/harfbuzz-world.cc` (`gen-harfbuzz-world.py`) and the eight `src/hb-gpu-*.hh`
       (`gen-gpu-shader-artifacts.py`) built. Each `build.ninja` command's first word is the
       script itself. The review named only the first of these.
     - `gen-def.py` is found but not built; `relative_to.py` is behind a branch not taken (no
       "Running command" line).
   - **(c) matplotlib's `tools/generate_matplotlibrc.py`** (step 55). Executable, with
     `#!/usr/bin/env python3`; `lib/matplotlib/mpl-data/meson.build:3` finds it by path, so the
     same route as (b). It writes `mpl-data/matplotlibrc`, which ships. The review did not name
     it.
     - EXECUTED (`e6-step-55-main-refused.out`): today's step 55 with the refusing stand-in
       stops with `FAILED: [code=97] lib/matplotlib/mpl-data/matplotlibrc`.
     - matplotlib's own `find_program('python3', 'python')` is answered by the cross file's
       `python` entry, `scripts/python-wasi-cross` (READ: `matplotlib-build/…/meson-log.txt:182`),
       because meson tries every name in the machine file before `PATH`.
   - **(d) CPython's configure for the native build-Python** (step 20). `configure.ac:207`
     is `AC_CHECK_PROGS([PYTHON_FOR_REGEN], [python$PACKAGE_VERSION python3.15 python3.14 …
     python3.10 python3 python], [python3])`.
     - READ, main tree: `cross-build/aarch64-apple-darwin/config.log:83-89` found
       `/Users/claygendron/.local/bin/python3.14` and ran it as `python3.14 -V` ("Python
       3.14.2"). Its Makefile records `PYTHON_FOR_REGEN?=python3.14`.
     - READ: in that Makefile, `$(PYTHON_FOR_REGEN)` appears only in `regen-*`, `clinic` and
       check recipes, which `make all` does not run. So it is probed and run once for its
       version, and generates nothing. The WASI configure's probe finds the build-Python
       (`--with-build-python`), as Decision 1 allows.
     - EXECUTED (`e4-step-20-main-refused.out`): today's step 20 with the refusing stand-in
       **passes**, and the stand-in's log holds two lines, `…/refuse/python3.15 -V`. configure
       sends the probe's stderr to the void and carries on. A refusal can be swallowed, so a
       refusal alone does not fail a step; Decision 4's log rule does.
   - **(e) Clean: every other step.** EXECUTED (`e8-steps-10-30-main-refused.out`,
     `e9-steps-35-54-main-refused.out`, `e10-steps-60-90-main-refused.out`): steps 10, 30, 35,
     36, 40, 50, 53, 54, 60, 70, 80 and 90 of today's recipe pass with the refusing stand-in
     first on `PATH`, and its log stays empty. READ, why: the scripts call `"$HOSTPY"` by path;
     the tool entry points under `build/tools/pylib/bin` (`meson`, `cython`, `pkgconf`,
     `versioneer`) carry `uv`'s absolute shebang to `$HOSTPY`; numpy, pandas and SheenBidi run
     their non-executable scripts through meson's own interpreter (`meson-log.txt` "Running
     command: …/build/tools/python/bin/python3 …"); numpy's four `env PYTHONPATH=…
     …/scripts/python-wasi-cross -m code_generators.…` commands run the build-Python
     (`numpy-build/build.ninja:114,118,122,126`); numpy's and pandas' `find_program` for Python
     answers with `scripts/python-wasi-cross`; zlib's, xz's, libxml2's (`--without-python`) and
     libxslt's configures probe no Python (READ, their `config.log`); SQLite and bzip2 are
     compiled directly. Step 00 runs `curl` and `shasum` only (READ).
   - **(f) Calls by absolute path: none today.** A call such as `/usr/bin/python3 x.py`, or a run
     script whose line is `#!/usr/bin/python3`, bypasses every name on `PATH`, so neither the
     shim nor the stand-in sees it. Two READ facts (the review's grep):
     - no `build.ninja`, `Makefile`, `config.status`, `libtool`, `config.log` or `meson-log.txt`
       in the main tree names an absolute host Python other than FreeType's, which is (a).
       `config.log`'s `PATH:` lines and CPython's `sed` over `idle3` and `pydoc3` are the other
       matches, and none of them runs a Python;
     - the absolute Python shebangs in the source trees sit only in files no step runs:
       CPython's `Tools/gdb`, `Tools/build/generate_slots.py` and generated `python-config`;
       numpy's tests; Pillow's fuzzers; lxml's docs; libxslt's `setup.py.in`.

     The judge reads absolute paths where meson and configure record them (Decision 6). A `make`
     recipe line it does not read. **The proof for this route is Decision 8:** a container with no
     Python on disk outside the clone, where an absolute call fails, or is swallowed and then
     shows as different bytes.
   - **Outside the build, not changed:** the release workflow's same-bytes job runs `python3 -`
     to print which zip entries differ when two wheels differ (`.github/workflows/release.yml`,
     the wheel comparison). It runs after the build, only on a failure, and writes no artifact.
     It is the runner's tool, like `sha256sum` beside it, and is out of scope. So is the wheel
     build after `scripts/build.sh` (Scope).

3. **The mechanism: a shim folder first on `PATH`.** Step 10, right after it unpacks the host
   Python and checks `$HOSTPY`, writes `build/tools/host-python/` holding three files, `python`,
   `python3` and `python3.15` (the last named from `scripts/line.conf`'s `PYTHON_VERSION`, cut to
   major and minor), each mode 755 and exactly:

   ```sh
   #!/bin/sh
   exec "<the absolute path of $HOSTPY>" "$@"
   ```

   `common.sh` puts the folder first: `PATH="$T/host-python:$T/pylib/bin:$T/$WASMTIME_DIR:$PATH"`.
   Every way a step finds a Python by name searches `PATH`, so every one of them now finds the
   pinned one: meson's `find_program` after the machine file (a), `env python3` in a shebang (b,
   c), configure's `AC_CHECK_PROGS` (d).
   - **Why `python3.15` and `python`.** CPython's configure tries `python3.15` first; with the shim
     holding it, configure stops at the pinned interpreter and never reaches an older name.
     `python` answers matplotlib's second name and the common `AM_PATH_PYTHON` lists. A step that
     asks for any other Python name the host has, or one of Decision 4's fixed list, meets the
     stand-in.
   - **Why three names and not `build/tools/python/bin` on `PATH`.** That folder also holds
     `pip`, `pip3`, `idle3`, `pydoc3` and the `-config` scripts (the review's N1, READ). The shim
     offers the interpreter and nothing else.
   - **Why a script and not a symlink.** `exec` hands over the pinned binary's own path, so its
     `sys.executable` and its prefix are the pinned ones however the interpreter treats links.
     EXECUTED: `PATH=build/tools/host-python:$PATH env python3 -c 'import sys;
     print(sys.executable, sys.prefix, sys.version.split()[0])'` printed
     `…/build/tools/python/bin/python3 …/build/tools/python 3.15.0`. A checkout path holding `"`,
     `$` or a backtick would break the `exec` line; Decision 5's `sys.prefix` probe stops the
     build in one line if it does (the review's N3).
   - **Why not a meson machine-file entry.** A `python3 = …` line in `recipes/wasi-plot-libs.cross`
     would fix (a) alone. It cannot reach (b) and (c), which the kernel resolves, nor (d), which is
     configure. One mechanism covers all four, and one check proves it. So no cross file changes.
   - **Why not rewriting the shebangs.** It would edit upstream source trees: §7 forbids a hand
     edit in `build/`, and §4.1 would make each a carried patch for a problem that is ours.
   - **The prototype worked and changed no byte.** EXECUTED, with the three files written by
     hand into this worktree's `build/tools/host-python/` and the folder put ahead of the
     refusing stand-in on the caller's `PATH` (so ahead of everything `common.sh` adds except
     `pylib/bin` and wasmtime's folder, which hold no Python):
     - step 37 (`e3-step-37-shim-refused.out`) passed with no refusal;
       `freetype-build/meson-logs/meson-log.txt:112` named `…/build/tools/host-python/python3`,
       and so did `build.ninja`'s three FreeType commands. `libfreetype.a` `2d2816e1…`,
       `libharfbuzz.a` `aae412e9…`, `libSheenBidi.a`, `libraqm.a`, `libqhull_r.a`, `ftoption.h`,
       `ftmodule.h`, `hb-version.h`, `harfbuzz.cc`, `harfbuzz-world.cc` and
       `hb-gpu-fragment-glsl.hh` each equal the main tree's (built with the host's 3.10) byte for
       byte. The review's own prototype repeated steps 10, 30 and 37 through `build.sh` from
       another checkout path and got the same bytes (p2);
     - step 20 (`e5-step-20-shim-refused.out`) passed with no refusal; configure `found
       …/build/tools/host-python/python3.15`, "Python 3.15.0". Its intermediate `python.wasm` was
       `f5663cd8…` with the refusing stand-in and with the shim alike (it holds this worktree's
       path, so it is compared only within this worktree);
     - step 55 (`e7-step-55-shim-refused.out`) passed with no refusal; `matplotlibrc`
       `8e8ff661…` and all 12 extension archives equal the main tree's;
     - steps 60, 70, 80 and 90 then completed a set from this worktree in which every Python was
       pinned: **its `SHA256SUMS` is `14ada22ab85623c5`, byte-identical to the main tree's**
       (`cmp`; spec 071's landing hash). No recipe file had changed yet, so `MANIFEST` was equal
       too.

4. **Fail closed: a refusing stand-in behind the shim, in every build.** Without it, a lost
   `PATH` line or a step that asks for a name the shim lacks falls back silently to the host's
   interpreter, which is today's defect. So `scripts/build.sh`, after its preflight and before
   its first step, and only when it builds (not for `--list`, `--check` or `--help`), does three
   things.
   - **It makes `build/no-host-python/` afresh** and fills it with one symbolic link to
     `scripts/refuse-python` for each of these names (the review's F2):
     - every name, on any folder of the caller's `PATH`, of an executable file matching
       `python*`, `pypy*`, `pip*`, `pydoc*` or `idle*`. The `PATH` is split on `:` alone, so a
       folder holding spaces is read whole. Folders under the repository's own `build/` are
       skipped;
     - the fixed list besides, for names the host lacks: `python`, `python2`, `python2.7`,
       `python3` and `python3.0` to `python3.20`.

     So shadowing follows what the host has, not a guess. On the drafting machine that adds
     `python3-intel64`, `python3.7m`, `python3-config`, `python3.10-config`, `python3.13-config`,
     `python3.7m-config` and `python-build` to the list (the review's p3a).
   - **It exports `PATH="$HERE/build/no-host-python:$PATH"`.**
   - **It removes `build/logs/unpinned-python.log` before each step.** When a step exits 0 but
     the log exists, it records the step as `error` and prints its usual failure line. So a refusal
     the step swallowed (as configure swallows `-V`, Decision 2 d) still stops the build. The
     step's log ends with one line, `ERROR: <step> ran an unpinned Python
     (build/logs/unpinned-python.log)`.

   **`scripts/refuse-python` finds its log from its own location, never from the environment**
   (the review's F1). Steps 35 and 36 run configure and make through `env -i PATH="$PATH" …`
   (`35_stdlib_libs.sh:13`, `36_xml_libs.sh:20`), and `apply_patches.sh:34` runs `git` so. That
   keeps `PATH` and drops every other variable, so a log path passed in a variable would be lost
   exactly where a swallowed configure probe is likeliest (EXECUTED by the review, p3b). So:
   - when the folder holding the link it was run through (`dirname "$0"`) is named
     `no-host-python`, it appends `$0` and its arguments, one line, to that folder's
     `../logs/unpinned-python.log`, which is `build/logs/unpinned-python.log`;
   - it writes `ERROR: an unpinned <name> was run; a build step runs only build/tools/host-python's
     Python (spec 079)` to stderr;
   - it exits 1.

   No variable is read or exported for it.

   `common.sh` prepends the shim ahead of the stand-in folder. So `python`, `python3` and
   `python3.15` reach the pinned interpreter, and every other shadowed name refuses. Before step
   10 writes the shim (step 00, and step 10 up to that point), every shadowed name refuses. That
   holds today's facts: step 00 and step 10 run no Python by name (Decision 2 e).
   A step script run by hand, outside `build.sh`, still gets the shim from `common.sh`, without
   the stand-in; the README says so, and step 10's gate line shows it (Decision 5).

5. **Step 10 gates the shim and names what stands behind it** (the review's "print `python3
   --version`", and the pre-build review's F4). Right after writing the three files, step 10
   stops in one line unless each holds:
   - `command -v python`, `command -v python3` and `command -v python3.15` each print the file
     of that name in `build/tools/host-python/`;
   - `/usr/bin/env python3 -c 'import sys; print(sys.prefix)'`, the route a shebang takes,
     prints `build/tools/python`'s absolute path.

   Then it prints one line:

   `host python: python3 is build/tools/host-python/python3, Python 3.15.0, prefix
   build/tools/python; behind it python2 is <what command -v python2 prints, or none>`

   Under `scripts/build.sh` the last part reads `build/no-host-python/python2`; `python2` is
   always on the fixed list and never a shim name. Run by hand it reads whatever the host has, or
   `none`. Step 10 does not stop on that part; the judge requires it (Decision 6). No step
   script runs a bare `python3`: the gate uses `command -v`, `/usr/bin/env` and `"$HOSTPY"` for
   the version. `test_build_scripts_call_python_only_through_uv_or_a_path` already allows all
   three (`BARE_PY` matches a bare `python3` after `$(`, the review's N2).

6. **The judge: `test_every_build_python_is_pinned`** in
   `tests/checks/test_v1_5_rebuild_from_pins.py`, with its scanning in `tests/harness/scan.py`.
   - **Recipe part** (no build needed). It requires each of these:
     - `common.sh`'s `PATH` line starts with `$T/host-python`;
     - step 10 writes the three names, runs Decision 5's gate (`command -v`, `/usr/bin/env
       python3`, `sys.prefix`) and prints the gate line with its `behind it` part;
     - `build.sh` makes `build/no-host-python`, shadows the five globs (`python*`, `pypy*`,
       `pip*`, `pydoc*`, `idle*`) over the caller's `PATH` and the fixed list, links them to
       `scripts/refuse-python`, puts the folder on `PATH`, and fails a step that left the log;
     - `scripts/refuse-python` exists, derives its log from `dirname "$0"`, names
       `unpinned-python.log`, reads no variable for it, and exits non-zero.
   - **Record part** (needs `compile records`, the meson records spec 059's need already names).
     The allowed interpreters are:
     - the three files of `build/tools/host-python/`;
     - `build/tools/python/bin/python3*`;
     - `scripts/python-wasi-cross`;
     - the build-Python under `build/Python-*/cross-build/*/`.

     A *Python name* is a basename matching one of the five globs. Every command is read by its
     **program word**, found this way (the review's F3):
     - Start at the first word. While it is `env`, skip it, its flags and its `NAME=value` words,
       and read the next. `env` with `-i`, `-S`, `-u PATH` or a `PATH=` word is a breach, because
       the program would not search the step's `PATH`.
     - A program word that is meson with `--internal exe` is read on: `--unpickle` is a hit, since
       the command is hidden in a file; otherwise the word after `--` is the program word. Today
       none of the eight meson builds, and none of scipy's, uses either (READ, p1).
     - A bare program word, with no `/`, resolves through `PATH`. A bare Python name is allowed
       only when it is one of the shim's three names, which the recipe part puts first.
     - A program word that is a path with a Python name must be an allowed interpreter.
     - A program word that is a file with a `#!` line is read by its shebang the same way.
       `#!/usr/bin/env` followed by one of the shim's three names is allowed: it resolves through
       `PATH`, whose head the recipe part holds. An absolute Python must be an allowed one.

     These files are read:
     - In every `meson-log.txt` of `scan.MESON_BUILDS`, every `Running command: …` line, and
       every `Program <name> found: YES (…)` line. In the second, the found command is read as
       above, and when the **requested** `<name>` is a Python name, the found command's program
       word must also be an allowed interpreter. So `Program python3 found: YES (/opt/x/bin/py)`
       is a hit even though `py` is no Python name.
     - Every `COMMAND =` and `command =` line of every listed `build.ninja`.
     - **Every `config.log` under `build/`** (the review's F4): every `configure:NNN: found <path>`
       line whose basename is a Python name must name an allowed interpreter. That reads CPython's
       two, and xz's, libxml2's and libxslt's, and any a later build adds. The folders the
       harness and the lane keep under `build/` (`uv-cache/`, `reviews-evidence/`, `harness*/`,
       `lane-*/`) are skipped; today none holds a `config.log` (READ, the main tree).
     - Every folder a step script puts on `PATH` ahead of the stand-in (parsed from each
       `PATH=…:$PATH` assignment in `scripts/steps/*.sh`, `$B` and `$T` read as `build/` and
       `build/tools/`), present on disk, holds no file with a Python name unless it is the shim
       folder. Today that is `pylib/bin` and wasmtime's folder; 037 adds `scipy-tools/bin`
       (Decision 9, the review's F6).
     - `build/logs/10_tools.log` holds the gate line, and its `behind it` part names
       `build/no-host-python/python2`. That proves the build ran under the stand-in.
     - `build/logs/unpinned-python.log` does not exist.

     Each hit names the file, the line and the interpreter.
   - **Unit mutations** in `tests/unit/test_scan.py`. Each of these must name its hit:
     - a meson log line `Program python3 found: YES (/usr/bin/python3)`;
     - a meson log line `Program python3 found: YES (/opt/x/bin/py)` (the requested name);
     - a `build.ninja` command `/opt/homebrew/bin/python3 x.py`;
     - a `build.ninja` command `env PYTHONPATH=x /usr/bin/python3 y.py` (read past `env`);
     - a `build.ninja` command `…/meson --internal exe --unpickle x.dat`;
     - a script named as a command's program word whose shebang is `#!/usr/bin/python3`;
     - one whose shebang is `#!/usr/bin/env -i python3`;
     - a `config.log` under `build/xz-build/` whose probe found `/Users/x/.local/bin/python3.14`;
     - a step folder ahead of the stand-in, on disk, holding a `python3`;
     - a `10_tools.log` whose gate line says `behind it python2 is none`;
     - a `common.sh` whose `PATH` line lacks the shim;
     - a `build.sh` without the stand-in folder, or without the globs;
     - a `refuse-python` that takes its log from a variable.

     Each of these must pass: a `#!/usr/bin/env python3` script; the shim; `$HOSTPY`;
     `python-wasi-cross`; numpy's `env PYTHONPATH=… …/scripts/python-wasi-cross -m …`; meson's own
     `…/build/tools/python/bin/python3 script.py`; a bare `cython`.
   - **Driver cases** in `tests/unit/test_build_progress.py`. Its fake tree gains
     `scripts/refuse-python` and `ln`, and the existing cases keep their output line for line,
     because the stand-in prints nothing when nothing asks for it. The new cases:
     - a fake step that runs `python3` fails with the refuser's line in its log;
     - a fake step that runs `python3 -V 2> /dev/null || true` and exits 0 still fails, by the
       log rule;
     - a fake step that runs `env -i PATH="$PATH" sh -c 'python3.14 -V 2> /dev/null || true'` and
       exits 0 still fails, by the log rule (the review's F1);
     - with a fake `python3-intel64` in a folder on the caller's `PATH`, a fake step that runs
       `python3-intel64` reaches the stand-in and fails (the review's F2).

7. **The bytes do not change.** The interpreter only runs text transforms of pinned input, and
   Decision 3's prototype set was `14ada22a`, equal to main's. At build time this is proved, not
   assumed.
   - After the change, the full build's `SHA256SUMS` must equal main's except in `MANIFEST`'s
     line.
   - `MANIFEST` must equal main's except in exactly four `recipe` lines:
     `scripts/build.sh`, `scripts/steps/common.sh` and `scripts/steps/10_tools.sh` change, and
     `scripts/refuse-python` is added. **The four are counted against main at the rebase**, so a
     recipe file 037 changed and landed first is in both sides and does not count.
   - `python.wasm`, `python-snapshot.wasm`, `python-stdlib.zip` and every licence keep their
     hashes. Every judge metric (fuel, bytes) is unchanged.
   - Any other difference stops the build; after two failed attempts at explaining it, rule 7
     applies and the builder writes it down.
   - **`scripts/refuse-python` is committed before any full build.** `MANIFEST`'s recipe lines
     come from `git ls-files recipes scripts`, and the assembler stops on an untracked recipe
     file (READ, `assemble_artifacts.py:269,346-356`).

8. **A host needs no Python, and no Python is on disk.** This is the proof for calls by absolute
   path (Decision 2 f; the review's F5), which neither the shim nor the stand-in can see. The
   `linux/arm64` research container as spec 059 met it, with no Debian `python3` installed,
   builds from empty `build/` and writes macOS's `SHA256SUMS`. Its `host.txt` records, before the
   build:
   - `command -v python3` printing nothing;
   - `find / \( -path /proc -o -path /sys -o -path <the clone> \) -prune -o -type f -name
     'python*' -perm -u+x -print` printing nothing, so no executable named `python*` exists
     outside the clone.

   This is also the failure spec 059's first container run hit at step 37, gone. The x86_64 and
   the GitHub runners are covered by the release dry run: their images have a `python3`, which
   the stand-in now shadows. So the dry run exercises the stand-in, and the container exercises
   the no-Python case.

9. **Meeting spec 037.** Spec 037 (scipy, build-class) is being built now, uncommitted in its own
   worktree. The review read its tree (READ). The two specifications share four files:
   - `scripts/build.sh`: 037 changes only the `ALL=` step list; this one adds hunks near the step
     loop;
   - `scripts/steps/10_tools.sh`: 037 adds the f2py numpy at the end and edits the `tools:` line;
     this one adds the shim and its gate after the host Python's unpack;
   - `tests/harness/scan.py`: 037 adds `scipy-build` to `MESON_BUILDS`; this one adds functions
     beside;
   - `tests/checks/test_v1_5_rebuild_from_pins.py`: each adds a check.

   Whichever lands second rebases onto the other, and the lane's delta review sees the merged
   hunks.
   - **037's step 57 prepends `$B/scipy-tools/bin` (holding `f2py` alone) ahead of the shim.**
     Decision 6's step-folder rule reads that folder, so a Python name placed there later is a
     hit.
   - **037's step 38 (OpenBLAS) is `make` and `perl`,** outside the record part. The stand-in
     covers it (READ: no `python` in its logs).
   - **Scipy's records pass the rule as written** (READ, p1 and `scipy-build`'s meson log): 118
     commands run scripts whose shebang is `$HOSTPY`; 8 run `$HOSTPY` directly; `Program python`
     is `scripts/python-wasi-cross`; `f2py` is `scripts/f2py-host`, which execs `$HOSTPY` by path.

   If 037 lands first, this branch rebases and its full build runs 037's steps under the
   stand-in. A scipy generator that asks for `python3` gets the pinned one; one that asks for
   another Python name fails, and is answered in the rebased branch, never by exempting the name.

10. **Nothing else.** No upstream patch, no pin, no new dependency in `pyproject.toml`, no
    change to `-ffp-contract`, to the cross files or to the release workflow. The host's C
    compiler stays the build-Python's one unpinned input (spec 003, Decision 2), as before.

## Intent

Every Python that runs while the artifact set is built is the pinned host Python, or one built
from pins. A build host needs no Python of its own, and a host's own Pythons cannot reach the
build by name: a shim puts the pinned one first on `PATH`, and a refusing stand-in behind it,
for every Python name the host has, stops any step that asks for another. Calls by absolute
path are proved absent in a container with no Python on disk. The artifacts stay the same bytes.

## Design

```
scripts/steps/10_tools.sh      write build/tools/host-python/{python,python3,python3.15}
                               (exec "$HOSTPY" "$@"); gate them (command -v, /usr/bin/env
                               python3, sys.prefix); print the "host python: … behind it" line
scripts/steps/common.sh        PATH="$T/host-python:$T/pylib/bin:$T/$WASMTIME_DIR:$PATH"
scripts/build.sh               build/no-host-python/: a link to scripts/refuse-python for every
                               python*, pypy*, pip*, pydoc*, idle* executable on the caller's PATH
                               and for the fixed list; first on PATH; the log removed before each
                               step, a step that leaves it fails
scripts/refuse-python          new: the log from dirname "$0" (never a variable), one ERROR line
                               on stderr, exit 1
tests/harness/scan.py          the Python-name globs, allowed interpreters, the program-word
                               reader (env, meson --internal exe, bare names, shebangs),
                               host_python_recipe_errors, host_python_record_errors (meson logs,
                               build.ninja, every config.log, step folders ahead of the stand-in,
                               step 10's line, the log's absence)
tests/checks/test_v1_5_rebuild_from_pins.py   test_every_build_python_is_pinned
tests/unit/test_scan.py        the mutations of Decision 6
tests/unit/test_build_progress.py   the tree copies refuse-python, links ln; four driver cases
README.md                      the build paragraph: one host Python, the shim, the stand-in
CHANGELOG.md                   0.1.0a7
```

Unchanged: every other step, `scripts/00_download.sh`, `scripts/python-wasi-cross`, the cross
files, `downloads/SHA256SUMS`, the release workflow, `src/`.

## Scope

In: the above.

Out:
- the release workflow's `python3 -` diagnostic (Decision 2, outside the build);
- the wheel build after `scripts/build.sh` (`uv build` with hatchling under the workflow's
  `UV_PYTHON`): it packs the finished artifact set and writes no byte of it, and the same-bytes
  job compares the wheels it makes on three hosts. It is outside this mechanism, and a later
  specification may pin it;
- other unpinned host tools (`cc`, `make`, `sh`, `tar`, `sed`, `uv`, `git`, `perl`): the
  preflight names the first ones, and none is this finding;
- a Python name that matches none of the five globs and is not on the fixed list: the record
  part of the judge reads what the meson builds and configure found, and the container (Decision
  8) has no Python to find;
- rewriting any upstream shebang or `meson.build` (Decision 3);
- isolating the build from the host's filesystem on every build (a sandbox): the stand-in
  shadows names, the judge reads absolute paths from the records, and the container proves the
  rest once per build-class change, which is what the finding asks.

## Acceptance criteria

1. **Seen failing first**, before the shim exists. Each is recorded in the landing notes with its
   output.
   - **The check.** `test_every_build_python_is_pinned` fails on today's tree. Its recipe part
     names the missing shim on `common.sh`'s `PATH`, step 10's missing shim and gate, and
     `build.sh`'s missing stand-in. Its record part, run against the records a build of today's
     recipe leaves in the builder's worktree, names:
     - `freetype-build/meson-logs/meson-log.txt:112`;
     - `freetype-build/build.ninja` lines 42, 46 and 258;
     - CPython's `cross-build/aarch64-apple-darwin/config.log`;
     - the gate line missing from `10_tools.log`.

     Each names the host interpreter it found (on the drafting machine,
     `/Library/…/3.10/bin/python3` and `/Users/claygendron/.local/bin/python3.14`). The landing
     notes say why HarfBuzz's and matplotlib's `env` shebangs pass the record part on any tree:
     they are safe exactly when the recipe part holds, and it fails here.
   - **The stand-in alone.** A first commit adds Decision 4 (the stand-in and the log rule,
     `scripts/refuse-python` committed) and no shim. In a worktree where a build of today's
     recipe has left every step's inputs, each of three steps is run alone:
     - `scripts/build.sh 20` fails by the log rule (two `python3.15 -V` lines in the log);
     - `scripts/build.sh 37` fails at `freetype-2.14.3/meson.build:40`;
     - `scripts/build.sh 55` fails at `matplotlibrc`.

     Step 10 passes (Decision 2 e). These repeat Decision 2's EXECUTED facts, now through
     `build.sh`'s own stand-in. The landing notes list the names `build/no-host-python/` holds on
     the build machine.
   - **The gate.** Step 10 stops the build, in one line, in each of three cases, each in its own
     clone: the shim not written; the `python3` file pointing at a missing interpreter; `common.sh`'s
     `PATH` line without the shim folder (so `command -v python3` finds the stand-in).
   - **The units.** Each mutation of Decision 6 names its hit, and each driver case fails as it
     says.
2. **One host Python, end to end.** `scripts/refuse-python` is committed first (Decision 7). Then,
   on macOS, from empty `build/` with downloads verified, `scripts/build.sh --plain` passes every
   step. Then:
   - `build/logs/unpinned-python.log` does not exist;
   - `10_tools.log` holds the gate line, whose `behind it` part names
     `build/no-host-python/python2`;
   - FreeType's `meson-log.txt` names `build/tools/host-python/python3`;
   - CPython's native `config.log` found `build/tools/host-python/python3.15`;
   - `test_every_build_python_is_pinned` passes, printing what it read.
3. **The same bytes** (Decision 7). That build's `SHA256SUMS` differs from main's at the rebase
   (today `14ada22ab85623c5`) in `MANIFEST`'s line alone. `MANIFEST` differs in the four `recipe`
   lines alone, counted against main at the rebase. The landing notes show both `diff`s.
4. **A host without Python** (Decision 8). The `linux/arm64` container without `python3` builds
   from empty `build/`, a clone at the branch's commit, downloads from a cache of verified pins.
   Its `SHA256SUMS` equals criterion 3's. Its `host.txt` records `command -v python3` printing
   nothing and Decision 8's `find` printing nothing.
5. **The judge.** `uv run pytest -n 6` is green before "built"; the lane's serial run is accepted
   with `--accept` and `--accept-judge` (one check added; the fake tree of
   `test_build_progress.py` changed). The ratchet shows lost 0, and no metric grew. `ruff check`
   and `ruff format --check` are clean.
6. **The dry run** (AGENTS.md rule 6b). After landing, one `workflow_dispatch` run of
   `release.yml` on main's exact commit passes every job on all three systems. The rebuild jobs
   build under the stand-in on runners that have their own `python3`, and `same-bytes` reports
   the same `SHA256SUMS` and wheel. No tag is pushed before it passes.
7. **The words.**
   - The README's build paragraph says:
     - every build step runs the one pinned host Python through `build/tools/host-python/`;
     - any other Python name the host has refuses inside `scripts/build.sh`;
     - a step run by hand gets the shim without the stand-in;
     - a build host needs no Python.
   - The CHANGELOG entry below is under "0.1.0a7 — unreleased", and names the 0.1.0a6 security
     review's F2.
   - The landing notes close F2 by name.

   The CHANGELOG entry:

   > - **The build runs only the pinned host Python** (spec 079; the 0.1.0a6 security review's
   >   F2). FreeType's configuration headers, HarfBuzz's generated sources and matplotlib's
   >   `matplotlibrc` were written by whatever `python3` the build host had first on `PATH`, and
   >   CPython's configure ran it once. Now step 10 puts a shim for the pinned CPython 3.15.0 first
   >   on every step's `PATH`. Behind it, `scripts/build.sh` puts a stand-in for every other Python
   >   name the host has, which fails the step if it is run. A build host needs no Python of its
   >   own. The artifacts are the same bytes; `MANIFEST`'s recipe lines change.

## The owner's choices

None open. The owner's rule is §4.2, and the security review asked for this fix before 0.1.0
final. The mechanism (Decision 3), failing closed (Decision 4), the gate (Decision 5), the check
(Decision 6) and the proof of the same bytes (Decision 7) are decided here with their reasons.
Nothing is added to `../questions-for-the-owner.md`.

## Disposition of the pre-build review

The review: the scratchpad's
`079-review/079-the-build-runs-only-the-pinned-host-python-spec-2026-10-19.md`, verdict "ready
once F1 to F3; F4 to F6 taken or answered in writing". All six are taken, as the coordinator
asked.

| finding | disposition | where |
|---|---|---|
| F1, medium: the log is lost under steps 35 and 36's `env -i` | Fixed. `refuse-python` finds its log from `dirname "$0"`; no variable. Driver case for `env -i`. | Decision 4; Decision 6 (recipe part, a mutation, the third driver case) |
| F2, medium: the fixed list misses names the host has | Fixed. `build.sh` shadows every `python*`, `pypy*`, `pip*`, `pydoc*` and `idle*` executable on the caller's `PATH`, plus the fixed list; the shim stays first. | Decision 4; Decision 3's "Why `python3.15`"; Decision 6 (recipe part, a mutation, the fourth driver case); Scope |
| F3, low to medium: the record part reads only the first word | Fixed. The program word is read past `env` and its `NAME=value` words; `meson --internal exe` is read on and `--unpickle` is a hit; a bare Python name counts only as a shim name; the requested name of `Program … found` is tested too. Three mutations as asked. | Decision 6 |
| F4, low: the judge cannot tell the stand-in was there | Fixed. The gate line names what is behind the shim (`python2`), and the judge requires the stand-in. Every `config.log` under `build/` is read. | Decision 5; Decision 6; criterion 2 |
| F5, low, words: absolute paths | Taken. Census item (f) with the two READ facts; Decision 8 named as the proof; `host.txt` records the `find`. | Decision 2 (f); Decision 8; criterion 4 |
| F6, low, words: the overlap with 037 | Taken. The four shared files named; step 57's `scipy-tools/bin` read by a new step-folder rule; the recipe lines counted at the rebase; the wheel build's `uv` in Scope "Out". | Decision 9; Decision 6 (step folders); Decision 7; Scope |
| N1 to N4 | Written in: N1 under Decision 3; N2 under Decision 5; N3 under Decision 3; N4 is Decision 2 (d) as it stood. | Decisions 2, 3, 5 |

The coordinator's further note, "commit `scripts/refuse-python` before any full build", is in
Decision 7 and criteria 1 and 2.

## Landing notes

Not yet built.

## One line

Put a shim for the pinned host Python first on every build step's `PATH`, and a refusing stand-in
for every other Python name the host has behind it, so FreeType, HarfBuzz, matplotlib and
CPython's configure stop reaching the host's own interpreters, with the same bytes out.
