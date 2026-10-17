# Upstream fixes, waiting for the owner

Drafts of changes this project needs from its dependencies. Nothing here is posted: the owner
reviews each text and posts it (constitution §4.1, a needed source change goes upstream first).
The issue texts and a reading guide are in the owner's "Upstream issue drafts" doc.

| folder | where | what | state |
|---|---|---|---|
| `1-wasmtime-py-last-exception/` | wasmtime-py | `LAST_EXCEPTION` per thread: one thread's host exception is never raised by another thread's call | PR ready (`pr.md`, `fix.patch`, evidence) |
| `2-wasmtime-py-sigint/` | wasmtime-py | component host functions catch `BaseException`; Ctrl-C at a callback's entry | PR ready for the first; `memo.md` and a prototype for the second, which has no sound fix inside wasmtime-py |
| `3-numpy-npy-wasi/` | numpy | `np.save` and `np.load` on WASI, where `os.dup` is unsupported | patch and facts; numpy's AI policy requires the owner to write the description |

Each patch is against the base named in its `pr.md`. `notes.md` in each folder records how the
fix was found and checked. When a fix lands upstream and a pin moves past it, record that here
and in the CHANGELOG, and drop any workaround in the runner.
