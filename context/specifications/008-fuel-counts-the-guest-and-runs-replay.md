# 008 — Fuel counts the guest only

- **Status:** draft, 2026-10-17; narrowed the same day to answer its review
  (`../reviews/008-fuel-counts-the-guest-and-runs-replay-spec-2026-10-17.md`): deterministic
  replay, its second half, moved to research
  (`../research/2026-10-17-what-a-replayable-run-needs.md`), because its review found that the
  guest observes host state the runner does not control (inode numbers, the real clock under
  `time.sleep`, clock resolution, directory order). It changes the runner and the judge's driver,
  so it is reviewed again before it is built.
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`), the judge's driver
  (`tests/harness/guest.py`), judge additions in `tests/`, `README.md`, `CHANGELOG.md`.
- **Depends on:** 006 (safe by default: this builds on its runner).
- **Research it stands on:** `../research/2026-10-17-fuel-depends-on-how-the-module-was-made.md`
  (executed: wasmtime charges one fuel per byte of the page-aligned memory image at
  instantiation when it cannot map the image copy-on-write: 42,352,641 for the snapshot and
  5,046,273 for the plain reactor on macOS when compiled in the process, none when loaded with
  `deserialize_file`; the guest's own count is identical every way). The review prototyped the
  change and measured it exact (EXECUTED: snapshot `pass` 81,903,103 compiled or loaded, a drop
  of exactly 42,352,641; plain `pass` a drop of exactly 5,046,273).

## Decisions

1. **Fuel is metered from the end of instantiation.** When a fuel cap is given (the runner's
   `fuel=`; the judge's driver always meters), the store gets `2**63 - 1` fuel before
   `linker.instantiate` and the cap right after it; `fuel_used` is `cap - store.get_fuel()` as
   before. `set_fuel` overwrites the amount (READ, wasmtime's `store.rs`). Without a cap the
   runner's engine does not meter and nothing changes. What instantiation runs is wasmtime's own
   memory fill, bounded by the artifact's size and the same for every program. `_initialize`
   (the plain reactor's constructors) runs after `instantiate` in both the runner and the driver,
   so it stays metered (the review, EXECUTED). So `fuel_used` and the cap no longer depend on how
   the module was obtained (compiled, loaded from a `.cwasm`) or on the operating system (Linux
   maps the image; macOS maps it only from a file; Windows never), and the README's "compare like
   with like" paragraph goes.
2. **No start section, checked.** Unmetered instantiation is sound only while neither binary has
   a WebAssembly start section (a start function runs guest code at instantiation). A v1.1
   check, `test_no_start_section`, asserts it on both binaries (`tests/harness/wasm.py` records
   section ids; section 8 is the start section). Neither has one today (EXECUTED). A unit test
   runs the same assertion on a WAT module with a start section, so the rule is seen to fail.
3. **The cache no longer moves fuel, checked.** A v1.4 check,
   `test_fuel_does_not_depend_on_the_module_cache`, runs `-c pass` on the snapshot, with a
   `fuel` cap and `deadline_s=None`, in two fresh processes sharing one private cache directory
   (as the existing cache probe does): a writer, which compiles and writes the `.cwasm`
   (`stats()`: compiled 1, written 1), and a loader, which loads it (`stats()`: loaded 1). Their
   `fuel_used` differ by less than 1,000,000 instructions: a fixed bound between the real
   clock's noise (the runner's snapshot `-c pass` spread 107,811 to 151,964 across sets of 15 to
   40 runs; the review, EXECUTED) and the 42.35M image charge it guards against. The judge's
   0.01% tolerance (about 8,190 instructions here) is for its own driver, whose clock is fixed;
   the runner's is real. It fails today by the charge (the research, EXECUTED). A unit test checks the
   driver's side: a WAT module with a data page and the same module without report the same fuel.
4. **The judge's figures change once.** With Decision 1 in the driver, every accepted fuel
   metric drops by its binary's instantiation charge on macOS: 42,352,641 for the snapshot,
   5,046,273 for the plain reactor. The "before" figures are re-measured on this build, not
   taken from `accepted.json`. Programs that touch inode numbers are expected not to drop by
   exactly that: wasmtime hashes them from the host's, so they move by tens of instructions
   between roots (the review, EXECUTED). The C++-exception check no longer records a fuel metric
   (spec 006's landing removed it: the runner's real clock spreads its count by about 96,000,
   wider than its 0.01% band; the review, EXECUTED), so it is not among the metrics. Any other
   metric that does not drop by exactly its charge is investigated. Accepted with
   `--accept-judge`; the 0.01% tolerance is unchanged.

## Intent

An instruction count that means one thing everywhere: the guest's own work, the same on every
host and however the module was loaded, so it can be a budget, and later a price.

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

In: the above. Out: deterministic replay (`../research/2026-10-17-what-a-replayable-run-needs.md`);
fuel as a price in any API.

## Acceptance criteria

1. The cache check was seen failing before the change; the start-section rule was seen failing on
   its WAT module.
2. `uv run pytest` is green; the judge's fuel metrics drop as Decision 4 says, listed in the
   landing notes with the exceptions named, accepted with `--accept-judge`.
3. A dry run of the release workflow passes every job.

## Landing notes

(Filled in on landing.)
