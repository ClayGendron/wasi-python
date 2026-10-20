#!/bin/sh
# The wasm signature of each OpenBLAS routine numpy's linalg declares, read from wasm-ld's
# mismatch warnings against a caller that declares every one as void(void).
set -u
: "${WORK:?a scratch folder}" "${REPO:?the main checkout}"
S="$WORK/probe"
SDK=$REPO/build/tools/wasi-sdk-34.0-arm64-macos
OB=$REPO/build/openblas-wasi
cd "$S"
NAMES="ccopy cdotc cdotu cgeev cgelsd cgemm cgesdd cgesv cgetrf cheevd cpotrf cpotri cpotrs dcopy ddot dgeev dgelsd dgemm dgeqrf dgesdd dgesv dgetrf dorgqr dpotrf dpotri dpotrs dsyevd scopy sdot sgeev sgelsd sgemm sgesdd sgesv sgetrf spotrf spotri spotrs ssyevd xerbla zcopy zdotc zdotu zgeev zgelsd zgemm zgeqrf zgesdd zgesv zgetrf zheevd zpotrf zpotri zpotrs zungqr"
{
  for n in $NAMES; do echo "void ${n}_(void);"; done
  echo "void probe(void) {"
  for n in $NAMES; do echo "  ${n}_();"; done
  echo "}"
} > sigs.c
"$SDK/bin/clang" --target=wasm32-wasip1 -O1 -c sigs.c -o sigs.o
"$SDK/bin/wasm-ld" --no-entry --allow-undefined --export=probe sigs.o "$OB/lib/libopenblas.a" -o sigs.wasm > sigs.log 2>&1
echo "link exit $?"
grep -A2 "signature mismatch" sigs.log | grep "libopenblas" | sed 's/.*defined as \(.*\) in .*(\(.*\))/\2 \1/' | sort
echo "== names with no definition in libopenblas.a"
for n in $NAMES; do "$SDK/bin/llvm-nm" "$OB/lib/libopenblas.a" 2>/dev/null | grep -q " T ${n}_$" || echo "${n}_"; done
