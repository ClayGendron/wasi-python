"""The progress harness: the judge of this repository.

It runs every check, prints the scoreboard by goal, compares the run with the last acceptance
(the ratchet), and records an acceptance only when asked.

Every module here is a judging file. Changing one changes the judge hash, which the history
records; `--accept` needs `--accept-judge "<reason>"` only when a verdict-bearing file changed
(`paths.VERDICT_BEARING`).
"""
