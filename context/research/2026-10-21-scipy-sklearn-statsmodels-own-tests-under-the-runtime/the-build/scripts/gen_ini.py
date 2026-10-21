"""Write tests/upstream/{scipy,scikit-learn,statsmodels}.ini from the sdists' own settings."""

import tomllib
from pathlib import Path

W = Path("/Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06")
UP = W / "tests/upstream"

scipy = (W / "build/scipy-1.18.1/pytest.ini").read_text()
head = (
    "# scipy's own pytest.ini, as its sdist has it, with one line added under filterwarnings:\n"
    "# the driver imports hypothesis before pytest starts (to load the judge's profile), so pytest\n"
    "# warns that it cannot rewrite it, and scipy's `error` filter would end the session there.\n"
    "# The line names pytest's own message about the kit, not any warning of scipy's.\n"
)
extra = (
    "    ignore:Module already imported so cannot be rewritten:pytest.PytestAssertRewriteWarning\n"
)
assert scipy.count("    error\n") == 1
(UP / "scipy.ini").write_text(head + scipy.replace("    error\n", "    error\n" + extra, 1))

(UP / "scikit-learn.ini").write_text(
    """# scikit-learn's own pytest settings (its pyproject.toml), transcribed. Left out, each for its
# reason: testpaths (each group names its paths), --color=yes (no terminal), --import-mode
# (the driver passes it), faulthandler_timeout and faulthandler_exit_on_timeout (the driver turns
# faulthandler off, so --strict-config would refuse them), thread_unsafe_fixtures (a key of a
# plugin the kit does not carry). Registered here: no_check_spmatrix, a marker its tests use and
# the sdist registers nowhere (upstream runs without --strict-markers).
[pytest]
doctest_optionflags = NORMALIZE_WHITESPACE ELLIPSIS
addopts = --disable-pytest-warnings
markers =
    no_check_spmatrix: scikit-learn's marker for the tests --check-spmatrix skips
"""
)

opts = tomllib.loads((W / "build/statsmodels-0.15.0/pyproject.toml").read_text())
opts = opts["tool"]["pytest"]["ini_options"]
lines = [
    "# statsmodels' own pytest settings (its pyproject.toml), transcribed. Left out, each for its",
    "# reason: --durations and --junitxml (reports, not selection), junit_family (the same),",
    "# --randomly-dont-reset-seed (an option of a plugin neither the kit nor the tests need),",
    "# --strict (the driver passes --strict-markers, its current name). Registered here: two",
    "# markers its tests use and the sdist registers nowhere.",
    "[pytest]",
    f"minversion = {opts['minversion']}",
    "xfail_strict = true",
    f"empty_parameter_set_mark = {opts['empty_parameter_set_mark']}",
    "filterwarnings =",
]
lines += [f"    {w}" for w in opts["filterwarnings"]]
lines += ["markers ="] + [f"    {m}" for m in opts["markers"]]
lines += [
    "    thread_unsafe: pytest-run-parallel's marker",
    "    skip_randomstate_check: statsmodels' marker its conftest reads",
]
(UP / "statsmodels.ini").write_text("\n".join(lines) + "\n")
print("written")
