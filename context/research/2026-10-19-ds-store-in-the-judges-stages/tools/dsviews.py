"""Print the view-settings blobs (lsvp, lsvP, icvp, bwsp) of named entries in a .DS_Store, decoded as plists."""
import plistlib, struct, sys
data = open(sys.argv[1], "rb").read() + bytes(16)
want = set(sys.argv[2:])
i = 0
while i + 4 < len(data):
    (ln,) = struct.unpack(">I", data[i:i+4])
    if 0 < ln < 256:
        try:
            name = data[i+4:i+4+2*ln].decode("utf-16-be")
        except UnicodeDecodeError:
            i += 1; continue
        j = i + 4 + 2*ln
        code, typ = data[j:j+4], data[j+4:j+8]
        if typ == b"blob" and code in (b"lsvp", b"lsvP", b"icvp", b"bwsp", b"lsvC") and (not want or name in want):
            (bl,) = struct.unpack(">I", data[j+8:j+12]); blob = data[j+12:j+12+bl]
            try:
                pl = plistlib.loads(blob)
                keep = {k: pl[k] for k in pl if k in ("calculateAllSizes", "viewOptionsVersion", "showSize", "ShowSidebar", "ShowStatusBar")}
                if "columns" in pl and isinstance(pl["columns"], dict):
                    keep["sizeColumnVisible"] = pl["columns"].get("size", {}).get("visible")
                print(name, code.decode(), keep)
            except Exception as e:
                print(name, code.decode(), "undecodable", e)
            i = j + 12 + bl; continue
    i += 1
