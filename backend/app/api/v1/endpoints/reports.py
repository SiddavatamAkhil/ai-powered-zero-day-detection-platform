"""
Report generation endpoint. Pulls model comparison data already stored in
Postgres (Phase 3-6) and renders it through ml/reports/report_generator.py,
then streams the PDF back — no separate "reports" table needed since a
report is a derived view over existing data, not new state.
"""
import os
import sys
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.deps import get_current_user, get_dataset_service, get_training_service
from app.core.config import settings
from app.models.user import User
from app.services.dataset_service import DatasetError, DatasetService
from app.services.training_service import TrainingService

router = APIRouter(prefix="/reports", tags=["Reports"])

ML_PACKAGE_PARENT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if ML_PACKAGE_PARENT not in sys.path:
    sys.path.insert(0, ML_PACKAGE_PARENT)


@router.get("/dataset/{dataset_id}/pdf")
async def generate_dataset_report(
    dataset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    dataset_service: DatasetService = Depends(get_dataset_service),
    training_service: TrainingService = Depends(get_training_service),
):
    from ml.reports.report_generator import generate_evaluation_report

    try:
        dataset = await dataset_service.get(dataset_id)
    except DatasetError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))

    models = await training_service.list_models_for_dataset(dataset_id)
    if not models:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="No trained models found for this dataset yet.")

    known = [c.class_name for c in dataset.classes if c.split.value == "known"]
    unknown = [c.class_name for c in dataset.classes if c.split.value == "unknown_holdout"]

    model_results = [
        {
            "model_name": m.architecture.value,
            "accuracy": m.accuracy, "precision": m.precision, "recall": m.recall, "f1": m.f1,
            "mcc": m.mcc, "roc_auc": m.roc_auc, "false_positive_rate": m.false_positive_rate,
            "unknown_attack_recall": m.unknown_attack_recall,
            "training_time_seconds": m.training_time_seconds,
            "inference_time_ms_per_sample": m.inference_time_ms_per_sample,
        }
        for m in models
    ]

    reports_dir = os.path.join(settings.PROCESSED_DIR, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    output_path = os.path.join(reports_dir, f"{dataset_id}_evaluation_report.pdf")

    generate_evaluation_report(
        output_path=output_path,
        project_title="AI-Powered Zero-Day Attack Detection Platform — Evaluation Report",
        dataset_name=dataset.name,
        known_classes=known,
        unknown_classes=unknown,
        model_results=model_results,
    )

    return FileResponse(output_path, media_type="application/pdf", filename=f"{dataset.name}_report.pdf")
