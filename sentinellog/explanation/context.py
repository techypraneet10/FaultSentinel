"""Context construction engine for Phase 9 LLM Explanation.

Builds bounded, sanitized, and leakage-safe context representations from:
- Phase 8 IncidentAssessment
- Phase 8 ReasoningTrace
- Phase 7 CitationBundle
- Source evidence coordinates and safe text excerpts

Enforces:
- Rule 1 (Test Set Protection)
- Rule 34 (Label Leakage Prevention)
- Context length boundedness
"""

from typing import Any, Dict, List, Optional, Sequence

from sentinellog.explanation.exceptions import InvalidSplitError, LabelLeakageError
from sentinellog.provenance.schemas import Citation, CitationBundle
from sentinellog.reasoning.schemas import IncidentAssessment, ReasoningTrace
from sentinellog.scoring.artifacts import guard_no_test_split

FORBIDDEN_LEAKAGE_KEYS = {
    "is_anomaly",
    "anomaly_label",
    "ground_truth",
    "target",
    "label",
    "test_label",
    "unmapped_label",
}


def scan_for_label_leakage(obj: Any, path: str = "context") -> None:
    """Recursively inspect object to guarantee zero sensitive label leakage."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            k_lower = str(k).lower().strip()
            if k_lower in FORBIDDEN_LEAKAGE_KEYS or k_lower.startswith("hidden_"):
                raise LabelLeakageError(
                    f"Label Leakage Violation: Sensitive field '{k}' detected at '{path}.{k}'."
                )
            scan_for_label_leakage(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for idx, item in enumerate(obj):
            scan_for_label_leakage(item, f"{path}[{idx}]")


class ExplanationContextBuilder:
    """Constructs leakage-safe, bounded prompt context for LLM explanation."""

    def __init__(self, max_excerpt_lines: int = 5, max_excerpt_chars: int = 400):
        self.max_excerpt_lines = max_excerpt_lines
        self.max_excerpt_chars = max_excerpt_chars

    def build_context(
        self,
        assessment: IncidentAssessment,
        citation_bundle: Optional[CitationBundle] = None,
        raw_excerpts: Optional[Dict[str, str]] = None,
        split: str = "calibration",
    ) -> Dict[str, Any]:
        """Construct sanitized context dictionary.
        
        Args:
            assessment: Deterministic Phase 8 assessment.
            citation_bundle: Optional Phase 7 citation bundle.
            raw_excerpts: Optional pre-loaded citation excerpt strings {citation_id: text}.
            split: Target split name (strictly non-test).
            
        Returns:
            Dictionary containing sanitized sections for prompt generation.
        """
        clean_split = split.strip().lower()
        if clean_split == "test":
            raise InvalidSplitError("Rule 1 Violation: Cannot build explanation context for frozen 'test' split.")
        guard_no_test_split(clean_split)

        raw_excerpts = raw_excerpts or {}

        # 1. Assessment Summary
        assessment_summary = {
            "dataset": assessment.dataset,
            "window_id": assessment.window_id,
            "decision": assessment.decision,
            "severity": assessment.severity,
            "confidence": round(assessment.confidence, 4),
            "evidence_sufficiency": assessment.signal_summary.get("evidence_sufficiency", "UNKNOWN"),
            "rules_fired": list(assessment.reasoning_trace.rules_fired),
        }

        # 2. Key Deterministic Signals
        sig_data = assessment.reasoning_trace.signals
        anomaly_val = "N/A"
        if "anomaly_score_strength" in sig_data:
            anomaly_val = round(float(sig_data["anomaly_score_strength"].get("value", 0.0)), 4)
        
        b_agree = "N/A"
        if "baseline_agreement" in sig_data:
            ag_val = sig_data["baseline_agreement"].get("value", {})
            if isinstance(ag_val, dict):
                b_agree = f"agree={ag_val.get('agree')}, B0={ag_val.get('b0', 0):.2f}, B2={ag_val.get('b2', 0):.2f}"

        signals_summary = {
            "anomaly_score": anomaly_val,
            "baseline_agreement": b_agree,
            "evidence_count": len(assessment.citation_ids),
        }

        # 3. Conflicts
        conflicts = [
            {"conflict_id": c.get("conflict_id", "CONF"), "description": c.get("description", "")}
            for c in assessment.reasoning_trace.conflicts
        ]

        # 4. Formatted Citations
        citations_list: List[Dict[str, Any]] = []
        if citation_bundle and citation_bundle.citations:
            for cit in citation_bundle.citations:
                excerpt = raw_excerpts.get(cit.citation_id, "")
                if not excerpt and hasattr(cit, "citation_text"):
                    excerpt = cit.citation_text

                # Bound excerpt length
                lines = excerpt.splitlines()[: self.max_excerpt_lines]
                bounded_excerpt = "\n".join(lines)[: self.max_excerpt_chars]

                loc_dict = cit.provenance.source_location.to_dict() if cit.provenance else {}

                citations_list.append({
                    "citation_id": cit.citation_id,
                    "citation_text": cit.citation_text,
                    "selected_rank": cit.selected_rank,
                    "retrieval_score": round(cit.retrieval_score, 4),
                    "selection_score": round(cit.selection_score, 4),
                    "source_location": loc_dict,
                    "excerpt": bounded_excerpt,
                })

        context = {
            "assessment": assessment_summary,
            "signals": signals_summary,
            "conflicts": conflicts,
            "citations": citations_list,
        }

        # Enforce Rule 34: Label Leakage Scan
        scan_for_label_leakage(context)

        return context
