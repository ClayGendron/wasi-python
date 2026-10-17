"""Golden job: sqlite3 on a file database, with pandas (spec 007, Decision 10).

Usage: sqlite.py <data dir> <out dir>. The database lives in the data directory, never in the
output directory: every file there is compared byte for byte, and a database's header records the
SQLite release that last wrote it. The oracle's SQLite is another release, built against another
math library, so the job prints only what both agree on: no version or error text, a total
ORDER BY on every query, floats rounded by the jobs' helper after they leave SQLite, no FTS5
scores, no JSON float text, no trigonometric or log10 results."""

import hashlib
import json
import os
import sqlite3
import sys

import pandas as pd


def f(x):
    return format(round(float(x), 9) + 0.0, ".9g")


data_dir, out_dir = sys.argv[1], sys.argv[2]
print(f"versions python={sys.version_info[0]}.{sys.version_info[1]} pandas={pd.__version__}")
db = os.path.join(data_dir, "jobs.db")
con = sqlite3.connect(db)

# Create, executemany, query.
con.execute("create table sales(id integer primary key, region text, month integer, sales real)")
with open(os.path.join(data_dir, "sales.csv")) as fh:
    rows = [line.strip().split(",") for line in fh.readlines()[1:]]
con.executemany(
    "insert into sales(region, month, sales) values (?, ?, ?)",
    [(r, int(m), float(s)) for r, m, s in rows],
)
con.commit()
q = "select region, count(*), sum(sales), avg(sales), max(sales) from sales group by region"
for region, n, total, mean, top in con.execute(q + " order by region"):
    print("group", region, n, f(total), f(mean), f(top))

# A transaction that commits, then one that fails and rolls back.
with con:
    con.execute("update sales set sales = sales + 1 where month = 1")
try:
    with con:
        con.execute("insert into sales(id, region, month, sales) values (1, 'east', 1, 0)")
except sqlite3.IntegrityError as e:
    print("rolled back", type(e).__name__)
print("after", con.execute("select count(*), sum(sales) from sales").fetchone()[0])
total = con.execute("select sum(sales) from sales").fetchone()[0]
print("total", f(total))

# JSON: integers and strings only.
doc = con.execute(
    "select json_group_array(json_object('region', region, 'n', n)) from "
    "(select region, count(*) as n from sales group by region order by region)"
).fetchone()[0]
print("json", json.loads(doc))
print(
    "json_extract",
    con.execute("""select json_extract('{"a": [1, 2, {"b": "c"}]}', '$.a[2].b')""").fetchone()[0],
)

# Window functions.
win = (
    "select region, month, row_number() over w, rank() over (order by month), "
    "sum(month) over w, lag(month) over w from sales "
    "window w as (partition by region order by month) order by region, month limit 6"
)
for row in con.execute(win):
    print("window", *row)
for row in con.execute(
    "select region, month, sales, sum(sales) over (partition by region order by month "
    "rows 2 preceding) from sales where month <= 3 order by region, month"
):
    print("moving", row[0], row[1], f(row[2]), f(row[3]))

# Math functions that agree across math libraries (sqrt, exp, ln, pow).
row = con.execute("select sqrt(2), exp(1), ln(10), pow(2, 0.5), sqrt(sum(sales)) from sales")
print("math", *(f(x) for x in row.fetchone()))

# FTS5: matches, never scores.
con.execute("create virtual table notes using fts5(body)")
con.executemany(
    "insert into notes(rowid, body) values (?, ?)",
    [
        (1, "north region grew in the spring"),
        (2, "south region was flat"),
        (3, "west region grew in the autumn and the spring"),
        (4, "nothing to report"),
    ],
)
for term in ("grew", "spring AND west", "region NOT grew", '"the spring"'):
    match = "select rowid from notes where notes match ? order by rowid"
    hits = [r[0] for r in con.execute(match, (term,))]
    print("fts5", repr(term), hits)
con.commit()

# A temporary table and a sort forced to temporary files, so the hosts' unlink of an open file runs.
con.execute("pragma temp_store=file")
con.execute("pragma cache_size=2")
con.execute("pragma temp.cache_size=2")
con.execute("create temp table spill(k integer, b blob)")
con.executemany(
    "insert into spill values (?, ?)",
    ((i * 7919 % 3001, hashlib.sha256(str(i).encode()).digest() * 32) for i in range(3000)),
)
keys = [r[0] for r in con.execute("select k from spill order by b, k")]
print("spill", len(keys), hashlib.sha256(json.dumps(keys).encode()).hexdigest()[:32])
print("spill sum", con.execute("select count(*), sum(length(b)) from spill").fetchone())
con.execute("drop table spill")

# pandas: to_sql, then read_sql.
df = pd.read_csv(os.path.join(data_dir, "sales.csv"))
print("to_sql", df.to_sql("frame", con, index=False))
back = pd.read_sql(
    "select region, count(*) as n, sum(sales) as total, max(month) as last from frame "
    "group by region order by region",
    con,
)
back["total"] = back["total"].map(f)
print(back.to_string())
whole = pd.read_sql("select * from frame order by region, month", con)
print("frame equal", whole.equals(df.sort_values(["region", "month"]).reset_index(drop=True)))
con.close()
print("files", sorted(n for n in os.listdir(data_dir) if n.startswith("jobs.db")))
