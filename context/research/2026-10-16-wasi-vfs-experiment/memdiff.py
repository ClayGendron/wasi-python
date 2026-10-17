"""Instantiate two modules without calling any export and compare their initial linear memories
and exported-or-not globals' first byte runs. Usage: memdiff.py <a.wasm> <b.wasm>"""

import sys

import wasmtime as wt


def image(path):
    eng = wt.Engine()
    mod = wt.Module.from_file(eng, path)
    st = wt.Store(eng)
    st.set_wasi(wt.WasiConfig())
    lk = wt.Linker(eng)
    lk.define_wasi()
    i32 = wt.ValType.i32()
    lk.define_func("host", "call", wt.FuncType([i32] * 4, [i32]), lambda *a: -1)
    inst = lk.instantiate(st, mod)
    mem = inst.exports(st)["memory"]
    return bytes(mem.read(st, 0, mem.data_len(st)))


a, b = image(sys.argv[1]), image(sys.argv[2])
print("memory bytes", len(a), len(b))
n = min(len(a), len(b))
runs, i = [], 0
while i < n:
    if a[i] != b[i]:
        j = i
        while j < n and a[j] != b[j]:
            j += 1
        runs.append((i, j))
        i = j
    else:
        i += 1
print("differing runs", len(runs), "bytes", sum(j - i for i, j in runs))
for i, j in runs[:12]:
    print(hex(i), j - i, a[i : min(j, i + 24)].hex(), "|", b[i : min(j, i + 24)].hex())
