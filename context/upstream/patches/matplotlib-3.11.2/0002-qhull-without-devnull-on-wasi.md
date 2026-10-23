- **Project:** matplotlib (https://github.com/matplotlib/matplotlib)
- **Against:** 3.11.2 (the pinned tarball)
- **Status:** drafted
- **Title:** Hide qhull's messages on WASI without opening /dev/null
- **Files:** src/_qhull_wrapper.cpp
- **Why we carry it:** every Delaunay triangulation (`matplotlib.tri.Triangulation(x, y)` without triangles, so `tricontour`, `tricontourf`, `tripcolor` and `triplot` on bare points) raises `RuntimeError: Could not open devnull` in the guest, because a WASI sandbox has no device files; and where a host grants a writable root with a `dev` folder, opening `/dev/null` for writing creates a real file there.

**This is a facts sheet, not a pull request** (question 80 in `context/decisions.md`). matplotlib's policy on AI, quoted in full below, rules out an agent opening the pull request and asks that its description be in the contributor's own words. So whether to engage at all is your decision. If you do, you write the issue or pull request yourself, from these facts. Nothing has been posted, and no agent will post anything to matplotlib.

When spec 043 is built, this file moves unchanged to `context/upstream/patches/matplotlib-3.11.2/0002-qhull-without-devnull-on-wasi.md`, and `fix.patch` is copied byte for byte to `recipes/patches/matplotlib-3.11.2/0002-qhull-without-devnull-on-wasi.patch`. The project carries it so the guest triangulates (§4.1). Carrying it does not depend on sending anything. The evidence stays in `context/upstream/7-matplotlib-qhull-devnull/evidence/`, so every link below is a path from the repository's top.

## What matplotlib asks of AI tools and contributors

**Its policy**, `doc/devel/contribute.rst`, section "Use of Generative AI", READ in the 3.11.2 sdist and on `main` (`493abb1b63`, 2026-10-18). On `main` it reads, whole:

> Generative AI tools are evolving rapidly and can be helpful. As with any tool, the resulting contribution is the responsibility of the human contributor. We expect dedicated and authentic engagement in our community. In particular when using AI, carefully consider what and how to communicate, question results, think things through thoroughly and make well-informed decisions.
>
> Acceptable uses:
> - Gaining understanding of the existing code
> - Getting solution ideas
> - Translating or proof-reading your comments or PR descriptions. Please keep the wording as close as possible to your original wording.
>
> Unacceptable uses:
> - External AI tooling (e.g. bots, agents) directly interacting with the project; including creating issues, PRs or commenting on GitHub or Discourse.
> - Solving topics that you wouldn't be able to solve yourself without AI
> - Using AI output without ensuring that you fully understand the output or without verifying that it is the correct approach.
> - Increasing breadth of contributions, i.e. simultaneously contributing to several projects. Instead of spreading your resources, you can provide greater value by engaging more deeply with one or two projects.
>
> To ensure project health and preserve limited core developer capacity, we will flag and reject low-value contributions that we believe are AI generated. We may ban and/or report users to GitHub if they harm the project or its community through irresponsible use of AI.

3.11.2's text is the same but for two things: it says "the responsibility of the contributor" (no "human"), and it has no "breadth" item. Three points bear on this sheet:
- an agent must not open the issue or the pull request, and none will;
- "Solving topics that you wouldn't be able to solve yourself without AI" and "fully understand the output" are yours to weigh: the change is 12 lines in one function, explained below line by line;
- the "breadth" item: this project also has drafts waiting for numpy, pandas, networkx and qhull. Whether to send this one, and when, is yours.

**Its pull request template** (`.github/PULL_REQUEST_TEMPLATE.md` on `main`, READ) has three sections: "PR summary" ("Describe what issue is resolved and why you chose this solution in your own words (no AI please)"), "AI Disclosure" ("Describe if and how AI is used"), and "PR quality check" (an expressive title; new and changed code tested; examples; release notes for new features and API changes; documentation guidelines). This change adds no feature and changes no API, so the last two do not apply.

**Other rules** (READ in the 3.11.2 sdist's `doc/devel/`):
- matplotlib does not assign issues; a pull request claims one, and duplicate pull requests may be closed;
- a new contributor finishes their first pull request before opening another;
- no contributor licence agreement is named. Contributed code must be BSD-compatible (`license.rst`); this change is new code;
- `main` has no `AGENTS.md` (READ by spec 043's review: 404).

**Checked for you** (2026-10-17): GitHub's issue search for "devnull qhull" in matplotlib finds nothing about this; the code is unchanged on `main` (`493abb1b63`, line 182 is still `error_file = fopen(STRINGIFY(MPL_DEVNULL), "w");`).

## The facts

**What fails.** `_qhull.delaunay` hides qhull's messages unless Python runs verbose. To hide them it opens `MPL_DEVNULL`, a path `src/meson.build` takes from the cross file's `devnull` property or from `os.devnull` (`src/meson.build:1-13`). If the open fails it throws. On `wasm32-wasip1` there are no device files. A guest sees only the folders its host grants, often none writable, so every Delaunay triangulation fails (tool output, `context/upstream/7-matplotlib-qhull-devnull/evidence/guest-run.txt`, item 1):

```
RuntimeError: Could not open devnull
```

**A second effect.** If the host grants a writable root that has a `dev` folder, the same `fopen("/dev/null", "w")` succeeds and creates, or truncates, a regular file named `null` in the host's folder (item 2). That is a write to the host that no Python code asked for.

**The change** (`fix.patch`, 12 added lines, 0 removed). On WASI, `error_file` is a stream from `fopencookie` whose write function returns the size it is given and stores nothing. No path is opened. On every other platform the `#else` branch is the current line, unchanged. `QhullInfo`'s destructor still `fclose`s the stream, on the error path too; musl's `fopencookie`, which wasi-libc's is, allows a null close function. wasi-sdk 33 declares it in `stdio.h` under `_GNU_SOURCE`, which its C++ compiler defines, and `libc.a` defines it (EXECUTED by spec 043's review).

**How it was tested** (EXECUTED 2026-10-17, item 3 and 4):
- in a WASI build of matplotlib 3.11.2 with the change: collinear points raise qhull's `singular input data` error, through qhull's own `longjmp` error path; four points give two triangles; no file appears in the host folder;
- a program that triangulates 30 seeded points, contours, labels the contours and saves SVG and PDF gives the same triangles, neighbours, contour numbers, SVG bytes and RGBA buffer as native matplotlib 3.11.2 from PyPI (item 4);
- `test_triangulation.py`'s Delaunay tests (`test_delaunay`, `test_delaunay_points_in_line` and others) are what CI would run on WASI; matplotlib's CI has no WASI job, and on the platforms it has, the code is unchanged, so no new test is proposed.

**Alternatives** a reviewer may raise:
- *Write to `stderr` when the open fails.* The guest would print qhull's warnings, unlike any other platform.
- *Try `fopen` first, fall back on failure* (the first form tried). It still makes a host file where a writable `dev` folder exists (item 2).
- *A discard stream on every platform.* Not every platform matplotlib supports has `fopencookie`: macOS has `funopen` instead, and Windows has neither. It would need a branch per C library for a case only WASI has.

**Base.** The change applies to `main` at `493abb1b63` with a 3-line offset (item 5). When you ask, an agent rebases it onto `main` in a scratch clone and hands you the branch and these facts. It never writes the description and never touches GitHub.

**AI disclosure, for you to state.** The change and this sheet were written in Claude Code with Claude Opus 5.5 (`claude-opus-5-5`); the drafting session did not record its reasoning level.
