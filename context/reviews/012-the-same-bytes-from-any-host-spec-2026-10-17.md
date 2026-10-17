# Review of 012 — The same bytes from any host (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the
  constitution, the reviews README, the 009 pre-build review (for its format), the specification,
  the memo `2026-10-16-reproducible-builds-on-linux.md` and its evidence folder (`edit.py`,
  `outputs/recipe-edits.diff`, `zip-diff.txt`, `runs.txt`, `sdk-runtime-diff.txt`), the recipe
  (`scripts/line.conf`, `line.sh`, `line.py`, `00_download.sh`, `build.sh`, `steps/*`,
  `make_stdlib_zip.py`, `assemble_artifacts.py`, `python-wasi-cross`), `recipes/reactor_main.c`,
  `.github/workflows/release.yml`, `release/version.py`, `downloads/SHA256SUMS`,
  `tests/known_gaps.toml`, `tests/checks/test_v1_5_rebuild_from_pins.py`, `tests/harness/scan.py`,
  `tests/harness/jobs.py` and `tests/harness/needs.py`. I did not rely on the author's summary.
- **Reviewed:** `context/specifications/012-the-same-bytes-from-any-host.md` (draft, untracked),
  against the working tree at `ab9bafd` plus its uncommitted changes.
- **Ran (EXECUTED, darwin-arm64).** Scripts and outputs are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev012a/`
  (`tools/`, `out/`). No tracked file but this review was written. Nothing under `build/` was
  written; I only read `build/artifacts/` (copied the zip out) and ran the pinned
  `wasmtime -W help`.
  - `shasum -a 256` on the research agent's copies of `wasi-sysroot-33.0+m.tar.gz`,
    `libclang_rt-33.0+m.tar.gz`, `wasi-sdk-33.0-arm64-linux.tar.gz` and
    `wasi-sdk-33.0-x86_64-linux.tar.gz`: all four equal the memo's pins.
  - `tools/cmptrees.py`: every file of the neutral sysroot and builtins, hashed against the
    `share/wasi-sysroot` and `lib/clang/22/lib` of the three host SDK tarballs
    (`out/runtime-trees.txt`). `tools/cmpinc.py`: the three SDKs' `lib/clang/22/include`.
  - The edited `line.py` and `line.conf` from `recipe-edits.diff`, applied to a scratch copy, and
    called with `platform` reporting `Windows-AMD64` and `Darwin-x86_64` (`win.py`).
  - `tools/members.py`, `tools/sysvars.py`, `tools/npcfg.py`: the two host-fact members of the
    current `build/artifacts/python-stdlib.zip`, unmarshalled with the pinned 3.15.0 host Python
    unpacked into the scratch folder (`out/members-scan.txt`, `out/sysvars-hosttools.txt`).
  - `tools/features.py`: the reactor's `target_features` section.
  - `gh run view 39008367705`: the last dry run's job times and step lines.
  - `harness.scan.spec_shape_errors` and `open_question_hits` on the specification: both `[]`.
  - I did not run `uv run pytest`. It writes under `build/`, which this review must not touch.
    The scoreboard is the build review's job.

## What holds

- **Zero upstream patches** (READ). Decision 2 changes an unpacked binary toolchain under
  `build/tools/`, not a source tree. Decisions 4 and 5 change our recipe files
  (`reactor_main.c`, `make_stdlib_zip.py`, step 70). The zero-patch check's four trees are
  untouched.
- **Pins and literal `get` lines** (READ, EXECUTED). Each Linux pin is a literal `get <url> <name>`
  line in a `case` branch. `scan.GET` is `^\s*(?:get|research)\s+…` with `re.M`, so an indented
  line counts (`scan.py:160`). I re-hashed the four SDK and neutral tarballs; they match.
- **No other macOS name in the recipe** (EXECUTED: grep of `scripts/`, `recipes/`, `release/`,
  `.github/`). Beyond `line.conf` and the ninja wheel in step 10, only comments name macOS. In the
  tests, macOS names appear only as unit-test fixtures and in `toolchain_errors`.
- **The overlay replaces exactly the runtime, and nothing is lost** (EXECUTED,
  `out/runtime-trees.txt`).
  - Every host tarball's `share/wasi-sysroot` has 18,282 files. The neutral sysroot has the same
    paths plus one `VERSION` file. So the experiment's `rm -rf` then unpack drops no host file.
  - Every header and the `libc.a` the build links are equal. On macOS, 24 `wasm32-wasip1` files
    differ: `eh/` and `noeh/` libc++, libc++abi, libc++experimental, `libc.so`, and the `llvm-lto/`
    variants. The build links none of the `.so` or `llvm-lto` files.
  - The x86_64 Linux tarball's whole runtime, sysroot and builtins, is byte-equal to the neutral
    tarballs. The neutral set is that build. So cause 1 cannot exist on x86_64.
  - The aarch64 Linux tarball differs from neutral only in `libc.so` (unused) and the builtins.
  - Clang's own headers (`lib/clang/22/include`, 267 files) are equal on all three hosts. So
    `-resource-dir` was not needed, and the overlay is the right choice.
- **Nothing in the judge or the guest reads the rewritten keys** (EXECUTED grep, READ). No file in
  `tests/`, `src/` or `recipes/` names `sysconfig`, `show_config`, `get_config_var` or
  `get_platform`. CPython 3.15's `sysconfig.get_platform()` takes its answer from `os.uname()`
  or `_PYTHON_HOST_PLATFORM`, not from `BUILD_GNU_TYPE`, `GNULD`, `MKDIR_P` or `CONFIG_ARGS`
  (`Lib/sysconfig/__init__.py:641-720`). `numpy.show_config()` would print `build` for the build
  machine. That is true and harmless.
- **The pin of a directory's size and nlink cannot reach a program** (READ, INFERRED).
  `pinned` starts at 1. `wizer_initialize` sets it to 0 after the imports (`reactor_main.c:196`).
  `run()` sets it to 0 before any interpreter start (`:272`). So the plain reactor's interpreter
  never sees a pinned stat. What a pinned directory stat could leave in a snapshot is a cached
  value. CPython caches no directory `stat_result`. getpath uses `isdir` booleans. zipimport
  stats only the zip, a file. `FileFinder` caches a directory's mtime, which is already pinned
  today. Nothing at start-up reads `st_nlink`. So the change moves heap layout only, as the memo
  measured.
- **The reactor has no SIMD** (EXECUTED: `target_features` lists bulk-memory,
  exception-handling, multivalue, reference-types, sign-ext and the rest, but no `simd128` or
  `relaxed-simd`). So relaxed-SIMD's host-dependent results cannot reach the snapshot.
- **A Linux rebuild job fits the runners** (EXECUTED, INFERRED). The last dry run's macOS build
  ran steps 00 to 90 in 7 min 18 s on `macos-15` (06:01:49 to 06:09:07). The memo's Linux build
  took 185 to 212 s on 10 CPUs. `build/` is 3.2 GB here, of which about 1.4 GB is judge and
  cwasm caches; `downloads/` is 446 MB. INFERRED: a 4-vCPU `ubuntu-24.04` or `ubuntu-24.04-arm`
  runner builds in 10 to 20 minutes with disk to spare. Both images carry gcc, make, curl, xz and
  perl's `shasum`, and glibc 2.39 meets the Cython wheels' `manylinux_2_28`.
- **The specification's shape is sound** (EXECUTED: `spec_shape_errors` and
  `open_question_hits` return `[]`).

## Acceptance criteria against evidence

1. *The zip check and the workflow scan seen failing first; the gap's check passes and its entry
   is gone.* Checkable. The zip check as worded would also fail after the change (finding 3).
2. *A local macOS build and a local Linux aarch64 build give the same three hashes.* Checkable.
   It does not exercise a build from a `downloads/` holding only one host's files (finding 11).
3. *`uv run pytest` green with `--accept-judge` and the new hashes accepted.* Checkable. The
   accept flags must also cover fuel (finding 9).
4. *A dry run passes every job, and both rebuild jobs report the macOS hashes.* Not checkable as
   designed: the file the jobs compare with does not carry two of the three hashes (finding 2).
   As drafted, the windows-2025 verify job would also go red (finding 1).

## Findings, most severe first

1. **The host-aware `line.py` raises `SystemExit` on any other host, and the judge's oracle runs
   on Windows in CI** (`012` Decision 1; `edit.py` edit 3; `tests/harness/jobs.py:66-75,121-133`).
   High.
   - EXECUTED (`win.py`): the experiment's `line.read()` with `platform` set to `Windows-AMD64`
     raises `SystemExit: no line for host Windows-AMD64`. It does the same on `Darwin-x86_64`.
   - READ: `oracle_available()` catches only `(OSError, RuntimeError)`. `SystemExit` is a
     `BaseException`, so it passes through. `needs.need("oracle")` is called by
     `test_v1_3_data_stack.py:145`. The `verify` job runs that file on `windows-2025`.
   - Failure: the Windows verify job calls `need("oracle")`. Today that is a clean skip, because
     the archive is missing (`RuntimeError`), and the job allows `oracle` among blocked needs.
     After the change, the test fails. The empty-baseline run turns red, so the dry run fails.
     A developer running the judge on Windows or on an Intel Mac hits the same failure.
   - The specification says every reader of a plain name "is unchanged, including the judge's
     oracle". That holds only on the three build hosts.
   - Fix (pick one and say which):
     - `line.read()` resolves the host names only for a known host and otherwise leaves them
       unset. `host_python_archive()` then raises `RuntimeError` ("no host Python for this
       host"), so the oracle reads as unavailable.
     - Or `line.py` raises `RuntimeError` rather than `SystemExit`, and the build scripts turn
       it into their one-line error.
   - Add a unit test: `line.read()` under a foreign `platform` does not escape
     `oracle_available()`.

2. **Decision 7 compares with `MANIFEST`, which holds the zip's hash but not the reactor's or the
   snapshot's. The build job uploads no `MANIFEST` of its own** (`012` Decision 7;
   `assemble_artifacts.py:153-163`; `release.yml:66-71`; `version.py:155-182`). High.
   - EXECUTED: the current `MANIFEST` has `python`, `package`, `pin`, `recipe`, `x-wizer`,
     `x-source-date-epoch`, `x-preimport` and `x-snapshot-zip` lines. The SHA-256 of
     `python.wasm` occurs 0 times, of `python-snapshot.wasm` 0 times, of the zip once.
   - READ: the build job uploads one artifact, `release-assets/`. It holds the wheel, the
     `.tar.xz` of the set, and the `SHA256SUMS` of those two. `MANIFEST` is only inside the
     `.tar.xz`.
   - Failure: a job built as specified either cannot find two of its three reference hashes, or
     compares only the zip.
   - Fix: the rebuild job downloads `release-assets`, unpacks the `.tar.xz` (as `verify` does),
     and compares its own `build/artifacts/SHA256SUMS` with the set's `SHA256SUMS`, byte for
     byte. That covers all 14 files: the three artifacts, `MANIFEST` and the licences.
     `MANIFEST` is host-neutral once `SHA256SUMS` lists every host's pins (READ:
     `assemble_artifacts.py`). So the claim can be "the whole artifact set", not three hashes.
     Since `version.py assets` is deterministic, the job could also rebuild the `.tar.xz` and
     compare it with the published asset's hash. Say whether the claim covers that asset.

3. **Decision 5's rewrite rule cannot be written as literal `--replace` pairs on every host,
   and its zip check fails on today's bytes** (`012` Decision 5; `make_stdlib_zip.py:118-127`;
   `70_zip.sh`). Medium-high.
   - **Host-specific old text against "refuse a `--replace` in neither member".** `'GNULD':
     'yes'` and `'/usr/bin/mkdir -p'` exist only on Linux. `"system": "darwin"`,
     `aarch64-apple-darwin` and `python.exe` exist only on macOS. A literal pair for one host has
     no match on the other. The new refusal then stops the build, unless step 70 branches per
     host. Order matters too. If the triple is rewritten before the build-Python's path
     `cross-build/<triple>/python.exe`, the path's old text is gone, and the build is refused.
   - **The existing path rewrite survives the refusal** (READ, EXECUTED). `$HERE` is `pwd -P`,
     and the same physical path reaches configure and meson. The current members hold
     `/wasi-python-build` 15 times and 5 times after rewriting, so the old text was there.
   - Fix: make the rewrite host-neutral by key. Set `GNULD`, `MKDIR_P`, `BUILD_GNU_TYPE` and
     `INSTALL*` (below) in `build_time_vars` to fixed values whatever they were. Set numpy's
     build-machine `cpu`, `family` and `system`, keeping `endian`. Refuse a key that is
     absent. Compute the remaining text rewrites in step 70 from what the build knows, not
     from literals: the SDK and wasmtime directory names, the build triple and the
     build-Python's name under `cross-build/`. Apply them longest first, and state that order.
   - **The forbidden list hits today's bytes** (EXECUTED, `out/sysvars-hosttools.txt`).
     `INSTALL`, `INSTALL_DATA`, `INSTALL_PROGRAM`, `INSTALL_SCRIPT` and `INSTALL_SHARED` are
     `/usr/bin/install -c…` on macOS. They are not in the rewrite list, so a check refusing
     `/usr/bin` fails after the change. Either rewrite them as well (a host's `install` path is a
     host fact too) or drop `/usr/bin` from the list.
   - The member also has 20 keys such as `HAVE_LINUX_CAN_H`. So the check must be
     case-sensitive, and the specification should say so.
   - The judge runs on Python 3.14.2 (`UV_PYTHON`) and cannot unmarshal 3.15 bytecode. So the
     check scans the `.pyc` bytes for ASCII text. Say so.
   - "The host triple" should name all three build triples:
     `aarch64-apple-darwin`, `aarch64-unknown-linux-gnu`, and `x86_64-unknown-linux-gnu`
     (EXECUTED: the x86_64 host Python's `BUILD_GNU_TYPE`), plus `x86_64` itself.
   - **List numpy's fields.** EXECUTED (`npcfg.py`): the build-machine section is
     `cpu: aarch64`, `family: aarch64`, `endian: little`, `system: darwin`. Only `system` showed
     in `zip-diff.txt`, because both hosts were aarch64. On x86_64, `cpu` and `family` differ
     too. "Its other build-machine fields" should name `cpu`, `family` and `system`.
   - `zip-diff.txt` cuts each line at about 200 characters. The list of keys is complete, but
     a difference late in `CONFIG_ARGS`, `PYTHON_FOR_BUILD`, `TESTPYTHON` or `TESTRUNNER` was not
     shown. The computed rewrites cover the SDK, wasmtime and triple text in them. The zip check
     is the guard.

4. **`attest` does not wait for the rebuild, so a tag can sign bytes that then fail the
   reproducibility gate** (`012` Decision 7; `release.yml:146-152`; spec 009). Medium.
   - READ: `attest` needs `[build, verify]`. The specification adds `rebuild` only to
     `publish`. On a pushed tag, `attest` writes a permanent Sigstore entry while the rebuild
     jobs still run. If a rebuild then fails, the public log holds a signature for an asset that
     was never released. Spec 009 signs only what is about to be published, and dry runs never
     sign.
   - Fix: `attest` needs `[build, verify, rebuild]`. The 009 scan asks only that `attest`'s
     needs include `build` and `verify`, so it still passes. The new scan checks that `attest`
     and `publish` both need `rebuild`. It also checks that the rebuild jobs have no tag-only
     `if:` (a dry run must run them, criterion 4) and no `id-token`.

5. **The overlay's hash check looks at one file, and on Linux that file is the same before and
   after the overlay** (`012` Decision 2). Medium.
   - EXECUTED (`out/runtime-trees.txt`): the neutral `eh/libc++abi.a` (`53a077fc…`) equals both
     Linux tarballs'. On aarch64 Linux the overlay changes only the builtins. On x86_64 it
     changes nothing. So a check of `libc++abi.a` alone passes on Linux even if the overlay
     never ran, or ran into the wrong directory. That is exactly where a broken builtins overlay
     would hide.
   - Check what the link used, not what was unpacked. Step 60 already writes `--Map` to
     `build/link/python.map`. Read from it the paths of `libc++.a`, `libc++abi.a` and
     `libclang_rt.builtins.a`. Require each to be under the overlaid directories, with the
     neutral tarball's hash.
   - Also add an output check: refuse a reactor holding `/Users/runner/work/wasi-sdk` or
     `/src/src/llvm-project` (the builder paths of `sdk-runtime-diff.txt`).
   - Wording: the specification says `lib/clang/*/lib/wasi`. The directory is
     `lib/clang/22/lib/wasm32-unknown-wasip1` (EXECUTED listing). The experiment replaces
     `share/wasi-sysroot` whole (`rm -rf`, then unpack); it does not lay one tree over the
     other. Say "replaces". That is better, because no host file can survive.
   - Also guard `RT_DIR=$(echo "$SDK"/lib/clang/*/lib)` against more than one match.

6. **x86_64 risks the memo did not run, and what happens if one appears** (`012` Decision 7,
   Decision 9; memo "Where it stopped"). Medium.
   - **NaN bits during Wizer's initialization** (INFERRED). Wasm leaves the sign and payload of
     an arithmetic NaN to the hardware. x86_64 and aarch64 produce different bits, and wasmtime
     does not canonicalize by default. The memo compared two aarch64 hosts, so this was never
     exercised. A NaN computed (not loaded as a constant) while numpy or pandas import would
     land in the snapshot and differ on x86_64. EXECUTED: the pinned wasmtime offers
     `-W nan-canonicalization[=y|n]`.
   - Numpy's `cpu` and `family` (finding 3) and the triple `x86_64-unknown-linux-gnu`
     (EXECUTED) are known. LLVM's code generation is not expected to depend on the host CPU
     (INFERRED).
   - The gap: with `publish` needing both rebuilds, an x86_64 difference blocks every release.
     The specification should decide the response now (constitution §5.2). For example: the
     first suspect is NaN, tested with `-W nan-canonicalization=y` in step 80's flags. If that
     fails twice (`AGENTS.md` rule 7), the x86_64 key stays a pinned build host without the CI
     gate, the README says so, and a memo records why.
   - Better still, run one x86_64 build before landing: a `workflow_dispatch` run of the new
     jobs. Criterion 4 does this, but only at the end.

7. **The extended file-metadata check needs a host-true expectation, and it is a v1.4 check**
   (`012` Decision 4; `test_v1_4_embedding.py:113-123`). Low-medium.
   - READ: the check that a program sees real metadata is
     `test_v1_4_embedding.py::test_a_program_sees_real_entropy_and_file_metadata`, not v1.2.
   - INFERRED: on Windows, wasmtime reports a directory's size as 0, and its link count is
     likely 1. Those are the pinned values, and `verify` runs this file on `windows-2025`. So
     "size != 0" or "nlink != 1" fails there.
   - Compare the guest's `os.stat('/w')` size and `nlink` with the host's `os.stat` of the same
     directory. Say that on a host whose real answer is (0, 1), the check cannot tell pinned
     from real.

8. **Nothing checks that every host key is complete, or that `line.sh` and `line.py` agree**
   (`scan.toolchain_errors`; `012` Decision 1). Low-medium.
   - READ: `toolchain_errors` asks only for wasi-sdk and wasmtime pins for x86_64 Linux and
     arm64 macOS. It does not check aarch64 Linux, the host Python, Cython or ninja.
   - `url_errors` accepts a URL anywhere in the script. So a Linux aarch64 wheel placed in the
     x86_64 branch passes every check.
   - The host table is written twice, as a shell `case` and as a Python dict.
   - Suggested check: for each host key, `line.conf` has all five names. Each name is pinned
     and is fetched by a `get` line inside that key's `case` branch. The host keys in `line.sh`,
     `line.py` and `00_download.sh` are the same set.

9. **Decision 6 names only the reactor's growth** (`012` Decision 6). Low.
   - EXECUTED (`runs.txt`): in run 7 the snapshot also grew, from 63,492,577 to 63,493,889 bytes
     (+1,312), before Decision 5's effect, which no run measured.
   - The heap layout changes, so fuel may move too. The ratchet treats fuel and bytes alike
     (`context/progress/README.md:38`).
   - Say "the new sizes and fuel are accepted with `--accept-growth` when they grow", and record
     both in the landing notes.

10. **The rebuild runs after the macOS build, not beside it** (`012` Decision 7). Low.
    - INFERRED: `needs: build` adds a whole Linux build (10 to 20 minutes) to the critical path
      of every release.
    - The rebuild jobs could start at once and upload their `SHA256SUMS`. A small compare step
      (or `attest`'s first step) would then check them against the build's set.
    - It also means a failed macOS build still yields a Linux result to read.
    - Optional. Either way, decide it in the specification.

11. **No run fetched only one host's inputs** (`runs.txt`; `run-build.sh`). Low.
    - EXECUTED (READ of the run lines): every `ok 00_download` line in runs 5 and 7, on macOS
      too, ends with the x86_64 ninja wheel. Every host's files were in `downloads/`, because
      `setup.sh` and `run-build.sh` copied them all.
    - So the per-host `case` and `shasum --ignore-missing` on a `downloads/` holding one host's
      files have not run.
    - Criterion 2 should say "from an empty `downloads/` and an empty `build/`". The CI jobs do
      exactly that.

12. **`MANIFEST` will list pins the build did not use** (`012` Decision 1). Low.
    - With every host's pins in `SHA256SUMS`, a macOS `MANIFEST` names the Linux SDKs as `pin`
      lines. That keeps it host-neutral, which finding 2 relies on. But a reader may take a
      `pin` line to mean "an input of these bytes".
    - Say in the README, or in `MANIFEST`'s own description, that the pins are those of every
      supported build host, and the bytes are the same from each.

13. **Decision 7's "A Linux build also runs the judge's fast tier" does not say where**
    (`012` Decision 7). Low.
    - If it runs in the CI rebuild jobs, they need `verify`'s guard: an empty baseline, and the
      allowed blocked needs named.
    - The oracle there would read the Linux host Python (finding 1's fix keeps that working).
    - If it means the local container run of criterion 2, say that.

## Constitution checks

- §4.1 zero patches: holds (above). The overlay is of a downloaded binary toolchain under
  `build/`. State in the specification that it is not a source tree, so a later reviewer does not
  read it as a patch.
- §4.2 pinned and hashed: holds. The two neutral tarballs and ten Linux files are URL plus
  SHA-256, verified on use by `pinned`. The CI runners' tools stay unpinned host inputs, as
  Decision 9 says.
- §4.3 one target: holds. Per-host branches are in the build recipe, never in the guest.
- §4.6 the artifact set is the product: unchanged. Nothing compiled per host is published.
- §4.9 tests count: holds. Every proposed check compares bytes or hashes, never time.
- §4.10 claims carry evidence: the specification's numbers trace to `runs.txt`. The "reactor
  grows by 10 bytes" claim is right (29,802,408 to 29,802,418). The snapshot's growth is not
  stated (finding 9).
- §4.11 platform semantics documented: `numpy.show_config()` and `sysconfig` will say `build`
  for the build machine. Say so in the README.
- §5.2 no open questions: finding 6 asks for a decided fallback for x86_64.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 — Fixed (Decision 1): `line.py` sets the per-host names only on a known host and
   otherwise leaves them unset; the oracle's `host_python_archive()` then raises `RuntimeError`,
   which `oracle_available()` already catches. `line.sh` still stops a foreign build host with
   one line. A unit test runs both under a foreign `platform`.
2. Finding 2 — Fixed (Decision 7): each rebuild uploads its `build/artifacts/SHA256SUMS`, and a
   `same-bytes` job compares it byte for byte with the `SHA256SUMS` inside the set's `.tar.xz`.
   The claim is the whole set of 14 files; the `.tar.xz` asset is stated to be outside it.
3. Finding 3 — Fixed (Decision 5): `make_stdlib_zip.py` rewrites by key to fixed values
   (`BUILD_GNU_TYPE`, `GNULD`, `MKDIR_P`, the five `INSTALL*` keys; numpy's `cpu`, `family` and
   `system`, `endian` kept), refusing an absent key. The text rewrites are computed in step 70
   and applied longest first in a stated order, and a computed old text missing from both
   members stops the build. The check is case-sensitive, scans the `.pyc` bytes as ASCII
   (stated why), names all three triples' parts, and no longer trips on `/usr/bin` because the
   `INSTALL*` keys are rewritten.
4. Finding 4 — Fixed (Decision 7): `attest` and `publish` both need `same-bytes`; the scan
   checks it, and checks the new jobs have no tag-only `if:` and no `id-token`.
5. Finding 5 — Fixed (Decision 2): step 60 checks the link map's runtime paths and hashes; a
   v1.1 check refuses a reactor holding either SDK builder's path. The wording says "replaces",
   names `lib/clang/<n>/lib/wasm32-unknown-wasip1`, and step 10 refuses more than one
   `lib/clang/*`. The spec states that the SDK is a downloaded toolchain, not a source tree.
6. Finding 6 — Decided (Decision 8): x86_64 is built locally (emulated) before landing; the first
   fix tried on a difference is `-W nan-canonicalization=y`; after two failed attempts x86_64
   leaves the CI gate, the README says so and a memo records why.
7. Finding 7 — Fixed (Decision 4): the v1.4 check compares the guest's directory size and
   `nlink` with the host's `os.stat`, and states that a (0, 1) host cannot tell.
8. Finding 8 — Fixed (Decision 1): a rules check of the host table (five names per key, each
   pinned and fetched in its own branch, equal key sets in the three files) replaces the
   narrower toolchain pin test.
9. Finding 9 — Fixed (Decision 6): the snapshot's +1,312 bytes and possible fuel movement are
   named; growth is accepted with `--accept-growth` and all values recorded.
10. Finding 10 — Taken (Decision 7): the rebuild jobs run beside `build`; `same-bytes` compares
    afterwards.
11. Finding 11 — Fixed (criterion 2): the local builds start from empty `downloads/` and
    `build/`, as the CI jobs do.
12. Finding 12 — Fixed (Decision 1): the README and `MANIFEST`'s header line say the pins are
    every supported build host's.
13. Finding 13 — Fixed (Decision 7 and criterion 3): the CI rebuild jobs do not run the judge;
    the fast tier runs in the local Linux container against the Linux-built set.

## Reviewer's confirmation (2026-10-17, against the revised specification)

I read the revised specification in full and checked each disposition against its text. I
probed three of them in the scratch folder (`tools/sim5.py`, `out/sim5.txt`). I read
`build/link/python.map` and did not write it.

1. **Confirmed.** `line.py` leaves the names unset on a foreign host. `host_python_archive()`
   raises `RuntimeError`, which `oracle_available()` catches, and a unit test covers it. Note
   for the build: today a missing key would raise `KeyError`, which the oracle does not catch.
   So the explicit `RuntimeError` is load-bearing; keep it.
2. **Confirmed.** Comparing the 14-file `SHA256SUMS` is sound. `MANIFEST` is host-neutral once
   `SHA256SUMS` lists every host's pins (READ: `assemble_artifacts.py`). Leaving the `.tar.xz`
   out of the claim is stated.
3. **Confirmed.** EXECUTED (`sim5.py`): on today's macOS members I applied the four computed text
   rewrites in the stated order, then the key rewrites.
   - Each computed old text was present, and each key was present.
   - The case-sensitive scan then finds none of the ten forbidden words.
   - On ordering: rule 4's triple is contained only in rule 1's old text, which runs first. No
     other old text contains another. So the order is safe. "Longest first" is not literally
     true (the repository path runs last), but nothing depends on it.
4. **Confirmed.** `attest` and `publish` need `same-bytes`. `attest` still needs `build` and
   `verify`, so 009's scan holds.
5. **Confirmed.** EXECUTED: today's link map names all three archives, plus `libunwind.a` and
   `libc.a`. One detail for the build: the paths read
   `…/wasi-sdk-…/bin/../share/wasi-sysroot/…`, so step 60 must normalize `..` before testing
   "under the replaced directory" (new finding N1).
6. **Confirmed.** The fallback is decided and bounded by rule 7. The emulated x86_64 build is
   useful evidence. INFERRED: Rosetta and qemu both emulate x86 floating-point NaN results. But
   the CI `ubuntu-24.04` job is the proof, and criterion 4 requires it.
7. **Confirmed.** The check now compares with the host's own `os.stat`, and the (0, 1) limit is
   stated.
8. **Confirmed**, with an ambiguity (new finding N3).
9. **Confirmed.**
10. **Confirmed.**
11. **Confirmed.**
12. **Confirmed**, with a constraint (new finding N2).
13. **Confirmed.**

**New findings from the revision (all Low; fix in the build, no re-review needed):**

- **N1.** Link-map paths carry `bin/../`. Step 60 resolves each path (`realpath`, or Python's
  `os.path.normpath`) before testing that it lies under the replaced sysroot or builtins
  directory. Without that, the check fails on correct input, or a loose prefix test passes on
  wrong input.
- **N2.** `MANIFEST`'s new header line must start with `#` or `x-`.
  - EXECUTED (READ: `tests/harness/paths.py:169-196`): `parse_manifest` rejects any other line
    word, and `test_v1_1_artifact_set` would fail.
  - `runner._version_tag` reads only the `python ` line, so the wheel is unaffected.
- **N3.** Decision 1 says the host-table check "replaces" `toolchain_errors`. Decision 9 says
  that test "passes" and its gap entry is removed. Say which happens.
  - If the old test is deleted, the ratchet sees a check disappear. The landing then needs
    `--accept-judge` with that reason, beside the gap's removal.
  - If it is kept, say it stays alongside the new check.
- **N4.** The rebuild matrix uploads one `SHA256SUMS` per runner. Give each upload its own
  artifact name, for example by the runner. Same-named uploads from a matrix conflict in
  `upload-artifact` v4 and later. `same-bytes` must check both, or one if Decision 8's fallback
  leaves one.
- **N5.** Decision 5 rewrites `build_time_vars` "by key" in generated source. That source may
  split a long value across lines.
  - After rewriting, load the result and assert each rewritten key has its fixed value. That
    catches a rewrite that silently missed, not only an absent key.
  - The forbidden list dropped bare `linux`. The key rewrite covers numpy's `system`. Consider
    keeping bare `linux` for the numpy member, where a stray value would otherwise go unseen.
- If Decision 8's fallback is taken, the Intent's "or x86_64 Linux" must change with it, along
  with the README.

**Updated verdict: it can be built.** Every finding is fixed or decided, and each fix holds where
I could probe it. N1 to N5 are small points the build and its review should close.

## Verdict

Not ready to build yet. The direction is sound and the evidence holds: the overlay is complete,
the pins are real, and the reactor fix is right. But as written, Decision 1 turns the Windows
verify job red, and Decision 7 compares with a file that lacks two of its three hashes.
Decision 5 cannot be written as literal pairs on every host, and its check fails today's bytes.
Fix findings 1 to 5, decide finding 6's fallback, then build.

One line: a sound plan with three defects that would fail the first dry run (the Windows
oracle, the `MANIFEST` comparison, the host-specific rewrites) and one ordering gap (`attest`
before the rebuild); fix those, and it can be built.
