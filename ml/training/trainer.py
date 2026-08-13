"""
Unified training loop. One function trains any of CNN / BiLSTM /
CNN-BiLSTM / Transformer against the SAME data pipeline, so the model
comparison table (Phase 6) is a fair comparison — identical splits,
identical epochs/batch size unless explicitly varied, identical metrics
computed the same way.

Autoencoder/VAE use a separate unsupervised loop (train_autoencoder) since
they don't take labels as input.
"""
import time

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from ml.evaluation.metrics import Timer
from ml.models.autoencoder import Autoencoder, VariationalAutoencoder
from ml.models.bilstm import BiLSTMClassifier
from ml.models.cnn import CNNClassifier
from ml.models.cnn_bilstm import CNNBiLSTMHybrid
from ml.models.transformer import TransformerClassifier
from ml.training.dataset import NetworkTrafficDataset

MODEL_REGISTRY = {
    "cnn": CNNClassifier,
    "bilstm": BiLSTMClassifier,
    "cnn_bilstm": CNNBiLSTMHybrid,
    "transformer": TransformerClassifier,
}


def build_model(architecture: str, num_features: int, num_classes: int) -> nn.Module:
    if architecture not in MODEL_REGISTRY:
        raise ValueError(f"Unknown architecture '{architecture}'. Choose from {list(MODEL_REGISTRY)}.")
    return MODEL_REGISTRY[architecture](num_features=num_features, num_classes=num_classes)


def train_classifier(
    architecture: str,
    train_dataset: NetworkTrafficDataset,
    val_dataset: NetworkTrafficDataset,
    num_features: int,
    num_classes: int,
    epochs: int = 20,
    batch_size: int = 128,
    lr: float = 1e-3,
    device: str = "cpu",
    progress_callback=None,
) -> dict:
    """
    Returns a dict with the trained model, training curves, activation
    vectors + logits on the training set (needed by OpenMax.fit), and
    timing/memory stats for the evaluation table.
    """
    model = build_model(architecture, num_features, num_classes).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    history = {"train_loss": [], "val_loss": [], "val_accuracy": []}

    with Timer() as training_timer:
        for epoch in range(epochs):
            model.train()
            epoch_loss = 0.0
            for X_batch, y_batch in train_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                optimizer.zero_grad()
                logits = model(X_batch)
                loss = criterion(logits, y_batch)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item() * len(X_batch)

            avg_train_loss = epoch_loss / len(train_dataset)

            model.eval()
            val_loss, correct = 0.0, 0
            with torch.no_grad():
                for X_batch, y_batch in val_loader:
                    X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                    logits = model(X_batch)
                    val_loss += criterion(logits, y_batch).item() * len(X_batch)
                    correct += (logits.argmax(dim=1) == y_batch).sum().item()

            avg_val_loss = val_loss / len(val_dataset)
            val_accuracy = correct / len(val_dataset)

            history["train_loss"].append(avg_train_loss)
            history["val_loss"].append(avg_val_loss)
            history["val_accuracy"].append(val_accuracy)

            if progress_callback:
                progress_callback(epoch + 1, epochs, avg_train_loss, avg_val_loss, val_accuracy)

    # Collect activation vectors + logits over the FULL training set for OpenMax fitting
    model.eval()
    all_embeddings, all_logits, all_labels = [], [], []
    with torch.no_grad():
        for X_batch, y_batch in DataLoader(train_dataset, batch_size=batch_size, shuffle=False):
            logits, embedding = model(X_batch.to(device), return_embedding=True)
            all_embeddings.append(embedding.cpu().numpy())
            all_logits.append(logits.cpu().numpy())
            all_labels.append(y_batch.numpy())

    return {
        "model": model,
        "history": history,
        "training_time_seconds": training_timer.elapsed_seconds,
        "train_embeddings": np.concatenate(all_embeddings),
        "train_logits": np.concatenate(all_logits),
        "train_labels": np.concatenate(all_labels),
    }


def train_autoencoder(
    architecture: str,  # "autoencoder" | "vae"
    train_dataset: NetworkTrafficDataset,
    num_features: int,
    epochs: int = 20,
    batch_size: int = 128,
    lr: float = 1e-3,
    device: str = "cpu",
) -> dict:
    is_vae = architecture == "vae"
    model = (VariationalAutoencoder if is_vae else Autoencoder)(num_features=num_features).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    history = {"loss": []}
    with Timer() as training_timer:
        for epoch in range(epochs):
            model.train()
            epoch_loss = 0.0
            for X_batch, _ in loader:
                X_batch = X_batch.to(device)
                optimizer.zero_grad()
                if is_vae:
                    recon, mu, logvar = model(X_batch)
                    loss = model.loss_function(recon, X_batch, mu, logvar)
                else:
                    recon = model(X_batch)
                    loss = nn.functional.mse_loss(recon, X_batch)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item() * len(X_batch)
            history["loss"].append(epoch_loss / len(train_dataset))

    return {"model": model, "history": history, "training_time_seconds": training_timer.elapsed_seconds}
