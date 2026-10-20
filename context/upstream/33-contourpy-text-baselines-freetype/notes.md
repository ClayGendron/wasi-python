# contourpy: the `--runtext` baselines of `test_config.py` fail at FreeType 2.14.3

Facts only (spec 066); nothing is drafted to send. The owner decides whether to report.

- **What runs.** contourpy 1.4.0's `tests/test_config.py` with `--runtext`: `test_config_filled*`
  and `test_config_lines*` with `show_text=True` compare rendered figures against
  `tests/baseline_images/*.png` with contourpy's thresholds (max 100, mean 0.02).
- **In the guest** (matplotlib 3.11.2, FreeType 2.14.3; contourpy's own `image_diffs.log`, spec
  066's rebuild, EXECUTED): 17 of the 18 `show_text=True` cases fail, max 255 and mean 3.5 to 8.4.
  The same figures without text pass (max at most 52, mean at most 0.0003). The image differs in
  the glyph shapes of the corner labels and titles, nothing else.
- **On native** (the repo's oracle, matplotlib 3.11.2 with FreeType 2.14.3, darwin-arm64; spec
  066's confirming review, EXECUTED): `ConfigFilled` and `ConfigLines` with text fail the same
  way, max 255, mean 4.77 to 6.46; without text they pass (max 0 to 52, mean at most 0.0005).
- **So** contourpy's text baselines belong to the FreeType its own CI pins, not to the product.
  contourpy's CI runs `--runtext` on one pinned configuration.
- **The gap it closes.** `tests/upstream/expected/contourpy-config-1/text-rendering.txt`, 17
  members. New baselines upstream, or a FreeType pin that matches them, empty the class.
