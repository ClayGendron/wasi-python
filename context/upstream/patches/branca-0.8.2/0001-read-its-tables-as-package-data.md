- **Project:** branca (https://github.com/python-visualization/branca)
- **Against:** 0.8.2 (the pinned sdist, `branca-0.8.2.tar.gz`)
- **Status:** drafted
- **Title:** Read the colour tables through the package's loader, so branca imports from a zip
- **Files:** branca/colormap.py, branca/utilities.py
- **Why we carry it:** the guest imports branca from its stdlib zip, and branca opens its JSON tables by a path built from `__file__`, which does not open inside a zip; `branca/colormap.py` does it at import, so `import branca.colormap`, and with it `import folium`, fails.

The patch is `recipes/patches/branca-0.8.2/0001-read-its-tables-as-package-data.patch`, written by specification 191's build (2026-11-15). The owner sends this, or not; nothing has been posted, and no agent will post anything to branca.

## What the project asks of a contributor

The sdist carries no contribution guide (read 2026-11-15); branca is maintained beside folium by the same organization, whose guide asks for a clear pull request that touches only the code the change needs, with the tests run first. Nothing there or here says anything about AI tools. So the route is the pull request below, which says that an AI tool wrote the change, the honest default.

## Related reports

Not searched: this session's GitHub access does not reach the repository. Before sending, search the issues for "zip", "zipimport" and "pkgutil" and cite any that asks the same.

## The pull request

**Title:** Read the colour tables through the package's loader

`branca/colormap.py` reads `_cnames.json` and `_schemes.json` at import with `open(os.path.join(rootpath, …))`, and `utilities.color_brewer` reads `_schemes.json`, `scheme_info.json` and `scheme_base_codes.json` the same way. A path built from `__file__` does not open when the package is imported from a zip (zipapps, frozen and embedded interpreters, WebAssembly runtimes), so `import branca.colormap` raises. The five reads become `json.loads(pkgutil.get_data("branca", name))`, which reads through the package's loader from a folder and from a zip alike. The files are already package data, so packaging does not change. `rootpath` stays, since it is a module attribute others may read.

**Tested** natively on CPython 3.13 (Linux x86_64), with branca and folium imported from a zip: `color_brewer("YlGn", 6)` gives `['#ffffcc', '#d9f0a3', '#addd8e', '#78c679', '#31a354', '#006837']`, and a folium map renders. The project's own suite was not run: its tests are in the repository, not in the sdist, and this session could not fetch the release tag's tree. The change was written with an AI tool (Claude Code, Claude Opus 5.5), and every line was read and run as described here.

## The evidence

EXECUTED on 2026-11-15 in specification 191's build (`context/specifications/191-pytz-rich-faker-and-folium.md`, landing notes): the native run above. In this project's guest, the golden job `web_maps` runs `color_brewer` and a branca colormap from the zip, on the first built set.
