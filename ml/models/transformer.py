"""
Transformer-encoder classifier over tabular features.

Each feature is projected to a token embedding and a learned positional
encoding is added (feature order is fixed and meaningful — e.g. column 0 is
always `duration` — unlike NLP tokens, so position matters and is not
interchangeable). Self-attention lets the model learn which feature
combinations matter jointly (e.g. high byte-count + short duration signals
a DoS burst) without hand-engineering interaction terms.
"""
import math

import torch
import torch.nn as nn


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 512):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, : x.size(1)]


class TransformerClassifier(nn.Module):
    def __init__(
        self,
        num_features: int,
        num_classes: int,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.token_embedding = nn.Linear(1, d_model)
        self.positional_encoding = PositionalEncoding(d_model, max_len=num_features)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        self.embedding_layer = nn.Sequential(
            nn.Linear(d_model, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.output_layer = nn.Linear(128, num_classes)
        self.embedding_dim = 128

    def forward(self, x: torch.Tensor, return_embedding: bool = False):
        # x: (batch, num_features) -> (batch, num_features, 1) -> (batch, num_features, d_model)
        x = x.unsqueeze(-1)
        x = self.token_embedding(x)
        x = self.positional_encoding(x)
        x = self.transformer_encoder(x)
        pooled = x.mean(dim=1)  # global average pool over the feature/token dimension
        embedding = self.embedding_layer(pooled)
        logits = self.output_layer(embedding)
        if return_embedding:
            return logits, embedding
        return logits
