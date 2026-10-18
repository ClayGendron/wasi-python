"""Prototype: the frozen zip with every .pyc's code named as zipimport names a .py in the zip."""
import marshal, sys, zipfile
src, dst, prefix = sys.argv[1], sys.argv[2], sys.argv[3]

def rename(code, name):
    consts = tuple(rename(c, name) if isinstance(c, type(code)) else c for c in code.co_consts)
    return code.replace(co_filename=name, co_consts=consts)

n = 0
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w") as zout:
    for info in zin.infolist():
        data = zin.read(info)
        if info.filename.endswith(".pyc"):
            code = marshal.loads(data[16:])
            data = data[:16] + marshal.dumps(rename(code, prefix + info.filename[:-1]))
            n += 1
        zi = zipfile.ZipInfo(info.filename, info.date_time)
        zi.compress_type, zi.external_attr = info.compress_type, info.external_attr
        zout.writestr(zi, data)
print("renamed", n)
