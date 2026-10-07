# SentinelLog Infrastructure as Code (Terraform) (Phase 15)

## 1. Overview

SentinelLog provisions cloud infrastructure declaratively using Terraform ($\ge$ 1.5.0) and the official AWS Provider ($\ge$ 5.0.0). All infrastructure definitions reside in `infra/`.

## 2. Terraform Module Architecture

```
infra/
├── modules/
│   ├── networking/   # VPC, Multi-AZ subnets, NAT Gateway, Security Groups
│   ├── alb/          # Application Load Balancer, TLS Termination, Health checks
│   ├── ecs/          # ECS Fargate Cluster, Task Definition (non-root), Service
│   ├── ecr/          # ECR Repository with immutable tags & vulnerability scans
│   ├── database/     # Aurora PostgreSQL Serverless v2 with KMS encryption
│   ├── storage/      # Private S3 Bucket with versioning & public access block
│   └── secrets/      # AWS Secrets Manager resources & access policies
└── environments/
    ├── staging/      # Staging environment composition & state configuration
    └── production/   # Production environment composition & state configuration
```

## 3. Remote State & Locking

- **Backend:** Amazon S3 with server-side encryption enabled (`encrypt = true`).
- **State Locking:** Amazon DynamoDB state locking table (`sentinellog-tf-locks-<env>`).
- **Access Control:** Restricted via IAM least-privilege policies.
- **Git Safety:** `*.tfstate`, `*.tfstate.*`, `.terraform/`, and `.terraform.lock.hcl` are strictly ignored by `.gitignore`.

## 4. Key Security & Compliance Controls

1. **Non-Root Compute:** ECS Fargate tasks run with `user = "10001:10001"` and `requires_compatibilities = ["FARGATE"]`.
2. **Private Data Services:** Aurora PostgreSQL and S3 are inaccessible from the public internet. Database instances reside strictly in private subnets.
3. **Least Privilege IAM:** Execution role only has access to specific Secrets Manager ARNs; Task role has scoped access only to the specific artifacts S3 bucket.
4. **Traffic Gating:** Public traffic enters exclusively through the Application Load Balancer with HTTP-to-HTTPS redirect.
