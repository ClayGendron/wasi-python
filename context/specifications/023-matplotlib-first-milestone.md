# 023 — matplotlib, the first milestone

- **Status:** drafted 2026-10-17, awaiting its pre-build review. It builds only after the owner
  answers question 35 (the pybind11 and cppy licences, §4.12).
- **Owner:** Clay Gendron
- **Kind:** the build recipe (pins, a new step for the plot libraries, a new step for the plot
  packages, steps 60 and 70, `scripts/wasi-cc`), one carried patch, the runner (a second runtime
  grant: matplotlib's data), judge additions, `README.md`, `CHANGELOG.md`, `LICENSES/`.
- **Depends on:** 017 (typed grants, the zip folder), 020 (carried patches), 021 (the first
  carried patch, landing first); the owner's answers to questions 2 (matplotlib's data as a
  read-only grant), 35 (licences) and 36 (upstream).
- **Research it stands on:** `../research/2026-10-17-matplotlib-on-the-current-line.md` (the whole
  set built and run in scratch, pixel-equal to native; its "ordered steps" and "new pins" are this
  specification's base), `../research/2026-10-16-what-matplotlib-needs.md`,
  `../research/2026-10-16-where-package-data-lives.md`.

## The problem

matplotlib is first on §2's list after v1. Agents plot, and a plot saved to a file is the most
common thing their code makes that is not text. The research built matplotlib 3.11.2 and its
native stack for wasm32-wasip1 and matched native output pixel for pixel; this specification
brings the first, smallest useful part of that into the build.

## Decisions

1. **The milestone (M1).** `import matplotlib; matplotlib.use("agg")`, `plt.plot(...)`, `savefig`
   to PNG in a granted folder, with the RGBA buffer equal to native's. Built in: the five C
   libraries (FreeType, HarfBuzz, SheenBidi, libraqm, qhull; qhull because matplotlib's configure
   requires it); matplotlib's `ft2font`, `_path`, `_image`, `_backend_agg`, `_c_internal_utils`,
   `_tri` and `_qhull`; kiwisolver; Pillow's `_imaging`, `_imagingmath` and `_imagingmorph`
   (zlib only); and cycler, pyparsing, packaging and fonttools in the zip. Triangulation
   (`matplotlib.tri`'s `_qhull` path, which needs the second patch) and contourpy are known gaps
   in `tests/known_gaps.toml`, each naming the specification that closes it (M2).
2. **The versions and pins** are the memo's "new pins", each a URL and SHA-256 in
   `downloads/SHA256SUMS`. FreeType 2.14.3, HarfBuzz 14.1.0 and libraqm 0.10.5 are held at
   matplotlib's own wrap versions, because those give native pixel parity; qhull's URL is GitHub's
   archive. The three `pkgconf` wheels (one per build host, a build tool only) are checked against
   their bytes when first downloaded; the memo took their hashes from PyPI's JSON. setuptools,
   setuptools_scm and meson-python are not pinned: small stand-ins under `recipes/` take their
   place, as the memo's build did.
3. **One carried patch:** `recipes/patches/matplotlib-3.11.2/0001-…`, matplotlib's own fix
   (PR #30291, merged for 3.12): `ft2font`'s enums no longer touch Python during static
   initialization, which hangs `_initialize` before Python starts. Its commit applies to 3.11.2
   only with offsets, so it is re-made against the pinned tarball (spec 020 refuses offsets). Its
   pull request draft records that upstream has merged it, `Status: merged <url>`, and the
   patch goes when the pin moves to a release that carries it.
4. **The build.**
   - **A new step 37, the plot libraries**, after step 35: FreeType, HarfBuzz, SheenBidi,
     libraqm and qhull, each from its pinned source, with the flags the memo lists (C:
     `-fwasm-exceptions -mllvm -wasm-enable-sjlj -mllvm -wasm-use-legacy-eh=false`; C++:
     `-fwasm-exceptions -mllvm -wasm-use-legacy-eh=false`; `-ffile-prefix-map` everywhere), each
     tree unpacked, patched (none today) and judged as spec 020 does.
   - **`scripts/wasi-cc` drops `-pthread`.** It would add the `+atomics` feature, a new host
     requirement; numpy and pandas never pass it (EXECUTED by the memo), so their bytes do not
     change.
   - **A new step 55, the plot packages**, after step 50: Pillow and kiwisolver compiled directly
     from their source lists against step 30's zlib; matplotlib (patched) with meson
     (`-Dsystem-freetype=true -Dsystem-libraqm=true -Dsystem-qhull=true -DrcParams-backend=Agg
     -Db_lto=false -Dmacosx=false`, the pinned `pkgconf`, pybind11's `pkgconfig` folder, the
     `setuptools_scm` stand-in), installed with `--tags python-runtime,data` and
     `-Dpython.bytecompile=-1`.
   - **Step 60** takes the inittab names from the install paths, honours `-l`/`-L` lines in
     `.deps` (qhull), adds `-lsetjmp`, and leaves `_tkagg` out.
   - **Step 70** packs the new trees and wheels, `matplotlib/mpl-data/` as plain members, and
     skips fontTools' `.data/`.
   - **Step 80 is unchanged in M1:** matplotlib is not pre-imported. Whether the default snapshot
     pre-imports it is question 34; this specification neither needs nor decides it.
5. **matplotlib's data is a second runtime grant.** matplotlib finds its data only at
   `Path(__file__).with_name("mpl-data")`, which with its code in the zip is
   `/usr/local/lib/python315.zip/matplotlib/mpl-data` (memo finding 3). So:
   - the data travels inside the stdlib zip, as plain members (the artifact set keeps its shape,
     §4.6; the zip's `MANIFEST` pairing covers it);
   - the runner extracts `matplotlib/mpl-data/` once per process into its zip folder (spec 017's
     private, locked folder, swept like it), checks each extracted file against the zip's member
     (size and CRC-32), records the stamps, and re-extracts on a change, as it re-copies the zip;
   - on every call it grants that folder read-only at that guest path, after the zip's own grant,
     with spec 017's identity check; a zip with no `matplotlib/mpl-data/` member gives no grant;
   - the README's embedder contract gains one line: for matplotlib, preopen the data folder
     read-only at that path.
6. **The font cache.** On the plain reactor, and on the snapshot while matplotlib is not
   pre-imported, each call with a fresh `HOME` rebuilds matplotlib's font list (about 2.0 G fuel,
   EXECUTED by the memo). With no writable `/tmp` (`root=False` and no writable grant there),
   `import matplotlib` raises `OSError`. The README says both, and that an embedder can set
   `MPLCONFIGDIR` to a writable grant to keep the cache between calls; the runner sets nothing.
7. **The checks**, each seen failing first:
   - v1.3, the milestone: a fixed plot program's RGBA buffer hash equals the native golden's
     (`eab6d61b37105e98` for the memo's program, recorded as a golden with how it was made), and
     its PNG's decoded pixels equal the golden's;
   - v1.3, `savefig(dpi=-1)` raises `ValueError`, and a kiwisolver error reaches Python;
   - v1.2, the data grant refuses writes (`EPERM`), and a program that does not import
     matplotlib behaves as before;
   - v1.1, `python.wasm`'s `target_features` has no `+atomics`; its imports are still WASI
     preview1 and the door;
   - v1.4, the plain reactor's `-c pass` exits 0: a C++ static constructor that calls Python
     would hang it (the failure patch 1 fixes);
   - the known gaps name their closer.
8. **Licences.** `LICENSES/` gains FreeType's (the FTL), HarfBuzz's, SheenBidi's (Apache-2.0),
   libraqm's, qhull's, matplotlib's, kiwisolver's, Pillow's (HPND), contourpy's (not built in M1),
   the fonts' (OFL, Bitstream Vera, BaKoMa), pybind11's and cppy's (BSD-3-Clause), and those of
   the four pure packages, each with its notice, as the owner approved on 2026-10-16 and question
   35 extends.

## Intent

An agent's code makes a line plot and saves it as a PNG in a granted folder, inside the same
sealed Python, and the image is the one native matplotlib makes.

## Design

```
downloads/SHA256SUMS, scripts/line.conf           the pins
scripts/steps/37_plot_libs.sh                     FreeType, HarfBuzz, SheenBidi, libraqm, qhull
scripts/steps/55_plot_packages.sh                 Pillow, kiwisolver, matplotlib
scripts/steps/60_link.sh, 70_zip.sh, wasi-cc      as Decision 4
recipes/                                          the stand-ins and cross files
recipes/patches/matplotlib-3.11.2/0001-…patch      Decision 3; its draft under context/upstream/
src/wasi_python/runner.py                          the data folder and its grant (Decision 5)
tests/checks/…, tests/known_gaps.toml, tests/goldens/…
README.md, CHANGELOG.md, the licence notices
```

## Scope

In: M1. Out:
- Triangulation and contourpy, with the second patch (`_qhull` without a writable `/dev/null`) and
  its new upstream pull request: the next specification (M2).
- Pre-importing matplotlib in the snapshot: question 34.
- Other backends (SVG and PDF save work through Agg's siblings in M1 only as far as they need no
  new native code; their goldens come with M2).

## Acceptance criteria

1. The checks exist and were seen failing first.
2. A full build from pins in a clean clone applies the patch, builds every new step, and makes a
   set whose binaries run the milestone; `MANIFEST` names every new pin and recipe.
3. The same-bytes rebuild on arm64 Linux gives the same `SHA256SUMS` (spec 012), so the release
   gate holds; if a new library's build differs by host, it is fixed or the difference is
   recorded and the gate's handling decided before landing.
4. `uv run pytest` is green with `--accept-judge` and `--accept-growth` (the set grows: the memo
   measured `python.wasm` +19.7% and the zip +6.5 MB with the data).
5. A release dry run passes every job.

## Landing notes

Not built.
