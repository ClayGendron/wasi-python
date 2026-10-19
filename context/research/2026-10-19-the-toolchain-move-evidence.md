# The toolchain move's evidence: wasi-sdk 34 builds the same bytes, and what moved

- **Status:** evidence for spec 086's build, 2026-10-19. Not a decision: the specification
  decides; this memo records what its build ran. The folder beside it holds the files.
- **Owner:** Clay Gendron
- **Builder:** a build agent (Claude Opus 5.5), on `spec/086-wasi-sdk-34` in its own worktree,
  at `810c032` (the recipe) on main `3866f56`.
- **Stands on:** `2026-10-19-the-try-table-order-in-llvm.md` (the cause and the fix).

Labels: **EXECUTED** (run here), **READ**, **INFERRED**. Every number has its file beside it. The
files here are 086's own: `surface_probe.py`, `readme_edges.py`, `fuel_moves.py`,
`wasm_sections.py`, `run-086-container.sh`, `control/`, `sha256sums/`, and the outputs named below.

## 1. The checks, seen failing first (EXECUTED, `seen-failing.txt`)

- **Check (a), the try_table reproducer**, on a wasi-sdk 33 build of today's tree:
  `wasi-sdk-33.0-arm64-macos: 2 objects in 64 runs (4e0dd4cb42bc x13, 601494f76b82 x51)`. With
  `build/tools` moved aside: `no build/tools/wasi-sdk-*/bin/clang: nothing was compiled`. On every
  wasi-sdk 34 build: one object in 64 runs.
- **Check (c), the recorded configure results**, on the same 33 tree: exactly the ten lines
  `HAVE_DUP`, `HAVE_DUP2`, `HAVE_DUP3`, `HAVE_GETC_UNLOCKED`, `HAVE_PIPE2`, `HAVE_PPOLL`,
  `HAVE_PTHREAD_GETCPUCLOCKID`, `HAVE_SEM_GETVALUE`, `HAVE_SEM_OPEN`, `HAVE_SEM_TIMEDWAIT`, each
  recorded and not built; nothing else.
- **Check (b), dup refused as ENOTSUP**, on a wasi-sdk 34 set without the refusal: `os.dup(1)
  EINVAL` on both binaries, every other line as expected. With `recipes/fcntl_dup_refusal.c`
  linked: passes on both.

## 2. The same bytes (EXECUTED, `sha256sums/`)

| Build | From | `SHA256SUMS` |
|---|---|---|
| macOS A | empty `build/` | `aac927dc826a9bd0d2f09aec77bf589991565dc9eb531daaa66772919e38c86f` |
| macOS B | empty `build/` | the same |
| linux/arm64 container, 1 | empty `downloads/` (staged pins re-verified) and `build/`, a clone at `810c032` | the same |
| linux/arm64 container, 2 | empty `build/` | the same |
| linux/amd64 container (Rosetta), its own x86_64 clang | as arm64 | the same |

The set: `python.wasm` `5f52d6480ee1ca80…` (41,167,259 bytes), the snapshot `89cdd3ebd04c6eb2…`
(44,695,908), the zip `9e22ff232afb1bf1…` (22,197,155).

## 3. What moved in the binary (EXECUTED, `sections-a7-vs-086.txt`)

Against main's set (0.1.0a7's release tarball, `fc59b977…`, whose `python.wasm` is the accepted
`ab78e893…`): `python.wasm` +67,598 bytes (+0.164%), the snapshot +61,925 (+0.139%), the zip −18.
Code +45,497, name +17,779, data +4,256, function +75, element −9; 70 more function bodies
(40,577 → 40,647). The same 43 imports, from `host` and `wasi_snapshot_preview1` only; the same
exports, types, tags and target features. The refusal itself is 208 of those bytes (a relink of
the same build with and without it: 41,167,051 → 41,167,259).

## 4. What a program sees (EXECUTED, `surface_diff.txt`)

`surface_probe.py` on both binaries of main's set and of 086's, 147 builtin modules each. The
diff, on each binary: `posix` gains `dup2` and `pipe2`, `select` gains `PIPE_BUF`, `time` gains
`pthread_getcpuclockid`; `sysconfig` shows the ten `HAVE_*` going 0 → 1, and `LIBOBJS` going
from `Python/dup2$U.o` to empty. Nothing else. The `LIBOBJS` line follows from `HAVE_DUP2`:
configure compiles CPython's replacement `dup2` only when the libc lacks one (READ,
`configure.ac:5882`, `AC_REPLACE_FUNCS([dup2])`). It is a build variable; no program behaviour
reads it.

## 5. The other libraries' configure results (EXECUTED, `configure-diff-without-paths.txt`)

Every generated config header (libxml2's, libxslt's, xz's, HarfBuzz's, libraqm's, numpy's
`config.h`, `_numpyconfig.h` and CPU-dispatch header, zlib's `zconf.h`) is byte for byte the same
in a wasi-sdk 33 and a wasi-sdk 34 build of the same tree. The autoconf caches of libxml2,
libxslt and xz differ only in the SDK's folder name in the tool paths. Every meson probe result
(FreeType, HarfBuzz, libraqm, matplotlib, numpy, pandas, SheenBidi) is the same. Only CPython's
configure moved, by the ten results above, which `ac_cv_func_*` and `ac_cv_have_getc_unlocked` show.

## 6. Depths: the README's trap rows (EXECUTED, `edges-*.jsonl`, `edges-compare.txt`)

`readme_edges.py` bisects each of fifteen README rows (spec 071's and spec 087's programs) on both
binaries, metered, on main's set and on 086's, darwin-arm64. **Every edge is the same on both
sets**: expat 130, a freed list 2,325, a freed dict 1,415, `json.loads` 1,204, `repr` 1,912, `==`
1,551, brackets 141, a freed traceback 2,957, XPath 356 parentheses and 4,055 predicates, XSLT
`call-template` 461, copying `apply-templates` 450 and bare 662, C14N 1,478, RelaxNG 395 (last depth
that completes). The README gives the lower host's (x86-64's) numbers, so its rows are not these;
since no darwin edge moved, the rows stand (INFERRED for x86-64; the amd64 container's criterion 5
run is the check). The README's zip-reader fuel figures moved under 0.4% on the same programs
(`readme-fuel.txt`), so their rounded values stand.

## 7. Fuel (EXECUTED, `growth-vs-accepted-prelim.txt`; preliminary)

The full judge (`uv run pytest -n 3`, set B, darwin-arm64) against `accepted.json`: 164 fuel rows,
62 up and 98 down by more than 0.01%, from −0.444% to +2.645%; the sum 3,097.06 G → 3,103.74 G
(+0.22%). Two rows above 1%: numpy-core +2.645% (203.36 G → 208.73 G) and the compress job +1.428%.
The per-group table is in the file. This is **not** spec 086's A/B: that is measured on the base
086 lands on, after spec 083, as Decision 9 says, and replaces this section at the landing.

## 8. The layout control (EXECUTED, `layout-control.txt`, `control/`)

Spec 073's build review found numpy-core's fuel keyed to `bool`'s address. On main's set
`id(bool)` is `0x15c5558`; on 086's it is `0x15c6548`, 0xFF0 bytes higher (the data section grew
4,256 bytes). Converting twenty lists of 32,768 bools with `np.array`, net of numpy's import, costs
523.3 M fuel on main's set and 688.4 M on 086's (snapshot): about 798 and 1,050 fuel per bool,
+31.5%. That is the mechanism 073 measured, at work in 086's set. How much of numpy-core's +2.645%
it explains is the A/B's question (Decision 9), asked on the landing base.

## 9. Criterion 5, before landing (EXECUTED, the container outputs)

- **linux/arm64:** the hostile guest's stack-overflow, recursion, deep-list, window, deep-data and
  dup checks: 49 passed. The CPython suites `cpython-a`, `cpython-b` and `cpython-c` pass; their 16
  classes and trap entries stand as gaps. Checks (a) and (c) pass on the aarch64 Linux clang.
- **linux/amd64 (Rosetta):** the same 49 hostile checks pass on Cranelift's x86-64 code (every recursion floor, the 128 KiB window, the deep-data limits); `cpython-a`, `-b` and `-c` pass with their 16 gaps; checks (a) and (c) pass on the x86_64 Linux clang. Neither container printed "trap entries with no trap here", which the darwin judge prints for `c-stack-itertools-tee`: on both Linux hosts every open trap entry trapped as named.

One line: wasi-sdk 34 gives one `SHA256SUMS` from every host tried, the guest sees three new
failing functions and one constant, and no depth moved; numpy-core's fuel moves with `bool`'s
address.
