# SentinelLog Disaster Recovery & Backup Strategy (Phase 15)

## 1. Overview

This document specifies the disaster recovery (DR) posture and backup procedures for SentinelLog serving components and data stores.

## 2. Recovery Objectives

| Metric | Target | Rationale |
| :--- | :--- | :--- |
| **Recovery Point Objective (RPO)** | **< 1 Hour** | Automated Aurora PostgreSQL continuous backups with point-in-time restore; S3 bucket versioning. |
| **Recovery Time Objective (RTO)** | **< 2 Hours** | Declarative Terraform provisioning and pre-built immutable ECR container images allow rapid environment reconstruction. |

*Note: In local or unprovisioned cloud environments, exact RTO/RPO values reflect target architectures and are marked NOT YET ESTABLISHED until live DR drills are executed.*

## 3. Component Backup Procedures

### 3.1 Relational & Vector Metadata (Aurora PostgreSQL)
- **Continuous Backups:** Aurora automated backups enabled with a 30-day retention period in Production (7 days in Staging).
- **Point-in-Time Restore (PITR):** Recovery available to any second within the retention window.
- **KMS Encryption:** All snapshots are encrypted with customer-managed AWS KMS keys.

### 3.2 Artifacts & Calibration Storage (Amazon S3)
- **Versioning:** S3 bucket versioning is enabled on `sentinellog-artifacts-*`.
- **Cross-Region Replication:** In production, critical model checkpoints and frozen calibration artifacts are replicated to a secondary AWS region (`us-west-2`).
- **Object Lock / Immutability:** S3 Object Lock prevents accidental deletion of frozen Phase 12 benchmark evaluation files.

### 3.3 Infrastructure & Configuration
- Infrastructure is fully codified in `infra/` Terraform definitions.
- Application code, schemas, and configurations reside under Git source control.
- Reconstruction of a complete environment from scratch requires only running `terraform apply` against a clean AWS account.

## 4. Disaster Recovery Scenarios

1. **Availability Zone (AZ) Outage:**
   - ECS Fargate tasks are automatically distributed across multiple AZs (`us-east-1a`, `us-east-1b`).
   - ALB automatically routes around the impaired AZ with zero operator intervention.
2. **Region-Wide Failure:**
   - Secondary region infrastructure can be provisioned via Terraform pointing to cross-region replicated S3 buckets and database snapshots.
   - Route 53 DNS records updated to point to secondary region ALB.
