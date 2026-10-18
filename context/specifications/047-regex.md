# 047 — regex, built in

- **Status:** drafted 2026-10-18. Not yet reviewed. It changes the build recipe and the artifact
  set, so it is reviewed once more before it is built (constitution §5.6). It is build-class: it
  touches `scripts/`, `recipes/`, `downloads/SHA256SUMS` and the release workflow (§5.7). It
  carries one upstream patch (§4.1, to regex), so the review reads the patch and its facts sheet
  (spec 020, Decision 8).
- **Owner:** Clay Gendron
- **Kind:** the build recipe (one pin in `downloads/SHA256SUMS` and `scripts/00_download.sh`; a
  new step `scripts/steps/53_regex.sh`; `scripts/build.sh`, `scripts/steps/60_link.sh`,
  `scripts/steps/70_zip.sh`, `scripts/assemble_artifacts.py`), one recipe file (a forced-include
  header that names the module), one carried patch to regex with its upstream facts sheet,
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
     `scripts/wasi-cc` with `-O2 -ffile-prefix-map=$HERE=/wasi-python-build`, CPython's
     `Include` and the cross-build folder's `pyconfig.h`, and, for `_regex.c` only,
     `-include $HERE/recipes/regex_module_name.h` (Decision 4). regex's `setup.py` adds one
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

4. **The module's name: a recipe header, `recipes/regex_module_name.h`.** CPython gives a
   module loaded from a shared library the full dotted name through its package context, but
   gives a builtin none (`Python/importdl.c`, `_Py_ext_module_loader_info_init_for_builtin`,
   `.newcontext=NULL`, READ in the line's CPython 3.15.0). regex's module is single-phase and
   created as `"_regex"` (`PyModule_Create(&regex_module)`, `m_name = "_regex"`), so as a
   builtin its `__name__`, and every function's `__module__`, stay `_regex`, and pickling a
   compiled pattern fails with `PicklingError: … No module named '_regex'` (EXECUTED). The
   header includes `Python.h`, then redefines `PyModule_Create(def)` to set `def->m_name` to
   `"regex._regex"` before calling `PyModule_Create2`, which is what the package context does
   for the native extension. It is forced into `_regex.c` alone. EXECUTED: with it,
   `regex._regex.__name__` and `regex._regex.compile.__module__` are `regex._regex`, and
   `pickle.dumps(regex.compile(r"(?P<a>\w)+", regex.I), protocol=5)` gives the same 117 bytes as
   native (equal SHA-256).
   - **No other builtin has this problem today:** on the scratch binary, every one of the 61
     dotted builtins (numpy's, pandas', lxml's, regex's) imports under a `__name__` equal to its
     import name, once the header is in; without it, `regex._regex` is the one exception
     (EXECUTED). numpy, pandas and lxml use multi-phase initialisation, which takes the name
     from the import. A general v1.1 check holds this for every later package (Decision 7).

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
     It passes on today's set (numpy's and pandas' builtins) and fails on a build without
     Decision 4's header with exactly `[('regex._regex', '_regex')]` (EXECUTED on the scratch
     binaries). It is general: a later single-phase package is caught the same way.
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
   - `python.wasm`: +715,730 bytes (31,760,992 to 32,476,722 with regex alone), +2.25%
     (Pyodide's `.so` is 0.66 MB, INFERRED comparable). A growth outside 0.6 to 0.85 MB is a
     finding for the build review.
   - The snapshot: about the same bytes (not pre-imported).
   - The zip: +4 members (three modules and `METADATA`), about 90 KB deflated (88,301 bytes of
     compressed data for the three modules in the scratch zip).
   - Plain `-c pass`: one more inittab entry and four members, measured by the build (spec
     046's scratch build measured +447,981 fuel for both specifications' three builtins
     together).
   - `import regex` on the plain reactor: 480,810,420 fuel against 256,076,439 for `-c pass`
     with the same scratch zip (about +225 M). The build records it on both binaries.

9. **Ordering and shared files.** Build-class, so it overlaps no other build-class change
   (§5.7). It needs nothing from scipy; decision 48 places it after scipy, and question 82 asks
   whether lxml and regex may go earlier (decided until answered: after 038). It is small and
   independent of spec 046; either may build first, and the second rebases onto the first's step
   60, step 70, `00_download.sh`, `SHA256SUMS` and the oracle's `pyproject.toml` and `uv.lock`.
   It shares those files with 023, 033, 037 and 039 as well; each is rebased onto main as it is
   when the builder starts. Once spec 040 has landed, the x86_64 rebuild must give the same
   bytes too.

10. **Licence** (§4.12; approved by decision 43: Apache-2.0 AND CNRI-Python). `LICENSES/regex.txt`
    is the sdist's `LICENSE.txt` (the Apache License 2.0, headed by regex's statement that it
    derives from CPython's `re` module under CNRI's Python 1.6 licence). The CNRI licence's text
    is already in `LICENSES/cpython.txt` (CPython's `LICENSE`), which the README's licence line
    names. `MANIFEST` gains `regex 2026.9.29`, its pin, the header recipe and the patch by hash.

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
| `recipes/regex_module_name.h` | new: the module's dotted name (Decision 4) |
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
   and is seen failing on a build without the header); the five calls trapping on a build
   without the patch; the patched-tree check on a tree without the patch.
2. **The build.** From an empty `build/` in a clean clone, `scripts/build.sh` applies the patch
   with no offset, builds step 53, links `regex._regex` with no clash, and makes a set whose
   binaries pass the checks and match the golden. `MANIFEST` names the pin, the header and the
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

Not built.
