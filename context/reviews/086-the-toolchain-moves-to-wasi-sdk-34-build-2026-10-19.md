# Build review of 086: the toolchain moves to wasi-sdk 34, 2026-10-19

- **Reviewer:** a fresh agent. I wrote none of 086's code or evidence. I wrote its pre-build
  review and the confirmation addendum.
- **Under review:** `spec/086-wasi-sdk-34` at `bd3e521`, on main `3866f56`. The code is `810c032`.
  `bd3e521` adds the evidence, the README, the CHANGELOG and the landing notes. The diff is
  `663bc15..bd3e521`.
- **Against:** the specification as confirmed at `663bc15`.
- **Left for later:** Decision 9's A/B and its growth accounting wait until 083 lands, by the
  lane's instruction. They come as a delta. This review covers everything else.
- **Read:**
  - the whole code diff: `downloads/SHA256SUMS`, `scripts/00_download.sh`, `line.conf`,
    `10_tools.sh`, `60_link.sh`, `recipes/fcntl_dup_refusal.c`, the comment edits, the three
    checks, `tests/cpython_configure.txt` and the fixture;
  - the README and CHANGELOG diffs, the wasi-libc facts sheet and notes, and the libxml2 sheet;
  - the landing notes;
  - the evidence memo and its folder;
  - the worktree's `build/086-evidence/`: the container outputs, `mac-A`/`mac-B`, the seen-failing
    logs and `latest-full-1.json`.
- **How I ran things:**
  - I cloned the whole worktree with `cp -c -Rp` into my scratch folder.
  - I replaced its `.git` with an independent clone at `bd3e521` and ran `git reset` to fill its
    index. `git status` was then clean.
  - I recreated `.venv` with `uv sync`.
  - The set's `SHA256SUMS` hashes to `aac927dc…` (EXECUTED).
  - I did not touch the main tree or its `build/`, and wrote nothing in any git tree. The copy is
    deleted.
  - My judge record is `latest-review.json` beside this file; its log is `judge-full.log`.
  - My probes are in `probes/`.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED**.

## Short version

The build matches the confirmed specification, and the bytes are proven.

- **One `SHA256SUMS` from five builds.** All five kept files hash to `aac927dc…` (EXECUTED): macOS
  A and B, linux/arm64 twice, linux/amd64 once. Check (a) passes on all three clangs.
- **The refusal is right.** It is a `switch` that reads an argument only where one is passed.
  It links in through `__wrap_fcntl` (READ, `python.map`), and its guard compile prints no
  warning.
- **The pass-through commands behave as on 0.1.0a7 (EXECUTED).** `os.get_blocking`,
  `os.set_blocking`, `os.get_inheritable` and `os.set_inheritable` give the same answers on both
  sets.
- **The judge matches the builder's.** My full judge, `-n 3`, matches the builder's record on
  every metric. The one exception is a check that cannot pass in a copied tree (section 1).
- **The amendment to check (c) keeps coverage whole.** I planted a change to the hidden line, and
  the digest caught it (section 3).

One thing must be done before landing:

- **B1. Criterion 5's trap-entry half was not run.** The containers never ran the nine
  `test_upstream_trap` nodes. So the landing notes' "on both Linux hosts every open trap entry
  trapped as named" has no evidence.

Two low findings and two notes follow.

## 1. The judge (EXECUTED)

- **The run.** `uv run pytest -n 3` on my copy, set `aac927dc`, darwin-arm64. It took 7 min 40 s,
  a benchmark fact.
- **The scoreboard.** 545/627 pass, 77 gap, 4 blocked (oracle, prior-art clones, three systems,
  wheel), 1 fail. Unit suite 1580/1587.
- **The ratchet.** Lost 1, gained 4, grew 64, "judge changed". It printed "trap entries with no
  trap here: c-stack-itertools-tee", as on main.
- **The one failure is my copy's, not 086's.**
  - The failing check is `test_every_build_python_is_pinned`.
  - Its findings name `/Users/…/wasi_python-086/build/tools`: the builder's worktree path, which
    the copied meson logs carry. From my copy, that path is outside the checkout.
  - The builder's `latest-full-1.json` records it as `pass`.
  - `tests/harness/sameness.py builder.json mine.json` prints exactly one difference: that check's
    status. Every fuel and byte metric is the same.
  - So the builder's 546/627, 0 fail, lost 0 stands. The lane's serial run in the main tree is the
    one that counts.
- **Lint.** `ruff check` and `ruff format --check` are clean on `src/` and `tests/` (EXECUTED).
- **The 64 growths.** They are the toolchain move's, and they wait for the A/B. The preliminary
  table (`growth-vs-accepted-prelim.txt`) gives the sum +0.22%, two rows over 1% (numpy-core
  +2.645%, the compress job +1.428%), and none over 3%.

## 2. The criteria, against their evidence

1. **Seen failing first. Met** (READ, `seen-failing.txt`, `build/086-evidence/seen-failing-*`).
   - Check (a) on a 33 tree: two objects, 13 and 51. With no clang: "nothing was compiled". My
     pre-build run gave 15 and 49; the same two objects.
   - Check (b) without the refusal: `os.dup(1) EINVAL` on both binaries.
   - Check (c) on 33: the ten `HAVE_*` lines and no other. That was the rewritten check's logic
     applied to 33's header. Section 3 runs the digest half.
2. **The pins. Met** (READ).
   - Fifteen lines are replaced in place, with exactly the hashes I verified before the build.
   - The URLs are literal, the `+m` is gone in steps 10 and 60, and both commit names in
     `line.conf` move.
   - No `33.0`, `161b3195` or `4434dabb` remains outside history comments.
   - "49 pins, 49 fetched, 49 verified" on macOS. The containers fetch 6 each and verify 49.
3. **The same bytes. Met** (EXECUTED).
   - `sha256sums/*` in the evidence folder, and `mac-A`, `mac-B`, `linux-arm64/SHA256SUMS-1/-2`
     and `linux-amd64-086/SHA256SUMS-1` in the worktree, all hash to `aac927dc…`.
   - The containers ran at `810c032` (their `host-tools.txt`).
   - Check (a) passes in both containers (`checks-a-c.txt`).
4. **What a program sees. Met, with B2 to add.**
   - The names: the surface diff is exactly the accepted list plus `sysconfig` `LIBOBJS`. That
     `LIBOBJS` move is correctly traced to `AC_REPLACE_FUNCS([dup2])`.
   - The values: my probe (`probes/values.py`, `probes/values.out`) compares the value of every
     simple attribute of every builtin module, on both binaries of 0.1.0a7's set and 086's. It
     finds only `select.PIPE_BUF`, `sys.version` and `time.CLOCK_MONOTONIC`/`CLOCK_REALTIME`. B2
     covers the last two.
   - The other libraries' config headers are unchanged (READ, `configure-diff-without-paths.txt`).
   - Imports and exports are unchanged (READ, `sections-a7-vs-086.txt`).
5. **The containers before landing. Partly met: B1.**
   - The 49 hostile checks pass on both Linux hosts (READ, `criterion5-hostile.txt`). They cover
     the recursion floors, the window, the deep-data limits and check (b).
   - `cpython-a`, `-b` and `-c` pass, with their 16 classes as gaps.
   - The trap entries are separate nodes, `test_upstream_trap[…]` (READ,
     `test_v1_3_upstream_suites.py:107-124`). `scoreboard.no_trap_here` reads only those nodes.
   - The container script selected `test_upstream_suite[…]` and `test_upstream_class`. No
     container output contains `test_upstream_trap` (EXECUTED, `grep -c`, 0 in every file).
   - So the absent "no trap here" line is the absence of the nodes, not a verdict about traps.
   - On darwin my run shows eight entries trapping as named and `c-stack-itertools-tee` not
     trapping, as before.
6. **The A/B. Deferred by the lane.**
   - The layout control is done and convincing (READ, `layout-control.txt`): `id(bool)` moves
     0xFF0, and the bool conversion costs +31.5% fuel on both binaries. That is 073's mechanism.
   - The trace, the growth reason and the bound wait for the rebase onto 083.
7. **The dry run.** It follows the landing, by rule.
8. **The judge.** Met, as in section 1.
9. **The record. Met, but for one stale line (N1).**
   - The memo names only 086's files.
   - The facts sheet is accurate against the source I read before the build.
   - The README and CHANGELOG say what Decision 11 asks, with the CPython-driver line (N2 of the
     pre-build review).
   - The libxml2 sheet's reason is changed.

## 3. The amendment to check (c)

**Why.** `HAVE_SYS_STATVFS_H` contains `vfs`, which `context/embedders.txt` reserves as a word
part. So the rules check refused a record that spelled that line out. The record now leaves out
lines holding a reserved word. It carries `digest`, the SHA-256 of every built `#define` line,
sorted.

**Coverage is whole (READ, then EXECUTED).**

- **The arithmetic.** The build's header gives 231 `#define` lines. The record holds 230 of them.
  The one missing is `HAVE_SYS_STATVFS_H 1`. The digest over all 231 equals the record's
  `d8eefd30…`.
- **A visible line moves:** the visible comparison names it.
- **A hidden line moves.** I planted `HAVE_SYS_STATVFS_H 0` in my copy's `pyconfig.h`. The check
  failed with "a line holding a reserved word moved: digest a4d4a837…, not d8eefd30…".
- **Restored,** the check passed again.
- **A new hidden line, or one removed,** changes the same digest.
- **A word added to `embedders.txt` later** would make a recorded line look "recorded, not
  built". The rules check would also flag the record itself. Either way the judge goes red.

So no change to the header can pass silently. One weakness: when visible lines also move, the
digest's message is held back until those are fixed. The check is red either way, so this is
acceptable.

## 4. The refusal in the binary (READ, then EXECUTED)

- **It is linked.** `python.map` lists `Modules/fcntl_dup_refusal.o:(__wrap_fcntl)`, and libc's
  `fcntl.c.obj` is reached as `__real_fcntl`.
- **The guard compiles cleanly.** `guard-fcntl_dup_refusal.log` is empty: no warning.
- **Both guards are in the link.** `60_link.sh`'s loop writes both guard compiles into
  `reactor-commands.txt` and adds both objects to the link. A failure names its file.
- **It costs 208 bytes.** The trial's unconditional wrapper cost 117; the `switch` is the
  difference. That is recorded in the memo.
- **Guest probe, on both sets.**

  | Call | 0.1.0a7 | 086 |
  |---|---|---|
  | `os.get_blocking(1)` (`F_GETFL`, the no-argument path) | `True` | `True` |
  | `os.set_blocking(1, True)` | `EBADF` (wasmtime's rights on stdout) | `EBADF` |
  | `os.get_inheritable(1)` | `False` | `False` |
  | `os.set_inheritable(1, False)` | `None` | `None` |
  | `os.dup(999)` | `ENOTSUP` | `ENOTSUP` |
  | `os.dup2(999, 5)` | absent | `ENOTSUP` |
  | `select.poll` on a writable stdout | (not run) | `[(1, 2)]` |
  | `select.poll().poll(1)`, empty | (not run) | `[]` |

## Findings

**B1 (medium; before landing). Run the trap entries in both containers, and correct the notes.**

- **The gap.** Criterion 5, as confirmed, asks for "the CPython groups that carry spec 065's trap
  entries … each open trap entry trapping as named or not at all". The script ran the groups and
  their classes, but not the nine `test_upstream_trap[…]` nodes.
- **The fix.**
  - Run `uv run pytest -n 3 tests/checks/test_v1_3_upstream_suites.py -k test_upstream_trap` in
    both containers, on the same set.
  - Keep the outputs beside the others, and quote each node's trap fact.
  - Replace the landing notes' and memo's sentence: "Neither container printed … every open trap
    entry trapped as named".
- **Why it matters.** `c-stack-itertools-tee` is the entry that traps on Linux x86-64 only. Its
  answer there is the one fact criterion 5 was written to see before landing.
- **The risk is small.** An open entry accepts the named trap or no trap. But the claim must have
  its evidence (§4.10).

**B2 (low). Two more surface changes, both values, should be written down.**

The surface probe compares names. My value probe finds two more changes. Neither needs action,
but both should be stated:

- **`sys.version`** (and so `platform.python_compiler()`) now says
  `[Clang 23.1.0-wasi-sdk (… 895aa2c8…)]` instead of Clang 22.1.0. This is expected for a
  toolchain move. Add it to the accepted list in the landing notes.
- **`time.CLOCK_MONOTONIC` and `time.CLOCK_REALTIME`** are 22668564/22668568, where they were
  22664664/22664668.
  - Both moved by 0xF00. In wasi-libc a `clockid_t` is the address of a static object
    (INFERRED from the values moving with the data segment), so their values are linear-memory
    addresses.
  - They are fixed within one set and change whenever the data segment moves. That is not 086's
    doing, but 086 is the first build to look.
  - One line in the memo is enough. A README platform fact ("clock ids are not stable across
    releases; use the names") is the owner's choice.

**B3 (low). Seen failing for check (c)'s digest half.**

- The evidence shows check (c) failing on 33 through its visible comparison only. My planted run
  (section 3) is the digest half's seen-failing.
- Cite it in the landing notes, or rerun it and keep the output.

**N1 (nit).** `context/upstream/25-wasi-libc-fcntl-dupfd/notes.md` ends with "README row, for when
this lands". The row is already in `context/upstream/README.md`, so drop the line or reword it.

**N2 (note, not a finding).** The full judge in a copy of a built tree cannot pass
`test_every_build_python_is_pinned`, because the meson logs carry the builder's path. That is how
spec 079's check works, not a defect. Reviewers who copy a tree should expect that one line.

## Verdict

**Lands once the A/B is done on 083's base (with its delta review, if its numbers move beyond
what the preliminary table shows) and B1 is run and written in.** B2 and B3 are written into
the landing notes or answered. The bytes, the refusal, the checks and the record are ready.

In one line: one `SHA256SUMS` from five builds, the refusal right, the judge the same as the
builder's; run the nine trap entries in the containers, and write down `sys.version` and the clock
ids.
