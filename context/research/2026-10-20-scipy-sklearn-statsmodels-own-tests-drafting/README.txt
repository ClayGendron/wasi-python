Spec 095's drafting reads and probes (2026-10-20). Not a memo: the survey's memo replaces every
INFERRED number here (spec 095, Decision 1).

Inputs, each SHA-256 recomputed equal to downloads/SHA256SUMS before use (EXECUTED, shasum -a 256),
unpacked with tar into an empty scratch folder outside the repository, read as text only:
  scipy-1.18.1.tar.gz          52c4b742...2747307 (main's pin)
  scikit_learn-1.9.1.tar.gz    629cada3...82977   (main's pin)
  statsmodels-0.15.0.tar.gz    5d257fe5...aecbc   (spec 045's pin, on spec/045-statsmodels)

Readers (scripts/, run with `uv run --no-project python -I`, nothing imported from the trees):
  survey.py <package folder> <name> <out>   -> <name>-inventory.txt, <name>-risks.txt
      test files, `def test*` counts per subpackage, non-.py data under tests/, conftests, the
      test files' top-level imports, and per-file regex hits for what the platform lacks
      (subprocess, multiprocessing, threads, network words, ctypes, mmap, importorskip), the
      upstream slow markers, and imports of scipy's seven `tests`-tagged C modules. A hit is a
      word in the text, not a finding: "network" counts URLs in comments too.
  sm_datasets.py <statsmodels folder>       -> printed below
      statsmodels test files that load one of the thirteen datasets spec 045 leaves out.
  probe095.py <package> <label> <fuel> [args]  (guest probes, below)

Guest probes (EXECUTED, darwin-arm64, one process at a time, the judge's own embedder
tests/harness/guest.py, the snapshot binary, measured=False, on main's set rebuilt in the main
tree from the structural chain's tip dbecd2d, SHA256SUMS of build/artifacts as read at the run,
python-stdlib.zip 49,771,987 bytes; tests/upstream/package_drive.py as main has it, unchanged; the
kit of build/upstream/wheels): see probes.txt.

statsmodels and the thirteen left-out datasets (sm_datasets.py, EXECUTED):
  ccard 2, committee 1, copper 0, cpunish 5, fair 4, scotland 1, spector 4, star98 5, fertility 0,
  china_smoking 0, cancer 1, heart 1, interest_inflation 1: 19 test files in all (some are
  results/ modules the tests import); 3 files name get_rdataset or webuse (network).
