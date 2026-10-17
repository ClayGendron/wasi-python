"""Names macOS Finder and Windows Explorer write into folders a person browses (spec 018). No
build input reads them and no artifact may carry them. The judge keeps the same set as
`tests/harness/paths.OS_LITTER`; a unit check holds the two equal."""

OS_LITTER = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})
