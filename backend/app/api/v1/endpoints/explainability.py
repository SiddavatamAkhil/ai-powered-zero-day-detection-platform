"""
Explainability endpoint — closes a real gap: ml/explainability/explainer.py
existed with no API surface reaching it. Loads the trained PyTorch model +
its persisted background/reference sample (saved at training time — see
TrainingService._run_supervised_pipeline) and delegates to
ExplainabilityService for a real SHAP or LIME explanation.
"""
import os
import sys

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_training_service
from app.models.user import User
from app.schemas.ml_model import ExplanationRequest
from app.services.training_service import TrainingService

router = APIRouter(prefix="/explainability", tags=["Explainability"])

ML_PACKAGE_PARENT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if ML_PACKAGE_PARENT not in sys.path:
    sys.path.insert(0, ML_PACKAGE_PARENT)


@router.post("/explain")
async def explain_prediction(
    request: ExplanationRequest,
    user: User = Depends(get_current_user),
    training_service: TrainingService = Depends(get_training_service),
):
    """
    Explains one sample's prediction from a trained model. `sample` must
    match the model's feature order — the frontend explainability page
    pulls this from an actual dataset row rather than free-typing floats,
    so ordering is guaranteed to match `feature_names`.
    """
    import torch

    from ml.explainability.explainer import ExplainabilityService
    from ml.training.trainer import build_model

    ml_model = await training_service.get_model_by_id(request.model_id)
    if ml_model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Model not found.")
    if ml_model.num_classes is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Explainability is only supported for supervised classifiers (cnn/bilstm/cnn_bilstm/transformer), not autoencoder/isolation forest.",
        )
    if not ml_model.background_data_path or not os.path.exists(ml_model.background_data_path):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="No background reference data saved for this model (only models trained after the explainability update have this).",
        )
    if not os.path.exists(ml_model.artifact_path):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Model artifact file is missing on disk.")

    sample = np.array(request.sample, dtype=np.float32)
    if len(sample) < ml_model.num_features:
        sample = np.pad(sample, (0, ml_model.num_features - len(sample)), mode="constant")
    elif len(sample) > ml_model.num_features:
        sample = sample[:ml_model.num_features]

    torch_model = build_model(ml_model.architecture.value, ml_model.num_features, ml_model.num_classes)
    torch_model.load_state_dict(torch.load(ml_model.artifact_path, map_location="cpu"))
    torch_model.eval()

    def predict_proba(X: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            logits = torch_model(torch.tensor(X, dtype=torch.float32))
            return torch.softmax(logits, dim=1).numpy()

    background = np.load(ml_model.background_data_path)
    feature_names = ml_model.feature_names or [f"feature_{i}" for i in range(ml_model.num_features)]
    class_names = ml_model.class_names or [f"class_{i}" for i in range(ml_model.num_classes)]

    service = ExplainabilityService(predict_proba, feature_names, class_names, background)

    try:
        if request.method == "lime":
            result = service.explain_with_lime(sample)
        else:
            result = service.explain_with_shap(sample)
    except ImportError as exc:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"{request.method} is not installed in this environment: {exc}",
        )

    return {
        "method": result.method,
        "predicted_class": result.predicted_class,
        "base_value": result.base_value,
        "contributions": [
            {"feature_name": c.feature_name, "contribution": c.contribution} for c in result.contributions
        ],
    }
