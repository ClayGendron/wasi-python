"""Experiment edits: move a scratch clone from 3.14.8 + wasi-sdk 24 to 3.15.0 + wasi-sdk 33."""

import re
import sys
from pathlib import Path

R = Path(sys.argv[1])


def sub(rel: str, *pairs: tuple[str, str], regex: bool = False) -> None:
    p = R / rel
    s = p.read_text()
    for old, new in pairs:
        if regex:
            s2 = re.sub(old, new, s)
        else:
            s2 = s.replace(old, new)
        if s2 == s:
            raise SystemExit(f"{rel}: no match for {old!r}")
        s = s2
    p.write_text(s)


SDK24, SDK33 = "wasi-sdk-24.0-arm64-macos", "wasi-sdk-33.0-arm64-macos"
EH = "'-fwasm-exceptions', '-mllvm', '-wasm-use-legacy-eh=false', "

sub(
    "scripts/00_download.sh",
    ("get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-24/wasi-sdk-24.0-arm64-macos.tar.gz wasi-sdk-24.0-arm64-macos.tar.gz",
     "get https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sdk-33.0-arm64-macos.tar.gz wasi-sdk-33.0-arm64-macos.tar.gz"),
    ("research https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sdk-33.0-arm64-macos.tar.gz wasi-sdk-33.0-arm64-macos.tar.gz\n", ""),
    ("cpython-3.14.8%2B20261009", "cpython-3.15.0%2B20261009"),
    ("cpython-3.14.8+20261009", "cpython-3.15.0+20261009"),
    ("https://www.python.org/ftp/python/3.14.8/Python-3.14.8.tar.xz Python-3.14.8.tar.xz",
     "https://www.python.org/ftp/python/3.15.0/Python-3.15.0.tar.xz Python-3.15.0.tar.xz"),
)
sub(
    "scripts/00_download.sh",
    (r"get https://files\.pythonhosted\.org/\S+/cython-3\.3\.0-cp314-cp314-macosx_11_0_arm64\.whl",
     "get https://files.pythonhosted.org/packages/ea/45/7f6988070013e16918e39b1b3dab9c5f2c8e404253a7fd10ee685bbd6902/cython-3.3.0-cp315-cp315-macosx_11_0_arm64.whl"),
    regex=True,
)
sub("scripts/steps/common.sh", (SDK24, SDK33), ("Python-3.14.8", "Python-3.15.0"))
sub(
    "scripts/steps/10_tools.sh",
    ("wasi-sdk-24.0-arm64-macos.tar.gz", "wasi-sdk-33.0-arm64-macos.tar.gz"),
    ("cpython-3.14.8+20261009", "cpython-3.15.0+20261009"),
    ("cython-3.3.0-cp314-cp314", "cython-3.3.0-cp315-cp315"),
)
sub(
    "scripts/steps/20_cpython.sh",
    ("Python-3.14.8.tar.xz", "Python-3.15.0.tar.xz"),
    ("Tools/wasm/wasi build", "Platforms/WASI build"),
)
sub("scripts/python-wasi-cross", ("Python-3.14.8", "Python-3.15.0"), ("lib.wasi-wasm32-3.14", "lib.wasi-wasm32-3.15"))
sub("scripts/gen_inittab.py", ("cpython-314-wasm32-wasi", "cpython-315-wasm32-wasi"))
sub(
    "scripts/steps/60_link.sh",
    ("cpython-314-wasm32-wasi", "cpython-315-wasm32-wasi"),
    ('cp "$HERE/recipes/hostmodule.c" "$HERE/recipes/cxa_stubs.c"', 'cp "$HERE/recipes/hostmodule.c"'),
    ("_host hostmodule.c cxa_stubs.c inittab.c", "_host hostmodule.c inittab.c"),
    ("-lc++ -lc++abi -lc-printscan-long-double", "-lc++ -lc++abi -lunwind -lc-printscan-long-double"),
    ('make -j8 all >', 'make -j8 all LDFLAGS_NODIST="-fwasm-exceptions" >'),
    ('make -n python.wasm >', 'make -n python.wasm LDFLAGS_NODIST="-fwasm-exceptions" >'),
)
sub("scripts/steps/70_zip.sh", ("lib.wasi-wasm32-3.14", "lib.wasi-wasm32-3.15"))
sub(
    "scripts/steps/80_snapshot.sh",
    ("python314.zip", "python315.zip"),
    ('WIZER="$T/wizer-v11.0.3-aarch64-macos/wizer"', 'WIZER="$T/wasmtime-v49.0.3-aarch64-macos/wasmtime wizer"'),
    ('FLAGS="--allow-wasi --wasm-bulk-memory true --init-func wizer.initialize"',
     'FLAGS="-W exceptions=y,unknown-imports-trap=y -S cli=y,inherit-stdin=n,inherit-stdout=n,inherit-stderr=n --init-func wizer.initialize"'),
    ('"$WIZER" $FLAGS --mapdir "/::$ROOT"', '$WIZER $FLAGS --dir "$ROOT::/"'),
)
sub("scripts/make_stdlib_zip.py", ("TARGET = (3, 14)", "TARGET = (3, 15)"))
sub("scripts/freeze_bootstrap.py", ("TARGET = (3, 14)", "TARGET = (3, 15)"))
sub(
    "scripts/assemble_artifacts.py",
    ('PYTHON = "3.14.8"', 'PYTHON = "3.15.0"'),
    ('RESEARCH_PINS = {"wasi-sdk-33.0-arm64-macos.tar.gz", "python-3.14.7-wasi_sdk-24.zip"}',
     'RESEARCH_PINS = {"python-3.14.7-wasi_sdk-24.zip", "Python-3.14.8.tar.xz", "cpython-3.14.8+20261009-aarch64-apple-darwin-install_only.tar.gz", "cython-3.3.0-cp314-cp314-macosx_11_0_arm64.whl", "wasi-sdk-24.0-arm64-macos.tar.gz"}'),
)
for cross in ("recipes/wasi-numpy.cross", "recipes/wasi-pandas.cross"):
    sub(cross, (SDK24, SDK33), ("cpp_args = [", "cpp_args = [" + EH))
print("edits applied")
sub("scripts/steps/10_tools.sh", ("sys.version_info[:3] == (3, 14, 8)", "sys.version_info[:3] == (3, 15, 0)"))
