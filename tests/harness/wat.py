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
)
"""

SNAPSHOT = f"""
(module
  {DOOR_IMPORT}
  (memory (export "memory") 1)
  {HOST_ALLOC}
  {DOOR_RUN}
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
