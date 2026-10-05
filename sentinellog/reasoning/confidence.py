"""Deterministic reasoning confidence and support-strength calculation.

CRITICAL RESEARCH NOTICE:
The value produced by this module represents 'reasoning_confidence' or 'support_strength'.
It reflects the degree of deterministic corroboration across signals, evidence quality,
and provenance integrity.
IT IS NOT A STATISTICAL PROBABILITY OF INCIDENT OCCURRENCE.
"""

from typing import Any, Dict, List, Optional, Sequence
import numpy as np

from sentinellog.reasoning.schemas import IncidentSignal


class ReasoningConfidenceCalculator:
    """Calculates deterministic support strength for reasoning assessments."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize calculator with configurable component weights and penalties."""
        cfg = config or {}
        conf_cfg = cfg.get("confidence", {})
        weights = conf_cfg.get("weights", {})

        self.w_agreement = float(weights.get("signal_agreement", 0.30))
        self.w_relevance = float(weights.get("evidence_relevance", 0.30))
        self.w_diversity = float(weights.get("evidence_diversity", 0.20))
        self.w_provenance = float(weights.get("provenance_validity", 0.20))

        # Normalize weights to sum to 1.0
        w_sum = self.w_agreement + self.w_relevance + self.w_diversity + self.w_provenance
        if w_sum > 0:
            self.w_agreement /= w_sum
            self.w_relevance /= w_sum
            self.w_diversity /= w_sum
            self.w_provenance /= w_sum

        self.conflict_penalty = float(conf_cfg.get("conflict_penalty", 0.25))
        self.insufficient_penalty = float(conf_cfg.get("insufficient_penalty", 0.40))

    def calculate_confidence(
        self,
        signals: Dict[str, IncidentSignal],
        agreement_score: float,
        conflicts: Sequence[Dict[str, Any]],
        provenance_verified: bool,
    ) -> float:
        """Compute deterministic reasoning confidence in [0.0, 1.0].

        Args:
            signals: Dictionary of extracted IncidentSignals.
            agreement_score: Normalized agreement score in [0.0, 1.0].
            conflicts: List of detected conflicts.
            provenance_verified: Whether provenance verification passed.

        Returns:
            Reasoning confidence float in [0.0, 1.0].
        """
        # If provenance failed, confidence collapses to minimum baseline
        if not provenance_verified:
            return 0.05

        escalation_sig = signals.get("selective_escalation_state")
        is_escalated = (escalation_sig.value == "ESCALATE") if escalation_sig else False

        # For auto-cleared windows, high confidence in normal state
        if not is_escalated:
            return 0.95

        # Component scores
        rel_sig = signals.get("evidence_relevance")
        rel_val = rel_sig.normalized_value if rel_sig else 0.0

        div_sig = signals.get("evidence_diversity")
        div_val = div_sig.normalized_value if div_sig else 0.0

        prov_val = 1.0 if provenance_verified else 0.0

        raw_conf = (
            self.w_agreement * agreement_score
            + self.w_relevance * rel_val
            + self.w_diversity * div_val
            + self.w_provenance * prov_val
        )

        # Apply conflict penalty
        if len(conflicts) > 0:
            raw_conf -= self.conflict_penalty * min(len(conflicts), 3)

        # Apply insufficiency penalty if sufficiency is INSUFFICIENT
        suff_sig = signals.get("evidence_sufficiency")
        if suff_sig and suff_sig.value == "INSUFFICIENT":
            raw_conf -= self.insufficient_penalty

        return float(np.clip(raw_conf, 0.05, 0.98))
