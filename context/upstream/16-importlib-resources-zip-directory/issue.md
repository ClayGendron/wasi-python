# `ZipReader.files()` parses the archive on every call; zipimport's directory already has it

- **Project:** importlib_resources (https://github.com/python/importlib_resources), where `importlib.resources` changes are proposed first; the same code is CPython's `Lib/importlib/resources/readers.py`.
- **Against:** CPython 3.15.0 (`Lib/importlib/resources/readers.py`, `Lib/zipfile/_path/`, `Lib/zipimport.py`).
- **Status:** drafted (spec 035, Decision 8). A courtesy issue: this project needs nothing from it, because its own recipe already answers from zipimport's dict (`recipes/zip_resources.py`).
- **Before posting:** the owner checks the project's contribution and AI-tool policy, and rewrites the text in their own words where it asks for that.

## The issue text (for the owner to post)

**Title:** `ZipReader.files()` parses the whole archive on every resource read

`zipimporter.get_resource_reader()` returns `importlib.resources.readers.ZipReader`, whose `files()` is `zipfile.Path(self.archive, self.prefix)`. Each call opens a new `ZipFile`, which parses the archive's central directory into a `ZipInfo` per member, and `zipfile.Path` then builds the set of every name and implied folder. Nothing is kept between calls. So every `importlib.resources.files(pkg).joinpath(name).read_bytes()` on a package imported from a zip costs time proportional to the whole archive, not to the resource.

zipimport already holds that directory, parsed, for the life of the process (`zipimporter._get_files()`, refreshed after `invalidate_caches()`).

Measured on a stdlib zip of 1,751 members (CPython 3.15.0 built for `wasm32-wasip1`, counting executed WebAssembly instructions, so the numbers repeat exactly):

- a first `zoneinfo.ZoneInfo("Europe/Paris")` read from `tzdata` in the zip: about 205 M instructions, of which about 198 M are the `zipfile` parse and name set (about 124,000 per member);
- the same read answered from zipimport's dict: about 8.6 M, the same on a zip four times larger.

`importlib.metadata.FastPath.zip_children` does the same once per process for a zip on `sys.path`.

A possible direction: give `ZipReader` a `Traversable` over the loader's own directory (`loader._get_files()`) for names, and keep `zipfile` for reading a member's bytes, so its CRC, local-header and decompression checks stay as they are. We did this outside the standard library for our runtime and compared every answer with `zipfile.Path`'s (bytes, listings, `is_file`, `is_dir`, `exists`, `name`, `str`, errors). The differences we found: odd names (`a//b`, duplicates, an empty name), where zipimport's implied folders differ from zipfile's; and freshness, since names come from zipimport's view of the archive, so a zip rewritten in place lists its old names (and `importlib.metadata` finds its old distributions) until `invalidate_caches()`, as its imports already do, where `zipfile.Path` re-reads the archive on every call. A third, `open(pwd=...)`, we closed by handing any password to `zipfile`.

## Facts behind it

- The measurements: `context/research/2026-10-17-the-zips-directory-is-read-once.md` (finding 3) and spec 035's landing notes (`context/specifications/035-the-zips-directory-is-read-once.md`).
- No open CPython or importlib_resources issue asked for this on 2026-10-17 (the memo's finding 6). CPython #121342 is related: direct use of `zipimport._zip_directory_cache` broke when 3.13 made invalidation lazy, so a reader must ask `_get_files()`.
