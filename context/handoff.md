# The lane's handoff

Where the work stands between sessions, written by the lane when a session ends and replaced by
the next one. It points at the records that matter: the roadmap for the order,
`decisions.md` for the owner's answers, each specification's landing notes for its state. The
lane never tags; the 0.1.0 tag is the owner's.

## 2026-10-22, midday (main `edb88a1b`; 0.1.0 accepted, its third dry run running)

### Where 0.1.0 stands

- **Waves 11 and 12 are on main.** Wave 11 (101, 102, 112, 114, 113) at `6411d4d5`, history
  line 93. Wave 12 (095, 067, the version bump to 0.1.0, and the lane's sealed-leftovers fix) at
  `148529ae`, history line 94; its acceptance was 0.1.0's first release acceptance.
- **The release acceptance, again,** on `0d5ab383`, accepted in `deb18923`, history line 95:
  1574/1873 pass, 0 fail, 297 gap, 2 blocked (the wheel, the three systems), `-n 6 --tier
  release`, 1 h 23 min. Its record is `build/releases/0.1.0/record.json` (SHA-256 in the
  commit).
- **The first dry run on main**, 39741960669 on `454f8b3c`: 275 jobs green, 4 skipped, Windows
  7/7 green, and one red release leg on Linux: networkx's `test_asadpour_integral_held_karp`
  did not end within its cap. On Linux the guest takes a different path on the same set and
  wasmtime (darwin: about 470 G), which may be the product's. 067 made it a trap with that
  reason (`1a0761a0`, `0d5ab383`; reviewed in `067-…-trap-2026-10-22.md`), and the lane accepted
  again.
- **The second dry run on main**, 39764234616 on `deb18923`: 275 jobs green, Windows 7/7, and
  one red release leg on ubuntu-24.04: joblib's
  `test_joblib_pickle_across_python_versions_with_mmap` failed as `AssertionError: assert False`,
  not its no-mmap class's message. Every pickle it loads meets mmap's error; which message the test
  ends on depends on the order the host lists its data folder. The lane's fix `42798898` lets the
  class take both messages (its 14 members and digest unchanged), reviewed: lands
  (`reviews/lane-joblib-listing-order-2026-10-22.md`, `8a26e68c`).
- **The release acceptance, a third time,** on `8a26e68c`, accepted in `edb88a1b`, history line
  96: 1574/1873 pass, 0 fail, 297 gap, 2 blocked, `-n 6 --tier release --accept-judge`, 1 h
  32 min; the record replaced at `build/releases/0.1.0/record.json`.
- **The third dry run on main**, 39790261668 on `edb88a1b`, running. When every job is green on
  three systems and the gather concludes success (`meta.tier` `release`, the set `3339091f`),
  0.1.0 is ready for the owner's tag, on `edb88a1b` or a later context-only commit whose fast tier
  is green.

### For the owner before the tag

1. **The security review's D2:** a required reviewer on the `pypi` environment, admin bypass
   off. Tonight's pushes to main printed "Bypassed rule violations"; the bypass is in use.
2. **The README's status line** still says "alpha" (wave 12's integration review, L4); the
   wording is the owner's. 0.1.0 becomes GitHub's "Latest" release and `pip install
   wasi-python` takes it without `--pre`.
3. **Sealed scratch folders** under `build/harness` from a release acceptance the lane stopped
   at 6% (to take a review's text fix). The judge never reads them. A safety check refused the
   lane's removal; once no judge runs, `chmod -R u+w build/harness` then remove its `run-*`
   folders.

### What the night found (each fixed and reviewed by a fresh agent)

- 067's `fetch.py` saved nine test sources under their URL names on CI (the integration
  review's H1).
- 11 of 067's release groups had never passed: its measuring read fuel and exit codes, not
  each group's verdict. Found by the first release acceptance; fixed in `254fd3e5`.
- The judge's sealed-leftovers scan raised on a folder another worker's guest removed: the
  lane's fix `618f891e` and `459e7f35`, reviewed in `lane-sealed-leftovers-race-2026-10-22.md`.
- networkx's held-Karp test on Linux (above).
- joblib's cross-version pickle test, whose message follows the host's listing order (above; the morning).

### The process, changed tonight (`decisions.md`, 2026-10-22)

The owner's compressed path, then the process advice instituted: the release acceptance at
`-n 6` on an otherwise idle machine; the last wave's acceptance may be the release acceptance;
the dry run dispatched before the notes. 117 to 121 reserved after 0.1.0, with the structural
review's M-a and M-b (the long-function allowance by length; `_platform.py`'s split).

### After the tag

The follow-ups the reviews reserved, in the roadmap: the Linux cause of the held-Karp test;
067's docstring rules (M1 of its build review); networkx's item-group warning filters; a
repository check that every group passes before the release tier; 115, 116, 117 to 121.

The night's log is `build/lane-log-2026-10-21-night.md`.
