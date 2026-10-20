"""Each repository scanner, firing on a bad input and quiet on a good one."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from harness import jobs, paths, scan


def write(base: Path, rel: str, text: str) -> Path:
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def test_embedder_names_in_text_and_in_paths(work) -> None:
    write(work, "src/clean.py", "x = 1\n")
    assert scan.embedder_hits(work, ["src"], ["acme"]) == []
    write(work, "src/acme_door.c", "int x;\n")
    write(work, "src/mod.py", "import os\nfrom ACME import door\n")
    assert scan.embedder_hits(work, ["src"], ["acme"]) == [
        "src/acme_door.c: in the file's path",
        "src/mod.py:2",
    ]


def test_names_file_ignores_comments(work) -> None:
    f = write(work, "names.txt", "# a comment naming nobody\nAcme\n\n")
    assert scan.read_names(f) == ["acme"]


def test_clock_reads(work) -> None:
    # The clock calls are assembled, so this file does not trip the scanner it tests.
    perf, from_time = "time." + "perf_counter()", "from " + "time import monotonic"
    good = write(work, "t/test_a.py", "def test(): assert 1  # " + "time." + "time() noted\n")
    bad = write(work, "t/test_b.py", f"import time\nstart = {perf}\n")
    from_import = write(work, "t/test_c.py", f"{from_time}\n")
    assert scan.clock_hits([good], work) == []
    assert scan.clock_hits([bad, from_import], work) == [
        f"t/test_b.py:2: start = {perf}",
        f"t/test_c.py:1: {from_time}",
    ]


def test_fetches_outside_the_download_script(work) -> None:
    dl = write(work, "s/00_download.sh", "#!/bin/sh\ncurl -o x https://e.org/x\n")
    ok = write(work, "s/build.sh", "#!/bin/sh\n# we never curl here\nmake\n")
    bad = write(work, "s/sneak.sh", "#!/bin/sh\nuv pip install cython\n")
    assert scan.fetch_hits([dl, ok], "00_download.sh", work) == []
    assert scan.fetch_hits([dl, ok, bad], "00_download.sh", work) == [
        "s/sneak.sh:2: uv pip install cython"
    ]


def test_only_a_sole_offline_hash_checked_uv_install_is_exempt(work) -> None:
    good = "uv pip install --target t --offline --no-index --require-hashes -r r.txt"
    lines = {
        "ok": good,
        "chained": good + '; curl -fsSL -o x "$MIRROR"',
        "online": good.replace("--offline ", ""),
        "unhashed": good.replace("--require-hashes ", ""),
        "url": good + " --find-links https://e.org/w",
    }
    for name, line in lines.items():
        write(work, f"s/{name}.sh", f"#!/bin/sh\n{line}\n")
    files = [work / "s" / f"{name}.sh" for name in lines]
    assert [h.split(":")[0] for h in scan.fetch_hits(files, "00_download.sh", work)] == [
        "s/chained.sh",
        "s/online.sh",
        "s/unhashed.sh",
        "s/url.sh",
    ]


def test_scripts_are_found_at_any_depth(work) -> None:
    top = write(work, "scripts/build.sh", "#!/bin/sh\n")
    step = write(work, "scripts/steps/40_x.sh", "#!/bin/sh\ncurl -o x https://e.org/x\n")
    write(work, "scripts/steps/__pycache__/x.pyc", "")
    found = scan.every_file(work / "scripts")
    assert found == [top, step]
    assert scan.fetch_hits(found, "00_download.sh", work) == [
        "scripts/steps/40_x.sh:2: curl -o x https://e.org/x"
    ]


def test_bare_python_is_found_and_paths_and_uv_are_not(work) -> None:
    ok = write(
        work,
        "s/ok.sh",
        '#!/bin/sh\n"$HERE/.venv-build/bin/python" x.py\nuv run python y.py\n# python z\n',
    )
    bad = write(work, "s/bad.sh", "#!/bin/sh\ncurl -s u | python3 -c 'print(1)'\npip install x\n")
    assert scan.bare_python_hits([ok], work) == []
    assert [h.split(":")[1] for h in scan.bare_python_hits([bad], work)] == ["2", "3"]


@pytest.mark.parametrize(
    "line",
    [
        'rm -rf "$x"',
        'rm -fr "$x"',
        'rm -Rf "$x"',
        'rm -r -f "$x"',
        'rm --recursive --force "$x"',
        "cd x && rm -rf y",
        "find . -name z -exec rm -rf {} +",
        'if true; then rm -rf "$x"; fi',
        'if rm -rf "$x"; then :; fi',
        "printf '%s\\0' a | xargs -0 rm -rf",
        '\\rm -rf "$x"',
        '/bin/rm -rf "$x"',
        'x=1 rm -rf "$x"',
        'rm \\\n  -rf "$x"',
    ],
)
def test_a_recursive_forced_rm_is_found(work, line) -> None:
    bad = write(work, "scripts/steps/x.sh", f"#!/bin/sh\n{line}\n")
    assert [h.split(":")[1] for h in scan.bare_rm_hits([bad], work)] == ["2"]


def test_rm_without_both_flags_and_remove_sh_are_not_hits(work) -> None:
    ok = write(
        work, "scripts/steps/ok.sh", '#!/bin/sh\nrm -f "$x"\nrm -r "$y"\nremove "$z"\n# rm -rf q\n'
    )
    sh = write(work, "scripts/steps/remove.sh", 'remove() { rm -rf "$1"; }\n')
    assert scan.bare_rm_hits([ok, sh], work) == []


def test_no_build_script_removes_without_retrying() -> None:
    """Every removal in a build script goes through `remove`."""
    scripts = scan.files_under(paths.REPO, "scripts")
    assert scan.bare_rm_hits(scripts, paths.REPO) == []


def test_every_pin_needs_a_literal_url(work) -> None:
    dl = write(work, "00_download.sh", 'get https://e.org/dl/a-1.tar.gz\nget "$(lookup b)"\n')
    assert scan.url_errors(dl, ["a-1.tar.gz"]) == []
    assert scan.url_errors(dl, ["a-1.tar.gz", "b-2.tar.gz"]) == [
        "b-2.tar.gz: no literal URL ends in it in 00_download.sh"
    ]
    named = write(
        work,
        "named.sh",
        "get https://e.org/download?id=7 c-3.whl\nresearch https://e.org/r r.zip\n",
    )
    assert scan.url_errors(named, ["c-3.whl", "r.zip"]) == []
    assert scan.url_errors(named, ["d-4.whl"]) == ["d-4.whl: no literal URL ends in it in named.sh"]


def test_the_download_script_must_verify_and_not_write(work) -> None:
    good = write(work, "good.sh", "fetch\nshasum -a 256 -c SHA256SUMS\n")
    bad = write(work, "bad.sh", "fetch\nshasum -a 256 *.tar.gz | tee SHA256SUMS\n")
    assert scan.download_script_errors(good) == []
    assert scan.download_script_errors(bad) == [
        "it never checks the downloads against SHA256SUMS (`shasum -a 256 -c`)",
        "it writes SHA256SUMS instead of only reading it",
    ]


def test_recipe_paths_must_exist_outside_generated_roots(work) -> None:
    write(work, "recipes/x.h", "")
    f = write(
        work,
        "s.sh",
        'cp "$HERE/recipes/x.h" "$HERE/build/y"\nsed @S12@/cross/x.h\nls $HERE/downloads/z.\n',
    )
    assert scan.recipe_path_errors([f], work) == ["s.sh:2: names cross/x.h, which does not exist"]
    cross = write(work, "w.cross", "c = '@ROOT@/recipes/x.h'\nd = '@ROOT@/recipes/gone.h'\n")
    assert scan.recipe_path_errors([cross], work) == [
        "w.cross:2: names recipes/gone.h, which does not exist"
    ]


def test_toolchain_pins_for_both_hosts() -> None:
    both = [
        "wasi-sdk-24.0-arm64-macos.tar.gz",
        "wasi-sdk-24.0-x86_64-linux.tar.gz",
        "wasmtime-v49.0.3-aarch64-macos.tar.xz",
        "wasmtime-v49.0.3-x86_64-linux.tar.xz",
    ]
    assert scan.toolchain_errors(both) == []
    assert scan.toolchain_errors(both[:1]) == [
        "wasi-sdk: no Linux x86_64 pin",
        "wasmtime: no Linux x86_64 pin",
        "wasmtime: no macOS arm64 pin",
    ]


def test_pure_python_pins() -> None:
    wheels = [
        "python_dateutil-2.9.0.post0-py2.py3-none-any.whl",
        "tzdata-2026.5-py2.py3-none-any.whl",
        "six-1.17.0-py2.py3-none-any.whl",
    ]
    assert scan.pure_python_errors(wheels) == []
    assert scan.pure_python_errors(wheels[1:]) == ["python-dateutil: not pinned"]


SPEC = """# 009 — A spec

- **Status:** {status}
- **Owner:** someone
- **Kind:** feature
- **Depends on:** nothing
- **Research it stands on:** a memo

## Decisions
## Intent
## Design
## Scope
## Acceptance criteria
## Landing notes
{notes}
"""


def test_spec_shape(work) -> None:
    good = write(work, "009-a.md", SPEC.format(status="draft", notes=""))
    bad = write(work, "010-b.md", "# 010\n\n- **Status:** draft\n\n## Intent\n")
    assert scan.spec_shape_errors(good) == []
    errors = scan.spec_shape_errors(bad)
    assert "010-b.md: no 'Owner' header line" in errors
    assert "010-b.md: no '## Decisions' section" in errors


def test_open_questions_outside_code(work) -> None:
    good = write(work, "a.md", "We forbid `TBD` and `open question` in code spans.\n")
    bad = write(work, "b.md", "## Questions for the owner\nThe size is TBD.\n")
    assert scan.open_question_hits(good) == []
    assert scan.open_question_hits(bad) == [
        "b.md: a questions heading: ## Questions for the owner",
        "b.md: The size is TBD.",
    ]


def test_a_landed_spec_cites_an_existing_review(work) -> None:
    reviews = work / "reviews"
    write(reviews, "009-a-2026-10-16.md", "review")
    landed_ok = write(
        work, "009-a.md", SPEC.format(status="landed", notes="See reviews/009-a-2026-10-16.md.")
    )
    landed_missing = write(
        work, "010-b.md", SPEC.format(status="landed, 2026", notes="See reviews/010-b.md.")
    )
    landed_none = write(work, "011-c.md", SPEC.format(status="landed", notes="Done."))
    draft = write(work, "012-d.md", SPEC.format(status="draft", notes=""))
    assert scan.landed_review_errors(landed_ok, reviews) == []
    assert scan.landed_review_errors(draft, reviews) == []
    assert scan.landed_review_errors(landed_missing, reviews) == [
        "010-b.md: cites reviews/010-b.md, which does not exist"
    ]
    assert scan.landed_review_errors(landed_none, reviews) == [
        "011-c.md: landed, but its landing notes cite no review"
    ]


ROWS = "".join(f"| {tag} {row} | Strong | Strong | holds |\n" for tag, row in scan.STRUCTURAL_ROWS)


def test_a_release_has_its_structural_review(work) -> None:
    reviews = work / "reviews"
    reviews.mkdir()
    assert scan.structural_review_errors("0.1.0a8", reviews) == []  # a prerelease: never
    assert scan.structural_review_errors("0.1.0", reviews) == [
        "0.1.0 is a release; reviews/ has no 0.1.0-structural-review-<date>.md"
    ]
    write(reviews, "0.1.0-security-review-2026-10-21.md", ROWS)  # the twin does not count
    write(reviews, "structural-0.1.0-2026-10-21.md", ROWS)  # nor the other order of words
    assert len(scan.structural_review_errors("0.1.0", reviews)) == 1
    write(reviews, "0.1.0-structural-review-2026-10-21.md", ROWS)
    assert scan.structural_review_errors("0.1.0", reviews) == []
    assert len(scan.structural_review_errors("0.2.0", reviews)) == 1  # another version's file
    write(reviews, "0.1.0-structural-review-2026-10-22.md", ROWS.replace("R4 Process state", "R4"))
    assert scan.structural_review_errors("0.1.0", reviews) == [
        "0.1.0-structural-review-2026-10-22.md: does not score R4 (Process state)"
    ]


STRUCTURAL = SPEC.replace(
    "- **Kind:** feature", "- **Kind:** parallel-safe;\n  **structural**: it adds a lock"
)
NOT_STRUCTURAL = SPEC.replace("- **Kind:** feature", "- **Kind:** parallel-safe; not structural")


def test_a_built_structural_spec_cites_its_pre_build_review(work) -> None:
    reviews = work / "reviews"
    write(reviews, "110-a-spec-2026-10-21.md", "review")
    plain = write(work, "110-a.md", SPEC.format(status="**built 2026-10-21**", notes=""))
    word = write(work, "109-z.md", NOT_STRUCTURAL.format(status="**built 2026-10-21**", notes=""))
    drafted = write(work, "111-b.md", STRUCTURAL.format(status="drafted 2026-10-21", notes=""))
    says = write(
        work,
        "115-g.md",
        STRUCTURAL.format(status="drafted 2026-10-21, to be built on 107's tip", notes=""),
    )
    none = write(work, "112-c.md", STRUCTURAL.format(status="**built 2026-10-21**", notes=""))
    ok = write(
        work,
        "110-d.md",
        STRUCTURAL.format(status="landed", notes="Reviewed: reviews/110-a-spec-2026-10-21.md."),
    )
    other = write(
        work,
        "113-e.md",
        STRUCTURAL.format(status="built", notes="Reviewed: reviews/110-a-spec-2026-10-21.md."),
    )
    cites_missing = "reviews/114-f-spec-2026-10-21.md"
    missing = write(work, "114-f.md", STRUCTURAL.format(status="built", notes=cites_missing))
    assert scan.structural_spec_review_errors(plain, reviews) == []  # no token
    assert scan.structural_spec_review_errors(word, reviews) == []  # the word, not the token
    assert scan.structural_spec_review_errors(drafted, reviews) == []  # not yet built
    assert scan.structural_spec_review_errors(says, reviews) == []  # says built, is drafted
    assert scan.structural_spec_review_errors(ok, reviews) == []
    assert scan.structural_spec_review_errors(none, reviews) == [
        "112-c.md: structural and built, but cites no reviews/112-<slug>-spec-<date>.md"
    ]
    assert scan.structural_spec_review_errors(other, reviews) == [  # another spec's review
        "113-e.md: structural and built, but cites no reviews/113-<slug>-spec-<date>.md"
    ]
    assert scan.structural_spec_review_errors(missing, reviews) == [
        "114-f.md: cites reviews/114-f-spec-2026-10-21.md, which does not exist"
    ]


# The programs below are assembled from pieces at run time, so this file's own string constants
# carry no import and patch together and do not trip the scanner they test.
RUNNER_IMPORT = "from wasi_python import runner\n"
PATCH_LINE = "def test(monkeypatch):\n    monkeypatch.setattr(runner, '_x', 1)\n"


def _seams(work: Path, allowed: tuple[str, ...]) -> list[str]:
    files = sorted(p for p in work.rglob("*.py"))
    return scan.seam_hits(files, work, allowed)


def test_a_private_runner_name_the_judge_patches_is_a_hit(work) -> None:
    write(work, "t/test_a.py", RUNNER_IMPORT + PATCH_LINE)
    assert _seams(work, ()) == ["t/test_a.py:3: runner._x"]
    assert _seams(work, ("_x",)) == []
    write(work, "t/test_a.py", RUNNER_IMPORT + "runner._x = 1\n")  # a plain assignment
    assert _seams(work, ()) == ["t/test_a.py:2: runner._x"]
    write(work, "t/test_a.py", "import wasi_python.runner\n" + "wasi_python." + "runner._x = 1\n")
    assert _seams(work, ()) == ["t/test_a.py:2: runner._x"]
    write(work, "t/test_a.py", 'PROGRAM = """\n' + RUNNER_IMPORT + "runner._x = 1\n" + '"""\n')
    assert _seams(work, ()) == ["t/test_a.py:3: runner._x"]  # a child program in a string
    write(work, "t/test_a.py", RUNNER_IMPORT + "def test(m):\n    m.setattr(runner, '_x', 1)\n")
    assert _seams(work, ()) == ["t/test_a.py:3: runner._x"]  # the fixture under another name
    write(work, "t/test_a.py", RUNNER_IMPORT + "runner._x, other = 1, 2\n")
    assert _seams(work, ()) == ["t/test_a.py:2: runner._x"]  # a tuple target
    write(
        work,
        "t/test_a.py",
        "def test(monkeypatch):\n    monkeypatch.setattr('wasi_python." + "runner._x', 1)\n",
    )
    assert _seams(work, ()) == ["t/test_a.py:2: runner._x"]  # the dotted-string form
    write(work, "t/test_a.py", RUNNER_IMPORT + "monkeypatch.setattr(runner._Home, '_x', 1)\n")
    assert _seams(work, ()) == []  # a class attribute
    write(
        work, "t/test_a.py", "from wasi_python import tools\nmonkeypatch.setattr(tools, '_x', 1)\n"
    )
    assert _seams(work, ()) == []  # tools is outside the rule
    write(
        work,
        "t/test_a.py",
        "from wasi_python import _tool_host as H\nmonkeypatch.setattr(H, '_x', 1)\n",
    )
    assert _seams(work, ()) == []  # so is the tool protocol's host, under the name it is bound to
    write(work, "t/test_a.py", "monkeypatch.setattr('wasi_python._tool_host._x', 1)\n")
    assert _seams(work, ()) == []  # and in the dotted-string form
    write(
        work,
        "t/test_a.py",
        "from wasi_python._process import process\n"
        "monkeypatch.setattr(process().observers, '_x', 1)\n",
    )
    assert _seams(work, ()) == []  # the one way: through the process object
    assert _seams(work, ("_x",)) == ["stale allowance: _x"]


def _function(name: str, lines: int, indent: str = "") -> str:
    """A function of exactly `lines` lines, def to last line."""
    body = "".join(f"{indent}    x = {i}\n" for i in range(lines - 1))
    return f"{indent}def {name}():\n{body}"


def test_a_function_over_the_ceiling_is_a_hit(work) -> None:
    over = scan.FUNCTION_CEILING + 1
    f = write(work, "m.py", _function("f", over))
    assert scan.long_function_hits([f], work, {}) == [f"m.py:1: f ({over} lines)"]
    assert scan.long_function_hits([f], work, {"m.py:f": over}) == []
    write(work, "m.py", _function("f", scan.FUNCTION_CEILING))
    assert scan.long_function_hits([f], work, {}) == []  # at the ceiling: fine
    assert scan.long_function_hits([f], work, {"m.py:f": over}) == [
        f"stale allowance: m.py:f ({scan.FUNCTION_CEILING} lines)"
    ]
    write(work, "m.py", "class C:\n" + _function("m", over, "    "))
    assert scan.long_function_hits([f], work, {}) == [f"m.py:2: C.m ({over} lines)"]
    write(work, "m.py", "def f():\n" + _function("g", over, "    ") + "    return g\n")
    assert scan.long_function_hits([f], work, {}) == [
        f"m.py:1: f ({over + 2} lines)",
        f"m.py:2: f.g ({over} lines)",
    ]
    assert scan.long_function_hits([f], work, {"m.py:f": over + 2, "m.py:f.g": over}) == []
    assert scan.long_function_hits(
        [f], work, {"m.py:f": over + 2, "m.py:f.g": over, "m.py:h": 90}
    ) == ["stale allowance: m.py:h (gone)"]


def test_memo_labels(work) -> None:
    labelled = write(work, "a.md", "- **Status:** executed\n\nIt ran (EXECUTED).\n")
    placeholder = write(work, "b.md", "- **Status:** placeholder (research to do)\n")
    bare = write(work, "c.md", "- **Status:** executed\n\nIt ran.\n")
    assert scan.memo_label_errors(labelled) == []
    assert scan.memo_label_errors(placeholder) == []
    assert scan.memo_label_errors(bare) == ["c.md: no EXECUTED, READ or INFERRED label"]


def test_prior_art_index(work) -> None:
    write(work, "README.md", "| clone | what | licence |\n|---|---|---|\n| `alpha` | x | MIT |\n")
    write(work, "alpha/LICENSE", "MIT")
    assert scan.prior_art_errors(work) == []
    write(work, "beta/main.c", "")
    assert scan.prior_art_errors(work) == [
        "beta: no row with a licence in context/prior_art/README.md",
        "beta: no licence file in the clone",
    ]


def test_golden_comparison_names_stale_goldens_and_the_first_difference(work) -> None:
    v1 = b"versions python=3.14 numpy=2.5.2 pandas=3.0.6\nrows 3\n"
    v2 = b"versions python=3.14 numpy=2.5.3 pandas=3.0.6\nrows 3\n"
    assert jobs.compare(v1, v1) is None
    assert jobs.compare(v1, v2).startswith("goldens are stale")
    trace = b"Traceback (most recent call last):\nrows 3\n"
    assert jobs.compare(v1, trace).startswith("line 1: expected 'versions")
    assert jobs.compare(v1, v1.replace(b"rows 3", b"rows 4")) == (
        "line 2: expected 'rows 3', got 'rows 4'"
    )
    out = work / "out"
    write(out, "b.csv", "2\n")
    write(out, "a.csv", "1\n")
    assert jobs.render(b"hello\n", out) == b"hello\n=== a.csv\n1\n=== b.csv\n2\n"


def test_a_digest_ignores_line_numbers_but_not_findings() -> None:
    moved = scan.digest(["scripts/a.sh:3: python3 x", "recipes/b.c:10"])
    assert moved == scan.digest(["scripts/a.sh:9: python3 x", "recipes/b.c:12"])
    assert moved != scan.digest(["scripts/a.sh:3: python3 x", "recipes/c.c:10"])
    assert moved != scan.digest(["scripts/a.sh:3: python3 x"])


GOOD_WORKFLOW = """name: release
jobs:
  build:
    runs-on: macos-15
  verify:
    needs: build
  attest:
    if: github.event_name == 'push' && github.ref_type == 'tag'
    needs: [build, verify, gather]
    permissions:
      id-token: write
      attestations: write
      contents: read
    steps:
      - uses: actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333 # v8.0.2
      - uses: actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6 # v4.2.2
        with:
          subject-path: release-assets/*
      - name: verify
        run: |
          gh attestation verify "$a" --repo "$R" \\
            --signer-workflow "$W" --source-ref "$REF" --deny-self-hosted-runners
  publish:
    if: github.event_name == 'push' && github.ref_type == 'tag'
    needs: [build, verify, attest, gather]
    permissions:
      contents: write
  pypi:
    permissions:
      id-token: write
"""

ATTEST_IF = "  attest:\n    if: github.event_name == 'push' && github.ref_type == 'tag'\n"
VERIFY = '          gh attestation verify "$a" --repo "$R" \\\n'

BAD_WORKFLOWS = [
    (("  attest:\n", "  other:\n"), "no attest job"),
    ((ATTEST_IF, "  attest:\n    if: always()\n"), "attest's or publish's if:"),
    (
        ("    needs: [build, verify, gather]\n", "    needs: [build]\n"),
        "attest does not need build,",
    ),
    (
        ("    needs: [build, verify, gather]\n", "    needs: [build, verify]\n"),
        "attest does not need build, verify and gather",
    ),
    (("      contents: read\n", "      contents: write\n"), "attest's permissions are not"),
    (
        ("actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6", "actions/attest@v4"),
        "no actions/attest step pinned by a 40-hex commit",
    ),
    (
        ("subject-path: release-assets/*", "subject-path: release-assets/*.whl"),
        "subject-path is not release-assets/*",
    ),
    ((" --deny-self-hosted-runners", ""), "a gh attestation verify without"),
    (
        ("      - uses: actions/download-artifact@", "      - uses: actions/fetch-artifact@"),
        "attest's steps are not download, attest, verify",
    ),
    (
        ("      - name: verify\n", "      - name: verify\n        continue-on-error: true\n"),
        "a step of attest has if: or continue-on-error:",
    ),
    (
        ("    contents: write\n  pypi:", "    contents: write\n      id-token: write\n  pypi:"),
        "publish has id-token: write or write-all",
    ),
    (
        ("    needs: [build, verify, attest, gather]\n", "    needs: [build, verify, gather]\n"),
        "publish does not need attest and gather",
    ),
    (
        ("    needs: [build, verify, attest, gather]\n", "    needs: [build, verify, attest]\n"),
        "publish does not need attest and gather",
    ),
    # Ways around the first scan.
    (
        ("      - uses: actions/attest@", "      # - uses: actions/attest@"),
        "no actions/attest step pinned by a 40-hex commit",
    ),
    (
        ("    needs: [build, verify, gather]\n", "    needs: [build]  # verify, gather\n"),
        "attest does not need build,",
    ),
    (
        (
            "    needs: [build, verify, gather]\n",
            "    needs: [build, verify, gather]\n    continue-on-error: true\n",
        ),
        "attest has a job-level continue-on-error:",
    ),
    (
        ("--deny-self-hosted-runners\n", "--deny-self-hosted-runners || true\n"),
        "a step of attest swallows a failure",
    ),
    (
        ("name: release\njobs:\n", "name: release\npermissions: write-all\njobs:\n"),
        "the workflow-level permissions grant",
    ),
    (
        (VERIFY, '          gh attestation verify "$a"\n          echo --repo \\\n'),
        "a gh attestation verify without",
    ),
    (
        ("      - name: verify\n", "      - uses: astral-sh/setup-uv@abc\n      - name: verify\n"),
        "attest runs setup-uv or uv",
    ),
]


def test_release_attestation_scan_passes_a_good_workflow() -> None:
    assert scan.release_attestation_errors(GOOD_WORKFLOW) == []


@pytest.mark.parametrize(("change", "error"), BAD_WORKFLOWS, ids=[e for _, e in BAD_WORKFLOWS])
def test_release_attestation_scan_names_each_breach(change, error) -> None:
    old, new = change
    assert GOOD_WORKFLOW.count(old) == 1, old
    errors = scan.release_attestation_errors(GOOD_WORKFLOW.replace(old, new))
    assert errors and errors[0].startswith(error), errors  # the first breach is the one named


HOST_CONF = """PYTHON_VERSION=3.15.0
A_WASI_SDK_DIR=sdk-a
A_WASMTIME_DIR=wt-a
A_HOST_PYTHON_ARCHIVE=py-a.tar.gz
A_CYTHON_WHEEL=cy-a.whl
A_NINJA_WHEEL=ninja-a.whl
B_WASI_SDK_DIR=sdk-b
B_WASMTIME_DIR=wt-b
B_HOST_PYTHON_ARCHIVE=py-b.tar.gz
B_CYTHON_WHEEL=cy-b.whl
B_NINJA_WHEEL=ninja-b.whl
"""
HOST_DOWNLOAD = """get() { :; }
case "$HOST_KEY" in
  A)
    get https://x/sdk-a.tar.gz sdk-a.tar.gz
    get https://x/wt-a.tar.xz wt-a.tar.xz
    get https://x/py-a.tar.gz py-a.tar.gz
    get https://x/cy-a.whl cy-a.whl
    get https://x/ninja-a.whl ninja-a.whl
    ;;
  B)
    get https://x/sdk-b.tar.gz sdk-b.tar.gz
    get https://x/wt-b.tar.xz wt-b.tar.xz
    get https://x/py-b.tar.gz py-b.tar.gz
    get https://x/cy-b.whl cy-b.whl
    get https://x/ninja-b.whl ninja-b.whl
    ;;
esac
get https://x/meson.whl meson.whl
"""
HOST_PINS = [
    f"{stem}-{key}{ext}"
    for key in "ab"
    for stem, ext in (
        ("sdk", ".tar.gz"),
        ("wt", ".tar.xz"),
        ("py", ".tar.gz"),
        ("cy", ".whl"),
        ("ninja", ".whl"),
    )
]


def _host_table(conf=HOST_CONF, sh=("A", "B"), py=("A", "B"), download=HOST_DOWNLOAD, pins=None):
    return scan.host_table_errors(conf, sh, py, download, HOST_PINS if pins is None else pins)


def test_host_table_passes_a_whole_table() -> None:
    assert scan.host_case_branches(HOST_DOWNLOAD)["B"][-1] == "ninja-b.whl"
    assert _host_table() == []


def test_host_table_names_each_breach() -> None:
    assert _host_table(conf=HOST_CONF.replace("B_NINJA_WHEEL=ninja-b.whl\n", "")) == [
        "line.conf: no B_NINJA_WHEEL"
    ]
    assert _host_table(pins=HOST_PINS[1:]) == ["A_WASI_SDK_DIR: sdk-a.tar.gz is not pinned"]
    swapped = HOST_DOWNLOAD.replace("ninja-a.whl ninja-a.whl", "ninja-b.whl ninja-b.whl")
    assert _host_table(download=swapped) == [
        "A_NINJA_WHEEL: ninja-a.whl is not fetched in the A branch"
    ]
    assert _host_table(sh=("A",)) == ["line.sh: hosts ['A'], but line.conf has ['A', 'B']"]
    assert _host_table(py=("A", "B", "C")) == [
        "line.py: hosts ['A', 'B', 'C'], but line.conf has ['A', 'B']"
    ]
    plain = "WASI_SDK_DIR=sdk-a\n" + HOST_CONF
    assert _host_table(conf=plain) == [
        "line.conf: WASI_SDK_DIR is set for every host, not per host key"
    ]
    today = "WASI_SDK_DIR=sdk-a\nWASMTIME_DIR=wt-a\n"
    assert _host_table(conf=today, sh=(), py=(), download="get https://x/a a\n") == [
        "line.conf: WASI_SDK_DIR is set for every host, not per host key",
        "line.conf: WASMTIME_DIR is set for every host, not per host key",
        "line.conf: no host key names a host's inputs",
    ]


# One workflow that every release scan reads. Every reader of the build's files guards
# the id, downloads by it, and checks the files; the rebuilds are two jobs alike.
PIN = "0123456789abcdef0123456789abcdef01234567"
GUARD = """      - name: The build job handed on an artifact id
        env:
          ASSETS_ID: ${{ needs.build.outputs.assets-id }}
        run: |
          case "$ASSETS_ID" in
            "" | *[!0-9]*) echo "the build job handed on no artifact id"; exit 1 ;;
          esac
"""
DOWNLOAD = f"""      - uses: actions/download-artifact@{PIN} # v8.0.2
        with:
          artifact-ids: ${{{{ needs.build.outputs.assets-id }}}}
          path: release-assets
          digest-mismatch: error
"""
CHECK = """      - name: These are the bytes the build job made
        env:
          SUMS_SHA256: ${{ needs.build.outputs.sums-sha256 }}
        run: |
          printf '%s  SHA256SUMS\\n' "$SUMS_SHA256" > SHA256SUMS.sha256
          ( cd release-assets && sha256sum -c ../SHA256SUMS.sha256 && sha256sum -c SHA256SUMS )
          have=$(cd release-assets && find . -mindepth 1 | sort)
"""
READ_ASSETS = GUARD + DOWNLOAD + CHECK


def _rebuild_job(job: str, runner: str, minutes: int) -> str:
    return f"""  {job}:
    name: rebuild from the pins ({runner})
    runs-on: {runner}
    timeout-minutes: {minutes}
    permissions:
      contents: read
    outputs:
      sums-id: ${{{{ steps.sums.outputs.artifact-id }}}}
      wheel-id: ${{{{ steps.wheel.outputs.artifact-id }}}}
    steps:
      - name: The runner's own tools
        run: |
          uname -srm
          nproc
          ls /proc/sys/fs/binfmt_misc/
          python3 --version
      - uses: astral-sh/setup-uv@{PIN} # v10.3.0
        with:
          enable-cache: false
      - name: Build from the pins
        run: scripts/build.sh
      - id: sums
        uses: actions/upload-artifact@{PIN} # v7.0.2
        with:
          name: rebuild-{runner}
          path: build/artifacts/SHA256SUMS
      - id: wheel
        uses: actions/upload-artifact@{PIN} # v7.0.2
        with:
          name: rebuild-wheel-{runner}
          path: dist/wasi_python-*.whl
"""


def _rebuild_download(job: str, output: str, folder: str, runner: str) -> str:
    return f"""      - uses: actions/download-artifact@{PIN} # v8.0.2
        with:
          artifact-ids: ${{{{ needs.{job}.outputs.{output} }}}}
          path: {folder}/{runner}
          digest-mismatch: error
"""


RELEASE_WORKFLOW = (
    f"""name: release
permissions: {{}}
jobs:
  build:
    runs-on: macos-15
    permissions:
      contents: read
    outputs:
      assets-id: ${{{{ steps.assets.outputs.artifact-id }}}}
      sums-sha256: ${{{{ steps.sums.outputs.sha256 }}}}
    steps:
      - uses: astral-sh/setup-uv@{PIN} # v10.3.0
        with:
          enable-cache: false
      - name: The SHA-256 of SHA256SUMS
        id: sums
        run: echo "sha256=$(shasum -a 256 release-assets/SHA256SUMS | cut -c1-64)" >> "$OUT"
      - id: assets
        uses: actions/upload-artifact@{PIN} # v7.0.2
        with:
          name: release-assets
          path: release-assets/
      - name: What this run checks, signs and publishes
        env:
          ASSETS_ID: ${{{{ steps.assets.outputs.artifact-id }}}}
          ASSETS_DIGEST: ${{{{ steps.assets.outputs.artifact-digest }}}}
        run: |
          echo "release-assets: artifact $ASSETS_ID, digest $ASSETS_DIGEST"
          cat release-assets/SHA256SUMS
"""
    + _rebuild_job("rebuild-linux-arm64", "ubuntu-24.04-arm", 120)
    + _rebuild_job("rebuild-linux-x86-64", "ubuntu-24.04", 120)
    + """  same-bytes:
    needs: [build, rebuild-linux-arm64, rebuild-linux-x86-64]
    runs-on: ubuntu-24.04
    permissions: {}
    steps:
"""
    + READ_ASSETS
    + """      - name: The rebuild jobs handed on artifact ids
        env:
          ARM64_SUMS_ID: ${{ needs.rebuild-linux-arm64.outputs.sums-id }}
          ARM64_WHEEL_ID: ${{ needs.rebuild-linux-arm64.outputs.wheel-id }}
          X86_64_SUMS_ID: ${{ needs.rebuild-linux-x86-64.outputs.sums-id }}
          X86_64_WHEEL_ID: ${{ needs.rebuild-linux-x86-64.outputs.wheel-id }}
        run: |
          for id in "$ARM64_SUMS_ID" "$ARM64_WHEEL_ID" "$X86_64_SUMS_ID" "$X86_64_WHEEL_ID"; do
            case "$id" in
              "" | *[!0-9]*) echo "a rebuild job handed on no artifact id"; exit 1 ;;
            esac
          done
"""
    + _rebuild_download("rebuild-linux-arm64", "sums-id", "rebuilds", "ubuntu-24.04-arm")
    + _rebuild_download("rebuild-linux-arm64", "wheel-id", "rebuilt-wheels", "ubuntu-24.04-arm")
    + _rebuild_download("rebuild-linux-x86-64", "sums-id", "rebuilds", "ubuntu-24.04")
    + _rebuild_download("rebuild-linux-x86-64", "wheel-id", "rebuilt-wheels", "ubuntu-24.04")
    + """      - name: Every rebuild's SHA256SUMS is the set's
        run: |
          sums=set/SHA256SUMS
          for runner in ubuntu-24.04-arm ubuntu-24.04; do
            cmp "$sums" "rebuilds/$runner/SHA256SUMS"
          done
      - name: The wheel is the wheel each host rebuilt
        run: |
          for r in ubuntu-24.04-arm ubuntu-24.04; do
            cmp -s "$wheel" "rebuilt-wheels/$r/$(basename "$wheel")"
          done
  verify:
    needs: build
    permissions:
      contents: read
    steps:
"""
    + READ_ASSETS
    + """  attest:
    if: github.event_name == 'push' && github.ref_type == 'tag'
    needs: [build, verify, same-bytes, gather]
    permissions:
      id-token: write
      attestations: write
      contents: read
    steps:
"""
    + READ_ASSETS
    + f"""      - uses: actions/attest@{PIN} # v4.2.2
        with:
          subject-path: release-assets/*
      - name: verify
        run: |
          gh attestation verify "$a" --repo "$R" \\
            --signer-workflow "$W" --source-ref "$REF" --deny-self-hosted-runners
  publish:
    if: github.event_name == 'push' && github.ref_type == 'tag'
    needs: [build, verify, same-bytes, attest, gather]
    environment: release
    permissions:
      contents: write
    steps:
"""
    + READ_ASSETS
    + """      - name: Create the release
        run: gh release create "$GITHUB_REF_NAME" release-assets/*
  pypi:
    if: github.event_name == 'push' && github.ref_type == 'tag' && vars.PYPI_PUBLISH == 'true'
    needs: [build, publish]
    environment: pypi
    permissions:
      id-token: write
    steps:
"""
    + READ_ASSETS
)


def _in_job(text: str, job: str, old: str, new: str) -> str:
    """The workflow with the first `old` inside `job` replaced by `new`."""
    start = text.index(f"\n  {job}:\n")
    end = text.find("\n  ", start + 1)
    while end != -1 and text[end + 3] == " ":
        end = text.find("\n  ", end + 1)
    end = len(text) if end == -1 else end
    section = text[start:end]
    assert old in section, (job, old)
    return text[:start] + section.replace(old, new, 1) + text[end:]


def test_the_release_workflow_passes_every_release_scan() -> None:
    assert scan.release_binding_errors(RELEASE_WORKFLOW) == []
    assert scan.rebuild_gate_errors(RELEASE_WORKFLOW) == []
    assert scan.release_attestation_errors(RELEASE_WORKFLOW) == []
    assert scan.action_pin_errors(RELEASE_WORKFLOW) == []


REBUILD_GUARD_LOOP = '"$ARM64_SUMS_ID" "$ARM64_WHEEL_ID" "$X86_64_SUMS_ID" "$X86_64_WHEEL_ID"'
ARM_SUMS = "artifact-ids: ${{ needs.rebuild-linux-arm64.outputs.sums-id }}"

# (job, old, new) -> the rules named, one variant per rule and per mutation of the reviews.
BAD_BINDINGS = [
    (("build", "assets-id: ${{ steps.assets.", "assets-id: ${{ steps.other."), {1}),
    (("build", "shasum -a 256 release-assets/SHA256SUMS", "shasum -a 256 dist/x"), {2}),
    (("build", "          cat release-assets/SHA256SUMS", "          true"), {3}),
    *[
        (
            (
                "verify",
                "          path: release-assets\n",
                f"          path: release-assets\n          {key}: x\n",
            ),
            {4},
        )
        for key in scan.NOT_BY_ID
    ],
    (("publish", "release create", "run download x; gh release create"), {4}),
    (
        (
            "publish",
            "      - name: Create the release\n",
            "      - uses: actions/github-script@" + PIN + "\n      - name: Create the release\n",
        ),
        {4},
    ),
    (("verify", "          digest-mismatch: error\n", ""), {5}),
    (("pypi", "    needs: [build, publish]\n", "    needs: [publish]\n"), {6}),
    (("verify", "          path: release-assets\n", "          path: assets\n"), {7}),
    (("pypi", "These are the bytes the build job made", "Some step"), {8}),
    (
        (
            "verify",
            "      - name: These are the bytes the build job made\n",
            "      - name: These are the bytes the build job made\n        shell: bash\n",
        ),
        {9},
    ),
    (("verify", GUARD, ""), {10}),
    # A rebuild id bound, but no longer tested.
    (
        ("same-bytes", REBUILD_GUARD_LOOP, REBUILD_GUARD_LOOP.replace(' "$X86_64_WHEEL_ID"', "")),
        {10},
    ),
    (("verify", 'case "$ASSETS_ID" in', 'case "$OTHER" in'), {10}),
    (("build", 'echo "release-assets: artifact', 'echo "${{ github.ref }}: artifact'), {11}),
    (("publish", "    environment: release\n", ""), {12}),
    (("pypi", "    environment: pypi\n", "    environment: release\n"), {12}),
    (("build", "enable-cache: false", "enable-cache: true"), {13}),
    (("verify", "      contents: read\n", "      contents: write\n"), {14}),
    (("same-bytes", "    permissions: {}\n", ""), {14}),
    # The rebuild guard, which has no twin, told to carry on.
    (
        (
            "same-bytes",
            "      - name: The rebuild jobs handed on artifact ids\n",
            "      - name: The rebuild jobs handed on artifact ids\n"
            "        continue-on-error: true\n",
        ),
        {15, 17},
    ),
    # publish's check step told to carry on.
    (
        (
            "publish",
            "      - name: These are the bytes the build job made\n",
            "      - name: These are the bytes the build job made\n"
            "        continue-on-error: true\n",
        ),
        {9, 15, 17},
    ),
    (
        (
            "attest",
            DOWNLOAD.splitlines()[0] + "\n",
            DOWNLOAD.splitlines()[0] + "\n        if: always()\n",
        ),
        {15},
    ),
    # Attest fetches a rebuild's SHA256SUMS into release-assets after its
    # check, guarded and by id, with that job added to its needs.
    (
        (
            "attest",
            "      - uses: actions/attest@",
            "      - name: The rebuild handed on an id\n"
            "        env:\n"
            "          R_ID: ${{ needs.rebuild-linux-arm64.outputs.sums-id }}\n"
            "        run: |\n"
            '          case "$R_ID" in\n'
            '            "" | *[!0-9]*) echo "no id"; exit 1 ;;\n'
            "          esac\n"
            f"      - uses: actions/download-artifact@{PIN} # v8.0.2\n"
            "        with:\n"
            "          artifact-ids: ${{ needs.rebuild-linux-arm64.outputs.sums-id }}\n"
            "          path: release-assets\n"
            "          digest-mismatch: error\n"
            "      - uses: actions/attest@",
        ),
        {6, 16},
    ),
    # The same move in same-bytes: a rebuild's wheel into release-assets.
    (
        (
            "same-bytes",
            "          path: rebuilt-wheels/ubuntu-24.04-arm\n",
            "          path: release-assets\n",
        ),
        {16},
    ),
    # The gate around pypi, and carrying on past a failure.
    (("pypi", "    needs: [build, publish]\n", "    needs: [build]\n"), {18}),
    (("pypi", "    if: github.event_name", "    if: always() && github.event_name"), {18}),
    (
        (
            "pypi",
            "    if: github.event_name == 'push' && github.ref_type == 'tag' && vars",
            "    if: vars",
        ),
        {18},
    ),
    (("verify", "    needs: build\n", "    needs: build\n    continue-on-error: true\n"), {17}),
    (
        (
            "build",
            "      - name: The SHA-256 of SHA256SUMS\n",
            "      - name: The SHA-256 of SHA256SUMS\n        continue-on-error: true\n",
        ),
        {17},
    ),
]


def _rules(errors: list[str]) -> set[int]:
    return {int(re.match(r"rule (\d+):", e)[1]) for e in errors}


@pytest.mark.parametrize(
    ("change", "rules"), BAD_BINDINGS, ids=[f"{c[0]}:{c[1][:40]}" for c, _ in BAD_BINDINGS]
)
def test_release_binding_scan_names_each_breach(change, rules) -> None:
    errors = scan.release_binding_errors(_in_job(RELEASE_WORKFLOW, *change))
    assert _rules(errors) == rules, errors


def test_release_binding_scan_reads_with_not_the_display_name() -> None:
    renamed = _in_job(
        RELEASE_WORKFLOW,
        "verify",
        "      - uses: actions/download-artifact@",
        "      - name: release-assets\n        uses: actions/download-artifact@",
    )
    assert scan.release_binding_errors(renamed) == []


# Rule 16 reads `path:` as a
# path, so another spelling of release-assets in same-bytes is the plain spelling's breach.
OTHER_SPELLINGS = [
    "./release-assets",
    "rebuilds/../release-assets",
    "${{ github.workspace }}/release-assets",
    "${{github.workspace}}/./release-assets/",
    "./release-assets/wheel",
    # A quoted value, as a YAML formatter may write it, and a doubled slash.
    '"release-assets"',
    "'release-assets'",
    '"./release-assets"',
    "${{ github.workspace }}//release-assets",
]


@pytest.mark.parametrize("spelling", OTHER_SPELLINGS)
def test_rule_16_reads_the_download_path_as_a_path(spelling) -> None:
    old = "          path: rebuilt-wheels/ubuntu-24.04-arm\n"
    changed = _in_job(RELEASE_WORKFLOW, "same-bytes", old, f"          path: {spelling}\n")
    assert _rules(scan.release_binding_errors(changed)) == {16}


@pytest.mark.parametrize(
    "spelling",
    [
        "./rebuilt-wheels/ubuntu-24.04-arm",
        "${{ github.workspace }}/rebuilt-wheels/ubuntu-24.04-arm",
        '"rebuilt-wheels/ubuntu-24.04-arm"',
    ],
)
def test_rule_16_lets_another_spelling_of_a_rebuild_folder_through(spelling) -> None:
    old = "          path: rebuilt-wheels/ubuntu-24.04-arm\n"
    changed = _in_job(RELEASE_WORKFLOW, "same-bytes", old, f"          path: {spelling}\n")
    assert scan.release_binding_errors(changed) == []


def test_the_workflow_level_permissions_must_be_empty() -> None:
    changed = RELEASE_WORKFLOW.replace(
        "permissions: {}\njobs:", "permissions:\n  contents: read\njobs:", 1
    )
    assert _rules(scan.release_binding_errors(changed)) == {14}


def test_a_step_script_is_read_exactly_and_its_absence_raises() -> None:
    script = scan.workflow_step_script(RELEASE_WORKFLOW, "attest", scan.CHECK_STEP)
    assert script.startswith("printf '%s  SHA256SUMS\\n'") and "find . -mindepth 1" in script
    with pytest.raises(LookupError):
        scan.workflow_step_script(RELEASE_WORKFLOW, "attest", "No such step")


def test_actions_must_be_pinned_by_a_full_commit() -> None:
    assert scan.action_pin_errors("      - uses: ./local\n") == []
    for ref in ("actions/checkout@v4", "actions/checkout@3d3c42e", "docker://alpine"):
        assert scan.action_pin_errors(f"      - uses: {ref} # x\n") == [
            f"{ref}: not pinned by a full commit"
        ]


def test_every_fetched_name_must_be_pinned(work) -> None:
    script = work / "00_download.sh"
    script.write_text("get https://e.org/a/x.tar.gz x.tar.gz\nresearch https://e.org/b/y.zip\n")
    assert scan.unpinned_fetch_errors(script, ["x.tar.gz", "y.zip"]) == []
    assert scan.unpinned_fetch_errors(script, ["x.tar.gz"]) == [
        "y.zip: fetched, but not pinned in downloads/SHA256SUMS"
    ]


# (job, old, new) -> the first breach the rebuild gate names.
BAD_REBUILDS = [
    (
        ("rebuild-linux-arm64", "rebuild-linux-arm64:", "rebuild-arm64:"),
        "no rebuild-linux-arm64 job",
    ),
    (("same-bytes", "same-bytes:", "same-bits:"), "no same-bytes job"),
    (
        ("rebuild-linux-x86-64", "    runs-on: ubuntu-24.04\n", "    runs-on: ubuntu-24.04-arm\n"),
        "rebuild-linux-x86-64 does not run on ubuntu-24.04",
    ),
    (
        ("rebuild-linux-arm64", "    timeout-minutes: 120\n", "    timeout-minutes: 360\n"),
        "rebuild-linux-arm64's timeout-minutes is not 120",
    ),
    (
        ("rebuild-linux-x86-64", "    timeout-minutes: 120\n", "    timeout-minutes: 360\n"),
        "rebuild-linux-x86-64's timeout-minutes is not 120",
    ),
    (
        ("rebuild-linux-arm64", "          nproc\n", ""),
        "rebuild-linux-arm64's tools step does not print nproc",
    ),
    (
        ("rebuild-linux-x86-64", "          ls /proc/sys/fs/binfmt_misc/\n", ""),
        "rebuild-linux-x86-64's tools step does not print binfmt_misc",
    ),
    (
        ("rebuild-linux-arm64", "run: scripts/build.sh", "run: echo"),
        "rebuild-linux-arm64 does not run scripts/build.sh",
    ),
    (
        ("rebuild-linux-x86-64", "name: rebuild-ubuntu-24.04\n", "name: rebuild\n"),
        "rebuild-linux-x86-64 does not upload build/artifacts/SHA256SUMS",
    ),
    (
        ("rebuild-linux-arm64", "      - id: wheel\n", "      - id: wheels\n"),
        "rebuild-linux-arm64 does not upload dist/wasi_python-*.whl",
    ),
    (
        ("rebuild-linux-x86-64", "wheel-id: ${{ steps.wheel.", "wheel-id: ${{ steps.sums."),
        "rebuild-linux-x86-64's outputs are not",
    ),
    (
        (
            "rebuild-linux-x86-64",
            "          uname -srm\n",
            "          uname -srm\n          df -h\n",
        ),
        "the rebuild jobs differ",
    ),
    (
        (
            "rebuild-linux-arm64",
            "    permissions:\n",
            "    if: github.ref_type == 'tag'\n    permissions:\n",
        ),
        "rebuild-linux-arm64 has a job-level if:",
    ),
    (
        (
            "same-bytes",
            "    permissions: {}\n",
            "    permissions: {}\n    continue-on-error: true\n",
        ),
        "same-bytes has a job-level continue-on-error:",
    ),
    (
        ("same-bytes", "    permissions: {}\n", "    permissions:\n      id-token: write\n"),
        "same-bytes's permissions are more than",
    ),
    (
        ("same-bytes", "rebuild-linux-arm64, rebuild-linux-x86-64]", "rebuild-linux-arm64]"),
        "same-bytes does not need build and both",
    ),
    (
        ("same-bytes", '            cmp "$sums"', '            diff "$sums"'),
        "same-bytes does not compare",
    ),
    # The x86_64 job's id downloaded into the arm64 job's folder.
    (
        ("same-bytes", ARM_SUMS, ARM_SUMS.replace("arm64", "x86-64")),
        "same-bytes does not download rebuild-linux-arm64's SHA256SUMS by id into "
        "rebuilds/ubuntu-24.04-arm",
    ),
    (
        ("same-bytes", "path: rebuilt-wheels/ubuntu-24.04\n", "path: elsewhere\n"),
        "same-bytes does not download rebuild-linux-x86-64's rebuilt wheel",
    ),
    (
        (
            "same-bytes",
            "for runner in ubuntu-24.04-arm ubuntu-24.04;",
            "for runner in ubuntu-24.04;",
        ),
        "same-bytes' SHA256SUMS loop does not run over ubuntu-24.04-arm",
    ),
    (
        ("same-bytes", "for r in ubuntu-24.04-arm ubuntu-24.04;", "for r in ubuntu-24.04-arm;"),
        "same-bytes' wheel loop does not run over ubuntu-24.04",
    ),
    (("same-bytes", '/SHA256SUMS"\n', '/SHA256SUMS" || true\n'), "a step of same-bytes swallows"),
    # The runner's own python3 is named in the log.
    (
        ("rebuild-linux-arm64", "          python3 --version\n", ""),
        "rebuild-linux-arm64's tools step does not print python3 --version",
    ),
    (
        (
            "attest",
            "    needs: [build, verify, same-bytes, gather]\n",
            "    needs: [build, verify, gather]\n",
        ),
        "attest does not need same-bytes",
    ),
    (
        ("publish", "same-bytes, attest, gather]", "attest, gather]"),
        "publish does not need same-bytes",
    ),
]


@pytest.mark.parametrize(("change", "error"), BAD_REBUILDS, ids=[e for _, e in BAD_REBUILDS])
def test_rebuild_gate_scan_names_each_breach(change, error) -> None:
    errors = scan.rebuild_gate_errors(_in_job(RELEASE_WORKFLOW, *change))
    assert errors and errors[0].startswith(error), errors


# Every host compiles with its own SDK; X carries the five emulation names, the
# fallback, switched off (its COMPILER_SDK_DIR is its own SDK; B's would throw the switch).
COMPILER_CONF = """PYTHON_VERSION=3.15.0
A_WASI_SDK_DIR=sdk-a-arm64
A_COMPILER_SDK_DIR=sdk-a-arm64
B_WASI_SDK_DIR=sdk-b-arm64
B_COMPILER_SDK_DIR=sdk-b-arm64
X_WASI_SDK_DIR=sdk-x
X_COMPILER_SDK_DIR=sdk-x
X_EMULATOR_DEB=qemu.deb
X_AARCH64_LIBC_DEB=libc.deb
X_AARCH64_LIBSTDCXX_DEB=libstdcxx.deb
X_AARCH64_LIBGCC_DEB=libgcc.deb
X_AARCH64_LIBTINFO_DEB=libtinfo.deb
"""
COMPILER_DOWNLOAD = """case "$HOST_KEY" in
  A)
    get https://x/sdk-a-arm64.tar.gz sdk-a-arm64.tar.gz
    ;;
  B)
    get https://x/sdk-b-arm64.tar.gz sdk-b-arm64.tar.gz
    ;;
  X)
    get https://x/sdk-x.tar.gz sdk-x.tar.gz
    get https://x/sdk-b-arm64.tar.gz sdk-b-arm64.tar.gz
    get https://x/qemu.deb qemu.deb
    get https://x/libc.deb libc.deb
    get https://x/libstdcxx.deb libstdcxx.deb
    get https://x/libgcc.deb libgcc.deb
    get https://x/libtinfo.deb libtinfo.deb
    ;;
esac
"""
COMPILER_PINS = [
    "sdk-a-arm64.tar.gz",
    "sdk-b-arm64.tar.gz",
    "sdk-x.tar.gz",
    *(f"{n}.deb" for n in ("qemu", "libc", "libstdcxx", "libgcc", "libtinfo")),
]
COMPILER_STEP_10 = """cp "$HERE/scripts/clang-emulated" "$CSDK/bin/clang-emulated"
: > "$T/aarch64-root/etc/ld.so.cache"
"$SDK/bin/clang" -v 2>&1 | grep -F "InstalledDir: $CSDK/bin"
"$SDK/bin/clang-cpp" "$probe"
"$T/emulator/qemu-aarch64" -strace -L "$T/aarch64-root" "$real" --version
"""
COMPILER_LAUNCHER = """for v in $(env | sed -n 's/^\\(QEMU_[A-Za-z0-9_]*\\)=.*/\\1/p'); do
  unset "$v"
done
case "$(basename "$0")" in
  clang) mode="";;
  clang++) mode="--driver-mode=g++";;
  clang-cpp) mode="--driver-mode=cpp";;
esac
exec "$emu" -L "$root" -U LD_PRELOAD -U LD_LIBRARY_PATH -U LD_AUDIT -0 "$A/clang-emulated" "$@"
"""
COMPILER_TEXTS = {
    "conf": COMPILER_CONF,
    "download": COMPILER_DOWNLOAD,
    "step": COMPILER_STEP_10,
    "launcher": COMPILER_LAUNCHER,
}


def _compiler_table(**changed) -> list[str]:
    texts = {**COMPILER_TEXTS, "pins": COMPILER_PINS, **changed}
    return scan.compiler_table_errors(
        texts["conf"], texts["download"], texts["pins"], texts["step"], texts["launcher"]
    )


BAD_COMPILERS = [
    ("conf", ("A_COMPILER_SDK_DIR=sdk-a-arm64\n", ""), "line.conf: no A_COMPILER_SDK_DIR"),
    ("conf", ("PYTHON", "COMPILER_SDK_DIR=sdk-a-arm64\nPYTHON"), "line.conf: COMPILER_SDK_DIR is"),
    (
        "conf",
        ("B_COMPILER_SDK_DIR=sdk-b-arm64", "B_COMPILER_SDK_DIR=sdk-a-arm64"),
        "B compiles with another host's SDK but lacks the five emulation names",
    ),
    (
        "conf",
        ("A_COMPILER_SDK_DIR=sdk-a-arm64\n", "A_COMPILER_SDK_DIR=sdk-a-arm64\nA_EMULATOR_DEB=q\n"),
        "A and X both carry the emulation names",
    ),
    (
        "conf",
        ("X_AARCH64_LIBTINFO_DEB=libtinfo.deb\n", ""),
        "X has 4 of the five emulation names",
    ),
    (
        "conf",
        ("X_COMPILER_SDK_DIR=sdk-x", "X_COMPILER_SDK_DIR=sdk-z"),
        "X_COMPILER_SDK_DIR: sdk-z is no host's own WASI_SDK_DIR",
    ),
    ("pins", ("qemu.deb", "other.deb"), "X_EMULATOR_DEB: qemu.deb is not pinned"),
    (
        "download",
        ("    get https://x/libgcc.deb libgcc.deb\n", ""),
        "X_AARCH64_LIBGCC_DEB: libgcc.deb is not fetched in the X branch",
    ),
    (
        "download",
        (
            "sdk-b-arm64.tar.gz\n    get https://x/qemu",
            "sdk-b-arm64.tar.gz.old\n    get https://x/qemu",
        ),
        "X's branch fetches no other host's SDK (the fallback's compiler)",
    ),
    ("step", ("/clang-emulated", "/launcher"), "10_tools.sh does not name clang-emulated"),
    ("step", ("aarch64-root", "guest-root"), "10_tools.sh does not name aarch64-root"),
    ("step", ("etc/ld.so.cache", "etc/cache"), "10_tools.sh does not name ld.so.cache"),
    ("step", ("InstalledDir", "Dir"), "10_tools.sh does not name InstalledDir"),
    ("step", ("bin/clang-cpp", "bin/cpp"), "10_tools.sh does not name clang-cpp"),
    ("step", (" -strace ", " "), "10_tools.sh does not trace the guest's loader"),
    ("launcher", ("-U LD_PRELOAD ", ""), "scripts/clang-emulated does not pass -U LD_PRELOAD"),
    (
        "launcher",
        ("-U LD_LIBRARY_PATH ", ""),
        "scripts/clang-emulated does not pass -U LD_LIBRARY_PATH",
    ),
    ("launcher", ("-U LD_AUDIT ", ""), "scripts/clang-emulated does not pass -U LD_AUDIT"),
    ("launcher", ('unset "$v"', ":"), "scripts/clang-emulated does not unset the QEMU_"),
    (
        "launcher",
        ('  clang-cpp) mode="--driver-mode=cpp";;\n', ""),
        "scripts/clang-emulated does not map clang-cpp to --driver-mode=cpp",
    ),
    (
        "launcher",
        ("--driver-mode=g++", "--driver-mode=cpp"),
        "scripts/clang-emulated does not map clang++ to --driver-mode=g++",
    ),
    (
        "launcher",
        ('  clang) mode="";;', '  clang) mode="--driver-mode=gcc";;'),
        "scripts/clang-emulated does not map clang to no mode",
    ),
]


def test_compiler_table_passes_a_whole_table() -> None:
    assert _compiler_table() == []


def test_compiler_table_passes_with_the_switch_thrown() -> None:
    """X compiling with B's SDK under the emulator, the five names present,
    is the fallback's legal second position."""
    thrown = COMPILER_CONF.replace("X_COMPILER_SDK_DIR=sdk-x", "X_COMPILER_SDK_DIR=sdk-b-arm64")
    assert _compiler_table(conf=thrown) == []


def test_compiler_table_needs_one_fallback() -> None:
    gone = "".join(line + "\n" for line in COMPILER_CONF.splitlines() if "_DEB=" not in line)
    errors = _compiler_table(conf=gone)
    assert errors == ["no host key carries the emulation names (the fallback is gone)"], errors


@pytest.mark.parametrize(
    ("where", "change", "error"), BAD_COMPILERS, ids=[e for *_, e in BAD_COMPILERS]
)
def test_compiler_table_names_each_breach(where, change, error) -> None:
    old, new = change
    if where == "pins":
        errors = _compiler_table(pins=[new if p == old else p for p in COMPILER_PINS])
    else:
        assert old in COMPILER_TEXTS[where], old  # every occurrence is changed
        errors = _compiler_table(**{where: COMPILER_TEXTS[where].replace(old, new)})
    assert errors and errors[0].startswith(error), errors


def test_compiler_table_needs_the_launcher_and_reads_code_not_comments(work) -> None:
    assert _compiler_table(launcher=None) == ["scripts/clang-emulated is missing"]
    commented = "".join(f"# {line}\n" for line in COMPILER_STEP_10.splitlines())
    step = write(work, "10_tools.sh", "set -eu\n" + commented)
    assert scan.code_text(step) == "set -eu"
    assert scan.code_text(work / "missing") is None
    errors = _compiler_table(step=scan.code_text(step))
    assert errors[0] == "10_tools.sh does not name clang-emulated", errors


def test_a_name_bound_twice_at_module_level_is_found(work) -> None:
    cases = {
        "tests/checks/a.py": 'A = "one"\n\ndef f():\n    pass\n\nA = "two"\n',
        "tests/checks/b.py": "def f():\n    pass\n\ndef f():\n    pass\n",
        "tests/checks/c.py": "def f():\n    pass\n\nclass f:\n    pass\n",
        "tests/checks/d.py": "script = 1\nscript = 2\n",
        "tests/checks/e.py": "A, B = 1, 2\n*C, A = [3, 4]\n",
        "tests/checks/f.py": "import os as A\nA = 1\n",
        "tests/checks/g.py": "x: int = 1\nx: int = 2\n",
    }
    files = [write(work, name, text) for name, text in cases.items()]
    hits = [h.split(":")[0] for h in scan.duplicate_name_hits(files, work)]
    assert hits == sorted(cases)


def test_what_may_be_bound_twice(work) -> None:
    files = [
        write(work, "tests/checks/a.py", "A = 1\n\ndef f():\n    A = 2\n    return A\n"),
        write(work, "tests/jobs/b.py", "blob = 1\nblob = blob + 1\nimport os\nimport os\n"),
        write(work, "tests/checks/c.py", "A = 1\nA += 1\n"),
        write(work, "tests/checks/d.py", "if X:\n    A = 1\nelse:\n    A = 2\n"),
        write(
            work,
            "tests/checks/e.py",
            "from typing import overload\n@overload\ndef f(x: int) -> int: ...\n"
            "@overload\ndef f(x: str) -> str: ...\ndef f(x): return x\n",
        ),
    ]
    assert scan.duplicate_name_hits(files, work) == []
    job = write(work, "tests/jobs/z.py", "LIMIT = 1\nLIMIT = 2\n")  # a constant, even in a job
    assert scan.duplicate_name_hits([job], work) == ["tests/jobs/z.py:2: LIMIT (first bound at 1)"]


# The process's state has one owner: no lock and no mutable at module or class level elsewhere.

LOCKS_MODULE = """\
import threading
from threading import Condition

a = threading.Lock()
b: threading.RLock = threading.RLock()
c = Condition()


class Ticker:
    _cond = threading.Condition()
    _count = 0  # an int is not a lock

    def __init__(self):
        self.lock = threading.Lock()  # an instance attribute: not at class level


def f():
    guard = threading.Lock()  # inside a function: not at module level
    return guard
"""

MUTABLES_MODULE = """\
import collections, itertools, queue, threading, weakref

__all__ = ["a"]
TABLE = {"k": 1}  # an upper-case display is a table that is only read
NAMES = ["a", "b"]
KINDS = {"x", "y"}
a = {}
b = []
c = set()
d = {k: 1 for k in "ab"}
e = [k for k in "ab"]
f = {k for k in "ab"}
g = dict()
h = list()
i = bytearray()
j = collections.deque()
k = collections.defaultdict(int)
l = collections.OrderedDict()
m = weakref.WeakSet()
n = weakref.WeakValueDictionary()
o = weakref.WeakKeyDictionary()
p = queue.SimpleQueue()
q = queue.Queue()
r = itertools.count(1)
s = threading.local()
t, u = [], {}
v: dict[str, int] = {}
w: dict[str, int]
PAIR = (1, 2)
FROZEN = frozenset({1})
SENTINEL = object()
UPPER_CALL = dict()  # an upper-case call is still a mutable: only a display is a table


class Record:
    _fields_ = [("x", int)]  # a ctypes declaration, read once
    table = {}


def g():
    cache = {}
    return cache
"""


def test_a_lock_at_module_or_class_level_is_found(work) -> None:
    p = write(work, "src/wasi_python/_mod.py", LOCKS_MODULE)
    assert scan.module_lock_hits([p], work) == [
        "src/wasi_python/_mod.py:4: a (Lock)",
        "src/wasi_python/_mod.py:5: b (RLock)",
        "src/wasi_python/_mod.py:6: c (Condition)",
        "src/wasi_python/_mod.py:10: Ticker._cond (Condition)",
    ]
    assert scan.module_lock_hits([write(work, "src/notes.txt", "x = Lock()\n")], work) == []


def test_a_mutable_at_module_or_class_level_is_found_and_the_exceptions_are_not(work) -> None:
    p = write(work, "src/wasi_python/_mod.py", MUTABLES_MODULE)
    hits = scan.module_mutable_hits([p], work)
    names = [h.split(": ", 1)[1] for h in hits]
    assert names == [
        "a (Dict)",
        "b (List)",
        "c (set)",
        "d (DictComp)",
        "e (ListComp)",
        "f (SetComp)",
        "g (dict)",
        "h (list)",
        "i (bytearray)",
        "j (deque)",
        "k (defaultdict)",
        "l (OrderedDict)",
        "m (WeakSet)",
        "n (WeakValueDictionary)",
        "o (WeakKeyDictionary)",
        "p (SimpleQueue)",
        "q (Queue)",
        "r (count)",
        "s (local)",
        "t (List)",
        "u (Dict)",
        "v (Dict)",
        "UPPER_CALL (dict)",
        "Record.table (Dict)",
    ], hits
    assert hits[0] == "src/wasi_python/_mod.py:7: a (Dict)"


# Only the engine seam touches wasmtime-py's private API, and the debt is documented.
# Every fixture line below is built by concatenation, so this file is not a hit of the rule.

FFI = "wasmtime." + "_ffi"  # the private module's dotted name, never spelled whole here


def test_private_engine_hits_each_alternation_once_and_the_exempt_files_not(work) -> None:
    lines = [
        "from wasmtime import Store, _" + "ffi",
        "import wasmtime." + "_bindings",
        "context = caller." + "_context()",
        "handle = exports[name]." + "_func",
        "raised = Trap." + "_from" + "_ptr(trap)",
        "address = store." + "ptr()",
        "copy = self." + "_context()",  # the tool host's own method, not wasmtime-py's
        "sym = '_GLOBAL__sub_I_highs_bindings.cpp'",  # no `wasmtime.` prefix
        "x = 1",
    ]
    write(work, "src/wasi_python/runner.py", "\n".join(lines) + "\n")
    write(work, "src/wasi_python/_wasmtime_ffi.py", lines[0] + "\n")
    write(work, "tests/unit/test_wasmtime_ffi.py", lines[1] + "\n")
    write(work, "tests/harness/other.txt", lines[2] + "\n")  # not a .py file
    exempt = (scan.ENGINE_SEAM, scan.ENGINE_SEAM_UNIT)
    hits = scan.private_engine_hits(work, ["src", "tests"], exempt)
    assert hits == [f"src/wasi_python/runner.py:{n}: {lines[n - 1]}" for n in range(1, 7)]
    own = ["tests/harness/scan.py", "tests/unit/test_scan.py"]
    real = scan.private_engine_hits(paths.REPO, own, ())
    assert real == [], real  # the rule's own files avoid the rule


ADAPTER = f'''"""The seam.

- `{FFI}.alpha` -> `Store.alpha`
- `wasmtime.Store.beta` -> a public identity
- `{FFI}.gamma` (optional) -> `Config.gamma`
"""

NEEDED: tuple[tuple[str, str], ...] = (("{FFI}", "alpha"), ("wasmtime.Store", "beta"))
OPTIONAL: tuple[tuple[str, str], ...] = (("{FFI}", "gamma"),)
'''

SHEET = f"""# A sheet

## The facts

| not | a binding row under this heading |
|---|---|
| `{FFI}.elsewhere` | not under the table's heading |

## The bindings

| binding | C API function |
|---|---|
| `{FFI}.alpha` | `alpha` |
| `wasmtime.Store.beta` | `beta` |
| `{FFI}.gamma` (optional) | `gamma` |

## Landed

| `{FFI}.old` | landed, so not a row of the table |
"""


def test_private_api_debt_agrees_and_names_each_drift(work) -> None:
    adapter = write(work, "src/wasi_python/_wasmtime_ffi.py", ADAPTER)
    sheet = write(work, "facts.md", SHEET)
    assert scan.private_api_debt_errors(adapter, sheet) == []
    assert scan.sheet_bindings(SHEET) == [f"{FFI}.alpha", "wasmtime.Store.beta", f"{FFI}.gamma"]
    short = write(work, "short.md", SHEET.replace("| `wasmtime.Store.beta` | `beta` |\n", ""))
    assert scan.private_api_debt_errors(adapter, short) == [
        "wasmtime.Store.beta: no row of the sheet's table"
    ]
    extra = write(work, "extra.md", SHEET.replace("## Landed", f"| `{FFI}.delta` | d |\n## Landed"))
    assert scan.private_api_debt_errors(adapter, extra) == [
        f"{FFI}.delta: a row naming no entry of NEEDED or OPTIONAL"
    ]
    quiet = write(work, "quiet.py", ADAPTER.replace(f"- `{FFI}.alpha` -> `Store.alpha`\n", ""))
    assert scan.private_api_debt_errors(quiet, sheet) == [
        f"{FFI}.alpha: not named in the adapter's docstring"
    ]
    computed = write(work, "computed.py", ADAPTER.replace(f'(("{FFI}", "gamma"),)', "tuple(x)"))
    assert scan.private_api_debt_errors(computed, sheet) == [
        "computed.py: OPTIONAL is not a tuple literal",
        f"{FFI}.gamma: a row naming no entry of NEEDED or OPTIONAL",
    ]
    assert scan.private_api_debt_errors(work / "none.py", sheet) == ["none.py does not exist"]


# Every compile contracts nothing.
def test_fp_override_names_the_family_as_whole_tokens() -> None:
    assert scan.fp_override("-ffp-contract=off") is None
    for tok in (
        "-ffp-contract=on",
        "-ffp-contract=fast",
        "-ffp-model=precise",
        "-ffast-math",
        "-Ofast",
        "-funsafe-math-optimizations",
        "--no-default-config",
        "--config",
        "--config=other.cfg",
    ):
        assert scan.fp_override(tok) == tok, tok
    for tok in (
        "-O3",
        "-ffp-contract",
        "--configure",
        "-Ofastest",
        "config",
        "--no-default-configs",
    ):
        assert scan.fp_override(tok) is None, tok
    assert scan.fp_hits("clang -O3 '-ffp-model=precise' -c x.c") == ["-ffp-model=precise"]
    assert scan.fp_hits("wasmtime run --dir a::/ --config x.toml") == ["--config"]
    # A flag inside a quoted multi-flag string, or in NAME=-flag.
    eh = (
        'CXX_EH="-fwasm-exceptions -mllvm -wasm-use-legacy-eh=false'
        ' -fexceptions -ffp-model=precise"'
    )
    assert scan.fp_hits(eh) == ["-ffp-model=precise"]
    assert scan.fp_hits("CFLAGS=-ffast-math") == ["-ffast-math"]
    assert scan.fp_hits('SQLITE_OPTS="-DSQLITE_THREADSAFE=0 -DSQLITE_MAX_MMAP_SIZE=0"') == []
    assert scan.fp_hits("clean $CC -O2 -D_FILE_OFFSET_BITS=64 -c a.c") == []


MAKEFILE = """CC=\t\t/t/wasi-sdk/bin/clang
CFLAGS_NODIST=\t-std=c11 -fvisibility=hidden
PY_STDMODULE_CFLAGS= $(PY_CORE_CFLAGS)
HOSTRUNNER= /t/wasmtime run --argv0 /x/python.wasm --dir /x::/ --config /x/wasmtime.toml
PYTHON_FOR_BUILD=_PYTHON_HOSTRUNNER='/t/wasmtime run --config /x/wasmtime.toml' /x/python.exe
MODULE__SQLITE3_CFLAGS=-I$(srcdir)/Modules/_sqlite
all:
\t$(CC) $(CFLAGS) -c a.c -o a.o
\t/t/wasmtime run --config /x/wasmtime.toml ./python.wasm
"""


def test_fp_makefile_scan_reads_compiler_lines_and_flag_variables_only() -> None:
    hits, read = scan.fp_makefile_hits(MAKEFILE)
    assert hits == [] and read == 5, (
        hits,
        read,
    )  # CC, CFLAGS_NODIST, PY_STDMODULE_CFLAGS, MODULE_, $(CC)
    hits, _ = scan.fp_makefile_hits(MAKEFILE.replace("-std=c11", "-std=c11 -ffast-math"))
    assert hits == ["CFLAGS_NODIST: -ffast-math"], hits
    hits, _ = scan.fp_makefile_hits(MAKEFILE.replace("$(CFLAGS) -c", "$(CFLAGS) --config x.cfg -c"))
    assert hits == ["recipe line: --config"], hits
    joined = MAKEFILE.replace("-fvisibility=hidden", "\\\n\t-fvisibility=hidden -ffp-contract=on")
    hits, _ = scan.fp_makefile_hits(joined)
    assert hits == ["CFLAGS_NODIST: -ffp-contract=on"], hits
    hits, read = scan.fp_command_file_hits(
        "/t/bin/clang --target=wasm32-wasip1 -O3 -c a.c\nwasmtime run --config x\n"
    )
    assert hits == [] and read == 1
    # Automake's COMPILE variable runs the compiler by its value.
    automake = (
        "COMPILE = $(CC) $(DEFS) $(DEFAULT_INCLUDES) $(AM_CFLAGS) $(CFLAGS)\n"
        "all:\n\t$(AM_V_CC)$(COMPILE) -c -o a.o a.c\n"
    )
    hits, read = scan.fp_makefile_hits(automake)
    assert hits == [] and read == 1, (hits, read)  # COMPILE by its value; the recipe line is not
    hits, _ = scan.fp_makefile_hits(automake.replace("$(DEFS)", "$(DEFS) -Ofast"))
    assert hits == ["COMPILE: -Ofast"], hits


def test_fp_record_scan_requires_every_listed_record_and_lists_every_record(work) -> None:
    build = work / "build"
    record = (
        '[{"directory": "/b", "command": "/t/bin/clang -O3 -c a.c -o a.o", '
        '"file": "a.c", "output": "a.o"}]'
    )
    for name in scan.MESON_BUILDS:
        write(build, f"{name}/compile_commands.json", record)
    for rel in scan.AUTOCONF_MAKEFILES:
        write(build, rel, MAKEFILE)
    write(build, "Python-3.15.0/cross-build/wasm32-wasip1/Makefile", MAKEFILE)
    write(build, "link/make-n.txt", "/t/bin/clang -O3 -c a.c -o a.o\n")
    write(
        build,
        "link/reactor-commands.txt",
        "/t/bin/clang -O3 -c r.c -o r.o\n/t/bin/clang -o python.wasm r.o\n",
    )
    errors, read = scan.fp_record_errors(work)
    assert errors == [], errors
    assert len(read) == len(scan.MESON_BUILDS) + len(scan.AUTOCONF_MAKEFILES) + 1 + len(
        scan.LINK_RECORDS
    )
    assert read[0] == "contourpy-build/compile_commands.json: 1 commands"  # the first, sorted
    # A listed record missing; an unlisted record present; a banned option on one command.
    (build / "pandas-build" / "compile_commands.json").unlink()
    errors, _ = scan.fp_record_errors(work)
    assert errors == ["pandas-build/compile_commands.json is missing (listed in MESON_BUILDS)"], (
        errors
    )
    write(build, "pandas-build/compile_commands.json", record)
    write(build, "extra-build/compile_commands.json", record)
    errors, _ = scan.fp_record_errors(work)
    assert errors == ["extra-build/compile_commands.json is not listed in MESON_BUILDS"], errors
    (build / "extra-build" / "compile_commands.json").unlink()
    write(
        build, "numpy-build/compile_commands.json", record.replace("-O3", "-O3 -ffp-model=precise")
    )
    errors, _ = scan.fp_record_errors(work)
    assert errors == ["numpy-build: a.c: -ffp-model=precise"], errors
    write(build, "numpy-build/compile_commands.json", record)
    write(build, "link/make-n.txt", "/t/bin/clang -O3 -Ofast -c a.c -o a.o\n")
    errors, _ = scan.fp_record_errors(work)
    assert errors == ["link/make-n.txt: -Ofast"], errors


def test_fp_record_scan_without_any_record(work) -> None:
    errors, read = scan.fp_record_errors(work)
    assert errors == ["no compile record under build/ (build first)"] and read == []


def test_fp_pragmas_are_found_in_source_trees(work) -> None:
    tree = work / "build" / "lib-1.0"
    write(tree, "a.c", "double f(double a, double b, double c) { return a * b + c; }\n")
    write(tree, "b.c", "#pragma STDC FP_CONTRACT ON\ndouble g(void) { return 0; }\n")
    write(tree, "c.cpp", "#pragma clang fp contract(fast)\n")
    write(tree, "d.c", "#pragma clang fp contract(off)\n#pragma STDC FP_CONTRACT OFF\n")
    write(tree, "e.txt", "#pragma STDC FP_CONTRACT ON\n")
    hits = scan.fp_pragma_hits([tree])
    assert hits == [
        "lib-1.0/b.c: a pragma turns contraction on",
        "lib-1.0/c.cpp: a pragma turns contraction on",
    ], hits
    # The project's own C under recipes/, force-included headers too.
    recipes = work / "recipes"
    write(recipes, "npy_rename.h", "#define npy_x wp_npy_x\n#pragma clang fp contract(fast)\n")
    write(recipes, "reactor_main.c", "#pragma STDC FP_CONTRACT ON\nint main(void) { return 0; }\n")
    write(recipes, "patches/numpy-2.5.2/0001.patch", "+#pragma STDC FP_CONTRACT ON\n")  # not C
    hits = scan.fp_pragma_hits([recipes])
    assert hits == [
        "recipes/npy_rename.h: a pragma turns contraction on",
        "recipes/reactor_main.c: a pragma turns contraction on",
    ], hits


def test_fp_cc1_line_must_carry_off_once_and_nothing_else() -> None:
    good = (
        'clang version 22\n "/t/bin/clang-22" "-cc1" "-triple" "wasm32" '
        '"-ffp-contract=off" "-O3" "x.c"\n'
    )
    assert scan.fp_cc1_errors("clang", good) == []
    assert scan.fp_cc1_errors(
        "clang", good.replace('"-ffp-contract=off"', '"-ffp-contract=on"')
    ) == ["clang -###: the -cc1 line carries ['-ffp-contract=on'], not -ffp-contract=off once"]
    doubled = good.replace('"-O3"', '"-O3" "-ffp-contract=off"')
    assert scan.fp_cc1_errors("clang", doubled)[0].startswith(
        "clang -###: the -cc1 line carries ['-ffp-contract=off', '-ffp-contract=off']"
    )
    after = good.replace('"-O3"', '"-O3" "-ffp-contract=fast"')
    assert scan.fp_cc1_errors("clang++", after)[0].startswith(
        "clang++ -###: the -cc1 line carries ['-ffp-contract=off', '-ffp-contract=fast']"
    )
    assert scan.fp_cc1_errors("clang", "clang version 22\n") == ["clang -###: no -cc1 line"]


STEP_10_FP = """printf '%s\\n' "-ffp-contract=off" >> "$1/bin/clang.cfg"
printf '%s\\n' "-ffp-contract=off" >> "$1/bin/clang++.cfg"
"$SDK/bin/clang" --target=wasm32-wasip1 -### -c "$G/fp-probe.c" > "$G/fp-clang.txt" 2>&1
grep -F -- '"-cc1"' "$G/fp-clang.txt"
"""


def test_fp_recipe_scan_reads_step_10_and_forbids_the_family_elsewhere() -> None:
    assert (
        scan.fp_recipe_errors(
            STEP_10_FP, {"scripts/wasi-cc": "exec clang --target=wasm32-wasip1 -O3\n"}
        )
        == []
    )
    assert scan.fp_recipe_errors(None, {}) == ["scripts/steps/10_tools.sh is missing"]
    errors = scan.fp_recipe_errors(STEP_10_FP.replace("clang++.cfg", "clangxx.cfg"), {})
    assert errors == ["10_tools.sh does not name clang++.cfg"], errors
    errors = scan.fp_recipe_errors(STEP_10_FP.replace("-###", "-v"), {})
    assert errors == ["10_tools.sh does not name -###"], errors
    errors = scan.fp_recipe_errors(
        STEP_10_FP, {"recipes/x.cross": "c_args = ['-O3', '-ffast-math']\n"}
    )
    assert errors == ["recipes/x.cross:1: -ffast-math"], errors
    errors = scan.fp_recipe_errors(
        STEP_10_FP, {"scripts/steps/30_zlib.sh": 'CFLAGS="-O2 -ffp-contract=off"\n'}
    )
    assert errors == ["scripts/steps/30_zlib.sh:1: sets -ffp-contract outside step 10"], errors
    # Step 55's quoted C++ flags, and NAME=-flag.
    planted = {
        "scripts/steps/55_matplotlib.sh": (
            'CXX_EH="-fwasm-exceptions -mllvm -wasm-use-legacy-eh=false'
            ' -fexceptions -ffp-model=precise"\n'
        ),
        "scripts/steps/35_stdlib_libs.sh": "CFLAGS=-ffast-math\n",
    }
    errors = scan.fp_recipe_errors(STEP_10_FP, planted)
    assert errors == [
        "scripts/steps/35_stdlib_libs.sh:1: -ffast-math",
        "scripts/steps/55_matplotlib.sh:1: -ffp-model=precise",
    ], errors


# The build runs only the pinned host Python.
SHIMS = scan.shim_names("3.15.0")
COMMON_079 = 'export PATH="$T/host-python:$T/pylib/bin:$T/$WASMTIME_DIR:$PATH"\n'
STEP_10_079 = (
    'printf \'#!/bin/sh\\nexec "%s" "$@"\\n\' "$HOSTPY" > "$T/host-python/python3"\n'
    '[ "$(command -v python3)" = "$T/host-python/python3" ] || die x\n'
    "/usr/bin/env python3 -c 'import sys; print(sys.prefix)'\n"
    'echo "host python: python3 is $a, Python $v, prefix $p; behind it python2 is $b"\n'
)
BUILD_079 = (
    "P_NOPY=$HERE/build/no-host-python\n"
    "P_UNPINNED=$HERE/build/logs/unpinned-python.log\n"
    'ln -s "$HERE/scripts/refuse-python" "$P_NOPY/$1"\n'
    'for p_file in "$p_dir"/python* "$p_dir"/pypy* "$p_dir"/pip* "$p_dir"/pydoc* "$p_dir"/idle*;'
    " do :; done\n"
    "for p_name in python python2 python2.7 python3; do :; done\n"
    'export PATH="$P_NOPY:$P_KEPT"\n'
)
REFUSER_079 = (
    "#!/bin/sh\n"
    'name=$(basename "$0")\n'
    'dir=$(dirname "$0")\n'
    'if [ "$(basename "$dir")" = no-host-python ]; then\n'
    '  printf \'%s\\n\' "$0 $*" >> "$dir/../logs/unpinned-python.log"\n'
    "fi\n"
    'echo "ERROR: an unpinned $name was run" >&2\n'
    "exit 1\n"
)


def _recipe_079(work: Path, **over: str) -> Path:
    files = {
        "scripts/steps/common.sh": COMMON_079,
        "scripts/steps/10_tools.sh": STEP_10_079,
        "scripts/build.sh": BUILD_079,
        "scripts/refuse-python": REFUSER_079,
        **over,
    }
    for rel, text in files.items():
        if text is not None:
            write(work, rel, text)
    return work


def test_host_python_recipe_holds_and_each_part_is_missed(work) -> None:
    assert scan.host_python_recipe_errors(_recipe_079(work)) == []
    errors = scan.host_python_recipe_errors(
        _recipe_079(work, **{"scripts/steps/common.sh": 'export PATH="$T/pylib/bin:$PATH"\n'})
    )
    assert errors == ["common.sh does not put $T/host-python first on PATH"], errors
    errors = scan.host_python_recipe_errors(
        _recipe_079(work, **{"scripts/build.sh": BUILD_079.replace("no-host-python", "nopy")})
    )
    assert errors == ["build.sh does not name build/no-host-python"], errors
    errors = scan.host_python_recipe_errors(
        _recipe_079(work, **{"scripts/build.sh": BUILD_079.replace(' "$p_dir"/idle*', "")})
    )
    assert errors == ['build.sh does not name "$p_dir"/idle*'], errors
    # A stand-in that takes its log from the environment is refused.
    from_env = REFUSER_079.replace('"$dir/../logs/unpinned-python.log"', '"$UNPINNED_PYTHON_LOG"')
    errors = scan.host_python_recipe_errors(
        _recipe_079(work, **{"scripts/refuse-python": from_env + "# unpinned-python.log\n"})
    )
    assert any("reads UNPINNED_PYTHON_LOG" in e for e in errors), errors
    errors = scan.host_python_recipe_errors(
        _recipe_079(work, **{"scripts/steps/10_tools.sh": STEP_10_079.replace("behind it", "and")})
    )
    assert errors == ["10_tools.sh does not name behind it python2 is"], errors


def test_program_word_reads_env_meson_shells_and_shebangs(work) -> None:
    root = work.resolve()
    pinned = f"{root}/build/tools/python/bin/python3"
    shim = f"{root}/build/tools/host-python/python3"
    cross = f"{root}/scripts/python-wasi-cross"
    env_script = write(work, "src/gen.py", "#!/usr/bin/env python3\nprint(1)\n")
    env_script.chmod(0o755)
    abs_script = write(work, "src/old.py", "#!/usr/bin/python3\nprint(1)\n")
    env_i_script = write(work, "src/clean.py", "#!/usr/bin/env -i python3\nprint(1)\n")
    hostpy_script = write(work, "build/tools/pylib/bin/meson", f"#!{pinned}\n")

    def problem(cmd: str) -> str | None:
        return scan.program_problem(scan._tokens(cmd), root, SHIMS, root)

    for good in (
        f"{env_script} a b",
        f"{shim} x.py",
        f"{pinned} x.py",
        f"{cross} --version",
        f"env PYTHONPATH={root}/numpy/_core {cross} -m code_generators.generate_umath",
        f"{hostpy_script} --internal regenerate",
        "cython -3 x.pyx",
        "python3 x.py",
        "rm -f x",
        "-x c -E -dM -",
    ):
        assert problem(good) is None, good
    for bad, says in (
        ("/opt/homebrew/bin/python3 x.py", "/opt/homebrew/bin/python3 is not a pinned"),
        ("env PYTHONPATH=x /usr/bin/python3 y.py", "/usr/bin/python3 is not a pinned"),
        # env's options by their grammar.
        ("env -u FOO /usr/bin/python3 y.py", "/usr/bin/python3 is not a pinned"),
        ("env -P /usr/local/bin python3 y.py", "`env -P` does not search"),
        ("env -i python3 y.py", "`env -i` does not search"),
        ("env - python3 y.py", "`env -` does not search"),
        ("env --unset=PATH python3", "`env --unset=PATH` does not search"),
        ("env -u PATH python3", "`env -u PATH` does not search"),
        ("env PATH=/usr/bin python3", "`env PATH=/usr/bin` does not search"),
        ("env -v python3", "`env -v` is an option the judge does not read"),
        ("sh -c '/usr/bin/python3 y.py'", "`sh -c` runs a string"),
        (f"{hostpy_script} --internal exe --unpickle x.dat", "--unpickle` hides"),
        (f"{hostpy_script} --internal exe -- /usr/bin/python3 y", "/usr/bin/python3 is not"),
        (f"{abs_script} a", "old.py's shebang: /usr/bin/python3 is not a pinned"),
        (f"{env_i_script} a", "clean.py's shebang: `env -i` does not search"),
        ("python3.14 -V", "`python3.14` is no shim name"),
    ):
        got = problem(bad)
        assert got is not None and says in got, (bad, got)


def test_host_python_records_are_read_and_each_breach_named(work) -> None:
    root = work.resolve()
    line = {"PYTHON_VERSION": "3.15.0", "WASMTIME_DIR": "wasmtime-v49"}
    shim = f"{root}/build/tools/host-python/python3"
    steps = {
        "common.sh": 'B="$HERE/build"\nT="$B/tools"\n' + COMMON_079,
        "57_scipy.sh": 'TOOLS="$B/scipy-tools"\nexport PATH="$TOOLS/bin:$PATH"\n',
    }
    write(
        work,
        "build/freetype-build/meson-logs/meson-log.txt",
        f"Program python3 found: YES ({shim})\nRunning command: {shim} x.py\n",
    )
    write(
        work, "build/freetype-build/build.ninja", f" COMMAND = {shim} y.py\n command = $COMMAND\n"
    )
    write(
        work,
        "build/Python-3.15.0/cross-build/aarch64-apple-darwin/config.log",
        f"configure:3876: found {root}/build/tools/host-python/python3.15\n",
    )
    write(work, "build/scipy-tools/bin/f2py", "#!/bin/sh\n")
    write(work, "build/tools/wasmtime-v49/wasmtime", "")
    gate = (
        "host python: python3 is build/tools/host-python/python3, Python 3.15.0, prefix "
        "build/tools/python; behind it python2 is build/no-host-python/python2\n"
    )
    write(work, "build/logs/10_tools.log", gate)
    errors, read = scan.host_python_record_errors(root, line, steps)
    assert errors == [], errors
    assert "freetype-build/build.ninja: 1 commands" in read, read
    # Each breach, named.
    write(
        work,
        "build/freetype-build/meson-logs/meson-log.txt",
        "Program python3 found: YES (/usr/bin/python3)\n"
        "Program python3 found: YES (/opt/x/bin/py)\n",
    )
    write(work, "build/freetype-build/build.ninja", " COMMAND = /opt/homebrew/bin/python3 x.py\n")
    write(
        work,
        "build/xz-build/config.log",
        "configure:3876: found /Users/x/.local/bin/python3.14\n",
    )
    write(work, "build/lane-047/xz-build/config.log", "configure:1: found /usr/bin/python3\n")
    write(work, "build/scipy-tools/bin/python3", "#!/bin/sh\n")
    write(work, "build/logs/10_tools.log", gate.replace("build/no-host-python/python2", "none"))
    write(work, "build/logs/unpinned-python.log", "x\n")
    unresolved = {**steps, "58_x.sh": 'export PATH="$NOWHERE/bin:$PATH"\n'}
    errors, _ = scan.host_python_record_errors(root, line, unresolved)
    joined = "\n".join(errors)
    for says in (
        "meson-log.txt:1: Program python3: /usr/bin/python3 is not a pinned interpreter",
        "meson-log.txt:2: Program python3 found /opt/x/bin/py, not a pinned interpreter",
        "build.ninja:1: /opt/homebrew/bin/python3 is not a pinned interpreter",
        "xz-build/config.log:1: found /Users/x/.local/bin/python3.14",
        "57_scipy.sh: "
        + f"{root}/build/scipy-tools/bin sits ahead of the stand-in and holds python3",
        "58_x.sh: PATH folder $NOWHERE/bin cannot be resolved",
        "behind the shim python2 is none, not the stand-in",
        "build/logs/unpinned-python.log exists",
    ):
        assert says in joined, (says, errors)
    assert "lane-047" not in joined, errors  # the lane's copies are skipped (direct children only)
    assert len(errors) == 8, errors


def test_config_log_skips_only_direct_children_of_build(work) -> None:
    write(work, "build/harness/config.log", "")
    write(work, "build/harness-tmp/a/config.log", "")
    write(work, "build/xz-build/harness/config.log", "")
    got = [str(p.relative_to(work)) for p in scan.config_logs(work / "build")]
    assert got == ["build/xz-build/harness/config.log"], got


def test_ninja_reader_skips_only_command_and_names_other_variables(work) -> None:
    # Only meson's `$COMMAND` indirection is skipped.
    root = work.resolve()
    text = (
        "rule CUSTOM_COMMAND\n command = $COMMAND\n"
        "rule ODD\n command = $PY gen.py\n"
        "build out: ODD in\n PY = /usr/bin/python3\n"
    )
    hits, read = scan.ninja_hits(text, root, SHIMS, root)
    assert hits == ["4: $PY is a ninja variable the judge does not read"], hits
    assert read == 1


def test_step_folder_with_a_command_substitution_is_unresolved(work) -> None:
    # `$(` and backticks are never resolved, so never skipped.
    root = work.resolve()
    steps = {
        "common.sh": 'B="$HERE/build"\n',
        "99_odd.sh": 'export PATH="$(pwd)/x:$PATH"\nPATH=`pwd`/y:$PATH\n',
    }
    folders, unresolved = scan.step_path_folders(steps, root, {})
    assert folders == [], folders
    assert unresolved == [
        "99_odd.sh: PATH folder $(pwd)/x cannot be resolved",
        "99_odd.sh: PATH folder `pwd`/y cannot be resolved",
    ], unresolved


# --------------------------------------------------------------------------------------------- The
# release judges in parallel shards (acceptance 5). The good workflow is the real one; each variant
# breaks one rule of release_shard_errors, or one of the signing ties' widened rules.

REAL_WORKFLOW = (paths.REPO / ".github" / "workflows" / "release.yml").read_text()
LINUX_IDS = "${{ needs.judge-linux.outputs.own-embedding-id }}"
MACOS_IDS = "${{ needs.judge-macos.outputs.own-embedding-id }}"
WASM_STEP = (
    "      - name: The SHA-256 of python.wasm, handed to the gather\n"
    "        id: wasm\n"
    '        run: echo "sha256=$(shasum -a 256 build/artifacts/python.wasm | cut -c1-64)" >> '
    '"$GITHUB_OUTPUT"\n'
)
ASSETS_IN_GATHER = f"""      - uses: actions/download-artifact@{PIN} # v8.0.2
        with:
          artifact-ids: ${{{{ needs.build.outputs.assets-id }}}}
          path: release-assets
          digest-mismatch: error
      - name: The gather
"""
# Spec 101: the build job runs no shard; the build shard is build-shard's.
REC_IN_BUILD = (
    "      - name: The build shard\n"
    "        run: uv run pytest -p no:cacheprovider --shard=build --progress-latest x\n"
)


def _shard_errors(text: str) -> list[str]:
    from harness import shards

    return scan.release_shard_errors(text, shards.load())


def test_the_real_workflow_passes_every_release_scan() -> None:
    assert _shard_errors(REAL_WORKFLOW) == []
    assert scan.release_binding_errors(REAL_WORKFLOW) == []
    assert scan.release_attestation_errors(REAL_WORKFLOW) == []
    assert scan.rebuild_gate_errors(REAL_WORKFLOW) == []
    assert scan.action_pin_errors(REAL_WORKFLOW) == []


def _without_wasm_then_late(text: str) -> str:
    text = text.replace(WASM_STEP, "", 1)
    late = "      - name: Keep the build logs when something fails\n"
    return text.replace(late, WASM_STEP + late, 1)


# The set's own SHA256SUMS, hashed before the upload, for the gather.
SET_SUMS_STEP = (
    "      - name: The SHA-256 of the set's own SHA256SUMS, handed to the gather (spec 085)\n"
    "        id: set-sums\n"
    '        run: echo "sha256=$(shasum -a 256 build/artifacts/SHA256SUMS | cut -c1-64)" >> '
    '"$GITHUB_OUTPUT"\n'
)


def _without_set_sums_then_late(text: str) -> str:
    assert SET_SUMS_STEP in text
    text = text.replace(SET_SUMS_STEP, "", 1)
    late = "      - name: Keep the build logs when something fails\n"
    return text.replace(late, SET_SUMS_STEP + late, 1)


BAD_SHARDS = [
    ("judge-linux", "upstream-frame, ", "", "rule 2: judge-linux"),
    ("judge-linux", "upstream-frame, ", "upstream-frame, upstream-extra, ", "rule 2: judge-linux"),
    ("judge-macos", "own-hostile, own-guest", "own-guest, own-hostile", "rule 2: judge-macos"),
    (
        "judge-windows",
        "      - name: These are the bytes the build job made\n",
        "      - name: Other bytes\n",
        "rule 4: judge-windows",
    ),
    ("judge-linux", "fetch-depth: 0", "fetch-depth: 1", "rule 3:"),
    (
        "judge-linux",
        "      upstream-frame-sha256: ${{ steps.out.outputs.upstream-frame-sha256 }}\n",
        "",
        "rule 5: judge-linux",
    ),
    ("attest", "same-bytes, gather]", "same-bytes]", "rule 8: attest"),
    (
        "gather",
        "artifact-ids: ${{ needs.build-shard.outputs.record-id }}",
        "name: record-build-build",
        "rule 7: gather does not download",
    ),
    ("gather", "      - name: The gather\n", ASSETS_IN_GATHER, "rule 7: gather does not download"),
    (
        "judge-linux",
        "    timeout-minutes: 30\n",
        "    timeout-minutes: 30\n    continue-on-error: true\n",
        "rule 1: judge-linux",
    ),
    ("judge-macos", "      contents: read\n", "      contents: write\n", "rule 1: judge-macos"),
    (
        "build-shard",
        '--shard=build --progress-latest "$RUNNER_TEMP/record/latest.json"',
        "",
        "rule 6:",
    ),
    ("build", "      wasm-sha256: ${{ steps.wasm.outputs.sha256 }}\n", "", "rule 6:"),
    (
        "judge-macos",
        "          RECORD_ID: ${{ steps.record.outputs.artifact-id }}\n",
        "          RECORD_ID: x\n",
        "rule 4: judge-macos",
    ),
    (
        "judge-macos",
        'echo "$SHARD-id=$RECORD_ID"',
        'echo "own-guest-id=$RECORD_ID"',
        "rule 4: judge-macos",
    ),
    (
        "judge-macos",
        '.hexdigest())" "$RUNNER_TEMP/record/latest.json" >> "$GITHUB_OUTPUT"',
        '.hexdigest())" "$RUNNER_TEMP/other.json" >> "$GITHUB_OUTPUT"',
        "rule 4: judge-macos",
    ),
    (
        "verify",
        "      - name: The wheel, installed fresh, runs a program in one call\n",
        "      - name: A judge\n        run: uv run pytest\n"
        "      - name: The wheel, installed fresh, runs a program in one call\n",
        "rule 9: verify runs pytest",
    ),
    # The set's own SHA256SUMS, from the build to the gather alone.
    ("build", "      set-sums-sha256: ${{ steps.set-sums.outputs.sha256 }}\n", "", "rule 6:"),
    ("build", "shasum -a 256 build/artifacts/SHA256SUMS", "shasum -a 256 MANIFEST", "rule 6:"),
    (
        "gather",
        "          SET_SUMS_SHA256: ${{ needs.build.outputs.set-sums-sha256 }}\n"
        "          SET_SOURCE:",
        "          SET_SOURCE:",
        "rule 7: gather's step",
    ),
    (
        "gather",
        "          SET_SUMS_SHA256: ${{ needs.build.outputs.set-sums-sha256 }}\n"
        "          SET_SOURCE:",
        "          SET_SUMS_SHA256: ${{ needs.build.outputs.sums-sha256 }}\n          SET_SOURCE:",
        "rule 7: gather's step",
    ),
    # Spec 101: the gather is told where the set came from, and reads build-shard's record.
    (
        "gather",
        "          SET_SOURCE: ${{ needs.build.outputs.set-source }}\n",
        "",
        "rule 7: gather's step",
    ),
    ("gather", "build-shard, same-bytes, judge-macos", "judge-macos", "rule 7: gather is not"),
    (
        "build",
        "      - name: The wheel\n",
        REC_IN_BUILD + "      - name: The wheel\n",
        "rule 6: build",
    ),
    (
        "judge-macos",
        "          SHARD: ${{ matrix.shard }}\n",
        "          SHARD: ${{ matrix.shard }}\n"
        "          S: ${{ needs.build.outputs.set-sums-sha256 }}\n",
        "rule 10: judge-macos reads set-sums-sha256",
    ),
    (
        "judge-linux",
        "    outputs:\n",
        "    outputs:\n      set-sums-sha256: x\n",
        "rule 10: judge-linux sets set-sums-sha256",
    ),
]


@pytest.mark.parametrize(
    ("job", "old", "new", "error"), BAD_SHARDS, ids=[b[3] + b[1][:30] for b in BAD_SHARDS]
)
def test_release_shard_scan_names_each_breach(job, old, new, error) -> None:
    errors = _shard_errors(_in_job(REAL_WORKFLOW, job, old, new))
    assert any(e.startswith(error) for e in errors), errors


def test_the_python_wasm_hash_must_come_before_the_upload() -> None:
    errors = _shard_errors(_without_wasm_then_late(REAL_WORKFLOW))
    assert any(e.startswith("rule 6:") for e in errors), errors


def test_the_set_sums_hash_must_come_before_the_upload() -> None:
    """Hashed after the upload, it could name a file other than the one uploaded."""
    errors = _shard_errors(_without_set_sums_then_late(REAL_WORKFLOW))
    assert any(e.startswith("rule 6:") for e in errors), errors


def test_the_gather_guards_the_set_sums_hash() -> None:
    """The gather's guard step tests SET_SUMS_SHA256 as 64 hex, with WASM_SHA256."""
    guard = scan.workflow_step_script(
        REAL_WORKFLOW,
        "gather",
        "Every job handed on its record's id, and the build python.wasm's SHA-256",
    )
    assert '"$SET_SUMS_SHA256"' in guard and '"${#SET_SUMS_SHA256}"' in guard


def test_a_gather_holding_the_assets_breaks_rule_16_too() -> None:
    text = _in_job(REAL_WORKFLOW, "gather", "      - name: The gather\n", ASSETS_IN_GATHER)
    errors = scan.release_binding_errors(text)
    assert any(e.startswith("rule 16: gather holds the build's files") for e in errors), errors
    second = ASSETS_IN_GATHER.replace(
        "needs.build.outputs.assets-id", "needs.build.outputs.record-id"
    )
    second = second.replace("path: release-assets", "path: release-assets/more")
    text = _in_job(REAL_WORKFLOW, "gather", "      - name: The gather\n", second)
    errors = scan.release_binding_errors(text)
    assert any(e.startswith("rule 16: gather downloads into release-assets") for e in errors), (
        errors
    )


def test_a_list_of_ids_from_two_jobs_or_with_one_unguarded_is_refused() -> None:
    mixed = _in_job(
        REAL_WORKFLOW, "gather", f"artifact-ids: {MACOS_IDS},", f"artifact-ids: {LINUX_IDS},"
    )
    errors = scan.release_binding_errors(mixed)
    assert any(e.startswith("rule 4: gather") for e in errors), errors
    unguarded = _in_job(REAL_WORKFLOW, "gather", ' "$MACOS_OWN_GUEST_ID"', "")
    errors = scan.release_binding_errors(unguarded)
    assert any(e.startswith("rule 10: gather") for e in errors), errors


# numpy's compile records each force-include the fenv recipe header once.
FENV_H = "/r/recipes/npy_fenv_flags.h"


def _compile(compiler: str, src: str, *extra: str, include: int = 1) -> dict:
    """A compile record shaped as meson writes numpy's: `command`, a shell string."""
    flags = " ".join(["-include", "/r/recipes/npy_rename.h"] + ["-include", FENV_H] * include)
    words = [f"/r/scripts/{compiler}", "-Inumpy/_core", flags, *extra, "-o", "x.o", "-c", src]
    return {"file": src, "command": " ".join(words)}


def test_npy_fenv_records_pass_when_every_compile_carries_the_header() -> None:
    records = [
        _compile("wasi-cc", "../numpy/_core/src/npymath/ieee754.c"),
        _compile("wasi-cxx", "../numpy/_core/src/npymath/halffloat.cpp"),
        {"file": "../numpy/random/mtrand.pyx", "command": "/r/build/tools/pylib/bin/cython a.pyx"},
    ]
    errors, counts = scan.npy_fenv_record_errors(records)
    assert errors == [] and counts == {"compiles": 2, "c": 1, "c++": 1, "not compiles": 1}, counts


def test_npy_fenv_records_name_a_missing_or_doubled_header() -> None:
    records = [
        _compile("wasi-cxx", "b.cpp", include=0),
        _compile("wasi-cc", "c.c", include=2),
        _compile("wasi-cc", "d.S", include=0),  # by compiler, not by extension
    ]
    errors, _ = scan.npy_fenv_record_errors(records)
    assert errors == [
        "b.cpp: force-includes recipes/npy_fenv_flags.h 0 times, not once",
        "c.c: force-includes recipes/npy_fenv_flags.h 2 times, not once",
        "d.S: force-includes recipes/npy_fenv_flags.h 0 times, not once",
    ], errors


def test_npy_fenv_records_read_compiles_only_by_the_first_arguments_path() -> None:
    link = {"file": "x", "command": "/r/scripts/wasi-cc a.o b.o -o lib.so"}  # no -c: a link
    named = {"file": "y.c", "command": "/usr/bin/cc -DX=scripts/wasi-cc -c y.c"}  # name elsewhere
    lookalike = {"file": "z.c", "command": "/r/scripts/not-wasi-cc -c z.c"}  # not a path ending
    errors, counts = scan.npy_fenv_record_errors([link, named, lookalike])
    assert counts["compiles"] == 0 and counts["not compiles"] == 3, counts
    assert errors == [f"{scan.NPY_FENV_RECORDS} lists no wasi-cc or wasi-cxx compile"], errors


def test_npy_fenv_records_read_both_record_shapes_and_refuse_none() -> None:
    as_list = {
        "file": "a.c",
        "arguments": ["/r/scripts/wasi-cc", "-include", FENV_H, "-c", "a.c"],
    }
    assert scan.npy_fenv_record_errors([as_list, _compile("wasi-cc", "b.c")])[0] == []
    as_list["arguments"] = ["/r/scripts/wasi-cc", "-c", "a.c"]
    assert scan.npy_fenv_record_errors([as_list])[0] == [
        "a.c: force-includes recipes/npy_fenv_flags.h 0 times, not once"
    ]
    errors, _ = scan.npy_fenv_record_errors([])
    assert errors == [f"{scan.NPY_FENV_RECORDS} lists no entry (a build that compiled nothing)"]


def test_npy_fenv_records_file_missing_is_a_finding(work) -> None:
    errors, counts = scan.npy_fenv_records_file_errors(work)
    assert errors == [f"{scan.NPY_FENV_RECORDS} is missing (numpy's compile records)"]
    assert counts == {}
    write(work, scan.NPY_FENV_RECORDS, '[{"file": "a.c", "command": "/r/scripts/wasi-cc -c a.c"}]')
    errors, counts = scan.npy_fenv_records_file_errors(work)
    assert counts["compiles"] == 1 and errors, errors


def test_npy_fenv_recipe_names_what_the_cross_file_and_header_lack() -> None:
    cross = (paths.REPO / scan.NPY_FENV_CROSS).read_text()
    header = (paths.REPO / scan.NPY_FENV_HEADER).read_text()
    assert scan.npy_fenv_recipe_errors(cross, header) == []
    without = "\n".join(
        t.replace(scan.NPY_FENV_INCLUDE + ", ", "") if t.startswith("cpp_args ") else t
        for t in cross.splitlines()
    )
    assert scan.npy_fenv_recipe_errors(without, header) == [
        "recipes/wasi-numpy.cross: cpp_args force-includes recipes/npy_fenv_flags.h 0 times,"
        " not once"
    ]
    assert scan.npy_fenv_recipe_errors(cross, None) == ["recipes/npy_fenv_flags.h is missing"]
    unguarded = header.replace("#error ", "#warning ")
    weakless = header.replace("__attribute__((weak)) int", "int")
    assert scan.npy_fenv_recipe_errors(cross, unguarded) == [
        "recipes/npy_fenv_flags.h lacks the #error guard"
    ]
    assert scan.npy_fenv_recipe_errors(cross, weakless) == [
        "recipes/npy_fenv_flags.h lacks the weak flag word"
    ]


# The citation rule's fixtures are assembled from parts, so this file's own text is never a
# citation the rule would read.
SPEC_WORD, DOC_TREE = "sp" + "ec", "con" + "text/"


@pytest.mark.parametrize(
    ("prose", "rule", "phrase"),
    [
        (f"see {SPEC_WORD} 052 here", "specification", f"{SPEC_WORD} 052"),
        (f"the {SPEC_WORD}ifications 012 and 040", "specification", f"{SPEC_WORD}ifications 012"),
        ("as the constitution §4.1 says", "constitution", "constitution §"),
        ("the clock-and-random m" + "emo says so", "memo", "m" + "emo"),
        ("the review 2026-10-19 found it", "review", "review 2026-10-19"),
        ("the review reviews/009-a.md", "review", "review reviews/"),
        ("the owner's question 95", "question", "question 95"),
        (f"read {DOC_TREE}research first", "context path", f"{DOC_TREE}research"),
        ("the build review's F4.2 again", "finding", "F4.2"),
        ("a bare (N2) here", "finding", "N2"),
        ("the Confirmation's M5 too", "named finding", "Confirmation's M5"),
        ("as 0" + "37's build found", "specification", "0" + "37's"),
        ("nothing writable (§4" + ".15) here", "constitution", "§4" + ".15"),
        ("as the pre-build re" + "view said", "review", "pre-build re" + "view"),
        ("the re-re" + "view agreed", "review", "re-re" + "view"),
    ],
)
def test_a_citation_in_a_comment_or_docstring_is_a_hit(work, prose, rule, phrase) -> None:
    py = write(work, "t/a.py", f'"""Module. {prose}."""\n\nx = 1  # {prose}\n')
    assert (1, rule, phrase) in scan.context_citation_hits(py)
    assert (3, rule, phrase) in scan.context_citation_hits(py)
    sh = write(work, "s/a.sh", f"#!/bin/sh\n# {prose}\necho hi  # {prose}\n")
    assert [h[0] for h in scan.context_citation_hits(sh) if h[1] == rule] == [2, 3]


def test_code_and_literals_are_not_citations(work) -> None:
    """A path read as data and a string literal are code, not prose: only comments and
    docstrings are read. In a comment, a ruff code or a word with digits in it is not an
    identifier; a lone capital and number is, and is written in words instead."""
    py = write(
        work,
        "t/b.py",
        f'"""Reads the progress history."""\n\nHISTORY = "{DOC_TREE}progress/history"\n'
        f'MESSAGE = "{SPEC_WORD} 052 refused"\n'
        "import os  # noqa: F401\n"
        'DIGEST = "MD5"  # MD5, F401 and D12x are words; C99 is refused\n'
        f"def f():\n    x = 1\n    return '{SPEC_WORD} 063'\n",
    )
    assert scan.context_citation_hits(py) == [(6, "finding", "C99")]
    sh = write(work, "s/b.sh", f'cat "$ROOT/{DOC_TREE}progress/x"\necho "{SPEC_WORD} 052"\n')
    assert scan.context_citation_hits(sh) == []
    # A licence's sections, a graph's number and a reviewed list are not project documents.
    words = write(work, "s/c.sh", "# Apache-2.0 §4(b); graph 100's edges; a reviewed list\n")
    assert scan.context_citation_hits(words) == []
    assert scan.context_citation_hits(write(work, "t/c.py", "def broken(:\n")) == []


def test_the_citation_rule_reads_its_four_trees(work) -> None:
    for rel_path in (
        "tests/a.py",
        "tests/b.toml",
        "tests/c.txt",
        "scripts/d",
        "release/e.in",
        ".github/workflows/f.yml",
        "src/g.py",
    ):
        write(work, rel_path, "x = 1\n")
    picked = [scan.rel(p, work) for p in scan.context_citation_files(work)]
    assert picked == [
        "tests/a.py",
        "tests/b.toml",
        ".github/workflows/f.yml",
        "scripts/d",
        "release/e.in",
    ]


def test_a_citation_split_across_lines_is_one_hit(work) -> None:
    """A citation whose number falls on the next line of a docstring or a comment block is found
    on the line it starts; a code line between two comments ends the block."""
    py = write(
        work,
        "t/split.py",
        f'"""A module that cites a\n{SPEC_WORD}\n052 here."""\n\n'
        f"# the {SPEC_WORD}\n# 052 again\nx = 1\n# {SPEC_WORD}\ny = 2  # 052, not joined\n",
    )
    assert scan.context_citation_hits(py) == [
        (2, "specification", f"{SPEC_WORD} 052"),
        (5, "specification", f"{SPEC_WORD} 052"),
    ]
    sh = write(work, "s/split.sh", f"#!/bin/sh\n# see {SPEC_WORD}\n#   063, Decision 2\necho\n")
    assert scan.context_citation_hits(sh) == [(2, "specification", f"{SPEC_WORD} 063")]


# The one-LAPACK check: one OpenBLAS, no lapack_lite, and the shim set (scan.one_lapack_errors).
_OB = "/b/build/openblas-wasi/lib/libopenblas.a"
_SHIMS = "/b/build/numpy-shims/libnumpy_lapack_shims.a"
_XERBLA = "/b/build/link/archives/numpy_lapack_lite.a"
_OB_DEFINED = {"dgesv_", "dgesdd_", "cblas_dgemm", "xerbla_"}


def _map_line(archive: str, member: str, symbol: str) -> str:
    return f"       -   70782f       fb         {archive}({member}):({symbol})"


def _good_map() -> list[str]:
    return [
        *(_map_line(_OB, f"{s}.o", s) for s in sorted(_OB_DEFINED)),
        _map_line(_SHIMS, "numpy_lapack_shims.o", "wasi_numpy_dgesv_"),
        _map_line(_XERBLA, "lapack_lite_python_xerbla.c.o", "wasi_numpy_xerbla_"),
    ]


def _one_lapack(lines, shims=frozenset({"wasi_numpy_dgesv_"}), called=None):
    called = {"wasi_numpy_dgesv_", "wasi_numpy_xerbla_"} if called is None else called
    return scan.one_lapack_errors(lines, _OB_DEFINED, set(shims), set(called))


def test_one_lapack_passes_one_openblas_and_its_shims() -> None:
    assert _one_lapack(_good_map()) == []


def test_one_lapack_names_a_routine_linked_twice_or_from_elsewhere() -> None:
    twice = [*_good_map(), _map_line(_OB, "dgesv2.o", "dgesv_")]
    assert _one_lapack(twice) == ["dgesv_ is linked 2 times"]
    other = _map_line("/b/x/libother.a", "d.o", "dgesv_")
    elsewhere = [other if "(dgesv_)" in t else t for t in _good_map()]
    assert _one_lapack(elsewhere) == ["dgesv_ comes from libother.a, not libopenblas.a"]


def test_one_lapack_counts_only_global_definitions() -> None:
    # f2c's file-local static cdotc_ wrappers (OpenBLAS's chetd2.o, scipy's PROPACK) are not copies
    local = _map_line("/b/x/propack.a", "lanbpro.c.o", "cdotc_")
    lines = [*_good_map(), _map_line(_OB, "cdotc.o", "cdotc_"), local]
    defined = {*_OB_DEFINED, "cdotc_"}
    shims, called = {"wasi_numpy_dgesv_"}, {"wasi_numpy_dgesv_", "wasi_numpy_xerbla_"}
    assert scan.one_lapack_errors(lines, defined, shims, called) == ["cdotc_ is linked 2 times"]
    not_local = lambda archive, member, symbol: member != "lanbpro.c.o"  # noqa: E731
    assert scan.one_lapack_errors(lines, defined, shims, called, not_local) == []


def test_one_lapack_names_lapack_lite() -> None:
    f2c = _map_line(_XERBLA, "lapack_lite_f2c_d_lapack.c.o", "numpy_lapack_lite_dgesv_")
    assert _one_lapack([*_good_map(), f2c]) == [
        "the link takes lapack_lite_f2c_d_lapack.c.o from numpy_lapack_lite.a",
        "the link takes numpy_lapack_lite_dgesv_",
    ]


def test_one_lapack_names_a_shim_from_another_archive() -> None:
    moved = [t.replace(_SHIMS, "/b/x/libscipy_lapack_shims.a") for t in _good_map()]
    assert _one_lapack(moved) == [
        "wasi_numpy_dgesv_ comes from libscipy_lapack_shims.a, not libnumpy_lapack_shims.a"
    ]


def test_one_lapack_with_no_openblas_is_a_finding() -> None:
    errors = _one_lapack([t for t in _good_map() if _OB not in t])
    assert errors[0] == "the link takes no symbol from libopenblas.a"


def test_one_lapack_names_an_uncalled_shim_and_a_call_with_none() -> None:
    extra = _one_lapack(_good_map(), shims={"wasi_numpy_dgesv_", "wasi_numpy_cgeev_"})
    assert extra == ["shim wasi_numpy_cgeev_ is called by no numpy object"]
    called = {"wasi_numpy_dgesv_", "wasi_numpy_dgetrf_", "wasi_numpy_xerbla_"}
    assert _one_lapack(_good_map(), called=called) == [
        "numpy calls wasi_numpy_dgetrf_, which no shim defines"
    ]


def test_one_lapack_recipe_as_written() -> None:
    cross = (paths.REPO / scan.ONE_LAPACK_CROSS).read_text()
    header = (paths.REPO / scan.ONE_LAPACK_HEADER).read_text()
    imap = (paths.REPO / scan.ONE_LAPACK_MAP).read_text()
    step = (paths.REPO / scan.ONE_LAPACK_STEP).read_text()
    assert scan.one_lapack_recipe_errors(cross, header, imap, step) == []
    old = cross.replace("'-DNPY_NO_SIGNAL'", "'-DBLAS_SYMBOL_PREFIX=x', '-DNPY_NO_SIGNAL'")
    assert scan.one_lapack_recipe_errors(old, header, imap, step) == [
        "recipes/wasi-numpy.cross still names BLAS_SYMBOL_PREFIX"
    ]
    assert scan.one_lapack_recipe_errors(cross, None, imap, step) == [
        "recipes/numpy_lapack_abi.h is missing"
    ]
    noblas = step.replace(scan.ONE_LAPACK_MESON, "-Dblas=none -Dlapack=none")
    assert scan.one_lapack_recipe_errors(cross, header, imap, noblas) == [
        f"scripts/steps/40_numpy.sh does not pass {scan.ONE_LAPACK_MESON}"
    ]


def test_one_lapack_include_log() -> None:
    entries = scan.include_map_entries((paths.REPO / scan.ONE_LAPACK_MAP).read_text())
    assert [n for _, _, n in entries] == [1, 1, 2, 1]
    log = "".join(f"{s}\tsrc\n" * n for s, _, n in entries)
    assert scan.include_log_errors(entries, log) == []
    assert scan.include_log_errors(entries, log.replace("common/", "x/")) == [
        "per-file include common/python_xerbla.c matched 0 compiles, not 1"
    ]
    assert scan.include_log_errors(entries, None)[0].endswith("(step 40's per-file include log)")


def test_one_lapack_records_and_deps() -> None:
    f2c = {"file": "../numpy/linalg/lapack_lite/f2c_blas.c", "command": "wasi-cc -c f2c_blas.c"}
    assert scan.numpy_blas_record_errors([f2c], ["a/lapack_lite_f2c_blas.c.o"]) == [
        "numpy compiles ../numpy/linalg/lapack_lite/f2c_blas.c: lapack_lite's f2c LAPACK",
        "build/numpy-build holds a/lapack_lite_f2c_blas.c.o",
    ]
    prefixed = {"file": "a.c", "command": "wasi-cc -DBLAS_SYMBOL_PREFIX=x -c a.c"}
    assert scan.numpy_blas_record_errors([prefixed], []) == ["a.c: carries -DBLAS_SYMBOL_PREFIX"]
    archive = Path("/b/build/openblas-wasi/lib/libopenblas.a")
    assert scan.numpy_deps_errors({"m.deps": [str(archive), "-lm"]}, archive) == []
    by_flags = ["-L/b/build/openblas-wasi/lib", "-lopenblas"]
    assert scan.numpy_deps_errors({"m.deps": by_flags}, archive) == []
    assert scan.numpy_deps_errors({"m.deps": ["-lm"]}, archive) == ["m.deps names no OpenBLAS"]
    other = "/x/lib/libopenblas.a"
    assert scan.numpy_deps_errors({"m.deps": [other]}, archive) == [
        f"m.deps names {other}, not {archive}"
    ]


def test_only_the_body_of_type_checking_is_typing_only(work) -> None:
    """An import under `if TYPE_CHECKING:` is for a type checker; one in its `else:` branch, in
    a function or at module level runs, and so does any import elsewhere in the package."""
    module = write(
        work,
        "pkg/mod.py",
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from ._fs_table import _Files\n"
        "else:\n"
        "    from ._fs_table import _Files as F\n"
        "from . import mounts\n"
        "def f():\n"
        "    import pkg._fs_memory\n"
        "    if TYPE_CHECKING:\n"
        "        from pkg._fs_paths import x\n"
        "import os\n",
    )
    assert scan.sibling_imports(module) == [
        (3, "_fs_table", True),
        (5, "_fs_table", False),
        (6, "mounts", False),
        (8, "_fs_memory", False),
        (10, "_fs_paths", True),
    ]


LOCK_PROJECT = """\
[project]
name = "p"
requires-python = "==3.15.0"
dependencies = [
    "numpy @ https://e.org/numpy.whl ; platform_machine == 'arm64'",
    "numpy==2.5.2 ; platform_machine != 'arm64'",
    "seaborn==0.13.2",
    "wrapt==2.5.1",
]

[tool.uv.sources]
wrapt = { url = "https://e.org/wrapt.whl" }
"""

NUMPY_BY_SOURCE = """\
    { name = "numpy", version = "2.5.2", source = { registry = "https://pypi.org/simple" } },
    { name = "numpy", version = "2.5.2", source = { url = "https://e.org/numpy.whl" } },
"""


def _lock(seaborn_numpy: str = NUMPY_BY_SOURCE, root_extra: str = "") -> str:
    """A lock in uv's shape: numpy as two packages (a registry pin and a direct wheel), so every
    entry naming numpy must say which."""
    return f"""\
version = 1
revision = 3
requires-python = "==3.15.0"

[[package]]
name = "numpy"
version = "2.5.2"
source = {{ registry = "https://pypi.org/simple" }}

[[package]]
name = "numpy"
version = "2.5.2"
source = {{ url = "https://e.org/numpy.whl" }}

[[package]]
name = "p"
version = "0"
source = {{ virtual = "." }}
dependencies = [
{NUMPY_BY_SOURCE}    {{ name = "seaborn" }},
    {{ name = "wrapt" }},
]

[package.metadata]
requires-dist = [
    {{ name = "numpy", marker = "platform_machine == 'arm64'", url = "https://e.org/numpy.whl" }},
    {{ name = "numpy", marker = "platform_machine != 'arm64'", specifier = "==2.5.2" }},
    {{ name = "seaborn", specifier = "==0.13.2" }},
    {{ name = "wrapt", url = "https://e.org/wrapt.whl" }},{root_extra}
]

[[package]]
name = "seaborn"
version = "0.13.2"
source = {{ registry = "https://pypi.org/simple" }}
dependencies = [
{seaborn_numpy}]

[[package]]
name = "wrapt"
version = "2.5.1"
source = {{ url = "https://e.org/wrapt.whl" }}
"""


def test_a_lock_uv_takes_is_quiet() -> None:
    assert scan.lock_errors(_lock(), LOCK_PROJECT) == []


def test_a_bare_entry_that_two_packages_answer_is_named() -> None:
    # The shape a text merge left twice: the entry uv refuses with "has missing `source` field
    # but has more than one matching package".
    lock = _lock(seaborn_numpy='    { name = "numpy" },\n')
    assert scan.lock_errors(lock, LOCK_PROJECT) == [
        "seaborn 0.13.2: its numpy entry has no source, and 2 packages are named numpy"
    ]


def test_a_shared_name_entry_with_a_version_and_no_source_is_named() -> None:
    # One version matches one package, but uv asks a shared name for its source all the same.
    lock = _lock(seaborn_numpy='    { name = "numpy", version = "2.5.2" },\n')
    lock = lock.replace('version = "2.5.2", source = { url', 'version = "2.4.0", source = { url')
    lock = lock.replace('version = "2.5.2"\nsource = { url', 'version = "2.4.0"\nsource = { url')
    assert scan.lock_errors(lock, LOCK_PROJECT) == [
        "seaborn 0.13.2: its numpy entry has no source, and 2 packages are named numpy"
    ]


def test_a_shared_name_entry_with_a_source_and_no_version_is_named() -> None:
    entry = '    { name = "numpy", source = { registry = "https://pypi.org/simple" } },\n'
    assert scan.lock_errors(_lock(seaborn_numpy=entry), LOCK_PROJECT) == [
        "seaborn 0.13.2: its numpy entry has no version, and 2 packages are named numpy"
    ]


def test_a_shared_name_entry_from_a_source_tree_needs_no_version() -> None:
    lock = _lock(seaborn_numpy='    { name = "numpy", source = { directory = "numpy" } },\n')
    lock = lock.replace(
        'version = "2.5.2", source = { url = "https://e.org/numpy.whl" }',
        'version = "2.5.2", source = { directory = "numpy" }',
    )
    lock = lock.replace(
        'version = "2.5.2"\nsource = { url = "https://e.org/numpy.whl" }',
        'version = "2.5.2"\nsource = { directory = "numpy" }',
    )
    assert scan.lock_errors(lock, LOCK_PROJECT) == []


def test_an_entry_that_no_package_answers_is_named() -> None:
    entry = (
        '    { name = "numpy", version = "2.4.0", source = { url = "https://e.org/numpy.whl" } },\n'
    )
    assert scan.lock_errors(_lock(seaborn_numpy=entry), LOCK_PROJECT) == [
        "seaborn 0.13.2: its numpy entry by version+source matches 0 packages"
    ]


def test_an_unparsable_lock_is_named() -> None:
    (error,) = scan.lock_errors(_lock() + "[[package]\n", LOCK_PROJECT)
    assert error.startswith("the lock does not parse: ")


def test_a_lock_behind_its_project_is_named() -> None:
    project = LOCK_PROJECT.replace('"wrapt==2.5.1",', '"wrapt==2.5.1",\n    "six==1.17.0",')
    project = project.replace('"==3.15.0"', '"==3.15.1"')
    extra = '\n    { name = "tqdm", specifier = "==4.70.1" },'
    assert scan.lock_errors(_lock(root_extra=extra), project) == [
        "the project requires six ==1.17.0, the lock does not",
        "the lock requires tqdm ==4.70.1, the project does not",
        "the lock's requires-python '==3.15.0' is not the project's '==3.15.1'",
    ]


def test_extras_spaces_and_an_unnormalised_name_are_read_as_uv_writes_them() -> None:
    # Extras are left out of the comparison, as markers are; uv writes a specifier without
    # spaces and the project's name normalised.
    project = LOCK_PROJECT.replace('name = "p"', 'name = "P_"')
    project = project.replace('"seaborn==0.13.2"', '"seaborn[stats] == 0.13.2"')
    lock = _lock().replace('name = "p"', 'name = "p-"')
    assert scan.lock_errors(lock, project) == []
