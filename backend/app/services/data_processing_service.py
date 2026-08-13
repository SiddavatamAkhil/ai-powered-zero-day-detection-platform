"""
Pure data cleaning + feature engineering logic.

Deliberately has ZERO knowledge of the database, HTTP, or the filesystem —
every method takes a DataFrame (and maybe a fitted scaler) and returns one.
This is what makes it:
  1. Unit-testable with a 10-row synthetic DataFrame, no fixtures needed.
  2. Reusable verbatim inside the Phase 3 training pipeline (same cleaning
     logic must run at train time and inference time, or you get train/serve
     skew — a classic silent bug in ML systems).
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


@dataclass
class CleaningReport:
    rows_before: int
    rows_after: int
    duplicates_dropped: int
    rows_with_inf_dropped: int
    rows_with_nan_dropped: int
    constant_columns_dropped: list[str] = field(default_factory=list)


@dataclass
class FeatureEngineeringResult:
    features: pd.DataFrame
    labels: pd.Series
    scaler: StandardScaler
    feature_columns: list[str]


class DataProcessingService:
    """
    Handles the two mechanical stages of Phase 2: cleaning and feature
    engineering. Both are static/pure — no instance state — so they can be
    called independently or composed.
    """

    @staticmethod
    def clean(df: pd.DataFrame, label_column: str) -> tuple[pd.DataFrame, CleaningReport]:
        rows_before = len(df)

        # Network traffic datasets (CIC-IDS2017, NSL-KDD, etc.) commonly
        # contain +/-inf from ratio features (e.g. bytes/sec division by
        # zero-duration flows). Treat as missing, then drop.
        df = df.replace([np.inf, -np.inf], np.nan)
        rows_with_inf_dropped = int(df.isna().any(axis=1).sum())

        rows_before_dedup = len(df)
        df = df.drop_duplicates()
        duplicates_dropped = rows_before_dedup - len(df)

        rows_before_dropna = len(df)
        df = df.dropna()
        rows_with_nan_dropped = rows_before_dropna - len(df)

        # Constant columns (zero variance) carry no signal and break
        # StandardScaler (division by zero std).
        constant_columns = [
            col for col in df.columns
            if col != label_column and df[col].nunique(dropna=False) <= 1
        ]
        df = df.drop(columns=constant_columns)

        report = CleaningReport(
            rows_before=rows_before,
            rows_after=len(df),
            duplicates_dropped=duplicates_dropped,
            rows_with_inf_dropped=rows_with_inf_dropped,
            rows_with_nan_dropped=rows_with_nan_dropped,
            constant_columns_dropped=constant_columns,
        )
        return df.reset_index(drop=True), report

    @staticmethod
    def engineer_features(
        df: pd.DataFrame,
        label_column: str,
        scaler: StandardScaler | None = None,
    ) -> FeatureEngineeringResult:
        """
        Splits label from features and applies z-score normalization.

        If `scaler` is None, fits a new one (training-time path). If a
        fitted scaler is passed in, only transforms (inference-time path,
        or applying the exact same scaling to a held-out unknown-class
        evaluation split) — this symmetry is what prevents train/serve skew.
        """
        labels = df[label_column]
        feature_df = df.drop(columns=[label_column])

        numeric_cols = feature_df.select_dtypes(include=[np.number]).columns.tolist()
        non_numeric_cols = [c for c in feature_df.columns if c not in numeric_cols]
        if non_numeric_cols:
            # Categorical columns (e.g. protocol_type) — one-hot encode
            # rather than silently dropping them.
            feature_df = pd.get_dummies(feature_df, columns=non_numeric_cols)
            numeric_cols = feature_df.columns.tolist()

        if scaler is None:
            scaler = StandardScaler()
            scaled = scaler.fit_transform(feature_df[numeric_cols])
        else:
            scaled = scaler.transform(feature_df[numeric_cols])

        scaled_df = pd.DataFrame(scaled, columns=numeric_cols, index=feature_df.index)

        return FeatureEngineeringResult(
            features=scaled_df,
            labels=labels.reset_index(drop=True),
            scaler=scaler,
            feature_columns=numeric_cols,
        )

    @staticmethod
    def profile(df: pd.DataFrame, label_column: str) -> dict:
        """Builds the document that gets written to MongoDB."""
        numeric_summary = {}
        for col in df.select_dtypes(include=[np.number]).columns:
            numeric_summary[col] = {
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "mean": float(df[col].mean()),
                "std": float(df[col].std()) if len(df) > 1 else 0.0,
            }

        return {
            "columns": df.columns.tolist(),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "missing_value_pct": (df.isna().mean() * 100).round(2).to_dict(),
            "class_distribution": df[label_column].value_counts().to_dict(),
            "numeric_summary": numeric_summary,
        }
