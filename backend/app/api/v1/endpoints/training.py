"""
Training + model endpoints. Training itself runs in a BackgroundTask so
the HTTP request returns immediately with the queued run id; the frontend
polls GET /training/{run_id} for status (Phase 8 dashboard wires this to
a progress bar).
"""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_current_user, get_training_service, require_role
from app.models.ml_model import ModelArchitecture
from app.models.user import User, UserRole
from app.schemas.ml_model import MLModelRead, TrainingRequest, TrainingRunRead
from app.services.hyperparameter_tuning_service import HyperparameterTuningService
from app.services.training_service import TrainingError, TrainingService

router = APIRouter(tags=["Training & Models"])
_can_edit = require_role(UserRole.ADMIN, UserRole.ANALYST)


def get_tuning_service(service: TrainingService = Depends(get_training_service)) -> HyperparameterTuningService:
    return HyperparameterTuningService(service)


class GridSearchRequest(BaseModel):
    dataset_id: uuid.UUID
    architecture: ModelArchitecture
    learning_rates: list[float] = [1e-3, 1e-4]
    batch_sizes: list[int] = [64, 128]
    epochs: int = 10


class AblationRequest(BaseModel):
    dataset_id: uuid.UUID
    architecture: ModelArchitecture
    seeds: list[int] = [1, 2, 3, 4, 5]
    epochs: int = 20
    batch_size: int = 128
    learning_rate: float = 1e-3


@router.post("/training/runs", response_model=TrainingRunRead, status_code=status.HTTP_202_ACCEPTED)
async def start_training_run(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(_can_edit),
    service: TrainingService = Depends(get_training_service),
):
    try:
        run = await service.queue_training_run(request, triggered_by=user.id)
    except TrainingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))

    background_tasks.add_task(service.execute_training_run, run.id)
    return run


@router.get("/training/runs/{run_id}", response_model=TrainingRunRead)
async def get_training_run(
    run_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TrainingService = Depends(get_training_service),
):
    run = await service.get_training_run(run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Training run not found.")
    return run


@router.get("/models/compare/{dataset_id}", response_model=list[MLModelRead])
async def compare_models(
    dataset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TrainingService = Depends(get_training_service),
):
    """Returns every trained model for a dataset, for the model comparison dashboard."""
    return await service.list_models_for_dataset(dataset_id)


@router.post("/training/grid-search")
async def grid_search(
    request: GridSearchRequest,
    user: User = Depends(_can_edit),
    tuning_service: HyperparameterTuningService = Depends(get_tuning_service),
):
    """
    Runs a small hyperparameter grid SEQUENTIALLY and blocks until every
    combination completes. This is intentionally synchronous (unlike
    /training/runs) because a grid search return value IS the leaderboard —
    there's nothing useful to return immediately and poll for. For a large
    grid on a real dataset this will be slow; keep the grid small (as the
    defaults do) or move this behind a job queue if it becomes a bottleneck.
    """
    try:
        results = await tuning_service.grid_search(
            dataset_id=request.dataset_id,
            architecture=request.architecture,
            triggered_by=user.id,
            learning_rates=request.learning_rates,
            batch_sizes=request.batch_sizes,
            epochs=request.epochs,
        )
    except TrainingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return [
        {"hyperparameters": r.hyperparameters, "metrics": r.metrics, "run_id": str(r.run_id)}
        for r in results
    ]


@router.post("/training/ablation")
async def multi_seed_ablation(
    request: AblationRequest,
    user: User = Depends(_can_edit),
    tuning_service: HyperparameterTuningService = Depends(get_tuning_service),
):
    """
    Trains the SAME architecture + hyperparameters across N seeds and
    reports mean +/- std for every metric — the statistical rigor a
    capstone evaluation needs instead of a single noisy run. Synchronous
    for the same reason as grid-search above.
    """
    try:
        summary = await tuning_service.multi_seed_ablation(
            dataset_id=request.dataset_id,
            architecture=request.architecture,
            triggered_by=user.id,
            seeds=request.seeds,
            epochs=request.epochs,
            batch_size=request.batch_size,
            learning_rate=request.learning_rate,
        )
    except TrainingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return {
        "architecture": summary.architecture,
        "seeds": summary.seeds,
        "per_seed_metrics": summary.per_seed_metrics,
        "mean_metrics": summary.mean_metrics,
        "std_metrics": summary.std_metrics,
    }
