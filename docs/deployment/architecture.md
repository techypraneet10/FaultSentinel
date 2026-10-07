# SentinelLog Target Deployment Architecture (Phase 15)

## 1. Executive Summary

SentinelLog employs a cloud-native, multi-AZ deployment architecture on Amazon Web Services (AWS) designed to deliver high availability, horizontal scalability, defense-in-depth isolation, and strict reproducibility. The deployment topology packages the hardened SentinelLog serving layer without modifying any research algorithms or benchmark metrics.

## 2. Ingress & Traffic Flow

```
[ Public Internet / Operator Clients ]
                 │
                 ▼
     [ Route 53 Public DNS ]
                 │
                 ▼
     [ Application Load Balancer (ALB) ]
       ├─ Port 80: HTTP → HTTPS 301 Redirect
       ├─ Port 443: TLS 1.3 / 1.2 Termination (ACM Certificate)
       ├─ Drop Invalid Headers: Enabled
       └─ Target Group: Ingress to private ECS tasks (Port 8000)
                 │
                 ▼ (Private VPC Boundary: 10.0.0.0/16)
     [ AWS ECS Fargate Cluster (Multi-AZ) ]
       ├─ Task 1 (us-east-1a) [Non-root USER 10001]
       ├─ Task 2 (us-east-1b) [Non-root USER 10001]
       ├─ Health Check: /health/live (Process liveness)
       ├─ Readiness Check: /health/ready (Routing gate)
       └─ Graceful Shutdown: 30s SIGTERM drain
                 │
       ┌─────────┴───────────────────────────────┐
       ▼                                         ▼
[ Internal Data & State ]             [ External Managed Services ]
 ├─ Aurora PostgreSQL / pgvector       ├─ Qdrant Cloud (Vector search)
 ├─ S3 Bucket (Artifacts & Models)     ├─ LLM Provider (OpenAI / Azure)
 └─ ElastiCache Redis (Rate Limiting)  └─ CloudWatch / OTLP (Telemetry)
```

## 3. Core Architectural Components

| Component | Technology | Role & Security Invariants |
| :--- | :--- | :--- |
| **DNS** | Amazon Route 53 | High-availability domain routing with health-check failover. |
| **Load Balancing** | AWS Application Load Balancer | TLS termination, HTTP-to-HTTPS redirection, path routing, and target group readiness gating. |
| **Compute** | AWS ECS Fargate | Serverless container execution; unprivileged user (`10001`), read-only root compatible, zero host mounts. |
| **Relational / Vector DB** | Amazon Aurora PostgreSQL (Serverless v2) | Private subnet placement; pgvector support; KMS encryption at rest; automated backups. |
| **Vector Index** | Qdrant Cloud | Isolated vector database for log candidate retrieval over TLS; authenticated with API key. |
| **Object Storage** | Amazon S3 | Private bucket with versioning and AES256/KMS encryption; public access completely blocked. |
| **Secrets Management** | AWS Secrets Manager | Runtime secret injection; automatic secret rotation procedures; zero committed keys. |
| **Distributed Rate Limiting** | Amazon ElastiCache (Redis) | Shared sliding-window counters for multi-replica rate enforcement with bounded memory. |
| **Observability** | CloudWatch & OpenTelemetry (OTLP) | Centralized structured log streaming, Prometheus scraping, and distributed trace collection. |
