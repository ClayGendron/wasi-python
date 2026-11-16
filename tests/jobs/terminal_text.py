"""Golden job: terminal text with rich, markdown-it-py, mdurl and Pygments.

Usage: terminal_text.py <data dir> <out dir> (both unused). rich draws a table, a panel, a tree,
Markdown (through markdown-it-py), highlighted code (through Pygments) and a pretty-printed value
on a recording console that writes to a string, with its width, colour system and terminal fixed
and no environment read, and exports the recording as text, HTML and SVG, each printed as length
and SHA-256. markdown-it-py renders CommonMark and lists its tokens, mdurl parses, encodes and
decodes a URL, and Pygments highlights code as HTML and for a terminal and guesses a lexer.
"""

import hashlib
import io
from importlib.metadata import version

import markdown_it
import mdurl
import pygments
from pygments.formatters import HtmlFormatter, TerminalFormatter
from pygments.lexers import PythonLexer, guess_lexer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.pretty import Pretty
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

print(
    "versions",
    f"rich={version('rich')}",
    f"markdown-it-py={version('markdown-it-py')}",
    f"mdurl={version('mdurl')}",
    f"pygments={version('pygments')}",
)


def digest(text):
    data = text.encode() if isinstance(text, str) else text
    return f"{len(data)} {hashlib.sha256(data).hexdigest()[:16]}"


CODE = 'def area(r):\n    """A circle\'s area."""\n    return 3.14159 * r ** 2\n'
TEXT = (
    "# Notes\n\nSome *emphasis*, some **strong**, `code` and a [link](https://example.org/a b).\n\n"
    "- one\n- two\n\n```python\nprint('hi')\n```\n"
)

console = Console(
    record=True,
    width=80,
    force_terminal=True,
    color_system="truecolor",
    file=io.StringIO(),
    _environ={},
)
table = Table(title="Sales")
for column in ("Region", "Units", "Price"):
    table.add_column(column, justify="right" if column != "Region" else "left")
for row in (("North", "120", "9.50"), ("South", "85", "10.25"), ("Éast–wést", "7", "1,000.00")):
    table.add_row(*row)
console.print(table)
console.print(Panel("A panel's [bold red]markup[/] and text", title="Panel", subtitle="end"))
tree = Tree("root")
branch = tree.add("branch")
branch.add("leaf one")
branch.add("[italic]leaf two[/]")
tree.add("another")
console.print(tree)
console.print(Markdown(TEXT))
console.print(Syntax(CODE, "python", line_numbers=True, theme="monokai"))
console.print(Pretty({"numbers": [1, 2.5, 3j], "nested": {"a": (None, True)}, "text": "wide ✓"}))
print("rich ansi", digest(console.file.getvalue()))
print("rich text", digest(console.export_text(clear=False)))
print("rich html", digest(console.export_html(inline_styles=True, clear=False)))
print("rich svg", digest(console.export_svg(unique_id="job")))

md = markdown_it.MarkdownIt("commonmark")
html = md.render(TEXT)
print("markdown html", digest(html))
print("markdown tokens", [t.type for t in md.parse(TEXT)])
print(html.splitlines()[2])

url = mdurl.parse("https://user@example.org:8080/a path/ü?q=1#frag")
print("mdurl", url.protocol, url.hostname, url.port, url.pathname, url.search, url.hash)
print("mdurl encode", mdurl.encode("/a path/ü?q=%zz"), mdurl.decode("/a%20path/%C3%BC"))
print("mdurl format", mdurl.format(url))

print("pygments html", digest(pygments.highlight(CODE, PythonLexer(), HtmlFormatter())))
print("pygments css", digest(HtmlFormatter().get_style_defs(".highlight")))
print("pygments terminal", digest(pygments.highlight(CODE, PythonLexer(), TerminalFormatter())))
print("pygments guess", guess_lexer("#!/usr/bin/env python\nimport sys\nprint(sys.argv)\n").name)
