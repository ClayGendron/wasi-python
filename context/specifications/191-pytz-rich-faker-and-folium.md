# 191: pytz, rich, Faker and folium

- **Status:** drafted 2026-11-15; answered 2026-11-15; built 2026-11-15 on `spec/191-pure-python-packages`, its suites waiting for 193 (the landing notes). Reviewed before it was built (constitution §5.6: it changes the artifact set, the build recipe and the binaries' per-call refresh, and carries two patches): `../reviews/191-pytz-rich-faker-and-folium-spec-2026-11-15.md`, which lands it at round 1. The owner answered The owner's choices 1 to 4 on 2026-11-15 ("Go with your picks", `../decisions.md`, "pytz, rich, Faker and folium: their licences and three choices"); choice 5 was not asked, and its gap is stated (Decision 8). The owner chose the packages on 2026-11-14 (`../decisions.md`, "0.1.5's scope": "all eight ranked packages, cut from the bottom if the release slips"; `../roadmap.md`, "0.1.5").
- **The owner's choices:** five, each written below with its default first. Choices 1 to 4 were asked together in the project chat on 2026-11-15, each with the orchestrating session's pick, and the owner answered "Go with your picks" (12:10 UTC): 1, the eight distributions' licences, approved; 2, Faker's data, option A, approved; 3, folium's `requests`, the carried patch; 4, pytz's line, the four bounds. 5, a release-tier dispatch per pull request, was not asked: the session's GitHub integration cannot dispatch workflows (403), so its gap is stated.
- **Date:** 2026-11-15
- **Owner:** Clay Gendron
- **Kind:** **build-class** (the zip's bytes and members, the snapshot's, `MANIFEST`'s package lines, the licence notices, two carried patches, and `recipes/reactor_bootstrap.py`'s per-call refresh, which step 60 freezes into both binaries: `scripts/steps/60_link.sh:186`), **a judge change** (nine new families, four golden jobs, guest checks, two existing checks rewritten, the driver rule of Decision 7, the smoke bound re-sized). Not structural: nothing under `src/` changes, and the guest's imports and exports do not change.
- **Depends on:** landed: 035 and 175 (the zip's resource reader, the directory read by folder), 041 (files read by path from the zip, and its rejected folder route), 063 (every package runs its own tests), 150 and 157 (a starting image, and the refresh that reseeds what it froze), 171 (the packages a set carries), 173 (a pure wheel joins the zip). Siblings that edit the same files: 187 and 190 (the Rust pipeline and pydantic), 188 (soupsieve: the oracle and its lock). Whichever lands second rebases and recounts the zero-patch tree count in `.github/workflows/release.yml` (41 today, READ). 190 adds rich, markdown-it-py and mdurl to `kit-extra.txt` while rich is not in the set (its review's Disposition, 9, READ on its branch); if 190 lands first, the rich pull request removes those three lines.
- **Research it stands on:** PyPI's JSON API for every distribution named here, read 2026-11-15 (version, files, SHA-256, `requires_dist`, licence, `vulnerabilities`); the pure wheels and sdists, downloaded from the addresses PyPI gives, each matched to PyPI's SHA-256 (EXECUTED, `sha256sum -c`), unpacked in scratch and read, never run; pandas 3.1.0's sdist, matched to `downloads/SHA256SUMS` and read; `git ls-remote` of four repositories for their release tags (EXECUTED). `../research/2026-10-17-what-else-the-default-profile-carries.md`, finding 4e (pytz cost 155 G a `timezone()` from a zip, 2026-10-17); `../research/2026-10-17-the-zips-directory-is-read-once.md`; decision 47 (pytz left out). The pre-build review's own runs (EXECUTED there): Faker's decode table against text-unidecode 1.3's, the zip estimate, the smoke groups' sum. **Not read:** the four GitHub tag archives. The proxy answered 403 for `github.com/<repo>/archive/…`, and nothing was retried by another route, so rich's, mdurl's, folium's and branca's test trees and their digests are the builder's to read.

Labels: EXECUTED, run and seen; READ, read from a file or a page, cited; INFERRED, reasoned.

## The problem

1. The roadmap ranks eight packages for 0.1.5. Four of them need compiled code: jsonschema with referencing needs rpds-py, altair needs jsonschema, python-calamine is Rust, wordcloud has C. Four are pure Python with pure dependencies: pytz, rich, Faker, folium. This specification adds those four.
2. pytz was left out in 2026-10 because one `pytz.timezone()` cost 155 G fuel from the zip (finding 4e). 035 and 175 have since made a resource read cheap. The roadmap asks for the cost to be measured again before pytz ships.
3. folium imports `requests` at the top of `folium/features.py:24`, and the set has no `requests` (READ). branca, folium's dependency, opens its JSON tables by path at import (`branca/colormap.py:19-25`), and a path into the zip does not open (041's problem).
4. Faker's wheel registers a pytest plugin (`[pytest11] faker = faker.contrib.pytest.plugin`, READ, its `entry_points.txt`), and step 70 packs a wheel's `entry_points.txt` (`scripts/make_stdlib_zip.py:137`, READ). Its session fixture is `autouse` (the review, READ). Every guest pytest session would then build a Faker.
5. Faker is not MIT alone. It carries text-unidecode's table and data from GeoNames and OpenStreetMap (the review's Finding 1). And its shared generator is made at import, so a starting image freezes it (Finding 2).

## Decisions

### 1. What is in, and what waits

In, the newest release of each on PyPI (READ, 2026-11-15; every one is pure Python and lists no vulnerability):

| distribution | version | file | SHA-256 | licence (READ) |
|---|---|---|---|---|
| pytz | 2026.6 | `pytz-2026.6-py2.py3-none-any.whl`, 506,321 B | `7fed3fee8fd6bd4a2b7b75a8d56021d0624127bf69bd5691f115db929ac570b3` | MIT |
| pytz (tests) | 2026.6 | `pytz-2026.6.tar.gz`, 318,520 B | `3b0fc2727707663d6e517936f444fd8a8b240f1fc32f4bf7ee03274245945284` | |
| rich | 15.0.0 | `rich-15.0.0-py3-none-any.whl`, 310,654 B | `33bd4ef74232fb73fe9279a257718407f169c09b78a87ad3d296f548e27de0bb` | MIT |
| markdown-it-py | 4.3.0 | `markdown_it_py-4.3.0-py3-none-any.whl`, 96,951 B | `7aa1511a46c39138de78d9eba92ce47e63124d8003fc98b3a351909e04239efa` | MIT |
| markdown-it-py (tests) | 4.3.0 | `markdown_it_py-4.3.0.tar.gz`, 242,701 B | `91a58fa5b72c71a40cf7177250fd767480d7a2bb3ac426ccfb76fb90305fdaaa` | |
| mdurl | 0.1.2 | `mdurl-0.1.2-py3-none-any.whl`, 9,979 B | `84008a41e51615a49fc9966191ff91509e3c40b939176e643fd50a5c2196b8f8` | MIT |
| Pygments | 2.21.0 | `pygments-2.21.0-py3-none-any.whl`, 1,250,147 B | `2363c69b61c4a97c838da3b130dcd6468f4848992b21a82f2a63ec34377137d9` | BSD-2-Clause |
| Pygments (tests) | 2.21.0 | `pygments-2.21.0.tar.gz`, 5,005,329 B | `610ca751c9bc2492b38eb9a38a7fbc93edbbb2d7182edaf34e66ae493dee5c8c` | |
| Faker | 40.54.0 | `faker-40.54.0-py3-none-any.whl`, 2,071,041 B | `2dd88ee8cb63a9149e19ef48bdd73879bc3854d8ba2d6c1535e902a762e603f7` | MIT, with third-party data (Decision 4) |
| Faker (tests) | 40.54.0 | `faker-40.54.0.tar.gz`, 2,037,669 B | `38fba73e32699a9f1071724d67e5a66a84bf057987cffb27c9d0c979fda3f135` | |
| folium | 0.20.0 | `folium-0.20.0.tar.gz`, 109,932 B | `a0d78b9d5a36ba7589ca9aedbd433e84e9fcab79cd6ac213adbcff922e454cb9` | MIT |
| branca | 0.8.2 | `branca-0.8.2.tar.gz`, 27,890 B | `e5040f4c286e973658c27de9225c1a5a7356dd0702a7c8d84c0f0dfbde388fe7` | MIT |
| xyzservices | 2026.9.1 | `xyzservices-2026.9.1-py3-none-any.whl`, 98,829 B | `af4fddac0f1fa5f7951834e2c58e10109e722be548cb1fe4f1a8e8b18cef4c09` | BSD-3-Clause |
| xyzservices (tests) | 2026.9.1 | `xyzservices-2026.9.1.tar.gz`, 1,134,047 B | `8d1a39bf6b192940cc5db5264eeefc1b20dd184f8b83b1303b078743744f5943` | |

Each comes from the address PyPI's JSON gives, at `files.pythonhosted.org`. rich needs markdown-it-py and Pygments; markdown-it-py needs mdurl; folium needs branca, jinja2, numpy, requests and xyzservices; branca needs jinja2 (READ, `requires_dist`). So Pygments and xyzservices join as dependencies, outside the ranked eight. jinja2 3.1.6 and numpy 2.5.4 are in the set already. Faker needs `tzdata` on Windows only, and the set has it. Pygments 2.21.0 is already in the test kit (`tests/upstream/kit.txt:5`, the same SHA-256) and pytz 2026.6 in `kit-extra.txt:10` for plotly and xarray (the same SHA-256). Those lines stay, as `packaging` stays in both today, since the runtime's own copy comes first and the bytes are equal.

Some test sources have no tests in their sdists (READ: the sdists of rich, mdurl, folium and branca hold no test file). Those come from their release tags' GitHub archives, as cycler's and plotly's do (EXECUTED, `git ls-remote`):

- `Textualize/rich` `v15.0.0`, commit `6ac483cb` (a lightweight tag);
- `executablebooks/mdurl` `0.1.2`, tag object `fb264855`, which peels to `596bf1c8`;
- `python-visualization/folium` `v0.20.0`, commit `5c460674` (lightweight);
- `python-visualization/branca` `v0.8.2`, commit `54f16d49` (lightweight).

Their SHA-256 are recorded at the first fetch, as cycler's are (`downloads/SHA256SUMS:171-180`), with 158's release-asset mirror if the owner asks for one.

Waits, each for a later specification (READ, PyPI's JSON):

- **jsonschema 4.26.0, referencing 0.37.0, jsonschema-specifications 2025.9.1.** Their wheels are pure, but jsonschema and referencing need rpds-py 2026.9.1. rpds-py publishes 127 compiled wheels and no pure one: Rust through PyO3. They wait on 187's pipeline.
- **altair 6.3.0.** Pure, but needs jsonschema, so it waits with it.
- **python-calamine 0.9.1.** Rust: 104 compiled wheels, two of them Pyodide's (`pyemscripten`), none for WASI. It waits on 187.
- **wordcloud 1.9.6.** 56 compiled wheels and no pure one: a C extension (INFERRED from the wheel tags). It waits on a C package specification.

### 2. pytz is measured first, and a line cuts it

pytz is the first pull request, and its measurement comes before anything else is built. pytz reads each zone through `importlib.resources.files("pytz").joinpath("zoneinfo", …)` once `os.path.exists` fails on the zip path (`pytz/__init__.py:95-106`, READ), so 035's reader serves it. Its first `timezone()` checks every one of its 597 zone names by opening it (`resource_exists`, `:121-134`, through `all_timezones_set`, `:1136-1139`, READ).

The measure, on the plain binary and the snapshot, from the pull request's own run with a `citest:full` commit line (fuel is compared on darwin-arm64 alone, 188's landing notes):

- the zip's bytes and members with and without pytz (INFERRED here: about 472 KB deflated, 610 members, 604 of them zone files; the review measured 498 KB);
- `-c pass`, `import pytz` over it, and `import pandas` on both binaries, since pandas imports pytz whenever it can (`pandas/_libs/tslibs/timezones.pyx:28`, `import_optional_dependency("pytz", errors="ignore")`, READ in the pinned 3.1.0 sdist);
- the first `pytz.timezone("Europe/Paris")` over `import pytz`, a second zone, and `len(pytz.all_timezones)`;
- beside it, the first `zoneinfo.ZoneInfo("Europe/Paris")` over `import zoneinfo`, on the same set.

A guest check, `test_pytz_first_zone_is_bounded`, holds the line of The owner's choices, 4. It sits in `tests/checks/test_v1_3_the_zips_directory.py` beside the zone check, `test_a_zone_load_does_not_grow_with_the_zip` (`:230`). On the default, pytz is cut if any of these holds:

- the first `timezone()` costs more than 1 G over `import pytz` on either binary (finding 4e measured 155 G; 175's reader projects about 0.2 G, INFERRED from 0.29 M a zone file);
- `import pandas` on the plain binary grows by more than 2%;
- a snapshot start grows by more than 1%;
- the zip grows by more than 0.6 MB.

If it is cut, the pull request carries the numbers and no pytz, decision 47 stands, and the owner is told the numbers. `PYTZ_SKIPEXISTSCHECK` (`:124`) is not set by the runtime; an embedder may set it.

**Two checks pin pytz's absence today, and change in the pytz pull request** (the review's Finding 3). Each is a judge change under `[claim.judge]`, with its reason:

- `test_import_pandas_loads_exactly_its_packages` (`tests/checks/test_v1_3_the_zips_directory.py:554-563`) asserts that `import pandas` loads the folders `PANDAS_FOLDERS` (`:535`): numpy, dateutil and pandas. `PANDAS_FOLDERS` gains `pytz`, since pandas imports it when it is there.
- `test_the_import_path_comes_after_the_runtime` (`tests/checks/test_v1_4_embedding.py:4768-4774`) stubs `pytz` on the import path and counts two `HIT pytz`. Once the zip has pytz, the runtime's copy wins and the stub is never reached. The stub's name becomes one that `import pandas` still looks for and the set still lacks: `pyarrow` is the candidate (`pandas/compat/pyarrow.py:12`, READ). The count it asserts is the one a run on the base set prints, read before the edit, not assumed.

**The pandas groups' growth is a normal-tier cost on the pytz pull request itself** (Finding 4). pandas' conftest calls `pytz.timezone("US/Pacific")` at collection in every pandas session. It grows `TIMEZONES` from 15 to 20 and `_UTCS` from 4 to 5 (READ, `pandas/conftest.py:83`, `:1176-1203`, `:1226-1227`). `tests/tslibs/test_timezones.py:58-60` loads all 433 common zones. The pandas groups are in the normal tier with fixed caps (`tests/upstream/pandas.toml:33-63`), and a pull request runs them when the build changes. So the pytz pull request:

- names each pandas group and each test-source smoke group that gains cases, from its own run (INFERRED here: pandas' groups, matplotlib's `test_dates` cases, and the plotly and xarray families, which have pytz already through the kit);
- claims each one's `passes` and `grows` in its news file;
- classifies any new guest failure in that family's file, with its list;
- raises no cap except by the rule that holds a cap at most 1.5 times its `measured`, claimed.

A family past its file's `budget` goes to the owner.

### 3. rich with markdown-it-py, mdurl and Pygments, as wheels

The four pure wheels go in by `--wheel` lines, as drawsvg's (`scripts/steps/70_zip.sh`). No patch. Pygments' `pygments/lexers/_mapping.py` names its lexers statically, and its plugin search is an `importlib.metadata` query, which 035 serves (INFERRED).

rich's live displays start a thread when they refresh themselves. `Live(auto_refresh=True)`, the default, starts `_RefreshThread` (READ, `rich/live.py:63`, `:142-143`; `Status` makes a `Live`, `rich/status.py:37`). So `rich.progress.track`, `Progress()` and `Console.status()` raise `RuntimeError: can't start new thread` (the guest's message, 188's Decision 4). `Progress(auto_refresh=False)` takes the thread-free branch (`progress.py:1224-1235`, READ). This goes on the limitations page and is not patched: a refresh that needs a thread is the platform's limit, not a bug in rich (§4.1). In the guest, `Console()` finds no terminal and writes plain text, as it does natively when piped.

Suites that skip without rich gain cases when rich ships: tqdm's `tqdm.rich` tests among them (INFERRED). The rich pull request names, claims and classifies them as Decision 2's last paragraph says for pytz.

### 4. Faker, as its wheel, whole, once its data is answered

**Its data (the review's Finding 1).** Faker is MIT, but it ships data under other terms:

- `faker/decode/codes.py`, which `providers/internet/__init__.py:4` imports at import, equals text-unidecode 1.3's `data.bin` entry for entry: 65,536 of 65,536 (EXECUTED by the review). Faker's CHANGELOG at 12.0.0 reads "Remove dependency from text-unidecode". text-unidecode is "Artistic License, or GPL or GPLv2+" (READ by the review, PyPI and its `DESCRIPTION.rst`).
- `providers/geo/__init__.py:13`: coordinates "extracted from geonames.org, under the Creative Commons Attribution 3.0 License"; `address/it_IT/__init__.py:11` is "Converted from" GeoNames (READ).
- `address/mk_MK/__init__.py:84` takes roads from OpenStreetMap, under ODbL (READ).
- 227 of its modules carry a provenance line (`source:`, `data from`, `extracted from`, a licence or a copyright), 334 of the lines cite Wikipedia and others cite national statistics offices (EXECUTED, a `grep -c` over the wheel). The builder's sweep (Decision 6) lists each dataset with its stated terms, and any that states terms is asked.

The owner's choices, 2, decides. Faker is not built until it is answered. Its option B, Faker without text-unidecode's table, is feasible (READ): the table's one reader is `faker/decode/__init__.py`, used only by `_to_ascii` in `providers/internet/__init__.py:221-226` and `internet/es_CL`. But `import faker` imports the internet provider at import (`faker/config.py:11-13`), so the module cannot simply be dropped. It takes a carried patch that folds to ASCII with `unicodedata` instead. Then a Cyrillic, Greek, CJK or Arabic name gives a different e-mail, user name or domain than native's (INFERRED: NFKD does not transliterate those scripts), and Faker's own internet tests for those locales become a class.

**Its listing.** Faker's wheel goes in whole: its 104 locales, across 26 provider packages, are most of its 2.7 MB (READ, its folders; INFERRED, the share). It finds its providers and locales with `pkgutil.iter_modules` on paths inside the package (`faker/utils/loading.py:31-38`, READ). A zipimporter made inside a folder loads that folder (`recipes/zip_directory.py`, its docstring), so the listing is expected whole (INFERRED). The golden job prints `len(faker.config.AVAILABLE_LOCALES)` and the provider list, so a short listing shows. `import faker` imports every provider package at import (`faker/config.py:11-13`, READ); its fuel is recorded, with no line.

**Its shared generator is reseeded in each call** (the review's Finding 2). `faker/generator.py:12` makes `random = random_module.Random()` at import, and every unseeded `Faker()` draws from it (`:68-75`). A starting image made by `make_package_snapshot` imports every package line (`src/wasi_python/_snapshot_make.py:179`), `faker: faker` among them, so the image holds that generator's state. The per-call `_refresh` reseeds only the generators it names: `random`, `numpy.random`, sympy's, more-itertools' and scikit-learn's grower, and `tempfile`'s name sequence (`recipes/reactor_bootstrap.py:90-110`, READ). Without a change, two calls from one image print the same `Faker().name()`; natively two processes differ (INFERRED from the code).

So `_refresh` gains one step, beside sympy's: when `faker.generator` is in `sys.modules`, `faker.generator.random.seed()`. Its comment says why in words, as the others do: a generator made at import is seeded afresh, as a fresh import would seed it. A program's own `Faker.seed(n)` runs after the refresh, so it still gives native's sequence. `test_the_refresh_reseeds_what_the_image_froze` (`tests/checks/test_v1_4_prepare.py:182`) gains `faker` in its `DRAWS` program and its `names`, its docstring names it, and it is seen failing first on an image with Faker and the old refresh. The check's driver answers entropy alike in every run, so the row cannot show that two calls differ; it shows that the call does not continue the image's sequence. The prelude also prints the next draw of a copy of the frozen state (`r = random.Random(); r.setstate(faker.generator.random.getstate()); r.random()`), and the call's `faker.generator.random.random()` must differ from that value (the review's Low 13). The plain binary and the default snapshot import no Faker, so neither changes in behaviour; both binaries' bytes change, since the refresh is frozen into them.

### 5. folium with branca and xyzservices, two from their sdists with a patch each

A wheel is never patched (`docs/contributing/adding-a-package.md`), so folium and branca come from their sdists, staged under `build/pure-install/`. Each is compared with its wheel once by step 70's `walk` and `wheel_members` (READ, 2026-11-15: folium's sdist adds `templates/leaflet.awesome.rotate.css`; branca's wheel adds `_version.py`, written by setuptools-scm). xyzservices goes in by its wheel. It reads its providers with `pkgutil.get_data` (`xyzservices/providers.py:13`, READ), which the zip serves, and its wheel's `.data/` copy is not packed (`make_stdlib_zip.py:176-191`).

- **folium's patch,** `recipes/patches/folium-0.20.0/0001-import-requests-where-a-url-is-fetched.patch`. The module-level `import requests` (`features.py:24`) moves into `GeoJson.get_geojson_from_web` (`:783`), its one use (READ, the only `requests.` in the package). `import folium` then works without requests. A `GeoJson` given a URL raises `ModuleNotFoundError: No module named 'requests'`, and the guest has no network either. This is 167's pdfminer move, and the default of The owner's choices, 3. folium's METADATA keeps `Requires-Dist: requests`, as pdfminer.six's keeps `cryptography`.
- **branca's patch,** `recipes/patches/branca-0.8.2/0001-read-its-tables-as-package-data.patch`. The five `open(os.path.join(rootpath, …))` of `colormap.py:21-25` and `utilities.py:141-148` read through `pkgutil.get_data("branca", …)`, as 167's plotly patch reads its data. 041 rejected a folder at the zip's path for the same need, and its reasons hold. branca's `PackageLoader("branca", "templates")`, which runs at import, needs no patch: jinja2's loader reads from the zip, as pandas' Styler shows (`tests/checks/test_v1_3_default_profile.py:285-292`).
- **branca's version.** A stand-in `branca/_version.py`, the wheel's member byte for byte (`__version__ = "0.8.2"`), staged through `stage` beside the sdist's tree (`scripts/steps/70_zip.sh:133-167`). So `branca.__version__` is native's, and folium's version check reads it (`folium/__init__.py:48-60`).
- **folium's bundled scripts stay out.** `--drop folium/templates` drops three JavaScript files that no Python reads (READ: folium's HTML loads them from a CDN by URL, `plugins/heat_map.py:62`, `heat_map_withtime.py:201-205`). They carry heatmap.js (MIT or Beerware) and Leaflet.heat with simpleheat (BSD-2-Clause, INFERRED), so two notices leave with them.

Each patch has its upstream draft under `../upstream/patches/`, written to its project's contribution rules, read at build (question 80). A map's HTML loads Leaflet, jQuery and Bootstrap from CDNs when a browser opens it, natively as here; the packages page says so.

### 6. The licences and their notices

`scripts/assemble_artifacts.py`'s `PACKAGES` and `WHEELS` gain the nine. Each notice is its wheel's licence files through `wheel_licences`, or its sdist's `LICENSE.txt` for folium and branca. The builder's sweep runs over every file packed, with the pattern `copyright|licen[cs]e|source:|data from|taken from|borrowed from|adapted from|converted from|extracted from|port of|based on` (the review's Finding 7: a notice worded "Data from" or "Borrowed from" escapes the first two words). These are added from the files' own lines (READ):

- rich: `rich/_spinners.py`, cli-spinners (MIT, Sindre Sorhus); `rich/_unicode_data/*.py`, "Data from wcwidth project" (MIT); `rich/filesize.py:1`, "Borrowed from" pyfilesystem2 (MIT, INFERRED); `rich/progress.py:808`, "Based on" tqdm's `std.py` (tqdm's MPL-2.0 AND MIT, approved in 2026-10 for tqdm itself). `rich/_palettes.py:4` takes terminal colours from Wikipedia's table, which is a list of facts, named in the sweep's notes.
- markdown-it-py: its wheel's `LICENSE.markdown-it` (markdown-it, MIT) and `markdown_it/_punycode.py`'s header (punycode.js, MIT, Mathias Bynens).
- mdurl: its `LICENSE` carries Node.js's MIT notice (Joyent) beside its own.
- Pygments: `AUTHORS`; `lexers/robotframework.py`, Apache-2.0 (Nokia Siemens Networks); `styles/solarized.py`, MIT. Its keyword lists "taken from" languages' manuals are facts, named in the sweep's notes.
- Faker: Decision 4's data, and `providers/color/color.py`, which adapts randomcolor-py (MIT, INFERRED from its docstring). Each text a notice needs and the wheel lacks is pinned as a file, as the Unicode terms are.
- folium: `plugins/encoded.py:67`, "Adapted from" Leaflet.encoded (its terms read by the builder; INFERRED a reference to the JavaScript it loads).
- branca: `_schemes.json` carries ColorBrewer's schemes (`utilities.py:106-109`), Apache-2.0, the attribution approved for plotly's copy, and viridis among them (CC0, INFERRED from matplotlib's).
- xyzservices: its provider data comes from leaflet-providers, BSD-2-Clause, "© 2013 Leaflet Providers" (READ, its README). That text is pinned as a file.

The builder repeats the sweep on the staged trees and asks again for any notice beyond this list (§4.12). The test-only wheels of Decision 8 are staged by the judge and never shipped, so §4.12 does not reach them.

### 7. The judge loads Faker's plugin for Faker's family alone

Both guest drivers (`tests/upstream/package_drive.py:260-282`, `tests/upstream/drive.py:113-125`) pass `-p no:faker` for every family but Faker's. So no other session imports Faker, and no other family's fuel moves. pluggy skips a blocked entry point before it loads it (INFERRED from pluggy's `load_setuptools_entrypoints`). A unit row holds the argument. The effect is shown too (the review's Finding 10): after its session, the package driver writes a line `M faker` to its stream when `faker` is in `sys.modules` and the family is not Faker's, and the gather reads its absence. A guest program that runs pytest gets the plugin, as natively.

### 8. The nine families, and how they are judged

Each package gets `tests/upstream/<name>.toml` and `.ini`, a smoke group in the normal tier and the whole suite in the release tier, a release shard, `kind = "suite"` in `packages.toml`, and its name in `PURE_SUITES`. Classes come from a survey of each suite, as 167's did. Those expected (INFERRED; the review's Finding 9 added the extras of markdown-it-py's testing extra and pytz's keys):

| family | test source | kit extras | expected classes and keys |
|---|---|---|---|
| pytz | sdist, `pytz/tests` (3 files; `test_docs.py` reads `README.rst` by a relative path) | none | none; its two `test_suite()` builders and its README doctest use the driver's `keep_classes` and doctest keys (`package_drive.py:129-133`) |
| rich | tag archive, `tests/` | none known | `no-threads` (live refresh) |
| markdown-it-py | sdist, `tests/` | pytest-regressions 2.11.0, pytest-datadir 1.9.0, pytest-timeout and flit_core (for `test_packaging`'s sdist build), versions read at build; the two plugins staged for this family alone | `tests/fuzz/` not selected (atheris) |
| mdurl | tag archive | none known | none |
| Pygments | sdist, `tests/` (457 example-file folders) | wcag-contrast-ratio 0.9 (sdist) | `no-processes` (`test_cmdline.py`), the image formatter's fonts |
| Faker | sdist, `tests/` (47 files) | freezegun (listed), validators 0.36.0, python-stdnum 2.2 | survey; on option B of choice 2, the internet tests of non-Latin locales |
| folium | tag archive, `tests/` | survey | `no-requests`; the Selenium and snapshot tests not selected (no browser) |
| branca | tag archive, `tests/` | survey | the Selenium tests not selected |
| xyzservices | sdist, `xyzservices/tests` | none | `test_providers.py` not selected (it fetches tiles; needs mercantile and requests) |

Every kit extra is a pure wheel or sdist from `files.pythonhosted.org` (READ, PyPI's JSON), as `kit-extra.txt` requires.

**The smoke bound is sized from measurement, per pull request** (the review's Finding 5). `SMOKE_TOTAL_BOUND` is 1.2 T (`tests/harness/packages.py:1499`). The 53 test-source smoke groups record 1,183.07 G, so 16.9 G is left (EXECUTED by the review). Nine new groups add about 95 to 162 G (INFERRED, the review: 10.5 G the smallest group, 18.0 G the median). Each smoke group is the smallest file set that imports the package from the zip and runs its core. Each pull request then raises the bound to the sum of every test-source smoke group's `measured` at its head, plus 17 G, rounded up to 10 G (the review's Low 14). The raise is a judge change under `[claim.judge]`, and the constant's comment names that pull request's families, as the cairo families' raise did (`:1491-1497`). It is never raised ahead of a measurement, and no existing group's `measured` rises to use the room.

**The release groups are judged before the merge** (the review's Finding 6). A pull request runs the normal tier, even with `citest:full` (READ by the review, `release/ci_plan.py:514-523`, `:541-545`). So each pull request is also judged by `release.yml`, dispatched on its branch with `release-tier: true`, as 188's Decision 4 does. That dispatch signs, publishes and pushes nothing (188, READ). The builder asks the owner's yes before each dispatch (The owner's choices, 5), since it is the workflow's longest run. Its landing notes record the run's id, each release group's fuel and passes, and its classes. Without the yes, the gap is stated in the landing notes: the release groups are first judged by the weekly run on `dev` after the merge and by 0.1.5's release pull request, where a red release group stops the tag before anything is signed.

### 9. The golden jobs and the guest checks

The oracle (`tests/jobs/oracle/pyproject.toml` and its lock, by `uv lock --upgrade-package` with uv 0.9.22) gains the nine pins. Natively folium also brings requests, which no job reaches. The oracle passes its own environment through (`tests/harness/jobs.py:251`), so it drops `NO_COLOR`, `FORCE_COLOR`, `PYTZ_TZDATADIR` and `PYTZ_SKIPEXISTSCHECK` (the review's Finding 8). Each job prints lengths and SHA-256 where its output is long, and joins `JOBS`:

- **`time_zones`:** pytz's `localize` and `normalize` across Paris's and New York's changes, Lord Howe's half-hour change, `utcoffset`, `dst` and `tzname`; `len(all_timezones)`, `len(common_timezones)`, `country_timezones("nz")`; a pickle round trip; a pandas `Timestamp` with a pytz zone and its `tz_convert`.
- **`terminal_text`:** rich on `Console(record=True, width=80, force_terminal=True, color_system="truecolor", file=io.StringIO(), _environ={})`: a `Table`, a `Panel`, a `Tree`, `Markdown` (through markdown-it-py), `Syntax` (through Pygments) and `pretty`; `export_text()`, `export_html(inline_styles=True)` and `export_svg(unique_id="job")`. markdown-it-py's `MarkdownIt("commonmark").render` and its tokens; mdurl's `parse`, `encode` and `decode`; Pygments' `highlight` with `HtmlFormatter` and `TerminalFormatter`, and `guess_lexer`.
- **`fake_data`:** `Faker.seed(4321)`; names, addresses, e-mails, `pydict(value_types=[str, int, float])` and `date_between_dates` with fixed dates, for `en_US`, `de_DE`, `ja_JP` and a two-locale `Faker`. No value relative to today: `pydict`'s default types include `date_time`, which ends at now (`faker/providers/python/__init__.py:25-37`, `date_time/__init__.py:1886-1900`, READ by the review). Also `unique.random_int`, the locale count and the provider list.
- **`web_maps`:** a `folium.Map` with a `Marker`, a `CircleMarker`, a `GeoJson` of a dict, a `Choropleth` of a pandas frame, a branca linear colormap, `LayerControl` and `plugins.MarkerCluster`. `get_root().render()` and `_repr_html_()`, each element id (`uuid4().hex`) replaced by a fixed token as `labelled_arrays` does. `branca.utilities.color_brewer("YlGn", 6)`; xyzservices' `CartoDB.Positron.build_url()` and `len(flatten())`.

Guest checks, each seen failing first on a set without its package:

- `test_folium_names_what_the_set_lacks` (`tests/checks/test_v1_3_default_profile.py`): `import folium` works and `requests` is not in `sys.modules`; `GeoJson("https://example.invalid/a.json")` raises `ModuleNotFoundError` naming `requests`.
- `test_rich_refreshes_without_a_thread` (the same file): `track(range(3))` raises `RuntimeError` naming the thread; `Progress(auto_refresh=False)` advances and renders.
- `test_pytz_first_zone_is_bounded` (Decision 2).
- `test_the_refresh_reseeds_what_the_image_froze`, widened for Faker (Decision 4).

### 10. Size and fuel

| distribution | members | in the zip (INFERRED) |
|---|---|---|
| pytz | 610 | 472 KB |
| rich | 101 | 564 KB |
| markdown-it-py | 68 | 140 KB |
| mdurl | 7 | 10 KB |
| Pygments | 343 | 1,831 KB |
| Faker | 752 | 2,687 KB |
| folium, less `templates/` | 49 | 166 KB |
| branca | 11 | 42 KB |
| xyzservices | 6 | 60 KB |
| **all** | **1,947** | **about 5.97 MB** |

INFERRED: each module compiled with the host's Python 3.13 and deflated at level 9, with each member's header, by a scratch script. The review's own measure, with METADATA kept as step 70 keeps it, gave 1,956 members and 6.07 MB (EXECUTED there). Step 70's measure under the line's 3.15.2 is the number. Step 70 also writes a `top_level.txt` for each (171's rule). The wheel grows by about the same, far under `PYPI_FILE_LIMIT` (268,435,456). Since 175, a plain start parses only a folder's own `__init__` entry, about 9 fuel a padding member (175's landing notes, EXECUTED there; `make_stdlib_zip.py:403`), so nine folders cost a start little. The builder records, per pull request, the zip's and the wheel's bytes, both starts, each package's import and each job's fuel, and the news file claims each growth.

## Intent

A program in the guest renders terminal text with rich, fakes data with Faker, draws a web map with folium and, if its cost holds, uses pytz, with native's output. What cannot work here raises a named error.

## Design

Four pull requests, in the roadmap's order, so a slip cuts from the bottom:

1. pytz, with Decision 2's measure and its two rewritten checks;
2. rich with markdown-it-py, mdurl and Pygments;
3. Faker, with Decisions 4 and 7, once The owner's choices, 2, is answered;
4. folium with branca and xyzservices.

Each carries its own news file and review, `191-<part>` (`191-pytz`, `191-rich`, `191-faker`, `191-folium`), and its own smoke-bound raise (Decision 8).

- Recipe: `scripts/00_download.sh` and `downloads/SHA256SUMS` (the pins, a `tests` line for each test source); `scripts/steps/70_zip.sh` (seven `--wheel` lines; folium's and branca's trees staged, the stand-in, `--drop folium/templates`); `scripts/assemble_artifacts.py`; `recipes/reactor_bootstrap.py` (Faker's reseed); `recipes/snapshot-packages.txt` (`pytz: pytz`, `rich: rich rich.console rich.table rich.markdown rich.syntax`, `markdown-it-py: markdown_it`, `mdurl: mdurl`, `pygments: pygments pygments.lexers pygments.formatters`, `faker: faker`, `folium: folium folium.plugins`, `branca: branca branca.colormap branca.element`, `xyzservices: xyzservices xyzservices.providers`).
- Patches: `recipes/patches/folium-0.20.0/`, `recipes/patches/branca-0.8.2/`, each with its draft (and on option B of choice 2, a third, Faker's); `tests/harness/pins.py` (`SOURCE_PATTERNS`), `tests/harness/needs.py` (`SOURCE_COMPONENTS`), and the zero-patch count in `release.yml`, two more trees.
- Judge: the nine families, their `.ini`, `packages.toml`, `PURE_SUITES`, `tests/release_shards.toml`, `kit-extra.txt`; Decision 7's driver arguments, its `M faker` line and unit row; the four jobs with their `.expected`, `tests/harness/jobs.py` (the oracle's environment), the oracle; the guest checks of Decision 9; the two checks of Decision 2; `tests/harness/paths.py` (`LICENCE_COMPONENTS`, `PACKAGES`); `tests/unit/test_artifact_rules.py`'s synthetic set; `SMOKE_TOTAL_BOUND`.
- Documents: `docs/reference/packages.md` (rows; line 83's pytz advice goes if pytz ships); `docs/reference/limitations.md` (rich's refresh; folium's URL `GeoJson`, a map's CDN scripts; line 51's "No pytz" goes if it ships); `docs/reference/guest-filesystem.md:102`, `docs/how-to/grants.md:89` and `docs/how-to/troubleshooting.md:118`, whose `pytz` example becomes a package the set still lacks.
- The news files' Upgrading entries: a program that brought its own pytz, rich, Pygments, Faker or folium through `import_path=` now gets the runtime's, since the runtime's modules come first (`docs/how-to/grants.md:89`); and pandas now imports pytz when it is there.

## Scope

In: Decisions 1 to 10, in the four pull requests of Design, the two existing checks of Decision 2 and the refresh check of Decision 4 included. Out: jsonschema, referencing, jsonschema-specifications, rpds-py, altair, python-calamine and wordcloud (Decision 1); requests and its dependencies (on the default of The owner's choices, 3); a mirror for the tag archives unless the owner asks.

## Acceptance criteria

1. The owner's answers to The owner's choices, 1, 2 (before the Faker pull request), 3 and 4 are recorded in `../decisions.md` before the first pull request is built. Each pull request's landing notes carry the builder's sweep with Decision 6's pattern, and any notice beyond Decision 6 is asked first.
2. Every pin's SHA-256 matches PyPI's or, for a tag archive, the bytes recorded at its first fetch (EXECUTED).
3. Decision 2's numbers are recorded from a `citest:full` run, and `test_pytz_first_zone_is_bounded` passes; or pytz is cut and its pull request says so. The two rewritten checks pass, each change claimed under `[claim.judge]`.
4. The pytz and rich pull requests name, claim and classify every group whose cases grow, from their own runs; no cap rises but by the 1.5 rule.
5. The zip's names differ from the base set's by exactly the computed additions, none under `folium/templates/`; folium's and branca's trees are their sdists plus their patches and the stand-in (the build shard).
6. The four golden jobs match native (`tests/jobs/regen.py --check`, and their checks in the guest).
7. The guest checks of Decision 9 are seen failing first and pass on both binaries, the refresh check on an image with Faker; Decision 7's unit row is seen failing first.
8. The nine families pass in their tiers with their surveyed classes, the release groups read on the dispatched run of Decision 8 (or, without the owner's yes, the gap stated); no gather of a family but Faker's has an `M faker` line; every growth is claimed.
9. `SMOKE_TOTAL_BOUND` is the sum of every test-source smoke group's `measured` at the pull request's head, plus 17 G, rounded up to 10 G, claimed.
10. The bytes and fuel of Decision 10 are recorded per pull request (EXECUTED).
11. The fast tier, `tests/lint` and each pull request's `ci-status` are green.

## The owner's choices

1. **The licences of eight distributions (§4.12).** **Answered 2026-11-15: approved, as recommended.** Recommended: approve, each shipped with its notices as Decision 6 lists them:
   - pytz (MIT);
   - rich (MIT, with cli-spinners', wcwidth's and pyfilesystem2's MIT, and tqdm's notice for the code it bases on);
   - markdown-it-py (MIT, with markdown-it's and punycode.js's MIT);
   - mdurl (MIT, with Node.js's MIT);
   - Pygments (BSD-2-Clause with its AUTHORS; its Robot Framework lexer under Apache-2.0; its Solarized style MIT);
   - folium (MIT);
   - branca (MIT, with ColorBrewer's Apache-2.0 and viridis);
   - xyzservices (BSD-3-Clause, with leaflet-providers' BSD-2-Clause).

   Pygments and xyzservices are dependencies outside the ranked eight. Alternative: approve part by part, and the parts not approved wait.
2. **Faker's third-party data.** **Answered 2026-11-15: A, approved.** Faker was not built until this was answered.
   - **A, recommended:** approve Faker (MIT) with its notices: text-unidecode's table under Artistic-1.0-Perl, of its "Artistic, or GPL-2.0-or-later" offer, its text pinned as a file; GeoNames (CC BY 3.0, attributed); the OpenStreetMap extract (ODbL, attributed); randomcolor-py (MIT); and each dataset the sweep finds with stated terms, listed to the owner before the build. Faker then gives native's output.
   - **B:** approve GeoNames, OpenStreetMap and the rest, and ship Faker without text-unidecode's table, through a carried patch that folds to ASCII with `unicodedata` (Decision 4: feasible, checked). E-mails and user names for non-Latin names then differ from native, and that patch has no upstream end.
   - **C:** leave Faker out of 0.1.5.
3. **folium's `requests`.** **Answered 2026-11-15: the carried patch.** Recommended: the carried patch of Decision 5. A `GeoJson` given a URL names `requests`, and folium's METADATA still lists it. Alternative: ship requests 2.34.2 with urllib3 2.8.0, idna 3.20 and certifi 2026.10.23 (Apache-2.0, MIT, BSD-3-Clause, MPL-2.0; four more licences, about 0.4 MB; it uses charset-normalizer, which the set has). Even then `import requests` needs a writable temporary folder: `requests/utils.py:82` calls `certifi.where()` at import, which copies its bundle out of the zip through `importlib.resources.as_file` (READ; 035 says `as_file` needs one). And the guest has no network.
4. **pytz's line.** **Answered 2026-11-15: the four bounds.** Recommended: the four bounds of Decision 2. Alternatives: ship pytz whatever the numbers, which are recorded; or keep decision 47 now and measure nothing.
5. **The release-tier dispatch.** **Not asked, not answered:** this session's GitHub integration cannot dispatch a workflow (it answers 403), so the alternative's gap is stated in the landing notes. Recommended: yes, for each of the four pull requests, before its merge (Decision 8), as asked for 188. Alternative: no dispatch, and each pull request states the gap.

## Landing notes

Built 2026-11-15 on `spec/191-pure-python-packages`, one branch for all nine (the orchestrating session's brief), in a container that could build no set: `www.python.org`, `sh.rustup.rs` and the OSV API were refused by its proxy, and GitHub's tag archives answered 403. Nothing was retried by another route. So no guest check, fuel figure or upstream group was run here; every number below that says EXECUTED was run natively in scratch.

**What was built.**

- The nine pins with PyPI's SHA-256 (`downloads/SHA256SUMS`, `scripts/00_download.sh`), and four more files the notices need: wcwidth 0.9.4's and fs 2.4.16's wheels (each only for its licence, which rich's lines name and its wheel lacks; neither is packed), text-unidecode 1.3's sdist (its `LICENSE`, which holds the Artistic License's text) and SPDX's BSD-2-Clause text at the commit the other SPDX texts use. The test-source sdists are not pinned: they belong to 193.
- Step 70: seven `--wheel` lines; folium and branca unpacked from their sdists and patched, folium copied whole and branca staged with its `_version.py` stand-in; both sdists' `PKG-INFO` packed as metadata; `--drop folium/templates`. `release.yml` counts 43 zero-patch trees; README counts 35 carried patches.
- The two carried patches and their upstream drafts (`../upstream/patches/folium-0.20.0/`, `../upstream/patches/branca-0.8.2/`), each with its native test evidence.
- The notices (`scripts/assemble_artifacts.py`): Decision 6's list, each line read from the pinned file and checked for its words. Built natively from the pinned files (EXECUTED): rich 9 parts, markdown-it-py 3, Pygments 6, Faker 10, xyzservices 3, folium 2, branca 3, pytz 1, mdurl 1.
- Faker's reseed in `_refresh`, and `test_the_refresh_reseeds_what_the_image_froze` widened with the frozen-state copy's next draw (the review's Low 13). Seen failing first natively only (EXECUTED, a scratch script that freezes and restores the generator's state as an image does): the old refresh gives the frozen state's next draw, the new one does not.
- Decision 7: `-p no:faker` in both drivers (the package driver for every family but Faker's), the `M faker` line, and the guard's finding for a module with no file. The unit row and the guard row were seen failing first (EXECUTED). Natively, `-p no:faker` keeps Faker out of `sys.modules` and its absence lets it in (EXECUTED, pytest 9 on the line's 3.15.2).
- The two checks of Decision 2: `PANDAS_FOLDERS` gains pytz (natively `import pandas` imports pytz when it is installed, EXECUTED); the import-path check stubs `pyarrow` and counts one lookup. That count was read natively, with pandas 3.1.0 on 3.15.2 and the stub first on `sys.path`, where the same method counts pytz twice, as the guest's check did (EXECUTED); not from a base-set guest run, which needs a built set.
- Three new guest checks: `test_pytz_first_zone_is_bounded`, `test_folium_names_what_the_set_lacks`, `test_rich_refreshes_without_a_thread`. Each program was run natively (EXECUTED): folium's, on the patched tree without requests, prints the expected answer, and on the unpatched tree fails at `import folium`; rich's `Progress` part passes natively, where `track` has threads. None was seen failing on a set without its package, since none could be built.
- The four golden jobs, written by the oracle under both hash seeds and reproduced with `--check` (EXECUTED, `tests/jobs/regen.py --online`, linux x86_64); the oracle gains the nine pins and requests with its three dependencies, locked with uv 0.9.22, and drops the four environment names. Natively, `web_maps` on the patched folium and branca trees, less `templates/`, prints the golden byte for byte (EXECUTED).
- The docs (packages, limitations, the import path's example, troubleshooting), the news file and the release ledger's block.

**Measured in scratch** (EXECUTED: each wheel's and tree's members as step 70 packs them, compiled under the line's 3.15.2 and deflated at level 9, with the `top_level.txt` step 70 writes; the zip's directory not counted):

| distribution | members | bytes |
|---|---|---|
| pytz | 612 | 504,821 |
| rich | 103 | 703,249 |
| markdown-it-py | 71 | 161,480 |
| mdurl | 9 | 11,923 |
| Pygments | 346 | 2,041,380 |
| Faker | 755 | 3,156,874 |
| folium, less `templates/` | 51 | 178,436 |
| branca | 13 | 45,572 |
| xyzservices | 7 | 53,010 |
| **all** | **1,967** | **6,856,745** |

pytz's 504,821 bytes are under the 0.6 MB line. Its other three bounds (the first zone, `import pandas`, a snapshot start) and every fuel figure wait for a built set.

**Deviations from the specification.**

- One branch builds all nine, not four pull requests.
- No family has its `.toml`, `.ini`, smoke group, release shard or `PURE_SUITES` entry: each is `later` in `packages.toml`, closing with 193, reserved in the roadmap, because no group's fuel could be measured, as 187's orjson suite waited. `SMOKE_TOTAL_BOUND` is unchanged, since no group joins. The four test trees that need a tag archive (rich, mdurl, folium, branca) could not be read either.
- rich's notice also carries wcwidth's and PyFilesystem2's licences, each read from that project's pinned wheel, and tqdm's: rich names each project and its wheel carries none of their texts.
- The guard names a bare `M` line "a module was loaded outside its family" rather than the zip finding it would otherwise fall into.

**Not machine-checked here, and waiting for a built set.** Every guest check named above; the four jobs' guest runs; pytz's four bounds; the zip's, the wheel's and both binaries' bytes; the starts' fuel; the pandas, matplotlib and tqdm groups' new cases and fuel, against their fixed caps (Finding 4: a group past its cap goes to the owner). The Faker row of the refresh check compares the call's first draw with the prelude's too, as the other generators' rows do; the driver answers entropy alike in every run, so a built set shows whether the two reseeds land on the same seed.

**The release tier.** Choice 5 was not asked (403), so the release groups are first judged by 0.1.5's release pull request or the weekly run on `dev` after the merge, where a red release group stops the tag before anything is signed.

**The sweep** (Decision 6's pattern over every packed file, EXECUTED). Beyond Decision 6's list, these lines state terms or a source, and were approved by the owner on 2026-11-15 ("Approve all three", `../decisions.md`; §4.12): Pygments' `formatters/terminal256.py:7`, adapted from xterm256-conv, which states no terms; Pygments' `lexers/configs.py:1130`, adapted from CPython's tomllib (the PSF licence, already in `LICENSES/cpython.txt`); rich's `syntax.py:62`, styles based on Pygments' (BSD-2-Clause, approved, and its line ships in rich's notice); Faker's `color.py:7`, randomColor (CC0), `person/hu_HU`, the Government of Hungary's records (public domain), and `date_time/th_TH`, code in the public domain or under CC0, each named in Faker's notice. Facts, named and not shipped as notices: rich's `_palettes.py:4` (Wikipedia's table of terminal colours) and Pygments' keyword lists taken from languages' manuals. wcwidth's licence also carries Markus Kuhn's permission notice, which ships with it.
