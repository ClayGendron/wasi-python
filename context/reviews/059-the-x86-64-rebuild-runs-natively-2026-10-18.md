# Review of 059 — The x86_64 rebuild runs natively (build)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude). It wrote the pre-build review and its confirmation (`build/reviews-evidence/059-spec/`), and none of the build.
- **Reviewed:** `git diff dfa820c 3557769` on `spec/059-the-x86-64-rebuild-runs-natively` (`27b22d6` the change, `c778a5b` criterion 2's outputs, `3557769` the landing notes): 25 files, +1,763 −78. Read against the specification as confirmed (`09589c9`), the pre-build review (F1 to F10) and the confirmation (N1, N2).
- **Re-ran** (in the worktree, against the builder's own set in `build/artifacts`, `SHA256SUMS` `25a101ac97212ab2…`):
  - `uv run pytest -p no:cacheprovider -m "not slow" -n 3` → 1488 passed, 9 skipped, exit 1. Scoreboard: `343/391 pass · 0 gap · 2 blocked · 0 fail · 46 deselected`; ratchet `lost 0 · absent 1 · gained 3 · grew 2`; RED only for `ABSENT …test_x86_64_compiles_with_an_aarch64_compiler` and the two `bytes` growths (`fast.txt`).
  - `uv run pytest -p no:cacheprovider` (full, serial) → 1519 passed, 10 skipped, 14 xfailed in 9m55s, exit 1. Scoreboard: `374/391 pass · 14 gap · 3 blocked · 0 fail`; ratchet `lost 0 · absent 1 · unrun 0 · unrun locally 2 · gained 3 · grew 2`; the same three RED lines, and nothing else (`full.txt`). The upstream groups' `passes` are unchanged (no `passes` line in the ratchet).
  - `uv run ruff check src tests` → clean. `uv run ruff format --check src tests` → 88 files already formatted.
  - Gate mutations: step 10 run for real in a scratch clone at `3557769`, with the worktree's verified downloads (`clone/`, logs `gate-*.txt`).
  - Scan mutations: the real `scan` functions on planted inputs and on copies of the build's own records (`probes/scan_probe.py`, `probes/records_probe.py`).
  - The numpy object, checked on macOS and in a `linux/amd64` container.
  - The git tree is untouched (`git status` clean).

## Acceptance criteria against evidence

1. **Seen failing first** — met. READ in the landing notes: two checks red and one green as Decision 4 says, the four gate clones, and main without the flag. EXECUTED here: I re-applied the gate cases myself (below). The main-without-flag run differs from main in three lines, not two, because `MANIFEST` carries `line.conf`'s hash and one line of it was edited. That departure is justified; I checked the diff against main's set (`out-main-amd64/SHA256SUMS`): exactly `python.wasm`, `python-snapshot.wasm` and `MANIFEST`. The old x86_64 object `d3689743…` is in that run.
2. **Decision 1 reproduced** — met. READ: `outputs/cfg-route/`. It agrees with the pre-build review's own probes.
3. **Three hosts, one set, natively** — met. EXECUTED here: macOS's `SHA256SUMS` and the two container outputs (`059-build/out-059-amd64`, `out-059-arm64`) all hash to `25a101ac97212ab2`. The x86_64 log shows the two new gate lines; its download summary is `45 pins, 0 fetched`, with no fallback `get` (the six fallback files only verify as "other files" already in the cache). The numpy object is `2914eb833ad62c93` in the worktree's build and in the amd64 output. **3b** is met: 51 pins; seven gate lines through the emulated clang; the object `2914eb83…` through the launcher.
4. **The arithmetic did not change** — met. Every golden equals its `.expected`, and every upstream group's `passes` equals its accepted value (READ in the landing notes; confirmed by the full judge here). No fold had to be traced.
5. **The judge** — met, pending the lane's acceptance flags (see "Flags").
6. **The dry run** — not yet run, rightly: it belongs to the lane after landing, and no tag goes out before it (rule 6b).
7. **Documents** — met. README, CHANGELOG (0.1.0a6), the upstream draft narrowed, the research script with its outputs, and 040 amended at Decisions 2, 4 and 11. Also a note on 012's Decision 8 saying "nothing here changes". That is harmless; the spec had said 012 needs no amendment.

## What I re-applied (EXECUTED)

- **The gate** (step 10 itself, scratch clone; macOS SDK):
  - the unmodified step → both lines `compiler gate: clang|clang++ contracts nothing (-ffp-contract=off)`, rc 0;
  - write removed → `…clang's -cc1 line carries "-ffp-contract=on"…`, rc 1;
  - `-ffp-contract=fast` after the write → `…carries "-ffp-contract=fast"…`, rc 1;
  - written twice → `…clang.cfg does not hold -ffp-contract=off exactly once`, rc 1;
  - *invented:* `-ffp-model=precise` appended to `clang++.cfg` only → the clang line passes, then `clang++'s -cc1 line carries "-ffp-contract=on"`, rc 1;
  - *invented:* the unmodified step under `CCC_OVERRIDE_OPTIONS='+-ffast-math'` → `…carries "-ffp-contract=fast"…`, rc 1. An injection through the environment is caught.
- **The record scan** (`fp_record_errors`, on copies of the build's records):
  - baseline → no errors;
  - N2: harfbuzz's record removed → `harfbuzz-build/compile_commands.json is missing (listed in MESON_BUILDS)`;
  - N2: an unlisted `scipy-build` record → `…is not listed in MESON_BUILDS`;
  - F1: `-ffp-model=precise` on a pandas command → named with its file;
  - F1: `-Ofast` in an `arguments` entry → named;
  - N1: the CPython Makefile as built, with its two wasmtime `--config` lines → no error; `--config` on an added `$(CC)` recipe line → `recipe line: --config`;
  - F1: `MODULE__DECIMAL_CFLAGS=-ffast-math` added → named;
  - `-ffp-contract=fast` on a clang line in `make-n.txt` → named;
  - zlib's Makefile removed → `build/zlib-build/Makefile is missing`;
  - *invented:* automake's `COMPILE = $(CC) $(DEFS) -Ofast` in liblzma's Makefile → **not named** (finding 3).
- **The token rule** (`fp_hits`): plain tokens, meson list items, `--config=`, and `-Xclang -ffp-contract=on` are all hits; wasmtime's `--config` off a compiler line is not. *Invented:* a banned flag inside a quoted multi-flag string, or in an unquoted `NAME=-flag` token → **not a hit** (finding 1).
- **The numpy object:** the worktree's own `numpy-build/…/meson-generated_npy_math_complex.c.o` is `2914eb833ad62c93`. Its `build/tools/…/clang.cfg` and `clang++.cfg` hold the line once. In a `linux/amd64` container (`debian@sha256:a29215f6…`, Rosetta), the pinned x86_64 SDK (`0ba8b5bf…`) with step 10's exact append, compiling the builder's preprocessed file (`2193b9bd4d40aadc`), also gives `2914eb833ad62c93`.
- **The workflow:** the diff is comments, plus `ubuntu-24.04`'s `timeout: 360` → `120`. Both runners stay in the matrix and in both `same-bytes` loops; `nproc` and `binfmt_misc` stay; `attest` and `publish` still need `same-bytes`. Nothing else in the release path changed: no file under `release/`, no other step or script besides `line.conf`, `00_download.sh` and `10_tools.sh`. `REBUILD_TIMEOUTS` is 120 for both. The switch is off: `LINUX_X86_64_COMPILER_SDK_DIR=wasi-sdk-33.0-x86_64-linux`, and the five names and six pins stay.

## Findings, most severe first

1. **A banned flag inside a quoted multi-flag shell string escapes the static scan, and a direct compile leaves no record to catch it** (medium; `tests/harness/scan.py`, `fp_hits` / `fp_recipe_errors`). `fp_hits` splits a line with `shlex` and tests each whole token. `SQLITE_OPTS="-DSQLITE_X=1 -ffp-model=precise"` becomes one token, `SQLITE_OPTS=-DSQLITE_X=1 -ffp-model=precise`, and `CFLAGS=-ffast-math` stays one token. So neither is a hit (EXECUTED: `fp_recipe_errors` returns `[]` for both). The recipe writes its direct compiles' flags exactly this way: `35_stdlib_libs.sh:67` `SQLITE_OPTS="…"`, and `55_matplotlib.sh:46-47` `MAP="…"` and `CXX_EH="-fwasm-exceptions -mllvm … -fexceptions"`. Those compiles (SQLite, bzip2, qhull, Pillow, kiwisolver) leave no record, and the gate sees only the bare driver. The `-ffp-contract=` substring rule still catches that one spelling. Failure: `CXX_EH="… -fexceptions -ffp-model=precise"` in step 55 → kiwisolver compiles with contraction on; every check stays green; the first sign is a `same-bytes` failure on x86_64 (it brings back exactly the old pair, per the pre-build review). Fix (a few lines): in `fp_hits`, split each `shlex` token again on whitespace, drop a leading `NAME=`, and add the two cases to the unit mutations.

2. **A pragma in the project's own C files escapes every part** (low; `fp_recipe_errors` skips every line starting with `#`; `fp_pragma_hits` reads the source trees and the meson folders, not `recipes/`). In a C file under `recipes/`, a `#` line is a preprocessor line, not a comment. `recipes/npy_rename.h` and `npy_random_legacy_rename.h` are force-included (`-include`) into every numpy compile, `pandas_rename.h` into every pandas compile, and `reactor_main.c` is compiled in step 60. EXECUTED: `#pragma STDC FP_CONTRACT ON` in `recipes/reactor_main.c` and `#pragma clang fp contract(fast)` in `recipes/npy_rename.h` give `[]`. The builder's departure (skipping `#` comments, so `line.conf`'s own comment is not a hit) is right for shell, `line.conf` and cross files, and wrong for C. Fix: add `recipes/` (or the tracked files under `scripts/` and `recipes/`) to `fp_pragma_hits`' trees.

3. **Automake's `COMPILE` variable is not read** (nit; `fp_makefile_hits`). Variables count by name (`CC`, `CXX`, `CPP`, or a name containing `CFLAGS`, `CXXFLAGS`, `CPPFLAGS`, `CCSHARED` or `OPT`). xz's `COMPILE = $(CC) $(DEFS) …` and its recipe lines `$(AM_V_CC)$(COMPILE) -c …` match neither rule. EXECUTED: `-Ofast` added to `COMPILE` is not named. Flags normally reach `COMPILE` through `AM_CFLAGS`, `CFLAGS` and `CPPFLAGS`, which are read, so this is a corner. Fix: also read an assignment whose value is a compiler line (`is_compiler_line(value)`).

4. **The scoreboard's not-machine-checked line is missing** (nit; spec Decision 4's last bullet: "gains one line: 'source pragmas and compiler options outside the scanned records; `same-bytes` is the backstop'"). The fast and full scoreboards print the old list unchanged. Fix: add the line, or record in the Disposition why not.

5. **The growth reason's mechanism is a guess** (nit; landing notes, criterion 3). "Plain `fmul`/`fadd` pairs where `fmuladd` was one node" does not explain bytes on wasm32, where `fmuladd` was already lowered to two instructions. The measured facts stand: EXECUTED here, CODE +6,360, `name` −1,850, FUNCTION +7, TYPE +9; and most `fuel` fell. Accepting the growth as "the flag's effect on the optimizer's decisions", with these numbers and labelled INFERRED, is enough.

## The departures the builder asked about

- **057 not amended:** right. Decision 5 gives the list to 057's builder at its rebase; 059 edits no line of 057.
- **Criterion 1's run differing in three lines:** justified (`MANIFEST` carries `line.conf`'s hash), and verified above.
- **`fp_recipe_errors` skipping `#` lines:** fine for shell and ini files, wrong for C (finding 2). **`fp_hits` stripping brackets and quotes:** fine for meson lists; the gap is the multi-flag string (finding 1).
- **023's unpinned `python3` (HarfBuzz's `gen-hb-version.py`):** does **not** block 059. It is 023's, already on main. 059 neither adds nor widens it. The three hosts agreed with Debian's `python3` 3.13.5 installed, and the script writes a version header from a string. The lane's separate follow-up should either run it with the pinned host Python or at least print `python3 --version` in the workflow's tools step beside `cc` and `make`.

## Flags

- **`--retire tests/checks/test_rules.py::test_x86_64_compiles_with_an_aarch64_compiler`:** justified. Its rules live on, rewritten, in `test_every_host_compiles_natively_with_the_fallback_kept`. The old rule ("an arm64 SDK") is now wrong by design.
- **`--accept-growth`:** justified with the measured numbers: `python.wasm` 36,911,971 → 36,916,497 bytes, the snapshot 70,897,198 → 70,901,724. It is the only growth; 66 of 68 moved `fuel` values fell.
- **`--accept-judge`:** for the two new checks, the rewritten rule, the need and the timeout constant. **No `--accept-fewer-passes`:** none is needed.

## Constitution checks

- §4.1: holds. The flag is a recipe item on the unpacked toolchain; no source tree changes and no patch. §4.2: holds. No pin changes; the six fallback pins stay in `SHA256SUMS` and `MANIFEST`, and the native build fetches 45 pins. §4.3, §4.6: hold; the set's members are unchanged, and only the reactor's, the snapshot's and `MANIFEST`'s hashes move. §4.9: times appear only in the landing notes. §4.10: claims are labelled, with one guessed mechanism (finding 5). §4.13: ruff is clean. §4.14: the branch is local, and this review wrote nothing in git.
- §7: nothing tripped.

## Verdict

**Lands once finding 1 is fixed** (a few lines in `fp_hits`, plus two unit cases). Finding 2 should be fixed in the same change, since it is one more tree in the pragma grep. Findings 3 to 5 may be fixed or answered in writing. The recipe, the gate, the workflow and the three-host evidence are sound as built.

## Confirmation (2026-10-18, against `0cd4400`)

- **Reviewed:** `git diff bb8aa46 0cd4400` (the rebase of `3557769` onto `cd97dac`, plus the fix). It touches judge files and the specification only (`scan.py`, `scoreboard.py`, `test_v1_5_rebuild_from_pins.py`, `test_scan.py`). The set is unchanged.
- **Re-ran:** `uv run pytest -p no:cacheprovider -m "not slow" -n 3` in the worktree against the builder's set → 1527 passed, 9 skipped, exit 1. Scoreboard: `343/391 pass · 0 gap · 2 blocked · 0 fail`. Ratchet: `lost 0 · absent 1 · gained 3 · grew 2`. RED is only the retired check and the two `bytes` growths (+4,526), as before. The second not-machine-checked line now ends with "source pragmas and compiler options outside the scanned records (same-bytes is the backstop)". I did not re-run the full judge: nothing below raised a doubt, and the set did not change.
- **Plants:** the real `scan` functions, run on copies of the tracked files and records (`probes/confirm_probe.py`, `probes/records_probe.py`).
  - **F1, fixed.**
    - Step 55's real text with `-ffp-model=precise` added to `CXX_EH="…"` → hit, at `55_matplotlib.sh:47`.
    - `CFLAGS=-ffast-math` → hit.
    - The unmodified steps 35 and 55 and the numpy cross file stay clean. So does a `-D` macro holding a flag-like value (`-DX=-ffast`).
  - **F2, fixed.**
    - A copy of `recipes/` with `#pragma clang fp contract(fast)` in `npy_rename.h` and `#pragma STDC FP_CONTRACT ON` in `reactor_main.c` → both named.
    - The real `recipes/` is clean.
  - **F3, fixed.** `COMPILE = $(CC) $(DEFS) -Ofast` → `COMPILE: -Ofast`. That holds on a copy of liblzma's real Makefile too.
  - **New plants, all hits:**
    - `-Ofast` on the first line of step 35's quoted `SQLITE_OPTS="…"` → `35_stdlib_libs.sh:67`.
    - xz's `CFLAGS="-O2 -funsafe-math-optimizations"` → `:46`.
    - A `NAME=` item on a meson `c_args` line (`'X=-ffast-math'`) → `wasi-numpy.cross:29`.
  - **No regression.** On copies of the build's own records, the baseline gives no error. Every earlier mutation still names its breach: N2 missing and unlisted records, the F1 plants, the N1 `--config` on a `$(CC)` line (with the wasmtime lines still clean), `make-n.txt`, and a removed autoconf Makefile.
- **F4, departure accepted.** The line is joined to the existing second not-machine-checked line instead of added as a third. A unit test pins the two-line shape, and the text is the one Decision 4 asked for.
- **F5, fixed.** The cause of the growth is labelled INFERRED, beside the measured section numbers.
- The git tree is untouched (`git status` clean).

**Confirmed: lands.** F1 to F5 are fixed or answered. The lane accepts with `--accept`, `--accept-judge`, `--retire tests/checks/test_rules.py::test_x86_64_compiles_with_an_aarch64_compiler` and `--accept-growth` with the measured bytes.
