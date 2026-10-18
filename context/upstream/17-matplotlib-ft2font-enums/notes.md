# matplotlib's ft2font enums: carried until 3.12 (spec 023)

Nothing to send: upstream merged the fix. This sheet records how the carried patch was made and
checked, for the owner and for the day the pin moves.

- **The symptom** (the research memo `2026-10-17-matplotlib-on-the-current-line.md`, finding 5,
  EXECUTED there): linked statically into the reactor, matplotlib 3.11.2's `ft2font` hung
  `_initialize` before Python started. `src/_enums.h`'s `P11X_DECLARE_ENUM` defines namespace-scope
  constants whose initializers take the GIL (`py::gil_scoped_acquire`) and call
  `pybind11::cast`; in a shared library they run at `dlopen`, after Python is up, but in a static
  link they run in the constructor pass, before `Py_Initialize`, and wait forever.
- **Upstream's fix:** pull request #30291, "Migrate to Pybind11 v3"
  (<https://github.com/matplotlib/matplotlib/pull/30291>), merged 2026-07-24 for 3.12.0; commit
  `8e5591bcb3163d88bd9900ae74fc043c080aa631` deletes `_enums.h` and binds the enums with
  `py::native_enum` inside module initialization.
- **The carried file** (`recipes/patches/matplotlib-3.11.2/0001-ft2font-enums-without-python.patch`):
  the commit applied to the 3.11.2 tarball in a scratch repository (`git apply` took offsets of 24
  and 188 lines) and taken back with `git diff`, so the build's applier, which refuses offsets,
  applies it cleanly. Spec 023's build re-made it so and found it byte-identical to the file its
  pre-build review had re-made (EXECUTED, `diff`); the review found its changed lines equal the
  commit's in all four files. It keeps the commit's `ci/mypy-stubtest-allowlist.txt` lines, so it
  is the merged commit whole.
- **The guard:** `tests/harness/constructors.py` lists the static constructors `__wasm_call_ctors`
  calls in `python.wasm`, compared with a reviewed list; step 60 runs it after every link and the
  judge runs it on the artifact set. Without the patch the build's step 60 stops, naming
  `_GLOBAL__sub_I_ft2font_wrapper.cpp` (EXECUTED by spec 023's build; its landing notes).
- **When to delete it:** when the pin moves to matplotlib 3.12.0 or later; its draft's status
  then becomes `released 3.12.0`, which the judge refuses while the patch stays.
