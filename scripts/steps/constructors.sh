# Sourced by steps 60 and 80: the judge's own constructor and feature check, and the import list
# (tests/harness/constructors.py) on the binary just linked, with $HERE and $HOSTPY set. A binary
# that fails is removed before the step stops, so no later step run by name (`build.sh 80 90`)
# can snapshot it, and Wizer never hangs on its constructor.
check_constructors() { # binary log
  if ! PYTHONPATH="$HERE/tests${PYTHONPATH:+:$PYTHONPATH}" "$HOSTPY" -m harness.constructors "$1" > "$2" 2>&1; then
    cat "$2"
    rm -f "$1"
    echo "ERROR: python.wasm has a static constructor or feature no review has read ($2); it is removed" >&2
    exit 1
  fi
  cat "$2"
}

# The binary's imports, module and field, against recipes/guest-imports.txt
# (tests/harness/import_list.py): a new import or a listed one it lacks removes the binary before
# the step stops, as above.
check_imports() { # binary log
  if ! PYTHONPATH="$HERE/tests${PYTHONPATH:+:$PYTHONPATH}" "$HOSTPY" -m harness.import_list "$1" > "$2" 2>&1; then
    cat "$2"
    rm -f "$1"
    echo "ERROR: $(basename "$1")'s imports are not recipes/guest-imports.txt ($2); it is removed" >&2
    exit 1
  fi
  cat "$2"
}
