"""release/version.py: versions, the changelog, the tag check and the assets."""

from __future__ import annotations

import importlib.util
import re
import sys
import tarfile
import types
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
# The ledger's paths as the module names them, read before any row points them at its own files.
REAL_LEDGER = (version.LEDGER, version.LEDGER_HISTORY)


@pytest.fixture(autouse=True)
def _no_real_git_and_no_real_files(tmp_path_factory, monkeypatch) -> None:
    """No row reaches real git or the repository's own news files and ledger: git and every
    subprocess fail unless a row fakes them, and the folders and files the release's commands
    write are empty ones of the row's own, unless it names others."""

    def refused(*args, **kwargs):
        pytest.fail(f"a release command ran {args} outside a fake")

    monkeypatch.setattr(version, "git", refused)
    monkeypatch.setattr(version, "subprocess", types.SimpleNamespace(run=refused))
    own = tmp_path_factory.mktemp("release-files")
    (own / "changes").mkdir()
    for name, path in (("CHANGES", own / "changes"), ("PACKAGES", own / "packages.md"),
                       ("LEDGER", own / "ledger"),
                       ("LEDGER_HISTORY", own / "ledger-history.md")):  # fmt: skip
        monkeypatch.setattr(version, name, path)


def test_no_row_reaches_real_git() -> None:
    with pytest.raises(pytest.fail.Exception, match="outside a fake"):
        version.git("status")
    with pytest.raises(pytest.fail.Exception, match="outside a fake"):
        version.subprocess.run(["git", "push"])


PYPROJECT = (
    '[project]\nname = "wasi-python"\ndynamic = ["version"]\n\n'
    '[tool.hatch.version]\npath = "src/wasi_python/__init__.py"\n'
)
INIT = '"""x"""\n\n__version__ = "0.1.0a1"\n'
LOG = "# Changelog\n\n## 0.1.0a1 — unreleased\n\n- first\n"
PACKAGES = (
    "# Packages\n\n## Compiled packages\n\n| package | version | what works |\n|---|---|---|\n"
    "| numpy | 2.5.2 | Built in. |\n| pandas | 3.0.6 | Built in. |\n\nAfter the table.\n"
)


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


def _bump_files(tmp_path: Path, monkeypatch) -> tuple[Path, Path, Path, Path]:
    """The files bump writes, in tmp_path: never the repository's own news files."""
    init, log = tmp_path / "__init__.py", tmp_path / "CHANGELOG.md"
    changes, packages = tmp_path / "changes", tmp_path / "packages.md"
    changes.mkdir()
    packages.write_text(PACKAGES)
    monkeypatch.setattr(version, "INIT", init)
    monkeypatch.setattr(version, "CHANGELOG", log)
    monkeypatch.setattr(version, "CHANGES", changes)
    monkeypatch.setattr(version, "PACKAGES", packages)
    return init, log, changes, packages


def test_bump_writes_both_files_or_neither(tmp_path: Path, monkeypatch) -> None:
    init, log, _, _ = _bump_files(tmp_path, monkeypatch)
    init.write_text(INIT)
    # A dated section for the next version already: that version was released.
    log.write_text(LOG.replace("0.1.0a1 — unreleased", "0.1.0a2 — 2026-01-01"))
    assert version.main(["bump"]) == 1  # the changelog edit fails...
    assert version.read_version(init.read_text()) == "0.1.0a1"  # ...and the version did not move
    log.write_text(LOG)
    assert version.main(["bump"]) == 0
    assert version.read_version(init.read_text()) == "0.1.0a2"
    assert list(version.sections(log.read_text())) == ["0.1.0a2", "0.1.0a1"]


NEWS = """# {n}: a change

## Changelog

### {heading}

- **Change {n} works now.** It moved. [Sessions](https://claygendron.github.io/wasi-python/how-to/sessions/)

## Package rows

{rows}

## Claims

```toml
[[claim]]
spec = "{n}"
```
"""


def entry(n: str) -> str:
    """The one entry the news file `NEWS` writes for change `n`."""
    return next(
        line for line in NEWS.format(n=n, heading="New", rows="").splitlines() if "**" in line
    )


def test_bump_assembles_the_news_files_into_the_changelog_and_the_rows(
    tmp_path: Path, monkeypatch
) -> None:
    """Each news file's entries go under their heading in the new version's section, in the
    reader's heading order whatever the files' names, and the files' name order under one
    heading; each package row replaces the row of its package or joins the table's end; the news
    files are removed."""
    init, log, changes, packages = _bump_files(tmp_path, monkeypatch)
    init.write_text(INIT)
    log.write_text(LOG)
    (changes / "README.md").write_text("# the folder\n")
    rows = "| numpy | 2.6.0 | Built in, newer. |\n| regex | 2026.9.29 | Fuzzy matching. |"
    (changes / "201-second.md").write_text(NEWS.format(n="201", heading="Security", rows="None."))
    (changes / "200-first.md").write_text(
        NEWS.format(n="200", heading="For contributors", rows=rows)
    )
    (changes / "203-fourth.md").write_text(NEWS.format(n="203", heading="Security", rows="None."))
    (changes / "202-third.md").write_text(NEWS.format(n="202", heading="New", rows="None."))
    assert version.main(["bump"]) == 0
    section = version.notes(log.read_text(), "0.1.0a2")
    assert section == (
        f"### New\n\n{entry('202')}\n\n"
        f"### Security\n\n{entry('201')}\n{entry('203')}\n\n"
        f"### For contributors\n\n{entry('200')}\n"
    )
    assert packages.read_text() == PACKAGES.replace(
        "| numpy | 2.5.2 | Built in. |", "| numpy | 2.6.0 | Built in, newer. |"
    ).replace(
        "| pandas | 3.0.6 | Built in. |\n",
        "| pandas | 3.0.6 | Built in. |\n| regex | 2026.9.29 | Fuzzy matching. |\n",
    )
    assert sorted(p.name for p in changes.iterdir()) == ["README.md"]


def test_bump_joins_the_news_to_an_unreleased_section_already_written(
    tmp_path: Path, monkeypatch
) -> None:
    init, log, changes, _ = _bump_files(tmp_path, monkeypatch)
    init.write_text(INIT)
    written = "## 0.1.0a2 — unreleased\n\n### Fixed\n\n- by hand\n\n## 0.1.0a1 —"
    log.write_text(LOG.replace("## 0.1.0a1 —", written))
    (changes / "200-first.md").write_text(NEWS.format(n="200", heading="Fixed", rows="None."))
    assert version.main(["bump"]) == 0
    assert version.notes(log.read_text(), "0.1.0a2") == f"### Fixed\n\n- by hand\n{entry('200')}\n"


def test_bump_refuses_a_broken_news_file_and_writes_nothing(tmp_path: Path, monkeypatch) -> None:
    init, log, changes, packages = _bump_files(tmp_path, monkeypatch)
    init.write_text(INIT)
    log.write_text(LOG)
    (changes / "200-first.md").write_text(NEWS.format(n="200", heading="Improved", rows="None."))
    assert version.main(["bump"]) == 1
    assert init.read_text() == INIT and log.read_text() == LOG and packages.read_text() == PACKAGES
    assert (changes / "200-first.md").is_file()


def test_the_release_notes_say_how_to_verify_this_version() -> None:
    note = version.verify_note("0.1.0a2")
    assert "(https://claygendron.github.io/wasi-python/how-to/verify-a-download/)" in note
    assert "README" not in note  # the README no longer carries the steps; the site's page does
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


def test_date_dates_the_versions_section_and_commits_nothing(tmp_path: Path, monkeypatch) -> None:
    init, log = tmp_path / "__init__.py", tmp_path / "CHANGELOG.md"
    init.write_text(INIT)
    log.write_text(LOG)
    monkeypatch.setattr(version, "INIT", init)
    monkeypatch.setattr(version, "CHANGELOG", log)
    assert version.main(["date", "--day", "2026-10-26"]) == 0
    assert version.sections(log.read_text())["0.1.0a1"] == "2026-10-26"
    assert version.main(["date", "--day", "2026-10-27"]) == 1  # dated once


def _main_tip(tmp_path: Path, monkeypatch, changelog: str) -> list[tuple[str, ...]]:
    """A checkout of main level with origin/main, and every git call release makes."""
    init, log = tmp_path / "__init__.py", tmp_path / "CHANGELOG.md"
    init.write_text(INIT)
    log.write_text(changelog)
    monkeypatch.setattr(version, "INIT", init)
    monkeypatch.setattr(version, "CHANGELOG", log)
    calls: list[tuple[str, ...]] = []
    answers = {"status": "", "rev-parse": "main", "tag": ""}

    def git(*args: str, strip: bool = True) -> str:
        calls.append(args)
        if args[:2] == ("rev-parse", "--abbrev-ref"):
            return "main"
        return "c" * 40 if args[0] == "rev-parse" else answers.get(args[0], "")

    monkeypatch.setattr(version, "git", git)
    return calls


def test_release_tags_mains_tip_and_commits_nothing(tmp_path: Path, monkeypatch) -> None:
    """The release pull request judged main's tip with the section dated: the tag goes on that
    commit, and nothing is committed after it."""
    calls = _main_tip(tmp_path, monkeypatch, LOG.replace("unreleased", "2026-10-26"))
    assert version.main(["release", "--push"]) == 0
    assert not [c for c in calls if c[0] == "commit"]
    assert ("tag", "-a", "v0.1.0a1", "-m", "wasi-python 0.1.0a1\n\n- first\n") in calls
    assert calls[-1] == ("push", "origin", "v0.1.0a1")


def test_release_refuses_a_section_still_unreleased(tmp_path: Path, monkeypatch) -> None:
    calls = _main_tip(tmp_path, monkeypatch, LOG)
    assert version.main(["release", "--push"]) == 1
    assert not [c for c in calls if c[0] in ("commit", "push") or c[:2] == ("tag", "-a")]


def test_the_ledger_is_the_release_claims_folder() -> None:
    """One ledger of any claim the release reconciles, a folder of one file per pull request,
    beside its history by release; the judge's reader and the release's commands name the same
    two paths."""
    assert REAL_LEDGER == (paths.REPO / "context" / "release-claims",
                           paths.REPO / "context" / "release-claims-history.md")  # fmt: skip
    assert REAL_LEDGER == (paths.REPO / version._reader().LEDGER,
                           paths.REPO / version._reader().LEDGER_HISTORY)  # fmt: skip


def _ledger_files(tmp_path: Path, monkeypatch, files: dict[str, str]) -> tuple[Path, Path]:
    init, log = tmp_path / "__init__.py", tmp_path / "CHANGELOG.md"
    ledger, history = tmp_path / "ledger", tmp_path / "history.md"
    init.write_text(INIT)
    log.write_text(LOG)
    ledger.mkdir()
    (ledger / "README.md").write_text("# The ledger\n")
    for name, text in files.items():
        (ledger / name).write_text(text)
    history.write_text("# history\n\nIntro.\n")
    for name, path in (("INIT", init), ("CHANGELOG", log), ("LEDGER", ledger),
                       ("LEDGER_HISTORY", history)):  # fmt: skip
        monkeypatch.setattr(version, name, path)
    return ledger, history


def test_date_moves_a_claim_of_any_kind_under_the_version(tmp_path: Path, monkeypatch) -> None:
    """The ledger carries any claim block, a fall in passes, a tier move or a judge file as well as
    a growth, and date moves each whole."""
    block = (
        '[[claim]]\nspec = "161"\npasses = ["g"]\nfewer = "two tests moved"\n'
        '[claim.judge]\n"tests/known_gaps.toml" = "a new allowance"\n'
        '[claim.moved]\n"tests/checks/test_x.py::test_y" = "it is slow"\n'
    )
    ledger, history = _ledger_files(tmp_path, monkeypatch, {"161-growth.toml": block})
    assert version.main(["date", "--day", "2026-10-30"]) == 0
    assert "## 0.1.0a1" in history.read_text() and block.strip() in history.read_text()
    assert [p.name for p in ledger.iterdir()] == ["README.md"]


def test_date_moves_each_ledger_file_under_the_version_and_removes_it(
    tmp_path: Path, monkeypatch
) -> None:
    """Each file moves under its own name, in file-name order, and is removed; the folder's
    README stays, so the folder does."""
    files = {
        "171-the-zip.toml": '[[claim]]\nspec = "171"\ngrows = ["x"]\ngrowth = "y"\n',
        "140-a-pin.toml": '[[claim]]\nspec = "140"\ngrows = ["x"]\ngrowth = "y"\n',
    }
    ledger, history = _ledger_files(tmp_path, monkeypatch, files)
    assert version.main(["date", "--day", "2026-10-26"]) == 0
    text = history.read_text()
    assert "## 0.1.0a1" in text and text.index("`140-a-pin.toml`:") < text.index(
        "`171-the-zip.toml`:"
    )
    assert [p.name for p in ledger.iterdir()] == ["README.md"]


def test_date_refuses_a_ledger_file_out_of_shape_and_writes_nothing(
    tmp_path: Path, monkeypatch
) -> None:
    ledger, history = _ledger_files(
        tmp_path, monkeypatch, {"ledger.toml": '[[claim]]\nspec = "1"\n'}
    )
    assert version.main(["date", "--day", "2026-10-26"]) == 1
    assert (ledger / "ledger.toml").exists() and "## 0.1.0a1" not in history.read_text()


def test_date_assembles_a_news_file_merged_after_bump(tmp_path: Path, monkeypatch) -> None:
    """A fix merged into dev between bump and the release pull request keeps its news file: the
    date joins its lines to the version's section and removes it, so it reaches the notes."""
    init, log, changes, _ = _bump_files(tmp_path, monkeypatch)
    init.write_text(INIT)
    log.write_text(LOG)
    (changes / "203-late.md").write_text(NEWS.format(n="203", heading="Fixed", rows="None."))
    assert version.main(["date", "--day", "2026-10-26"]) == 0
    assert version.sections(log.read_text())["0.1.0a1"] == "2026-10-26"
    assert entry("203") in version.notes(log.read_text(), "0.1.0a1")
    assert "- first" in version.notes(log.read_text(), "0.1.0a1")
    assert not (changes / "203-late.md").exists()


# ---------------------------------------------------------------------------------------------
# From 0.1.2 a section is the reader's notes: a summary, then entries under the six headings

SUMMARY = (
    "This release is for embedders who keep many guests running. Every session ends, however it "
    "is closed, and tool calls have bounds you can read. One change may need action: a tool call "
    "that nothing else bounds now ends after an hour."
)
INIT_012 = INIT.replace("0.1.0a1", "0.1.2")
OLD_011 = "## 0.1.1 — 2026-10-27\n\n### Changed\n\n- **A thing moved** (a line in the old shape).\n"


def reader_log(body: str, day: str = "unreleased") -> str:
    return f"# Changelog\n\nThe header.\n\n## 0.1.2 — {day}\n\n{body}\n\n{OLD_011}"


def _dated_files(tmp_path: Path, monkeypatch, changelog: str) -> Path:
    init, log = tmp_path / "__init__.py", tmp_path / "CHANGELOG.md"
    init.write_text(INIT_012)
    log.write_text(changelog)
    monkeypatch.setattr(version, "INIT", init)
    monkeypatch.setattr(version, "CHANGELOG", log)
    return log


def test_date_refuses_a_readers_section_without_its_summary(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """A section from 0.1.2 on is dated only with its summary: without one `date` names the fault
    and writes nothing; with one of 30 to 120 words it dates the section."""
    bare = reader_log(f"### Fixed\n\n{entry('200')}")
    log = _dated_files(tmp_path, monkeypatch, bare)
    assert version.main(["date", "--day", "2026-11-02"]) == 1
    assert "no summary" in capsys.readouterr().err
    assert log.read_text() == bare
    log.write_text(reader_log(f"{SUMMARY}\n\n### Fixed\n\n{entry('200')}"))
    assert version.main(["date", "--day", "2026-11-02"]) == 0
    assert version.sections(log.read_text())["0.1.2"] == "2026-11-02"


def test_check_names_a_dated_readers_section_out_of_shape() -> None:
    """Every dated section from 0.1.2 on is held to the reader's shape; the published 0.1.1 in
    the old shape is not read."""
    good = reader_log(f"{SUMMARY}\n\n### Fixed\n\n{entry('200')}", "2026-11-02")
    assert version.check_errors(INIT_012, PYPROJECT, good) == []
    no_summary = reader_log(f"### Fixed\n\n{entry('200')}", "2026-11-02")
    old_heading = reader_log(f"{SUMMARY}\n\n### Changed\n\n{entry('200')}", "2026-11-02")
    bad_entry = reader_log(f"{SUMMARY}\n\n### Fixed\n\n- **Change 200**: it moved.", "2026-11-02")
    for log, words in [
        (no_summary, "no summary"),
        (old_heading, "'Changed' is not one of New, Faster"),
        (bad_entry, "end with a link"),
    ]:
        errors = version.check_errors(INIT_012, PYPROJECT, log)
        assert errors and all(e.startswith("CHANGELOG.md's section for 0.1.2: ") for e in errors)
        assert any(words in e for e in errors), errors
    # Not yet dated: the summary is written between bump and date, so nothing is asked yet.
    assert (
        version.check_errors(INIT_012, PYPROJECT, reader_log(f"### Fixed\n\n{entry('200')}")) == []
    )


def test_the_notes_open_with_the_summary_then_the_headings_then_the_verify_note(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """The release's whole path for a reader's version: bump assembles the news files under the
    headings in the reader's order, the summary is written in, date dates it, and notes prints
    the summary first, the headings in order and the verify note last."""
    init, log, changes, _ = _bump_files(tmp_path, monkeypatch)
    init.write_text(INIT.replace("0.1.0a1", "0.1.1"))
    log.write_text("# Changelog\n\nThe header.\n\n" + OLD_011)
    (changes / "200-first.md").write_text(NEWS.format(n="200", heading="Fixed", rows="None."))
    (changes / "201-second.md").write_text(NEWS.format(n="201", heading="New", rows="None."))
    assert version.main(["bump", "--to", "0.1.2"]) == 0
    text = log.read_text()
    log.write_text(
        text.replace("## 0.1.2 — unreleased\n\n", f"## 0.1.2 — unreleased\n\n{SUMMARY}\n\n")
    )
    assert version.main(["date", "--day", "2026-11-02"]) == 0
    capsys.readouterr()
    assert version.main(["notes", "0.1.2"]) == 0
    out = capsys.readouterr().out
    assert out.startswith(SUMMARY + "\n\n### New\n\n" + entry("201") + "\n\n### Fixed\n\n")
    assert out.index(entry("200")) < out.index("**Verify a download**")
