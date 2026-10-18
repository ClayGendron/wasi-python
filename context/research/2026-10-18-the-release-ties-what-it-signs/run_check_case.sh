#!/bin/bash
# case-name, then mutate, then run check.sh in a fresh dir; print exit
S=$1; name=$2; mut=$3; pathmode=$4
d=$(mktemp -d "$S/case.XXXX"); cd "$d"; mkdir release-assets
printf 'wheel bytes' > release-assets/wasi_python-0.1.0a5-py3-none-any.whl
printf 'tar bytes' > release-assets/wasi-python-0.1.0a5-wasm32-wasip1.tar.xz
(cd release-assets && shasum -a 256 wasi* > SHA256SUMS)
SUMS_SHA256=$(shasum -a 256 release-assets/SHA256SUMS | cut -c1-64)
eval "$mut"
export SUMS_SHA256
if [ "$pathmode" = noshasum256 ]; then P=/usr/bin:/bin; else P=$PATH; fi
PATH=$P bash -e "$S/check.sh" > out.txt 2>&1; echo "$name ($pathmode): exit $? | $(tail -1 out.txt)"
