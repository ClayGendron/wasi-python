"""Golden job: Pillow reads and writes JPEG through libjpeg-turbo.

Usage: jpeg_images.py <data dir> <out dir>.

A 256 x 192 RGB image is made from integer arithmetic on numpy's index grids, so the job reads no
file: smooth ramps, a product that wraps and sharp diagonal edges, which reach every frequency the
encoder quantizes. It is saved as JPEG with the defaults, at quality 95, without chroma
subsampling, and progressive with optimized Huffman tables; then as L and as CMYK, with the
defaults. For each file the job prints its length and SHA-256, then the mode, size and SHA-256 of
the pixels it decodes to. The library's versions come first, on a line of their own, so a different
libjpeg shows as that line and not as a hash. The output directory stays empty.

Encoding and decoding use libjpeg's integer DCT, which its SIMD code and its plain C code compute
alike, so the native oracle's SIMD build and the guest's plain C build give the same bytes."""

import hashlib
import io
import sys

import numpy as np
import PIL
from PIL import Image, features

WIDTH, HEIGHT = 256, 192


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def image() -> Image.Image:
    """The job's RGB image: the same pixels on every platform, from integer arithmetic alone."""
    y, x = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.int64)
    r = (x + y) % 256
    g = (x * y // 64) % 256
    b = np.where((x // 16 + y // 16) % 2 == 0, (3 * (x - y)) % 256, 255 - (x * 255) // (WIDTH - 1))
    return Image.fromarray(np.stack([r, g, b], axis=-1).astype(np.uint8), "RGB")


def encode(im: Image.Image, **options) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "JPEG", **options)
    return buf.getvalue()


def decoded(data: bytes) -> str:
    with Image.open(io.BytesIO(data)) as im:
        im.load()
        return f"{im.format} {im.mode} {im.width}x{im.height} {sha(im.tobytes())}"


def files() -> list[tuple[str, bytes]]:
    rgb = image()
    return [
        ("default", encode(rgb)),
        ("quality95", encode(rgb, quality=95)),
        ("subsampling0", encode(rgb, subsampling=0)),
        ("progressive-optimize", encode(rgb, progressive=True, optimize=True)),
        ("L", encode(rgb.convert("L"))),
        ("CMYK", encode(rgb.convert("CMYK"))),
    ]


def main() -> None:
    print(f"versions python={sys.version_info[0]}.{sys.version_info[1]} pillow={PIL.__version__}")
    print(
        f"libjpeg libjpeg_turbo={features.version('libjpeg_turbo')} jpg={features.version('jpg')}"
    )
    print(f"source RGB {WIDTH}x{HEIGHT} {sha(image().tobytes())}")
    for name, data in files():
        print(f"{name} {len(data)} {sha(data)}")
        print(f"{name} decodes to {decoded(data)}")


if __name__ == "__main__":
    main()
