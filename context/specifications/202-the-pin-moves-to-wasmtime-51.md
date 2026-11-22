# 202: The pin moves to wasmtime 51

- **Status:** **drafted 2026-11-22**, from the owner's request to upgrade to wasmtime 51 and release (`decisions.md`, "0.1.6 is a security release"), and the research memo below. Its checks are named in Decision 3 and not yet written: the builder writes them first and sees them fail where the row says, then builds. It moves the build's wasmtime command line, which changes the snapshot's bytes, and it changes the engine's configuration, so a **pre-build review is required** (constitution §5.6; AGENTS.md step 7). A different agent reviews the build.
- **Date:** 2026-11-22
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe** (one rebase with the open path-call specifications, For the lane), **not structural** (Decision 9), **a judge change**, **build-class**. It touches `pyproject.toml` and `uv.lock` (the pin), `src/` (`_wasmtime_ffi.py`'s `PIN`, `_engines.py`'s config and its one message), `scripts/line.conf` and `downloads/SHA256SUMS` (the command line), `tests/` (the checks of Decision 3), `SECURITY.md`, `README.md`, the pages of `docs/` that name wasmtime 50, the debt sheet `../upstream/34-wasmtime-py-public-api-for-the-runner/facts.md`, and its news file. It changes `python-snapshot.wasm`'s bytes (a new wizer), not `python.wasm`'s and not the zip's. It changes no default an embedder can observe except that a GC-typed module is refused (Decision 6).
- **Depends on:** landed and unchanged: 127 (the shape of a major move, which this follows), 103 (the engine seam), 166 (the rule that the build's wasmtime is the runner's line), 002 (fuel is not compared across versions), 185 (the wheel's provenance, which the release keeps). On nothing in flight.
- **Research it stands on:** `../research/2026-11-22-moving-to-wasmtime-51.md` (every fact below is EXECUTED or READ there unless marked) and `../research/2026-11-22-the-gc-proposal-off-under-wasmtime-51.md` (the probe the owner asked for before turning the GC proposal off).

Labels: EXECUTED, run and seen; READ, read from a file or a page, cited; INFERRED, reasoned.

## The problem

The published pin is `wasmtime>=50,<51`. The only wasmtime-py in that range is 50.0.1, which bundles wasmtime 50.0.0. wasmtime has since fixed nine advisories in 50.0.2 and 50.0.3, but wasmtime-py published neither, so no 0.1.5 user can reach those fixes by pinning.

One of them is High and very likely reaches the runner. GHSA-f2pq-268w-886c lets a guest on Windows escape a granted folder with a name such as `./C:foo`. The runner forwards every path call on a plain host grant to wasmtime unchanged. Its own rule against a `:` serves only its mounts. A second advisory, GHSA-5m8g-xhq4-4h93 (Moderate), lets zero-length writes grow host memory without bound through the C API's custom output. The runner uses that output on Windows, where it has no pipe to open by path.

wasmtime-py 51.0.0, on PyPI since 2026-11-20, bundles wasmtime 51.0.0, which carries every one of those fixes, the Windows one included, though 51's notes do not list it. The seam's private names all resolve on it, and 0.1.5's binaries validate under it.

## Decisions

### 1. The pin is `wasmtime>=51,<52`, done where the seam says

`pyproject.toml`'s one dependency becomes `wasmtime>=51,<52`. `_wasmtime_ffi.PIN` says the same. `uv.lock` is remade with `uv lock --upgrade-package wasmtime` and names 51.0.0. `_engines._wasmtime`'s `ImportError` message spells the pin by hand, as it does today. The builder follows the seam's bump steps and says so in the landing notes, including step 7: file output is still written on the guest's thread (READ at `v51.0.0`, the memo's §4).

- **What the wheel bundles, recorded.** The builder reads it from the wheel's library, as 127 did. The memo has it from the C header (`51.0.0`) and the upload order. If the wheel bundles anything but 51.0.0, the build stops and the owner is asked.

### 2. The build's command line moves to wasmtime 51.0.0

`test_the_builds_wasmtime_is_the_runners_line` holds the three `*_WASMTIME_DIR` folders on the runner's major, so the command line follows. Its three archives (`wasmtime-v51.0.0-aarch64-macos.tar.xz`, `-aarch64-linux`, `-x86_64-linux`) are pinned by URL and SHA-256 in `downloads/SHA256SUMS` and verified before use. `scripts/line.conf` names their folders. `scripts/00_download.sh` changes only if it spells the version. The snapshot is made again by `wasmtime wizer` 51.0.0, and `MANIFEST`'s `x-wizer` line names it.

- **What changes in the artifact set.** `python-snapshot.wasm`'s bytes and their hashes, which `MANIFEST` and `SHA256SUMS` record. `python.wasm` and the zip are not made by wasmtime and keep their bytes (INFERRED; the rebuild-from-pins check is the evidence). The builder records both sizes and hashes in the landing notes.

### 3. The checks first

Each check is written or changed before the code, and seen failing on `dev`'s code where the row says so. None measures time.

- **3a. The drive-prefixed name stays in its grant.** `tests/checks/test_v1_2_hostile_guest.py::test_a_drive_prefixed_name_stays_in_its_grant`. The host's current folder is a fresh folder outside every grant, holding a canary file. A guest with a read-only grant and a writable grant tries names built on the drive of that folder (`./D:canary`, `D:canary`, `sub/D:canary`, and a link whose target is `D:canary`) in each path call: open to read, open to create, `path_filestat_get`, `path_readlink`, `path_create_directory`, `path_remove_directory`, `path_unlink_file`, both sides of `path_rename` and of `path_link`, and `path_symlink`. On every system: the canary's bytes are never read into the guest, it is not changed or removed, and nothing is created outside the grants. On Windows each call is refused, and its errno is recorded per system as the branch's run gives it. On macOS and Linux a colon is a plain name character, so whatever is made is made inside the grant. **Seen failing first:** on the Windows leg, under wasmtime-py 50.0.1. No Windows machine is available to the building session, so this is the one deliberate red. The first commit carries the check alone, the pull request's description and a message to the owner say before the push that its Windows leg will be red and why, and the next commit moves the pin. If the Windows leg is green on 50.0.1, the reach the memo infers is wrong: the check stays as a guard, and the landing notes and `SECURITY.md` say the runner was not reached.
- **3b. Empty writes cost the host nothing** (on the custom-output capture). `tests/checks/test_v1_2_hostile_guest.py::test_empty_writes_do_not_grow_the_host`. A guest makes two million zero-length writes to stdout and to stderr, through the custom-output capture (on every system if the process object's seam can force that capture, else on Windows alone). The host's peak resident memory grows by less than a bound the builder sets from the measurement, with room on every system. Memory, not time, so the rule on wall-clock does not apply. **Seen failing first:** under wasmtime-py 50.0.1. If the builder cannot make it fail there in two attempts (AGENTS.md's two strikes), it is not added: a check that never failed proves nothing. The memo then records the measurement and `SECURITY.md` says the advisory's reach was not reproduced.
- **3c. A large write still arrives whole.** wasmtime 51 traps a write larger than a stream's budget (the memo's §4). The builder names the existing check in which a guest writes 8 MiB or more to stdout in one call, on both captures, and arrives whole with no trap. If none exists, it adds `tests/checks/test_v1_4_embedding.py::test_one_large_write_arrives_whole` with those rows. No row is expected to fail first. It holds what is expected to stay true.
- **3d. The slash rows are read again.** wasmtime 51 changed how a folder named with a trailing slash is removed (#14662, #14663). The slash-named rows of `test_a_trailing_slash_rename_rule`, the parity of a mount with a plain grant (`tests/unit/test_runner_grants.py`, `tests/unit/test_runner_mounts.py`) and any `rmdir` row are re-derived on three systems from the branch's run. A row whose errno moved is recorded per system, as 127's Decision 3b allowed. The safety assertions stay unconditional on every system: nothing outside a grant is touched. The mount's own answers follow a plain grant's where the parity says they must, and that is runner code (`_fs_paths._namespace`), named in the landing notes.
- **3e. The engines refuse GC types.** `tests/unit/test_engines.py::test_the_engines_refuse_gc_types` (or the existing engine unit file): both engines, metered and not, refuse `(module (type (struct)))` and accept a module with a tag, `throw` and `try_table`. **Seen failing first:** on `dev`'s code, which accepts the struct.
- **3f. The pin's text.** `test_a_plain_install_brings_wasmtime`, `test_a_wasmtime_that_cannot_load_is_named` and `test_the_pin_is_written_the_same_in_three_places` say `>=51,<52`. `tests/unit/test_build_scripts.py`'s CLI rows that spell the line's folder as data follow `line.conf`. The fixtures that spell older versions as their own inputs stay, as in 127.
- Nothing in `tests/known_gaps.toml`, no golden output, no upstream allowance changes, unless a release-tier row moves, which goes in the release ledger with its reason.

### 4. No new seam row

Every private name in `NEEDED` and `OPTIONAL` resolves on 51.0.0, and no public form the seam prefers appeared (EXECUTED, the memo's §4). The debt sheet's "Against" line says 51.0.0. If the builder finds otherwise, it follows the seam's steps and adds the row, as 127's Decision 5 did.

### 5. The runner adds no colon rule of its own

wasmtime 51 refuses a `:` in every path on Windows, which covers the forwarded calls. A rule of the runner's on forwarded calls would refuse colons on macOS and Linux too, where they are legal names that guests use (`12:00.log`), or it would be a platform branch. So the engine's rule is the fix, and 3a holds it against the installed engine, as 127 held the rename fix.

### 6. The GC proposal is off

Both engines set `cfg.wasm_gc = False` in `_engines.py`, next to `consume_fuel`, with a comment that gives the reason in words: the guest uses exceptions but no GC types, and an engine that refuses GC types keeps that code out of a guest's reach. Exceptions stay on. The owner approved this on the condition that a probe shows no impact on wasi-python and no change in performance (`decisions.md`, "0.1.6 is a security release"). The probe's memo is that evidence. **If the probe found an impact, this decision goes back to the owner before the build, and the pin moves without it.**

- **What a guest or embedder sees.** A module that declares a GC struct or array type is refused when compiled. The artifact set declares none (EXECUTED: both binaries validate with GC off). wasmtime keeps its small heap for exception objects either way, so this hardens. It closes no open advisory, and the documents say exactly that.
- **The module cache.** A module compiled by a GC-on engine and loaded by a GC-off one is recompiled or refused by wasmtime's compatibility check, never misread. The probe records which, and the cache's key needs no change if wasmtime refuses the mismatch (INFERRED; the probe is the evidence).

### 7. Fuel: recorded fresh, no growth flag

As 127's Decision 7: a row whose accepted `wasmtime` is not the run's goes to `fuel_not_compared`, and the acceptance records the fresh value. No `--accept-growth` is needed for fuel. A growth line for bytes stays red. The snapshot's bytes change by design (Decision 2), and the claim block names that.

### 8. What the documents say

- `SECURITY.md`'s upstream paragraph: the runner uses wasmtime-py 51.0.0, which bundles wasmtime 51.0.0. Two advisories reached 0.1.5 on Windows and are fixed by it: GHSA-f2pq-268w-886c (High) and GHSA-5m8g-xhq4-4h93 (Moderate), each as 3a and 3b found it. An embedder who drives the artifact set with its own wasmtime needs 50.0.3, 49.0.7, 48.0.10 or 36.0.22 for the first, and 50.0.2 or the matching patch line for the second. The other seven do not reach the runner, with one sentence on why. The build's command line is on the runner's line, 51.0.0. The three older bullets stay as they are, carried by 51.
- `docs/explanation/security-model.md`: the same, in words. A short paragraph says the GC proposal is off and why, and that the exception heap remains.
- `docs/get-started/install.md`, `docs/reference/support-and-versioning.md`, `docs/how-to/embed-from-other-languages.md`, `docs/explanation/why-wasi.md`, the README's *Hosts*: wasmtime 51 (`wasmtime>=51,<52`). `docs/explanation/performance-and-size.md` keeps the figures it dates to an older engine.

### 9. The shape of the change (not structural)

One config line and one message in `_engines.py`, one string in `_wasmtime_ffi.py`, data in `scripts/` and `downloads/`, and checks. No module-level mutable or lock, no private name outside the seam, no platform branch, no test seam that is not on the process object (3b uses the process object's), and no module or function nears a ceiling.

## Intent

A `pip install wasi-python` user on Windows can no longer climb out of a granted folder with a drive-prefixed name, and zero-length writes no longer grow the host's memory. The engine also stops accepting a WebAssembly feature the artifacts never use. Nothing else an embedder can observe changes but fuel figures and the snapshot's hash.

## Design

- `pyproject.toml`, `uv.lock`: Decision 1.
- `src/wasi_python/_wasmtime_ffi.py`: `PIN`. `src/wasi_python/_engines.py`: `cfg.wasm_gc = False` with its reason, and the `ImportError` message.
- `src/wasi_python/_fs_paths.py`: only if 3d's parity moves a mount's answer.
- `scripts/line.conf`, `downloads/SHA256SUMS` (and `scripts/00_download.sh` if it spells the version): Decision 2.
- The checks of Decision 3.
- `context/upstream/34-wasmtime-py-public-api-for-the-runner/facts.md`: its "Against" line.
- `SECURITY.md`, `README.md`, `docs/`: Decision 8.
- `context/changes/202-the-pin-moves-to-wasmtime-51.md`: the news file, its CHANGELOG lines below, and its claim block. A release-claims file of the same name if a release-tier row moves.

### The CHANGELOG lines

Under **Security**:

- **A guest on Windows can no longer leave its folder through a drive letter.** The runner moves to wasmtime 51, which refuses a `:` in any path on Windows. Before, a guest given any host folder could name a file such as `./C:secret`, which Windows reads relative to the current folder of drive C, and so read outside the folder, or write outside it through a writable one (GHSA-f2pq-268w-886c, High). Your own wasmtime needs 50.0.3, 49.0.7, 48.0.10 or 36.0.22 to have the fix. [Security model](https://claygendron.github.io/wasi-python/explanation/security-model/)
- **Empty writes no longer grow the host's memory on Windows.** A guest that wrote zero bytes to stdout or stderr millions of times could grow the host process's memory without limit, since those writes count against no cap (GHSA-5m8g-xhq4-4h93, Moderate). [Security model](https://claygendron.github.io/wasi-python/explanation/security-model/)
- **The engine refuses WebAssembly GC types.** The runtime uses exceptions but none of the GC proposal's structs and arrays, so the runner now turns that proposal off. A module that declares one is refused. [Security model](https://claygendron.github.io/wasi-python/explanation/security-model/)

Under **Upgrading**:

- **wasmtime 51 is required.** The wheel requires `wasmtime>=51,<52`. Fuel figures change slightly, since fuel is counted by the new engine. [Support and versioning](https://claygendron.github.io/wasi-python/reference/support-and-versioning/)

The builder adjusts a line to what 3a and 3b found. If a check showed no reach, its line says the fix is carried, not that 0.1.5 was exposed.

## Scope

In: the pin and the lock; the command line and the snapshot it makes; the GC proposal off; the checks of Decision 3; the documents of Decision 8; the news file. Out: a colon rule of the runner's own (Decision 5); wasmtime 51's new WASI buffer sizes (wasmtime-py does not expose them); the GuestProfiler, the component model, wasi-http; 115's second half and the roadmap's other 0.1.6 items, which move to 0.1.7 (`decisions.md`).

## Acceptance criteria

1. `pyproject.toml`, `_wasmtime_ffi.PIN` and `_engines._wasmtime`'s message spell `wasmtime>=51,<52`; `uv.lock` names 51.0.0; the seam imports; the wheel's library is recorded as bundling 51.0.0 (Decision 1).
2. `line.conf` names the 51.0.0 folders, `SHA256SUMS` pins their archives, `MANIFEST`'s `x-wizer` names 51.0.0, and the rebuild-from-pins check is green on the branch's release run (Decision 2).
3. 3a passes on three systems, and its Windows leg was seen red on 50.0.1 (or the landing notes say it was green there, and the documents say so).
4. 3b passes where it runs and was seen failing on 50.0.1, or the memo records why it was not added.
5. 3c, 3d, 3e and 3f pass on three systems; every slash row whose errno moved is recorded per system with its safety assertions unconditional.
6. Both engines refuse a GC struct type; the probe's memo shows no change in verdicts and none in fuel from the GC switch (Decision 6).
7. The fast tier is green on the branch, and the branch's run is green on three systems, with its `fuel_not_compared` rows named in the landing notes and no `grew` line for bytes other than the snapshot's, which the claim block names (Decision 7).
8. `ruff check`, `ruff format --check`, `mypy --strict` and the rules checks are green.

## For the lane

- **Order with the open pull requests.** #124 (199) and #126 (198) change `_fs_paths.py`. Neither changes the pin. Whichever lands second rebases. 3d's rows are read on the branch's own run after that rebase.
- **The claim list:** 3a and 3e new passes; 3b a new pass if added; 3c's row named or new; 3d's re-derived rows by node id; the pin's text rows; every metered check's fuel re-recorded under 51.0.0 (not compared); the snapshot's bytes changed by the new wizer.
- **Flags:** `--accept "202: the pin moves to wasmtime 51; the GC proposal is off"`, `--accept-judge "202: pyproject.toml and uv.lock move the pin to wasmtime>=51,<52; the build's wasmtime is 51.0.0; the slash rows follow wasmtime 51"`.
- **Then the release, 0.1.6.** Once 202's post-merge run accepts: a fresh agent writes the structural review of `src/`, another the security review (which reads 3a's and 3b's evidence); the preparation pull request carries them with `release/version.py bump --to 0.1.6` and `date`; the release pull request from `dev` to `main` runs the whole workflow, which verifies the GitHub attestations and reads PyPI's provenance back (spec 185); the owner moves `main` and tags `v0.1.6`. The repository advisory draft, `../research/2026-11-22-moving-to-wasmtime-51/advisory-draft.md`, is the owner's to publish, with its versions filled in from what 3a found.
- **The roadmap line** (at merge): "202, the pin moves to wasmtime 51: built and landed; the Windows drive-letter escape and the empty-write growth are closed; the GC proposal is off. Next: 0.1.6's reviews and release."

## Landing notes

Not built yet. The pre-build review comes first.

## One line

Move the runner and the build to wasmtime 51, which is the only way 0.1.5's Windows users get the fix for a High sandbox escape, and turn off the GC proposal while we are there, if the probe finds nothing.
