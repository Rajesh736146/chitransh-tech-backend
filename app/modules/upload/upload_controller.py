"""File upload routes using Cloudflare R2."""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query

from app.core.dependencies import get_current_user
from app.modules.auth.model import User
from app.services.r2_storage_service import R2StorageService

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_DOC_TYPES = {"application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_DOC_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post(
    "/image",
    summary="Upload an image (profile pic, company logo, etc.)",
    status_code=status.HTTP_201_CREATED,
)
async def upload_image(
    file: UploadFile = File(...),
    folder: str = Query("images", description="Subfolder in R2 bucket"),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image size must be under 5 MB",
        )

    # Reset file pointer for upload
    await file.seek(0)

    r2 = R2StorageService()
    key = r2.upload_file(
        file=file.file,
        filename=file.filename or "image.png",
        folder=folder,
        content_type=file.content_type,
    )
    url = r2.generate_presigned_url(key, expires_in=7 * 24 * 3600)  # 7-day URL

    return {"key": key, "url": url, "content_type": file.content_type}


@router.post(
    "/document",
    summary="Upload a document (resume, cover letter, etc.)",
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    folder: str = Query("documents", description="Subfolder in R2 bucket"),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type. Allowed: {', '.join(ALLOWED_DOC_TYPES)}",
        )

    content = await file.read()
    if len(content) > MAX_DOC_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document size must be under 10 MB",
        )

    await file.seek(0)

    r2 = R2StorageService()
    key = r2.upload_file(
        file=file.file,
        filename=file.filename or "document.pdf",
        folder=folder,
        content_type=file.content_type,
    )
    url = r2.generate_presigned_url(key, expires_in=7 * 24 * 3600)

    return {"key": key, "url": url, "content_type": file.content_type}


@router.delete(
    "/",
    summary="Delete a file from R2",
)
async def delete_file(
    key: str = Query(..., description="Object key to delete"),
    current_user: User = Depends(get_current_user),
):
    r2 = R2StorageService()
    r2.delete_file(key)
    return {"message": "File deleted", "key": key}
