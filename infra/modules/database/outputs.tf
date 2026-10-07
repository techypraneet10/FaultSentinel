output "cluster_endpoint" {
  value       = aws_rds_cluster.aurora.endpoint
  description = "Writer endpoint for Aurora PostgreSQL cluster"
}

output "cluster_arn" {
  value       = aws_rds_cluster.aurora.arn
  description = "ARN of the Aurora PostgreSQL cluster"
}

output "database_security_group_id" {
  value       = aws_security_group.db.id
  description = "Security group ID of the database"
}
