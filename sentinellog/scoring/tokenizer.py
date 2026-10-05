"""Sequential template tokenizer for learned anomaly scoring.

Derives sequence vocabulary strictly from training windows and maps log events
to fixed-dimensional token IDs with explicit PAD and UNKNOWN special tokens.
Calibration and test sequences never alter or expand the vocabulary.
"""

from typing import Any, Dict, List, Optional, Sequence, Set
import torch

from sentinellog.ingestion.schemas import LogWindow, UNKNOWN_TEMPLATE_ID


PAD_TOKEN_ID = 0
UNKNOWN_TOKEN_ID = 1

PAD_TOKEN_STR = "<PAD>"
UNKNOWN_TOKEN_STR = "<UNKNOWN>"


class SequenceTokenizer:
    """Extracts integer token sequences from log windows using a frozen training vocabulary.

    Token 0 is reserved for PAD.
    Token 1 is reserved for UNKNOWN (representing template_id = -1 or unseen templates).
    Known template IDs from TRAIN are sorted and mapped to integers >= 2.
    """

    def __init__(self, max_seq_len: Optional[int] = 100):
        """Initialize tokenizer.

        Args:
            max_seq_len: Maximum sequence length. Longer sequences are deterministically
                truncated to the chronological prefix. If None, sequences are not truncated.
        """
        self.max_seq_len = max_seq_len
        self.is_fitted = False
        self.is_frozen = False

        self.template_to_id_: Dict[int, int] = {}
        self.id_to_template_: Dict[int, int] = {}
        self.known_templates_: List[int] = []

    def fit(self, windows: Sequence[LogWindow]) -> "SequenceTokenizer":
        """Fit vocabulary strictly on training windows.

        Args:
            windows: Sequence of training LogWindow instances.

        Returns:
            self
        """
        if self.is_frozen:
            raise RuntimeError("Cannot fit a frozen tokenizer.")

        seen_templates: Set[int] = set()
        for w in windows:
            seen_templates.update(w.template_ids)

        # Exclude UNKNOWN_TEMPLATE_ID (-1) from known templates
        seen_templates.discard(UNKNOWN_TEMPLATE_ID)

        # Deterministic alphabetical/numerical sorting of known templates
        self.known_templates_ = sorted(list(seen_templates))

        self.template_to_id_ = {
            UNKNOWN_TEMPLATE_ID: UNKNOWN_TOKEN_ID,
        }
        self.id_to_template_ = {
            PAD_TOKEN_ID: -999,  # Non-log sentinel
            UNKNOWN_TOKEN_ID: UNKNOWN_TEMPLATE_ID,
        }

        for idx, tid in enumerate(self.known_templates_, start=2):
            self.template_to_id_[tid] = idx
            self.id_to_template_[idx] = tid

        self.is_fitted = True
        self.is_frozen = True
        return self

    def encode_window(self, window: LogWindow) -> List[int]:
        """Convert a LogWindow template_ids sequence into integer token IDs.

        Any template not in the training vocabulary maps to UNKNOWN_TOKEN_ID (1).
        """
        if not self.is_fitted:
            raise RuntimeError("SequenceTokenizer must be fitted before encoding.")

        tokens: List[int] = []
        for tid in window.template_ids:
            token_id = self.template_to_id_.get(tid, UNKNOWN_TOKEN_ID)
            tokens.append(token_id)

        if self.max_seq_len is not None and len(tokens) > self.max_seq_len:
            # Deterministic chronological prefix truncation
            tokens = tokens[: self.max_seq_len]

        return tokens

    def encode_batch(
        self,
        windows: Sequence[LogWindow],
    ) -> Dict[str, torch.Tensor]:
        """Encode a batch of windows into padded PyTorch tensors.

        Returns:
            Dict containing:
                - 'input_ids': LongTensor of shape (batch_size, max_batch_len)
                - 'lengths': LongTensor of shape (batch_size,) with original sequence lengths
                - 'attention_mask': BoolTensor of shape (batch_size, max_batch_len) where True = valid token
        """
        encoded_list = [self.encode_window(w) for w in windows]
        lengths = [len(seq) for seq in encoded_list]
        batch_size = len(windows)
        max_len = max(lengths) if lengths else 0

        input_ids = torch.full((batch_size, max_len), PAD_TOKEN_ID, dtype=torch.long)
        attention_mask = torch.zeros((batch_size, max_len), dtype=torch.bool)

        for i, seq in enumerate(encoded_list):
            if seq:
                input_ids[i, : len(seq)] = torch.tensor(seq, dtype=torch.long)
                attention_mask[i, : len(seq)] = True

        return {
            "input_ids": input_ids,
            "lengths": torch.tensor(lengths, dtype=torch.long),
            "attention_mask": attention_mask,
        }

    @property
    def vocab_size(self) -> int:
        """Total vocabulary size including PAD and UNKNOWN."""
        if not self.is_fitted:
            raise RuntimeError("Tokenizer not fitted.")
        return len(self.id_to_template_)

    def get_metadata(self) -> Dict[str, Any]:
        """Return serializable metadata describing vocabulary and special tokens."""
        return {
            "vocab_size": self.vocab_size if self.is_fitted else 0,
            "max_seq_len": self.max_seq_len,
            "pad_token_id": PAD_TOKEN_ID,
            "unknown_token_id": UNKNOWN_TOKEN_ID,
            "known_templates_count": len(self.known_templates_),
            "known_templates": self.known_templates_,
            "template_to_id": {str(k): v for k, v in self.template_to_id_.items()},
        }
