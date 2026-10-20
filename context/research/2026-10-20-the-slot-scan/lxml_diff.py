# Spec 096: import lxml.html.diff and diff two fragments.
try:
    from lxml.html.diff import htmldiff
except Exception as e:
    print(f"import raises {type(e).__name__}: {e}")
else:
    print(htmldiff("<p>Hello world</p>", "<p>Hello there world</p>"))
