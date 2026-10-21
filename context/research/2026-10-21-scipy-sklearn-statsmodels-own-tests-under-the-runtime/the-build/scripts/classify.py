"""Sort each group's failures (from the judge's kept streams) into the catalog's classes; write
classes.json for gen095.py and print what no class admits, per group.

    uv run python classify.py [group ...]      (default: every group with a stream)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SP = Path(__file__).parent
W = Path("/Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06")
STREAMS = W / "build/harness/streams"
README = "README.md"

# (id, match, reason, closes_with, where): `where` only checks my assignment (a node-id regex);
# the class itself matches by reason alone.
CATALOG = {
    "scipy": [
        ("no-threads", r"can't start new thread|thread constructor failed",
         "no threads: the runtime starts none on WASI, so a test that starts one fails (README)", README, None),
        ("no-threads-unraisable", r"PytestUnraisableExceptionWarning: Exception ignored in: 'scipy\.stats\._qmc_cy\.threaded_loops'",
         "no threads: qmc's C++ workers fail to start and the exception they leave is reported when pytest collects it (README)", README, None),
        ("no-threads-results", r"^AssertionError:$",
         "a check of work that would run on threads: Matrix Market's parallelism stays 1 (the carried patch reads and writes serially) and qmc's C++ workers cannot start, so their result is unset (README)", README, r"test_threadpoolctl|test_discrepancy_parallel"),
        ("no-processes", r"has no attribute 'pipe'|does not support processes|No module named '_multiprocessing'|_posixsubprocess",
         "no processes: os has no pipe and subprocess is unavailable on WASI, so a process pool or a child interpreter fails (README)", README, None),
        ("no-native-id-test-names", r"has no attribute 'get_native_id'",
         "the runtime's threading names no native thread id on WASI, and these tests make their temporary file names from it (README)", README, r"^scipy/(io|interpolate)/"),
        ("mpmath-tolerance", r"^AssertionError:$",
         "at a few of thousands of points the guest's value differs from mpmath's: Airy Ai' and Bi at one point each by 1.2e-4 relative (the test allows 1e-5), and Bessel Y of order -5.6e25 finite where mpmath gives -inf, since wasm's libm differs from native's (README)", README, r"test_mpmath\.py"),
        ("float32-rounding", r"^AssertionError:$",
         "two of 483 float32 values miss the test's 1e-5 absolute tolerance by about one float32 step (1.19e-5): wasm's float rounding differs from native's (README)", README, r"test_fir_filter_design\.py::TestMinimumPhase::test_nyquist"),
        ("no-native-id-uarray", r"has no attribute 'get_native_id'",
         "uarray's set_backend and skip_backend read threading.get_native_id(), which the runtime's threading lacks on WASI, so switching scipy.fft's backend fails (README)", README, r"^scipy/(fft|_lib)/"),
        ("enotsup-io", r"OSError: \[Errno 58\] Not supported",
         "numpy's fromfile and tofile duplicate the file's descriptor, which WASI preview1 refuses, so scipy.io's FortranFile and wavfile fail (README)", README, None),
        ("no-mmap", r"mmap is unavailable",
         "no mmap: the stand-in raises OSError (README)", README, None),
        ("no-fp-exceptions", r"DID NOT WARN\. No warnings of type \(<class 'RuntimeWarning'>|DID NOT RAISE <class '(ValueError|FloatingPointError)'>",
         "wasm has no floating-point exception flags, so an errstate that raises or warns on a division by zero or an invalid value sees nothing (README)", README, None),
        ("test-only-modules", r"DID NOT WARN\. No warnings of type \(<class 'DeprecationWarning'>",
         "the test imports scipy's test-only C module _test_deprecation_call, which the product leaves out on purpose; the judge-only binary the roadmap reserves (088) links it", "context/roadmap.md", r"test_deprecation\.py"),
        ("enotsup-io-file-left-open", r"Exception ignored while finalizing file <_io\.FileIO name='/upstream-scipy/tree/scipy/io/tests/data/",
         "a file that a failed FortranFile read left open (numpy's fromfile cannot duplicate its descriptor on WASI) is reported when it is finalized, during whichever test runs then (README)", README, None),
        ("enotsup-io-no-warning", r"DID NOT WARN\. No warnings of type \(<class 'scipy\.io\.wavfile\.WavFileWarning'>",
         "wavfile's read fails with ENOTSUP inside the test's warning block (numpy's fromfile cannot duplicate the descriptor on WASI), so the warning the test expects never comes (README)", README, None),
        ("fit-flat-likelihood", r"^AssertionError:$",
         "fitting the f distribution to interval-censored data, the first shape parameter barely moves the likelihood: the guest's optimizer stops at 341.2 where native's stops at 290.5 (the other three within 3%), since wasm rounds differently (README)", README, r"test_fit\.py::test_cont_fit\[MLE-f-"),
        ("odr-stand-in-visible", r"Found unexpected modules: \['scipy\.odr'\]",
         "scipy's public-API check finds the product's scipy.odr stand-in module, which upstream removes in 1.19 and the product keeps as a stand-in", "context/specifications/037-scipy.md", None),
        ("wasm32-memory", r"array is too big|MemoryError|Unable to allocate",
         "wasm32's 4 GiB address space bounds the guest; these tests ask for more (README)", README, None),
    ],
    "scikit-learn": [
        ("no-mmap", r"mmap is unavailable",
         "no mmap: the stand-in raises OSError, so a test on memory-mapped data fails (README)", README, None),
        ("no-dup", r"OSError: \[Errno 58\] Not supported",
         "a verbose fit redirects the process's standard output with a duplicated descriptor, which WASI preview1 refuses (README)", README, None),
        ("pillow-zlib-only", r"(en|de)coder jpeg not available",
         "Pillow is built with zlib only, so the faces dataset's JPEG fixtures cannot be written (README)", README, None),
        ("no-openmp", r"^AssertionError:$",
         "there is no OpenMP in the build (wasi-sdk has no runtime, and the guest no threads), so _openmp_parallelism_enabled() is False (README)", README, r"test_openmp_parallelism_enabled"),
        ("no-mmap-estimator-checks", r"assert 8 == 4$|^assert 4 == 0$",
         "check_estimator finds four more failing checks for NuSVC than upstream expects: the checks that copy the data into memory maps fail without mmap (README)", README, r"test_estimator_checks\.py"),
        ("no-dev-null", r"No such file or directory: '/dev/null'",
         "WASI has no /dev/null, so a test that sends verbose output there fails (README)", README, None),
        ("wasm32-int128", r"^assert 16 == 8$",
         "wasm32's compiler has a 128-bit integer, which upstream's test expects only on 64-bit platforms and on emscripten's wasm32; the guest's platform is wasi (README)", README, None),
        ("package-in-zip", r"Not a directory: '/usr/local/lib/python\d+\.zip/sklearn/",
         "the package's files are in the stdlib zip, not in folders, so a test that lists the package's folder fails (README)", README, None),
    ],
    "statsmodels": [
        ("no-processes", r"has no attribute 'pipe'|does not support processes",
         "no processes: os has no pipe on WASI, so a multiprocessing pool fails (README)", README, None),
        ("wasm-is-not-emscripten", r"SingularMatrixWarning: The design matrix is rank-deficient|Function is marked as not warning but the following warnings were found",
         "upstream special-cases wasm by sys.platform 'emscripten' (Pyodide); the guest is wasm on WASI, so the case does not apply and the warning upstream expects of wasm (no floating-point exception flags) differs (README)", README, None),
        ("upstream-xfail-platform", r"class: TestTTPowerOneS1, key: alpha",
         "upstream xfails this alpha solve on Windows and macOS with recent scipy; the guest is neither, so it fails here as it does there unmarked", README, None),
        ("left-out-datasets", r"FileNotFoundError: .*statsmodels/datasets/\w+/",
         "the test loads one of the thirteen datasets the product leaves out for their terms (README)", README, None),
    ],
}


def parse(text: str) -> list[tuple[str, str, str]]:
    out = []
    for line in text.splitlines():
        if line.startswith("R failed ") or line.startswith("R error "):
            kind, rest = line[2:].split(" ", 1)
            node, _, reason = rest.partition(" -- ")
            out.append((kind, node, reason))
    return out


def main() -> None:
    classes = json.loads((SP / "classes.json").read_text()) if (SP / "classes.json").exists() else {}
    wanted = sys.argv[1:]
    for f in sorted(STREAMS.glob("*.txt")):
        fam = next(p for p in CATALOG if f.name.startswith(p + "-"))
        group = f.name[len(fam) + 1 : -4]
        if wanted and group not in wanted:
            continue
        text = f.read_text(errors="replace")
        got: dict[tuple[str, str], dict] = {}
        loose = []
        for kind, node, reason in parse(text):
            hit = None
            for cid, rx, why, closer, where in CATALOG[fam]:
                if re.search(rx, reason) and (where is None or re.search(where, node)):
                    hit = (cid, why, closer)
                    break
            if hit is None:
                loose.append((kind, node, reason))
                continue
            cid = hit[0] if kind == "failed" else hit[0] + "-at-setup"
            k = got.setdefault((cid, kind), {"id": cid, "outcome": kind, "match": "", "reason": hit[1], "closes_with": hit[2], "members": []})
            k["members"].append(node)
        for (cid, kind), k in got.items():
            base = cid.removesuffix("-at-setup")
            k["match"] = next(rx for c, rx, *_ in CATALOG[fam] if c == base)
            if kind == "error":
                k["reason"] = k["reason"].replace(" (README)", ", at setup or teardown (README)")
        classes[group] = sorted(got.values(), key=lambda k: k["id"])
        seen_rx: dict[tuple[str, str], str] = {}
        for k in classes[group]:
            key = (k["match"], k["outcome"])
            if key in seen_rx:
                print(f"   CONFLICT {group}: {k['id']} and {seen_rx[key]} share a match")
            seen_rx[key] = k["id"]
        ends = [line for line in text.splitlines() if line[:2] in ("E ", "X ")]
        print(f"== {group}: " + ", ".join(f"{k['id']} {len(k['members'])}" for k in classes[group]) + f"; ends {ends[-3:]}")
        for kind, node, reason in loose:
            print(f"   LOOSE {kind} {node} -- {reason[:160]}")
    (SP / "classes.json").write_text(json.dumps(classes, indent=1))


if __name__ == "__main__":
    main()
