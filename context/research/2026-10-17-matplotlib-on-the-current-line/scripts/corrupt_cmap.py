import struct, sys
data = bytearray(open(sys.argv[1], "rb").read())
n = struct.unpack(">H", data[4:6])[0]
for i in range(n):
    tag, _, off, length = struct.unpack(">4sIII", data[12 + 16 * i: 28 + 16 * i])
    if tag == b"cmap":
        cmap = off
nsub = struct.unpack(">H", data[cmap + 2: cmap + 4])[0]
hit = 0
for i in range(nsub):
    pid, eid, soff = struct.unpack(">HHI", data[cmap + 4 + 8 * i: cmap + 12 + 8 * i])
    st = cmap + soff
    fmt = struct.unpack(">H", data[st: st + 2])[0]
    if fmt == 4:
        data[st + 6: st + 8] = struct.pack(">H", 7)  # segCountX2 must be even: invalid
        hit += 1
open(sys.argv[2], "wb").write(data)
print("format-4 subtables corrupted:", hit, "of", nsub)
