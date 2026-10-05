"""Calibration package for selective prediction and conformal gate scaffolding."""

from sentinellog.calibration.conformal import SplitConformalCalibrator
from sentinellog.calibration.gate import (
    Decision,
    SelectiveGate,
    evaluate_selective_performance,
    sweep_alpha_grid,
)

__all__ = [
    "SplitConformalCalibrator",
    "Decision",
    "SelectiveGate",
    "evaluate_selective_performance",
    "sweep_alpha_grid",
]
