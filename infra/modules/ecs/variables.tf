variable "environment" {
  type        = string
  description = "Target deployment environment"
}

variable "image_uri" {
  type        = string
  description = "Immutable container image URI (e.g. 123456789.dkr.ecr.us-east-1.amazonaws.com/sentinellog-prod:v0.15.0)"
}

variable "cpu" {
  type        = number
  description = "CPU units allocated to Fargate task"
  default     = 1024
}

variable "memory" {
  type        = number
  description = "Memory allocated to Fargate task in MB"
  default     = 2048
}

variable "container_port" {
  type        = number
  description = "Port exposed by the SentinelLog application container"
  default     = 8000
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnets for Fargate task placement"
}

variable "ecs_security_group_id" {
  type        = string
  description = "Security group ID for ECS tasks"
}

variable "target_group_arn" {
  type        = string
  description = "ARN of ALB target group"
}

variable "desired_count" {
  type        = number
  description = "Desired number of running task instances"
  default     = 2
}

variable "api_key_secret_arn" {
  type        = string
  description = "Secrets Manager ARN for API key"
}

variable "db_credentials_secret_arn" {
  type        = string
  description = "Secrets Manager ARN for database credentials"
}

variable "llm_credentials_secret_arn" {
  type        = string
  description = "Secrets Manager ARN for LLM API key"
}

variable "storage_bucket_arn" {
  type        = string
  description = "ARN of private S3 artifacts bucket"
}
