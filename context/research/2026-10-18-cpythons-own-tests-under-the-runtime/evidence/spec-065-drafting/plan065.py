"""Spec 065's drafting plan: CPython's modules in four groups, one per Linux upstream shard.

uv run python plan065.py <per-module-results.tsv> <out dir>

- left out: the 14 modules that fail to load (not selected) and test_traceback (a whole-module trap);
- cpython-fs: the file-system modules, run on Linux, macOS and Windows (decision 7);
- cpython-a, -b, -c: every other module, greedy largest first, each into the group whose shard
  (with its numpy and pandas groups, fuel from spec 063's memo) is lightest;
- order inside a group: sorted, test_monitoring last (decision 5); test_profiling not in its group.
Fuel per module is the per-module session's less the fixed start (1.14 G), as the research's
shards.py does; a group's session adds one start and an INFERRED composition effect.
"""
import csv
import sys
from pathlib import Path

START = 1.14
NOT_SELECTED = {
    "test_ctypes", "test_code", "test_genericalias",            # the ctypes stand-in
    "test_class", "test_with", "test_getpath",                  # CPython's C test modules
    "test_ensurepip", "test_venv", "test_sysconfig",            # not in the zip
    "test_ast",                                                 # the bytecode-only zip
    "test_time", "test_calendar", "test_strptime", "test_os.test_posix",  # sys.executable
}
WHOLE_TRAP = {"test_traceback"}
FS = [
    "test_os.test_os", "test_os.test_windows", "test_shutil", "test_pathlib", "test_tempfile",
    "test_glob", "test_posixpath", "test_genericpath", "test_stat", "test_filecmp",
    "test_fileinput", "test_zipfile", "test_zipfile64", "test_tarfile", "test_zipimport",
    "test_zipimport_support", "test_shelve", "test_dbm", "test_dbm_dumb", "test_dbm_gnu",
    "test_dbm_ndbm", "test_dbm_sqlite3", "test_sqlite3", "test_mailbox", "test_py_compile",
    "test_compileall", "test_importlib", "test_linecache", "test_gzip", "test_bz2", "test_lzma",
    "test_logging", "test_mmap", "test_unicode_file", "test_unicode_file_functions",
    "test_file_eintr", "test_fileutils", "test_netrc", "test_zipapp", "test_site", "test_pkgutil",
    "test_io.test_bufferedio", "test_io.test_file", "test_io.test_fileio", "test_io.test_general",
    "test_io.test_largefile", "test_io.test_memoryio", "test_io.test_signals",
    "test_io.test_textio", "test_io.test_univnewlines",
]
# spec 063's Linux upstream shards (fuel G, its memo section 2); cpython-fs goes with frame
SHARDS = {"upstream-frame": 338.1, "upstream-numpy-a": 333.4, "upstream-numpy-b": 273.3,
          "upstream-pandas-small": 214.3}


def main() -> None:
    rows = list(csv.DictReader(open(sys.argv[1]), delimiter="\t"))
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    cost = {r["module"]: max(float(r["fuel_G"]) - START, 0.0) for r in rows}
    passed = {r["module"]: int(r["passed"]) for r in rows}
    missing = [m for m in FS if m not in cost]
    assert not missing, missing
    groups = {"cpython-fs": list(FS), "cpython-a": [], "cpython-b": [], "cpython-c": []}
    home = {"cpython-fs": "upstream-frame", "cpython-a": "upstream-numpy-a",
            "cpython-b": "upstream-numpy-b", "cpython-c": "upstream-pandas-small"}
    load = {g: SHARDS[home[g]] + sum(cost[m] for m in ms) for g, ms in groups.items()}
    rest = [m for m in cost if m not in NOT_SELECTED | WHOLE_TRAP and m not in FS]
    rest.sort(key=lambda m: -cost[m])
    for m in rest:
        choices = [g for g in ("cpython-a", "cpython-b", "cpython-c")]
        if m == "test_profiling":
            choices = [g for g in choices if "test_monitoring" not in groups[g]]
        g = min(choices, key=lambda g: load[g])
        groups[g].append(m)
        load[g] += cost[m]
    total = 0.0
    for g, ms in groups.items():
        ms.sort()
        if "test_monitoring" in ms:
            ms.remove("test_monitoring")
            ms.append("test_monitoring")
        (out / f"{g}.txt").write_text("\n".join(ms) + "\n")
        f = sum(cost[m] for m in ms) + START
        total += f
        print(f"{g:11} {len(ms):3} modules {sum(passed[m] for m in ms):6} passes "
              f"{f:6.1f} G   shard {home[g]:22} {load[g] + START:6.1f} G with its groups")
    print(f"all         {sum(len(v) for v in groups.values())} modules, {total:.1f} G expected")
    (out / "not-selected.txt").write_text("\n".join(sorted(NOT_SELECTED)) + "\n")


if __name__ == "__main__":
    main()
