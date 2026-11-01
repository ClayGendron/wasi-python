# Review of 174 — SVG to PNG through cairo (the first pull request, #88)

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude), a fresh sub-agent of Claude Code session 0672b924-ca3c-4b6c-91ca-f834537cb1bc; not the author
- **Reviewed:** `2ec3c1ee..557933a2`, with the specification, its pre-build review, the memo and the landing notes; then, rebased onto `dev` at `9c0d879e`, `e33d94f1`: `git range-diff` against `557933a2`, the fix commit `1d899fed` and drawsvg's commit `e33d94f1`
- **Run:** 41276016814 on `e33d94f1` (relayed): the gather and every judge shard green, all 13 windows-2025 legs included; `review` and `ci-status` red only for this file.
- **Re-ran:** (darwin arm64) at `557933a2`: the drawing file → 6 passed; lint → 14; the six tree rows → 6; the suite rule, news shape, `cairosvg-smoke` and its class → 3 passed, 1 xfailed. At `e33d94f1`, on the rebuilt set: `test_v1_3_drawing.py`, `test_drawsvg_names_what_the_set_lacks`, the verdict-bearing, news-shape, suite and ledger rules → 12 passed; `tests/lint` → 14 passed. All exit 0.
- **Box:** 45 minutes; overran by about fifteen.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning.

## Acceptance criteria against evidence

1. libpng's signature, the sweep — met (READ): the tree equals the signed tag `v1.6.59`.
2. Exact pixels — met (EXECUTED, both binaries), no libm allowance.
3. The drawing checks — met (EXECUTED); seen failing first (READ).
4. Imports, tags, constructors — held by step 60 at the build (READ).
5. The suites — met: `cairosvg-smoke` and the suite rule (EXECUTED), the rest in run 41276016814 (relayed).
6. Trees, the zip's source — met (EXECUTED): the zip's `cairosvg/*.py` equal the sdist's plus the patch, less `test_api.py`.
7. Bytes, fuel, the wheel — met (READ). `PYPI_FILE_LIMIT = 104_857_600` (`tests/harness/artifacts.py:248`) is PyPI's 100 MiB: set right.
8. The run — met: 41276016814 green but for this file (relayed).

**The departures.**

1. **pixman's constructor lines:** a recipe, not a source change. Step 39 edits meson's generated header outside the tree and refuses on either line's state; the tree check passes (EXECUTED).
2. **The CairoSVG patch:** recorded as §4.1 asks: MANIFEST's `recipe` line (EXECUTED), the CHANGELOG line, the upstream draft, the README's count of 31. A stand-in `__init__.py` would be a fork of the whole module.
3. **The non-regression suite:** reasoned in `cairosvg.toml`; spec 063 is met by the API tests (Low 4).
4. **The judge changes:** honest and narrow; none turns red to green. The pikepdf stand-in raises, so its tests fail in a named class; the zip admits `.py` under `cairosvg/` only, beside its `.pyc`; the smoke bounds guard cost, not verdicts. A release-only tinycss2 would need a wider change, since a test-source family's one normal group is its smoke group (`source_rule_errors`).

**Security** (EXECUTED in the guest). `_cffi_backend`'s `load_library` and `dlopen` raise `OSError: dlopen not implemented`; a call through a cast pointer and a read past linear memory trap; run-time callbacks raise `MemoryError`. `ffi.cast` reaches only the guest's own memory, as numpy's array interface already does.

**Licences** (READ). cairo's MPL-1.1 election with URL and SHA-256, and eight MIT-style notices; pixman's 26; CairoSVG's LGPL-3.0, pinned GPL-3.0 and facts claiming nothing; the rest their own texts. No font is added. All within §4.12. **`.github/`:** `release.yml` expects 38 trees, not 32; nothing else.

**Round 2: the rebase onto `9c0d879e` and drawsvg's lines.**

1. **The rebase.** The claim block moved to `context/release-claims/174-svg-to-png-through-cairo.toml` unchanged (EXECUTED, `diff`). Every `dev` line the diff removes is one this change replaces; #71's pandas 3.1.0, #86's drawsvg lines and #87's ledger rule stand (READ).
2. **173's check expects PNG bytes:** not a weakening. Its old expectation is false once CairoSVG ships; the new one asserts `rasterize()` returns PNG's signature, and the golden holds the pixels (`rasterize()` equals `svg2png`; three GIF frames equal the oracle's). The news file's `changed` claim and the landing notes give the reason.
3. **`cairo_native.sh`** builds zlib 1.3.2, `dev`'s pin.
4. **The wheel:** 104,677,500 bytes, 180,100 under PyPI's 104,857,600 (READ). The owner raises the wheel test's limit to the 256 MiB asked of PyPI in a pull request of its own, and holds PyPI publishing until PyPI approves: a fact, not a blocker.

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

## Constitution checks

§4.1: one patch, recorded in full. §4.12: every new text ships, within the approval. §4.15: nothing writable. §5.6: pre-build review confirmed; not structural. Pins: URL and SHA-256 for each. §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1–6. Fixed in `1d899fed` (READ). The stand-ins are verdict-bearing and `test_rules.py` agrees (EXECUTED). `LICENSES/cairosvg.txt` carries the date and `LICENSES/cffi.txt` the `malloc_closure.h` part, in the rebuilt set (EXECUTED).
7. Closed by the orchestrator: the Windows box ticked with run 41276016814.

## Verdict

Lands on `e33d94f1`: run 41276016814 is green with its Windows legs, nothing High or Medium stands, the seven Lows are closed, and the rebase and drawsvg's lines undo nothing and weaken no check.
