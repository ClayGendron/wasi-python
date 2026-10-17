"""An async provider called from a synchronous shadow, and a cancel or deadline while inside it.

uv run --no-sync python async_cancel.py > async_cancel.txt

The event loop runs on the main thread (as an embedder's would); the guest runs on a worker thread
(as run_async does). The shadowed path_filestat_get posts the provider's coroutine to the loop and
waits in slices of 10 ms, checking a cancel event and a deadline between slices. On either, it
cancels the coroutine, answers ECANCELED and sets the store's epoch deadline to 0, as the runner's
_Call.stop does; the guest, which then spins, traps at its next function entry. Times are a
benchmark fact only.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import struct
import threading
import time

import wasmtime as wt
from wasmtime import _ffi

P1 = "wasi_snapshot_preview1"
CANCELED, NOENT = 11, 44

GUEST = f"""(module
 (import "{P1}" "path_filestat_get" (func $st (param i32 i32 i32 i32 i32) (result i32)))
 (memory (export "memory") 1)
 (data (i32.const 0) "slow.txt")
 (global $e (export "errno") (mut i32) (i32.const -1))
 (func $nop)
 (func (export "run") (result i32)
  (global.set $e (call $st (i32.const 3) (i32.const 0) (i32.const 0) (i32.const 8) (i32.const 64)))
  ;; a spin that enters a function each round, as CPython's interpreter does: wasmtime keeps the
  ;; epoch deadline in a local and reloads it at a function entry, so a bare (loop (br)) never
  ;; sees a deadline lowered by a host call (seen first; the runner's _Call.stop says the same)
  (loop $spin (call $nop) (br $spin))
  (i32.const 0)))"""


class SlowProvider:
    def __init__(self) -> None:
        self.seen: list[str] = []

    async def stat(self, path: str) -> tuple[str, int]:
        self.seen.append(f"stat {path} started")
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            self.seen.append("stat cancelled")
            raise
        return "file", 1


def trial(loop: asyncio.AbstractEventLoop, cancel_after: float | None, deadline_s: float | None) -> str:
    cfg = wt.Config()
    cfg.epoch_interruption = True
    engine = wt.Engine(cfg)
    store = wt.Store(engine)
    store.set_epoch_deadline(2**62)  # no deadline of the epoch's own: the shadow sets it to 0
    store.set_wasi(wt.WasiConfig())
    provider = SlowProvider()
    cancel = threading.Event()
    stop_at = None if deadline_s is None else time.monotonic() + deadline_s
    state = {"errno": None}

    def shadow(c, fd, flags, p, n, out):
        path = bytes(c.get("memory").read(c, p, p + n)).decode()
        fut = asyncio.run_coroutine_threadsafe(provider.stat(path), loop)
        while True:
            try:
                kind, size = fut.result(timeout=0.01)
                c.get("memory").write(c, struct.pack("<QQB7xQQQQQ", 0, 0, 4, 1, size, 0, 0, 0), out)
                return 0
            except concurrent.futures.TimeoutError:
                pass
            if cancel.is_set() or (stop_at is not None and time.monotonic() >= stop_at):
                fut.cancel()
                state["why"] = "cancelled" if cancel.is_set() else "deadline"
                _ffi.wasmtime_context_set_epoch_deadline(c._context(), 0)  # as _Call.stop
                return CANCELED

    linker = wt.Linker(engine)
    linker.define_wasi()
    linker.allow_shadowing = True
    i32 = wt.ValType.i32()
    linker.define_func(P1, "path_filestat_get", wt.FuncType([i32] * 5, [i32]), shadow, True)
    inst = linker.instantiate(store, wt.Module(engine, GUEST))
    run = inst.exports(store)["run"]
    if cancel_after is not None:
        threading.Timer(cancel_after, cancel.set).start()
    ticking = threading.Event()

    def ticker() -> None:  # the runner's epoch ticker: one tick every 10 ms
        while not ticking.wait(0.01):
            engine.increment_epoch()

    threading.Thread(target=ticker, daemon=True).start()
    t0 = time.perf_counter()
    try:
        run(store)
        outcome = "returned"
    except wt.Trap as e:
        outcome = f"trap {e.trap_code}"
    finally:
        ticking.set()
    secs = time.perf_counter() - t0
    errno = inst.exports(store)["errno"].value(store)
    time.sleep(0.05)  # let the loop deliver the cancellation to the coroutine
    return (f"cancel_after={cancel_after} deadline_s={deadline_s}: why={state.get('why')} "
            f"guest errno={errno} outcome={outcome} after {secs:.3f}s; provider saw {provider.seen}")


async def main() -> None:
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor(1) as pool:  # the guest's worker thread
        for args in ((0.3, None), (None, 0.5)):
            print(await loop.run_in_executor(pool, trial, loop, *args), flush=True)


asyncio.run(main())
