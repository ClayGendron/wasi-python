# 145: A mount's names work the same on every host

- **Status:** **built 2026-10-27, but for Decision 3's set-times answer**, which the landing notes give back to the owner with the evidence against it; on `spec/145-a-mounts-names-work-the-same-on-every-host`, rebased onto `ee72523e`; not yet in a pull request. Before: drafted 2026-10-27 from `../research/2026-10-27-a-code-review-of-the-runner-for-production-use.md` (§3); not yet built; the owner asked for it to be built on 2026-10-27 with the 0.1.2 scope (`../roadmap.md`).
- **Date:** 2026-10-27
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural**: `src/wasi_python/_fs_paths.py` (`_resolve`, the `O_DIRECTORY` open, `path_filestat_set_times`; 578 lines, about 15 added), `src/wasi_python/_fs_descriptors.py` (`fd_pread`'s slice; 442 lines, one line), rows in `tests/unit/test_runner_mounts.py` and `tests/checks/test_v1_2_hostile_guest.py`, two paragraphs in `docs/how-to/mounts.md` and one in `docs/reference/guest-filesystem.md`. It changes four answers of the guest's filesystem on a mount and nothing on a grant, no import or export of the guest, no artifact, no recipe. No change to `tests/public_api.txt`.
- **Depends on:** nothing in flight. Landed and unchanged: the mounts and their resolver (032, 034, 110, 111), the poll shadow (140).
- **Research it stands on:** `../research/2026-10-27-a-code-review-of-the-runner-for-production-use.md`, §3 (Medium 4 and four of its Low rows), a fresh sub-agent's read of the four `_fs_*.py` modules and `mounts.py`, cited by line.

## The problem

The provider contract promises a normalised absolute path (`mounts.py:82`; `docs/how-to/mounts.md:39`) and says nothing else about a component. `_resolve` splits on `/` alone (`_fs_paths.py:69`), so a guest's `a\..\..\x` or `C:x` reaches the provider as one component. A provider on Windows that writes the obvious `Path(root) / path` then opens outside its mount: `pathlib` resets to the drive on `C:x`, and the host treats `\` as a separator. No provider ships in the package, so no shipped code is wrong, but it is the first provider anyone writes, and the contract does not warn them (READ, the memo's Medium 4).

Three answers on a writable mount differ from wasmtime's on a grant, each small (READ, the memo's §3 Low rows): `path_filestat_set_times` succeeds on a missing path, since it resolves and returns without a `stat` (`_fs_paths.py:424-426`); `fd_pread` bounds its `EINVAL` check by `count` and its slice by `size` (`_fs_descriptors.py:254-257`); an `O_DIRECTORY` open asks the provider to `list` without a `stat` first (`_fs_paths.py:150-155`), so a lenient provider hands a listing back for a file.

## Decisions

### 1. A component with a backslash or a colon is refused with `EINVAL`

`_resolve` answers `EINVAL` for any component that holds `\` or `:`, before the provider is asked anything, on every host. Reason: a mount's names must mean the same thing on every WASI host (the constitution's §6.3), and a name with either character cannot be a Windows name, so a provider that stores on a host filesystem would have to refuse it there anyway; refusing it in the runner means the provider never sees a component that any host's path logic could reinterpret. A grant is not touched: wasmtime answers a grant's names itself, host by host, and the limitations page already says errors are WASI's numbers. The guest-filesystem page lists the two characters under the mount's rules.

### 2. The contract says what a provider may assume

`docs/how-to/mounts.md` gains a paragraph: each component is a name, never `.`, `..`, empty, or a string with `/`, `\`, `:` or NUL, and a provider that stores on a host filesystem joins components one at a time and never hands the whole path to a host path function. The `FileProvider` docstring says the same in one sentence. Reason: the resolver's rules are the contract's; writing them where the provider's author reads them is the fix for the gap, and Decision 1 makes the written rule true.

### 3. The three answers follow wasmtime's

`path_filestat_set_times` on a writable mount asks the provider `stat` first and answers its errno when the path is missing; times stay accepted and ignored, as today. `fd_pread` slices by `count`, the bound its check judged. An `O_DIRECTORY` open asks `stat` first and answers `ENOTDIR` itself for a file, before any `list`. Reason: each is one call or one word, and each brings the mount's answer to what wasmtime answers on a grant, which is the rule every shadow in `_fs_paths.py` already states for itself.

### 4. The rows first

- `tests/unit/test_runner_mounts.py`: a component with a backslash and one with a colon answer `EINVAL` on a read-only and on a writable mount, and the counting provider saw no call (red today); `path_filestat_set_times` on a missing path answers `ENOENT` and the provider saw one `stat` (red today); `fd_pread` past `PREAD_CHUNK` writes `count` bytes (red today); `O_DIRECTORY` on a file answers `ENOTDIR` and the provider saw no `list` (red today).
- `tests/checks/test_v1_2_hostile_guest.py`: a guest program that opens `a\..\..\x` and `C:x` on a mount gets `OSError` with WASI's `EINVAL` and the mount's provider recorded no call; green only after the change.

## Intent

After this specification, a provider's author can read the mount contract and write a provider that stores on any host filesystem without a path escaping the mount, because the runner has already refused every component a host could reinterpret; and the four small answers of a mount that differed from a grant's no longer do.

## Design

- `src/wasi_python/_fs_paths.py`: the two characters refused in `_resolve` with the `/` split (Decision 1); `stat` before `list` for `O_DIRECTORY` and before the times answer (Decision 3).
- `src/wasi_python/_fs_descriptors.py`: `fd_pread`'s slice by `count` (Decision 3).
- `src/wasi_python/mounts.py`: one sentence in the `FileProvider` docstring (Decision 2).
- `docs/how-to/mounts.md` and `docs/reference/guest-filesystem.md`: the component rules (Decisions 1 and 2).
- The news file `../changes/145-a-mounts-names-work-the-same-on-every-host.md`: under Fixed, "A mount refuses a path component with a backslash or a colon with `EINVAL` on every host, and its times, `pread` and directory-open answers follow wasmtime's."
- The commits, in order: the rows seen failing; the resolver and the three answers; the docs and the news file.

## Scope

In: the above. Out:

- any change to a grant's answers, which are wasmtime's;
- the `writable` checks moved to one chokepoint, and the nested-preopen `EPERM` against `ENOENT`: design choices for a change to the boundary, as the memo's §6 says;
- a provider shipped in the package;
- any change to `tests/public_api.txt`.

## Acceptance criteria

1. The rows of Decision 4 exist and were seen failing before the change, each named with its failing output in the pull request.
2. `uv run pytest tests/unit/test_runner_mounts.py` is green on Linux, macOS and Windows in the pull request's run, and the hostile-guest row is green on the pull request's shards.
3. No accepted pass is lost, and the mount rows' fuel stays within the ratchet's tolerance, or the growth is claimed in the news file with its reason.
4. `docs/how-to/mounts.md` states the component rules and `docs/reference/guest-filesystem.md` lists the two refused characters, and `mkdocs build --strict` is green.
5. The news file exists and `ci-status` is green.

## Landing notes

Built 2026-10-27 by an agent (Claude Opus 5.5), the builder of this specification, a sub-agent of the orchestrating session, in the worktree `../wasi_python-wt/spec-145`, on `spec/145-a-mounts-names-work-the-same-on-every-host` from `898bc091`, rebased onto `ee72523e` (`dev`'s tip with this specification, pull request #26) before these notes. Guest checks ran on the published 0.1.1 artifact set, read-only. Labels: EXECUTED means I ran it, READ means I read the file cited, INFERRED means my reasoning.

The commits, in order: `2029cd15` the rows, seen failing; `bb5904d4` the resolver and two of the three answers; `90cc0d79` the docs, the docstring and the news file; then this section.

The rows seen failing first, on the unchanged code (EXECUTED, `build/145/rows-unit-before.log`, `build/145/row-hostile-before.log`, not committed):

- `test_a_backslash_or_a_colon_in_a_component_is_refused[read-only]` and `[writable]`: every row answered 44 (`ENOENT`, the provider asked) where 28 (`EINVAL`) is wanted.
- `test_pread_writes_no_more_than_it_judged`: `(0, 65600)` bytes read where `(0, 65536)` is wanted.
- `test_a_folder_open_of_a_file_is_refused_before_any_listing`: a file opened with `O_DIRECTORY` over a lenient provider answered 0 where 54 (`ENOTDIR`) is wanted.
- `test_a_mount_refuses_a_name_a_host_could_reinterpret` (hostile guest): `a\..\..\x` and `C:x` answered 44 to read and were created (`opened`) to write, where 28 is wanted for all four.

After (EXECUTED): all five green; `tests/unit/test_runner_mounts.py` 72 passed with the artifact set; the mount-related selection of `test_runner_grants.py`, `test_runner_waits.py`, `test_runner_mounts.py`, `test_v1_4_sessions.py`, `test_v1_4_embedding.py` and `test_v1_2_hostile_guest.py`, slow rows included, 170 passed, 2 skipped (`build/145/mount-related-2.log`).

Three existing checks hold the new `stat` (READ, the diff): an `O_DIRECTORY` open of a folder below the mount now makes one `stat` before its `list`, as Decision 3 asks. `test_a_path_is_normalized_before_the_provider_sees_it` gains `("stat", "/d")` before `("list", "/d")`; `test_a_listing_is_kept_and_listed_again_from_cookie_zero` counts `stat` 1, not 0; `test_v1_4_embedding.py::test_a_mount_serves_reads` counts `scandir` of `/work/d` as one `stat` and one `list` and the run's total `stat` as 3, not 2. Each check still asserts every call; none is loosened. The specification's Design did not name them.

The cost of Decision 1, recorded as the owner asked (2026-10-27): Decision 1 refuses a colon on every host, so a guest cannot name a file with a colon on a mount, such as `12:30.csv`, where it can on a Linux or macOS grant. The cost is accepted and written on `docs/reference/limitations.md`, beside the mount's other host rules, and in the CHANGELOG line.

### Different from the specification, each for a reason

1. **Decision 3's set-times part is not built.** Spec 034's landing notes record, EXECUTED on wasmtime 49 in a Linux container and on macOS, that `path_filestat_set_times` of a missing path with no time flags answers 0 on a Linux grant (wasmtime's reference) and 44 on macOS; `tests/unit/test_runner_grants.py`'s `LINUX_ROWS` holds `"path set times 'missing'": 0`, and the parity row compares the grant with the mount on Linux. With Decision 3 as written (a `stat` first, its errno answered), the mount answered 44 and both `test_raw_write_calls_answer_as_a_writable_grant_does` and `test_the_write_differences_are_as_decided` failed (EXECUTED, `build/145/mount-related.log`): the change would have moved the mount away from Linux's grant answer, not toward it. The likely reason is Linux's `utimensat`, which returns 0 without looking up the path when both times are `UTIME_OMIT` (INFERRED; not run here). A design that would hold both answers, such as a `stat` only when a time flag is set, is a new design and is the owner's: the set-times code, its row and its `utime` expectation are left as they were, and the CHANGELOG line names the `pread` and directory-open answers only. Today `os.utime` always sets a flag, so a guest's `os.utime` of a missing path on a mount still succeeds, where a Linux grant would answer `ENOENT` (INFERRED).
2. **The folder open is its own function, `_open_folder`.** With the `stat` inline, `_path_open` was 82 lines and `test_no_function_is_over_eighty_lines` failed (EXECUTED); split out, `_path_open` is 76 lines and `_open_folder` 12 (EXECUTED, `ast`). The answers are the same.
3. **The mount itself is listed with no `stat`.** A folder open of `/` lists at once, as `_open_writing` already answers the mount itself with no call: its `stat` must be a folder by the protocol. So `os.listdir` of the mount still makes one `list`.
4. **A listed name is not checked for the two characters.** A provider's `list` may still return a name with `\` or `:`; the guest sees it but cannot open it. The how-to says so; checking listed names was not in the specification.

### Verification (EXECUTED)

- `uv run ruff check src tests`: all checks passed; `uv run ruff format --check src tests`: 188 files already formatted; `uv run mypy src/wasi_python`: no issues in 27 files.
- `uv run pytest tests/unit/test_runner_mounts.py -q` with the artifact set: 72 passed (65 passed, 7 skipped without it).
- `uv run pytest tests/lint -q`: 9 passed. `uv run pytest tests/checks/test_rules.py -q`: 121 passed, 1 skipped. `mkdocs build --strict` with the docs group: built, exit 0 (`build/145/mkdocs.log`).
- The fast tier, `uv run pytest -m "not slow" -n 3` (`build/145/fast-tier-2.log`): 3,815 passed, 51 skipped in 415 s; `ratchet vs 1921c3815c: lost 0 · absent 0 · unrun 1 · unrun locally 40 · gained 1 · grew 0`. The one gained is the hostile-guest row. The 41 unrun are blocked by needs a worktree does not have (the source trees, the compile records, the prior-art clones, the wheel, the wasmtime CLI), none of them a mount's; the judge marks one of them "accepted pass blocked", which CI, where the needs are met, reads. No fuel grew, so the claim block names no growth. A first run of the fast tier was red with five unit failures of the judge's own wiring (`test_landing_lane.py`, `test_checks_wiring.py`): `uv run --group docs` had installed `platformdirs`, whose pytest plugin the judge rightly names as foreign; after `uv sync` the second run above is clean.
- `_fs_paths.py` 578 to 592 lines, `_fs_descriptors.py` 442 to 443; `_path_open` 76 lines, `_open_folder` 12, `_resolve` 31 (`ast`). No module-level mutable, no private wasmtime-py name, no platform branch; `tests/public_api.txt` unchanged. The added lines under `src/` and `tests/` name no specification, review or `context/` path.

## One line

A mount refuses a path component with a backslash or a colon on every host, so a provider never sees a name a host could read another way, and its `pread` and folder opens answer as wasmtime's do; the set-times answer waits on the owner.
