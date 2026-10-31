"""The fixed vocabulary of needs.

A check that cannot run calls `need(name)`. The call skips only when the need's predicate is
false, with the reason `needs: <name>`; the plugin re-evaluates the predicate and turns a skip
that names a met need, or no known need, into a failure. Each need names the document that
provides it, so the scoreboard can say what to do next.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass

import pytest

from harness import paths, pins

PREFIX = "needs: "


@dataclass(frozen=True)
class Need:
    name: str
    met: Callable[[], bool]
    provided_by: str


def _artifact_file(name: str) -> Callable[[], bool]:
    def met() -> bool:
        d = paths.artifact_dir()
        return d is not None and (d / name).is_file()

    return met


def _wasmtime() -> bool:
    try:
        import wasmtime  # noqa: F401
    except ImportError:
        return False
    return True


def _runner() -> bool:
    import wasi_python

    return callable(getattr(wasi_python, "run", None))


def _wheel() -> bool:
    return any(paths.DIST.glob("wasi_python-*.whl"))


def _three_systems() -> bool:
    from harness import history

    d = paths.artifact_dir()
    wasm = d / "python.wasm" if d else None
    if wasm is None or not wasm.is_file():
        return False
    return history.systems_that_passed(paths.PROGRESS, paths.sha256_file(wasm)) >= {
        "linux",
        "darwin",
        "win32",
    }


def _oracle() -> bool:
    from harness import jobs

    return jobs.oracle_available()


def _reference_build() -> bool:
    return (paths.REFERENCE_BUILD / "python.wasm").is_file()


def _prior_art() -> bool:
    return any(p.is_dir() for p in paths.PRIOR_ART.iterdir()) if paths.PRIOR_ART.is_dir() else False


def _git() -> bool:
    try:
        r = subprocess.run(
            ["git", "-C", str(paths.REPO), "rev-parse", "HEAD"], capture_output=True, check=False
        )
    except OSError:
        return False
    return r.returncode == 0


def _git_history() -> bool:
    """The whole history is here: a shallow clone's oldest commit has no parent to compare."""
    return (paths.git("rev-parse", "--is-shallow-repository") or "").strip() == "false"


def _upstream_kit() -> bool:
    from harness import upstream

    return upstream.kit_met()


def _compile_records() -> bool:
    """A build left its meson records under build/: the compile-flag check
    reads them, and the generated Makefiles and step 60's command files beside them."""
    from harness import scan

    return any((paths.BUILD / n / "compile_commands.json").is_file() for n in scan.MESON_BUILDS)


def _descriptor_limit() -> bool:
    """The host can lower a process's descriptor limit (RLIMIT_NOFILE): POSIX, not Windows. The
    first Windows run found the one check that needs it skipping without a need."""
    import importlib.util

    return importlib.util.find_spec("resource") is not None


def _read_only_files() -> bool:
    """Read-only content refuses a guest's unlink: on POSIX the host's folder without write
    permission does; on Windows the read-only attribute does not, and the guest deletes the file
    itself (seen in a dry run, 39358820218, on wasmtime 49)."""
    import os

    return os.name != "nt"


def _source_tree(component: str) -> Callable[[], bool]:
    def met() -> bool:
        from harness import pins

        return pins.source_pair(component) is not None

    return met


SPEC_001 = "context/specifications/001-the-neutral-host-door-and-the-runner.md"
SPEC_003 = "context/specifications/003-the-pinned-build-end-to-end.md"
REPRO_MEMO = "context/research/2026-10-16-reproducible-builds-on-linux.md"
SPEC_002 = "context/specifications/002-the-progress-harness.md"
SPEC_004 = "context/specifications/004-alpha-releases.md"  # the release workflow builds both
SPEC_050 = "context/specifications/050-numpy-and-pandas-own-tests-under-the-runtime.md"
SPEC_059 = "context/specifications/059-the-x86-64-rebuild-runs-natively.md"
SPEC_071 = "context/specifications/071-deep-recursion-raises-recursionerror.md"
SPEC_032 = "context/specifications/032-a-filesystem-provider.md"
SPEC_094 = "context/specifications/094-the-removal-rows-name-their-windows-need.md"

SOURCE_COMPONENTS = (
    "cpython",
    "numpy",
    "pandas",
    "zlib",
    "bzip2",
    "xz",
    "sqlite",
    "zstd",
    "regex",
    "freetype",
    "harfbuzz",
    "sheenbidi",
    "libraqm",
    "qhull",
    "libjpeg-turbo",
    "pillow",
    "kiwisolver",
    "matplotlib",
    "contourpy",
    "libxml2",
    "libxslt",
    "lxml",
    "pyyaml",
    "markupsafe",
    "networkx",
    "openblas",
    "scipy",
    "scikit_learn",
    "seaborn",
    "statsmodels",
    "python-docx",
    "python-pptx",
    "pdfminer-six",
    "xarray",
)

# The test sources: every other pinned source the judge stages but never builds (the pure-Python
# packages' tests), each unpacked by tests/upstream/fetch.py.
TEST_SOURCES = tuple(c for c in pins.SOURCE_PATTERNS if c not in SOURCE_COMPONENTS)
FETCH_TREES = "tests/upstream/fetch.py"

VOCABULARY: dict[str, Need] = {
    n.name: n
    for n in [
        Need("artifact dir", lambda: paths.artifact_dir() is not None, SPEC_003),
        Need("plain binary", _artifact_file("python.wasm"), SPEC_003),
        Need("snapshot binary", _artifact_file("python-snapshot.wasm"), SPEC_003),
        Need("stdlib zip", _artifact_file("python-stdlib.zip"), SPEC_003),
        Need("manifest", _artifact_file("MANIFEST"), SPEC_003),
        Need("wasmtime-py", _wasmtime, SPEC_002),
        Need("runner", _runner, SPEC_001),
        Need("wheel", _wheel, SPEC_004),
        Need("three systems", _three_systems, SPEC_004),
        Need("oracle", _oracle, SPEC_002),
        Need("reference build", _reference_build, SPEC_002),
        Need("prior-art clones", _prior_art, "context/prior_art/README.md"),
        Need("git", _git, "-"),
        Need("git history", _git_history, "-"),
        Need("upstream kit", _upstream_kit, SPEC_050),  # tests/upstream/fetch.py fetches it
        Need("compile records", _compile_records, SPEC_059),
        Need("wasmtime cli", lambda: paths.wasmtime_cli() is not None, SPEC_071),
        Need("descriptor limit", _descriptor_limit, SPEC_032),  # RLIMIT_NOFILE
        Need("read-only files", _read_only_files, SPEC_094),  # not on Windows
        *[Need(f"source tree {c}", _source_tree(c), REPRO_MEMO) for c in SOURCE_COMPONENTS],
        *[Need(f"source tree {c}", _source_tree(c), FETCH_TREES) for c in TEST_SOURCES],
    ]
}


def need(*names: str) -> None:
    """Skip the calling check unless every named need is met; report the first unmet one."""
    for name in names:
        n = VOCABULARY[name]  # a KeyError here is a harness bug, and fails loudly
        if not n.met():
            pytest.skip(PREFIX + name)


def parse_reason(reason: str) -> str | None:
    """The need named by a skip reason, or None when the reason names no need."""
    text = reason.strip()
    if text.startswith("Skipped: "):
        text = text[len("Skipped: ") :]
    if not text.startswith(PREFIX):
        return None
    return text[len(PREFIX) :].strip()
