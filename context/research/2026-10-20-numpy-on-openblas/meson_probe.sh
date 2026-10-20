#!/bin/sh
# numpy's vendored meson's OpenBLAS link probe (blas_lapack.py check_symbols), against the set's OpenBLAS.
set -u
: "${WORK:?a scratch folder}" "${REPO:?the main checkout}"
S="$WORK/probe"
SDK=$REPO/build/tools/wasi-sdk-34.0-arm64-macos
OB=$REPO/build/openblas-wasi
cd "$S"
cat > t.c <<'EOF'
void dgemm_();
void cblas_dgemm();
void zungqr_();
int main(int argc, const char *argv[])
{
  dgemm_();
  cblas_dgemm();
  zungqr_();
  return 0;
}
EOF
"$SDK/bin/clang" --target=wasm32-wasip1 t.c -o t.wasm -L"$OB/lib" -lopenblas > link.log 2>&1
echo "plain link exit $?"
head -c 1200 link.log; echo
"$SDK/bin/clang" --target=wasm32-wasip1 t.c -o t2.wasm -L"$OB/lib" -lopenblas -lwasi-emulated-mman > link2.log 2>&1
echo "with mman exit $?"
head -c 1200 link2.log; echo
echo "== symbols"
"$SDK/bin/llvm-nm" "$OB/lib/libopenblas.a" 2>/dev/null | grep -E " [TW] (dgesv_|dgesv64_|cblas_dgemm|xerbla_|dgemm_|sdot_|scopy_|dlamch_|lsame_|dgetrf_|dgesdd_|cdotc_|zdotc_|openblas_set_num_threads)$" | sort | uniq -c
