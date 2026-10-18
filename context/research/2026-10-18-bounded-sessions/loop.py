"""The door-loop prototype (the research's E2): one `run`, each door answer is the next turn."""
import sys; sys.path.insert(0, sys.argv[1]) if len(sys.argv) > 1 else None
import h, wasmtime as wt

LOOP = r'''
import _host, sys, traceback
g = {"__name__": "__main__", "__builtins__": __builtins__}
code = _host.call(b"start")
while code:
    try:
        exec(compile(code, "<turn>", "exec"), g)
    except BaseException:
        traceback.print_exc()
    sys.stdout.flush(); sys.stderr.flush()
    code = _host.call(b"done")
'''

def session(turns, memory_bytes=None, on_turn=None):
    """Run `turns` in one instance. Returns per-turn (stdout, stderr, memory bytes) and how it ended."""
    results = []
    queue = list(turns)
    state = {"g": None}
    def door(caller, req):
        g = state["g"]
        if req == b"done":
            out, err = g.swap_streams()
            mem = caller["memory"].data_len(caller)
            results.append((bytes(out.data), bytes(err.data), mem))
            if on_turn: on_turn(len(results), out, err)
        else:
            g.swap_streams()
        return queue.pop(0).encode() if queue else b""
    g = h.Guest(door=door, argv=("python", "-c", LOOP), memory_bytes=memory_bytes)
    state["g"] = g
    g.store.set_fuel(2**62)
    try:
        rc = g.ex["run"](g.store); ended = f"run returned {rc}"
    except wt.ExitTrap as e:
        ended = f"exit {e.code}"
    except wt.Trap as e:
        ended = f"trap {e.trap_code}: {e.message.splitlines()[0]}"
    tail = (bytes(g.out.data), bytes(g.err.data))
    g.close()
    return results, ended, tail
