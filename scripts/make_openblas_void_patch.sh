#!/bin/sh
# Make OpenBLAS 0.3.34's carried patches from their script:
#
#   scripts/make_openblas_void_patch.sh OUT_DIR
#
# It unpacks the pinned tarball (downloads/, its SHA-256 checked) into a fresh folder under OUT_DIR,
# commits the pristine tree in a git repository run as scripts/steps/apply_patches.sh runs git (no
# caller configuration, attributes or environment, a ceiling), runs scripts/openblas_make_void.py on
# it, and writes, with plain `git diff` and no other option:
#   OUT_DIR/0001-c-lapack-subroutines-return-void-1-of-2.patch and
#   OUT_DIR/0002-c-lapack-subroutines-return-void-2-of-2.patch   the convention, every file but
#       ilaver.c: one `git diff` cut in two at the first file at or after lapack-netlib/SRC/s, so
#       that each stays under the rules check's 1 MiB; the two concatenated are that one diff, byte
#       for byte
#   OUT_DIR/0003-ilaver-returns-void.patch   ilaver.c alone,
# and beside each its drafts' `Files:` line (`<patch>.files`), from `git diff --name-only`.
# The tree is added with --force: the tarball's own .gitignore hides two of its files, and an edit
# to one would otherwise be left out silently. The commit has a fixed identity. The script stops if
# the convention script's "files changed" count is not git's. The Python that runs the convention
# script is $PYTHON when set, else `uv run python -I` from the repository.
set -eu
HERE=$(CDPATH= cd "$(dirname "$0")/.." && pwd -P)
TOP=OpenBLAS-0.3.34
TARBALL="$HERE/downloads/$TOP.tar.gz"
P1=0001-c-lapack-subroutines-return-void-1-of-2.patch
P2=0002-c-lapack-subroutines-return-void-2-of-2.patch
P3=0003-ilaver-returns-void.patch
ILAVER=lapack-netlib/INSTALL/ilaver.c
CUT=lapack-netlib/SRC/s

die() {
  echo "ERROR: $*" >&2
  exit 1
}

[ "$#" -eq 1 ] || die "usage: make_openblas_void_patch.sh OUT_DIR"
[ -s "$TARBALL" ] || die "downloads/$TOP.tar.gz is missing: run scripts/00_download.sh"
want=$(grep "  $TOP.tar.gz\$" "$HERE/downloads/SHA256SUMS" | cut -c1-64)
[ -n "$want" ] || die "$TOP.tar.gz is not pinned in downloads/SHA256SUMS"
got=$(shasum -a 256 "$TARBALL" | cut -c1-64)
[ "$got" = "$want" ] || die "downloads/$TOP.tar.gz does not match its pin"

. "$HERE/scripts/steps/remove.sh"
mkdir -p "$1"
OUT=$(CDPATH= cd "$1" && pwd -P)
WORK="$OUT/work"
remove "$WORK"
mkdir -p "$WORK/home"
tar -xzf "$TARBALL" -C "$WORK"
TREE="$WORK/$TOP"
[ -d "$TREE" ] || die "the tarball did not unpack to $TOP"
g() {
  env -i PATH="$PATH" HOME="$WORK/home" XDG_CONFIG_HOME="$WORK/home" GIT_CONFIG_NOSYSTEM=1 \
    GIT_CONFIG_GLOBAL=/dev/null GIT_CEILING_DIRECTORIES="$WORK" \
    git -c core.quotePath=false -C "$TREE" "$@"
}
py() { # the Python that runs this project's scripts: $PYTHON, or uv's
  if [ -n "${PYTHON:-}" ]; then
    "$PYTHON" -I "$@"
  else
    (cd "$HERE" && uv run python -I "$@")
  fi
}
# Host litter: names an operating system writes into a folder on its own
# (macOS's .DS_Store in a fresh tree under a home folder, AppleDouble ._ files), by the one list in
# scripts/litter.py. Never OpenBLAS's: the tarball is checked to hold none, so unstaging them after
# each `add` drops no real file. They stay out of the pristine commit, the count and the patches
# (an untracked file is in no `git diff`).
LITTER_IN='
import sys
sys.path.insert(0, sys.argv[1])
from litter import has_litter
names = sys.stdin.buffer.read().decode("utf-8", "surrogateescape").split("\0")
with open(sys.argv[2], "w", encoding="utf-8", errors="surrogateescape") as f:
    f.writelines(n + "\n" for n in names if n and has_litter(n.rstrip("/")))
'
litter_in() { # the litter paths among the NUL-separated paths on stdin, one per line, into $1
  py -c "$LITTER_IN" "$HERE/scripts" "$1"
}
# A desktop writer rewrites or removes litter at any moment (spec 097). So each add leaves litter
# out by pathspec (scripts/litter.py's git_excludes), and git never opens a litter file; and the
# unstage, by has_litter, removes a staged one with update-index --force-remove, which compares
# nothing with the work tree, so a rewrite after the add cannot make it refuse.
EXCLUDES='
import sys
sys.path.insert(0, sys.argv[1])
from litter import git_excludes
sys.stdout.buffer.write(b"\0".join(s.encode() for s in [".", *git_excludes()]))
'
add_all() { # stage the tree, litter left out
  g add -A --force --pathspec-from-file="$WORK/add.pathspec" --pathspec-file-nul
}
unstage_litter() { # every staged litter path leaves the index; the files stay where they are
  g ls-files --cached -z | litter_in "$WORK/litter.txt"
  while IFS= read -r p; do
    g update-index --force-remove -- "$p"
  done < "$WORK/litter.txt"
}
tar -tzf "$TARBALL" | tr '\n' '\0' | litter_in "$WORK/tarball-litter.txt"
[ ! -s "$WORK/tarball-litter.txt" ] || die "the tarball itself holds a litter name: $(head -n 1 "$WORK/tarball-litter.txt")"

py -c "$EXCLUDES" "$HERE/scripts" > "$WORK/add.pathspec"
g init -q
add_all
unstage_litter
g -c user.name=wasi-python -c user.email=build@wasi-python.invalid commit -q -m pristine

py "$HERE/scripts/openblas_make_void.py" "$TREE" > "$OUT/make_void.txt"
cat "$OUT/make_void.txt"
said=$(sed -n 's/^files changed: //p' "$OUT/make_void.txt")
add_all
unstage_litter
counted=$(g diff --cached --name-only | wc -l | tr -d ' ')
g reset -q
[ "$said" = "$counted" ] || die "openblas_make_void.py says $said files changed, git diff names $counted"

g diff -- . ":!$ILAVER" > "$WORK/convention.diff"
g diff -- "$ILAVER" > "$OUT/$P3"
g diff --name-only -- "$ILAVER" > "$OUT/$P3.files"
# The convention's one diff, cut at a file boundary: git orders files by path, so every file
# before the cut is in 0001 and every file from it on in 0002, and the two concatenated are the
# one diff, byte for byte.
py - "$WORK/convention.diff" "$CUT" "$OUT/$P1" "$OUT/$P2" << 'EOF'
import re, sys
diff, cut, first, second = sys.argv[1:]
data = open(diff, "rb").read()
heads = [(m.start(), m.group(1).decode()) for m in re.finditer(rb"^diff --git a/(\S+) b/", data, re.M)]
at = next((pos for pos, path in heads if path >= cut), None)
if at is None or at == 0:
    sys.exit(f"ERROR: no file of the diff sorts at or after {cut}, or every file does")
open(first, "wb").write(data[:at])
open(second, "wb").write(data[at:])
for name, part in ((first, data[:at]), (second, data[at:])):
    files = re.findall(rb"^diff --git a/(\S+) b/", part, re.M)
    open(name + ".files", "wb").write(b"\n".join(files) + b"\n")
EOF
n1=$(wc -l < "$OUT/$P1.files" | tr -d ' ')
n2=$(wc -l < "$OUT/$P2.files" | tr -d ' ')
n3=$(wc -l < "$OUT/$P3.files" | tr -d ' ')
[ $((n1 + n2 + n3)) = "$counted" ] || die "the three patches name $((n1 + n2 + n3)) files, git diff names $counted"
remove "$WORK"
for p in "$P1" "$P2" "$P3"; do
  echo "$p: $(wc -c < "$OUT/$p" | tr -d ' ') bytes, $(wc -l < "$OUT/$p.files" | tr -d ' ') files, $(shasum -a 256 "$OUT/$p" | cut -c1-64)"
done
