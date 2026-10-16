"""Each repository scanner, firing on a bad input and quiet on a good one."""

from __future__ import annotations

from pathlib import Path

from harness import jobs, scan


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
        "wizer-v11.0.3-aarch64-macos.tar.xz",
        "wizer-v11.0.3-x86_64-linux.tar.xz",
        "wasmtime-v49.0.3-aarch64-macos.tar.xz",
        "wasmtime-v49.0.3-x86_64-linux.tar.xz",
    ]
    assert scan.toolchain_errors(both) == []
    assert scan.toolchain_errors(both[:1]) == [
        "wasi-sdk: no Linux x86_64 pin",
        "wizer: no Linux x86_64 pin",
        "wizer: no macOS arm64 pin",
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
