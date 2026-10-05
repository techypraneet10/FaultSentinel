"""Main orchestration engine for Phase 8 Deterministic Incident Reasoning.

Coordinates:
1. Strict input validation and label leakage guards.
2. Provenance gate verification before reasoning.
3. Signal extraction and multi-signal aggregation.
4. Conflict detection and evidence contribution evaluation.
5. Rule precedence execution and severity determination.
6. Deterministic confidence scoring.
7. Construction of reproducible IncidentAssessment and ReasoningTrace.
"""

import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple
import yaml

from sentinellog.ingestion.schemas import LogWindow
from sentinellog.provenance.schemas import CitationBundle
from sentinellog.reasoning.aggregation import SignalAggregator
from sentinellog.reasoning.confidence import ReasoningConfidenceCalculator
from sentinellog.reasoning.exceptions import (
    ConfigurationError,
    InvalidSplitError,
    LabelLeakageError,
    ProvenanceInvalidError,
)
from sentinellog.reasoning.rules import RuleEngine
from sentinellog.reasoning.schemas import (
    IncidentAssessment,
    IncidentDecision,
    IncidentSeverity,
    ProvenanceStatus,
    ReasoningResult,
    ReasoningTrace,
    SufficiencyStatus,
)
from sentinellog.reasoning.signals import SignalExtractor
from sentinellog.reasoning.validation import (
    validate_no_label_leakage,
    validate_provenance_gate,
    validate_reasoning_split,
)
from sentinellog.reasoning.version import ENGINE_VERSION


def compute_configuration_hash(config: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 fingerprint over canonical configuration dict."""
    canonical_json = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class IncidentReasoningEngine:
    """Deterministic, auditable reasoning engine for selective incident triage."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None):
        """Initialize reasoning engine from configuration.

        Args:
            config: Optional configuration dictionary.
            config_path: Optional path to YAML configuration file.
        """
        if config is not None:
            self.config = config
        elif config_path is not None:
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {}

        self.engine_version = self.config.get("engine", {}).get("version", ENGINE_VERSION)
        self.config_hash = compute_configuration_hash(self.config)

        # Initialize subcomponents
        self.signal_extractor = SignalExtractor(config=self.config)
        self.aggregator = SignalAggregator(config=self.config)
        self.rule_engine = RuleEngine(config=self.config)
        self.confidence_calc = ReasoningConfidenceCalculator(config=self.config)

        pg = self.config.get("provenance_gate", {})
        self.strict_provenance = bool(pg.get("strict", True))
        self.allowed_splits = pg.get("allowed_splits", ["calibration", "train"])

    def assess(
        self,
        window: LogWindow,
        anomaly_score: float,
        gate_decision: str,
        citation_bundle: Optional[CitationBundle] = None,
        b0_score: Optional[float] = None,
        split: str = "calibration",
        ablation_mode: Optional[str] = None,
    ) -> ReasoningResult:
        """Execute deterministic incident reasoning for a single query window.

        Args:
            window: LogWindow object representing the query window.
            anomaly_score: Phase 4 sequential model score (B2).
            gate_decision: Phase 4 gate decision ('ESCALATE' or 'AUTO-CLEAR').
            citation_bundle: Optional Phase 7 CitationBundle with verified citations.
            b0_score: Optional Phase 3 frequency baseline score.
            split: Data partition ('calibration' or 'train').
            ablation_mode: Optional ablation variant name.

        Returns:
            ReasoningResult containing structured IncidentAssessment and ReasoningTrace.
        """
        start_time = time.perf_counter()

        target_split = getattr(window, "split", split)

        # 1. Strict Input Validation & Label Leakage Guards
        validate_reasoning_split(target_split, allowed_splits=self.allowed_splits)

        validate_no_label_leakage({
            "window_id": window.window_id,
            "session_id": window.session_id,
            "template_ids": window.template_ids,
            "record_count": window.record_count,
            "metadata": window.metadata,
        }, path="query_window")

        is_escalated = (gate_decision.strip().upper() == "ESCALATE")

        # 2. Strict Provenance Gate
        prov_verified = True
        prov_status = ProvenanceStatus.VERIFIED.value
        prov_error_msg = ""

        if is_escalated:
            is_valid, reason = validate_provenance_gate(
                bundle=citation_bundle,
                dataset=window.dataset,
                strict=self.strict_provenance,
            )
            if not is_valid:
                prov_verified = False
                prov_status = ProvenanceStatus.INVALID.value
                prov_error_msg = reason

        # 3. Deterministic Signal Extraction
        signals = self.signal_extractor.extract_signals(
            window=window,
            anomaly_score=anomaly_score,
            gate_decision=gate_decision,
            citation_bundle=citation_bundle,
            b0_score=b0_score,
            provenance_verified=prov_verified,
        )

        # Apply Ablation: Relevance Only (ignores diversity in sufficiency)
        if ablation_mode == "relevance_only":
            rel_sig = signals.get("evidence_relevance")
            mean_rel = rel_sig.value.get("mean", 0.0) if (rel_sig and isinstance(rel_sig.value, dict)) else 0.0
            ev_cnt = signals["evidence_count"].value
            if not is_escalated:
                suff = SufficiencyStatus.SUFFICIENT.value
            elif not prov_verified:
                suff = SufficiencyStatus.INSUFFICIENT.value
            elif ev_cnt >= 2 and mean_rel >= 0.50:
                suff = SufficiencyStatus.SUFFICIENT.value
            elif ev_cnt >= 1 and mean_rel >= 0.40:
                suff = SufficiencyStatus.PARTIAL.value
            else:
                suff = SufficiencyStatus.INSUFFICIENT.value
            signals["evidence_sufficiency"] = signals["evidence_sufficiency"].__class__(
                name="evidence_sufficiency",
                value=suff,
                normalized_value=1.0 if suff == "SUFFICIENT" else (0.5 if suff == "PARTIAL" else 0.0),
                strength="HIGH" if suff == "SUFFICIENT" else ("MEDIUM" if suff == "PARTIAL" else "LOW"),
                description="Ablation relevance_only: diversity ignored.",
            )

        # Apply Ablation: Sufficiency Disabled
        if ablation_mode == "sufficiency_disabled":
            if is_escalated and prov_verified and signals["evidence_count"].value > 0:
                suff = SufficiencyStatus.SUFFICIENT.value
                signals["evidence_sufficiency"] = signals["evidence_sufficiency"].__class__(
                    name="evidence_sufficiency",
                    value=suff,
                    normalized_value=1.0,
                    strength="HIGH",
                    description="Ablation sufficiency_disabled: all non-empty sets considered sufficient.",
                )

        # 4. Evidence Contribution Evaluation
        citations = citation_bundle.citations if citation_bundle else []
        contributions = self.aggregator.evaluate_contributions(
            citations=citations,
            provenance_verified=prov_verified,
        )

        # 5. Conflict Detection & Signal Agreement
        conflicts = self.aggregator.detect_conflicts(
            signals=signals,
            contributions=contributions,
        )

        # Add provenance failure conflict if applicable
        if not prov_verified and is_escalated:
            conflicts.append({
                "conflict_id": "CONF-PROV",
                "type": "PROVENANCE_INTEGRITY_FAILURE",
                "description": f"Provenance verification failed: {prov_error_msg}",
                "severity": "CRITICAL",
            })

        # Apply Ablation: Conflict Ignored
        active_conflicts = [] if ablation_mode == "conflict_ignored" else conflicts

        agreement_score, agreement_level = self.aggregator.compute_signal_agreement(
            signals=signals,
            conflicts=active_conflicts,
        )

        # 6. Rule Precedence Execution
        decision, rules_evaluated, rules_fired = self.rule_engine.evaluate_decision(
            signals=signals,
            contributions=contributions,
            conflicts=active_conflicts,
            provenance_verified=prov_verified,
        )

        # 7. Severity Determination
        severity = self.rule_engine.evaluate_severity(
            decision=decision,
            signals=signals,
            contributions=contributions,
            conflicts=active_conflicts,
        )

        # 8. Deterministic Confidence Calculation
        confidence = self.confidence_calc.calculate_confidence(
            signals=signals,
            agreement_score=agreement_score,
            conflicts=active_conflicts,
            provenance_verified=prov_verified,
        )

        # 9. Machine-Readable Reasoning Trace
        citation_ids = [c.citation_id for c in citations]
        trace = ReasoningTrace(
            rules_evaluated=rules_evaluated,
            rules_fired=rules_fired,
            signals={k: v.to_dict() for k, v in signals.items()},
            evidence_used=citation_ids,
            conflicts=conflicts,
            final_decision=decision,
            final_severity=severity,
        )

        # 10. Assemble Immutable IncidentAssessment
        assessment = IncidentAssessment(
            dataset=window.dataset,
            split=target_split,
            window_id=window.window_id,
            session_id=window.session_id,
            decision=decision,
            severity=severity,
            confidence=confidence,
            signal_summary={
                "anomaly_strength": signals["anomaly_score_strength"].strength,
                "escalation_state": signals["selective_escalation_state"].value,
                "evidence_count": signals["evidence_count"].value,
                "evidence_relevance_mean": (
                    signals["evidence_relevance"].value.get("mean")
                    if isinstance(signals["evidence_relevance"].value, dict)
                    else 0.0
                ),
                "evidence_sufficiency": signals["evidence_sufficiency"].value,
                "signal_agreement": agreement_level,
                "conflict_count": len(conflicts),
            },
            evidence_contributions=contributions,
            reasoning_trace=trace,
            citation_ids=citation_ids,
            provenance_status=prov_status,
            engine_version=self.engine_version,
            configuration_hash=self.config_hash,
            created_timestamp=None,  # Populated deterministically at dataset run if required
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return ReasoningResult(
            assessment=assessment,
            raw_window_id=window.window_id,
            processing_time_ms=round(elapsed_ms, 3),
        )
