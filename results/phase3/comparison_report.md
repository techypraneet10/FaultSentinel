# Phase 3 Unsupervised Baselines Comparison Report

> **IMPORTANT GUARDRAIL NOTE**: All metrics reported below are computed strictly on the **CALIBRATION** partition. The **TEST** partition remains completely frozen and was NOT accessed or evaluated, in strict accordance with Rule 1.

## Calibration Diagnostics Summary (Unsupervised Threshold at 95th Percentile)

| Dataset | Baseline | Threshold | Flagged | TP | FP | FN | Precision | Recall | F1 | ROC-AUC | PR-AUC | Oracle F1 (Diag) |
|---------|----------|-----------|---------|----|----|----|-----------|--------|----|---------|--------|------------------|
| HDFS | B0_Frequency | 1.5774 | 26 | 19 | 7 | 10 | 0.7308 | 0.6552 | 0.6909 | 0.8501 | 0.6128 | 0.6909 |
| HDFS | B1_PCA | 0.0000 | 26 | 19 | 7 | 10 | 0.7308 | 0.6552 | 0.6909 | 0.8237 | 0.5433 | 0.7037 |
| HDFS | B1_IsolationForest | 0.4354 | 26 | 19 | 7 | 10 | 0.7308 | 0.6552 | 0.6909 | 0.8221 | 0.4451 | 0.7037 |
| BGL | B0_Frequency | 8.1140 | 5 | 1 | 4 | 35 | 0.2000 | 0.0278 | 0.0488 | 0.9089 | 0.7082 | 0.9231 |
| BGL | B1_PCA | 0.6664 | 5 | 1 | 4 | 35 | 0.2000 | 0.0278 | 0.0488 | 0.2786 | 0.3679 | 0.4151 |
| BGL | B1_IsolationForest | 0.4193 | 5 | 4 | 1 | 32 | 0.8000 | 0.1111 | 0.1951 | 0.9390 | 0.8582 | 0.9231 |

## Key Observations
1. **Unsupervised Thresholding**: Decision thresholds are derived purely as the 95th percentile of calibration scores without using ground-truth labels.
2. **Oracle Comparison**: The oracle F1 represents the theoretical maximum F1 achievable on calibration by searching over candidate thresholds with supervised hindsight.
3. **BGL Slice Context**: In the 50K development slice, BGL has 36 anomalous calibration windows and 0 anomalous test windows. Baselines are evaluated on BGL calibration for behavioral inspection only.
