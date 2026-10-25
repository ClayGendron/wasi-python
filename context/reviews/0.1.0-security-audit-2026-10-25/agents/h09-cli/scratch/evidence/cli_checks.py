"""Bounded local checks of the wasi-python CLI: grant split, --env KEY, --root creation,
--stdin, JSON escaping, option splitting. Writes cli_checks.json beside this script.
Run inside the brief's wrapper (env -i, sandbox-exec deny network, ulimits)."""

import json
import os
import stat
import subprocess
import sys

SCRATCH = "context/reviews/0.1.0-security-audit-2026-10-25/agents/h09-cli/scratch"
WORK = os.path.join(SCRATCH, "work")
CLI = "./.venv/bin/wasi-python"
OUT = os.path.join(SCRATCH, "evidence", "cli_checks.json")

results = []


def run(name, args, env_extra=None, stdin=None):
    env = {k: os.environ[k] for k in ("PATH", "HOME", "TMPDIR", "WASI_PYTHON_CACHE")}
    if env_extra:
        env.update(env_extra)
    p = subprocess.run(
        [CLI, *args], env=env, input=stdin, capture_output=True, timeout=120, cwd=WORK
    )
    rec = {
        "case": name,
        "argv": args,
        "added_env_names": sorted((env_extra or {}).keys()),
        "rc": p.returncode,
        "stdout": p.stdout.decode("utf-8", "replace")[:3000],
        "stderr": p.stderr.decode("utf-8", "replace")[:1500],
    }
    results.append(rec)
    return rec


os.makedirs(WORK, exist_ok=True)

# A. --env KEY copies only the named key; the rest of this process's env stays out.
show_env = "import os,json;print(json.dumps(dict(sorted(os.environ.items()))))"
run(
    "env_key_copy",
    ["run", "--env", "DUMMY_SECRET", "--env", "OTHER=x", "--", "-c", show_env],
    {"DUMMY_SECRET": "dummy-value-123", "NOT_NAMED": "should-not-appear"},
)
run("env_no_env_flag", ["run", "--", "-c", show_env], {"NOT_NAMED": "should-not-appear"})
run("env_missing_key", ["run", "--env", "dummy-value-typed-as-name", "--", "-c", "pass"])
run("env_empty_key", ["run", "--env", "=v", "--", "-c", "pass"])

# B. Grant split at the first '='.
hostdir = os.path.join(WORK, "a=b")
os.makedirs(hostdir, exist_ok=True)
with open(os.path.join(hostdir, "f.txt"), "w") as f:
    f.write("hello\n")
prog_ro = (
    "import os\nprint(sorted(os.listdir('/data')))\n"
    "try:\n open('/data/w','w')\n print('WROTE')\nexcept OSError as e:\n print('refused', e.errno)\n"
)
run("grant_host_with_equals", ["run", "--grant", "/data=a=b", "--", "-c", prog_ro])
run("grant_no_equals", ["run", "--grant", "/data", "--", "-c", "pass"])
run("grant_empty_guest", ["run", "--grant", "=a=b", "--", "-c", "pass"])
run("grant_relative_guest", ["run", "--grant", "data=a=b", "--", "-c", "pass"])
run("grant_dotdot_guest", ["run", "--grant", "/data/..=a=b", "--", "-c", "pass"])
run("grant_runtime_guest", ["run", "--grant", "/usr/local/lib=a=b", "--", "-c", "pass"])
# A link in a folder this user can write is refused.
link = os.path.join(WORK, "link-to-ab")
if not os.path.lexists(link):
    os.symlink("a=b", link)
run("grant_through_user_link", ["run", "--grant", "/data=link-to-ab", "--", "-c", "pass"])

# C. --root made if missing: its mode, and a root through a link.
newroot = os.path.join(WORK, "newroot")
if os.path.exists(newroot):
    import shutil

    shutil.rmtree(newroot)
prog_root = "import os\nopen('/out.txt','w').write('x')\nprint(sorted(os.listdir('/')))"
rec = run("root_made_if_missing", ["run", "--root", "newroot", "--", "-c", prog_root])
try:
    st = os.stat(newroot)
    rec["made_root_mode"] = oct(stat.S_IMODE(st.st_mode))
    rec["made_root_uid_is_self"] = st.st_uid == os.getuid()
    rec["process_umask"] = oct(os.umask(0o022))
    os.umask(int(rec["process_umask"], 8))
    rec["made_root_tmp_mode"] = oct(stat.S_IMODE(os.stat(os.path.join(newroot, "tmp")).st_mode))
except OSError as e:
    rec["made_root_stat_error"] = str(e)
rlink = os.path.join(WORK, "rootlink")
if not os.path.lexists(rlink):
    os.symlink("newroot", rlink)
run("root_through_user_link", ["run", "--root", "rootlink", "--", "-c", "pass"])
run("root_twice", ["run", "--root", "newroot", "--root", "newroot", "--", "-c", "pass"])
run("root_and_private", ["run", "--root", "newroot", "--private-root", "--", "-c", "pass"])
# A pre-existing world-writable folder is accepted as the root (no ownership/mode check).
shared = os.path.join(WORK, "shared0777")
os.makedirs(shared, exist_ok=True)
os.chmod(shared, 0o777)
run("root_preexisting_0777", ["run", "--root", "shared0777", "--", "-c", "print('ran')"])

# D. JSON escaping of guest output: terminal escapes and non-UTF-8 bytes.
esc = (
    "import sys\nsys.stdout.write('\\x1b]0;TITLE\\x07\\x1b[31mred\\u2028\\n')\n"
    "sys.stderr.buffer.write(b'\\xff\\xfe')"
)
run("json_escaping", ["run", "--", "-c", esc])

# E. --stdin from a file and from this command's input.
with open(os.path.join(WORK, "in.txt"), "wb") as f:
    f.write(b"from-file\n")
rd = "import sys;print(repr(sys.stdin.buffer.read()))"
run("stdin_file", ["run", "--stdin", "in.txt", "--", "-c", rd])
run("stdin_dash", ["run", "--stdin", "-", "--", "-c", rd], stdin=b"from-pipe\n")
run("stdin_missing_file", ["run", "--stdin", "nope.txt", "--", "-c", rd])

# G. Option splitting: guest argv is never parsed as this command's options.
run("guest_argv_after_script_name", ["run", "-c", "print(1)", "--root", "/"])
run("split_env_consumes_dashdash", ["run", "--env", "--", "-c", "print(1)"])
run(
    "guest_gets_root_flag_after_dashdash",
    ["run", "--", "-c", "import sys;print(sys.argv)", "--root", "/"],
)

with open(OUT, "w") as f:
    json.dump(results, f, indent=1)
print("wrote", OUT, len(results))
sys.exit(0)
