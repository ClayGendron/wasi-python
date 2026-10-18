"""reportlab imported from a zip: does it find its own files inside the zip?

Run: uv run --no-project --python 3.12 python -I reportlab_from_zip.py WHEEL
WHEEL is reportlab-5.0.1-py3-none-any.whl (a wheel is a zip, so it goes on sys.path as is).
"""

import os
import sys

wheel = os.path.abspath(sys.argv[1])
sys.path.insert(0, wheel)

from reportlab.lib import utils  # noqa: E402

print("python", sys.version.split()[0])
print("reportlab", __import__("reportlab").Version, "from", utils.__file__)
print("utils.__loader__:", type(utils.__loader__).__name__)
print("isCompactDistro():", utils.isCompactDistro())
print("__rl_loader__ is None:", utils.__rl_loader__ is None)
member = os.path.join(wheel, "reportlab", "fonts", "Vera.ttf")
print("rl_isfile(<wheel>/reportlab/fonts/Vera.ttf):", utils.rl_isfile(member))
try:
    with utils.open_for_read(member) as f:
        print("open_for_read: read", len(f.read()), "bytes")
except Exception as e:
    print("open_for_read raised:", type(e).__name__)
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402

try:
    TTFont("Vera", member)  # a path inside the zip
    print('TTFont("Vera", <wheel>/reportlab/fonts/Vera.ttf): loaded')
except Exception as e:
    print('TTFont("Vera", <wheel>/reportlab/fonts/Vera.ttf) raised:', type(e).__name__)
