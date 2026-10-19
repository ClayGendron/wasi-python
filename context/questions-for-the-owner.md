# Questions for the owner

Questions the agent could not answer alone, written down so the work could go on (the owner's
instruction of 2026-10-16: "If you do have questions, please write them down in the repo and
continue working"). Each says what waits on it and what the agent did meanwhile. An answered
question moves to another document (research, spec, review, etc.) and is deleted from this
document.

## Open

### 105. scipy's same-bytes exception would turn every release red at gather's G7: relax G7, or move the toolchain first?

- **Asked:** 2026-10-19. **Source:** spec 085's draft (`specifications/085-gather-checks-what-it-trusts.md` on its branch, "For the owner"), confirmed by the lane in `tests/harness/gather.py` (G7). Spec 037 cannot land until this is settled; 039, 043 and 065 land first in any case.
- **The fact:** gather's G7 requires the newest acceptance's `artifact` (the `python.wasm` the lane judged) to equal the hash of the `python.wasm` the release's build job made. Under question 104's exception, the pinned clang compiles ducc0's FFT to different bytes on every run, so the build job's `python.wasm` never equals the lane's (EXECUTED by spec 037's builder: every macOS build gave its own hash). Once 037 lands, every release and every dry run of main fails G7 until spec 086 moves the toolchain. The "three systems" need, which matches records by `python.wasm`'s hash, is met only by the release's own judged set. Spec 037 does not mention G7.
- **The question:** which way?
  - **(a) A canonical digest.** `scripts/same_bytes.py` also computes a digest of `python.wasm` that every allowed variant shares: the bytes with the named functions' `try_table` instructions deleted, plus each named function's per-instruction handler chain. The lane records it at acceptance beside the plain hash, the build job prints it, and G7 compares canonical digests while the exception holds (exact hashes otherwise). It stays as narrow as the exception: any other byte still breaks it. The snapshot varies the same way, so the set's `SHA256SUMS` differs on every build too: option (a) also needs a canonical digest of the set (spec 085, which adds the set's hash to G7, found this in its pre-build review, F2). A design amendment to spec 037, reviewed, then built; it goes away with 086.
  - **(b) Move the toolchain first.** Build spec 086 (wasi-sdk 34, which fixes the bug upstream) before 037 lands, and drop 037's exception entirely. No new rule anywhere, but every package's bytes are re-verified on every host first. scipy waits for 086's build, review and landing, and 038, 044 and 045 wait with it.
  - **(c) Relax G7 to the set's other files.** This was rejected by spec 085's author: it breaks spec 063's "gather never holds the assets" or spec 057's "ship what you built".
- **The agent's recommendation:** (a). It keeps scipy on the path you chose this morning ("exception now, fix in parallel"), its digest is exactly as narrow as the exception's rule, and it disappears with 086. Choose (b) if you would rather carry no special rule in the release path at all and accept scipy arriving later.
- **Meanwhile:** 037's build review continues. Its builder writes (a) as a design option for review, so it is ready if you choose it. Nothing else waits on this answer.

## The owner's direction for the product (2026-10-17)

"I am thinking of this more as a safe runtime for agent code. The use case is much more
powerful web agents that can access code and interact with their data and tools (either through
a file system, tools in the host program, api calls, mcp, etc.) its main use case is to work with
~/Git/repos/vfs and run on top of that where vfs manages the permissions and governance."

The code stays embedder-neutral (§4.5). The capabilities that agent use needs are built as
general features; `research/2026-10-17-the-runtime-for-agent-code.md` studies which. State
across turns is researched before any specification (`research/2026-10-17-state-across-agent-turns.md`).
