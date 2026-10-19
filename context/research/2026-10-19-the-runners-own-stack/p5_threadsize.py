"""Probe 5: with the runner's wasm stack at W, which thread sizes survive a guest that uses all of
it? Each trial in its own process: a host killed by SIGSEGV or SIGBUS shows as a negative exit."""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))

def trial(w, where, shape, metered=True):
    args = [sys.executable, os.path.join(HERE, "stackrun.py"), str(w), str(where), shape]
    if metered:
        args.append("metered")
    r = subprocess.run(args, capture_output=True, text=True, timeout=900)
    line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    try:
        res = json.loads(line)
    except Exception:
        res = {}
    return r.returncode, res

def survives(w, t, shape):
    code, res = trial(w, t, shape)
    return code == 0 and res.get("trapped") == "stack overflow", code, res

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "grid":
        w = int(sys.argv[2]); shape = sys.argv[3]
        for t in sys.argv[4:]:
            code, res = trial(w, t, shape)
            print(f"W={w} T={t} shape={shape}: exit {code} trapped={res.get('trapped')} "
                  f"stdout={res.get('stdout', '')!r} thread_stack={res.get('thread_stack')}", flush=True)
    elif mode == "bisect":
        # smallest T (to `step`) at or above lo that survives; assumes survival is monotone in T
        w, shape, lo, hi, step = int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
        ok_hi = survives(w, hi, shape)
        print(f"W={w} {shape}: T={hi} -> {ok_hi[0]} (exit {ok_hi[1]})", flush=True)
        if not ok_hi[0]:
            sys.exit(0)
        while hi - lo > step:
            mid = (lo + hi) // 2 // step * step
            ok, code, res = survives(w, mid, shape)
            print(f"W={w} {shape}: T={mid} -> {ok} (exit {code}, thread_stack {res.get('thread_stack')})", flush=True)
            if ok:
                hi = mid
            else:
                lo = mid
        print(f"RESULT W={w} {shape}: smallest surviving T = {hi} ({(hi - w) / 1024:+.0f} KiB over W)", flush=True)

def depth_edge(w, t, name, lo, hi):
    """The largest depth of `name` that completes ('freed') at wasm stack w on a thread of t."""
    while hi - lo > 1:
        mid = (lo + hi) // 2
        code, res = trial(w, t, f"{name}:{mid}")
        ok = code == 0 and res.get("stdout", "").strip().endswith("freed")
        if code != 0:
            print(f"  depth {mid}: host died (exit {code})", flush=True)
        if ok:
            lo = mid
        else:
            hi = mid
    return lo

if __name__ == "__main__" and sys.argv[1] == "edge":
    w, t, name, lo, hi = int(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
    print(f"RESULT W={w} T={t} {name}: last depth that completes = {depth_edge(w, t, name, lo, hi)}", flush=True)
