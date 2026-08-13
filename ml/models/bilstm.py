"""
Bidirectional LSTM classifier.

Network flow features don't have inherent temporal order, but BiLSTM is a
standard IDS-literature baseline because flow records are often processed
as short sequences of sub-features (or literally as packet sequences in
richer datasets). Here we treat the feature vector as a length-N sequence
of scalars so the same architecture generalizes to genuinely sequential
inputs (e.g. per-packet features) later without an interface change.
"""
import torch
import torch.nn as nn


class BiLSTMClassifier(nn.Module):
    def __init__(self, num_features: int, num_classes: int, hidden_size: int = 64, num_layers: int = 2, dropout: float = 0.3):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=1,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.embedding_layer = nn.Sequential(
            nn.Linear(hidden_size * 2, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.output_layer = nn.Linear(128, num_classes)
        self.embedding_dim = 128

    def forward(self, x: torch.Tensor, return_embedding: bool = False):
        # x: (batch, num_features) -> (batch, num_features, 1)
        x = x.unsqueeze(-1)
        lstm_out, (h_n, _) = self.lstm(x)
        # Concat final forward + backward hidden states
        final_hidden = torch.cat([h_n[-2], h_n[-1]], dim=1)
        embedding = self.embedding_layer(final_hidden)
        logits = self.output_layer(embedding)
        if return_embedding:
            return logits, embedding
        return logits
