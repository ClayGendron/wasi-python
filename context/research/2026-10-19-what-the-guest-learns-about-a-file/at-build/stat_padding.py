"""(The pre-build review's probes/stat_padding.py, copied with its work folder removed at exit.)
F8's second half: does the driver write the 7 padding bytes after a filestat's filetype? The
guest fills its result buffer with 0xAA, calls fd_filestat_get on the root preopen, and exits
with the number of padding bytes (offsets 17 to 23) that are no longer 0xAA.
Usage: uv run python -I stat_padding.py <tests dir> <work dir>"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from harness import guest  # noqa: E402
import wasmtime as wt
work = Path(tempfile.mkdtemp(prefix="pad-", dir=sys.argv[2]))
import atexit, shutil; atexit.register(shutil.rmtree, work, True)
wat = """(module
  (import "wasi_snapshot_preview1" "fd_filestat_get" (func $st (param i32 i32) (result i32)))
  (import "wasi_snapshot_preview1" "proc_exit" (func $exit (param i32)))
  (memory (export "memory") 1)
  (func (export "_start") (local $i i32) (local $n i32)
    (memory.fill (i32.const 0) (i32.const 0xAA) (i32.const 64))
    (drop (call $st (i32.const 3) (i32.const 0)))
    (local.set $i (i32.const 17))
    (loop $l
      (if (i32.ne (i32.load8_u (local.get $i)) (i32.const 0xAA))
        (then (local.set $n (i32.add (local.get $n) (i32.const 1)))))
      (local.set $i (i32.add (local.get $i) (i32.const 1)))
      (br_if $l (i32.lt_u (local.get $i) (i32.const 24))))
    (call $exit (local.get $n))))"""
p = work / "pad.wasm"; p.write_bytes(wt.wat2wasm(wat))
r = guest.run(p, [], workdir=work)
print(f"filestat padding bytes changed by the call: {r.exit_code} of 7 ({r.describe()})")
