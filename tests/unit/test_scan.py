"""Each repository scanner, firing on a bad input and quiet on a good one."""

from __future__ import annotations

from pathlib import Path

import pytest

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
    needs: [build, verify]
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
    needs: [build, verify, attest]
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
    (("    needs: [build, verify]\n", "    needs: [build]\n"), "attest does not need build and"),
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
        ("    needs: [build, verify, attest]\n", "    needs: [build, verify]\n"),
        "publish does not need attest",
    ),
    # The review's ways around the first scan (spec 009's build review, findings 1 to 4).
    (
        ("      - uses: actions/attest@", "      # - uses: actions/attest@"),
        "no actions/attest step pinned by a 40-hex commit",
    ),
    (
        ("    needs: [build, verify]\n", "    needs: [build]  # verify\n"),
        "attest does not need build and",
    ),
    (
        (
            "    needs: [build, verify]\n",
            "    needs: [build, verify]\n    continue-on-error: true\n",
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


REBUILD_WORKFLOW = """name: release
permissions:
  contents: read
jobs:
  build:
    runs-on: macos-15
  rebuild:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-24.04-arm]
    runs-on: ${{ matrix.os }}
    steps:
      - name: Build from the pins
        run: scripts/build.sh
      - uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2
        with:
          name: rebuild-${{ matrix.os }}
          path: build/artifacts/SHA256SUMS
        if: failure()
  same-bytes:
    needs: [build, rebuild]
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/download-artifact@0000000000000000000000000000000000000000
        with:
          name: rebuild-ubuntu-24.04-arm
          path: rebuilds/ubuntu-24.04-arm
      - name: Every rebuild's SHA256SUMS is the set's
        run: |
          sums=set/SHA256SUMS
          for runner in ubuntu-24.04-arm; do
            cmp "$sums" "rebuilds/$runner/SHA256SUMS"
          done
  verify:
    needs: build
  attest:
    if: github.event_name == 'push' && github.ref_type == 'tag'
    needs: [build, verify, same-bytes]
  publish:
    if: github.event_name == 'push' && github.ref_type == 'tag'
    needs: [build, verify, same-bytes, attest]
"""

BAD_REBUILDS = [
    (("  rebuild:\n", "  rebuilt:\n"), "no rebuild job"),
    (("  same-bytes:\n", "  same-bits:\n"), "no same-bytes job"),
    (("os: [ubuntu-24.04-arm]", "os: [ubuntu-24.04]"), "rebuild's matrix lacks"),
    (("    runs-on: ${{ matrix.os }}\n", "    runs-on: ubuntu-24.04\n"), "rebuild does not run on"),
    (("        run: scripts/build.sh\n", "        run: echo\n"), "rebuild does not run scripts"),
    (("name: rebuild-${{ matrix.os }}", "name: rebuild"), "rebuild does not upload"),
    (
        (
            "    runs-on: ${{ matrix.os }}\n",
            "    runs-on: ${{ matrix.os }}\n    if: github.ref_type == 'tag'\n",
        ),
        "rebuild has a job-level if:",
    ),
    (
        (
            "    needs: [build, rebuild]\n",
            "    needs: [build, rebuild]\n    permissions:\n      id-token: write\n",
        ),
        "same-bytes's permissions are more than",
    ),
    (
        (
            "    needs: [build, rebuild]\n",
            "    needs: [build, rebuild]\n    continue-on-error: true\n",
        ),
        "same-bytes has a job-level continue-on-error:",
    ),
    (
        ("    needs: [build, rebuild]\n", "    needs: [build]\n"),
        "same-bytes does not need build and",
    ),
    (("            cmp ", "            diff "), "same-bytes does not compare"),
    (
        ('cmp "$sums" "rebuilds/$runner/SHA256SUMS"', 'cmp "$sums" "$sums"'),
        "same-bytes does not compare",
    ),
    (("path: rebuilds/ubuntu-24.04-arm", "path: elsewhere"), "same-bytes does not name"),
    (
        ("for runner in ubuntu-24.04-arm; do", "for runner in ubuntu-24.04; do"),
        "same-bytes does not name ubuntu-24.04-arm'",
    ),
    (('/SHA256SUMS"\n', '/SHA256SUMS" || true\n'), "a step of same-bytes swallows"),
    (
        ("    needs: [build, verify, same-bytes]\n", "    needs: [build, verify]\n"),
        "attest does not need",
    ),
    (
        (
            "    needs: [build, verify, same-bytes, attest]\n",
            "    needs: [build, verify, attest]\n",
        ),
        "publish does not need",
    ),
    (
        ("    needs: [build, rebuild]\n", "    needs: [build]  # rebuild\n"),
        "same-bytes does not need",
    ),
]


def test_rebuild_gate_scan_passes_a_good_workflow() -> None:
    assert scan.rebuild_gate_errors(REBUILD_WORKFLOW) == []


@pytest.mark.parametrize(("change", "error"), BAD_REBUILDS, ids=[e for _, e in BAD_REBUILDS])
def test_rebuild_gate_scan_names_each_breach(change, error) -> None:
    old, new = change
    assert REBUILD_WORKFLOW.count(old) == 1, old
    errors = scan.rebuild_gate_errors(REBUILD_WORKFLOW.replace(old, new))
    assert errors and errors[0].startswith(error), errors
