# The module cache is refused where another uid owns `/`

- **Status:** research, 2026-10-27. A finding from outside this repository: wasipython.dev's runner, on Cloudflare Containers. It changes nothing here: no code in `src/`, no pin, no specification. Whether and how the check changes is the owner's to decide here.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), in a session of the `wasi-python-dev` repository (the wasipython.dev site).
- **Evidence:** `wasi-python-dev`, commit `f092cdd`: `context/research/2026-10-27-the-runner-on-cloudflare-measured.md` (the measurement), `bench/cloudflare/` (the harness: a Worker, a Durable Object that starts the container and runs read-only `exec` probes in it), and `bench/cloudflare/results/2026-10-28T01-46-17-050Z.json`. The deploy was deleted after the measurement.
- **Stands on:** `src/wasi_python/_platform.py`, `_way` (the path check); `_engines.py` (`_cache_warning`, the cache's load and write); `docs/get-started/install.md` (what the cache needs). Read in the 0.1.1 wheel from PyPI, which is this repository's `src/wasi_python/` at `898bc091`.
- **Host:** Cloudflare Containers, `standard-1` (1/2 vCPU, 4 GiB), "AMD EPYC" with `avx2 avx512f bmi2 fma popcnt sse4_2`; the account's only allowed scheduling policy, `durable_object` (public beta). The image is `python:3.14-slim` (CPython 3.14.10) with `wasi-python==0.1.1` and `wasmtime==50.0.1` from PyPI. It runs as a non-root user `runner`, uid 10001, with `WASI_PYTHON_CACHE=/home/runner/.cache/wasi_python`. The fuel `.cwasm` is compiled into that folder at image build.

Labels: EXECUTED means run on that host and seen; READ means read from a file or page, cited; INFERRED means the researcher's reasoning.

## The short version

1. **On Cloudflare Containers the container's `/` is owned by uid 2346, not root.** wasi-python loads a `.cwasm` only from a path in which every folder, from `/` down, is root's or the running user's and is not writable by others unless sticky (`_way`). `/` is on the way to every path. So **no cache folder can pass on that host**: each process compiles the module in memory and writes nothing.
2. **The cost is a full compile at every container start:** 323 s and 295 s on `standard-1`, against about 0.3 s for a load.
3. **The check is right in its purpose:** compiled native code must not come from a folder another user could swap. But the owner of `/` is not "another user" in the sense the check guards against. Whoever owns `/` can already rename or replace any path below it, the cache's own folder included. Trusting `/`'s owner as the check trusts root adds no one who could not already swap the file.
4. **The warning's advice cannot be followed there.** It says "set $WASI_PYTHON_CACHE to a folder of yours", but every folder is below `/`.
5. **The site does not work around it.** Its owner chose to fix the check here (wasi-python-dev's decisions, 2026-10-27). Until a release does, the site's runner compiles at every start and stays always on.

## 1. What was seen (EXECUTED)

- **Every start compiled.** `wasi_python.stats()` around a warm-up call, `run(["-V"], fuel=30_000_000_000)`, at two container starts read `compiled 1, loaded 0, written 0`. The warm-ups took 322,867 ms and 295,016 ms.
- **The container was as built.** A read-only `exec` in the running container showed:
  - `/proc/1/status`: the main process runs as `Uid: 10001` and `Gid: 10001`.
  - `/proc/1/environ` holds `WASI_PYTHON_CACHE=/home/runner/.cache/wasi_python` and `HOME=/home/runner`.
  - `stat` shows `/home/runner`, `/home/runner/.cache` and `/home/runner/.cache/wasi_python` at `700 runner:runner`, and the `.cwasm`, `879bdb628a1a799dc3a6d1a645fee0f8-wasmtime50.0.1-fuel.cwasm`, at `600 runner:runner`.
- **wasi-python said why.** The first call, repeated in the container as uid 10001 with `warnings.simplefilter("always")`, printed:

  > RuntimeWarning: wasi_python: not using the module cache at /home/runner/.cache/wasi_python: /, on the way to it, is another user's (uid 2346); set $WASI_PYTHON_CACHE to a folder of yours

- **That probe's compile was killed at about 300 s** (exit 137, SIGKILL). It ran beside the main process, which held its own compiled module. The likely cause is a time limit on the host's `exec`, or memory. It was not investigated, and it does not bear on the finding.
- **The same image, run locally,** under Docker Desktop's linux/amd64 emulation on an M1 Pro, loaded the baked file: `loaded 1, written 0`, a warm-up of 1,410 ms. So the image and the folder's modes are right, and the difference is the host's `/`.

## 2. Why the check refuses it (READ)

`_way(folder, lstat)` walks `[*reversed(folder.parents), folder]`. For each folder that exists, it raises `PermissionError` when:
- it is not a folder;
- its `st_uid` is not in `(0, os.getuid())`;
- or it is writable by group or others and not sticky.

`_cache_warning` turns that into the `RuntimeWarning` above. The module is then compiled in the process and kept there, never written, and the call never fails. The first folder walked is `/`. On this host `lstat("/").st_uid == 2346`, so the walk stops there for every cache path.

INFERRED: uid 2346 is likely how the host's container runtime maps the root filesystem's owner, through a user namespace or an id-mapped mount. It is not documented on the pages read (READ, <https://developers.cloudflare.com/containers/>, 2026-10-27). Other runtimes that map ids could show the same, with another number.

## 3. Ways the check could change (INFERRED; none decided)

1. **Trust `/`'s owner as the check trusts root.** Accept `st_uid` in `(0, os.getuid(), lstat("/").st_uid)`, keeping the mode rule unchanged.
   - *For:* it adds no trust. Whoever owns `/` can already replace any path below it, so the check's guarantee — no one but you and those who already control the tree can swap the file — is unchanged.
   - *For:* it needs no embedder action, and it changes no public API.
   - *Against:* it is a change to a security check, so it needs its own specification and review.
2. **An embedder's explicit opt-in,** such as an environment variable or a `cache_dir` argument that vouches for a path.
   - *For:* nothing changes by default.
   - *Against:* it is a new public surface, and a vouch is easy to give carelessly.
3. **Leave the check, and say so in the docs.** `docs/get-started/install.md` would name this case and the workaround of running as `/`'s owner.
   - *Against:* the warning's advice stays wrong on such hosts.
4. **Better words in the warning, whatever else is done.** When the refused folder is `/` itself, no `$WASI_PYTHON_CACHE` can help, so the warning could say that instead of pointing at another folder.

## 4. What the site does meanwhile

Nothing in its image. Recorded in wasi-python-dev's `context/decisions.md`, 2026-10-27, "The cache fix is wasi-python's; no workaround here".
- The runner keeps its own user, uid 10001.
- Each start on Cloudflare compiles, so the runner is kept always on.
- A wasi-python release that changes the check is picked up by pinning it. The site's warm-up then reports `loaded`.

A workaround was considered and dropped: running the service as uid 2346, the owner of `/`, would pass the check as written. It would rest on an undocumented host detail. It would also be unsafe as the image stands, as the review of the site's specification 002 noted (INFERRED). `python:3.14-slim` carries setuid `su`, `mount` and `passwd`, and a process that owns `/` can replace `/etc`, for example with its own `/etc/ld.so.preload`, and so become root. Any plan to run as `/`'s owner would strip setuid bits first.

## Still unknown

- `/`'s mode, and `/home`'s owner and mode, on Cloudflare. The check stops at the first folder that fails it, and it refuses a non-sticky folder others may write, so trusting `/`'s owner is enough only if `/` is not writable by others and `/home` passes too. Only `/`'s owner was read. The site's next deploy reads both.

- Whether uid 2346 is stable across Cloudflare's hosts, accounts and the `default` scheduling policy. Only `durable_object` was seen.
- Whether a `.cwasm` compiled under emulation on arm64 loads on that host's CPU once the path check passes. It was never offered to wasmtime there. The site's next deploy answers it.
- Why the compile took about 300 s on a 1/2-vCPU instance, against the about 25 CPU-seconds measured on an M1 Pro (`2026-10-18-the-judge-on-several-cores.md`). A throttled share, a slower core, or both. Not measured.

In one line: on Cloudflare Containers `/` belongs to uid 2346, so wasi-python's cache path check refuses every folder and each start compiles for about five minutes; trusting `/`'s owner as root is trusted would fix it without trusting anyone new.
