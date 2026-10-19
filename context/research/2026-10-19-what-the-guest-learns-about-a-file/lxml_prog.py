
import json, sys
import lxml
from lxml import etree, objectify
dotted = lambda t: ".".join(map(str, t))
print(json.dumps({
    "builtin": [m for m in ("lxml.etree", "lxml.objectify") if m in sys.builtin_module_names],
    "lxml": lxml.__version__,
    "libxml2": dotted(etree.LIBXML_VERSION),
    "libxslt": dotted(etree.LIBXSLT_VERSION),
    "features": sorted(etree.LIBXML_FEATURES & {"iconv", "schematron", "zlib", "thread"}),
}))
