Spec 095's build tools and measurement data (2026-10-21, the builder), kept so a later session can
resume the build. Scratch tools, not judge code: they write the judge files (the three TOMLs, the
expected lists, the gaps, the shards and the workflow's lists) from the data here.

Each script names its folder as SP (the scratchpad of the session that wrote it) and the worktree
as W; set both to this folder's data/ and to the worktree before running.

scripts/
  inventory.py     the three sdists' staged tests folders and test files -> data/inventory.json
  gen_ini.py       tests/upstream/{scipy,scikit-learn,statsmodels}.ini from the sdists' settings
  extra.py         data/extra.json: not_selected, smoke_cover, derived per family
  gen095.py        init: pass 1's groups by the survey's folder fuel; write: the TOMLs, the
                   expected lists and the known gaps from groups/splits/measured/classes/extra
  lanes.py         deal release groups into N serial lanes (node-id files)
  lanes.sh         run a pass's three lanes with the poller and the measurement plugin
  fuel095.py       pytest plugin (-p fuel095): every check's metrics and facts, pass or fail, to
                   $FUEL095_OUT/<pid>.jsonl (the judge records fuel only for a passing check)
  poller.py        tails every guest stream with wall times (build/095/poll-<pass>.tsv)
  split_plan.py    per-file and per-test fuel estimates from the poller and the measured fuel
  pass2.py         repack groups past 480 G by whole files, files past it by [[split]] -k
                   (character prefixes of parameters; pytest in the guest compiles at most about
                   200 -k terms, kdepth.py)
  fix_special.py   betainc and betaincc: their own split groups, 100 us clock step
  run_pass2.sh     the repack from pass 1's groups
  merge_fuel.py    measured.json from the plugin's jsonl files; lists the unmeasured groups
  classify.py      the class catalog; data/classes.json from the kept streams
  gen_shards.py    tests/release_shards.toml's three-family section and the workflow's lists
  probe.py, probes.sh  one or more node ids in the guest with a long traceback (CLOCK=<ns>)
  status.py        where the build stands (data/status.txt)
  gen_stages.py    the base's stage digests (tests/fixtures/upstream-stages.json)
  setup095.sh      clone the main tree's frozen set and tarballs into the worktree

data/
  groups-pass1.json, splits-pass1.json   pass 1 (one group per folder or pack of small folders)
  groups.json, splits.json               pass 2 (as the TOMLs on the branch hold them)
  measured.json, facts.json              each group's judge-measured fuel and facts, EXECUTED on
                                         set d0d91cef, darwin-arm64
  classes.json                           each group's classes with their members
  status.txt                             unmeasured and over-bound groups at the stop
  base-unit-run.txt                      the new unit rows run on the base harness (failing)
