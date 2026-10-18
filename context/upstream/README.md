# Upstream fixes, waiting for the owner

Drafts of changes this project needs from its dependencies. Nothing here is posted: the owner
reviews each text and posts it (constitution §4.1, a needed source change goes upstream first).
The issue texts and a reading guide are in the owner's "Upstream issue drafts" doc.

| folder | where | what | state |
|---|---|---|---|
| `1-wasmtime-py-last-exception/` | wasmtime-py | `LAST_EXCEPTION` per thread: one thread's host exception is never raised by another thread's call | PR ready (`pr.md`, `fix.patch`, evidence) |
| `2-wasmtime-py-sigint/` | wasmtime-py | component host functions catch `BaseException`; Ctrl-C at a callback's entry | PR ready for the first; `memo.md` and a prototype for the second, which has no sound fix inside wasmtime-py |
| `3-numpy-npy-wasi/` | numpy | `np.save` and `np.load` on WASI, where `os.dup` is unsupported | patch and facts; numpy's AI policy requires the owner to write the description |
| `5-pandas-styler-from-a-zip/` | pandas | the Styler's templates when pandas is imported from a zip archive | patch and facts for spec 041; pandas' policy asks the owner to write the description |
| `6-networkx-atlas-from-a-zip/` | networkx | the graph atlas when networkx is imported from a zip archive | patch, test and facts for spec 041; networkx's policy asks the owner to write the description |

Each patch is against the base named in its `pr.md`. `notes.md` in each folder records how the
fix was found and checked. When a fix lands upstream and a pin moves past it, record that here
and in the CHANGELOG, and drop any workaround in the runner.

## Pull requests for carried patches

Since §4.1's amendment (question 32), a fix the project cannot wait for is carried as a patch
under `recipes/patches/<top>/` (specification 020). Its pull request lives here, at
`patches/<top>/NNNN-<slug>.md`, the same name as the patch, starting with six header lines:

```
- **Project:** <name> (<repository URL>)
- **Against:** <version> (the pinned tarball)
- **Status:** drafted | sent <url> | merged <url> | released <version, as the pinned file name writes it>
- **Title:** <the pull request's title>
- **Files:** <every path the patch touches, comma-separated>
- **Why we carry it:** <what fails without it, in this project>
```

The body is the text for the upstream maintainers, and says whether the project needs a
contributor licence agreement, which the owner signs. The owner sends it; then the status records
the link. Where a project forbids AI-written pull request descriptions (numpy does), the draft's body is the facts for the owner to write from, not the text. A draft is not a build input, so recording the status changes no `MANIFEST` line.
