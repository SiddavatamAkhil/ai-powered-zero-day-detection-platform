"""
Unit tests for DataProcessingService. Uses tiny synthetic DataFrames only —
no file I/O, no DB, no fixtures — proving the cleaning/feature-engineering
logic is correct in isolation, independent of Postgres/Mongo wiring.
"""
import numpy as np
import pandas as pd
import pytest

from app.services.data_processing_service import DataProcessingService


def make_raw_df() -> pd.DataFrame:
    return pd.DataFrame({
        "duration": [1.0, 2.0, 2.0, np.inf, 5.0, 6.0],
        "protocol_type": ["tcp", "udp", "udp", "tcp", "tcp", "tcp"],
        "constant_col": [1, 1, 1, 1, 1, 1],
        "bytes_sent": [100, 200, 200, 400, np.nan, 600],
        "label": ["benign", "dos", "dos", "benign", "probe", "benign"],
    })


class TestClean:
    def test_drops_duplicate_rows(self):
        df = make_raw_df()
        cleaned, report = DataProcessingService.clean(df, label_column="label")
        # row index 1 and 2 are exact duplicates
        assert report.duplicates_dropped >= 1
        assert len(cleaned) < len(df)

    def test_drops_rows_with_inf_and_nan(self):
        df = make_raw_df()
        cleaned, report = DataProcessingService.clean(df, label_column="label")
        assert not np.isinf(cleaned.select_dtypes(include=[np.number])).any().any()
        assert not cleaned.isna().any().any()

    def test_drops_constant_columns_but_keeps_label(self):
        df = make_raw_df()
        cleaned, report = DataProcessingService.clean(df, label_column="label")
        assert "constant_col" in report.constant_columns_dropped
        assert "constant_col" not in cleaned.columns
        assert "label" in cleaned.columns

    def test_never_drops_label_column_even_if_constant(self):
        df = pd.DataFrame({"x": [1, 2, 3], "label": ["benign", "benign", "benign"]})
        cleaned, report = DataProcessingService.clean(df, label_column="label")
        assert "label" in cleaned.columns
        assert "label" not in report.constant_columns_dropped


class TestFeatureEngineering:
    def test_one_hot_encodes_categorical_columns(self):
        df = pd.DataFrame({
            "protocol_type": ["tcp", "udp", "tcp"],
            "bytes_sent": [100, 200, 300],
            "label": ["benign", "dos", "benign"],
        })
        result = DataProcessingService.engineer_features(df, label_column="label")
        assert any(c.startswith("protocol_type_") for c in result.feature_columns)

    def test_scales_numeric_features_to_zero_mean(self):
        df = pd.DataFrame({
            "bytes_sent": [100, 200, 300, 400],
            "label": ["benign", "dos", "benign", "probe"],
        })
        result = DataProcessingService.engineer_features(df, label_column="label")
        assert abs(result.features["bytes_sent"].mean()) < 1e-6

    def test_reusing_fitted_scaler_produces_consistent_transform(self):
        """
        Critical for open-set eval: the held-out unknown-class split must be
        scaled with the SAME fitted scaler as the known-class training data,
        never refit — otherwise the two aren't in the same feature space.
        """
        train_df = pd.DataFrame({"bytes_sent": [100, 200, 300, 400], "label": ["benign"] * 4})
        train_result = DataProcessingService.engineer_features(train_df, label_column="label")

        unseen_df = pd.DataFrame({"bytes_sent": [150, 250], "label": ["unknown_attack"] * 2})
        unseen_result = DataProcessingService.engineer_features(
            unseen_df, label_column="label", scaler=train_result.scaler
        )
        # 150 is exactly halfway between 100 and 200 in the training scale
        expected_midpoint = (train_result.features["bytes_sent"][0] + train_result.features["bytes_sent"][1]) / 2
        assert abs(unseen_result.features["bytes_sent"][0] - expected_midpoint) < 1e-6


class TestProfile:
    def test_profile_reports_class_distribution(self):
        df = make_raw_df()
        profile = DataProcessingService.profile(df, label_column="label")
        assert profile["class_distribution"]["benign"] == 3
        assert profile["class_distribution"]["dos"] == 2

    def test_profile_reports_missing_value_percentage(self):
        df = make_raw_df()
        profile = DataProcessingService.profile(df, label_column="label")
        assert profile["missing_value_pct"]["bytes_sent"] > 0
