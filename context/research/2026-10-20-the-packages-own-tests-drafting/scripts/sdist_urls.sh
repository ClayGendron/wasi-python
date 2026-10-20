#!/bin/sh
# name version -> sdist url sha256 size
while read name ver; do
  curl -s "https://pypi.org/pypi/$name/$ver/json" | /usr/bin/python3 -I -c '
import json,sys
d=json.load(sys.stdin)
s=[u for u in d["urls"] if u["packagetype"]=="sdist"]
n=sys.argv[1]
if not s: print(n, "NO-SDIST")
for u in s: print(n, u["digests"]["sha256"], u["size"], u["url"])
' "$name-$ver"
done
