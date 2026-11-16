# Review of 191 — pytz, rich, Faker and folium

- **Date:** 2026-11-15
- **Reviewer:** an agent (Claude), a fresh sub-agent of https://claude.ai/code/session_01BD1pVHiZoxnwRv6JCqJKeC; not the author
- **Reviewed:** the specification as drafted, `context/specifications/191-pytz-rich-faker-and-folium.md`, at `3d8fe05f` on `spec/191-pure-python-packages` (off `dev` at `4bed5d73`)
- **Run:** none: a specification review
- **Re-ran:** the checks under Confirmed and the findings, each labelled; with this file written, `uv run pytest tests/lint -q -p no:cacheprovider` → 14 passed (EXECUTED).
- **Time box:** 45 minutes (build-class); overrun by the licence sweep of Findings 1 and 7.

Labels: EXECUTED, I ran it; READ, I read the file or page cited; INFERRED, my reasoning. Downloads were matched to PyPI's SHA-256 in scratch and read, never run. No `gh` call, no dispatch, no GitHub archive fetched; nothing but this file changed.

Confirmed:

- **The pins (EXECUTED).** Each of the nine is PyPI's newest release, with no vulnerability, and its file, size and SHA-256 are Decision 1's; the 18 downloads pass `sha256sum -c`. Every wheel is `Root-Is-Purelib: true`, `none-any`, with no `.so`, `.pyd` or `.c`.
- **The dependencies (EXECUTED, `requires_dist`).** As Decision 1 says: rich needs markdown-it-py and Pygments, markdown-it-py needs mdurl, folium needs branca, jinja2, numpy, requests and xyzservices, branca needs jinja2, Faker needs tzdata on Windows only. Pygments 2.21.0 and pytz 2026.6 have the kit's digests (READ, `tests/upstream/kit.txt:5`, `kit-extra.txt:10`).
- **The licences (EXECUTED, PyPI).** As Decision 1's table says, and each wheel's licence files as Decision 6 says; but see Finding 1.
- **folium and branca (READ, the sdists).** `import requests` is at `folium/features.py:24`, its one use at `:783`. The sdist and wheel differ as Decision 5 says. The templates are reached by CDN URL only. branca's five opens are at `colormap.py:21-25` and `utilities.py:141-148`.
- **requests (EXECUTED, its wheel).** `requests/utils.py:82` calls `certs.where()` at import, through `as_file` (`certifi/core.py:40`).
- **pytz (READ, its wheel).** `open_resource` falls back to `importlib.resources` (`__init__.py:95-106`); 597 names are checked (`:538`, `:1136-1139`) against 604 zone files. pandas 3.1.0's sdist (EXECUTED: it matches `downloads/SHA256SUMS:2`) imports pytz at `_libs/tslibs/timezones.pyx:28`.
- **rich (READ).** `Live(auto_refresh=True)` starts `_RefreshThread` (`live.py:63`, `:142-143`). `Progress.track` takes the thread-free branch when `auto_refresh` is off (`progress.py:1224-1235`).
- **Faker's plugin (READ).** It is registered under `pytest11`, and its session fixture `_session_faker` is `autouse`, so every session that loads it builds a Faker: Decision 7 is needed.
- **What waits (EXECUTED, PyPI).** jsonschema and referencing require rpds-py; rpds-py, python-calamine and wordcloud publish no pure and no WASI wheel; altair requires jsonschema. The reasons hold, with the counts in Finding 11.
- **The tags (EXECUTED, `git ls-remote`).** The four tags resolve to Decision 1's ids.
- **The zip (EXECUTED).** Compiled with Python 3.13, deflated at level 9, METADATA kept as step 70 keeps it: 1,956 members, 6.07 MB, within 2% of the spec's 1,949 and 5.97 MB. pytz alone is 498 KB, under its 0.6 MB line.
- **The smoke total (EXECUTED, `upstream.load_all()`).** The 53 test-source smoke groups record 1,183.07 G; the smallest is 10.5 G and the median 18.0 G, so nine new groups add about 95 to 162 G, as Decision 8 says.

## Acceptance criteria against evidence
1. Licences approved first — can be judged, but the list put to the owner is wrong (Findings 1 and 7).
2. Pins match — can be judged. The 14 PyPI pins match (EXECUTED). The four tag archives are trusted at first fetch, as cycler's are (`downloads/SHA256SUMS:171-180`).
3. pytz's numbers, or the cut — can be judged. Built as scoped, though, two existing checks go red (Finding 3).
4. The zip's names — can be judged from the build shard.
5. Golden jobs — two jobs as written are not reproducible (Finding 8).
6. Checks seen failing first — can be judged.
7. Families in their tiers — the release tier is not run before the merge (Finding 6). "No family but Faker's imports Faker" has nothing that shows it (Finding 10).
8. Bytes and fuel recorded — can be judged.
9. Green — not met as scoped (Findings 3 and 4).

## Findings, most severe first
1. **High: Faker is not MIT alone, and Owner's choice 1 asks for MIT** (Decision 6; Owner's choices, 1). `faker/decode/codes.py`, which `providers/internet/__init__.py:4` imports at import, equals text-unidecode 1.3's `data.bin` entry for entry: 65,536 of 65,536 (EXECUTED, its pinned wheel). Faker's CHANGELOG at 12.0.0 reads "Remove dependency from text-unidecode" (READ). text-unidecode is licensed "Artistic License, or GPL or GPLv2+" (READ, PyPI and its DESCRIPTION.rst). `providers/geo/__init__.py:13` says its coordinates are "extracted from geonames.org, under the Creative Commons Attribution 3.0 License". `address/it_IT/__init__.py:11` is "Converted from" GeoNames. `address/mk_MK/__init__.py:84` takes roads from OpenStreetMap (ODbL). `person/de_LU/__init__.py:364` and others cite datasets whose terms the wheel does not state (READ). Failure: the owner approves "Faker (MIT, with randomcolor-py's MIT)", and the release ships an Artistic-or-GPL table and CC BY data with no notice, against §4.12. Fix: "Decision 6 lists for Faker: text-unidecode's table (Artistic-1.0-Perl OR GPL-2.0-or-later; offered under Artistic-1.0-Perl, its text pinned as a file), GeoNames (CC BY 3.0, attributed), the OpenStreetMap extract (ODbL, attributed), and each `Source:` dataset with its terms. Each is asked in Owner's choice 1. If the owner declines one, Faker waits."

2. **High: a package snapshot freezes Faker's shared generator** (Decision 4; Design, `snapshot-packages.txt`'s `faker: faker`). `faker/generator.py:12` makes `random = random_module.Random()` at import. Every unseeded `Faker()` draws from it (`:68-75`). `make_package_snapshot` imports every package line (`src/wasi_python/_snapshot_make.py:179`). The per-call `_refresh` reseeds only the generators it names: `random`, `numpy.random`, sympy, more-itertools and scikit-learn's grower (`recipes/reactor_bootstrap.py:90-110`). Failure: two calls from one image both print the same `Faker().name()`. Natively, two processes differ (INFERRED from the code). Fix: "`_refresh` seeds `faker.generator.random` when `faker.generator` is loaded. The module and its reason go into `test_the_refresh_reseeds_what_the_image_froze` (`tests/checks/test_v1_4_prepare.py:182`), seen failing first. Decision 4 says so."

3. **Medium: two checks pin pytz's absence, and Scope leaves both out.** `test_import_pandas_loads_exactly_its_packages` asserts that `import pandas` loads exactly numpy, dateutil and pandas (`tests/checks/test_v1_3_the_zips_directory.py:535`, `:554-563`). `test_the_import_path_comes_after_the_runtime` counts two `HIT pytz` from a stub pytz on the import path (`tests/checks/test_v1_4_embedding.py:4768-4774`). Failure: once pytz ships, pandas loads `pytz` and the stub is never reached, so both are red on the pytz pull request (INFERRED). Fix: "Scope adds both as a judge change under `[claim.judge]`. `PANDAS_FOLDERS` gains `pytz`, with the reason. The embedding check's lacked name becomes one pandas' import still looks for and the set lacks, counted by a run before the edit."

4. **Medium: pytz's cost to the pandas groups is a normal-tier cost on the pull request, and Decision 2 puts it at the release tier.** pandas' conftest calls `pytz.timezone("US/Pacific")` at collection in every pandas session. It grows `TIMEZONES` from 15 to 20 and `_UTCS` from 4 to 5 (READ, `pandas/conftest.py:83`, `:1176-1203`, `:1226-1227`). `tests/tslibs/test_timezones.py:58-60` loads all 433 common zones. The pandas groups are normal tier with fixed caps (`tests/upstream/pandas.toml:33-63`), and a pull request runs them when the build changes (`AGENTS.md`, step 6). rich likewise un-skips tests in the test-source smoke groups. Failure: new cases, new fuel and any new guest failure appear unclaimed, or as an unlisted failure, in the pytz pull request's own run. Fix: "Decision 2 names the pandas groups and the smoke groups that gain cases. The pytz and rich pull requests claim their `passes` and `grows`, classify any new failure, and raise no cap except by the 1.5 rule, claimed."

5. **Medium: the smoke bound is raised before it is measured** (Owner's choices, 4). Precedent sized the last raise from measurement: 1 T to 1.2 T for five cairo families that measured 201.3 G (`tests/harness/packages.py:1491-1497`). Here 1.4 T leaves 217 G against an estimated 95 to 162 G. Failure: 55 to 120 G of headroom is tied to no group, and later smoke growth fits under it without notice. A raise sized to new groups is a justified re-budget. A fixed figure chosen ahead is partly a weakening. Fix: "Each pull request raises `SMOKE_TOTAL_BOUND` to its measured sum plus 17 G, rounded up to 10 G, under `[claim.judge]`, its comment naming its families. No existing group's `measured` rises to use the room."

6. **Medium: the nine release groups are first judged after the merge.** A pull request runs the normal tier, even with `citest:full` (READ, `release/ci_plan.py:514-523`, `:541-545`). This is 188's Medium 2 again. Failure: a release group past its cap, or a wrong class, reaches `dev` green and stops the tag at the release pull request. Fix: "each pull request is judged by `release.yml` dispatched on its branch with `release-tier: true`, after the owner's yes, as 188 does. The landing notes record that run's id, fuel, passes and classes."

7. **Medium: notices beyond Faker are missing, and the sweep cannot find them** (Decision 6). rich's `_unicode_data/*.py` say "Data from wcwidth project" (MIT, READ `unicode17-0-0.py:2`). `rich/filesize.py:1` is "Borrowed from" pyfilesystem2. branca's `_schemes.json` carries ColorBrewer's schemes (`utilities.py:106-109`), whose Apache-2.0 attribution was approved for plotly's copy, beside viridis (READ). Failure: the sweep `copyright|licen[cs]e` misses notices worded "Data from", "Borrowed from" or "Source:", so they ship without notices. Fix: "the sweep adds `source:|data from|taken from|borrowed from|adapted from|converted from|port of|based on`. Decision 6 adds wcwidth (MIT) to rich and ColorBrewer (Apache-2.0) with viridis to branca."

8. **Low: two jobs would not repeat** (Decision 9). `pydict`'s default types include `date_time` (`faker/providers/python/__init__.py:25-37`), which ends at now (`date_time/__init__.py:1886-1900`). The oracle passes its own environment through (`tests/harness/jobs.py:251`), where `NO_COLOR` or `FORCE_COLOR` change rich's native output, and `PYTZ_*` changes pytz's. Fix: "`pydict(value_types=[str, int, float])`; `Console(..., _environ={})`; the oracle drops `NO_COLOR`, `FORCE_COLOR`, `PYTZ_TZDATADIR` and `PYTZ_SKIPEXISTSCHECK`."

9. **Low: the survey omits known needs** (Decision 8). markdown-it-py's testing extra also names flit_core, for `test_packaging`'s sdist build, and pytest-timeout. pytest-regressions and pytest-datadir are pytest plugins too, staged for that family alone (READ, PyPI). pytz's two `test_suite()` builders and its README doctest use the driver's `keep_classes` and doctest keys (`tests/upstream/package_drive.py:129-133`). Fix: "the table names them".

10. **Low: criterion 7's Faker clause has no evidence.** The unit row shows the argument, not the effect. Fix: "the package driver writes `M faker` when `faker` is in `sys.modules` and the family is not Faker's. Criterion 7 reads the absence of that line."

11. **Low: pointers and counts.** The zone check is `test_a_zone_load_does_not_grow_with_the_zip` (`tests/checks/test_v1_3_the_zips_directory.py:230`), not `test_v1_3_data_stack.py:190-209`. The wheel counts are rpds-py 127, python-calamine 104 and wordcloud 56. xyzservices packs 6 members. `top_level.txt` is step 70's own, not the wheel's. The rich, folium and branca tags are lightweight (commit ids), and mdurl's tag object peels to `596bf1c8`. Pygments has 457 example folders. Fix: those values.

12. **Low: the owner's questions should say what they cover** (Owner's choices, 1 and 2). Pygments and xyzservices are dependencies outside the eight ranked packages (`../roadmap.md`, "0.1.5"). requests' alternative also needs charset-normalizer, which the set has. With the patch, folium's METADATA keeps `Requires-Dist: requests`. branca's `PackageLoader("branca", "templates")` runs at import and is served from the zip, as pandas' Styler is (`tests/checks/test_v1_3_default_profile.py:285-292`). Fix: "say each."

## Constitution checks
- §4.1: the two patches are a source move each. A stand-in `requests` would shadow a user's own, so a patch is the smaller change, as with 167's pdfminer patch. The stand-in `_version.py` is a recipe file through `stage` (`scripts/steps/70_zip.sh:133-167`). This holds.
- §4.2: holds (EXECUTED). §4.12: fails as drafted (Findings 1 and 7). §4.6, §4.15: no import and no default moves.
- "Never weaken the judge": the smoke raise is a re-budget once Finding 5 sizes it. The edits in Finding 3 are judge changes with reasons, not a way to get a pass.
- §7: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)
The round's fix commit follows `d67f2659`. It changes only the specification and this section.

1. **Fixed; waits on the owner.** Decision 4 lists Faker's data: text-unidecode's table, GeoNames (CC BY 3.0), the OpenStreetMap extract (ODbL), randomcolor-py, and the 227 modules with a provenance line for the sweep to classify. It is now The owner's choices, 2, and Faker is not built until it is answered.
   - A, recommended: approve with notices, text-unidecode's table under Artistic-1.0-Perl, its text pinned as a file.
   - B: no table. This was checked as feasible: its one reader is `_to_ascii` (`providers/internet/__init__.py:221-226`), but `import faker` imports that provider, so it takes a carried patch that folds with `unicodedata`. Non-Latin e-mails then differ from native.
   - C: Faker out of 0.1.5.
   - Choice 1 now covers the other eight alone.
2. **Fixed.** Decision 4: `_refresh` seeds `faker.generator.random` when `faker.generator` is loaded, with its reason in words. `test_the_refresh_reseeds_what_the_image_froze` gains `faker` and is seen failing first on an image with Faker. Kind and Design name `recipes/reactor_bootstrap.py`, which is frozen into both binaries.
3. **Fixed.** Decision 2 names both checks and how they change, each under `[claim.judge]`:
   - `PANDAS_FOLDERS` gains `pytz`.
   - The embedding check's stub moves to a name pandas still looks for and the set lacks (`pyarrow` is the candidate), its count read from a run before the edit.
   - Scope includes both.
4. **Fixed.** Decision 2 makes the pandas groups' and the smoke groups' growth a normal-tier cost of the pytz pull request: named, claimed, classified, with no cap raised but by the 1.5 rule. Decision 3 does the same for rich. Criterion 4 holds it.
5. **Fixed.** The fixed 1.4 T is gone, and so is the owner's choice. Decision 8 has each pull request raise the bound to its measured sum plus 17 G, rounded up to 10 G, under `[claim.judge]`. The bound is never raised ahead of measurement, and no group's `measured` rises to use the room. This is criterion 9.
6. **Fixed; waits on the owner.** Decision 8 has each pull request dispatch `release.yml` with `release-tier: true` after the owner's yes, as 188 does. The run's id, fuel, passes and classes go in the landing notes; without the yes, the gap is stated there. This is The owner's choices, 5.
7. **Fixed.**
   - The sweep's pattern is widened as asked.
   - Decision 6 adds to rich: wcwidth (MIT), pyfilesystem2 (`filesize.py:1`), and tqdm's notice for `progress.py:808`.
   - It adds to branca ColorBrewer (Apache-2.0) with viridis, and to folium `plugins/encoded.py:67`.
   - Facts lists (rich's palette, Pygments' keyword lists) are named in the sweep's notes.
8. **Fixed.** Decision 9 has `pydict(value_types=[str, int, float])` and `Console(..., _environ={})`, and the oracle drops the four variables.
9. **Fixed.** Decision 8's table names markdown-it-py's flit_core and pytest-timeout, says its two plugins are staged for that family alone, and lists pytz's `keep_classes` and doctest keys.
10. **Fixed.** Decision 7: the package driver writes `M faker` when `faker` is loaded outside Faker's family. Criterion 8 reads its absence.
11. **Fixed.** Every pointer and count is corrected:
   - the zone check's name and file;
   - the wheel counts 127, 104 and 56;
   - xyzservices' 6 members;
   - `top_level.txt` as step 70's own;
   - the lightweight tags, and mdurl's tag peeling to `596bf1c8`;
   - Pygments' 457 folders.
12. **Fixed.** The owner's choices say:
   - Pygments and xyzservices are outside the ranked eight;
   - requests' alternative uses charset-normalizer;
   - folium's METADATA keeps `Requires-Dist: requests`.
   
   Decision 5 says branca's `PackageLoader` is served from the zip.

The owner's answers are not recorded here or in the specification. The orchestrating session asks the five choices together with AskUserQuestion.

## Reviewer's confirmation (round one, on c8f1141f)

I read the specification whole again at `c8f1141f` (READ, `git show c8f1141f`). Its new citations hold: `pandas/compat/pyarrow.py:12` imports pyarrow, `faker/providers/internet/__init__.py:221-226` is `_to_ascii`, `folium/plugins/encoded.py:67` reads "Adapted from", and `scripts/steps/60_link.sh:186` freezes `reactor_bootstrap.py` (all READ).

1. High 1 — confirmed. Decision 4 lists the table, GeoNames, the OpenStreetMap extract and the provenance lines. Faker is now its own owner's choice, 2, with three options, and it waits on that answer. Option B's reader is the one `_to_ascii` (READ), and its cost is stated.
2. High 2 — confirmed for the fix. `_refresh` seeds `faker.generator.random` when `faker.generator` is loaded, beside sympy's step. That is the existing pattern, and a fresh import would seed the generator the same way (READ, `recipes/reactor_bootstrap.py:90-110`). A call's own `Faker.seed(n)` still runs after the refresh. A seed set in the image's prelude is reseeded away, as `random.seed` in a prelude is today. The check's wording is not right, which Low 13 below fixes.
3. Medium 3 — confirmed. Both checks are named, each change is claimed, and the stub's count is read from a run, not assumed.
4. Medium 4 — confirmed (Decision 2's last paragraph, Decision 3, criterion 4).
5. Medium 5 — confirmed: the fixed 1.4 T and its owner's choice are gone. Each raise comes after a measurement, carries +17 G of headroom (today's is 16.9 G), is rounded up to 10 G and is claimed. That is the cairo precedent, so it is a re-budget, not a weakening. Its wording is ambiguous, which Low 14 below fixes.
6. Medium 6 — confirmed (Decision 8; The owner's choices, 5). The gap is stated if the owner says no.
7. Medium 7 — confirmed. The pattern is widened, and the rich, branca and folium notices are added.
8. to 12. Lows 8 to 12 — confirmed, each as its fix text asked (READ).
13. **Low: the Faker row cannot show "two calls from one image differ"** (Decision 4, last paragraph; criterion 7). The check file says its driver "answers entropy and the clocks alike in every run, so a row shows that a generator was reseeded, not that two calls differ" (READ, `tests/checks/test_v1_4_prepare.py:1-9`). Its rows compare a call's draw with the prelude's (`:182-193`). For Faker, an unreseeded call draws the next value from the frozen state, which may already differ from the prelude's, so the row might pass with the old refresh (INFERRED; not run). Fix: "the prelude also prints the next draw of a copy of the frozen state (`r = random.Random(); r.setstate(faker.generator.random.getstate()); r.random()`). The call's `faker.generator.random.random()` must differ from that value. The row is seen failing first with the old refresh. Decision 4 says 'the call does not continue the image's sequence', not 'two calls differ'."
14. **Low: which sum the smoke bound is sized from** (Decision 8; criterion 9). "Its families' measured sum" can be read as that pull request's new groups alone, which would set the bound far below today's 1,183 G. Fix: "the sum of every test-source smoke group's `measured` at the pull request's head, plus 17 G, rounded up to 10 G."

With this round confirmed, `uv run pytest tests/lint -q -p no:cacheprovider` → 14 passed (EXECUTED).

The author's answer to Lows 13 and 14: both fixed in `4339820d`, in the reviewer's words. Both touch only the specification and need no second signing.

## Verdict
Lands: at `c8f1141f` both Highs and all five Mediums are answered, and Lows 13 and 14 need no round, so the specification is fit to build. Building waits on the owner. Choices 1, 3 and 4 must be recorded in `../decisions.md` before the first pull request is built, choice 2 before the Faker pull request, and choice 5 before each dispatch. None was answered when this was signed.
