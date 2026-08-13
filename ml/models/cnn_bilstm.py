"""
CNN-BiLSTM hybrid: CNN extracts local feature patterns, BiLSTM models
dependencies across the resulting feature map. This is one of the
strongest-performing architectures in recent zero-day/IDS literature
(the combination consistently beats either component alone in the
capstone survey's comparison tables) because it captures both local
(convolutional) and sequential (recurrent) structure.
"""
import torch
import torch.nn as nn


class CNNBiLSTMHybrid(nn.Module):
    def __init__(self, num_features: int, num_classes: int, dropout: float = 0.3):
        super().__init__()
        self.conv_block = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(2),
        )
        # After one pool, sequence length is num_features // 2, channels = 32.
        # LSTM consumes this as a sequence of 32-dim vectors.
        self.lstm = nn.LSTM(
            input_size=32,
            hidden_size=64,
            num_layers=1,
            batch_first=True,
            bidirectional=True,
        )
        self.embedding_layer = nn.Sequential(
            nn.Linear(64 * 2, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.output_layer = nn.Linear(128, num_classes)
        self.embedding_dim = 128

    def forward(self, x: torch.Tensor, return_embedding: bool = False):
        x = x.unsqueeze(1)                     # (batch, 1, num_features)
        x = self.conv_block(x)                 # (batch, 32, num_features//2)
        x = x.permute(0, 2, 1)                  # (batch, seq_len, 32) for LSTM
        _, (h_n, _) = self.lstm(x)
        final_hidden = torch.cat([h_n[-2], h_n[-1]], dim=1)
        embedding = self.embedding_layer(final_hidden)
        logits = self.output_layer(embedding)
        if return_embedding:
            return logits, embedding
        return logits
