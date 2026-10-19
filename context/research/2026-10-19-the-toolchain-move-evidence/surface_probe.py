"""What a guest program can see, compared between two artifact sets (spec 086, criterion 4).

    uv run python surface_probe.py OLD_SET_DIR NEW_SET_DIR > surface_diff.txt

For each set and each binary (plain and snapshot), one guest program imports every module in
`sys.builtin_module_names` (the static build's compiled modules, packages' extensions included),
in sorted order, and writes `sorted(dir(module))` for each, or its import error, and
`sysconfig.get_config_vars()`. The host side runs it through `wasi-python run` with
`WASI_PYTHON_ARTIFACTS` pointing at the set, and prints every difference, one per line:
`<binary> <module> +name` / `-name`, and `<binary> sysconfig KEY: old -> new`. Counts, never time.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

GUEST = r"""
import importlib, json, sys, sysconfig
out = {"modules": {}, "sysconfig": {}}
for name in sorted(sys.builtin_module_names):
    try:
        m = importlib.import_module(name)
        out["modules"][name] = sorted(dir(m))
    except BaseException as e:
        out["modules"][name] = "import error: " + type(e).__name__
for k, v in sorted(sysconfig.get_config_vars().items()):
    out["sysconfig"][k] = v if isinstance(v, (str, int, float)) or v is None else repr(v)
sys.stdout.write(json.dumps(out, sort_keys=True))
"""


def surface(set_dir: str, snapshot: bool) -> dict:
    cmd = ["wasi-python", "run", "--output-bytes", str(64 * 2**20), "--fuel", str(10**12)]
    if not snapshot:
        cmd.append("--no-snapshot")
    cmd += ["--", "-c", GUEST]
    env = dict(os.environ, WASI_PYTHON_ARTIFACTS=set_dir)
    done = subprocess.run(cmd, capture_output=True, text=True, env=env, check=True)
    result = json.loads(done.stdout)
    if result["exit_code"] != 0:
        sys.exit(f"{set_dir} ({'snapshot' if snapshot else 'plain'}): {result['stderr'][-500:]}")
    return json.loads(result["stdout"])


def main() -> None:
    old_dir, new_dir = sys.argv[1:3]
    lines = []
    for snapshot in (False, True):
        which = "snapshot" if snapshot else "plain"
        old, new = surface(old_dir, snapshot), surface(new_dir, snapshot)
        for name in sorted(set(old["modules"]) | set(new["modules"])):
            a, b = old["modules"].get(name), new["modules"].get(name)
            if a == b:
                continue
            if not isinstance(a, list) or not isinstance(b, list):
                lines.append(f"{which} {name}: {a if not isinstance(a, list) else 'imports'} -> "
                             f"{b if not isinstance(b, list) else 'imports'}")
                continue
            lines += [f"{which} {name} +{n}" for n in sorted(set(b) - set(a))]
            lines += [f"{which} {name} -{n}" for n in sorted(set(a) - set(b))]
        for key in sorted(set(old["sysconfig"]) | set(new["sysconfig"])):
            a, b = old["sysconfig"].get(key), new["sysconfig"].get(key)
            if a != b:
                lines.append(f"{which} sysconfig {key}: {a!r} -> {b!r}")
        print(f"# {which}: {len(old['modules'])} modules in the old set, {len(new['modules'])} in "
              f"the new", file=sys.stderr)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
