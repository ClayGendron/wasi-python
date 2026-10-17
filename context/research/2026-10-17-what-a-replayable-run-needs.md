# What a replayable run needs

- **Status:** placeholder, 2026-10-17.
- **Owner:** Clay Gendron
- **Researcher:** the author agent (Claude Opus 5.5), from the pre-build review of spec 008
  (`../reviews/008-fuel-counts-the-guest-and-runs-replay-spec-2026-10-17.md`), which found the
  first design not ready.
- **Feeds:** a later specification for `run(..., deterministic=True)` and a run record (the
  principal engineer's memo, direction 6: "a run that replays exactly … as an audit record").
- **Blocks:** that specification only. Spec 008 (fuel counts the guest only) does not wait.

## The question

What must the runner control so that the same artifacts, program, inputs, seed and starting
root give byte-identical outputs and identical fuel, every time and on every host, and what must
a record of the run hold so that equal records mean the same run?

## What is known (from the review of spec 008's first draft, EXECUTED unless marked)

- **Answered by the runner already (the judge's driver does this):** the realtime and monotonic
  clocks and `random_get`. With them fixed, `os.urandom`, `uuid4`/`uuid1`, `random`, numpy's
  legacy generator and unseeded `default_rng`, `tempfile`'s names and the plain reactor's hash
  secret all repeat.
- **Not controlled, and observable:**
  - **inode numbers.** wasmtime reports a hash of the host's device and inode, so a fresh root
    shows new ones. The pandas golden job's `to_csv` moved by 17 to 51 instructions in about one
    run in thirty; roughly one replay pair in eight would differ in fuel.
  - **`time.sleep`.** CPython sleeps until an absolute deadline on the guest's clock, and
    wasmtime's `poll_oneoff` waits for the real clock to reach that value. With a fake clock,
    `sleep(1)` after 3 s of real work returns at once, and a loop that sleeps 0.05 s until 0.5 s
    of guest time pass ran 250,000 times instead of 10 (about 15 times the fuel).
  - **`clock_res_get`**, which is not faked, so the host's resolution shows through.
  - **directory listing order, a directory's size and link count**, which come from the host's
    filesystem.
  - **file timestamps** the host sets when the guest creates or writes a file.
- **What a record must hold** for "equal records, same run": the binary's and the stdlib zip's
  digests, the wasmtime version, a format version, argv, the environment as the guest got it,
  stdin's digest, the seed, the limits (fuel, memory, output, deadline), the outcome (exit code,
  `trapped`, `fuel_used`, `truncated`, stdout's and stderr's digests), and a digest of the door's
  traffic (requests and responses in order). Its encoding must be fixed to the byte, and the run
  should return the encoded record, not only its hash.

## What would answer it

An experiment that answers, from the runner, `clock_res_get`, `poll_oneoff` for clock-only
subscriptions (advancing the fake clock instead of waiting), and the inode and timestamp fields
of `fd_filestat_get`, `path_filestat_get` and `fd_readdir` (a stable inode per path; fixed
times), then runs the golden jobs and a set of probes a hundred times each across fresh roots and
two operating systems, and counts how many outputs and fuel figures differ. Then the record's
encoding, specified to the byte, and a check that a changed door response changes the record.

## One line

Fixing the clock and entropy is not enough for exact replay: the guest also sees inode numbers,
the real clock under `sleep`, clock resolution and directory order, which the runner must answer
before a replay can be promised.
