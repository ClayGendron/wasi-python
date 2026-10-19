"""A simulated .DS_Store writer: as this user, like Finder or StorageManagementService, write a
.DS_Store into every folder under each run-* stage below <base>, again and again, until <stop>
exists. Logs one line per pass: the time, folders tried, files written, refusals.
usage: writer.py <base> <stop> <log> [<interval s>]"""
import os, sys, time
base, stop, log = sys.argv[1], sys.argv[2], sys.argv[3]
interval = float(sys.argv[4]) if len(sys.argv) > 4 else 0.3
BLOB = b"\x00\x00\x00\x01Bud1" + bytes(6140)
with open(log, "a") as out:
    while not os.path.exists(stop):
        tried = wrote = refused = 0
        try:
            stages = [os.path.join(base, n) for n in os.listdir(base) if n.startswith("run-")]
        except OSError:
            stages = []
        for s in stages:
            for d, dirs, files in os.walk(s):
                tried += 1
                p = os.path.join(d, ".DS_Store")
                if os.path.exists(p):
                    continue
                try:
                    with open(p, "wb") as f:
                        f.write(BLOB)
                    wrote += 1
                except OSError:
                    refused += 1
        if tried:
            out.write(f"{time.strftime('%H:%M:%S')} stages={len(stages)} folders={tried} wrote={wrote} refused={refused}\n")
            out.flush()
        time.sleep(interval)
