variable "aws_region" {
  type        = string
  description = "AWS production deployment region"
  default     = "us-east-1"
}

variable "image_uri" {
  type        = string
  description = "Immutable production container image URI (pinned to immutable tag or digest)"
}

variable "certificate_arn" {
  type        = string
  description = "ARN of ACM TLS Certificate for production HTTPS listener"
}
