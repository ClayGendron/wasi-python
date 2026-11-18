# 197: Protect missing host interpreter folders

- **Status:** Built on the specification branch, awaiting pull-request review. Requested by the owner on 2026-11-17.
- **Owner:** Clay Gendron
- **Kind:** Parallel-safe runner change.
- **Depends on:** The existing grant and missing-cache checks in `src/wasi_python/_places.py`.
- **Research it stands on:** The grant review of 0.1.5 found that the runner registers the interpreter's configured folders only when they already exist.

## Decisions

Use the same identity and remaining-path checks for the host interpreter's folders as for a module cache. Protect the user site when the interpreter enables it.

## Intent

A caller can grant a workspace while preserving the folders a later host interpreter will trust.

## Design

Keep the configured spelling of each path. Record its canonical chain, the identities on its written path, and the remaining components under its deepest existing ancestor. Judge grants and planned roots together before creating any directory.

## Scope

The host's configured library and scripts folders and enabled user site. The existing rules for sharing a read-only folder and creating an unrelated sibling root still apply.

## Acceptance criteria

1. A writable grant over a missing host Python folder is refused. The same grant is accepted read-only.
2. A new root overlapping a missing host Python folder is refused before anything is created. An unrelated sibling root is accepted.
3. The same rules cover the user site and an installation path supplied by sysconfig.

## Landing notes

On the original runner, all four new parameter cases failed because no ValueError was raised. After the change, the public-runner cases, their file's existing checks and the writing-convention suite passed (30 checks on Linux, Python 3.12).
