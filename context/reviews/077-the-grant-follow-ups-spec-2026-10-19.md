# Review of 077 — The grant follow-ups (the specification, before build)

- **Date:** 2026-10-19
- **Reviewer:** a fresh agent (Claude Opus 5.5). I wrote spec 076's build review, whose F1 and
  F2 this spec closes, and none of this spec.
- **Reviewed:** `spec/077-the-grant-follow-ups` at `f7f248c` on main `d900dd9`
  (`git diff d900dd9..f7f248c`: the spec only, 186 lines; READ). I also read the worktree's
  `build/077/` probes and their outputs; the raw case and `_rewritten` as on main;
  CPython's `Lib/ntpath.py:300-333` and `PC/errmap.h` (`context/prior_art/cpython`, `7c04882`);
  and the verify step in main's `release.yml`. Microsoft's "Naming Files, Paths, and Namespaces"
  I read on 2026-10-19 for 076's build review.
- **Ran (EXECUTED, macOS arm64, wasmtime-py 49.0.0, -B).** No git tree was touched. Beside this
  file:
  - `probe_control_order.py` → `.out`: the raw case in its **real order**, where the final
    write of `XX` runs before the control read, with three `read` exports: the Design's, S3 as
    written, and a read that reads nothing.
  - `probe_077_names.py` → `.out`: the walk on main, with 077's eight names added to
    `_WIN_DEVICES`, over the Win32 model of 076's build review. It shows `_rewritten` before and
    after, roots to be made, and a fuzz of 16,653 spellings whose alphabet holds `COM¹`,
    `conin$` and `com0`.

## What holds

1. **F2's names** (READ, and EXECUTED in the model).
   - The six superscript names are Microsoft's, "reserved in every directory".
   - `CONIN$` and `CONOUT$` are CPython's `_reserved_names`, which CPython adds "on the side of
     caution" for names that may not be reserved.
   - `_rewritten` matches the stem as CPython's `_isreservedname` does (before the first period,
     trailing spaces dropped), with `.lower()` where CPython uses `.upper()`. For these ASCII
     names, `$` and the superscripts (`'¹'.lower() == '¹'`) the two are the same.
   - With the eight names added, `COM¹`, `Com² .x`, `lpt³.txt`, `CONIN$` and `conout$.log` are
     refused, and `COM0` and `LPT0` are not.
   - `root=C:\b\new\COM¹` and `C:\b\new\CONIN$` are refused before anything is made.
   - The fuzz gives 590 accepted spellings, none with a wrong chain (`probe_077_names.out`).
2. **`CONIN$` and `CONOUT$` against the model, as the lane asked.** Adding a name to the refused
   set can only add refusals; it can never make a chain wrong. If Windows does not treat `CONIN$`
   inside a path as the console, which is likely (INFERRED: CPython's own comment says it "may
   not" be reserved), then a folder so named is an ordinary name, and refusing it costs one
   unusable spelling. If Windows does map it in the last segment, the walk's open fails and the
   path is refused anyway, and the refusal now comes before `_make_missing`. Either way no rule
   is skipped. Accepted, as the lane ruled. The README should say these two are refused out of
   caution, as `ntpath.isreserved` refuses them, not that Windows rewrites them (N1).
3. **`COM0` and `LPT0` allowed.** Neither Microsoft's list nor CPython's names them. Even if a
   Windows version treated one as a device in the last segment, the result would be a refusal or
   the corner of F1 below, never a wrong chain. The model row pinning the boundary is right.
4. **F1's direction is right.** The read row through the iovec at 200 answers 8 on macOS with two
   real bytes asked for (`build/077/probe_raw_read.out`; and my 076 probe).
5. **The Windows route.** Main's verify step runs `tests/unit/test_runner_grants.py` whole on all
   three systems (READ, `release.yml:432-437`), so `-rA` alone is enough. The rest of the route,
   its authority and its freshness rule are 076's, which its build review found honest.

## Findings, most severe first

### F1 (Low-Medium): the control row's count check is stale, and the stated failures are wrong

The raw case's final write, `ex["write"](store, ro_fd)` after the renumber, already writes its
count, 2, at 208. The control read runs after it and is checked for "the count at 208 is 2". That
check passes whether the control read wrote its count or not.

EXECUTED in the case's real order (`probe_control_order.out`):

| `read` export | count at 208 | memory at 300 |
| --- | --- | --- |
| the Design's (iovec 200, count 208) | 2, passes | `b'or'`, passes |
| S3 as written (today's export, 400/408) | **2, passes** | `b'XX'`, fails |
| a read that reads nothing (answers 0) | **2, passes** | `b'XX'`, fails |

So only the bytes check bites. The spec's evidence statements are therefore wrong:
- criterion 2's "seen failing before the change: the control row (the count at 208 is 0)";
- S3's "`0 == 2`".

The build-time probe `build/077/probe_raw_read.py` showed `nread 0` only because it ran the
control without the earlier write, and with the 400 export's count moved to 208.

Fix: before the control, zero the count and the buffer (`memory.write(store, bytes(4), 208)` and
`memory.write(store, b"\0\0", 300)`), so both assertions are live. Or give `read` its own count
slot. Then state each expected failure as it will appear: S3 fails on the count (`0 == 2`) and on
the bytes.

### F2 (Low): the same "made, then failed" corner remains for Windows' reserved characters

The Scope line says names with `<>"|?*` or control characters need nothing, because "the walk's
open fails and the path is refused". That holds when the name is reached. But `_walk_windows`
returns at the **first** missing component, and only `_rewritten` checks the rest.
- So `root=C:\b\new\a*b` is returned as `missing ('new', 'a*b')` (EXECUTED in the model,
  `probe_077_names.out`).
- `_make_missing` then makes `new` and fails on `a*b` (`ERROR_INVALID_NAME`, which CPython maps
  to `EINVAL`, `PC/errmap.h` default; READ). The refusal "cannot be made" comes after a folder
  was made.

That is the corner F2 of 076's build review asked to close for device names, and no rule is
skipped. CPython's `_isreservedname`, which this spec follows for the names, refuses these
characters in the same function (`ntpath.py:300-303, 323-326`). Fix: add CPython's
`_reserved_chars` (`chr(0)` to `chr(31)`, `" * < > ? |`; `:` is already there, and `/` and `\`
never reach a component) to `_rewritten` and to the model, with one criterion-1 row, for example
`C:\b\new\a*b` with `may_make`, refused with nothing made. Or correct the Scope line to say
these names can leave the folders before them made. Folding them in makes `_rewritten` equal to
`ntpath.isreserved` for one component, which is easy to state and to check.

## Notes (no action required)

- N1. README wording: "refused, since Windows rewrites such names" is exact for `:`, trailing
  spaces and periods, and the classic devices. For `CONIN$`/`CONOUT$` say "or may treat as a
  device (as `ntpath.isreserved` does)".
- N2. Decision 4 says the verify step runs `pytest -q`; it does not (`release.yml:432`, no
  `-q`). The reason `-rA` is needed is pytest's default report, which names failures only. Fix
  the sentence.
- N3. Criterion 1's six-names coverage is complete: `com²`, `Com³`, `LPT¹`, `lpt²`, `lpt³`, plus
  `COM¹` in the root row. The fuzz count, 16,653, holds, since the unit case's alphabet is
  unchanged.

## Verdict

**Ready once F1 and F2** (F1: zero 208 and 300 before the control, and restate criterion 2's and
S3's failures; F2: CPython's reserved characters in `_rewritten`, or the Scope line corrected).
N1 and N2 can go with the build.

## One line

The eight names are right and, under the model, cannot make a chain wrong. But the control row's
count check reads the earlier write's value, and the reserved characters leave the same "made,
then failed" corner the device names just closed.

## Confirmation of 077's revision (addendum)

- **Date:** 2026-10-19. Same reviewer.
- **Reviewed:** `cba597e` against the draft `f7f248c` (`git diff f7f248c..cba597e`, the spec
  only, +179 −95; READ). I also read the author's new `build/077/probe_oracle.py` and its
  output. No git tree was touched.
- **Ran (EXECUTED, macOS, CPython 3.14.2, -B).** Beside this file:
  - `probe_control_zeroed.py` → `.out`: the control row in the raw case's real order, now with
    208 and 300 zeroed first.
  - `probe_casefold.py` → `.out`: every code point tried in every letter position of every
    reserved name. It compares the revision's `str.upper()` stem against `str.lower()` (076's
    rule) and against an ASCII-only case-insensitive comparison, which is how Windows'
    device-name check is INFERRED to compare (ASCII letters, plus the superscript digits
    Microsoft names).

### Each item

- **F1: fixed.** With the zeroing, both assertions are live (`probe_control_zeroed.out`):
  - the Design's export passes, with count 2 and bytes `b'or'`;
  - S3, the export put back at 400/408, fails on the count, `0`, and on the bytes, `b'\0\0'`;
  - a read that reads nothing fails both ways.

  Criterion 2's "seen failing" and S3's `0 == 2` are now what happens.
- **F2: fixed.**
  - `_WIN_RESERVED_CHARS` is CPython's `_reserved_chars` less `/` and `\`, which never reach a
    component, and with `:` kept in its own test.
  - `root=C:\b\new\a*b` is a criterion-1 row, and S5 guards it.
  - The Scope line's correction is written in.
  - The author's oracle probe, re-read: over 18,275 names, the revised rule differs from
    `ntpath.isreserved` on 0, and the lower-cased rule on 76, all with `ı` (READ; the output
    matches the script).
- **The oracle unit case: accepted.**
  - It counts names, not time, and asserts its count and that both answers occur.
  - The `x\` prefix stops a leading `D:` being read as a drive.
  - It skips below 3.13, but the judge and the release run 3.14.2, so the skip never applies
    where the judge counts. On Windows `ntpath` uses its C `splitroot`; for `x\<name>` that only
    splits off the `x`, so the oracle's answer is the same there. The Windows verify step's run
    of the case shows it.
- **N1: taken.** The README names the characters and says `CONIN$` and `CONOUT$` are refused out
  of caution, as `ntpath.isreserved` refuses them. **N2: taken.** The reason for `-rA` is now
  right.

### Upper-casing against Windows' own case folding (the lane's question)

- **Which names change** (EXECUTED, `probe_casefold.out`). Over 191 one-letter variants:
  - The `str.upper()` rule refuses exactly one spelling the ASCII-only comparison does not:
    `CON\u0131N$`, the dotless `ı` in `CONIN$`, with or without an extension.
  - Nothing the ASCII-only comparison refuses is missed by `upper()` or by `lower()`.
  - No reserved name holds `K` or `S`, so the Kelvin sign and the long `ſ`, whose case mappings
    reach ASCII, cannot matter.
  - Full-width letters case-map only to full-width letters, so they match under no rule.
- **What Windows does with that one spelling.** Either it treats `conın$` as `CONIN$` (it does if
  its upcase table maps U+0131 to `I`, INFERRED), and `upper()` matches Windows where `lower()`
  would not. Or it does not, and refusing `conın$` is one false refusal of a name nobody needs.
  `CONIN$` itself is only "may be reserved" (CPython).
- **The walk model's verdicts.** A refusal comes before any open, so the set of refused names
  never touches the chain property: a larger refused set can only turn an accepted path into a
  refused one. The model's named rows and its fuzz alphabet hold no `ı`. With the eight names in
  both sets, my fuzz gave 0 wrong chains (`probe_077_names.out`). So upper-casing changes no
  verdict the model relies on, and it moves only one spelling, toward refusal.

### Anything new that is wrong

Nothing.
- One wording nit: a name with `*` keeps 076's message, "a name Windows rewrites", though Windows
  rejects rather than rewrites it. The README explains the difference, and Decision 3 keeps the
  message on purpose, so 076's rows stand. No action needed.
- `_rewritten` still sees only the components after the drive, so the `?` of a `\\?\` prefix is
  never checked (READ in 076's code).

### Verdict

**Confirmed for build.**

### One line

The control row now reads live values, and `_rewritten` equals `ntpath.isreserved` for one
component. Upper-casing adds a single spelling, `CONIN$` with a dotless `ı`, to the refused set
and cannot make a chain wrong.
