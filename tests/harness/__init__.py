"""The progress harness: the judge of this repository.

It runs every check, prints the scoreboard by goal, compares the run with the last acceptance
(the ratchet), and records an acceptance only when asked.

Every module here is a judging file. Changing one changes the judge hash, and `--accept` then
needs `--accept-judge "<reason>"`.
"""
