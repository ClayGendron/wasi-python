#!/bin/sh
# Inside a research container (spec 086, criterion 5; the build review's B1): spec 065's trap-entry
# checks on this host's Cranelift code. The artifact set is the one every host builds byte for byte
# (SHA256SUMS aac927dc..., criterion 3), copied in from /set; the CPython tree the regrtest stage
# reads is unpacked from its pinned tarball, verified against SHA256SUMS first. Outputs to /out.
set -eu
R=/work/wasi_python
rm -rf "$R"
git clone -q /src "$R"
cd "$R"
cp /pins/Python-3.15.0.tar.xz downloads/
(cd downloads && grep '  Python-3.15.0.tar.xz$' SHA256SUMS | sha256sum -c -) > /out/traps-verify.txt
mkdir -p build
tar -xf downloads/Python-3.15.0.tar.xz -C build
cp -R /set build/artifacts
(cd build/artifacts && sha256sum SHA256SUMS) > /out/traps-set.txt
{ echo "uname: $(uname -srm)"; echo "commit: $(git rev-parse HEAD)"; } > /out/traps-host.txt
uv run pytest -p no:cacheprovider -n 3 -q -rA tests/checks/test_v1_3_upstream_suites.py \
  -k test_upstream_trap > /out/traps.txt 2>&1 || true
cp build/progress/latest.json /out/traps-latest.json 2>/dev/null || true
echo done > /out/traps-finished
