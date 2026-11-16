# 182: A class for tests the collector flips

## Changelog

### For contributors

- **A failing class check names every test that moved.** Its message, and a gap's "fails differently" reason, now list each test that joined or left the class, so a job log is enough to re-pin it. jinja2's asyncio classes and fontTools' counted-clock class name the tests the garbage collector moves, which may fail or pass. [Two tiers of tests](https://claygendron.github.io/wasi-python/contributing/release-process/#two-tiers-of-tests)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "182"
changed = [
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r-no-asyncio-loop-error]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[jinja2-r-no-asyncio-loop]",
    "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[fonttools-r-rest-counted-clock]",
]
units = 11
[claim.judge]
"tests/harness/scan.py" = "moved() gives a class's every +id and -id finding on one line, none cut, and moved_line() finds it in a failure message; report() and digest() do not change, so no gap's match does"
"tests/harness/plugin.py" = "a gap that fails differently keeps the message's first line, cut to 240 characters, as before, and appends its moved line whole, so the job log and the record's reason name every test that joined or left the class"
"tests/harness/upstream.py" = "an ordinary class may name collector_moves, tests the collector's timing moves into it, into a sibling class or to a pass; class_findings leaves them out, members or not, and every other member stays exact; judge_group's sorting and the passes count do not change; the rules refuse an empty, unsorted or repeated list, a named test in the class's list file or named by a node-limited class, collector_moves with nodes, and collector_moves in CPython's family"
"tests/checks/test_v1_3_upstream_suites.py" = "test_upstream_class passes the class's collector_moves to class_findings, adds the moved line to its message, and records collector_moves_in, the named tests that were members, for a class that names any"
"tests/upstream/jinja2.toml" = "jinja2-r's no-asyncio-loop-error names nine collector moves (four from its list's history, five from run 43865484595's members, reproduced by digest) and no-asyncio-loop six (its list's history); a leaked event loop's warning lands on whichever test runs when the collector fires (181's Decision 2; the owner's choice of 2026-11-01, 'Restore + follow-up spec')"
"tests/upstream/fonttools.toml" = "fonttools-r-rest's counted-clock names TimerTest::test_split, which passes when a collector pass reads the counted clock in its second lap (181's Decision 3; back in the class in run 43865484595)"
"tests/upstream/expected/jinja2-r/no-asyncio-loop-error.txt" = "the four collector moves it held leave it (test_custom_async_iteratable_filter[asyncio-<lambda>0], test_join_attribute[<lambda>1], test_simple_select_attr[<lambda>0], test_sum[<lambda>1]); nine stable members stay"
"tests/upstream/expected/jinja2-r/no-asyncio-loop.txt" = "the two collector moves it held leave it (test_streamfilter_extension, test_balancing); 102 stable members stay"
"tests/known_gaps.toml" = "jinja2-r-no-asyncio-loop-error 9, 1891e18dfe2d and jinja2-r-no-asyncio-loop 102, ea1eb2ac4985: the stable members, the same in every state the list files' history and run 43865484595 show; fonttools-r-rest-counted-clock stays 2, 0c61ab6175e3"
"tests/unit/test_upstream.py" = "the moved line, a class leaving the collector's tests out, two siblings in three states, the six rules and the three classes that carry the key"
"tests/unit/test_plugin.py" = "a gap that fails differently names what moved, past the first line's cut"
"context/release-claims/182-a-class-for-tests-the-collector-flips.toml" = "182's block: the three release-tier classes"
```
