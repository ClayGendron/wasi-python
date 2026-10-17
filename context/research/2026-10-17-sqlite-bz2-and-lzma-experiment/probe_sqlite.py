"""Guest probe: sqlite3 in memory and on a file, its pragmas, a second connection, the APIs the
module offers, and pandas' to_sql/read_sql. Each case prints one line; an exception is printed as
its type and message, so one failure does not hide the next. WORK names a writable directory."""

import os
import sqlite3
import sys

W = os.environ.get("WORK", "/work")
os.makedirs(W, exist_ok=True)
DB = f"{W}/t.db"
for suffix in ("", "-journal", "-wal", "-shm", ".lock"):
    p = DB + suffix
    if os.path.isdir(p):
        os.rmdir(p)
    elif os.path.exists(p):
        os.remove(p)


def case(name, fn):
    try:
        print(name, "->", fn())
    except Exception as e:  # noqa: BLE001
        print(name, "!!", type(e).__name__, str(e)[:120])


def listing():
    return sorted(n for n in os.listdir(W) if n.startswith("t.db"))


print("sqlite", sqlite3.sqlite_version_info >= (3, 53), "module", sys.version_info[:2])
mem = sqlite3.connect(":memory:")
case("memory create", lambda: mem.execute("create table t(a integer primary key, b text, c real)").rowcount)
case("memory executemany", lambda: mem.executemany("insert into t(b, c) values (?, ?)",
                                                   [(f"r{i}", i / 7) for i in range(1000)]).rowcount)
case("memory query", lambda: mem.execute("select count(*), sum(c), max(b) from t").fetchone())
case("json", lambda: mem.execute("select json_extract('{\"a\":[1,2,3]}', '$.a[2]')").fetchone())
case("math", lambda: mem.execute("select round(sqrt(2), 6), round(ln(10), 6)").fetchone())
case("window", lambda: mem.execute(
    "select b, sum(a) over (order by a rows 2 preceding) from t order by a limit 3").fetchall())
case("fts5", lambda: (mem.execute("create virtual table f using fts5(x)"),
                      mem.execute("insert into f values ('hello wasi world')"),
                      mem.execute("select * from f where f match 'wasi'").fetchall())[-1])
case("rtree", lambda: (mem.execute("create virtual table r using rtree(id, x0, x1)"),
                       mem.execute("insert into r values (1, 0, 5)"),
                       mem.execute("select id from r where x0 <= 3 and x1 >= 3").fetchall())[-1])
case("create_function", lambda: (mem.create_function("dbl", 1, lambda x: 2 * x, deterministic=True),
                                 mem.execute("select dbl(21)").fetchone())[-1])


class Agg:
    def __init__(self):
        self.n = 0

    def step(self, v):
        self.n += v

    def finalize(self):
        return self.n


case("create_aggregate", lambda: (mem.create_aggregate("tot", 1, Agg),
                                  mem.execute("select tot(a) from t").fetchone())[-1])
case("collation", lambda: (mem.create_collation("rev", lambda a, b: (a < b) - (a > b)),
                           mem.execute("select b from t order by b collate rev limit 2").fetchall())[-1])
case("serialize", lambda: len(mem.serialize()))
case("deserialize", lambda: (lambda c: (c.deserialize(mem.serialize()),
                                        c.execute("select count(*) from t").fetchone())[-1])(sqlite3.connect(":memory:")))
case("blobopen", lambda: (mem.execute("create table bl(x blob)"),
                          mem.execute("insert into bl values (zeroblob(16))"),
                          mem.commit(),
                          len(mem.blobopen("bl", "x", 1).read()))[-1])
case("iterdump", lambda: sum(1 for _ in mem.iterdump()))
case("load_extension", lambda: hasattr(mem, "enable_load_extension"))
case("compile_options", lambda: [o for o in (r[0] for r in mem.execute("pragma compile_options"))
                                 if o.startswith(("THREADSAFE", "TEMP_STORE", "OMIT", "MAX_MMAP", "ENABLE_FTS5"))])
case("temp_store default", lambda: mem.execute("pragma temp_store").fetchone())

# On a file in the root.
con = sqlite3.connect(DB)
case("file create", lambda: (con.execute("create table t(a integer primary key, b text)"), con.commit(), listing())[-1])
case("file executemany", lambda: (con.executemany("insert into t(b) values (?)", [(f"v{i}",) for i in range(5000)]),
                                  con.commit(), con.execute("select count(*) from t").fetchone())[-1])
case("journal_mode", lambda: con.execute("pragma journal_mode").fetchone())
case("locking_mode", lambda: con.execute("pragma locking_mode").fetchone())
case("open transaction files", lambda: (con.execute("insert into t(b) values ('x')"), listing())[-1])
case("rollback", lambda: (con.rollback(), con.execute("select count(*) from t").fetchone())[-1])
case("with commit", lambda: ((lambda: [con.execute("insert into t(b) values ('y')") for _ in range(1)])(),
                             con.commit(), con.execute("select count(*) from t").fetchone())[-1])

con2 = sqlite3.connect(DB, timeout=0)
case("second reads", lambda: con2.execute("select count(*) from t").fetchone())
case("first writes, second reads", lambda: (con.execute("insert into t(b) values ('z')"),
                                            con2.execute("select count(*) from t").fetchone())[-1])
case("second writes while first holds", lambda: con2.execute("insert into t(b) values ('w')").rowcount)
case("first commits", lambda: (con.commit(), listing())[-1])
case("second writes after", lambda: (con2.execute("insert into t(b) values ('w')"), con2.commit(),
                                     con.execute("select count(*) from t").fetchone())[-1])
case("uri read-only", lambda: sqlite3.connect(f"file:{DB}?mode=ro", uri=True).execute("select count(*) from t").fetchone())
case("uri ro write", lambda: sqlite3.connect(f"file:{DB}?mode=ro", uri=True).execute("insert into t(b) values (1)"))
case("big sort (temp)", lambda: con.execute(
    "select count(*) from (select b, randomblob(200) r from t, (select 1 union all select 2) order by r)").fetchone())
case("temp table", lambda: (con.execute("create temp table tt as select * from t"),
                            con.execute("select count(*) from tt").fetchone(), listing())[1:])
case("vacuum", lambda: (con.execute("vacuum"), listing())[-1])
case("backup", lambda: (lambda d: (con.backup(d), d.execute("select count(*) from t").fetchone())[-1])(sqlite3.connect(":memory:")))
case("backup to file", lambda: (lambda d: (con.backup(d), d.close(), os.path.getsize(f"{W}/t2.db") > 0)[-1])(sqlite3.connect(f"{W}/t2.db")))
for mode in ("wal", "truncate", "persist", "memory", "off", "delete"):
    case(f"journal_mode={mode}", lambda m=mode: (con.execute(f"pragma journal_mode={m}").fetchone(),
                                                  con.execute("insert into t(b) values ('j')"), con.commit(),
                                                  listing())[::3])
case("locking_mode=exclusive then wal", lambda: (con.execute("pragma locking_mode=exclusive").fetchone(),
                                                 con.execute("pragma journal_mode=wal").fetchone(),
                                                 con.execute("insert into t(b) values ('e')").rowcount, con.commit(),
                                                 listing(), con.execute("select count(*) from t").fetchone(),
                                                 con.execute("pragma journal_mode=delete").fetchone()))
con2.close()
con.close()
case("after close", listing)

# A clean unix-dotfile lock: is a lock directory present while a write transaction is open?
c3 = sqlite3.connect(DB, isolation_level=None)
case("begin immediate", lambda: (c3.execute("begin immediate"), listing())[-1])
case("commit", lambda: (c3.execute("commit"), listing())[-1])
c3.close()


def pandas_case():
    import pandas as pd

    df = pd.DataFrame({"k": ["a", "b", "a", "c"], "v": [1.5, 2.0, 3.25, None],
                       "d": pd.to_datetime(["2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01"])})
    c = sqlite3.connect(f"{W}/p.db")
    n = df.to_sql("df", c, index=False, if_exists="replace")
    back = pd.read_sql("select k, sum(v) as s, count(*) as n from df group by k order by k", c)
    whole = pd.read_sql_query("select * from df", c, parse_dates=["d"])
    out = (n, back.to_dict("list"), whole.dtypes.astype(str).to_dict(), whole.equals(df))
    c.close()
    return out


case("pandas to_sql/read_sql", pandas_case)


def vfs_case(vfs):
    c = sqlite3.connect(f"file:{W}/v-{vfs}.db?vfs={vfs}", uri=True, timeout=0)
    c.execute("create table if not exists t(a)")
    c.execute("insert into t values (1)")
    files = sorted(n for n in os.listdir(W) if n.startswith(f"v-{vfs}"))
    c.commit()
    return files, c.execute("select count(*) from t").fetchone()


for vfs in ("unix-none", "unix-dotfile", "unix", "unix-excl"):
    case(f"vfs={vfs}", lambda v=vfs: vfs_case(v))
print("done")
