# The toolchain move's evidence: wasi-sdk 34 builds the same bytes, and what moved

- **Status:** evidence for spec 086's build, 2026-10-19. Not a decision: the specification decides; this memo records what its build ran. The folder beside it holds the files.
- **Owner:** Clay Gendron
- **Builder:** a build agent (Claude Opus 5.5), on `spec/086-wasi-sdk-34` in its own worktree, at `810c032` (the recipe) on main `3866f56`.
- **Stands on:** `2026-10-19-the-try-table-order-in-llvm.md` (the cause and the fix).

Labels: **EXECUTED** (run here), **READ**, **INFERRED**. Every number has its file beside it. The files here are 086's own: `surface_probe.py`, `readme_edges.py`, `fuel_moves.py`, `wasm_sections.py`, `run-086-container.sh`, `run-086-traps.sh`, `control/`, `sha256sums/`, and the outputs named below.

## 1. The checks, seen failing first (EXECUTED, `seen-failing.txt`)

- **Check (a), the try_table reproducer**, on a wasi-sdk 33 build of today's tree: `wasi-sdk-33.0-arm64-macos: 2 objects in 64 runs (4e0dd4cb42bc x13, 601494f76b82 x51)`. With `build/tools` moved aside: `no build/tools/wasi-sdk-*/bin/clang: nothing was compiled`. On every wasi-sdk 34 build: one object in 64 runs.
- **Check (c), the recorded configure results**, on the same 33 tree: exactly the ten lines `HAVE_DUP`, `HAVE_DUP2`, `HAVE_DUP3`, `HAVE_GETC_UNLOCKED`, `HAVE_PIPE2`, `HAVE_PPOLL`, `HAVE_PTHREAD_GETCPUCLOCKID`, `HAVE_SEM_GETVALUE`, `HAVE_SEM_OPEN`, `HAVE_SEM_TIMEDWAIT`, each recorded and not built; nothing else.
- **Check (b), dup refused as ENOTSUP**, on a wasi-sdk 34 set without the refusal: `os.dup(1) EINVAL` on both binaries, every other line as expected. With `recipes/fcntl_dup_refusal.c` linked: passes on both.

## 2. The same bytes (EXECUTED, `sha256sums/`)

| Build | From | `SHA256SUMS` |
|---|---|---|
| macOS A | empty `build/` | `aac927dc826a9bd0d2f09aec77bf589991565dc9eb531daaa66772919e38c86f` |
| macOS B | empty `build/` | the same |
| linux/arm64 container, 1 | empty `downloads/` (staged pins re-verified) and `build/`, a clone at `810c032` | the same |
| linux/arm64 container, 2 | empty `build/` | the same |
| linux/amd64 container (Rosetta), its own x86_64 clang | as arm64 | the same |

The set: `python.wasm` `5f52d6480ee1ca80…` (41,167,259 bytes), the snapshot `89cdd3ebd04c6eb2…` (44,695,908), the zip `9e22ff232afb1bf1…` (22,197,155).

## 3. What moved in the binary (EXECUTED, `sections-a7-vs-086.txt`)

Against main's set (0.1.0a7's release tarball, `fc59b977…`, whose `python.wasm` is the accepted `ab78e893…`): `python.wasm` +67,598 bytes (+0.164%), the snapshot +61,925 (+0.139%), the zip −18. Code +45,497, name +17,779, data +4,256, function +75, element −9; 70 more function bodies (40,577 → 40,647). The same 43 imports, from `host` and `wasi_snapshot_preview1` only; the same exports, types, tags and target features. The refusal itself is 208 of those bytes (a relink of the same build with and without it: 41,167,051 → 41,167,259).

## 4. What a program sees (EXECUTED, `surface_diff.txt`)

`surface_probe.py` on both binaries of main's set and of 086's, 147 builtin modules each. The diff, on each binary: `posix` gains `dup2` and `pipe2`, `select` gains `PIPE_BUF`, `time` gains `pthread_getcpuclockid`; `sysconfig` shows the ten `HAVE_*` going 0 → 1, and `LIBOBJS` going from `Python/dup2$U.o` to empty. Nothing else. The `LIBOBJS` line follows from `HAVE_DUP2`: configure compiles CPython's replacement `dup2` only when the libc lacks one (READ, `configure.ac:5882`, `AC_REPLACE_FUNCS([dup2])`). It is a build variable; no program behaviour reads it. Two values the probe does not compare move as well (the build review's B2, confirmed here, EXECUTED, `b2-version-clocks.txt`): `sys.version` names Clang 23.1.0, and `time.CLOCK_MONOTONIC` and `time.CLOCK_REALTIME` are 22668564 and 22668568 (22664664 and 22664668 on main's set): in wasi-libc a `clockid_t` is the address of a static object (INFERRED from the values moving with the data segment), so both ids moved 0xF00 with it.

## 5. The other libraries' configure results (EXECUTED, `configure-diff-without-paths.txt`)

Every generated config header (libxml2's, libxslt's, xz's, HarfBuzz's, libraqm's, numpy's `config.h`, `_numpyconfig.h` and CPU-dispatch header, zlib's `zconf.h`) is byte for byte the same in a wasi-sdk 33 and a wasi-sdk 34 build of the same tree. The autoconf caches of libxml2, libxslt and xz differ only in the SDK's folder name in the tool paths. Every meson probe result (FreeType, HarfBuzz, libraqm, matplotlib, numpy, pandas, SheenBidi) is the same. Only CPython's configure moved, by the ten results above, which `ac_cv_func_*` and `ac_cv_have_getc_unlocked` show.

## 6. Depths: the README's trap rows (EXECUTED, `edges-*.jsonl`, `edges-compare.txt`)

`readme_edges.py` bisects each of fifteen README rows (spec 071's and spec 087's programs) on both binaries, metered, on main's set and on 086's, darwin-arm64. **Every edge is the same on both sets**: expat 130, a freed list 2,325, a freed dict 1,415, `json.loads` 1,204, `repr` 1,912, `==` 1,551, brackets 141, a freed traceback 2,957, XPath 356 parentheses and 4,055 predicates, XSLT `call-template` 461, copying `apply-templates` 450 and bare 662, C14N 1,478, RelaxNG 395 (last depth that completes). The README gives the lower host's (x86-64's) numbers, so its rows are not these; since no darwin edge moved, the rows stand (INFERRED for x86-64; the amd64 container's criterion 5 run is the check). The README's zip-reader fuel figures moved under 0.4% on the same programs (`readme-fuel.txt`), so their rounded values stand.

## 7. Fuel (EXECUTED, `growth-vs-accepted-prelim.txt`; preliminary)

The full judge (`uv run pytest -n 3`, set B, darwin-arm64) against `accepted.json`: 164 fuel rows, 62 up and 98 down by more than 0.01%, from −0.444% to +2.645%; the sum 3,097.06 G → 3,103.74 G (+0.22%). Two rows above 1%: numpy-core +2.645% (203.36 G → 208.73 G) and the compress job +1.428%. The per-group table is in the file. This is **not** spec 086's A/B: that is measured on the base 086 lands on, after spec 083, as Decision 9 says, and replaces this section at the landing.

## 8. The layout control (EXECUTED, `layout-control.txt`, `control/`)

Spec 073's build review found numpy-core's fuel keyed to `bool`'s address. On main's set `id(bool)` is `0x15c5558`; on 086's it is `0x15c6548`, 0xFF0 bytes higher (the data section grew 4,256 bytes). Converting twenty lists of 32,768 bools with `np.array`, net of numpy's import, costs 523.3 M fuel on main's set and 688.4 M on 086's (snapshot): about 798 and 1,050 fuel per bool, +31.5%. That is the mechanism 073 measured, at work in 086's set. How much of numpy-core's +2.645% it explains is the A/B's question (Decision 9), asked on the landing base.

## 9. Criterion 5, before landing (EXECUTED, the container outputs)

- **linux/arm64:** the hostile guest's stack-overflow, recursion, deep-list, window, deep-data and dup checks: 49 passed. The CPython suites `cpython-a`, `cpython-b` and `cpython-c` pass; their 16 classes and trap entries stand as gaps. Checks (a) and (c) pass on the aarch64 Linux clang.
- **linux/amd64 (Rosetta):** the same 49 hostile checks pass on Cranelift's x86-64 code (every recursion floor, the 128 KiB window, the deep-data limits); `cpython-a`, `-b` and `-c` pass with their 16 gaps; checks (a) and (c) pass on the x86_64 Linux clang. Spec 065's nine trap-entry checks (`-k test_upstream_trap`) were not in that first run, which selected only the groups and their classes, so it showed nothing about them (the build review's B1). They were run afterwards in both containers, on the same set (`SHA256SUMS` `aac927dc…`, copied in; `run-086-traps.sh`, `traps-linux-*.txt`): on linux/amd64 all nine trap as named, `c-stack-itertools-tee` included ("trap at or after test.test_itertools.TestPurePythonRoughEquivalents.test_tee_recipe"); on linux/arm64 eight trap as named and `c-stack-itertools-tee` reports "no trap on this host", as on darwin, which an open entry accepts (it traps on Linux x86-64 only). Each stays a gap closed by 078.

## 10. The rebase: S5's hash flag and the zip fix folded in, rebuilt, and the A/B (EXECUTED, `rebase/`)

The builder rebased 086 onto main `45b917c` (083 and 089), then `97be88a` (078), then `e8ba20a` (wave 01: 087, 085, 084, 091). Two changes were folded in at the owner's word (`../decisions.md`, 2026-10-19):

- **S5:** step 20 passes `--with-hash-algorithm=siphash13`. CPython's configure falls back to FNV when a cross build cannot run its aligned-access probe.
- **The zip fix:** step 70 copies the generated `_missing_stdlib_info.py`, which spec 078's build review found missing (its F2).

**Seen failing first** (`rebase/seen-failing.txt`), each on the `aac927dc` set:

- the hash check gave `fnv 32 32 64` on both binaries;
- the zip check gave "Standard library module '_tkinter' was not found";
- check (c), once built, named `+Py_HASH_ALGORITHM 3 (built, not recorded)` on macOS and in both containers.

**The same bytes.**

| Base | Build | `SHA256SUMS` |
|---|---|---|
| `45b917c` (at `45efcc3`) | macOS A (empty `downloads/` and `build/`), macOS B (empty `build/`), linux/arm64, linux/amd64 (Rosetta) | `4586ce2a…` (all four) |
| `e8ba20a` (at `77d2a81`) | macOS (empty `build/`), linux/arm64 | `6d362277…` (both) |

- On `e8ba20a`, 087's carried regex patch is the first code clang 23 compiles here (Decision 10's trigger). It applied cleanly, and python.wasm grew 200 bytes (087 measured +202 on 33).
- In the containers, on `45efcc3` (`rebase/container-linux-*.txt`): 51 hostile checks pass; `cpython-a`, `-b` and `-c` pass; and all nine trap entries trap as named on linux/amd64 (`rebase/traps-linux-amd64.txt`).
- On `77d2a81`, after 078, linux/arm64: 52 hostile checks pass (078's 8 MiB rows among them); `cpython-a`, `-b` and `-c` pass with their 16 classes; checks (a), (c) and the zip check pass.

**What the hash flag is** (`rebase/hash-probe.txt`). Both binaries report `sys.hash_info` `siphash13`, width 32, hash bits 64, seed bits 128. The snapshot's key is fixed: `hash_randomization` is 0, and `hash('abc')` is `69611762` in every call. The plain reactor draws a fresh key in every call. A fixed key is public, so the README states the hash and adds a *Not protected* item.

**The A/B** (`rebase/ab-097be88a.txt`, `rebase/ab.py`). Four full judges, `uv run pytest -n 3`, one judge commit, on 078's base, darwin-arm64:

- **M:** main's set, the same bytes as 0.1.0a7's (`ab78e893`); no build input changed since that tag.
- **T:** wasi-sdk 34 (`aac927dc`).
- **TZ:** T plus the zip file, steps 70 to 90 re-run.
- **F:** TZ plus siphash13 (`4586ce2a`).

Each step changes one thing, so each row's move in a step is that change's.

| Step | Fuel rows | Up / down (>0.01%) | Median | Range | Sum | Bytes |
|---|---|---|---|---|---|---|
| M→T, the toolchain | 169 | 66 / 100 | −0.097% | −0.365% to +2.706% | +0.230% | python.wasm +67,598, snapshot +61,925, zip −18 |
| T→TZ, the zip file | 171 | 102 / 22 | +0.015% | −0.230% to +1.094% | −0.004% | snapshot +14,967, zip +1,497 |
| TZ→F, the hash flag | 173 | 159 / 12 | +0.737% | −2.475% to +1.836% | +0.230% | python.wasm −380 (code −409), snapshot +5,966, zip +17 |
| M→F, the whole | 169 | 164 / 3 | +0.582% | −2.519% to +2.700% | +0.460% | python.wasm +67,218 (+0.164%), snapshot +82,858 (+0.186%), zip +1,496 |

(`cpython-a` is not among M's and T's rows. With 078's class closed it fails on any set that lacks the zip file, as it should.)

- **The toolchain's rows** repeat the preliminary table.
  - numpy-core is +2.706% (203.33 G → 208.83 G). It is the layout mechanism, measured again (`rebase/layout-control.txt`). `bool` sits 0xFF0 higher in T, TZ and F alike. Twenty 32,768-bool conversions, net of numpy's import, cost 523.5 M on M, 688.2 M on T and 688.5 M on F. So the hash flag adds nothing to that row.
  - Spec 091 has landed on `e8ba20a`. It takes `test_string_comparisons`' fuel out of the ratchet as a fact, so on the landing base this row loses the layout part.
  - The compress job is +1.430%, the toolchain's own (the backend's choices, INFERRED, as in section 7).
- **The zip file's rows** are small.
  - The one above 1%, `test_uncaught_errors_print_as_native[snapshot]` (+1.094%), is traced: the program prints a traceback. traceback's import now finds `_missing_stdlib_info` in the zip and loads it, where it used to fail to find it.
  - The snapshot runs' +0.3% (about 50 k fuel each) is INFERRED: the snapshot's image is 14,967 bytes larger, and its heap layout moved. Not traced.
- **The hash flag's rows** are the guest hashing strings with SipHash-1-3 instead of FNV.
  - Measured on its own (`rebase/hashcost.txt`): hashing 200,000 fresh 8-character strings costs 142.7 more instructions per string on F than on TZ, about 6% of a loop-and-hash.
  - A plain start hashes every string it interns, so the plain-start rows rise about 1.43% (about 2.4 M fuel).
  - The snapshot programs that import regex or pickle rise up to 1.84%.
  - `test_pickling_a_deep_list_raises` falls 2.48%. INFERRED: fewer dict probe collisions under SipHash's spread.
- **The bounds** (Decision 9), each against M:
  - the fuel sum rose +0.460%, under 1%;
  - python.wasm rose +0.164% and the snapshot +0.186%, each under 1%;
  - the zip changed beyond `_sysconfigdata` by exactly the folded-in file, which the owner asked for.
  - No row's A/B rise is over 3%. numpy-core's 1 to 3% rise is explained by the control above, and its layout part is now 091's fact.

**078's edges** (Decision 8). 078's own script (`2026-10-19-the-runners-own-stack/edges8.py`) ran at 8 MiB on darwin, on M and on F, for the seven rows that still trap. Every edge is the same on both sets and equals 078's record: free list 37,433, tuple 37,434, dict 22,785, `hash` of a tuple 40,313, compile 58,227 terms, C14N 23,818, and a raised recursion limit unbounded to 400,000 (`rebase/edges-078-8m-arm64-*.jsonl`). x86-64 was not re-measured here. The dry run's Linux x86-64 job runs 078's checks.

One line: wasi-sdk 34 gives one `SHA256SUMS` from every host tried, the guest sees three new failing functions and one constant, strings hash with SipHash-1-3, no depth moved, and numpy-core's fuel moves with `bool`'s address.
