# Byte-identical wasm builds across hosts: what other projects do, and one flag that ends our tie

- **Status:** research, 2026-10-18; commits the project to nothing.
- **Owner:** Clay Gendron
- **Researcher:** a research agent (Claude Fable 5.1), outside the repository. Read-only on the
  repository. Nothing in it was changed; its judge was not run.
- **Box:** about 90 minutes of study, plus two cheap experiments (under ten minutes of compiles)
  in the scratch folder `prior-art-repro/` beside this memo.
- **Question:** How do WebAssembly build projects, and reproducible-build projects in general,
  get (or decline to get) the same bytes from different build hosts and CPU architectures? How do
  they verify it without long emulated builds? What does that say about our x86_64 rebuild, which
  runs the aarch64 clang under qemu for about an hour (spec 040) because the x86_64 clang orders two
  stack slots differently in one numpy function?
- **Labels:** every claim is EXECUTED (run here, command given), READ (a source, URL given) or
  INFERRED (a conclusion of mine, marked).

Terms used once and defined here. A **tie** is a choice between two equal-cost code layouts that a
compiler must make somehow. A **libcall** is a call the compiler emits to a runtime function for an
operation the target lacks (wasm32 has no 128-bit float, so `long double` arithmetic becomes
`__multf3`, `__addtf3`). **Contraction** is fusing `a*b+c` into one fused multiply-add; clang's
default (`-ffp-contract=on`) marks such expressions with the `llvm.fmuladd` intrinsic and lets the
backend decide. A **normalized comparison** compares two artifacts after a transform that hides
known, accepted differences (a signature, a timestamp).

## Summary in five lines

1. Nobody studied gets cross-architecture identical compiler output for free. The projects that
   have it (Go) designed the compiler for it. The ones that use LLVM or GCC have hit host-dependent
   output (LLVM #99396, Bitcoin Core #27897/#31207, Rust in 2024 to 2026) and treated it as a
   compiler bug: fixed upstream, carried as a short-lived patch, or the affected target was dropped.
2. Nobody studied emulates a compiler to make a second architecture agree. Verification practice
   is either "same architecture only" (Debian, Arch, Tor Browser) or "cross-compile everything from
   one reference host and let several builders attest" (Go, Bitcoin Core, Tor Browser).
3. Normalized comparison is used for signatures and installers (Go, F-Droid), never for compiler
   output. A per-function allow-list has no precedent among the projects studied.
4. EXECUTED here: `-ffp-contract=off` makes the pinned x86_64 and aarch64 clangs produce the
   **same object** for the real numpy file (`2914eb833ad62c93` on both), and for the nine-line
   reproducer. The host difference lives in how `llvm.fmuladd` on `long double` is lowered. That is
   a recipe flag, which §4.1 lists first, and it makes a native x86_64 rebuild (about 7 minutes)
   possible with the gate kept.
5. Recommendation: take the flag, run x86_64 natively in the gate, keep the emulation launcher one
   release as a fallback, sharpen the upstream issue with the `fmuladd` clue. Details below.

## Part 1: what the toolchains and the Python-on-wasm projects do

### wasi-sdk (our compiler)

- READ (`https://github.com/WebAssembly/wasi-sdk/blob/main/.github/workflows/main.yml`,
  `ci/docker-build.sh`, `ci/docker/Dockerfile`): each host's binaries are built natively on that
  host's runner: `ubuntu-24.04` for x86_64 Linux, `ubuntu-22.04-arm` for arm64 Linux, `macos-14`
  for both macOS builds, Windows runners for Windows. The Linux builds run in an `almalinux:8`
  container whose host compiler is that distribution's unpinned `clang`. riscv64 alone is
  cross-compiled with GCC. No `SOURCE_DATE_EPOCH`, no `-ffp-contract` setting, no reproducibility
  claim anywhere in the workflow or scripts. ccache is used across runs.
- READ (`https://github.com/WebAssembly/wasi-sdk/blob/main/RELEASING.md`): a release reuses the
  artifacts of the tag's CI run; nothing is rebuilt or compared.
- INFERRED: so the three wasi-sdk 33 clangs we pin are three different builds of LLVM
  `4434dabb6991`, each by a different host compiler on a different host. Any host-dependent code
  path in LLVM (host float precision, pointer-keyed iteration) can show as a difference between them.
  wasi-sdk makes no promise that it does not.
- READ (`https://gitlab.torproject.org/tpo/applications/tor-browser-build/-/issues/40802`): Tor
  Browser found wasi-libc's build non-reproducible, fixed it upstream and carried the patch until
  the wasi-sdk Firefox uses picked it up. That is the carried-patch pattern our §4.1 describes.

### LLVM upstream: host-dependent codegen is a known bug class, and it gets fixed

- READ (`https://github.com/llvm/llvm-project/issues/99396`, "i386-on-i386 build is different
  from i386-on-amd64 build", opened 2024-07-17, closed 2024-07-26): the same clang, built for two
  hosts, chose different registers for the same i386 input. Cause: a spill weight computed in
  `float` in `weightCalcHelper()`, where x87 excess precision on the i386 host changed the last
  digit (`7.938738e-02` against `7.938739e-02`). Fix: commit `c80c09f3e380`, "[CalcSpillWeights]
  Avoid x87 excess precision influencing weight result", backported to `release/19.x` as `1eae7f7`
  on 2024-08-10 (READ, `https://lists.llvm.org/pipermail/llvm-branch-commits/2024-August/035941.html`).
  INFERRED from the dates: it shipped in LLVM 19.1.0. Nine days from report to fix.
- READ (same issue, and FreeBSD ports `devel/llvm18: fix host dependent compiler output for
  i386`): FreeBSD saw it as "very small differences in a couple object files in buildworld for
  i386 depending on the host architecture", carried a temporary ports patch, and said "as soon as
  upstream has a permanent solution we will import that". A reporter also found a flag workaround,
  `-mllvm -enable-misched=0`, before the cause was known.
- READ (`https://llvm.org/docs/CMake.html`): `LLVM_REVERSE_ITERATION` iterates every unordered
  container backwards, "useful for uncovering non-determinism caused by iteration of unordered
  containers". READ (`https://llvm.org/docs/ProgrammersManual.html`): pointer-keyed sets and
  `StringMap` have no deterministic iteration order; `SetVector` and `MapVector` exist for code that
  needs one. So LLVM treats both known sources of host-dependent output (host float, pointer order)
  as defects, with tooling for the second.
- READ (`https://github.com/llvm/llvm-project/pull/161355`, September 2025): the WebAssembly
  backend lowers vector `fmuladd` to a fused instruction only with relaxed SIMD. Without it, there is
  no fused multiply-add on wasm32. INFERRED: so `-ffp-contract=off` cannot change a floating-point
  result in our build, which does not enable relaxed SIMD (the numpy compile command carries no
  `-m` SIMD flag, and `-DNPY_DISABLE_OPTIMIZATION`). It can only change which IR the optimizer sees.

### Emscripten, Binaryen, wasm-tools, Wizer

- READ (searches of the Emscripten issue tracker and docs, no hit): no reproducibility claim across
  hosts was found. Emscripten ships per-host binaries like wasi-sdk. SQLite's wasm build notes
  (`https://huggingface.co/AryaWu/sqlite/blob/main/ext/wasm/mkwasmbuilds.c`) say only that builds
  with the same wasm-affecting flags give identical `.wasm` on one machine.
- READ (Binaryen docs and commits): no cross-host nondeterminism report found; commits about
  determinism concern the fuzzer. INFERRED, not run: `wasm-opt` cannot be a normalizer for our
  difference. The 21 bytes are frame offsets in `i32.const`, `i64.load` and `i64.store`
  immediates; no Binaryen pass re-allocates the linear-memory shadow stack, so two swapped slots
  stay swapped through any `wasm-opt` run.
- EXECUTED earlier by the project (memo `2026-10-17-x86-64-rebuilds-differ-in-one-function.md`,
  finding 6): Wizer's snapshot step is host-independent on x86_64. Nothing found contradicts it.

### Python-on-wasm projects: none checks reproducibility, none builds on two architectures and compares

| project | how it builds | reproducibility check | source |
|---|---|---|---|
| Pyodide | GitHub Actions, `build-core` on `ubuntu-latest` and `macos-15`, no container; artifacts uploaded per host, never compared | none; the only post-build check is a compressed-size script | READ `https://github.com/pyodide/pyodide/blob/main/.github/workflows/main.yml`; docs recommend the x86_64 Docker image or native conda on Apple silicon (`https://pyodide.org/en/stable/development/building-from-sources.html`) |
| CPython `Tools/wasm` (WASI CI) | one runner, `ubuntu-26.04-arm`; builds and runs the test suite | none | READ `https://github.com/python/cpython/blob/main/.github/workflows/reusable-wasi.yml` |
| Brett Cannon's `cpython-wasi-build` | README not fetchable (404 on raw `main`); the project's prior-art clone is the record | not studied here | — |
| VMware Labs WLR | `make python/vX` in Docker | none stated | READ `https://github.com/vmware-labs/webassembly-language-runtimes/blob/main/python/README.md` |
| componentize-py | releases on GitHub | none stated | READ README |
| SingleStore python-wasi, py2wasm | not reached in the box | — | — |

INFERRED: among Python-on-wasm projects, ours is the only one with a cross-host byte gate at all.
There is no precedent to copy and no bar we are below.

## Part 2: general reproducible-build practice

### Go: host independence by design, two trusted builders, nightly third-party rebuild

- READ (`https://go.dev/blog/rebuild`, Russ Cox, 2023-08-28): Go 1.21 is "perfectly reproducible";
  a toolchain built "on a Linux/x86-64 host, or a Windows/ARM64 host, or a FreeBSD/386 host" gives
  the same bytes. They removed each host input one by one: sorted every list before output, vendored
  the bootstrap libraries, disabled cgo, used `-trimpath`, fixed an ARM floating-point default so
  cross-compiled and native builds matched, moved packaging into the tree, fixed timestamps.
- READ (same): release verification is two builders, "a trusted Linux/x86-64 system and a
  Windows/x86-64 system", and "the two systems must produce bit-for-bit identical archives or else
  we do not proceed with the release". `gorebuild` runs nightly and anyone can run it
  (`https://go.dev/rebuild`). No emulation: everything is cross-compiled.
- READ (same): the only normalized comparisons are for the macOS and Windows installers and signed
  archives, "checked by content" because the signing key cannot be shared.
- INFERRED: Go could do this because the Go compiler is written in Go, which fixes IEEE semantics
  for the compiler's own arithmetic, and because the team owns every line. We own neither clang nor
  LLVM; the analogue for us is to remove the host-dependent input from what we feed the compiler.

### Bitcoin Core: Guix, 19 attesting builders, cross-arch differences handled by dropping a target

- READ (`https://github.com/bitcoin/bitcoin/blob/master/contrib/guix/README.md`): every release
  target (Linux x86_64, arm, aarch64, riscv64, powerpc64, Windows, both macOS) is cross-compiled in
  Guix. Builders upload attestations to `guix.sigs`; `guix-verify` needs "at least one other
  signer". READ (`https://github.com/bitcoin-core/guix.sigs/tree/main/29.0`): 19 signer directories
  for 29.0. The README names no requirement on the builder's own architecture.
- READ (`https://github.com/bitcoin/bitcoin/pull/27897`, merged 2024-03-14): the `powerpc64le`
  output differed when built on x86_64 against aarch64 hosts (GCC 12; "there is also
  non-determinism with GCC-11"). Selective optimization flags "didn't fix all issues". The team
  disabled that target: "less than ideal, but it's not worth having as a blocker". No upstream report
  existed at the time; "a minimal reproducer still needed to be produced".
- READ (`https://github.com/bitcoin/bitcoin/issues/31207`, open since 2024-11): a builder on a
  powerpc64le host gets different Linux and macOS binaries than the x86_64 builders; "apparently
  the optimizer is non-deterministic?"; a maintainer noted "a few swapped instructions
  (`addi`/`li`)" in the related case. Still open; no exception list, no normalizer: a mismatched
  attestation simply does not count.
- INFERRED: the largest independent-builder scheme studied treats a host-dependent compiler the same
  way twice: it does not weaken the comparison; it drops the target or lets the odd builder's
  attestation fail.

### Tor Browser: one build host architecture, two builders per release, manual

- READ (`https://forum.torproject.org/t/tor-project-questions-about-tor-reproducibility/799`):
  "for each Tor Browser release we have two people from the team building and comparing the results
  of the builds", and "checking that builds have been reproduced is still a manual process". The
  build system (rbm) runs in containers on Linux and cross-compiles the other platforms; no second
  host architecture is part of the check (READ, the same thread and `tor-browser-build`'s issues; the
  README itself returned 403).
- READ (`https://lists.torproject.org/pipermail/tor-bugs/2019-April/186315.html`): a container
  build and a non-container build each reproduced on its own machine, yet their Android `.apk`
  differed in the Firefox `.so` files. Treated as a bug to find, not a difference to allow.

### Debian, Arch, Guix, Nix: reproducibility is tested on the same architecture

- READ (`https://tests.reproducible-builds.org/debian/index_variations.html`): Debian varies the
  hostname, user, shell, locale, time zone, date (398 days later), umask, niceness and (on amd64)
  the kernel between its two builds. "CPU type" is listed under "not varied". Each architecture is
  tested on its own machines (amd64 on amd64 hosts, arm64 on `codethink*-arm64`). INFERRED: Debian
  has never promised that an amd64 package built on an arm64 host matches.
- READ (`https://tests.reproducible-builds.org/debian/index_issues.html`): known differences are
  catalogued as some sixty named issue categories ("gcc captures build path", "records build
  flags", "build id differences only") and attached to packages as notes. That is documentation of
  what is still wrong, not an allowance in the comparison: a package with a note is still counted
  unreproducible. `diffoscope` explains the difference and has WebAssembly support through
  `wasm2wat` and `wasm-objdump` since 2018 (READ,
  `https://salsa.debian.org/reproducible-builds/diffoscope/-/merge_requests/17`).
- READ (`https://wiki.archlinux.org/title/Rebuilderd`, rebuilderd README): independent rebuilders
  (reproducible.archlinux.org, wolfpit.net, NYU, HSLU) each rebuild on x86_64 and publish per-package
  results; "if multiple rebuilders you trust report 100% reproducible ... you can be confident". One
  architecture.
- READ (`https://reproducible-builds.org/docs/definition/`): a build is reproducible "given the same
  source code, build environment and build instructions". The environment "would usually include
  dependencies and their versions, build configuration flags and environment variables"; "it is
  preferable to reduce this set of attributes". INFERRED: by the community's own definition, the host
  compiler binary is part of the environment. Our three-host claim is stronger than the definition
  asks. Reducing the set of attributes that matter (removing the construct that exposes the compiler
  difference) is squarely within the recommended direction.
- READ (Guix: `https://lists.gnu.org/r/guix-devel/2021-03/msg00049.html`, bug-guix 2018): Guix can
  build for a foreign architecture through `binfmt_misc` and QEMU ("way slower than
  cross-compilation, because every instruction needs to be emulated"); whether emulated builds match
  native ones was left to "play with this and use `guix challenge`". No result was found. INFERRED:
  our spec 040 is the only case found where emulation was adopted as the way to make a second
  architecture agree, and its 9x cost is in line with Guix's warning.
- READ (`https://bugs.gnu.org/38434`, 2020): `guix challenge` once found an aarch64 `qemu` binary
  differing between builders; an emulator's own build can be the unreproducible one.

### Rust: cross-host (x86_64 against aarch64) reproducibility is still being fixed in 2026

- READ (`https://internals.rust-lang.org/t/name-mangling-different-on-different-architectures/21405`):
  rustc 1.80 on x86_64 and on aarch64 hosts gave different symbol hashes for the same target; the
  fix slated for 1.81 did not fully land.
- READ (`https://patchwork.yoctoproject.org/project/oe-core/patch/20260908160005.2474299-1-alhe@linux.microsoft.com/`,
  2026-09-08, under review): three causes named and patched: the bootstrap compiler's fingerprint
  (host-arch dependent) in the Strict Version Hash; cargo hashing the `host:` triple into
  `-Cmetadata`; a doc-link table and hygiene data serialized in hash-map order. The claim: "Rust
  metadata and compiled libraries are reproducible across mixed-architecture build hosts". Yocto
  carries these as patches to the compiler, which is the carried-patch route.
- INFERRED: a mature toolchain with a reproducibility working group took two years to approach
  cross-host identity, and still does it by patching. We should not expect wasi-sdk to promise it.

### Chromium: deterministic on one machine, for caching, not for cross-host release verification

- READ (`https://chromium.googlesource.com/chromium/src/+/HEAD/docs/deterministic_builds.md`):
  "building Chromium at the same revision should yield the same binary across builds on different
  machines"; bots check it with `compare_build_artifacts`, to cache test results. No cross-architecture
  claim, no release-time independent builders.

### Zig and "the compiler as a wasm file"

- READ (`https://jakstys.lt/2024/zig-reproduced-without-binaries/`, and Zig commits): Zig checks in
  its bootstrap compiler as `zig1.wasm` and rebuilds it from any host through a C translation; a
  third party rebuilt 0.13.0's `zig1.wasm` and got the official hash. The wasm form exists to break
  the self-hosting cycle; the sources do not call host independence a goal, but a wasm program's
  arithmetic is the same on every host by the wasm specification (NaN payloads aside).
- READ (`https://github.com/forkbook/emception`, `https://wasmer.io/posts/clang-in-browser`):
  clang and LLVM have been compiled to wasm and run in a browser (Emception bundles "many llvm
  executables in one binary"; Wasmer runs clang in Chrome, Safari and Firefox, a 100 MB download).
  "Not ready for production" in Emception's own words.
- INFERRED: a clang compiled to wasm32-wasi and run under our pinned wasmtime would give the same
  bytes on every host by construction, as the emulated aarch64 clang does, and likely faster than
  qemu (wasmtime compiles ahead of time; qemu interprets and translates). Nobody ships such a clang
  for wasi-sdk; it would be a toolchain of our own. Recorded as an option, not a recommendation.

## Part 3: two experiments run here (EXECUTED)

Both ran in the scratch folder `prior-art-repro/exp/`, never in the repository. The compilers are
the project's pins: `wasi-sdk-33.0-arm64-macos.tar.gz` (`85c997a2…`, from the repository's
`downloads/`, hash checked) run natively, and `wasi-sdk-33.0-x86_64-linux.tar.gz` (`0ba8b5bf…`,
fetched from the pinned URL, hash checked) run in a `linux/amd64` container of the research
folder's pinned image `debian:trixie-slim@sha256:a29215f6…`, under Rosetta, as spec 040's
experiments did. Both clangs print `clang version 22.1.0-wasi-sdk (… 4434dabb6991…)`. Scripts:
`sweep.sh`, `sweep-numpy.sh`; outputs: `exp/sweep-output.txt`, `exp/sweep-numpy-output.txt`.

### Experiment 1: a flag sweep on the nine-line reproducer

`slot-order.c` is the project's reproducer (`context/upstream/4-llvm-wasm-isel-slot-order/evidence/`).
Base flags: `--target=wasm32-wasip1 -std=c11 -fno-strict-aliasing -ftrapping-math
-fvisibility=hidden -w`, plus the variant.

| variant | aarch64 object | x86_64 object | same? |
|---|---|---|---|
| `-O3` (the build's) | `9afcef294ca52dad` | `7daeec0794b49c01` | no (the project's result, reproduced) |
| `-O2` | `9afcef294ca52dad` | `7daeec0794b49c01` | no |
| `-O1`, `-Os`, `-Oz` | each differs | each differs | no |
| `-O3 -mllvm -enable-misched=0` (the #99396 workaround) | `9afcef29…` | `7daeec07…` | no |
| `-O3 -mllvm -fast-isel` | `9afcef29…` | `7daeec07…` | no (fp128 falls back to SelectionDAG) |
| `-O3 -fno-unroll-loops` | `3e9bd062…` | `2eb258a2…` | no |
| `-O3 -fno-vectorize -fno-slp-vectorize` | `9afcef29…` | `7daeec07…` | no |
| `-O3 -fno-omit-frame-pointer` | `9afcef29…` | `7daeec07…` | no |
| `-O3 -mllvm -pre-RA-sched=source` | differs | differs | no (as spec 040 found) |
| **`-O3 -ffp-contract=off`** | **`bca38dcd95e249c3`** | **`bca38dcd95e249c3`** | **yes** |
| `-O3 -flto` | `2aac0089…` | `2aac0089…` | yes, but trivially: an LTO object is bitcode, no code generated |

Also: the x86_64 clang run with an empty environment (`env -i`) gives the same `7daeec07…`, and the
aarch64 clang gives `9afcef29…` with an empty or a 300 KB environment. INFERRED: the order does not
move with process addresses, which argues against pointer-keyed iteration and for a deterministic
difference between the two compiler builds (such as a host-float heuristic, the #99396 class).
The `setarch -R` (no ASLR) probe could not run in the container ("Operation not permitted").

### Experiment 2: the same flag on the real numpy file

The build's `npy_math_complex.c` was preprocessed with the build's own command from the
repository's `build/numpy-build/compile_commands.json` (`-E -P`, output into the scratch folder):
324,353 bytes, `2193b9bd4d40aadc`, equal to spec 040's. Code-generation flags as spec 040's
Decision 1 (`-O3 -std=c11 -fno-strict-aliasing -ftrapping-math -fvisibility=hidden
-Wno-unsupported-floating-point-opt -w`).

| variant | aarch64 object | x86_64 object | same? |
|---|---|---|---|
| the build's flags | `20ef33440bb2e944` (the build's own object) | `d36897438056e356` (the x86_64 build's) | no |
| **`-ffp-contract=off`** | **`2914eb833ad62c93`** | **`2914eb833ad62c93`** | **yes** |
| `-ffp-contract=fast` | `2914eb833ad62c93` | `2914eb833ad62c93` | yes, the same object as `off` |
| `-O2 -ffp-contract=off` | `21063254043c180d` | `21063254043c180d` | yes |

What the flag changes in the IR (EXECUTED, `-S -emit-llvm` on the aarch64 clang): the build's
flags emit 78 `llvm.fmuladd` calls in this file, 26 each on `f32`, `f64` and `f128`. With `off`
clang emits plain `fmul` and `fadd` instead. With `fast` it also emits plain `fmul` and `fadd` and
leaves fusion to the backend, which on wasm32 has nothing to fuse with; hence the identical object.

What the flag changes in the object (EXECUTED, `llvm-objdump -d` on the two aarch64 objects): the
set of call targets is identical (no `fmal` or other new libcall appears or disappears); the
instruction count drops from 10,484 to 10,092; the opcode histogram shows one fewer `f32.mul` and
one fewer `f64.mul`, six fewer `f32.select`, 28 fewer `i32.add`, otherwise the same arithmetic
opcode counts. INFERRED: the optimizer can share a multiply across two expressions when it is a
plain `fmul`, which it may not do inside a `fmuladd`; that is value-preserving. Since wasm32 lowers
`fmuladd` to a separate multiply and add anyway (no fused instruction without relaxed SIMD), no
floating-point result should change. The project's judge, with numpy's and pandas's own test suites
run in the guest (memo `2026-10-18-numpy-and-pandas-own-tests-in-the-guest.md`), is the check that
settles this as EXECUTED rather than INFERRED.

What it means for the upstream issue: the host dependence sits in the lowering of
`llvm.fmuladd` for `fp128` into `__multf3` and `__addtf3` libcalls with 16-byte result slots. That
is a sharper clue than the draft's "something in the SelectionDAG lowering of the libcall results".
It also resembles #99396: a deterministic per-build difference with no address dependence.

## Part 4: the comparison

| project or practice | cross-host identical? | how verified | how often | independent builders | emulation? |
|---|---|---|---|---|---|
| wasi-sdk (our compiler) | no claim; three different builds of one LLVM | not verified | never | 0 | no |
| Pyodide | no claim | no comparison; builds on Linux and macOS, uploads both | per CI run | 0 | no |
| CPython WASI CI | no claim | none | per CI run | 0 | no |
| WLR, componentize-py | no claim | none | — | 0 | no |
| Go toolchain | yes, by design, any host and arch | two trusted builders must match bit for bit; nightly `gorebuild` by anyone | every release, nightly | 2 + public | no; cross-compile |
| Bitcoin Core | mostly; cross-arch host differences hit twice (GCC) | 19 Guix builders attest; mismatch simply fails to match | every release | 19 | no; cross-compile |
| Tor Browser | one build architecture only | two team members compare, manually | every release | 2 | no; cross-compile in containers |
| Debian | same architecture only ("CPU type: not varied") | two varied builds per package; issue catalogue; diffoscope | continuously | rebuilders per arch | no |
| Arch (rebuilderd) | same architecture only | independent rebuilders publish results | continuously | 4+ | no |
| Guix | foreign-arch builds possible under QEMU; parity with native unverified | `guix challenge` | on demand | build farms | optional, "way slower" |
| Rust toolchain | not yet across x86_64/aarch64 hosts; patches in review 2026 | distro rebuilds | — | distros | no |
| Chromium | one machine class | bots compare artifacts | every build | 0 | no |
| LLVM itself (#99396) | treated as a bug; fixed in 9 days, backported | reporter's two-host diff | — | — | no |
| wasi_python today (spec 040) | yes, three hosts, every tag and dry run | `SHA256SUMS` byte-equal | every release run | 3 (all ours) | yes, the x86_64 compiler, ~65 min |

## Part 5: the options, with what each protects, costs and gives up

The owner asked for the menu to be open. A to D are the original four; E to K come from the prior
art and the experiment. Costs are wall time on the GitHub runners (benchmark facts, never checks):
the emulated x86_64 rebuild took 64.5 minutes against 7m16s for arm64 in spec 040's dry run 2
(READ, spec 040's landing notes).

**A. Native x86_64 rebuild compared by a wasm-aware check that allows exactly the one known
function.**
- Protects against: every difference except the one recorded; keeps a 7-minute x86_64 job.
- Costs: a comparison tool of ours (function-level, hash-pinned allow-list), its own checks, and
  a second notion of "same" beside `SHA256SUMS`. The published hashes would then not be
  reproducible on x86_64, only "explainably different".
- Gives up: the plain claim "the same `SHA256SUMS` from any host". No project studied allows a
  compiler-output difference this way; Go and F-Droid normalize only signatures and installers;
  Debian catalogues differences but still counts the package unreproducible. An allow-list invites
  growth with each new library (023, 037). Useful as a diagnostic (diffoscope with `wasm2wat`), not
  as a gate.

**B. A compile setting that makes both compiler builds agree.** Spec 040 refused this because the
cause was untraced and the only lever tried (the scheduler) failed. The experiment changes the
facts: `-ffp-contract=off` makes both compilers emit the same object for the real numpy file and
the reproducer, and names the construct (`llvm.fmuladd` on `long double`). So B becomes E.

**E. `-ffp-contract=off` in the recipe, x86_64 native in the gate, emulation kept as a fallback for
one release.**
- Protects against: this tie, by removing the IR construct that exposes it, in every file of every
  package we compile, including the C and C++ that 023 and 037 bring. Keeps the three-host
  byte-equal gate and `SHA256SUMS` as the single notion of "same". A new tie of another kind is
  still caught, at 7 minutes instead of 65, with the emulation launcher one line away.
- Costs: every artifact hash changes once (an accepted change with its reason); the judge's guest
  test suites must stay green (INFERRED that they will; the arithmetic is unchanged on wasm32);
  one dry run with the emulation off on the real `ubuntu-24.04` runner to show the three sets equal
  natively; a sentence in the README and the CHANGELOG; the upstream draft gains the `fmuladd` clue.
  Where to set it: the meson cross files and `scripts/wasi-cc` (numpy, pandas, later scipy), and
  CPython's `CFLAGS` through the WASI driver, so one rule holds everywhere; or numpy alone, as the
  smallest thing (§6.4). Everywhere is recommended below, with the reason.
- Gives up: the "fixes the whole class by construction" argument of spec 040, Decision 2. It fixes
  the construct, not the class. Prior art says that is the norm: FreeBSD took a targeted workaround
  for #99396; Bitcoin Core tried flags; Yocto patches three named causes. The whole-class property
  stays available in the fallback.

**C. Keep emulation only for tag runs.**
- Protects against: a tie reaching a published release; dry runs and landings get the 7-minute job.
- Costs: two code paths in the workflow; a tie found only at tag time blocks the release at the
  worst moment (spec 040's Decision 11 fallback would then run under release pressure). Does not
  reduce what a release costs.
- Gives up: the three-host proof on every build-class landing, which is where 023's and 037's new
  compiles would first show a tie. Combined with E it is redundant: E makes the native job the
  gate; the emulation is then not needed on tags either.

**D. Drop the x86_64 rebuild.**
- Protects against: nothing new; saves the hour.
- Costs: the roadmap item and the README claim go back to spec 012's wording.
- Gives up: the check on the architecture most people have. Prior art shows one-architecture
  verification is the norm (Debian, Arch, Tor), so this would not be unusual. But E makes the check
  cost 7 minutes, so the saving no longer buys anything.

**F. Build or patch the compiler from source (wasi-sdk from source with the LLVM fix once traced;
or our own pinned clang binaries for all three hosts from one LLVM build each).**
- Protects against: the whole class, if every host's clang is built by one host compiler with
  `-ffp-contract=off` and the fix.
- Costs: hours per toolchain build per host, a toolchain pin set of our own, every artifact byte
  changes, and the Rust precedent says patching a compiler for cross-host identity is a
  multi-year chase. Spec 040 ruled it out as not the smallest thing.
- Gives up: wasi-sdk's released binaries as the pinned, publisher-hashed inputs.

**G. The compiler as a wasm program under the pinned wasmtime.**
- Protects against: the whole class by construction (wasm arithmetic is host-independent); likely
  faster than qemu.
- Costs: nobody ships clang as wasm32-wasi for wasi-sdk; building LLVM to wasm is a project (Emception
  took "slow" Docker builds and is "not ready for production"); CPython's configure and meson would
  drive a wrapper, as the launcher does today. A toolchain of our own, again.
- Gives up: the pinned wasi-sdk binaries. Recorded because it is the principled version of what the
  emulation does; not recommended now.

**H. One reference architecture compiles; the other hosts rebuild and compare only what they can
build natively.** (Go's model: all targets from one trusted host.)
- Protects against: nothing a compiler difference could cause, because only one compiler build is
  ever used; verification becomes "two builders on arm64 agree" plus "x86_64 reproduces the zip,
  `MANIFEST`, licences and the snapshot step from the arm64 reactor".
- Costs: the x86_64 job becomes a partial rebuild with its own comparison logic; the README must say
  which layers x86_64 verifies.
- Gives up: "anyone can rebuild `python.wasm` on x86_64 and get our hash". That is exactly the
  roadmap item. Weaker than E for the same price.

**I. A different cadence: native x86_64 with E on every run; a scheduled (weekly or per-release)
emulated run as a cross-check while the LLVM issue is open.**
- Protects against: a regression in E's property between releases, at no cost to landings.
- Costs: a scheduled workflow and someone reading its result; the hour, but off the critical path.
- Gives up: little. Optional companion to E; the three-host gate already proves the same thing on
  each tag.

**J. Third-party rebuilders and attestations** (Bitcoin Core's `guix.sigs`, Go's `gorebuild`, Arch's
rebuilderd).
- Protects against: our own CI being the only witness (a compromised or misconfigured runner).
- Costs: a documented rebuild procedure per host (the README has it), a place to collect
  attestations, and people. Go needed two trusted machines; Bitcoin Core has 19 volunteers.
- Gives up: nothing; it is additive. Not a substitute for a fast in-tree gate. E makes an x86_64
  rebuild cheap enough for a volunteer to run in seven minutes, which is what makes J realistic.

**K. Upstream fix, then a wasi-sdk bump that removes every workaround.** This is spec 040's exit
plan and stays the end state. #99396 shows LLVM fixes this class fast once a reproducer names the
cause. E hands the issue the `fmuladd` clue and a one-flag reproducer, which is what a maintainer
needs; `-mllvm -print-after-all` on the two hosts with and without the flag will localize the pass.

## Part 6: recommendation

1. **Take E.** Add `-ffp-contract=off` to every compile in the recipe (CPython through the WASI
   driver's `CFLAGS`, numpy and pandas through the meson cross files and `scripts/wasi-cc`, and
   whatever 023 and 037 add). Everywhere, not numpy alone, because the construct is `fmuladd` on
   `long double`, which any new C or C++ with complex or `long double` arithmetic can produce, and
   because one rule in one place is what a reviewer can check. It is a recipe item (§4.1's first
   kind), it costs no time, and on wasm32 it changes no arithmetic (INFERRED; the judge's guest
   suites make it EXECUTED).
2. **Run x86_64 natively in the gate.** Switch `LINUX_X86_64_COMPILER_SDK_DIR` back to the host's
   own SDK and drop the emulation branch from the x86_64 job. Keep `scripts/clang-emulated`, the
   five pins and step 10's branch in the tree for one release, switched off, as the same-day
   fallback spec 040's Decision 11 already describes; delete them in the release after if the gate
   holds. The expected x86_64 rebuild time then matches arm64's, about 7 minutes (INFERRED from
   the native-under-Rosetta figure: 1,406 s native against 11,669 s emulated in spec 040's notes).
3. **Prove it the way spec 040 proved its change**, in a specification of its own: the two objects
   above equal with the flag (EXECUTED here; the builder reproduces it into the research folder);
   `uv run pytest` green with the new hashes accepted with the reason; one dry run on
   `ubuntu-24.04` with the emulation off giving the same `SHA256SUMS` as macOS and arm64 Linux.
   Record the native x86_64 wall time as a benchmark fact. If the dry run differs, the fallback is
   the launcher, already in the tree.
4. **Sharpen the upstream draft** with the `fmuladd` finding and the two tables above, and keep the
   owner's "run it on real x86_64 first" condition. LLVM's record on #99396 (report to fix in nine
   days, backported) makes K realistic.
5. **Do not take A** as a gate. Keep `SHA256SUMS` byte-equality as the one meaning of "same", as
   every project studied does for compiler output. Use diffoscope's wasm support, or the project's
   own `cmp`-and-link-map method, as the diagnostic when the gate fails.
6. **C, D and H are not needed** once the x86_64 job costs seven minutes. **I** is optional and
   cheap if the owner wants a watch on the open LLVM issue. **J** is for later; E is what makes it
   feasible. **F** and **G** are recorded as the principled routes and are not worth their cost
   while a flag does the job and upstream is responsive.

The one-line version: a recipe flag we had not tried makes both compilers agree on the real file, so
the hour of emulation can go, the three-host gate can stay, and the emulation stays in the tree one
release as the parachute.

## Appendix A: sources

LLVM and wasi-sdk
- https://github.com/WebAssembly/wasi-sdk/blob/main/.github/workflows/main.yml
- https://github.com/WebAssembly/wasi-sdk/blob/main/ci/docker-build.sh and `ci/docker/Dockerfile`
- https://github.com/WebAssembly/wasi-sdk/blob/main/RELEASING.md
- https://github.com/llvm/llvm-project/issues/99396
- https://lists.llvm.org/pipermail/llvm-branch-commits/2024-August/035941.html (the 19.x backport)
- https://reviews-dev.freebsd.org/R11:a4e0cb2fd99adef4cbd4f778be729a079a5f2dea (FreeBSD's temporary patch)
- https://llvm.org/docs/CMake.html (`LLVM_REVERSE_ITERATION`)
- https://llvm.org/docs/ProgrammersManual.html (pointer-keyed containers)
- https://github.com/llvm/llvm-project/pull/161355 (wasm `fmuladd` to fma only with relaxed SIMD)
- https://gitlab.torproject.org/tpo/applications/tor-browser-build/-/issues/40802 (wasi-libc)

Python on wasm
- https://github.com/pyodide/pyodide/blob/main/.github/workflows/main.yml
- https://pyodide.org/en/stable/development/building-from-sources.html
- https://github.com/python/cpython/blob/main/.github/workflows/reusable-wasi.yml
- https://github.com/vmware-labs/webassembly-language-runtimes/blob/main/python/README.md
- https://github.com/bytecodealliance/componentize-py/blob/main/README.md

General practice
- https://go.dev/blog/rebuild and https://go.dev/rebuild
- https://github.com/bitcoin/bitcoin/blob/master/contrib/guix/README.md
- https://github.com/bitcoin-core/guix.sigs/tree/main/29.0
- https://github.com/bitcoin/bitcoin/pull/27897 and https://github.com/bitcoin/bitcoin/issues/31207
- https://forum.torproject.org/t/tor-project-questions-about-tor-reproducibility/799
- https://lists.torproject.org/pipermail/tor-bugs/2019-April/186315.html
- https://tests.reproducible-builds.org/debian/index_variations.html
- https://tests.reproducible-builds.org/debian/index_issues.html
- https://reproducible-builds.org/docs/definition/
- https://salsa.debian.org/reproducible-builds/diffoscope/-/merge_requests/17 (wasm support)
- https://wiki.archlinux.org/title/Rebuilderd
- https://lists.gnu.org/r/guix-devel/2021-03/msg00049.html and https://bugs.gnu.org/38434
- https://internals.rust-lang.org/t/name-mangling-different-on-different-architectures/21405
- https://patchwork.yoctoproject.org/project/oe-core/patch/20260908160005.2474299-1-alhe@linux.microsoft.com/
- https://chromium.googlesource.com/chromium/src/+/HEAD/docs/deterministic_builds.md
- https://jakstys.lt/2024/zig-reproduced-without-binaries/
- https://github.com/forkbook/emception and https://wasmer.io/posts/clang-in-browser

Not reachable in the box (403 or 404), so not cited for content: the Guix manual's virtualization
and native-builds pages, `tor-browser-build`'s README, `cpython-wasi-build`'s README on `main`.

## Appendix B: clones, downloads and the scratch folder

- **Clones: none.** `prior-art-repro/clones/` is empty. Everything was read on the web. No code
  was copied from any project.
- **Downloads** (untrusted inputs, unpacked only under the scratch folder, run only as build tools):
  - `wasi-sdk-33.0-x86_64-linux.tar.gz` from the pinned URL in `scripts/00_download.sh`; SHA-256
    `0ba8b5bfaeb2adf3f29bab5841d76cf5318ab8e1642ea195f88baba1abd47bce`, checked against
    `downloads/SHA256SUMS` before use (`shasum -a 256 -c`).
  - `wasi-sdk-33.0-arm64-macos.tar.gz`, read from the repository's `downloads/`; SHA-256
    `85c997a2665ead91673b5bb88b7d0df3fc8900df3bfa244f720d478187bbdc78`, checked the same way.
  - Docker image `debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f`,
    the research folder's pinned image, run as `linux/amd64` (Rosetta). Containers removed after use.
- **Files:** `sweep.sh`, `sweep-numpy.sh` (the scripts); `exp/slot-order.c` (a copy of the
  project's reproducer); `exp/npy_math_complex.i` (regenerated from the repository's build tree with
  the build's own command; numpy's and wasi-libc's text, not to be committed); `exp/*.o` (the
  objects, named `a-`/`x-` for the reproducer and `na-`/`nx-` for numpy, by compiler host);
  `exp/sweep-output.txt`, `exp/sweep-numpy-output.txt`.
- **The repository:** read only. `git status` in it shows only the pre-existing untracked
  `test_app/`. The preprocessing step ran with `build/numpy-build` as its working directory and
  wrote only into the scratch folder (`-E -P -o <scratch>/npy_math_complex.i`, no depfile).
