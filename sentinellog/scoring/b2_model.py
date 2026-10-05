"""PyTorch GRU sequential anomaly scoring model (B2).

Implements autoregressive next-template prediction over structured log event sequences.
Parameter count is strictly enforced to remain below 2,000,000 parameters.
"""

from typing import Any, Dict, Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

from sentinellog.scoring.tokenizer import PAD_TOKEN_ID


MAX_ALLOWED_PARAMETERS = 2_000_000


class SequentialGRU(nn.Module):
    """Lightweight GRU for sequential log template modeling and anomaly scoring.

    Trained on self-supervised next-template prediction:
        P(t_{i+1} | t_1, ..., t_i)
    """

    def __init__(
        self,
        vocab_size: int,
        embedding_dim: int = 32,
        hidden_dim: int = 64,
        num_layers: int = 1,
        dropout: float = 0.1,
    ):
        """Initialize SequentialGRU.

        Args:
            vocab_size: Total number of tokens in vocabulary.
            embedding_dim: Dimension of template embeddings.
            hidden_dim: Dimension of recurrent hidden state.
            num_layers: Number of stacked GRU layers.
            dropout: Dropout probability between recurrent layers.
        """
        super().__init__()
        self.vocab_size = vocab_size
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout_prob = dropout

        self.embedding = nn.Embedding(
            num_embeddings=vocab_size,
            embedding_dim=embedding_dim,
            padding_idx=PAD_TOKEN_ID,
        )

        self.gru = nn.GRU(
            input_size=embedding_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(hidden_dim, vocab_size)

        # Enforce Rule 6 parameter limit immediately on initialization
        total_params = self.count_parameters()
        if total_params >= MAX_ALLOWED_PARAMETERS:
            raise ValueError(
                f"Model parameter count {total_params:,} exceeds max allowed {MAX_ALLOWED_PARAMETERS:,}."
            )

    def count_parameters(self) -> int:
        """Count total trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def forward(
        self,
        input_ids: torch.Tensor,
        hidden: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Forward pass for next-token prediction logits.

        Args:
            input_ids: LongTensor of shape (batch_size, seq_len)
            hidden: Optional initial hidden state

        Returns:
            logits: FloatTensor of shape (batch_size, seq_len, vocab_size)
            hidden: Final recurrent hidden state
        """
        embeds = self.embedding(input_ids)  # (B, T, E)
        out, hidden = self.gru(embeds, hidden)  # (B, T, H)
        out = self.dropout(out)
        logits = self.head(out)  # (B, T, V)
        return logits, hidden

    def compute_loss(
        self,
        input_ids: torch.Tensor,
    ) -> torch.Tensor:
        """Compute autoregressive next-token cross-entropy loss over a batch.

        For each sequence [t_1, t_2, ..., t_L], the model predicts:
            targets = [t_2, ..., t_L]
            from inputs = [t_1, ..., t_{L-1}]

        Args:
            input_ids: LongTensor of shape (batch_size, seq_len)

        Returns:
            Scalar cross-entropy loss averaged across non-pad target tokens.
        """
        if input_ids.size(1) < 2:
            # Cannot form any transition with sequence length < 2
            return torch.tensor(0.0, device=input_ids.device, requires_grad=True)

        inputs = input_ids[:, :-1]  # (B, T-1)
        targets = input_ids[:, 1:]  # (B, T-1)

        logits, _ = self.forward(inputs)  # (B, T-1, V)

        # Compute cross entropy ignoring padding tokens in targets
        loss = F.cross_entropy(
            logits.reshape(-1, self.vocab_size),
            targets.reshape(-1),
            ignore_index=PAD_TOKEN_ID,
            reduction="mean",
        )
        return loss

    @torch.no_grad()
    def score_sequence(
        self,
        token_ids: torch.Tensor,
    ) -> float:
        """Compute window-level sequential anomaly score (mean negative log-likelihood).

        Args:
            token_ids: 1D LongTensor of token IDs for a single window.

        Returns:
            Float anomaly score (higher = less expected sequence = more anomalous).
        """
        seq_len = len(token_ids)
        if seq_len == 0:
            return 0.0

        if seq_len == 1:
            # Single event window: score using prior prediction from zero-hidden state
            dummy_input = torch.tensor([[token_ids[0]]], device=token_ids.device, dtype=torch.long)
            logits, _ = self.forward(dummy_input)
            log_probs = F.log_softmax(logits[0, 0], dim=-1)
            target_id = token_ids[0].item()
            return float(-log_probs[target_id].item())

        inputs = token_ids[:-1].unsqueeze(0)  # (1, T-1)
        targets = token_ids[1:]  # (T-1)

        logits, _ = self.forward(inputs)  # (1, T-1, V)
        log_probs = F.log_softmax(logits[0], dim=-1)  # (T-1, V)

        # Gather negative log-likelihood of each observed target token
        nll = -log_probs[torch.arange(seq_len - 1), targets]  # (T-1)
        mean_nll = torch.mean(nll).item()

        return float(mean_nll)

    def get_metadata(self) -> Dict[str, Any]:
        """Return serializable model configuration and parameter counts."""
        return {
            "model_type": "SequentialGRU",
            "vocab_size": self.vocab_size,
            "embedding_dim": self.embedding_dim,
            "hidden_dim": self.hidden_dim,
            "num_layers": self.num_layers,
            "dropout": self.dropout_prob,
            "total_parameters": self.count_parameters(),
            "trainable_parameters": self.count_parameters(),
            "max_allowed_parameters": MAX_ALLOWED_PARAMETERS,
        }
