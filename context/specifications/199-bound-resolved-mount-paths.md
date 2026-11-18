# 199: Bound resolved mount paths

- **Status:** built from `dev` at `a85cac7f`; awaiting pull request review.
- **Date:** 2026-11-17
- **Owner:** Clay Gendron
- **Kind:** parallel-safe runner change. The guest ABI, build and artifact set stay the same. The two affected functions and their modules stay inside the structural ceilings.
- **Depends on:** the mount path checks and descriptor tracking on `dev`.
- **Research it stands on:** the path resolver and rename handling in `src/wasi_python/_fs_paths.py` and the mount table's descriptor tracking in `src/wasi_python/_fs_table.py`, read on the base commit.

## Decisions

Measure the canonical provider path in UTF-8, including the leading slash. Keep the existing 4,096-byte limit and error number.

## Intent

The provider receives a mount-relative absolute path. Its 4,096-byte limit includes the leading slash, the open folder's path and the normalized relative argument, measured as UTF-8. The raw argument keeps its existing limit.

## Design

Check the normalized path before calling the provider. A rename that would lengthen an open descendant's path past the same bound fails before the provider can commit the namespace change. Include pending write-backs in that check. An unlinked descriptor no longer follows the name. Descriptors in another mount are independent.

## Scope

The runner's provider-backed mounts, their tests and the mount guide. Wasmtime continues to resolve paths in ordinary grants.

## Acceptance criteria

1. A lookup relative to an open folder accepts a resolved path of exactly 4,096 bytes. Another byte yields `ENAMETOOLONG` without a provider call.
2. A rename may put a live or pending descriptor exactly on the boundary. A rename that would exceed it returns `ENAMETOOLONG` before the provider changes anything. The original write-back path and staged bytes survive the refusal.
3. Existing mount and grant semantics pass the mount suite.

## Landing notes

EXECUTED on Linux, Python 3.14.2. The three added unit cases failed against the original runner. Lookup returned the provider's missing-file answer and both rename cases reached the provider. The same cases pass on the change, including the write-back at the last valid path.

The [independent review](../reviews/199-bound-resolved-mount-paths-pr-2026-11-17.md) read the green Windows and Linux judges and the gather in [run 44234604089](https://github.com/ClayGendron/wasi-python/actions/runs/44234604089).
