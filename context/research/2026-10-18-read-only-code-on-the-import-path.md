# Read-only code on the import path: what it takes, probed on both binaries

- **Status:** research, 2026-10-18. Drafting research for spec 054. No code, test, recipe or download was changed; every probe called today's `wasi_python.run` with an argv the probe built itself.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5). Box: one session, inside the drafting of spec 054.
- **Stands on:** the owner's decisions 16 ("yes, as an explicit read-only typed grant the embedder asks for; never writable, never by default") and 49 (0.1.0 carries it) (`../decisions.md`); `2026-10-17-the-runtime-for-agent-code.md` (§4.1 item 3, §5 item 5, §6 question 4); `2026-10-17-typed-grants.md`; specs 006, 017, 022, 025, 032, 034, 041, 049 and 035 (read in its build worktree, `wasi_python-035`, at `625a4d6`); `recipes/reactor_main.c` and `recipes/reactor_bootstrap.py` (READ, main `62d2c56`).
- **Evidence:** `2026-10-18-read-only-code-on-the-import-path/` beside this memo: `probe.py` (the probes) and `outputs.txt` (one run of it, both binaries); `equal.py` and `equal.txt` (byte equality with and without the prelude); `root_and_mount.py` and `root_and_mount.txt`. Host: arm64 macOS (Darwin 25.5.0), CPython 3.14.2 under uv, wasmtime-py 49.0.0. Artifact set: the main tree's `build/artifacts` (read only): `python-snapshot.wasm` `f94dec53…`, `python.wasm` `5648e4c5…`, `python-stdlib.zip` `daf2cdd8…`.

One idea per sentence. The **import path** is `sys.path`, the list of places Python searches for a module. A **read-only place** is a read-only grant (spec 017) or a read-only mount (spec 032). A **prelude** is a short `-c` program the runner puts before the caller's argv.

## The short version

1. **No guest change is needed.** The runner can put read-only places on the import path by itself. It prepends a one-line `-c` prelude that extends `sys.path` and then re-enters the reactor's own argument handling, `_reactor.run`. Every mode behaves as before: `-c`, `-m`, a script, standard input, `-V`, `-u`, exit codes, `SystemExit` messages and tracebacks (EXECUTED, both binaries). The snapshot froze `sys.path` as a value, not as a rule: a list changed at run time works there as on the plain binary (EXECUTED).
2. **The environment cannot do it.** The interpreter runs isolated: `PYTHONPATH` reaches `os.environ` but not `sys.path` (EXECUTED, both binaries).
3. **Bytecode is never written.** `sys.dont_write_bytecode` is `True` on both binaries, so the loader never tries (EXECUTED). If a program sets it to `False`, the write to a read-only grant fails quietly: the import succeeds, nothing reaches stderr, and the host folder is unchanged (EXECUTED). A valid `.pyc` already in the grant is read (EXECUTED).
4. **Zips work.** A zip file inside a read-only grant, named on the import path, imports; its resources and its `dist-info` metadata read (EXECUTED).
5. **The import path goes after the stdlib zip.** Before it, a package shadows the runtime's own modules on the plain binary but not on the snapshot, which has them already imported (EXECUTED). So the same call would answer differently on the two binaries.
6. **Two writable layouts would break spec 006's guarantee** ("code one run planted never runs in another"). A writable grant whose host folder lies inside the read-only one, and a writable grant whose guest path lies under the entry, both put writable files where an import finds them: in the first a later call imported what an earlier one wrote (EXECUTED); in the second a call imported what it had just written (EXECUTED), which a later call with the same layout would import too (INFERRED). The runner must refuse both.
7. **`importlib.invalidate_caches()` is not needed** for a read-only entry: a file the host adds mid-call is seen without it (EXECUTED). It works, and costs what it costs today.

## 1. How the import path is formed today (READ, EXECUTED)

- `recipes/reactor_main.c`, `init_interpreter`: `PyConfig_InitIsolatedConfig`; `config.write_bytecode = 0`; `config.module_search_paths_set = 1` with one entry, the stdlib zip (`/usr/local/lib/python315.zip`); `config.site_import = 0` (READ). Both binaries run this. The snapshot runs it once at build time inside `wizer.initialize`; the plain binary runs it in `run()` (READ).
- `recipes/reactor_bootstrap.py`, `run(argv, environ)`: clears and refills `os.environ`, parses the reactor's options and runs `-c`, `-m` (through `runpy.run_module`), a script (through `runpy.run_path`) or standard input. It never touches `sys.path` (READ).
- P1 (EXECUTED, both binaries, `env={"PYTHONPATH": "/code"}` and a read-only grant at `/code`): `sys.path == ['/usr/local/lib/python315.zip']`; `sys.flags.isolated == 1`; `sys.flags.no_site == 1`; `sys.dont_write_bytecode is True`; `os.environ['PYTHONPATH'] == '/code'`; `import mylib` raises `ModuleNotFoundError`. `sys.meta_path` is `BuiltinImporter`, `FrozenImporter`, `PathFinder`, and on the snapshot also six's `_SixMetaPathImporter` (pandas imports `dateutil`, which imports six).
- With `root=True`, and with a provider mounted at `/`, `-c` still has `sys.path == ['/usr/local/lib/python315.zip']` with working directory `/`, and the mount's `/evil.py` does not import (EXECUTED, both binaries: `root_and_mount.py`, output in `root_and_mount.txt`). The README's sentence (from spec 034) that "with a writable mount at `/`, a `-c` program has `/`, its working directory, first on `sys.path`" is therefore wrong today. Nothing writable is on the import path in any layout. Spec 054 corrects the sentence.

## 2. The prelude (EXECUTED)

The probe's prelude is one expression statement:

```
__import__('sys').path.extend(ENTRIES) or __import__('sys').exit(__import__('_reactor').run(
    ['/usr/local/bin/python.wasm', *__import__('sys').argv[1:]], dict(__import__('os').environ)))
```

`ENTRIES` is the list's `repr`. The runner's argv becomes `["-c", PRELUDE, *argv]`. The outer `_reactor.run` runs the prelude in `-c` mode, with `sys.argv == ["-c", *argv]`. The prelude extends `sys.path` and calls `_reactor.run` again with the caller's own argv. That inner call parses it as if nothing came before, runs the program, catches its exceptions and returns its exit code. The prelude raises `SystemExit` with that code, and the outer call returns it.

P2, each case run without the prelude and with it, on both binaries (`outputs.txt`):

| case | without | with |
|---|---|---|
| `-c "import mylib …" a1` | `ModuleNotFoundError` | imports; `sys.argv == ['-c', 'a1']`; `sys.path[-1] == '/code'` |
| `-m pkg x y` | `No module named pkg` | runs `pkg/__main__.py`; `sys.argv == ['/code/pkg/__main__.py', 'x', 'y']` |
| script `/code/main.py s1` (imports `mylib`, exits 3) | `ModuleNotFoundError` | runs; exit 3 |
| standard input | — | imports; `sys.argv == ['']` |
| `-V`, `-u -c …`, `sys.exit(7)`, `SystemExit('bye')` | same | same (exit 0, 0, 7, 1 with `bye`) |
| `sys.orig_argv[1:]` | the caller's argv | the same |
| non-dunder names in `__main__` | `[]` | `[]` (the prelude binds none) |
| `-c 1/0`, a script raising in a function | traceback | the same last lines |
| a missing script | exit 2, `can't open file …` | the same |
| `len(traceback.extract_stack())` | 2 | **4** |

- **Byte-equal where it matters.** For `-V`, `-u -c`, `sys.exit(7)`, `SystemExit('bye')`, `-c 1/0`, a script raising in a function, a missing script, and a program printing `sys.orig_argv` and `__main__`'s names, the exit code, stdout and stderr are byte-equal with and without the prelude: 16 of 16 calls, both binaries (EXECUTED: `equal.py`, `equal.txt`).
- **Two differences are visible.** The stack is two frames deeper: the prelude's `<string>` frame and the inner `<reactor>` frame. A traceback does not show them: the inner call catches the exception and prints only the program's frames, as before. A program that walks its own stack sees them, and has two frames less before the recursion limit.
- **Fuel** (operation counts, one run each; a benchmark fact, not a test bound): `-c pass` costs 82,108,619 without and 85,372,093 with the prelude on the snapshot (+3.26 M, +4.0%), and 241,945,809 against 243,271,392 on the plain binary (+1.33 M, +0.5%). The snapshot pays more because `_reactor.run`'s per-call refresh runs twice, and on the snapshot it reseeds `random` and `numpy.random`, which are imported there (INFERRED from `_refresh`). A call without an import path pays nothing: its argv is unchanged.
- The inner `-c` program's source is registered in `linecache` after the prelude's, under the same key, so a traceback shows the program's line, not the prelude's (EXECUTED: `1/0` is shown in both columns).

## 3. Bytecode (EXECUTED)

- P3, both binaries, a read-only grant at `/code` on the import path: `import mylib, pkg` works; with `sys.dont_write_bytecode = False` set by the program first, it works too, stderr is empty, and the host's listing of the grant is the same before and after.
- The loader does not even try: a **writable** folder put on `sys.path` by the program gets no `__pycache__` after an import with the default flag; with the flag set to `False` it gets `__pycache__/wmod.cpython-315.pyc`. So the flag is what stops the write, and on a read-only grant the write would fail (EPERM, spec 017) and CPython's loader swallows the error (READ: `SourceFileLoader.set_data` returns on `OSError`).
- A valid `.pyc` in a read-only grant is used. The probe compiled `wmod.py` (`X = 1`) in the guest, then rewrote the source to `X = 2` with the same size and restored its times on the host. The next call imported `X == 1` from `/w/__pycache__/wmod.cpython-315.pyc`, on both binaries. CPython 3.15 sets no `__cached__` on modules; `__spec__.cached` names the file. The cache tag is `cpython-315`, so a `.pyc` the host's CPython 3.14 wrote is ignored (INFERRED from the tag).

## 4. Zips, resources and metadata (EXECUTED)

P4, both binaries: `lib.zip` inside the grant, the import path `["/code", "/code/lib.zip"]`. `zmod` imports through `zipimporter` with `__file__ == '/code/lib.zip/zmod.py'`; `importlib.resources.files('zpkg').joinpath('data.txt').read_text()` reads; and `importlib.metadata.version` answers `1.2` for a `dist-info` inside the zip and `3.4` for one in the folder.

Spec 035 (being built) replaces zipimport's directory reader for every zip on the import path, and the resource and metadata readers for every zip on it (its Decisions 3, 6 and 7, READ). Entries named by spec 054 are such zips. Nothing in 054 depends on 035: P4 ran on today's set, and the same check must pass after 035 lands.

P10, both binaries: an entry that does not exist (`/code/missing.zip`) or is a plain file (`/code/mylib.py`) is skipped, with `None` in `sys.path_importer_cache`, as CPython skips a bad `PYTHONPATH` entry. A guest path holding a quote (`/code/it's here`) survives the prelude's literal.

## 5. Order and shadowing (EXECUTED)

P6, both binaries. The grant holds `json/`, `numpy/`, `csv/`, `host/` (the tool protocol's guest package name), `math.py` and `uuid.py`, each defining `SHADOW`.

| module | appended after the zip, snapshot | appended, plain | inserted before the zip, snapshot | inserted, plain |
|---|---|---|---|---|
| `json` | runtime | runtime | runtime | **grant** |
| `math` (builtin) | runtime | runtime | runtime | runtime |
| `numpy` | runtime | runtime | runtime | **grant** |
| `csv` | runtime | runtime | runtime | **grant** |
| `uuid` | runtime | runtime | runtime | **grant** |
| `host` | runtime | runtime | **grant** | **grant** |

- Appended, the runtime wins everywhere, on both binaries.
- Inserted first, the answer depends on the binary. The snapshot has `json`, `numpy`, `csv` and `uuid` in `sys.modules` already, so the grant's copies never load there; the plain binary loads them. A builtin module wins either way: `BuiltinImporter` is first on `sys.meta_path`.
- A shadowed `numpy` package would pair the grant's Python with the runtime's compiled-in C extension modules of the pinned version (INFERRED; not run, since it would only show a crash).

## 6. Writable places near an entry (EXECUTED)

P8, both binaries, host folder `proj` with a subfolder `out`:

- **Host nesting.** Call 1 grants `proj/out` writable at `/out` and writes `/out/evil.py`. Call 2 grants `proj` read-only at `/code2` with `/code2` on the import path, and runs `import out.evil`. It prints `planted code ran`. Spec 017 refuses a read-only grant *inside* a writable one; it allows the reverse, which is this layout. Within one call the runner can see it by identity (spec 017's walk); across calls it cannot.
- **Guest nesting.** One call grants `proj` read-only at `/code2`, on the import path, and `proj/out` writable at `/code2/out`. The program writes `/code2/out/evil.py` and imports `out.evil`; it runs. wasi-libc resolves `/code2/out/…` to the writable grant (the longest guest prefix), so the folder on the import path holds a writable subfolder. The next call with the same layout would import what this one left.
- P9: with `root=True` (writable `/`) and a read-only grant at `/code`, `/code` on the import path is served by the grant (`mylib.__file__ == '/code/mylib.py'`), and a write to `/code/x.py` is `PermissionError: [Errno 63]`. The writable root above an entry is harmless; a writable place under it is not.

## 7. A read-only mount on the import path (EXECUTED)

P7, both binaries, an in-memory provider mounted read-only at `/m`, on the import path:

| program | provider calls, snapshot | plain |
|---|---|---|
| `pass` | 0 | 0 |
| `import json` | 0 | 0 |
| `import mlib, mpkg` (a module and a package in the mount) | stat 14, list 1, read 4 | stat 14, list 1, read 4 |
| `import nosuch1` (a miss) | stat 3, list 1 | stat 16, list 1 |

The zip comes first, so a module the zip holds costs the mount nothing. A module found in the mount, and every miss, costs provider calls, which count toward the call's file-call limit as any other (spec 032). The plain binary's miss costs more stats, because its error path imports modules the snapshot already holds, and each lookup that misses the zip reaches the mount (INFERRED).

## 8. `importlib.invalidate_caches()` (EXECUTED)

- P5, both binaries: the program calls the door; the host function writes `late.py` into the read-only grant's host folder; the program then imports `late` **without** calling `invalidate_caches()`, and it works. `FileFinder` re-lists a folder whose modification time changed (INFERRED from the result and CPython's `FileFinder.find_spec`).
- `importlib.invalidate_caches()` after an import costs 170,762,049 fuel on the snapshot and 384,944,589 on the plain binary, almost all of it re-reading the stdlib zip's directory, which spec 035 cuts (its "The problem" measured 170.8 M on the snapshot). An import path adds nothing to that: an entry's finder is rebuilt lazily.

## 9. Ways that were weighed

- **The environment** (`PYTHONPATH`, or a variable of our own read by the bootstrap). Isolated mode ignores `PYTHONPATH` (P1). Honouring any variable needs a bootstrap change: a rebuild of both binaries and the snapshot, a build-class specification with a review before build. And a variable in `env=` could name a writable folder, so the runner would have to refuse the key. The agent-runtime memo (§5 item 5) already said: an explicit argument, not the environment.
- **A bootstrap argument or export.** The same rebuild cost, and a new guest contract every embedder must learn, for no new power: an embedder's host owns argv already.
- **`site` and `.pth` files.** `site` does not run (`no_site == 1`, P1), by design (spec 006).
- **The prelude** (section 2). Runner-only, no rebuild, no new guest contract, and testable on today's set. Its two visible costs are the two stack frames and the fuel. If a later build-class change rebuilds the bootstrap for another reason, the mechanism can move into the guest without changing the runner's public argument.
- **A flag on `Grant`** (`importable=True`) against **a list of guest paths** (`import_path=`). A flag can name only a grant's own folder: not a zip inside it (P4), not a subfolder (a `src/` layout), and not a mount without a second flag on `Mount`. A list names exactly the entries, in order, whichever read-only place serves each.

## Where it stopped

Every question the drafting brief named has an executed answer above. Not run: a native-host comparison of the prelude's stack (not needed: the reactor is not CPython's `main`), and a crash from a shadowed `numpy` (section 5's last bullet, INFERRED).

## Corrected by spec 054's pre-build review (2026-10-18, before landing)

Appended, not rewritten. The review (`../reviews/054-read-only-code-on-the-import-path-spec-2026-10-18.md`) ran what this memo did not, and three things above are incomplete:

- **§2, "A traceback does not show them".** True for the prelude's frames, but its *source* appeared in tracebacks of `exec`/`eval` in a script, `-m` or standard input: the prelude and those strings share one `linecache` key (EXECUTED by the reviewer). Clearing `linecache._interactive_cache` first in the prelude makes them byte-equal again (`revision_linecache.py`, `revision_linecache.txt`: 3 of 3 per binary, against 0 of 3).
- **§5, "Appended, the runtime wins everywhere".** True for names the runtime *has*. For names it looks for and lacks (C accelerators, other platforms' modules, the profile's optional dependencies), an entry supplies them, and the plain binary also tries them for packages the snapshot imported at build time: an entry's `pytz.py` is imported by `import pandas` 2 times on the plain binary and 0 on the snapshot; an entry's `_hashlib.py` breaks `import hashlib` on both (EXECUTED by the reviewer; `revision_lacking_names.py`, `.txt`).
- **§7 and §9's mount line.** The measurements stand, but a read-only mount on the import path is unsafe when its provider is also mounted writable: one provider at `/lib` (read-only) and `/work` (writable) let call 1 plant code that call 2 imported (EXECUTED by the reviewer). Spec 054 refuses mounts as servers; owner question 93 asks about later.

## One line

The runner can put read-only folders and zips on the import path today, after the stdlib zip, with a one-line prelude and no rebuild, provided it refuses every layout that puts a writable place under an entry.
