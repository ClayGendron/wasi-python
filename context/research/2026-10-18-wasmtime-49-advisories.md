# wasmtime 49 advisories since 49.0.0, and what they mean for us

- **Status:** research, 2026-10-18. Security research only; no code, test, recipe, download or specification was changed. Reproductions ran against the frozen artifact set, not a rebuild.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5). Box: one session. It stopped where "Where it stopped" says.
- **Stands on:** `AGENTS.md`; `context/constitution.md` (§4.1, §4.13, §4.15, §5.5, §5.6); the threat model (`2026-10-16-a-principal-engineers-direction.md`, §2); `SECURITY.md`; `README.md` (*Enforced, and judged*, line 740; *Not protected*); the 0.1.0a2 and 0.1.0a3 security reviews; the upstream facts sheet 12 (`context/upstream/12-wasmtime-py-on-wasmtime-49-0-3/`, on worktree `spec/032-dirent-padding`, commit `ced2145`) and spec 032 (`src/wasi_python/mounts.py`, the shadow/trampoline machinery); specs 006, 016, 017, 024, 025, 032.
- **Evidence:** `2026-10-18-wasmtime-49-advisories/` beside this memo. `advisories/*.json` are the 28 GHSA records (EXECUTED `gh api`, 2026-10-18); `advisories-since-2026-09.txt`, `releases.txt`, `pypi-wasmtime.txt`, `compare-*.txt`, `fix-49.0.3*.diff` are the version and diff facts; `repro/` holds the reproduction scripts and `repro/transcript.txt` their output. Host: arm64 macOS (Darwin 25.5.0). Runtime: wasmtime-py 49.0.0 bundling wasmtime 49.0.0 (the pin `wasmtime>=49,<50` resolves to; PyPI's only 49 release). Artifact set: `build/sets/s-8d84b3b190fe9bce` (frozen, not rebuilt).

One idea per sentence. A term of art is defined where it first appears.

## The short version

wasmtime 49.0.0 is the only wasmtime a `pip install wasi-python` user gets today, because PyPI's `wasmtime` has no release past 49.0.0 (EXECUTED, PyPI JSON). Two of the advisories fixed since then touch what we use, and both are **confirmed against our own runner**:

1. **GHSA-m9f7-9w4p-gv38 (HIGH): a full filesystem sandbox escape** on macOS and FreeBSD, through a writable grant or `root=True`. A guest renames a symlink with a trailing slash; the kernel follows it out of the sandbox and moves an outside directory *in*. I moved a directory that sat outside every grant into the sandbox and read and wrote its contents (EXECUTED). This breaks a boundary the README claims and the judge checks (README line 740: "the guest cannot follow a symbolic link out"). It is in scope per `SECURITY.md`.
2. **GHSA-96f6-r43r-8c24 (LOW): `fd_readdir` leaks up to 3 bytes of host memory** per directory entry into the guest, on every listing, even with nothing granted (the stdlib zip's folder is listed). Already found and documented by spec 032; facts sheet 12 holds the reproduction.

Everything else fixed in 49.0.1 → 49.0.3 is component-model, GC-proposal, exception-handling, `wasi-http`, or preview0 code. **Our guest imports only `wasi_snapshot_preview1` and the one door `host::call`** (EXECUTED: the module's imports). We build no component, link no `wasi-http`, and enable no GC or exception proposal (READ: `_engine`, only `consume_fuel` and `epoch_interruption` on an otherwise default `Config`). So those advisories do not reach us.

**Recommended mitigation:** reuse spec 032's shadow/trampoline to intercept `path_rename` on every call that has a writable place, and apply wasmtime 49.0.3's own rule — a rename whose source or target ends in `/` must fail with `ENOTDIR` unless the source really is a directory. Shadow `fd_readdir` on every call to zero the three padding bytes. This is a small, counted change that needs no new wasmtime-py. **Building our own wasmtime-py on 49.0.3 is feasible but wrong here**: it would make the published wheel depend on a wasmtime that is not on PyPI, which breaks `pip install wasi-python` (§2.1, §2.4).

**Release impact:** the escape **blocks 0.1.0** (§5.5: a security fix in a pinned component is a reason to release). For the alpha **0.1.0a4** it should carry the mitigation too, because our primary platform (macOS) is exactly where the escape works, and the alpha advertises writable grants. The owner decides whether 0.1.0a4 ships the mitigation or holds; it must not ship silent.

## 1. GHSA-m9f7-9w4p-gv38 — the filesystem escape

### What it is (READ: the advisory, `gh api`; the fix diff `fix-49.0.3-rename-only.diff`)

A **preopen** is a directory the runtime opens before the guest starts; the guest reaches a host file only through one. `wasmtime-wasi` implements `path_rename` by opening the parent of each path and renaming by the last component. To find the parent it strips a trailing `/` from the path, and then — this is the bug — on macOS and FreeBSD it re-appends the `/` before calling the `renameat` syscall. On those kernels `renameat` **follows a symbolic link that has a trailing slash**. Linux and Windows do not, so they are unaffected (the advisory says so; the fix is `#[cfg(not(target_os = "linux"))]`).

So a guest that can write in a preopen can: create a relative symlink pointing out, e.g. `symlink("../outside", "up")`, then `rename("up/", "inside")`. The kernel follows `up/` to `../outside` and moves that outside directory into the sandbox. The guest then reads and writes it freely. The advisory calls it "a full filesystem sandbox escape". It is rated HIGH (CVSS 4.0 8.8), CWE-61 (symlink following). It is the sibling of GHSA-vqjp-4c8c-hfgg (the open path, fixed earlier); 49.0.3 fixes the rename path.

The 49.0.3 fix: strip the trailing slash from both paths, and if either path *had* one, require the source to be a directory — on non-Linux by an explicit `lstat` (no symlink followed) returning `ENOTDIR` otherwise; on Linux by letting the kernel enforce it. The new preview1 test program (`crates/test-programs/src/bin/p1_path_rename_trailing_slashes.rs`) is exactly the attack: `path_symlink("../outside", ..., "up")` then `path_rename("up/", "stolen")` must return `ENOTDIR`.

### Whether a wasi_python guest can trigger it (EXECUTED, `repro/transcript.txt`)

Yes, through CPython's ordinary `os.symlink` and `os.rename`, with no low-level tricks.

| configuration | can create symlink? | can rename-with-slash across? | result |
|---|---|---|---|
| **writable grant** (`Grant(..., writable=True)`) | yes | yes | **full escape** |
| **`root=True`** (private root) | yes | yes (same-device targets) | **escape within the device** |
| **read-only grant** (`writable=False`) | **no** (errno 63 EPERM) | n/a | safe |
| **default** (`root=False`, no grants) | no (nothing writable) | n/a | safe (INFERRED: no writable preopen exists; the only preopen is the read-only stdlib zip, which refuses creation as the read-only grant does, EXECUTED) |

- **Writable grant (EXECUTED):** scratch layout of a writable `grant/` and a sibling `outside/` that is outside every grant, holding `secret_dir/canary.txt` and `loose_canary.txt`. Grant `grant/` writable at `/work`, nothing else. The guest ran `os.symlink("../outside", "up")` then `os.rename("up/", "stolen")`: both succeeded. It then listed `/work/stolen` and read `CANARY-do-not-reach` and `sibling-canary`, and wrote `/work/stolen/pwned.txt`. On the host, `outside/` was gone — the kernel had moved it into `grant/stolen`. `run` returned exit 0, no trap. (`repro/guest_escape.py`, `repro/host_run.py`.)
- **`root=True` (EXECUTED):** the private root is a fresh directory under the system temp folder. Pointing a symlink at a sibling directory I planted in that temp folder and renaming `up/` to `stolen` moved it into the private root; the guest read its canary. Cross-device targets such as `/etc` fail: the symlink is created, but the rename returns EPERM because `renameat` cannot move across filesystems — a kernel limit, not a sandbox check. So the reach is "any same-filesystem directory the host process can open", which on a developer box is most of `$HOME` and `$TMPDIR`. (`repro/guest_root.py` toward `/etc` → EPERM; `repro/guest_root2.py` toward a temp sibling → reached.)
- **Read-only grant (EXECUTED):** `os.symlink` returns errno 63 (EPERM); the escape needs a writable preopen, so a read-only grant cannot start it. (`repro/guest_ro.py`.)

### Why this matters more than its rating suggests

The README makes a specific, judged claim (line 740, `tests/checks/test_v1_2_*.py`): "the guest cannot follow a symbolic link out (refused on open). It can still *create* a relative link that points out, which matters to host code that reads its root afterwards." The threat model's filesystem row repeats it (EXECUTED): "a relative link that climbs out is created but refused on open (63)." The escape **defeats exactly this**: the guest never *opens* through the link; it *renames* the link, and the kernel follows it during `renameat`. The protection we tested and documented is bypassed. This is the sandbox boundary in `SECURITY.md`'s "In scope", not a "Not protected" item.

One precondition holds in the main use case. The AI-code use case (`the-runtime-for-agent-code.md`) gives a guest a writable scratch directory. That is a writable grant or `root=True`: exactly where the escape works. A prompt-injected guest (threat-model adversary) reaches the embedder's whole same-device filesystem.

## 2. Every other advisory fixed 49.0.0 → 49.0.3, and whether it reaches us

Source: `advisories-since-2026-09.txt` (28 records, EXECUTED). "Reaches us?" is judged against what our guest imports (`wasi_snapshot_preview1` + `host::call`, EXECUTED), our `Config` (`consume_fuel`, `epoch_interruption`; default Cranelift compiler; default on-demand allocator, not pooling — READ `_engine`), and the fact that we instantiate a core module, never a component.

| GHSA | sev | fixed in | area | reaches us? |
|---|---|---|---|---|
| **m9f7-9w4p-gv38** | HIGH | 49.0.3 | preview1 filesystem (`path_rename` + symlink) | **YES — confirmed (§1)** |
| **96f6-r43r-8c24** | LOW | 49.0.2 | preview1 `fd_readdir` padding leak | **YES — confirmed (spec 032, facts sheet 12)** |
| j2g9-4prp-pf6h | MED | 49.0.1 | preview1/2/3 filesystem set-times datetime overflow → host panic | **in range for 49.0.0, but not reachable through the guest's CPython in my test** (see below) |
| m63x-6p34-q65x | MED | 49.0.1 | fuel accounting dropped by `call_ref` / exception `catch` | **unlikely** — needs the typed-function-references or exception-handling proposals; our C-built core module uses neither (INFERRED; not proven by disassembly — see "Where it stopped") |
| jqpg-j7w6-42pr | LOW | 49.0.1 | hostcall fuel on dynamic *record lifting* | no — component model |
| c9gc-w9vx-w86p | MED | 49.0.1 | `wasi-http` outgoing body host memory | no — no `wasi-http` |
| j366-h8gg-77pm | MED | 49.0.2 | **preview 0** `poll_oneoff` circumvents fuel | no — we import preview1 only, not preview0 (EXECUTED: import modules) |
| gqmc-89g8-p25r | MED | 49.0.2 | excess host memory when a guest has **no stdio** | no — the runner always gives stdin/stdout/stderr (READ `_send_outputs`, `wasi.stdin_file`) |
| mr2v-56j5-cmfc | MED | 49.0.2 | **wasip3** timestamp-before-epoch panic | no — preview1 only |
| 32h6-97mm-8q3c | CRIT | 49.0.2 | component async-lifted callback result count | no — component model |
| cfhf-m2cr-62wj | MED | 49.0.2 | mis-typed tag imports → GC heap corruption | no — GC/exception proposal, no component |
| w4qr-p94g-mjhv | MED | 49.0.2 | `wasi:http` zero timeout | no — no `wasi-http` |
| hw8m-q44c-ggrf | MED | 49.0.2 | GC rooting across `try_call` | no — GC proposal |
| 93g3-36p8-x2gc | MED | 49.0.3 | out-of-bounds zero-length **stream** writes | no — component model streams |
| 3r89-v5mq-j5xf | MED | 49.0.3 | component `call_async` cancel panic | no — component model |
| 5hhx-4wrr-3j9g | MED | 49.0.3 | yielding in a component start fn | no — component model |
| m6w2-jwq2-cv2c | MED | 49.0.3 | async-lifted fn via `call` panic | no — component model |
| hmwq-g22x-qjw5 | MED | 49.0.3 | pending calls run after a trap | no — component model |
| 63h4-6cx9-pjfj | MED | 49.0.3 | component stream/future wrong-type view | no — component model |
| vcg5-q8m5-8379 | MED | 49.0.3 | async-entrypoint enforcement | no — component model async |
| 7v24-42x9-pxf7 | MED | 49.0.3 | erroneous call-to-host from guest `realloc` | no — component model |
| wjc8-633q-pwxr | MED | 49.0.3 | stack overflow dropping recursive **types** | unlikely — the GC/func-ref type registry; our core module is not GC-typed (INFERRED) |
| q554-3cjc-rx7p | MED | 49.0.3 | component handle tables uncapped | no — component model |
| p79w-pv2r-29qp | LOW | 49.0.3 | exception tags unalign host data | no — exception-handling proposal |
| 54p9-vhhq-8f7q | MED | 49.0.3 | fused adapter string transcode | no — component model |
| 5qpp-g3j2-8frx | LOW | 49.0.3 | `wasi-http` absolute-form requests | no — no `wasi-http` |
| w36r-2hch-9xp9 | MED | 49.0.3 | `wasi-http` long url | no — no `wasi-http` |

Notes:

- **j2g9-4prp-pf6h (set-times host panic), EXECUTED negative.** The advisory: a guest sets a filesystem timestamp out of range and panics the host (a DoS of the embedder's process, not a sandbox escape). I ran a guest calling `os.utime` with nanoseconds at `2**63-1`, `-2**63`, `2**64-1`, `±10**30`, on `root=True`, in an isolated subprocess with `faulthandler`. The host survived (exit 0, no trap, no abort): CPython's own `time_t` handling clamps or raises `OverflowError`/`EINVAL` before the raw triggering value reaches wasmtime. The exact triggering value needs a hand-crafted `fd_filestat_set_times`/`path_filestat_set_times` call, which the guest can only make through CPython's libc, and CPython does not pass it. **Judged: in the vulnerable range but not reachable through our guest's stdlib** (EXECUTED; a crafted-wasm guest is out of scope since our only guest is `python.wasm`). (`repro/guest_settimes.py`.)
- **Newest major.** PyPI has no wasmtime past 49.0.0; wasmtime itself has `50.0.0` released and `51.0.0` unreleased (`releases.txt`, `prior_art/wasmtime` `RELEASES.md`). The pin `<50` excludes 50 regardless. No 50.x advisory was reviewed because we cannot resolve 50 from PyPI; it is only relevant if the owner widens the pin.

## 3. Mitigations available without a new wasmtime-py

### Option A (recommended) — shadow the two affected preview1 calls on the linker

Spec 032 already built the machinery. `src/wasi_python/mounts.py` shadows all 29 descriptor-acting preview1 calls (including `path_rename`, `path_symlink`, `fd_readdir`: `SIGNATURES`/`SHADOWED`) on a **mount linker**, and forwards the ones it does not serve to wasmtime's own WASI through a `wasmtime_func_call` trampoline on the guest's memory, resetting fuel by `FUEL_ALLOWANCE` after each forward so the forward is **fuel-neutral**. But spec 032 keeps *today's* linker (wasmtime's native WASI, no shadow) for every call **without** mounts, precisely to leave fuel and parity unchanged there. That is why the vulnerable calls run straight to wasmtime on a normal call.

The mitigation: make the shadow apply to a normal call too, for the few calls that need it.

- **`path_rename`:** before forwarding, read `old_path` and `new_path` from guest memory; if either ends in `/`, `lstat` the source basename through the source directory descriptor without following symlinks (spec 032 already has the pieces: it opens parents and reads paths). If it is not a directory, answer `ENOTDIR` (54) and do not forward. This is exactly wasmtime 49.0.3's rule and preserves every legitimate rename, including renaming a real directory with a trailing slash.
- **`fd_readdir`:** forward to wasmtime, then zero the 3 padding bytes after each entry's `d_type` in the guest's buffer. Spec 032's mount path already writes zero padding (the `DIRENT` layout `<QQIB3x>`), so the parity table already expects zeros from a mount; extending that to the forwarded case closes the leak on every listing (the stdlib zip folder included).
- **`path_symlink`:** optional. Refusing symlink *creation* (EPERM) when a writable place exists would also stop a guest *planting* the symlink. It is **not sufficient alone** — an embedder's writable grant may already contain a host-placed symlink, which the rename fix is what actually catches — so `path_rename` is the load-bearing fix, and refusing `path_symlink` is a defence in depth the owner may or may not want (it is a tightening, so §4.15-aligned, but it changes guest behaviour: `os.symlink` would fail).

Scope decision inside Option A: the `path_rename`/`path_symlink` shadow need run only when the call has a writable root or a writable grant (the escape needs a writable preopen). The `fd_readdir` padding shadow must run on **every** call, because the leak happens on the always-present read-only stdlib-zip listing.

- **Fuel consequence:** the trampoline's few instructions are covered by `FUEL_ALLOWANCE` and set back after each forward, so counts can stay identical; this must be re-proven across the suite (spec 032 proved it for mounts, not for every call).
- **Parity consequence:** the raw parity table (`test_runner_grants.py::test_raw_calls_answer_as_a_grant_does`) compares bytes a grant and a mount return; the only intended change is zeroed `fd_readdir` padding and an `ENOTDIR` for the trailing-slash-symlink rename, both of which the fix makes the *correct* answer.
- **Cost/shape:** this is a **build-class + design change** (it changes how the guest's imports are served on normal calls), so §5.6 gives it a design review before it is built, then a build review. It touches `src/` only, not the recipe or downloads, so it needs no artifact rebuild.

### Option B — build our own wasmtime-py wheel on wasmtime 49.0.3

Feasible: wasmtime-py bundles a prebuilt wasmtime C-API shared library fetched by `ci/download-wasmtime.py` (`WASMTIME_VERSION`), and the C API did not change across the 49 patch releases (INFERRED, facts sheet 12 fact 4). Pointing it at `v49.0.3`'s released C-API assets, each pinned by URL+SHA (§4.2), would carry the fix.

But it is the wrong choice here. The published `wasi-python` wheel must `pip install` (§2.1, §2.4: "A Python embedder does it in one call through the wheel"), and it declares `wasmtime>=49,<50` (`pyproject.toml`). A locally-built wasmtime would not be the PyPI `wasmtime`, so either the wheel depends on a package users cannot resolve, or we vendor a second wasmtime inside our wheel and diverge from the one embedders already have — both break the clean PyPI story and add a large, per-platform maintenance surface (a native build per OS/arch). It also does not fit §4.1 (that is about upstream *source* patches; this is a dependency swap) but it strains §6.4 ("the smallest thing that meets the specification") and the product posture ("few pins", embedder-neutral). Keep it as the fallback only if upstream never ships a wasmtime-py on a fixed wasmtime.

### Option C — refuse symlink creation in grants by default

This collapses into Option A. wasmtime-py's `preopen_dir(path, guest, fs_mutable: bool)` exposes only a single writable/read-only bit (READ, `_wasi.py:172`); there is no "writable but no symlink" preopen flag to set. So refusing symlink creation still means intercepting `path_symlink` on the linker — the same shadow machinery as Option A, and, as noted, not sufficient on its own.

### Recommendation and a spec outline

Adopt **Option A**, minimal form: the `path_rename` trailing-slash rule on every writable-place call, plus `fd_readdir` padding zeroing on every call. A spec "The symlink-rename escape is shadowed" (build-class):

- **What changes:** `src/wasi_python/mounts.py` / `runner.py`. Extend the shadow so a call with a writable root or writable grant installs the `path_rename` shadow (49.0.3's rule), and every call installs the `fd_readdir` padding-zeroing shadow. `path_symlink` refusal is offered as a reviewed option for the owner to accept or decline.
- **Checks, counting operations, seen failing first** (constitution §5.2, AGENTS.md rule 3):
  1. a writable-grant guest that runs `symlink("../outside","up"); rename("up/","x")` gets `ENOTDIR`, and a host file outside every grant is unchanged after the call — seen failing on today's code (it is the escape I reproduced);
  2. the same under `root=True` — seen failing today;
  3. a *legitimate* `rename("realdir/","renamed")` of a real directory still succeeds (so the fix does not over-refuse) — passes before and after;
  4. a read-only grant still refuses `symlink` with EPERM — passes before and after;
  5. `fd_readdir` on the stdlib-zip folder returns zero padding bytes (extend the existing raw parity check to the no-mount case) — seen failing today (995/1000 calls carried a non-zero byte, facts sheet 12);
  6. fuel for a file-listing and a rename is unchanged from today (fuel-neutrality of the shadow).
- **The upstream pin still moves when wasmtime-py ships a fixed wasmtime** (§5.5, `SECURITY.md`: "we will move our pin when a fix ships"). The shadow is the temporary belt until then, and facts sheet 12 is the standing ask. When the pin moves to a wasmtime ≥ 49.0.3, the `path_rename` and `fd_readdir` shadows become redundant and can be removed, like a carried patch (§4.1 spirit).

## Release impact (§5.5)

- **0.1.0 (the real release): blocked.** A HIGH full filesystem escape across the sandbox boundary, in `SECURITY.md`'s "In scope", reachable in the primary use case (a writable scratch directory), on our primary platform. §5.5 makes a security fix in a pinned component a reason to release; the agent prepares one (Option A) and asks. The pre-release threat-model review (§5.6) would fail on it as it stands.
- **0.1.0a4 (alpha): should not ship silent.** Either land the Option A mitigation, or, if the owner chooses to ship without it, say plainly in `README.md`/`SECURITY.md` and the CHANGELOG that on macOS and FreeBSD a guest with a writable grant or `root=True` can escape the sandbox, with the advisory id — because the README and threat model currently claim the opposite (line 740). My recommendation is to land the mitigation before 0.1.0a4, since the fix is small and the claim is load-bearing.
- **The `fd_readdir` leak (LOW)** does not block on its own, but its shadow rides the same change cheaply, so fixing it with the escape is the economical path.

## Questions for the owner

1. For **0.1.0a4**, land the Option A mitigation, or ship with the escape documented and the pin note? (For **0.1.0** the memo recommends blocked-until-fixed.)
2. Within Option A, also refuse `path_symlink` creation when a writable place exists (defence in depth, but `os.symlink` in a guest then fails), or only fix `path_rename` (the precise 49.0.3 rule, no behaviour change for legitimate code)?
3. Keep facts sheet 12 as the standing upstream ask (a wasmtime-py release on wasmtime ≥ 49.0.3), with the shadow as the temporary belt removed when the pin moves — yes?

## Where it stopped

- The two reaching advisories are reproduced against the real runner (EXECUTED). The escape was demonstrated end to end; the host directory outside every grant was moved in, read and written.
- j2g9 (set-times panic) was tested through CPython and did not reach the host; I did **not** build a hand-crafted wasm guest to drive the raw preview1 call, because our only shipped guest is `python.wasm`. If the owner wants certainty that no stdlib path reaches it, that is a follow-up.
- m63x and wjc8 are judged "unlikely" by what the proposals are, **not** by disassembling `python.wasm` to prove the typed-function-references / exception-handling / GC opcodes are absent. A `wasm-tools print | grep` for `call_ref`, `try_table`, `throw`, `struct.new` on the module would settle it; left as a follow-up (it does not change the two confirmed findings).
- No mitigation was built: this is research only, per the task. Option A's spec is outlined, not written.

## One line

wasmtime 49.0.0 — the only wasmtime a `pip install` user gets — carries a HIGH filesystem sandbox escape (GHSA-m9f7-9w4p-gv38) that a writable-grant or `root=True` guest triggers on macOS, confirmed by moving an outside directory into the sandbox; fix it by reusing spec 032's shadow to apply wasmtime 49.0.3's own trailing-slash rename rule (and zero the `fd_readdir` padding), block 0.1.0 on it, and do not ship 0.1.0a4 with the boundary silently broken.
