- **Project:** qhull (https://github.com/qhull/qhull)
- **Against:** 8.0.2 (the pinned tarball)
- **Status:** merged https://github.com/qhull/qhull/pull/143
- **Title:** Fix arguments inconsistent with their format strings
- **Files:** src/libqhull_r/poly2_r.c
- **Why we carry it:** scipy 1.18.1 compiles its vendored qhull with this hunk (its `subprojects/qhull_r/patches/poly2rc.patch`, a security scanner's finding); spec 037 links step 37's qhull in its place, the one matplotlib's `_qhull` links (spec 043), so the shared qhull carries scipy's fix and scipy's qhull is unchanged.

There is nothing to send. The hunk is upstream's own: the `poly2_r.c` part of qhull's pull request
#143, merged as commit `1b67ec9046d2f6721a6fbdd2fe55adb44ec23c06` (2025-08-07), which no qhull
release carries yet (8.0.2 is the latest). In `qh_initialhull`, the `trace1` message for an
incorrect initial orientation names three values (`%2.2g`, `f%d`, `f%d`) and passed none; the
hunk passes `dist`, `facet->id` and `firstfacet->id`. scipy's patch file is that commit's
`poly2_r.c` diff with its first hunk removed by hand (the hunk the scanner did not flag), and this
patch is the same one hunk, made against the qhull 8.0.2 tarball in `git diff` form so it applies
with no offset. With it, the tarball's `src/libqhull_r/*.c` and `*.h` are byte for byte scipy
1.18.1's `subprojects/qhull_r/libqhull_r/` (EXECUTED, spec 037's stacked rebuild, `diff -r`: only
documentation and build files differ).

The patch is deleted when the qhull pin moves to a release that carries the commit (8.2.0 or
later, as scipy's note says).
