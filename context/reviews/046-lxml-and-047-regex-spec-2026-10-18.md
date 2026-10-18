# Review of 046 — lxml, with libxml2 and libxslt — and 047 — regex (the specifications, before build)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the
  constitution (§4.1, §4.2, §4.4, §4.9 to §4.12, §4.15, §5.2, §5.6, §5.7, §6, §7), both
  specifications, both facts-sheet folders in full (`../upstream/8-libxml2-input-without-dup/`
  and `../upstream/9-regex-callback-signatures/`: `pr.md`, `fix.patch`, `notes.md`,
  `evidence/`), questions 80 and 82, and the 043 pre-build review (its §4.1 reasoning on forced
  headers). Code read: `scripts/gen_inittab.py`, `scripts/steps/35_stdlib_libs.sh` and
  `60_link.sh` (the link flags), `tests/harness/artifacts.py` (`host_fact_errors`,
  `sdk_builder_path_errors`), `tests/harness/jobs.py` (`oracle_env`), `src/wasi_python/runner.py`
  (output capture), CPython 3.15.0's `Python/importdl.c` and `Python/import.c` (the package
  context), numpy 2.5.2's `numpy/f2py/rules.py`. Upstream sources read from the pinned tarballs
  (below): libxml2 2.15.4 (`xmlIO.c`, `catalog.c`, `configure.ac`, `configure --help`,
  `threads.c`, `dict.c`, `parser.c`, `xpath.c`, `Copyright`, every file's header), libxslt
  1.1.45 (`security.c`, `documents.c`, `Copyright`, every file's header), lxml 6.1.3
  (`parser.pxi`, `xslt.pxi`, `xmlerror.pxi`, `extensions.pxi`, `saxparser.pxi`, `xsltext.pxi`,
  `serializer.pxi`, `pyproject.toml`, `LICENSES.txt`, the generated C's heads), regex 2026.9.29
  (`src/_regex.c`, `setup.py`, `PKG-INFO`, `LICENSE.txt`), scipy 1.18.1 (037's scratch tree:
  every `PyModule_Create`, the `meson.build` module lists), Pillow 13.0.0 and kiwisolver 1.5.1
  (their init functions). Each claim below is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/046-lxml.md` and `context/specifications/047-regex.md`
  as drafted (committed in `5be7721`), and their facts sheets.
- **Ran (EXECUTED, darwin-arm64).** Nothing in `src/`, `tests/`, `scripts/`, `recipes/`,
  `downloads/`, the specifications or the upstream folders was edited; `scripts/build.sh` and
  the judge were not run. Python ran only through `uv run` (the guest through the repository's
  `wasi_python`; native lxml on the line's CPython 3.15.0 from `build/oracle/venv` with the
  drafting's unpacked lxml 6.1.3 universal2 wheel, by `uv run --no-project --python …`).
  Everything is under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/046-review/`:
  - `set/base/`: a copy of `build/sets/s-8d84b3b190fe9bce`; `set/scratch-python.wasm` and
    `set/scratch-zipc.zip`: copies of the drafting's scratch binary (SHA-256 `958fa1f6…ca3ec`,
    the one `evidence/guest.txt` names; 36,110,233 bytes) and zip; `set/python-regex-only.wasm`
    (32,476,722 bytes).
  - `src/`: the four pinned tarballs, unpacked; their SHA-256 recomputed and equal to the specs'
    pins (`98087fd1…8821`, `9acfe684…216e`, `45222d94…dd21`, `8b5fcc47…42cb`). `pt/`: both
    `fix.patch` files dry-run on pristine copies (`patch -p1 --dry-run`: no offset, no fuzz;
    `git apply --numstat`: 40/2 in `xmlIO.c`, 5/5 in `src/_regex.c`).
  - `tools/rg.py` (one program on a scratch plain reactor with `/data` read-only, `/prog`
    read-only, `/out` writable), `tools/rboth.py` (today's plain and snapshot binaries),
    `tools/fuel.py`, `tools/ctors.py` (the drafting's constructor reader), `tools/imports.py`,
    `tools/layout.py` (stack pointer and data segments), `tools/scan_sigs.py` (method, getset
    and slot tables against definitions).
  - `prog/`: `fd_probe.py`, `fd2.py` to `fd5.py` (descriptor ownership), `enc_breadth.py`,
    `enc_fail.py`, `enc_wrong.py`, `gb_ranges.py` (encodings over each codec's whole BMP
    repertoire), `safety.py`, `html_meta.py`, `names.py` (every dotted builtin's `__name__`),
    `regex_sweep.py` (every public method of regex's four objects); their outputs beside them
    (`enc-guest.txt`, `enc-native.txt`, `enc-fail-*.txt`, `html-*.txt`, `regex-sweep-guest.txt`).
  - `shim/`: a feasibility sketch for finding 4 (a reference-counting `dup`/`close` header),
    compiled only.

## What holds

- **The libxml2 patch owns each descriptor exactly once.** READ: on WASI `xmlInputFromFd`
  reads the caller's descriptor and frees with `xmlFdFree` (no close), which is what every
  public caller of `xmlInputFromFd` (`xmlCtxtNewInputFromFd`, `xmlReaderForFd`,
  `xmlReaderNewFd`, the `-` stdin path) documents; `xmlParserInputBufferCreateUrl` switches the
  buffer to `xmlFdClose` only on success and closes the descriptor itself on every failure
  (including `xmlMalloc` failing inside `xmlInputFromFd`); the `-` output path never closes
  standard output. No other code in the library calls `dup` once zlib is off (READ: the third
  call is in the `XML_INPUT_UNZIP` branch). EXECUTED in the scratch guest (`fd_probe.py`,
  `fd2.py`, `fd3.py`, `fd4.py`): the descriptor number the next `os.open` receives did not
  move across 3,000 parses by path, 500 `iterparse` runs, 500 missing files, 500 malformed
  files, 2,000 writes by path, 51 XSLT `document()` transforms and 300 XIncludes (a leak would
  make it climb); two Python files held open across 200 parses and writes were still readable
  afterwards (no stray close hit them); two `write("-")` calls in a row left standard output
  usable. One shift seen in `fd_probe.py` (7 to 9 after Python files were opened and closed) is
  the runtime's descriptor reuse order, not lxml: `fd5.py` on today's binary, with no lxml at
  all, shows the same 7 to 9 (EXECUTED). The patch applies to the pristine tarball with no
  offset (EXECUTED).
- **The regex patch is five and only five.** EXECUTED (`scan_sigs.py` over `src/_regex.c`): of
  74 method, getset and slot entries, the mismatches are exactly `match_capturesdict`,
  `match_allcaptures`, `match_allspans` (`METH_NOARGS`, one parameter) and `pattern_groupindex`,
  `pattern_pickled_data` (getters, one parameter); the other getters take `(self, void*)`, the
  other `METH_NOARGS` methods take `(self, PyObject*)`, the two casted mapping slots match
  `lenfunc` and `binaryfunc`, and the type slots are assigned without casts (the compiler checks
  them). EXECUTED (`regex_sweep.py` on the scratch binary): every public method and attribute of
  a pattern, a match, a scanner and a splitter, called with plausible arguments, then `len(m)`,
  `m[1]`, `copy`, `deepcopy`, a pickle round trip and both module functions: no trap.
- **lxml's own callbacks are typed right.** READ: every callback lxml casts into libxml2 or
  libxslt (`_receiveError`, `_receiveParserError`, `_receiveXPathError`, the variadic
  `_receiveXSLTError`, `_receiveRelaxNG*Error` and `_nullGenericErrorFunc`, `_local_resolver`,
  `_xslt_doc_loader`, `_xpath_function_call`, `_callExtensionElement`, the four SAX handlers,
  `_writeFilelikeWriter`) has the parameter count of the type it is cast to; libxml2 and
  libxslt themselves cast no function into a callback type (one cast of a lookup result). So the
  regex class of trap is not expected in lxml (INFERRED from READ; the drafting's probe ran the
  error paths without a trap, EXECUTED by the drafting).
- **No new channel, no new constructor.** EXECUTED: the scratch binary imports the same 43
  functions as today's (WASI preview 1 and `host`); its constructor list is today's plus only
  the scratch inittab's `register_extra` (`ctors.py`), as Decision 3 says for `-DLIBXML_STATIC`
  (READ: `threads.c:504-509`, the destructor is guarded by `!defined(LIBXML_STATIC)`).
- **A deep recursion traps instead of corrupting memory.** EXECUTED (`layout.py`): today's
  `python.wasm` keeps the 16 MiB stack first (stack pointer 16,777,216; data from 16,777,216),
  so an overflow from libxml2's XPath recursion (limit 5,000, READ) or libxslt's template depth
  runs off address zero and traps.
- **Today's builtins already keep their names.** EXECUTED (`names.py` through `rboth.py`): all
  58 dotted builtins of today's set import with `__name__` equal to their import name on both
  binaries; on the scratch binary all 61 do (lxml's two use multi-phase init; regex's with the
  header). This is 047's general check, and it is green today.
- **The generated C is sound to use.** READ: `etree.c` and `objectify.c` start with
  `/* Generated by Cython 3.2.9 */`; they are bytes of the hashed sdist, so they are as
  deterministic as any other pinned C; their `__pyx_f` file names are relative; the modules use
  multi-phase init (`CYTHON_PEP489_MULTI_PHASE_INIT 1`); lxml's own `pyproject.toml` caps Cython
  at `<3.3`, so regenerating with the line's 3.3.0 would build a configuration lxml does not
  support. The step's first-line check is the right guard.
- **The growth and the imports reproduce.** EXECUTED: 32,476,722 − 31,760,992 = +715,730 for
  regex and 36,110,233 − 32,476,722 = +3,633,511 for lxml; `import lxml.etree` 559,299,688,
  `import lxml.html` 643,929,233 and `import regex` 479,375,151 fuel on the scratch plain reactor
  with the scratch zip, each within 0.3% of the specifications' numbers.
- **`lxml.html` serialization is the same on 2.14.6 and 2.15.4.** EXECUTED (`html_meta.py`):
  three documents (with `<meta charset>`, with the `http-equiv` form, with none), each through
  `lxml.html.tostring` with five option sets and through `etree.tostring(method="html")`: the
  guest's output equals native's line for line. Decision 10's `<meta charset>` line in the
  golden is safe; only XSLT's `method="html"` differs, as it says.
- **The safety defaults reproduce.** EXECUTED (`safety.py`, guest and native): the default
  parser refuses an external entity; `resolve_entities=True` reads a granted file; a `../`
  escape out of a grant and an `http:` URL both fail to load; billion laughs raises
  "Maximum entity amplification factor exceeded", with `huge_tree=True` too; `exsl:document`
  into a read-only grant, to `/tmp` (no grant) and into a missing folder of a writable grant
  all raise "unable to save" (the last natively too: with no access control libxslt makes no
  folder). Finding 5 adds one case the text misses.

## Acceptance criteria against evidence

046:
1. Seen failing first: holds as written; the build failure without the patch is in the facts
   sheet (EXECUTED by the drafting) and the patch applies cleanly (EXECUTED here).
2. Full build: holds in design, with finding 1's flag in step 36's configure line.
3. Same bytes everywhere: **fails as designed** (finding 1): the binary would carry the build
   host's folder.
4. The patch is its sheet: holds (EXECUTED: dry run, numstat 40/2).
5. The numbers: holds, with finding 7 on how the plain-start delta is measured.
6. The judge: holds, with finding 1's binary scan and finding 2's encodings check in the
   judge-change list.
7. Dry run: nothing to check before build.

047:
1. Seen failing first: holds (EXECUTED by the drafting: each of the five calls traps alone).
2. Full build: holds; the patch applies with no offset (EXECUTED).
3. Same bytes: holds in design (no configure; one C pair, one header).
4. The patch is its sheet: holds (EXECUTED: numstat 5/5).
5. The numbers: holds (EXECUTED: +715,730 bytes; `import regex` fuel within 0.3%), finding 7
   applies.
6. The judge: holds today, but finding 3 says what turns its general check red.
7. Dry run: nothing to check before build.

## Findings, most severe first

1. **046: libxml2 compiles the build host's folder into the binary, through its default
   catalog path.** High: criterion 3 (spec 012's same bytes, and 040's) cannot pass, and the
   artifact names the builder's disk.
   - READ: `catalog.c:57-58` defines `XML_XML_DEFAULT_CATALOG` as `"file://" XML_SYSCONFDIR
     "/xml/catalog"` (under `#ifndef`), and `configure.ac:1022-1023` sets `XML_SYSCONFDIR` from
     `$sysconfdir`, which is `$prefix/etc`. Decision 3 configures `--prefix=$B/xml-libs`, so the
     string is `file://<checkout>/build/xml-libs/etc/xml/catalog`. `-ffile-prefix-map` rewrites
     `__FILE__` and debug paths, not a `-D` string from `config.h`.
   - EXECUTED: the drafting's `config.h:100` holds `XML_SYSCONFDIR "<scratch>/046-spec/b/xml2-inst/etc"`;
     `strings` finds `file://<scratch>/046-spec/b/xml2-inst/etc/xml/catalog` in its
     `libxml2.a` and in the scratch `python.wasm`. Today's `python.wasm` holds no `/Users/` and
     no `claygendron` (0 matches). A main tree, a `spec/NNN` worktree, the macOS runner and the
     Linux containers all build at different paths, so `SHA256SUMS` differ.
   - Also INFERRED: in the guest, a resolution through the catalog (a DTD by public ID, for
     instance) would try to open the host's build path inside the guest.
   - **Fix:** add `-DXML_XML_DEFAULT_CATALOG='"file:///etc/xml/catalog"'
     -DXML_SGML_DEFAULT_CATALOG='"file:///etc/sgml/catalog"'` to step 36's libxml2 `CFLAGS`
     (`catalog.c` honours both under `#ifndef`; this is native Linux's value), or configure with
     `--sysconfdir=/etc` (READ: `make install-data` installs nothing under `sysconfdir`). Say in
     the README that a catalog is read only if an embedder grants a folder at `/etc/xml`. And add
     a v1.1 judge check, general for every later package: neither binary holds the bytes of
     `paths.REPO` (the binary-side twin of `host_fact_errors`); it is green today (EXECUTED: 0
     matches) and red on the scratch binary.

2. **046: Decision 9's encodings table rests on two characters per encoding, and over the
   whole repertoire wasi-libc's iconv parses three of the "agreeing" encodings differently,
   one of them silently.** Medium: §4.11 asks that platform semantics be documented, not
   disguised, and the golden's "agreeing set" would hide the differences.
   - READ: `evidence/encodings.py` and the probe test one short string per encoding ("日本",
     "中文", "한국").
   - EXECUTED (`enc_breadth.py`, every BMP character Python's codec can encode, one element
     each, guest against native lxml 6.1.3 with libxml2 2.14.6 and GNU libiconv):

     | encoding | guest parse | native parse | guest write | native write |
     |---|---|---|---|---|
     | windows-1252, ISO-8859-2, ISO-8859-15, cp1251, KOI8-R, TIS-620, UTF-16 | all equal | all equal | equal | equal (same SHA-256) |
     | Shift_JIS | 3 of 6,944 differ | 0 | 3 differ | 2 differ |
     | ISO-2022-JP | 1 of 6,881 differs | 0 | 1 | 0 |
     | **cp932** | **the document fails** (`Invalid bytes`) | 6 of 7,395 differ | 460 differ | 6 |
     | **EUC-JP** | **the document fails** | 2 of 13,010 | 6,069 differ | 2 |
     | **GB18030** | **1,617 of 56,926 decode to the wrong character, no error** | 1 | `LookupError` | 19 |
     | GB2312 | 2 of 7,445 differ | 0 | `LookupError` | 0 |
     | GBK, cp949 | all equal | all equal | `LookupError` | equal |
     | Big5, cp950 | the document fails | the document fails | `LookupError` | 0 / 1 |

     Per character (`enc_fail.py`, `enc_wrong.py`, `gb_ranges.py`): cp932 fails on its NEC row
     13 and IBM extensions (lead bytes `0x87`, `0xED`: 103 characters, among them №, ℡ and the
     Roman numerals) and reads 351 others as their JIS forms (`81 60` → U+301C, not U+FF5E);
     EUC-JP fails on every JIS X 0212 character (lead byte `0x8F`: 6,066); GB18030's four-byte
     forms of U+F900 to U+FFFD come back shifted (U+F900 → U+F100, U+FFFD → U+F750) in 21 runs.
     The last is neither Python's mapping nor GNU libiconv's (INFERRED: a defect in musl's
     GB18030 decoder as wasi-libc ships it).
   - **Fix:** rewrite Decision 9 from a whole-repertoire run, as the table above, and name
     each partial encoding with what fails. Make the golden's "agreeing set" the first row
     (plus GBK and cp949 for parsing only). Make the v1.3 encodings case assert the
     whole-repertoire outcome of each documented encoding, so a wasi-sdk update that changes
     musl's tables shows as a red check. Give the README the workaround that keeps Python's
     complete codecs: decode the bytes with Python, re-encode as UTF-8, and parse with
     `etree.XMLParser(encoding="utf-8")`. Decide in the text whether GB18030 should fail loudly
     instead of decoding wrong (a recipe can refuse it, for example a forced header for
     `encoding.c` whose `iconv_open` returns `EINVAL` for `GB18030`; libxml2 then raises its
     unsupported-encoding error); if it stays, say "silently wrong" in those words. A
     wasi-libc/musl report is worth drafting under question 80's form.

3. **047: the general builtin-name check meets scipy's single-phase modules, and neither 047
   nor 037/038 says what then.** Medium: under decision 48's order (047 after 038), 047's builder
   starts from a set whose dotted builtins do not all pass its new check; under question 82's
   proposed order (047 first), 037's builder meets a red v1.1 check its text does not mention.
   - READ: numpy 2.5.2's f2py template creates every module with `PyModule_Create(&moduledef)`
     (`numpy/f2py/rules.py:257`), and scipy 1.18.1 builds f2py modules (`linalg/_fblas`,
     `_flapack`, among others in its `meson.build` files) and three hand-written single-phase
     modules (`odr/__odrpack.c`, `integrate/__quadpack.h`, `_lib/_uarray/_uarray_dispatch.cxx`).
     CPython gives a builtin no package context (`importdl.c:173`, `.newcontext=NULL`), so each
     keeps its short name, as `_regex` did. Pillow 13 and kiwisolver 1.5.1 use multi-phase
     init, and pybind11 3.1.0 does too (READ), so 023 and 043 pass.
   - INFERRED: once 037 lands, `test_dotted_builtins_keep_their_import_names` reports at least
     `scipy.linalg._fblas`, `scipy.linalg._flapack`, `scipy.odr.__odrpack`,
     `scipy.integrate._quadpack` and `scipy._lib._uarray._uarray`.
   - **Fix (preferred): name every dotted builtin the way a native import does, once, in the
     generated inittab.** `gen_inittab.py` can emit, for each entry, a wrapper that sets the
     package context around the real init function:
     `old = _PyImport_SwapPackageContext("regex._regex"); m = PyInit__regex();
     _PyImport_SwapPackageContext(old); return m;`. READ in CPython 3.15.0: this is exactly
     what `_PyImport_RunModInitFunction` does for a shared library (`importdl.c:435-437`), and
     `PyModule_Create2` then takes the dotted name (`import.c:911-921`,
     `moduleobject.c:363`); multi-phase modules ignore it. It needs `Py_BUILD_CORE` for the
     glue's one declaration, and it is a recipe (generated code), not a patch. It makes
     `recipes/regex_module_name.h` unnecessary and fixes scipy's modules for free. Measure it on
     the scratch binary before choosing (pickle bytes against native, as Decision 4 did).
     **Or**, keep the header and write into 047 (and into 037/038 by amendment) which order
     carries which fix, and what the check does in between; an exemption list in the check
     would weaken the judge and is not a fix.

4. **046: the facts sheet dismisses the recipe alternative in one clause.** Low, §4.1. The
   notes say a reference-counting `close` "would be a hidden source change". EXECUTED
   (`shim/`): a forced-include header that maps `dup` and `close` in `xmlIO.c` alone to a
   twenty-line counting pair compiles the pristine `xmlIO.c` under libxml2's own warning flags
   (`-pedantic -Wall -Wextra`) with no warning; INFERRED, it gives the same ownership as the
   patch at all three `dup` sites. So a recipe is possible, and §4.1 asks for one first. I still
   think the patch is the better choice, for the reason the 043 review accepted (a forced header
   that redefines a libc call changes upstream code without showing it; the patch is the
   smaller, visible, upstreamable change, and it is deleted when upstream takes it). **Fix:** say
   so in the notes and in Decision 4 in those terms (both forms, why the patch), rather than
   "cannot be honest". Also a nit in `pr.md`'s "What it does not cover": on WASI with zlib,
   `xmlOutputDefaultOpen("-")` with compression would hand `STDOUT_FILENO` to `gzdopen`, whose
   `gzclose` closes it, and its failure branch calls `close(fd)` unconditionally; say that the
   `owned` flag does not cover the zlib branch either.

5. **046: an XSLT `document()` resolves the external entities of what it loads, whatever the
   parser's defaults.** Low-Medium (§4.15 documentation). EXECUTED, guest and native alike
   (`safety.py`): a stylesheet with no access control that calls `document('…/ent.xml')`, where
   `ent.xml` declares `<!ENTITY e SYSTEM "secret.txt">`, returns the secret file's text; with
   `XSLTAccessControl.DENY_ALL` or `read_file=False` it raises "read rights … denied". READ:
   libxslt loads documents with `XSLT_PARSE_OPTIONS` (`NOENT | DTDLOAD | …`), so lxml's
   `resolve_entities='internal'` does not reach them. Decision 7 says "external entities are
   not resolved" without the qualifier, and the README note names `DENY_ALL` only for writes'
   sake. **Fix:** Decision 7 and the README say that an untrusted stylesheet, or an untrusted
   document loaded by `document()` or `xsl:include`, can read any file in a grant, entities
   included, and that `DENY_ALL` (or `read_file=False`) closes it; pandas' `read_xml(stylesheet=…)`
   applies a stylesheet with no access control (READ). Add this case to the v1.3 safety check.

6. **046: `LICENSES/libxml2.txt` leaves out `list.c`'s notice.** Low, §4.12. READ: libxml2's
   `Copyright` names "the files dict.c and list.c" as the exceptions; `list.c`'s head carries
   its own ISC-style grant, "Copyright (C) 2000 Gary Pennington and Daniel Veillard"; `list.c`
   is compiled into every build. Decision 15 names `dict.c` and `timsort.h` only. A scan of every
   header in both trees found no other separate notice (EXECUTED). **Fix:** add `list.c`'s head
   to `libxml2.txt`, and have `assemble_artifacts.py` fail if a named file is missing.

7. **046 and 047: the plain-start fuel delta is smaller than the run-to-run spread.** Low,
   §4.10. EXECUTED (`fuel.py`, unseeded, as the drafting ran): today's binary and zip gave
   242,399,669 and then 241,903,106 for `-c pass` (a spread of 496,563 on the same bytes); the
   scratch binary gave 241,971,273 and 241,735,636. Decision 11's "+447,981 fuel (+0.19%)" is
   inside that spread. **Fix:** state the plain-start growth as measured by the judge's seeded
   guest (the ratchet's own runs), not as a single-run delta; drop the six-figure number from
   the specification or mark it as noise-bounded.

8. **046: the configure runs find the host's `pkg-config`.** Low (§4.8, spec 012's hygiene).
   EXECUTED: both drafting `config.log`s record `found /opt/homebrew/bin/pkg-config`. Nothing was
   queried through it this time (zlib, ICU and libgcrypt are off; libxslt is given
   `LIBXML_CFLAGS`/`LIBXML_LIBS`), but a host with different `.pc` files is one changed default
   away from a different configure. **Fix:** pass `PKG_CONFIG=false` to both configures (or an
   empty `PKG_CONFIG_LIBDIR`), and say so beside the other host facts.

9. **047: Apache-2.0 §4(b) asks that a modified file carry a notice of the change.** Low,
   §4.12. The release ships `_regex.c` only in object form, so the duty is arguable, but the
   cheap reading is to meet it: **Fix:** `LICENSES/regex.txt` ends with one line naming the
   carried patch and the forced-include header by path, as the CHANGELOG does.

10. **047: the general check costs about 5 G fuel on the plain binary.** Low. EXECUTED
    (`names.py`): importing all 58 of today's dotted builtins took 5,016,014,720 fuel on the
    plain reactor and 104,839,431 on the snapshot. **Fix:** say so in Decision 7 and give the
    check a fuel budget with room for scipy's builtins (or run its plain case once per judge
    run).

## Security

- **What reaches the host.** Nothing new. The guest's only channels stay WASI preview 1 and the
  door (EXECUTED: 43 imports, unchanged). libxml2 2.15 has no HTTP or FTP client
  (`--with-http` is now "ABI compatibility for removed HTTP support", off; READ), modules and
  plugins are off, zlib is off, and every file libxml2 or libxslt opens goes through
  `path_open` under the embedder's preopens (EXECUTED: a `../` escape and an `http:` URL fail).
  Catalogs stay on, and after finding 1 they read `/etc/xml/catalog` only if a grant puts one
  there; `XML_CATALOG_FILES` is read from the guest's environment, which the embedder sets.
- **XXE.** Off by default for the parser (EXECUTED); on for documents an XSLT loads (finding 5);
  both contained to granted folders.
- **Billion laughs.** Refused with and without `huge_tree` (EXECUTED); the guest's memory and
  fuel limits bound whatever gets past it.
- **XSLT writes.** `exsl:document` and `ElementTree.write` reach only writable grants
  (EXECUTED); no folder is created without access control. Decision 7's README text plus
  finding 5 is the right disclosure; nothing about the defaults needs the owner (§4.15 is
  unchanged).
- **Memory safety.** Stack overflow traps (EXECUTED: stack-first layout). libxml2 2.15.4 and
  libxslt 1.1.45 carry the upstream security fixes 2.14.6 and 1.1.43 lack (READ, Decision 2);
  that is a reason for the newer pins, and the price is the version gap the golden must
  respect.
- **Silent corruption.** Finding 2's GB18030 row is the one place this design returns wrong data
  without an error.

## Constitution checks

- **§4.1, patches few, recorded, temporary:** holds for both. The regex patch is unavoidable (a
  function's type cannot be changed by a recipe). The libxml2 patch is a choice between a patch
  and a forced header; the choice is right, its stated reason is not (finding 4). Both facts
  sheets follow question 80's form; nothing is sent.
- **§4.2, every input pinned:** holds (EXECUTED: four hashes equal the pins).
- **§4.3 and §4.4, one target, two channels:** holds (EXECUTED).
- **§4.7, prior art studied, not copied:** holds as far as I can see: boomslang's change adds a
  function; this one reuses `xmlFdFree` (READ the notes; I did not diff boomslang's patch).
- **§4.9, tests count:** holds.
- **§4.10, claims carry evidence:** holds, except Decision 9's "as natively" (finding 2) and
  the fuel delta (finding 7).
- **§4.11, platform semantics documented:** needs finding 2 and finding 5.
- **§4.12, licences:** approved by decision 43; finding 6 and finding 9 are notices; question
  82(b) and (c) are the owner's.
- **§4.15, safe by default:** holds; no default loosened. Finding 5 is documentation.
- **§5.2, no open questions:** 046 holds; 047 holds once finding 3 decides its order story.
- **§5.6 and §5.7:** this review; each is build-class and overlaps no other.
- **Spec 012 / 040:** fails for 046 until finding 1.
- **§6 order:** question 82(a) is sound on dependencies (neither needs scipy), with finding 3's
  caveat that 047's check and scipy's modules must be reconciled in whichever lands second.

## Disposition (filled in by the author, then confirmed by the reviewer)

By the author, 2026-10-18. Every finding is fixed in the text; nothing is answered by
disagreement. The revision's own runs (EXECUTED in the drafting scratch folder, `ctx/` and
`art5/`) are on a scratch binary, SHA-256 `31265405…`, built with every change below; the
lxml and regex probes on it are unchanged from the drafting runs.

1. **Fixed** (046 Decision 3; Decision 10; Acceptance 1). libxml2's `CFLAGS` gain
   `-DXML_XML_DEFAULT_CATALOG='"file:///etc/xml/catalog"'` and
   `-DXML_SGML_DEFAULT_CATALOG='"file:///etc/sgml/catalog"'`. The revision also found twelve
   CPython header paths from `assert`'s `__FILE__` in the drafting binary, so lxml's and regex's
   compiles gain `-DNDEBUG` (with `-ffile-prefix-map` as before). EXECUTED: the drafting binary
   holds 15 build paths, the revised one 0, today's 0
   (`../upstream/8-libxml2-input-without-dup/evidence/build-paths.txt`). New v1.1 check
   `test_binaries_hold_no_build_path` (both binaries; `str(paths.REPO)` and the home folder),
   seen failing on the drafting binary. The README says a catalog is read only from a grant at
   `/etc/xml`.
2. **Fixed** (046 Decision 9, rewritten; Decision 10's golden and encodings case; README row).
   The table is now the whole-repertoire run, by row, with each partial encoding and what
   fails, and the three "read as another character" rows explained character by character
   (`evidence/enc_which.py`: 0x5C/0x7E conventions, GB2312 `A1 AA`/`A1 A4`). The golden's set is
   the first row, plus GBK and cp949 for parsing. The v1.3 case asserts each row's
   whole-repertoire outcome (31 G fuel, so once, on the snapshot, `slow`, 40 G budget). The
   README workaround (decode with Python, parse as UTF-8) gives native's results over cp932,
   EUC-JP, GB18030 and Big5 (EXECUTED, `evidence/workaround.txt`). **GB18030 now fails
   loudly:** `recipes/iconv_refusals.c` wraps `iconv_open` (`-Wl,--wrap=iconv_open` on the
   reactor's link, beside its four existing wraps) and refuses GB18030; EXECUTED: the document
   raises `XMLSyntaxError: Unsupported encoding: gb18030` and every other row is unchanged
   (`evidence/encodings_whole_repertoire.txt`). A wasi-libc report is question 82(d).
3. **Fixed, the preferred way** (047 Decision 4, rewritten; Decisions 2, 7, 9; Kind; Design).
   `gen_inittab.py` registers each builtin through a wrapper that calls its init function inside
   `_PyImport_SwapPackageContext`, as `_PyImport_RunModInitFunction` does; the header is gone.
   EXECUTED on a scratch binary wrapping all 61 builtins, regex without the header: every dotted
   builtin keeps its import name, the regex pickle equals native's (117 bytes, same SHA-256),
   numpy and pandas give native's results (`../upstream/9-regex-callback-signatures/evidence/package-context.txt`).
   Decision 4 says what it does to multi-phase modules (nothing), to numpy's f2py template and
   scipy's hand-written single-phase modules (the dotted name, as natively, when `m_name` is the
   last part), and what the check names otherwise. Decision 9 writes the condition on whichever
   of 047 and 037/038 lands second: the check green over all of scipy's builtins, fixed in 037
   by a rename entry or recipe, never an exemption; 038 lands only with it green. A unit check
   covers the generator.
4. **Fixed** (046 Decision 4; facts sheet `notes.md` and `pr.md`). Both forms are named; the
   patch is chosen because the counting header would change two libc calls' meaning inside
   upstream's file invisibly and add bookkeeping upstream never carries, while the patch is as
   small, visible, upstreamable and deletable (043's review's reasoning). `pr.md` now says the
   `owned` flag covers only the uncompressed path, and that with zlib the compression branch
   would hand standard output to `gzdopen` and its failure path closes it.
5. **Fixed** (046 Decision 7; Decision 10's safety case; README row). Decision 7 says that an
   untrusted stylesheet, or a document it loads, can read any granted file, external entities
   included (libxslt's `XSLT_PARSE_OPTIONS`), and write any writable grant; `DENY_ALL` or
   `read_file=False` closes it; `read_xml(stylesheet=…)` uses no access control. The v1.3 case
   holds the entity read without access control and its refusal with `DENY_ALL` and with
   `read_file=False`.
6. **Fixed** (046 Decision 15). `libxml2.txt` gains `list.c`'s notice; `assemble_artifacts.py`
   stops the build if a named file or its notice is missing.
7. **Fixed** (046 Decision 11, 047 Decision 8, Acceptance 5 of both). Every fuel number is now
   from the judge's seeded guest (`tests/harness/guest.py`), EXECUTED twice, identical:
   `-c pass` 242,002,526 today and 242,032,305 on the revised binary (+29,779 for both
   specifications); `import lxml.etree` 558,497,299, `import lxml.html` 643,313,348,
   `import regex` 483,392,295 against 255,861,559 for `-c pass` with the scratch zip. The
   per-member cost of the new zip members is left to the ratchet at build time.
8. **Fixed** (046 Decision 3). `PKG_CONFIG=false` makes libxml2's configure stop ("pkg-config
   not found", EXECUTED), so both configures get an empty `PKG_CONFIG_LIBDIR` and
   `PKG_CONFIG_PATH` instead; EXECUTED: configure passes and `config.h` is unchanged but for
   `XML_SYSCONFDIR`. Once 023 lands, its pinned `pkgconf` replaces the host's.
9. **Fixed** (047 Decision 10). `LICENSES/regex.txt` ends with a line naming the carried patch,
   written by `assemble_artifacts.py` from the patch's path.
10. **Fixed** (047 Decision 7). The check's cost is stated (5.0 G plain and 0.105 G snapshot
    today, by the review; about 5.2 G plain with lxml and regex, EXECUTED); it runs once per
    judge run on each binary with budgets of 20 G plain and 10 G snapshot, a figure above half
    the budget is a finding, and past the budget the plain case is split by top-level package,
    never narrowed.


## Verdict

- **046: Not yet: revise, then confirm.** The design is sound and largely reproduces: the
  `dup()` patch is correct (no leak, no double close, standard output kept, EXECUTED), lxml's
  callbacks are typed right, the safety defaults hold, the constructor list and the imports
  are unchanged, and the growth matches. One High finding blocks the same-bytes criterion (the
  catalog path; a one-flag fix plus a general check). One Medium is text and checks (the
  encodings table, measured over whole repertoires). The Lows can be written in at the same
  time. It is built after question 82 is answered or, failing that, after 038.
- **047: Not yet: revise, then confirm.** The patch is exactly the five callbacks (EXECUTED
  scan and sweep), the module-name header works, and the general check is green today. Finding
  3 must decide how that check meets scipy's single-phase modules; the inittab-wide package
  context is the smaller, general answer and would retire the header.

## One line

The libxml2 and regex patches are correct and complete, but 046 bakes the build folder into
the binary through libxml2's catalog path and overstates its encodings, and 047's name check
needs a general fix before scipy's single-phase modules meet it.

## Confirmation (2026-10-18)

By the reviewer, against the revision in `e8755fe` (both specifications, the two facts-sheet
folders and their new evidence). I re-ran what each finding could be re-run on, on a copy of the
author's revised scratch binary (`set/rev-python.wasm`, SHA-256 `312654058c3f6b72…`, 35,936,637
bytes: the catalog defines, `-DNDEBUG`, the GB18030 wrap, every builtin wrapped in its package
context, regex without the header) with the drafting's scratch zip, in the same scratch folder
as above. Nothing but this section was edited.

### Each disposition against its finding

1. **Holds.** EXECUTED: `strings` finds 0 matches for `/Users/`, the user's name,
   `/private/tmp`, `scratchpad` or `/home/` in the revised binary (15 in the drafting one, as
   `evidence/build-paths.txt` says), and the catalog string is now `file:///etc/xml/catalog`.
   The constructor list equals today's exactly (`ctors.py`: `init`,
   `__wasilibc_initialize_environ_eagerly`, `_mi_process_init`, `register_builtin_extensions`,
   `_GLOBAL__sub_I_unique.cpp`); the imports are today's 43; the stack is still first. The
   `-DNDEBUG` the revision added for lxml's and regex's compiles is what CPython's release
   build and native wheels use, and removed the twelve CPython header paths the drafting
   binary carried through `assert`; good catch. `test_binaries_hold_no_build_path` is in
   Decision 10 and Acceptance 1.
2. **Holds.** EXECUTED (`enc_breadth.py` on the revised binary): every row equals my first run
   except GB18030, which now raises `XMLSyntaxError: Unsupported encoding: gb18030`; the output
   equals the author's `evidence/encodings_whole_repertoire.txt` row for row. Decision 9's table,
   its mapping notes (Shift_JIS `5C`/`7E`, GB2312 `A1 AA`/`A1 A4`), the golden's set, the
   whole-repertoire v1.3 case and the README workaround are written in. The refusal is a recipe
   (a link-time wrap and a small file, no upstream source changed), visible on step 60's link
   line, and the check turns red when wasi-libc's tables change. Question 82(d) holds the
   wasi-libc report.
3. **Holds, the preferred way.** EXECUTED (`ctx_check.py` on the revised binary, then the same
   program natively): all 61 dotted builtins import under their own names; the regex pickle is
   117 bytes with SHA-256 `5dfc121b6135ce13…` in both, and `regex._regex.compile.__module__` is
   `regex._regex`; numpy's `_multiarray_umath` and `numpy.random._pcg64` keep their names, a
   seeded `default_rng(0)` and a pickled-and-restored `default_rng(1)` give native's numbers, a
   pandas groupby, a DataFrame pickle round trip, `pandas._libs.lib` and a Timestamp equal
   native, and `lxml.etree`/`lxml.objectify` keep their names. `regex_sweep.py`: no trap, same
   output as before. Decision 4 states the wrapper, its declaration guard, what it does to
   multi-phase and single-phase modules, and Decision 9 states the no-exemption condition on
   whichever of 047 and 037/038 lands second.
4. **Holds.** Decision 4 and the notes now weigh both forms in the terms I asked; `pr.md` names
   the zlib branch's handling of standard output.
5. **Holds.** EXECUTED on the revised binary: the `document()` entity read without access
   control and its refusal under `DENY_ALL` and `read_file=False`, as before; Decision 7, the
   v1.3 safety case and the README row say it.
6. **Holds.** Decision 15 names `list.c`; `assemble_artifacts.py` stops on a missing notice.
7. **Holds.** EXECUTED through the judge's seeded guest (`tests/harness/guest.py`, twice each,
   identical): `-c pass` 242,002,560 today and 242,032,339 on the revised binary, +29,779 (the
   author's absolute numbers differ by 34 from mine, a work-folder path length; the delta is the
   same).
8. **Holds.** An empty `PKG_CONFIG_LIBDIR` and `PKG_CONFIG_PATH` instead of `PKG_CONFIG=false`
   is the right correction (libxml2's configure requires a `pkg-config` binary); not re-run.
9. **Holds.** Decision 10 of 047 adds the modification line, written from the patch's path.
10. **Holds.** The cost and budgets are stated; my 5.0 G plain and 0.105 G snapshot, and the
    author's 5.2 G with lxml and regex (EXECUTED here: 5,227,541,312 for `ctx_check.py`, which
    imports every dotted builtin plus numpy, pandas and lxml work), sit well inside 20 G.

Also re-run on the revised binary: `fd_probe.py` (no descriptor drift, held files readable,
standard output kept after two `write("-")`), and `safety.py` (every case as in "What holds").

### Conditions

- **046** is built after question 82(a) is answered, or after 038 as decision 48 says; its
  builder measures the snapshot with the new flags (the revision rebuilt only the plain
  reactor) and records the same-bytes result on the second host.
- **047** carries Decision 9's condition: the name check green over every scipy builtin in
  whichever of 047 and 037/038 lands second, never by an exemption. The builder also confirms
  on the snapshot binary that the package-context wrappers leave the pre-imported numpy and
  pandas as they are (the revision ran the plain reactor only).

### Verdict

- **046: confirmed for build**, with the conditions above.
- **047: confirmed for build**, with the conditions above.

One line: every finding is fixed in the text and the fixes reproduce on the revised binary: no
build path, GB18030 refused loudly, all 61 builtins named as natively with numpy, pandas and
regex giving native's results.
