"""Comprehensive test suite for FaultSentinel v1.1 Investigation & Reliability Workbench.

Validates all 5 primary v1.1 features plus human adjudication, security RBAC, and safety invariants:
- Feature 1: Incident Replay Lab (10 tests)
- Feature 2: Reliability & Fault Injection Lab (15 tests)
- Feature 3: Calibration Drift Monitor (10 tests)
- Feature 4: Evidence Graph & Provenance DAG (10 tests)
- Feature 5: Decision Passport & Cryptographic Auditing (8 tests)
- Human Adjudication Store (7 tests)
- Workbench Security & RBAC Controls (10 tests)
Total: 70 comprehensive tests.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from sentinellog.security.auth import authenticate_request, authorize_request
from sentinellog.security.config import SecurityConfig, reset_security_config
from sentinellog.serving.app import create_app
from sentinellog.workbench.adjudication import HumanAdjudicationStore
from sentinellog.workbench.drift import CalibrationDriftMonitor
from sentinellog.workbench.evidence_graph import EvidenceGraphBuilder
from sentinellog.workbench.fault_injection import ReliabilityFaultLab
from sentinellog.workbench.passport import DecisionPassportGenerator
from sentinellog.workbench.replay import IncidentReplayEngine


# -----------------------------------------------------------------------------
# FEATURE 1: INCIDENT REPLAY LAB (10 tests)
# -----------------------------------------------------------------------------
class TestIncidentReplayLab:
    @pytest.fixture
    def engine(self):
        return IncidentReplayEngine(dataset="hdfs")

    def test_replay_contains_all_11_stages(self, engine):
        res = engine.replay_incident()
        assert "stages" in res
        assert len(res["stages"]) == 11

    def test_stages_are_chronologically_ordered(self, engine):
        res = engine.replay_incident()
        orders = [s["order"] for s in res["stages"]]
        assert orders == list(range(1, 12))

    def test_stage_metadata_attributes_present(self, engine):
        res = engine.replay_incident()
        for stage in res["stages"]:
            assert "stage_id" in stage
            assert "stage_name" in stage
            assert "implementation" in stage
            assert "dependencies" in stage
            assert "failure_mode" in stage
            assert "inputs" in stage
            assert "outputs" in stage
            assert "latency_ms" in stage

    def test_auto_clear_skips_downstream_stages(self, engine):
        normal_data = engine.generate_sample_incident(normal=True)
        res = engine.replay_incident(incident_data=normal_data)
        assert res["incident_summary"]["conformal_decision"] == "AUTO_CLEAR"

        # Stages 6 (Retrieve) through 11 (Verify) should be skipped
        stage_map = {s["order"]: s for s in res["stages"]}
        assert stage_map[6]["skipped"] is True
        assert stage_map[10]["skipped"] is True
        assert stage_map[11]["skipped"] is True

    def test_escalated_incident_executes_all_stages(self, engine):
        inc_data = engine.generate_sample_incident(normal=False)
        res = engine.replay_incident(incident_data=inc_data)
        assert res["incident_summary"]["conformal_decision"] == "ESCALATE"
        for s in res["stages"]:
            assert s["skipped"] is False

    def test_analytical_synthesis_fields(self, engine):
        res = engine.replay_incident()
        synth = res["analytical_synthesis"]
        assert "why_escalated" in synth
        assert "why_decision" in synth
        assert "why_faithfulness" in synth
        assert len(synth["why_escalated"]) > 10

    def test_counterfactual_score_below_threshold_clears(self, engine):
        cf = engine.get_counterfactual(
            actual_score=1.37,
            hypothetical_score=0.85,
            conformal_threshold=1.15459,
            target_alpha=0.05,
        )
        assert cf["hypothetical_decision"] == "AUTO_CLEAR"
        assert cf["decision_changed"] is True
        assert cf["is_counterfactual"] is True

    def test_counterfactual_score_above_threshold_escalates(self, engine):
        cf = engine.get_counterfactual(
            actual_score=1.37,
            hypothetical_score=1.45,
            conformal_threshold=1.15459,
            target_alpha=0.05,
        )
        assert cf["hypothetical_decision"] == "ESCALATE"
        assert cf["decision_changed"] is False
        assert cf["is_counterfactual"] is True

    def test_counterfactual_labels_strictly_marked(self, engine):
        cf = engine.get_counterfactual(1.2, 0.5)
        assert cf["audit_notice"] == "COUNTERFACTUAL SIMULATION ONLY — DOES NOT ALTER PRODUCTION TRIAGE"

    def test_replay_total_latency_is_sum_of_stages(self, engine):
        res = engine.replay_incident()
        computed_sum = sum(s["latency_ms"] for s in res["stages"] if not s["skipped"])
        assert res["total_latency_ms"] == round(computed_sum, 2)
        assert res["total_latency_ms"] > 0


# -----------------------------------------------------------------------------
# FEATURE 2: RELIABILITY & FAULT INJECTION LAB (15 tests)
# -----------------------------------------------------------------------------
class TestReliabilityFaultLab:
    def test_list_scenarios_returns_9_scenarios(self):
        lab = ReliabilityFaultLab(environment="local")
        scenarios = lab.list_scenarios()
        assert len(scenarios) == 9

    def test_production_environment_locks_fault_injection(self):
        lab = ReliabilityFaultLab(environment="production")
        res = lab.run_scenario("llm_unavailable")
        assert res["status"] == "DISABLED_IN_PRODUCTION"
        assert res["safe"] is True
        assert "production" in res["message"].lower()

    def test_staging_environment_permits_execution(self):
        lab = ReliabilityFaultLab(environment="staging")
        res = lab.run_scenario("llm_unavailable")
        assert res["status"] == "PASS"
        assert res["safe"] is True

    def test_demo_environment_permits_execution(self):
        lab = ReliabilityFaultLab(environment="demo")
        res = lab.run_scenario("llm_unavailable")
        assert res["status"] == "PASS"

    def test_local_environment_permits_execution(self):
        lab = ReliabilityFaultLab(environment="local")
        res = lab.run_scenario("llm_unavailable")
        assert res["status"] == "PASS"

    def test_scenario_llm_unavailable_preserves_deterministic_reasoning(self):
        lab = ReliabilityFaultLab(environment="local")
        res = lab.run_scenario("llm_unavailable")
        assert res["status"] == "PASS"
        assert res["target_component"] == "ExplanationOrchestrator"
        assertions = {a["name"]: a["passed"] for a in res["assertions"]}
        assert assertions["deterministic_reasoning_authoritative"] is True
        assert assertions["safe_fallback_explanation"] is True

    def test_scenario_retrieval_unavailable_triggers_insufficient_evidence(self):
        lab = ReliabilityFaultLab(environment="local")
        res = lab.run_scenario("retrieval_unavailable")
        assert res["status"] == "PASS"
        assertions = {a["name"]: a["passed"] for a in res["assertions"]}
        assert assertions["insufficient_evidence_triggered"] is True
        assert assertions["no_fabricated_root_cause"] is True

    def test_scenario_invalid_log_input_returns_422(self):
        lab = ReliabilityFaultLab(environment="local")
        res = lab.run_scenario("invalid_log_input")
        assert res["status"] == "PASS"
        assertions = {a["name"]: a["passed"] for a in res["assertions"]}
        assert assertions["http_422_status_code"] is True
        assert assertions["no_stack_trace_leak"] is True

    def test_scenario_parser_failure_handles_malformed_json(self):
        lab = ReliabilityFaultLab(environment="local")
        res = lab.run_scenario("parser_failure")
        assert res["status"] == "PASS"
        assertions = {a["name"]: a["passed"] for a in res["assertions"]}
        assert assertions["http_422_status_code"] is True

    def test_scenario_faithfulness_failure_flags_unsupported(self):
        lab = ReliabilityFaultLab(environment="local")
        res = lab.run_scenario("faithfulness_failure")
        assert res["status"] == "PASS"
        assertions = {a["name"]: a["passed"] for a in res["assertions"]}
        assert assertions["grounding_failed_detected"] is True
        assert assertions["fallback_explanation_rendered"] is True

    def test_scenario_invalid_auth_returns_401(self):
        lab = ReliabilityFaultLab(environment="local")
        res = lab.run_scenario("invalid_auth")
        assert res["status"] == "PASS"
        assertions = {a["name"]: a["passed"] for a in res["assertions"]}
        assert assertions["http_401_returned"] is True
        assert assertions["error_code_authentication_required"] is True

    def test_scenario_invalid_authz_returns_403(self):
        lab = ReliabilityFaultLab(environment="local")
        res = lab.run_scenario("invalid_authz")
        assert res["status"] == "PASS"
        assertions = {a["name"]: a["passed"] for a in res["assertions"]}
        assert assertions["http_403_returned"] is True
        assert assertions["error_code_forbidden"] is True

    def test_scenario_config_failure_catches_invalid_alpha(self):
        lab = ReliabilityFaultLab(environment="local")
        res = lab.run_scenario("config_failure")
        assert res["status"] == "PASS"
        assertions = {a["name"]: a["passed"] for a in res["assertions"]}
        assert assertions["validation_error_raised"] is True

    def test_scenario_timeout_simulation_preserves_sla(self):
        lab = ReliabilityFaultLab(environment="local")
        res = lab.run_scenario("timeout_simulation")
        assert res["status"] == "PASS"
        assertions = {a["name"]: a["passed"] for a in res["assertions"]}
        assert assertions["graceful_timeout_handling"] is True

    def test_run_all_scenarios_produces_clean_failure_matrix(self):
        lab = ReliabilityFaultLab(environment="local")
        matrix = lab.run_all_scenarios()
        assert len(matrix) == 9
        for item in matrix:
            assert item["status"] in ("PASS", "FAIL", "NOT_SUPPORTED")


# -----------------------------------------------------------------------------
# FEATURE 3: CALIBRATION DRIFT MONITOR (10 tests)
# -----------------------------------------------------------------------------
class TestCalibrationDriftMonitor:
    @pytest.fixture
    def monitor(self):
        return CalibrationDriftMonitor(dataset_name="hdfs")

    def test_reference_distribution_loaded(self, monitor):
        assert len(monitor.reference_scores) > 0
        assert monitor.reference_threshold is not None
        assert abs(monitor.reference_threshold - 1.15459) < 0.01

    def test_insufficient_data_when_sample_under_20(self, monitor):
        small_sample = [0.5, 0.6, 0.7]
        res = monitor.evaluate_drift(small_sample)
        assert res["drift_status"] == "INSUFFICIENT DATA"
        assert res["review_required"] is False

    def test_stable_distribution_evaluates_stable(self, monitor):
        # Sample drawn from identical distribution as reference
        import numpy as np
        np.random.seed(42)
        sample = np.random.choice(monitor.reference_scores, 200, replace=True).tolist()
        res = monitor.evaluate_drift(sample)
        assert res["drift_status"] in ("STABLE", "WATCH")
        assert res["metrics"]["population_stability_index"] < 0.25

    def test_shifted_distribution_triggers_drift_alert(self, monitor):
        # Strongly shifted distribution (mean ~2.5)
        import numpy as np
        shifted = (np.random.gamma(shape=4.5, scale=0.45, size=200) + 1.0).tolist()
        res = monitor.evaluate_drift(shifted)
        assert res["drift_status"] == "DRIFT DETECTED"
        assert res["review_required"] is True
        assert res["recommendation"] == "CALIBRATION REVIEW REQUIRED"

    def test_psi_computation_returns_non_negative_value(self, monitor):
        import numpy as np
        scores = np.random.uniform(0.1, 2.0, 100).tolist()
        psi, bins = monitor.compute_psi(scores, num_bins=10)
        assert psi >= 0.0
        assert len(bins) > 0

    def test_quantile_shifts_computed_correctly(self, monitor):
        import numpy as np
        scores = np.random.gamma(shape=2.5, scale=0.265, size=150).tolist()
        res = monitor.evaluate_drift(scores)
        qs = res["quantile_shifts"]
        for p in ("p25", "p50", "p75", "p90", "p99"):
            assert p in qs

    def test_escalation_rate_metrics_calculated(self, monitor):
        import numpy as np
        scores = np.random.uniform(0.1, 2.0, 100).tolist()
        res = monitor.evaluate_drift(scores)
        m = res["metrics"]
        assert "current_escalation_rate" in m
        assert "reference_escalation_rate" in m
        assert "escalation_rate_delta" in m

    def test_rule_25_auto_recalibration_never_permitted(self, monitor):
        import numpy as np
        shifted = (np.random.gamma(shape=5.0, scale=0.5, size=200) + 2.0).tolist()
        res = monitor.evaluate_drift(shifted)
        assert res["auto_recalibration_allowed"] is False

    def test_suggested_review_workflow_contains_8_steps(self, monitor):
        import numpy as np
        shifted = [2.5] * 50
        res = monitor.evaluate_drift(shifted)
        wf = res["suggested_review_workflow"]
        assert len(wf) == 8
        assert "1. Inspect drift" in wf[0]

    def test_histogram_data_generation_for_ui(self, monitor):
        import numpy as np
        scores = np.random.uniform(0.1, 2.0, 100).tolist()
        res = monitor.evaluate_drift(scores)
        hist = res["histogram"]
        assert len(hist) > 0
        for bar in hist:
            assert "range" in bar
            assert "reference_density" in bar
            assert "current_density" in bar
            assert "status_color" in bar


# -----------------------------------------------------------------------------
# FEATURE 4: EVIDENCE GRAPH & PROVENANCE DAG (10 tests)
# -----------------------------------------------------------------------------
class TestEvidenceGraphBuilder:
    @pytest.fixture
    def builder(self):
        return EvidenceGraphBuilder()

    def test_builds_graph_with_valid_node_types(self, builder):
        graph = builder.build_graph()
        node_types = {n["type"] for n in graph["nodes"]}
        for t in node_types:
            assert t in builder.VALID_NODE_TYPES

    def test_graph_contains_expected_nodes(self, builder):
        graph = builder.build_graph()
        node_types = {n["type"] for n in graph["nodes"]}
        expected = {"Incident", "Window", "Score", "Decision", "Retrieved Chunk", "Evidence", "Provenance", "Reasoning Claim", "LLM Claim", "Citation", "Source Log"}
        assert expected.issubset(node_types)

    def test_all_edges_connect_existing_nodes(self, builder):
        graph = builder.build_graph()
        node_ids = {n["id"] for n in graph["nodes"]}
        for edge in graph["edges"]:
            assert edge["source"] in node_ids
            assert edge["target"] in node_ids

    def test_auto_clear_generates_compact_graph(self, builder):
        auto_clear_incident = {
            "incident_id": "inc_normal",
            "anomaly_score": 0.42,
            "conformal_threshold": 1.15459,
            "escalate": False,
            "evidence": [],
        }
        graph = builder.build_graph(incident=auto_clear_incident)
        node_types = {n["type"] for n in graph["nodes"]}
        assert "Incident" in node_types
        assert "Decision" in node_types
        # Auto-clear should NOT trigger retrieval or LLM
        assert "Retrieved Chunk" not in node_types
        assert "LLM Claim" not in node_types

    def test_nodes_contain_deterministic_hashes(self, builder):
        graph = builder.build_graph()
        for node in graph["nodes"]:
            assert "hash" in node
            assert len(node["hash"]) >= 8

    def test_citation_nodes_contain_provenance_metadata(self, builder):
        graph = builder.build_graph()
        citation_nodes = [n for n in graph["nodes"] if n["type"] == "Citation"]
        assert len(citation_nodes) > 0
        for cn in citation_nodes:
            d = cn["data"]
            assert "citation_id" in d
            assert "source_window" in d
            assert "line_range" in d

    def test_source_log_nodes_link_to_train_split(self, builder):
        graph = builder.build_graph()
        src_nodes = [n for n in graph["nodes"] if n["type"] == "Source Log"]
        assert len(src_nodes) > 0
        for sn in src_nodes:
            assert "train" in sn["data"]["file"]

    def test_llm_claim_nodes_contain_grounding_status(self, builder):
        graph = builder.build_graph()
        llm_nodes = [n for n in graph["nodes"] if n["type"] == "LLM Claim"]
        assert len(llm_nodes) > 0
        for ln in llm_nodes:
            assert "verification_status" in ln["data"]
            assert "claim_text" in ln["data"]

    def test_edge_relationship_labels_are_meaningful(self, builder):
        graph = builder.build_graph()
        labels = {e["label"] for e in graph["edges"]}
        assert "evaluates" in labels
        assert "computes_signal" in labels
        assert "gates_through" in labels

    def test_graph_integrity_marker_is_present(self, builder):
        graph = builder.build_graph()
        assert graph["integrity"] == "PROVENANCE_TRACEABLE"


# -----------------------------------------------------------------------------
# FEATURE 5: DECISION PASSPORT (8 tests)
# -----------------------------------------------------------------------------
class TestDecisionPassport:
    @pytest.fixture
    def generator(self):
        return DecisionPassportGenerator(git_commit="e84b5cd3")

    @pytest.fixture
    def sample_incident(self):
        return {
            "incident_id": "inc_test_101",
            "dataset": "hdfs",
            "window_id": "hdfs_win_101",
            "anomaly_score": 1.45,
            "conformal_alpha": 0.05,
            "conformal_threshold": 1.15459,
            "final_decision": "ESCALATE",
            "severity": "CRITICAL",
            "faithfulness_status": "VERIFIED",
        }

    def test_passport_contains_all_23_fields(self, generator, sample_incident):
        p = generator.generate_passport(sample_incident)
        required = [
            "faultsentinel_version", "pipeline_version", "status", "incident_id",
            "dataset", "window_id", "timestamp", "anomaly_score", "calibration_alpha",
            "threshold", "conformal_decision", "final_decision", "severity",
            "escalation_state", "retrieval_count", "mmr_evidence_count", "citation_count",
            "faithfulness_status", "llm_invocation", "git_commit", "configuration_hash",
            "evidence_hash", "decision_hash", "generation_timestamp",
        ]
        for field in required:
            assert field in p, f"Missing field {field}"

    def test_passport_status_is_verified_on_clean_incident(self, generator, sample_incident):
        p = generator.generate_passport(sample_incident)
        assert p["status"] == "VERIFIED"

    def test_passport_status_requires_review_on_unverified_faithfulness(self, generator, sample_incident):
        sample_incident["faithfulness_status"] = "UNSUPPORTED"
        p = generator.generate_passport(sample_incident)
        assert p["status"] == "REVIEW REQUIRED"

    def test_decision_hash_is_valid_sha256(self, generator, sample_incident):
        p = generator.generate_passport(sample_incident)
        assert len(p["decision_hash"]) == 64

    def test_verify_passport_passes_for_untampered_passport(self, generator, sample_incident):
        p = generator.generate_passport(sample_incident)
        is_valid, msg = generator.verify_passport(p)
        assert is_valid is True
        assert "verified valid" in msg

    def test_verify_passport_detects_tampered_score(self, generator, sample_incident):
        p = generator.generate_passport(sample_incident)
        tampered = dict(p)
        tampered["anomaly_score"] = 0.12  # Tampered score
        is_valid, msg = generator.verify_passport(tampered)
        assert is_valid is False
        assert "mismatch" in msg

    def test_verify_passport_detects_tampered_decision(self, generator, sample_incident):
        p = generator.generate_passport(sample_incident)
        tampered = dict(p)
        tampered["final_decision"] = "AUTO_CLEAR"  # Tampered decision
        is_valid, msg = generator.verify_passport(tampered)
        assert is_valid is False

    def test_to_markdown_report_generates_valid_report(self, generator, sample_incident):
        p = generator.generate_passport(sample_incident)
        report = generator.to_markdown_report(p)
        assert "# FAULTSENTINEL DECISION PASSPORT" in report
        assert p["decision_hash"][:16] in report
        assert p["incident_id"] in report


# -----------------------------------------------------------------------------
# HUMAN ADJUDICATION STORE (7 tests)
# -----------------------------------------------------------------------------
class TestHumanAdjudication:
    @pytest.fixture
    def store(self):
        return HumanAdjudicationStore()

    def test_records_confirm_review(self, store):
        rec = store.record_review(
            incident_id="inc_001",
            machine_decision="ESCALATE",
            human_decision="CONFIRM",
            reviewer_id="sre_alice",
        )
        assert rec["human_decision"] == "CONFIRM"
        assert rec["reviewer_id"] == "sre_alice"
        assert rec["scientific_pipeline_modified"] is False

    def test_records_reject_review_with_valid_reason(self, store):
        rec = store.record_review(
            incident_id="inc_002",
            machine_decision="ESCALATE",
            human_decision="REJECT",
            reason="False Positive",
            reviewer_id="sre_bob",
        )
        assert rec["human_decision"] == "REJECT"
        assert rec["reason"] == "False Positive"

    def test_invalid_decision_raises_value_error(self, store):
        with pytest.raises(ValueError):
            store.record_review(
                incident_id="inc_003",
                machine_decision="ESCALATE",
                human_decision="INVALID_CHOICE",
            )

    def test_get_reviews_filters_by_incident_id(self, store):
        store.record_review("inc_A", "ESCALATE", "CONFIRM")
        store.record_review("inc_B", "ESCALATE", "CONFIRM")
        revs = store.get_reviews(incident_id="inc_A")
        assert len(revs) == 1
        assert revs[0]["incident_id"] == "inc_A"

    def test_summary_computes_agreement_rate(self, store):
        store.record_review("inc_1", "ESCALATE", "CONFIRM", reviewer_id="rev_1")
        store.record_review("inc_2", "ESCALATE", "CONFIRM", reviewer_id="rev_2")
        store.record_review("inc_3", "ESCALATE", "REJECT", reason="False Positive", reviewer_id="rev_3")
        summary = store.get_summary()
        assert summary["total_reviews"] == 3
        assert summary["confirm_count"] == 2
        assert summary["reject_count"] == 1
        assert abs(summary["human_agreement_rate"] - 0.6667) < 0.01

    def test_summary_tallies_reasons_breakdown(self, store):
        store.record_review("inc_1", "ESCALATE", "REJECT", reason="False Positive", reviewer_id="rev_1")
        store.record_review("inc_2", "ESCALATE", "REJECT", reason="False Positive", reviewer_id="rev_2")
        store.record_review("inc_3", "ESCALATE", "REJECT", reason="Wrong Severity", reviewer_id="rev_3")
        summary = store.get_summary()
        assert summary["reasons_breakdown"]["False Positive"] == 2
        assert summary["reasons_breakdown"]["Wrong Severity"] == 1

    def test_rule_9_safety_invariant_audit_only(self, store):
        rec = store.record_review("inc_4", "ESCALATE", "REJECT", reason="Wrong Root Cause")
        assert rec["scientific_pipeline_modified"] is False


# -----------------------------------------------------------------------------
# WORKBENCH SECURITY & RBAC CONTROLS (10 tests)
# -----------------------------------------------------------------------------
class TestWorkbenchSecurity:
    @pytest.fixture(autouse=True)
    def setup_security(self):
        reset_security_config(
            SecurityConfig(
                auth_enabled=True,
                api_key="secret-admin-key-123456",
                analyst_api_key="secret-analyst-key-123456",
                operator_api_key="secret-operator-key-123456",
            )
        )
        yield
        reset_security_config()

    @pytest.fixture
    def client(self):
        app = create_app()
        return TestClient(app)

    def test_unauthenticated_request_to_replay_returns_401(self, client):
        resp = client.get("/api/v1/replay/inc_001")
        assert resp.status_code == 401

    def test_unauthenticated_request_to_fault_injection_returns_401(self, client):
        resp = client.post("/api/v1/fault-injection/run", json={"scenario_id": "llm_unavailable"})
        assert resp.status_code == 401

    def test_unauthenticated_request_to_calibration_returns_401(self, client):
        resp = client.get("/api/v1/calibration/drift")
        assert resp.status_code == 401

    def test_unauthenticated_request_to_evidence_graph_returns_401(self, client):
        resp = client.get("/api/v1/evidence/inc_001/graph")
        assert resp.status_code == 401

    def test_analyst_role_permitted_for_replay(self, client):
        resp = client.get("/api/v1/replay/inc_001", headers={"Authorization": "Bearer secret-analyst-key-123456"})
        assert resp.status_code == 200

    def test_analyst_role_permitted_for_evidence_graph(self, client):
        resp = client.get("/api/v1/evidence/inc_001/graph", headers={"Authorization": "Bearer secret-analyst-key-123456"})
        assert resp.status_code == 200

    def test_analyst_role_denied_for_fault_injection(self, client):
        resp = client.post(
            "/api/v1/fault-injection/run",
            json={"scenario_id": "llm_unavailable"},
            headers={"Authorization": "Bearer secret-analyst-key-123456"},
        )
        assert resp.status_code == 403

    def test_operator_role_permitted_for_fault_injection(self, client):
        resp = client.post(
            "/api/v1/fault-injection/run",
            json={"scenario_id": "llm_unavailable"},
            headers={"Authorization": "Bearer secret-operator-key-123456"},
        )
        assert resp.status_code == 200

    def test_admin_role_permitted_for_all_workbench_endpoints(self, client):
        headers = {"Authorization": "Bearer secret-admin-key-123456"}
        r1 = client.get("/api/v1/replay/inc_001", headers=headers)
        assert r1.status_code == 200
        r2 = client.get("/api/v1/calibration/drift", headers=headers)
        assert r2.status_code == 200

    def test_role_authorization_logic_helper(self):
        authz_admin, _ = authorize_request("admin", "/api/v1/fault-injection/run")
        assert authz_admin is True

        authz_operator, _ = authorize_request("operator", "/api/v1/fault-injection/run")
        assert authz_operator is True

        authz_analyst, _ = authorize_request("analyst", "/api/v1/fault-injection/run")
        assert authz_analyst is False
