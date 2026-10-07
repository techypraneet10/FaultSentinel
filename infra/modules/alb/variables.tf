variable "environment" {
  type        = string
  description = "Target deployment environment"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID where target group is defined"
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "Public subnet IDs for ALB placement"
}

variable "alb_security_group_id" {
  type        = string
  description = "Security group ID for the ALB"
}

variable "container_port" {
  type        = number
  description = "Application port on ECS container"
  default     = 8000
}

variable "certificate_arn" {
  type        = string
  description = "ARN of ACM TLS Certificate for HTTPS listener (optional for dev/mock)"
  default     = ""
}
