# Roadmap

The owner's living plan: what each release contains and the order of work. It changes by the owner's decision, recorded here with its date; the constitution (`constitution.md`) holds the mission, the bar every release meets (§2) and the rules, and does not change with this file. Specifications and research memos carry the detail; this page only orders them. Work before 0.1.2 is the table at the end, one row per specification; each release's preparation pull request adds its specifications' rows.

The runtime is embedder-neutral (constitution §4.5): its consumers are not on this roadmap. A feature lands because it is general, whoever asked for it first.

## Released

**0.1.0**, tagged 2026-10-23, the first release to rely on: CPython 3.15 with its stdlib, numpy, pandas, scipy, matplotlib, scikit-learn, statsmodels, lxml, regex and about thirty pure-Python packages, each package's own tests run inside the sandbox; the agent runtime's features (tools over the host door, filesystem providers and writable mounts, sessions, `run_async` and cancellation); and its hardening (a security review of the whole surface, byte-identical rebuilds, the public API frozen). Seven alphas came before it, from 2026-10-17.

**0.1.1**, tagged 2026-10-27: the pin on wasmtime 50; the module cache read through the descriptor it was checked by; output read from a pipe on macOS and Linux; the platform module split in three; fixes at the door, in `poll_oneoff`, in `env=` and for a missing root's folders; and work merged into `dev` by pull requests that CI judges and accepts, with each release a pull request into `main`.

## Reserved, not yet scheduled

Reserved (the lane numbers it): the macOS exit tail (101's Decision 10 and the owner's choice 4): 3.5 to 5 minutes after pytest's summary line on every macOS shard that starts many guests, 0.01 minute on Linux and Windows, not shrunk by a split; it points at the process's exit on macOS (the runner's `atexit` handler dropping cached wasmtime engines and modules), not confirmed (101's landing notes, "The tail"); a runner change, so its own specification with its own pre-build review.

Noted (101's Decision 11 and the owner's choice 5): a release run is about 38 jobs wide on the plan's 40 (`max-parallel: 18` keeps it at 38 at most), so a second live run queues nearly whole; the rule of three live runs stays.

Reserved: 115, a closer for spec 108's two allowances (the eighteen private runner names the judge still patches, `SEAM_ALLOWED` in `tests/checks/test_rules.py`, each with the field or parameter its comment names; the seven functions over 80 lines, `LONG_FUNCTIONS`): parallel-safe, `src/` and the tests that patch, one specification or two; the 0.1.0 structural review's M1 names it as that Medium's reserved specification; after 0.1.0.

Reserved: 116 (the type checker's escapes: `type: ignore` in `src/` went from 12 to 25; a second mypy pass with `--platform win32` over `_platform_windows.py` once 131 splits the platform module (with `--follow-imports silent`, and the Linux pass excluding that file, as `specifications/131-the-platform-module-is-split.md` Decision 10 measured), so the Windows half is checked on every system, and a ratchet on the count of `type: ignore` that only falls); the 0.1.0 structural review's M2; parallel-safe, a judge change with the `src/` lines it clears; after 0.1.0.

Reserved: 141 (the access lists on the ancestors of the module cache are read: spec 135 judges each ancestor by owner and mode bits only and reads the access list of the cache folder and file alone, since a macOS home carries a `deny delete` entry for everyone and a presence test there would refuse every default cache; each entry of an ancestor's list is read through `acl_get_entry`, `acl_get_tag_type` and `acl_get_permset` on macOS and `system.posix_acl_access` on Linux, and an allow entry that lets another user write or delete in a folder on the way means the cache is not used, with a warning, never a refused call; defence in depth after 0.1.0, as question 112 answered; parallel-safe, runner code, stacks on 135; the source is `reviews/135-the-module-cache-is-read-through-the-descriptor-it-was-checked-by-spec-2026-10-25.md` finding L2).

143, built on `spec/143-a-path-open-on-a-special-file-is-refused`, awaiting its pull-request review (a `path_open` on a grant whose target is a FIFO, a socket or a device file is refused with `ENXIO`, or `ENOTDIR` under `O_DIRECTORY`, after a forwarded `path_filestat_get` on the open's own descriptor that follows links exactly as the open does, since a host's open of a FIFO waits in the kernel for its other end and the deadline, `cancel` and `Session.close()` stop wasm code alone; the rows assert the call returns with the refusal and `Session.close()` returns; runner code, parallel-safe; the 0.1.0 audit's deferred lead, carried as M1 of `reviews/0.1.1-security-review-2026-10-26.md`, which gave it this number).

Not reserved, the owner's: release authority (both rulesets give the admin role `bypass_mode: always`, no required reviewer on the `release` and `pypi` environments, the tag-on-main check in the tagged commit's own workflow file) and the PyPI trusted publisher's environment binding (confirm on pypi.org that the publisher names `release.yml` and environment `pypi`); the deferred units' lead (the owner reads `reviews/0.1.0-security-audit-2026-10-25/agents/h07-sessions-limits/artifacts/evidence/` and `…/h13-sessions-limits/artifacts/evidence/` first).

Reserved: 142 (the 80-line allowance judged by length as well as name: today a listed function may grow without limit, and `run`, `run_async` and `Session.__init__` are past their listed lengths, 156, 181 and 178 against 151, 176 and 173 at 0.1.1; the list reset to today's lengths, and any function past its listed length reported; the judge alone, parallel-safe; from the 0.1.0 structural review's M-a, `reviews/0.1.0-structural-review-2026-10-21.md`, carried as the one Medium of `reviews/0.1.1-structural-review-2026-10-26.md`, which gave it this number). The second item of that delta read, `_platform.py` split before it passes its ceiling (M-b), landed as 131.

Reserved after 0.1.0, from 0.1.0's second dry run (39764234616, red on joblib-r on ubuntu-24.04; the lane's fix `42798898`, reviewed in `reviews/lane-joblib-listing-order-2026-10-22.md`): the guest lists a folder in the host file system's order (APFS keeps one; ext4's differs between machines), so an upstream test that walks a folder unsorted can meet its cases in another order on another host. Not a product defect (WASI promises no order, and native CPython lists the same way), but the judge should find such a test before a dry run does: a repository check, or a release group run once with a reversed listing. And the review's Low 1: joblib-r's no-mmap reason, here and in its gap, names this test's case (today only the TOML comment does).

Reserved: a cache's path judged one component at a time (113's build review, confirmation, L5: a link whose target climbs through a second link in another folder, `a/link -> ../m/n/..` with `m/n -> x/y`, passes a writable grant at `m`, since the chain holds the folders on the path as written and those holding a link on it, not those met inside a link's target; the lane's decision, 2026-10-21: documented in the README's Safety bullet now, fixed after 0.1.0): resolve the path one component at a time, following each link's target the same way, and judge every folder that holds a link met on the way; a row for this case, seen failing first; runner code, parallel-safe; after 0.1.0; the number is the lane's when it is drafted.

Reserved: the artifact set judged by its path as written (113's Decision 1 and its confirmation read's L8: the set comes from `artifacts=` or `$WASI_PYTHON_ARTIFACTS` and is checked only against its own `SHA256SUMS`, so a link on its path inside a writable grant could let a guest swap a later call's interpreter; that is wasm under the wall, not native code, so it waits; the rule is 113's for the caches, every existing prefix of the path as written in the chain); runner code, parallel-safe; after 0.1.0; the number is the lane's when it is drafted.

Reserved: a protected access list for the module cache on Windows (113's Decision 4: the runner sets an access list of its own, not inherited, on the cache folder and each `.cwasm` it writes, and loads only a file that carries it, the Windows counterpart of POSIX's 0700 and 0600, so a file a guest wrote through a grant is told apart from the runner's; `advapi32` through ctypes, past what `_platform.py` holds under its ceiling, so likely structural); runner code; after 0.1.0, since 113's rule is the fix and this is defence in depth; the number is the lane's when it is drafted.

Reserved: the judge's two staging follow-ups spec 066 named (`test_elementsoup.py` under pytest's import mode; the `stage-layout` class), split from 097, which built the host-litter half only; that specification rewrites `tests/upstream/matplotlib.toml`'s `stage-layout` reason, which still names 097 (wave 09's integration review, L3); parallel-safe, a judge change; the number is the lane's when it is drafted.

Reserved: a closer for spec 109's leftovers (code speaks for itself, the leftovers: the 78 citing string literals outside `src/`, held by one regex over string tokens for `spec NNN`; the judge's allowance files' comments; the guest's own sources, their fuel re-measured; whether a message a user reads falls under the rule is the owner's to say); it also rewords the 487 lines of `tests/known_gaps.toml` and `tests/upstream/*.toml` whose reasons still say "README" (their closers already name the limitations page) and the 26 lines of `tests/checks/` docstrings and comments that point at a README section, in the one judge change and the one release-tier ledger block: parallel-safe, the judge and the guest's inputs; the number is the lane's when it is drafted (109's build review, finding 2; the integration review's finding 3).

Reserved after 0.1.0 (the lane numbers it): a check that the empty HOME 114 makes is removed without `root=True`: `run(["-c", "pass"])` first, then `tempfile.tempdir` redirected to a scratch folder, a call with a read-only grant at `/tmp` and a session opened and closed, and the folder empty with nothing from `_private_dirs._flush_warnings`, on every system; today a regression in the release order on Windows shows only as a `RuntimeWarning` (114's build review, L4). Parallel-safe, a judge change.

Reserved: 088, the judge-only binary (questions 89 and 101): a build never published, linked with numpy's C test modules and built with CPython's (`--enable-test-modules`), on which the judge runs the tests that need them. Build-class; after the packages.

Reserved: 074 (what CPython's suite asks of the product; spec 065's follow-up A, build-class; before 0.1.0, since it closes classes in the gate the owner set): `sys.executable` empty; `_reset_cache` in the `ctypes` stand-in, so the judge's driver drops it; and whether the `ctypes` and `mmap` stand-ins name what CPython's tests name at import (`pythonapi`, `py_object`, `Array`, `mmap.error`, `ACCESS_DEFAULT`).

Follow-ups from spec 068's pre-build review (2026-10-18): **spec 072, a bound on path depth** (not drafted): a limit on the components of every path a path call resolves, so the descriptors wasmtime holds while it walks a deep path on macOS (and Linux without `openat2`) are bounded too, which 068's cap does not count (question 100 tells the owner); and **a cheaper forward** for the runner's shadows (about 26 µs per shadowed call), which after spec 069 every default call that imports from the zip pays, through 068's counted `path_open` and `fd_close`.

Reserved (carried by the next build-class specification that edits a file under `scripts/`): `scripts/assemble_artifacts.py`'s two `F402` (the loop variable `line` at `:587` and `:601`, which shadows the imported module `line`, renamed `text`) and its format, and `scripts/make_stdlib_zip.py`'s `E501` and `I001`; both leave `[tool.ruff] extend-exclude`, so ruff reads every build script; build-class, since `MANIFEST` hashes each tracked file under `scripts/` as a `recipe` line and `SHA256SUMS` hashes `MANIFEST`, so the change rides a run that compares the three artifacts anyway.

## 0.1.2: the embedder's release

Decided by the owner on 2026-10-27, from the two memos an embedder's session wrote against 0.1.1 (`research/2026-10-27-a-snapshot-the-embedder-chooses.md`, `research/2026-10-27-the-module-cache-refused-where-another-uid-owns-the-root.md`), the production-use review (`research/2026-10-27-a-code-review-of-the-runner-for-production-use.md`), the 0.1.1 security and structural reviews, and the follow-ups the 0.1.1 landing notes record. The owner approved the scope whole, asked for the deferred items to be pulled in where they can be, and delegated the push of `main` and the tag for 0.1.2 to the orchestrating agent (`decisions.md`, 2026-10-27). The version stays 0.1.2. Every specification below is built by a pull request into `dev` under the nine steps of `AGENTS.md`; the ones that change a security check, what the guest sees or the public API are reviewed before they are built.

**The headline.** Reserved: 150 (a starting image the embedder chooses: an embedder names a prelude of imports, wasi-python makes an image from it once, and every `run` or `Session` given it starts as a fresh instance from that image, so a program that spends 90 to 99 percent of its instructions importing packages pays them once; a time-boxed research spike first, in a worktree of its own, measures the per-call cost of restoring a 150 to 300 MiB image through wasmtime-py's public API, whether the module's non-exported globals and the runner's host-side state are back at their base between calls, and which of the stack's packages seed randomness or do host work at import; then the specification, **structural**, a new public argument and a new lifecycle, reviewed before it is built under constitution §5.6; `fuel_used` counts the call's own work alone and the docs say so; the owner, 2026-10-27: a snapshot is any code the embedder runs and saves, not only imports, and a helper makes the snapshot that imports every package the set ships, so a developer never types the list; the shape is designed for the developer's experience first; a snapshot can be kept in the process that made it and saved to disk to be loaded by another process, both supported (the owner, 2026-10-27); the prelude is the embedder's own code, and a checkpoint of a guest's run is out of 0.1.2).

Reserved: 157 (the reactor prepares a starting image: the snapshot binary gains one export, `prepare`, that runs the embedder's code in a fresh instance with the clocks and entropy pinned, then leaves its memory ready to be copied into each later instance, with the preopen table cleared, the code's names kept for every program and the heap frozen; a call from such an image ends at the cost of its own work; the per-call refresh reseeds `tempfile`'s names and sympy's generators too; MANIFEST names the modules that import every package the set ships; build-class, a new export of both binaries and new artifact bytes, reviewed before it is built under constitution §5.6; 150 stacks on it).

**The embedder's blocker.** Reserved: 147 (the module cache on a host where another uid owns `/`: on Cloudflare Containers `/` belongs to uid 2346, so `_way` refuses every cache folder and each start compiles for about five minutes; the owner of `/` is trusted as root is, since whoever owns `/` can already replace any path below it, the mode rule stays, and when `/` itself is what fails the warning no longer points at another folder; a change to a security check, reviewed before it is built; it carries what else was deferred on that code: the owner test by the effective uid in `_way` and `_as_made` through `_this_users` (the 0.1.1 security review's L3, 139's follow-up), 135's three Lows (the swap row rewritten, `held` without a default, `_way` once more after the `mkdir` loop) and `$WASI_PYTHON_CACHE` read once (the 0.1.1 structural review's L5)).

**The carried findings, already numbered.** 143 (a `path_open` on a FIFO, a socket or a device is refused with `ENXIO`; the 0.1.1 security review's one Medium; it changes what the guest sees, so it is reviewed before it is built), 142 (the 80-line allowance judged by length; the 0.1.1 structural review's one Medium; the judge alone), 141 (the access lists on the cache's ancestors; stacks on 147), 115 (the seam allowances closed) and 116 (the type checker's escapes: a Windows mypy pass and a ratchet on `type: ignore`): each as its reserved line above says.

**From the production-use review.** 144 (a session is always ended), 145 (a mount's names work the same on every host) and 146 (the tool host's bounds are the process's), drafted 2026-10-27 and approved to build with this scope.

**Two bundles of Lows.** Reserved: 148 (the release path's Lows from `reviews/0.1.1-security-review-2026-10-26.md`: `.claude/` and `AGENTS.md` leave the plan's documentation row (L2), GitHub's `skip-checks: true` trailer is refused beside the skip words (DL1), a path git quotes is read right (L4), `edited` joins the pull request's trigger types (L5), the release token is set on `gh release create` alone and `uv publish --trusted-publishing always` replaces the container named by tag (L6, 0.1.0's L5a and L5b), `SECURITY.md` names the advisory batch of 2026-10-19 and the install page's umask sentence is corrected (L6), and the reviews README tells every reviewer to read a change under `.github/` and `release/` as code (L1); build-class, a change to the release workflow, reviewed before it is built). Reserved: 149 (the runner's structure Lows from `reviews/0.1.1-structural-review-2026-10-26.md`: the platform object's resolve-once tables filled under a lock, since a concurrent first use can raise `KeyError` out of `run()` on macOS (L1); the poll shadow's stop recorded through a `_Files` method (L2); the three `_platform_common` names re-exported through `_platform` and a rule check that only the platform modules import its halves (L3); the two judge-only branches removed (L4); 129's Lows 9 and 10 (the slow loop's fall reported, `dropped` set only where a piece is lost); and the flaky unit row `test_a_late_gate_skips_an_async_tool`, which failed two runs once each and passed on re-run, made deterministic; runner code, not structural).

**The release's words.** Reserved: 152 (release notes that say what a release gives the reader: today a release's notes are the CHANGELOG section, one dense paragraph per specification written for the agent that built it; from 0.1.2 a release's notes open with what the release gives an embedder in a few sentences, group the changes by what they do for the reader (new, faster, safer, fixed) with one short paragraph each that says the value first and links the page that explains it, and keep the specification-level detail in the landing notes where it lives; the news file's shape in `changes/README.md` gains the reader's paragraph beside the CHANGELOG line, `release/version.py bump` and `notes` render both, and the shape check holds it; the owner, 2026-10-27: "they should be like release notes that explain the value to the reader, right now ours are just a blob of text").

**Housekeeping.** The 0.1.1 landing notes and the three memos land first as a documentation pull request. 127's ledger block is removed by a one-line pull request once this scope lands, unless 154 lands first and takes it. Reserved: 151 (the documentation's and the knowledge tree's hygiene, the follow-ups reserved for 0.1.1 that slipped: the six stale README pointers in `src/` (`__init__.py`, `tools.py`, `runner.py`, `_artifacts.py`, `_tool_schema.py`), the known gaps' and suites' reasons that still say "README", the command's remaining `help=` strings so `tests/harness/cli_doc.py`'s `DESCRIBED` empties, `SECURITY.md` read by the public-page scans, `mkdocs.yml`'s first comment, this roadmap trimmed with 117 to 121 retired as superseded by 138 and the landed specifications' lines folded into one table, landed specifications archived with their reviews and the scans taught the archive path, and `tool.ruff.src` extended to `scripts` and `release` with the two `F402` renamed, as the production-use review's §6 asks).

**Stretch, in this order, each only if the release is not waiting on it.** Reserved: 153 (a guest's output read from a pipe on Windows too, where 129 kept the callback; it needs a Windows host, so the pull request's Windows legs are its only evidence). Reserved: 154 (the acceptance takes Linux's measurement as the first fuel under a new engine, so an engine move no longer leaves every Linux-only upstream row without fuel until a Mac runs the release tier; it removes 127's ledger block). Reserved: 155 (the tag's run promotes the release pull request's attested assets instead of rebuilding, as Wasmtime publishes what CI built; 138's landing notes name it). Reserved: 156 (the judge finds an upstream test that walks a folder unsorted before a dry run does, the listing-order check reserved after 0.1.0).

**Out of 0.1.2.** A Rust core (the 2026-10-23 memo's "adopt in part" stands, and nothing in it is urgent); build-time profiles beyond the default; the cancellation of an abandoned tool thread; the duplication of `_instance` and `_open_session` (a structural specification of its own, after 142 gives the judge its length rule); a benchmark memo of many sessions at once (research first, as the production-use review's §6 says).

**The release.** Once the above has landed, a fresh agent writes the structural review and another the security review, the preparation pull request carries them with `bump --to 0.1.2` and `date`, the release pull request from `dev` to `main` runs the whole workflow, and the orchestrating agent fast-forwards `main` and tags, as delegated.

## After 0.1.0

The documentation's follow-ups still open (specs 122 and 123; the owner, 2026-10-22): the quickstart and how-to snippets as files under `docs/examples/`, run as a slow-tier guest job; versioned docs; the included-packages table generated from `MANIFEST` and `tests/upstream/packages.toml`; a scheduled external link check, upstream download hosts excluded; and `recipes/numpy_lapack_shims.c:13`'s pointer to its generator in the evidence folder `research/2026-10-20-numpy-on-openblas/`, which went with the evidence folders' deletion (the generator stays in git history at `bb2235f2`; a build-class change).

Left out of 0.1.0's default profile: pytz (decision 47); Rust packages, pyarrow, polars, duckdb, plotly (later, or a profile); network libraries.

Build-time profiles beyond the default (constitution §2's principle; `research/2026-10-16-build-time-profiles-of-the-core-c-libraries.md`).

## Retired

Retired: 126 (native unwind information is left out: superseded in substance by 127, under which the module drop measures 22 ms with the information on, and dropped by the owner on 2026-10-25 (`decisions.md`, "Spec 126 is dropped"); what remained, about 10 MB off every cached `.cwasm` and a drop of 2 to 12 ms instead of 22, stays a benchmark fact in `research/2026-10-24-native-unwind-information-and-the-module-drop.md`; `specifications/126-native-unwind-information-is-left-out.md` is kept as the record).

Retired: 117 (red means broken), 118 (one news file per specification), 119 (branch runs pick shards by their paths), 120 (a light branch run and the full run once at the wave) and 121 (the pre-tag dry run beside the release acceptance), the process advice's five (`research/2026-10-22-process-advice.md`): superseded by 138, which supersedes 117, 119, 120 and 121 and absorbs 118 as its Decisions 3, 2, 4 and 7 (138's Depends on line); none will be written. The advice's later items, each the owner's call, are in the memo.

## Specifications before 0.1.2

| spec | title | released in |
|---|---|---|
| [001](specifications/001-the-neutral-host-door-and-the-runner.md) | The neutral host door and the runner | — |
| [002](specifications/002-the-progress-harness.md) | The progress harness | — |
| [003](specifications/003-the-pinned-build-end-to-end.md) | The pinned build, end to end, with the neutral door | — |
| [004](specifications/004-alpha-releases.md) | Alpha releases: the version, the tag and the release workflow | — |
| [005](specifications/005-the-3-15-line.md) | The CPython 3.15 + wasi-sdk 33 line | — |
| [006](specifications/006-safe-by-default.md) | Safe by default: the hostile guest, judged | — |
| [007](specifications/007-sqlite3-bz2-and-lzma.md) | sqlite3, bz2 and lzma, built in | — |
| [008](specifications/008-fuel-counts-the-guest-and-runs-replay.md) | Fuel counts the guest only | — |
| [009](specifications/009-release-security.md) | Release provenance: every asset attested and verified | — |
| [010](specifications/010-a-sleeping-guest-keeps-its-deadline.md) | A sleeping guest keeps its deadline | — |
| [011](specifications/011-concurrent-calls-share-nothing.md) | Concurrent calls share nothing | — |
| [012](specifications/012-the-same-bytes-from-any-host.md) | The same bytes from any host | — |
| [013](specifications/013-the-limits-are-checked.md) | The limits are checked | — |
| [014](specifications/014-the-inputs-are-checked.md) | The inputs are checked | — |
| [015](specifications/015-run-from-async-code.md) | Run from async code | — |
| [016](specifications/016-the-security-reviews-leftovers.md) | The security review's leftovers | — |
| [017](specifications/017-typed-grants.md) | Typed grants | 0.1.0a6 |
| [018](specifications/018-finder-litter-never-breaks-a-build.md) | Finder litter never breaks a build | — |
| [019](specifications/019-the-command-line.md) | The command line | — |
| [020](specifications/020-carried-patches.md) | Carried patches | — |
| [021](specifications/021-npy-files-on-wasi.md) | `.npy` files on WASI: the first carried patch | — |
| [022](specifications/022-grants-on-the-command-line.md) | Grants on the command line | — |
| [023](specifications/023-matplotlib-first-milestone.md) | matplotlib, the first milestone | 0.1.0a6 |
| [024](specifications/024-a-root-prepared-through-its-walk.md) | A root prepared through its walk | — |
| [025](specifications/025-nothing-writable-by-default.md) | Nothing writable by default | 0.1.0a3 |
| [026](specifications/026-finder-litter-in-the-judges-extraction.md) | Finder litter in the judge's own extraction | — |
| [027](specifications/027-the-build-says-where-it-is.md) | The build says where it is | 0.1.0a4 |
| [028](specifications/028-pip-install-wasi-python.md) | `pip install wasi-python` runs programs | 0.1.0a4 |
| [029](specifications/029-the-landing-lane-is-guarded.md) | The landing lane is guarded | — |
| [030](specifications/030-a-cancel-in-the-door-is-named.md) | A cancel during a door call is named "cancelled" | 0.1.0a4 |
| [031](specifications/031-a-tool-protocol-over-the-door.md) | A tool protocol over the door | 0.1.0a4 |
| [032](specifications/032-a-filesystem-provider.md) | A filesystem provider (read-only mounts) | 0.1.0a4 |
| [033](specifications/033-the-zip-carries-what-packages-need.md) | The zip carries what packages need | 0.1.0a4 |
| [034](specifications/034-writable-mounts.md) | Writable mounts | 0.1.0a4 |
| [035](specifications/035-the-zips-directory-is-read-once.md) | The zip's directory is read once | 0.1.0a4 |
| [036](specifications/036-tools-in-the-runner.md) | Tools in the runner | 0.1.0a4 |
| [037](specifications/037-scipy.md) | scipy, the first milestone | 0.1.0 |
| [038](specifications/038-scipy-second-milestone.md) | scipy, the second milestone: the sandbox's edges | 0.1.0 |
| [039](specifications/039-tier-a-packages.md) | Tier A: the pure-Python packages | 0.1.0 |
| [040](specifications/040-x86-64-rebuilds-the-same-bytes.md) | x86_64 rebuilds the same bytes | 0.1.0a4 |
| [041](specifications/041-files-read-by-path-from-the-zip.md) | Files read by path from the zip | 0.1.0 |
| [042](specifications/042-seaborn-and-reportlab.md) | seaborn and reportlab | 0.1.0 |
| [043](specifications/043-matplotlib-second-milestone.md) | matplotlib, the second milestone: triangles, contours, SVG and PDF | 0.1.0 |
| [044](specifications/044-scikit-learn.md) | scikit-learn | 0.1.0 |
| [045](specifications/045-statsmodels.md) | statsmodels, with formulaic, interface-meta and wrapt | 0.1.0 |
| [046](specifications/046-lxml.md) | lxml, with libxml2 and libxslt built in | 0.1.0a7 |
| [047](specifications/047-regex.md) | regex, built in | 0.1.0a7 |
| [048](specifications/048-the-sandbox-holds-on-wasmtime-49-0-0.md) | The sandbox holds on wasmtime 49.0.0 | 0.1.0a4 |
| [049](specifications/049-the-public-api-is-frozen.md) | The public API is frozen and documented | 0.1.0a5 |
| [050](specifications/050-numpy-and-pandas-own-tests-under-the-runtime.md) | numpy's and pandas' own tests under the runtime | 0.1.0a4 |
| [051](specifications/051-what-the-upstream-tests-found.md) | What the upstream tests found | 0.1.0a4 |
| [052](specifications/052-the-judge-on-several-cores.md) | The judge on several cores | 0.1.0a6 |
| [053](specifications/053-async-host-functions.md) | Async host functions | 0.1.0a6 |
| [054](specifications/054-read-only-code-on-the-import-path.md) | Read-only code on the import path | 0.1.0a5 |
| [055](specifications/055-bounded-sessions.md) | Bounded sessions | 0.1.0a7 |
| [056](specifications/056-the-a4-security-reviews-findings.md) | The 0.1.0a4 security review's findings | 0.1.0a4 |
| [057](specifications/057-the-release-ties-what-it-signs-to-what-it-built.md) | The release ties what it signs to what it built | 0.1.0a6 |
| [058](specifications/058-windows-renames-a-folder-over-a-file.md) | A Windows grant renames a folder over a file | 0.1.0a4 |
| [059](specifications/059-the-x86-64-rebuild-runs-natively.md) | The x86_64 rebuild runs natively | 0.1.0a6 |
| [060](specifications/060-a-per-run-budget-of-request-bytes.md) | A per-run budget of request bytes | 0.1.0a6 |
| [061](specifications/061-a-providers-oserror-carries-its-errno.md) | A provider's OSError carries its errno | 0.1.0a6 |
| [062](specifications/062-the-progress-history-stays-small.md) | The progress history stays small | — |
| [063](specifications/063-the-release-judges-in-parallel-shards.md) | The release judges in parallel shards | 0.1.0a7 |
| [065](specifications/065-cpythons-own-tests-in-the-release.md) | CPython's own tests in the release | 0.1.0 |
| [066](specifications/066-the-compiled-packages-own-tests.md) | the compiled packages' own tests in the release | 0.1.0 |
| [067](specifications/067-the-pure-python-packages-own-tests.md) | the pure-Python packages' own tests in the release | 0.1.0 |
| [068](specifications/068-a-cap-on-open-files.md) | A cap on files open at once | 0.1.0a7 |
| [069](specifications/069-the-snapshot-pre-imports-no-package.md) | The snapshot pre-imports no package | 0.1.0a7 |
| [070](specifications/070-the-judges-small-follow-ups.md) | The judge's small follow-ups | 0.1.0a7 |
| [071](specifications/071-deep-recursion-raises-recursionerror.md) | Deep recursion raises RecursionError instead of trapping the guest | 0.1.0a7 |
| [073](specifications/073-run-keeps-an-unclosed-files-bytes.md) | `run` keeps an unclosed file's buffered bytes | 0.1.0a7 |
| [075](specifications/075-tools-small-fixes.md) | tools.py small fixes | 0.1.0a7 |
| [076](specifications/076-the-grant-checks-agree-on-windows.md) | The grant checks agree on Windows | 0.1.0a7 |
| [077](specifications/077-the-grant-follow-ups.md) | The grant follow-ups | 0.1.0a7 |
| [078](specifications/078-the-runner-runs-each-guest-on-a-stack-of-its-own.md) | The runner runs each guest on a stack of its own | 0.1.0 |
| [079](specifications/079-the-build-runs-only-the-pinned-host-python.md) | The build runs only the pinned host Python | 0.1.0a7 |
| [080](specifications/080-deterministic-recursion-fuel.md) | 071's recursion checks count deterministic fuel, and its guard's unit tests stand alone | 0.1.0 |
| [081](specifications/081-guest-fuel-does-not-depend-on-the-checkout.md) | guest fuel does not depend on where the repository is checked out | — |
| [082](specifications/082-inline-sessions-keep-the-handlers.md) | Inline pytest sessions keep wasmtime's signal handlers | 0.1.0 |
| [083](specifications/083-the-driver-answers-file-timestamps.md) | the judge's driver answers a file's times and inode number itself | 0.1.0 |
| [084](specifications/084-a-private-root-never-outlives-its-call.md) | A private root never outlives its call | 0.1.0 |
| [085](specifications/085-gather-checks-what-it-trusts.md) | `gather` checks what it trusts | 0.1.0 |
| [086](specifications/086-the-toolchain-moves-to-wasi-sdk-34.md) | The toolchain moves to wasi-sdk 34 | 0.1.0 |
| [087](specifications/087-the-a7-reviews-guest-follow-ups.md) | the 0.1.0a7 review's guest follow-ups | 0.1.0 |
| [089](specifications/089-host-litter-never-reaches-a-verdict.md) | host litter never reaches a verdict: the judge seals its stages and watches its grants | — |
| [090](specifications/090-the-build-ignores-host-litter.md) | the build and its artifact checks agree on one litter list | 0.1.0 |
| [091](specifications/091-numpy-core-layout-fuel-as-a-fact.md) | numpy-core's layout-dependent fuel as a fact | — |
| [092](specifications/092-the-judge-reads-a-release-record.md) | the judge reads a release record: sameness against a CI run, and claim lists | 0.1.0 |
| [093](specifications/093-an-abandoned-turn-on-windows.md) | An abandoned turn on Windows | 0.1.0 |
| [094](specifications/094-the-removal-rows-name-their-windows-need.md) | The removal rows name their Windows need | 0.1.0 |
| [095](specifications/095-scipy-sklearn-statsmodels-own-tests.md) | scipy's, scikit-learn's and statsmodels' own tests in the release | 0.1.0 |
| [096](specifications/096-kiwisolver-clear-and-lxml-final.md) | kiwisolver's `tp_clear` returns `int`, `lxml.html.diff` imports, and the scan reads type slots | 0.1.0 |
| [097](specifications/097-host-litter-outside-home.md) | host litter outside the home folder: the judge's guest folders leave HOME on macOS, and the OpenBLAS script never reads litter | 0.1.0 |
| [099](specifications/099-numpy-singular-inverse.md) | numpy's own floating-point signals are kept in software, so a singular matrix raises `LinAlgError` | 0.1.0 |
| [100](specifications/100-numpy-on-openblas.md) | numpy's linear algebra, `dot` and `matmul` run on the set's OpenBLAS | 0.1.0 |
| [101](specifications/101-faster-release-run.md) | a faster release run: reuse a proven set on branches, and macOS shards that finish together | 0.1.0 |
| [102](specifications/102-the-release-tier.md) | the release tier: slow tests run before a publication, never left out | 0.1.0 |
| [103](specifications/103-the-engine-seam.md) | The engine seam: one module touches wasmtime-py's private API | 0.1.0 |
| [104](specifications/104-the-runner-becomes-a-package.md) | The runner becomes a package: one module per concern | 0.1.0 |
| [105](specifications/105-one-owner-for-the-process-state.md) | One owner for the process's state, and the test seams move off module globals | 0.1.0 |
| [106](specifications/106-typed-call-state-and-explicit-lifecycles.md) | Typed call state, explicit lifecycles, and a type checker in the judge | 0.1.0 |
| [107](specifications/107-mounts-behind-a-protocol-and-one-platform-module.md) | `mounts.py` behind a call-context protocol, one platform module, one stamp, and the source explains itself | 0.1.0 |
| [108](specifications/108-a-structural-review-is-a-stage.md) | A structural review is a stage | 0.1.0 |
| [109](specifications/109-code-speaks-for-itself.md) | Code speaks for itself: no document cited in a comment outside `src/` | 0.1.0 |
| [110](specifications/110-tools-behind-its-facade.md) | `tools.py` behind its public facade | 0.1.0 |
| [111](specifications/111-the-filesystem-along-the-wasi-seams.md) | the filesystem along the WASI seams | 0.1.0 |
| [112](specifications/112-strings-speak-for-themselves.md) | Strings speak for themselves: no document cited in a string literal | 0.1.0 |
| [113](specifications/113-every-module-cache-is-guarded.md) | every module cache is guarded | 0.1.0 |
| [114](specifications/114-home-is-never-the-root.md) | HOME is never the root | 0.1.0 |
| [122](specifications/122-a-short-readme-and-a-clean-tree.md) | A short README and a clean tree | 0.1.0 |
| [123](specifications/123-the-documentation-site.md) | The documentation site | 0.1.0 |
| [124](specifications/124-a-coverage-badge-from-ci.md) | A coverage badge from CI | 0.1.0 |
| [125](specifications/125-the-wheel-licence-carries-every-component.md) | The wheel's LICENSE carries every component licence | 0.1.0 |
| [127](specifications/127-the-pin-moves-to-wasmtime-50.md) | The pin moves to wasmtime 50 | 0.1.1 |
| [128](specifications/128-concurrent-runs-do-not-wait-on-each-other.md) | Concurrent runs wait less on each other: the data comparison by scandir | 0.1.1 |
| [129](specifications/129-output-is-read-from-a-pipe.md) | Output is read from a pipe | 0.1.1 |
| [131](specifications/131-the-platform-module-is-split.md) | The platform module is split | 0.1.1 |
| [132](specifications/132-an-env-key-that-loads-code-is-refused.md) | an `env=` key that loads code is refused | 0.1.1 |
| [133](specifications/133-a-class-tools-construction-path-is-read-for-bound-keywords.md) | a class tool's construction path is read for bound keywords | 0.1.1 |
| [134](specifications/134-fuel-counts-the-work-a-caught-exception-ends.md) | fuel counts the work a caught exception ends | 0.1.1 |
| [135](specifications/135-the-module-cache-is-read-through-the-descriptor-it-was-checked-by.md) | the module cache is read through the descriptor it was checked by | 0.1.1 |
| [136](specifications/136-the-build-reads-its-pins-by-exact-name-and-the-release-checks-every-inner-file.md) | the build reads its pins by exact name, and the release checks every inner file | 0.1.1 |
| [137](specifications/137-the-door-answers-exact-bytes.md) | The door answers exact bytes | 0.1.1 |
| [138](specifications/138-pull-requests-into-dev-and-the-judge-runs-where-it-is-needed.md) | pull requests into `dev`, and the judge runs where it is needed | 0.1.1 |
| [139](specifications/139-the-runners-folders-are-this-users-and-the-data-guard-refuses-windows-names.md) | The runner's folders are this user's, and the data guard refuses Windows's names | 0.1.1 |
| [140](specifications/140-the-poll-shadow-answers-as-wasmtime-does.md) | The poll shadow answers as wasmtime does | 0.1.1 |
