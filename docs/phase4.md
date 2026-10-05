# SentinelLog Phase 4: Learned Sequential Scorer + Conformal Risk-Controlled Selective Gate

## 1. Overview & Research Objective

Phase 4 establishes an empirical investigation into whether a **lightweight learned sequential anomaly scorer (B2)** combined with **split conformal prediction** can selectively gate log windows, auto-clearing normal traffic while escalating uncertain or high-risk windows to downstream triage components.

Central Research Question:
> *Can a lightweight learned sequential scorer plus conformal calibration selectively escalate only uncertain/high-risk windows while reducing unnecessary downstream computation under real-world chronological log conditions?*

All model fitting is conducted strictly on **TRAIN** without anomaly labels, calibrated on **CALIBRATION**, and strictly isolated from the **TEST** split (Rule 1).

---

## 2. B2 Architecture & Sequential Modeling

### 2.1 Model Architecture
- **Type**: Autoregressive Recurrent Neural Network ([`SequentialGRU`](file:///d:/FaultSentinel/sentinellog/scoring/b2_model.py#L18-L135)).
- **Layers**:
  - `nn.Embedding(vocab_size, embedding_dim=32, padding_idx=0)`
  - `nn.GRU(input_size=32, hidden_size=64, num_layers=1, batch_first=True)`
  - `nn.Dropout(p=0.1)`
  - `nn.Linear(in_features=64, out_features=vocab_size)`
- **Parameter Discipline (Rule 6)**:
  - HDFS model: **20,562** trainable parameters ($< 1.1\%$ of the $2,000,000$ limit).
  - BGL model: **20,853** trainable parameters ($< 1.1\%$ of the $2,000,000$ limit).
  - CPU-only execution: Zero CUDA dependency, sub-second inference.

### 2.2 Token Vocabulary & Special Tokens
The vocabulary is learned strictly from TRAIN and frozen:
- Token 0: `<PAD>` (reserved for sequence padding)
- Token 1: `<UNKNOWN>` (explicit representation for `template_id = -1` or novel templates)
- Tokens $\ge 2$: Unique known templates from TRAIN sorted deterministically.
Novel templates encountered during calibration or inference map exclusively to token 1 without altering model dimensions.

### 2.3 Training Protocol & Normal Workflow Learning
- **Self-Supervised Objective**: Next-template prediction. For an event sequence $t_1, t_2, \dots, t_L$:
  $$\mathcal{L}_{seq} = -\frac{1}{L - 1} \sum_{i=1}^{L-1} \log P(t_{i+1} \mid t_{\le i})$$
- **Training Subset Selection (Section 12)**: The model learns expected workflow patterns from normal operations. Normal-only TRAIN sequences are used for fitting (`train_normal_only: true`). Ground-truth anomaly labels are used solely for filtering the training set and are **never** prediction targets.
- **Internal Validation Split (Section 17)**: TRAIN is partitioned chronologically into 90% training subsplit and 10% validation subsplit for early stopping (patience = 3 epochs). CALIBRATION and TEST are never touched during training.

### 2.4 Sequential Nonconformity Score
For a window $W = (t_1, \dots, t_L)$, the nonconformity score is the mean negative log-likelihood (surprisal) across all observed transitions:
$$S_{B2}(W) = \frac{1}{\max(1, L-1)} \sum_{i=1}^{L-1} -\log P(t_{i+1} \mid t_{\le i})$$
Normalizing by transition count ensures long sessions are not penalized simply for having more events. For single-event windows ($L=1$), the score evaluates against the unconditional prior log-probability $-\log P(t_1)$.
**Direction**: Higher score $\implies$ less expected transition dynamics $\implies$ more anomalous.

---

## 3. Split Conformal Calibration & Selective Gate

### 3.1 Finite-Sample Split Conformal Calibration
Let $\{s_1, \dots, s_n\}$ be the calibration nonconformity scores computed by the frozen B2 model over the CALIBRATION partition.
Given nominal significance level $\alpha \in (0, 1)$, the finite-sample conformal threshold is defined via the order-statistic quantile:
$$k = \min\left(n, \max\left(1, \lceil (n + 1)(1 - \alpha) \rceil\right)\right)$$
$$\hat{\tau}_\alpha = s_{(k)}$$
where $s_{(1)} \le s_{(2)} \le \dots \le s_{(n)}$ are the sorted calibration scores.

### 3.2 Selective Escalation Gate
Each window $W$ is evaluated through the decision rule:
$$\text{Decision}(W) = \begin{cases} \text{ESCALATE} & \text{if } S_{B2}(W) > \hat{\tau}_\alpha \\ \text{AUTO-CLEAR} & \text{if } S_{B2}(W) \le \hat{\tau}_\alpha \end{cases}$$

### 3.3 Metric Definitions
- **Coverage (Auto-Clear Rate)**: $C = \frac{N_{clear}}{N}$ (fraction of windows resolved without downstream escalation)
- **Escalation Rate**: $R_{esc} = \frac{N_{esc}}{N} = 1 - C$
- **False Clear (FN)**: An anomalous window erroneously classified as `AUTO-CLEAR` ($y=1$ and $\text{Decision} = \text{AUTO-CLEAR}$)
- **Selective Risk**: Rate of false clears among auto-cleared windows:
  $$\text{Selective Risk} = \frac{\sum_{i=1}^N \mathbb{I}(y_i = 1 \text{ and } \text{Decision}_i = \text{AUTO-CLEAR})}{N_{clear}}$$
- **Empirical Miscoverage**: Fraction of all windows that are missed anomalies:
  $$\text{Empirical Miscoverage} = \frac{\sum_{i=1}^N \mathbb{I}(y_i = 1 \text{ and } \text{Decision}_i = \text{AUTO-CLEAR})}{N}$$
- **Deviation**: $\Delta = \text{Empirical Miscoverage} - \alpha$

---

## 4. Empirical Results (50K Development Slice)

All evaluations are conducted strictly on **CALIBRATION** ($N_{HDFS} = 814, N_{BGL} = 100$). **TEST** was not accessed.

### 4.1 HDFS Target Alpha Sweep

| Nominal $\alpha$ | Conformal $\hat{\tau}_\alpha$ | Escalated | Coverage | Escalation Precision | Escalation Recall | False Clears | Selective Risk | Empirical Miscoverage | Deviation |
|---|---|---|---|---|---|---|---|---|---|
| **0.01** | 1.6723 | 7 (0.9%) | 99.1% | **0.8571** | 0.2069 | 23 | 0.0285 | 0.0283 | +0.0183 |
| **0.05** | 1.1546 | 39 (4.8%) | 95.2% | 0.1795 | 0.2414 | 22 | 0.0284 | 0.0270 | -0.0230 |
| **0.10** | 0.9766 | 79 (9.7%) | 90.3% | 0.0886 | 0.2414 | 22 | 0.0299 | 0.0270 | -0.0730 |
| **0.20** | 0.9461 | 158 (19.4%) | 80.6% | 0.0570 | 0.3103 | 20 | 0.0305 | 0.0246 | -0.1754 |

### 4.2 BGL Target Alpha Sweep

| Nominal $\alpha$ | Conformal $\hat{\tau}_\alpha$ | Escalated | Coverage | Escalation Precision | Escalation Recall | False Clears | Selective Risk | Empirical Miscoverage | Deviation |
|---|---|---|---|---|---|---|---|---|---|
| **0.01** | 3.0238 | 0 (0.0%) | 100.0% | 0.0000 | 0.0000 | 36 | 0.3600 | 0.3600 | +0.3500 |
| **0.05** | 2.5947 | 2 (2.0%) | 98.0% | 0.5000 | 0.0278 | 35 | 0.3571 | 0.3500 | +0.3000 |
| **0.10** | 0.7196 | 9 (9.0%) | 91.0% | 0.4444 | 0.1111 | 32 | 0.3516 | 0.3200 | +0.2200 |
| **0.20** | 0.1898 | 19 (19.0%) | 81.0% | **0.6842** | **0.3611** | 23 | 0.2840 | 0.2300 | +0.0300 |

---

## 5. Ablation Studies

### Ablation A: Fixed Heuristic Threshold vs Conformal Gate
- On HDFS, a fixed 95th-percentile threshold flags 5.0% of windows with Precision = 0.1707 and Selective Risk = 0.0285. Conformal calibration at $\alpha=0.05$ flags 4.8% of windows with Precision = 0.1795 and Selective Risk = 0.0284, matching heuristic performance while providing calibrated significance parametrization.
- At $\alpha=0.01$, the conformal gate cuts escalation from 5.0% down to 0.9% while increasing precision to **85.7%** (6 TP out of 7 escalated windows).

### Ablation B: B1 PCA vs B2 Sequential GRU
- At $\alpha=0.20$ on BGL, B2 Sequential GRU achieves higher Precision (68.4% vs 64.7%) and higher Recall (36.1% vs 30.6%) compared with B1 PCA, demonstrating that sequential transition modeling improves anomaly separation on complex multi-node logs.
- On HDFS at low escalation budgets ($\alpha=0.01$), B1 PCA and B2 GRU both achieve high precision ($\ge 85\%$).

### Ablation C: Calibration Sample Size Sensitivity ($\alpha=0.05$)
Evaluating chronological prefixes of calibration data on HDFS:
- 25% ($n=203$): $\hat{\tau}_{0.05} = 1.0000$, Escalation Rate = 4.4%, Selective Risk = 0.0309
- 50% ($n=407$): $\hat{\tau}_{0.05} = 1.1506$, Escalation Rate = 4.7%, Selective Risk = 0.0387
- 100% ($n=814$): $\hat{\tau}_{0.05} = 1.1546$, Escalation Rate = 4.8%, Selective Risk = 0.0284
The conformal threshold stabilizes rapidly once $n \ge 400$, exhibiting robust convergence under chronological sampling.

---

## 6. Critical Theoretical vs Empirical Distinctions

### Why Formal Exchangeability Guarantees Do Not Hold in Production Logs
1. **Temporal Non-Exchangeability**: System logs exhibit strong chronological drift, concept shifts, bursty error cascades, and maintenance windows. Conformal prediction's theoretical coverage property assumes exchangeability ($P(Z_1, \dots, Z_n, Z_{n+1})$ invariant to permutation), which is strictly violated by temporal dependencies.
2. **Calibration Anomaly Density Discrepancy**: In BGL calibration, 36% of windows are anomalous. A user requesting $\alpha = 0.05$ expects to escalate only 5% of traffic. Under a 5% budget, empirical miscoverage unavoidably reaches 35% because the true anomaly rate in that time slice exceeds the entire escalation budget.
3. **Engineering Conclusion**: Split conformal calibration provides a rigorous, principled mechanism for tuning operating thresholds to target error budgets, but must be reported as an **empirical risk-control tool**, not an unconditional mathematical guarantee against operational false negatives.
