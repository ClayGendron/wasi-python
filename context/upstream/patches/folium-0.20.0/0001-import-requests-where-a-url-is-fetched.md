- **Project:** folium (https://github.com/python-visualization/folium)
- **Against:** 0.20.0 (the pinned sdist, `folium-0.20.0.tar.gz`)
- **Status:** drafted
- **Title:** Import requests only where a GeoJSON URL is fetched, so folium imports without it
- **Files:** folium/features.py
- **Why we carry it:** the guest has no `requests` and no network, and `folium/features.py` imports `requests` at its top, so `import folium` fails with `ModuleNotFoundError` though only `GeoJson.get_geojson_from_web` uses it.

The patch is `recipes/patches/folium-0.20.0/0001-import-requests-where-a-url-is-fetched.patch`, written by specification 191's build (2026-11-15). The owner sends this, or not; nothing has been posted, and no agent will post anything to folium.

## What the project asks of a contributor

Read 2026-11-15 from the sdist's `.github/CONTRIBUTING.md`: fork, branch, install `requirements.txt` and `requirements-dev.txt`, run `pre-commit install` for the linter, run `python -m pytest tests --ignore=tests/selenium` and `python -m pytest tests/selenium`, and open a pull request "easy to review": a clear description, touching only the code the change needs. It says nothing about AI tools. So the route is the pull request below, which says that an AI tool wrote the change, the honest default; an issue first is not asked for.

## Related reports

Not searched: this session's GitHub access does not reach the repository. Before sending, search the issues for `requests` and "optional dependency" and cite any that asks the same.

## The pull request

**Title:** Import requests only where a GeoJSON URL is fetched

`folium/features.py` imports `requests` at module level (line 24), and its one use is `GeoJson.get_geojson_from_web` (line 783), which fetches a GeoJSON given as a URL. The import moves into that method. Nothing else changes: with `requests` installed, a URL is fetched by the same call as before. Without it, `import folium` works and every map renders, and a `GeoJson` given a URL raises `ModuleNotFoundError: No module named 'requests'` when it is made. This helps installs where `requests` is not available or not wanted, such as WebAssembly runtimes and slim containers.

`requests` stays in `requirements.txt`, so nothing changes for anyone installing the package today. A follow-up could make it an extra; this change does not.

**Tested** natively on CPython 3.13 (Linux x86_64), with folium and branca imported from a zip and no `requests` installed: `import folium` leaves `requests` out of `sys.modules`, a map with a marker and a `GeoJson` of a dict renders, and `GeoJson("https://example.invalid/a.json")` raises `ModuleNotFoundError` naming `requests`. The project's own suite was not run: its tests are in the repository, not in the sdist, and this session could not fetch the release tag's tree. The change was written with an AI tool (Claude Code, Claude Opus 5.5), and every line was read and run as described here.

## The evidence

EXECUTED on 2026-11-15 in specification 191's build (`context/specifications/191-pytz-rich-faker-and-folium.md`, landing notes): the native run above. In this project's guest (CPython for `wasm32-wasip1`, folium in its stdlib zip, no `requests`), `test_folium_names_what_the_set_lacks` checks the same, on the first built set.
