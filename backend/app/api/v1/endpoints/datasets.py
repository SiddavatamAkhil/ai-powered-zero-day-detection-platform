"""
Dataset endpoints. File upload uses multipart/form-data; everything else
is JSON. All routes require authentication; mutating routes (upload,
clean, feature-engineer, split) require analyst or admin role — viewers
can look but not touch.
"""
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import get_current_user, get_dataset_service, require_role
from app.core.config import settings
from app.models.user import User, UserRole
from app.schemas.dataset import DatasetRead, OpenSetSplitConfig
from app.services.dataset_service import DatasetError, DatasetService

router = APIRouter(prefix="/datasets", tags=["Datasets"])

_can_edit = require_role(UserRole.ADMIN, UserRole.ANALYST)


@router.post("/upload", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    name: str = Form(...),
    label_column: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(_can_edit),
    service: DatasetService = Depends(get_dataset_service),
):
    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds maximum upload size.")

    try:
        dataset = await service.upload(name, label_column, file.filename, contents, user.id)
    except DatasetError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return dataset


import logging
import traceback

logger = logging.getLogger(__name__)

@router.get("", response_model=list[DatasetRead])
async def list_datasets(
    user: User = Depends(get_current_user),
    service: DatasetService = Depends(get_dataset_service),
):
    try:
        return await service.list_all()
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(f"Error in list_datasets: {exc}\n{tb}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Datasets fetch failed [{type(exc).__name__}]: {str(exc)} | TRACE: {tb[-300:]}"
        )


@router.get("/{dataset_id}", response_model=DatasetRead)
async def get_dataset(
    dataset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: DatasetService = Depends(get_dataset_service),
):
    try:
        return await service.get(dataset_id)
    except DatasetError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{dataset_id}/profile")
async def profile_dataset(
    dataset_id: uuid.UUID,
    user: User = Depends(_can_edit),
    service: DatasetService = Depends(get_dataset_service),
):
    """Inspects the raw file: discovers columns, class distribution, missing values."""
    try:
        profile = await service.profile_and_register_classes(dataset_id)
    except DatasetError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"message": "Profiling complete.", "class_distribution": profile["class_distribution"]}


@router.post("/{dataset_id}/clean")
async def clean_dataset(
    dataset_id: uuid.UUID,
    user: User = Depends(_can_edit),
    service: DatasetService = Depends(get_dataset_service),
):
    try:
        report = await service.clean(dataset_id)
    except DatasetError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return report


@router.post("/{dataset_id}/feature-engineer")
async def feature_engineer_dataset(
    dataset_id: uuid.UUID,
    user: User = Depends(_can_edit),
    service: DatasetService = Depends(get_dataset_service),
):
    try:
        result = await service.engineer_features(dataset_id)
    except DatasetError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"message": "Feature engineering complete.", "num_features": len(result.feature_columns)}


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: uuid.UUID,
    user: User = Depends(_can_edit),
    service: DatasetService = Depends(get_dataset_service),
):
    try:
        await service.delete(dataset_id)
    except DatasetError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{dataset_id}/open-set-split")
async def configure_open_set_split(
    dataset_id: uuid.UUID,
    config: OpenSetSplitConfig,
    user: User = Depends(_can_edit),
    service: DatasetService = Depends(get_dataset_service),
):
    try:
        return await service.configure_open_set_split(dataset_id, config)
    except DatasetError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))
