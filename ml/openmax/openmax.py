"""
OpenMax (Bendale & Boult, 2016) — open-set recognition on top of any
classifier that exposes penultimate-layer activation vectors.

Core idea: closed-set softmax forces every input into one of N known
classes, even attacks the model has never seen (a zero-day gets
misclassified as whichever known attack it resembles most). OpenMax fixes
this by:
  1. For each known class, fitting a Weibull distribution to the tail of
     distances between correctly-classified training activation vectors
     and their class mean ("mean activation vector", MAV).
  2. At inference, recalibrating the logits based on how far the input's
     activation vector is from each class's MAV, redistributing some
     probability mass to a synthetic "unknown" class.
  3. If the unknown-class probability exceeds a threshold (or the
     recalibrated confidence in every known class is too low), reject the
     sample as unknown — this is what "unknown attack recall" measures.

This is pure numpy/scipy — no torch/tensorflow dependency — so it works
identically regardless of which model produced the activation vectors.
"""
from dataclasses import dataclass

import numpy as np
from scipy.stats import exponweib


@dataclass
class ClassWeibullModel:
    mean_activation_vector: np.ndarray
    weibull_params: tuple  # (a, c, loc, scale) from scipy exponweib fit


class OpenMaxRecalibrator:
    def __init__(self, tail_size: int = 20, alpha_rank: int = 3):
        """
        tail_size: number of largest distances used to fit each class's
            Weibull tail (standard OpenMax hyperparameter; smaller datasets
            need a smaller tail).
        alpha_rank: number of top classes whose logits get revised during
            recalibration (per the original paper, usually 3-10).
        """
        self.tail_size = tail_size
        self.alpha_rank = alpha_rank
        self.class_models: dict[int, ClassWeibullModel] = {}

    def fit(self, activation_vectors: np.ndarray, logits: np.ndarray, true_labels: np.ndarray) -> None:
        """
        Fit one Weibull model per known class using only CORRECTLY
        classified training samples (misclassified samples would corrupt
        the notion of "typical distance from the class center").
        """
        predicted = np.argmax(logits, axis=1)
        correct_mask = predicted == true_labels

        for class_id in np.unique(true_labels):
            class_mask = correct_mask & (true_labels == class_id)
            class_vectors = activation_vectors[class_mask]
            if len(class_vectors) < 2:
                continue  # not enough samples to fit a tail distribution

            mav = class_vectors.mean(axis=0)
            distances = np.linalg.norm(class_vectors - mav, axis=1)

            tail = np.sort(distances)[-min(self.tail_size, len(distances)):]
            try:
                params = exponweib.fit(tail, floc=0)
            except Exception:
                params = (1.0, 1.0, 0.0, float(distances.std() + 1e-6))

            self.class_models[int(class_id)] = ClassWeibullModel(mean_activation_vector=mav, weibull_params=params)

    def recalibrate(self, activation_vector: np.ndarray, logits: np.ndarray) -> tuple[np.ndarray, bool]:
        """
        Returns (recalibrated_probabilities_including_unknown, is_unknown).
        recalibrated_probabilities has length num_known_classes + 1, where
        the last entry is P(unknown).
        """
        num_classes = len(logits)
        ranked_classes = np.argsort(logits)[::-1][: self.alpha_rank]

        revised_logits = logits.copy()
        unknown_mass = 0.0

        for rank, class_id in enumerate(ranked_classes):
            model = self.class_models.get(int(class_id))
            if model is None:
                continue
            distance = np.linalg.norm(activation_vector - model.mean_activation_vector)
            a, c, loc, scale = model.weibull_params
            w_score = exponweib.cdf(distance, a, c, loc=loc, scale=scale)
            # Weight decays for lower-ranked classes (alpha-weighting from the paper)
            alpha_weight = (self.alpha_rank - rank) / self.alpha_rank
            reduction = logits[class_id] * w_score * alpha_weight
            revised_logits[class_id] -= reduction
            unknown_mass += reduction

        exp_scores = np.exp(revised_logits - np.max(revised_logits))
        exp_unknown = np.exp(unknown_mass - np.max(revised_logits))
        total = exp_scores.sum() + exp_unknown

        probs = np.concatenate([exp_scores / total, [exp_unknown / total]])
        is_unknown = bool(np.argmax(probs) == num_classes)
        return probs, is_unknown

    def save(self, path: str) -> None:
        import joblib
        joblib.dump({"tail_size": self.tail_size, "alpha_rank": self.alpha_rank, "class_models": self.class_models}, path)

    @classmethod
    def load(cls, path: str) -> "OpenMaxRecalibrator":
        import joblib
        state = joblib.load(path)
        instance = cls(tail_size=state["tail_size"], alpha_rank=state["alpha_rank"])
        instance.class_models = state["class_models"]
        return instance
