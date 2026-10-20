# Build review of 039 — tier A: the pure-Python packages, 2026-10-19

- **Reviewer:** a fresh agent. I wrote none of 039, neither its specification nor its build, and
  I did not review it before build (AGENTS.md rule 8; constitution §5.6).
- **Under review:** `spec/039-tier-a-packages` at `45c70cb`, on main `e49e515`, in the worktree
  `../wasi_python-039`.
  - Commits: `3195e02` (the build), `7d1a705` (pandas' own Styler tests as known failures) and
    `45c70cb` (landing notes).
  - The specification: its Decisions, criteria, the eight amendments at build, and the landing
    notes. The pre-build review: `039-tier-a-packages-spec-2026-10-17.md`.
  - The builder's evidence: the worktree's `build/evidence/`.
- **How I ran it:** in the worktree, against its own `build/artifacts/` (`SHA256SUMS`
  `ada941bc…`), and `build/old-artifacts/` (main's set). I checked that
  `build/old-artifacts/SHA256SUMS` is the main tree's (`c9dcb5b8…`). My probes are in the
  scratch folder's `probes/`, and their run folders are deleted. I wrote nothing in any git tree;
  `git status` in the worktree is clean. The judge runs rewrote the worktree's ignored
  `build/progress/latest.json`. It now holds my fast-tier record. My full record is in the
  scratch folder (below). One slip: I once ran a bare `python3 -c "print(1)"`, a no-op, by
  mistake (not `uv run`). Nothing depended on it.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED** (reasoned, not run).

## Short version

It is built as specified, and the eight amendments are honest.
- I re-ran the full judge with `-n 3`. The verdict is the builder's, check for check: 553/574,
  0 fail, lost 0, gained 17, grew 158, and one fewer pass. `sameness.py` between the builder's
  record and mine finds no difference.
- The fallen pass (`pandas-frame`, 10,852 → 10,851) is what jinja2's arrival does. It hides no
  pandas regression. But it points at a change users will see that the README does not name
  (F1).
- All 31 pins equal PyPI's digests and URLs. All 30 licences are named in §4.12. No patch was
  added.
- In the zip, 2,014 members are added, none removed, and one changes: `ctypes/util.pyc`, by
  design.

**Verdict: lands once the README's Styler line says that `hasattr(df, "style")`,
`getattr(df, "style", None)` and `inspect.getmembers(df)` now raise `TemplateNotFound` (F1).**
That is a docs-only change. The lane's own steps are listed at the end.

## Findings, by severity

### F1 (minor; the condition). `hasattr(df, "style")` and `inspect.getmembers(df)` now raise. EXECUTED

On main's set, pandas' `.style` accessor raises `AttributeError: The '.style' accessor requires
jinja2`. With jinja2 in the zip, it raises jinja2's `TemplateNotFound` instead. That is a
`LookupError`, not an `AttributeError`, so Python's probing idioms stop swallowing it
(`probes/getmembers.py`, `probes/hasattr.py`, plain and snapshot):

| call | main | 039 |
|---|---|---|
| `inspect.getmembers(pd.DataFrame())` | ok | `TemplateNotFound: 'html.tpl' not found …` |
| `hasattr(df, "style")` | `False` | `TemplateNotFound` |
| `getattr(df, "style", None)` | `None` | `TemplateNotFound` |
| `"style" in dir(df)` | `True` | `True` |

This is exactly why pandas' `test_inspect_getmembers` fell (finding A2 below). Code that probes
for the Styler, or walks a frame's members, worked on main and fails here.

The README's gap line names only `df.style` and `df.to_latex()`. Decision 9 and the Intent say
the README states first where the sandbox says no. **Fix:** one sentence in the README's
"Two known gaps" bullet, plus the CHANGELOG's line: until spec 041, `hasattr(df, "style")`,
`getattr(df, "style", default)` and `inspect.getmembers(df)` raise `TemplateNotFound` too. No
check is needed. 041 restores the old behaviour, and pandas' own test already holds it (class
`styler-templates`).

### F2 (minor; for the lane). Nothing brings the eleven set-aside Styler files back when 041 lands. READ

`tests/upstream/pandas.toml` gains a `[[not_selected]]` entry for eleven files under
`pandas/tests/io/formats/style/`, closing with 041.
- The harness turns them into `--ignore` (`upstream.group_spec`).
- Its rules check only that each file is a tarball member and that its closer exists
  (`upstream.rule_errors`). Nothing fails when the files would collect again.
- The two `styler-templates` classes and the four gaps *do* force their own removal. A class that
  loses members prints `-id` findings, and a gap that passes is reported.
- Spec 041 is confirmed for build, but its text names none of these: the `not_selected` entry,
  the two classes, or the pass it gives back.

**Fix (the lane, at landing):** one line in 041, or in the roadmap's 041 entry. It should say
that 041 re-selects the eleven files, removes the two classes and their lists, and expects
`pandas-frame` back at 10,852 passes. This does not block the landing.

### F3 (informational). Code from data runs in the guest through four tier A calls; the sandbox contains it. EXECUTED

`probes/security.py` ran on the branch's snapshot:
- `yaml.unsafe_load("!!python/object/apply:os.getcwd []")` returns `'/'`.
- `sympy.sympify("__import__('os').getcwd()")` returns `'/'`.
- A plain `jinja2.Environment` renders `''.__class__.__mro__[1].__subclasses__()`.
- `yaml.safe_load` and `yaml.full_load` refuse the tag. `jinja2.sandbox.SandboxedEnvironment`
  raises `SecurityError`, as natively.

None of this reaches past the guest. It is the same code an agent could already run. But an
embedder who passes *untrusted data* (rather than untrusted code) to these calls should know
that it executes, with the call's grants. The README makes no sandboxing claim for jinja2 or
pyyaml, so nothing it says is wrong.

**Optional:** one line under "The other edges": `yaml.unsafe_load`, `sympify` on strings,
non-sandboxed jinja2 templates and `pickle`/`cloudpickle`/`joblib.load` run code from their
input inside the guest; use `safe_load`, `SandboxedEnvironment` and trusted pickles.

The rest of the security sweep found nothing:
- `ctypes.CDLL(None)` still raises `OSError: ctypes is unavailable on wasm32-wasi`.
  `dllist()` answers `[]` and loads nothing.
- `joblib.Parallel` with `n_jobs=-1`, `backend="loky"` and `backend="threading"` each return the
  serial result, with no process and no trap.
- `pypdf.PdfReader("http://…")` is a missing file. Nothing fetches.
- `defusedxml` refuses an entity-expansion document.
- openpyxl runs with `DEFUSEDXML = True` (and `LXML = True`), so it parses `.xlsx` XML through
  defusedxml.
- The judge's sealing checks (no network, only its root, no processes) all pass in my run.

### F4 (informational). The upstream groups' growth above Decision 13's metadata row has a measured cause. EXECUTED + INFERRED

The growth account labels the cause INFERRED. Six upstream groups grew by +0.23 G to +0.64 G
(`numpy-others`, `pandas-reshape`, `-libs`, `-internals`, `-tslibs` are past the +72.5 M row,
inside the per-read row's 0.75 G). I measured one scan on the snapshot, main against 039
(`probes/metascan.py`):

| on the snapshot, beyond `import importlib.metadata` | main | 039 | delta |
|---|---|---|---|
| `entry_points(group="pytest11")` | 321,136,198 | 525,761,594 | +204,625,396 |
| `[d.metadata["Name"] for d in distributions()]` | 318,560,622 | 517,318,577 | +198,757,955 |
| `[d.entry_points for d in distributions()]` | 16,845,234 | 32,218,491 | +15,373,257 |

So each `entry_points(group=…)` call costs about +205 M more. It reads every distribution's
`METADATA` for its name. One to three such scans per pytest session (pytest, pluggy and
hypothesis each look up their groups) give the +0.23 G to +0.64 G seen (INFERRED for the count).
The cause is sound, and the account could cite this table.

### F5 (informational). Spec 035's check 6, re-based: honest, with thin headroom per member. EXECUTED + READ

- The miss on the snapshot measured 26,653,265 fuel in my run. That is past the old 20 M and
  inside the new bound, 36,062,000 = 20 M + 6,000 × (4,435 − 1,758).
- The formula is Decision 13's proposed text, and the Design table lists the file. So it is in
  the specification, not an edit outside it.
- Two notes for 035's text when the lane writes it in:
  - The measured per-member growth of this miss is 5,683, above the 4,844 expected and 5% under
    the bound's 6,000. Most of the bound's slack is the old fixed part (9.4 M measured against
    20 M).
  - The check holds one sum. Decision 13's "guards the fixed part and the per-member part
    separately" is true only together with check 6's plain slope bound, which is the separate
    guard.

## The owner's eight questions

1. **Amendment 3, the GB18030 check. A faithful update, not a weakening.** READ + EXECUTED.
   - Spec 046's Decision 14 says whichever of 039 and 046 lands second updates the `read_html`
     line. 039 is second.
   - The check's property, "never silently wrong", is unchanged. Its assertion is as exact as
     before: one named exception type, `UnicodeDecodeError` for `ImportError`.
   - pandas tries its flavors in order only on `ValueError` (lxml finds no table), then bs4.
     bs4 reads the file as UTF-8 and raises.
   - The neighbouring assertions all still pass in my run: the silent cut-off case pinned as
     documented, and `encoding="gb18030"` raising `LookupError`.
   - Its fuel growth (+0.91 G plain, +0.85 G snapshot) fits the bs4 and html5lib imports, which
     the builder measured at 1.28 G on the snapshot.
2. **Amendment 4 and the fallen pass. A measured consequence, honestly recorded; no hidden
   regression.** EXECUTED.
   - I ran `test_inspect_getmembers`'s body alone on both sets (F1's table). On main it passes
     because `.style` raises `AttributeError`, which `inspect.getmembers` skips. On 039 it raises
     `TemplateNotFound`.
   - The eleven files all `importorskip("jinja2")` at module top (READ), so on main they gave no
     passes. Setting them aside loses nothing that was counted, and it keeps the rest of
     `pandas-io-formats` running instead of the whole group stopping at collection.
   - The `pandas-io-formats` class's `match` includes `Regex pattern did not match`. That is
     broad, but members are listed by node id and digested (221), so nothing new can hide in it.
   - The +20 `pandas-io-formats` passes are stated separately. They do not pay for the fallen
     one (rule 5).
   - `--accept-fewer-passes` is justified, with 041 as the restorer. F1 is the user-facing side
     of it, and F2 is the bookkeeping 041 needs.
3. **Amendment 6, `ctypes/util.pyc`. Faithful.** EXECUTED (`probes/zipdiff.py`).
   - 2,421 → 4,435 members: 2,014 added, 0 removed.
   - The only shared member that differs is `ctypes/util.pyc`. Its source diff is Decision 5's
     `dllist` and nothing else.
   - Criterion 2's "no existing member changes" overlooked Decision 5. The amendment says so.
   - The builder's own seen-failing run with main's `util.pyc` in the built zip
     (`no-dllist-set/`) shows the change is load-bearing.
4. **Amendment 7 and check 6's bound.** See F5. The formula is the specification's own, and it
   is measured on today's snapshot (spec 069 removed the pre-imports the review's rows had).
   The snapshot rows came in under their caps: +4,719,693 on `pass` (2,343 a member, cap 3,500)
   and +729,607 bytes (362 a member, cap 1,000).
5. **The 158 growth rows. Each has a cause.** READ + EXECUTED.
   - 120 plain rows, 39 snapshot rows, and the zip's and the snapshot's bytes. Most plain rows
     sit at +50.6 M to +60.6 M, inside +60.4 M + 0.2%.
   - Every row past a cap is named in the landing notes with its cause. I checked the largest:
     - **`pandas-io-formats` +7.73 G:** the Styler tests that now run (221 class members and
       20 more passes). READ: the class list and `pandas.toml`.
     - **`test_resources_read_as_zipfile_reads_them` +4.32 G / +4.26 G:** its guest program
       lists every `tzdata/` and `pandas/` folder through `zipfile.Path.iterdir`, each a walk of
       the whole name list. Its cost is folders × members, and members grew 1.83×, so +69% to
       +71% is the expected shape. READ.
     - **The fast reader's `padded`, `small`, `snapshot` cases and the re-read after
       `invalidate_caches`:** zips built from the artifact zip, by design. READ.
     - **The upstream groups:** F4. EXECUTED.
     - **033's metadata check +444 M:** about 30 × 15 M, under its 0.75 G row.
   - The zip's bytes are +16,529,166, under the +17.0 MB cap. The plain binary is
     `cmp`-identical to main's (EXECUTED).
6. **The 063 rules.** READ + EXECUTED.
   - All thirty are in `tests/upstream/packages.toml` as `later`, with `closes_with = "spec 067"`.
   - The 28 wheels say "pinned as a wheel, which carries no tests". pyyaml and markupsafe say
     their sdist is pinned and the zip takes only the pure package. True: their sdists hold
     tests, 601 and 8 members under `tests/`.
   - 067 is reserved in the roadmap.
   - `test_every_package_names_its_own_suite` passes in my run. The new check file is in the
     `own-guest` shard.
7. **Licences, pins, patches.** EXECUTED + READ.
   - All 31 `SHA256SUMS` lines equal PyPI's published SHA-256 for that exact file, and each
     `get` URL is PyPI's URL for it. None is yanked (`probes/pypi.py`, PyPI's JSON API).
   - `shasum -c` of the 31 against `downloads/` is clean.
   - All thirty are named in constitution §4.12's question-43 list, with tqdm as
     MPL-2.0 AND MIT. PyPI's licence fields agree.
   - `LICENSES/` holds a notice for each of the thirty.
   - `tqdm.txt` has its three parts, and `tqdm-4.70.1-source.whl` is the pin's bytes.
     `sympy.txt` carries the nested latex2sympy notice.
   - No file was added under `recipes/patches/`.
   - The two sdists pass `test_source_tree_matches_its_tarball`, with 21 trees passing locally.
     The release's count is 21.
8. **Security.** F3. Nothing in tier A reaches outside the grants, opens a network connection,
   spawns a process or loads native code. The four code-from-data calls run inside the guest.

## Executed

- **The full judge, `uv run pytest -n 3`,** at `45c70cb` on the branch's set (`full-judge.txt`;
  record `latest-full-reviewer.json`, SHA-256 `23a0a8e8…`), 15 min 11 s on a loaded machine:

  ```
  wasi_python v1: 553/574 pass · 19 gap · 2 blocked · 0 fail   (unit suite 1500/1507, 7 skipped)
  ratchet vs 9a446e03f6: lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 17 · grew 158 · fewer 1 · more 1 · judge changed: … and 32 more
  FEWER tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pandas-frame]: passes 10852 -> 10851
  RED: 1 pass count(s) fell (say --accept-fewer-passes); 158 metric(s) grew
  2053 passed, 9 skipped, 19 xfailed in 910.78s (0:15:10)
  ```

  The two blocked checks are the worktree's (prior-art clones; the three systems). The four new
  gaps print exactly their `known_gaps.toml` digests (`2cf3dc27c61a`, `e6c0905e9cce`,
  `f89301d2f31f`, `cba9b5f7c560`).
- **Sameness:** `uv run python tests/harness/sameness.py build/evidence/latest-full.json
  <mine>` prints nothing and exits 0.
- **The fast tier, `-m "not slow" -n 3`** (`fast-judge.txt`, record
  `latest-fast-reviewer.json`): 509/574, 3 gap, 2 blocked, 0 fail, 60 deselected; lost 0,
  grew 131. 2009 passed in 9 min 2 s.
- `ruff check` and `ruff format --check` on `src/` and `tests/`: clean.
- **Probes** (`probes/`): `getmembers.py` and `hasattr.py` (F1, A2), `zipdiff.py` (A3),
  `pypi.py` (A7), `metascan.py` (F4), `security.py` (F3).

## What the lane must do

1. **Rebase** onto whichever of 037 and 043 lands first. Take both sides of step 70,
   `00_download.sh`, `SHA256SUMS`, `assemble_artifacts.py`, `paths`, the metadata set, the
   oracle's `pyproject.toml` and a re-lock, `packages.toml`, `needs.SOURCE_COMPONENTS` and the
   release's tree count (21 plus theirs). Re-derive Decision 13's caps from the members really
   added. Rebuild in the main tree. A delta review follows if recipe hunks or numbers move.
2. **The release dry run** on the reviewed commit: `rebuild`, `same-bytes`, and the zero-patch
   job at 21 trees (or 21 plus the other spec's trees after a rebase), with every job on all
   three systems. This is criterion 3 and criterion 6. Its run number goes in the landing notes.
   Windows runs only there.
3. **Judge serially** on the exact commit. Record `sameness.py` between my `-n 3` record
   (`latest-full-reviewer.json`) and the lane's serial one.
4. **Accept** with three flags, each with its reason:
   - `--accept-judge`: the new checks, jobs and goldens; the lists; the moved helper; check 6
     re-based; amendments 3 and 4.
   - `--accept-growth`: the account, with F4's table.
   - **`--accept-fewer-passes`:** `pandas-frame` 10,852 → 10,851, `test_inspect_getmembers`
     meeting the Styler gap; 041 restores it. This is the lane's decision; the reason is sound.
5. **Write** Decision 13's text into 035's check 6 (with F5's two notes if wanted), and the
   F2 line into 041 or the roadmap.
6. **F1's README sentence** first: the condition.

**One line:** tier A is built as specified, with honest amendments and measured growth, and it
lands once the README says that probing `df.style` (by `hasattr`, `getattr` or
`inspect.getmembers`) now raises.

## Addendum, 2026-10-19: the two judge fixes in `7fc8b12` (after dry run 39264473516)

The lane asked whether either fix weakens a check (rule 4). It is `7fc8b12` on the rebased
`0dd1ddd`. The set is unchanged (`SHA256SUMS` `ada941bc…`).

**1. `tier_a_notice_errors` reads the set alone. As strong as before, and in one place stronger.**
READ + EXECUTED.
- **The chain is unbroken.** `test_manifest_pins_match_the_pin_list` requires every MANIFEST
  `pin` line to equal its line in `downloads/SHA256SUMS` (`paths.manifest_pin_errors`). That
  file is tracked in git, so it is in every shard, and the check runs in the release. So:
  - carried wheel's SHA-256 = MANIFEST's pin = the repository's pin;
  - MPL part's SHA-256 = MANIFEST's spdx pin = the repository's pin.
  These are the same equalities the old rule got by reading `downloads/`, through one more
  checked link.
- **The LICENCE** is now read from the carried wheel. Its hash is the pin's, so these are the
  same bytes as the downloaded wheel's.
- **The MPL text is stronger.** It used to be a substring anywhere in the notice. Now it is one
  whole part, hashed against the pin. `notice_parts` undoes step 90's `notice()` exactly when
  the data ends in a newline. The pinned MPL text does (READ, `od`). If it did not, the rule
  would fail falsely, not pass falsely.
- **The source part** now looks only inside the part labelled `tqdm source`, not everything
  after its header. That is slightly stricter.
- **Sympy's nested notice** is now compared with the zip's member rather than the pinned
  wheel's. This shifts the referent. It does not weaken the check:
  - The zip's member is what ships. It is tied to the pin by criterion 2 (every `METADATA` and
    member from its pinned wheel) and by same-bytes.
  - The rule also now fails if the zip lacks the file.
- **Nothing in the rule reads `downloads/` any more** (READ, `grep`). Checking that downloads
  match their pins is the job of other checks, as it was before.
- **The unit self-test** keeps the earlier mutants and adds one: the MPL text one byte changed.
  It now builds its synthetic set with no `downloads/`.

**2. The `utilities` job caches a named function. Not a weakening.** READ + EXECUTED (golden),
INFERRED (Windows).
- What it exercises is the same: `joblib.Memory.cache`, called twice, with one cached result.
- `utilities.expected` is unchanged (no diff between `45c70cb` and `7fc8b12`), so the golden
  still equals native.
- The README line about `<lambda>` on Windows hosts is a fair fact for embedders. Only the
  dry run proves the Windows side.

**Executed at `7fc8b12`** (`addendum-run.txt`), on the branch's set:
- `test_tqdm_notice_carries_the_mpl_and_its_source` (the guest check), the unit self-test of the
  same name, `test_manifest_pins_match_the_pin_list` and `test_utilities_job_matches_native`:
  4 passed.

**Verdict: lands**, given F1 and F2 answered in `8d9f082` (I did not re-review that commit
here), the lane's steps above, and a green re-run of the release dry run on the exact commit,
Windows included.

## Addendum 2, 2026-10-19: 065's CPython groups on 039's set (rebased tip `dcd94ff`)

**The growth is measured: cpython-fs makes exactly twelve full distribution scans.** EXECUTED.
- I ran one `cpython-fs` session on the branch's set (`probes/count_scans.py` →
  `count-fs.txt`). It staged `/cpython` as the judge does, with a counter prepended to the staged
  copy of the driver only.
  - It counted every `Distribution.discover`, every `METADATA` read from the zip, and every
    `pkgutil.iter_modules` and `walk_packages` call.
  - Every one came from `test_importlib`: 95 discovers, and 528 `METADATA` reads from the zip.
    360 of the reads are tier A's, which is 12 × 30. So it makes exactly twelve full scans.
  - It made no `iter_modules` or `walk_packages` call that the counter saw. Calls through a
    fresh copy of a module would escape it, so these counts are a floor.
- **The arithmetic closes.** 12 × 198.6 M = 2.38 G of the +2.56 G (59.84 G → 62.39 G). The
  rest, about 0.17 G, fits the 95 discovers walking a zip with 2,014 more names.
- The session exited 0. With the counter, its fuel was 62.52 G (+0.13 G of counting).
- The other four groups' +0.13% to +0.67% are the same kind of cost and far smaller. I did not
  count them.
- `--accept-growth` should say "twelve scans, counted", not "about a dozen, inferred".

**Verdict: lands.**
