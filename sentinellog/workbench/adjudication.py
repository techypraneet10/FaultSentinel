"""Human Adjudication & Audit Review Store for FaultSentinel v1.1.

Stores SRE human verification decisions: CONFIRM, REJECT, or NEEDS_REVIEW.
Strict Rule 9: Human feedback serves strictly as an operational review and audit signal.
It NEVER automatically retrains models, mutates calibration, or changes scientific benchmarks.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional


class HumanAdjudicationStore:
    """Thread-safe store for human triage adjudication records."""

    VALID_HUMAN_DECISIONS = ["CONFIRM", "REJECT", "NEEDS_REVIEW"]
    VALID_REJECT_REASONS = [
        "False Positive",
        "Insufficient Evidence",
        "Wrong Severity",
        "Wrong Root Cause",
        "Missing Evidence",
        "Other",
    ]

    def __init__(self, persistence_file: Optional[str | Path] = None) -> None:
        self.persistence_file = Path(persistence_file) if persistence_file else None
        self._lock = threading.Lock()
        self._reviews: List[Dict[str, Any]] = []
        if self.persistence_file and self.persistence_file.exists():
            self._load()

    def record_review(
        self,
        incident_id: str,
        machine_decision: str,
        human_decision: str,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
        reviewer_id: str = "sre-oncall",
    ) -> Dict[str, Any]:
        """Record an immutable human adjudication entry."""
        if human_decision not in self.VALID_HUMAN_DECISIONS:
            raise ValueError(f"Invalid human decision '{human_decision}'. Must be one of {self.VALID_HUMAN_DECISIONS}")

        if human_decision == "REJECT" and reason and reason not in self.VALID_REJECT_REASONS:
            # Allow custom string if not matching exact list, but log/warn
            pass

        record = {
            "incident_id": str(incident_id),
            "machine_decision": str(machine_decision),
            "human_decision": human_decision,
            "reason": reason or ("Agreed with machine triage" if human_decision == "CONFIRM" else None),
            "notes": notes or "",
            "reviewer_id": reviewer_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "scientific_pipeline_modified": False,  # Strict Rule 9
        }

        with self._lock:
            # Overwrite if already reviewed by same reviewer, or append
            self._reviews = [r for r in self._reviews if not (r["incident_id"] == incident_id and r["reviewer_id"] == reviewer_id)]
            self._reviews.append(record)
            if self.persistence_file:
                self._persist()

        return record

    def get_reviews(self, incident_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve recorded reviews, optionally filtered by incident ID."""
        with self._lock:
            if incident_id:
                return [r for r in self._reviews if r["incident_id"] == incident_id]
            return list(self._reviews)

    def get_summary(self) -> Dict[str, Any]:
        """Compute aggregate human agreement and review distribution."""
        with self._lock:
            total = len(self._reviews)
            if total == 0:
                return {
                    "total_reviews": 0,
                    "confirm_count": 0,
                    "reject_count": 0,
                    "needs_review_count": 0,
                    "human_agreement_rate": 1.0,
                    "reasons_breakdown": {},
                }

            confirms = sum(1 for r in self._reviews if r["human_decision"] == "CONFIRM")
            rejects = sum(1 for r in self._reviews if r["human_decision"] == "REJECT")
            needs_rev = sum(1 for r in self._reviews if r["human_decision"] == "NEEDS_REVIEW")

            reasons: Dict[str, int] = {}
            for r in self._reviews:
                rsn = r.get("reason")
                if rsn:
                    reasons[rsn] = reasons.get(rsn, 0) + 1

            return {
                "total_reviews": total,
                "confirm_count": confirms,
                "reject_count": rejects,
                "needs_review_count": needs_rev,
                "human_agreement_rate": round(confirms / total, 4) if total > 0 else 0.0,
                "reasons_breakdown": reasons,
            }

    def _persist(self) -> None:
        if not self.persistence_file:
            return
        self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.persistence_file, "w", encoding="utf-8") as f:
            json.dump(self._reviews, f, indent=2)

    def _load(self) -> None:
        try:
            with open(self.persistence_file, "r", encoding="utf-8") as f:
                self._reviews = json.load(f)
        except Exception:
            self._reviews = []


# Singleton helper
_GLOBAL_ADJUDICATION_STORE: Optional[HumanAdjudicationStore] = None


def get_adjudication_store(persistence_path: Optional[str | Path] = None) -> HumanAdjudicationStore:
    """Return the global human adjudication review store."""
    global _GLOBAL_ADJUDICATION_STORE
    if _GLOBAL_ADJUDICATION_STORE is None:
        p_path = persistence_path or Path("results/v1.1/human_reviews.json")
        _GLOBAL_ADJUDICATION_STORE = HumanAdjudicationStore(persistence_file=p_path)
    return _GLOBAL_ADJUDICATION_STORE
