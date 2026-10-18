- **Project:** networkx (https://github.com/networkx/networkx)
- **Against:** 3.7 (the pinned tarball)
- **Status:** drafted
- **Title:** Read the graph atlas through its resource's file object, so it works from a zip archive
- **Files:** networkx/generators/atlas.py, networkx/generators/tests/test_atlas.py
- **Why we carry it:** `nx.graph_atlas` and `nx.graph_atlas_g` raise `TypeError: filename must be a str or bytes object, or a file` in the guest, because networkx is read from the stdlib zip and `gzip.open` is given a `Traversable`, not a path.

This draft is not the pull request's description. networkx's contributor guide
(*Automated Contributions Policy*, READ 2026-10-17 at
`https://networkx.org/documentation/latest/developer/contribute.html`) says: "Please do not paste
AI generated text in the description of issues, PRs or in comments", "Do not submit any
AI-generated code that you haven't personally reviewed, understood and tested", and "If you used
AI tools, please state so in your PR description." So the owner writes the description from the
facts below, after reviewing and testing the change, and states that an agent (Claude Opus 5.5,
in Claude Code) wrote it.

When this patch is built (spec 041), this file moves, unchanged, to
`context/upstream/patches/networkx-3.7/0001-graph-atlas-from-a-zip.md`, and `fix.patch` is copied,
byte for byte, to `recipes/patches/networkx-3.7/0001-graph-atlas-from-a-zip.patch`.

## The facts, for the owner to write from

**What fails.** With networkx imported from a zip archive, `graph_atlas(i)` and `graph_atlas_g()`
raise:

```
  File ".../networkx/generators/atlas.py", line 63, in _generate_graphs
    with gzip.open(ATLAS_FILE, "rb") as f:
TypeError: filename must be a str or bytes object, or a file
```

It reproduces on any CPython with the stock wheel on `PYTHONPATH`, since a wheel is a zip that
zipimport reads (`evidence/networkx-native.txt`, EXECUTED on CPython 3.15.0 with networkx 3.7):

```
PYTHONPATH=networkx-3.7-py3-none-any.whl python -c "import networkx as nx; nx.graph_atlas(6)"
```

**Why.** `ATLAS_FILE = importlib.resources.files("networkx.generators") / "atlas.dat.gz"` is a
`pathlib.Path` only when networkx is installed as files. From a zip archive it is a
`zipfile.Path` (or another `Traversable`), which has no `__fspath__` and no `read`, so
`gzip.open` refuses it.

**The change** (one line, plus a two-line comment): open the resource through its own `open`
and give `gzip.open` the file object.

```python
    with ATLAS_FILE.open("rb") as raw, gzip.open(raw, "rb") as f:
```

`Traversable.open("rb")` is part of the `importlib.resources` API, so this works for a path and for
any resource reader. `ATLAS_FILE` keeps its value and type. Its comment above calls it "the
absolute path" of the file; the maintainers may want that worded as "the resource" too.

**The test** (in the patch): `test_atlas_file_in_a_zip` writes `atlas.dat.gz` into a zip under
`tmp_path`, points `atlas.ATLAS_FILE` at a `zipfile.Path` in it with `monkeypatch`, and checks
`graph_atlas(6)` as `test_graph` does. Without the fix it fails with the `TypeError`; with it, the
file's 9 tests pass, and `networkx/generators/tests` gives 598 passed and 34 skipped
(`evidence/networkx-native.txt`, EXECUTED with pytest 8.4.2 on a CPython 3.15.0a3).

**Also tested** in a statically linked CPython 3.15.0 for `wasm32-wasip1` whose packages are one
zip: `graph_atlas(100)` and `graph_atlas_g()` give results equal to native CPython 3.15.0 with
networkx installed normally (`evidence/guest-run.txt`, EXECUTED 2026-10-17).

**What networkx asks for besides the code.** No contributor licence agreement and no changelog
entry are asked for (READ, the same guide); a link to an issue is welcome ("Fixes #…"). The agent
rebases the change onto networkx's `main` in a scratch clone when the owner asks to send it.
`main` has the same lines as 3.7 (READ 2026-10-17).
