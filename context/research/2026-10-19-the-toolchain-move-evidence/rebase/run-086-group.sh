#!/bin/sh
# Inside a research container (spec 086, the Linux cpython-b trace): clone the branch (/src), unpack
# the pinned CPython tarball (verified against SHA256SUMS), then run one upstream group's check on
# each artifact set under /sets/<name>, keeping each record. usage: run-086-group.sh GROUP NAME...
set -eu
G=$1; shift
R=/work/wasi_python
rm -rf "$R"
git clone -q /src "$R"
cd "$R"
cp /pins/Python-3.15.0.tar.xz downloads/
(cd downloads && grep '  Python-3.15.0.tar.xz$' SHA256SUMS | sha256sum -c -) > /out/verify.txt
mkdir -p build
tar -xf downloads/Python-3.15.0.tar.xz -C build
{ echo "uname: $(uname -srm)"; echo "commit: $(git rev-parse HEAD)"; } > /out/host.txt
for s in "$@"; do
  WASI_PYTHON_ARTIFACTS=/sets/$s uv run pytest -p no:cacheprovider -q \
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[$G]" \
    --progress-latest /out/$G-$s.json > /out/$G-$s.log 2>&1 || true
  echo "$s: $(tail -1 /out/$G-$s.log)" >> /out/summary.txt
done
echo done > /out/finished
