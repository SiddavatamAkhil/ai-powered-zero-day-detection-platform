"""
Explainability service wrapping SHAP and LIME behind a common interface.

Both explain a single prediction as a list of (feature_name, contribution)
pairs so the frontend explainability page (Phase 8) can render one
consistent bar chart regardless of which method produced it. SHAP is the
default (theoretically grounded, consistent attributions via Shapley
values); LIME is offered as the faster, model-agnostic alternative for
cases where SHAP's KernelExplainer is too slow (e.g. quick interactive
what-if exploration in the dashboard).
"""
from dataclasses import dataclass

import numpy as np


@dataclass
class FeatureContribution:
    feature_name: str
    contribution: float  # signed: positive = pushes toward predicted class


@dataclass
class ExplanationResult:
    method: str  # "shap" | "lime"
    predicted_class: str
    contributions: list[FeatureContribution]
    base_value: float | None = None


class ExplainabilityService:
    def __init__(self, predict_proba_fn, feature_names: list[str], class_names: list[str], background_data: np.ndarray):
        """
        predict_proba_fn: callable(X: np.ndarray[n, num_features]) -> np.ndarray[n, num_classes]
        background_data: a representative sample of training data (SHAP
            KernelExplainer and LIME both need a reference distribution to
            perturb around — using the full training set would be
            prohibitively slow, so callers pass a small representative
            subsample, e.g. via sklearn's shap.sample or random selection).
        """
        self._predict_proba = predict_proba_fn
        self._feature_names = feature_names
        self._class_names = class_names
        self._background = background_data

    def explain_with_shap(self, sample: np.ndarray, top_k: int = 10) -> ExplanationResult:
        import shap

        explainer = shap.KernelExplainer(self._predict_proba, self._background)
        shap_values = explainer.shap_values(sample.reshape(1, -1), nsamples=100)

        proba = self._predict_proba(sample.reshape(1, -1))[0]
        predicted_idx = int(np.argmax(proba))

        # shap_values is a list of arrays (one per class) for multi-class output
        if isinstance(shap_values, list):
            class_shap = np.asarray(shap_values[predicted_idx]).squeeze()
        else:
            class_shap = np.asarray(shap_values).squeeze()

        contributions = self._top_k_contributions(class_shap, top_k)
        return ExplanationResult(
            method="shap",
            predicted_class=self._class_names[predicted_idx],
            contributions=contributions,
            base_value=float(explainer.expected_value[predicted_idx]) if isinstance(explainer.expected_value, (list, np.ndarray)) else float(explainer.expected_value),
        )

    def explain_with_lime(self, sample: np.ndarray, top_k: int = 10) -> ExplanationResult:
        from lime.lime_tabular import LimeTabularExplainer

        explainer = LimeTabularExplainer(
            self._background,
            feature_names=self._feature_names,
            class_names=self._class_names,
            mode="classification",
        )
        proba = self._predict_proba(sample.reshape(1, -1))[0]
        predicted_idx = int(np.argmax(proba))

        explanation = explainer.explain_instance(
            sample, self._predict_proba, num_features=top_k, labels=(predicted_idx,)
        )
        contributions = [
            FeatureContribution(feature_name=name, contribution=float(weight))
            for name, weight in explanation.as_list(label=predicted_idx)
        ]
        return ExplanationResult(
            method="lime",
            predicted_class=self._class_names[predicted_idx],
            contributions=contributions,
        )

    def _top_k_contributions(self, values: np.ndarray, top_k: int) -> list[FeatureContribution]:
        values_arr = np.asarray(values).squeeze()
        if values_arr.ndim > 1:
            values_arr = values_arr.flatten()
        values_arr = values_arr[: len(self._feature_names)]
        order = np.argsort(np.abs(values_arr))[::-1][:top_k]
        return [
            FeatureContribution(
                feature_name=self._feature_names[int(idx)],
                contribution=float(values_arr[int(idx)])
            )
            for idx in order
        ]
