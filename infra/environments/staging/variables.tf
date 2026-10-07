variable "aws_region" {
  type        = string
  description = "AWS deployment region"
  default     = "us-east-1"
}

variable "image_uri" {
  type        = string
  description = "Immutable container image URI"
  default     = "123456789012.dkr.ecr.us-east-1.amazonaws.com/sentinellog-staging:v0.15.0"
}
