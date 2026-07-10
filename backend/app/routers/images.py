"""Serve cached vocabulary illustrations (public — safe for <img> tags)."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..vocab_images import image_file_for_slug, manifest_has

router = APIRouter(prefix="/api/images", tags=["images"])


@router.get("/vocab/{slug}")
def vocab_image(slug: str):
    if not manifest_has(slug):
        raise HTTPException(status_code=404, detail="Image not found")

    path = image_file_for_slug(slug)
    if not path:
        raise HTTPException(status_code=404, detail="Image file missing")

    ext = path.rsplit(".", 1)[-1].lower()
    media = {"webp": "image/webp", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(
        ext, "application/octet-stream"
    )
    return FileResponse(
        path,
        media_type=media,
        headers={"Cache-Control": "public, max-age=86400, must-revalidate"},
    )
