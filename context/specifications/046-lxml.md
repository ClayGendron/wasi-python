# 046 — lxml, with libxml2 and libxslt built in

- **Status:** drafted 2026-10-18. Not yet reviewed. It changes the build recipe and the artifact
  set, so it is reviewed once more before it is built (constitution §5.6). It is build-class: it
  touches `scripts/`, `recipes/`, `downloads/SHA256SUMS` and the release workflow (§5.7). It
  carries one upstream patch (§4.1, to libxml2), so the review reads the patch and its facts
  sheet (spec 020, Decision 8).
- **Owner:** Clay Gendron
- **Kind:** the build recipe (three pins in `downloads/SHA256SUMS` and `scripts/00_download.sh`;
  two new steps, `scripts/steps/36_xml_libs.sh` and `scripts/steps/54_lxml.sh`;
  `scripts/build.sh`, `scripts/steps/60_link.sh`, `scripts/steps/70_zip.sh`,
  `scripts/assemble_artifacts.py`), one recipe file (the `lxml.isoschematron` stand-in), one
  carried patch to libxml2 with its upstream facts sheet, the reactor's `-V` sentence, judge
  additions and changes (`tests/`: one golden job, the oracle's pin, guest checks, the judge's
  package, licence and source-tree lists), the release workflow's tree count, `README.md`,
  `CHANGELOG.md`, `LICENSES/`.
- **Depends on:** landed specifications only: 033 (the zip keeps `METADATA`;
  `make_stdlib_zip.py --metadata`; `tree_members`), 020 (carried patches: the applier, the tree
  check, the rules), 012 (the same bytes from any host), 007 (step 35's pattern for C libraries
  built under an empty environment), 004 and 009 (the licence notices). It needs nothing from
  scipy (037, 038), matplotlib (023, 043) or tier A (039); Decision 13 says how it meets each of
  them in either order. Where a specification it meets lands in another shape than its text,
  this specification uses what landed and says so in its landing notes.
- **Research it stands on:** `../research/2026-10-17-what-else-the-default-profile-carries.md`
  (tier B; the native-extensions table: lxml "moderate", `dup()` in libxml2, a static wasip1
  build in HubSpot's boomslang; Pyodide's 4.71 MB of `.so`); the owner's decisions 43 (the
  licences, §4.12) and 48 (lxml with python-docx and python-pptx in 0.1.0, after scipy) in
  `../decisions.md`; the prior art `../prior_art/boomslang/cpython/lxml-wasi/` (Apache-2.0,
  studied, not copied: its configure lines, its choice of the sdist's generated C, its own
  `dup()` change) and `../prior_art/pyodide-recipes/packages/{libxml,libxslt,lxml}/`. **The
  drafting runs** (EXECUTED 2026-10-17 and 2026-10-18 in the session's scratch folder, outside
  the repository; nothing in the repository changed but this file, spec 047, question 82, the
  prior-art index and the two upstream folders `../upstream/8-libxml2-input-without-dup/` and
  `../upstream/9-regex-callback-signatures/`):
  - the pins: PyPI's JSON and GNOME's `.sha256sum` files read, each file downloaded and its
    SHA-256 recomputed (all equal);
  - libxml2 2.15.4 and libxslt 1.1.45 configured and built static for `wasm32-wasip1` with the
    toolchain under `build/tools/` (wasi-sdk 33's clang) under `env -i`, first without the patch
    (two compile errors on `dup`), then with it (no warning in either library);
  - lxml 6.1.3's `etree.c` and `objectify.c` compiled against CPython 3.15.0's headers and the
    line's `pyconfig.h`; with the two libraries and regex (spec 047) linked into a scratch copy
    of today's plain reactor by step 60's own reactor link command, run from the main tree's
    cross-build directory with only its output and map redirected to the scratch folder;
  - a probe program (`../upstream/8-libxml2-input-without-dup/evidence/lxml_probe.py`) run
    natively (the line's CPython 3.15.0 in `build/oracle/venv` with lxml's macOS universal2
    wheel) and in that scratch guest through `wasi_python.run` with a read-only data grant and
    a writable output grant; an encodings probe (`evidence/encodings.py`); python-docx 1.2.0
    reading and writing a `.docx` in the guest; the constructor list read from both binaries'
    name sections; plain-reactor fuel for `-c pass` and for imports, with the added modules
    compiled to bytecode by the line's host Python.

## The problem

lxml is the XML and HTML library agents reach for: XPath, XSLT, schema validation, fast HTML
parsing. pandas uses it for `read_html`'s default flavor and for `read_xml` and `to_xml` (whose
default parser is lxml), and python-docx and python-pptx are built on it. Today the guest has
none of it: `import lxml` fails, and `pd.read_html` without `flavor="bs4"` raises `ImportError`
(spec 039, Decision 9).

lxml is a Cython package over two C libraries, libxml2 and libxslt. No release of either builds
for `wasm32-wasip1` unchanged: libxml2's file input duplicates descriptors with `dup()`, which
WASI preview 1 does not have, so `xmlIO.c` does not compile. Once that is solved, everything else
the drafting runs tried works, with differences that this specification states, checks or leaves
out: the guest's libxml2 is newer than the one in lxml's own wheels, its character conversion is
wasi-libc's, it has no zlib, and one lxml module reads its data files by path.

## Decisions

1. **What goes in, and what does not.**
   - **In:** libxml2 (with its HTML parser, XPath, XPointer, XInclude, C14N, catalogs, DTD,
     XML Schema, RELAX NG and Schematron validation, the reader, writer and push interfaces),
     libxslt and libexslt, and lxml's two C extension modules, `lxml.etree` and
     `lxml.objectify`, as builtins; lxml's Python package (`lxml.html`, `lxml.builder`,
     `lxml.sax`, `ElementInclude`, `lxml.html.diff`, the doctest helpers).
   - **lxml's five Cython-compiled Python modules are not compiled.** lxml's `setup.py` also
     compiles `lxml.builder`, `lxml._elementpath`, `lxml.html.diff`, `lxml.html._difflib` and
     `lxml.sax` with Cython for speed (`setupinfo.py`, `COMPILED_MODULES`, READ); each is a
     plain `.py` file in the sdist that lxml imports when the compiled one is absent, as it does
     on PyPy. They go into the zip as bytecode. Their compiled forms would add five builtins
     whose init names (`PyInit_builder`, `PyInit_diff`, `PyInit_sax`) are generic enough to
     clash with other packages', for speed no judge job needs. The drafting runs used the `.py`
     forms and matched native output.
   - **Out: `lxml.isoschematron`** (Decision 8): a stand-in raises `ImportError`.
   - **Out: python-docx and python-pptx** (Decision 12), to a follow-up specification.
   - **Not shipped because lxml does not require them:** `cssselect`, `lxml_html_clean`. As
     natively without them, `lxml.cssselect` and `lxml.html.clean` raise lxml's own
     `ImportError` messages.

2. **The pins.** Each a `get` line in `scripts/00_download.sh`'s host-neutral sources block and a
   line in `downloads/SHA256SUMS` (EXECUTED: each downloaded and its SHA-256 recomputed, equal to
   the published value):
   - `libxml2-2.15.4.tar.xz`, `https://download.gnome.org/sources/libxml2/2.15/libxml2-2.15.4.tar.xz`,
     `98087fd181d9070724f3fbc65c7377db03038eb92bd882374daff44940138821` (GNOME's
     `libxml2-2.15.4.sha256sum`);
   - `libxslt-1.1.45.tar.xz`, `https://download.gnome.org/sources/libxslt/1.1/libxslt-1.1.45.tar.xz`,
     `9acfe68419c4d06a45c550321b3212762d92f41465062ca4ea19e632ee5d216e` (GNOME's
     `libxslt-1.1.45.sha256sum`);
   - `lxml-6.1.3.tar.gz`,
     `https://files.pythonhosted.org/packages/23/ad/28ecd7cb894d172f3c9c80a075eeeb2017ac62e3632cee05a5f9493547eb/lxml-6.1.3.tar.gz`,
     `45222d94ddd511536f3b2f7d9deae3b2339b4ce0f075f1ca25703b07cad9dd21` (PyPI's digest).

   **Why these versions.** lxml 6.1.3 is the current release (2026-09-02; 7.0.0b1 is a beta).
   libxml2 2.15.4 (2026-09-01) and libxslt 1.1.45 are the newest releases of each. lxml's own
   Linux and macOS wheels bundle older ones, libxml2 2.14.6 and libxslt 1.1.43 with a backport
   patch of lxml's (`pyproject.toml`'s cibuildwheel environment, `libxslt-1.1.43-backport1.patch`,
   READ). Matching them would make the native oracle's library the guest's, but 2.14 ended at
   2.14.6 in September 2025, and 2.15.4's own news lists six security fixes since (out-of-bounds
   and overflow checks in `xmlregexp`, `dict.c`, `uri.c`, `valid.c`, `xpointer`, `xmlIO`). libxslt
   1.1.44/1.1.45 is upstream's release of the fixes lxml backports (CVE-2025-7424,
   CVE-2025-11731), so it needs no patch. A pinned component with known security fixes waiting is
   a reason to release (§5.5), not a pin to choose. The oracle therefore runs other library
   versions; Decision 10 says how the goldens live with that.

3. **Step 36: libxml2 and libxslt** (`scripts/steps/36_xml_libs.sh`, new, after step 35, needing
   step 10), on step 35's pattern: every tool under `env -i` with only `PATH` and `LC_ALL`, the
   toolchain's clang over the host-neutral sysroot, out-of-tree (VPATH) builds, so each source
   tree stays its tarball plus its recorded patches.
   - It unpacks `libxml2-2.15.4` and `libxslt-1.1.45` from `pinned …` into `build/`, runs
     `patch_tree` on each (libxml2 has one patch, Decision 4; libxslt none), and builds in
     `build/libxml2-build` and `build/libxslt-build`, installing into `build/xml-libs/`.
   - **libxml2's configure line:** `CC="$SDK/bin/clang --target=wasm32-wasip1"`, the SDK's
     `llvm-ar` and `llvm-ranlib`, `CFLAGS="-O2 -DLIBXML_STATIC
     -ffile-prefix-map=$HERE=/wasi-python-build"`, `--host=wasm32-unknown-wasip1
     --prefix=$B/xml-libs --disable-shared --enable-static --without-python --without-threads
     --without-modules --without-zlib --with-schematron`. Then `make libxml2.la` and `make
     install-libLTLIBRARIES install-data` (the library and its headers; no `xmllint`, no
     documentation). Every other option keeps upstream's default, which is also what lxml's
     wheels use (`buildlibxml.py`, READ). Each choice:
     - `--without-threads`: wasm32-wasip1 has no threads. libxml2 keeps its globals in one
       static set, which is what one guest thread needs.
     - `--without-modules`: no `dlopen` in a static guest.
     - `--without-zlib`: lxml then writes compressed output through Python's `gzip` itself
       (`serializer.pxi`, `HAS_ZLIB_COMPRESSION`, READ; EXECUTED in the guest: `write(…,
       compression=6)` read back by `gzip` equals native). What is lost is
       `XMLParser(decompress=True)` on a compressed file, off by default since lxml 6.0; libxml2
       2.15's news names zlib file I/O as a removal candidate. It also keeps the decompression
       branch, which calls `dup` a third time, out of the build.
     - `--with-schematron`: 2.15 turned Schematron off by default; lxml's wheels (2.14.6) have it
       on, so `etree.Schematron` works as it does natively. lxml marks it deprecated (a
       `DeprecationWarning`, natively too).
     - **iconv:** left at its default, which finds wasi-libc's iconv (musl's; configure:
       "checking for libiconv... none required"). wasi-libc's licence is already shipped. It is
       not GNU libiconv, which lxml's wheels bundle and which is LGPL, not approved (§4.12).
       Decision 9 says what it converts.
     - `-DLIBXML_STATIC`: libxml2 then compiles out its one destructor, `xmlDestructor`
       (`threads.c:504`, guarded by `!defined(LIBXML_STATIC)`), so the build adds no entry to
       what `__wasm_call_ctors` runs (EXECUTED: without the flag the scratch binary's
       constructor list gained `.Lregister_call_dtors`; with it, nothing but the scratch
       inittab's own entry). This matters for 023's constructor check and for the snapshot.
     - HTTP: libxml2 2.15 removed its HTTP client (its news); nothing in the guest can open a
       socket anyway.
   - **libxslt's configure line:** the same `CC`, tools and `CFLAGS` (with `-DLIBXSLT_STATIC
     -DLIBEXSLT_STATIC` in place of `-DLIBXML_STATIC`), `LIBXML_CFLAGS=-I$B/xml-libs/include/libxml2`
     and `LIBXML_LIBS="-L$B/xml-libs/lib -lxml2"` on the configure command line,
     `--host=wasm32-unknown-wasip1 --prefix=$B/xml-libs --disable-shared --enable-static
     --without-python --without-crypto`. Then `make -C libxslt`, `make -C libexslt` and their
     `install`. `--without-crypto` is what lxml's wheels use (EXSLT's crypto functions need
     libgcrypt). The profiler stays on: lxml's `etree.c` calls `xsltGetProfileInformation`
     (the first drafting build turned it off and `etree.c` did not compile). Plugins are off by
     default (no `dlopen`).
   - The step prints each archive's size and SHA-256 into its log, and stops with one line if
     `libxml2.a`, `libxslt.a` or `libexslt.a` is missing. In the drafting build:
     `libxml2.a` 1,554,346 bytes, `libxslt.a` 281,986, `libexslt.a` 83,844.
   - **Host facts.** Both configures run the build host's `sh`, `sed`, `grep` and `awk`, as xz's
     does in step 35 (spec 007's A2); the same-bytes gate is what shows they leave the archives
     alone (Decision 11). Both tarballs are `.tar.xz`; every build host already unpacks
     CPython's `.tar.xz` in step 20.

4. **One carried patch to libxml2: files without `dup()` on WASI** (§4.1, spec 020's
   mechanism). `recipes/patches/libxml2-2.15.4/0001-xmlio-without-dup-on-wasi.patch`, 40 lines
   added and 2 removed in `xmlIO.c`, all under `#ifdef __wasi__` with today's code in the `#else`
   branches: `xmlInputFromFd` reads from its caller's descriptor and closes the buffer with
   libxml2's own `xmlFdFree` (frees, does not close); the default file opener hands the
   descriptor it opened to the buffer, which then closes it; output to `"-"` writes to standard
   output without closing it. Its facts sheet is drafted at
   `../upstream/8-libxml2-input-without-dup/` (`pr.md`, `fix.patch`, `notes.md`, `evidence/`) and
   moves at build time to `../upstream/patches/libxml2-2.15.4/0001-xmlio-without-dup-on-wasi.md`,
   with `fix.patch` copied byte for byte into `recipes/patches/`.
   - **Why a patch and not a recipe** (§4.1 prefers a recipe): a stand-in `dup` cannot be
     honest, because WASI preview 1 cannot copy a descriptor. Returning an error breaks every
     file read by name; returning the same number lets the opener close it at once. The facts
     sheet's notes say this at length.
   - **Seen failing first** (EXECUTED): without the patch, `make libxml2.la` stops on `dup` at
     `xmlIO.c:1230` and `:1264`. With it: no warning, and in the guest a parse by path (fifty in
     a row), `iterparse` of a path, XInclude, a DTD by path, XSLT `document()`, a missing file's
     `OSError`, a write to a path and a write to `-` all equal native.
   - The facts sheet follows question 80's recommendation; libxml2's tree names no rule on
     AI-written changes, and the owner decides whether and how to send it.

5. **Step 54: lxml's two modules** (`scripts/steps/54_lxml.sh`, new, after step 50, needing steps
   10, 20 and 36).
   - It unpacks `lxml-6.1.3` from `pinned …` into `build/`, runs `patch_tree` (no patches), and
     **compiles the sdist's generated C**, `src/lxml/etree.c` and `src/lxml/objectify.c`, as
     step 35 compiles SQLite's amalgamation. lxml ships them so that a build needs no Cython
     (`setupinfo.py` uses them when Cython is absent, READ); boomslang does the same. The step
     stops unless each file's first line is `/* Generated by Cython 3.2.9 */`, so a later sdist
     with other generated code is a visible change. **Why not regenerate them:** lxml requires
     `Cython>=3.2.9,<3.3` (`pyproject.toml`), and the line's Cython is 3.3.0; regenerating would
     pin a second Cython for three hosts to rebuild what the sdist already holds. Two Cython
     versions' code in one binary is safe: each module keeps its own utility code (spec 037,
     Decision 2).
   - **The compile:** through `scripts/wasi-cc` (which drops `-fPIC`), `-O2`
     `-ffile-prefix-map=$HERE=/wasi-python-build`, lxml's own macros for a static build
     (`setupinfo.define_macros()` with `OPTION_BUILD_LIBXML2XSLT`: `-DLIBXML_STATIC
     -DLIBXSLT_STATIC -DLIBEXSLT_STATIC -DCYTHON_CLINE_IN_TRACEBACK=0`), the line's WASI
     emulation defines (`-D_WASI_EMULATED_SIGNAL -D_WASI_EMULATED_PROCESS_CLOCKS
     -D_WASI_EMULATED_GETPID`, as the cross files pass), and include folders `src/lxml`,
     `src/lxml/includes`, CPython's `Include`, the cross-build folder's `pyconfig.h`, and
     `build/xml-libs/include/libxml2` and `build/xml-libs/include`. The drafting compile gave
     64 warnings in `etree.c`, all deprecation warnings for libxml2 fields lxml still reads
     and three `-Wswitch` notes, and none in `objectify.c`; the step keeps them in its log.
   - **The archives, in the shape step 60 already reads.** The step then calls `scripts/wasi-cc
     -shared -o build/lxml-build/lxml/etree.cpython-315-wasm32-wasi.so etree.o
     $B/xml-libs/lib/libexslt.a $B/xml-libs/lib/libxslt.a $B/xml-libs/lib/libxml2.a` (and the
     same for `objectify` with no libraries): the wrapper writes each `.so` as a static archive
     and its `.so.deps`, exactly as for numpy and pandas. So step 60 and `gen_inittab.py` need
     no new mechanism: `lxml.etree` and `lxml.objectify` are found by path under
     `build/lxml-build`, with init functions `PyInit_etree` and `PyInit_objectify` (EXECUTED:
     present in the objects; no clash with numpy's, pandas', 023's or 037's names, READ from
     their module lists).
   - **The package:** `build/lxml-install/lxml/` is a copy of `src/lxml/` without
     `isoschematron/` (Decision 8). Step 70's suffix rules then leave out the `.c`, `.h`, `.pyx`,
     `.pxd` and `.pxi` files and `tests/`; 24 modules go in, among them `includes/__init__.py`,
     as in lxml's wheels.

6. **Step 60 and step 70.**
   - Step 60's package loop and its `gen_inittab.py` call gain `lxml:"$B/lxml-build"` and
     `lxml=$B/lxml-build`; its archive check gains the three `build/xml-libs/lib` archives, with
     one line naming a missing one ("run step 36"). Its `clashes()` detector covers the new link
     (the drafting link gave no `signature mismatch` and no `duplicate symbol`). `python.wasm`'s
     imports stay WASI preview 1 and the door (EXECUTED on the scratch binary: the same 43
     imports as today's).
   - Step 70 gains `--tree "$B/lxml-install"`, `--metadata "$B/lxml-6.1.3/PKG-INFO"` (spec 033)
     and `--file "$HERE/recipes/lxml_isoschematron_stand_in.py=lxml/isoschematron.py"`.
   - `scripts/build.sh`'s `ALL` gains `36_xml_libs` after `35_stdlib_libs` and `54_lxml` after
     `50_pandas`.

7. **Safety: what lxml does by default here, and what the sandbox adds.** lxml 6.1's defaults
   are already the safe ones (`parser.pxi`, READ): external entities are not resolved
   (`resolve_entities='internal'`), `no_network=True`, DTDs are not loaded, `huge_tree=False`,
   and libxml2 caps entity amplification. None is changed. What the guest adds: a file can be
   read only inside a grant, and no network exists at all. EXECUTED in the guest: the default
   parser refuses an external entity naming a granted file (`XMLSyntaxError`, as natively);
   `resolve_entities=True` reads it, as natively, but only because it was granted; an entity
   on `http://127.0.0.1:9/` with `no_network=False` gives an empty element, and one on a path
   outside every grant gives an empty element too; a billion-laughs document raises "Maximum
   entity amplification factor exceeded".
   **XSLT reads and writes files by default:** lxml's `XSLT()` without an `access_control`
   allows `document()` and `exsl:document` (READ: `xslt.pxi`). In the guest that reaches only
   granted folders, and writes only writable ones. The README says so and names
   `etree.XSLTAccessControl.DENY_ALL` for untrusted stylesheets; libxml2's own README advises
   against untrusted input, which the sandbox contains but does not make correct. EXECUTED: an
   `exsl:document` aimed at a read-only grant raises `XSLTApplyError` and leaves no file. A check
   (Decision 10) holds it.

8. **`lxml.isoschematron` is left out, with a stand-in.** It reads its XSL and RELAX NG
   resources by file path at import (`isoschematron/__init__.py:41-68`, READ), which fails from
   the zip (EXECUTED: `OSError: Error reading file '/usr/local/lib/python315.zip/lxml/isoschematron/resources/xsl/XSD2Schtrn.xsl'`).
   And its resources carry terms §4.12 does not name: the ISO/IEC schema's own permission
   notice, Rick Jelliffe's zlib-style notice on the skeleton XSLs, and two files lxml's
   `LICENSES.txt` calls "unlicensed and copyright the respective authors". So neither the
   folder nor its resources go into the zip. `recipes/lxml_isoschematron_stand_in.py` is packed
   as `lxml/isoschematron.py` and raises `ImportError("lxml.isoschematron is not in this build:
   it reads its stylesheets by file path, and their licences are not approved; use
   lxml.etree.Schematron")`. `etree.Schematron` (libxml2's) works. Bringing it in needs the
   owner's approval of those terms and a carried patch to read the resources from the zip
   (question 82).

9. **Character encodings are wasi-libc's.** EXECUTED in the guest, beside native
   (`../upstream/8-libxml2-input-without-dup/evidence/encodings.txt`): parsing a document that
   declares windows-1252, cp1251, ISO-8859-2 and -15, KOI8-R, Shift_JIS, cp932, EUC-JP,
   ISO-2022-JP, GBK, GB18030, GB2312, Big5, EUC-KR, cp949, cp950, TIS-620 or UTF-16 works as
   natively; and so does writing in each of these except the Chinese and Korean ones. **What
   differs:** writing in GBK, GB18030, GB2312, Big5, EUC-KR, cp949 or cp950 raises
   `LookupError: unknown encoding` (wasi-libc's iconv decodes them but does not encode them);
   windows-874 and HZ neither parse nor write; UTF-32 output is not the bytes Python's
   `utf-32` codec reads back; and cp437, which native lxml rejects, works. A program that needs
   one of those outputs can serialize to a `str` (`encoding="unicode"`) and encode with
   Python's codecs, which are complete. The README lists this; a check holds it (Decision 10).
   Without iconv libxml2 would know only UTF-8, UTF-16, ASCII and ISO-8859-x, so a windows-1252
   or Shift_JIS page could not be read at all; iconv's tables cost part of the growth in
   Decision 11 (INFERRED from the link map: `iconv.c.obj` is new in it).

10. **The checks**, each seen failing first.
    - **The oracle.** `tests/jobs/oracle/pyproject.toml` gains `lxml==6.1.3`, and `uv.lock`
      records its wheels (on macOS arm64 the `macosx_10_15_universal2` wheel, SHA-256
      `6ea2f13dce778ca072ccee598bca46a092ce192e8fd907b6c1f0e52c800529a0`; on Linux aarch64
      `2e01125896585139453cab8cb235893644d8815d7509520da95ae3ee8d1c1f79`; on Linux x86_64
      `73fc05988ed20809450474ba760a87c8ad4e455fc09783c02195e56ec634b41a`, READ from PyPI). Those
      wheels carry libxml2 2.14.6 and libxslt 1.1.43; the existing goldens must still reproduce
      (`regen.py --check`).
    - **A golden job, `lxml_xml` (v1.3),** `tests/jobs/lxml_xml.py` in `JOBS` (not `xml.py`: the
      script's folder is first on `sys.path`, and a file named `xml.py` would hide the stdlib's
      `xml` package), run on the plain reactor
      with a data folder (the job writes `doc.xml`, `d.dtd` and `inc.xml` there first) and an
      output folder. Its first line is `versions python=… lxml=6.1.3 pandas=…` (no library
      versions: the oracle's differ). It prints: XPath (counts, namespaces, string functions,
      EXSLT regular expressions, sets and math); XSLT with the `xml` output method (sorting,
      parameters, EXSLT strings); `objectify`; C14N; `lxml.html` (links, `text_content`, a
      document with a `<meta charset>` head serialized with `lxml.html.tostring`); `iterparse`;
      a parse by path, XInclude and a DTD validation of the files in the data folder; XML
      Schema and RELAX NG validity; a document written by path and a gzip-compressed one read
      back with `gzip`; encodings in Decision 9's agreeing set, both ways; then pandas:
      `read_html` with no `flavor`, `read_xml` with an XPath and with a stylesheet, and
      `to_xml(parser="lxml")` written into the output folder.
      **What it must not print**, because libxml2 2.14 and 2.15 differ there (EXECUTED: the
      drafting runs' only differences): XSLT output with `method="html"` (2.15 writes `<meta
      charset="UTF-8">`, 2.14 the `http-equiv` form), error messages and their columns, and
      any version. If another line differs between the oracle and the guest when the builder
      runs it, the job's input changes and the landing notes say why; the job never prints a
      library's behaviour that the two versions do not share.
      Seen failing first on the current set: `ModuleNotFoundError: No module named 'lxml'`.
    - **v1.1, `test_lxml_is_builtin_at_manifest_versions`** (both binaries): `lxml.etree` and
      `lxml.objectify` are in `sys.builtin_module_names`; `lxml.__version__`,
      `etree.LIBXML_VERSION` and `etree.LIBXSLT_VERSION` equal `MANIFEST`'s lxml, libxml2 and
      libxslt lines; `etree.LIBXML_FEATURES` has `iconv` and `schematron` and not `zlib` or
      `thread`. Seen failing first: no lxml.
    - **v1.3, `tests/checks/test_v1_3_lxml.py`** (both binaries, nothing writable unless the
      case grants it):
      - files by path in a read-only grant: parse, `iterparse`, a DTD, XInclude, XSLT
        `document()` give the expected values; a missing file raises `OSError`;
      - writing by path into a read-only grant raises `OSError`, and into a writable grant
        writes the bytes; `ElementTree.write("-")` reaches the program's standard output;
      - safety (Decision 7): the default parser refuses an external entity on a granted file;
        `resolve_entities=True` on a path outside every grant gives an empty element (the guest
        has no such path); `no_network=False` with an `http:` entity gives an empty element;
        billion laughs raises; a stylesheet's `exsl:document` aimed at a read-only grant raises
        `XSLTApplyError` ("unable to save") and writes nothing, and with
        `XSLTAccessControl.DENY_ALL` raises "write rights … denied" (all four EXECUTED in the
        scratch guest);
      - encodings (Decision 9): the agreeing set round-trips, and the seven Chinese and Korean
        encodings parse but raise `LookupError` on output (the documented difference);
      - `XMLParser(decompress=True)` on a gzip file raises `XMLSyntaxError` (no zlib in
        libxml2; documented);
      - `import lxml.isoschematron` raises `ImportError` naming "licences"; `etree.Schematron`
        validates;
      - `pd.read_html` with no `flavor` returns the table (lxml is pandas' first flavor).
      Seen failing first: each fails on the current set (no lxml); the file-by-path cases are
      the patch's behaviour, seen as a build failure without it (Decision 4).
    - **Judge changes** (under `--accept-judge`): `tests/harness/paths.py`'s
      `LICENCE_COMPONENTS` gains `libxml2`, `libxslt` and `lxml`, and `PACKAGES` the same three;
      `pins.SOURCE_PATTERNS` and `needs.SOURCE_COMPONENTS` gain the three trees, and the patched-
      tree check covers libxml2's patch; the release workflow's zero-patch count rises by three
      from main's count when this lands; `jobs.JOBS` gains `lxml_xml`; `scripts/gen_inittab.py`'s
      clash check runs on the new names unchanged. If spec 023 has landed, its constructor list
      does not change (Decision 3, `-DLIBXML_STATIC`); if it has not, the builder reads the list
      from the name section once and records that it gained nothing.
    - **The `-V` sentence** (`recipes/reactor_bootstrap.py`) names nothing new as missing; the
      README states the absences (Decisions 1, 8, 9).

11. **What the set costs, so growth can be told from regression** (EXECUTED on the scratch
    build unless marked; the build measures each again and records it).
    - `python.wasm`: +3,633,511 bytes for lxml, libxml2, libxslt and wasi-libc's iconv
      (31,760,992 today; 32,476,722 with regex alone; 36,110,233 with both), +11.4%. Pyodide's
      Emscripten `.so` files total 4.71 MB, times the memo's 0.92 ratio about 4.3 MB (INFERRED).
      A growth outside 3.2 to 4.2 MB is a finding for the build review, not a reason to accept.
    - The snapshot: about the same bytes (lxml is not pre-imported; Decision 12).
    - The zip: +26 members (24 lxml modules, the stand-in, `METADATA`), about 150 KB deflated
      (146,120 bytes of compressed data for the 23 modules the scratch zip held).
    - Plain `-c pass`: +447,981 fuel (+0.19%) for lxml and regex's three new builtins together
      (241,937,030 to 242,385,011 on today's zip); plus about 26 members at the per-member cost
      (about 26,700 fuel each after spec 035, 77,912 before), **measured, not estimated,** by
      the build.
    - `import lxml.etree` on the plain reactor: 558,881,952 fuel against 256,076,439 for
      `-c pass` with the same scratch zip (about +303 M); `import lxml.html`: 643,551,902. The
      build records both on both binaries.
    - Snapshot `-c pass`: within 1%; every existing golden: no change beyond the plain-start
      growth.

12. **python-docx and python-pptx: a follow-up specification, not this one.** Both are pure
    Python on lxml, MIT, approved (§4.12, decision 48), but neither works from the zip as
    released, and they need more than lxml (EXECUTED and READ while drafting):
    - python-docx 1.2.0 (needs `typing_extensions`, from spec 039): in the guest it reads a
      `.docx` from a granted folder, adds a paragraph, saves to `BytesIO` and reads it back,
      all as natively. But `docx.Document()` with no argument, the usual way to start a
      document, raises `PackageNotFoundError`: it opens `docx/templates/default.docx` by path
      (`docx/api.py:36`), and five parts read their XML templates the same way.
    - python-pptx 1.0.2 imports Pillow at import (`pptx/parts/image.py:10`; Pillow comes with
      spec 023) and `xlsxwriter` for charts (spec 039), and `Presentation()` opens
      `pptx/templates/default.pptx` by path, as do two other places.
    So the follow-up carries a patch to each (read the templates as package resources, as spec
    041 does for pandas and networkx), with facts sheets, and depends on 046, 023 and 039. It is
    drafted after this specification's review; its number is given when it is written. The
    owner's decision 48 is met when it lands.

13. **The snapshot does not pre-import lxml**, and step 80 is unchanged. Whether it should is the
    owner's, with question 34's matplotlib numbers and question 61's scipy numbers; the build
    records lxml's import fuel on both binaries for it.

14. **Ordering and shared files.** It is build-class, so it overlaps no other build-class
    change (§5.7).
    - **It needs nothing from scipy.** Decision 48 places tier B after scipy; this specification
      can build before spec 037 if the owner says so (question 82). Until the owner answers, it
      queues after 038, as decision 48 says. Spec 047 (regex) shares the oracle and the scratch
      evidence, not a file it must wait for; either may build first.
    - **Spec 039** (tier A): its `markup` golden prints pandas' default-flavor `ImportError`
      line, which lxml removes, and its oracle gains no lxml. Whichever of 039 and 046 lands
      second regenerates `markup.expected` with lxml in the oracle (039's Scope says the same)
      and updates the README's `read_html` line. With 039 in, `lxml.html.soupparser` (bs4) and
      `lxml.html.html5parser` (html5lib) also work; nothing here depends on it.
    - **Spec 023** (matplotlib M1): its constructor check; Decision 3's flag keeps the list as
      it is in either order.
    - Files shared with others: step 60 and `gen_inittab.py` (023, 035, 037), step 70 and
      `make_stdlib_zip.py` (023, 033, 037, 039, 041), `00_download.sh` and `SHA256SUMS` (all
      build-class work), the oracle's `pyproject.toml` and `uv.lock` (037, 039, 047). Each is
      rebased onto main as it is when the builder starts; step numbers 36 and 54 are new.
    - **Spec 040** (x86_64 in the same-bytes gate): if it has landed, the x86_64 rebuild must
      give the same `SHA256SUMS` too (Acceptance, criterion 3).

15. **Licences** (§4.12; approved by decision 43: libxml2 and libxslt MIT, lxml BSD-3-Clause).
    `LICENSES/` gains, each read from its pinned tarball by `scripts/assemble_artifacts.py`:
    - `libxml2.txt`: its `Copyright` file, then the notices at the head of `dict.c` (an
      ISC-style grant to Daniel Veillard's copyright) and `timsort.h` (MIT), which `Copyright`
      names as exceptions;
    - `libxslt.txt`: its `Copyright` file (libxslt and libexslt);
    - `lxml.txt`: `LICENSE.txt`, `LICENSES.txt`, `doc/licenses/BSD.txt` and
      `doc/licenses/elementtree.txt`. `LICENSES.txt` describes lxml's wheels, which bundle GNU
      libiconv and zlib; this build links neither (wasi-libc's iconv, no zlib), and the README
      says so. lxml also carries code derived from ElementTree (`_elementpath.py`, under the
      ElementTree terms in `elementtree.txt`, the terms CPython's own `xml.etree` carries) and a
      fork of CPython's `difflib` (PSF), both inside the CPython family already shipped;
      question 82 records this reading for the owner.
    `MANIFEST` gains package lines `libxml2 2.15.4`, `libxslt 1.1.45` and `lxml 6.1.3`, the three
    pins, the stand-in recipe and the patch by hash.

## Intent

An agent's code parses, queries, transforms and validates XML and HTML with lxml inside the same
sealed Python, and pandas reads HTML tables and XML with its default parser, getting native
lxml's answers, with libxml2's one WASI gap carried as a recorded, temporary patch.

## Design

| file | change |
|---|---|
| `downloads/SHA256SUMS`, `scripts/00_download.sh` | the libxml2, libxslt and lxml pins (Decision 2) |
| `scripts/steps/36_xml_libs.sh` | new: libxml2 and libxslt static archives into `build/xml-libs/` (Decision 3) |
| `recipes/patches/libxml2-2.15.4/0001-xmlio-without-dup-on-wasi.patch` | new (Decision 4) |
| `context/upstream/patches/libxml2-2.15.4/0001-xmlio-without-dup-on-wasi.md`, `context/upstream/README.md` | the facts sheet, moved from `../upstream/8-libxml2-input-without-dup/pr.md`; its row |
| `scripts/steps/54_lxml.sh` | new: `etree` and `objectify` archives into `build/lxml-build/`, the package into `build/lxml-install/` (Decision 5) |
| `recipes/lxml_isoschematron_stand_in.py` | new (Decision 8) |
| `scripts/build.sh`, `scripts/steps/60_link.sh`, `scripts/steps/70_zip.sh` | the two steps in `ALL`; lxml in the link and the inittab; the tree, metadata and stand-in in the zip (Decision 6) |
| `scripts/assemble_artifacts.py`, `LICENSES/` | three packages, three notices (Decision 15) |
| `tests/jobs/lxml_xml.py`, `lxml_xml.expected`, `tests/jobs/oracle/pyproject.toml`, `uv.lock`, `tests/harness/jobs.py` | the golden job and the oracle's lxml (Decision 10) |
| `tests/checks/test_v1_3_lxml.py`, `tests/checks/test_v1_1_artifact_set.py` | the behaviour checks; the builtin-at-manifest-versions check |
| `tests/harness/paths.py`, `pins.py`, `needs.py`, `tests/unit/test_artifact_rules.py` | the three components in each list and the synthetic set |
| `.github/workflows/release.yml` | the zero-patch tree count, three more |
| `README.md` | lxml in the profile; Decision 7's XSLT note and `DENY_ALL`; Decision 9's encodings; no zlib in libxml2 (`decompress=True`); `lxml.isoschematron` left out; wasi-libc's iconv, not GNU libiconv |
| `CHANGELOG.md` | lxml, libxml2 and libxslt; the libxml2 patch by path; `pd.read_html`'s default flavor works |

## Scope

In: Decisions 1 to 15. Out:

- **python-docx and python-pptx** (Decision 12), the follow-up specification.
- **`lxml.isoschematron`** (Decision 8), until the owner approves its resources' terms.
- **lxml's Cython-compiled `.py` modules** (Decision 1); **regenerating lxml's C** with Cython.
- **zlib in libxml2**, and with it `decompress=True`; **GNU libiconv** or ICU.
- **cssselect** and **lxml_html_clean**: not in the default profile; a later profile decision.
- **Pre-importing lxml in the snapshot** (Decision 13).
- **lxml's own test suite under the runtime** (roadmap milestone 6, hardening).

## Acceptance criteria

1. **The checks exist and were seen failing first:** the golden job, the v1.1 check and every
   v1.3 case on the set the builder starts from (no lxml); the patched-tree check on a tree
   without the patch; step 36 failing to compile `xmlIO.c` with the patch removed, as Decision
   4 records.
2. **The build.** From an empty `build/` in a clean clone, `scripts/build.sh` applies libxml2's
   patch with no offset, builds steps 36 and 54, links `lxml.etree` and `lxml.objectify` as
   builtins with no clash, and makes a set whose binaries pass the checks and match the golden.
   `MANIFEST` names every new pin, recipe and the patch. Steps 36 to 90 run twice give the same
   `SHA256SUMS`.
3. **The same bytes everywhere** (spec 012): the arm64 Linux rebuild gives macOS's `SHA256SUMS`;
   once spec 040 has landed, so does x86_64 Linux. A difference that two attempts do not fix
   stops the build with a memo (AGENTS.md rule 7).
4. **The patch is what its sheet says:** `recipes/patches/libxml2-2.15.4/0001-…patch` equals
   `../upstream/8-libxml2-input-without-dup/fix.patch` byte for byte, and spec 020's rules pass
   on it and its draft.
5. **The numbers recorded** in the landing notes: the three binaries' and the zip's bytes, the
   zip's members, the three archives' sizes, the constructor list, plain and snapshot `-c pass`
   fuel, `import lxml.etree` and `import lxml.html` fuel on both binaries; each bound of Decision
   11 holds or is a finding.
6. **The judge.** `uv run pytest` is green with `--accept "<reason>"`, `--accept-judge "<the
   judge files>"` and `--accept-growth "<the causes>"`.
7. **The release.** A release dry run passes every job.

## The owner's choices

None open here. One entry is recorded as **82** in `../questions-for-the-owner.md`, each part
decided here so that nothing waits: whether lxml and regex (spec 047) may build before scipy,
which they do not need (decided: they wait for 038, as decision 48 says, unless the owner says
otherwise); `lxml.isoschematron` left out, its resources' terms unapproved and its by-path reads
unfixed (decided: out, with a stand-in); and lxml's ElementTree- and difflib-derived code read as
inside the CPython family already shipped (decided: shipped with its notices). The libxml2 facts
sheet follows question 80's recommendation; if the owner answers 80 otherwise, only the sheet's
body changes before the build moves it.

## Landing notes

Not built.
