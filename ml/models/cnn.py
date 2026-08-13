"""
1D-CNN over tabular network-flow features.

Treats the feature vector as a 1D signal (Conv1d over feature dimension) —
a standard approach in IDS literature for capturing local feature
interactions (e.g. adjacent byte-count / packet-count features) without
assuming spatial structure like an image CNN would.

`return_embedding=True` exposes the penultimate-layer activation vector,
which OpenMax (ml/openmax/openmax.py) needs to fit per-class Weibull models —
OpenMax operates on activation vectors, not raw logits.
"""
import torch
import torch.nn as nn


class CNNClassifier(nn.Module):
    def __init__(self, num_features: int, num_classes: int, dropout: float = 0.3):
        super().__init__()
        self.conv_block = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(2),
        )
        flattened_size = 64 * (num_features // 4)
        self.embedding_layer = nn.Sequential(
            nn.Flatten(),
            nn.Linear(flattened_size, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.output_layer = nn.Linear(128, num_classes)
        self.embedding_dim = 128

    def forward(self, x: torch.Tensor, return_embedding: bool = False):
        x = x.unsqueeze(1)  # (batch, num_features) -> (batch, 1, num_features)
        x = self.conv_block(x)
        embedding = self.embedding_layer(x)
        logits = self.output_layer(embedding)
        if return_embedding:
            return logits, embedding
        return logits
