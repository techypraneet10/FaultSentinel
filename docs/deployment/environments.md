# SentinelLog Environment Model & Isolation Strategy (Phase 15)

## 1. Overview

SentinelLog defines three explicitly segregated environments:
1. **Development (`development`)**
2. **Staging (`staging`)**
3. **Production (`production`)**

Each environment maintains its own isolated network, configuration, credentials, storage buckets, and database resources.

## 2. Environment Comparison Matrix

| Dimension | Development | Staging | Production |
| :--- | :--- | :--- | :--- |
| **Location** | Local workstations / CI | Dedicated Staging AWS VPC (`10.1.0.0/16`) | Dedicated Production AWS VPC (`10.0.0.0/16`) |
| **Authentication** | Optional / Permissive | Mandatory (Enforce Production Mode) | Mandatory (Enforce Production Mode) |
| **Secrets Source** | Local environment / `.env` | AWS Secrets Manager (`staging/*`) | AWS Secrets Manager (`production/*`) |
| **Compute** | Local Python / Docker | AWS ECS Fargate (2 tasks) | AWS ECS Fargate (4 tasks multi-AZ) |
| **Load Balancer** | None (direct port 8000) | AWS ALB with Staging TLS | AWS ALB with Production TLS & Route 53 |
| **Database** | Mock / Local PostgreSQL | Aurora PostgreSQL (`sentinellog_staging`) | Aurora PostgreSQL (`sentinellog_production`) |
| **Vector DB** | Local Mock / In-memory | Qdrant Cloud (`sentinellog_staging`) | Qdrant Cloud (`sentinellog_production`) |
| **Object Storage** | Local filesystem (`data/`, `results/`) | Private S3 (`sentinellog-artifacts-staging`) | Private S3 (`sentinellog-artifacts-production`) |
| **Rate Limiting** | Bounded in-memory sliding window | ElastiCache Redis / In-memory fallback | ElastiCache Redis Cluster |
| **Observability** | Standard stdout / in-memory | CloudWatch + OTLP Collector | CloudWatch + OTLP + Managed Prometheus |

## 3. Strict Isolation Invariants (Rule 3)

1. **No Shared Credentials:** Staging and Production Secrets Manager instances use strictly separate KMS keys and secret ARNs.
2. **Zero Cross-Talk:** VPC peering between Staging and Production is strictly prohibited. Security groups reject all inter-environment ingress.
3. **Data Segregation:** Staging never points to Production S3 buckets or database instances. Production data is never copied to Staging without formal sanitization and redaction.
4. **Promotion Discipline:** Code and images only move from Staging to Production through signed immutable release manifests after green smoke tests.
