"""Guest probe, in stages across separate runs on one root: what a guest that ends inside a write
transaction leaves behind, and what the next run sees. STAGE picks the stage; WORK the directory.

  die     open a write transaction with a hot journal, then os._exit (as a killed guest would)
  spin    the same, then loop until the host's fuel runs out (a trap, not an exit)
  after   connect again: try a read and a write with timeout=0, then list the directory
  clear   remove <db>.lock, then read: SQLite rolls the hot journal back
  temp    where SQLite's temporary files go: force a spill to disk and list / and $SQLITE_TMPDIR
"""

import os
import sqlite3

W = os.environ.get("WORK", "/work")
STAGE = os.environ["STAGE"]
DB = f"{W}/k.db"
os.makedirs(W, exist_ok=True)


def listing(d=W):
    try:
        return sorted(os.listdir(d))
    except OSError as e:
        return f"{type(e).__name__}"


def attempt(name, fn):
    try:
        print(name, "->", fn())
    except Exception as e:  # noqa: BLE001
        print(name, "!!", type(e).__name__, e)


if STAGE in ("die", "spin"):
    for p in (DB, DB + "-journal"):
        if os.path.exists(p):
            os.remove(p)
    if os.path.isdir(DB + ".lock"):
        os.rmdir(DB + ".lock")
    c = sqlite3.connect(DB)
    c.execute("create table t(a)")
    c.executemany("insert into t values (?)", [(i,) for i in range(100)])
    c.commit()
    c.execute("pragma cache_size=1")
    c.execute("update t set a = a + 1000")  # changes pages: the journal holds their old content
    c.execute("insert into t select randomblob(4000) from t")  # forces a spill to the file
    print("in transaction", listing(), flush=True)
    if STAGE == "die":
        os._exit(3)
    while True:
        pass
elif STAGE == "after":
    print("left behind", listing())
    c = sqlite3.connect(DB, timeout=0)
    attempt("read", lambda: c.execute("select count(*), min(a) from t").fetchone())
    attempt("write", lambda: (c.execute("insert into t values (1)"), c.commit()))
elif STAGE == "clear":
    os.rmdir(DB + ".lock")
    c = sqlite3.connect(DB, timeout=0)
    attempt("read after clearing", lambda: c.execute("select count(*), min(a) from t").fetchone())
    print("after recovery", listing())
elif STAGE == "temp":
    print("SQLITE_TMPDIR", os.environ.get("SQLITE_TMPDIR"), "TMPDIR", os.environ.get("TMPDIR"))
    c = sqlite3.connect(":memory:")
    c.execute("pragma temp_store=file")
    c.execute("pragma cache_size=2")
    c.execute("create temp table big(x)")
    c.executemany("insert into big values (randomblob(1000))", [()] * 3000)
    cur = c.execute("select x from big order by x")
    cur.fetchone()
    print("during: /", [n for n in listing("/") if n.startswith("etilqs")],
          "tmp", listing(os.environ["SQLITE_TMPDIR"]) if os.environ.get("SQLITE_TMPDIR") else None)
    cur.close()
    c.commit()
    attempt("vacuum into", lambda: (c.execute(f"vacuum into '{W}/v.db'"), os.path.getsize(f"{W}/v.db") > 0)[-1])
    print("after: /", [n for n in listing("/") if n.startswith("etilqs")])
print("end", STAGE)
