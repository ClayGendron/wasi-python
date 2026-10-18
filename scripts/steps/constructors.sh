# Sourced by step 60 (spec 023, Decision 4): the judge's own constructor and feature check
# (tests/harness/constructors.py) on the binary just linked, with $HERE and $HOSTPY set. A binary
# that fails is removed before the step stops, so no later step run by name (`build.sh 80 90`)
# can snapshot it, and Wizer never hangs on its constructor (spec 023's build review, F6).
check_constructors() { # binary log
  if ! PYTHONPATH="$HERE/tests${PYTHONPATH:+:$PYTHONPATH}" "$HOSTPY" -m harness.constructors "$1" > "$2" 2>&1; then
    cat "$2"
    rm -f "$1"
    echo "ERROR: python.wasm has a static constructor or feature no review has read ($2); it is removed" >&2
    exit 1
  fi
  cat "$2"
}
