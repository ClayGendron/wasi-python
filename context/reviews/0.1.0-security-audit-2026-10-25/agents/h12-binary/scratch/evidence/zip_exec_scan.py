"""List zip members whose code objects name both a home/cwd/env path source and a way to
run code from a file (string constants and names in the .pyc). Data only; nothing is executed."""
import sys, zipfile, re
z = zipfile.ZipFile(sys.argv[1])
src = re.compile(rb'expanduser|getcwd|PYTHONSTARTUP|XDG_CONFIG_HOME|APPDATA|\.pythonrc|\brc\b')
run = re.compile(rb'spec_from_file_location|exec_module|run_path|load_source|SourceFileLoader|execfile|\bexec\b|_fake_import|rl_exec|import_module|sys\.path\.insert|path\.insert')
for n in z.namelist():
    if not n.endswith('.pyc'): continue
    b = z.read(n)
    s = set(m.group(0) for m in src.finditer(b)); r = set(m.group(0) for m in run.finditer(b))
    if s and r:
        print(n, sorted(x.decode() for x in s), sorted(x.decode() for x in r))
