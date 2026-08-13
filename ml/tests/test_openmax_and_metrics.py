"""
Tests for the framework-agnostic parts of ml/: OpenMax, evaluation metrics,
and the Isolation Forest wrapper. Deliberately excludes the PyTorch model
tests (cnn.py, bilstm.py, etc.) since those require torch, which may not be
installed in every environment that runs this test suite (e.g. a
lightweight CI stage) — model architecture correctness is instead checked
via shape-assertion tests that live alongside the ml/models code once torch
is available in the target environment.
"""
import numpy as np

try:
    import pytest  # noqa: F401  (not used directly; kept so `pytest` collects this file consistently in CI)
except ImportError:
    pass

from ml.evaluation.metrics import (
    compute_closed_set_metrics,
    compute_false_positive_rate,
    compute_unknown_attack_recall,
)
from ml.models.isolation_forest import IsolationForestDetector
from ml.openmax.openmax import OpenMaxRecalibrator


class TestIsolationForestDetector:
    def test_flags_true_anomalies_more_than_normals(self):
        rng = np.random.default_rng(0)
        normal = rng.normal(0, 1, (500, 10))
        anomalies = rng.normal(6, 1, (20, 10))

        detector = IsolationForestDetector().fit(normal)
        preds_normal = detector.predict_is_anomaly(normal[:100])
        preds_anomaly = detector.predict_is_anomaly(anomalies)

        assert preds_anomaly.mean() > preds_normal.mean()

    def test_anomaly_scores_are_higher_for_true_anomalies(self):
        rng = np.random.default_rng(1)
        normal = rng.normal(0, 1, (300, 5))
        anomalies = rng.normal(8, 1, (30, 5))

        detector = IsolationForestDetector().fit(normal)
        assert detector.anomaly_scores(anomalies).mean() > detector.anomaly_scores(normal).mean()


class TestOpenMaxRecalibrator:
    def _fit_three_class_model(self, rng):
        n = 100
        embeddings, labels = [], []
        centers = [rng.normal(0, 1, 8) * 5 + c * 10 for c in range(3)]
        for c, center in enumerate(centers):
            pts = center + rng.normal(0, 1, (n, 8))
            embeddings.append(pts)
            labels.append(np.full(n, c))
        X = np.vstack(embeddings)
        y = np.concatenate(labels)

        logits = np.zeros((len(X), 3))
        for i in range(len(X)):
            for c in range(3):
                logits[i, c] = -np.linalg.norm(X[i] - centers[c])
            logits[i] -= logits[i].min()

        model = OpenMaxRecalibrator(tail_size=20, alpha_rank=3)
        model.fit(X, logits, y)
        return model, centers

    def test_known_sample_not_flagged_unknown(self):
        rng = np.random.default_rng(2)
        model, centers = self._fit_three_class_model(rng)

        sample = centers[0] + rng.normal(0, 0.5, 8)
        logits = np.array([-np.linalg.norm(sample - c) for c in centers])
        logits -= logits.min()

        _, is_unknown = model.recalibrate(sample, logits)
        assert is_unknown is False

    def test_far_out_of_distribution_sample_flagged_unknown(self):
        rng = np.random.default_rng(3)
        model, centers = self._fit_three_class_model(rng)

        far_sample = rng.normal(0, 1, 8) * 5 + 200  # nowhere near any known class center
        logits = np.array([-np.linalg.norm(far_sample - c) for c in centers])
        logits -= logits.min()

        probs, is_unknown = model.recalibrate(far_sample, logits)
        assert is_unknown is True
        assert probs[-1] == max(probs)  # unknown class carries the most probability mass


class TestEvaluationMetrics:
    def test_perfect_predictions_score_1(self):
        y_true = np.array([0, 1, 2, 0, 1, 2])
        y_pred = y_true.copy()
        metrics = compute_closed_set_metrics(y_true, y_pred)
        assert metrics["accuracy"] == 1.0
        assert metrics["f1"] == 1.0
        assert metrics["mcc"] == 1.0

    def test_false_positive_rate_only_counts_benign_misclassified(self):
        y_true = np.array([0, 0, 0, 0, 1, 1])  # 0 = benign
        y_pred = np.array([0, 1, 0, 1, 1, 1])  # 2 of 4 benign misclassified
        fpr = compute_false_positive_rate(y_true, y_pred, benign_class=0)
        assert fpr == 0.5

    def test_unknown_attack_recall_counts_correct_rejections(self):
        is_unknown_true = np.ones(10)  # all 10 samples are true zero-day attacks
        is_unknown_pred = np.array([1, 1, 1, 0, 1, 1, 0, 1, 1, 1])  # 8/10 correctly flagged
        recall = compute_unknown_attack_recall(is_unknown_true, is_unknown_pred)
        assert recall == 0.8

    def test_unknown_attack_recall_zero_when_no_true_unknowns(self):
        is_unknown_true = np.zeros(10)
        is_unknown_pred = np.ones(10)
        assert compute_unknown_attack_recall(is_unknown_true, is_unknown_pred) == 0.0
