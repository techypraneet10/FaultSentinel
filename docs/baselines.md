# SentinelLog Baselines: B0 & B1 (Phase 3)

## Overview

Phase 3 establishes rigorous, transparent, reproducible **unsupervised anomaly detection baselines** for log window triage prior to learned scoring, conformal risk control, retrieval, or LLM reasoning.

Two baseline families are implemented:
1. **B0 (Frequency Scorer)**: A classical token-frequency rarity baseline.
2. **B1 (Template-Count Vector Detectors)**:
   - **B1 Primary (PCA)**: Principal Component Analysis reconstruction error.
   - **B1 Secondary (Isolation Forest)**: Non-linear tree isolation depth scoring.

All models are trained strictly without labels on **TRAIN**, evaluated for threshold calibration on **CALIBRATION**, and completely isolated from the frozen **TEST** split (Rule 1).

---

## 1. Mathematical Formulation

### 1.1 B0 — Simple Frequency/Rarity Baseline

Let $\mathcal{V}_{train}^{known}$ be the set of distinct template identifiers mined from the training split (excluding UNKNOWN). The total support of the categorical event distribution has cardinality $K = |\mathcal{V}_{train}^{known}| + 1$, where the $+1$ accounts for the explicit unmapped/unknown template bin $\text{UNKNOWN} = -1$.

Let $C_{train}(t)$ denote the total occurrences of template $t$ in the training windows, and $N_{train} = \sum_{t} C_{train}(t)$ be the total token count. Using Laplace smoothing with parameter $\alpha > 0$ (default $\alpha = 1.0$):

$$P_{train}(t) = \frac{C_{train}(t) + \alpha}{N_{train} + \alpha K} = \frac{C_{train}(t) + \alpha}{N_{train} + \alpha (|\mathcal{V}_{train}^{known}| + 1)}$$

For any template $t \notin \mathcal{V}_{train}^{known}$ (or $t = -1$), it maps to the $\text{UNKNOWN}$ bin:

$$P_{train}(\text{UNKNOWN}) = \frac{C_{train}(-1) + \alpha}{N_{train} + \alpha K}$$

This guarantees proper normalization:

$$\sum_{t \in \mathcal{V}_{train}^{known} \cup \{-1\}} P_{train}(t) = 1.0$$

The rarity (surprisal) of an individual template event is its negative log-probability:

$$R(t) = -\log P_{train}(t)$$

For a window $W = (t_1, t_2, \dots, t_L)$ containing $L = \text{record\_count}$ events, the window-level anomaly score is the mean surprisal:

$$S_{B0}(W) = \frac{1}{L} \sum_{i=1}^L R(t_i) = -\frac{1}{L} \sum_{i=1}^L \log P_{train}(t_i)$$

**Direction**: Higher score $\implies$ more rare/surprising templates $\implies$ more anomalous.

---

### 1.2 B1 — Template Count Vectorization

Each log window is represented as a fixed-dimensional vector $\mathbf{x} \in \mathbb{R}^D$:

$$\mathbf{x} = \left[ c(t_1), c(t_2), \dots, c(t_K), c(\text{UNKNOWN}) \right]$$

where $K = |\mathcal{V}_{train}|$ and the final dimension captures all $\text{UNKNOWN}$ (-1) occurrences.

#### Invariant Vocabulary & Leakage Protection
- The vocabulary $\mathcal{V}_{train}$ is learned strictly on TRAIN and frozen.
- Calibration and test windows cannot alter or expand the feature dimensions ($D$ remains constant).
- Any template appearing in calibration or test that was not in $\mathcal{V}_{train}$ maps exclusively into the $c(\text{UNKNOWN})$ index.

#### Normalization
To prevent window length from dominating the feature representation (crucial for HDFS session windows whose lengths vary from 1 to hundreds of events), the default representation uses normalized frequencies:

$$x_j = \frac{c(t_j)}{L_W}$$

where $L_W = \max(1, \text{record\_count})$.

---

### 1.3 B1 Primary — PCA Reconstruction Error

PCA projects the centered training vectors $\mathbf{x} - \boldsymbol{\mu}$ into a $k$-dimensional principal subspace spanned by orthonormal eigenvectors $\mathbf{W}_k \in \mathbb{R}^{D \times k}$:

$$\mathbf{z} = (\mathbf{x} - \boldsymbol{\mu}) \mathbf{W}_k$$

$$\hat{\mathbf{x}} = \mathbf{z} \mathbf{W}_k^T + \boldsymbol{\mu}$$

The anomaly score is the squared reconstruction error (residual distance from the normal subspace):

$$S_{PCA}(\mathbf{x}) = \|\mathbf{x} - \hat{\mathbf{x}}\|_2^2 = \sum_{j=1}^D (x_j - \hat{x}_j)^2$$

**Component Selection Rule**: The number of components $k$ is determined strictly from TRAIN by finding the smallest $k$ such that the cumulative explained variance ratio meets the target $\sigma_{target} = 0.95$:

$$k = \min \left\{ m \;\middle|\; \sum_{i=1}^m \lambda_i / \sum_{j=1}^D \lambda_j \ge \sigma_{target} \right\}$$

**Direction**: Higher reconstruction error $\implies$ larger departure from normal subspace $\implies$ more anomalous.

---

### 1.4 B1 Secondary — Isolation Forest

Isolation Forest partitions the feature space using random axis-aligned splits. Anomalous points isolate in fewer partitions (shorter path lengths).

Given average path length $h(\mathbf{x})$ and normalization factor $c(n)$, the raw anomaly score $s(\mathbf{x}, n) = 2^{-\frac{\mathbb{E}(h(\mathbf{x}))}{c(n)}}$. In `scikit-learn`, `score_samples(x)` returns negative values for anomalies and positive values for normal points.

To maintain uniform score direction across all baselines, we negate `score_samples`:

$$S_{IF}(\mathbf{x}) = -\text{score\_samples}(\mathbf{x})$$

**Direction**: Higher score $\implies$ shorter isolation tree depth $\implies$ more anomalous.

---

## 2. Thresholding Strategy

The models remain strictly unsupervised. To convert continuous anomaly scores into discrete triage decisions, an unsupervised quantile threshold is calibrated on the CALIBRATION partition:

$$\tau = \text{Quantile}(S(\mathcal{W}_{calib}), q)$$

where $q \in (0, 1)$ is configurable (default $q = 0.95$, representing an expectation that top ~5% scores warrant triage).

### Strict Inequality Handling for Discrete Tied Scores
In system log data, normal operational behavior frequently produces identical sequences (e.g., standard HDFS block replication). Over 96% of normal windows can share the exact same minimum reconstruction error $s_{base}$.

If $\ge 95\%$ of calibration samples tie at $s_{base}$, the 95th percentile equals $s_{base}$. A non-strict comparison ($S \ge \tau$) would erroneously flag all $96\%$ of normal windows as anomalous. SentinelLog enforces a strict decision operator:

$$\hat{y}(W) = \mathbb{I}(S(W) > \tau)$$

This properly flags only windows strictly exceeding the normal mass, preserving low false-positive rates.

---

## 3. Empirical Results (50K Development Slice)

All metrics below are computed strictly on **CALIBRATION** ($N_{HDFS} = 814, N_{BGL} = 100$). **TEST** was not accessed.

| Dataset | Baseline | Threshold $\tau$ | Flagged | TP | FP | FN | Precision | Recall | F1 | ROC-AUC | PR-AUC | Oracle F1 (Diag) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **HDFS** | **B0 (Frequency)** | 1.5774 | 26 | 19 | 7 | 10 | **0.7308** | **0.6552** | **0.6909** | **0.8501** | **0.6128** | 0.6909 |
| **HDFS** | **B1 (PCA)** | 2.81e-9 | 26 | 19 | 7 | 10 | **0.7308** | **0.6552** | **0.6909** | 0.8237 | 0.5433 | 0.7037 |
| **HDFS** | **B1 (Isolation Forest)** | 0.4354 | 26 | 19 | 7 | 10 | **0.7308** | **0.6552** | **0.6909** | 0.8221 | 0.4451 | 0.7037 |
| **BGL** | **B0 (Frequency)** | 8.1140 | 5 | 1 | 4 | 35 | 0.2000 | 0.0278 | 0.0488 | 0.9089 | 0.7082 | 0.9231 |
| **BGL** | **B1 (PCA)** | 0.6664 | 5 | 1 | 4 | 35 | 0.2000 | 0.0278 | 0.0488 | 0.2786 | 0.3679 | 0.4151 |
| **BGL** | **B1 (Isolation Forest)** | 0.4193 | 5 | 4 | 1 | 32 | **0.8000** | 0.1111 | **0.1951** | **0.9390** | **0.8582** | 0.9231 |

### Key Scientific Insights
1. **B0 vs B1 on HDFS**: On HDFS session data, B0 frequency scoring matches B1 PCA and Isolation Forest in F1 score (0.6909) and achieves higher ROC-AUC (0.8501 vs 0.8237) and PR-AUC (0.6128 vs 0.5433). Because HDFS block anomalies primarily manifest as novel template sequences or unexpected termination events, simple template surprisal is remarkably competitive with multivariate projections.
2. **Isolation Forest on BGL**: On BGL fixed windows ($W=100$), Isolation Forest achieves the highest PR-AUC (0.8582) and ROC-AUC (0.9390), with 80% precision on its top flagged windows.
3. **Quantile Threshold Limitations**: In the BGL 50K development slice, 36% of calibration windows are anomalous. A fixed 95th percentile threshold only flags 5% of windows, mechanically capping recall at $\approx 0.14$. When the oracle search tunes the threshold to the actual anomaly density, F1 jumps to 0.9231. This motivates the need for Phase 4's calibrated risk control and conformal prediction.

---

## 4. Reproducibility & Test Set Protection

### Traceability Invariant
Every baseline execution produces a machine-readable experiment manifest (`results/phase3/{dataset}/{baseline}/manifest.json`) recording:
- Dataset name and data version
- SHA-256 hash of Phase 2 data manifest
- Model hyperparameters and vector dimension
- Threshold configuration and numerical value
- Git commit hash
- Permanent flag: `"test_used": false`

### Test Access Guard
Module `sentinellog.scoring.artifacts` provides `guard_no_test_split(split_name, file_path)`. Attempting to pass `test` or path to `test.jsonl` raises `TestAccessViolationError`, preventing accidental test data leakage during baseline training and calibration.
