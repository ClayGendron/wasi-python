# Trimming fontTools is a small lever on plain start

- **Status:** executed, 2026-10-17.
- **Owner:** Clay Gendron
- **Researcher:** the author agent (Claude Opus 5.5).
- **Feeds:** spec 023's Scope ("trimming fontTools … measured against Decision 6's plain-start cost"); the next matplotlib specification.
- **Stands on:** spec 023's pre-build review (about 76,490 instructions per zip member on every plain start, EXECUTED there), the research zip of `2026-10-17-matplotlib-on-the-current-line.md`.

## The question

matplotlib brings fontTools into the stdlib zip: 343 members of the research zip's 681 new ones. zipimport reads the whole central directory at every plain start, so each member costs every plain call. How many could go?

## What matplotlib imports (EXECUTED, native)

`trace.py` (in this memo's folder) runs natively under Python 3.15.0 with matplotlib 3.11.2 and its pinned dependencies, `MPL_IGNORE_SYSTEM_FONTS=1`, and saves one figure (text in three families, mathtext in DejaVu and STIX, a legend) as PNG, PDF, PS, EPS and SVG, with Type 3 and Type 42 fonts, SVG text as paths and as text, and through `PdfPages`. Then it lists every `fontTools` module loaded: 142 (`modules.txt`).

PDF and PS font subsetting (`fontTools.subset`) reaches far: `varLib` (11 modules), `feaLib` (5), `otlLib` (6), `designspaceLib` (4), `colorLib` (6), `cffLib`, `pens` (7), `misc` (26) and `ttLib` (60). `ttLib`'s table modules load by name per table a font holds, so a font not traced here can need any of them.

## What a safe trim drops (EXECUTED, the research zip's listing)

A trim that is safe without a per-module audit keeps every subpackage the trace touches whole, and `ttLib` whole. It drops the subpackages and top-level modules never imported: `cu2qu`, `diff`, `merge`, `mtiLib`, `qu2cu`, `svgLib`, `ufoLib`, `voltLib`, `afmLib`, `fontBuilder`, `help`, `t1Lib`, `tfmLib`, `ttx`, `annotations` and `__main__`: **58 members** of 343.

At the review's 76,490 instructions per member that is about 4.4 M fuel per plain start (INFERRED), 1.8% of today's plain `-c pass` (241.46 M) and a tenth of the 47 M that spec 023's Decision 6 expects matplotlib's set to add.

Dropping the unimported modules inside the kept subpackages (about 140 more members) would need an audit of every lazy import in `subset`, `varLib` and `ttLib`, and would break on fonts or options not traced. Not worth it for this gain.

## What it decides

- fontTools stays whole in matplotlib's first milestone, as spec 023 says. A trim, if ever made, is the 58-member list above, with this trace as its check.
- The lever on plain start is the per-member cost itself (about 76,000 instructions to read one central-directory entry, in zipimport's Python code under the interpreter), not the member count of one package. That is a separate question for a later memo; the snapshot, which already holds the directory, is unaffected (+2.0% with the whole set).

## One line

A safe fontTools trim saves 58 of 343 members, about 1.8% of a plain start; it is not worth a specification on its own.
