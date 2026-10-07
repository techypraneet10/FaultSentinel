variable "environment" {
  type        = string
  description = "Target deployment environment"
}

variable "bucket_prefix" {
  type        = string
  description = "Prefix for S3 storage bucket"
  default     = "sentinellog-artifacts"
}
