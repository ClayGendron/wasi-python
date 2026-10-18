(module
  (memory (export "memory") 1)
  (global $n (mut i32) (i32.const 0))
  (func (export "_initialize"))
  (func (export "wizer.initialize") (global.set $n (i32.const 41)) (i32.store (i32.const 0) (i32.const 7)))
  (func (export "run") (result i32) (global.get $n))
  (func (export "turn") (param i32 i32) (result i32) (i32.add (global.get $n) (i32.load (i32.const 0))))
  (func (export "host_alloc") (param i32) (result i32) (i32.const 64)))
