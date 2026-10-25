"""Scan binary files for embedded build-host paths and secret-shaped strings."""
import sys, re
pats = {
 'users_home': rb'/Users/[A-Za-z0-9._-]+',
 'home_runner': rb'/home/[A-Za-z0-9._-]+',
 'private_tmp': rb'/private/(?:tmp|var)/[^\x00\s"]{0,60}',
 'var_folders': rb'/var/folders/[^\x00\s"]{0,60}',
 'build_dir': rb'/build/(?:src|cpython|wasi|host|stage|work)[^\x00\s"]{0,60}',
 'gh_workspace': rb'/__w/|/github/workspace|/runner/work',
 'c_users': rb'[Cc]:\\\\Users\\\\',
 'owner': rb'claygendron|Gendron',
 'pem': rb'-----BEGIN [A-Z ]*PRIVATE KEY-----',
 'ghp': rb'gh[pousr]_[A-Za-z0-9]{30,}',
 'aws': rb'AKIA[0-9A-Z]{16}',
 'pypi': rb'pypi-AgE[A-Za-z0-9_-]{20,}',
 'slack': rb'xox[abpr]-[A-Za-z0-9-]{10,}',
 'bearer': rb'Bearer [A-Za-z0-9._-]{20,}',
}
for path in sys.argv[1:]:
    b = open(path, 'rb').read()
    for k, p in pats.items():
        hits = {}
        for m in re.finditer(p, b):
            hits[m.group(0)[:80]] = hits.get(m.group(0)[:80], 0) + 1
        top = sorted(hits.items(), key=lambda x: -x[1])[:8]
        print(f'{path.rsplit("/",1)[-1]} {k}: distinct={len(hits)} total={sum(hits.values())} sample={top}')
