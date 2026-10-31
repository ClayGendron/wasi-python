# 160: The rules follow the data

## Changelog

### For contributors

- **A red run on `dev` no longer stops other merges.** A red run after a merge opens an issue naming its red legs, the merged change's author fixes it forward the same day or reverts it, and other pull requests keep merging; a pull request no longer needs to be up to date with `dev`. [Review and landing](https://claygendron.github.io/wasi-python/contributing/review-and-landing/)
- **A review takes one round.** A round's fixes are one commit, and a Low finding answered in writing needs no second signing. A release's notes are read in its review against the threat model, which starts beside the release's last changes. [Release process](https://claygendron.github.io/wasi-python/contributing/release-process/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "160"
new = [
  "tests/checks/test_rules.py::test_the_red_run_issue_opens_on_a_red_merge_or_weekly_run_and_on_nothing_else",
  "tests/checks/test_rules.py::test_a_releases_security_review_reads_its_notes",
  "tests/unit/test_scan.py::test_a_releases_notes_are_read_in_its_security_review",
  "tests/unit/test_scan.py::test_a_release_up_to_0_1_2_may_have_its_notes_read_in_a_file_of_their_own",
  "tests/unit/test_scan.py::test_the_0_1_2_reviews_pass_the_release_notes_rule_unchanged",
  "tests/unit/test_scan.py::test_the_real_workflows_red_run_issue_holds",
  "tests/unit/test_scan.py::test_the_red_run_issue_scan_names_each_breach[*",
  "tests/unit/test_scan.py::test_the_red_run_issue_opens_on_a_red_merge_or_weekly_run_and_closes_on_a_green_merge",
  "tests/unit/test_scan.py::test_a_merges_run_whose_plan_failed_opens_the_issue_and_no_other_run_does",
  "tests/unit/test_budget.py::test_a_specification_past_2000_words_is_named_and_one_under_is_not",
  "tests/unit/test_budget.py::test_landing_notes_past_15_lines_are_named_and_15_are_not",
  "tests/unit/test_budget.py::test_a_long_specification_is_a_warning_and_never_a_failure",
  "tests/unit/test_budget.py::test_a_specification_dated_before_the_caps_is_not_named",
]
retired = ["tests/checks/test_rules.py::test_a_release_has_its_release_notes_review"]
units = 17
```
