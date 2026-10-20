# Review of 041 — files read by path from the zip (the build)

- **Date:** 2026-10-19
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write, build or pre-review this
  specification. Each claim below is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `spec/041-files-read-by-path-from-the-zip` at `f2c351b` (the build `39cf425`, the
  landing notes `f2c351b`). It is the first **stacked build** (constitution §4.14, AGENTS.md rule 2,
  the owner, 2026-10-19), on spec 039's reviewed tip `dcd94ff`. I reviewed 041's own change only:
  `git diff dcd94ff..f2c351b` (28 files, +634 −325). I read:
  - the specification and its pre-build review with its confirmation and conditions C1 and C2;
  - every non-specification hunk: both patches, `make_stdlib_zip.py`, `70_zip.sh`,
    `assemble_artifacts.py`, `00_download.sh`, `downloads/SHA256SUMS`, `release.yml`,
    `pins.py`, `needs.py`, `jobs.py`, the new job and its golden, `test_v1_3_default_profile.py`,
    the two unit-test files, `known_gaps.toml`, `pandas.toml` and the two emptied lists;
  - the README, CHANGELOG and `context/upstream/` hunks;
  - the harness code the judge changes lean on: `upstream.stage`, `upstream.class_findings`,
    `tests/upstream/drive.py` (how pandas' `__path__` gains the stage), `guest._place`, and
    `scoreboard.FUEL_TOLERANCE`;
  - the builder's evidence under the worktree's `build/041/`.
- **Ran (EXECUTED, darwin-arm64, in the 041 worktree, against its own `build/artifacts/`).**
  Nothing committed, pushed, dispatched or edited in the tree. Outputs are beside this file.
  - `full-judge.log`: `uv run pytest -n 3`, started with no `lane.lock`. The record is
    `reviewer-latest.json`.
  - `zipcmp.py`: 039's zip against 041's, by name, bytes and order.
  - `probe_hardexit.py`: the `[snapshot]` growth line's program on both sets and both binaries,
    through the judge's driver. Its run folders were removed afterwards.
  - `shasum -c` of the set; `diff` of the two `MANIFEST`s; `cmp` of the two `python.wasm`s.
  - `ruff check` / `ruff format --check` on `src/` and `tests/`.
  - `dry-run-failed.log`: `gh run view 39345809724 --log-failed`.

## What holds

- **The judge reproduces the builder's record (EXECUTED, `full-judge.log`).** It ran in 954.91 s
  at `-n 3`, with another builder's judge and a reviewer's CPython re-run on the machine. The
  summary is the landing notes' line for line:

  ```
  wasi_python v1: 568/647 pass · 77 gap · 2 blocked · 0 fail   (unit suite 1583/1590, 7 skipped)
  ratchet vs b91e0eaa4e: lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 25 · grew 165 · more 2 · judge changed: …
  RED: 165 metric(s) grew
  2151 passed, 9 skipped, 77 xfailed in 954.91s (0:15:54)
  ```

  - `uv run python tests/harness/sameness.py build/041/latest-full.json reviewer-latest.json`
    exits 0 and prints nothing (`sameness.txt`). Every status, pass count, byte count, gap reason
    and fuel (within 0.01%) is the builder's.
  - The checks this specification adds or turns all pass in my record: the job check, the Styler
    and atlas checks on `plain` and `snapshot`, both emptied `styler-templates` classes,
    `test_source_tree_matches_its_tarball[networkx]` and `[pandas]`,
    `test_carried_patches_follow_the_rules`, `test_goldens_reproduce_under_the_pinned_oracle`, and
    051's `test_callbacks_have_the_types_cpython_calls`.
  - The two blocked checks are this worktree's (prior-art clones; three systems).
- **The artifact set is the one the notes name (EXECUTED).**
  - `shasum -a 256 -c SHA256SUMS` in `build/artifacts/` passes for every file. The file's own
    SHA-256 is `95b2f93a…f5ff`. 039's copy in `build/old-artifacts/` is `ada941bc…`, the same as
    `../wasi_python-039/build/artifacts/SHA256SUMS`.
  - `python.wasm` is `cmp`-equal to 039's.
  - `zipcmp.py`: 4,435 → 4,434 members. The only name removed is `networkx/conftest.pyc`; none
    is added. The only members whose bytes differ are `networkx/generators/atlas.pyc` and
    `pandas/io/formats/style_render.pyc`. The shared members keep their order. This is criterion
    2 exactly.
  - `diff` of the two `MANIFEST`s gives exactly Decision 8's lines: networkx's `pin` (sdist for
    wheel), two new `recipe` lines for the patches, the `recipe` lines of `00_download.sh`,
    `assemble_artifacts.py`, `make_stdlib_zip.py` and `70_zip.sh`, and `x-snapshot-zip`. The four
    script hashes equal `shasum` of the committed files, and the two patch hashes equal the
    patches' (`0b6b418b…ce7d`, `3b8b6d2d…5384`).
- **The patches are small, correct and recorded (READ; the judge's rules EXECUTED).**
  - pandas (1 file, +6 −1): `StylerRenderer` keeps `FileSystemLoader` when the templates folder
    is a directory, and otherwise uses `PackageLoader("pandas", "io/formats/templates")`. Every
    install where the Styler works today keeps today's loader. Only the failing case changes, so
    pandas#62123's fix for editable installs stands.
  - networkx (2 files, +16 −1): `_generate_graphs` opens the resource with its own
    `open("rb")` and hands the stream to `gzip.open`. That is `importlib.resources`' own API, so it
    works for a `Path`, a `zipfile.Path` and 035's reader. The added upstream test is correct: it
    consumes the generator inside the `with` that keeps the zip open. The zip never holds it.
  - **The upstream lines are what the projects ship.** In the guest, pandas' `__path__` is
    `[<zip>/pandas, /upstream/tests/pandas]` (`drive.py` appends the stage). jinja2's zipimporter
    branch takes the first location, so even in the upstream suites the product reads the zip's
    templates, not the staged copies (READ).
  - **Recorded as §4.1 asks.** Each is under `recipes/patches/<tree>/`, hashed in `MANIFEST`, named
    by path in the CHANGELOG, and has its facts sheet under `context/upstream/patches/`, moved by
    rename at 100% similarity. Each patch is a byte-for-byte rename of its `fix.patch`.
    `test_carried_patches_follow_the_rules` and both trees' `test_source_tree_matches_its_tarball`
    pass in my run. The release's zero-patch step passed in the dry run with 22 trees.
    `pins.SOURCE_PATTERNS` and `needs.SOURCE_COMPONENTS` both have 22 entries and the same names
    (EXECUTED).
- **The sdist route matches the wheel (READ, `build/041/criterion-2.txt`; EXECUTED for the
  zip).** The staged `networkx/` is the wheel's package but for `conftest.py` (skipped by `walk`)
  and the patched `atlas.py`. `METADATA` and `entry_points.txt` are byte-equal to 039's zip.
- **`--entry-points` does what Decision 5 says (READ).** `sdist_entry_points` names the member
  with `sdist_metadata`'s own folder. `check_entry_points` runs once every input is gathered
  (after `--file`), and stops in one line naming both files when the folder has no `METADATA`. A
  clash with a wheel's own file is stopped by `add`'s "comes from two inputs". F2 covers what the
  unit check does not reach.
- **The judge changes do not weaken the judge (READ; AGENTS rule 4).**
  - **The eight templates as `support`.** `upstream.stage` copies only tarball members
    (`allowed`), and `rule_errors` fails a `support` name that is not a member. So the staged
    files are pandas 3.0.6's own bytes, staged read-only where pandas' source tree has them, for
    `test_html.py`'s `env` fixture (`FileSystemLoader` on `../../../../io/formats/templates`) and
    `test_html_template_extends_options`. The product does not read them (above).
  - **`pandas-io-formats`' cap 82 G → 120 G.** A cap is a ceiling for a run, not a metric. Growth
    is still ratcheted at 0.01%. 120 G is 1.34× the measured 89.2 G (82 G was 1.40× main's
    58.6 G), and the family's caps sum to 2,557 G, under the 3,000 G budget that `rule_errors`
    enforces.
  - **The emptied classes.** `class_findings` returns no finding for an empty class. Any failure
    that matches it again is a finding, and with the gap removed it is red. The class keeps
    guarding, as `zip-code-names` does (spec 050, C1, written at the top of `pandas.toml`). F5 is
    a small point about its `match`.
  - **The unit check's spelling.** The departure is right. `Path("./x/PKG-INFO")` is
    `Path("x/PKG-INFO")`, so the spec's spelling pair cannot tell a path-string guard from the
    folder guard. `x/../x/PKG-INFO` can, and the builder's mutant fails on it
    (`build/041/seen-failing-unit.txt`).
  - **The synthetic pin set** in `test_artifact_rules.py` follows the pin it mirrors.
- **The two new gap checks are honest.** On both binaries, the Styler check asserts
  `type(StylerRenderer.loader).__name__ == "PackageLoader"`, which ties the golden's equal
  output to the patched branch. Without the patch, a `TemplateNotFound` at import is caught and
  recorded as a finding, not raised (READ; seen failing in `build/041/seen-failing-findings.txt`).
- **Spec 051's callback scan binds and passes.** `test_callbacks_have_the_types_cpython_calls`
  passes in my run. The patches change Python only.
- **Conditions.** C1 holds: question 80 is answered as recommended (`context/decisions.md`), and
  the notes say so. C2 is overridden by the stacked-build rule, a listed departure (1). It uses
  033's landed `sdist_metadata`, as C2 also asks.
- **ruff** is green on `src/` and `tests/` (EXECUTED). Under `scripts/`, the only error in a
  touched file is `make_stdlib_zip.py:12` E501, which predates this change.
- **The dry run (EXECUTED, `dry-run-failed.log`).** As the notes say, only the three
  `macos-15` shards are red. Each shows `0 fail` and `lost 0`, and its only red lines are
  `GREW` lines. The visible ones are 039's (the snapshot's bytes, `dotted_builtins`, tier A's
  start, `cpython-fs`, `numpy-lib`). Every rebuild, same-bytes, `verify`, Linux and Windows job
  passes, and so does the 22-tree zero-patch step.

## The departures, judged

1. **Built before 039 landed:** accepted. This is the owner's stacked-build rule. The delta review
   at rebase covers what moves.
2. **Classes emptied, not removed:** accepted. `pandas.toml`'s own rule (spec 050, C1) governs,
   and the judge's code is written for it.
3. **Templates staged beside the tests:** accepted. It is a judge change in the open, with its
   reason, and it weakens nothing (above).
4. **The cap 82 G → 120 G:** accepted (above).
5. **The unit check's spellings:** accepted (above).
6. **+29 bytes per member against Decision 8's table:** accepted. It is spec 051's guest-path
   `co_filename`, and the deltas are the table's (EXECUTED: the same two members change).
7. **`LICENSES/networkx.txt` header line:** accepted. The licence text is unchanged, and the header
   now names a tree file as pyyaml's and markupsafe's do.
8. **Counts 7 → 9 and 21 → 22, relative to 039's tip:** accepted. The lane re-counts on rebase.

## The two growth lines new against main, judged

`test_unbuffered_output_survives_a_hard_exit[snapshot]` (+1,623) and
`test_the_readmes_encoding_workaround_reads_what_iconv_cannot` (+2,073,959, +0.034%). Both run
on the snapshot binary. Each is within the band of the other 114 moves (snapshot checks −0.45% to
+0.42%, in both directions).

- **Neither program can reach a changed member (READ).** The first is
  `print('kept'); import os; os._exit(0)`. The second imports only `lxml.etree` and uses the
  stdlib's CJK codecs. Neither imports pandas or networkx, and the snapshot pre-imports no
  package. So the patched `style_render.pyc` and `atlas.pyc` cannot run in either program. The
  only inputs that differ are the zip's directory (one entry fewer) and the snapshot heap built
  from it.
- **Reproduced (EXECUTED, `probe_hardexit.py`).** On 039's set the hard-exit program costs
  186,706,318 (plain) and 1,212,377 (snapshot). On 041's it costs 186,686,764 and 1,214,000. The
  plain binary, which reads the directory at start, is 19,554 cheaper (one entry fewer, near the
  slope of 25,120 per member). The snapshot moves the other way, by an amount no code change can
  explain. That is layout, as the notes infer and as spec 091 records for numpy-core.
- **Verdict:** this is not a regression. Decision 8's "no accepted metric should grow beyond the
  judge's noise" is met in substance. The snapshot's layout sensitivity is the noise floor here,
  and it is deterministic per set. The `--accept-growth` text names both lines with that cause,
  which is the right handling. F4 asks for one clause.

## The accept texts, judged

- **`--accept-judge`** names every judge change in the diff:
  - the job and its golden (with `jobs.JOBS`);
  - the two checks widened, on both binaries, and their gaps removed;
  - the unit check;
  - the source-tree patterns (`pins` and `needs`);
  - the eleven files re-selected, the classes emptied and their gaps removed, the templates
    staged, the cap;
  - the synthetic pin set.

  It is complete for the diff as built. F1 adds one clause.
- **`--accept-growth`** separates 039's growth from 041's cleanly. It names only 041's own moves
  (`pandas-io-formats` +22.8 G and +975 passes, `pandas-frame` +0.69 G and +2 passes, the other
  upstream groups −0.09% to +0.11%, and the layout band). Its bounds match
  `build/041/grew-vs-039.txt` (EXECUTED: largest plain move +0.050% `symbolic`, largest snapshot
  move +0.421% `min-key`, upstream groups up to `numpy-others` +0.108%). 039's 163 lines are
  accepted by 039's own flags when it lands, so after the rebase the lane's ratchet (against main
  with 039 accepted) shows only 041's. Its numbers are this base's. After the rebase onto a main
  that carries 083 and 089 (driver changes), the lane restates them from its serial record, and
  the delta review checks the restated text.

## Findings, most severe first

### F1 (fix before landing): `tests/upstream/packages.toml` now gives a false reason for networkx

- **What (READ).** `[package.networkx]` says `kind = "later"`,
  `reason = "pinned as a wheel, which carries no tests; its sdist is to be pinned as data"`. 041
  pins networkx as its sdist, which carries its tests: the carried patch edits
  `networkx/generators/tests/test_atlas.py` in it. AGENTS.md's spec-063 rule binds this file:
  "says in `tests/upstream/packages.toml` why not yet". The stated "why" is now untrue, and the
  judge does not read the reason's content (`shards.py` only checks that one exists), so nothing
  catches it.
- **Fix.** One line, for example: `reason = "pinned as its sdist since spec 041, which carries its
  tests; staging and running them is spec 067's"`. Keep `kind = "later"` and the closer. It is a
  judge file, so add "networkx's packages.toml reason (now its sdist)" to `--accept-judge`. It
  can ride in the rebase commit.

### F2 (Low): the unit check never reaches `main`'s guard, and `origins` duplicates `entries`

- **What (READ).** `test_an_sdists_entry_points_go_beside_its_metadata` calls `sdist_metadata`,
  `sdist_entry_points` and `check_entry_points` directly. It never runs `main`. So a mutant that
  deletes `check_entry_points(origins, placed)` from `main`, or moves it before the `--metadata`
  loop, leaves the unit check green. Separately, `check_entry_points` reads only the keys of
  `origins`, which are exactly `entries`' keys (`add` sets both together). The new dict exists
  only to make departure 5's mutant "natural", and its values are never read.
- **Fix.** Add one `main()` case in the file's existing pattern
  (`test_the_zip_refuses_a_code_prefix_…` sets `sys.argv` and calls `make_stdlib_zip.main()`):
  `--lib <empty tmp> --entry-points x/PKG-INFO x/entry_points.txt out.zip` with no `--metadata`
  stops naming both files, and with `--metadata x/../x/PKG-INFO` it writes
  `some_pkg-1.0.dist-info/entry_points.txt`. Then pass `entries` (its keys) to
  `check_entry_points` and drop `origins`. Or keep `origins` and say in a comment why it exists.
  It is optional before landing, since the recipe change needs a rebuild only if `make_stdlib_zip.py`
  changes. If it is done, do it in the rebase, which rebuilds anyway.

### F3 (Low): the builder's measure folder leaves nine hard links on the worktree's set

- **What (EXECUTED).** At my start, `build/artifacts/python-stdlib.zip` had `nlink` 10. `find
  -inum` gives nine links under `build/041/measure-rlgqqr8a/run-*/lib/python315.zip`, left by
  `measure.py` through `guest._place`. My judge left none behind: the count was 10 again when it ended. On this base the guest sees `st_nlink`, and 081's build
  review found fuel flips above about 1,018 links. Ten is far below that, so neither the builder's
  record nor mine is affected (INFERRED from that threshold). But the brief asks for nlink 1, and
  on a base with 089's sealing such leftovers do not go away with `rm -rf`.
- **Fix.** Remove `build/041/measure-rlgqqr8a/` (its numbers are in `measure.json`) before
  anyone else judges on this set. The lane rebuilds in the main tree, so landing does not depend
  on it.

### F4 (note): the growth-line reason could say why it is layout

- The `--accept-growth` clause is accurate. It would be stronger with the one fact that decides
  it: "neither program imports pandas or networkx; plain −19,554 on the same program". Optional
  wording, no rebuild.

### F5 (note): an emptied class keeps a broad `match`

- `pandas-io-formats`' emptied `styler-templates` class still matches
  `'TemplateNotFound|Regex pattern did not match'`. A future, unrelated `pytest.raises(match=…)`
  mismatch in that group would be filed under this class, with a closer naming 041. It is still
  red (no gap), so the judge is not weakened. Only the message would mislead. The precedent
  (`zip-code-names`) also kept its text. No change is needed. If anyone touches it, narrowing the
  emptied class to `'TemplateNotFound'` is a judge change of its own.

### F6 (note): the facts sheets still say "When spec 041 is built, this file moves…"

- They moved unchanged, as Decision 6 ordered, and 046's and 047's sheets read the same way
  (READ). A tense sweep across the four sheets is a `context/`-only follow-up, if the owner wants
  one.

### F7 (note): criterion 6 is met only after the lane accepts

- The branch dry run cannot be green: CI ratchets against the accepted progress in the commit,
  which does not yet hold 039's moves. Criterion 6 ("a release dry run passes every job") is
  met by the lane's dry run on the accepted commit. Record its run number in the landing notes,
  as 065's were.

## Verdict

**Lands once F1** is fixed (one line in a judge file, named in `--accept-judge`; it can ride in
the rebase onto main after 039). F2 and F3 are Low. Fix them in the rebase if convenient. F4 to F7
are notes. The build is correct. Both patches are minimal, recorded and right. The zip changes
in exactly the three members the specification predicts. The judge is not weakened. The two
growth lines new against main are snapshot layout, since neither program can reach a changed
member.

One line: 041 is built as specified and its judge reproduces; fix packages.toml's networkx reason,
then it lands after 039 with a delta review.
