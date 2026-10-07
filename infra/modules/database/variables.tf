variable "environment" {
  type        = string
  description = "Target deployment environment"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for Aurora PostgreSQL cluster"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnets for database placement"
}

variable "ecs_security_group_id" {
  type        = string
  description = "Security group ID of ECS tasks authorized to connect"
}

variable "database_name" {
  type        = string
  description = "Name of the default PostgreSQL database"
  default     = "sentinellog"
}

variable "backup_retention_days" {
  type        = number
  description = "Backup retention period in days"
  default     = 7
}
