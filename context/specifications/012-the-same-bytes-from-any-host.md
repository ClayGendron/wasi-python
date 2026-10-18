# 012 — The same bytes from any host

- **Status:** landed, 2026-10-17, with Decision 8's fallback taken for x86_64. Reviewed before
  build (`../reviews/012-the-same-bytes-from-any-host-spec-2026-10-17.md`) and after
  (`../reviews/012-the-same-bytes-from-any-host-2026-10-17.md`). Criterion 4, the dry run, is
  recorded after the push (landing notes).
- **Owner:** Clay Gendron
- **Kind:** the recipe (`scripts/`, `recipes/reactor_main.c`), the pins
  (`downloads/SHA256SUMS`), the release workflow, judge additions in `tests/`, `README.md`,
  `CHANGELOG.md`.
- **Depends on:** 003 (the pinned build), 005 (the line in `scripts/line.conf`), 009 (the
  release workflow and its attest order).
- **Research it stands on:** `../research/2026-10-16-reproducible-builds-on-linux.md` (executed
  2026-10-17), with its evidence in `../research/2026-10-17-the-linux-build-experiment/`. The
  recipe ran on Linux aarch64 with only host names changed, and each host reproduced itself. The
  two hosts differed through four leaks. With three recipe fixes the reactor was byte-identical
  on both hosts, and `wasmtime wizer` was shown to be host-independent. The fourth leak, two zip
  members, was found but not fixed. The pre-build review added the facts marked "the review"
  below.

## The problem

Today `SHA256SUMS` is an integrity claim: these are the bytes we published. It is not a
reproducibility claim: that anyone can rebuild them. The build runs only on arm64 macOS, and a
Linux build of the same pins gives different bytes for all three artifacts. People who run
untrusted code in this sandbox trust its bytes. They should be able to rebuild those bytes on a
machine they choose and get the same hashes.

The four leaks, all EXECUTED in the memo:

1. Each host's wasi-sdk tarball carries its own build of libc++, libc++abi and the compiler-rt
   builtins. Two `__FILE__` strings from libc++abi reach the reactor.
2. Step 60 orders the link with `sort`, and `sort` follows the builder's locale.
3. The snapshot keeps the host file system's answer for a directory's size and link count:
   APFS answers 96, ext4 4096. CPython's heap layout follows that answer.
4. `_sysconfigdata` and numpy's `__config__.py` in the zip record the build host.

## Decisions

1. **Per-host inputs are named per host, and a foreign host still reads the line.** This is the
   memo's edits 1–5, with one change from the review.
   - `scripts/line.conf` gives each host-specific name one line per host, with a host-key
     prefix: `MACOS_ARM64_`, `LINUX_AARCH64_`, `LINUX_X86_64_`. The names are `WASI_SDK_DIR`,
     `HOST_PYTHON_ARCHIVE`, `CYTHON_WHEEL`, `WASMTIME_DIR` and a new `NINJA_WHEEL`.
   - `line.sh` (for the build) sets the plain names for the running host, taken from
     `uname -s` and `uname -m`. On any other host it stops with one line naming the three keys.
   - `line.py` (for the judge) sets the plain names only on a known host, taken from
     `platform`. On any other host, such as Windows or an Intel Mac, it leaves them unset and
     raises nothing. The oracle's `host_python_archive()` then raises `RuntimeError` ("no host
     Python for this host"), which `oracle_available()` already treats as unavailable. Without
     this, the Windows `verify` job would go red (the review, EXECUTED: the experiment's
     `line.py` raised `SystemExit` under `Windows-AMD64`, which the oracle does not catch). A
     unit test runs `line.read()` and `oracle_available()` under a foreign `platform`.
   - `00_download.sh` fetches the running host's toolchain, host Python and native wheels in a
     `case` on the key. The `get` lines stay literal, one pin per line (spec 003, Decision 1).
   - `downloads/SHA256SUMS` lists every host's pins, each checked against its publisher's
     digest (memo, finding 1). So `MANIFEST`, which lists the pins, is the same file on every
     host. Its `pin` lines then name every supported build host's inputs, not only the ones one
     build used. The README says so, and so does a new `MANIFEST` line,
     `x-pins every-supported-build-host` (it must start with `x-`, or the v1.1 check's parser
     refuses it; the review's confirmation, N2).
   - **A host-table check** (rules): every host key has all five names in `line.conf`. Each
     name is pinned and is fetched by a `get` line inside that key's own `case` branch. The
     sets of keys in `line.sh`, `line.py` and `00_download.sh` are equal. It is the stricter
     guard; the narrower `toolchain_errors` pin test (two hosts' SDK and wasmtime) stays beside
     it and passes (Decision 9).
2. **One wasm runtime for every host.**
   - `00_download.sh` pins wasi-sdk 33's host-neutral `wasi-sysroot-33.0+m` and
     `libclang_rt-33.0+m`.
   - Step 10 **replaces** the unpacked SDK's `share/wasi-sysroot` (removed, then unpacked) and
     the builtins directory `lib/clang/<n>/lib/wasm32-unknown-wasip1`. Step 10 refuses
     unless `lib/clang/*` matches exactly one directory.
   - The host tarball then supplies only the compiler. This is the memo's edit 8 (EXECUTED).
   - The SDK is a downloaded binary toolchain unpacked under `build/`, not a source tree, so
     this is no upstream patch.
   - Passing `--sysroot` and `-resource-dir` instead was not tried. `-resource-dir` would also
     need the compiler's own headers.
   - **The check is on what the link used.** A file check alone proves nothing on Linux, where
     the neutral `libc++abi.a` already equals the host tarball's (the review, EXECUTED). So
     step 60 reads its link map (`build/link/python.map`). It resolves each path (the map
     writes `bin/../share/…`) and requires `libc++.a`, `libc++abi.a` and
     `libclang_rt.builtins.a` to lie under the replaced directories, with the neutral
     tarballs' hashes.
   - A v1.1 check refuses a reactor that holds either SDK builder's path
     (`/Users/runner/work/wasi-sdk` or `/src/src/llvm-project`; memo,
     `outputs/sdk-runtime-diff.txt`). *As built, it refuses only the first: the neutral runtime
     is itself built at `/src/src/llvm-project` (landing notes, deviation 1).*
3. **One collation.** `scripts/build.sh` exports `LC_ALL=C` (edit 6). Every `sort` in every
   step then orders bytes the same way on every host.
4. **A directory's size and link count are pinned while initializing.** While the clocks are
   pinned, `pin_filestat` in `recipes/reactor_main.c` (our recipe file) also answers a
   directory's `size` as 0 and its `nlink` as 1 (edit 7). The pin ends before `run`, as the
   clock pin does, so a program never sees it (the review, INFERRED from reading
   `reactor_main.c` and CPython's start-up).
   - The v1.4 check `test_a_program_sees_real_entropy_and_file_metadata` gains a directory. It
     compares the guest's `os.stat` size and `nlink` with the host's `os.stat` of the same
     directory, not with fixed numbers.
   - On a host whose real answer is (0, 1), which may be Windows, that check cannot tell pinned
     from real. The check says so; the macOS and Linux runs are the ones that tell.
5. **The zip says nothing about its build host, rewritten by key.** Literal `--replace` pairs
   cannot work: the old text differs per host, and order matters (the review). So
   `make_stdlib_zip.py`, our script, gains a host-neutral rewrite.
   - **By key, to fixed values, whatever they were.**
     - In `_sysconfigdata`'s `build_time_vars`: `BUILD_GNU_TYPE` becomes `build`; `GNULD`
       becomes `no`; `MKDIR_P` becomes `mkdir -p`; `INSTALL`, `INSTALL_DATA`,
       `INSTALL_PROGRAM`, `INSTALL_SCRIPT` and `INSTALL_SHARED` become `install -c` followed by
       their own flags.
     - In numpy's `__config__.py`, the build machine's `cpu`, `family` and `system` become
       `build`; `endian` stays.
     - A key that is absent stops the build with one line. After rewriting, the script loads
       the result and requires each rewritten key to hold its fixed value, since generated
       source may split a long value across lines.
   - **Computed text, longest first.** Step 70 passes text rewrites computed from what the
     build knows, never from literals:
     1. the build-Python's path `cross-build/<triple>/<name>` becomes `cross-build/build/python`;
     2. the SDK directory name becomes `wasi-sdk`;
     3. the wasmtime directory name becomes `wasmtime`;
     4. the build triple becomes `build`;
     5. the repository path becomes `/wasi-python-build`, as today.

     They are applied in that order: rule 4's triple appears only inside rule 1's old text,
     which runs first, and no other old text contains another (the review, EXECUTED). A computed old text found
     in neither member stops the build. On every host each one is present (the review,
     EXECUTED, for the existing path rewrite).
   - **Safe inside the guest.** These values describe the machine that built CPython, and no
     compiler runs in a WASI guest. Nothing in `src/`, the tests or the guest's
     `sysconfig.get_platform()` reads them (the review, EXECUTED by grep).
     `numpy.show_config()` and `sysconfig.get_config_var` will print `build` for the build
     machine; the README says so (constitution §4.11).
   - **A v1.5 check** reads the two members' `.pyc` bytes from the built zip. The judge runs
     on 3.14 and cannot unmarshal 3.15 bytecode, so it scans the bytes as ASCII. The scan is
     case-sensitive, because the member holds 20 `HAVE_LINUX_*` keys. It refuses any of:
     - `darwin`, `apple`, `linux-gnu`, `-macos`, `-linux`;
     - `aarch64`, `x86_64`, `arm64`;
     - `python.exe`, `/usr/bin`;
     - the repository path.
6. **The bytes change once, and are accepted once.** Decisions 2–5 change the reactor, the zip
   and the snapshot. In the memo's run 7 the reactor grew by 10 bytes and the snapshot by 1,312,
   before Decision 5, which no run measured. Fuel may move too, because the heap layout changes.
   The landing accepts the new hashes and, where they grow, the sizes and fuel with
   `--accept-growth` and a reason. The landing notes record all of them.
7. **Two more hosts check it, in CI, beside the build.** The release workflow gains a `rebuild`
   job, a matrix of `ubuntu-24.04-arm` and `ubuntu-24.04` (x86_64). Both runners are
   GitHub-hosted and free for public repositories. *As built, the matrix is `ubuntu-24.04-arm`
   only: Decision 8's fallback was taken (landing notes).*
   - The jobs start at once, beside `build`, from an empty `downloads/` and `build/`.
   - Each runs `scripts/build.sh`. It uploads its `build/artifacts/SHA256SUMS`, under an
     artifact name of its own (by runner), which covers the whole set of 14 files: the three
     artifacts, `MANIFEST` and the licences.
   - A small `same-bytes` job needs `build` and `rebuild`. It unpacks the set's `.tar.xz` from
     `release-assets` (as `verify` does) and requires every matrix entry's `SHA256SUMS` to be
     present and to equal the set's, byte for byte. So the claim is "the whole artifact set", not three hashes. The
     `.tar.xz` asset itself is made deterministically from the set (`version.py assets`), but
     it is outside this claim.
   - `attest` needs `same-bytes`, and so does `publish`, so a tag never signs bytes that failed
     the gate (the review: spec 009 signs only what is about to be published).
   - `rebuild` and `same-bytes` have no tag-only `if:` (a dry run runs them), no `id-token`, and
     only `contents: read`.
   - The rebuild jobs do not run the judge. `verify` already runs it on Linux against the
     published set, and the memo ran the fast tier on Linux-built artifacts.
   - **A scan check** (in spec 009's style) requires all of the above in the workflow:
     - both runners in the matrix;
     - no tag-only `if:` on either new job;
     - the `SHA256SUMS` comparison;
     - `attest` and `publish` each need `same-bytes`.

     The scoreboard drops "second-host rebuild" from its not-machine-checked list.
8. **x86_64 is built before landing, and its fallback is decided now.** x86_64 was pinned but
   not built. The review names one risk that two aarch64 hosts could not show. The bits of an
   arithmetic NaN are left to the hardware, and wasmtime does not canonicalize them by default.
   So a NaN computed while numpy or pandas import would land in the snapshot, and differ on
   x86_64 (INFERRED). Relaxed SIMD is ruled out: the reactor has no SIMD (the review, EXECUTED).
   - **Note (spec 059, 2026-10-18):** this decision's fallback, x86_64 as a pinned build host
     outside the gate, stands as the last resort behind spec 059's switch (059, Decision 9);
     nothing here changes.
   - The build runs the full recipe for linux/amd64 in the experiment's container before
     landing (emulated on this machine; slow, and a benchmark fact) and compares the set.
   - If x86_64 differs, the first fix tried is wasmtime's `-W nan-canonicalization=y` in step
     80's Wizer flags (the pinned wasmtime has it; the review, EXECUTED).
   - If two attempts fail (`AGENTS.md` rule 7), x86_64 Linux stays a pinned build host without
     the CI gate: the matrix keeps only `ubuntu-24.04-arm`, the README says x86_64 rebuilds are
     not yet byte-identical, and a memo records why.
9. **The known gap closes.** With the Linux pins in `SHA256SUMS`,
   `test_toolchain_is_pinned_for_linux_and_macos` passes, and its entry leaves
   `tests/known_gaps.toml` in the same change (`--accept-judge`). It stays, with Decision 1's
   host-table check beside it as the stricter guard. If Decision 8's fallback is taken, the
   Intent and the README say x86_64 is pinned but not yet byte-identical.
10. **What stays unpinned.** The runner images' own tools stay unpinned host inputs, as the
    README already says: a C compiler for the build-Python, make, curl, tar, xz and perl's
    `shasum`.
    - The memo showed that gcc 14.2 and Apple clang give the same artifact bytes.
    - The CI jobs print their tools' versions to the job log.
    - Cython's C output is not deterministic (memo, finding 11), but it compiles to equal
      objects. It stays a recorded latent risk, which the `same-bytes` gate would catch.

## Intent

Anyone can rebuild the published sandbox from its pins on arm64 macOS or arm64 Linux and get the
same artifact set, byte for byte. CI proves it on every release, before anything is signed. x86_64
Linux is a pinned build host, but its rebuild is not yet byte-identical (Decision 8's fallback,
taken: see the landing notes).

## Design

```
scripts/line.conf, line.sh, line.py   per-host names; a foreign host leaves them unset (line.py)
scripts/00_download.sh                per-host get lines; the neutral sysroot and builtins
scripts/steps/10_tools.sh             the runtime replaced; one clang dir; $NINJA_WHEEL
scripts/build.sh                      LC_ALL=C
scripts/steps/60_link.sh              the link map's runtime paths and hashes checked
recipes/reactor_main.c                a directory's size and nlink pinned while initializing
scripts/steps/70_zip.sh, make_stdlib_zip.py   host facts rewritten by key and computed text
downloads/SHA256SUMS                  every host's pins
.github/workflows/release.yml         rebuild (arm64 only, Decision 8), same-bytes; attest, publish need it
tests/…                               host table; zip names no host; reactor has no builder path;
                                      directory metadata (v1.4); the workflow scan; line.py on a
                                      foreign host; the known gap removed
README.md, CHANGELOG.md
```

## Scope

In: the above. Out:
- Windows or Intel macOS as build hosts;
- pinning the runner images' packages;
- tracing Cython's nondeterminism;
- a published container recipe for local Linux rebuilds (the experiment's `Dockerfile` stays in
  the research folder).

## Acceptance criteria

1. The zip check, the builder-path check, the host-table check, the workflow scan and the
   foreign-host test were seen failing before the change. The known gap's check passes, and its
   entry is gone.
2. A local macOS build from an empty `downloads/` and an empty `build/` gives the new set. Local
   Linux aarch64 and x86_64 builds in the experiment's container, from empty `downloads/` and
   `build/`, give the same `SHA256SUMS`. Or, for x86_64, Decision 8's fallback is taken and
   recorded.
3. `uv run pytest` is green with `--accept-judge` and the new bytes accepted, and the fast tier
   passes in the Linux container against the Linux-built set.
4. A dry run of the release workflow passes every job, and `same-bytes` reports equal sets.

## Landing notes

Built 2026-10-17 by the implementer (Claude Opus 5.5) in a scratch clone of `9512e3a`, not in the
main tree, and applied to the main tree after spec 011 landed; reviewed in
`../reviews/012-the-same-bytes-from-any-host-2026-10-17.md`. The review's fixes: the workflow
scan refuses a `same-bytes` compare that does not set a rebuild's download against the set's
(mutation M18), and requires each gated runner's download step; Decisions 2 and 7 point to the
recorded deviations; the seen-failing-first log and each host's download list are in the
research folder; two long lines are wrapped; `make_stdlib_zip.py` refuses an empty `--replace`.
The Linux aarch64 fast tier below ran the judge as it stood before the fallback (with the
two-runner workflow scan), against the same bytes. Every claim below was run (EXECUTED) unless
it says otherwise. Evidence for the Linux runs is in `../research/2026-10-17-the-x86-64-rebuild/`.

### Seen failing first (criterion 1)

The new checks ran against today's recipe and today's artifact set (`4e2b2470…`, `c6a791d3…`,
`e95b35de…`, copied out of the main tree), before any recipe change:

- `test_rules.py::test_every_build_host_has_its_whole_table`: failed, 5 findings. Four host names
  are set for every host, and no host key names a host's inputs.
- `test_v1_1_artifact_set.py::test_reactor_holds_no_sdk_builder_path`: failed. `python.wasm`
  holds `/Users/runner/work/wasi-sdk`.
- `test_v1_5_rebuild_from_pins.py::test_stdlib_zip_names_no_build_host`: failed, 9 findings.
  - `_sysconfigdata` holds `darwin`, `apple`, `-macos`, `aarch64`, `arm64`, `python.exe` and
    `/usr/bin`.
  - numpy's `__config__` holds `darwin` and `aarch64`.
- The workflow scan (then named `…_rebuilds_on_two_more_hosts`): failed with `no rebuild job` and
  `no same-bytes job`.
- `tests/unit/test_line.py`: all 5 failed. Each build host got macOS's names. A foreign host got
  them too, so `host_python_archive()` did not raise.
- The v1.4 directory check passed on the old bytes, as it should. It guards that the new pin never
  reaches a program; it cannot fail before the pin exists.

After the change all of these pass. `test_toolchain_is_pinned_for_linux_and_macos` passes, and
its entry is gone from `tests/known_gaps.toml`. It stays beside the host-table check (N3).

### The new set (criterion 2)

macOS, in the clone, from an empty `downloads/` (only `SHA256SUMS`) and no `build/`:
`sh scripts/build.sh`. It fetched 26 pins (macOS's own and the host-neutral ones). It built in
385 s, a benchmark fact, run beside a container build.

| file | bytes | SHA-256 | before |
|---|---|---|---|
| `python.wasm` | 29,802,418 | `2df569f2f59397d59b175eec7553d6a0ec7dff99b5e819659f9ce0758fdba3ad` | 29,802,408 `4e2b2470…` |
| `python-snapshot.wasm` | 63,489,079 | `4130d3baa218ce9b6fec08d84bb62f6a470ea791545f86b79d78f89c64ae4c44` | 63,492,577 `c6a791d3…` |
| `python-stdlib.zip` | 11,140,578 | `2a8085a23f661f81eb6f522708e1957b849588681a69e3992f7707731754e7c5` | 11,140,659 `e95b35de…` |
| `MANIFEST` | 7,874 | `69f776d8fd22a5184cdd855b2b337bfeb7f9c45e61f0bddddc19e45299ab083c` | `51ad8d75…` |
| `SHA256SUMS` | | `e51434a759a25aeb926679514198dac48e2edca3c67de77ce6c8f13ab4435019` | |

After the build review, `make_stdlib_zip.py` gained the empty-`--replace` refusal, and
`MANIFEST` records each recipe file's hash. So the main tree's rebuild (EXECUTED: the whole
build from the patched tree, then steps 70–90 again after that fix) gives the same reactor,
snapshot and zip as above, with `MANIFEST` `980beb0a6b9977ffe84eae92918411f9c5e7dd7973c6c7d6f25fc28225d125eb`
(7,874 bytes) and `SHA256SUMS` `5353ad94ca610640a8fd015871787ba682a87267b7f418af74e4ce8e599e97f8`.
The Linux equality below was shown on the earlier `MANIFEST`; on the final one it is shown by
the dry run's `same-bytes` job.

- The reactor equals the memo's run 7 (`2df569f2…`).
- The nine licence files are unchanged.
- `MANIFEST` now has 36 `pin` lines and `x-pins every-supported-build-host`.
- Step 60's runtime check logged the three archives the link used. Each was under the replaced
  directories, and each equalled the neutral tarball's member: `libc++.a` `d4527e52…`,
  `libc++abi.a` `53a077fc…`, `libclang_rt.builtins.a` `b1e23c03…`.

**Linux aarch64:** the experiment's image (`debian:trixie-slim@sha256:a29215f6…`, with uv 0.9.22
checked against its digest). It started from an empty `downloads/` and `build/`, in a fresh clone
of the change. All ten steps passed in 302 s. Its `build/artifacts/SHA256SUMS` is **byte-identical
to macOS's** (`cmp`; both `e51434a7…`). It fetched only aarch64 Linux's own inputs.

**Linux x86_64** (`--platform linux/amd64`, under Rosetta): all ten steps passed in 1,155 s. Its
`SHA256SUMS` **differs** in two lines:

- `python.wasm` is `36c654782b6cdd4b…`, at the same 29,802,418 bytes.
- `python-snapshot.wasm` is `568b9db75d1686a0…`, at the same 63,489,079 bytes.
- The zip, `MANIFEST` and the licences are the same.

**Decision 8 was followed. Its fallback is taken.**

- Attempt 1: NaN canonicalization, run as step 80's exact Wizer command on x86_64 against macOS's
  reactor and zip.
  - Without the flag, it wrote macOS's snapshot, `4130d3ba…`. With
    `-W nan-canonicalization=y` it wrote the same.
  - So Wizer is host-independent on x86_64, and the flag is neither needed nor a fix. Step 80 is
    unchanged.
  - Rebuilding all three hosts with the flag in step 80 was not done: the reactor already
    differed before step 80.
- Attempt 2: find the cause.
  - The 21 differing bytes are all in numpy's `npy_cpowl`. Its one object,
    `meson-generated_npy_math_complex.c.o`, differs from identical source and flags.
  - Each host's clang is deterministic: three recompiles each gave `20ef3344…` on aarch64 and
    `d3689743…` on x86_64.
  - Two spill slots trade frame offsets, 112 and 160.
  - No recipe-level fix was found that is not a per-file workaround.
- The fallback, as decided:
  - the matrix keeps only `ubuntu-24.04-arm`;
  - the scan requires that one runner;
  - the README, the CHANGELOG and this specification's Intent say x86_64 is pinned but not yet
    byte-identical;
  - `../research/2026-10-17-x86-64-rebuilds-differ-in-one-function.md` records why.
- x86_64 keeps its key, pins and download branch, and it builds.

### The judge (criterion 3)

**Fast tier on Linux aarch64**, in the container, against the Linux-built set, with an empty
progress dir: `uv run pytest -m "not slow" --progress-dir=build/no-baseline`. The `=` form is
needed: with a space, pytest took the value as a path and never loaded the plugin. Result:
`125/132 pass · 0 gap · 3 blocked · 0 fail · 4 deselected`, `346 passed, 8 skipped`, exit 0. The
blocked checks are prior-art clones, three systems and the wheel. The v1.4 directory check
passed against ext4's real answers. (`outputs/judge-fast-linux-aarch64.txt`)

**The whole judge on macOS**, in the clone, against the clone's set: `uv run pytest`. It ran after
`tests/jobs/regen.py --online --check` fetched the pinned oracle into the clone; all three goldens
reproduced. Not accepted.

```
wasi_python v1: 129/132 pass · 0 gap · 3 blocked · 0 fail   (unit suite 220/225, 5 skipped)
  v1.1  artifact set        22/23  blocked 1
  v1.2  portable, sealed    29/30  blocked 1
  v1.3  data stack          12/12
  v1.4  embedding           35/35
  v1.5  rebuild from pins   15/15
  rules constitution rules  16/17  blocked 1
blocked by: prior-art clones 1 · three systems 1 · wheel 1
ratchet vs ab9bafd727: lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 5 · grew 16 ·
  judge changed: tests/checks/test_rules.py, tests/checks/test_v1_1_artifact_set.py,
  tests/checks/test_v1_4_embedding.py and 9 more
RED: 16 metric(s) grew
349 passed, 8 skipped
```

The 16 growths, against `context/progress/accepted.json`, to accept with `--accept-growth`:

| check | metric | accepted | now |
|---|---|---|---|
| `test_binary_is_a_core_wasm_module[plain]` | bytes | 29,802,408 | 29,802,418 |
| `test_no_cpython_test_module_is_built_in` | fuel | 82,603,616 | 82,620,024 (+0.020%) |
| `test_guest_runs_here[snapshot]` | fuel | 81,974,560 | 81,994,395 (+0.024%) |
| `test_numpy_and_pandas_are_builtin_at_manifest_versions[snapshot]` | fuel | 82,268,970 | 82,285,108 (+0.020%) |
| `test_snapshot_preimports_the_stack` | fuel | 81,907,057 | 81,926,472 (+0.024%) |
| `test_stdlib_debugging_tools_import` | fuel | 534,816,860 | 534,905,050 (+0.016%) |
| `test_a_program_sees_real_entropy_and_file_metadata[plain]` | fuel | 241,965,052 | 242,227,843 (+0.109%) |
| `test_a_program_sees_real_entropy_and_file_metadata[snapshot]` | fuel | 82,471,455 | 82,775,098 (+0.368%) |
| `test_door_round_trips_bytes_through_a_host[snapshot]` | fuel | 82,330,274 | 82,374,344 (+0.054%) |
| `test_door_without_a_host_says_so[snapshot]` | fuel | 82,760,082 | 82,782,357 (+0.027%) |
| `test_exit_status_is_a_process_status[snapshot]` | fuel | 81,976,093 | 81,996,007 (+0.024%) |
| `test_main_starts_as_native[snapshot]` | fuel | 82,080,883 | 82,101,223 (+0.025%) |
| `test_run_reads_argv_and_environment_each_call[snapshot]` | fuel | 82,267,575 | 82,283,408 (+0.019%) |
| `test_run_returns_the_exit_code[snapshot]` | fuel | 82,026,695 | 82,047,342 (+0.025%) |
| `test_uncaught_errors_print_as_native[plain]` | fuel | 670,492,719 | 670,579,668 (+0.013%) |
| `test_uncaught_errors_print_as_native[snapshot]` | fuel | 83,322,729 | 83,340,903 (+0.022%) |

- Why it grew (INFERRED):
  - The snapshot's heap layout changed, through the pinned directory stats and the shorter zip
    offsets. A snapshot call's fuel moved by about +0.02%.
  - The two metadata checks grew more because their program changed: it now stats a directory
    and prints two more values. That is a judge change.
- 18 other metrics shrank: the snapshot by 3,498 bytes, the zip by 81 bytes, and plain-reactor
  fuel by up to −0.02%.
- The ratchet counts 5 gained: the four new goal checks (host table, builder path, zip, workflow
  scan), and the toolchain check, which was a gap. `unrun locally 1` is the prior-art clones,
  which the clone lacks.
- The judge changed. It needs `--accept-judge`, with the gap's removal as part of the reason.

### Deviations from the specification, for the review

1. **The builder-path check refuses only `/Users/runner/work/wasi-sdk`, not
   `/src/src/llvm-project`.**
   - The host-neutral runtime that Decision 2 links is itself built at `/src/src/llvm-project`:
     its `libc++abi.a` equals the Linux tarballs' (the review's own finding 5).
   - So the correct new reactor holds `/src/src/llvm-project/libcxxabi/src/private_typeinfo.cpp`
     and `…/fallback_malloc.cpp` (`strings`) on every host.
   - Refusing that path would fail the right bytes. The check refuses the per-host path it can
     tell apart.
   - Step 60's link-map hash check is the guard that the neutral archives were used.
2. **Decision 8's fallback is taken** (above). The scan's runner list and the workflow have one
   runner. The check is renamed `test_release_workflow_rebuilds_on_a_second_host`.
3. **NaN canonicalization was tested directly, without a rebuild** (above). Step 80 is unchanged.
4. **A small evidence folder and a memo were added** (`2026-10-17-the-x86-64-rebuild/`), as
   Decision 8's fallback requires. The folder holds a parameterized copy of the experiment's
   `Dockerfile`, with a uv build argument so the same file serves both platforms.

### Left over

- **Criterion 4 is not run.** A dry run of the release workflow needs a push. Neither a push nor
  a tag was made.
  - The new jobs have not run on GitHub.
  - `same-bytes` downloads one artifact by name and unpacks the set with `tar -xJf`. Both are
    untested there.
- **Windows risk in the v1.4 check (INFERRED).** The directory part compares the guest's size and
  `nlink` with Python's `os.stat`.
  - On Windows, Python reports a directory's `st_nlink` as 1. The build review read wasmtime
    49.0.3's source: it takes `nlink` and `size` from the same NTFS handle fields that CPython's
    `os.stat` reads, so both sides should agree (INFERRED: pass).
  - If wasmtime reports 0, the `windows-2025` verify job fails on this check. The dry run will
    show it.
- x86_64 under Rosetta stands in for the `ubuntu-24.04` runner (INFERRED to agree). It runs in no
  CI job now.
- Cython's nondeterminism (memo, finding 11) stays a recorded latent risk. The `same-bytes` gate
  would catch it.
- The patch carries this specification as a new file. It replaces the untracked copy in the main
  tree. The review file is unchanged and is not in the patch.

**The dry run** (EXECUTED: https://github.com/ClayGendron/wasi_python/actions/runs/39022271049,
on `513455e`, which carries this change): every job it runs passed (criterion 4).
- `rebuild from the pins (ubuntu-24.04-arm)` built the set from empty `downloads/` and `build/`
  on GitHub's arm64 Linux runner.
- `the same bytes from every host` found that set's `SHA256SUMS` byte-identical to the macOS
  build's, with the final `MANIFEST`.
- Verify passed on ubuntu-24.04, windows-2025 and macos-15, the v1.4 directory check on Windows
  included.
- `attest`, `publish` and PyPI were skipped, as a dry run must.
