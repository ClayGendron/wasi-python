# 047 — regex, built in

- **Status:** **built 2026-10-18; revised against its build review; confirmed; rebased onto
  spec 046 (main `7d377dd`) and rebuilt; awaiting the reviewer's delta look** (landing notes
  below; branch `spec/047-regex`, built from main `3e949a1`, rebased onto `4a94c14` and then
  `7d377dd`; the review is
  `build/reviews-evidence/047-buildreview/047-regex-2026-10-18.md` in the main tree, to be
  copied under `context/reviews/` by the lane). **Spec 051's callback scan binds this build** (051, Decision 4a; written in when 051 landed): `test_callbacks_have_the_types_cpython_calls` is green, and a mismatch it finds is fixed by a carried patch or an upstream release, never by an exclusion. confirmed for build 2026-10-18 with conditions (the review's Confirmation): Decision 9's rule binds — the name check is green over every scipy builtin in whichever of 047 and 037/038 lands second, never by an exemption; the builder confirms the package-context wrappers on the snapshot binary. drafted 2026-10-18; revised the same day against its pre-build review
  (`../reviews/046-lxml-and-047-regex-spec-2026-10-18.md`): the findings that concern it (3, 7,
  9, 10) are written in, and the review's Disposition says where. Finding 3 replaced the
  draft's forced-include header with a general fix in `scripts/gen_inittab.py`. Awaiting the
  review's confirmation. It changes the build recipe and the artifact
  set, so it is reviewed once more before it is built (constitution §5.6). It is build-class: it
  touches `scripts/`, `recipes/`, `downloads/SHA256SUMS` and the release workflow (§5.7). It
  carries one upstream patch (§4.1, to regex), so the review reads the patch and its facts sheet
  (spec 020, Decision 8).
- **Owner:** Clay Gendron
- **Kind:** the build recipe (one pin in `downloads/SHA256SUMS` and `scripts/00_download.sh`; a
  new step `scripts/steps/53_regex.sh`; `scripts/build.sh`, `scripts/steps/60_link.sh`,
  `scripts/steps/70_zip.sh`, `scripts/assemble_artifacts.py`), `scripts/gen_inittab.py` (every
  builtin's init function called inside CPython's package context), one carried patch to
  regex with its upstream facts sheet,
  judge additions and changes (`tests/`: one golden job, the oracle's pin, a general v1.1 check
  on builtin module names, guest checks, the judge's package, licence and source-tree lists),
  the release workflow's tree count, `README.md`, `CHANGELOG.md`, `LICENSES/`.
- **Depends on:** landed specifications only: 033 (`make_stdlib_zip.py --metadata`,
  `tree_members`), 020 (carried patches), 012 (the same bytes from any host), 004 and 009 (the
  licence notices). It needs nothing from scipy, matplotlib, tier A or spec 046 (lxml); Decision
  9 says how it meets them. Where one of them lands first in another shape than its text, this
  specification uses what landed and says so in its landing notes.
- **Research it stands on:** `../research/2026-10-17-what-else-the-default-profile-carries.md`
  (tier B: regex "one C file … nothing [WASI lacks] … easy"; nltk needs it; Pyodide's 0.66 MB
  `.so`; built with setuptools, read from the sdist); the owner's decisions 43 (its licence,
  Apache-2.0 AND CNRI-Python, §4.12) and 48 (in 0.1.0, after scipy) in `../decisions.md`;
  `../prior_art/pyodide-recipes/packages/regex/` (built unpatched for Emscripten). **The drafting
  runs** (EXECUTED 2026-10-17 and 2026-10-18 in the session's scratch folder, outside the
  repository, alongside spec 046's; the evidence is in
  `../upstream/9-regex-callback-signatures/evidence/`):
  - PyPI's JSON for regex 2026.9.29; the sdist and the macOS arm64 wheel downloaded and their
    SHA-256 recomputed (equal to PyPI's);
  - `src/_regex.c` and `src/_regex_unicode.c` compiled for `wasm32-wasip1` with the line's
    toolchain against CPython 3.15.0's headers (no warning under `-Wall`), linked into a
    scratch copy of today's plain reactor by step 60's own reactor link command (output and map
    redirected to the scratch folder), and run through `wasi_python.run`;
  - a feature program (`evidence/regex_probe.py`) natively and in the guest: first a trap, then,
    with the patch, byte-for-byte equal output; each of the five trapping calls alone, without
    and with the patch; pickling a compiled pattern, without and with the module-name header;
    every dotted builtin's `__name__` on the scratch binary; plain-reactor fuel.
  **The revision's runs** (EXECUTED 2026-10-18, after the pre-build review
  `../reviews/046-lxml-and-047-regex-spec-2026-10-18.md`, whose own runs are cited as "EXECUTED
  by the review"): a scratch inittab, generated from today's `build/link/inittab.c` plus lxml's
  and regex's entries, that calls each of the 61 init functions inside
  `_PyImport_SwapPackageContext`, compiled with `-DPy_BUILD_CORE_BUILTIN` and linked in place of
  `Modules/inittab.o`, with regex built without the header
  (`../upstream/9-regex-callback-signatures/evidence/package-context.txt`); `-DNDEBUG` and
  `-ffile-prefix-map` builds; fuel through the judge's seeded guest (`tests/harness/guest.py`).

## The problem

`regex` is the richer regular-expression engine (fuzzy matching, full Unicode properties,
graphemes, variable-length lookbehind, `captures()`), and the one nltk and tiktoken require.
Agents use it directly for text work. It is one C extension, `regex._regex`, over two C files,
with a pure-Python layer.

The research rated it easy: nothing it touches is missing on WASI. That holds, with two catches
the drafting runs found. Five of regex's callbacks are defined with fewer parameters than
CPython calls them with; native platforms ignore the extra argument, but WebAssembly checks the
type of every indirect call and traps ("bad signature"). And as a builtin, the module keeps the
name `_regex`, so pickling a compiled pattern looks for a top-level `_regex` and fails.

## Decisions

1. **The pin.** `regex-2026.9.29.tar.gz`,
   `https://files.pythonhosted.org/packages/fc/f2/af1da9d3ceed77bfcdce40427d49ba0be94e4fe84245e3bfef68c10e75b6/regex-2026.9.29.tar.gz`,
   SHA-256 `8b5fcc4771732191b2b7d1dd68d8f0353f47f8d90b6150f6dce58bf1112442cb` (PyPI's digest,
   recomputed). It is the current release (2026-09-29) and lists Python 3.15. A `get` line in
   `scripts/00_download.sh`'s host-neutral sources block; one line in `downloads/SHA256SUMS`.

2. **Step 53: regex** (`scripts/steps/53_regex.sh`, new, after step 50, needing steps 10 and 20).
   - It unpacks `regex-2026.9.29` from `pinned …` into `build/`, runs `patch_tree` (one patch,
     Decision 3), and compiles `src/_regex.c` and `src/_regex_unicode.c` through
     `scripts/wasi-cc` with `-O2 -DNDEBUG -ffile-prefix-map=$HERE=/wasi-python-build` (no
     build path in the binary: spec 046's Decision 3 and its v1.1 check; EXECUTED, `strings`
     finds none), CPython's `Include` and the cross-build folder's `pyconfig.h`. regex's `setup.py` adds one
     macro, `Py_GIL_DISABLED`, and only on a free-threaded build (READ); the line's CPython is
     not one, so no macro is added.
   - It then calls `scripts/wasi-cc -shared -o build/regex-build/regex/_regex.cpython-315-wasm32-wasi.so`
     on the two objects, so the archive and its `.so.deps` are in the shape step 60 already
     reads, as spec 046's step 54 does. `gen_inittab.py` finds `regex._regex` by path, with
     init function `PyInit__regex` (no clash with any module of numpy, pandas, 023, 037 or 046,
     READ from their lists).
   - **The package:** `build/regex-install/regex/` is a copy of the sdist's `regex/` folder
     (`__init__.py`, `_main.py`, `_regex_core.py`, `tests/`, which step 70 skips). The staging
     folder is needed because the sdist keeps `regex.egg-info/` beside the package, which
     spec 033's `tree_members` refuses at a tree's top (spec 039's pattern for pyyaml).

3. **One carried patch to regex: five callbacks gain the parameter CPython passes** (§4.1, spec
   020's mechanism). `recipes/patches/regex-2026.9.29/0001-callback-signatures.patch`, five lines
   changed in `src/_regex.c`: the getters `pattern_groupindex` and `pattern_pickled_data` gain
   `void* Py_UNUSED(closure)`, and the `METH_NOARGS` methods `match_capturesdict`,
   `match_allcaptures` and `match_allspans` gain `PyObject* Py_UNUSED(ignored)`. No caller and
   no behaviour changes on any platform. Its facts sheet is drafted at
   `../upstream/9-regex-callback-signatures/` (`pr.md`, `fix.patch`, `notes.md`, `evidence/`)
   and moves at build time to `../upstream/patches/regex-2026.9.29/0001-callback-signatures.md`,
   with `fix.patch` copied byte for byte into `recipes/patches/`.
   - **What fails without it** (EXECUTED, `evidence/unpatched-guest.txt`): `p.groupindex`,
     `pickle.dumps(p)`, `m.capturesdict()`, `m.allcaptures()` and `m.allspans()` each trap with
     "bad signature"; `m.groups()` in the same guest works. `regex.sub` with a `\g<name>`
     template reads `groupindex`, so it traps too; that is how the drafting runs found it.
   - **Why five and only five:** a scan of every `(getter)` and `(PyCFunction)` table entry in
     `_regex.c` against its definition's parameter count found these five; the type slots are
     assigned without casts, so the compiler checks them (`notes.md`).
   - **Why a patch:** no recipe can change a function's type. Pyodide builds the file unpatched
     because CPython's Emscripten build calls these through a trampoline; WASI's has none.
   - The facts sheet follows question 80's recommendation; regex's repository names no rule on
     AI-written changes, and the owner decides whether and how to send it.

4. **The module's name: every builtin is initialised inside the package context, by
   `scripts/gen_inittab.py`** (the review's finding 3; the draft's forced-include header is
   dropped). CPython gives a module loaded from a shared library its full dotted name through
   the package context, and gives a builtin none: `_PyImport_RunModInitFunction` swaps the
   context in around the init call (`Python/importdl.c:435-437`), and
   `_Py_ext_module_loader_info_init_for_builtin` sets `.newcontext=NULL` (`importdl.c:173`;
   READ in the line's CPython 3.15.0). A single-phase module then keeps its short `m_name`
   (`PyModule_Create2` resolves the name through `_PyImport_ResolveNameWithPackageContext`,
   `import.c:911-921`, `moduleobject.c:363`). regex's module is single-phase, created as
   `"_regex"`, so as a builtin its `__name__` and every function's `__module__` stay `_regex`,
   and pickling a compiled pattern fails with `PicklingError: … No module named '_regex'`
   (EXECUTED).
   - **The fix, general and in our own generated code.** `gen_inittab.py` writes, for each
     entry, a static wrapper
     `static PyObject *ctx_N(void) { const char *old = _PyImport_SwapPackageContext("regex._regex");
     PyObject *m = PyInit__regex(); _PyImport_SwapPackageContext(old); return m; }` and
     registers the wrapper, not the init function, with `PyImport_AppendInittab`. That is what a
     native import does. The generated file declares the one internal function itself (`extern
     const char *_PyImport_SwapPackageContext(const char *);`, the declaration of
     `Include/internal/pycore_import.h:77`); step 60 stops with one line if the pinned header no
     longer declares it so. `inittab.c` is already compiled with `PY_BUILTIN_MODULE_CFLAGS`
     (`-DPy_BUILD_CORE_BUILTIN`, READ in the cross-build `Makefile`). It is a change to a script
     of ours, not a patch.
   - **What it does to each kind of module.** Multi-phase modules (numpy's, pandas', lxml's,
     every Cython and pybind11 module, Pillow's and kiwisolver's) return a definition, not a
     module; the context is never read and is restored before their exec runs, so nothing
     changes. Single-phase modules whose `m_name` equals the last part of their import name
     take the dotted name, exactly as natively: regex's `_regex`, and, once spec 037 lands,
     scipy's f2py modules (numpy 2.5.2's f2py template calls `PyModule_Create(&moduledef)` with
     the module's own name, `numpy/f2py/rules.py:257`, READ by the review: `_fblas`, `_flapack`
     and the rest) and scipy's hand-written single-phase modules (`integrate/__quadpack.h`,
     `_lib/_uarray/_uarray_dispatch.cxx`; `odr/__odrpack.c` is not built, spec 037 Decision 9).
     A single-phase module whose `m_name` differs from its import name's last part keeps its
     short name (CPython's own rule), and the check below names it. The context is cleared by
     the first `PyModule_Create` that uses it, so a submodule an init function creates keeps its
     own name, as natively. The generated names come from the same table as the inittab, spec
     037's rename table for `PyInit_scipy__cyutility` included.
   - **EXECUTED** on a scratch binary whose inittab wraps all 61 builtins (numpy's 13, pandas'
     45, lxml's 2, regex's 1) and whose regex has no header: every dotted builtin imports with
     `__name__` equal to its import name; `regex._regex.__name__` and
     `regex._regex.compile.__module__` are `regex._regex`; `pickle.dumps(regex.compile(r"(?P<a>\w)+",
     regex.I), protocol=5)` gives the same 117 bytes as native (equal SHA-256); a pandas
     groupby, a numpy sum, a pickled DataFrame's length, `read_csv` and a seeded
     `default_rng` give native's results
     (`../upstream/9-regex-callback-signatures/evidence/package-context.txt`). The snapshot was
     not rebuilt with it; the build runs the check on both binaries.
   - Without the fix, today's 58 dotted builtins already keep their names (EXECUTED by the
     review); regex would be the first exception, and scipy's single-phase modules the next.

5. **Step 60 and step 70.** Step 60's package loop and its `gen_inittab.py` call gain
   `regex:"$B/regex-build"` and `regex=$B/regex-build`. Step 70 gains `--tree
   "$B/regex-install"` and `--metadata "$B/regex-2026.9.29/PKG-INFO"` (`Name: regex`, `Version:
   2026.9.29`, READ). `scripts/build.sh`'s `ALL` gains `53_regex` after `50_pandas`.

6. **What a guest sees.** Everything regex does natively, with its own Unicode tables (regex
   carries them in `_regex_unicode.c`, so the host never shows through). The drafting program's
   whole output equals native byte for byte (EXECUTED). One edge, stated in the README and not
   checked: `timeout=` works from the guest's clock, so a timeout depends on the host's speed;
   the embedder's fuel and deadline are the limits that hold. regex releases the GIL during long
   matches with `concurrent=True`; with no threads in the guest that changes nothing.

7. **The checks**, each seen failing first.
   - **The oracle.** `tests/jobs/oracle/pyproject.toml` gains `regex==2026.9.29`; `uv.lock`
     records its wheels (macOS arm64 `regex-2026.9.29-cp315-cp315-macosx_11_0_arm64.whl`,
     `7c03031610e3e6ed1768a2b7a8fc84637c1257b50c5eacaf094c6e17a84fc563`, recomputed; Linux
     aarch64 `42e82e578c904445d4c8a35b8f28052cf567593215fa5db06266fbc6f77aaa2e`; Linux x86_64
     `a714befaacbd10092ffe4cea0d3c5f008fb9efe9bc322c715bcdfdee414b9a3d`, READ from PyPI). The
     existing goldens must still reproduce (`regen.py --check`).
   - **A golden job, `regex_features` (v1.3),** `tests/jobs/regex_features.py` in `JOBS` (not
     `regex.py`, which would hide the package from its own script's folder on `sys.path`). Its
     first line is `versions python=… regex=2026.9.29`. It prints what the drafting program
     printed (fuzzy matching and `fuzzy_counts`, `BESTMATCH`, Unicode scripts and categories,
     graphemes, full case folding, named lists, `captures`, overlapped and reverse searches,
     partial matches, set operations, recursion, atomic and possessive groups, branch reset,
     variable lookbehind, POSIX matching, `subf`, `split`, named-group substitution, an error
     message) and the five patched calls, `groupindex`, `capturesdict()`, `allcaptures()`,
     `allspans()` and a pickle round trip with the pickle's length and SHA-256. Seen failing
     first on the current set: `ModuleNotFoundError: No module named 'regex'`; and on a build
     without the patch it traps (Decision 3).
   - **v1.1, `test_dotted_builtins_keep_their_import_names`** (both binaries): for every name in
     `sys.builtin_module_names` that contains a dot, the imported module's `__name__` equals it.
     It passes on today's set (numpy's and pandas' builtins) and fails on a build with regex
     and without Decision 4's wrappers with exactly `[('regex._regex', '_regex')]` (EXECUTED on
     the scratch binaries). It is general: a later single-phase package is caught the same way.
     **Its cost** (the review's finding 10): importing every dotted builtin took 5,016,014,720
     fuel on today's plain reactor and 104,839,431 on the snapshot (EXECUTED by the review),
     about 5.2 G on the scratch plain binary with lxml and regex (EXECUTED). scipy adds about
     85 builtins whose imports pull most of scipy. So the check runs once per judge run on each
     binary (it is one program, not one per module), with a fuel budget of 20 G on the plain
     binary and 10 G on the snapshot; the build records the real figures, and a figure above
     half its budget is a finding for the build review. If scipy pushes the plain run past its
     budget, the plain case is split into one run per top-level package, never narrowed to
     fewer modules.
   - **A unit check** on `gen_inittab.py` (no artifacts, seen failing before the change): the
     generated file registers a wrapper for every entry, each wrapper names its entry's dotted
     name, and no entry registers its init function directly.
   - **v1.1, `test_regex_is_builtin_at_manifest_version`** (both binaries): `regex._regex` is in
     `sys.builtin_module_names` and `regex.__version__` equals `MANIFEST`'s regex line.
   - **v1.3, `tests/checks/test_v1_3_regex.py`** (both binaries, nothing writable): the five
     patched calls return their native values without a trap, and a pickled compiled pattern
     loads back equal (its pattern, flags and `groupindex`).
   - **Judge changes** (under `--accept-judge`): `tests/harness/paths.py`'s
     `LICENCE_COMPONENTS` and `PACKAGES` gain `regex`; `pins.SOURCE_PATTERNS` and
     `needs.SOURCE_COMPONENTS` gain the tree, and the patched-tree check covers its patch; the
     release workflow's zero-patch count rises by one from main's count when this lands;
     `jobs.JOBS` gains `regex_features`; the synthetic set in `tests/unit/test_artifact_rules.py`
     gains the package and pin.

8. **What the set costs, so growth can be told from regression** (EXECUTED on the scratch
   build; the build measures each again and records it).
   - `python.wasm`: +713,905 bytes (31,760,992 to 32,474,897 with regex alone, `-DNDEBUG`),
     +2.25% (Pyodide's `.so` is 0.66 MB, INFERRED comparable). A growth outside 0.6 to 0.85 MB
     is a finding for the build review.
   - The snapshot: about the same bytes (not pre-imported).
   - The zip: +4 members (three modules and `METADATA`), about 90 KB deflated (88,301 bytes of
     compressed data for the three modules in the scratch zip).
   - **Fuel, through the judge's seeded guest** (`tests/harness/guest.py`, exact from run to
     run; the review's finding 7 showed an unseeded `-c pass` spreads by about 500,000):
     plain `-c pass` with today's zip is 242,002,526 on today's binary and 242,032,305 on the
     revised scratch binary (+29,779 for both specifications' three builtins and the 61
     wrappers together, EXECUTED twice, identical). The four new members add their
     per-member cost on top, measured by the judge's ratchet at build time.
   - `import regex` on the plain reactor through the same guest: 483,392,295 fuel against
     255,861,559 for `-c pass` with the same scratch zip (+227.5 M). The build records it on
     both binaries.

9. **Ordering and shared files.** Build-class, so it overlaps no other build-class change
   (§5.7). It needs nothing from scipy; decision 48 places it after scipy, and question 82 asks
   whether lxml and regex may go earlier (decided until answered: after 038). It is small and
   independent of spec 046; either may build first, and the second rebases onto the first's step
   60, step 70, `00_download.sh`, `SHA256SUMS` and the oracle's `pyproject.toml` and `uv.lock`.
   It shares those files with 023, 033, 037 and 039 as well; each is rebased onto main as it is
   when the builder starts. Once spec 040 has landed, the x86_64 rebuild must give the same
   bytes too.
   - **The condition with scipy (037 and 038), on whichever lands second** (the review's
     finding 3). If 047 lands first, 037's builder meets `test_dotted_builtins_keep_their_import_names`
     with scipy's modules in it: the wrappers name scipy's single-phase modules as natively, so
     the check must be green with all of scipy's builtins, and any module it still names (an
     `m_name` that is not the last part of its import name) is fixed in 037 by a rename-table
     entry or a recipe, never by an exemption in the check. If 037 lands first, 047's builder
     must make the check green over scipy's builtins too, and records each scipy module the
     wrappers renamed. Either way 038 lands only with the check green. Spec 037's text is not
     amended here; its builder reads this condition, and the landing notes of whichever lands
     second record it.

10. **Licence** (§4.12; approved by decision 43: Apache-2.0 AND CNRI-Python). `LICENSES/regex.txt`
    is the sdist's `LICENSE.txt` (the Apache License 2.0, headed by regex's statement that it
    derives from CPython's `re` module under CNRI's Python 1.6 licence), and then one line, as
    Apache-2.0 §4(b) asks of a modified file (the review's finding 9): "This build modifies
    src/_regex.c with recipes/patches/regex-2026.9.29/0001-callback-signatures.patch (five
    callbacks gain the parameter CPython passes); the module is otherwise compiled as
    released." The release ships `_regex.c` only as object code, so the duty is arguable; the
    line costs nothing. `assemble_artifacts.py` writes it from the patch's path, so the line
    and the patch cannot drift. The CNRI licence's text is already in `LICENSES/cpython.txt`
    (CPython's `LICENSE`, EXECUTED: it holds "CNRI LICENSE AGREEMENT"), which the README's
    licence line names. `MANIFEST` gains `regex 2026.9.29`, its pin and the patch by hash.

## Intent

An agent's code imports `regex` and gets native regex's answers, including fuzzy matching,
Unicode properties and pickled patterns, inside the same sealed Python, with regex's one
WebAssembly defect carried as a recorded, temporary patch.

## Design

| file | change |
|---|---|
| `downloads/SHA256SUMS`, `scripts/00_download.sh` | the regex sdist pin (Decision 1) |
| `scripts/steps/53_regex.sh` | new: the archive into `build/regex-build/`, the package into `build/regex-install/` (Decision 2) |
| `recipes/patches/regex-2026.9.29/0001-callback-signatures.patch` | new (Decision 3) |
| `context/upstream/patches/regex-2026.9.29/0001-callback-signatures.md`, `context/upstream/README.md` | the facts sheet, moved from `../upstream/9-regex-callback-signatures/pr.md`; its row |
| `scripts/gen_inittab.py` | each entry registered through a wrapper that sets the package context (Decision 4) |
| `scripts/build.sh`, `scripts/steps/60_link.sh`, `scripts/steps/70_zip.sh` | the step in `ALL`; regex in the link and the inittab; the tree and its metadata in the zip (Decision 5) |
| `scripts/assemble_artifacts.py`, `LICENSES/regex.txt` | the package and its notice (Decision 10) |
| `tests/jobs/regex_features.py`, `regex_features.expected`, `tests/jobs/oracle/pyproject.toml`, `uv.lock`, `tests/harness/jobs.py` | the golden job and the oracle's regex (Decision 7) |
| `tests/checks/test_v1_1_artifact_set.py`, `tests/checks/test_v1_3_regex.py` | the module-name check, the version check, the behaviour checks |
| `tests/harness/paths.py`, `pins.py`, `needs.py`, `tests/unit/test_artifact_rules.py` | regex in each list and the synthetic set |
| `.github/workflows/release.yml` | the zero-patch tree count, one more |
| `README.md`, `CHANGELOG.md` | regex in the profile; the `timeout=` note; the patch by path |

## Scope

In: Decisions 1 to 10. Out: nltk and tiktoken (nltk is pure but needs its data downloaded;
tiktoken is Rust and downloads its encodings: neither is in the default profile); pre-importing
regex in the snapshot; regex's own test suite under the runtime (hardening).

## Acceptance criteria

1. **The checks exist and were seen failing first:** the golden job, the two v1.1 checks and the
   v1.3 checks on the set the builder starts from (no regex; the module-name check passes there
   and is seen failing on a build with regex and without the wrappers); the unit check on
   `gen_inittab.py` before its change; the five calls trapping on a build
   without the patch; the patched-tree check on a tree without the patch.
2. **The build.** From an empty `build/` in a clean clone, `scripts/build.sh` applies the patch
   with no offset, builds step 53, links `regex._regex` with no clash, and makes a set whose
   binaries pass the checks and match the golden. `MANIFEST` names the pin and the
   patch. Steps 53 to 90 run twice give the same `SHA256SUMS`.
3. **The same bytes everywhere** (spec 012): the arm64 Linux rebuild gives macOS's `SHA256SUMS`;
   once spec 040 has landed, so does x86_64 Linux.
4. **The patch is what its sheet says:** the carried patch equals
   `../upstream/9-regex-callback-signatures/fix.patch` byte for byte, and spec 020's rules pass.
5. **The numbers recorded** in the landing notes: the binaries' and the zip's bytes and members,
   plain and snapshot `-c pass` fuel, `import regex` fuel on both binaries; each bound of
   Decision 8 holds or is a finding.
6. **The judge.** `uv run pytest` is green with `--accept`, `--accept-judge` and
   `--accept-growth`, each reason stated.
7. **The release.** A release dry run passes every job.

## The owner's choices

None open here. The ordering part of question **82** in `../questions-for-the-owner.md` covers
this specification with spec 046 (decided until answered: after 038, as decision 48 says). The
regex facts sheet follows question 80's recommendation; if the owner answers 80 otherwise, only
the sheet's body changes before the build moves it.

## Landing notes

Built 2026-10-18 by a builder agent (Claude Opus 5.5) in the worktree `wasi_python-047`, branch
`spec/047-regex`, from main `3e949a1` (spec 059 in: every compile carries `-ffp-contract=off`).
The machine: Apple arm64, macOS 26.5, 10 cores; Docker with the research image `wp040-arm64`
(Debian 13, uv 0.9.22). Every claim is EXECUTED unless labelled. Evidence is under the main
tree's git-ignored `build/reviews-evidence/047-build/` (named below by file). Not yet reviewed:
the build review is next, then the lane. Spec 037 (scipy) has not landed, so Decision 9's
condition passes to 037's builder: the name check must be green over every scipy builtin when
037 lands, never by an exemption.

### What changed

- Commits `f4ee3d9` (the build) and `a120cf3` (the build progress checks count fourteen steps).
- **The pin** (`downloads/SHA256SUMS`, `scripts/00_download.sh`'s sources block):
  `regex-2026.9.29.tar.gz` `8b5fcc47…`, PyPI's JSON digest, and the downloaded file's SHA-256
  recomputed equal. The oracle's three wheels in `uv.lock` carry the digests Decision 7 names
  (`7c030316…`, `42e82e57…`, `a714befa…`), equal to PyPI's JSON.
- **Step 53** (`scripts/steps/53_regex.sh`), in `build.sh`'s `ALL` after `50_pandas` (fourteen
  steps): unpack, `patch_tree`, check `PKG-INFO`'s version, compile the two C files with `-O2
  -DNDEBUG -ffile-prefix-map=…` (0 warnings each), `wasi-cc -shared` into
  `build/regex-build/regex/_regex.cpython-315-wasm32-wasi.so`, and stage the package under
  `build/regex-install/regex/`.
- **The patch** `recipes/patches/regex-2026.9.29/0001-callback-signatures.patch` (SHA-256
  `4c5dcaa9…`), `cmp`-equal to `context/upstream/9-regex-callback-signatures/fix.patch`; applied
  "cleanly" (no offset). Its sheet moved unchanged (`git mv`, 100% similarity) to
  `context/upstream/patches/regex-2026.9.29/0001-callback-signatures.md`; the upstream README's
  row says it is carried.
- **`scripts/gen_inittab.py`**: each entry is registered through `ctx_N`, which calls its init
  function between two `_PyImport_SwapPackageContext` calls, the first naming its dotted name;
  the file declares the function as `pycore_import.h:77` does. **Step 60** stops with one line if
  the pinned header's declaration changes (the `grep` matches the 3.15.0 header, EXECUTED), and
  links `regex._regex`. **Step 70** adds the tree and `PKG-INFO`. **Step 90** adds `package regex
  2026.9.29` and writes `LICENSES/regex.txt`: the sdist's `LICENSE.txt`, then the line
  `modified_notice` builds from the patch's own `+++ b/` paths and a table keyed by the patch's
  path ("This build modifies src/_regex.c with recipes/patches/regex-2026.9.29/0001-callback-
  signatures.patch (five callbacks gain the parameter CPython passes); the module is otherwise
  compiled as released."). A patch with no line, or a tree with none, stops the build.
- **The judge** (`--accept-judge`): `test_v1_3_regex.py` (the golden job on both binaries, slow;
  the five patched calls; a pickle round trip), `test_dotted_builtins_keep_their_import_names`
  and `test_regex_is_builtin_at_manifest_version` in v1.1, the unit check
  `test_the_inittab_registers_each_module_through_its_package_context`, `regex_features` in
  `JOBS` with its golden, the oracle's `regex==2026.9.29`, regex in `paths.LICENCE_COMPONENTS`
  and `PACKAGES`, `pins.SOURCE_PATTERNS`, `needs.SOURCE_COMPONENTS`, the synthetic set,
  `DISTRIBUTIONS` (spec 033's rule for a new distribution), and the build progress checks'
  step counts (`[7/14]`, `[14/14]`, `done: 14 steps`). The release workflow's zero-patch count is
  sixteen (main's fifteen plus one).
- `README.md` (the profile rows, *regex in the guest* with the `timeout=` edge and the licence,
  the patch count six, fourteen steps), `CHANGELOG.md` (0.1.0a6 — unreleased, the patch by path).

### Each criterion against its evidence

1. **The checks exist and were seen failing first.**
   - On main's frozen set `s-4eb5418a2b1bb553` (`seen-failing-main-set.txt`): the golden job, the
     five calls, the pickle and the version check fail on both binaries with
     `ModuleNotFoundError: No module named 'regex'`. The name check passes there once matplotlib
     can import (below: 68 dotted builtins; 6,163,121,466 fuel plain, 1,313,272,023 snapshot).
   - On a build with regex and the patch but **without the wrappers** (main's `gen_inittab.py`
     put back for steps 53 to 90; `B-build.log`, `B-checks.txt`): the name check fails on both
     binaries with exactly `[['regex._regex', '_regex']] (of 69 dotted builtins)`; the pickle
     check and the golden job fail with `when serializing _regex.Pattern object`. Six failures
     in all: those three checks, each on both binaries. The five-calls check passes there, as it
     should: the patch is in, and `p._pickled_data` returns a tuple without pickling anything
     (corrected against the build review's finding 1).
   - On a build **without the patch** (the patch folder moved aside for step 53, then put back,
     `cmp`-equal; `A-checks.txt`, `A-five-alone.txt`): each of the five calls alone traps on both
     binaries (`wasm trap: indirect call type mismatch`), as does `regex.sub` with a `\g<name>`
     template, while `m.groups()` answers `('x', '2')`; spec 051's scan names the five
     (`5 callback mismatches: getter _pickled_data: table index 17587 has (i32) -> (i32), called as
     (i32, i32) -> (i32) …`); and the patched-tree check fails on that tree
     (`src/_regex.c: modified`).
   - The unit check failed before `gen_inittab.py` changed (`seen-failing-unit.txt`: no
     `_PyImport_SwapPackageContext` declaration in the generated file).
2. **The build.** A committed worktree at `f4ee3d9`, `rm -rf build`, `scripts/build.sh --plain`:
   fourteen steps in 8 min 05 s (`build-047.log`); the patch applies with no offset, step 53 is
   ok in 4 s, step 60 links with no clash. `MANIFEST` names `package regex 2026.9.29`, the pin
   `8b5fcc47… regex-2026.9.29.tar.gz` and `recipe 4c5dcaa9…
   recipes/patches/regex-2026.9.29/0001-callback-signatures.patch`. Steps 53 to 90 run again give
   the same `SHA256SUMS`, every line (`rebuild-53-90.log`, `diff` against `SHA256SUMS-first`).
3. **The same bytes everywhere.** A clean clone of `f4ee3d9`, built from an empty `build/` in a
   `linux/arm64` container (`linux/host.txt`, `linux/build-output.txt`): fourteen steps in
   20 min 58 s (the judge ran beside it), and its `SHA256SUMS` equals macOS's, every line (`diff`;
   the file's SHA-256 `db73583a…` on both). The container first installs Debian's `python3`
   (3.13.5), which step 37 runs through HarfBuzz's `#!/usr/bin/env python3` (023's unpinned host
   input, a known follow-up, not fixed here). The x86_64 rebuild was not run here: the release dry
   run's.
4. **The patch is what its sheet says:** `cmp` equal (SHA-256 `4c5dcaa9…` both);
   `test_carried_patches_follow_the_rules` passes (CHANGELOG names it, the sheet's six header
   lines and `Files: src/_regex.c` match, README says "upstream patches carried: 6");
   `test_source_tree_matches_its_tarball[regex]` passes on the build's tree.
5. **The numbers** (below). Each bound of Decision 8 holds: `python.wasm` grew 717,283 bytes
   (inside 0.6 to 0.85 MB); the snapshot about the same (700,265); the zip four members.
6. **The judge** (below): green but for growth, each growth with its cause; not accepted (the
   lane's).
7. **The release dry run:** not run here; the lane's.

### The snapshot condition (the review's Confirmation)

The wrappers leave the pre-imported numpy and pandas as they are (`snapshot-probe.txt`): on this
set's snapshot and plain binaries, main's two and natively, the same output, line for line:
`numpy._core._multiarray_umath`, `numpy.random._pcg64` and `pandas._libs.lib` keep their names,
`default_rng(0)` gives `[0.6369616873214543, 0.2697867137638703, 0.04097352393619469]`, a
pickled `default_rng(1)` continues the same stream, a groupby, a 926-byte DataFrame pickle round
trip, a Timestamp and a dtype pickle's hash are native's. The name check passes on the snapshot,
and the full judge's numpy, pandas and matplotlib checks pass on both binaries.

Which builtins the wrappers rename: only `regex._regex` (set B, without wrappers, names it
alone among 69). numpy's, pandas', Pillow's, kiwisolver's and matplotlib's modules already had
their names; the wrappers change nothing in them that any check or the probe sees.

### The numbers (Decision 8; seeded guest, `tests/harness/guest.py`)

| | main `3e949a1` (set `s-4eb5418a2b1bb553`) | this set |
|---|---|---|
| `python.wasm` | 36,916,497 `16550143…` | 37,633,780 `b232655f…` (+717,283, +1.94%) |
| `python-snapshot.wasm` | 70,901,724 `4eb5418a…` | 71,601,989 `449f4029…` (+700,265) |
| `python-stdlib.zip` | 21,948,256, 2,391 members | 22,046,871 `276b4dcf…`, 2,395 members (+98,615) |
| wheel (the release's `uv build --wheel …`, each from its own commit and set) | 52,095,964 | 52,501,836 (+405,872, +0.78%) |
| plain `-c pass` | 166,511,583 | 166,647,401 (+135,818, +0.082%) |
| snapshot `-c pass` | 83,372,077 | 83,512,487 (+140,410, +0.17%) |
| plain `import regex` | — | 395,297,353 (+228.6 M over `-c pass`) |
| snapshot `import regex` | — | 195,217,333 (+111.7 M over `-c pass`) |
| the name check, plain / snapshot | 6,163,121,466 / 1,313,272,023 | 6,281,364,302 / 1,427,908,448 |

- The zip's four members (`numbers-047.txt`): `regex/__init__.pyc` 207 bytes compressed,
  `_main.pyc` 13,506, `_regex_core.pyc` 73,186 (86,899 for the three modules; the draft's scratch
  zip: 88,301), and `regex-2026.9.29.dist-info/METADATA` 11,236.
- **Where plain `-c pass`'s growth comes from** (`fuel-cross.txt`, each binary with each zip):
  the binary +19,328 (one more inittab entry and 70 wrappers; the draft's scratch figure was
  +29,779 for three builtins and 61 wrappers) and the zip +96,941 (four members, about 24,000
  each, under the judge's 30,000 per member). The wrappers alone cost 34 fuel on plain `-c pass`
  and 0 on the snapshot, and 3,365 bytes (sets A and B, `numbers-A-B.txt`). The snapshot's
  +140,410 cannot be split the same way (a snapshot runs only with its own zip); INFERRED: the
  same two causes.
- `import regex` costs 228.6 M on the plain reactor (the draft: 227.5 M).
- **The name check's budgets.** Plain 6.28 G of 20 G, snapshot 1.43 G of 10 G: both under half.
  The review's 0.105 G snapshot figure predates matplotlib, whose ten builtins the snapshot does
  not pre-import; main's set already takes 1.31 G.

`SHA256SUMS`'s artifact, `MANIFEST` and regex licence lines (the 26 other licence lines are
main's, unchanged; the whole file is `SHA256SUMS-first`, equal on both hosts):

```
d3777e281eddd30b3128a19c263e5a428cfec613e0f8f37d9bec451f3e673e8e  LICENSES/regex.txt
e50715e5eb866d1b6d2b05e12ff087c4eab44a4a4671dcbbda2d6ddcc441e505  MANIFEST
449f4029b758768ebed58ff462ca57486ab518d8997f20c9ab015af53935d437  python-snapshot.wasm
276b4dcfbfd4a314a63bdc4a87c678ebcd5a02f5830121efe7190a6238f72dda  python-stdlib.zip
b232655f0396463412dc4e376ecb63d72032d858eab3f371c8602a2b816e727d  python.wasm
```

### The judge

The fast tier, `uv run pytest -m "not slow" -n 3` (`fast-1.txt`): 1549 passed, 9 skipped, 0
fail. The full `uv run pytest`, serially, once, at `a120cf3` with this set, the wheel built from
it and the upstream kit copied from the main tree's `build/upstream/wheels/` (the harness checks
each wheel's hash; `full-judge.txt`, `latest-full.json`):

```
wasi_python v1: 392/408 pass · 14 gap · 2 blocked · 0 fail   (unit suite 1191/1198, 7 skipped)
blocked by: prior-art clones 1 · three systems 1
ratchet vs fdb06c26f1: lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 12 · grew 78 · judge changed: tests/checks/test_v1_1_artifact_set.py, tests/checks/test_v1_3_data_stack.py, tests/checks/test_v1_3_regex.py and 11 more
RED: 78 metric(s) grew
1583 passed, 9 skipped, 14 xfailed in 959.04s (0:15:59)
```

The two blocked checks are the prior-art clones (the worktree has none) and the three systems
(the release's); the 14 gaps are main's. Gained 12: this specification's eleven new checks and
the wheel check (main's acceptance ran without a wheel); `test_same_bytes_passed_on_three_systems`
is new to the record and blocked. **Each growth, with its cause** (`growth-full.txt`, 81 rows against
`accepted.json`, 78 past the ratchet's tolerance):

- **Bytes, three:** `python.wasm` +717,283 and the snapshot +700,265 (regex's module and its
  Unicode tables, Decision 8's bound), the zip +98,615 (four members).
- **Every guest start, about +0.13 M to +0.15 M fuel** (most rows: v1.2, v1.4, the zip's directory
  checks, the `-c` checks of v1.1 and v1.3): the four members' per-member cost and the binary's
  one more builtin, split above.
- **The upstream suites** (+6.8 M to +78.5 M, 0.013% to 0.235%): each group runs in one guest,
  so the per-start cost explains about 0.14 M of each. The rest is regex's `METADATA` in the zip,
  read by every `importlib.metadata` walk: pytest, pluggy and hypothesis walk the distributions
  at start-up, and a full walk costs 14.6 M more on this set (13.7 M on the snapshot), an
  `entry_points(group='pytest11')` 14.4 M more (EXECUTED by the build review). How many walks
  each group makes is INFERRED from the totals, not counted.
- **The golden jobs and matplotlib's checks** (+0.3 M to +2.6 M, at most 0.05%): the per-start
  cost and more; not split (INFERRED: lookups among the zip's four more members).
- **`test_packages_carry_their_metadata`**, +28.4 M plain (+0.53%) and +27.8 M snapshot (+5.65%):
  regex's 40,564-byte `METADATA` in the zip. Parsing it costs 14.1 M on either binary, and the
  check's guest program reads each distribution's metadata twice, its `Name` and then its
  `version` (EXECUTED by the build review). It is not a judge change: the guest program did not
  change, and `DISTRIBUTIONS` is read on the host.
- **`test_resources_read_as_zipfile_reads_them`**, +9.4 M plain and +17.8 M snapshot (0.15%,
  0.31%): it walks every member of the zip, four more.

The accepting run needs `--accept`, `--accept-judge` (the judge changed: the checks above, the
oracle and its lock, the lists) and `--accept-growth`. The growth reason, word for word:

```
spec 047 adds regex: python.wasm +717,283 and the snapshot +700,265 bytes (regex's module and its Unicode tables); the zip +98,615 bytes, four members; every guest start about +0.14 M fuel (the four members' per-member cost and one more builtin); regex's 40,564-byte METADATA in the zip, parsed by every importlib.metadata walk (14.1 M each, measured): test_packages_carry_their_metadata reads it twice, and the upstream suites make a few such walks per group through pytest, pluggy and hypothesis (inferred, not counted); test_resources_read_as_zipfile_reads_them walks four more members
```

### Stand-ins and departures

- **No stand-in module.** regex builds unmodified but for the one patch.
- **The name check grants matplotlib's data** (`MPLCONFIGDIR` and the mpl-data grant, as
  matplotlib's own checks do). The spec's check imports every dotted builtin; since spec 023
  landed after the draft, ten of them are matplotlib's, and importing `matplotlib._image` without
  its data raises `NotADirectoryError` (seen on main's set). The grant lets every module import;
  no module is left out.
- **The trap reads "indirect call type mismatch"**, not the draft's "bad signature": the judge's
  driver reports wasmtime's own message. The same five calls trap.
- **The golden job's pattern** carries `regex.I` and its pickle is 142 bytes (`a1304727…`, native
  and guest alike), not the draft's 117-byte pattern without flags; the checks also cover the
  draft's form (`test_a_pickled_pattern_loads_back_equal`).
- **The snapshot name-check figure** is 1.43 G, not the review's 0.105 G: matplotlib's builtins
  (above).
- **The hunks shared with spec 046** (`SHA256SUMS`, `00_download.sh`, the oracle's
  `pyproject.toml`, `paths.py`, `pins.py`, `needs.py`, `DISTRIBUTIONS`, the synthetic set) sit at
  other lines than 046's where the order does not matter, so the second to land rebases with few
  conflicts; step 60's loop and `gen_inittab.py` call, step 70's two lines, `build.sh`'s `ALL`,
  the progress checks' counts, the README's counts and the release's tree count will conflict
  by a word each.

### Revised against the build review

The build review (`047-regex-2026-10-18.md`, in the main tree's
`build/reviews-evidence/047-buildreview/`) found the wrappers correct, no existing module changed
(68 fingerprinted on both binaries) and the snapshot's pre-import identical. Its verdict: lands
once findings 1 and 2 are fixed; both are text.

**Disposition.**

1. **Finding 1, the set B sentence: fixed.** Criterion 1 now says set B's six failures are the
   name check, the pickle check and the golden job, each on both binaries, and that the
   five-calls check passes there (`B-checks.txt`; the patch is in, and `p._pickled_data` returns
   a tuple without pickling anything).
2. **Finding 2, two growth causes: fixed.** `test_packages_carry_their_metadata` grows from
   regex's 40,564-byte `METADATA` in the zip, parsed at 14.1 M and read twice by the check; it is
   not a judge change. The upstream suites grow from the metadata walks of pytest, pluggy and
   hypothesis, each about 14.5 M more; the number of walks per suite is INFERRED, not counted. The
   figures are the review's (EXECUTED by the review). *The judge* above gives the
   `--accept-growth` reason word for word.
3. **Finding 3, "every builtin": fixed in the README and the CHANGELOG.** Both now say the init
   function of each of the 69 cross-built builtins runs inside the package context (CPython's
   own builtins are not wrapped, and need not be: their names have no dot), and the CHANGELOG says
   numpy's, pandas' and matplotlib's modules are multi-phase "or already named in full"
   (`pandas._libs.json` is single-phase with its full name). Decision 4's own text is left as
   reviewed before the build.
- **Notes N1 to N3** are left for the owner and the lane: the facts sheet moved unchanged, as
  Decision 3 asked (its tense and "bad signature" are the owner's to update before sending); the
  README's sizes row stays spec 023's, as it says; step 60's guard message is unchanged.
- **N4, the build-progress segfault:** never seen in this builder's runs. No `Segmentation` line
  in the two fast-tier runs (`-n 3`), the two full serial runs or the unit runs, before or after
  the rebase; `test_build_progress.py` passed whole each time.

### Rebased onto main

`git rebase 4a94c14` (main with 057, 059, 060, 061, 062 and decision 34) applied all three
commits with no conflict: `d75da15` (the build), `26c1d22` (the progress checks), `3dcf0d9` (the
landing notes), then `63376c5` (findings 1 and 3) and this revision. Rebuilt from the pins in the
worktree, from an empty `build/` (`rebased/build-rebased.log`, fourteen steps in 11 min 05 s,
057's unpinned-name check in step 00 passing): `python.wasm` `b232655f…`, the snapshot
`449f4029…` and the zip `276b4dcf…` are unchanged, byte for byte. `MANIFEST` differs from the
first build in one line, `scripts/00_download.sh`'s recipe hash (`3b408469…` to `4a3c2b4d…`,
057's edit), so the set's `SHA256SUMS` (SHA-256 `6322071c…`) differs from the first build's
in the `MANIFEST` line only:

```
d3777e281eddd30b3128a19c263e5a428cfec613e0f8f37d9bec451f3e673e8e  LICENSES/regex.txt
13456dd9b890b5f3121960ba77c5b56418e2599de9345451846b0eed34f0e88a  MANIFEST
449f4029b758768ebed58ff462ca57486ab518d8997f20c9ab015af53935d437  python-snapshot.wasm
276b4dcfbfd4a314a63bdc4a87c678ebcd5a02f5830121efe7190a6238f72dda  python-stdlib.zip
b232655f0396463412dc4e376ecb63d72032d858eab3f371c8602a2b816e727d  python.wasm
```

The 26 other licence lines are main's, unchanged. The wheel from this set is 52,502,412 bytes
(the README's revised wording). The judge against this rebuilt set, at `63376c5` (evidence under
`rebased/`): the fast tier, `uv run pytest -m "not slow" -n 3`, 1602 passed, 9 skipped, 0 fail;
the full `uv run pytest`, serially, once:

```
wasi_python v1: 411/427 pass · 14 gap · 2 blocked · 0 fail   (unit suite 1225/1232, 7 skipped)
blocked by: prior-art clones 1 · three systems 1
ratchet vs 2ce08a592d: lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 12 · grew 78 · judge changed: tests/checks/test_v1_1_artifact_set.py, tests/checks/test_v1_3_data_stack.py, tests/checks/test_v1_3_regex.py and 11 more
RED: 78 metric(s) grew
1636 passed, 9 skipped, 14 xfailed in 842.34s (0:14:02)
```

The 78 grown metrics are the same rows with the same causes as before the rebase
(`rebased/growth-rebased.txt`: the same 81 rows against the new `accepted.json`, each delta
within 22,219 fuel of its first value); the name check takes 6,281,364,302 plain and 1,427,908,431 snapshot. Spec
069 (no package pre-imported in the snapshot, decision 34) has not landed; if it lands first, the
snapshot's figures here move.

### Rebased onto 046

Spec 046 (lxml) landed as main `7d377dd` (accepted as `41dffc2`, frozen set
`s-ff5246a2c2f1a52b`). `git rebase 7d377dd` stopped on the build commit with conflicts in ten
files, each resolved so both packages are present (EXECUTED):

- `scripts/build.sh`: `… 50_pandas 53_regex 54_lxml 55_matplotlib …`, **sixteen steps**; the
  build progress checks count them (`53_regex` before `54_lxml` in `STEPS`, `n = 16`, `40_numpy`
  at **[8/16]**, `[16/16] 90_artifacts`, `[1/16]`, `lines[17:]`, `done: 16 steps`). The old
  progress commit `26c1d22` became empty (its edits were taken into the build commit) and was
  dropped.
- `scripts/steps/60_link.sh`: the header names both; the `gen_inittab.py` call and the package
  loop take `regex=` / `regex:` and then `lxml=` / `lxml:`. `scripts/steps/70_zip.sh`: both
  trees, both `PKG-INFO`s, both directory checks. `scripts/assemble_artifacts.py`: lxml's
  notices and regex's `MODIFIED` and `modified_notice`, side by side; `MODIFIED` needs no line for
  libxml2's patch (`modified_notice` reads only regex's folder).
- `.github/workflows/release.yml`: **nineteen** trees. `README.md`: both packages in the profile
  rows, **"upstream patches carried: 7"**, seven patches named, sixteen steps, both build
  steps described; main's sizes and build-time rows kept. `context/upstream/README.md`: rows 8
  and 9 both "carried". `tests/harness/jobs.py`: `lxml_xml` and `regex_features`.
- `tests/jobs/oracle/pyproject.toml`: both pins. `uv.lock` was made with `uv lock` (as before,
  through the oracle's own interpreter and cache); I regenerated it from the merged
  `pyproject.toml` and it equals git's text merge byte for byte. Both goldens reproduce under the
  synced oracle (`lxml_xml`, `regex_features`: no diff).
- `CHANGELOG.md`: regex's entry moved into **"0.1.0a7 — unreleased"**, after lxml's (0.1.0a6 was
  released on 2026-10-19). The README's and CHANGELOG's builtin count is now **71** (69 plus lxml's
  two).
- The review's **C1**: the rebase section's `00_download.sh` hash pair now reads in order,
  `3b408469…` to `4a3c2b4d…` (the first build's `MANIFEST` held `3b408469…`).

**The rebuild.** From an empty `build/` at `c297791`, from the pins in the worktree
(`on-046/build-046base.log`): sixteen steps in 9 min 53 s; step 53 ok, step 54 ok, step 60 links
with no clash. The set's `SHA256SUMS` (SHA-256 `0923cd6e14f3c984…`; `on-046/SHA256SUMS`) against
046's frozen set: `LICENSES/regex.txt` added, and the three artifacts and `MANIFEST` changed; the
other 28 licence lines are 046's.

```
d3777e281eddd30b3128a19c263e5a428cfec613e0f8f37d9bec451f3e673e8e  LICENSES/regex.txt
d2943c284f53ad8dd21855cafe9a70d7c8365fef28be498b5ec885aef1153725  MANIFEST
a8221564acc6afc3e12bdee3321a120ba8dc044567c8a72174a0348634b24fa3  python-snapshot.wasm
02026895917b7e22923db1bad99a02ee1d22f7382ff63715271e39fb9032d1fe  python-stdlib.zip
feb7fc0729dd7e4bf275f9a8c29ca5f2073c8619760618f09598eaee578d0fe0  python.wasm
```

**The numbers against 046's set** (seeded guest; `on-046/numbers.txt`, `on-046/fuel-cross.txt`):

| | 046 (`s-ff5246a2c2f1a52b`) | this set |
|---|---|---|
| `python.wasm` | 40,374,948 `308118d1…` | 41,092,208 `feb7fc07…` (+717,260, +1.78%) |
| `python-snapshot.wasm` | 74,364,935 `ff5246a2…` | 75,071,675 `a8221564…` (+706,740, +0.95%) |
| `python-stdlib.zip` | 22,098,558, 2,417 members | 22,197,173 `02026895…`, 2,421 members (+98,615) |
| wheel (the release's command, each from its own commit and set) | 54,342,031 | 54,777,796 (+435,765, +0.80%) |
| plain `-c pass` | 167,180,268 | 167,230,744 (+50,476, +0.030%) |
| snapshot `-c pass` | 83,425,451 | 83,491,413 (+65,962, +0.079%) |
| plain / snapshot `import regex` | — | 395,928,886 / 195,429,820 |
| the name check (71 dotted builtins), plain / snapshot | — | 6,333,244,223 / 1,474,244,263 |

Plain `-c pass` split by binary and zip: this binary with 046's zip costs 40,850 **less**
(167,139,418), and 046's binary with this zip 83,162 more (167,263,430). The binary's part is
negative here, where it was +19,328 against `4a94c14`'s set: INFERRED, the memory layout moves
with every link (below). The name check is green over all **71** dotted builtins on both
binaries, each under half its budget. Spec 051's scan: 3,604 method-array entries, 2,313 single
definitions, 1,325 getset entries, 451 member entries, no finding.

**No existing module moved** (the build review's fingerprint probe, `modfp_host.py` and
`modfp_guest.py` copied unchanged, run on 046's set and this set, both binaries;
`on-046/modfp.json`, `on-046/modfp-compare.txt`): 69 of 046's 70 dotted builtins have identical
fingerprints; `regex._regex` is new and named in full; no module's `__name__` differs from its
import name; the modules present at start are the same (70 plain, 594 snapshot, the same
digest). The one difference is `lxml.objectify`'s `attr_modules`, which holds the `repr` of an
`_ObjectifyElementMakerCaller` instance, `<… object at 0x1c33eb8>` against `0x1cb2158`: a heap
address in the probe's own output, not a change to the module.

**The judge** at `c297791` against this set, with the wheel built from it and the upstream kit
copied by hash: the fast tier (`-n 3`) 1622 passed, 9 skipped, 0 failed. The full `uv run
pytest`, serially, once (`on-046/full-046base.txt`, `on-046/latest-046base.json`):

```
wasi_python v1: 433/449 pass · 14 gap · 2 blocked · 0 fail   (unit suite 1226/1233, 7 skipped)
blocked by: prior-art clones 1 · three systems 1
ratchet vs 5475925677: lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 12 · grew 89 · judge changed: tests/checks/test_v1_1_artifact_set.py, tests/checks/test_v1_3_data_stack.py, tests/checks/test_v1_3_regex.py and 11 more
RED: 89 metric(s) grew
1659 passed, 9 skipped, 14 xfailed in 951.58s (0:15:51)
```

No `Segmentation` line in either run. **The growth against 046's acceptance**
(`on-046/growth.txt`: 100 rows, 89 past the ratchet's tolerance):

- **Bytes:** `python.wasm` +717,260, the snapshot +706,740, the zip +98,615 (four members).
- **Every guest start:** +0.04 M to +0.13 M (plain), +0.04 M to +0.07 M (snapshot), on the v1.1,
  v1.2, v1.4, lxml, matplotlib and zip-directory checks.
- **`test_packages_carry_their_metadata`:** +28.3 M plain (+0.53%), +28.0 M snapshot (+5.61%):
  regex's METADATA parsed twice, as before.
- **`test_resources_read_as_zipfile_reads_them`:** +15.2 M plain, +9.2 M snapshot (four more
  members walked).
- **`test_extra_preopens_work_on_the_snapshot`** (both orders): +3.04 M (+0.36%). The probe walks
  every live object (`gc.get_objects()`). Its figure moves both ways with the set: 850,787,596 at
  `4a94c14`'s acceptance, 849,218,103 with 047 on that base (lower), 848,648,184 at 046's
  acceptance (046 lowered it by 2.1 M), 851,684,695 here. INFERRED: the heap's layout.
- **The upstream suites:** the review's metadata walks (about 14.5 M each) explain rows of tens of
  millions, but not `numpy-core`'s **+1,284,358,477 (+0.635%)**. That figure is deterministic and
  is this set's (EXECUTED: `numpy-core` alone, three runs: 203,634,070,415 and 203,634,092,974 on
  this set, 202,349,694,921 on 046's, which equals 046's accepted 202,349,737,812 to 43 K;
  identical pass digest `df21e78e7032`, 9,519 passes). The groups move both ways with any change
  to the set, by hundreds of millions:

  | group | 046 against `4a94c14` | 047 against `4a94c14` | 047 against 046 |
  |---|---|---|---|
  | numpy-core | +113,579,111 | +49,653,702 | **+1,284,358,477** |
  | numpy-lib | +61,529,901 | +22,780,343 | +6,070,331 |
  | numpy-others | +234,418,884 | +70,006,740 | −190,890,497 |
  | pandas-frame | −131,180,293 | −109,650,302 | −194,790,196 |
  | pandas-groupby | +10,094,187 | −262,607,401 | −182,981,881 |
  | pandas-internals | −15,308,403 | +9,490,995 | +35,360,723 |
  | pandas-io-formats | −3,219,970 | +6,819,851 | +14,865,832 |
  | pandas-io-parser | −66,007,325 | −22,752,512 | +33,847,832 |
  | pandas-libs | −58,389 | +25,732,209 | +22,412,494 |
  | pandas-reshape | −97,536,540 | −58,944,940 | +28,203,284 |
  | pandas-tslibs | −23,198,695 | +78,524,563 | +57,278,942 |

  Against 046 the eleven groups' net is +913,735,341 (046's own net against `4a94c14`:
  +83,112,468). INFERRED, not proved: the snapshot's heap layout. Objects hashed by address
  (sets and dicts of types and functions) and the collector's timing change with every link,
  and a long suite magnifies that. Even so, `numpy-core`'s +0.635% is the largest single move
  in this table, and it is a finding for the delta look, not a cause I have measured. The two
  causes in hand are far too small for it: a metadata walk costs about 14.5 M, and a start under
  0.2 M. I did not split it further; a per-test fuel split of `numpy-core` on both sets would
  decide it.

**The `--accept-growth` reason against 046**, word for word, if the delta look accepts the
upstream rows as layout:

```
spec 047 adds regex on 046: python.wasm +717,260 and the snapshot +706,740 bytes (regex's module and its Unicode tables); the zip +98,615 bytes, four members; guest starts +0.04 M to +0.13 M fuel (four more zip members, one more builtin); test_packages_carry_their_metadata +28 M (regex's 40,564-byte METADATA, parsed at 14.1 M and read twice); test_resources_read_as_zipfile_reads_them walks four more members; test_extra_preopens_work_on_the_snapshot +3.0 M and the upstream groups (-195 M to +1,284 M; numpy-core +0.635%, deterministic) move both ways with the snapshot's heap layout, as 046's own landing moved them (-131 M to +234 M) (inferred, not split per test)
```

