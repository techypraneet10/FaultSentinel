"""Comprehensive test suite for Phase 8: Deterministic Incident Reasoning Engine.

Covers:
1. Schema serialization and dataclass integrity.
2. Signal extraction and normalization.
3. Evidence contribution taxonomy and classification.
4. Conflict detection and signal agreement.
5. Strict provenance gate enforcement and rejection modes.
6. Label leakage protection and split guardrails.
7. Explicit rule precedence and determinism.
8. Severity derivation logic.
9. Deterministic reasoning confidence and penalty mechanics.
10. Configuration hashing and reproducibility.
11. End-to-end integration and ablation sensitivity.
12. Regression against Phase 7 outputs (117 HDFS citations, 6 BGL citations).
"""

import copy
import json
import os
import pytest

from sentinellog.ingestion.schemas import LogWindow
from sentinellog.provenance.schemas import (
    Citation,
    CitationBundle,
    EvidenceProvenance,
    SourceArtifact,
    SourceLocation,
)
from sentinellog.reasoning.aggregation import SignalAggregator
from sentinellog.reasoning.confidence import ReasoningConfidenceCalculator
from sentinellog.reasoning.engine import (
    IncidentReasoningEngine,
    compute_configuration_hash,
)
from sentinellog.reasoning.exceptions import (
    InvalidSplitError,
    LabelLeakageError,
    ProvenanceInvalidError,
)
from sentinellog.reasoning.rules import RuleEngine
from sentinellog.reasoning.schemas import (
    ContributionType,
    EvidenceContribution,
    IncidentAssessment,
    IncidentDecision,
    IncidentRule,
    IncidentSeverity,
    IncidentSignal,
    ProvenanceStatus,
    ReasoningResult,
    ReasoningSummary,
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
from sentinellog.scoring.artifacts import TestAccessViolationError


@pytest.fixture
def sample_window():
    return LogWindow(
        dataset="hdfs",
        window_id="hdfs_session_blk_-7628164677193243450",
        session_id="blk_-7628164677193243450",
        start_time=1226243162.0,
        end_time=1226243445.0,
        record_count=14,
        template_ids=[1, 2, 3, 1, 2],
        raw_messages=["msg1", "msg2"],
        is_anomaly=False,
        metadata={"first_line": 2322, "last_line": 37840, "has_unknown_template": False},
    )


@pytest.fixture
def sample_citation_bundle():
    # Load actual verified Phase 7 citation bundle
    with open("results/phase7/hdfs/citations.jsonl", "r", encoding="utf-8") as f:
        bundle_dict = json.loads(f.readline())
    return CitationBundle.from_dict(bundle_dict)


@pytest.fixture
def bgl_citation_bundle():
    # Load actual verified Phase 7 BGL citation bundle
    with open("results/phase7/bgl/citations.jsonl", "r", encoding="utf-8") as f:
        bundle_dict = json.loads(f.readline())
    return CitationBundle.from_dict(bundle_dict)


# -----------------------------------------------------------------------------
# 1. SCHEMA SERIALIZATION & MODELS
# -----------------------------------------------------------------------------

def test_incident_assessment_dataclass():
    trace = ReasoningTrace(
        rules_evaluated=["RULE-INC-001"],
        rules_fired=["RULE-INC-001"],
        signals={"sig1": {"value": 1.0}},
        evidence_used=["cit_1"],
        conflicts=[],
        final_decision="INCIDENT",
        final_severity="HIGH",
    )
    contrib = EvidenceContribution(
        citation_id="cit_1",
        chunk_id="chunk_1",
        relevance_score=0.95,
        redundancy_score=0.0,
        contribution_type="SUPPORTING",
        contribution_strength="HIGH",
        provenance_status="VERIFIED",
    )
    assessment = IncidentAssessment(
        dataset="hdfs",
        split="calibration",
        window_id="win_1",
        session_id="blk_1",
        decision="INCIDENT",
        severity="HIGH",
        confidence=0.92,
        signal_summary={"anomaly": "HIGH"},
        evidence_contributions=[contrib],
        reasoning_trace=trace,
        citation_ids=["cit_1"],
        provenance_status="VERIFIED",
        engine_version=ENGINE_VERSION,
        configuration_hash="hash_123",
    )
    d = assessment.to_dict()
    reconstructed = IncidentAssessment.from_dict(d)
    assert reconstructed.decision == "INCIDENT"
    assert reconstructed.severity == "HIGH"
    assert reconstructed.confidence == 0.92
    assert len(reconstructed.evidence_contributions) == 1
    assert reconstructed.evidence_contributions[0].contribution_type == "SUPPORTING"


def test_evidence_contribution_dataclass():
    ec = EvidenceContribution(
        citation_id="c1",
        chunk_id="chk1",
        relevance_score=0.88,
        redundancy_score=0.12,
        contribution_type="SUPPORTING",
        contribution_strength="HIGH",
        provenance_status="VERIFIED",
    )
    d = ec.to_dict()
    rec = EvidenceContribution.from_dict(d)
    assert rec == ec
    assert rec.relevance_score == 0.88


def test_incident_rule_dataclass():
    rule = IncidentRule(
        rule_id="RULE-TEST-001",
        description="Test rule",
        inputs=["sig1"],
        condition="sig1 > 0",
        output="INCIDENT",
        priority=5,
    )
    d = rule.to_dict()
    rec = IncidentRule.from_dict(d)
    assert rec == rule
    assert rec.priority == 5


# -----------------------------------------------------------------------------
# 2. EVIDENCE CONTRIBUTION TAXONOMY
# -----------------------------------------------------------------------------

def test_evidence_contribution_classification_supporting(sample_citation_bundle):
    aggregator = SignalAggregator()
    contributions = aggregator.evaluate_contributions(sample_citation_bundle.citations, provenance_verified=True)
    # The first citation in HDFS has retrieval_score=1.0 >= 0.70
    assert contributions[0].contribution_type == ContributionType.SUPPORTING.value
    assert contributions[0].contribution_strength == "HIGH"
    assert contributions[0].provenance_status == "VERIFIED"


def test_evidence_contribution_classification_contextual(sample_citation_bundle):
    aggregator = SignalAggregator({"contributions": {"supporting_relevance_threshold": 0.99, "contextual_relevance_threshold": 0.50}})
    # Give a citation with 0.80 relevance -> becomes CONTEXTUAL under this threshold
    cit = sample_citation_bundle.citations[0]
    cit_dict = cit.to_dict()
    cit_dict["retrieval_score"] = 0.80
    mod_cit = Citation.from_dict(cit_dict)

    contributions = aggregator.evaluate_contributions([mod_cit], provenance_verified=True)
    assert contributions[0].contribution_type == ContributionType.CONTEXTUAL.value


def test_evidence_contribution_classification_contradicting(sample_citation_bundle):
    aggregator = SignalAggregator({"contributions": {"contextual_relevance_threshold": 0.50}})
    cit = sample_citation_bundle.citations[0]
    cit_dict = cit.to_dict()
    cit_dict["retrieval_score"] = 0.10  # Below 0.50
    mod_cit = Citation.from_dict(cit_dict)

    contributions = aggregator.evaluate_contributions([mod_cit], provenance_verified=True)
    assert contributions[0].contribution_type == ContributionType.CONTRADICTING.value


def test_evidence_contribution_classification_insufficient(sample_citation_bundle):
    aggregator = SignalAggregator()
    # When provenance fails, contributions are marked INSUFFICIENT
    contributions = aggregator.evaluate_contributions(sample_citation_bundle.citations, provenance_verified=False)
    for c in contributions:
        assert c.contribution_type == ContributionType.INSUFFICIENT.value
        assert c.provenance_status == "INVALID"


# -----------------------------------------------------------------------------
# 3. SIGNAL EXTRACTION & NORMALIZATION
# -----------------------------------------------------------------------------

def test_signal_extraction_values_and_strengths(sample_window, sample_citation_bundle):
    extractor = SignalExtractor()
    signals = extractor.extract_signals(
        window=sample_window,
        anomaly_score=1.85,
        gate_decision="ESCALATE",
        citation_bundle=sample_citation_bundle,
        b0_score=1.50,
        provenance_verified=True,
    )

    assert "anomaly_score_strength" in signals
    assert signals["anomaly_score_strength"].strength == "HIGH"
    assert signals["anomaly_score_strength"].normalized_value == 1.0

    assert "selective_escalation_state" in signals
    assert signals["selective_escalation_state"].value == "ESCALATE"

    assert "baseline_agreement" in signals
    assert signals["baseline_agreement"].strength == "HIGH"

    assert "evidence_relevance" in signals
    assert signals["evidence_relevance"].strength == "HIGH"

    assert "evidence_diversity" in signals
    assert signals["evidence_diversity"].normalized_value > 0.0

    assert "evidence_provenance_validity" in signals
    assert signals["evidence_provenance_validity"].value is True

    assert "evidence_sufficiency" in signals
    assert signals["evidence_sufficiency"].value == "SUFFICIENT"


# -----------------------------------------------------------------------------
# 4. CONFLICT DETECTION & SIGNAL AGREEMENT
# -----------------------------------------------------------------------------

def test_conflict_detection_anomaly_evidence_mismatch(sample_window, sample_citation_bundle):
    extractor = SignalExtractor()
    aggregator = SignalAggregator()

    # Create low relevance citation
    low_rel_cit = sample_citation_bundle.citations[0].to_dict()
    low_rel_cit["retrieval_score"] = 0.05
    c_low = Citation.from_dict(low_rel_cit)
    mod_bundle = copy.deepcopy(sample_citation_bundle)
    mod_bundle.citations = [c_low]

    signals = extractor.extract_signals(
        window=sample_window,
        anomaly_score=2.50,  # HIGH anomaly
        gate_decision="ESCALATE",
        citation_bundle=mod_bundle,
        provenance_verified=True,
    )
    contributions = aggregator.evaluate_contributions(mod_bundle.citations, provenance_verified=True)
    conflicts = aggregator.detect_conflicts(signals, contributions)

    assert len(conflicts) > 0
    assert any(c["type"] == "ANOMALY_EVIDENCE_MISMATCH" for c in conflicts)


def test_conflict_detection_cross_model_disagreement(sample_window, sample_citation_bundle):
    extractor = SignalExtractor()
    aggregator = SignalAggregator()

    # B2 score is high (2.0), but B0 frequency score is 0.05 (normal)
    signals = extractor.extract_signals(
        window=sample_window,
        anomaly_score=2.0,
        gate_decision="ESCALATE",
        citation_bundle=sample_citation_bundle,
        b0_score=0.05,
        provenance_verified=True,
    )
    contributions = aggregator.evaluate_contributions(sample_citation_bundle.citations, provenance_verified=True)
    conflicts = aggregator.detect_conflicts(signals, contributions)

    assert any(c["type"] == "CROSS_MODEL_DISAGREEMENT" for c in conflicts)


def test_signal_agreement_penalizes_conflicts():
    aggregator = SignalAggregator()
    signals = {}
    conflicts = [{"type": "TEST_CONFLICT", "severity": "HIGH"}]
    score, level = aggregator.compute_signal_agreement(signals, conflicts)
    assert score <= 0.60
    assert level in ("MODERATE", "LOW", "CONFLICT")


# -----------------------------------------------------------------------------
# 5. STRICT PROVENANCE GATE ENFORCEMENT
# -----------------------------------------------------------------------------

def test_provenance_gate_enforcement_valid(sample_citation_bundle):
    is_valid, msg = validate_provenance_gate(sample_citation_bundle, dataset="hdfs", strict=True)
    assert is_valid is True
    assert msg == "VERIFIED"


def test_provenance_gate_rejection_none():
    is_valid, msg = validate_provenance_gate(None, dataset="hdfs", strict=True)
    assert is_valid is False
    assert "No citation bundle" in msg


def test_provenance_gate_rejection_unverified_bundle(sample_citation_bundle):
    tampered_bundle = copy.deepcopy(sample_citation_bundle)
    tampered_bundle.all_verified = False

    is_valid, msg = validate_provenance_gate(tampered_bundle, dataset="hdfs", strict=True)
    assert is_valid is False
    assert "failed Phase 7 integrity checks" in msg


def test_provenance_gate_rejection_tampered_hashes(sample_citation_bundle):
    tampered_bundle = copy.deepcopy(sample_citation_bundle)
    c0_dict = tampered_bundle.citations[0].to_dict()
    c0_dict["source_content_hash"] = "invalid_hash"
    tampered_bundle.citations[0] = Citation.from_dict(c0_dict)

    is_valid, msg = validate_provenance_gate(tampered_bundle, dataset="hdfs", strict=True)
    assert is_valid is False
    assert "invalid source_content_hash" in msg


def test_provenance_gate_rejection_tampered_citation_id(sample_citation_bundle):
    tampered_bundle = copy.deepcopy(sample_citation_bundle)
    c0_dict = tampered_bundle.citations[0].to_dict()
    c0_dict["citation_id"] = "0000000000000000000000000000000000000000000000000000000000000000"
    tampered_bundle.citations[0] = Citation.from_dict(c0_dict)

    is_valid, msg = validate_provenance_gate(tampered_bundle, dataset="hdfs", strict=True)
    assert is_valid is False
    assert "Citation ID mismatch" in msg


# -----------------------------------------------------------------------------
# 6. LABEL LEAKAGE & PARTITION GUARDS
# -----------------------------------------------------------------------------

def test_label_leakage_protection_fails_on_label_key():
    with pytest.raises(LabelLeakageError, match="Label leakage detected"):
        validate_no_label_leakage({"window_id": "win_1", "anomaly_label": True})


def test_label_leakage_protection_fails_on_nested_label_key():
    with pytest.raises(LabelLeakageError, match="Label leakage detected"):
        validate_no_label_leakage({"evidence": [{"id": 1, "is_anomaly": True}]})


def test_test_split_access_strictly_rejected():
    with pytest.raises(TestAccessViolationError):
        validate_reasoning_split("test")


def test_unallowed_split_strictly_rejected():
    with pytest.raises(InvalidSplitError, match="not permitted"):
        validate_reasoning_split("arbitrary_split")


# -----------------------------------------------------------------------------
# 7. RULE ENGINE PRECEDENCE & DECISIONS
# -----------------------------------------------------------------------------

def test_rule_precedence_provenance_invalid_overrides_strong_anomaly(sample_window, sample_citation_bundle):
    engine = IncidentReasoningEngine()
    tampered_bundle = copy.deepcopy(sample_citation_bundle)
    tampered_bundle.all_verified = False

    res = engine.assess(
        window=sample_window,
        anomaly_score=3.5,  # Very high anomaly!
        gate_decision="ESCALATE",
        citation_bundle=tampered_bundle,
    )
    # Must refuse to declare incident and return INSUFFICIENT_EVIDENCE
    assert res.assessment.decision == IncidentDecision.INSUFFICIENT_EVIDENCE.value
    assert res.assessment.provenance_status == ProvenanceStatus.INVALID.value
    assert "RULE-PROV-001" in res.assessment.reasoning_trace.rules_fired


def test_rule_precedence_insufficient_evidence(sample_window, sample_citation_bundle):
    engine = IncidentReasoningEngine()
    # Zero citations
    empty_bundle = copy.deepcopy(sample_citation_bundle)
    empty_bundle.citations = []

    res = engine.assess(
        window=sample_window,
        anomaly_score=2.0,
        gate_decision="ESCALATE",
        citation_bundle=empty_bundle,
    )
    assert res.assessment.decision == IncidentDecision.INSUFFICIENT_EVIDENCE.value
    assert "RULE-SUFF-001" in res.assessment.reasoning_trace.rules_fired


def test_rule_precedence_conflict_declaration(sample_window, sample_citation_bundle):
    engine = IncidentReasoningEngine()
    # High anomaly, but completely irrelevant evidence -> conflict
    c_low = sample_citation_bundle.citations[0].to_dict()
    c_low["retrieval_score"] = 0.05
    c_low["selection_score"] = 0.05
    low_bundle = copy.deepcopy(sample_citation_bundle)
    low_bundle.citations = [Citation.from_dict(c_low)]

    res = engine.assess(
        window=sample_window,
        anomaly_score=2.5,
        gate_decision="ESCALATE",
        citation_bundle=low_bundle,
        ablation_mode="sufficiency_disabled",  # Test conflict firing specifically
    )
    assert res.assessment.decision == IncidentDecision.SUSPICIOUS.value
    assert "RULE-CONF-001" in res.assessment.reasoning_trace.rules_fired


def test_rule_precedence_incident_declaration(sample_window, sample_citation_bundle):
    engine = IncidentReasoningEngine()
    res = engine.assess(
        window=sample_window,
        anomaly_score=1.85,
        gate_decision="ESCALATE",
        citation_bundle=sample_citation_bundle,
        b0_score=1.75,
    )
    assert res.assessment.decision == IncidentDecision.INCIDENT.value
    assert res.assessment.severity in ("HIGH", "CRITICAL")
    assert "RULE-INC-001" in res.assessment.reasoning_trace.rules_fired


def test_rule_precedence_normal_auto_clear(sample_window, sample_citation_bundle):
    engine = IncidentReasoningEngine()
    res = engine.assess(
        window=sample_window,
        anomaly_score=0.10,
        gate_decision="AUTO-CLEAR",
        citation_bundle=None,
    )
    assert res.assessment.decision == IncidentDecision.NORMAL.value
    assert res.assessment.severity == IncidentSeverity.LOW.value
    assert "RULE-NORM-001" in res.assessment.reasoning_trace.rules_fired


# -----------------------------------------------------------------------------
# 8. SEVERITY DERIVATION LOGIC
# -----------------------------------------------------------------------------

def test_severity_calculation_critical_on_unknown_template(sample_window, sample_citation_bundle):
    engine = IncidentReasoningEngine()
    win_unknown = copy.deepcopy(sample_window)
    win_unknown.metadata["has_unknown_template"] = True

    res = engine.assess(
        window=win_unknown,
        anomaly_score=1.5,
        gate_decision="ESCALATE",
        citation_bundle=sample_citation_bundle,
    )
    assert res.assessment.decision == IncidentDecision.INCIDENT.value
    assert res.assessment.severity == IncidentSeverity.CRITICAL.value


def test_severity_calculation_low_on_normal(sample_window):
    engine = IncidentReasoningEngine()
    res = engine.assess(
        window=sample_window,
        anomaly_score=0.05,
        gate_decision="AUTO-CLEAR",
    )
    assert res.assessment.severity == IncidentSeverity.LOW.value


# -----------------------------------------------------------------------------
# 9. CONFIDENCE & SUPPORT STRENGTH
# -----------------------------------------------------------------------------

def test_deterministic_confidence_calculation(sample_window, sample_citation_bundle):
    engine = IncidentReasoningEngine()
    res1 = engine.assess(sample_window, 1.85, "ESCALATE", sample_citation_bundle, b0_score=1.5)
    res2 = engine.assess(sample_window, 1.85, "ESCALATE", sample_citation_bundle, b0_score=1.5)

    assert res1.assessment.confidence == res2.assessment.confidence
    assert 0.0 <= res1.assessment.confidence <= 1.0
    # High corroboration should yield high confidence
    assert res1.assessment.confidence >= 0.70


def test_confidence_collapses_on_invalid_provenance(sample_window, sample_citation_bundle):
    engine = IncidentReasoningEngine()
    tampered_bundle = copy.deepcopy(sample_citation_bundle)
    tampered_bundle.all_verified = False

    res = engine.assess(sample_window, 1.85, "ESCALATE", tampered_bundle)
    assert res.assessment.confidence <= 0.10


# -----------------------------------------------------------------------------
# 10. CONFIGURATION HASHING & DETERMINISM
# -----------------------------------------------------------------------------

def test_configuration_hashing_determinism():
    c1 = {"a": 1, "b": [2, 3], "c": {"d": "test"}}
    c2 = {"c": {"d": "test"}, "b": [2, 3], "a": 1}
    h1 = compute_configuration_hash(c1)
    h2 = compute_configuration_hash(c2)
    assert h1 == h2
    assert len(h1) == 64


def test_repeated_run_determinism(sample_window, sample_citation_bundle):
    engine = IncidentReasoningEngine()
    r1 = engine.assess(sample_window, 1.85, "ESCALATE", sample_citation_bundle, b0_score=1.5)
    r2 = engine.assess(sample_window, 1.85, "ESCALATE", sample_citation_bundle, b0_score=1.5)

    assert r1.assessment.to_dict() == r2.assessment.to_dict()
    assert r1.assessment.decision == r2.assessment.decision
    assert r1.assessment.severity == r2.assessment.severity
    assert r1.assessment.confidence == r2.assessment.confidence


# -----------------------------------------------------------------------------
# 11. ABLATION SENSITIVITY
# -----------------------------------------------------------------------------

def test_ablation_relevance_only(sample_window, sample_citation_bundle):
    engine = IncidentReasoningEngine()
    res_orig = engine.assess(sample_window, 1.85, "ESCALATE", sample_citation_bundle)
    res_abl = engine.assess(sample_window, 1.85, "ESCALATE", sample_citation_bundle, ablation_mode="relevance_only")
    assert res_abl.assessment.decision == res_orig.assessment.decision


def test_ablation_conflict_ignored(sample_window, sample_citation_bundle):
    engine = IncidentReasoningEngine()
    # Create conflict condition
    c_low = sample_citation_bundle.citations[0].to_dict()
    c_low["retrieval_score"] = 0.05
    c_low["selection_score"] = 0.05
    low_bundle = copy.deepcopy(sample_citation_bundle)
    low_bundle.citations = [Citation.from_dict(c_low)]

    res_conflict = engine.assess(sample_window, 2.5, "ESCALATE", low_bundle, ablation_mode="sufficiency_disabled")
    res_ignored = engine.assess(sample_window, 2.5, "ESCALATE", low_bundle, ablation_mode="conflict_ignored")

    # Conflict ignored avoids RULE-CONF-001 firing
    assert "RULE-CONF-001" in res_conflict.assessment.reasoning_trace.rules_fired
    assert "RULE-CONF-001" not in res_ignored.assessment.reasoning_trace.rules_fired


# -----------------------------------------------------------------------------
# 12. REGRESSION AGAINST PHASE 7 OUTPUTS
# -----------------------------------------------------------------------------

def test_regression_against_phase7_hdfs_outputs(sample_window, sample_citation_bundle):
    # Verify Phase 7 citation bundle properties are fully preserved
    assert len(sample_citation_bundle.citations) == 3
    assert sample_citation_bundle.all_verified is True
    engine = IncidentReasoningEngine()
    res = engine.assess(sample_window, 1.68, "ESCALATE", sample_citation_bundle, b0_score=1.77)
    assert res.assessment.dataset == "hdfs"
    assert res.assessment.provenance_status == "VERIFIED"
    assert len(res.assessment.citation_ids) == 3
    assert res.assessment.citation_ids == [c.citation_id for c in sample_citation_bundle.citations]


def test_regression_against_phase7_bgl_outputs(bgl_citation_bundle):
    # Verify BGL bundle is processed and correctly flags insufficient evidence due to low corpus relevance
    assert len(bgl_citation_bundle.citations) == 3
    assert bgl_citation_bundle.all_verified is True

    bgl_win = LogWindow(
        dataset="bgl",
        window_id=bgl_citation_bundle.query_id,
        session_id=None,
        start_time=1117838570.0,
        end_time=1117838670.0,
        record_count=100,
        template_ids=[1, 2, 3],
        raw_messages=["msg"],
        is_anomaly=False,
    )

    engine = IncidentReasoningEngine()
    res = engine.assess(bgl_win, 2.99, "ESCALATE", bgl_citation_bundle, b0_score=1.0)
    assert res.assessment.dataset == "bgl"
    assert res.assessment.provenance_status == "VERIFIED"
    assert res.assessment.decision == IncidentDecision.INSUFFICIENT_EVIDENCE.value
