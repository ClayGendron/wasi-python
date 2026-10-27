# 145: A mount's names work the same on every host

- **Status:** drafted 2026-10-27 from `../research/2026-10-27-a-code-review-of-the-runner-for-production-use.md` (§3); not yet built. It waits for the owner's instruction to build.
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

Not yet built.
