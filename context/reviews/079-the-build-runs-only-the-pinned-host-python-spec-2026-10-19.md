# Review of spec 079 before build: the build runs only the pinned host Python

- **Date:** 2026-10-19
- **Reviewer:** a fresh agent that did not write the specification (constitution §5.6).
- **What was reviewed:** `context/specifications/079-the-build-runs-only-the-pinned-host-python.md` at `abf1817` on `spec/079-the-build-runs-only-the-pinned-host-python` (from main `23f1c4f`), worktree `/Users/claygendron/Git/Repos/wasi_python-079`, and the author's evidence in that worktree's `build/079/`.
- **Read beside it:** `AGENTS.md`; constitution §4.1, §4.2, §5.6; the 0.1.0a6 security review's F2; spec 059's landing notes (the container run that stopped at step 37); spec 037's worktree (`/Users/claygendron/Git/Repos/wasi_python-037`, uncommitted, read only); the pinned meson 1.12.1 under the main tree's `build/tools/pylib/mesonbuild/`.
- **How:** read only in the main tree and both worktrees. One scratch copy (`git archive abf1817`) with my own prototype of Decisions 3 to 5 (not the builder's code), under `…/scratchpad/079-review/tree/`. Probes and their logs are in `probes/` beside this file. Labels: EXECUTED (I ran it), READ (I read it in a file), INFERRED (I reasoned it).

## Verdict in one paragraph

The design is right and the census is good. The shim works, and it changes no byte: I repeated steps 10, 30 and 37 independently and got the main tree's bytes. But the fail-closed half has two holes. A refusal is logged only through an environment variable, and steps 35 and 36 clear the environment. The stand-in's fixed list also misses Python interpreters that exist on the drafting machine itself. The judge's record part also needs to read through `env` prefixes. Each is a small fix to the spec's text. **Ready once F1 to F3; F4 to F6 taken or answered in writing.**

## Findings, most severe first

### F1. The log rule is lost in steps 35 and 36, which run configure under `env -i`. Medium.

Decision 4 says a refusal the step swallowed still stops the build, by the log. But `scripts/refuse-python` writes the log only "when `$UNPINNED_PYTHON_LOG` is set".

- READ: steps 35 and 36 run xz's, libxml2's and libxslt's `configure` and `make` through `clean() { env -i PATH="$PATH" LC_ALL=C "$@"; }` (`35_stdlib_libs.sh:13,46,52`; `36_xml_libs.sh:20,43,49`). `apply_patches.sh:34` does the same for `git`.
- `env -i` keeps `PATH`, so the shim and the stand-in still apply. It drops `UNPINNED_PYTHON_LOG`. So the refusal happens, and nothing is written.
- EXECUTED (`probes/p3_coverage_and_env_i.log`, part p3b), with a stand-in written as Decision 4 says: `python3.14 -V 2>/dev/null || true` leaves the log and so fails the step; the same command under `env -i PATH="$PATH"` exits 0 and leaves no log.
- This is exactly the case Decision 4 exists for: configure probing a Python and carrying on (Decision 2 d). It is latent today: libxml2 runs with `--without-python`, and the author's step 35 and 36 runs saw no refusal. One dropped flag in a later upstream would make it real.

**Fix.** Make the log path independent of the environment. Either:

- `refuse-python` derives the log from its own link: `$0` is `build/no-host-python/<name>`, so the log is `$(dirname "$0")/../logs/unpinned-python.log`; or
- `build.sh` writes each stand-in as a two-line script with the log's absolute path in it, not a symbolic link.

Keep the variable as an override at most. Add a driver case to Decision 6: a fake step that runs `env -i PATH="$PATH" sh -c 'python3.14 -V 2> /dev/null || true'` and exits 0 must fail by the log rule.

### F2. The stand-in's fixed list misses interpreters this machine has. Medium.

Decision 4 shadows `python`, `python2`, `python2.7`, `python3` and `python3.0` to `python3.20`.

- EXECUTED (`probes/p3_coverage_and_env_i.log`, part p3a): with that folder first on `PATH`, these names still reach the host:
  - `python3-intel64` (Framework 3.10) and `python3.7m` (`/usr/local/bin`): Mach-O interpreters;
  - `python3-config`, `python3.10-config`, `python3.13-config`, `python3.7m-config`: Python programs whose absolute shebangs name host interpreters (READ, `head -1` of each);
  - `python-build` (pyenv).
- EXECUTED in the real build environment: my scratch step 10 printed `python3-intel64 is /Library/Frameworks/…/3.10/bin/python3-intel64` and `python3.10-config is …` from inside `scripts/build.sh` (`probes/p2_steps_10_30_37.out`; the line is in the scratch `build/logs/10_tools.log`).
- Nothing asks for these names today (INFERRED, from the author's clean runs and my census below). But "a step that asks for another name meets Decision 4's stand-in" (Decision 3) is not true as written. Names past `python3.20` and `python3.15-config` fall out the same way.

**Fix.** Shadow what the host has, not only what a list guesses. Before the first step, `build.sh` adds a stand-in for every executable on the caller's `PATH` whose name matches `python*`, `pypy*`, `pip*`, `pydoc*` or `idle*`, plus today's fixed list for names the host lacks. The shim folder still comes first, so the three pinned names still win. Update the Scope line "a Python name outside Decision 4's list" to match. Decision 6's recipe part can check the glob, and a unit case can put a fake `python3-intel64` on a fake `PATH`.

### F3. The record part reads a command's first word, but numpy's generators start with `env`. Low to medium.

Decision 6 checks "every `COMMAND =` and `command =` line … by its first word".

- READ (`probes/p1_ninja_first_words.log`): four of numpy's commands are `env PYTHONPATH=…/numpy/_core …/scripts/python-wasi-cross -m code_generators.…` (`numpy-build/build.ninja:114,118,122,126`). The first word is `env`. Today the real program is allowed. An `env PYTHONPATH=x /usr/bin/python3 y.py` would pass the rule as written.
- meson wraps some custom commands as `meson --internal exe … -- <prog>`, or hides them in a pickled file with `--unpickle`. READ: none in today's 8 meson builds or in scipy's (0 of each). The first word would be `meson`, which is allowed.
- Bare first words (`cython`, `rm`) resolve through `PATH`. The spec does not say how a bare `python3` is read.
- The "name is `python*`" test looks only at the found path. `Program python3 found: YES (/opt/x/bin/py)` would pass.

**Fix.** In Decision 6:
- skip `env`, its flags and its `NAME=value` words, and read the next word (`env -i`, `-S`, `-u PATH` or `PATH=` stay breaches);
- treat `--internal exe` as a hit unless the program after `--` is read, and `--unpickle` as a hit;
- read a bare Python name as the shim, allowed only when the recipe part holds;
- apply the Python-name test to meson's requested name as well as to the found path.

Add three mutations: `env PYTHONPATH=x /usr/bin/python3 y.py`; `meson --internal exe --unpickle x.dat`; `Program python3 found: YES (/opt/x/bin/py)`.

### F4. The judge cannot tell whether the build ran under the stand-in. Low.

- The record part requires `build/logs/unpinned-python.log` to be absent. After any successful `build.sh` run this is always true, because a step that left the log failed. For steps run by hand (`common.sh` only, no stand-in) it is true trivially. So it proves nothing by itself (INFERRED from Decision 4's text).
- The gate line proves the shim, not the stand-in behind it.

**Fix.** Step 10's gate line also names what is behind the shim, for example `command -v python3.14`: `build/no-host-python/python3.14`, or `none (run outside scripts/build.sh)`. The record part requires the stand-in. EXECUTED: my prototype's line printed `python3.14 is <tree>/build/no-host-python/python3.14` (scratch `build/logs/10_tools.log`).

While there: the record part reads only CPython's two `config.log`. xz's, libxml2's and libxslt's `config.log` are just as cheap to read. "Every `checking for python…` followed by `found <path>` in any `config.log` under `build/` names an allowed interpreter" covers them all.

### F5. The census does not discuss absolute paths, which neither the stand-in nor most records see. Low; words only.

The stand-in shadows names. A call by absolute path (`/usr/bin/python3 x.py`, or a run script with a `#!/usr/bin/python3` line) bypasses it. The record part sees one only in meson's and CPython's records, not in a Makefile recipe run by `make`.

- READ (grep of the main tree's records): no `build.ninja`, `Makefile`, `config.status`, `libtool`, `config.log` or `meson-log.txt` names an absolute host Python, other than FreeType's (the finding itself). `config.log`'s `PATH:` lines and CPython's `sed` of `idle3` and `pydoc3` are the other matches, and none runs a Python.
- READ: absolute Python shebangs in the source trees sit only in files no step runs (CPython's `Tools/gdb`, `Tools/build/generate_slots.py`, the generated `python-config`; numpy's tests; pillow's fuzzers; lxml's docs; libxslt's `setup.py.in`).
- The real backstop is Decision 8. The container has no Python on disk, so an absolute call there fails, or is swallowed and then shows as different bytes.

**Fix (words).** Add a census item (f) for absolute paths, with the two READ facts above. Name Decision 8 as the proof for this route. In criterion 4, have `host.txt` record that no `python*` executable exists outside the clone, for example `ls /usr/bin/python* /usr/local/bin/python*` failing, not only `command -v python3` printing nothing.

### F6. Decision 9 understates the overlap with spec 037. Low; words only.

READ, 037's uncommitted tree (`git diff HEAD`):

- 037 edits `scripts/steps/10_tools.sh` too: the f2py numpy at the end of the file and the `tools:` line. It also edits `tests/harness/scan.py` (`MESON_BUILDS` gains `scipy-build`) and `tests/checks/test_v1_5_rebuild_from_pins.py`. Decision 9 names only `build.sh`.
- 037's step 57 prepends its own `$B/scipy-tools/bin` (holding `f2py` only) ahead of the shim. The recipe part checks only `common.sh`'s line. A later step folder holding a Python name would sit ahead of the shim unseen.
- 037's step 38 (OpenBLAS) is `make` and `perl`, outside the record part; the stand-in covers it (READ: no `python` in its logs).
- Scipy's records pass the rule as proposed (READ, `probes/p1_ninja_first_words.log` and `scipy-build/meson-logs/meson-log.txt`): 118 commands run scripts whose shebang is `$HOSTPY`; 8 run `$HOSTPY` directly; `Program python` is `scripts/python-wasi-cross`; `f2py` is `scripts/f2py-host`, which execs `$HOSTPY` by path; meson runs scipy's generators on its own interpreter.

**Fix (words).** Name the three shared files in Decision 9. Say that Decision 7's "exactly four `recipe` lines" is counted against main at the rebase. Optionally, the recipe part could check that no step-local `PATH` prepend holds a Python name.

## The questions asked, answered

- **Absolute `/usr/bin/python3`.** See F5: none reached today (READ). Only the container proves this.
- **`py` on Windows.** Not a route. The build hosts are `MACOS_ARM64`, `LINUX_AARCH64` and `LINUX_X86_64` (READ, `scripts/line.sh`). The release's rebuild jobs run on `macos-15`, `ubuntu-24.04-arm` and `ubuntu-24.04` (READ, `release.yml:37,120,183`). Windows only verifies.
- **meson's own interpreter.** `$HOSTPY`: `build/tools/pylib/bin/meson`'s shebang is `…/build/tools/python/bin/python3` (READ). Meson rewrites a non-executable script's `/usr/bin/env python3` or `…/python3` shebang to its own interpreter (READ, `mesonbuild/programs.py:262-265`). `find_program('python3')` falls back to meson's interpreter only when `PATH` has none (READ, `interpreter/interpreter.py:1864`). The spec's account is right.
- **ninja regenerating.** `REGENERATE_BUILD` runs `build/tools/pylib/bin/meson` (`$HOSTPY` shebang), or numpy's vendored meson under `$HOSTPY` (READ, `freetype-build/build.ninja:31`, `numpy-build/build.ninja:56`). Pinned either way.
- **pip or uv in steps.** No `pip` in any step. `uv` only in step 10, with `--python "$HOSTPY"` (READ). The workflow's `UV_PYTHON: "3.14.2"` does not override a command-line `--python` (INFERRED from uv's documented precedence). The wheel build after `build.sh` (`uv build`, hatchling, `UV_PYTHON` 3.14.2) is outside this spec's mechanism. Worth one line in Scope "Out", beside the `python3 -` diagnostic, because the wheel is part of the product.
- **scipy's meson build.** Clean under the proposed rule. See F6.
- **pkg-config, cmake.** pkg-config is the pinned pkgconf binary by path in the cross files (spec 023). Meson's CMake lookup points at `build/no-cmake` for matplotlib and finds none for numpy (READ, the meson logs). Neither runs a Python.
- **Coverage list.** See F2: wrong by construction. Shadow by glob.
- **Can the judge be fooled?** Yes, three ways, F1, F3 and F4. It is honest about which files it reads (criterion 2 prints them), but its name claims more than meson logs, ninja files and configure logs show. With F1 to F4 taken it is as good as a name-based guard can be. The container (F5) covers the rest.
- **Same-bytes claim.** Holds.
  - READ: the 079 worktree's `build/artifacts/SHA256SUMS` hashes `14ada22ab85623c5…`, the same as the main tree's (`shasum`).
  - READ: its FreeType log line 112 names `build/tools/host-python/python3`. Its native `config.log:85-87` found `build/tools/host-python/python3.15`.
  - EXECUTED, independently (`probes/p2_steps_10_30_37.out`, `probes/p2_records.log`): a scratch copy of `abf1817` with my prototype of Decisions 3 to 5 ran steps 10, 30 and 37 through `build.sh`. The gate passed. FreeType found the shim. The log stayed absent, so HarfBuzz's `env python3` reached the shim and not the stand-in behind it. `libfreetype.a`, `libharfbuzz.a`, `libSheenBidi.a`, `libraqm.a`, `libqhull_r.a`, `ftoption.h`, `ftmodule.h`, `hb-version.h`, `harfbuzz.cc` and `harfbuzz-world.cc` equal the main tree's byte for byte, from a different checkout path.
  - I did not repeat step 20 or 55: the machine's load average was 93 on 10 cores. The author's runs cover them.
- **Container plan.** Sound, with F5's stronger `host.txt` line. Only `linux/arm64` is run locally. `linux/amd64` is left to the dry run, where runners have their own `python3`, so the stand-in is exercised there and the no-Python case is not. That is acceptable.
- **"No `recipes/` change" and build-class.** Both right.
  - Build-class: the spec touches `scripts/` (AGENTS.md rule 2).
  - `MANIFEST`'s `recipe` lines come from `git ls-files recipes scripts` (`assemble_artifacts.py:346-356`, READ). So `scripts/refuse-python` adds one line, and the three edits change three. Decision 7's count of four is right.
  - The file must be committed before the full build: the assembler stops on untracked recipe files (`assemble_artifacts.py:269`).
- **Interplay with 037's `build.sh` changes.** 037 changes only the `ALL=` line of `build.sh`. 079's hunks sit near the step loop, so they rebase cleanly (INFERRED). The real overlap is in F6.

## Notes (no finding)

- **N1. Why a shim and not `build/tools/python/bin` on `PATH`.** That folder also holds `pip`, `pip3`, `idle3`, `pydoc3` and the `-config` scripts (READ). The three-name shim is narrower. I agree with the choice. The spec could say so in one line under Decision 3.
- **N2. The gate must not print the version through `$(python3 …)`.** `BARE_PY` in `tests/harness/scan.py:160` matches a bare `python3` after `$(`. Use `"$HOSTPY"` or `/usr/bin/env python3`, as Decision 5 already says for the probes.
- **N3. The shim is written with `printf '%s'` into a double-quoted `exec` line.** A checkout path holding `"`, `$` or a backtick would break it. The gate's `sys.prefix` check would catch that in one line, so no change is needed.
- **N4. CPython's `PYTHON_FOR_REGEN` is still probed and run once, now as the shim.** Its Makefile uses it only in `regen-*`, `clinic` and check recipes (READ, `cross-build/aarch64-apple-darwin/Makefile:454-2182`). As the spec says.

## Probes

- `probes/p1_ninja_first_words.py`, `.log`: every `build.ninja` command's first word in the main tree and in 037's, classified (binary, script with its shebang, bare name, ninja variable).
- `probes/p2_steps_10_30_37.out`, `probes/p2_records.log`: the scratch run of steps 10, 30 and 37 with the prototype; the records and the byte comparison with the main tree.
- `probes/p3_coverage_and_env_i.log`: names the stand-in list leaves reachable on this host (p3a), and the swallowed refusal under `env -i` (p3b).
- `tree/`: the scratch copy of `abf1817` with my prototype edits to `scripts/build.sh`, `scripts/steps/common.sh`, `scripts/steps/10_tools.sh` and a new `scripts/refuse-python`. It is a probe, not a proposal for the builder's code.

## Verdict

**Ready once F1 to F3.** F4 to F6 should be taken, or answered in writing in the specification, before the build starts.

One line: the shim is right and changes no byte, but the refusing stand-in must log without the environment, shadow every Python the host actually has, and be read through `env` by the judge.

---

## Confirmation of the revision (`558a3fe` on `abf1817`, main still `23f1c4f`)

- **What was reviewed:** `git diff abf1817..558a3fe` in worktree -079. It changes the specification alone (333 lines in, 153 out). I read the revised text whole, including its disposition table.
- **How:** read only in both worktrees and the main tree. Probes ran in a fresh scratch copy (`git archive 558a3fe`, `…/scratchpad/079-review/tree2/`), with my own probe versions of the revised sweep and stand-in. New probes: `probes/p4_path_sweep.log` with `p4/sweep.sh`, `probes/p5_program_word.py` with `.log`, `probes/p6_refuse_dirname.log`.

### Each finding

- **F1: taken, and it works.** `refuse-python` now finds its log from `dirname "$0"` when that folder is `no-host-python`. It reads no variable. The recipe part, a mutation and a driver case check this. EXECUTED (`p6`): a probe written to the revised text logged `…/no-host-python/python3.14 -V` from under `env -i PATH="$PATH"`, run from `/tmp`. It also logged `python3-intel64` and `pip3` under `env -i`, and a meson-style call by absolute path.
- **F2: taken, and it works.** The sweep takes every `python*`, `pypy*`, `pip*`, `pydoc*` and `idle*` executable on the caller's `PATH`, plus the fixed list. EXECUTED (`p4a`): read as written over this machine's `PATH` and three test folders, it gave 61 links. They include `python3-intel64`, `python3.7m`, every `-config`, `pip3`, `pipenv`, `python-build`, a name in a folder whose path holds a space, and a symbolic link to an interpreter. Three details are open; see C2.
- **F3: taken, but the `env` grammar is too loose.** `env` prefixes, `--internal exe` and `--unpickle`, bare names and the requested name are all read now. The three mutations are there. See C1.
- **F4: taken.** The gate line names `python2`'s resolution, and the judge requires `build/no-host-python/python2`. `python2` is always on the fixed list and is never a shim name, so the probe is sound. Every `config.log` under `build/` is read. My earlier note that the log's absence proves little is answered by the gate line.
- **F5: taken.** Census item (f) holds both READ facts. Decision 8 is named as the proof. The `find` in `host.txt` prunes `/proc`, `/sys` and the clone. It matches regular files, so it catches a symbolic link's target, such as `/usr/bin/python3.11`. It would also catch a uv-managed Python left in the image. That is right.
- **F6: taken.**
  - Decision 9 names the four shared files, step 57's `scipy-tools/bin`, and step 38.
  - The recipe lines are counted against main at the rebase.
  - The wheel build is in Scope "Out".
  - A new step-folder rule reads every folder a step puts ahead of the stand-in. See C3 for how it resolves variables.
- **N1 to N4:** written in where the table says.

### The author's config.log skip (`uv-cache/`, `reviews-evidence/`, `harness*/`, `lane-*/`): safe

- **No step writes there.** Steps write to fixed folders: `*-build`, `Python-*`, `*-install`, the library folders and `tools/` (READ, `scripts/steps/*.sh`). `uv-cache/` holds the wheels of step 10's offline install; `uv` builds nothing there. The harness writes to `build/harness` (`tests/harness/paths.py:31`). The lane's and reviewers' folders hold copies and evidence.
- **Today the skip changes nothing.** The only `config.log` files under `build/` in the main tree, in 037's and in 079's are xz's, libxml2's, libxslt's and CPython's two (EXECUTED, `find`).
- **It is a skip list, not an allow list.** Any new step folder is read by default. The failure it avoids is a false red from a copy of some other build's records, not a missed real one.
- **Two refinements; neither blocks.**
  - Anchor each skip to a direct child of `build/`, so a folder of that name deep inside a source tree is still read.
  - Spell `harness*` as the two names that exist, `harness` and `harness-tmp`.
- Other non-step folders under the main tree's `build/` are read and hold no `config.log` today: `oracle/`, `upstream/`, `cpython-suite-research/`, `029/`, `a5-verify/`, `sets/`. A future research configure in one of them would show as a red. That is the safe direction.

### Corrections for the builder (small; none needs another pre-build round)

**C1. Read `env`'s options by their grammar, and treat `sh -c` as a hit. Low; judge text.** Decision 6 says to skip `env`'s "flags and `NAME=value` words". Read literally, that misses several cases. EXECUTED (`p5`), a reader written to the text:

- `env -u FOO /usr/bin/python3 y.py`: the reader takes `FOO` as the program word and passes it. `-u` takes an argument.
- `env -C /tmp /usr/bin/python3 y.py`: the same, through `-C`'s argument.
- `env -P /usr/local/bin python3 y.py`: passes. On macOS `-P altpath` searches `altpath` instead of `PATH` (READ, `man env`), so it is a breach, like `-i`.
- `env - python3`, `env --ignore-environment python3`, `env --unset=PATH python3`: pass as the bare shim name. Each clears `PATH`, so `env` falls back to a default path such as `/usr/bin`. All are breaches.
- `sh -c '/usr/bin/python3 y.py'`: the program word is `sh`, so it passes.

None of these appears in today's records (EXECUTED, a `grep` over the main tree's and 037's `build.ninja` and meson logs). So this is latent.

Fix in Decision 6:
- `-u`, `-C`, `-P` and `-S` consume their argument.
- `-i`, `-`, `-P`, `-S`, `--ignore-environment`, `--split-string…`, `-u PATH`, `--unset=PATH` and a `PATH=` word are breaches.
- Any other option is a hit (fail closed).
- A program word that is a shell with `-c` is a hit, unless its string is read the same way.
- Add two mutations: `env -u FOO /usr/bin/python3 y.py` and `env -P /usr/local/bin python3 y.py`.

**C2. Three details of the `PATH` sweep. Low; driver text.**

- **Duplicate names must not stop the build.** EXECUTED (`p4b`): with plain `ln -s` under `set -eu`, the sweep stops at the first name found in two folders (`python3.10`, in Homebrew's and `/usr/local/bin`). The fixed list also overlaps swept names. Say "the first link of a name wins, and later ones are skipped".
- **Empty and relative entries.** This machine's `PATH` holds a literal `~/.dotnet/tools`, a relative entry (EXECUTED, `p4a`). An empty entry means the current folder. Either kind resolves against each step's own current folder, so no sweep can see what it holds. Have `build.sh` drop empty and relative entries from the `PATH` it hands the steps, and say so in one line.
- **Skipping folders under `build/` has no stated reason, and is wider than needed.** Shadowing a name in `build/tools/python/bin` would be harmless, because the shim comes first. Skipping everything under `build/` leaves out, for example, an activated `build/oracle/venv/bin`.
  - READ: that venv exists in the main tree and in 037's. Its `pip`, `pip3` and `pip3.15` run that venv's own interpreter, which is not `$HOSTPY`.
  - `python`, `python3` and `python3.15` are on the fixed list anyway.
  - Narrow the skip to `build/no-host-python` itself, the folder being remade, or give the reason.

Spaces in folder names and symbolic links behave as the text says (EXECUTED, `p4a`). One more point: the test should be `-f` and `-x`, because `-x` alone is true for a folder.

**C3. Say how the step-folder rule resolves variables. Low; judge text.** The rule reads `$B` and `$T` alone.
- `common.sh`'s line also holds `$T/$WASMTIME_DIR`, a value that depends on the host (from `line.conf`).
- 037's step 57 uses `$TOOLS/bin`, with `TOOLS="$B/scipy-tools"` set in the step.

Say that a step's own simple assignments and the host's `line.conf` values are resolved, and that a folder the rule cannot resolve is a hit, never a skip.

### Nothing else new is wrong

- READ: the gate, the record part's allowed set, the unit mutations and driver cases, Decisions 7 to 9, Scope, the criteria and the CHANGELOG entry agree with each other and with the table.
- The revision changes only the specification. The scripts at `558a3fe` are `abf1817`'s, so the same-bytes evidence still stands (spec Decision 3; this review's p2).

### Verdict on the revision

**Confirmed for build.** All six findings are taken and do what they say. Two are EXECUTED (F1 and F2, `p6` and `p4`).

The author's config.log skip is safe, with two refinements that do not block. C1 to C3 are small text corrections to the judge and the driver. The builder writes them in as the build begins, and the build review checks them. None needs another pre-build round.

One line: the revision closes F1 to F6. What remains is `env`'s option grammar, duplicate and relative `PATH` entries in the sweep, and the step-folder rule's variables, which the builder takes in the build.
