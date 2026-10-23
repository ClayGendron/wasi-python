# Typed grants

- **Status:** research, 2026-10-17
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5). Box: one session. It stopped where "Where it stopped" says.
- **Feeds:** the typed-grants specification. It ends constitution §4.15's alpha exception (the stdlib zip in the guest's writable root).
- **Stands on:** the owner's answers to questions 1 and 2 (`../questions-for-the-owner.md`): several grants, each a host path, a guest path and read-only or writable, possibly none; matplotlib's data is a read-only grant. Also `2026-10-16-where-package-data-lives.md` (findings 1 to 4), `2026-10-17-the-runtime-for-agent-code.md` §3.1 and §5 item 1, and `src/wasi_python/runner.py` (`run`, `_run_checked`, `_place_stdlib`, `_place_private`, `_real_dir`, `_instance`).

## Terms

- A **grant** is a host directory the embedder hands to the guest under a guest path, read-only or writable. Under WASI preview1 it is a **preopen**: a directory descriptor the runtime opens before the guest starts. A guest sees no file except through one.
- The **root** is today's one grant: a writable host directory at `/`. `root=` names it; without it the runner makes a fresh private one per call.
- A **shadow** is a file in the root at a path a grant also covers, such as `<root>/usr/local/lib/x` beside a grant at `/usr/local/lib`.
- **Longest prefix** is how wasi-libc picks the preopen for a path: the one whose guest path is the longest leading match, compared as text.

## Labels

Each claim is **EXECUTED** (run here, output shown or saved), **READ** (from a file or page, cited) or **INFERRED** (reasoned from the two).

## Method

- **Read:** the files named above; `recipes/reactor_main.c:194-208` (the snapshot's `__wasilibc_reset_preopens`); `scripts/steps/80_snapshot.sh`; `CHANGELOG.md:107`; README "Running it", "Safety" and "sqlite3 in the guest".
- **Read in prior art** (`context/prior_art/`, commits as recorded there): wasmtime `v49.0.3` (`f96eaba`): `crates/c-api/src/wasi.rs:312-338`, `crates/wasi/src/ctx.rs:296-317`, `crates/wasi/src/filesystem.rs`; wasmtime-py `280ce73`; pyodide `6754c1f` (`src/js/api.ts:560-640`).
- **wasi-libc as wasi-sdk 33 pins it.** The SDK's `VERSION` file says `wasi-libc: 161b3195fc25` (EXECUTED: `tar -xzf downloads/wasi-sdk-33.0-arm64-macos.tar.gz …/VERSION`). The prior-art clone is at `165235b`, a later commit. So `preopens.c` and `chdir.c` were fetched at `161b3195fc2558d2b1ba3eb9ffae3b2b47407623` from GitHub into the scratchpad (SHA-256 `e0d32b6a…` and `d7704ac0…`). Its `preopens.c` differs from the clone's only in the lock macro (EXECUTED: `diff`).
- **Executed** with the real artifact set (`WASI_PYTHON_ARTIFACTS=build/artifacts`, CPython 3.15.0, both binaries), wasmtime-py 49.0.0 from `.venv`, through `uv run`. A scratch harness (`harness.py`) calls the runner's own `_run_checked`. It passes a `wt` whose `WasiConfig` swaps the runner's one preopen at `/` for a list of typed grants, so the limits, the door, `poll_oneoff` and outputs are the runner's. A second probe (`probe_raw.py`) is a small WAT module of our own. It makes each mutating preview1 call directly. Every script and its output is in the session scratchpad, `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/grants/` (outputs under `out/`). No tracked file was changed except this memo.
- **Machine:** Apple M1 Pro, macOS 25.5, APFS (93 % full), host CPython 3.14.2. Windows and Linux were not run.

## 1. Read-only is enforced, by one flag (EXECUTED, READ)

**What wasmtime-py 49 offers.** `WasiConfig.preopen_dir(path, guest_path, fs_mutable=True)`. There is no `DirPerms` or `FilePerms` (EXECUTED: `inspect.signature`, and `[n for n in dir(wasmtime) if 'Perm' in n]` → `[]`). The two enums were removed in wasmtime-py 48.0.0, commit `2ed8d100` "Bump to 48.0.0 (#341)" (READ: `gh api` of the commit's patch). The docstring still describes `dir_perms` and `file_perms`, which no longer exist. The project pins `wasmtime>=49,<50` (`pyproject.toml:20`), so `fs_mutable` is the whole API.

**What the flag does (READ).** The C API maps `false` to `FsPerms::ReadOnly` (`c-api/src/wasi.rs:328-332`). wasmtime-wasi then opens the host directory with `OpenMode::READ` only (`wasi/src/ctx.rs:303-306`). Every mutating operation checks `perms.write_not_permitted()` first and answers `NotPermitted`: open with create, truncate or write (`filesystem.rs:1005-1008`), set-size (`:770`), set-times on a path or a descriptor (`:588`, `:595`, `:853`), mkdir (`:807`), link and rename (`:910-921`, `:1084-1092`), symlink (`:1111`), unlink and rmdir (`:1070`, `:1120`). Link and rename also refuse two preopens of different modes (`self.perms != new_dir.perms`).

The two older split permissions had a bypass, CVE-2026-47261 (GHSA-2r75-cxrj-cmph): a preopen with `DirPerms::MUTATE` and `FilePerms::READ` could still be opened with truncate. It is fixed in 24.0.9, 36.0.10 and 44.0.2 (READ: [the advisory](https://advisories.gitlab.com/cargo/wasmtime-wasi/CVE-2026-47261/)). 49's single `FsPerms` has no such split. Truncate on a read-only grant is refused below.

**Through Python in the guest** (`probe_q1.py`; same result on the snapshot and on the plain reactor; a writable grant is the control, reset before each operation):

| operation on `/ro` (read-only) | read-only | writable |
|---|---|---|
| read, `listdir`, `stat`, `open(O_RDONLY)` | ok | ok |
| `open` with `O_WRONLY`, `O_RDWR`, `O_WRONLY\|O_APPEND`, `O_RDONLY\|O_TRUNC` | EPERM (63) | ok |
| create, `O_CREAT\|O_EXCL` even with read-only access | EPERM | ok |
| `open(f, "w")`, `"a"`, `"r+"`; `os.truncate(path)` | EPERM | ok |
| rename in place; into or out of another preopen; `os.replace` over a file | EPERM | ok |
| `unlink`, `rmdir`, `mkdir`, `symlink` | EPERM | ok |
| `link` in place, out to a writable preopen, in from one | EPERM | ok |
| `os.utime` on a file, with `follow_symlinks=False`, and on a directory | EPERM | ok |
| `mkdir` and create through a directory descriptor (`dir_fd=`) | EPERM | ok |
| `tempfile.TemporaryFile(dir=B)` | EPERM | ok |
| on a read-only descriptor: `os.write` → EBADF (8); `os.ftruncate` → EPERM; `os.utime(fd)` → EPERM | | |
| `open(O_RDONLY\|O_APPEND)`; `os.fsync` on a read descriptor | ok (no write right follows) | ok |
| `os.chmod` | ok, and nothing changes | ok, nothing changes |

The host tree was unchanged after the read-only run: same names, `f.txt` still `original`, mode still `0o100644`. `os.chmod` "succeeds" because WASI preview1 has no chmod call and CPython's WASI build returns 0 without calling anything (READ: `Modules/posixmodule.c:4186-4189`, "WASI SDK 15.0 does not support chmod. Ignore missing syscall for now."). `os.chown`, `os.fchmod`, `os.mkfifo`, `os.posix_fallocate` and `fcntl` do not exist in the guest.

**Through the raw preview1 calls** (`probe_raw.py`, fd 3 is the grant, fd 4 a writable preopen):

| raw call | read-only | writable |
|---|---|---|
| `path_open` with all rights and no flags; with `CREAT`; `CREAT\|EXCL` and read rights; `TRUNC` and read rights | EPERM | ok |
| `path_open` with fdflag `APPEND` and read rights | ok | ok |
| `path_open` of `../outside.txt`; of a host link pointing out | EPERM | EPERM |
| `fd_write`, `fd_pwrite` on a read descriptor | EBADF | EBADF |
| `fd_filestat_set_size` on a read descriptor | EPERM | EINVAL |
| `fd_filestat_set_times` on the file, and on the grant's own descriptor | EPERM | ok |
| `fd_allocate`; `fd_fdstat_set_rights` to more rights | ENOTSUP (58) | ENOTSUP |
| `fd_fdstat_set_flags(APPEND)` on a read descriptor | ok | ok |
| `path_filestat_set_times` (follow and no-follow) | EPERM | ok |
| `path_link` in place, to fd 4, from fd 4 | EPERM | ok |
| `path_symlink`, `path_rename` (in place, to fd 4, from fd 4) | EPERM | ok |
| `path_unlink_file`, `path_remove_directory`, `path_create_directory` | EPERM | ok |

The read-only tree was asserted unchanged after every call. **The guest sees EPERM, WASI errno 63, `PermissionError` in Python.** The two "ok" rows on a read-only grant change no byte. An append flag on a read descriptor still cannot write (EBADF).

One thing the writable column shows: **a guest can hard-link and rename between two writable grants** (`path_link` and `path_rename` to and from fd 4 succeed when both are writable). It matters to the threats in section 7.

## 2. Nested grants: longest prefix, compared as text (READ, EXECUTED)

**How wasi-libc picks the preopen (READ, wasi-libc `161b3195`).**

- At registration, `strip_prefixes` removes only leading `/`, `./` and a lone `.` from the guest path (`preopens.c:155-172`). Nothing else is normalised.
- `__wasilibc_find_abspath` strips the path's leading `/`. It then walks the table from the last entry to the first and keeps the longest prefix that matches (`preopens.c:262-308`). A later entry wins a tie, because the test is a strict `len > match_len` taken in reverse.
- `prefix_matches` compares bytes with `memcmp` and requires the match to end at a `/` or at the end of the path. A trailing `/` in the prefix is ignored. An empty prefix matches any relative path (`preopens.c:204-224`).
- A relative path is first made absolute by joining it to the working directory as text, with no normalisation except a leading `./` (`chdir.c:79-130`). `chdir` records the preopen-relative result (`chdir.c:23-77`).
- The relative part handed to wasmtime may hold `..` and `.`. wasmtime resolves them inside that one preopen (cap-std) and refuses a path that leaves it.

**The probe** (`probe_q2.py`): a writable root at `/` and a read-only grant at `/usr/local/lib` holding the zip and `which.txt` = `GRANT`. In variant A the root also holds a shadow `usr/local/lib/which.txt` = `ROOT-SHADOW`; in variant B the root has no `usr/`. The snapshot and the plain reactor gave the same lines.

| path the guest opens | A | B |
|---|---|---|
| `/usr/local/lib/python315.zip` (`sys.path[0]`; `json.__file__` is under it) | grant | grant |
| `/usr/local/lib/which.txt`, `//usr/…`, `/usr/local/lib/./which.txt`, `/usr/local/lib//which.txt` | GRANT | GRANT |
| `/./usr/local/lib/…`, `/usr/./local/lib/…`, `/usr//local/lib/…`, `/usr/local/../local/lib/…` | ROOT-SHADOW | ENOENT |
| `/usr/local/lib/../lib/which.txt` | EPERM | EPERM |
| relative `usr/local/lib/which.txt` and `./usr/…` from cwd `/` | GRANT | GRANT |
| `chdir("/usr")`, then `local/lib/which.txt` | GRANT | ENOENT (no `/usr`) |
| `chdir("/usr/local/lib")`, then `which.txt`; `os.getcwd()` | GRANT; `/usr/local/lib` | same |
| …then `../lib/which.txt` | EPERM | EPERM |
| `os.listdir("/usr/local")` | `['lib']` (the root's) | ENOENT |
| `os.path.realpath("/usr/./local/lib/which.txt")` | `/usr/local/lib/which.txt` | same |

What it means:

- **Only the exact spelling reaches the grant.** A path that spells the prefix differently, with `.`, `..` or `//` before the prefix ends, goes to the root and sees the root's own files. CPython imports through the exact string in `sys.path`, so imports always reach the grant (EXECUTED: after the planting below, `import csv` still came from the grant).
- **`..` never crosses from one preopen to another.** `/usr/local/lib/../lib/x` is EPERM, even though the target is inside the guest's namespace. Native code that walks up out of a grant fails where it would work on a real filesystem.
- **The directories above a grant exist only if the root has them.** With no shadow `usr/`, `chdir("/usr")` and `listdir("/usr/local")` fail.

**Links the guest makes in the root (EXECUTED).**

- `os.symlink("/usr/local/lib/which.txt", "/lnk_abs")`: EPERM. wasmtime refuses to create a link with an absolute target.
- `os.symlink("usr/local/lib/which.txt", "/lnk_rel")`: made. Reading it gives `ROOT-SHADOW` in A and ENOENT in B. A link resolves inside the preopen that holds it and never reaches another preopen.
- `os.symlink("../../usr/local/lib/which.txt", "/lnk_up")`: **made**. Reading it is EPERM. The guest can create a link that points out of its grant but cannot follow it (README "Safety" already says so). Section 7 shows why the host must care.
- `os.link` from the root to a grant file: EPERM.

**Can the guest write into the read-only area through the root? (EXECUTED)** Not into the grant. `open("/usr/local/lib/which.txt", "w")`, the same for `python315.zip`, `mkdir("/usr/local/lib")` and `os.replace(root file, "/usr/local/lib/which.txt")` were all EPERM. But `makedirs("/usr/./local/lib")` and writing `/usr/./local/lib/python315.zip` and `which.txt` succeeded: they landed in the root, as shadows. After that, `/usr/local/lib/which.txt` still read `GRANT` and `/usr/./local/lib/which.txt` read `PLANTED`. The host grant was unchanged (names, text and the zip's SHA-256). **A shadow is invisible to imports and to every exact spelling. It is visible only to code that spells the path oddly.**

**Can the guest reach a host path outside every grant? (EXECUTED)** No, through any path it spells. `/../../etc/passwd` and `listdir("/..")` are EPERM. A host link inside a grant that points out is refused (`probe_raw`, `open_follow_link_out`). With no root, a path under no grant answers ENOENT from wasi-libc before any call is made (`preopens.c:291-294`; section 4). The one way out goes through the host, not the guest: a link the guest leaves that a later grant's host path follows (section 7, threat a).

## 3. The snapshot honours grants by name, in any order (EXECUTED)

`recipes/reactor_main.c:204-206` calls `__wasilibc_reset_preopens()` at the end of `wizer.initialize`, so the table is rebuilt from the runtime's preopens on first use (READ).

**Many grants, every order** (`probe_q3.py`). Five grants: the zip read-only at `/usr/local/lib`, `/data` read-only, `/out` writable, `/tmp` writable, and a grant nested under the zip's own name, `/usr/local/lib/python315.zip/matplotlib/mpl-data`, read-only. All 120 orders gave one identical result on the snapshot, and the same on the plain reactor: each path read its own grant's marker, `/out` took a write, `/data` refused one (EPERM), and numpy and pandas ran. The CHANGELOG's claim (`CHANGELOG.md:107`) holds.

**The zip from a read-only grant works** on both binaries, with no root at all (sections 3 and 4). Fuel does not move beyond its usual spread (`probe_fuel.py`, `probe_fuel2.py`, seven runs each): `pass` on the snapshot spends 81.9 to 82.0 M either way. `import email.parser, statistics` spends 175.9 M with the zip in the root and 176.0 to 176.1 M from a grant, about 0.06 % more. One more preopen to compare per path lookup would explain it (INFERRED).

**The zip must be at exactly `/usr/local/lib/python315.zip`, with exactly the artifact's bytes** (EXECUTED, `PROGS` in `probe_q3.py`):

| case | snapshot | plain reactor |
|---|---|---|
| the zip only at `/opt/python315.zip` | `print`, `import csv`, numpy and pandas work (all were imported at snapshot time); `import email.parser` fails, `FileNotFoundError … '/usr/local/lib/python315.zip'` | fails at start: `Failed to import encodings module` |
| a different zip at the right path (one member left out) | the same pre-imported modules work; `import email.parser` fails, `ZipImportError: bad local file header` | reads the new zip: works except the missing module (`No module named '__future__'`) |
| no grant at all | as the first row | as the first row |

The snapshot keeps zipimport's index of the zip it was built against (spec 003 Decision 9, READ). So the snapshot does not fail at start without its zip. It fails at the first import that is not pre-imported. A different zip is read through the stale index. **The runner must therefore grant the artifact's own zip, checked by hash, on every call. The guest cannot check it.**

**No writable grant at all** (the zip read-only and nothing else; section 4 has the table). CPython starts on both binaries. `print`, numpy and pandas imports, and imports from the zip work. `__pycache__` is never written: the bootstrap sets `write_bytecode = 0` (`reactor_main.c:131`, READ). What breaks is `tempfile`, `HOME`, `/` itself, and any relative path (section 4).

## 4. No root: what `/`, `/tmp` and `HOME` should be (EXECUTED)

`probe_q4.py`, `probe_q4b.py` and `probe_home.py`. The zip is read-only at `/usr/local/lib`; `/data` (read-only) holds a CSV and a SQLite file. Both binaries gave the same lines.

| program | 1. nothing writable | 1b. only `/out` writable | 2. a private `/tmp` (and `/out`) | 3. an empty read-only `/` plus private `/tmp` |
|---|---|---|---|---|
| `print` | ok | ok | ok | ok |
| `import numpy, pandas`; `import email.parser` | ok | ok | ok | ok |
| `os.getcwd()` | `/` | `/` | `/` | `/` |
| `os.stat("/")`, `os.listdir("/")` | ENOENT | ENOENT | ENOENT | a directory; `[]` |
| `open("rel.txt", "w")` from cwd `/` | ENOENT | ENOENT | ENOENT | EPERM |
| `tempfile.gettempdir()`, `TemporaryFile()`, `mkdtemp()` | `FileNotFoundError: No usable temporary directory` | same | ok, under `/tmp` | ok |
| `HOME` (the runner's `/tmp/.home-<hex>`) | set, but missing: `Path.home().exists()` False | same | `HOME=/tmp/home`: exists | — |
| `pd.read_csv("/data/in.csv")` and a groupby | ok | ok | ok | — |
| `df.to_csv("/out/res.csv")` | `OSError: Cannot save file into a non-existent directory` | ok | ok | — |
| `df.to_csv("/data/res.csv")` (read-only) | EPERM | EPERM | EPERM | — |
| `sqlite3` `:memory:` and a temp table | ok | ok | ok | — |
| `sqlite3` file in `/out` | `unable to open database file` | ok | ok | — |
| `sqlite3` file in read-only `/data`, plain or `mode=ro` | `access permission denied` | same | same | — |
| `zoneinfo.ZoneInfo("Europe/Paris")` | ok | ok | ok | — |

The SQLite row is the README's known fact: a database in a read-only directory opens only through `immutable=1` or `nolock=1`, because its lock is a directory made beside it (README "sqlite3 in the guest", READ).

With `HOME` removed from the environment (`probe_home.py`): `os.path.expanduser("~/x")` returns `~/x` unchanged, `pathlib.Path.home()` raises `RuntimeError: Could not determine home directory`, and imports work.

Option 3 shows one more fact: **a grant never appears in a listing of its parent.** `os.listdir("/")` on an empty read-only root is `[]`, and `os.walk("/")` finds nothing, while `/tmp` and `/usr/local/lib` both work. A program discovers its grants only by name.

**What the runner should give (INFERRED from the table).**

- **Nothing writable is a valid run.** Pure computation, imports and reading granted data work. Only temporary files and relative writes fail, each with an ordinary `OSError`.
- **A private `/tmp` is what most programs miss.** It is the only change between columns 1b and 2 that matters, and it is the runner's own fresh directory, as today's private root is.
- **An empty read-only `/` buys little.** It makes `stat("/")` succeed and turns ENOENT into EPERM for relative writes, at the cost of a fourth preopen. Not recommended.
- **`HOME`:** inside the private `/tmp` when there is one, as today; otherwise left unset, so a program gets Python's own "no home" answer rather than a path that does not exist.

## 5. Cost: what the zip's placement costs today (EXECUTED, a benchmark)

`bench_q5.py`, medians of 25 (9 for the hashes), wall time, the snapshot, the module warm in the process, the zip 11,140,578 bytes. These are benchmark facts, not test numbers.

| what | median | min to max |
|---|---|---|
| no root today: `mkdtemp` + copy the zip + `rmtree`, per call | 6.99 ms | 5.15 to 7.88 |
| the same without the zip (`mkdtemp` + `tmp/` + `rmtree`) | 0.39 ms | 0.22 to 1.88 |
| `root=`, zip unchanged: `_place_stdlib`'s stamp check, per call | 0.05 ms | 0.05 to 0.12 |
| `root=`, a new process or coarse times: hash the root's zip | 5.39 ms | 5.37 to 5.53 |
| `root=`, zip changed by a guest: copy and rename | 4.90 ms | 3.16 to 12.48 |
| a shared directory: copy + SHA-256, once per process | 9.76 ms | 8.81 to 13.57 |
| SHA-256 of the artifact zip alone | 5.75 ms | 5.46 to 5.89 |
| `run(["-c", "pass"])` today, no root | 26.73 ms | 24.15 to 37.23 |
| `run(["-c", "pass"], root=…)` today, zip already placed | 23.10 ms | 20.53 to 36.25 |
| private root without the zip + a shared read-only zip grant | 23.77 ms | 21.10 to 73.34 |
| a shared read-only zip grant only, no root granted | 23.01 ms | 21.66 to 30.83 |
| control: the same harness with today's copy into the root | 24.90 ms | 23.03 to 49.44 |

- **A call without `root` saves about 6.6 ms of host work and 11 MB of disk writes** when the zip comes from a shared directory: 6.99 ms against 0.39 ms. End to end that showed as 26.7 ms against 23.0 to 23.8 ms. N concurrent calls today hold N copies of the zip on disk.
- **A call with `root=` saves little time.** Its stamp check is 0.05 ms. It saves the first call's copy, the 5.4 ms hash per new process, and the guest's ability to make the next call re-copy.
- **The shared directory costs about 10 ms once per process** (copy and hash), or 5.8 ms if the hash alone is checked against a copy that already exists. After that a call pays one stamp check.

## 6. How others express mounts and permissions (READ)

| system | shape | read-only | default | source |
|---|---|---|---|---|
| wasmtime CLI 49 | `--dir HOST[::GUEST]`, repeated | **none**: no flag for a read-only `--dir` (`wasmtime run --help`, `-S help`, EXECUTED) | no directory | `build/tools/wasmtime-v49.0.3-aarch64-macos/wasmtime run --help`; [CLI options](https://docs.wasmtime.dev/cli-options.html) |
| wasmtime-py 49 | `WasiConfig.preopen_dir(path, guest_path, fs_mutable=True)`, one call per grant | `fs_mutable=False` | writable | `wasmtime/_wasi.py:172`; commit `2ed8d100` |
| wasmtime-wasi (Rust) 49 | `WasiCtxBuilder::preopened_dir(host, guest, FsPerms)` | `FsPerms::ReadOnly` | n/a (required) | `crates/wasi/src/ctx.rs:296` |
| Deno | `--allow-read[=P,…]`, `--allow-write[=P,…]`, `--deny-read`, `--deny-write`; host paths only, no renaming | a path in `--allow-read` but not `--allow-write` | nothing allowed; deny wins over allow; checks a link by its location, not its target | [security](https://docs.deno.com/runtime/fundamentals/security/), [permissions](https://docs.deno.com/runtime/reference/permissions/) |
| Pyodide (Node) | `pyodide.mountNodeFS(emscriptenPath, hostPath)`; `mountNativeFS(path, handle)` in the browser | none | nothing mounted; the host path must exist and be a directory | [JS API](https://pyodide.org/en/stable/usage/api/js-api.html); `src/js/api.ts:569-640` |
| Docker | `-v host:container[:ro]`; `--mount type=bind,src=,dst=,readonly` | `:ro` / `readonly`; `bind-recursive` decides submounts | `-v` creates a missing host path, `--mount` refuses it | [bind mounts](https://docs.docker.com/engine/storage/bind-mounts/) |
| Modal | `volumes={"/data": vol}` on a function or `Sandbox.create` | `vol.with_mount_options(read_only=True)`, per mount | writable | [volumes](https://modal.com/docs/guide/volumes) |
| E2B | no host mount; files are uploaded, written, read and downloaded through the sandbox's files API | n/a | nothing | [filesystem](https://docs.e2b.dev/filesystem) |

What the survey says (INFERRED):

- **Every system that maps a guest path takes (host, guest, mode) per mount.** Only the spelling differs: a positional triple (wasmtime), a string (Docker), a mapping with a per-mount option (Modal).
- **Deno splits by mode** (one list to read, one to write), but it does not rename paths, so it needs no guest path.
- **Mode is opt-in for read-only in wasmtime, Docker and Modal.** Writable is their default. That default is the wrong one under §4.15.
- **Docker's `-v` creates a missing host path; its newer `--mount` refuses one.** Refusing is the safer choice, and wasmtime refuses anyway (EXECUTED: `failed to add preopen dir` for a missing path and for a file).
- **Pyodide refuses a mount point that is not empty.** WASI has no such rule: a grant simply hides whatever the root has under it, as a shadow (section 2).

### Candidate shapes for `run`

`root=` must keep working (it is in the public API and the README). Each candidate keeps it.

- **A. A small value type.** `grants=[Grant(host, guest), Grant(out, "/out", writable=True)]`. `Grant` is a frozen dataclass exported by `wasi_python`, read-only unless `writable=True`.
  - For: one value holds everything, so it is checked and named in an error as a unit. The default is safe. It has room for a later field without a new `run` argument, such as an importable flag (question 16, research memo §5 item 5). It reads like wasmtime's own triple.
  - Against: one more public name, and an import for the caller.
- **B. Triples.** `grants=[(host, guest, "ro"), (out, "/out", "rw")]`.
  - For: no new name; Docker-like.
  - Against: a mode string can be misspelt, so it needs its own checks. Tuples cannot grow a field without breaking callers. An omitted mode has no obvious safe reading.
- **C. Two mappings, Deno-like.** `read={"/data": host}, write={"/out": host}`.
  - For: shortest at the call site; the mode is the argument's name; a guest path cannot repeat within one mapping.
  - Against: two new `run` arguments now and more for every later kind of grant. A guest path can still appear in both mappings, so that must be checked. It does not fit `run_async`'s pass-through as neatly as one argument.
- **D. One mapping with a wrapper.** `grants={"/data": host, "/out": writable(host)}`.
  - For: one argument; read-only by default.
  - Against: two kinds of value in one mapping. The guest path is the key, so normalising it can merge two keys silently.
- **E. Docker strings.** `"host:guest:ro"`. Rejected: `:` is in Windows paths (`C:\data`), and a string hides a typo until it is parsed.

**Recommended: A**, with `root=` kept and given a third value.

```python
from wasi_python import Grant, run

run(argv, grants=[Grant("in", "/data"), Grant("out", "/out", writable=True)])
run(argv, root=False, grants=[Grant("in", "/data")])   # nothing writable at all
```

- `root=None` (the default) is today's fresh private writable root at `/`, minus the zip.
- `root=path` is today's `root=`: that directory, writable, at `/`, minus the zip.
- `root=False` is no root: the guest sees only its grants, possibly none, and the runtime's own read-only zip.
- The runner always adds its own read-only grant at `/usr/local/lib`. It is not in `grants`.

## 7. Threats specific to grants, and the runner's checks

**a. A link a guest left, followed by a later grant's host path (EXECUTED).** Call 1 had a writable grant over a shared work tree. It replaced `shared/data` with a relative link, `data -> ../secret`, which it is allowed to make. Call 2 granted `shared/data` read-only, by host path. wasmtime followed the link when it opened the host directory. Call 2's guest read `['key.txt'] HOST SECRET` from a directory no grant named. The same happens today when a later `root=` names a path under an earlier call's root (INFERRED). wasmtime also follows a link given directly as the host path (EXECUTED: `f host path link-to-secret` listed the secret). *Check:* resolve each host path without following any link that sits in a directory this process can write. A guest writes as this user, so only such a link could be a guest's. A link in a directory this user cannot write, such as macOS's `/var -> private/var`, is the system's and may be followed. Refuse otherwise, before any work.

**b. A TOCTOU swap between the check and the preopen (INFERRED; one mitigation EXECUTED).** wasmtime opens the host directory by path inside `preopen_dir` (READ: `ctx.rs:302`). A guest that runs at the same time and can write a parent of that path can swap it in between. The obvious fix is to open the directory once with `O_NOFOLLOW|O_DIRECTORY` and preopen `/dev/fd/N`. **It does not work on macOS:** `preopen_dir("/dev/fd/N")` raises `failed to add preopen dir` (EXECUTED). Linux's `/proc/self/fd/N` was not tried. *Check:* record `(st_dev, st_ino)` from a no-follow open before the preopen. After the preopen, compare it with what the guest's preopen really is. That can be read by calling `fd_filestat_get` on the new descriptor from a tiny module of the runner's own in the same store, before the guest runs (INFERRED, untried). Refuse the call on a mismatch. Document the rest: do not grant a directory that sits inside a directory another running guest can write.

**c. Two grants at the same guest path (EXECUTED).** The one given last wins (`SECOND` with d1 then d2, `FIRST` with d2 then d1), as wasi-libc's reverse walk predicts. The other is silently hidden. *Check:* refuse a repeated guest path after normalising it. **Nested** guest paths (`/d` read-only with `/d/out` writable) work by longest prefix (EXECUTED) and are allowed.

**d. A guest path that is not absolute or holds `.`, `..` or `//` (EXECUTED).** wasmtime takes any string. wasi-libc strips only leading `/` and `./`. So `data`, `./data` and `/data/` all mean `/data`. `/a/../data` and `/data//x` match only that exact text, which no normal program spells. `""` becomes a second root. *Check:* the guest path must be a `str`, absolute, with no NUL, no empty, `.` or `..` component and no trailing `/`. It must not be `/` (that is `root=`). It must not be `/usr/local/lib` or under it: that is the runtime's, and a grant there could hide the zip or, under the zip's name, stand in for matplotlib's data.

**e. One host directory granted twice, or a read-only grant inside a writable one (EXECUTED).** Granted as `/ro` and `/rw`, a write through `/rw` was read back as `CHANGED` through `/ro`. With `c` writable at `/rw` and `c/sub` read-only at `/ro`, the same. Read-only means "not writable through this name", not "unchanging". *Check:* compare the resolved host paths. Refuse a read-only grant that is equal to, or inside, a writable grant's host directory. A writable grant inside a read-only one (`/src` read-only, `/src/out` writable) is the common pattern and is allowed. Its writes show in the read-only view.

**f. A writable grant that reaches the runtime's own files (INFERRED from section 1's writable column).** A writable grant at or above the runner's shared zip directory lets a guest rewrite the zip that every later call trusts. One at or above the `.cwasm` cache lets it write native code that a later process loads: the cache checks owner and mode (`_private`, `runner.py:1432-1448`), and the guest writes as that owner. One above the system temporary directory reaches other calls' private roots. *Check:* refuse a writable grant, `root=` included, that is equal to, inside, or above the shared zip directory, the artifact directory or the module cache.

**g. Hard links between writable grants (EXECUTED: section 1, raw `path_link` to and from fd 4).** A guest can make a file in output grant B that is the same inode as a file in writable grant A. Host code that later edits B's file in place edits A's. *Check:* none before the call. The rule goes with `Completed.outputs` (research memo §5 item 4): write-back copies, or refuses a file with `st_nlink > 1`, as well as never following a link.

**h. Windows (not run; INFERRED).** wasmtime opens directories through cap-std on Windows too (READ in the earlier memo). Path checks there must compare `os.path.normcase` of the resolved paths, since names are case-insensitive. `\\?\` and drive-relative forms must be resolved first. A guest cannot make a link on Windows (`runner.py:527-529` says so), which removes threat a's guest-made link, but not a junction an embedder made. `/dev/fd` does not exist there.

## 7b, answered: the post-preopen check works (EXECUTED by the author, 2026-10-17)

Threat b's check was untried when this memo was written. It now has a result.

- A tiny module (two WASI imports, `fd_filestat_get` and `fd_prestat_get`) instantiated in a store that has preopens reads each preopen's `filestat`. wasmtime does not report the host's numbers: `dev` is always 1 and `ino` is a hash.
- The hash is a fixed function of the host directory: the same folder gave the same `ino` in two stores and in two processes, and another folder a different one.
- READ (`crates/wasi/src/filesystem.rs:354-371`, `filesystem/unix.rs:107-118`): on POSIX the `ino` is the lower 64 bits of `MetadataHashValue::new((st_dev, st_ino))`, Rust's `DefaultHasher` over the pair, which is SipHash-1-3 with zero keys over the two values as little-endian 64-bit words. wasmtime's own comment warns it "may change when a different rustc release is used to build this host implementation".
- EXECUTED: a 30-line SipHash-1-3 in Python over `struct.pack("<QQ", st_dev, st_ino)` of the scratch folder gave `14205808286320391386`, the `ino` the guest's `fd_filestat_get` reported.
- So the runner can open each grant's host directory itself, without following links, `fstat` it, and compare the hash with what the call's own preopen reports, before the guest runs. A swap between the check and the preopen shows as a mismatch. A wasmtime build that hashes differently refuses every grant, loudly; a unit test that compares the two on a scratch folder pins it, so the pin move is where it fails first.
- Windows hashes a different identity (`filesystem/windows.rs`); it was not reproduced. There a guest cannot make a link, so a swap can only exchange directories inside the guest's own writable area, which reaches no host path outside the grants (INFERRED).

## Where it stopped

- Windows and Linux were not run. The Linux `/proc/self/fd/N` preopen is untried; the `fd_filestat_get` post-check (threat b) was later tried on macOS and works (section 7b).
- The `.cwasm` threat (f) was reasoned, not demonstrated: no native code was written.
- The private `/tmp` and `HOME` rules were probed through the harness, not through a changed runner.

## Recommendations for the specification

1. **The API is `grants=[Grant(host, guest, *, writable=False)]`, and `root` gains `False`.** `Grant` is a frozen dataclass; the default is read-only. `root=None` keeps today's private writable root, `root=path` keeps today's `root=`, and `root=False` gives only the grants. `run` and `run_async` take the same arguments. *Evidence:* section 6 (every surveyed system uses (host, guest, mode); wasmtime, Docker and Modal default to writable, which §4.15 forbids); section 4 (nothing writable is a working run).
2. **The zip moves to one read-only directory per process, granted at `/usr/local/lib`, on every call, on both binaries.** The runner copies the artifact's zip into a fresh `0700` directory once, as `python315.zip` alone, and checks its SHA-256 against the artifact's. Each call checks the copy's stamp, as `_place_stdlib` does today, and re-copies on a change. The runner stops writing the zip into any root. This ends §4.15's alpha exception. *Evidence:* sections 1 (all writes refused, EPERM), 2 (imports reach the grant, not a shadow), 3 (all 120 orders, both binaries; fuel within its spread) and 5 (6.6 ms and 11 MB saved per call without a root).
3. **The runner gives `/tmp` as today when there is a root, and none when `root=False`.** With a root, `/tmp` and the fresh `HOME` stay inside it. With `root=False`, `TMPDIR` stays `/tmp`. `HOME` is made fresh inside a writable grant at `/tmp` if the caller gave one, and is left unset otherwise. *Evidence:* section 4 (tempfile and `Path.home()` are what break; an unset `HOME` gives Python's own error).
4. **Check every grant before any work, raising `TypeError` or `ValueError` as spec 013 does.** The guest path rules (threat d), no repeated guest path (c), host paths resolved without following a link in a directory this process can write (a), host directories that exist and are directories (wasmtime refuses the others late, with an opaque error), no read-only grant inside a writable one (e), and no writable grant that reaches the runtime's own files (f). *Evidence:* section 7, each item EXECUTED except f.
5. **Verify after the preopen that each grant is the directory that was checked.** Prefer the `fd_filestat_get` comparison from a runner-owned module in the same store. It needs one experiment first. If it fails, use a second no-follow walk and document the residual race. *Evidence:* section 7 b (`/dev/fd/N` is refused on macOS).
6. **The embedder contract changes in one line.** README "Any other embedder" step 1 becomes: preopen the artifact set's zip, read-only, in a directory at `/usr/local/lib`, plus whatever the embedder grants, possibly nothing. The snapshot needs no rebuild. *Evidence:* section 3.
7. **The README gains four facts.** `..` never crosses between grants. A grant does not appear in a listing of its parent. A read-only grant can change if the same host files are writable elsewhere. A database in a read-only grant needs `immutable=1`. *Evidence:* sections 2, 4 and 7 e.
8. **Checks to write before the code** (spec 002's judge): a read-only grant refuses each operation in section 1's table with EPERM and leaves the host bytes unchanged; the snapshot reads five grants in shuffled orders; `root=False` with no grants runs `print` and pandas; each refusal in recommendation 4 raises before a store exists; and the runner never writes into a `root=` directory except `tmp/`. *Evidence:* the probes in the scratchpad, which the checks can follow.

## Questions for the owner

1. **Does `run(argv)`, with no root and no grants, keep its private writable root at `/`?** *Recommended: yes.* Changing it to a private `/tmp` only, or to nothing writable, is safer. But it breaks today's callers that write a relative or absolute file (section 4), and a default is the owner's to change (§4.15). `root=False` makes the stricter run available either way.
2. **May an embedder's grant be importable?** This is question 16, unchanged. The `Grant` shape leaves room for an `importable` field. This specification does not add one.

## One line

Give each grant a host path, a guest path and a mode that defaults to read-only. Serve the zip from one read-only, hash-checked directory per process at `/usr/local/lib`, which wasmtime enforces with EPERM and the snapshot already honours in any order. Check every grant on the host before the call, because the guest cannot escape by any path it spells, but a link it leaves can redirect the next grant.
