"""The wheel's LICENSE as the release workflow writes it, from a small set."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from harness import paths


def _licences():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("licences", paths.REPO / "release/licences.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lic = _licences()


def _set(tmp_path: Path, files: dict[str, str]) -> Path:
    (tmp_path / "LICENSES").mkdir(parents=True)
    for name, text in files.items():
        (tmp_path / "LICENSES" / name).write_text(text)
    return tmp_path


def test_parts_are_by_name_txt_only_and_skip_dot_files(tmp_path: Path) -> None:
    d = _set(tmp_path, {"b.txt": "B", "a.txt": "A", "._a.txt": "x", "c.TXT": "C", "d.whl": "w"})
    assert [p.name for p in lic.parts(d)] == ["a.txt", "b.txt"]


def test_combined_is_the_licence_then_each_part(tmp_path: Path) -> None:
    d = _set(tmp_path, {"b.txt": "B licence\n", "a.txt": "A licence\n"})
    text = lic.combined("Apache\n", d)
    assert text.startswith("Apache" + lic.MARK)
    assert text.index("A licence") < text.index("B licence")
    assert lic.combined(text, d) == text  # appending twice gives the same file
    assert lic.own_licence(text) == "Apache\n"


def test_freetypes_credit_is_written_only_when_freetype_ships(tmp_path: Path) -> None:
    without = lic.combined("Apache\n", _set(tmp_path / "a", {"zlib.txt": "zlib\n"}))
    assert "FreeType Team" not in without
    with_ft = lic.combined("Apache\n", _set(tmp_path / "b", {"freetype.txt": "FTL\n"}))
    assert "based in part on the work of the FreeType Team" in with_ft
    assert "copyright © 2026 The FreeType Project (https://freetype.org)" in with_ft
