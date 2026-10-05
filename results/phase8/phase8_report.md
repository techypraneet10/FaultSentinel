# Phase 8 Summary Report: Deterministic Incident Reasoning Engine

- **Git Commit**: `973da9d3367a8d9975790bd94e12e0d8b01f3b23`
- **Configuration Hash**: `57e370a7c64a9172e20819307b621b4531e8be8a5f09125296fa3becdee602ea`
- **Rule 1 Enforced (Test Used)**: `False`

## Dataset: HDFS

- **Total Windows Assessed**: 39
- **Decision Distribution**: `{'INCIDENT': 33, 'SUSPICIOUS': 6}`
- **Severity Distribution**: `{'HIGH': 27, 'CRITICAL': 6, 'LOW': 6}`
- **Sufficiency Distribution**: `{'SUFFICIENT': 39}`
- **Provenance Status Distribution**: `{'VERIFIED': 39}`
- **Conflict Rate**: 0.0%
- **Average Evidence Count**: 3.00
- **Average Evidence Relevance**: 0.9239
- **Average Confidence (Support Strength)**: 0.9043
- **Rule Firing Frequencies**: `{'RULE-INC-001': 33, 'RULE-SUSP-001': 6}`

### Ablation Sensitivity Diagnostics

- **single_strongest_signal**: Decisions={'INCIDENT': 33, 'SUSPICIOUS': 6}, Severities={'HIGH': 27, 'CRITICAL': 6, 'LOW': 6}, AvgConf=0.9043
- **relevance_only**: Decisions={'INCIDENT': 33, 'SUSPICIOUS': 6}, Severities={'HIGH': 27, 'CRITICAL': 6, 'LOW': 6}, AvgConf=0.9043
- **conflict_ignored**: Decisions={'INCIDENT': 33, 'SUSPICIOUS': 6}, Severities={'HIGH': 27, 'CRITICAL': 6, 'LOW': 6}, AvgConf=0.9043
- **sufficiency_disabled**: Decisions={'INCIDENT': 33, 'SUSPICIOUS': 6}, Severities={'HIGH': 27, 'CRITICAL': 6, 'LOW': 6}, AvgConf=0.9043

---

## Dataset: BGL

- **Total Windows Assessed**: 2
- **Decision Distribution**: `{'INSUFFICIENT_EVIDENCE': 2}`
- **Severity Distribution**: `{'LOW': 2}`
- **Sufficiency Distribution**: `{'INSUFFICIENT': 2}`
- **Provenance Status Distribution**: `{'VERIFIED': 2}`
- **Conflict Rate**: 100.0%
- **Average Evidence Count**: 3.00
- **Average Evidence Relevance**: 0.0240
- **Average Confidence (Support Strength)**: 0.0500
- **Rule Firing Frequencies**: `{'RULE-SUFF-001': 2}`

### Ablation Sensitivity Diagnostics

- **single_strongest_signal**: Decisions={'INSUFFICIENT_EVIDENCE': 2}, Severities={'LOW': 2}, AvgConf=0.0500
- **relevance_only**: Decisions={'INSUFFICIENT_EVIDENCE': 2}, Severities={'LOW': 2}, AvgConf=0.0500
- **conflict_ignored**: Decisions={'INSUFFICIENT_EVIDENCE': 2}, Severities={'LOW': 2}, AvgConf=0.2873
- **sufficiency_disabled**: Decisions={'SUSPICIOUS': 2}, Severities={'MEDIUM': 2}, AvgConf=0.3173

---

## Runtime Execution Metadata

- **Execution Timestamp**: 2026-10-05T19:41:19.049320+00:00
- **Python Version**: `3.12.4`
- **Execution Timing**: hdfs=0.0083s, bgl=0.0009s
- **Note**: Runtime metadata is strictly separated from deterministic content artifacts.

