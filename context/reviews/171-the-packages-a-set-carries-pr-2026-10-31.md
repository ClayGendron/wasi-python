# Review of 171 — The packages a set carries

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** pull request #78, `117bcd67...df910ed1`, the fix `0370affe`, then the rebase onto `a750e8fe` at `05206aed`, with the specification and its pre-build review
- **Run:** 41216203527 on `0370affe` (relayed): gather green, 0 fail, 11 Windows legs green, `ci-status` red only for this file; no `GROWTH` rows, since fuel is compared only on macOS legs and none ran, so the post-merge run reads growth against the claims. Then 41244515439 on `05206aed`, alike. No `gh` call
- **Re-ran:** `tests/lint` → 14 passed; six unit files → 156 passed; `test_rules.py`'s length, generated-pages and news-file rows with `test_v1_4_public_api.py` → 14 passed; the two new goal checks on the branch's set → 3 passed; `wasi-python packages` with a set, without one, with `--bogus`, and an unknown command → exits 0, 1, 2, 2; three malformed zips (Finding 1). At `05206aed`: the goal checks, the two unit files and four rules rows → 92 passed; the zip holds 58 `top_level.txt`, `pdfminer`, `pdfplumber` and `xarray` among them.
- **Time box:** 45 minutes (build recipe and public API); kept.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning.

## Acceptance criteria against evidence

1. Unit rows — met: 15 rows in `tests/unit/test_package_list.py` cover criterion 1 (EXECUTED); failing first on `dev` (READ). One promise has no row (Finding 1).
2. Build rows — met: one row for the names and nine stops, the pre-build review's three open cases among them (EXECUTED; failing first READ).
3. Command rows — met: text, JSON, exits 1 and 2, the usage (EXECUTED).
4. Oracle and coverage — met (EXECUTED). Sound: the program runs in the guest on both binaries through the `guest` fixture; `packages_distributions()` reads `top_level.txt` with the guest's own path class and parser; `find_spec` ties each name to a module without importing it. On `dev`'s set both fail (READ; INFERRED from the code).
5. The contract — met: `tests/public_api.txt` gains `Package`, its fields and `packages`, claimed (READ). The other judge files are not verdict-bearing (`tests/harness/paths.py:303`) (READ).
6. The set — met (READ): after the rebase, zip +9,589 bytes, snapshot +19,784, starts +0.50% and +0.09%, claimed.
7. Documents — met: `test_generated_pages_are_current` and `tests/lint` green (EXECUTED).
8. The run — met: 41244515439 (relayed).

**Robustness.** The 1 MiB bound holds every `.dist-info` member, and `ZipExtFile` stops at the declared size. C0 and C1 controls, U+2028 and U+2029 are refused in every name, and a missing METADATA, Name or Version raises `ArtifactsMissing` naming the folder. The cache keys on the resolved path and `_stamp`, and a rewrite in place is read again (EXECUTED). Findings 1 and 2 are the gaps.

**Build rule (READ).** A wheel owns what `add` took, a tree's names need a claim, and `--lib` and `--file` own nothing, so `host` and the two reportlab stand-ins stay unowned, as the coverage check pins. The namespace `mpl_toolkits` is matplotlib's by claim. Builtins sit under their tree's names. The zip stays reproducible: `sorted(entries)`, `EPOCH`, names sorted.

**Public API (READ).** `__all__`, `public_api.txt`, `python-api.md` and `cli.md` agree; the JSON is `cli._write`'s sorted line. The CHANGELOG lines fit the house shape, and the newly working `packages_distributions()` has its Fixed line. No code file names a specification or `context/` path.

**Structure, one line (4a).** No row moves: two snapshotted public names (R1); one field on `_Process`, in `KEPT`, with `__init__` at its listed 84 lines (EXECUTED); no mutable, platform branch or private wasmtime API (R3 to R5); `_packages.py` 141 lines. **Not structural** stands.

**4b.** No `.github/` or `release/` line.

## Findings, most severe first

1. **Medium: a zip that cannot be read escapes as an untyped exception** (`src/wasi_python/_packages.py:84-90`, `:120-127`). The read catches only `OSError`, `BadZipFile`, `UnicodeDecodeError` and `ValueError`, but Decision 1 and the docstring promise `ArtifactsMissing` for a zip that cannot be read. Failure, EXECUTED on three one-member zips: an invalid deflate block raises `zlib.error`, compression method 99 raises `NotImplementedError`, and the encrypted flag raises `RuntimeError`. An embedder that catches `ArtifactsMissing` crashes, though the command still exits 1 through `except Exception`. Fix text: around the open and read, `except ArtifactsMissing: raise`, then `except Exception as e: raise ArtifactsMissing(f"{path} cannot be read ({e})") from None`, or name `zlib.error`, `NotImplementedError`, `RuntimeError`, `EOFError` and `lzma.LZMAError` with the two caught now. Add one parametrized row in `test_package_list.py` for the three zips, seen failing first. Evidence that closes it: that row green.
2. **Low: the cache's stamp is taken after the read, not before as `_digest` takes it** (`src/wasi_python/_packages.py:90`). `samestat` compares only device and inode. A zip rewritten in place between the read's end and this `os.stat` keeps the old list under the new stamp, and later calls never read it again. Decision 4 says the stamp is "taken as `_digest` takes it", and `_digest` stats by name beside the `fstat`, before hashing. Fix text: move `named = os.stat(path)` up beside `opened = os.fstat(fd)`, before `ZipFile(f)`. It goes into the fix commit of Finding 1.
3. **Low: no release-ledger block** (`context/release-claims.toml`). The zip grows, so every release-tier upstream group's start does too: a plain start grows +1.4 M fuel, beyond the 0.01% tolerance for a small group. `context/progress/README.md:119` asks a merged change "that changes … what one runs" to append its block, as 165 did for the same cause. The news file's `tests/checks/*` prefix would be read from git at the release, so this is belt and braces, but it is the written rule. Fix text: append `[[claim]]`, `spec = "171"`, `grows = ["tests/checks/test_v1_3_upstream_suites.py::*"]`, and a `growth` naming the 55 `top_level.txt` members and the plain and snapshot start figures.
4. **Low: the Windows box of the self-check is unticked** (the pull request's description, read from the orchestrator's copy). `Author:` names the builder sub-agent. Three boxes are ticked: seen failing first, gaps and the news file. The Windows box reads "Not yet: the run has not started". Fix text: once the run on the fix commit's head is read, tick it in one edit with the legs named.

## Constitution checks

- §4.1: no upstream patch; a recipe change only. Holds.
- §4.2, §4.8: no new input. Holds.
- §4.6: sizes and hashes recorded, no artifact in git. Holds.
- §4.9: the cache row counts opens and the goal checks count fuel. Holds.
- §4.15: the host reads an unchecked set, bounded and refused by type except for Finding 1.
- §5.6: pre-build review held; its Low closed.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Fixed in `0370affe`: other exceptions become `ArtifactsMissing`, chained; its new row failed first (READ) and passes, as do my probes (EXECUTED). Confirmed.
2. Fixed in `0370affe`: both stamps before the read (READ). Confirmed.
3. Fixed in `0370affe`: the ledger's block, in shape (EXECUTED). Confirmed.
4. Fixed: the Windows box ticked (relayed). Confirmed.

Rebase, `05206aed` (READ, range-diff): the replayed commits change only conflict context; the new commit names 167's `pdfminer` and `xarray` and re-measures.

## Verdict

Lands: at `05206aed` Findings 1 to 4 are fixed, the rebase is read, and run 41244515439 is green but for this file.
