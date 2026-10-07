# ==============================================================================
# SentinelLog Secrets Module (AWS Secrets Manager Definitions)
# ==============================================================================
# Rule 6: Zero hardcoded secrets in source. Secret values are injected at runtime.

resource "aws_secretsmanager_secret" "api_key" {
  name                    = "sentinellog/${var.environment}/api_key"
  description             = "SentinelLog API Authentication Key for ${var.environment}"
  recovery_window_in_days = 7

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "sentinellog/${var.environment}/database"
  description             = "Aurora PostgreSQL credentials for ${var.environment}"
  recovery_window_in_days = 7

  tags = {
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret" "qdrant_credentials" {
  name                    = "sentinellog/${var.environment}/qdrant"
  description             = "Qdrant vector store credentials for ${var.environment}"
  recovery_window_in_days = 7

  tags = {
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret" "llm_credentials" {
  name                    = "sentinellog/${var.environment}/llm_api_key"
  description             = "LLM provider API key for ${var.environment}"
  recovery_window_in_days = 7

  tags = {
    Environment = var.environment
  }
}
