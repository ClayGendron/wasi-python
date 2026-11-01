"""A test-side stand-in for pikepdf, which cairocffi's test_cairo.py imports at its top to read
back the PDF files some of its tests write. pikepdf is a compiled binding of QPDF with no build for
wasm32-wasip1, so it is not in the test kit. With this stand-in the module collects and its other
tests run; each test that opens a PDF with pikepdf raises the error below, which the family's
expected class names. It is staged into the family's kit only, never into the product."""

MESSAGE = (
    "pikepdf is not in the test kit: it is a compiled QPDF binding with no wasm32-wasip1 build"
)


class _Missing:
    def __getattr__(self, name: str):
        raise ModuleNotFoundError(MESSAGE)


Pdf = _Missing()
