# The guest program for shadow.py's provider mode: ordinary file calls on /work (a provider)
# beside /data (a real read-only grant), and imports from the zip.
import csv, json, os, decimal
rows = list(csv.reader(open("/data/in.csv")))
print("grant:", rows)
print("seed:", open("/work/seed.txt").read().strip())
os.mkdir("/work/out")
with open("/work/out/a.json", "w") as f:
    json.dump({"rows": rows}, f)
with open("/work/out/a.json", "a") as f:
    f.write("\n")
os.rename("/work/out/a.json", "/work/out/b.json")
print("listdir:", sorted(os.listdir("/work")), sorted(os.listdir("/work/out")))
print("stat:", os.stat("/work/out/b.json").st_size, os.path.isdir("/work/out"))
print("roundtrip:", json.load(open("/work/out/b.json")) == {"rows": rows})
for bad in ("/work/../data/in.csv", "/work/out/../../etc"):
    try:
        open(bad); print("opened", bad)
    except OSError as e:
        print("refused:", bad, e.errno, e.strerror)
try:
    with open("/work/denied.txt", "w") as f:
        f.write("x")
except OSError as e:
    print("write-back refused at close:", e.errno, e.strerror)
os.remove("/work/out/b.json"); os.rmdir("/work/out")
try:
    open("/data/new.txt", "w")
except OSError as e:
    print("read-only grant still read-only:", e.errno)
print("after:", sorted(os.listdir("/work")))
