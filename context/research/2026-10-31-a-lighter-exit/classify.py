"""Phase totals from a fuel-sampled profile. usage: classify.py <prof.tsv> <step> [--detail]
A sample's phase is its most specific marker frame; a sample whose stack was cut (wasmtime keeps
the innermost 20 frames) takes the phase of its neighbours when they agree."""
import sys, collections
MARK = [  # (frame, phase); later entries are more specific
    ("run", "program and the reactor"),
    ("gc_unfreeze", "gc.unfreeze"), ("gc_unfreeze_impl", "gc.unfreeze"),
    ("Py_FinalizeEx", "finalize: other"),
    ("make_pre_finalization_calls", "atexit and threads"), ("_PyAtExit_Call", "atexit and threads"),
    ("flush_std_files", "flush stdout/stderr"),
    ("PyGC_Collect", "collect 1 (whole heap, before modules)"),
    ("_PyImport_FiniExternal", "finalize: other"),
    ("finalize_modules", "modules: other"),
    ("finalize_modules_delete_special", "modules: delete special"),
    ("finalize_remove_modules", "modules: sys.modules values to None"),
    ("finalize_clear_modules_dict", "modules: clear sys.modules"),
    ("finalize_restore_builtins", "modules: restore builtins"),
    ("_PyGC_CollectNoFail", "COLLECTNOFAIL"),
    ("finalize_modules_clear_weaklist", "modules: wipe surviving modules' dicts"),
    ("_PyModule_Clear", "modules: wipe surviving modules' dicts"),
    ("finalize_clear_sys_builtins_dict", "modules: wipe sys and builtins"),
    ("_PyImport_ClearModulesByIndex", "modules: other"),
    ("_PyImport_ClearModules", "modules: other"),
    ("finalize_interp_clear", "interpreter state and types"),
    ("finalize_interp_delete", "interpreter state and types"),
    ("_PyRuntime_Finalize", "interpreter state and types"),
]
RANK = {f: (i, p) for i, (f, p) in enumerate(MARK)}
ALLOC = ("free", "dlfree", "dispose_chunk", "malloc", "dlmalloc", "realloc", "calloc", "PyMem_", "_PyMem_", "PyObject_Free", "_PyObject_Free", "mi_", "_mi_", "memset", "memcpy", "sbrk")
GC = ("gc_", "visit_", "update_refs", "subtract_refs", "move_", "deduce_", "_traverse", "handle_", "finalize_garbage", "delete_garbage", "untrack_", "clear_weakrefs")
def leaf_class(stack):
    leaf = stack[-1]
    if leaf.startswith(ALLOC) or leaf in ("free",):
        return "allocator"
    if any(leaf.startswith(g) or g in leaf for g in GC):
        return "collector walk"
    return "dealloc and other"
rows = [l.rstrip("\n").split("\t") for l in open(sys.argv[1])]
step = int(sys.argv[2])
phases = []
seen_weak = False
for fuel, st in rows:
    if st.startswith("END"):
        phases.append(("END", [])); continue
    stack = st.split(";")
    best = None
    for f in stack:
        if f in RANK and (best is None or RANK[f][0] > best[0]):
            best = RANK[f]
    p = best[1] if best else None
    if p == "COLLECTNOFAIL":
        p = "modules: collect 3 (last)" if seen_weak else "modules: collect 2 (after sys.modules cleared)"
    if p and p.startswith("modules: wipe"):
        seen_weak = True
    # a cut stack whose only marker is "run" with no finalize frames could be anywhere: mark unknown
    if p == "program and the reactor" and stack[0] != "run":
        p = None
    phases.append((p, stack))
# neighbour fill
lab = [p for p, _ in phases]
for i, p in enumerate(lab):
    if p is None:
        j = i - 1
        while j >= 0 and lab[j] is None: j -= 1
        k = i + 1
        while k < len(lab) and phases[k][0] is None: k += 1
        a = lab[j] if j >= 0 else None
        b = phases[k][0] if k < len(lab) else None
        lab[i] = a if a == b and a else f"(cut) {a} | {b}"
tot = collections.Counter(); leaf = collections.defaultdict(collections.Counter)
for (p, stack), l in zip(phases, lab):
    if l == "END": continue
    tot[l] += step
    if stack: leaf[l][leaf_class(stack)] += step
order = []
for l in lab:
    if l not in order and l != "END": order.append(l)
s = sum(tot.values())
for l in order:
    lc = ", ".join(f"{k} {v/1e6:.2f}" for k, v in leaf[l].most_common())
    print(f"{tot[l]/1e6:7.2f} M  {l}   [{lc}]")
print(f"{s/1e6:7.2f} M  sampled")
allc = collections.Counter()
for l in leaf:
    if l != "program and the reactor": allc.update(leaf[l])
print("teardown by leaf:", {k: round(v/1e6, 2) for k, v in allc.items()})
if "--detail" in sys.argv:
    c = collections.Counter(st[-1] for p, st in phases if st and p != "program and the reactor")
    for k, v in c.most_common(30): print(f"  {v*step/1e6:6.2f} M leaf {k}")
