variable "repository_name" {
  type        = string
  description = "Name of the ECR repository"
  default     = "sentinellog"
}

variable "environment" {
  type        = string
  description = "Target deployment environment"
}
