# Stand-in for lxml.isoschematron in the guest (spec 046, Decision 8), packed as
# lxml/isoschematron.py. The real package reads its XSL and RELAX NG resources by file path at
# import, which fails from the zip, and those resources carry terms the constitution's §4.12 does
# not name (the owner's question 82(b): out for 0.1.0). libxml2's own Schematron,
# lxml.etree.Schematron, is built in.
raise ImportError(
    "lxml.isoschematron is not in this build: it reads its stylesheets by file path, and their"
    " licences are not approved; use lxml.etree.Schematron"
)
