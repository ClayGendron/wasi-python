Drafting evidence for specs 066 and 067 (2026-10-20). No guest was built or run.

- sdists.txt: the 34 PyPI sdists 067 would pin (PyPI JSON; each downloaded, SHA-256 recomputed equal).
- tag-archives.txt: release-tag archives for the eight packages whose sdists carry no tests.
- inventory.txt: per package, test files, `def test` count, conftest count, features grepped
  (subprocess, threading, sockets, mmap, getsource, network), third-party imports, importorskip names.
  The first part reads the sdists (and, for 066, the pinned compiled sdists in downloads/); the second
  the tag archives.
- collection-risks.txt: test files whose top-level imports name a module neither the product, the
  stdlib, the kit nor the proposed extra kit has, or that use processes, threads or sockets.
- source-equality.txt: every .py file each pinned wheel installs, compared by SHA-256 with the same
  path in the sdist or tag archive (paths tried: as is, src/, lib/).
- product-top-level-names.txt: the top-level names in main's built python-stdlib.zip (1ce7381's set).
- scripts/: the readers used (run with `uv run --no-project --python 3.13 python -I`, from this
  folder, on extracted copies in a scratch folder; archives are data, never imported).
