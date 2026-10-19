; Nondeterministic try_table nesting in the WebAssembly backend (LLVM 22.1.0).
; llc -O3 -mtriple=wasm32-unknown-wasip1 -exception-model=wasm -mattr=+exception-handling \
;     -wasm-use-legacy-eh=false -filetype=obj try-table-order.ll
; gives one of two objects from run to run (address-space randomization).
target triple = "wasm32-unknown-wasip1"

declare i32 @__gxx_wasm_personality_v0(...)
declare ptr @__cxa_allocate_exception()
declare void @__cxa_throw(ptr, ptr, ptr)
declare void @fail_a()
declare void @fail_b()

define void @f(i1 %c) personality ptr @__gxx_wasm_personality_v0 {
entry:
  br i1 %c, label %a, label %other

a:
  invoke void @fail_a()
          to label %unreach unwind label %cleanup1

other:
  br i1 %c, label %throw, label %b

throw:
  %e = call ptr @__cxa_allocate_exception()
  invoke void @__cxa_throw(ptr %e, ptr null, ptr null)
          to label %unreach unwind label %cleanup2

b:
  invoke void @fail_b()
          to label %unreach unwind label %cleanup1

unreach:
  unreachable

cleanup1:
  %p1 = cleanuppad within none []
  cleanupret from %p1 unwind label %cleanup2

cleanup2:
  %p2 = cleanuppad within none []
  cleanupret from %p2 unwind to caller
}
