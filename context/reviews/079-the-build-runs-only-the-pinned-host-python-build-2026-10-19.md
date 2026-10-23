# Build review of spec 079: the build runs only the pinned host Python

- **Date:** 2026-10-19
- **Reviewer:** a fresh agent. I reviewed this specification before build (its F1 to F6 and its confirmation's C1 to C3). I wrote none of its code.
- **What was reviewed:** branch `spec/079-the-build-runs-only-the-pinned-host-python`, worktree `/Users/claygendron/Git/Repos/wasi_python-079`, on main `23f1c4f`. The commits:
  - `064d913`: C1 to C3 written into the specification;
  - `3469f49`: part 1, the stand-in, the check and the tests, in the "seen failing first" state;
  - `7efdb6e`: part 2, the shim and the gate;
  - `6094a01`: README and CHANGELOG;
  - `00dcfce`: the landing notes.

  The evidence is in the worktree's `build/079/`, including `container/`.
- **How:** I read the code diff `23f1c4f..00dcfce` whole (scripts, `scan.py`, the check, both unit files, README, CHANGELOG) and the landing notes. Probes ran in a fresh scratch copy of `00dcfce` (`git archive`, at `…/scratchpad/079-buildreview/tree3/`), with the pinned downloads linked in. Where a probe needed it, the step script it ran was replaced by a probe step; the built `build.sh`, `refuse-python` and `scan.py` were left untouched. Read-only probes ran against the main tree and the worktree. I ran the fast tier with `-n 3` in the worktree. I did no full rebuild, because of the machine's load; I compared the builder's sets instead. I touched no git tree. Labels: EXECUTED, READ, INFERRED.
- **Probes:** `probes/` beside this file:
  - `p7_built_sweep.log`: the built `build.sh` with a hostile `PATH`;
  - `p8_built_reader.py` and `.log`: the built reader on review cases;
  - `p9_check_on_main.py` and `.log`: the check, read only, on main and the worktree;
  - `fast-tier.out`.

## Verdict in one paragraph

The code does what the specification says.
- The bytes are main's, apart from `MANIFEST`'s four recipe lines, on macOS and in a container with no Python on disk.
- The check fails on main's records with exactly the 11 hits the notes name. It passes on the branch.
- C1 to C3 are in the code, and every pre-build probe I re-ran against the built scripts now behaves.

Two small holes in the judge remain. Each is latent, and each fails open only for a construction no step or meson emits today:
- the ninja reader skips every command line that starts with a variable, not just `$COMMAND`;
- the step-folder rule takes `$(…)` literally.

**Lands once F1 and F2** are fixed, or answered in writing in the landing notes. Both are judge-only changes of a few lines. Neither touches a script, so the bytes stand.

## Findings, most severe first

### F1. The ninja reader skips every `$`-led command line, not only `$COMMAND`. Low.

`ninja_hits` passes over any `command =` or `COMMAND =` line whose text starts with `$`. The notes describe the departure as "skips a ninja variable (`command = $COMMAND`, meson's rule indirection)". The code is wider than that.

- EXECUTED (`p8`): `rule ODD` with ` command = $PY gen.py`, and an edge setting ` PY = /usr/bin/python3`. The reader read 0 commands and gave no hit. The edge's `PY =` line is never read, because only `COMMAND =` lines are.
- READ (`p1` of the pre-build review): in every meson build of main and of 037, the one `$`-led command line is `command = $COMMAND`. So this costs nothing today.

**Fix.** Skip exactly `$COMMAND` (and `${COMMAND}`). Any other leading variable is a hit ("a ninja variable the judge does not read"). Add one mutation.

### F2. The step-folder rule takes `$(…)` and backticks literally. Low.

C3 says a folder the rule cannot resolve is a hit, never a skip. `_resolve` replaces `$NAME` and `${NAME}` only. In `PATH=$(pwd)/x:$PATH` the part `$(pwd)/x` comes out unchanged. It is then not a folder on disk, so the check skips it without a word.

- EXECUTED (`p8`): `step_path_folders` returned `99_odd.sh $(pwd)/x` as a folder, with no unresolved line. `$NOWHERE/bin` and `$HOME/bin` were reported unresolved, as C3 asks.
- READ: no step script uses a command substitution in a `PATH=` line today.

**Fix.** A part holding `$(` or a backtick is unresolved. Add one mutation.

## C1 to C3, as written in the code

- **C1, `env`'s grammar: in, and correct.**
  - READ: `scan.env_program`. `-u`, `-C`, `-P` and `-S` consume their argument. `-i`, `-`, `-P`, `-S`, `--ignore-environment`, `--split-string…`, `--unset=PATH`, `-u PATH` and a `PATH=` word are breaches. Any other option is a hit. A shell with `-c` is a hit.
  - EXECUTED (`p8`), all as asked:
    - `env -u FOO /usr/bin/python3`, `env -C /tmp /usr/bin/python3` and `env env PYTHONPATH=a /usr/bin/python3`: hits on `/usr/bin/python3`;
    - `env -P`, `env -`, `--ignore-environment`, `--unset=PATH`, `-u PATH` and `PATH=/usr/bin`: breaches;
    - `--unset=FOO` and `-iv`: hits as unread options;
    - `sh -c` and `bash -c`: hits;
    - `--unpickle`: a hit; `--internal exe … -- /usr/bin/python3`: read on to the hit;
    - numpy's `env PYTHONPATH=… …/python-wasi-cross -m …`, the shim, `$HOSTPY`, the build-Python and a bare `cython`: pass.
  - The unit file holds the same cases (READ, `test_program_word_reads_env_meson_shells_and_shebangs`).
- **C2, the sweep: in, and correct.**
  - READ: `build.sh` splits `PATH` on `:` with globbing off. It keeps only absolute entries, skips only `build/no-host-python`, tests `-f` and `-x`, and lets the first link of a name win.
  - EXECUTED (`p7`): the built `build.sh` ran under this `PATH`: `relbin` (relative), an empty entry, a folder whose path holds a space, a folder whose name holds `*`, one folder twice, a symbolic link to `/usr/local/bin/python3.7m`, a folder named `python3.dir`, a dangling `python-dangling`, a trailing `:`, then this machine's own `PATH`. Results:
    - the step's `PATH` was the stand-in, then the absolute entries only. `relbin`, the empty entries and this machine's literal `~/.dotnet/tools` were dropped;
    - `python3.99` (the spaced folder), `pypy3.88` (the `*` folder) and `python3.7m` (the link) resolved to the stand-in;
    - `python3.77` (only in `relbin`) resolved to nothing;
    - the folder and the dangling link were not linked;
    - 62 links in all, and no error from the duplicates.
- **C3, variables in the step-folder rule: in.** With F2's exception it is correct.
  - EXECUTED (`p8`): `$T/$WASMTIME_DIR` resolved from `line.conf`'s value, and 037's `TOOLS="$B/scipy-tools"` with `$TOOLS/bin` resolved to `build/scipy-tools/bin`. An unknown `$NOWHERE` and `$HOME` were reported unresolved.

## The pre-build probes against the built scripts

- **`env -i` (F1 of the pre-build review): closed.** EXECUTED (`p7`, `PROBE=envi`): a probe step ran `env -i PATH="$PATH" LC_ALL=C sh -c 'python3.14 -V 2>/dev/null || true'` and exited 0. The built `build.sh` failed it with `ERROR: 00_download ran an unpinned Python (build/logs/unpinned-python.log)`. The log held `…/build/no-host-python/python3.14 -V`.
- **Names the old list missed (F2): closed.** EXECUTED (`p7`, `PROBE=intel`): `python3-intel64 -c 1 || true` reached the stand-in and failed the step by the log rule.
- **The env option rules, duplicates and relative entries, and the step-folder variables:** see C1 to C3 above.

## The check really fails on main's records

EXECUTED (`p9`, the built `scan.py`, read only):
- **Main tree (`23f1c4f`):** the recipe part gives 18 errors and the record part 11 hits, from 59 files read. The hits are FreeType's `meson-log.txt` lines 112, 113, 120, 127, 149 and 161; `build.ninja` lines 42, 46 and 258; CPython's native `config.log:88` (`~/.local/bin/python3.14`); and no gate line. This matches `build/079/c1-check-on-main-records.out` line for line.
- **The 079 worktree:** 0 recipe errors and 0 record hits, from 60 files read.

## The container's `host.txt` and the same bytes

- READ, `build/079/container/host.txt`:
  - the build host was `Linux 7.0.12-linuxkit aarch64`, at commit `6094a01`. `00dcfce` after it changes only the landing notes;
  - `command -v python3` printed nothing;
  - the `find` printed nothing between its header and `(end of find)`.
- READ, `run.sh`: the `find` prunes `/proc`, `/sys` and the clone `/work`, as the specification says, and also the three mounts `/src` (the worktree, read only), `/cache` (downloads) and `/out`. None of the mounts is on `PATH` or at a system path. So the extra prunes are a fair reading of "outside the clone". Note the difference anyway (N1).
- READ, `container/build.txt`: all 16 steps ok. `10_tools.log`'s gate line reads `behind it python2 is build/no-host-python/python2`. `records.txt` shows FreeType's `Program python3 found: YES (build/tools/host-python/python3)`, the native `config.log` `found build/tools/host-python/python3.15`, and `unpinned-python.log: absent`.
- EXECUTED (`cmp`, `diff`, `shasum`):
  - the container's `SHA256SUMS` and `MANIFEST` equal the worktree's macOS set byte for byte (`c9dcb5b84ae2447a…`);
  - against main's set (`14ada22a…`), `SHA256SUMS` differs in `MANIFEST`'s line alone, and `MANIFEST` in exactly the four recipe lines: `scripts/build.sh`, `scripts/refuse-python` (added), `scripts/steps/10_tools.sh` and `scripts/steps/common.sh`;
  - each of those four hashes equals `shasum` of the file at `00dcfce`;
  - `python.wasm` (`ab78e893…`) and the snapshot (`c50ca51f…`) are main's.

## The builder's departures

- **The by-hand fixture exports the stand-in's `PATH`:** acceptable. The test compares a step's whole environment under `build.sh` with a by-hand run under `build.sh`'s exports. `build.sh` now exports `PATH`, so the reference must too. The test still compares the whole environment (READ). It changes the judge's reference in the one place the behaviour changed. The lane's `--accept-judge` covers it.
- **The judge skips `$COMMAND`:** right in intent. The code is wider than the words (F1).
- **"No variable" is checked as reading only `$0`, `$*`, `name` and `dir`:** stricter than the specification's words. Good.
- **Extra sweep cases:** good. They cover what C2 asked.
- **The gate's missing-interpreter case stops at the `env` probe:** right. `command -v` still finds the shim's file, and the stop is one line.
- **Duplicate folders in the step-folder rule's list:** harmless. `common.sh`'s lines are read ahead of each step, so a folder appears once per step (EXECUTED, `p8`). Only the "read" list grows.

## Notes (no finding)

- **N1.** The container's `find` also prunes the three mounts (above). Say so in the criterion 4 note.
- **N2.** A program whose name is not a Python name passes the ninja reader, for example a `/opt/x/bin/py` that is a host interpreter (EXECUTED, `p8`). Meson's `Program python3 found` lines are caught through the requested name. The rest is the container's proof, as Decision 8 says.
- **N3.** CPython's `Platforms/WASI` puts `wasi-sdk/bin` first on configure's `PATH` from Python, not from a step script, so the step-folder rule does not read it. That folder holds no Python (READ in the pre-build review).
- **N4.** For 037's rebase: the step-folder rule resolves `$TOOLS/bin` (above). `scipy-build` joins `MESON_BUILDS`. 037's records passed the program-word rule in the pre-build review's `p1`. OpenBLAS's `make` writes no `config.log`.
- **N5.** The fast tier's and the full judge's `grew` rows are spec 071's plain-recursion rows. The builder's full run shows `heapq-plain` at three different values across three runs. The bytes are main's. So I agree the growth is noise, which spec 080 addresses.

## The judge in this review

EXECUTED: `uv run pytest -m "not slow" -n 3 -p no:cacheprovider` in the worktree, at `00dcfce`, without `--accept` (`probes/fast-tier.out`). The result:

- `496/551 pass · 1 gap · 3 blocked · 0 fail · 51 deselected`;
- `1772 passed, 10 skipped, 1 xfailed`;
- ratchet `lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 1 · grew 2`.

The pass counts match the builder's fast run. The two `grew` rows are `lru-cache-plain` (+0.19 %) and `pickle-partial-plain` (+0.05 %), both spec 071's plain-recursion rows. They are not the same rows the builder's runs grew (`heapq-plain`, `lru-cache-plain`). That supports N5: the fuel moves from run to run on bytes identical to main's. The check `test_every_build_python_is_pinned` passes (it is the one gained). I did not run the full tier, because of the machine's load. The builder's full run is `533/551 · 0 fail · lost 0` (READ, `build/079/judge-full.out`).

## Verdict

**Lands once F1 and F2.** Each is fixed (a few lines of `scan.py` and one unit mutation; no script changes, so no rebuild is needed), or answered in writing in the landing notes.

One line: the shim and the stand-in work and the bytes are main's; the judge should stop skipping `$`-led ninja commands other than `$COMMAND`, and stop reading `$(…)` as a folder.
