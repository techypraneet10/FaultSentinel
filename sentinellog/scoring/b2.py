"""B2: Learned sequential log anomaly scorer.

Coordinates dataset tokenization, internal chronological train/validation splitting,
deterministic PyTorch training on CPU, and sequence-level nonconformity scoring.
"""

import copy
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

from sentinellog.ingestion.schemas import LogWindow
from sentinellog.scoring.b2_model import SequentialGRU
from sentinellog.scoring.tokenizer import SequenceTokenizer


class LogWindowDataset(Dataset):
    """PyTorch Dataset wrapper for LogWindow sequences."""

    def __init__(self, windows: Sequence[LogWindow], tokenizer: SequenceTokenizer):
        self.windows = list(windows)
        self.tokenizer = tokenizer

    def __len__(self) -> int:
        return len(self.windows)

    def __getitem__(self, idx: int) -> torch.Tensor:
        tokens = self.tokenizer.encode_window(self.windows[idx])
        return torch.tensor(tokens, dtype=torch.long)


def collate_fn(batch: List[torch.Tensor]) -> torch.Tensor:
    """Collate variable-length token sequences with padding."""
    return torch.nn.utils.rnn.pad_sequence(batch, batch_first=True, padding_value=0)


class B2SequentialScorer:
    """Learned sequential anomaly detector (B2) using an autoregressive GRU.

    Trained on self-supervised next-template prediction over normal workflow sequences.
    """

    def __init__(
        self,
        embedding_dim: int = 32,
        hidden_dim: int = 64,
        num_layers: int = 1,
        dropout: float = 0.1,
        learning_rate: float = 0.001,
        weight_decay: float = 1e-4,
        batch_size: int = 64,
        epochs: int = 20,
        patience: int = 3,
        max_seq_len: int = 100,
        train_normal_only: bool = True,
        val_ratio: float = 0.10,
        random_state: int = 42,
    ):
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.batch_size = batch_size
        self.epochs = epochs
        self.patience = patience
        self.max_seq_len = max_seq_len
        self.train_normal_only = train_normal_only
        self.val_ratio = val_ratio
        self.random_state = random_state

        self.tokenizer = SequenceTokenizer(max_seq_len=max_seq_len)
        self.model: Optional[SequentialGRU] = None
        self.is_fitted = False

        self.training_history_: List[Dict[str, Any]] = []
        self.best_epoch_: int = 0
        self.best_val_loss_: float = float("inf")
        self.excluded_anomalies_count_: int = 0

    def fit(self, windows: Sequence[LogWindow]) -> "B2SequentialScorer":
        """Fit tokenizer and sequential GRU strictly on training windows.

        Args:
            windows: Sequence of training LogWindow instances.

        Returns:
            self
        """
        # 1. Deterministic seeding
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)

        # 2. Fit tokenizer vocabulary strictly on all training windows
        self.tokenizer.fit(windows)

        # 3. Training subset selection (Normal-only vs All TRAIN per Section 12)
        if self.train_normal_only:
            normal_windows = [w for w in windows if not w.is_anomaly]
            self.excluded_anomalies_count_ = len(windows) - len(normal_windows)
            fit_pool = normal_windows
        else:
            self.excluded_anomalies_count_ = 0
            fit_pool = list(windows)

        if not fit_pool:
            raise ValueError("No windows available for training after filtering.")

        # 4. Internal Chronological Split (Section 17: 90% train subsplit, 10% val subsplit)
        n_total = len(fit_pool)
        n_val = max(1, int(n_total * self.val_ratio))
        n_train = n_total - n_val

        # Preserve chronological ordering: first n_train for fitting, last n_val for early stopping
        train_sub = fit_pool[:n_train]
        val_sub = fit_pool[n_train:]

        train_dataset = LogWindowDataset(train_sub, self.tokenizer)
        val_dataset = LogWindowDataset(val_sub, self.tokenizer)

        # Use deterministic single-process DataLoader on CPU
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.batch_size,
            shuffle=False,  # Chronological order within batches
            collate_fn=collate_fn,
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            collate_fn=collate_fn,
        )

        # 5. Initialize model
        self.model = SequentialGRU(
            vocab_size=self.tokenizer.vocab_size,
            embedding_dim=self.embedding_dim,
            hidden_dim=self.hidden_dim,
            num_layers=self.num_layers,
            dropout=self.dropout,
        )
        self.model.to("cpu")

        optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=self.learning_rate,
            weight_decay=self.weight_decay,
        )

        best_weights = None
        patience_counter = 0
        self.training_history_ = []

        # 6. Training loop
        for epoch in range(1, self.epochs + 1):
            self.model.train()
            train_loss_sum = 0.0
            train_batches = 0

            for batch_ids in train_loader:
                if batch_ids.size(1) < 2:
                    continue
                optimizer.zero_grad()
                loss = self.model.compute_loss(batch_ids)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()

                train_loss_sum += loss.item()
                train_batches += 1

            train_epoch_loss = train_loss_sum / max(1, train_batches)

            # Validation evaluation
            self.model.eval()
            val_loss_sum = 0.0
            val_batches = 0
            with torch.no_grad():
                for batch_ids in val_loader:
                    if batch_ids.size(1) < 2:
                        continue
                    loss = self.model.compute_loss(batch_ids)
                    val_loss_sum += loss.item()
                    val_batches += 1

            val_epoch_loss = val_loss_sum / max(1, val_batches)

            self.training_history_.append({
                "epoch": epoch,
                "train_loss": float(train_epoch_loss),
                "val_loss": float(val_epoch_loss),
            })

            # Early stopping check
            if val_epoch_loss < self.best_val_loss_:
                self.best_val_loss_ = float(val_epoch_loss)
                self.best_epoch_ = epoch
                best_weights = copy.deepcopy(self.model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= self.patience:
                    break

        if best_weights is not None:
            self.model.load_state_dict(best_weights)

        self.model.eval()
        self.is_fitted = True
        return self

    def score_window(self, window: LogWindow) -> float:
        """Compute B2 sequential anomaly score for a single window."""
        if not self.is_fitted or self.model is None:
            raise RuntimeError("B2SequentialScorer must be fitted before scoring.")

        tokens = self.tokenizer.encode_window(window)
        token_tensor = torch.tensor(tokens, dtype=torch.long, device="cpu")
        return self.model.score_sequence(token_tensor)

    def score(self, windows: Sequence[LogWindow]) -> np.ndarray:
        """Compute B2 sequential anomaly scores for a sequence of windows.

        Args:
            windows: Sequence of LogWindow instances.

        Returns:
            1D numpy array of float anomaly scores (higher = more anomalous).
        """
        return np.array([self.score_window(w) for w in windows], dtype=np.float64)

    def get_metadata(self) -> Dict[str, Any]:
        """Return serializable model configuration and training summary."""
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Scorer not fitted.")

        return {
            "baseline": "B2_SequentialGRU",
            "name": "B2SequentialScorer",
            "model_metadata": self.model.get_metadata(),
            "tokenizer_metadata": self.tokenizer.get_metadata(),
            "train_normal_only": self.train_normal_only,
            "excluded_anomalies_count": self.excluded_anomalies_count_,
            "val_ratio": self.val_ratio,
            "best_epoch": self.best_epoch_,
            "best_val_loss": self.best_val_loss_,
            "epochs_trained": len(self.training_history_),
            "random_state": self.random_state,
            "score_direction": "higher_is_more_anomalous",
        }
