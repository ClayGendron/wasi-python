# Review of 147 — The module cache on a host where another uid owns the root

- **Date:** 2026-10-28
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** pull request #32, `git diff origin/dev...bf0c0b1e` on `spec/147-the-module-cache-on-a-host-where-another-uid-owns-the-root` over `dev` at `86fab037`: the rows (`80577fd1`), the owner of `/` and the words (`6a65a26c`), the one owner test (`68a67e57`), 135's Lows (`5ae12424`), the variable read once (`0eabc967`), the pages and the news file (`a48306d9`), the landing notes (`bf0c0b1e`); with the specification, its pre-build review (M1 applied in `c90aa3b8`, signed again in `7d44586d`), the memo `context/research/2026-10-27-the-module-cache-refused-where-another-uid-owns-the-root.md`, 135's pull request review, the news file and the pull request's description (one `gh pr view 32`).
- **Run:** 40631872235 (`ci-status`), **still running** when read with one `gh pr checks 32` at 00:25: `plan`, `quick` (ruff, mypy, the unit tests, lint), the set's key and the arm64 macOS set green; every `judge` shard on Linux, macOS and Windows, and `verify`, pending. The gather's summary and the Windows legs are not yet read; the criteria that need them say so.
- **Re-ran** (macOS arm64, Darwin 25.5.0, `WASI_PYTHON_ARTIFACTS` at the main tree's `build/release-0.1.1/set/wasi-python-0.1.1`; probes under `build/147-review/`, not committed):
  - `uv run pytest -q -p no:cacheprovider tests/unit/test_runner_module_caches.py tests/unit/test_runner_module_cache_read.py tests/unit/test_runner_sets.py tests/unit/test_runner_grants.py tests/unit/test_runner_sweep.py` → **159 passed, 3 skipped**, exit 0; ratchet lost 0, gained 0, grew 0, "judge changed" the two row files.
  - `uv run pytest -q -p no:cacheprovider tests/checks/test_rules.py` → **121 passed, 1 skipped**, exit 0.
  - `uv run python build/147-review/probe.py`: `_platform._way` given stand-in `lstat`s for fifteen hosts, and two full misses through `_engines._module_miss` on real folders. EXECUTED; the table is under "The predicate, as coded".
  - The guard `test_a_cache_reached_through_a_link_then_dotdot_in_a_writable_grant_is_refused` (two cases) and row 11 by node id → 3 passed, exit 0; the same two with row 9, under `-p probe_abspath` (a plugin under `build/147-review/` that makes `PLATFORM.absolute` `os.path.abspath`) → **the guard's `[2]` and row 11 failed**, the guard's `[1]` and row 9 passed, exit 1.
  - `uv run python build/147-review/probe_cwd.py`, on this branch's `src/` and on `origin/dev`'s (`git archive` into `build/147-review/dev-src`, `PYTHONPATH`): a process whose working folder was removed fails every `run` with `FileNotFoundError`, with or without a cache folder or the variable, on both. EXECUTED.
  - `uv run python build/147-review/probe_count.py`: the `lstat` calls `cache_folder` makes, 20 for a way ten folders deep, 24 for twelve with two to make. EXECUTED.
  - `git log --format='%(trailers:key=Co-Authored-By,valueonly)' origin/dev..HEAD` → every commit `Claude Opus 5.5 <noreply@anthropic.com>`; no `Claude-Session:` trailer.
- **Time box:** 25 minutes plus the probes (a parallel-safe runner change, read as a security reviewer because it changes the check on the way to native code); kept, 00:22 to 00:31.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning.

## The predicate, as coded

`_way` (`src/wasi_python/_platform.py:593`) walks `/` first, keeps `/`'s stat as `top`, and for every folder other than `/` asks `_owner_trusted(st, top)` (`:624`): this user's by `_this_users` (the effective uid, through `_owner`), else owner 0, else, when `top` is known, `owner == root_owner != _OVERFLOW_UID and st.st_dev == top.st_dev`. Python's chained compare means `st_dev` is read only after the owner matched `/`'s and `/`'s owner is not 65534, so a stand-in without `st_dev` (135's ancestor row) never reaches it (READ, and EXECUTED below). `/` skips the owner test and keeps the kind and mode tests; when `/` fails, the advice is `_ROOT_ADVICE` (`:132`), Decision 2's text verbatim (READ, compared with the specification's sentence). `top is None` (only a stand-in that hides `/`) trusts no owner of `/`, the safe answer. The probe's table (EXECUTED, `build/147-review/probe.py`; cache at `/home/runner/.cache/wasi_python`, `/home/runner` and `.cache` this user's at 0700 unless named):

| host | answer |
|---|---|
| `/` 2346 at 0755, `/home` 2346 on `/`'s device (the embedder's shape) | used |
| the same, `/home` on another device | refused: "/home, on the way to it, is another user's (uid 2346); set $WASI_PYTHON_CACHE to a folder of yours" |
| `/` 2346 at 0777 | refused: "/, on the way to it, may be written by others (mode 777) and is not sticky; no folder can hold the cache while it is, so have its owner run chmod go-w /, or pass cache_dir=False to compile in memory without this warning" |
| `/` 2346 at 0775 | refused, the same words with "(mode 775)" |
| `/` 2346 at 1777 | used |
| `/` 65534, `/home` 0 | used |
| `/` 65534, `/home` 65534 | refused at `/home`, "(uid 65534)" |
| `/` 0, `/home` 2346 | refused at `/home` |
| chroot-like: `/` this user's, `/home` this user's | used |
| chroot-like: `/` this user's, `/home` 2346 | refused at `/home` |
| `/` 2346, `/home` 2346 at 0775 | refused at `/home` for its mode |
| `/` 2346, `/home` 0, `/home/runner` 2346 on another device | refused at `/home/runner` |
| `/` hidden from the stand-in, `/home` 2346 | refused at `/home` |
| `/` 2346 with no `st_dev`, `/home` 0 (135's stand-in shape) | used, no `AttributeError` |
| full miss, real folders, `/` stood in as 2346, the folder above the cache 2346 on `/`'s device | `{'compiled': 1, 'loaded': 0, 'written': 1}`, no warning |
| the same, the folder above on `/`'s device plus one | `{'compiled': 1, 'loaded': 0, 'written': 0}`, one warning naming the folder above as "another user's (uid 2346)" |

Each answer is the one Decision 1, its edge cases and M1's narrowing ask for. Trusting `/`'s owner below `/` on `/`'s own device adds no one: that owner can already `chmod` `/` and rename the way (INFERRED, as the pre-build review argued); past a mount it is refused, as the second and twelfth rows show; a bind mount of `/`'s own file system is the remainder the specification names, not closed (READ, Decision 1). Btrfs subvolumes and other mounts that give one file system several devices answer "refused", the safe direction (INFERRED).

The rest of the security change, read against the code. `_as_made` (`:507`) and `_way` ask the one owner test by the effective uid; under a setuid program that tightens the way (the invoking real uid's folders are no longer trusted on it) and lets the process load the files it made itself, which the real-uid test refused (INFERRED). `default_cache_dirs` (`:468`) lists the homes of both uids, each `pwd` lookup in its own `try`; a wider list only keeps more folders from the guest's grants (READ). `cache_folder` walks the way again after its `mkdir` loop (`:538`): a folder another user made in between is judged, a link put there is "not a folder", a folder gone raises `FileNotFoundError`, which `_module_miss` catches as `OSError` and turns into the warning (READ, `_engines.py:216-218`; EXECUTED by row 6). `_cache_given` (`_engines.py:89`) reads `$WASI_PYTHON_CACHE` once and returns `_Cache(folder, named)`; `_caches` names `chosen.named` and never reads the variable again (READ). `PLATFORM.absolute` joins without collapsing on POSIX (`_platform.py:354`) and is `os.path.abspath` on Windows (`_platform_windows.py:244`). `os.path.abspath` would collapse `granted/link/../c` to `granted/c`, a folder the system would not reach, so the grant judge would see a path that never passes the link in the writable grant and the guard would lose its case; with it swapped in, the guard's `[2]` and row 11 turn red (EXECUTED). `absolute` calls `os.getcwd()` for an absolute path too, where `abspath` did not; a removed working folder already fails every call on `dev` (EXECUTED, `probe_cwd.py`), so it adds no failure.

**The pages, read as the embedder on Cloudflare would.** The install page now says every folder on the way must be "yours, root's or the owner of `/`'s, since whoever owns `/` can already replace every folder below it on its own file system", with the mode rule after it; the security model adds that "some container hosts give `/` to a uid of their own". An embedder whose `/` is uid 2346 at 0755, with `/home` on the same overlay and `/home/runner` its own, learns that its cache will now be used (and the warm-up should report `loaded`), that a volume mounted on the way and owned by `/`'s uid is not trusted, and, from the warning itself, that a `/` open to other writers needs `chmod go-w /` in the image or `cache_dir=False`. The memo's two unread facts (`/`'s mode, `/home`'s owner) decide whether that host passes; the pages say what each answer means (READ). They name no host, specification or review (READ; `tests/lint` below).

## Acceptance criteria against evidence

1. Rows 1 to 7 and 9 to 11 exist and were seen failing on the base, each named with its failing line in the description; the guards 2(d) and 3(b) green both ways — met: the description lists each row's failing line from `build/147/rows-before.txt`, "18 failed, 3 passed", the three passes the two guards and the rewritten row 8 (READ, `gh pr view 32`); the rows pass on this branch (EXECUTED, 159 passed).
2. The two row files green on Linux and macOS, the POSIX rows skipped on Windows with their reason — met on macOS (EXECUTED); Linux and Windows wait on run 40631872235. The skip reason is "Windows has no ancestor rule; the grant rule guards it" on every new POSIX row (READ).
3. Row 8 through the by-path fallback, skipped on Windows naming the held-handle row — met on macOS (EXECUTED): its `reopen` stand-in raises, so wasmtime is given the path, and the row asserts `given == [str(checked)]`, so it cannot pass for the old reason (READ); the Linux leg and the Windows skip wait on the run.
4. Every guard Decision 6 lists green, unchanged — met on macOS for the five unit guards (EXECUTED, among the 159; READ, their bodies untouched but for `held=None` at two calls); `test_runner_caches_the_compiled_module` and `test_fuel_does_not_depend_on_the_module_cache` are in the embedding shards of the run, not read yet.
5. Decision 2's text verbatim in `_platform.py`, row 3 asserting it — met (READ, `_platform.py:132`, the row's `ROOT_ADVICE` and `endswith`; EXECUTED, the probe's third row prints it whole).
6. No accepted pass lost, no fuel or byte grows — met locally (EXECUTED, ratchet lost 0, grew 0 on the five files; READ, the builder's fast tier "lost 0 · gained 0 · grew 0"); the guest is untouched, so no fuel or byte can move (READ, the diff touches no recipe or artifact). The gather's `GROWTH` rows wait on the run.
7. The rules checks, `public_api.txt`, ruff, mypy, lint — met: `quick` green in the run (READ, `gh pr checks`), `tests/checks/test_rules.py` 121 passed, 1 skipped (EXECUTED), `tests/public_api.txt`, `LONG_FUNCTIONS` and `SEAM_ALLOWED` untouched (EXECUTED, `git diff --stat` of `tests/checks` and `tests/public_api.txt` empty); no function over 80 lines outside the known list (EXECUTED, the `ast` command: `_call._instance`, `_process.__init__`, `_sessions._open_session`, `runner.run`, `run_async`, `Session.__init__`, as on `dev`).
8. The news file with Decision 7's line and its claim, the four pages, `ci-status` green — the news file's line is Decision 7's verbatim but for "(spec 147)" at its end, the four pages carry Decision 7's sentences (READ); `ci-status` waits on the run.

## Findings, most severe first

No High and no Medium. Three Lows, two written in.

1. **L1. The self-check's Windows box is not checked** (pull request #32's description) — "The Windows legs of this pull request's run were read. (not yet read)", as expected while the run is going. Fix text, the author's: check it once run 40631872235 has ended, with one line saying that the new POSIX rows and row 8 were skipped on Windows with their reasons and every other row in the two files passed there, and name the run in the specification's landing notes.
2. **L2. The claim's `changed` names one check where Decision 7 named four, and the landing notes do not say why** (`context/changes/147-the-module-cache-on-a-host-where-another-uid-owns-the-root.md`, Claims) — the three calls that now pass `held=None` move no check's status, need, reason or metric, which is what `changed` lists (`context/changes/README.md:16`), so the block's comment naming them is right; only the record of the difference was missing. **Written in** (`85b1e31f`), under "Different from the specification": "The claim's `changed` names the swap row alone, where Decision 7 also named the three direct calls of `_module_miss` that now pass `held=None`: those calls move no check's status, need, reason or metric, which is what `changed` lists (`../changes/README.md`), so the claim block's comment names them instead."
3. **L3. The second walk's count is not in the landing notes, which Decision 4 asks for** (the specification, Decision 4's last sentence) — **written in** (`85b1e31f`), from my probe: "**The second walk's cost** (EXECUTED by the pull request's reviewer, `build/147-review/probe_count.py`, not committed, counting the calls of the `lstat` the walk is given, on this macOS host): a cache miss now takes two `lstat`s per folder on the way to the cache where it took one, 20 for a way ten folders deep whether the cache folder is new or already there, and 24 for a way of twelve with two folders to make. It runs once per flavor per process, on a miss of the process's own modules."

Two notes, no change asked. A `/` that is not a folder gets `_ROOT_ADVICE` ("have its owner run chmod go-w /"), which names the mode's fix; `lstat("/")` is a folder on every real system, so only a stand-in reaches it (EXECUTED, the probe's "/ is a link" row; INFERRED). The security model's earlier sentence, "The runner trusts every folder on the way to its cache to be yours, so running it with another user's home … is not supported", now sits beside "yours, root's or the owner of `/`'s"; it is about a home, not the way's owners, and reads true.

**Structure (4a).** Not structural, confirmed: two module constants (`_OVERFLOW_UID`, an `int`; `_ROOT_ADVICE`, a `str`) and one `NamedTuple` class, none mutable; no lock; no use of wasmtime's private API; no `sys.platform`, `os.name` or `platform.system` added (EXECUTED, `grep` of the diff's added lines); the one platform difference is `absolute`, a method of the platform object with its protocol line; the seams are `_module_miss`'s existing `lstat` and `reopen` parameters and the observers' `owner_of` on the process object; the longest new or changed function is `_Posix.cache_folder`, 30 lines (READ, the landing notes; EXECUTED, the `ast` command finds none new over 80). R6's judge-only branch (`_owner` asking the observers) is now asked by the cache's checks too, as the pre-build review's L2 wrote down for the next structural review.

## Constitution checks

- §4.1, §4.2, §4.8: no patch, no pin, no download touched (READ, the diff's paths).
- §4.4, §4.6: the guest's imports and the artifact set are untouched (READ).
- §4.5 (embedder-neutral): the code, the rows and the pages name no host; "Cloudflare Containers" is in the news file and the memo only, and `context/embedders.txt` lists none of them (READ).
- §4.9: every row counts `stats()` deltas and warnings; none times anything (READ).
- §4.13: ruff, mypy and the unit tests green in `quick` (READ, the run); `tests/lint` green (EXECUTED, below).
- §4.15 (safe by default): Decision 1 loosens a default, one more owner trusted on the way to native code, and the owner decided it on 2026-10-27 (READ, the specification's Status, the roadmap's 0.1.2 line); M1's device rule, the overflow rule, the effective-uid test and the second walk each tighten what was decided; no call is refused, the cache is unused with a warning (READ, Scope; EXECUTED, the probes).
- §5.6: reviewed before it was built and signed fit to build on `c90aa3b8`; the code is that specification (READ, this review).
- §7 never-do list: nothing tripped; no prior art copied, no artifact in git, no third-party host probed, no number reported that was not executed (READ; the landing notes cite their files under `build/147/`).

## Disposition (filled in by the author, then confirmed by the reviewer)

1. L1 — 
2. L2 — written in by the reviewer, `85b1e31f`.
3. L3 — written in by the reviewer, `85b1e31f`.

## Verdict

Does not land yet: run 40631872235 has not concluded, so criteria 2, 3, 4 (the embedding guards), 6 (the gather's `GROWTH`) and 8 (`ci-status`) and the Windows legs are unread; nothing in the code stands (no High, no Medium), and once the run is green with its Windows legs read this verdict is written again to begin "Lands".
