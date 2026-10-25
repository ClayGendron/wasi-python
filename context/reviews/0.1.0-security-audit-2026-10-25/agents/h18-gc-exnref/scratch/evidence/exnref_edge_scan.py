"""Read-only scan of a wasm module for the precondition of wasmtime GHSA-hw8m-q44c-ggrf.

The defect (wasmtime 49.0.0, cranelift-frontend 0.136.0, fixed in 0.136.3): a GC
reference passed as a block-call argument on a `try_call`'s edge was counted as a use
*before* the call, so a reference live after the call only through that edge was left
out of the call's stack map.

How Wasmtime 49.0.0 builds those edges (wasmtime-internal-cranelift-49.0.0):
  * every call / call_indirect / throw / throw_ref lexically inside a try_table becomes
    try_call with edges continuation(ret..) and handler(exn0) only;
  * the continuation block is sealed at once with one predecessor, so it never gets an
    SSA parameter;
  * a catch handler block has every try_call of its region as predecessor; cranelift's
    SSA builder adds a parameter to it (and a Value argument on each try_call edge) only
    when a wasm *local* is read on the catch path before being written AND the
    predecessors disagree on that local's SSA value.
Only exnref-typed (GC) locals matter: i32/i64/f32/f64 values need no stack map, and
operand-stack values cannot flow across a catch edge (a branch carries only the label's
types).

So the precondition, at the wasm level, for a GC-ref local L and a try_call c inside a
try_table whose catch clause targets handler H:
  P1  L is live at H's continuation (read before written on some path from there);
  P2  L is not live at c's normal successor (otherwise the value is in the stack map
      anyway and the edge argument is reloaded from a rooted slot);
  P3  the reaching definitions of L at H's predecessor calls are not all one value.
This script parses the type/import/function/code sections for local types, streams
`llvm-objdump -d` text for instruction structure, builds an instruction-level CFG with
exception edges, and reports every (function, call, L, handler) satisfying P1..P3.
It never executes the module.
"""
import re
import subprocess
import sys
import json
from collections import defaultdict


def leb_u(b, i):
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        s += 7
        if not x & 0x80:
            return r, i


def leb_s(b, i):
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        s += 7
        if not x & 0x80:
            if x & 0x40:
                r |= -(1 << s)
            return r, i


def valtype(b, i):
    t = b[i]
    i += 1
    if t in (0x63, 0x64):
        ht, i = leb_s(b, i)
        return (t, ht), i
    return (t, None), i


# GC-managed reference types that need a stack map in Wasmtime (funcref does not).
GC_SHORT = {0x6F: "externref", 0x6E: "anyref", 0x6D: "eqref", 0x6C: "i31ref",
            0x6B: "structref", 0x6A: "arrayref", 0x69: "exnref"}
GC_HEAP = {-0x11: "extern", -0x12: "any", -0x13: "eq", -0x14: "i31", -0x15: "struct",
           -0x16: "array", -0x17: "exn"}


def gc_name(vt):
    t, ht = vt
    if t in GC_SHORT:
        return GC_SHORT[t]
    if t in (0x63, 0x64):
        if ht is not None and ht >= 0:
            return "concrete%d" % ht  # a defined type: GC unless a func type
        return GC_HEAP.get(ht)
    return None


def module_locals(path):
    b = open(path, "rb").read()
    i = 8
    types = []
    nimp_func = 0
    func_types = []
    bodies = []
    while i < len(b):
        sid = b[i]
        i += 1
        sz, i = leb_u(b, i)
        start, end = i, i + sz
        if sid == 1:
            n, j = leb_u(b, i)
            for _ in range(n):
                group = 1
                if b[j] == 0x4E:
                    j += 1
                    group, j = leb_u(b, j)
                for _ in range(group):
                    if b[j] in (0x50, 0x4F):
                        j += 1
                        ns, j = leb_u(b, j)
                        for _ in range(ns):
                            _, j = leb_u(b, j)
                    form = b[j]
                    j += 1
                    assert form == 0x60, hex(form)
                    np_, j = leb_u(b, j)
                    ps = []
                    for _ in range(np_):
                        vt, j = valtype(b, j)
                        ps.append(vt)
                    nr, j = leb_u(b, j)
                    for _ in range(nr):
                        _, j = valtype(b, j)
                    types.append(ps)
        elif sid == 2:
            n, j = leb_u(b, i)
            for _ in range(n):
                for _ in range(2):
                    ln, j = leb_u(b, j)
                    j += ln
                kind = b[j]
                j += 1
                if kind == 0:
                    _, j = leb_u(b, j)
                    nimp_func += 1
                elif kind == 1:
                    j += 1
                    fl, j = leb_u(b, j)
                    _, j = leb_u(b, j)
                    if fl & 1:
                        _, j = leb_u(b, j)
                elif kind == 2:
                    fl, j = leb_u(b, j)
                    _, j = leb_u(b, j)
                    if fl & 1:
                        _, j = leb_u(b, j)
                elif kind == 3:
                    _, j = valtype(b, j)
                    j += 1
                elif kind == 4:
                    j += 1
                    _, j = leb_u(b, j)
                else:
                    raise ValueError(kind)
        elif sid == 3:
            n, j = leb_u(b, i)
            for _ in range(n):
                t, j = leb_u(b, j)
                func_types.append(t)
        elif sid == 10:
            n, j = leb_u(b, i)
            for k in range(n):
                bsz, j = leb_u(b, j)
                bend = j + bsz
                ng, q = leb_u(b, j)
                params = types[func_types[k]]
                idx = len(params)
                gc = {}
                for pi, vt in enumerate(params):
                    nm = gc_name(vt)
                    if nm:
                        gc[pi] = nm
                for _ in range(ng):
                    cnt, q = leb_u(b, q)
                    vt, q = valtype(b, q)
                    nm = gc_name(vt)
                    if nm:
                        for x in range(idx, idx + cnt):
                            gc[x] = nm
                    idx += cnt
                bodies.append(gc)
                j = bend
        i = end
    return nimp_func, bodies


HDR = re.compile(r"^[0-9a-f]+ <(.*)>:$")
CATCH = re.compile(r"\((catch_all_ref|catch_all|catch_ref|catch)((?: \d+)+)\)")
CALLS = {"call", "call_indirect", "throw", "throw_ref", "call_ref"}
TERM = {"return", "unreachable", "return_call", "return_call_indirect", "return_call_ref"}


def analyse(name, insns, gc):
    """insns: list of (addr, mnemonic, operands). Returns findings and stats."""
    n = len(insns)
    # Structure: match block/loop/if/try_table with end; else to its if.
    stack = []
    match_end = {}
    else_of = {}
    frame_kind = {}
    for k, (_, m, _) in enumerate(insns):
        if m in ("block", "loop", "if", "try_table"):
            stack.append(k)
            frame_kind[k] = m
        elif m == "else":
            else_of[stack[-1]] = k
        elif m == "end":
            if stack:
                match_end[stack.pop()] = k
            # the final end closes the function
    # Successors and exception successors per instruction.
    succ = [[] for _ in range(n + 1)]  # n = function exit
    exc = defaultdict(list)  # call index -> list of (handler continuation index, try_table idx)
    stack = []
    for k, (_, m, ops) in enumerate(insns):
        def target(depth):
            fr = stack[-1 - depth] if depth < len(stack) else None
            if fr is None:
                return n
            if frame_kind[fr] == "loop":
                return fr + 1
            return match_end[fr] + 1 if fr in match_end else n
        nxt = k + 1 if k + 1 < n else n
        if m in ("block", "loop", "try_table"):
            if m == "try_table":
                # catch labels are resolved outside the try_table's own label
                clauses = []
                for kind, labs in CATCH.findall(ops):
                    nums = [int(x) for x in labs.split()]
                    lab = nums[-1]
                    clauses.append((kind, target(lab)))
                stack.append(k)
                insns[k] = (insns[k][0], m, ops, clauses)
            else:
                stack.append(k)
            succ[k] = [nxt]
        elif m == "if":
            stack.append(k)
            e = else_of.get(k)
            en = match_end[k]
            succ[k] = [nxt, (e + 1) if e is not None else en]
        elif m == "else":
            fr = stack[-1]
            succ[k] = [match_end[fr]]
        elif m == "end":
            if stack:
                stack.pop()
            succ[k] = [nxt]
        elif m == "br":
            succ[k] = [target(int(ops.split()[0]))]
        elif m == "br_if" or m in ("br_on_null", "br_on_non_null"):
            succ[k] = [nxt, target(int(ops.split()[0]))]
        elif m == "br_table":
            labs = [int(x) for x in re.findall(r"\d+", ops.split("}")[0])]
            succ[k] = sorted({target(x) for x in labs})
        elif m in TERM or m in ("throw", "throw_ref"):
            succ[k] = []
        else:
            succ[k] = [nxt]
        if m in CALLS:
            for fr in reversed(stack):
                if frame_kind[fr] == "try_table":
                    for kind, cont in insns[fr][3]:
                        exc[k].append((cont, fr, kind))
    # Liveness (backward) of GC locals over normal + exception edges.
    locs = sorted(gc)
    uses = [set() for _ in range(n + 1)]
    defs = [set() for _ in range(n + 1)]
    for k, ins in enumerate(insns):
        m, ops = ins[1], ins[2]
        if m in ("local.get", "local.set", "local.tee"):
            x = int(ops.split()[0])
            if x in gc:
                (uses if m == "local.get" else defs)[k].add(x)
    if not any(defs) and not any(uses):
        return None
    allsucc = [list(succ[k]) + [c for c, _, _ in exc.get(k, [])] for k in range(n + 1)]
    preds = [[] for _ in range(n + 1)]
    for k in range(n + 1):
        for s in allsucc[k]:
            preds[s].append(k)
    live_in = [set() for _ in range(n + 1)]
    work = list(range(n + 1))
    inq = [True] * (n + 1)
    while work:
        k = work.pop()
        inq[k] = False
        out = set()
        for s in allsucc[k]:
            out |= live_in[s]
        new = (out - defs[k]) | uses[k]
        if new != live_in[k]:
            live_in[k] = new
            for p in preds[k]:
                if not inq[p]:
                    inq[p] = True
                    work.append(p)
    # Reaching definitions (forward), definition id = instruction index; -1 = entry value.
    reach = [None] * (n + 1)
    reach_in = [dict() for _ in range(n + 1)]
    reach_in[0] = {x: {-1} for x in locs}
    work = [0]
    inq = [False] * (n + 1)
    inq[0] = True
    while work:
        k = work.pop()
        inq[k] = False
        cur = {x: set(v) for x, v in reach_in[k].items()}
        if k < n:
            for x in defs[k]:
                cur[x] = {k}
        for s in allsucc[k]:
            changed = False
            ri = reach_in[s]
            for x, v in cur.items():
                old = ri.get(x)
                if old is None or not v <= old:
                    ri[x] = (old or set()) | v
                    changed = True
            if changed and not inq[s]:
                inq[s] = True
                work.append(s)
    findings = []
    stats = {"try_calls": 0, "p1": 0, "p1p2": 0,
             "try_calls_with_gc_local_live_on_normal_path": 0,
             "instructions_with_gc_local_live_in": sum(1 for k in range(n) if live_in[k]),
             "handler_continuations": 0}
    handler_preds = defaultdict(list)
    for k, lst in exc.items():
        for cont, fr, kind in lst:
            handler_preds[(fr, cont, kind)].append(k)
    stats["handler_continuations"] = len(handler_preds)
    for k, lst in exc.items():
        stats["try_calls"] += 1
        normal_live = set()
        for s in succ[k]:
            normal_live |= live_in[s]
        if not succ[k]:
            normal_live = set()
        if normal_live:
            stats["try_calls_with_gc_local_live_on_normal_path"] += 1
        for cont, fr, kind in lst:
            for x in live_in[cont]:
                stats["p1"] += 1
                if x in normal_live:
                    continue
                stats["p1p2"] += 1
                vals = set()
                for p in handler_preds[(fr, cont, kind)]:
                    vals.add(frozenset(reach_in[p].get(x, {-1})))
                agree = len(vals) == 1
                findings.append({
                    "function": name, "call_addr": insns[k][0], "call": insns[k][1] + " " + insns[k][2],
                    "local": x, "local_type": gc[x], "try_table_addr": insns[fr][0],
                    "clause": kind, "handler_cont_addr": insns[cont][0] if cont < n else "exit",
                    "reaching_defs_at_handler_preds": sorted(str(sorted(v)) for v in vals),
                    "p3_disagreement": not agree,
                })
    return findings, stats


def main(wasm, objdump, out_json):
    nimp, bodies = module_locals(wasm)
    with_gc = sum(1 for g in bodies if g)
    kinds = defaultdict(int)
    for g in bodies:
        for v in g.values():
            kinds[v] += 1
    proc = subprocess.Popen([objdump, "-d", wasm], stdout=subprocess.PIPE, text=True,
                            bufsize=1 << 20, stderr=subprocess.DEVNULL)
    fidx = -1
    name = None
    insns = []
    all_findings = []
    totals = defaultdict(int)
    analysed = 0

    def flush():
        nonlocal analysed
        if name is None or fidx < 0 or fidx >= len(bodies):
            return
        gc = bodies[fidx]
        if not gc or not any(i[1] == "try_table" for i in insns):
            return
        r = analyse(name, insns, gc)
        analysed += 1
        if r:
            f, st = r
            all_findings.extend(f)
            for a, v in st.items():
                totals[a] += v

    for line in proc.stdout:
        h = HDR.match(line)
        if h:
            if h.group(1) == "CODE":
                continue
            flush()
            fidx += 1
            name = h.group(1)
            insns = []
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) >= 2 and ":" in parts[0]:
            addr = parts[0].strip().split(":")[0]
            m = parts[1].strip()
            ops = "\t".join(parts[2:]).split("#")[0].strip() if len(parts) > 2 else ""
            if m == "br_table":
                ops = "\t".join(parts[2:])
            insns.append((addr, m, ops))
    flush()
    proc.wait()
    res = {
        "wasm": wasm.split("/")[-1],
        "imported_functions": nimp,
        "defined_function_bodies": len(bodies),
        "objdump_functions_seen": fidx + 1,
        "bodies_with_gc_ref_locals_or_params": with_gc,
        "gc_ref_local_slots_by_type": dict(kinds),
        "functions_analysed_gc_locals_and_try_table": analysed,
        "totals": dict(totals),
        "p1_p2_findings": len(all_findings),
        "p1_p2_p3_findings": sum(1 for f in all_findings if f["p3_disagreement"]),
        "findings_sample": all_findings[:200],
    }
    json.dump(res, open(out_json, "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "findings_sample"}, indent=1))


def selftest():
    """The bug's shape in hand-written wasm text: local 0 is exnref; inside try_table T a
    call c1 sees L's entry value, then L is set from an inner catch, then call c2 sees the
    new value and L is dead after c2 on the normal path, but T's catch path reads L."""
    prog = [
        ("a0", "block", ""),                        # label for T's catch
        ("a1", "try_table", "(catch_all 0)"),
        ("a2", "call", "1"),                        # c1
        ("a3", "block", "exnref"),
        ("a4", "try_table", "(catch_all_ref 0)"),
        ("a5", "call", "2"),
        ("a6", "end", ""),
        ("a7", "unreachable", ""),
        ("a8", "end", ""),
        ("a9", "local.set", "0"),                   # L := exnref from the inner catch
        ("aa", "call", "3"),                        # c2: L dead on the normal path after it
        ("ab", "return", ""),
        ("ac", "end", ""),
        ("ad", "end", ""),
        ("ae", "local.get", "0"),                   # T's catch path reads L
        ("af", "throw_ref", ""),
        ("b0", "end", ""),
    ]
    f, st = analyse("selftest", prog, {0: "exnref"})
    hits = [x for x in f if x["call_addr"] == "aa" and x["p3_disagreement"]]
    assert hits, (f, st)
    # The ordinary, correctly handled shape: L read on the normal path after the call.
    prog2 = [
        ("b0", "block", "exnref"),
        ("b1", "try_table", "(catch_all_ref 0)"),
        ("b2", "call", "1"),
        ("b3", "end", ""),
        ("b4", "unreachable", ""),
        ("b5", "end", ""),
        ("b6", "local.set", "0"),
        ("b7", "block", ""),
        ("b8", "try_table", "(catch_all 0)"),
        ("b9", "call", "2"),
        ("ba", "end", ""),
        ("bb", "end", ""),
        ("bc", "local.get", "0"),
        ("bd", "throw_ref", ""),
        ("be", "end", ""),
    ]
    f2, st2 = analyse("selftest2", prog2, {0: "exnref"})
    assert not f2 and st2["try_calls_with_gc_local_live_on_normal_path"] >= 1, (f2, st2)
    print("selftest ok", st, st2)


if __name__ == "__main__":
    if sys.argv[1] == "--selftest":
        selftest()
    else:
        selftest()
        main(sys.argv[1], sys.argv[2], sys.argv[3])
