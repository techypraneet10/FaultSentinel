"""Baseline loader and scoring adapter for Phase 12 evaluation.

Supports:
- B0: Frequency / Surprisal Scorer
- B1 PCA: Reconstruction Error Scorer
- B1 Isolation Forest: Anomaly Scorer
- B2: Autoregressive Sequential GRU Scorer
- B3: LLM-every-window adapter (all windows escalated)

All baseline thresholds are frozen from Phase 3 and Phase 4 calibration splits.
Zero threshold tuning or refitting is performed on the test set.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import torch

from sentinellog.ingestion.schemas import LogWindow
from sentinellog.scoring.artifacts import load_model_artifact
from sentinellog.scoring.b0 import FrequencyScorer
from sentinellog.scoring.b1 import IsolationForestScorer, PCAScorer
from sentinellog.scoring.b2 import B2SequentialScorer
from sentinellog.scoring.b2_model import SequentialGRU
from sentinellog.scoring.tokenizer import SequenceTokenizer


FROZEN_CALIB_THRESHOLDS = {
    "hdfs": {
        "b0": 1.577379,
        "b1_pca": 0.0,
        "b1_iforest": 0.435372,
        "b2_alpha_0_01": 1.6723480224609375,
        "b2_alpha_0_05": 1.1545928716659546,
        "b2_alpha_0_10": 0.9765617847442627,
        "b2_alpha_0_20": 0.9460925459861755,
    },
    "bgl": {
        "b0": 8.113998,
        "b1_pca": 0.666416,
        "b1_iforest": 0.419321,
        "b2_alpha_0_01": 3.0237722396850586,
        "b2_alpha_0_05": 2.5946779251098633,
        "b2_alpha_0_10": 2.5946779251098633,
        "b2_alpha_0_20": 0.060652121901512146,
    },
}


def load_b2_scorer(
    dataset: str,
    train_windows: List[LogWindow],
    checkpoint_path: Optional[str] = None,
) -> B2SequentialScorer:
    """Load and reconstruct fitted B2 Sequential GRU scorer."""
    if checkpoint_path is None:
        checkpoint_path = f"results/phase4/{dataset}/b2_model.pt"

    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"B2 model checkpoint not found: {checkpoint_path}")

    ckpt = torch.load(checkpoint_path, map_location="cpu")
    meta = ckpt["model_metadata"]

    tok = SequenceTokenizer(max_seq_len=100)
    tok.fit(train_windows)

    model = SequentialGRU(
        vocab_size=meta["vocab_size"],
        embedding_dim=meta["embedding_dim"],
        hidden_dim=meta["hidden_dim"],
        num_layers=meta["num_layers"],
        dropout=meta["dropout"],
    )
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    scorer = B2SequentialScorer()
    scorer.model = model
    scorer.tokenizer = tok
    scorer.is_fitted = True
    return scorer


def load_all_baseline_scorers(
    dataset: str,
    train_windows: List[LogWindow],
    results_root: str = "results",
) -> Dict[str, Any]:
    """Load all fitted baseline models and their frozen calibration thresholds.

    Args:
        dataset: Dataset name ('hdfs' or 'bgl').
        train_windows: Training windows (used strictly to fit tokenizer vocabulary).
        results_root: Root directory of previous phase artifacts.

    Returns:
        Dict of scorers and frozen thresholds.
    """
    b0_path = os.path.join(results_root, "phase3", dataset, "b0", "model.joblib")
    b1_pca_path = os.path.join(results_root, "phase3", dataset, "b1_pca", "model.joblib")
    b1_iforest_path = os.path.join(results_root, "phase3", dataset, "b1_iforest", "model.joblib")
    b2_ckpt_path = os.path.join(results_root, "phase4", dataset, "b2_model.pt")

    b0_scorer: FrequencyScorer = load_model_artifact(b0_path)
    b1_pca_scorer: PCAScorer = load_model_artifact(b1_pca_path)
    b1_if_scorer: IsolationForestScorer = load_model_artifact(b1_iforest_path)
    b2_scorer: B2SequentialScorer = load_b2_scorer(dataset, train_windows, b2_ckpt_path)

    thresholds = FROZEN_CALIB_THRESHOLDS[dataset]

    return {
        "b0": {
            "scorer": b0_scorer,
            "threshold": thresholds["b0"],
            "name": "B0_Frequency",
        },
        "b1_pca": {
            "scorer": b1_pca_scorer,
            "threshold": thresholds["b1_pca"],
            "name": "B1_PCA",
        },
        "b1_iforest": {
            "scorer": b1_if_scorer,
            "threshold": thresholds["b1_iforest"],
            "name": "B1_IsolationForest",
        },
        "b2": {
            "scorer": b2_scorer,
            "threshold": thresholds["b2_alpha_0_05"],
            "thresholds_alpha_grid": {
                0.01: thresholds["b2_alpha_0_01"],
                0.05: thresholds["b2_alpha_0_05"],
                0.10: thresholds["b2_alpha_0_10"],
                0.20: thresholds["b2_alpha_0_20"],
            },
            "name": "B2_SequentialGRU",
        },
    }


def score_and_classify(
    scorer: Any,
    windows: List[LogWindow],
    threshold: float,
    strict: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """Score windows using a scorer and classify according to threshold.

    Args:
        scorer: Baseline scorer with .score(windows) method.
        windows: List of LogWindow objects.
        threshold: Frozen decision threshold.
        strict: If True, score > threshold; if False, score >= threshold.

    Returns:
        (scores, predictions) arrays.
    """
    scores = scorer.score(windows)
    preds = np.array([1 if (s > threshold if strict else s >= threshold) else 0 for s in scores], dtype=int)
    return scores, preds
