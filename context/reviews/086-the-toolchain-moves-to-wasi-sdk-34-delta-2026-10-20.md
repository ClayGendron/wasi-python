# Delta review of 086: the toolchain moves to wasi-sdk 34, 2026-10-20

- **Reviewer:** a fresh agent. I wrote none of 086's code, evidence or landing notes, and none of
  its earlier reviews.
- **Under review:** `spec/086-wasi-sdk-34` at `9255b37`, on main `e8ba20a`.
- **The base of this delta:** the build review read `bd3e521` on main `3866f56`. The delta is
  everything after it, as rebased:
  - `76e6bb9`, the build review's B1 to B3 and N1;
  - `3b37fef` (was `007317b`): S5 in step 20, the zip's `_missing_stdlib_info.py` in step 70,
    two new checks;
  - `3d6029a` (was `7594cca`): `Py_HASH_ALGORITHM 3` in `tests/cpython_configure.txt`, the README
    and the CHANGELOG;
  - `7e3e181` (was `66ea09a`): 078's class `cpython-a-no-missing-stdlib-info` removed;
  - `87d2dc9`, `e3933c2`: the rebase evidence and the A/B;
  - `77d2a81`: `test_regrtest`'s class count 26 → 25;
  - `9255b37`: the landing notes.
- **Read:** every code and judge diff above; the landing notes' rebase section and For the lane;
  the `rebase/` folder; `context/progress/README.md` on fixed classes and `--retire`;
  `tests/harness/scoreboard.py` and `upstream.py` where they handle absent checks and empty
  classes; CPython 3.15.0's `configure.ac` and `Include/pyhash.h`; `gh run view 39360800335`.
- **How I ran things:** in the 086 worktree, against its own set. `build/lane.lock` was absent
  before each run. No full judge.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED**.

## Short version

S5 is right and honestly told. The zip fix is right. The A/B text matches its evidence, but for
two byte figures whose base it did not name; I fixed that in writing (L1). The sums hold.

One finding needs an answer. 086 deletes the fixed class. The project's documented rule keeps a
fixed class, with an empty list file, as a passing check. Deleting it is not a weakening. But it
makes the ABSENT line that stopped the branch dry run. So no judge shard has yet run 086's guest
on any system, Windows and Linux x86-64 included. Keeping the class empty removes that line, and
the next branch dry run can then confirm the shards before acceptance (M1).

## What I ran

- **The delta's checks, by node id** (EXECUTED; `delta-nodes.log` beside this file): 5 passed.
  They were `test_the_string_hash_is_siphash13[plain]` and `[snapshot]`,
  `test_a_missing_stdlib_module_says_why`, `test_the_guests_configure_results_are_recorded`, and
  `test_regrtest`'s class-count test.
- **The set** (EXECUTED): the worktree's `build/artifacts/SHA256SUMS` hashes to `6d362277…`.
  Every artifact verifies against it. The zip holds `_missing_stdlib_info.pyc` (4,499 bytes).
  The sizes are 41,167,079, 44,717,041 and 22,198,669 bytes, as the fast tier says.
- **The hash key** (EXECUTED; `hashprobe.py`): `hash('collide-me')`, two runs per binary.
  - The snapshot printed `siphash13 0 1455296457` both times.
  - The plain binary printed `siphash13 1 -120789301`, then `siphash13 1 -807666186`.
  - The host's CPython 3.14 with `PYTHONHASHSEED=0` gives `-5529100604879794231`. Its low 32
    bits, read as signed, are `1455296457`.
  - So anyone can compute the snapshot's string hashes off-line with a stock CPython. "Public"
    is exact.
- **Missing modules** (EXECUTED; `missprobe.py`): both binaries say "Unsupported platform for
  Windows-only standard library module 'msvcrt'" and "Unsupported platform for standard library
  module '_tkinter'", as the README now says.
- **The flags** (EXECUTED): I pulled the four lines out of the fenced block and ran each through
  `shlex.split`. Each is two words, a flag and one quoted value. None holds `!`, `$`, a backtick
  or a backslash.

## (a) S5

**Correct** (READ, EXECUTED).

- `pyhash.h` falls back to `Py_HASH_FNV` when `HAVE_ALIGNED_REQUIRED` is defined.
- `configure.ac`'s probe sets `ac_cv_aligned_required=yes` when it cannot run, as in a cross
  build. The record still holds `HAVE_ALIGNED_REQUIRED 1`, so the step 20 comment is accurate.
- The flag pins the algorithm without a patch (§4.1 untouched). `Py_HASH_SIPHASH13` is 3, which
  matches the record's new line.

**The check is meaningful.**

- It reads `sys.hash_info` at run time on both binaries and compares all four fields.
- It was seen failing on the FNV set as `fnv 32 32 64`, the exact shape a regression would give.
- Check (c) guards the configure define by its own route; it was seen failing as
  `+Py_HASH_ALGORITHM 3 (built, not recorded)` on three hosts.
- Together they catch a dropped flag at configure time and at run time.

**The "Not protected" wording is accurate.**

- The snapshot's key is all zeros (`reactor_main.c` sets `hash_seed = 0`). The probe above shows
  it is public in practice.
- With a known key, an attacker can grind keys whose 32-bit `Py_hash_t` collide off-line. The
  dict's probe sequence depends on the whole hash, so full collisions give long chains. Inserts
  and lookups then go quadratic.
- The cost is about 2³² SipHash evaluations per colliding key (INFERRED): hours of CPU for
  thousands of keys. It is paid once per release and works against every deployment of that
  snapshot. The README's "quadratic until its deadline" does not overstate it.
- The CHANGELOG's "whatever its key (PEP 456)" is fair: PEP 456 records that randomized FNV
  stayed open to collision attacks.

**L2 (low, README; for the builder).** The README says "the plain reactor draws a fresh key in
every call", and the Not protected advice says "load untrusted keys with `snapshot=False`, whose
key is fresh in every call". That is true of `run`.
- A `Session` defaults to `snapshot=True`, so it hashes with the fixed key for its whole life.
- A `Session(snapshot=False)` draws one key and keeps it for the session's life.
- Suggest "fresh in every plain call, and in every plain session". The advice then covers
  sessions too.

**N1 (note).** `int` keys (and tuples of them) collide on every CPython whatever its key, since
`hash(n)` is `n` mod 2³¹−1 with a 32-bit `Py_hash_t`. Native CPython is the same. This is not
086's subject, and the README's item rightly names string keys.

## (b) The class closure

**Justified, not a weakening** (READ, EXECUTED).

- The class excused `MiscTest.test_windows_only_module_error`. It failed only because the zip
  lacked the generated file.
- The zip now carries the file. The test passes, and the full judge reported the gap as stale
  ("passes, but tests/known_gaps.toml still lists it").
- After the removal, the test must pass inside `cpython-a`'s group. A regression would turn the
  group red, and 086's own `test_a_missing_stdlib_module_says_why` would fail as well. Protection
  rises.

**M1 (medium): the removal departs from the documented rule, and that costs the pre-acceptance
dry run.**

- `context/progress/README.md` (lines 96–100) says: "A class or trap that is fixed: its check
  passes and its gap says 'remove the gap'. **A fixed class stays, with an empty list file, as a
  passing check.** A fixed trap's `[[trap]]` entry is removed …, and its now absent check is
  retired with `--retire`."
- The harness is built for that: `upstream.class_findings` returns no finding for an empty
  class, and `upstream.py:835` names an empty class that still has a gap.
- Nine classes sit empty in `tests/upstream/expected/` today. Before 086, no class's expected
  file was ever deleted (`git log --diff-filter=D`, EXECUTED).
- **`--retire` is the right flag for the change as made.** Deleting the class makes its check
  absent. `scoreboard.accept` refuses an absent check unless it is retired, and accepts `--retire`
  only for absent checks.
- **But the documented route needs no `--retire`.** It keeps the `[[expected]]` entry, empties
  the list file, removes only the gap, and keeps the count at 26. The check then passes, which
  against main's record is a gain, not red.
- So run 39360800335's one red line, the ABSENT line, would not exist. Its judge shards
  (Windows, Ubuntu x86-64, macOS) and the same-bytes job would have run on the branch.
- The landing notes and the lane's ruling (a) do not mention this alternative. 078's case
  differed: its absent checks were trap entries, which the rule says to remove and retire.
- **Fix, either way:**
  - **Preferred:** at the wave-03 rebase, which already redoes the rebuild and the A/B, restore
    the class with an empty list file. Drop `--retire` and the count change. Dispatch the branch
    dry run, and read its judge shards and same-bytes job before acceptance. The class's reason
    can then say it is closed by 086.
  - **Or** the lane records in the landing notes why the deletion stands against
    `context/progress/README.md`'s rule. If that becomes the rule for classes too, amend the
    README's sentence, which is a judge-documentation change.

## (c) The A/B against its evidence

**They match** (READ). I compared every figure in `--accept-growth` with
`rebase/ab-097be88a.txt`, `hashcost.txt` and `layout-control.txt`.

- **The toolchain:** 66 up and 100 down, −0.365% to +2.706%, sum +0.230%. numpy-core is +2.706%
  and the compress job +1.430%.
- **The zip file:** median +0.015%, max +1.094% (`test_uncaught_errors_print_as_native[snapshot]`),
  sum −0.004%.
- **The hash flag:** 159 up and 12 down, −2.475% to +1.836%, median +0.737%, sum +0.230%.
  2678.0 − 2535.3 = 142.7 instructions per 8-character hash. Plain starts are about +1.43%.
- **The whole:** +0.460%.
- **The layout control:** `boolconv` is 1.300 G → 1.463 G (T) → 1.467 G (F). The +31.5% sits on
  the toolchain step, as claimed.

**L1 (low; fixed in `2c6c95e`).** The byte figures (+67,216, +82,856, +1,496) are not the A/B's.
They come from the fast tier on `77d2a81` against `e8ba20a`'s accepted record. The A/B, M→F on
078's base, gives python.wasm +67,218 and the snapshot +82,858; the base moved by 087's +202
bytes. The flag now names that base and gives the A/B's two numbers. It still parses as one
quoted value. For the lane already says the whole text is restated at the wave-03 rebase.

## (d) For the lane's flags

**Complete and paste-safe** (EXECUTED, READ).

- There are four flags: `--accept`, `--accept-judge`, `--accept-growth` and `--retire`.
- The seven new node ids in the claim list match the fast tier's "gained 7".
- `--accept-judge` names the checks, the record, the fixture and the closure, with its count
  change.
- No `--accept-fewer-passes` is needed, since `cpython-a` gains one. No `--partial` is needed.
- If M1 takes the preferred route, `--retire` goes and the judge text's "removed … 26 to 25"
  becomes "emptied, its gap removed".

## (e) The dry-run situation

**Agree only as a fallback** (READ; `gh run view`).

- Run 39360800335 stopped in the build shard on the ABSENT line. The two rebuilds from the pins
  are green. Every judge shard, the gather and the same-bytes job were skipped.
- AGENTS rule 2 counts a build-class specification as "built" only when its branch's red lines
  are growth lines or G7. An ABSENT line is neither, and no 086 branch run has ever reached a
  judge shard, on this base or on the first one.
- What is unconfirmed before acceptance (READ, from the memo):
  - 078's 8 MiB edges on x86-64 under clang 23. "x86-64 was not re-measured here. The dry run's
    Linux x86-64 job runs 078's checks";
  - Windows as a whole.
  - 0.1.0a4's tag run failed on Windows (AGENTS rule 6b). The hash flag and the toolchain touch
    every guest run there.
- Ruling (a) followed 078's precedent. But 078's absent lines were unavoidable, and 086's is
  avoidable (M1).
- **What I would do:** take M1's preferred route at the wave-03 rebase, so the branch dry run
  confirms the shards before acceptance.
- **If the lane keeps ruling (a),** then:
  - the post-acceptance dry run on main must pass all three systems before anything else
    build-class lands on top of 086;
  - a red Windows or x86-64 shard there means fixing or reverting 086, not accepting growth;
  - the landing notes should say so.

## (f) The cross-host sums

**They hold** (EXECUTED).

- `sha256sums-e8ba20a-macos` and `-linux-arm64` are identical and hash to `6d362277…`. The
  arm64 container log names commit `77d2a81`, exit 0, 52 hostile checks passed, and checks
  (a), (c) and the zip check passed.
- The worktree's own set is `6d362277…`, and every file verifies.
- The four `45b917c` files (macOS A, macOS B, linux/arm64, linux/amd64) are identical and hash to
  `4586ce2a…`.
- Between the two bases, only python.wasm, the snapshot, MANIFEST and regex's licence differ
  (087's regex patch). The zip does not.
- Decision 10's same-bytes trigger asks for the linux/arm64 comparison when clang-23 code
  arrives, here 087's regex. It was met.

**N2 (note).** x86-64 sameness on the `e8ba20a` base is not confirmed. The CI rebuild on
ubuntu-24.04 built green, but "the same bytes from every host" was skipped. The trigger did not
ask for x86-64. The next dry run's same-bytes job is that confirmation, on the branch if M1's
route is taken.

## Also seen

- **`76e6bb9`** (B1 to B3, N1): the trap runs are kept for both containers on `aac927dc`. They
  show nine traps on amd64, and eight plus "no trap on this host" for `c-stack-itertools-tee` on
  arm64. This matches the landing notes. B3 cites my predecessor's planted run. Answered.
- **Step 70** dies with a named path if the generated file is missing. A future CPython that
  renames it fails the build loudly, not quietly.

## Verdict

**Lands once M1 is answered.** Preferably: at the wave-03 rebase, keep 078's class with an empty
list file (no `--retire`, count 26), and read the branch dry run's judge shards and same-bytes
job before acceptance. Otherwise, the lane writes why the deletion stands against
`context/progress/README.md`'s rule and binds the post-acceptance dry run as (e) says.

- L1 is fixed (`2c6c95e`, context/ only).
- L2 is a README wording for the builder.
- N1 and N2 need nothing.

In one line: S5 is right and the public key is honestly stated. The class closure strengthens
the judge, but deleting the class instead of emptying it is what kept every judge shard from
running before acceptance.

## Confirmation (2026-10-20)

**What I confirmed:** `c4af3c4`, on main `f7511b7`. The pushed branch is
`spec/086-the-toolchain-moves-to-wasi-sdk-34`; the local one is `spec/086-wasi-sdk-34`. Read only,
apart from two unit files run while `build/lane.lock` was absent.

**M1: done, by the documented route** (READ, EXECUTED).

- `git diff f7511b7 c4af3c4` on the judge:
  - `tests/known_gaps.toml` loses the class's gap;
  - `tests/upstream/expected/cpython-a/no-missing-stdlib-info.txt` is emptied (0 bytes), not
    deleted;
  - `tests/upstream/python.toml` keeps the `[[expected]]` entry. Only its `reason` and
    `closes_with` change, and they now name spec 086;
  - `tests/unit/test_regrtest.py` does not change, so the count stays 26.
- `tests/unit/test_regrtest.py` and `tests/unit/test_upstream.py` pass: 151 tests.
- Branch run 39364304770 is at `47a853b`, the M1 commit (`gh run view`, its failed-job log kept
  as `run-39364304770-failed.log` beside this file).
  - Every shard's ratchet says "absent 0". The build-and-judge job and the same-bytes job are
    green.
  - The red jobs are macOS upstream-macos (grew 2), macOS own-guest (grew 132) and macOS
    own-embedding (grew 21).
  - Windows own-embedding is red only on 084's two rows,
    `test_the_removal_never_deletes_what_the_guest_may_not[home]` and `[private]` ("skipped
    without a known need"). These are the rows 094 fixed on main.
  - Every Ubuntu shard, the other Windows shards, the three `verify` jobs and both rebuilds are
    green.
- So the shards ran on all three systems before acceptance, which M1 asked for.
- The run predates the rebase onto `f7511b7`. Wave 03 changed no build input, and the builder's
  step 90 gives the same `SHA256SUMS`. The worktree's set is `4e0dc0cf…` (EXECUTED). The
  post-acceptance dry run (rule 6b) remains the confirmation on main.

**L2: done.** The README now says the key is fresh "in every plain call and every plain
session". It also says that a session keeps its key for its life, and that a `Session` is on the
snapshot unless `snapshot=False`. The Not protected item now says "that call's or session's".

**The claim list and the flags: complete, correct, paste-safe** (EXECUTED, READ).

- There are three flags: `--accept`, `--accept-judge` and `--accept-growth`. There is no
  `--retire`, rightly. Each parses as one flag and one quoted value, with no `!`, `$`, backtick
  or backslash.
- The claim list names 7 new checks and "a gap that now passes" (the empty class). It retires
  nothing, and `cpython-a` gains one pass.
- `--accept-judge` now says "emptied, its gap removed, its reason naming 086", which matches the
  diff.
- I checked the growth text's figures against
  `rebase/ci-same-shard-39363060501-vs-39364304770.txt` and `numpy-core-alone-b0c7a74.txt`:
  - 193 rows, 164 up and 26 down, median +0.573%, −2.530% to +1.854%, sum +0.284%;
  - numpy-core 156.190 G → 156.506 G;
  - bytes 41,102,131 → 41,169,347 (+67,216), 45,374,111 → 45,444,036 (+69,925),
    38,721,644 → 38,723,140 (+1,496).
  - All of these match.
- **N3 (note).** The same-shard file sets apart two Linux rows as "bimodal on Linux, apart":
  `cpython-b` and `cpython-archives`. The growth flag's 193-row figures exclude them without
  saying so. Nothing turns on it, since 092 compares a release record's fuel only where a darwin
  shard gave it. A clause such as "two bimodal Linux x86-64 rows set apart" would make the text
  self-contained. The lane may add it.

**The variance reading: it holds, on the evidence given** (READ, INFERRED).

- One set, one plan, two values. On 097be88a's inputs, Linux x86-64 `cpython-b` gave 301.98 G
  once and 292.48 G four times.
  - Those runs span 97be88a, 2787003, a8a3830 and set B.
  - 2787003 descends from 97be88a. Between them only `tests/harness/gather.py`, `sameness.py` and
    their unit tests change. Nothing a guest runs changes. So that swing is the runner, not a
    judge change.
- 086's high mode is near the old high mode. 086's 302.99 G is +0.33% over that set's high mode,
  301.98 G. That is consistent with the arm64 container's exact, repeated +0.231% and darwin's
  +0.18%.
- **The reading is plausible, not proven.**
  - 086 has one Linux x86-64 sample, in the high mode, and none in the low mode.
  - A fuel count that is bimodal on a fixed set and plan means the guest does different work on
    different runners. That is worth its own specification, as the builder says.
- **What would settle it:** the post-acceptance dry run gives a second sample.
  - Near 293.4 G (low mode) or near 303 G (high mode): the reading stands.
  - Anywhere else: it reopens.
  - Under 092 the lane's ratchet does not compare this Linux row, so acceptance does not wait
    on it.

**Verdict on the confirmation: lands.** M1 and L2 are done. The claim list and the flags are
right. The branch run reached every shard, and its red lines are growth lines or 084's two
Windows rows that 094 has fixed.

- N3 is optional wording.
- The variance reading stands, pending the second x86-64 sample that the dry run after
  acceptance gives.
