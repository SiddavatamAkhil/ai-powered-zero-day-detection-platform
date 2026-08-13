"""
Evaluation metrics for closed-set + open-set IDS performance.

Pure functions over numpy arrays — no model/framework dependency — so the
identical evaluation code runs against PyTorch, TensorFlow, or sklearn
model outputs alike, which is required to produce a fair model-comparison
table (Phase 6).
"""
import time
from dataclasses import dataclass, asdict

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)


@dataclass
class EvaluationResult:
    accuracy: float
    precision: float
    recall: float
    f1: float
    mcc: float
    roc_auc: float | None
    false_positive_rate: float
    unknown_attack_recall: float | None
    training_time_seconds: float | None = None
    inference_time_ms_per_sample: float | None = None
    memory_usage_mb: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def compute_closed_set_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_score: np.ndarray | None = None) -> dict:
    """
    y_true / y_pred: integer class labels for KNOWN classes only.
    y_score: (n_samples, n_classes) predicted probabilities, for ROC-AUC.
    """
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, average="macro", zero_division=0)
    recall = recall_score(y_true, y_pred, average="macro", zero_division=0)
    f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    mcc = matthews_corrcoef(y_true, y_pred)

    roc_auc = None
    if y_score is not None:
        try:
            roc_auc = roc_auc_score(y_true, y_score, multi_class="ovr", average="macro")
        except ValueError:
            roc_auc = None  # e.g. a class missing from this batch

    fpr = compute_false_positive_rate(y_true, y_pred, benign_class=0)

    return {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "mcc": float(mcc),
        "roc_auc": float(roc_auc) if roc_auc is not None else None,
        "false_positive_rate": float(fpr),
    }


def compute_false_positive_rate(y_true: np.ndarray, y_pred: np.ndarray, benign_class: int = 0) -> float:
    """
    FPR = benign samples incorrectly flagged as an attack / total benign samples.
    Standard IDS metric — distinct from macro-averaged multi-class recall.
    """
    benign_mask = y_true == benign_class
    if benign_mask.sum() == 0:
        return 0.0
    false_positives = np.sum((y_true == benign_class) & (y_pred != benign_class))
    return float(false_positives / benign_mask.sum())


def compute_unknown_attack_recall(is_unknown_true: np.ndarray, is_unknown_pred: np.ndarray) -> float:
    """
    Of all samples that are TRUE zero-day/unknown-class attacks (held out
    from training), what fraction did the open-set mechanism (OpenMax
    rejection or high autoencoder reconstruction error) correctly flag as
    unknown? This is THE headline open-set metric for the capstone.
    """
    true_unknown_mask = is_unknown_true == 1
    if true_unknown_mask.sum() == 0:
        return 0.0
    correctly_flagged = np.sum((is_unknown_true == 1) & (is_unknown_pred == 1))
    return float(correctly_flagged / true_unknown_mask.sum())


class Timer:
    """Context manager for wall-clock timing (training time, inference latency)."""

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed_seconds = time.perf_counter() - self.start


def measure_inference_latency_ms(predict_fn, X: np.ndarray, n_repeats: int = 20) -> float:
    """Average per-sample inference latency in milliseconds over repeated single-sample calls."""
    sample = X[:1]
    predict_fn(sample)  # warmup

    with Timer() as t:
        for _ in range(n_repeats):
            predict_fn(sample)
    return (t.elapsed_seconds / n_repeats) * 1000
