# How numpy's callback signatures were found and checked

- **Found** (2026-10-18) by numpy's own tests run in the guest (spec 050's drafting hunt): seven
  test groups ended in the trap `indirect call type mismatch`, at `copy.copy` of a scalar and at
  `a.dtype = …`. Narrowed to `gentype___copy__` and `array_descr_set`, each defined with fewer
  parameters than CPython passes (research memo
  `context/research/2026-10-18-numpy-and-pandas-own-tests-in-the-guest.md`, findings 3 to 5).
- **Scanned.** A scan of the linked `python.wasm` (now the judge's
  `tests/harness/callbacks.py`, spec 051, Decision 4) checks every `PyMethodDef` and `PyGetSetDef`
  entry that something references, and every single `PyMethodDef` code points at, against the
  type CPython calls it with. On the frozen set it named exactly six numpy functions (the table in
  `pr.md`) and nothing in CPython or pandas (`evidence/scan-before.txt`). The last two of the six
  were not found by any test; `scalar_input` traps the guest too.
- **Seen failing first** (EXECUTED, spec 051's build, on a set byte-identical to the frozen
  `s-0cdc7b2bd78db6f5`): each call alone traps; a control line with no such callback runs
  (`evidence/guest-before.txt`).
- **Checked** (EXECUTED, spec 051's build): with the patch carried, the scan finds nothing
  (`evidence/scan-after.txt`), each call alone runs (`evidence/guest-after.txt`), and the judge's
  golden job `tests/jobs/callbacks.py` equals the pinned native oracle's output on both binaries
  (`evidence/native.txt` is that output). The six objects' function types after the change, read
  back from objects compiled with the build's own commands, are in
  `evidence/object-types-after.txt` (spec 051's drafting runs).
- **Against `main`** (`7ed6cf7`, read by raw file 2026-10-17): the six definitions are
  unchanged; six of the seven hunks apply, and `convert_datatype.h`'s context has moved. The
  rebased `fix.patch` is made in a scratch clone when the owner asks to send.
- **Policy.** numpy's AI policy keeps the description in the owner's words, with a disclosure
  (`pr.md`, "Read first").
