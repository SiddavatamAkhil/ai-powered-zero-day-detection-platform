"""
Training orchestration service. Bridges the persistence layer (Postgres
via repositories) and the framework-agnostic `ml/` package.

IMPORTANT FIX (post-review): the original version of this file called
train_classifier() unconditionally for every architecture, including
"autoencoder", "vae", and "isolation_forest" — which would crash, since
those aren't supervised classifiers and don't fit train_classifier's
signature or evaluation logic (no logits, no OpenMax activation vectors).
This version branches by model family:
  - SUPERVISED_ARCHITECTURES (cnn/bilstm/cnn_bilstm/transformer): trained
    with train_classifier(), evaluated with OpenMax + closed-set metrics.
  - ANOMALY_ARCHITECTURES (autoencoder/vae): trained unsupervised on known
    traffic only, evaluated by reconstruction-error threshold instead of
    OpenMax (there's no classifier logits to recalibrate).
  - isolation_forest: trained on known traffic, evaluated via its own
    anomaly score threshold — same idea as the autoencoder path, different
    underlying model.

Training runs synchronously inside a FastAPI BackgroundTask (not the
request/response cycle itself) — acceptable for a capstone-scale dataset;
a production system at real IDS data volumes would hand this off to a
Celery/RQ worker instead, using the identical `ml/` functions untouched.
"""
import os
import sys
import uuid

ML_PACKAGE_PARENT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if ML_PACKAGE_PARENT not in sys.path:
    sys.path.insert(0, ML_PACKAGE_PARENT)

from app.core.config import settings
from app.models.dataset import Dataset
from app.models.ml_model import MLModel, ModelArchitecture, TrainingRun, TrainingStatus
from app.repositories.dataset_repository import AbstractDatasetRepository
from app.repositories.ml_model_repository import AbstractMLModelRepository
from app.schemas.ml_model import TrainingRequest

SUPERVISED_ARCHITECTURES = {
    ModelArchitecture.CNN, ModelArchitecture.BILSTM,
    ModelArchitecture.CNN_BILSTM, ModelArchitecture.TRANSFORMER,
}
ANOMALY_ARCHITECTURES = {ModelArchitecture.AUTOENCODER, ModelArchitecture.VAE}


class TrainingError(Exception):
    pass


class TrainingService:
    def __init__(self, model_repo: AbstractMLModelRepository, dataset_repo: AbstractDatasetRepository):
        self._model_repo = model_repo
        self._dataset_repo = dataset_repo

    async def queue_training_run(self, request: TrainingRequest, triggered_by: uuid.UUID) -> TrainingRun:
        dataset = await self._dataset_repo.get_by_id(request.dataset_id)
        if dataset is None:
            raise TrainingError("Dataset not found.")
        if not dataset.features_path:
            raise TrainingError("Dataset must complete feature engineering before training.")

        run = TrainingRun(
            dataset_id=request.dataset_id,
            architecture=request.architecture,
            status=TrainingStatus.QUEUED,
            hyperparameters={
                "epochs": request.epochs,
                "batch_size": request.batch_size,
                "learning_rate": request.learning_rate,
                "seed": request.seed,
            },
            triggered_by=triggered_by,
        )
        return await self._model_repo.create_training_run(run)

    async def get_training_run(self, run_id: uuid.UUID) -> TrainingRun | None:
        return await self._model_repo.get_training_run(run_id)

    async def list_models_for_dataset(self, dataset_id: uuid.UUID) -> list[MLModel]:
        return await self._model_repo.list_models_for_dataset_training_runs(dataset_id)

    async def get_model_by_id(self, model_id: uuid.UUID) -> MLModel | None:
        return await self._model_repo.get_model_by_id(model_id)

    async def execute_training_run(self, run_id: uuid.UUID) -> None:
        """
        Called from a BackgroundTask. Any exception is caught and recorded
        on the run (never silently swallowed, never crashes the worker).
        """
        run = await self._model_repo.get_training_run(run_id)
        if run is None:
            return

        await self._model_repo.update_training_status(run_id, TrainingStatus.RUNNING)
        try:
            dataset = await self._dataset_repo.get_by_id(run.dataset_id)
            known_classes = await self._dataset_repo.get_known_classes(run.dataset_id)
            unknown_classes = await self._dataset_repo.get_unknown_classes(run.dataset_id)

            if run.architecture in SUPERVISED_ARCHITECTURES:
                result = await self._run_supervised_pipeline(dataset, run, known_classes, unknown_classes)
            elif run.architecture in ANOMALY_ARCHITECTURES:
                result = await self._run_anomaly_pipeline(dataset, run, known_classes, unknown_classes)
            elif run.architecture == ModelArchitecture.ISOLATION_FOREST:
                result = await self._run_isolation_forest_pipeline(dataset, run, known_classes, unknown_classes)
            else:
                raise TrainingError(f"Unsupported architecture: {run.architecture}")

            model = MLModel(
                training_run_id=run.id,
                architecture=run.architecture,
                artifact_path=result["artifact_path"],
                openmax_path=result.get("openmax_path"),
                background_data_path=result.get("background_data_path"),
                feature_names=result.get("feature_names"),
                class_names=result.get("class_names"),
                num_features=result["num_features"],
                num_classes=result.get("num_classes"),
                **result["metrics"],
            )
            await self._model_repo.save_model(model)
            await self._model_repo.update_training_status(run_id, TrainingStatus.COMPLETED)
        except Exception as exc:  # noqa: BLE001 - intentionally broad; recorded, not swallowed
            await self._model_repo.update_training_status(run_id, TrainingStatus.FAILED, error_message=str(exc))

    # ------------------------------------------------------------------
    # Supervised classifiers: CNN / BiLSTM / CNN-BiLSTM / Transformer
    # ------------------------------------------------------------------
    async def _run_supervised_pipeline(self, dataset: Dataset, run: TrainingRun, known_classes: list[str], unknown_classes: list[str]) -> dict:
        import numpy as np
        import pandas as pd
        import torch
        from sklearn.model_selection import train_test_split

        from ml.evaluation.metrics import compute_closed_set_metrics, compute_unknown_attack_recall, measure_inference_latency_ms
        from ml.openmax.openmax import OpenMaxRecalibrator
        from ml.training.dataset import LabelEncoder, NetworkTrafficDataset
        from ml.training.trainer import train_classifier

        seed = run.hyperparameters.get("seed", 42)
        torch.manual_seed(seed)
        np.random.seed(seed)

        df = pd.read_parquet(dataset.features_path)
        label_col = dataset.label_column

        known_df = df[df[label_col].isin(known_classes)].reset_index(drop=True)
        unknown_df = df[df[label_col].isin(unknown_classes)].reset_index(drop=True) if unknown_classes else None

        label_encoder = LabelEncoder(known_classes)
        train_df, val_df = train_test_split(known_df, test_size=0.2, random_state=seed, stratify=known_df[label_col])

        train_dataset = NetworkTrafficDataset(train_df.drop(columns=[label_col]), train_df[label_col], label_encoder)
        val_dataset = NetworkTrafficDataset(val_df.drop(columns=[label_col]), val_df[label_col], label_encoder)

        num_features = df.shape[1] - 1
        num_classes = label_encoder.num_classes()

        train_result = train_classifier(
            architecture=run.architecture.value,
            train_dataset=train_dataset,
            val_dataset=val_dataset,
            num_features=num_features,
            num_classes=num_classes,
            epochs=run.hyperparameters.get("epochs", 20),
            batch_size=run.hyperparameters.get("batch_size", 128),
            lr=run.hyperparameters.get("learning_rate", 1e-3),
        )
        model = train_result["model"]

        openmax = OpenMaxRecalibrator()
        openmax.fit(train_result["train_embeddings"], train_result["train_logits"], train_result["train_labels"])

        model.eval()
        with torch.no_grad():
            val_X = torch.tensor(val_df.drop(columns=[label_col]).to_numpy(), dtype=torch.float32)
            val_logits, val_embeddings = model(val_X, return_embedding=True)
            val_probs = torch.softmax(val_logits, dim=1).numpy()
            val_pred = val_probs.argmax(axis=1)
        val_true = label_encoder.encode(val_df[label_col])
        closed_metrics = compute_closed_set_metrics(val_true, val_pred, val_probs)

        unknown_recall = None
        if unknown_df is not None and len(unknown_df) > 0:
            with torch.no_grad():
                unk_X = torch.tensor(unknown_df.drop(columns=[label_col]).to_numpy(), dtype=torch.float32)
                unk_logits, unk_embeddings = model(unk_X, return_embedding=True)
            is_unknown_pred = np.array([
                openmax.recalibrate(unk_embeddings[i].numpy(), unk_logits[i].numpy())[1]
                for i in range(len(unk_embeddings))
            ]).astype(int)
            is_unknown_true = np.ones(len(unknown_df), dtype=int)
            unknown_recall = compute_unknown_attack_recall(is_unknown_true, is_unknown_pred)

        def _predict_one(x: np.ndarray):
            with torch.no_grad():
                return model(torch.tensor(x, dtype=torch.float32))
        inference_ms = measure_inference_latency_ms(_predict_one, val_X.numpy())

        artifact_path = os.path.join(settings.MODEL_ARTIFACT_DIR, f"{run.id}_{run.architecture.value}.pt")
        os.makedirs(settings.MODEL_ARTIFACT_DIR, exist_ok=True)
        torch.save(model.state_dict(), artifact_path)

        openmax_path = os.path.join(settings.MODEL_ARTIFACT_DIR, f"{run.id}_openmax.joblib")
        openmax.save(openmax_path)

        # Persist a small background/reference sample from TRAINING data —
        # SHAP's KernelExplainer and LIME's tabular explainer both need a
        # reference distribution to perturb around at explanation time.
        # Using training data (not validation/unknown data) avoids leaking
        # eval-set information into every future explanation call.
        background_sample = train_df.drop(columns=[label_col]).sample(
            n=min(100, len(train_df)), random_state=seed
        ).to_numpy()
        background_path = os.path.join(settings.MODEL_ARTIFACT_DIR, f"{run.id}_background.npy")
        np.save(background_path, background_sample)

        feature_names = train_df.drop(columns=[label_col]).columns.tolist()
        class_names = [label_encoder.idx_to_class[i] for i in range(num_classes)]

        return {
            "artifact_path": artifact_path,
            "openmax_path": openmax_path,
            "background_data_path": background_path,
            "feature_names": feature_names,
            "class_names": class_names,
            "num_features": num_features,
            "num_classes": num_classes,
            "metrics": {
                **closed_metrics,
                "unknown_attack_recall": unknown_recall,
                "training_time_seconds": train_result["training_time_seconds"],
                "inference_time_ms_per_sample": inference_ms,
                "memory_usage_mb": None,
            },
        }

    # ------------------------------------------------------------------
    # Anomaly-based: Autoencoder / VAE — no OpenMax; reconstruction-error
    # threshold (99th percentile on KNOWN training data) is the open-set
    # decision rule instead.
    # ------------------------------------------------------------------
    async def _run_anomaly_pipeline(self, dataset: Dataset, run: TrainingRun, known_classes: list[str], unknown_classes: list[str]) -> dict:
        import numpy as np
        import pandas as pd
        import torch
        from sklearn.model_selection import train_test_split

        from ml.evaluation.metrics import compute_unknown_attack_recall, measure_inference_latency_ms
        from ml.training.dataset import LabelEncoder, NetworkTrafficDataset
        from ml.training.trainer import train_autoencoder

        seed = run.hyperparameters.get("seed", 42)
        torch.manual_seed(seed)
        np.random.seed(seed)

        df = pd.read_parquet(dataset.features_path)
        label_col = dataset.label_column

        known_df = df[df[label_col].isin(known_classes)].reset_index(drop=True)
        unknown_df = df[df[label_col].isin(unknown_classes)].reset_index(drop=True) if unknown_classes else None

        label_encoder = LabelEncoder(known_classes)
        train_df, val_df = train_test_split(known_df, test_size=0.2, random_state=seed)

        train_dataset = NetworkTrafficDataset(train_df.drop(columns=[label_col]), train_df[label_col], label_encoder)
        num_features = df.shape[1] - 1

        train_result = train_autoencoder(
            architecture="vae" if run.architecture == ModelArchitecture.VAE else "autoencoder",
            train_dataset=train_dataset,
            num_features=num_features,
            epochs=run.hyperparameters.get("epochs", 20),
            batch_size=run.hyperparameters.get("batch_size", 128),
            lr=run.hyperparameters.get("learning_rate", 1e-3),
        )
        model = train_result["model"]
        model.eval()

        # Threshold: 99th percentile of reconstruction error on KNOWN
        # training data — anything above this on unseen data is flagged.
        with torch.no_grad():
            train_X = torch.tensor(train_df.drop(columns=[label_col]).to_numpy(), dtype=torch.float32)
            train_errors = model.reconstruction_error(train_X).numpy()
        threshold = float(np.percentile(train_errors, 99))

        with torch.no_grad():
            val_X = torch.tensor(val_df.drop(columns=[label_col]).to_numpy(), dtype=torch.float32)
            val_errors = model.reconstruction_error(val_X).numpy()
        false_positive_rate = float((val_errors > threshold).mean())  # known val flagged as anomaly = false alarm

        unknown_recall = None
        if unknown_df is not None and len(unknown_df) > 0:
            with torch.no_grad():
                unk_X = torch.tensor(unknown_df.drop(columns=[label_col]).to_numpy(), dtype=torch.float32)
                unk_errors = model.reconstruction_error(unk_X).numpy()
            is_unknown_pred = (unk_errors > threshold).astype(int)
            is_unknown_true = np.ones(len(unknown_df), dtype=int)
            unknown_recall = compute_unknown_attack_recall(is_unknown_true, is_unknown_pred)

        def _predict_one(x: np.ndarray):
            with torch.no_grad():
                return model.reconstruction_error(torch.tensor(x, dtype=torch.float32))
        inference_ms = measure_inference_latency_ms(_predict_one, val_X.numpy())

        artifact_path = os.path.join(settings.MODEL_ARTIFACT_DIR, f"{run.id}_{run.architecture.value}.pt")
        os.makedirs(settings.MODEL_ARTIFACT_DIR, exist_ok=True)
        torch.save({"state_dict": model.state_dict(), "threshold": threshold}, artifact_path)

        return {
            "artifact_path": artifact_path,
            "openmax_path": None,
            "num_features": num_features,
            "num_classes": None,
            "metrics": {
                "accuracy": None, "precision": None, "recall": None, "f1": None, "mcc": None, "roc_auc": None,
                "false_positive_rate": false_positive_rate,
                "unknown_attack_recall": unknown_recall,
                "training_time_seconds": train_result["training_time_seconds"],
                "inference_time_ms_per_sample": inference_ms,
                "memory_usage_mb": None,
            },
        }

    # ------------------------------------------------------------------
    # Isolation Forest — same anomaly-threshold idea, sklearn model.
    # ------------------------------------------------------------------
    async def _run_isolation_forest_pipeline(self, dataset: Dataset, run: TrainingRun, known_classes: list[str], unknown_classes: list[str]) -> dict:
        import numpy as np
        import pandas as pd
        from sklearn.model_selection import train_test_split

        from ml.evaluation.metrics import Timer, compute_unknown_attack_recall, measure_inference_latency_ms
        from ml.models.isolation_forest import IsolationForestDetector

        df = pd.read_parquet(dataset.features_path)
        label_col = dataset.label_column

        known_df = df[df[label_col].isin(known_classes)].reset_index(drop=True)
        unknown_df = df[df[label_col].isin(unknown_classes)].reset_index(drop=True) if unknown_classes else None

        seed = run.hyperparameters.get("seed", 42)
        train_df, val_df = train_test_split(known_df, test_size=0.2, random_state=seed)

        train_X = train_df.drop(columns=[label_col]).to_numpy()
        val_X = val_df.drop(columns=[label_col]).to_numpy()
        num_features = train_X.shape[1]

        detector = IsolationForestDetector(random_state=seed)
        with Timer() as t:
            detector.fit(train_X)

        val_pred = detector.predict_is_anomaly(val_X)
        false_positive_rate = float(val_pred.mean())  # known val flagged as anomaly = false alarm

        unknown_recall = None
        if unknown_df is not None and len(unknown_df) > 0:
            unk_X = unknown_df.drop(columns=[label_col]).to_numpy()
            is_unknown_pred = detector.predict_is_anomaly(unk_X)
            is_unknown_true = np.ones(len(unknown_df), dtype=int)
            unknown_recall = compute_unknown_attack_recall(is_unknown_true, is_unknown_pred)

        inference_ms = measure_inference_latency_ms(detector.predict_is_anomaly, val_X)

        artifact_path = os.path.join(settings.MODEL_ARTIFACT_DIR, f"{run.id}_isolation_forest.joblib")
        os.makedirs(settings.MODEL_ARTIFACT_DIR, exist_ok=True)
        detector.save(artifact_path)

        return {
            "artifact_path": artifact_path,
            "openmax_path": None,
            "num_features": num_features,
            "num_classes": None,
            "metrics": {
                "accuracy": None, "precision": None, "recall": None, "f1": None, "mcc": None, "roc_auc": None,
                "false_positive_rate": false_positive_rate,
                "unknown_attack_recall": unknown_recall,
                "training_time_seconds": t.elapsed_seconds,
                "inference_time_ms_per_sample": inference_ms,
                "memory_usage_mb": None,
            },
        }
