"""Golden job: YAML, TOML, templates, tables and encodings (spec 039, Decisions 9 and 11).

Usage: text_formats.py <data dir> <out dir> (both unused). A YAML round trip through the safe
loader and dumper (pyyaml's pure Python: the guest has no libyaml), several documents, and the
safe loader refusing a python tag; tomli-w read back by the stdlib's tomllib; a jinja2 template
with autoescape, StrictUndefined, a loop and filters; markupsafe; `df.to_markdown()` (tabulate,
found through its metadata) and a grid table; charset-normalizer guessing the encoding of one
German sentence's bytes in three encodings. For the cp1252 bytes it names cp1250, which decodes
this sentence the same, so the line records that guess.
"""

import tomllib
from importlib.metadata import version

import charset_normalizer
import jinja2
import markupsafe
import pandas as pd
import tabulate
import tomli_w
import yaml

names = ("pyyaml", "jinja2", "markupsafe", "tabulate", "tomli-w", "charset-normalizer", "pandas")
print("versions", " ".join(f"{d}={version(d)}" for d in names))

doc = {
    "name": "job",
    "steps": [{"run": "a", "n": 2}, {"run": "b", "ok": True}],
    "when": None,
    "ratio": 0.5,
}
dumped = yaml.safe_dump(doc, sort_keys=False)
print(dumped, end="")
print(yaml.safe_load(dumped) == doc)
print(list(yaml.safe_load_all("a: 1\n---\nb: [x, y]\n")))
try:
    yaml.safe_load("!!python/object/apply:os.system ['true']")
except yaml.constructor.ConstructorError as e:
    print("yaml refuses:", e.problem)

toml = tomli_w.dumps({"tool": {"name": "x", "deps": ["a", "b"], "n": 3}})
print(toml, end="")
print(tomllib.loads(toml))

env = jinja2.Environment(autoescape=True, undefined=jinja2.StrictUndefined)
template = env.from_string(
    "{% for r in rows %}<li>{{ r.name|title }}: {{ '%.1f'|format(r.v) }}</li>{% endfor %}{{ note }}"
)
print(
    template.render(rows=[{"name": "north", "v": 2.25}, {"name": "south", "v": 1}], note="<b>&</b>")
)
print(markupsafe.escape("<a href='x'>&</a>"), markupsafe.Markup("<i>%s</i>") % "<x>")

df = pd.DataFrame({"region": ["north", "south"], "units": [3, 5], "price": [2.5, 1.25]})
print(df.to_markdown(index=False))
print(tabulate.tabulate(df.values.tolist(), headers=list(df.columns), tablefmt="grid"))

text = "Grüße aus Köln: Straße, Bäcker, Übermut, Ärger und Öl. " * 4
for encoding in ("utf_8", "cp1252", "utf_16"):
    best = charset_normalizer.from_bytes(text.encode(encoding)).best()
    print(encoding, "->", best.encoding, str(best) == text)
