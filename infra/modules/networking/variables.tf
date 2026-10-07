variable "environment" {
  type        = string
  description = "Target deployment environment (staging, production)"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the VPC"
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  type        = list(string)
  description = "List of availability zones for multi-AZ topology"
  default     = ["us-east-1a", "us-east-1b"]
}

variable "public_subnet_cidrs" {
  type        = list(string)
  description = "CIDR blocks for public ingress subnets"
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  type        = list(string)
  description = "CIDR blocks for private application/data subnets"
  default     = ["10.0.10.0/24", "10.0.20.0/24"]
}

variable "container_port" {
  type        = number
  description = "Listening port of the SentinelLog container"
  default     = 8000
}
