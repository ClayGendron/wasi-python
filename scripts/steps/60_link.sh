#!/bin/sh
# Step 60: link numpy, pandas, the plot packages (Pillow with zlib and JPEG, kiwisolver, matplotlib;
# contourpy and matplotlib's _qhull with step 37's qhull), regex, lxml with libxml2 and libxslt,
# scipy and numpy with one OpenBLAS, scikit-learn, statsmodels, zlib, bz2, lzma, sqlite3 and the
# host door into CPython as builtins through the build-directory Modules/Setup.local, then relink
# the interpreter as a WASI reactor (build/out/python.wasm) with recipes/reactor_main.c in place of
# Programs/python.o, and with three link-time refusals: recipes/iconv_refusals.c, which refuses
# GB18030 at iconv_open, recipes/fcntl_dup_refusal.c, which answers fcntl's two dup commands ENOTSUP
# as wasi-libc's dup does, and recipes/freopen_refusal.c, which refuses freopen. Last, the static
# constructors and target features are checked against the judge's reviewed lists, so a build with a
# constructor no review has read stops here, before step 80 would hang on it. Around the link, two
# checks of scripts/weak_duplicates.py: before it, no weak definition that two archives share unless
# a review allowed it (recipes/weak-duplicates-allowed.txt), which wasm-ld would resolve without a
# word; after it, the link map names scikit-learn's renamed random generators and none of the
# originals.
set -eu
. "$(dirname "$0")/common.sh"

L="$B/link"
# Step 35's archives: a tree built before that step has none, and make would fail
# with a long log.
for lib in libbz2.a liblzma.a libsqlite3.a; do
  [ -s "$B/stdlib-libs/lib/$lib" ] || die "build/stdlib-libs/lib/$lib is missing: run step 35"
done
# Step 55's extension archives, each at its import path (contourpy).
for pkg in pillow kiwisolver matplotlib contourpy; do
  [ -d "$B/plot-modules/$pkg" ] || die "build/plot-modules/$pkg is missing: run step 55"
done
# Step 36's archives and step 54's modules.
for lib in libxml2.a libxslt.a libexslt.a; do
  [ -s "$B/xml-libs/lib/$lib" ] || die "build/xml-libs/lib/$lib is missing: run step 36"
done
[ -d "$B/lxml-build/lxml" ] || die "build/lxml-build/lxml is missing: run step 54"
PM="$B/plot-modules"
[ -d "$B/regex-build/regex" ] || die "build/regex-build/regex is missing: run step 53"
# Step 38's OpenBLAS and step 57's modules and shims.
[ -s "$B/openblas-wasi/lib/libopenblas.a" ] || die "build/openblas-wasi/lib/libopenblas.a is missing: run step 38"
[ -d "$B/scipy-modules/scipy" ] || die "build/scipy-modules/scipy is missing: run step 57"
[ -s "$B/scipy-shims/libscipy_lapack_shims.a" ] || die "build/scipy-shims/libscipy_lapack_shims.a is missing: run step 57"
# Step 58's modules.
[ -d "$B/sklearn-modules/sklearn" ] || die "build/sklearn-modules/sklearn is missing: run step 58"
# numpy's side of the same ABI: step 40's shims, numpy's int-declared calls to OpenBLAS.
[ -s "$B/numpy-shims/libnumpy_lapack_shims.a" ] || die "build/numpy-shims/libnumpy_lapack_shims.a is missing: run step 40"
# Step 59's modules.
[ -d "$B/statsmodels-modules/statsmodels" ] || die "build/statsmodels-modules/statsmodels is missing: run step 59"
# The generated inittab declares CPython's internal _PyImport_SwapPackageContext itself, as this
# header declares it: a CPython that changes it stops here, not at run time.
grep -q '^extern const char \* _PyImport_SwapPackageContext(const char \*newcontext);$' \
  "$CP/Include/internal/pycore_import.h" \
  || die "Include/internal/pycore_import.h no longer declares _PyImport_SwapPackageContext as gen_inittab.py does"
remove "$L" "$OUT/python.wasm"
mkdir -p "$L/archives" "$OUT"
"$HOSTPY" "$HERE/scripts/gen_inittab.py" --against "$W/Modules/config.c" "$L/inittab.c" numpy="$B/numpy-build" pandas="$B/pandas-build" \
  PIL="$PM/pillow" kiwisolver="$PM/kiwisolver" matplotlib="$PM/matplotlib" \
  contourpy="$PM/contourpy" regex="$B/regex-build" lxml="$B/lxml-build" scipy="$B/scipy-modules" \
  sklearn="$B/sklearn-modules" statsmodels="$B/statsmodels-modules"

# makesetup takes *.a tokens as libraries: each module's archive is copied under a unique name, and
# the static libraries its .deps file names are linked once each, with its -L and -l lines (qhull's
# -lqhull_r, matplotlib's -lm and -ldl). A relative path in a .deps file is its build folder's.
# Left out, as scripts/gen_inittab.py leaves them out: numpy's test modules, and matplotlib's _tkagg
# (no Tk). matplotlib's _qhull is linked, with carried patch 0002, which opens no
# /dev/null on WASI; its .deps names step 37's libqhull_r once. scipy's _qhull is linked too, with
# the same qhull. scipy has two modules named _zeros, so its archives are named by their import
# path, and so are scikit-learn's, which has three such pairs, and statsmodels', whose state-space
# filters and smoothers share three names.
archives=""
deps=""
for pair in numpy:"$B/numpy-build" pandas:"$B/pandas-build" pillow:"$PM/pillow" \
  kiwisolver:"$PM/kiwisolver" matplotlib:"$PM/matplotlib" contourpy:"$PM/contourpy" \
  regex:"$B/regex-build" lxml:"$B/lxml-build" scipy:"$B/scipy-modules" sklearn:"$B/sklearn-modules" \
  statsmodels:"$B/statsmodels-modules"; do
  pkg=${pair%%:*}
  dir=${pair#*:}
  for so in $(find "$dir" -name "*.cpython-$PYTHON_TAG-wasm32-wasi.so" | sort); do
    name=$(basename "$so" .cpython-$PYTHON_TAG-wasm32-wasi.so)
    case "$pkg:$name" in *:*_tests|numpy:_simd|matplotlib:_tkagg) continue;; esac
    case "$pkg" in
      scipy|sklearn|statsmodels) a="$L/archives/$(printf '%s' "${so#"$dir"/}" | sed "s#\.cpython-$PYTHON_TAG-wasm32-wasi\.so\$##; s#/#_#g").a";;
      *) a="$L/archives/${pkg}_$name.a";;
    esac
    [ ! -e "$a" ] || die "two modules would share the archive name $(basename "$a")"
    cp "$so" "$a"
    archives="$archives $a"
    deps="$deps $(sed "s#^\([^/-]\)#$dir/\1#" "$so.deps" | tr '\n' ' ')"
  done
done
libs=$(printf '%s\n' $deps | grep '\.a$' | sort -u | tr '\n' ' ')
libs="$libs$(printf '%s\n' $deps | grep '^-L' | sort -u | tr '\n' ' ')"
libs="$libs$(printf '%s\n' $deps | grep '^-l' | sort -u | tr '\n' ' ')"
# scipy's and numpy's sides of the LAPACK ABI (no module's .deps names them),
# and the emulated mmap OpenBLAS's buffer uses (wasi-libc's, malloc underneath; no new import).
libs="$libs$B/scipy-shims/libscipy_lapack_shims.a $B/numpy-shims/libnumpy_lapack_shims.a -lwasi-emulated-mman "

# The weak-duplicate gate: every archive this link takes but the SDK's
# runtime libraries and CPython's own (the modules', the static libraries their .deps name,
# scipy's and numpy's shims, and the four C libraries the Setup lines below link), read with the
# SDK's llvm-nm.
weak_archives="$archives $(printf '%s\n' $deps | grep '\.a$' | sort -u | tr '\n' ' ')"
weak_archives="$weak_archives $B/scipy-shims/libscipy_lapack_shims.a $B/numpy-shims/libnumpy_lapack_shims.a $B/zlib-wasi/lib/libz.a"
for lib in libbz2.a liblzma.a libsqlite3.a; do weak_archives="$weak_archives $B/stdlib-libs/lib/$lib"; done
"$HOSTPY" "$HERE/scripts/weak_duplicates.py" archives "$SDK/bin/llvm-nm" "$SDK/bin/llvm-cxxfilt" \
  "$HERE/recipes/weak-duplicates-allowed.txt" $weak_archives > "$L/weak-duplicates.log" 2>&1 \
  || { grep '^ERROR' "$L/weak-duplicates.log" | head -n 20; die "the link's archives share a weak definition no review allowed (build/link/weak-duplicates.log)"; }
tail -n 1 "$L/weak-duplicates.log"

# _sqlite3 from CPython's own sources (Modules/Setup.stdlib.in), with the one define CPython's
# configure adds when it finds sqlite3_serialize. No `=` may appear in a Setup.local module line:
# makesetup reads such a line as a Make variable and drops the module without an error.
SL="$B/stdlib-libs"
SQLITE_SRC=""
for f in blob connection cursor microprotocols module prepare_protocol row statement util; do
  SQLITE_SRC="$SQLITE_SRC _sqlite/$f.c"
done
SQLITE_SRC=${SQLITE_SRC# }

# makesetup mangles absolute source paths, so the two C files are copied into Modules/.
cp "$HERE/recipes/hostmodule.c" "$L/inittab.c" "$CP/Modules/"
{
  echo "# Generated by scripts/steps/60_link.sh: numpy, pandas, the plot packages, lxml, the"
  echo "# compression and database modules and the host door as builtins."
  echo "*static*"
  echo "_host hostmodule.c inittab.c $archives $libs -lc++ -lc++abi -lunwind -lsetjmp -lc-printscan-long-double"
  echo "zlib zlibmodule.c -I$B/zlib-wasi/include $B/zlib-wasi/lib/libz.a"
  echo "_bz2 _bz2module.c -I$SL/include $SL/lib/libbz2.a"
  echo "_lzma _lzmamodule.c -I$SL/include $SL/lib/liblzma.a"
  echo "_sqlite3 $SQLITE_SRC -I$CP/Modules/_sqlite -I$SL/include -DPY_SQLITE_HAVE_SERIALIZE $SL/lib/libsqlite3.a"
} > "$W/Modules/Setup.local"
cd "$W"
make -j8 all LDFLAGS_NODIST="-fwasm-exceptions" > "$L/make.log" 2>&1 || { tail -n 20 "$L/make.log"; die "make failed (build/link/make.log)"; }
# A clash that only a static link creates is a trap at run time: wasm-ld's warning is the detector.
clashes() {
  if grep -E 'signature mismatch|duplicate symbol' "$1"; then
    die "the static link has clashing symbols (build/link/${1##*/}); add a rename header"
  fi
}
clashes "$L/make.log"
# makesetup drops a module it cannot read without an error; the judge would see it, but the build
# stops here first.
for m in _bz2 _lzma _sqlite3; do
  grep -q "PyInit_$m" "$W/Modules/config.c" || die "Setup.local's $m line was dropped (Modules/config.c)"
done

# The reactor: CPython's own compile and link commands for its main, read with `make -n`, with
# Programs/python.c swapped for the reactor's entry points. The link wraps the four WASI calls whose
# answers a snapshot would otherwise capture (recipes/reactor_main.c, "pinned"), poll_oneoff, whose
# absolute monotonic waits a store resumed from a checkpoint shifts into its own time, and iconv_open,
# whose wrapper refuses GB18030, which wasi-libc decodes wrongly without an error
# (recipes/iconv_refusals.c), and fcntl, whose wrapper answers F_DUPFD and
# F_DUPFD_CLOEXEC with ENOTSUP, which wasi-libc 34 answers EINVAL on preview1
# (recipes/fcntl_dup_refusal.c). It also wraps the C library's allocators (malloc, calloc,
# realloc, aligned_alloc, posix_memalign, and musl's __libc_malloc and __libc_calloc, which its
# locale and time-zone code calls), so the reactor counts every allocation a call's teardown makes
# while it skips frees, and frees what it skipped before teardown could take more than its budget
# (recipes/reactor_main.c, "Teardown frees nothing"). Each guard is compiled by the reactor's own
# command into its own object. Only the reactor carries them: the interpreter `make all` links
# above is CPython's own build, never shipped.
rm -f python.wasm Programs/python.o
make -n python.wasm LDFLAGS_NODIST="-fwasm-exceptions" > "$L/make-n.txt"
compile=$(grep -- '-o Programs/python.o' "$L/make-n.txt" | tail -n 1)
link=$(grep -- '-o python.wasm Programs/python.o' "$L/make-n.txt" | tail -n 1)
[ -n "$compile" ] && [ -n "$link" ] || die "make -n python.wasm printed no compile or link command"
compile=$(printf '%s' "$compile" | sed "s#[^ ]*Programs/python\.c#$HERE/recipes/reactor_main.c#; s#-o Programs/python\.o#-I$L -o Modules/reactor_main.o#")
# freopen refused: qhull's `TI` option is its one caller, and wasi-libc's freopen is the
# one user of fd_renumber, which the runner shadows; refusing it keeps the import list as
# it is (recipes/freopen_refusal.c).
GUARDS="iconv_refusals fcntl_dup_refusal freopen_refusal"
guards=""
guard_objects=""
for g in $GUARDS; do
  guards="$guards$(printf '%s' "$compile" | sed "s#[^ ]*/reactor_main\.c#$HERE/recipes/$g.c#; s#-o Modules/reactor_main\.o#-o Modules/$g.o#")
"
  guard_objects="$guard_objects Modules/$g.o"
done
WRAP="-Wl,--wrap=__wasi_clock_time_get -Wl,--wrap=__wasi_poll_oneoff -Wl,--wrap=__wasi_random_get -Wl,--wrap=__wasi_path_filestat_get -Wl,--wrap=__wasi_fd_filestat_get -Wl,--wrap=iconv_open -Wl,--wrap=iconv -Wl,--wrap=iconv_close -Wl,--wrap=fcntl -Wl,--wrap=freopen"
WRAP="$WRAP -Wl,--wrap=malloc -Wl,--wrap=calloc -Wl,--wrap=realloc -Wl,--wrap=aligned_alloc"
WRAP="$WRAP -Wl,--wrap=posix_memalign -Wl,--wrap=__libc_malloc -Wl,--wrap=__libc_calloc"
link=$(printf '%s' "$link" | sed "s#-o python\.wasm Programs/python\.o#-mexec-model=reactor $WRAP -Wl,--Map=$L/python.map -o $OUT/python.wasm Modules/reactor_main.o$guard_objects#")
host_from_source
"$HOSTPY" "$HERE/scripts/freeze_bootstrap.py" "$HERE/recipes/reactor_bootstrap.py" "$L/reactor_bootstrap.h" \
  > "$L/freeze.log" 2>&1 || { cat "$L/freeze.log"; die "the reactor's bootstrap did not compile"; }
# The zip's directory reader and resource reader: frozen modules of the
# reactor's own, named as CPython names its frozen modules.
"$HOSTPY" "$HERE/scripts/freeze_bootstrap.py" "$HERE/recipes/zip_directory.py" "$L/zip_directory.h" \
  ZIP_DIRECTORY "<frozen _zip_directory>" \
  >> "$L/freeze.log" 2>&1 || { cat "$L/freeze.log"; die "recipes/zip_directory.py did not compile"; }
"$HOSTPY" "$HERE/scripts/freeze_bootstrap.py" "$HERE/recipes/zip_resources.py" "$L/zip_resources.h" \
  ZIP_RESOURCES "<frozen _zip_resources>" \
  >> "$L/freeze.log" 2>&1 || { cat "$L/freeze.log"; die "recipes/zip_resources.py did not compile"; }
printf '%s\n%s%s\n' "$compile" "$guards" "$link" > "$L/reactor-commands.txt"
eval "$compile" > "$L/reactor-compile.log" 2>&1 || { tail -n 20 "$L/reactor-compile.log"; die "the reactor's compile failed"; }
for g in $GUARDS; do
  guard=$(printf '%s' "$guards" | grep -F -- "-o Modules/$g.o")
  eval "$guard" > "$L/guard-$g.log" 2>&1 || { tail -n 20 "$L/guard-$g.log"; die "recipes/$g.c did not compile"; }
done
eval "$link" > "$L/reactor-link.log" 2>&1 || { tail -n 20 "$L/reactor-link.log"; die "the reactor's link failed"; }
clashes "$L/reactor-link.log"
# scikit-learn's three random generators kept their own names: the map names
# each renamed mt_rand and liblinear's set_seed, which _liblinear's helper calls from another file,
# and none of the original names. The other renamed set_seed and bounded_rand_int calls sit in the
# file that defines them, where the compiler may inline every call and the linker then drop the
# definition, so they are not required; the weak-duplicate gate stood behind bounded_rand_int.
"$HOSTPY" "$HERE/scripts/weak_duplicates.py" link-map "$L/python.map" \
  --require sklearn_libsvm_mt_rand sklearn_liblinear_mt_rand sklearn_newrand_mt_rand sklearn_liblinear_set_seed \
  --forbid mt_rand set_seed bounded_rand_int > "$L/link-map-check.log" 2>&1 \
  || { cat "$L/link-map-check.log"; die "the link map shows a random generator of scikit-learn's under its original name, or none (build/link/link-map-check.log)"; }
tail -n 1 "$L/link-map-check.log"

# The link used the host-neutral wasm runtime that step 10 put in place, not
# the host tarball's: each runtime archive the link map names, its path resolved (the map writes
# bin/../share/...), lies in the replaced sysroot or builtins directory and equals its member of the
# pinned neutral tarball. Read only: the tarballs are opened, never unpacked, here. The directories
# are the compiling SDK's, whose driver links: $SDK's own on the arm64 hosts.
set -- "$CSDK"/lib/clang/*/lib/wasm32-unknown-wasip1
"$HOSTPY" - "$L/python.map" "$CSDK/share/wasi-sysroot" "$1" \
  "$(pinned "wasi-sysroot-$WASI_SDK_VERSION.0.tar.gz")" "$(pinned "libclang_rt-$WASI_SDK_VERSION.0.tar.gz")" \
  > "$L/runtime-check.log" 2>&1 <<'EOF_RUNTIME' || { cat "$L/runtime-check.log"; die "the link did not use the neutral wasm runtime"; }
import hashlib, os, re, sys, tarfile

link_map, sysroot, builtins, sysroot_tgz, rt_tgz = sys.argv[1:]
text = open(link_map, encoding="utf-8", errors="replace").read()
want = {
    "libc++.a": (sysroot, sysroot_tgz, "lib/wasm32-wasip1/eh/libc++.a"),
    "libc++abi.a": (sysroot, sysroot_tgz, "lib/wasm32-wasip1/eh/libc++abi.a"),
    "libclang_rt.builtins.a": (builtins, rt_tgz, "wasm32-unknown-wasip1/libclang_rt.builtins.a"),
}
members = {}
for tgz in (sysroot_tgz, rt_tgz):
    with tarfile.open(tgz) as t:
        for info in t:
            inside = info.name.split("/", 1)[-1]
            if info.isfile() and any(m == inside for _, g, m in want.values() if g == tgz):
                members[inside] = hashlib.sha256(t.extractfile(info).read()).hexdigest()
for name, (root, _, member) in want.items():
    used = sorted({os.path.realpath(p) for p in re.findall(r"(\S+/" + re.escape(name) + r")\(", text)})
    if len(used) != 1:
        sys.exit(f"ERROR: the link map names {len(used)} {name}: {used}")
    if not used[0].startswith(os.path.realpath(root) + os.sep):
        sys.exit(f"ERROR: {used[0]} is not under {os.path.realpath(root)}")
    with open(used[0], "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    if sha != members.get(member):
        sys.exit(f"ERROR: {used[0]} is not the neutral tarball's {member}")
    print(f"{name}: {used[0]} {sha}")
EOF_RUNTIME
"$SDK/bin/llvm-strip" --strip-debug "$OUT/python.wasm"
# The judge's own check (tests/harness/constructors.py), run on the binary just linked; a binary
# that fails it is removed.
. "$HERE/scripts/steps/constructors.sh"
check_constructors "$OUT/python.wasm" "$L/constructors.log"
echo "reactor: $(wc -c < "$OUT/python.wasm" | tr -d ' ') bytes, $(shasum -a 256 "$OUT/python.wasm" | cut -c1-16)"
