"""Inventory the stdlib zip (and its inner mpl-data.zip) as data: names, types, duplicates,
traversal, start-up hooks, packaging tools, credential- or fixture-shaped files."""
import sys, zipfile, stat, io, re, collections, posixpath

def scan(zf, label):
    infos = zf.infolist()
    names = [i.filename for i in infos]
    out = collections.OrderedDict()
    out['entries'] = len(infos)
    out['dirs'] = sum(i.is_dir() for i in infos)
    kinds = collections.Counter(stat.S_IFMT(i.external_attr >> 16) for i in infos)
    out['unix_type_counts'] = {oct(k): v for k, v in kinds.items()}
    out['symlinks'] = [i.filename for i in infos if stat.S_ISLNK(i.external_attr >> 16)]
    out['create_system'] = dict(collections.Counter(i.create_system for i in infos))
    dup = [n for n, c in collections.Counter(names).items() if c > 1]
    out['duplicate_names'] = dup
    low = [n for n, c in collections.Counter(n.lower() for n in names).items() if c > 1]
    out['case_insensitive_duplicates'] = low[:20]; out['case_insensitive_duplicates_count'] = len(low)
    bad = [n for n in names if n.startswith('/') or '\\' in n or ':' in n or any(p in ('..', '.') for p in n.split('/')) or '\x00' in n or '//' in n]
    out['absolute_or_traversal_names'] = bad
    out['nonascii_names'] = [n for n in names if not n.isascii()][:20]
    top = collections.Counter(n.split('/')[0] for n in names)
    out['top_level_count'] = len(top)
    out['top_level_files'] = sorted(n for n in names if '/' not in n.rstrip('/'))
    hooks = [n for n in names if re.search(r'(^|/)(sitecustomize|usercustomize|site)\.py[c]?$', n) or n.endswith('.pth') or n.endswith('pyvenv.cfg') or posixpath.basename(n) in ('__main__.py',) and n.count('/') == 0]
    out['startup_hook_like'] = hooks
    out['pth_files'] = [n for n in names if n.endswith('.pth')]
    out['pip_ensurepip_setuptools'] = sorted({n.split('/')[0] for n in names if re.match(r'(pip|ensurepip|setuptools|_distutils_hack|distutils|wheel|venv)(/|\.py)', n)})
    out['ensurepip_wheels'] = [n for n in names if n.endswith('.whl')]
    cred = [n for n in names if re.search(r'(\.pem|\.key|\.p12|\.pfx|id_rsa|id_ed25519|\.env$|credentials|\.netrc|\.pypirc|secret|token|password|htpasswd|\.crt$|\.cer$)', n, re.I)]
    out['credential_shaped_names'] = cred
    out['test_dirs'] = sorted({ '/'.join(n.split('/')[:k+1]) for n in names for k, p in enumerate(n.split('/')[:-1]) if p in ('test', 'tests', 'testing', 'idle_test')})[:60]
    out['test_dirs_count'] = len({ '/'.join(n.split('/')[:k+1]) for n in names for k, p in enumerate(n.split('/')[:-1]) if p in ('test', 'tests', 'testing', 'idle_test')})
    out['reportlab'] = [n for n in names if 'reportlab' in n.lower()][:40]
    out['settings_like'] = [n for n in names if re.search(r'(local_settings|rl_settings|rl_local_settings|settings\.py$|reportlab_mods)', n)]
    out['native_like'] = [n for n in names if re.search(r'\.(so|dylib|dll|pyd|wasm|cwasm|exe)$', n)]
    exts = collections.Counter(posixpath.splitext(n)[1] for n in names if not n.endswith('/'))
    out['ext_counts'] = dict(exts.most_common(25))
    out['inner_zips'] = [n for n in names if n.endswith('.zip')]
    out['total_uncompressed'] = sum(i.file_size for i in infos)
    out['max_ratio'] = max(((i.file_size / i.compress_size) if i.compress_size else 0, i.filename) for i in infos)
    out['comment'] = zf.comment[:200].decode('latin-1')
    print(f'== {label}')
    for k, v in out.items(): print(f'{k}: {v}')
    return names

zpath = sys.argv[1]
with zipfile.ZipFile(zpath) as z:
    names = scan(z, zpath.rsplit('/', 1)[-1])
    for inner in [n for n in names if n.endswith('.zip')]:
        with zipfile.ZipFile(io.BytesIO(z.read(inner))) as iz:
            scan(iz, inner)
            # the runner's own guard, re-stated: what _member_parts would refuse
            bad = []
            for n in iz.namelist():
                parts = tuple(n.rstrip('/').split('/'))
                if not n or n.startswith('/') or '\\' in n or ':' in n or any(p in ('', '.', '..') for p in parts): bad.append(n)
            print('member_parts_refusals:', bad)
            win = [n for n in iz.namelist() if any(p != p.rstrip('. ') or p.split('.')[0].upper() in ('CON','PRN','AUX','NUL','COM1','LPT1') for p in n.rstrip('/').split('/'))]
            print('windows_awkward_names:', win)
