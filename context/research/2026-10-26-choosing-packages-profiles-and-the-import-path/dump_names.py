import sys
from pathlib import Path
exec(Path("wasm_sections.py").read_text().split("def bucket")[0].replace('print(', 'void=(') )
with open("names.tsv", "w") as f:
    for idx, sz in sizes.items():
        f.write(f"{sz}\t{fn.get(idx, '?')}\n")
