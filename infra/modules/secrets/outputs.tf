output "api_key_secret_arn" {
  value       = aws_secretsmanager_secret.api_key.arn
  description = "ARN of the API key secret"
}

output "db_credentials_secret_arn" {
  value       = aws_secretsmanager_secret.db_credentials.arn
  description = "ARN of the database credentials secret"
}

output "qdrant_credentials_secret_arn" {
  value       = aws_secretsmanager_secret.qdrant_credentials.arn
  description = "ARN of the Qdrant credentials secret"
}

output "llm_credentials_secret_arn" {
  value       = aws_secretsmanager_secret.llm_credentials.arn
  description = "ARN of the LLM credentials secret"
}
