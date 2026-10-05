"""Integration between Selective Prediction Gate and Phase 5 Retrieval Engine.

Enforces the central research principle:
    - Normal / low-risk windows that receive AUTO-CLEAR bypass retrieval entirely.
    - Only windows that receive ESCALATE invoke the contextual retrieval engine.
"""

from typing import List, Optional, Sequence

from sentinellog.calibration.gate import SelectiveGate
from sentinellog.ingestion.schemas import LogWindow
from sentinellog.retrieval.engine import IncidentRetriever
from sentinellog.retrieval.schemas import GatedRetrievalResult


class GatedRetrievalPipeline:
    """End-to-end pipeline connecting calibrated selective escalation to contextual retrieval."""

    def __init__(self, gate: SelectiveGate, retriever: IncidentRetriever):
        """Initialize gated pipeline.

        Args:
            gate: Calibrated SelectiveGate instance.
            retriever: IncidentRetriever instance holding the TRAIN corpus index.
        """
        self.gate = gate
        self.retriever = retriever

    def process_window(
        self,
        window: LogWindow,
        score: float,
        k: int = 5,
    ) -> GatedRetrievalResult:
        """Process a single log window through selective gate and conditional retrieval.

        Args:
            window: LogWindow to triage.
            score: Calibrated nonconformity anomaly score.
            k: Top-k evidence chunks to retrieve if escalated.

        Returns:
            GatedRetrievalResult containing decision, retrieval invocation flag, and evidence.
        """
        decision = self.gate.decide(score)

        if decision == "AUTO-CLEAR":
            return GatedRetrievalResult(
                window_id=window.window_id,
                score=float(score),
                decision="AUTO-CLEAR",
                retrieval_invoked=False,
                retrieved_evidence=None,
            )

        # Decision is "ESCALATE": Invoke retrieval over historical TRAIN incidents
        evidence = self.retriever.retrieve(query=window, k=k)
        return GatedRetrievalResult(
            window_id=window.window_id,
            score=float(score),
            decision="ESCALATE",
            retrieval_invoked=True,
            retrieved_evidence=evidence,
        )

    def process_batch(
        self,
        windows: Sequence[LogWindow],
        scores: Sequence[float],
        k: int = 5,
    ) -> List[GatedRetrievalResult]:
        """Process a batch of log windows through selective gating and conditional retrieval."""
        if len(windows) != len(scores):
            raise ValueError(
                f"Mismatch between windows count ({len(windows)}) and scores count ({len(scores)})"
            )

        return [
            self.process_window(w, s, k=k)
            for w, s in zip(windows, scores)
        ]
