export R=/Users/claygendron/Git/Repos/wasi_python SDK=/Users/claygendron/Git/Repos/wasi_python/build/tools/wasi-sdk-33.0-arm64-macos WT=/Users/claygendron/Git/Repos/wasi_python/build/tools/wasmtime-v49.0.3-aarch64-macos/wasmtime S=/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/mpl-research
export WASI_SDK_PATH=/Users/claygendron/Git/Repos/wasi_python/build/tools/wasi-sdk-33.0-arm64-macos PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Users/claygendron/Git/Repos/wasi_python/build/tools/pylib PATH=/Users/claygendron/Git/Repos/wasi_python/build/tools/pylib/bin:$PATH
HP=/Users/claygendron/Git/Repos/wasi_python/build/tools/python/bin/python3
meson() { $HP -m mesonbuild.mesonmain "$@"; }
