"""release/version.py: versions, the changelog, the tag check and the assets."""

from __future__ import annotations

import importlib.util
import re
import sys
import tarfile
from pathlib import Path

import pytest

from harness import paths

_spec = importlib.util.spec_from_file_location(
    "release_version", paths.REPO / "release" / "version.py"
)
version = importlib.util.module_from_spec(_spec)
sys.modules["release_version"] = version  # dataclasses look their module up here
_spec.loader.exec_module(version)
V = version.Version.parse

PYPROJECT = (
    '[project]\nname = "wasi-python"\ndynamic = ["version"]\n\n'
    '[tool.hatch.version]\npath = "src/wasi_python/__init__.py"\n'
)
INIT = '"""x"""\n\n__version__ = "0.1.0a1"\n'
LOG = "# Changelog\n\n## 0.1.0a1 — unreleased\n\n- first\n"


@pytest.mark.parametrize("text", ["0.1.0a1", "0.1.0b2", "0.1.0rc1", "1.2.3", "0.1.0a10"])
def test_versions_round_trip(text) -> None:
    assert str(V(text)) == text


@pytest.mark.parametrize("text", ["0.1", "0.1.0a0", "0.1.0-a1", "v0.1.0a1", "0.1.0.dev1", "0.1.0a"])
def test_other_forms_are_refused(text) -> None:
    with pytest.raises(version.ReleaseError):
        V(text)


def test_order_is_pep_440s() -> None:
    order = ["0.0.0", "0.1.0a1", "0.1.0a2", "0.1.0a10", "0.1.0b1", "0.1.0rc1", "0.1.0", "0.2.0a1"]
    assert sorted(order, key=V) == order


def test_the_next_alpha() -> None:
    assert [
        str(V(v).next_alpha()) for v in ("0.0.0", "0.1.0a1", "0.1.0a9", "0.1.0", "0.1.0b2")
    ] == [
        "0.1.0a1",
        "0.1.0a2",
        "0.1.0a10",
        "0.2.0a1",
        "0.2.0a1",
    ]


def test_the_version_line_is_read_and_written() -> None:
    assert version.read_version(INIT) == "0.1.0a1"
    assert version.read_version(version.write_version(INIT, V("0.1.0a2"))) == "0.1.0a2"


def test_changelog_sections_are_added_dated_and_read() -> None:
    log = version.add_section(LOG, V("0.1.0a2"))
    assert list(version.sections(log)) == ["0.1.0a2", "0.1.0a1"]
    with pytest.raises(version.ReleaseError, match="already has a section"):
        version.add_section(log, V("0.1.0a2"))
    dated = version.date_section(log, V("0.1.0a1"), "2026-10-17")
    assert version.sections(dated)["0.1.0a1"] == "2026-10-17"
    assert version.notes(dated, "0.1.0a1") == "- first\n"


def test_check_passes_a_good_tree_and_names_each_fault() -> None:
    dated = LOG.replace("unreleased", "2026-10-17")
    assert version.check_errors(INIT, PYPROJECT, LOG) == []
    assert version.check_errors(INIT, PYPROJECT, dated, tag="v0.1.0a1") == []
    assert version.check_errors(INIT, PYPROJECT, dated, tag="v0.1.0a2") == [
        "the tag v0.1.0a2 is not v0.1.0a1, the version it points to"
    ]
    assert version.check_errors(INIT, PYPROJECT, LOG, tag="v0.1.0a1") == [
        "CHANGELOG.md's section for 0.1.0a1 is still unreleased"
    ]
    assert version.check_errors(INIT, PYPROJECT, "# Changelog\n") == [
        "CHANGELOG.md has no section for 0.1.0a1"
    ]
    static = PYPROJECT.replace('dynamic = ["version"]', 'version = "0.1.0a1"')
    assert version.check_errors(INIT, static, LOG) == [
        'pyproject.toml must declare dynamic = ["version"]',
        "pyproject.toml writes a static version; __init__.py is the only place",
    ]


def _sums(art: Path) -> None:
    import hashlib

    files = sorted(p for p in art.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (art / "SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(art).as_posix()}\n"
            for p in files
        )
    )


def test_assets_are_deterministic(tmp_path: Path) -> None:
    art = tmp_path / "artifacts"
    (art / "LICENSES").mkdir(parents=True)
    (art / "python.wasm").write_bytes(b"\0asm")
    (art / "LICENSES" / "cpython.txt").write_text("PSF")
    _sums(art)
    wheel = tmp_path / "wasi_python-0.1.0a1-py3-none-any.whl"
    wheel.write_bytes(b"PK")
    first = version.write_assets(art, wheel, tmp_path / "one", "0.1.0a1")
    second = version.write_assets(art, wheel, tmp_path / "two", "0.1.0a1")
    assert [p.read_bytes() for p in first] == [p.read_bytes() for p in second]
    with tarfile.open(first[1]) as tar:
        assert tar.getnames() == [
            "wasi-python-0.1.0a1",
            "wasi-python-0.1.0a1/LICENSES",
            "wasi-python-0.1.0a1/LICENSES/cpython.txt",
            "wasi-python-0.1.0a1/SHA256SUMS",
            "wasi-python-0.1.0a1/python.wasm",
        ]
        assert {m.mtime for m in tar.getmembers()} == {version.EPOCH}
    assert first[2].read_text().count("  ") == 2


def test_the_assets_pack_the_sets_list_never_its_folder(tmp_path: Path) -> None:
    """Litter in the folder (a name, an AppleDouble file, a volume folder)
    never enters the tarball, and the bytes are those of a clean folder."""
    wheel = tmp_path / "wasi_python-0.1.0a1-py3-none-any.whl"
    wheel.write_bytes(b"PK")
    tars = []
    for name, litter in (("clean", False), ("littered", True)):
        art = tmp_path / name / "artifacts"
        (art / "LICENSES").mkdir(parents=True)
        (art / "python.wasm").write_bytes(b"\0asm")
        (art / "LICENSES" / "cpython.txt").write_text("PSF")
        _sums(art)
        if litter:
            for rel in (".DS_Store", "LICENSES/._cpython.txt", ".TemporaryItems/x", "Thumbs.db"):
                (art / rel).parent.mkdir(parents=True, exist_ok=True)
                (art / rel).write_bytes(b"litter")
        tars.append(version.write_assets(art, wheel, tmp_path / name / "out", "0.1.0a1")[1])
    assert tars[0].read_bytes() == tars[1].read_bytes()


def test_the_assets_refuse_a_listed_file_that_is_missing(tmp_path: Path) -> None:
    art = tmp_path / "artifacts"
    art.mkdir()
    (art / "python.wasm").write_bytes(b"\0asm")
    _sums(art)
    (art / "python.wasm").unlink()
    wheel = tmp_path / "wasi_python-0.1.0a1-py3-none-any.whl"
    wheel.write_bytes(b"PK")
    with pytest.raises(SystemExit, match="python.wasm"):
        version.write_assets(art, wheel, tmp_path / "out", "0.1.0a1")


def test_bump_writes_both_files_or_neither(tmp_path: Path, monkeypatch) -> None:
    init, log = tmp_path / "__init__.py", tmp_path / "CHANGELOG.md"
    init.write_text(INIT)
    log.write_text(LOG.replace("0.1.0a1 —", "0.1.0a2 —"))  # a section for the next version already
    monkeypatch.setattr(version, "INIT", init)
    monkeypatch.setattr(version, "CHANGELOG", log)
    assert version.main(["bump"]) == 1  # the changelog edit fails...
    assert version.read_version(init.read_text()) == "0.1.0a1"  # ...and the version did not move
    log.write_text(LOG)
    assert version.main(["bump"]) == 0
    assert version.read_version(init.read_text()) == "0.1.0a2"
    assert list(version.sections(log.read_text())) == ["0.1.0a2", "0.1.0a1"]


def test_the_release_notes_say_how_to_verify_this_version() -> None:
    note = version.verify_note("0.1.0a2")
    assert "--source-ref refs/tags/v0.1.0a2" in note
    assert "--signer-workflow ClayGendron/wasi-python/.github/workflows/release.yml" in note
    assert "--deny-self-hosted-runners" in note


def test_the_notes_command_prints_the_verify_note(capsys) -> None:
    assert version.main(["notes", "0.1.0a1"]) == 0
    out = capsys.readouterr().out
    assert out.endswith(version.verify_note("0.1.0a1"))
    assert version.notes(version.CHANGELOG.read_text(), "0.1.0a1") in out


def test_the_verify_note_names_the_repository_it_is_given() -> None:
    note = version.verify_note("0.2.0", "ClayGendron/wasi-python")
    assert "--repo ClayGendron/wasi-python " in note
    assert "ClayGendron/wasi-python/.github/workflows/release.yml@refs/tags/v0.2.0" in note
    other = version.verify_note("0.2.0", "someone/fork")
    assert "--repo someone/fork " in other and "ClayGendron" not in other


def test_the_notes_command_takes_the_repository(capsys) -> None:
    assert version.main(["notes", "0.1.0a1", "--repository", "someone/fork"]) == 0
    assert capsys.readouterr().out.endswith(version.verify_note("0.1.0a1", "someone/fork"))


RELEASE_YML = paths.REPO / ".github" / "workflows" / "release.yml"


def _one_line(text: str) -> str:
    """A command with its `\\`-continued lines joined and its whitespace collapsed."""
    return " ".join(text.replace("\\\n", " ").split())


def _attest_command(workflow: str, tag_version: str, repository: str) -> str:
    """The attest job's `gh attestation verify` line, read as the command a user runs: the
    repository and the tag the job reads from its environment written out, the asset named
    `<asset>`, and the shell's quotes dropped."""
    from harness import scan

    jobs = scan.workflow_jobs(scan.without_comments(workflow))
    body = "\n".join(line.strip() for line in jobs["attest"])
    logical = body.replace("\\\n", " ").splitlines()
    lines = [line for line in logical if line.startswith("gh attestation verify")]
    assert len(lines) == 1, lines
    line = lines[0].replace('"$asset"', "<asset>")
    line = re.sub(r"\$GITHUB_REPOSITORY\b", repository, line)
    line = re.sub(r"\$GITHUB_REF\b", f"refs/tags/v{tag_version}", line)
    return _one_line(line.replace('"', ""))


def _note_command(note: str) -> str:
    block = note.split("```\n", 2)[1]
    return _one_line(block)


def test_the_verify_note_is_the_command_the_attest_job_runs() -> None:
    """The release notes tell users to run the command the release's attest job runs before it
    publishes, so an edit to either side, or a rename of the repository, fails here first."""
    repo = "ClayGendron/wasi-python"
    want = _attest_command(RELEASE_YML.read_text(), "0.2.0", repo)
    assert _note_command(version.verify_note("0.2.0", repo)) == want


def test_a_changed_flag_in_the_attest_job_breaks_the_equality() -> None:
    text = RELEASE_YML.read_text()
    flag = "--deny-self-hosted-runners"
    assert text.count(flag) == 1
    planted = text.replace(flag, "--cert-oidc-issuer x")
    note = _note_command(version.verify_note("0.2.0", "ClayGendron/wasi-python"))
    assert _attest_command(planted, "0.2.0", "ClayGendron/wasi-python") != note
