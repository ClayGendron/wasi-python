"""Each repository scanner, firing on a bad input and quiet on a good one."""

from __future__ import annotations

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
    """Spec 018: every removal in a build script goes through `remove`."""
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
        os: [ubuntu-24.04-arm, ubuntu-24.04]
        include:
          - os: ubuntu-24.04-arm
            timeout: 120
          - os: ubuntu-24.04
            timeout: 120
    runs-on: ${{ matrix.os }}
    timeout-minutes: ${{ matrix.timeout }}
    steps:
      - name: The runner's own tools
        run: |
          uname -srm
          nproc
          ls /proc/sys/fs/binfmt_misc/
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
      - uses: actions/download-artifact@0000000000000000000000000000000000000000
        with:
          name: rebuild-wheel-ubuntu-24.04-arm
          path: rebuilt-wheels/ubuntu-24.04-arm
      - uses: actions/download-artifact@0000000000000000000000000000000000000000
        with:
          name: rebuild-ubuntu-24.04
          path: rebuilds/ubuntu-24.04
      - uses: actions/download-artifact@0000000000000000000000000000000000000000
        with:
          name: rebuild-wheel-ubuntu-24.04
          path: rebuilt-wheels/ubuntu-24.04
      - name: Every rebuild's SHA256SUMS is the set's
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
  attest:
    if: github.event_name == 'push' && github.ref_type == 'tag'
    needs: [build, verify, same-bytes]
  publish:
    if: github.event_name == 'push' && github.ref_type == 'tag'
    needs: [build, verify, same-bytes, attest]
"""
X86_ROW = "          - os: ubuntu-24.04\n            timeout: 120\n"
ARM_ROW = "          - os: ubuntu-24.04-arm\n            timeout: 120\n"

BAD_REBUILDS = [
    (("  rebuild:\n", "  rebuilt:\n"), "no rebuild job"),
    (("  same-bytes:\n", "  same-bits:\n"), "no same-bytes job"),
    (("os: [ubuntu-24.04-arm, ubuntu-24.04]", "os: [ubuntu-24.04]"), "rebuild's matrix lacks"),
    (
        ("os: [ubuntu-24.04-arm, ubuntu-24.04]", "os: [ubuntu-24.04-arm]"),
        "rebuild's matrix lacks ubuntu-24.04",
    ),
    (("    runs-on: ${{ matrix.os }}\n", "    runs-on: ubuntu-24.04\n"), "rebuild does not run on"),
    (
        ("    timeout-minutes: ${{ matrix.timeout }}\n", "    timeout-minutes: 360\n"),
        "rebuild's timeout-minutes does not come from its matrix",
    ),
    (
        (ARM_ROW, ARM_ROW.replace("120", "360")),
        "rebuild's matrix does not give ubuntu-24.04-arm 120 minutes",
    ),
    (
        (X86_ROW, X86_ROW.replace("120", "360")),
        "rebuild's matrix does not give ubuntu-24.04 120 minutes",
    ),
    ((X86_ROW, ""), "rebuild's matrix does not give ubuntu-24.04 120 minutes"),
    (("          nproc\n", ""), "rebuild's tools step does not print nproc"),
    (
        ("          ls /proc/sys/fs/binfmt_misc/\n", ""),
        "rebuild's tools step does not print binfmt_misc",
    ),
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
    (('            cmp "$sums"', '            diff "$sums"'), "same-bytes does not compare"),
    (
        ('cmp "$sums" "rebuilds/$runner/SHA256SUMS"', 'cmp "$sums" "$sums"'),
        "same-bytes does not compare",
    ),
    (
        ("path: rebuilds/ubuntu-24.04-arm", "path: elsewhere"),
        "same-bytes does not name ubuntu-24.04-arm's SHA256SUMS",
    ),
    (
        ("path: rebuilds/ubuntu-24.04\n", "path: elsewhere\n"),
        "same-bytes does not name ubuntu-24.04's SHA256SUMS",
    ),
    (
        ("path: rebuilt-wheels/ubuntu-24.04-arm", "path: elsewhere"),
        "same-bytes does not name ubuntu-24.04-arm's rebuilt wheel",
    ),
    (
        ("name: rebuild-wheel-ubuntu-24.04\n", "name: rebuild-wheel\n"),
        "same-bytes does not name ubuntu-24.04's rebuilt wheel",
    ),
    (
        ("for runner in ubuntu-24.04-arm ubuntu-24.04;", "for runner in ubuntu-24.04;"),
        "same-bytes' SHA256SUMS loop does not run over ubuntu-24.04-arm",
    ),
    (
        ("for runner in ubuntu-24.04-arm ubuntu-24.04;", "for runner in ubuntu-24.04-arm;"),
        "same-bytes' SHA256SUMS loop does not run over ubuntu-24.04",
    ),
    (
        ("for r in ubuntu-24.04-arm ubuntu-24.04;", "for r in ubuntu-24.04;"),
        "same-bytes' wheel loop does not run over ubuntu-24.04-arm",
    ),
    (
        ("for r in ubuntu-24.04-arm ubuntu-24.04;", "for r in ubuntu-24.04-arm;"),
        "same-bytes' wheel loop does not run over ubuntu-24.04",
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


# Spec 059: every host compiles with its own SDK; X carries the five emulation names, the
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
    """X compiling with B's SDK under the emulator, the five names present (spec 040's position),
    is the fallback's legal second position (spec 059, Decision 3)."""
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


# Spec 059: every compile contracts nothing.
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
    # The build review's finding 1: a flag inside a quoted multi-flag string, or in NAME=-flag.
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
    # The build review's finding 3: automake's COMPILE variable runs the compiler by its value.
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
    assert read[0] == "freetype-build/compile_commands.json: 1 commands"
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
    # The build review's finding 2: the project's own C under recipes/, force-included headers too.
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
    # The build review's finding 1, its own example: step 55's quoted C++ flags, and NAME=-flag.
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
