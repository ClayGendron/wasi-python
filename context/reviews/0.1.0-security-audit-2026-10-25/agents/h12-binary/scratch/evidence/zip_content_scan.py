"""Scan every decompressed stdlib-zip member (and the inner mpl-data.zip) for build-host paths
and secret-shaped strings. Data only."""
import sys, zipfile, re, io, collections
pats = {k: re.compile(v) for k, v in {
 'users_home': rb'/Users/[A-Za-z0-9._-]+', 'home_runner': rb'/home/runner|/home/[a-z][a-z0-9_-]{2,}/',
 'private_tmp': rb'/private/(?:tmp|var)/', 'var_folders': rb'/var/folders/', 'wasi_build': rb'/wasi-python-build/',
 'gh_workspace': rb'/__w/|/github/workspace|/runner/work', 'owner': rb'claygendron|Gendron',
 'pem_private': rb'-----BEGIN [A-Z ]*PRIVATE KEY-----', 'ghp': rb'\bgh[pousr]_[A-Za-z0-9]{36}\b',
 'aws': rb'\bAKIA[0-9A-Z]{16}\b', 'pypi': rb'pypi-AgE[A-Za-z0-9_-]{20,}', 'slack': rb'xox[abpr]-[0-9]{6,}-',
}.items()}
hits = collections.defaultdict(list)
def scan(z, prefix=''):
    for n in z.namelist():
        b = z.read(n)
        if n.endswith('.zip'):
            scan(zipfile.ZipFile(io.BytesIO(b)), prefix + n + '!')
        for k, p in pats.items():
            m = p.search(b)
            if m: hits[k].append((prefix + n, m.group(0)[:60]))
scan(zipfile.ZipFile(sys.argv[1]))
for k in pats: print(k, len(hits[k]), hits[k][:10])
