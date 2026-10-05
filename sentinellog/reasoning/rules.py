"""Deterministic rule engine and priority execution for Phase 8.

Implements explicit, testable rule objects:
1. Ordered precedence:
   - Priority 1: Provenance Invalid (RULE-PROV-001)
   - Priority 2: Invalid Input (RULE-INPUT-001)
   - Priority 3: Insufficient Evidence (RULE-SUFF-001)
   - Priority 4: Explicit High-Confidence Conflict (RULE-CONF-001)
   - Priority 5: Strong Supported Incident (RULE-INC-001)
   - Priority 6: Suspicious Anomaly (RULE-SUSP-001)
   - Priority 7: Normal Operation (RULE-NORM-001)
2. Severity derivation rules based on explicit signals and evidence corroboration.
"""

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from sentinellog.reasoning.schemas import (
    EvidenceContribution,
    IncidentDecision,
    IncidentRule,
    IncidentSeverity,
    IncidentSignal,
)


class RuleEngine:
    """Evaluates explicit deterministic reasoning rules against extracted signals."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize rule engine with configuration thresholds."""
        cfg = config or {}
        st = cfg.get("signal_thresholds", {})
        self.anomaly_high = float(st.get("anomaly_high", 1.20))
        self.relevance_high = float(st.get("relevance_high", 0.70))

        sr = cfg.get("severity_rules", {})
        self.critical_anomaly_thresh = float(sr.get("critical_anomaly_threshold", 2.50))
        self.high_relevance_thresh = float(sr.get("high_relevance_threshold", 0.80))

        self.rules: List[IncidentRule] = self._build_rule_definitions()

    def _build_rule_definitions(self) -> List[IncidentRule]:
        """Construct deterministic rule catalog with documented priorities."""
        return [
            IncidentRule(
                rule_id="RULE-PROV-001",
                description="If provenance verification fails, refuse to reason over evidence and declare INSUFFICIENT_EVIDENCE.",
                inputs=["evidence_provenance_validity"],
                condition="provenance_validity == False",
                output="INSUFFICIENT_EVIDENCE",
                priority=1,
            ),
            IncidentRule(
                rule_id="RULE-INPUT-001",
                description="If input validation fails (e.g., test split access or label leakage), fail closed.",
                inputs=["split", "labels"],
                condition="invalid_split or label_leakage",
                output="INVALID_INPUT",
                priority=2,
            ),
            IncidentRule(
                rule_id="RULE-SUFF-001",
                description="If evidence sufficiency is INSUFFICIENT for an escalated window, declare INSUFFICIENT_EVIDENCE.",
                inputs=["selective_escalation_state", "evidence_sufficiency"],
                condition="escalated and evidence_sufficiency == 'INSUFFICIENT'",
                output="INSUFFICIENT_EVIDENCE",
                priority=3,
            ),
            IncidentRule(
                rule_id="RULE-CONF-001",
                description="If high-severity conflict exists between anomaly score and evidence relevance, declare SUSPICIOUS.",
                inputs=["conflicts", "signal_agreement"],
                condition="has_high_severity_conflict",
                output="SUSPICIOUS",
                priority=4,
            ),
            IncidentRule(
                rule_id="RULE-INC-001",
                description="If strong anomaly signal and strong supporting historical evidence agree, declare INCIDENT.",
                inputs=["anomaly_score_strength", "evidence_relevance", "evidence_sufficiency", "signal_agreement"],
                condition="anomaly == 'HIGH' and supporting_evidence >= 1 and sufficiency == 'SUFFICIENT'",
                output="INCIDENT",
                priority=5,
            ),
            IncidentRule(
                rule_id="RULE-SUSP-001",
                description="If window is escalated with partial evidence or moderate anomaly signal, declare SUSPICIOUS.",
                inputs=["selective_escalation_state", "anomaly_score_strength"],
                condition="escalated and (anomaly == 'MEDIUM' or sufficiency == 'PARTIAL')",
                output="SUSPICIOUS",
                priority=6,
            ),
            IncidentRule(
                rule_id="RULE-NORM-001",
                description="If window was auto-cleared by conformal selective gate, declare NORMAL.",
                inputs=["selective_escalation_state"],
                condition="selective_escalation_state == 'AUTO-CLEAR'",
                output="NORMAL",
                priority=7,
            ),
        ]

    def evaluate_decision(
        self,
        signals: Dict[str, IncidentSignal],
        contributions: Sequence[EvidenceContribution],
        conflicts: Sequence[Dict[str, Any]],
        provenance_verified: bool,
    ) -> Tuple[str, List[str], List[str]]:
        """Evaluate rule precedence and return final decision and firing trace.

        Args:
            signals: Dictionary of extracted IncidentSignals.
            contributions: Evaluated EvidenceContributions.
            conflicts: Detected conflicts.
            provenance_verified: Whether provenance verification passed.

        Returns:
            Tuple of (decision: str, rules_evaluated: List[str], rules_fired: List[str]).
        """
        rules_evaluated: List[str] = []
        rules_fired: List[str] = []

        escalation_sig = signals.get("selective_escalation_state")
        is_escalated = (escalation_sig.value == "ESCALATE") if escalation_sig else False

        anomaly_sig = signals.get("anomaly_score_strength")
        anomaly_str = anomaly_sig.strength if anomaly_sig else "LOW"

        suff_sig = signals.get("evidence_sufficiency")
        suff_val = suff_sig.value if suff_sig else "INSUFFICIENT"

        supporting_count = sum(1 for c in contributions if c.contribution_type == "SUPPORTING")
        has_high_conflict = any(c.get("severity") == "HIGH" for c in conflicts)

        # Priority 1: Provenance Gate (RULE-PROV-001)
        rules_evaluated.append("RULE-PROV-001")
        if is_escalated and not provenance_verified:
            rules_fired.append("RULE-PROV-001")
            return IncidentDecision.INSUFFICIENT_EVIDENCE.value, rules_evaluated, rules_fired

        # Priority 2: Input Guardrails evaluated in validation.py (RULE-INPUT-001)
        rules_evaluated.append("RULE-INPUT-001")

        # Priority 7: Auto-Clear Normal (RULE-NORM-001)
        if not is_escalated:
            rules_evaluated.append("RULE-NORM-001")
            rules_fired.append("RULE-NORM-001")
            return IncidentDecision.NORMAL.value, rules_evaluated, rules_fired

        # Priority 3: Insufficient Evidence (RULE-SUFF-001)
        rules_evaluated.append("RULE-SUFF-001")
        if suff_val == "INSUFFICIENT":
            rules_fired.append("RULE-SUFF-001")
            return IncidentDecision.INSUFFICIENT_EVIDENCE.value, rules_evaluated, rules_fired

        # Priority 4: High Conflict (RULE-CONF-001)
        rules_evaluated.append("RULE-CONF-001")
        if has_high_conflict:
            rules_fired.append("RULE-CONF-001")
            return IncidentDecision.SUSPICIOUS.value, rules_evaluated, rules_fired

        # Priority 5: Strong Supported Incident (RULE-INC-001)
        rules_evaluated.append("RULE-INC-001")
        if anomaly_str == "HIGH" and supporting_count >= 1 and suff_val == "SUFFICIENT":
            rules_fired.append("RULE-INC-001")
            return IncidentDecision.INCIDENT.value, rules_evaluated, rules_fired

        # Priority 6: Suspicious (RULE-SUSP-001)
        rules_evaluated.append("RULE-SUSP-001")
        rules_fired.append("RULE-SUSP-001")
        return IncidentDecision.SUSPICIOUS.value, rules_evaluated, rules_fired

    def evaluate_severity(
        self,
        decision: str,
        signals: Dict[str, IncidentSignal],
        contributions: Sequence[EvidenceContribution],
        conflicts: Sequence[Dict[str, Any]],
    ) -> str:
        """Derive deterministic incident severity level from explicit signals.

        Args:
            decision: Final incident decision string.
            signals: Dictionary of extracted IncidentSignals.
            contributions: Evaluated EvidenceContributions.
            conflicts: Detected conflicts.

        Returns:
            Severity string ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL').
        """
        if decision == IncidentDecision.NORMAL.value or decision == IncidentDecision.INSUFFICIENT_EVIDENCE.value:
            return IncidentSeverity.LOW.value

        anomaly_sig = signals.get("anomaly_score_strength")
        anomaly_val = float(anomaly_sig.value) if anomaly_sig else 0.0

        rel_sig = signals.get("evidence_relevance")
        max_rel = float(rel_sig.value.get("max", 0.0)) if (rel_sig and isinstance(rel_sig.value, dict)) else 0.0

        unknown_sig = signals.get("unknown_template_presence")
        has_unknown = bool(unknown_sig.value) if unknown_sig else False

        supporting_count = sum(1 for c in contributions if c.contribution_type == "SUPPORTING")

        # CRITICAL: Confirmed high-anomaly incident with unknown templates or extreme anomaly magnitude
        if decision == IncidentDecision.INCIDENT.value:
            if has_unknown or anomaly_val >= self.critical_anomaly_thresh:
                return IncidentSeverity.CRITICAL.value
            if max_rel >= self.high_relevance_thresh and supporting_count >= 2:
                return IncidentSeverity.HIGH.value
            return IncidentSeverity.MEDIUM.value

        # SUSPICIOUS:
        if decision == IncidentDecision.SUSPICIOUS.value:
            if anomaly_val >= self.anomaly_high or len(conflicts) > 0:
                return IncidentSeverity.MEDIUM.value
            return IncidentSeverity.LOW.value

        return IncidentSeverity.LOW.value
