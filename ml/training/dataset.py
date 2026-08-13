"""
PyTorch Dataset over engineered features. Training pipeline instantiates
this ONLY with rows whose class is in the dataset's `known` split — the
unknown-holdout rows are loaded separately, only at evaluation time, via
the same class with `label_encoder` reused (never refit) to guarantee
train/eval label consistency.
"""
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset


class LabelEncoder:
    """Tiny deterministic label encoder — avoids sklearn's LabelEncoder
    reordering classes differently between train/eval calls if categories
    differ, which would silently corrupt metric computation."""

    def __init__(self, class_names: list[str]):
        self.class_to_idx = {name: idx for idx, name in enumerate(sorted(class_names))}
        self.idx_to_class = {idx: name for name, idx in self.class_to_idx.items()}

    def encode(self, labels: pd.Series) -> np.ndarray:
        return labels.map(self.class_to_idx).to_numpy()

    def num_classes(self) -> int:
        return len(self.class_to_idx)


class NetworkTrafficDataset(Dataset):
    def __init__(self, features: pd.DataFrame, labels: pd.Series, label_encoder: LabelEncoder):
        self.X = torch.tensor(features.to_numpy(), dtype=torch.float32)
        self.y = torch.tensor(label_encoder.encode(labels), dtype=torch.long)

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int):
        return self.X[idx], self.y[idx]
