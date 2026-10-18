"""Repository scanners behind the `rules` and `v1.5` checks. Each returns a list of findings,
one line each; an empty list means the rule holds."""

from __future__ import annotations

import ast
import json
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
            if p.suffix == ".patch" and not _our_patch_line(line):
                continue  # a patch's context and removed lines are upstream's text (spec 020)
            low = line.lower()
            if any(name in low for name in names):
                hits.append(f"{r}:{n}")
    return hits


def _our_patch_line(line: str) -> bool:
    """A patch line this project wrote: an added line, or one naming a file."""
    if line.startswith(("+++", "---")):
        return True
    return line.startswith(("+", "diff --git "))


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


# `rm` as a word anywhere (after `if`, `!`, `xargs`, `command`, an assignment...), or `\rm`,
# `/bin/rm`, `/usr/bin/rm`; a string or a trailing comment can match too, which fails closed.
RM = re.compile(r"(?<![\w./-])(?:\\|/(?:usr/)?bin/)?rm((?:\s+-[-A-Za-z]+)+)")
REMOVE_SH = "scripts/steps/remove.sh"


def _recursive_force(flags: str) -> bool:
    short = "".join(t[1:] for t in flags.split() if not t.startswith("--"))
    long = {t for t in flags.split() if t.startswith("--")}
    recursive = bool(set(short) & {"r", "R"}) or "--recursive" in long
    return recursive and ("f" in short or "--force" in long)


def bare_rm_hits(scripts: list[Path], root: Path) -> list[str]:
    """A recursive, forced `rm` in a build script outside remove.sh, in any spelling (`-rf`,
    `-fr`, `-Rf`, `-r -f`, `--recursive --force`): Finder can make it fail, so every removal goes
    through `remove`, which retries (spec 018)."""
    hits = []
    for p in scripts:
        if not is_shell(p) or rel(p, root) == REMOVE_SH:
            continue
        joined: list[tuple[int, str]] = []  # a line ending in `\` continues on the next
        for n, line in _code_lines(p):
            if joined and joined[-1][1].endswith("\\"):
                joined[-1] = (joined[-1][0], joined[-1][1][:-1] + " " + line)
            else:
                joined.append((n, line.rstrip()))
        for n, line in joined:
            if any(_recursive_force(m.group(1)) for m in RM.finditer(line)):
                hits.append(f"{rel(p, root)}:{n}: {line.strip()[:100]}")
    return hits


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
CPP_CROSS_FILES = (
    "recipes/wasi-numpy.cross",
    "recipes/wasi-pandas.cross",
    "recipes/wasi-plot-libs.cross",
    "recipes/wasi-matplotlib.cross",
)
# kiwisolver's C++ is compiled by step 55 itself: its flags variable, and the compile that uses it.
CPP_DIRECT = "scripts/steps/55_matplotlib.sh"
CPP_EH_AGAINST = ("'-fno-exceptions'", "'-wasm-use-legacy-eh=true'", "'-fno-wasm-exceptions'")


def cpp_exception_errors(root: Path) -> list[str]:
    """Every C++ object is compiled, and the binary linked, for standard-form exceptions (spec 005,
    Decision 9): a cross file without the flags compiles C++ whose `throw` is never caught. Every
    C++ build is judged (spec 023): numpy's and pandas' cross files, HarfBuzz's (step 37),
    matplotlib's, and kiwisolver's compile line in step 55."""
    errors = []
    for cross in CPP_CROSS_FILES:
        lines = [t for t in (root / cross).read_text().splitlines() if t.startswith("cpp_args")]
        if len(lines) != 1:
            errors.append(f"{cross}: {len(lines)} cpp_args lines, not 1")
            continue
        errors += [f"{cross}: cpp_args lacks {f}" for f in CPP_EH_FLAGS if f not in lines[0]]
        errors += [f"{cross}: cpp_args has {f}" for f in CPP_EH_AGAINST if f in lines[0]]
    direct = (root / CPP_DIRECT).read_text().splitlines()
    flags = [t for t in direct if t.startswith("CXX_EH=")]
    if len(flags) != 1:
        errors.append(f"{CPP_DIRECT}: {len(flags)} CXX_EH= lines, not 1")
    else:
        errors += [
            f"{CPP_DIRECT}: CXX_EH lacks {f}" for f in CPP_EH_FLAGS if f[1:-1] not in flags[0]
        ]
        errors += [f"{CPP_DIRECT}: CXX_EH has {f}" for f in CPP_EH_AGAINST if f[1:-1] in flags[0]]
    compiles = [t for t in direct if t.lstrip().startswith("$CXX ")]
    if not compiles or not all("$CXX_EH" in t for t in compiles):
        errors.append(f"{CPP_DIRECT}: a $CXX compile without $CXX_EH")
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
# The compiler each host runs (spec 040, Decisions 4 and 5): an arm64 build of the pinned clang on
# every host, natively on the arm64 hosts and under the pinned emulator on x86_64 Linux.

COMPILER_NAME = "COMPILER_SDK_DIR"
EMULATION_NAMES = (
    "EMULATOR_DEB",
    "AARCH64_LIBC_DEB",
    "AARCH64_LIBSTDCXX_DEB",
    "AARCH64_LIBGCC_DEB",
    "AARCH64_LIBTINFO_DEB",
)
CONF_COMPILER_LINE = re.compile(
    rf"^([A-Z][A-Z0-9_]*?)_({'|'.join((COMPILER_NAME, *EMULATION_NAMES))})=(\S+)$", re.M
)
# What step 10's code must name: the launcher, the guest's root and its empty loader cache, and
# the gate's probes (the InstalledDir, the cpp mode, the loader-cache trace).
STEP_10_WORDS = ("clang-emulated", "aarch64-root", "ld.so.cache", "InstalledDir", "clang-cpp")
STEP_10_STRACE = re.compile(r"qemu-aarch64\S*\s+-strace\b")
LAUNCHER_FLAGS = ("-U LD_PRELOAD", "-U LD_LIBRARY_PATH", "-U LD_AUDIT")
# The name the launcher was called by -> the driver mode it must add (None: no mode).
LAUNCHER_MODES = {"clang": None, "clang++": "--driver-mode=g++", "clang-cpp": "--driver-mode=cpp"}


def code_text(p: Path) -> str | None:
    """A shell script's text with its full-line comments dropped, or None if it is missing."""
    return "\n".join(line for _, line in _code_lines(p)) if p.is_file() else None


def _maps(launcher: str, name: str, mode: str | None) -> bool:
    """The launcher has a `case` arm for the name, adding exactly its mode (or none)."""
    arm = re.search(rf"^\s*{re.escape(name)}\)(.*)$", launcher, re.M)
    if arm is None:
        return False
    return mode in arm[1] if mode else "--driver-mode" not in arm[1]


def compiler_table_errors(
    conf: str, download: str, pinned: Iterable[str], step_10: str, launcher: str | None
) -> list[str]:
    """Every rule of spec 040, Decision 7's rule check, one line per breach. `step_10` and
    `launcher` are scripts/steps/10_tools.sh and scripts/clang-emulated without their comment
    lines (None: the launcher is missing), so a comment satisfies nothing."""
    pinned = set(pinned)
    own = {k: v for k, name, v in CONF_HOST_LINE.findall(conf) if name == "WASI_SDK_DIR"}
    table: dict[str, dict[str, str]] = {}
    for key, name, value in CONF_COMPILER_LINE.findall(conf):
        table.setdefault(key, {})[name] = value
    branches = host_case_branches(download)
    errors = [
        f"line.conf: {name} is set for every host, not per host key"
        for name in (COMPILER_NAME, *EMULATION_NAMES)
        if re.search(rf"^{name}=", conf, re.M)
    ]
    for key in sorted(own):
        names = table.get(key, {})
        compiler = names.get(COMPILER_NAME)
        if compiler is None:
            errors.append(f"line.conf: no {key}_{COMPILER_NAME}")
            continue
        if "arm64" not in compiler:
            errors.append(f"{key}_{COMPILER_NAME}: {compiler} is not an arm64 SDK")
        files = {COMPILER_NAME: f"{compiler}.tar.gz"}
        emulation = [n for n in EMULATION_NAMES if n in names]
        if compiler == own[key]:
            if emulation:
                errors.append(f"{key} compiles with its own SDK but has {', '.join(emulation)}")
        else:
            if compiler not in own.values():
                errors.append(f"{key}_{COMPILER_NAME}: {compiler} is no host's own WASI_SDK_DIR")
            errors += [f"line.conf: no {key}_{n}" for n in EMULATION_NAMES if n not in names]
            files.update({n: names[n] for n in emulation})
        for name, file in files.items():
            if file not in pinned:
                errors.append(f"{key}_{name}: {file} is not pinned")
            if file not in branches.get(key, []):
                errors.append(f"{key}_{name}: {file} is not fetched in the {key} branch")
    errors += [f"10_tools.sh does not name {w}" for w in STEP_10_WORDS if w not in step_10]
    if not STEP_10_STRACE.search(step_10):
        errors.append("10_tools.sh does not trace the guest's loader (qemu-aarch64 -strace)")
    if launcher is None:
        return [*errors, "scripts/clang-emulated is missing"]
    errors += [
        f"scripts/clang-emulated does not pass {f}" for f in LAUNCHER_FLAGS if f not in launcher
    ]
    if not (re.search(r"\bQEMU_", launcher) and re.search(r"\bunset\b", launcher)):
        errors.append("scripts/clang-emulated does not unset the QEMU_ variables")
    errors += [
        f"scripts/clang-emulated does not map {name} to {mode or 'no mode'}"
        for name, mode in LAUNCHER_MODES.items()
        if not _maps(launcher, name, mode)
    ]
    return errors


# ---------------------------------------------------------------------------------------------
# The release workflow's second-host rebuild (spec 012, Decision 7)

# arm64 Linux, and x86_64 Linux, which compiles with the arm64 Linux SDK's clang under the pinned
# qemu (spec 040). Each runner's job time limit, in minutes: an emulated rebuild is slower, and a
# hung arm64 job still frees the gate after two hours (spec 040, Decision 6).
REBUILD_RUNNERS = ("ubuntu-24.04-arm", "ubuntu-24.04")
REBUILD_TIMEOUTS = {"ubuntu-24.04-arm": 120, "ubuntu-24.04": 360}


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
    if _job_field(rebuild, "timeout-minutes") != "${{ matrix.timeout }}":
        errors.append("rebuild's timeout-minutes does not come from its matrix")
    given = dict(re.findall(r"^\s+- os:\s*(\S+)\s*\n\s+timeout:\s*(\d+)\s*$", body, re.M))
    errors += [
        f"rebuild's matrix does not give {r} {minutes} minutes"
        for r, minutes in REBUILD_TIMEOUTS.items()
        if given.get(r) != str(minutes)
    ]
    # The core count beside every time figure, and any binfmt_misc entry that would run an aarch64
    # ELF through the runner's own qemu and hide a gap in the launcher's closure (spec 040).
    for fact, pattern in (
        ("nproc", r"^\s+nproc\s*$"),
        ("binfmt_misc", r"/proc/sys/fs/binfmt_misc"),
    ):
        if not re.search(pattern, body, re.M):
            errors.append(f"rebuild's tools step does not print {fact}")
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
    errors += [
        f"same-bytes does not name {r}'s rebuilt wheel"
        for r in REBUILD_RUNNERS
        if not re.search(
            rf"^\s+name:\s*rebuild-wheel-{re.escape(r)}\s*\n\s+path:\s*rebuilt-wheels/{re.escape(r)}\s*$",
            same_body,
            re.M,
        )
    ]
    # Both of same-bytes' loops, the set's SHA256SUMS and spec 016's wheel, run over every runner.
    for what, marker in (("SHA256SUMS", "rebuilds/$"), ("wheel", "rebuilt-wheels/$")):
        looped = {
            runner
            for step in re.split(r"^      - ", same_body, flags=re.M)
            if marker in step
            for m in re.finditer(r"\bfor\s+\w+\s+in\s+([^;\n]*);\s*do\b", step)
            for runner in m[1].split()
        }
        errors += [
            f"same-bytes' {what} loop does not run over {r}"
            for r in REBUILD_RUNNERS
            if r not in looped
        ]
    if re.search(r"\|\||set \+e", same_body):
        errors.append("a step of same-bytes swallows a failure (|| or set +e)")
    for name in ("attest", "publish"):
        if "same-bytes" not in _needs(jobs.get(name, [])):
            errors.append(f"{name} does not need same-bytes")
    return errors


# ---------------------------------------------------------------------------------------------
# A module-level name bound twice: the second silently replaces the first, so checks that used
# the first run the second's code (spec 019's rebase redefined `CTRL_C` and lost two checks).


def _bound(node: ast.stmt) -> list[str]:
    """The names a module-level statement binds: definitions, imports and assignment targets
    (tuples and starred ones included). Names bound inside `if`, `try`, `for` or `with` are not
    counted: their branches are often real alternatives (a `TYPE_CHECKING` import, a fallback)."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        decorators = [ast.unparse(d) for d in node.decorator_list]
        if any(d.endswith("overload") or d.endswith(".register") for d in decorators):
            return []  # typing's overloads and singledispatch's registrations repeat by design
        return [node.name]
    if isinstance(node, ast.ClassDef):
        return [node.name]
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return [(a.asname or a.name).split(".")[0] for a in node.names if a.name != "*"]
    targets: list[ast.expr] = []
    if isinstance(node, ast.Assign):
        targets = list(node.targets)
    elif isinstance(node, ast.AnnAssign) and node.value is not None:
        targets = [node.target]
    names = []
    while targets:
        t = targets.pop(0)
        if isinstance(t, ast.Name):
            names.append(t.id)
        elif isinstance(t, (ast.Tuple, ast.List)):
            targets[:0] = t.elts
        elif isinstance(t, ast.Starred):
            targets.insert(0, t.value)
    return names


def duplicate_name_hits(files: Iterable[Path], root: Path) -> list[str]:
    hits = []
    for p in files:
        if p.suffix != ".py":
            continue
        try:
            tree = ast.parse(p.read_text(), str(p))
        except (SyntaxError, UnicodeDecodeError):
            continue
        # A guest program under tests/jobs/ rebinds its working names on purpose; there only a
        # constant (an upper-case name), a function or a class bound twice is the hazard.
        guest = rel(p, root).startswith("tests/jobs/")
        seen: dict[str, int] = {}
        defined: set[str] = set()
        for node in tree.body:
            names = _bound(node)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.update(names)
            for name in names:
                hazard = not guest or name.isupper() or name in defined
                if name in seen and hazard:
                    hits.append(
                        f"{rel(p, root)}:{node.lineno}: {name} (first bound at {seen[name]})"
                    )
                seen.setdefault(name, node.lineno)
    return hits


# Constitution §4.1: carried patches, recorded and temporary (spec 020)

PATCH_NAME = re.compile(r"(\d{4})-[A-Za-z0-9][A-Za-z0-9._-]*\.patch")
DRAFT_FIELDS = ("Project", "Against", "Status", "Title", "Files", "Why we carry it")
STATUS = re.compile(r"drafted|sent \S+|merged \S+|released (\S+)")
AUTOTOOLS_INPUTS = {"configure.ac", "configure.in", "Makefile.am"}
PATCH_SHAPES = {  # the line's start -> why it is refused
    "new file mode 120000": "adds a link",
    "new mode 120000": "makes a link",
    "old mode": "changes a mode",
    "new mode": "changes a mode",
    "GIT binary patch": "has a binary hunk",
    "Binary files": "has a binary hunk",
    "rename from": "renames a file",
    "copy from": "copies a file",
}
CARRIED_ROW = re.compile(r"upstream patches carried: (\d+)")


def _version(text: str) -> tuple[int, ...] | None:
    try:
        return tuple(int(x) for x in text.split("."))
    except ValueError:
        return None


def _git_reads(text: str) -> tuple[list[str], str, str]:
    """What git itself would apply: the paths (`--numstat -z`), the summary (modes, creations,
    deletions) and any error; outside any repository, with the caller's configuration cleared."""
    import os
    import shutil
    import subprocess
    import tempfile

    git = shutil.which("git")
    if git is None:
        return [], "", "git is not on PATH, so the patch cannot be read as git reads it"
    with tempfile.TemporaryDirectory() as home:
        env = {"PATH": os.environ.get("PATH", ""), "HOME": home, "XDG_CONFIG_HOME": home}
        env.update(
            GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_CEILING_DIRECTORIES=home
        )
        work = Path(home) / "w"  # below the ceiling, so git never finds an enclosing repository
        work.mkdir()
        out = {}
        for flag in ("--numstat", "--summary"):
            cmd = [git, "-c", "core.quotePath=false", "apply", flag]
            cmd += ["-z", "-"] if flag == "--numstat" else ["-"]
            r = subprocess.run(cmd, input=text.encode(), capture_output=True, cwd=work, env=env)
            if r.returncode != 0:
                return [], "", r.stderr.decode(errors="replace").strip().splitlines()[0]
            out[flag] = r.stdout.decode(errors="replace")
    paths = [rec.split("\t", 2)[2] for rec in out["--numstat"].split("\0") if rec.count("\t") >= 2]
    return paths, out["--summary"], ""


def patch_shape_errors(text: str, where: str) -> tuple[list[str], set[str]]:
    """What a patch may not contain (spec 020, Decision 6), and the paths it touches, as git reads
    it: a plain `---`/`+++` section after a hunk, or names that differ from `diff --git`, are
    applied by git and so are judged here too (the build review, finding 2)."""
    errors: list[str] = []
    for n, line in enumerate(text.splitlines(), 1):
        for start, why in PATCH_SHAPES.items():
            if line.startswith(start):
                errors.append(f"{where}:{n}: {why}")
        if line.startswith("new file mode ") and line.split()[-1] != "100644":
            errors.append(f"{where}:{n}: adds a file with mode {line.split()[-1]}")
    paths, summary, failed = _git_reads(text)
    if failed:
        return [*errors, f"{where}: git cannot read it: {failed}"], set()
    for line in summary.splitlines():
        words = line.split()
        if words[:1] in (["create"], ["delete"]) and words[2] not in ("100644",):
            errors.append(f"{where}: {line.strip()}: only plain files (mode 100644)")
        elif words[:2] == ["mode", "change"] or words[:1] in (["rename"], ["copy"]):
            errors.append(f"{where}: {line.strip()}")
    touched = set()
    for path in paths:
        parts = path.split("/")
        if path.startswith("/") or any(part in ("", ".", "..") for part in parts):
            errors.append(f"{where}: {path!r} is outside the tree")
            continue
        touched.add(path)
        if parts[-1] in paths_os_litter():
            errors.append(f"{where}: touches {path}, a name Finder or Explorer writes (spec 026)")
        if parts[-1] in AUTOTOOLS_INPUTS or parts[-1].endswith(".m4"):
            errors.append(f"{where}: changes the autotools input {path}; patch its output")
    if not touched:
        errors.append(f"{where}: changes no file")
    return errors, touched


def _draft_errors(draft: Path, top: str, touched: set[str], where: str) -> list[str]:
    lines = draft.read_text().splitlines()
    errors, fields = [], {}
    for i, field in enumerate(DRAFT_FIELDS):
        m = re.fullmatch(rf"- \*\*{re.escape(field)}:\*\* (.+)", lines[i] if i < len(lines) else "")
        if m is None:
            errors.append(f"{where}: line {i + 1} must be '- **{field}:** …'")
        else:
            fields[field] = m[1].strip()
    if not "".join(lines[len(DRAFT_FIELDS) :]).strip():
        errors.append(f"{where}: no pull request text after the header")
    status = STATUS.fullmatch(fields.get("Status", "drafted"))
    if status is None:
        errors.append(
            f"{where}: status {fields['Status']!r} is not drafted, sent, merged or released"
        )
    elif status[1] is not None:
        pinned = top.rsplit("-", 1)[-1]
        have, fixed = _version(pinned), _version(status[1])
        if have is None or fixed is None or len(have) != len(fixed):
            errors.append(
                f"{where}: write the released version as the pinned file name does ({pinned})"
            )
        elif have >= fixed:
            errors.append(f"{where}: released in {status[1]}, which {top} has: delete the patch")
    if "Files" in fields:
        listed = {f.strip() for f in fields["Files"].split(",") if f.strip()}
        if listed != touched:
            errors.append(
                f"{where}: Files lists {sorted(listed)}, the patch touches {sorted(touched)}"
            )
    return errors


def patch_errors(root: Path, tops: Iterable[str]) -> list[str]:
    """Every rule of spec 020, Decisions 6 and 7, on `recipes/patches/` and its drafts. `tops` are
    the pinned source tarballs' top folders."""
    tops = set(tops)
    patches, drafts = root / "recipes" / "patches", root / "context" / "upstream" / "patches"
    changelog = (root / "CHANGELOG.md").read_text() if (root / "CHANGELOG.md").is_file() else ""
    errors, count, made = [], 0, set()
    folders = sorted(p for p in patches.iterdir()) if patches.is_dir() else []
    for d in folders:
        if d.name in paths_os_litter():
            continue  # Finder's or Explorer's, not ours (spec 018)
        if not d.is_dir():
            if d.name != "README.md":
                errors.append(f"recipes/patches/{d.name}: only folders and README.md belong here")
            continue
        if d.name not in tops:
            errors.append(f"recipes/patches/{d.name}: no pinned source tarball has this top folder")
        numbers = set()
        for f in sorted(d.iterdir()):
            if f.name in paths_os_litter():
                continue
            where = f"recipes/patches/{d.name}/{f.name}"
            m = PATCH_NAME.fullmatch(f.name)
            if m is None:
                errors.append(f"{where}: not named NNNN-<slug>.patch, so it would never be applied")
                continue
            if m[1] in numbers:
                errors.append(f"{where}: another patch has the number {m[1]}")
            numbers.add(m[1])
            count += 1
            made.add((d.name, f.stem))
            if where not in changelog:
                errors.append(f"{where}: not named in CHANGELOG.md")
            shape, touched = patch_shape_errors(f.read_text(errors="replace"), where)
            errors += shape
            draft = drafts / d.name / f"{f.stem}.md"
            if not draft.is_file():
                errors.append(f"{where}: no pull request draft at {rel(draft, root)}")
            else:
                errors += _draft_errors(draft, d.name, touched, rel(draft, root))
    if drafts.is_dir():
        for draft in sorted(p for p in drafts.rglob("*.md") if p.name not in paths_os_litter()):
            if (draft.parent.name, draft.stem) not in made:
                errors.append(f"{rel(draft, root)}: a draft with no patch")
    readme = (root / "README.md").read_text() if (root / "README.md").is_file() else ""
    m = CARRIED_ROW.search(readme)
    if m is None or int(m[1]) != count:
        errors.append(f"README.md: must say 'upstream patches carried: {count}'")
    return errors


def paths_os_litter() -> set[str]:
    from harness import paths

    return set(paths.OS_LITTER)


# ---------------------------------------------------------------------------------------------
# The landing lane (spec 029)

PROGRESS_FILES = ("context/progress/accepted.json", "context/progress/history.jsonl")
HISTORY_FILE = PROGRESS_FILES[1]
# Rule 1 requires `dirty: false` of an acceptance whose judge holds this file: 029's own and every
# later one. Older lines are not re-judged (they all say true: Decision 2).
FIRST_CLEAN_JUDGE = "tests/unit/test_landing_lane.py"


def _committed_json(repo: Path, rev: str, path: str) -> object:
    text = paths.git("show", f"{rev}:{path}", repo=repo)
    try:
        return json.loads(text) if text else None
    except json.JSONDecodeError:
        return None


def acceptance_errors(repo: Path) -> list[str]:
    """Rule 1 (spec 029, Decisions 1 and 2), read from committed history only: the newest commit
    that changed history.jsonl sits on (first parent) the commit its newest line names, changes
    nothing but the two progress files, and, from 029's judge on, says `dirty: false`."""
    found = paths.git("rev-list", "-1", "HEAD", "--", HISTORY_FILE, repo=repo)
    if found is None:
        return [f"git rev-list -1 HEAD -- {HISTORY_FILE} failed"]
    c = found.strip()
    if not c:
        return []  # nothing accepted yet
    text = paths.git("show", f"{c}:{HISTORY_FILE}", repo=repo) or ""
    lines = [x for x in text.splitlines() if x.strip()]
    try:
        line = json.loads(lines[-1]) if lines else None
    except json.JSONDecodeError:
        line = None
    if not isinstance(line, dict):
        return [f"the newest acceptance {c[:12]}: its newest history line is not a JSON object"]
    n, named = line.get("n"), str(line.get("commit"))
    errors = []
    parent = (paths.git("rev-parse", "--verify", "-q", f"{c}^1", repo=repo) or "").strip()
    if not parent:
        errors.append(
            f"the newest acceptance {c[:12]} has no parent; its line {n} judged {named[:12]}"
        )
        changed = (
            paths.git(
                "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "-z", c, repo=repo
            )
            or ""
        )
    else:
        if named != parent:
            errors.append(
                f"the newest acceptance {c[:12]} sits on {parent[:12]}, but its history line {n} "
                f"judged {named[:12]} (carried across a rebase or an amend)"
            )
        changed = (
            paths.git(
                "diff-tree", "--no-commit-id", "--name-only", "-r", "-z", parent, c, repo=repo
            )
            or ""
        )
    extra = sorted(set(changed.split("\0")) - set(PROGRESS_FILES) - {""})
    if extra:
        more = f" and {len(extra) - 3} more" if len(extra) > 3 else ""
        errors.append(
            f"the newest acceptance {c[:12]} also changes {', '.join(extra[:3])}{more}; an "
            "acceptance commit carries only accepted.json and history.jsonl"
        )
    accepted = _committed_json(repo, c, PROGRESS_FILES[0])
    judge = accepted.get("judge") if isinstance(accepted, dict) else None
    files = judge.get("files", {}) if isinstance(judge, dict) else {}
    if FIRST_CLEAN_JUDGE in files and line.get("dirty") is not False:
        errors.append(
            f"the newest acceptance's history line {n} says dirty: {line.get('dirty')}; "
            "an acceptance is made on a clean tree"
        )
    return errors


def merge_commit_errors(repo: Path) -> list[str]:
    """Rule 3 (spec 029, Decision 3): no merge commit is reachable from HEAD."""
    out = paths.git("rev-list", "--merges", "HEAD", repo=repo)
    if out is None:
        return ["git rev-list --merges HEAD failed"]
    return [f"{h[:12]} is a merge commit; main moves only by fast-forward" for h in out.split()]
