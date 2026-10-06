"""Evaluation package for SentinelLog benchmarks and metrics."""

from sentinellog.evaluation.cost import CostAccounting, evaluate_cost_model
from sentinellog.evaluation.evaluator import Phase12Evaluator
from sentinellog.evaluation.leakage import TestMutationViolationError, audit_corpus_leakage
from sentinellog.evaluation.metrics import (
    ClassificationMetrics,
    SelectiveMetrics,
    compute_classification_metrics,
    compute_pr_auc,
    compute_roc_auc,
    compute_selective_metrics,
)
from sentinellog.evaluation.statistics import mcnemar_test, wilson_score_interval

__all__ = [
    "ClassificationMetrics",
    "SelectiveMetrics",
    "CostAccounting",
    "compute_classification_metrics",
    "compute_selective_metrics",
    "compute_pr_auc",
    "compute_roc_auc",
    "wilson_score_interval",
    "mcnemar_test",
    "evaluate_cost_model",
    "audit_corpus_leakage",
    "TestMutationViolationError",
    "Phase12Evaluator",
]
