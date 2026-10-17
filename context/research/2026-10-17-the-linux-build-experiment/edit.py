"""Experiment edits: make a scratch clone's recipe host-aware (arm64 macOS, aarch64 Linux,
x86_64 Linux) with the smallest change. Nothing in the real repo changes.

    python3 -I edit.py <scratch clone>

The host-specific names of scripts/line.conf (the toolchain, the host Python, the two native
build-tool wheels) get one line per host, prefixed by a host key; scripts/line.sh and
scripts/line.py resolve the plain name for the host they run on, so every reader of the plain
name (the steps, the cross files' @SDK@, the judge's oracle) is unchanged. scripts/00_download.sh
fetches only the running host's toolchain pins; downloads/SHA256SUMS lists every host's.
"""

import sys
from pathlib import Path

R = Path(sys.argv[1])


def sub(rel: str, *pairs: tuple[str, str]) -> None:
    p = R / rel
    s = p.read_text()
    for old, new in pairs:
        if s.count(old) != 1:
            raise SystemExit(f"{rel}: {s.count(old)} matches for {old!r}, not 1")
        s = s.replace(old, new)
    p.write_text(s)


# 1. line.conf: one line per host for each host-specific name (NINJA_WHEEL is new: step 10 named
#    the macOS ninja wheel literally).
sub(
    "scripts/line.conf",
    (
        "WASI_SDK_DIR=wasi-sdk-33.0-arm64-macos\n"
        "HOST_PYTHON_ARCHIVE=cpython-3.15.0+20261009-aarch64-apple-darwin-install_only.tar.gz\n"
        "CYTHON_WHEEL=cython-3.3.0-cp315-cp315-macosx_11_0_arm64.whl\n"
        "WASMTIME_DIR=wasmtime-v49.0.3-aarch64-macos\n",
        "# Host-specific names: one line per host, prefixed by its key (MACOS_ARM64, LINUX_AARCH64,\n"
        "# LINUX_X86_64); line.sh and line.py set the plain name for the host they run on.\n"
        "MACOS_ARM64_WASI_SDK_DIR=wasi-sdk-33.0-arm64-macos\n"
        "MACOS_ARM64_HOST_PYTHON_ARCHIVE=cpython-3.15.0+20261009-aarch64-apple-darwin-install_only.tar.gz\n"
        "MACOS_ARM64_CYTHON_WHEEL=cython-3.3.0-cp315-cp315-macosx_11_0_arm64.whl\n"
        "MACOS_ARM64_NINJA_WHEEL=ninja-1.13.2-py3-none-macosx_10_9_universal2.whl\n"
        "MACOS_ARM64_WASMTIME_DIR=wasmtime-v49.0.3-aarch64-macos\n"
        "LINUX_AARCH64_WASI_SDK_DIR=wasi-sdk-33.0-arm64-linux\n"
        "LINUX_AARCH64_HOST_PYTHON_ARCHIVE=cpython-3.15.0+20261009-aarch64-unknown-linux-gnu-install_only.tar.gz\n"
        "LINUX_AARCH64_CYTHON_WHEEL=cython-3.3.0-cp315-cp315-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl\n"
        "LINUX_AARCH64_NINJA_WHEEL=ninja-1.13.2-py3-none-manylinux2014_aarch64.manylinux_2_17_aarch64.whl\n"
        "LINUX_AARCH64_WASMTIME_DIR=wasmtime-v49.0.3-aarch64-linux\n"
        "LINUX_X86_64_WASI_SDK_DIR=wasi-sdk-33.0-x86_64-linux\n"
        "LINUX_X86_64_HOST_PYTHON_ARCHIVE=cpython-3.15.0+20261009-x86_64-unknown-linux-gnu-install_only.tar.gz\n"
        "LINUX_X86_64_CYTHON_WHEEL=cython-3.3.0-cp315-cp315-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl\n"
        "LINUX_X86_64_NINJA_WHEEL=ninja-1.13.2-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl\n"
        "LINUX_X86_64_WASMTIME_DIR=wasmtime-v49.0.3-x86_64-linux\n",
    ),
)

# 2. line.sh: the host key from uname, and the plain names resolved for it.
sub(
    "scripts/line.sh",
    (
        '. "$LINE_CONF"\n',
        '. "$LINE_CONF"\n'
        'case "$(uname -s)-$(uname -m)" in\n'
        "  Darwin-arm64) HOST_KEY=MACOS_ARM64;;\n"
        "  Linux-aarch64|Linux-arm64) HOST_KEY=LINUX_AARCH64;;\n"
        "  Linux-x86_64) HOST_KEY=LINUX_X86_64;;\n"
        '  *) echo "ERROR: no line for host $(uname -s)-$(uname -m)" >&2; exit 1;;\n'
        "esac\n"
        "for name in WASI_SDK_DIR WASMTIME_DIR HOST_PYTHON_ARCHIVE CYTHON_WHEEL NINJA_WHEEL; do\n"
        '  eval "value=\\${${HOST_KEY}_$name:-}"\n'
        '  [ -n "$value" ] || { echo "ERROR: scripts/line.conf has no ${HOST_KEY}_$name" >&2; exit 1; }\n'
        '  eval "$name=\\$value"\n'
        "done\n",
    ),
)

# 3. line.py: the same resolution, so the judge's oracle (HOST_PYTHON_ARCHIVE) follows the host.
sub(
    "scripts/line.py",
    ("import re\n", "import platform\nimport re\n"),
    (
        '    major, minor, _ = values["PYTHON_VERSION"].split(".")\n',
        "    key = HOSTS.get((platform.system(), platform.machine()))\n"
        "    if key is None:\n"
        '        raise SystemExit(f"no line for host {platform.system()}-{platform.machine()}")\n'
        "    for name in HOST_NAMES:\n"
        '        if f"{key}_{name}" not in values:\n'
        '            raise SystemExit(f"{path.name} has no {key}_{name}")\n'
        '        values[name] = values[f"{key}_{name}"]\n'
        '    major, minor, _ = values["PYTHON_VERSION"].split(".")\n',
    ),
    (
        'LINE = re.compile(r"([A-Z][A-Z0-9_]*)=([A-Za-z0-9._+-]+)")\n',
        'LINE = re.compile(r"([A-Z][A-Z0-9_]*)=([A-Za-z0-9._+-]+)")\n'
        "HOSTS = {\n"
        '    ("Darwin", "arm64"): "MACOS_ARM64",\n'
        '    ("Linux", "aarch64"): "LINUX_AARCH64",\n'
        '    ("Linux", "arm64"): "LINUX_AARCH64",\n'
        '    ("Linux", "x86_64"): "LINUX_X86_64",\n'
        "}\n"
        'HOST_NAMES = ("WASI_SDK_DIR", "WASMTIME_DIR", "HOST_PYTHON_ARCHIVE", "CYTHON_WHEEL", "NINJA_WHEEL")\n',
    ),
)

# 4. 00_download.sh: the toolchain, host Python and native wheels per host; the rest unchanged.
MAC_TOOLS = (
    "get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sdk-33.0-arm64-macos.tar.gz wasi-sdk-33.0-arm64-macos.tar.gz\n"
    "get https://github.com/bytecodealliance/wasmtime/releases/download/v49.0.3/wasmtime-v49.0.3-aarch64-macos.tar.xz wasmtime-v49.0.3-aarch64-macos.tar.xz\n"
    "get https://github.com/astral-sh/python-build-standalone/releases/download/20261009/cpython-3.15.0%2B20261009-aarch64-apple-darwin-install_only.tar.gz cpython-3.15.0+20261009-aarch64-apple-darwin-install_only.tar.gz\n"
)
MAC_CYTHON = "get https://files.pythonhosted.org/packages/ea/45/7f6988070013e16918e39b1b3dab9c5f2c8e404253a7fd10ee685bbd6902/cython-3.3.0-cp315-cp315-macosx_11_0_arm64.whl cython-3.3.0-cp315-cp315-macosx_11_0_arm64.whl\n"
MAC_NINJA = "get https://files.pythonhosted.org/packages/b5/b8/90a9518f2264637084d6199bc20c2f3fb97fefc4c474d277720150c3bd6d/ninja-1.13.2-py3-none-macosx_10_9_universal2.whl ninja-1.13.2-py3-none-macosx_10_9_universal2.whl\n"


def gets(pins: list[tuple[str, str]]) -> str:
    return "".join(f"    get {url} {name}\n" for url, name in pins)


LINUX_AARCH64 = [
    ("https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sdk-33.0-arm64-linux.tar.gz", "wasi-sdk-33.0-arm64-linux.tar.gz"),
    ("https://github.com/bytecodealliance/wasmtime/releases/download/v49.0.3/wasmtime-v49.0.3-aarch64-linux.tar.xz", "wasmtime-v49.0.3-aarch64-linux.tar.xz"),
    ("https://github.com/astral-sh/python-build-standalone/releases/download/20261009/cpython-3.15.0%2B20261009-aarch64-unknown-linux-gnu-install_only.tar.gz", "cpython-3.15.0+20261009-aarch64-unknown-linux-gnu-install_only.tar.gz"),
    ("https://files.pythonhosted.org/packages/6e/5d/afb6866ab10236bb208dff0f172ea4b397c9693c5250280c4d9d26057218/cython-3.3.0-cp315-cp315-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl", "cython-3.3.0-cp315-cp315-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl"),
    ("https://files.pythonhosted.org/packages/35/54/7368ce188625e39acc03ee362bb86cc9bfa6ad15e25c50889ae36e2889b3/ninja-1.13.2-py3-none-manylinux2014_aarch64.manylinux_2_17_aarch64.whl", "ninja-1.13.2-py3-none-manylinux2014_aarch64.manylinux_2_17_aarch64.whl"),
]
LINUX_X86_64 = [
    ("https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sdk-33.0-x86_64-linux.tar.gz", "wasi-sdk-33.0-x86_64-linux.tar.gz"),
    ("https://github.com/bytecodealliance/wasmtime/releases/download/v49.0.3/wasmtime-v49.0.3-x86_64-linux.tar.xz", "wasmtime-v49.0.3-x86_64-linux.tar.xz"),
    ("https://github.com/astral-sh/python-build-standalone/releases/download/20261009/cpython-3.15.0%2B20261009-x86_64-unknown-linux-gnu-install_only.tar.gz", "cpython-3.15.0+20261009-x86_64-unknown-linux-gnu-install_only.tar.gz"),
    ("https://files.pythonhosted.org/packages/c9/aa/4c0b6773ecf6bc1ec6cda7db8312a566611b330fb6dae87d740e44a47822/cython-3.3.0-cp315-cp315-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl", "cython-3.3.0-cp315-cp315-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl"),
    ("https://files.pythonhosted.org/packages/6e/53/ebfed7b689c338dd8ebeec9c0730c8d56821292f14e2536e5f3ef1a05744/ninja-1.13.2-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl", "ninja-1.13.2-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl"),
]

sub(
    "scripts/00_download.sh",
    (MAC_CYTHON, ""),
    (MAC_NINJA, ""),
    (
        "# Toolchain and host tools (macOS arm64). The line's versions are named in scripts/line.conf; the\n"
        "# URLs here stay literal, one pin per line (spec 003, Decision 1).\n" + MAC_TOOLS,
        "# Toolchain, host Python and the native build-tool wheels: the running host's only (its key from\n"
        "# scripts/line.sh). The line's versions are named in scripts/line.conf; the URLs here stay\n"
        "# literal, one pin per line (spec 003, Decision 1).\n"
        '. "$HERE/scripts/line.sh"\n'
        'case "$HOST_KEY" in\n'
        "  MACOS_ARM64)\n"
        + "".join("    " + g for g in (MAC_TOOLS + MAC_CYTHON + MAC_NINJA).splitlines(keepends=True))
        + "    ;;\n"
        "  LINUX_AARCH64)\n" + gets(LINUX_AARCH64) + "    ;;\n"
        "  LINUX_X86_64)\n" + gets(LINUX_X86_64) + "    ;;\n"
        "esac\n",
    ),
)

# 5. 10_tools.sh: the ninja wheel by its line name.
sub(
    "scripts/steps/10_tools.sh",
    ("ninja-1.13.2-py3-none-macosx_10_9_universal2.whl versioneer", "$NINJA_WHEEL versioneer"),
)
print("edits applied")

# 6. build.sh: one collation for every step. Step 60 orders the extension archives with `find | sort`
#    and `sort -u`; under macOS's en_US.UTF-8 `ops_dispatch` sorts before `ops`, under C/POSIX after,
#    so the link order (and the reactor's bytes) followed the builder's locale (finding of run 1).
sub(
    "scripts/build.sh",
    ("export PYTHONHASHSEED=0\n", "export PYTHONHASHSEED=0\nexport LC_ALL=C  # one collation: step 60's `sort` orders the link\n"),
)
print("edit 6 applied")

# 7. reactor_main.c: while initializing, a directory's size and link count are pinned too. The
#    host's file system answers them (APFS: size 96, nlink 3; ext4/overlayfs: 4096 and 2) and
#    CPython keeps a small int (<= 256) shared but allocates a larger one, so the heap, and the
#    snapshot, followed the builder's file system (finding of the WASI trace, run 4).
sub(
    "recipes/reactor_main.c",
    (
        "    st->dev = 0;\n    st->ino = 0;\n",
        "    st->dev = 0;\n    st->ino = 0;\n"
        "    if (st->filetype == __WASI_FILETYPE_DIRECTORY) {\n"
        "        st->size = 0;  /* the host's file system answers it: APFS 96, ext4 4096 */\n"
        "        st->nlink = 1;\n"
        "    }\n",
    ),
)
print("edit 7 applied")

# 8. One wasm runtime for every host: wasi-sdk's host-neutral sysroot and compiler-rt builtins
#    (published beside the per-host tarballs), laid over the host SDK's own copies in step 10.
#    The per-host tarballs' libc++, libc++abi and builtins differ (each was built at its own path,
#    which assert messages keep: 64 bytes of the reactor's DATA); libc.a and the headers do not.
NEUTRAL = (
    "get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sysroot-33.0%2Bm.tar.gz wasi-sysroot-33.0+m.tar.gz\n"
    "get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/libclang_rt-33.0%2Bm.tar.gz libclang_rt-33.0+m.tar.gz\n"
)
sub(
    "scripts/00_download.sh",
    ("esac\n\n# Sources\n", "esac\n# The wasm runtime (sysroot and compiler-rt builtins), the same bytes for every host\n" + NEUTRAL + "\n# Sources\n"),
)
sub(
    "scripts/steps/10_tools.sh",
    (
        '[ -x "$HOSTPY" ] || die "the host Python did not unpack to $HOSTPY"\n',
        '[ -x "$HOSTPY" ] || die "the host Python did not unpack to $HOSTPY"\n'
        "# The wasm runtime every host links: the host-neutral sysroot and builtins over the SDK's own.\n"
        'SYSROOT_TGZ=$(pinned "wasi-sysroot-$WASI_SDK_VERSION.0+m.tar.gz")\n'
        'RT_TGZ=$(pinned "libclang_rt-$WASI_SDK_VERSION.0+m.tar.gz")\n'
        'rm -rf "$SDK/share/wasi-sysroot" "$B/rt"\n'
        'mkdir -p "$SDK/share/wasi-sysroot" "$B/rt"\n'
        'tar -xzf "$SYSROOT_TGZ" -C "$SDK/share/wasi-sysroot" --strip-components=1\n'
        'tar -xzf "$RT_TGZ" -C "$B/rt" --strip-components=1\n'
        'RT_DIR=$(echo "$SDK"/lib/clang/*/lib)\n'
        '[ -d "$RT_DIR/wasm32-unknown-wasip1" ] || die "no compiler-rt directory in the SDK"\n'
        'for target in "$B"/rt/*; do cp "$target"/* "$RT_DIR/${target##*/}/"; done\n'
        'rm -rf "$B/rt"\n',
    ),
)
print("edit 8 applied")
