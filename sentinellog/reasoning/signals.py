"""Deterministic signal extraction for Phase 8 Incident Reasoning Engine.

Derives objective, auditable signals from:
- Phase 3 baseline anomaly scores (B0)
- Phase 4 sequential model scores (B2) and selective gate states
- Phase 5 & 6 retrieval candidate and MMR selection scores
- Phase 7 citation bundle and provenance verification status
- Window structural metadata (record count, timestamps, template repetitions)
"""

from typing import Any, Dict, List, Optional, Sequence
import numpy as np

from sentinellog.ingestion.schemas import LogWindow
from sentinellog.provenance.schemas import Citation, CitationBundle
from sentinellog.reasoning.schemas import IncidentSignal, SufficiencyStatus


class SignalExtractor:
    """Extracts deterministic numerical and categorical reasoning signals."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize signal extractor with configuration thresholds."""
        cfg = config or {}
        st = cfg.get("signal_thresholds", {})
        self.anomaly_high = float(st.get("anomaly_high", 1.20))
        self.anomaly_medium = float(st.get("anomaly_medium", 0.50))
        self.relevance_high = float(st.get("relevance_high", 0.70))
        self.relevance_medium = float(st.get("relevance_medium", 0.40))
        self.diversity_min = float(st.get("diversity_min", 0.30))
        self.agreement_threshold = float(st.get("agreement_threshold", 0.25))

        es = cfg.get("evidence_sufficiency", {})
        self.min_evidence_count = int(es.get("min_evidence_count", 1))
        self.min_sufficient_evidence_count = int(es.get("min_sufficient_evidence_count", 2))
        self.min_mean_relevance = float(es.get("min_mean_relevance", 0.50))
        self.min_diversity = float(es.get("min_diversity", 0.20))

    def extract_signals(
        self,
        window: LogWindow,
        anomaly_score: float,
        gate_decision: str,
        citation_bundle: Optional[CitationBundle] = None,
        b0_score: Optional[float] = None,
        provenance_verified: bool = True,
    ) -> Dict[str, IncidentSignal]:
        """Extract all deterministic signals for a query window.

        Args:
            window: LogWindow record.
            anomaly_score: Phase 4 sequential score (B2).
            gate_decision: Phase 4 gate output ('ESCALATE' or 'AUTO-CLEAR').
            citation_bundle: Optional Phase 7 citation bundle.
            b0_score: Optional Phase 3 frequency baseline score.
            provenance_verified: Whether provenance verification passed.

        Returns:
            Dictionary of signal_name -> IncidentSignal.
        """
        signals: Dict[str, IncidentSignal] = {}

        # 1. Anomaly Score Strength
        norm_anomaly = float(np.clip(anomaly_score / max(self.anomaly_high, 1e-6), 0.0, 1.0))
        if anomaly_score >= self.anomaly_high:
            anomaly_str = "HIGH"
        elif anomaly_score >= self.anomaly_medium:
            anomaly_str = "MEDIUM"
        else:
            anomaly_str = "LOW"

        signals["anomaly_score_strength"] = IncidentSignal(
            name="anomaly_score_strength",
            value=float(anomaly_score),
            normalized_value=norm_anomaly,
            strength=anomaly_str,
            description=f"Sequential anomaly score ({anomaly_score:.4f}) evaluated against thresholds.",
        )

        # 2. Selective Escalation State
        is_escalated = (gate_decision.upper() == "ESCALATE")
        signals["selective_escalation_state"] = IncidentSignal(
            name="selective_escalation_state",
            value=gate_decision.upper(),
            normalized_value=1.0 if is_escalated else 0.0,
            strength="HIGH" if is_escalated else "LOW",
            description=f"Selective prediction gate decision: {gate_decision}.",
        )

        # 3. Baseline Agreement (B0 vs B2)
        if b0_score is not None:
            # Check if both agree on elevated or normal
            b0_elevated = (b0_score >= 1.0)
            b2_elevated = (anomaly_score >= self.anomaly_medium)
            agreement = (b0_elevated == b2_elevated)
            signals["baseline_agreement"] = IncidentSignal(
                name="baseline_agreement",
                value={"b0": float(b0_score), "b2": float(anomaly_score), "agree": agreement},
                normalized_value=1.0 if agreement else 0.0,
                strength="HIGH" if agreement else "LOW",
                description="Cross-model alignment between frequency baseline (B0) and sequential scorer (B2).",
            )
        else:
            signals["baseline_agreement"] = IncidentSignal(
                name="baseline_agreement",
                value=None,
                normalized_value=0.5,
                strength="MEDIUM",
                description="Baseline B0 score not provided; neutral agreement assumed.",
            )

        # 4. Evidence Retrieval Metrics
        citations: List[Citation] = citation_bundle.citations if citation_bundle else []
        ev_count = len(citations)
        signals["evidence_count"] = IncidentSignal(
            name="evidence_count",
            value=ev_count,
            normalized_value=float(np.clip(ev_count / max(self.min_sufficient_evidence_count, 1), 0.0, 1.0)),
            strength="HIGH" if ev_count >= self.min_sufficient_evidence_count else ("MEDIUM" if ev_count > 0 else "LOW"),
            description=f"Number of retrieved and verified evidence items: {ev_count}.",
        )

        # 5. Evidence Relevance
        if ev_count > 0:
            rel_scores = [c.retrieval_score for c in citations]
            mean_rel = float(np.mean(rel_scores))
            max_rel = float(np.max(rel_scores))
            if mean_rel >= self.relevance_high:
                rel_strength = "HIGH"
            elif mean_rel >= self.relevance_medium:
                rel_strength = "MEDIUM"
            else:
                rel_strength = "LOW"
        else:
            mean_rel = 0.0
            max_rel = 0.0
            rel_strength = "LOW"

        signals["evidence_relevance"] = IncidentSignal(
            name="evidence_relevance",
            value={"mean": round(mean_rel, 4), "max": round(max_rel, 4)},
            normalized_value=float(np.clip(mean_rel, 0.0, 1.0)),
            strength=rel_strength,
            description=f"Evidence similarity score (mean={mean_rel:.4f}, max={max_rel:.4f}).",
        )

        # 6. Evidence Diversity (MMR redundancy)
        if ev_count > 1:
            # MMR redundancy penalty proxy from Phase 6
            # In Phase 6, selection_score = lambda * rel - (1 - lambda) * redundancy
            # Higher diversity = lower inter-evidence similarity
            sel_scores = [c.selection_score for c in citations]
            redundancy_proxies = [max(0.0, c.retrieval_score - c.selection_score) for c in citations]
            mean_redundancy = float(np.mean(redundancy_proxies))
            diversity = float(np.clip(1.0 - mean_redundancy, 0.0, 1.0))
        elif ev_count == 1:
            diversity = 0.5  # Neutral for single item
        else:
            diversity = 0.0

        signals["evidence_diversity"] = IncidentSignal(
            name="evidence_diversity",
            value=round(diversity, 4),
            normalized_value=diversity,
            strength="HIGH" if diversity >= self.diversity_min else "LOW",
            description=f"Evidence set diversity (diversity={diversity:.4f}).",
        )

        # 7. Repeated Template Behavior
        n_records = window.record_count
        t_ids = window.template_ids or []
        n_unique_templates = len(set(t_ids))
        rep_ratio = float(1.0 - (n_unique_templates / max(n_records, 1))) if n_records > 0 else 0.0

        signals["repeated_template_behavior"] = IncidentSignal(
            name="repeated_template_behavior",
            value={"unique_templates": n_unique_templates, "total_records": n_records, "repeat_ratio": round(rep_ratio, 4)},
            normalized_value=rep_ratio,
            strength="HIGH" if rep_ratio >= 0.80 else ("MEDIUM" if rep_ratio >= 0.40 else "LOW"),
            description=f"Repetition density: {rep_ratio * 100:.1f}% repeated templates in window.",
        )

        # 8. Unknown Template Presence
        has_unknown = bool(window.metadata.get("has_unknown_template", False)) if hasattr(window, "metadata") and window.metadata else False
        signals["unknown_template_presence"] = IncidentSignal(
            name="unknown_template_presence",
            value=has_unknown,
            normalized_value=1.0 if has_unknown else 0.0,
            strength="HIGH" if has_unknown else "LOW",
            description="Presence of log events matching no known historical Drain3 template.",
        )

        # 9. Temporal Concentration
        duration = max(0.0, window.end_time - window.start_time)
        rate = float(n_records / max(duration, 1.0)) if duration > 0 else float(n_records)
        signals["temporal_concentration"] = IncidentSignal(
            name="temporal_concentration",
            value={"duration_sec": round(duration, 2), "rate_per_sec": round(rate, 4)},
            normalized_value=float(np.clip(rate / 50.0, 0.0, 1.0)),
            strength="HIGH" if rate >= 10.0 else "LOW",
            description=f"Log event density over time: {rate:.2f} msgs/sec.",
        )

        # 10. Provenance Validity
        prov_valid = provenance_verified and (citation_bundle.all_verified if citation_bundle else False) if is_escalated else True
        signals["evidence_provenance_validity"] = IncidentSignal(
            name="evidence_provenance_validity",
            value=prov_valid,
            normalized_value=1.0 if prov_valid else 0.0,
            strength="HIGH" if prov_valid else "LOW",
            description="Status of round-trip source addressability and dual-hash integrity verification.",
        )

        # 11. Evidence Sufficiency
        if not is_escalated:
            sufficiency = SufficiencyStatus.SUFFICIENT.value
        elif not prov_valid:
            sufficiency = SufficiencyStatus.INSUFFICIENT.value
        elif ev_count >= self.min_sufficient_evidence_count and mean_rel >= self.min_mean_relevance and diversity >= self.min_diversity:
            sufficiency = SufficiencyStatus.SUFFICIENT.value
        elif ev_count >= self.min_evidence_count and mean_rel >= self.relevance_medium:
            sufficiency = SufficiencyStatus.PARTIAL.value
        else:
            sufficiency = SufficiencyStatus.INSUFFICIENT.value

        signals["evidence_sufficiency"] = IncidentSignal(
            name="evidence_sufficiency",
            value=sufficiency,
            normalized_value=1.0 if sufficiency == "SUFFICIENT" else (0.5 if sufficiency == "PARTIAL" else 0.0),
            strength="HIGH" if sufficiency == "SUFFICIENT" else ("MEDIUM" if sufficiency == "PARTIAL" else "LOW"),
            description=f"Evaluation of evidence quality, diversity, and count: {sufficiency}.",
        )

        return signals
