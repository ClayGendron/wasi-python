"""The rustc wrapper of the Rust step: each compile's `-C metadata` becomes a hash of the compile
itself, the same on every build host and in every checkout, where cargo's mixes in the host's
`rustc -vV` through every build script and proc macro a crate depends on."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from harness import paths

sys.path.insert(0, str(paths.REPO / "scripts"))

import rust_ids  # noqa: E402


def _dep(folder: Path, crate: str, extra: str, kind: str, ident: str, suffix: str = ".rlib") -> str:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"lib{crate}{extra}.rustc-id").write_text(f"{kind} {ident}\n")
    return str(folder / f"lib{crate}{extra}{suffix}")


def _guest(
    root: Path,
    cargo_hash: str,
    macro_suffix: str,
    macro_id: str,
    feature: str = "std",
    core_id: str = "1111222233334444",
) -> list[str]:
    """A guest compile as cargo writes it, its cargo hashes and host-built paths given."""
    out = root / "build/rust/target/wasm32-wasip1/release/deps"
    core = _dep(out, "core", "-0f0f", "guest", core_id)
    macros = _dep(
        root / "build/rust/target/release/deps",
        "pyo3_macros",
        f"-{cargo_hash}",
        "host",
        macro_id,
        macro_suffix,
    )
    return [
        "--crate-name", "orjson", "--edition=2021",
        f"{root}/build/rust/vendor/orjson-3.13.0/src/lib.rs",
        "--error-format=json", "--json=diagnostic-rendered-ansi,artifacts,future-incompat",
        "--crate-type", "rlib", "--emit=dep-info,metadata,link", "-C", "opt-level=3",
        "--cfg", f'feature="{feature}"',
        "-C", f"metadata={cargo_hash}", "-C", f"extra-filename=-{cargo_hash}",
        "--out-dir", str(out), "--target", "wasm32-wasip1",
        "-L", f"dependency={out}",
        "--extern", f"noprelude:core={core}", "--extern", f"pyo3_macros={macros}",
        "-Cpanic=unwind", f"--remap-path-prefix={root}=/wasi-python-build",
    ]  # fmt: skip


def test_a_guest_crates_id_is_the_same_from_every_host_and_checkout(tmp_path) -> None:
    a, b = tmp_path / "a" / "wasi-python", tmp_path / "a-longer-folder" / "wasi-python"
    on_linux = _guest(a, "a1b2c3d4e5f60718", ".so", "becd127728ea10bd")
    on_macos = _guest(b, "9f8e7d6c5b4a3928", ".dylib", "13da8e258b334a3e")
    assert rust_ids.crate_id(str(a), on_linux) == rust_ids.crate_id(str(b), on_macos)


def test_a_feature_or_a_guest_dependency_changes_the_id(tmp_path) -> None:
    root = tmp_path / "wasi-python"
    base = rust_ids.crate_id(str(root), _guest(root, "a1", ".so", "e1"))
    assert rust_ids.crate_id(str(root), _guest(root, "a1", ".so", "e1", feature="alloc")) != base
    assert (
        rust_ids.crate_id(str(root), _guest(root, "a1", ".so", "e1", core_id="5555666677778888"))
        != base
    )


def test_the_metadata_is_replaced_and_cargos_file_names_kept(tmp_path) -> None:
    root = tmp_path / "wasi-python"
    args = _guest(root, "a1b2", ".so", "e1")
    out, record, text = rust_ids.rewritten(str(root), args)
    ident = rust_ids.crate_id(str(root), args)
    assert out[out.index("-C", out.index('feature="std"')) + 1] == f"metadata={ident}"
    assert "extra-filename=-a1b2" in out and "metadata=a1b2" not in out
    assert len(out) == len(args)
    assert record == root / "build/rust/target/wasm32-wasip1/release/deps/liborjson-a1b2.rustc-id"
    assert text == f"guest {ident}\n"


def test_a_host_compile_is_recorded_as_the_hosts(tmp_path) -> None:
    out = tmp_path / "release/deps"
    args = [
        "--crate-name",
        "syn",
        "src/lib.rs",
        "-C",
        "metadata=77",
        "-C",
        "extra-filename=-77",
        "--out-dir",
        str(out),
    ]
    _, record, text = rust_ids.rewritten(str(tmp_path), args)
    assert record == out / "libsyn-77.rustc-id"
    assert text.startswith("host ")


def test_cargos_queries_run_unchanged(tmp_path) -> None:
    for args in (
        ["-vV"],
        ["-", "--crate-name", "___", "--print=file-names", "--crate-type", "lib"],
    ):
        assert rust_ids.rewritten(str(tmp_path), args) == (args, None, "")


def test_a_dependency_compiled_around_the_wrapper_stops_the_compile(tmp_path) -> None:
    args = _guest(tmp_path, "a1", ".so", "e1")
    (tmp_path / "build/rust/target/wasm32-wasip1/release/deps/libcore-0f0f.rustc-id").unlink()
    with pytest.raises(rust_ids.IdError, match="no crate id beside"):
        rust_ids.crate_id(str(tmp_path), args)


def test_an_argument_file_stops_the_compile(tmp_path) -> None:
    with pytest.raises(rust_ids.IdError, match="argument file"):
        rust_ids.crate_id(str(tmp_path), ["--crate-name", "x", "@args.txt", "-C", "metadata=1"])
