"""Small wasm modules for the harness self-tests, written in WAT and built with wasmtime.wat2wasm.

Each mirrors one shape the driver and the v1.1 rules must handle: a command, a plain reactor
with the door, a snapshot, a module with a third import, and one with no entry point.
"""

from __future__ import annotations

from pathlib import Path

import wasmtime

DOOR_IMPORT = '(import "host" "call" (func $door (param i32 i32 i32 i32) (result i32)))'
WASI = "wasi_snapshot_preview1"

# The door exercise: write "abc" at 16, call the door, and report what came back:
# 0 = "cba" received; 101 = no host (-1); 102 = host fault (-2); 50 = wrong bytes.
DOOR_RUN = """
  (func (export "run") (result i32) (local $rc i32) (local $p i32)
    (i32.store8 (i32.const 16) (i32.const 97))
    (i32.store8 (i32.const 17) (i32.const 98))
    (i32.store8 (i32.const 18) (i32.const 99))
    (local.set $rc (call $door (i32.const 16) (i32.const 3) (i32.const 100) (i32.const 104)))
    (if (i32.lt_s (local.get $rc) (i32.const 0))
      (then (return (i32.sub (i32.const 100) (local.get $rc)))))
    (if (i32.ne (i32.load (i32.const 104)) (i32.const 3)) (then (return (i32.const 50))))
    (local.set $p (i32.load (i32.const 100)))
    (if (i32.ne (i32.load8_u (local.get $p)) (i32.const 99)) (then (return (i32.const 50))))
    (if (i32.ne (i32.load8_u (i32.add (local.get $p) (i32.const 2))) (i32.const 97))
      (then (return (i32.const 50))))
    (i32.const 0))
"""

# A session's exports, a turn that runs nothing, a turn's stdin that is taken and dropped, and
# a shutdown that does nothing, and a `prepare` that refuses.
SESSION = """
  (func (export "turn") (param i32 i32) (result i32) (i32.const 0))
  (func (export "turn_input") (param i32 i32) (result i32) (i32.const 0))
  (func (export "shutdown") (result i32) (i32.const 0))
  (func (export "prepare") (param i32 i32) (result i32) (i32.const -1))
"""

HOST_ALLOC = """
  (global $next (mut i32) (i32.const 1024))
  (func (export "host_alloc") (param $n i32) (result i32) (local $p i32)
    (local.set $p (global.get $next))
    (global.set $next (i32.add (global.get $next) (local.get $n)))
    (local.get $p))
"""

PLAIN_REACTOR = f"""
(module
  {DOOR_IMPORT}
  (import "{WASI}" "random_get" (func $random (param i32 i32) (result i32)))
  (memory (export "memory") 1)
  (global $ready (mut i32) (i32.const 0))
  {HOST_ALLOC}
  (func (export "_initialize") (global.set $ready (i32.const 1)))
  (func (export "wizer.initialize"))
  {DOOR_RUN}
  {SESSION}
)
"""

SNAPSHOT = f"""
(module
  {DOOR_IMPORT}
  (memory (export "memory") 1)
  {HOST_ALLOC}
  {DOOR_RUN}
  {SESSION}
)
"""

# A snapshot as sets before bounded sessions were: no `turn` and no `shutdown`.
BEFORE_SESSIONS = f"""
(module
  {DOOR_IMPORT}
  (memory (export "memory") 1)
  {HOST_ALLOC}
  {DOOR_RUN}
)
"""

# A snapshot with `turn` and without `shutdown`.
TURN_ONLY = f"""
(module
  {DOOR_IMPORT}
  (memory (export "memory") 1)
  {HOST_ALLOC}
  {DOOR_RUN}
  (func (export "turn") (param i32 i32) (result i32) (i32.const 0))
)
"""

# A reactor whose run() returns 5 only if _initialize ran first.
INIT_ORDER = """
(module
  (memory (export "memory") 1)
  (global $ready (mut i32) (i32.const 0))
  (func (export "_initialize") (global.set $ready (i32.const 1)))
  (func (export "run") (result i32)
    (if (result i32) (global.get $ready) (then (i32.const 5)) (else (i32.const 9)))))
"""

COMMAND_EXIT_7 = f"""
(module
  (import "{WASI}" "proc_exit" (func $exit (param i32)))
  (memory (export "memory") 1)
  (func (export "_start") (call $exit (i32.const 7))))
"""

SPIN = """
(module
  (memory (export "memory") 1)
  (func (export "run") (result i32) (loop $l (br $l)) (i32.const 0)))
"""

# run() returns the first 4 bytes from random_get, so two runs can be compared.
RANDOM_PROBE = f"""
(module
  (import "{WASI}" "random_get" (func $random (param i32 i32) (result i32)))
  (memory (export "memory") 1)
  (func (export "run") (result i32)
    (drop (call $random (i32.const 200) (i32.const 8)))
    (i32.load (i32.const 200))))
"""

# run() returns (realtime - fixed start) / 1 µs for the first clock read: 1 when deterministic.
CLOCK_PROBE = f"""
(module
  (import "{WASI}" "clock_time_get" (func $clock (param i32 i64 i32) (result i32)))
  (memory (export "memory") 1)
  (func (export "run") (result i32)
    (drop (call $clock (i32.const 0) (i64.const 0) (i32.const 304)))
    (i32.wrap_i64 (i64.div_u
      (i64.sub (i64.load (i32.const 304)) (i64.const 1767225600000000000))
      (i64.const 1000)))))
"""

# run() returns the difference of two monotonic clock reads in µs: the driver's step.
CLOCK_STEP_PROBE = f"""
(module
  (import "{WASI}" "clock_time_get" (func $clock (param i32 i64 i32) (result i32)))
  (memory (export "memory") 1)
  (func (export "run") (result i32)
    (drop (call $clock (i32.const 1) (i64.const 0) (i32.const 304)))
    (drop (call $clock (i32.const 1) (i64.const 0) (i32.const 312)))
    (i32.wrap_i64 (i64.div_u
      (i64.sub (i64.load (i32.const 312)) (i64.load (i32.const 304)))
      (i64.const 1000)))))
"""

# run() returns the monotonic clock's stated resolution in µs.
CLOCK_RES_PROBE = f"""
(module
  (import "{WASI}" "clock_res_get" (func $res (param i32 i32) (result i32)))
  (memory (export "memory") 1)
  (func (export "run") (result i32)
    (drop (call $res (i32.const 1) (i32.const 304)))
    (i32.wrap_i64 (i64.div_u (i64.load (i32.const 304)) (i64.const 1000)))))
"""

THIRD_IMPORT = f"""
(module
  {DOOR_IMPORT}
  (import "env" "sneak" (func $sneak (param i32) (result i32)))
  (memory (export "memory") 1)
  {HOST_ALLOC}
  (func (export "_initialize"))
  (func (export "wizer.initialize"))
  {DOOR_RUN}
)
"""

WRONG_DOOR_TYPE = """
(module
  (import "host" "call" (func $door (param i32) (result i32)))
  (memory (export "memory") 1)
  (func (export "run") (result i32) (i32.const 0)))
"""

NO_ENTRY = """
(module (memory (export "memory") 1) (func (export "other")))
"""


def build(directory: Path, name: str, wat: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_bytes(wasmtime.wat2wasm(wat))
    return path


# The exception-handling proposal's standard form: a tag, and a function type naming exnref.
EXCEPTIONS = """
(module
  (type (func (param exnref)))
  (tag $e (param i32))
  (func (export "throws") (throw $e (i32.const 1))))
"""

# One imported tag and one defined: the module's tag count is two.
IMPORTED_AND_DEFINED_TAGS = """
(module
  (import "env" "outer" (tag $outer (param i32)))
  (tag $inner (param i32))
  (func (export "throws") (throw $inner (i32.const 1))))
"""


def door_probe(ptr: int, length: int) -> str:
    """A snapshot-shaped guest whose run() sends one door frame of `length` bytes at `ptr` and
    returns the door's answer (0, -1 or -2): one page of memory, so 65536 is its end."""
    return f"""
(module
  {DOOR_IMPORT}
  (memory (export "memory") 1)
  {HOST_ALLOC}
  (func (export "run") (result i32)
    (call $door (i32.const {ptr}) (i32.const {length}) (i32.const 100) (i32.const 104))))
"""


# A module with a start function: guest code that runs at instantiation.
WITH_START = """
(module
  (memory (export "memory") 1)
  (func $boot (i32.store (i32.const 0) (i32.const 7)))
  (start $boot))
"""


# The door-free command shape with and without one page of data, for the fuel-at-instantiation
# rule: the driver must charge them alike.
def command_with_data(data: bool) -> str:
    segment = '(data (i32.const 16) "0123456789")' if data else ""
    return f"""
(module
  (import "{WASI}" "proc_exit" (func $exit (param i32)))
  (memory (export "memory") 1)
  {segment}
  (func (export "_start") (call $exit (i32.const 0))))
"""


def reactor_with_init(iterations: int) -> str:
    """A plain reactor whose _initialize loops `iterations` times: that cost must be metered."""
    return f"""
(module
  (memory (export "memory") 1)
  (func (export "_initialize") (local $i i32)
    (block $done (loop $next
      (br_if $done (i32.ge_u (local.get $i) (i32.const {iterations})))
      (local.set $i (i32.add (local.get $i) (i32.const 1)))
      (br $next))))
  (func (export "run") (result i32) (i32.const 0)))
"""


# A stand-in for the judge's raw turn driver: `turn` returns the length of the code
# written at its pointer plus the first byte there, and counts its calls; `shutdown` returns the
# count of turns. Each call that runs nothing else lets the driver's bookkeeping be checked.
TURNS = f"""
(module
  {DOOR_IMPORT}
  (memory (export "memory") 1)
  (global $turns (mut i32) (i32.const 0))
  {HOST_ALLOC}
  (func (export "turn") (param $p i32) (param $n i32) (result i32)
    (global.set $turns (i32.add (global.get $turns) (i32.const 1)))
    (if (result i32) (i32.eqz (local.get $n))
      (then (i32.const 0))
      (else (i32.add (local.get $n) (i32.load8_u (local.get $p))))))
  (func (export "shutdown") (result i32) (global.get $turns))
  (func (export "run") (result i32) (i32.const 0))
)
"""


# run() reads the realtime clock twice, then stats `f` in the
# grant at fd 4, and returns (its mtim - the second read) in µs: one step when a file's times
# follow the run's clock step, as the driver draws them from the same ticks.
FILE_TIME_PROBE = f"""
(module
  (import "{WASI}" "clock_time_get" (func $clock (param i32 i64 i32) (result i32)))
  (import "{WASI}" "path_filestat_get" (func $pstat (param i32 i32 i32 i32 i32) (result i32)))
  (memory (export "memory") 1)
  (data (i32.const 16) "f")
  (func (export "run") (result i32)
    (drop (call $clock (i32.const 0) (i64.const 0) (i32.const 304)))
    (drop (call $clock (i32.const 0) (i64.const 0) (i32.const 312)))
    (if (call $pstat (i32.const 4) (i32.const 0) (i32.const 16) (i32.const 1) (i32.const 8192))
      (then (return (i32.const -1))))
    (i32.wrap_i64 (i64.div_s
      (i64.sub (i64.load (i32.const 8240)) (i64.load (i32.const 312)))
      (i64.const 1000)))))
"""


# What a guest learns about a file, through the judge's driver. `run` stats `f` in the
# grant at fd 4 (after filling the result with 0xAA), stats it again after the host changes it
# (the door call between), opens and reads it and stats it by descriptor after the host reads it
# too, lists the grant, sets its times exactly by path and by descriptor, then "now", and stats
# fd 1 (stdout). Each answer goes through the door. Then it spins once for every set bit of each
# stat's inode, atim and mtim (never ctim, which hosts move by their own rules), so its fuel
# follows those values. It returns 0, or 10 + the step whose call failed.
FILE_FACTS_RESULT = 8192  # each stat's 64 bytes
FILE_FACTS_LISTING = 12288  # 1,024 bytes of fd_readdir
FILE_FACTS = f"""
(module
  {DOOR_IMPORT}
  (import "{WASI}" "fd_filestat_get" (func $fstat (param i32 i32) (result i32)))
  (import "{WASI}" "path_filestat_get" (func $pstat (param i32 i32 i32 i32 i32) (result i32)))
  (import "{WASI}" "fd_filestat_set_times"
    (func $fset (param i32 i64 i64 i32) (result i32)))
  (import "{WASI}" "path_filestat_set_times"
    (func $pset (param i32 i32 i32 i32 i64 i64 i32) (result i32)))
  (import "{WASI}" "fd_readdir" (func $readdir (param i32 i32 i32 i64 i32) (result i32)))
  (import "{WASI}" "path_open"
    (func $open (param i32 i32 i32 i32 i32 i64 i64 i32 i32) (result i32)))
  (import "{WASI}" "fd_read" (func $read (param i32 i32 i32 i32) (result i32)))
  (memory (export "memory") 1)
  (data (i32.const 16) "f")
  (global $acc (mut i64) (i64.const 0))
  {HOST_ALLOC}
  (func $send (param $p i32) (param $n i32)
    (drop (call $door (local.get $p) (local.get $n) (i32.const 100) (i32.const 104))))
  (func $stat_sent
    (call $send (i32.const {FILE_FACTS_RESULT}) (i32.const 64))
    (global.set $acc (i64.add (global.get $acc) (i64.add
      (i64.popcnt (i64.load (i32.const {FILE_FACTS_RESULT + 8})))
      (i64.add (i64.popcnt (i64.load (i32.const {FILE_FACTS_RESULT + 40})))
               (i64.popcnt (i64.load (i32.const {FILE_FACTS_RESULT + 48}))))))))
  (func (export "run") (result i32) (local $fd i32) (local $e i32) (local $i i64)
    (memory.fill (i32.const {FILE_FACTS_RESULT}) (i32.const 0xAA) (i32.const 64))
    ;; 1: the first stat; the host changes the file in this door call
    (local.set $e (call $pstat (i32.const 4) (i32.const 0) (i32.const 16) (i32.const 1)
      (i32.const {FILE_FACTS_RESULT})))
    (if (local.get $e) (then (return (i32.const 11))))
    (call $stat_sent)
    ;; 2: after the host's change
    (local.set $e (call $pstat (i32.const 4) (i32.const 0) (i32.const 16) (i32.const 1)
      (i32.const {FILE_FACTS_RESULT})))
    (if (local.get $e) (then (return (i32.const 12))))
    (call $stat_sent)
    ;; 3: open and read 16 bytes; the host reads it too in this door call
    (local.set $e (call $open (i32.const 4) (i32.const 0) (i32.const 16) (i32.const 1)
      (i32.const 0) (i64.const 0x3fffffff) (i64.const 0) (i32.const 0) (i32.const 300)))
    (if (local.get $e) (then (return (i32.const 13))))
    (local.set $fd (i32.load (i32.const 300)))
    (i32.store (i32.const 320) (i32.const 400))
    (i32.store (i32.const 324) (i32.const 16))
    (local.set $e (call $read (local.get $fd) (i32.const 320) (i32.const 1) (i32.const 304)))
    (if (local.get $e) (then (return (i32.const 13))))
    (call $send (i32.const 304) (i32.const 4))
    ;; 4: a stat by descriptor after both reads
    (local.set $e (call $fstat (local.get $fd) (i32.const {FILE_FACTS_RESULT})))
    (if (local.get $e) (then (return (i32.const 14))))
    (call $stat_sent)
    ;; 5: the grant's listing
    (local.set $e (call $readdir (i32.const 4) (i32.const {FILE_FACTS_LISTING}) (i32.const 1024)
      (i64.const 0) (i32.const 308)))
    (if (local.get $e) (then (return (i32.const 15))))
    (call $send (i32.const {FILE_FACTS_LISTING}) (i32.load (i32.const 308)))
    ;; 6: exact times by path (atim and mtim: flags 1 | 4)
    (local.set $e (call $pset (i32.const 4) (i32.const 0) (i32.const 16) (i32.const 1)
      (i64.const 111) (i64.const 222) (i32.const 5)))
    (if (local.get $e) (then (return (i32.const 16))))
    (local.set $e (call $pstat (i32.const 4) (i32.const 0) (i32.const 16) (i32.const 1)
      (i32.const {FILE_FACTS_RESULT})))
    (if (local.get $e) (then (return (i32.const 16))))
    (call $stat_sent)
    ;; 7: exact times by descriptor
    (local.set $e (call $fset (local.get $fd) (i64.const 333) (i64.const 444) (i32.const 5)))
    (if (local.get $e) (then (return (i32.const 17))))
    (local.set $e (call $fstat (local.get $fd) (i32.const {FILE_FACTS_RESULT})))
    (if (local.get $e) (then (return (i32.const 17))))
    (call $stat_sent)
    ;; 8: "now" by descriptor (flags 2 | 8)
    (local.set $e (call $fset (local.get $fd) (i64.const 0) (i64.const 0) (i32.const 10)))
    (if (local.get $e) (then (return (i32.const 18))))
    (local.set $e (call $fstat (local.get $fd) (i32.const {FILE_FACTS_RESULT})))
    (if (local.get $e) (then (return (i32.const 18))))
    (call $stat_sent)
    ;; 9: stdout
    (local.set $e (call $fstat (i32.const 1) (i32.const {FILE_FACTS_RESULT})))
    (if (local.get $e) (then (return (i32.const 19))))
    (call $stat_sent)
    ;; the spin: its fuel follows the answers
    (block $done (loop $next
      (br_if $done (i64.ge_u (local.get $i) (global.get $acc)))
      (local.set $i (i64.add (local.get $i) (i64.const 1)))
      (br $next)))
    (i32.const 0))
)
"""


def stat_loop(call: str, n: int) -> str:
    """A command that calls a two-argument preview1 call (`fd_filestat_get` or `fd_fdstat_get`)
    on fd 3 `n` times, its answer at address 0: the same instructions whichever it is."""
    return f"""
(module
  (import "{WASI}" "{call}" (func $call (param i32 i32) (result i32)))
  (memory (export "memory") 1)
  (func (export "_start") (local $i i32)
    (block $done (loop $next
      (br_if $done (i32.ge_u (local.get $i) (i32.const {n})))
      (drop (call $call (i32.const 3) (i32.const 0)))
      (local.set $i (i32.add (local.get $i) (i32.const 1)))
      (br $next)))))
"""
