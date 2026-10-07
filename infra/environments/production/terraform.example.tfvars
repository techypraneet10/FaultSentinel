# SentinelLog Production Example Terraform Variables
# NEVER commit real values, ARNs with sensitive account IDs, or credentials here.

aws_region      = "us-east-1"
image_uri       = "123456789012.dkr.ecr.us-east-1.amazonaws.com/sentinellog-production:v0.15.0"
certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/00000000-0000-0000-0000-000000000000"
