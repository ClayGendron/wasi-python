"""Decode a PNG with the stdlib alone (spec 023, Decision 8): zlib and the five row filters.

The judge compares a plot's pixels, never its PNG bytes alone: native matplotlib's Pillow deflates
with zlib-ng and the guest's with zlib, so equal pixels can make different files. This reads
8-bit, non-interlaced greyscale, RGB, grey-with-alpha and RGBA images (all a matplotlib PNG can
be) and returns the rows unfiltered, with no row's filter byte.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

SIGNATURE = b"\x89PNG\r\n\x1a\n"
CHANNELS = {0: 1, 2: 3, 4: 2, 6: 4}  # colour type -> samples per pixel


class PngError(ValueError):
    """The bytes are not a PNG this reader understands."""


@dataclass(frozen=True)
class Image:
    width: int
    height: int
    channels: int
    pixels: bytes  # rows top to bottom, each width * channels bytes

    @property
    def shape(self) -> tuple[int, int, int]:
        return (self.height, self.width, self.channels)


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def decode(data: bytes) -> Image:
    if data[:8] != SIGNATURE:
        raise PngError("no PNG signature")
    pos, header, idat = 8, None, []
    while pos < len(data):
        if pos + 8 > len(data):
            raise PngError("a chunk runs past the end")
        length, kind = struct.unpack(">I4s", data[pos : pos + 8])
        body = data[pos + 8 : pos + 8 + length]
        crc = data[pos + 8 + length : pos + 12 + length]
        if len(body) != length or len(crc) != 4:
            raise PngError(f"chunk {kind!r} runs past the end")
        if zlib.crc32(kind + body) != struct.unpack(">I", crc)[0]:
            raise PngError(f"chunk {kind!r} fails its CRC")
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
        pos += 12 + length
    if header is None:
        raise PngError("no IHDR chunk")
    width, height, depth, colour, method, filtering, interlace = header
    if depth != 8 or colour not in CHANNELS or (method, filtering, interlace) != (0, 0, 0):
        raise PngError(f"unsupported: depth {depth}, colour {colour}, interlace {interlace}")
    bpp = CHANNELS[colour]
    stride = width * bpp
    raw = zlib.decompress(b"".join(idat))
    if len(raw) != height * (stride + 1):
        raise PngError(f"{len(raw)} bytes of image data, not {height * (stride + 1)}")
    out = bytearray(height * stride)
    prev = bytearray(stride)
    for y in range(height):
        kind = raw[y * (stride + 1)]
        row = bytearray(raw[y * (stride + 1) + 1 : (y + 1) * (stride + 1)])
        if kind == 1:
            for i in range(bpp, stride):
                row[i] = (row[i] + row[i - bpp]) & 0xFF
        elif kind == 2:
            for i in range(stride):
                row[i] = (row[i] + prev[i]) & 0xFF
        elif kind == 3:
            for i in range(stride):
                left = row[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif kind == 4:
            for i in range(stride):
                left = row[i - bpp] if i >= bpp else 0
                up_left = prev[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + _paeth(left, prev[i], up_left)) & 0xFF
        elif kind != 0:
            raise PngError(f"row {y}: filter {kind}")
        out[y * stride : (y + 1) * stride] = row
        prev = row
    return Image(width, height, bpp, bytes(out))
