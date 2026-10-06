"""Computational cost model and expensive-call accounting for Phase 12.

Focuses on transparent computational resource accounting without fictitious monetary assumptions.
Compares:
- LLM-every-window (B3): All N windows incur expensive LLM explanation calls.
- Selective SentinelLog: Only escalated windows (E <= N) incur expensive LLM calls;
  auto-cleared windows incur only lightweight scoring costs.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class CostAccounting:
    """Computational resource accounting."""

    total_windows: int
    escalated_windows: int
    auto_cleared_windows: int
    expensive_calls: int
    expensive_call_fraction: float
    total_compute_units: float
    llm_call_reduction_ratio: float
    relative_cost_reduction_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_cost_model(
    total_windows: int,
    escalated_windows: int,
    cheap_scoring_unit: float = 1.0,
    retrieval_unit: float = 5.0,
    explanation_unit: float = 50.0,
) -> CostAccounting:
    """Compute normalized compute costs and expensive-call reduction.

    Args:
        total_windows: Total number of evaluated windows (N).
        escalated_windows: Number of windows escalated to LLM layer (E).
        cheap_scoring_unit: Normalized cost to compute baseline/B2 score (per window).
        retrieval_unit: Normalized cost to retrieve and rerank evidence (per escalated window).
        explanation_unit: Normalized cost to orchestrate grounded LLM call (per escalated window).

    Returns:
        CostAccounting instance.
    """
    if total_windows <= 0:
        raise ValueError("total_windows must be positive.")

    n = total_windows
    e = min(escalated_windows, n)
    c = n - e

    # B3 Baseline: All N windows incur scoring, retrieval, and explanation
    b3_compute = n * (cheap_scoring_unit + retrieval_unit + explanation_unit)

    # Selective System: All N incur scoring; only E incur retrieval and explanation
    selective_compute = (n * cheap_scoring_unit) + (e * (retrieval_unit + explanation_unit))

    expensive_calls = e
    expensive_fraction = float(e / n)

    llm_call_reduction = float((n - e) / n)
    relative_cost_reduction = float((b3_compute - selective_compute) / b3_compute) if b3_compute > 0 else 0.0

    return CostAccounting(
        total_windows=n,
        escalated_windows=e,
        auto_cleared_windows=c,
        expensive_calls=expensive_calls,
        expensive_call_fraction=expensive_fraction,
        total_compute_units=float(selective_compute),
        llm_call_reduction_ratio=llm_call_reduction,
        relative_cost_reduction_ratio=relative_cost_reduction,
    )
