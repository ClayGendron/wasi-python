# 087 — the 0.1.0a7 review's guest follow-ups

- **Status:** **built** 2026-10-19 on `2abcba0`; rebased onto main `8c07ad4` and the build review's F1 to F3 and F8 answered (*After the build review*, at the end); the full judge on the rebased commit waits for the coordinator. Built (rebased onto main `91eb2c7`; full judge 0 fail, lost 0, grew 2 bytes; dry run 39346784823, its only red lines the two growth lines; see *Landing notes*). Drafted 2026-10-19 on `spec/087-the-a7-reviews-guest-follow-ups` from main `a6dfc17`,
  with its research; reviewed before build the same day
  (`scratchpad/087-review/087-the-a7-reviews-guest-follow-ups-spec-2026-10-19.md`, for the lane to
  copy to `../reviews/`; verdict: "ready once F1 to F5 are written in, and the spec is rebased on
  main per F6", F7 to F11 as wording); **revised against all eleven findings** and rebased onto
  main `932bc00` (spec 065 landed; the README's two recursion corrections landed). The section
  "Disposition of the pre-build review" says where each went. It carries an
  upstream patch (§4.1) and changes the build recipe and the artifact set, so it was reviewed
  before it is built (constitution §5.6), and the review read the patch and its facts sheet
  (spec 020, Decision 8). A different agent reviews the build.
  **Revised 2026-10-19 (the owner, "add to existing spec"):** the 0.1.0 whole-surface security
  review's finding S3 joins the scope as Decision 10, criterion 10 and checks 7 and 8. It changes
  the runner's code (`src/wasi_python/__init__.py`, `runner.py`); the owner's coordinator directed
  that the build review cover it with the rest, in place of a pre-build review (AGENTS.md rule 8
  asks one for the runner's code; named as a departure in the landing notes).
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** **build-class** (§5.7). It adds a carried patch under `recipes/patches/` and a line to
  `scripts/assemble_artifacts.py`'s `MODIFIED`. Everything else is judge additions (`tests/`), one
  driver parameter, the runner's artifact lookup (Decision 10, `src/`), `README.md`,
  `CHANGELOG.md` and the patch's facts sheet. The guest's imports
  and exports do not change. `python.wasm` and the snapshot change by about 200 bytes each;
  `LICENSES/regex.txt` gains a line; `MANIFEST` gains the patch's hash. No line of
  `tests/public_api.txt` changes. The lane accepts it with `--accept-judge` and `--accept-growth`.
- **Depends on:** landed specifications only: 047 (regex, its step 53 and its first patch), 046
  (lxml), 071 (the 128 KiB window, `test_deep_data_limits`, the default-engine check), 020 (carried
  patches), 081 (measured runs take guest paths only). It meets 078, 086 and 065 (Decision 9).
- **Research it stands on:** the 0.1.0a7 security review
  (`../reviews/0.1.0a7-security-review-2026-10-19.md`), findings F2, F3 and F4 and its addendum;
  the README's corrected text (`e72ccf2`, `c53c05c`); `../roadmap.md`'s 087 paragraph. **The
  drafting runs** (EXECUTED 2026-10-19 on macOS arm64, wasmtime-py 49.0.0, in a session scratch
  folder outside the repository, on a fresh `cp -Rp` copy of main's set
  `s-c50ca51fae5eb55b-c9dcb5b8`, whose 33 files `shasum -c` passed). Their scripts and outputs:
  - F3: `../upstream/24-regex-timeout-ticks/` (the facts sheet `pr.md`, `fix.patch`, and
    `evidence/`);
  - F2 and F4: `../research/2026-10-19-the-a7-guest-follow-ups/`.

## Why

The 0.1.0a7 review found three things inside the guest that the README stated wrongly. The
README was corrected before the tag. This specification fixes the one that can be fixed, and
puts a check under each sentence, so none can drift back.

- **F3, regex's `timeout=` is dead above 2.147 s.** regex keeps clock ticks in `Py_ssize_t`,
  32 bits on wasm32, and wasi-libc's `CLOCKS_PER_SEC` is 10**9. A program that relies on
  `timeout=5` against a hostile pattern runs until the call's own limit. The embedder's fuel,
  deadline and cancel still hold, so this is a promise to programs, not a sandbox matter. A
  carried patch fixes it.
- **F2, `XSLTAccessControl.DENY_ALL` does not cover a stylesheet's own `xsl:import` and
  `xsl:include`.** The README now says so, and names the remedy (a parser whose resolver refuses
  every URL). Nothing checks either sentence.
- **F4, the list of recursion that still traps was incomplete.** The README now lists more rows.
  Nothing checks them. And two of them are still wrong (Decision 5).

## Decisions

### 1. F3: what is wrong, exactly (EXECUTED and READ)

- **The code** (READ, `src/_regex.c` in the pinned 2026.9.29, which equals upstream's head on its
  default branch `hg`, `0e8cb0596b`, byte for byte):
  - `decode_timeout` returns `(Py_ssize_t)(value * CLOCKS_PER_SEC)` (line 21092);
  - `check_timed_out` compares `(Py_ssize_t)(clock() - state->start_time)` with the timeout
    (line 2258);
  - `RE_State.timeout`, three parameters and nine locals carry the value as `Py_ssize_t`.
- **wasi-libc's clock** (READ, wasi-sdk 33's sysroot): `clock_t` is `long long`, and
  `CLOCKS_PER_SEC` is `((clock_t)1000000000)`. `clock()` comes from
  `libwasi-emulated-process-clocks.a`: it is `CLOCK_MONOTONIC` since a constructor ran, so it is
  wall time, where native `clock()` counts CPU time.
- **What the compiler makes of it** (EXECUTED, `llvm-objdump` on the build's own `_regex.o`,
  `evidence/decode_timeout_wasm.txt`). The conversion is `i32.trunc_sat_f64_s`. It saturates at
  `INT32_MAX`, which is 2.147483647 s of ticks. The elapsed ticks are cast to 32 bits as well, and
  a 32-bit value never exceeds `INT32_MAX`. So a saturated timeout never fires.
- **The edge is exact** (EXECUTED, the judge's driver, its clock stepping 1 ms per read;
  `evidence/f3_driver_1ms_unpatched.out`):
  - `timeout=2.147` raises `TimeoutError` after 2.149 s of the guest's clock;
  - `timeout=2.148`, `2.2`, `3`, `5`, `1e9` and `inf` run on to the 2·10**10 fuel cap.
- **Under a real clock** (EXECUTED, `wasi_python.run`, `evidence/f3_runner.out`): `timeout=2.0`
  fires after 2.0 s; `timeout=3` and `5` end at the 12 s deadline.
- **No newer regex fixes it.** 2026.9.29 is the newest release on PyPI (EXECUTED, PyPI's JSON,
  2026-10-19), and upstream's head carries the same code. No upstream issue reports it (READ,
  GitHub search for "timeout"; #321 is about CPU time, not this).
- **Upstream has the same bug natively.** On x86-64, native regex 2026.9.29 raises `TimeoutError`
  at once for `timeout=1e13`, `1e30` and `float("inf")` (EXECUTED, its own cp315 wheel in a
  linux/amd64 container, `evidence/native_x86_64.out`): the double does not fit `Py_ssize_t`, and
  `cvttsd2si` gives `INT64_MIN`. On arm64 the same values saturate and never fire (EXECUTED,
  `evidence/native_arm64.out`). On 32-bit hosts the edge is about 2,147 s (INFERRED).

### 2. F3: the carried patch, `recipes/patches/regex-2026.9.29/0002-timeout-ticks.patch`

A source change: no recipe can change a C type inside `_regex.c`. It is a patch under §4.1.

- **The change** (`../upstream/24-regex-timeout-ticks/fix.patch`, SHA-256 `9da893d0…`, 26 lines
  in and 16 out, in `src/_regex.c` only):
  - `typedef long long RE_Ticks;` beside `RE_NO_TIMEOUT`, with a comment saying why;
  - `RE_State.timeout`, `decode_timeout`'s return type, the `timeout` parameters of
    `state_init_2`, `state_init` and `pattern_subx`, and the nine `tim` locals become `RE_Ticks`;
  - `check_timed_out` casts the elapsed ticks to `RE_Ticks`;
  - `decode_timeout` returns `RE_NO_TIMEOUT` for a negative value or NaN (as today) and for one
    whose ticks reach `LLONG_MAX` (new). It converts only a value that fits.
- **Why `long long` and not `clock_t`**, as the review and the roadmap put it. On wasm32 the two
  are the same type. Upstream they are not. `clock_t` is a 32-bit `long` on Windows, where it
  would narrow today's 64-bit `Py_ssize_t` on Win64. `long long` is 64 bits everywhere. Same idea,
  safer type.
- **What neither type fixes: 32-bit glibc** (the pre-build review's F10). There `clock_t` is a
  32-bit `long` at 10**6 ticks a second, so `clock() - start_time` itself wraps past 2**31 ticks,
  about 2,147 s. A timeout above that still cannot fire there: with the patch it never fires,
  where 32-bit x86 fired at once (INFERRED). The facts sheet says so plainly.
- **Why the clamp.** Without it, a huge timeout is undefined behaviour in C (C11 6.3.1.4). With
  it, `inf` and `1e30` mean "no timeout" on every target. That fixes x86-64's immediate
  `TimeoutError` too, so the upstream pull request fixes a native bug, not only ours.
- **It applies on top of 0001** with no offset, and also to the pristine release (EXECUTED,
  `git apply --check`, both). The two patches touch different lines. The judge's patch rules
  (`patch_errors`: one plain file, no mode change) hold by construction.
- **What it does** (EXECUTED in the scratch build, `evidence/relink.txt`):
  - rebuilding `_regex.c` with 0001 alone gives the build's `_regex.o`, and relinking by step 60's
    own command gives the set's `python.wasm` (`ab78e893…`), both byte for byte. So the scratch
    build is the real one;
  - with 0002 the compile gives 0 warnings under step 53's flags, and none on the changed lines
    under `-Wall -Wextra -Wconversion -Wshorten-64-to-32`. The conversion becomes a guarded
    `i64.trunc_sat_f64_s`;
  - `python.wasm` grows by 202 bytes, to 41,099,863 (`5f8d1b29…`);
  - `timeout=2.148`, `2.2`, `3`, `4.3`, `4.4`, `5` and `9` each raise `TimeoutError` after that many
    seconds of the guest's clock; `0` at once; `1e9` runs on; `1e30`, `inf`, NaN and `-1` are
    no timeout (`evidence/f3_driver_1ms_patched.out`);
  - under the real clock, `timeout=3` and `5` fire after 3.0 and 5.0 s (`evidence/f3_runner.out`);
  - fuel does not move: plain `-c pass` is 167,481,449 and `import regex` 396,193,197 on both
    binaries (`evidence/fuel.out`).
- **Its facts sheet** is drafted at `../upstream/24-regex-timeout-ticks/pr.md`, with the six header
  lines (`Project`, `Against`, `Status`, `Title`, `Files`, `Why we carry it`). It follows question
  80's recommendation, as 0001's does: the owner writes and sends it. At build time it moves
  unchanged (`git mv`) to `../upstream/patches/regex-2026.9.29/0002-timeout-ticks.md`, and
  `fix.patch` is copied byte for byte into `recipes/patches/`. The number 24 is the next folder
  free across main and the open branches (21 to 23 are taken by 037, 065, 078 and 085; the
  pre-build review checked it); if one of them lands with 24 first, the builder renumbers.
- **The licence line.** `MODIFIED` in `scripts/assemble_artifacts.py` gains
  `"recipes/patches/regex-2026.9.29/0002-timeout-ticks.patch": "clock ticks kept in 64 bits, so
  timeout= fires past 2.147 s"`. `modified_notice` then writes a second line into
  `LICENSES/regex.txt`, as Apache-2.0 §4(b) asks (spec 047, Decision 10). A patch without a line
  already stops the build.

### 3. F3's check counts clock reads, not seconds

The judge's driver answers `clock_time_get` itself: each read advances the clock by a fixed step
(`CLOCK_STEP_NS`, 1 µs). A guest's clock is then a count of reads. regex reads it once per 256
backtracking steps. So a timeout in guest seconds is a number of operations, and the check
times nothing (AGENTS.md: tests count operations).

- **The driver gains one keyword**, `run(…, clock_step_ns: int = CLOCK_STEP_NS)`, read by its
  `clock_time_get`. The default keeps every other check's fuel. The `guest` fixture already
  passes keywords through.
- **The stated resolution follows a changed step** (the pre-build review's F9, and its
  confirmation's C1). `clock_res_get` keeps answering from `CLOCK_RESOLUTION_NS`, read at call
  time, as today. Only when `clock_step_ns` differs from the default `CLOCK_STEP_NS` do the
  realtime and monotonic clocks answer the run's step instead, so `time.get_clock_info` tells the
  truth for that run. At the default nothing changes: spec 065's guard
  `test_v1_2_portable_and_sealed.py::test_the_guest_clocks_resolution_is_the_judges`, which sets
  `CLOCK_RESOLUTION_NS` to 7,000 and 11,000 and expects to see them, stays unchanged and green,
  and `test_regrtest.py`'s comparison of the two constants still holds. The docstring says so.
- **The guest reads its clock with `time.clock_gettime_ns(time.CLOCK_MONOTONIC)`**, not
  `time.monotonic_ns()` (the pre-build review's F3). The rules check `test_no_test_reads_a_clock`
  flags `time.monotonic(_ns)` in any line under `tests/checks` and `tests/unit`, strings included,
  and editing it would weaken the judge. The other spelling reads the same clock: the review ran
  check 1 with it and measured the same 2 ms step and the same verdicts (EXECUTED by the review,
  `check1.out`). The research program `evidence/f3_check.py` keeps the first spelling: it lives
  under `context/`, which the scanner does not read.
- **The check runs at 2 ms per read**, so 3 s of guest clock is 1,500 reads, about 384,000
  backtracking steps. The program (EXECUTED as written, `evidence/f3_check.py`,
  `evidence/f3_check.out`) searches `(a|aa)+$` in `"a" * 20 + "!"`, which takes 4.658 s of guest
  clock to fail, once per timeout:

  | `timeout=` | released set (0001 only) | with 0002 |
  |---|---|---|
  | `0` | `TimeoutError` at once | the same |
  | `2.0` | `TimeoutError`, 2.004 s | the same |
  | `3` | **runs to the end, 4.658 s** | **`TimeoutError`, 3.004 s** |
  | `1e9` | runs to the end | the same |
  | `1e13`, `inf` | runs to the end (saturated) | runs to the end, no clock read (no timeout) |

  The whole program takes 1,037,717,935 fuel with 0002 and 1,079,875,166 without.

### 4. F2's checks hold the README's two sentences (EXECUTED)

The review's helper probes `x04b` and `x04c` are not in the repository. They are rebuilt from the
review's text (`f2_driver.py`, `f2_plain.out`). A read-only grant at `/ro` holds `data.txt` and
`ent.xsl`. `ent.xsl` declares `<!ENTITY s SYSTEM "/ro/data.txt">` and a named template that
writes `&s;`. The main stylesheet, compiled from a string, imports or includes it and calls the
template:

| case, for both `xsl:import` and `xsl:include` | result |
|---|---|
| `href="file:///ro/ent.xsl"`, `access_control=DENY_ALL` | **compiles; the output holds `data.txt`** |
| `href="ent.xsl"` with `base_url="file:///ro/main.xsl"`, `DENY_ALL` | the same |
| `href="/ro/ent.xsl"` with `base_url="/ro/main.xsl"`, `DENY_ALL` | the same |
| `file:///ro/ent.xsl`, `XSLTAccessControl(read_file=False, read_network=False)` | the same |
| `file:///ro/none.xsl` (absent), `DENY_ALL` | `XSLTParseError`, "Cannot resolve URI file:///ro/none.xsl": compiling tells whether a granted file exists |
| `href="/ro/ent.xsl"` with no base URL | `XSLTParseError` (the base is `string://__STRING__XSLT__`), with or without a resolver; so the review's `x04b` had a base URL or a `file:` href (INFERRED). No check uses this form: refusing a load that cannot happen proves nothing (the pre-build review's F5) |
| the stylesheet parsed from its bytes with a parser whose `etree.Resolver` raises on every URL, then compiled under `DENY_ALL`, in the three forms that otherwise load | **both loads raise**, with the resolver's own exception naming the URL: `file:///ro/ent.xsl` for the `file:` href, `file:///ro/ent.xsl` for `ent.xsl` with `base_url="file:///ro/main.xsl"`, `/ro/ent.xsl` for `/ro/ent.xsl` with `base_url="/ro/main.xsl"`; nothing of `data.txt` appears |
| the same parser, but the stylesheet parsed by path (`etree.parse("/ro/main.xsl", p)`) | the resolver refuses the stylesheet itself: fails closed, but gives no stylesheet (EXECUTED by the review, `f2_file_parse.out`); from an open file object or from bytes it compiles and refuses the import |

Both binaries give the same answers (EXECUTED: plain 511,271,219 fuel, snapshot 211,000,190 for
the first form of the probe). Native lxml 6.1.3 prints the granted file under `DENY_ALL` too
(EXECUTED by the review, `native_f2.out`).

### 5. F4: what traps, measured three ways, and two README rows corrected

Each row was bisected to its exact edge (EXECUTED; the programs are `f4_edges.py`'s kinds). The
edge is the first depth that ends in the trap "stack overflow". Every trap was clean, and the next
call printed `ok`. The plain and snapshot binaries gave the same edge in every row. Three
engines, because the edge moves with Cranelift's frames:

- **the runner, unmetered** (`run`'s default, `fuel=None`): the engine the README's numbers came
  from;
- **the runner, metered** (`fuel=10**11`), as spec 071's `test_deep_data_limits` runs: fuel checks
  make the frames larger;
- **an engine at wasmtime's defaults** (no fuel, no epochs, 512 KiB), through the judge's driver's
  `own` path, as spec 071's `test_recursion_raises_on_wasmtimes_default_engine` makes one: the
  engine an embedder following the README's step 4 gets. It has the most room.

| row | README (`c53c05c`) | runner, unmetered | runner, metered | wasmtime's defaults | upstream's own limit |
|---|---|---|---|---|---|
| XPath, nested parentheses | about 375 | 373 | 357 | 500 | 5,000 (`XPATH_MAX_RECURSION_DEPTH`) |
| XPath, chained predicates (`a[1][1]…`) | about 4,600 | 4,637 | 4,056 | 4,644 | 5,000 |
| XSLT, nested `call-template` | about 480 | 483 | 462 | 523 | `xsltMaxDepth` 3,000 |
| XSLT, `apply-templates` with `xsl:copy` over a tree built in Python | about 670 (now about 470) | **471** | 451 | 509 | 3,000 |
| XSLT, a bare `apply-templates` over the same tree | (now about 670) | 677 | 663 | 740 | 3,000 |
| C14N of a tree built in Python | about 1,500 | 1,479 | 1,479 | 1,629 | none |
| RelaxNG validation of a tree built in Python | about 430 | 433 | 396 | 516 | none |
| an exception freed after unwinding N Python frames | (see below) | 2,712 | 2,958 | 3,259 | the recursion limit |
| `RecursionError` at a raised limit N | "between 1,000 and 3,000" (now: the traceback, about 2,700) | 2,715 | 2,961 | 3,262 | the limit |

Sources: `f4_runner_unmetered.jsonl`, `f4_runner_metered.jsonl`, `f4_runner_apply_bare.jsonl`,
`f4_defaults_engine.jsonl`.

**Two rows were wrong in the README; both corrections have landed** (main `932bc00`, from this
draft's bisection, before this specification is built). The README column above is
`c53c05c`'s; "now" gives `932bc00`'s words.

1. **`apply-templates`.** "A tree deeper than about 670" holds only for a template that does
   nothing but apply templates (the review's shape: 677). A template that copies each element,
   the common identity shape, traps from 471. Main now says "about 470 with a template that
   copies (about 670 with one that only applies templates)".
2. **"Plain Python recursion between about 1,000 and 3,000 levels once a program raises
   `sys.setrecursionlimit` to 3,000 or more."** Plain recursion does not trap. With the limit at
   10**6, a function that recurses 99,950 deep and returns completes (`f4_rec.out`). What traps is
   **freeing a traceback** of more than about 2,700 frames:
   - an exception that unwinds through 3,000 frames traps, whether `RecursionError` or a
     `ValueError` raised at the bottom (`f4_rec2.out`);
   - with the traceback kept, the program goes on; the trap comes at `del` of the traceback
     (`f4_rec2.out`, "caught/ok", then the trap);
   - a `RecursionError` needs the limit raised to reach that depth, which is why the review saw it
     only above 3,000. INFERRED: freeing a traceback recurses in C once per frame, and the
     trashcan's guard watches the linear-memory stack, not wasm's own (spec 071's window).

   Main now says "freeing a traceback longer than about 2,700 frames (deep recursion is itself
   fine, but once a program raises `sys.setrecursionlimit` past that, the `RecursionError`'s
   traceback traps when it is freed)".

A fuel cap moves every edge, by up to an eighth (XPath predicates: 4,637 to 4,056). The README
says so in one clause (Decision 8).

**Which engine the README's numbers describe** (the pre-build review's F7). They are the
runner's: 512 KiB with epoch interruption on, no fuel cap. Check 4 holds a different engine,
wasmtime's defaults, whose edges are 4% to 35% higher (parens 500 against 373), because it has no
epoch checks. The two agree in direction, and check 4's depths hold both (Decision 6). Once 078
moves the list into step 4, for an embedder at 512 KiB, the list keeps the runner's numbers and
gains one clause saying so (Decision 8).

### 6. F4's checks state their depths against one engine: wasmtime's defaults

Spec 078 (confirmed, building soon) runs every guest of `run` on 8 MiB. There these depths raise
or trap 10 to 16 times deeper, and 078 restates `test_deep_data_limits` at 8 MiB, with XPath, XSLT,
C14N, RelaxNG and the raised limit among its rows. 078 also moves the README's 512 KiB list,
unchanged, into *From any language*, step 4, as the limits an embedder meets who keeps
wasmtime's 512 KiB.

So F4's checks do not run through `run`. They run on **an engine at wasmtime's defaults**,
through the driver's `own` path. That engine is exactly step 4's embedder, before 078 and after
it. Its depths are independent of the runner's stack, so 078 restates nothing of 087's, and 087
need not wait for 078. The depths are set so that they also hold the runner's own 512 KiB
engines, metered and not, as long as `run` has 512 KiB:

- **completes at** at most three quarters of the lowest edge of the three engines;
- **traps at** at least a quarter past the highest; where upstream's own limit is closer, between
  the highest edge and that limit, with room on both sides.

| row | completes at | traps at | why that trap depth |
|---|---|---|---|
| XPath, nested parentheses | ~~260~~ **240** | 640 | 128% of 500 |
| XPath, chained predicates | ~~3,000~~ **2,700** | 4,950 | below libxml2's 5,000 (which raises `XPathEvalError`); 6.6% past 4,644 |
| XSLT, nested `call-template` | ~~340~~ **320** | 700 | 134% of 523 |
| XSLT, `apply-templates` with `xsl:copy` | ~~330~~ **320** | 680 | 134% of 509 |
| XSLT, a bare `apply-templates` | ~~490~~ **480** | 930 | 126% of 740 (74% of 663 to complete) |
| C14N | ~~1,100~~ **1,000** | 2,100 | 129% of 1,629 |
| RelaxNG validation | ~~290~~ **260** | 660 | 128% of 516 |
| an exception freed after N frames | 2,000 | 4,200 | 129% of 3,259 |

- **Restated by the builder (2026-10-19), as the next paragraph but two allows.** linux/amd64's
  edges (the landing notes) are lower than arm64 macOS's on every engine; its metered runner is the
  lowest edge in every row but C14N (its unmetered runner, 1,355) and the traceback row. To keep
  "at most three quarters of the lowest edge" on both hosts, seven "completes at" depths fall (struck
  through above). Every "traps at" depth holds as drafted: the highest edge is arm64 macOS's
  wasmtime's-defaults engine in every row, and no host's predicates edge passes 4,800.
- **Two rows that must not trap.** A function that recurses 20,000 deep under a raised limit and
  returns completes (the README's corrected sentence). And with
  `etree.XSLT.set_global_max_depth(250)`, `call-template` 2,000 deep and `apply-templates` over a
  2,000-deep tree raise `XSLTApplyError`, not a trap (Decision 7).
- **What a trap looks like on this path** (the pre-build review's F1). The driver's `own` path
  does not name traps as the runner does. A stack overflow there gives `trapped == "error while
  executing at wasm backtrace:"` (wasmtime's heading) and `trap_cause == "wasm trap: call stack
  exhausted"` (EXECUTED by the review, `f4_cause.out`). So check 4 asserts `(r.exit_code,
  r.trap_cause) == (None, "wasm trap: call stack exhausted")`. Teaching the driver to name traps
  would be a judge change of its own, for no gain here; it is not done.
- **On the snapshot binary only, one test, one module** (the pre-build review's F8). Every edge is
  the same on both binaries (EXECUTED), and compiling 45 MB on a second engine costs seconds and
  a gigabyte. So check 4 is one test that compiles the module once and loops over the rows,
  collecting every row's failure, as spec 071's default-engine check does. Under `-n 6` it then
  compiles once, on whichever worker runs it, not once per worker. It is in the fast tier: about
  thirty short guests on one compiled module.
- **Hosts.** The edges above are arm64 macOS's. The builder measures the same table on
  linux/amd64 (the research image, as 078 did) before fixing the numbers, and moves a number only
  to keep the two rules. Windows is judged by the release dry run.
- **The predicates row's fallback** (the pre-build review's F4). With room, libxml2 completes
  5,000 chained predicates and raises `XPathEvalError` from 5,001 (EXECUTED by the review on a
  2 MiB engine, `f4_xpath_limit.out`). So 4,950 traps only where the stack edge is below it. Its
  margin, 6.6% past 4,644, is the only one under the 25% rule. If any host's edge passes 4,800
  (the builder's linux/amd64 run, or 086's re-measure), the row's deep depth becomes 5,500 and it
  asserts "traps or raises `XPathEvalError`", and the README says "near libxml2's own limit of
  5,000".
- **Spec 086** (wasi-sdk 34) recompiles the guest, so its frames move. It re-measures this table
  with its other edges; the margins are there for it, but for predicates (above).
- **x86-64's frames** (INFERRED from 071's measured 0 to 29% larger x86-64 frames, the review's
  reading). Larger frames lower every edge, so the "traps at" depths only get safer. The thinnest
  "completes at" is predicates (4,644 / 1.29 ≈ 3,600 against 3,000), then C14N (1,263 against
  1,100) and call-template (405 against 340). The builder's linux/amd64 run is the gate.

### 7. libxslt's depth: no recipe constructor; the README names lxml's own call

The review suggested, as optional, lowering libxslt's public `xsltMaxDepth` to about 250 from a
recipe constructor, so deep XSLT raises `XSLTApplyError` instead of trapping. It is not done.

- **lxml already exposes it** (READ, `src/lxml/xslt.pxi:454`): `etree.XSLT.set_global_max_depth(n)`
  sets `xsltMaxDepth`. A program that runs untrusted XSLT can call it. With 250 (or 300),
  `call-template` 2,000 deep, `apply-templates` with `xsl:copy` over a 2,000-deep tree, and a
  heavier template (two variables, nested literal elements, `for-each` with `sort`, `choose`) each
  raise `XSLTApplyError`, metered and unmetered; with the default 3,000 the same program traps
  (EXECUTED, `f4_maxdepth.out`).
- **After 078 a lower default costs real programs.** At 8 MiB libxslt's own 3,000 raises before any
  trap (078's criterion 9). A default of 250 would then refuse legitimate recursive templates,
  such as a tokenizer over a 1,000-character string, that work natively and in `run`. It would
  help only embedders who keep 512 KiB, and they can make the call above.
- **A constructor is not free.** It joins the reviewed constructor list (spec 023, Decision 4),
  runs before the snapshot, and makes lxml differ from native lxml's default.

So the README's deep-recursion text gains one sentence naming `set_global_max_depth`, and
Decision 6's table holds it. It says "templates like these", not "deep templates": three shapes
were measured, and a template with much heavier C frames per level could still trap before 250
(INFERRED; the review's wording point). The owner may overrule (*The owner's choices*).

### 8. The README and the CHANGELOG

- ***regex in the guest*** (lines 181 to 185), replaced: "One edge: `timeout=` counts the guest's
  clock, which on WASI is the time since the guest started, waits included (wasi-libc's `clock()`),
  where native regex counts CPU time. regex kept its clock ticks in a 32-bit type on wasm32, so a
  `timeout=` above about 2.1 seconds never fired; a second carried patch
  (`recipes/patches/regex-2026.9.29/0002-timeout-ticks.patch`) keeps them in 64 bits, until regex
  releases the change, and makes `timeout=float('inf')` mean no timeout." "Five of regex's
  callbacks … a carried patch" becomes "two carried patches" where it counts them.
- **The patches row**: "upstream patches carried: 8", the eighth named.
- ***Deep recursion***: Decision 5's two corrections are already on main (`932bc00`), so this
  specification does not write them. It adds, after the list: "These are the runner's depths, with
  epoch interruption on; a fuel cap moves them by up to an eighth, and an engine without epoch
  checks (wasmtime's defaults) has up to a third more room." Then: "For untrusted XSLT,
  `etree.XSLT.set_global_max_depth(250)` makes templates like these raise `XSLTApplyError`
  instead." The other rows stand: the measured edges agree with them.
- ***lxml in the guest***, the remedy sentence gains: "parse it from its bytes or an open file;
  parsed by path through that parser, the stylesheet itself is refused" (the review's F5 note).
- **Where those words go depends on 078** (Decision 9). If 078 has landed, the 512 KiB rows live in
  step 4, and the added sentences go there, the first saying the numbers are the runner's at
  512 KiB (the pre-build review's F7). And 078's *Deep recursion* row "recursion that reaches a
  `sys.setrecursionlimit` above about 43,000" becomes "an exception that unwinds through more than
  about 43,000 Python frames", keeping 078's number. INFERRED: the same traceback free; the builder
  confirms it with one 8 MiB run of each (`traceback-freed` at 50,000 traps; plain recursion
  100,000 deep that returns completes).
- **CHANGELOG**, the open release's section: "regex's `timeout=` fires past 2.1 seconds (spec 087;
  the 0.1.0a7 security review's F3): a second carried patch,
  `recipes/patches/regex-2026.9.29/0002-timeout-ticks.patch`, keeps regex's clock ticks in 64 bits
  (wasm32's `Py_ssize_t` is 32 bits, and wasi-libc counts 10**9 ticks a second); `timeout=inf` now
  means no timeout. Checks now hold the README's lxml `DENY_ALL` sentences and each 512 KiB
  recursion row, on an engine at wasmtime's defaults."

### 9. Where this meets other specifications

- **078** (confirmed; parallel-safe; builds after 065). Decision 6 makes the checks independent of
  it: they run on their own engine at wasmtime's defaults, never through `run`. 078 edits the
  driver's cached engine and runs every `run()` on a 10 MiB thread; a 512 KiB `own` engine on that
  thread traps at the same depths, since the trap depends on `max_wasm_stack`, not on the thread
  (INFERRED from 078's Decision 1; the builder runs the table once on 078's driver if 078 has
  landed). Both edit `tests/harness/guest.py` (078 the engine and `run()`'s thread; 087 one keyword)
  and `test_v1_2_hostile_guest.py` (078 restates `test_deep_data_limits`; 087 adds a separate
  check): textual merges. **083** (the driver answers file timestamps) edits `guest.py` too; the
  merge is textual, but not right as it falls (the build review's F3): 083's `FileFacts` draws a
  file's times from the same `ticks` as the clocks, with `CLOCK_STEP_NS`. After the rebase onto
  main `8c07ad4` it uses `clock_step_ns`, so a file's times follow a changed step as the clocks do;
  `tests/unit/test_guest.py::test_a_files_times_follow_the_runs_clock_step` holds it with
  `wat.FILE_TIME_PROBE` (seen failing on the merged driver: a file dated 3,997 µs behind the
  clock at a 2 ms step). The README follows Decision 8. **Expected order:** 078 first. It is
  parallel-safe and ready; 087 is build-class and waits for a build slot. Either order works.
- **086** (wasi-sdk 34, reserved): re-measures Decision 6's table; Decision 6 leaves the margin.
- **065** (landed, `a4b46de`): no overlap. 087 adds no upstream suite group (`tests/upstream/` is
  untouched; regex's own suite is spec 063's matter).
- **085** (build-class, drafted) and **037** (build-class): no shared file but `CHANGELOG.md` and
  `context/upstream/README.md`; one build-class landing at a time (§5.7).

### 10. S3: an installed copy never takes a neighbouring set, and a found set is checked (added 2026-10-19)

The 0.1.0 whole-surface security review
(`scratchpad/security-review/0.1.0-whole-surface-security-review-2026-10-19.md`, S3, Low; its
helper's probe `probes/supply/s1_target_layout.log`) found two things in `__init__.py` and the
runner (READ):

- `_REPO = Path(__file__).resolve().parents[2]`, and a `build/artifacts/` holding a `MANIFEST`
  under it was preferred to the wheel's own set whenever `_REPO/pyproject.toml` existed. After
  `pip install --target proj/deps` (or vendoring), `_REPO` is the user's own project, and
  `artifact_dir()` returned `proj/build/artifacts` (EXECUTED by the review's helper).
- No set was checked when it loaded: the binaries were compiled from whatever bytes were there.
- The planting path (INFERRED by the review, not run): an embedder so installed who gives a guest
  a writable grant at `proj/build` lets it write a set that a later call loads and runs, with
  that later call's grants. The runtime-folders judge does not refuse that grant, since
  `proj/build/artifacts` is not yet the set in use.

**The rule.** The checkout's `build/artifacts/` is looked at only when the package is
`<repo>/src/wasi_python/` and `<repo>/pyproject.toml`'s `[project] name` is `wasi-python` (read
with `tomllib`; any error reading it means "not a checkout"). Everywhere else, `$WASI_PYTHON_ARTIFACTS`
and then the wheel's own `artifacts/` are the only places, as before.

- **Why `src/` and the name, and not a `.git` folder** (the coordinator's example). The judge, the
  build and the release workflow all import the package from `<repo>/src/wasi_python/` (uv's
  editable install), so the rule keeps every one of them. A wheel never has a `src/` folder above
  the package, and a project of the user's names itself, not wasi-python. A `.git` test would
  add nothing against planting (the attacker needs no `.git`) and would break a checkout copied
  without one (an exported tree, a container's `COPY`).
- **The check of a found set.** `run` and `Session`, given no `artifacts=`, check the set
  `artifacts()` finds before using it: its `MANIFEST`, the binary the call runs and the stdlib zip
  each against the set's own `SHA256SUMS` (written by step 90; the wheel carries it, since the
  release copies the whole `build/artifacts/`). A file that differs, is not listed, or a set with
  no `SHA256SUMS`, raises `ArtifactsMissing` naming the file, before anything is compiled. The
  digests are kept per file stamp, so the check costs two small reads a call.
- **The checked digests bind the bytes the call uses** (the build review's F1, taken). The check
  hands its binary and zip digests on. `_module` compiles a found set's binary only from bytes read
  once and hashed to the checked digest (`wasmtime.Module(engine, data)`), and writes the `.cwasm`
  under that digest only from them; `_zip_folder` holds the guest's private copy of the zip to the
  checked digest. So a file swapped after the check, by a writer of the set's folder during the
  call, is refused (`ArtifactsMissing`, or the zip copy's `RuntimeError`), never run, and never
  left in the module cache. Three unit rows in `tests/unit/test_runner_sets.py` hold the review's
  cases a, b (with c: the set put right compiles anew) and z; each was seen failing on the
  runner before it. A set the caller passes keeps today's path.
- **What the check does and does not do.** It refuses a changed or half-written file. It does not
  stop a guest that writes a whole consistent set, `SHA256SUMS` included: the location rule does
  that. Both are needed; neither alone is the fix.
- **A set the caller passes is the caller's own.** `run(artifacts=Artifacts(…))` is public API
  for four paths of the caller's choosing, and three of the judge's checks pass a WAT stand-in
  beside the real `MANIFEST` this way (`test_the_door_bounds_every_frame`,
  `test_an_old_artifact_set_is_named`, `test_an_artifact_set_without_the_guest_package_is_refused`).
  Checking such a set would break the API and those checks, so it is not checked; the README says
  that `$WASI_PYTHON_ARTIFACTS`, a checkout's `build/` and a passed set (even one from
  `artifacts()`) are trusted input, and that the check catches a changed or half-written file, not
  a set rewritten whole with its `SHA256SUMS` (the build review's F2). This is the one place S3's
  brief ("any set it does load") is narrowed, and why.
- **No public signature changes**; `tests/public_api.txt` is unchanged. The docstrings of `run`,
  `run_async` and `Session` and of `artifact_dir` say it, and the README's reference is
  regenerated from them (`tests/harness/api.py --write`).

## Intent

A program that sets `timeout=` on a regex match gets its timeout, whatever its length. And every
sentence the README says about lxml's `DENY_ALL` and about recursion that still traps is a check,
stated against an engine that does not move when the runner's stack does.

## Design

| file | change |
|---|---|
| `recipes/patches/regex-2026.9.29/0002-timeout-ticks.patch` | new, `fix.patch` byte for byte (Decision 2) |
| `context/upstream/24-regex-timeout-ticks/pr.md` → `context/upstream/patches/regex-2026.9.29/0002-timeout-ticks.md`; `context/upstream/README.md` | the facts sheet moves at build time; its row says it is carried |
| `scripts/assemble_artifacts.py` | `MODIFIED` gains 0002's line (Decision 2) |
| `tests/harness/guest.py`, `tests/harness/wat.py`, `tests/unit/test_guest.py` | the `clock_step_ns` keyword, the resolution that follows it, a WAT probe and their unit checks (Decision 3) |
| `tests/checks/test_v1_3_regex.py` | check 1 |
| `tests/checks/test_v1_3_lxml.py` | checks 2 and 3, with a grant of their own |
| `tests/checks/test_v1_2_hostile_guest.py` | check 4 and its table (Decision 6) |
| `README.md`, `CHANGELOG.md` | Decision 8; Decision 10's sentence on where sets are found |
| `src/wasi_python/__init__.py`, `src/wasi_python/runner.py` | Decision 10: the checkout rule; the found set checked against its `SHA256SUMS` |
| `tests/test_api.py`, `tests/unit/test_runner_sets.py` | checks 7 and 8 |

## The checks, first

Each is written before the change it judges. Each was, or will be, seen failing first.

1. **v1.3, `test_a_timeout_past_2_147_seconds_fires[which]`** (`tests/checks/test_v1_3_regex.py`,
   both binaries, fast tier). Through the `guest` fixture with `clock_step_ns=2_000_000` and a fuel
   cap of 5·10**9, Decision 3's program. It asserts, from the program's JSON:
   - `timeout=3` raises `TimeoutError`, and the guest's clock moved between 3.0 and 3.1 s;
   - `timeout=2.0` and `timeout=0` raise `TimeoutError`;
   - `timeout=1e9`, `1e13` and `inf` complete with `None`, the search's own answer.
   The guest reads its clock with `time.clock_gettime_ns(time.CLOCK_MONOTONIC)` (Decision 3).
   Seen failing first: on the released set, `timeout=3` completes after 4.658 s
   (EXECUTED, `evidence/f3_check.out`). It records fuel (about 1.04 G on the plain binary).
2. **v1.3, `test_deny_all_leaves_a_stylesheets_imports_to_its_parser[which]`**
   (`tests/checks/test_v1_3_lxml.py`, both binaries). **A grant of its own** (the pre-build
   review's F2): a fresh read-only folder at `/ro` holding only `ent.xsl` (an external entity on
   `/ro/secret.txt`) and `secret.txt`, made by a helper beside `_grants`, never by `_grants`
   itself, whose `/ro` listing `test_files_by_path_in_grants` prints and whose files that check's
   last assertion names. So no expectation (`FILES_WANT`) and no recorded fuel moves. Guest paths
   only (spec 081). For `xsl:import` and `xsl:include` each, under `DENY_ALL`: the output holds
   `SECRET` for a `file:` href and for a relative href with a base URL; under
   `XSLTAccessControl(read_file=False)` too; an absent file raises `XSLTParseError` naming its URL.
   Seen failing first: the builder shows each assertion bites with a mutant (an `ent.xsl` without
   the entity; an href to the absent file in the "present" row).
3. **v1.3, `test_a_refusing_resolver_stops_a_stylesheets_imports[which]`** (same file). The same
   stylesheets parsed with an `etree.XMLParser` whose `resolvers` hold one `etree.Resolver` that
   raises its own exception class on every URL, the stylesheet parsed from its bytes, then
   compiled under `DENY_ALL`: for `xsl:import` and `xsl:include`, in the three forms that load
   without the resolver, `etree.XSLT(…)` raises that exception naming the URL, and nothing of
   `SECRET` is printed. The forms and their URLs (the pre-build review's F5): a `file:` href,
   `file:///ro/ent.xsl`; `ent.xsl` with `base_url="file:///ro/main.xsl"`, `file:///ro/ent.xsl`;
   `/ro/ent.xsl` with `base_url="/ro/main.xsl"`, `/ro/ent.xsl`. Its own grant, as check 2's. Seen failing first: with a
   resolver that returns `None` (does not refuse), the loads succeed and the check fails.
4. **v1.2, `test_what_traps_on_wasmtimes_default_engine`** (`tests/checks/test_v1_2_hostile_guest.py`,
   fast tier; one test, not parametrized: the snapshot binary compiled once on an engine at
   wasmtime's defaults, the rows looped and every failing row reported together; through
   `driver.run(…, own=…)`, which records no fuel; Decision 6). For each of the eight trap rows:
   the completing depth prints `ok`; the deep one ends with `(r.exit_code, r.trap_cause) == (None,
   "wasm trap: call stack exhausted")`, the driver's words for a stack overflow (the pre-build
   review's F1); then `print('ok')` on the same engine prints `ok`. The two must-not-trap rows end with exit 0 and their expected line
   (`ok`, or `XSLTApplyError` twice). The programs are `f4_edges.py`'s kinds, moved into the check.
   Seen failing first: on an engine with `max_wasm_stack` at 1 MiB, every trap row completes or
   raises instead (the builder records it).
5. **Unit, `tests/unit/test_guest.py`, with WAT probes** (the pre-build review's F3; no
   artifact needed). `CLOCK_STEP_PROBE`, beside `CLOCK_PROBE` in `tests/harness/wat.py`, calls
   `clock_time_get` on the monotonic clock twice and returns the difference in microseconds;
   `CLOCK_RES_PROBE` calls `clock_res_get` on it and returns the resolution in microseconds. The
   step probe returns 1 at the default and 2,000 with `clock_step_ns=2_000_000`; the resolution
   probe runs with `clock_step_ns=2_000_000` and returns 2,000 (the default's resolution is spec
   065's guard's, unchanged). Seen failing first: the keyword does not exist.
6. **The patch rules and trees** (existing): `test_carried_patches_follow_the_rules` (README's count
   8, CHANGELOG names the patch, the sheet's six header lines and `Files: src/_regex.c`) and
   `test_source_tree_matches_its_tarball[regex]` cover 0002 by construction. Seen failing first:
   the builder shows the trees check failing on a tree with 0002 applied and the patch file absent.

7. **`tests/test_api.py::test_an_installed_copy_ignores_a_neighbouring_set[…]`** (three layouts: a
   `--target` install in a project, the same in a project that names itself wasi-python, a copy
   vendored under a project's `src/`) and **`test_a_source_checkout_prefers_its_build`**. The
   package's modules are copied to `proj/<where>/wasi_python/` with a set of its own, a planted
   set waits at `proj/build/artifacts`, and a fresh `python -I` imports the copy and prints
   `artifact_dir()`: the copy's own set, never the planted one; in the checkout layout, the
   build's. Seen failing first: on main, all three layouts print the planted set.
8. **`tests/unit/test_runner_sets.py`**: a small set at `$WASI_PYTHON_ARTIFACTS` (a WAT snapshot, an
   empty zip, its `SHA256SUMS`) runs; with its snapshot, zip or `MANIFEST` changed, or its
   `SHA256SUMS` gone, `run` raises `ArtifactsMissing` naming the file and `SHA256SUMS` before
   anything is compiled (`stats()["compiled"]` unchanged); a `Session` checks too; the same set
   passed as `artifacts=` runs unchecked. Seen failing first: on main, the five refusals fail and
   the two runs pass.

## Scope

In: Decisions 1 to 9. Out:
- **the `xsltMaxDepth` recipe** (Decision 7);
- **XPath's recursion limit.** `XPATH_MAX_RECURSION_DEPTH` is a plain `#define` in libxml2's
  `xpath.c:117`, not guarded by `#ifndef` (READ), so lowering it would need a patch. At 8 MiB
  libxml2's own 5,000 already raises first (078);
- **the 8 MiB rows**, which are 078's;
- **regex's own test suite under the runtime** (spec 063's frame).

## Acceptance criteria

1. **The checks exist and were seen failing first,** as *The checks* says, each failure recorded
   in the landing notes.
2. **The build.** From an empty `build/` in a clean clone, `scripts/build.sh` applies 0001 and then
   0002 with no offset, builds step 53 with 0 warnings, and makes a set whose binaries pass every
   check. `MANIFEST` names both patches by hash. `LICENSES/regex.txt` holds two modification
   lines, one per patch. Steps 53 to 90 run twice give the same `SHA256SUMS`.
3. **The same bytes everywhere** (spec 012): the arm64 Linux rebuild gives macOS's `SHA256SUMS`,
   and the release's x86_64 rebuild too.
4. **The patch is what its sheet says.** `recipes/patches/regex-2026.9.29/0002-timeout-ticks.patch`
   equals `../upstream/24-regex-timeout-ticks/fix.patch` byte for byte (SHA-256 `9da893d0…`, or the
   builder's restated hash if the review changes it). The sheet moved unchanged.
5. **The numbers recorded** in the landing notes: both binaries' bytes (the scratch build's
   `python.wasm` grew 202 bytes; a growth above 2 KB is a finding for the build review), plain and
   snapshot `-c pass` fuel and `import regex` fuel (unchanged in the scratch build; any move is
   explained), and check 1's fuel.
6. **Decision 6's table on two hosts.** The edges measured on arm64 macOS (above) and on
   linux/amd64 by the builder, both in the landing notes, and every row's depths obey Decision 6's
   two rules on both.
7. **078's order.** The landing notes say which of 078 and 087 landed first and where the README's
   512 KiB rows went. If 078 is in, check 4 ran on 078's driver.
8. **The judge.** `uv run pytest -n 3`, then the lane's serial run, green but for the growth named
   here. The lane accepts with `--accept-judge` (the new checks and the driver keyword) and
   `--accept-growth` (the binaries' bytes, and any per-check fuel the patch moves, each with its
   reason).
9. **The release.** A release dry run passes every job on all three systems (AGENTS.md rule 6b).
10. **S3 (Decision 10).** Checks 7 and 8 pass, and were seen failing first on main. Every other
    check finds its set as before: no check, expectation or recorded fuel moves for Decision 10.

## The judge's changes

- `tests/harness/guest.py`: `run()` gains `clock_step_ns: int = CLOCK_STEP_NS`, read by its
  `clock_time_get`; its `clock_res_get` answers from `CLOCK_RESOLUTION_NS` as today, and answers
  the step for the realtime and monotonic clocks only when `clock_step_ns` is not the default.
  Its docstring says both. No other check's fuel moves (the default is today's step), and spec
  065's `test_the_guest_clocks_resolution_is_the_judges` is unchanged.
- `tests/harness/wat.py`, `tests/unit/test_guest.py`: check 5's two probes and its unit check.
- `tests/checks/test_v1_3_regex.py`: check 1.
- `tests/checks/test_v1_3_lxml.py`: checks 2 and 3, on a grant of their own. `_grants`,
  `FILES_WANT` and every existing check's fuel are unchanged (the pre-build review's F2).
- `tests/checks/test_v1_2_hostile_guest.py`: check 4, with its programs and its table.
- `tests/test_api.py`, `tests/unit/test_runner_sets.py`: checks 7 and 8 (Decision 10).
- No golden output, gap, allowance or progress file is edited. No check is weakened.

The accepting reasons, for the lane:

```
--accept-judge "spec 087: checks that hold the README's lxml DENY_ALL sentences on a grant of their own (an imported stylesheet's entity reads a granted file under DENY_ALL; a refusing resolver stops both loads), a check that regex's timeout=3 fires (the driver's clock steps 2 ms per read: a new clock_step_ns keyword, its stated resolution following it when not the default, two WAT probes), and the README's 512 KiB recursion rows on an engine at wasmtime's defaults"
--accept-growth "spec 087: regex's second carried patch keeps clock ticks in 64 bits: python.wasm +<bytes> and the snapshot +<bytes> (the builder's measured numbers); LICENSES/regex.txt one line; MANIFEST one recipe line"
```

The builder writes the two byte counts it measured in place of `<bytes>` (the pre-build review's
F11: the scratch build measured only `python.wasm`, +202; the snapshot was not rebuilt). No
existing expectation is edited; if the build had to edit one (`FILES_WANT` or another), the
`--accept-judge` reason would name it.

## The owner's choices

None blocks the build. The two README corrections this draft found are already on main
(`932bc00`), so that choice is gone. Decided until answered:

1. **The `xsltMaxDepth` recipe:** not carried (Decision 7). The README names lxml's own
   `etree.XSLT.set_global_max_depth`. If you want the lower default anyway, it is a recipe
   constructor, a reviewed-constructor entry and a check, and it changes lxml's default from
   native's. The pre-build review agrees with declining it.
2. **The upstream sheet.** Whether and how to send it, as with 0001 (question 80). It also fixes
   x86-64's immediate `TimeoutError` for `timeout=float("inf")`, a native bug, which may make it
   easier to send.

## Disposition of the pre-build review

The review (`scratchpad/087-review/087-the-a7-reviews-guest-follow-ups-spec-2026-10-19.md`, for
the lane to copy to `../reviews/`) reproduced the patch byte for byte (202 bytes, no new warning
under the strictest flags), found the timeout check and F2's facts sound, held every F4 depth on
its engine, and agreed with declining the `xsltMaxDepth` recipe. Every finding is written in; no
decision changed.

- **F1, check 4's trap name: written in.** Check 4 asserts `(exit_code, trap_cause) == (None,
  "wasm trap: call stack exhausted")`, the `own` path's words; the driver is not changed to name
  traps (Decision 6, check 4).
- **F2, `_grants` would move an existing check: written in.** Checks 2 and 3 get a grant of their
  own; `_grants`, `FILES_WANT` and every recorded fuel stay as they are (check 2, *The judge's
  changes*).
- **F3, the clock scanner: written in.** Check 1's guest reads
  `time.clock_gettime_ns(time.CLOCK_MONOTONIC)`; check 5 is two WAT probes beside `CLOCK_PROBE`,
  with no artifact; the scanner is untouched (Decision 3, checks 1 and 5).
- **F4, the predicates fallback: written in.** The fallback's deep depth is 5,500, above
  libxml2's 5,000, and 086's re-measure triggers it as the builder's linux/amd64 run does
  (Decision 6).
- **F5, check 3's absolute case: written in.** It carries `base_url="/ro/main.xsl"`, each of the
  three cases names the URL its exception carries, and the no-base form is used by no check; the
  README's remedy gains "parse it from its bytes or an open file" (Decisions 4 and 8, check 3).
- **F6, the rebase: done.** Rebased onto main `932bc00` (065 landed). Decision 5's two corrections
  are restated as landed there; Decision 8 no longer writes them; the owner's choice about them is
  gone. Check 4 gains the bare `apply-templates` row, 490 to complete and 930 to trap, holding
  main's "about 670" (Decisions 5, 6 and 8).
- **F7, which engine the README describes: written in.** The README's numbers are the runner's
  (epochs on); check 4's engine has up to a third more room; the README gains one clause saying
  so, in step 4 once 078 has landed (Decisions 5 and 8).
- **F8, the shared module and the tier: written in.** Check 4 is one fast-tier test that compiles
  once and loops the rows, as 071's default-engine check does, so `-n 6` compiles it once
  (Decision 6, check 4).
- **F9, the stated resolution: written in.** `clock_res_get` answers the run's step for the
  realtime and monotonic clocks when `clock_step_ns` is not the default, and from
  `CLOCK_RESOLUTION_NS` otherwise, as today; check 5's second probe holds it at 2 ms (Decision 3).
- **The confirmation's C1: written in.** The first revision read as "always the step", which would
  have broken spec 065's guard `test_the_guest_clocks_resolution_is_the_judges`. Decision 3 now
  keeps `CLOCK_RESOLUTION_NS` at the default and names that guard as unchanged; check 5's
  resolution probe runs with a non-default step.
- **F10, 32-bit glibc: written in.** The facts sheet and Decision 2 say plainly that `clock_t`'s
  own 32-bit wrap at about 2,147 s remains there; the case for `long long` rests on Win64.
- **F11, the accepting lines: written in.** `--accept-growth` carries the builder's measured byte
  counts for both binaries, not "about +200"; `--accept-judge` names any edited expectation, and
  none is edited.
- **The optional wording points: taken.** The README says "templates like these" for
  `set_global_max_depth` (Decision 7); 083's textual merge in `guest.py` is named (Decision 9).

## One line

regex's `timeout=` fires past 2.147 s through a second carried patch that keeps clock ticks in
64 bits, and new checks hold the README's lxml `DENY_ALL` sentences and its 512 KiB recursion
rows on an engine at wasmtime's defaults, which spec 078 never has to restate.

## Landing notes

**Built 2026-10-19** on `2abcba0` (the branch rebased onto main `91eb2c7` first; 078, 083 and 086
had not landed). Builder's evidence is under the worktree's `build/087/` (not tracked): the build
logs, `seen-failing.txt`, `mutants.log`, `edges/` (both hosts), `fast-2.log`, `full.log` and the
record `build/087/latest-full.json`.

### The build (criteria 2 to 5)

- **From an empty `build/`** in the worktree, downloads seeded from main's verified pins (49 pins,
  0 fetched, 49 verified): `scripts/build.sh --plain`, 16 steps. Step 53 applied 0001 then 0002
  cleanly ("Applied patch src/_regex.c cleanly", no offset) and compiled `_regex.c` with 0 warnings.
  Step 90 first refused the then-untracked patch ("untracked recipe files (stage them first)"); with
  it staged, step 90 ran. **Steps 53 to 90 run again** gave the same `SHA256SUMS`, byte for byte.
- **Before the patch**, the same full build reproduced main's set `s-c50ca51fae5eb55b-c9dcb5b8`
  exactly (`SHA256SUMS` identical): the set check 1 was seen failing on.
- **The same bytes everywhere** (criterion 3): the dry run's "the same bytes from every host" job
  passed (arm64 Linux and x86_64 Linux rebuilds against the macOS build) — run 39346784823.
- **The patch is its sheet's** (criterion 4): `recipes/patches/regex-2026.9.29/0002-timeout-ticks.patch`
  is `fix.patch` byte for byte, SHA-256 `9da893d047d2f365814c9731d1a51d275dc96bd77f48270b67fd6b8ddb69d3ce`;
  the sheet moved by `git mv`, unchanged. `MANIFEST` names both patches by hash;
  `LICENSES/regex.txt` holds two modification lines, one per patch.
- **The set's `SHA256SUMS`** (`89b14f67…` as a file), the lines that differ from main's set:

  ```
  87d0dbdf9ddf6bdbfe40476434a7f3b77143354102fa78d2800cbbb766ee31ce  LICENSES/regex.txt
  cd17dcd398404c3899cdedc57acb29e279557c7b313fbc3e238b99596c42b771  MANIFEST
  47cb880f18fa1904de9b96033d94fb73d561a3c2f277c45b0011d764b98a27ff  python-snapshot.wasm
  02026895917b7e22923db1bad99a02ee1d22f7382ff63715271e39fb9032d1fe  python-stdlib.zip   (unchanged)
  5f8d1b29c91849aaeab813fb1d4c498404812d7ac1e2e260b9160e8c9f112801  python.wasm
  ```

  The other 29 lines (the licence notices but regex's) equal main's.

### The numbers (criterion 5)

| what | main's set | this set | move, and why |
|---|---|---|---|
| `python.wasm` bytes | 41,099,661 | 41,099,863 | +202: `_regex.c`'s ticks in 64 bits (the scratch build's `5f8d1b29…`, reproduced) |
| `python-snapshot.wasm` bytes | 44,633,983 | 44,634,185 | +202: the same code |
| `python-stdlib.zip` bytes | 22,197,173 | 22,197,173 | none |
| `-c pass` fuel, plain / snapshot (`test_guest_runs_here`) | 167,589,143 / 15,721,612 | the same | none |
| `import regex` fuel, plain / snapshot (`test_regex_is_builtin_at_manifest_version`) | 440,316,072 / 168,432,729 | the same | none |
| check 1's fuel, plain / snapshot | new | 921,068,281 / 648,492,948 | new (the spec's "about 1.04 G" was the review's program, with a seventh `None` case) |
| checks 2 and 3, plain / snapshot | new | 501,240,084 / 210,275,104 and 498,792,899 / 207,695,137 | new |

Other fuel moved only by layout, inside the ratchet's tolerance and never red: seventeen fast-tier
rows by 17 to 51 instructions either way (spec 091's layout-dependent kind), the plot job by +102,
and the upstream groups by at most 0.004% (`cpython-a` −9,990,648, `cpython-archives` +4,631,408,
the rest under 75,000). No upstream group's `passes` moved.

### The checks, seen failing first (criterion 1)

- **Check 1** on the rebuilt base set, both binaries: `timeout=3` gave `['completed', 'None',
  4658000000]` (4.658 s of guest clock); with 0002, `TimeoutError` within 3.0 to 3.1 s.
- **Check 2**: passes on the base set (it holds a README sentence); a mutant `ent.xsl` without the
  entity fails it on both binaries, and an absent href in the "present" row fails it ("Cannot resolve
  URI file:///ro/none.xsl").
- **Check 3**: a resolver that returns `None` fails it on both binaries (the stylesheet's `SECRET`
  printed).
- **Check 4**: with `max_wasm_stack` at 1 MiB, all eight trap rows fail (XPath parentheses raises
  `XPathEvalError`; the other seven complete).
- **Check 5**: on HEAD's driver both unit checks fail (no `clock_step_ns`).
- **Check 6**: with 0002 applied in the tree and the patch file moved aside,
  `test_source_tree_matches_its_tarball[regex]` fails, "src/_regex.c: modified".
- **Checks 7 and 8 (S3)**: on main's runner the three layouts of check 7 print the planted
  `proj/build/artifacts`, and check 8's five refusals fail while its two runs pass.

The mutants ran as a pytest plugin outside the repository (`scratchpad/087-mutants/mutant087.py`);
no check was edited for them.

### Decision 6's table on two hosts (criterion 6)

Bisected on this set's snapshot binary (`scratchpad/087-amd64/scripts/edges.py`, using check 4's own
programs), the first depth that traps. arm64 macOS equals the spec's table in every cell.
linux/amd64 ran in `ghcr.io/astral-sh/uv:0.9-trixie-slim` under Rosetta, wasmtime-py 49.0.0:

| row | amd64 runner unmetered | amd64 runner metered | amd64 wasmtime's defaults | lowest of both hosts | ¾ of it | completes at | highest | traps at |
|---|---|---|---|---|---|---|---|---|
| XPath parentheses | 342 | 324 | 445 | 324 | 243 | **240** | 500 | 640 |
| XPath predicates | 4,056 | 3,603 | 4,062 | 3,603 | 2,702 | **2,700** | 4,644 | 4,950 |
| `call-template` | 463 | 437 | 499 | 437 | 327 | **320** | 523 | 700 |
| `apply-templates`, copy | 451 | 433 | 479 | 433 | 324 | **320** | 509 | 680 |
| `apply-templates`, bare | 663 | 649 | 707 | 649 | 486 | **480** | 740 | 930 |
| C14N | 1,355 | 1,478 | 1,480 | 1,355 | 1,016 | **1,000** | 1,629 | 2,100 |
| RelaxNG | 396 | 357 | 478 | 357 | 267 | **260** | 516 | 660 |
| traceback freed | 2,712 | 2,711 | 2,963 | 2,711 | 2,033 | 2,000 | 3,259 | 4,200 |

Seven "completes at" depths fell to keep the rule (Decision 6's note); every "traps at" holds. No
host's predicates edge passes 4,800, so the fallback is not taken. Check 4 itself, called on
linux/amd64 with the restated depths, passed (`edges/amd64-check4.log`). The README's rows (the
runner's darwin numbers, "about") stand; amd64's runner edges are 0 to 9% lower.

### 078's order (criterion 7)

078 had not landed: 087 is built first. The README's 512 KiB rows stay under *Deep recursion*, and
Decision 8's two sentences follow them there. When 078 lands it moves them, with the sentences, to
step 4. Check 4 ran on main's driver; the 8 MiB confirmations are 078's.

### The judge (criterion 8)

- Fast tier `uv run pytest -m "not slow" -n 3`: 507/630 pass, 0 fail; ratchet lost 0, grew 2 (the
  two binaries' bytes).
- **Full judge** `uv run pytest -n 3` on the clean committed tree `2abcba0`:
  `wasi_python v1: 549/630 pass · 77 gap · 4 blocked · 0 fail (unit suite 1593/1600, 7 skipped)`;
  `ratchet vs b91e0eaa4e: lost 0 · absent 0 · unrun 0 · unrun locally 2 · gained 7 · grew 2`; the
  two unrun locally are the prior-art licence check and the oracle, blocked in any worktree. The
  record is `build/087/latest-full.json`.

The accepting texts, for the lane:

```
--accept "spec 087: regex's timeout= fires past 2.147 s (carried patch 0002), checks for the README's lxml DENY_ALL sentences and 512 KiB recursion rows, and S3: an installed copy never takes a neighbouring artifact set, and a found set is checked against its SHA256SUMS"
--accept-judge "spec 087: checks that hold the README's lxml DENY_ALL sentences on a grant of their own (an imported stylesheet's entity reads a granted file under DENY_ALL; a refusing resolver stops both loads), a check that regex's timeout=3 fires (the driver's clock steps 2 ms per read: a new clock_step_ns keyword, its stated resolution following it when not the default, two WAT probes), the README's 512 KiB recursion rows on an engine at wasmtime's defaults, and S3's checks (tests/test_api.py's installed-copy layouts, tests/unit/test_runner_sets.py, with the build review's swap cases, added to the own-runner shard in tests/release_shards.toml); after the rebase onto 083, the driver's file times follow clock_step_ns, with a WAT probe and a unit row; no existing expectation edited"
--accept-growth "spec 087: regex's second carried patch keeps clock ticks in 64 bits: python.wasm +202 bytes (41,099,661 -> 41,099,863) and the snapshot +202 bytes (44,633,983 -> 44,634,185); LICENSES/regex.txt one line; MANIFEST one recipe line"
```

### The release (criterion 9)

Dry run **39346784823** on the branch's `2abcba0` (pushed as `spec/087-the-a7-reviews-guest-follow-ups`):
24 jobs passed, among them both Linux rebuilds, the macOS build and judge, the three `verify` jobs,
"the same bytes from every host", and every judge shard on Windows (`own-runner`, `own-guest`,
`own-embedding`, `upstream-windows`), Linux and macOS but one. **The one red job,
`judge (macos-15, own-guest)`**, had 0 failures (`289/630 pass · 2 gap · 2 blocked · 0 fail`); its
only red lines are the two growth lines above (`GREW …test_binary_is_a_core_wasm_module[plain]:
bytes 41099661 -> 41099863`, `[snapshot]: bytes 44633983 -> 44634185`), which the lane's
`--accept-growth` accepts. `gather` and the publishing jobs were skipped (gather needs every judge
green; the others run only on a tag). So every red line is a growth line: built by AGENTS.md
rule 2. A dry run on main after acceptance is the lane's (rule 6b).

### Departures

1. **S3 joined the scope during the build** (the owner, 2026-10-19), as Decision 10, criterion 10
   and checks 7 and 8. It changes the runner's code with no pre-build review: the coordinator
   directed that the build review cover it (AGENTS.md rule 8 asks a pre-build review for the
   runner's code).
2. **S3's check covers the sets the runner finds, not a set the caller passes** (Decision 10): the
   brief said "any set it does load"; checking `run(artifacts=…)` would break that public API and
   three existing checks, so it is narrowed, and the README calls a passed set trusted input.
3. **Seven completing depths** of check 4 were restated after the linux/amd64 run, as Decision 6
   allows.
4. **Check 2 carries a third form**, a path href against a path base, beside the spec's `file:` and
   relative hrefs (Decision 4's table had it; check 3 uses it).
5. **`tests/release_shards.toml`** gains the new unit file in `own-runner` (the rules check asks every
   runner unit file to be in a files shard on all three systems); named in `--accept-judge`.
6. **"In a clean clone"** (criterion 2): the local full build ran from an empty `build/` in the
   worktree; the dry run's two Linux rebuilds and the macOS build are the clean clones, and they
   agree.

### After the build review (2026-10-19)

The build review (`scratchpad/087-buildreview/087-the-a7-reviews-guest-follow-ups-build-2026-10-19.md`,
for the lane to copy to `../reviews/`; verdict "lands once F2 and F3") is answered on the branch
rebased onto main `8c07ad4` (089 and 083 landed; the only conflict was `CHANGELOG.md`, both
entries kept). main changed no build input since `91eb2c7` (`scripts/`, `recipes/`, `downloads/`,
`src/`, the workflow), so the set above stands and was not rebuilt.

- **F3, fixed:** the merged driver's file times take `clock_step_ns` (Decision 9), with a unit row
  seen failing first (−3,997 µs) and the driver's docstring saying so.
- **F2, fixed:** the README's runner paragraph says what the check catches and what it does not,
  and names a checkout's `build/` and `run(artifacts=artifacts())` as trusted input.
- **F1, taken:** the checked digests bind the compiled bytes and the guest's zip (Decision 10),
  with three unit rows seen failing first on the runner before it.
- **F4, a follow-up:** `modified_notice` writes "the module is otherwise compiled as released"
  after each patch line; with two patches it should say it once, after the last. It changes
  `LICENSES/regex.txt` and so the set's name, so it waits for the next build-class specification
  that reassembles the set (roadmap line for the lane).
- **F8, fixed:** `Session`'s `artifacts` docstring continues at 16 spaces.
- **F5 to F7, notes:** F5's `cpython-c` growth is the pre-083 base's noise, so the lane's records
  are taken on the rebased commit; F6 (a zip literally named `src`) needs an embedder to make it,
  never a guest; F7 is criterion 9 as the lane's own dry run on main settles it.

These touch only `tests/`, `src/`, `README.md` and this file; no fuel row a check records moves
by them, and the judge's full run waits for the coordinator's go (the machine is saturated).

### For the lane (wave 1, its first entry; 2026-10-19)

- **The full judge is CI run 39351900172** on `ace3bdc` (the branch rebased onto main `8c07ad4`,
  pushed with lease), under the owner's wave pipeline; the local full judge on `ace3bdc` was started
  and stopped unfinished at the coordinator's word, so no local record stands for this commit.
- **Its result:** 24 jobs passed (both Linux rebuilds, the macOS build and judge, the three
  `verify` jobs, "the same bytes from every host", every judge shard on Windows and Linux, and every
  macOS shard but one). **One red job, `judge (macos-15, own-guest)`**:
  `wasi_python v1: 289/636 pass · 2 gap · 2 blocked · 0 fail`, `ratchet vs 69004e2129: lost 0 ·
  absent 0 · unrun 0 · unrun locally 1 · gained 8 · grew 2`. **Its only red lines are GREW lines:**

  ```
  GREW tests/checks/test_v1_1_artifact_set.py::test_binary_is_a_core_wasm_module[plain]: bytes 41099661 -> 41099863
  GREW tests/checks/test_v1_1_artifact_set.py::test_binary_is_a_core_wasm_module[snapshot]: bytes 44633983 -> 44634185
  ```

  No G7 line. `gather` was skipped, since it needs every judge green, so the run has **no
  `release-record-1`**; the nineteen shard records (`record-*`, the macOS own-guest one as
  `record-macos-own-guest-failed-1`) are downloaded to the worktree's `build/087/ci/`.
- **The claim list: the rows 087 changes.**
  - **New checks (7)**, each passing in the run:
    - `tests/checks/test_v1_3_regex.py::test_a_timeout_past_2_147_seconds_fires[plain]`, `[snapshot]`
      (fuel recorded);
    - `tests/checks/test_v1_3_lxml.py::test_deny_all_leaves_a_stylesheets_imports_to_its_parser[plain]`,
      `[snapshot]` (fuel recorded);
    - `tests/checks/test_v1_3_lxml.py::test_a_refusing_resolver_stops_a_stylesheets_imports[plain]`,
      `[snapshot]` (fuel recorded);
    - `tests/checks/test_v1_2_hostile_guest.py::test_what_traps_on_wasmtimes_default_engine` (no fuel).
  - **New unit rows** (the unit suite, not ratcheted checks): `tests/unit/test_guest.py` (the clock
    step, its resolution, a file's times at the step: 4 rows), `tests/unit/test_runner_sets.py` (10),
    `tests/test_api.py` (4).
  - **Retired checks:** none. **Moved or lost passes:** none.
  - **Rows that grow:** the two `test_binary_is_a_core_wasm_module` byte rows above, +202 each:
    regex's `_regex.c` with its clock ticks in 64 bits (carried patch 0002). No fuel row grows past
    the tolerance; the seventeen layout moves of ±17 to ±51 instructions on the old base are inside
    it.
  - **Not 087's:** the run's eighth gained row, `test_v1_1_artifact_set.py::test_wheel_carries_the_artifact_set`,
    passes in CI because CI has a wheel; it is blocked ("wheel") in any local worktree.
- **The exact accept flags:**

  ```
  --accept "087: regex's timeout= fires past 2.147 s (carried patch 0002), checks for the README's lxml DENY_ALL sentences and 512 KiB recursion rows, and S3: an installed copy never takes a neighbouring artifact set, and a found set is checked against its SHA256SUMS and binds the bytes it checked"
  --accept-judge "087: checks that hold the README's lxml DENY_ALL sentences on a grant of their own (an imported stylesheet's entity reads a granted file under DENY_ALL; a refusing resolver stops both loads), a check that regex's timeout=3 fires (the driver's clock steps 2 ms per read: a new clock_step_ns keyword, its stated resolution following it when not the default, two WAT probes), the README's 512 KiB recursion rows on an engine at wasmtime's defaults, and S3's checks (tests/test_api.py's installed-copy layouts, tests/unit/test_runner_sets.py with the build review's swap cases, added to the own-runner shard in tests/release_shards.toml); after the rebase onto 083, the driver's file times follow clock_step_ns, with a WAT probe and a unit row; no existing expectation edited"
  --accept-growth "087: regex's second carried patch keeps clock ticks in 64 bits: python.wasm +202 bytes (41,099,661 -> 41,099,863) and the snapshot +202 bytes (44,633,983 -> 44,634,185); LICENSES/regex.txt one line; MANIFEST one recipe line"
  ```
