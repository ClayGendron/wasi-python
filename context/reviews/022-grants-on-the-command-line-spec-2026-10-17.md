# Review of 022 — Grants on the command line (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the specification. I read `AGENTS.md`, the constitution (§3, §4.15, §5.2, §5.6), `context/reviews/README.md` and the 021 pre-build review (for the format). Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/022-grants-on-the-command-line.md` as drafted (`8d77d93`).
- **Read:** spec 019 and its two reviews; `src/wasi_python/cli.py`; `tests/unit/test_cli.py`; spec 017; the README's *Grants* and *From any language*; `run`, `Grant`, `_text`, `_host_path`, `_guest_path`, `_check_root`, `_check_grants`, `_runtime_folders` and `_shared_folders` in `src/wasi_python/runner.py`; the 019 real-call checks in `tests/checks/test_v1_4_embedding.py` (`_cli`, from line 1210).
- **Ran (EXECUTED, darwin-arm64, Python 3.14.2).** No tracked file was edited. I did not run `uv run pytest`. Everything is under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev022/`:
  - `scripts/today_cli.py`: today's `cli.main` on the spec's usage-error cases, with a fake `run` (`out/today_cli.txt`).
  - `scripts/proto.py`: the spec's options added to today's parser in scratch; 20 argument lists through `_split` and `argparse` (`out/proto.txt`).
  - `proto/cli022.py`: a scratch copy of `cli.py` with the three options, one way the design could be built. `scripts/proto_real.py` runs it end to end on the real runner (`out/proto_real.txt`); `scripts/order.py` checks grant order with a fake `run` (`out/order.txt`).
  - `scripts/real.py`: the v1.4 cases through `wasi_python.run` directly (`out/real.txt`).
  - Real calls used `WASI_PYTHON_ARTIFACTS=…/build/artifacts` and `WASI_PYTHON_CACHE=…/build/cwasm-cache` of the main tree.

## What holds

- **The read-only grant's write fails as the spec says.** EXECUTED (`out/real.txt`, `out/proto_real.txt`). With `--grant /data=./inputs --grant-writable /out=./results`, the program reads `/data/a.txt`, writes `/out/r.txt` (it appears on the host), and `open('/data/n','w')` fails. The stderr ends `PermissionError: [Errno 63] Operation not permitted: '/data/n'`. The command exits 0; the JSON has `"exit_code": 1`. Append, `r+`, `remove`, `mkdir` and `rename` in a read-only grant each fail the same way.
- **Granting the temporary folder is exit 1 with `ValueError`.** EXECUTED: `--grant /t=$(tempfile.gettempdir())` gives `{"error": "grants[0] at /t holds the temporary folder, which holds every call's private folders and stdin; grant a folder apart from it", "kind": "ValueError"}`. A folder inside the temporary folder (as pytest's `tmp_path`) is granted and read.
- **Two grants at one guest path are refused, not merged.** EXECUTED: `--grant /d=./inputs --grant-writable /d=./results` is exit 1, `grants[1] at /d: another grant has the same guest path`. So a repeated guest path never silently becomes writable. This differs from `--env`, where the last value wins. That is right here.
- **A typo never gives a writable folder.** EXECUTED (`out/proto.txt`): `--grant-writabl`, `--grant-w` and `--gran` are each exit 2, `unrecognized arguments`. `allow_abbrev=False` holds for the new options. `--grant` is a prefix of `--grant-writable`, and it is never taken as one.
- **The scan does not break.** EXECUTED: `--no-root` is a flag, so `_split` steps over it alone (`--no-root --grant /d=x -c 1` splits correctly). `--grant=/d=x` and `--grant-writable=/d=x` parse. `--root a --no-root` is exit 2 from a mutually exclusive group. `--no-root=x` is exit 2. `--no` stays exit 2, though it now matches two options. A `--root` value starting with `-` needs `--root=-x`, as `--stdin` already does.
- **Guest first keeps the value from looking like an option.** INFERRED from the scan: a guest path must start with `/`, so a `--grant` value never starts with `-`. A host-first or two-value form would let a host path such as `-data` be taken for an option.
- **Relative host paths are the command's working directory.** EXECUTED: `--grant /d=./inputs` reads the right file; the runner joins it to `os.getcwd()` (READ, `_walk_posix`).
- **Nothing is added that `run()` lacks.** READ: each option maps to one argument, as 019's table does. §3 and §4.15 hold (below).

## Acceptance criteria against evidence

1. The checks exist and were seen failing first — **not reachable for the usage-error checks as written**: they pass today, for another reason (Finding 2).
2. Green with `--accept-judge` — plausible. The 019 helper `_cli` records no metric (READ), so a new real call adds no fuel or bytes to the ratchet (INFERRED). Not run.
3. A release dry run passes — not run; nothing found that would stop it (INFERRED).

## Findings, most severe first

1. **Medium. "A guest path with `=` is refused as a usage error" cannot be built.** (Decision 1)
   - The defect. Split at the first `=`, the guest side can never hold an `=`. So nothing is left to refuse. `--grant /a=b=/host` is read as guest `/a`, host `b=/host`.
   - Failure. EXECUTED: that case is exit 1, `grants[0] at /a: 'b=/host' does not exist`, not exit 2. If a folder `b=/host` existed under the working directory, it would be granted at `/a` without a word. Also, `run()` accepts a guest path with `=`: `Grant(inp, "/a=b")` runs and lists the folder (EXECUTED). So the command can name fewer guest paths than `run()`. The stated reason is also off: `run()` accepts `:` and `\` in a guest path too (EXECUTED, `/c:\x`), and guest-first never needs to care about them.
   - Is that a loss of power? No (INFERRED). Any host folder can still be granted, in either mode, at some guest path. Only the guest-side name is narrowed. §3 forbids adding power, not narrowing names. A guest path with `=` is rare.
   - The alternatives, weighed.
     - `GUEST=HOST`, first `=` (the draft): one value; `--name=value` works; host paths with `=`, `:`, `\`, UNC (`\\server\share`) and drive letters all pass (EXECUTED: `/d=C:\data`, `/d=\\server\share\x`, `/d=./a=b`); the value always starts with `/`; it reads like `--env NAME=VALUE`. Cost: no `=` in a guest path.
     - `--grant GUEST HOST` (two values): no restriction at all. Cost: `_split` must learn a two-value option; `--grant=…` cannot carry both; a host path starting with `-` is taken as an option by `argparse` (INFERRED from the `--root -x` case, EXECUTED).
     - `HOST:GUEST` (Docker style): ambiguous on Windows (`C:\data:/d`), and `run()` allows `:` in a guest path. Rejected.
     - `HOST=GUEST`, last `=`: the same restriction, moved, and the value can start with `-`.
   - Fix. Keep `GUEST=HOST`, split at the first `=`. Replace the sentence with: "Everything after the first `=` is the host path, which may hold `=`, `:` or `\`. A guest path holding `=` cannot be written here, though `run()` takes one; it narrows names, not reach." Put the weighing above in one or two sentences, so the choice is decided (§5.2). In the README, say the guest path comes first, as a name does in `--env NAME=VALUE`.

2. **Medium. The usage-error checks pass today, so they cannot be "seen failing first".** (Design, checks; criterion 1)
   - The defect. Today every new option is unknown, and an unknown option is exit 2.
   - Failure. EXECUTED (`out/today_cli.txt`): `--grant /d`, `--grant =x` and `--root x --no-root` are each exit 2 today, with `unrecognized arguments: --grant` (or `--root`). A check that asserts only exit 2 is green before any code is written.
   - Fix. Each usage-error check also asserts its reason on standard error: for no `=`, a phrase the new message must hold (say `GUEST=HOST`); for `--root` with `--no-root`, `not allowed with argument`. Then each fails today, for the right reason.

3. **Medium. The design as written loses the grants' order.** (Decision 1 against the Design)
   - The defect. Decision 1 says grants keep their command-line order. The Design has `_grants(items, writable)`, one call per option, which means two lists.
   - Failure. INFERRED from `argparse`, EXECUTED in `out/proto.txt`: two `append` options give two lists, `grant` and `grant_writable`. `--grant /a=x --grant-writable /b=y --grant /c=z` reaches `run()` as `/a, /c, /b`. The runner accepts any order, but its errors name `grants[i]` by position. A caller then sees `grants[2]` for the second option it typed.
   - Fix. Both options append to one destination, each value tagged with its mode (for example `dest="grants"` with `type=lambda t: (t, False)` and `(t, True)`). EXECUTED (`out/order.txt`): order kept, modes right. The unit check uses an interleaved case like the one above. The README says errors number grants from 0 across both options, in the order typed.

4. **Low. The line between exit 2 and exit 1 is drawn in two places.** (Decisions 1 and 3; spec 019 Decision 2)
   - The defect. Spec 019's rule is: a value that does not parse is exit 2; one that parses but `run()` refuses is exit 1. An empty side parses. The Design makes it exit 2. Decision 3 says "Nothing is checked twice", yet the command would check emptiness and `run()` would too.
   - Failure. EXECUTED (`out/proto_real.txt`): `--root ""` reaches `run()` and is exit 1, `root is empty`; under the draft, `--grant /d=` would be exit 2. Two empty paths, two exit codes. `run()` already words both empties well: `grants[0] at /d: host is empty` and `grants[0]: the guest path must be absolute; got ''`.
   - A second risk. A builder who writes `if ns.root:` drops `--root ""`, and the call quietly gets a private root instead of an error. The existing "not given is not passed" check does not catch it (READ).
   - Fix. Exit 2 only for what does not parse: `--grant` without `=`, and `--root` with `--no-root`. Empty sides go to `run()`, exit 1. The `--grant =x` check becomes exit 1 with `"kind": "ValueError"`. Add a check: `--root ""` is exit 1, `root is empty`. Use `default=argparse.SUPPRESS` or `is not None` for `--root`.

5. **Low. `--root` is a short word that gives a writable folder.** (Decision 2; §4.15)
   - The defect. Decision 2 says "a caller never gets a writable folder by a missing word". True for grants. But `--root HOST` is always writable, and `run()` makes a missing root. The table does not say either.
   - Failure. EXECUTED: `root="./newroot"` makes the folder and runs with `/tmp` and `/usr` in it. A typo such as `--root ./resutls` makes a new folder and writes there, with no error. Also, `--root a --root b` keeps `b`, silently (EXECUTED, `out/proto.txt`). This is `run()`'s behaviour, not a loosened default, so §4.15 holds. But a caller reading Decision 2 would think every short option is read-only.
   - Fix. The table says `--root HOST` is writable and made if missing. Decision 2 adds: "`--root` is the one short form that writes; it is `run()`'s root". The `--help` text and the README say the same. Decide repeated `--root`: either a usage error (as `--root` with `--no-root` is), or "the last one wins", as for `--fuel`. I would refuse it; it is one line in a custom action.

6. **Low. The v1.4 real call needs three precisions.** (Design, checks)
   - The defect. "Grant the temporary folder" does not say which folder. The write failure does not say what is asserted.
   - Failure. EXECUTED: on macOS `tempfile.gettempdir()` is `/var/folders/…/T`, not `/tmp`. A check that grants `/tmp` gets exit 0, and its guest lists 261 entries of `/private/tmp`. It would fail on macOS and pass on Linux. Separately, "PermissionError in its stderr" alone would also pass if the read-only grant were writable and the program failed some other way with the same word.
   - Fix. Grant `tempfile.gettempdir()` by name, and assert the exact error text and `"kind": "ValueError"`. For the read and write: assert the command's 0, `"exit_code": 1`, `stdout` holding the read file's text, the written file on the host with its contents, and `PermissionError: [Errno 63]` in `stderr`, with no new file in the read-only folder. These are counts and texts; no clock (§4.9).

7. **Low. Small things to write down before the build.** (§5.2)
   - The header is stale: spec 019 has landed (`84f4e1c`, accepted in `98d0210`). The Status and Depends lines can say so.
   - Where the `=` split runs. It uses `parser.error`, which raises `SystemExit`. It must run inside `_main`'s `try … except SystemExit`, as `_env` does. EXECUTED: in my first prototype it ran after that block, and `SystemExit` escaped `main` instead of returning 2.
   - The no-`=` message. Say whether it echoes the value. A path is not a secret, so echoing is fine; `--env`'s "number i" style also works. Pick one.
   - The unit check's split table (`test_the_guests_argv_is_split_off_in_one_scan`) gains `--grant=/d=x`, `--grant /d=x x.py` and `--no-root x.py`.
   - `--no-root` alone gives the guest no `/`. A relative program path then fails (EXECUTED: `s.py` gives `[Errno 44]`). The README's *Grants* already says this for `root=False`. The CLI section can point there.

## Simpler options

- **`--root none` instead of `--no-root`.** Considered and not better. For the limits, `none` means `None`, no limit. For `root`, `None` is the private root and `False` is no root. A folder named `none` would also be ambiguous. Keep `--no-root`.
- **Leave out `--root HOST`.** A writable host root is the strongest option here. `--no-root` with `--grant-writable /work=…` and `--grant-writable /tmp=…` covers most uses, and gives a `HOME` (README *Grants*). But `run()` takes `root`, and spec 019 promised both. This is the owner's call. The draft's choice is sound if Finding 5's words are added.
- Nothing simpler than `GUEST=HOST` was found (Finding 1).

## Constitution checks

- §3: the command adds no power. Each option is one `run()` argument. The `=` rule narrows the guest names the command can write (Finding 1); it adds nothing.
- §4.9: the proposed checks assert texts and counts. No clock.
- §4.15: no default loosens. Without an option, the call keeps `run()`'s private root and no grant. A grant is read-only unless the longer option is typed. A typo is exit 2 (EXECUTED). `--root` is writable by design; the spec should say so (Finding 5).
- §5.2: the guest-path rule, the order mechanism, repeated `--root`, and the no-`=` message are not yet decided (Findings 1, 3, 5, 7).
- §5.6: the spec changes no import, export, artifact or build recipe; this review was asked for anyway.
- §7: nothing on the never-do list is tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

Every finding is taken; the specification is revised in place.

1. **The `=` sentence:** reworded (Decision 1): the split at the first `=` means a guest path with `=` cannot be written here; it narrows names, not reach, so §3 holds; the alternatives and why `GUEST=HOST` wins are recorded.
2. **Checks that pass today:** every usage-error case asserts its message (Design), so each fails first.
3. **Order:** both grant options write to one tagged list (Decisions 2, Design).
4. **Exit codes:** exit 2 only for a missing `=`, `--root` twice, or with `--no-root`; empty sides and `--root ""` go to `run()` (exit 1); a check pins `--root ""` (Decision 5).
5. **`--root` writes:** said in the README and `--help`; a repeat is a usage error (Decision 4).
6. **The real call:** grants `tempfile.gettempdir()` by name, asserts the host files, the error text and the exit codes (Design).
7. **Small things:** Status and Depends updated; the split runs inside the `try`; the message is "--grant needs GUEST=HOST"; the scan table gains the new forms; the README points to the `root=False` note.

## Verdict

Revise first: correct the `=` sentence and record the choice (Finding 1), make the usage-error checks fail for the right reason (Finding 2), and keep the grants' order with one destination (Finding 3); the rest are a few sentences. The design itself is right: `GUEST=HOST`, read-only by default, and `run()` as the only judge.

One line: the options are safe and the syntax is the right one, but one claim cannot be built, three checks would pass before the code exists, and the design as written loses the order it promises.

## Confirmation

- **Date:** 2026-10-17
- **Reviewer:** the same fresh agent (Claude Opus 5.5); not the author.
- **Reviewed:** the specification as revised in `641c2c2`, and the Disposition above. The findings above are my text, unchanged (EXECUTED `diff` against my draft).
- **Ran (EXECUTED, darwin-arm64).** No tracked file was edited, except to append this section. Scripts and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev022/` (`confirm/argp.py` → `out/confirm-argparse.txt`; `confirm/tmpgrant.py` → `out/confirm-tmpgrant.txt`).
  - `confirm/argp.py`: the revised parser alone, in plain `argparse`, run with `python -I` on every Python the project supports (3.11.14, 3.12.12, 3.13.11, 3.14.2). It has the tagged shared list and a `--root` that refuses a second value. The output is the same on all four.
  - `confirm/tmpgrant.py`: two fresh processes, each making two calls with a read-only and a writable grant inside `tempfile.gettempdir()`, on the main tree's artifacts.

### Each disposition against its finding

1. **The `=` sentence:** closed. Decision 1 now says what the split does, says it narrows names and not reach, and records why `GUEST=HOST` beats the three other forms.
2. **Checks that pass today:** closed. The Design asks every usage-error check to assert its message. Each new case now fails today for the right reason (INFERRED from `out/today_cli.txt`). Today `--grant /d` says `unrecognized arguments`, not `needs GUEST=HOST`. Today `--root ""` and `--grant /d=` are exit 2 and never reach `run()`.
3. **Order:** closed. EXECUTED on all four Pythons: two `append` options share one `dest`, each with a tagging `type`. `--grant /a=x --grant-writable /b=y --grant /c=z` gives `[("ro", "/a=x"), ("rw", "/b=y"), ("ro", "/c=z")]`. Writable first, then read-only, keeps that order too. With no grant, the list is `[]`. With only `--grant-writable`, it holds that one value. argparse copies the default list, so one call never leaks into the next.
4. **Exit codes:** closed. Decision 5 draws the line once and follows 019's rule. EXECUTED: `--root ""` parses to `root=""`, which `run()` refuses with exit 1 (`root is empty`, first round). `--grant=` parses to an empty value, which has no `=` and so is exit 2. That is consistent: an empty value cannot be split. `--grant /d=` reaches `run()`. A check pins `--root ""`.
5. **`--root` writes:** closed. Decision 4 has the words for the README and `--help`. EXECUTED: a custom action that refuses a second value works on all four Pythons. `--root a --root b`, `--root a --root a` and `--root= --root=x` are each exit 2, `argument --root: given twice`. `--root a --no-root` and `--no-root --root a` are each exit 2, `not allowed with argument`. The mutually exclusive group and the custom action work together. `--no-root --no-root` is accepted, which is harmless.
6. **The real call:** closed. EXECUTED: grants of folders inside `tempfile.gettempdir()` work, one read-only and one writable. That includes the first call of a fresh process, before the runtime's stdlib folder exists. So "folders under the check's own temporary folder" is safe for the v1.4 check. Only a grant at or above the temporary folder itself is refused.
7. **Small things:** closed. Status and Depends are current. The split runs inside the `try`. The message is named. The scan table and the README note are in the Design.

### New gaps (§5.2)

None that change the design. Three points of wording; the builder can carry each one:

- **A. The README does not say how grants are numbered.** Decision 2 says errors name grants by position, in the order typed. Finding 3 asked the README to say so. The Design's README bullet leaves it out. Fix: one sentence in *From any language*. "`run()`'s errors number grants from 0, across `--grant` and `--grant-writable`, in the order typed."
- **B. "Exit 2 only for…" reads as a complete list.** argparse's own errors are also exit 2: an unknown option, `--grant` with no value, `--no-root=x`. Spec 019 already decides them. Fix: "Exit 2 for what cannot be parsed: argparse's own errors (spec 019), and also …".
- **C. The message names one option.** "--grant needs GUEST=HOST" is wrong for `--grant-writable /d`. The tag tells the code which option was given, so the message can name it. The check's phrase, `needs GUEST=HOST`, fits both.

One build note, not a gap. The refusal of a second `--root` relies on its default being `argparse.SUPPRESS`, so the attribute is missing until the first value. With `default=None`, a `hasattr` test would refuse every `--root`. Testing `is not None` would also work, since `""` is not `None`. The Design's checks catch either mistake: `--root x` must reach `run()`.

### Verdict

Ready to build. Every finding is closed, and the revision opens no new open question. A, B and C are one sentence each, and the builder can add them during the build.

## Disposition of the confirmation (filled in by the author)

- **A:** made: the README line says grants are numbered from 0 across both options, in the order typed.
- **B:** made: Decision 5 says argparse's own errors stay exit 2.
- **C:** made: the missing-`=` message names the option given.
- The build note (`--root` with no default) is taken.

Your verdict made the specification ready to build with these.

