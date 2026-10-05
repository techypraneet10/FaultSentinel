"""Signal aggregation, conflict detection, and evidence contribution mapping.

Analyzes interactions across signals:
1. Categorizes each citation into a typed EvidenceContribution.
2. Explicitly identifies conflicts across signals (e.g., high anomaly score vs weak evidence).
3. Evaluates overall signal agreement and consistency.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np

from sentinellog.provenance.schemas import Citation, CitationBundle
from sentinellog.reasoning.schemas import (
    ContributionType,
    EvidenceContribution,
    IncidentSignal,
)


class SignalAggregator:
    """Aggregates extracted signals, detects conflicts, and evaluates evidence contributions."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize aggregator with contribution and conflict thresholds."""
        cfg = config or {}
        cb = cfg.get("contributions", {})
        self.supporting_thresh = float(cb.get("supporting_relevance_threshold", 0.70))
        self.contextual_thresh = float(cb.get("contextual_relevance_threshold", 0.40))
        self.max_redundancy_penalty = float(cb.get("max_redundancy_penalty", 0.60))

    def evaluate_contributions(
        self,
        citations: Sequence[Citation],
        provenance_verified: bool = True,
    ) -> List[EvidenceContribution]:
        """Classify each citation into a deterministic EvidenceContribution record.

        Args:
            citations: Ordered sequence of Citation objects.
            provenance_verified: Overall bundle provenance verification status.

        Returns:
            List of EvidenceContribution objects.
        """
        contributions: List[EvidenceContribution] = []

        for cit in citations:
            rel = float(cit.retrieval_score)
            sel = float(cit.selection_score)
            redundancy = max(0.0, rel - sel)

            if not provenance_verified:
                c_type = ContributionType.INSUFFICIENT.value
                strength = "LOW"
                p_status = "INVALID"
            elif rel >= self.supporting_thresh:
                c_type = ContributionType.SUPPORTING.value
                strength = "HIGH" if rel >= 0.85 else "MEDIUM"
                p_status = "VERIFIED"
            elif rel >= self.contextual_thresh:
                c_type = ContributionType.CONTEXTUAL.value
                strength = "MEDIUM" if redundancy < self.max_redundancy_penalty else "LOW"
                p_status = "VERIFIED"
            else:
                c_type = ContributionType.CONTRADICTING.value
                strength = "LOW"
                p_status = "VERIFIED"

            contributions.append(
                EvidenceContribution(
                    citation_id=cit.citation_id,
                    chunk_id=cit.chunk_id,
                    relevance_score=round(rel, 4),
                    redundancy_score=round(redundancy, 4),
                    contribution_type=c_type,
                    contribution_strength=strength,
                    provenance_status=p_status,
                )
            )

        return contributions

    def detect_conflicts(
        self,
        signals: Dict[str, IncidentSignal],
        contributions: Sequence[EvidenceContribution],
    ) -> List[Dict[str, Any]]:
        """Identify explicit logical or numerical conflicts among reasoning signals.

        Args:
            signals: Dictionary of extracted IncidentSignals.
            contributions: Evaluated EvidenceContributions.

        Returns:
            List of detected conflict descriptions.
        """
        conflicts: List[Dict[str, Any]] = []

        anomaly_sig = signals.get("anomaly_score_strength")
        escalation_sig = signals.get("selective_escalation_state")
        relevance_sig = signals.get("evidence_relevance")
        baseline_sig = signals.get("baseline_agreement")
        sufficiency_sig = signals.get("evidence_sufficiency")

        is_escalated = (escalation_sig.value == "ESCALATE") if escalation_sig else False
        if not is_escalated:
            return conflicts  # Auto-cleared windows have no conflict

        # Conflict 1: High Anomaly Score with Low/Contradicting Evidence Relevance
        if anomaly_sig and anomaly_sig.strength == "HIGH":
            supporting_count = sum(1 for c in contributions if c.contribution_type == "SUPPORTING")
            if supporting_count == 0:
                conflicts.append({
                    "conflict_id": "CONF-001",
                    "type": "ANOMALY_EVIDENCE_MISMATCH",
                    "description": (
                        f"High anomaly score ({anomaly_sig.value:.4f}) but zero supporting historical evidence chunks. "
                        f"Retrieved patterns do not corroborate an established incident type."
                    ),
                    "severity": "HIGH",
                })

        # Conflict 2: Model Disagreement (B0 vs B2)
        if baseline_sig and isinstance(baseline_sig.value, dict):
            b0_v = baseline_sig.value.get("b0", 0.0)
            b2_v = baseline_sig.value.get("b2", 0.0)
            agree = baseline_sig.value.get("agree", True)
            if not agree:
                conflicts.append({
                    "conflict_id": "CONF-002",
                    "type": "CROSS_MODEL_DISAGREEMENT",
                    "description": (
                        f"Disagreement between frequency baseline B0 ({b0_v:.4f}) and sequential model B2 ({b2_v:.4f}). "
                        f"Sequence is anomalous in order but normal in event frequency."
                    ),
                    "severity": "MEDIUM",
                })

        # Conflict 3: Sufficient Count but Insufficient Relevance
        if sufficiency_sig and sufficiency_sig.value == "INSUFFICIENT" and len(contributions) >= 2:
            conflicts.append({
                "conflict_id": "CONF-003",
                "type": "COUNT_RELEVANCE_DIVERGENCE",
                "description": (
                    f"Retrieved {len(contributions)} candidate evidence items, but their similarity was below sufficiency thresholds."
                ),
                "severity": "LOW",
            })

        return conflicts

    def compute_signal_agreement(
        self,
        signals: Dict[str, IncidentSignal],
        conflicts: Sequence[Dict[str, Any]],
    ) -> Tuple[float, str]:
        """Compute aggregate numerical agreement score and categorical agreement level.

        Args:
            signals: Dictionary of extracted IncidentSignals.
            conflicts: List of detected conflicts.

        Returns:
            Tuple of (agreement_score: float in [0.0, 1.0], agreement_level: str).
        """
        # Base agreement starts at 1.0
        score = 1.0

        # Penalize for each detected conflict
        for conf in conflicts:
            sev = conf.get("severity", "MEDIUM")
            if sev == "HIGH":
                score -= 0.40
            elif sev == "MEDIUM":
                score -= 0.20
            else:
                score -= 0.10

        score = float(np.clip(score, 0.0, 1.0))

        if score >= 0.80:
            level = "HIGH"
        elif score >= 0.50:
            level = "MODERATE"
        elif score >= 0.30:
            level = "LOW"
        else:
            level = "CONFLICT"

        return round(score, 4), level
