# SentinelLog Data Pipeline & Versioning Specification

This document details the architecture, design decisions, leakage protections, and reproducibility protocols of Phase 2 for SentinelLog.

---

## 1. Overview & Data Sources

SentinelLog processes two primary benchmark datasets from the official Loghub distribution (DOI: `10.5281/zenodo.8196385`):

1. **HDFS (Primary Dataset)**:
   - Source: Hadoop Distributed File System cluster logs collected in a private cloud environment.
   - Files: `HDFS.log` (raw event logs) and `preprocessed/anomaly_label.csv` (block-level ground truth).
   - Traceability: Session grouping based on HDFS Block IDs (`blk_-...`).
2. **BGL (Secondary/Generalization Dataset)**:
   - Source: BlueGene/L supercomputer log collected at Lawrence Livermore National Laboratory (LLNL).
   - File: `BGL.log` (sequential system event logs with alert severity tags).
   - Traceability: Fixed-size sequential windows ($W=100$) tracking alert classifications.

---

## 2. Raw Data Storage & Integrity

All raw files are treated as immutable and preserved under:
```text
data/raw/
├── hdfs/
│   ├── HDFS.log
│   ├── anomaly_label.csv
│   ├── HDFS_v1.zip
│   └── manifest.json
└── bgl/
    ├── BGL.log
    ├── BGL.zip
    └── manifest.json
```
For every acquired file, SHA-256 hashes and byte lengths are computed and recorded in `manifest.json`.

---

## 3. Log Parsing & Template Extraction (Drain3)

We utilize **Drain3**, a streaming tree-based log parsing algorithm, implemented in `sentinellog.ingestion.parser.DrainParser`:

- **Variable Masking**:
  - HDFS: Block IDs (`blk_-?\d+`), IP addresses, file paths, and standalone numbers are masked with `<*>`.
  - BGL: Core IDs (`core\.\d+`), hex memory addresses (`0x[0-9a-fA-F]+`), IP addresses, and numbers are masked with `<*>`.
- **Parsing Parameters**:
  - Tree depth: $4$
  - Similarity threshold: $0.5$
  - Max children: $100$
- **Explicit Unknown Template Handling**:
  - If a log line fails header regex extraction or encountered parsing errors, it is assigned:
    - `template_id = -1` (`UNKNOWN_TEMPLATE_ID`)
    - `template = "UNKNOWN"` (`UNKNOWN_TEMPLATE_STR`)
  - No records are silently dropped or converted into normal records without explicit tracking.

---

## 4. Window Construction

### 4.1 HDFS Session-Based Windows
- Grouping: Records sharing the same `session_id` (`BlockId`, e.g., `blk_-1608999687919862906`).
- Internal Ordering: Records within a session are ordered strictly chronologically by timestamp and line number.
- Window Labeling: Derived directly from `anomaly_label.csv` (Normal = `False`, Anomaly = `True`).
- Global Ordering: Windows are sorted chronologically by the start time of the session. Tie-breaking is deterministic on `BlockId`.

### 4.2 BGL Fixed-Size Windows
- Grouping: Sequential log lines grouped into non-overlapping windows of configurable size (default $W=100$).
- Window Labeling: A window is labeled anomalous (`is_anomaly = True`) if **any** constituent log event possesses an alert label (i.e. token $\neq \text{'-'}$).
- Final Partial Window: Deterministically retained if `len >= min_window_size` to ensure zero data loss.

---

## 5. Leakage-Safe Chronological Partitioning

Splits are strictly chronological without random shuffling or stratification:
- **Train (60%)**: Earliest 60% of windows.
- **Calibration (20%)**: Next sequential 20% of windows (reserved for Phase 4 conformal gating).
- **Test (20%)**: Final sequential 20% of windows.

### 5.1 Leakage Protection Invariants
The pipeline programmatically validates and enforces:
1. **Temporal Boundary Isolation**:
   $$\max(\text{train\_start\_time}) \le \min(\text{calib\_start\_time}) \le \min(\text{test\_start\_time})$$
2. **Window ID Disjointness**:
   $$\text{Train\_IDs} \cap \text{Calib\_IDs} = \emptyset, \quad \text{Train\_IDs} \cap \text{Test\_IDs} = \emptyset, \quad \text{Calib\_IDs} \cap \text{Test\_IDs} = \emptyset$$
3. **Session/Block Isolation**:
   No HDFS block trace may cross partition boundaries.
4. Violation of any invariant immediately raises a `DataLeakageError`.

### 5.2 Test Set Protection Protocol (Rule 1 & Rule 10)
- The test split artifacts (`data/processed/*/test.jsonl`) are generated for structural validation only.
- The test set is **FROZEN** until Phase 7.
- No model training, hyperparameter tuning, feature selection, or selective threshold fitting may access test data before Phase 7.

---

## 6. Processed Artifact Structure

Processed windows are saved as JSON Lines (`.jsonl`) format:
```text
data/processed/
├── hdfs/
│   ├── train.jsonl
│   ├── calibration.jsonl
│   ├── test.jsonl
│   ├── data_quality_report.json
│   └── manifest.json
└── bgl/
    ├── train.jsonl
    ├── calibration.jsonl
    ├── test.jsonl
    ├── data_quality_report.json
    └── manifest.json
```

Each window object contains:
- `dataset`: `"hdfs"` or `"bgl"`
- `window_id`: Unique identifier
- `session_id`: Session or block ID (if applicable)
- `start_time` / `end_time`: Timestamps
- `record_count`: Number of log events in the window
- `template_ids`: List of integer template cluster IDs
- `raw_messages`: List of raw unparsed log messages
- `is_anomaly`: Ground-truth boolean label
- `metadata`: Provenance and anomaly diagnostics
