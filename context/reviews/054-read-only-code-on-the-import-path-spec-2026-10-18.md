# Review of 054 — Read-only code on the import path

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). It wrote none of 054, its memo or its probes.
- **Reviewed:** the specification as drafted and its research memo, branch `spec/054-read-only-code-on-the-import-path` at `27b37a0` (diff `62d2c56...HEAD`: the spec, the memo and its six evidence files). It is a pre-build review, and also a security review of the design, because 054 widens a README safety claim.
- **Re-ran:** no judge run. A pre-build review changes no code, and the brief kept every tree read-only. Instead, seven scratch probes ran against the main tree's frozen set `build/sets/s-f94dec535086b06c` (read-only), with today's `wasi_python.run` (`uv run --project ../wasi_python-054`), on both binaries. Each probe builds the memo's prelude itself, as the memo did. The scripts and their outputs sit beside this file: `probe_review.py` and `.txt`, `probe_lazy2.py` and `.txt`, `probe_pytz.py` and `.txt`, `probe_links.py` and `.txt`, `probe_mount_alias.py` and `.txt`, `probe_linecache_fix.py` and `.txt`, `probe_quote.py` and `.txt`, `probe_mount_pandas.py` and `.txt`. `git status` in the 054 worktree is clean afterwards.

Labels: EXECUTED (run here), READ (read in a file), INFERRED (reasoned, not run).

## The questions the brief asked

- **Decision 16: a list or a typed grant.** The list fits the substance for grants. The code still arrives only through a read-only grant the embedder names. It is never writable and never on by default. A flag cannot name a zip or a subfolder (memo §4). So the list is an API shape inside what the owner approved, and that shape is the agent's to choose (§6). **Read-only mounts are different** (F1). Decision 16 says "typed grant", and spec 032's Scope deliberately left mounts out ("stays a typed grant … A mount … may import; it is not claimed"). A mount's provider can alias a writable store, and the runner can judge it only partly. That widens the claim beyond what the owner approved. It goes to the owner, or out of 054.
- **Can a guest get code onto the import path the embedder did not grant read-only?**
  - Through a shared provider: yes (F1, EXECUTED).
  - Through grants within one call: no, given Decisions 3 to 5. The checks need two more cases to hold a builder to that (F4, F5).
  - Hard link: refused (EXECUTED). A guest's `os.link('/code/mylib.py', '/work/l.py')`, from a read-only grant into a writable one, is `EPERM`, and the file is unchanged.
  - Symbolic links: a link out of a grant does not resolve, whether absolute or relative (EXECUTED). A link that stays inside a grant does resolve, into any folder of that grant (EXECUTED). That is why Decision 5 must compare against the serving grant's whole folder (F5).
  - Case-insensitive host filesystems: covered. Host rules compare identities. Guest rules compare text, exactly as wasi-libc does (READ: `_judge` and the comment in `_instance`).
  - `..`: refused in entries (spec 017's `_guest_path`), and wasi-libc does not resolve it.
  - `.pth`, `sitecustomize`, `usercustomize`: `site` does not run. Stubs with those names in an entry were never imported (EXECUTED, `probe_lazy2.txt`).
  - `__pycache__`: no `.pyc` is ever written (memo §3). A `.pyc` already in an entry belongs to the embedder.
  - Namespace packages: the stdlib zip has no top-level folder without an `__init__`. So a regular package in an entry can never beat a namespace portion in the zip (EXECUTED, `ns2.py`: the 19 such folders all sit inside regular packages).
  - The prelude's literal: it survives a newline, both quote marks, a backslash, U+2028, U+0085, an escape sequence, `{x}%s` and a non-BMP character (EXECUTED, `probe_quote.txt`). NUL and lone surrogates are refused before that point. One spelling gap remains (F6).
  - The environment: it reaches the inner call byte for byte (EXECUTED).
- **Order after the zip.** Right for both binaries for any name the runtime *has*. It does not cover names the runtime *looks for but lacks* (F3, EXECUTED).
- **The prelude's visible differences.** Two extra frames and +1.33 M / +3.26 M fuel, paid only when an import path is used. Acceptable, and documented in Decisions 7 and 11. A third difference is not documented: the prelude's source shows up in some tracebacks (F2, EXECUTED).
- **Counted criteria and stand-ins.** Mostly sound. Without the refusals, criterion 5's nesting cases would run instead of raising, so the two planted-code layouts are caught. But two stand-in predictions are wrong, and the likeliest unsafe bug is not caught (F4).
- **049 interplay.** The three snapshot lines match the format of 049's `tests/public_api.txt` (READ, `../wasi_python-049` at `9e0bc0c`: `param mounts: Iterable[Mount] = ()  keyword-only`, and `option --grant GUEST=HOST  append`). Decision 10's two landing orders are complete.
- **The README correction of 034's sentence.** Backed by `root_and_mount.txt` (READ): with `root=True` and with a mount at `/`, `sys.path` is the zip alone on both binaries. The correction is right.
- **Open questions, embedder neutrality, wall-clock.** No open question, except F1's owner question. Embedder-neutral (the *Any other embedder* sentence). No check measures time.

## Acceptance criteria against the evidence

1. Every mode — sound. The memo's `equal.txt` ran its eight cases, 16 of 16. It is incomplete on tracebacks (F2): script and stdin cases with `eval`/`exec` would differ.
2. After the runtime — sound for names the runtime has (memo P6). It does not cover names the runtime lacks (F3).
3. A zip — sound (memo P4, P10).
4. Writes nothing — sound (memo P3).
5. A writable place never serves — sound in intent. Its cases and stand-in predictions need F4's and F5's corrections.
6. A read-only mount — sound as written. It would need F1's case if mounts stay.
7. The command line — sound (READ, `cli.py`: `VALUED`, `_split`).
8. and 9. Unchanged guarantees, and lost 0 / grew 0 — sound. A call without `import_path` keeps today's argv.
10. Documentation — sound once F1 to F3 and F7 change what it says.

## Findings, most severe first

1. **High — a read-only mount on the import path can serve what a writable mount wrote, and the decision to allow mounts at all needs the owner** (Decision 9, Decision 5's last bullet, Decision 11's *Safety* sentence). EXECUTED, both binaries (`probe_mount_alias.txt`).
   - Failure: one `MemoryProvider` is mounted read-only at `/lib` and writable at `/work`. Call 1 writes `/work/lib/evil.py`. Call 2 has the same layout and `/lib/lib` on the import path; it runs `import evil` and prints `planted code ran`.
   - Every rule in 054 allows this layout. The writable mount is not under the entry, and mounts have no host identity.
   - This is the agent runtime's typical shape: one store, a turn that writes it, a later turn that imports from it. The README would still say "nothing writable ever is" under "Enforced, and judged".
   - Unlike the cross-call grant case, here the runner *can* see the aliasing within one call: the same provider object is given twice.
   - Write in one of these:
     - (a) Read-only mounts leave 054 (Out of scope). The owner is asked whether a later specification should add them. This is the smallest choice (§6.4) and matches 032's reservation.
     - (b) Mounts stay. Then `ValueError` refuses a read-only mount serving an entry whose provider `is` the provider of a writable mount in the same call. Criterion 6 gains that case and its stand-in. The README says for mounts what Decision 5 says for grants: a provider that serves read-only what is written elsewhere — through another mount, another call, or any other route — imports what was written. And the question still goes to `questions-for-the-owner.md`, because decision 16 named a typed grant and 032 reserved mounts.
2. **Medium — the prelude's source appears in tracebacks** (Decision 7, "tracebacks … show only the program's frames and lines"; memo §2). EXECUTED, both binaries (`probe_review.txt`).
   - Cause: `_reactor.run` registers the prelude in `linecache` under the key (`<string>`, `<module>`, 1). Every `exec`/`eval` of a string compiled with the default filename shares that key.
   - Failure: script `/code/s.py` holding `eval('1/0')`. With an import path, stderr gains the prelude's whole line, with the entries in it, under `File "<string>", line 1`. Without one, no line is shown. The same happens for `exec` in a script, for `-m`, and for standard input. In `-c` mode the program's own source replaces the key, so the memo's eight cases missed it.
   - Fix (EXECUTED, `probe_linecache_fix.txt`): start the prelude with `__import__('linecache')._interactive_cache.clear() or …`. Script, stdin and `-c` are then byte-equal again, and `-m` shows no prelude line. The name is private, as is the `linecache._register_code` that `_reactor` already uses. The pinned set fixes it, and criterion 1 pins it.
   - Add to criterion 1's byte-equal list: a script with `eval('1/0')`, a script with `exec('x = 1/0')`, and standard input with `eval('1/0')`. Add a stand-in: the memo's prelude, without the clear, must fail those three.
3. **Medium — "after the zip" does not stop entries supplying names the runtime lacks but looks for, and the two binaries differ** (Decision 6: "the same call answers the same on both binaries", "the pinned set stays the pinned set", "name your packages apart"). EXECUTED (`probe_lazy2.txt`, `probe_pytz.txt`, `probe_review.txt`).
   - Stubs in an entry were imported by the runtime's own modules:
     - on both binaries: `_hashlib`, `pwd`, `termios`, `msvcrt`;
     - on the plain binary only: also `_decimal`, `_uuid`, `_winapi`, `nt`, `fcntl`, `grp`, `_zstd`, and pandas's optional dependencies `pytz`, `pyarrow`, `numexpr` and `bottleneck`. `import pandas` imports them there, while the snapshot imported pandas at build time.
   - Failure: an embedder ships pure-Python `pytz` (common) in its entry. `import pandas` imports it on the plain binary, not on the snapshot. An entry's `_hashlib.py` or `_uuid.py` makes `import hashlib` or `import uuid` raise `AttributeError` (EXECUTED, `probe_lazy.txt`).
   - Write in:
     - correct Decision 6's claims;
     - the README names the rule ("a module the runtime looks for and lacks — C accelerators, other platforms' modules, the profile's optional dependencies — is taken from an entry, and on the plain binary also by packages the snapshot imported at build time");
     - criterion 2 gains a counted case that pins today's answer, for example an entry's `pytz.py` is imported by `import pandas` on plain and not on snapshot, so a set that changes it is seen.
4. **Medium — the likeliest unsafe bug is not caught, and two stand-in predictions are wrong** (criterion 5). READ / INFERRED.
   - (a) A serving-place match by text (`startswith`) instead of by whole components lets a writable place serve an entry. With a writable root at a host path, a read-only grant at `/code` and the entry `/code2`, wasi-libc serves `/code2` from the writable root, but a text match says the read-only `/code`. None of the 22 refusal cases uses sibling-prefix names. Add that case (refused), and a stand-in "prefix by text" that fails it.
   - (b) The "shortest prefix" stand-in also refuses the allowed case `root=True` with a read-only grant at `/code` and `["/code"]`: the root is the shortest prefix. So it fails two allowed cases, not one, and "each failing exactly the named cases" is wrong as written.
   - (c) The "by a writable grant" and "by a writable mount" serving cases must put the entry strictly *under* the writable place (`/work/lib`), not at it. At it, the guest-nesting rule also refuses, so the "no serving-place rule" stand-in fails fewer than the predicted five.
5. **Low-medium — host nesting must stay against the serving grant's whole folder, and a check must hold a builder to it** (Decision 5). EXECUTED (`probe_links.txt`).
   - A symbolic link inside a read-only grant reaches any folder of that grant. With the entry `/p/lib`, `proj/lib/plug -> ../out` imported `plug.evil_in` from `proj/out`.
   - So a writable grant of `proj/out` must be refused even when the entry is only the subfolder `/p/lib`. The spec's text (the serving grant) is right but gives no reason. All three host-nesting cases use an entry equal to the grant's root, so a "precise" subfolder implementation would pass them.
   - Add the case and the reason.
6. **Low — build the prelude only from the checked plain strings** (Decision 1: "`repr(list( import_path))`"; Decision 2). INFERRED.
   - `isinstance(x, str)` admits a subclass. `repr()` on a subclass calls its override, so a `__repr__` that returns code would be written into the prelude.
   - `_text` and `_guest_path` already return plain `str` (READ, `runner.py:130-142`). The spec should say that the tuple holds those values and that `_import_prelude` takes only them.
   - Add a case: a `str` subclass whose `__repr__` and `__str__` lie reaches `sys.path` as its plain value. The source is the embedder, not the guest, but spec 017 handles subclasses for exactly this reason.
7. **Low — the *Safety* sentence over-claims even for grants** (Decision 11). READ.
   - "Nothing writable ever is" sits under "Enforced, and judged". Decision 5 itself documents the cross-call layout the runner cannot see.
   - Suggested: "only the stdlib zip and the read-only entries the embedder names are on the import path; nothing the same call can write is under one (across calls, see *Grants*)". Adjust it to F1's outcome.

## Constitution checks

- §4.4 (two imports only): unchanged. No guest change and no new import (READ).
- §4.5 and §4.15 (safe by default): the default (empty) keeps today's argv byte for byte. No default is loosened. The runtime's own folders stay refused (`/usr/local/lib` in `_guest_path`; spec 017's `_runtime_folders`). F1 is about widening an explicit opt-in beyond the owner's words, not about a default.
- §5.2 (no open questions): met, except F1, which must become the owner's or leave 054.
- §5.6: a pre-build review is optional here and was held. This is it.
- §6: the list-versus-flag choice is the agent's (rules 4 and 5). Including mounts is not settled by §6 (F1).
- §7: nothing tripped. No tree was written. Every probe ran from the scratchpad against the frozen set.

## Disposition (filled in by the author, then confirmed by the reviewer)

The author's record is at `f79d966` ("Disposition of the pre-build review" in the spec, and `disposition.md` beside this file). Each finding, and the reviewer's check of it:

1. **F1** — fixed by the lane's ruling. Mounts serve no entry (Decisions 3, 4 and 9). Owner question 93 asks about later. Criterion 5 gains S3, S4, S6, S7 and G2. **Confirmed.**
2. **F2** — fixed. The prelude clears `linecache._interactive_cache` first (Decision 7). Criterion 1 now has 11 byte-equal cases, plus stand-in (c). **Confirmed.**
3. **F3** — fixed. The rule is stated and pinned (Decision 6, criterion 2, Scope, the README). **Confirmed.**
4. **F4** — fixed. S8 and the text-prefix stand-in were added. The shortest-prefix prediction is now A1 and A2, every serving case puts the entry strictly under its server, and A4 was added. **Confirmed**, with one wording gap (R1 below).
5. **F5** — fixed. The whole folder is the bound, the reason is given, and H4 was added with its stand-in. **Confirmed.**
6. **F6** — fixed. Only the checked plain strings are kept (Decision 2), and A5 was added with its stand-in. **Confirmed**, with a non-blocking remark (R2 below).
7. **F7** — fixed. The *Safety* sentence and the *Mounts* clause were reworded. **Confirmed.**

## Verdict

**Ready once F1 to F7 are written in.** For F1 that means either cutting read-only mounts from 054, or keeping them with the provider-identity refusal and an honest README. Either way the question goes to `questions-for-the-owner.md`.

One line: the grant design holds and the prelude works, but a shared provider plants code past every rule, the prelude leaks into tracebacks, and "after the zip" lets entries fill names the runtime looks for.

## Confirmation (2026-10-18)

- **Reviewed:** `git diff 27b37a0 f79d966` on `spec/054-read-only-code-on-the-import-path`: the spec, question 93, the memo's appended correction, and `revision_lacking_names.*` and `revision_linecache.*`. I wrote none of it.
- **Re-ran against the frozen set** `build/sets/s-f94dec535086b06c` (read-only; not `build/artifacts`, which is being rebuilt), on both binaries, from a scratch copy, with no tree written.

### Executed

- `revision_lacking_names.py` → output byte-identical to the committed `.txt` (`rerun_lacking_names.txt`). On the plain binary `HIT pytz` appears 2 times, on the snapshot
  0. `_hashlib` gives 1 hit and `AttributeError` on both binaries. Criterion 2's numbers hold.
- `revision_linecache.py` → output byte-identical to the committed `.txt` (`rerun_linecache.txt`). With the clearing prelude, 3 of 3 cases are byte-equal per binary; with the memo's prelude, 0 of 3. Criterion 1 and stand-in (c) hold.
- **A5** (`probe_a5.*`). Built from the checked plain string, the call runs and prints `/code 7`, with no `injected`. Built from the caller's object (the stand-in), the call exits 1 with a `SyntaxError`, so A5 fails it as predicted.

### Read

Each stand-in prediction was worked through against cases S1–S8, G1–G3, H1–H4 and A1–A5. All hold, with one exception:

- **R1 (low; write it in at build).** S8 says "`root=` an existing host folder". That folder must be apart from `code`, neither holding it nor at it. If the root held `code`, spec 017's existing rule (a read-only grant inside a writable root) would refuse S8 first. The "text-prefix" stand-in would then not fail S8, and its predicted count of 1 would be wrong. The criterion should say "a host folder apart from `code`". The builder can write this in; the landing notes record it.
- **R2 (nit, non-blocking).** A5's payload (`'/x']) or print('injected') or (['`) makes the stand-in's prelude a `SyntaxError`. It does not run injected code. The check still fails the stand-in, because the call does not run and `mylib` is not imported. A payload that parses, such as `'/code'] + [print('injected') or '/code'`, shows the real hazard: the stand-in prints `injected` and still imports `mylib` (EXECUTED, `probe_a5b.*`). With it, the "no `injected`" clause does the catching. Optional.

### The rest

- **Question 93.** Its facts match my runs. The question and the recommendation are clear, and nothing waits on the answer. "Meanwhile refused" keeps the default whole (§4.15).
- **The memo.** The correction is appended, not rewritten, and every claim in it is labelled EXECUTED with evidence.
- **The lane's F1 ruling.** It is faithful to decision 16's words and to §6 rules 1 and 4. It is the smaller of the two options this review offered.
- No open question remains except question 93, which blocks nothing. No wall-clock. Still embedder-neutral.

**Verdict: ready to build.** R1 is a one-line clarification to write in at build; R2 is optional.

One line: every finding is answered and reproduced on the frozen set; only S8's root needs to be named as apart from `code`.
