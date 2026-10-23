# 008 — Fuel counts the guest only

- **Status:** landed, 2026-10-17. Reviewed before build (`../reviews/008-fuel-counts-the-guest-and-runs-replay-spec-2026-10-17.md`) and after (`../reviews/008-fuel-counts-the-guest-2026-10-17.md`). Deterministic replay, the first draft's second half, is in `../research/2026-10-17-what-a-replayable-run-needs.md`.
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`), the judge's driver (`tests/harness/guest.py`), judge additions in `tests/`, `README.md`, `CHANGELOG.md`.
- **Depends on:** 006 (safe by default: this builds on its runner).
- **Research it stands on:** `../research/2026-10-17-fuel-depends-on-how-the-module-was-made.md` (executed: wasmtime charges one fuel per byte of the page-aligned memory image at instantiation when it cannot map the image copy-on-write: 42,352,641 for the snapshot and 5,046,273 for the plain reactor on macOS when compiled in the process, none when loaded with `deserialize_file`; the guest's own count is identical every way). The review prototyped the change and measured it exact (EXECUTED: snapshot `pass` 81,903,103 compiled or loaded, a drop of exactly 42,352,641; plain `pass` a drop of exactly 5,046,273).

## Decisions

1. **Fuel is metered from the end of instantiation.** When a fuel cap is given (the runner's `fuel=`; the judge's driver always meters), the store gets `2**63 - 1` fuel before `linker.instantiate` and the cap right after it; `fuel_used` is `cap - store.get_fuel()` as before. `set_fuel` overwrites the amount (READ, wasmtime's `store.rs`). Without a cap the runner's engine does not meter and nothing changes. What instantiation runs is wasmtime's own memory fill, bounded by the artifact's size and the same for every program. `_initialize` (the plain reactor's constructors) runs after `instantiate` in both the runner and the driver, so it stays metered (the review, EXECUTED). So `fuel_used` and the cap no longer depend on how the module was obtained (compiled, loaded from a `.cwasm`) or on the operating system (Linux maps the image; macOS maps it only from a file; Windows never), and the README's "compare like with like" paragraph goes.
2. **No start section, checked.** Unmetered instantiation is sound only while neither binary has a WebAssembly start section (a start function runs guest code at instantiation). A v1.1 check, `test_no_start_section`, asserts it on both binaries (`tests/harness/wasm.py` records section ids; section 8 is the start section). Neither has one today (EXECUTED). A unit test runs the same assertion on a WAT module with a start section, so the rule is seen to fail.
3. **The cache no longer moves fuel, checked.** A v1.4 check, `test_fuel_does_not_depend_on_the_module_cache`, runs `-c pass` on the snapshot, with a `fuel` cap and `deadline_s=None`, in two fresh processes sharing one private cache directory (as the existing cache probe does): a writer, which compiles and writes the `.cwasm` (`stats()`: compiled 1, written 1), and a loader, which loads it (`stats()`: loaded 1). Their `fuel_used` differ by less than 1,000,000 instructions: a fixed bound between the real clock's noise (the runner's snapshot `-c pass` spread 107,811 to 151,964 across sets of 15 to 40 runs; the review, EXECUTED) and the 42.35M image charge it guards against. The judge's 0.01% tolerance (about 8,190 instructions here) is for its own driver, whose clock is fixed; the runner's is real. It fails today by the charge (the research, EXECUTED). A unit test checks the driver's side: a WAT module with a data page and the same module without report the same fuel.
4. **The judge's figures change once.** With Decision 1 in the driver, every accepted fuel metric drops by its binary's instantiation charge on macOS: 42,352,641 for the snapshot, 5,046,273 for the plain reactor. The "before" figures are re-measured on this build, not taken from `accepted.json`. Programs that touch inode numbers are expected not to drop by exactly that: wasmtime hashes them from the host's, so they move by tens of instructions between roots (the review, EXECUTED). The C++-exception check no longer records a fuel metric (spec 006's landing removed it: the runner's real clock spreads its count by about 96,000, wider than its 0.01% band; the review, EXECUTED), so it is not among the metrics. Any other metric that does not drop by exactly its charge is investigated. Accepted with `--accept-judge`; the 0.01% tolerance is unchanged.

## Intent

An instruction count that means one thing everywhere: the guest's own work, the same on every host and however the module was loaded, so it can be a budget, and later a price.

## Design

```
src/wasi_python/runner.py   fuel from after instantiation, when a cap is given
tests/harness/guest.py      the same
tests/harness/wasm.py       START_SECTION = 8
tests/checks/…              test_no_start_section (v1.1);
                            test_fuel_does_not_depend_on_the_module_cache (v1.4)
tests/unit/…                a start-section module; a data-page module's fuel
README.md, CHANGELOG.md
```

## Scope

In: the above. Out: deterministic replay (`../research/2026-10-17-what-a-replayable-run-needs.md`); fuel as a price in any API.

## Acceptance criteria

1. The cache check was seen failing before the change; the start-section rule was seen failing on its WAT module.
2. `uv run pytest` is green; the judge's fuel metrics drop as Decision 4 says, listed in the landing notes with the exceptions named, accepted with `--accept-judge`.
3. A dry run of the release workflow passes every job.

## Landing notes

Built 2026-10-17 by the author agent (commit `f6b67ac`); reviewed in `../reviews/008-fuel-counts-the-guest-2026-10-17.md`.

**Seen failing first** (EXECUTED): `test_fuel_does_not_depend_on_the_module_cache` failed with "compiled 124,252,680, loaded 81,846,084"; the unit test `test_fuel_counts_no_memory_image_copy` failed (a page of data cost its image); `test_start_section_rule_names_a_start_function` shows the rule failing on a WAT module with a start section. After the change all pass.

**The judge's metrics** (EXECUTED: the full judge against the accepted state of spec 006, the same build): every fuel metric dropped by its binary's charge, 42,352,641 (snapshot) or 5,046,273 (plain), exactly or within tens of instructions. Which few miss by tens changes from run to run (the author's run: `test_nothing_is_a_shared_library` −34, the numpy CSV job +34, the random job +17; the review's: `test_nothing_is_a_shared_library` −34 and plain `import numpy, pandas` −34): wasmtime's inode numbers are hashed from the host's, and any program that stats a file sees them, not only programs that write (Decision 4).

**The build review's fixes** (`../reviews/008-fuel-counts-the-guest-2026-10-17.md`): a failed instantiation now reports 0 fuel, not the unmetered budget (runner and driver; a v1.4 check and a unit test, the check seen failing without the fix, EXECUTED); a unit test shows `_initialize` is metered; the README says which systems were measured.

**The scoreboard fix** that lands with this spec: `accept()` kept a check's old metrics when the run recorded none, so the C++-exception check's dropped metric (spec 006) could never be accepted, and the dry run of `2519620` (https://github.com/ClayGendron/wasi_python/actions/runs/39005940343) failed its judge on it alone. Accepting growth now drops metrics a passing check no longer records; a unit test saw the old behaviour fail first. Landing uses `--accept-judge` and `--accept-growth`.

**The dry run** (EXECUTED, 2026-10-17: https://github.com/ClayGendron/wasi_python/actions/runs/39007135732, on `57913ac`, which carries specs 005, 006 and 008): **every job passed.** The build job rebuilt the reactor `4e2b2470314ee392…` and the snapshot `c6a791d3960c6398…`, the same bytes as the author's machine; the zero-patch step `4 passed`; the judge `118/122 pass · 1 gap · 3 blocked · 0 fail`, `277 passed, 8 skipped, 1 xfailed`. Verify on ubuntu-24.04, windows-2025 and macos-15: `71/74 pass · 0 gap · 3 blocked · 0 fail` each, and the installed wheel ran a program in one call to `Completed(exit_code=0, stdout=b'6\n', …)` on all three. Publish and PyPI were skipped, as a dry run must. Earlier dry runs were cancelled or failed for reasons recorded in spec 005's and 008's notes (a missing review citation; a staged file moved without its imports; the scoreboard keeping a dropped metric).
