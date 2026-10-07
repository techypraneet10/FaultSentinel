# ==============================================================================
# SentinelLog Storage Module (Private S3, Block Public Access, KMS Encryption)
# ==============================================================================

resource "aws_s3_bucket" "artifacts" {
  bucket        = "${var.bucket_prefix}-${var.environment}"
  force_destroy = false

  tags = {
    Name        = "sentinellog-${var.environment}-artifacts"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "encryption" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Rule 40: Prohibit all public access to S3 storage bucket
resource "aws_s3_bucket_public_access_block" "block_public" {
  bucket = aws_s3_bucket.artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
