# A principal engineer's direction

- **Status:** review, 2026-10-16. An assessment and a ranked direction; it
  commits the project to nothing until the owner decides the items marked
  **constitution**.
- **Owner:** Clay Gendron
- **Researcher:** a principal-engineer review agent (Claude Fable 5.1), who
  wrote none of the code or documents assessed. Box: 90 minutes; stopped
  at about 85.
- **The framing it answers:** the owner's, verbatim: "the main users of
  this project will be people running AI-generated code in a safe and
  secure way, so we should optimize for that use case", built "so anyone
  can embed it", with "no way (unless explicitly provided) to access the
  host file system or network"; a "drop-in, easy-to-use, sealed Python
  on WASI meant for lightweight loads". And the owner's three-layer
  filesystem design (section 4 quotes it).

## Method

- **Read:** `constitution.md`, `AGENTS.md`, `README.md`,
  `context/README.md`; specifications 001 to 005; the runner
  (`src/wasi_python/runner.py`, `__init__.py`); the guest side
  (`recipes/reactor_main.c`, `reactor_bootstrap.py`, `hostmodule.c`);
  the checks under `tests/checks/`; `tests/known_gaps.toml`; the release
  workflow and `pyproject.toml`; the memos on package data, data folders,
  C++ exceptions, matplotlib, the lean exit, profiles, fuel, the host
  clock, the snapshot, and the autonomous-port study; the wasi-vfs
  experiment's scripts; wasi-vfs's README in `prior_art/`.
- **Executed**, on the 0.1.0a1 artifacts in `build/artifacts/` through
  `wasi_python.run` and through wasmtime-py directly, on scratch roots
  under the session scratchpad, with `$WASI_PYTHON_CACHE` pointed there
  (nothing under `build/` was written):
  - `uv run pytest -m "not slow" -q -p no:cacheprovider`;
  - a probe of twenty guest behaviours (`scratchpad/principal/probe.py`):
    environment, clock, entropy, host paths, links, processes, disk,
    stdout, memory, hashing, fuel repeatability, the door, errors, fuel
    and deadline traps;
  - a zero-preopen start of the snapshot, and an embedder-shadowed
    `path_open` (the owner's layer 3b), through wasmtime-py's
    `Linker.allow_shadowing`.
- Every claim below is labelled EXECUTED (run here), READ (seen in a
  file) or INFERRED (reasoned from the two).

Terms used throughout. A **preopen** is a host directory the embedder
hands the guest under a guest path; under WASI preview1 it is the only
way a guest sees a file. The **door** is the one custom import,
`host::call`, whose frames the embedder defines. **Fuel** is wasmtime's
count of executed instructions. The **snapshot** is the reactor after
Wizer ran its imports at build time. The **judge** is `uv run pytest`.
A **grant** is anything the embedder explicitly gives the guest: a
preopen, an environment variable, a host function behind the door.

## 1. Where the project stands (the scoreboard, EXECUTED)

`wasi_python v1: 86/94 pass · 1 gap · 2 blocked · 1 fail · 4 deselected
(unit suite 155/155)`. The one failure is
`test_every_prior_art_clone_has_its_licence_recorded`: a research agent
cloned `wasi-vfs` into `prior_art/` during this box without recording
its licence yet. That is the rules check doing its job on in-flight
work, not a defect in the product. The two blocked checks are the wheel
and the three-systems run, both release work.

The short verdict. The build is right: zero patches, pinned inputs, a
static binary, a byte-reproducible snapshot, and a judge that counts
operations and refuses to lose a pass. The isolation is real where it
is claimed: no host path, no network, no process. What is wrong is
narrower than it looks and is all in one place: **the product's
filesystem is one writable host directory that the runtime's own files
share with the untrusted program**, and three consequences of that are
exposed below. What is missing is that **safety is claimed but not
judged**: of 94 checks, three test the wall (`test_guest_sees_only_its_root`,
`test_guest_has_no_network`, and the link checks in v1.4), and none
tests a hostile guest's resource use or cross-run contamination.

## 2. Threat model for AI-generated code

### Assets

1. The host: its filesystem, network, processes, other users' data, and
   the embedder's secrets in its own memory and environment.
2. The embedder's other runs: their inputs, outputs and roots.
3. The runtime's own files: the binary, the stdlib zip, the `.cwasm`
   cache, the artifact set on disk.
4. The integrity of the result: that what the embedder gets back is what
   the program computed, and that the embedder can tell a program that
   finished from one that was stopped.
5. The embedder's resources: CPU, memory, disk, the memory holding
   captured output.

### Adversary

The program itself. AI-generated code is untrusted in two ways: it is
wrong by accident, and it can be steered on purpose by prompt injection
in the data it reads (a CSV cell that says "write your findings to
`/etc/cron.d`", a document that asks the agent to exfiltrate). The
adversary therefore has: arbitrary Python inside the guest, every WASI
preview1 call the binary imports (42: READ, spec 005 Decision 4), the
door, and whatever the embedder granted. It does not have: a second
instance, the host's clock resolution beyond what WASI gives, or any
host-specific behaviour (constitution §4.3).

### Boundaries and channels: what is enforced versus what is claimed

| channel | claim (READ: README, constitution §2.2) | what holds today | label |
|---|---|---|---|
| host filesystem | "sees only the directories you hand it" | `/..`, `/etc/passwd`, `/Users`, `/proc`, an absolute host path: all absent. A symbolic link with an absolute host target is refused at creation (errno 63); a relative link that climbs out is created but refused on open (63). | EXECUTED |
| network | none | `socket.socket` fails; `_ssl`, `_socket` absent | EXECUTED (judge `test_guest_has_no_network`) |
| processes | none | `os.fork`, `system`, `execv`, `spawnv` absent; `subprocess.run` raises `OSError` | EXECUTED |
| environment | "nothing is inherited from the host" | `os.environ` holds exactly what `env=` gave, else nothing | EXECUTED |
| the door | opaque frames, −1 without a host | `ConnectionRefusedError` without a host; `OSError` on a host fault | EXECUTED |
| stdout/stderr | captured | **unbounded**: 64 MB written by the guest was held in the embedder's memory; there is no cap | EXECUTED |
| disk in the root | the guest "can write anything in it" (spec 001) | **unbounded**: 200 MB written in 1 MB chunks; no quota | EXECUTED |
| memory | `memory_bytes` caps it | **no default cap**: 1 GiB allocated with no argument; wasm32's own ceiling is 4 GiB. With `memory_bytes=256 MiB` the guest gets `MemoryError`, as documented | EXECUTED |
| CPU | fuel and `deadline_s` | both work: `out of fuel` with `fuel_used` exact; `deadline` with `fuel_used` `None` (wasmtime's known limit). **Neither has a default**; a call with no limits runs forever | EXECUTED |
| exit code | the program's | 8 bits, as POSIX; a covert channel of one byte, not worth closing | EXECUTED |
| timing | not claimed | `time.time()` is the real wall clock and `perf_counter` has sub-millisecond resolution; a guest can time its own operations and so measure the host (a side channel class, not an escape) | EXECUTED |
| entropy | real | `os.urandom` is real; the snapshot's string hash secret is fixed (`hash_randomization == 0`), the plain reactor's is random | EXECUTED |
| the stdlib zip | re-placed before every call; links never followed | holds (the v1.4 checks); a vandalised zip is replaced | EXECUTED (judge) |
| the `.cwasm` cache | user-private only | directory `0700`, files `0600`, owner-checked; a cache another user can write is refused with a warning | READ (`_private`), EXECUTED (judge) |

**Cross-run contamination.** This is the weakest point, and it is now
proven rather than suspected. From
`2026-10-16-what-data-folders-the-packages-need.md`, findings 7 and 8,
all EXECUTED on 0.1.0a1:

- The plain reactor keeps `/usr/local/lib/python3.14`, a directory
  inside the **writable** root, on `sys.path`. A module planted there by
  one run is imported by the next run on the same root. That is code
  execution across runs in a shared root. The snapshot escapes it only
  by accident: its import cache was frozen with that directory absent.
- A planted `/usr/share/zoneinfo/...` or `/etc/mime.types` changes a
  later run's answers.
- `tempfile` falls back to `/` when there is no `/tmp`, so temporary
  files land beside the user's data.

Spec 001 documents the shared-root hazard and says: one root per
untrusted program. That is the right rule, but today it is advice in a
paragraph, not a default or a check. For the AI use case, where a
framework will reuse a scratch directory because it is convenient, the
default must make reuse safe or impossible, not merely discouraged.

**The runtime's own files.** The zip is protected per call by
re-placement, and the placement code is careful (copies, never links;
`O_NOFOLLOW`; rename over). But it is protection by repair: the guest
can still overwrite its own stdlib during its run (a program that
corrupts `python314.zip` after import changes its own later imports;
INFERRED). And the design has a known race the spec admits: a guest
running concurrently on the same root can swap a link between the
runner's check and its write. The owner's direction (runtime files
read-only, inside the binary) removes this whole class rather than
repairing it. That is the right instinct; section 4 says how.

**Determinism and replay.** The snapshot's bytes reproduce
(`2026-10-16-making-the-snapshot-byte-reproducible.md`, READ). A run
does not: the same `sum(range(10**6))` cost 1,016,087,417 and then
1,016,083,285 instructions in two calls; a pandas groupby 122,642,590
then 122,578,435 (EXECUTED). The variance comes from the real clock and
entropy the runner hands the guest. The judge's driver removes it by
answering `random_get` and `clock_time_get` itself (READ,
`tests/harness/guest.py:153-191`), so exact replay is a runner option
away, not research away.

**Supply chain.** Every input is pinned by URL and SHA-256 and verified
(READ, `downloads/SHA256SUMS`, v1.5 checks). Actions in the release
workflow are pinned by commit. The wheel is built in CI from the same
build. PyPI publishing is off until a trusted publisher is set up. What
is missing: no signature or provenance attestation on the release
assets (grep for `sigstore`, `attestation`, `cosign`: nothing); no
`SECURITY.md`; no rule for a security-triggered release (a CVE in a
pinned CPython, numpy or pandas has no stated path to a new set); the
Linux rebuild (the one known gap) is what would let a second party
confirm the bytes. The `.cwasm` cache is keyed by artifact digest and
wasmtime version and is never checked against the binary; the spec's
reasoning (anyone who can write a private cache already runs code as
that user) is sound.

**Claims that go beyond the evidence.** The README says the sandbox "is
WASI's capability model: the guest sees only the directories and host
functions you hand it". True for files and the door. It is silent on
the three resources that have no default (CPU, memory, output) and on
the shared-root hazard, which live in spec 001 and the memos. A reader
who installs the wheel and reads only the README will run untrusted
code with no limits. The README needs a "what it does not protect
against by default" paragraph until the defaults change.

## 3. Precedent

What the systems that sandbox untrusted code converged on, and where
this project sits against each (all READ from public design documents;
none executed here).

- **WASI's capability model.** Authority is a handle you were given, not
  a path you can name. The project is built on this and the imports
  check (`test_imports_are_wasi_and_the_door_only`) is the analogue of
  a seccomp allowlist: the only syscalls that exist are the 42 the
  binary imports. **Aligned.** One caution: preview1 cannot express
  read-only in the ABI; the rights bits a guest sees are the same for a
  read-only and a writable preopen (EXECUTED in the package-data memo).
  Read-only is a host-side property, enforced by wasmtime's cap-std
  layer, and the guest cannot check it. The project must never promise
  "the guest knows what it may write"; only "the host refuses".
- **Deno.** Default deny; each capability (`--allow-read=path`,
  `--allow-net=host`) is explicit, per resource, and separately typed
  for read and write. **Adopt** the shape: a grant is per path, named,
  and read or write, never a single writable root. Today `root` is one
  writable `/` holding everything.
- **Cloudflare Workers (V8 isolates).** No filesystem at all; CPU time
  and memory have defaults; and the clock does not advance during
  execution except at I/O, to blunt timing side channels after Spectre.
  **Adopt** two things: safe defaults for every limit, and a coarse or
  virtual clock as a runner option (the judge's driver already has one).
  The project is right not to copy the "no filesystem" rule: AI code
  writes CSVs and PNGs.
- **gVisor and Firecracker.** Defence in depth: the sandbox is one wall,
  the process around it is another (seccomp, no network namespace, a
  memory cgroup). The embedder owns that outer wall. The project should
  **document** it as the embedder's responsibility and keep its own
  wall small enough to audit (one import, one function; it is).
- **E2B, OpenAI's code interpreter, Anthropic's code execution tool.**
  A microVM or container per session, with: files in and out through an
  API, images (PNG) as first-class outputs, a timeout, stdout/stderr and
  a structured error, and state that persists across calls in a session.
  **Adopt** the result shape (section 5). Do **not** adopt the session:
  one instance per run is this project's strength (20 ms, soon 6 ms;
  nothing leaks between runs by construction). A framework that wants
  state can keep it in a granted directory.
- **Pyodide.** An in-memory filesystem by default; package data shipped
  with the package; matplotlib works with the fonts beside the code. The
  lesson the owner has already taken: the runtime's files travel with
  the runtime, and the host is touched only on request.
- **Browser site isolation.** One process per origin, because in-process
  isolation could not be made safe against speculative execution. The
  analogue here: one wasm instance per run (already), and, for an
  embedder with secrets in process, the advice to run wasmtime in a
  process of its own. Document; do not build.
- **seccomp.** An allowlist of syscalls, checked mechanically on every
  build. The imports check is that. **Aligned.**
- **WASI preview 2 and the component model.** Typed interfaces, and
  virtualisation (`wasi-virt`) that replaces the filesystem at the
  component boundary. The project rightly stays on preview1 (one target,
  the hosts that exist). It should keep its host contract small enough
  that a preview2 adapter is a mechanical wrapper later; 42 functions
  and one door is small enough.
- **Metered execution (EVM gas; Lambda SnapStart; CRIU).** A
  deterministic cost unit and a restored image. The project has both:
  fuel, and a Wizer snapshot. It has not yet sold either to its users;
  section 6 does.

Where the project is already ahead of most precedent: the zero-patch
rule, the pinned reproducible build, and a judge that hashes itself.
Where it is behind: no default limits, a writable root shared with the
runtime, and no signed release.

## 4. The filesystem design

The owner's three layers, quoted, each assessed.

### Layer 1: "The runtime's own files are read-only and ship inside the artifact"

**Right.** It removes the whole class of findings above (the vandalised
zip, the planted module, the concurrent-root race, the snapshot's
pairing with "the exact zip it was built against"). It also simplifies
the embedder contract to the thing the constitution promised: one file,
one function, one export. Two facts bear on it:

- **The snapshot already starts with zero preopens** (EXECUTED, through
  wasmtime-py with no `preopen_dir`): `-c "print('no data')"` printed
  and the program failed only when it touched the filesystem
  (`os.listdir('/')` → `EBADF`). Everything pre-imported is in memory;
  only a new import or a file read needs the zip. So "zero preopens is a
  valid run" is close for the snapshot once the zip is inside.
- **wasi-vfs sits between wasi-libc and WASI inside the guest** (READ,
  its README and the experiment's `relink.sh`). It defines the WASI
  import symbols, serves embedded paths itself and forwards the rest.
  Two things to verify before it is adopted, which the running
  experiment's `imports.py` is set up to show: the import list after
  linking is still exactly the 42 plus the door (the wall is unchanged
  by construction only if the forwarded imports are the same names), and
  the link order does not let `libwasi_vfs.a` supply `libm`, `memcpy`
  or the soft-float to the whole link (the experiment's `vfs-late`
  variant exists for this; a changed `memcpy` would change every
  golden's fuel and possibly numpy's results).

What I would change or add:

1. **Pick the fallback by the same rule as the main path: the runtime's
   files are never writable by the guest.** If wasi-vfs fails its
   experiment, C2 (a read-only preopen from the artifact set) is the
   fallback, and the stdlib zip should move there too, out of the
   writable root. Either way the writable root stops holding runtime
   files.
2. **Count the cost in the ratchet.** Fonts do not deflate; the zip is
   10.5 MB; a snapshot that embeds both grows by about 20 MB, and the
   `.cwasm` with it (the snapshot's is 105 MB today, READ spec 001). The
   bytes metric will grow and must be accepted with its cause. A
   build-time profile without matplotlib (constitution §2, "Beyond v1")
   is the answer for embedders who do not want the fonts.
3. **wasi-vfs is a third-party binary inside the wall.** It is Apache-2.0
   (READ), so licensing is fine, but it is Rust, and §4.2 wants every
   tool pinned and §4.8 wants downloads treated as untrusted. The
   experiment pins the prebuilt `.a` and CLI by SHA-256, which matches
   how wasi-sdk is used; building it from source would mean pinning a
   Rust toolchain. Prebuilt and pinned is acceptable; record the
   decision and the hash in `MANIFEST`.
4. **A record of what is embedded.** `MANIFEST` should list every
   embedded path and its hash, so an embedder (and the judge) can prove
   what the binary serves without unpacking it.

### Layer 2: "Package caches never reach the host by default"

**Right, and already mostly a runner default.** The data-folders memo
found every writable need is redirectable by an environment variable
(`TMPDIR`, `MPLCONFIGDIR`, `HOME`, `PYTHONTZPATH`, `MPL_IGNORE_SYSTEM_FONTS`;
EXECUTED there). So:

- The runner sets them by default to paths inside whatever writable
  grant exists, and to nothing when none does. A program that needs a
  temporary file with zero grants fails with a clear `OSError`; that is
  correct behaviour, not a bug.
- matplotlib's font cache is built at snapshot time inside Wizer (the
  matplotlib memo, 6.3, READ), so a figure costs no cache rebuild and
  no write. A check asserts there is no "created a temporary cache
  directory" warning.
- The one thing to add: a **writable scratch inside the guest with no
  host directory at all** would make "zero preopens" cover programs that
  use `tempfile`. wasi-vfs does not offer a writable filesystem (its
  README: "to be implemented more"). The honest answer today is that a
  writable scratch is a grant, and the Python runner can make and
  remove one in the OS temp directory on the embedder's behalf when
  asked (`scratch=True`). An in-memory writable overlay is a later
  research memo, not a promise.

### Layer 3: "User files come only from folders the embedder explicitly grants, and there may be none"

**Right.** Two refinements:

1. **Grants are typed.** `root=` becomes one of several `mounts`, each a
   host path, a guest path and `ro` or `rw`. wasmtime-py's
   `preopen_dir(..., fs_mutable=False)` enforces read-only at the host
   (EXECUTED in the package-data memo: every write and every escape was
   refused). The default is no mounts. The README's embedder contract
   says the same in WASI terms: "preopen what you grant; the runtime
   needs none".
2. **3b, "implement the WASI file calls itself on top of vfs-py", works
   in wasmtime-py** (EXECUTED here, once): with `Linker.allow_shadowing`
   an embedder-defined `path_open` replaced wasmtime's, and the guest saw
   `FileNotFoundError` for the path the shadow refused. So the owner's
   other project can back the filesystem without a host directory. It is
   the embedder's code and belongs there, not here (constitution §4.5).
   What this project owes it is a **conformance check**: a small guest
   program that exercises every file call CPython makes (open, read,
   write, stat, readdir, rename, unlink, seek, the `..` and link cases),
   runnable by any embedder against its own filesystem. The judge
   already has most of it in the v1.2 and v1.4 checks; it needs to be
   published as a job, not kept as a test. Also note: with wasi-vfs
   inside the guest, an embedder's shadowed call sees only the paths
   wasi-vfs forwards (INFERRED); the conformance job would show that.

### What the design does not yet say

- **Where the program's working directory is.** Today it is `/`, the
  writable root. With no grants there is no `/`. Decide: cwd is the
  first `rw` mount, else a read-only `/` that wasi-vfs serves.
- **The plain reactor and `sys.path`.** The writable directory on
  `sys.path` (finding 8) goes, whatever else happens: the bootstrap sets
  `sys.path` to the zip (and later the embedded tree) and nothing else.
  That is a recipe change, not a patch.
- **The two artifacts must behave alike.** The snapshot and the plain
  reactor differ on preopens (the package-data memo, finding 2) and on
  `sys.path` (finding 8). Every filesystem decision needs one check that
  runs on both, as the v1.4 checks already do with `which`.

## 5. Fit for the AI-code use case

What an AI-generated program needs, against what the API gives today
(READ, `runner.py`; EXECUTED where marked).

| need | today | gap |
|---|---|---|
| run a program, get stdout, stderr, exit | yes, one call | none |
| libraries | numpy, pandas, stdlib minus the listed modules | sqlite3, matplotlib, scipy (the planned order); `requests` is correctly impossible |
| files in | copy into `root` | typed `ro` grants; a `files={path: bytes}` convenience for the common case |
| files out (CSV, PNG) | read the root afterwards | `Completed.outputs`: the files the guest created or changed in `rw` grants, so a framework need not diff a directory |
| structured results | print JSON | fine; a documented convention beats a feature |
| an error an agent can act on | the native traceback on stderr (EXECUTED: the `json.loads` failure printed the stdlib frames and the exception) | add `Completed.error`: exception type, message, line of the user's code; and a stable reason for stops: `out of fuel`, `deadline`, `memory`, `output truncated` |
| timeouts | `fuel`, `deadline_s` | **defaults**; `fuel_used` after a deadline is `None` (wasmtime), so frameworks should prefer fuel |
| reproducibility | the snapshot; not the run | `deterministic=True` (section 6) |
| numpy binary file I/O | **broken**: `np.save`/`np.load` fail on `os.dup` (EXECUTED in the data-folders memo) | a known gap with the `BytesIO` workaround, and an upstream numpy issue; AI code uses `np.save` often |
| a CLI for non-Python frameworks | none; the README gives the three-step contract | a thin `wasi-python run` that prints a JSON `Completed` would let any agent framework call it by subprocess; **constitution** §3 says "no shell", so this is the owner's call (I would allow it: it is the runner, not a shell) |

**Defaults for the AI case.** A framework author should get a safe
sandbox from `run(code)` with no other argument: no mounts, a memory cap
(256 MiB is enough for the golden jobs; the fuel check for the
exception test used 560 MiB, so 512 MiB is a safer default), a fuel cap
in the tens of billions (a `-c pass` costs 118 M on the snapshot;
the pandas golden job 789 M: READ, the lean-exit memo), an output cap
with a truncation flag, and `TMPDIR`, `HOME`, `PYTHONTZPATH=` set. An
embedder that wants more asks for it. This inverts today's defaults
(everything unlimited, one writable root) and is the single change that
most serves the owner's stated users.

**Package scope.** The order in the constitution (matplotlib, then
sqlite/bz2/lzma, then scipy) is right by value and wrong by cost.
sqlite3, bz2 and lzma are C, need no C++ exceptions, and build on the
current line (the data-folders memo found no blocker beyond pins; READ).
matplotlib waits on spec 005 and then on five native libraries and a
font cache (weeks). AI-generated code asks for sqlite and plots about
equally. Do the cheap one first, in parallel with 005. That is a
reorder of §2's list: **constitution**, the owner's.

## 6. Innovation: what this project can do that others cannot

Ranked by value over cleverness.

1. **Deterministic replay as an audit record (high).** Fix the clock,
   the entropy and the environment (the judge's driver does it in forty
   lines), record the hashes of the artifact, argv, env, stdin, every
   granted file, and the door transcript, and a run becomes a pure
   function of its record: the same fuel, the same bytes, anywhere. An
   embedder can store the record instead of the output and re-run to
   prove what a program did, or replay a run an agent claims it made.
   No container sandbox can offer this; the microVM ones cannot even
   repeat a wall-clock. Cost: a runner option and one check.
2. **Fuel as the price of execution (high).** Fuel is the same number on
   every host for the same program (within the variance the clock
   causes, which item 1 removes). Bill by it, limit by it, compare
   agents by it. Already built; it needs a default and a sentence in the
   README. Also: `fuel_used` is a faithful "how much work did this
   program do" signal for an agent loop deciding whether to retry.
3. **Signed, attested releases (high, cheap).** The build is
   reproducible; add GitHub artifact attestations (SLSA provenance) and
   a signed `SHA256SUMS`, and the Linux rebuild as a second witness.
   Then an embedder can verify that the bytes it runs are the bytes the
   pins produce. A sandbox that cannot prove its own provenance is a
   weaker claim than it needs to be.
4. **A warm instance pool (medium-high).** wasmtime's pre-instantiation
   and pooling allocator make instantiation microseconds; with the lean
   exit (45 M instructions, about 6 ms: EXECUTED in its memo) a call is
   dominated by the program. For an agent framework running hundreds of
   small programs, that is the difference from a container. A runner
   feature; nothing in the guest changes.
5. **Embedder snapshots (medium).** Any embedder can Wizer the plain
   reactor with its own pre-imports and its own read-only data. The
   build does exactly this. Publishing the recipe as a documented step
   (not a tool) lets an embedder ship "my Python" as one file. It leans
   toward "general wasm toolchain" (§3), so document, do not build.
6. **Capability tokens through the door (medium, later).** The door is
   opaque, which is right. A non-binding convention memo (a frame is
   `{capability, operation, arguments}`; the host checks the capability
   it issued) would help embedders converge without naming one. Only
   after two embedders exist.
7. **Merely clever, not now:** forking a live instance mid-run (no
   runtime support), checkpoint and resume of a running program (the
   wasm stack is not in linear memory), copy-on-write of the snapshot's
   memory between instances (wasmtime already maps the image
   copy-on-write; nothing to build), a fuel market.

## 7. Engineering practice

**Working.** The constitution is short, checkable and obeyed; the
specifications decide rather than list questions; every landing has a
fresh-agent review on file (8 reviews for 5 specs, READ); the judge
hashes itself and refuses to lose a pass; the memos label their claims,
and the labels were honest everywhere I checked them against the code.
The zero-patch rule has held through a cross-compile of numpy and
pandas, which is rare. The red run during this box was the process
catching a concurrent agent, which is the process working.

**Overhead.** Every document in the repository is dated 2026-10-16 and
most say "amended the same day": the date-prefixed names will collide
and the history has no time depth; a sequence number in the slug would
help. The specifications restate decisions at length (001 is 300 lines
for a 490-line runner); the decisions sections are the durable part and
the rest could be shorter. Research memos are long because they are
thorough; that is fine for research, but the "What it decides" sections
are what a specification needs, and they are often buried.

**Missing.**

1. **A security goal in the judge.** v1.2 "portable and sealed" has
   three sealing checks. The threat model in section 2 lists about
   fifteen behaviours a hostile guest can try. Each becomes a check:
   climbing links, rename races, planted modules, the unbounded
   channels, door abuse (a frame of length 2³¹, a host that returns 2 GB,
   a pointer past memory), argument parsing with hostile `argv`.
2. **Fuzzing.** Two targets are small and worth it: the door
   (`hostmodule.c` and `_door` in the runner) and the bootstrap's
   argument parser. A property-based test with `hypothesis` in the unit
   suite covers both without a new tool.
3. **A security review per release**, by a fresh agent given the threat
   model and the diff, recorded under `reviews/` like any other; and a
   rule that a CVE in a pinned component starts a release
   (**constitution**, §5.5).
4. **`SECURITY.md`** with a disclosure address and the supported sets.
5. **The upstream test subsets** (README "Next", item 4) are the only
   semantic oracle beyond three golden jobs. They are the cheapest way to
   find the next `os.dup`.

## The direction

Ranked. Each item: why, what it unblocks, and how the judge would know
it is done. Items marked **constitution** need the owner's decision.

1. **Write the threat model into the judge: a `v1.6 hostile guest` goal
   (or widen v1.2).** Why: the product's claim is safety and it is
   judged by three checks. Unblocks: every item below becomes
   measurable. Done when: checks exist and pass for every row of the
   table in section 2 (links and `..`, planted module on both binaries,
   stdout and disk and memory caps, door abuse, hostile argv), each
   written before its fix so the first run shows the gap.
2. **Safe defaults and the writable `sys.path` gone.** Why: a framework
   author gets a safe sandbox from `run(code)`; the cross-run code
   execution hole closes. Unblocks: the README can claim what it does.
   Done when: `run(["-c", "..."])` with no other argument runs under a
   memory, fuel and output cap and no mounts; a module planted in
   `/usr/local/lib/python3XY` is not imported on either binary; `TMPDIR`,
   `HOME`, `PYTHONTZPATH` have runner defaults; the v1.4 checks for all
   of this pass. (`root` keeps working, with a deprecation, until item
   4.)
3. **Spec 005, as revised and reviewed.** Why: C++ exceptions are the
   prerequisite for matplotlib and for turning a C++ error into a Python
   exception. Done when: its five acceptance criteria hold.
4. **The runtime brings its own files; zero preopens is a run.** Why:
   layer 1; it removes the zip-repair class and the snapshot's pairing
   hazard. Decide wasi-vfs or C2 from the running experiment; whichever
   wins, runtime files are never in a writable grant. **Constitution:**
   §2.2 and §2.4 ("the one the embedder preopens" → "only the grants the
   embedder gives, which may be none"), §4.6 if the zip moves inside the
   binary or a data directory joins the set. Done when: the snapshot
   runs `import pandas; read a CSV from an ro grant; write the result to
   an rw grant` with no runtime preopen; the imports are still the 42
   plus the door; `MANIFEST` lists every embedded path and hash; the
   bytes growth is accepted with its cause.
5. **Typed grants and a result an agent can act on.** Why: layer 3 and
   section 5. `mounts` with `ro`/`rw`, `files=` in, `Completed.outputs`
   and `Completed.error` out, a stable stop reason, and the embedder
   conformance job published under `tests/jobs/`. Done when: a check
   writes through an `ro` mount and is refused; a check lists the
   outputs of a program that wrote a CSV and a PNG; the conformance job
   passes on the runner and on the judge's driver.
6. **Deterministic replay.** Why: section 6, item 1; cheap. Done when: a
   check runs the pandas golden job twice with `deterministic=True` and
   gets identical `fuel_used`, stdout and outputs, and a `Record` whose
   hash matches.
7. **Signed releases, `SECURITY.md`, a security-triggered release
   rule.** Why: section 2, supply chain. **Constitution:** §5.5 gains
   "a CVE in a pinned component is a reason to release"; §5.6 gains a
   security review per release. Done when: a rules check finds the
   attestation step in the workflow and `SECURITY.md` in the tree; the
   release's assets verify against their attestation on a clean machine.
8. **sqlite3, bz2, lzma on the current line.** Why: cheap, no C++,
   asked for by AI code as often as plots. **Constitution:** §2's order
   (cost before value). Done when: `import sqlite3` and a round-trip
   golden job match native, and the `-V` sentence shrinks its list.
9. **matplotlib headless to PNG**, after 3 and 4, on its existing
   specification research. Done when: a PNG golden job matches native
   on the same pins, and no cache warning appears on stderr.
10. **The lean exit and a warm pool in the runner.** Why: throughput for
    many small programs. Done when: the fuel metric of `-c pass` on the
    snapshot ratchets down from 117.7 M toward 45 M with every kept
    guarantee's check passing, and a runner check shows a second call
    does not re-instantiate from bytes.

Then the Linux rebuild (the known gap) and the upstream test subsets,
which are already on the README's list.

## Constitution changes proposed, collected

For the owner. None is made here.

- §2.2, §2.4: "the one directory the embedder preopens" becomes "only
  the grants the embedder gives, which may be none"; the embedder
  contract becomes "bind one function, call one export; preopen what
  you grant".
- §4.6: if the stdlib zip or package data moves inside the binary, the
  artifact set changes; `MANIFEST` lists embedded paths and hashes.
- §2 "Beyond v1": sqlite3, bz2, lzma before matplotlib, by cost.
- A new §4 constraint, **safe by default**: every limit has a default;
  no channel to the host is open without an explicit argument; the
  runtime's files are never in a writable grant. This is the owner's
  framing written as a rule the judge can hold.
- §5.5: a security fix in a pinned component is a reason to release.
- §5.6: a security review, against the written threat model, before
  each release.
- §3 "ships no shell": whether a thin `wasi-python run` CLI that prints
  a JSON result is the runner or a shell. I read it as the runner.

## One line

The wall is real and the build is exemplary; make the sandbox safe by
default, take the runtime's own files out of the guest's writable
reach, judge the hostile guest as carefully as the build is judged, and
then sell what only this project has: a run that replays exactly, costs
a known number of instructions, and comes from bytes anyone can
reproduce.
