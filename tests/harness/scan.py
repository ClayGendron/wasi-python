"""Repository scanners behind the `rules` and `v1.5` checks. Each returns a list of findings,
one line each; an empty list means the rule holds."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from harness import paths

SKIP_PARTS = {"__pycache__", ".venv", ".pytest_cache", ".ruff_cache"}


def files_under(root: Path, *subdirs: str) -> list[Path]:
    out = []
    for sub in subdirs:
        base = root / sub
        if base.is_file():
            out.append(base)
        elif base.is_dir():
            out += [
                p for p in sorted(base.rglob("*")) if p.is_file() and not SKIP_PARTS & set(p.parts)
            ]
    return out


def _text(p: Path) -> str | None:
    try:
        return p.read_text()
    except (UnicodeDecodeError, OSError):
        return None


def rel(p: Path, root: Path) -> str:
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return str(p)


# ---------------------------------------------------------------------------------------------
# Constitution §4.5: no embedder names in code


def read_names(path: Path) -> list[str]:
    return [
        line.strip().lower()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def embedder_hits(root: Path, subdirs: Iterable[str], names: list[str]) -> list[str]:
    hits = []
    for p in files_under(root, *subdirs):
        r = rel(p, root)
        for name in names:
            if name in r.lower():
                hits.append(f"{r}: in the file's path")
        text = _text(p)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            if any(name in low for name in names):
                hits.append(f"{r}:{n}")
    return hits


# ---------------------------------------------------------------------------------------------
# Constitution §4.9: no test reads a clock

CLOCK = re.compile(
    r"\btime\.(time|perf_counter|monotonic|process_time|thread_time)(_ns)?\b"
    r"|\bdatetime\.(now|utcnow|today)\b|\bdate\.today\b|\btimeit\b"
    r"|\bfrom\s+time\s+import\b"
)


def clock_hits(files: Iterable[Path], root: Path) -> list[str]:
    hits = []
    for p in files:
        if p.suffix != ".py":
            continue
        for n, line in enumerate((_text(p) or "").splitlines(), 1):
            if CLOCK.search(line.split("#", 1)[0]):
                hits.append(f"{rel(p, root)}:{n}: {line.strip()}")
    return hits


# ---------------------------------------------------------------------------------------------
# Build scripts


def is_shell(p: Path) -> bool:
    if p.suffix == ".sh":
        return True
    first = (_text(p) or "").split("\n", 1)[0]
    return first.startswith("#!") and ("sh" in first.split("/")[-1])


def _code_lines(p: Path) -> list[tuple[int, str]]:
    """Lines of a shell script with full-line comments dropped."""
    return [
        (n, line)
        for n, line in enumerate((_text(p) or "").splitlines(), 1)
        if not line.lstrip().startswith("#")
    ]


FETCH = re.compile(r"\b(curl|wget|git\s+clone|uv\s+pip|uv\s+add|pip3?\s+install)\b")


def offline_install(line: str) -> bool:
    """An install that cannot fetch: from local, hash-checked files only (spec 003, Decision 13).
    It exempts a line only when `uv pip` is the line's one fetch word."""
    words = [m.group(1) for m in FETCH.finditer(line)]
    return (
        len(words) == 1
        and re.fullmatch(r"uv\s+pip", words[0]) is not None
        and re.search(r"\buv\s+pip\s+install\b", line) is not None
        and all(flag in line.split() for flag in ("--offline", "--no-index", "--require-hashes"))
        and "://" not in line
    )


def every_file(base: Path) -> list[Path]:
    """Every file under a directory, at any depth, bytecode caches left out."""
    return [p for p in sorted(base.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]


def fetch_hits(scripts: list[Path], allowed: str, root: Path) -> list[str]:
    hits = []
    for p in scripts:
        if p.name == allowed:
            continue
        lines = _code_lines(p) if is_shell(p) else enumerate((_text(p) or "").splitlines(), 1)
        for n, line in lines:
            if FETCH.search(line) and not offline_install(line):
                hits.append(f"{rel(p, root)}:{n}: {line.strip()[:100]}")
    return hits


BARE_PY = re.compile(r"(?:^|[;&|(`]|\$\(|\bthen\b|\bdo\b)\s*(python3?|pip3?)(?=\s|$)")


def bare_python_hits(scripts: list[Path], root: Path) -> list[str]:
    hits = []
    for p in scripts:
        if not is_shell(p):
            continue
        for n, line in _code_lines(p):
            if BARE_PY.search(line):
                hits.append(f"{rel(p, root)}:{n}: {line.strip()[:100]}")
    return hits


URL = re.compile(r"https?://[^\s\"')]+")
GET = re.compile(r"^\s*(?:get|research)\s+(https?://\S+)(?:\s+(\S+))?", re.M)


def url_errors(download_script: Path, pinned: Iterable[str]) -> list[str]:
    """Every pin is named on a `get <url> <name>` line (or is a literal URL's basename)."""
    text = _text(download_script) or ""
    basenames = {u.rstrip("/").rsplit("/", 1)[-1] for u in URL.findall(text)}
    basenames |= {name for _, name in GET.findall(text) if name}
    return [
        f"{name}: no literal URL ends in it in {download_script.name}"
        for name in sorted(pinned)
        if name not in basenames
    ]


def download_script_errors(download_script: Path) -> list[str]:
    text = "\n".join(line for _, line in _code_lines(download_script))
    errors = []
    if not re.search(r"(shasum\s+-a\s*256|sha256sum)\b[^\n]*\s-c\b[^\n]*SHA256SUMS", text):
        errors.append("it never checks the downloads against SHA256SUMS (`shasum -a 256 -c`)")
    if re.search(r"(>{1,2}\s*\S*SHA256SUMS|\btee\b[^\n]*SHA256SUMS)", text):
        errors.append("it writes SHA256SUMS instead of only reading it")
    return errors


PATH_TOKEN = re.compile(r"(?:\$HERE|\$\{HERE\}|@S12@|@ROOT@)/([A-Za-z0-9_.][\w./-]*)")
GENERATED_ROOTS = {"build", "downloads", ".venv-build"}


def recipe_path_errors(files: Iterable[Path], root: Path) -> list[str]:
    errors = []
    for p in files:
        for n, line in enumerate((_text(p) or "").splitlines(), 1):
            for token in PATH_TOKEN.findall(line):
                token = token.rstrip(".")
                if token.split("/")[0] in GENERATED_ROOTS:
                    continue
                if not (root / token).exists():
                    errors.append(f"{rel(p, root)}:{n}: names {token}, which does not exist")
    return errors


def toolchain_errors(pinned: Iterable[str]) -> list[str]:
    names = [n.lower() for n in pinned]
    errors = []
    for tool in ("wasi-sdk", "wasmtime"):
        mine = [n for n in names if n.startswith(tool + "-")]
        if not any("x86_64-linux" in n or "linux-x86_64" in n for n in mine):
            errors.append(f"{tool}: no Linux x86_64 pin")
        if not any("arm64-macos" in n or "aarch64-macos" in n for n in mine):
            errors.append(f"{tool}: no macOS arm64 pin")
    return errors


CPP_EH_FLAGS = ("'-fwasm-exceptions'", "'-wasm-use-legacy-eh=false'")
CPP_EH_AGAINST = ("'-fno-exceptions'", "'-wasm-use-legacy-eh=true'", "'-fno-wasm-exceptions'")


def cpp_exception_errors(root: Path) -> list[str]:
    """Every C++ object is compiled, and the binary linked, for standard-form exceptions (spec 005,
    Decision 9): a cross file without the flags compiles C++ whose `throw` is never caught."""
    errors = []
    for cross in ("recipes/wasi-numpy.cross", "recipes/wasi-pandas.cross"):
        lines = [t for t in (root / cross).read_text().splitlines() if t.startswith("cpp_args")]
        if len(lines) != 1:
            errors.append(f"{cross}: {len(lines)} cpp_args lines, not 1")
            continue
        errors += [f"{cross}: cpp_args lacks {f}" for f in CPP_EH_FLAGS if f not in lines[0]]
        errors += [f"{cross}: cpp_args has {f}" for f in CPP_EH_AGAINST if f in lines[0]]
    link = (root / "scripts/steps/60_link.sh").read_text().splitlines()
    if not any("-lunwind" in t and t.lstrip().startswith("echo") for t in link):
        errors.append("scripts/steps/60_link.sh: Setup.local does not link -lunwind")
    flag = 'LDFLAGS_NODIST="-fwasm-exceptions"'
    for target in ("make -j8 all", "make -n python.wasm"):
        calls = [t for t in link if t.lstrip().startswith(target)]
        if not calls or not all(flag in t for t in calls):
            errors.append(f"scripts/steps/60_link.sh: `{target}` without {flag}")
    return errors


def pure_python_errors(pinned: Iterable[str]) -> list[str]:
    names = [paths.norm(n) for n in pinned]
    return [
        f"{pkg}: not pinned"
        for pkg in ("python-dateutil", "tzdata", "six")
        if not any(n.startswith(pkg + "-") for n in names)
    ]


# ---------------------------------------------------------------------------------------------
# Context documents

SPEC_HEADER = ("Status", "Owner", "Kind", "Depends on", "Research it stands on")
SPEC_SECTIONS = ("Decisions", "Intent", "Design", "Scope", "Acceptance criteria", "Landing notes")


def spec_shape_errors(path: Path) -> list[str]:
    text = path.read_text()
    errors = []
    for field in SPEC_HEADER:
        if not re.search(rf"^- \*\*{re.escape(field)}:\*\*", text, re.M):
            errors.append(f"{path.name}: no '{field}' header line")
    for section in SPEC_SECTIONS:
        if not re.search(rf"^## {re.escape(section)}\s*$", text, re.M):
            errors.append(f"{path.name}: no '## {section}' section")
    return errors


def strip_code(text: str) -> str:
    text = re.sub(r"^```.*?^```", "", text, flags=re.M | re.S)
    return re.sub(r"`[^`\n]*`", "", text)


OPEN = re.compile(r"\bTBD\b|\bTODO\b|open question", re.I)


def open_question_hits(path: Path) -> list[str]:
    hits = []
    for line in strip_code(path.read_text()).splitlines():
        if line.startswith("#") and "question" in line.lower():
            hits.append(f"{path.name}: a questions heading: {line.strip()}")
        elif OPEN.search(line):
            hits.append(f"{path.name}: {line.strip()[:100]}")
    return hits


def status_line(text: str) -> str:
    m = re.search(r"^- \*\*Status:\*\*(.*)$", text, re.M)
    return m[1].strip().lower() if m else ""


def landed_review_errors(path: Path, reviews: Path) -> list[str]:
    text = path.read_text()
    if not status_line(text).startswith("landed"):
        return []
    notes = text.split("## Landing notes", 1)[-1]
    cited = re.findall(r"reviews/([\w.-]+\.md)", notes)
    if not cited:
        return [f"{path.name}: landed, but its landing notes cite no review"]
    return [
        f"{path.name}: cites reviews/{c}, which does not exist"
        for c in cited
        if not (reviews / c).is_file()
    ]


def memo_label_errors(path: Path) -> list[str]:
    text = path.read_text()
    if "placeholder" in status_line(text):
        return []
    if re.search(r"\b(EXECUTED|READ|INFERRED)\b", text):
        return []
    return [f"{path.name}: no EXECUTED, READ or INFERRED label"]


def prior_art_errors(prior_art: Path) -> list[str]:
    index = (prior_art / "README.md").read_text()
    rows = {}
    for line in index.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        m = re.fullmatch(r"`([^`]+)`.*", cells[0]) if cells else None
        if m and len(cells) >= 3:
            rows[m[1]] = cells[2]
    errors = []
    for d in sorted(p for p in prior_art.iterdir() if p.is_dir()):
        if d.name not in rows or not rows[d.name]:
            errors.append(f"{d.name}: no row with a licence in context/prior_art/README.md")
        if not any(re.match(r"(licen[cs]e|copying)", f.name, re.I) for f in d.iterdir()):
            errors.append(f"{d.name}: no licence file in the clone")
    return errors


# ---------------------------------------------------------------------------------------------
# How a check reports its findings (spec 002, Decision 4)


LINE_REF = re.compile(r":\d+(?=[:\s]|$)")


def digest(findings: list[str]) -> str:
    """A short hash of the exact set of findings. A gap matches it, so a gap admits exactly
    the findings it was written for: one more, or one fewer, is a different failure. Line
    numbers are left out, so an edit that only moves a finding does not disturb its gap."""
    return paths.sha256_bytes("\n".join(sorted(LINE_REF.sub("", f) for f in findings)).encode())[
        :12
    ]


def report(findings: list[str], what: str = "findings") -> str:
    shown = "; ".join(findings[:5]) + (f"; +{len(findings) - 5} more" if len(findings) > 5 else "")
    return f"{what}: {len(findings)} finding(s), digest {digest(findings)}: {shown}"


# ---------------------------------------------------------------------------------------------
# The release workflow's provenance (spec 009)

ATTEST_PERMISSIONS = {"id-token: write", "attestations: write", "contents: read"}
ATTEST_USES = re.compile(r"uses:\s*actions/attest@[0-9a-f]{40}\b")
VERIFY_FLAGS = ("--repo", "--signer-workflow", "--source-ref", "--deny-self-hosted-runners")
TAG_ONLY = "github.event_name == 'push' && github.ref_type == 'tag'"
ID_TOKEN = re.compile(r"id-token:\s*write|write-all")


def without_comments(text: str) -> str:
    """The workflow with its comments removed, so a commented-out step or name counts for nothing:
    whole-line comments, and trailing ` # …` comments."""
    out = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        out.append(re.sub(r"\s+#\s.*$", "", line))
    return "\n".join(out) + "\n"


def workflow_jobs(text: str) -> dict[str, list[str]]:
    """The workflow's jobs, each as its lines, read as text (the judge has no YAML library): a job
    starts at a two-space-indented `name:` line under `jobs:`."""
    jobs: dict[str, list[str]] = {}
    current: list[str] | None = None
    in_jobs = False
    for line in text.splitlines():
        if line.startswith("jobs:"):
            in_jobs = True
            continue
        if not in_jobs:
            continue
        m = re.fullmatch(r"  ([A-Za-z0-9_-]+):\s*", line)
        if m:
            current = jobs.setdefault(m[1], [])
        elif line and not line.startswith(" "):
            in_jobs, current = False, None
        elif current is not None:
            current.append(line)
    return jobs


def _job_field(lines: list[str], key: str) -> str | None:
    for line in lines:
        m = re.fullmatch(rf"    {key}:\s*(.*)", line)
        if m:
            return m[1].strip()
    return None


def _job_permissions(lines: list[str]) -> set[str]:
    out, inside = set(), False
    for line in lines:
        if re.fullmatch(r"    permissions:\s*", line):
            inside = True
            continue
        if inside:
            if line.startswith("      ") and line.strip():
                out.add(" ".join(line.split()))
            else:
                break
    return out


def release_attestation_errors(text: str) -> list[str]:
    """Every rule of spec 009, Decision 6, as one line per breach, on the workflow without its
    comments."""
    text = without_comments(text)
    jobs = workflow_jobs(text)
    if "attest" not in jobs:
        return ["no attest job"]
    attest, publish = jobs["attest"], jobs.get("publish", [])
    errors = []
    if _job_field(attest, "if") != TAG_ONLY or _job_field(publish, "if") != TAG_ONLY:
        errors.append("attest's or publish's if: is not the pushed-tag condition")
    needs_attest = _job_field(attest, "needs") or ""
    if not {"build", "verify"} <= set(re.findall(r"[a-z_-]+", needs_attest)):
        errors.append("attest does not need build and verify")
    if _job_permissions(attest) != ATTEST_PERMISSIONS:
        errors.append(f"attest's permissions are not {sorted(ATTEST_PERMISSIONS)}")
    body = "\n".join(attest)
    if not ATTEST_USES.search(body):
        errors.append("no actions/attest step pinned by a 40-hex commit")
    if not re.search(r"subject-path:\s*release-assets/\*\s*$", body, re.M):
        errors.append("subject-path is not release-assets/*")
    logical = body.replace("\\\n", " ").splitlines()  # a `\`-continued command is one line
    verify = [line for line in logical if "gh attestation verify" in line]
    if not verify or any(not all(flag in line for flag in VERIFY_FLAGS) for line in verify):
        errors.append(
            "a gh attestation verify without --repo, --signer-workflow, --source-ref and "
            "--deny-self-hosted-runners"
        )
    if re.search(r"^    continue-on-error:", body, re.M):
        errors.append("attest has a job-level continue-on-error:")
    if re.search(r"\|\||set \+e", body):
        errors.append("a step of attest swallows a failure (|| or set +e)")
    if re.search(r"setup-uv|uv run", body):
        errors.append("attest runs setup-uv or uv")
    order = [
        next((i for i, line in enumerate(attest) if marker in line), None)
        for marker in ("actions/download-artifact@", "actions/attest@", "gh attestation verify")
    ]
    if None in order or order != sorted(order):
        errors.append("attest's steps are not download, attest, verify, in that order")
    if re.search(r"^      (- )?\s*(if|continue-on-error):", body, re.M):
        errors.append("a step of attest has if: or continue-on-error:")
    if ID_TOKEN.search(text.split("\njobs:", 1)[0]):
        errors.append("the workflow-level permissions grant id-token: write or write-all")
    for name, lines in jobs.items():
        if name not in ("attest", "pypi") and ID_TOKEN.search("\n".join(lines)):
            errors.append(f"{name} has id-token: write or write-all")
    if "attest" not in re.findall(r"[a-z_-]+", _job_field(publish, "needs") or ""):
        errors.append("publish does not need attest")
    return errors


# ---------------------------------------------------------------------------------------------
# The build hosts (spec 012, Decision 1)

HOST_NAMES = ("WASI_SDK_DIR", "WASMTIME_DIR", "HOST_PYTHON_ARCHIVE", "CYTHON_WHEEL", "NINJA_WHEEL")
# The file in downloads/ each host name stands for: a directory name is its tarball's stem.
HOST_FILE = {"WASI_SDK_DIR": "{}.tar.gz", "WASMTIME_DIR": "{}.tar.xz"}
CONF_HOST_LINE = re.compile(rf"^([A-Z][A-Z0-9_]*?)_({'|'.join(HOST_NAMES)})=(\S+)$", re.M)
SH_HOST_KEY = re.compile(r"\bHOST_KEY=([A-Z][A-Z0-9_]*)")


def host_case_branches(text: str) -> dict[str, list[str]]:
    """The file names the `get` lines fetch in each branch of the download script's
    `case "$HOST_KEY" in … esac`."""
    branches: dict[str, list[str]] = {}
    current: list[str] | None = None
    inside = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            continue
        if re.fullmatch(r'case\s+"?\$\{?HOST_KEY\}?"?\s+in', s):
            inside = True
        elif inside and s == "esac":
            break
        elif inside and (m := re.fullmatch(r"([A-Z][A-Z0-9_]*)\)", s)):
            current = branches.setdefault(m[1], [])
        elif inside and s == ";;":
            current = None
        elif inside and current is not None and (g := GET.match(line)):
            current.append(g[2] or g[1].rstrip("/").rsplit("/", 1)[-1])
    return branches


def host_table_errors(
    conf: str, sh_keys: Iterable[str], py_keys: Iterable[str], download: str, pinned: Iterable[str]
) -> list[str]:
    """Every build host has all five host names in `line.conf`; each names a pinned file that the
    download script fetches in that host's own `case` branch; and `line.conf`, `line.sh`,
    `line.py` and `00_download.sh` know the same hosts."""
    pinned = set(pinned)
    table: dict[str, dict[str, str]] = {}
    for key, name, value in CONF_HOST_LINE.findall(conf):
        table.setdefault(key, {})[name] = value
    errors = [
        f"line.conf: {name} is set for every host, not per host key"
        for name in HOST_NAMES
        if re.search(rf"^{name}=", conf, re.M)
    ]
    if not table:
        errors.append("line.conf: no host key names a host's inputs")
    branches = host_case_branches(download)
    for where, keys in (
        ("line.sh", set(sh_keys)),
        ("line.py", set(py_keys)),
        ("00_download.sh", set(branches)),
    ):
        if keys != set(table):
            errors.append(f"{where}: hosts {sorted(keys)}, but line.conf has {sorted(table)}")
    for key in sorted(table):
        for name in HOST_NAMES:
            value = table[key].get(name)
            if value is None:
                errors.append(f"line.conf: no {key}_{name}")
                continue
            file = HOST_FILE.get(name, "{}").format(value)
            if file not in pinned:
                errors.append(f"{key}_{name}: {file} is not pinned")
            if file not in branches.get(key, []):
                errors.append(f"{key}_{name}: {file} is not fetched in the {key} branch")
    return errors


# ---------------------------------------------------------------------------------------------
# The release workflow's second-host rebuild (spec 012, Decision 7)

# arm64 Linux only: x86_64 Linux is pinned but its rebuild is not yet byte-identical, so it is
# left out of the gate (spec 012, Decision 8's fallback, taken in its landing notes).
REBUILD_RUNNERS = ("ubuntu-24.04-arm",)


def _needs(lines: list[str]) -> set[str]:
    return set(re.findall(r"[a-z0-9_-]+", _job_field(lines, "needs") or ""))


def rebuild_gate_errors(text: str) -> list[str]:
    """Every rule of spec 012, Decision 7, as one line per breach, on the workflow without its
    comments: a rebuild on each gated runner beside the build, a same-bytes job that compares every
    rebuild's SHA256SUMS with the set's byte for byte, and nothing signed or published before it."""
    text = without_comments(text)
    jobs = workflow_jobs(text)
    rebuild, same = jobs.get("rebuild"), jobs.get("same-bytes")
    errors = [
        f"no {name} job" for name, job in (("rebuild", rebuild), ("same-bytes", same)) if not job
    ]
    if errors:
        return errors
    body = "\n".join(rebuild)
    same_body = "\n".join(line for line in same if not line.startswith("    runs-on:"))
    m = re.search(r"^\s+os:\s*\[([^\]]*)\]", body, re.M)
    runners = [r.strip() for r in m[1].split(",")] if m else []
    errors += [f"rebuild's matrix lacks {r}" for r in REBUILD_RUNNERS if r not in runners]
    if _job_field(rebuild, "runs-on") != "${{ matrix.os }}":
        errors.append("rebuild does not run on its matrix's runner")
    if not re.search(r"^\s+(- )?run:\s*scripts/build\.sh\s*$", body, re.M):
        errors.append("rebuild does not run scripts/build.sh")
    if not re.search(r"^\s+path:\s*build/artifacts/SHA256SUMS\s*$", body, re.M) or not re.search(
        r"^\s+name:\s*\S*\$\{\{\s*matrix\.os\s*\}\}\S*\s*$", body, re.M
    ):
        errors.append("rebuild does not upload build/artifacts/SHA256SUMS under a name per runner")
    for name, lines in (("rebuild", rebuild), ("same-bytes", same)):
        joined = "\n".join(lines)
        if _job_field(lines, "if") is not None:
            errors.append(f"{name} has a job-level if: (a dry run must run it)")
        if _job_permissions(lines) - {"contents: read"}:
            errors.append(f"{name}'s permissions are more than contents: read")
        if re.search(r"^    continue-on-error:", joined, re.M):
            errors.append(f"{name} has a job-level continue-on-error:")
    if not {"build", "rebuild"} <= _needs(same):
        errors.append("same-bytes does not need build and rebuild")
    # One operand a rebuild's download, the other not: comparing the set's file with itself, or
    # one rebuild with another, proves nothing (the build review, mutation M18).
    pairs = re.findall(r"\bcmp\s+(\S+)\s+(\S+)", same_body)
    if not any(("rebuilds/" in a) != ("rebuilds/" in b) for a, b in pairs):
        errors.append("same-bytes does not compare a rebuild's SHA256SUMS with the set's (cmp)")
    errors += [
        f"same-bytes does not name {r}'s SHA256SUMS"
        for r in REBUILD_RUNNERS
        if not re.search(
            rf"^\s+name:\s*rebuild-{re.escape(r)}\s*\n\s+path:\s*rebuilds/{re.escape(r)}\s*$",
            same_body,
            re.M,
        )
        or not re.search(rf"(?<![\w.-]){re.escape(r)}(?![\w.-])", same_body.split("run:", 1)[-1])
    ]
    if re.search(r"\|\||set \+e", same_body):
        errors.append("a step of same-bytes swallows a failure (|| or set +e)")
    for name in ("attest", "publish"):
        if "same-bytes" not in _needs(jobs.get(name, [])):
            errors.append(f"{name} does not need same-bytes")
    return errors
