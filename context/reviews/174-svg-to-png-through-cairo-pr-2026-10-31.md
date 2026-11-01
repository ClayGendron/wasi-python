# Review of 174 — SVG to PNG through cairo (the first pull request, #88)

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude), a fresh sub-agent of Claude Code session 0672b924-ca3c-4b6c-91ca-f834537cb1bc; not the author
- **Reviewed:** `2ec3c1ee..557933a2` with the specification, its pre-build review, the memo and the landing notes; then each rebase by `git range-diff` and `git diff origin/dev...HEAD`: `e33d94f1` on `9c0d879e`, `bd808b50` on `da830491`, `b8c3575f`, and `812f5cba` on `1129b7ef`
- **Run:** 41317719111 on `812f5cba` (relayed): the gather and every judge shard green, all 13 windows-2025 legs and the wheel check included; red only for this file's position.
- **Re-ran:** (darwin arm64, each head's rebuilt set) the drawing file, the new tree rows, `cairosvg-smoke`, `imageio-smoke`, the callback scan, 173's drawsvg row, `tests/unit/test_callbacks.py` and the rules, each passing, with Low 8's row seen failing without the skip. At `812f5cba`: the drawing file, the callback scan and the 40 tree rows → 47 passed; `test_rules.py`, `test_callbacks.py`, `test_artifact_rules.py` → 210 passed, 1 skipped; lint → 14 passed. All exit 0.
- **Box:** 45 minutes; overran by about fifteen.

Labels: EXECUTED, I ran it; READ, I read it; INFERRED, my reasoning.

## Acceptance criteria against evidence

- **1–4.** libpng's signed tag, exact pixels on both binaries, the drawing checks seen failing first, imports and constructors held — met (EXECUTED, READ).
- **5.** The suites — met at `e33d94f1` (run 41276016814, relayed); at `bd808b50`, `imageio-smoke` (EXECUTED), the rest wait on the run.
- **6.** The zip's `cairosvg/*.py` equal the sdist's plus the patch — met (EXECUTED).
- **7.** Bytes and fuel claimed — met (READ).
- **8.** The run — met: 41317719111 (relayed).

**Rounds 1 and 2.** pixman's constructor edit is to meson's generated header outside the tree: a recipe. The CairoSVG patch is recorded as §4.1 asks (MANIFEST, CHANGELOG, draft, README's 31); a stand-in `__init__.py` would fork the module. The first judge changes are honest and narrow. `_cffi_backend` cannot `dlopen`, and a pointer call or a read past memory traps (EXECUTED). Every licence text ships, within §4.12. The claim block moved to its ledger file unchanged (EXECUTED). 173's check now expects PNG bytes: a stronger assertion, the old one false once CairoSVG ships, claimed as `changed`. `cairo_native.sh` builds `dev`'s zlib 1.3.2.

**Round 3: the rebase onto `da830491` (#89, #80, #91) and `0ced0084`.**

1. **imageio's JPEG classes go.** All three named only JPEG, which Pillow now reads; their tests pass (imageio-r 100 → 106 passes, READ; `imageio-smoke` passes, EXECUTED). They never reached `dev`, so no accepted pass is lost. `test_plugin_selection_success[.jpg]` fails for the driver's `--import-mode=importlib` (`tests/upstream/package_drive.py:272`), a cause four gaps already name. `test_imopen_extension_malformatted[.jpg]` fails in its `.cap` hint: in the guest it reaches FreeImage's ctypes and raises `OSError`, no `UserWarning` (EXECUTED), which `pytest.warns` reports as "DID NOT WARN". Both reclassifications are true, and the news file, its `[claim.judge]` and the ledger follow.
2. **The callback scan's getset skip** (`tests/harness/callbacks.py:276-277`) is name-gated: a getter at index 1 to 20 is skipped only when the name section calls it `*_rule`, `_PyPegen_*` or `skipping_*`. A binary without names skips nothing. On the set it hides one record, cairo's table at `skipping_calloc` (EXECUTED). Narrow and claimed: not a weakening (Low 8).
3. **Conflicts:** `60_link.sh`'s and `70_zip.sh`'s comments, `JOBS`, `PLATFORM_BOUND` and `own-guest-c` keep `dev`'s entries and add this change's (READ).

**Round 4: the rebases onto `badce7af` (#91) and `1129b7ef` (#81, zstd).** The range-diff changes only commit 1: `release.yml` counts 40 trees, zstd the 34th, in three places; `60_link.sh` names zstd and cairo; the README edit leaves commit 1, and `812f5cba` sets the count to 32, which equals the patch files under `recipes/patches/` and the drafts (EXECUTED: 32 and 32; `dev` has 31). The other commits are unchanged; zstd's lines stand (READ); the 40 tree rows pass (EXECUTED). The wheel is 105,155,986 bytes (relayed), under #91's 256 MiB limit: a fact.

## Findings, most severe first

1. **Low: the news file omits the harness judge changes** (`context/changes/174-svg-to-png-through-cairo.md`). The smoke bounds (`tests/harness/packages.py:1503-1504`), the `test_stand_ins` key and the zip's source rule (`tests/harness/artifacts.py:211-230`) are in the PR description and the landing notes, but not in the CHANGELOG lines. Fix text: add a "For contributors" line, "The judge: a test-source smoke group may measure 110 G and all of them 1.2 T (tinycss2's one file is 105.9 G); a family may stage test-side stand-ins (`test_stand_ins`) that name no module the zip carries; the zip may carry `cairosvg/*.py` beside its bytecode."
2. **Low: a test-side stand-in steers verdicts but is not verdict-bearing** (`tests/harness/paths.py:332-340`). A later edit of `tests/upstream/stand-ins/pikepdf.py` could make its five tests pass with no claim. Fix text: add `"tests/upstream/stand-ins/**"` to `VERDICT_BEARING`. It may also go to a later specification with a roadmap line.
3. **Low: the modified CairoSVG gives no date** (`scripts/assemble_artifacts.py:515-532`). GPL-3.0 §5(a), which LGPL-3.0 builds on, asks a modified work to say that it was modified and to give a relevant date. The notice names the patch but gives no date. Fix text: in `CAIROSVG_FACTS`, "with one recorded change, made 2026-10-31, …".
4. **Low: `packages.toml` does not say why CairoSVG's non-regression suite is not run** (`tests/upstream/packages.toml`, `[package.cairosvg]`). Fix text for its comment: "its API tests from its sdist; its non-regression suite compares with an older CairoSVG from a git submodule, not in the sdist, and is not run (the golden job checks its rendering against native cairo)".
5. **Low: stale words.**
   - The specification's Kind line still says "no carried patch".
   - Landing-notes departure 4 says a run-time `ffi.callback` of the real backend raises `SystemError`. In the guest it raises `MemoryError` ("Cannot allocate write+execute memory"), for `_cairocffi_api.ffi` and for a bare `_cffi_backend.FFI()` (EXECUTED).
   - `scripts/assemble_artifacts.py:481` and `tests/harness/paths.py:191` say "nine" MIT-style cairo files; there are eight, as the landing notes say.
   - The `upstream-pure-smoke-b` comment in `tests/release_shards.toml` still reads "253.0 G measured"; it is about 454.3 G with the five groups (201.3 G more).
6. **Low: cffi's notice could point to the PSF terms** (`scripts/assemble_artifacts.py`, the `cffi` entry). `malloc_closure.h` is compiled in, and the code comment says it is under CPython's licence. `LICENSES/cffi.txt` does not say so. Fix text: add a part, "src/c/malloc_closure.h is from CPython's `_ctypes`, under the PSF licence in LICENSES/cpython.txt."
7. **Low: the self-check's Windows box is open, with its reason** (the run has not finished). It is ticked once the run's Windows legs are read.

8. **Low: the getset skip has no unit row** (`tests/harness/callbacks.py:276-277`). The single-method skip has two (`tests/unit/test_callbacks.py:200-220`); a later edit that skipped every low getter would go unseen. Fix text: a row where a getset record's getter at index 1 is `skipping_calloc` is not counted, and the same record with `handler` there, or with names cleared, is a finding; seen failing first without the skip.

## Constitution checks

§4.1: one patch, recorded in full. §4.12: every new text ships, within the approval. §4.15: nothing writable. §5.6: pre-build review confirmed; not structural. Pins: URL and SHA-256 for each. §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

- **1–6.** Fixed in `a21d0359` (READ). The stand-ins are verdict-bearing and `test_rules.py` agrees (EXECUTED). `LICENSES/cairosvg.txt` carries the date and `LICENSES/cffi.txt` the `malloc_closure.h` part, in the rebuilt set (EXECUTED).
- **7.** Closed by the orchestrator: the Windows box ticked with run 41276016814.
- **8.** Fixed in `b8c3575f`: `test_a_getset_at_the_reactors_allocator_is_not_a_getset` skips the record at `skipping_calloc` and finds it with `handler` there or with the names cleared. With the two skip lines removed from a copy of `callbacks.py`, it fails at its first assertion (EXECUTED); with them, `tests/unit/test_callbacks.py` passes, 32 rows (EXECUTED).

## Verdict

Lands on `812f5cba`: run 41317719111 is green with its Windows legs, nothing High or Medium stands, the two judge changes of `0ced0084` are true and narrow, and the eight Lows are closed.
