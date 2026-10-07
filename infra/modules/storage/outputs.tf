output "bucket_id" {
  value       = aws_s3_bucket.artifacts.id
  description = "Name/ID of the private S3 artifacts bucket"
}

output "bucket_arn" {
  value       = aws_s3_bucket.artifacts.arn
  description = "ARN of the private S3 artifacts bucket"
}
