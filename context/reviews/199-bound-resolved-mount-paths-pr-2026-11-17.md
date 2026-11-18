# Review of 199 — Bound resolved mount paths

- **Date:** 2026-11-17
- **Reviewer:** an agent (Codex), a fresh sub-agent of the Codex session coordinating PR 124; not the author
- **Reviewed:** `a85cac7f..b50eed31` on PR 124, tree `f28d4af7`. Parallel-safe review, 25-minute review box.
- **Run:** 44234604089. The gather (job 134572700931) reported 1,146 goal passes, six blocked, zero failures, and 4,788 unit passes with 109 skipped. All eleven Windows judge shards passed. The only refusal in the review and ci-status logs was the missing review file. I read all four checked boxes in the author's self-check.
- **Re-ran:** `tests/unit/test_runner_mounts.py::test_a_resolved_mount_path_counts_its_folder_in_utf8` and `::test_rename_bounds_the_path_of_a_staged_file`, three cases passed, exit 0. The full `tests/unit/test_runner_mounts.py` then passed 72 cases, seven skipped, exit 0, on Linux with CPython 3.14.2.

## Acceptance criteria against evidence

1. **EXECUTED.** A normalized descriptor-relative path with a multibyte final name succeeds at exactly 4,096 UTF-8 bytes. The over-limit lookup returns `ENAMETOOLONG` and leaves the provider call count unchanged.
2. **EXECUTED.** Both the open and pending-write-back cases complete a rename to the boundary, refuse the next rename before the provider is called and persist the staged byte to the last accepted path.
3. **EXECUTED and READ.** The local mount suite passed. The hosted Linux and Windows judges passed. The normalized lookup and preflight are reached through the provider mount paths. Forwarded grant operations retain their existing dispatch.

## Findings, most severe first

None.

## Constitution checks

- **§4.** The runner reuses the existing path limit and error. The guest imports, exports, build inputs, permissions and artifact set keep their existing contracts.
- **Structure.** The resolver checks the UTF-8 length and the descriptor table checks descendants before the provider mutates them. The change introduces no new shared state, platform conditional or native API. Both modules and the changed functions are within the existing size ceilings.
- **Judge.** The news file claims the three new unit cases. The gather listed no growth. The diff touches no workflow or release script.
- **§7.** The review inspected the source, existing test results and the normal PR run.

## Disposition

There are no findings to resolve.

## Verdict

Lands: provider lookups and tracked renames now enforce the documented byte limit before a provider sees an overlong path or changes its namespace.
