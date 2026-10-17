# Review of 014 — The inputs are checked (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the
  constitution, `context/reviews/README.md`, the 013 pre-build review (for its format), spec 006
  Decision 2 (the environment), the specification, the placeholder memo, `run` and `_instance` in
  `src/wasi_python/runner.py`, wasmtime-py 49's `WasiConfig` (`wasmtime/_wasi.py`), and the
  wasmtime and CPython code named below. Spec 013 is built in the working tree and under its own
  review; I read it for context only. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/014-the-inputs-are-checked.md` as drafted (untracked).
  The runner is the working tree on `513455e`, with spec 013's uncommitted change in it.
- **Ran (EXECUTED, darwin-arm64, host CPython 3.14, wasmtime-py 49.0.0, the artifacts in
  `build/artifacts/` read only, `WASI_PYTHON_CACHE=$PWD/build/cwasm-cache`).**
  - The author's `inputs_probe.py`, re-run: its output is byte-identical to `inputs_before.txt`
    (`rev014a/inputs_rerun.txt`, `diff` empty).
  - My scripts and outputs are under
    `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev014a/`:
    - `n1_native.py` → `n1_native.txt`: what native `subprocess`, `os.execve` and `os.putenv`
      refuse, on this host;
    - `p1_today.py` → `p1_today.txt`: today's `run` on inputs the specification's table leaves
      out (surrogates, iterables, odd keys, odd `stdin` values);
    - `p2_sizes.py` → `p2_sizes.txt`: large `argv`, `env` and `stdin` against the memory cap;
    - `p3_env_override.py` → `p3_env_override.txt` and `p4_home.py` → `p4_home.txt`: what a
      caller's `env` can steer on a reused root where an earlier guest planted files;
    - `p5_leading_eq.txt` and `p6_denylist.txt`: one-line probes (the command is in each
      finding) of a key `"=K"`, and of a key that smuggles `HOME` past a filter.
    - Roots for `p3`/`p4` were made under `rev014a/roots/`, never in the tree.
  - I did not run `uv run pytest`. Nothing is built yet, and the scoreboard is the build
    review's job.

## What holds

- **The defect is real and reproduces.** EXECUTED: every row of the table matches my re-run.
- **The motivating case is worse than the table says, which supports the specification.**
  EXECUTED (`p6_denylist.txt`), on both binaries:
  - `env={"HOME\0x": "/shared"}` gives the guest `HOME='/shared'`. The key is cut to `HOME`,
    and wasmtime receives two `HOME` entries; the guest keeps the later one. So a host that
    filters keys by a deny-list (refusing `HOME`) is bypassed, and spec 006's per-call `HOME`
    is replaced.
  - `env={"HOME=/shared": ""}` gives `HOME='/shared='`.
  - `env={"PYTHONTZPATH\0": "/tz"}` gives `zoneinfo.TZPATH == ('/tz',)`.
  - The specification should cite this as the concrete harm (finding 5).
- **Where the NUL is lost.** READ: wasmtime-py's `to_char_array` does `c_char_p(s.encode('utf-8'))`
  (`wasmtime/_wasi.py:190-194`). ctypes keeps the NUL in the buffer, and the C API reads each
  string with `CStr::from_ptr(..).to_str()` (`crates/c-api/src/wasi.rs:67-109` in
  `wasmtime-v49`), which stops at the first NUL. The `=` split happens in the guest:
  `environ_get` writes `k`, `=`, `v`, NUL (`crates/wasi/src/p1.rs:1234-1260`), and the guest
  splits at the first `=`.
- **Refusing NUL, `=` and the empty key is right, and nothing stricter is needed.**
  - EXECUTED (`p1_today.txt`): keys that are non-ASCII (`"KÉ"`), start with a digit (`"1K"`)
    or hold a space (`"A B"`), and an empty value, all reach the guest exactly. Native
    `subprocess` and `os.putenv` accept them too (`n1_native.txt`). WASI preview1 puts no rule
    on names beyond the `k=v\0` layout (READ, `p1.rs` above). So the specification should
    **not** refuse them. It does not, and that is right.
  - EXECUTED (`p5_leading_eq.txt`): a key `"=K"` and a key `""` both make the guest's start-up
    fail on both binaries: `<reactor>` line 98, `os.environ.update`, `OSError: [Errno 28]`.
    So "no `=` anywhere" (not only after the first character) is right for this guest.
- **Refusing `str` for `stdin`, and `0`, is right.** A falsy non-bytes value is a caller's bug;
  today `""`, `0`, `False` and `[]` all silently become empty input (EXECUTED, `p1_today.txt`).
  The reason given needs correcting (finding 3).
- **An empty `argv` stays allowed.** Right: `run([])` is used by
  `tests/checks/test_v1_2_hostile_guest.py:240`.
- **No existing caller passes a value the new rules refuse.** READ, by grep of `tests/`, `src/`,
  `scripts/`, `README.md` and `.github/workflows/release.yml`:
  - every `run(...)` call passes a `list` of `str` literals or f-strings;
  - no call passes `env=` to `run` (the `env=` at `test_v1_4_embedding.py:65` goes to the
    judge's driver, `tests/harness/guest.py`, which builds its own `WasiConfig` and does not go
    through `run`; the ones at lines 230 and 259 go to `subprocess.run`);
  - the one `stdin=` is `b"c\n"` (`test_v1_2_hostile_guest.py:341`);
  - the release workflow and the README example pass a list of `str`.
- **No silent truncation from size.** READ: `args_sizes_get` and `environ_sizes_get` sum the
  lengths into a `usize` and `try_into` a `u32`, returning `Errno::Overflow` past 4 GiB
  (`p1.rs:1214-1279`); there is no other limit in wasmtime. EXECUTED (`p2_sizes.txt`): an
  8 MiB argument, an 8 MiB value and 100,000 arguments arrive whole. Past the guest's memory,
  the call fails; it is not cut short (finding 7).

## Acceptance criteria against evidence

1. The unit tests and the v1.4 check exist and are seen failing first. Checkable as written.
   Today `run` with a NUL in `argv` or an `env` key, or an `=` in a key, returns exit 0
   (EXECUTED), so the v1.4 check fails first. The unit list misses the cases in findings 1, 2,
   3 and 6.
2. `uv run pytest` green with `--accept-judge`. Right: new checks change the judge hash.
3. A dry run of the release workflow passes. Right, since `README.md` and `CHANGELOG.md` change.

## Findings, most severe first

1. **A `str` that is not valid UTF-8 text is not covered, and it fails late, naming nothing.**
   Medium. It breaks the specification's own intent.
   - READ: wasmtime-py encodes every argument, key and value with strict UTF-8
     (`_wasi.py:193`), and the C API takes only valid UTF-8 (`wasi.rs:73-76`, `98-105`). WASI
     strings here are UTF-8.
   - EXECUTED (`p1_today.txt`): `argv=[..., "\ud800"]`, `argv=[..., "\udcff"]`,
     `env={"K\ud800": "v"}` and `env={"K": "\udcff"}` each raise
     `UnicodeEncodeError: 'utf-8' codec can't encode character ... surrogates not allowed`.
   - It is raised from `_instance` (`runner.py`, the `wasi.argv` and `wasi.env` lines). That is
     after the artifacts are found, the module compiled, the stdlib zip placed in a `root=` and
     the per-call `HOME` made. So it is not "before any work", and it names no argument.
   - It is not exotic. `\udc80`–`\udcff` are what `os.environ`, `os.listdir` and `sys.argv` hold
     for bytes that are not UTF-8 (surrogateescape). A host doing `env=dict(os.environ)`, or
     passing a file name it listed, hits it. Native `subprocess` passes such strings on as raw
     bytes (EXECUTED: `"\udcff"` in argv and in a key run fine), but WASI cannot carry them.
   - Fix: add a rule to Decision 2 for every `str` in `argv` and `env`: it must encode as UTF-8
     (no surrogate code points), else `ValueError` naming the argument, for example
     "argv[2] is not valid UTF-8 text (it holds a surrogate)". `UnicodeEncodeError` is already
     a `ValueError`, so the type of error does not change; the place and the message do. Add
     `"\ud800"` and `"\udcff"` to the unit tests, in an argument, a key and a value.
2. **"Any sequence" refuses iterables that work today.** Medium-low. It breaks working code.
   - EXECUTED (`p1_today.txt`): `argv=(a for a in ["-c", code, "g"])` (a generator) runs
     correctly today, because the runner does `[ARGV0, *argv]`. So does
     `argv={"-c": 0, code: 0}.keys()`. Neither is a `collections.abc.Sequence`.
   - Native `subprocess` accepts any iterable (EXECUTED, `n1_native.txt`: a generator runs).
   - Proposal: accept any iterable except `str`, `bytes`, `bytearray` (and `memoryview`, whose
     items are ints and would be refused anyway), and consume it exactly once with `list()`,
     catching `TypeError` for a non-iterable. The checked list is what `run` passes on, so a
     generator is never read twice.
   - If the author keeps "sequence", the specification and the CHANGELOG line must name the
     break: "a generator or other non-sequence iterable as `argv` is now refused".
   - The same applies, more weakly, to `env`. Today `{**env}` takes any object with `keys()` and
     `__getitem__`. An `isinstance(env, Mapping)` test refuses one that is not registered
     (INFERRED; no caller does this). Either accept what `{**env}` accepts, or name it.
3. **Two reasons in the specification misstate native CPython.** Medium-low. §4.10: a claim must
   be true as stated. The rules themselves are right.
   - "These are `subprocess`'s rules" (Decision 2, `env`). EXECUTED on this host
     (`n1_native.txt`):
     - POSIX `subprocess` **accepts an empty key**: the child sees `{'': 'v'}`. It refuses any
       `=` (READ, `Lib/subprocess.py:1903-1906`).
     - `os.execve` refuses the empty key ("illegal environment variable name") but **accepts a
       leading `=`**: `{"=K": "v"}` reaches the exec. It checks for `=` from the second
       character on (READ, `Modules/posixmodule.c:6922-6923`). Windows does the same, so that
       `=C:`-style hidden variables pass (READ, `Modules/_winapi.c:1102-1105`).
     - `os.putenv("")` raises `OSError: [Errno 22]`.
     - So the specification's rule (non-empty, no `=` anywhere, no NUL) is the strictest of
       the native rules, not any one of them. That is right for this guest, because the
       guest's start-up fails on both `""` and `"=K"` (EXECUTED, `p5_leading_eq.txt`). Say
       that: "the union of `subprocess`'s and `os.execve`'s rules, because the guest fails
       on an empty or leading-`=` name". Add `"=K"` to the table and the unit tests.
   - "As `subprocess.run(input=…)` refuses one in binary mode" (Decision 2, `stdin`).
     EXECUTED: `subprocess.run(input="hi")` raises `TypeError`, but `input=""` and `input=0`
     run with no error, because `communicate` skips a falsy input. Refusing them is still
     right. Give the true reason: the type rule holds whatever the value, and a falsy
     non-bytes value is a caller's bug. Add `False` and `[]` to the unit tests; both are
     silently empty today (EXECUTED).
4. **A caller's `env` can undo spec 006's per-call `HOME`, and the specification should say
   what that costs.** Medium-low. It is allowed by design (spec 006 Decision 2: "can be
   overridden but not removed"), and the caller is trusted. But Decision 3 restates the
   permission with no consequence attached.
   - EXECUTED (`p4_home.txt`), on a reused `root=` where a first guest call planted files:
     - with `env={"HOME": "/shared"}`, `pdb.Pdb().rcLines` in a second call holds the planted
       `/shared/.pdbrc` (`['print("PDBRC RAN")\n']`). pdb runs these lines when a program
       starts the debugger. This is exactly what spec 006 made `HOME` fresh to prevent;
     - with `env={"PYTHONTZPATH": "/tz"}`, `zoneinfo.ZoneInfo("Fake")` parses the planted file
       (`ValueError: invalid literal for int()`), instead of the zip's tzdata.
   - EXECUTED (`p3_env_override.txt`): `PYTHONPATH`, `PYTHONUSERBASE` and a `HOME` holding a
     planted user-site `.pth` have no effect on either binary. `sys.path` stays the stdlib zip
     alone and `site.ENABLE_USER_SITE` is `None`. So `HOME`, `TMPDIR` and `PYTHONTZPATH` are the
     variables whose override matters, and only on a reused root (a fresh root has nothing
     planted).
   - Fix, text only: Decision 3 should say "a caller who sets `HOME`, `TMPDIR` or
     `PYTHONTZPATH` to a path in a reused root gives up spec 006's protection for it: the call
     reads what earlier calls left there". The README's environment sentence and its
     **Not protected** list should say the same. No code change: refusing the override would
     break spec 006's stated contract.
5. **The defect should name the concrete harm: a key filter is bypassed.** Low. EXECUTED
   (`p6_denylist.txt`, command
   `run(["-c", "import os, zoneinfo; print(repr(os.environ['HOME']), zoneinfo.TZPATH)"], env=…)`
   for each `env` below, both binaries):
   - `{"HOME\0x": "/shared"}` → `HOME='/shared'`; `{"HOME=/shared": ""}` → `HOME='/shared='`;
     `{"PYTHONTZPATH\0": "/tz"}` → `TZPATH=('/tz',)`.
   - "A host that passes untrusted text as an environment key" is too broad: a host that lets
     an untrusted party choose any key has already handed over `HOME` and `PYTHONTZPATH`, with
     or without this specification. What the specification fixes is a host that **filters**
     keys (a deny-list, or an allow-list compared before the cut) and is bypassed by a NUL or
     an `=`. Say that, and make `{"HOME\0x": …}` one of the v1.4 check's cases: it is the
     row that shows a protected variable being replaced.
6. **The `stdin` rule needs three details pinned down.** Low.
   - **Non-contiguous buffers.** EXECUTED: `stdin=memoryview(b"abcdef")[::2]` raises
     `BufferError: memoryview: underlying buffer is not C-contiguous` today, late, from
     `Path.write_bytes`. "Passed on as `bytes`" fixes it, since `bytes()` of any buffer is
     contiguous. Add it to the unit tests. A multi-dimensional or `array('i')` buffer is passed
     as its raw bytes today (EXECUTED); say that this stays.
   - **How to test for the buffer protocol.** READ: `requires-python = ">=3.11"`
     (`pyproject.toml:6`). `collections.abc.Buffer` exists only from 3.12, so the test must be
     `memoryview(x)` in a `try`, turning its `TypeError` into one that names `stdin`.
   - **The copy and the cap.** `bytes(x)` copies a `bytearray` or `memoryview`, so a large one
     costs its size again for the call (INFERRED). An exact `bytes` is not copied:
     `bytes(b) is b` (EXECUTED). The copy is the right choice: the guest then sees the input as
     it was at the call, even if the caller changes a `bytearray` afterwards. Say so.
     No cap is needed. EXECUTED (`p2_sizes.txt`): 128 MiB of `stdin` under a 96 MiB memory cap
     runs, and the guest's own `sys.stdin.buffer.read()` raises `MemoryError` inside the guest.
     The runner writes `stdin` to a host temporary file and the guest reads it on demand, so the
     memory cap already bounds the guest, and the bytes are the caller's own. The README should
     say that `stdin` is written to a temporary file of its size under `tempfile.gettempdir()`.
7. **An `argv` or `env` larger than the guest's memory fails with no message.** Low; document,
   do not check. EXECUTED (`p2_sizes.txt`): a 128 MiB argument, or a 128 MiB value, under
   `memory_bytes=96 << 20`, returns `exit_code=1`, `trapped=None` and empty stderr. Below the
   snapshot's minimum memory (902 pages), the call traps at instantiation instead, as for any
   call. Nothing is truncated, so this is not the specification's defect. The runner cannot
   know the guest's own overhead, so a host-side size check would be a guess. One README
   sentence is enough: "arguments and environment are copied into the guest's memory at
   start; if they do not fit, the call exits 1".
8. **Error messages must not echo values.** Low. Decision 1 says each message names the
   argument; it should also say it does not quote the value. Environment values are often
   secrets (tokens, keys), and an argument can be a whole program of megabytes. Name the
   position or the key: `argv[2]: embedded null byte`, `env['API_TOKEN']: embedded null byte`.
   A key with a NUL should be shown by `repr`, cut to a few dozen characters. Native
   `subprocess` quotes neither (EXECUTED, `n1_native.txt`).
9. **Two small choices to state.** Low.
   - **`os.PathLike` items in `argv`.** `subprocess` accepts them (EXECUTED). Today `run`
     raises `AttributeError` (EXECUTED). Refusing them is right here, and the reason is worth a
     sentence: a host `Path` names a host file, while the guest sees the root at `/`, so
     passing one is usually a mistake (INFERRED).
   - **Plain values out.** "Passed on as a `list[str]`" should mean plain `str`, not a `str`
     subclass, as spec 013 passes plain `int` on. wasmtime-py calls each item's `.encode`
     (READ, `_wasi.py:193`), which a subclass can override. `str.encode(x, "utf-8")` does
     finding 1's check and ignores any override; `str(x)` does not, since it calls a subclass's
     `__str__`.

## Constitution checks

- §4.4 two imports, §4.6 artifacts: untouched. The change is host-side only.
- §4.5 embedder-neutral: holds. The rules name no embedder.
- §4.9 tests count: holds. The checks compare exceptions and count directory entries.
- §4.10 evidence: the author's probe is quoted and reproduces byte for byte. Two reasons are not
  true as stated (finding 3).
- §4.13 tooling: no new dependency. Finding 6 avoids `collections.abc.Buffer`, which the
  declared Python floor lacks.
- §5.2 no open questions: the specification decides each rule. Findings 2 and 4 each need a
  stated decision, not a question.
- §7 never-do list: nothing tripped. The new checks change the judge, so `--accept-judge` is
  needed, as acceptance criterion 2 says.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 — Fixed (Decision 2): every `str` must encode as UTF-8, or `ValueError` names the
   argument; a lone surrogate is tested in `argv`, an env key, an env value and the v1.4 check.
2. Finding 2 — Taken: `argv` is any iterable but `str`/`bytes`/`bytearray`, consumed with
   `list()`; `env` stays a `Mapping`, as today.
3. Finding 3 — Fixed: the reasons now say the key rule is the strictest of the native ones and
   why it is right for this guest (`"=K"` tested), and that refusing `stdin=""`, `0`, `False`,
   `[]` is stricter than `subprocess` on purpose (all tested).
4. Finding 4 — Fixed (Decision 3): the cost of overriding `HOME` or `PYTHONTZPATH` on a reused
   root is stated, and goes in the README's "Not protected" list.
5. Finding 5 — Fixed: the defect is described as a key filter being bypassed, and
   `{"HOME\0x": "/shared"}` is a v1.4 case.
6. Finding 6 — Fixed: `memoryview(x).tobytes()` (a non-contiguous view tested), the buffer test
   is `memoryview()`, no cap, and the README says stdin goes to a host file of its size.
7. Finding 7 — Fixed (Decision 3): documented, not checked.
8. Finding 8 — Fixed (Decision 2): messages name the argument and position or key, never the
   value; a unit test checks it.
9. Finding 9 — Fixed (Decision 2): why `PathLike` is refused is stated; items are passed on as
   plain `str`.

## Reviewer's confirmation, 2026-10-17

I re-read the revised specification against each disposition. I also checked three details of
the revised rules in scratch: `rev014a/c1_confirm.txt`, from a `uv run python -I -c` one-liner
with no wasm. Nothing under `build/` was touched.

1. **Finding 1: confirmed.** Decision 2 adds the UTF-8 rule for every `str`. The table gains the
   surrogate row. A lone surrogate is unit-tested in an argument, a key and a value, and it is a
   v1.4 case.
2. **Finding 2: confirmed, with one wording fix.** `argv` takes any iterable except `str`,
   `bytes` and `bytearray`, consumed once, and a generator is in the accepted tests. But "`env`
   stays a `Mapping`, as today" is not quite true. Today `{**env}` takes any object with `keys()`
   and `__getitem__`. An `isinstance(env, Mapping)` test refuses one that is not registered as a
   `Mapping`. No caller does this (READ). Either drop "as today", or put it in the CHANGELOG line.
   This does not block the build.
3. **Finding 3: confirmed.** The key rule is called the strictest of the native rules, with its
   reason, and `"=K"` is tested. The `stdin` refusal is called stricter than `subprocess` on
   purpose, and `False` and `[]` are tested. EXECUTED: `memoryview()` refuses `0`, `False`, `[]`,
   `""` and `"hi"` with `TypeError`, so the single `memoryview()` test enforces the whole rule.
4. **Finding 4: confirmed.** Decision 3 states the cost on a reused root for `HOME` and
   `PYTHONTZPATH`, says why `PYTHONPATH` and the user site do not matter, and puts the cost in the
   README's "Not protected" list.
5. **Finding 5: confirmed.** The defect now names the filter bypass, and `{"HOME\0x": "/shared"}`
   is a v1.4 case. Today that call returns exit 0 (EXECUTED, `p6_denylist.txt`), so the check
   fails first.
6. **Finding 6: confirmed, with one note.** The rule is `memoryview(x).tobytes()`.
   - EXECUTED: it handles a non-contiguous view (`b'ace'`) and an `array('i')` (its raw bytes).
   - EXECUTED: `tobytes()` always copies, even for an exact `bytes` (`is not b` is `True`). So a
     large `bytes` input costs its size again for the call. `bytes(b)` on an exact `bytes` does
     not copy.
   - Taking `x` as it is when `type(x) is bytes`, and `memoryview(x).tobytes()` otherwise, avoids
     the copy. That is optional. The behaviour is correct either way.
7. **Finding 7: confirmed.** Decision 3 documents it and adds no check.
8. **Finding 8: confirmed.** Messages name the argument and the position or key, never the
   value, and a unit test asserts it. Small point: a refused key is itself quoted. Show it with
   `repr` and cut it to a few dozen characters, so that a huge key does not fill a log.
9. **Finding 9: confirmed, with one implementation point.** The reason for refusing `PathLike` is
   stated. "Passed on as a plain `str`" must not be built with `str(x)`. EXECUTED: for a subclass
   that overrides `__str__` and `encode`, `str(x)` returns the override (`'evil'`). In contrast,
   `str.__str__(x)` returns the real text as a plain `str` (`'ok'`), and
   `str.encode(x, "utf-8")` gives `b'ok'`. So use `str.encode(x, "utf-8")` for the UTF-8 check
   and `str.__str__(x)` for the plain copy. The accepted-`str`-subclass unit test should use such
   a subclass, so that it catches `str(x)`.

### Verdict (confirmation)

All nine dispositions are confirmed. It can be built. Three points go into the text or the build.
None of them blocks:
- drop "as today" for the `env` `Mapping` test, or name it in the CHANGELOG (item 2);
- make the plain-`str` copy with `str.__str__(x)`, never `str(x)`, and test it with a subclass
  that overrides `__str__` (item 9);
- optionally, skip the `tobytes()` copy for an exact `bytes` (item 6).

## Verdict

Ready to build once the text is revised. The design is sound: check first, `TypeError` for a
wrong type and `ValueError` for a bad value, NUL and `=` and the empty key refused, odd but
valid keys left alone, `stdin` bytes-like only, and no existing caller refused. Before building:
add the UTF-8 rule (finding 1), decide whether `argv` takes any iterable or name the break
(finding 2), correct the two native-CPython reasons (finding 3), and state what overriding
`HOME`, `TMPDIR` or `PYTHONTZPATH` costs on a reused root (finding 4). Findings 5 to 9 are
small text and test additions.
