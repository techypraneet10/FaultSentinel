"""Incident classification and batch interface for Phase 8.

Provides high-level batch processing and query dispatching using IncidentReasoningEngine.
"""

from typing import Any, Dict, List, Optional, Sequence

from sentinellog.ingestion.schemas import LogWindow
from sentinellog.provenance.schemas import CitationBundle
from sentinellog.reasoning.engine import IncidentReasoningEngine
from sentinellog.reasoning.schemas import IncidentAssessment, ReasoningResult


class IncidentClassifier:
    """High-level classifier coordinating window assessments through IncidentReasoningEngine."""

    def __init__(self, engine: Optional[IncidentReasoningEngine] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize classifier.

        Args:
            engine: Optional IncidentReasoningEngine instance.
            config: Optional configuration dictionary.
        """
        self.engine = engine or IncidentReasoningEngine(config=config)

    def classify_window(
        self,
        window: LogWindow,
        anomaly_score: float,
        gate_decision: str,
        citation_bundle: Optional[CitationBundle] = None,
        b0_score: Optional[float] = None,
        ablation_mode: Optional[str] = None,
    ) -> IncidentAssessment:
        """Classify a single window and return its IncidentAssessment."""
        res = self.engine.assess(
            window=window,
            anomaly_score=anomaly_score,
            gate_decision=gate_decision,
            citation_bundle=citation_bundle,
            b0_score=b0_score,
            ablation_mode=ablation_mode,
        )
        return res.assessment

    def classify_batch(
        self,
        windows: Sequence[LogWindow],
        anomaly_scores: Sequence[float],
        gate_decisions: Sequence[str],
        citation_bundles: Optional[Dict[str, CitationBundle]] = None,
        b0_scores: Optional[Sequence[Optional[float]]] = None,
        ablation_mode: Optional[str] = None,
    ) -> List[ReasoningResult]:
        """Classify a batch of windows deterministically."""
        bundles_map = citation_bundles or {}
        b0_list = b0_scores if b0_scores is not None else [None] * len(windows)

        results: List[ReasoningResult] = []
        for win, score, decision, b0_s in zip(windows, anomaly_scores, gate_decisions, b0_list):
            bundle = bundles_map.get(win.window_id)
            res = self.engine.assess(
                window=win,
                anomaly_score=score,
                gate_decision=decision,
                citation_bundle=bundle,
                b0_score=b0_s,
                ablation_mode=ablation_mode,
            )
            results.append(res)

        return results
