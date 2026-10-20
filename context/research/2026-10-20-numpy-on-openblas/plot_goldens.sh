#!/bin/sh
# Review L4: the two pixel-hash goldens natively, on the oracle's own venv (numpy on Accelerate) and on
# a copy of it whose numpy is the macosx_11_0_arm64 OpenBLAS wheel; each stdout compared with the job's
# .expected (their out directories stay empty). The environment is the oracle's (tests/harness/jobs.py,
# oracle_env): matplotlib's own fonts, a fresh MPLCONFIGDIR, one BLAS thread, PYTHONHASHSEED=0.
set -eu
: "${WORK:?a scratch folder}" "${REPO:?the main checkout}" "${WT:?this checkout}"
ORACLE="$REPO/build/oracle/venv"
SP=lib/python3.15/site-packages
if [ ! -d "$WORK/venv-plot" ]; then
  UV_CACHE_DIR="$WORK/uvcache" uv venv -q --python "$ORACLE/bin/python" "$WORK/venv-plot"
  for f in "$ORACLE/$SP"/*; do
    case "$(basename "$f")" in numpy|numpy-*|numpy.libs|_virtualenv*) continue;; esac
    cp -c -R "$f" "$WORK/venv-plot/$SP/"
  done
  UV_CACHE_DIR="$WORK/uvcache" uv pip install -q --python "$WORK/venv-plot/bin/python" --no-index --no-deps \
    "$WORK/dl/numpy-2.5.2-cp315-cp315-macosx_11_0_arm64.whl"
fi
for venv in "$ORACLE" "$WORK/venv-plot"; do
  "$venv/bin/python" -I -c "import numpy; print('numpy BLAS:', numpy.show_config(mode='dicts')['Build Dependencies']['blas']['name'])"
  for job in plot_line plot_contour; do
    rm -rf "$WORK/plotrun"; mkdir -p "$WORK/plotrun/out" "$WORK/plotrun/mpl"
    MPL_IGNORE_SYSTEM_FONTS=1 MPLCONFIGDIR="$WORK/plotrun/mpl" OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
      PYTHONHASHSEED=0 "$venv/bin/python" "$WT/tests/jobs/$job.py" "$WT/tests/jobs" "$WORK/plotrun/out" \
      > "$WORK/plotrun/stdout.txt"
    if cmp -s "$WORK/plotrun/stdout.txt" "$WT/tests/jobs/$job.expected"; then r="equal to .expected"; else r="DIFFERS from .expected"; fi
    echo "$job: $r ($(ls "$WORK/plotrun/out" | wc -l | tr -d ' ') files in out)"
    [ "$r" = "equal to .expected" ] || diff "$WT/tests/jobs/$job.expected" "$WORK/plotrun/stdout.txt" | head -6
  done
done
