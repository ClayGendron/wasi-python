# 054 — Read-only code on the import path

- **Status:** **landed 2026-10-18** (accepted on `5f56591` as `c79a3a9`; the build review, `../reviews/054-read-only-code-on-the-import-path-2026-10-18.md`, confirmed it; see the Landing notes' last part). Before landing: built 2026-10-18; revised against its build review (F1 to F4, F6; "Revised against the build review" and its Disposition); rebased onto main `3dfdab4` (049 landed) by the author, judged green there ("Rebased onto main"); awaiting the reviewer's confirmation of the revision. Confirmed for build 2026-10-18. The reviewer's Confirmation passed it ("ready to build") with two remarks, written in here: R1 (S8's root is a host folder apart from `code`) and R2 (A5's payload parses, so the stand-in really prints `injected`). Drafted 2026-10-18; reviewed before build the same day (`../reviews/054-read-only-code-on-the-import-path-spec-2026-10-18.md`; verdict: ready once F1 to F7 are written in) and revised against all seven findings (the Disposition below says where each went). §5.6 does not require a review before build here (no guest import or export, artifact or recipe changes); one was held, as for 032 and 034, because this widens a safety claim the README makes and the judge checks ("only the stdlib zip is on the import path").
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`: `run`, `run_async`, `_check_places`, `_walk_grants` and `_judge`, `_instance`), the command line (`src/wasi_python/cli.py`), judge additions in `tests/` (Decision 12), `README.md`, `CHANGELOG.md`. **Changes the public API** (spec 049, Decision 13): one keyword-only parameter on `run` and `run_async`, one command option (Decision 10). **Not build-class:** it touches no `scripts/`, `recipes/`, `downloads/SHA256SUMS` or release workflow, and it runs on today's artifact set unchanged.
- **Depends on:** 017 (typed grants: the walk, identities, `_judge`), 022 (grants on the command line), 025 (nothing writable by default), 032 and 034 (mounts, read-only and writable: here refused as servers and checked for nesting), all landed. **049** (the public API frozen), confirmed for build and not landed: Decision 10 says what each order of landing asks. It does not depend on 035 (the zip's directory, being built) or 041; Decision 8 says how it meets 035.
- **Research it stands on:** `../research/2026-10-18-read-only-code-on-the-import-path.md` and its evidence folder (`probe.py`, `outputs.txt`, `equal.py`, `equal.txt`, `root_and_mount.py`, `root_and_mount.txt`, and, for this revision, `revision_linecache.py` and `.txt`, `revision_lacking_names.py` and `.txt`; EXECUTED on both binaries of the main tree's artifact set, wasmtime-py 49.0.0). The pre-build review's probes (EXECUTED there, against the frozen set `s-f94dec535086b06c`: the shared-provider layout, the traceback leak and its fix, names the runtime lacks, links inside a grant, the prelude's literal). The owner's decisions 16 ("yes, as an explicit read-only typed grant the embedder asks for; never writable, never by default") and 49 (0.1.0 carries it) (`../decisions.md`). The lane's ruling on F1 (2026-10-18: grants only; mounts refused as servers; question 93). `../research/2026-10-17-the-runtime-for-agent-code.md` (§4.1 item 3, §4.2, §5 item 5). `../research/2026-10-17-typed-grants.md` (candidate shape A left room for this). Spec 032's Scope ("Read-only code on the import path (decision 16) stays a typed grant. A mount … may import; it is not claimed").

## The problem

An embedder cannot hand a guest a library. The import path holds one entry, the stdlib zip. `site` does not run, and the interpreter is isolated, so `PYTHONPATH` reaches `os.environ` but not `sys.path` (memo §1, EXECUTED). An agent runtime needs this most: the embedder ships a small guest-side helper (for its files, its tools, its data model) and the agent's code imports it. Today the only way is for the program to edit `sys.path` itself, which every program would have to repeat, and which the runner cannot check.

What must not change is spec 006's guarantee: nothing writable is ever on the import path the runtime sets up, so code one call plants never runs in a later call by being imported. Three layouts would break that if an import path were allowed naively (EXECUTED, both binaries):

- a writable grant whose host folder lies inside the importable one (memo §6): a later call imported a module an earlier call wrote;
- a writable grant whose guest path lies under the entry (memo §6): a call imported a module it had just written, which a later call with the same layout would import too (INFERRED from the first);
- one provider object mounted read-only and writable (the review's F1): a later call imported a module an earlier call wrote through the writable mount.

## Terms

- **The import path** is the guest's `sys.path`.
- **An entry** is one guest path the embedder puts on it: a folder, or a zip file.
- **A place** is a grant, a mount, the root or the stdlib folder: something preopened at a guest path.
- **Under**, for guest paths, means at or below by whole components: `/code/a` is under `/code`; `/code2` is not. It is never a text prefix test.
- **The place that serves a guest path** is the place whose guest path is the longest whole- component prefix of it. wasi-libc resolves every path that way (the runner's own comment in `_instance`: "wasi-libc picks by the longest guest prefix"; memo §6, P9 EXECUTED).
- **The serving grant** of an entry is the read-only grant that serves it (Decision 3).

## Decisions

1. **The surface: `import_path=`, a list of guest paths.**
   - `run(argv, *, …, import_path: Iterable[str] = (), …)`, and `run_async` alike. The parameter sits right after `mounts`. The default, empty, keeps today's import path exactly: never by default (decision 16).
   - Each entry is a `str` (not `os.PathLike`, not `bytes`: guest paths are `str` in `Grant` and `Mount` too). The argument is any iterable of `str` except a `str` itself.
   - **Why a list and not a flag on `Grant`.** A flag (`Grant(…, importable=True)`) can name only a grant's own folder. It cannot name a zip inside a grant (memo §4) or a subfolder (a `src/` layout). A list names exactly what goes on `sys.path`, in order.
   - **It is decision 16 as the owner gave it.** The code arrives only through a read-only typed grant the embedder gives, explicitly (the embedder names the entry), never writable (Decisions 3 to 5 and 9), never by default (the empty default).
2. **Each entry's spelling is checked before any work** (`TypeError` for a type, `ValueError` for a value, as specs 013 and 014; each message names `import_path[i]` and the entry):
   - spec 017's guest-path rule, `_guest_path`: absolute; no NUL; valid UTF-8; no empty, `.` or `..` component; no trailing `/`; not `/`; not `/usr/local/lib` or under it (the stdlib zip is already first, and the stdlib folder is the runtime's own). The builder gives `/` a message of its own here (`_guest_path`'s "pass root= instead" fits grants, not entries);
   - no two entries equal. CPython allows duplicates; here a duplicate is always a mistake, and grants refuse theirs the same way.
   - **What is kept is the checked plain string** (the review's F6). `_check_places` stores, as a tuple, the values `_guest_path` returns, which `_text` has made plain `str` through `str.__str__` (`runner.py`, `_text`). Nothing later reads the caller's objects: a `str` subclass whose `__repr__` or `__str__` lies cannot write anything into the prelude (Decision 7). So `run_async` also hands its worker no used iterator (spec 017's rule for `grants`).
   - The runner does not check that an entry exists or is importable: for a grant the answer could change before the guest runs, and Python skips an entry that is missing or not a folder or a zip, as it skips a bad `PYTHONPATH` entry (memo §4, P10, EXECUTED: `None` in `sys.path_importer_cache`). The README says so.
3. **Each entry is served by a read-only grant.** The place that serves it (Terms) must be a read-only grant. Otherwise `ValueError`:
   - served by the root or a writable grant: "is served by <place>, which is writable; only a read-only grant may serve the import path";
   - served by a mount, read-only or writable, a mount at `/` included: "is served by a mount; only a read-only grant may serve the import path" (Decision 9);
   - served by nothing (no grant, no mount, no root above it): "no grant serves it".
   - Nested places resolve as the guest resolves them: with a writable grant at `/work` and a read-only grant at `/work/lib`, the entry `/work/lib` is served by the read-only grant and is allowed; the entry `/work/other` is served by the writable grant and is refused.
   - Sibling names are not nested (the review's F4a): with a writable root and a read-only grant at `/code`, the entry `/code2` is served by the root, as wasi-libc serves it, and is refused. A text-prefix match would wrongly give it to `/code`.
4. **No writable place lies under an entry (guest nesting).** A writable grant, or any mount, whose guest path is under an entry is refused with `ValueError` naming both. Memo §6, P8 (EXECUTED): with `/code2` on the import path and a writable grant at `/code2/out`, a program wrote `/code2/out/evil.py` and `import out.evil` ran it. A mount is refused here whether read-only or writable, for Decision 9's reason: its provider may alias a writable store. The root is never under an entry (`/` is not an entry). A writable place *above* an entry is harmless: the entry's own grant serves everything under it (memo §6, P9).
5. **No writable host folder lies inside an entry's serving grant (host nesting).** For each serving grant, the root (when it is a host path) and every writable grant are compared with it by identity, as spec 017's `_judge` compares (the walked chains of `(st_dev, st_ino)`; on Windows the volume serial and file index): a writable folder at or inside **the serving grant's whole folder** is refused with `ValueError`.
   - Memo §6, P8 (EXECUTED): call 1 wrote `out/evil.py` through a writable grant of `proj/out`; call 2, granting `proj` read-only with `/code2` on the import path, imported and ran it.
   - **The whole folder, not the entry's subfolder** (the review's F5). A symbolic link inside a grant resolves into any folder of that grant (EXECUTED by the reviewer: with the entry `/p/lib`, a link `proj/lib/plug -> ../out` imported `plug.evil_in` from `proj/out`). So with the entry `/p/lib`, a writable grant of `proj/out` is refused too, though `out` is not under `lib`. A link that leaves the grant does not resolve (EXECUTED there, absolute and relative), so the grant's folder is the bound.
   - Spec 017 already refuses the other direction: a read-only grant at or inside a writable one. Together, a serving grant shares no host folder with any writable grant or root of the same call.
   - A root still to be made counts as inside whatever its deepest existing ancestor is inside (spec 017, Decision 4), so a missing root inside a serving grant is refused and no folder is made.
   - **Across calls the runner cannot see.** An embedder that grants a folder writable in one call and serves an entry from it in another plants code for itself. The README says so, beside spec 017's existing sentence that a read-only grant can change if the same host files are writable elsewhere.
6. **Entries go after the stdlib zip, in the order given.** `sys.path` becomes `['/usr/local/lib/python315.zip', *import_path]`; among entries the first wins, as in CPython.
   - **For a name the runtime has, the runtime wins, on both binaries alike** (memo §5, P6, EXECUTED). Before the zip, a grant's `json`, `numpy`, `csv` and `uuid` load on the plain binary but not on the snapshot, which imported them at build time, and the grant's `host` replaces the tool protocol's package on both. After the zip, the runtime's modules win everywhere, so an entry cannot replace numpy's Python half under its compiled-in C half. Builtin modules win in either order (`BuiltinImporter` is first on `sys.meta_path`).
   - **A name the runtime looks for and lacks can come from an entry, and the binaries may differ** (the review's F3, EXECUTED there and in `revision_lacking_names.txt`). The runtime's own modules try optional names and fall back when they are missing: C accelerators (`_decimal`, `_uuid`, `_hashlib`), other platforms' modules (`nt`, `msvcrt`, `_winapi`, `fcntl`, `grp`, `pwd`, `termios`), and the profile's optional dependencies (`pytz`, `pyarrow`, `numexpr`, `bottleneck`). An entry holding such a name supplies it. And the plain binary makes those tries at run time also for packages the snapshot imported at build time, when no entry existed: an entry's `pytz.py` is imported by `import pandas` on the plain binary (2 times today) and not at all on the snapshot; an entry's `_hashlib.py` is imported by `import hashlib` on both, which then fails with `AttributeError`.
   - **That is the rule, stated and pinned rather than prevented.** These names are the embedder's to avoid or to supply on purpose (a real pure-Python `pytz` makes pandas use it on the plain binary). Preventing it would need an import hook that tells the runtime's own lookups from the program's, which is a guest change and a source of its own surprises. The README states the rule with the examples above; criterion 2 pins today's answers, so a set that changes them is seen.
   - This differs from CPython, where `PYTHONPATH` comes before the stdlib, on purpose.
7. **The mechanism is the runner's: a one-line prelude, no guest change.** When `import_path` is not empty, the guest's argv becomes `[ARGV0, "-c", PRELUDE, *argv]`. `_import_prelude` takes only Decision 2's tuple of plain strings and writes, as one line:

   ```
   __import__('linecache')._interactive_cache.clear() or __import__('sys').path.extend(ENTRIES)
   or __import__('sys').exit(__import__('_reactor').run(['/usr/local/bin/python.wasm',
   *__import__('sys').argv[1:]], dict(__import__('os').environ)))
   ```

   where `ENTRIES` is `repr(list(entries))` of those plain strings (CPython's own `str.__repr__`, which the reviewer ran on newlines, both quotes, backslashes, U+2028, U+0085 and non-BMP characters). The outer `_reactor.run` runs it in `-c` mode; it extends `sys.path` and calls `_reactor.run` again with the caller's argv, which handles every mode as it always has; its exit code becomes the call's.
   - **The `linecache` clear** (the review's F2). The outer call registers the prelude's source in `linecache` under the key (`<string>`, `<module>`, 1), which every `exec` or `eval` of a string with the default filename shares. Without the clear, a script running `eval('1/0')` shows the prelude's whole line, entries included, in its traceback (EXECUTED by the reviewer; `revision_linecache.txt`: the memo's prelude differs from the call without an import path in 3 of 3 cases per binary, the clearing prelude in 0 of 3). `_interactive_cache` is private, as is the `linecache._register_code` that `_reactor` already calls; the pinned set fixes both, and criterion 1 pins the result.
   - **What stays the same** (memo §2, P2, `equal.txt`, `revision_linecache.txt`, EXECUTED on both binaries): `-c`, `-m`, a script, standard input, `-V`, `-u`; `sys.argv` and `sys.orig_argv`; exit codes, `SystemExit`'s message; tracebacks, byte-equal in every case criterion 1 lists, `exec` and `eval` inside scripts and standard input included; a missing script's message and exit 2; no name added to `__main__`.
   - **What differs, documented in the README:** a program that walks its own stack sees two more frames (`len(traceback.extract_stack())` is 4, not 2), and has two frames less before the recursion limit (996 frames of its own instead of 998, both binaries; the build review's `probe_fuel.txt`). A call with an import path costs more fuel, as built (with the clear) and measured on spec 035's set `s-c4190ca065ada03a`, the set 054 lands on: about +3.35 M to +3.58 M on the snapshot and +0.51 M to +1.94 M on the plain binary for `-c pass` (the build review's `probe_fuel_main.txt`, two pairs per binary, and the author's two pairs per binary in the landing notes; fuel varies by up to 0.5 M between runs of one call; benchmark facts, never a bound). The draft's +3.26 M and +1.33 M were measured without the clear, on the set before 035. The README states both differences (the build review's F4).
   - **A call without an import path is untouched:** its argv is today's, byte for byte. The ratchet cannot see this (its fuel comes from the harness's own driver, not from `run()`; the build review's F2), so criterion 1 pins it: such a call's stack is 2 frames deep.
   - **Why not the guest** (memo §9): `PYTHONPATH` is ignored by the isolated interpreter; honouring it, or a variable or argument of our own, needs a bootstrap change, so a rebuild of both binaries and the snapshot, a build-class specification and a new guest contract, for no power an embedder's host lacks (it owns argv). A variable in `env=` could also name a writable folder. `site` does not run, by design. If a later build-class change rebuilds the bootstrap for its own reasons, the mechanism may move into the guest; `import_path=` does not change.
   - **It leans on `_reactor.run(argv, environ)`,** the reactor's own module since spec 003, present in every artifact set. Criterion 1 pins it on both binaries, so a set that changed it fails the judge before any user meets it.
   - The prelude is never shown to the caller: `Completed` has no argv, and the command line prints only `run()`'s result.
8. **Bytecode, zips and caches need nothing built** (memo §3, §4, §8, EXECUTED):
   - **No `.pyc` is ever written.** `sys.dont_write_bytecode` is `True` on both binaries (`config.write_bytecode = 0`), so the loader does not try. A program that sets it `False` gets a quiet failure on a read-only grant: the import succeeds, stderr is empty, the host folder is unchanged. Criterion 4 checks both.
   - **A valid `.pyc` in an entry is read**, with the guest's cache tag (`cpython-315`) and CPython's own validation. It is the embedder's code like the source beside it; an embedder may precompile with a CPython 3.15.
   - **A zip entry** imports through `zipimport`, with `importlib.resources` and `importlib.metadata` working on it (memo §4). Spec 035, once landed, serves its directory and resources with its own readers, which cover every zip on the import path (035's Decisions 3, 6 and 7). This specification's checks run on whatever set the judge has, so they meet 035 when it lands; neither waits on the other.
   - **`importlib.invalidate_caches()` is not needed** for an entry: a read-only entry changes only if the host changes it, and a file the host added mid-call was imported without it (P5). It works as today, at today's cost.
9. **Mounts serve no entry** (the review's F1; the lane's ruling of 2026-10-18).
   - **Why.** A provider can alias a writable store, and the runner can judge that only in part. The reviewer ran it (EXECUTED, both binaries): one provider object mounted read-only at `/lib` and writable at `/work`; call 1 wrote `/work/lib/evil.py`; call 2, with `/lib/lib` on the import path, ran `import evil` and printed "planted code ran". Every grant rule here allowed that layout, because a mount has no host identity.
   - Constitution §6 decides it: keep the wall whole first (rule 1), and the smallest thing that meets the specification (rule 4). Decision 16 says "a typed grant", and spec 032 reserved mounts on purpose. So a mount serving an entry, read-only or writable, at `/` or elsewhere, is refused (Decision 3), and a mount under an entry is refused (Decision 4).
   - Whether a read-only mount may serve an entry later, with a refusal when its provider is also mounted writable, is the owner's: question 93 (`../questions-for-the-owner.md`), with the facts and the agent's recommendation. Meanwhile it is refused, and nothing waits. An embedder whose library lives in a store copies it to a folder and grants that, read-only.
   - What the draft measured stays true and is kept in the memo (§7): through a mount, an import the zip satisfies costs 0 provider calls. It is input for question 93, not a claim here.
10. **The command line, and the public API.**
    - `wasi-python run --import-path GUEST` (repeatable; `VALUED` gains it). Each value is one entry, in the order typed, passed whole as `import_path=[…]`; nothing else is parsed. Every refusal is `run()`'s (exit 1, `"kind": "ValueError"` or `"TypeError"`), as spec 022 decides for grants. A missing value is argparse's usage error (exit 2). An entry there is served by a `--grant`.
    - **What changes in spec 049's snapshot** (049, Decision 13's rule), each allowed by 049's Decision 8 (a minor release may add keyword-only arguments whose default keeps today's behaviour, and command options; before 0.1.0 anything may change anyway):
      - under `def run`: `param import_path: Iterable[str] = ()  keyword-only`, after `mounts`;
      - under `async def run_async`: the same line, after `mounts`;
      - under `command wasi-python`: `option --import-path GUEST  append`.

      No public name is added, and no dataclass changes.
    - **If 049 has landed when 054 is built:** the builder writes the `Args:` entry for `import_path` with the same text in `run` and `run_async` (049, Decision 10), regenerates `tests/public_api.txt` and the README's reference with `uv run python tests/harness/api.py --write`, and the review checks the snapshot's diff is exactly the three lines above. **If 054 lands first:** its docstring sentence is prose like the rest of today's `run` docstring, and 049's builder renders the parameter and writes its `Args:` entry like any other; 049's reviewer then sees the three lines in the first snapshot.
11. **The README and the CHANGELOG.**
    - README *Grants* gains a short part, "The import path": `import_path=` and `--import-path`; that only a read-only grant serves an entry and why mounts do not (one sentence on F1); the order after the stdlib zip; Decision 6's rule for names the runtime lacks, with its examples (C accelerators, other platforms' modules, the profile's optional dependencies, and on the plain binary also packages the snapshot pre-imported); zips; that no `.pyc` is written and a valid one is read; that a missing entry is skipped; the two stack frames, the recursion limit two frames sooner and the fuel a call with an import path costs (Decision 7; the build review's F4); what the runner cannot see, across calls Amended 2026-10-19 by spec 069: the snapshot pre-imports no package, so "on the plain binary also packages the snapshot pre-imported" is moot (it holds on both binaries); the `HIT pytz` numbers of criterion 2 are restated there (2 on both binaries). (Decision 5) and within one call (an embedder's hard link between an entry's grant and a writable grant, and a writable mount whose provider stores into an entry's folder; the build review's F3, both EXECUTED there); a five-line example.
    - *Safety*, "Enforced, and judged" (the pre-build review's F7, narrowed by the build review's F3): "only the stdlib zip is on the import path" becomes "only the stdlib zip and the read-only entries the embedder names are on the import path; each is served by a read-only grant, and no folder the same call's root or grants can write lies under one (a hard link, a writable mount whose store is an entry's folder, and other calls are yours to keep apart: see *The import path*)".
    - *Mounts*, "State across runs is yours": the clause "with a writable mount at `/`, a `-c` program has `/`, its working directory, first on `sys.path`" is wrong today (memo §1, EXECUTED: `sys.path` is the zip alone with `root=True` and with a mount at `/`, and the mount's `/evil.py` does not import; the reviewer re-read the evidence and agrees). It becomes: "a later run that imports from it (by adding it to its own `sys.path`; the runner never puts a mount or a writable place there)".
    - *Any other embedder*: one sentence: the import path holds only the zip; a host that adds entries should add read-only ones only, after the zip, and may do it as the runner does (a `-c` prelude around `_reactor.run`), since it owns argv.
    - CHANGELOG, unreleased, Added: `import_path=` on `run` and `run_async`, and `--import-path`; Fixed (docs): the README's `sys.path` clause under *Mounts*.
12. **Checks.** Each counts or compares; none measures time; each is seen failing first (the criteria say against what).

## Intent

An embedder names the read-only folders and zips, inside its read-only grants, that the guest may import from; the guest imports them after the runtime's own modules; and nothing the same call can write lies under the import path the runtime sets up.

## Design

```
src/wasi_python/runner.py   run, run_async: import_path= (after mounts), docstrings;
                            _check_places: _check_import_path (Decisions 2 to 4: spelling, the
                              plain strings kept, the serving place by longest whole-component
                              prefix, mounts refused, guest nesting), returning the tuple and,
                              per entry, the serving grant's index;
                            _walk_grants / _judge: Decision 5 (host nesting), against each
                              serving grant's walked chain;
                            _instance: wasi.argv = [ARGV0, *_import_prelude(entries), *argv]
                              when entries, else today's; _import_prelude(entries: tuple of
                              plain str) builds Decision 7's line
src/wasi_python/cli.py      --import-path GUEST (append; VALUED); passed as import_path=
tests/checks/test_v1_4_embedding.py   criteria 1 to 3, 6 (real calls)
tests/checks/test_v1_2_hostile_guest.py   criteria 4 and 5
tests/unit/test_cli.py      criterion 6's parsing cases
README.md, CHANGELOG.md     Decision 11
(tests/public_api.txt, the README reference: only if 049 has landed; Decision 10)
```

`_check_import_path` sees only guest paths, so it needs no artifact set and runs in the caller's thread with the other argument checks. Decision 5 needs the walk, so it runs in `_judge`, which runs before the stdlib folder, the module or any preopen is made. Either refusal comes before the guest exists.

## Scope

In: the above.

Out:
- **A writable entry**, in any form (decision 16: never writable).
- **A mount serving an entry** (Decision 9; question 93).
- **Entries before the stdlib zip** (Decision 6).
- **Keeping entries from supplying names the runtime lacks** (Decision 6: stated and pinned, not prevented).
- **A script's folder on `sys.path`** (CPython's `sys.path[0]`). The reactor runs isolated and never adds it today; the README says so. An embedder that wants it names the folder as an entry.
- **Checking an entry's contents** (Decision 2), or that a zip is well formed: Python and spec 035's readers judge a zip, with upstream's checks for anything odd.
- **A guest-side mechanism** (a bootstrap change; Decision 7).
- **Cross-call layouts** the runner cannot see (Decision 5, documented).

## Acceptance criteria

Every check runs on both binaries where it starts a guest (`[snapshot]`, `[plain]`). Folders are made under the check's own temporary folder. Each is seen failing first: against main's runner, where `import_path=` does not exist (`TypeError: run() got an unexpected keyword argument`), and, where a criterion names one, against a **stand-in**: the built runner with one change, made in a scratch copy, which the named check must catch, failing exactly the cases named.

1. **`test_the_import_path_reaches_every_mode`** (v1.4). A read-only grant of a folder holding `mylib.py`, a package `pkg` with `__main__.py`, `main.py` (imports `mylib`, prints `sys.argv`, exits 3), `boom.py` (raises `ZeroDivisionError` in a function), `s_eval.py` (`eval('1/0')`) and `s_exec.py` (`exec('x = 1/0')`), at `/code`, with `import_path=["/code"]`:
   - `-c` imports `mylib` and prints `sys.path`, which equals `['/usr/local/lib/python315.zip', '/code']`;
   - `-m pkg x y` runs `pkg/__main__.py` with `sys.argv == ['/code/pkg/__main__.py', 'x', 'y']`;
   - the script `/code/main.py s1` exits 3 and prints `['/code/main.py', 's1']`;
   - standard input imports `mylib`;
   - **`run_async`** with `import_path=["/code"]`: `-c` imports `mylib` and prints the same `sys.path` (the build review's F2: no other check ran that path);
   - **the two frames, only with an import path:** `-c "import traceback; print(len(traceback.extract_stack()))"` prints `2` without `import_path` and `4` with it (the build review's F2: a prelude added to every call is invisible to the ratchet, whose fuel comes from the harness's own driver, not from `run()`);
   - an entry whose guest path holds a quote, a double quote and a backslash (`/a'b"c\d`, a grant there holding `odd.py`) reaches `sys.path` exactly and `odd` imports (the build review's F6, against naive quoting);
   - for each of these 11 cases the `exit_code`, `stdout` and `stderr` are byte-equal to the same call without `import_path`: `-V`; `-u -c "print(1)"`; `-c "import sys; sys.exit(7)"`; `-c "raise SystemExit('bye')"`; `-c "1/0"`; `/code/boom.py`; `/code/nope.py`; `-c "import sys; print(sys.orig_argv, sorted(k for k in dir() if not k.startswith('__')))"`; `/code/s_eval.py`; `/code/s_exec.py`; standard input `eval('1/0')`. (The memo's `equal.txt` ran the first eight, 16 of 16; `revision_linecache.txt` the last three, 6 of 6.)
   - Stand-ins: (a) the prelude passes `sys.argv[2:]` (one argument dropped): every mode case fails; (b) the prelude passes `sys.argv` whole, so the inner argv0 is `-c`: the missing script's case and the `orig_argv` case fail; (c) **the memo's prelude, without the `linecache` clear**: exactly the last three byte-equal cases fail, on both binaries (as `revision_linecache.txt` shows); and the build review's mutants (d) R22, `run_async` dropping `import_path`: the `run_async` case fails; (e) R17, the prelude on every call: the frame pin fails (`4`, `4`); (f) R13, the prelude quoting entries by hand instead of `repr`: the odd entry's case fails (a `SyntaxError` in the guest).
2. **`test_the_import_path_comes_after_the_runtime`** (v1.4).
   - **Names the runtime has.** The grant also holds `json/`, `numpy/`, `csv/`, `uuid.py`, `host/` and `math.py`, each defining `SHADOW`: each imported module lacks `SHADOW` (6 of 6 are the runtime's), on both binaries.
   - **Order among entries.** Two grants `/a` and `/b` each hold `same.py` (`WHO = "a"` and `"b"`): `import_path=["/a", "/b"]` imports `a`'s, and `["/b", "/a"]` imports `b`'s.
   - **Names the runtime lacks, pinned** (Decision 6; `revision_lacking_names.txt`). An entry holding only `pytz.py` (writes `HIT pytz` to stderr, then raises `ImportError`): `import pandas` exits 0 on both binaries, and stderr holds `HIT pytz` 0 times on the snapshot and 2 times on the plain binary. An entry holding only `_hashlib.py` (writes `HIT _hashlib`): `import hashlib` exits 1 on both binaries, stderr holds `HIT _hashlib` once and ends in `AttributeError`. A set that changes any of these numbers fails the check, and the specification that changes the set restates them with its reason. Restated 2026-10-19 by spec 069 (Decision 5g): `HIT pytz` 2 times on both binaries; with no package pre-imported, pandas' import runs in the call on the snapshot too, after the prelude.
   - Stand-in: the prelude inserts at 0; the first part fails with 5 of 6 shadowed on the plain binary (`json`, `numpy`, `csv`, `uuid`, `host`) and 1 on the snapshot (`host`).
3. **`test_a_zip_on_the_import_path`** (v1.4). `lib.zip` in the grant (a module, a package with a data file, a `dist-info` with `METADATA`) and a `dist-info` folder beside it; `import_path=["/code", "/code/lib.zip"]`: the module's `__file__` is `/code/lib.zip/zmod.py`; `importlib.resources.files('zpkg').joinpath('data.txt').read_text()` equals the bytes written; `importlib.metadata.version` answers both distributions' versions. `import_path=["/code/missing.zip", "/code"]` still imports `mylib`, and the missing entry's `sys.path_importer_cache` value is `None`.
4. **`test_the_import_path_writes_nothing`** (v1.2). Importing `mylib` and `pkg` from a read-only entry, once as is and once after the program sets `sys.dont_write_bytecode = False`: `exit_code` 0, `stderr` empty, and the host folder's sorted listing and every file's SHA-256 are the same before and after (0 files added, 0 changed). A `.pyc` compiled in an earlier call through a writable grant, whose source was then rewritten to the same size with its times restored, is the one imported from a read-only entry (`X == 1`, and `__spec__.cached` names it).
5. **`test_a_writable_place_never_serves_the_import_path`** (v1.2). Each refused case raises before any work, and a door host that counts calls stays at 0; the message names `import_path[i]`. `code` below is a host folder holding `mylib.py`, granted read-only at `/code` unless a case says otherwise; `mem` is an in-memory provider.
   - `TypeError` (5 cases): `import_path="/code"`, `[b"/code"]`, `[Path("/code")]`, `[None]`, `5`.
   - `ValueError` for spelling (7 cases): `["code"]`, `["/code/"]`, `["/code/../x"]`, `["/"]` (its own message, "/ cannot be on the import path", pinned: the build review's F6), `["/usr/local/lib/x"]`, `["/code", "/code"]`, `["/co\0de"]`.
   - `ValueError` for the serving place (9 cases), each entry strictly under its server, so no nesting rule also applies (the review's F4c):
     - S1 the root: `root=True`, `["/x"]`;
     - S2 a writable grant at `/work`, `["/work/lib"]`;
     - S3 a read-only mount of `mem` at `/m`, `["/m/lib"]`;
     - S4 a writable mount of `mem` at `/w`, `["/w/lib"]`;
     - S5 nothing: no root, `["/nowhere/lib"]`;
     - S6 a read-only mount of `mem` at `/`, `["/lib"]`;
     - S7 the review's F1 layout: `mem` mounted read-only at `/lib` and writable at `/work`, `["/lib/lib"]`;
     - S8 a sibling name (F4a): `root=` an existing host folder apart from `code` (neither holding it nor at it, R1: else spec 017's rule refuses S8 first), the read-only grant at `/code`, `["/code2"]`;
     - S9 case (the build review's F1, R3): `root=` a host folder apart from `code`, the read-only grant of `code` at `/Code`, `["/code/lib"]`: served by the root, since the guest's match is case-sensitive, as the runner's must be.
   - `ValueError` for guest nesting (4 cases), each beside the read-only grant at `/code` with `["/code"]`: G1 a writable grant at `/code/out`; G2 a read-only mount of `mem` at `/code/out`; G3 a writable grant at `/code/a/b`; G4 (the build review's F1, R9) G1's layout with the entry second, `["/a", "/code"]` (a read-only grant at `/a`), refused naming `import_path[1]`.
   - `ValueError` for host nesting (5 cases): H1 a writable grant of `code/out` at `/out` with `["/code"]`; H2 `root=` the existing folder `code/r` with `["/code"]`; H3 `root=` the missing folder `code/new` with `["/code"]`, refused and not made (absent afterwards); H4 (F5) a folder `proj` with `proj/lib/mylib.py`, granted read-only at `/p`, the entry `["/p/lib"]`, and a writable grant of `proj/out` at `/out`; H5 (the build review's F1, R8) H1's layout with the entry second, `["/a", "/code"]`, refused naming `import_path[1]`.
   - **Allowed** (5 cases, each runs and imports `mylib` from its entry): A1 a writable grant at `/work` and a read-only grant at `/work/lib`, `["/work/lib"]`; A2 `root=True`, `["/code"]`; A3 a writable grant of a sibling of `code` at `/out`, `["/code"]`; A4 a writable grant at `/code2` beside `/code`, `["/code"]`; A5 (F6) the entry given as an instance of a `str` subclass whose value is `"/code"` and whose `__repr__` and `__str__` return `"'/code'] + [print('injected') or '/code'"` (R2: a payload that parses, so the stand-in below runs it): it runs, `sys.path[-1] == '/code'`, and stdout has no `injected`.
   - Stand-ins, each failing exactly these cases and no other:
     - no serving-place rule: S1 to S9 (9);
     - mounts accepted as read-only servers (the draft's Decision 9): S3, S6, S7 (3);
     - the serving place matched by text prefix (F4a): S8 (1);
     - the serving place matched case-insensitively (the build review's R3): S9 (1);
     - the serving place by the shortest prefix instead of the longest (F4b): A1 and A2, and H2 and H3, refused for the wrong reason (4; see the landing notes);
     - guest nesting by text prefix: A4 (1);
     - no guest-nesting rule: G1 to G4 (4);
     - guest nesting judged for the first entry only (R9): G4 (1);
     - no host-nesting rule: H1 to H5 (5);
     - host nesting judged for the first entry only (R8): H5 (1);
     - host nesting against the entry's own folder instead of the serving grant's (F5): H4 (1);
     - the prelude built from the caller's objects (`repr(list(import_path))` on the argument as given, F6): A5 (1);
     - the runner's own message for `/` changed (R19): V4 (1).
6. **The command line.** Unit (`tests/unit/test_cli.py`, the fake `run`): `--import-path /a --grant /a=x --import-path /b -- -c pass` reaches `run()` with `import_path=["/a", "/b"]` and one grant; `--import-path=/a` likewise; `--import-path` with no value exits 2; without the option `run()` receives no `import_path` keyword; the scan table gains `--import-path /a x.py`. v1.4, a real call: `wasi-python run --grant /code=<dir> --import-path /code -- -c "import mylib; print(mylib.VALUE)"` exits 0 with the value on `stdout` in the JSON; `--import-path /code` without the grant exits 1 with `"kind": "ValueError"`.
7. **Spec 006's guarantee is still judged.** `test_planted_code_never_runs` and the `sys.path` print in `test_v1_2_hostile_guest.py` pass unchanged (no `import_path` given).
8. **The judge.** `uv run pytest` is green with `--accept-judge` (new checks); **lost 0, grew 0** (the ratchet's fuel is the harness driver's; that a call without `import_path` keeps today's argv is held by criterion 1's frame pin, not by the ratchet: the build review's F2). `ruff check` and `ruff format --check` clean. If 049 has landed, `test_the_public_api_matches_its_snapshot` passes after `--write`, and the snapshot's diff is exactly Decision 10's three lines.
9. The README and CHANGELOG say what Decision 11 lists; the landing notes record the stand-ins' results and each check's seen-failing run.

## The owner's choices

Question 93 (`../questions-for-the-owner.md`): may a read-only mount serve an import-path entry, with a refusal when its provider is also mounted writable? Nothing waits on it: until it is answered, a mount serving an entry is refused (Decision 9), and that is what this specification builds. Decision 16 gave the feature and its two limits; decision 49 placed it in 0.1.0. The other choices here (a list rather than a flag, after the zip, a runner-only mechanism, the rule for names the runtime lacks) are made by §6's rules and carry their reasons; none loosens a default (§4.15): with no `import_path` every call is as today.

## Disposition of the pre-build review

The review: `../reviews/054-read-only-code-on-the-import-path-spec-2026-10-18.md` (written in the lane's evidence folder, `build/reviews-evidence/054-review/`, until the lane copies it). Each finding, and where it went:

1. **F1 (high), a shared provider plants code past every rule.** Fixed by the lane's ruling: mounts serve no entry (Decision 9, with the reviewer's run as its reason; Decision 3's mount bullet; Decision 4 refuses any mount under an entry). Question 93 asks the owner whether a read-only mount may serve one later, with the facts and a recommendation; meanwhile refused, nothing waits. Criterion 5 gains S3, S4, S6 and S7 and G2, and the stand-in "mounts accepted as read-only servers"; the draft's criterion 6 (a read-only mount on the import path) is removed and its measurements stay in the memo (§7) as input for question 93. The Problem, Terms, Intent, Scope (Out: a mount serving an entry), Design and Decision 11 follow.
2. **F2 (medium), the prelude's source in tracebacks.** Fixed: the prelude starts with `__import__('linecache')._interactive_cache.clear()` (Decision 7, with its reason). Criterion 1 gains `s_eval.py`, `s_exec.py` and standard input `eval('1/0')` among its byte-equal cases (11 in all), and stand-in (c), the memo's prelude, which fails exactly those three. Re-run for this revision: `revision_linecache.txt` (both binaries: the clearing prelude 3 of 3 equal per binary, the memo's 0 of 3).
3. **F3 (medium), entries supply names the runtime lacks, differently per binary.** Fixed: Decision 6's claims are corrected (the runtime wins for names it *has*), the rule for names it *lacks* is stated with its examples and its plain-versus-snapshot difference, with the reason it is stated rather than prevented; the README states it (Decision 11); criterion 2 pins today's answers (`pytz`: 0 on the snapshot, 2 on the plain binary; `_hashlib`: 1 and `AttributeError` on both), re-run for this revision in `revision_lacking_names.txt`; Scope (Out) names it.
4. **F4 (medium), criterion 5's cases and predictions.** Fixed: (a) case S8, `/code2` beside `/code` under a writable root, and the stand-in "matched by text prefix" (S8 only), with Terms' "Under" and Decision 3's sibling bullet; (b) the shortest-prefix stand-in now predicts A1 and A2; (c) every serving case puts the entry strictly under its server. The stand-in list now says "exactly these cases and no other" with a count for each, and adds "guest nesting by text prefix" against the new allowed case A4.
5. **F5 (low-medium), host nesting against the whole folder.** Fixed: Decision 5 says "the serving grant's whole folder" and gives the reason (a link inside a grant reaches any of its folders; one leaving it does not resolve; the reviewer's runs). Criterion 5 gains H4 (the `/p/lib` subfolder entry with a writable `proj/out`) and the stand-in that judges the entry's own folder (H4 only).
6. **F6 (low), the prelude from checked plain strings.** Fixed: Decision 2 keeps the plain strings `_guest_path` returns, and Decision 7's `_import_prelude` takes only that tuple. Criterion 5 gains A5, a lying `str` subclass, and the stand-in that builds the prelude from the caller's objects.
7. **F7 (low), the *Safety* sentence over-claims.** Fixed: Decision 11's sentence now reads "… each is served by a read-only grant, and nothing the same call can write lies under one (across calls, see *Grants*)", which also fits F1's outcome. The *Mounts* clause is reworded to say the runner never puts a mount or a writable place on the import path.

## Landing notes

Built 2026-10-18 by the author (Claude Opus 5.5) on `spec/054-read-only-code-on-the-import-path` in `../wasi_python-054`, from main `62d2c56`, after the reviewer's Confirmation. **Not yet reviewed and not accepted.** Every claim below was run (EXECUTED) on arm64 macOS, CPython 3.14.2 under uv, wasmtime-py 49.0.0, against the frozen artifact set `build/sets/s-f94dec535086b06c` of the main tree (read only; `WASI_PYTHON_ARTIFACTS` set to it, never `build/artifacts`). Logs are in the worktree's `build/` (ignored); the ones a reviewer needs are copied to `build/reviews-evidence/054-review/build/` in the main tree.

### Commits

- `615e447` the Confirmation's R1 and R2 written in; status "confirmed for build".
- `9063ff3` build step 1: the checks, seen failing.
- `3ccb6b4` build step 2: `import_path=` and `--import-path` (runner and command).
- `9dedc19` criterion 5 matches each serving refusal's reason (see "Stand-ins").
- `8c5bc7a` build step 3: README and CHANGELOG.
- `799f391` the nothing-written check's helper renamed `_digests`: `test_rules`'s "no module-level name bound twice" found `_tree` already bound at line 511 of the v1.2 file. Step 1 committed it with that defect; the fast tier caught it before any acceptance.
- the commit carrying these notes.

### What was built

- `runner.py`: `import_path: Iterable[str] = ()` on `run` and `run_async`, right after `mounts`, and a docstring sentence (prose, as the rest of today's `run` docstring; Decision 10's "054 first" path, since 049 has not landed here). `_check_places` takes it and returns `import_path` and `import_serving`. `_under` (whole-component containment). `_check_import_path` (Decisions 2 to 4: the type; `/` with its own message; `_guest_path`'s rule; duplicates; the serving place by the longest whole-component prefix among grants, mounts and the root; a mount refused as server; a writable server refused; nothing serving refused; a writable grant or any mount under an entry refused; the plain strings and the serving grant's index kept). `_judge_import_path` (Decision 5, by identity against each serving grant's whole walked folder, called in `_walk_grants` after `_judge` and before a missing root is made). `_import_prelude` (Decision 7's line, from the kept plain strings, passed again through `str.__str__`), used in `_instance`: `wasi.argv = [ARGV0, *_import_prelude(…), *argv]`, and `[]` without entries, so the argv is today's.
- `cli.py`: `--import-path GUEST` (append, in `VALUED`), passed as `import_path=` only when given.
- Checks: v1.4 `test_the_import_path_reaches_every_mode`, `test_the_import_path_comes_after_the_runtime`, `test_a_zip_on_the_import_path` (each `[plain]`, `[snapshot]`) and `test_the_command_takes_import_paths`; v1.2 `test_the_import_path_writes_nothing` and `test_a_writable_place_never_serves_the_import_path` (each both binaries); unit `test_import_paths_reach_run_in_the_order_typed`, `test_an_import_path_without_a_value_is_a_usage_error` and a scan-table row in `tests/unit/test_cli.py`.
- README: *Grants* gains "The import path"; *From any language* names `--import-path`; *Any other embedder* gains Decision 11's sentence; *Mounts*' wrong `sys.path` clause is replaced; *Safety*'s sentence is F7's. CHANGELOG: one entry under `0.1.0a4 — unreleased` (main's CHANGELOG still has that section open, checked at the end).

### Seen failing first

Against the runner before step 2 (the branch at `9063ff3`): all 11 new goal checks fail (`run() got an unexpected keyword argument 'import_path'`, and the command's case on its missing `exit_code`), `build/054-seen-failing-main.txt`; the unit case `test_import_paths_reach_run_in_the_order_typed` and the new scan row fail. The usage-error unit case passed already (an unknown option is exit 2 too); it guards.

### Stand-ins

`build/054-mut/run.py` copies `src/` to a scratch folder, makes one text change to `runner.py` (each asserted to apply exactly once), and runs the named checks with that copy first on `PYTHONPATH`; `results.txt` holds the lines. Every stand-in fails its checks on both binaries:

| stand-in | the spec's prediction | seen |
|---|---|---|
| 1a: the prelude passes `sys.argv[2:]` | every mode case | both checks fail at the first mode (`-c` is read as a script name) |
| 1b: the prelude passes `sys.argv` whole | missing script, `orig_argv` | 2 of 11 byte-equal cases differ |
| 1c: the memo's prelude, no `linecache` clear | the last three | 3 of 11 differ |
| 2: entries inserted at 0 | plain 5 shadowed, snapshot 1 | plain `['json', 'numpy', 'csv', 'uuid', 'host']`, snapshot `['host']` |
| no serving-place rule | S1 to S8 | S1 to S8 (8) |
| mounts accepted as read-only servers | S3, S6, S7 | S3, S6, S7 (3) |
| serving place by text prefix | S8 | S8 (1) |
| shortest prefix instead of longest | A1, A2 | **A1, A2, H2, H3** (4) |
| guest nesting by text prefix | A4 | A4 (1) |
| no guest-nesting rule | G1 to G3 | G1 to G3 (3) |
| no host-nesting rule | H1 to H4 | H1 to H4 (4; H3 twice: it ran, and the refused root was made) |
| host nesting by the entry's own folder | H4 | H4 (1) |
| the prelude from the caller's objects | A5 | A5 (1: it printed `injected`) |

Two differences from the spec's text, both because the check is stricter than criterion 5 asks: it matches each refusal's **reason**, not only its type and `import_path[i]`.

- **Shortest prefix also fails H2 and H3.** With `root=` a path, the shortest prefix is the root, so H2 and H3 are refused as "served by the root" instead of for host nesting. A refusal for the wrong reason is counted wrong.
- **The first run of "no serving-place rule" saw 7 of 8**: S2 (a writable grant at `/work` serving `/work/lib`) was still refused, by the host-nesting rule (the serving grant's own folder is a writable grant's), and the check's first regular expression accepted that message. `9dedc19` makes the serving cases match "is served by …, which is writable; only a read-only grant", so S2 refused for another reason counts as wrong: 8 of 8 on the re-run.
- The stand-in "host nesting by the entry's own folder" is emulated: the runner never walks an entry's subfolder, so the stand-in skips host nesting when the entry is not the serving grant's own guest path, which is what a "precise" implementation would allow for H4.

### Criteria

1. Every mode: passes, both binaries; 11 of 11 byte-equal cases. Stand-ins 1a to 1c above.
2. After the runtime: passes; 0 of 6 shadowed; order among entries; the pins (pytz 0 on the snapshot, 2 on the plain binary; `_hashlib` once and `AttributeError` on both). Stand-in 2.
3. A zip: passes, both binaries (`/code/lib.zip/zmod.py`, the resource, `1.2 3.4`; the missing entry's importer `None`).
4. Writes nothing: passes, both binaries (0 files added or changed, stderr empty, with and without `sys.dont_write_bytecode = False`; the `.pyc` gives `X == 1`).
5. 32 cases: passes, both binaries. Stand-ins above.
6. The command line: the unit cases and the v1.4 call pass (exit 0 with the module's value; exit 1, `ValueError`, naming `import_path[0]`, without the grant).
7. Spec 006's guarantee: `test_planted_code_never_runs` and the v1.2 file's `sys.path` check pass unchanged (in the fast tier below).
8. The judge: below; lost 0, grew 0. ruff check and ruff format --check: clean. 049 has not landed here, so there is no snapshot to regenerate.
9. README and CHANGELOG: as listed above.

Fuel of the prelude with the `linecache` clear, a benchmark fact (one run each, `-c pass`, a read-only grant at `/code`): snapshot 82,066,061 without and 85,458,178 with `import_path` (+3.39 M); plain 242,561,175 and 244,106,174 (+1.54 M). The spec's +3.26 M and +1.33 M were measured without the clear.

### The judge

`WASI_PYTHON_ARTIFACTS=…/build/sets/s-f94dec535086b06c uv run pytest -m "not slow"` (`build/054-fast.txt`), no `--accept`:

```
wasi_python v1: 270/319 pass · 0 gap · 10 blocked · 0 fail · 39 deselected   (unit suite 1020/1028, 8 skipped)
  v1.2  portable, sealed    60/61  blocked 1
  v1.4  embedding           132/132
ratchet vs 34eb315196: lost 0 · absent 0 · unrun 0 · unrun locally 8 · gained 11 · grew 0 · upstream unrun 31 · not selected 27 · judge changed: tests/checks/test_v1_2_hostile_guest.py, tests/checks/test_v1_4_embedding.py, tests/unit/test_cli.py
1290 passed, 18 skipped, 39 deselected
```

The full judge once, the same way (`build/054-full.txt`), no `--accept`:

```
wasi_python v1: 277/319 pass · 0 gap · 42 blocked · 0 fail   (unit suite 1020/1028, 8 skipped)
  v1.2  portable, sealed    60/61  blocked 1
  v1.3  data stack          26/58  blocked 32
  v1.4  embedding           132/132
ratchet vs 34eb315196: lost 0 · absent 0 · unrun 0 · unrun locally 28 · gained 11 · grew 0 · upstream unrun 31 · judge changed: tests/checks/test_v1_2_hostile_guest.py, tests/checks/test_v1_4_embedding.py, tests/unit/test_cli.py
1297 passed, 50 skipped
```

The 32 blocked v1.3 checks are numpy's and pandas' own suites, which need the source trees under `build/` that this worktree does not have ("source tree numpy 17 · source tree pandas 16 · oracle 1"); they are "unrun locally", not lost. The lane's run in the main tree has them.

### For the build review

- Decision 5 is judged against each serving grant's whole folder (`_judge_import_path`); H4 and its stand-in hold it. Check that a missing root inside a serving grant is refused before `_make_missing` (H3: the folder is absent afterwards).
- The prelude is built from `str.__str__` of the kept strings twice over (`_check_import_path` keeps `_guest_path`'s plain value; `_import_prelude` passes each through `str.__str__` again). The A5 stand-in had to remove both.
- `_check_places` now checks mounts before the import path and returns them under the same key; 049's builder changes `_check_places` too (one read of the defaults), so the lane's rebase may meet a small conflict there; the two changes are independent.
- Criterion 5's check is stricter than the spec's text (reasons are matched), which is why the shortest-prefix stand-in fails 4 cases, not 2.
- The README example in *The import path* is illustrative (its `helpers` and `toolbox` are the reader's); every claim around it is a check above.
- The runner's message for `/` is its own (Decision 2); the others reuse `_guest_path`'s.
- Not run here: Windows and Linux. The v1.4 checks are in the file `verify` runs on all three systems, so the release dry run meets them there; the host-nesting rule uses spec 017's identities, which that job already exercises.

### Revised against the build review

The build review (`../reviews/054-read-only-code-on-the-import-path-2026-10-18.md`, in the lane's evidence folder `build/reviews-evidence/054-buildreview/` until the lane copies it; verdict: lands once F1 to F4 are fixed) found no defect in the refusal logic and four gaps in judge strength and wording. All four are fixed, plus F6's three optional points; F5 is the rebase (below). EXECUTED against spec 035's set `build/sets/s-c4190ca065ada03a` (the coordinator's instruction: `s-f94dec535086b06c` is stale).

- **F1.** Criterion 5 gains S9 (`/Code` granted, `/code/lib` named, a root apart: served by the root), G4 and H5 (G1's and H1's layouts with the entry second, refused naming `import_path[1]`). The review's mutants, added to `build/054-mut/run.py`, each fail exactly their case on both binaries: R3 (case-insensitive serving) S9; R8 (host nesting for the first entry only) H5; R9 (guest nesting for the first entry only) G4.
- **F2.** Criterion 1 gains a `run_async` call with `import_path=["/code"]`, and the frame pin (`2` without an import path, `4` with). R22 (`run_async` dropping the argument) fails the first; R17 (the prelude on every call) fails the second (`4`, `4`). Decision 7 and criterion 8 now say the ratchet cannot see a prelude added to every call, and that the pin holds it.
- **F3.** README *Safety*: "… and no folder the same call's root or grants can write lies under one (a hard link, a writable mount whose store is an entry's folder, and other calls are yours to keep apart: see *The import path*)"; *The import path* names both same-call routes beside the cross-call one. Decision 11 says so.
- **F4.** README: "reaches the recursion limit two frames sooner (996 frames of its own instead of 998); and a call with an import path costs more fuel, about 3.5 M on the snapshot and about 1 M (0.5 to 2 M) on the plain binary. A call without one is unchanged." Decision 7 carries the built range on 035's set: the review's +3.41 M to +3.58 M (snapshot) and +0.90 M to +1.94 M (plain), and the author's two pairs per binary, snapshot 81,870,647 → 85,316,454 (+3.45 M) and 81,868,465 → 85,217,404 (+3.35 M), plain 151,431,836 → 151,938,455 (+0.51 M) and 151,451,729 → 152,448,320 (+1.00 M). (Plain `-c pass` is 151 M on 035's set, against 242 M before: 035's reader.) The author's recursion probe counts 997 and 995 calls of its own function: the same two-frame difference, from a different base than the review's 998 and 996.
- **F6 (optional, done).** An entry `/a'b"c\d` in criterion 1 (R13, naive quoting, fails it with a guest `SyntaxError`); V4 pins the runner's message for `/` (R19 fails it). R14 and R15 (each of F6's two layers alone) are defence in depth, as the review says; unchanged.
- Every earlier stand-in, re-run on 035's set, fails as before, with the counts the new cases add: no serving-place rule S1 to S9 (9); no guest-nesting rule G1 to G4 (4); no host-nesting rule H1 to H5 (5, H3 twice); the others unchanged (`build/054-mut/results.txt`).
- **The fast tier on this branch against 035's set is red for a reason outside 054:** `lost 1` (`test_manifest_recipes_match_the_tree`: the set's MANIFEST names `recipes/zip_directory.py` and other 035 files this pre-035 tree lacks) and `grew 4` (the binaries' bytes and one harness-driver fuel, 035's). Every 054 check passes. The rebase onto main, which carries 035, removes the mismatch; the judge lines after the rebase are below.

### Rebased onto main

The coordinator asked the author to rebase once spec 049 had landed (the build review's F5). `git rebase main` from `af50169` onto main `3dfdab4` (049 landed, accepted as `6d6dfc5`; 035, 056 and the 0.1.0a4 release before it). Twelve commits replayed; three conflicted:

- **`context/questions-for-the-owner.md`** (at the pre-build revision): context only. Main had added questions 91, 94 and 92 where 93 went; both kept, 93 last. A blank line lost before `### 93.` is restored in the snapshot commit below.
- **`src/wasi_python/runner.py`** (at build step 2), four hunks. Both signatures: 049's docstrings kept (Google style, no spec numbers), 054's prose docstring dropped, and an `Args:` entry for `import_path` written after `mounts`, the same text in `run` and `run_async` (049, Decision 10). The two `checked.update(_check_places(…))` calls are gone: 049 moved that call into `_checked`, so `_checked` takes `import_path=` (keyword-only, default `()`) and both `run` and `run_async` pass it. `_check_places`: 049's fifth positional `limits` kept, and `import_path` made keyword-only after `*`, so no positional call can mistake one for the other; `limits.file_calls` replaces the old `DEFAULTS.file_calls`.
- **`CHANGELOG.md`** (at build step 3): 0.1.0a4 is released, so 054's entry moved to the top of `0.1.0a5 — unreleased`, above 049's; the merged file equals main's plus that one entry (`diff` shows nothing else).
- README auto-merged; *The import path* and the other passages sit beside 049's new `## API reference`.

Then `uv run python tests/harness/api.py --write`: `tests/public_api.txt` gains exactly Decision 10's three lines (`param import_path: Iterable[str] = ()  keyword-only` under `run` and under `run_async`, after `mounts`; `option --import-path GUEST  append` under the command); the README's generated reference gains `run`'s signature line and `Args:` entry, `run_async`'s signature line (its short form shows only `executor`), and the options table's row. `--check` then exits 0.

Re-run on the rebased branch, against `s-c4190ca065ada03a`, no `--accept`:

- every stand-in and mutant (`build/054-mut/run.py`, R22's anchor moved to `run_async`'s `_checked` call): each fails exactly as listed in "Revised against the build review" (R22 fails the `run_async` case, which now guards the argument 049's structure threads through).
- the fast tier (`build/054-fast-r3.txt`):

  ```
  wasi_python v1: 305/354 pass · 0 gap · 10 blocked · 0 fail · 39 deselected   (unit suite 1059/1067, 8 skipped)
    v1.2  portable, sealed    60/61  blocked 1
    v1.4  embedding           147/147
  ratchet vs 323ad21aa5: lost 0 · absent 0 · unrun 0 · unrun locally 8 · gained 11 · grew 0 · upstream unrun 31 · not selected 27 · judge changed: tests/checks/test_v1_2_hostile_guest.py, tests/checks/test_v1_4_embedding.py, tests/public_api.txt and 1 more
  1364 passed, 18 skipped, 39 deselected
  ```
- none of 054's checks is marked slow; the full judge once (`build/054-full-r3.txt`):

  ```
  wasi_python v1: 312/354 pass · 0 gap · 42 blocked · 0 fail   (unit suite 1059/1067, 8 skipped)
    v1.3  data stack          46/78  blocked 32
    v1.4  embedding           147/147
  ratchet vs 323ad21aa5: lost 0 · absent 0 · unrun 0 · unrun locally 28 · gained 11 · grew 0 · upstream unrun 31 · judge changed: tests/checks/test_v1_2_hostile_guest.py, tests/checks/test_v1_4_embedding.py, tests/public_api.txt and 1 more
  1371 passed, 50 skipped
  ```

  The 32 blocked v1.3 checks are numpy's and pandas' own suites, whose source trees this worktree lacks; they are unrun locally, not lost.
- ruff check and ruff format --check: clean.

## Disposition of the build review

1. **F1 (low-medium), three unsafe mutants passed.** Fixed: S9, G4, H5 in criterion 5, each seen failing on its mutant (R3, R9, R8) and passing on the built runner.
2. **F2 (low-medium), two paths unrun.** Fixed: the `run_async` case and the two-frame pin in criterion 1, seen failing on R22 and R17; Decision 7 and criterion 8 corrected.
3. **F3 (low), the *Safety* sentence over-claimed.** Fixed: the sentence is narrowed to folders of the same call's root and grants, and names the hard link and the writable mount's store as the embedder's, as other calls are; *The import path* says the same.
4. **F4 (low), two README omissions and stale numbers.** Fixed: the README states the recursion limit two frames sooner (996 instead of 998) and the fuel cost; Decision 7 carries the built range on 035's set.
5. **F5 (the rebase).** Done by the author after 049 landed: see "Rebased onto main".
6. **F6 (info).** Done: the odd entry (R13) and V4's message (R19); R14 and R15 left as defence in depth.

**Landed 2026-10-18** through the lane. Its pre-build review (`../reviews/054-read-only-code-on-the-import-path-spec-2026-10-18.md`) and its build review (`../reviews/054-read-only-code-on-the-import-path-2026-10-18.md`: "lands once F1 to F4 are fixed", then, after the builder's revision and its rebase onto spec 049, "confirmed, it lands") were committed on the detached HEAD as `5f56591`. The lane rebased once more onto main `c7b7f26` (AGENTS.md rule 6b only); `git range-diff` shows all fourteen commits unchanged (`=`). The full judge there, on spec 035's artifact set: `wasi_python v1: 340/354 pass · 12 gap · 2 blocked · 0 fail (unit suite 1065/1067, 2 skipped)`, `ratchet vs 5f56591135: lost 0 · absent 0 · unrun 0 · gained 0 · grew 0` after acceptance, `1405 passed, 4 skipped, 12 xfailed in 903.58s` (EXECUTED, `build/lane-054-accept.log`). Accepted with `--accept-judge` as `c79a3a9` (history line 54); the rules tier passed (24/24); main fast-forwarded. Owner question 93 (read-only mounts on the import path) stays open; nothing waits on it.
