# Review of 012 — The same bytes from any host (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author or the implementer. I read `AGENTS.md`, the constitution, the reviews README, the 010 build review (for its format), the pre-build review of 012 with its dispositions and confirmation, the specification with its landing notes, the memo `2026-10-17-x86-64-rebuilds-differ-in-one-function.md` and every file in its evidence folder, and the whole diff. I did not rely on the landing notes; each claim below was checked as labelled.
- **Reviewed:** the scratch clone at `9512e3a` plus its uncommitted change (45 files, +1,736 −53). `spec012.patch` is byte-identical to the clone's `git diff HEAD` (EXECUTED: `cmp`). The container builds ran commit `15dd872` of `build012/linux-src`; its `scripts/`, `recipes/` and `downloads/SHA256SUMS` diffs equal the clone's. Only the workflow, the scan and its unit test differ: they are the two-runner version, before the fallback (EXECUTED: per-path `git diff` compared).
- **Re-ran (EXECUTED, darwin-arm64, in the clone).** Scripts and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev012b/` (`tools/`, `out/`).
  - `uv run pytest` (no `--accept`): `129/132 pass · 0 gap · 3 blocked · 0 fail`, unit suite 220/225 with 5 skipped, `349 passed, 8 skipped`. Ratchet against `ab9bafd727`: `lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 5 · grew 16`, judge changed, `RED: 16 metric(s) grew`, exit 1. This is the landing notes' scoreboard, line for line.
  - `uv run ruff check src tests` and `uv run ruff format --check src tests`: both clean.
  - The tracked tree was hashed before and after all runs and mutations: equal (`status-before.txt`, `diff-before.sha`, `tree-before.sha`). Mutated files were restored byte for byte and their mtimes reset. `build/progress/latest.json` holds my unmutated full run.

## Acceptance criteria against evidence

1. *The five new checks seen failing before the change; the gap's check passes; its entry is gone.* **Met.**
   - READ: `build012/seen-failing-first.log` shows the four goal checks and the five `test_line` cases failing on the old recipe and set, with the findings the notes quote (5, 1, 2, 9).
   - EXECUTED: the mutations below make each new check fail again (M1 to M17, Z1 to Z7, P1).
   - EXECUTED: `test_toolchain_is_pinned_for_linux_and_macos` passes; its `known_gaps.toml` entry is removed in the diff.
2. *macOS and Linux aarch64 from empty `downloads/` and `build/` give the same `SHA256SUMS`; x86_64 the same, or the fallback recorded.* **Met, with the fallback.**
   - EXECUTED: the clone's `build/artifacts` passes `shasum -c SHA256SUMS`. `SHA256SUMS` is `e51434a7…`. The sizes and the four hashes in the landing notes' table are exact.
   - EXECUTED: `cmp` of the clone's `SHA256SUMS` with `out-aarch64/artifacts/SHA256SUMS`: equal. The reactor, snapshot, zip and `MANIFEST` are byte-equal too.
   - EXECUTED: `out-x86_64` differs in exactly the two lines the notes give (`36c65478…`, `568b9db7…`). `cmp -l` of the two reactors gives 21 bytes, identical to `outputs/reactor-cmp-macos-vs-x86_64.txt`.
   - READ: `downloads.txt` per host. aarch64 and x86_64 fetched only their own five inputs plus the shared ones. The clone's `downloads/` holds 26 pins: macOS's own and the shared ones.
   - The build outputs in the evidence folder equal the scratch originals (EXECUTED: `cmp`).
3. *`uv run pytest` green with `--accept-judge` and the new bytes accepted; the fast tier passes in the Linux container.* **Met, pending the author's accept.**
   - EXECUTED: the 16 growths above the 0.01% fuel tolerance are the landing notes' 16 values, exactly. Five more fuel changes are below the tolerance. 18 metrics shrank, as stated (`out/metrics.txt`).
   - READ: `judge-fast-linux-aarch64.txt`: `125/132 pass · 0 fail`, exit 0. It ran the pre-fallback judge (commit `15dd872`). The only difference is the workflow scan, which does not depend on the host.
4. *A dry run passes every job, and `same-bytes` reports equal sets.* **Not met** (finding 1).

## What holds

- **The host table and the three readers agree** (READ, EXECUTED).
  - `line.conf` has five names for each of `MACOS_ARM64`, `LINUX_AARCH64` and `LINUX_X86_64`, and no plain host name.
  - `line.sh` (`uname`), `line.py` (`platform`) and the `case` in `00_download.sh` name the same three keys. `Linux-arm64` maps to `LINUX_AARCH64` in both readers.
  - Every `get` line in a branch fetches that host's own file. All twelve new pins are in `SHA256SUMS`, and each hash appears in the Linux memo's table (EXECUTED: `grep` per hash).
  - `line.py` on a foreign host sets no host name and raises nothing. `host_python_archive()` raises `RuntimeError`, which `oracle_available()` catches (EXECUTED: `test_line.py`, and M7).
- **Step 10 replaces the runtime, and step 60 proves the link used it** (READ, EXECUTED).
  - Step 10 refuses unless `lib/clang/*` is exactly one directory. It removes and re-unpacks `share/wasi-sysroot` and the `wasm32-unknown-wasip1` builtins.
  - The link map names the three archives as `…/bin/../share/…`. Step 60 resolves each path with `realpath`, requires it under the replaced directory, and hashes it against the member of the pinned neutral tarball, read without unpacking.
  - EXECUTED (`tools/members.py`): the neutral members hash to `d4527e52…`, `53a077fc…` and `b1e23c03…`. These equal `build/link/runtime-check.log`.
  - EXECUTED (`out/linkmap.txt`): I ran step 60's own heredoc on the real map (pass) and on four mutated maps (each refused; see the table).
- **The zip rewrite is complete and refuses what it cannot do** (EXECUTED: `out/neutral.txt`, and the R rows below).
  - On the real members, the key rewrite changes only `BUILD_GNU_TYPE` and the five `INSTALL*` keys (`GNULD` and `MKDIR_P` already held their fixed values on macOS). In numpy, it changes only `cpu`, `family` and `system`.
  - The script reads its own output back. A value split across two lines is still rewritten and reads back as fixed (N5).
  - I re-ran `make_stdlib_zip.py` on the build's own two members, with step 70's five computed rewrites in the stated order. Both resulting `.pyc` members are byte-equal to those in the built zip.
  - EXECUTED: three hosts, three repository paths (the clone, `/work/wasi_python` twice), one zip hash. So nothing host-specific is left in the zip that differs between these hosts.
- **What the guest now prints** (EXECUTED: `out/guest-sysconfig.txt`, a plain-reactor run through `wasi_python.run`).
  - `sysconfig`: `BUILD_GNU_TYPE='build'`, `GNULD='no'`, `MKDIR_P='mkdir -p'`, `INSTALL='install -c'`, `INSTALL_DATA='install -c -m 644'`. `CONFIG_ARGS` holds `--build=build` and `cross-build/build/python`. `CC` names `/wasi-python-build/build/tools/wasi-sdk/bin/clang`.
  - `sysconfig.get_platform()` is `wasi-0.0.0-wasm32`, unchanged.
  - `numpy.show_config()`: the build machine is `cpu: build, family: build, endian: little, system: build`. The host machine is `wasm32 … wasi`, unchanged.
  - This is what the README and the CHANGELOG say.
- **The directory pin cannot reach a program, and the check shows it on macOS** (READ, EXECUTED).
  - `pin_filestat` sets a directory's `size` 0 and `nlink` 1 only while `pinned`, which `wizer_initialize` and `run()` clear (`reactor_main.c:89-100,203,279`).
  - EXECUTED: a one-file directory on APFS stats as `96 3`. A leaked pin would print `0 1`, so the v1.4 check would fail on macOS. It passes on both binaries.
- **The builder-path deviation is right** (EXECUTED).
  - `main`'s reactor holds `/Users/runner/work/wasi-sdk` once and `/src/src/llvm-project` never.
  - The new reactor holds `/src/src/llvm-project/libcxxabi/src/{fallback_malloc,private_typeinfo}.cpp` and not the macOS path. The x86_64 reactor passes the check too.
  - So refusing `/src/src/llvm-project` would fail the correct bytes. On Linux the output check cannot tell the runtimes apart. Step 60's hash check is the guard there, and it holds.
- **The workflow** (READ, EXECUTED).
  - `rebuild`: matrix `[ubuntu-24.04-arm]`, `fail-fast: false`, `runs-on: ${{ matrix.os }}`, no job `if:`, no job `permissions:` (the workflow's `contents: read` applies). It runs `00_download.sh` and `build.sh` from a fresh checkout, prints its tools, and uploads `build/artifacts/SHA256SUMS` as `rebuild-${{ matrix.os }}` with `if-no-files-found: error`.
  - `same-bytes`: `needs: [build, rebuild]`, no `if:`, no `id-token`. It downloads `release-assets` and `rebuild-ubuntu-24.04-arm`, unpacks the `.tar.xz`, and `cmp`s.
  - `attest` needs `[build, verify, same-bytes]` and `publish` needs `[build, verify, same-bytes, attest]`. `pypi` needs `publish`, so it waits for the gate too.
  - EXECUTED (`sim/`): I made a real `.tar.xz` with `release/version.py`'s `write_assets` and ran the step's script under `bash -e`. With the aarch64 container's `SHA256SUMS` it exits 0. With x86_64's it exits 1 (`differ: char 864, line 11`). With none it exits 2.
  - The arm-only fallback is consistent in the workflow, the scan, the README, the CHANGELOG, the Intent and the memo. Only the specification's Decision 7 and Design block still say two runners (finding 3).
- **The v1.4 directory check on `windows-2025` should pass** (READ, INFERRED).
  - READ (wasmtime 49.0.3, `crates/wasi/src/filesystem/windows.rs:116-147`): `stat_at` opens the path with `FILE_FLAG_BACKUP_SEMANTICS`, then `stat` builds `Metadata::from_file`. The link count is `winx` file information's `number_of_links()` (`primitives/windows/fs/metadata_ext.rs:16-18`): `GetFileInformationByHandle`'s `nNumberOfLinks`. The size is `std`'s `len()` (`primitives/metadata.rs:53`), from the same call's `nFileSize`.
  - INFERRED: CPython's `os.stat` on Windows reads the same two fields, from `GetFileInformationByHandle` or `GetFileInformationByName`'s `NumberOfLinks` and `EndOfFile`. On NTFS a directory has one link and size 0. So both sides say `0 1`, and the check passes. As the check's docstring says, it cannot tell pinned from real there.
  - Caveat: the judge runs wasmtime-py 49.0.0, and I read 49.0.3's source. INFERRED that 49.0.0 reads the same handle information. The dry run is the proof.
- **The x86_64 fallback and its memo** (EXECUTED, READ).
  - The 21 bytes lie at file offsets 0x1610c91 to 0x1610cd1. The link map puts `npy_cpowl` at 0x16107d1, size 0x724, so they are inside it (EXECUTED: `grep` of `python.map`). Code offsets come before the debug sections that `llvm-strip` removes (INFERRED).
  - The disassembly diff swaps frame offsets 112 and 160. The instruction offsets shift by one byte inside the function, because 160 takes two LEB128 bytes and 112 one. That fits "same instructions, same size" (READ).
  - Attempt 1, NaN canonicalization, was run directly, and Wizer was host-independent with and without the flag (READ: `wizer-x86_64.txt`). Attempt 2 was a diagnosis, not a second fix. That is a fair use of rule 7: the cause is in the per-host compiler binary, which no recipe flag is known to steer, and the memo says why it tried none.
  - The FMA explanation and "Rosetta reproduces x86" are labelled INFERRED, as they should be.

## Mutation table

Each mutation weakened one check's subject in the clone, ran the named check, and was restored byte for byte (EXECUTED: `tools/mutate.py`, `mutate2.py`, `mutate3.py`, `out/mutations.txt`). The Z and P rows used a copy of the artifact set through `WASI_PYTHON_ARTIFACTS`.

| # | Mutation | Check | Result |
|---|---|---|---|
| M1 | `LINUX_X86_64_NINJA_WHEEL` removed from `line.conf` | host table | **fails**: `no LINUX_X86_64_NINJA_WHEEL` |
| M2 | aarch64 and x86_64 ninja `get` lines swapped between branches | host table | **fails**: 2 findings, `not fetched in the LINUX_AARCH64 branch` |
| M3 | `Linux-x86_64` key removed from `line.sh` | host table | **fails**: `line.sh: hosts [...]` |
| M4 | `("Linux", "x86_64")` removed from `line.py` | host table | **fails**: `line.py: hosts [...]` |
| M5 | x86_64 ninja wheel's pin removed from `SHA256SUMS` | host table / toolchain | **fails**: `is not pinned` / passes (narrower, as expected) |
| M6 | a plain `NINJA_WHEEL=` added to `line.conf` | host table | **fails**: `set for every host` |
| M7 | `line.py` raises `SystemExit` on a foreign host | `test_line.py` | **fails**: 2 of 5 |
| M8 | `same-bytes` dropped from `attest`'s needs | rebuild scan / 009 scan | **fails** / passes (as expected) |
| M9 | `same-bytes` dropped from `publish`'s needs | rebuild scan | **fails** |
| M10 | `if: github.ref_type == 'tag'` on `rebuild` | rebuild scan | **fails** |
| M11 | `permissions: id-token: write` on `same-bytes` | rebuild scan | **fails** |
| M12 | matrix `[ubuntu-24.04]` | rebuild scan | **fails** |
| M13 | `same-bytes` needs only `build` | rebuild scan | **fails** |
| M14 | `cmp … \|\| true` | rebuild scan | **fails** |
| M15 | `cmp` replaced by `echo` | rebuild scan | **fails** |
| M16 | `SHA256SUMS` uploaded as plain `rebuild` | rebuild scan | passes (the logs upload's name satisfies the rule); fails closed at run time: `same-bytes` finds no artifact |
| M17 | `same-bytes` downloads `rebuild-ubuntu-24.04` | rebuild scan | passes; fails closed at run time: no such artifact |
| M18 | `cmp "$sums" set/wasi-python-*/SHA256SUMS` (the set against itself) | rebuild scan | **passes: fails open** (finding 2) |
| M19 | `same-bytes` never downloads the rebuild | rebuild scan | passes; fails closed at run time (`cmp` exits 2) |
| M20 | `continue-on-error: true` on the rebuild's build step | rebuild scan | passes; fails closed at run time (`if-no-files-found: error`) |
| Z1 | `aarch64-apple-darwin` appended to `_sysconfigdata` | zip check | **fails**: `darwin`, `apple`, `aarch64` |
| Z2 | `system linux` appended to numpy's `__config__` | zip check | **fails**: `linux` |
| Z3 | the repository path appended to `_sysconfigdata` | zip check | **fails** |
| Z4 | `/usr/bin/install -c` appended | zip check | **fails**: `/usr/bin` |
| Z5 | `x86_64` appended to numpy's `__config__` | zip check | **fails** |
| Z6 | numpy's `__config__.pyc` removed | zip check | **fails**: `not in the zip` |
| Z7 | `main`'s zip | zip check | **fails**: 9 findings |
| Z8 | the x86_64 container's zip | zip check | passes (correct) |
| P1 | `main`'s reactor | builder-path check | **fails**: `/Users/runner/work/wasi-sdk` |
| P2 | the x86_64 container's reactor | builder-path check | passes (correct) |
| N2 | `GNULD` removed from `_sysconfigdata` | `host_neutral` | **stops**: `no GNULD to make host-neutral` |
| N3 | `INSTALL` set to `cp -p` | `host_neutral` | **stops**: `not an install -c command` |
| N4 | numpy's build `family` removed | `host_neutral` | **stops**: `no family` |
| R1 | the triple rewritten before the build-Python's path | `make_stdlib_zip.py` | **stops**: `--replace 'cross-build/…/python.exe': in neither` |
| R2 | the Linux SDK name passed on macOS | `make_stdlib_zip.py` | **stops**: `in neither` |
| R3 | numpy's member not given | `make_stdlib_zip.py` | **stops**: `no member to make host-neutral` |
| L1 | the link map points at the macOS tarball's own `libc++.a`/`libc++abi.a` | step 60 heredoc | **stops**: `is not the neutral tarball's` |
| L2 | `libc++.a` from outside the sysroot | step 60 heredoc | **stops**: `is not under` |
| L3 | two `libc++abi.a` in the map | step 60 heredoc | **stops**: `names 2` |
| L4 | no builtins in the map | step 60 heredoc | **stops**: `names 0` |
| D1 | the reactor leaks the directory pin to a program | v1.4 directory check | INFERRED **fails** on macOS and Linux: the guest would print `0 1`, the host `96 3` (APFS, EXECUTED) or `4096 2` (ext4). Not run: needs a rebuild |

## Findings, most severe first

1. **Criterion 4 is not met: no new CI job has run on GitHub** (`release.yml:86-161`; landing notes, "Left over"). Medium.
   - The `rebuild` job on `ubuntu-24.04-arm`, the `same-bytes` download and compare, and the Windows run of the changed v1.4 check have never run there.
   - What reduces the risk: the container build used the same scripts (EXECUTED); my local run of `same-bytes`' script on a real `.tar.xz` behaves right (EXECUTED); and the Windows reading above says pass (INFERRED).
   - What is still open (INFERRED): the runner's own gcc 13 and path. The research showed gcc 14.2 and Apple clang give the same bytes, and the build-Python's compiler reaches no artifact. A difference would block every release, and `same-bytes` would say so.
   - Spec 009 landed before its dry run and recorded the dry run after (`b41ac52`). If the author lands the same way, the landing notes must say criterion 4 is open. Run the dry run before any tag, and record the job results in the specification.
2. **The workflow scan passes a `same-bytes` that compares the set with itself** (`tests/harness/scan.py:589-597`). Low.
   - EXECUTED (M18): `cmp "$sums" set/wasi-python-*/SHA256SUMS` passes the scan. Such a job always reports equal bytes. That is the one way to break the gate that fails open.
   - The scan asks only for `cmp` and `SHA256SUMS` on one line, and for the runner's name anywhere in the job. M16, M17 and M19 also pass the scan, but each of them fails closed at run time.
   - Fix: for each gated runner, require a download step with `name: rebuild-<runner>` and a `cmp` whose operands include that step's `path`. Add M18 to `BAD_REBUILDS`.
3. **The specification's Decisions still describe the plan, not the build** (`012` Decision 2, Decision 7, Design). Low.
   - Decision 7 says "a matrix of `ubuntu-24.04-arm` and `ubuntu-24.04`" and "both runners in the matrix". The Design block says "rebuild (two runners)". Decision 2 says the check refuses `/src/src/llvm-project`.
   - The landing notes record both deviations. A later reader of the Decisions alone is misled.
   - Fix: one line in each place, pointing to Decision 8's fallback and to deviation 1.
4. **Two pieces of evidence live only in the scratch folder** (`build012/seen-failing-first.log`; `build012/out-*/downloads.txt`). Low.
   - The "seen failing first" claims (criterion 1) and "fetched only its own inputs" (criterion 2) cite runs whose outputs are not in the patch. Constitution §4.10 asks a claim to carry its evidence.
   - Fix: copy the log and the two `downloads.txt` into `context/research/2026-10-17-the-x86-64-rebuild/outputs/`. Say in the notes that the Linux fast tier ran the pre-fallback judge (`15dd872`), which differs only in the workflow scan.
5. **Two prose lines overflow the wrapping around them** (`README.md:180`, `CHANGELOG.md:58`). Nit.
   - README line 180 is 165 characters inside a paragraph wrapped near 96. CHANGELOG line 58 is 118, and it is the only line over 100 in that file (EXECUTED: `awk`).
6. **`make_stdlib_zip.py` does not refuse an empty `--replace` old text** (`scripts/make_stdlib_zip.py:206-207`). Nit.
   - `"" in text` is true, and `str.replace("", new)` would insert `new` between every character.
   - Unreachable today: `line.sh` stops on an empty host name, and step 70 stops when it finds no build-Python. One `if not old` line would make the script safe on its own.

## Constitution checks

- §4.1 zero patches: holds. EXECUTED: the four zero-patch checks pass in the full run. Step 10 changes a downloaded binary SDK under `build/tools/`, not a source tree. The other changes are recipe files (`reactor_main.c`, `make_stdlib_zip.py`, the steps).
- §4.2 pinned and hashed: holds. Twelve new pins, each a literal `get` line and a `SHA256SUMS` line, each matching the Linux memo (EXECUTED). The clone's 26 local files verify (EXECUTED: `shasum -c --ignore-missing`, 26 OK). The runners' tools stay unpinned, as Decision 10 says, and the job prints their versions.
- §4.3 one target: holds. The per-host branches are in the build recipe, never in the guest.
- §4.6, artifacts not in git: holds. EXECUTED: the patch has no binary hunk and no `.wasm`, `.zip`, `.tar.*`, `.whl` or `.pyc` path. Hashes and sizes live in the notes and the memo.
- §4.9 tests count: holds. Every new check compares bytes, hashes, names or the host's own stat answers. Times appear only in the memo, as benchmark facts.
- §4.10 claims carry evidence: holds, but for finding 4. Each landing-note number I checked was exact.
- §4.11 platform semantics: holds. The README says `sysconfig` and `numpy.show_config()` name the build machine `build`. EXECUTED: the guest prints exactly that.
- §4.13 uv only, ruff and pytest green: holds on `src/` and `tests/`. `scripts/` has old ruff findings in the bench scripts and one long docstring line in `make_stdlib_zip.py:8`, none new.
- §5.6 review: this is the build review. The pre-build review's N1 to N5 are closed: N1 (EXECUTED, `realpath`), N2 (`x-pins`, and v1.1 passes), N3 (the old check stays and passes), N4 (one name per runner), N5 (the read-back, and bare `linux` for numpy).
- §7: nothing tripped. No commit, push, tag or publish. The main tree was only read; a `git apply --check` there (read-only) shows the patch applies, except the new specification, which already exists there as an untracked file. The author must replace that copy.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **Finding 1 — answered.** As with spec 009, 012 lands before its dry run. The landing notes say criterion 4 is open. The dry run is dispatched right after the push, and its result is recorded before any tag. A red dry run is fixed before anything else lands.
2. **Finding 2 — fixed.** `rebuild_gate_errors` now:
   - requires a `cmp` whose two operands are one rebuild's download and one not;
   - requires each gated runner's download step (`name: rebuild-<runner>`, `path: rebuilds/<runner>`) and the runner's name in the compare script.

   The unit test's sample workflow mirrors the real `same-bytes` job. It gains M18 (`cmp "$sums" "$sums"`) and a moved download path as bad cases. EXECUTED: `test_scan.py` 59 passed, and the real workflow scans clean.
3. **Finding 3 — fixed.** Decision 2 and Decision 7 each carry a one-line pointer to the recorded deviation, and the Design block says "arm64 only, Decision 8".
4. **Finding 4 — fixed.** `seen-failing-first.txt` and the three hosts' `downloads-*.txt` are in `context/research/2026-10-17-the-x86-64-rebuild/outputs/`, with no home path in them. The landing notes say the Linux fast tier ran the pre-fallback judge.
5. **Finding 5 — fixed.** Both added lines are wrapped.
6. **Finding 6 — fixed.** `make_stdlib_zip.py` refuses an empty `--replace` old text.

## Reviewer's confirmation (2026-10-17, against the revised clone)

I re-read the revised `rebuild_gate_errors`, `make_stdlib_zip.py`, the specification and the new evidence files. I re-ran the mutations below and the whole judge in the clone, then restored every file byte for byte, with its mtime (EXECUTED: tree, status and diff hashes equal before and after; `tools/mutate4.py`, `out/confirm-mutations.txt`, `c2/pytest.txt`). I did not touch the main repository.

1. **Confirmed.** The Status and "Left over" say criterion 4 is open, and the plan matches spec 009's precedent. One stale line: "Left over" still says wasmtime's Windows answer "was not checked". The review read it (INFERRED pass); the author may cite that, but it is not a blocker.
2. **Confirmed.** EXECUTED, on the real workflow:
   - The unmutated job passes. M18 (set against the glob), M18b (`"$sums"` twice), M18c (a rebuild against itself) and M15 (`echo`) each fail: `does not compare a rebuild's SHA256SUMS with the set's`. M14 (`|| true`) fails.
   - M17 (wrong artifact name), M19 (download removed), M21 (download path moved) and M22 (the loop no longer names the runner) each fail: `does not name ubuntu-24.04-arm's SHA256SUMS`.
   - M16 (the upload named plain `rebuild`) still passes the scan. It fails closed at run time, and the disposition did not claim it. Not a blocker.
   - `test_scan.py` passes; `ruff check` and `ruff format --check` on `src/` and `tests/` are clean.
3. **Confirmed.** Decisions 2 and 7 each carry an "As built" sentence. The Design block says "arm64 only, Decision 8".
4. **Confirmed, with one correction.** `seen-failing-first.txt` is byte-identical to the scratch log. `downloads-aarch64.txt` and `downloads-x86_64.txt` equal the container lists. The notes say the Linux fast tier ran the pre-fallback judge. But the disposition's "with no home path in them" is not true: `seen-failing-first.txt` lines 41 and 56 hold the scratch path `/private/tmp/claude-501/-Users-claygendron-…/old-artifacts` (EXECUTED: `grep`). Strip those two paths or drop the claim. It is a nit.
5. **Confirmed.** The added README and CHANGELOG lines wrap. The one README line over 100 near there (173) is an old code line. One new long line was added: the landing notes' sentence ending "Evidence for the Linux" is about 150 characters (nit).
6. **Confirmed in effect, disputed in form.** The refusal sits after `add()` has already applied the replacements.
   - EXECUTED: `--replace "="` stops with `--replace with an empty old text`, exit 1.
   - EXECUTED: `--replace "=x"` inserts `x` between every character first. The build then stops on a `SyntaxError` traceback from `compile`, not on the one-line refusal. It still fails closed, and no zip is written.
   - Moving the check to where `replacements` is parsed would give the one line in both cases. A nit; not a blocker.

**New point from the fix (Low, for the landing notes).** Finding 6's fix changes `scripts/make_stdlib_zip.py`, which `MANIFEST` lists as a `recipe` line.
- EXECUTED: the clone's judge now reports `test_manifest_recipes_match_the_tree` failing with `stale artifact: scripts/make_stdlib_zip.py changed since the build`.
- It also reports `test_landed_specifications_cite_an_existing_review` failing, because this review is not yet in the clone. Both are expected in the clone, and the main tree's rebuild and the review's move clear them.
- But `MANIFEST`'s hash (`69f776d8…`) and `SHA256SUMS`' (`e51434a7…`) in the landing notes will change. So will the claim that the aarch64 container's `SHA256SUMS` equals macOS's, which was made for the old `MANIFEST`.
- EXECUTED: the fixed script, given the build's two members and step 70's five rewrites, writes `.pyc` members byte-equal to the built zip's. So the reactor, the snapshot and the zip should not move (INFERRED for the whole zip).
- Record the main-tree rebuild's `MANIFEST` and `SHA256SUMS` hashes in the notes. Say the Linux equality now rests on `MANIFEST` being host-neutral by construction (INFERRED) until the dry run's `same-bytes` proves it.

**Updated verdict: it lands.** Each finding is fixed or answered. The fail-open scan gap is closed, and every mutation I doubted now fails. The remaining points are nits and a notes update for the new `MANIFEST` and `SHA256SUMS` hashes. None blocks landing, provided the dry run runs before any tag.

## Verdict

**It lands once findings 2 to 4 are fixed or answered, and the landing notes state that criterion 4 is open until the dry run.** The build does what the specification decided. macOS and arm64 Linux give one artifact set, byte for byte. Every new check fails on a weakened subject, but for the one fail-open scan gap in finding 2. The x86_64 fallback is evidenced and honestly bounded.

One line: the same bytes from macOS and arm64 Linux are real and well guarded; close the scan's self-compare gap, align the Decisions with the build, keep the evidence in the repo, and run the dry run before any tag.
