# Review of 021 — `.npy` files on WASI: the first carried patch (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the specification. I read
  `AGENTS.md`, the constitution (§4.1, §4.9, §4.15, §5.2, §5.5, §5.6, §6.2, §7),
  `context/reviews/README.md` and the 020 pre-build review (for the format). Each claim is
  labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/021-npy-files-on-wasi.md` as drafted (`a456f1d`).
- **Read:** spec 020 and its applier, rules and README as built so far in the scratch clone
  (`…/scratchpad/build020/repo`: `scripts/steps/apply_patches.sh`, `common.sh`'s `patch_tree`,
  `tests/harness/scan.py` `patch_shape_errors`/`_draft_errors`/`patch_errors`,
  `recipes/patches/README.md`); `context/research/2026-10-17-numpy-npy-files-need-dup.md`;
  `context/upstream/3-numpy-npy-wasi/` (`notes.md`, `fix.patch`, `pr.md`, `evidence/`,
  `scripts/`); `scripts/steps/40_numpy.sh`, `70_zip.sh`, `80_snapshot.sh`,
  `scripts/make_stdlib_zip.py`; `recipes/reactor_main.c` (`PREIMPORT`); `tests/harness/guest.py`;
  `tests/checks/conftest.py` (`guest`); `tests/checks/test_v1_3_data_stack.py`;
  `tests/harness/scoreboard.py` (the ratchet); `context/progress/accepted.json`; numpy 2.5.2's
  `numpy/lib/_format_impl.py`, `numpy/meson.build`, `numpy/_build_utils/gitversion.py` and
  `doc/source/dev/ai_policy.rst` (from the pinned tarball).
- **Ran (EXECUTED, darwin-arm64).** The repo, the 020 clone, `build/` and `downloads/` were only
  read. The main tree's `build/` inputs were read by scripts that write only to scratch. I did
  not run `scripts/build.sh` or `uv run pytest`. Everything is under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev021/`:
  - `shasum -a 256 downloads/numpy-2.5.2.tar.gz` equals its pin (`d482d171…`).
  - `scripts/remake.sh`: the patch re-made against 2.5.2 by `git diff` of an edited copy →
    `out/0001-npy-files-without-dup.patch`.
  - The 020 clone's `apply_patches.sh` on three fresh extractions: the re-made patch, `fix.patch`'s
    first file as is, and that file with only its hunk lines renumbered (`out/apply-*.log`).
  - `scripts/rules.py`: the 020 clone's `scan.patch_errors` on a scratch root holding the patch, a
    draft, a CHANGELOG line and a README count.
  - `context/upstream/3-numpy-npy-wasi/scripts/run_in_guest.py` through `wasi_python.run` on
    today's artifacts, with a scratch compile cache (`out/guest-run.txt`).
  - `scripts/check_body.py`: a candidate body of `test_npy_files_round_trip` through the judge's
    own driver (`tests/harness/guest.py`), on both binaries, on copies of today's artifacts and on
    a patched set (`out/check-body-*.txt`).
  - `scripts/zip.sh`: step 70's exact command into scratch, with the host Python's caches kept
    out (`-X pycache_prefix`), stock and with the patched `_format_impl.py`; `scripts/zipdiff.py`.
  - `scripts/snap.sh`: step 80's exact Wizer command into scratch, on each zip.
  - `scripts/fuel.py`: fuel of four short programs on the stock and patched sets (`out/fuel*.txt`).

## What holds

- **The tarball has the file, and the fix is one place for `.npy`.** READ: in numpy 2.5.2's
  Python code, `isfileobj` is the only gate to `tofile`/`fromfile` (`_format_impl.py` lines 764,
  771, 847, and `open_memmap` at 948). No other numpy or pandas Python module calls `os.dup`,
  `.tofile(` or `np.fromfile(` (EXECUTED grep of `build/numpy-2.5.2` and `build/pandas-3.0.6`,
  tests excluded). `np.savez` and `np.load` of `.npz` go through `zipfile`'s file objects, which
  are not `io.FileIO` or `io.Buffered*`, and work today (EXECUTED, below).
- **The fix works in the real guest.** EXECUTED (`out/guest-run.txt`, today's artifacts):
  stock numpy fails `np.save`, `np.load`, `tofile` and `fromfile` with `OSError: [Errno 58] Not
  supported`, and passes 12 of 161 of the upstream test's arrays. With the patched `isfileobj`
  applied at run time: 161 of 161; Fortran, 0-d, zero-size, big-endian, unicode, object, a 3 MiB
  array, two arrays through one open file; the file's bytes equal an in-memory save's. This
  reproduces `evidence/guest-run.txt` line for line.
- **The carried patch, built into the set, works on both binaries.** EXECUTED
  (`out/check-body-patched.txt`): with the re-made patch compiled into the zip and a snapshot made
  from it, a plain, a record, a 0-d, a Fortran and an object array round-trip through `/tmp`, and
  `.npz` round-trips, on `python.wasm` and on the snapshot.
- **The snapshot really changes.** EXECUTED: `'numpy.lib._format_impl' in sys.modules` is `True`
  in the snapshot before any import, and in the plain binary after `import numpy`. So the
  snapshot holds the module's code objects. The stock Wizer re-run gives today's snapshot byte
  for byte (`a7a0a4a8…`); the patched one differs (`c7302cfd…`, 65,506,824 bytes, 90 fewer).
- **The zip changes only in that `.pyc`.** EXECUTED: step 70 re-run on stock inputs gives
  today's zip byte for byte (`2a8085a2…`). With the patched file: the same 1,751 names in the
  same order, the same metadata, and one member's bytes differ, `numpy/lib/_format_impl.pyc`
  (36,040 → 36,140 bytes; compressed 15,440 → 15,497). The zip grows 57 bytes, to 11,140,635.
- **`python.wasm` does not depend on the file.** READ: `numpy/meson.build` installs `lib` as a
  pure subdirectory (`pure_subdirs`); nothing compiles or generates from `_format_impl.py`.
  `numpy/version.py` ships in the sdist, so no git revision is read from the tree. INFERRED:
  `python.wasm` is byte for byte today's. Criterion 2 checks it.
- **The same-bytes rule can hold.** INFERRED: the patch changes one LF text file, applied by
  the 020 applier's clean `git` environment; the `.pyc` is compiled by the pinned host Python
  with `PYTHONHASHSEED=0`, which spec 012 already makes host-independent. Nothing new depends on
  the host. Only macOS was run here; criterion 4's arm64 Linux rebuild checks it.
- **The re-made patch meets every spec 020 rule.** EXECUTED (`scripts/rules.py`): no errors
  from `patch_errors` (name `0001-npy-files-without-dup.patch` matches four digits; `a/` and
  `b/` paths, no `..`; no mode, link, binary, rename or autotools line; `Files:` equals the
  touched path; a body after the header; the CHANGELOG path; the README count of 1). No name
  from `context/embedders.txt` is in the patch, `pr.md` or `notes.md` (EXECUTED grep).
- **The applier takes it cleanly.** EXECUTED: "Applied patch numpy/lib/_format_impl.py cleanly",
  no offset line, exit 0; the file keeps its tarball mtime (1786234431 before and after); a
  `diff -r` against a fresh extraction shows only the five added lines.
- **Object arrays are safe under `allow_pickle`.** INFERRED: the guest loads a file it wrote in
  the same run, inside its own root; nothing from the host is unpickled. `np.load`'s default
  stays `allow_pickle=False`. Pickled arrays never reach `isfileobj` (READ, `write_array`).

## Acceptance criteria against evidence

1. The check exists and was seen failing — **not reachable as written**: in the judge's root
   the check fails with `FileNotFoundError`, before and after the fix (Finding 1). With `/tmp`
   made, it fails with `OSError` 58 today (EXECUTED).
2. A clean build applies the patch; `python.wasm` equal; the zip differs only in the `.pyc` —
   **the zip half is shown** (EXECUTED, steps 70 and 80 re-run); the `python.wasm` half is
   INFERRED from READ code; the build log line comes from the 020 applier ("applied 0001-…").
3. Green with `--accept-judge` — **not as written**: snapshot fuel and zip bytes grow past the
   ratchet, so the run also needs `--accept-growth` (Finding 2).
4. A release dry run passes — not run; nothing found that would stop it (INFERRED).

## Findings, most severe first

1. **Medium. The check writes to `/tmp`, and the judge's root has no `/tmp`.**
   (Decision 4; `tests/harness/guest.py:134-150`)
   - The defect. The judge's driver makes a fresh, empty root with only `usr/local/lib` and the
     files a check passes. The runner's private root makes `tmp`; the judge's does not.
   - Failure. EXECUTED (`out/check-body-stock.txt` and `-patched.txt`): every case raises
     `FileNotFoundError: [Errno 44] No such file or directory: '/tmp/plain.npy'`, on both
     binaries, on the stock set and on the patched set. A builder would see it "failing first"
     for the wrong reason (criterion 1), and the fix would not turn it green.
   - Fix. Make the folder: pass `files={"/tmp/.keep": b""}` (as `_run_job` does for `/out`), or
     `os.makedirs("/tmp", exist_ok=True)` in the body (as `SQLITE_LOCK` does for `/work`). And
     say in criterion 1 that the stock failure must be `OSError` 58, by number, on the four
     arrays that take the file path (plain, record, 0-d, Fortran).

2. **Medium. The judge's fuel and bytes do move, past the ratchet.** (Decision 3; criterion 3)
   - The defect. Decision 3 infers that judge fuel should not move, and criterion 3 names only
     `--accept-judge`.
   - Failure. EXECUTED (`out/fuel.txt`, repeated exactly in `out/fuel-repeat.txt`): every
     snapshot run costs about 24,000 more instructions. `-c pass`: 81,938,099 → 81,962,284
     (+0.030%). `-c "import pandas"`: 81,961,874 → 81,985,841 (+0.029%); the stock number is
     exactly `test_snapshot_preimports_the_stack`'s accepted fuel. `FUEL_TOLERANCE` is 0.01%
     (`scoreboard.py:31`), so every snapshot check under about 242M fuel reports growth: at least
     13 accepted checks with `snapshot` in their name (EXECUTED count). The zip's `bytes` metric
     grows 57 bytes, and bytes have no tolerance (`scoreboard.py:130`). The plain binary moves
     less: `import numpy` +61,982 (0.0055%, inside the tolerance); `import pandas` −196,495.
   - Fix. Decision 3: state these numbers (fuel ≈ +24,000 per snapshot run, zip +57 bytes,
     snapshot −90 bytes, `python.wasm` 0). Criterion 3: `--accept "<reason>" --accept-judge
     "<the new check>" --accept-growth "<one carried .pyc: zip +57 bytes; snapshot fuel ≈ +24k per
     run>"`. The cause of the snapshot's constant cost was not traced (INFERRED: a different
     snapshot heap and zip layout); the build review should name it, or say it was not traced.

3. **Low. "Re-made" must mean regenerated, not renumbered.** (Decision 1; Intent)
   - The defect. `fix.patch`'s first hunk has the context line `import operator` (numpy main).
     numpy 2.5.2 has `import io` there.
   - Failure. EXECUTED: `fix.patch`'s first file fails on 2.5.2 ("while searching for: import
     operator …"); with only its hunk lines renumbered to 164 and 1029 it still fails ("patch
     failed: numpy/lib/_format_impl.py:164"). Regenerated by `git diff` of an edited 2.5.2 copy, it
     applies cleanly at 164 and 1029, and its added lines equal `fix.patch`'s (EXECUTED `diff`).
   - Fix. Decision 1: say the patch is made by editing a copy of the 2.5.2 file and running
     `git diff`; that one context line differs from upstream's (`import io` for `import operator`)
     and the `index` line differs; and that the added lines are the same. In Intent, "the exact
     change" becomes "the same added lines".

4. **Low. Where the README text goes, and what it says, is not decided; the memo is stale.**
   (Decision 5; §5.2)
   - The defect. The README has no "data-stack facts" section (READ: headings). Its platform
     paragraph (line 52) says "documented rather than patched". The README says nothing about
     `.npy` today (EXECUTED grep), although the research memo's "What it decides" says the
     README names the limit and the judge records a known gap; neither exists. The memo's
     status ("the fix waits upstream") and "Why it is not fixed here" now contradict §4.1.
   - Failure. The builder picks a place and words. A reader learns `np.save` works and assumes
     `ndarray.tofile` and `np.fromfile` do too. They still raise `OSError` 58 (EXECUTED, stock;
     the patch does not touch them). `np.load(…, mmap_mode=…)` changes its error from `OSError`
     58 to "mmap is unavailable on wasm32-wasi" (READ, `evidence/guest-memmap-probe.txt`).
   - Fix. Name the place: the paragraph after the `-V` quote (README lines 57-63). Fix the words:
     `np.save`/`np.load` of paths and open files work through a carried patch; `tofile` and
     `fromfile` on real files still fail (use `tobytes()`/`frombuffer`, or `io.BytesIO`); memory
     maps are unavailable. Add the memo to the Design: its status line says the fix is carried
     by spec 021 and sent upstream by the owner.

5. **Low. The check's set misses the chunked read loop and the open-file path.** (Decision 4)
   - The defect. The object array and `.npz` pass today (EXECUTED); they guard, they do not test
     the fix. Every array is far under `BUFFER_SIZE` (256 KiB), so the read loop runs once. User
     code often writes `with open(p, "wb") as f: np.save(f, a)`, which the set leaves out.
     "Equals" is not defined.
   - Failure. A regression in the second pass of the read loop, or in reading two arrays from
     one open file, passes the check.
   - Fix. Add one array over 256 KiB (for example 40,000 `float64`), a zero-size array, and two
     arrays saved to one open file and loaded back from it. Compare `dtype`, `shape`,
     `tolist()` and `flags.f_contiguous`. Pass `allow_pickle=True` only for the object array.

6. **Low. The spec does not say why a recipe file cannot do this.** (§4.1 "a recipe file first",
   §6.2)
   - The defect. §4.1 allows a patch only "where a source change is unavoidable". A recipe file
     could replace `numpy.lib._format_impl.isfileobj` at start-up (the run-time probe does exactly
     that). The spec does not weigh it.
   - Failure. A later reader cannot tell whether the first carried patch met §4.1's bar.
   - Fix. One sentence in Decisions: a start-up replacement would run numpy-specific code in
     the runtime's bootstrap; the plain binary does not import numpy at start, so it would need an
     import hook on every call; and it would differ from the change upstream is asked to take. The
     patch is smaller and goes away by itself when numpy releases the fix.

7. **Low. The draft's words for the owner.** (Decision 2; spec 020 Decision 2)
   - The defect, three parts. (a) Spec 020 Decision 2 says the body "is the pull request's text
     for the upstream maintainers". This draft's body is a pointer instead. 020's rule only
     checks for a non-empty body, so it passes (EXECUTED), but the prose rule is broken silently.
     (b) numpy's policy (READ, `doc/source/dev/ai_policy.rst` in the 2.5.2 tarball) also has
     "Code Quality" (do not submit code "fully or mostly generated by AI" that does not meet their
     standards) and "Copyright" (the submitter must own the code's copyright). `pr.md`'s
     disclosure says all of `fix.patch` is AI-generated, and neither `pr.md` nor `notes.md`
     names those two sections. (c) The spec writes the pointer as
     `../upstream/3-numpy-npy-wasi/pr.md`, which is relative to `context/specifications/`; from
     the draft it is `../../3-numpy-npy-wasi/pr.md`.
   - Failure. (a) The next author reads 020 and 021 as disagreeing. (b) The owner sends a fully
     AI-written change without having weighed two clauses of the policy he is sending under.
     (c) A dead link.
   - Fix. (a) Decision 2 says it departs from 020 Decision 2 where a project forbids AI-written
     descriptions, and `context/upstream/README.md` gains that sentence. (b) The draft's body
     names the Code Quality and Copyright clauses for the owner. (c) Use the path relative to the
     draft. Also: `Files:` must be bare paths; with backticks the rule fails (EXECUTED).

8. **Low. The release words.** (§5.5, §5.6)
   - The defect. §5.5 makes a *security* fix in a pinned component a reason to release. This is
     a bug fix, so a release is the owner's cadence call, not automatic (READ). Spec 020
     Decision 8 already says the §5.6 review covers every carried patch (READ). Spec 021 says
     neither.
   - Failure. None now. The first release after this lands might skip the patch in its review.
   - Fix. One line in the landing notes or the CHANGELOG entry: the next §5.6 review reads
     `0001-npy-files-without-dup.patch` and its draft. Its threat-model angle is small (INFERRED):
     the chunked path is the one `io.BytesIO` already takes; no new channel, no import, and
     `allow_pickle` stays `False` by default.

## Simpler options

- **Carry the upstream test too.** EXECUTED: `fix.patch`'s second file applies cleanly to
  2.5.2's `numpy/lib/tests/test_format.py`. Tests are not installed (`--tags
  python-runtime,devel`) and `make_stdlib_zip.py` skips `tests` folders (READ), so the artifact
  set would not change. The carried patch would then have the same added lines as the pull
  request, file for file. The spec's choice (leave it out) is also sound; either is fine, but
  say which and why.
- Nothing simpler than the patch was found for `.npy` files. The `sys.platform` test costs one
  comparison per call elsewhere, and none on the data.

## Constitution checks

- §4.1: the patch meets every 020 rule (EXECUTED) and has its upstream PR drafted; the "a recipe
  file first" weighing is missing (Finding 6). 020 must land first; the spec says so.
- §4.2: the tarball's hash was checked against its pin before use (EXECUTED).
- §4.3: `sys.platform == "wasi"` is a target test inside numpy, not a host branch in the build.
- §4.4: `python.wasm` does not change (INFERRED, READ), so the imports do not.
- §4.5: no embedder name in the patch or the PR material (EXECUTED).
- §4.6: the artifact set keeps its five members; two change (zip, snapshot).
- §4.9: the check asserts outputs and records fuel; no clock.
- §4.10: Decision 3's fuel claim was INFERRED and is wrong (Finding 2).
- §4.12: the patch carries numpy's BSD-3-Clause, as 020 Decision 10 says.
- §4.15: no default loosens; `allow_pickle` stays `False` by default.
- §5.2: README place and words, and the memo's status, are undecided (Finding 4).
- §7: the spec leaves sending the pull request to the owner, as §7 and numpy's policy require.
  Nothing on the never-do list is tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

Every finding is taken; the specification is revised in place.

1. **`/tmp`:** the program makes `/npy` first (Decision 5); criterion 1 names `OSError` 58, by
   number, and the arrays that must show it.
2. **Fuel and bytes:** Decision 4 states your numbers; criterion 3 adds `--accept-growth` with
   them; the build traces the snapshot's constant cost or names it untraced.
3. **Re-made:** Decision 1 says the patch is regenerated by `git diff` of an edited 2.5.2 copy,
   with upstream's added lines and different context and `index` lines; the Intent says "the
   same added lines".
4. **README and memo:** Decision 6 names the place (after the `-V` quote) and the words, with
   `tofile`/`fromfile` and memory maps; the memo's status is in the Design.
5. **The check's set:** adds the >256 KiB array, the zero-size array and two arrays through one
   open file; "equal" is defined; `allow_pickle` only for the object array.
6. **Why not a recipe:** Decision 2.
7. **The draft:** Decision 3 says it departs from 020 Decision 2's prose, and why; names the
   policy's disclosure, Code Quality and Copyright clauses; the link is relative to the draft;
   `Files:` bare paths; `context/upstream/README.md` gains the sentence.
8. **Release:** Decision 7: the owner's call; the next §5.6 review reads the patch and draft.

Simpler option taken: the upstream test is carried too (Decision 1), so the patch has the pull
request's added lines, file for file, and changes no artifact.

1.
2.
3.
4.
5.
6.
7.
8.

## Verdict

Revise first: make `/tmp` in the check and state the fuel and bytes growth and the
`--accept-growth` it needs (Findings 1 and 2), then fix the smaller wording findings; the patch
itself is right, applies cleanly once regenerated, and changes only the one `.pyc` and the snapshot.

One line: the fix is correct and narrow, but the check as written cannot pass in the judge's
root, and the judge's ratchet will move, so revise before building.
