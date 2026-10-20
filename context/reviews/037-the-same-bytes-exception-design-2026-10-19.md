# Review: spec 037, Decision 17, the same-bytes exception for ducc0 (design, before build)

- **Reviewed:** `context/specifications/037-scipy.md` on `spec/037-scipy` at `7d06242`
  (rebased onto main `2968512`): Decision 17, amended criterion 3, the file-table row
  (`git show 7d06242`). Read with the research memo
  `context/research/2026-10-19-ducc0-is-not-reproducible-with-the-pinned-clang.md`, decisions.md
  "104, answered", `.github/workflows/release.yml` (build, rebuild and same-bytes jobs),
  `tests/harness/scan.py::rebuild_gate_errors`, `tests/harness/sameness.py`, `README.md`,
  `context/constitution.md` §4 and §6.
- **Reviewer:** a fresh agent (Claude Opus 5.5). It wrote none of spec 037 or its design.
- **Date:** 2026-10-19.
- **Evidence used:** the builder's objects and binaries, read only. Eleven `-O3` compiles of
  `pyduccfft.cxx` (`w-O3again-1..8.o`, `ducc1..3.o`), and two linked reactors that differ only in
  ducc0 (`mac.wasm` `2de9ee20…`, `lin.wasm` `3414b489…`). All are in the session scratchpad. Also
  `build/037/ducc0/d1.txt` and `d2.txt`, and the set in `build/artifacts/`.
- **The reviewer's tools:** written for this review only, in the scratchpad folder
  `037-exception-review/`. `wdec.py` is an independent wasm decoder with a coverage analysis.
  `objpairs.py` compares the objects pairwise. `moves.py` locates the moved `try_table`s.
  `bytes_rule.py` tests a byte-level rule. `mutant2.py` builds the counter-example. `fuel.py`
  measures fuel. Nothing was written in a git tree. No judge was run: this is a design review,
  and nothing is built yet.

## Terms

- **Cover chain.** For one instruction, the list of `try_table` blocks around it, innermost
  first, each with its catch clauses. That list decides which handler gets an exception thrown
  by the instruction.
- **Effective handler chain.** The cover chain cut after the first `catch_all` or
  `catch_all_ref` clause. Such a clause catches every exception, so the outer blocks after it can
  never see one thrown from that instruction. This is exactly what wasm EH dispatch uses.

## Summary

The exception is the right shape, and it can be made strictly tighter than the design. The
design's structural rule has a real gap. Two bodies can pass it and still handle an exception
differently: I built a valid module (wasmtime validates it) that passes the rule, yet one `call`
in it has lost its cleanup handler. The real variants meet a much stronger rule that the design
does not ask for. In every differing pair, every instruction has the same effective handler
chain. And with the `try_table` instructions removed, the bytes are identical, branch encodings
and `end`s included. Require both. The not-machine-checked line then goes away. The rest of the
findings are smaller: name uniqueness, the gate's shape, three README sentences, pinning the
decoder against llvm-objdump, and a few recording points.

## Findings, by severity

### F1, high: the structural rule accepts a variant that handles an exception differently (EXECUTED)

As written, the rule asks for four things. The same length and locals. The same instruction
sequence once `try_table`/`end` are gone and labels are absolute. The same number of
`try_table`s. The same multiset of catch lists. None of this pins where a region begins or ends.

- **Counter-example (EXECUTED, `mutant2.py`).** Take `lin.wasm`'s body of
  `ducc0::detail_fft::rfftpass<double>::make_pass`. Move the `try_table` at body offset 52 past
  the straight-line instructions that follow it, through a `call` and the `local.set` of its
  result. The result:
  - wasmtime 49 (`wt.Module.validate`) accepts the whole module;
  - the design's rule passes: same length, same locals, same normalized sequence, same catch
    multiset;
  - six instructions now have a different effective handler chain. One of them is a `call`, which
    is no longer covered by its `catch_all_ref` cleanup. If that call throws, the exception skips
    the cleanup and goes to the next handler outward.

  So "the same instructions … with the same handlers" (Decision 17's sentence) is not what the
  rule proves.
- **The real variants meet the strict rule (EXECUTED, `wdec.py`, `objpairs.py`).**
  - `mac.wasm` against `lin.wasm`: all non-code sections are byte-identical, and 8 of the 75,323
    bodies differ. In all 8, the full cover chain differs at 3 to 15 instructions. The
    **effective** handler chain is identical at **every** instruction.
  - The 55 pairs of the 11 objects: 384 differing bodies. Every one has the same normalized
    sequence and the same catch multiset. None has the same full cover chain. **All 384 have the
    same effective handler chain.**
  - No branch or catch label in any differing body targets a `try_table`'s own label.
  - All 376 `try_table`s in the differing bodies have an empty block type and exactly one clause,
    `catch_all_ref`.
- **Why the full cover chain differs but the effective one does not (EXECUTED, `moves.py`, and
  `d1.txt`/`d2.txt` at line 109175).**
  - Variant one has the shape `try_table A { try_table B { i32.const; call; local.set } …rest… }`.
  - Variant two has the shape `try_table B { i32.const; call; local.set } try_table A { …rest… }`.
  - The call is covered by B and A in the first, and by B alone in the second. B is a
    `catch_all_ref`, so A can never see the call's exception in either variant.
  - Every one of the 8 functions' moves (24 sites in `mac.wasm`/`lin.wasm`) is the same move: an
    opening goes past exactly `i32.const; call; local.set`, with no control instruction between,
    and no `end` moves.

**Asks.**
1. Replace the catch-multiset clause with a per-instruction rule. After normalization, every
   instruction must have the same effective handler chain in both bodies: each clause's kind, tag
   and absolute target, innermost first, cut after the first catch-all.
2. Refuse (fail closed on) any `br`, `br_if`, `br_table` or catch label that targets a
   `try_table`. Refuse any `try_table` whose block type is not empty.
3. Refuse the legacy EH opcodes (`try`, `catch`, `catch_all`, `delegate`, `rethrow`).
4. Include each clause's tag in what is compared. The design names only "kind and absolute
   target".
5. Delete the not-machine-checked line. Change the README wording to say that every instruction
   keeps its exception handler. The unit check must include this counter-example (a `try_table`
   moved past a `call`) as a case that fails.

### F2, medium: the rule can require byte identity outside the `try_table` instructions (EXECUTED)

"Instruction for instruction and immediate for immediate" compares decoded values. Two LEB128
encodings of one value are different bytes, and `wasm-ld` leaves relocated immediates padded to
5 bytes. With only "the same length" asked, padding could move between instructions and still
pass.

The evidence allows a far narrower rule: delete only the `try_table` instructions, keep every
`end`, and the remaining body bytes are identical. It held for all 384 differing object bodies and
all 8 differing `python.wasm` bodies (`bytes_rule.py`). Branch encodings included: the `br` depths
did not change.

**Ask.** Add the byte rule: same locals bytes, and identical byte streams once the `try_table`
instructions (not their `end`s) are deleted. Keep the absolute-label comparison too. Identical
bytes do not mean identical targets: a `br 2` resolves through the nesting, and the nesting is
what moved. Together with F1 this says exactly what the owner asked for: only where the
`try_table`s open differs, and nothing about what any instruction does.

### F3, medium: a recipe name must match exactly one function (EXECUTED)

`python.wasm`'s name section has 75,366 function names. **1,243 names occur more than once**
(static functions with the same name in different files, e.g. `init_interpreter`,
`tok_underflow_string`). The nine ducc0 names are unique today, but the design does not require
it.

**Ask.** `same_bytes.py` refuses unless each recipe name matches exactly one function in each
binary. The name section is a non-code section, so it is compared byte for byte first and the
indices agree. `test_the_same_bytes_exception_is_still_needed` asserts the same thing ("present
exactly once", not just "present").

### F4, medium: the gate's shape is not yet specified tightly enough (READ, partly INFERRED)

What holds (READ):
- Spec 057's rule stands. The published, signed and judged bytes are still only the build job's
  set, checked by the hash of its `SHA256SUMS`.
- A rebuild host's binaries are evidence only. They are never shipped.
- A malicious rebuild host could already pass today's gate by uploading the expected
  `SHA256SUMS`. That threat model is unchanged.

The new exposure is the other way round. The same-bytes job is the only independent check on a
compromised or broken **build** job. Under F1's gap, a build host could ship a ducc0 that passes
the gate but routes an exception differently. F1 and F2 close that.

Under-specified points:
1. **Where the logic lives.** Comparing "every line but two" in shell is hard for
   `rebuild_gate_errors` to pin, and hard to unit-test. Put the whole comparison in
   `scripts/compare_sets.py`: the `SHA256SUMS` lines, the binaries through `same_bytes.py`, and
   the wheel entries and the `RECORD` lines. Call it once per runner in a `for runner in …` loop.
   The gate then requires:
   - that call, with one operand under `rebuilds/` and the other not (the M18 analogue);
   - both runners in the loop;
   - no `||` or `set +e`;
   - `attest` and `publish` still needing `same-bytes`.
   Today's `cmp` rule is replaced, not kept beside the new one.
2. **Tie the rebuild's binaries to the rebuild's own `SHA256SUMS`.** The design uploads them
   separately. `compare_sets.py` must check that each rebuilt binary hashes to its line in that
   rebuild's `SHA256SUMS`. Otherwise stale or mixed-up uploads prove nothing.
3. **Simpler: no new uploads.** The rebuilt wheel, already downloaded by id, carries
   `wasi_python/artifacts/python.wasm` and the snapshot. Take the binaries from it and check them
   against the rebuild's `SHA256SUMS`. That avoids two new upload steps, two new outputs and their
   gate rules.
4. **The job's new needs.** It now needs a checkout (persist-credentials false, the run's commit)
   and setup-uv: the project rule is uv only, and the design says `uv run python`. Today
   `same-bytes` has `permissions: {}`, and `JOB_PERMISSIONS["same-bytes"]` is the empty set.
   Whether checkout works with no `contents: read` depends on the repository's visibility
   (INFERRED). Say which, and change `JOB_PERMISSIONS` if needed.
5. **Bind the recipe's toolchain inside the script too.** `same_bytes.py` should refuse the
   exception path when the recipe's `WASI_SDK_VERSION`/`LLVM_COMMIT` is not `scripts/line.conf`'s.
   The still-needed check catches this in the lane, but the release gate should not depend on it.

### F5, medium: the README says "the same bytes" in more places than the one the design names (READ)

The design amends "the README's reproducibility claim", in the singular. At least three sentences
become false:
- `README.md:121`: the snapshot "is the same bytes on every build, from any supported build host".
- `README.md:489-491`: "all three give the same artifact set, byte for byte: the same
  `SHA256SUMS`".
- `README.md:618`: "re-run all jobs: the build makes the same bytes again". A re-run's build job
  now gives a different `python.wasm`, so a different `SHA256SUMS` and different signed bytes.

Two more things belong there:
- One line telling a third party how to check a rebuild against a release
  (`uv run python scripts/compare_sets.py <release set> <their build>`). A plain `shasum -c` of
  their own build will fail.
- The CHANGELOG entry should say the same.

### F6, low: pin the decoder against the pinned llvm-objdump (EXECUTED)

A new decoder is credible when it agrees with a known tool. I checked that this is cheap:
- my decoder (about 250 lines, standard library only) found exactly the same 430,126 instruction
  boundaries as wasi-sdk 33's `llvm-objdump -d` (LLVM 22.1.0) on `w-O3again-1.o`;
- it agreed on every `try_table`, `call` and `end` mnemonic;
- it decoded all 75,323 bodies of `python.wasm` with no refusal;
- the disassembly took 2 s.

**Ask.**
1. The fixture JSON carries, for each fixture body, the instruction offsets the pinned
   `llvm-objdump` printed. The unit check asserts the decoder's boundaries equal them.
2. The still-needed check (which has the build tree and the toolchain) also compares the decoder
   with `llvm-objdump` on its three fresh objects.
3. Fail closed means more than unknown opcodes:
   - reject a LEB longer than 5 bytes (u32) or 10 bytes (s64);
   - treat a truncated read as a refusal, not a traceback;
   - require the control stack to be empty exactly at the body's last byte;
   - refuse multi-memory memargs, the legacy EH opcodes, and the `0xFE` (atomics) prefix.

### F7, low: fuel and sameness across variants (EXECUTED in part; the conclusion INFERRED)

The lane's main-tree rebuild will carry a different ducc0 variant from the builder's and the
reviewer's set. `meta.artifact` differs, but `sameness.py` does not compare it. Fuel could matter.

- Measured: four `scipy.fft` turns on `mac.wasm` and `lin.wasm`, two runs each (`fuel.py`). Runs
  of the **same** binary vary by about 0.1% (for example 20,164,089 and 20,192,604 for one
  turn). The noise hides any difference between the variants. No conclusion either way from
  timing-free fuel at this resolution.
- Static fact (EXECUTED, `moves.py`): every moved opening crosses only
  `i32.const; call; local.set`, with no branch, block or `end` between. So each `try_table` runs
  the same number of times on every path.
- INFERRED from that: the variants' fuel is identical, and so are sameness and the ratchet.

**Ask.** Say this in Decision 17, so a future sameness difference is not blamed on the exception
without evidence. Optionally, require it: under F1's normalization, each `try_table` opens and
closes in the same basic block in both bodies.

### F8, low: the still-needed check (INFERRED from EXECUTED counts)

- **Not flaky toward "identical".** Over 55 pairs, the fewest functions that differed was 4;
  never 0. From the per-function rates (each name differed in 28 to 54 of the 55 pairs), and
  assuming the functions vary independently, P(two compiles identical) is about 4e-8, and three
  identical about 1e-15.
- It can go red on a host where address-space randomization is off: some containers, or
  `setarch -R`. That is acceptable. Its message should name the host.
- **What it misses: a source or flag change under the same toolchain.**
  - A scipy bump keeps the names, so the exception would carry over to new code, still narrow
    under F1 and F2 but unrenewed.
  - So would a changed compile command, such as an optimization level.
  - Ask: the recipe also names the scipy tarball's SHA-256 and the SHA-256 of the
    `compile_commands.json` entry it was measured with. The check goes red when either moves.
- **The list (READ).** The union is 9 names over 11 compiles here, the same 9 the builder found
  in 8. A union over 32 is fine. A name that never differs costs nothing under F1 and F2. A tenth
  name appearing later fails the gate closed.

### F9, low: "three systems" is keyed by the `python.wasm` hash (READ)

`history.systems_that_passed` and the `three systems` need match accepted runs by
`python.wasm`'s SHA-256. Under the exception, each host's own rebuild has a different hash. The
need can then be met only by one set judged on three systems, the release's, never by each
host's own build. Today only darwin records exist, so nothing changes now. Write it in the
decision, so nobody later expects local Linux records to count.

### F10, info: rule 4 and the constitution (READ)

- **Allowed.**
  - §4 has no byte-for-byte hard constraint. §6.2 ("keep the build reproducible") is a
    tie-breaker, and the owner decided (question 104).
  - Rule 4 forbids editing checks, goldens, gaps or allowances **to get a pass**. This is a new,
    owner-decided judge rule, recorded and reviewed.
- **How it lands.** It needs `--accept-judge "<reason citing 104>"`, and the review must see the
  judge-hash line.
- **The `[[gap]]` question.** Not using one is right. No check fails, and criterion 3 is amended
  in the spec.
- **The MANIFEST.** It holds no binary hashes (READ, `build/artifacts/MANIFEST`), so it stays
  byte-identical across hosts. The `x-same-bytes-exception` line is generated from the recipe and
  is the same on every host.

### F11, info: simpler alternatives (INFERRED)

- **Ship one host's ducc0 object as canonical.** That needs a binary in git (forbidden) or a
  pinned prebuilt object, which is not "built from pinned sources". Recompiling until a canonical
  hash appears does not work either: 11 of 11 compiles were distinct.
- **A normalizer that rewrites the object to one canonical `try_table` order.** A binary rewrite
  of compiler output. It is more code and more risk than a checker, and the shipped bytes would
  no longer be the compiler's.
- **Running clang with ASLR off.** macOS `posix_spawn` with `_POSIX_SPAWN_DISABLE_ASLR`, or Linux
  `setarch -R`. It might make each host deterministic, but not equal across hosts: different
  clang builds have different heap layouts. A one-hour experiment for the parallel research at
  most, not for this decision.
- The exception, tightened by F1 and F2, is the narrowest correct choice.

## Verdict

**Build it once** Decision 17 is amended with:
- F1: per-instruction effective handler chains; refuse labels that target a `try_table`;
  non-empty block types and the legacy EH opcodes refused; tags compared; the
  not-machine-checked line deleted; the mutant as a failing unit case;
- F2: byte identity once the `try_table` instructions are removed;
- F3: each name matches exactly one function;
- F4: one `compare_sets.py` call per runner, held by the gate; the rebuilt binaries tied to the
  rebuild's `SHA256SUMS`, preferably taken from the rebuilt wheel; the toolchain bound in the
  script; checkout, uv and permissions stated;
- F5: the three README sentences, and a verification line.

F6 to F9 may be done during the build and checked by the build review.

One line: the exception is the right idea, but as designed it lets a moved `try` region drop a
handler; require identical effective handlers per instruction and identical bytes outside the
`try_table`s, which the real variants already satisfy, and the exception proves exactly what the
owner asked for.

---

## The implementation, reviewed against F1 to F9 (2026-10-19, later the same day)

- **Reviewed:** `spec/037-scipy` at `c098886` (Decision 17 revised), `e8573ae` (built) and
  `ad937dc` (landing notes):
  - `recipes/same_bytes_exceptions.toml`;
  - `scripts/same_bytes.py` and `scripts/compare_sets.py`;
  - `tests/unit/test_same_bytes.py` and its fixture;
  - the release workflow's `same-bytes` job;
  - `scan.rebuild_gate_errors` and `JOB_PERMISSIONS`;
  - `assemble_artifacts.py`'s `MANIFEST` line;
  - `test_the_same_bytes_exception_is_still_needed`;
  - the README and the CHANGELOG.
- **How:** I read the code, then ran probes against it. The probes import the branch's own
  scripts read-only. They run on the two reactors (`mac.wasm`, `lin.wasm`), on the set in
  `build/artifacts` with its wheel `dist/wasi_python-0.1.0a7-py3-none-any.whl`, and on sets and
  wheels I made in the scratchpad.
- **The builder's Linux binaries are gone.** Only their `SHA256SUMS` was kept
  (`build/037/linux-e8573ae/`). So the Linux variant used below is `lin.wasm`. It passes
  `same_bytes.py` against the current set's `python.wasm` (`a25dd5bf…`).
- **Unit checks:** `tests/unit/test_same_bytes.py` and `tests/unit/test_scan.py` were run in a
  `git archive` copy of `ad937dc` in the scratchpad: 247 passed.
- **Scripts:** in the scratchpad folder `037-exception-review/`: `probes.py`, `mutant3.py`,
  `setprobes.py`, `gateprobes.py`, `gateprobes2.py`, `fuel2.py`.
- Nothing was written in a git tree.

### What matches the design review (EXECUTED unless marked)

- **F1, handlers.** Rule 8 compares, at every instruction, the effective handler chain: each
  clause's kind, tag and absolute target, cut after the first catch-all.
  - Catch labels are resolved outside their `try_table`, which is correct.
  - Rule 5 refuses a label that targets a `try_table` (probe P5j) and a `try_table` with a block
    type (P5k). The decoder refuses the legacy EH opcodes (P5e).
  - I made every "move a `try_table` past a `call` and its `local.set`" mutant in the nine recipe
    functions of `lin.wasm`: 90 of them. **All 90 fail rule 8.** The first three I checked are
    modules wasmtime 49 validates.
  - A correction to my design review: its single mutant was in the overload
    `rfftpass<double>::make_pass(unsigned long, bool)`, which the recipe does not name. The finding
    stands. The 90 mutants above are all in named functions.
- **F2, bytes.** Rule 6 requires byte identity once only the `try_table` instructions are deleted.
  Rule 7 keeps the absolute-label comparison.
- **F3, names.** A name matching nothing (P6a) or two functions (P6b, `init_interpreter`) fails
  rule 3. So does a differing unnamed body (P7). The still-needed check counts each name exactly
  once.
- **F4, the release.**
  - **Rule 1, in the script.** A moved `LLVM_COMMIT` or scipy pin is refused (P10, P10b), and
    identical files need no recipe (P10c).
  - **One call per runner.** `compare_sets.py` is called once per runner, with the binaries taken
    from the rebuilt wheel.
  - **The rebuilt binaries are tied to their own `SHA256SUMS`:**
    - a rebuilt file that is not its own line fails (C3, C6);
    - a rebuild folder disagreeing with its wheel fails (C6b);
    - any other differing set file fails (C2, `MANIFEST`);
    - another wheel entry fails (C5, `runner.py`).
  - **The gate.** It catches the set compared with itself (G3), `|| true` (G4), and one runner
    dropped (G5).
  - **Spec 057 holds (READ).** `same-bytes` has no outputs and no uploads. `attest` and `publish`
    only need it. `release-assets` is still fetched by `assets-id` and checked against the build
    job's hash. What is signed and published is still only the build job's set.
- **F5, the README.** All four README places, the re-run sentence and the verify line are written
  (READ).
- **F6, the decoder.** It is pinned to the pinned `llvm-objdump` in the unit fixture and in the
  still-needed check. Overlong LEBs, out-of-range LEBs, truncation, an unbalanced end, an end
  before the last byte, a stray `else`, and relaxed-SIMD and atomics opcodes are all refused, never
  a traceback (P5a–P5i).
- **F7, fuel: now EXECUTED.** The judge's own driver (`harness.guest.run`, with its host-supplied
  clock and random) ran one program on each variant, three runs each. The program builds `fft`,
  `rfft` and `irfft` plans for `float32`, `float64` and `longdouble`, plus lengths 997 and 1536,
  so it runs the named `make_pass` functions.
  - `lin.wasm`: 3,651,499,402 three times.
  - `mac.wasm`: 3,651,499,402 twice, and 34 fewer once. That is the driver's documented residual
    of a few parts in ten million.
  - The variants' fuel is the same. The spec's "stays INFERRED" (Decision 17, fuel, and the
    landing notes' "Not measured") can say EXECUTED.
- **F8, the still-needed check.** The recipe pins the scipy tarball and the compile command's
  hash. The check goes red on any of its five conditions, and its message names
  address-randomization-off hosts (READ).
- **F9, "three systems".** Written into the decision (READ).
- **The builder's departures** are acceptable:
  - the compile-command hash is checked in the lane only, since the gate has no build tree and
    rule 1 binds the toolchain and the scipy pin there;
  - `contents: read` is stated;
  - x86_64 was not rebuilt locally. The release dry run (AGENTS.md rule 6b) is the first run of
    the changed `same-bytes` job on GitHub. Dispatch it before the next tag, as that rule already
    requires.

### New findings

**I1, medium: bytes outside the named bodies can differ and still pass (EXECUTED).**
- `same_bytes.compare` checks four things:
  - the non-code sections;
  - the number of bodies;
  - each body's content;
  - the differing named bodies under the rules.
- It never checks the code section's own framing:
  - the section's size LEB;
  - each body's size LEB;
  - where the code section sits among the other sections.
- Two wasm-valid probes:
  - P2: one unnamed function's body-size LEB padded by one byte, with the section size
    re-encoded;
  - P3: the code section's size LEB padded.
- Both **pass** with "the same bytes but where 0 named functions open a try_table".
- Through the release path, C7 (P2's `python.wasm` in a rebuilt set) **passes**
  `compare_sets.py`.
- Nothing about any instruction changes. But this is a non-exception byte difference that the gate
  lets through. The README and CHANGELOG say "every other byte of both … is the same", and the
  owner asked that nothing else differ.
- **Fix:**
  - once the rules pass, copy A, splice in B's differing named bodies (same lengths), and require
    the result to equal B byte for byte;
  - refuse `a != b` when no named body differs;
  - add a unit row for each.

**I2, low: the rebuild's `SHA256SUMS` is compared line by line, not byte by byte (EXECUTED).**
- `read_sums` uses `splitlines()` and `partition("  ")`, so its bytes beyond those lines go
  uncompared. Three cases pass:
  - a rebuild `SHA256SUMS` with CRLF line ends (C4, exception path);
  - the same with no binary differing (C4b, folder mode);
  - one with no final newline (C4c).
- The wheel check catches it only when the wheel's copy differs too.
- Before `e8573ae`, this file went through `cmp`.
- **Fix:** require the rebuild's `SHA256SUMS` bytes to equal the set's with only the exception
  lines' digests replaced, and add a unit row.

**I3, low (EXECUTED; the gap existed before this change): the compare step can be switched off
with a step-level `if:`.**
- `if: false` (G2), or any `if:` expression (G2b), on "Every rebuild is the set and its wheel the
  wheel" passes every workflow gate:
  - `rebuild_gate_errors`;
  - `release_binding_errors`;
  - `release_attestation_errors`;
  - `action_pin_errors`.
- Rule 15 covers only download, guard and check steps. A step-level `continue-on-error` is caught
  by rule 17 (G1).
- The old `cmp` step had the same gap. But the whole comparison is now this one step.
- **Fix:** refuse an `if:` on any step of `same-bytes`, or give this step rule 15's role.
- Two contrived edits also pass the gate, because it reads the call's words but not their shell
  meaning: `set_dir` pointed at a rebuild folder (G7), and the call prefixed by `echo` (G8). A
  workflow review would see either. Note them, no change needed.

### Verdict

**The exception as built: lands once I1 and I2 are fixed**, each with a unit row:
- I1: B must equal A with B's differing named bodies spliced in, and a difference with no named
  body is refused;
- I2: the rebuild's `SHA256SUMS` is compared as bytes, with only the exception lines replaced.

Both are a few lines in `same_bytes.py` and `compare_sets.py` and change no rule's intent. I3 is
recommended in the same change. F7's wording moves from INFERRED to EXECUTED with the numbers
above. Then a delta look at the diff is enough.

One line: the handler and byte rules work (90 of 90 mutants refused, fuel identical across the
variants, spec 057 intact), but padding outside the named bodies, and a reformatted `SHA256SUMS`,
still pass; close those two and it lands.
