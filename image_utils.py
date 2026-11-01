"""Image processing and perceptual hashing for FindMe uploads.

Every uploaded image is normalised once, here:

* EXIF orientation is applied (phone photos are no longer sideways);
* transparency is flattened onto white (no black backgrounds in JPEG);
* very large photos are shrunk to 1200 px on the longest side;
* the result is always a compact, optimised JPEG.

``dhash`` produces a 64-bit difference hash.  Two photos of the same item
have a small Hamming distance even after re-compression or a small crop,
which lets the matcher use real picture evidence instead of filenames.
"""
import hashlib
import io

from PIL import Image, ImageOps

MAX_DIMENSION = 1200
JPEG_QUALITY = 85
JPEG_MIME = 'image/jpeg'


def _resample():
    """Lanczos filter across Pillow versions."""
    try:
        return Image.Resampling.LANCZOS
    except AttributeError:  # Pillow < 9.1
        return Image.LANCZOS


def dhash(img):
    """Return a 64-bit perceptual difference hash as 16 hex characters.

    The image is reduced to 9x8 greyscale pixels; each pixel is compared
    with its right neighbour, producing 64 bits.  Small edits, resizing and
    JPEG re-compression change very few bits.
    """
    small = img.convert('L').resize((9, 8), _resample())
    pixels = list(small.getdata())
    bits = 0
    for row in range(8):
        offset = row * 9
        for col in range(8):
            bits = (bits << 1) | (1 if pixels[offset + col] > pixels[offset + col + 1] else 0)
    return f'{bits:016x}'


def process_upload(file):
    """Normalise an uploaded image.

    Returns ``(pil_image, jpeg_bytes, sha256_hex, dhash_hex)``.
    Raises ``ValueError`` for files Pillow cannot decode.
    """
    try:
        source = Image.open(file)
    except Exception as exc:  # Pillow raises several unrelated subclasses
        raise ValueError('Unsupported or corrupt image file') from exc

    with source:
        # Apply the camera's EXIF orientation before resizing.
        img = ImageOps.exif_transpose(source)

        # Flatten transparency onto white so JPEG output never turns black.
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            rgba = img.convert('RGBA')
            background = Image.new('RGB', rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.getchannel('A'))
            img = background
        else:
            img = img.convert('RGB')

        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), _resample())

        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', optimize=True, quality=JPEG_QUALITY)
        data = buffer.getvalue()

    return img, data, hashlib.sha256(data).hexdigest(), dhash(img)
