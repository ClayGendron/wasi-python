# Work with Excel, PDF and XML files

This guide covers the office formats the artifact set carries libraries for: `.xlsx` workbooks
through pandas, openpyxl and xlsxwriter; PDFs through pypdf and reportlab; and XML and HTML
through lxml. Each section gives the one thing that differs from native Python.

The sandbox's default matters here. With nothing writable, a library that writes through a
temporary file fails; one that works in memory does not.

## Read and write Excel workbooks

Reading works everywhere: `pd.read_excel` and `openpyxl.load_workbook` read from a path in a grant
or from bytes. xlrd reads old `.xls` files.

Writing needs a temporary folder, because openpyxl always writes through `tempfile`, and
xlsxwriter does too unless it is told to work in memory. So with nothing writable, write `.xlsx`
through xlsxwriter in memory:

```python
pd.ExcelWriter(buf, engine="xlsxwriter", engine_kwargs={"options": {"in_memory": True}})
xlsxwriter.Workbook(buf, {"in_memory": True})
```

Without that, `df.to_excel(…)` raises `xlsxwriter.exceptions.FileCreateError`, and openpyxl's
`save` raises `FileNotFoundError` ("No usable temporary directory").

To use every writer, give the call a writable folder at `/tmp`
(`Grant(folder, "/tmp", writable=True)`, or `root=True`), or point `tempfile.tempdir` at a
writable grant inside the program.

`.ods` (`engine="odf"`) and `.xlsb` files need odfpy and pyxlsb, which are not carried.

## Read and write PDFs

**pypdf** reads, extracts text, merges, splits and encrypts with RC4. AES encryption
(`encrypt(…, algorithm="AES-128")`, or an AES file) needs `cryptography`, which is not carried,
and raises `pypdf.errors.DependencyError`.

**reportlab** builds PDFs in memory, with nothing writable: a canvas, a platypus document, and
`renderPDF` and `renderSVG` charts. It stamps the time and a random document id into each PDF;
pass `invariant=1` for the same bytes on every run.

reportlab's own fonts are not shipped. The fourteen standard PDF fonts (Helvetica, Times,
Courier, Symbol, ZapfDingbats) need no file. For Unicode text, register DejaVu Sans from
matplotlib's data, or any TrueType file in a granted folder:

```python
path = os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSans.ttf")
pdfmetrics.registerFont(TTFont("DejaVuSans", path))
```

reportlab has no bitmap renderer here: `renderPM` raises `RenderPMError`. Draw a chart to PDF or
SVG, or draw the bitmap with matplotlib. Its barcode and QR code modules are not in the zip.

## Parse and transform XML

lxml gives native lxml's answers for XPath, XSLT, XInclude, C14N, DTD, XML Schema, RELAX NG and
Schematron validation, the HTML parser and `iterparse`. Files are read and written by path inside
a grant. pandas' `read_xml` and `to_xml` use lxml by default, and `read_html` with no `flavor`
does too.

### Lock down an untrusted stylesheet

By default an XSLT stylesheet may read documents in any grant, external entities included, and
write into any writable grant. Give an untrusted stylesheet, or a trusted one that loads untrusted
documents, no file access:

```python
etree.XSLT(sheet, access_control=etree.XSLTAccessControl.DENY_ALL)
```

A read or write in the transform then raises "read rights … denied" or "write rights … denied".
`DENY_ALL` covers the transform, not the stylesheet's own `xsl:import` and `xsl:include`, which
load while the stylesheet compiles. To refuse those too, parse the stylesheet from its bytes with
a parser whose resolver refuses every URL, and compile it from that parse.

pandas' `read_xml(…, stylesheet=…)` applies its stylesheet with no access control.

### Decode unusual encodings in Python first

lxml's character conversion comes from the guest's C library, not GNU libiconv. Most Western,
Cyrillic and UTF-16 documents read and write as natively. Several East Asian encodings do not:
some documents fail, and GB18030 fails on purpose at its first byte above ASCII. In HTML and in
recover mode such a document does not raise: its text just ends there.

Python's own codecs are complete, so decode the bytes in Python and give lxml the text:

- XML: `etree.fromstring(data.decode("gb18030").encode("utf-8"), etree.XMLParser(encoding="utf-8"))`;
- HTML: `lxml.html.document_fromstring(data.decode("gb18030"))`, or
  `pd.read_html(io.StringIO(data.decode("gb18030")))`;
- to write, serialize with `encoding="unicode"` and encode the `str` with Python.

For what else differs from native, see the [limitations page](../reference/limitations.md).

## In one line

Read anything from a grant; write `.xlsx` in memory or give the call a writable `/tmp`; build PDFs
in memory with reportlab; and give untrusted XSLT `DENY_ALL`.
