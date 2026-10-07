output "repository_url" {
  value       = aws_ecr_repository.app.repository_url
  description = "URL of the ECR repository"
}

output "repository_arn" {
  value       = aws_ecr_repository.app.arn
  description = "ARN of the ECR repository"
}
