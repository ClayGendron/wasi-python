# Review of 032, revised after landing — fd_readdir's padding (the build; a judge change)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change. I read `AGENTS.md`,
  the constitution, specification 032's "Revised after landing" notes and its Decision 6 table,
  the diff (`git show ced2145`), `masked_dirents` and `Raw.readdir` in `tests/harness/files.py`,
  the parity rows in `tests/unit/test_runner_grants.py` (lines 388-438, 571-585), the mount's
  dirent encoder (`src/wasi_python/mounts.py`, `DIRENT` and `_listing`), and the failed release
  dry run's log (`gh run view 39097514484 --log-failed`). Each claim is labelled EXECUTED, READ
  or INFERRED.
- **Reviewed:** commit `ced2145` on `spec/032-dirent-padding` in the worktree
  `../wasi_python-032b`, on main's `987012e` (spec 032 accepted). `git merge-tree --write-tree
  main HEAD` exits 0 (main has since gained two review commits only).
- **Ran (EXECUTED, darwin-arm64, set `build/sets/s-8d84b3b190fe9bce` read only).** Scripts and
  outputs are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/`
  (`judge.log`; `mut/dirent_mutant.py`, `mut/mutants.txt`, `mut/run-*.log`; `mut/headers.py`,
  `mut/headers.txt`). Mutants were applied in process by a pytest plugin (`-p dirent_mutant`) that
  wraps `struct.pack` for `mounts.DIRENT`, or `mounts._listed` for the name, so no file in the
  worktree was edited; `git status` in the worktree is clean.

## The judge

`WASI_PYTHON_ARTIFACTS=…/s-8d84b3b190fe9bce uv run pytest` in the worktree, no flags (EXECUTED,
exit 0):

- `wasi_python v1: 212/223 pass · 0 gap · 11 blocked · 0 fail (unit suite 633/641, 8 skipped)`
- `ratchet vs 789c841673: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 0 · grew 0 ·
  judge changed: tests/harness/files.py, tests/unit/test_runner_mounts.py`
- `845 passed, 19 skipped`. `ruff check src tests` and `ruff format --check src tests` clean.

All equal to the landing notes' numbers.

## Is the judge change honest?

Yes (EXECUTED and READ).

- **The failure is what the notes say.** The CI diff for `dir fd_readdir` and `plain dir
  fd_readdir` differs in one byte only: offset 21 of the `.` entry, `0x60` on the grant, `0x00` on
  the mount. Every other byte, `d_ino` included (already masked), is equal (EXECUTED, the log's
  full diff).
- **The mask is exactly the padding.** A WASI preview 1 dirent is `d_next` u64 (0-7), `d_ino` u64
  (8-15), `d_namlen` u32 (16-19), `d_type` u8 (20), padding (21-23); the mount packs it as
  `"<QQIB3x"`. `DIRENT_MASKED = (*range(8, 16), 21, 22, 23)`: `d_ino` as before, plus the three
  padding bytes. `d_next`, `d_namlen`, `d_type` and the name are never masked. `namlen` is read
  from the header copy taken before masking, so the walk is unaffected (READ).
- **Cut-short buffers.** Each index is masked only if `i < len(header)`, and the walk stops after
  a short header, as before. The parity's short rows (`readdir 10/24/25/30/50 0`) go through it
  (READ). No index outside the header is touched.
- **The reference's bytes are undefined.** wasmtime 49.0.2's release notes list GHSA-96f6-r43r-8c24
  (READ, `context/prior_art/wasmtime-v49/RELEASES.md`). At `v49.0.3`, `p1.rs:2010` builds the
  dirent from `vec![0; Dirent::guest_size()]` (READ). `evidence/padding.py 200` reproduced the
  sheet's table exactly: `..` padding `03 04 00 00` 995 of 1,000 (EXECUTED).
- **The claim about the mount got stronger, not weaker.** Before, the parity asserted the mount's
  padding equals whatever the grant's memory held, which was only true by chance. Now
  `test_a_mount_writes_zero_dirent_padding` pins it to zero over a 0xFF-filled buffer, from the
  preopen and a folder.

### Mutants (EXECUTED, `mut/mutants.txt`)

| mutant (in the mount's dirent) | parity `test_raw_calls_…` | `…deliberate_differences…` | new `…zero_dirent_padding` |
|---|---|---|---|
| none | pass | pass | pass |
| byte 21 = `0x04` (the notes' mutant) | pass | pass | **fail** |
| byte 23 = `0x01` | pass | pass | **fail** |
| byte 22 = `0x60`, `.` only | pass | pass | **fail** |
| `d_next` low bit flipped | **fail** (`dir fd_readdir`) | pass | pass |
| `d_namlen` + 1 | **fail** (`preopen fd_readdir names` cannot decode) | pass | **fail** |
| byte 19 (`d_namlen` high byte) = 1 | **fail** | pass | pass |
| `d_type` 3 ↔ 4 | **fail** (`dir fd_readdir`) | pass | pass |
| last name byte `^ 0x20` | **fail** (`dir fd_readdir`) | pass | pass |
| `d_ino` byte 8 flipped | pass (masked by design since the build) | pass | pass |

Every real field difference still turns the parity red; only padding passes it, and padding turns
the new check red.

## Findings, most severe first

**F1 (should fix or answer): the disclosure is documented as a mount difference, not as an
exposure.** The landing notes say every `fd_readdir` wasmtime serves leaks up to three bytes of
host memory per entry, on every call (the stdlib folder at `/usr/local/lib` is a wasmtime preopen,
READ `runner.py:279, 784`), reachable with no argument. The README says so only inside the mounts
list ("each `fd_readdir` entry's three padding bytes are zeros; on a grant, …"). A reader of
"Safety" → "Not protected" (README line 808) learns nothing of it. Constitution §4.10/§4.11 and
the threat model's audience (people running unreviewed code) want it there: one item such as
"until a wasmtime-py release carries wasmtime ≥ 49.0.2, `fd_readdir` on a grant, a root or the
stdlib folder copies up to three bytes of uninitialized host memory per entry into the guest
(GHSA-96f6-r43r-8c24)", and the same line under a known-issue note in the CHANGELOG if the
release carries it. Answering "the owner decides with the workaround" is acceptable if written.

**F2 (should fix): the new check never cuts inside a header.** Its docstring says "full and
cut-short buffers alike", and the `len(header) < 24` branch exists for that, but sizes 4096, 25,
50 and 80 on this tree always end on a name byte or an entry boundary: every header seen is 24
bytes (EXECUTED, `mut/headers.txt`). A size that ends inside the padding (47 → a 22-byte second
header, 48 → 23 bytes; or 22 → the first header) exercises it; the mount answers zeros there today
(EXECUTED, same file). Add 47 and 48 (or 22 and 23) to the sizes.

**F3 (minor): no removal trigger on the mask.** The mask is a judge concession to a pinned bug,
like a temporary patch. When `uv.lock` moves to a wasmtime-py on wasmtime ≥ 49.0.2, the reference
writes zeros again and the padding bytes can go back into the parity. The comment on
`DIRENT_MASKED` (or the facts sheet's "What would close it") should say so, so the judge regains
the bytes then; `context/upstream/README.md`'s closing rule covers the sheet, not the test.

**F4 (information): Linux and Windows have still not run the parity.** In run 39097514484 only
"build and judge (arm64 macOS)" failed; `verify (${{ matrix.os }})` and later jobs were skipped
(EXECUTED, `gh run view --json jobs`). The mask is host-independent, so it holds there, but other
per-system differences, if any, appear only on the next dry run. For the lane, not a condition.

**F5 (nit): `evidence/padding.py`.** `import wasmtime` is unused (its `noqa` covers E402 only;
ruff does not lint `context/`). Harmless.

## The facts sheet and the AI policy

Accurate (READ and EXECUTED):

- wasmtime-py `280ce73`: `ci/download-wasmtime.py:15` is `WASMTIME_VERSION = "v49.0.0"`, `VERSION`
  is `49.0.0`; `uv.lock` pins `wasmtime 49.0.0`. PyPI's JSON lists 48.0.0 and 49.0.0 only, 49.0.0
  uploaded 2026-09-21 (EXECUTED today).
- `RELEASES.md` at `v49.0.3`: 49.0.2 (2026-10-02) lists GHSA-96f6-r43r-8c24; 49.0.3 (2026-10-14)
  lists fifteen advisories, GHSA-m9f7-9w4p-gv38 among them.
- wasmtime's `AGENTS.md` says agents never open pull requests, never comment on or review issues
  or pull requests, and are never listed as co-authors; wasmtime-py's `CONTRIBUTING.md` names
  itself a Bytecode Alliance project. The sheet is marked "a facts sheet, not an issue", says
  nothing was posted and no agent will post, leaves the ask and its words to the owner (question
  80 exists), and says the private reporting form does not apply to public advisories. It
  respects the policy.
- "the C API … did not change in a patch release" is labelled INFERRED, correctly.

## The specification text

The Decision 6 row, the README row and the "Revised after landing" notes agree with the code and
the evidence. "Bytes 21 to 24" reads as the half-open range, consistent with "8 to 16" in the
same docstring. "the threat model (§2)" means the principal engineer's memo §2, not the
constitution's §2; worth naming the memo. The notes rightly leave the runner workaround (shadowing
`fd_readdir` for calls without mounts) to the owner and flag GHSA-m9f7-9w4p-gv38 for its own
research.

## Constitution checks

- Never weaken the judge: the change is stated with its reason, the ratchet shows it, and the
  combined claim about the mount is stronger (above). Passes.
- Tests count, never time: the new check counts bytes. Passes.
- No upstream patch; prior art read and cited, not copied. Passes.
- §5.5 (a security fix in a pinned component is a reason to release): the notes say none can be
  taken yet and prepare the ask. Passes.

## Disposition (filled in by the author, then confirmed by the reviewer)

By the implementer, 2026-10-18, in `8ed8b82` on `spec/032-dirent-padding` (rebased onto main
`1868a54` first).

1. **F1: fixed.** README *Safety* → *Not protected* now opens with the leak: until a wasmtime-py
   release carries wasmtime 49.0.2 or later, `fd_readdir` on a grant, a root or the stdlib folder
   (so on every call) copies up to three bytes of uninitialized host memory per entry into the
   guest (GHSA-96f6-r43r-8c24), a mitigation is being researched, and a mount's listings write
   zeros. The CHANGELOG's 0.1.0a4 section has the same as a known issue. The research memo was
   not touched.
2. **F2: fixed.** `test_a_mount_writes_zero_dirent_padding` also runs sizes 22, 23, 47 and 48,
   which end inside a header's padding; it passes (zeros there).
3. **F3: fixed.** The comment on `DIRENT_MASKED` and the facts sheet's "What would close it" say
   the padding returns to the parity once `uv.lock` moves to a wasmtime-py on wasmtime 49.0.2 or
   later.
4. **F4:** for the lane; no change.
5. **F5: fixed.** The unused `import wasmtime` is gone from `evidence/padding.py`.

Also: "the threat model (§2)" in the landing notes now names the principal engineer's memo. Judge
(`…/s-8d84b3b190fe9bce`): `212/223 pass · 0 fail`, `lost 0 · gained 0 · grew 0`, `845 passed, 19
skipped`; ruff clean.

## Verdict

**Lands, once F1 and F2 are fixed or answered in writing.** The judge change is honest: the mask
hides exactly the three padding bytes, every real field difference still fails the parity, and
the new check pins the mount's padding to zero and fails with each padding mutant. F3 to F5 are
minor.

## One line

The parity now ignores only the three padding bytes wasmtime 49.0.0 leaves undefined, a new check
holds the mount to zeros, and it lands after the leak is named under "Not protected" and the
check cuts a header short.
