"""Write the survey's job list (one guest session per line, tab-separated: family, label, fuel,
pytest args...) and run it in order, one session at a time, skipping labels already done.

    uv run python build/095/survey/plan.py write
    uv run python build/095/survey/plan.py run
"""

import json
import subprocess
import sys
from pathlib import Path

W = Path.cwd()
SURVEY = W / "build/095/survey"
SD = Path(
    "/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/"
    "6c490d24-fe1d-441f-9d11-d529e2f0c242/scratchpad/sdists"
)
TREES = {"scipy": SD / "scipy/scipy-1.18.1", "scikit-learn": SD / "sklearn/scikit_learn-1.9.1",
         "statsmodels": SD / "sm/statsmodels-0.15.0"}
PKG = {"scipy": "scipy", "scikit-learn": "sklearn", "statsmodels": "statsmodels"}

RV = [3, 20, 21, 29, 41, 53, 55, 56, 57, 58, 60, 61, 62, 83, 89, 90, 93, 100, 114]
K_CONT = "TestMakeDistribution and (" + " or ".join(
    f"test_rv_generic[{i}-distdata{i}]" for i in RV) + ")"
K_TANH = "TestTanhSinh and (" + " or ".join(
    f"test_accuracy[numpy-case{c}-{r}]" for c in (68, 100) for r in ("0.5", "ref1")) + ")"
K_AXIS = "test_axis_nan_policy_full or (test_axis_nan_policy_fast and kruskal)"
K_ALL = f"({K_CONT}) or ({K_TANH}) or ({K_AXIS})"
KW_FILES = ["scipy/stats/tests/test_axis_nan_policy.py", "scipy/stats/tests/test_continuous.py",
            "scipy/integrate/tests/test_tanhsinh.py"]


def folders(fam: str) -> list[str]:
    tree = TREES[fam]
    out = []
    for p in sorted((tree / PKG[fam]).rglob("tests")):
        rel = p.relative_to(tree)
        if p.is_dir() and "tests" not in rel.parts[:-1] and rel.as_posix() != "scipy/odr/tests":
            out.append(rel.as_posix())
    return out


def label(prefix: str, folder: str) -> str:
    return prefix + "-" + folder.split("/", 1)[1].removesuffix("/tests").replace("/", ".")


def write() -> None:
    jobs = []
    for f in folders("scipy"):
        jobs.append(["scipy", label("sci-n", f), "3e12", "-mnot slow and not xslow",
                     f"-knot ({K_ALL})", f])
    for f in folders("scikit-learn"):
        jobs.append(["scikit-learn", label("skl-n", f), "8e12", f])
    for f in folders("statsmodels"):
        jobs.append(["statsmodels", label("sm-n", f), "4e12", f])
    for f in folders("scipy"):
        jobs.append(["scipy", label("sci-r", f), "6e12", "-mslow or xslow", f])
    jobs.append(["scipy", "sci-r-keywords", "6e12", "-mnot slow and not xslow",
                 f"-k{K_ALL}", *KW_FILES])
    # scipy.signal's normal tier ran out of its 3 T cap inside test_choose_conv_method, which
    # times both methods until a fixed time passes: run the rest without it, then it alone
    conv = "/upstream-scipy/tree/scipy/signal/tests/test_signaltools.py::test_choose_conv_method"
    jobs.append(["scipy", "sci-n-signal-2", "4e12", "-mnot slow and not xslow",
                 f"-knot ({K_ALL})", f"--deselect={conv}", "scipy/signal/tests"])
    jobs.append(["scipy", "sci-n-signal-3", "4e12", "-mnot slow and not xslow",
                 f"-knot ({K_ALL}) and not (test_choose_conv_method and not _2)",
                 "scipy/signal/tests"])
    jobs.append(["scipy", "sci-n-conv-method", "6e11", "-mnot slow and not xslow",
                 "-ktest_choose_conv_method and not _2",
                 "scipy/signal/tests/test_signaltools.py"])
    (SURVEY / "jobs.tsv").write_text("\n".join("\t".join(j) for j in jobs) + "\n")
    print(len(jobs), "jobs")


def run() -> None:
    for line in (SURVEY / "jobs.tsv").read_text().splitlines():
        fam, lab, fuel, *args = line.split("\t")
        args = ["--continue-on-collection-errors", *args]
        if (SURVEY / "out" / lab / "result.json").exists():
            continue
        log = W / "build/095/logs" / f"{lab}.log"
        with log.open("w") as fh:
            subprocess.run(["uv", "run", "python", "build/095/survey/survey.py", fam, lab, fuel,
                            *args], stdout=fh, stderr=subprocess.STDOUT, check=False)
        res = SURVEY / "out" / lab / "result.json"
        if res.exists():
            r = json.loads(res.read_text())
            print(lab, r["fuel"], r["exit"], r["trapped"], json.dumps(r["counts"]), flush=True)
        else:
            print(lab, "NO RESULT", flush=True)


if __name__ == "__main__":
    {"write": write, "run": run}[sys.argv[1]]()
