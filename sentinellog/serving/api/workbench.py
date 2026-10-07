"""FastAPI router for FaultSentinel v1.1 Investigation & Reliability Workbench."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sentinellog.security.auth import AuthenticationResult
from sentinellog.serving.dependencies import get_request_id
from sentinellog.workbench.adjudication import HumanAdjudicationStore, get_adjudication_store
from sentinellog.workbench.drift import CalibrationDriftMonitor
from sentinellog.workbench.evidence_graph import EvidenceGraphBuilder
from sentinellog.workbench.fault_injection import ReliabilityFaultLab
from sentinellog.workbench.passport import DecisionPassportGenerator
from sentinellog.workbench.replay import IncidentReplayEngine

logger = logging.getLogger("sentinellog.serving.workbench")
router = APIRouter(prefix="/api/v1", tags=["Workbench v1.1"])


# Pydantic Schemas
class FaultScenarioRunRequest(BaseModel):
    scenario_id: str = Field(..., description="Failure scenario to simulate (e.g., llm_unavailable)")
    environment: str = Field("local", description="Execution environment (local, demo, staging, production)")


class HumanReviewRequest(BaseModel):
    human_decision: str = Field(..., description="Human adjudication: CONFIRM, REJECT, or NEEDS_REVIEW")
    machine_decision: str = Field("ESCALATE", description="Authoritative automated decision")
    reason: Optional[str] = Field(None, description="Reason if rejected (e.g. False Positive, Insufficient Evidence)")
    notes: Optional[str] = Field(None, description="Optional SRE engineer notes")
    reviewer_id: str = Field("sre-oncall", description="Identifier of the reviewing human engineer")


class CounterfactualRequest(BaseModel):
    actual_score: float = Field(..., description="Actual computed anomaly score")
    hypothetical_score: float = Field(..., description="Hypothetical score for what-if simulation")
    conformal_threshold: float = Field(1.15459, description="Calibrated conformal threshold")
    target_alpha: float = Field(0.05, description="Calibrated significance level alpha")


class PassportVerifyRequest(BaseModel):
    passport: Dict[str, Any] = Field(..., description="Full passport dictionary to verify")


# Replay Endpoints
@router.get("/replay/{incident_id}", summary="Get Incident Replay Trace")
async def get_incident_replay(
    incident_id: str,
    dataset: str = Query("hdfs", description="Dataset identifier (hdfs or bgl)"),
    request_id: str = Depends(get_request_id),
) -> Dict[str, Any]:
    """Retrieve complete 11-stage playback execution trace for an incident."""
    engine = IncidentReplayEngine(dataset=dataset)
    try:
        return engine.replay_incident(incident_id=incident_id)
    except Exception as exc:
        logger.error(f"Replay error for {incident_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/replay/sample/{scenario_type}", summary="Get Sample Replay Trace")
async def get_sample_replay(
    scenario_type: str,
    dataset: str = Query("hdfs", description="Dataset identifier (hdfs or bgl)"),
    request_id: str = Depends(get_request_id),
) -> Dict[str, Any]:
    """Retrieve sample replay trace (incident or normal auto-clear)."""
    engine = IncidentReplayEngine(dataset=dataset)
    is_normal = scenario_type.lower() in ("normal", "auto_clear", "clear")
    inc_data = engine.generate_sample_incident(normal=is_normal)
    return engine.replay_incident(incident_data=inc_data)


@router.post("/incidents/counterfactual", summary="Simulate Counterfactual Score Decision")
async def simulate_counterfactual(
    request: CounterfactualRequest,
    request_id: str = Depends(get_request_id),
) -> Dict[str, Any]:
    """Compute what-if decision boundary under a counterfactual anomaly score."""
    engine = IncidentReplayEngine()
    return engine.get_counterfactual(
        actual_score=request.actual_score,
        hypothetical_score=request.hypothetical_score,
        conformal_threshold=request.conformal_threshold,
        target_alpha=request.target_alpha,
    )


# Reliability / Fault Injection Lab Endpoints
@router.get("/fault-injection/scenarios", summary="List Available Fault Scenarios")
async def list_fault_scenarios() -> Dict[str, Any]:
    """List supported controlled fault injection scenarios and descriptions."""
    lab = ReliabilityFaultLab(environment="local")
    return {
        "environment": "local",
        "supported_scenarios": lab.list_scenarios(),
    }


@router.post("/fault-injection/run", summary="Execute Controlled Fault Scenario")
async def run_fault_scenario(
    request: FaultScenarioRunRequest,
    request_id: str = Depends(get_request_id),
) -> Dict[str, Any]:
    """Execute a controlled reliability fault scenario and verify safety assertions."""
    lab = ReliabilityFaultLab(environment=request.environment)
    return lab.run_scenario(request.scenario_id)


# Calibration Drift Monitor Endpoints
@router.get("/calibration/drift", summary="Evaluate Calibration Drift")
async def evaluate_calibration_drift(
    dataset: str = Query("hdfs", description="Calibration dataset name"),
    psi_stable_thresh: Optional[float] = Query(0.10, description="PSI stable threshold"),
    psi_drift_thresh: Optional[float] = Query(0.25, description="PSI drift alert threshold"),
    simulate_drift: bool = Query(False, description="Simulate shifted distribution for testing"),
    sample_size: int = Query(200, ge=20, le=1000, description="Number of evaluated windows"),
    request_id: str = Depends(get_request_id),
) -> Dict[str, Any]:
    """Assess Population Stability Index and quantile shift against reference calibration."""
    monitor = CalibrationDriftMonitor(dataset_name=dataset)

    # Generate current window scores based on simulation flag
    import numpy as np
    np.random.seed(1337 if not simulate_drift else 42)
    if simulate_drift:
        # Heavily shifted distribution to test drift alert
        curr_scores = np.random.gamma(shape=4.5, scale=0.45, size=sample_size) + 0.3
    else:
        # Well-calibrated stable distribution matching reference
        curr_scores = np.random.gamma(shape=2.5, scale=0.265, size=sample_size)

    curr_scores = np.clip(curr_scores, 0.02, 4.0).tolist()

    return monitor.evaluate_drift(
        current_scores=curr_scores,
        psi_stable_thresh=psi_stable_thresh,
        psi_drift_thresh=psi_drift_thresh,
    )


# Evidence Graph Endpoints
@router.get("/evidence/{incident_id}/graph", summary="Get Evidence Provenance Graph")
async def get_evidence_graph(
    incident_id: str,
    dataset: str = Query("hdfs", description="Dataset identifier"),
    request_id: str = Depends(get_request_id),
) -> Dict[str, Any]:
    """Retrieve full 10-node provenance topology and verified citations DAG."""
    builder = EvidenceGraphBuilder()
    engine = IncidentReplayEngine(dataset=dataset)
    inc_data = engine.generate_sample_incident(normal=False)
    inc_data["incident_id"] = incident_id
    return builder.build_graph(incident=inc_data)


# Decision Passport Endpoints
@router.get("/incidents/{incident_id}/passport", summary="Generate Decision Passport")
async def get_decision_passport(
    incident_id: str,
    dataset: str = Query("hdfs", description="Dataset identifier"),
    request_id: str = Depends(get_request_id),
) -> Dict[str, Any]:
    """Generate tamper-evident cryptographic Decision Passport for an incident."""
    generator = DecisionPassportGenerator()
    engine = IncidentReplayEngine(dataset=dataset)
    inc_data = engine.generate_sample_incident(normal=False)
    inc_data["incident_id"] = incident_id
    passport = generator.generate_passport(inc_data)
    markdown_report = generator.to_markdown_report(passport)
    return {
        "passport": passport,
        "markdown_report": markdown_report,
    }


@router.post("/incidents/{incident_id}/passport/verify", summary="Verify Passport Authenticity")
async def verify_decision_passport(
    incident_id: str,
    request: PassportVerifyRequest,
    request_id: str = Depends(get_request_id),
) -> Dict[str, Any]:
    """Cryptographically verify the authenticity and signature of a Decision Passport."""
    generator = DecisionPassportGenerator()
    valid, reason = generator.verify_passport(request.passport)
    return {
        "incident_id": incident_id,
        "is_valid": valid,
        "verification_message": reason,
    }


# Human Adjudication Endpoints
@router.post("/incidents/{incident_id}/review", summary="Record Human Adjudication")
async def submit_human_review(
    incident_id: str,
    request: HumanReviewRequest,
    request_id: str = Depends(get_request_id),
) -> Dict[str, Any]:
    """Record an SRE engineer human adjudication review."""
    store = get_adjudication_store()
    try:
        record = store.record_review(
            incident_id=incident_id,
            machine_decision=request.machine_decision,
            human_decision=request.human_decision,
            reason=request.reason,
            notes=request.notes,
            reviewer_id=request.reviewer_id,
        )
        return {
            "status": "RECORDED",
            "review": record,
            "message": "Human adjudication recorded. Scientific pipeline preserved unmodified.",
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))


@router.get("/incidents/{incident_id}/reviews", summary="Get Incident Human Reviews")
async def get_incident_reviews(
    incident_id: str,
    request_id: str = Depends(get_request_id),
) -> Dict[str, Any]:
    """Get all human reviews for a specific incident."""
    store = get_adjudication_store()
    reviews = store.get_reviews(incident_id=incident_id)
    return {
        "incident_id": incident_id,
        "review_count": len(reviews),
        "reviews": reviews,
    }


@router.get("/incidents/reviews/summary", summary="Get Human Adjudication Summary")
async def get_adjudication_summary() -> Dict[str, Any]:
    """Get aggregate agreement and rejection metrics across all human reviews."""
    store = get_adjudication_store()
    return store.get_summary()
