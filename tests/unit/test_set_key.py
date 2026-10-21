"""The set's key, the check that a set is this commit's, and the reuse rules on the workflows:
each row a mutant of what the rules check reads, red with its own reason."""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
from pathlib import Path

import pytest

from harness import paths, scan

ENV = {
    "SOURCE_DATE_EPOCH": "1767225600",
    "UV_VERSION": "0.9.22",
    "UV_LOCKED": "1",
    "UV_PYTHON": "3.14.2",
    "UV_BUILD_CONSTRAINT": "release/build-constraints.txt",
}
RELEASE = paths.REPO / ".github" / "workflows" / "release.yml"
SET_CACHE = paths.REPO / ".github" / "workflows" / "set-cache.yml"


def _module():
    spec = importlib.util.spec_from_file_location(
        "wasi_python_set_key_unit", paths.REPO / "release" / "set_key.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sk = _module()

# A repository with the shape the key reads: a step, a recipe, the pins, the gate and its import.
FAKE = {
    "scripts/build.sh": "echo build\n",
    "scripts/assemble_artifacts.py": (
        "import hashlib\nRESEARCH_PINS = {'research.zip'}\n"
        "def sha256(p):\n    return hashlib.sha256(p.read_bytes()).hexdigest()\n"
    ),
    "scripts/bench_x.py": "print(1)\n",
    "recipes/a.patch": "--- a\n",
    "downloads/SHA256SUMS": f"{'1' * 64}  zlib.tar.gz\n{'2' * 64}  research.zip\n",
    "release/set_key.py": "# stand-in\n",
    "release/build-constraints.txt": "hatchling==1\n",
    "tests/harness/__init__.py": "",
    "tests/harness/constructors.py": "from harness import wasm\nfrom . import helper\n",
    "tests/harness/wasm.py": "import json\n",
    "tests/harness/helper.py": "",
    "tests/harness/other.py": "",
    "tests/checks/test_x.py": "def test_x(): pass\n",
}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    for rel, text in FAKE.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
    git = ["git", "-C", str(tmp_path)]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    return tmp_path


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _set(repo: Path, folder: Path) -> Path:
    """A whole set of this repository's inputs: two files, MANIFEST as assemble makes it, sums."""
    folder.mkdir()
    (folder / "python.wasm").write_bytes(b"\0asm")
    (folder / "LICENSES").mkdir()
    (folder / "LICENSES" / "a.txt").write_text("licence\n")
    pins, recipes = sk.manifest_lines(repo)
    (folder / "MANIFEST").write_text("\n".join(["python 3.15.0", *pins, *recipes]) + "\n")
    files = sorted(p for p in folder.rglob("*") if p.is_file())
    (folder / "SHA256SUMS").write_text(
        "".join(f"{_sha(p.read_bytes())}  {p.relative_to(folder).as_posix()}\n" for p in files)
    )
    return folder


# ---------------------------------------------------------------------------------------------
# The key


def test_the_closure_is_the_trees_the_pins_and_the_gate_with_its_imports(repo) -> None:
    got = sk.closure(repo)
    assert "tests/harness/wasm.py" in got and "tests/harness/helper.py" in got
    assert "tests/harness/__init__.py" in got and "tests/harness/constructors.py" in got
    assert "tests/harness/other.py" not in got and "tests/checks/test_x.py" not in got
    assert "downloads/SHA256SUMS" in got and "scripts/bench_x.py" in got


def test_the_key_moves_with_an_input_and_not_with_anything_else(repo) -> None:
    first = sk.key(repo, ENV)
    assert first.startswith(sk.PREFIX) and first == sk.key(repo, ENV)
    (repo / "tests" / "checks" / "test_x.py").write_text("def test_y(): pass\n")
    (repo / "tests" / "harness" / "other.py").write_text("x = 1\n")
    assert sk.key(repo, ENV) == first
    for rel in ("recipes/a.patch", "tests/harness/wasm.py", "downloads/SHA256SUMS"):
        before = (repo / rel).read_text()
        (repo / rel).write_text(before + "\n")
        assert sk.key(repo, ENV) != first, rel
        (repo / rel).write_text(before)
    assert sk.key(repo, {**ENV, "UV_VERSION": "0.9.23"}) != first


def test_the_key_refuses_a_missing_variable(repo) -> None:
    with pytest.raises(SystemExit, match="UV_PYTHON"):
        sk.key(repo, {k: v for k, v in ENV.items() if k != "UV_PYTHON"})


def test_the_judges_walk_and_the_keys_walk_agree() -> None:
    """Two walks of the gate's imports, written apart: each checks the other."""
    assert set(sk.gate_files(paths.REPO)) == scan.local_import_files(
        paths.REPO, sk.GATE_ROOT, sk.GATES
    )


# ---------------------------------------------------------------------------------------------
# Check 4: the set is this commit's


def _verify(repo, folder, **kw):
    return sk.verify(folder, repo, environ=ENV, **kw)


CASES = {
    "a changed byte": (lambda r, s: (s / "python.wasm").write_bytes(b"\0asn"), "not the bytes"),
    "an extra file": (lambda r, s: (s / "extra").write_text("x"), "does not list"),
    "a missing file": (lambda r, s: (s / "LICENSES" / "a.txt").unlink(), "absent"),
    "a recipe changed after the build": (
        lambda r, s: (r / "recipes" / "a.patch").write_text("--- b\n"),
        "recipe lines",
    ),
    "a pin changed after the build": (
        lambda r, s: (r / "downloads" / "SHA256SUMS").write_text(f"{'3' * 64}  zlib.tar.gz\n"),
        "pin lines",
    ),
    "no MANIFEST": (lambda r, s: None, None),
}


@pytest.mark.parametrize("case", CASES)
def test_the_set_check_refuses_other_bytes(case, repo, tmp_path) -> None:
    folder = _set(repo, tmp_path / "set")
    assert _verify(repo, folder) == []
    assert _verify(repo, folder, want_key=sk.key(repo, ENV)) == []
    change, want = CASES[case]
    if want is None:  # MANIFEST removed and SHA256SUMS rewritten to match: still refused
        (folder / "MANIFEST").unlink()
        files = sorted(p for p in folder.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
        (folder / "SHA256SUMS").write_text(
            "".join(f"{_sha(p.read_bytes())}  {p.relative_to(folder).as_posix()}\n" for p in files)
        )
        want = "MANIFEST: absent"
    else:
        change(repo, folder)
    assert any(want in e for e in _verify(repo, folder)), _verify(repo, folder)


def test_the_set_check_refuses_another_key(repo, tmp_path) -> None:
    folder = _set(repo, tmp_path / "set")
    errors = _verify(repo, folder, want_key=sk.PREFIX + "0" * 64)
    assert len(errors) == 1 and errors[0].startswith("key: this checkout gives"), errors


# ---------------------------------------------------------------------------------------------
# The key rule's mutants: what the key must hold, the first layer of its proof


def _inputs(**changes) -> dict:
    tracked = paths.tracked_files(*sk.TREES)
    tests = paths.REPO / sk.GATE_ROOT
    out = {
        "closure": sk.closure(paths.REPO),
        "tracked": tracked,
        "texts": {r: (paths.REPO / r).read_text(errors="replace") for r in tracked},
        "release_text": RELEASE.read_text(),
        "key_env": sk.ENV,
        "gate_root": sk.GATE_ROOT,
        "gates": sk.GATES,
        "tests_names": sorted(p.name for p in tests.iterdir() if p.suffix == ".py" or p.is_dir()),
        "gate_imports": scan.local_import_files(paths.REPO, sk.GATE_ROOT, sk.GATES),
    }
    out.update(changes)
    return out


def test_the_real_inputs_pass() -> None:
    assert scan.set_key_errors(**_inputs()) == []


def _without(rel):
    return lambda i: {"closure": [c for c in i["closure"] if c != rel]}


def _text(rel, extra):
    return lambda i: {"texts": {**i["texts"], rel: i["texts"][rel] + extra}}


KEY_MUTANTS = {
    "the gate's import left out": (_without("tests/harness/wasm.py"), "K8: tests/harness/wasm.py"),
    "the pins left out": (_without("downloads/SHA256SUMS"), "K9:"),
    "a recipe left out": (_without("recipes/reactor_main.c"), "K1: recipes/reactor_main.c"),
    "a step names LICENSES/x": (
        _text("scripts/steps/90_artifacts.sh", 'cp "$HERE/LICENSES/x" "$OUT"\n'),
        "K2: scripts/steps/90_artifacts.sh names LICENSES/x",
    ),
    "a gate the key does not hold": (
        _text(
            "scripts/steps/constructors.sh",
            'PYTHONPATH="$HERE/tests" "$HOSTPY" -m harness.gate2 "$1"\n',
        ),
        "K3: scripts/steps/constructors.sh runs -m harness.gate2",
    ),
    "a top-level env the key does not hold": (
        lambda i: {"release_text": i["release_text"].replace("env:\n", "env:\n  FOO: 1\n", 1)},
        "K4: release.yml's top-level env",
    ),
    "a tests/sitecustomize.py": (
        lambda i: {"tests_names": [*i["tests_names"], "sitecustomize.py"]},
        "K7: tests/sitecustomize.py",
    ),
    "a tests/json.py": (lambda i: {"tests_names": [*i["tests_names"], "json.py"]}, "K7:"),
    "the build with an argument": (
        lambda i: {
            "release_text": i["release_text"].replace(
                "        run: scripts/build.sh\n", "        run: scripts/build.sh 60\n", 1
            )
        },
        "K6:",
    ),
}


@pytest.mark.parametrize("case", KEY_MUTANTS)
def test_each_key_mutant_is_named(case) -> None:
    change, want = KEY_MUTANTS[case]
    base = _inputs()
    errors = scan.set_key_errors(**{**base, **change(base)})
    assert any(e.startswith(want) for e in errors), errors


# ---------------------------------------------------------------------------------------------
# The reuse rules' mutants: where a set may be reused, how it is checked, and set-cache.yml


def _reuse(release: str | None = None, cache: str | None = None) -> list[str]:
    return scan.release_reuse_errors(
        release if release is not None else RELEASE.read_text(),
        cache if cache is not None else SET_CACHE.read_text(),
        sk.ENV,
    )


def test_the_real_workflows_pass() -> None:
    assert _reuse() == []


def _r(old, new, count=1):
    text = RELEASE.read_text()
    assert old in text, old
    return text.replace(old, new, count)


def _c(old, new):
    text = SET_CACHE.read_text()
    assert old in text, old
    return text.replace(old, new, 1)


REUSE_MUTANTS = {
    "!= 'false' in build's runs-on": (
        lambda: _reuse(
            _r("reuse == 'true' && 'ubuntu-24.04'", "reuse != 'false' && 'ubuntu-24.04'")
        ),
        "R3: build's runs-on",
    ),
    "a save before same-bytes": (
        lambda: _reuse(_r("    needs: [build, same-bytes]\n", "    needs: [build]\n")),
        "R5: save-set does not need build and same-bytes",
    ),
    "a restore without fail-on-cache-miss": (
        lambda: _reuse(_r("          fail-on-cache-miss: true\n", "")),
        "R3: build's restore",
    ),
    "set-source from the decision": (
        lambda: _reuse(
            _r(
                "steps.compile.outcome == 'success' && 'built'",
                "needs.inputs.outputs.reuse != 'true' && 'built'",
            )
        ),
        "R3: build's set-source",
    ),
    "the set check skipped on a source run": (
        lambda: _reuse(
            _r(
                "      - name: The set is this commit's\n        # Every run",
                "      - name: The set is this commit's\n"
                "        if: needs.inputs.outputs.reuse == 'true'\n        # Every run",
            )
        ),
        "R3: build's step \"The set is this commit's\" has if:",
    ),
    "build-shard downloads the build's assets": (
        lambda: _reuse(
            _r(
                "      - name: The build shard\n        # Only the checks that need the build tree",
                "      - uses: actions/download-artifact@x\n      - name: The build shard\n"
                "        # Only the checks that need the build tree",
            )
        ),
        "R4: build-shard downloads an artifact",
    ),
    "the gather without same-bytes": (
        lambda: _reuse(_r("build-shard, same-bytes, judge-macos", "build-shard, judge-macos")),
        "R6:",
    ),
    "a pull_request trigger on set-cache": (
        lambda: _reuse(
            cache=_c("  workflow_dispatch:\n", "  workflow_dispatch:\n  pull_request:\n")
        ),
        "C1:",
    ),
    "UV_VERSION in one workflow only": (
        lambda: _reuse(cache=_c('  UV_VERSION: "0.9.22"', '  UV_VERSION: "0.9.23"')),
        "C7:",
    ),
    "set-cache saves before the verify": (
        lambda: _reuse(
            cache=_c(
                "      - name: The set is this commit's\n",
                "      - uses: actions/cache/save@x\n      - name: The set is this commit's\n",
            )
        ),
        "C8:",
    ),
    "set-cache with write permissions": (
        lambda: _reuse(cache=_c("      contents: read\n", "      contents: write\n")),
        "C3:",
    ),
}


@pytest.mark.parametrize("case", REUSE_MUTANTS)
def test_each_reuse_mutant_is_named(case) -> None:
    run, want = REUSE_MUTANTS[case]
    errors = run()
    assert any(e.startswith(want) for e in errors), errors
