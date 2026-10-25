# Trusted driver: plant start-up and import hooks in a reused root under scratch, then run
# programs that import modules not pre-imported; report which planted files ran.
import json, os, pathlib, sys, zipfile, io
import wasi_python
scratch = pathlib.Path(__file__).resolve().parent.parent
root = scratch / 'root-plant'
root.mkdir(exist_ok=True)
def plant(rel, tag):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"open('/RAN_{tag}', 'w').write('x')\n")
names = {
 'sitecustomize.py': 'sitecustomize', 'usercustomize.py': 'usercustomize',
 'tempfile.py': 'cwd_tempfile', 'reportlab_mods.py': 'cwd_reportlab_mods',
 'reportlab_settings.py': 'cwd_reportlab_settings', 'helper.py': 'script_dir_helper',
 '.reportlab_mods': 'home_reportlab_mods', '.reportlab_settings': 'home_reportlab_settings',
 'lib/python3.15/site-packages/sitecustomize.py': 'site_packages_sitecustomize',
 'lib/python3.15/tempfile.py': 'lib_tempfile', 'lib/python315.zip': None,
 'usr/local/lib/python3.15/tempfile.py': 'usr_lib_tempfile',
 'usr/local/lib/python3.15/site-packages/sitecustomize.py': 'usr_site_sitecustomize',
 'usr/lib/python3.15/tempfile.py': 'usr_lib2_tempfile',
 '.local/lib/python3.15/site-packages/usercustomize.py': 'user_site',
 'reportlab/local_rl_mods.py': 'pkg_local_rl_mods',
 'matplotlib/__init__.py': 'cwd_matplotlib',
}
for rel, tag in names.items():
    if tag: plant(rel, tag)
(root / 'x.pth').write_text("import os; open('/RAN_pth', 'w').write('x')\n")
(root / 'pyvenv.cfg').write_text("home = /\ninclude-system-site-packages = true\n")
(root / '.pythonrc.py').write_text("open('/RAN_pythonrc', 'w').write('x')\n")
(root / 'script.py').write_text("try:\n    import helper\nexcept ImportError as e:\n    print('helper:', e)\nimport sys; print(sys.path)\n")
probe = ("import sys, os\n"
         "import tempfile, reportlab, reportlab.rl_config, matplotlib, sqlite3, pdb, sympy\n"
         "print(tempfile.__file__, reportlab.__file__, matplotlib.__file__)\n"
         "print(sorted(n for n in os.listdir('/') if n.startswith('RAN_')))\n")
out = {}
for snap in (True, False):
    for f in root.glob('RAN_*'): f.unlink()
    c = wasi_python.run(['-c', probe], root=root, snapshot=snap, env={'HOME': '/'}, deadline_s=240)
    out[f'-c snapshot={snap}'] = {'exit': c.exit_code, 'stdout': c.stdout.decode(), 'stderr': c.stderr.decode()[-1500:], 'ran': sorted(p.name for p in root.glob('RAN_*'))}
    for f in root.glob('RAN_*'): f.unlink()
    c = wasi_python.run(['/script.py'], root=root, snapshot=snap, env={'HOME': '/'})
    out[f'script snapshot={snap}'] = {'exit': c.exit_code, 'stdout': c.stdout.decode(), 'stderr': c.stderr.decode()[-1500:], 'ran': sorted(p.name for p in root.glob('RAN_*'))}
    for f in root.glob('RAN_*'): f.unlink()
    c = wasi_python.run(['-m', 'helper'], root=root, snapshot=snap, env={'HOME': '/'})
    out[f'-m helper snapshot={snap}'] = {'exit': c.exit_code, 'stdout': c.stdout.decode(), 'stderr': c.stderr.decode()[-600:], 'ran': sorted(p.name for p in root.glob('RAN_*'))}
print(json.dumps(out, indent=1))
