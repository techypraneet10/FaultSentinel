# Phase 4: Learned Sequential Scorer + Conformal Selective Gate Report

> **RESEARCH INTEGRITY GUARDRAIL**: All results are derived exclusively from **TRAIN** and **CALIBRATION** partitions. The **TEST** partition remains strictly **FROZEN** under Rule 1.

## Dataset: HDFS

- **Architecture**: Sequential GRU (Embedding: 32, Hidden: 64, Layers: 1)
- **Trainable Parameters**: 20,562 (Constraint: < 2,000,000)
- **Training Epochs**: 20 (Best Val Loss: 0.4632 at epoch 20)
- **Calibration Sample Size ($n$)**: 814

### Target Alpha Sweep (Split Conformal Calibration)

| Nominal $\alpha$ | Threshold $\hat{\tau}_\alpha$ | Escalated | Coverage | Escalation Precision | Escalation Recall | False Clears | Selective Risk | Empirical Miscoverage | Deviation |
|---|---|---|---|---|---|---|---|---|---|
| 0.01 | 1.6723 | 7 (0.9%) | 99.1% | 0.8571 | 0.2069 | 23 | 0.0285 | 0.0283 | +0.0183 |
| 0.05 | 1.1546 | 39 (4.8%) | 95.2% | 0.1795 | 0.2414 | 22 | 0.0284 | 0.0270 | -0.0230 |
| 0.10 | 0.9766 | 79 (9.7%) | 90.3% | 0.0886 | 0.2414 | 22 | 0.0299 | 0.0270 | -0.0730 |
| 0.20 | 0.9461 | 158 (19.4%) | 80.6% | 0.0570 | 0.3103 | 20 | 0.0305 | 0.0246 | -0.1754 |

### Ablation Summary

1. **Ablation A (Heuristic Threshold vs Conformal)**: Fixed 95th-percentile threshold flags 5.0% of windows (Precision: 0.1707, Recall: 0.2414, Selective Risk: 0.0285).
2. **Ablation B (B1 PCA vs B2 Sequential GRU)**:

| Model | Nominal $\alpha$ | Threshold | Escalation Rate | Coverage | Precision | Recall | Selective Risk |
|---|---|---|---|---|---|---|---|
| B1 PCA | 0.01 | 0.0419 | 0.7% | 99.3% | 1.0000 | 0.2069 | 0.0285 |
| **B2 GRU** | 0.01 | 1.6723 | 0.9% | 99.1% | 0.8571 | 0.2069 | 0.0285 |
| B1 PCA | 0.05 | 0.0000 | 3.2% | 96.8% | 0.7308 | 0.6552 | 0.0127 |
| **B2 GRU** | 0.05 | 1.1546 | 4.8% | 95.2% | 0.1795 | 0.2414 | 0.0284 |
| B1 PCA | 0.10 | 0.0000 | 3.2% | 96.8% | 0.7308 | 0.6552 | 0.0127 |
| **B2 GRU** | 0.10 | 0.9766 | 9.7% | 90.3% | 0.0886 | 0.2414 | 0.0299 |
| B1 PCA | 0.20 | 0.0000 | 3.2% | 96.8% | 0.7308 | 0.6552 | 0.0127 |
| **B2 GRU** | 0.20 | 0.9461 | 19.4% | 80.6% | 0.0570 | 0.3103 | 0.0305 |

3. **Ablation C (Calibration Size Sensitivity at $\alpha=0.05$)**:

| Fraction | Sample Size | Conformal $\hat{\tau}_{0.05}$ | Escalation Rate | Coverage | Selective Risk | Miscoverage |
|---|---|---|---|---|---|---|
| 25% | 203 | 1.0000 | 4.4% | 95.6% | 0.0309 | 0.0296 |
| 50% | 407 | 1.1506 | 4.7% | 95.3% | 0.0387 | 0.0369 |
| 100% | 814 | 1.1546 | 4.8% | 95.2% | 0.0284 | 0.0270 |

---

## Dataset: BGL

- **Architecture**: Sequential GRU (Embedding: 32, Hidden: 64, Layers: 1)
- **Trainable Parameters**: 20,853 (Constraint: < 2,000,000)
- **Training Epochs**: 20 (Best Val Loss: 0.0607 at epoch 20)
- **Calibration Sample Size ($n$)**: 100

### Target Alpha Sweep (Split Conformal Calibration)

| Nominal $\alpha$ | Threshold $\hat{\tau}_\alpha$ | Escalated | Coverage | Escalation Precision | Escalation Recall | False Clears | Selective Risk | Empirical Miscoverage | Deviation |
|---|---|---|---|---|---|---|---|---|---|
| 0.01 | 3.0238 | 0 (0.0%) | 100.0% | 0.0000 | 0.0000 | 36 | 0.3600 | 0.3600 | +0.3500 |
| 0.05 | 2.5947 | 2 (2.0%) | 98.0% | 0.5000 | 0.0278 | 35 | 0.3571 | 0.3500 | +0.3000 |
| 0.10 | 0.7196 | 9 (9.0%) | 91.0% | 0.4444 | 0.1111 | 32 | 0.3516 | 0.3200 | +0.2200 |
| 0.20 | 0.1898 | 19 (19.0%) | 81.0% | 0.6842 | 0.3611 | 23 | 0.2840 | 0.2300 | +0.0300 |

### Ablation Summary

1. **Ablation A (Heuristic Threshold vs Conformal)**: Fixed 95th-percentile threshold flags 5.0% of windows (Precision: 0.2000, Recall: 0.0278, Selective Risk: 0.3684).
2. **Ablation B (B1 PCA vs B2 Sequential GRU)**:

| Model | Nominal $\alpha$ | Threshold | Escalation Rate | Coverage | Precision | Recall | Selective Risk |
|---|---|---|---|---|---|---|---|
| B1 PCA | 0.01 | 1.1726 | 0.0% | 100.0% | 0.0000 | 0.0000 | 0.3600 |
| **B2 GRU** | 0.01 | 3.0238 | 0.0% | 100.0% | 0.0000 | 0.0000 | 0.3600 |
| B1 PCA | 0.05 | 0.9163 | 4.0% | 96.0% | 0.0000 | 0.0000 | 0.3750 |
| **B2 GRU** | 0.05 | 2.5947 | 2.0% | 98.0% | 0.5000 | 0.0278 | 0.3571 |
| B1 PCA | 0.10 | 0.0129 | 9.0% | 91.0% | 0.3333 | 0.0833 | 0.3626 |
| **B2 GRU** | 0.10 | 0.7196 | 9.0% | 91.0% | 0.4444 | 0.1111 | 0.3516 |
| B1 PCA | 0.20 | 0.0002 | 17.0% | 83.0% | 0.6471 | 0.3056 | 0.3012 |
| **B2 GRU** | 0.20 | 0.1898 | 19.0% | 81.0% | 0.6842 | 0.3611 | 0.2840 |

3. **Ablation C (Calibration Size Sensitivity at $\alpha=0.05$)**:

| Fraction | Sample Size | Conformal $\hat{\tau}_{0.05}$ | Escalation Rate | Coverage | Selective Risk | Miscoverage |
|---|---|---|---|---|---|---|
| 25% | 25 | 0.3580 | 0.0% | 100.0% | 0.6800 | 0.6800 |
| 50% | 50 | 2.5947 | 2.0% | 98.0% | 0.6735 | 0.6600 |
| 100% | 100 | 2.5947 | 2.0% | 98.0% | 0.3571 | 0.3500 |

---

