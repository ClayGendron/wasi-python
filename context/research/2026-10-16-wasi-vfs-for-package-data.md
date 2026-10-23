# wasi-vfs for package data

- **Status:** research, 2026-10-16
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5). Box: about 2 hours, widened mid-task by the owner's direction (findings 7 to 9: the stdlib zip inside the binary, no preopen at all, a writable area, and a root on top of packed files). Stopped inside the box. Where it stopped is listed at the end.
- **Feeds:** the matplotlib specification, and the owner's direction that the runtime should need nothing from the host filesystem unless the embedder grants it.
- **Stands on:** `2026-10-16-where-package-data-lives.md` (options C2 and C3, and its finding 2 on the snapshotted preopen table); `2026-10-16-making-the-snapshot-byte-reproducible.md`; spec 003 (the reactor, the four `--wrap` flags, step 80).

## The question

Can wasi-vfs pack read-only package data (matplotlib's `mpl-data`, and later other data folders) inside our artifacts, so the embedder still hands the guest one preopen, or none? What does it cost, and is it safe?

Three terms first.

- A **preopen** is a host directory the embedder hands the guest under a guest path. Under WASI preview1 it is the only way a guest sees a file.
- **wasi-vfs** is a library linked into the guest plus a command-line tool. The tool copies host directories into the module's memory. The library then answers file calls on those paths from memory.
- **Packing** is that copy step (`wasi-vfs pack`). It produces a new `.wasm` with the files inside.

## Method

- **Read:** wasi-vfs, cloned shallow into `context/prior_art/wasi-vfs` at `0f4db4b` (tag v0.6.3, 2026-04-12). Licence recorded in `context/prior_art/README.md`. Also its GitHub releases and open issues (through `gh`), and Wizer's `_initialize` handling in the wasmtime clone (`crates/wizer/src/wasmtime.rs:62-70`, `rewrite.rs:128-136`).
- **Downloads** (each in its own empty directory in the session scratchpad, checked against the SHA-256 GitHub publishes for the asset, run only as a build tool or under wasmtime):

  | asset (v0.6.3) | SHA-256 | inner file, SHA-256 |
  |---|---|---|
  | `libwasi_vfs-wasm32-unknown-unknown.zip` (3,380,336 B) | `f94dc7fdabdefc0fed78b70f1ab100207db0558cbabb004dd9e5a0bdeec4256f` | `libwasi_vfs.a` (9,349,788 B) `a362f13066048638423742573dcc32e812fe3e65eb91983c1a41fda63837bf57` |
  | `wasi-vfs-cli-aarch64-apple-darwin.zip` (6,023,105 B) | `d9ebf1cb77927b39c543dccb3fc35842b0f14ca8f70223de1daf2585896de3c1` | `wasi-vfs` (17,466,928 B) `4f6f903d1325851c7505a35a2b86c4f501dc61683def0efd03eb4127012bee9e` |

  `mpl-data` came from the matplotlib 3.11.2 wheel already in the scratchpad (`matplotlib-3.11.2-cp314-cp314-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`, SHA-256 `8c8255de28f986d935a64c9ca71c0ec2d2f41d355691f5ea684725dc91413f71`, re-checked): 204 files, 10 directories, 9,647,777 bytes.
- **Executed, in a scratch clone only.** The scripts are in [`2026-10-16-wasi-vfs-experiment/`](2026-10-16-wasi-vfs-experiment/), with their outputs beside them (`*-output.txt`). Order: `setup.sh` (clone, links to the real build trees, downloads), `relink.sh` (the reactor link exactly as step 60 recorded it in `build/link/reactor-commands.txt`, with or without wasi-vfs), `variants.sh` (pack, then step 80's Wizer, for each variant), `behaviour.py` with `probe_guest.py`, `costs.py`, and `toy/toy.c`. `drive.py` runs a guest like the judge's driver (`tests/harness/guest.py`): the same host-answered clock and random, so fuel is exact, but with the preopens chosen by the caller (none is allowed). Tools: wasi-sdk 24, Wizer 11.0.3, wasmtime-py 49.0.0, all pinned. The real `build/out/` was read, never written.
- **The control.** `relink.sh` with no wasi-vfs reproduced `build/out/python.wasm` byte for byte (`d77dc946…`), and `snapshot.sh` on it reproduced `build/out/python-snapshot.wasm` (`b450c7a6…`). So every difference below comes from wasi-vfs (EXECUTED, `reproducibility-output.txt`).
- **The variants** (EXECUTED, `variants-output.txt`):

  | name | what | snapshot taken with |
  |---|---|---|
  | control | today's reactor | step 80's root |
  | late | wasi-vfs linked, nothing packed | step 80's root |
  | packA | `mpl-data` packed at `/usr/local/lib/python314.zip/matplotlib/mpl-data` | step 80's root |
  | packP | `mpl-data` packed at `/usr/local/share/wasi-python/mpl-data` | step 80's root |
  | packZ | the stdlib zip packed at `/usr/local/lib`, and `mpl-data` as packA | **no preopen** |
  | packZr | packZ's reactor | step 80's root |
  | orderB | late's snapshot, packed afterwards (the other order) | (step 80 first) |

## Findings

### 1. How wasi-vfs works (READ)

- **Interception is a link-time override, not `--wrap`.** wasi-libc calls each WASI function through an undefined symbol such as `__imported_wasi_snapshot_preview1_path_open`, which carries an import attribute. If nothing defines it, `wasm-ld` makes it an import. `libwasi_vfs.a` defines those symbols weakly (`src/trampoline_generated.c`), so the linker binds them to wasi-vfs instead (README "Limitations"). Each one forwards to a Rust handler (`src/wasi_snapshot_preview1.rs`).
- **The handler keeps its own descriptor table.** Each guest descriptor maps to either a real WASI descriptor or a virtual one (`src/lib.rs:24-31`, `FdMap`). A real one is passed to the real import unchanged. wasi-vfs's own calls use the `wasi` crate, which imports `wasi_snapshot_preview1` directly. So the import list does not change.
- **Paths outside the packed directories fall through.** At start, wasi-vfs registers every real preopen first, then each packed directory as an extra preopen, with wasi-libc (`__wasilibc_register_preopened_fd`, `src/lib.rs:44-90`). wasi-libc picks the preopen whose name is the longest prefix of the path. So a packed directory wins inside its own path, and the real root serves everything else. The maintainer confirms the fall-through on issue #17.
- **`pack` is a Wizer run.** The CLI embeds wasmtime 40 and `wasmtime-wizer` 40 (`crates/wasi-vfs-cli/Cargo.toml`). It preopens the mapped host directories, runs the module's `_initialize`, then the exported `wasi_vfs_pack_fs`. That function walks each directory and copies every file into `malloc`ed memory, in a linked tree of nodes (`src/lib.rs:296-417`, `src/embed/linked_storage.c`). Wizer then writes the memory out as data segments. No custom section or side file is involved.
- **A reactor needs a rename.** For a module that exports `_initialize`, the CLI tells Wizer to export wasi-vfs's `__wasi_vfs_rt_init` under the name `_initialize`. It also keeps a copy named `__wasi_vfs_rt_init` (`lib.rs:120-127, 140`). The original `_initialize`, which ran the C constructors, is consumed at pack time. The constructor hook in `src/init.c` mounts the tree only for commands (`_start`), so for a reactor nothing mounts it except that renamed `_initialize`.
- **Read-only by construction.** Every write-type call on a virtual descriptor returns `ENOTSUP`: write, pwrite, allocate, set size, set times, sync, create directory, remove, rename, link, symlink, unlink (`wasi_snapshot_preview1.rs`, every `BackingFd::Virtual` arm). `path_open` on a packed directory ignores the open flags and the rights (`:722-738`). There is no writable in-memory filesystem: the README lists only "Embedded file system: a read only file system", and issue #7, "Possibility of adding write capabilities", is open since 2022. Also unsupported on packed files: `fd_pread` (`:240`), `fd_advise`, `poll_oneoff`, and `fd_renumber`.
- **`..` stops at the packed directory.** Path resolution walks the node tree. A `..` at the top of a packed directory returns `ENOTDIR` (`linked_storage.c:203-208`). There are no links in the tree.
- **Licence and maintenance (READ, `gh`).** Apache-2.0 (`LICENSE`; `Cargo.toml` says Apache-2.0 WITH LLVM-exception). One maintainer. Last commit and release v0.6.3 on 2026-04-12, which "enable[d] wasm exceptions in pack engine". 190 stars, 7 open issues. On issue #21 (December 2024; building from source fails with wasi-sdk 25) the maintainer wrote "I don't have time to work on this project right now" and pointed to WASI-Virt for preview 2. Issue #11 reports duplicate `rint`/`rintf` symbols when linking pandas. That is the same root cause as finding 2's trap, seen another way.

### 2. It links into the real reactor, after one link-order fix (EXECUTED)

`libwasi_vfs.a` linked beside the four `--wrap` flags with no error and no warning. The wraps still sit on top: libc calls `__wasi_path_filestat_get`, the wrap pins it, the real one calls the trampoline, and wasi-vfs answers.

**The trap.** Appended as wasi-vfs's README shows (after our objects, before the driver's own `-lc`), the library also brings Rust's `compiler_builtins`. The linker then took **169 C symbols from it instead of from wasi-libc and compiler-rt**, with no duplicate-symbol error. They include all of libm (`exp`, `sin`, `pow`, `log10`, `fma`, `rint`, …), `memcpy`, `memmove`, `memset`, `memcmp`, `strlen`, and the 128-bit long-double soft float (`__addtf3`, `__multf3`, …). numpy and CPython would silently run on another maths library (`linked-symbols.txt`).

**The fix is a recipe line.** Name `-lc -lm` and compiler-rt's builtins before `libwasi_vfs.a` (`relink.sh`, variant `vfs-late`). Then the link takes only wasi-vfs's own symbols: 29 trampolines, its handlers, and six entry points. A build check would have to assert this, by reading the link map, so the trap cannot come back (INFERRED).

The result (variant late):

- **Imports unchanged:** 42 from `wasi_snapshot_preview1` and one from `host`, as today (`imports-output.txt`). Constitution §4.4 holds.
- **Exports grow by two:** `__wasi_vfs_rt_init` and `wasi_vfs_pack_fs`, on the reactor and on every snapshot. Only an embedder can call an export. Calling either after start finds no pending tree and changes nothing (READ, `lib.rs:156-175`), but the export list in spec 003 changes.
- **Byte-reproducible.** Two relinks and two step-80 runs gave the same hashes (`3f6e1b11…`, `4f958fa7…`).

### 3. Pack, then Wizer, works; the other order does not (EXECUTED)

- **Pack, then step 80 (packA).** It works. Wizer 11 calls the packed module's `_initialize`, which is now wasi-vfs's start. That registers the root preopen, then the packed directory. Wizer then runs `wizer.initialize` and snapshots both tables. The snapshot runs with the embedder's one root (finding 4).
- **Step 80, then pack (orderB).** The data is inside (71.7 MB), but it is never mounted. The snapshot has no `_initialize` left, so nothing calls wasi-vfs's start. Every path under the data directory gave `ENOTDIR`, from the root. That matches the source (finding 1).
- The plain reactor also works after packing (packA `python.wasm`). But it is no longer a plain link output. It is a Wizer image whose C constructors already ran at pack time, under the pins.

### 4. Behaviour on the real reactor and snapshot (EXECUTED)

`probe_guest.py` ran on packA's reactor and snapshot, and on packP's, each with one writable root at `/` holding the stdlib zip (`behaviour-output.txt`). All four gave the same results.

| operation on the packed directory | result |
|---|---|
| `open().readline()`, `os.listdir`, `os.path.isfile`, `os.path.isdir`, `Path.is_dir`, `os.walk` + read all | correct: 204 files, 9,647,777 bytes, the same hash before and after the writes |
| `os.stat` on a file | `st_mode 0o100000`, the right size, `st_mtime 0`, `st_nlink 0`; `st_ino` is a memory address |
| create a new file | `ENOENT` (44) |
| `open(existing, "w")` | **succeeds, and does not truncate** (the size stays 45,318) |
| write after `open(…, "a")`, `open(…, "r+")`, `os.open(O_RDWR)` | `ENOTSUP` (58) at the write |
| unlink, mkdir, rmdir, rename inside, rename to the root, symlink, hard link to the root, utime, truncate | `ENOTSUP` (58) |
| `P + "/../../../../../../etc/passwd"` | `ENOTDIR` (54) |
| `import decimal`, `import json` (zip in the root) | work, from `/usr/local/lib/python314.zip/…` |
| write and list the root | works |

**Shadowing (EXECUTED).** wasi-libc matches a preopen by its name string. So `/usr/local/share/./wasi-python/mpl-data` does not match the packed directory's name and goes to the root. Under packP, a guest created that spelling in its root and wrote a planted `matplotlibrc` there. The planted file landed in the host root. But the canonical path still read the packed file. Only the odd spelling read the planted one. Under packA (the zip's path) the same attempt failed with `ENOTDIR`, because the zip is a file in the way. That matches the previous memo's finding 3 for C2.

### 5. No preopen at all: the stdlib zip inside the binary (EXECUTED)

packZ packs the stdlib zip at `/usr/local/lib` and `mpl-data`, and its snapshot was taken with no preopen. Run with **no preopen**:

```
import decimal, numpy; print(1)        -> 1
os.getcwd()                            -> '/'
import csv / import fractions (lazy)   -> /usr/local/lib/python314.zip/csv.pyc, …/fractions.pyc
os.listdir('/')                        -> FileNotFoundError, errno 44
open('/tmp/x', 'w'), open('/x', 'w')   -> FileNotFoundError, errno 44
tempfile.mkstemp()                     -> FileNotFoundError: No usable temporary directory found
os.remove('/usr/local/lib/python314.zip') -> OSError, errno 58 (ENOTSUP)
```

The plain reactor gave the same results with no preopen. Python starts, imports from the zip inside, and runs. There is nowhere to write: wasi-vfs has no writable area (finding 1). So a program that needs a temporary file needs the embedder to grant a directory.

This also removes a pairing. Today the snapshot runs only beside the exact zip it was taken with (spec 003, Decision 9), and the runner places and checks that zip in every root. With the zip inside, the pair cannot be broken. A root holding a bad zip was ignored (finding 6). (INFERRED from those runs.)

### 6. A root on top of packed files (EXECUTED)

The root held a bad `usr/local/lib/python314.zip` (the bytes `not a zip`).

- **packZ's reactor, and packZr's snapshot (taken with a root).** The packed files win on their own paths. `os.path.isfile` on the zip gave True, `os.listdir('/usr/local/lib')` gave only the packed zip, and `import json` came from the packed zip. The bad zip was never read. Everything else used the root: `listdir('/')` gave `['usr']`, and writing `/w` worked.
  - Delete the packed zip: `ENOTSUP`.
  - Delete it through `/usr/local/./lib/python314.zip`: this removed the **root's** copy, not the packed one.
  - Plant `/usr/local/./lib/plantme.py`: the file landed in the root. But `import plantme` failed, because `sys.path` names only the canonical path, which the packed directory serves.

  So a guest cannot shadow or delete a packed file at its canonical path. It can only make files under spellings that nothing on `sys.path` uses.
- **packZ's snapshot (taken with no preopen), given a root.** **The root was ignored.** `listdir('/')` and writing `/w` gave `ENOENT`, and the host root was untouched. The snapshot froze descriptor 3 as a packed directory, so the real root, also at 3, is never reached. That is the previous memo's finding 2 again: a snapshot honours only the preopens it was taken with. Here it fails closed.

### 7. Costs (EXECUTED; fuel exact, wall time a benchmark)

Fuel is the guest's instruction count under `drive.py`, the same in every repeat (spread 0 to 6,000 out of hundreds of millions). Wall time is the median of five runs on M-series macOS, with the module already compiled. It is a benchmark fact, not a test (`costs-output.txt`).

**Size, in bytes:**

| artifact | control | late | packA | packZ |
|---|---|---|---|---|
| reactor | 29,829,406 | 29,943,733 (+114,327) | 39,055,930 (+9,226,524) | 49,530,626 (+19,701,220) |
| snapshot | 62,317,581 | 62,428,837 (+111,256) | 72,128,558 (+9,810,977) | 82,605,549 (+20,287,968) |
| snapshot, `gzip -9` | 18,684,276 | — | 23,508,566 (+4,824,290) | 33,791,883 (+15,107,607) |

packZ's snapshot is 9,813,383 bytes above today's snapshot plus the separate 10,474,585-byte zip. So packing the zip costs almost nothing beyond moving it. The data costs about 9.8 MB raw and 4.8 MB compressed.

**Start, `-c pass`:**

| variant | fuel | vs control | wall |
|---|---|---|---|
| control snapshot, root | 117,641,834 | — | 18.7 ms |
| late snapshot, root | 117,517,184 | −124,650 | 18.2 ms |
| packA snapshot, root | 127,202,487 | +9,560,653 (+8.1%) | 19.1 ms |
| packZ snapshot, no preopen | 137,623,088 | +19,981,254 (+17.0%) | 20.1 ms |
| packZr snapshot, root without a zip | 137,582,191 | +19,940,357 | 19.5 ms |
| control plain reactor, root | 246,651,162 | — | 32.4 ms |
| packA plain reactor, root | 266,700,379 | +20,049,217 | 32.8 ms |

**Start fuel grows by about one unit per packed byte.** A pack of one 5,000,000-byte file added 5,020,629 fuel. A pack of 200 two-byte files added nothing (−33,760). The extra stays when finalization is skipped (`os._exit(0)`: 43,627,327 against 48,603,041). So it is spent before or while the program runs. The cause was not found (see "Where it stopped"). Wall time barely moves: 0.4 ms for packA.

**Lazy stdlib imports** (`import decimal, fractions, numpy`): 139,148,058 on control and 159,383,949 on packZ. Each is about 21.5 M above its own `pass`. So importing from the packed zip costs about what importing from the root's zip costs.

**Reading all of `mpl-data`** (`os.walk`, then read every file):

| where the data is | fuel above its own `pass` | wall |
|---|---|---|
| copied into the root, control (C1) | 12,868,957 | 54.8 ms |
| copied into the root, late (through wasi-vfs) | 13,078,002 | 55.7 ms |
| packed, packA (C3) | 25,085,486 | 21.8 ms |

Packed reads cost about twice the fuel, because the copy now happens inside the guest and is counted. They are 2.5 times faster in wall time, because no host call reads a file.

**Ordinary file I/O in the root** (2,000 rounds of open, write, close, stat, open, read, close):

| variant | fuel | vs control | wall |
|---|---|---|---|
| control | 420,824,644 | — | 413.7 ms |
| late | 426,368,612 | +5,543,968 (+1.3%) | 379.7 ms |
| packA | 450,801,126 | +29,976,482 (+7.1%) | 383.3 ms |

Linking wasi-vfs costs about 1.3% on calls that only pass through it. With data packed, the overhead grows to 7.1%, which is more than packA's fixed start cost. This is probably the same unexplained effect as the start cost (INFERRED).

**Pack time:** 3.8 s wall, one run, for `mpl-data`.

### 8. The pack is not byte-reproducible (EXECUTED)

Seven packs of the same reactor with the same `mpl-data` gave **seven different hashes**. The two step-80 snapshots built on top of two of them differ in **one byte** (`b60f8f68…` against `d55df0aa…`) (`reproducibility-output.txt`).

- The differences are in the guest's heap. Between two packs, 45 bytes differ. Most are dead memory, freed buffers with leftover file text. Python's start overwrites them, so they are gone from the snapshot.
- The byte that survives into the snapshot is padding. A tree node is `{ bool is_dir; size_t count; … }`. It comes from `malloc`, and only its fields are set (`linked_storage.c`, `new_node`). So the three padding bytes after `is_dir` keep whatever the heap held before (READ, and the differing byte sits right after an `is_dir` of 1).
- The toy guest shows the same thing. A 22-byte file packed the same three times out of three. `mpl-data` packed differently one time in three, in 3-byte runs about every 48 bytes, which is the node padding.
- Why the heap's history differs from run to run is not known. A likely source is that the pack's host reads come back in different-sized pieces (INFERRED, not tested).

Two things would fix it. Upstream, the node could be zeroed (`calloc`). On our side, a recipe could hand out zeroed memory while the build is pinned. The second was not tried.

### 9. The supply chain (READ, EXECUTED)

- **Prebuilt, no Rust needed.** `libwasi_vfs.a` is one library for every wasi-sdk. Upstream CI builds it with Rust 1.92 for `wasm32-unknown-unknown`, and compiles its C parts with wasi-sdk 20 (READ: `release.yml`, `rust-toolchain.toml`). It linked with wasi-sdk 24 into the real reactor. It also linked with **wasi-sdk 33** into the toy guest, which then packed, read its packed file, passed the stat wrap and wrote to the root (EXECUTED, `toy-output.txt`; SDK 33 from the pinned tarball, hash re-checked).
- **The CLI is per host.** Releases exist for Linux x86_64 and aarch64, macOS x86_64 and arm64, and Windows x86_64 (gnu). GitHub publishes SHA-256 digests for every 0.6.x asset, so each pins by URL and hash. A Linux CI build needs the Linux CLI pinned as well.
- **What it adds to the build.** A second Wizer, with its own wasmtime 40, runs our reactor at build time beside Wizer 11.
- **What it adds to the binary.** The static library carries Rust's `std`, `core`, `alloc`, `hashbrown`, `compiler_builtins` and the `wasi` crate (EXECUTED: the link map). Their notices (MIT or Apache-2.0) would have to ship (constitution §4.12), and the owner would have to approve them.
- **Building from source** would need a Rust 1.92 toolchain and its crates pinned, and wasi-sdk 20 for the C parts. Issue #21 says the source build breaks on wasi-sdk 25 and later. The prebuilt library avoids that.

### 10. C3 against C2 (from findings 1 to 9 and the previous memo)

| | C2: second read-only preopen | C3: wasi-vfs |
|---|---|---|
| Security against the host | The guest reads only that directory. Escapes are refused by wasmtime (errno 63). The read-only flag is the embedder's to set, and the guest cannot check it. | No host directory at all for the data. wasi-vfs passes every real call to the real import, so wasmtime still enforces the root. It cannot widen access. A wasi-vfs bug can only corrupt the guest's own memory (INFERRED). |
| Security between runs | Holds while the mount is read-only. A writable mount lets one run change the data for every later run, and the guest cannot tell. | Holds by construction. Each instance starts from the module's own bytes, and every write is refused. |
| Embedder contract | Grows: an optional second preopen, at a fixed guest path, read-only. | Unchanged: one preopen. With the zip packed, it can be **none**. |
| Snapshot fit | Needs the same preopens in the same order at Wizer time, or a reset call. | Works if packed before Wizer. The snapshot is then bound to the preopen count it was taken with, as today. |
| Cost | No size growth in the binary. Reads at host speed. 9.6 MB on disk once per install. | +9.8 MB raw (+4.8 MB gzip) per binary. +8.1% start fuel. +7.1% fuel on root I/O. Double fuel for data reads, but 2.5 times faster wall. |
| POSIX fidelity | Native wasmtime errors. | `ENOTSUP` for writes. `open("w")` succeeds without truncating. `pread` unsupported. `mtime` 0. |
| Reproducibility | Unaffected. | **Broken** at the pack step (finding 8). |
| Build and trust | Nothing new. | Two new pins (the library, and a CLI per host), a second Wizer, Rust runtime code in the guest, and a link-order trap to guard. |
| Maintenance risk | wasmtime's API only. | One maintainer who says he has no time. Preview1 only, and upstream points to WASI-Virt. |
| More data folders | One preopen per folder, or one shared parent preopen. The contract grows each time. | One more `--dir` per folder at pack time. The contract never grows. Each folder is baked into every binary, so profiles (constitution §2) would carry only their own. |

## What it decides

**Verdict: partly.** wasi-vfs works with our reactor and our snapshot, if two conditions hold. The link must name libc first. The pack must run before step 80. It keeps the two imports, reads correctly, refuses every write, and keeps one preopen. It can even run with **no preopen at all**, with the stdlib zip inside the binary (EXECUTED). That is the strongest isolation of any option, and it is what the owner's direction asks for.

It is **not ready to adopt**, for three reasons:

1. **The pack is not byte-reproducible.** The published snapshot changed by one byte between two builds. That breaks the rebuild promise (constitution §2.5 and the reproducibility memos) until upstream zeroes its nodes, or a recipe of ours makes the heap deterministic at pack time. This is the blocker.
2. **Start fuel grows by about one unit per packed byte, and the cause is unknown.** That is +8% for `mpl-data` and +17% with the zip as well. Root I/O is 7% slower. Constitution §3 asks that a slowdown have a stated reason, and there isn't one yet.
3. **It brings real weight**: a link-order trap that silently swaps the maths library, a second Wizer, Rust runtime code with new notices, two extra exports, and a maintainer with no time.

**For matplotlib's data, C2 stays the recommendation** of the previous memo. It costs nothing in the binary and nothing in reproducibility. C3 is the right candidate if the owner chooses the sealed, no-preopen runtime as a goal. Then the zip and the data are packed together, and the runner's zip placement and check go away (findings 5 and 6). It should not be chosen for `mpl-data` alone. The specification should not be written on C3 until the two experiments under "Where it stopped" pass.

If C3 is later chosen, the specification must decide these, from these findings:

- the link names `-lc -lm` and compiler-rt before `libwasi_vfs.a`, and a check reads the link map: wasi-vfs supplies only its own symbols;
- the order is pack, then Wizer, and a check fails on orderB's `ENOTDIR`;
- the snapshot is taken with exactly the preopens the runtime will give (none, for the sealed form);
- the two extra exports are accepted in spec 003's list, or removed by a recipe;
- the README documents the deviations of the packed files: `ENOTSUP`, non-truncating `open("w")`, no `pread`, `mtime` 0;
- an embedder that wants scratch space grants a directory, because wasi-vfs has none.

## Where it stopped

- **Reproducibility.** Not fixed. The next experiment: in `recipes/reactor_main.c`, wrap `malloc` and `free` through the link while `pinned` is set, so allocation hands out zeroed memory and freeing clears it. Pack five times, run step 80 on each, and compare the hashes. Then repeat on Linux, where directory order and read sizes differ.
- **Where the per-byte fuel goes.** Two attempts were made, and the two-strike rule stopped the work. First, wasmtime's sampling guest profiler (`--profile=guest`, 100 µs) was too coarse to see 4% of a 20 ms run. Second, skipping finalization showed the cost is not there. The next experiment: pack about 200 MB of data, so the extra fuel dominates, and profile that.
- **Why the pack's heap history varies** was not traced (finding 8).
- **matplotlib itself** was not built. Only its data files were read, with the same calls matplotlib uses (`open`, `os.path.isfile`, `Path.is_dir`). FreeType reads through a Python file object (previous memo), so `pread` should not be needed (INFERRED).
- **Windows and Linux** were not run. Only the macOS arm64 CLI was fetched.

## One line

wasi-vfs can seal the data, and even the stdlib zip, inside the binary, so the guest needs no preopen and no run can change what the next one reads. But its pack is not byte-reproducible, start fuel grows with every packed byte for a reason not yet found, and it brings a second Wizer, a maths-swapping link trap and an unmaintained upstream. So C2 stays the answer for matplotlib, and C3 waits for two experiments.
