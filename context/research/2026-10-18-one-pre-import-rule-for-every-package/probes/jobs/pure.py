"""A pure-Python agent script: build records, round-trip them through json and csv, run a regex."""
import csv, io, json, re
rows = [{"id": i, "name": f"item-{i:04d}", "price": round(i * 1.37, 2), "tag": "ab"[i % 2]} for i in range(2000)]
text = json.dumps(rows)
back = json.loads(text)
buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=["id", "name", "price", "tag"]); w.writeheader(); w.writerows(back)
total = sum(float(r["price"]) for r in csv.DictReader(io.StringIO(buf.getvalue())))
hits = len(re.findall(r"item-0\d{2}[13579]\b", buf.getvalue()))
print(len(back), round(total, 2), hits)
