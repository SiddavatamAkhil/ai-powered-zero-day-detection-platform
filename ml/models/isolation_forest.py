"""
Isolation Forest — classical unsupervised anomaly baseline.

Included as the "non-deep-learning" comparison point in the model
comparison dashboard (Phase 6). Wrapped in a small class so training.py
can call `.fit_predict_scores()` identically across every model type,
deep or not.
"""
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest


class IsolationForestDetector:
    def __init__(self, n_estimators: int = 200, contamination: float = "auto", random_state: int = 42):
        self.model = IsolationForest(
            n_estimators=n_estimators, contamination=contamination, random_state=random_state, n_jobs=-1
        )

    def fit(self, X: np.ndarray) -> "IsolationForestDetector":
        self.model.fit(X)
        return self

    def anomaly_scores(self, X: np.ndarray) -> np.ndarray:
        """Higher = more anomalous (note: sklearn's raw score_samples is inverted, so we flip it)."""
        return -self.model.score_samples(X)

    def predict_is_anomaly(self, X: np.ndarray) -> np.ndarray:
        """Returns 1 for anomaly (potential unknown attack), 0 for normal."""
        raw = self.model.predict(X)  # sklearn: -1 = anomaly, 1 = normal
        return (raw == -1).astype(int)

    def save(self, path: str) -> None:
        joblib.dump(self.model, path)

    @classmethod
    def load(cls, path: str) -> "IsolationForestDetector":
        instance = cls()
        instance.model = joblib.load(path)
        return instance
