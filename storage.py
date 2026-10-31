"""Cloudinary image storage helper.

Used by app.save_image() only when CLOUDINARY_* env vars are all set.
Without them (local development) images are written to static/uploads
exactly as before, so local dev needs no accounts or credentials.
"""
import io

from PIL import Image
import cloudinary
import cloudinary.uploader


def cloudinary_configured(config):
    """True when all three Cloudinary credentials are present."""
    return bool(
        config.get('CLOUDINARY_CLOUD_NAME')
        and config.get('CLOUDINARY_API_KEY')
        and config.get('CLOUDINARY_API_SECRET')
    )


def _configure(config):
    cloudinary.config(
        cloud_name=config['CLOUDINARY_CLOUD_NAME'],
        api_key=config['CLOUDINARY_API_KEY'],
        api_secret=config['CLOUDINARY_API_SECRET'],
        secure=True,
    )


def upload_processed_image(img, public_id, config):
    """Upload an already-processed PIL image to Cloudinary as JPG.

    Args:
        img: PIL image (already thumbnailed/converted by save_image)
        public_id: e.g. "lost/3f2a..." (no extension)
        config: the Flask config (with CLOUDINARY_* values)

    Returns:
        The Cloudinary secure_url.
    """
    _configure(config)

    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', optimize=True, quality=85)
    buffer.seek(0)

    result = cloudinary.uploader.upload(
        buffer,
        resource_type='image',
        public_id=public_id,
        format='jpg',
        overwrite=False,
    )
    return result['secure_url']


def delete_image(public_id, config):
    """Delete an image from Cloudinary (best effort, never raises)."""
    try:
        _configure(config)
        cloudinary.uploader.destroy(public_id, resource_type='image')
    except Exception:
        pass
