# 054 — Read-only code on the import path

- **Status:** drafted 2026-10-18; awaiting its pre-build review. §5.6 does not require one here
  (no guest import or export, artifact or recipe changes), but it is held, as for 032 and 034,
  because this widens a safety claim the README makes and the judge checks ("only the stdlib zip
  is on the import path").
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`: `run`, `run_async`, `_check_places`,
  `_walk_grants` and `_judge`, `_instance`), the command line (`src/wasi_python/cli.py`), judge
  additions in `tests/` (Decision 12), `README.md`, `CHANGELOG.md`. **Changes the public API**
  (spec 049, Decision 13): one keyword-only parameter on `run` and `run_async`, one command
  option (Decision 10). **Not build-class:** it touches no `scripts/`, `recipes/`,
  `downloads/SHA256SUMS` or release workflow, and it runs on today's artifact set unchanged.
- **Depends on:** 017 (typed grants: the walk, identities, `_judge`), 022 (grants on the command
  line), 025 (nothing writable by default), 032 and 034 (mounts, read-only and writable), all
  landed. **049** (the public API frozen), confirmed for build and not landed: Decision 10 says
  what each order of landing asks. It does not depend on 035 (the zip's directory, being built)
  or 041; Decision 8 says how it meets 035.
- **Research it stands on:** `../research/2026-10-18-read-only-code-on-the-import-path.md` and
  its evidence folder (`probe.py`, `outputs.txt`, `equal.py`, `equal.txt`, `root_and_mount.py`,
  `root_and_mount.txt`; EXECUTED on both binaries of the main tree's artifact set, wasmtime-py
  49.0.0). The owner's
  decisions 16 ("yes, as an explicit read-only typed grant the embedder asks for; never writable,
  never by default") and 49 (0.1.0 carries it) (`../decisions.md`).
  `../research/2026-10-17-the-runtime-for-agent-code.md` (§4.1 item 3, §4.2, §5 item 5).
  `../research/2026-10-17-typed-grants.md` (candidate shape A left room for this). Spec 032's
  Scope ("Read-only code on the import path (decision 16) stays a typed grant. A mount … may
  import; it is not claimed"), which this specification settles.

## The problem

An embedder cannot hand a guest a library. The import path holds one entry, the stdlib zip.
`site` does not run, and the interpreter is isolated, so `PYTHONPATH` reaches `os.environ` but
not `sys.path` (memo §1, EXECUTED). An agent runtime needs this most: the embedder ships a small
guest-side helper (for its files, its tools, its data model) and the agent's code imports it.
Today the only way is for the program to edit `sys.path` itself, which every program would have
to repeat, and which the runner cannot check.

What must not change is spec 006's guarantee: nothing writable is ever on the import path the
runtime sets up, so code one call plants never runs in a later call by being imported. Two
layouts would break that if an import path were allowed naively (memo §6, EXECUTED, both
binaries): a writable grant whose host folder lies inside the importable one, and a writable
grant whose guest path lies under the entry. In the first, a later call imported a module an
earlier call wrote. In the second, a call imported a module it had just written through the
writable grant, which a later call with the same layout would import too (INFERRED from the
first).

## Terms

- **The import path** is the guest's `sys.path`.
- **An entry** is one guest path the embedder puts on it: a folder, or a zip file.
- **A place** is a grant, a mount, the root or the stdlib folder: something preopened at a guest
  path.
- **The place that serves a guest path** is the place whose guest path is the longest prefix of
  it, compared by whole components. wasi-libc resolves every path that way (the runner's own
  comment in `_instance`: "wasi-libc picks by the longest guest prefix"; memo §6, P9 EXECUTED).
- **A read-only place** is a read-only grant or a read-only mount.

## Decisions

1. **The surface: `import_path=`, a list of guest paths.**
   - `run(argv, *, …, import_path: Iterable[str] = (), …)`, and `run_async` alike. The
     parameter sits right after `mounts`. The default, empty, keeps today's import path exactly:
     never by default (decision 16).
   - Each entry is a `str` (not `os.PathLike`, not `bytes`: guest paths are `str` in `Grant` and
     `Mount` too). The argument is any iterable of `str` except a `str` itself; `_check_places`
     turns it into a tuple, so `run_async` hands its worker no used iterator (spec 017's rule
     for `grants`).
   - **Why a list and not a flag on `Grant`.** A flag (`Grant(…, importable=True)`) can name only
     a grant's own folder. It cannot name a zip inside a grant (memo §4), a subfolder (a `src/`
     layout), or a mount, without a second flag on `Mount` and two places to check. A list names
     exactly what goes on `sys.path`, in order, whichever read-only place serves each entry.
   - **It is decision 16 as the owner gave it.** The code still arrives only through a
     read-only place the embedder grants, explicitly (the embedder names the entry), never
     writable (Decisions 3 to 5), never by default (the empty default).
2. **Each entry's spelling is checked before any work** (`TypeError` for a type, `ValueError`
   for a value, as specs 013 and 014; each message names `import_path[i]` and the entry):
   - spec 017's guest-path rule, `_guest_path`: absolute; no NUL; valid UTF-8; no empty, `.` or
     `..` component; no trailing `/`; not `/`; not `/usr/local/lib` or under it (the stdlib zip
     is already first, and the stdlib folder is the runtime's own);
   - no two entries equal. CPython allows duplicates; here a duplicate is always a mistake, and
     grants refuse theirs the same way.
   - The runner does not check that an entry exists or is importable. It cannot look inside a
     mount, and for a grant the answer could change before the guest runs. Python skips an entry
     that is missing or not a folder or a zip, as it skips a bad `PYTHONPATH` entry (memo §4,
     P10, EXECUTED: `None` in `sys.path_importer_cache`). The README says so.
3. **Each entry is served by a read-only place.** The place that serves it (Terms) must be a
   read-only grant or a read-only mount. Otherwise `ValueError`:
   - served by the root, a writable grant or a writable mount: "is served by <place>, which is
     writable; only a read-only grant or mount may be on the import path";
   - served by nothing (no grant, no mount, no root above it): "no grant or mount serves it".
   - A mount at `/` counts: it serves every path no longer prefix serves. A read-only mount at
     `/` may serve `/lib`; a writable one may serve nothing on the import path.
   - Nested places resolve as the guest resolves them: with a writable grant at `/work` and a
     read-only grant at `/work/lib`, the entry `/work/lib` is served by the read-only grant and
     is allowed; the entry `/work/other` is served by the writable grant and is refused.
4. **No writable place lies under an entry (guest nesting).** A writable grant or writable mount
   whose guest path is at or under an entry, by whole components, is refused with `ValueError`
   naming both. Memo §6, P8 (EXECUTED): with `/code2` on the import path and a writable grant at
   `/code2/out`, a program wrote `/code2/out/evil.py` and `import out.evil` ran it; the next call
   with that layout would too. The root is never under an entry (`/` is not an entry).
5. **No writable host folder lies inside an entry's grant (host nesting).** For each read-only
   grant that serves an entry, the root (when it is a host path) and every writable grant are
   compared with it by identity, as spec 017's `_judge` compares (the walked chains of
   `(st_dev, st_ino)`; on Windows the volume serial and file index): a writable folder at or
   inside the serving grant's folder is refused with `ValueError`.
   - Memo §6, P8 (EXECUTED): call 1 wrote `out/evil.py` through a writable grant of `proj/out`;
     call 2, granting `proj` read-only with `/code2` on the import path, imported and ran it.
     Inside one call the runner sees this layout; this rule refuses it.
   - Spec 017 already refuses the other direction: a read-only grant at or inside a writable
     one. Together, a grant that serves an entry shares no host folder with any writable place of
     the same call.
   - A root still to be made counts as inside whatever its deepest existing ancestor is inside
     (spec 017, Decision 4), so a missing root under an entry's grant is refused and no folder is
     made.
   - **Across calls the runner cannot see.** An embedder that grants a folder writable in one
     call and serves an entry from it in another plants code for itself. The README says so,
     beside spec 017's existing sentence that a read-only grant can change if the same host
     files are writable elsewhere.
   - Mounts have no host identity; what a read-only provider serves is the embedder's code
     (decision 17: governance is the embedder's).
6. **Entries go after the stdlib zip, in the order given.** `sys.path` becomes
   `['/usr/local/lib/python315.zip', *import_path]`. Reasons (memo §5, P6, EXECUTED):
   - **The same call answers the same on both binaries.** Before the zip, a grant's `json`,
     `numpy`, `csv` and `uuid` load on the plain binary but not on the snapshot, which imported
     them at build time. After it, the runtime's modules win on both.
   - **The pinned set stays the pinned set** (§3: a release is one pinned set). An entry cannot
     replace numpy's Python half under its compiled-in C half, nor the tool protocol's `host`
     package (P6: before the zip, the grant's `host` loaded on both binaries).
   - Builtin modules win in either order (`BuiltinImporter` is first on `sys.meta_path`).
   - So a module of an entry whose name the runtime already has is never imported. The README
     says: name your packages apart from the stdlib and the profile's. This differs from
     CPython, where `PYTHONPATH` comes before the stdlib, on purpose.
   - Among entries, the first wins, as in CPython.
7. **The mechanism is the runner's: a one-line prelude, no guest change.** When `import_path` is
   not empty, the guest's argv becomes `[ARGV0, "-c", PRELUDE, *argv]`, where `PRELUDE` is the
   single expression statement of memo §2 with `repr(list(import_path))` in it:

   ```
   __import__('sys').path.extend(ENTRIES) or __import__('sys').exit(__import__('_reactor').run(
       ['/usr/local/bin/python.wasm', *__import__('sys').argv[1:]], dict(__import__('os').environ)))
   ```

   (as one line). The outer `_reactor.run` runs it in `-c` mode; it extends `sys.path` and calls
   `_reactor.run` again with the caller's argv, which handles every mode as it always has; its
   exit code becomes the call's.
   - **What stays the same** (memo §2, P2, EXECUTED on both binaries): `-c`, `-m`, a script,
     standard input, `-V`, `-u`; `sys.argv` and `sys.orig_argv`; exit codes, `SystemExit`'s
     message; tracebacks, which still show only the program's frames and lines; a missing
     script's message and exit 2; no name added to `__main__`.
   - **What differs, documented in the README:** a program that walks its own stack sees two
     more frames (`len(traceback.extract_stack())` is 4, not 2), and has two frames less before
     the recursion limit. A call with an import path costs more fuel: +3.26 M on the snapshot
     and +1.33 M on the plain binary for `-c pass` (memo §2; a benchmark fact, never a bound).
   - **A call without an import path is untouched:** its argv is today's, byte for byte, so no
     existing check's fuel moves (criterion 9).
   - **Why not the guest** (memo §9): `PYTHONPATH` is ignored by the isolated interpreter;
     honouring it, or a variable or argument of our own, needs a bootstrap change, so a rebuild
     of both binaries and the snapshot, a build-class specification and a new guest contract,
     for no power an embedder's host lacks (it owns argv). A variable in `env=` could also name a
     writable folder. `site` does not run, by design. If a later build-class change rebuilds the
     bootstrap for its own reasons, the mechanism may move into the guest; `import_path=` does
     not change.
   - **It leans on `_reactor.run(argv, environ)`,** the reactor's own module since spec 003,
     present in every artifact set. Criterion 1 pins it on both binaries, so a set that changed
     it fails the judge before any user meets it.
   - `-c` with the prelude is never shown to the caller: `Completed` has no argv, and the
     command line prints only `run()`'s result.
8. **Bytecode, zips and caches need nothing built** (memo §3, §4, §8, EXECUTED):
   - **No `.pyc` is ever written.** `sys.dont_write_bytecode` is `True` on both binaries
     (`config.write_bytecode = 0`), so the loader does not try. A program that sets it `False`
     gets a quiet failure on a read-only place: the import succeeds, stderr is empty, the host
     folder is unchanged. Criterion 4 checks both.
   - **A valid `.pyc` in an entry is read**, with the guest's cache tag (`cpython-315`) and
     CPython's own validation. It is the embedder's code like the source beside it; an embedder
     may precompile with a CPython 3.15.
   - **A zip entry** imports through `zipimport`, with `importlib.resources` and
     `importlib.metadata` working on it (memo §4). Spec 035, once landed, serves its directory
     and resources with its own readers, which cover every zip on the import path (035's
     Decisions 3, 6 and 7). This specification's checks run on whatever set the judge has, so
     they meet 035 when it lands; neither waits on the other.
   - **`importlib.invalidate_caches()` is not needed** for an entry: a read-only entry changes
     only if the host changes it, and a file the host added mid-call was imported without it
     (P5). It works as today, at today's cost.
9. **A read-only mount may serve an entry.** Spec 032 left this to decision 16's specification.
   It is allowed, because a read-only provider serves the embedder's own files exactly as a
   read-only grant does, and because the agent runtime's files often live in a store, not on
   disk (decision 13: an embedder converges on the runner through a provider). Refusing it would
   make such an embedder copy its library to a folder first.
   - Imports the zip satisfies cost the mount nothing: `pass` and `import json` made 0 provider
     calls with a mount on the import path (memo §7, P7). A module found in the mount, and every
     import that misses the zip, makes provider calls (P7: a module and a package, 14 `stat`, 1
     `list`, 4 `read`). They count toward `max_file_calls` like any other provider call; nothing
     new is limited.
10. **The command line, and the public API.**
    - `wasi-python run --import-path GUEST` (repeatable; `VALUED` gains it). Each value is one
      entry, in the order typed, passed whole as `import_path=[…]`; nothing else is parsed.
      Every refusal is `run()`'s (exit 1, `"kind": "ValueError"` or `"TypeError"`), as spec 022
      decides for grants. A missing value is argparse's usage error (exit 2). Mounts are not on
      the command line (spec 032), so there an entry is served by a `--grant`.
    - **What changes in spec 049's snapshot** (049, Decision 13's rule), each allowed by 049's
      Decision 8 (a minor release may add keyword-only arguments whose default keeps today's
      behaviour, and command options; before 0.1.0 anything may change anyway):
      - under `def run`: `param import_path: Iterable[str] = ()  keyword-only`, after `mounts`;
      - under `async def run_async`: the same line, after `mounts`;
      - under `command wasi-python`: `option --import-path GUEST  append`.

      No public name is added, and no dataclass changes.
    - **If 049 has landed when 054 is built:** the builder writes the `Args:` entry for
      `import_path` with the same text in `run` and `run_async` (049, Decision 10), regenerates
      `tests/public_api.txt` and the README's reference with `uv run python
      tests/harness/api.py --write`, and the review checks the snapshot's diff is exactly the
      three lines above. **If 054 lands first:** its docstring sentence is prose like the rest
      of today's `run` docstring, and 049's builder renders the parameter and writes its `Args:`
      entry like any other; 049's reviewer then sees the three lines in the first snapshot.
11. **The README and the CHANGELOG.**
    - README *Grants* gains a short part, "The import path": `import_path=` and
      `--import-path`; what may serve an entry; the order after the stdlib zip and why (name
      packages apart); zips; that no `.pyc` is written and a valid one is read; that a missing
      entry is skipped; the two stack frames; the cross-call rule of Decision 5; a five-line
      example.
    - *Safety*, "Enforced, and judged": "only the stdlib zip is on the import path" becomes
      "only the stdlib zip and the read-only entries the embedder names are on the import path;
      nothing writable ever is".
    - *Mounts*, "State across runs is yours": the clause "with a writable mount at `/`, a `-c`
      program has `/`, its working directory, first on `sys.path`" is wrong today (memo §1,
      EXECUTED: `sys.path` is the zip alone with `root=True` and with a mount at `/`, and the
      mount's `/evil.py` does not import). It becomes: "a later run that imports from it (by
      adding it to its own `sys.path`; the runner never puts a writable place there)".
    - *Any other embedder*: one sentence: the import path holds only the zip; a host that adds
      entries should add read-only ones only, after the zip, and may do it as the runner does
      (a `-c` prelude around `_reactor.run`), since it owns argv.
    - CHANGELOG, unreleased, Added: `import_path=` on `run` and `run_async`, and
      `--import-path`; Fixed (docs): the README's `sys.path` clause under *Mounts*.
12. **Checks.** Each counts or compares; none measures time; each is seen failing first (the
    criteria say against what).

## Intent

An embedder names the read-only folders and zips the guest may import from, and the guest
imports them after the runtime's own modules, on both binaries alike, while nothing writable ever
reaches the import path the runtime sets up.

## Design

```
src/wasi_python/runner.py   run, run_async: import_path= (after mounts), docstrings;
                            _check_places: _check_import_path (Decisions 2 to 4: spelling,
                              the serving place by longest whole-component prefix, guest
                              nesting), returning the tuple and, per entry, the serving grant's
                              index or None (a mount);
                            _walk_grants / _judge: Decision 5 (host nesting), with the serving
                              grants' walked chains;
                            _instance: wasi.argv = [ARGV0, *_import_prelude(entries), *argv]
                              when entries, else today's; _import_prelude builds Decision 7's
                              line from repr(list(entries))
src/wasi_python/cli.py      --import-path GUEST (append; VALUED); passed as import_path=
tests/checks/test_v1_4_embedding.py   criteria 1 to 3, 6, 7 (real calls)
tests/checks/test_v1_2_hostile_guest.py   criteria 4 and 5
tests/unit/test_cli.py      criterion 7's parsing cases
README.md, CHANGELOG.md     Decision 11
(tests/public_api.txt, the README reference: only if 049 has landed; Decision 10)
```

`_check_import_path` sees only guest paths, so it needs no artifact set and runs in the caller's
thread with the other argument checks. Decision 5 needs the walk, so it runs in `_judge`, which
runs before the stdlib folder, the module or any preopen is made. Either refusal comes before
the guest exists.

## Scope

In: the above.

Out:
- **A writable entry**, in any form (decision 16: never writable).
- **Entries before the stdlib zip** (Decision 6).
- **A script's folder on `sys.path`** (CPython's `sys.path[0]`). The reactor runs isolated and
  never adds it today; the README says so. An embedder that wants it names the folder as an
  entry.
- **Checking an entry's contents** (Decision 2), or that a zip is well formed: Python and spec
  035's readers judge a zip, with upstream's checks for anything odd.
- **A guest-side mechanism** (a bootstrap change; Decision 7).
- **Mounts on the command line** (spec 032).
- **Cross-call layouts** the runner cannot see (Decision 5, documented).

## Acceptance criteria

Every check runs on both binaries where it starts a guest (`[snapshot]`, `[plain]`). Folders are
made under the check's own temporary folder. Each is seen failing first: against main's runner,
where `import_path=` does not exist (`TypeError: run() got an unexpected keyword argument`), and,
where a criterion names one, against a **stand-in**: the built runner with one change, made in a
scratch copy, which the named check must catch.

1. **`test_the_import_path_reaches_every_mode`** (v1.4). A read-only grant of a folder holding
   `mylib.py`, a package `pkg` with `__main__.py`, `main.py` (imports `mylib`, prints `sys.argv`,
   exits 3) and `boom.py` (raises `ZeroDivisionError` in a function), at `/code`, with
   `import_path=["/code"]`:
   - `-c` imports `mylib` and prints `sys.path`, which equals
     `['/usr/local/lib/python315.zip', '/code']`;
   - `-m pkg x y` runs `pkg/__main__.py` with `sys.argv == ['/code/pkg/__main__.py', 'x', 'y']`;
   - the script `/code/main.py s1` exits 3 and prints `['/code/main.py', 's1']`;
   - standard input imports `mylib`;
   - for each of `-V`, `-u -c "print(1)"`, `-c "import sys; sys.exit(7)"`, `-c "raise
     SystemExit('bye')"`, `-c "1/0"`, `/code/boom.py`, `/code/nope.py`, and `-c "import sys;
     print(sys.orig_argv, sorted(k for k in dir() if not k.startswith('__')))"`, the
     `exit_code`, `stdout` and `stderr` are byte-equal to the same call without `import_path`
     (8 of 8 per binary; the memo's `equal.txt` ran exactly these, 16 of 16).
   - Stand-ins: (a) the prelude passes `sys.argv[2:]` (one argument dropped): every mode case
     fails; (b) the prelude passes `sys.argv` whole, so the inner argv0 is `-c`: the missing
     script's message and the `orig_argv` case fail.
2. **`test_the_import_path_comes_after_the_runtime`** (v1.4). The grant also holds `json/`,
   `numpy/`, `csv/`, `uuid.py`, `host/` and `math.py`, each defining `SHADOW`: each imported
   module lacks `SHADOW` (6 of 6 are the runtime's), on both binaries. Two grants `/a` and `/b`
   each hold `same.py` (`WHO = "a"` and `"b"`): `import_path=["/a", "/b"]` imports `a`'s, and
   `["/b", "/a"]` imports `b`'s. Stand-in: the prelude inserts at 0; the plain case fails with 5
   of 6 shadowed (`json`, `numpy`, `csv`, `uuid`, `host`) and the snapshot case with 1 (`host`).
3. **`test_a_zip_on_the_import_path`** (v1.4). `lib.zip` in the grant (a module, a package with
   a data file, a `dist-info` with `METADATA`) and a `dist-info` folder beside it;
   `import_path=["/code", "/code/lib.zip"]`: the module's `__file__` is
   `/code/lib.zip/zmod.py`; `importlib.resources.files('zpkg').joinpath('data.txt').read_text()`
   equals the bytes written; `importlib.metadata.version` answers both distributions' versions.
   `import_path=["/code/missing.zip", "/code"]` still imports `mylib`, and the missing entry's
   `sys.path_importer_cache` value is `None`.
4. **`test_the_import_path_writes_nothing`** (v1.2). Importing `mylib` and `pkg` from a
   read-only entry, once as is and once after the program sets `sys.dont_write_bytecode =
   False`: `exit_code` 0, `stderr` empty, and the host folder's sorted listing and every file's
   SHA-256 are the same before and after (0 files added, 0 changed). A `.pyc` compiled in an
   earlier call through a writable grant, whose source was then rewritten to the same size with
   its times restored, is the one imported from a read-only entry (`X == 1`, and
   `__spec__.cached` names it).
5. **`test_a_writable_place_never_serves_the_import_path`** (v1.2). Each case raises before any
   work, and a door host that counts calls stays at 0; the message names `import_path[i]`:
   - `TypeError` (5 cases): `import_path="/code"`, `[b"/code"]`, `[Path("/code")]`, `[None]`,
     `5`;
   - `ValueError` for spelling (7 cases): `["code"]`, `["/code/"]`, `["/code/../x"]`, `["/"]`,
     `["/usr/local/lib/x"]`, `["/code", "/code"]`, `["/co\0de"]`;
   - `ValueError` for the serving place (5 cases): served by the root (`root=True`, `["/x"]`); by
     a writable grant; by a writable mount; by nothing; by a writable mount at `/` (`["/lib"]`);
   - `ValueError` for guest nesting (3 cases), each beside the read-only grant at `/code` with
     `["/code"]`: a writable grant at `/code/out`; a writable mount at `/code/out`; a writable
     grant at `/code/a/b`;
   - `ValueError` for host nesting (3 cases): a writable grant of `code/out` at `/out` with the
     read-only grant of `code` serving `["/code"]`; `root=` a path `code/r` (existing) with the
     same; `root=` a path `code/new` that does not exist, which is refused and not made (the
     folder is absent afterwards);
   - **allowed** (4 cases, each runs and imports `mylib` from its entry): a writable grant at
     `/work` and a read-only grant at `/work/lib` with `["/work/lib"]`; `root=True` with a
     read-only grant at `/code` and `["/code"]`; a writable grant whose host folder is a sibling
     of the entry's grant's; a read-only mount at `/` with `["/lib"]` (an in-memory provider).
   - Stand-ins, each failing exactly the named cases: no serving-place rule (5 serving cases);
     first match by shortest prefix instead of longest (the first allowed case is refused, and
     the writable-grant serving case passes); no guest-nesting rule (3); no host-nesting rule
     (3).
6. **`test_a_read_only_mount_on_the_import_path`** (v1.4). An in-memory provider mounted
   read-only at `/m`, holding `mlib.py` and `mpkg/__init__.py`, `import_path=["/m"]`: `-c pass`
   and `-c "import json"` each make 0 provider calls (`sum(files.calls.values()) == 0`);
   `import mlib, mpkg` prints `mlib`'s value, with `files.calls["read"] >= 2` and
   `files.calls["list"] >= 1`; with `max_file_calls=1`, the same import ends `"out of file
   calls"`.
7. **The command line.** Unit (`tests/unit/test_cli.py`, the fake `run`): `--import-path /a
   --grant /a=x --import-path /b -- -c pass` reaches `run()` with `import_path=["/a", "/b"]` and
   one grant; `--import-path=/a` likewise; `--import-path` with no value exits 2; without the
   option `run()` receives no `import_path` keyword; the scan table gains `--import-path /a
   x.py`. v1.4, a real call: `wasi-python run --grant /code=<dir> --import-path /code -- -c
   "import mylib; print(mylib.VALUE)"` exits 0 with the value on `stdout` in the JSON;
   `--import-path /code` without the grant exits 1 with `"kind": "ValueError"`.
8. **Spec 006's guarantee is still judged.** `test_planted_code_never_runs` and the
   `sys.path` print in `test_v1_2_hostile_guest.py` pass unchanged (no `import_path` given).
9. **The judge.** `uv run pytest` is green with `--accept-judge` (new checks); **lost 0, grew
   0**: no existing check passes `import_path`, so no existing call's argv or fuel changes.
   `ruff check` and `ruff format --check` clean. If 049 has landed,
   `test_the_public_api_matches_its_snapshot` passes after `--write`, and the snapshot's diff
   is exactly Decision 10's three lines.
10. The README and CHANGELOG say what Decision 11 lists; the landing notes record the stand-ins'
    results and each check's seen-failing run.

## The owner's choices

None waits on the owner. Decision 16 gave the feature and its two limits (never writable,
never by default); decision 49 placed it in 0.1.0. The choices here (a list rather than a flag,
read-only mounts included, after the zip, a runner-only mechanism) are made by §6's rules and
carry their reasons; none loosens a default (§4.15): with no `import_path` every call is as
today.

## Landing notes

Not built.
