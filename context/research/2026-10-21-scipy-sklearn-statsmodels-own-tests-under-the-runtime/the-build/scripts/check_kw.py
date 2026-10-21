"""Which split keywords pytest's parser refuses, and the first refused name in each."""

import json
from pathlib import Path

from _pytest.mark.expression import Expression

SP = Path(__file__).parent
for fam, ss in json.loads((SP / "splits.json").read_text()).items():
    for s in ss:
        for k in s["keywords"]:
            try:
                Expression.compile(k)
            except Exception as e:  # noqa: BLE001
                bad = [t for t in k.split(" or ") if not _ok(t)] if False else None
                for t in k.split(" or "):
                    try:
                        Expression.compile(t)
                    except Exception as e2:  # noqa: BLE001
                        print(s["file"], repr(t)[:200], str(e2)[:120])
                        break
                else:
                    print(s["file"], "whole fails:", str(e)[:200])
