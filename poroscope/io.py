"""Safe in-memory image parsing for user-supplied microscope images."""
from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 16_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS * 2


def decode_image(contents: bytes) -> Image.Image:
    if not contents:
        raise ValueError("Image file is empty")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise ValueError("Maximum upload size is 12 MB")
    try:
        with Image.open(BytesIO(contents)) as opened:
            if opened.format not in {"PNG", "JPEG", "TIFF", "BMP", "WEBP"}:
                raise ValueError("Unsupported image format. Use PNG, JPEG, TIFF, BMP or WEBP")
            if opened.width * opened.height > MAX_PIXELS:
                raise ValueError("Maximum image size is 16 megapixels")
            return ImageOps.exif_transpose(opened).convert("RGB").copy()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("The uploaded file is not a valid supported image") from exc
