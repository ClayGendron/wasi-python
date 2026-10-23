# The README banner

- **Status:** research, 2026-10-22. A record of how `docs/assets/wasi-python*.svg` were made, so they can be remade.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Fable 5.1), at the owner's request for a large central "WASI-PYTHON" in IBM Plex Sans at the top of the README.

## Labels

A claim carries READ (seen in a file or source), EXECUTED (run and observed) or INFERRED (reasoned, not run).

## What was made

Three SVG files under `docs/assets/`, each the text "WASI-PYTHON" in IBM Plex Sans Bold with every glyph converted to an outline path, so nothing loads a font when the page is viewed:

| file | fill |
|---|---|
| `wasi-python.svg` | follows the viewer's colour scheme through a media query inside the SVG |
| `wasi-python-light.svg` | dark text for a light page |
| `wasi-python-dark.svg` | light text for a dark page |

The README shows them through a `<picture>` element with one `<source>` per scheme and the first file as the `<img>` fallback. GitHub maps `prefers-color-scheme` sources to its own theme; PyPI's renderer keeps only the `<img>`, whose media query then follows the browser. Every URL is absolute, since the README is also the wheel's description.

## How

`make_banner.py` beside this memo shapes the text with HarfBuzz (kerning on), draws each glyph through fontTools' SVG path pen, flips and scales the outlines to pixels, and writes one `<g>` of paths. It was run as

```
uv run --no-project --with fonttools --with uharfbuzz python -I make_banner.py \
  ~/Library/Fonts/IBMPlexSans-Bold.ttf "WASI-PYTHON" wasi-python.svg 160 20
```

(size 160 px, 20 font units of tracking). The light and dark variants were made from it by editing the one `fill` rule and dropping the media query.

The font files came from the owner's machine (`~/Library/Fonts`). IBM Plex is published under the SIL Open Font License 1.1 (READ: the licence text shipped with the font), which licenses the font software; an outline drawn from it into an image carries no font and is not covered by the Reserved Font Name clause. No font file is in the repository.

## Checked

EXECUTED: rendered in headless Chrome on a white and a dark background and in Quick Look: the glyph shapes, kerning and the hyphen's weight are IBM Plex Sans Bold's. EXECUTED: the judge's README checks pass with the new README (`tests/checks/test_rules.py`, `tests/checks/test_v1_4_public_api.py`, the default-integer and `-V` checks), and `mkdocs build --strict` copies the assets into the site.
