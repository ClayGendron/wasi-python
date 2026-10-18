# How wasi-libc's GB18030 decoder defect was found and checked

- **Found** by spec 046's pre-build review (2026-10-18, finding 2). It measured every encoding
  over its whole BMP repertoire, guest against native lxml. GB18030 was the one row where text
  came back wrong with no error (`context/reviews/046-lxml-and-047-regex-spec-2026-10-18.md`;
  the outputs in `context/upstream/8-libxml2-input-without-dup/evidence/encodings_whole_repertoire.txt`).
  The review guessed "a defect in musl's GB18030 decoder as wasi-libc ships it" (INFERRED
  there). Spec 046, Decision 9, refuses GB18030 with a link-time `iconv_open` wrap (sketched in
  `context/upstream/8-libxml2-input-without-dup/evidence/iconv_guard_sketch.c`). It left a
  wasi-libc report to question 80's form. The owner asked for this sheet (decision 82(d)).
- **Located and explained** for this sheet (2026-10-18):
  - wasi-libc `161b3195`'s `libc-top-half/musl/src/locale/{iconv.c,gb18030.h,../../VERSION}`,
    fetched by `raw.githubusercontent.com` URL into the session's scratch folder (not the
    repository; SHA-256 recorded in `facts.md` and `evidence/gb18030_sim.txt`). `161b3195` is
    the commit `scripts/00_download.sh:102` names as wasi-sdk 33's. The pinned SDK ships only
    compiled `libc.a`, so its source is read from that commit. The prior-art clone
    (`context/prior_art/wasi-libc`, `165235b`) is newer, and its `iconv.c` differs from the
    pinned one (EXECUTED, `diff`).
  - musl master's `src/locale/iconv.c`, the cgit log of that file, commit `67219f0`'s patch and
    its `gb18030utf.h`, the `v1.2.6` tag and `iconv.c` at that tag, `WHATSNEW`, and the patches
    of `e5adcd9` and `7ada6dd`. All were fetched from `git.musl-libc.org` into the scratch folder
    and read. No musl or wasi-libc code is stored in this repository.
- **Modelled** (EXECUTED 2026-10-18, darwin-arm64): `uv run -q --no-project --python 3.13.11
  python -I evidence/gb18030_sim.py gb18030.h gb18030utf.h` → `evidence/gb18030_sim.txt`. The
  model is ours and follows the pinned loop step by step. It counts table values with bisection
  instead of a full scan, which gives the same count: the C test `v - d <= c - d`, in unsigned
  arithmetic, means `d <= v <= c`. Its 1,617 count, its 21 runs and its two end points equal the
  guest's. That is the check that the model is the code the guest ran.
- **Not run:** the fixed decoder in a guest (no wasi-libc was rebuilt; the "after" numbers are
  the model's). The four-byte supplementary-plane forms in a guest. The Shift_JIS out-of-bounds
  read's visible effect (the cp932 document already fails at an earlier byte). musl's and
  wasi-libc's views on AI-written mail or issues (not read).
- **README row, for when this lands** (for `context/upstream/README.md`'s table):
  `| 15-wasi-libc-gb18030-decoder/ | wasi-libc (musl) | GB18030 four-byte characters above the surrogates decode 0x800 or more too low (1,617 of 56,926 BMP characters, no error); musl fixed it on master (67219f0, after 1.2.6), wasi-libc has not taken it | a facts sheet (question 82(d), question 80); spec 046 refuses GB18030 by a recipe until a wasi-sdk carries the fix |`
