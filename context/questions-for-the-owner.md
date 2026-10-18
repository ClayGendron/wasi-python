# Questions for the owner

Questions the agent could not answer alone, written down so the work could go on (the owner's
instruction of 2026-10-16: "If you do have questions, please write them down in the repo and
continue working"). Each says what waits on it and what the agent did meanwhile. An answered
question moves to another document (research, spec, review, etc.) and is deleted from this
document.

## Open

### 34. Pre-import matplotlib in the default snapshot?

- **Asked:** 2026-10-17. **Source:** `research/2026-10-17-matplotlib-on-the-current-line.md`.
- Pre-importing makes a plotting call 4.6 times cheaper (5.81 G to 1.25 G fuel) but costs every
  call +23.4 M fuel (+28% on `pass`), grows the snapshot 17.5 MB and each instance's starting
  memory 18 MiB.
- **The owner, 2026-10-17:** decide after matplotlib's first milestone (spec 023) is built,
  from the real set's measurements. The agent brings the numbers back then.

### 49. Which agent-runtime features are in 0.1.0?

- **Asked:** 2026-10-17 (overnight; the owner asked the agent to keep working to 0.1.0 and write
  questions down). **Source:** `roadmap.md`, "Agent runtime features (placement in 0.1.0 to be
  decided)".
- Decided as features, not yet placed: the cancel fix (spec 030, a defect), the tool protocol
  (specs 031 and 036), async host functions, read-only code on the import path, the filesystem provider
  (spec 032), bounded sessions.
- **The agent's recommendation:** in 0.1.0: the cancel fix, the tool protocol and the
  filesystem provider (the first two are what an agent's code calls most; the provider lets
  vfs run on this runner). After 0.1.0: async host functions (unless the tool spec needs
  them), read-only code on the import path, bounded sessions.
- **Meanwhile:** the agent specifies and builds 030, 031, 036 (031's runner part) and 032 as 0.1.0 work, and leaves the
  rest unspecified. Answering otherwise moves them out; nothing built is lost.

### 50 to 53. The tool protocol's defaults (specs 031 and 036)

- **Asked:** 2026-10-17 (overnight); revised the same day with the specifications, after 031's
  pre-build review split the runner part into 036. **Source:** spec 031, Decisions 3 and 5
  (50 to 52), and spec 036, Decisions 4 and 5 (53). Each is decided in the specifications as
  written below, so nothing waits; the owner may change any of them before or after they are
  built.
- **50. A schema keyword the runner does not check** (the tool memo's question 3): refused
  unless the tool says `validates_input=True`, reading decision 39's "validated first" strictly.
  After the review the checked subset is wider (`uniqueItems`, `prefixItems`, `multipleOf`,
  `minProperties`, `maxProperties`), so ordinary pydantic models and LangChain tools pass;
  `pattern` stays refused, since an embedder's regular expression on 1 MiB of guest text is a
  ReDoS risk. The alternative checks the subset and skips the rest silently.
- **51. The discovery frame counts toward `max_tool_calls`,** so `max_tool_calls=4` allows three
  tool calls. The alternative counts only `call` frames.
- **52. At the limit the guest gets `ToolBudgetExceeded` and runs on,** so its code can handle
  it. Spec 036 answers frames past the limit from their length alone, before any copy, so a guest
  that loops on them costs the host constant work per frame and spends only its own fuel and
  time. Decision 42 stops the run at the filesystem provider's limit instead; the two could be
  made the same.
- **53. No per-call default timeout beyond the run's deadline; at most 4 abandoned tools per
  call.** The memo proposed 30 s per call. With `deadline_s=None` a hung tool holds the run until
  `cancel`, which is the embedder's explicit choice of no limit. A tool that timed out keeps its
  thread until it ends; a call may hold 4 such threads, after which its tool calls are answered
  `timeout` at once.

### 54 to 56. The filesystem provider's choices (spec 032)

- **Asked:** 2026-10-17 (overnight). **Source:** spec 032, Decisions 3 and 8. Each is decided
  in the spec as written below, so nothing waits.
- **54. Answers or exceptions.** The provider memo proposed that a provider raise `OSError`.
  Spec 032 has it return an `Errno` and treats any exception as a fault (the guest gets `EIO`),
  following vfs's "a denial is a result" (decision 37). Keep it, or also accept a raised
  `OSError` as its errno?
- **55. The staging bound.** Bytes a provider stages are bounded by the call's `memory_bytes`,
  or 4 GiB (wasm32's own ceiling) when it is `None`, with no knob of their own (revised after
  the pre-build review, finding 7). The bound is on what the runner keeps; a provider should
  refuse a large file before reading it. Keep it, or add `max_staged_bytes`?
- **56. Names.** `max_file_calls`, `Defaults.file_calls` and `trapped == "out of file calls"`
  (after `"out of fuel"`), beside the tool protocol's `max_tool_calls`.

### 57 and 58. The zip carries what packages need (spec 033)

- **Asked:** 2026-10-17 (overnight). **Source:** spec 033. Both are decided in the spec as
  written below, so nothing waits.
- **57. May it land before "the zip's directory is read once"?** Decision 44 asks for the
  per-member cut before tier A grows the zip. Spec 033 adds only seven members and is the
  prerequisite tier A needs either way. Its pre-build review measured the cost on a prototype of
  the confirmed design:
  - a plain start: +0.54 M fuel (+0.22%);
  - a plain `import numpy`: about +1 M;
  - each snapshot call: about +0.15 M;
  - the zip and the snapshot: about +21 KB and +7 KB.

  Two costs that only programs asking for metadata pay are larger. On the snapshot, the first
  metadata lookup in a process costs about 0.36 G, of which about 0.14 G is new.
  `import numpy.testing` costs +136 M. Spec 035 cuts the lookup's directory scan (most of the
  0.36 G), but not, as far as is known, the new 0.14 G. Decided: yes.
- **58. Keep "no ctypes" in the `-V` banner?** After spec 033, `import ctypes` succeeds (a
  stand-in that names and sizes the C types and gives numpy their dtypes), but no foreign call
  can be made. Decided: keep the banner,
  and the README says what the stand-in does.

### 59 and 60. The zip's directory is read once

- **Asked:** 2026-10-17 (overnight). **Source:** `research/2026-10-17-the-zips-directory-is-read-once.md`
  ("Questions for the owner"). The agent drafts the specification with the recommended answers;
  nothing waits.
- **59.** `importlib.resources.files()` on a package in a zip on the import path would return
  our own `Traversable`, not a `zipfile.Path` (spec 035, Decision 6). For the runtime's zip the
  bytes and listings are the same, and a resource read becomes about 28 times cheaper today
  (and stops growing with the zip). For any other zip, such as one a guest puts on `sys.path`,
  a member is served by our reader only when it is stored or deflate, at most 1 MiB, with its
  local header and CRC checked; any other member (LZMA, large, corrupt, encrypted) opens through
  upstream's `zipfile.Path`, with its streaming and checks. A few differences remain and are
  documented: no `root`, `at` or `glob`; odd names' implied directories; duplicates and the empty
  name in a listing; two `files()` calls compare equal. Accept it? The agent recommends yes.
- **60.** Three stdlib functions (zipimport's directory reader, the zip resource reader, and
  `importlib.metadata`'s zip search) are replaced at run time by recipe code, with judge checks
  that their results equal upstream's. Is that a recipe under §4.1 ("a stand-in module"), or must
  it be a carried patch? The agent recommends a recipe: no upstream file changes, the zip's bytes
  do not change, and a carried patch would stay carried for good (upstream builds `_struct`
  outside the bootstrap).

### 61 and 62. scipy (spec 037)

- **Asked:** 2026-10-17 (overnight). **Source:** `specifications/037-scipy.md`, Decisions 5 and
  11. Each is decided in the specification as written below, so nothing waits.
- **61. Pre-import scipy in the default snapshot?** The scipy counterpart of question 34. Spec
  037 leaves the snapshot unchanged, so a first `import scipy.stats` on the snapshot pays
  scipy's whole import, and plain calls that never use scipy pay nothing for it. Pre-importing
  would make scipy calls much cheaper but cost every call some fuel and every instance more
  starting memory, as matplotlib's would (34: +23.4 M fuel, +17.5 MB). Decided: not
  pre-imported. The build of 037 measures the import fuel on both binaries and the snapshot's
  bytes and `pass` fuel with `scipy.stats` pre-imported (its Acceptance, criterion 5); the agent
  brings the numbers back, with 34's.
- **62. A 1.1 MB carried patch in git?** OpenBLAS's `void` convention (upstream's merged
  #6008 to #6082, backported by our script) touches 1,664 files: about 1.1 MB of text, about
  116 KB compressed (EXECUTED on the research patch), with a `Files:` line of about 49 KB, as spec
  020's rule requires. §4.6 says nothing large lives in git. Decided: it is carried, under
  `recipes/patches/OpenBLAS-0.3.34/`. It is source text, not an artifact; generating it at build
  time instead would be an unrecorded source change (§7); and it is deleted when OpenBLAS
  0.3.35 releases the convention. The alternative is to wait for 0.3.35, which question 32
  already declined.

### 63. x86_64 rebuilds with the aarch64 compiler under emulation (spec 040)

- **Asked:** 2026-10-17 (overnight). **Source:** `specifications/040-x86-64-rebuilds-the-same-bytes.md`,
  Decision 2. It is decided there as written below, so nothing waits.
- wasi-sdk's x86_64 clang orders two stack slots differently in one numpy function. The IR it is
  given is equal on both hosts; the difference starts in instruction selection (EXECUTED while
  drafting). It is not caused by anything in our recipe, and no flag that was tried removes it.
- **The question:** may "x86_64 Linux rebuilds byte-identical" (roadmap, milestone 6) be met by
  an x86_64 host that compiles with the pinned aarch64 Linux clang, run under Debian's pinned
  `qemu-aarch64`? Every other tool stays native. Five Debian packages are pinned: qemu, which is
  GPL-2.0, and four aarch64 runtime libraries. They are build tools only, and nothing of them
  ships. This holds until upstream fixes the tie, and an LLVM issue is drafted for the owner to
  send. An emulated compile is slower, so the release gate waits longer for the x86_64 rebuild
  (360-minute job limit; at 240 minutes the owner is asked before the next build-class
  specification lands, spec 040 Decision 11).
- **Decided: yes.** It fixes the whole class, not one tie. It changes no artifact byte. Without
  it the only other routes are an untraced flag or building LLVM ourselves. The alternative is
  to leave x86_64 outside the gate until a wasi-sdk release agrees across hosts, which has no
  date.

### 64. The wheel and PyPI's file-size limit

- **Asked:** 2026-10-17 (overnight). **Source:** `specifications/039-tier-a-packages.md`,
  Decision 13. Nothing in spec 039 waits on it; 0.1.0's PyPI upload does.
- **The fact:** PyPI refuses a file over 100.0 MiB unless the project's own limit is raised
  ("100.0 MiB by default; individual projects may differ … we can sometimes increase your
  limit", READ: `https://pypi.org/help/`, 2026-10-17). The `wasi-python` wheel carries the
  whole artifact set. Its three large files deflate to about 38.7 MB today (EXECUTED while
  drafting 039: `python.wasm` 7.6 MB, the snapshot 20.1 MB, the zip 10.9 MB, which is already
  deflated). Tier A adds about 16.5 MB of zip. With matplotlib M1, scipy and tier B as their
  documents estimate, the wheel reaches about 95 to 110 MB before 0.1.0 (INFERRED).
- **The question:** before 0.1.0, will you ask PyPI to raise `wasi-python`'s limit (an action on
  your account), or should the agent plan another route? The other routes each cost something
  the project has chosen against: publishing the snapshot binary as a second wheel makes one
  install two packages; a smaller default profile undoes decisions 43 and 48.
- **The agent's recommendation:** ask for the raise once spec 023 has landed, citing the
  measured wheel. Each landing until then records the wheel's size (039's landing notes do), so
  the request carries real numbers.

### 70. A red acceptance commit that reached main

- **Asked:** 2026-10-17 (overnight). **Source:** spec 029's build review
  (`reviews/029-the-landing-lane-is-guarded-2026-10-17.md`, finding 1). Numbered 70 to leave
  63 to 69 for the specifications being drafted tonight.
- Once rule 1 (an acceptance sits on the commit it judged, and carries nothing else) is in the
  judge, a bad acceptance commit on `main` makes every later run red, and `--accept` refuses a
  red run, so no forward repair exists. The lane now accepts on a detached HEAD, runs the rules on
  the two-file commit, and only then fast-forwards `main`, so this should not happen.
- **The question:** if it happens anyway, may the lane `git reset --soft` one unpushed acceptance
  commit, as a named exception to §4.14? The reviewer and the agent recommend yes, unpushed only.
  The alternative is a judge escape that accepts a failing state, which neither recommends.
- **Meanwhile:** the README says to stop and write it down here.

### 71 and 72. Writable mounts (spec 034)

- **Asked:** 2026-10-17. **Source:** `specifications/034-writable-mounts.md`, Decisions 8 and
  12. Each is decided in the specification as written below, so nothing waits.
- **71. Write back after a cancel or a deadline?** The runner holds what the guest wrote to a
  mount until close, `fsync` or the end of the run. Spec 034 hands every unclosed file to the
  provider at every ending that returns a result: an exit, a trap, out of fuel, the deadline, a
  cancel. Its reason is POSIX's: bytes a killed process wrote are still in the file. The cost is
  provider calls after a cancel or a deadline: at most min(1,024, the file calls left) whole-file
  `write`s, at most the staging bound in bytes (1 GiB by default), each counted in
  `max_file_calls`, each taking the provider's own time. So a mounted run may return after its
  deadline by the time those calls take. A cancelled `run_async` raises `CancelledError`, so its
  write-backs' refusals reach only the provider. A run that raises (Ctrl-C) writes nothing back,
  and neither does a run stopped by the interpreter's exit (a provider called then could block
  exit for ever; the pre-build review's finding 3). The other way is "a stop means stop": write
  nothing after a cancel or a deadline, and list each unwritten file in the result. Keep the
  POSIX rule? The agent and the pre-build review recommend yes, and recommend answering before
  the landing lane lands 034. vfs's design is consistent with it, though it is not the same
  rule: vfs flushes on every exit, but each flush waits only for the line's remaining time
  (vfs spec 169 §b8), so a flush after the timeout is recorded as a timeout. Under 034 a
  provider that must honour the deadline does the same by answering `ETIMEDOUT`, which the
  result records.
- **72. One buffer per open, not per path.** Two descriptors on one path in one run hold two
  buffers, and the later write-back wins; a file's unflushed writes are seen by other opens only
  after its close or `fsync` (a new file exists from its open, after the pre-build review). This is vfs's staging model, and it keeps the
  provider to whole-file calls. Sharing one buffer per path would remove these differences from a
  host folder, at the cost of reference-counted buffers. Keep one per open? The agent
  recommends yes, until a real program needs the other.

### 73. reportlab's fonts, its barcode code's licence, and its zip loader (spec 042)

- **Asked:** 2026-10-17 (overnight); part (c) added 2026-10-18 from spec 042's pre-build review
  (`reviews/042-seaborn-and-reportlab-spec-2026-10-17.md`, finding 1). **Source:**
  `specifications/042-seaborn-and-reportlab.md`, Decisions 4 and 4a. Spec 042 decides as
  written below, so nothing waits.
- **The facts.** reportlab 5.0.1's wheel ships 32 files under `reportlab/fonts/`. Sixteen are
  Type 1 programs whose notices say "Adobe Systems Incorporated. All Rights Reserved" (eight
  also under Monotype's copyright, naming Arial and Times New Roman), with no grant to
  redistribute; Dark Garden is GPL-2.0-or-later with a font exception; `callig15` has its
  author's own free-use terms; `hb-test.ttf` has no notice. Only the four Bitstream Vera files
  have approved terms. Separately, reportlab finds files inside a zip through
  `zipimporter._files`, which CPython removed in 3.13, so none of these fonts can be read from
  the zip anyway (EXECUTED in the guest and natively). The standard PDF fonts need no file, and
  DejaVu Sans from matplotlib's data covers Unicode text (EXECUTED, equal to native).
- **The barcode code (READ).** Eight modules of `reportlab/graphics/barcode/` (`__init__`,
  `code128`, `code39`, `code93`, `common`, `fourstate`, `usps`, `test`) are "Copyright (c)
  1996-2000 Tyler C. Sarna" under the **four-clause BSD licence**. It is the three-clause BSD
  plus one more obligation, the advertising clause, which says, word for word: "All advertising
  materials mentioning features or use of this software must display the following
  acknowledgement: This product includes software developed by Tyler C. Sarna." In plain terms:
  any README, release note, web page or other material that mentions barcodes (a feature of
  this code) must carry that sentence. §4.12 does not list it; decision 43's
  "reportlab (BSD)" came from reportlab's own licence file, which does not mention it. Every
  barcode and QR module imports Sarna's `__init__`, so the folder ships or stays out whole.
  The same folder holds the QR encoder, "Copyright (c) 2014 Open End AB" and "(c) 2009
  Kazuhiko Arase", MIT. Outside it, `pdfbase/_glyphlist.py` is Adobe's Glyph List,
  BSD-3-Clause. These notices are comments, which compilation drops, so spec 042 ships them in
  `LICENSES/reportlab.txt`.
- **Lesser facts, for the whole picture (READ; none names terms the wheel could supply):**
  `graphics/svgpath.py` is "derived from that used by svglib" (svglib is LGPL-3.0; the file
  carries reportlab's licence only); `lib/normalDate.py` is derived from Jeff Bauer's code "used
  with his kind permission"; `graphics/barcode/ecc200datamatrix.py` has a method "basically
  verbatim from huBarcode which is BSD licensed", with no huBarcode notice in the wheel (it is
  in the barcode folder); `platypus/paragraph.py` has a URI regex "derived from Django
  validator". In seaborn (spec 042, Decision 7), the vendored appdirs and husl are MIT and
  numpydoc's `docscrape` is BSD-2-Clause; their notices ship in `LICENSES/seaborn.txt`.
- **What spec 042 does:** leaves `reportlab/fonts/` out of the zip for good, with a judge check
  that it stays out, and carries no patch. It also leaves `reportlab/graphics/barcode/` out
  (16 members) until you answer (c), ships all three third-party notices now, and draws no
  barcode or QR code in its PDF golden.
- **The questions:** (a) keep reportlab's fonts out for good? The agent recommends yes; shipping
  any but Vera would need you to approve their terms, and Vera would also need a carried patch
  to be readable. (b) report the `_files` bug to reportlab (its users' list)? The agent
  recommends yes, as a facts sheet in your own words (question 80's form); it would draft one
  under `context/upstream/` on your word. Nothing is sent meanwhile. (c) **approve the
  four-clause BSD (Tyler C. Sarna's barcode modules), with its advertising clause,** and record
  it in §4.12? If yes, a small later change ships the barcode folder, adds a QR code and a Code
  128 barcode to the PDF golden, and puts "This product includes software developed by Tyler C.
  Sarna." in the README's barcode line and the CHANGELOG, and in any later material that
  mentions barcodes. If no, barcodes and QR codes stay out and the README says so. The agent
  leans yes: barcodes and QR codes are common in generated reports, and the obligation is one
  sentence wherever barcodes are advertised; but it is a lasting duty on the project's
  materials, so it is yours to accept.

### 80. Upstream drafts where a project refuses AI-written contributions

- **Asked:** 2026-10-17 (overnight). **Source:** spec 041's pre-build review
  (`reviews/041-files-read-by-path-from-the-zip-spec-2026-10-17.md`, findings 1 and 2).
  Numbered 80 to stay clear of the specifications being drafted tonight.
- §4.1 asks each carried patch to have "its upstream pull request drafted under
  `context/upstream/patches/` for the owner to send". networkx's `CONTRIBUTING.rst` tells AI
  assistants not to generate or suggest a PR and to have the user engage manually, and closes
  PRs that break its policy; pandas asks that AI output be reviewed and modified by the
  contributor, disclosed with harness, model and effort, and tied to a triaged issue the
  contributor claimed.
- **The question:** for such projects, should the "draft" be a facts sheet (the defect, the
  reproduction, the evidence, the patch we carry) from which the owner writes and files the
  issue or PR in their own words, rather than PR text? The agent recommends yes, and that
  spec 020's draft rules accept a facts sheet with the same six header lines.
- **Meanwhile:** spec 041's drafts are being rewritten as facts sheets that say so; nothing is
  sent.

### 81. contourpy's licence (spec 043)

- **Asked:** 2026-10-17 (overnight). **Source:** `specifications/043-matplotlib-second-milestone.md`,
  Decision 11. Numbered after 80 to stay clear of the numbers left for tonight's drafts.
- matplotlib's second milestone links contourpy 1.4.0, the C++ package every `contour` and
  `contourf` goes through. Its licence is BSD-3-Clause (its `LICENSE`, and PyPI's
  `license = "BSD-3-Clause"`). §4.12 names kiwisolver, pybind11 and cppy under BSD-3-Clause for
  matplotlib (question 35), but not contourpy; the 2026-10-16 memo's table listed it, and no
  approval named it. §4.12 says nothing is linked in under a licence the owner has not approved.
- **One older notice comes with it** (found by 043's pre-build review, finding 8). contourpy's
  `mpl2005` algorithm "came from gcntr.c, part of the GIST package"
  (`src/mpl2005_original.cpp:7`), and contourpy ships only its own `LICENSE`. GIST's notice is
  the Regents of the University of California's (1996), a BSD-style permission that asks for
  "this entire notice" in every copy. matplotlib already ships it as `LICENSE/LICENSE_YORICK`
  (for its gist/yorick colormaps), and spec 023 ships matplotlib's whole `LICENSE/` folder, so
  it is in the release; 043 keeps it there by name.
- **The question:** approve contourpy (BSD-3-Clause), shipped with its notice and with
  `LICENSE_YORICK` covering its GIST-derived code, and record it in §4.12? The agent recommends
  yes: it is the same licence as numpy's and kiwisolver's, and the Yorick notice is already
  shipped for matplotlib.
- **Meanwhile:** spec 043 is drafted and can be reviewed; it is not built until this is answered.
  qhull's licence, which 043 also ships now that qhull is linked, is already approved.

## The owner's direction for the product (2026-10-17)

"I am thinking of this more as a safe runtime for agent code. The use case is much more
powerful web agents that can access code and interact with their data and tools (either through
a file system, tools in the host program, api calls, mcp, etc.) its main use case is to work with
~/Git/repos/vfs and run on top of that where vfs manages the permissions and governance."

The code stays embedder-neutral (§4.5). The capabilities that agent use needs are built as
general features; `research/2026-10-17-the-runtime-for-agent-code.md` studies which. State
across turns is researched before any specification (`research/2026-10-17-state-across-agent-turns.md`).
