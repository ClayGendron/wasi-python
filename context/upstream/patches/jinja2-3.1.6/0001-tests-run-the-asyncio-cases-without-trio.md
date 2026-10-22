- **Project:** Jinja (https://github.com/pallets/jinja)
- **Against:** 3.1.6 (the pinned sdist, `jinja2-3.1.6.tar.gz`, a test source of spec 067)
- **Status:** drafted
- **Title:** Run the async tests' asyncio cases when trio is not installed
- **Files:** tests/test_async.py, tests/test_async_filters.py
- **Why we carry it:** trio cannot be imported on our Python (CPython 3.15 for `wasm32-wasip1`;
  trio raises `NotImplementedError: unsupported platform` in `trio/_core/_run.py`), and it is not
  in our test kit. `tests/test_async.py` (60 test functions) and `tests/test_async_filters.py` (25)
  import trio at module level only to parametrize one fixture over `[_asyncio_run, trio.run]`, so
  their asyncio cases could not load either. With trio optional, the asyncio cases run and the
  trio cases skip ("trio is not installed").

The patch is `recipes/patches/jinja2-3.1.6/0001-tests-run-the-asyncio-cases-without-trio.patch`:
test code only, no file of the `jinja2/` package changes. Written by spec 067's build
(2026-10-21), the rule of its Decision 8.

**This is a facts sheet only. It must not be sent, and must not be used as the base of a pull
request.** The Pallets organization's contributing guide (READ, `gh api
repos/pallets/.github/contents/CONTRIBUTING.md`, 2026-10-21) says: "AI-generated PRs and issues
are closed on sight, without review or discussion. This applies regardless of code quality or
correctness. AI-generated contributions must not be reopened, cleaned up, or used as a base for
further work." This change was written by an AI tool. If the owner wishes to raise the point with
Jinja, it is theirs to do by hand, in their own words and their own code. Nothing has been posted,
and no agent will post anything to Pallets. Carrying the patch does not depend on sending
anything (§4.1).

## The facts

**What fails.** On a Python without trio, collecting `tests/test_async.py` and
`tests/test_async_filters.py` fails with `ModuleNotFoundError: No module named 'trio'` (EXECUTED
in our guest, spec 067's survey), so the asyncio half of both files never runs.

**How it was tested** (EXECUTED in our guest, spec 067's build): both files collect; the asyncio
cases run, the trio cases skip.
