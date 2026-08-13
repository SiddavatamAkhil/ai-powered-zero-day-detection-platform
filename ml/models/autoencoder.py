"""
Autoencoder and Variational Autoencoder for unsupervised anomaly scoring.

Unlike the supervised classifiers above, these never see labels. Trained
only on benign + known-attack traffic, high reconstruction error at
inference time is itself a zero-day/unknown-attack signal — this is
the classical anomaly-detection complement to OpenMax's classifier-based
open-set approach, and the evaluation script (Phase 3 eval) compares both.
"""
import torch
import torch.nn as nn


class Autoencoder(nn.Module):
    def __init__(self, num_features: int, latent_dim: int = 16):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(num_features, 64), nn.ReLU(),
            nn.Linear(64, 32), nn.ReLU(),
            nn.Linear(32, latent_dim),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 32), nn.ReLU(),
            nn.Linear(32, 64), nn.ReLU(),
            nn.Linear(64, num_features),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))

    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        """Per-sample MSE — used directly as an anomaly score."""
        recon = self.forward(x)
        return torch.mean((x - recon) ** 2, dim=1)


class VariationalAutoencoder(nn.Module):
    def __init__(self, num_features: int, latent_dim: int = 16):
        super().__init__()
        self.encoder_hidden = nn.Sequential(
            nn.Linear(num_features, 64), nn.ReLU(),
            nn.Linear(64, 32), nn.ReLU(),
        )
        self.fc_mu = nn.Linear(32, latent_dim)
        self.fc_logvar = nn.Linear(32, latent_dim)
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 32), nn.ReLU(),
            nn.Linear(32, 64), nn.ReLU(),
            nn.Linear(64, num_features),
        )

    def encode(self, x: torch.Tensor):
        h = self.encoder_hidden(x)
        return self.fc_mu(h), self.fc_logvar(h)

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x: torch.Tensor):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        recon = self.decoder(z)
        return recon, mu, logvar

    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        recon, _, _ = self.forward(x)
        return torch.mean((x - recon) ** 2, dim=1)

    @staticmethod
    def loss_function(recon: torch.Tensor, x: torch.Tensor, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        recon_loss = nn.functional.mse_loss(recon, x, reduction="mean")
        kl_div = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
        return recon_loss + kl_div
