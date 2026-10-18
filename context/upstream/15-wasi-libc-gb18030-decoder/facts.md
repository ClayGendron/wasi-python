- **Project:** wasi-libc (https://github.com/WebAssembly/wasi-libc), whose `libc-top-half/musl` is a subtree of musl (https://git.musl-libc.org/cgit/musl)
- **Against:** wasi-libc `161b3195` (the commit wasi-sdk 33 names, `scripts/00_download.sh:102`; its musl subtree says 1.2.5)
- **Status:** drafted
- **Title:** iconv: take musl's GB18030 decoder fix (67219f0): four-byte forms above the surrogates decode to the wrong character
- **Files:** libc-top-half/musl/src/locale/iconv.c, libc-top-half/musl/src/locale/gb18030utf.h (new)
- **Why we carry it:** spec 046 (lxml; confirmed for build, not yet built) carries a recipe, not a patch: `recipes/iconv_refusals.c`, linked with `-Wl,--wrap=iconv_open`. It refuses GB18030, so libxml2 raises "Unsupported encoding: gb18030" and never returns wrong text. Without it, 1,617 of 56,926 characters in a GB18030 document read back as other characters, with no error.

**This is a facts sheet, not an issue or a pull request** (question 82(d); decision 80). The
owner writes in their own words. wasi-libc's clone has no contributor guide and no rule on
AI-written contributions (READ: `README.md`, `CODE_OF_CONDUCT.md`, `libc-top-half/README.md` at
`165235b`). musl takes patches and reports on its mailing list. Its policy on AI-written mail was
not read. Nothing has been posted, and no agent will post anything.

**The short version.** musl has already fixed this bug, on master, after its 1.2.6 release.
wasi-libc's main branch has not taken that fix. So the ask is mainly to wasi-libc: take musl
commit 67219f0, and then ship it in a wasi-sdk release. musl needs no new report. The owner
might ask musl when a release will carry it.

## The facts

1. **What the guest saw** (EXECUTED by spec 046's review and again on spec 046's revised
   scratch binary; `context/upstream/8-libxml2-input-without-dup/evidence/encodings_whole_repertoire.txt`,
   line 21). lxml in the guest parsed a GB18030 XML document holding every BMP character that
   CPython's `gb18030` codec encodes. The script skips surrogates, private use U+E000 to U+F8FF,
   U+FFFE and U+FFFF (`encodings_whole_repertoire.py`, `chars()`). Result: 1,617 of 56,926
   characters came back as other characters, with no error. The wrong ones are the four-byte
   forms of U+F900 to U+FFFD. U+F900 reads as U+F100, and U+FFFD reads as U+F750, in 21 runs
   (the review, `context/reviews/046-lxml-and-047-regex-spec-2026-10-18.md`, finding 2).
   Native lxml with GNU libiconv 1.18 read 56,925 of 56,926 correctly (the one difference,
   U+1E3F, is a GB18030 edition change, not this bug; INFERRED).

2. **The decoder that does it** (READ: wasi-libc `161b3195`,
   `libc-top-half/musl/src/locale/iconv.c:405-441`; fetched by raw URL into a scratch folder,
   SHA-256 `d04b46b1e88f70e31681c21f7208464306dd4011457bb7ec114fb97f7c44aec2`). For a
   four-byte sequence, lines 419-425 compute the linear index. Lines 426-435 then turn it into a
   code point. They add 128, then keep adding the number of 2-byte-table values at or below the
   running result, scanning the whole 126×190 table each time. So the index counts every code
   point from U+0080 that the 2-byte table does not hold. **But GB18030's four-byte BMP mapping
   skips the surrogates, U+D800 to U+DFFF.** The loop does not skip them. So every four-byte
   character above the surrogate block decodes at least 0x800 (2,048) code points too low.
   U+F900 − 0x800 = U+F100, which is what the guest saw (INFERRED from the code; the model in
   item 3 shows it).

3. **A model of that loop matches the guest exactly** (EXECUTED 2026-10-18,
   `evidence/gb18030_sim.py`, output in `evidence/gb18030_sim.txt`). The model follows lines
   419-435 step by step, against the pinned `gb18030.h` (SHA-256 `5483eb15…6b78d`). The table
   has 23,940 distinct non-zero values. The model uses CPython's own codec as the truth, over the
   same repertoire as item 1:
   - 35,054 of the 56,926 characters are four-byte;
   - **1,617 decode to another character**, all from U+F900 to U+FFFD, with shifts from 0x800
     to 0x8AD (21 distinct shifts, matching the review's "21 runs");
   - `84 30 81 31` (U+F900) → U+F100, and `84 31 a4 37` (U+FFFD) → U+F750, the same as the
     guest.

   Outside the BMP the model goes wrong too: `90 30 81 30` (U+10000) → U+3404C, and `e3 32 9a 35`
   (U+10FFFF) → U+13404B, which is not a Unicode code point at all. **This part was not run in
   the guest** (spec 046's check covers the BMP only), so it is INFERRED from the model.
   Pinned `iconv.c:544` turns a result that UTF-8 cannot encode into `EILSEQ`. A wrong
   result still inside Unicode, such as U+3404C, would pass through silently (READ; INFERRED).

4. **musl fixed it on master, after 1.2.6** (READ, git.musl-libc.org, 2026-10-18).
   - Commit `67219f0130ec7c876ac0b299046460fad31caabf`, "fix pathological slowness & incorrect
     mappings in iconv gb18030 decoder", Rich Felker, authored 2026-03-30 (cgit's log dates it 2026-04-02). It adds
     `src/locale/gb18030utf.h` (206 ranges of code points the 2-byte table does not hold) and
     changes `iconv.c` by 24 lines added and 9 removed. Its message names both defects: "wrong
     results for BMP characters above the surrogate range, as a result of not correctly
     accounting for it being excluded, and for characters outside the BMP". It also names a
     third: up to "tens of thousands" of table scans per character, "run times exceeding an
     entire second per character".
   - The same model with the fix's table (`after` in `evidence/gb18030_sim.txt`): **0 wrong**
     over the same 35,054 four-byte characters. U+10000, U+1F600 and U+10FFFF decode correctly
     (EXECUTED, the model; not run in a guest).
   - The commit says a few mappings are still wrong. These are edition changes that swapped
     private-use code points for real characters, and "a postprocessing step … will be added
     later". No later commit to `src/locale/iconv.c` appears in musl's log as of 2026-10-18
     (READ, the cgit log of that file).
   - musl 1.2.6 was tagged on 2026-03-20 (READ, the tag's commit `9fa28ece75`). Its
     `src/locale/iconv.c` has no `gb18030utf` (EXECUTED: `grep -c gb18030utf` → 0). So **no
     musl release carries the fix yet**.

5. **wasi-libc does not carry it yet** (READ). wasi-libc main at `165235b` (2026-09-30, the
   clone in `context/prior_art/wasi-libc`) has a musl subtree at 1.2.6. Its `iconv.c` equals
   musl master's except for the GB18030 hunk of 67219f0 (EXECUTED: `diff`). The pinned
   `161b3195` (musl 1.2.5) has the old decoder too. wasi-libc's `libc-top-half/README.md`
   updates musl by `git subtree pull … v1.2.6 --squash`, by release tag. So a plain subtree
   update would not bring the fix in until musl tags a release that has it (INFERRED).

6. **Why it matters on WASI** (INFERRED). wasi-libc's iconv is the only character conversion a
   static `wasm32-wasip1` program has, unless it carries GNU libiconv. libxml2 (and so lxml) uses
   it for every non-UTF encoding. GB18030 is China's national standard encoding (general knowledge, not checked here).
   Getting the wrong character with no error is worse than getting an error. The slowness in
   item 4 also costs fuel or time in a metered guest (not measured on its own here).

## Adjacent, in the same file (not this ask; for the owner's picture)

The pinned `161b3195` lacks two Shift_JIS checks that musl added and wasi-libc main (`165235b`)
already has (READ, the `diff` above, and musl's log):

- musl `7ada6dd` (2024-03-02), "iconv: fix missing bounds checking for shift_jis decoding". In
  the pinned code, lead bytes 0xEB to 0xEF give a row of 84 to 93 (`iconv.c:331-334`). The
  `jis0208` table has only 84 rows (0 to 83), so the read goes past the end of the table.
- musl `5e594ae` (2025-02-09), "iconv: fix erroneous decoding of some invalid ShiftJIS
  sequences". In the pinned code, a trail byte outside both ranges falls through unadjusted
  (`iconv.c:335-342`).

These reads stay inside the guest's linear memory, so the sandbox still holds (INFERRED). They
come in with any wasi-sdk built on wasi-libc main, so they need no separate ask (INFERRED). The
pinned code already has the EUC-KR fix for CVE-2025-26519 (musl `e5adcd9`): its line 498 is that
commit's new line (READ, both).

## What the owner might ask

- **wasi-libc:** take musl's `67219f0` (both files) into `libc-top-half/musl` before musl tags a
  release with it, or say when they expect to. Item 3's numbers and the shape of the bug are the
  evidence. A wasi-sdk release that ships the fix lets this project delete
  `recipes/iconv_refusals.c` and its link flag. Spec 046's encodings check turns red on the day
  the decoder's output changes, which shows when to delete them.
- **musl** (optional): when a release will carry `67219f0`, and whether the postprocessing step
  it mentions is planned.
