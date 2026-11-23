# Review of 197 — Protect missing host interpreter folders

- **Date:** 2026-11-17
- **Reviewer:** an agent (Codex), a fresh sub-agent of the Codex session coordinating PR 127; not the author
- **Reviewed:** `a85cac7f..54552dff` on PR 127, tree `571e9334`. Parallel-safe review, 25-minute review box.
- **Run:** 44235435012. The gather (job 134575454966) reported 1,146 goal passes, six blocked and zero failures. The unit suite recorded 4,796 passes with 109 skipped. All eleven Windows judge shards passed. The review and ci-status jobs each named the missing review file as their only refusal. All four boxes in the author's self-check are checked.
- **Re-ran:** `tests/unit/test_runner_sets.py::test_missing_host_python_folders_are_protected`, `tests/unit/test_runner_grants.py::test_changed_directory_depth_keeps_the_pending_folder_protected` and `::test_a_trusted_folders_missing_tail_matches_its_observed_ancestor` on Linux with CPython 3.14.2. Seven passed, exit 0.

## Acceptance criteria against evidence

1. **EXECUTED.** A writable grant above the absent user site or scripts folder is refused. Its read-only counterpart can run.
2. **EXECUTED.** New roots above, at and below the protected path are refused before creation. An unrelated sibling root succeeds.
3. **EXECUTED and READ.** The public runner tests cover both the enabled user site and a sysconfig installation folder. The implementation inventories the configured libraries and scripts through the same trusted-path function.
4. **EXECUTED and READ.** Three timing cases exercised a checked ancestor and its suffix when another component appears during validation. The walk compares existing and planned components from the matched ancestor on both POSIX and Windows. The reported scope is the configured host interpreter and its enabled user site.

## Findings, most severe first

1. **Medium, resolved during review.** The first implementation inventoried a missing folder before walking the caller's paths. A newly created directory could then separate the two recorded depths. A second filesystem pass could also lose the missing suffix.

## Constitution checks

- **§4.** The change uses the existing grant walk and directory identities. The guest interface, artifact set, build inputs and upstream sources retain their contracts.
- **Structure.** The path relationships remain in the existing grant-policy module. The change adds no shared state, platform conditional or native API. The new checks sit in existing unit files.
- **Judge.** The news file claims seven new unit cases. The gather listed no growth. The diff touches no workflow or release script.
- **§7.** The reviewer read the source, the normal PR run and the results from the focused regression tests.

## Disposition

1. **Fixed and confirmed** in the reviewed tree. The resolver derives the trusted identity, deepest existing ancestor and suffix in one scan. The judge compares each writable walk from the matching ancestor. The three added timing cases passed on the corrected head.

## Verdict

Lands: configured interpreter folders are protected while missing and during the directory creation covered by the review.
