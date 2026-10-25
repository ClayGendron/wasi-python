(module
  (tag $t)
  ;; burn: count n down to zero, then throw (or return)
  (func $burn_throw (param $n i32)
    (loop $l
      (local.set $n (i32.sub (local.get $n) (i32.const 1)))
      (br_if $l (i32.gt_s (local.get $n) (i32.const 0))))
    (throw $t))
  (func $burn_ret (param $n i32)
    (loop $l
      (local.set $n (i32.sub (local.get $n) (i32.const 1)))
      (br_if $l (i32.gt_s (local.get $n) (i32.const 0)))))
  ;; r rounds of: try_table { call callee(n) } catch $t
  (func (export "thrown") (param $r i32) (param $n i32)
    (loop $outer
      (block $h
        (try_table (catch $t $h)
          (call $burn_throw (local.get $n))))
      (local.set $r (i32.sub (local.get $r) (i32.const 1)))
      (br_if $outer (i32.gt_s (local.get $r) (i32.const 0)))))
  (func (export "returned") (param $r i32) (param $n i32)
    (loop $outer
      (block $h
        (try_table (catch $t $h)
          (call $burn_ret (local.get $n))))
      (local.set $r (i32.sub (local.get $r) (i32.const 1)))
      (br_if $outer (i32.gt_s (local.get $r) (i32.const 0)))))
)
