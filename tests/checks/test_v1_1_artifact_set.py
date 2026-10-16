"""v1.1: the artifact set is complete, sealed behind the wall, and says what built it."""

from __future__ import annotations

import zipfile

import pytest

from harness import artifacts as rules
from harness import needs, paths, scan

pytestmark = pytest.mark.goal("v1.1")

BINARY = pytest.mark.parametrize("which", ["plain", "snapshot"])
NEED_OF = {"plain": "plain binary", "snapshot": "snapshot binary"}


def _binary(artifacts, which):
    needs.need(NEED_OF[which])
    return artifacts.binary(which)


def test_artifact_set_is_complete(artifacts) -> None:
    errors = rules.complete_errors(artifacts.dir)
    assert not errors, scan.report(errors)


def test_sha256sums_match_the_files(artifacts) -> None:
    errors = rules.sums_errors(artifacts.dir)
    assert not errors, scan.report(errors)


def test_no_compiled_module_in_the_set(artifacts) -> None:
    errors = rules.cwasm_errors(artifacts.dir)
    assert not errors, scan.report(errors)


@BINARY
def test_binary_is_a_core_wasm_module(artifacts, which, metric) -> None:
    binary = _binary(artifacts, which)
    metric("bytes", binary.stat().st_size)
    errors = rules.is_core_module_errors(binary)
    assert not errors, scan.report(errors)


@BINARY
def test_imports_are_wasi_and_the_door_only(artifacts, which) -> None:
    errors = rules.module_errors(_binary(artifacts, which))
    assert not errors, scan.report(errors)


def test_plain_reactor_exports(artifacts) -> None:
    errors = rules.export_errors(_binary(artifacts, "plain"), rules.PLAIN_EXPORTS)
    assert not errors, scan.report(errors)


def test_snapshot_exports(artifacts) -> None:
    errors = rules.export_errors(
        _binary(artifacts, "snapshot"), rules.SNAPSHOT_EXPORTS, rules.SNAPSHOT_FORBIDDEN
    )
    assert not errors, scan.report(errors)


def test_manifest_is_well_formed(artifacts) -> None:
    needs.need("manifest")
    m = artifacts.manifest()
    assert not m.errors, scan.report(m.errors)


def test_manifest_pins_match_the_pin_list(artifacts) -> None:
    needs.need("manifest")
    errors = paths.manifest_pin_errors(artifacts.manifest(), paths.read_pin_list())
    assert not errors, scan.report(errors)


def test_manifest_recipes_match_the_tree(artifacts) -> None:
    needs.need("manifest")
    errors = paths.manifest_recipe_errors(artifacts.manifest(), paths.recipe_files())
    assert not errors, scan.report(errors)


def test_licence_notices_cover_every_component(artifacts) -> None:
    m = artifacts.manifest() if artifacts.path("MANIFEST").is_file() else None
    errors, content, presence = paths.licence_errors(artifacts.dir, m)
    scope = f"content checked: {', '.join(content) or 'none'}; presence only: {', '.join(presence)}"
    assert not errors, scan.report(errors, f"licence notices ({scope})")


def test_stdlib_zip_is_bytecode_only_and_deflated(artifacts, metric) -> None:
    needs.need("stdlib zip")
    z = artifacts.path("python-stdlib.zip")
    metric("bytes", z.stat().st_size)
    errors = rules.stdlib_zip_errors(z)
    assert not errors, scan.report(errors)


def test_artifacts_carry_no_build_path(artifacts) -> None:
    """No file in the set holds the checkout's path: it would publish the builder's home
    directory and tie every hash to where the repository was cloned."""
    needle = str(paths.REPO).encode()
    hits = [
        p.name for p in sorted(artifacts.dir.rglob("*")) if p.is_file() and needle in p.read_bytes()
    ]
    with zipfile.ZipFile(artifacts.path("python-stdlib.zip")) as z:  # members are deflated
        hits += [f"python-stdlib.zip:{n}" for n in z.namelist() if needle in z.read(n)]
    assert not hits, scan.report(hits, f"files holding {paths.REPO}")


def test_no_cpython_test_module_is_built_in(guest) -> None:
    """CPython's _test* and xx* modules are test scaffolding, not part of the product."""
    code = (
        "import sys\n"
        "print([m for m in sys.builtin_module_names if m.startswith(('_test', 'xx', '_xx'))])\n"
    )
    r = guest("snapshot", ["-c", code])
    assert (r.exit_code, r.text.strip()) == (0, "[]"), r.text or r.describe()


def test_wheel_carries_the_artifact_set(artifacts) -> None:
    needs.need("wheel")
    wheels = sorted(paths.DIST.glob("wasi_python-*.whl"))
    assert len(wheels) == 1, scan.report([w.name for w in wheels], "dist/ must hold one wheel")
    errors = rules.wheel_errors(wheels[0], artifacts.dir)
    assert not errors, scan.report(errors)
