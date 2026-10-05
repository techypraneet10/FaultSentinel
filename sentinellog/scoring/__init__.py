"""SentinelLog Scoring Package.

Provides unsupervised anomaly detection baselines:
- FrequencyScorer (B0)
- PCAScorer (B1 Primary)
- IsolationForestScorer (B1 Secondary)
- TemplateCountVectorizer
- Quantile thresholding and calibration diagnostics
- Artifact management and test set protection guards
"""

from sentinellog.scoring.features import TemplateCountVectorizer
from sentinellog.scoring.b0 import FrequencyScorer
from sentinellog.scoring.b1 import PCAScorer, IsolationForestScorer
from sentinellog.scoring.thresholds import (
    compute_unsupervised_threshold,
    compute_oracle_threshold,
    evaluate_calibration_diagnostics,
)
from sentinellog.scoring.artifacts import (
    TestAccessViolationError,
    guard_no_test_split,
    save_model_artifact,
    load_model_artifact,
    save_experiment_manifest,
    save_diagnostics,
)

__all__ = [
    "TemplateCountVectorizer",
    "FrequencyScorer",
    "PCAScorer",
    "IsolationForestScorer",
    "compute_unsupervised_threshold",
    "compute_oracle_threshold",
    "evaluate_calibration_diagnostics",
    "TestAccessViolationError",
    "guard_no_test_split",
    "save_model_artifact",
    "load_model_artifact",
    "save_experiment_manifest",
    "save_diagnostics",
]
