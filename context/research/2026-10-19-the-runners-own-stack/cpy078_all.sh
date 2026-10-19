#!/bin/sh
# The eight trap entries of spec 065 (on its branch, 19c4acb), each alone, at 512 KiB and 8 MiB.
P="uv run --project /Users/claygendron/Git/Repos/wasi_python-078 python cpy078.py"
for S in 524288 8388608; do
  $P $S doctest -- test_doctest -m test_issue35753
  $P $S exceptions -- test_exceptions -m test_recursion_in_except_handler
  $P $S syntax-both -- test_syntax -m test_error_on_parser_stack_overflow
  $P $S odict-py -- test_ordered_dict -m '*.PurePythonOrderedDictTests.test_highly_nested'
  $P $S odict-py-subclass -- test_ordered_dict -m '*.PurePythonOrderedDictSubclassTests.test_highly_nested'
  $P $S odict-c-subclass -- test_ordered_dict -m '*.CPythonOrderedDictSubclassTests.test_highly_nested'
  $P $S traceback-module -- test_traceback
done
