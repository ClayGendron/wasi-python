# 191: pytz, rich, Faker and folium

- **Status:** drafted 2026-11-15, not built. To be reviewed before it is built (constitution §5.6: it changes the artifact set and the build recipe, and carries two patches). **Not to be built** until the owner approves the licences of The owner's choices, 1 (the roadmap: "Each licence approved before it is built"); `../decisions.md` records no approval for any of the nine distributions here (READ, 2026-11-15: its "0.1.5's scope" approves the pydantic family's and orjson's licences alone). The owner chose the packages on 2026-11-14 (`../decisions.md`, "0.1.5's scope": "all eight ranked packages, cut from the bottom if the release slips"; `../roadmap.md`, "0.1.5").
- **Open for the owner:** four choices, each written below with its default first, to be asked together by the orchestrating session with AskUserQuestion; this author could not ask them. 1: the licences. 2: how folium meets its `requests` import. 3: the line that cuts pytz. 4: the smoke groups' total bound.
- **Date:** 2026-11-15
- **Owner:** Clay Gendron
- **Kind:** **build-class** (the zip's bytes and members, the snapshot's, `MANIFEST`'s package lines, the licence notices, two carried patches), **a judge change** (nine new families, four golden jobs, guest checks, the plugin rule of Decision 7, one bound). Not structural: nothing under `src/` changes, and the guest's imports and exports do not change.
- **Depends on:** landed: 035 and 175 (the zip's resource reader, the directory read by folder), 041 (files read by path from the zip, and its rejected folder route), 063 (every package runs its own tests), 171 (the packages a set carries), 173 (a pure wheel joins the zip). Siblings that edit the same files: 187 and 190 (the Rust pipeline and pydantic), 188 (soupsieve: the oracle and its lock). Whichever lands second rebases and recounts the zero-patch tree count in `.github/workflows/release.yml` (41 today, READ).
- **Research it stands on:** PyPI's JSON API for every distribution named here, read 2026-11-15 (version, files, SHA-256, `requires_dist`, licence, `vulnerabilities`); the pure wheels and sdists, downloaded from the addresses PyPI gives, each matched to PyPI's SHA-256 (EXECUTED, `sha256sum -c`), unpacked in scratch and read, never run; pandas 3.1.0's sdist, matched to `downloads/SHA256SUMS` and read; `git ls-remote` of four repositories for their release tags (EXECUTED). `../research/2026-10-17-what-else-the-default-profile-carries.md`, finding 4e (pytz cost 155 G a `timezone()` from a zip, 2026-10-17); `../research/2026-10-17-the-zips-directory-is-read-once.md`; decision 47 (pytz left out). **Not read:** the four GitHub tag archives (the proxy answered 403 for `github.com/<repo>/archive/…`; not retried by another route), so rich's, mdurl's, folium's and branca's test trees and their digests are the builder's to read.

Labels: EXECUTED, run and seen; READ, read from a file or a page, cited; INFERRED, reasoned.

## The problem

1. The roadmap ranks eight packages for 0.1.5. Four of them need compiled code: jsonschema with referencing needs rpds-py, altair needs jsonschema, python-calamine is Rust, wordcloud has C. Four are pure Python with pure dependencies: pytz, rich, Faker, folium. This specification adds those four.
2. pytz was left out in 2026-10 because one `pytz.timezone()` cost 155 G fuel from the zip (finding 4e). 035 and 175 have since made a resource read cheap. The roadmap asks for the cost to be measured again before pytz ships.
3. folium imports `requests` at the top of `folium/features.py:24`, and the set has no `requests` (READ). branca, folium's dependency, opens its JSON tables by path at import (`branca/colormap.py:19-25`), and a path into the zip does not open (041's problem).
4. Faker's wheel registers a pytest plugin (`[pytest11] faker = faker.contrib.pytest.plugin`, READ, its `entry_points.txt`), and step 70 packs a wheel's `entry_points.txt` (`scripts/make_stdlib_zip.py:137`, READ). Every guest pytest session would then import Faker.

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
| Faker | 40.54.0 | `faker-40.54.0-py3-none-any.whl`, 2,071,041 B | `2dd88ee8cb63a9149e19ef48bdd73879bc3854d8ba2d6c1535e902a762e603f7` | MIT |
| Faker (tests) | 40.54.0 | `faker-40.54.0.tar.gz`, 2,037,669 B | `38fba73e32699a9f1071724d67e5a66a84bf057987cffb27c9d0c979fda3f135` | |
| folium | 0.20.0 | `folium-0.20.0.tar.gz`, 109,932 B | `a0d78b9d5a36ba7589ca9aedbd433e84e9fcab79cd6ac213adbcff922e454cb9` | MIT |
| branca | 0.8.2 | `branca-0.8.2.tar.gz`, 27,890 B | `e5040f4c286e973658c27de9225c1a5a7356dd0702a7c8d84c0f0dfbde388fe7` | MIT |
| xyzservices | 2026.9.1 | `xyzservices-2026.9.1-py3-none-any.whl`, 98,829 B | `af4fddac0f1fa5f7951834e2c58e10109e722be548cb1fe4f1a8e8b18cef4c09` | BSD-3-Clause |
| xyzservices (tests) | 2026.9.1 | `xyzservices-2026.9.1.tar.gz`, 1,134,047 B | `8d1a39bf6b192940cc5db5264eeefc1b20dd184f8b83b1303b078743744f5943` | |

Each comes from the address PyPI's JSON gives, at `files.pythonhosted.org`. rich needs markdown-it-py and Pygments; markdown-it-py needs mdurl; folium needs branca, jinja2, numpy, requests and xyzservices; branca needs jinja2 (READ, `requires_dist`). jinja2 3.1.6 and numpy 2.5.4 are in the set already. Faker needs `tzdata` on Windows only, and the set has it. Pygments 2.21.0 is already in the test kit (`tests/upstream/kit.txt`, the same SHA-256) and pytz 2026.6 in `kit-extra.txt` for plotly and xarray (the same SHA-256): those lines stay, as `packaging` stays in both today, since the runtime's own copy comes first and the bytes are equal.

Test sources with no sdist tests (READ: the sdists of rich, mdurl, folium and branca hold no test file) come from their release tags' GitHub archives, as cycler's and plotly's do: `Textualize/rich` `v15.0.0` (tag object `6ac483cb`), `executablebooks/mdurl` `0.1.2` (`fb264855`), `python-visualization/folium` `v0.20.0` (`5c460674`), `python-visualization/branca` `v0.8.2` (`54f16d49`) (EXECUTED, `git ls-remote`). Their SHA-256 are the builder's to record, at the first fetch, with the release-asset mirror of 158 if the owner asks for one.

Waits, each for a later specification (READ, PyPI's JSON):

- **jsonschema 4.26.0, referencing 0.37.0, jsonschema-specifications 2025.9.1.** Their wheels are pure, but both need rpds-py 2026.9.1, which publishes 128 compiled wheels and no pure one: Rust through PyO3. They wait on 187's pipeline.
- **altair 6.3.0.** Pure, but needs jsonschema, so it waits with it.
- **python-calamine 0.9.1.** Rust: 105 compiled wheels, two of them Pyodide's (`pyemscripten`), none for WASI. It waits on 187.
- **wordcloud 1.9.6.** 57 compiled wheels and no pure one: a C extension (INFERRED from the wheel tags). It waits on a C package specification.

### 2. pytz is measured first, and a line cuts it

pytz is the first pull request, and its measurement comes before anything else is built. pytz reads each zone through `importlib.resources.files("pytz").joinpath("zoneinfo", …)` once `os.path.exists` fails on the zip path (`pytz/__init__.py:95-106`, READ), so 035's reader serves it. Its first `timezone()` checks every one of its 597 zone names by opening it (`resource_exists`, `:121-134`, through `all_timezones_set`, `:1136-1139`, READ).

The measure, on the plain binary and the snapshot, from the pull request's own run with a `citest:full` commit line (fuel is compared on darwin-arm64 alone, 188's landing notes):

- the zip's bytes and members with and without pytz (INFERRED here: about 472 KB deflated, 610 members, 604 of them zone files);
- `-c pass`, `import pytz` over it, and `import pandas` on both binaries, since pandas imports pytz whenever it can (`pandas/_libs/tslibs/timezones.pyx:28`, `import_optional_dependency("pytz", errors="ignore")`, READ in the pinned 3.1.0 sdist);
- the first `pytz.timezone("Europe/Paris")` over `import pytz`, a second zone, and `len(pytz.all_timezones)`;
- beside it, the first `zoneinfo.ZoneInfo("Europe/Paris")` over `import zoneinfo`, on the same set.

A guest check, `test_pytz_first_zone_is_bounded` in `tests/checks/test_v1_3_data_stack.py` beside the zone check (`:190-209`), holds the line of The owner's choices, 3. On the default, pytz is cut if any of these holds:

- the first `timezone()` costs more than 1 G over `import pytz` on either binary (finding 4e measured 155 G; 175's reader projects about 0.2 G, INFERRED from 0.29 M a zone file);
- `import pandas` on the plain binary grows by more than 2%;
- a snapshot start grows by more than 1%;
- the zip grows by more than 0.6 MB.

If it is cut, the pull request carries the numbers and no pytz, decision 47 stands, and the owner is told the numbers. `PYTZ_SKIPEXISTSCHECK` (`:124`) is not set by the runtime; an embedder may set it.

Two costs follow pytz into the judge, and are claimed, not gated. pandas' conftest adds pytz zones to its time-zone fixtures when pytz imports (`pandas/conftest.py:83`, READ), so the pandas families gain cases; and matplotlib's and tqdm's suites, which skip without pytz or rich, gain theirs (INFERRED). The builder reads each family's count and fuel at the release tier's run, and a family past its file's `budget` goes to the owner.

### 3. rich with markdown-it-py, mdurl and Pygments, as wheels

The four pure wheels go in by `--wheel` lines, as drawsvg's (`scripts/steps/70_zip.sh`). No patch. Pygments' `pygments/lexers/_mapping.py` names its lexers statically, and its plugin search is an `importlib.metadata` query, which 035 serves (INFERRED).

rich's live displays start a thread when they refresh themselves: `Live(auto_refresh=True)`, the default, starts `_RefreshThread` (READ, `rich/live.py:63`, `:142-143`; `Status` makes a `Live`, `rich/status.py:37`), so `rich.progress.track`, `Progress()` and `Console.status()` raise `RuntimeError: can't start new thread` (the guest's message, 188's Decision 4). `Progress(auto_refresh=False)` with `refresh()` works. This is written on the limitations page, not patched: a refresh that needs a thread is the platform's limit, not a bug in rich (§4.1). In the guest, `Console()` finds no terminal and writes plain text, as it does natively when piped.

### 4. Faker, as its wheel, whole

Faker's wheel goes in whole: its 104 locales, across 26 provider packages, are most of its 2.7 MB (READ, its folders; INFERRED, the share). It finds its providers and locales with `pkgutil.iter_modules` on paths inside the package (`faker/utils/loading.py:31-38`, READ). A zipimporter made inside a folder loads that folder (`recipes/zip_directory.py`, its docstring), so the listing is expected whole (INFERRED); the golden job prints `len(faker.config.AVAILABLE_LOCALES)` and the provider list, so a short listing shows. `import faker` imports every provider package at import (`faker/config.py:11-13`, READ); its fuel is recorded, with no line.

### 5. folium with branca and xyzservices, two from their sdists with a patch each

A wheel is never patched (`docs/contributing/adding-a-package.md`), so folium and branca come from their sdists, staged under `build/pure-install/`, compared with their wheels once by step 70's `walk` and `wheel_members` (READ, 2026-11-15: folium's sdist adds `templates/leaflet.awesome.rotate.css`; branca's wheel adds `_version.py`, written by setuptools-scm). xyzservices goes in by its wheel; it reads its providers with `pkgutil.get_data` (`xyzservices/providers.py:13`, READ), which the zip serves, and its wheel's `.data/` copy is not packed (`make_stdlib_zip.py:176-191`).

- **folium's patch,** `recipes/patches/folium-0.20.0/0001-import-requests-where-a-url-is-fetched.patch`: the module-level `import requests` (`features.py:24`) moves into `GeoJson.get_geojson_from_web` (`:783`), its one use (READ, the only `requests.` in the package). `import folium` then works without requests, and a `GeoJson` given a URL raises `ModuleNotFoundError: No module named 'requests'`; the guest has no network either. This is 167's pdfminer move. The default of The owner's choices, 2.
- **branca's patch,** `recipes/patches/branca-0.8.2/0001-read-its-tables-as-package-data.patch`: the five `open(os.path.join(rootpath, …))` of `colormap.py:21-25` and `utilities.py:141-148` read through `pkgutil.get_data("branca", …)`, as 167's plotly patch reads its data. 041 rejected a folder at the zip's path for the same need, and its reasons hold.
- **branca's version.** A stand-in `branca/_version.py`, the wheel's member byte for byte (`__version__ = "0.8.2"`), staged beside the sdist's tree, so `branca.__version__` is native's and folium's version check reads it (`folium/__init__.py:48-60`).
- **folium's bundled scripts stay out.** `--drop folium/templates`: three JavaScript files and no Python reader (READ: folium's HTML loads them from a CDN by URL, `plugins/heat_map.py:62`, `heat_map_withtime.py:201-205`). They carry heatmap.js (MIT or Beerware) and Leaflet.heat with simpleheat (BSD-2-Clause, INFERRED), so two notices leave with them.

Each patch has its upstream draft under `../upstream/patches/`, written to its project's contribution rules, read at build (question 80). A map's HTML loads Leaflet, jQuery and Bootstrap from CDNs when a browser opens it, natively as here; the packages page says so.

### 6. The licences and their notices

`scripts/assemble_artifacts.py`'s `PACKAGES` and `WHEELS` gain the nine; each notice is its wheel's licence files through `wheel_licences`, or its sdist's `LICENSE.txt` for folium and branca, with these added from the files' own headers (READ, a sweep of `copyright|licen[cs]e` over every file packed):

- rich: `rich/_spinners.py`, cli-spinners (MIT, Sindre Sorhus).
- markdown-it-py: its wheel's `LICENSE.markdown-it` (markdown-it, MIT) and `markdown_it/_punycode.py`'s header (punycode.js, MIT, Mathias Bynens).
- mdurl: its `LICENSE` carries Node.js's MIT notice (Joyent) beside its own.
- Pygments: `AUTHORS`; `lexers/robotframework.py`, Apache-2.0 (Nokia Siemens Networks); `styles/solarized.py`, MIT.
- Faker: `providers/color/color.py` adapts randomcolor-py (MIT, INFERRED from its docstring; its text is pinned as a file if the sweep needs it, as the Unicode terms are).
- xyzservices: its provider data comes from leaflet-providers, BSD-2-Clause, "© 2013 Leaflet Providers" (READ, its README); that text is pinned as a file.

The builder repeats the sweep on the staged trees and asks again for any notice beyond this list (§4.12). The test-only wheels of Decision 8 are staged by the judge and never shipped, so §4.12 does not reach them.

### 7. The judge loads Faker's plugin for Faker's family alone

Both guest drivers (`tests/upstream/package_drive.py:260-282`, `tests/upstream/drive.py:113-125`) pass `-p no:faker` for every family but Faker's, so no other session imports Faker and no other family's fuel moves. pluggy skips a blocked entry point before it loads it (INFERRED from pluggy's `load_setuptools_entrypoints`). A unit row holds the argument. A guest program that runs pytest gets the plugin, as natively.

### 8. The nine families

Each package gets `tests/upstream/<name>.toml` and `.ini`, a smoke group in the normal tier and the whole suite in the release tier, a release shard, `kind = "suite"` in `packages.toml`, and its name in `PURE_SUITES`. Classes come from a survey of each suite, as 167's did; those expected (INFERRED):

| family | test source | kit extras | expected classes |
|---|---|---|---|
| pytz | sdist, `pytz/tests` (3 files; `test_docs.py` reads `README.rst` by a relative path) | none | none |
| rich | tag archive, `tests/` | none known | `no-threads` (live refresh) |
| markdown-it-py | sdist, `tests/` | pytest-regressions 2.11.0, pytest-datadir 1.9.0 | `tests/fuzz/` not selected (atheris) |
| mdurl | tag archive | none known | none |
| Pygments | sdist, `tests/` (458 example-file folders) | wcag-contrast-ratio 0.9 (sdist) | `no-processes` (`test_cmdline.py`), the image formatter's fonts |
| Faker | sdist, `tests/` (47 files) | freezegun (listed), validators 0.36.0, python-stdnum 2.2 | survey |
| folium | tag archive, `tests/` | survey | `no-requests`; the Selenium and snapshot tests not selected (no browser) |
| branca | tag archive, `tests/` | survey | the Selenium tests not selected |
| xyzservices | sdist, `xyzservices/tests` | none | `test_providers.py` not selected (it fetches tiles; needs mercantile and requests) |

Every kit extra is a pure wheel or sdist from `files.pythonhosted.org` (READ, PyPI's JSON), as `kit-extra.txt` requires.

Nine smoke groups put the test-source total past `SMOKE_TOTAL_BOUND` (1.2 T, `tests/harness/packages.py:1499`), which stood at 1,183.07 G with 16.9 G to spare at 188 (EXECUTED there): at 10 to 20 G a group, about 1.27 to 1.36 T (INFERRED). Each smoke group is the smallest file set that imports the package from the zip and runs its core. The owner's choices, 4, sets the bound.

### 9. The golden jobs and the guest checks

The oracle (`tests/jobs/oracle/pyproject.toml` and its lock, by `uv lock --upgrade-package` with uv 0.9.22) gains the nine pins; natively folium also brings requests, which no job reaches. Each job prints lengths and SHA-256 where its output is long, and joins `JOBS`:

- **`time_zones`:** pytz's `localize` and `normalize` across Paris's and New York's changes, Lord Howe's half-hour change, `utcoffset`, `dst` and `tzname`; `len(all_timezones)`, `len(common_timezones)`, `country_timezones("nz")`; a pickle round trip; a pandas `Timestamp` with a pytz zone and its `tz_convert`.
- **`terminal_text`:** rich on `Console(record=True, width=80, force_terminal=True, color_system="truecolor", file=io.StringIO())`: a `Table`, a `Panel`, a `Tree`, `Markdown` (through markdown-it-py), `Syntax` (through Pygments) and `pretty`; `export_text()`, `export_html(inline_styles=True)` and `export_svg(unique_id="job")`. markdown-it-py's `MarkdownIt("commonmark").render` and its tokens; mdurl's `parse`, `encode` and `decode`; Pygments' `highlight` with `HtmlFormatter` and `TerminalFormatter`, and `guess_lexer`.
- **`fake_data`:** `Faker.seed(4321)`; names, addresses, e-mails, `pydict` and `date_between_dates` with fixed dates (never a date relative to today) for `en_US`, `de_DE`, `ja_JP` and a two-locale `Faker`; `unique.random_int`; the locale count and provider list.
- **`web_maps`:** a `folium.Map` with a `Marker`, a `CircleMarker`, a `GeoJson` of a dict, a `Choropleth` of a pandas frame, a branca linear colormap, `LayerControl` and `plugins.MarkerCluster`; `get_root().render()` and `_repr_html_()`, each element id (`uuid4().hex`) replaced by a fixed token as `labelled_arrays` does; `branca.utilities.color_brewer("YlGn", 6)`; xyzservices' `CartoDB.Positron.build_url()` and `len(flatten())`.

Guest checks in `tests/checks/test_v1_3_default_profile.py`, each seen failing first on a set without its package:

- `test_folium_names_what_the_set_lacks`: `import folium` works and `requests` is not in `sys.modules`; `GeoJson("https://example.invalid/a.json")` raises `ModuleNotFoundError` naming `requests`.
- `test_rich_refreshes_without_a_thread`: `track(range(3))` raises `RuntimeError` naming the thread; `Progress(auto_refresh=False)` advances and renders.
- `test_pytz_first_zone_is_bounded` (Decision 2).

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
| xyzservices | 8 | 60 KB |
| **all** | **1,949** | **about 5.97 MB** |

INFERRED: each module compiled with the host's Python 3.13 and deflated at level 9, with each member's header, by a scratch script; step 70's own measure, under the line's 3.15.2, is the number. The METADATA, `top_level.txt` and `entry_points.txt` members add a few dozen. The wheel grows by about the same, far under `PYPI_FILE_LIMIT` (268,435,456). Since 175, a plain start parses only a folder's own `__init__` entry, about 9 fuel a padding member (175's landing notes, EXECUTED there; `make_stdlib_zip.py:403`), so nine folders cost a start little. The builder records, per pull request, the zip's and the wheel's bytes, both starts, each package's import and each job's fuel, and the news file claims each growth.

## Intent

A program in the guest renders terminal text with rich, fakes data with Faker, draws a web map with folium and, if its cost holds, uses pytz, with native's output. What cannot work here raises a named error.

## Design

Four pull requests, in the roadmap's order, so a slip cuts from the bottom: pytz (with Decision 2's measure), rich with markdown-it-py, mdurl and Pygments, Faker (with Decision 7), folium with branca and xyzservices. Each carries its own news file and review, `191-<part>` (`191-pytz`, `191-rich`, `191-faker`, `191-folium`).

- Recipe: `scripts/00_download.sh` and `downloads/SHA256SUMS` (the pins, a `tests` line for each test source); `scripts/steps/70_zip.sh` (seven `--wheel` lines; folium's and branca's trees staged, the stand-in, `--drop folium/templates`); `scripts/assemble_artifacts.py`; `recipes/snapshot-packages.txt` (`pytz: pytz`, `rich: rich rich.console rich.table rich.markdown rich.syntax`, `markdown-it-py: markdown_it`, `mdurl: mdurl`, `pygments: pygments pygments.lexers pygments.formatters`, `faker: faker`, `folium: folium folium.plugins`, `branca: branca branca.colormap branca.element`, `xyzservices: xyzservices xyzservices.providers`).
- Patches: `recipes/patches/folium-0.20.0/`, `recipes/patches/branca-0.8.2/`, each with its draft; `tests/harness/pins.py` (`SOURCE_PATTERNS`), `tests/harness/needs.py` (`SOURCE_COMPONENTS`), and the zero-patch count in `release.yml`, two more trees.
- Judge: the nine families, their `.ini`, `packages.toml`, `PURE_SUITES`, `tests/release_shards.toml`, `kit-extra.txt`; Decision 7's driver arguments and unit row; the four jobs with their `.expected`, `tests/harness/jobs.py`, the oracle; the three guest checks; `tests/harness/paths.py` (`LICENCE_COMPONENTS`, `PACKAGES`); `tests/unit/test_artifact_rules.py`'s synthetic set; the bound of The owner's choices, 4.
- Documents: `docs/reference/packages.md` (rows; line 83's pytz advice goes if pytz ships); `docs/reference/limitations.md` (rich's refresh; folium's URL `GeoJson`, a map's CDN scripts; line 51's "No pytz" goes if it ships); `docs/reference/guest-filesystem.md:102`, `docs/how-to/grants.md:89` and `docs/how-to/troubleshooting.md:118`, whose `pytz` example becomes a package the set still lacks.
- The news files' Upgrading entries: a program that brought its own pytz, rich, Pygments, Faker or folium through `import_path=` now gets the runtime's, since the runtime's modules come first (`docs/how-to/grants.md:89`); and pandas now imports pytz when it is there.

## Scope

In: Decisions 1 to 10, in the four pull requests of Design. Out: jsonschema, referencing, jsonschema-specifications, rpds-py, altair, python-calamine and wordcloud (Decision 1); requests and its dependencies (on the default of The owner's choices, 2); a mirror for the tag archives unless the owner asks.

## Acceptance criteria

1. The licences of The owner's choices, 1, are approved in `../decisions.md` before the first pull request is built, and the builder's sweep is in each pull request's landing notes, any notice beyond Decision 6 asked first.
2. Every pin's SHA-256 matches PyPI's or, for a tag archive, the bytes recorded at its first fetch (EXECUTED).
3. Decision 2's numbers are recorded from a `citest:full` run; `test_pytz_first_zone_is_bounded` passes, or pytz is cut and its pull request says so.
4. The zip's names differ from the base set's by exactly the computed additions, none under `folium/templates/`; folium's and branca's trees are their sdists plus their patches and the stand-in (the build shard).
5. The four golden jobs match native (`tests/jobs/regen.py --check`, and their checks in the guest).
6. The guest checks of Decision 9 are seen failing first and pass on both binaries; Decision 7's unit row is seen failing first.
7. The nine families pass in their tiers with their surveyed classes; no family but Faker's imports Faker; every growth is claimed.
8. The bytes and fuel of Decision 10 are recorded per pull request (EXECUTED).
9. The fast tier, `tests/lint` and each pull request's `ci-status` are green.

## The owner's choices

1. **The licences (§4.12).** Default: approve, each shipped with its notice: pytz (MIT); rich (MIT, with cli-spinners' MIT); markdown-it-py (MIT, with markdown-it's and punycode.js's MIT); mdurl (MIT, with Node.js's MIT); Pygments (BSD-2-Clause with its AUTHORS, its Robot Framework lexer under Apache-2.0, its Solarized style MIT); Faker (MIT, with randomcolor-py's MIT); folium (MIT); branca (MIT); xyzservices (BSD-3-Clause, with leaflet-providers' BSD-2-Clause). Alternative: approve part by part, and the parts not approved wait.
2. **folium's `requests`.** Default: the carried patch of Decision 5; a `GeoJson` given a URL names `requests`. Alternative: ship requests 2.34.2 with urllib3 2.8.0, idna 3.20 and certifi 2026.10.23 (Apache-2.0, MIT, BSD-3-Clause, MPL-2.0; four more licences, about 0.4 MB). Even then `import requests` needs a writable temporary folder, since `requests/utils.py:82` calls `certifi.where()` at import, which copies its bundle out of the zip through `importlib.resources.as_file` (READ; 035 says `as_file` needs one), and the guest has no network.
3. **pytz's line.** Default: the four bounds of Decision 2. Alternatives: ship pytz whatever the numbers, which are recorded; or keep decision 47 now and measure nothing.
4. **The smoke total.** Default: `SMOKE_TOTAL_BOUND` from 1.2 T to 1.4 T, a judge change whose comment names these nine families, as the cairo families' raise did. Alternative: the bound stays, and the heaviest smoke files move to the release tier by path.

## Landing notes

Not built.
